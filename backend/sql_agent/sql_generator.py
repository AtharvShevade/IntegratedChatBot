import re
import json
import difflib
import calendar
import requests
from collections import defaultdict
from datetime import date, timedelta
from backend.sql_agent.config import OLLAMA_MODEL, OLLAMA_URL, SCHEMA_JSON_PATH

BANNED_KEYWORDS = ["delete", "update", "drop", "insert", "truncate", "alter", "create", "exec"]

# Oracle built-in pseudo-tables that are always valid
ORACLE_PSEUDO_TABLES = frozenset({"dual"})

# Oracle date/time format tokens and built-in function names that must not be
# treated as column names during SQL validation.
_ORACLE_FORMAT_TOKENS = frozenset({
    'yyyy', 'yy', 'mm', 'dd', 'hh', 'hh24', 'mi', 'ss', 'mon', 'dy', 'ddd',
    'am', 'pm', 'ff', 'tz', 'ww', 'iw', 'sssss', 'j', 'rr', 'rrrr',
})
_ORACLE_BUILTIN_TOKENS = frozenset({
    'add_months', 'months_between', 'trunc', 'sysdate', 'systimestamp',
    'decode', 'instr', 'substr', 'substrb', 'length', 'round', 'floor', 'ceil',
    'greatest', 'least', 'nvl2', 'lpad', 'rpad', 'replace', 'regexp_like',
    'regexp_substr', 'listagg', 'level', 'rowid', 'prior', 'connect_by_root',
    'extract', 'to_number', 'numtoyminterval', 'numtodsinterval',
})

# Module-level caches — loaded once per process restart
_schema_cache: list | None = None
_samples_cache: dict | None = None


def _get_schema(schema_path=None) -> list:
    """Return schema.json contents, loading from disk only once."""
    global _schema_cache
    if _schema_cache is None:
        p = schema_path or SCHEMA_JSON_PATH
        with open(p) as f:
            _schema_cache = json.load(f)
    return _schema_cache


def _get_samples() -> dict:
    """Return description_samples.json contents, loading from disk only once."""
    global _samples_cache
    if _samples_cache is None:
        from backend.sql_agent.description_fetcher import load_samples
        _samples_cache = load_samples()
    return _samples_cache


def _fix_unbalanced_parens(sql: str) -> str:
    """
    Remove unmatched closing ')' from LLM-generated SQL.
    Tracks depth while ignoring parentheses inside string literals.
    Example: SELECT (...) + (...) ) ) AS X FROM DUAL  →  SELECT (...) + (...) AS X FROM DUAL
    """
    depth = 0
    in_str = False
    unmatched: list[int] = []

    for i, ch in enumerate(sql):
        if ch == "'" :
            in_str = not in_str
        elif not in_str:
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
                if depth < 0:
                    unmatched.append(i)
                    depth = 0   # keep scanning for more unmatched closes

    if not unmatched:
        return sql

    chars = list(sql)
    for idx in reversed(unmatched):
        chars[idx] = ''
    return ''.join(chars).strip()


def _string_literal_spans(s: str) -> list:
    """Return [(start, end), ...] character ranges that fall inside '...' literals."""
    spans, start = [], None
    for i, ch in enumerate(s):
        if ch == "'":
            if start is None:
                start = i
            else:
                spans.append((start, i))
                start = None
    return spans


def _preceding_word(s: str, pos: int) -> str:
    """The lowercase word immediately before position *pos* in *s*, if any."""
    m = re.search(r'([a-zA-Z_]+)\s*$', s[:pos].rstrip())
    return m.group(1).lower() if m else ''


_AGG_FUNC_NAMES = ('sum', 'avg', 'min', 'max', 'count', 'stddev', 'variance')


def _split_top_level(s: str, sep: str = ',') -> list:
    """Split *s* on *sep* only at paren-depth 0 and outside string literals."""
    parts, depth, in_str, current = [], 0, False, []
    for ch in s:
        if ch == "'":
            in_str = not in_str
            current.append(ch)
        elif not in_str and ch == '(':
            depth += 1
            current.append(ch)
        elif not in_str and ch == ')':
            depth -= 1
            current.append(ch)
        elif not in_str and depth == 0 and ch == sep:
            parts.append(''.join(current))
            current = []
        else:
            current.append(ch)
    parts.append(''.join(current))
    return parts


def _find_top_level_from_pos(q: str) -> int:
    """Position of the outer (depth-0) FROM keyword, or -1 if none."""
    depth, in_str = 0, False
    for i, ch in enumerate(q):
        if ch == "'":
            in_str = not in_str
        elif not in_str:
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
            elif depth == 0 and q[i:i + 4] == 'from':
                before = q[i - 1] if i > 0 else ' '
                after  = q[i + 4] if i + 4 < len(q) else ' '
                if not (before.isalnum() or before == '_') and not (after.isalnum() or after == '_'):
                    return i
    return -1


_AGG_ITEM_RE = re.compile(
    rf'^(\s*)({"|".join(_AGG_FUNC_NAMES)})\s*\(\s*(.*?)\s*\)((?:\s+as\s+[a-zA-Z_][a-zA-Z0-9_]*)?\s*)$',
    re.IGNORECASE | re.DOTALL,
)


def _select_list_items(sql: str):
    """Return (select_prefix_end, items) for the outer SELECT list, or None."""
    q_lower = sql.lower()
    from_pos = _find_top_level_from_pos(q_lower)
    if from_pos == -1:
        return None
    select_clause = sql[:from_pos]
    m = re.match(r'^\s*select\s+(distinct\s+)?', select_clause, re.IGNORECASE)
    if not m:
        return None
    items = _split_top_level(select_clause[m.end():], ',')
    return m.end(), items


def _has_mixed_aggregation(sql: str) -> bool:
    """True if the SELECT list mixes an aggregate call with a plain column
    and there's no GROUP BY — the exact shape that raises Oracle ORA-00937."""
    if re.search(r'\bgroup\s+by\b', sql, re.IGNORECASE):
        return False
    parsed = _select_list_items(sql)
    if not parsed:
        return False
    _, items = parsed
    has_agg = has_plain = False
    for item in items:
        stripped = item.strip()
        if not stripped:
            continue
        if _AGG_ITEM_RE.match(stripped):
            has_agg = True
        elif stripped != '*' and not stripped.isdigit():
            has_plain = True
    return has_agg and has_plain


