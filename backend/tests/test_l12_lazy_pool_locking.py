"""L-12: lazy global pools/caches without locking.

1. backend/sql_agent/sqlcore/executor.py's _get_pool() -- a classic
   check-then-create race: two concurrent first callers could both see
   `_pool is None` and both oracledb.create_pool(), leaking one pool's
   connections. Now guarded by `_pool_lock` with double-checked locking.

2. backend/db_qa/intents/embedding_index.py's _load_index() -- same race on
   `_INDEX_CACHE`. Now guarded by `_index_lock`.
"""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import backend.sql_agent  # noqa: F401,E402  (runs _bootstrap.ensure(), puts `sqlcore` on sys.path)
from sqlcore import executor as sql_executor  # noqa: E402

import backend.db_qa.intents.embedding_index as embedding_index  # noqa: E402


class TestOracleConnectionPoolLocking:
    def test_concurrent_first_callers_create_exactly_one_pool(self, monkeypatch):
        monkeypatch.setattr(sql_executor, "_pool", None)
        create_calls = {"n": 0}

        class _FakePool:
            def acquire(self):
                return "fake-connection"

        def _slow_create_pool(**kwargs):
            # Widen the race window so two threads reliably both pass the
            # first (unlocked) `if _pool is None` check without the lock.
            time.sleep(0.05)
            create_calls["n"] += 1
            return _FakePool()

        monkeypatch.setattr(sql_executor.oracledb, "create_pool", _slow_create_pool)
        monkeypatch.setattr(sql_executor.oracledb, "makedsn", lambda *a, **k: "fake-dsn")

        threads = [threading.Thread(target=sql_executor._get_pool) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert create_calls["n"] == 1, "oracledb.create_pool() must only run once under concurrent first access"
        assert sql_executor._pool is not None

    def test_normal_single_threaded_init_still_works(self, monkeypatch):
        monkeypatch.setattr(sql_executor, "_pool", None)

        class _FakePool:
            def acquire(self):
                return "fake-connection"

        monkeypatch.setattr(sql_executor.oracledb, "create_pool", lambda **k: _FakePool())
        monkeypatch.setattr(sql_executor.oracledb, "makedsn", lambda *a, **k: "fake-dsn")

        pool1 = sql_executor._get_pool()
        pool2 = sql_executor._get_pool()
        assert pool1 is pool2


class TestEmbeddingIndexCacheLocking:
    def test_concurrent_first_callers_load_the_index_exactly_once(self, monkeypatch):
        monkeypatch.setattr(embedding_index, "_INDEX_CACHE", {})
        monkeypatch.setattr(embedding_index.os.path, "exists", lambda p: True)
        monkeypatch.setattr(embedding_index, "check_index_freshness", lambda: (True, "fresh"))

        load_calls = {"n": 0}

        class _FakeFaissModule:
            @staticmethod
            def read_index(path):
                time.sleep(0.05)  # widen the race window
                load_calls["n"] += 1
                return f"fake-index-{load_calls['n']}"

        fake_faiss = _FakeFaissModule()
        monkeypatch.setitem(sys.modules, "faiss", fake_faiss)

        import backend.sql_agent.sqlcore.integrity as integrity_module
        monkeypatch.setattr(integrity_module, "safe_pickle_load", lambda *a, **k: ["fake-meta"])

        threads = [threading.Thread(target=embedding_index._load_index) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert load_calls["n"] == 1, "faiss.read_index() must only run once under concurrent first access"

    def test_normal_single_threaded_load_still_works_and_is_cached(self, monkeypatch):
        monkeypatch.setattr(embedding_index, "_INDEX_CACHE", {})
        monkeypatch.setattr(embedding_index.os.path, "exists", lambda p: True)
        monkeypatch.setattr(embedding_index, "check_index_freshness", lambda: (True, "fresh"))

        class _FakeFaissModule:
            @staticmethod
            def read_index(path):
                return "the-index"

        monkeypatch.setitem(sys.modules, "faiss", _FakeFaissModule())

        import backend.sql_agent.sqlcore.integrity as integrity_module
        monkeypatch.setattr(integrity_module, "safe_pickle_load", lambda *a, **k: ["the-meta"])

        index1, meta1 = embedding_index._load_index()
        index2, meta2 = embedding_index._load_index()
        assert index1 is index2 == "the-index"
        assert meta1 is meta2 == ["the-meta"]

    def test_missing_index_file_raises_not_crashes_silently(self, monkeypatch):
        monkeypatch.setattr(embedding_index, "_INDEX_CACHE", {})
        monkeypatch.setattr(embedding_index.os.path, "exists", lambda p: False)
        import pytest
        with pytest.raises(FileNotFoundError):
            embedding_index._load_index()
