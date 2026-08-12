"""
BM25 lexical retrieval — Signal G in src/retriever.py's fusion, Phase 1 of the
retrieval accuracy roadmap.

Complementary to the 5 existing dense/embedding signals, not a replacement for
any of them: dense embeddings smooth over exact structural markers ("Part A"
vs "Part B" score within 0.02 of each other because the surrounding column
vocabulary is nearly identical), which is precisely where term-frequency
scoring is strong. See embedding_building/cims_raq_quarterly/build_bm25_index.py
for the corpus this searches (the SAME enriched table documents the dense
table_index.faiss embeds, so the two signals describe identically the same
tables).
"""
import logging
import os
import pickle
import re

from src import config
from src.business_dictionary import expand_acronyms

log = logging.getLogger("lexical_search")

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Cache keyed by resolved path, same convention as _index_cache in
# src/retriever.py — a scope switch (different EMBEDDING_DIR) gets its own
# entry instead of serving another scope's index.
_cache: dict = {}


def _tokenize(text: str) -> list:
    """Must match build_bm25_index.py's tokenize() exactly — same expansion,
    same lowercase/word-split — or query and document tokens would silently
    stop being comparable."""
    return _TOKEN_RE.findall(expand_acronyms(text).lower())


def _load_bm25_index(path: str):
    if path not in _cache:
        if not os.path.exists(path):
            _cache[path] = None
        else:
            with open(path, "rb") as f:
                _cache[path] = pickle.load(f)
    return _cache[path]


def search_bm25(query: str, top_k: int = 15):
    """
    Search the BM25 table index using the RAW (pre-embedding) query text — BM25
    does its own tokenization, so this does NOT take a pre-computed embedding
    the way search_qa/search_concepts do; it takes the query string itself.

    Returns [] if the index hasn't been built (bm25_table_index.pkl absent),
    which is what keeps this signal fully optional — mirrors every other
    signal's degrade-to-empty behaviour in this codebase (concept_index,
    member_index, qa_index all do the same when their file is missing).

    Returns list of (score, meta_dict) exactly like src/retriever.py's other
    search_* functions, so it plugs into the same fusion loop shape.
    """
    path = os.path.join(config.EMBEDDING_DIR, "bm25_table_index.pkl")
    data = _load_bm25_index(path)
    if data is None:
        return []

    bm25, records = data["bm25"], data["records"]
    tokens = _tokenize(query)
    if not tokens:
        return []

    scores = bm25.get_scores(tokens)
    ranked = sorted(range(len(records)), key=lambda i: scores[i], reverse=True)

    results = []
    for i in ranked[:top_k]:
        if scores[i] <= 0:
            break  # BM25 scores are non-negative; 0 means no term overlap at all
        results.append((float(scores[i]), records[i]))
    return results