def _autofix_mixed_aggregation(sql: str) -> str:
    """
    Deterministically resolve ORA-00937 (mixing an aggregate function with a
    plain column in the same SELECT, no GROUP BY) by unwrapping the
    aggregate call(s) rather than waiting on an LLM retry.

    Safe because by the time this fires, the vertical-format guard has
    already required any aggregated vertical-table column to be filtered to
    a single label row — SUM()/AVG() over that one row and the bare value
    are equivalent, so dropping the wrapper changes nothing except making
    the syntax valid.
    """
    if not sql or not _has_mixed_aggregation(sql):
        return sql

    q_lower = sql.lower()
    from_pos = _find_top_level_from_pos(q_lower)
    prefix_end, items = _select_list_items(sql)

    new_items = []
    for item in items:
        stripped = item.strip()
        m = _AGG_ITEM_RE.match(stripped)
        if m:
            lead_ws, _fn, inner, alias_part = m.groups()
            new_items.append(f"{lead_ws}{inner}{alias_part}")
        else:
            new_items.append(item)

    # .strip() above drops the whitespace that used to separate the last
    # item from the FROM keyword — re-add a single space so "...GROSS_ADV"
    # and "FROM" don't get concatenated into "...GROSS_ADVFROM".
    new_select_clause = (sql[:prefix_end] + ','.join(new_items)).rstrip() + ' '
    return new_select_clause + sql[from_pos:]


def _autocorrect_columns(sql: str, tables: list) -> str:
    """
    Ground the LLM's output against the REAL table/column names in
    schema.json instead of only rejecting bad ones after the fact. Catches
    near-miss hallucinations — typos, singular/plural drift, a garbled
    repeat of a table name in a subquery — and snaps them to the actual
    name deterministically.

    Deliberately conservative (cutoff=0.75): this is a safety net for close
    misses, not a fix for a wholesale fabricated name unrelated to anything
    real — those still fail validate_sql and trigger a retry, which is the
    correct outcome (the query needs a different answer, not a guess).
    """
    if not sql:
        return sql

    valid_table_names = {t["table"].lower() for t in tables}
    q_lower = sql.lower()
    q_for_tables = re.sub(r'\bextract\s*\([^)]*\)', '', q_lower)
    q_for_tables = re.sub(r'\btrim\s*\([^)]*\)', '', q_for_tables)
    referenced_tables = set(re.findall(r'(?:from|join)\s+([a-z_][a-z0-9_]*)', q_for_tables))
    used_table_names = referenced_tables & valid_table_names
    if not used_table_names:
        return sql

    all_columns     = _load_all_columns(used_table_names)
    valid_col_names = {c["column"].lower() for c in all_columns}

    literal_spans = _string_literal_spans(sql)

    def _in_literal(pos: int) -> bool:
        return any(s <= pos < e for s, e in literal_spans)

    corrected, offset = sql, 0
    for m in re.finditer(r'\b[a-zA-Z_][a-zA-Z0-9_]{2,}\b', sql):
        tok_l = m.group(0).lower()
        if (
            tok_l in valid_col_names
            or tok_l in valid_table_names
            or tok_l in _SQL_KEYWORDS
            or tok_l in _ORACLE_FORMAT_TOKENS
            or tok_l in _ORACLE_BUILTIN_TOKENS
            or _in_literal(m.start())
        ):
            continue

        # A token right after FROM/JOIN is a table reference — match it
        # against the table(s) already confirmed correct elsewhere in this
        # same query first (the most confident guess: the model likely
        # meant "the table it already used"), falling back to the full
        # candidate pool. Anything else is a column reference.
        if _preceding_word(sql, m.start()) in ('from', 'join'):
            pool = used_table_names or valid_table_names
        else:
            pool = valid_col_names
        if not pool:
            continue

        match = difflib.get_close_matches(tok_l, pool, n=1, cutoff=0.75)
        if not match:
            continue

        start, end   = m.start() + offset, m.end() + offset
        replacement  = match[0].upper()
        corrected    = corrected[:start] + replacement + corrected[end:]
        offset      += len(replacement) - (end - start)

    return corrected


