"""
Read-side access to description_samples.json / needs_trim.json / the
row-label FAISS index — all three are prebuilt artifacts shipped in
config.EMBEDDING_DIR and injected into the LLM prompt so it can write accurate
WHERE clauses.

This is a runtime-only trim of the dev repo's description_fetcher.py: the
write-side functions that query Oracle to (re)build these artifacts
(fetch_and_save, build_and_save_label_index) are build-time tooling and have
no place in a package that ships prebuilt artifacts — they live in the
development repo, not here.
"""

import json
import os
import src.config as config


def _output_path():
    return f"{config.EMBEDDING_DIR}/description_samples.json"


def _row_label_index_path():
    return f"{config.EMBEDDING_DIR}/row_label_index.faiss"


def _row_label_meta_path():
    return f"{config.EMBEDDING_DIR}/row_label_meta.pkl"


# Cache of parsed description_samples.json / needs_trim.json contents, keyed
# by path. Unlike every sibling data source in this codebase (FAISS indexes,
# BM25 index, concept_map, business_dictionary), these two were re-read and
# re-parsed from disk on EVERY call — and check_literal_validity() in
# literal_validator.py calls both on every SQL validation, so a single request
# (plus every retry) paid for this disk I/O + JSON parse repeatedly even
# though the underlying file never changes between requests. Cached for the
# life of the process — a re-fetch (fetch_and_save) needs a restart to be
# picked up, same caveat as the other module-level caches.
_needs_trim_cache: dict = {}
_samples_cache: dict = {}


def load_needs_trim(path=None):
    """
    {table: [label_column, ...]} for label columns whose stored values are
    whitespace-padded, written by fetch_and_save.

    Consumed by the prompt builder so it can tell the model to write
    TRIM(COL) = 'value' for those columns. Returns {} when absent.
    """
    if path is None:
        path = os.path.join(config.EMBEDDING_DIR, "needs_trim.json")
    if path not in _needs_trim_cache:
        try:
            with open(path) as f:
                _needs_trim_cache[path] = json.load(f)
        except FileNotFoundError:
            _needs_trim_cache[path] = {}
    return _needs_trim_cache[path]


def load_samples(path=None):
    """Load previously fetched description samples. Returns {} if file missing."""
    if path is None:
        path = _output_path()
    if path not in _samples_cache:
        try:
            with open(path) as f:
                _samples_cache[path] = json.load(f)
        except FileNotFoundError:
            _samples_cache[path] = {}
    return _samples_cache[path]


# ──────────────────────────────────────────────────────────────────────────────
# Row-label vector index — read only. Rebuilding this index (embedding every
# distinct row-label value) is build-time tooling that lives in the
# development repo, not here.
# ──────────────────────────────────────────────────────────────────────────────


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
