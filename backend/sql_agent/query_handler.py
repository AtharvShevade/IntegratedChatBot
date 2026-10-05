# backend/sql_agent/query_handler.py
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
# get_relevant_schema now returns a RetrievalResult object (tables, columns,
# matched_labels, qa_example, concept_bindings) instead of a plain tuple —
# deliberately non-iterable so any stale positional-unpack call site fails
# loudly instead of silently reading a stale shape.

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

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


# M-07: matches a raw Oracle error code/message, or a Python exception's own
# string form -- the shapes a real internal error takes, never a
# validate_sql()-produced message (which is always plain English describing
# a schema/keyword/structure problem). Applied as the ONE choke point every
# response dict is built through (_build_result below), so a future call
# site that accidentally passes a raw exception string into db_error cannot
# ship it to the client -- it is caught here regardless of which code path
# forgot to sanitize it itself.
_RAW_INTERNAL_ERROR_PATTERN = re.compile(
    r"ORA-\d{4,5}"                                   # Oracle error code
    r"|Connection failed:|Query execution failed:"   # executor.py's own exception prefixes
    r"|Unexpected error:|Traceback \(most recent call last\)"
    r"|dry-run skipped",                              # executor.py's dry-run connection-failure prefix
    re.IGNORECASE,
)


def _safe_client_error(db_error: str | None) -> str | None:
    """M-07: never let a raw Oracle exception, Python exception, or internal
    diagnostic string reach the client — only validate_sql()'s own plain-
    English reasons (e.g. "Hallucinated columns...", "Dangerous keyword
    detected...") pass through unchanged, since those describe the GENERATED
    SQL's shape, not the server's internals, and are genuinely useful to a
    caller building on top of this API. Anything matching an internal-error
    shape is logged here (the one place it's about to be dropped) and
    replaced with a generic message."""
    if not db_error:
        return db_error
    if _RAW_INTERNAL_ERROR_PATTERN.search(db_error):
        logger.warning("[SQL_AGENT] M-07: suppressed internal error detail from client response: %s", db_error)
        return "A database error occurred while processing your query. Please try again."
    return db_error


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
    db_error = _safe_client_error(db_error)
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


def _resolve_target_return_form_ids(table_names: list[str]) -> tuple[set[str], list[str]]:
    """H-02: map SQL-Agent-selected table(s) back to the regulatory return(s)
    they belong to, and resolve each to the FormId the rest of the 5.5 app
    already authorizes by (auth_service.get_allowed_form_ids's vocabulary).

    Two existing, already-configured pieces are reused here — nothing new is
    built or regenerated:
      - sqlcore.sql_generator._load_table_entries(): reads schema.json (the
        SAME file validate_sql() already reads for column-hallucination
        checks) and returns each table's full entry, including its
        `return_name` field. Read-only, no FAISS/embeddings/retrieval
        involvement at all.
      - backend.tools.report_lookup.find_matching_reports_tiered(): the
        existing Returns.xml name resolver already used by the
        status/generate/schedule flows. Only a MATCH_EXACT, single-candidate
        result is trusted here — a fuzzy/ambiguous match is treated as
        unresolved (see PART 10: never guess).

    Returns (form_ids, unresolved_return_names). An unresolved return name
    (one present in schema.json but not confidently mapped to a Returns.xml
    FormId) means the caller must NOT treat this as an unscoped/allowed
    query -- see _authorize_sql_agent_access.
    """
    from sqlcore.sql_generator import _load_table_entries
    from backend.tools.report_lookup import find_matching_reports_tiered, MATCH_EXACT

    entries = _load_table_entries(table_names)
    return_names = sorted({
        (entry.get("return_name") or "").strip()
        for entry in entries.values()
        if (entry.get("return_name") or "").strip()
    })

    form_ids: set[str] = set()
    unresolved: list[str] = []
    for name in return_names:
        matches, tier = find_matching_reports_tiered(name)
        fid = matches[0].get("Id", "").strip() if (tier == MATCH_EXACT and len(matches) == 1) else ""
        if fid:
            form_ids.add(fid)
        else:
            unresolved.append(name)

    return form_ids, unresolved


