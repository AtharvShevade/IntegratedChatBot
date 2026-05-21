import re
import logging

from fastapi import APIRouter, HTTPException

from api.schemas import QueryRequest, QueryResult
from api.utils import serialize_rows
from src.executor import execute_query
from src.retriever import get_relevant_schema
from src.sql_generator import generate_sql, validate_sql

log = logging.getLogger("query")

router = APIRouter(tags=["query"])

MIN_QUERY_LENGTH = 20

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


def _empty_result(query: str, hint: str) -> QueryResult:
    return QueryResult(
        query=query,
        matched_tables=[],
        matched_columns=[],
        sql="",
        is_valid=False,
        validation_reason=None,
        columns=[],
        rows=[],
        needs_more_info=True,
        more_info_hint=hint,
    )


@router.post("/query", response_model=QueryResult)
def run_text_query(body: QueryRequest):
    q = body.query.strip()

    # Guard 1 — minimum query length
    if len(q) < MIN_QUERY_LENGTH:
        return _empty_result(
            q,
            "Please provide more details about what data you need. "
            "Describe the report or metric you want, and include a time period "
            "(e.g. Q1 FY2024, March 2025, FY 2023-24, or a specific date).",
        )

    # Soft hint — no time duration detected; run query but suggest refinement
    _accuracy_hint = None
    if not _has_time_context(q):
        _accuracy_hint = (
            "Tip: For more accurate results, try specifying a time period — "
            "e.g. a specific date (01-Mar-2025), month (March 2025), "
            "quarter (Q1 FY2024), half-year (H1 2024), year (2024), "
            "or a date range (Jan–Jun 2025)."
        )

    # Step 1 — schema retrieval (L1: tables/columns  L2: row-label values)
    tables, columns, matched_labels = get_relevant_schema(q)
    log.info("TABLES  : %s", [t["table"] for t in tables])
    log.info("COLUMNS : %s", [f"{c['table']}.{c['column']}" for c in columns])

    if not tables:
        return QueryResult(
            query=q,
            matched_tables=[],
            matched_columns=[],
            sql="",
            is_valid=False,
            validation_reason="No matching tables found in the vector index.",
            columns=[],
            rows=[],
            accuracy_hint=_accuracy_hint,
        )

    # Step 2 — SQL generation
    try:
        result = generate_sql(q, tables, columns, dialect=body.dialect, matched_labels=matched_labels)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    sql = result.get("sql", "")
    log.info("SQL     :\n%s", sql)

    # Step 3 — validation
    is_valid, reason = validate_sql(sql, tables, columns)
    log.info("VALID   : %s  reason=%s", is_valid, reason)

    # Step 4 — execution (only if valid)
    col_names, rows, db_error = [], [], None
    if is_valid:
        col_names, rows, db_error = execute_query(sql)
        log.info("DB COLS : %s", col_names)
        log.info("DB ROWS : %d row(s) returned", len(rows))
        if db_error:
            log.error("DB ERR  : %s", db_error)

    return QueryResult(
        query=q,
        matched_tables=[t["table"] for t in tables],
        matched_columns=[f"{c['table']}.{c['column']}" for c in columns],
        sql=sql,
        is_valid=is_valid,
        validation_reason=reason if not is_valid else None,
        columns=col_names,
        rows=serialize_rows(rows),
        db_error=db_error,
        accuracy_hint=_accuracy_hint,
    )
