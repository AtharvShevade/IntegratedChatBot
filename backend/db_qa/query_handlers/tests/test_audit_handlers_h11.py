"""H-11 regression tests: a non-admin, department-scoped caller must not see
cross-validation / audit-trail entries for returns outside their department's
allowed_form_ids -- neither when they name a specific (out-of-scope) return,
nor when they ask for the log with no return named at all (the "self-scoped
query leaks other departments' data" case).

Uses a mocked XMLStore (no real data tree dependency) so this test runs
everywhere, unlike the existing _need_5_5-gated handler tests.
"""
from __future__ import annotations

from unittest.mock import MagicMock

from backend.db_qa.query_handlers import audit_handlers as ah


def _make_store(cross_val_entries, returns, non_xbrl_returns=()):
    store = MagicMock()
    store.cross_validation_log.return_value = cross_val_entries
    store.enrich_cross_val_entry.side_effect = lambda e: dict(e)
    store.enrich_log_entry.side_effect = lambda e: dict(e)
    store.audit_log.return_value = []
    store.returns.return_value = list(returns)
    store.non_xbrl_returns.return_value = list(non_xbrl_returns)

    def _resolve_return(name):
        for r in list(returns) + list(non_xbrl_returns):
            if r.get("Name", "").lower() == name.lower():
                return r
        return None

    store.resolve_return.side_effect = _resolve_return
    return store


_RETURN_A = {"Name": "ReturnA", "Id": "1001", "ReturnId": "1001"}
_RETURN_B = {"Name": "ReturnB", "Id": "2002", "ReturnId": "2002"}

_CROSS_VAL = [
    {"FirstReportName": "ReturnA", "SecondReportName": "ReturnA", "Status": "Fail", "GeneratedBy": "u1"},
    {"FirstReportName": "ReturnB", "SecondReportName": "ReturnB", "Status": "Fail", "GeneratedBy": "u2"},
]


class TestHandleLogQueryCrossValidationScoping:
    def test_admin_sees_all_departments(self):
        store = _make_store(_CROSS_VAL, [_RETURN_A, _RETURN_B])
        scope = {"target_type": "self", "login_id": "admin1", "user_id": None,
                 "is_admin": True, "allowed_form_ids": None}
        result = ah.handle_log_query(scope, {"log_type": "cross_validation"}, store)
        assert result["meta"]["count"] == 2

    def test_self_scoped_non_admin_only_sees_own_department(self, monkeypatch):
        store = _make_store(_CROSS_VAL, [_RETURN_A, _RETURN_B])
        monkeypatch.setattr(
            "backend.db_qa.access_control.resolve_allowed_form_ids",
            lambda login_id: {"1001"},
        )
        scope = {"target_type": "self", "login_id": "dept_a_user", "user_id": None,
                 "is_admin": False, "allowed_form_ids": None}
        result = ah.handle_log_query(scope, {"log_type": "cross_validation"}, store)
        assert result["meta"]["count"] == 1
        assert result["records"][0]["FirstReportName"] == "ReturnA"

    def test_named_out_of_scope_return_is_denied(self):
        store = _make_store(_CROSS_VAL, [_RETURN_A, _RETURN_B])
        scope = {"target_type": "return", "login_id": "dept_a_user", "user_id": None,
                 "is_admin": False, "allowed_form_ids": {"1001"}}
        result = ah.handle_log_query(scope, {"target_return": "ReturnB"}, store)
        assert result["intent"] == "access_denied"
        assert result["found"] is False

    def test_named_in_scope_return_is_allowed(self):
        store = _make_store(_CROSS_VAL, [_RETURN_A, _RETURN_B])
        scope = {"target_type": "return", "login_id": "dept_a_user", "user_id": None,
                 "is_admin": False, "allowed_form_ids": {"1001"}}
        result = ah.handle_log_query(scope, {"target_return": "ReturnA"}, store)
        assert result["found"] is True
        assert all(e["FirstReportName"] == "ReturnA" for e in result["records"])

    def test_authorization_disabled_bypass_still_shows_all(self, monkeypatch):
        store = _make_store(_CROSS_VAL, [_RETURN_A, _RETURN_B])
        monkeypatch.setattr(
            "backend.db_qa.access_control.resolve_allowed_form_ids",
            lambda login_id: None,
        )
        scope = {"target_type": "self", "login_id": "any_user", "user_id": None,
                 "is_admin": False, "allowed_form_ids": None}
        result = ah.handle_log_query(scope, {"log_type": "cross_validation"}, store)
        assert result["meta"]["count"] == 2


class TestHandleAuditEntityTrailReturnScoping:
    def _audit_log(self):
        return [
            {"UserId": "u1", "AuditDateTime": "01-Jan-2026 10:00:00 AM", "Remark": "Submitted ReturnA"},
            {"UserId": "u2", "AuditDateTime": "02-Jan-2026 10:00:00 AM", "Remark": "Submitted ReturnB"},
        ]

    def test_named_out_of_scope_return_is_denied(self):
        store = _make_store([], [_RETURN_A, _RETURN_B])
        store.audit_log.return_value = self._audit_log()
        scope = {"target_type": "return", "login_id": "dept_a_user", "user_id": None,
                 "is_admin": False, "allowed_form_ids": {"1001"}}
        result = ah.handle_audit_entity_trail(scope, {"target_return": "ReturnB"}, store)
        assert result["intent"] == "access_denied"

    def test_named_in_scope_return_is_allowed(self):
        store = _make_store([], [_RETURN_A, _RETURN_B])
        store.audit_log.return_value = self._audit_log()
        scope = {"target_type": "return", "login_id": "dept_a_user", "user_id": None,
                 "is_admin": False, "allowed_form_ids": {"1001"}}
        result = ah.handle_audit_entity_trail(scope, {"target_return": "ReturnA"}, store)
        assert result["found"] is True
        assert all("ReturnA" in e["Remark"] for e in result["records"])
