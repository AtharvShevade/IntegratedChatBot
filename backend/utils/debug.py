"""Centralized debug logger for the iDEAL db_qa pipeline.

Provides a single ``debug_log()`` function that emits a structured,
human-readable block via Python logging at DEBUG level. Respects the
configured log level/handlers instead of writing to stdout unconditionally,
so it stays silent in production (console level INFO) and is available on
demand by lowering the console/file level to DEBUG.

Usage::

    from backend.utils.debug import debug_log

    debug_log(
        "DB QA ROUTER",
        question="What is my department?",
        detected_intent="db_my_department",
        handler="handle_my_department",
    )
"""
from __future__ import annotations

import logging

_dbg = logging.getLogger("dbqa.debug")
_SEP = "=" * 60


def debug_log(title: str, **kwargs) -> None:
    """Log a structured, human-readable debug block at DEBUG level.

    Parameters
    ----------
    title:
        Short section header, e.g. ``"/chat API HIT"`` or ``"INTENT CLASSIFIER"``.
    **kwargs:
        Key-value pairs printed as ``  key : value`` lines.
        Values longer than 300 characters are automatically truncated.
    """
    if not _dbg.isEnabledFor(logging.DEBUG):
        return
    lines: list[str] = [f"\n{_SEP}", f"  {title}"]
    for key, value in kwargs.items():
        v = str(value)
        if len(v) > 300:
            v = v[:297] + "..."
        lines.append(f"  {key:<22}: {v}")
    lines.append(f"{_SEP}\n")
    _dbg.debug("\n".join(lines))
