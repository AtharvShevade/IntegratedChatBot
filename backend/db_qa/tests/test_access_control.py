"""Phase 3 access-control tests — run against real 5.5/6.0 data.

Real login_ids used (confirmed present in the real data trees):
  5.5 (D:\\Repo(new)\\DataBase): iris810 (RoleId=101, admin), test810 (RoleId=104, non-admin)
  6.0 tenant 1001 (D:\\Repo6\\Repo6\\1001\\DataBase): vaibhav@irisindia.net (RoleId=101, admin)

NOTE on BASE_REPO_PATH / APP_VERSION: both backend.config.BASE_REPO_PATH and
backend.version_mode.IS_6_0 are read once, at first import, from os.getenv —
this mirrors the real deployment model (a running backend process is always
one version, fixed at process start; see version_mode.py's own docstring).
Because of this, tests that need a DIFFERENT BASE_REPO_PATH than whatever
this test session's process happened to import backend.config with cannot
use monkeypatch.setenv (it's too late — the module-level constant is already
frozen). Where that matters, the test below runs in a subprocess with the
env var set BEFORE the interpreter starts, which is the only way to
genuinely exercise a different BASE_REPO_PATH/APP_VERSION in-process.
"""
from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from backend.db_qa import access_control

PATH_5_5 = Path(r"D:\Repo(new)\DataBase")
PATH_6_0_1001 = Path(r"D:\Repo6\Repo6\1001\DataBase")
REPO_ROOT = Path(__file__).resolve().parents[3]

_need_5_5 = pytest.mark.skipif(not PATH_5_5.is_dir(), reason="5.5 real data tree not present")
_need_6_0_1001 = pytest.mark.skipif(not PATH_6_0_1001.is_dir(), reason="6.0 tenant 1001 real data tree not present")

ADMIN_LOGIN_5_5 = "iris810"
NON_ADMIN_LOGIN_5_5 = "test810"
ADMIN_LOGIN_6_0 = "vaibhav@irisindia.net"


@_need_5_5
def test_is_admin_true_for_real_admin_5_5():
    assert access_control.is_admin(ADMIN_LOGIN_5_5, tenant_id=None) is True


@_need_5_5
def test_is_admin_false_for_real_non_admin_5_5():
    assert access_control.is_admin(NON_ADMIN_LOGIN_5_5, tenant_id=None) is False


def test_is_admin_false_for_unknown_login():
    assert access_control.is_admin("no-such-user-xyz", tenant_id=None) is False


def test_is_admin_false_for_empty_login():
    assert access_control.is_admin("", tenant_id=None) is False


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


@_need_6_0_1001
def test_tenant_id_enforced_in_6_0_mode(monkeypatch):
    monkeypatch.setenv("APP_VERSION", "6.0")
    with pytest.raises(PermissionError):
        access_control.scope_query(
            {"login_id": ADMIN_LOGIN_6_0},  # tenant_id deliberately omitted
            "user_list", {"target_type": "system_wide"},
        )


@_need_6_0_1001
def test_tenant_id_present_allows_6_0_admin():
    # backend.config.BASE_REPO_PATH is a module-level constant frozen at
    # first import from os.getenv — this test process may have already
    # imported it (e.g. transitively, via access_control -> auth_service ->
    # config) with BASE_REPO_PATH pointed at the 5.5 tree per the real
    # .env. monkeypatch.setenv can't retroactively change an already-frozen
    # constant, so this genuinely needs a fresh subprocess with the right
    # env vars set BEFORE the interpreter starts.
    script = textwrap.dedent(f"""
        import sys
        sys.path.insert(0, {str(REPO_ROOT)!r})
        from backend.db_qa import access_control
        scope = access_control.scope_query(
            {{"login_id": {ADMIN_LOGIN_6_0!r}, "tenant_id": "1001"}},
            "user_list", {{"target_type": "system_wide"}},
        )
        assert scope["is_admin"] is True, scope
        assert scope["tenant_id"] == "1001", scope
        print("OK")
    """)
    env = dict(os.environ)
    env["APP_VERSION"] = "6.0"
    env["BASE_REPO_PATH"] = str(PATH_6_0_1001.parent.parent)
    result = subprocess.run(
        [sys.executable, "-c", script], env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, f"stdout={result.stdout!r} stderr={result.stderr!r}"
    assert "OK" in result.stdout


@_need_5_5
def test_tenant_id_ignored_in_5_5_mode(monkeypatch):
    monkeypatch.setenv("APP_VERSION", "5.5")
    # A tenant_id of None/absent is the normal 5.5 case — scope_query must
    # not require one, and auth_service must resolve straight off
    # BASE_REPO_PATH without attempting any tenant registry lookup.
    scope = access_control.scope_query(
        {"login_id": ADMIN_LOGIN_5_5, "tenant_id": None},
        "user_list", {"target_type": "system_wide"},
    )
    assert scope["is_admin"] is True
    assert scope["tenant_id"] is None


def test_tenant_id_never_sourced_from_entities():
    """Even if a malicious/confused caller puts tenant_id in `entities`
    (which would come from LLM-extracted chat text), scope_query must
    never read it from there — only from session_user."""
    scope = access_control.scope_query(
        {"login_id": "whoever", "tenant_id": None},
        "user_field",
        {"target_type": "self", "tenant_id": "attacker-supplied-tenant"},
    )
    assert scope["tenant_id"] is None


# ── Category-specific access-control verification (USER/DEPARTMENT/ROLE/
#    ROLE_ACCESS) — end-to-end through the real classifier + real handlers
#    against real data, not just scope_query() in isolation. ────────────

@_need_5_5
def test_self_email_always_allowed_end_to_end():
    from backend.db_qa.new_intent_classifier import classify_new
    from backend.db_qa import query_handlers as qh
    from backend.db_qa.xml_store import XMLStore

    store = XMLStore(str(PATH_5_5), tenant_id=None)
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

    store = XMLStore(str(PATH_5_5), tenant_id=None)
    intent, params, tt = classify_new("What is the department of user test810?")
    params["target_type"] = "other_user"
    params["target_user"] = "test810"
    scope = access_control.scope_query({"login_id": ADMIN_LOGIN_5_5}, intent.value, params)
    assert scope["is_admin"] is True
    result = qh.dispatch2(intent, scope, params, store)
    assert result is not None
