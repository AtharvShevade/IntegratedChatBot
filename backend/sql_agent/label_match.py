# backend/sql_agent/label_match.py
#
# Loose line-item label matching, used only when a generated query finds NOTHING.
#
# Why: the same line item is often spelled differently from one reporting date to
# the next ("(iii)Term Loans", "(iii) Term Loans ", "Term Loans"), but the model
# writes an exact comparison:  DESCRIPTION = 'Term Loans'  and gets 0 rows.
#
# What this does (generic, no table or label is special-cased):
#   1. Find one `<text label column> = '<literal>'` filter in a single-table query.
#   2. Look up the labels that really exist in that table containing the text.
#   3. Compare them ignoring case, spaces and a leading numbering prefix
#      ("(iii)", "1.", "a)").
#        * the same label spelled differently  -> use all of those spellings
#        * exactly one other label contains it -> best guess, use it
#        * several different labels            -> do NOT guess: ask the user
#   4. Rewrite the filter to the exact labels found (IN (...)) and take the latest
#      reporting date among those rows, so the result is the latest figure that
#      really exists for that line item.
#
# It never runs when the query already returned rows, never touches codes / dates
# / numbers, and returns None (leave the result alone) on anything it is unsure of.

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

__all__ = ["LabelFix", "normalize_label", "plan_label_fix"]

_MAX_CANDIDATES = 50
_LABEL_COLUMN_NAME = re.compile(r"(desc|label|name|particular|item|head)", re.IGNORECASE)
_NOT_A_LABEL = re.compile(r"(code|^id$|_id$|rdate|date)", re.IGNORECASE)
# `<col> = '<text>'`, not part of a longer identifier, not already a function call.
_EQ_FILTER = re.compile(r"(?<![\w.])([A-Za-z_][\w$#]*)\s*=\s*'((?:[^']|'')*)'")
_MAX_RDATE = re.compile(r"\(\s*SELECT\s+MAX\s*\(\s*RDATE\s*\)\s+FROM\s+(\w+)\s*\)", re.IGNORECASE)
_SAFE_TEXT = re.compile(r"[^A-Za-z0-9 &()/.,'\-]")
_LEADING_NUMBER = re.compile(r"^\s*(\(\s*[ivxlc]+\s*\)|\(\s*[a-z0-9]{1,3}\s*\)|[ivxlc]+\.|[a-z0-9]{1,3}[.)])\s*", re.IGNORECASE)


@dataclass
class LabelFix:
    sql: str | None = None                  # rewritten SQL to run (None -> ask instead)
    labels: list[str] = field(default_factory=list)   # exact labels used / to choose from
    ask: bool = False                       # several different labels: ask the user
    column: str = ""


def normalize_label(text: str) -> str:
    """Case, spaces and a leading numbering prefix ignored."""
    s = (text or "").strip()
    s = _LEADING_NUMBER.sub("", s)
    s = re.sub(r"[^\w]+", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def _q(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def _single_table(sql: str, table: str) -> bool:
    names = {m.lower() for m in re.findall(r"\b(?:FROM|JOIN)\s+([A-Za-z_][\w$#]*)", sql, re.IGNORECASE)}
    return names == {table.lower()}


def _label_columns(table_entry: dict) -> set[str]:
    out: set[str] = set()
    for col in table_entry.get("columns") or []:
        name = str(col.get("name") or "")
        if not name or str(col.get("type") or "").lower().split("(")[0] not in ("varchar2", "varchar", "nvarchar2", "char"):
            continue
        if _NOT_A_LABEL.search(name):
            continue
        if _LABEL_COLUMN_NAME.search(name) or "label" in str(col.get("description") or "").lower():
            out.add(name.lower())
    return out


def plan_label_fix(sql: str, table: str, table_entry: dict, execute_query) -> LabelFix | None:
    """None when this is not a label-spelling problem (leave the empty result alone)."""
    if not sql or not table or not _single_table(sql, table):
        return None
    label_cols = _label_columns(table_entry)
    filters = [m for m in _EQ_FILTER.finditer(sql) if m.group(1).lower() in label_cols]
    if len(filters) != 1:
        return None
    match = filters[0]
    column, literal = match.group(1), match.group(2).replace("''", "'")
    wanted = normalize_label(literal)
    if not wanted:
        return None

    probe_text = _SAFE_TEXT.sub("", literal).strip()
    if not probe_text:
        return None
    probe = (
        f"SELECT DISTINCT {column} FROM {table} WHERE UPPER({column}) LIKE "
        f"{_q('%' + probe_text.upper() + '%')} FETCH FIRST {_MAX_CANDIDATES} ROWS ONLY"
    )
    try:
        _cols, rows, err = execute_query(probe)
    except Exception as exc:  # noqa: BLE001
        logger.info("[SQL_AGENT] label probe failed: %s", exc)
        return None
    if err or not rows:
        return None
    found = [str(r[0]) for r in rows if r and r[0] is not None]

    groups: dict[str, list[str]] = {}
    for label in found:
        groups.setdefault(normalize_label(label), []).append(label)

    if wanted in groups:                       # same label, different spelling
        chosen = groups[wanted]
    elif len(groups) == 1:                     # one other label contains the text: best guess
        chosen = next(iter(groups.values()))
    else:                                      # several different labels: never guess
        return LabelFix(ask=True, labels=sorted({v[0].strip() for v in groups.values()}), column=column)

    in_list = "(" + ", ".join(_q(v) for v in chosen) + ")"
    new_sql = sql[:match.start()] + f"{column} IN {in_list}" + sql[match.end():]
    # Latest date among the rows that really exist for this line item.
    new_sql = _MAX_RDATE.sub(
        lambda m: f"(SELECT MAX(RDATE) FROM {m.group(1)} WHERE {column} IN {in_list})", new_sql,
    )
    return LabelFix(sql=new_sql, labels=chosen, column=column)
