import json
import math
import re
import faiss
import pickle
from collections import Counter
import numpy as np
from backend.sql_agent.vectorizer import embed_query
from backend.sql_agent.config import (
    TOP_K_TABLES, TOP_K_COLUMNS,
    TABLE_INDEX_PATH, TABLE_META_PATH,
    COLUMN_INDEX_PATH, COLUMN_META_PATH,
    SCHEMA_JSON_PATH,
)

TOP_K_LABELS = 10   # max row-label values to retrieve per query

# Module-level FAISS index + metadata cache (loaded once per process, not per query)
_INDEX_CACHE: dict = {}

# Minimum cosine similarity score to accept a FAISS result (IndexFlatIP,
# vectors are L2-normalised so dot-product == cosine similarity).
MIN_TABLE_SCORE  = 0.25
MIN_COLUMN_SCORE = 0.20

# ── Banking / CIMS domain abbreviation expansion ──────────────────────────────
_QUERY_EXPANSIONS = [
    (r'\bnpa\b',                     'NPA non performing assets'),
    (r'\bgnpa\b',                    'gross NPA non performing assets'),
    (r'\bnnpa\b',                    'net NPA non performing assets'),
    (r'\bsma\b',                     'special mention accounts SMA'),
    (r'\bcar\b',                     'capital adequacy ratio CAR'),
    (r'\bpcr\b',                     'provision coverage ratio PCR'),
    (r'\brwa\b',                     'risk weighted assets RWA'),
    (r'\bslr\b',                     'statutory liquidity ratio SLR'),
    (r'\bcrr\b',                     'cash reserve ratio CRR'),
    (r'\bpsl\b',                     'priority sector lending PSL'),
    (r'\braq\b',                     'Risk Assessment Questionnaire RAQ CIMS'),
    (r'\bcims\b',                    'CIMS banking supervisory return'),
    (r'\bale\b',                     'ALE asset liability exposure CIMS_ALE monthly'),
    (r'\bcrilc\b',                   'CRILC central repository large credits exposure'),
    (r'\bbsr\b',                     'BSR basic statistical returns deposits advances'),
    (r'\blcr\b',                     'LCR liquidity coverage ratio high quality liquid assets'),
    (r'\bnsfr\b',                    'NSFR net stable funding ratio stable funding'),
    (r'\b(form\s*fr|fr\s*return)\b', 'Form FR statutory reporting CIMS_FORM_FR'),
    (r'\bderivative[s]?\b',          'derivative notional principal MTM credit equivalent ALE section D'),
    (r'\bsec(\d+)\b',                r'section \1'),
    (r'\bdom\b',                     'domestic'),
    (r'\bove\b',                     'overseas'),
    (r'\binfra\b',                   'infrastructure'),
    (r'\bsensec\b',                  'sensitive sector'),
    (r'\bparta\b',                   'part A'),
    (r'\bpartb\b',                   'part B'),
    (r'\bpartc\b',                   'part C'),
    (r'\bpartd\b',                   'part D'),
]


def _expand_query(query: str) -> str:
    """Expand banking abbreviations so the embedding model understands them."""
    q = query
    for pattern, replacement in _QUERY_EXPANSIONS:
        q = re.sub(pattern, replacement, q, flags=re.IGNORECASE)
    return q


# ── Sparse (BM25) lexical signal ──────────────────────────────────────────────
# Dense embeddings are good at "means roughly the same thing" but bad at exact
# term grounding — two tables whose descriptions differ by one decisive word
# (a bank code, a report section name, "Gross NPA" vs "Net NPA") can end up
# almost equidistant in vector space. BM25 fixes exactly that gap: it scores
# tables by literal term overlap, weighted by how rare/informative each term
# is. Built once from schema.json (already on disk, no embedding involved) and
# fused with the dense FAISS signal below via RRF.
_BM25_TOKEN_RE = re.compile(r'[a-z0-9]+')
_BM25_K1, _BM25_B = 1.5, 0.75
_bm25_cache: dict | None = None


def _tokenize(text: str) -> list:
    return [t for t in _BM25_TOKEN_RE.findall(text.lower()) if len(t) > 1]


