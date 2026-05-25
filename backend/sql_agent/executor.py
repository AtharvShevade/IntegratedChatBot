import oracledb
from backend.sql_agent.config import DB_HOST, DB_PORT, DB_SERVICE, DB_USER, DB_PASSWORD, DB_MAX_ROWS

# ── Connection pool ────────────────────────────────────────────────────────────
# Created once per process; each query acquires/releases a connection from the
# pool instead of opening a fresh TCP connection every time (~2s saved/query).
_pool: oracledb.ConnectionPool | None = None


def _nls_session_callback(conn, requested_tag, actual_tag):
    """
    Called by the pool once when a new physical connection is created.
    Sets NLS parameters so every pooled connection has the correct locale
    without re-running ALTER SESSION on every query.
    """
    cursor = conn.cursor()
    for stmt in [
        "ALTER SESSION SET NLS_DATE_LANGUAGE  = 'AMERICAN'",
        "ALTER SESSION SET NLS_DATE_FORMAT    = 'DD-MON-YYYY'",
        "ALTER SESSION SET NLS_NUMERIC_CHARACTERS = '.,'",
    ]:
        cursor.execute(stmt)
    cursor.close()


def _get_pool() -> oracledb.ConnectionPool:
    """Return the module-level pool, creating it on first call."""
    global _pool
    if _pool is None:
        dsn = oracledb.makedsn(DB_HOST, DB_PORT, service_name=DB_SERVICE)
        _pool = oracledb.create_pool(
            user=DB_USER,
            password=DB_PASSWORD,
            dsn=dsn,
            min=1,
            max=5,
            increment=1,
            session_callback=_nls_session_callback,
        )
    return _pool


def get_connection():
    """Acquire a connection from the pool (falls back to direct connect if pool fails)."""
    try:
        return _get_pool().acquire()
    except Exception:
        dsn = oracledb.makedsn(DB_HOST, DB_PORT, service_name=DB_SERVICE)
        return oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=dsn)


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
        cursor = conn.cursor()
        cursor.callTimeout = 60000  # 60-second statement timeout
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


def print_results(columns, rows):
    if not rows:
        print("  (no rows returned)")
        return

    # Calculate column widths
    widths = [len(c) for c in columns]
    for row in rows:
        for i, val in enumerate(row):
            widths[i] = max(widths[i], len(str(val) if val is not None else "NULL"))

    sep    = "+-" + "-+-".join("-" * w for w in widths) + "-+"
    header = "| " + " | ".join(c.ljust(widths[i]) for i, c in enumerate(columns)) + " |"

    print(sep)
    print(header)
    print(sep)
    for row in rows:
        print("| " + " | ".join((str(v) if v is not None else "NULL").ljust(widths[i]) for i, v in enumerate(row)) + " |")
    print(sep)
