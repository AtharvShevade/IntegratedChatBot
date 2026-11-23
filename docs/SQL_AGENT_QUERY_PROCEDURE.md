# SQL Agent — How a User Query Is Processed and Shown

This document describes the complete procedure the SQL agent follows, from the moment a user types a
question in the chat until the result table is shown. It is written from the code in
`backend/sql_agent/` (the adapter) and `backend/sql_agent/sqlcore/` (the vendored engine).

---

## 1. What the SQL agent is

The SQL agent turns a natural-language question about regulatory-return data (CIMS / QCB / RAQ etc.)
into a safe, read-only **Oracle SELECT**, runs it, and returns the rows to the chat UI.

| Layer | Location | Responsibility |
|---|---|---|
| Chatbot adapter | `backend/sql_agent/query_handler.py` | Chat contract, guards, authorization, follow-ups, response shaping. Entry point `handle_db_query()` |
| Context resolver | `backend/sql_agent/context_resolver.py` | Detects named return(s) and reporting date/period |
| Session memory | `backend/sql_agent/session_context.py` | Remembers last answer for follow-ups |
| Latest-date logic | `backend/sql_agent/latest_date.py` | Pins SQL to the requested / latest `RDATE` |
| Bootstrap | `backend/sql_agent/_bootstrap.py` | Maps `.env` names to engine config, picks embedding folder |
| Engine | `backend/sql_agent/sqlcore/` | Retrieval (FAISS + BM25), table selection, prompt build, LLM call, validation, Oracle execution |
| Artefacts | `backend/sql_agent/embeddings_5.5/`, `embeddings_6.0/` | Prebuilt FAISS indexes, `schema.json`, `qa_pairs.json`, `concept_map.json`, etc. |

---

## 2. End-to-end pipeline at a glance

```
User message
   │
   ▼
[A] Chat routing  (agent/router.py, guided.py)  ──► decides "this is a DB/SQL question"
   │
   ▼
handle_db_query(message, session_id, login_id, conversation_history)
   │
   ├─ Step 0   Session context: pending "which return?" answer / follow-up on last result
   ├─ Guard 1  Minimum word count (5 words)
   ├─ Step 1.5 Context: named return(s) + named reporting date/period
   ├─ Step 1   Retrieval + table selection (worker thread)
   │             0. embed query once
   │             1. verified-answer tier (exact stored question → reuse its SQL, no LLM)
   │             2. wide retrieval (7 signals fused with RRF)
   │             3. narrow selection (1 table, or a declared join pair)
   ├─ Ambiguity check: tables span several returns → ask "which return?"
   ├─ Step 1.5 H-02 Authorization (login_id vs. department/return access)  ← BEFORE any SQL
   ├─ Step 2   SQL generation (Ollama LLM) with internal validate/dry-run/correct loop
   ├─ Step 2.5 Pin reporting period (explicit date, or default to latest RDATE)
   ├─ Step 3   Final validation (SELECT-only, hallucination checks)
   ├─ Step 4   Execute on Oracle (row-capped, timeout-capped)
   └─ Step 5   Shape response (rows, SQL, hints) + save session context
   │
   ▼
ChatResponse dict ──► FastAPI /chat ──► React UI renders table + SQL + hints
```

---

## 3. Stage A — How a message reaches the SQL agent

`handle_db_query` is called from four places:

1. **Router `query_database` intent** — `backend/agent/router.py` (`if intent == "query_database"`).
2. **Router SQL keyword fast-path (STEP 3)** — runs only when both the workflow check and the XML DB-QA
   check fail ("SQL keywords alone no longer win over XML domains").
3. **Router SQL follow-up** — if `session_context.looks_like_followup()` is true and no workflow / XML
   DB-QA signal matched, the message is routed back to the SQL agent.
4. **Guided flow fallback** — `backend/guided.py` (`STAGE_DB_QUERY`): if the XML DB-QA has no match, it
   falls back to the SQL agent.

