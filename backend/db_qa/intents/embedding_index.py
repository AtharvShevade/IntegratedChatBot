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

import logging
import os

from backend.db_qa.intents.exemplars import EXEMPLARS
from backend.db_qa.intents.taxonomy import Intent

logger = logging.getLogger(__name__)

_HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(_HERE, "output")
INDEX_PATH = os.path.join(OUTPUT_DIR, "intent_exemplar_index.faiss")
META_PATH = os.path.join(OUTPUT_DIR, "intent_exemplar_meta.pkl")

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

TOP_K = 3


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
    logger.info("Wrote intent exemplar index: %s (%d vectors)", INDEX_PATH, len(texts))


_INDEX_CACHE: dict = {}


def _load_index():
    if "index" not in _INDEX_CACHE:
        import faiss
        import pickle

        if not os.path.exists(INDEX_PATH) or not os.path.exists(META_PATH):
            raise FileNotFoundError(
                f"Intent exemplar index not found at {INDEX_PATH} — "
                "run `python -m backend.db_qa.intents.embedding_index` to build it."
            )
        _INDEX_CACHE["index"] = faiss.read_index(INDEX_PATH)
        with open(META_PATH, "rb") as fh:
            _INDEX_CACHE["meta"] = pickle.load(fh)
    return _INDEX_CACHE["index"], _INDEX_CACHE["meta"]


def search_intent(query: str, k: int = TOP_K) -> list[tuple[Intent, float, str]]:
    """Return up to *k* (Intent, cosine_score, matched_exemplar_text)
    tuples, sorted by descending score, filtered to score >= MIN_SCORE.

    Returns [] if the index hasn't been built yet (logged as a warning,
    not raised — callers should treat this the same as "no match" and
    fall through to the next tier, since a missing index is a deploy/
    setup gap, not a per-query error).
    """
    from backend.sql_agent.vectorizer import embed_query
    import numpy as np

    try:
        index, meta = _load_index()
    except FileNotFoundError as exc:
        logger.warning("%s", exc)
        return []

    effective_k = min(k, len(meta))
    if effective_k == 0:
        return []

    q_vec = np.array([embed_query(query)]).astype("float32")
    distances, indices = index.search(q_vec, effective_k)

    results: list[tuple[Intent, float, str]] = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx == -1 or dist < MIN_SCORE:
            continue
        record = meta[idx]
        results.append((Intent(record["intent"]), float(dist), record["text"]))
    return results


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