def _get_bm25_index():
    """Build (once per process) an inverted-index BM25 corpus over table text."""
    global _bm25_cache
    if _bm25_cache is not None:
        return _bm25_cache

    try:
        with open(SCHEMA_JSON_PATH, encoding="utf-8") as f:
            schema = json.load(f)
    except Exception:
        _bm25_cache = {"tables": [], "doc_tokens": [], "postings": {}, "avgdl": 0.0, "n": 0}
        return _bm25_cache

    tables, doc_tokens, doc_lens = [], [], []
    postings: dict[str, dict[int, int]] = {}   # term -> {doc_idx: term_freq}

    for entry in schema:
        if entry.get("is_backup"):
            continue
        text = " ".join([
            entry.get("table", ""),
            entry.get("description", ""),
            entry.get("return_name", ""),
            entry.get("text", ""),
        ])
        tokens = _tokenize(text)
        doc_idx = len(tables)
        tables.append(entry["table"])
        doc_tokens.append(tokens)
        doc_lens.append(len(tokens))
        for term, tf in Counter(tokens).items():
            postings.setdefault(term, {})[doc_idx] = tf

    n = len(tables)
    avgdl = (sum(doc_lens) / n) if n else 0.0

    _bm25_cache = {
        "tables": tables, "doc_lens": doc_lens,
        "postings": postings, "avgdl": avgdl, "n": n,
    }
    return _bm25_cache


def bm25_search(query: str, top_k: int) -> list:
    """Return [(score, {'table': name}), ...] ranked by BM25 lexical relevance."""
    idx = _get_bm25_index()
    n, avgdl = idx["n"], idx["avgdl"]
    if n == 0 or avgdl == 0.0:
        return []

    query_terms = set(_tokenize(query))
    doc_scores: dict[int, float] = {}

    for term in query_terms:
        doc_freqs = idx["postings"].get(term)
        if not doc_freqs:
            continue
        # Standard BM25 idf (Robertson-Spärck Jones), floored at 0 to avoid
        # negative weights for terms that appear in most documents.
        idf = max(0.0, math.log((n - len(doc_freqs) + 0.5) / (len(doc_freqs) + 0.5) + 1))
        if idf == 0.0:
            continue
        for doc_idx, tf in doc_freqs.items():
            dl = idx["doc_lens"][doc_idx]
            denom = tf + _BM25_K1 * (1 - _BM25_B + _BM25_B * dl / avgdl)
            score = idf * (tf * (_BM25_K1 + 1)) / denom
            doc_scores[doc_idx] = doc_scores.get(doc_idx, 0.0) + score

    ranked = sorted(doc_scores.items(), key=lambda kv: kv[1], reverse=True)[:top_k]
    return [(score, {"table": idx["tables"][doc_idx]}) for doc_idx, score in ranked]


def _dynamic_top_k(query: str) -> int:
    """Return a higher TOP_K for complex queries that mention multiple items."""
    hits = len(re.findall(
        r'\b(sec\d+|part\s*[abcd]|section\s*\d+|compare|versus|vs|and|both|all|every|across|combined|union)\b',
        query, re.IGNORECASE,
    ))
    if hits >= 3:
        return TOP_K_TABLES + 3
    if hits >= 1:
        return TOP_K_TABLES + 1
    return TOP_K_TABLES


def search(index_path, meta_path, query, k, min_score=0.0):
    """Search a FAISS index, returning only hits above min_score.
    Indexes are cached in memory after the first load."""
    if index_path not in _INDEX_CACHE:
        _INDEX_CACHE[index_path] = {
            "index": faiss.read_index(index_path),
            "meta":  pickle.load(open(meta_path, "rb")),
        }
    cached = _INDEX_CACHE[index_path]
    index  = cached["index"]
    meta   = cached["meta"]

    if not meta:
        return []

    effective_k = min(k, len(meta))
    q_vec = np.array([embed_query(query)]).astype("float32")
    distances, indices = index.search(q_vec, effective_k)

    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx != -1 and dist >= min_score:
            results.append((float(dist), meta[idx]))
    return results   # list of (score, meta_dict)


def _rrf(rank: int, k: int = 60) -> float:
    """Reciprocal Rank Fusion score."""
    return 1.0 / (k + rank + 1)


_DISAMBIG_BOOST = 0.15


def _apply_disambiguation_boost(query: str, scores: dict) -> None:
    """
    Re-rank tables using explicit domestic/overseas/part signals in the raw
    query. Embedding similarity alone can't reliably tell apart sibling
    tables that share almost all their prompt text (e.g.
    CIMS_RAQ_Q_SEC1_PART_A_DOM vs CIMS_RAQ_Q_SEC1_PART_D_O both describe
    "RAQ section 1 loan assets") — when the user is explicit about which
    one they want, that should outweigh a marginal embedding-score edge.
    Mutates *scores* in place; a no-op when the query gives no such signal.
    """
    qlow = query.lower()
    wants_domestic = bool(re.search(r'\bdomestic\b', qlow))
    wants_overseas = bool(re.search(r'\boverseas\b', qlow))
    part_match = re.search(r'\bpart[\s_-]?([abcd])\b', qlow)
    wants_part = part_match.group(1) if part_match else None

    if not (wants_domestic or wants_overseas or wants_part):
        return

    for tbl in list(scores.keys()):
        tl = tbl.lower()
        is_dom_table = bool(re.search(r'_dom(_|$)', tl))
        is_ove_table = bool(re.search(r'_o$', tl)) or bool(re.search(r'_ove(_|$)', tl))
        part_tbl_match = re.search(r'part_?([abcd])(_|$)', tl)
        tbl_part = part_tbl_match.group(1) if part_tbl_match else None

        if wants_domestic and is_dom_table:
            scores[tbl] += _DISAMBIG_BOOST
        if wants_domestic and is_ove_table:
            scores[tbl] -= _DISAMBIG_BOOST
        if wants_overseas and is_ove_table:
            scores[tbl] += _DISAMBIG_BOOST
        if wants_overseas and is_dom_table:
            scores[tbl] -= _DISAMBIG_BOOST
        if wants_part and tbl_part:
            scores[tbl] += _DISAMBIG_BOOST if tbl_part == wants_part else -_DISAMBIG_BOOST


