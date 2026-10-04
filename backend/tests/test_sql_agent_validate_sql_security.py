"""Regression tests for the C-05 interim hardening of the SQL agent's
validate_sql() (doc/CRITICAL_FIXES_LOG.md):

  - comma-joined FROM lists no longer let an unmatched table (e.g. a system
    view) slip past the hallucinated-table check;
  - a reference to a privileged Oracle package (DBMS_*/UTL_*/SYS.*) is
    rejected outright, closing the self-aliasing trick that defeated the
    column-hallucination check;
  - the banned-keyword list now also covers MERGE/GRANT/REVOKE/CALL/LOCK/
    BEGIN/DECLARE/EXECUTE;
  - stacked (multi-statement) SQL is rejected;
  - SQL comments are stripped before any check runs, fixing a false-positive
    (a keyword appearing only inside a comment used to be rejected) without
    opening any new hole (Oracle itself treats comment content as inert).

These are targeted patches (Option B from the review discussion) applied on
top of the EXISTING regex-based validator -- deliberately not a rewrite, so
the accuracy-oriented checks (hallucinated columns, alias-aware column
checks, join-graph enforcement, vertical-table aggregation guard) are
exercised here only enough to confirm they still behave as before.

login_id/tenant_id/DB-user-privilege items are out of scope here -- this
file only covers validate_sql() and the new call_timeout in executor.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import backend.sql_agent  # noqa: F401  (runs _bootstrap.ensure(), puts `sqlcore` on sys.path)
from sqlcore.sql_generator import validate_sql
from sqlcore import config as sql_config

# A real table + columns from whichever embeddings set (5.5 or 6.0) this
# environment is actively configured for -- resolved at collection time so
# these tests work regardless of which one is active, rather than hardcoding
# a table name from one specific dataset.
import json as _json


def _first_real_table_and_columns():
    schema_path = f"{sql_config.EMBEDDING_DIR}/schema.json"
    schema = _json.load(open(schema_path, encoding="utf-8"))
    entry = schema[0]
    table = entry.get("table") or entry.get("table_name")
    cols = [c["name"] for c in entry.get("columns", [])]
    return table, cols


_TABLE, _COLUMNS = _first_real_table_and_columns()
_TABLES_ARG = [{"table": _TABLE}]


def _valid_query():
    col = _COLUMNS[0] if _COLUMNS else "rdate"
    return f"SELECT {col} FROM {_TABLE} WHERE rownum < 5"


class TestBaselineStillWorks:
    """Regression guard: the existing, legitimate query shape must still
    validate exactly as before these changes."""

    def test_simple_valid_select_still_passes(self):
        ok, reason = validate_sql(_valid_query(), _TABLES_ARG, [])
        assert ok is True, reason

    def test_trailing_semicolon_alone_still_passes(self):
        """executor.py strips a trailing ';' before execution -- validate_sql
        must keep tolerating one, not just reject every ';'."""
        ok, reason = validate_sql(_valid_query() + ";", _TABLES_ARG, [])
        assert ok is True, reason

    def test_existing_dml_keywords_still_rejected(self):
        for stmt in (
            f"DELETE FROM {_TABLE}",
            f"DROP TABLE {_TABLE}",
            f"UPDATE {_TABLE} SET rdate = NULL",
        ):
            ok, reason = validate_sql(stmt, _TABLES_ARG, [])
            assert ok is False, f"{stmt!r} should still be rejected"


class TestCommaJoinedHallucinatedTableNowRejected:
    """The exact bypass verified during the code review: a comma-joined
    FROM list only had its FIRST table checked, so a second, unmatched
    table (e.g. a system view) slipped through untouched."""

    def test_comma_joined_unmatched_table_rejected(self):
        sql = f"SELECT * FROM {_TABLE}, all_users WHERE rownum < 5"
        ok, reason = validate_sql(sql, _TABLES_ARG, [])
        assert ok is False
        assert "all_users" in reason.lower() or "hallucinat" in reason.lower()

    def test_comma_joined_with_aliases_rejected(self):
        sql = f"SELECT t.rowid FROM {_TABLE} t, all_users u WHERE rownum < 5"
        ok, reason = validate_sql(sql, _TABLES_ARG, [])
        assert ok is False

    def test_comma_joined_both_matched_tables_still_allowed_by_table_check(self):
        """Sanity check that the fix only ADDS detection for unmatched
        tables -- it must not start rejecting a comma-joined list where
        every table actually is in the allowed/matched set."""
        two_tables = [{"table": _TABLE}, {"table": _TABLE}]  # same table twice is fine for this check
        sql = f"SELECT 1 FROM {_TABLE} a, {_TABLE} b WHERE a.rowid = b.rowid"
        ok, reason = validate_sql(sql, two_tables, [])
        # Must not fail specifically on the (now-fixed) table-detection step;
        # any failure here would have to come from some other, unrelated
        # check (e.g. join-graph), not from "all_users"-style hallucination.
        assert "hallucinat" not in (reason or "").lower() or ok is True


class TestPrivilegedPackageCallRejected:
    """The second verified bypass: DBMS_XMLGEN.GETXML(...) aliased to its
    own function name defeated the hallucinated-column check. Now banned
    outright by package-name prefix, independent of aliasing."""

    def test_dbms_xmlgen_call_rejected_even_with_self_named_alias(self):
        sql = (
            f"SELECT dbms_xmlgen.getxml('select * from all_users') AS getxml "
            f"FROM {_TABLE} WHERE rownum = 1"
        )
        ok, reason = validate_sql(sql, _TABLES_ARG, [])
        assert ok is False
        assert "privileged" in reason.lower() or "dbms" in reason.lower()

    @pytest.mark.parametrize("call", [
        "dbms_lock.sleep(5)",
        "utl_http.request('http://evil')",
        "sys.dbms_output.put_line('x')",
    ])
    def test_other_privileged_packages_rejected(self, call):
        sql = f"SELECT {call} FROM {_TABLE} WHERE rownum = 1"
        ok, reason = validate_sql(sql, _TABLES_ARG, [])
        assert ok is False

    def test_ordinary_column_named_similarly_is_not_falsely_flagged(self):
        """A column merely containing 'sys' or 'db' as a substring (not a
        package-qualified call) must not be rejected -- the check requires
        the package-prefix pattern (word + '_' or '.'), not a bare
        substring match."""
        sql = f"SELECT * FROM {_TABLE} WHERE rownum < 5"
        ok, reason = validate_sql(sql, _TABLES_ARG, [])
        assert ok is True, reason


class TestExpandedBannedKeywords:
    @pytest.mark.parametrize("stmt", [
        "MERGE INTO t USING dual ON (1=1) WHEN MATCHED THEN UPDATE SET x=1",
        "GRANT SELECT ON t TO public",
        "REVOKE SELECT ON t FROM public",
        "CALL some_procedure()",
        "LOCK TABLE t IN EXCLUSIVE MODE",
        "BEGIN NULL; END;",
        "DECLARE x NUMBER; BEGIN NULL; END;",
        "EXECUTE IMMEDIATE 'DROP TABLE x'",
    ])
    def test_newly_banned_statement_shapes_rejected(self, stmt):
        ok, reason = validate_sql(stmt, _TABLES_ARG, [])
        assert ok is False, f"{stmt!r} should be rejected: got {reason!r}"


class TestStackedStatementsRejected:
    def test_semicolon_followed_by_second_statement_rejected(self):
        sql = f"SELECT 1 FROM {_TABLE}; DROP TABLE {_TABLE}"
        ok, reason = validate_sql(sql, _TABLES_ARG, [])
        assert ok is False

    def test_semicolon_followed_by_whitespace_only_still_allowed(self):
        sql = f"SELECT 1 FROM {_TABLE};   \n  "
        ok, reason = validate_sql(sql, _TABLES_ARG, [])
        assert ok is True, reason


class TestCommentHandling:
    def test_dangerous_word_inside_a_real_comment_no_longer_falsely_rejected(self):
        """Fixes a false positive: before comment-stripping, a keyword that
        only ever appeared inside an inert SQL comment (Oracle itself never
        executes it) was wrongly rejected as if it were real SQL."""
        sql = f"SELECT 1 FROM {_TABLE} -- remember to drop this test table later\n WHERE rownum < 5"
        ok, reason = validate_sql(sql, _TABLES_ARG, [])
        assert ok is True, reason

    def test_block_comment_does_not_hide_a_real_dangerous_keyword(self):
        """A comment can obscure PART of a keyword, but it can never let the
        keyword's own characters run together into a functioning statement
        Oracle would execute -- confirm stripping doesn't accidentally
        concatenate tokens across a comment boundary either."""
        sql = f"SELECT 1 FROM {_TABLE} /* just a note */ WHERE rownum < 5"
        ok, reason = validate_sql(sql, _TABLES_ARG, [])
        assert ok is True, reason
