import re
import json
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


def build_prompt(user_query, tables, columns, dialect="Oracle", today_date=None,
                 matched_labels=None, previous_sql=None, previous_error=None):
    if today_date is None:
        today_date = date.today().isoformat()

    table_names = {t["table"] for t in tables}
    all_columns = _load_all_columns(table_names)

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

    schema_lines = []
    for t in tables:
        table_name = t["table"].upper()
        table_col_objs = [c for c in all_columns if c["table"] == t["table"]]
        col_parts = []
        for c in table_col_objs:
            label = c.get("return_name") or c.get("description") or ""
            part  = c["column"].upper()
            if label:
                part += f" ({label})"
            col_parts.append(part)
        cols_str = ", ".join(col_parts) if col_parts else "(none)"
        block    = f"Table: {table_name}\nAllowed columns (use ONLY these): {cols_str}"

        col_labels = label_map.get(t["table"], {})
        if col_labels:
            block += "\nSTORAGE FORMAT: VERTICAL — each row is a named metric. DO NOT aggregate with SUM() across all rows."
            label_lines = []
            for col, values in col_labels.items():
                sample_str = ", ".join(f"'{v}'" for v in values)
                label_lines.append(f"  {col.upper()} relevant values: {sample_str}")
                total_row = _find_total_row(values)
                if total_row:
                    label_lines.append(
                        f"  *** TOTAL ROW for {col.upper()}: '{total_row}' — "
                        f"use WHERE {col.upper()} = '{total_row}' when user asks for totals/overall/grand total ***"
                    )
            block += "\nRelevant row labels (matched to your query):\n" + "\n".join(label_lines)

        schema_lines.append(block)

    schema_context = "\n\n".join(schema_lines)
    valid_tables   = ", ".join(t["table"].upper() for t in tables)

    today_obj          = date.fromisoformat(today_date) if isinstance(today_date, str) else today_date
    _time_block        = _resolve_relative_time(user_query, today_obj)
    time_context_block = (_time_block + "\n") if _time_block else ""

    # Correction block injected on retry attempts
    if previous_sql and previous_error:
        correction_block = (
            "\n════════════════════════════════════════════════\n"
            "CORRECTION REQUIRED — your previous attempt failed\n"
            "════════════════════════════════════════════════\n"
            f"Error   : {previous_error}\n"
            f"Bad SQL : {previous_sql}\n"
            "Fix ONLY the error above. Keep the same tables, columns, and WHERE logic "
            "unless the error explicitly requires changing them.\n"
            "════════════════════════════════════════════════\n"
        )
    else:
        correction_block = ""

    return f"""You are an expert {dialect} SQL generator. Today is {today_date}.

════════════════════════════════════════════════
ABSOLUTE RULES (never break these)
════════════════════════════════════════════════
1. Return ONLY a raw SQL SELECT query — no explanation, no markdown, no code fences, no semicolon.
2. Use ONLY table names and column names listed in the SCHEMA CONTEXT below. Never invent names.
3. Never use bind variables or placeholders (:val, ?, %s). Embed all values as literals.
4. Never touch backup tables (_bkup, _bk, _bckup, _backup suffixes). Use only the main tables.
5. COUNT EVERY PARENTHESIS before returning — the total number of '(' must equal ')'.
   WRONG: SELECT ( (subq1) + (subq2) ) ) AS X FROM DUAL   ← extra ')'
   RIGHT: SELECT ( (subq1) + (subq2) ) AS X FROM DUAL
6. Use TO_DATE('DD-MON-YYYY','DD-MON-YYYY') format for ALL date literals. Never write bare date strings.
7. SELECT ... FROM DUAL is valid ONLY for pure expression evaluation with no table rows.
   Never wrap a subquery that already returns rows with FROM DUAL.

════════════════════════════════════════════════
VERTICAL FORMAT TABLES — CRITICAL RULES
════════════════════════════════════════════════
Any table tagged "STORAGE FORMAT: VERTICAL" below stores data as named rows.
Each row is one pre-computed metric (e.g. "Substandard", "Total", "Grand Total").
The database already has aggregated/total rows — DO NOT re-aggregate them.

RULE V1 — NEVER aggregate vertically:
  WRONG:  SELECT SUM(TOTAL_LOAN_ASSETS) FROM CIMS_RAQ_Q_SEC1_PART_A_DOM
  RIGHT:  SELECT TOTAL_LOAN_ASSETS FROM CIMS_RAQ_Q_SEC1_PART_A_DOM
          WHERE PERIOD_DELINQUENCY = 'C. Total ( A + B)'

RULE V2 — To get the TOTAL / OVERALL value:
  Use WHERE <label_col> = '<*** TOTAL ROW ***>' shown for each table below.

RULE V3 — To get a SPECIFIC metric:
  Use WHERE <label_col> = '<exact value from Known row labels list>'

RULE V4 — LIKE fallback (use ONLY when no exact match is available):
  WHERE <label_col> LIKE '%keyword%'

RULE V5 — You MAY use SUM/AVG only when the table is NOT tagged VERTICAL.

════════════════════════════════════════════════
DOM / OVE COLUMN RULES  (Domestic + Overseas)
════════════════════════════════════════════════
RULE D1 — When user asks for "total"/"combined"/"overall": SELECT (col_DOM + col_OVE) AS TOTAL_col
RULE D2 — "domestic only" → col_DOM; "overseas only" → col_OVE
RULE D3 — comparing dom vs ove → select both columns separately
RULE D4 — Do NOT invent TOTAL_<x>; compute inline as (col_DOM + col_OVE)

════════════════════════════════════════════════
MULTI-PART / MULTI-SECTION RULES
════════════════════════════════════════════════
RULE M1 — Combined total across parts: use UNION ALL subquery then SUM
RULE M2 — Use UNION ALL (not UNION)
RULE M3 — Only union parts explicitly mentioned
RULE M4 — Apply same label WHERE filter in each branch of UNION ALL
RULE M5 — Tag section with literal column when unioning across sections

════════════════════════════════════════════════
JOIN RULES
════════════════════════════════════════════════
RULE J1 — JOIN only when multiple tables needed
RULE J2 — Always join on CODE and RDATE together
RULE J3 — Use LEFT JOIN for optional rows
RULE J4 — Never JOIN main table with its backup

════════════════════════════════════════════════
MULTI-CODE / BANK RULES
════════════════════════════════════════════════
RULE B1 — CODE identifies reporting bank. Omit CODE filter if bank not specified.
RULE B2 — Specific bank → WHERE CODE = <bank_code>

════════════════════════════════════════════════
DATE & PERIOD RULES
════════════════════════════════════════════════
RULE P1 — RDATE is the reporting date column.
RULE P2 — "Latest" → WHERE RDATE = (SELECT MAX(RDATE) FROM <same_table>)
RULE P3 — "Last N quarters" → WHERE RDATE >= ADD_MONTHS((SELECT MAX(RDATE) FROM <t>), -<N*3>)
RULE P4 — "Year YYYY" → WHERE EXTRACT(YEAR FROM RDATE) = YYYY
RULE P5 — Date range → WHERE RDATE BETWEEN TO_DATE('DD-MON-YYYY','DD-MON-YYYY') AND TO_DATE('DD-MON-YYYY','DD-MON-YYYY')
RULE P6 — "Trend" → include RDATE in SELECT + ORDER BY RDATE ASC
RULE P7 — Never hardcode date literals; derive via MAX(RDATE)
RULE P8 — *** ORACLE HAS NO EXTRACT(QUARTER FROM ...) — it is INVALID SYNTAX ***
           To filter by quarter, use EXTRACT(MONTH FROM RDATE) with a month range:
             Calendar Q1 (Jan–Mar)  → EXTRACT(MONTH FROM RDATE) BETWEEN 1 AND 3
             Calendar Q2 (Apr–Jun)  → EXTRACT(MONTH FROM RDATE) BETWEEN 4 AND 6
             Calendar Q3 (Jul–Sep)  → EXTRACT(MONTH FROM RDATE) BETWEEN 7 AND 9
             Calendar Q4 (Oct–Dec)  → EXTRACT(MONTH FROM RDATE) BETWEEN 10 AND 12
           Indian FY quarters (FY starts April):
             FY Q1 (Apr–Jun)  → EXTRACT(MONTH FROM RDATE) BETWEEN 4  AND 6
             FY Q2 (Jul–Sep)  → EXTRACT(MONTH FROM RDATE) BETWEEN 7  AND 9
             FY Q3 (Oct–Dec)  → EXTRACT(MONTH FROM RDATE) BETWEEN 10 AND 12
             FY Q4 (Jan–Mar)  → EXTRACT(MONTH FROM RDATE) BETWEEN 1  AND 3
           If RESOLVED TIME CONTEXT is provided above, use the exact RDATE range from there instead.

════════════════════════════════════════════════
RANKING & TOP-N RULES
════════════════════════════════════════════════
RULE R1 — "Top N" → ORDER BY col DESC FETCH FIRST N ROWS ONLY
RULE R2 — "Bottom N" → ORDER BY col ASC FETCH FIRST N ROWS ONLY
RULE R3 — "Rank banks" → RANK() OVER (PARTITION BY RDATE ORDER BY col DESC)
RULE R4 — Prefer FETCH FIRST over ROWNUM

════════════════════════════════════════════════
SCHEMA CONTEXT
════════════════════════════════════════════════
{schema_context}

════════════════════════════════════════════════
Allowed tables: {valid_tables}
{time_context_block}{correction_block}User question: {user_query}
════════════════════════════════════════════════
SQL:"""


