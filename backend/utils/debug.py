"""Centralized debug logger for the iDEAL db_qa pipeline.

Provides a single ``debug_log()`` function that:
  * prints a nicely-formatted block to stdout  (always visible in uvicorn terminal)
  * emits the same block via Python logging at DEBUG level
    (captured by uvicorn / gunicorn log handlers)

Usage::

    from backend.utils.debug import debug_log

    debug_log(
        "DB QA ROUTER",
        question="What is my department?",
        detected_intent="db_my_department",
        handler="handle_my_department",
    )

Expected console output::

    ============================================================
      DB QA ROUTER
      question              : What is my department?
      detected_intent       : db_my_department
      handler               : handle_my_department
    ============================================================
"""
from __future__ import annotations

import logging

_dbg = logging.getLogger("dbqa.debug")
_SEP = "=" * 60


def debug_log(title: str, **kwargs) -> None:
    """Print a structured, human-readable debug block to the console.

    Parameters
    ----------
    title:
        Short section header, e.g. ``"/chat API HIT"`` or ``"INTENT CLASSIFIER"``.
    **kwargs:
        Key-value pairs printed as ``  key : value`` lines.
        Values longer than 300 characters are automatically truncated.
    """
    lines: list[str] = [f"\n{_SEP}", f"  {title}"]
    for key, value in kwargs.items():
        v = str(value)
        if len(v) > 300:
            v = v[:297] + "..."
        lines.append(f"  {key:<22}: {v}")
    lines.append(f"{_SEP}\n")
    block = "\n".join(lines)
    # print() ensures output appears immediately in the uvicorn/cmd terminal
    print(block, flush=True)
    # also emit via logging so it can be captured by file handlers at DEBUG level
    _dbg.debug("%s", block)
