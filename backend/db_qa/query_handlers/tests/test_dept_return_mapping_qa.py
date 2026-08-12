"""Department <-> return access questions: which side is the entity?

"which RETURNS department testing can access" and "which DEPARTMENTS have
access to CIMS_ROR" use the same three nouns and differ only in which one
is being asked about. Two extraction bugs followed from that:

  * the department extractor took the word immediately BEFORE
    "department" — which in this phrasing is "returns" — and answered
    "Department 'returns' was not found";
  * the return extractor anchored on the bare verb "access" and captured
    "to CIMS_ROR", turning an exact name into a 23-way disambiguation.

Both are filler-word problems, and both are pinned here alongside the
routing for the phrasings that reached no rule at all.
"""
from __future__ import annotations

import pytest

from backend.db_qa.new_intent_classifier import classify_new
from backend.db_qa.intents.taxonomy import Intent


def _classify(q: str):
    intent, params, _target_type = classify_new(q)
    return intent, params


# ── department name: never a filler word, never truncated ────────────────

@pytest.mark.parametrize("question, dept, xbrl_type", [
    ("which returns department test can access", "test", None),
    ("what are the xbrl returns department testing can access", "testing", "xbrl"),
    ("what are the non xbrl returns department test2 can access", "test2", "non_xbrl"),
    ("list of non xbrl returns department dept1 can access", "dept1", "non_xbrl"),
    ("what xbrl returns department testing can access", "testing", "xbrl"),
    ("what non xbrl returns department Test2 can access", "Test2", "non_xbrl"),
    ("List all returns department Test can access.", "Test", None),
    ("give me list of return of department testing", "testing", None),
    ("give me list of return accessible to department testing", "testing", None),
    ("Which returns can department Test access?", "Test", None),
    ("What returns can department Test access?", "Test", None),
    ("What can department Test access?", "Test", None),
    ("Which XBRL returns can department Test access?", "Test", "xbrl"),
    ("Which Non-XBRL returns can department Test2 access?", "Test2", "non_xbrl"),
    ("What XBRL returns are available to department Test2?", "Test2", "xbrl"),
    ("What Non-XBRL returns are available to department Test2?", "Test2", "non_xbrl"),
    ("show returns accessible by department Test", "Test", None),
    ("which returns are assigned to department Test", "Test", None),
    ("Which returns does department Test have access to?", "Test", None),
    # no "department" noun anywhere — the relationship verb is the anchor
    ("Which returns are assigned to Test?", "Test", None),
    # a trailing sentence period is not part of the name
    ("Give me all returns accessible to department Test.", "Test", None),
])
def test_department_name_extraction(question, dept, xbrl_type):
    intent, params = _classify(question)
    assert intent is Intent.DEPARTMENT_RETURNS, f"{question!r} -> {intent}"
    assert params.get("target_department") == dept, \
        f"{question!r} -> {params.get('target_department')!r}"
    assert params.get("xbrl_type") == xbrl_type


@pytest.mark.parametrize("question", [
    "which returns department test can access",
    "what are the xbrl returns department testing can access",
    "List all returns department Test can access.",
    "give me list of return of department testing",
    "Which returns are assigned to Test?",
])
def test_no_filler_word_becomes_the_department(question):
    _intent, params = _classify(question)
    assert (params.get("target_department") or "").lower() not in {
        "return", "returns", "access", "accessible", "assigned", "available",
        "department", "dept", "can", "what", "which", "list", "all",
    }, f"{question!r} -> {params.get('target_department')!r}"


def test_complete_access_list_is_a_listing_not_a_yes_no_check():
    """"complete return access list for department Test" was routed to
    DEPARTMENT_HAS_RETURN, whose return extractor then captured "access
    list for department Test" as the return name."""
    intent, params = _classify("What is the complete return access list for department Test?")
    assert intent is Intent.DEPARTMENT_RETURNS
    assert params.get("target_department") == "Test"
    assert not params.get("target_return")


def test_complete_list_of_returns_for_department_keeps_its_own_intent():
    """DEPT_FULL_RETURN_LIST owns this exact phrasing, and keyword rules run
    before the _mk rule that holds it — a DEPARTMENT_RETURNS trigger that
    also matches it silently takes the intent over."""
    intent, _params = _classify("What is the complete list of returns for department Test?")
    assert intent is Intent.DEPT_FULL_RETURN_LIST


# ── return name: the preposition is not part of it ───────────────────────

@pytest.mark.parametrize("question, name", [
    ("Which departments have access to CIMS_ROR?", "CIMS_ROR"),
    ("How many departments have access to CIMS_ROR?", "CIMS_ROR"),
    ("Which departments can access FormA?", "FormA"),
    ("which departments can submit CIMS_RAQ(Quarterly)", "CIMS_RAQ(Quarterly)"),
    ("which departments have access to return CIMS_ROR", "CIMS_ROR"),
    ("Which departments have access to BSR1(Quarterly)?", "BSR1(Quarterly)"),
])
def test_return_name_extraction(question, name):
    intent, params = _classify(question)
    assert intent is Intent.DEPARTMENTS_WITH_RETURN_ACCESS, f"{question!r} -> {intent}"
    assert params.get("target_return") == name, \
        f"{question!r} -> {params.get('target_return')!r}"


# ── preserved behaviour ──────────────────────────────────────────────────

@pytest.mark.parametrize("question, expected", [
    ("Which department has access to the most returns?", Intent.DEPARTMENT_LIST),
    ("Which returns are accessible by all departments?", Intent.DEPT_RETURN_ACCESS_MATRIX),
    ("Does my department have access to XBRL return R018?", Intent.DEPARTMENT_HAS_RETURN),
    ("Does my department have access to Non-XBRL return R002?", Intent.DEPARTMENT_HAS_RETURN),
    ("Give me the complete list of returns I can work with.", Intent.MY_RETURN_ACCESS),
    ("Which XBRL returns are accessible to my department?", Intent.DEPARTMENT_RETURNS),
    ("Which Non-XBRL returns are accessible to my department?", Intent.DEPARTMENT_RETURNS),
    ("xbrl returns assigned to department test", Intent.DEPARTMENT_RETURNS),
    ("non xbrl returns assigned to department test2", Intent.DEPARTMENT_RETURNS),
])
def test_existing_mapping_questions_still_route_the_same(question, expected):
    intent, _params = _classify(question)
    assert intent is expected, f"{question!r} -> {intent}"


@pytest.mark.parametrize("question", [
    "Which XBRL returns are accessible to my department?",
    "Which Non-XBRL returns are accessible to my department?",
])
def test_self_scope_is_preserved(question):
    _intent, params = _classify(question)
    assert params.get("target_type") == "self"
