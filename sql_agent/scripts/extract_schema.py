"""
Connects to Oracle DB using credentials from src/config.py,
extracts column metadata for all tables in the configured schema
via ALL_COLUMNS (avoids DBMS_METADATA LOB issues), reconstructs
single-line CREATE TABLE statements, and writes them to data/schema.sql.

Usage:
    python scripts/extract_schema.py
"""

import sys
import os
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import oracledb
from src.config import DB_HOST, DB_PORT, DB_SERVICE, DB_USER, DB_PASSWORD

SCHEMA = DB_USER.upper()
OUTPUT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "schema.sql")


def extract_schema():
    dsn = f"{DB_HOST}:{DB_PORT}/{DB_SERVICE}"
    print(f"Connecting to Oracle DB at {dsn} as {SCHEMA}...")

    with oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=dsn) as conn:
        cur = conn.cursor()

        # Single query for all columns — avoids per-table DBMS_METADATA LOB issues.
        # ALL_TAB_COLUMNS is the correct Oracle view (ALL_COLUMNS does not exist).
        cur.execute("""
            SELECT table_name, column_name,
                   data_type, data_length, data_precision, data_scale
            FROM   all_tab_columns
            WHERE  owner = :owner
            ORDER  BY table_name, column_id
        """, {"owner": SCHEMA})

        table_cols = defaultdict(list)
        for tname, cname, dtype, dlength, dprec, dscale in cur.fetchall():
            if dtype in ("VARCHAR2", "CHAR", "NVARCHAR2", "NCHAR"):
                type_str = f"{dtype}({dlength})"
            elif dtype == "NUMBER":
                if dprec is not None and dscale is not None and dscale != 0:
                    type_str = f"NUMBER({dprec},{dscale})"
                elif dprec is not None:
                    type_str = f"NUMBER({dprec})"
                else:
                    type_str = "NUMBER"
            else:
                type_str = dtype
            table_cols[tname].append(f'"{cname}" {type_str}')

        print(f"Found {len(table_cols)} tables in schema '{SCHEMA}'")

        now_str = datetime.now().strftime("%A-%B-%d-%Y")
        ddl_parts = [
            "--------------------------------------------------------\n"
            f"--  File created - {now_str}   \n"
            "--------------------------------------------------------\n"
        ]

        for tname in sorted(table_cols):
            cols_str = ", ".join(table_cols[tname])
            # No schema prefix — parser regex expects CREATE TABLE "TABLE" (...)
            ddl = f'CREATE TABLE "{tname}" ({cols_str});'
            ddl_parts.append(
                "--------------------------------------------------------\n"
                f"--  DDL for Table {tname}\n"
                "--------------------------------------------------------\n\n"
                f"  {ddl}\n"
            )
            print(f"  ✓ {tname}")

        with open(OUTPUT_PATH, "w", encoding="utf-8") as fh:
            fh.write("\n".join(ddl_parts))

    print(f"\n✅ Schema extracted → {OUTPUT_PATH}  ({len(table_cols)} tables)")


if __name__ == "__main__":
    extract_schema()
