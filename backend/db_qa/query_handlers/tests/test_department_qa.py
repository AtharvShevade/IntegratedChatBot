"""Department Management Q&A: four questions that share the same nouns.

"departments" + "returns" + "assigned" describes all four of these, and
they have four different answers:

  A. departments with NO returns          -> DEPARTMENT_LIST/no_returns
  B. every department WITH its counts     -> DEPARTMENT_LIST/with_counts
  C. departments that can access RETURN X -> DEPARTMENTS_WITH_RETURN_ACCESS
  D. the returns of DEPARTMENT X          -> DEPARTMENT_RETURNS

Before these tests, A and B both landed on C, which answered "14
department(s) have access to at least one return" — a true statement about
a question nobody asked, and the most dangerous kind of wrong answer
because it looks like a real result.

The classification tests need no data. The resolution tests do, and are
skipped where the real XML tree isn't present.
"""
from __future__ import annotations

import pytest

from backend.db_qa.new_intent_classifier import classify_new
from backend.db_qa.intents.taxonomy import Intent
from backend.db_qa.xml_store import XMLStore


def _classify(q: str):
    intent, params, _target_type = classify_new(q)
    return intent, params


# ── A. no / zero / 0 returns — one intent, every phrasing ────────────────

@pytest.mark.parametrize("question", [
    "which department have 0 returns assigned ?",
    "which department have zero returns assigned ?",
    "which department have no returns assigned ?",
    "Which departments have no returns assigned?",
    "Which departments have zero returns assigned?",
    "show departments with no assigned returns",
    "departments without any returns",
    "which departments don't have any returns",
    "departments with 0 returns",
    "list departments with none assigned",
])
def test_no_returns_variants_all_reach_the_same_branch(question):
    intent, params = _classify(question)
    assert intent is Intent.DEPARTMENT_LIST, f"{question!r} -> {intent}"
    assert params["query_type"] == "no_returns"


# ── B. every department with its return counts ───────────────────────────

@pytest.mark.parametrize("question", [
    "give me list of departments along with the count of their returns",
    "give me list of all departments along with the count of their returns",
    "show each department with its return counts",
    "list departments with XBRL and Non-XBRL return counts",
    "list all departments with return counts",
    "give me departments along with their return counts",
    "give me all departments with their total returns",
    "show each department and the number of returns assigned",
])
def test_return_count_table_is_not_a_department_count(question):
    intent, params = _classify(question)
    assert intent is Intent.DEPARTMENT_LIST, f"{question!r} -> {intent}"
    # "count" would answer "how many departments exist" — the wrong question.
    assert params["query_type"] == "with_counts", f"{question!r} -> {params}"


def test_plain_department_count_still_counts_departments():
    """The with_counts patterns sit ahead of "count" in the query_type
    table; a genuine how-many-departments question must still get there."""
    intent, params = _classify("how many departments are there in total")
    assert intent is Intent.DEPARTMENT_LIST
    assert params["query_type"] == "count"


# ── C vs D: access to a named RETURN vs the returns of a named DEPARTMENT ─

@pytest.mark.parametrize("question, expected", [
    ("which departments have access to return CIMS_ROR", Intent.DEPARTMENTS_WITH_RETURN_ACCESS),
    ("how many departments have access to return CIMS_ROR", Intent.DEPARTMENTS_WITH_RETURN_ACCESS),
    ("xbrl returns assigned to department test", Intent.DEPARTMENT_RETURNS),
    ("non xbrl returns assigned to department test2", Intent.DEPARTMENT_RETURNS),
    ("Which XBRL returns are assigned to department test2?", Intent.DEPARTMENT_RETURNS),
    ("Which Non-XBRL returns are assigned to department test2?", Intent.DEPARTMENT_RETURNS),
])
def test_return_access_direction(question, expected):
    intent, _params = _classify(question)
    assert intent is expected, f"{question!r} -> {intent}"


@pytest.mark.parametrize("question, xbrl_type, dept", [
    ("xbrl returns assigned to department test", "xbrl", "test"),
    ("non xbrl returns assigned to department test2", "non_xbrl", "test2"),
    ("Which XBRL returns are assigned to department test2?", "xbrl", "test2"),
])
def test_department_return_entities(question, xbrl_type, dept):
    _intent, params = _classify(question)
    assert params["target_department"] == dept
    assert params["xbrl_type"] == xbrl_type


