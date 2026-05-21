import json
import os
import sys

# Ensure the project root (IntegratedChatBot/) is on sys.path so that
# "backend.sql_agent.*" imports resolve when running this script directly.
_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_HERE)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Load .env from project root so DB/Ollama/Sarvam credentials are available
from dotenv import load_dotenv
load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))

from backend.sql_agent.parser import parse_sql_schema
from backend.sql_agent.formatter import build_schema_json, build_vector_records, load_descriptions
from backend.sql_agent.vectorizer import embed_documents, build_faiss_index, save_index
from backend.sql_agent.description_fetcher import fetch_and_save, build_and_save_label_index
from backend.sql_agent.executor import get_accessible_tables
from backend.sql_agent.config import FAISS_OUTPUT_DIR

# ── Paths ─────────────────────────────────────────────────────────────────────
_SCHEMA_SQL  = os.path.join(_HERE, "data", "schema.sql")
_SCHEMA_JSON = os.path.join(FAISS_OUTPUT_DIR, "schema.json")
os.makedirs(FAISS_OUTPUT_DIR, exist_ok=True)

# Load DDL
print("[1/6] Parsing schema SQL...")
with open(_SCHEMA_SQL) as f:
    sql_text = f.read()

# Parse
tables = parse_sql_schema(sql_text)
print(f"      → {len(tables)} tables parsed from DDL")

# Cross-check against the live Oracle database
print("[1/6] Fetching accessible tables from Oracle...")
accessible = get_accessible_tables()
if accessible:
    before = len(tables)
    tables = {t: cols for t, cols in tables.items() if t.upper() in accessible}
    removed = before - len(tables)
    print(f"      → {len(tables)} tables exist in Oracle  ({removed} DDL-only tables excluded)")
else:
    print("      → Could not reach Oracle; using all DDL tables (ORA-00942 risk)")

# Load column descriptions from the JSON-formatted mapping file
print("[2/6] Loading column descriptions from mapping file...")
descriptions = load_descriptions(os.path.join(_HERE, "data", ".json-formatted"))
print(f"      → {len(descriptions)} column mappings loaded")

# Format JSON (enriched with excel_name, db_name, return_name from descriptions)
print("[3/6] Building enriched schema.json...")
schema_json = build_schema_json(tables, descriptions=descriptions)

with open(_SCHEMA_JSON, "w") as f:
    json.dump(schema_json, f, indent=2)
print(f"      → {_SCHEMA_JSON} written ({len(schema_json)} tables)")

# Vector records
table_records, column_records = build_vector_records(schema_json)
print(f"      → {len(table_records)} table records, {len(column_records)} column records")

# Embed
print("[4/6] Embedding table records...")
table_vecs = embed_documents([t["text"] for t in table_records])
print("[4/6] Embedding column records...")
column_vecs = embed_documents([c["text"] for c in column_records])

# Index
print("[5/6] Building FAISS indexes...")
table_index  = build_faiss_index(table_vecs)
column_index = build_faiss_index(column_vecs)

# Save
from backend.sql_agent.config import (
    TABLE_INDEX_PATH, TABLE_META_PATH,
    COLUMN_INDEX_PATH, COLUMN_META_PATH,
)
save_index(table_index,  table_records,  TABLE_INDEX_PATH,  TABLE_META_PATH)
save_index(column_index, column_records, COLUMN_INDEX_PATH, COLUMN_META_PATH)

print("✅ L1 Vector DB (tables + columns) built successfully")

# ── L2 — Fetch distinct row-label values from Oracle ─────────────────────────
print("\n[5/6] Fetching row-label samples from Oracle DB...")
samples = fetch_and_save(_SCHEMA_JSON)

# ── L3 — Embed row-label values into a third FAISS index ─────────────────────
print("\n[6/6] Building row-label embedding index...")
build_and_save_label_index(samples)

print("\n✅ All indexes built successfully")

# Load DDL
print("[1/6] Parsing schema SQL...")
with open("data/schema.sql") as f:
    sql_text = f.read()

# Parse
tables = parse_sql_schema(sql_text)
print(f"      → {len(tables)} tables parsed from DDL")

# Cross-check against the live Oracle database — only embed tables that
# actually exist so the LLM never generates SQL for ghost tables.
print("[1/6] Fetching accessible tables from Oracle...")
accessible = get_accessible_tables()
if accessible:
    before = len(tables)
    tables = {t: cols for t, cols in tables.items() if t.upper() in accessible}
    removed = before - len(tables)
    print(f"      → {len(tables)} tables exist in Oracle  ({removed} DDL-only tables excluded)")
else:
    print("      → Could not reach Oracle; using all DDL tables (ORA-00942 risk)")

# Load column descriptions from the JSON-formatted mapping file
print("[2/6] Loading column descriptions from mapping file...")
descriptions = load_descriptions("data/.json-formatted")
print(f"      → {len(descriptions)} column mappings loaded")

# Format JSON (enriched with excel_name, db_name, return_name from descriptions)
print("[3/6] Building enriched schema.json...")
schema_json = build_schema_json(tables, descriptions=descriptions)

with open("output/schema.json", "w") as f:
    json.dump(schema_json, f, indent=2)
print(f"      → output/schema.json written ({len(schema_json)} tables)")

# Vector records
table_records, column_records = build_vector_records(schema_json)
print(f"      → {len(table_records)} table records, {len(column_records)} column records")

# Embed
print("[4/6] Embedding table records...")
table_vecs = embed_documents([t["text"] for t in table_records])
print("[4/6] Embedding column records...")
column_vecs = embed_documents([c["text"] for c in column_records])

# Index
print("[5/6] Building FAISS indexes...")
table_index = build_faiss_index(table_vecs)
column_index = build_faiss_index(column_vecs)

# Save
save_index(table_index, table_records, "output/table_index.faiss", "output/table_meta.pkl")
save_index(column_index, column_records, "output/column_index.faiss", "output/column_meta.pkl")

print("✅ L1 Vector DB (tables + columns) built successfully")

# ── L2 — Fetch distinct row-label values from Oracle ─────────────────────────
print("\n[5/6] Fetching row-label samples from Oracle DB...")
samples = fetch_and_save("output/schema.json")

# ── L3 — Embed row-label values into a third FAISS index ─────────────────────
print("\n[6/6] Building row-label embedding index...")
build_and_save_label_index(samples)

print("\n✅ All indexes built successfully")