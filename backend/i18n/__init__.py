"""Multilingual translation boundary for /chat and /guided.

    user language -> English -> existing English pipeline -> English -> user language

The English pipeline is untouched. backend/agent/__init__.py:811 decide() sees
exactly the English string it would have seen before this package existed, and
returns exactly the dict it returned before. Everything here happens strictly
outside it, at the endpoint.

Why the boundary is at the endpoint and not inside the agent: routing is
entirely English string matching on ``lower_q`` (agent/__init__.py:821) feeding
the regex fast-paths (:378-449), the db_qa taxonomy classifier, and the
FAISS/bge-large-en retrieval -- an English-only embedder. Translating before
decide() preserves all of it. Translating inside it would break all of it.

Turning MULTILINGUAL_ENABLED off, or omitting ``lang``, makes every function
here an identity: no model call, no mutation, no new response keys.
"""
from __future__ import annotations

from backend.i18n.boundary import (
    InboundResult,
    OutboundResult,
    inbound_failure_response,
    normalize_lang,
    should_translate,
    translate_inbound,
    translate_outbound,
)
from backend.i18n.config import is_enabled, runtime_config, translation_model

__all__ = [
    "InboundResult",
    "OutboundResult",
    "inbound_failure_response",
    "is_enabled",
    "normalize_lang",
    "runtime_config",
    "should_translate",
    "translate_inbound",
    "translate_outbound",
    "translation_model",
]
