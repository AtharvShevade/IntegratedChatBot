"""
Table + column selection: turn a retrieval shortlist into exactly ONE table
(or an explicitly declared join set) before the SQL model ever sees the schema.

Why this exists
---------------
Retrieval used to hand its top-3 tables straight to SQLCoder-7B. Every logged
failure in eval/results/hallucination_log.jsonl that involved multiple candidate
tables shows the same behaviour: the model JOINed all of them and fabricated a
join key to make it work (`cims_raq_q_sec7_exp_cr.cims_raq_q_sec1_part_a_dom_fk`,
`cims_raq_q_sec2_part_a.id`). A prose instruction telling it not to ("Allowed
tables is listed in relevance order... use ONLY that table") did not work at 7B.

So the fix is structural: retrieval widens for recall, this module narrows for
precision, and the SQL model receives one table. That mirrors WrenAI's
db_schema_retrieval pipeline, which pairs a coarse table search with an LLM call
that selects tables and columns and requires a reason per column.

SQLCoder cannot do this job — it is a completion model that emits only SQL. So
this uses config.SELECTOR_MODEL (an instruct model on the same Ollama proxy).

Every failure path falls back to the top-1 retrieved table, never to top-3.
"""

import json
import logging
import re

import requests

from src import config
from src.sql_generator import _load_table_entries, build_table_ddl

log = logging.getLogger("selector")

# Below this many candidates there is nothing to choose, so skip the LLM call
# entirely (WrenAI's check_using_db_schemas_without_pruning short-circuit).
MIN_CANDIDATES_FOR_LLM = 2

# When the best candidate's fused RRF score dominates the runner-up by this
# factor, retrieval is already confident and the extra call buys nothing.
DOMINANCE_RATIO = 2.0

_SELECTOR_CONNECT_TIMEOUT_S = 3
_SELECTOR_READ_TIMEOUT_S = 120


# Compact line format, used by default. JSON costs noticeably more time here:
# constrained decoding is slower per token, the braces/quotes/keys are pure
# overhead, and a reason per column can triple the output length. This format
# carries the same decisions in roughly a third of the tokens. The JSON prompt
# below is kept for models that follow schemas better than instructions.
SELECTOR_PROMPT_COMPACT = """You are a data analyst choosing which table answers a question about Indian banking regulatory returns (RBI CIMS/RAQ).

### Question
{question}

### Candidate tables
{candidates}

### Instructions
1. Choose the ONE table that can answer the question on its own.
2. Only add a second table if the question needs a column that genuinely does not exist on the first. CODE identifies the reporting entity and RDATE the reporting period.
3. Use names exactly as written above. Never name a table or column that is not listed.
4. Prefer the table whose row labels or column descriptions match the wording of the question.

### Answer
Reply with these lines and nothing else:
TABLE: <table name>
COLUMNS: <comma-separated column names needed>
WHY: <one short line>
JOIN: none
"""

SELECTOR_PROMPT_JSON = """You are a data analyst choosing which table answers a question about Indian banking regulatory returns (RBI CIMS/RAQ).

### Question
{question}

### Candidate tables
{candidates}

### Instructions
1. Choose the ONE table that can answer the question on its own.
2. Only choose a second table if the question genuinely needs a column that does not exist on the first table. If you do, state the join condition using only columns that appear in both tables (CODE and RDATE identify the reporting entity and the reporting period).
3. For every table you choose, list the columns needed to answer the question, and give a one-line reason for each column. The number of reasons must equal the number of columns.
4. Use table and column names exactly as written above. Never name a table or column that is not listed.
5. Prefer the table whose row labels or column descriptions match the wording of the question.

### Answer
Reply with JSON only, in exactly this shape:
{{"tables": [{{"table": "TABLE_NAME", "why": "one line", "columns": [{{"name": "COL", "why": "one line"}}]}}], "join": null}}

If two tables are genuinely required, set "join" to the exact condition, e.g. "a.CODE = b.CODE AND a.RDATE = b.RDATE".
"""


