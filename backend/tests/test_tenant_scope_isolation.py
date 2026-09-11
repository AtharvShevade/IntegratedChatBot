"""APP_VERSION=6.0 tenant-scope propagation.

Covers the fixes made after the 6.0 readiness audit:

  1. version_config.scoped_session_id -- identity under 5.5, tenant-prefixed
     under 6.0, so two tenants' users cannot collide in agent._session_context.
  2. importance_json / taxonomy_lookup / auth_service caches -- now keyed by
     (tenant_id, id) instead of a bare id, so two tenants sharing the same
     form_id/login_id never see each other's cached data.
  3. agent._start_error_enrichment_thread -- the background error-enrichment
     thread now runs inside a copied contextvars.Context, so it sees the
     SAME active repo root / tenant_id the request that spawned it had.
  4. /compare-execute and /explain-category now establish the same
     version_config.repo_scope /chat and /guided already use.

None of this touches the multilingual/i18n or STT systems, and every check
below asserts APP_VERSION=5.5 behavior is UNCHANGED (tenant_id always None
=> identical partitioning to before these fixes existed).
"""
from __future__ import annotations

import contextvars
import threading

import pytest
from fastapi.testclient import TestClient

from backend import main as main_module
from backend import version_config
from backend.tools import importance_json, taxonomy_lookup


@pytest.fixture
def client():
    return TestClient(main_module.app)


# ---------------------------------------------------------------------------
# 1. scoped_session_id
# ---------------------------------------------------------------------------

def test_scoped_session_id_is_identity_under_5_5(monkeypatch):
    """No active tenant (the 5.5 case, and 6.0 with no scope entered) must
    return the session_id byte-for-byte unchanged."""
    monkeypatch.setattr(version_config, "get_active_tenant_id", lambda: None)
    assert version_config.scoped_session_id("abc-123") == "abc-123"
    assert version_config.scoped_session_id(None) is None
    assert version_config.scoped_session_id("") == ""


def test_scoped_session_id_prefixes_under_6_0(monkeypatch):
    monkeypatch.setattr(version_config, "get_active_tenant_id", lambda: "TenantA")
    assert version_config.scoped_session_id("abc-123") == "TenantA:abc-123"


def test_scoped_session_id_isolates_two_tenants_sharing_a_raw_id(monkeypatch):
    """The exact risk found in App.jsx: sessionId falls back to the app's own
    `uid`, which is not namespaced per tenant. Two tenants' users with the
    SAME raw session_id must produce DIFFERENT scoped keys."""
    monkeypatch.setattr(version_config, "get_active_tenant_id", lambda: "TenantA")
    key_a = version_config.scoped_session_id("42")
    monkeypatch.setattr(version_config, "get_active_tenant_id", lambda: "TenantB")
    key_b = version_config.scoped_session_id("42")
    assert key_a != key_b


# ---------------------------------------------------------------------------
# 2a. importance_json cache isolation
# ---------------------------------------------------------------------------

def test_importance_json_cache_key_isolates_tenants(monkeypatch):
    monkeypatch.setattr(version_config, "get_active_tenant_id", lambda: "TenantA")
    key_a = importance_json._cache_key("1042")
    monkeypatch.setattr(version_config, "get_active_tenant_id", lambda: "TenantB")
    key_b = importance_json._cache_key("1042")
    assert key_a != key_b, "same form_id under two tenants must not collide"


def test_importance_json_cache_key_matches_bare_form_id_under_5_5(monkeypatch):
    """5.5 has no tenant, so the key must partition exactly as a bare
    form_id would -- i.e. it is constant across every 5.5 call."""
    monkeypatch.setattr(version_config, "get_active_tenant_id", lambda: None)
    assert importance_json._cache_key("1042") == importance_json._cache_key("1042")
    assert importance_json._cache_key("1042")[1] == "1042"


def test_importance_json_cache_actually_separates_two_tenants(monkeypatch):
    """End-to-end on the real _CACHE dict (not just the key function): write
    an entry for TenantA, confirm TenantB's lookup at the same form_id is a
    clean miss rather than TenantA's stale entry."""
    importance_json._CACHE.clear()
    monkeypatch.setattr(version_config, "get_active_tenant_id", lambda: "TenantA")
    importance_json._CACHE[importance_json._cache_key("1042")] = (123.0, "tenant-a-data")

    monkeypatch.setattr(version_config, "get_active_tenant_id", lambda: "TenantB")
    assert importance_json._CACHE.get(importance_json._cache_key("1042")) is None

    monkeypatch.setattr(version_config, "get_active_tenant_id", lambda: "TenantA")
    assert importance_json._CACHE.get(importance_json._cache_key("1042")) == (123.0, "tenant-a-data")
    importance_json._CACHE.clear()


# ---------------------------------------------------------------------------
# 2b. taxonomy_lookup cache isolation
# ---------------------------------------------------------------------------

