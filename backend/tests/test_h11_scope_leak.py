"""Regression test for the H-11 fix (doc/CRITICAL_FIXES_LOG.md):
backend/db_qa/query_handlers/return_handlers.py's handle_nonxbrl_return_list
checked entities["target_department"] BEFORE scope["target_type"] == "self",
so a request whose classifier assigned target_type="self" but still
extracted a target_department entity (e.g. "show my non-XBRL returns for
Treasury department") returned Treasury's data -- unscoped, with no
authorization check -- labelled as if it were the caller's own.

This is purely a self-vs-department scope-check ordering fix in one
handler; the SQL agent (H-02) is untouched.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.db_qa.query_handlers.return_handlers import handle_nonxbrl_return_list


class _FakeStore:
    """Minimal duck-typed stand-in for XMLStore -- only the methods this
    handler actually calls."""

    def __init__(self, returns, depts, users):
        self._returns = returns
        self._depts = depts  # name -> dept dict
        self._users = users  # login_id -> user dict

    def non_xbrl_returns(self):
        return list(self._returns)

    def dept_by_name(self, name):
        return self._depts.get(name)

    def dept_by_id(self, dept_id):
        for d in self._depts.values():
            if d.get("DepartmentId") == dept_id:
                return d
        return None

    def user_by_id(self, user_id):
        for u in self._users.values():
            if u.get("UserId") == user_id:
                return u
        return None

    def user_by_name(self, login_id):
        return self._users.get(login_id)


# Two departments, each with one non-XBRL return only they can access.
_TREASURY = {"DepartmentId": "50", "NXForms": "T-100"}
_CALLERS_OWN_DEPT = {"DepartmentId": "10", "NXForms": "C-200"}
_RETURNS = [
    {"Id": "T-100", "ReturnId": "T-100", "Name": "Treasury Monthly Return"},
    {"Id": "C-200", "ReturnId": "C-200", "Name": "Caller Dept Monthly Return"},
]
_USERS = {
    "someuser": {"UserId": "1", "LoginId": "someuser", "DepartmentId": "10"},
}
_STORE = _FakeStore(_RETURNS, {"Treasury": _TREASURY, "Own": _CALLERS_OWN_DEPT}, _USERS)


def _self_scope():
    return {"target_type": "self", "login_id": "someuser", "user_id": "1", "is_admin": False}


class TestH11SelfScopeCannotLeakOtherDepartment:
    def test_self_scoped_request_naming_another_department_gets_own_data_only(self):
        """The core H-11 bug: a self-scoped caller mentioning 'Treasury' in
        the question text must still only see THEIR OWN department's
        returns, never Treasury's."""
        entities = {"target_department": "Treasury"}
        result = handle_nonxbrl_return_list(_self_scope(), entities, _STORE)

        names = [r["Name"] for r in result["records"]]
        assert "Treasury Monthly Return" not in names
        assert "Caller Dept Monthly Return" in names
        # The label must also say "mine", not attribute the (correct, own)
        # data to the named department it ignored.
        assert result["label"] == "My Non-XBRL Returns"

    def test_self_scoped_request_with_no_department_named_still_works(self):
        """Regression check: the ordinary self-scope case (no
        target_department at all) must be completely unaffected."""
        result = handle_nonxbrl_return_list(_self_scope(), {}, _STORE)
        names = [r["Name"] for r in result["records"]]
        assert names == ["Caller Dept Monthly Return"]
        assert result["label"] == "My Non-XBRL Returns"

    def test_non_self_scope_with_named_department_still_works(self):
        """The legitimate admin/"department" path (access_control.scope_query
        already required admin to reach target_type != "self") must still
        resolve the NAMED department correctly -- this fix must not disable
        that case."""
        scope = {"target_type": "department", "login_id": "adminuser", "user_id": "2", "is_admin": True}
        entities = {"target_department": "Treasury"}
        result = handle_nonxbrl_return_list(scope, entities, _STORE)
        names = [r["Name"] for r in result["records"]]
        assert names == ["Treasury Monthly Return"]
        assert result["label"] == "Non-XBRL Returns of Treasury"

    def test_non_self_scope_unknown_department_still_not_found(self):
        scope = {"target_type": "department", "login_id": "adminuser", "user_id": "2", "is_admin": True}
        result = handle_nonxbrl_return_list(scope, {"target_department": "NoSuchDept"}, _STORE)
        assert result["found"] is False
        assert "not found" in result["summary"].lower()
