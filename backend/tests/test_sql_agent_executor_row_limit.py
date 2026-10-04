"""Regression tests for the H-08 fix (doc/CRITICAL_FIXES_LOG.md): executor.py's
execute_query() now wraps the validated statement in
"SELECT * FROM (<stmt>) FETCH FIRST {DB_MAX_ROWS + 1} ROWS ONLY" so Oracle's
own optimizer can short-circuit row production for ordinary queries, instead
of relying solely on the C-05 call_timeout to bound server-side cost -- and
truncation (previously silent) is now logged and detectable.

These need a live Oracle connection (this repo's own SQL agent has none of
its own tests otherwise -- see H-16) -- skipped automatically if the
configured DB isn't reachable, same pattern as the existing "real data tree
not present" skips elsewhere in this suite.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import backend.sql_agent  # noqa: F401  (runs _bootstrap.ensure(), puts `sqlcore` on sys.path)


def _oracle_reachable() -> bool:
    try:
        from sqlcore.executor import get_connection
        conn = get_connection()
        conn.close()
        return True
    except Exception:
        return False


_need_oracle = pytest.mark.skipif(not _oracle_reachable(), reason="configured Oracle DB not reachable")


@_need_oracle
class TestExecuteQueryRowLimit:
    def test_small_result_set_unaffected(self):
        from sqlcore.executor import execute_query
        cols, rows, err = execute_query("SELECT LEVEL AS n FROM dual CONNECT BY LEVEL <= 5")
        assert err is None
        assert cols == ["N"]
        assert len(rows) == 5
        assert [r[0] for r in rows] == [1, 2, 3, 4, 5]

    def test_result_set_larger_than_db_max_rows_is_truncated_and_logged(self, caplog):
        """Note: the OLD code (bare fetchmany(DB_MAX_ROWS)) also happened to
        return exactly DB_MAX_ROWS rows here, since a simple ascending
        CONNECT BY query's row order is unaffected either way -- so row
        count/values alone do NOT distinguish the fix from the old behavior
        for this synthetic query (the fix's real value is bounding
        server-side WORK for a query that can't stream, which fetchmany
        cannot demonstrate without a genuinely expensive live query). What
        DOES differ, and is asserted here: truncation is now detected and
        logged -- the old code never logged this at all."""
        from sqlcore.executor import execute_query
        from sqlcore.config import DB_MAX_ROWS

        with caplog.at_level("WARNING", logger="executor"):
            cols, rows, err = execute_query(
                f"SELECT LEVEL AS n FROM dual CONNECT BY LEVEL <= {DB_MAX_ROWS + 50}"
            )
        assert err is None
        assert len(rows) == DB_MAX_ROWS
        # FETCH FIRST preserves the inner query's natural row order -- the
        # truncated set must be rows 1..DB_MAX_ROWS, not an arbitrary subset.
        assert [r[0] for r in rows] == list(range(1, DB_MAX_ROWS + 1))
        assert any("truncated" in r.message for r in caplog.records)

    def test_result_set_exactly_at_the_limit_is_not_flagged_truncated(self, caplog):
        from sqlcore.executor import execute_query
        from sqlcore.config import DB_MAX_ROWS

        with caplog.at_level("WARNING", logger="executor"):
            cols, rows, err = execute_query(
                f"SELECT LEVEL AS n FROM dual CONNECT BY LEVEL <= {DB_MAX_ROWS}"
            )
        assert err is None
        assert len(rows) == DB_MAX_ROWS
        assert not any("truncated" in r.message for r in caplog.records)

    def test_wrapping_preserves_column_aliases(self):
        from sqlcore.executor import execute_query
        cols, rows, err = execute_query(
            "SELECT LEVEL AS my_custom_alias FROM dual CONNECT BY LEVEL <= 3"
        )
        assert err is None
        assert cols == ["MY_CUSTOM_ALIAS"]

    def test_order_by_inside_wrapped_query_is_respected(self):
        from sqlcore.executor import execute_query
        cols, rows, err = execute_query(
            "SELECT n FROM (SELECT LEVEL AS n FROM dual CONNECT BY LEVEL <= 5) ORDER BY n DESC"
        )
        assert err is None
        assert [r[0] for r in rows] == [5, 4, 3, 2, 1]
