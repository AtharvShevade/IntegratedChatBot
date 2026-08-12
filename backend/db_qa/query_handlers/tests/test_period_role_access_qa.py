"""PERIOD / ROLE / ROLE_ACCESS: rankings, per-group counts, permissions.

Three recurring shapes are pinned here:

  * a COUNT question answered with a LIST (and vice versa) — "how many
    reporting frequencies are defined?" returned all 23 rows, while "list
    roles along with the number of users in each" returned one row of
    totals;
  * a superlative with only half its vocabulary implemented — every
    "most returns" phrasing worked and every "least returns" phrasing
    either matched nothing or fell through to the plain list;
  * a permission question routed to a membership listing — "Can the Admin
    User create new users?" answered with the 14 people holding that role,
    because the role's own name ends in "User".
"""
from __future__ import annotations

import pytest

from backend.db_qa.new_intent_classifier import classify_new
from backend.db_qa.intents.taxonomy import Intent


def _classify(q: str):
    intent, params, _target_type = classify_new(q)
    return intent, params


# ── PERIOD ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("question", [
    "How many reporting frequencies are defined?",
    "how many frequencies are there?",
    "what is the total number of reporting frequencies?",
    "How many reporting periods are configured?",
])
def test_frequency_count_is_a_count_not_a_listing(question):
    intent, params = _classify(question)
    assert intent is Intent.PERIOD_LIST, f"{question!r} -> {intent}"
    assert params.get("query_type") == "count"


@pytest.mark.parametrize("question, expected", [
    ("Which frequency has the most returns?", "most_returns"),
    ("which frequency has maximum returns?", "most_returns"),
    ("Which reporting frequency has the highest number of returns?", "most_returns"),
    ("Which period has the most returns assigned?", "most_returns"),
    ("Which frequency has the least returns?", "least_returns"),
    ("which frequency has minimum returns?", "least_returns"),
    ("Which reporting frequency has the lowest number of returns?", "least_returns"),
    ("Which period has the fewest returns assigned?", "least_returns"),
])
def test_frequency_rankings_both_directions(question, expected):
    intent, params = _classify(question)
    assert intent is Intent.PERIOD_LIST, f"{question!r} -> {intent}"
    assert params.get("query_type") == expected


@pytest.mark.parametrize("question, period_id", [
    ("What is the period name for period ID 3?", "3"),
    ("what is the period name for period ID 107", "107"),
    ("what period is ID 103?", "103"),
    ("which period is id 105", "105"),
])
def test_numeric_period_id_is_extracted_as_a_period_id(question, period_id):
    """A numeric ID must resolve against the period data, never be treated
    as a return name to search for."""
    intent, params = _classify(question)
    assert intent is Intent.PERIOD_LOOKUP, f"{question!r} -> {intent}"
    assert params.get("period_id") == period_id
    assert not params.get("target_return")


@pytest.mark.parametrize("question", [
    "what is my reporting calendar",
    "show me my personal reporting calendar",
])
def test_personal_calendar(question):
    intent, params = _classify(question)
    assert intent is Intent.PERIOD_LOOKUP, f"{question!r} -> {intent}"
    assert params.get("query_type") == "personal_calendar"
    assert params.get("target_type") == "self"


@pytest.mark.parametrize("question, query_type", [
    ("What are all the reporting periods?", None),
    ("difference between QF and QAD frequencies", "compare"),
])
def test_existing_period_questions_unchanged(question, query_type):
    intent, params = _classify(question)
    assert intent is Intent.PERIOD_LOOKUP if query_type == "compare" else Intent.PERIOD_LIST
    assert params.get("query_type") == query_type


# ── ROLE ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("question", [
    "Give me list of roles along with the number of users in each",
    "List all roles along with the number of users in each.",
    "Show every role with its user count.",
    "How many users are assigned to each role?",
    "List each role and the number of users holding it.",
])
def test_per_role_user_counts(question):
    """A per-role breakdown, not "Total roles: 16 (14 active, 2 inactive)"
    and not a listing of the users holding one role."""
    intent, params = _classify(question)
    assert intent is Intent.ROLE_LIST, f"{question!r} -> {intent}"
    assert params.get("query_type") == "with_counts"


def test_plain_role_count_still_counts_roles():
    intent, params = _classify("How many roles are there in total?")
    assert intent is Intent.ROLE_LIST
    assert params.get("query_type") == "count"


def test_plain_user_count_still_counts_users():
    """The per-role exclusions must not swallow an ordinary user count."""
    intent, params = _classify("give me the count of users")
    assert intent is Intent.USER_LIST
    assert params.get("query_type") == "count"


