"""M-01: TTLDict is a dict subclass that bounds itself (LRU eviction) and
expires stale entries, swept opportunistically on write -- used to close the
unbounded-growth gap in backend/agent/state.py's _session_context/_error_jobs
and backend/guided.py's _guided_sessions, none of which previously had any
generic cap or expiry.
"""
from __future__ import annotations

import threading
import time

import pytest

from backend.utils.ttl_registry import TTLDict


class TestBasicDictInterface:
    def test_set_get_pop_contains_work_like_a_plain_dict(self):
        d = TTLDict(max_size=10, ttl_seconds=60)
        d["a"] = {"x": 1}
        assert d["a"] == {"x": 1}
        assert "a" in d
        assert d.get("a") == {"x": 1}
        assert d.get("missing") is None
        assert d.pop("a", None) == {"x": 1}
        assert "a" not in d
        assert d.pop("missing", None) is None

    def test_isinstance_dict(self):
        """Call sites may type-check or serialize as a plain dict."""
        d = TTLDict(max_size=10, ttl_seconds=60)
        assert isinstance(d, dict)


class TestMaxSizeEviction:
    def test_oldest_entries_evicted_when_over_capacity(self):
        d = TTLDict(max_size=3, ttl_seconds=3600)
        d["a"] = 1
        d["b"] = 2
        d["c"] = 3
        d["d"] = 4  # should evict "a" (oldest)
        assert len(d) == 3
        assert "a" not in d
        assert "d" in d

    def test_rewriting_an_existing_key_refreshes_its_recency(self):
        d = TTLDict(max_size=2, ttl_seconds=3600)
        d["a"] = 1
        d["b"] = 2
        d["a"] = 10  # touch "a" again -- now "b" is oldest
        d["c"] = 3   # should evict "b", not "a"
        assert "a" in d
        assert "b" not in d
        assert "c" in d


class TestTTLExpiry:
    def test_entry_older_than_ttl_is_evicted_on_next_write(self):
        d = TTLDict(max_size=100, ttl_seconds=0.05)
        d["a"] = 1
        time.sleep(0.1)
        d["b"] = 2  # sweep runs here
        assert "a" not in d
        assert "b" in d

    def test_fresh_entries_survive_a_sweep(self):
        d = TTLDict(max_size=100, ttl_seconds=10)
        d["a"] = 1
        d["b"] = 2
        assert "a" in d and "b" in d


class TestConcurrentAccess:
    def test_concurrent_writes_from_multiple_threads_do_not_corrupt_state(self):
        """Mirrors _error_jobs, which is written from both the request thread
        and background_jobs.py's ThreadPoolExecutor workers (M-02)."""
        d = TTLDict(max_size=1000, ttl_seconds=3600)
        errors = []

        def _worker(i):
            try:
                for j in range(50):
                    d[f"job-{i}-{j}"] = {"status": "pending"}
            except Exception as exc:  # pragma: no cover - failure path only
                errors.append(exc)

        threads = [threading.Thread(target=_worker, args=(i,)) for i in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert len(d) <= 1000


class TestConstructorValidation:
    def test_rejects_non_positive_max_size(self):
        with pytest.raises(ValueError):
            TTLDict(max_size=0, ttl_seconds=60)

    def test_rejects_non_positive_ttl(self):
        with pytest.raises(ValueError):
            TTLDict(max_size=10, ttl_seconds=0)
