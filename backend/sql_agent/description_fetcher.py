"""
Fetches distinct DESCRIPTION (and ITEM / CATEGORY / MOVEMENT_FROM etc.) values
from Oracle for tables that use a text column as a row-label identifier.
Results are saved to output/description_samples.json and injected into the
LLM prompt so it can write accurate WHERE clauses.
"""

import json
import os

from backend.sql_agent.config import (
    ROW_LABEL_INDEX_PATH,
    ROW_LABEL_META_PATH,
    DESC_SAMPLES_PATH,
    SCHEMA_JSON_PATH,
    FAISS_OUTPUT_DIR,
    COLUMN_TYPES_PATH,
)

# Column names that act as row labels / identifiers in this schema.
# Kept as a fast-path allowlist — most tables still match here without
# needing the Oracle metadata round-trip in _detect_label_columns().
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
    # Phase 5 additions — cover more vertical-format tables
    "particulars",
    "borrower_category",
    "sector",
    "activity",
    "exposure_type",
    "asset_type",
    "movement_from_npa",
    "sl_no_description",
    "assets",
}

# Columns that are structurally never row-labels, even though they may be
# CHAR/VARCHAR2 in Oracle (bank/report identifiers, not descriptive metrics).
NON_LABEL_COLUMNS = {
    "code", "rdate", "typeid", "type_id", "id", "sl_no", "return_code",
    # Free-text annotation fields can coincidentally have low cardinality in
    # a given data snapshot (e.g. mostly blank/NIL) and pass the cardinality
    # heuristic below, but they're never a real row-category axis — e.g.
    # CIMS_ALE_M_SEC2_D1.REMARK sampled as random test strings, not a fixed
    # enumerable label like its real label column DERIVATIVE. Including a
    # false-positive label column here also disables the single-label-column
    # deterministic autofix for tables that otherwise have exactly one.
    "remark", "remarks", "comment", "comments", "note", "notes",
    "narration", "description_text",
}

MAX_SAMPLES = 50          # max distinct values to keep per table in the final sample
_FETCH_POOL_CAP = 1000    # max distinct values to pull from Oracle before selecting from them

# Kept in sync with sql_generator._TOTAL_ROW_KEYWORDS. Duplicated here (rather
# than imported) to avoid a circular import — sql_generator already imports
# from this module. A row matching any of these is a "total/overall" row that
# the prompt and the deterministic vertical-format autofix both depend on
# being present; it must never be silently dropped by sample truncation.
_TOTAL_ROW_KEYWORDS = [
    "total", "grand total", "sub-total", "subtotal",
    "all industries", "c. total", "c total", "grand-total",
    "i. gross", "iii. non-food", "ii. food",
]

# Heuristic thresholds for detecting label columns not covered by the
# LABEL_COLUMNS whitelist (any text column whose distinct-value count is
# small relative to its row count behaves like a row-label, regardless of
# its name).
_LABEL_MAX_DISTINCT       = 200
_LABEL_MAX_DISTINCT_RATIO = 0.5


def _detect_label_columns(cursor, table: str, col_names: list[str]) -> list[str]:
    """
    Return columns in *table* that behave like row-labels: VARCHAR2/CHAR type,
    not a known identifier column, and with low cardinality relative to row
    count. Falls back to [] on any Oracle error (table missing/inaccessible).
    """
    candidates = [c for c in col_names if c not in NON_LABEL_COLUMNS]
    if not candidates:
        return []

    try:
        cursor.execute(
            "SELECT COLUMN_NAME FROM USER_TAB_COLUMNS "
            "WHERE TABLE_NAME = :t AND DATA_TYPE IN ('VARCHAR2', 'CHAR', 'NVARCHAR2', 'NCHAR')",
            {"t": table.upper()},
        )
        text_cols = {r[0].lower() for r in cursor.fetchall()}
    except Exception:
        return []

    text_candidates = [c for c in candidates if c in text_cols]
    if not text_candidates:
        return []

    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        row_count = cursor.fetchone()[0]
    except Exception:
        return []

    if row_count == 0:
        return []

    detected = []
    for col in text_candidates:
        try:
            cursor.execute(f"SELECT COUNT(DISTINCT {col.upper()}) FROM {table}")
            distinct_count = cursor.fetchone()[0]
        except Exception:
            continue
        if distinct_count == 0:
            continue
        if distinct_count <= _LABEL_MAX_DISTINCT and (distinct_count / row_count) <= _LABEL_MAX_DISTINCT_RATIO:
            detected.append(col)

    return detected


def _get_connection():
    """Lazy import so the module can be imported without oracledb installed."""
    import oracledb
    from backend.sql_agent.config import DB_HOST, DB_PORT, DB_SERVICE, DB_USER, DB_PASSWORD
    dsn = oracledb.makedsn(DB_HOST, DB_PORT, service_name=DB_SERVICE)
    return oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=dsn)


