"""
Builds vector embeddings (tables, columns, row-labels) for the scoped
CIMS_RAQ(Quarterly) schema.json produced by build_schema.py — everything
lands inside this folder, completely independent of the production
embedding_building/output/ indexes.

Run build_schema.py first. Then:
    python embedding_building/cims_raq_quarterly/build_embeddings.py
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEMA_PATH = os.path.join(OUT_DIR, "schema.json")

from embedding_building.formatter import build_vector_records
from src.vectorizer import embed_documents, build_faiss_index, save_index, build_row_label_index
from src.description_fetcher import MAX_SAMPLES, _is_label_column


def fetch_row_label_samples(schema):
    """
    Same logic as src/description_fetcher.fetch_and_save, but scoped to this
    schema's tables and writing nowhere except the caller's return value (path is
    decided by the caller, not the shared EMBEDDING_DIR global).

    Returns (samples, needs_trim).

    Two bugs used to live in this copy, both because it reimplemented the shared
    logic instead of reusing it:

      * It matched only the exact LABEL_COLUMNS set, missing per-table variants
        that _is_label_column catches by substring — CATEGORY_INVESTMENT_DOM_OPR
        and MEMORANDUM_ITEM. Those two tables got no row labels at all, so the
        prompt never marked them VERTICAL and the model was free to SUM() across
        their label rows, double-counting the pre-aggregated total row.
      * It stripped sampled values, so a value stored as '     C2. Slipped to
        NPAs' was offered to the model without its padding and the resulting
        `= 'C2. Slipped to NPAs'` filter matched zero rows — silently, with no
        error. Values are now kept verbatim and padded columns are reported in
        needs_trim so the prompt can require TRIM().
    """
    import oracledb
    from src.config import DB_HOST, DB_PORT, DB_SERVICE, DB_USER, DB_PASSWORD

    samples = {}
    needs_trim = {}
    dsn = oracledb.makedsn(DB_HOST, DB_PORT, service_name=DB_SERVICE)
    try:
        conn = oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=dsn)
    except Exception as e:
        print(f"  [warn] DB connection failed: {e}")
        return {}, {}

    try:
        cursor = conn.cursor()
        for entry in schema:
            table = entry["table"].upper()
            col_names = [c["name"].lower() for c in entry["columns"]]
            label_cols = [c for c in col_names if _is_label_column(c)]
            if not label_cols:
                continue

            table_samples = {}
            for col in label_cols:
                try:
                    cursor.execute(
                        f"SELECT DISTINCT {col.upper()} FROM {table} "
                        f"WHERE {col.upper()} IS NOT NULL AND ROWNUM <= :max_rows",
                        {"max_rows": MAX_SAMPLES},
                    )
                    raw_values = [str(r[0]) for r in cursor.fetchall() if r[0]]
                    values = [v for v in raw_values if v.strip()]
                    if values:
                        table_samples[col] = sorted(values)
                        if any(v != v.strip() for v in values):
                            needs_trim.setdefault(entry["table"], []).append(col)
                except Exception:
                    pass

            if table_samples:
                samples[entry["table"]] = table_samples
                padded = [c for c in table_samples if c in (needs_trim.get(entry["table"]) or [])]
                note = f"  (TRIM needed: {', '.join(padded)})" if padded else ""
                print(f"  [ok] {table}: sampled {sum(len(v) for v in table_samples.values())} values{note}")
            else:
                print(f"  [--] {table}: no live label samples")
    finally:
        cursor.close()
        conn.close()

    return samples, needs_trim


def main():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        schema = json.load(f)
    print(f"Loaded {len(schema)} tables from {SCHEMA_PATH}\n")

    # ── Table + column embeddings ──────────────────────────────────────────
    table_records, column_records = build_vector_records(schema)
    print(f"Embedding {len(table_records)} table records...")
    table_vecs = embed_documents([t["text"] for t in table_records])
    table_index = build_faiss_index(table_vecs)
    save_index(table_index, table_records,
               os.path.join(OUT_DIR, "table_index.faiss"), os.path.join(OUT_DIR, "table_meta.pkl"))
    print(f"  -> table_index.faiss ({table_index.ntotal} vectors)\n")

    print(f"Embedding {len(column_records)} column records...")
    column_vecs = embed_documents([c["text"] for c in column_records])
    column_index = build_faiss_index(column_vecs)
    save_index(column_index, column_records,
               os.path.join(OUT_DIR, "column_index.faiss"), os.path.join(OUT_DIR, "column_meta.pkl"))
    print(f"  -> column_index.faiss ({column_index.ntotal} vectors)\n")

    # ── Row-label sampling + embedding ─────────────────────────────────────
    print(f"Fetching row-label samples from Oracle (scoped to these {len(schema)} tables)...")
    samples, needs_trim = fetch_row_label_samples(schema)
    with open(os.path.join(OUT_DIR, "description_samples.json"), "w", encoding="utf-8") as f:
        json.dump(samples, f, indent=2)
    print(f"  -> description_samples.json ({len(samples)} tables with samples)")

    # Always write needs_trim.json, even when empty: a stale file from an earlier
    # build would otherwise keep asking for TRIM() on columns that no longer need
    # it, and the prompt would carry an instruction that is simply wrong.
    trim_path = os.path.join(OUT_DIR, "needs_trim.json")
    with open(trim_path, "w", encoding="utf-8") as f:
        json.dump(needs_trim, f, indent=2)
    trim_count = sum(len(v) for v in needs_trim.values())
    print(f"  -> needs_trim.json ({trim_count} column(s) with whitespace-padded values)\n")

    if samples:
        print("Building row-label FAISS index...")
        label_index, label_records = build_row_label_index(samples)
        if label_index is not None:
            save_index(label_index, label_records,
                       os.path.join(OUT_DIR, "row_label_index.faiss"), os.path.join(OUT_DIR, "row_label_meta.pkl"))
            print(f"  -> row_label_index.faiss ({label_index.ntotal} vectors)")
    else:
        print("No row-label samples found — skipping row-label index.")

    print("\nDone.")


if __name__ == "__main__":
    main()
