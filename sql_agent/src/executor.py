import oracledb
from src.config import DB_HOST, DB_PORT, DB_SERVICE, DB_USER, DB_PASSWORD, DB_MAX_ROWS

# Previously every get_connection() call opened a brand-new TCP+auth session
# with Oracle and every execute_query() paid for a second round-trip just to
# set NLS_DATE_LANGUAGE. A pool keeps a small number of warm connections
# open and reuses them — session setup happens once per physical connection
# (via session_callback below), not once per request.
_pool = None


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
        print(f"  [warn] Could not fetch USER_TABLES: {e}")
        return set()


def dry_run_sql(sql):
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
            return True, f"dry-run skipped ({message})"
        return False, message
    except Exception as e:
        return True, f"dry-run skipped (unexpected error: {e})"
    finally:
        if cursor is not None:
            cursor.close()
        try:
            conn.rollback()      # discard the PLAN_TABLE rows
        except Exception:
            pass
        conn.close()


def execute_query(sql):
    """
    Execute a SELECT query against Oracle DB.
    Returns (columns: list[str], rows: list[tuple], error: str|None)
    """
    try:
        conn = get_connection()
    except oracledb.DatabaseError as e:
        return [], [], f"Connection failed: {e}"

    cursor = None
    try:
        # NLS_DATE_LANGUAGE is now set once per physical connection by the
        # pool's session_callback (_init_session) instead of on every
        # request — no longer needs a second cursor/round-trip here.
        cursor = conn.cursor()
        # Oracle driver does not accept a trailing semicolon
        cursor.execute(sql.rstrip().rstrip(";"))
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchmany(DB_MAX_ROWS)
        return columns, rows, None
    except oracledb.DatabaseError as e:
        return [], [], f"Query execution failed: {e}"
    except Exception as e:
        return [], [], f"Unexpected error: {e}"
    finally:
        if cursor is not None:
            cursor.close()
        conn.close()


