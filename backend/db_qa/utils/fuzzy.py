"""Fuzzy matching utilities — difflib only, no ML, no third-party deps.

Public API::

    confidence(a, b)                         → int 0-100
    partial_confidence(a, b)                 → int 0-100  (substring-aware)
    best_match(query, candidates, threshold) → str | None
    ranked_matches(query, candidates, ...)   → list[(str, int)]

All functions are case-insensitive.
"""
from __future__ import annotations

import difflib


def confidence(a: str, b: str) -> int:
    """SequenceMatcher similarity ratio as 0-100 integer.

    100 = identical strings, 0 = nothing in common.
    """
    if not a or not b:
        return 0
    return int(difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio() * 100)


def partial_confidence(needle: str, haystack: str) -> int:
    """Score whether *needle* appears (approximately) in *haystack*.

    Returns 100 for exact substring, otherwise the best ratio of
    *needle* against any same-length window of *haystack*.
    Useful for short partial names: 'abhay' → 'Abhay Pandey'.
    """
    if not needle or not haystack:
        return 0
    n_l = needle.lower()
    h_l = haystack.lower()

    if n_l in h_l:
        return 100

    n = len(n_l)
    if n > len(h_l):
        return confidence(n_l, h_l)

    best = 0
    for i in range(len(h_l) - n + 1):
        sub = h_l[i: i + n]
        score = int(difflib.SequenceMatcher(None, n_l, sub).ratio() * 100)
        if score > best:
            best = score
    return best


def best_match(
    query: str,
    candidates: list[str],
    threshold: int = 70,
    *,
    use_partial: bool = True,
) -> str | None:
    """Return the best-matching candidate or None if no candidate reaches *threshold*.

    Args:
        query:       Input string.
        candidates:  Reference strings to compare against.
        threshold:   Minimum score (0-100) required to return a match.
        use_partial: Also run partial_confidence for substring-aware scoring.
    """
    if not query or not candidates:
        return None

    best_score = 0
    best_val: str | None = None
    q = query.lower()

    for c in candidates:
        score = confidence(q, c)
        if use_partial:
            score = max(score, partial_confidence(q, c))
        if score > best_score:
            best_score = score
            best_val = c

    return best_val if best_score >= threshold else None


def ranked_matches(
    query: str,
    candidates: list[str],
    threshold: int = 50,
    *,
    use_partial: bool = True,
    limit: int = 5,
) -> list[tuple[str, int]]:
    """Return up to *limit* (candidate, score) pairs above *threshold*, sorted descending.

    Useful for building "Did you mean…?" suggestion lists.
    """
    if not query or not candidates:
        return []

    results: list[tuple[str, int]] = []
    q = query.lower()

    for c in candidates:
        score = confidence(q, c)
        if use_partial:
            score = max(score, partial_confidence(q, c))
        if score >= threshold:
            results.append((c, score))

    results.sort(key=lambda x: x[1], reverse=True)
    return results[:limit]
