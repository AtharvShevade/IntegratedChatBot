"""L-08: three small logic/safety fixes in the audit/user-list DB Q&A
handlers.

1. The account-lock threshold (`>= 5`) was hardcoded at two call sites in
   audit_handlers.py -- now one named constant (`FAILED_LOGIN_LOCK_THRESHOLD`).
2. "Last N days" was approximated as `entries[: N*10]` -- now filters by the
   entry's own parsed AuditDateTime against an actual cutoff date.
3. `int(u.get("FailedLoginCount", "0") or "0")` crashed on malformed data
   (e.g. a non-numeric string) -- now parsed safely via `_safe_int()`,
   degrading to a default instead of raising.
"""
from __future__ import annotations

from datetime import date, timedelta

from backend.db_qa.query_handlers import audit_handlers as ah
from backend.db_qa.query_handlers import user_handlers as uh


class _FakeStore:
    def __init__(self, users=None, audit_log=None):
        self._users = users or []
        self._audit_log = audit_log or []

    def users(self):
        return self._users

    def audit_log(self):
        return self._audit_log

    def enrich_log_entry(self, e):
        return e

    def enrich_user(self, u):
        return u

    def user_by_id(self, _id):
        return None

    def user_by_name(self, _name):
        return None

    def resolve_user(self, _name):
        return None


class TestNamedLockThreshold:
    def test_threshold_constant_is_five(self):
        assert ah.FAILED_LOGIN_LOCK_THRESHOLD == 5

    def test_exceeded_query_uses_the_constant(self):
        users = [
            {"UserId": "1", "FailedLoginCount": "5"},   # exactly at threshold -> locked
            {"UserId": "2", "FailedLoginCount": "4"},   # one below -> not locked
            {"UserId": "3", "FailedLoginCount": "10"},  # well above -> locked
        ]
        store = _FakeStore(users=users)
        result = ah.handle_security_events(
            {"target_type": "system"}, {"query_type": "failed_login_exceeded"}, store,
        )
        locked_ids = {u["UserId"] for u in result["records"]}
        assert locked_ids == {"1", "3"}

    def test_self_service_lock_status_uses_the_same_threshold(self):
        store = _FakeStore()
        store.user_by_id = lambda _id: {"UserId": "1", "FailedLoginCount": "5"}
        result = ah.handle_security_events(
            {"target_type": "self", "login_id": "u1", "user_id": "1"}, {}, store,
        )
        assert result["records"][0]["Locked"] is True


class TestDateBasedLastNDays:
    def test_only_entries_within_the_window_are_returned(self):
        today = date.today()
        recent = (today - timedelta(days=2)).strftime("%d-%b-%Y") + " 10:00:00 AM"
        old = (today - timedelta(days=40)).strftime("%d-%b-%Y") + " 10:00:00 AM"
        entries = [
            {"UserId": "u1", "AuditDateTime": recent},
            {"UserId": "u1", "AuditDateTime": old},
        ]
        store = _FakeStore(audit_log=entries)
        result = ah.handle_audit_history(
            {"target_type": "self", "login_id": "u1"}, {"days_n": "7"}, store,
        )
        dates = [e["AuditDateTime"] for e in result["records"]]
        assert recent in dates
        assert old not in dates

    def test_entry_exactly_at_the_boundary_is_included(self):
        today = date.today()
        boundary = (today - timedelta(days=7)).strftime("%d-%b-%Y") + " 09:00:00 AM"
        entries = [{"UserId": "u1", "AuditDateTime": boundary}]
        store = _FakeStore(audit_log=entries)
        result = ah.handle_audit_history(
            {"target_type": "self", "login_id": "u1"}, {"days_n": "7"}, store,
        )
        assert len(result["records"]) == 1

    def test_unparseable_date_is_excluded_not_crashed_on(self):
        entries = [{"UserId": "u1", "AuditDateTime": "not-a-real-date"}]
        store = _FakeStore(audit_log=entries)
        result = ah.handle_audit_history(
            {"target_type": "self", "login_id": "u1"}, {"days_n": "7"}, store,
        )
        assert result["records"] == []  # fails safe: excluded, not an exception

    def test_no_days_n_returns_everything_unfiltered(self):
        entries = [{"UserId": "u1", "AuditDateTime": "01-Jan-2020 01:00:00 AM"}]
        store = _FakeStore(audit_log=entries)
        result = ah.handle_audit_history(
            {"target_type": "self", "login_id": "u1"}, {}, store,
        )
        assert len(result["records"]) == 1

    def test_malformed_days_n_does_not_crash(self):
        entries = [{"UserId": "u1", "AuditDateTime": "01-Jan-2026 01:00:00 AM"}]
        store = _FakeStore(audit_log=entries)
        result = ah.handle_audit_history(
            {"target_type": "self", "login_id": "u1"}, {"days_n": "not-a-number"}, store,
        )
        # Must not raise; falls back to "no filter applied" for an
        # unparseable days_n rather than crashing the whole request.
        assert "records" in result


class TestSafeIntParsing:
    def test_safe_int_parses_valid_values(self):
        assert ah._safe_int("5") == 5
        assert ah._safe_int(5) == 5

    def test_safe_int_handles_none_and_empty(self):
        assert ah._safe_int(None) == 0
        assert ah._safe_int("") == 0

    def test_safe_int_handles_malformed_data_without_raising(self):
        assert ah._safe_int("not-a-number") == 0
        assert ah._safe_int("5.5abc") == 0

    def test_safe_int_custom_default(self):
        assert ah._safe_int("garbage", default=-1) == -1

    def test_failed_login_exceeded_does_not_crash_on_malformed_count(self):
        users = [
            {"UserId": "1", "FailedLoginCount": "not-a-number"},
            {"UserId": "2", "FailedLoginCount": "7"},
        ]
        store = _FakeStore(users=users)
        result = ah.handle_security_events(
            {"target_type": "system"}, {"query_type": "failed_login_exceeded"}, store,
        )
        # Must not raise; the malformed entry is simply not counted as locked.
        ids = {u["UserId"] for u in result["records"]}
        assert ids == {"2"}

    def test_user_handlers_failed_login_list_does_not_crash_on_malformed_count(self):
        users = [
            {"UserId": "1", "FailedLoginCount": "garbage", "LoginId": "a"},
            {"UserId": "2", "FailedLoginCount": "3", "LoginId": "b"},
        ]
        store = _FakeStore(users=users)
        result = uh.handle_user_list(
            {"target_type": "system"}, {"query_type": "failed_login"}, store,
        )
        ids = {u["UserId"] for u in result["records"]}
        assert ids == {"2"}  # the malformed one is correctly excluded (count treated as 0), not a crash
