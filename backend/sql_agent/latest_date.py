# backend/sql_agent/latest_date.py
#
# Default-to-the-latest-period safeguard for generated SQL.
#
# The prompt already tells the model "if the question names no date, filter
# RDATE = (SELECT MAX(RDATE) FROM <table>)", but a small model can still ignore
# it and return every reporting period mixed together. This is the mechanical
# backstop, applied after generation and kept deliberately narrow:
#
#   * only when the user's question names no date / period at all, and does not
#     ask for a trend, history, comparison or any other multi-period answer;
#   * only when the generated SQL does not mention RDATE anywhere (so a query
#     the model already pinned, ranged or grouped by period is never touched);
#   * only the tables the agent selected for this question.
#
# Each table reference is replaced by an inline view of that table restricted to
# its latest RDATE, which works wherever the table appears (FROM, JOIN, a
# subquery) without having to edit WHERE / GROUP BY / ORDER BY by regex:
#
#     FROM QCB_F013_T t   ->   FROM (SELECT * FROM QCB_F013_T
#                                    WHERE RDATE = (SELECT MAX(RDATE) FROM QCB_F013_T)) t
#
# Anything ambiguous (comma joins, a selected table that cannot be rewritten
# safely) leaves the SQL exactly as the model wrote it.

from __future__ import annotations

import logging
import re
from datetime import date

logger = logging.getLogger(__name__)

__all__ = ["query_implies_period", "apply_latest_date_default"]

# Words that mean "more than one period" or name a time reference. Any of them
# means the user did NOT leave the period open, so the default must not apply.
_PERIOD_WORDS = re.compile(
    r"\b(trend|trends|over\s+time|history|historical|historically|time\s+series|"
    r"(each|every|per)\s+(day|week|month|quarter|year|period|date|reporting)|"
    r"(day|week|month|quarter|year|period|date)[\s-]?(wise|by[\s-](day|week|month|quarter|year|period))|"
    r"all\s+(the\s+)?(dates|periods|quarters|months|years|reporting)|"
    r"(last|past|previous|prior|next|recent|latest|first)\s+\d+|"
    r"since|between|from\s+.+\s+to\s+|compar\w*|versus|vs\.?|growth|"
    r"yoy|qoq|mom|ytd|mtd|qtd|"
    r"today|yesterday|tomorrow|tonight|now)\b",
    re.IGNORECASE,
)

# Reporting dates written as numbers: 31/03/2026, 2026-03-31, 31.03.26 ...
_NUMERIC_DATE = re.compile(r"\b\d{1,4}[/.\-]\d{1,2}[/.\-]\d{1,4}\b")

# Words that can follow a table name but are not an alias.
_NOT_AN_ALIAS = frozenset({
    "where", "join", "on", "group", "order", "having", "left", "right", "inner",
    "outer", "full", "cross", "natural", "fetch", "union", "intersect", "minus",
    "connect", "start", "using", "limit", "offset", "for", "with", "as",
    "select", "from", "and", "or", "not", "set", "when", "then", "else", "end",
})


def query_implies_period(query: str) -> bool:
    """True when the question already says which period(s) it wants, or asks
    for a multi-period answer, so no default period should be added.

    Deliberately wide: the cost of a false positive is only that the model's own
    SQL runs unchanged (today's behaviour); a false negative would collapse a
    trend question to a single date."""
    q = (query or "").strip()
    if not q:
        return True
    if _PERIOD_WORDS.search(q) or _NUMERIC_DATE.search(q):
        return True
    # Explicit dates / months / years / quarters / FY - one shared definition
    # with the adapter's own "no time context" hint.
    try:
        from backend.sql_agent.query_handler import _has_time_context
        if _has_time_context(q):
            return True
    except Exception:  # pragma: no cover
        pass
    # The agent's own relative-expression resolver ("last quarter", "FY24 Q2").
    try:
        from sqlcore.sql_generator import _resolve_relative_time
        if _resolve_relative_time(q, date.today()):
            return True
    except Exception:  # pragma: no cover - the resolver is optional here
        pass
    return False


def _table_names(tables) -> list[str]:
    names: list[str] = []
    for t in tables or []:
        name = (t.get("table") if isinstance(t, dict) else t) or ""
        name = str(name).strip()
        if name and re.fullmatch(r"[A-Za-z_][\w$#]*", name) and name not in names:
            names.append(name)
    # longest first so a name that is a prefix of another cannot shadow it
    return sorted(names, key=len, reverse=True)


def apply_latest_date_default(sql: str, tables, query_names_period: bool) -> tuple[str, bool]:
    """Return ``(sql, changed)``: *sql* with every selected-table reference
    limited to that table's latest RDATE, or the original SQL untouched when
    the safeguard does not apply."""
    if not sql or query_names_period:
        return sql, False
    # The model already dealt with the period in some way: leave it alone.
    if re.search(r"\brdate\b", sql, re.IGNORECASE):
        return sql, False
    names = _table_names(tables)
    if not names:
        return sql, False

    alt = "|".join(re.escape(n) for n in names)
    ref = re.compile(
        rf"\b(?P<kw>from|join)(?P<sp>\s+)(?P<q>\"?)(?P<name>{alt})(?P=q)(?![\w$#.])",
        re.IGNORECASE,
    )
    if not ref.search(sql):
        return sql, False

    # A comma join ("FROM a, b") cannot be rewritten reference by reference.
    if re.search(rf"\bfrom\s+\"?(?:{alt})\"?(?:\s+(?:as\s+)?[A-Za-z_]\w*)?\s*,", sql, re.IGNORECASE):
        return sql, False
    if re.search(rf",\s*\"?(?:{alt})\"?(?![\w$#.(])", sql, re.IGNORECASE):
        # a bare ", TABLE" that is not a column list element is a comma join;
        # a column list never contains an unqualified selected-table name
        return sql, False

    count = 0

    def _wrap(m: re.Match) -> str:
        nonlocal count
        name = m.group("name")
        tail = sql[m.end():]
        alias_m = re.match(r"\s+(?:as\s+)?([A-Za-z_][\w$#]*)", tail, re.IGNORECASE)
        has_alias = bool(alias_m) and alias_m.group(1).lower() not in _NOT_AN_ALIAS
        count += 1
        inline = f"(SELECT * FROM {name} WHERE RDATE = (SELECT MAX(RDATE) FROM {name}))"
        # Without an alias the view takes the table's own name, so qualified
        # references (TABLE.COLUMN) elsewhere in the query keep working.
        return f"{m.group('kw')}{m.group('sp')}{inline}" + ("" if has_alias else f" {name}")

    new_sql = ref.sub(_wrap, sql)
    if count == 0 or new_sql == sql:
        return sql, False
    logger.info(
        "[SQL_AGENT] no period named in the question -> latest RDATE default applied "
        "to %d table reference(s)", count,
    )
    return new_sql, True
