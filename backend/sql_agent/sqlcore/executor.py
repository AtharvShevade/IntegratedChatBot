import logging
import threading
import time

import oracledb
from sqlcore.config import (
    DB_HOST, DB_PORT, DB_SERVICE, DB_USER, DB_PASSWORD, DB_MAX_ROWS,
    DB_STATEMENT_TIMEOUT_MS,
)

log = logging.getLogger("executor")

# Previously every get_connection() call opened a brand-new TCP+auth session
# with Oracle and every execute_query() paid for a second round-trip just to
# set NLS_DATE_LANGUAGE. A pool keeps a small number of warm connections
# open and reuses them — session setup happens once per physical connection
# (via session_callback below), not once per request.
_pool = None
# L-12: guards the lazy-init check-then-create below. Without this, two
# concurrent first callers could both see _pool is None and both call
# oracledb.create_pool(), leaking one pool's connections (never closed) and
# leaving _pool pointing at whichever pool was assigned last.
_pool_lock = threading.Lock()


def _init_session(connection, requested_tag):
    """Runs once per NEW physical connection the pool creates (not on every
    acquire of an already-warm one) — moves the per-request NLS ALTER
    SESSION cost out of the request path entirely."""
    cursor = connection.cursor()
    cursor.execute("ALTER SESSION SET NLS_DATE_LANGUAGE = 'AMERICAN'")
    cursor.close()


def _get_pool():
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:  # re-check: another thread may have just finished
                dsn = oracledb.makedsn(DB_HOST, DB_PORT, service_name=DB_SERVICE)
                _pool = oracledb.create_pool(
                    user=DB_USER, password=DB_PASSWORD, dsn=dsn,
                    min=2, max=10, increment=1,
                    session_callback=_init_session,
                )
    return _pool


def get_connection():
    """
    Acquire a connection from the shared pool. Callers should still call
    .close() on it as before — for a pooled connection this releases it back
    to the pool rather than tearing down the socket, so existing call sites
    (execute_query, get_accessible_tables) need no other changes.
    """
    return _get_pool().acquire()