def _candidate_block(tables, matched_labels=None):
    """
    Render the shortlist for the selector. Uses the same DDL serializer as the
    generation prompt so the selector and the SQL writer are looking at exactly
    the same picture of the schema.
    """
    table_names = [t["table"] for t in tables]
    entries = _load_table_entries(table_names)

    label_map = {}
    for lbl in matched_labels or []:
        label_map.setdefault(lbl["table"], {}).setdefault(lbl["column"], [])
        if len(label_map[lbl["table"]][lbl["column"]]) < 6:
            label_map[lbl["table"]][lbl["column"]].append(lbl["value"])

    blocks = []
    for t in tables:
        entry = entries.get(t["table"].lower())
        if entry is None:
            continue
        blocks.append(build_table_ddl(
            entry,
            label_values=label_map.get(t["table"], {}),
            selected_tables=table_names,
        ))
    return "\n\n".join(blocks)


def _parse_selection(raw: str):
    """
    Pull the JSON object out of an instruct model's reply.

    Even with Ollama's format=json, a quantized 7B can wrap the object in prose
    or emit trailing text, so locate the outermost braces rather than trusting
    the whole string to parse.
    """
    if not raw or not raw.strip():
        return None
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE | re.MULTILINE)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None


def _parse_compact(raw: str):
    """
    Parse the compact line format into the same dict shape as the JSON path.

        TABLE: CIMS_RAQ_Q_SEC1_PART_A_DOM
        COLUMNS: PERIOD_DELINQUENCY, TOTAL_LOAN_ASSETS
        WHY: holds loan assets by delinquency period
        JOIN: none

    Repeated TABLE: lines start a new table block, so a two-table answer parses
    without any nesting. Returns None when no TABLE: line is present, which lets
    the caller fall back to JSON parsing.
    """
    if not raw:
        return None

    tables = []
    join = None
    current = None

    for line in raw.splitlines():
        line = line.strip().lstrip("-*").strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().upper()
        value = value.strip().strip("`").strip()

        if key == "TABLE":
            if value:
                current = {"table": value, "why": "", "columns": []}
                tables.append(current)
        elif key == "COLUMNS" and current is not None:
            current["columns"] = [
                {"name": c.strip(), "why": ""}
                for c in value.replace(";", ",").split(",")
                if c.strip() and c.strip().lower() not in ("none", "all", "*")
            ]
        elif key == "WHY" and current is not None:
            current["why"] = value
        elif key == "JOIN":
            if value and value.lower() not in ("none", "null", "n/a", "-"):
                join = value

    if not tables:
        return None
    return {"tables": tables, "join": join}


def _call_selector_model(prompt: str, use_json: bool) -> str:
    payload = {
        "model": config.SELECTOR_MODEL,
        "prompt": prompt,
        "stream": False,
        # keep_alive stops Ollama unloading the model between requests. Without
        # it the first call after the idle timeout pays a multi-second model load,
        # and alternating between the selector and SQL models reloads both.
        "keep_alive": config.OLLAMA_KEEP_ALIVE,
        "options": {
            "temperature": 0.0,
            "num_ctx": config.OLLAMA_NUM_CTX,
            # The compact format needs far fewer tokens than JSON. Capping this
            # low also bounds the worst case when the model starts rambling.
            "num_predict": 400 if use_json else 160,
        },
    }
    if use_json:
        payload["format"] = "json"   # constrained decoding: correct, but slower

    response = requests.post(
        config.OLLAMA_URL, json=payload,
        timeout=(_SELECTOR_CONNECT_TIMEOUT_S, _SELECTOR_READ_TIMEOUT_S),
    )
    response.raise_for_status()
    return response.json().get("response", "")


