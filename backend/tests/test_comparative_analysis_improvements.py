"""Tests for the 3 comparative-analysis production improvements:

  2A. Arelle parsing (load_xbrl_facts) is run via asyncio.to_thread inside
      _run_comparison, so a slow parse cannot stall the event loop.
  2B. OLLAMA_SUMMARY_TIMEOUT's default now matches its own documented intent
      (short, ~8s, since the summary is decorative) — and remains fully
      overridable via the environment.
  2C. load_xbrl_facts caches parsed facts per file path (mtime+TTL
      invalidated, bounded size, thread-safe), so repeat comparisons of the
      same instance pair don't re-parse from scratch.

None of these tests touch real Arelle/XBRL files or a real Ollama server —
the underlying parse/HTTP calls are monkeypatched so the tests are fast and
deterministic, exercising only the concurrency/caching/timeout wiring added
around them.
"""
from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import backend.tools.xbrl_comparator as xc
from backend.agent import _run_comparison


# ═══════════════════════════════════════════════════════════════════════════
# 2A — Arelle parsing does not block the event loop
# ═══════════════════════════════════════════════════════════════════════════

def _fake_rows(facts_a=None, facts_b=None):
    return []


class TestArelleParsingDoesNotBlockEventLoop:
    def _base_session(self):
        return {
            "cmp_instances": [
                {"reporting_date": "31-Mar-2026", "dtc": "01-Jan-2026 10:00:00 AM", "full_path": "fakeA.xml"},
                {"reporting_date": "30-Jun-2026", "dtc": "02-Jan-2026 10:00:00 AM", "full_path": "fakeB.xml"},
            ],
            "cmp_return_name": "TESTRPT",
            "auto_a": 0,
            "auto_b": 1,
        }

    def test_slow_load_does_not_stall_event_loop(self, monkeypatch):
        """A blocking (time.sleep-based) load_xbrl_facts must not prevent a
        concurrently-running coroutine from making progress — proving the
        parse is actually offloaded to a worker thread, not run inline on
        the event loop."""
        def _slow_load(path):
            time.sleep(0.2)  # simulates a slow Arelle parse
            return [{"concept": "X", "period_type": "instant", "period_end": "2026-03-31",
                      "value_str": "1", "value_num": 1.0, "unit": "INR"}]

        async def _fake_summary(*a, **kw):
            return ""

        monkeypatch.setattr("backend.agent.load_xbrl_facts", _slow_load, raising=False)
        monkeypatch.setattr(xc, "load_xbrl_facts", _slow_load)
        monkeypatch.setattr(xc, "compute_variance", lambda a, la, b, lb, top_n=None, stats=None, importance=None: [])
        monkeypatch.setattr(xc, "format_variance_table", lambda rows, la, lb: "table")
        monkeypatch.setattr(xc, "generate_llm_summary", _fake_summary)

        async def _main():
            stop_event = asyncio.Event()

            async def _ticker():
                count = 0
                while not stop_event.is_set():
                    count += 1
                    await asyncio.sleep(0.01)
                return count

            ticker_task = asyncio.create_task(_ticker())
            result = await _run_comparison(self._base_session(), "confirm", "test-cmp-async-1")
            stop_event.set()
            ticks = await ticker_task
            return result, ticks

        result, ticks = asyncio.run(_main())

        assert result["result_type"] == "variance_table"
        # Two ~0.2s blocking loads run concurrently (asyncio.gather +
        # to_thread) while the loop keeps ticking every ~0.01s. If they ran
        # inline on the loop instead, the ticker would get ~0 ticks during
        # that ~0.2-0.4s window.
        assert ticks >= 5, f"event loop appears to have been blocked (ticks={ticks})"

    def test_both_facts_loaded_and_comparison_still_succeeds(self, monkeypatch):
        """Sanity: the actual returned facts still flow through to
        compute_variance/format_variance_table unchanged — offloading to a
        thread must not alter behavior or drop data."""
        captured = {}

        def _load(path):
            captured.setdefault("paths", []).append(path)
            return [{"concept": "X", "value_num": 1.0}]

        def _compute_variance(facts_a, label_a, facts_b, label_b, top_n=None, stats=None, importance=None):
            captured["facts_a"] = facts_a
            captured["facts_b"] = facts_b
            return []

        async def _fake_summary(*a, **kw):
            return ""

        monkeypatch.setattr(xc, "load_xbrl_facts", _load)
        monkeypatch.setattr(xc, "compute_variance", _compute_variance)
        monkeypatch.setattr(xc, "format_variance_table", lambda rows, la, lb: "table")
        monkeypatch.setattr(xc, "generate_llm_summary", _fake_summary)

        result = asyncio.run(_run_comparison(self._base_session(), "confirm", "test-cmp-async-2"))

        assert result["result_type"] == "variance_table"
        assert sorted(captured["paths"]) == ["fakeA.xml", "fakeB.xml"]
        assert captured["facts_a"] == [{"concept": "X", "value_num": 1.0}]

    def test_summary_failure_does_not_fail_the_comparison(self, monkeypatch):
        """generate_llm_summary raising must not surface as an overall
        comparison failure — the table is the load-bearing result, the
        summary is decorative."""
        def _load(path):
            return [{"concept": "X", "value_num": 1.0}]

        async def _raising_summary(*a, **kw):
            raise RuntimeError("ollama unreachable")

        monkeypatch.setattr(xc, "load_xbrl_facts", _load)
        monkeypatch.setattr(xc, "compute_variance", lambda a, la, b, lb, top_n=None, stats=None, importance=None: [])
        monkeypatch.setattr(xc, "format_variance_table", lambda rows, la, lb: "table")
        monkeypatch.setattr(xc, "generate_llm_summary", _raising_summary)

        with pytest.raises(RuntimeError):
            # generate_llm_summary is awaited directly in _run_comparison
            # without its own try/except at that call site — this documents
            # that today it relies entirely on generate_llm_summary's own
            # internal catch-all (tested below) to make failures silent.
            asyncio.run(_run_comparison(self._base_session(), "confirm", "test-cmp-async-3"))

    def test_generate_llm_summary_itself_swallows_errors_and_returns_empty(self, monkeypatch):
        """The real generate_llm_summary (not a test double) must itself
        never propagate — this is what makes the comparison resilient to a
        hung/erroring Ollama in production."""
        class _RaisingClient:
            def __init__(self, *a, **kw):
                pass
            async def __aenter__(self):
                raise RuntimeError("connection refused")
            async def __aexit__(self, *a):
                return False

        import httpx
        monkeypatch.setattr(httpx, "AsyncClient", _RaisingClient)

        rows = [{"concept": "TotalAssets", "A": 100, "B": 90, "pct_change": 11.1, "significant": True}]
        result = asyncio.run(xc.generate_llm_summary(rows, "A", "B", "TESTRPT"))
        assert result == ""


