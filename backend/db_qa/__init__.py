"""backend.db_qa — Structured Q&A module for iDEAL application database.

Integrates intent classification, XML data lookup, and LLM formatting
into the main chatbot decision pipeline.

Public exports:
  - intent_classifier.classify()     — Regex-based intent detection
  - query_handlers.dispatch()        — Execute intent handler
  - xml_store.XMLStore              — In-memory XML cache
  - beautifier.beautify_stream()    — LLM formatting wrapper
"""
from __future__ import annotations

from backend.db_qa import beautifier, intent_classifier, query_handlers, xml_store
from backend.db_qa.config import (
    APP_DB_ADMIN_ROLE_ID,
    APP_DB_BASE_PATH,
    APP_DB_BEAUTIFY_MODEL,
    APP_DB_ENABLE_BEAUTIFY,
)

__all__ = [
    # Config
    "APP_DB_BASE_PATH",
    "APP_DB_ADMIN_ROLE_ID",
    "APP_DB_ENABLE_BEAUTIFY",
    "APP_DB_BEAUTIFY_MODEL",
    # Modules
    "intent_classifier",
    "query_handlers",
    "xml_store",
    "beautifier",
]