def _resolve_relative_time(query: str, today: date) -> str | None:
    """
    Detect relative time expressions in the user query and resolve them to
    concrete calendar date ranges.  The returned block is injected into the
    SQL prompt so the LLM never has to guess what 'last quarter' means.
    """
    q = query.lower()
    lines = []

    def fmt(d): return d.strftime("%Y-%m-%d")
    def month_end(y, m): return date(y, m, calendar.monthrange(y, m)[1])

    if re.search(r'\b(this|current)\s+week\b', q):
        mon = today - timedelta(days=today.weekday())
        sun = mon + timedelta(days=6)
        lines.append(f"'this week'  = {fmt(mon)} to {fmt(sun)}")

    if re.search(r'\b(last|previous)\s+week\b', q):
        mon = today - timedelta(days=today.weekday() + 7)
        sun = mon + timedelta(days=6)
        lines.append(f"'last week'  = {fmt(mon)} to {fmt(sun)}")

    if re.search(r'\b(this|current)\s+month\b', q):
        start = today.replace(day=1)
        end   = month_end(today.year, today.month)
        lines.append(f"'this month' = {today.strftime('%B %Y')}  ({fmt(start)} to {fmt(end)})")

    if re.search(r'\b(last|previous)\s+month\b', q):
        end   = today.replace(day=1) - timedelta(days=1)
        start = end.replace(day=1)
        lines.append(f"'last month' = {end.strftime('%B %Y')}  ({fmt(start)} to {fmt(end)})")

    if re.search(r'\b(this|current)\s+year\b', q):
        lines.append(f"'this year'  = {today.year}  (01-JAN-{today.year} to 31-DEC-{today.year})")

    if re.search(r'\b(last|previous)\s+year\b', q):
        y = today.year - 1
        lines.append(f"'last year'  = {y}  (01-JAN-{y} to 31-DEC-{y})")

    _CQ_START = {1: (1, 1),  2: (4, 1),  3: (7, 1),  4: (10, 1)}
    _CQ_END   = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}
    cur_cq    = (today.month - 1) // 3 + 1

    if re.search(r'\b(this|current)\s+quarter\b', q):
        s = date(today.year, *_CQ_START[cur_cq])
        e = date(today.year, *_CQ_END[cur_cq])
        lines.append(f"'this quarter' = Q{cur_cq} {today.year} (calendar)  ({fmt(s)} to {fmt(e)})")

    if re.search(r'\b(last|previous)\s+quarter\b', q):
        prev_cq      = cur_cq - 1 if cur_cq > 1 else 4
        prev_cq_year = today.year if cur_cq > 1 else today.year - 1
        s = date(prev_cq_year, *_CQ_START[prev_cq])
        e = date(prev_cq_year, *_CQ_END[prev_cq])
        lines.append(f"'last quarter' = Q{prev_cq} {prev_cq_year} (calendar)  ({fmt(s)} to {fmt(e)})")

    fy_sy = today.year if today.month >= 4 else today.year - 1
    _FYQ  = {
        1: {"months": {4, 5, 6},    "start": (4, 1),  "end": (6, 30),  "offset": 0},
        2: {"months": {7, 8, 9},    "start": (7, 1),  "end": (9, 30),  "offset": 0},
        3: {"months": {10, 11, 12}, "start": (10, 1), "end": (12, 31), "offset": 0},
        4: {"months": {1, 2, 3},    "start": (1, 1),  "end": (3, 31),  "offset": 1},
    }
    cur_fyq = next(fq for fq, v in _FYQ.items() if today.month in v["months"])

    if re.search(r'\b(this|current)\s+(fy|financial|fiscal)\s*(quarter|q)\b', q):
        off = _FYQ[cur_fyq]["offset"]
        s   = date(fy_sy + off, *_FYQ[cur_fyq]["start"])
        e   = date(fy_sy + off, *_FYQ[cur_fyq]["end"])
        lines.append(f"'this FY quarter' = Q{cur_fyq} FY{fy_sy+1}  ({fmt(s)} to {fmt(e)})")

    if re.search(r'\b(last|previous)\s+(fy|financial|fiscal)\s*(quarter|q)\b', q):
        prev_fyq    = cur_fyq - 1 if cur_fyq > 1 else 4
        prev_fy_sy  = fy_sy if cur_fyq > 1 else fy_sy - 1
        off         = _FYQ[prev_fyq]["offset"]
        s = date(prev_fy_sy + off, *_FYQ[prev_fyq]["start"])
        e = date(prev_fy_sy + off, *_FYQ[prev_fyq]["end"])
        lines.append(f"'last FY quarter' = Q{prev_fyq} FY{prev_fy_sy+1}  ({fmt(s)} to {fmt(e)})")

    if re.search(r'\b(this|current)\s+(financial year|fiscal year|fy)\b', q):
        lines.append(
            f"'this financial year' = FY{fy_sy+1}  "
            f"(01-APR-{fy_sy} to 31-MAR-{fy_sy+1})"
        )

    if re.search(r'\b(last|previous)\s+(financial year|fiscal year|fy)\b', q):
        lines.append(
            f"'last financial year' = FY{fy_sy}  "
            f"(01-APR-{fy_sy-1} to 31-MAR-{fy_sy})"
        )

    # Explicit "Q<n> FY<yyyy>" or "FY<yyyy> Q<n>" patterns
    # e.g. "Q1 FY2024", "FY2024 Q2", "Q3 FY24", "q1 fy2024"
    _FY_QTR_MONTHS = {
        1: (4,  6,  "APR", "JUN"),
        2: (7,  9,  "JUL", "SEP"),
        3: (10, 12, "OCT", "DEC"),
        4: (1,  3,  "JAN", "MAR"),
    }
    _fy_qtr_pat = re.compile(
        r'\bq([1-4])\s*fy(\d{2,4})\b|\bfy(\d{2,4})\s*q([1-4])\b', re.IGNORECASE
    )
    for m in _fy_qtr_pat.finditer(q):
        qnum = int(m.group(1) or m.group(4))
        raw_yr = m.group(2) or m.group(3)
        yr = int(raw_yr) if len(raw_yr) == 4 else 2000 + int(raw_yr)
        # yr is the END year of the FY (e.g. FY2024 ends Mar 2024, starts Apr 2023)
        fy_start_yr = yr - 1
        mm_s, mm_e, mon_s, mon_e = _FY_QTR_MONTHS[qnum]
        # Q4 spans Jan-Mar of the end year; Q1-Q3 span Apr-Dec of start year
        actual_yr_s = fy_start_yr if qnum <= 3 else yr
        actual_yr_e = fy_start_yr if qnum <= 3 else yr
        s = f"01-{mon_s}-{actual_yr_s}"
        e_day = 30 if mon_e in ("JUN", "SEP", "NOV", "APR") else (28 if mon_e == "FEB" else 31)
        e = f"{e_day:02d}-{mon_e}-{actual_yr_e}"
        lines.append(
            f"'Q{qnum} FY{yr}' = {fmt(date(actual_yr_s, mm_s, 1))} to "
            f"{fmt(date(actual_yr_e, mm_e, calendar.monthrange(actual_yr_e, mm_e)[1]))}"
            f"  → use RDATE BETWEEN TO_DATE('{s}','DD-MON-YYYY') AND "
            f"TO_DATE('{e}','DD-MON-YYYY')"
        )

    # Explicit "Month YYYY" pattern: e.g. "March 2025", "December 2024", "Jan 2026"
    _MONTH_NUM = {
        'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5,
        'june': 6, 'july': 7, 'august': 8, 'september': 9, 'october': 10,
        'november': 11, 'december': 12,
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
        'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9,
        'oct': 10, 'nov': 11, 'dec': 12,
    }
    _mon_yr_pat = re.compile(
        r'\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|'
        r'jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)'
        r'\s+(\d{4})\b', re.IGNORECASE,
    )
    for m in _mon_yr_pat.finditer(q):
        mon_key = m.group(1).lower()
        mon_num = _MONTH_NUM.get(mon_key, _MONTH_NUM.get(mon_key[:3], 0))
        if not mon_num:
            continue
        yr       = int(m.group(2))
        last_day = calendar.monthrange(yr, mon_num)[1]
        mon_abbr = date(yr, mon_num, 1).strftime('%b').upper()
        lines.append(
            f"'{m.group(1).title()} {yr}' = {fmt(date(yr, mon_num, 1))} to "
            f"{fmt(date(yr, mon_num, last_day))}"
            f"  \u2192 use RDATE BETWEEN TO_DATE('01-{mon_abbr}-{yr}','DD-MON-YYYY') AND "
            f"TO_DATE('{last_day:02d}-{mon_abbr}-{yr}','DD-MON-YYYY')"
        )

    if not lines:
        return None

    block = (
        "════════════════════════════════════════════════\n"
        "RESOLVED TIME CONTEXT\n"
        "(these are the EXACT date ranges for the relative terms the user wrote)\n"
        "════════════════════════════════════════════════\n"
    )
    block += "\n".join(f"  {l}" for l in lines)
    block += "\n"
    return block


