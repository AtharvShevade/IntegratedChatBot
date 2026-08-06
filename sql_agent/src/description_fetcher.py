"""
Fetches distinct DESCRIPTION (and ITEM / CATEGORY / MOVEMENT_FROM etc.) values
from Oracle for tables that use a text column as a row-label identifier.
Results are saved to output/description_samples.json and injected into the
LLM prompt so it can write accurate WHERE clauses.
"""

import json
import os
import src.config as config

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

# This regulatory schema reuses the same handful of "row is a named category"
# concepts across hundreds of tables, but with per-table naming variants
# (e.g. "memorandum_item", "category_investment_dom_opr") that an exact-match
# set silently misses — the table then gets ZERO row-label coverage even
# though it has an obvious label column. Substring keywords catch those
# variants; kept as a fallback (checked only if the exact set misses) so this
# stays a superset, not a behavior change for anything already matched.
_LABEL_KEYWORDS = ("description", "item", "category", "movement", "industry_name", "period_delinquency", "country")


def _is_label_column(col_name: str) -> bool:
    return col_name in LABEL_COLUMNS or any(kw in col_name for kw in _LABEL_KEYWORDS)


MAX_SAMPLES = 50          # max distinct values to fetch per table


def _output_path():
    return f"{config.EMBEDDING_DIR}/description_samples.json"


def _row_label_index_path():
    return f"{config.EMBEDDING_DIR}/row_label_index.faiss"


def _row_label_meta_path():
    return f"{config.EMBEDDING_DIR}/row_label_meta.pkl"


def _get_connection():
    """Lazy import so the module can be imported without oracledb installed."""
    import oracledb
    from src.config import DB_HOST, DB_PORT, DB_SERVICE, DB_USER, DB_PASSWORD
    dsn = oracledb.makedsn(DB_HOST, DB_PORT, service_name=DB_SERVICE)
    return oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=dsn)


