"""M-25: a small in-process sliding-window rate limiter.

Disabled by default (``RATE_LIMIT_ENABLED`` unset/false) so existing
behavior, local development, and the rest of the test suite are completely
unaffected unless a deployment explicitly opts in. No new persistence system
is introduced -- bucket state lives in a plain dict in process memory,
consistent with this codebase's existing in-process session-state pattern
(``agent/state.py``'s ``_session_context``). Like that state, this is
single-process only: running more than one worker would give each worker its
own independent counters (a pre-existing, documented constraint of this
codebase, not something this module changes).
"""
from __future__ import annotations

import os
import threading
import time


def is_enabled() -> bool:
    return os.getenv("RATE_LIMIT_ENABLED", "false").strip().lower() in ("1", "true", "yes", "on")


def max_requests() -> int:
    try:
        return max(1, int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "30")))
    except ValueError:
        return 30


def window_seconds() -> float:
    try:
        return max(1.0, float(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60")))
    except ValueError:
        return 60.0


class SlidingWindowRateLimiter:
    """Per-key sliding-window request counter."""

    def __init__(self) -> None:
        self._hits: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str, *, limit: int, window: float) -> tuple[bool, float]:
        """Record one hit for *key* and return ``(allowed, retry_after_seconds)``.

        A rejected request is NOT counted again on its next retry beyond what
        the window naturally expires -- only accepted hits are recorded, so a
        client that backs off recovers exactly when the oldest accepted hit
        ages out of the window.
        """
        now = time.monotonic()
        with self._lock:
            hits = self._hits.setdefault(key, [])
            cutoff = now - window
            while hits and hits[0] < cutoff:
                hits.pop(0)
            if len(hits) >= limit:
                retry_after = window - (now - hits[0])
                return False, max(retry_after, 0.0)
            hits.append(now)
            return True, 0.0

    def reset(self) -> None:
        """Test-only: clear all tracked state between test cases."""
        with self._lock:
            self._hits.clear()


# One process-wide limiter instance, mirroring the existing module-level
# singletons elsewhere in this codebase (e.g. agent/state.py's dicts).
limiter = SlidingWindowRateLimiter()
