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

*Compiled from a direct source trace of `Chat-SystemWorking` and `TrendAnalysis_JSON_Extractor` by six parallel code-reading passes. Items marked "needs verification" throughout are explicit gaps, not omissions — close them against current source before treating this as a final sign-off document.*
