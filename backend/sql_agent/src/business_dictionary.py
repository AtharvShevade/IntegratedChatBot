"""
Business-term registry — Phase 1 of the retrieval accuracy roadmap.

Loads business_dictionary.yaml (aliases, acronyms, synonyms) from
config.EMBEDDING_DIR into three lookup structures. This is the SINGLE place expansion/alias logic
lives; src/retriever.py's `_expand_query` and the query-rewrite layer
(src/query_rewrite.py) both delegate here rather than each re-implementing
their own regex list.

Why not keep the old `_QUERY_EXPANSIONS` list in retriever.py: it is
acronym-only (a plain find/replace) and cannot express an ALIAS (a surface
form that pins one specific table), which is what fixes real source-data label
drift — see the "part b"/"part c" collision comment inline in the yaml file for
a concrete, confirmed case. A hardcoded Python list also cannot grow with the
dataset the way a YAML file — versioned and lintable the same way
`semantic_layer.yaml`/`qa_pairs.json` already are in this codebase — can.
"""
import logging
import os
import re

import yaml

from src import config

log = logging.getLogger("business_dictionary")

def _default_path() -> str:
    """Resolved at call time (not import time) so an EMBEDDING_DIR override or
    reassignment is honored — same discipline every other artifact path in
    this package follows (see src/config.py's EMBEDDING_DIR docstring)."""
    return os.path.join(config.EMBEDDING_DIR, "business_dictionary.yaml")

# Structural transforms (any digit, any letter) rather than fixed vocabulary —
# these stay as code, not data rows, exactly as _QUERY_EXPANSIONS in
# retriever.py already did for "sec4" -> "section 4" / "parta" -> "part A".
_STRUCTURAL_PATTERNS = [
    (re.compile(r"\bsec(\d+)\b", re.IGNORECASE), r"section \1"),
    (re.compile(r"\bparta\b", re.IGNORECASE), "part A"),
    (re.compile(r"\bpartb\b", re.IGNORECASE), "part B"),
]

_cache: dict = {}


def _compile_acronym_patterns(entries):
    """One whole-word, case-insensitive regex per acronym surface form."""
    compiled = []
    for entry in entries:
        canonical = entry["canonical"]
        for form in entry["forms"]:
            compiled.append((re.compile(rf"\b{re.escape(form)}\b", re.IGNORECASE), canonical))
    return compiled


def _compile_alias_patterns(entries):
    """
    Longest-surface-form-first, so "section 2 part b" matches before a shorter
    substring of it could (there are none today, but this keeps the ordering
    invariant explicit rather than accidental).
    """
    compiled = []
    for entry in entries:
        target = entry["canonical"]
        for form in entry["forms"]:
            compiled.append((form.lower(), re.compile(rf"\b{re.escape(form)}\b", re.IGNORECASE), target))
    compiled.sort(key=lambda t: len(t[0]), reverse=True)
    return [(pattern, target) for _form, pattern, target in compiled]


def _compile_synonym_patterns(entries):
    compiled = []
    for entry in entries:
        canonical = entry["canonical"]
        for form in entry["forms"]:
            compiled.append((re.compile(rf"\b{re.escape(form)}\b", re.IGNORECASE), canonical))
    return compiled


def load_dictionary(path: str | None = None) -> dict:
    """
    Load and cache the compiled dictionary. Returns an EMPTY (but structurally
    valid) dictionary when the file is absent or fails to parse, so callers
    degrade to "no expansion" rather than crashing — the same tolerance
    src/concept_map.py extends toward a missing concept_map.json.
    """
    path = path or _default_path()
    if path in _cache:
        return _cache[path]

    empty = {"acronyms": [], "aliases": [], "synonyms": []}
    if not os.path.exists(path):
        log.info("no business_dictionary.yaml at %s - expansion disabled", path)
        _cache[path] = empty
        return empty
    try:
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    except Exception as e:
        log.warning("could not read %s (%s) - expansion disabled", path, e)
        _cache[path] = empty
        return empty

    compiled = {
        "acronyms": _compile_acronym_patterns(raw.get("acronyms") or []),
        "aliases": _compile_alias_patterns(raw.get("aliases") or []),
        "synonyms": _compile_synonym_patterns(raw.get("synonyms") or []),
        "_raw": raw,
    }
    _cache[path] = compiled
    return compiled


def clear_cache():
    """Same affordance the FAISS/section-alias caches have — call after a
    yaml edit + restart is inconvenient to test without."""
    _cache.clear()


def expand_acronyms(query: str) -> str:
    """
    Expand banking abbreviations so the embedding model (and BM25) see the full
    phrase instead of a bare acronym. This is the exact behaviour
    src/retriever.py's `_expand_query` had inline — moved here so it is
    defined in exactly one place.
    """
    q = query
    for pattern, replacement in _STRUCTURAL_PATTERNS:
        q = pattern.sub(replacement, q)
    for pattern, canonical in load_dictionary()["acronyms"]:
        q = pattern.sub(canonical, q)
    return q


def detect_pinned_table(query: str) -> str | None:
    """
    The FIRST alias whose surface form appears in `query`, or None. Aliases are
    sorted longest-form-first at load time so a more specific phrase always
    wins over a shorter one it happens to contain.

    Callers MUST treat this as a harder signal than any embedding score — same
    precedence tier as src/section_alias.py's explicit section-number pin —
    and every alias `canonical` value is expected to be a real table name
    (enforced by scripts/validate_business_dictionary.py, not at load time,
    so a stale entry degrades to "no pin" rather than crashing a request).
    """
    for pattern, canonical in load_dictionary()["aliases"]:
        if pattern.search(query):
            return canonical
    return None


def detect_metrics(query: str) -> list[str]:
    """Canonical business terms ('loan_assets', 'restructured_standard_advances',
    ...) whose surface forms appear in the query. Order-preserving, deduplicated.
    Feeds RewrittenQuery.detected_metrics for the Context Resolver — does NOT
    pin a table, unlike detect_pinned_table."""
    seen, out = set(), []
    for pattern, canonical in load_dictionary()["synonyms"]:
        if canonical not in seen and pattern.search(query):
            seen.add(canonical)
            out.append(canonical)
    return out