Priority: workflow requests (generate / schedule / status) and the XML-based DB-QA are tried first; the SQL
agent handles whatever remains (analytical questions over Oracle data).

---

## 4. Stage B — `handle_db_query()` step by step

### Step 0 — Session context (follow-ups and clarifications)
Source: `query_handler.py`, `session_context.py`.

The agent keeps an in-process, per-session memory of its last answer (question, returns, tables, SQL,
columns, up to 50 rows, period label). Limits: **TTL 30 min**, **max 500 sessions** (LRU), never persisted.

- **Pending clarification** — if the agent previously asked "which return?", the user's reply is matched
  to an option (exact text, a number such as `2`, a return name found in the text, or a unique
  substring). The question is rebuilt as `"<original question> in return <chosen>"` and the return is forced.
- **Follow-up detection** — if there is a previous SQL answer and the message is ≤ 25 words and contains
  referential wording (it, that, same, highest, total, why, explain, "what about", "previous quarter", …),
  an LLM classifies it (`temperature 0`, last 4 history turns) into:
  - `data_question` — answerable from the already-shown table → the LLM answers **using only that table**
    (max 6 sentences, no invented values). **No new SQL is run.**
  - `refine` — same query with something changed → rewritten as one standalone question; the previous
    return is re-applied if the new text names none.
  - `new` — unrelated → processed as a fresh question.
  - Any classifier failure falls back to `new`.

### Guard 1 — Minimum length
Queries shorter than **`MIN_QUERY_WORDS = 5`** words are rejected with a hint and example questions
(skipped when the question was resolved from session context).

### Step 1.5 — Context resolution (named return + reporting period)
Source: `context_resolver.py`. Fully deterministic, read-only.

**Return detection (`detect_returns`)** — the return catalogue is built from the active embedding folder's
`schema.json` (+ `concept_map.json` for numeric codes). A return matches if the query contains:
- its full name, or
- a code (`F010`, `f10`, `f-010`, `RAQ`, `4091` …; codes that identify exactly one return), or
- at least two thirds of its title words (prefix match), or a fuzzy title match (rapidfuzz ≥ 90).

If more than one return is found and the wording is not a comparison (`compare / both / versus / across /
each return / all returns`), the agent **asks the user which return** (clickable options) and stores a pending
clarification.

**Period detection (`extract_report_date`)** — recognises ISO dates, `dd-mm-yyyy`, `31-Mar-2025`,
`March 31, 2025`, `Q1 2025` / `2025 Q1`, `March 2025`, `FY2024`, and bare years (`for 2024`). Multi-period
wording (trend, history, between, compare, growth, each quarter, last N …) deliberately returns `None`.
Result is a `ReportPeriod(start, end, label)`.

**Accuracy hint** — if no period was resolved and no time wording exists in the text, a soft tip is
attached suggesting a date / month / quarter / year.

### Step 1 — Retrieval and table selection
Source: `_retrieve()` in `query_handler.py` → `sqlcore/retriever.py`, `selector.py`.
Runs on a **worker thread** (`asyncio.to_thread`) so `/stop` cancellation works and other sessions are not blocked.

**0. Embed once** — the query is abbreviation-expanded (banking jargon, via `business_dictionary`) and
embedded a single time (`compute_query_embedding`, model `BAAI/bge-large-en` with BGE query prefix); the vector
is reused by every later signal.

**1. Verified-answer tier (`find_exact_qa_match`)** — looks up `qa_index` for a stored, hand-verified
question with text similarity ≥ **0.99**. If found (and inside the named-return scope, if any) the stored SQL is
reused directly: **no retrieval, no LLM, zero hallucination risk**. It still goes through authorization,
period pinning, validation and execution.

**2. Wide retrieval (`get_relevant_schema`)** — up to 7 signals run concurrently and are fused with
Reciprocal Rank Fusion (RRF):