# ── ranking ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("question, expected_type", [
    ("which department have most returns assigned?", "most"),
    ("which department have least returns assigned?", "fewest"),
    ("which department has the highest number of returns?", "most"),
    ("which department has the lowest number of returns?", "fewest"),
    # rank word and noun separated by the relationship word — the ordering
    # the ranking pattern used to miss entirely.
    ("which department has the most assigned returns?", "most"),
    ("which department has the fewest assigned returns?", "fewest"),
    ("which department has the maximum returns?", "most"),
    ("which department has the minimum returns?", "fewest"),
])
def test_ranking_variants(question, expected_type):
    intent, params = _classify(question)
    assert intent is Intent.DEPARTMENT_LIST, f"{question!r} -> {intent}"
    assert params["query_type"] == expected_type


# ── profile / id lookups ─────────────────────────────────────────────────

@pytest.mark.parametrize("question, dept, want_id", [
    ("department test", "test", False),
    ("what is the department ID of department dept1", "dept1", True),
    ("what is the department ID of department test", "test", True),
    ("what is the ID of department test", "test", True),
    ("department ID for test", "test", True),
    ("what is test department ID", "test", True),
    ("give me the department ID of test", "test", True),
    # No standalone "department"/"dept" token at all — the name carries it.
    ("what is the id of dept1", "dept1", True),
])
def test_department_profile_lookups(question, dept, want_id):
    intent, params = _classify(question)
    assert intent is Intent.DEPARTMENT_PROFILE, f"{question!r} -> {intent}"
    assert params["target_department"] == dept
    assert bool(params.get("want_dept_id")) is want_id


@pytest.mark.parametrize("question", [
    # A screen name, not a department called "Management".
    "Department Management",
    # These carry their own signals and belong to other intents.
    "departments without any returns",
    "department with the most returns",
])
def test_bare_lookup_does_not_swallow_other_questions(question):
    intent, _params = _classify(question)
    assert intent is not Intent.DEPARTMENT_PROFILE, f"{question!r} -> {intent}"


# ── preserved behaviour ──────────────────────────────────────────────────

@pytest.mark.parametrize("question, expected, query_type", [
    ("give me all departments", Intent.DEPARTMENT_LIST, None),
    ("what are the departments currently active", Intent.DEPARTMENT_LIST, "active"),
    ("what are the inactive departments", Intent.DEPARTMENT_LIST, "inactive"),
    ("what is my department", Intent.DEPARTMENT_PROFILE, None),
    ("what are the XBRL returns accessible to my department", Intent.DEPARTMENT_RETURNS, None),
    ("what are the Non-XBRL returns accessible to my department", Intent.DEPARTMENT_RETURNS, None),
    ("what is the email address of department test", Intent.DEPARTMENT_PROFILE, None),
])
def test_existing_department_questions_still_work(question, expected, query_type):
    intent, params = _classify(question)
    assert intent is expected, f"{question!r} -> {intent}"
    if query_type is not None:
        assert params["query_type"] == query_type


# ── entity resolution: never answer about a department nobody named ──────

_store = XMLStore()
_has_data = bool(_store.departments())
_need_data = pytest.mark.skipif(not _has_data, reason="department data not present")


@_need_data
@pytest.mark.parametrize("query", [
    "tes1",   # 0.75 against "test" — close enough for the old 0.70 cutoff
    "t",      # one character; near-equidistant from half the list
    "te",
    "nonexistent department",
])
def test_partial_names_do_not_resolve_to_another_department(query):
    """A confident answer about the wrong department is worse than no
    answer: the user cannot tell it apart from a correct one."""
    assert _store.resolve_dept(query) is None


@_need_data
def test_case_distinguishes_two_same_named_departments():
    """This data has both "Test" (101) and "test" (118). A case-insensitive
    index collapses them and answers every question about either one with
    whichever row happened to be indexed last."""
    upper = _store.dept_by_name("Test")
    lower = _store.dept_by_name("test")
    if upper is None or lower is None:
        pytest.skip("both case variants not present in this dataset")
    assert upper.get("Name") == "Test"
    assert lower.get("Name") == "test"
    assert upper is not lower


@_need_data
@pytest.mark.parametrize("query, expected", [
    ("test2", "Test2"),
    ("Test2", "Test2"),
    # Punctuation/spacing the user dropped — an exact match on the
    # collapsed form, not a fuzzy guess.
    ("dept1", "Dept 1"),
    ("DEPT1", "Dept 1"),
    ("Dept 1", "Dept 1"),
])
def test_real_names_still_resolve(query, expected):
    d = _store.resolve_dept(query)
    assert d is not None, f"{query!r} did not resolve"
    assert d.get("Name") == expected