_SQL_KEYWORDS = {
    "select", "from", "where", "and", "or", "not", "in", "is", "null",
    "as", "on", "join", "inner", "outer", "left", "right", "full", "cross",
    "group", "by", "order", "having", "distinct", "between", "like", "case",
    "when", "then", "else", "end", "union", "all", "exists", "limit", "offset",
    "count", "sum", "avg", "min", "max", "coalesce", "nvl", "trim", "upper",
    "lower", "to_date", "to_char", "rownum", "dual", "with", "asc", "desc",
    "over", "partition", "rows", "range", "unbounded", "preceding",
    "following", "current", "row", "window", "rank", "dense_rank",
    "row_number", "ntile", "lag", "lead", "first_value", "last_value",
}


def _load_all_columns(table_names, schema_path=None):
    """Return all columns for the given table names using cached schema."""
    schema = _get_schema(schema_path)
    result = []
    for entry in schema:
        if entry["table"] in table_names:
            for col in entry["columns"]:
                result.append({
                    "table":       entry["table"],
                    "column":      col["name"],
                    "description": col.get("description", ""),
                    "return_name": col.get("return_name", ""),
                })
    return result


_TOTAL_ROW_KEYWORDS = [
    "total", "grand total", "sub-total", "subtotal",
    "all industries", "c. total", "c total", "grand-total",
    "i. gross", "iii. non-food", "ii. food",
]


def _find_total_row(values: list) -> str | None:
    for v in values:
        vl = v.lower()
        if any(kw in vl for kw in _TOTAL_ROW_KEYWORDS):
            return v
    return None


def _find_dom_ove_sibling(col_name: str, other_cols_upper: set) -> str | None:
    """
    Return the domestic/overseas counterpart of col_name if one exists among
    other_cols_upper. The schema isn't consistent about this: RAQ-style
    tables suffix it (EXPOSURE_DOM / EXPOSURE_OVE), while ALE-style tables
    prefix it AND abbreviate "overseas" differently (DOM_AMT_TOT /
    OVR_AMT_TOT — "OVR", not "OVE"). Both conventions are checked.
    """
    cu = col_name.upper()
    if cu.endswith("_DOM"):
        cand = cu[:-4] + "_OVE"
        if cand in other_cols_upper:
            return cand
    if cu.endswith("_OVE"):
        cand = cu[:-4] + "_DOM"
        if cand in other_cols_upper:
            return cand
    if cu.startswith("DOM_"):
        rest = cu[4:]
        for ove_prefix in ("OVR_", "OVE_"):
            cand = ove_prefix + rest
            if cand in other_cols_upper:
                return cand
    if cu.startswith("OVR_") or cu.startswith("OVE_"):
        rest = cu.split("_", 1)[1]
        cand = "DOM_" + rest
        if cand in other_cols_upper:
            return cand
    return None


def _autofix_vertical_total(sql: str, tables: list) -> str:
    """
    Deterministically rewrite the single most common vertical-format
    mistake instead of relying on the LLM to self-correct it on retry:
    SUM()/AVG() over a vertical table's metric column with no label-column
    filter at all, when the "total/overall" question intent is unambiguous
    because the table has exactly one label column and a known TOTAL row.

    Retries against this exact model have shown it can repeat this mistake
    across multiple attempts even after being told the specific fix — this
    makes the fix happen in code on the first attempt instead of gambling
    on a 3rd/4th retry. Deliberately narrow in scope (single table, single
    label column, no pre-existing label filter) so it never overrides a
    filter the model already wrote, which could be an intentional and
    correct choice we shouldn't second-guess.
    """
    if not sql:
        return sql

    valid_table_names = {t["table"].lower() for t in tables}
    q_lower = sql.lower()
    referenced_tables = set(re.findall(r'(?:from|join)\s+([a-z_][a-z0-9_]*)', q_lower))
    used_table_names = referenced_tables & valid_table_names
    if len(used_table_names) != 1:
        return sql
    tbl = next(iter(used_table_names))

    samples = _get_samples()
    label_cols = samples.get(tbl, {})
    if len(label_cols) != 1:
        return sql
    label_col, values = next(iter(label_cols.items()))

    total_row = _find_total_row(values)
    if not total_row:
        return sql

    # Bail if the label column is already referenced anywhere — never
    # override a filter the model already chose to write.
    if re.search(rf'\b{re.escape(label_col)}\b', q_lower):
        return sql

    agg_match = re.search(
        rf'\b(sum|avg)\s*\(\s*((?:[a-zA-Z_][a-zA-Z0-9_]*\.)?[a-zA-Z_][a-zA-Z0-9_]*)\s*\)',
        sql, re.IGNORECASE,
    )
    if not agg_match:
        return sql

    inner_col = agg_match.group(2)
    bare_col  = inner_col.split('.')[-1].lower()
    all_cols  = {c["column"].lower() for c in _load_all_columns({tbl})}
    if bare_col not in all_cols or bare_col == label_col:
        return sql

    alias_match = re.search(
        rf'\bfrom\s+{re.escape(tbl)}\s+(?:as\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\b',
        sql, re.IGNORECASE,
    )
    alias     = alias_match.group(1) if alias_match and alias_match.group(1).lower() not in _SQL_KEYWORDS else None
    label_ref = f"{alias}.{label_col.upper()}" if alias else label_col.upper()
    condition = f"{label_ref} = '{total_row}'"

    # 1) Unwrap SUM(...)/AVG(...) down to the plain column reference.
    new_sql = sql[:agg_match.start()] + inner_col + sql[agg_match.end():]

    # 2) Inject the total-row filter — into an existing WHERE, or add one
    # before any trailing GROUP BY/ORDER BY/FETCH clause, or at the end.
    where_match = re.search(r'\bwhere\b', new_sql, re.IGNORECASE)
    if where_match:
        insert_at = where_match.end()
        new_sql = new_sql[:insert_at] + f" {condition} AND" + new_sql[insert_at:]
    else:
        trailing_match = re.search(r'\b(group\s+by|order\s+by|fetch\s+first)\b', new_sql, re.IGNORECASE)
        if trailing_match:
            insert_at = trailing_match.start()
            new_sql = new_sql[:insert_at] + f"WHERE {condition} " + new_sql[insert_at:]
        else:
            new_sql = new_sql.rstrip() + f" WHERE {condition}"

    return new_sql


