import re
import json
import time
import calendar
import logging
import requests
from datetime import date, timedelta
import src.config as config
# Safe at module level: description_fetcher imports only json/os/config up front
# (oracledb and faiss are function-local there) and never imports this module.
from src.description_fetcher import load_samples

log = logging.getLogger("sql_generator")

BANNED_KEYWORDS = ["delete", "update", "drop", "insert", "truncate", "alter", "create", "exec"]
MAX_LABELS_MINIMAL = 8
# Correction rounds after the first attempt. Each round is a fresh LLM call
# followed by a fresh validation AND a fresh Oracle dry run. Was 1; WrenAI uses
# 3 (max_sql_correction_retries), and a single round is not enough when the
# first error is a column name and the second is a type mismatch.
MAX_CORRECTION_RETRIES = 3
# Row-label values rendered per column in a CREATE TABLE comment. Higher than
# the minimal-prompt cap because the DDL block is far more compact than the old
# prose schema listing, and an exact label literal is the one thing the model
# cannot invent correctly.
MAX_LABELS_DDL = 14

# ── Ollama circuit breaker ──────────────────────────────────────────────────
# Without this, an unreachable/down proxy made every single request hang for
# up to the full 300s read-timeout before failing (connect failures were not
# capped separately from the read timeout). Two fixes:
#   1. A short connect-timeout so a dead/unreachable host fails in seconds,
#      not minutes, while still allowing up to 300s for a slow-but-alive
#      model to actually finish generating.
#   2. A short in-process "recently confirmed down" cache so repeated
#      requests during an ongoing outage fail in ~0ms instead of each
#      re-attempting and re-waiting for the connect timeout.
_OLLAMA_CONNECT_TIMEOUT_S = 3
_OLLAMA_OUTAGE_COOLDOWN_S = 30
_ollama_outage_until = 0.0  # monotonic timestamp; 0 = not currently marked down


