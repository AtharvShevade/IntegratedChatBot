# backend/sql_agent/__init__.py
#
# Chatbot-side adapter for the SQL agent vendored at <project_root>/sql_agent.
# Exposes handle_db_query(), called by:
#   - backend/guided.py            STAGE_DB_QUERY handler
#   - backend/agent/__init__.py    query_database intent handler
#
# This module owns the *chatbot contract* (the ChatResponse-shaped dict, the
# minimum-word guard, the retry budget, the accuracy hints); the vendored agent
# owns the NL→SQL pipeline. The vendored agent ships its own FastAPI app under
# sql_agent/api — that layer is deliberately unused: this project's own
# /chat endpoint and React frontend stay the entry point, so only the pipeline
# below is reused.
#
# Pipeline (mirrors sql_agent/api/routes/query.py, which is the reference
# implementation of the same stages):
#   0. embed the query ONCE                       retriever.compute_query_embedding
#   1. verified-answer tier: near-identical stored question → reuse its SQL
#                                                 retriever.find_exact_qa_match
#   2. retrieval, wide for recall                 retriever.get_relevant_schema
#   3. selection, narrow for precision            selector.select_tables
#   4. generate → validate → execute (retry loop)
#
# Steps 1-4 in the OLD agent were a 3-tuple retrieval feeding generation
# directly. The selection stage and the exact-match tier are new, and
# get_relevant_schema now returns four values.

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from backend.sql_agent import _bootstrap

# Runs before any `src.*` import anywhere in this package: puts the vendored
# agent on sys.path and maps this project's .env names onto the ones it reads.
_bootstrap.ensure()

logger = logging.getLogger(__name__)

# ── Minimum word-count guard ───────────────────────────────────────────────────
MIN_QUERY_WORDS = 5   # queries with fewer words are too vague for accurate SQL
MAX_SQL_RETRIES = 2   # max generate→validate→execute attempts per user query

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


def _rows_result(col_names, serialized_rows, sql, accuracy_hint) -> dict[str, Any]:
    """Shared success/empty-result shaping for both the exact-match tier and the
    generated-SQL path."""
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
                "• Adding a time period — e.g. 'Q1 FY2024', 'March 2025', 'latest'\n"
                "• Being more specific — e.g. include the report section name\n"
                "• Checking the spelling of report/section names"
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


def _retrieve(query: str):
    """Steps 0-3, all blocking — run as one unit on a worker thread.

    Returns (tables, columns, matched_labels, qa_example, exact) where `exact` is
    a verified stored question/SQL pair when the user typed essentially the same
    sentence (in which case the other four are empty and no LLM is involved).
    """
    from backend.sql_agent import config
    from backend.sql_agent.retriever import (
        compute_query_embedding, find_exact_qa_match, get_relevant_schema,
    )

    query_vec = compute_query_embedding(query)

    exact = find_exact_qa_match(query, query_vec=query_vec)
    if exact:
        return [], [], [], None, exact

    tables, columns, matched_labels, qa_example = get_relevant_schema(
        query, query_vec=query_vec, shortlist_k=config.SRC_CONFIG.SHORTLIST_K,
    )
    if not tables:
        return [], [], [], None, None

    # Narrow the shortlist to what the SQL model may see, then drop the columns
    # and row labels belonging to tables the selector rejected so nothing from a
    # discarded table leaks into the prompt.
    from backend.sql_agent.selector import select_tables
    from backend.sql_agent.semantic_layer import load_join_graph

    tables, selection = select_tables(
        query, tables, matched_labels=matched_labels, join_graph=load_join_graph(),
    )
    selected = {t["table"] for t in tables}
    columns = [c for c in columns if c["table"] in selected]
    matched_labels = [l for l in matched_labels if l["table"] in selected]

    return tables, columns, matched_labels, (qa_example, selection), None


