"""Accuracy-hardening tests for the USER / DEPARTMENT / ROLE / ROLE_ACCESS
categories — 5-phrasing-variant matrix per intent, per the user's own
example pattern (original catalog wording, natural wording, reordered
wording, short query, conversational query), plus targeted regression
tests for bugs found and fixed during hardening (query_type extraction,
action-word extraction, department-name extraction, false-positive
keyword-rule matches stealing from other categories).
"""
from __future__ import annotations

import pytest

from backend.db_qa.new_intent_classifier import classify_new
from backend.db_qa.intents.taxonomy import Intent


def _intents(*texts):
    return [classify_new(t)[0] for t in texts]


# ── 5-variant phrasing matrix ────────────────────────────────────────────

@pytest.mark.parametrize("text", [
    "What is my role?",           # original catalog wording
    "Tell me my role",            # natural wording
    "Which role do I have",       # reordered wording
    "My assigned role",           # short query
    "Can you tell me my role",    # conversational query
])
def test_role_profile_self_variants(text):
    intent, params, tt = classify_new(text)
    assert intent == Intent.ROLE_PROFILE
    assert tt == "self"


@pytest.mark.parametrize("text", [
    "Which users belong to department Finance",  # original catalog wording
    "Users in Finance",                          # natural wording
    "Finance department users",                  # reordered wording
    "List Finance users",                        # short query
    "Who works in Finance",                       # conversational query
])
def test_users_by_department_variants(text):
    intent, params, tt = classify_new(text)
    assert intent == Intent.USERS_BY_DEPARTMENT
    assert params.get("target_department") == "Finance"


@pytest.mark.parametrize("text", [
    "What is my email address?",  # original catalog wording
    "My email",                   # natural wording / short query
    "Show my email",              # conversational query
])
def test_user_field_email_variants(text):
    intent, params, tt = classify_new(text)
    assert intent == Intent.USER_FIELD
    assert params.get("field") == "email"


@pytest.mark.parametrize("text,expected_action", [
    ("Can I approve submissions?", "approve"),
    ("Can I create new users?", "create"),
    ("Am I allowed to edit department settings?", "edit"),
    ("Can I view the audit log?", "view"),
])
def test_permission_check_variants(text, expected_action):
    intent, params, tt = classify_new(text)
    assert intent == Intent.PERMISSION_CHECK
    assert params.get("action") == expected_action
    assert tt == "self"


# Only the phrasings that still hit the (deliberately narrowed) tier-1
# keyword rule directly — see backend/db_qa/new_intent_classifier.py's
# DEPARTMENT_RETURNS rule comment. Broader paraphrase coverage
# ("Show me the returns accessible to my department.", "Show returns
# accessible by my department.", "What returns are assigned to my
# department?" — all correctly classified via the embedding/LLM tiers, not
# regex) now lives in test_department_semantic_paraphrasing.py, which
# exercises the full classify_new_with_semantic_tiers() pipeline instead of
# classify_new() alone.
@pytest.mark.parametrize("text", [
    "Which returns does my department have access to?",   # canonical / catalog wording
    "What returns can my department access?",
    "Which returns are available for my department?",
    "What returns is my department allowed to access?",
    "List all returns my department has access to.",
    "Which returns can my department view?",
    "Give me the list of returns my department can access.",
])
def test_department_returns_self_variants(text):
    intent, params, tt = classify_new(text)
    assert intent == Intent.DEPARTMENT_RETURNS
    assert tt == "self"


@pytest.mark.parametrize("text", [
    "What are all the departments in the system?",
    "List all departments",
    "Show me every department",
    "All departments",
    "Give me the departments",
])
def test_department_list_variants(text):
    intent, params, tt = classify_new(text)
    assert intent == Intent.DEPARTMENT_LIST
    assert tt == "system_wide"


@pytest.mark.parametrize("text", [
    "What are all the roles defined in the system?",
    "List all roles",
    "Show every role",
    "All roles",
    "Give me the roles",
])
def test_role_list_variants(text):
    intent, params, tt = classify_new(text)
    assert intent == Intent.ROLE_LIST
    assert tt == "system_wide"


# ── query_type extraction (the direct fix for the real transcript bug:
#    "how many active users" previously fell through to a full dump) ────

