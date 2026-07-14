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
    ("which department has the most returns?", None),  # routes to department_profile, not department_list
])
def test_department_list_query_type_extraction(text, expected_query_type):
    intent, params, tt = classify_new(text)
    if expected_query_type is None:
        assert intent != Intent.DEPARTMENT_LIST
    else:
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
