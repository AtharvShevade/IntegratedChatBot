"""Query handlers package — dual dispatch during incremental migration.

Historically this was a single flat module (query_handlers.py) holding ~90
handler functions, one per db_* intent, plus a dispatch(intent, params,
user_id, role_id, is_admin, store) entry point and an INTENT_TO_HANDLER
dict. That code is now query_handlers/legacy.py, moved VERBATIM (byte-for-
byte reflow into the new package, no logic changes) — every symbol it
exported is re-exported here so existing importers
(backend/agent/db_qa_router.py, backend/db_qa/__init__.py) keep working
with zero changes: `from backend.db_qa import query_handlers` then
`query_handlers.dispatch(...)`, `query_handlers.INTENT_TO_HANDLER`,
`query_handlers.handle_unknown` all still resolve exactly as before.

The new intent-scoped dispatcher (dispatch2, NEW_INTENT_TO_HANDLER,
handle_unknown_new) lives in dispatcher.py and is re-exported below.
"""
from __future__ import annotations

# ── Legacy re-exports (zero behavior change for existing importers) ────────
from backend.db_qa.query_handlers.legacy import (  # noqa: F401
    dispatch,
    HANDLERS,
    INTENT_TO_HANDLER,
    handle_unknown,
    # Individual handle_* functions are NOT all re-exported by name here —
    # any caller needing one directly should import
    # backend.db_qa.query_handlers.legacy explicitly. dispatch()/
    # INTENT_TO_HANDLER/handle_unknown are the only symbols the live
    # request path (agent/db_qa_router.py) actually touches (confirmed by
    # grep), so those are the compatibility surface that matters.
)

# ── New taxonomy-based dispatch (see dispatcher.py) ─────────────────────────
from backend.db_qa.query_handlers.dispatcher import (  # noqa: F401
    dispatch2,
    NEW_INTENT_TO_HANDLER,
    handle_unknown_new,
)

__all__ = [
    "dispatch", "HANDLERS", "INTENT_TO_HANDLER", "handle_unknown",
    "dispatch2", "NEW_INTENT_TO_HANDLER", "handle_unknown_new",
]
