"""
Build all FAISS indexes from schema.sql + .json-formatted mapping.

Run from the project root:
    python backend/sql_agent/main.py

Steps:
  1. Parse schema.sql  → table/column structure
  2. Cross-check against live Oracle (skips DDL-only ghost tables)
  3. Load .json-formatted  → excel_name / return_name per column
  4. Build enriched schema.json
  5. Embed table + column records → FAISS indexes (L1)
  6. Fetch distinct row-label values from Oracle → row-label FAISS index (L2/L3)
"""

import json
import os
import sys

# Ensure project root (IntegratedChatBot/) is on sys.path
_HERE         = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_HERE))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))

from backend.sql_agent.parser import parse_sql_schema
from backend.sql_agent.formatter import build_schema_json, build_vector_records, load_descriptions
from backend.sql_agent.vectorizer import embed_documents, build_faiss_index, save_index
from backend.sql_agent.description_fetcher import fetch_and_save, build_and_save_label_index
from backend.sql_agent.executor import get_accessible_tables
from backend.sql_agent.config import (
    FAISS_OUTPUT_DIR,
    SQL_AGENT_DATA_DIR,
    TABLE_INDEX_PATH,  TABLE_META_PATH,
    COLUMN_INDEX_PATH, COLUMN_META_PATH,
)

# ── Paths ──────────────────────────────────────────────────────────────────────
_SCHEMA_SQL  = os.path.join(SQL_AGENT_DATA_DIR, "schema.sql")
_MAP_FILE    = os.path.join(SQL_AGENT_DATA_DIR, ".json-formatted")
_SCHEMA_JSON = os.path.join(FAISS_OUTPUT_DIR, "schema.json")
os.makedirs(FAISS_OUTPUT_DIR, exist_ok=True)

# ── [1/6] Parse DDL ────────────────────────────────────────────────────────────
print("[1/6] Parsing schema SQL...")
with open(_SCHEMA_SQL) as f:
    sql_text = f.read()

tables = parse_sql_schema(sql_text)
print(f"      → {len(tables)} tables parsed from DDL")

# ── [1/6] Cross-check against live Oracle ──────────────────────────────────────
print("[1/6] Fetching accessible tables from Oracle...")
accessible = get_accessible_tables()
if accessible:
    before = len(tables)
    tables = {t: cols for t, cols in tables.items() if t.upper() in accessible}
    print(f"      → {len(tables)} tables exist in Oracle  ({before - len(tables)} DDL-only excluded)")
else:
    print("      → Could not reach Oracle; using all DDL tables (ORA-00942 risk)")

# ── [2/6] Load column descriptions ────────────────────────────────────────────
print("[2/6] Loading column descriptions from mapping file...")
descriptions = load_descriptions(_MAP_FILE)
print(f"      → {len(descriptions)} column mappings loaded")

# ── [3/6] Build enriched schema.json ──────────────────────────────────────────
print("[3/6] Building enriched schema.json...")
schema_json = build_schema_json(tables, descriptions=descriptions)

with open(_SCHEMA_JSON, "w") as f:
    json.dump(schema_json, f, indent=2)
print(f"      → {_SCHEMA_JSON} written ({len(schema_json)} tables)")

# Vector records
table_records, column_records = build_vector_records(schema_json)
print(f"      → {len(table_records)} table records, {len(column_records)} column records")

# ── [4/6] Embed ────────────────────────────────────────────────────────────────
print("[4/6] Embedding table records...")
table_vecs = embed_documents([t["text"] for t in table_records])

print("[4/6] Embedding column records...")
column_vecs = embed_documents([c["text"] for c in column_records])

# ── [5/6] Build + save FAISS indexes ──────────────────────────────────────────
print("[5/6] Building FAISS indexes...")
save_index(build_faiss_index(table_vecs),  table_records,  TABLE_INDEX_PATH,  TABLE_META_PATH)
save_index(build_faiss_index(column_vecs), column_records, COLUMN_INDEX_PATH, COLUMN_META_PATH)

print("✅ L1 Vector DB (tables + columns) built successfully")

# ── [5/6] Fetch row-label samples from Oracle ──────────────────────────────────
print("\n[5/6] Fetching row-label samples from Oracle DB...")
samples = fetch_and_save(_SCHEMA_JSON)

# ── [6/6] Build row-label FAISS index ─────────────────────────────────────────
print("\n[6/6] Building row-label embedding index...")
build_and_save_label_index(samples)

print("\n✅ All indexes built successfully")
