"""Canonical intent registry — built FROM backend.db_qa.intents.taxonomy.

Previously this module hand-duplicated a ~90-rule regex ruleset that
overlapped (and drifted from) backend/db_qa/intent_classifier.py's actual
regex patterns, wired into an unused class-based router
(backend/db_qa/router.py). That whole path had no live importer anywhere in
the app and has been retired.

This module now does one thing: register every Intent from
backend.db_qa.intents.taxonomy into a REGISTRY (IntentRegistry instance),
carrying over each IntentSpec's target_types/required_entities/
optional_entities so any caller that wants registry-style introspection
(e.g. a /help listing, or a future debug endpoint) has a single, correct
source of truth — instead of a second hand-maintained rule list.

Regex PATTERN MATCHING itself still lives in intent_classifier.py (Phase 6
wires intent_classifier's classify() output onto these same Intent names).
This registry does not perform matching for the live request path; it's a
structured catalog + optional matching capability for tooling/introspection.
"""
from __future__ import annotations

from backend.db_qa.intents.registry import IntentRegistry
from backend.db_qa.intents.taxonomy import Intent, INTENT_SPECS

REGISTRY = IntentRegistry()


def _noop_handler(store, params, user_id, is_admin):  # pragma: no cover
    """Placeholder — real dispatch goes through query_handlers.dispatch2()
    (Phase 4), not through this registry's .handler field. Present only so
    IntentRegistry's dataclass contract (handler: Callable, required) is
    satisfied for intents registered here purely for introspection.
    """
    raise NotImplementedError(
        "This registry is for introspection only — dispatch via "
        "query_handlers.dispatch2(), not IntentRegistry.match().handler"
    )


for _intent, _spec in INTENT_SPECS.items():
    # requires_admin is a coarse /help-display hint only — actual admission
    # decisions are made per-request by access_control.scope_query() (Phase
    # 3), which knows the caller's resolved target_type, not just the
    # intent's set of *possible* target_types. An intent counts as
    # "requires_admin" here only if NONE of its accepted target_types is
    # "self" (i.e. there is no self-service phrasing of this question at
    # all) — reference-data intents with no target_types are never flagged.
    _requires_admin = bool(_spec.target_types) and "self" not in _spec.target_types

    REGISTRY.register(
        name=_intent.value,
        patterns=[],  # no regex here — intent_classifier.py owns matching
        handler=_noop_handler,
        description=_spec.description,
        requires_admin=_requires_admin,
        target_types=_spec.target_types,
        required_entities=_spec.required_entities,
        optional_entities=_spec.optional_entities,
    )
