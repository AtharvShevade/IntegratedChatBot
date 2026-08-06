"""
Standalone DB connectivity check for src/config.py's DB_* settings.
Does not import anything else from the project (no oracledb dependency risk
on the rest of the pipeline) — just proves whether these credentials/host
are reachable right now, and reports basic facts about the connection.

Usage:
    python embedding_building/cims_raq_quarterly/check_db_connection.py
"""
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from src.config import DB_HOST, DB_PORT, DB_SERVICE, DB_USER, DB_PASSWORD


def main():
    import oracledb

    print(f"Connecting to {DB_HOST}:{DB_PORT}/{DB_SERVICE} as {DB_USER} ...")
    dsn = oracledb.makedsn(DB_HOST, DB_PORT, service_name=DB_SERVICE)

    try:
        conn = oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=dsn)
    except oracledb.DatabaseError as e:
        print(f"[FAIL] Could not connect: {e}")
        sys.exit(1)

    print("[ok] Connected.")
    cursor = conn.cursor()

    cursor.execute("SELECT sys_context('USERENV','DB_NAME') FROM dual")
    print("  DB_NAME:", cursor.fetchone()[0])

    cursor.execute("SELECT sys_context('USERENV','SERVER_HOST') FROM dual")
    print("  SERVER_HOST:", cursor.fetchone()[0])

    cursor.execute("SELECT COUNT(*) FROM USER_TABLES")
    print("  Tables owned by this user:", cursor.fetchone()[0])

    cursor.execute("SELECT table_name FROM USER_TABLES WHERE table_name LIKE 'CIMS_RAQ_Q_%' ORDER BY table_name")
    quarterly_tables = [r[0] for r in cursor.fetchall()]
    print(f"  CIMS_RAQ_Q_* tables live in this DB: {len(quarterly_tables)}")
    for t in quarterly_tables:
        print("    -", t)

    cursor.close()
    conn.close()
    print("\n[ok] DB_HOST/DB_PORT/DB_SERVICE/DB_USER/DB_PASSWORD in src/config.py are correct and reachable.")


if __name__ == "__main__":
    main()
