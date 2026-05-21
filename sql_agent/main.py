import json
from src.parser import parse_sql_schema
from src.formatter import build_schema_json, build_vector_records, load_descriptions
from src.vectorizer import embed_documents, build_faiss_index, save_index
from src.description_fetcher import fetch_and_save, build_and_save_label_index
from src.executor import get_accessible_tables

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