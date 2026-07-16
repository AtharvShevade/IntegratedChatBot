# backend/sql_agent/__init__.py
# Entry point for the SQL agent integration with the chatbot.
# Exposes handle_db_query() which is called by both:
#   - backend/guided.py  STAGE_DB_QUERY handler
#   - backend/agent/__init__.py  query_database intent handler

from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)

# ── Minimum word-count guard ───────────────────────────────────────────────────
MIN_QUERY_WORDS = 5   # queries with fewer words are too vague for accurate SQL
MAX_SQL_RETRIES = 1   # max generate→validate→execute attempts per user query

# ── Time-context patterns for the accuracy hint ───────────────────────────────
_TIME_PATTERNS = [
    r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b",
    r"\b(january|february|march|april|june|july|august|september|october|november|december)\b",
    r"\b(q[1-4]|quarter)\b",
    r"\b(20\d{2}|19\d{2})\b",
    r"\b(fy|financial year|fiscal year)\b",
    r"\b(last|this|current|previous)\s+(month|year|quarter|week)\b",
    r"\b(ytd|mtd|year[\s-]to[\s-]date|month[\s-]to[\s-]date)\b",
    r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
    r"\b(period|as of|ending|ended|as at)\b",
    r"\b(h[12]|half year|half-year)\b",
]


def _has_time_context(query: str) -> bool:
    q = query.lower()
    return any(re.search(p, q) for p in _TIME_PATTERNS)


def _build_result(
    response_text: str,
    result_type:   str,
    *,
    db_columns:     list[str]        = None,
    db_rows:        list[list]       = None,
    db_sql:         str              = "",
    db_error:       str | None       = None,
    accuracy_hint:  str | None       = None,
    needs_more_info: bool            = False,
    more_info_hint: str | None       = None,
) -> dict[str, Any]:
    return {
        "intent":             "query_database",
        "report_name":        None,
        "response_text":      response_text,
        "need_clarification": False,
        "result_type":        result_type,
        "options":            [],
        "variance_data":      [],
        "variance_label_a":   "",
        "variance_label_b":   "",
        "llm_summary":        "",
        "instances_data":     [],
        # ── DB-specific fields ──────────────────────────────────────────────
        "db_columns":         db_columns or [],
        "db_rows":            db_rows    or [],
        "db_sql":             db_sql,
        "db_error":           db_error,
        "accuracy_hint":      accuracy_hint,
        "needs_more_info":    needs_more_info,
        "more_info_hint":     more_info_hint,
    }