| Signal | Index | Purpose |
|---|---|---|
| A | table semantic search | most direct (weight 2.0) |
| B | column search | column names are very specific (1.5) |
| C | row-label search | values in vertical tables (1.0) |
| D | QA (question→SQL) search | strongest signal (2.5) |
| E | XBRL concept search | business label → one (table, column) (2.0) |
| F | dimension-member search | disabled by default (0.0) |
| G | BM25 lexical search | exact-term / sibling-table separation (1.5) |

Then: hybrid calibration term (`HYBRID_BLEND_GAMMA = 0.3`), a QA-match bonus for a confident prior-question
hit, a relative-floor prune so a table scraping in on one weak signal is dropped, dynamic top-K
(`TOP_K_TABLES` widened for section/comparison wording), and pinning rules:
- near-duplicate question (≥ 0.95) → that table is placed first and flagged `strong_match`;
- a business alias → pinned table; a section reference (`sec1`, `part A`) → resolved/scoped table.

Output is a `RetrievalResult`: tables, columns, matched row labels, a QA example (few-shot), concept bindings.
The shortlist size for recall is `SHORTLIST_K` (default 8). If a return was named, the shortlist is scoped to
that return's tables (falling back to the unscoped list if the scope is empty).

**3. Narrow selection (`select_tables`)** — deterministic, **no LLM call**:
1. `strong_match` → keep that single table.
2. Fewer than 2 candidates → keep the top one.
3. Top score ≥ 2× runner-up → keep the top one.
4. Otherwise a second table is added **only if the semantic layer declares a join** for that pair
   (a `join_hint` is passed to the prompt). No join is ever invented.
5. Anything else → top-1 fallback.

Columns and row labels of rejected tables are dropped so nothing from them leaks into the prompt.

If there are no tables → "No matching tables found for your query. Try rephrasing with different keywords."

### Ambiguity check
If no return was named and the selected tables belong to more than one return (and the wording is not a
comparison), the agent asks which return to use.

### Step 1.5 (H-02) — Authorization, before any SQL exists
Source: `_authorize_sql_agent_access()`.

- No `login_id` → denied ("You need to be signed in…").
- `resolve_allowed_form_ids(login_id)`; unknown user → denied.
- `AUTHORIZATION_ENABLED=false` → admin-wide bypass (allowed).
- Selected tables are mapped to their `return_name` (`schema.json`) and then to a **FormId** via exact,
  single-candidate `Returns.xml` matching. Unresolved / fuzzy → **denied rather than guess**
  ("mention the specific return name").
- **Every** targeted return must be in the user's allowed set; partial access denies the whole question.

Authorization happens before the LLM call and before any Oracle connection. The verified-answer tier is
authorized too.

### Step 2 — SQL generation
Source: `sqlcore/sql_generator.py` (`generate_sql`).

1. **Sanitize** the question (neutralises prompt-delimiter injection such as `[/QUESTION]`).
2. **Build the prompt** per model profile (`ddl`, `rules` or `minimal` style, set in `MODEL_PROFILES`):
   dialect hint (Oracle), allowed table(s) and column types (from `data/schema.sql`), matched row labels,
   few-shot QA example, join hint, business-semantics layers (units, metrics, aggregation, dimensions —
   per `BUSINESS_SEMANTICS_LEVEL`), "latest RDATE" instruction, today's date, and relative-time resolution
   ("last quarter").
3. **Token budget** — `enforce_token_budget` trims optional prompt sections if the prompt would overflow
   `OLLAMA_NUM_CTX` (8192).
4. **Call Ollama** (`OLLAMA_URL`, streaming, `keep_alive 30m`, temperature per profile; `num_predict`
   raised for multi-part `_PART_A/B` tables). A circuit breaker pauses calls for 30 s after a connect
   failure; connect timeout 3 s, read 300 s.
5. **Strip** markdown fences and trailing `;`.
6. **Check** each candidate with `validate_sql` **and** an Oracle `EXPLAIN PLAN` dry-run (parses and plans
   without data access; rolled back; if the DB or `PLAN_TABLE` is unavailable the dry-run is skipped and
   does not block).
