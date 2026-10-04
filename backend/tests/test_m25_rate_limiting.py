"""M-25: nothing in the backend previously limited how many requests a single
caller/IP could make -- every endpoint, including the expensive LLM-backed
ones, was wide open to being hammered (DoS / "denial of wallet").

``backend/rate_limit.py`` adds a small in-process sliding-window limiter,
wired into ``backend/main.py`` as HTTP middleware on the expensive endpoints
only (``_RATE_LIMITED_PATHS``). It is OFF by default
(``RATE_LIMIT_ENABLED`` unset) so normal development and the rest of this
test suite are unaffected; a deployment opts in explicitly via env vars.

These tests exercise the limiter unit directly (fast, deterministic, no
sleeping through real windows) and the middleware wiring end-to-end with a
tiny configured window.
"""
from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from backend import main as main_module
from backend.rate_limit import SlidingWindowRateLimiter


# ---------------------------------------------------------------------------
# Unit tests for the limiter itself
# ---------------------------------------------------------------------------

class TestSlidingWindowRateLimiter:
    def test_requests_below_limit_are_all_allowed(self):
        rl = SlidingWindowRateLimiter()
        for _ in range(5):
            allowed, _ = rl.check("k", limit=5, window=60)
            assert allowed

    def test_request_exceeding_limit_is_rejected(self):
        rl = SlidingWindowRateLimiter()
        for _ in range(5):
            assert rl.check("k", limit=5, window=60)[0] is True
        allowed, retry_after = rl.check("k", limit=5, window=60)
        assert allowed is False
        assert retry_after > 0

    def test_independent_keys_do_not_share_a_budget(self):
        rl = SlidingWindowRateLimiter()
        for _ in range(5):
            assert rl.check("user-a", limit=5, window=60)[0] is True
        # A different key (different IP/principal/path) has its own budget.
        assert rl.check("user-b", limit=5, window=60)[0] is True

    def test_window_reset_allows_requests_again(self):
        rl = SlidingWindowRateLimiter()
        for _ in range(3):
            assert rl.check("k", limit=3, window=0.2)[0] is True
        assert rl.check("k", limit=3, window=0.2)[0] is False
        time.sleep(0.25)
        allowed, _ = rl.check("k", limit=3, window=0.2)
        assert allowed is True

    def test_reset_clears_all_state(self):
        rl = SlidingWindowRateLimiter()
        rl.check("k", limit=1, window=60)
        assert rl.check("k", limit=1, window=60)[0] is False
        rl.reset()
        assert rl.check("k", limit=1, window=60)[0] is True


# ---------------------------------------------------------------------------
# Middleware wiring (disabled by default; enabled with a tiny window here)
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    return TestClient(main_module.app)


@pytest.fixture(autouse=True)
def _reset_limiter():
    main_module.rate_limit.limiter.reset()
    yield
    main_module.rate_limit.limiter.reset()


class TestMiddlewareDisabledByDefault:
    def test_rate_limiting_is_off_unless_explicitly_enabled(self, monkeypatch):
        monkeypatch.delenv("RATE_LIMIT_ENABLED", raising=False)
        assert main_module.rate_limit.is_enabled() is False

    def test_health_endpoint_is_never_rate_limited(self, client, monkeypatch):
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
        monkeypatch.setenv("RATE_LIMIT_MAX_REQUESTS", "1")
        monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")
        for _ in range(10):
            res = client.get("/health")
            assert res.status_code == 200


class TestMiddlewareEnforcement:
    def test_requests_below_limit_pass_through(self, client, monkeypatch):
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
        monkeypatch.setenv("RATE_LIMIT_MAX_REQUESTS", "3")
        monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")
        # M-11: /stop now gates on a resolvable login_id when REQUIRE_AUTH is
        # on; this test uses it only as a cheap endpoint to probe the rate
        # limit middleware, not to test auth (see test_m05_m11_endpoint_auth.py).
        monkeypatch.setenv("REQUIRE_AUTH", "false")
        for _ in range(3):
            res = client.post("/stop", json={"request_id": "nonexistent"})
            # /stop is not in the rate-limited path set, so this always
            # passes -- used here only as a cheap unauthenticated endpoint
            # to confirm the middleware doesn't block unrelated paths.
            assert res.status_code == 200

    def test_exceeding_limit_returns_429_with_retry_after(self, client, monkeypatch):
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
        monkeypatch.setenv("RATE_LIMIT_MAX_REQUESTS", "2")
        monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")

        payload = {"message": "hi"}
        r1 = client.post("/chat", json=payload)
        r2 = client.post("/chat", json=payload)
        r3 = client.post("/chat", json=payload)

        assert r1.status_code != 429
        assert r2.status_code != 429
        assert r3.status_code == 429
        assert "retry-after" in {k.lower() for k in r3.headers.keys()}
        assert int(r3.headers["Retry-After"]) >= 1

    def test_independent_ips_are_tracked_separately(self, monkeypatch):
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
        monkeypatch.setenv("RATE_LIMIT_MAX_REQUESTS", "1")
        monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")

        allowed_a, _ = main_module.rate_limit.limiter.check("/chat:1.2.3.4", limit=1, window=60)
        allowed_b, _ = main_module.rate_limit.limiter.check("/chat:5.6.7.8", limit=1, window=60)
        assert allowed_a is True
        assert allowed_b is True  # different IP, independent budget

    def test_configuration_can_disable_limiting_for_tests(self, client, monkeypatch):
        monkeypatch.delenv("RATE_LIMIT_ENABLED", raising=False)
        for _ in range(10):
            res = client.post("/chat", json={"message": "hi"})
            assert res.status_code != 429

    def test_window_env_vars_are_read_with_safe_fallbacks(self, monkeypatch):
        monkeypatch.setenv("RATE_LIMIT_MAX_REQUESTS", "not-a-number")
        monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "not-a-number")
        assert main_module.rate_limit.max_requests() == 30
        assert main_module.rate_limit.window_seconds() == 60.0
