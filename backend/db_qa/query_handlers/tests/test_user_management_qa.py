"""User Management Q&A: one named user's own attribute vs. a listing.

Every question here shares its nouns with a listing intent — "the
department of user atharv815" contains both "department" and "user", the
same two words as "which users are in the Finance department". The
difference is a NAME sitting where only a username can sit, and these
tests pin that distinction down in both directions:

  * naming a user must reach USER_FIELD, with the username extracted and
    no sentence fragment ("attempts", "their", "role") mistaken for one;
  * naming no user must stay with the listing intent it belonged to.

Classification only — no XMLStore needed, so these run everywhere. The
handler-side behaviour they feed (department/role resolved off the
enriched user row) is covered by test_new_handlers.py.
"""
from __future__ import annotations

import pytest

from backend.agent.db_qa_router import _build_db_qa_data
from backend.db_qa.new_intent_classifier import classify_new
from backend.db_qa.intents.taxonomy import Intent


def _classify(q: str):
    intent, params, _target_type = classify_new(q)
    return intent, params


# ── single named user: department / role ─────────────────────────────────

@pytest.mark.parametrize("question, field, name", [
    ("what is the department of user atharv815", "department", "atharv815"),
    ("what is the department of atharv815", "department", "atharv815"),
    ("What is the department of user jsmith?", "department", "jsmith"),
    ("what is the role of user atharv815", "role", "atharv815"),
    ("what is the role of atharv810", "role", "atharv810"),
    ("what is the role of atharv8100", "role", "atharv8100"),
    ("What is the role for jsmith?", "role", "jsmith"),
    ("atharv815's department", "department", "atharv815"),
    ("what is the role of user maker", "role", "maker"),
])
def test_named_user_attribute_lookup(question, field, name):
    intent, params = _classify(question)
    assert intent is Intent.USER_FIELD, f"{question!r} -> {intent}"
    assert params["field"] == field
    assert params["target_user"] == name
    assert params["target_type"] == "other_user"


# ── failed-login attempts for a named user ───────────────────────────────

@pytest.mark.parametrize("question, name", [
    ("how many failed attempts user maker has ?", "maker"),
    ("how many failed login attempts does user maker have", "maker"),
    ("How many failed login attempts does user jsmith have?", "jsmith"),
    ("failed attempts of user atharv815", "atharv815"),
])
def test_failed_attempts_for_named_user(question, name):
    intent, params = _classify(question)
    assert intent is Intent.USER_FIELD
    assert params["field"] == "failed_login_count"
    assert params["target_user"] == name


def test_failed_attempts_for_self_stays_self():
    intent, params = _classify("how many failed login attempts does my account have")
    assert intent is Intent.USER_FIELD
    assert params["field"] == "failed_login_count"
    assert params["target_type"] == "self"
    assert not params.get("target_user")


# ── never mistake sentence grammar for a username ────────────────────────

@pytest.mark.parametrize("question", [
    "how many failed attempts user maker has ?",
    "which users have failed login attempts",
    "give me list of all users with their departments",
    "list all users along with their roles and departments",
    "which users are assigned the Admin User role",
    "what is my user code",
    "list all users",
])
def test_no_filler_word_is_extracted_as_a_name(question):
    _intent, params = _classify(question)
    for key in ("target_user", "target_role", "target_department"):
        value = (params.get(key) or "").lower()
        assert value not in {
            "user", "users", "role", "roles", "department", "departments",
            "attempts", "attempt", "their", "them", "code", "failed", "login",
        }, f"{question!r} extracted {key}={value!r}"


# ── list/filter questions must NOT become single-user lookups ────────────

@pytest.mark.parametrize("question, expected", [
    ("give me list of all users with their departments",
     Intent.USERS_WITH_ROLES_AND_DEPARTMENTS),
    ("give me list of all users along with their departments",
     Intent.USERS_WITH_ROLES_AND_DEPARTMENTS),
    ("list all users with their roles", Intent.USERS_WITH_ROLES_AND_DEPARTMENTS),
    ("list all users along with their roles and departments",
     Intent.USERS_WITH_ROLES_AND_DEPARTMENTS),
    ("which users belong to the Finance department", Intent.USERS_BY_DEPARTMENT),
    ("which users are assigned the Admin User role", Intent.USERS_BY_ROLE),
    ("give me all admin users", Intent.USERS_BY_ROLE),
    ("users assigned to Admin", Intent.USERS_BY_ROLE),
    ("list all users", Intent.USER_LIST),
    ("which users have failed login attempts", Intent.USER_LIST),
    ("how many users are there", Intent.USER_LIST),
    # A per-role user COUNT is an aggregation over roles, not a user listing —
    # relaxing USERS_WITH_ROLES_AND_DEPARTMENTS to one noun put it in range.
    ("List all roles along with the number of users in each.", Intent.ROLE_LIST),
])
def test_listing_questions_keep_their_intent(question, expected):
    intent, _params = _classify(question)
    assert intent is expected, f"{question!r} -> {intent}"


def test_users_with_departments_needs_no_department_filter():
    """The reported failure: this asked "Please specify a department name."
    because it landed on USERS_BY_DEPARTMENT with nothing to filter by."""
    intent, params = _classify("give me list of all users with their departments")
    assert intent is Intent.USERS_WITH_ROLES_AND_DEPARTMENTS
    assert not params.get("target_department")


# ── the Failed Logins column ─────────────────────────────────────────────

_USER_ROW = {
    "Name": "Tester", "LoginId": "test810", "EmailId": "t@example.com",
    "DeptName": "Dept 1", "RoleName": "Maker", "Status": "true",
    "LastLoginDT": "17-Apr-2025 04:36:07 PM", "FailedLoginCount": "2",
}


def test_general_user_table_has_no_failed_logins_column():
    data = _build_db_qa_data(
        {"label": "All Users", "summary": "", "records": [_USER_ROW, _USER_ROW],
         "meta": {}}, "user_list")
    assert data["headers"] == ["Name", "Login ID", "Email", "Department",
                               "Role", "Status", "Last Login"]
    assert "FailedLoginCount" not in data["cols"]


def test_failed_login_question_still_shows_the_count():
    data = _build_db_qa_data(
        {"label": "Users with Failed Login Attempts", "summary": "",
         "records": [_USER_ROW, _USER_ROW],
         "meta": {"show_failed_logins": True}}, "user_list")
    assert "Failed Logins" in data["headers"]
    assert data["records"][0]["FailedLoginCount"] == "2"


def test_single_user_failed_login_answer_is_not_blank():
    """USER_FIELD returns one record holding only FailedLoginCount — hiding
    the column unconditionally would render it with no columns at all."""
    data = _build_db_qa_data(
        {"label": "Failed Login Count", "summary": "",
         "records": [{"FailedLoginCount": "3"}],
         "meta": {"show_failed_logins": True}}, "user_field")
    assert data["headers"] == ["Failed Logins"]
    assert data["records"] == [{"FailedLoginCount": "3"}]
