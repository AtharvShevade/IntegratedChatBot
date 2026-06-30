"""Modular DBQA query router.

Entry point::

    from backend.db_qa.router import QueryRouter
    from backend.db_qa.intents.definitions import REGISTRY

    router = QueryRouter(REGISTRY)
    result = router.route("list active users", user_id="104", role_id="101", store=store, is_admin=True)

Full pipeline:
  1. Normalize query          (backend.db_qa.utils.normalizer)
  2. Match intent             (IntentRegistry)
  3. Extract entities         (backend.db_qa.extractors)
  4. Admin-access guard
  5. Invoke handler           (IntentPattern.handler)
  6. Return structured result

Also provides ``debug_query(query, store)`` for diagnostics without
executing any handler.
"""
from __future__ import annotations

import logging
from typing import Any

from backend.db_qa.xml_store import XMLStore
from backend.db_qa.utils.normalizer import normalize, tokenize
from backend.db_qa.utils.fuzzy import ranked_matches
from backend.db_qa.extractors import (
    extract_user,
    extract_dept,
    extract_role,
    extract_return,
    extract_status,
)
from backend.db_qa.intents.registry import IntentRegistry, IntentPattern

logger = logging.getLogger("dbqa.router")

# ── Access-denied template ────────────────────────────────────────────────────
_ACCESS_DENIED: dict[str, Any] = {
    "label": "Access Denied",
    "found": False,
    "records": [],
    "summary": (
        "You do not have permission to view this information. "
        "Please contact your system administrator."
    ),
    "meta": {},
}


class QueryRouter:
    """Route normalised queries to the correct handler via an IntentRegistry.

    Separation of concerns:
      - Normalisation  → ``utils.normalizer``
      - Pattern match  → ``IntentRegistry``
      - Entity extract → ``extractors``
      - Business logic → individual handler functions
      - Formatting     → ``formatters`` (optional, caller's choice)
    """

    def __init__(self, registry: IntentRegistry) -> None:
        self._registry = registry

    # ── Public API ────────────────────────────────────────────────────────────

    def route(
        self,
        query: str,
        *,
        user_id: str,
        role_id: str,
        store: XMLStore,
        is_admin: bool = False,
    ) -> dict[str, Any]:
        """Full pipeline: normalize → match → extract → guard → invoke.

        Args:
            query:    Raw user input.
            user_id:  Current user's UserId (numeric string).
            role_id:  Current user's RoleId (for admin checks).
            store:    Live XMLStore instance.
            is_admin: Pre-computed admin flag from the caller.

        Returns:
            A ``QueryResult`` dict compatible with existing handler outputs::

                {intent, label, found, records, summary, meta}
        """
        # Keep all words (including "my", "who", "what") for pattern matching;
        # many intents rely on pronouns like \bmy\b to distinguish self-service
        # from admin queries.
        norm = normalize(query, strip_stops=False)
        logger.debug("[ROUTER] raw=%r  norm=%r", query, norm)

        intent, _match_obj = self._registry.match(norm)

        if intent is None:
            return self._no_match(normalize(query))  # stripped version for suggestions

        # Access-control guard
        if intent.requires_admin and not is_admin:
            result = dict(_ACCESS_DENIED)
            result["intent"] = intent.name
            return result

        # Entity extraction (uses full normalised query with prepositions)
        params = self._extract_entities(norm, store)
        logger.debug("[ROUTER] intent=%r params=%r", intent.name, params)

        # Invoke handler
        try:
            result = intent.handler(store, params, user_id, is_admin)
        except Exception as exc:
            logger.exception("[ROUTER] Handler %r raised: %s", intent.name, exc)
            return {
                "intent": intent.name,
                "label": "Error",
                "found": False,
                "records": [],
                "summary": "An error occurred while processing your query.",
                "meta": {},
            }

        return result

    def debug_query(self, query: str, store: XMLStore | None = None) -> dict[str, Any]:
        """Return diagnostic info for *query* without invoking any handler.

        Useful for troubleshooting mis-matches in development / admin tools.

        Returns::

            {
                original, normalized, tokens,
                matched_intent, confidence,
                extracted_entities,
                suggestions,
            }
        """
        norm = normalize(query, strip_stops=False)
        tokens = tokenize(query)
        intent, _m = self._registry.match(norm)

        entities: dict[str, Any] = {}
        if store is not None:
            for extractor, key in (
                (extract_user,   "user"),
                (extract_dept,   "dept"),
                (extract_return, "return"),
                (extract_role,   "role"),
            ):
                r = extractor(norm, store)  # type: ignore[operator]
                if r:
                    entities[key] = {
                        "value":      r.value,
                        "confidence": r.confidence,
                        "source":     r.source,
                    }
            st = extract_status(norm)
            if st:
                entities["status"] = st

        return {
            "original":           query,
            "normalized":         norm_stripped,
            "tokens":             tokens,
            "matched_intent":     intent.name if intent else None,
            "requires_admin":     intent.requires_admin if intent else None,
            "confidence":         100 if intent else 0,
            "extracted_entities": entities,
            "suggestions":        [] if intent else self._suggest(norm_stripped),
        }

    # ── Private helpers ───────────────────────────────────────────────────────

    def _no_match(self, norm: str) -> dict[str, Any]:
        return {
            "intent":  "UNKNOWN",
            "label":   "No Match",
            "found":   False,
            "records": [],
            "summary": (
                "I couldn't understand that query. "
                "Try rephrasing, or type **help** to see available commands."
            ),
            "meta": {
                "suggestions": self._suggest(norm),
                "normalized":  norm,
            },
        }

    def _extract_entities(self, norm: str, store: XMLStore) -> dict[str, Any]:
        """Run all extractors; merge results into a unified params dict."""
        params: dict[str, Any] = {}

        u = extract_user(norm, store)
        if u:
            params["target_user"] = u.value

        d = extract_dept(norm, store)
        if d:
            params["target_dept"] = d.value
            params["target_department"] = d.value  # alias used by some handlers

        r = extract_return(norm, store)
        if r:
            params["target_return"] = r.value

        rol = extract_role(norm, store)
        if rol:
            params["target_role"] = rol.value

        st = extract_status(norm)
        if st:
            params["status_filter"] = st

        return params

    def _suggest(self, norm: str) -> list[str]:
        """Return up to 3 example queries most similar to *norm* (for Did-you-mean)."""
        all_examples: list[str] = [
            ex
            for intent in self._registry.all_intents()
            for ex in intent.examples
        ]
        return [ex for ex, _ in ranked_matches(norm, all_examples, threshold=30, limit=3)]