def build_prompt(user_query, tables, columns, dialect="Oracle", today_date=None,
                 matched_labels=None, previous_sql=None, previous_error=None):
    if today_date is None:
        today_date = date.today().isoformat()

    table_names = {t["table"] for t in tables}
    all_columns = _load_all_columns(table_names)

    # Adaptive cap on how many "known values" get shown per column. Wide
    # multi-table retrievals (e.g. 5 candidate tables at 22-30 columns each)
    # produce a much larger DDL block, and the local Ollama/proxy setup has
    # shown a hard ~120s gateway timeout — large prompts on wide tables
    # reliably exceed it and come back as a 502, something no retry can fix
    # since it's a proxy-side ceiling, not a flaky one-off. Shrinking the
    # per-column value preview keeps prompt size (and generation time) more
    # bounded for these cases while leaving small/typical queries untouched.
    # The TOTAL row itself is never affected — _find_total_row() always
    # scans the FULL value list regardless of this display cap.
    _total_candidate_cols = len(all_columns)
    if _total_candidate_cols <= 40:
        _known_values_cap = 15
    elif _total_candidate_cols <= 80:
        _known_values_cap = 8
    else:
        _known_values_cap = 5

    if matched_labels is None:
        raw_samples = _get_samples()
        matched_labels = []
        for tbl, col_map in raw_samples.items():
            for col, vals in col_map.items():
                for v in vals:
                    matched_labels.append({"table": tbl, "column": col, "value": v})

    label_map = defaultdict(lambda: defaultdict(list))
    for lbl in matched_labels:
        label_map[lbl["table"]][lbl["column"]].append(lbl["value"])

    from backend.sql_agent.description_fetcher import load_samples as _load_samples
    all_samples = _get_samples()
    for tbl in table_names:
        if tbl in all_samples:
            for col, vals in all_samples[tbl].items():
                existing = set(label_map[tbl][col])
                for v in vals:
                    if v not in existing:
                        label_map[tbl][col].append(v)

    # ── DDL-style schema block ───────────────────────────────────────────────
    # The active model (SQLCoder-7B, see config.py SQL_OLLAMA_MODEL) was
    # fine-tuned specifically on CREATE TABLE-style schema blocks paired with
    # a plain question — not on a long custom rule-book or abstract bracket
    # tags. Both of those are off-distribution for it and were likely working
    # against its own specialization rather than helping. This builds the
    # schema the way SQLCoder actually expects: real column names as DDL,
    # with per-column inline comments carrying the semantic hints (known row
    # values, the TOTAL row, domestic/overseas counterparts) that used to
    # live in separate rule blocks.
    from backend.sql_agent.description_fetcher import load_column_types
    real_column_types = load_column_types()

    def _guess_oracle_type(table: str, col_name: str, has_label_values: bool) -> str:
        # Prefer the REAL Oracle type when we have it (see column_types.json /
        # fetch_and_save_column_types()) — only fall back to guessing for a
        # table/column that hasn't been backfilled yet. Guessing "NUMBER" by
        # default for an unsampled column is what caused SUM(ASSETS) to be
        # generated against a text row-label column (ORA-01722) — real type
        # info removes the guess entirely wherever it's available.
        real_type = real_column_types.get(table, {}).get(col_name.lower())
        if real_type:
            dt = (real_type.get("data_type") or "").upper()
            if dt in ("VARCHAR2", "CHAR", "NVARCHAR2", "NCHAR"):
                length = real_type.get("data_length") or 400
                return f"VARCHAR2({length})"
            if dt == "DATE":
                return "DATE"
            if dt:
                return dt   # NUMBER, FLOAT, etc. — pass through as-is

        if col_name.upper() == "RDATE":
            return "DATE"
        if col_name.upper() == "CODE":
            return "VARCHAR2(20)"
        if has_label_values:
            return "VARCHAR2(400)"
        return "NUMBER"

    # Filter down to relevant columns for WIDE tables only — showing every
    # column of a 30-column table when the query only needs 2-3 of them is
    # pure wasted prefill on this CPU-bound Ollama host (measured ~42ms per
    # input token). `columns` is the retriever's own column-search ranking
    # (already scoped to these tables) — previously computed and passed in
    # but never actually used here. Small tables are left untouched (no
    # risk, no benefit); a table only gets trimmed if it's wide AND enough
    # relevant columns survive the filter, so we never risk hiding the one
    # column the query actually needs.
    _WIDE_TABLE_THRESHOLD = 15
    _MIN_FILTERED_COLUMNS = 4
    _relevant_cols_by_table = defaultdict(set)
    for c in columns:
        _relevant_cols_by_table[c["table"]].add(c["column"].upper())

    ddl_blocks = []
    has_vertical_table = False
    for t in tables:
        table_name = t["table"].upper()
        table_col_objs = [c for c in all_columns if c["table"] == t["table"]]
        col_labels = label_map.get(t["table"], {})

        omitted_count = 0
        if len(table_col_objs) > _WIDE_TABLE_THRESHOLD:
            always_keep = {"CODE", "RDATE"} | {col.upper() for col in col_labels}
            keep_names  = always_keep | _relevant_cols_by_table.get(t["table"], set())
            filtered    = [c for c in table_col_objs if c["column"].upper() in keep_names]
            if len(filtered) >= _MIN_FILTERED_COLUMNS:
                omitted_count  = len(table_col_objs) - len(filtered)
                table_col_objs = filtered

        col_names_upper = {c["column"].upper() for c in table_col_objs}

        col_lines = []
        for c in table_col_objs:
            col_name = c["column"].upper()
            values   = col_labels.get(c["column"])
            comment_parts = []

            # description is the actual per-column meaning (e.g. "Total Loan
            # Assets"); return_name is a generic report-category label that's
            # identical across every column in the table — nearly always
            # useless as a per-column comment, so it's only a last resort.
            desc = c.get("description") or c.get("return_name") or ""
            if desc:
                comment_parts.append(desc)

            if values:
                total_row = _find_total_row(values)
                shown_values = values[:_known_values_cap]
                if total_row and total_row not in shown_values:
                    # Guarantee the TOTAL row is visible in the preview text
                    # itself too, not just the separate "TOTAL row =" line —
                    # some tables have too many values for it to survive an
                    # aggressive cap otherwise.
                    shown_values = shown_values[:-1] + [total_row] if shown_values else [total_row]
                comment_parts.append("known values: " + ", ".join(f"'{v}'" for v in shown_values))
                if total_row:
                    comment_parts.append(f"TOTAL row = '{total_row}' — use this for overall/total figures")

            sibling = _find_dom_ove_sibling(col_name, col_names_upper)
            if sibling:
                side = "domestic" if (col_name.endswith("_DOM") or col_name.startswith("DOM_")) else "overseas"
                comment_parts.append(f"{side}-side value; counterpart = {sibling}")

            col_type = _guess_oracle_type(t["table"], col_name, bool(values))
            comment  = f" -- {'; '.join(comment_parts)}" if comment_parts else ""
            col_lines.append(f"  {col_name} {col_type},{comment}")

        if col_lines:
            # strip the trailing comma from the last column definition
            last_line = col_lines[-1]
            col_lines[-1] = re.sub(r',(?=(\s*--|$))', '', last_line, count=1)

        vertical_note = ""
        if col_labels:
            has_vertical_table = True
            vertical_note = (
                "\n  -- NOTE: this table is VERTICAL FORMAT — each row is one named metric "
                "(see 'known values' comments above). Do NOT SUM()/AVG() a value column across "
                "rows; instead filter the label column to the exact row you need."
            )
        if omitted_count:
            vertical_note += (
                f"\n  -- NOTE: {omitted_count} additional column(s) on this table were omitted "
                f"here as not relevant to this question — this is not the full table."
            )

        ddl_blocks.append(f"CREATE TABLE {table_name} (\n" + "\n".join(col_lines) + f"\n){vertical_note};")

    schema_context = "\n\n".join(ddl_blocks)
    valid_tables   = ", ".join(t["table"].upper() for t in tables)

    today_obj          = date.fromisoformat(today_date) if isinstance(today_date, str) else today_date
    _time_block        = _resolve_relative_time(user_query, today_obj)
    time_context_block = (_time_block + "\n") if _time_block else ""

    # Correction block injected on retry attempts. Kept short and appended
    # inside ### Notes rather than as its own separate ceremonial block —
    # SQLCoder's own training format doesn't use section banners, so this
    # stays close to plain instruction text.
    if previous_sql and previous_error:
        correction_block = (
            f"\n- CORRECTION REQUIRED: your previous attempt failed.\n"
            f"  Error: {previous_error}\n"
            f"  Bad SQL: {previous_sql}\n"
            f"  Fix ONLY the error above; keep the same tables/columns/WHERE logic "
            f"unless the error explicitly requires changing them.\n"
        )
    else:
        correction_block = ""

    # Compact, conditional multi-table/DOM-OVE hints — same guidance a
    # verbose rule-book would give, but kept to one line each and only
    # included when actually relevant, matching SQLCoder's terse own
    # training format rather than reverting to a long prose rule section.
    has_dom_ove_pair = any(
        _find_dom_ove_sibling(
            c["column"], {cc["column"].upper() for cc in all_columns if cc["table"] == c["table"]}
        )
        for c in all_columns
    )
    has_multi_table = len(tables) > 1
    qlow = user_query.lower()
    wants_combine = has_multi_table or bool(
        re.search(r'\b(compare|versus|vs|combined|union|both|all sections?)\b', qlow)
    )

    extra_notes = []
    if has_dom_ove_pair:
        extra_notes.append(
            "- A column with a noted domestic/overseas counterpart: if the question doesn't say "
            "\"domestic only\" or \"overseas only\", sum both sides, e.g. (col_DOM + col_OVE); "
            "never invent a separate TOTAL_<x> column."
        )
    if has_multi_table:
        extra_notes.append(
            "- If you need to JOIN tables above, join on CODE and RDATE together; use LEFT JOIN "
            "for optional data; never JOIN a table with its backup."
        )
    if wants_combine:
        extra_notes.append(
            "- To combine/compare figures across multiple parts or sections, use UNION ALL (not "
            "UNION) and apply the same label-column filter in every branch."
        )
    extra_notes_block = ("\n".join(extra_notes) + "\n") if extra_notes else ""

    notes = f"""### Notes
- Dialect: {dialect}. Today's date is {today_date}.
- Use ONLY the table/column names in the CREATE TABLE schema above — never invent one.
- Return ONLY the raw SQL SELECT statement — no explanation, no markdown fences, no semicolon.
- Never use bind variables/placeholders (:val, ?, %s) — embed all values as literals.
- Never touch backup tables (_bkup, _bk, _bckup, _backup suffixes).
- Date literals: TO_DATE('DD-MON-YYYY','DD-MON-YYYY'). Oracle has no EXTRACT(QUARTER FROM ...) — use EXTRACT(MONTH FROM RDATE) with a month range instead.
- "Latest" -> WHERE RDATE = (SELECT MAX(RDATE) FROM <same table>).
- Never invent a CODE value (a bank code) — omit the CODE filter entirely unless the question names a specific bank.
- When a table's comments say VERTICAL FORMAT, never SUM()/AVG() its value columns — filter the label column to the exact row instead (see the TOTAL row noted in its comment when the question asks for an overall/total figure).
{extra_notes_block}{time_context_block}{correction_block}"""

    # One compact worked example, shown only when a retrieved table is
    # actually vertical-format — SQLCoder-style models follow a concrete
    # example more reliably than an abstract rule, and this targets the
    # single most common first-attempt mistake seen in production logs:
    # SUM()-ing a vertical table's value column instead of filtering to
    # its TOTAL row. Kept deliberately short and schema-agnostic (fake
    # table/column names) so it can't be confused with a real candidate
    # table, and only added when relevant so it doesn't inflate every
    # prompt's size/generation time on this CPU-bound Ollama host.
    example_block = ""
    if has_vertical_table:
        example_block = """### Example
Example question: `Total sanctioned amount from EXAMPLE_RETURN latest`
Example schema:
CREATE TABLE EXAMPLE_RETURN (
  CATEGORY VARCHAR2(100), -- row label; known values: 'Corporate', 'Retail', 'Grand Total'; TOTAL row = 'Grand Total'
  SANCTIONED_AMT NUMBER,
  RDATE DATE
);
Example answer:
```sql
SELECT SANCTIONED_AMT FROM EXAMPLE_RETURN WHERE CATEGORY = 'Grand Total' AND RDATE = (SELECT MAX(RDATE) FROM EXAMPLE_RETURN)
```
(Note: no SUM()/AVG() — the label column is filtered to the TOTAL row instead.)

"""

    prompt = f"""### Task
Generate a {dialect} SQL query to answer the following question:
`{user_query}`

### Database Schema
The query will run on a database with the following schema:
{schema_context}

{notes}
{example_block}### Answer
Given the database schema, here is the SQL query that answers `{user_query}`:
```sql
"""

    # No bracket-tag scheme in this prompt format (see docstring above) —
    # returned for interface compatibility with generate_sql's unpacking;
    # _substitute_tags() is a no-op against an empty map.
    return prompt, {}


