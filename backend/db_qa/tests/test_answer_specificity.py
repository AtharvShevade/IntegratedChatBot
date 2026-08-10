"""Every question must answer ITSELF, not a neighbouring question.

These come from a systematic sweep of the whole catalogue
(app_db_questions_augmented.json) across USER, DEPARTMENT, ROLE,
ROLE_ACCESS, XBRL_RETURNS, NON_XBRL_RETURNS and DEPT_RETURN_MAPPING, tracing
each one Question -> Intent -> Params -> Handler -> Answer.

The failure mode they lock out is NOT "no answer" — it is a confident,
well-formatted answer to a DIFFERENT question. Several distinct questions
were all collapsing onto one intent and returning the same generic rows, so
the assertions here check the SUMMARY and the ROW SHAPE, not just the intent:
an intent can be right while the rows are about the wrong entity entirely.
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


@pytest.fixture(scope="module")
def store():
    return XMLStore(str(PATH_5_5))


def _c(text):
    intent, params, _tt = classify_new(text)
    return intent, params


def _answer(text, store, login_id=ADMIN_LOGIN):
    intent, params, _ = classify_new(text)
    assert intent is not None, f"unclassified: {text!r}"
    scope = access_control.scope_query({"login_id": login_id}, intent.value, params)
    return intent, qh.dispatch2(intent, scope, params, store)


# ── the DEPARTMENTS_WITH_RETURN_ACCESS magnet ────────────────────────────
#
# This intent answers exactly one question — "which departments have access
# to RETURN X" — but its dept+access+which groups plus a priority bump made
# it win four other question shapes, all answered "14 department(s) have
# access to at least one return."

@_need_5_5
@pytest.mark.parametrize("text,expected_intent", [
    ("which department has most returns assigned", Intent.DEPARTMENT_LIST),
    ("Which department has the most returns assigned?", Intent.DEPARTMENT_LIST),
    ("which department has access to most returns", Intent.DEPARTMENT_LIST),
    ("Which department has the fewest returns assigned?", Intent.DEPARTMENT_LIST),
])
def test_department_return_aggregations_name_one_department(text, expected_intent, store):
    intent, res = _answer(text, store)
    assert intent == expected_intent, text
    assert len(res["records"]) == 1, f"{text!r} -> expected a single winner, got {len(res['records'])}"
    assert "at least one return" not in res["summary"], text


@_need_5_5
@pytest.mark.parametrize("text", [
    "which department has access to all returns",
    "How many department has access to all returns",
])
def test_access_to_all_returns_is_a_coverage_question(text, store):
    """"ALL returns" means every return, not "at least one" — the old answer
    listed all 14 departments and called them all matches."""
    intent, res = _answer(text, store)
    assert intent == Intent.DEPT_RETURN_ACCESS_MATRIX, text
    assert "at least one return" not in res["summary"], text
    assert "all" in res["summary"].lower()


@_need_5_5
def test_departments_with_access_to_a_named_return_still_works(store):
    """Guard: the excludes above must not break the question this intent
    actually owns."""
    intent, res = _answer("How many department has access to return cims ror", store)
    assert intent == Intent.DEPARTMENTS_WITH_RETURN_ACCESS
    assert "CIMS_ROR" in res["summary"]
    assert res["records"]


# ── a named department is not a request for a list of departments ────────

@_need_5_5
@pytest.mark.parametrize("text", [
    "Can you show me which XBRL returns are assigned to department dept1?",
    "which XBRL returns are assigned to department Dept 1?",
    "what returns are assigned to department dept1",
])
def test_returns_of_a_named_department_returns_RETURNS(text, store):
    """The old exclude was `\\b(?i:department|dept)\\s+[A-Z]\\w*` — the inline
    (?i:) covers only the noun, so a lowercase name ("department dept1", how
    users actually type it) never matched and the answer was a list of
    DEPARTMENTS instead of that department's returns."""
    intent, res = _answer(text, store)
    assert intent == Intent.DEPARTMENT_RETURNS, text
    assert res["records"], text
    row = res["records"][0]
    assert "EmailId" not in row, f"{text!r} answered with DEPARTMENT rows: {sorted(row)[:6]}"
    assert any(k in row for k in ("ReturnCode", "ReturnName", "ReturnLabel", "ReturnId")), sorted(row)[:6]


# ── "access"/"run"/"use" mean ANY permission, not a missing flag ──────────

