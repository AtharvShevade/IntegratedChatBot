"""Regression tests for the H-04 fixes (doc/CRITICAL_FIXES_LOG.md) that are
independent of the session_id-caching question (that part is still pending
your decision -- see the report handed back separately):

  1. The static DOTNET_SESSION_COOKIE fallback is ignored unless an operator
     explicitly opts in via ALLOW_STATIC_DOTNET_COOKIE=true.
  2. Outbound calls to .NET verify TLS by default (verify=True / a configured
     CA bundle), never verify=False.
  3. A redirect response is only followed when its Location host/port matches
     the configured .NET host -- a redirect to a different host is refused.
  4. No cookie/JWT value (not even a truncated prefix) is ever logged.

None of these touch .NET's own authentication, the cookie/JWT names, the
request contract, or session_id handling -- this file only exercises
backend/tools/instance_generator.py's outbound HTTP behavior, with httpx
mocked out (no real network calls).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import backend.tools.instance_generator as ig


class _FakeResponse:
    def __init__(self, status_code, headers=None, json_data=None, text=""):
        self.status_code = status_code
        self.headers = headers or {}
        self._json_data = json_data
        self.text = text

    def json(self):
        if self._json_data is None:
            raise ValueError("no json")
        return self._json_data


class _FakeAsyncClient:
    """Records every constructor call's kwargs and every .post() call, and
    returns responses from a queue -- lets a test script exactly what the
    (mocked) network would return without touching httpx for real."""

    instances: list["_FakeAsyncClient"] = []

    def __init__(self, *args, **kwargs):
        self.init_kwargs = kwargs
        self.post_calls: list[dict] = []
        _FakeAsyncClient.instances.append(self)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, url, **kwargs):
        self.post_calls.append({"url": url, **kwargs})
        return _RESPONSE_QUEUE.pop(0)


_RESPONSE_QUEUE: list[_FakeResponse] = []


@pytest.fixture(autouse=True)
def _patch_httpx(monkeypatch):
    _FakeAsyncClient.instances = []
    _RESPONSE_QUEUE.clear()
    monkeypatch.setattr(ig.httpx, "AsyncClient", _FakeAsyncClient)
    yield
    _RESPONSE_QUEUE.clear()


def _queue(*responses):
    _RESPONSE_QUEUE.extend(responses)


class TestStaticCookieFallbackDisabledByDefault:
    def test_static_cookie_not_used_when_flag_unset(self, monkeypatch):
        monkeypatch.setattr(ig, "_DOTNET_SESSION_COOKIE", "shared-service-account-cookie")
        monkeypatch.setattr(ig, "_ALLOW_STATIC_DOTNET_COOKIE", False)
        _queue(_FakeResponse(200, json_data=[True, "01-Jan-2026", "OK", True, "Submitted"]))

        import asyncio
        asyncio.run(ig.call_generate_api("4046", "01-Jan-2026", asp_session=None))

        sent_cookies = _FakeAsyncClient.instances[0].post_calls[0]["cookies"]
        assert sent_cookies == {}

    def test_static_cookie_used_when_flag_explicitly_enabled(self, monkeypatch):
        monkeypatch.setattr(ig, "_DOTNET_SESSION_COOKIE", "shared-service-account-cookie")
        monkeypatch.setattr(ig, "_ALLOW_STATIC_DOTNET_COOKIE", True)
        _queue(_FakeResponse(200, json_data=[True, "01-Jan-2026", "OK", True, "Submitted"]))

        import asyncio
        asyncio.run(ig.call_generate_api("4046", "01-Jan-2026", asp_session=None))

        sent_cookies = _FakeAsyncClient.instances[0].post_calls[0]["cookies"]
        assert sent_cookies == {".AspNetCore.Session": "shared-service-account-cookie"}

    def test_forwarded_asp_session_always_used_regardless_of_flag(self, monkeypatch):
        """Sanity/regression check: a genuinely forwarded browser cookie must
        keep working exactly as before, independent of the new flag."""
        monkeypatch.setattr(ig, "_ALLOW_STATIC_DOTNET_COOKIE", False)
        _queue(_FakeResponse(200, json_data=[True, "01-Jan-2026", "OK", True, "Submitted"]))

        import asyncio
        asyncio.run(ig.call_generate_api("4046", "01-Jan-2026", asp_session="real-browser-cookie"))

        sent_cookies = _FakeAsyncClient.instances[0].post_calls[0]["cookies"]
        assert sent_cookies == {".AspNetCore.Session": "real-browser-cookie"}


class TestTlsVerificationEnabledByDefault:
    def test_call_generate_api_verifies_tls(self, monkeypatch):
        monkeypatch.setattr(ig, "_TLS_VERIFY", True)
        _queue(_FakeResponse(200, json_data=[True, "01-Jan-2026", "OK", True, "Submitted"]))

        import asyncio
        asyncio.run(ig.call_generate_api("4046", "01-Jan-2026", asp_session="cookie"))

        assert _FakeAsyncClient.instances[0].init_kwargs["verify"] is True

    def test_call_generate_api_v6_verifies_tls(self, monkeypatch):
        monkeypatch.setattr(ig, "_TLS_VERIFY", True)
        _queue(_FakeResponse(200, json_data={"data": 123}))

        import asyncio
        asyncio.run(ig.call_generate_api_v6("4046", "01-Jan-2026", tenant_id="T1", jwt="tok"))

        assert _FakeAsyncClient.instances[0].init_kwargs["verify"] is True

    def test_ca_bundle_path_used_when_configured(self, monkeypatch):
        monkeypatch.setattr(ig, "_TLS_VERIFY", "/etc/ssl/internal-ca.pem")
        _queue(_FakeResponse(200, json_data=[True, "01-Jan-2026", "OK", True, "Submitted"]))

        import asyncio
        asyncio.run(ig.call_generate_api("4046", "01-Jan-2026", asp_session="cookie"))

        assert _FakeAsyncClient.instances[0].init_kwargs["verify"] == "/etc/ssl/internal-ca.pem"


class TestRedirectHostValidation:
    def test_same_host_https_upgrade_redirect_is_followed(self, monkeypatch):
        """Regression check: the legitimate HTTP->HTTPS upgrade case (same
        host, scheme changes) must still work exactly as before."""
        monkeypatch.setattr(ig, "_DOTNET_URL", "http://localhost:5000")
        _queue(
            _FakeResponse(302, headers={"location": "https://localhost:5000/CreateInstance/FunPubInsertInstanceLog"}),
            _FakeResponse(200, json_data=[True, "01-Jan-2026", "OK", True, "Submitted"]),
        )

        import asyncio
        result = asyncio.run(ig.call_generate_api("4046", "01-Jan-2026", asp_session="cookie"))

        assert result["success"] is True
        assert len(_FakeAsyncClient.instances) == 2  # original + HTTPS retry

    def test_redirect_to_a_different_host_is_not_followed(self, monkeypatch):
        """The H-04 fix: a redirect to a DIFFERENT host must be refused, not
        followed with the session cookie attached."""
        monkeypatch.setattr(ig, "_DOTNET_URL", "http://localhost:5000")
        _queue(
            _FakeResponse(302, headers={"location": "https://evil.example.com/steal"}),
        )

        import asyncio
        result = asyncio.run(ig.call_generate_api("4046", "01-Jan-2026", asp_session="cookie"))

        assert result["success"] is False
        # Only the original request was made -- the malicious redirect was
        # never followed with the cookie attached.
        assert len(_FakeAsyncClient.instances) == 1

    def test_login_redirect_on_same_host_still_treated_as_auth_failure(self, monkeypatch):
        monkeypatch.setattr(ig, "_DOTNET_URL", "http://localhost:5000")
        _queue(
            _FakeResponse(302, headers={"location": "http://localhost:5000/Account/Login"}),
        )

        import asyncio
        result = asyncio.run(ig.call_generate_api("4046", "01-Jan-2026", asp_session="cookie"))

        assert result["success"] is False
        assert len(_FakeAsyncClient.instances) == 1


class TestNoCookieValueLogged:
    def test_call_generate_api_never_logs_the_cookie_value(self, monkeypatch, caplog):
        secret_cookie = "SUPER-SECRET-SESSION-VALUE-DO-NOT-LOG"
        _queue(_FakeResponse(200, json_data=[True, "01-Jan-2026", "OK", True, "Submitted"]))

        import asyncio
        with caplog.at_level("INFO"):
            asyncio.run(ig.call_generate_api("4046", "01-Jan-2026", asp_session=secret_cookie))

        for record in caplog.records:
            assert secret_cookie not in record.getMessage()
            assert secret_cookie[:16] not in record.getMessage()
