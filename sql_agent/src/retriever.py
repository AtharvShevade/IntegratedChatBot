import re
import faiss
import pickle
import numpy as np
from src.vectorizer import embed_query
from src.config import TOP_K_TABLES, TOP_K_COLUMNS

TOP_K_LABELS = 10   # max row-label values to retrieve per query

# Minimum cosine similarity score to accept a FAISS result (IndexFlatIP,
# vectors are L2-normalised so dot-product == cosine similarity).
MIN_TABLE_SCORE  = 0.25
MIN_COLUMN_SCORE = 0.20

# ── Banking / CIMS domain abbreviation expansion ──────────────────────────────
_QUERY_EXPANSIONS = [
    (r'\bnpa\b',    'NPA non performing assets'),
    (r'\bgnpa\b',   'gross NPA non performing assets'),
    (r'\bnnpa\b',   'net NPA non performing assets'),
    (r'\bsma\b',    'special mention accounts SMA'),
    (r'\bcar\b',    'capital adequacy ratio CAR'),
    (r'\bpcr\b',    'provision coverage ratio PCR'),
    (r'\brwa\b',    'risk weighted assets RWA'),
    (r'\bslr\b',    'statutory liquidity ratio SLR'),
    (r'\bcrr\b',    'cash reserve ratio CRR'),
    (r'\bpsl\b',    'priority sector lending PSL'),
    (r'\braq\b',    'Risk Assessment Questionnaire RAQ CIMS'),
    (r'\bcims\b',   'CIMS banking supervisory return'),
    (r'\bsec(\d+)\b', r'section \1'),
    (r'\bdom\b',    'domestic'),
    (r'\bove\b',    'overseas'),
    (r'\binfra\b',  'infrastructure'),
    (r'\bsensec\b', 'sensitive sector'),
    (r'\bparta\b',  'part A'),
    (r'\bpartb\b',  'part B'),
]


def _expand_query(query: str) -> str:
    """Expand banking abbreviations so the embedding model understands them."""
    q = query
    for pattern, replacement in _QUERY_EXPANSIONS:
        q = re.sub(pattern, replacement, q, flags=re.IGNORECASE)
    return q


def _dynamic_top_k(query: str) -> int:
    """Return a higher TOP_K for complex queries that mention multiple items."""
    hits = len(re.findall(
        r'\b(sec\d+|part\s*[ab]|section\s*\d+|compare|versus|vs|and|both|all|union)\b',
        query, re.IGNORECASE,
    ))
    if hits >= 3:
        return TOP_K_TABLES + 3
    if hits >= 1:
        return TOP_K_TABLES + 1
    return TOP_K_TABLES


def search(index_path, meta_path, query, k, min_score=0.0):
    """Search a FAISS index, returning only hits above min_score."""
    index = faiss.read_index(index_path)

    with open(meta_path, "rb") as f:
        meta = pickle.load(f)

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


def get_relevant_schema(query: str):
    expanded = _expand_query(query)
    top_k = _dynamic_top_k(query)

    # ── Signal A: direct table semantic search ────────────────────────────────
    table_hits = search(
        "output/table_index.faiss", "output/table_meta.pkl",
        expanded, top_k * 3, min_score=MIN_TABLE_SCORE,
    )

    # ── Signal B: column search → which tables do best columns belong to? ─────
    col_hits = search(
        "output/column_index.faiss", "output/column_meta.pkl",
        expanded, TOP_K_COLUMNS * 6, min_score=MIN_COLUMN_SCORE,
    )

    # ── Signal C: row-label search → which tables do best labels belong to? ───
    from src.description_fetcher import search_labels_with_scores
    label_hits = search_labels_with_scores(expanded, top_k=TOP_K_LABELS * 3)

    # ── RRF: fuse all 3 signals into a single table ranking ───────────────────
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
            # Column matched a table the table-search missed — add it
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

    # Pick top_k tables by fused score
    ranked = sorted(scores, key=scores.__getitem__, reverse=True)[:top_k]
    tables = [all_table_meta[tbl] for tbl in ranked]
    table_names = {t["table"] for t in tables}

    # ── Columns: take top matches from selected tables ────────────────────────
    columns = [c for _, c in col_hits if c["table"] in table_names]
    # Deduplicate (table, column) pairs while preserving rank order
    seen_cols: set = set()
    unique_cols = []
    for c in columns:
        key = (c["table"], c["column"])
        if key not in seen_cols:
            seen_cols.add(key)
            unique_cols.append(c)
    columns = unique_cols[:TOP_K_COLUMNS * 2]

    # ── Row labels: restrict to selected tables ───────────────────────────────
    from src.description_fetcher import search_labels
    matched_labels = search_labels(query, table_names, top_k=TOP_K_LABELS)

    return tables, columns, matched_labels