def generate_sql(user_query, tables, columns, dialect="Oracle", today_date=None,
                 matched_labels=None, previous_sql=None, previous_error=None):
    prompt = build_prompt(
        user_query, tables, columns,
        dialect=dialect, today_date=today_date, matched_labels=matched_labels,
        previous_sql=previous_sql, previous_error=previous_error,
    )

    payload = {
        "model":  OLLAMA_MODEL,
        "prompt": prompt,
        "stream": True,
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
    all_columns       = _load_all_columns(valid_table_names)
    valid_col_names   = {c["column"].lower() for c in all_columns}

    subquery_aliases  = set(re.findall(r'\bas\s+([a-z_][a-z0-9_]*)', q))
    subquery_aliases |= set(re.findall(r'\)\s+([a-z_][a-z0-9_]*)\b', q))

    q_for_tables      = re.sub(r'\bextract\s*\([^)]*\)', '', q)
    q_for_tables      = re.sub(r'\btrim\s*\([^)]*\)', '', q_for_tables)
    referenced_tables = set(re.findall(r'(?:from|join)\s+([a-z_][a-z0-9_]*)', q_for_tables))
    real_table_refs   = referenced_tables - subquery_aliases - ORACLE_PSEUDO_TABLES
    hallucinated_tables = real_table_refs - valid_table_names
    if hallucinated_tables:
        return False, f"Hallucinated tables (not in schema): {sorted(hallucinated_tables)}"

    if not referenced_tables & valid_table_names:
        return False, f"Query does not reference any matched table: {sorted(valid_table_names)}"

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

    return True, "Valid"