def _validate_selection(parsed, tables, join_graph=None):
    """
    Keep only what the shortlist actually contains, and enforce the one-table
    rule. Returns a normalized selection dict, or None if nothing usable
    survived (caller then falls back to top-1).

    join_graph: {(table_a, table_b): "condition"} of declared, allowed joins.
    A join the graph does not declare is dropped along with its second table —
    the model does not get to invent relationships, which is the entire point.
    """
    if not isinstance(parsed, dict):
        return None

    valid_names = {t["table"].lower(): t["table"] for t in tables}
    entries = _load_table_entries(list(valid_names.values()))

    chosen = []
    for item in parsed.get("tables") or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("table", "")).strip().lower()
        if name not in valid_names:
            log.warning("Selector named a table outside the shortlist: %r", item.get("table"))
            continue

        entry = entries.get(name) or {}
        real_cols = {
            (c.get("name") or "").lower()
            for c in entry.get("columns") or []
        }
        cols = []
        for col in item.get("columns") or []:
            if isinstance(col, dict):
                col_name = str(col.get("name", "")).strip()
                why = str(col.get("why", "")).strip()
            else:
                col_name, why = str(col).strip(), ""
            if col_name and (not real_cols or col_name.lower() in real_cols):
                cols.append({"name": col_name, "why": why})

        chosen.append({
            "table": valid_names[name],
            "why": str(item.get("why", "")).strip(),
            "columns": cols,
        })

    if not chosen:
        return None

    join_hint = None
    if len(chosen) > 1:
        pair = tuple(sorted(t["table"].lower() for t in chosen[:2]))
        declared = (join_graph or {}).get(pair)
        raw_join = str(parsed.get("join") or "").strip()
        if declared:
            join_hint = f"Join the two tables above ON {declared}."
        elif raw_join and not join_graph:
            # No join graph authored yet: allow the model's condition but only
            # when it references CODE/RDATE, the only keys this schema shares.
            lowered = raw_join.lower()
            if "code" in lowered and "rdate" in lowered:
                join_hint = f"Join the two tables above ON {raw_join}."
        if join_hint is None:
            log.warning(
                "Dropping undeclared join between %s — keeping the best table only",
                pair,
            )
            chosen = chosen[:1]

    return {"tables": chosen, "join_hint": join_hint}


def select_tables(question, tables, matched_labels=None, join_graph=None):
    """
    Narrow a retrieval shortlist to the table(s) that actually go in the prompt.

    Returns (selected_tables, selection) where selected_tables is the list to
    pass on to generate_sql (in place of the shortlist) and selection carries the
    per-column reasoning for prompt pruning, or None when no LLM call was made.

    Never raises: any failure returns the top-1 retrieved table.
    """
    if not tables:
        return [], None

    # ── Short-circuits, cheapest first ───────────────────────────────────────
    if tables[0].get("strong_match"):
        log.info("Selector skipped: near-duplicate prior question identifies %s", tables[0]["table"])
        return tables[:1], None

    if len(tables) < MIN_CANDIDATES_FOR_LLM:
        return tables[:1], None

    top_score = tables[0].get("score") or 0.0
    runner_up = tables[1].get("score") or 0.0
    if runner_up and top_score >= runner_up * DOMINANCE_RATIO:
        log.info(
            "Selector skipped: %s dominates on retrieval score (%.3f vs %.3f)",
            tables[0]["table"], top_score, runner_up,
        )
        return tables[:1], None

    # ── LLM selection ────────────────────────────────────────────────────────
    candidates = _candidate_block(tables, matched_labels)
    if not candidates:
        log.warning("No schema entries for shortlist %s — falling back to top-1",
                    [t["table"] for t in tables])
        return tables[:1], None

    use_json = config.SELECTOR_OUTPUT_FORMAT == "json"
    template = SELECTOR_PROMPT_JSON if use_json else SELECTOR_PROMPT_COMPACT
    prompt = template.format(question=question, candidates=candidates)

    try:
        raw = _call_selector_model(prompt, use_json=use_json)
    except (requests.RequestException, ValueError) as e:
        log.error("Selector model call failed (%s) — falling back to top-1", e)
        return tables[:1], None

    # Try both parsers regardless of the configured format: a model asked for
    # lines sometimes answers in JSON anyway, and vice versa.
    parsed = _parse_compact(raw) if not use_json else _parse_selection(raw)
    if parsed is None:
        parsed = _parse_selection(raw) if not use_json else _parse_compact(raw)

    selection = _validate_selection(parsed, tables, join_graph=join_graph)
    if not selection:
        log.warning("Selector returned nothing usable (%r) — falling back to top-1", raw[:200])
        return tables[:1], None

    chosen_names = {t["table"].lower() for t in selection["tables"]}
    selected_tables = [t for t in tables if t["table"].lower() in chosen_names]
    # Preserve the selector's own ordering: its first table is the primary one.
    order = {t["table"].lower(): i for i, t in enumerate(selection["tables"])}
    selected_tables.sort(key=lambda t: order.get(t["table"].lower(), 99))

    log.info("Selector chose %s (from %d candidates)",
             [t["table"] for t in selected_tables], len(tables))
    return selected_tables or tables[:1], selection