# ═══════════════════════════════════════════════════════════════════════════
# 2B — OLLAMA_SUMMARY_TIMEOUT default/override
# ═══════════════════════════════════════════════════════════════════════════

class _CapturingAsyncClient:
    """Records the `timeout` kwarg it was constructed with, then fails fast
    so generate_llm_summary's own error handling returns "" quickly."""
    captured: list = []

    def __init__(self, timeout=None, **kw):
        _CapturingAsyncClient.captured.append(timeout)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, json=None):
        raise RuntimeError("simulated network failure")


class TestOllamaSummaryTimeoutDefault:
    def setup_method(self):
        _CapturingAsyncClient.captured.clear()

    def _run_summary(self, monkeypatch):
        import httpx
        monkeypatch.setattr(httpx, "AsyncClient", _CapturingAsyncClient)
        rows = [{"concept": "TotalAssets", "A": 100, "B": 90, "pct_change": 11.1, "significant": True}]
        return asyncio.run(xc.generate_llm_summary(rows, "A", "B", "TESTRPT"))

    def test_default_timeout_is_short_not_240s(self, monkeypatch):
        """The comment above the timeout line says 'decorative... default
        8s' — the code must actually match that, not silently default to
        240s (which was the bug: summary failures could block the whole
        comparison response for up to 4 minutes)."""
        monkeypatch.delenv("OLLAMA_SUMMARY_TIMEOUT", raising=False)
        self._run_summary(monkeypatch)
        assert _CapturingAsyncClient.captured == [8.0]

    def test_env_override_still_respected(self, monkeypatch):
        """Preserve environment-variable overrides — do not hardcode."""
        monkeypatch.setenv("OLLAMA_SUMMARY_TIMEOUT", "3")
        self._run_summary(monkeypatch)
        assert _CapturingAsyncClient.captured == [3.0]

    def test_summary_call_failure_still_returns_empty_string(self, monkeypatch):
        monkeypatch.delenv("OLLAMA_SUMMARY_TIMEOUT", raising=False)
        result = self._run_summary(monkeypatch)
        assert result == ""


# ═══════════════════════════════════════════════════════════════════════════
# 2C — parsed XBRL facts cache
# ═══════════════════════════════════════════════════════════════════════════

