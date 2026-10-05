"""M-07: db_sql / db_error exposure.

Investigation finding (see doc/CRITICAL_FIXES_LOG.md's M-07 entry for the
full writeup): tracing every one of handle_db_query's ~13 return points
showed `db_error` was already never populated with a raw exception in
practice -- executor.py's `execute_query()` DOES return raw Oracle/Python
exception strings, but query_handler.py already discarded them (explicitly
substituting `db_error=None` after logging) before building the client
response at every such path. The only non-None `db_error` values reaching
the client were validate_sql()'s own plain-English reasons -- which never
touch Oracle, so they were already safe in practice.

The gap was architectural, not a live leak: nothing PREVENTED a future edit
from accidentally wiring a raw exception into db_error (e.g. "just pass the
real reason through" during a refactor). Fixed by adding
`_safe_client_error()`, applied as the ONE choke point every response is
built through (`_build_result`) -- it recognizes Oracle/Python-exception
SHAPES (ORA-nnnnn, "Connection failed:", "Traceback", etc.) and replaces
them with a generic message, logging the real one server-side. A
validate_sql()-style plain-English reason still passes through unchanged,
preserving the existing "tell the caller what was wrong with the generated
SQL" behavior.

`db_sql` (the generated/stored SQL itself) is an intentional, legitimate
feature (confirmed live in frontend/src/components/MessageBubble.jsx) and is
deliberately left untouched -- M-07 is about db_error, not db_sql.

These tests exercise the real _safe_client_error()/_build_result() directly,
plus handle_db_query() end-to-end for the error paths that matter.
"""
from __future__ import annotations

import asyncio

import backend.sql_agent  # noqa: F401  (runs _bootstrap.ensure(), puts `sqlcore` on sys.path)
from backend.sql_agent import query_handler as qh


class TestSafeClientError:
    def test_plain_validate_sql_reason_passes_through(self):
        reason = "Hallucinated columns (not in schema): ['fake_col']"
        assert qh._safe_client_error(reason) == reason

    def test_dangerous_keyword_reason_passes_through(self):
        reason = "Dangerous keyword detected: 'drop'"
        assert qh._safe_client_error(reason) == reason

    def test_none_passes_through(self):
        assert qh._safe_client_error(None) is None

    def test_empty_string_passes_through(self):
        assert qh._safe_client_error("") == ""

    def test_oracle_error_code_is_suppressed(self):
        raw = "ORA-00904: \"FAKE_COL\": invalid identifier"
        result = qh._safe_client_error(raw)
        assert "ORA-00904" not in result
        assert "FAKE_COL" not in result
        assert "database error occurred" in result.lower()

    def test_connection_failed_message_is_suppressed(self):
        raw = "Connection failed: ORA-12541: TNS:no listener at host db-internal.prod:1521"
        result = qh._safe_client_error(raw)
        assert "db-internal.prod" not in result
        assert "1521" not in result

    def test_query_execution_failed_message_is_suppressed(self):
        raw = "Query execution failed: ORA-00001: unique constraint violated"
        result = qh._safe_client_error(raw)
        assert "ORA-00001" not in result

    def test_unexpected_error_message_is_suppressed(self):
        raw = "Unexpected error: KeyError('schema_name')"
        result = qh._safe_client_error(raw)
        assert "KeyError" not in result

    def test_python_traceback_is_suppressed(self):
        raw = "Traceback (most recent call last):\n  File \"executor.py\", line 42, in execute_query"
        result = qh._safe_client_error(raw)
        assert "File \"executor.py\"" not in result
        assert "line 42" not in result

    def test_oracle_dry_run_rejection_message_is_suppressed(self):
        """The one real route an Oracle message could reach a `reason`
        string -- generate_sql()'s own internal dry-run check formats it as
        "Oracle rejected the query: {engine_error}"."""
        raw = "Oracle rejected the query: ORA-01861: literal does not match format string"
        result = qh._safe_client_error(raw)
        assert "ORA-01861" not in result


class TestBuildResultAppliesTheSanitizerUnconditionally:
    """The guarantee the task asked for: ANY call site, including ones that
    don't exist yet, gets sanitized -- not just the two known today."""

    def test_a_hypothetical_future_call_site_cannot_leak_a_raw_exception(self):
        result = qh._build_result(
            "oops", "db_result",
            db_error="Connection failed: ORA-12154: TNS could not resolve DB_HOST=10.0.0.5",
        )
        assert "10.0.0.5" not in result["db_error"]
        assert "ORA-12154" not in result["db_error"]

    def test_db_sql_is_never_touched_by_the_sanitizer(self):
        result = qh._build_result(
            "ok", "db_result",
            db_sql="SELECT code FROM cims_ale_q_anx_1_a",
            db_error=None,
        )
        assert result["db_sql"] == "SELECT code FROM cims_ale_q_anx_1_a"