7. **Correction loop** (up to `MAX_CORRECTION_RETRIES = 3`):
   - first tries a **deterministic auto-correct** for vertical-table aggregations (adds the missing
     row-label filter);
   - otherwise sends a correction prompt with allowed tables/columns, the previous SQL, the failure reason and
     a category-specific hint (hallucinated table / column / engine-rejected);
   - retry temperature 0.15 (+0.1 on the last round); stops early if the SQL repeats.
8. **Advisory checks** on a valid result: stock-vs-flow aggregation, literal-value check against known
   row-label values (`literal_validator`).
9. Invalid SQL after all rounds is logged to `eval/results/hallucination_log.jsonl`.

The adapter wraps this in `MAX_SQL_RETRIES = 2` which covers only **transient Ollama failures**
(`RuntimeError`). Generation runs at temperature 0, so repeating an identical prompt would give identical SQL.

### Step 2.5 — Pin the reporting period
Source: `latest_date.py`.

- **Period named** → `apply_explicit_date` rewrites the "latest RDATE" idiom (or wraps the table) to the
  requested date/range.
- **No period named** (and not a trend/history/multi-period question) → `apply_latest_date_default`
  wraps each selected table in an inline view limited to `MAX(RDATE)`. Only applied when the SQL does not
  already mention `RDATE`.
- Every rewrite is re-validated; if it fails, the model's own SQL is kept.

### Step 3 — Final validation (`validate_sql`)
This decides whether execution is allowed at all. Checks include:
- non-empty; **one statement only**; must start with `SELECT`;
- banned keywords: `delete update drop insert truncate alter create exec merge grant revoke call lock begin
  declare execute`;
- no privileged packages (`DBMS_*`, `UTL_*`, `OWA`, `HTP`, `SYS.`);
- no non-Oracle syntax (`ILIKE`, `~` regex); bare `'YYYY-MM-DD'` literals must be `TO_DATE(...)`;
- **hallucinated tables** (not in the allowed set), must reference at least one matched table;
- **undeclared joins** between tables rejected against the semantic-layer join graph;
- **column/alias mismatches** and **hallucinated columns** in the SELECT list;
- **vertical-table aggregation** without a row-label filter (would double-count the total row).

Failure → "Unable to process your query right now. Please try again." (plus a plain-English `db_error`).

### Step 4 — Execution
Source: `sqlcore/executor.py` → `execute_query`.

- Pooled Oracle connection (`DB_HOST/PORT/SERVICE/USER/PASSWORD`).
- Statement timeout **`DB_STATEMENT_TIMEOUT_MS = 30000`** (server-side `call_timeout`).
- Wrapped as `SELECT * FROM (<sql>) FETCH FIRST DB_MAX_ROWS+1 ROWS ONLY`; result truncated to
  **`DB_MAX_ROWS` (default 100)** with a warning.
- Runs on a worker thread. Returns `(columns, rows, error)`.

### Step 5 — Response shaping (`_finish` / `_rows_result`)
- Rows are serialized to JSON-safe types (`Decimal` → string to keep exact precision).
- **Date hint** — tells the user which reporting date the data is for:
  - period named → "Showing data for reporting date …";
  - no date mentioned and SQL uses `MAX(RDATE)` → "No date was mentioned, so this shows the latest available
    reporting date: …";
  - period named but **0 rows** → "No data is available for …. The nearest earlier reporting date is …; the
    latest available is …".
- Rows > 0 → `"Found N row(s)."`; 0 rows → `"No data found for your query."` with tips.
- The result is saved to session memory (question, returns, tables, SQL, columns, ≤ 50 rows, period) to enable
  follow-ups.

---

## 5. What is returned and how it is shown

`_build_result()` is the single choke point for every response and returns a `ChatResponse`-shaped dict:

