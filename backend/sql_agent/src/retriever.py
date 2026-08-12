import logging
import os
import re
import time
import difflib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Literal

import faiss
import pickle
import numpy as np
from src.vectorizer import embed_query
from src.section_alias import detect_section_reference
from src.lexical_search import search_bm25
import src.config as config
from src.config import TOP_K_TABLES, TOP_K_COLUMNS


@dataclass
class ColumnBinding:
    """
    A concept-index hit's OWN column payload, carried forward as a typed
    binding rather than discarded at fusion time. Phase 1 retrieval-accuracy
    roadmap, Section 5 ("concept binding promotion").

    Before this existed, `search_concepts()` returned (score, meta) pairs where
    meta already carried a `column` field (set in
    build_concept_embeddings.py's concept_documents()) — but the fusion loop
    below only ever read meta["table"] to vote, and the column was re-derived
    LATER, lexically, via concept_map.py's rank_metrics() token-overlap pass,
    after a table had already been chosen. That re-derivation is strictly
    weaker than the embedding-similarity match the concept index itself found.
    This class is what lets a caller (the Context Resolver, or anything else
    building the SQL prompt) use the FIRST, stronger signal instead.
    """
    table: str
    column: str
    concept_id: str
    concept_label: str
    confidence: float
    source: Literal["concept_semantic", "concept_lexical", "qa_example", "bm25_literal"]
    is_certain: bool


@dataclass
class RetrievalResult:
    """
    Return type of get_relevant_schema(), replacing a positional 4-tuple.

    Deliberately NOT a NamedTuple/plain tuple: every existing call site
    unpacks the old 4-tuple by position (`tables, columns, matched_labels,
    qa_example = get_relevant_schema(...)`), so adding a 5th field to a tuple
    would either silently shift meaning (if a caller used `*_` to swallow
    extras, harmless) or break loudly with "too many values to unpack" (every
    exact-4 unpack site) — a deliberate choice per the Phase 1 roadmap: a
    non-iterable object makes EVERY old call site fail at the assignment line
    with an unambiguous TypeError, rather than some sites failing loudly and
    others (the `*_` ones) silently reading a stale shape.
    """
    tables: list
    columns: list
    matched_labels: list
    qa_example: dict | None
    concept_bindings: list = field(default_factory=list)

TOP_K_LABELS = 10   # max row-label values to retrieve per query

# Minimum cosine similarity score to accept a FAISS result (IndexFlatIP,
# vectors are L2-normalised so dot-product == cosine similarity).
MIN_TABLE_SCORE  = 0.25
MIN_COLUMN_SCORE = 0.20

# Minimum similarity for a qa_index hit to be trusted as a concrete few-shot
# example in the SQL prompt (higher bar than table retrieval — a weak match
# here would actively mislead the LLM rather than just miss a table).
QA_EXAMPLE_MIN_SCORE = 0.75

# Two LITERAL TEXT similarity (0-1) tiers for a qa_pairs.json match, checked
# against the user's raw query. Deliberately NOT based on the embedding
# cosine score: bge-large-en's asymmetric query/passage encoding means even a
# word-for-word identical question can score anywhere from ~0.79 to ~0.95
# depending on length/content, and an unrelated-but-topically-similar question
# can land in that same range — so cosine score alone cannot safely
# distinguish "this IS the same question" from "this just sounds similar".
# Literal text similarity has no such ambiguity.
#
#   >= EXACT_MATCH_MIN_RATIO   -> the user typed essentially the SAME sentence
#                                 as a stored question. Skip the LLM entirely,
#                                 execute the verified stored SQL directly.
#   >= STRONG_MATCH_MIN_RATIO  -> close but not identical. Still call the LLM,
#                                 but ground it hard with this near-exact
#                                 example instead of letting it guess.
EXACT_MATCH_MIN_RATIO = 0.99
STRONG_MATCH_MIN_RATIO = 0.95


def _normalize_for_match(text: str) -> str:
    return re.sub(r'\s+', ' ', text.strip().lower())


def text_similarity(a: str, b: str) -> float:
    """Character-level similarity ratio (0-1) between two strings, whitespace/case-insensitive."""
    return difflib.SequenceMatcher(None, _normalize_for_match(a), _normalize_for_match(b)).ratio()


# Generic FUNCTION words only — no distinguishing meaning for "is this the
# same question" — stripped before token comparison so two questions match
# on their actual CONTENT words (not just "what"/"the"/"is"). Deliberately
# does NOT include "raq"/"cims"/etc: those are return/product identifiers,
# not filler — stripping them would make "for RAQ" and "for RBS" (or any
# other real return) look identical once this scope covers more than one
# return, erasing exactly the token that distinguishes them.
_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "what", "how", "of", "for",
    "to", "in", "on", "and", "or", "show", "me", "give", "tell", "please",
    "does", "do", "this", "that", "it", "its", "much", "many",
}

