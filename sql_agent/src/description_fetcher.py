"""
Fetches distinct DESCRIPTION (and ITEM / CATEGORY / MOVEMENT_FROM etc.) values
from Oracle for tables that use a text column as a row-label identifier.
Results are saved to output/description_samples.json and injected into the
LLM prompt so it can write accurate WHERE clauses.
"""

import json
import os

# Column names that act as row labels / identifiers in this schema
LABEL_COLUMNS = {
    "description",
    "item",
    "category",
    "movement_from",
    "movement_provision_npa",
    "movement_restructure_std_la",
    "risk_category",
    "industry_name",
    "period_delinquency",
    "country_brw_cuntr_party",
}

MAX_SAMPLES = 50          # max distinct values to fetch per table
OUTPUT_PATH = "output/description_samples.json"


def _get_connection():
    """Lazy import so the module can be imported without oracledb installed."""
    import oracledb
    from src.config import DB_HOST, DB_PORT, DB_SERVICE, DB_USER, DB_PASSWORD
    dsn = oracledb.makedsn(DB_HOST, DB_PORT, service_name=DB_SERVICE)
    return oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=dsn)


def fetch_and_save(schema_json_path="output/schema.json"):
    """
    Read schema.json, identify tables with label columns, query Oracle for
    distinct values, and write output/description_samples.json.

    Returns dict: { table_name: { col_name: [val1, val2, ...] } }
    """
    with open(schema_json_path) as f:
        schema = json.load(f)

    samples = {}

    try:
        conn = _get_connection()
    except Exception as e:
        print(f"  [description_fetcher] DB connection failed: {e}")
        return {}

    try:
        cursor = conn.cursor()
        for entry in schema:
            table = entry["table"].upper()
            col_names = [c["name"].lower() for c in entry["columns"]]
            label_cols_in_table = [c for c in col_names if c in LABEL_COLUMNS]

            if not label_cols_in_table:
                continue

            table_samples = {}
            for col in label_cols_in_table:
                try:
                    cursor.execute(
                        f"SELECT DISTINCT {col.upper()} FROM {table} "
                        f"WHERE {col.upper()} IS NOT NULL AND ROWNUM <= :max_rows",
                        {"max_rows": MAX_SAMPLES},
                    )
                    rows = cursor.fetchall()
                    values = [str(r[0]).strip() for r in rows if r[0]]
                    if values:
                        table_samples[col] = sorted(values)
                except Exception:
                    pass  # table may be empty or inaccessible

            if table_samples:
                samples[entry["table"]] = table_samples
                print(f"  ✓ {table}: sampled {sum(len(v) for v in table_samples.values())} values")

    finally:
        cursor.close()
        conn.close()

    os.makedirs("output", exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(samples, f, indent=2)

    print(f"\n  Saved → {OUTPUT_PATH}")
    return samples


def load_samples(path=OUTPUT_PATH):
    """Load previously fetched description samples. Returns {} if file missing."""
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


# ──────────────────────────────────────────────────────────────────────────────
# Row-label vector index helpers
# ──────────────────────────────────────────────────────────────────────────────

ROW_LABEL_INDEX_PATH = "output/row_label_index.faiss"
ROW_LABEL_META_PATH  = "output/row_label_meta.pkl"


def build_and_save_label_index(samples: dict | None = None):
    """
    Embed every distinct row-label value and persist a FAISS index so
    get_relevant_schema() can retrieve only the labels relevant to a query.

    Parameters
    ----------
    samples : dict, optional
        Pre-loaded samples dict.  If None, loads from OUTPUT_PATH.

    Returns the (index, records) tuple.
    """
    from src.vectorizer import build_row_label_index, save_index

    if samples is None:
        samples = load_samples()

    if not samples:
        print("  [label_index] No samples found — skipping row-label index build.")
        return None, []

    print(f"  [label_index] Building row-label FAISS index …")
    index, records = build_row_label_index(samples)

    if index is not None:
        os.makedirs("output", exist_ok=True)
        save_index(index, records, ROW_LABEL_INDEX_PATH, ROW_LABEL_META_PATH)
        print(f"  [label_index] ✓ Indexed {len(records)} label values → {ROW_LABEL_INDEX_PATH}")
    else:
        print("  [label_index] No records to index.")

    return index, records


def search_labels(query: str, table_names: set, top_k: int = 8) -> list:
    """
    Retrieve the top-k row-label values most semantically similar to *query*,
    restricted to the given *table_names*.

    Returns list of dicts: [{table, column, value}, ...]
    Falls back to an empty list if the index does not exist.
    """
    return [lbl for _, lbl in search_labels_with_scores(query, top_k=top_k * 3)
            if lbl["table"] in table_names][:top_k]


def search_labels_with_scores(query: str, top_k: int = 30) -> list:
    """
    Retrieve the top-k row-label values with their similarity scores,
    across ALL tables (no table filter).

    Returns list of (score, dict) where dict has keys: table, column, value.
    Falls back to an empty list if the index does not exist.
    """
    import faiss as _faiss
    import pickle
    import numpy as np
    from src.vectorizer import embed_query

    if not os.path.exists(ROW_LABEL_INDEX_PATH):
        return []

    index = _faiss.read_index(ROW_LABEL_INDEX_PATH)
    with open(ROW_LABEL_META_PATH, "rb") as f:
        meta = pickle.load(f)

    if not meta:
        return []

    q_vec = np.array([embed_query(query)], dtype="float32")
    effective_k = min(top_k, len(meta))
    distances, indices = index.search(q_vec, effective_k)

    results = []
    seen: set = set()
    for dist, i in zip(distances[0], indices[0]):
        if i == -1:
            continue
        rec = meta[i]
        key = (rec["table"], rec["column"], rec["value"])
        if key in seen:
            continue
        seen.add(key)
        results.append((float(dist), {
            "table": rec["table"],
            "column": rec["column"],
            "value": rec["value"],
        }))

    return results