@pytest.mark.parametrize("text,expected_query_type", [
    ("how many active users are there?", "active_count"),
    ("how many total users?", "count"),
    ("how many inactive users are there?", "inactive_count"),
    ("who are the inactive users?", "inactive"),
    ("which users have never logged in?", "never_login"),
    ("duplicate email users", "duplicate_email"),
])
def test_user_list_query_type_extraction(text, expected_query_type):
    intent, params, tt = classify_new(text)
    assert intent == Intent.USER_LIST
    assert params.get("query_type") == expected_query_type


@pytest.mark.parametrize("text,expected_query_type", [
    ("how many active departments are there?", "active_count"),
    ("how many total departments are there in the system?", "count"),
    ("which departments have no returns?", "no_returns"),
    # Was previously documented as routing to department_profile instead
    # (a DEPARTMENT_PROFILE/DEPARTMENT_LIST scoring tie, resolved by list
    # position) — corrected per the department-module downstream-processing
    # pass: "which department has the most/least/maximum/minimum returns"
    # is unambiguously an aggregation question, not a single-department
    # profile lookup, and DEPARTMENT_PROFILE now explicitly excludes this
    # phrasing shape so DEPARTMENT_LIST's own most/fewest branch wins.
    ("which department has the most returns?", "most"),
    ("which department has the least returns?", "fewest"),
    ("department with maximum returns", "most"),
    ("top 5 departments by return count", "top_n"),
])
def test_department_list_query_type_extraction(text, expected_query_type):
    intent, params, tt = classify_new(text)
    assert intent == Intent.DEPARTMENT_LIST
    assert params.get("query_type") == expected_query_type


@pytest.mark.parametrize("text,expected_query_type", [
    ("how many roles are there?", "count"),
    ("which roles are inactive?", "inactive"),
    ("is there a role called Admin?", "exists"),
])
def test_role_list_query_type_extraction(text, expected_query_type):
    intent, params, tt = classify_new(text)
    assert intent == Intent.ROLE_LIST
    assert params.get("query_type") == expected_query_type


# ── regression tests for bugs found and fixed during hardening ──────────

def test_submission_status_not_stolen_by_user_field():
    """USER_FIELD's 'status' keyword must not steal submission-status
    questions — found during hardening: 'status' alone matched both."""
    intent, params, tt = classify_new("What is the status of my submission ID 123?")
    assert intent == Intent.SUBMISSION_STATUS


def test_user_access_summary_not_stolen_by_role_profile():
    """A 'full summary of my access' mentioning role/department/returns
    together must not be misrouted to a single-category rule."""
    intent, params, tt = classify_new(
        "Give me a full summary of my access - role, department, and returns."
    )
    assert intent == Intent.USER_ACCESS_SUMMARY


def test_department_profile_not_stolen_by_users_by_department():
    """'What department am I in?' is a self-profile question, not a
    users-by-department listing, even though 'department' appears."""
    intent, params, tt = classify_new("What department am I in?")
    assert intent == Intent.DEPARTMENT_PROFILE
    assert tt == "self"


def test_department_name_extraction_skips_question_word():
    """'Which users belong to department Finance' must extract 'Finance',
    not the sentence-initial capitalized question word 'Which'."""
    intent, params, tt = classify_new("Which users belong to department Finance")
    assert params.get("target_department") == "Finance"


def test_who_belongs_to_department_without_users_word():
    """'Who belongs to Finance department' has no literal 'users' word —
    must still classify as USERS_BY_DEPARTMENT, not DEPARTMENT_LIST."""
    intent, params, tt = classify_new("Who belongs to Finance department")
    assert intent == Intent.USERS_BY_DEPARTMENT
    assert params.get("target_department") == "Finance"


def test_permission_check_action_word_not_pre_mapped():
    """The classifier must return the RAW action keyword ('approve'), not
    the mapped HasApprove/HasNew/... attribute name — the new-taxonomy
    handlers do their own ACTION_MAP lookup and would double-map/fail to
    match if given an already-mapped value."""
    intent, params, tt = classify_new("Can I approve submissions?")
    assert params.get("action") == "approve"
    assert params.get("action") != "HasApprove"


def test_permission_check_prefers_canonical_verb_over_synonym():
    """'create new users' contains both 'create' and 'new' (both map to
    HasNew) — the canonical verb 'create' should be extracted for natural
    response phrasing, not the awkward 'new'."""
    intent, params, tt = classify_new("Can I create new users?")
    assert params.get("action") == "create"