def get_relevant_schema(query: str):
    expanded = _expand_query(query)
    top_k    = _dynamic_top_k(query)

    # ── Signal A: direct table semantic search ────────────────────────────────
    table_hits = search(
        TABLE_INDEX_PATH, TABLE_META_PATH,
        expanded, top_k * 3, min_score=MIN_TABLE_SCORE,
    )

    # ── Signal B: column search → which tables do best columns belong to? ─────
    col_hits = search(
        COLUMN_INDEX_PATH, COLUMN_META_PATH,
        expanded, TOP_K_COLUMNS * 10, min_score=MIN_COLUMN_SCORE,
    )

    # ── Signal C: row-label search → which tables do best labels belong to? ───
    from backend.sql_agent.description_fetcher import search_labels_with_scores
    label_hits = search_labels_with_scores(expanded, top_k=TOP_K_LABELS * 3)

    # ── Signal D: BM25 lexical search → exact term grounding, no embedding ────
    bm25_hits = bm25_search(expanded, top_k * 3)

    # ── RRF: fuse all 4 signals into a single table ranking ───────────────────
    all_table_meta = {h["table"]: h for _, h in table_hits}
    scores: dict[str, float] = {tbl: 0.0 for tbl in all_table_meta}

    # Signal A weight = 2.0 (most direct)
    for rank, (_, t) in enumerate(table_hits):
        scores[t["table"]] = scores.get(t["table"], 0.0) + _rrf(rank) * 2.0

    # Signal B weight = 1.5 (strong: column names are very specific)
    col_table_seen: dict[str, int] = {}
    for _, c in col_hits:
        tbl = c["table"]
        if tbl not in col_table_seen:
            col_table_seen[tbl] = 0
        rank = col_table_seen[tbl]
        col_table_seen[tbl] += 1
        if tbl in scores:
            scores[tbl] += _rrf(rank) * 1.5
        else:
            all_table_meta[tbl] = {"table": tbl}
            scores[tbl] = _rrf(rank) * 1.5

    # Signal C weight = 1.0
    label_table_seen: dict[str, int] = {}
    for _, lbl in label_hits:
        tbl = lbl["table"]
        if tbl not in label_table_seen:
            label_table_seen[tbl] = 0
        rank = label_table_seen[tbl]
        label_table_seen[tbl] += 1
        if tbl in scores:
            scores[tbl] += _rrf(rank) * 1.0
        else:
            all_table_meta[tbl] = {"table": tbl}
            scores[tbl] = _rrf(rank) * 1.0

    # Signal D weight = 1.75 (between column and table signal — exact lexical
    # match is a strong indicator, but shouldn't fully override semantic fit)
    for rank, (_, t) in enumerate(bm25_hits):
        tbl = t["table"]
        if tbl in scores:
            scores[tbl] += _rrf(rank) * 1.75
        else:
            all_table_meta[tbl] = t
            scores[tbl] = _rrf(rank) * 1.75

    # ── Disambiguation boost: explicit domestic/overseas/part signals ─────────
    _apply_disambiguation_boost(query, scores)

    # Pick top_k tables by fused score
    ranked     = sorted(scores, key=scores.__getitem__, reverse=True)[:top_k]
    tables     = [all_table_meta[tbl] for tbl in ranked]
    table_names = {t["table"] for t in tables}

    # ── Columns: take top matches from selected tables ────────────────────────
    columns = [c for _, c in col_hits if c["table"] in table_names]
    seen_cols: set = set()
    unique_cols    = []
    for c in columns:
        key = (c["table"], c["column"])
        if key not in seen_cols:
            seen_cols.add(key)
            unique_cols.append(c)
    columns = unique_cols[:TOP_K_COLUMNS * 2]

    # ── Row labels: restrict to selected tables ───────────────────────────────
    from backend.sql_agent.description_fetcher import search_labels
    matched_labels = search_labels(query, table_names, top_k=TOP_K_LABELS)

    return tables, columns, matched_labels
