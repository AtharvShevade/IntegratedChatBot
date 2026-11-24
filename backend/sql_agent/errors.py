# backend/sql_agent/errors.py
#
# Classifies the SQL agent's infrastructure failures (LLM / Oracle timeouts,
# unreachable services) and maps each to ONE short, user-facing message.
#
# Only used to refine messages for those specific failures. Every other failure
# keeps the generic wording the pipeline already used, so nothing that depends on
# the old text changes. Raw exception text never reaches the client: callers log
# it and show only the message returned here.

from __future__ import annotations

import os

# Failure kinds
LLM_TIMEOUT = "llm_timeout"
LLM_UNAVAILABLE = "llm_unavailable"
DB_TIMEOUT = "db_timeout"
DB_UNAVAILABLE = "db_unavailable"
PIPELINE_TIMEOUT = "pipeline_timeout"
INTERNAL = "internal"
OTHER = "other"          # not an infrastructure failure -> caller keeps its own message

MESSAGES: dict[str, str] = {
    LLM_TIMEOUT: "The AI service took too long to respond. Please try again, or ask a more specific question.",
    LLM_UNAVAILABLE: "The AI service is temporarily unavailable. Please try again in a moment.",
    DB_TIMEOUT: "The database took too long to respond. Try narrowing your question (a specific return, section or date).",
    DB_UNAVAILABLE: "The database is temporarily unavailable. Please try again shortly.",
    PIPELINE_TIMEOUT: "This request took too long and was stopped. Please try again, or ask a more specific question.",
    INTERNAL: "Something went wrong while processing your query. Please try again.",
}

# Whole-request wall-clock limit (seconds). Matches the LLM read timeout, so a
# request that could legitimately finish before still does.
try:
    PIPELINE_TIMEOUT_SEC = max(30, int(os.environ.get("SQL_AGENT_TIMEOUT_SEC", "300")))
except ValueError:
    PIPELINE_TIMEOUT_SEC = 300


def classify(error) -> str:
    """Kind of failure for an exception or an error string (case-insensitive).
    Returns OTHER when it is not a recognised timeout / unavailable condition."""
    if isinstance(error, TimeoutError):
        return PIPELINE_TIMEOUT
    t = str(error or "").lower()
    if not t:
        return OTHER

    # Oracle (executor.py prefixes its errors with "Connection failed:" /
    # "Query execution failed:"; raw codes are python-oracledb DPY / ORA).
    if any(k in t for k in ("dpy-4024", "dpi-1067", "ora-01013", "ora-03156", "call timeout")):
        return DB_TIMEOUT
    if t.startswith("connection failed:") or any(
        k in t for k in ("ora-12170", "ora-12541", "ora-12514", "ora-12537", "ora-03113", "ora-03114",
                         "dpy-6005", "dpy-4011", "dpi-1080", "ora-12154", "ora-12543")
    ):
        return DB_UNAVAILABLE

    # Ollama (sql_generator.py raises RuntimeError with these phrases).
    if "ollama timed out" in t or "read timed out" in t or "readtimeout" in t:
        return LLM_TIMEOUT
    if any(k in t for k in ("cannot connect to ollama", "ollama proxy", "circuit breaker", "was unreachable",
                            "ollama unreachable", "ollama api error", "connection refused")):
        return LLM_UNAVAILABLE

    if "timed out" in t or "timeout" in t:
        return PIPELINE_TIMEOUT
    return OTHER


def message_for(kind: str) -> str | None:
    return MESSAGES.get(kind)
