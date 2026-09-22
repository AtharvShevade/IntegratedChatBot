"""backend/agent/state.py — shared, dependency-free state for the agent package.

Holds the in-memory session/job stores, the multi-turn "awaiting" stage
constants, the routing regexes shared by more than one submodule, and the
generic ChatResponse-shaped dict builder (_build). Every other module under
backend/agent/ imports what it needs from here rather than each other,
keeping the dependency direction simple: state.py has no imports on any
sibling module.

Moved out of backend/agent/__init__.py verbatim — no logic changes.
"""

from __future__ import annotations

import re
from typing import Any

# ── In-memory async error-enrichment job store ────────────────────────────────
# Structure: { job_id: {"status": "pending"|"done", "payload": dict|None} }
# For multi-worker deployments replace with Redis.
_error_jobs: dict[str, dict] = {}

# Stage constants -- stored in session under key "awaiting"
STAGE_DATE         = "AWAITING_DATE_SELECTION"    # status: picking a date
STAGE_REPORT       = "AWAITING_REPORT_SELECTION"  # status: picking from disambiguation
STAGE_GEN_REPORT   = "AWAITING_GEN_REPORT"        # generate: picking from disambiguation
STAGE_GEN_DATE     = "AWAITING_GEN_DATE"          # generate: providing reporting date
STAGE_RUN          = "AWAITING_RUN_SELECTION"      # status: picking a run by timestamp
STAGE_SCHED_REPORT = "AWAITING_SCHED_REPORT"      # schedule: picking from disambiguation
STAGE_SCHED_RPT_DATE = "AWAITING_SCHED_REPORTING_DATE"  # schedule: providing reporting (period) date
STAGE_SCHED_DT      = "AWAITING_SCHED_DATETIME"    # schedule: providing date and time
STAGE_SCHED_CONFIRM = "AWAITING_SCHED_CONFIRM"      # schedule: awaiting user confirmation
STAGE_SCHED_NAME    = "AWAITING_SCHED_NAME"          # schedule: re-entering report name after Change Data
STAGE_CMP_REPORT    = "AWAITING_CMP_REPORT"         # compare: picking report from disambiguation
STAGE_CMP_FILE     = "AWAITING_CMP_FILE"            # compare: confirming which 2 instances
STAGE_PREV_DATES   = "AWAITING_PREV_DATES_CONFIRM"  # status: yes/no for previous dates
STAGE_RETURN_QA = "AWAITING_RETURN_QA_SELECTION"  # db_qa: picking a return from disambiguation (any return-scoped intent)

# In-memory session store per session_id
_session_context: dict[str, dict[str, Any]] = {}

# Phrases that explicitly signal the user wants to start a new report query
_NEW_REPORT_KWS = frozenset({
    "new report", "different report", "another report",
    "reset", "start over", "new query", "change report",
})

_STATUS_KW_RE   = re.compile(r'\b(status|state|progress|check|details|info)\b', re.I)
_STATUS_OF_RE   = re.compile(
    r'\b(status|state|check|details|info)\s+(of|for|about)\s+\S+', re.I
)
_GEN_KW_RE      = re.compile(
    r'\b(generate|create\s+instance|trigger\s+instance|run\s+report|produce\s+instance|new\s+instance)\b',
    re.I,
)
_SCHED_KW_RE    = re.compile(r'\b(schedule|scheduled|scheduling)\b', re.I)

# DB query keyword detector — catches data-fetch queries regardless of LLM classification.
# Deliberately not meant to be an exhaustive metric list (that's a losing battle — new
# regulatory/banking terms show up constantly); it's a fast, deterministic short-circuit
# for the common cases, with extract_intent_entities_llm's generic (non-enumerated)
# "any financial/regulatory data point" rule as the real fallback for anything this misses.
_DB_QUERY_KW_RE = re.compile(
    r'\b(fetch|retrieve|show|list|display|get|select|query|how\s+many|what\s+is\s+the|'
    r'total|sum|count|average|npa|gnpa|nnpa|sma|car|slr|crr|psl|rwa|pcr|'
    r'exposure|provision|capital|loan|deposit|asset|liability|'
    r'derivative|notional|principal|advance|advances|investment|investments|yield|'
    r'gross|net|outstanding|balance|amount|value|data|records?|figures?|'
    r'from\s+(the\s+)?(database|db|oracle|table))\b',
    re.I,
)

