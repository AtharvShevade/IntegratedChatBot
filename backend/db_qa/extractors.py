"""Smart entity extraction for DBQA queries.

Uses fuzzy/partial matching with alias support — no ML.

All extractors accept the *full* normalised query plus the live XMLStore so
they can look up actual names/IDs from the XML data at call time.

Public API::

    extract_user(query, store)   → ExtractionResult | None
    extract_dept(query, store)   → ExtractionResult | None
    extract_role(query, store)   → ExtractionResult | None
    extract_return(query, store) → ExtractionResult | None
    extract_status(query)        → str | None

``ExtractionResult`` fields: value, raw, confidence, source
"""
from __future__ import annotations

import logging
import re
from typing import NamedTuple

from backend.db_qa.xml_store import XMLStore
from backend.db_qa.utils.fuzzy import best_match

logger = logging.getLogger("dbqa.extractors")


# ── Result type ───────────────────────────────────────────────────────────────

class ExtractionResult(NamedTuple):
    value: str       # Matched / resolved canonical value
    raw: str         # Original token from query
    confidence: int  # 0-100
    source: str      # "exact" | "partial" | "fuzzy" | "alias"


# ── Alias maps (extend these as your data grows) ──────────────────────────────

_DEPT_ALIASES: dict[str, str] = {
    "fin":        "Finance",
    "hr":         "Human Resources",
    "it":         "Information Technology",
    "ops":        "Operations",
    "compliance": "Compliance",
}

_RETURN_ALIASES: dict[str, str] = {
    "lr":    "CIMS_LR",
    "raq":   "CIMS_RAQ",
    "gold":  "ImportOfGold",
    "rof":   "ROF",
    "gpb":   "CIMS_FormGPB",
}

_STATUS_ALIASES: dict[str, str] = {
    "ok":          "approved",
    "done":        "approved",
    "passed":      "approved",
    "approved":    "approved",
    "accepted":    "approved",
    "audited":     "approved",
    "pending":     "pending",
    "waiting":     "pending",
    "open":        "pending",
    "running":     "in_progress",
    "processing":  "in_progress",
    "in progress": "in_progress",
    "in_progress": "in_progress",
    "failed":      "failed",
    "rejected":    "failed",
    "error":       "failed",
    "new":         "new",
    "active":      "active",
    "enabled":     "active",
    "inactive":    "inactive",
    "disabled":    "inactive",
}

# ── Regex helpers ─────────────────────────────────────────────────────────────

_QUOTED_RE = re.compile(r'"([^"]+)"|\'([^\']+)\'')


def _quoted(query: str) -> str | None:
    """Extract a quoted substring from *query*, if present."""
    m = _QUOTED_RE.search(query)
    return (m.group(1) or m.group(2)) if m else None


def _tokens_after(query: str, *keywords: str, max_tokens: int = 3) -> str | None:
    """Return up to *max_tokens* words following the first keyword match."""
    for kw in keywords:
        m = re.search(
            rf"\b{re.escape(kw)}\b\s+((?:\S+\s*){{1,{max_tokens}}})",
            query,
            re.IGNORECASE,
        )
        if m:
            return m.group(1).strip().rstrip("?.,;:")
    return None


# ── User extractor ────────────────────────────────────────────────────────────

def extract_user(query: str, store: XMLStore) -> ExtractionResult | None:
    """Resolve a user name / ID from *query* using the live XMLStore.

    Strategy order:
      1. Quoted string → exact store lookup
      2. Tokens after anchor keywords → exact then fuzzy
      3. Short query (≤4 tokens) → full-query fuzzy
    """
    all_names = [u.get("Name", "") for u in store.users() if u.get("Name")]
    all_logins = [u.get("LoginId", "").lower() for u in store.users() if u.get("LoginId")]

    def _resolve(raw: str) -> ExtractionResult | None:
        if not raw:
            return None
        rl = raw.strip().lower()

        # Exact match via LoginId or display Name
        u = store.user_by_name(rl)
        if u:
            return ExtractionResult(u.get("Name", rl), raw, 100, "exact")

        # Fuzzy on display names (threshold=65 — generous for partial names)
        match = best_match(rl, all_names, threshold=65)
        if match:
            return ExtractionResult(match, raw, 80, "fuzzy")

        # Fuzzy on login IDs
        match = best_match(rl, all_logins, threshold=75)
        if match:
            u = store.user_by_name(match)
            name = u.get("Name", match) if u else match
            return ExtractionResult(name, raw, 80, "fuzzy")

        return None

    # 1. Quoted
    q = _quoted(query)
    if q:
        r = _resolve(q)
        if r:
            return r

    # 2. After anchor keywords
    raw = _tokens_after(query, "user", "profile", "for", "by", "about", "named", "called")
    if raw:
        r = _resolve(raw)
        if r:
            return r

    # 3. Short query — full fuzzy attempt
    if len(query.split()) <= 4:
        r = _resolve(query)
        if r:
            return r

    return None