def test_taxonomy_lookup_cache_key_isolates_tenants(monkeypatch):
    monkeypatch.setattr(version_config, "get_active_tenant_id", lambda: "TenantA")
    key_a = taxonomy_lookup._cache_key("1042")
    monkeypatch.setattr(version_config, "get_active_tenant_id", lambda: "TenantB")
    key_b = taxonomy_lookup._cache_key("1042")
    assert key_a != key_b


def test_taxonomy_lookup_cache_key_matches_bare_form_id_under_5_5(monkeypatch):
    monkeypatch.setattr(version_config, "get_active_tenant_id", lambda: None)
    assert taxonomy_lookup._cache_key("1042") == taxonomy_lookup._cache_key(" 1042 ")


def test_taxonomy_lookup_cache_actually_separates_two_tenants(monkeypatch):
    taxonomy_lookup._TAXONOMY_CACHE.clear()
    monkeypatch.setattr(version_config, "get_active_tenant_id", lambda: "TenantA")
    taxonomy_lookup._TAXONOMY_CACHE[taxonomy_lookup._cache_key("1042")] = {"path": "A"}

    monkeypatch.setattr(version_config, "get_active_tenant_id", lambda: "TenantB")
    assert taxonomy_lookup._TAXONOMY_CACHE.get(taxonomy_lookup._cache_key("1042")) is None
    taxonomy_lookup._TAXONOMY_CACHE.clear()


# ---------------------------------------------------------------------------
# 2c. auth_service cache isolation
# ---------------------------------------------------------------------------

def test_auth_service_cache_key_isolates_tenants(monkeypatch):
    from backend.services import auth_service
    monkeypatch.setattr(version_config, "get_active_tenant_id", lambda: "TenantA")
    key_a = auth_service._cache_key("user1")
    monkeypatch.setattr(version_config, "get_active_tenant_id", lambda: "TenantB")
    key_b = auth_service._cache_key("user1")
    assert key_a != key_b


def test_auth_service_cache_key_matches_bare_login_id_under_5_5(monkeypatch):
    from backend.services import auth_service
    monkeypatch.setattr(version_config, "get_active_tenant_id", lambda: None)
    assert auth_service._cache_key("user1") == (None, "user1")


def test_auth_service_get_allowed_form_ids_does_not_leak_across_tenants(monkeypatch):
    """Same login_id, two tenants, two different XML-derived results --
    confirms the fix at the actual public API, not just the key function."""
    from backend.services import auth_service

    auth_service._cache.clear()
    monkeypatch.setattr(auth_service, "AUTHORIZATION_ENABLED", True)
    monkeypatch.setattr(auth_service, "_auth_xml_mtime", lambda: 1.0)

    calls = []

    def _fake_lookup(login_id, forms_attr=None):
        calls.append(version_config.get_active_tenant_id())
        return {"tenant-a-form"} if version_config.get_active_tenant_id() == "TenantA" else {"tenant-b-form"}

    monkeypatch.setattr(auth_service, "_lookup", _fake_lookup)

    monkeypatch.setattr(version_config, "get_active_tenant_id", lambda: "TenantA")
    result_a = auth_service.get_allowed_form_ids("shared_user")
    monkeypatch.setattr(version_config, "get_active_tenant_id", lambda: "TenantB")
    result_b = auth_service.get_allowed_form_ids("shared_user")

    assert result_a == {"tenant-a-form"}
    assert result_b == {"tenant-b-form"}, "TenantB got TenantA's cached permission set"
    assert len(calls) == 2, "both tenants must have triggered a real lookup, no false cache hit"
    auth_service._cache.clear()


# ---------------------------------------------------------------------------
# 3. Background error-enrichment thread inherits the calling request's context
# ---------------------------------------------------------------------------

def test_background_thread_sees_the_active_tenant_context():
    """The core of the fix: threading.Thread does not normally inherit
    contextvars. _start_error_enrichment_thread must run its target through
    a copied Context so the background job sees the SAME active repo root /
    tenant_id the request that spawned it had."""
    from backend.agent import _start_error_enrichment_thread

    seen: dict = {}

    def _probe(job_id, form_id, row, dl, code):
        seen["tenant_id"] = version_config.get_active_tenant_id()
        seen["root"] = version_config.get_active_root()

    import backend.agent as agent_module
    original = agent_module._run_error_enrichment_async
    agent_module._run_error_enrichment_async = _probe
    try:
        with version_config.repo_scope(r"D:\Repo6\Repo6\TenantA", tenant_id="TenantA"):
            done = threading.Event()

            def _start_and_signal():
                _start_error_enrichment_thread("job1", "1042", {}, {}, 200)
                done.set()

            # _start_error_enrichment_thread itself just launches a thread and
            # returns immediately; call it directly (still inside the scope)
            # and wait for the spawned thread to finish.
            _start_error_enrichment_thread("job1", "1042", {}, {}, 200)
        # Give the daemon thread a moment to run; it was started while the
        # scope above was active, which is what must be captured.
        for _ in range(100):
            if "tenant_id" in seen:
                break
            threading.Event().wait(0.01)
    finally:
        agent_module._run_error_enrichment_async = original

    assert seen.get("tenant_id") == "TenantA", (
        "background thread did not see the spawning request's tenant context"
    )
    assert seen.get("root") == r"D:\Repo6\Repo6\TenantA"