@pytest.mark.parametrize("question, role", [
    ("What is the role ID of Tester?", "Tester"),
    ("What is Tester role ID?", "Tester"),
    ("What is the role ID of Admin User?", "Admin User"),
    ("What is the role ID for Admin User?", "Admin User"),
])
def test_role_id_lookup_is_not_a_user_listing(question, role):
    """"Admin User" ends in "User", which is all the structural
    users-of-a-role pattern needed to claim the question."""
    intent, params = _classify(question)
    assert intent is Intent.ROLE_PROFILE, f"{question!r} -> {intent}"
    assert params.get("target_role") == role
    assert params.get("want_role_id") is True


def test_role_id_by_number_resolves_the_name():
    intent, params = _classify("What is the name of role ID 101?")
    assert intent is Intent.ROLE_PROFILE
    assert params.get("role_id") == "101"


def test_my_role_does_not_request_the_id():
    _intent, params = _classify("what is my role")
    assert params.get("want_role_id") is False


@pytest.mark.parametrize("question, expected", [
    ("list all roles", Intent.ROLE_LIST),
    ("which roles are active", Intent.ROLE_LIST),
    ("which users have the Tester role", Intent.USERS_BY_ROLE),
    ("which role has the most users", Intent.ROLE_LIST),
    ("what is my role", Intent.ROLE_PROFILE),
    ("give me all admin users", Intent.USERS_BY_ROLE),
])
def test_existing_role_questions_unchanged(question, expected):
    intent, _params = _classify(question)
    assert intent is expected, f"{question!r} -> {intent}"


# ── ROLE_ACCESS ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("question", [
    "Which roles can create XBRL instances?",
    "Which roles are allowed to create XBRL instances?",
    "Who can create XBRL instances?",
])
def test_which_roles_can_create_xbrl_instances(question):
    """"XBRL instances" matched no module synonym, so the bare "roles"
    catch-all won and the answer was filtered by the Roles MENU module:
    "11 role(s) can create on role."."""
    intent, params = _classify(question)
    assert intent is Intent.ROLES_WITH_PERMISSION, f"{question!r} -> {intent}"
    assert params.get("action") == "create"
    assert params.get("module") == "xbrl generation"


@pytest.mark.parametrize("question", [
    "Can the Admin User create new users?",
    "Can Admin User create users?",
    "Does Admin User have permission to create users?",
    "Is Admin User allowed to create users?",
])
def test_named_role_permission_check(question):
    intent, params = _classify(question)
    assert intent is Intent.PERMISSION_CHECK, f"{question!r} -> {intent}"
    assert params.get("target_role") == "Admin User"
    assert params.get("action") == "create"
    assert params.get("module") == "user"
    assert params.get("target_type") == "role"


@pytest.mark.parametrize("question", [
    "Can I upload Non-XBRL files?",
    "Can I upload a Non-XBRL file?",
    "Do I have permission to upload Non-XBRL files?",
])
def test_self_permission_check_for_non_xbrl_upload(question):
    intent, params = _classify(question)
    assert intent is Intent.PERMISSION_CHECK, f"{question!r} -> {intent}"
    assert params.get("target_type") == "self"
    assert params.get("action") == "upload"
    assert params.get("module") == "fileupload"


def test_modules_i_do_not_have_access_to():
    intent, params = _classify("what modules do I not have access to")
    assert intent is Intent.PERMISSION_PROFILE
    assert params.get("query_type") == "not_access"
    assert params.get("target_type") == "self"


@pytest.mark.parametrize("question, expected", [
    ("what permissions do I have", Intent.PERMISSION_PROFILE),
    ("which modules can the Admin User role access", Intent.ROLE_MODULE_ACCESS),
    ("Which roles can upload Non-XBRL files?", Intent.ROLES_WITH_PERMISSION),
    ("Does role Tester have access to the SDMX generation module?", Intent.ROLE_MODULE_ACCESS),
    ("Can I create new users?", Intent.PERMISSION_CHECK),
    ("Can role Tester view the audit log?", Intent.PERMISSION_CHECK),
])
def test_existing_role_access_questions_unchanged(question, expected):
    intent, _params = _classify(question)
    assert intent is expected, f"{question!r} -> {intent}"


@pytest.mark.parametrize("question", [
    "Which roles can create XBRL instances?",
    "Can the Admin User create new users?",
    "Can I upload Non-XBRL files?",
])
def test_no_filler_word_becomes_a_role_or_module(question):
    _intent, params = _classify(question)
    assert (params.get("target_role") or "").lower() not in {
        "role", "roles", "user", "users", "permission", "create", "the", "which",
    }
    assert (params.get("module") or "").lower() not in {"role", "permission", "can"}