class TestHandleDbQueryErrorPathsNeverLeak:
    def _patch_retrieval(self, monkeypatch, tables):
        monkeypatch.setattr(qh, "_retrieve", lambda query: (tables, [], [], (None, None), None))
        monkeypatch.setattr(qh, "_authorize_sql_agent_access", lambda login_id, tables: (True, None))

    def test_execute_query_raising_never_reaches_the_client(self, monkeypatch):
        self._patch_retrieval(monkeypatch, [{"table": "cims_ale_q_anx_1_a"}])
        import backend.sql_agent.sql_generator as sql_generator_shim
        import backend.sql_agent.executor as executor_shim
        monkeypatch.setattr(sql_generator_shim, "generate_sql", lambda *a, **k: {"sql": "SELECT code FROM cims_ale_q_anx_1_a", "warnings": []})
        monkeypatch.setattr(sql_generator_shim, "validate_sql", lambda sql, tables, columns: (True, "Valid"))

        def _boom(sql):
            raise RuntimeError("oracledb.DatabaseError: ORA-12541: TNS:no listener at secret-db-host:1521")
        monkeypatch.setattr(executor_shim, "execute_query", _boom)

        result = asyncio.run(qh.handle_db_query("show me the total outstanding please", login_id="any"))
        assert "secret-db-host" not in result["response_text"]
        assert result["db_error"] is None  # already-correct behavior, confirmed unchanged

    def test_execute_query_returning_an_error_string_never_reaches_the_client(self, monkeypatch):
        self._patch_retrieval(monkeypatch, [{"table": "cims_ale_q_anx_1_a"}])
        import backend.sql_agent.sql_generator as sql_generator_shim
        import backend.sql_agent.executor as executor_shim
        monkeypatch.setattr(sql_generator_shim, "generate_sql", lambda *a, **k: {"sql": "SELECT code FROM cims_ale_q_anx_1_a", "warnings": []})
        monkeypatch.setattr(sql_generator_shim, "validate_sql", lambda sql, tables, columns: (True, "Valid"))
        monkeypatch.setattr(
            executor_shim, "execute_query",
            lambda sql: ([], [], "Connection failed: ORA-12154: TNS could not resolve DB_HOST=10.0.0.5"),
        )

        result = asyncio.run(qh.handle_db_query("show me the total outstanding please", login_id="any"))
        assert "10.0.0.5" not in result["response_text"]
        assert result["db_error"] is None

    def test_validate_sql_rejection_still_surfaces_its_plain_reason(self, monkeypatch):
        """Confirms the sanitizer does NOT break the legitimate, existing
        behavior of telling the caller why the generated SQL was rejected."""
        self._patch_retrieval(monkeypatch, [{"table": "cims_ale_q_anx_1_a"}])
        import backend.sql_agent.sql_generator as sql_generator_shim
        monkeypatch.setattr(sql_generator_shim, "generate_sql", lambda *a, **k: {"sql": "SELECT fake_col FROM cims_ale_q_anx_1_a", "warnings": []})
        monkeypatch.setattr(
            sql_generator_shim, "validate_sql",
            lambda sql, tables, columns: (False, "Hallucinated columns (not in schema): ['fake_col']"),
        )

        result = asyncio.run(qh.handle_db_query("show me the fake column please", login_id="any"))
        assert result["db_error"] == "Hallucinated columns (not in schema): ['fake_col']"

    def test_successful_response_still_includes_db_sql(self, monkeypatch):
        self._patch_retrieval(monkeypatch, [{"table": "cims_ale_q_anx_1_a"}])
        import backend.sql_agent.sql_generator as sql_generator_shim
        import backend.sql_agent.executor as executor_shim
        monkeypatch.setattr(sql_generator_shim, "generate_sql", lambda *a, **k: {"sql": "SELECT code FROM cims_ale_q_anx_1_a", "warnings": []})
        monkeypatch.setattr(sql_generator_shim, "validate_sql", lambda sql, tables, columns: (True, "Valid"))
        monkeypatch.setattr(executor_shim, "execute_query", lambda sql: (["CODE"], [("X",)], None))

        result = asyncio.run(qh.handle_db_query("show me the total please", login_id="any"))
        assert result["db_sql"] == "SELECT code FROM cims_ale_q_anx_1_a"
        assert result["db_rows"] == [["X"]]
        assert result["db_error"] is None