def test_background_thread_under_5_5_sees_no_override():
    """5.5 has no repo_scope override active (root=None always) -- the
    background thread must see that unchanged, i.e. BASE_REPO_PATH via
    get_active_root(), not some stale value from a previous test."""
    from backend.agent import _start_error_enrichment_thread
    from backend import config as backend_config

    seen: dict = {}

    def _probe(job_id, form_id, row, dl, code):
        seen["root"] = version_config.get_active_root()

    import backend.agent as agent_module
    original = agent_module._run_error_enrichment_async
    agent_module._run_error_enrichment_async = _probe
    try:
        with version_config.repo_scope(None):
            _start_error_enrichment_thread("job2", "1042", {}, {}, 200)
        for _ in range(100):
            if "root" in seen:
                break
            threading.Event().wait(0.01)
    finally:
        agent_module._run_error_enrichment_async = original

    assert seen.get("root") == backend_config.BASE_REPO_PATH


# ---------------------------------------------------------------------------
# 4. /compare-execute and /explain-category establish repo scope
# ---------------------------------------------------------------------------

def _spy_make_repo_scope(monkeypatch):
    calls: list[tuple] = []
    real = main_module._make_repo_scope

    def _spy(tenant_id, domain, jwt):
        calls.append((tenant_id, domain, jwt))
        return real(tenant_id, domain, jwt)

    monkeypatch.setattr(main_module, "_make_repo_scope", _spy)
    return calls


def test_compare_execute_establishes_repo_scope(client, monkeypatch):
    calls = _spy_make_repo_scope(monkeypatch)

    async def _execute(*args, **kwargs):
        return {
            "intent": "compare_reports", "report_name": "RAQ(Monthly)",
            "response_text": "Variance Analysis — RAQ(Monthly)\nComparing: A vs B",
            "result_type": "variance_table", "options": [],
        }

    monkeypatch.setattr("backend.agent.execute_comparison", _execute, raising=False)

    resp = client.post("/compare-execute", json={
        "session_id": "s1", "instance_a": 0, "instance_b": 1,
        "tenant_id": "TenantA", "domain": None, "jwt": "tok123",
    })
    assert resp.status_code == 200
    assert calls == [("TenantA", None, "tok123")]


def test_explain_category_establishes_repo_scope(client, monkeypatch):
    calls = _spy_make_repo_scope(monkeypatch)

    async def _explain(*args, **kwargs):
        return {
            "intent": "get_status", "response_text": "", "options": [],
            "error_details": [],
        }

    monkeypatch.setattr(
        "backend.main.explain_category_for_report", _explain, raising=False,
    )

    resp = client.post("/explain-category", json={
        "error_file_path": r"D:\Repo6\Repo6\TenantA\Instance\1042\x.html",
        "category": "formula_error",
        "tenant_id": "TenantA", "domain": None, "jwt": "tok123",
    })
    assert resp.status_code == 200
    assert calls == [("TenantA", None, "tok123")]


def test_compare_request_model_accepts_tenant_fields():
    from backend.models import CompareRequest
    req = CompareRequest(
        session_id="s1", instance_a=0, instance_b=1,
        tenant_id="TenantA", domain="example.com", jwt="tok",
    )
    assert req.tenant_id == "TenantA"
    assert req.domain == "example.com"
    assert req.jwt == "tok"


def test_explain_category_request_model_accepts_tenant_fields():
    from backend.models import ExplainCategoryRequest
    req = ExplainCategoryRequest(
        error_file_path="x.html", category="formula_error",
        tenant_id="TenantA", domain="example.com", jwt="tok",
    )
    assert req.tenant_id == "TenantA"
    assert req.domain == "example.com"
    assert req.jwt == "tok"


def test_compare_request_still_works_with_no_tenant_fields_at_all():
    """5.5 callers (and the existing test suite) never send these fields --
    they must stay fully optional."""
    from backend.models import CompareRequest, ExplainCategoryRequest
    c = CompareRequest(session_id="s1", instance_a=0, instance_b=1)
    assert c.tenant_id is None and c.domain is None and c.jwt is None
    e = ExplainCategoryRequest(error_file_path="x.html", category="formula_error")
    assert e.tenant_id is None and e.domain is None and e.jwt is None
