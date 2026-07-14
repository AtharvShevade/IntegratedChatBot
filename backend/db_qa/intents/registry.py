"""Intent registry — central pattern store with priority-based matching.

Usage::

    from backend.db_qa.intents.registry import IntentRegistry, IntentPattern

    registry = IntentRegistry()
    registry.register(
        name="user_list",
        patterns=[r"list\\s+(all\\s+)?users?", r"show\\s+users?"],
        handler=handle_user_list,
        priority=10,
        requires_admin=True,
        description="List all system users",
        examples=["list all users", "show users"],
    )
    intent, match = registry.match("list all users")
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger("dbqa.registry")


@dataclass(slots=True)
class IntentPattern:
    """A single intent registration.

    Attributes:
        name:           Unique intent name (e.g. ``user_list``).
        patterns:       Pre-compiled regex patterns.  First match wins.
        handler:        ``handler(store, params, user_id, is_admin) → dict``
        priority:       Lower = higher priority.  Default 50.
        requires_admin: Non-admin callers get an access-denied result.
                        Deprecated in favor of target_types + access_control.
                        scope_query(), kept for any caller that still reads
                        it directly (e.g. generate_help()'s admin-only note).
        description:    Human-readable label (used in /help output).
        examples:       Sample queries shown in /help.
        target_types:   Accepted target_type entity values for this intent —
                         subset of {"self","other_user","department","role",
                         "return","system_wide"}. Empty tuple means the
                         intent has no access-tiering concept at all (e.g.
                         bank_info/segment_info, always-allowed reference
                         data).
        required_entities:  Entity names that MUST be resolved (from the
                         query or from the session/self context) before the
                         handler can run; missing ones trigger multi-turn
                         slot-filling via _session_context (see Phase 6).
        optional_entities:  Entity names the handler may use if present but
                         doesn't require.
    """

    name: str
    patterns: list[re.Pattern]
    handler: Callable
    priority: int = 50
    requires_admin: bool = False
    description: str = ""
    examples: list[str] = field(default_factory=list)
    target_types: tuple[str, ...] = ()
    required_entities: tuple[str, ...] = ()
    optional_entities: tuple[str, ...] = ()


class IntentRegistry:
    """Thread-safe, priority-ordered store for IntentPattern registrations."""

    def __init__(self) -> None:
        self._intents: list[IntentPattern] = []

    # ── Registration ──────────────────────────────────────────────────────────

    def register(
        self,
        *,
        name: str,
        patterns: list[str],
        handler: Callable,
        priority: int = 50,
        requires_admin: bool = False,
        description: str = "",
        examples: list[str] | None = None,
        target_types: tuple[str, ...] = (),
        required_entities: tuple[str, ...] = (),
        optional_entities: tuple[str, ...] = (),
    ) -> None:
        """Register an intent.  Compiles *patterns* once at registration time."""
        compiled = [re.compile(p, re.IGNORECASE) for p in patterns]
        intent = IntentPattern(
            name=name,
            patterns=compiled,
            handler=handler,
            priority=priority,
            requires_admin=requires_admin,
            description=description,
            examples=examples or [],
            target_types=target_types,
            required_entities=required_entities,
            optional_entities=optional_entities,
        )
        self._intents.append(intent)
        # Re-sort after each registration so the list is always correct
        self._intents.sort(key=lambda x: x.priority)
        logger.debug("[REGISTRY] Registered %r (priority=%d)", name, priority)

    # ── Matching ──────────────────────────────────────────────────────────────

    def match(self, query: str) -> tuple[IntentPattern | None, re.Match | None]:
        """Return (IntentPattern, match_object) for the first pattern hit.

        Patterns are tried in ascending priority order.  Returns ``(None, None)``
        when nothing matches.
        """
        for intent in self._intents:
            for pattern in intent.patterns:
                m = pattern.search(query)
                if m:
                    logger.debug(
                        "[REGISTRY] %r matched %r via %r",
                        query, intent.name, pattern.pattern,
                    )
                    return intent, m
        return None, None

    # ── Introspection ─────────────────────────────────────────────────────────

    def all_intents(self) -> list[IntentPattern]:
        """All registered intents in priority order."""
        return list(self._intents)

    def get(self, name: str) -> IntentPattern | None:
        """Look up a registered intent by name."""
        for intent in self._intents:
            if intent.name == name:
                return intent
        return None

    def generate_help(self) -> str:
        """Build a Markdown help string from all registered intents."""
        lines: list[str] = ["**Available queries:**\n"]
        for intent in self._intents:
            if not intent.description:
                continue
            admin_note = " _(admin only)_" if intent.requires_admin else ""
            lines.append(f"• **{intent.description}**{admin_note}")
            for ex in intent.examples[:2]:
                lines.append(f'  _e.g. "{ex}"_')
        return "\n".join(lines)

    def debug_all(self) -> list[dict[str, Any]]:
        """Return a list of dicts summarising all registrations (for diagnostics)."""
        return [
            {
                "name": i.name,
                "priority": i.priority,
                "requires_admin": i.requires_admin,
                "pattern_count": len(i.patterns),
                "examples": i.examples,
            }
            for i in self._intents
        ]