def get_accessible_tables() -> set:
    """
    Query Oracle USER_TABLES to get the exact set of tables the connected
    user owns.  Used at index-build time to exclude DDL-only tables that
    don't exist in the live database.
    Returns a set of UPPERCASE table names.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT TABLE_NAME FROM USER_TABLES")
        tables = {row[0].upper() for row in cursor.fetchall()}
        cursor.close()
        conn.close()
        return tables
    except Exception as e:
        log.warning("Could not fetch USER_TABLES: %s", e)
        return set()


def dry_run_sql(sql):
    """Timed wrapper around _dry_run_sql — see that function's docstring.
    This round-trip previously had no latency visibility of its own; it was
    folded into whichever caller's [TIMING] block wrapped the whole retry
    round, so its cost (up to one per generation attempt) was invisible."""
    t0 = time.perf_counter()
    try:
        return _dry_run_sql(sql)
    finally:
        log.info("[TIMING] dry_run_sql total_ms=%.1f", (time.perf_counter() - t0) * 1000)


def _dry_run_sql(sql):
    """
    Ask Oracle to parse and plan the query without running it.

    Returns (ok: bool, error: str|None). ok=True means Oracle accepted the
    statement: every table and column exists, the types are comparable, and the
    syntax is valid for this dialect.

    This is the check the regex validator structurally cannot do. Real logged
    failures it catches that validate_sql() cannot: ORA-00904 for a plausible
    but nonexistent column, ORA-01861 for a string compared to a DATE, and
    comparing the NUMBER column CODE against a quoted literal.

    EXPLAIN PLAN is used rather than executing with a row limit because it costs
    no data access at all — Oracle parses, resolves names and produces a plan.
    The plan rows are written to PLAN_TABLE, so the transaction is rolled back
    afterwards; nothing is left behind and nothing is committed.

    A connection failure returns ok=True: the dry run is an accuracy gate, not
    an availability gate, and must never block generation when the DB is down.
    """
    statement = sql.rstrip().rstrip(";")
    if not statement:
        return False, "Empty SQL"

    try:
        conn = get_connection()
    except oracledb.DatabaseError as e:
        # Cannot verify — do not fail the query on infrastructure grounds.
        log.warning("[SQL_AGENT] dry_run_sql: connection unavailable, skipping validation: %s", e)
        return True, f"dry-run skipped (connection failed: {e})"

    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(f"EXPLAIN PLAN SET STATEMENT_ID = 'sqlgen_dryrun' FOR {statement}")
        return True, None
    except oracledb.DatabaseError as e:
        (error_obj,) = e.args
        message = getattr(error_obj, "message", str(e)).strip()
        if "ORA-01039" in message or "PLAN_TABLE" in message.upper():
            # No PLAN_TABLE or no privilege to write it: that is an environment
            # problem, not bad SQL, so it must not be reported as invalid.
            log.warning("[SQL_AGENT] dry_run_sql: PLAN_TABLE unavailable, skipping validation: %s", message)
            return True, f"dry-run skipped ({message})"
        log.warning("[SQL_AGENT] dry_run_sql rejected generated SQL: %s", message)
        return False, message
    except Exception as e:
        log.warning("[SQL_AGENT] dry_run_sql: unexpected error, skipping validation: %s", e, exc_info=True)
        return True, f"dry-run skipped (unexpected error: {e})"
    finally:
        if cursor is not None:
            cursor.close()
        try:
            conn.rollback()      # discard the PLAN_TABLE rows
        except Exception as exc:
            log.debug("[SQL_AGENT] dry_run_sql: rollback after EXPLAIN PLAN failed (non-critical): %s", exc)
        conn.close()


def execute_query(sql):
    """
    Execute a SELECT query against Oracle DB.
    Returns (columns: list[str], rows: list[tuple], error: str|None)

    Timed in three parts — connect (pool acquire), execute (Oracle actually
    running the query), fetch (pulling DB_MAX_ROWS back over the network) —
    because api/routes/query.py's `db_execution` timings_ms entry only ever
    showed the sum of all three, so a slow pool wait and a slow query looked
    identical from the response's timing breakdown.
    """
    t0 = time.perf_counter()
    try:
        conn = get_connection()
    except oracledb.DatabaseError as e:
        log.error("[SQL_AGENT] execute_query: connection failed after %.1fms: %s",
                  (time.perf_counter() - t0) * 1000, e)
        return [], [], f"Connection failed: {e}"
    connect_ms = (time.perf_counter() - t0) * 1000

    # C-05 hardening: bound how long Oracle may spend on this one statement,
    # independent of DB_MAX_ROWS (which only limits rows FETCHED back, not
    # work done server-side by a heavy join/aggregate that already passed
    # validate_sql()). Best-effort: if this driver/DB combo doesn't support
    # call_timeout, log and continue rather than failing the query over it.
    try:
        conn.call_timeout = DB_STATEMENT_TIMEOUT_MS
    except Exception as e:
        log.warning("[SQL_AGENT] execute_query: could not set call_timeout: %s", e)

    cursor = None
    try:
        # NLS_DATE_LANGUAGE is now set once per physical connection by the
        # pool's session_callback (_init_session) instead of on every
        # request — no longer needs a second cursor/round-trip here.
        cursor = conn.cursor()
        # Oracle driver does not accept a trailing semicolon
        statement = sql.rstrip().rstrip(";")
        # H-08 hardening: fetchmany(DB_MAX_ROWS) below only ever limited what
        # was FETCHED back over the network -- the statement itself still ran
        # to completion server-side first. Wrapping in FETCH FIRST lets
        # Oracle's own optimizer short-circuit row production for ordinary
        # (non-blocking-aggregate) queries instead of relying solely on
        # call_timeout (C-05) to bound cost. Fetch one extra row so
        # truncation can be detected and logged rather than silently
        # dropped, matching how DB_MAX_ROWS is already documented (100 max
        # rows) but was never actually surfaced anywhere before.
        wrapped_statement = (
            f"SELECT * FROM ({statement}) FETCH FIRST {DB_MAX_ROWS + 1} ROWS ONLY"
        )
        t1 = time.perf_counter()
        cursor.execute(wrapped_statement)
        execute_ms = (time.perf_counter() - t1) * 1000
        columns = [col[0] for col in cursor.description]
        t2 = time.perf_counter()
        rows = cursor.fetchall()
        fetch_ms = (time.perf_counter() - t2) * 1000
        truncated = len(rows) > DB_MAX_ROWS
        if truncated:
            rows = rows[:DB_MAX_ROWS]
            log.warning(
                "[SQL_AGENT] execute_query: result truncated to DB_MAX_ROWS=%d", DB_MAX_ROWS,
            )
        log.info(
            "[TIMING] execute_query connect_ms=%.1f execute_ms=%.1f fetch_ms=%.1f "
            "total_ms=%.1f rows=%d truncated=%s",
            connect_ms, execute_ms, fetch_ms,
            connect_ms + execute_ms + fetch_ms, len(rows), truncated,
        )
        return columns, rows, None
    except oracledb.DatabaseError as e:
        log.error(
            "[SQL_AGENT] execute_query: query execution failed after connect_ms=%.1f total_ms=%.1f: %s",
            connect_ms, (time.perf_counter() - t0) * 1000, e,
        )
        return [], [], f"Query execution failed: {e}"
    except Exception as e:
        log.error(
            "[SQL_AGENT] execute_query: unexpected error after connect_ms=%.1f total_ms=%.1f: %s",
            connect_ms, (time.perf_counter() - t0) * 1000, e, exc_info=True,
        )
        return [], [], f"Unexpected error: {e}"
    finally:
        if cursor is not None:
            cursor.close()
        conn.close()


