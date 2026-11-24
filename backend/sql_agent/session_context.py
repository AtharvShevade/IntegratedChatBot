# backend/sql_agent/session_context.py
#
# Per-session memory of the SQL agent's last answer, so a follow-up such as
# "which bucket is highest?" or "same for F013" can be understood against it.
#
# In-process only (like agent/router.py's _session_context): bounded by an LRU
# cap and a TTL, holds at most MAX_ROWS result rows per session, and is never
# persisted. Losing it (restart, TTL) only means a follow-up is treated as a
# fresh question — exactly today's behaviour.

from __future__ import annotations

import re
import threading
import time
from collections import OrderedDict
from typing import Any

__all__ = [
    "save_result", "save_pending_clarification", "get", "clear_pending",
    "has_context", "looks_like_followup", "is_self_contained_question", "MAX_ROWS",
]

TTL_SEC = 30 * 60
MAX_SESSIONS = 500
MAX_ROWS = 50

_lock = threading.Lock()
_store: "OrderedDict[str, dict[str, Any]]" = OrderedDict()


def _put(session_id: str, ctx: dict[str, Any]) -> None:
    ctx["ts"] = time.monotonic()
    with _lock:
        _store[session_id] = ctx
        _store.move_to_end(session_id)
        while len(_store) > MAX_SESSIONS:
            _store.popitem(last=False)


def get(session_id: str | None) -> dict[str, Any] | None:
    if not session_id:
        return None
    with _lock:
        ctx = _store.get(session_id)
        if ctx is None:
            return None
        if time.monotonic() - ctx.get("ts", 0) > TTL_SEC:
            _store.pop(session_id, None)
            return None
        return ctx


def save_result(
    session_id: str | None, *, question: str, returns: list[str], tables: list[str],
    sql: str, columns: list[str], rows: list[list], period_label: str | None,
) -> None:
    """Remember the last successfully answered question for this session."""
    if not session_id:
        return
    _put(session_id, {
        "question": question,
        "returns": list(returns or []),
        "tables": list(tables or []),
        "sql": sql,
        "columns": list(columns or []),
        "rows": list(rows or [])[:MAX_ROWS],
        "row_count": len(rows or []),
        "period_label": period_label,
        "pending": None,
    })


def save_pending_clarification(session_id: str | None, *, question: str, options: list[str]) -> None:
    """Remember a question the agent asked the user to disambiguate, keeping
    the previous answer (if any) for later follow-ups."""
    if not session_id:
        return
    prev = get(session_id) or {}
    ctx = {k: v for k, v in prev.items() if k != "ts"}
    ctx["pending"] = {"question": question, "options": list(options)}
    _put(session_id, ctx)


def clear_pending(session_id: str | None) -> None:
    ctx = get(session_id)
    if ctx is not None:
        ctx["pending"] = None


def has_context(session_id: str | None) -> bool:
    ctx = get(session_id)
    return bool(ctx and (ctx.get("pending") or ctx.get("sql")))


# Referential / follow-up wording: pronouns pointing at the shown result,
# comparative/aggregate asks about it, or "same ... for X" refinements.
_FOLLOWUP_RE = re.compile(
    r"\b(it|its|this|that|these|those|them|they|above|previous|same|also|again|instead|"
    r"highest|lowest|largest|smallest|maximum|minimum|top|bottom|rank|"
    r"total|sum|average|avg|mean|percent(age)?|share|"
    r"explain|why|meaning|mean|summari[sz]e|insight|"
    r"which|difference|change|increase|decrease|"
    r"sort|order|filter|only|exclude|include|"
    r"what\s+about|how\s+about|and\s+for|now\s+for|for\s+the\s+(previous|last|next)|"
    r"(previous|last|prior|next)\s+(quarter|month|year|period|date))\b",
    re.IGNORECASE,
)


# Words that point back at the previously shown result. A message containing any
# of them is a follow-up even when it also names a return ("same for LR").
_REFERENTIAL_RE = re.compile(
    r"\b(it|its|this|that|these|those|them|they|above|previous|same|also|again|instead|"
    r"what\s+about|how\s+about|and\s+for|now\s+for|shown|result|results)\b",
    re.IGNORECASE,
)


def is_self_contained_question(message: str) -> bool:
    """True for a NEW question that names its own return and does not refer back
    to the shown result -- e.g. "show the total loan for cims raq". Such a message
    must be answered with fresh SQL, never from the previous result table."""
    msg = (message or "").strip()
    if not msg or _REFERENTIAL_RE.search(msg):
        return False
    try:
        from backend.sql_agent.context_resolver import detect_returns
        return bool(detect_returns(msg))
    except Exception:  # pragma: no cover - never let this guard break routing
        return False


def looks_like_followup(session_id: str | None, message: str) -> bool:
    """Cheap router-side check: should this message go back to the SQL agent
    because it continues the session's last SQL answer / pending question?"""
    ctx = get(session_id)
    if not ctx:
        return False
    msg = (message or "").strip()
    if not msg:
        return False
    pending = ctx.get("pending")
    if pending:
        low = msg.lower()
        if any(low == o.lower() or low in o.lower() or o.lower() in low for o in pending["options"]):
            return True
        if len(msg.split()) <= 8:
            return True
    if not ctx.get("sql"):
        return False
    return len(msg.split()) <= 25 and bool(_FOLLOWUP_RE.search(msg))