def _substitute_tags(sql: str, tag_map: dict) -> str:
    """
    Replace every [T<i>] / [C<i>_<j>] bracket tag in *sql* with its real
    schema name. A tag the model invented (not in tag_map) is deliberately
    left as literal bracket text — that's invalid SQL/an unresolvable
    identifier, so it fails validate_sql or Oracle execution loudly instead
    of silently resolving to a plausible-but-wrong name.
    """
    def _replace(m):
        tag = m.group(1)
        return tag_map.get(tag, m.group(0))
    return re.sub(r'\[([TC]\d+(?:_\d+)?)\]', _replace, sql)


def generate_sql(user_query, tables, columns, dialect="Oracle", today_date=None,
                 matched_labels=None, previous_sql=None, previous_error=None):
    prompt, tag_map = build_prompt(
        user_query, tables, columns,
        dialect=dialect, today_date=today_date, matched_labels=matched_labels,
        previous_sql=previous_sql, previous_error=previous_error,
    )

    payload = {
        "model":  OLLAMA_MODEL,
        "prompt": prompt,
        "stream": True,
        # Keep the model resident in Ollama between requests — without this,
        # Ollama's default idle timeout can unload the model and every
        # request pays a full reload (can be many seconds) before generation
        # even starts.
        "keep_alive": "30m",
        "options": {
            # Generated SQL is short; capping tokens stops the model from
            # running past its answer (e.g. re-explaining itself) and
            # burning time on tokens we'd strip anyway. Measured on this
            # (CPU-only) Ollama host at ~111ms/output-token — every unused
            # token in this cap is pure latency risk against the proxy's
            # ~120s gateway timeout, so this is kept as tight as a
            # multi-branch UNION ALL query can still comfortably need.
            "num_predict": 250,
            # SQL generation should be deterministic, not creative — greedy
            # decoding is also cheaper per-token than sampling.
            "temperature": 0,
        },
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=300, stream=True)
        response.raise_for_status()
    except requests.exceptions.ConnectionError:
        raise RuntimeError("Cannot connect to Ollama. Make sure it is running: `ollama serve`")
    except requests.exceptions.ReadTimeout:
        raise RuntimeError("Ollama timed out (300s). Try a smaller/faster model.")
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(f"Ollama API error: {e}")

    raw = ""
    for line in response.iter_lines():
        if not line:
            continue
        chunk = json.loads(line)
        raw += chunk.get("response", "")
        if chunk.get("done"):
            break

    # Strip markdown fences and trailing semicolons
    raw = re.sub(r'^```(?:sql)?\s*', '', raw.strip(), flags=re.IGNORECASE)
    raw = re.sub(r'```\s*$', '', raw).strip()
    raw = raw.rstrip().rstrip(";")

    # Fix unbalanced parentheses (LLM sometimes adds extra closing parens)
    raw = _fix_unbalanced_parens(raw)

    # Resolve [T1]/[C1_6]-style tags to their real schema.json names. This is
    # the primary defense against hallucinated identifiers — the model never
    # gets to freely type a table/column name in the first place.
    raw = _substitute_tags(raw, tag_map)

    # Fallback safety net: if the model ignored the tag instruction and wrote
    # a plain name directly anyway, still try to ground near-miss typos
    # against the real schema (e.g. singular/plural drift).
    raw = _autocorrect_columns(raw, tables)

    # Deterministically fix the most common vertical-format mistake (blind
    # SUM/AVG with no total-row filter) instead of gambling on a retry.
    raw = _autofix_vertical_total(raw, tables)

    # Deterministically fix ORA-00937 (aggregate mixed with a plain column,
    # no GROUP BY) — a pure syntax error, unrelated to which table/column
    # was chosen, so there's no ambiguity risk in fixing it directly.
    raw = _autofix_mixed_aggregation(raw)

    return {
        "sql": raw,
        "question_understanding": "",
        "result_columns": [],
        "visualizations": [],
        "followup_questions": [],
        "warnings": [],
    }