# ── Department extractor ──────────────────────────────────────────────────────

def extract_dept(query: str, store: XMLStore) -> ExtractionResult | None:
    """Resolve a department name from *query*."""
    all_depts = [d.get("Name", "") for d in store.departments() if d.get("Name")]

    def _resolve(raw: str) -> ExtractionResult | None:
        if not raw:
            return None
        rl = raw.strip().lower()

        # Alias check first
        if rl in _DEPT_ALIASES:
            canonical = _DEPT_ALIASES[rl]
            if store.dept_by_name(canonical):
                return ExtractionResult(canonical, raw, 100, "alias")

        # Exact
        d = store.dept_by_name(rl)
        if d:
            return ExtractionResult(d.get("Name", rl), raw, 100, "exact")

        # Fuzzy
        match = best_match(rl, all_depts, threshold=70)
        if match:
            return ExtractionResult(match, raw, 80, "fuzzy")

        return None

    q = _quoted(query)
    if q:
        r = _resolve(q)
        if r:
            return r

    raw = _tokens_after(query, "department", "dept", "in", "for", "from", "of")
    if raw:
        r = _resolve(raw)
        if r:
            return r

    return None


# ── Role extractor ────────────────────────────────────────────────────────────

def extract_role(query: str, store: XMLStore) -> ExtractionResult | None:
    """Resolve a role name from *query*."""
    all_roles = [r.get("Name", "") for r in store.roles() if r.get("Name")]

    def _resolve(raw: str) -> ExtractionResult | None:
        if not raw:
            return None
        rl = raw.strip().lower()
        r = store.role_by_name(rl)
        if r:
            return ExtractionResult(r.get("Name", rl), raw, 100, "exact")
        match = best_match(rl, all_roles, threshold=70)
        if match:
            return ExtractionResult(match, raw, 80, "fuzzy")
        return None

    q = _quoted(query)
    if q:
        r = _resolve(q)
        if r:
            return r

    raw = _tokens_after(query, "role", "with", "as", "having", "assigned")
    if raw:
        r = _resolve(raw)
        if r:
            return r

    return None


# ── Return / Report extractor ─────────────────────────────────────────────────

def extract_return(query: str, store: XMLStore) -> ExtractionResult | None:
    """Resolve a return / report name from *query*."""
    all_xbrl = [r.get("Name", "") for r in store.returns() if r.get("Name")]
    all_non = [r.get("Name", "") for r in store.non_xbrl_returns() if r.get("Name")]
    all_names = all_xbrl + all_non
    all_lower = [n.lower() for n in all_names]

    def _resolve(raw: str) -> ExtractionResult | None:
        if not raw:
            return None
        rl = raw.strip().lower()

        # Alias
        if rl in _RETURN_ALIASES:
            canonical = _RETURN_ALIASES[rl]
            match = best_match(canonical.lower(), all_lower, threshold=60)
            if match:
                idx = all_lower.index(match)
                return ExtractionResult(all_names[idx], raw, 100, "alias")

        # Exact
        r = store.return_by_name(rl)
        if r:
            return ExtractionResult(r.get("Name", rl), raw, 100, "exact")

        # Fuzzy
        match = best_match(rl, all_names, threshold=65)
        if match:
            return ExtractionResult(match, raw, 80, "fuzzy")

        return None

    q = _quoted(query)
    if q:
        r = _resolve(q)
        if r:
            return r

    raw = _tokens_after(query, "return", "report", "form", "for", "of")
    if raw:
        r = _resolve(raw)
        if r:
            return r

    return None


# ── Status extractor ──────────────────────────────────────────────────────────

def extract_status(query: str) -> str | None:
    """Return a canonical status string from *query*, or None.

    Returns one of: 'approved', 'pending', 'failed', 'in_progress',
    'new', 'active', 'inactive'.
    """
    q_lower = query.lower()
    for kw, canonical in _STATUS_ALIASES.items():
        if re.search(rf"\b{re.escape(kw)}\b", q_lower):
            return canonical
    return None
