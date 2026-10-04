# iDEALXia / XBRL Intelligent Assistant

**End-to-end technical architecture, data preparation, AI models, functionalities, and production documentation**

Production Handover · Reverse-Engineered from Source

End-to-end technical architecture, data preparation, AI models, functionalities, and production documentation — organized around real data flows traced directly from `Chat-SystemWorking` (the chatbot) and `TrendAnalysis_JSON_Extractor` (the upstream Custom Return JSON generator). Every claim below carries a `file:line` citation back to source; anything that could not be confirmed is marked **needs verification**.

---

## Contents

1. [Complete System Flow](#1--complete-system-flow)
2. [Source Data → Prepared Data](#2--source-data--prepared-data)
   - 2.1 [Custom Return JSON pipeline](#21-custom-return-json--how-it-is-built)
   - 2.2 [SQL Agent preparation](#22-sql-agent-data-preparation)
3. [Common Runtime Request Flow](#3--common-runtime-request-flow)
   - [Auth / tenant / version context](#auth--user--tenant--version-context)
   - [Request routing (decide())](#request-routing--is-there-an-intent-classifier)
4. [Chatbot Functional Flows](#4--chatbot-functional-flows)
5. [Complete AI Model Inventory](#5--complete-ai-model-inventory)
6. [SQL Agent — Failure Handling Reference](#6--sql-agent--failure-handling-reference)
7. [Frontend & API Flow](#7--frontend--api-flow)
8. [Deployment & Configuration Flow](#8--deployment--configuration-flow)
9. [Logging, Debugging & Testing](#9--logging-debugging--testing)
10. [Security Flow](#10--security-flow)
11. [Reference Matrices](#11--reference-matrices)
12. [Worked End-to-End Examples](#12--worked-end-to-end-examples)
13. [Production Readiness](#13--production-readiness)
14. [Known Limitations & Troubleshooting](#14--known-limitations--troubleshooting)

---

## 1 · Complete System Flow

The system is two repositories, not one. **TrendAnalysis_JSON_Extractor** is an offline producer: given a taxonomy entry-point and a return's repo folder, it walks the XBRL DTS with Arelle, joins it to the reporting database's physical columns, scores regulatory importance, and writes one `<return_code>.json` file per return into an `output/` directory. **Chat-SystemWorking** is the runtime: a single FastAPI process (`backend/main.py`) fronted by a React app and an IIS reverse proxy, which reads those JSON files — plus live XML repositories, XBRL instances, and an Oracle warehouse — to answer chat, comparison, error-explanation, and SQL questions.

```
SOURCE DATA                           DATA PREPARATION                        RUNTIME (Chat-SystemWorking)
─────────────                         ──────────────                          ────────────────────────────
XBRL Taxonomy (.xsd+linkbases)  ──▶   TrendAnalysis_JSON_Extractor (Arelle)  ──▶  <repo>/Json/<form_id>.json
Return repo (Mapping_N.xml,           Stage A: concepts/axes/formulas             read by backend/tools/importance_json.py
  PreLnkBases.xml, XML_Query.xml) ─▶  Stage B: 4-hop DB-column join               (OPTIONAL enrichment, never required)
Oracle "CDR" warehouse (optional) ─▶  Stage: regulatory_importance scorer
                                       merge.py → write JSON + summary_index

XML repositories (Returns.xml,        read live per-request via
  XML_User/Dept/Role, InstanceLog) ─▶  backend/config.py path helpers      ──▶   FastAPI /chat /guided /compare-execute
XBRL instance documents (.xml)    ──▶  Arelle live parse (xbrl_comparator)  ──▶  /explain-category /speech-to-text
Error/validator HTML files        ──▶  regex/HTML parsers (formula_error.py,      │
                                        dimension_error.py)                       ▼
Oracle regulatory tables          ──▶  FAISS retrieval + SQLCoder (sql_agent) ──▶  React frontend (IIS reverse proxy)
```

### Master data-lineage diagram

```
 USER (browser, embedded via iframe in a .NET host page)
   │  postMessage CHATBOT_READY/CHATBOT_AUTH → jwt, tenant_id, domain   (6.0 only)
   ▼
 React SPA (frontend/src) ── POST /chat|/guided|/compare-execute|/explain-category|/speech-to-text
   │  body carries login_id, user_id, role_id, asp_session, tenant_id, domain, jwt, lang   [App.jsx:9-40, api.js]
   ▼
 FastAPI backend/main.py
   ├─ _make_repo_scope()  → version_config: resolve tenant → contextvar repo root         [main.py:284-311]
   ├─ i18n.translate_inbound()  (lang≠en, ENGLISH-only pipeline beyond this point)         [boundary.py:266-309]
   ├─ decide()  — rule-based intent cascade + LLM fallback                                 [agent/__init__.py:818]
   │     STEP0 conversational LLM (gated) → STEP1 workflow regex → STEP2 DB-QA (XML,
   │     regex+embedding exemplars) → STEP3 SQL-agent keyword → STEP4 LLM intent+entity
   ├─ functionality handler (status / generate / schedule / compare / explain / db_qa / sql)
   │     reads: Returns.xml, XML_InstanceLog, XBRL instance docs, error HTML, Custom
   │     Return JSON (<repo>/Json/<form_id>.json), Oracle DB, taxonomy folders
   ├─ i18n.translate_outbound()  (8 whitelisted prose fields only, entity-masked)          [boundary.py:57-66]
   ▼
 ChatResponse (one wide envelope, result_type discriminator)                               [models.py:32-81]
   ▼
 MessageBubble.jsx switches on result_type → renders table / card / chart / plain text
```

---

## 2 · Source Data → Prepared Data

### 2.1 Custom Return JSON — how it is built

Built entirely inside the separate `TrendAnalysis_JSON_Extractor` repo (FastAPI POC), triggered by `POST /generate`. The chatbot never generates this file itself — it only *reads* the finished output.

```
Step 1 — Inputs (per request body)
  repo_path        → return's folder, e.g. D:\Repo5.5\Database\4055\   [app/main.py:23]
  entry_point_path → taxonomy entry .xsd, e.g. fed06-entry.xsd
  return_code      → optional; else = basename(repo_path)              [app/main.py:45]

Step 2 — Stage A: Taxonomy extraction (Arelle DTS)                     [stage_a_taxonomy.py:61-124]
  Cntlr.modelManager.load(entry_point_path)
  → _detect_linkbases()                 presentation/calc/def/formula linkbases present?
  → _extract_presentation_and_dimensions()   tables[], concept↔table map, tree depth
  → _extract_dimensions()               axes[] + domain members (XBRL Dimensions 1.0)
  → _extract_formulas()                 $Vn variable resolution → 6 rule_category buckets
  → _extract_calculations()             classic summation-item roll-ups
  → _extract_concepts()                 per-concept: label, doc, type, period/balance,
                                         table membership, formula participation
  → build_regulatory_importance()       SEPARATE raw-XML scorer (no Arelle) — 5-factor
                                         score: Mandate/Rules/Section/Blocking/Recency    [importance/scorer.py:605-699]

Step 3 — Stage B: DB mapping (4-hop deterministic join)                [stage_b_mapping.py:137-318]
  PreLnkBases.xml  (RoleURI ↔ numeric PriEle table)
     ↔ Mapping_N.xml  (PriEle → Code)
     ↔ XML_Query.xml  (Code → real table.column, 3 physical patterns)
     ↔ join on template_id → PriEle/concept_id
  status: "confirmed" (provable) | "suggested" (ordinal fallback, unvalidated)
  [fuzzy DB-fallback via Oracle exists in code but is NOT auto-invoked by /generate]

Step 4 — Merge & write                                                 [app/core/merge.py:16-105, main.py:80-96]
  merge.build_return_json() → overlay db_mapping onto concepts, compute unmapped_summary
  → write  OUTPUT_DIR/<return_code>.json   (no schema validation step)
  → update  OUTPUT_DIR/summary_index.json  (replaces prior entry for same return_code)
```

**Return/form identification** is purely folder-naming, not embedded taxonomy metadata — there is no taxonomy-native "return ID." `taxonomy_version` is a best-effort regex guess over the taxonomy path string (`[/\](\d+\.\d+\.\d+)[/\]`), explicitly documented as heuristic, not authoritative [`summary_index.py:18-30`].

> **Note:** Two importance-like scores exist per concept and must not be confused: `concept.importance` (cheap heuristic from facts already in hand this run) vs. `concept.regulatory_importance` (the 5-factor scorer that re-reads the raw taxonomy XML independently of Arelle, specifically for RBI-circular mandate text and section groupings). Only the second is what `importance_json.py` on the chatbot side actually consumes.

#### What exactly is inside the Custom Return JSON

| Top-level key | Contents |
|---|---|
| `return_metadata` | return_code, taxonomy_path, repo_path, linkbase_generation_detected, db_mapping_source_detected, extraction_run, and (newer runs only) regulatory_importance_status |
| `structure` | presentation tables + axes/domain-members |
| `concepts[]` | per concept: concept_id, label, documentation, data_type, period/balance_type, abstract, substitution_group, importance{}, presentation{tables,depth,siblings}, calculation{}, formula_participation[], dimensional_context_required[], db_mapping{status,table_name,column_name,join_provenance}, llm_context{review_status:"not_generated"}, trend_profile{}, variance_profile{}, and (newer runs) regulatory_importance{matched,score,tier,section_code} |
| `validation_rules[]` | every formula/assertion extracted by Stage A, with rule_category classification |
| `unmapped_summary` | mapped/suggested/unmapped counts, validation_rule_category_breakdown |

#### Storage & consumption on the chatbot side

Files land at `<repo_root>/Json/<form_id>.json`, resolved via `backend.config.json_metadata_base_dir()` and read by `backend/tools/importance_json.get_importance_from_json(form_id)` [`importance_json.py:226-284`]. The loader caches by `(tenant_id, form_id) → mtime` so a regenerated file is picked up without a backend restart, and returns `None` — never raises — when the file is missing or its `regulatory_importance_status.available` flag is false. **No exact runtime path/copy-step was found on either repo side** connecting the extractor's `output/` folder to a tenant's `Json/` folder — **needs verification** against whatever manual/ops process moves generated files into place.

| Consumer | How used | Required? |
|---|---|---|
| Instance comparison (§4 Compare) | Blends importance/section/tier into the variance ranking and into the LLM narrative's grounding context | Optional — degrades to movement-only ranking |
| Formula-error explanation, 4000-series returns | "4000-series taxonomy-JSON enrichment" referenced in `report_lookup.py:3730-3733`; exact read call not located | Needs verification |

No functionality found treats the Custom Return JSON as strictly required — every consumer degrades gracefully. The design intent, per the module's own comment: *"UNMATCHED IS NOT LOW"* — an unclassified concept is a distinct, non-blocking state, not a zero score.

### 2.2 SQL Agent data preparation

Two parallel query subsystems exist under this heading and must not be conflated:

- **SQL Agent** (`backend/sql_agent/`) — free-form NL → LLM-generated SQL → Oracle execution.
- **DB Q&A** (`backend/db_qa/`) — a fixed taxonomy of intents resolved by regex + an embedding index over hand-written exemplar phrasings, routed to hand-written Python query handlers. No SQL is ever generated here; only an optional LLM "beautifier" reformats already-fetched rows.

```
Build-time (OUTSIDE this repo — a separate "Embedding maker" tool)
  Oracle schema introspection (USER_TABLES, live)
    → schema.json  (table+column docs, PK/FK, precomputed embedding-source strings)
    → qa_pairs.json (question→gold-SQL few-shot examples)
    → business_dictionary.yaml, semantic_layer.yaml (declared join graph), concept_map.json
    → description_samples.json (real row-label values sampled from Oracle)
    → FAISS indexes: table_index / column_index / row_label_index / concept_index / qa_index
    → build_stamp.json  (checksums, published_at, src=D:\Tools\Embeding maker\output\...)
  ⤷ TWO versioned drops ship in THIS repo: embeddings_5.5/  and  embeddings_6.0/          [_bootstrap.py:54-55]
    Selected at process start by APP_VERSION; RuntimeError (fail-loud) if the folder for
    the active version is missing — never silently falls back to the other version.      [_bootstrap.py:182-195]

Runtime — user asks a database question                                                  [sql_agent/__init__.py:179-383]
  question  ──▶  length guard (≥5 words)
            ──▶  compute_query_embedding()  (BAAI/bge-large-en, local SentenceTransformer)
            ──▶  exact-match tier: ≥0.99 similarity to a stored qa_pair → REUSE ITS SQL,
                 skip the LLM entirely
            ──▶  get_relevant_schema(): 7 parallel signals fused by weighted RRF
                 (table / column / row-label / QA-example / XBRL-concept /
                  XBRL-dimension-member semantic search + BM25 lexical), with hard
                  overrides: QA strong-match > business-dictionary pin > explicit
                  section reference in the query text
            ──▶  select_tables(): deterministic — narrows to exactly one table (or a
                 declared join pair from semantic_layer.yaml). No LLM here (removed
                 for latency; an earlier version did call one).
            ──▶  build_prompt(): DDL-style CREATE TABLE block with types, PK/NOT NULL,
                 row-label sample values as comments, resolved relative-time literals
            ──▶  generate_sql()  — Ollama SQLCoder-7B (remote proxy), streamed,
                 circuit-breaker on outage (30s cooldown)
            ──▶  validate_sql()  — regex allow-list: SELECT-only, banned DML/DDL
                 keywords, Oracle-only operators, table/column allow-list, declared
                 join-graph enforcement (added directly in response to invented-join
                 hallucinations logged in eval/results/hallucination_log.jsonl)
            ──▶  dry_run_sql()  — Oracle EXPLAIN PLAN (read-only, never touches data)
            ──▶  up to 3 correction retries with the validation reason re-sent to the LLM
            ──▶  execute_query()  — pooled oracledb connection, fetchmany(DB_MAX_ROWS≈100)
            ──▶  db_columns / db_rows / db_sql returned as-is — no NL-summarization
                 step was found for SQL-agent results (contrast DB Q&A's beautifier)
```

#### SQL Agent — verified implementation detail (code-confirmed)

**Code layout.** Chatbot-side adapter is `backend/sql_agent/query_handler.py` (`handle_db_query(message, session_id)`), called from `backend/guided.py` (STAGE_DB_QUERY, as the fallback after XML/app-DB Q&A intent classification fails) and from `backend/agent/router.py` STEP 3 (`_DB_QUERY_KW_RE` keyword trigger) / STEP 4 (`query_database` intent from the LLM fallback). The actual NL→SQL engine is a vendored package under `backend/sql_agent/sqlcore/{config.py, vectorizer.py, retriever.py, selector.py, sql_generator.py, executor.py, schema_store.py, description_fetcher.py, business_dictionary.py, business_semantics.py, concept_map.py, semantic_layer.py, lexical_search.py, literal_validator.py, section_alias.py, ddl_parser.py}`, made importable via `backend/sql_agent/_bootstrap.py` (which also loads `sql_agent/.env` — the SQL Agent has its **own** env file, separate from the app-level `.env`, with a fallback name-mapping from `ORACLE_DSN/HOST/PORT/SERVICE/USER/PASSWORD`, `SQL_OLLAMA_MODEL`, `SQL_EMBED_MODEL` onto the engine's own `DB_*`/`OLLAMA_MODEL`/`EMBED_MODEL` names). Thin re-export shims at `backend/sql_agent/{config.py, executor.py, selector.py, semantic_layer.py, ...}` map to `sqlcore.*` so the rest of the app imports via `backend.sql_agent.X`. **No embedding-build code exists anywhere in this repository** — `sqlcore/config.py`'s own docstring calls `EMBEDDING_DIR` "a self-contained, prebuilt artifact set with no embedding-building code anywhere in this runtime package"; the generator (`embedding_building/cims_raq_quarterly/build_concept_map.py` and siblings) lives in a separate, external development repo and only its output artifacts ship here.

**Embedding model.** `backend/sql_agent/sqlcore/vectorizer.py`: `SentenceTransformer(EMBED_MODEL)` loaded once at module import (local, in-process — no external embedding API call), library = HuggingFace `sentence-transformers` + `faiss` for the index + `pickle` for metadata. `EMBED_MODEL` defaults to `BAAI/bge-large-en` (`sqlcore/config.py`). BGE models require an asymmetric **query-side-only** instruction prefix: `QUERY_PREFIX = "Represent this sentence for searching relevant passages: "` — applied by `embed_query()` but never by `embed_documents()`; changing `EMBED_MODEL` to a non-BGE model without clearing `QUERY_PREFIX` silently degrades retrieval (flagged in code comments). `normalize_text()` (lowercase, whitespace-collapse, trailing-punctuation strip) is applied identically to index-build documents and runtime queries. `embed_documents()` calls `model.encode(texts, normalize_embeddings=True, batch_size=32)` (L2-normalized, so cosine similarity == dot product). Index type: `faiss.IndexFlatIP` (exact brute-force inner-product search over normalized vectors).

**What is embedded, and where it is stored.** Everything is a **prebuilt, static artifact** — flat FAISS index files + pickle metadata + plain JSON/YAML, on local disk, loaded into an in-process cache. No external vector DB (no Chroma/pgvector/Pinecone). Two versioned drops ship in-repo, selected by `APP_VERSION` at process start: `backend/sql_agent/embeddings_5.5/` and `embeddings_6.0/` (the 6.0 drop is a reduced subset — no concept/member/business-dictionary/semantic-layer files, suggesting the XBRL business-semantics layer was rolled out to 5.5 first). A missing folder for the active version is a **hard fail-loud RuntimeError at startup**, never a silent cross-version fallback.

| File in `embeddings_5.5/` | Content embedded / held | Used as |
|---|---|---|
| `table_index.faiss` + `table_meta.pkl` | Table-level descriptive text (name/description/column summary) | Signal A: table semantic search |
| `column_index.faiss` + `column_meta.pkl` | Per-column descriptive text | Signal B: column search → infers relevant tables |
| `row_label_index.faiss` + `row_label_meta.pkl` | Every distinct row-label value sampled from Oracle for "vertical" tables, as `"{table} {col} label: {val}"` strings | Signal C: which table/column holds a label value like the query (e.g. "Total (1 to 4)") |
| `qa_index.faiss` + `qa_meta.pkl` (+`qa_pairs.json`, `qa_pairs_new.json`) | Hand-curated `{question, sql, table}` triples — question text embedded | Signal D + the "verified-answer" exact-match tier + few-shot prompt injection |
| `concept_index.faiss` + `concept_meta.pkl` (+`concept_map.json`) | XBRL business-concept labels (regulatory/business phrasing) mapped to `(table, column)` — built by the external `build_concept_map.py` tool | Signal E: business-concept → column identification |
| `member_index.faiss` + `member_meta.pkl` | XBRL dimension-member text (e.g. "doubtful assets two") mapped to tables sharing that axis | Signal F: dimension/axis narrowing (weight 0 by default — measured to hurt precision) |
| `bm25_table_index.pkl` | Lexical (BM25) index over table documents, tokenized via `business_dictionary.expand_acronyms` | Signal G: exact-term lexical matching, complements dense embeddings |
| `schema.json` | Full DDL-derived schema (tables/columns/types/PK/FK/descriptions) — plain JSON, not embedded | Prompt DDL rendering + validation |
| `description_samples.json` | Sampled row-label values per (table, column) — plain JSON | Source for row_label_index + injected raw into prompts + literal validation |
| `needs_trim.json` | `{table: [label_column,...]}` for whitespace-padded columns | Tells the LLM to emit `TRIM(col) = 'value'` |
| `business_dictionary.yaml` | Acronym/alias/synonym registry | Query expansion so abbreviations match embedding text |
| `semantic_layer.yaml` | Declared table joins, vertical-table specs, metric definitions | Gates which joins `selector.py`/`sql_generator.py` consider legal |
| `taxonomies.json` | XBRL taxonomy data | Supports the concept/business-semantics layer |

**Loading & caching.** `sqlcore/retriever.py::_get_index()` keeps a module-level `_index_cache` dict keyed by `(index_path, meta_path)` — `faiss.read_index()` + `pickle.load()` run once per process, then served from memory. `description_fetcher.py::_label_index_cache` and `schema_store.py`/`sql_generator.py::_schema_json_cache` follow the same pattern for the row-label index and parsed `schema.json`/`description_samples.json`/`needs_trim.json` (added after these were found being re-parsed 4-6 times per request). Rebuilding the index files requires a process restart. `config.EMBEDDING_DIR` is read at **call time everywhere**, not import time, so a later scope/env change is honored without re-import.

**Retrieval → generation → execution, in detail.** Entry point `backend/sql_agent/query_handler.py::handle_db_query()`:
1. **Guard**: `MIN_QUERY_WORDS=5` — shorter queries get an immediate "too short" prompt.
2. **Accuracy hint**: `_has_time_context()` regex-checks for month/quarter/year/date patterns; absence attaches a soft "try adding a time period" hint to the final response.
3. **Retrieval + selection** runs via `asyncio.to_thread()` (gives the coroutine a real await point so `/stop` can cancel mid-pipeline):
   - `retriever.compute_query_embedding(query)` — embeds the query once (after jargon expansion via `business_dictionary.expand_acronyms`), reused by every downstream signal.
   - `retriever.find_exact_qa_match(query, query_vec)` — checks the `qa_index` for a near-identical stored question (character-similarity ratio ≥ `EXACT_MATCH_MIN_RATIO=0.99`); if matched, the verified stored SQL is used directly with **no LLM call**.
   - Else `retriever.get_relevant_schema(query, query_vec, shortlist_k=SHORTLIST_K=8)` — see fusion algorithm below.
   - `selector.select_tables()` narrows the shortlist to exactly one table (or a declared join pair per `semantic_layer.yaml`) — **deterministic, no LLM**. An earlier design used a second LLM call here for table selection; it cost 75-135s per request in production and was replaced with a dominance-ratio/declared-join-only heuristic.
4. **SQL generation** (`sql_generator.generate_sql()`, worker thread, `temperature=0`) builds the prompt via `build_prompt()`/`build_table_ddl()`: the selected table(s) rendered as literal Oracle `CREATE TABLE` DDL (SQLCoder-7B was trained on DDL-style context) — column types from `schema.json`, falling back to checked-in `data/schema.sql` parsed by `ddl_parser.py`, then heuristic name-pattern inference. Row-label sample values ride as inline column comments (`-- row label, allowed values: '...'`), including detected TOTAL rows and TRIM() hints. `_resolve_relative_time()` converts phrases like "last quarter"/"YTD" into concrete calendar dates so the LLM never guesses date math. A matched `qa_example` is injected as a worked few-shot example.
5. **Validation loop** inside `generate_sql()` itself (the outer `MAX_SQL_RETRIES=2` in `query_handler.py` only covers transient Ollama connection failures, since temperature=0 makes a naive outer retry reproduce the same wrong SQL): (a) `validate_sql()` — regex-based static validator (SELECT-only, banned DML/DDL keywords, privileged-package ban, non-Oracle-operator ban, bare-date-literal detection, hallucinated table/column detection, alias-aware mismatch detection, undeclared-join detection against `semantic_layer.yaml`, vertical-table-aggregation-without-label-filter detection); (b) `executor.dry_run_sql()` — Oracle `EXPLAIN PLAN` (no data touched, rolled back) catching what regex can't (ORA-00904 unknown column, ORA-01861 type mismatch). On failure, retries up to `MAX_CORRECTION_RETRIES=3` with an escalating correction prompt (deterministic vertical-aggregation autocorrect first, then targeted-hint retries, then a final +0.1 temperature bump), logging every still-invalid final result to `eval/results/hallucination_log.jsonl`. Post-validation advisory checks: `business_semantics.py`/`concept_map.py::check_stock_aggregation()` (stock-vs-flow XBRL sanity) and `literal_validator.py::check_literal_validity()` (hallucinated-literal detection against known label samples).
6. **Execution**: `executor.py` runs on Oracle via a pooled `oracledb` connection (`min=2, max=10`), wraps the statement in `FETCH FIRST {DB_MAX_ROWS+1} ROWS ONLY` (Oracle-side short-circuit, default `DB_MAX_ROWS=100`) and enforces `conn.call_timeout = DB_STATEMENT_TIMEOUT_MS` (default 30000ms) as defense against expensive queries that pass validation.
7. **Response shaping**: `_build_result()`/`_rows_result()` produce the `ChatResponse`-shaped dict (`intent="query_database"`, `db_columns`, `db_rows`, `db_sql`, `db_error`, `accuracy_hint`, `needs_more_info`).

**The retrieval fusion algorithm.** `retriever.get_relevant_schema()` runs 7 signals in parallel via a `ThreadPoolExecutor` (FAISS releases the GIL): A table_index (weight 2.0), B column_index (1.5), C row_label (1.0), D qa_index (`QA_SIGNAL_WEIGHT=2.5`, strongest), E concept_index/XBRL business-concept (`CONCEPT_SIGNAL_WEIGHT=2.0`, best-hit-only, capped at `CONCEPT_MAX_HITS_PER_TABLE=2`), F member_index/dimension-member (`MEMBER_SIGNAL_WEIGHT=0.0`, disabled — measured to hurt precision), G BM25 lexical (`BM25_SIGNAL_WEIGHT=1.5`). Fusion is **Reciprocal Rank Fusion**, `_rrf(rank, k=60) = 1/(k+rank+1)`, summed per table across signals, plus a hybrid calibration term `HYBRID_BLEND_GAMMA=0.3` (min-max normalized raw-score blend layered on pure rank fusion, to fix RRF's blindness to near-ties). A QA-match bonus adds an uncapped score addend when a stored question scores ≥ `QA_EXAMPLE_MIN_SCORE=0.75`. Tables below `RELATIVE_FLOOR=0.15` of the top (pre-bonus) score are pruned. Explicit section-reference detection (`section_alias.py`), business-dictionary alias pinning (`detect_pinned_table`), and a "strong match" tier (literal/token ratio ≥ `STRONG_MATCH_MIN_RATIO=0.95`) can override the fused ranking outright as harder-than-embedding business rules.

**Config reference (`backend/sql_agent/sqlcore/config.py`, `sql_agent/.env`).** `EMBED_MODEL` (`BAAI/bge-large-en`), `EMBEDDING_DIR` (`<repo>/embeddings`, in practice `embeddings_5.5`/`embeddings_6.0`), `QUERY_PREFIX`, `TOP_K_TABLES=3`, `TOP_K_COLUMNS=5`, `SHORTLIST_K=8`, `MINIMAL_MULTIPART_NUM_PREDICT=1024`, `OLLAMA_URL` (no hardcoded default — a previously-hardcoded public IP was removed as part of H-07 hardening), `OLLAMA_MODEL` (default `hf.co/defog/sqlcoder-7b-2:Q5_K_M`), `OLLAMA_NUM_CTX=8192`, `OLLAMA_KEEP_ALIVE=30m`, a `MODEL_PROFILES` dict (in-code, per-model prompt_style/dialect_hint/temperature/num_predict for `gpt-oss:120b-cloud`, `qwen2.5:7b`, `llama3.1:latest`, the active `hf.co/defog/sqlcoder-7b-2:Q5_K_M` using `"ddl"` prompt style, and `hf.co/mradermacher/Arctic-Text2SQL-R1-7B-GGUF:Q5_K_M`), `BUSINESS_SEMANTICS_LEVEL` (default `"off"`; levels off/units/metrics/aggregation/dimensions/derivation), the signal weights listed above, and Oracle connection settings `DB_HOST`/`DB_PORT` (1521)/`DB_SERVICE` (XE)/`DB_USER`/`DB_PASSWORD` (no hardcoded fallback, `DB_MAX_ROWS=100`, `DB_STATEMENT_TIMEOUT_MS=30000`). The legacy `SQL_SELECTOR_MODEL`/`SELECTOR_MODEL` env vars still appear in some config files but are dead — the selector no longer calls an LLM.

#### Models in the SQL Agent

| Model | Role | Where configured |
|---|---|---|
| `BAAI/bge-large-en` (local SentenceTransformer) | Embeds schema/column/row-label/QA/concept docs and user queries | `EMBED_MODEL` / `SQL_EMBED_MODEL` |
| `hf.co/defog/sqlcoder-7b-2:Q5_K_M` (Ollama, remote proxy) | NL → SQL generation | `OLLAMA_MODEL` / `SQL_OLLAMA_MODEL` |
| `phi3:mini` (Ollama) | DB Q&A only — reformats fetched rows into prose, never invents data | `APP_DB_BEAUTIFY_MODEL` |

> **Drift issues:** `APP_DB_BEAUTIFY_MODEL=phi3:mini` is configured but was found to be *absent* from the live remote Ollama proxy's model list (`doc/INTENT_GAP_ANALYSIS.md`) — a live, measured misconfiguration, not a guess. And the generator scripts that *build* schema.json / qa_pairs.json / the FAISS indexes live entirely outside this repository (a separate "Embedding maker" tool) — only their output artifacts ship here.

---

## 3 · Common Runtime Request Flow

### Auth / user / tenant / version context

There is **no auth middleware and no JWT signature verification inside FastAPI**. Identity fields (`login_id, user_id, role_id, asp_session`, and — 6.0 only — `tenant_id, domain, jwt`) arrive as plain fields on the request body's Pydantic model and are trusted as explicit function parameters all the way down into `decide()` [`models.py:9-29, agent/__init__.py:818-825`]. For 5.5, `asp_session` is an opaque cookie value forwarded to an external .NET API that owns the real session check. For 6.0, the JWT arrives via a `postMessage CHATBOT_AUTH` handshake from the embedding iframe and is threaded through per-request `contextvars` — but **no code path was found that cryptographically verifies that JWT inside this backend**; it is passed through to the external .NET V6 API for verification. `tenant_id`/`login_id`/`role_id` supplied by the client are trusted as-is. This is a real, code-confirmed trust-boundary decision, not a search gap — flagged again in §10.

```
Request body {login_id, user_id, role_id, asp_session, tenant_id?, domain?, jwt?}
  ▼
_make_repo_scope(tenant_id, domain, jwt)                                    [main.py:284-311]
  ▼
version_config.resolve_tenant_id()                                          [version_config.py:80-92]
  explicit tenant_id trusted as-is  ─or─  domain → cached XML_Tenant.xml lookup
  ▼
repo_root_for_tenant() = APP_600_REPO_ROOT\{TenantId}   (6.0)                [version_config.py:95-102]
  vs. BASE_REPO_PATH                                     (5.5, unconditional)
  ▼
repo_scope() context manager → contextvars (_active_root/_active_tenant_id/_active_jwt)
  coroutine-scoped, so concurrent requests for different tenants never cross-contaminate  [version_config.py:105-131]
  ▼
scoped_session_id() prefixes session_id with tenant_id → isolates agent._session_context   [version_config.py:142-161]
  ▼
role resolution: auth_service.get_user_role_id(login_id) reads XML_User.xml if role_id
  not supplied; get_allowed_form_ids(login_id) → DepartmentId → XML_Dept.xml → FormIds set  [auth_service.py:111-158, 282-311]
  (AUTHORIZATION_ENABLED=false or REQUIRE_AUTH bypass ⇒ allowed_form_ids=None ⇒ unrestricted)
```

**Version handling:** `APP_VERSION` is read once at process start into a module-level constant — fixed for the process's lifetime. 5.5 and 6.0 therefore run as two *separate OS processes* sharing one code checkout, each launched with its own `ENV_FILE` (hence its own `BACKEND_PORT`, `LOG_DIR`, DB/repo paths, embeddings_5.5 vs embeddings_6.0). Only *tenant*, not version, varies per-request. Model/embedding selection is **not** version-branched anywhere in code — purely env-var driven, identical code path regardless of `APP_VERSION`.

### Request routing — is there an intent classifier?

Yes, but it is a staged, mostly rule-based cascade, not one ML classifier. The LLM is gated *off* by cheaper deterministic checks first, and used only as a fallback in two of five steps.

```
POST /chat → i18n.translate_inbound() → decide(text, session_id, login_id, ...)     [agent/__init__.py:818]
  STEP 0  conversational/small-talk LLM classifier — invoked ONLY if nothing below matched   [:763,1674]
  STEP 1  workflow regex/fuzzy matchers → get_status / generate_instance / schedule_report /
          compare_reports (deterministic dispatch)                                            [:1692-1785]
  STEP 2  DB-QA intent (XML-backed): regex classifier + embedding-similarity exemplar index    [:1790-1809]
  STEP 3  SQL-agent keyword trigger (_DB_QUERY_KW_RE) → backend.sql_agent.handle_db_query       [:1836-1845]
  STEP 4  LLM intent+entity extraction (llm_extractor) — fallback only; dates/report-name
          are ALWAYS extracted deterministically via regex/dateutil, never by the LLM,
          specifically to prevent hallucinated entities                                        [llm_extractor.py:1063-1069]
```

`/guided`, `/compare-execute`, and `/explain-category` are separate endpoints that *bypass* this cascade entirely by design — guided is explicitly deterministic/button-driven with no LLM call anywhere in `guided.py`.

---

## 4 · Chatbot Functional Flows

### Guided Workflow Menu
| | |
|---|---|
| **Purpose** | Clickable 5-button menu (status / generate / schedule / compare / retrieve-from-DB) instead of free text. |
| **Entry point** | `guided_step()` [`guided.py:165-356`] |
| **Context** | session_id, asp_session, login_id (drives `can_generate_instance`/`get_allowed_form_ids`) |
| **AI model** | None — explicitly zero LLM calls in this file [`guided.py:1-9`] |
| **Non-AI logic** | Stage-machine dict keyed by session_id; fuzzy text match against Returns.xml; regex Request-ID detection |
| **Fallback** | Unrecognized login_id → "account not recognised"; disallowed action → generic no-access error |

### Report / Instance Status Check
| | |
|---|---|
| **Purpose** | Latest (or specific) reporting-date run status for a return, incl. error counts. |
| **Data sources** | Returns.xml (master list) · XML_InstanceLog (run history) · error/render files under `instance_base_dir()/<form_id>/` |
| **Processing** | 100% deterministic XML parsing + status classification + error-category counting [`report_lookup.py`] |
| **AI model** | None directly — a hook line ("Generating error explanations…") leads into the Error Explanation flow, which is itself hybrid |
| **Output** | `result_type`: final / ask_previous / disambiguation / date_selection / run_selection, carrying download_url + error_category_counts |

### Instance Generation
| | |
|---|---|
| **Purpose** | Trigger a new XBRL instance/return submission. |
| **Entry point** | `_handle_generate()` → `_finalize_generation()` → `_handle_gen_date()` [`agent/__init__.py:3716,3508,3617`] |
| **Data sources** | Returns.xml fuzzy match · auth_service permission check · downstream .NET API (`DOTNET_API_URL` 5.5 / `DOTNET_V6_API_URL` 6.0) |
| **AI model** | None identified |
| **Fallback** | Permission denial handled centrally in `_finalize_generation` |

### Report Scheduling
| | |
|---|---|
| **Purpose** | Queue a future instance-generation run. |
| **Entry point** | `_handle_schedule()` [`agent/__init__.py:3284`] |
| **Processing** | Deterministic date/time extraction (`extract_schedule_datetime`), disambiguates a message containing both a reporting date and a schedule date by anchor-phrase proximity [`llm_extractor.py:783-967`] |
| **AI model** | None — explicitly deterministic by module docstring |

### Instance Comparison — the clearest deterministic+LLM hybrid
| | |
|---|---|
| **Purpose** | Diff two XBRL instances of the same return (typically two reporting dates) into a variance table + narrative. |
| **Entry points** | `_handle_compare` → `_compare_with_name` → `_run_comparison`; or direct `execute_comparison()` for the `/compare-execute` HTTP endpoint (bypasses intent detection) [`agent/__init__.py:2213,2461,2549,2726`] |
| **Data sources** | Candidate instance list from `instance_service.get_instances_for_report()` (scans `{INSTANCE_BASE_DIR}/{report_id}/*.xml`) · Custom Return JSON via `importance_json.get_importance_from_json()` — **optional** enrichment only |
| **Processing** | Load both instances concurrently (Arelle, off-event-loop) → `compute_variance()`: 100% deterministic — canonicalize, align on (concept, context_key), diff/% change, importance+magnitude ranked sort |
| **AI model** | `OLLAMA_COMPARE_MODEL` (default `llama3.1:latest`) generates exactly 5 markdown bullets, ≤22 words each, strictly grounded in the given numbers [`xbrl_comparator.py:1459,1561-1620`]. Additive only — `_normalise_bullets()` returns "" on failure rather than blocking; the table always renders even if the narrative times out (measured ~140s CPU latency vs. an 8s inline budget) |
| **Non-AI logic** | The diff itself, always. The LLM never computes a number — only narrates ones already computed. |
| **Output** | `result_type: "variance_table"` with variance_data/all/meta + llm_summary |
| **Fallback** | Arelle load exception → generic "unable to compare" error; expired comparison session → explicit "session not found or expired"; missing importance JSON → silently degrades to movement-only ranking, never an error |

### Error Explanation — formula / dimensional / XBRL-schema
| | |
|---|---|
| **Purpose** | Turn raw validator error-file rows into grounded, plain-language explanations, batched by category. |
| **Entry point** | `explain_category_for_report()` [`agent/__init__.py:4081`], called after a status check surfaces `error_count>0`, or via an explicit "Explain Next Errors" pagination action. |
| **Required context** | `error_file_path` (required, else explicit error) · `category` (formula_error / xbrl_schema / dimensional) · `form_id` (drives routing) · `offset` (pagination) · `lang` |
| **Data sources** | Error HTML file at `error_file_path` (required) · XBRL instance document *if available* — resolved by matching the SAME run's `ErrorDocPath` basename in the instance log, deliberately not a folder scan, to avoid attributing one filing's values to a neighbouring run · Taxonomy index, preferring the folder from the instance's own `schemaRef` over the form's default (documented as sometimes wrong) · Custom Return JSON for 4000-series enrichment (needs verification of exact call site) |
| **Processing** | Deterministic HTML/table parse (`parse_formula_errors_v2` / `parse_dimension_errors`) → evidence-building (`build_evidence`: concept label, observed dimensions from the instance doc or inferred from context-id naming and explicitly labelled as an inference) → deterministic template explanation → optional LLM phrasing |
| **AI model** | `OLLAMA_MODEL` (default `llama3.1:latest`) via the shared `error_llm.phrase()` layer. Given ONLY an already-verified structured payload — never raw HTML, never the taxonomy file, never asked to compute anything. |
| **Grounding gate** | `is_grounded()` re-checks the model's raw output against the same payload and **rejects the whole response** if it invents a number, leaks an internal variable id, contradicts the verified relationship, or names an unlisted taxonomy member — falling back to the deterministic template. *"The explanation is never less than correct — only sometimes less fluent."* [`error_llm.py:20-22,187-294`] |
| **Fallback** | No error_file_path → explicit error · unsupported category → explicit error · parse exception → generic retry message · missing instance/taxonomy → degrades to inference-labelled evidence, never blocks · LLM unreachable/ungrounded → silent fallback to deterministic template |

### Database Q&A (XML-backed application data)
| | |
|---|---|
| **Purpose** | Answer fixed-taxonomy questions about users/departments/returns/submissions from the XML repositories (distinct from the free-form SQL Agent). |
| **Entry point** | `db_qa_router.check_new_taxonomy_intent_full / check_db_qa_intent / handle_db_qa_query` [`agent/__init__.py:1790-1875`] |
| **Processing** | Regex + slot extraction, supplemented by a small embedding-similarity index over hand-written exemplar phrasings (reuses the SQL Agent's loaded SentenceTransformer instance) — not schema retrieval, just intent matching against a taxonomy of exemplars |
| **AI model** | Optional beautifier only: `phi3:mini` reformats already-fetched rows into prose (max 30 records/6000 chars, "never invent data"), gated by `APP_DB_ENABLE_BEAUTIFY` |

### Multilingual
| | |
|---|---|
| **Languages** | English, French, Arabic, Hindi (default set, overridable via `SUPPORTED_LANGUAGES`); Arabic is the only RTL language. Anything unsupported silently falls back to English. |
| **Detection** | None — `lang` is a client-supplied tag, only normalized (BCP-47 `fr-CA→fr`), never inferred from text. |
| **Where it happens** | A boundary around an English-only pipeline, never in-language prompting: `translate_inbound()` before `decide()`, `translate_outbound()` after. Routing itself is always English regex/FAISS (embedder is `BAAI/bge-large-en`). |
| **Model** | Local Ollama LLM, `qwen3:14b` by default (`TRANSLATION_MODEL`); a separate override, `aya-expanse:8b`, exists specifically for `/compare-summary` because qwen3:14b exceeded even a 180s budget on that endpoint's prose. |
| **Scope** | Only 8 whitelisted prose fields are ever translated outbound (response_text, llm_summary, db_summary, db_beautified, status_note, accuracy_hint, more_info_hint, download_label) — SQL/report names/options/IDs are never sent to the model. Identifiers/numbers/dates are masked before translation and restored after. |
| **Fallback asymmetry** | **Inbound failure is fatal by design** — `decide()` is never called; the user gets a static pre-translated error message. **Outbound failure is not fatal** — a field simply stays in English with a visible note appended, because "a correct answer in the wrong language beats no answer." |
| **Kill switch** | `MULTILINGUAL_ENABLED` (default false) makes both translation functions byte-identical no-ops. |

### Speech-to-Text
| | |
|---|---|
| **Entry point** | `POST /speech-to-text` [`main.py:745-835`] — a live route, distinct from the offline `eval/stt/` benchmarking harness |
| **Model** | Not in-process — a remote HTTP Whisper microservice (`STT_BASE_URL`, task hardcoded to `"transcribe"`, never `"translate"`, to keep translation strictly the job of i18n). Eval filenames suggest `large-v3-turbo`; exact serving library unconfirmed. |
| **Flow** | Browser MediaRecorder → multipart upload → backend validates size/enable flag → forwards to Whisper service → returns transcript to the frontend, which places it in the input box for the user to review and explicitly submit as a normal chat message. **Re-entry into the chat pipeline is never automatic.** |
| **Failure** | Disabled → 503 · empty/oversized upload → 400/413 · remote timeout/error → 503 "Unable to transcribe audio right now," deliberately with no textual fallback ("a failed transcription has nothing to degrade to") |

---

## 5 · Complete AI Model Inventory

Every distinct model call found anywhere in the system, in one place. "Local" means an in-process model loaded by this backend at import time; "remote Ollama" means an HTTP call to a shared Ollama instance/proxy that is not part of this backend's own process. Model names are the `.env` defaults — an operator can repoint any of them via the listed variable without a code change.

| Model | Type | Used in flow / step | Input | Output | Config variable |
|---|---|---|---|---|---|
| `BAAI/bge-large-en` | Local SentenceTransformer | SQL Agent retrieval — embeds schema/column/row-label/QA/concept docs at build time and the user's question at query time; DB Q&A reuses the same loaded instance for its intent-exemplar index | Table/column/row-label text · user question text | Dense vector for FAISS cosine search | `EMBED_MODEL` / `SQL_EMBED_MODEL` |
| `hf.co/defog/sqlcoder-7b-2:Q5_K_M` | Remote Ollama (SQLCoder-7B GGUF) | SQL Agent — natural language → SQL generation, streamed, with up to 3 correction retries | DDL-style prompt: CREATE TABLE block + types + row-label samples + resolved date literals + question | A single SQL SELECT statement | `OLLAMA_MODEL` / `SQL_OLLAMA_MODEL` |
| `qwen2.5:7b` | Remote Ollama | General chat routing STEP 4 — LLM intent+entity extraction, used only as a fallback when the deterministic regex cascade (STEPS 1–3) found nothing | User message + short conversation history | JSON with `intent` field only — dates/report-name are extracted deterministically, never trusted from this call | `OLLAMA_EXTRACT_MODEL` |
| `qwen2.5:7b` or `llama3.1:latest` (proxy-dependent — see note below) | Remote Ollama | General chat routing STEP 0 — conversational/small-talk classifier, gated off by cheaper deterministic checks and only invoked if nothing else matched | User message | Small-talk vs. task classification | `OLLAMA_MODEL` / `OLLAMA_FALLBACK_MODEL` |
| `llama3.1:latest` | Remote Ollama | Instance Comparison — generates the 5-bullet variance narrative layered on top of the deterministic diff; never computes a number itself | Report name, period labels, up to N ranked variance rows with values/%-change/importance context | Exactly 5 markdown bullets, ≤22 words each, strictly grounded — "" on failure/timeout, never blocks the table | `OLLAMA_COMPARE_MODEL` |
| `llama3.1:latest` | Remote Ollama | Error Explanation — phrases already-verified formula/dimensional/schema error evidence into prose, via the shared `error_llm.phrase()` layer | A structured, pre-verified evidence payload (labels, numbers, relationship, taxonomy context) — never raw HTML or the taxonomy file itself | A single-line JSON object with the requested prose fields; rejected and replaced by a deterministic template if the grounding gate (`is_grounded()`) finds an invented number, leaked variable id, or unlisted taxonomy member | `OLLAMA_MODEL` |
| `qwen3:14b` | Remote Ollama | Multilingual boundary — translates the 8 whitelisted outbound prose fields, and the user's inbound message, at the edges of an otherwise English-only pipeline | Masked prose (identifiers/numbers/dates protected) + target language | Translated prose with protected entities restored | `TRANSLATION_MODEL` |
| `aya-expanse:8b` | Remote Ollama | Multilingual — `/compare-summary` narrative translation only, a separate override because `qwen3:14b` measured over an 180s budget on this endpoint's longer prose | Compare-summary narrative text + target language | Translated narrative | `COMPARE_SUMMARY_TRANSLATION_MODEL` |
| Whisper (`large-v3-turbo` inferred from eval filenames — exact serving library needs verification) | Remote HTTP microservice (not Ollama) | Speech-to-Text — transcription only; `task` is hardcoded to `"transcribe"`, never `"translate"`, to keep translation strictly i18n's job | Raw audio bytes (webm/ogg/mp4) + optional UI-language hint | `{text, language, language_probability, duration, model}` — transcript is placed in the input box, never auto-submitted | `STT_BASE_URL` |

> **Removed, not present:** an earlier version of the SQL Agent called an instruct LLM to arbitrate ambiguous table shortlists during retrieval (a "selector model"). It was removed for latency and replaced with a deterministic heuristic — `SQL_SELECTOR_MODEL`/`SELECTOR_MODEL` still appear in some config files but the code comment explicitly states this model "no longer exist[s]" in the active path.

> **Needs verification:** STEP 0's exact model identity is the one item in this inventory not pinned to a single confirmed name across all research passes — one trace attributed it to `OLLAMA_MODEL` (shared with error explanation), another surfaced a distinct `OLLAMA_FALLBACK_MODEL` env var whose code comment says "must be wired up" to actually take effect. Confirm which is live before treating this row as final.

---

## 6 · SQL Agent — Failure Handling Reference

| Failure | Behavior |
|---|---|
| Retrieval throws | Generic "unable to process" response, logged server-side |
| No candidate tables found | Explicit "No matching tables found — try rephrasing" |
| A FAISS index file is missing | That signal silently contributes nothing — not treated as an error |
| `schema.json` missing/corrupt | Treated as an empty catalog, logged — deliberately chosen over raising |
| Ollama unreachable / timeout (300s) / HTTP error | Circuit breaker opens for 30s; one retry; then "SQL generation failed. Please try again." |
| Generated SQL invalid after 3 retries | Logged to `eval/results/hallucination_log.jsonl` for offline analysis; execution is blocked |
| Oracle connection failure (query) | Generic "unable to retrieve" to the user; real error logged only server-side |
| Oracle connection failure (dry-run only) | Returns `ok=True` — deliberately: "the dry run is an accuracy gate, not an availability gate" |
| `EMBEDDING_DIR` for the active APP_VERSION missing | Hard fail at startup — no cross-version fallback |

---

## 7 · Frontend & API Flow

React SPA (`frontend/src`), no Redux — identity read once at load from URL params with sessionStorage persistence, sent as JSON body fields (never headers) on every call. Language switching is pure client state, attached as `lang` on the next request.

| Functionality | Endpoint | Frontend trigger |
|---|---|---|
| Send chat message | `POST /chat` | `sendMessage()`, normal submit |
| Guided menu / stepper | `POST /guided` | welcome-card action button, or each stepper reply |
| Instance comparison | `POST /compare-execute` | "Compare Instances" click |
| Comparison AI narrative | `POST /compare-summary` | auto-fired after the variance table renders |
| Error category explanation | `POST /explain-category` | "Explain … Errors" button |
| Voice input | `POST /speech-to-text` | mic recorder stop |
| Cancel in-flight request | `POST /stop` | Stop button / voice cancel |
| Thumbs up/down | `POST /feedback` | `FeedbackPrompt` on a completed reply |
| Gate visible guided actions | `GET /allowed-actions` | on load |

Rendering is fully discriminated: the backend's `ChatResponse.result_type` field (guided_menu, guided_input, db_result, db_qa_result, date_selection, instance_selection, variance_table, ask_previous, sched_confirm, final) drives which UI `MessageBubble.jsx` renders — a real switch, not pre-rendered HTML from the server. Error cards carry a second-level discriminant, `kind` (headline/locator/matrix/fix/details/rule/values/points/note).

---

## 8 · Deployment & Configuration Flow

```
Browser ── IIS site ──▶ static frontend build (React dist)
                    └─ URL Rewrite: ^api/(.*) ──▶ http://127.0.0.1:8001/{R:1}     [frontend/public/web.config]
                                                    │  (hardcoded port — must be
                                                    │   kept in sync with .env
                                                    │   BACKEND_PORT by hand;
                                                    │   no automated sync found)
                                                    ▼
                                         uvicorn (service_server.py, reload=False)
                                              backend.main:app
                                              │  ENV_FILE lets a second instance
                                              │  (5.5 or 6.0) run on its own port/
                                              │  log dir from a separate .env
                                              ▼
                                         Ollama (remote proxy) · Oracle DB · XML/XBRL repo
```

No Docker, no nginx, no systemd unit found anywhere in the repo — `doc/APP_OVERVIEW.md` confirms: "deployment is direct-on-Windows (uvicorn + IIS/.NET-hosted iframe embed)." `dev_server.py` (autoreload, watches only `backend/`) is dev-only; `service_server.py` (no reload) is the production launcher — both read `BACKEND_PORT`/`ENV_FILE` identically.

### Configuration reference (names and purpose only — no secret values)

| Variable | Purpose | Secret? |
|---|---|---|
| `APP_VERSION` | 5.5 (flat repo) vs 6.0 (tenant-scoped repo) mode switch | No |
| `BASE_REPO_PATH` / `APP_600_REPO_ROOT` | Repository roots per version | No |
| `BACKEND_PORT` / `LOG_DIR` / `ENV_FILE` | Per-process port, log directory, alternate .env — lets 5.5 and 6.0 coexist without colliding | No |
| `CORS_ORIGINS` | Explicit allow-list (not wildcard) for cross-origin requests | No |
| `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_EXTRACT_MODEL`, `OLLAMA_COMPARE_MODEL`, timeouts | LLM connection + per-flow model/timeout tuning | URL only, not credential |
| `ORACLE_DSN/HOST/PORT/SERVICE/USER/PASSWORD` | Warehouse connection for SQL Agent | **Yes — found in plaintext in .env.deployment** |
| `TRANSLATION_MODEL`, `MULTILINGUAL_ENABLED`, `SUPPORTED_LANGUAGES` | i18n model + feature flags | No |
| `STT_ENABLED`, `STT_BASE_URL`, `STT_MAX_BYTES/SECONDS` | Speech-to-text feature flags + limits | No |
| `AUTHORIZATION_ENABLED`, `REQUIRE_AUTH`, `AUTH_TTL_SEC` | Department/role permission enforcement toggle + cache TTL | No |
| `APP_DB_ADMIN_ROLE_ID`, `APP_DB_ENABLE_BEAUTIFY`, `APP_DB_BEAUTIFY_MODEL` | DB Q&A behavior | No |
| `DOTNET_API_URL` / `DOTNET_V6_API_URL` | Legacy .NET instance-generation API endpoints per version | No |

> **⚠ Secrets in the repository.** Both `.env` and `.env.deployment` at the Chat-System root, and `.env` at the TrendAnalysis_JSON_Extractor root, were found to contain live Oracle credentials in plaintext, tracked in version control. This should be rotated and moved to a secrets manager before handover; `.env.example` is the correct placeholder-only template to keep in the repo.

---

## 9 · Logging, Debugging & Testing

Plain-text daily-rotating logs (`logs/YYYY-MM-DD.log`, midnight rollover), format `timestamp | LEVEL | module:funcName | message`. No structured JSON logging — tracing a single request means grepping the day's file for its `session=<id>` (present on nearly every line of that turn) or `request_id=` (present on cancellation/exception paths). `LOG_DIR` lets 5.5 and 6.0 write to separate directories (`logs` vs `logs_6.0`), confirmed present on disk. Feedback persists separately to `logs/feedback.jsonl`.

**Testing:** 44 pytest files under `backend/tests/` spanning unit logic (i18n masking, dimension taxonomy, variance datasets), auth/tenant isolation, and API integration (STT endpoint, stop-request, DB-QA integration). Tests are **not hermetic** — the root `conftest.py` loads the real `.env` before any backend import, so a test run can hit the real remote Ollama proxy rather than a mock. Separately, `eval/` is model-behavior evaluation, not unit testing: `eval/model_bench` benchmarks intent-extraction model arms against a hand-labeled 56-query set; `eval/multilingual` LLM-judges the translate-wrap-translate pipeline; `eval/stt` benchmarks Whisper configurations; `eval/results/hallucination_log.jsonl` is both an eval artifact and a live design-justification trail for the SQL Agent's join-graph enforcement rule.

---

## 10 · Security Flow

### Confirmed protections
- Path-traversal guard on `/download-file`: digits-only form_id, basename-only filename, resolved-path containment check
- CORS: explicit origin allow-list, not a wildcard
- Tenant isolation via coroutine-scoped `contextvars`, not global mutable state — covered by a dedicated test file
- SQL Agent: regex allow-list validator (SELECT-only, banned DML/DDL, table/column/join allow-lists) plus an Oracle EXPLAIN-PLAN dry run before any execution
- Auth cache keyed by `(tenant_id, login_id)` composite, preventing cross-tenant permission-cache bleed

### Gaps to flag for handover
- No JWT signature verification found inside FastAPI — tenant_id/login_id/role_id are trusted from the client-supplied body
- `AUTHORIZATION_ENABLED=false` disables all department/role checks entirely — a deliberate dev bypass switch that must never be left off in production
- No rate-limiting middleware anywhere — only a concurrency semaphore on STT, not a rate limit over time
- Live Oracle credentials committed to the repo in plaintext (see §8)
- SQL-injection defense is a bespoke regex validator over LLM-generated SQL, not a real SQL parser/AST — a reasonable mitigation for this specific hallucination threat model, but with unfuzzed edge-case risk

---

## 11 · Reference Matrices

### Data source → storage → consumer

| Source | Stored where | Consumed by |
|---|---|---|
| XBRL taxonomy (.xsd + linkbases) | Filesystem, per-return taxonomy folder | Custom JSON generator (Arelle) · live comparison/error-explanation taxonomy lookups |
| Return repo (Mapping_N.xml, XML_Query.xml) | Filesystem, per return_code | Custom JSON generator Stage B (DB-column join) |
| Custom Return JSON | `<repo>/Json/<form_id>.json` | Instance comparison (optional) · 4000-series formula-error enrichment (needs verification) |
| XML repositories (Returns/User/Dept/Role/InstanceLog) | Filesystem, version-specific paths | Status check, auth, guided workflow, DB Q&A |
| XBRL instance documents | Filesystem, `Instance/<form_id>/` | Comparison, error-explanation dimension evidence |
| Validator error HTML files | Filesystem, `Instance/<form_id>/` | Error explanation parsers |
| SQL Agent schema.json / qa_pairs.json / FAISS indexes | `embeddings_5.5/` or `embeddings_6.0/` (prebuilt elsewhere, shipped as static artifacts) | SQL Agent retrieval |
| Oracle regulatory warehouse | External Oracle instance | SQL Agent execution · Custom JSON stats refresh |

### Functionality → data → model

| Functionality | Required data | AI model | Output |
|---|---|---|---|
| Guided menu | Returns.xml, auth | None | guided_menu / guided_input |
| Status check | Returns.xml, InstanceLog | None | final / date_selection |
| Instance generation | Returns.xml, auth, .NET API | None | confirmation |
| Scheduling | Returns.xml, auth | None (deterministic date parsing) | sched_confirm |
| Instance comparison | 2 XBRL instances (required); Custom JSON (optional) | llama3.1 — 5-bullet narrative only | variance_table |
| Error explanation | Error HTML (required); instance doc + taxonomy + Custom JSON (optional) | llama3.1 via grounded error_llm.phrase() | final + error_details[] |
| DB Q&A | XML repositories | phi3:mini — optional beautifier only | db_qa_result |
| SQL Agent | schema.json, FAISS indexes, Oracle | bge-large-en (embed) + sqlcoder-7b-2 (generate) | db_result |
| Multilingual boundary | — | qwen3:14b / aya-expanse:8b | translated prose fields only |
| Speech-to-text | Audio blob | Whisper (remote, large-v3-turbo inferred) | transcript (manual re-entry) |

---

## 12 · Worked End-to-End Examples

### A. "Explain the formula errors on my 4000-series return"

```
Status check surfaces error_count>0 → user clicks "Explain Errors"
  → POST /explain-category {error_file_path, category:"formula_error", form_id, offset:0}
  → parse_formula_errors_v2(html) — deterministic table parse
  → explain_formula_rules(rows, form_id) — evidence: values, operator meaning, business labels
  → optional 4000-series Custom-JSON enrichment
  → error_llm.phrase(payload) — llama3.1, JSON-only output, grounding-gate checked
  → is_grounded() rejects any invented number/leaked variable id → falls back to template if so
  → result_type:"final", error_details[], data:{has_more, next_offset}
  → MessageBubble renders card by "kind" (headline/locator/matrix/fix)
```

### B. Instance comparison across two reporting dates

```
User: "Compare Instances" → _handle_compare → candidate list from InstanceLog scan
  → user picks "1 vs 3" → _run_comparison
  → asyncio.gather(load_xbrl_facts(A), load_xbrl_facts(B))  — Arelle, off event loop
  → compute_variance() — deterministic diff, importance-ranked using Custom Return JSON if present
  → generate_llm_summary() — llama3.1, 5 grounded bullets, 8s budget, "" on failure/timeout
  → result_type:"variance_table" → frontend renders table + VarianceChartModal
  → /compare-summary auto-fires to backfill the narrative asynchronously if it wasn't ready
```

### C. "What was the credit exposure for domestic derivatives last quarter?"

```
STEP3 keyword match → backend.sql_agent.handle_db_query(question)
  → embed question (bge-large-en) → exact-QA check (0.99 sim) → else 7-signal FAISS+BM25 fusion
  → select_tables() deterministic narrowing → build_prompt() DDL-style with resolved date literal
  → generate_sql() via SQLCoder-7B (remote Ollama) → validate_sql() + dry_run_sql() (EXPLAIN PLAN)
  → up to 3 correction retries → execute_query() (pooled oracledb, fetchmany≈100)
  → db_columns/db_rows/db_sql returned as-is, no NL summarization layer
  → frontend renders a plain results table
```

---

## 13 · Production Readiness

| Area | Status | Note |
|---|---|---|
| Core chat/guided/compare/error/SQL flows | ✅ Implemented | Traced end-to-end, deterministic cores with grounded LLM narration layers |
| Tenant isolation (6.0) | ✅ Implemented | Contextvar-scoped, has a dedicated isolation test |
| JWT verification | ⚠ Partially implemented | Forwarded, not locally verified inside FastAPI |
| Secrets management | 🔴 Not production-ready | Live DB credentials committed in plaintext across both repos |
| Rate limiting | 🔴 Not found | No middleware or per-user throttling anywhere |
| Structured logging / request correlation | ⚠ Partially implemented | Plain-text logs, session_id greppable but no structured tenant_id field on the hot path |
| SQL Agent embedding build pipeline | ❓ Needs verification | Generator scripts live outside this repo entirely; only output artifacts ship here |
| Custom JSON → chatbot hand-off path | ❓ Needs verification | No copy-step/mount config found connecting the two repos at runtime |
| Test hermeticity | ⚠ Partially implemented | pytest suite loads the real .env; can hit live remote Ollama |

---

## 14 · Known Limitations & Troubleshooting

### Known limitations

- **LLM fallback latency** — a measured self-test (`doc/INTENT_GAP_ANALYSIS.md`) found 9 of 52 real questions exceeded a 60s timeout when the deterministic cascade missed and fell through to the LLM fallback, because the shared remote Ollama proxy runs under real inference load. Affects: general chat fallback (STEP 4), comparison/error narratives.
- **Configured-but-unavailable model** — `APP_DB_BEAUTIFY_MODEL=phi3:mini` was measured absent from the live proxy's model list. Affects: DB Q&A beautification only (data itself is unaffected).
- **No taxonomy-version tracking** — the Custom Return JSON generator's "version" is a best-effort regex guess over a path string, not an authoritative field. Affects: confidence in which taxonomy generation a given JSON reflects.
- **output/ vs output6.0/ split is operator convention, not code** — no version flag exists in the extractor; the two directories exist because `OUTPUT_DIR` was pointed at different source trees by hand.

### Troubleshooting playbooks

**Error Explanation is failing**
1. Confirm `error_file_path` was supplied and resolves under `instance_base_dir()/<form_id>`
2. Check whether the matching instance document exists in the same run's InstanceLog row
3. Check the Custom Return JSON's presence/freshness for 4000-series enrichment
4. Check taxonomy folder resolution against the instance's schemaRef, not just the form's default
5. Grep the day's log for the session_id to see which grounding check rejected the LLM output, if any

**Instance Comparison is failing**
1. Confirm both selected instance indices exist in `session["cmp_instances"]` and haven't expired
2. Confirm both instance XML files are Arelle-parseable (check for a load exception in logs)
3. Check Custom Return JSON availability — its absence should degrade, not fail, the ranking
4. If the table renders but no narrative appears, check the 8s LLM budget against the proxy's current latency

**SQL Agent gives an incorrect or failed query**
1. Confirm the active `APP_VERSION`'s `embeddings_5.5`/`embeddings_6.0` folder exists and loaded at startup (a missing folder is a hard crash, not a silent fallback)
2. Check `eval/results/hallucination_log.jsonl` for a matching prior failure pattern
3. Inspect `db_sql`/`db_error` returned in the response for the validator's rejection reason
4. Confirm the question surfaced a candidate table at all — retrieval returning empty degrades to a "try rephrasing" message, not a silent wrong answer

---

---

## 15 · Addendum — Additional Verified Detail (Deep-Dive Pass 2)

This section fills gaps found on a follow-up source pass; nothing above was changed. It documents `backend/main.py` route-by-route, `models.py`, `guided.py`, `version_config.py`, `stt/config.py`, the two server launchers, `agent/router.py`, `agent/generation.py`, `agent/error_explanation.py`, `tools/report_lookup.py`, and the frontend files, at a level of detail not previously captured.

### 15.1 `backend/main.py` — full route inventory

FastAPI app, `title="Report Assistant"`, `version="3.0.0"`. Loads `.env` (or `ENV_FILE` override) and calls `setup_logging()` before importing backend modules, so every module logger is wired from process start.

**Lifespan (`lifespan(app)`)** — an async contextmanager guarded by a module-level `_warmup_done` flag (so uvicorn's autoreloader re-import doesn't re-warm). On startup it: warms the SentenceTransformer + FAISS table/column indexes (`backend.sql_agent.vectorizer`, `.retriever`), the DB-QA intent-exemplar FAISS index (`backend.db_qa.intents.embedding_index`), and the XML app-DB store (`backend.db_qa.xml_store.XMLStore`) — all off the event loop in a thread executor; pings Ollama (`OLLAMA_BASE_URL/api/chat`) for `OLLAMA_EXTRACT_MODEL`/`OLLAMA_MODEL` to keep them warm/resident; logs `i18n.runtime_config()` and `stt.runtime_config()`, warning if either is disabled.

**Routes** (all defined directly on `app`):

| Route | Purpose |
|---|---|
| `POST /chat` | Main chat endpoint. `ChatRequest → ChatResponse`. Resolves per-request tenant repo scope (`_make_repo_scope`), `i18n.translate_inbound`, `backend.agent.decide()`, `i18n.translate_outbound`. |
| `POST /guided` | Deterministic step-by-step guided flow via `backend.guided.guided_step`. Outbound-only translation — inbound messages here are protocol tokens, never translated. |
| `POST /compare-execute` | `CompareRequest → ChatResponse`. Direct pre-staged instance comparison via `backend.agent.execute_comparison`, bypasses intent detection entirely; has its own translation timeout/batching for the (potentially large) variance table. |
| `POST /compare-summary` | Async LLM narrative for an already-rendered variance table (`backend.tools.variance_explain.generate_explanations`); returns `{"llm_summary": str}`. Fired automatically by the frontend right after the variance table renders, so the narrative can "backfill" if it wasn't ready in time. |
| `POST /explain-category` | `ExplainCategoryRequest → ChatResponse`. On-demand error explanation via `backend.agent.explain_category_for_report`. |
| `POST /speech-to-text` | Multipart file upload → `{"transcript", "detected_language", "language_probability"}`. Guarded by `stt.is_enabled()`, size limit `stt_config.max_bytes()`, and a semaphore `_stt_slots = asyncio.Semaphore(stt_config.concurrency())`. |
| `POST /stop` | Cancels an in-flight task by `request_id` — cooperative cancellation via an `_inflight_tasks` dict of `asyncio.Task`. |
| `POST /feedback` | Thumbs up/down, persisted via `backend.utils.intent_log.log_feedback` to `logs/feedback.jsonl`. |
| `GET /health` | `{"status": "ok"}`. |
| `GET /download-file` | Serves render/error files; `form_id` sanitized to digits-only, `filename` basename-only, resolved path checked for containment against `render_base_dir()`/`instance_base_dir()`. |
| `GET /reports` | List of all report names from `returns.xml` — feeds guided-mode autocomplete. |
| `GET /allowed-actions` | Subset of guided-menu actions a given user may perform (`backend.guided._allowed_actions`). |
| `GET /status-errors/{job_id}` | Polls a background LLM error-enrichment job (`backend.agent._error_jobs`). |

**Middleware**: `CORSMiddleware` (origins from `CORS_ORIGINS`, default `http://localhost:3000`; `allow_credentials=True`; all methods/headers allowed). A global `@app.exception_handler(Exception)` returns a generic 500 JSON body and logs the real exception only server-side (`log_exception`).

**Multi-tenant wiring**: `_make_repo_scope(tenant_id, domain, jwt)` is a no-op under `APP_VERSION=5.5`; under `6.0` it resolves `TenantId` via `version_config.resolve_tenant_id`/`repo_root_for_tenant` and enters a `version_config.repo_scope` contextvar scope for the duration of the request.

**API docs are gated off by default**: `/docs`, `/redoc`, `/openapi.json` only mount if `ENABLE_API_DOCS=true` (part of the H-07 hardening pass — off by default in production).

### 15.2 `backend/models.py` — request/response schema reference

All Pydantic models, `from __future__ import annotations`:

- **`ChatRequest`** — `message` (1-2000 chars), `session_id`, `asp_session`, `login_id`, `conversation_history: list[dict]`, `beautify: bool=True`, `user_id`, `role_id`, `request_id` (enables `/stop`), `lang` (BCP-47: en/fr/ar/hi); plus, only under `APP_VERSION=6.0`: `tenant_id`, `domain`, `jwt`.
- **`ChatResponse`** — the universal response envelope: `intent`, `report_name`, `response_text`, `need_clarification`, `result_type` (final/variance_table/disambiguation/date_selection/error/stopped/…), `options: list[str]`; variance fields (`variance_data`, `variance_all`, `variance_meta`, `variance_label_a/b`, `llm_summary`, `llm_summary_is_draft`); `instances_data`; `download_url`/`download_label`; `status_note`; `error_details: list[dict]`; a generic `data: dict` catch-all; SQL Agent fields (`db_columns`, `db_rows`, `db_sql`, `db_error`, `accuracy_hint`, `needs_more_info`, `more_info_hint`); XML/App-DB Q&A fields (`db_intent`, `db_found`, `db_records`, `db_summary`, `db_beautified`, `db_qa_data`); `job_id` for async error enrichment.
- **`CompareRequest`** — `session_id`, `instance_a`/`instance_b` (0-based indices, ≥0), `request_id`, `lang`, plus v6.0 tenant fields. Bypasses intent detection entirely.
- **`CompareSummaryRow`** — one variance row echoed back from the frontend: `concept`, `val_a`/`val_b`, `diff`, `pct_change`, `significant`, regulatory context (`section`, `importance_tier`, `mandated_by`), selection fields (`concept_base`, `context_key`, `unit`, `section_code`, `importance`, `priority`, `importance_matched`).
- **`CompareSummaryRequest`** — `rows: list[CompareSummaryRow]` (max 2000), `label_a`/`label_b`, `report_name`, `request_id`, `lang`.
- **`ExplainCategoryRequest`** — `filename` (bare filename only), `category` (formula_error|xbrl_schema|dimensional), `form_id` (required — the server rebuilds the real path from filename+form_id and never trusts a client-supplied path), `report_name`, `request_id`, `offset` (batching), `lang`, plus v6.0 tenant fields.
- **`FeedbackRequest`** — `rating` (regex `^(up|down)$`), `query`, `intent`, `result_type`, `session_id`.

### 15.3 `backend/guided.py` — state machine detail

Deterministic (zero-LLM) button-driven workflow, keyed by `session_id` in a module-level dict `_guided_sessions`.

- **Stages**: `STAGE_MENU`, `STAGE_STATUS_REPORT`, `STAGE_GEN_REPORT`, `STAGE_SCHED_REPORT`, `STAGE_CMP_REPORT`, `STAGE_DB_QUERY`.
- **`GUIDED_ACTIONS`** — the 5 menu labels ("Check report status", "Generate instance for a report", "Schedule a report", "Perform comparative analysis", "Retrieve data from database") — English protocol tokens matched verbatim, never translated.
- `normalize_confirmation(text)` — locale-aware yes/no matching via `CONFIRMATION_TOKENS` (en/fr/ar/hi).
- `_allowed_actions(login_id)` — filters `GUIDED_ACTIONS` by `can_generate_instance()` (`backend.services.auth_service`).
- `async def guided_step(message, session_id, asp_session, login_id=None) -> dict` — main entry point for `POST /guided`. Action selection sets stage + prompts for a report name; the report-name step is fuzzy-matched directly against `returns.xml` (`report_lookup.get_report_status`/`find_matching_reports`) with **no LLM call**, then clears guided session state so any follow-up routes through `/chat`'s own `_session_context` machinery. Per-stage dispatch: `STAGE_STATUS_REPORT` → `get_report_status`/`get_report_status_by_id_fast`; `STAGE_GEN_REPORT` → `backend.agent._handle_generate`; `STAGE_SCHED_REPORT` → `backend.agent._handle_schedule`; `STAGE_CMP_REPORT` → `backend.agent._handle_compare`; `STAGE_DB_QUERY` → tries the XML-QA classifiers (`check_new_taxonomy_intent`/`check_db_qa_intent` + `handle_db_qa_query`) first, **falling back to `backend.sql_agent.handle_db_query` only if no XML-QA intent matches** — i.e. guided DB queries try structured app-data Q&A before falling through to the free-form NL→SQL agent.
- Fail-closed auth (H-01 fix): denies guided requests when `REQUIRE_AUTH=true` and no `login_id` is present, mirroring `/chat`'s `decide()`.

### 15.4 `backend/version_config.py` — multi-tenant repo routing (not a generic feature-flag file)

- `APP_VERSION = os.getenv("APP_VERSION", "5.5")`; `IS_V6 = APP_VERSION == "6.0"`.
- Under 5.5 (default): inert — `get_active_root()` always returns `backend.config.BASE_REPO_PATH`.
- Under 6.0: `APP_600_REPO_ROOT` is a **required** env var (raises `RuntimeError` if unset, no hardcoded default) plus an `XML_Tenant.xml` tenant registry, cached with TTL `TENANT_REGISTRY_TTL_SEC=3600` and mtime-invalidated.
- `resolve_tenant_id(tenant_id, domain)` — trusts an explicit `tenant_id` from the frontend as-is; otherwise looks up `domain` in the registry.
- `repo_root_for_tenant(tenant_id)` — builds `D:\Repo6\Repo6\{TenantId}`, validated against a strict regex (`_TENANT_ID_RE`) and a known-tenant list, with path-escape protection via `os.path.commonpath`.
- Per-request state lives in `contextvars` (`_active_root`, `_active_tenant_id`, `_active_jwt`), exposed through the `repo_scope` context manager and accessors `get_active_root()`/`get_active_tenant_id()`/`get_active_jwt()`/`get_repo_root_override()`.
- `scoped_session_id(session_id)` prefixes session IDs with the tenant ID under 6.0, preventing cross-tenant collisions in `agent._session_context`.

### 15.5 `backend/stt/config.py` — STT configuration seam

Thin config layer for the remote Whisper-based STT microservice; every function reads `os.environ` at **call time** (not import time), for testability. Keys: `is_enabled()` → `STT_ENABLED` (default true); `base_url()` → `STT_BASE_URL` (no hardcoded default — H-07 hardening, empty string if unset); `transcribe_url()`/`health_url()` → `{base_url}/transcribe`, `{base_url}/health`; `timeout()` → `STT_TIMEOUT` (default 120s; measured ~14s for a 30s clip, ~23s for a 60s clip); `max_seconds()` → `STT_MAX_SECONDS` (default 60); `max_bytes()` → `STT_MAX_BYTES` (default 10 MiB); `language_mode()` → `STT_LANGUAGE_MODE` ("ui" default sends the selected UI language as a hint, vs "auto" lets Whisper detect); `send_hints()` → `STT_SEND_HINTS` (default true); `concurrency()` → `STT_CONCURRENCY` (default 2 — bounds in-flight requests because the remote service serializes transcriptions); `supported_languages()` → `STT_LANGUAGES` (default `"en,fr,ar,hi"`); `runtime_config()` returns all of the above as a dict, logged once at startup by `main.py`. No API key here — this is a self-hosted Whisper HTTP service reached purely by base URL, no auth token in this file.

### 15.6 `dev_server.py` / `service_server.py` — launchers

Both scripts: load `.env` (or `ENV_FILE`), import `BACKEND_PORT` from `backend.config`, call `assert_port_matches_web_config()` (`port_guard.py`) to **fail fast** if the configured port doesn't match the IIS reverse-proxy rewrite rule, then `uvicorn.run("backend.main:app", host=_host, port=BACKEND_PORT, ...)`. `BACKEND_HOST` defaults to `127.0.0.1` (loopback-only, H-07 hardening — reachable only via the local IIS reverse proxy, never directly from the network).

- **`dev_server.py`** — `reload=True`, `reload_dirs=[<root>/backend]` only, `reload_excludes=["logs","frontend","__pycache__",".git",".venv","temp","tmp"]`, `reload_delay=1.0`. Local-development launcher with autoreload.
- **`service_server.py`** — `reload=False`, otherwise identical; the production launcher (code comment: "Server 228 runs both IIS and this backend"). No Windows-service wrapper code in the file itself — it's a plain uvicorn process, presumably wrapped externally (e.g. NSSM/`sc.exe`) to run as a Windows service.

### 15.7 `backend/agent/router.py` — `decide()` control flow in detail

Single function `decide()` (~1,487 lines) is the intent dispatcher behind `/chat`, composed via `from ... import *` from sibling modules: `backend.agent.state` (session state, `STAGE_*` constants, response builders), `.background_jobs`, `.auth_filters`, `.conversational`, `.report_resolution`, `.comparison`, `.scheduling`, `.generation`. `extract_intent_and_entities(*args, **kwargs)` is a thin proxy to `backend.agent.extract_intent_and_entities`, kept so tests that patch that path still work.

`async def decide(user_query, session_id=None, asp_session=None, login_id=None, user_id=None, role_id=None, conversation_history=None) -> dict`:

1. **Auth resolution** — resolves `allowed_form_ids` via `auth_service.get_allowed_form_ids(login_id)`; fail-closed if `REQUIRE_AUTH=true` and no `login_id`; a client-supplied `role_id` is always discarded and re-resolved server-side (a deliberate security fix, not an oversight).
2. **Session bootstrap** — persists `asp_session`; a "reset" keyword clears session state.
3. **Staged multi-turn continuations** — a long chain of `if session.get("awaiting") == STAGE_X` blocks that resume paused flows: `STAGE_DATE`, `STAGE_PREV_DATES`, `STAGE_RUN`, `STAGE_REPORT`, `STAGE_RETURN_QA` (DB Q&A disambiguation), `STAGE_GEN_REPORT`/`STAGE_GEN_DATE` (generate-instance), five `STAGE_SCHED_*` sub-stages (schedule flow), `STAGE_CMP_REPORT`/`STAGE_CMP_FILE` (compare flow). Each checks `_looks_like_new_query` first so the user can escape into a fresh query mid-flow.
4. **Fast-path intent detection** (only reached when not in a staged session) — STEP 0 conversational/small-talk (`_get_conversational_response`, LLM fallback `_classify_conversational`); STEP 1 workflow keyword/GUID fast paths (`_STATUS_KW_RE`, `_CMP_KW_RE`, etc., including instance-GUID status lookup); STEP 2 app/XML Q&A (`check_new_taxonomy_intent_full`/`check_db_qa_intent` → `handle_db_qa_query`); STEP 3 SQL Agent (`_DB_QUERY_KW_RE` keyword trigger → `backend.sql_agent.handle_db_query`).
5. **STEP 4 LLM fallback** — `extract_intent_and_entities()`, then branches on the returned intent: `db_*` → DB Q&A, `query_database` → SQL Agent, `unknown` → deterministic report-name reclassification, `generate_instance`/`schedule_report`/`compare_reports` → respective handlers, default → `get_status`.

Session state lives in `_session_context` (dict keyed by `session_id`, defined in `backend/agent/state.py`): `awaiting`, `pending_options`, `db_intent`/`db_params`, `sched_*`, `last_search_terms`, etc. Effective routing priority: **staged continuation > conversational > workflow keywords (status/generate/schedule/compare) > app/XML DB Q&A > SQL Agent keywords > LLM-based fallback classification.**

### 15.8 `backend/agent/generation.py` — generate-instance flow

Zero LLM calls anywhere in this file — purely deterministic fuzzy matching plus a synchronous .NET API call wrapped in async. Key functions: `_matching_instance_log_rows()` reads `XML_InstanceLog.xml` via `backend.db_qa.xml_store.XMLStore`; `_parse_dtc()` parses `"%d-%b-%Y %I:%M:%S %p"` timestamps; `async _find_new_instance_log_id()` polls up to 8×1s for the newly-created InstanceLog row's Id after a generate call, diffing against a before-snapshot to avoid picking up a stale duplicate row; `async _finalize_generation()` enforces `can_generate_instance` auth (fail-closed under `REQUIRE_AUTH`), validates the reporting date, calls `backend.tools.instance_generator.call_generate_api` (5.5) or `call_generate_api_v6` (6.0, with `tenant_id`/`jwt`), then locates the new instance's Request ID; `async _handle_gen_date()` is a thin wrapper delegating to `_finalize_generation`; `_date_ask_prompt()` builds frequency-specific (Q/M/H/C/Y/B/W/F/HM/E/D) date-format guidance with examples; `async _handle_generate()` is the entry point for the free-text/guided generate flow — pre-auth check, `find_matching_reports`/`fuzzy_report_suggestions` for name resolution, disambiguation handling, then either prompts for a date or calls `_finalize_generation`.

### 15.9 `backend/agent/error_explanation.py` — the thin wrapper around `report_lookup.py`

Triggered by the frontend's "Explain … Errors" buttons. `_is_contained_error_file()` validates a rebuilt error-file path is inside `instance_base_dir()` with an allowed extension (`.xml`/`.html`) — defense against a client supplying an arbitrary path. `async def explain_category_for_report(filename, category, form_id, report_name=None, offset=0, lang="en") -> dict` is the sole public entry point: it rebuilds the real server path via `report_lookup.build_error_file_path(form_id, basename(filename))` (never trusts a client-sent path), then runs the blocking `explain_errors_by_category_for_form()` in a thread executor, batching one page of errors at a time (batch size = `report_lookup._MAX_EXPLAIN = 3`), returning a `ChatResponse`-shaped dict with `error_details` and `data.has_more`/`next_offset`/`total_count` for pagination. The actual LLM-assisted explanation generation lives inside `report_lookup.py` (`explain_errors_by_category_for_form`/`explain_validation_errors`/`explain_formula_errors`), not in this file.

### 15.10 `backend/tools/report_lookup.py` (≈4,850 lines) — report/instance catalog + error-explanation engine

The report/return registry parser, fuzzy report-name matcher, status-result assembler, render/error/instance file-path resolver, and the large dimensional/schema/formula error-explanation subsystem (optionally LLM-assisted). Notable groupings: parsing/caching (`class _TTLCache`, `_parse_returns()`, `_parse_instances()`); dimensional errors (`parse_dimensional_html_errors`, `explain_dimensional_errors`); backtrack/schema errors (`parse_backtrack_html_errors`, `_group_schema_errors_by_root_cause`, `explain_validation_errors`); sum/ratio discrepancy rendering (`_render_sum_check_explanation_detailed`, `_render_ratio_check_explanation_detailed`, `_explain_verified_context_via_llm` — an LLM-assisted rendering path); formula errors (`parse_formula_errors`, `enrich_formula_errors`, `explain_formula_errors`); error categorization (`_classify_error_category`, `count_errors_by_category()`, `explain_errors_by_category_for_form()` — the function called by `agent/error_explanation.py`); report matching (`find_matching_reports_tiered()`, `find_matching_reports()`, `fuzzy_report_suggestions(user_input, n=5, cutoff=0.75)`); file-path builders (`build_render_file_path()`, `build_error_file_path()`, `build_instance_doc_path()`, `resolve_instance_doc_path()`, `file_exists()`); status assembly (`_build_status_result_fast`, `get_report_status_by_id_fast()` — GUID-based lookup, `get_report_status_fast()`, `get_report_status()` — full non-fast lookup with error enrichment, `get_form_id_by_name()`). Data flow: `router.py`/`guided.py` call `find_matching_reports`/`get_available_instances` for name resolution and date-selection prompts; `agent/error_explanation.py` calls `build_error_file_path` + `explain_errors_by_category_for_form`/`count_errors_by_category`; `main.py`'s `/download-file` calls `build_render_file_path`/`build_error_file_path` directly.

### 15.11 Frontend — `MessageBubble.jsx` and `api.js`

**`MessageBubble.jsx`** (~2,756 lines) is the universal message renderer, dispatching first on `role` then on `resultType`:
- Special roles: `welcome` → `WelcomeCard` (guided-action suggestion buttons); `action_menu` → `ActionMenu`; `sql_welcome` → `SqlWelcomeCard`; `feedback_prompt` → `FeedbackPrompt` (thumbs up/down, 6.5s auto-hide timer); `feedback_positive`/`feedback_negative` → thank-you / `SupportContact` cards.
- `resultType` dispatch: `guided_menu` → `GuidedMenuCard`; `guided_input` → prompt bubble with option chips; `db_result` (+`sqlData`) → `SqlResultBlock` (the SQL Agent's results table); `db_qa_result` (+`dbQaData`) → `DbQaResultBlock`; `date_selection` → `InstanceDropdown` (color-coded status dots via `getStatusMeta`/`STATUS_LEGEND`); `instance_selection` → `InstanceSelectionBlock` (compare picker); `variance_table` → `VarianceTableBlock` (chart/table + AI summary, triggers `fetchCompareSummary`); `ask_previous`/`sched_confirm` → yes/no confirmation cards.
- Error rendering pipeline: `ErrorDetailsPanel` routes to `ErrorDetailsTablePanel` (4000-series schema table), `DimensionalErrorPanel`, or `PlainTextErrorPanel` based on `detectErrorCategory(details)`; `FormulaErrorSections`/`ErrorCardMatrix` render structured formula-error cards (headline/locator/matrix/fix/details, handling both v1 and v2 backend schema shapes); `ErrorSummaryPanel` shows category counts with "Explain … Errors" buttons wired to `onExplainCategory` → `explainErrorCategory` in `api.js`; `ExplainNextErrorsButton` continues pagination via `data.has_more`/`next_offset`.
- No audio player in this file — voice-input transcripts (from `transcribeAudio`) just populate the chat input box elsewhere (e.g. `App.jsx`); re-entry into the chat pipeline is never automatic.
- `DownloadButton`/`triggerBlobDownload` fetches `/download-file` as a blob and force-downloads it.

**`api.js`** — all backend HTTP calls. `BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''` (empty in dev, relying on Vite's dev-server proxy to `localhost:8001`; set explicitly in production since the app may be served from a different path than the API, e.g. `/AiChatbot/` vs `/AIChatBot/api`). Functions: `getAllowedActions()` → `GET /allowed-actions`; `stopRequest(requestId)` → `POST /stop`; `sendFeedback()` → `POST /feedback`; `compareInstances()` → `POST /compare-execute`; `fetchCompareSummary()` → `POST /compare-summary`; `sendMessage()` → `POST /chat`; `sendGuidedMessage()` → `POST /guided`; `transcribeAudio(audioBlob, opts)` → `POST /speech-to-text` (multipart FormData, file extension inferred from the blob's MIME type); `explainErrorCategory()` → `POST /explain-category`; `fetchStatusErrors(jobId)` → `GET /status-errors/{jobId}`. All POST calls support `opts.signal` (AbortController) and `opts.requestId` (wired to `/stop`) and `opts.lang`/`tenantId`/`domain`/`jwt` where relevant (v6.0 tenant fields sent only if present).

---

*Compiled from a direct source trace of `Chat-SystemWorking` and `TrendAnalysis_JSON_Extractor` by six parallel code-reading passes. Items marked "needs verification" throughout are explicit gaps, not omissions — close them against current source before treating this as a final sign-off document.*