def validate_sql(sql, tables, columns):
    """Returns (is_valid: bool, reason: str)"""
    if isinstance(sql, dict):
        sql = sql.get("sql", "")

    if not sql:
        return False, "Empty SQL"

    # An unresolved [T<i>]/[C<i>_<j>] tag means the model referenced a tag it
    # was never given (invented one) — _substitute_tags() only replaces tags
    # present in tag_map and deliberately leaves unknown ones untouched so
    # this is catchable here instead of silently producing broken SQL.
    unresolved_tags = re.findall(r'\[[TC]\d+(?:_\d+)?\]', sql)
    if unresolved_tags:
        return False, f"Unresolved tag reference(s) — not a table/column you were given: {sorted(set(unresolved_tags))}"

    q = sql.lower().replace('"', '').strip()

    # Mask string literals: replace content inside '...' with spaces so
    # tokens like 'Substandard' don't leak as column candidates.
    def _mask_literals(s: str) -> str:
        out, in_str = [], False
        for ch in s:
            if ch == "'":
                in_str = not in_str
                out.append(ch)
            elif in_str:
                out.append(' ')
            else:
                out.append(ch)
        return ''.join(out)

    q = _mask_literals(q)

    if not q.startswith("select"):
        return False, "Only SELECT queries are allowed"

    for word in BANNED_KEYWORDS:
        if re.search(rf'\b{word}\b', q):
            return False, f"Dangerous keyword detected: '{word}'"

    valid_table_names = {t["table"].lower() for t in tables}

    subquery_aliases  = set(re.findall(r'\bas\s+([a-z_][a-z0-9_]*)', q))
    subquery_aliases |= set(re.findall(r'\)\s+([a-z_][a-z0-9_]*)\b', q))

    q_for_tables      = re.sub(r'\bextract\s*\([^)]*\)', '', q)
    q_for_tables      = re.sub(r'\btrim\s*\([^)]*\)', '', q_for_tables)
    referenced_tables = set(re.findall(r'(?:from|join)\s+([a-z_][a-z0-9_]*)', q_for_tables))
    real_table_refs   = referenced_tables - subquery_aliases - ORACLE_PSEUDO_TABLES
    hallucinated_tables = real_table_refs - valid_table_names
    if hallucinated_tables:
        return False, f"Hallucinated tables (not in schema): {sorted(hallucinated_tables)}"

    # Tables actually used in this SQL (not the whole retrieved candidate pool) —
    # columns are validated only against these, so a column that belongs to a
    # sibling candidate table but isn't in this query's FROM/JOIN is rejected
    # instead of silently passing validation.
    used_table_names = real_table_refs & valid_table_names
    if not used_table_names:
        return False, f"Query does not reference any matched table: {sorted(valid_table_names)}"

    all_columns     = _load_all_columns(used_table_names)
    valid_col_names = {c["column"].lower() for c in all_columns}

    # Find the top-level FROM (depth-0), not a FROM inside a subquery
    _depth, _in_str, _outer_from_pos = 0, False, -1
    _lq = q
    for _i, _ch in enumerate(_lq):
        if _ch == "'":
            _in_str = not _in_str
        elif not _in_str:
            if _ch == '(':
                _depth += 1
            elif _ch == ')':
                _depth -= 1
            elif _depth == 0 and _lq[_i:_i+4] == 'from':
                _before = _lq[_i-1] if _i > 0 else ' '
                _after  = _lq[_i+4] if _i+4 < len(_lq) else ' '
                if not (_before.isalnum() or _before == '_') and not (_after.isalnum() or _after == '_'):
                    _outer_from_pos = _i
                    break
    select_body = (q[:_outer_from_pos] if _outer_from_pos != -1 else q)
    select_body = select_body.replace("select", "", 1).strip()
    select_body = re.sub(r'\bas\s+[a-z_][a-z0-9_]*', '', select_body)
    select_body = re.sub(r'\b(sum|avg|min|max|count|coalesce|nvl|nullif|trim|upper|lower|to_date|to_char)\s*\(', '(', select_body)
    select_body = re.sub(r'[*/+\-()\[\]]', ' ', select_body)

    col_tokens = re.findall(r'(?:[a-z_][a-z0-9_]*\.)?([a-z_][a-z0-9_]*)', select_body)

    hallucinated_cols = {
        t for t in col_tokens
        if (
            t not in valid_col_names
            and t not in valid_table_names          # table names in inline subqueries are valid
            and t not in _SQL_KEYWORDS
            and t not in subquery_aliases
            and t not in _ORACLE_FORMAT_TOKENS
            and t not in _ORACLE_BUILTIN_TOKENS
            and t != "*"
            and not t.isdigit()
            and len(t) > 2
        )
    }

    if hallucinated_cols:
        return False, f"Hallucinated columns (not in schema): {sorted(hallucinated_cols)}"

    # ── Vertical-format guard ───────────────────────────────────────────────
    # Tables with row-label samples (description_samples.json) store one
    # pre-computed metric per row rather than raw numbers to aggregate. This
    # checks two things, both against the ORIGINAL (unmasked) sql so the
    # actual literal filter value can be inspected:
    #   1. the label column is filtered at all (not just SUM/AVG-ed blind)
    #   2. the value used is one of the table's REAL known row values — a
    #      model that gets rejected for (1) can "fix" it just enough to pass
    #      a shallow name-presence check by bolting on a fabricated value
    #      (e.g. WHERE PERIOD_DELINQUENCY = 'Latest', echoing a word from the
    #      user's question rather than looking up an actual row); that must
    #      still be caught, or a 0-row match silently returns SUM() = NULL
    #      and looks like a successful, if wrong, answer.
    if re.search(r'\b(sum|avg)\s*\(', q):
        samples = _get_samples()
        for tbl in used_table_names:
            label_cols = samples.get(tbl, {})
            if not label_cols:
                continue

            matched_col, matched_value = None, None
            for lc in label_cols:
                m = re.search(rf'\b{re.escape(lc)}\b\s*=\s*\'([^\']*)\'', sql, re.IGNORECASE)
                if m:
                    matched_col, matched_value = lc, m.group(1)
                    break

            if matched_col is None:
                # Also allow the LIKE fallback (RULE V4) without the exact-value
                # check below — a fuzzy filter is intentionally more permissive.
                has_like = any(
                    re.search(rf'\b{re.escape(lc)}\b\s+like\s+\'', q) for lc in label_cols
                )
                if has_like:
                    continue
                return False, (
                    f"Table {tbl.upper()} is VERTICAL format (each row is a named "
                    f"metric) but the query uses SUM/AVG without filtering its "
                    f"label column ({', '.join(sorted(c.upper() for c in label_cols))}). "
                    f"Do not aggregate — SELECT the metric column directly and add "
                    f"WHERE <label_col> = '<exact row value>' for the total/specific row."
                )

            known_values = label_cols[matched_col]
            if matched_value.lower() not in {v.lower() for v in known_values}:
                preview = ", ".join(f"'{v}'" for v in known_values[:10])
                return False, (
                    f"Table {tbl.upper()} column {matched_col.upper()} was filtered to "
                    f"'{matched_value}', which is NOT a real row value for this table "
                    f"— it looks invented. Known real values include: {preview}. "
                    f"Use one of these exact values (the one containing 'Total' is "
                    f"usually the right row for an overall/total figure)."
                )

    # ── Mixed-aggregation backstop ───────────────────────────────────────────
    # _autofix_mixed_aggregation() already handles the common shape (a whole
    # SELECT item being a single aggregate call). This catches anything that
    # slips past it (e.g. an aggregate nested inside a larger expression) so
    # a guaranteed ORA-00937 triggers a retry with a clear reason instead of
    # reaching Oracle.
    if _has_mixed_aggregation(sql):
        return False, (
            "SELECT list mixes an aggregate function (SUM/AVG/COUNT/MIN/MAX) "
            "with a plain (non-aggregated) column and has no GROUP BY — this "
            "is invalid SQL (ORA-00937). Either remove the aggregate function "
            "(select the plain column directly) or add a GROUP BY covering "
            "every non-aggregated column."
        )

    return True, "Valid"