def fetch_and_save(schema_json_path=None):
    """
    Read schema.json, identify tables with label columns, query Oracle for
    distinct values, and write description_samples.json.

    Returns dict: { table_name: { col_name: [val1, val2, ...] } }
    """
    if schema_json_path is None:
        schema_json_path = SCHEMA_JSON_PATH

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

            # Whitelist miss? Fall back to the cardinality heuristic instead
            # of silently skipping the table (this is what left ~57% of
            # tables — e.g. anything using "assets" as its label column —
            # without any row-label samples at all).
            if not label_cols_in_table:
                label_cols_in_table = _detect_label_columns(cursor, table, col_names)

            if not label_cols_in_table:
                continue

            table_samples = {}
            for col in label_cols_in_table:
                try:
                    # Pull a larger pool first — selecting which MAX_SAMPLES
                    # to KEEP happens in Python below, so an arbitrary
                    # ROWNUM cutoff here can't silently drop the one row
                    # that matters (e.g. 'XX. Total Assets' sorting past
                    # position 50 out of 127 distinct values).
                    cursor.execute(
                        f"SELECT DISTINCT {col.upper()} FROM {table} "
                        f"WHERE {col.upper()} IS NOT NULL AND ROWNUM <= :max_rows",
                        {"max_rows": _FETCH_POOL_CAP},
                    )
                    rows = cursor.fetchall()
                    values = sorted({str(r[0]).strip() for r in rows if r[0]})
                    if not values:
                        continue

                    if len(values) <= MAX_SAMPLES:
                        table_samples[col] = values
                    else:
                        # Always keep total/overall-style rows regardless of
                        # where they'd sort, then fill the remaining budget.
                        is_total = lambda v: any(kw in v.lower() for kw in _TOTAL_ROW_KEYWORDS)
                        total_rows = [v for v in values if is_total(v)]
                        other_rows = [v for v in values if not is_total(v)]
                        fill = max(0, MAX_SAMPLES - len(total_rows))
                        table_samples[col] = sorted(total_rows + other_rows[:fill])
                except Exception:
                    pass  # table may be empty or inaccessible

            if table_samples:
                samples[entry["table"]] = table_samples
                # ASCII-only: Windows consoles default to cp1252, which can't
                # encode a checkmark and crashes the whole run before the
                # final json.dump() — this run is meant to complete cleanly
                # without needing PYTHONIOENCODING set.
                print(f"  [ok] {table}: sampled {sum(len(v) for v in table_samples.values())} values")

    finally:
        cursor.close()
        conn.close()

    os.makedirs(FAISS_OUTPUT_DIR, exist_ok=True)
    with open(DESC_SAMPLES_PATH, "w") as f:
        json.dump(samples, f, indent=2)

    print(f"\n  Saved → {DESC_SAMPLES_PATH}")
    return samples


def fetch_and_save_column_types(schema_json_path=None):
    """
    Bulk-fetch REAL Oracle column data types via USER_TAB_COLUMNS (one query)
    and cache them to column_types.json.

    Without this, the DDL prompt builder has to guess a column's Oracle type
    from schema.json alone (which carries no type info) — its fallback
    guess defaults an unsampled column to NUMBER, which is wrong for any
    text/label column that fetch_and_save() hasn't sampled yet and actively
    misleads the LLM into thinking it can SUM() a text column.

    Returns dict: { table_name: { col_name: {"data_type": ..., "data_length": ...} } }
    """
    try:
        conn = _get_connection()
    except Exception as e:
        print(f"  [description_fetcher] DB connection failed: {e}")
        return {}

    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, DATA_LENGTH FROM USER_TAB_COLUMNS"
        )
        rows = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    types: dict = {}
    for table_name, column_name, data_type, data_length in rows:
        types.setdefault(table_name.lower(), {})[column_name.lower()] = {
            "data_type":   data_type,
            "data_length": data_length,
        }

    os.makedirs(FAISS_OUTPUT_DIR, exist_ok=True)
    with open(COLUMN_TYPES_PATH, "w") as f:
        json.dump(types, f, indent=2)

    print(f"  [ok] Saved real column types for {len(types)} tables -> {COLUMN_TYPES_PATH}")
    return types


def load_column_types(path=None) -> dict:
    """Load previously fetched real Oracle column types. Returns {} if file missing."""
    if path is None:
        path = COLUMN_TYPES_PATH
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def load_samples(path=None):
    """Load previously fetched description samples. Returns {} if file missing."""
    if path is None:
        path = DESC_SAMPLES_PATH
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


# ──────────────────────────────────────────────────────────────────────────────
# Row-label vector index helpers
# ──────────────────────────────────────────────────────────────────────────────

def build_and_save_label_index(samples: dict | None = None):
    """
    Embed every distinct row-label value and persist a FAISS index so
    get_relevant_schema() can retrieve only the labels relevant to a query.
    """
    from backend.sql_agent.vectorizer import build_row_label_index, save_index

    if samples is None:
        samples = load_samples()

    if not samples:
        print("  [label_index] No samples found — skipping row-label index build.")
        return None, []

    print("  [label_index] Building row-label FAISS index …")
    index, records = build_row_label_index(samples)

    if index is not None:
        os.makedirs(FAISS_OUTPUT_DIR, exist_ok=True)
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
    from backend.sql_agent.vectorizer import embed_query

    if not os.path.exists(ROW_LABEL_INDEX_PATH):
        return []

    index = _faiss.read_index(ROW_LABEL_INDEX_PATH)
    with open(ROW_LABEL_META_PATH, "rb") as f:
        meta = pickle.load(f)

    if not meta:
        return []

    q_vec      = np.array([embed_query(query)], dtype="float32")
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
            "table":  rec["table"],
            "column": rec["column"],
            "value":  rec["value"],
        }))

    return results