def fetch_and_save(schema_json_path=None):
    """
    Read schema.json, identify tables with label columns, query Oracle for
    distinct values, and write description_samples.json under
    config.EMBEDDING_DIR (read at call time, so switching EMBEDDING_DIR —
    e.g. via env var — before calling this actually takes effect).

    Returns dict: { table_name: { col_name: [val1, val2, ...] } }
    """
    if schema_json_path is None:
        schema_json_path = f"{config.EMBEDDING_DIR}/schema.json"

    with open(schema_json_path) as f:
        schema = json.load(f)

    samples = {}
    # {table: [label_column, ...]} for columns whose stored values have leading
    # or trailing whitespace, so generated filters must use TRIM().
    needs_trim = {}

    try:
        conn = _get_connection()
    except Exception as e:
        print(f"  [description_fetcher] DB connection failed: {e}")
        return {}

    try:
        cursor = conn.cursor()
        for entry in schema:
            table_name = entry.get("table") or entry.get("table_name")
            table = table_name.upper()
            col_names = [(c.get("name") or c.get("column_name")).lower() for c in entry["columns"]]
            label_cols_in_table = [c for c in col_names if _is_label_column(c)]

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
                    # Keep the value EXACTLY as stored. Stripping it here was a
                    # silent wrong-answer bug: several values carry leading
                    # whitespace ('     C2. Slipped to NPAs'), so a filter built
                    # from the stripped sample — WHERE COL = 'C2. Slipped to
                    # NPAs' — matches zero rows and returns an empty result with
                    # no error at all. Values whose stored form differs from
                    # their trimmed form are recorded in _needs_trim so the
                    # prompt can emit TRIM(COL) = '...' instead.
                    raw_values = [str(r[0]) for r in rows if r[0]]
                    values = [v for v in raw_values if v.strip()]
                    if values:
                        table_samples[col] = sorted(values)
                        if any(v != v.strip() for v in values):
                            needs_trim.setdefault(table_name, []).append(col)
                except Exception:
                    pass  # table may be empty, inaccessible, or not yet in the DB

            if table_samples:
                samples[table_name] = table_samples
                print(f"  [ok] {table}: sampled {sum(len(v) for v in table_samples.values())} values")
            else:
                print(f"  [--] {table}: no live label samples (table absent or empty)")

    finally:
        cursor.close()
        conn.close()

    out_path = _output_path()
    os.makedirs(config.EMBEDDING_DIR, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(samples, f, indent=2)

    print(f"\n  Saved -> {out_path}")

    if needs_trim:
        trim_path = os.path.join(config.EMBEDDING_DIR, "needs_trim.json")
        with open(trim_path, "w", encoding="utf-8") as f:
            json.dump(needs_trim, f, indent=2)
        print(f"  Saved -> {trim_path}  "
              f"({sum(len(v) for v in needs_trim.values())} column(s) need TRIM())")

    # These files were just rewritten, so anything this process cached from the
    # previous version is now stale.
    from src import schema_store
    schema_store.clear_cache()

    return samples


def load_needs_trim(path=None):
    """
    {table_lower: {label_column_lower, ...}} for label columns whose stored
    values are whitespace-padded, written by fetch_and_save.

    Consumed by the context slicer, which combines it with a live padding check
    over the sampled values — the two sources disagree when the file is stale or
    absent, and a missed TRIM() is a silent empty result rather than an error.
    Returns {} when absent.
    """
    from src import schema_store
    return schema_store.needs_trim(path)


def load_samples(path=None):
    """
    Load previously fetched description samples. Returns {} if file missing.

    Reads through src.schema_store's process-lifetime cache: this is called
    from the prompt builder and from validate_sql on every request, and used to
    re-parse the whole file each time. The returned dict is SHARED — do not
    mutate it.
    """
    from src import schema_store
    return schema_store.label_samples(path)


# ──────────────────────────────────────────────────────────────────────────────
# Row-label vector index helpers
# ──────────────────────────────────────────────────────────────────────────────


def build_and_save_label_index(samples: dict | None = None):
    """
    Embed every distinct row-label value and persist a FAISS index so
    get_relevant_schema() can retrieve only the labels relevant to a query.

    Parameters
    ----------
    samples : dict, optional
        Pre-loaded samples dict.  If None, loads from the current
        config.EMBEDDING_DIR's description_samples.json.

    Returns the (index, records) tuple.
    """
    from src.vectorizer import build_row_label_index, save_index

    if samples is None:
        samples = load_samples()

    if not samples:
        print("  [label_index] No samples found — skipping row-label index build.")
        return None, []

    print(f"  [label_index] Building row-label FAISS index ...")
    index, records = build_row_label_index(samples)

    if index is not None:
        index_path, meta_path = _row_label_index_path(), _row_label_meta_path()
        os.makedirs(config.EMBEDDING_DIR, exist_ok=True)
        save_index(index, records, index_path, meta_path)
        print(f"  [label_index] Indexed {len(records)} label values -> {index_path}")
    else:
        print("  [label_index] No records to index.")

    return index, records


def search_labels(query_vec, table_names: set, top_k: int = 8) -> list:
    """
    Retrieve the top-k row-label values most semantically similar to the
    given PRE-COMPUTED query embedding, restricted to *table_names*.

    query_vec: embedding from src.vectorizer.embed_query (or
    src.retriever.compute_query_embedding) — callers should reuse the same
    vector already computed for the table/column search rather than
    re-embedding the same query text here.

    Returns list of dicts: [{table, column, value}, ...]
    Falls back to an empty list if the index does not exist.
    """
    return [lbl for _, lbl in search_labels_with_scores(query_vec, top_k=top_k * 3)
            if lbl["table"] in table_names][:top_k]


# Cache of the loaded row-label FAISS index + metadata, keyed by
# (index_path, meta_path) — mirrors src.retriever._index_cache so this index
# is also loaded once instead of re-read from disk on every call.
# Cached for the life of the process — a rebuild needs a restart to take effect.
_label_index_cache: dict = {}


def search_labels_with_scores(query_vec, top_k: int = 30) -> list:
    """
    Retrieve the top-k row-label values with their similarity scores,
    across ALL tables (no table filter), using a PRE-COMPUTED query
    embedding (see search_labels docstring).

    Returns list of (score, dict) where dict has keys: table, column, value.
    Falls back to an empty list if the index does not exist.
    """
    import faiss as _faiss
    import pickle
    import numpy as np

    index_path, meta_path = _row_label_index_path(), _row_label_meta_path()
    cache_key = (index_path, meta_path)
    if cache_key not in _label_index_cache:
        if not os.path.exists(index_path):
            _label_index_cache[cache_key] = (None, [])
        else:
            index = _faiss.read_index(index_path)
            with open(meta_path, "rb") as f:
                meta = pickle.load(f)
            _label_index_cache[cache_key] = (index, meta)
    index, meta = _label_index_cache[cache_key]

    if index is None or not meta:
        return []

    q_vec = np.asarray(query_vec, dtype="float32").reshape(1, -1)
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
