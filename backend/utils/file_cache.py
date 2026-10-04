"""backend/utils/file_cache.py — M-15: one small, shared, bounded cache
utility to replace the three independent, inconsistent ad-hoc caches
previously hand-rolled in backend/tools/report_lookup.py (a `_TTLCache`
class with a per-instance mtime check, re-implemented locally),
backend/tools/instance_generator.py (a plain `{path: {"data", "ts"}}` dict
with a TTL but NO mtime check at all -- a genuine missing-invalidation bug),
and backend/tools/taxonomy_index.py (an already-thread-safe, already
content-signature-keyed dict, just unbounded).

Design:
- `FileCache` is a thread-safe, size-bounded (LRU eviction), generic
  key -> value cache. The caller picks the key shape that fits their own
  invalidation semantics -- a bare file path, or (like
  taxonomy_index.py already did) a tuple that itself encodes a freshness
  signature.
- `get_or_load(key, loader, *, path=None, ttl=None)` is the convenience
  entry point report_lookup.py and instance_generator.py use: pass the
  source file's path and this cache transparently re-invokes `loader()`
  (and replaces the stored entry) whenever that file's mtime has changed
  since it was cached, or `ttl` seconds have elapsed, whichever comes
  first. taxonomy_index.py instead uses the plain `get`/`set` pair with its
  own signature-shaped key, since its freshness check is already baked
  into the key itself (unchanged behavior, now just bounded and reusing
  one lock/eviction implementation instead of its own).

Does not introduce a new dependency -- `collections.OrderedDict` is stdlib
and is sufficient for simple LRU (move-to-end on access, pop the oldest on
overflow).
"""
from __future__ import annotations

import os
import threading
import time
from collections import OrderedDict
from typing import Any, Callable, Generic, Hashable, TypeVar

K = TypeVar("K", bound=Hashable)
V = TypeVar("V")

_DEFAULT_MAX_SIZE = 256


class FileCache(Generic[K, V]):
    """Thread-safe, bounded, LRU-evicting cache.

    Safe under concurrent access: every read/write/eviction happens while
    holding one internal lock, so two threads racing to populate the same
    key cannot corrupt the backing dict (the race the original
    report_lookup.py `_TTLCache` dict-of-caches was exposed to: a
    check-then-insert on the outer `_returns_caches`/`_instances_caches`
    dict with no lock at all).
    """

    def __init__(self, max_size: int = _DEFAULT_MAX_SIZE):
        if max_size < 1:
            raise ValueError("max_size must be >= 1")
        self._max_size = max_size
        self._lock = threading.Lock()
        # value -> (payload, mtime_or_None, cached_at_monotonic)
        self._store: "OrderedDict[K, tuple[V, float | None, float]]" = OrderedDict()

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)

    def get(self, key: K) -> V | None:
        """Plain bounded-LRU get -- no mtime/TTL check. Use this when the
        key itself already encodes freshness (e.g. taxonomy_index.py's
        (roots, tree_signature) keys)."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            self._store.move_to_end(key)
            return entry[0]

    def set(self, key: K, value: V) -> V:
        with self._lock:
            self._store[key] = (value, None, time.monotonic())
            self._store.move_to_end(key)
            self._evict_if_needed()
        return value

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def invalidate(self, key: K) -> None:
        """Evict *key* only, if present. For a cache whose freshness also
        depends on another cache/computation (e.g. report_lookup.py's
        `_normalised_returns()`, derived from `_parse_returns()`'s own
        cached result) rather than purely on its own file's mtime."""
        with self._lock:
            self._store.pop(key, None)

    def loaded_at(self, key: K) -> float | None:
        """Monotonic timestamp *key* was last (re)loaded at, or None if not
        cached."""
        with self._lock:
            entry = self._store.get(key)
            return entry[2] if entry is not None else None

    def _evict_if_needed(self) -> None:
        """Caller must hold self._lock."""
        while len(self._store) > self._max_size:
            self._store.popitem(last=False)  # evict least-recently-used

    def get_or_load(
        self,
        key: K,
        loader: Callable[[], V],
        *,
        path: str | None = None,
        ttl: float | None = None,
        should_cache: Callable[[V], bool] | None = None,
    ) -> V:
        """Return the cached value for *key*, reloading via *loader()* when:
          - nothing is cached for *key* yet, or
          - *path* is given and its mtime has changed since the value was
            cached (an OSError reading the mtime, e.g. a deleted file, is
            treated as "not changed" -- the same fail-safe behavior
            report_lookup.py's original `_TTLCache._file_changed()` used),
            or
          - *ttl* is given and that many seconds have elapsed since caching.

        *loader* runs OUTSIDE the lock (parsing a file can be slow; holding
        the lock across it would serialize unrelated keys too), so two
        threads racing on a cold key may both call *loader* once -- the
        same "first one to finish wins" behavior the previous per-site
        caches already had, not a new race this change introduces.

        *should_cache*, if given, is checked against the freshly-loaded
        value before storing it -- returning False means "use this value
        for this call, but don't persist it" (e.g. report_lookup.py's
        original `cache.set(result, cache_empty=False)`: an empty parse
        result, possibly from a transient read, should not evict a
        previous good result from the cache).
        """
        with self._lock:
            entry = self._store.get(key)
        if entry is not None:
            value, cached_mtime, cached_at = entry
            if ttl is not None and (time.monotonic() - cached_at) >= ttl:
                entry = None
            elif path is not None and cached_mtime is not None:
                try:
                    current_mtime = os.path.getmtime(path)
                except OSError:
                    current_mtime = cached_mtime  # fail safe: treat as unchanged
                if current_mtime != cached_mtime:
                    entry = None
            if entry is not None:
                with self._lock:
                    # Re-check presence (another thread may have evicted or
                    # replaced it) before touching LRU order.
                    if key in self._store:
                        self._store.move_to_end(key)
                return entry[0]

        value = loader()
        if should_cache is not None and not should_cache(value):
            return value
        mtime: float | None = None
        if path is not None:
            try:
                mtime = os.path.getmtime(path)
            except OSError:
                mtime = None
        with self._lock:
            self._store[key] = (value, mtime, time.monotonic())
            self._store.move_to_end(key)
            self._evict_if_needed()
        return value
