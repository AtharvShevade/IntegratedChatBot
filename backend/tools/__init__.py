"""
backend/tools/__init__.py â€” Tool registry for the agent.

Design principles:
  - Tools ONLY fetch / filter raw data. Zero business logic.
  - Every tool is a plain async function with a clear docstring.
  - To add a new tool, define an async function and register it in TOOL_REGISTRY.

Current tools:
  get_error_logs()          â€” reads logs/report_logs.txt, returns [ERR] blocks
  get_logs_by_report(id)    â€” filters log lines for a specific report_id

Future tools (stubs â€” uncomment when ready):
  get_report_status(id)     â€” queries Oracle DB
  get_report_errors(id)     â€” queries Oracle DB
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Callable

logger = logging.getLogger(__name__)

# â”€â”€ Configuration â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# __file__ is backend/tools/__init__.py â€” three dirname calls reach project root
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_FILE_PATH = os.path.join(_PROJECT_ROOT, "logs", "report_logs.txt")

DEFAULT_ERROR_BLOCK_COUNT = int(os.getenv("MAX_ERROR_BLOCKS", "10"))

# Regex patterns shared by both tools
_TOP_LEVEL = re.compile(r"\[(INF|WRN|ERR|DBG|VRB|FTL)\]")
_ERR_MARKER = re.compile(r"\[ERR\]")


# â”€â”€ Tool: get_error_logs â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async def get_error_logs(n: int = DEFAULT_ERROR_BLOCK_COUNT) -> str:
    """
    Read logs/report_logs.txt and return the last N [ERR] blocks as plain text.

    Supports both log formats:
      "[ERR] 2026-04-28 ..."          (tag at start)
      "2026-03-27 12:37 [ERR] ..."    (tag after timestamp)

    Returns an error message string (never raises) so the agent can pass it to the LLM.
    """
    if not os.path.exists(LOG_FILE_PATH):
        logger.warning("Log file not found at %s", LOG_FILE_PATH)
        return f"[TOOL] Log file not found at {LOG_FILE_PATH}"

    try:
        with open(LOG_FILE_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except OSError as exc:
        logger.error("Could not read log file: %s", exc)
        return f"[TOOL] Could not read log file: {exc}"

    error_blocks: list[str] = []
    current_block: list[str] = []
    in_error_block = False

    for line in lines:
        is_top_level = bool(_TOP_LEVEL.search(line))

        if is_top_level:
            if in_error_block and current_block:
                error_blocks.append("".join(current_block).rstrip())
            current_block = [line]
            in_error_block = bool(_ERR_MARKER.search(line))
        else:
            if current_block:
                current_block.append(line)

    if in_error_block and current_block:
        error_blocks.append("".join(current_block).rstrip())

    if not error_blocks:
        return "[TOOL] No [ERR] entries found in the log file."

    recent = error_blocks[-n:]
    logger.info("get_error_logs: returning %d of %d total error blocks", len(recent), len(error_blocks))
    return "\n\n".join(recent)


# â”€â”€ Tool: get_logs_by_report â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async def get_logs_by_report(report_id: int, n: int = DEFAULT_ERROR_BLOCK_COUNT) -> str:
    """
    Return all [ERR] log blocks that mention a specific report_id.

    Args:
        report_id: The numeric report identifier to filter on.
        n:         Maximum number of error blocks to return.
    """
    if not os.path.exists(LOG_FILE_PATH):
        return f"[TOOL] Log file not found at {LOG_FILE_PATH}"

    try:
        with open(LOG_FILE_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except OSError as exc:
        return f"[TOOL] Could not read log file: {exc}"

    id_pattern = re.compile(rf"report_id\s*=\s*{report_id}\b", re.IGNORECASE)

    error_blocks: list[str] = []
    current_block: list[str] = []
    in_error_block = False
    block_matches = False

    for line in lines:
        is_top_level = bool(_TOP_LEVEL.search(line))

        if is_top_level:
            if in_error_block and block_matches and current_block:
                error_blocks.append("".join(current_block).rstrip())
            current_block = [line]
            in_error_block = bool(_ERR_MARKER.search(line))
            block_matches = in_error_block and bool(id_pattern.search(line))
        else:
            if current_block:
                current_block.append(line)
                if in_error_block and id_pattern.search(line):
                    block_matches = True

    if in_error_block and block_matches and current_block:
        error_blocks.append("".join(current_block).rstrip())

    if not error_blocks:
        return f"[TOOL] No [ERR] entries found for report_id={report_id}."

    recent = error_blocks[-n:]
    return "\n\n".join(recent)


# â”€â”€ Tool Registry â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Maps tool name â†’ async callable.
# Agent looks up tools here â€” add new tools without changing agent code.

TOOL_REGISTRY: dict[str, Callable[..., Any]] = {
    "get_error_logs":     get_error_logs,
    "get_logs_by_report": get_logs_by_report,
    # Future DB tools:
    # "get_report_status":  get_report_status,
    # "get_report_errors":  get_report_errors,
}
