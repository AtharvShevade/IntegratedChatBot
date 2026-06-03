"""Generic filter engine for DBQA record sets.

Supports:
  - StatusFilter        — active, inactive, approved, pending, failed, in_progress, new
  - FieldFilter         — exact equality on any field
  - ContainsFilter      — case-insensitive substring on any field
  - RegexFilter         — compiled regex on any field
  - CompositeAndFilter  — all sub-filters must pass (AND)
  - CompositeOrFilter   — at least one sub-filter must pass (OR)
  - FilterEngine        — accumulates filters and applies them together (implicit AND)

Usage::

    from backend.db_qa.filters import FilterEngine, StatusFilter, FieldFilter

    results = (
        FilterEngine()
        .add(StatusFilter("active"))
        .add(FieldFilter("DeptName", "Finance"))
        .apply(store.users())
    )
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any, Callable


# ── Abstract base ─────────────────────────────────────────────────────────────

class BaseFilter(ABC):
    """Base class for all filter types."""

    @abstractmethod
    def match(self, record: dict) -> bool: ...

    def apply(self, records: list[dict]) -> list[dict]:
        return [r for r in records if self.match(r)]


# ── Concrete filters ──────────────────────────────────────────────────────────

class StatusFilter(BaseFilter):
    """Filter records by Status field using friendly label → raw XML value mapping.

    Recognised labels:
      active / inactive / approved / audited / pending / failed / in_progress / new
    """

    # Maps friendly label → callable predicate on a record dict
    _RULES: dict[str, Callable[[dict], bool]] = {
        "active":      lambda r: r.get("Status", "").lower() == "true",
        "inactive":    lambda r: r.get("Status", "").lower() not in ("true",),
        "approved":    lambda r: r.get("Status", "") in ("9", "11"),
        "audited":     lambda r: r.get("Status", "") in ("9", "11"),
        "pending":     lambda r: r.get("Status", "") in ("0", "1", "2"),
        "failed":      lambda r: r.get("Status", "") in ("3", "4", "5"),
        "in_progress": lambda r: r.get("Status", "") in ("1", "6"),
        "new":         lambda r: r.get("Status", "") == "0",
    }

    def __init__(self, status: str) -> None:
        self._rule: Callable[[dict], bool] | None = self._RULES.get(status.lower())
        self._status = status

    def match(self, record: dict) -> bool:
        # Unknown status label → pass-through (no filtering)
        return self._rule(record) if self._rule is not None else True


class FieldFilter(BaseFilter):
    """Exact equality filter on a named field."""

    def __init__(self, field: str, value: str, *, case_insensitive: bool = True) -> None:
        self._field = field
        self._value = value.lower() if case_insensitive else value
        self._ci = case_insensitive

    def match(self, record: dict) -> bool:
        v = record.get(self._field, "")
        return (v.lower() if self._ci else v) == self._value


class ContainsFilter(BaseFilter):
    """Case-insensitive substring filter on a named field."""

    def __init__(self, field: str, substring: str) -> None:
        self._field = field
        self._sub = substring.lower()

    def match(self, record: dict) -> bool:
        return self._sub in record.get(self._field, "").lower()


class RegexFilter(BaseFilter):
    """Pre-compiled regex filter on a named field."""

    def __init__(self, field: str, pattern: str) -> None:
        self._field = field
        self._re = re.compile(pattern, re.IGNORECASE)

    def match(self, record: dict) -> bool:
        return bool(self._re.search(record.get(self._field, "")))


class LambdaFilter(BaseFilter):
    """Arbitrary predicate filter — for one-off scenarios."""

    def __init__(self, predicate: Callable[[dict], bool]) -> None:
        self._pred = predicate

    def match(self, record: dict) -> bool:
        return self._pred(record)


# ── Composite filters ─────────────────────────────────────────────────────────

class CompositeAndFilter(BaseFilter):
    """All sub-filters must match (AND semantics)."""

    def __init__(self, *filters: BaseFilter) -> None:
        self._filters = list(filters)

    def match(self, record: dict) -> bool:
        return all(f.match(record) for f in self._filters)


class CompositeOrFilter(BaseFilter):
    """At least one sub-filter must match (OR semantics)."""

    def __init__(self, *filters: BaseFilter) -> None:
        self._filters = list(filters)

    def match(self, record: dict) -> bool:
        return any(f.match(record) for f in self._filters)


# ── Engine ────────────────────────────────────────────────────────────────────

class FilterEngine:
    """Accumulate filters and apply them together (implicit AND).

    Chainable usage::

        results = FilterEngine().add(StatusFilter("active")).add(FieldFilter("DeptName", "IT")).apply(records)
    """

    def __init__(self) -> None:
        self._filters: list[BaseFilter] = []

    def add(self, f: BaseFilter) -> "FilterEngine":
        """Add a filter; returns *self* for chaining."""
        self._filters.append(f)
        return self

    def reset(self) -> "FilterEngine":
        """Clear all accumulated filters."""
        self._filters.clear()
        return self

    def apply(self, records: list[dict]) -> list[dict]:
        """Apply all accumulated filters to *records* (AND of all conditions)."""
        if not self._filters:
            return list(records)
        composite = CompositeAndFilter(*self._filters)
        return composite.apply(records)

    def count(self, records: list[dict]) -> int:
        """Return the count of matching records without building a new list."""
        if not self._filters:
            return len(records)
        composite = CompositeAndFilter(*self._filters)
        return sum(1 for r in records if composite.match(r))
