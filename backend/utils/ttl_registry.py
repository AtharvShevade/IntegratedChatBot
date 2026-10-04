"""M-01: a small, generic bounded + TTL-expiring in-memory registry for
module-level session/job state.

backend/utils/file_cache.py already solves this for FILE-BACKED caches
(mtime-aware, path keyed). The gap this closes is different: plain in-memory
dicts keyed by session_id/job_id (backend/agent/state.py's _session_context
and _error_jobs, backend/guided.py's _guided_sessions) that are only ever
added to -- cleanup is a handful of ad-hoc `.pop()` calls on specific
success-path branches, so a session abandoned before reaching one of those
branches (closed tab, crashed browser) leaks forever, and _error_jobs has no
cleanup at all.

TTLDict is a dict subclass so every existing call site (`d[k] = v`,
`d.get(k)`, `d.pop(k, None)`, `k in d`) keeps working completely unchanged --
only the three module-level declarations (`{}` -> `TTLDict(...)`) need to
change. Eviction is swept opportunistically on write (no background thread
or scheduler needed): cheap for the write rates these registries see
(one entry per chat session/background job).

Thread-safe because _error_jobs is written from both the request-handling
thread and background_jobs.py's ThreadPoolExecutor workers (see M-02) --
the one genuine concurrent-write case among these three registries (L-12).
"""
from __future__ import annotations

import threading
import time
from typing import Any


class TTLDict(dict):
    """A dict that bounds itself by max_size (LRU eviction) and expires
    entries older than ttl_seconds, swept on every write.

    Not a general-purpose cache (no get_or_load/mtime awareness -- see
    FileCache for that) -- this is deliberately just "a dict that cleans up
    after itself" for session/job registries where the caller fully owns the
    value's lifecycle otherwise.
    """

    def __init__(self, *, max_size: int = 10_000, ttl_seconds: float = 24 * 3600):
        super().__init__()
        if max_size < 1:
            raise ValueError("max_size must be >= 1")
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be > 0")
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._touched: dict[Any, float] = {}
        self._lock = threading.Lock()

    def __setitem__(self, key, value) -> None:
        with self._lock:
            super().__setitem__(key, value)
            self._touched[key] = time.monotonic()
            self._evict_locked()

    def __delitem__(self, key) -> None:
        with self._lock:
            super().__delitem__(key)
            self._touched.pop(key, None)

    def pop(self, key, *default):
        with self._lock:
            self._touched.pop(key, None)
            return super().pop(key, *default)

    def _evict_locked(self) -> None:
        """Caller must hold self._lock. Expire stale entries first, then —
        if still over max_size — drop the oldest-touched entries until
        within bound. Runs on every write, so each call only ever has at
        most one new entry to account for; still O(n) worst case, which is
        fine at the sizes these registries see (sessions/jobs, not a hot
        per-request cache)."""
        now = time.monotonic()
        expired = [k for k, ts in self._touched.items() if now - ts > self._ttl_seconds]
        for k in expired:
            dict.__delitem__(self, k)
            self._touched.pop(k, None)

        overflow = len(self) - self._max_size
        if overflow > 0:
            oldest = sorted(self._touched.items(), key=lambda kv: kv[1])[:overflow]
            for k, _ts in oldest:
                dict.__delitem__(self, k)
                self._touched.pop(k, None)
