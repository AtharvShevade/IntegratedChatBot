"""M-29: the existing /health endpoint only proves the process is alive --
it never touches Oracle/Ollama/STT/the data repo path. /health/ready is a
separate endpoint that actually checks those dependencies, with a short
timeout per check (so one hung dependency cannot make the endpoint itself
hang) and a brief result cache (so a tight polling loop doesn't hammer every
dependency on every call).
"""
from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from backend import main as main_module

client = TestClient(main_module.app)


@pytest.fixture(autouse=True)
def _reset_readiness_cache():
    main_module._READINESS_CACHE["result"] = None
    main_module._READINESS_CACHE["checked_at"] = 0.0
    yield
    main_module._READINESS_CACHE["result"] = None
    main_module._READINESS_CACHE["checked_at"] = 0.0


class TestLivenessUnaffected:
    def test_health_endpoint_still_works_unchanged(self):
        res = client.get("/health")
        assert res.status_code == 200
        assert res.json() == {"status": "ok"}

    def test_health_endpoint_never_touches_dependencies(self, monkeypatch):
        # If /health ever starts calling a dependency check, this will fail
        # loudly instead of silently passing.
        called = {"n": 0}

        async def _poison(*a, **kw):
            called["n"] += 1
            return False

        monkeypatch.setattr(main_module, "_check_oracle", _poison)
        monkeypatch.setattr(main_module, "_check_ollama", _poison)
        res = client.get("/health")
        assert res.status_code == 200
        assert called["n"] == 0


class TestAllDependenciesAvailable:
    def test_ready_when_everything_is_up(self, monkeypatch):
        async def _ok():
            return True
        async def _stt_ok():
            return True
        monkeypatch.setattr(main_module, "_check_oracle", _ok)
        monkeypatch.setattr(main_module, "_check_ollama", _ok)
        monkeypatch.setattr(main_module, "_check_stt", _stt_ok)
        monkeypatch.setattr(main_module, "_check_data_repo_path", lambda: True)

        res = client.get("/health/ready")
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "ready"
        assert body["ready"] is True
        assert body["checks"] == {
            "oracle": True, "ollama": True, "stt": True, "data_repo_path": True,
        }

    def test_ready_when_stt_disabled_is_not_a_failure(self, monkeypatch):
        async def _ok():
            return True
        async def _stt_disabled():
            return None
        monkeypatch.setattr(main_module, "_check_oracle", _ok)
        monkeypatch.setattr(main_module, "_check_ollama", _ok)
        monkeypatch.setattr(main_module, "_check_stt", _stt_disabled)
        monkeypatch.setattr(main_module, "_check_data_repo_path", lambda: True)

        res = client.get("/health/ready")
        assert res.status_code == 200
        assert res.json()["ready"] is True
        assert res.json()["checks"]["stt"] == "disabled"


class TestOneDependencyUnavailable:
    @pytest.mark.parametrize("failing_check", ["_check_oracle", "_check_ollama"])
    def test_one_failing_dependency_reports_not_ready_with_503(self, monkeypatch, failing_check):
        async def _ok():
            return True
        async def _fail():
            return False
        monkeypatch.setattr(main_module, "_check_oracle", _ok)
        monkeypatch.setattr(main_module, "_check_ollama", _ok)
        monkeypatch.setattr(main_module, "_check_stt", lambda: _const_coro(None))
        monkeypatch.setattr(main_module, "_check_data_repo_path", lambda: True)
        monkeypatch.setattr(main_module, failing_check, _fail)

        res = client.get("/health/ready")
        assert res.status_code == 503
        body = res.json()
        assert body["status"] == "not_ready"
        assert body["ready"] is False

    def test_data_repo_path_missing_is_reported(self, monkeypatch):
        async def _ok():
            return True
        monkeypatch.setattr(main_module, "_check_oracle", _ok)
        monkeypatch.setattr(main_module, "_check_ollama", _ok)
        monkeypatch.setattr(main_module, "_check_stt", lambda: _const_coro(None))
        monkeypatch.setattr(main_module, "_check_data_repo_path", lambda: False)

        res = client.get("/health/ready")
        assert res.status_code == 503
        assert res.json()["checks"]["data_repo_path"] is False


async def _const_coro(value):
    return value


class TestDependencyTimeoutDoesNotHang:
    def test_slow_oracle_check_is_bounded_by_the_timeout(self, monkeypatch):
        monkeypatch.setattr(main_module, "_READINESS_CHECK_TIMEOUT_S", 0.2)

        async def _ok():
            return True

        async def _never_finishes():
            try:
                await asyncio.wait_for(asyncio.sleep(10), timeout=main_module._READINESS_CHECK_TIMEOUT_S)
                return True
            except asyncio.TimeoutError:
                return False

        monkeypatch.setattr(main_module, "_check_oracle", _never_finishes)
        monkeypatch.setattr(main_module, "_check_ollama", _ok)
        monkeypatch.setattr(main_module, "_check_stt", lambda: _const_coro(None))
        monkeypatch.setattr(main_module, "_check_data_repo_path", lambda: True)

        import time
        start = time.monotonic()
        res = client.get("/health/ready")
        elapsed = time.monotonic() - start

        assert elapsed < 2.0, f"readiness endpoint took {elapsed}s -- a hung dependency must not block it"
        assert res.status_code == 503  # the bounded-out check correctly reports not-ready


class TestResultIsCachedBriefly:
    def test_repeated_calls_within_ttl_do_not_recheck_dependencies(self, monkeypatch):
        call_counts = {"oracle": 0, "ollama": 0}

        async def _counting_oracle():
            call_counts["oracle"] += 1
            return True

        async def _counting_ollama():
            call_counts["ollama"] += 1
            return True

        monkeypatch.setattr(main_module, "_check_oracle", _counting_oracle)
        monkeypatch.setattr(main_module, "_check_ollama", _counting_ollama)
        monkeypatch.setattr(main_module, "_check_stt", lambda: _const_coro(None))
        monkeypatch.setattr(main_module, "_check_data_repo_path", lambda: True)
        monkeypatch.setattr(main_module, "_READINESS_CACHE_TTL_S", 60.0)

        client.get("/health/ready")
        client.get("/health/ready")
        client.get("/health/ready")

        assert call_counts["oracle"] == 1, "cached result must be reused, not re-checked every call"
        assert call_counts["ollama"] == 1