async def handle_db_query(message: str, session_id: str | None = None) -> dict[str, Any]:
    """
    Full NL → SQL → Execute pipeline.

    Steps:
      1. Length guard — ask for more detail if query is too short
      2. Retrieve + select relevant schema (FAISS + selector), or short-circuit
         on a verified stored question
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
                "• 'Overseas assets total for ALE section 1A'\n"
                "• 'Total loan assets from RAQ section 1 latest'\n"
                "• 'Fetch derivative notional principal from ALE domestic'"
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

    from backend.sql_agent.executor import execute_query
    from backend.sql_agent.sql_generator import generate_sql, validate_sql
    from backend.sql_agent.utils import serialize_rows

    # ── Step 1: retrieval + selection ─────────────────────────────────────────
    # Run on a worker thread (not directly on the event loop) so this
    # coroutine has a real `await` suspension point — that's what lets
    # /stop's task.cancel() interrupt this request immediately instead of
    # only taking effect after the whole (possibly 300s+) pipeline finishes,
    # and it keeps this session's blocking work from stalling every other
    # session sharing the single event loop in the meantime.
    try:
        tables, columns, matched_labels, gen_context, exact = await asyncio.to_thread(_retrieve, q)
    except Exception as exc:
        logger.error("[SQL_AGENT] Schema retrieval failed: %s", exc)
        return _build_result(
            response_text="Unable to process your database query right now. Please try again later.",
            result_type="db_result",
            db_error=None,
        )

    # ── Verified-answer tier ──────────────────────────────────────────────────
    # The user typed essentially the same sentence as a stored, hand-verified
    # question: nothing to retrieve or generate, so execute its SQL directly.
    # Fully deterministic, zero hallucination risk.
    if exact:
        sql = exact["sql"]
        logger.info(
            "[SQL_AGENT] exact QA match (text_similarity=%.3f) table=%s",
            exact["text_similarity"], exact["table"],
        )
        is_valid, reason = validate_sql(sql, [{"table": exact["table"]}], [])
        if not is_valid:
            logger.warning("[SQL_AGENT] stored SQL failed validation: %s", reason)
            return _build_result(
                response_text="Unable to process your query right now. Please try again.",
                result_type="db_result",
                db_sql=sql,
                db_error=reason,
                accuracy_hint=accuracy_hint,
            )
        try:
            col_names, rows, db_error = await asyncio.to_thread(execute_query, sql)
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
            logger.error("[SQL_AGENT] db_error=%s", db_error)
            return _build_result(
                response_text="Unable to retrieve the requested information. Please try again.",
                result_type="db_result",
                db_sql=sql,
                db_error=None,
                accuracy_hint=accuracy_hint,
            )
        return _rows_result(col_names, serialize_rows(rows), sql, accuracy_hint)

    if not tables:
        return _build_result(
            response_text="No matching tables found for your query. Try rephrasing with different keywords.",
            result_type="db_result",
            accuracy_hint=accuracy_hint,
        )

    qa_example, selection = gen_context
    logger.info("[SQL_AGENT] selected=%s", [t["table"] for t in tables])

    # ── Step 2: SQL generation ────────────────────────────────────────────────
    # Worker thread — see the note above on Step 1.
    #
    # No outer generate→validate→execute retry loop here any more: the new
    # generate_sql() runs its own correction loop internally (regex validation +
    # an Oracle EXPLAIN PLAN dry run after every attempt, a deterministic
    # vertical-aggregation autocorrect, then targeted correction prompts). Since
    # it generates at temperature 0, re-calling it with the identical prompt
    # would reproduce the identical SQL — the old outer loop only helped because
    # the old generate_sql accepted previous_sql/previous_error, which this one
    # does not. MAX_SQL_RETRIES now covers only transient Ollama failures.
    sql = ""
    for attempt in range(MAX_SQL_RETRIES):
        try:
            result = await asyncio.to_thread(
                generate_sql,
                q, tables, columns, matched_labels=matched_labels,
                qa_example=qa_example, selection=selection,
            )
            sql = result.get("sql", "")
            for warning in result.get("warnings") or []:
                logger.warning("[SQL_AGENT] %s", warning)
            logger.info("[SQL_AGENT] sql=\n%s", sql)
            break
        except RuntimeError as exc:
            # generate_sql() raises RuntimeError for Ollama-level failures
            # (connection refused, timeout, HTTP 5xx from a proxy) — these
            # are transient infra issues, not "the model wrote bad SQL", so
            # they get a second chance instead of failing outright on the very
            # first hiccup.
            logger.error("[SQL_AGENT] attempt=%d SQL generation failed: %s", attempt + 1, exc)
            if attempt + 1 < MAX_SQL_RETRIES:
                continue
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

    # ── Step 3: validation ────────────────────────────────────────────────────
    # generate_sql already validated (and tried to correct) this; re-checking is
    # cheap and is what decides whether we are allowed to execute at all — it
    # returns SQL that is still invalid rather than raising.
    is_valid, reason = validate_sql(sql, tables, columns)
    logger.debug("[SQL_AGENT] valid=%s reason=%s", is_valid, reason)
    if not is_valid:
        return _build_result(
            response_text="Unable to process your query right now. Please try again.",
            result_type="db_result",
            db_sql=sql,
            db_error=reason,
            accuracy_hint=accuracy_hint,
        )

    # ── Step 4: execution (worker thread — see note above on Step 1) ──────────
    try:
        col_names, rows, db_error = await asyncio.to_thread(execute_query, sql)
        serialized_rows = serialize_rows(rows)
        logger.info("[SQL_AGENT] rows=%d db_error=%s", len(rows), db_error)
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
        logger.error("[SQL_AGENT] db_error=%s", db_error)
        return _build_result(
            response_text="Unable to retrieve the requested information. Please try again.",
            result_type="db_result",
            db_sql=sql,
            db_error=None,
            accuracy_hint=accuracy_hint,
        )

    return _rows_result(col_names, serialized_rows, sql, accuracy_hint)
