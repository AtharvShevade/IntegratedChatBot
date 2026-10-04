"""Regression tests for the H-07 fix (doc/CRITICAL_FIXES_LOG.md):

  - OpenAPI docs (/docs, /redoc, /openapi.json) are disabled by default,
    since they document every request field including security-sensitive
    ones (role_id, tenant_id, error_file_path, ...).
  - The Ollama proxy URL and the Whisper STT base URL no longer default to
    a public IP over plain HTTP when unset -- a deployment that forgets to
    set them now gets an empty/broken value it can act on, instead of
    silently sending user data to a public endpoint nobody chose.

host="127.0.0.1" in dev_server.py/service_server.py is a startup-argument
change (not exercised by pytest, which never calls uvicorn.run()) and is
covered by manual/deployment verification instead, per the fixes log.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend import main as main_module


@pytest.fixture
def client():
    return TestClient(main_module.app)


class TestOpenAPIDocsDisabledByDefault:
    def test_app_has_docs_disabled_in_this_test_environment(self):
        """This repo's test environment does not set ENABLE_API_DOCS=true,
        so the already-constructed app object must have every docs route
        turned off -- confirms the default this ships with."""
        assert main_module.app.docs_url is None
        assert main_module.app.redoc_url is None
        assert main_module.app.openapi_url is None

    def test_docs_endpoint_returns_404(self, client):
        resp = client.get("/docs")
        assert resp.status_code == 404

    def test_redoc_endpoint_returns_404(self, client):
        resp = client.get("/redoc")
        assert resp.status_code == 404

    def test_openapi_schema_endpoint_returns_404(self, client):
        resp = client.get("/openapi.json")
        assert resp.status_code == 404

    def test_health_endpoint_still_works(self, client):
        """Sanity check: disabling docs must not disable ordinary routes."""
        resp = client.get("/health")
        assert resp.status_code == 200


class TestNoPublicIpFallbackDefaults:
    def test_ollama_url_has_no_hardcoded_public_ip_default(self, monkeypatch):
        monkeypatch.delenv("OLLAMA_URL", raising=False)
        import importlib
        from backend.sql_agent.sqlcore import config as sql_config
        importlib.reload(sql_config)
        try:
            assert sql_config.OLLAMA_URL == ""
            assert "3.109.51.228" not in sql_config.OLLAMA_URL
        finally:
            importlib.reload(sql_config)  # restore real .env-derived value for later tests

    def test_stt_base_url_has_no_hardcoded_public_ip_default(self, monkeypatch):
        monkeypatch.delenv("STT_BASE_URL", raising=False)
        from backend.stt import config as stt_config
        assert stt_config.base_url() == ""
        assert "3.109.51.228" not in stt_config.base_url()

    def test_stt_base_url_still_honours_an_explicitly_set_value(self, monkeypatch):
        monkeypatch.setenv("STT_BASE_URL", "http://example-internal-host/whisper-api")
        from backend.stt import config as stt_config
        assert stt_config.base_url() == "http://example-internal-host/whisper-api"
