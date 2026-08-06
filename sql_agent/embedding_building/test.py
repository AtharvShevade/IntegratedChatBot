"""
test.py — Full automated pipeline to build the entire output/ folder.

Steps
-----
1. Extract Oracle schema   ->  data/schema.sql
2. Parse DDL + load descriptions  ->  output/schema.json
3. Embed tables & columns  ->  output/table_index.faiss / column_index.faiss
4. Fetch row-label samples ->  output/description_samples.json
5. Build row-label index   ->  output/row_label_index.faiss

Run:
    python test.py
"""

import sys
import json
import os

# Force UTF-8 output so Unicode characters don't crash on Windows consoles
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
DATA_DIR = os.path.join(ROOT, "data")
OUTPUT_DIR = os.path.join(ROOT, "embedding_building", "output")

# ── 0. Ensure output directory exists ───────────────────────────────────────
os.makedirs(OUTPUT_DIR, exist_ok=True)
print("=" * 60)
print("  SQL Query Gen — Full Build Pipeline")
print("=" * 60)

# ── 1. Extract Oracle schema to data/schema.sql ──────────────────────────────
print("\n[1/5] Extracting Oracle schema -> data/schema.sql ...")
from collections import defaultdict
from datetime import datetime
import oracledb
from src.config import DB_HOST, DB_PORT, DB_SERVICE, DB_USER, DB_PASSWORD

SCHEMA = DB_USER.upper()
dsn = f"{DB_HOST}:{DB_PORT}/{DB_SERVICE}"
print(f"       Connecting to {dsn} as {SCHEMA}")

try:
    with oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=dsn) as conn:
        cur = conn.cursor()

        # Single query — fetch all columns for all tables at once.
        # ALL_TAB_COLUMNS is the correct Oracle view (ALL_COLUMNS does not exist).
        # Avoids DBMS_METADATA LOB issues and dropped-connection errors.
        cur.execute("""
            SELECT table_name, column_name,
                   data_type, data_length, data_precision, data_scale
            FROM   all_tab_columns
            WHERE  owner = :owner
            ORDER  BY table_name, column_id
        """, {"owner": SCHEMA})

        table_cols = defaultdict(list)
        for tname, cname, dtype, dlength, dprec, dscale in cur.fetchall():
            # Rebuild the Oracle type string
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

        print(f"       Found {len(table_cols)} tables")

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

        with open(os.path.join(DATA_DIR, "schema.sql"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(ddl_parts))

    print(f"  OK schema.sql written  ({len(table_cols)} tables)")
except Exception as e:
    print(f"  WARNING DB connection failed: {e}")
    print("       Falling back to existing data/schema.sql")

# ── 2. Parse DDL + load descriptions → output/schema.json ───────────────────
print("\n[2/5] Building output/schema.json ...")
from embedding_building.parser import parse_sql_schema
from embedding_building.formatter import build_schema_json, build_vector_records, load_descriptions

with open(os.path.join(DATA_DIR, "schema.sql"), encoding="utf-8") as fh:
    sql_text = fh.read()

tables = parse_sql_schema(sql_text)
descriptions = load_descriptions(os.path.join(DATA_DIR, ".json-formatted"))
schema_json = build_schema_json(tables, descriptions=descriptions)

schema_json_path = os.path.join(OUTPUT_DIR, "schema.json")
with open(schema_json_path, "w", encoding="utf-8") as fh:
    json.dump(schema_json, fh, indent=2)

print(f"  OK schema.json written  ({len(schema_json)} tables)")

# ── 3. Embed + build FAISS indexes ──────────────────────────────────────────
print("\n[3/5] Building table & column vector indexes ...")
from src.vectorizer import embed_documents, build_faiss_index, save_index

if not schema_json:
    print("  WARNING schema.json is empty — skipping vector index build.")
    print("       Check that data/schema.sql was extracted correctly.")
    exit(1)

table_records, column_records = build_vector_records(schema_json)

print(f"       Embedding {len(table_records)} table records ...")
table_vecs = embed_documents([t["text"] for t in table_records])

print(f"       Embedding {len(column_records)} column records ...")
column_vecs = embed_documents([c["text"] for c in column_records])

table_index = build_faiss_index(table_vecs)
column_index = build_faiss_index(column_vecs)

save_index(table_index, table_records, os.path.join(OUTPUT_DIR, "table_index.faiss"), os.path.join(OUTPUT_DIR, "table_meta.pkl"))
save_index(column_index, column_records, os.path.join(OUTPUT_DIR, "column_index.faiss"), os.path.join(OUTPUT_DIR, "column_meta.pkl"))
print("  OK table_index.faiss + column_index.faiss saved")

# ── 4. Fetch row-label samples from Oracle ──────────────────────────────────
print("\n[4/5] Fetching row-label samples from Oracle ...")
from src.description_fetcher import fetch_and_save

samples = fetch_and_save(schema_json_path)
print(f"  OK description_samples.json saved  ({len(samples)} tables with samples)")

# ── 5. Build row-label FAISS index ──────────────────────────────────────────
print("\n[5/5] Building row-label embedding index ...")
from src.description_fetcher import build_and_save_label_index

build_and_save_label_index(samples)
print("  OK row_label_index.faiss saved")

# ── Done ─────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("  DONE  Output folder build complete!")
print("=" * 60)
print("\nFiles in output/:")
for f in sorted(os.listdir(OUTPUT_DIR)):
    size = os.path.getsize(os.path.join(OUTPUT_DIR, f))
    print(f"  {f:<40} {size:>10,} bytes")