| Field | Meaning |
|---|---|
| `intent` | always `query_database` |
| `result_type` | `db_result` |
| `response_text` | "Found N rows." / message / error text |
| `db_columns` | column headers from Oracle |
| `db_rows` | serialized rows (list of lists) |
| `db_sql` | generated/stored SQL (shown to the user) |
| `db_error` | plain-English validation reason, or `null` |
| `accuracy_hint` | date tip / "which reporting date" note |
| `needs_more_info`, `more_info_hint` | shown when the query is too short or returns no rows |
| `need_clarification`, `options` | "which return?" choices |

The FastAPI `/chat` endpoint passes this through (`backend/models.py` fields `db_columns`, `db_rows`,
`db_sql`, `accuracy_hint`, …). In the React app (`frontend/src/App.jsx`, around `_hasSqlContent`) a message is
treated as a SQL result when it has `db_sql` or columns, and the UI renders a **table of rows**, the **SQL**,
the **accuracy hint**, the **more-info hint**, and clarification **options** as clickable choices.

Error handling (M-07): any text that looks like a raw Oracle/Python error (`ORA-xxxxx`, `Connection failed:`,
`Query execution failed:`, `Traceback…`) is replaced with *"A database error occurred while processing your
query. Please try again."* so internals never reach the client; the original is logged.

---

## 6. Messages the user can see (outcome map)

| Situation | Response |
|---|---|
| Fewer than 5 words | "Your query is too short…" + examples |
| Several returns match | "Which return should I look in?" + options |
| Not signed in / no access / return unresolved | Access-denied or "mention the return name" message |
| No tables found | "No matching tables found… rephrasing" |
| Retrieval crash | "Unable to process your database query right now." |
| Ollama failure (after retry) | "SQL generation failed. Please try again." |
| Invalid SQL | "Unable to process your query right now." (+ reason) |
| DB error / timeout | "Unable to retrieve the requested information." |
| 0 rows | "No data found…" + tips (or nearest/latest available dates) |
| Success | "Found N rows." + table + SQL + date hint |

---

## 7. Safety and accuracy design points

- **Read-only**: SELECT-only validation, keyword blocklist, single statement, privileged-package block.
- **Authorization before generation**: no LLM or DB work for a user who cannot access the return.
- **Hallucination controls**: one-table selection, declared-join-only, allowed table/column lists in
  correction prompts, EXPLAIN PLAN dry-run, vertical-table guard, literal check, verified-answer tier.
- **Resource limits**: row cap, 30 s statement timeout, token budget, Ollama circuit breaker, bounded session store.
- **Prompt-injection hygiene**: delimiter neutralisation on the user question.
- **No internals leaked**: error sanitisation at the response choke point.
- **Non-blocking**: blocking work runs in worker threads so `/stop` cancels immediately.

---

## 8. Configuration

Set in `.env` (and per-version overlay `.env.5.5` / `.env.6.0`); `_bootstrap.py` translates them for the engine.

| `.env` name | Engine setting | Notes |
|---|---|---|
| `APP_VERSION` | picks `embeddings_5.5` or `embeddings_6.0` | missing folder → hard error (no cross-version fallback) |
| `EMBEDDING_DIR` | embedding folder override | relative paths resolved against `backend/sql_agent` |
| `SQL_EMBED_MODEL` / `SQL_QUERY_PREFIX` | `EMBED_MODEL` / `QUERY_PREFIX` | default `BAAI/bge-large-en` |
| `OLLAMA_BASE_URL` | `OLLAMA_URL` = `<base>/api/generate` | no hardcoded fallback |
| `SQL_OLLAMA_MODEL` | `OLLAMA_MODEL` | SQL model; kept separate from the chatbot's own `OLLAMA_MODEL` |
| `ORACLE_HOST/PORT/SERVICE/USER/PASSWORD` (or `ORACLE_DSN`) | `DB_*` | credentials have no in-code default |
| `ORACLE_MAX_ROWS` | `DB_MAX_ROWS` | default 100 |