def _resolve_relative_time(query: str, today: date) -> str | None:
    """
    Detect relative time expressions in the user query and resolve them to
    concrete calendar date ranges.  The returned block is injected into the
    SQL prompt so the LLM never has to guess what 'last quarter' means.
    """
    q = query.lower()
    lines = []

    # ── helpers ──────────────────────────────────────────────────────────────
    def fmt(d): return d.strftime("%Y-%m-%d")
    def month_end(y, m): return date(y, m, calendar.monthrange(y, m)[1])

    # ── This / last WEEK ─────────────────────────────────────────────────────
    if re.search(r'\b(this|current)\s+week\b', q):
        mon = today - timedelta(days=today.weekday())
        sun = mon + timedelta(days=6)
        lines.append(f"'this week'  = {fmt(mon)} to {fmt(sun)}")

    if re.search(r'\b(last|previous)\s+week\b', q):
        mon = today - timedelta(days=today.weekday() + 7)
        sun = mon + timedelta(days=6)
        lines.append(f"'last week'  = {fmt(mon)} to {fmt(sun)}")

    # ── This / last MONTH ────────────────────────────────────────────────────
    if re.search(r'\b(this|current)\s+month\b', q):
        start = today.replace(day=1)
        end = month_end(today.year, today.month)
        lines.append(f"'this month' = {today.strftime('%B %Y')}  ({fmt(start)} to {fmt(end)})")

    if re.search(r'\b(last|previous)\s+month\b', q):
        end = today.replace(day=1) - timedelta(days=1)
        start = end.replace(day=1)
        lines.append(f"'last month' = {end.strftime('%B %Y')}  ({fmt(start)} to {fmt(end)})")

    # ── helper: subtract N whole months from a date, returning (year, month) ───
    def _months_back(y, m, n):
        idx = (y * 12 + (m - 1)) - n
        return idx // 12, idx % 12 + 1

    _WORD_NUM = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
        "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    }

    def _extract_n(token: str) -> int:
        return int(token) if token.isdigit() else _WORD_NUM.get(token.lower(), 0)

    _N_WORD_RE = r'(\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)'

    # ── Last/previous/past N MONTHS ──────────────────────────────────────────
    # Matches: "last 3 months", "past 6 months", "previous two months", "trailing 4 months"
    m_months = re.search(rf'\b(?:last|previous|past|trailing)\s+{_N_WORD_RE}\s+months?\b', q)
    if m_months:
        n = _extract_n(m_months.group(1))
        if n > 0:
            # The N complete months immediately preceding the current (in-progress) month.
            end_y, end_m = _months_back(today.year, today.month, 1)
            end = month_end(end_y, end_m)
            start_y, start_m = _months_back(today.year, today.month, n)
            start = date(start_y, start_m, 1)
            lines.append(
                f"'last {n} months' = {start.strftime('%B %Y')} to {end.strftime('%B %Y')}  "
                f"({fmt(start)} to {fmt(end)})"
            )

    # ── Last/previous/past N YEARS ───────────────────────────────────────────
    m_years = re.search(rf'\b(?:last|previous|past|trailing)\s+{_N_WORD_RE}\s+years?\b', q)
    if m_years:
        n = _extract_n(m_years.group(1))
        if n > 0:
            end_y = today.year - 1
            start_y = today.year - n
            lines.append(
                f"'last {n} years' = {start_y} to {end_y}  "
                f"(01-JAN-{start_y} to 31-DEC-{end_y})"
            )

    # ── This / last YEAR (calendar) ──────────────────────────────────────────
    if re.search(r'\b(this|current)\s+year\b', q):
        lines.append(f"'this year'  = {today.year}  (01-JAN-{today.year} to 31-DEC-{today.year})")

    if re.search(r'\b(last|previous)\s+year\b', q):
        y = today.year - 1
        lines.append(f"'last year'  = {y}  (01-JAN-{y} to 31-DEC-{y})")

    # ── Calendar QUARTER (Jan-Mar / Apr-Jun / Jul-Sep / Oct-Dec) ─────────────
    _CQ_START = {1: (1, 1),  2: (4, 1),  3: (7, 1),  4: (10, 1)}
    _CQ_END   = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}
    cur_cq = (today.month - 1) // 3 + 1

    if re.search(r'\b(this|current)\s+quarter\b', q):
        s = date(today.year, *_CQ_START[cur_cq])
        e = date(today.year, *_CQ_END[cur_cq])
        lines.append(f"'this quarter' = Q{cur_cq} {today.year} (calendar)  ({fmt(s)} to {fmt(e)})")

    if re.search(r'\b(last|previous)\s+quarter\b', q):
        prev_cq = cur_cq - 1 if cur_cq > 1 else 4
        prev_cq_year = today.year if cur_cq > 1 else today.year - 1
        s = date(prev_cq_year, *_CQ_START[prev_cq])
        e = date(prev_cq_year, *_CQ_END[prev_cq])
        lines.append(f"'last quarter' = Q{prev_cq} {prev_cq_year} (calendar)  ({fmt(s)} to {fmt(e)})")

    # ── Last/previous/past N QUARTERS (calendar) ─────────────────────────────
    # Matches: "last 3 quarters", "past 4 quarters", "previous two quarters"
    # Range = the N most recently COMPLETED calendar quarters (current quarter excluded).
    m_quarters = re.search(rf'\b(?:last|previous|past|trailing)\s+{_N_WORD_RE}\s+quarters?\b', q)
    if m_quarters:
        n = _extract_n(m_quarters.group(1))
        if n > 0:
            end_cq, end_cq_year = cur_cq - 1, today.year
            if end_cq == 0:
                end_cq, end_cq_year = 4, today.year - 1
            # step back (n - 1) more quarters from the end quarter to get the start quarter
            start_idx = (end_cq_year * 4 + (end_cq - 1)) - (n - 1)
            start_cq_year, start_cq = start_idx // 4, start_idx % 4 + 1
            s = date(start_cq_year, *_CQ_START[start_cq])
            e = date(end_cq_year, *_CQ_END[end_cq])
            unit = "quarter" if n == 1 else "quarters"
            lines.append(
                f"'last {n} {unit}' = Q{start_cq} {start_cq_year} to Q{end_cq} {end_cq_year} (calendar)  "
                f"({fmt(s)} to {fmt(e)})"
            )

    # ── Financial Year quarters (India Apr–Mar, Q1=Apr-Jun … Q4=Jan-Mar) ─────
    fy_sy = today.year if today.month >= 4 else today.year - 1  # FY start year
    _FYQ = {
        1: {"months": {4, 5, 6},    "start": (4, 1),  "end": (6, 30),  "offset": 0},
        2: {"months": {7, 8, 9},    "start": (7, 1),  "end": (9, 30),  "offset": 0},
        3: {"months": {10, 11, 12}, "start": (10, 1), "end": (12, 31), "offset": 0},
        4: {"months": {1, 2, 3},    "start": (1, 1),  "end": (3, 31),  "offset": 1},
    }
    cur_fyq = next(fq for fq, v in _FYQ.items() if today.month in v["months"])

    if re.search(r'\b(this|current)\s+(fy|financial|fiscal)\s*(quarter|q)\b', q):
        off = _FYQ[cur_fyq]["offset"]
        s = date(fy_sy + off, *_FYQ[cur_fyq]["start"])
        e = date(fy_sy + off, *_FYQ[cur_fyq]["end"])
        lines.append(f"'this FY quarter' = Q{cur_fyq} FY{fy_sy+1}  ({fmt(s)} to {fmt(e)})")

    if re.search(r'\b(last|previous)\s+(fy|financial|fiscal)\s*(quarter|q)\b', q):
        prev_fyq = cur_fyq - 1 if cur_fyq > 1 else 4
        prev_fy_sy = fy_sy if cur_fyq > 1 else fy_sy - 1
        off = _FYQ[prev_fyq]["offset"]
        s = date(prev_fy_sy + off, *_FYQ[prev_fyq]["start"])
        e = date(prev_fy_sy + off, *_FYQ[prev_fyq]["end"])
        lines.append(f"'last FY quarter' = Q{prev_fyq} FY{prev_fy_sy+1}  ({fmt(s)} to {fmt(e)})")

    # ── Last/previous/past N FY QUARTERS ─────────────────────────────────────
    # Matches: "last 3 fy quarters", "past 2 fiscal quarters"
    # FY quarters run consecutively Q1→Q4 each starting April; index them on a
    # continuous timeline so stepping back N just means subtracting N from the index.
    m_fyq = re.search(rf'\b(?:last|previous|past|trailing)\s+{_N_WORD_RE}\s+(?:fy|financial|fiscal)\s*(?:quarter|q)s?\b', q)
    if m_fyq:
        n = _extract_n(m_fyq.group(1))
        if n > 0:
            # continuous FY-quarter index: FY_start_year*4 + (fyq-1), counting from current FY quarter
            cur_idx = fy_sy * 4 + (cur_fyq - 1)
            end_idx = cur_idx - 1               # most recently completed FY quarter
            start_idx = end_idx - (n - 1)
            end_fy_sy, end_fyq = end_idx // 4, end_idx % 4 + 1
            start_fy_sy, start_fyq = start_idx // 4, start_idx % 4 + 1
            s = date(start_fy_sy + _FYQ[start_fyq]["offset"], *_FYQ[start_fyq]["start"])
            e = date(end_fy_sy + _FYQ[end_fyq]["offset"], *_FYQ[end_fyq]["end"])
            lines.append(
                f"'last {n} FY quarters' = Q{start_fyq} FY{start_fy_sy+1} to Q{end_fyq} FY{end_fy_sy+1}  "
                f"({fmt(s)} to {fmt(e)})"
            )

    # ── This / last FINANCIAL YEAR ────────────────────────────────────────────
    if re.search(r'\b(this|current)\s+(financial year|fiscal year|fy)\b(?!\s*(?:quarter|q)\b)', q):
        lines.append(
            f"'this financial year' = FY{fy_sy+1}  "
            f"(01-APR-{fy_sy} to 31-MAR-{fy_sy+1})"
        )

    if re.search(r'\b(last|previous)\s+(financial year|fiscal year|fy)\b(?!\s*(?:quarter|q)\b)', q):
        lines.append(
            f"'last financial year' = FY{fy_sy}  "
            f"(01-APR-{fy_sy-1} to 31-MAR-{fy_sy})"
        )

    # ── Generic "last N periods" / "last N reporting periods" ───────────────
    # A "period" here is whatever granularity RDATE reports at for that table
    # (monthly, quarterly, etc.) — it cannot be resolved to a fixed calendar
    # range up front, so instead we tell the LLM exactly how to fetch the last
    # N distinct RDATE rows. Only fires if no more specific unit (month/
    # quarter/year/FY quarter) was already matched above, so an explicit
    # "last 3 quarters" still gets the precise calendar-quarter resolution.
    m_periods = re.search(rf'\b(?:last|previous|past|trailing)\s+{_N_WORD_RE}\s+(?:periods?|reporting\s+periods?)\b', q)
    if m_periods and not any(("quarter" in l or "month" in l or "year" in l) for l in lines):
        n = _extract_n(m_periods.group(1))
        if n > 0:
            lines.append(
                f"'last {n} periods' = the {n} most recent distinct RDATE values for the table "
                f"(NOT a fixed calendar range). Resolve with:\n"
                f"    WHERE RDATE IN (\n"
                f"      SELECT DISTINCT RDATE FROM <same_table>\n"
                f"      ORDER BY RDATE DESC FETCH FIRST {n} ROWS ONLY\n"
                f"    )"
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

# SQL keywords and functions to skip during column validation
_SQL_KEYWORDS = {
    "select", "from", "where", "and", "or", "not", "in", "is", "null",
    "as", "on", "join", "inner", "outer", "left", "right", "full", "cross",
    "group", "by", "order", "having", "distinct", "between", "like", "case",
    "when", "then", "else", "end", "union", "all", "exists", "limit", "offset",
    "count", "sum", "avg", "min", "max", "coalesce", "nvl", "trim", "upper",
    "lower", "to_date", "to_char", "rownum", "dual", "with", "asc", "desc",
    # window function keywords
    "over", "partition", "rows", "range", "unbounded", "preceding",
    "following", "current", "row", "window", "rank", "dense_rank",
    "row_number", "ntile", "lag", "lead", "first_value", "last_value",
}


# Cache of parsed schema.json contents, keyed by path — _columns_from_schema
# and _table_entries_from_schema both re-read and re-parsed the same file from
# disk on every call (build_prompt, retry-prep, and validate_sql all call into
# these, so a single request could pay for this several times). Mirrors the
# load-once pattern already used for FAISS/BM25/
# concept_map/business_dictionary elsewhere in this codebase. Cached for the
# life of the process — a schema.json rebuild needs a restart to take effect,
# same caveat as retriever.py's _index_cache.
_schema_json_cache: dict = {}


def _load_schema_json(schema_path):
    if schema_path not in _schema_json_cache:
        try:
            with open(schema_path) as f:
                _schema_json_cache[schema_path] = json.load(f)
        except FileNotFoundError:
            _schema_json_cache[schema_path] = None
    return _schema_json_cache[schema_path]


def _columns_from_schema(schema_path, normalized_table_names):
    schema = _load_schema_json(schema_path)
    if schema is None:
        return []
    result = []
    for entry in schema:
        table_name = entry.get("table") or entry.get("table_name")
        if not table_name or table_name.lower() not in normalized_table_names:
            continue
        for col in entry.get("columns") or []:
            column_name = col.get("name") or col.get("column_name")
            if not column_name:
                continue
            result.append({"table": table_name, "column": column_name})
    return result


def _load_all_columns(table_names, schema_path=None):
    """
    Return all columns for the given table names loaded from schema.json
    (config.EMBEDDING_DIR by default). No fallback to any other schema —
    a table missing from the active schema simply returns no columns.
    """
    if schema_path is None:
        schema_path = f"{config.EMBEDDING_DIR}/schema.json"

    normalized_table_names = {name.lower() for name in table_names}
    return _columns_from_schema(schema_path, normalized_table_names)


def _table_entries_from_schema(schema_path, normalized_table_names):
    """Full schema.json entries (not just column names) for the given tables."""
    schema = _load_schema_json(schema_path)
    if schema is None:
        return {}
    out = {}
    for entry in schema:
        table_name = entry.get("table") or entry.get("table_name")
        if table_name and table_name.lower() in normalized_table_names:
            out[table_name.lower()] = entry
    return out


def _load_table_entries(table_names, schema_path=None):
    """
    Load full table entries — columns with type/nullable/is_primary_key, plus
    table-level primary_key/foreign_keys/description — for DDL rendering, from
    schema.json (config.EMBEDDING_DIR by default). No fallback to any other
    schema — a table missing from the active schema simply has no entry.
    """
    if schema_path is None:
        schema_path = f"{config.EMBEDDING_DIR}/schema.json"

    normalized = {name.lower() for name in table_names}
    return _table_entries_from_schema(schema_path, normalized)


_ddl_type_cache = None


def _load_ddl_types(ddl_path="data/schema.sql"):
    """
    {table_lower: {column_lower: "NUMBER(20,2)"}} parsed from the checked-in DDL.

    schema.json files built before types were preserved have no `type` field, so
    this is the authoritative fallback — it is Oracle-derived (extract_schema.py
    writes it from ALL_TAB_COLUMNS) rather than guessed. It matters: CODE is
    NUMBER(20,2) in this schema, so a generated `CODE = 'BANK'` is a type error,
    and without types in the prompt nothing told the model that.
    """
    global _ddl_type_cache
    if _ddl_type_cache is not None:
        return _ddl_type_cache

    types = {}
    try:
        from src.ddl_parser import parse_sql_schema
        with open(ddl_path, encoding="utf-8", errors="replace") as fh:
            for table, cols in parse_sql_schema(fh.read()).items():
                types[table.lower()] = {
                    c["name"].lower(): (c.get("type") or "").upper() for c in cols
                }
    except (OSError, ImportError) as e:
        log.warning("Could not load column types from %s: %s", ddl_path, e)

    _ddl_type_cache = types
    return types


# Last-resort type inference, used only when neither schema.json nor the DDL
# file knows the column. A CREATE TABLE block with no types would be worse than
# a guessed one: SQLCoder relies on the type to decide between TO_DATE, string
# literals and arithmetic.
_TYPE_HINTS = (
    (("rdate", "_date", "date_", "dt_"), "DATE"),
    (("code",), "VARCHAR2(50)"),
    (("amt", "amount", "total", "value", "val", "num", "count", "qty",
      "os", "exposure", "expo", "provision", "ratio", "per_", "pct"), "NUMBER(20,2)"),
)


def _infer_column_type(column_name: str) -> str:
    lowered = column_name.lower()
    for needles, sql_type in _TYPE_HINTS:
        if any(n in lowered for n in needles):
            return sql_type
    return "VARCHAR2(400)"


def _get_model_profile(model_name):
    default_profile = {
        "prompt_style": "rules",
        "dialect_hint": "Oracle",
        "temperature": None,
        "num_predict": None,
    }
    profile = config.MODEL_PROFILES.get(model_name, {})
    return {**default_profile, **profile}


def _validation_failure_category(reason: str) -> str:
    reason = reason.lower()
    if "oracle rejected the query" in reason:
        return "engine rejected"
    if "undeclared join" in reason:
        return "undeclared join"
    if "dangerous keyword" in reason:
        return "banned keyword"
    if "hallucinated tables" in reason:
        return "hallucinated table"
    if "column/table mismatch" in reason:
        return "alias/table mismatch"
    if "hallucinated columns" in reason:
        return "hallucinated column"
    if "does not reference any matched table" in reason:
        return "schema grounding"
    if reason.strip() == "empty sql":
        return "empty sql"
    return "unknown validation"


HALLUCINATION_LOG_PATH = "eval/results/hallucination_log.jsonl"


def _log_hallucination(user_query, tables, model_name, first_attempt_sql, first_attempt_reason,
                        retry_sql, retry_reason, category):
    """
    Append every generation that's STILL invalid after the retry to a JSONL
    log, so hallucination patterns (which category, which tables, whether the
    retry made it better/worse/no-different) can be analyzed in aggregate
    instead of diagnosed one pasted error at a time.
    """
    import os
    try:
        os.makedirs(os.path.dirname(HALLUCINATION_LOG_PATH), exist_ok=True)
        record = {
            "question": user_query,
            "matched_tables": [t.get("table") for t in tables],
            "model": model_name,
            "final_category": category,
            "first_attempt_sql": first_attempt_sql,
            "first_attempt_reason": first_attempt_reason,
            "retry_sql": retry_sql,
            "retry_reason": retry_reason,
            "retry_changed_sql": first_attempt_sql != retry_sql,
        }
        with open(HALLUCINATION_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except OSError as e:
        print(f"[WARNING] Could not write hallucination log: {e}")


def _build_full_rules_block(dialect_hint: str) -> str:
    return f"""You are an expert {dialect_hint} SQL generator.
Use {dialect_hint} syntax, including Oracle-specific constructs such as FETCH FIRST N ROWS ONLY, ADD_MONTHS, EXTRACT(YEAR FROM ...), and TO_DATE(...,'YYYY-MM-DD').

════════════════════════════════════════════════
ABSOLUTE RULES (never break these)
════════════════════════════════════════════════
1. Return ONLY a raw SQL SELECT query — no explanation, no markdown, no code fences, no semicolon.
2. Use ONLY table names and column names listed in the SCHEMA CONTEXT below. Never invent names.
3. Never use bind variables or placeholders (:val, ?, %s). Embed all values as literals.
4. Never touch backup tables (_bkup, _bk, _bckup, _backup suffixes). Use only the main tables.
5. This is Oracle SQL only. Never use ILIKE, ~*, or any other non-Oracle operator (those
   belong to PostgreSQL/MySQL). For case-insensitive matching use UPPER(col) LIKE UPPER('%...%')
   instead; prefer an exact literal match from the schema's row-label values whenever one exists.

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
  Never skip the WHERE clause on a vertical table.

RULE V3 — To get a SPECIFIC metric:
  Use WHERE <label_col> = '<exact value from Known row labels list>'
  Match the label value CHARACTER FOR CHARACTER — case, spaces, dots, brackets all matter.

RULE V4 — LIKE fallback (use ONLY when no exact match is available):
  If the value you need is NOT listed in the Known row labels, use:
    WHERE <label_col> LIKE '%keyword%'
  NEVER invent or guess an exact string — use LIKE if uncertain.

RULE V5 — You MAY use SUM/AVG only when:
  (a) The table is NOT tagged VERTICAL, OR
  (b) You are aggregating across CODE or RDATE partitions on a non-label column
      (e.g. total across all bank codes: SUM(col) GROUP BY RDATE on a non-vertical table).

════════════════════════════════════════════════
DOM / OVE COLUMN RULES  (Domestic + Overseas)
════════════════════════════════════════════════
Many tables store the same metric in two separate columns:
  <col>_DOM  → domestic value
  <col>_OVE  → overseas value

RULE D1 — When the user asks for "total", "combined", "overall", or does NOT specify
  domestic/overseas, add both columns:
    SELECT (EXPOSURE_DOM + EXPOSURE_OVE) AS TOTAL_EXPOSURE ...

RULE D2 — When the user asks for "domestic only" → use <col>_DOM alone.
  When the user asks for "overseas only"  → use <col>_OVE alone.

RULE D3 — When comparing domestic vs overseas, select both columns separately:
    SELECT CODE, RDATE, EXPOSURE_DOM, EXPOSURE_OVE FROM ...

RULE D4 — Do NOT invent a column named TOTAL_<x>; compute it inline as (<col>_DOM + <col>_OVE).

════════════════════════════════════════════════
MULTI-PART / MULTI-SECTION RULES
════════════════════════════════════════════════
Some sections split their data across multiple sibling tables
(e.g. SEC1_PART_A_DOM and SEC1_PART_B_DOM, or SEC9_SENSEC_PARTA and SEC9_SENSEC_PARTB).
Part A typically covers one loan/asset category; Part B covers another.

RULE M1 — If the user asks for a COMBINED / OVERALL total that spans multiple parts of the
  SAME section, use a UNION ALL subquery and then SUM the result:

  EXAMPLE — "total gross NPA across Part A and Part B of SEC1":
    SELECT SUM(val) AS TOTAL_GROSS_NPA
    FROM (
      SELECT GROSS_NPA_END AS val FROM CIMS_RAQ_Q_SEC1_PART_A_DOM
        WHERE PERIOD_DELINQUENCY = '<total row label>'
      UNION ALL
      SELECT GROSS_NPA_END AS val FROM CIMS_RAQ_Q_SEC1_PART_B_DOM
        WHERE PERIOD_DELINQUENCY = '<total row label>'
    )

RULE M2 — Use UNION ALL (not UNION) to preserve all rows including duplicates.

RULE M3 — When the user only mentions one part explicitly (e.g. "Part A"), query ONLY that
  part — do NOT union with other parts.

RULE M4 — When unioning vertical tables, apply the SAME label WHERE filter in each branch.
  Never union without label filters on vertical tables.

RULE M5 — When the same metric exists across multiple sections (e.g. NPA in SEC1 and SEC3),
  use UNION ALL with a literal section tag column so the user can distinguish results:
    SELECT 'SEC1' AS section, NPA_AMT FROM CIMS_RAQ_Q_SEC1_PART_A_DOM WHERE ...
    UNION ALL
    SELECT 'SEC3' AS section, NPA_AMT FROM CIMS_RAQ_Q_SEC3_DETAILS WHERE ...

════════════════════════════════════════════════
JOIN RULES
════════════════════════════════════════════════
RULE J1 — Use JOINs ONLY when the user question requires data from multiple tables.
RULE J2 — Always join on CODE and RDATE together to avoid cross-joining reporting periods.
RULE J3 — For optional/possibly-missing rows use LEFT JOIN, not INNER JOIN.
RULE J4 — Never JOIN a main table with its own backup table.
RULE J5 — When joining two vertical tables, apply the WHERE label filter on BOTH sides.

EXAMPLE JOIN:
  User: "compare industry NPA vs infra NPA"
  RIGHT:
    SELECT i.INDUSTRY_NAME, i.GROSS_NPA_END AS industry_npa, r.GROSS_NPA_END AS infra_npa
    FROM CIMS_RAQ_Q_SEC8_IND_BRKUP i
    LEFT JOIN CIMS_RAQ_Q_SEC8_INFRA_BRKUP r
      ON i.CODE = r.CODE AND i.RDATE = r.RDATE AND i.INDUSTRY_NAME = r.INDUSTRY_NAME

════════════════════════════════════════════════
MULTI-CODE / BANK RULES
════════════════════════════════════════════════
RULE B1 — Column CODE identifies the reporting bank/entity. If user does not specify a bank, omit CODE filter.
RULE B2 — If user asks for a specific bank, filter WHERE CODE = <bank_code>.

════════════════════════════════════════════════
DATE & PERIOD RULES
════════════════════════════════════════════════
RULE P1 — RDATE is the reporting date column. Use it for all date-based filtering.

RULE P2 — "Latest" / "most recent" / "current" → use a subquery:
    WHERE RDATE = (SELECT MAX(RDATE) FROM <same_table>)

RULE P3 — "Last/past/previous N quarters, months, years, FY quarters, or periods":
    If a RESOLVED TIME CONTEXT block appears below with a matching entry, use those
    EXACT dates verbatim — do not recompute them yourself.
    For "last N periods" specifically (where period = one reporting row, not a fixed
    calendar span), use the RDATE IN (SELECT DISTINCT RDATE ... ORDER BY RDATE DESC
    FETCH FIRST N ROWS ONLY) pattern shown in that block, NOT a date range.
    Only if no RESOLVED TIME CONTEXT entry covers the phrase, fall back to:
    WHERE RDATE >= ADD_MONTHS((SELECT MAX(RDATE) FROM <same_table>), -<N*3 for quarters, -N for months>)

RULE P4 — "For year YYYY" → filter with:
    WHERE EXTRACT(YEAR FROM RDATE) = YYYY

RULE P5 — "Between <date1> and <date2>" → filter with:
    WHERE RDATE BETWEEN TO_DATE('<date1>', 'YYYY-MM-DD') AND TO_DATE('<date2>', 'YYYY-MM-DD')

RULE P6 — "Trend" / "over time" / "quarter-by-quarter" → include RDATE in SELECT and GROUP BY,
    ORDER BY RDATE ASC.

RULE P7 — Never hardcode a date literal like '2024-03-31'. Always derive latest date via MAX(RDATE).

════════════════════════════════════════════════
RANKING & TOP-N RULES
════════════════════════════════════════════════
RULE R1 — "Top N" / "highest N" → use Oracle FETCH syntax:
    SELECT ... FROM ... ORDER BY <col> DESC FETCH FIRST <N> ROWS ONLY

RULE R2 — "Bottom N" / "lowest N" → ORDER BY <col> ASC FETCH FIRST <N> ROWS ONLY

RULE R3 — "Rank banks by <metric>" → use RANK() or DENSE_RANK() window function:
    SELECT CODE, <col>,
           RANK() OVER (PARTITION BY RDATE ORDER BY <col> DESC) AS rnk
    FROM ...

RULE R4 — Never use ROWNUM for top-N unless the table has no ORDER BY option; prefer FETCH FIRST.
"""


def _build_minimal_prompt(
    dialect_hint: str,
    user_query: str,
    schema_context: str,
    time_context_block: str,
    valid_tables: str,
    vertical_tables=None,
    dom_ove_tables=None,
    multipart_tables=None,
    qa_example=None,
    business_block=None,
    business_rules=None,
) -> str:
    time_section = f"\n{time_context_block}" if time_context_block else ""
    business_section = (
        f"\n\n### Business semantics\n{business_block}" if business_block else ""
    )
    business_rules_section = (
        "\n" + "\n".join(business_rules) if business_rules else ""
    )
    example_blocks = []

    if qa_example:
        example_blocks.append(
            f"Example — closely matching prior question (table: {qa_example['table']}):\n"
            f"Q: {qa_example['question']}\n"
            f"SQL: {qa_example['sql']}"
        )

    if vertical_tables:
        example_blocks.append(
            "Example — vertical table:\n"
            "SELECT PERIOD_DELINQUENCY, TOTAL_LOAN_ASSETS\n"
            "FROM <table>\n"
            "WHERE PERIOD_DELINQUENCY = '<total row label>'"
        )

    if dom_ove_tables:
        example_blocks.append(
            "Example — domestic/overseas table:\n"
            "SELECT CODE, RDATE, EXPOSURE_DOM, EXPOSURE_OVE\n"
            "FROM <table>"
        )

    if multipart_tables:
        example_blocks.append(
            "Example — multi-part table:\n"
            "SELECT SUM(val) FROM (SELECT value_col AS val FROM <table_a> UNION ALL SELECT value_col AS val FROM <table_b>)"
        )

    examples_section = ""
    if example_blocks:
        examples_section = "\n\n### Few-shot examples\n" + "\n\n".join(example_blocks)

    return f"""You are an expert {dialect_hint} SQL generator.
Use {dialect_hint} syntax, including Oracle-specific constructs such as FETCH FIRST N ROWS ONLY, ADD_MONTHS, EXTRACT(YEAR FROM ...), and TO_DATE(...,'YYYY-MM-DD').

### Task
{user_query}

### Database Schema
{schema_context}

Allowed tables: {valid_tables}{time_section}{business_section}{examples_section}

### Important
- If a table is marked STORAGE FORMAT: VERTICAL, each row is a named metric and you must filter by the exact row label values shown above.
- Do NOT aggregate vertical tables with SUM() across row labels unless the user explicitly asks for an aggregation that requires it.
- When the user requests a total or overall value, use the exact total row label provided in the schema context.
- Never invent row labels or column names that are not shown in the schema context.
- Never use bind variables or placeholders (:val, ?, %s, :rdate, :bank_code, etc.) — embed every value as a literal. The query must run standalone with no parameters supplied.
- This is Oracle SQL only. Never use ILIKE, ~*, or any other non-Oracle operator (those belong to PostgreSQL/MySQL). For case-insensitive matching use UPPER(col) LIKE UPPER('%...%') instead; prefer an exact literal match from the schema's row-label values whenever one exists.
- If the user's question does NOT mention a date/period, filter with RDATE = (SELECT MAX(RDATE) FROM <same_table>) to get the latest available reporting period. Never omit the RDATE filter and never guess a hardcoded date.
- Copy every table and column name EXACTLY as spelled in the schema above, character for character. Do not alter, abbreviate, or "correct" the spelling of any identifier.
- A column such as RISK_CATEGORY, CATEGORY, ITEM, or DESCRIPTION is a plain text VALUE stored directly on the table shown above — it is NOT a separate lookup/dimension table. Never JOIN to a table that is not listed under "Allowed tables".
- "Allowed tables" is listed in relevance order — the FIRST table is the best match to the question. Several tables may be listed because they are topically similar, not because the question needs all of them. If the first table's own columns already answer the question, use ONLY that table. Only JOIN a second table when the question explicitly needs data that genuinely does not exist on the first table.{business_rules_section}

### Answer
Return ONLY a raw SQL SELECT query. No explanation, no markdown, no code fences, no semicolon.
"""


def _ddl_comment(text: str, limit: int = 90) -> str:
    """One-line trailing comment, collapsed and clipped."""
    if not text:
        return ""
    # Normalise typographic dashes/quotes to ASCII: they cost extra tokens and
    # the generated descriptions in schema.json are full of them.
    flat = str(text).translate(str.maketrans({
        "—": "-", "–": "-", "‘": "'", "’": "'",
        "“": '"', "”": '"', "…": "...",
    }))
    flat = re.sub(r"\s+", " ", flat).strip()
    if len(flat) > limit:
        flat = flat[:limit - 3].rstrip() + "..."
    return flat


def build_table_ddl(entry, label_values=None, selected_tables=None, selected_columns=None):
    """
    Render one schema.json table entry as a real CREATE TABLE block.

    SQLCoder was trained on CREATE TABLE context, so giving it DDL rather than
    the previous prose "Allowed columns (use ONLY these): A, B, C" listing plays
    to the model instead of fighting it. Types, NOT NULL and PRIMARY KEY come
    from the schema; row-label values ride along as column comments so the model
    can copy an exact literal instead of inventing one.

    A FOREIGN KEY renders only when the referenced table is also in
    `selected_tables` — a dangling REFERENCES to a table that isn't in context
    is an open invitation to join to something the model cannot see.

    `selected_columns` (lowercase names), when given, prunes the column list;
    key columns and the row-label column are always kept so the query remains
    filterable.
    """
    raw_name = entry.get("table") or entry.get("table_name") or ""
    table_name = raw_name.upper()
    label_values = label_values or {}
    label_cols = {c.lower() for c in label_values}
    keep = {c.lower() for c in (selected_columns or [])} or None
    ddl_types = _load_ddl_types().get(raw_name.lower(), {})

    lines = []
    header_desc = _ddl_comment(entry.get("description"), limit=200)
    if header_desc:
        lines.append(f"-- {header_desc}")
    if label_values:
        keyed_by = ", ".join(sorted(c.upper() for c in label_values))
        lines.append(
            f"-- STORAGE FORMAT: VERTICAL - each row is one named metric, keyed by {keyed_by}. "
            f"Filter by an exact label value below; do NOT SUM across labels."
        )

    # (definition, comment) pairs — the comma that separates column definitions
    # has to go BEFORE the trailing comment, or the `--` swallows it and the DDL
    # stops being parseable.
    col_defs = []
    pk_cols = []
    for col in entry.get("columns") or []:
        name = (col.get("name") or col.get("column_name") or "")
        if not name:
            continue
        lowered = name.lower()
        is_key = lowered in ("code", "rdate") or col.get("is_primary_key")
        if keep is not None and lowered not in keep and not is_key and lowered not in label_cols:
            continue

        if col.get("is_primary_key"):
            pk_cols.append(name.upper())

        col_type = ((col.get("type") or "").upper()
                    or ddl_types.get(lowered, "")
                    or _infer_column_type(name))
        definition = f"{name.upper()} {col_type}"
        if col.get("nullable") is False:
            definition += " NOT NULL"

        comment_bits = []
        desc = _ddl_comment(col.get("description"))
        # A description that just restates the column name adds nothing.
        if desc and desc.lower() not in (lowered, lowered.replace("_", " ")):
            comment_bits.append(desc)

        values = label_values.get(lowered) or label_values.get(name) or []
        if values:
            # Some stored values carry leading whitespace ('     C2. Slipped to
            # NPAs'). Matching those with `= 'C2. Slipped to NPAs'` fails
            # silently — zero rows, no error. So when any value in the column is
            # padded, show the trimmed literals and require TRIM() on the column,
            # which is correct for padded and unpadded values alike.
            padded = any(v != v.strip() for v in values)
            values = [v.strip() for v in values] if padded else list(values)

            total_row = _find_total_row(values)
            shown = list(values)
            if len(shown) > MAX_LABELS_DDL:
                # Trim, but never drop the pre-aggregated TOTAL row: it is the
                # one literal the model needs for "total/overall" questions.
                shown = [v for v in shown if v != total_row][:MAX_LABELS_DDL - 1]
                if total_row:
                    shown.append(total_row)
                shown.append("...")
            rendered = ", ".join(v if v == "..." else f"'{v}'" for v in shown)
            comment_bits.append(f"row label, allowed values: {rendered}")
            if padded:
                comment_bits.append(
                    f"stored values are whitespace-padded - you MUST filter with "
                    f"TRIM({name.upper()}) = '<value>'"
                )
            if total_row:
                filter_expr = f"TRIM({name.upper()})" if padded else name.upper()
                comment_bits.append(f"TOTAL row: {filter_expr} = '{total_row}'")

        col_defs.append((definition, " | ".join(comment_bits)))

    if pk_cols:
        col_defs.append((f"PRIMARY KEY ({', '.join(pk_cols)})", ""))

    allowed = {t.lower() for t in (selected_tables or [])}
    for fk in entry.get("foreign_keys") or []:
        ref_table = (fk.get("ref_table") or "").lower()
        if allowed and ref_table not in allowed:
            continue
        cols = ", ".join(c.upper() for c in fk.get("columns") or [])
        ref_cols = ", ".join(c.upper() for c in fk.get("ref_columns") or [])
        if cols and ref_table:
            ref = f"{ref_table.upper()}({ref_cols})" if ref_cols else ref_table.upper()
            col_defs.append((f"FOREIGN KEY ({cols}) REFERENCES {ref}", ""))

    lines.append(f"CREATE TABLE {table_name} (")
    rendered_defs = []
    for idx, (definition, comment) in enumerate(col_defs):
        separator = "," if idx < len(col_defs) - 1 else ""
        line = f"  {definition}{separator}"
        if comment:
            line += f"  -- {comment}"
        rendered_defs.append(line)
    lines.append("\n".join(rendered_defs))
    lines.append(");")
    lines.append(
        f"-- latest reporting period: RDATE = (SELECT MAX(RDATE) FROM {table_name})"
    )
    return "\n".join(lines)


# The subset of _build_ddl_prompt's rules that is IDENTICAL on every call to
# this model, regardless of question/table/join — moved to the very front of
# the prompt (see _build_ddl_prompt) so a serving stack that does prompt-
# prefix caching (Ollama/llama.cpp KV-cache reuse) can reuse these tokens
# across every request instead of reprocessing them from scratch each time.
# Previously this text lived inside "### Rules" near the END of the prompt,
# AFTER the per-request question and schema — meaning even though this text
# never changes, no serving stack could ever cache it, because everything
# before it already differed call to call. Pure reordering, no wording
# change: each line still maps to the same specific hallucination class noted
# where it originally lived (identifier copying, phantom lookup tables, bind
# variables, date literals, RDATE-latest default, vertical-table labels).
_STATIC_DDL_RULES = (
    "### Rules\n"
    "- Copy identifiers character for character. Do not abbreviate, pluralise or 'correct' a name.\n"
    "- A text column such as DESCRIPTION, ITEM, CATEGORY or RISK_CATEGORY holds the value directly. "
    "It is not a lookup table - never join to a table that is not declared in the schema below.\n"
    "- Never use bind variables or placeholders (:val, ?, %s). Embed every value as a literal.\n"
    "- Wrap every date literal as TO_DATE('YYYY-MM-DD', 'YYYY-MM-DD').\n"
    "- If the question names no period, filter RDATE = (SELECT MAX(RDATE) FROM <that table>).\n"
    "- On a VERTICAL table, filter by an exact row-label literal from its comment; "
    "for a total, use the TOTAL row label rather than SUM() across labels.\n"
    "- This is Oracle SQL only. Never use ILIKE, ~*, or any other non-Oracle operator "
    "(those belong to PostgreSQL/MySQL). For case-insensitive matching use "
    "UPPER(col) LIKE UPPER('%...%') instead; prefer an exact literal match from the "
    "schema's row-label values whenever one exists."
)


def _build_ddl_prompt(
    dialect_hint: str,
    user_query: str,
    ddl_context: str,
    time_context_block: str,
    valid_tables: str,
    qa_example=None,
    reasoning_plan=None,
    join_hint=None,
    business_block=None,
    business_rules=None,
) -> str:
    """
    Prompt in SQLCoder-7b-2's own training format ("### Task / ### Database
    Schema / ### Answer" with [QUESTION]…[/QUESTION] delimiters), replacing the
    prose bullet list that a 7B model demonstrably did not follow.

    Section order follows WrenAI's assembly: schema, then examples, then
    instructions, then the reasoning plan, then the question last — EXCEPT
    for the model-invariant rules text, which goes first (see
    _STATIC_DDL_RULES) so it's the one part of the prompt a prefix-caching
    serving stack could ever actually reuse across different tables/questions.
    """
    sections = [
        _STATIC_DDL_RULES,
        f"### Task\nGenerate an {dialect_hint} SQL SELECT query to answer "
        f"[QUESTION]{user_query}[/QUESTION]",
        "### Database Schema\nThe query will run on a database with the following schema:\n"
        + ddl_context,
    ]

    # After the schema (so the columns are already established) and before the
    # worked example (which stays closest to the completion point). This block
    # carries the facts the DDL cannot express: the reporting unit, whether a
    # figure is a stock or a flow, and which CODE selects which reported row.
    if business_block:
        sections.append("### Business semantics\n" + business_block)

    if time_context_block:
        sections.append(time_context_block.strip())

    if qa_example:
        sections.append(
            "### Worked example\n"
            f"-- table: {qa_example['table']}\n"
            f"-- question: {qa_example['question']}\n"
            f"{qa_example['sql']}"
        )

    # Per-request rules only — the model-invariant bullets that used to live
    # here moved to _STATIC_DDL_RULES at the front of the prompt (see there).
    # Kept under a distinct header (not "### Rules" again) since these lines
    # genuinely vary call to call and can never be part of a cached prefix.
    rules = [
        f"- Use only the tables and columns declared in the schema above. Allowed tables: {valid_tables}.",
    ]
    if join_hint:
        rules.append(f"- {join_hint}")
    else:
        rules.append(
            "- Answer from the single table above. Do not join."
        )
    rules.extend(business_rules or [])
    sections.append("### Query-specific constraints\n" + "\n".join(rules))

    if reasoning_plan:
        sections.append("### Reasoning plan\n" + reasoning_plan.strip())

    sections.append(
        "### Answer\nGiven the database schema, here is the "
        f"{dialect_hint} SQL query that answers [QUESTION]{user_query}[/QUESTION]\n"
        "Return only the raw SQL - no explanation, no markdown, no semicolon.\n[SQL]"
    )

    return "\n\n".join(sections) + "\n"


# Keywords in row-label values that indicate a pre-aggregated total row
_TOTAL_ROW_KEYWORDS = [
    "total", "grand total", "sub-total", "subtotal",
    "all industries", "c. total", "c total", "grand-total",
    "i. gross", "iii. non-food", "ii. food",
]


def _find_total_row(values: list) -> str | None:
    """Return the first value in the list that looks like a total/grand-total row."""
    for v in values:
        vl = v.lower()
        if any(kw in vl for kw in _TOTAL_ROW_KEYWORDS):
            return v
    return None


def _try_autocorrect_vertical_aggregation(sql: str, reason: str):
    """
    Deterministic last-resort fix for the ONE failure mode observed to
    survive even a targeted retry: validate_sql's "is a vertical table" rule
    already tells the model the exact WHERE clause to add (it's in the retry
    prompt verbatim), but a small/quantized model can still ignore it twice
    in a row. Rather than gamble on a third LLM call repeating the same
    instruction, mechanically rewrite the query — but ONLY for this one
    narrow, unambiguous pattern: a single aggregate, over a single table,
    with a single confidently-known total-row label. Returns corrected SQL,
    or None if anything is ambiguous (never guesses a rewrite).
    """
    m = re.match(r'^Table (\S+) is a vertical table \(each row is a named metric via (\S+),', reason)
    if not m:
        return None
    table_name, label_col = m.group(1), m.group(2)

    # Only safe to rewrite a genuinely single-table query — a JOIN means the
    # aggregate could legitimately need to span rows from another table.
    table_refs = set(re.findall(r'\b(?:from|join)\s+([a-zA-Z_][a-zA-Z0-9_]*)', sql, re.IGNORECASE))
    if len(table_refs) != 1:
        return None

    label_samples = {k.lower(): v for k, v in load_samples().items()}
    values = label_samples.get(table_name.lower(), {}).get(label_col.lower())
    if not values:
        return None
    total_row = _find_total_row(values)
    if not total_row:
        return None

    # Must be exactly ONE aggregate call over exactly ONE non-RDATE/CODE
    # column — more than one, or an aggregate wrapping an expression rather
    # than a plain column, is left alone rather than risk mangling it.
    agg_matches = list(re.finditer(
        r'\b(sum|avg|count|min|max)\s*\(\s*((?:[a-zA-Z_][a-zA-Z0-9_]*\.)?[a-zA-Z_][a-zA-Z0-9_]*)\s*\)',
        sql, re.IGNORECASE,
    ))
    metric_aggs = [mm for mm in agg_matches if mm.group(2).split('.')[-1].lower() not in ("rdate", "code")]
    if len(metric_aggs) != 1:
        return None
    agg = metric_aggs[0]

    corrected = sql[:agg.start()] + agg.group(2) + sql[agg.end():]

    # A padded stored value must be compared through TRIM(), otherwise the
    # rewritten query returns zero rows instead of the total.
    if total_row != total_row.strip():
        escaped_total = total_row.strip().replace("'", "''")
        where_clause = f"TRIM({label_col}) = '{escaped_total}'"
    else:
        escaped_total = total_row.replace("'", "''")
        where_clause = f"{label_col} = '{escaped_total}'"
    if re.search(r'\bwhere\b', corrected, re.IGNORECASE):
        corrected = re.sub(r'\bwhere\b', f"WHERE {where_clause} AND", corrected, count=1, flags=re.IGNORECASE)
    else:
        corrected = corrected.rstrip() + f" WHERE {where_clause}"

    return corrected


def build_prompt(user_query, tables, columns, dialect="Oracle", today_date=None, matched_labels=None,
                 model_name=None, qa_example=None, selection=None, reasoning_plan=None):
    if today_date is None:
        today_date = date.today().isoformat()

    if model_name is None:
        model_name = config.OLLAMA_MODEL
    profile = _get_model_profile(model_name)
    dialect_hint = profile.get("dialect_hint") or dialect
    prompt_style = profile.get("prompt_style", "rules")

    table_names = {t["table"] for t in tables}
    all_columns = _load_all_columns(table_names)

    # ── Build per-table label lookup from matched_labels (L2 embeddings) ──────
    # matched_labels: [{table, column, value}, ...]  — already ranked by relevance
    # Fall back to full sample dump if index doesn't exist yet (e.g. first run).
    if matched_labels is None:
        raw_samples = load_samples()
        matched_labels = []
        for tbl, col_map in raw_samples.items():
            for col, vals in col_map.items():
                for v in vals:
                    matched_labels.append({"table": tbl, "column": col, "value": v})

    # Group matched labels by (table, column) for easy lookup in prompt builder
    from collections import defaultdict
    label_map = defaultdict(lambda: defaultdict(list))  # label_map[table][col] = [val, …]
    for lbl in matched_labels:
        table_name = lbl["table"]
        column_name = lbl["column"]
        if prompt_style == "minimal":
            if len(label_map[table_name][column_name]) < MAX_LABELS_MINIMAL:
                label_map[table_name][column_name].append(lbl["value"])
        else:
            label_map[table_name][column_name].append(lbl["value"])

    # ── Supplement with ALL known samples for matched tables ──────────────────
    # Semantic search only returns top-K matches keyed on embedding similarity
    # to the free-form question — for a vague query like "show total loan"
    # that never mentions a specific row-label wording, it can return ZERO
    # matches even though the table is genuinely vertical, which silently
    # drops the "STORAGE FORMAT: VERTICAL" / total-row warning from the
    # prompt and lets the model fall back to a naive SUM() across all rows
    # (double-counting the pre-aggregated total row). So this fallback must
    # run for EVERY prompt style, not just "rules" — whether a table needs a
    # row-label filter is a schema-shape fact, not something that should
    # depend on how verbose the prompt is allowed to be.
    all_samples = load_samples()
    for tbl in table_names:
        if tbl in all_samples:
            for col, vals in all_samples[tbl].items():
                existing = set(label_map[tbl][col])
                for v in vals:
                    if v not in existing:
                        label_map[tbl][col].append(v)
                if prompt_style == "minimal" and len(label_map[tbl][col]) > MAX_LABELS_MINIMAL:
                    # Keep the prompt concise for small-context models, but never
                    # let truncation drop the pre-aggregated TOTAL row — without
                    # it, RULE V2 ("use WHERE <label> = '<TOTAL ROW>'") has
                    # nothing to point at and the model has no way to satisfy it.
                    total_row = _find_total_row(label_map[tbl][col])
                    kept = [v for v in label_map[tbl][col] if v != total_row][:MAX_LABELS_MINIMAL - 1]
                    if total_row:
                        kept.append(total_row)
                    label_map[tbl][col] = kept

    vertical_tables = set()
    dom_ove_tables = set()
    multipart_tables = set()
    for t in tables:
        table_name = t["table"]
        table_upper = table_name.upper()
        if table_name in label_map and label_map[table_name]:
            vertical_tables.add(table_name)
        if any(re.search(r'(_dom|_ove)\b', c["column"].upper()) for c in all_columns if c["table"].upper() == table_upper):
            dom_ove_tables.add(table_name)
        if re.search(r'_part_[ab](?:_|$)', table_name.lower()):
            multipart_tables.add(table_name)

    schema_lines = []
    for t in tables:
        table_name = t["table"].upper()
        table_cols = [c["column"].upper() for c in all_columns if c["table"].upper() == table_name]
        cols_str = ", ".join(table_cols) if table_cols else "(none)"
        block = f"Table: {table_name}\nAllowed columns (use ONLY these): {cols_str}"

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
    valid_tables = ", ".join(t["table"].upper() for t in tables)

    # ── XBRL business semantics (units, stock/flow, CODE meaning, dimensions) ──
    # Rendered per table because the reporting unit is a per-table fact. In the
    # normal case the selector has already narrowed to one table, so this is one
    # block with no table prefix; the prefix only appears for a declared join.
    from src.business_semantics import build_block, build_rules
    business_blocks, business_rules = [], []
    for t in tables:
        tname = t["table"].upper()
        blk = build_block(user_query, tname, label_map.get(t["table"], {}))
        if blk:
            business_blocks.append(blk if len(tables) == 1 else f"{tname}:\n{blk}")
        for r in build_rules(tname):
            if r not in business_rules:
                business_rules.append(r)
    business_block = "\n".join(business_blocks)

    today_obj = date.fromisoformat(today_date) if isinstance(today_date, str) else today_date
    _time_block = _resolve_relative_time(user_query, today_obj)
    time_context_block = (_time_block + "\n") if _time_block else ""

    if prompt_style == "ddl":
        entries = _load_table_entries(table_names)
        selected_cols_by_table = {}
        join_hint = None
        if selection:
            for sel in selection.get("tables") or []:
                sel_name = str(sel.get("table", "")).lower()
                cols = [c.get("name", "") for c in (sel.get("columns") or []) if c.get("name")]
                if sel_name and cols:
                    selected_cols_by_table[sel_name] = cols
            join_hint = selection.get("join_hint")

        ddl_blocks = []
        for t in tables:
            table_key = t["table"].lower()
            entry = entries.get(table_key)
            if entry is None:
                # No schema.json entry (shouldn't happen once the build is in
                # sync) — fall back to the plain column list rather than emitting
                # a CREATE TABLE with no columns at all.
                cols = [c["column"].upper() for c in all_columns if c["table"].lower() == table_key]
                ddl_blocks.append(
                    f"-- schema entry missing; columns only\nCREATE TABLE {t['table'].upper()} (\n"
                    + ",\n".join(f"  {c} {_infer_column_type(c)}" for c in cols)
                    + "\n);"
                )
                continue
            ddl_blocks.append(build_table_ddl(
                entry,
                label_values=label_map.get(t["table"], {}),
                selected_tables=table_names,
                selected_columns=selected_cols_by_table.get(table_key),
            ))

        return _build_ddl_prompt(
            dialect_hint,
            user_query,
            "\n\n".join(ddl_blocks),
            time_context_block,
            valid_tables,
            qa_example=qa_example,
            reasoning_plan=reasoning_plan,
            join_hint=join_hint,
            business_block=business_block,
            business_rules=business_rules,
        )

    if prompt_style == "minimal":
        return _build_minimal_prompt(
            dialect_hint,
            user_query,
            schema_context,
            time_context_block,
            valid_tables,
            vertical_tables=vertical_tables,
            dom_ove_tables=dom_ove_tables,
            multipart_tables=multipart_tables,
            qa_example=qa_example,
            # compact=True on the minimal style: cap at the aggregation level so
            # a small-context model still gets units + stock/flow without the
            # dimension and derivation lines.
            business_block="\n".join(
                blk for blk in (
                    build_block(user_query, t["table"].upper(),
                                label_map.get(t["table"], {}), compact=True)
                    for t in tables
                ) if blk
            ),
            business_rules=business_rules,
        )

    # Only the "rules" style reaches here, and every profile that selects it also
    # sets supports_full_ruleset=True (as does the default profile), so the full
    # block is the single remaining template. The compressed variant it used to
    # fall back to was unreachable for every configured model and was removed.
    template = _build_full_rules_block(dialect_hint)

    qa_example_block = ""
    if qa_example:
        qa_example_block = f"""
════════════════════════════════════════════════
CLOSEST MATCHING PRIOR EXAMPLE (table: {qa_example['table']}) — follow this pattern
════════════════════════════════════════════════
Q: {qa_example['question']}
SQL: {qa_example['sql']}
"""

    business_semantics_block = ""
    if business_block:
        business_semantics_block = f"""
════════════════════════════════════════════════
BUSINESS SEMANTICS
════════════════════════════════════════════════
{business_block}
{chr(10).join(business_rules)}
"""

    return f"""{template}
════════════════════════════════════════════════
SCHEMA CONTEXT
════════════════════════════════════════════════
{schema_context}
{business_semantics_block}{qa_example_block}
════════════════════════════════════════════════
Allowed tables: {valid_tables}
{time_context_block}User question: {user_query}
════════════════════════════════════════════════
SQL:"""

def generate_sql(user_query, tables, columns, dialect="Oracle", today_date=None, matched_labels=None,
                 qa_example=None, selection=None, reasoning_plan=None):
    prompt = build_prompt(user_query, tables, columns, dialect=dialect, today_date=today_date,
                          matched_labels=matched_labels, qa_example=qa_example,
                          selection=selection, reasoning_plan=reasoning_plan)
    model_name = config.OLLAMA_MODEL
    model_profile = _get_model_profile(model_name)

    table_names = [str((t.get("table") or t.get("table_name") or "")).strip() for t in tables]
    needs_multi_part_output = any(re.search(r'_part_[ab](?:_|$)', name.lower()) for name in table_names if name)
    effective_num_predict = model_profile.get("num_predict")
    if model_profile.get("prompt_style") in ("minimal", "ddl") and needs_multi_part_output:
        effective_num_predict = max(effective_num_predict or 0, config.MINIMAL_MULTIPART_NUM_PREDICT)

    def _call_ollama(prompt_text: str, temperature_override=None, call_label="call"):
        payload = {
            "model": model_name,
            "prompt": prompt_text,
            "stream": True,   # stream tokens as they arrive
            # Keep the model resident between requests; without this the first
            # call after Ollama's 5-minute idle timeout pays a full model load.
            "keep_alive": config.OLLAMA_KEEP_ALIVE,
        }
        options = {"num_ctx": config.OLLAMA_NUM_CTX}
        if temperature_override is not None:
            options["temperature"] = temperature_override
        elif model_profile.get("temperature") is not None:
            options["temperature"] = model_profile["temperature"]
        if effective_num_predict is not None:
            options["num_predict"] = effective_num_predict
        payload["options"] = options

        global _ollama_outage_until
        _call_started = time.perf_counter()

        _now = time.monotonic()
        if _now < _ollama_outage_until:
            remaining = round(_ollama_outage_until - _now, 1)
            log.warning(
                "Ollama circuit breaker OPEN — skipping call, retrying in %ss (url=%s)",
                remaining, config.OLLAMA_URL,
            )
            raise RuntimeError(
                f"Ollama proxy at {config.OLLAMA_URL} was unreachable {round(_OLLAMA_OUTAGE_COOLDOWN_S - remaining, 1)}s ago "
                f"— skipping retry for {remaining}s to avoid hanging every request during an outage."
            )

        try:
            response = requests.post(
                config.OLLAMA_URL, json=payload,
                timeout=(_OLLAMA_CONNECT_TIMEOUT_S, 300),  # (connect, read) — fail fast if unreachable
                stream=True,
            )
            response.raise_for_status()
            _ollama_outage_until = 0.0  # connection succeeded — clear any stale outage marker
        except (requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError) as e:
            _ollama_outage_until = time.monotonic() + _OLLAMA_OUTAGE_COOLDOWN_S
            log.error("Ollama unreachable at %s (connect failure): %s", config.OLLAMA_URL, e)
            raise RuntimeError(
                f"Cannot connect to Ollama at {config.OLLAMA_URL}. Make sure it is running/reachable."
            )
        except requests.exceptions.ReadTimeout as e:
            log.error("Ollama timed out at %s after connecting: %s", config.OLLAMA_URL, e)
            raise RuntimeError(
                "Ollama timed out (300s) after connecting successfully. Try a smaller/faster model in config.py."
            )
        except requests.exceptions.HTTPError as e:
            log.error("Ollama HTTP error at %s: %s", config.OLLAMA_URL, e)
            raise RuntimeError(f"Ollama API error: {e}")
        _connect_ms = round((time.perf_counter() - _call_started) * 1000, 1)

        print("  ", end="", flush=True)
        raw = ""
        token_count = 0
        _ttft_ms = None
        _final_chunk = {}
        for line in response.iter_lines():
            if not line:
                continue
            chunk = json.loads(line)
            token = chunk.get("response", "")
            if token and _ttft_ms is None:
                # Time-to-first-token: separates prompt processing (prefill —
                # everything before this) from decoding (everything after).
                # `connect_ms` above is just TCP+headers and says nothing
                # about model speed; without TTFT, a slow call's entire cost
                # is one opaque `total_ms` number that could equally mean
                # "huge prompt, slow prefill" or "tiny response, slow decode
                # (CPU inference)" — two different fixes.
                _ttft_ms = round((time.perf_counter() - _call_started) * 1000, 1)
            if token:
                token_count += 1
            print(token, end="", flush=True)
            raw += token
            if chunk.get("done"):
                _final_chunk = chunk
                break
        print()
        total_ms = round((time.perf_counter() - _call_started) * 1000, 1)
        ttft_ms = _ttft_ms if _ttft_ms is not None else total_ms
        decode_s = (total_ms - ttft_ms) / 1000
        # tokens/sec is the standard CPU-vs-GPU inference signal: single
        # digits strongly indicates CPU-only serving or a contended GPU;
        # tens-to-hundreds indicates a healthy dedicated GPU. token_count - 1
        # excludes the token that produced TTFT itself from the decode-rate
        # window, but guard against token_count <= 1 (e.g. empty response).
        tokens_per_sec = round((token_count - 1) / decode_s, 1) if token_count > 1 and decode_s > 0 else None

        # Ollama's own server-side breakdown, carried on the final ("done":
        # true) chunk, in nanoseconds. This is authoritative — unlike every
        # timing above, which is inferred from OUR side of the wire and can't
        # actually tell model-load time, prompt-eval (prefill) time, and
        # generation time apart. A slow call with a small ollama_load_ms and
        # a large ollama_prompt_eval_ms is a prompt-size problem (fixable
        # here); a large ollama_load_ms means the model is being reloaded
        # every call (a keep_alive/host/proxy problem, not a prompt problem).
        # .get(...) with None defaults so an older Ollama/proxy that omits
        # these fields degrades to "unknown" instead of a KeyError.
        def _ns_to_ms(ns):
            return round(ns / 1e6, 1) if isinstance(ns, (int, float)) else None

        ollama_load_ms = _ns_to_ms(_final_chunk.get("load_duration"))
        ollama_prompt_eval_ms = _ns_to_ms(_final_chunk.get("prompt_eval_duration"))
        ollama_prompt_tokens = _final_chunk.get("prompt_eval_count")
        ollama_eval_ms = _ns_to_ms(_final_chunk.get("eval_duration"))

        # Prompt length correlates with time-to-first-token on a remote proxy —
        # log it alongside timing so a slow call can be attributed to network/
        # model latency vs. an oversized prompt, instead of staying a mystery.
        print(f"[TIMING] ollama {call_label}: connect={_connect_ms}ms ttft={ttft_ms}ms "
              f"total={total_ms}ms tokens={token_count} tokens_per_sec={tokens_per_sec} "
              f"ollama_load_ms={ollama_load_ms} ollama_prompt_eval_ms={ollama_prompt_eval_ms} "
              f"ollama_prompt_tokens={ollama_prompt_tokens} ollama_eval_ms={ollama_eval_ms} "
              f"prompt_chars={len(prompt_text)} response_chars={len(raw)}")
        return raw

    print(f"[DEBUG] Ollama model={model_name} prompt_style={model_profile.get('prompt_style')}")
    raw = _call_ollama(prompt, call_label="first_attempt")

    # Strip markdown fences if present
    raw = re.sub(r'^```(?:sql)?\s*', '', raw.strip(), flags=re.IGNORECASE)
    raw = re.sub(r'```\s*$', '', raw).strip()
    # Oracle driver rejects trailing semicolons
    raw = raw.rstrip().rstrip(";")

    # Two-layer check, run after every attempt: the regex validator catches what
    # it can see statically, then Oracle is asked to parse and plan the statement.
    # The dry run is what catches ORA-00904 for a plausible-but-absent column and
    # ORA-01861 for a string compared to a DATE — errors no regex can detect. It
    # returns ok when the DB is unreachable, so an outage degrades to the old
    # behaviour instead of failing every query.
    # Imported lazily so sql_generator stays importable (for prompt building and
    # offline tests) on machines without the Oracle driver configured.
    from src.executor import dry_run_sql

    def _check(candidate_sql):
        ok, why = validate_sql(candidate_sql, tables, columns)
        if not ok:
            return False, why
        engine_ok, engine_error = dry_run_sql(candidate_sql)
        if not engine_ok:
            return False, f"Oracle rejected the query: {engine_error}"
        if engine_error:
            log.info("Dry run unavailable: %s", engine_error)
        return True, "Valid"

    is_valid, reason = _check(raw)
    warnings = []
    first_attempt_sql, first_attempt_reason = raw, reason

    # The retry prompt lists ALL columns of the selected tables, not just the
    # retrieved ones. The old version passed `columns` (the retrieval subset)
    # while the validator checked the full schema, so a retry could be told a
    # perfectly valid column did not exist.
    all_table_columns = _load_all_columns([t["table"] for t in tables])
    valid_tables_str = ", ".join(t["table"].upper() for t in tables)
    valid_cols_str = ", ".join(
        f"{c['table'].upper()}.{c['column'].upper()}" for c in all_table_columns
    )

    base_temp = model_profile.get("temperature")
    # Temperature is 0.0 for deterministic generation, so resending the same
    # prompt reproduces the identical wrong answer — but pushing it too high
    # (tried 0.4) let a weak 7B model wander into pure fabrication instead of
    # correcting itself. Keep the nudge small and constant across rounds.
    retry_temp = 0.15 if base_temp is not None and base_temp <= 0.05 else base_temp
    # Reserved for the LAST retry round only (see below) — the model has
    # already had two attempts at the safe, information-only retry prompt by
    # then, so a small additional nudge is scoped to the one round that was
    # already heading for failure anyway, rather than broadly re-attempting
    # the flat 0.4 this codebase already tried and rejected.
    FINAL_ROUND_TEMP_BUMP = 0.1

    # Failed-attempt memory: without this, each retry round is rebuilt purely
    # from the CURRENT raw/reason, so if the model reproduces the same wrong
    # SQL on round 2 the round-3 prompt carries no new information — pure
    # wasted latency (each Ollama round costs 75-135s+ in this deployment) on
    # a guaranteed repeat of the same mistake.
    tried_sql = [raw]

    attempt = 0
    while not is_valid and attempt < MAX_CORRECTION_RETRIES:
        attempt += 1
        # Per-round timing: the caller's `llm_generation` timings_ms entry
        # covers this ENTIRE retry loop as one lump sum, so a slow first
        # attempt was indistinguishable from 3 slow retries. Logged
        # unconditionally at the end of the round (see round_t0 uses below)
        # regardless of which of the round's several exit points is taken.
        round_t0 = time.perf_counter()

        # Deterministic fix first — it is free and it targets the one failure
        # mode observed to survive a targeted retry (the vertical-table
        # aggregation rule, whose exact required WHERE clause is already in the
        # prompt verbatim and still gets ignored by a quantized model).
        corrected = _try_autocorrect_vertical_aggregation(raw, reason)
        if corrected is not None:
            corrected_valid, corrected_reason = _check(corrected)
            if corrected_valid:
                print(f"[AUTOCORRECT] Rewrote the vertical-table aggregation deterministically:\n"
                      f"  before: {raw}\n  after:  {corrected}")
                warnings.append(
                    "Auto-corrected: the model did not add the required row-label filter, "
                    "so it was rewritten deterministically instead of guessed."
                )
                raw, is_valid, reason = corrected, corrected_valid, corrected_reason
                log.info("[TIMING] retry_round=%d (autocorrect) total_ms=%.1f",
                         attempt, (time.perf_counter() - round_t0) * 1000)
                break

        extra_hint = ""
        category = _validation_failure_category(reason)
        if category == "hallucinated table":
            extra_hint = (
                "\nYou invented a table that is not in the allowed list — most likely by either "
                "misspelling an allowed table name, or by treating a plain text column (like a "
                "category/description/label column) as if it were its own lookup table. "
                "Re-read the allowed table names character by character and copy them exactly; "
                "do not JOIN to anything outside that list."
            )
        elif category == "hallucinated column":
            extra_hint = (
                "\nYou used a column name that does not exist on the table/alias you attached it to. "
                "Double-check which specific table each alias refers to before using alias.column."
            )
        elif category == "engine rejected":
            extra_hint = (
                "\nThe database itself rejected this SQL. Fix exactly what the error says — "
                "do not restructure the rest of the query."
            )

        # Failed-attempt memory: at the top of each loop iteration, `raw` (the
        # SQL about to be retried) is always the most recently appended entry
        # in tried_sql — so checking it against every EARLIER entry detects
        # whether this exact SQL already failed once before (not just last
        # round). Tell the model outright instead of silently resending an
        # equivalent prompt and hoping for a different roll. Purely additive
        # information — never removes an existing guardrail — so it cannot
        # make fabrication more likely, only less likely to repeat verbatim.
        if raw.strip() in {s.strip() for s in tried_sql[:-1]}:
            extra_hint += (
                "\nYou already tried this exact SQL in a previous attempt and it had this "
                "same problem — do not repeat it verbatim. Make a structurally different "
                "change this time, not a cosmetic one."
            )

        # Keep the retry prompt short: resending the full original prompt
        # doubles its size and can overflow the context window, which returns
        # nothing at all.
        retry_prompt = (
            "The previous SQL was invalid. Return ONLY the corrected raw SQL SELECT query "
            "(no explanation, no markdown, no semicolon).\n\n"
            f"User question: {user_query}\n\n"
            f"Allowed tables (this is the COMPLETE list — do not use, JOIN to, or invent ANY table "
            f"not in this list, including lookup/dimension tables for category or label columns):\n"
            f"{valid_tables_str}\n\n"
            f"Allowed columns (these are the ONLY columns that exist — do not invent a column name "
            f"that merely sounds plausible, such as an ID, code, or country field not listed here):\n"
            f"{valid_cols_str}\n\n"
            f"Invalid SQL:\n{raw}\n\n"
            f"Validation reason:\n{reason}{extra_hint}\n\n"
            "Corrected SQL:"
        )

        # Final-round-only temperature bump: by the last attempt, the safe
        # information-only escalation above has already had two rounds to
        # work: if the model is still stuck, the alternative is certain
        # failure anyway, so a small bounded nudge is scoped to the one round
        # where there is nothing left to lose.
        attempt_temp = retry_temp
        if attempt == MAX_CORRECTION_RETRIES and retry_temp is not None:
            attempt_temp = retry_temp + FINAL_ROUND_TEMP_BUMP

        try:
            raw = _call_ollama(retry_prompt, temperature_override=attempt_temp,
                               call_label=f"retry_{attempt}")
        except RuntimeError as e:
            # Outage or timeout mid-loop: stop retrying and report the last
            # validation reason rather than a connection error.
            log.error("Correction retry %d aborted: %s", attempt, e)
            log.info("[TIMING] retry_round=%d (aborted) total_ms=%.1f",
                     attempt, (time.perf_counter() - round_t0) * 1000)
            break

        raw = re.sub(r'^```(?:sql)?\s*', '', raw.strip(), flags=re.IGNORECASE)
        raw = re.sub(r'```\s*$', '', raw).strip()
        raw = raw.rstrip().rstrip(";")

        # Same-as-last-time early exit: the model reproduced the identical
        # SQL it was just told was invalid — every subsequent round would
        # face the exact same prompt shape with no new information, so stop
        # burning latency (75-135s+ per round observed against this backend)
        # on a guaranteed repeat instead of using up the remaining budget.
        if raw.strip() == tried_sql[-1].strip():
            is_valid, reason = _check(raw)
            log.info("Correction retry %d reproduced the identical SQL — stopping early.", attempt)
            log.info("[TIMING] retry_round=%d (duplicate) total_ms=%.1f",
                     attempt, (time.perf_counter() - round_t0) * 1000)
            break

        tried_sql.append(raw)
        is_valid, reason = _check(raw)
        if is_valid:
            print(f"[CORRECTED] Valid after retry {attempt}")
        log.info("[TIMING] retry_round=%d total_ms=%.1f", attempt,
                 (time.perf_counter() - round_t0) * 1000)

    if not is_valid:
        category = _validation_failure_category(reason)
        warning = (
            f"Model '{model_name}' generated invalid SQL; probable failure category: {category}. "
            f"Reason: {reason}"
        )
        warnings.append(warning)
        print(f"[WARNING] {warning}")
        _log_hallucination(
            user_query=user_query,
            tables=tables,
            model_name=model_name,
            first_attempt_sql=first_attempt_sql,
            first_attempt_reason=first_attempt_reason,
            retry_sql=raw,
            retry_reason=reason,
            category=category,
        )

    # Stock/flow sanity check, from the XBRL period_type. Advisory only: a
    # point-in-time balance summed across periods is wrong often enough to
    # surface and legitimate rarely enough that failing the query here would
    # spend correction rounds on SQL that is actually fine. Only runs when the
    # business layer is enabled, since that is what gates the prompt guidance the
    # model was given in the first place.
    if is_valid:
        from src.business_semantics import enabled as _bs_enabled
        if _bs_enabled():
            from src.concept_map import check_stock_aggregation
            for w in check_stock_aggregation(raw, tables):
                warnings.append(w)
                print(f"[WARNING] {w}")

    # Hallucinated-literal check. Always on (not gated by BUSINESS_SEMANTICS_LEVEL) —
    # description_samples.json's values are already unconditionally in the prompt,
    # so this check's relevance doesn't depend on that flag.
    if is_valid:
        from src.literal_validator import check_literal_validity
        for w in check_literal_validity(raw, tables):
            warnings.append(w)
            print(f"[WARNING] {w}")

    return {
        "question_understanding": "",
        "sql": raw,
        "result_columns": [],
        "visualizations": [],
        "followup_questions": [],
        "warnings": warnings,
        # Already computed above by the internal _check()/retry loop — the
        # caller (api/routes/query.py) used to call validate_sql() again on
        # this exact `raw` SQL, re-running the same regex checks for no
        # reason. Surfacing the result here lets the caller skip that.
        "is_valid": is_valid,
        "validation_reason": reason,
    }


def validate_sql(sql, tables, columns):
    """Returns (is_valid: bool, reason: str)"""
    if isinstance(sql, dict):
        sql = sql.get("sql", "")

    if not sql:
        return False, "Empty SQL"
    # Normalise: blank out string-literal contents (not just the quote marks —
    # a literal like 'Total (1 to 4)' otherwise leaves the word "total" in the
    # token stream, where the SELECT-list column scanner below mistakes it for
    # a hallucinated column reference), then lowercase.
    q = re.sub(r"'[^']*'", ' ', sql).lower()
    q = q.replace('"', '').strip()

    # 1 — must start with SELECT
    if not q.startswith("select"):
        return False, "Only SELECT queries are allowed"

    # 2 — no dangerous DML/DDL keywords (whole-word match)
    for word in BANNED_KEYWORDS:
        if re.search(rf'\b{word}\b', q):
            return False, f"Dangerous keyword detected: '{word}'"

    # 2.2 — non-Oracle operators (ILIKE, ~*, POSIX regex ~) are PostgreSQL/MySQL
    # syntax; Oracle's parser rejects them outright. Caught here as a fast,
    # DB-independent reject instead of relying solely on the Oracle EXPLAIN
    # PLAN dry run (which also catches this, but only with a live connection).
    if re.search(r'\bilike\b', q):
        return False, "Non-Oracle operator 'ILIKE' is not valid Oracle SQL — use UPPER(col) LIKE UPPER('%...%') instead"
    if re.search(r'~\*?', sql):
        return False, "Non-Oracle regex operator ('~' / '~*') is not valid Oracle SQL"

    # 2.5 — bare 'YYYY-MM-DD' string literals compared against a DATE column
    # (e.g. RDATE) pass every other check here but fail at Oracle execution
    # time with ORA-01861 "literal does not match format string", because
    # Oracle implicitly converts the string using NLS_DATE_FORMAT, not the
    # literal's own shape. Must be wrapped in TO_DATE(..., 'YYYY-MM-DD').
    # Checked on the ORIGINAL sql (quotes intact), before the quote-stripped
    # `q` normalisation above discards the evidence.
    for m in re.finditer(r"'\d{4}-\d{2}-\d{2}'", sql):
        preceding = sql[:m.start()].rstrip().lower()
        if not preceding.endswith("to_date("):
            return False, (
                f"Bare date literal {m.group(0)} must be wrapped as "
                f"TO_DATE({m.group(0)}, 'YYYY-MM-DD') — an unwrapped string "
                f"literal compared to a DATE column causes ORA-01861 at execution"
            )

    valid_table_names = {t["table"].lower() for t in tables}

    # 3 — load ALL real columns for matched tables for accurate validation
    all_columns = _load_all_columns(valid_table_names)
    valid_col_names = {c["column"].lower() for c in all_columns}

    # Collect aliases defined inside subqueries / CTEs — these are valid even
    # though they don't appear in the schema (e.g. SUM(...) AS industry_npa)
    subquery_aliases = set(re.findall(r'\bas\s+([a-z_][a-z0-9_]*)', q))
    # Also collect subquery range variables  (... ) alias_name)
    subquery_aliases |= set(re.findall(r'\)\s+([a-z_][a-z0-9_]*)\b', q))

    # 4 — every table in FROM / JOIN must be an allowed table OR a subquery alias
    # Strip EXTRACT(... FROM ...) and TRIM(... FROM ...) before scanning for
    # table references — otherwise "FROM RDATE" inside EXTRACT is mistakenly
    # treated as a table name, causing false "hallucinated table" errors.
    q_for_tables = re.sub(r'\bextract\s*\([^)]*\)', '', q)
    q_for_tables = re.sub(r'\btrim\s*\([^)]*\)', '', q_for_tables)
    referenced_tables = set(re.findall(r'(?:from|join)\s+([a-z_][a-z0-9_]*)', q_for_tables))
    real_table_refs = referenced_tables - subquery_aliases
    hallucinated_tables = real_table_refs - valid_table_names
    if hallucinated_tables:
        return False, f"Hallucinated tables (not in schema): {sorted(hallucinated_tables)}"

    # 5 — at least one allowed table must appear
    if not referenced_tables & valid_table_names:
        return False, f"Query does not reference any matched table: {sorted(valid_table_names)}"

    # 5.2 — declared-join enforcement. Every multi-table failure in
    # eval/results/hallucination_log.jsonl was an INVENTED relationship, not a
    # slightly-wrong one: `..._sec1_part_a_dom_fk`, `.id`. So a join between two
    # real tables is only allowed if the semantic layer declares that pair; a
    # prompt instruction is not enough at 7B. An empty join graph means the layer
    # has not been authored yet, in which case this check permits the pair and the
    # column checks below still apply.
    joined_tables = sorted(real_table_refs & valid_table_names)
    if len(joined_tables) > 1:
        from src.semantic_layer import load_join_graph
        join_graph = load_join_graph()
        if join_graph:
            for i, left in enumerate(joined_tables):
                for right in joined_tables[i + 1:]:
                    if tuple(sorted((left, right))) not in join_graph:
                        return False, (
                            f"Undeclared join between {left.upper()} and {right.upper()}. "
                            f"No relationship between these tables is declared in the semantic "
                            f"layer, so they must not be joined — answer from a single table."
                        )

    # 5.5 — alias-aware column check: a column name can be valid on SOME matched
    # table but still be wrong on the specific table/alias it's qualified with
    # (e.g. "b.gross_amt_os_dom" where b = SEC9_SENSEC_PARTB but that column only
    # exists on SEC9_SENSEC_PARTA). Catch that here instead of letting Oracle
    # reject it with ORA-00904 at execution time.
    columns_by_table = {}
    for c in all_columns:
        columns_by_table.setdefault(c["table"].lower(), set()).add(c["column"].lower())

    _NON_ALIAS_TOKENS = _SQL_KEYWORDS | {"on", "using"}
    alias_to_table = {}
    # Match ONLY the table name here — do not also try to capture a trailing
    # alias in the same match. Capturing it inline (the old approach) makes
    # that match's span SWALLOW the next token; in "FROM a JOIN b", the "JOIN"
    # keyword gets consumed as a's (rejected) alias, and finditer then never
    # sees "JOIN b" as a separate trigger at all — b never enters
    # alias_to_table, so every b.column reference resolves to table=None and
    # silently skips validation instead of being checked. Peeking ahead for
    # an alias without consuming it (below) keeps each "from|join <table>"
    # match to just the table name, so back-to-back joins are never merged.
    for m in re.finditer(r'\b(?:from|join)\s+([a-z_][a-z0-9_]*)', q_for_tables):
        tbl = m.group(1)
        if tbl not in valid_table_names:
            continue
        alias_to_table[tbl] = tbl
        alias_match = re.match(r'\s+(?:as\s+)?([a-z_][a-z0-9_]*)', q_for_tables[m.end():])
        if alias_match:
            alias = alias_match.group(1)
            if alias not in _NON_ALIAS_TOKENS:
                alias_to_table[alias] = tbl

    mismatched = []
    for alias, col in re.findall(r'\b([a-z_][a-z0-9_]*)\.([a-z_][a-z0-9_]*)\b', q_for_tables):
        table = alias_to_table.get(alias)
        if table is None or col in _SQL_KEYWORDS:
            continue
        if col not in columns_by_table.get(table, set()):
            mismatched.append(f"{alias}.{col} (table {table.upper()} has no such column)")

    if mismatched:
        return False, f"Column/table mismatch: {sorted(set(mismatched))}"

    # 6 — check outermost SELECT-list columns only
    select_body = re.split(r'\bfrom\b', q_for_tables, maxsplit=1)[0]
    select_body = select_body.replace("select", "", 1).strip()

    # remove aliases (AS xxx)
    select_body = re.sub(r'\bas\s+[a-z_][a-z0-9_]*', '', select_body)
    # remove aggregate / scalar functions
    select_body = re.sub(r'\b(sum|avg|min|max|count|coalesce|nvl|nullif|trim|upper|lower|to_date|to_char)\s*\(', '(', select_body)
    # remove math operators and parens
    select_body = re.sub(r'[*/+\-()\[\]]', ' ', select_body)

    col_tokens = re.findall(r'(?:[a-z_][a-z0-9_]*\.)?([a-z_][a-z0-9_]*)', select_body)

    # An UNQUALIFIED column (no table.column prefix) in a genuinely single-table
    # query (no JOIN) must belong to THAT specific table — not just to some
    # table among all matched candidates. Falling back to valid_col_names
    # (the union across every candidate table) let a column that only exists
    # on a completely different matched table (e.g. STD_FUN_ADV from
    # SEC8_INFRA_BRKUP) silently pass validation on a SEC3_PART_B-only query,
    # only to fail with ORA-00904 at the database. Qualified references
    # (alias.column) are already checked precisely by the step 5.5 logic
    # above; this closes the same gap for the unqualified, single-table case.
    if len(real_table_refs) == 1:
        only_table = next(iter(real_table_refs))
        effective_col_names = columns_by_table.get(only_table, valid_col_names)
    else:
        effective_col_names = valid_col_names

    hallucinated_cols = {
        t for t in col_tokens
        if (
            t not in effective_col_names
            and t not in _SQL_KEYWORDS
            and t not in subquery_aliases     # ← skip aliases defined in subqueries
            and t != "*"
            and not t.isdigit()
            and len(t) > 2
        )
    }

    if hallucinated_cols:
        return False, f"Hallucinated columns (not in schema): {sorted(hallucinated_cols)}"

    # 7 — vertical-table aggregation without a row-label filter. Each row in
    # a vertical table (e.g. PERIOD_DELINQUENCY on CIMS_RAQ_Q_SEC1_PART_A_DOM)
    # is a named metric, including a pre-aggregated "grand total" row —
    # SUM()/AVG()/COUNT() over the whole column double-counts that total row
    # against its own components. The prompt already tells the model this
    # (STORAGE FORMAT: VERTICAL + a matching few-shot example), but a small
    # model does not reliably follow it even when shown the exact correct
    # answer in the same prompt — so enforce it here deterministically and
    # feed a targeted correction into the existing retry path instead.
    # Only trigger on an aggregate wrapping an actual metric column — MAX(RDATE)/
    # MIN(RDATE) (the standard "latest reporting period" subquery, used
    # throughout this schema) is not the double-counting pattern this rule
    # targets and must not be flagged.
    _agg_call_cols = re.findall(
        r'\b(?:sum|avg|count|min|max)\s*\(\s*(?:[a-z_][a-z0-9_]*\.)?([a-z_][a-z0-9_]*)\s*\)', q,
    )
    _metric_aggregates = [c for c in _agg_call_cols if c not in ("rdate", "code")]
    if _metric_aggregates:
        # Different EMBEDDING_DIR scopes have been observed with different
        # table-name key casing in description_samples.json (some uppercase,
        # some lowercase) — normalise to lowercase for a reliable lookup
        # regardless of which scope is active.
        label_samples = {k.lower(): v for k, v in load_samples().items()}
        where_match = re.search(r'\bwhere\b(.*)$', q, re.DOTALL)
        where_clause = where_match.group(1) if where_match else ""
        for tbl in real_table_refs & valid_table_names:
            col_labels = label_samples.get(tbl.lower())
            if not col_labels:
                continue
            for label_col, values in col_labels.items():
                if label_col not in where_clause:
                    total_row = _find_total_row(values)
                    hint = f" e.g. WHERE {label_col.upper()} = '{total_row}'" if total_row else ""
                    return False, (
                        f"Table {tbl.upper()} is a vertical table (each row is a named metric "
                        f"via {label_col.upper()}, including a pre-aggregated total row) — "
                        f"aggregating with SUM/AVG/COUNT/MIN/MAX without filtering "
                        f"{label_col.upper()} to a specific row label double-counts the total "
                        f"row against its own components. Add a WHERE {label_col.upper()} = "
                        f"'<exact row label>' clause.{hint}"
                    )

    return True, "Valid"