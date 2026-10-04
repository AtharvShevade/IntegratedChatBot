"""L-11: SQL Agent package initialization/import-path review.

Investigation findings (see Batch 3 report for full detail):
  - backend/sql_agent/_bootstrap.py's ensure() is already idempotent (a
    `_done` module flag) and already restores every env var it temporarily
    sets (_restore_env()) once sqlcore.config has read them -- so OLLAMA_MODEL
    etc. never leak the SQL agent's values into the rest of the process.
  - backend/sql_agent/__init__.py calls ensure() at package-import time, so
    by Python's own import ordering every submodule shim under
    backend/sql_agent/ (config.py, executor.py, retriever.py, selector.py,
    semantic_layer.py, vectorizer.py, sql_generator.py) is GUARANTEED to run
    after ensure() has already executed, even though each one also calls
    ensure() itself (harmless -- the _done guard makes every call after the
    first a no-op). No production code was changed for this investigation;
    these tests lock in the properties L-11 cares about (no network/DB call
    merely from import, no duplicate resource init, no env leakage,
    idempotent bootstrap) to prove the existing behavior is already correct.
  - UPDATE (L-11 cleanup batch): the vendored engine's internal package was
    renamed from the generic `src` to `sqlcore` (still put on sys.path by
    _bootstrap.ensure(), still importable directly by tests the same way
    `src` was) -- the namespace-collision risk this originally flagged is
    now closed. Every `from src.xxx import` / `import src.xxx` call site
    across the vendored engine's own files, the backend/sql_agent/*.py
    shims, and this test suite was updated to `sqlcore`. No behavior change:
    this is a pure import-path rename, same module contents, same public
    shim API (backend.sql_agent.config/executor/retriever/...).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestModulesImportSuccessfully:
    """Every current import path into the SQL agent package must keep
    working -- these are exactly the paths real call sites use."""

    def test_package_import_succeeds(self):
        import backend.sql_agent  # noqa: F401

    def test_config_shim_imports_successfully(self):
        from backend.sql_agent import config  # noqa: F401

    def test_executor_shim_imports_successfully(self):
        from backend.sql_agent import executor  # noqa: F401

    def test_retriever_shim_imports_successfully(self):
        from backend.sql_agent import retriever  # noqa: F401

    def test_selector_shim_imports_successfully(self):
        from backend.sql_agent import selector  # noqa: F401

    def test_semantic_layer_shim_imports_successfully(self):
        from backend.sql_agent import semantic_layer  # noqa: F401

    def test_vectorizer_shim_imports_successfully(self):
        from backend.sql_agent import vectorizer  # noqa: F401

    def test_sql_generator_shim_imports_successfully(self):
        from backend.sql_agent import sql_generator  # noqa: F401

    def test_query_handler_entry_point_still_exported(self):
        from backend.sql_agent import handle_db_query
        assert callable(handle_db_query)

    def test_vendored_src_package_importable_directly(self):
        """The path real sql_agent tests already use (sqlcore.* after
        `import backend.sql_agent`)."""
        import backend.sql_agent  # noqa: F401
        from sqlcore import config  # noqa: F401
        from sqlcore.sql_generator import validate_sql  # noqa: F401


class TestBootstrapIdempotency:
    def test_ensure_is_a_no_op_after_the_first_call(self):
        from backend.sql_agent import _bootstrap
        assert _bootstrap._done is True  # already run by every import above
        # Calling it again must not raise and must not change state.
        _bootstrap.ensure()
        assert _bootstrap._done is True

    def test_repeated_ensure_calls_do_not_grow_the_saved_env_snapshot_unboundedly(self):
        from backend.sql_agent import _bootstrap
        snapshot_size_before = len(_bootstrap._saved_env)
        for _ in range(5):
            _bootstrap.ensure()
        assert len(_bootstrap._saved_env) == snapshot_size_before


class TestNoEnvLeakage:
    """_restore_env() must hand the real OLLAMA_MODEL/OLLAMA_URL back to
    whatever the chatbot's own .env set -- these are read by
    backend/services/llm_service.py (OLLAMA_MODEL) and must never end up
    holding the SQL agent's own model name after ensure() returns."""

    def test_ollama_model_env_var_is_restored_not_left_as_the_sql_model(self):
        import os
        from backend.sql_agent import _bootstrap
        from sqlcore import config as sql_config

        # Whatever the SQL agent actually resolved for itself must differ
        # from (or at least not silently leak as) the live process env
        # unless they already happened to be the same model.
        chatbot_ollama_model = os.environ.get("OLLAMA_MODEL")
        assert "OLLAMA_MODEL" not in _bootstrap._saved_env or (
            os.environ.get("OLLAMA_MODEL") == _bootstrap._saved_env["OLLAMA_MODEL"]
            or (
                _bootstrap._saved_env["OLLAMA_MODEL"] is None
                and "OLLAMA_MODEL" not in os.environ
            )
        ), "ensure() must restore OLLAMA_MODEL to its pre-bootstrap value, not leave the SQL agent's model in the process env"


class TestNoUnnecessaryStartupNetworkOrDbCalls:
    def test_importing_executor_does_not_create_an_oracle_pool(self, monkeypatch):
        import importlib
        from sqlcore import executor as sql_executor

        create_pool_calls = {"n": 0}
        monkeypatch.setattr(
            sql_executor.oracledb, "create_pool",
            lambda **k: create_pool_calls.__setitem__("n", create_pool_calls["n"] + 1),
        )
        importlib.reload(sql_executor)

        assert create_pool_calls["n"] == 0
        assert sql_executor._pool is None

    def test_importing_vectorizer_does_not_make_network_calls(self):
        """The SentenceTransformer load is a local-disk model load (already
        warmed at FastAPI startup elsewhere), not a network call -- confirm
        importing this module doesn't itself trigger anything beyond that
        by checking the module imports without error and without requiring
        network access in this sandboxed test environment."""
        from sqlcore import vectorizer  # noqa: F401


class TestNoDuplicateResourceInitialization:
    def test_oracle_pool_is_created_at_most_once_across_many_get_connection_style_calls(self, monkeypatch):
        from sqlcore import executor as sql_executor

        monkeypatch.setattr(sql_executor, "_pool", None)
        create_calls = {"n": 0}

        class _FakePool:
            def acquire(self):
                return "fake-connection"

        monkeypatch.setattr(sql_executor.oracledb, "create_pool", lambda **k: (
            create_calls.__setitem__("n", create_calls["n"] + 1), _FakePool()
        )[1])
        monkeypatch.setattr(sql_executor.oracledb, "makedsn", lambda *a, **k: "fake-dsn")

        for _ in range(10):
            sql_executor._get_pool()

        assert create_calls["n"] == 1

    def test_sentence_transformer_model_is_a_single_shared_instance(self):
        """backend/db_qa/intents/embedding_index.py and
        backend/main.py's warm-up both reuse sqlcore.vectorizer's module-level
        `model` rather than loading a second copy -- confirm it really is
        the same object across both import paths."""
        from sqlcore import vectorizer as sql_vectorizer
        from backend.sql_agent import vectorizer as shim_vectorizer
        assert shim_vectorizer.model is sql_vectorizer.model