# Compare keyword detector — signals compare/variance/comparative-analysis workflow intent.
# Catches: compare, comparative, comparative analysis, comparison, comparing, variance, etc.
# Prevents compare queries from leaking into the SQL or QA fast-paths.
_CMP_KW_RE = re.compile(
    r'\b(compar\w*|versus|vs\.?|varianc\w*|contrast|differences?\s+between|side.?by.?side)\b',
    re.I,
)

# Detect ASP.NET / browser session GUIDs forwarded as user_id by the .NET iframe.
# These are 32-char hex strings (UUID without dashes) or standard UUID format.
# When matched the value is NOT a real user identifier — fall back to login_id.
_SESSION_GUID_RE = re.compile(
    r'^[0-9a-fA-F]{32}$'                                                     # 32-hex no dashes
    r'|^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'  # UUID
)


def _build(
    intent: str,
    report_name: str | None,
    response_text: str = "",
    need_clarification: bool = False,
    result_type: str = "",
    options: list[str] | None = None,
    scheduled_datetime: str | None = None,
    schedule_date: str | None = None,
    schedule_time: str | None = None,
    reporting_date_out: str | None = None,
    variance_data:    list[dict] | None = None,
    variance_all:     list[dict] | None = None,
    variance_meta:    dict | None = None,
    variance_label_a: str | None = None,
    variance_label_b: str | None = None,
    llm_summary:      str | None = None,
    instances_data:   list[dict] | None = None,
    download_url:     str = "",
    download_label:   str = "",
    status_note:      str = "",
    error_details:    list[dict] | None = None,
    job_id:           str | None = None,
    data:             dict[str, Any] | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "intent":             intent,
        "report_name":        report_name,
        "response_text":      response_text,
        "need_clarification": need_clarification,
        "result_type":        result_type,
        "options":            options or [],
        "download_url":       download_url,
        "download_label":     download_label,
        "status_note":        status_note,
    }
    if scheduled_datetime is not None:
        out["scheduled_datetime"] = scheduled_datetime
    if schedule_date is not None:
        out["schedule_date"] = schedule_date
    if schedule_time is not None:
        out["schedule_time"] = schedule_time
    if reporting_date_out is not None:
        out["reporting_date"] = reporting_date_out
    if variance_data is not None:
        out["variance_data"]    = variance_data
        out["variance_label_a"] = variance_label_a or ""
        out["variance_label_b"] = variance_label_b or ""
        out["llm_summary"]      = llm_summary or ""
        # Every inline comparison now ships Python's deterministic draft, so
        # the frontend needs an explicit signal that the model has not run yet.
        out["llm_summary_is_draft"] = bool(llm_summary)
    # Set independently of variance_data: the chart's dataset (ALL comparable
    # rows) and the coverage counts must never be gated on the table's slice.
    if variance_all is not None:
        out["variance_all"] = variance_all
    if variance_meta is not None:
        out["variance_meta"] = variance_meta
    # Set independently too: an empty list is a meaningful answer ("taxonomy
    # read, nothing to group") and must not be conflated with the key's absence.
    if instances_data is not None:
        out["instances_data"] = instances_data
    if error_details:
        out["error_details"] = error_details
    if job_id is not None:
        out["job_id"] = job_id
    if data:
        out["data"] = data
    return out


__all__ = [
    "_error_jobs", "_session_context",
    "STAGE_DATE", "STAGE_REPORT", "STAGE_GEN_REPORT", "STAGE_GEN_DATE", "STAGE_RUN",
    "STAGE_SCHED_REPORT", "STAGE_SCHED_RPT_DATE", "STAGE_SCHED_DT", "STAGE_SCHED_CONFIRM",
    "STAGE_SCHED_NAME", "STAGE_CMP_REPORT", "STAGE_CMP_FILE", "STAGE_PREV_DATES", "STAGE_RETURN_QA",
    "_NEW_REPORT_KWS", "_STATUS_KW_RE", "_STATUS_OF_RE", "_GEN_KW_RE", "_SCHED_KW_RE",
    "_DB_QUERY_KW_RE", "_CMP_KW_RE", "_SESSION_GUID_RE",
    "_build",
]
