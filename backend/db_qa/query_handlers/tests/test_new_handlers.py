"""Phase 4 tests — new-taxonomy handlers via dispatch2(), against real 5.5
data. One representative happy-path test per category, plus the
legacy-reexport-intact check and a denial-path check.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from backend.db_qa import access_control, query_handlers as qh
from backend.db_qa.xml_store import XMLStore

PATH_5_5 = Path(r"D:\Repo(new)\DataBase")
_need_5_5 = pytest.mark.skipif(not PATH_5_5.is_dir(), reason="5.5 real data tree not present")

ADMIN_LOGIN = "iris810"
NON_ADMIN_LOGIN = "test810"


@pytest.fixture
def store():
    return XMLStore(str(PATH_5_5))


def _scoped(login_id: str, intent: str, entities: dict) -> dict:
    return access_control.scope_query({"login_id": login_id}, intent, entities)


def test_legacy_reexport_intact():
    assert callable(qh.dispatch)
    assert callable(qh.handle_unknown)
    assert isinstance(qh.INTENT_TO_HANDLER, dict) and len(qh.INTENT_TO_HANDLER) > 0


@_need_5_5
def test_user_profile_self(store):
    scope = _scoped(ADMIN_LOGIN, "user_profile", {"target_type": "self"})
    r = qh.dispatch2("user_profile", scope, {"target_type": "self"}, store)
    assert r["found"] is True
    assert "iris810" in r["summary"]


@_need_5_5
def test_user_field_self(store):
    scope = _scoped(ADMIN_LOGIN, "user_field", {"target_type": "self"})
    r = qh.dispatch2("user_field", scope, {"target_type": "self", "field": "email"}, store)
    assert r["found"] is True


@_need_5_5
def test_department_returns_self(store):
    scope = _scoped(ADMIN_LOGIN, "department_returns", {"target_type": "self"})
    r = qh.dispatch2("department_returns", scope, {"target_type": "self"}, store)
    assert r["found"] is True
    assert "XBRL" in r["summary"]


@_need_5_5
def test_role_profile_self(store):
    scope = _scoped(ADMIN_LOGIN, "role_profile", {"target_type": "self"})
    r = qh.dispatch2("role_profile", scope, {"target_type": "self"}, store)
    assert r["found"] is True


@_need_5_5
def test_return_list_admin(store):
    scope = _scoped(ADMIN_LOGIN, "return_list", {"target_type": "system_wide"})
    r = qh.dispatch2("return_list", scope, {"target_type": "system_wide"}, store)
    assert r["found"] is True
    assert r["meta"]["count"] > 0


@_need_5_5
def test_dept_return_access_matrix(store):
    scope = _scoped(ADMIN_LOGIN, "dept_return_access_matrix", {"target_type": "system_wide"})
    r = qh.dispatch2("dept_return_access_matrix", scope, {"target_type": "system_wide"}, store)
    assert r["found"] is True


@_need_5_5
def test_submission_list_self(store):
    scope = _scoped(ADMIN_LOGIN, "submission_list", {"target_type": "self"})
    r = qh.dispatch2("submission_list", scope, {"target_type": "self"}, store)
    assert isinstance(r["records"], list)


@_need_5_5
def test_menu_list_self(store):
    scope = _scoped(ADMIN_LOGIN, "menu_list", {"target_type": "self"})
    r = qh.dispatch2("menu_list", scope, {"target_type": "self"}, store)
    assert r["found"] is True


@_need_5_5
def test_audit_history_self(store):
    scope = _scoped(ADMIN_LOGIN, "audit_history", {"target_type": "self"})
    r = qh.dispatch2("audit_history", scope, {"target_type": "self"}, store)
    assert isinstance(r["records"], list)


@_need_5_5
def test_user_access_summary_self(store):
    scope = _scoped(ADMIN_LOGIN, "user_access_summary", {"target_type": "self"})
    r = qh.dispatch2("user_access_summary", scope, {"target_type": "self"}, store)
    assert r["found"] is True
    assert "RoleName" in r["records"][0]


@_need_5_5
def test_bank_info(store):
    scope = _scoped(ADMIN_LOGIN, "bank_info", {"target_type": "self"})
    r = qh.dispatch2("bank_info", scope, {"target_type": "self"}, store)
    assert r["found"] is True


@_need_5_5
def test_segment_info(store):
    scope = _scoped(ADMIN_LOGIN, "segment_info", {"target_type": "self"})
    r = qh.dispatch2("segment_info", scope, {"target_type": "self"}, store)
    assert isinstance(r["records"], list)


@_need_5_5
def test_non_admin_denied_before_handler_runs():
    with pytest.raises(PermissionError):
        _scoped(NON_ADMIN_LOGIN, "user_list", {"target_type": "system_wide"})


@_need_5_5
def test_dispatch2_returns_none_for_unmigrated_intent(store):
    scope = _scoped(ADMIN_LOGIN, "totally_made_up_intent", {"target_type": "self"})
    result = qh.dispatch2("totally_made_up_intent", scope, {"target_type": "self"}, store)
    assert result is None


@_need_5_5
def test_role_permission_diff(store):
    scope = _scoped(ADMIN_LOGIN, "role_permission_diff", {"target_type": "role"})
    r = qh.dispatch2(
        "role_permission_diff", scope,
        {"target_type": "role", "target_role": "Admin User", "role_b": "Maker"}, store,
    )
    assert r["found"] is True