async def handle_db_query(message: str, session_id: str | None = None) -> dict[str, Any]:
    """
    Full NL → SQL → Execute pipeline.

    Steps:
      1. Length guard — ask for more detail if query is too short
      2. Retrieve relevant schema via FAISS (retriever)
      3. Generate SQL via LLM (sql_generator)
      4. Validate SQL (SELECT-only + hallucination check)
      5. Execute on Oracle DB (executor)
      6. Return result dict matching ChatResponse shape

    Returns a dict that can be passed directly to ChatResponse(**result).
    """
    q = message.strip()

    # ── Guard 1: minimum word count ────────────────────────────────────────────
    word_count = len(q.split())
    if word_count < MIN_QUERY_WORDS:
        return _build_result(
            response_text=(
                f"Your query is too short ({word_count} word{'s' if word_count != 1 else ''}). "
                "Please describe what you need in more detail."
            ),
            result_type="db_result",
            needs_more_info=True,
            more_info_hint=(
                f"Please use at least {MIN_QUERY_WORDS} words. For example:\n"
                "\u2022 'Show gross NPA for Q1 FY2024'\n"
                "\u2022 'Total loan assets from RAQ section 1 latest'\n"
                "\u2022 'Fetch derivative notional principal from ALE domestic March 2025'"
            ),
        )

    # ── Soft hint when no time context detected ───────────────────────────────
    accuracy_hint = None
    if not _has_time_context(q):
        accuracy_hint = (
            "Tip: For more accurate results, try specifying a time period — "
            "e.g. a specific date (01-Mar-2025), month (March 2025), "
            "quarter (Q1 FY2024), or year (2024)."
        )

    # ── Step 1: schema retrieval ──────────────────────────────────────────────
    # Run on a worker thread (not directly on the event loop) so this
    # coroutine has a real `await` suspension point — that's what lets
    # /stop's task.cancel() interrupt this request immediately instead of
    # only taking effect after the whole (possibly 300s+) pipeline finishes,
    # and it keeps this session's blocking work from stalling every other
    # session sharing the single event loop in the meantime.
    try:
        from backend.sql_agent.retriever import get_relevant_schema
        tables, columns, matched_labels = await asyncio.to_thread(get_relevant_schema, q)
        logger.info("[SQL_AGENT] tables=%s", [t["table"] for t in tables])
    except Exception as exc:
        logger.error("[SQL_AGENT] Schema retrieval failed: %s", exc)
        return _build_result(
            response_text="Unable to process your database query right now. Please try again later.",
            result_type="db_result",
            db_error=None,
        )

    if not tables:
        return _build_result(
            response_text="No matching tables found for your query. Try rephrasing with different keywords.",
            result_type="db_result",
            accuracy_hint=accuracy_hint,
        )

    # ── Steps 2-4: generate → validate → execute (retry loop) ─────────────────
    from backend.sql_agent.sql_generator import generate_sql, validate_sql
    from backend.sql_agent.executor import execute_query
    from backend.sql_agent.utils import serialize_rows

    previous_sql   = None
    previous_error = None

    for attempt in range(MAX_SQL_RETRIES):
        # Step 2: SQL generation (worker thread — see note above on Step 1)
        try:
            result = await asyncio.to_thread(
                generate_sql,
                q, tables, columns, matched_labels=matched_labels,
                previous_sql=previous_sql, previous_error=previous_error,
            )
            sql = result.get("sql", "")
            logger.info("[SQL_AGENT] attempt=%d sql=\n%s", attempt + 1, sql)
        except RuntimeError as exc:
            logger.error("[SQL_AGENT] SQL generation failed: %s", exc)
            return _build_result(
                response_text="SQL generation failed. Please try again.",
                result_type="db_result",
                db_error=None,
                accuracy_hint=accuracy_hint,
            )
        except Exception as exc:
            logger.error("[SQL_AGENT] Unexpected error in generate_sql: %s", exc)
            return _build_result(
                response_text="An unexpected error occurred while generating SQL. Please try again.",
                result_type="db_result",
                db_error=None,
            )

        # Step 3: validation
        is_valid, reason = validate_sql(sql, tables, columns)
        logger.debug("[SQL_AGENT] attempt=%d valid=%s reason=%s", attempt + 1, is_valid, reason)
        if not is_valid:
            if attempt + 1 < MAX_SQL_RETRIES:
                previous_sql   = sql
                previous_error = f"Validation error: {reason}"
                logger.info("[SQL_AGENT] retrying after validation failure: %s", reason)
                continue
            return _build_result(
                response_text="Unable to process your query right now. Please try again.",
                result_type="db_result",
                db_sql=sql,
                db_error=reason,
                accuracy_hint=accuracy_hint,
            )

        # Step 4: execution (worker thread — see note above on Step 1)
        try:
            col_names, rows, db_error = await asyncio.to_thread(execute_query, sql)
            serialized_rows = serialize_rows(rows)
            logger.info("[SQL_AGENT] attempt=%d rows=%d db_error=%s", attempt + 1, len(rows), db_error)
        except Exception as exc:
            logger.error("[SQL_AGENT] Execution error: %s", exc)
            return _build_result(
                response_text="Unable to retrieve the requested information. Please try again.",
                result_type="db_result",
                db_sql=sql,
                db_error=None,
                accuracy_hint=accuracy_hint,
            )

        if db_error:
            if attempt + 1 < MAX_SQL_RETRIES:
                previous_sql   = sql
                previous_error = db_error
                logger.info("[SQL_AGENT] retrying after DB error: %s", db_error)
                continue
            return _build_result(
                response_text="Unable to retrieve the requested information. Please try again.",
                result_type="db_result",
                db_sql=sql,
                db_error=None,
                accuracy_hint=accuracy_hint,
            )

        # Success
        row_count = len(serialized_rows)

        if row_count == 0:
            return _build_result(
                response_text="No data found for your query.",
                result_type="db_result",
                db_columns=col_names,
                db_rows=[],
                db_sql=sql,
                needs_more_info=True,
                more_info_hint=(
                    "The query ran successfully but returned no rows. Try:\n"
                    "\u2022 Adding a time period \u2014 e.g. 'Q1 FY2024', 'March 2025', 'latest'\n"
                    "\u2022 Being more specific \u2014 e.g. include the report section name\n"
                    "\u2022 Checking the spelling of report/section names"
                ),
                accuracy_hint=accuracy_hint,
            )

        return _build_result(
            response_text=f"Found {row_count} row{'s' if row_count != 1 else ''}.",
            result_type="db_result",
            db_columns=col_names,
            db_rows=serialized_rows,
            db_sql=sql,
            accuracy_hint=accuracy_hint,
        )

    # Exhausted retries without success
    return _build_result(
        response_text="Unable to generate a valid SQL query after multiple attempts. Please rephrase your question.",
        result_type="db_result",
        db_error=None,
        accuracy_hint=accuracy_hint,
    )
