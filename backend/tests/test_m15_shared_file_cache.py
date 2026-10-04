"""M-15: backend/utils/file_cache.py's shared FileCache utility, replacing
the three independent ad-hoc caches in report_lookup.py, instance_generator.py,
and taxonomy_index.py.
"""
from __future__ import annotations

import threading
import time

import pytest

from backend.utils.file_cache import FileCache


class TestCacheHitAndMiss:
    def test_miss_calls_the_loader(self):
        cache = FileCache()
        calls = {"n": 0}

        def _load():
            calls["n"] += 1
            return "value"

        result = cache.get_or_load("k", _load)
        assert result == "value"
        assert calls["n"] == 1

    def test_hit_does_not_call_the_loader_again(self):
        cache = FileCache()
        calls = {"n": 0}

        def _load():
            calls["n"] += 1
            return "value"

        cache.get_or_load("k", _load)
        cache.get_or_load("k", _load)
        cache.get_or_load("k", _load)
        assert calls["n"] == 1

    def test_plain_get_set_without_loader(self):
        cache = FileCache()
        assert cache.get("k") is None
        cache.set("k", "v")
        assert cache.get("k") == "v"

    def test_different_keys_are_independent(self):
        cache = FileCache()
        cache.set("a", 1)
        cache.set("b", 2)
        assert cache.get("a") == 1
        assert cache.get("b") == 2


class TestMtimeInvalidation:
    def test_unchanged_file_serves_cached_value(self, tmp_path):
        cache = FileCache()
        p = tmp_path / "f.txt"
        p.write_text("v1")
        calls = {"n": 0}

        def _load():
            calls["n"] += 1
            return p.read_text()

        assert cache.get_or_load(str(p), _load, path=str(p)) == "v1"
        assert cache.get_or_load(str(p), _load, path=str(p)) == "v1"
        assert calls["n"] == 1

    def test_changed_mtime_triggers_reload(self, tmp_path):
        cache = FileCache()
        p = tmp_path / "f.txt"
        p.write_text("v1")
        calls = {"n": 0}

        def _load():
            calls["n"] += 1
            return p.read_text()

        assert cache.get_or_load(str(p), _load, path=str(p)) == "v1"

        time.sleep(0.05)
        p.write_text("v2")
        future = time.time() + 5
        import os
        os.utime(str(p), (future, future))

        assert cache.get_or_load(str(p), _load, path=str(p)) == "v2"
        assert calls["n"] == 2

    def test_deleted_file_fails_safe_and_serves_stale_value(self, tmp_path):
        """Mirrors the original _TTLCache._file_changed()'s OSError handling
        -- a file that's momentarily unreadable must not be treated as
        'changed' (which would mean re-running loader(), which would itself
        likely fail)."""
        cache = FileCache()
        p = tmp_path / "f.txt"
        p.write_text("v1")
        calls = {"n": 0}

        def _load():
            calls["n"] += 1
            return "loaded"

        assert cache.get_or_load(str(p), _load, path=str(p)) == "loaded"
        p.unlink()
        assert cache.get_or_load(str(p), _load, path=str(p)) == "loaded"
        assert calls["n"] == 1


class TestTtlExpiry:
    def test_ttl_expiry_triggers_reload(self):
        cache = FileCache()
        calls = {"n": 0}

        def _load():
            calls["n"] += 1
            return calls["n"]

        assert cache.get_or_load("k", _load, ttl=0.05) == 1
        time.sleep(0.1)
        assert cache.get_or_load("k", _load, ttl=0.05) == 2

    def test_within_ttl_serves_cached_value(self):
        cache = FileCache()
        calls = {"n": 0}

        def _load():
            calls["n"] += 1
            return calls["n"]

        assert cache.get_or_load("k", _load, ttl=10.0) == 1
        assert cache.get_or_load("k", _load, ttl=10.0) == 1
        assert calls["n"] == 1


class TestBoundedSize:
    def test_max_size_is_enforced(self):
        cache = FileCache(max_size=3)
        for i in range(10):
            cache.set(f"k{i}", i)
        assert len(cache) == 3

    def test_least_recently_used_is_evicted_first(self):
        cache = FileCache(max_size=2)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.get("a")  # touch "a" -- "b" is now least-recently-used
        cache.set("c", 3)  # should evict "b", not "a"
        assert cache.get("a") == 1
        assert cache.get("b") is None
        assert cache.get("c") == 3

    def test_invalid_max_size_rejected(self):
        with pytest.raises(ValueError):
            FileCache(max_size=0)


class TestConcurrentAccess:
    def test_concurrent_get_or_load_is_safe_and_converges(self):
        cache = FileCache()
        calls = {"n": 0}
        lock = threading.Lock()

        def _load():
            with lock:
                calls["n"] += 1
            time.sleep(0.01)
            return "value"

        results = []

        def _worker():
            results.append(cache.get_or_load("shared-key", _load))

        threads = [threading.Thread(target=_worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert all(r == "value" for r in results)
        # Every thread converges on the same cached value; the loader may
        # run more than once under a cold-key race (documented, same as the
        # previous per-site caches), but the cache never ends up corrupted.
        assert cache.get("shared-key") == "value"

    def test_concurrent_set_does_not_corrupt_the_store(self):
        cache = FileCache(max_size=50)

        def _worker(i):
            for j in range(20):
                cache.set(f"k{i}-{j}", (i, j))

        threads = [threading.Thread(target=_worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(cache) <= 50
