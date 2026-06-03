"""DBQA intents sub-package.

Exports:
    IntentPattern   — dataclass describing a single registered intent
    IntentRegistry  — central pattern store with priority-based matching
"""
from backend.db_qa.intents.registry import IntentPattern, IntentRegistry

__all__ = ["IntentPattern", "IntentRegistry"]
