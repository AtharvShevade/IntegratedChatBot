"""
Adds the tables/columns described in an XBRL-resolver return JSON's
`semantic_description` block into this project's output/schema.json,
table_index.faiss, and column_index.faiss — WITHOUT rebuilding or touching
any existing entries.

Source of truth for what gets added: ONLY the `semantic_description` section
of the return JSON (overview/tables/columns), not the full resolved document.
The full document's per-concept db_mapping/axis/source_trace fields are
resolver bookkeeping, not embedding-suitable text.

Row-label (L3) embeddings are intentionally NOT built here — that requires
live Oracle sampling (src/description_fetcher.py), which is out of scope for
this script.

Usage:
    python embedding_building/add_return_schema.py <path-to-resolved-return.json>
"""

import json
import os
import pickle
import shutil
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import faiss

from src.vectorizer import embed_documents

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
SCHEMA_PATH = os.path.join(OUTPUT_DIR, "schema.json")
TABLE_INDEX_PATH = os.path.join(OUTPUT_DIR, "table_index.faiss")
TABLE_META_PATH = os.path.join(OUTPUT_DIR, "table_meta.pkl")
COLUMN_INDEX_PATH = os.path.join(OUTPUT_DIR, "column_index.faiss")
COLUMN_META_PATH = os.path.join(OUTPUT_DIR, "column_meta.pkl")


def _timestamped_backup(path: str, stamp: str) -> None:
    if os.path.exists(path):
        shutil.copy2(path, f"{path}.bak.{stamp}")


def add_return_schema(return_json_path: str) -> None:
    with open(return_json_path, encoding="utf-8") as fh:
        doc = json.load(fh)

    sem = doc.get("semantic_description")
    if not sem:
        raise SystemExit(f"{return_json_path} has no semantic_description — run the pipeline with --describe first.")

    return_meta = doc.get("return_metadata") or {}
    return_name = return_meta.get("return_code") or return_meta.get("return_id") or ""

    with open(SCHEMA_PATH, encoding="utf-8") as fh:
        schema = json.load(fh)
    existing_table_names = {t["table_name"] for t in schema}

    # Group semantic_description columns by table
    cols_by_table: dict = {}
    for col in sem.get("columns", []):
        cols_by_table.setdefault(col["table"], []).append(col)

    new_tables = [t for t in sem.get("tables", []) if t["table"] not in existing_table_names]
    if not new_tables:
        print("No new tables to add — every table in semantic_description already exists in schema.json.")
        return

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    new_schema_entries = []
    new_table_records = []
    new_column_records = []

    for t in new_tables:
        table_name = t["table"]
        table_desc = t.get("description", "")
        table_cols = cols_by_table.get(table_name, [])

        schema_entry = {
            "table_name": table_name,
            "table_description": table_desc,
            "return_name": return_name,
            "template_sheet_no": None,
            "isactive": 1,
            "scale": "",
            "columns": [
                {"column_name": c["column"], "column_description": c.get("description", "")}
                for c in table_cols
            ],
        }
        new_schema_entries.append(schema_entry)

        col_names = ", ".join(c["column"] for c in table_cols) or "(none)"
        new_table_records.append({
            "text": f"Table {table_name} includes columns such as {col_names}. {table_desc}",
            "table": table_name,
        })

        for c in table_cols:
            new_column_records.append({
                "text": f"Column {c['column']} in table {table_name}. {c.get('description', '')}",
                "table": table_name,
                "column": c["column"],
            })

    # ── Write schema.json (backup first) ──────────────────────────────────────
    _timestamped_backup(SCHEMA_PATH, stamp)
    schema.extend(new_schema_entries)
    with open(SCHEMA_PATH, "w", encoding="utf-8") as fh:
        json.dump(schema, fh, indent=2)
    print(f"schema.json: +{len(new_schema_entries)} tables (backup: schema.json.bak.{stamp})")

    # ── Embed + append to table_index.faiss / table_meta.pkl ──────────────────
    _timestamped_backup(TABLE_INDEX_PATH, stamp)
    _timestamped_backup(TABLE_META_PATH, stamp)

    table_index = faiss.read_index(TABLE_INDEX_PATH)
    with open(TABLE_META_PATH, "rb") as fh:
        table_meta = pickle.load(fh)

    table_vecs = embed_documents([r["text"] for r in new_table_records])
    table_index.add(table_vecs)
    table_meta.extend(new_table_records)

    faiss.write_index(table_index, TABLE_INDEX_PATH)
    with open(TABLE_META_PATH, "wb") as fh:
        pickle.dump(table_meta, fh)
    print(f"table_index.faiss: +{len(new_table_records)} vectors (total {table_index.ntotal})")

    # ── Embed + append to column_index.faiss / column_meta.pkl ────────────────
    _timestamped_backup(COLUMN_INDEX_PATH, stamp)
    _timestamped_backup(COLUMN_META_PATH, stamp)

    column_index = faiss.read_index(COLUMN_INDEX_PATH)
    with open(COLUMN_META_PATH, "rb") as fh:
        column_meta = pickle.load(fh)

    column_vecs = embed_documents([r["text"] for r in new_column_records])
    column_index.add(column_vecs)
    column_meta.extend(new_column_records)

    faiss.write_index(column_index, COLUMN_INDEX_PATH)
    with open(COLUMN_META_PATH, "wb") as fh:
        pickle.dump(column_meta, fh)
    print(f"column_index.faiss: +{len(new_column_records)} vectors (total {column_index.ntotal})")

    print(f"\nDone. Added tables: {', '.join(t['table'] for t in new_tables)}")
    print("Row-label (L3) embeddings were NOT built — that needs a live Oracle sample "
          "(src/description_fetcher.py) which this script does not run.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/add_return_schema.py <path-to-resolved-return.json>")
    add_return_schema(sys.argv[1])
