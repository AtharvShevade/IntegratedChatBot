"""M-16: a tiny, generic memoization cache for "parse this file" functions,
keyed by ``(path, mtime)``.

The same error-explanation document was being re-read and re-parsed from
disk on every batch of "Explain next" clicks (`report_lookup.py`'s
``parse_backtrack_html_errors`` and `formula_error.py`'s
``parse_formula_errors_v2`` are each called multiple times per on-demand
explanation, and again on every subsequent batch for the same file).

Keyed per-path (not an unbounded, ever-growing list): each path stores only
its most recent ``(mtime, result)`` pair, so a file that changes on disk
invalidates its own entry automatically and the cache can never grow past
one entry per distinct file ever parsed in this process — never stale
indefinitely, never unbounded across unrelated files beyond that.
"""
from __future__ import annotations

import os
import threading
from typing import Callable, TypeVar

T = TypeVar("T")

_lock = threading.Lock()
_cache: dict[str, tuple[float, object]] = {}


def cached_by_mtime(path: str, parse: Callable[[], T]) -> T:
    """Return ``parse()``'s result, reusing a cached value for *path* when
    the file's mtime hasn't changed since it was last parsed.

    *parse* is only called on a genuine cache miss (first time this path is
    seen, or the file's mtime has changed) -- never on every call.
    """
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        # File missing/unreadable -- do not cache a failure, let the normal
        # (uncached) code path handle it exactly as it would without this
        # cache existing at all.
        return parse()

    with _lock:
        cached = _cache.get(path)
        if cached is not None and cached[0] == mtime:
            return cached[1]  # type: ignore[return-value]

    result = parse()

    with _lock:
        _cache[path] = (mtime, result)

    return result
