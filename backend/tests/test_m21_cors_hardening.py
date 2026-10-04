"""M-21: CORS previously allowed any method/header via wildcards
(``allow_methods=["*"]``, ``allow_headers=["*"]``) and never checked whether a
configured, credentialed origin was actually served over https -- a
credentialed CORS origin over plain http is a live MITM exposure for any real
(non-localhost) host.

``backend/main.py`` now: filters ``CORS_ORIGINS`` through
``_is_safe_credentialed_origin`` (https, or localhost/127.0.0.1 for local
dev -- everything else is dropped with a warning log, never silently
allowed); sets explicit ``allow_methods=["GET", "POST", "OPTIONS"]``; sets
explicit ``allow_headers=["Content-Type", "Authorization"]`` instead of "*".
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from backend import main as main_module

client = TestClient(main_module.app)


class TestOriginFiltering:
    def test_https_origin_is_always_safe(self):
        assert main_module._is_safe_credentialed_origin("https://idealtest.irisregtech.com")
        assert main_module._is_safe_credentialed_origin("https://3.109.51.228")

    def test_plain_http_localhost_is_safe_for_dev(self):
        assert main_module._is_safe_credentialed_origin("http://localhost:3000")
        assert main_module._is_safe_credentialed_origin("http://127.0.0.1:3000")

    def test_plain_http_real_host_is_rejected(self):
        assert not main_module._is_safe_credentialed_origin("http://3.109.51.228")
        assert not main_module._is_safe_credentialed_origin("http://example.com")

    def test_configured_origins_list_contains_no_unsafe_entries(self):
        # Whatever CORS_ORIGINS the running .env configures, every origin the
        # middleware actually allows must pass the safety filter.
        for origin in main_module._cors_origins:
            assert main_module._is_safe_credentialed_origin(origin), origin


class TestMiddlewareIsExactNotWildcard:
    def test_no_wildcard_origin_configured(self):
        assert "*" not in main_module._cors_origins

    def test_methods_are_explicit_not_wildcard(self):
        cors_mw = next(
            m for m in main_module.app.user_middleware
            if m.cls.__name__ == "CORSMiddleware"
        )
        assert cors_mw.kwargs["allow_methods"] == ["GET", "POST", "OPTIONS"]
        assert "*" not in cors_mw.kwargs["allow_methods"]

    def test_headers_are_explicit_not_wildcard(self):
        cors_mw = next(
            m for m in main_module.app.user_middleware
            if m.cls.__name__ == "CORSMiddleware"
        )
        assert "*" not in cors_mw.kwargs["allow_headers"]
        assert "Content-Type" in cors_mw.kwargs["allow_headers"]


class TestPreflightBehavior:
    def test_allowed_origin_preflight_is_accepted(self):
        if not main_module._cors_origins:
            return  # nothing configured in this environment -- nothing to assert
        allowed = main_module._cors_origins[0]
        resp = client.options(
            "/chat",
            headers={
                "Origin": allowed,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        assert resp.headers.get("access-control-allow-origin") == allowed

    def test_disallowed_origin_preflight_gets_no_cors_headers(self):
        resp = client.options(
            "/chat",
            headers={
                "Origin": "https://evil.example.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        assert "access-control-allow-origin" not in {k.lower() for k in resp.headers.keys()}

    def test_credentialed_requests_are_enabled(self):
        cors_mw = next(
            m for m in main_module.app.user_middleware
            if m.cls.__name__ == "CORSMiddleware"
        )
        assert cors_mw.kwargs["allow_credentials"] is True