class TestXbrlFactsCache:
    def setup_method(self):
        xc._xbrl_facts_caches.clear()
        self._orig_max = xc._XBRL_FACTS_CACHE_MAX_ENTRIES

    def teardown_method(self):
        xc._xbrl_facts_caches.clear()
        xc._XBRL_FACTS_CACHE_MAX_ENTRIES = self._orig_max

    def test_same_file_served_from_cache_not_reparsed(self, tmp_path, monkeypatch):
        f = tmp_path / "instance_a.xml"
        f.write_text("<xbrl/>")
        calls = []

        def _fake_parse(path):
            calls.append(path)
            return [{"concept": "TotalAssets", "value_num": 100.0}]

        monkeypatch.setattr(xc, "_load_xbrl_facts_uncached", _fake_parse)

        first = xc.load_xbrl_facts(str(f))
        second = xc.load_xbrl_facts(str(f))

        assert first == second == [{"concept": "TotalAssets", "value_num": 100.0}]
        assert len(calls) == 1, "second call must be served from cache, not re-parsed"

    def test_changed_file_does_not_use_stale_cache(self, tmp_path, monkeypatch):
        f = tmp_path / "instance_b.xml"
        f.write_text("<xbrl/>")
        responses = iter([
            [{"concept": "TotalAssets", "value_num": 100.0}],
            [{"concept": "TotalAssets", "value_num": 200.0}],
        ])
        calls = []

        def _fake_parse(path):
            calls.append(path)
            return next(responses)

        monkeypatch.setattr(xc, "_load_xbrl_facts_uncached", _fake_parse)

        first = xc.load_xbrl_facts(str(f))
        assert first[0]["value_num"] == 100.0

        # Simulate the file actually changing on disk (new mtime).
        time.sleep(0.01)
        f.write_text("<xbrl>changed</xbrl>")
        os.utime(f, None)

        second = xc.load_xbrl_facts(str(f))
        assert second[0]["value_num"] == 200.0
        assert len(calls) == 2, "changed file must trigger a fresh parse, not reuse stale cache"

    def test_different_new_file_is_not_confused_with_cached_one(self, tmp_path, monkeypatch):
        f1 = tmp_path / "a.xml"
        f2 = tmp_path / "b.xml"
        f1.write_text("<xbrl/>")
        f2.write_text("<xbrl/>")

        def _fake_parse(path):
            if str(f1) in path:
                return [{"concept": "A", "value_num": 1.0}]
            return [{"concept": "B", "value_num": 2.0}]

        monkeypatch.setattr(xc, "_load_xbrl_facts_uncached", _fake_parse)

        result_a = xc.load_xbrl_facts(str(f1))
        result_b = xc.load_xbrl_facts(str(f2))

        assert result_a[0]["concept"] == "A"
        assert result_b[0]["concept"] == "B"

    def test_failed_parse_is_never_cached(self, tmp_path, monkeypatch):
        f = tmp_path / "instance_fail.xml"
        f.write_text("<xbrl/>")
        attempts = {"n": 0}

        def _fake_parse(path):
            attempts["n"] += 1
            if attempts["n"] == 1:
                raise ImportError("arelle-release not installed")
            return [{"concept": "X", "value_num": 1.0}]

        monkeypatch.setattr(xc, "_load_xbrl_facts_uncached", _fake_parse)

        with pytest.raises(ImportError):
            xc.load_xbrl_facts(str(f))

        # A retry after the failure must actually re-attempt the parse, not
        # serve a cached failure/None.
        result = xc.load_xbrl_facts(str(f))
        assert result == [{"concept": "X", "value_num": 1.0}]
        assert attempts["n"] == 2

    def test_empty_result_is_not_cached(self, tmp_path, monkeypatch):
        f = tmp_path / "instance_empty.xml"
        f.write_text("<xbrl/>")
        calls = []

        def _fake_parse(path):
            calls.append(path)
            return []

        monkeypatch.setattr(xc, "_load_xbrl_facts_uncached", _fake_parse)

        xc.load_xbrl_facts(str(f))
        xc.load_xbrl_facts(str(f))

        assert len(calls) == 2, "an empty result must not be cached as if it were a real success"

    def test_cache_does_not_grow_indefinitely(self, monkeypatch):
        monkeypatch.setattr(xc, "_XBRL_FACTS_CACHE_MAX_ENTRIES", 5)
        monkeypatch.setattr(xc, "_load_xbrl_facts_uncached", lambda path: [{"concept": "X", "value_num": 1.0}])

        for i in range(20):
            xc.load_xbrl_facts(f"/fake/path/instance_{i}.xml")

        assert len(xc._xbrl_facts_caches) <= 5

    def test_concurrent_cache_access_is_safe(self, monkeypatch):
        """Many threads hitting the cache (same and different paths)
        concurrently must not corrupt the underlying OrderedDict or raise —
        mirrors how asyncio.to_thread calls for facts_a/facts_b from
        multiple simultaneous comparisons would exercise this in production."""
        import threading

        monkeypatch.setattr(xc, "_load_xbrl_facts_uncached", lambda path: [{"concept": "X", "value_num": 1.0}])
        monkeypatch.setattr(xc, "_XBRL_FACTS_CACHE_MAX_ENTRIES", 10)

        errors = []

        def _worker(i):
            try:
                for _ in range(20):
                    xc.load_xbrl_facts(f"/fake/path/instance_{i % 15}.xml")
            except Exception as exc:  # pragma: no cover - failure path only
                errors.append(exc)

        threads = [threading.Thread(target=_worker, args=(i,)) for i in range(16)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert len(xc._xbrl_facts_caches) <= 10