Tuning knobs (env): `SHORTLIST_K` (8), `TOP_K_TABLES` (3), `TOP_K_COLUMNS` (5), `OLLAMA_NUM_CTX` (8192),
`OLLAMA_KEEP_ALIVE` (30m), `OLLAMA_NUM_PREDICT`, `OLLAMA_TEMPERATURE`, `BUSINESS_SEMANTICS_LEVEL` (off),
`CONCEPT_SIGNAL_WEIGHT` (2.0), `MEMBER_SIGNAL_WEIGHT` (0), `BM25_SIGNAL_WEIGHT` (1.5),
`HYBRID_BLEND_GAMMA` (0.3), `QA_SIGNAL_WEIGHT` (2.5), `DB_STATEMENT_TIMEOUT_MS` (30000).

The bootstrap restores `os.environ` after the engine config is read, so the SQL model name does not leak into
other chatbot features that read `OLLAMA_MODEL`.

---

## 9. Startup behaviour

On backend startup (`backend/main.py` lifespan) the SQL agent is bootstrapped (`[SQL_AGENT] bootstrapped
root=… embedding_dir=… model=…`), and the embedding model and indexes are warmed up so the first query is not slow.
If Ollama is unreachable at startup, the LLM warm-up logs a warning but the server still starts; SQL questions
will then fail at generation with "SQL generation failed" until the model endpoint is reachable.

---

## 10. Worked example

User: **"Show total loan assets for domestic operations in RAQ for March 2025"** (signed in as an allowed user)

1. Router → SQL agent. Word count OK (11).
2. Context: return `CIMS_RAQ(Quarterly)` detected via code `RAQ`; period `March 2025`
   (2025-03-01 → 2025-03-31).
3. Embed query → no ≥ 0.99 stored match → wide retrieval scoped to RAQ tables → selector keeps the dominant
   table (e.g. `CIMS_RAQ_Q_SEC1_PART_A_DOM`).
4. Authorization: table → return → FormId; user's allowed set contains it → continue.
5. Prompt built with the table DDL, matching row labels, a similar QA example; LLM returns SQL; `validate_sql`
   + `EXPLAIN PLAN` pass.
6. Period pin rewrites the latest-RDATE idiom to the March 2025 range; re-validated.
7. Oracle runs it (≤ 100 rows, 30 s limit).
8. Response: `Found 1 row.`, `db_columns`, `db_rows`, `db_sql`, `accuracy_hint` =
   "Showing data for reporting date 31-Mar-2025 (March 2025)."; saved to session memory.
9. Follow-up **"which is highest?"** → classified `data_question` → answered from the stored rows, no new SQL.

---

## 11. Source map

| Concern | File |
|---|---|
| Entry point, guards, auth, follow-ups, response | `backend/sql_agent/query_handler.py` |
| Return/date detection | `backend/sql_agent/context_resolver.py` |
| Session memory | `backend/sql_agent/session_context.py` |
| Latest/explicit date pinning | `backend/sql_agent/latest_date.py` |
| Env mapping + embedding folder choice | `backend/sql_agent/_bootstrap.py`, `backend/sql_agent/config.py` |
| Row serialization | `backend/sql_agent/utils.py` |
| Retrieval (FAISS/BM25/RRF) | `backend/sql_agent/sqlcore/retriever.py`, `lexical_search.py`, `concept_map.py` |
| Table selection | `backend/sql_agent/sqlcore/selector.py`, `semantic_layer.py` |
| Prompt, LLM call, validation, correction | `backend/sql_agent/sqlcore/sql_generator.py`, `sql_prompts.py`, `token_budget.py` |
| Oracle execution / dry run | `backend/sql_agent/sqlcore/executor.py` |
| Literal check | `backend/sql_agent/sqlcore/literal_validator.py` |
| Routing into the agent | `backend/agent/router.py`, `backend/guided.py` |
| UI rendering | `frontend/src/App.jsx` |
