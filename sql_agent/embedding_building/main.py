import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
OUTPUT_DIR = os.path.join(ROOT, "embedding_building", "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

from embedding_building.parser import parse_schema_and_constraints
from embedding_building.formatter import build_schema_json, build_vector_records, load_descriptions
from src.vectorizer import embed_documents, build_faiss_index, save_index
from src.description_fetcher import fetch_and_save, build_and_save_label_index
from src.executor import get_accessible_tables

# Load DDL
print("[1/6] Parsing schema SQL...")
with open(os.path.join(ROOT, "data", "schema.sql")) as f:
    sql_text = f.read()

# Parse. Constraints come from the DDL when it declares any; Oracle is the
# authoritative source, so extract_constraints.py output is preferred below.
tables, constraints = parse_schema_and_constraints(sql_text)
print(f"      -> {len(tables)} tables parsed from DDL")

constraints_path = os.path.join(ROOT, "data", "constraints.json")
if os.path.exists(constraints_path):
    with open(constraints_path, encoding="utf-8") as f:
        constraints = json.load(f)
    print(f"      -> key metadata for {len(constraints)} tables from {constraints_path}")
elif constraints:
    print(f"      -> key metadata for {len(constraints)} tables from the DDL")
else:
    print("      -> no PK/FK declared; run embedding_building/extract_constraints.py")

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
descriptions = load_descriptions(os.path.join(ROOT, "data", ".json-formatted"))
print(f"      → {len(descriptions)} column mappings loaded")

# Format JSON (enriched with excel_name, db_name, return_name from descriptions)
print("[3/6] Building enriched schema.json...")
schema_json = build_schema_json(tables, descriptions=descriptions, constraints=constraints)

schema_json_path = os.path.join(OUTPUT_DIR, "schema.json")
with open(schema_json_path, "w") as f:
    json.dump(schema_json, f, indent=2)
print(f"      → {schema_json_path} written ({len(schema_json)} tables)")

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
save_index(table_index, table_records, os.path.join(OUTPUT_DIR, "table_index.faiss"), os.path.join(OUTPUT_DIR, "table_meta.pkl"))
save_index(column_index, column_records, os.path.join(OUTPUT_DIR, "column_index.faiss"), os.path.join(OUTPUT_DIR, "column_meta.pkl"))

print("✅ L1 Vector DB (tables + columns) built successfully")

# ── L2 — Fetch distinct row-label values from Oracle ─────────────────────────
print("\n[5/6] Fetching row-label samples from Oracle DB...")
samples = fetch_and_save(schema_json_path)

# ── L3 — Embed row-label values into a third FAISS index ─────────────────────
print("\n[6/6] Building row-label embedding index...")
build_and_save_label_index(samples)

print("\n✅ All indexes built successfully")