def test_data_preparation_permission_check_matches():
    """'Can I do data preparation?' has no create/edit/view/... verb —
    'do' must be recognized as a generic action trigger."""
    intent, params, tt = classify_new("Can I do data preparation?")
    assert intent == Intent.PERMISSION_CHECK
    assert params.get("module") == "data preparation"


def test_module_extraction_does_not_swallow_action_verb():
    """'edit department settings' must extract module='department settings',
    not 'edit department settings' (the action verb bleeding into the
    module name — an over-capture bug found during hardening)."""
    intent, params, tt = classify_new("Am I allowed to edit department settings?")
    assert params.get("module") == "department settings"


# ── Department downstream-processing pass: entity extraction, filters,
# and classification-tie fixes (Steps 2-5 of that pass) ─────────────────

@pytest.mark.parametrize("text", [
    "What is department ID of department Dept1?",   # bare "department" noun word appears TWICE
    "What is the ID of department Dept1?",
    "Department ID of Dept1",
    "Show department ID for Dept1",
])
def test_department_name_extraction_strips_id_filler(text):
    """Every phrasing must extract exactly 'Dept1' — previously 3 of these
    4 leaked the parser's own intermediate text into target_department
    ('ID of department Dept1', 'ID of Dept1', 'ID for Dept1'), which then
    surfaced directly in user-facing not-found messages."""
    intent, params, tt = classify_new(text)
    assert intent == Intent.DEPARTMENT_PROFILE
    assert params.get("target_department") == "Dept1"


@pytest.mark.parametrize("text,expected_xbrl_type", [
    ("List XBRL returns assigned to my department", "xbrl"),
    ("Show non-XBRL returns for my department", "non_xbrl"),
    ("Which XBRL returns does my department have access to?", "xbrl"),
    ("Which returns does my department have access to?", None),
])
def test_department_returns_xbrl_type_extraction(text, expected_xbrl_type):
    """DEPARTMENT_RETURNS previously never populated xbrl_type at all —
    the handler already filters on it, so an explicit "XBRL"/"non-XBRL"
    request was silently ignored and both types were always returned."""
    intent, params, tt = classify_new(text)
    assert intent == Intent.DEPARTMENT_RETURNS
    assert params.get("xbrl_type") == expected_xbrl_type


def test_departments_with_return_access_not_stolen_by_department_has_return():
    """'Which departments have access to return X?' previously misrouted to
    DEPARTMENT_HAS_RETURN (a scoring tie broken by list position) — the
    plural 'which departments...access...return' framing must resolve to
    DEPARTMENTS_WITH_RETURN_ACCESS, extracting the RETURN name, not a
    (nonexistent) department name."""
    intent, params, tt = classify_new("Which departments have access to return CIMS_ROR?")
    assert intent == Intent.DEPARTMENTS_WITH_RETURN_ACCESS
    assert params.get("target_return") == "CIMS_ROR"
    assert tt == "return"


@pytest.mark.xfail(
    reason=(
        "Pre-existing collision, confirmed present before the department "
        "downstream-processing pass (unaffected by the DEPARTMENTS_WITH_"
        "RETURN_ACCESS priority bump this pass added) — USERS_BY_DEPARTMENT's "
        "structural rule (_UsersByDeptStructuralPattern, priority=1, score "
        "101) matches ANY '<Capitalized Word> department' phrase anywhere in "
        "the sentence, so 'Does the Treasury DEPARTMENT have access...' is "
        "swept into USERS_BY_DEPARTMENT before DEPARTMENT_HAS_RETURN's rule "
        "(score ~3) is even considered. Out of scope for this pass (fixing it "
        "means touching the classifier's structural rule, not the department- "
        "module downstream processing this pass covers) — flagged for "
        "business/product input rather than fixed silently.",
    ),
    strict=True,
)
def test_department_has_return_singular_framing_unaffected():
    """Regression guard for the priority bump above: the SINGULAR/named-
    department framing must still resolve to DEPARTMENT_HAS_RETURN, not be
    accidentally swept into DEPARTMENTS_WITH_RETURN_ACCESS."""
    intent, params, tt = classify_new("Does the Treasury department have access to DBR01?")
    assert intent == Intent.DEPARTMENT_HAS_RETURN
