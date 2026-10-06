"""M-05 / M-11: /compare-summary and /stop previously had no authentication
at all -- any caller could trigger LLM-narrative generation for arbitrary
rows, or cancel any other session's in-flight request, just by guessing/
observing a request_id.

Both now share main.py's _caller_is_authenticated() -- the same
REQUIRE_AUTH/AUTHORIZATION_ENABLED fail-closed contract already established
by agent/router.py's decide() and main.py's _caller_may_access_form() (used
by /download-file, /reports, /status-errors/{job_id}). No new authorization
system is introduced.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend import main as main_mod


@pytest.fixture
def client():
    return TestClient(main_mod.app)


class TestCallerIsAuthenticatedHelper:
    def test_no_login_id_denied_when_require_auth_true(self, monkeypatch):
        monkeypatch.setenv("REQUIRE_AUTH", "true")
        monkeypatch.setattr("backend.services.auth_service.AUTHORIZATION_ENABLED", True)
        assert main_mod._caller_is_authenticated(None) is False

    def test_no_login_id_allowed_when_require_auth_false(self, monkeypatch):
        monkeypatch.setenv("REQUIRE_AUTH", "false")
        assert main_mod._caller_is_authenticated(None) is True

    def test_unresolvable_login_id_denied(self, monkeypatch):
        monkeypatch.setattr("backend.services.auth_service.AUTHORIZATION_ENABLED", True)
        monkeypatch.setattr("backend.services.auth_service.get_allowed_form_ids", lambda login_id: None)
        assert main_mod._caller_is_authenticated("ghost-user") is False

    def test_resolvable_login_id_allowed(self, monkeypatch):
        monkeypatch.setattr("backend.services.auth_service.AUTHORIZATION_ENABLED", True)
        monkeypatch.setattr("backend.services.auth_service.get_allowed_form_ids", lambda login_id: {"1001"})
        assert main_mod._caller_is_authenticated("real-user") is True

    def test_authorization_disabled_bypasses_resolution(self, monkeypatch):
        monkeypatch.setattr("backend.services.auth_service.AUTHORIZATION_ENABLED", False)
        assert main_mod._caller_is_authenticated("anyone") is True


class TestCompareSummaryAuth:
    def test_denied_without_login_id_when_require_auth_true(self, client, monkeypatch):
        monkeypatch.setenv("REQUIRE_AUTH", "true")
        monkeypatch.setattr("backend.services.auth_service.AUTHORIZATION_ENABLED", True)
        res = client.post("/compare-summary", json={"rows": [], "report_name": "R"})
        assert res.status_code == 403

    def test_allowed_with_resolvable_login_id(self, client, monkeypatch):
        monkeypatch.setenv("REQUIRE_AUTH", "true")
        monkeypatch.setattr("backend.services.auth_service.AUTHORIZATION_ENABLED", True)
        monkeypatch.setattr("backend.services.auth_service.get_allowed_form_ids", lambda login_id: {"1001"})
        res = client.post("/compare-summary", json={"rows": [], "report_name": "R", "login_id": "real-user"})
        assert res.status_code == 200

    def test_allowed_without_login_id_when_require_auth_false(self, client, monkeypatch):
        monkeypatch.setenv("REQUIRE_AUTH", "false")
        res = client.post("/compare-summary", json={"rows": [], "report_name": "R"})
        assert res.status_code == 200


class TestCompareSummaryTenantScoping:
    """Regression: /compare-summary never entered version_config.repo_scope
    before this fix, so _caller_is_authenticated() resolved every login_id
    against the default/unscoped repo root -- a real APP_VERSION=6.0
    login_id could never be found (each tenant's users live under their own
    D:\\Repo6.0\\<TenantId>\\DataBase\\User.xml), so the endpoint 403'd for
    every 6.0 caller and the frontend surfaced this as "AI analysis is
    unavailable" with no visible cause. CompareSummaryRequest now carries
    tenant_id/domain/jwt (same fields ExplainCategoryRequest already has)
    and the endpoint enters repo_scope with them before the auth check.

    get_allowed_form_ids is faked here to depend on the ACTIVE tenant id --
    exactly the real-world shape (each tenant resolves against its own
    User.xml) -- so a pass here proves repo_scope is genuinely active by
    the time the auth check runs, not just that some login_id resolves.
    """

    @staticmethod
    def _tenant_scoped_lookup(login_id):
        from backend import version_config
        if version_config.get_active_tenant_id() == "1001":
            return {"4108"}
        return None

    def test_denied_without_tenant_id_for_a_tenant_scoped_login(self, client, monkeypatch):
        monkeypatch.setenv("REQUIRE_AUTH", "true")
        monkeypatch.setattr("backend.services.auth_service.AUTHORIZATION_ENABLED", True)
        monkeypatch.setattr(
            "backend.services.auth_service.get_allowed_form_ids",
            self._tenant_scoped_lookup,
        )
        res = client.post("/compare-summary", json={
            "rows": [], "report_name": "R", "login_id": "real-user",
            # tenant_id deliberately omitted -- reproduces the bug exactly.
        })
        assert res.status_code == 403

    def test_allowed_with_matching_tenant_id(self, client, monkeypatch):
        monkeypatch.setenv("REQUIRE_AUTH", "true")
        monkeypatch.setattr("backend.services.auth_service.AUTHORIZATION_ENABLED", True)
        monkeypatch.setattr(
            "backend.services.auth_service.get_allowed_form_ids",
            self._tenant_scoped_lookup,
        )
        res = client.post("/compare-summary", json={
            "rows": [], "report_name": "R", "login_id": "real-user",
            "tenant_id": "1001",
        })
        assert res.status_code == 200

    def test_denied_with_the_wrong_tenant_id(self, client, monkeypatch):
        monkeypatch.setenv("REQUIRE_AUTH", "true")
        monkeypatch.setattr("backend.services.auth_service.AUTHORIZATION_ENABLED", True)
        monkeypatch.setattr(
            "backend.services.auth_service.get_allowed_form_ids",
            self._tenant_scoped_lookup,
        )
        res = client.post("/compare-summary", json={
            "rows": [], "report_name": "R", "login_id": "real-user",
            "tenant_id": "9999",
        })
        assert res.status_code == 403

    def test_5_5_unaffected_tenant_id_absent_is_a_no_op(self, client, monkeypatch):
        """5.5 never sends tenant_id -- repo_scope(root=None, ...) must stay
        a true no-op, exactly as it already is for every other endpoint."""
        monkeypatch.setenv("REQUIRE_AUTH", "true")
        monkeypatch.setattr("backend.services.auth_service.AUTHORIZATION_ENABLED", True)
        monkeypatch.setattr(
            "backend.services.auth_service.get_allowed_form_ids",
            lambda login_id: {"2041"},  # ordinary 5.5-style resolution, tenant-independent
        )
        res = client.post("/compare-summary", json={
            "rows": [], "report_name": "R", "login_id": "real-user",
        })
        assert res.status_code == 200


class TestStopAuth:
    def test_denied_without_login_id_when_require_auth_true(self, client, monkeypatch):
        monkeypatch.setenv("REQUIRE_AUTH", "true")
        monkeypatch.setattr("backend.services.auth_service.AUTHORIZATION_ENABLED", True)
        res = client.post("/stop", json={"request_id": "some-id"})
        assert res.status_code == 403

    def test_allowed_with_resolvable_login_id(self, client, monkeypatch):
        monkeypatch.setenv("REQUIRE_AUTH", "true")
        monkeypatch.setattr("backend.services.auth_service.AUTHORIZATION_ENABLED", True)
        monkeypatch.setattr("backend.services.auth_service.get_allowed_form_ids", lambda login_id: {"1001"})
        res = client.post("/stop", json={"request_id": "some-id", "login_id": "real-user"})
        assert res.status_code == 200
        assert res.json() == {"stopped": False}  # unknown request_id -> no-op, not an auth failure

    def test_allowed_without_login_id_when_require_auth_false(self, client, monkeypatch):
        monkeypatch.setenv("REQUIRE_AUTH", "false")
        res = client.post("/stop", json={"request_id": "some-id"})
        assert res.status_code == 200