@_need_5_5
@pytest.mark.parametrize("text", [
    "Can I access the Balance Sheet module?",
    "Can I run cross-validation?",
    "Can I access data preparation?",
    "Am I allowed to run cross-validation?",
    "Do I have permission to access the Balance Sheet module?",
    "Which roles can access the Balance Sheet module?",
    "Which roles have access to the NXQueryBuilder?",
])
def test_any_permission_verbs_are_answered_not_refused(text, store):
    """There is no HasAccess column, so these verbs missed _ACTION_MAP, fell
    through to the LLM and came back "Sorry, I couldn't understand your
    request" — 17 catalogue questions in ROLE_ACCESS alone."""
    _intent, res = _answer(text, store)
    assert "couldn't understand" not in res["summary"], text
    assert "Unrecognized" not in res["summary"], text


def test_a_specific_verb_still_wins_over_the_any_verb():
    """"do I have ACCESS to CREATE users" is a create check, not an
    any-permission one — ordering in _CANONICAL_ACTION_ORDER guarantees it."""
    _i, p = _c("do i have access to create users")
    assert p.get("action") == "create"
    _i, p = _c("can i access the balance sheet")
    assert p.get("action") == "access"


# ── polite framing must not change the answer ────────────────────────────

@_need_5_5
@pytest.mark.parametrize("text", [
    "I need to know which roles can create XBRL instances.",
    "I need to know which roles can upload Non-XBRL files.",
])
def test_polite_framing_does_not_suppress_system_wide_role_questions(text, store):
    """ROLES_WITH_PERMISSION excluded a bare "\\bi\\b" as a self-reference, so
    "I need to know ..." matched no rule at all. The self-reference that
    matters is "can I"/"am I"/"do I", not any "I"."""
    intent, res = _answer(text, store)
    assert intent == Intent.ROLES_WITH_PERMISSION, text
    assert "couldn't understand" not in res["summary"], text


@_need_5_5
@pytest.mark.parametrize("prefix", ["", "Can you show me ", "I need to know "])
def test_role_with_most_users_is_stable_under_polite_prefixes(prefix, store):
    text = f"{prefix}which role has the most users?"
    intent, res = _answer(text, store)
    assert intent == Intent.ROLE_LIST, text
    assert "users in the system" not in res["summary"], \
        f"{text!r} answered with a flat user count: {res['summary']!r}"


# ── a role NAME containing a common noun ─────────────────────────────────

@_need_5_5
@pytest.mark.parametrize("prefix", ["", "Can you show me ", "I need to know "])
def test_admin_user_role_full_control_lists_modules(prefix, store):
    """"Admin User" is a real role name. "User" was a hard stop in the
    role-name extractor, so target_role came back empty AND "User" was then
    re-read as the MODULE — the answer was "11 role(s) have access to
    'user'", or a list of 14 users, or a count of all 16 roles."""
    text = f"{prefix}which modules does the Admin User role have full control over?"
    intent, res = _answer(text, store)
    assert intent == Intent.ROLE_MODULE_ACCESS, text
    assert "Admin User" in res["summary"], text
    assert "full control" in res["summary"].lower(), text


def test_role_name_extraction_handles_multiword_and_bare_nouns():
    _i, p = _c("which modules does the Admin User role have full control over?")
    assert p.get("target_role") == "Admin User"
    # ...but a bare generic noun is still not a name.
    _i, p = _c("which users have tester role in the system")
    assert p.get("target_role") == "tester"


# ── list-vs-check, and combined listings ─────────────────────────────────

@_need_5_5
@pytest.mark.parametrize("text", [
    "List all users along with their roles and departments.",
    "Can you list all users along with their roles and departments.",
    "Give me a list of all users along with their roles and departments.",
])
def test_users_with_roles_and_departments_has_a_route(text, store):
    """The intent, handler and exemplars all existed; no regex rule did, so
    USERS_BY_ROLE / USERS_BY_DEPARTMENT grabbed it, found no name to filter
    by, and asked the user to rephrase."""
    intent, res = _answer(text, store)
    assert intent == Intent.USERS_WITH_ROLES_AND_DEPARTMENTS, text
    assert res["records"], text
    assert "couldn't understand" not in res["summary"], text
    assert "Please specify" not in res["summary"], text


@_need_5_5
def test_what_modules_am_i_allowed_to_access_lists_modules(store):
    """A "what modules ..." question wants a LIST; landing on
    PERMISSION_CHECK produced the degenerate summary "You can access."."""
    _intent, res = _answer("What modules am I allowed to access?", store)
    assert res["summary"] != "You can access."
    assert res["records"], "expected a list of modules"


# ── password phrasings ───────────────────────────────────────────────────

@pytest.mark.parametrize("text", [
    "Which users have not updated their password recently?",
    "I need to know which users have not updated their password recently.",
])
def test_password_phrasings_classify(text):
    """The literal trigger was "not updated password"; real phrasing puts a
    possessive in between, so these matched no rule at all."""
    intent, _p = _c(text)
    assert intent is not None, text