# Light suffix-stripping (not a real stemmer — no NLTK/spaCy dependency
# needed for this) so "advance"/"advances", "expose"/"exposure"-style
# plural/inflection differences don't count as a mismatch.
_STEM_SUFFIXES = ("ing", "ed", "es", "s")


def _stem(token: str) -> str:
    for suf in _STEM_SUFFIXES:
        if len(token) > len(suf) + 2 and token.endswith(suf):
            return token[: -len(suf)]
    return token


def _tokenize(text: str) -> set:
    # Route through _expand_query first so domain abbreviations (dom/ove,
    # npa, raq, sec1/sec2...) normalize the same way on both sides of the
    # comparison — a user typing "dom" and a stored question saying
    # "domestic" should count as the same token, not a mismatch.
    words = re.findall(r'[a-z0-9]+', _expand_query(text).lower())
    return {_stem(w) for w in words if w not in _STOPWORDS and len(w) > 2}


def token_similarity(a: str, b: str) -> float:
    """
    Token-set (Jaccard) similarity after lowercasing, domain-abbreviation
    expansion, stopword removal, and light suffix-stripping. This catches
    real paraphrases that character-level text_similarity misses — reordered
    clauses, plurals, "closing balance of X" vs "X at the end of the
    period" — without the unpredictable scoring range of raw embedding
    cosine similarity (see the note on EXACT_MATCH_MIN_RATIO above).

    Deliberately NOT used to gate the skip-the-LLM tier: word-overlap can be
    fooled by a meaning-changing swap that still shares most tokens (e.g.
    "domestic" vs "overseas", "Part A" vs "Part B") — safe enough to
    guarantee a table is worth showing the model, not safe enough to bypass
    the model's judgment entirely.
    """
    ta, tb = _tokenize(a), _tokenize(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def best_qa_similarity(a: str, b: str) -> float:
    """The stronger of literal text similarity and token-set similarity — use
    for the "should we ground/prioritize this table" decision, never for the
    "skip the LLM entirely" decision (see token_similarity's docstring)."""
    return max(text_similarity(a, b), token_similarity(a, b))


def _rerank_qa_hits(query: str, qa_hits: list) -> list:
    """
    Embedding score alone does not reliably rank near-tied QA candidates:
    two hits 0.001-0.03 apart in cosine score (routine for this schema, since
    table/question descriptions are worded similarly) can differ hugely in
    whether they're actually about the same topic — e.g. "total export
    credit exposure" vs "total domestic loan exposure" both score ~0.81
    against "show total loan from cims raq". Among the hits that clear
    QA_EXAMPLE_MIN_SCORE, re-rank by best_qa_similarity (literal/token text
    overlap), which discriminates far better here, so a genuinely
    better-worded match wins instead of embedding noise picking the winner.

    Only affects which SINGLE hit is treated as "the" best match (for the
    strong-match/forced-table tier, the score bonus, and the few-shot
    example) — the RRF fusion signal over all qa_hits is untouched.
    """
    if not qa_hits:
        return qa_hits
    strong_enough = [pair for pair in qa_hits if pair[0] >= QA_EXAMPLE_MIN_SCORE]
    if len(strong_enough) <= 1:
        return qa_hits
    reranked = sorted(
        strong_enough,
        key=lambda pair: best_qa_similarity(query, pair[1]["question"]),
        reverse=True,
    )
    rest = [h for h in qa_hits if h not in strong_enough]
    return reranked + rest


def compute_query_embedding(query: str):
    """
    Embed the jargon-expanded query ONCE. Both find_exact_qa_match and
    get_relevant_schema need the same vector (they embed the same expanded
    text) — call this once per request and pass the result to both via their
    query_vec= parameter, instead of letting each function (and each of the
    4 signals inside get_relevant_schema) re-run model.encode() on its own.
    Measured cost of a single embed_query() call is ~100ms on CPU; before
    this, a single request could pay for it up to 6 times.
    """
    return embed_query(_expand_query(query))


def find_exact_qa_match(query: str, query_vec=None):
    """
    Cheap, standalone check run BEFORE any table/column shortlisting: look up
    only the qa_index (question -> gold SQL) for a near-identical stored
    question. If the user typed essentially the same sentence as one already
    in qa_pairs.json, there's nothing to retrieve or generate — just reuse
    the verified answer.

    query_vec: optional pre-computed embedding (see compute_query_embedding).
    If omitted, computed internally so existing callers keep working unchanged.

    Returns {question, sql, table, text_similarity} or None.
    """
    if query_vec is None:
        query_vec = compute_query_embedding(query)
    hits = search_qa(query_vec, top_k=1)
    if not hits:
        return None
    _score, qa = hits[0]
    sim = text_similarity(query, qa["question"])
    if sim >= EXACT_MATCH_MIN_RATIO:
        return {"question": qa["question"], "sql": qa["sql"], "table": qa["table"], "text_similarity": sim}
    return None


# ── Banking / CIMS domain abbreviation expansion ──────────────────────────────
# Delegates to src/business_dictionary.py, the single place this expansion list
# now lives (embedding_building/business_dictionary.yaml is the data source).
# Was a hardcoded regex list inline here; moved out so BM25
# (src/lexical_search.py) and any future signal expand the SAME way instead of
# each forking their own copy — see src/query_rewrite.py's module docstring.
from src.business_dictionary import detect_pinned_table, expand_acronyms


def _expand_query(query: str) -> str:
    """Expand banking abbreviations so the embedding model understands them."""
    return expand_acronyms(query)


def _dynamic_top_k(query: str) -> int:
    """
    Return a higher TOP_K only for queries with genuine multi-section signals
    (explicit section/part references, or comparison language). Generic
    conjunctions like "and"/"both"/"all" were previously counted too — those
    appear in almost any single-topic question ("show X and Y from this
    return") and caused routine over-widening, which let unrelated tables
    fill the extra slots via a single weak column/label match.
    """
    hits = len(re.findall(
        r'\b(sec\d+|part\s*[ab]|section\s*\d+|compare|versus|vs)\b',
        query, re.IGNORECASE,
    ))
    if hits >= 3:
        return TOP_K_TABLES + 3
    if hits >= 1:
        return TOP_K_TABLES + 1
    return TOP_K_TABLES


# Cache of loaded FAISS indexes + metadata, keyed by (index_path, meta_path)
# so a scope switch (different EMBEDDING_DIR) naturally gets its own cache
# entry instead of serving a stale index. Previously every search() call
# re-read and unpickled these files from disk — cheap for today's small
# indexes but still wasted, repeated work on every single request.
# Cached for the life of the process: rebuilding the indexes requires a restart
# to pick them up (uvicorn's reloader watches api/ and src/, not
# embedding_building/, so a rebuild alone will not trigger one).
_index_cache: dict = {}


def _get_index(index_path, meta_path):
    key = (index_path, meta_path)
    if key not in _index_cache:
        if not os.path.exists(index_path):
            _index_cache[key] = (None, [])
        else:
            index = faiss.read_index(index_path)
            with open(meta_path, "rb") as f:
                meta = pickle.load(f)
            _index_cache[key] = (index, meta)
    return _index_cache[key]


def search(index_path, meta_path, query_vec, k, min_score=0.0):
    """Search a FAISS index using a PRE-COMPUTED query embedding, returning
    only hits above min_score. Index/metadata are loaded once and cached
    (see _get_index) rather than re-read from disk on every call."""
    index, meta = _get_index(index_path, meta_path)
    if index is None or not meta:
        return []

    effective_k = min(k, len(meta))
    q_vec = np.asarray(query_vec, dtype="float32").reshape(1, -1)
    distances, indices = index.search(q_vec, effective_k)

    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx != -1 and dist >= min_score:
            results.append((float(dist), meta[idx]))
    return results   # list of (score, meta_dict)


log = logging.getLogger("retriever")


def _rrf(rank: int, k: int = 60) -> float:
    """Reciprocal Rank Fusion score."""
    return 1.0 / (k + rank + 1)


# Minimum similarity for the two XBRL-derived signals. Both sit slightly above
# MIN_TABLE_SCORE: their documents are short, business-worded sentences rather
# than the long concatenated blobs the table/column indexes hold, so a weak match
# here is genuinely weak rather than an artefact of document length.
MIN_CONCEPT_SCORE = 0.30
MIN_MEMBER_SCORE = 0.35


def search_concepts(query_vec, top_k: int = 15):
    """
    Search the XBRL business-concept index (concept_index.faiss, built by
    embedding_building/cims_raq_quarterly/build_concept_embeddings.py) using a
    pre-computed query embedding. Returns [] if it hasn't been built, which is
    what keeps this signal fully optional.

    Each hit carries the physical table its concept maps to, so a hit on the
    regulatory phrasing of a metric routes straight to one table+column.
    """
    return search(
        f"{config.EMBEDDING_DIR}/concept_index.faiss",
        f"{config.EMBEDDING_DIR}/concept_meta.pkl",
        query_vec, top_k, min_score=MIN_CONCEPT_SCORE,
    )


def search_members(query_vec, top_k: int = 15):
    """
    Search the dimension-member index (member_index.faiss). A member hit says
    "this DIMENSION is involved" ('doubtful assets two', 'non-funded', 'in
    rupees'), which narrows the plausible tables without identifying a column —
    hence the low fusion weight where it is used.

    Each hit carries every table whose mapped concepts reference that member's
    axis, so one member can vote for several tables.
    """
    return search(
        f"{config.EMBEDDING_DIR}/member_index.faiss",
        f"{config.EMBEDDING_DIR}/member_meta.pkl",
        query_vec, top_k, min_score=MIN_MEMBER_SCORE,
    )


def search_qa(query_vec, top_k: int = 15):
    """
    Search the table_qa.json-derived question index (test/qa_index.faiss),
    built by test/build_test_index.py, using a pre-computed query embedding.
    Returns [] if the index hasn't been built.
    """
    qa_index_path = f"{config.EMBEDDING_DIR}/qa_index.faiss"
    qa_meta_path = f"{config.EMBEDDING_DIR}/qa_meta.pkl"
    return search(qa_index_path, qa_meta_path, query_vec, top_k, min_score=MIN_TABLE_SCORE)


def get_relevant_schema(query: str, query_vec=None, shortlist_k: int | None = None):
    """
    query_vec: optional pre-computed embedding of the jargon-expanded query
    (see compute_query_embedding). Pass this in when the caller already
    computed it (e.g. alongside find_exact_qa_match for the same request) to
    avoid embedding the same text twice. If omitted, computed internally —
    all 4 signals below (and the later row-label lookup) reuse this ONE
    vector instead of each calling embed_query() independently.

    shortlist_k: when given, return this many candidate tables instead of the
    dynamic top_k. This is the recall stage for src/selector.py, which then
    picks ONE table to actually put in front of the SQL model. Handing three
    similarly-scored tables straight to a 7B model made it JOIN all three and
    invent the foreign key to do it (see eval/results/hallucination_log.jsonl),
    so breadth belongs here and precision belongs in the selector.

    Each returned table dict carries "score" (fused RRF score) and, on at most
    one of them, "strong_match": True — a near-duplicate prior question, which
    is reason enough to skip the selector entirely.
    """
    expanded = _expand_query(query)
    if query_vec is None:
        query_vec = embed_query(expanded)
    top_k = _dynamic_top_k(query)
    effective_k = shortlist_k if shortlist_k else top_k
    embedding_dir = config.EMBEDDING_DIR

    # ── Signals A-G: 7 independent FAISS/BM25 searches ─────────────────────────
    # Each signal only reads an already-loaded, cached index (see _get_index)
    # and the single query_vec computed above — there is no cross-signal
    # dependency, so they used to run one after another for no reason. Run
    # them concurrently via a thread pool instead: FAISS's native search()
    # releases the GIL, and disabled signals (weight 0) are cheap no-op
    # lambdas so the pool overhead never dominates. Per-signal timing is
    # logged so a slow signal shows up without re-instrumenting later.
    from src.description_fetcher import search_labels_with_scores

    qa_weight = config.QA_SIGNAL_WEIGHT
    concept_weight = config.CONCEPT_SIGNAL_WEIGHT
    member_weight = config.MEMBER_SIGNAL_WEIGHT
    bm25_weight = config.BM25_SIGNAL_WEIGHT

    def _timed(name, fn):
        def _run():
            t0 = time.perf_counter()
            result = fn()
            log.info("[TIMING] retrieval signal %s = %.1fms", name,
                      (time.perf_counter() - t0) * 1000)
            return result
        return _run

    signal_jobs = {
        # ── Signal A: direct table semantic search ─────────────────────────
        "A_table": _timed("A_table", lambda: search(
            f"{embedding_dir}/table_index.faiss", f"{embedding_dir}/table_meta.pkl",
            query_vec, top_k * 3, min_score=MIN_TABLE_SCORE,
        )),
        # ── Signal B: column search → which tables do best columns belong to? ─
        "B_column": _timed("B_column", lambda: search(
            f"{embedding_dir}/column_index.faiss", f"{embedding_dir}/column_meta.pkl",
            query_vec, TOP_K_COLUMNS * 6, min_score=MIN_COLUMN_SCORE,
        )),
        # ── Signal C: row-label search → which tables do best labels belong to? ─
        "C_label": _timed("C_label", lambda: search_labels_with_scores(
            query_vec, top_k=TOP_K_LABELS * 3,
        )),
        # ── Signal D: question→SQL example search (test/qa_index.faiss, optional) ─
        # Weight 0 removes this signal entirely — the search, the fusion votes,
        # the score bonus and the strong-match tier — so retrieval can be
        # measured on qa_pairs.json without the index leaking its own answers
        # back in.
        "D_qa": _timed("D_qa", lambda: search_qa(query_vec, top_k=top_k * 3) if qa_weight else []),
        # ── Signal E: XBRL business-concept search → concept's mapped table ────
        # Weight 0 disables the signal entirely (no search, no fusion) so the
        # two XBRL signals can be A/B'd against the pre-integration ranking
        # without rebuilding or moving any index file.
        "E_concept": _timed("E_concept", lambda: search_concepts(query_vec, top_k=top_k * 3) if concept_weight else []),
        # ── Signal F: XBRL dimension-member search → tables using that axis ────
        "F_member": _timed("F_member", lambda: search_members(query_vec, top_k=TOP_K_LABELS) if member_weight else []),
        # ── Signal G: BM25 lexical search → exact-term table match ─────────────
        # Takes the RAW query text (BM25 does its own tokenization internally
        # via src/business_dictionary.py's expand_acronyms, applied identically
        # on the document side by build_bm25_index.py) — not query_vec, which
        # is an embedding and meaningless to a lexical scorer.
        "G_bm25": _timed("G_bm25", lambda: search_bm25(query, top_k=top_k * 3) if bm25_weight else []),
    }

    _signal_t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=len(signal_jobs)) as pool:
        futures = {name: pool.submit(job) for name, job in signal_jobs.items()}
        signal_results = {name: fut.result() for name, fut in futures.items()}
    log.info("[TIMING] retrieval signals A-G total (parallel) = %.1fms",
              (time.perf_counter() - _signal_t0) * 1000)

    table_hits = signal_results["A_table"]
    col_hits = signal_results["B_column"]
    label_hits = signal_results["C_label"]
    qa_hits = signal_results["D_qa"]
    concept_hits = signal_results["E_concept"]
    member_hits = signal_results["F_member"]
    bm25_hits = signal_results["G_bm25"]
    # Best single QA match, re-ranked by text/token overlap rather than raw
    # embedding rank — see _rerank_qa_hits docstring. Used below wherever ONE
    # winning hit is picked (bonus, strong-match, few-shot example); RRF
    # fusion over all qa_hits a few lines down is untouched.
    qa_hits_ranked = _rerank_qa_hits(query, qa_hits)

    # ── RRF: fuse all 3 signals into a single table ranking ───────────────────
    # Different sources can disagree on table-name casing (schema.json-derived
    # indexes store lowercase; a hand-written qa_pairs.json might use
    # uppercase) — fuse on a normalised (uppercase) key everywhere so the same
    # real table never gets split into two separate score-dict entries.
    def _norm(name: str) -> str:
        return name.upper()

    all_table_meta = {_norm(h["table"]): h for _, h in table_hits}
    scores: dict[str, float] = {tbl: 0.0 for tbl in all_table_meta}

    # Signal A weight = 2.0 (most direct)
    for rank, (_, t) in enumerate(table_hits):
        key = _norm(t["table"])
        scores[key] = scores.get(key, 0.0) + _rrf(rank) * 2.0

    # Signal B weight = 1.5 (strong: column names are very specific)
    col_table_seen: dict[str, int] = {}
    for _, c in col_hits:
        tbl = _norm(c["table"])
        if tbl not in col_table_seen:
            col_table_seen[tbl] = 0
        rank = col_table_seen[tbl]
        col_table_seen[tbl] += 1
        if tbl in scores:
            scores[tbl] += _rrf(rank) * 1.5
        else:
            # Column matched a table the table-search missed — add it
            all_table_meta[tbl] = {"table": c["table"]}
            scores[tbl] = _rrf(rank) * 1.5

    # Signal C weight = 1.0
    label_table_seen: dict[str, int] = {}
    for _, lbl in label_hits:
        tbl = _norm(lbl["table"])
        if tbl not in label_table_seen:
            label_table_seen[tbl] = 0
        rank = label_table_seen[tbl]
        label_table_seen[tbl] += 1
        if tbl in scores:
            scores[tbl] += _rrf(rank) * 1.0
        else:
            all_table_meta[tbl] = {"table": lbl["table"]}
            scores[tbl] = _rrf(rank) * 1.0

    # Signal D weight = config.QA_SIGNAL_WEIGHT, default 2.5 (a question→SQL
    # example match is the strongest signal available). At 0 the loop below is a
    # no-op because qa_hits is empty, and so are the bonus and strong-match tiers
    # that read qa_hits_ranked.
    qa_table_seen: dict[str, int] = {}
    for _, qa in qa_hits:
        tbl = _norm(qa["table"])
        if tbl not in qa_table_seen:
            qa_table_seen[tbl] = 0
        rank = qa_table_seen[tbl]
        qa_table_seen[tbl] += 1
        if tbl in scores:
            scores[tbl] += _rrf(rank) * qa_weight
        else:
            all_table_meta[tbl] = {"table": qa["table"]}
            scores[tbl] = _rrf(rank) * qa_weight

    # Signal E weight = 2.0 (as strong as direct table search, below the QA
    # signal). A concept match is PRECISE — it names one column via a mapping
    # verified by a deterministic 4-hop join — but a business label can still be
    # ambiguous across sections ("advances outstanding" appears in several), so it
    # must not outrank a verified prior question.
    # Scored on each table's BEST concept hit only — deliberately unlike the
    # column/label/qa signals above, which accumulate a vote per hit.
    #
    # Those signals are evidence-gathering: many matching columns genuinely means
    # a table is more relevant. A concept hit is not evidence, it is an ANSWER —
    # it names one column via a verified mapping. Summing per-hit votes therefore
    # rewards the wrong thing: a table holding many similarly-worded sibling
    # concepts outvotes the table holding the one exact match. Measured case,
    # "Show inter-bank assets by period of delinquency": the rank-0 hit is
    # 'Inter bank assets' -> SEC1_PART_B_DOM (0.865, the correct table), but
    # SEC1_PART_A_DOM held four weaker hits ('Loans', 'Overdraft and cash
    # credits', ...) and won the sum. Best-hit scoring fixes that without
    # weakening the signal where it is right.
    # concept_bindings is built from the SAME loop but is NOT subject to
    # CONCEPT_MAX_HITS_PER_TABLE — that cap exists only to stop weak sibling
    # hits from winning the table VOTE (see the measured "inter-bank assets"
    # case above); it has nothing to do with how many candidate column
    # bindings a downstream consumer (the Context Resolver) might reasonably
    # want to consider for a table once it IS selected. Different consumer,
    # different tolerance for multiple candidates — see ColumnBinding's
    # docstring.
    concept_bindings: list[ColumnBinding] = []
    concept_hits_used: dict[str, int] = {}
    for score, cp in concept_hits:
        tbl = _norm(cp["table"])
        if cp.get("column"):
            from src.concept_map import metrics_for_table
            is_certain = False
            for m in metrics_for_table(cp["table"]):
                if m.get("concept_id") == cp.get("concept_id"):
                    is_certain = bool(m.get("row_code_selects_metric"))
                    break
            concept_bindings.append(ColumnBinding(
                table=cp["table"], column=cp["column"],
                concept_id=cp.get("concept_id", ""), concept_label=cp.get("label", ""),
                confidence=score, source="concept_semantic", is_certain=is_certain,
            ))
        used = concept_hits_used.setdefault(tbl, 0)
        if used >= config.CONCEPT_MAX_HITS_PER_TABLE:
            continue
        concept_hits_used[tbl] = used + 1
        if tbl not in scores:
            all_table_meta[tbl] = {"table": cp["table"]}
            scores[tbl] = 0.0
        scores[tbl] += _rrf(used) * concept_weight

    # Signal F weight = 0.75 (narrows, rarely decides). One member can reference
    # several tables, so its vote is split across them by rank rather than given
    # to each at full strength — otherwise a single generic member ('Total') would
    # outvote every other signal simply by touching more tables.
    member_table_seen: dict[str, int] = {}
    for _, mem in member_hits:
        for tbl_raw in mem.get("tables") or []:
            tbl = _norm(tbl_raw)
            rank = member_table_seen.setdefault(tbl, 0)
            member_table_seen[tbl] += 1
            if tbl in scores:
                scores[tbl] += _rrf(rank) * member_weight
            else:
                all_table_meta[tbl] = {"table": tbl_raw}
                scores[tbl] = _rrf(rank) * member_weight

    # Signal G weight = config.BM25_SIGNAL_WEIGHT, default 1.5 (same tier as
    # column_index: a precision signal on exact terms). Accumulates a vote per
    # hit, like signals A/B/C/D — BM25 hits are genuine evidence (more matching
    # terms means more relevant), unlike the concept signal's best-hit-only
    # scoring, which exists because a concept hit is an ANSWER, not evidence.
    bm25_table_seen: dict[str, int] = {}
    for _, bt in bm25_hits:
        tbl = _norm(bt["table"])
        rank = bm25_table_seen.setdefault(tbl, 0)
        bm25_table_seen[tbl] += 1
        if tbl in scores:
            scores[tbl] += _rrf(rank) * bm25_weight
        else:
            all_table_meta[tbl] = {"table": bt["table"]}
            scores[tbl] = _rrf(rank) * bm25_weight

    # ── Hybrid calibration term (addresses RRF's rank-only blindness) ─────────
    # RRF discards magnitude: a near-exact match (raw score 0.95) and a
    # mediocre one (0.81) vote almost identically if they land at the same
    # rank. This is why the QA-match bonus above exists as a hand-tuned patch;
    # HYBRID_BLEND_GAMMA is a general replacement for that PATTERN — a small
    # additive term scaled by how strong each table's single best raw score
    # was, normalised within its own signal's hit list so a BM25 score (0-20+)
    # and a cosine score (0-1) are never compared on raw magnitude directly.
    # gamma=0.0 (the default) makes this entire block a no-op — byte-identical
    # to pre-Phase-1 fusion.
    if config.HYBRID_BLEND_GAMMA:
        def _normalized_top_raw(hit_lists):
            """{table: 0..1} — this table's best raw score in this signal,
            min-max normalised against the FULL range of scores this signal
            returned (not against other signals, which use unrelated scales)."""
            best_raw: dict[str, float] = {}
            for _, meta in hit_lists:
                tbl = _norm(meta["table"])
                sc = meta.get("_raw_score")
                if sc is None:
                    continue
                if tbl not in best_raw or sc > best_raw[tbl]:
                    best_raw[tbl] = sc
            if not best_raw:
                return {}
            lo, hi = min(best_raw.values()), max(best_raw.values())
            if hi <= lo:
                return {t: 1.0 for t in best_raw}
            return {t: (v - lo) / (hi - lo) for t, v in best_raw.items()}

        # Reattach each hit's own raw score into its meta for the helper above
        # (search() results are (score, meta) pairs — the score lives outside
        # meta, so pair them back together here rather than mutate `search()`'s
        # contract for every caller).
        def _with_raw(hits):
            return [(sc, {**meta, "_raw_score": sc}) for sc, meta in hits]

        normalized_per_signal = [
            _normalized_top_raw(_with_raw(table_hits)),
            _normalized_top_raw(_with_raw(col_hits)),
            _normalized_top_raw(_with_raw(label_hits)),
            _normalized_top_raw(_with_raw(qa_hits)),
            _normalized_top_raw(_with_raw(concept_hits)),
            _normalized_top_raw(_with_raw(bm25_hits)),
        ]
        for tbl in scores:
            best_normalized = max((d.get(tbl, 0.0) for d in normalized_per_signal), default=0.0)
            scores[tbl] += config.HYBRID_BLEND_GAMMA * best_normalized

    # RRF only considers rank, not raw similarity magnitude — so a near-exact
    # paraphrase match (e.g. 0.895) and a mediocre one (e.g. 0.866) get almost
    # the same vote if they land at rank 0 vs rank 1. In this schema, table
    # descriptions are all worded similarly ("risk category, domestic vs
    # overseas, outstanding amount..."), so raw table/column cosine scores
    # cluster tightly and rarely discriminate well on their own — but a close
    # match against a REAL worded question (qa_hits) is a much stronger
    # confidence signal. Give the top QA hit's table a decisive bonus scaled
    # by how far above the "trustworthy example" bar it scores, so a
    # confident question match can override a crowd of similarly-scored but
    # actually-unrelated tables instead of being diluted into one more vote.
    # Snapshot the fused score BEFORE the QA bonus below can inflate it. Bug
    # fix: RELATIVE_FLOOR used to be computed off the post-bonus top score, so
    # a confident QA match (bonus up to ~1.25, vs typical fused scores of
    # 0.05-0.4) inflated the reference every OTHER table's prune floor was
    # measured against, silently dropping genuinely relevant tables (e.g. a
    # join partner for a "compare X vs Y" question) before the selector ever
    # saw them. The bonus's effect on final ranking/inclusion is untouched —
    # only the floor's reference point changes. See config.QA_BONUS_FLOOR_FIX.
    pre_bonus_top = max(scores.values()) if scores else 0.0

    if qa_hits_ranked:
        top_qa_score, top_qa = qa_hits_ranked[0]
        if top_qa_score >= QA_EXAMPLE_MIN_SCORE:
            bonus_tbl = _norm(top_qa["table"])
            bonus = (top_qa_score - QA_EXAMPLE_MIN_SCORE) * 5.0
            scores[bonus_tbl] = scores.get(bonus_tbl, 0.0) + bonus
            all_table_meta.setdefault(bonus_tbl, {"table": top_qa["table"]})

    # Pick top_k tables by fused score, but drop any table that only scraped
    # in via a single weak signal while a clearly dominant table exists —
    # otherwise a widened top_k slot gets filled by an unrelated table on the
    # strength of one stray column/label hit (e.g. a shared _DOM/_OVE column
    # name pulling in a table from a completely different section).
    ranked_all = sorted(scores, key=scores.__getitem__, reverse=True)
    if ranked_all:
        top_score = scores[ranked_all[0]]
        # pre_bonus_top can be 0.0 if `scores` started empty and the only entry
        # came from the QA bonus itself (bonus_tbl wasn't previously in
        # scores) — fall back to the post-bonus top score rather than a zero
        # floor in that edge case, matching pre-fix behaviour for the one
        # table that IS the QA hit.
        if config.QA_BONUS_FLOOR_FIX and pre_bonus_top > 0.0:
            floor_reference = pre_bonus_top
        else:
            floor_reference = top_score
        RELATIVE_FLOOR = 0.15  # keep tables scoring at least this fraction of the top hit
        ranked = [t for t in ranked_all if scores[t] >= floor_reference * RELATIVE_FLOOR][:effective_k]
    else:
        ranked = []
    # Copy the meta dicts rather than annotating them in place — they come from
    # the module-level pickle cache and are reused across requests.
    tables = [{**all_table_meta[tbl], "score": scores[tbl]} for tbl in ranked]

    # (A dedupe pass used to live here because the Annual->Quarterly fallback
    # could map two Annual tables onto one Quarterly table. That feature is gone,
    # and `ranked` holds uppercase-normalised keys that are unique by
    # construction, so no two entries can resolve to the same table name.)

    # If the top qa_pairs.json hit is a STRONG match (95%+ on literal text OR
    # token-set/paraphrase similarity) to the user's raw query, GUARANTEE its
    # table is included, front of the list — stronger than the score-based
    # bonus above, which only makes the table likely to win fusion, not
    # certain. This is the "95%+ -> ground the LLM hard with this near-exact
    # example" tier. Token similarity catches real paraphrases (reordered
    # clauses, plurals, synonyms) that character-diff alone would miss.
    if qa_hits_ranked:
        _top_score, _top_qa = qa_hits_ranked[0]
        if best_qa_similarity(query, _top_qa["question"]) >= STRONG_MATCH_MIN_RATIO:
            strong_table = _top_qa["table"]
            tables = [t for t in tables if t["table"].upper() != strong_table.upper()]
            # "strong_match" tells the selector it can skip its LLM call: a 95%+
            # paraphrase of a prior question already identifies the table.
            tables.insert(0, {"table": strong_table, "strong_match": True})
            if effective_k:
                tables = tables[:effective_k]

    # A BUSINESS-DICTIONARY ALIAS ("other risk assets and exposures" -> the
    # table whose real name is sec2_part_b but whose own source-sheet header
    # reads "Part C") is a harder signal than any embedding score, same tier as
    # the QA strong-match above — the alias is a curated, validated fact, not a
    # ranking. Checked BEFORE the explicit-section-reference block below so an
    # unambiguous, genuinely-different section number (rare, but possible if a
    # query names one) still has the final say — see business_dictionary.py's
    # detect_pinned_table docstring for why this precedence is safe.
    pinned_alias = detect_pinned_table(query)
    if pinned_alias:
        tables = [t for t in tables if t["table"].upper() != pinned_alias.upper()]
        tables.insert(0, {"table": pinned_alias, "alias_match": True})
        if effective_k:
            tables = tables[:effective_k]

    # An EXPLICIT section reference in the question ("Section 10", "Section 12
    # Misc T4") is a harder signal than any embedding score — the user named the
    # table. Applied last so it outranks even the QA strong-match tier above.
    # Without this, embedding retrieval picks whichever table's COLUMNS resemble
    # the wording (interest-rate columns pull toward SEC10 regardless of which
    # section was actually named), which was 5 of 11 wrong answers in testing.
    section_ref = detect_section_reference(query)
    if section_ref:
        if section_ref["resolved"]:
            pinned = section_ref["resolved"]
            tables = [t for t in tables if t["table"].upper() != pinned.upper()]
            tables.insert(0, {"table": pinned, "section_match": True})
        else:
            # Ambiguous within the section (e.g. "Section 12" spans 4 tables):
            # restrict to that section's tables so retrieval keeps its ranking
            # WITHIN the right scope, rather than forcing a blind pick.
            allowed = {c.upper() for c in section_ref["candidates"]}
            scoped = [t for t in tables if t["table"].upper() in allowed]
            missing = [c for c in section_ref["candidates"]
                       if c.upper() not in {t["table"].upper() for t in scoped}]
            tables = scoped + [{"table": c} for c in missing]
        if effective_k:
            tables = tables[:effective_k]

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
    # Reuses query_vec (same embedding as label_hits above) instead of
    # re-embedding — this used to be a 6th independent embed_query() call.
    from src.description_fetcher import search_labels
    matched_labels = search_labels(query_vec, table_names, top_k=TOP_K_LABELS)

    # ── Best qa_index match: surfaced separately for few-shot prompt injection ─
    # Use the re-ranked winner (text/token overlap), not raw embedding rank.
    qa_example = None
    if qa_hits_ranked and qa_hits_ranked[0][0] >= QA_EXAMPLE_MIN_SCORE:
        score, qa = qa_hits_ranked[0]
        qa_example = {
            "question": qa["question"], "sql": qa["sql"], "table": qa["table"],
            "score": score,
            "text_similarity": text_similarity(query, qa["question"]),
            "token_similarity": token_similarity(query, qa["question"]),
        }

    return RetrievalResult(
        tables=tables, columns=columns, matched_labels=matched_labels,
        qa_example=qa_example, concept_bindings=concept_bindings,
    )
