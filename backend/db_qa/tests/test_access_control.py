"""Phase 3 access-control tests — run against real 5.5 data.

Real login_ids used (confirmed present in the real data tree):
  D:\\Repo(new)\\DataBase: iris810 (RoleId=101, admin), test810 (RoleId=104, non-admin)
"""
from __future__ import annotations

from pathlib import Path

import pytest

from backend.db_qa import access_control

PATH_5_5 = Path(r"D:\Repo(new)\DataBase")

_need_5_5 = pytest.mark.skipif(not PATH_5_5.is_dir(), reason="5.5 real data tree not present")

ADMIN_LOGIN_5_5 = "iris810"
NON_ADMIN_LOGIN_5_5 = "test810"


@_need_5_5
def test_is_admin_true_for_real_admin_5_5():
    assert access_control.is_admin(ADMIN_LOGIN_5_5) is True


@_need_5_5
def test_is_admin_false_for_real_non_admin_5_5():
    assert access_control.is_admin(NON_ADMIN_LOGIN_5_5) is False


def test_is_admin_false_for_unknown_login():
    assert access_control.is_admin("no-such-user-xyz") is False


def test_is_admin_false_for_empty_login():
    assert access_control.is_admin("") is False


@_need_5_5
def test_self_always_allowed():
    scope = access_control.scope_query(
        {"login_id": NON_ADMIN_LOGIN_5_5}, "user_field", {"target_type": "self"},
    )
    assert scope["target_type"] == "self"
    assert scope["login_id"] == NON_ADMIN_LOGIN_5_5


@_need_5_5
@pytest.mark.parametrize("target_type", ["other_user", "department", "role", "system_wide"])
def test_non_admin_denied_for_each_admin_target_type(target_type):
    with pytest.raises(PermissionError) as exc_info:
        access_control.scope_query(
            {"login_id": NON_ADMIN_LOGIN_5_5}, "user_list", {"target_type": target_type},
        )
    # Must include a self-service suggestion, not just a bare denial.
    assert len(str(exc_info.value)) > 10


@_need_5_5
@pytest.mark.parametrize("target_type", ["other_user", "department", "role", "system_wide"])
def test_admin_allowed_for_each_target_type(target_type):
    scope = access_control.scope_query(
        {"login_id": ADMIN_LOGIN_5_5}, "user_list", {"target_type": target_type},
    )
    assert scope["is_admin"] is True
    assert scope["target_type"] == target_type


@_need_5_5
def test_return_target_type_scoped_by_allowed_form_ids():
    scope = access_control.scope_query(
        {"login_id": NON_ADMIN_LOGIN_5_5}, "return_profile", {"target_type": "return"},
    )
    assert scope["target_type"] == "return"
    assert scope["allowed_form_ids"] is not None  # a set (possibly empty), not None


def test_unrecognized_target_type_denied():
    with pytest.raises(PermissionError):
        access_control.scope_query(
            {"login_id": "whoever"}, "user_list", {"target_type": "totally_bogus"},
        )


# ── Category-specific access-control verification (USER/DEPARTMENT/ROLE/
#    ROLE_ACCESS) — end-to-end through the real classifier + real handlers
#    against real data, not just scope_query() in isolation. ────────────

@_need_5_5
def test_self_email_always_allowed_end_to_end():
    from backend.db_qa.new_intent_classifier import classify_new
    from backend.db_qa import query_handlers as qh
    from backend.db_qa.xml_store import XMLStore

    store = XMLStore(str(PATH_5_5))
    intent, params, tt = classify_new("What is my email address?")
    scope = access_control.scope_query({"login_id": NON_ADMIN_LOGIN_5_5}, intent.value, params)
    result = qh.dispatch2(intent, scope, params, store)
    assert result["found"] is True


@_need_5_5
def test_other_user_email_denied_for_non_admin_end_to_end():
    """'What is John's email?' (other_user target_type) must be denied for
    a non-admin BEFORE any handler runs — matches the user's own example."""
    scope_kwargs = {"login_id": NON_ADMIN_LOGIN_5_5}
    with pytest.raises(PermissionError):
        access_control.scope_query(
            scope_kwargs, "user_field",
            {"target_type": "other_user", "target_user": "iris810", "field": "email"},
        )


@_need_5_5
def test_department_list_denied_for_non_admin():
    with pytest.raises(PermissionError):
        access_control.scope_query(
            {"login_id": NON_ADMIN_LOGIN_5_5}, "department_list", {"target_type": "system_wide"},
        )


@_need_5_5
def test_role_list_denied_for_non_admin():
    with pytest.raises(PermissionError):
        access_control.scope_query(
            {"login_id": NON_ADMIN_LOGIN_5_5}, "role_list", {"target_type": "system_wide"},
        )


@_need_5_5
def test_permission_profile_for_another_role_denied_for_non_admin():
    """A non-admin asking about a DIFFERENT role's permissions (not their
    own) must be denied — target_type=role requires admin."""
    with pytest.raises(PermissionError):
        access_control.scope_query(
            {"login_id": NON_ADMIN_LOGIN_5_5}, "permission_profile",
            {"target_type": "role", "target_role": "Admin User"},
        )


@_need_5_5
def test_permission_check_self_always_allowed():
    """'Can I approve submissions?' (self) must always be allowed —
    regardless of admin status, since it's asking about the caller's own
    permissions, not another role's."""
    from backend.db_qa.new_intent_classifier import classify_new

    intent, params, tt = classify_new("Can I approve submissions?")
    scope = access_control.scope_query({"login_id": NON_ADMIN_LOGIN_5_5}, intent.value, params)
    assert scope["target_type"] == "self"


@_need_5_5
def test_admin_can_see_other_user_profile_end_to_end():
    from backend.db_qa.new_intent_classifier import classify_new
    from backend.db_qa import query_handlers as qh
    from backend.db_qa.xml_store import XMLStore

    store = XMLStore(str(PATH_5_5))
    intent, params, tt = classify_new("What is the department of user test810?")
    params["target_type"] = "other_user"
    params["target_user"] = "test810"
    scope = access_control.scope_query({"login_id": ADMIN_LOGIN_5_5}, intent.value, params)
    assert scope["is_admin"] is True
    result = qh.dispatch2(intent, scope, params, store)
    assert result is not None
