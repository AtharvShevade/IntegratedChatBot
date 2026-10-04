"""Embedding-based semantic intent matching — build and search a FAISS
index over backend.db_qa.intents.exemplars.EXEMPLARS.

This is the second tier of the intent-classification pipeline (after the
regex classifiers in new_intent_classifier.py / intent_classifier.py):
when a query doesn't match any regex pattern, embed it and find the
nearest exemplar phrasings by cosine similarity. A confident, well-
separated top match can be executed directly; a close top-2/3 is
genuine ambiguity for the LLM disambiguation tier to resolve; a low
top score means nothing in the taxonomy actually covers the question,
and the caller should fall through to the existing RAG/SQL/conversational
fallback.

Reuses backend.sql_agent.vectorizer's SentenceTransformer instance rather
than loading a second model into memory — that module is already loaded
and warmed up at FastAPI startup (see main.py's lifespan), and embedding a
short intent-classification query is a stateless operation with no
coupling to sql_agent's schema-retrieval logic.

Artifacts are written under backend/db_qa/intents/output/ (parallel to
sql_agent's own output/ convention, but scoped to db_qa so the two index
sets never collide).
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import threading

from backend.db_qa.intents.exemplars import EXEMPLARS
from backend.db_qa.intents.taxonomy import Intent

logger = logging.getLogger(__name__)

_HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(_HERE, "output")
INDEX_PATH = os.path.join(OUTPUT_DIR, "intent_exemplar_index.faiss")
META_PATH = os.path.join(OUTPUT_DIR, "intent_exemplar_meta.pkl")

# H-17: a deterministic fingerprint of EXEMPLARS + the embedding model name,
# written alongside the index/metadata every time build_index() runs. Kept as
# its own small JSON file rather than folded into META_PATH's pickle, so the
# existing per-vector meta list format (consumed by _search_dedup via
# meta[idx]["intent"]/["text"]) never changes shape.
MANIFEST_PATH = os.path.join(OUTPUT_DIR, "intent_exemplar_manifest.json")


def _current_embed_model_name() -> str:
    """The embedding model name currently configured for this process.

    Read-only import of the SQL agent's config constant (EMBED_MODEL) --
    the same model embedding_index.py already borrows the loaded
    SentenceTransformer instance from via backend.sql_agent.vectorizer.
    Does not modify or call into any SQL agent behavior.
    """
    from backend.sql_agent.sqlcore.config import EMBED_MODEL
    return EMBED_MODEL


def _fingerprint_exemplars() -> str:
    """Deterministic hash of every (intent, phrasing) pair in EXEMPLARS.

    Order-independent (sorted first) so reordering entries in exemplars.py
    without changing their content does not look like drift; any actual
    addition, removal, or edit of a phrasing changes the hash.
    """
    items = sorted(
        (intent.value, phrasing)
        for intent, phrasings in EXEMPLARS.items()
        for phrasing in phrasings
    )
    h = hashlib.sha256()
    for intent_value, phrasing in items:
        h.update(intent_value.encode("utf-8"))
        h.update(b"\x00")
        h.update(phrasing.encode("utf-8"))
        h.update(b"\x01")
    return h.hexdigest()


def _write_manifest() -> None:
    from backend.sql_agent.sqlcore.integrity import sha256_of_file

    manifest = {
        "fingerprint": _fingerprint_exemplars(),
        "embed_model": _current_embed_model_name(),
        "exemplar_count": sum(len(p) for p in EXEMPLARS.values()),
        # M-08: lets _load_index() verify META_PATH's integrity (same
        # {"checksums": {filename: sha256}} convention the SQL agent's own
        # build_stamp.json already uses) before ever unpickling it -- not
        # just checking it's semantically fresh (the fingerprint above),
        # but that the bytes on disk are exactly what this build wrote.
        "checksums": {os.path.basename(META_PATH): sha256_of_file(META_PATH)},
    }
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)


def check_index_freshness() -> tuple[bool, str]:
    """Compare the on-disk manifest against the exemplars/model currently
    configured. Returns (fresh, reason) -- *reason* is empty when fresh,
    otherwise names exactly what mismatched (or that the manifest is simply
    missing, e.g. an index built before H-17 existed)."""
    if not os.path.exists(MANIFEST_PATH):
        return False, "no manifest found (index predates freshness tracking, or was never built)"

    try:
        with open(MANIFEST_PATH, "r", encoding="utf-8") as fh:
            manifest = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        return False, f"manifest unreadable: {exc}"

    current_fingerprint = _fingerprint_exemplars()
    if manifest.get("fingerprint") != current_fingerprint:
        return False, "exemplars.py has changed since the index was built"

    current_model = _current_embed_model_name()
    if manifest.get("embed_model") != current_model:
        return False, (
            f"embedding model changed (index built with {manifest.get('embed_model')!r}, "
            f"currently configured {current_model!r})"
        )

    return True, ""

# Minimum cosine similarity for a candidate to be considered a match at
# all (below this, treat as "nothing in the taxonomy covers this query").
#
# BGE-large's cosine similarity has a surprisingly high noise floor for
# this domain: manual probing against clearly out-of-domain queries
# ("what is the weather today", "tell me a joke", "the quick brown fox
# jumps", random gibberish) scored 0.67-0.79 top-1 against these
# exemplars, while genuine in-domain paraphrases scored 0.83-0.92. Do
# NOT assume cosine similarity behaves like a 0-1 "relatedness" scale —
# it does not for this model/domain. These thresholds sit in the
# observed gap; revisit once backend.utils.intent_log accumulates real
# production queries to check empirically, especially the risky
# 0.79-0.83 overlap zone between the two clusters observed above.
MIN_SCORE = 0.80

# Top-1 must clear this to execute directly without LLM disambiguation.
CONFIDENT_SCORE = 0.85

# If top-1 and top-2 scores are within this margin of each other, treat
# it as ambiguous (needs LLM disambiguation) even if top-1 clears
# CONFIDENT_SCORE — a close second means the phrasing is genuinely
# consistent with more than one intent.
AMBIGUOUS_MARGIN = 0.05

TOP_K = 5


def build_index() -> None:
    """Embed every exemplar phrasing and write the FAISS index + metadata
    to disk. Run this once after editing exemplars.py (not at request
    time) — e.g. `python -m backend.db_qa.intents.embedding_index`.
    """
    from backend.sql_agent.vectorizer import embed_documents, build_faiss_index, save_index

    texts: list[str] = []
    meta: list[dict] = []
    for intent, phrasings in EXEMPLARS.items():
        for phrasing in phrasings:
            texts.append(phrasing)
            meta.append({"intent": intent.value, "text": phrasing})

    if not texts:
        raise RuntimeError("EXEMPLARS is empty — nothing to index")

    logger.info("Embedding %d exemplar phrasings across %d intents...", len(texts), len(EXEMPLARS))
    vectors = embed_documents(texts)
    index = build_faiss_index(vectors)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    save_index(index, meta, INDEX_PATH, META_PATH)
    _write_manifest()
    _INDEX_CACHE.clear()  # force the next _load_index() to re-read the fresh files
    logger.info("Wrote intent exemplar index: %s (%d vectors)", INDEX_PATH, len(texts))


_INDEX_CACHE: dict = {}
# L-12: guards the lazy-init check-then-load below. Without this, two
# concurrent first callers (e.g. two requests racing on cold start) could
# both see "index" missing and both re-read/rebuild the index, wasting work
# and briefly leaving _INDEX_CACHE in an inconsistent partial state.
_index_lock = threading.Lock()


def _load_index():
    if "index" not in _INDEX_CACHE:
        with _index_lock:
            if "index" not in _INDEX_CACHE:  # re-check: another thread may have just finished
                import faiss

                if not os.path.exists(INDEX_PATH) or not os.path.exists(META_PATH):
                    raise FileNotFoundError(
                        f"Intent exemplar index not found at {INDEX_PATH} — "
                        "run `python -m backend.db_qa.intents.embedding_index` to build it."
                    )

                # H-17: never silently serve a stale index. Detect mismatch against
                # the exemplars/model currently configured and rebuild automatically
                # -- this architecture already supports an on-demand rebuild
                # (build_index() just needs the SentenceTransformer, already loaded).
                # This runs at most once per process (the result is cached below), so
                # it costs one rebuild at warm-up/first-use, not a per-request delay.
                fresh, reason = check_index_freshness()
                if not fresh:
                    logger.warning(
                        "Intent exemplar index is stale (%s) — rebuilding automatically.", reason,
                    )
                    try:
                        build_index()
                    except Exception as exc:
                        logger.error(
                            "Automatic rebuild of the intent exemplar index failed (%s); "
                            "continuing with the existing (possibly stale) index. Run "
                            "`python -m backend.db_qa.intents.embedding_index` manually to rebuild.",
                            exc,
                        )

                # M-08: verified against MANIFEST_PATH's recorded checksum (when one
                # exists -- i.e. this index was built after M-08) before this file
                # is ever unpickled.
                from backend.sql_agent.sqlcore.integrity import safe_pickle_load
                _INDEX_CACHE["index"] = faiss.read_index(INDEX_PATH)
                _INDEX_CACHE["meta"] = safe_pickle_load(META_PATH, stamp_path=MANIFEST_PATH)
    return _INDEX_CACHE["index"], _INDEX_CACHE["meta"]


def _search_dedup(query: str, k: int, min_score: float | None) -> list[tuple[Intent, float, str]]:
    """Shared FAISS search for search_intent()/search_intent_relaxed().

    Deduplicated BY INTENT, keeping only the best-scoring exemplar hit per
    intent, before truncating to *k* — without this, a single intent with
    several similar exemplars can occupy multiple candidate slots and crowd
    out a genuinely relevant intent before it ever reaches LLM disambiguation
    (observed directly: "Which reports can my department file?" returned
    returns_submittable_by_dept in BOTH of its top-2 non-top1 slots, leaving
    no room for the correct intent at k=3).

    To dedup meaningfully we must look further into the ranking than just the
    final k — fetch max(k*4, 20) raw hits (FAISS returns them sorted by
    descending similarity for IndexFlatIP, so the first occurrence of a given
    intent in that raw list is always its best-scored one).
    """
    from backend.sql_agent.vectorizer import embed_query
    import numpy as np

    try:
        index, meta = _load_index()
    except FileNotFoundError as exc:
        logger.warning("%s", exc)
        return []

    if len(meta) == 0:
        return []

    raw_k = min(len(meta), max(k * 4, 20))
    q_vec = np.array([embed_query(query)]).astype("float32")
    distances, indices = index.search(q_vec, raw_k)

    results: list[tuple[Intent, float, str]] = []
    seen: set[Intent] = set()
    for dist, idx in zip(distances[0], indices[0]):
        if idx == -1:
            continue
        if min_score is not None and dist < min_score:
            continue
        record = meta[idx]
        intent = Intent(record["intent"])
        if intent in seen:
            continue
        seen.add(intent)
        results.append((intent, float(dist), record["text"]))
        if len(results) >= k:
            break
    return results


def search_intent(query: str, k: int = TOP_K) -> list[tuple[Intent, float, str]]:
    """Return up to *k* (Intent, cosine_score, matched_exemplar_text) tuples,
    one per distinct intent, sorted by descending score, filtered to
    score >= MIN_SCORE.

    Returns [] if the index hasn't been built yet (logged as a warning,
    not raised — callers should treat this the same as "no match" and
    fall through to the next tier, since a missing index is a deploy/
    setup gap, not a per-query error).
    """
    return _search_dedup(query, k, MIN_SCORE)


def search_intent_relaxed(query: str, k: int = TOP_K) -> list[tuple[Intent, float, str]]:
    """Same as search_intent(), but WITHOUT the MIN_SCORE floor.

    For candidate-gathering only, when the strict search found nothing at
    all — MIN_SCORE still governs whether classify_by_embedding() treats a
    query as "confident"/"ambiguous" vs. out of scope; this just gives a
    caller (e.g. a module-scoped widening of LLM disambiguation) something
    to offer the LLM instead of nothing, for queries that are recognisably
    close to a known intent but too far to pass the floor.
    """
    return _search_dedup(query, k, None)


def classify_by_embedding(query: str) -> dict:
    """Classify *query* via nearest-neighbor exemplar search.

    Returns a dict describing the outcome, always with a "tier" field
    matching backend.utils.intent_log's conventions:

        {"tier": "embedding_confident", "intent": Intent, "score": float,
         "candidates": [...]}
            Top match clears CONFIDENT_SCORE with clear separation from
            the runner-up — safe to execute this intent's handler
            directly, no LLM disambiguation needed.

        {"tier": "embedding_ambiguous", "candidates": [(Intent, score, text), ...]}
            Top-1 and top-2 (or more) are close enough that the LLM
            disambiguation tier should pick between them.

        {"tier": "embedding_none", "candidates": []}
            Nothing cleared MIN_SCORE — fall through to the existing
            RAG/SQL/conversational fallback.
    """
    candidates = search_intent(query, k=TOP_K)

    if not candidates:
        return {"tier": "embedding_none", "candidates": []}

    top_intent, top_score, top_text = candidates[0]

    if top_score >= CONFIDENT_SCORE:
        runner_up_score = candidates[1][1] if len(candidates) > 1 else 0.0
        if (top_score - runner_up_score) >= AMBIGUOUS_MARGIN:
            return {
                "tier": "embedding_confident",
                "intent": top_intent,
                "score": top_score,
                "matched_text": top_text,
                "candidates": candidates,
            }

    return {"tier": "embedding_ambiguous", "candidates": candidates}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    build_index()
