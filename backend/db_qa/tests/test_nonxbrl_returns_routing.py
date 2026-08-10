"""Regression tests for the NON_XBRL_RETURNS hardening pass.

Each test names the wrong behavior it locks out, since every case here
came from a live misroute rather than from the taxonomy on paper:

  1. "what are the non-XBRL returns I have access to" answered with the
     caller's ROLE PERMISSIONS (permission_profile) instead of returns.
  2. "which departments can access non-XBRL returns" tried to resolve the
     literal string "non xbrl returns" as a RETURN NAME.
  3. "what is my next non-XBRL return due" answered with the whole
     non-XBRL access list instead of the next due date.
  4. Named-return questions only resolved when the name was typed exactly
     as stored.
  5. A non-XBRL question could resolve to an XBRL return, and vice versa.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from backend.db_qa import access_control, query_handlers as qh
from backend.db_qa.intents.taxonomy import Intent
from backend.db_qa.new_intent_classifier import classify_new
from backend.db_qa.xml_store import XMLStore

PATH_5_5 = Path(r"D:\Repo(new)\DataBase")
_need_5_5 = pytest.mark.skipif(not PATH_5_5.is_dir(), reason="5.5 real data tree not present")

ADMIN_LOGIN = "iris810"


@pytest.fixture
def store():
    return XMLStore(str(PATH_5_5))


def _c(text):
    intent, params, _ = classify_new(text)
    return intent, params


def _answer(text, store, login_id=ADMIN_LOGIN):
    """Classify -> authorize -> dispatch, i.e. exactly what the router does."""
    intent, params, _ = classify_new(text)
    assert intent is not None, f"unclassified: {text}"
    scope = access_control.scope_query({"login_id": login_id}, intent.value, params)
    return qh.dispatch2(intent, scope, params, store)


# ── 1. "non-XBRL returns I have access to" is a RETURNS question ─────────

@pytest.mark.parametrize("text", [
    "what are the non xbrl returns i have access?",
    "give me list of non xbrl returns for which i have access?",
    "show me the non xbrl returns i can access",
    "list the non xbrl returns available to me",
    "what non-xbrl returns am i able to access",
    "How many Non-XBRL returns do I have access to?",
])
def test_nonxbrl_access_questions_are_return_lists_not_permissions(text):
    intent, params = _c(text)
    assert intent == Intent.NONXBRL_RETURN_LIST, text
    # Must stay scoped to the caller — a system-wide count would be a
    # different (and wrong) answer to "returns I have access to".
    assert params.get("target_type") == "self", text


def test_genuine_permission_profile_still_routes_there():
    assert _c("what are my permissions")[0] == Intent.PERMISSION_PROFILE


# ── 2. type-level department access ──────────────────────────────────────

@pytest.mark.parametrize("text,expected_type", [
    ("which departments can access non xbrl returns", "non_xbrl"),
    ("which departments are assigned non xbrl returns", "non_xbrl"),
    ("what departments have non-xbrl return access", "non_xbrl"),
    ("which departments have access to xbrl returns", "xbrl"),
])
def test_type_level_department_access(text, expected_type):
    intent, params = _c(text)
    assert intent == Intent.DEPARTMENTS_WITH_RETURN_ACCESS, text
    assert params.get("xbrl_type") == expected_type, text
    # The category phrase must NOT be mistaken for a return name.
    assert not params.get("target_return"), text


def test_named_return_department_access_still_extracts_the_name():
    intent, params = _c("which departments have access to return CIMS_ROR?")
    assert intent == Intent.DEPARTMENTS_WITH_RETURN_ACCESS
    assert params.get("target_return") == "CIMS_ROR"
    assert not params.get("xbrl_type")


@pytest.mark.parametrize("text", [
    "which xbrl returns does department Dept1 have access to?",
    "what returns does my department have access to",
])
def test_single_department_questions_are_not_stolen_by_type_level_rule(text):
    assert _c(text)[0] == Intent.DEPARTMENT_RETURNS, text


# ── 3. next due return ───────────────────────────────────────────────────

@pytest.mark.parametrize("text", [
    "what is my next non xbrl return due?",
    "what is my next non xbrl return has due?",
    "which non xbrl return is due next",
    "what is my next due non xbrl return",
])
def test_next_due_nonxbrl(text):
    intent, params = _c(text)
    assert intent == Intent.REPORTS_UPCOMING_IN_RANGE, text
    assert params.get("query_type") == "next_due", text
    assert params.get("xbrl_type") == "non_xbrl", text


def test_next_due_without_a_type_covers_all_returns():
    intent, params = _c("when is my next return due")
    assert intent == Intent.REPORTS_UPCOMING_IN_RANGE
    assert params.get("query_type") == "next_due"
    assert params.get("xbrl_type") is None


def test_named_return_due_date_is_still_next_reporting_date():
    """The name between "return" and "due" is what separates this from the
    next_due form — it must keep winning."""
    intent, params = _c("When is my next Non-XBRL return BSR1(Quarterly) due?")
    assert intent == Intent.NEXT_REPORTING_DATE
    assert params.get("target_return") == "BSR1(Quarterly)"


def test_overdue_is_unchanged():
    intent, params = _c("Are any of my Non-XBRL returns overdue?")
    assert intent == Intent.REPORTS_UPCOMING_IN_RANGE
    assert params.get("query_type") == "overdue"


# ── 4. name extraction robustness ────────────────────────────────────────

@pytest.mark.parametrize("text,expected", [
    ("is non xbrl return BSR1(Quarterly) CIMS-enabled?", "BSR1(Quarterly)"),
    ("is non xbrl return bsr1-quarterly CIMS-enabled?", "bsr1-quarterly"),
    ("how many due days does non xbrl return R002 have", "R002"),
    ("tell me about the non xbrl return natural calamity relief measure",
     "natural calamity relief measure"),
    ("details of non xbrl return Collateral Loan", "Collateral Loan"),
    ("Is the report ready for my Non-XBRL submission of BSR1(Quarterly)?",
     "BSR1(Quarterly)"),
])
def test_return_name_extraction_variants(text, expected):
    intent, params = _c(text)
    assert intent == Intent.NONXBRL_RETURN_PROFILE, text
    assert params.get("target_return") == expected, text


# ── 5. return-type safety at the data layer ──────────────────────────────

@_need_5_5
def test_find_return_candidates_respects_type(store):
    # CIMS_ROR is an XBRL return; asking for it within the non-XBRL pool
    # must find nothing rather than falling back across the type boundary.
    assert store.find_return_candidates("CIMS_ROR", xbrl_type="non_xbrl") == []
    assert [r.get("Name") for r in store.find_return_candidates("CIMS_ROR", xbrl_type="xbrl")] == ["CIMS_ROR"]
    # BSR1(Quarterly) is non-XBRL; the restricted lookup returns exactly it.
    assert [r.get("Name") for r in
            store.find_return_candidates("BSR1(Quarterly)", xbrl_type="non_xbrl")] == ["BSR1(Quarterly)"]
    assert "BSR1(Quarterly)" not in [
        r.get("Name") for r in store.find_return_candidates("BSR1(Quarterly)", xbrl_type="xbrl")]


# ── politeness preambles must not narrow scope ───────────────────────────

@pytest.mark.parametrize("text", [
    "Can you show me which Non-XBRL returns have no due days configured?",
    "I need to know which Non-XBRL returns have no due days configured.",
])
def test_request_framing_does_not_change_scope(text):
    """"I need to know ..." is a request framing, not a self-reference —
    left unstripped it answered the caller's own 20 returns while the
    identical "Can you show me ..." answered all 89."""
    intent, params = _c(text)
    assert intent == Intent.NONXBRL_RETURN_LIST, text
    assert params.get("target_type") == "department", text


def test_genuine_self_reference_after_a_preamble_still_counts():
    assert _c("I want to know my role")[1].get("target_type") == "self"


# ── end-to-end: the four reported questions produce real answers ─────────

@_need_5_5
@pytest.mark.parametrize("text", [
    "what are the non xbrl returns i have access?",
    "give me list of non xbrl returns for which i have access?",
])
def test_e2e_my_nonxbrl_returns(text, store):
    res = _answer(text, store)
    assert res["intent"] == "nonxbrl_return_list"
    assert res["label"] == "My Non-XBRL Returns"
    # Department-scoped, so strictly fewer than the full catalogue — the
    # bug being locked out returned the permission matrix instead.
    assert 0 < len(res["records"]) < len(store.non_xbrl_returns())
    assert "access to" in res["summary"]


@_need_5_5
def test_e2e_departments_with_nonxbrl_access(store):
    res = _answer("which departments can access non xbrl returns", store)
    assert res["intent"] == "departments_with_return_access"
    assert res["records"], "expected at least one department"
    assert "non-XBRL" in res["summary"]
    # Every listed department must genuinely hold a real non-XBRL return.
    nx_ids = {v for r in store.non_xbrl_returns()
              for v in (r.get("Id", ""), r.get("ReturnId", "")) if v}
    for d in res["records"]:
        assert {f.strip() for f in (d.get("NXForms") or "").split("|") if f.strip()} & nx_ids


@_need_5_5
@pytest.mark.parametrize("text", [
    "what is my next non xbrl return due?",
    "what is my next non xbrl return has due?",
])
def test_e2e_next_due_nonxbrl(text, store):
    res = _answer(text, store)
    assert res["intent"] == "reports_upcoming_in_range"
    assert res["records"], "expected at least one upcoming return"
    assert res["meta"].get("next_due_date")
    # The whole point: a single next-due answer, not the 20-row access list.
    assert len(res["records"]) < len(_answer(
        "what are the non xbrl returns i have access?", store)["records"])
    nx_names = {r.get("Name", "") for r in store.non_xbrl_returns()}
    for row in res["records"]:
        assert row["ReturnName"] in nx_names, "an XBRL return leaked into a non-XBRL answer"


@_need_5_5
@pytest.mark.parametrize("text", [
    "is non xbrl return bsr1-quarterly CIMS-enabled?",
    "how many due days does non xbrl return R002 have",
    "frequency of bsr1 quarterly",
])
def test_e2e_name_variants_resolve_to_the_same_return(text, store):
    res = _answer(text, store)
    assert "BSR1(Quarterly)" in res["summary"], res["summary"]


# ── functionality that already worked and must keep working ─────────────

@_need_5_5
@pytest.mark.parametrize("text,expected_intent", [
    ("How many Non-XBRL returns are there in total?", "nonxbrl_return_list"),
    ("List all Non-XBRL returns with their return IDs and frequencies.", "nonxbrl_return_list"),
    ("How many Non-XBRL returns do I have access to?", "nonxbrl_return_list"),
    ("Which Non-XBRL returns have no due days configured?", "nonxbrl_return_list"),
    ("Which Non-XBRL returns have a folder structure?", "nonxbrl_return_list"),
    ("Are any of my Non-XBRL returns overdue?", "reports_upcoming_in_range"),
])
def test_e2e_previously_working_questions_unchanged(text, expected_intent, store):
    res = _answer(text, store)
    assert res["intent"] == expected_intent, text
    assert res["records"], text
