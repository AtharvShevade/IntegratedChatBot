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
    need_clarification: bool         = False,
    options:        list[str]        = None,
) -> dict[str, Any]:
    db_error = _safe_client_error(db_error)
    return {
        "intent":             "query_database",
        "report_name":        None,
        "response_text":      response_text,
        "need_clarification": need_clarification,
        "result_type":        result_type,
        "options":            options or [],
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

    def _exact_form_id(name: str) -> str:
        matches, tier = find_matching_reports_tiered(name)
        return matches[0].get("Id", "").strip() if (tier == MATCH_EXACT and len(matches) == 1) else ""

    form_ids: set[str] = set()
    unresolved: list[str] = []
    for name in return_names:
        fid = _exact_form_id(name)
        if fid:
            form_ids.add(fid)
            continue
        # A table shared by several frequencies lists them in one field, e.g.
        # "CIMS_RAQ(Annually), CIMS_RAQ(Monthly), CIMS_RAQ(Quarterly)". Resolve
        # each name on its own; every one must match a return exactly, otherwise
        # the whole entry stays unresolved (still never guess).
        parts = [p.strip() for p in name.split(",") if p.strip()]
        part_ids = [_exact_form_id(p) for p in parts] if len(parts) > 1 else []
        if part_ids and all(part_ids):
            form_ids.update(part_ids)
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

    from backend.db_qa.access_control import is_admin, resolve_allowed_form_ids

    # Admin role (APP_DB_ADMIN_ROLE_ID, same check the DB Q&A layer uses) has
    # access to every return, so no per-return check is needed -- and none can
    # be made reliably: many tables carry composite return names
    # ("CIMS_RAQ(Annually), CIMS_RAQ(Monthly), ...") that match no single
    # Returns.xml entry. Non-admin users still go through the check below.
    try:
        if is_admin(login_id):
            logger.info("[SQL_AGENT] H-02: login_id=%r is admin -- all returns allowed.", login_id)
            return True, None
    except Exception as exc:
        logger.warning("[SQL_AGENT] H-02: admin check failed for login_id=%r (%s) -- using normal check.", login_id, exc)

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


def _retrieve(query: str, return_names: list[str] | None = None):
    """Steps 0-3, all blocking — run as one unit on a worker thread.

    Returns (tables, columns, matched_labels, qa_example, exact) where `exact` is
    a verified stored question/SQL pair when the user typed essentially the same
    sentence (in which case the other four are empty and no LLM is involved).

    `return_names`: the return(s) the question explicitly names. When given,
    retrieval is scoped to those returns' tables only (the return name is also
    added to the retrieval text to pull their tables into the shortlist). If the
    scoped shortlist ends up empty, the unscoped result is used unchanged.
    """
    from backend.sql_agent import config
    from backend.sql_agent.context_resolver import load_returns, tables_for_returns
    from backend.sql_agent.retriever import (
        compute_query_embedding, find_exact_qa_match, get_relevant_schema,
    )

    scope = tables_for_returns(return_names) if return_names else set()

    query_vec = compute_query_embedding(query)

    exact = find_exact_qa_match(query, query_vec=query_vec)
    if exact and (not scope or str(exact.get("table", "")).lower() in scope):
        return [], [], [], None, exact

    retrieval_text, retrieval_vec = query, query_vec
    shortlist_k = config.SRC_CONFIG.SHORTLIST_K
    if scope:
        catalogue = load_returns()
        titles = " ".join(catalogue[r].title for r in return_names if r in catalogue)
        if titles and titles.lower() not in query.lower():
            retrieval_text = f"{query} {titles}"
            retrieval_vec = compute_query_embedding(retrieval_text)
        shortlist_k = max(shortlist_k or 0, len(scope), 5)

    retrieval = get_relevant_schema(
        retrieval_text, query_vec=retrieval_vec, shortlist_k=shortlist_k,
    )
    tables, columns = retrieval.tables, retrieval.columns
    matched_labels, qa_example = retrieval.matched_labels, retrieval.qa_example

    if scope and tables:
        scoped = [t for t in tables if str(t["table"]).lower() in scope]
        if scoped:
            kept = {t["table"] for t in scoped}
            tables = scoped
            columns = [c for c in columns if c["table"] in kept]
            matched_labels = [l for l in matched_labels if l["table"] in kept]
            if qa_example and qa_example.get("table") not in kept:
                qa_example = None
            logger.info("[SQL_AGENT] retrieval scoped to return(s) %s -> %s", return_names, sorted(kept))
        else:
            logger.info(
                "[SQL_AGENT] no shortlisted table belongs to return(s) %s -- using unscoped retrieval",
                return_names,
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


# ── Follow-up handling (previous SQL-agent answer in this session) ────────────

_FOLLOWUP_SYSTEM = """You help a database assistant understand follow-up messages.
The assistant previously answered a database question and showed a result table.
Classify the user's NEW message into exactly one type:
  "data_question" - asks about the result already shown (highest/lowest value, explain, summarise,
                    compare rows of it, total of the shown rows) and can be answered from that table alone.
  "refine"        - wants the same kind of query again with something changed (a different date or period,
                    a different return/table, an extra filter, more or other columns, "same for ...").
  "new"           - an unrelated, self-contained new question.
For "refine", also write "question": ONE standalone question that combines the previous question with the
change, keeping the previous return name and reporting period unless the user changed them.
Reply with JSON only, e.g. {"type": "refine", "question": "..."} or {"type": "data_question"}."""

_ANSWER_SYSTEM = """You are a regulatory-reporting data assistant. Answer the user's question using ONLY
the result table provided. Quote the exact numbers and row labels from the table. If the table does not
contain what is needed, say so plainly and suggest how to ask for it. Be concise (at most 6 sentences).
Never invent values."""


def _context_brief(ctx: dict[str, Any]) -> str:
    return (
        f"Previous question: {ctx.get('question')}\n"
        f"Return(s): {', '.join(ctx.get('returns') or []) or 'unknown'}\n"
        f"Reporting period: {ctx.get('period_label') or 'latest available'}\n"
        f"Result columns: {', '.join(map(str, ctx.get('columns') or []))}\n"
        f"Rows returned: {ctx.get('row_count', 0)}"
    )


def _result_table_text(ctx: dict[str, Any], max_cell: int = 60) -> str:
    cols = [str(c) for c in ctx.get("columns") or []]
    lines = [" | ".join(cols)]
    for row in ctx.get("rows") or []:
        lines.append(" | ".join(str(v)[:max_cell] if v is not None else "" for v in row))
    if ctx.get("row_count", 0) > len(ctx.get("rows") or []):
        lines.append(f"... ({ctx['row_count']} rows in total, first {len(ctx['rows'])} shown)")
    return "\n".join(lines)


def _parse_json_obj(text: str) -> dict[str, Any] | None:
    import json
    m = re.search(r"\{.*\}", text or "", re.DOTALL)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


async def _classify_followup(message: str, ctx: dict[str, Any], history) -> tuple[str, str | None]:
    """("data_question" | "refine" | "new", standalone question for refine)."""
    from backend.services.llm_service import _call_ollama
    prompt = f"{_context_brief(ctx)}\n\nNEW message: {message}"
    try:
        raw = await _call_ollama(prompt, _FOLLOWUP_SYSTEM, history=(history or [])[-4:], temperature=0.0)
    except Exception as exc:
        logger.warning("[SQL_AGENT] follow-up classification failed (%s) -- treating as new question", exc)
        return "new", None
    obj = _parse_json_obj(raw) or {}
    kind = str(obj.get("type", "")).strip().lower()
    if kind not in ("data_question", "refine", "new"):
        kind = "new"
    standalone = (obj.get("question") or "").strip() or None
    if kind == "refine" and not standalone:
        standalone = f"{ctx.get('question')} — {message}"
    logger.info("[SQL_AGENT] follow-up type=%s standalone=%r", kind, standalone)
    return kind, standalone


async def _answer_from_previous(message: str, ctx: dict[str, Any], history) -> dict[str, Any] | None:
    """Answer a question about the result already shown, without new SQL."""
    from backend.services.llm_service import _call_ollama
    prompt = (
        f"{_context_brief(ctx)}\n\nResult table:\n{_result_table_text(ctx)}\n\n"
        f"User question: {message}"
    )
    try:
        answer = (await _call_ollama(prompt, _ANSWER_SYSTEM, history=(history or [])[-4:], temperature=0.1)).strip()
    except Exception as exc:
        logger.warning("[SQL_AGENT] answering from previous result failed: %s", exc)
        return None
    if not answer:
        return None
    return _build_result(response_text=answer, result_type="db_result")


def _pick_pending_option(message: str, options: list[str]) -> str | None:
    from backend.sql_agent.context_resolver import detect_returns
    low = message.strip().lower()
    for o in options:
        if low == o.lower():
            return o
    if low.isdigit() and 1 <= int(low) <= len(options):
        return options[int(low) - 1]
    hits = [o for o in options if o in detect_returns(message)]
    if len(hits) == 1:
        return hits[0]
    contains = [o for o in options if low and (low in o.lower() or o.lower() in low)]
    return contains[0] if len(contains) == 1 else None


# ── Reporting-date helpers ────────────────────────────────────────────────────

def _fmt_date(v) -> str | None:
    if v is None:
        return None
    try:
        return v.strftime("%d-%b-%Y")
    except AttributeError:
        return str(v)[:10]


def _scalar(sql: str):
    """First cell of a tiny lookup query, or None on any failure."""
    from backend.sql_agent.executor import execute_query
    try:
        _cols, rows, err = execute_query(sql)
    except Exception as exc:
        logger.debug("[SQL_AGENT] date lookup failed: %s", exc)
        return None
    if err or not rows:
        return None
    return rows[0][0]


def _safe_ident(name: str) -> str | None:
    return name if re.fullmatch(r"[A-Za-z_][\w$#]*", name or "") else None


def _latest_rdate(table: str, period=None):
    t = _safe_ident(table)
    if not t:
        return None
    if period is None:
        return _scalar(f"SELECT MAX(RDATE) FROM {t}")
    return _scalar(
        f"SELECT MAX(RDATE) FROM {t} WHERE RDATE BETWEEN "
        f"TO_DATE('{period.start.isoformat()}', 'YYYY-MM-DD') AND TO_DATE('{period.end.isoformat()}', 'YYYY-MM-DD')"
    )


def _nearest_rdate_before(table: str, d) -> Any:
    t = _safe_ident(table)
    if not t:
        return None
    return _scalar(f"SELECT MAX(RDATE) FROM {t} WHERE RDATE <= TO_DATE('{d.isoformat()}', 'YYYY-MM-DD')")


def _pin_period(sql: str, tables, columns, period, validate_sql) -> str:
    """Pin *sql* to the explicitly named period (no-op when *period* is None),
    keeping the model's own SQL whenever the rewrite fails validation."""
    if period is None:
        return sql
    from backend.sql_agent.latest_date import apply_explicit_date
    label = f"explicit period {period.label}"
    try:
        new_sql, changed = apply_explicit_date(sql, tables, period.start, period.end)
        if changed:
            ok, why = validate_sql(new_sql, tables, columns)
            if ok:
                logger.info("[SQL_AGENT] sql (%s applied)=\n%s", label, new_sql)
                return new_sql
            logger.warning("[SQL_AGENT] %s rejected by validation (%s); keeping model SQL", label, why)
    except Exception as exc:
        logger.warning("[SQL_AGENT] period pinning skipped: %s", exc)
    return sql


def _date_stats(table: str):
    """(distinct reporting dates, earliest, latest) for *table*, or None on failure."""
    t = _safe_ident(table)
    if not t:
        return None
    from backend.sql_agent.executor import execute_query
    try:
        _c, rows, err = execute_query(f"SELECT COUNT(DISTINCT RDATE), MIN(RDATE), MAX(RDATE) FROM {t}")
    except Exception as exc:
        logger.debug("[SQL_AGENT] date stats failed: %s", exc)
        return None
    if err or not rows:
        return None
    return int(rows[0][0] or 0), rows[0][1], rows[0][2]


async def _date_hint(sql: str, primary_table: str | None, period, row_count: int) -> tuple[str | None, str | None]:
    """(accuracy_hint, more_info_hint) describing which reporting date the
    answer is for — or, for an explicit period with no rows, which dates exist."""
    if not primary_table:
        return None, None
    if period is not None:
        if row_count == 0:
            nearest = await asyncio.to_thread(_nearest_rdate_before, primary_table, period.end)
            latest = await asyncio.to_thread(_latest_rdate, primary_table)
            parts = [f"No data is available for {period.label}."]
            if nearest is not None:
                parts.append(f"The nearest earlier reporting date is {_fmt_date(nearest)}.")
            if latest is not None:
                parts.append(f"The latest available reporting date is {_fmt_date(latest)}.")
            return None, " ".join(parts)
        actual = await asyncio.to_thread(_latest_rdate, primary_table, period)
        if actual is not None and not period.is_single_day:
            return f"Showing data for reporting date {_fmt_date(actual)} ({period.label}).", None
        return f"Showing data for reporting date {_fmt_date(actual) or period.label}.", None
    if row_count == 0:
        stats = await asyncio.to_thread(_date_stats, primary_table)
        if stats:
            count, first, last = stats
            from backend.sql_agent.latest_date import uses_prior_period_pattern
            if count == 0:
                return None, "The table has no data at all."
            if uses_prior_period_pattern(sql) and count < 2:
                return None, (
                    f"There is no previous reporting period to compare with: this table has data for only one "
                    f"reporting date ({_fmt_date(last)})."
                )
            span = f"{_fmt_date(first)} to {_fmt_date(last)}" if count > 1 else _fmt_date(last)
            return None, (
                f"No rows matched. This table has {count} reporting date{'s' if count != 1 else ''} "
                f"({span}); the latest is {_fmt_date(last)}. The question may refer to a row or "
                f"period that is not in the data."
            )
    if re.search(r"MAX\s*\(\s*(?:\w+\.)?RDATE\s*\)", sql or "", re.IGNORECASE):
        latest = await asyncio.to_thread(_latest_rdate, primary_table)
        if latest is not None:
            return (
                f"No date was mentioned, so this shows the latest available reporting date: "
                f"{_fmt_date(latest)}. Mention a date (e.g. 31-Mar-2025) for another period."
            ), None
    return None, None


async def _finish(
    *, q: str, sql: str, col_names, rows, tables_used: list[str], period,
    session_id: str | None, base_hint: str | None,
) -> dict[str, Any]:
    from backend.sql_agent.context_resolver import returns_for_tables
    from backend.sql_agent import session_context
    from backend.sql_agent.utils import serialize_rows

    serialized_rows = serialize_rows(rows)
    primary = tables_used[0] if tables_used else None
    date_hint, no_data_hint = await _date_hint(sql, primary, period, len(serialized_rows))
    result = _rows_result(col_names, serialized_rows, sql, date_hint or base_hint)
    if no_data_hint:
        result["response_text"] = no_data_hint
        # Only suggest re-asking with a date when the hint actually lists dates to pick from.
        _lists_dates = "nearest earlier" in no_data_hint or "latest available" in no_data_hint
        result["more_info_hint"] = no_data_hint + (" Ask again with one of those dates." if _lists_dates else "")

    session_context.save_result(
        session_id, question=q, returns=returns_for_tables(tables_used), tables=tables_used,
        sql=sql, columns=list(col_names or []), rows=serialized_rows,
        period_label=period.label if period is not None else None,
    )
    return result


_MULTI_RETURN_OK_RE = re.compile(r"\b(compar\w*|both|versus|vs\.?|across|each\s+return|all\s+returns)\b", re.IGNORECASE)


def _clarify_return(q: str, candidates: list[str], session_id: str | None) -> dict[str, Any]:
    from backend.sql_agent import session_context
    session_context.save_pending_clarification(session_id, question=q, options=candidates)
    return _build_result(
        response_text=(
            "Your question matches data in more than one return. "
            "Which return should I look in? Pick one below, or ask again mentioning the return name."
        ),
        result_type="db_result",
        need_clarification=True,
        options=candidates,
    )


async def handle_db_query(
    message: str, session_id: str | None = None, login_id: str | None = None,
    conversation_history: list[dict] | None = None,
) -> dict[str, Any]:
    """
    Full NL → SQL → Execute pipeline.

    Steps:
      0. Session context — resolve a pending "which return?" answer, or a
         follow-up on the previous SQL answer (answered from the shown rows,
         or rewritten into a standalone question).
      1. Length guard — ask for more detail if query is too short
      1.5 Context — named return(s) (scope retrieval to their tables) and the
         named reporting date/period (no date = latest available RDATE)
      2. Retrieve + select relevant schema (FAISS + selector), or short-circuit
         on a verified stored question; ask which return when the matched
         tables span several returns and none was named
      2.5. H-02: identify the target return(s) and authorize login_id against
           them using the existing 5.5 department/return access check, BEFORE
           any SQL is generated.
      3. Generate SQL via LLM (sql_generator)
      4. Validate SQL (SELECT-only + hallucination check)
      5. Execute on Oracle DB (executor)
      6. Return result dict matching ChatResponse shape

    Returns a dict that can be passed directly to ChatResponse(**result).
    """
    from backend.sql_agent import session_context
    from backend.sql_agent.context_resolver import (
        detect_returns, extract_report_date, returns_for_tables,
    )

    q = message.strip()
    forced_returns: list[str] | None = None
    resolved_from_context = False

    # ── Step 0: session context ───────────────────────────────────────────────
    ctx = session_context.get(session_id)
    if ctx and ctx.get("pending"):
        pending = ctx["pending"]
        chosen = _pick_pending_option(q, pending["options"])
        session_context.clear_pending(session_id)
        if chosen:
            q = f"{pending['question']} in return {chosen}"
            forced_returns = [chosen]
            resolved_from_context = True
            logger.info("[SQL_AGENT] clarification resolved -> return=%s question=%r", chosen, q)
    elif ctx and ctx.get("sql") and session_context.looks_like_followup(session_id, q):
        kind, standalone = await _classify_followup(q, ctx, conversation_history)
        if kind == "data_question":
            answered = await _answer_from_previous(q, ctx, conversation_history)
            if answered is not None:
                return answered
        elif kind == "refine" and standalone:
            q = standalone
            resolved_from_context = True
            if not detect_returns(q) and ctx.get("returns"):
                forced_returns = list(ctx["returns"])

    # ── Guard 1: minimum word count ────────────────────────────────────────────
    word_count = len(q.split())
    if word_count < MIN_QUERY_WORDS and not resolved_from_context:
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

    # ── Step 1.5: named return(s) and reporting period ────────────────────────
    named_returns = forced_returns or detect_returns(q)
    if len(named_returns) > 1 and not _MULTI_RETURN_OK_RE.search(q):
        return _clarify_return(q, named_returns, session_id)
    period = extract_report_date(q)
    logger.info("[SQL_AGENT] context returns=%s period=%s", named_returns, period)

    # ── Soft hint when no time context detected ───────────────────────────────
    accuracy_hint = None
    if period is None and not _has_time_context(q):
        accuracy_hint = (
            "Tip: For more accurate results, try specifying a time period — "
            "e.g. a specific date (01-Mar-2025), month (March 2025), "
            "quarter (Q1 FY2024), or year (2024)."
        )

    from backend.sql_agent.executor import execute_query
    from backend.sql_agent.sql_generator import generate_sql, validate_sql

    # ── Step 1: retrieval + selection ─────────────────────────────────────────
    # Run on a worker thread (not directly on the event loop) so this
    # coroutine has a real `await` suspension point — that's what lets
    # /stop's task.cancel() interrupt this request immediately instead of
    # only taking effect after the whole (possibly 300s+) pipeline finishes,
    # and it keeps this session's blocking work from stalling every other
    # session sharing the single event loop in the meantime.
    try:
        _retrieve_args = (q, named_returns) if named_returns else (q,)
        tables, columns, matched_labels, gen_context, exact = await asyncio.to_thread(
            _retrieve, *_retrieve_args,
        )
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

        exact_tables = [{"table": exact["table"]}]
        # Stored SQL defaults to the latest RDATE; pin it to a named period.
        sql = _pin_period(sql, exact_tables, [], period, validate_sql)

        is_valid, reason = validate_sql(sql, exact_tables, [])
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
        return await _finish(
            q=q, sql=sql, col_names=col_names, rows=rows, tables_used=[exact["table"]],
            period=period, session_id=session_id, base_hint=accuracy_hint,
        )

    if not tables:
        return _build_result(
            response_text="No matching tables found for your query. Try rephrasing with different keywords.",
            result_type="db_result",
            accuracy_hint=accuracy_hint,
        )

    qa_example, selection = gen_context
    logger.info("[SQL_AGENT] selected=%s", [t["table"] for t in tables])

    # ── Ambiguity: no return named and the selected tables span several ───────
    if not named_returns:
        owners = returns_for_tables([t["table"] for t in tables])
        if len(owners) > 1 and not _MULTI_RETURN_OK_RE.search(q):
            logger.info("[SQL_AGENT] selected tables span returns %s -- asking user", owners)
            return _clarify_return(q, owners, session_id)

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

    # ── Step 2.4: undo an unasked "previous period" ────────────────────────────
    # The model sometimes copies the "second-latest RDATE" idiom from stored
    # examples for a question that never asked for it; on a table with one
    # reporting date that returns nothing. Use the latest date instead.
    try:
        from backend.sql_agent.latest_date import collapse_unasked_prior_period
        _fixed_sql, _fixed = collapse_unasked_prior_period(sql, q)
        if _fixed:
            _ok, _why = validate_sql(_fixed_sql, tables, columns)
            if _ok:
                sql = _fixed_sql
                logger.info("[SQL_AGENT] sql (unasked previous-period removed)=\n%s", sql)
            else:
                logger.warning("[SQL_AGENT] previous-period rewrite rejected (%s); keeping model SQL", _why)
    except Exception as exc:
        logger.warning("[SQL_AGENT] previous-period check skipped: %s", exc)

    # ── Step 2.5: pin the reporting period ────────────────────────────────────
    # A named date/period: rewrite the latest-RDATE idiom (or wrap the tables)
    # so the answer is for exactly that period. No period named: default to the
    # latest one. The prompt asks for this already; this is the mechanical
    # backstop for a model that ignored it (see latest_date.py for exactly when
    # it applies). The rewritten SQL must itself pass validation, otherwise the
    # model's own SQL is kept unchanged.
    if period is not None:
        sql = _pin_period(sql, tables, columns, period, validate_sql)
    else:
        try:
            from backend.sql_agent.latest_date import apply_latest_date_default, query_implies_period
            _names_period = _has_time_context(q) or query_implies_period(q)
            _latest_sql, _latest_changed = apply_latest_date_default(sql, tables, _names_period)
            if _latest_changed:
                _latest_ok, _latest_why = validate_sql(_latest_sql, tables, columns)
                if _latest_ok:
                    sql = _latest_sql
                    logger.info("[SQL_AGENT] sql (latest-period default applied)=\n%s", sql)
                else:
                    logger.warning(
                        "[SQL_AGENT] latest-period default rejected by validation (%s); keeping model SQL",
                        _latest_why,
                    )
        except Exception as exc:
            logger.warning("[SQL_AGENT] latest-period default skipped: %s", exc)

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

    used = [t["table"] for t in tables if re.search(rf"\b{re.escape(t['table'])}\b", sql, re.IGNORECASE)]

    # -- Step 4.5: nothing found -> try the line-item label spelled differently --
    # The same label is often written differently across reporting dates
    # ("(iii)Term Loans" / "Term Loans"). See label_match.py: it asks the user when
    # several different labels fit, otherwise retries once with the labels that
    # really exist. Never runs when rows came back.
    label_note = None
    if not rows and len(used) == 1:
        try:
            from backend.sql_agent.label_match import plan_label_fix
            from sqlcore.sql_generator import _load_table_entries
            entries = _load_table_entries(used)
            entry = entries.get(used[0]) or entries.get(used[0].lower()) or {}
            fix = await asyncio.to_thread(plan_label_fix, sql, used[0], entry, execute_query)
            if fix and fix.ask:
                return _build_result(
                    response_text=(
                        "I found more than one line item that fits your question:\n"
                        + "\n".join(f"• {label}" for label in fix.labels)
                        + "\nWhich one do you mean? Please repeat the question with the exact line item, "
                          "and mention the return name or table if you can."
                    ),
                    result_type="db_result",
                    needs_more_info=True,
                    more_info_hint="Mention the exact line item, and the return name or table.",
                    accuracy_hint=accuracy_hint,
                )
            if fix and fix.sql:
                ok, why = validate_sql(fix.sql, tables, columns)
                if ok:
                    c2, r2, e2 = await asyncio.to_thread(execute_query, fix.sql)
                    if not e2 and r2:
                        logger.info("[SQL_AGENT] label match applied labels=%s sql=\n%s", fix.labels, fix.sql)
                        sql, col_names, rows = fix.sql, c2, r2
                        label_note = "Matched the line item as: " + "; ".join(sorted({v.strip() for v in fix.labels})) + "."
                else:
                    logger.warning("[SQL_AGENT] label-match SQL rejected by validation: %s", why)
        except Exception as exc:  # noqa: BLE001 -- the retry must never break the normal answer
            logger.warning("[SQL_AGENT] label match skipped: %s", exc)

    result = await _finish(
        q=q, sql=sql, col_names=col_names, rows=rows,
        tables_used=used or [t["table"] for t in tables],
        period=period, session_id=session_id, base_hint=accuracy_hint,
    )
    if label_note:
        result["accuracy_hint"] = (result.get("accuracy_hint") + " " if result.get("accuracy_hint") else "") + label_note
    return result
