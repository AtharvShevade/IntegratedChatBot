"""Structured intent-classification outcome logging — one JSON line per query.

Unlike backend.utils.debug.debug_log (which is DEBUG-gated and produces
human-readable blocks, silent in production), this logger always writes
at INFO level in a machine-parseable JSONL format, so classification
outcomes can be mined later to tune the semantic-matching tier and
prioritize exemplar coverage — without needing to enable verbose debug
logging or parse free-text log blocks.

Output: logs/intent_classifications.jsonl (one file, appended forever —
not date-rotated, since this is a dataset to mine over time, not a daily
operational log).

Usage::

    from backend.utils.intent_log import log_intent_outcome

    log_intent_outcome(
        query="who owns this report?",
        tier="regex",
        intent="report_owner",
        found=True,
    )
"""
from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone

from backend.utils.logger import LOG_DIR

logger = logging.getLogger(__name__)

INTENT_LOG_PATH = os.path.join(LOG_DIR, "intent_classifications.jsonl")
FEEDBACK_LOG_PATH = os.path.join(LOG_DIR, "feedback.jsonl")

_lock = threading.Lock()
_feedback_lock = threading.Lock()


def log_intent_outcome(
    query: str,
    tier: str,
    intent: str | None,
    found: bool,
    **extra,
) -> None:
    """Append one JSON line recording a single intent-classification attempt.

    Parameters
    ----------
    query:
        The raw user message (truncated to 500 chars — enough for any
        realistic chat question, without unbounded log growth).
    tier:
        Which classification stage produced this outcome, e.g. "regex",
        "embedding", "llm_disambiguation", "fallback".
    intent:
        The matched intent value, or None if this tier didn't match.
    found:
        Whether this tier resolved to a confident intent.
    **extra:
        Additional fields to record (e.g. confidence score, session_id) —
        merged directly into the JSON record.
    """
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "query": query[:500],
        "tier": tier,
        "intent": intent,
        "found": found,
        **extra,
    }
    line = json.dumps(record, ensure_ascii=False)
    try:
        with _lock:
            os.makedirs(LOG_DIR, exist_ok=True)
            with open(INTENT_LOG_PATH, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
    except OSError as exc:
        logger.warning("Failed to write intent classification log: %s", exc)


def log_feedback(
    rating: str,
    query: str | None = None,
    intent: str | None = None,
    result_type: str | None = None,
    session_id: str | None = None,
) -> None:
    """Append one JSON line recording a user's thumbs up/down on a response.

    Kept in a separate file from log_intent_outcome — feedback is a
    per-response quality signal (join key: query/intent/session_id), while
    the classification log is a per-tier routing trace; mining either
    independently should not require filtering the other out.
    """
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "rating": rating,
        "query": (query or "")[:500] or None,
        "intent": intent,
        "result_type": result_type,
        "session_id": session_id,
    }
    line = json.dumps(record, ensure_ascii=False)
    try:
        with _feedback_lock:
            os.makedirs(LOG_DIR, exist_ok=True)
            with open(FEEDBACK_LOG_PATH, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
    except OSError as exc:
        logger.warning("Failed to write feedback log: %s", exc)