def _authorize_sql_agent_access(login_id: str | None, table_names: list[str]) -> tuple[bool, str | None]:
    """H-02: gate SQL Agent access using the EXISTING 5.5 department/return
    authorization (auth_service.get_allowed_form_ids/get_allowed_nx_form_ids,
    via access_control.resolve_allowed_form_ids) -- no new authorization
    system, no tenant concept. 5.5 only.

    Returns (allowed, denial_message); denial_message is None when allowed.
    Never calls into SQL generation/execution itself -- purely a gate the
    caller must check before doing either.
    """
    if not login_id or not login_id.strip():
        logger.warning("[SQL_AGENT] H-02: no login_id provided -- denying.")
        return False, (
            "You need to be signed in to use the database query assistant. "
            "Please reload and try again."
        )

    from backend.db_qa.access_control import resolve_allowed_form_ids
    try:
        allowed_form_ids = resolve_allowed_form_ids(login_id)
    except PermissionError as exc:
        logger.warning("[SQL_AGENT] H-02: login_id=%r not recognised: %s", login_id, exc)
        return False, str(exc)

    if allowed_form_ids is None:
        # AUTHORIZATION_ENABLED=false -- the same process-wide, admin-only
        # bypass every other authorization check in this app already honors.
        return True, None

    target_form_ids, unresolved = _resolve_target_return_form_ids(table_names)
    if unresolved or not target_form_ids:
        # PART 10: retrieval could not reliably identify which return(s) this
        # question targets (or a table's return_name didn't map to an exact
        # Returns.xml entry) -- never guess the user's authorization here.
        logger.info(
            "[SQL_AGENT] H-02: could not verify target return(s) for tables=%s "
            "(unresolved=%s) -- denying rather than guessing.", table_names, unresolved,
        )
        return False, (
            "I couldn't determine which return this question refers to, so I "
            "can't confirm you have access to it. Please mention the specific "
            "return name in your question."
        )

    if not target_form_ids.issubset(allowed_form_ids):
        # Require EVERY targeted return to be allowed, not just any overlap --
        # a query spanning two returns where the user has access to only one
        # must still be denied in full, not partially answered.
        logger.info(
            "[SQL_AGENT] H-02: login_id=%r denied -- target_form_ids=%s not all in "
            "allowed set (%d forms)", login_id, target_form_ids, len(allowed_form_ids),
        )
        return False, (
            "You don't currently have access to this return. Please try a "
            "query for another return you have access to."
        )

    return True, None


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

    retrieval = get_relevant_schema(
        query, query_vec=query_vec, shortlist_k=config.SRC_CONFIG.SHORTLIST_K,
    )
    tables, columns = retrieval.tables, retrieval.columns
    matched_labels, qa_example = retrieval.matched_labels, retrieval.qa_example
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


async def handle_db_query(
    message: str, session_id: str | None = None, login_id: str | None = None,
) -> dict[str, Any]:
    """
    Full NL → SQL → Execute pipeline.

    Steps:
      1. Length guard — ask for more detail if query is too short
      2. Retrieve + select relevant schema (FAISS + selector), or short-circuit
         on a verified stored question
      2.5. H-02: identify the target return(s) and authorize login_id against
           them using the existing 5.5 department/return access check, BEFORE
           any SQL is generated.
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

        # H-02: authorize BEFORE validating/executing the stored SQL — a
        # verified Q&A pair is still scoped to whatever return its table
        # belongs to, and must not bypass the access check.
        allowed, denial_message = _authorize_sql_agent_access(login_id, [exact["table"]])
        if not allowed:
            return _build_result(
                response_text=denial_message,
                result_type="db_result",
                accuracy_hint=accuracy_hint,
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

    # ── Step 1.5: H-02 authorization ──────────────────────────────────────────
    # Identify the target return(s) from the final selected tables and
    # authorize BEFORE any SQL is generated — never after. No LLM call, no
    # Oracle connection, happens entirely here.
    allowed, denial_message = _authorize_sql_agent_access(login_id, [t["table"] for t in tables])
    if not allowed:
        return _build_result(
            response_text=denial_message,
            result_type="db_result",
            accuracy_hint=accuracy_hint,
        )

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
