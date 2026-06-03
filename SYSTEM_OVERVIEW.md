# iDEAL Report Assistant — System Overview Document

**Document Type:** System Overview / Architecture Reference  
**Application Name:** iDEAL Report Assistant  
**Version:** 3.0.0  
**Backend Framework:** FastAPI (Python 3.11)  
**Date:** June 2026  
**Audience:** Senior Management · Technical Leads · Solution Architects  

---

## 1. Introduction

The **iDEAL Report Assistant** is an enterprise-grade, AI-powered conversational chatbot integrated into the iDEAL regulatory reporting platform. It enables users to interact with the system using natural language — checking submission status, generating reports, scheduling runs, performing XBRL variance analysis, querying Oracle database metrics, and retrieving application metadata — all through a unified chat interface.

The system is designed with a **local-first, privacy-preserving** AI architecture: all language models run on-premise via Ollama with no data leaving the organisation's infrastructure.

---

## 2. Objectives

| Objective | Description |
|---|---|
| **Self-Service Reporting** | Allow non-technical users to check, generate, and schedule XBRL reports without navigating complex UI screens |
| **Natural Language Queries** | Accept plain English (and voice) queries — no SQL or XML knowledge required |
| **Operational Intelligence** | Expose Oracle database analytics and application metadata through a conversational interface |
| **XBRL Compliance** | Support period-over-period XBRL variance analysis with AI-generated narrative summaries |
| **Data Governance** | Enforce role-based access control — users see only data they are authorised to view |
| **Zero Cloud Dependency** | All AI inferencing runs locally; no API keys, no external data exposure |

---

## 3. Features

### Core Capabilities

| Feature | Description |
|---|---|
| **Report Status** | Check submission status, download error/render files, view run history |
| **Report Generation** | Trigger new XBRL instance generation via the .NET API with date validation |
| **Report Scheduling** | Schedule report runs for a future date and time with confirmation flow |
| **XBRL Comparative Analysis** | Period-over-period variance analysis using Arelle; AI narrative summary |
| **Oracle Database Querying** | Semantic natural-language-to-SQL with FAISS-assisted schema retrieval |
| **Application DB Q&A** | Query user accounts, departments, roles, returns, submission logs via XML |
| **Guided Workflow** | Step-by-step button-driven interface for all five core actions |
| **Speech-to-Text** | Browser-native voice input via Web Speech API |
| **Variance Chart** | Interactive period-over-period comparison rendered with Recharts |
| **Multi-turn Conversations** | Stateful disambiguation, date selection, and confirmation stages |
| **Role-Aware Responses** | Admin users see system-wide data; regular users see personal data only |
| **LLM Beautification** | Optional Ollama-powered natural language formatting of structured results |

---

## 4. Architecture

### High-Level System Diagram

```
┌───────────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                                  │
│   React 18 + Vite  │  Recharts (variance)  │  Web Speech API (voice) │
└────────────────────────────────┬──────────────────────────────────────┘
                                 │  HTTPS  POST /chat
                                 ▼
┌───────────────────────────────────────────────────────────────────────┐
│                        API GATEWAY LAYER                              │
│   FastAPI 3.0  │  Uvicorn ASGI  │  CORS Middleware  │  Pydantic       │
│   /chat  │  /guided  │  /compare  │  /speech-to-text  │  /health       │
└────────────────────────────────┬──────────────────────────────────────┘
                                 │
                                 ▼
┌───────────────────────────────────────────────────────────────────────┐
│                       ORCHESTRATION LAYER                             │
│   backend/agent/__init__.py  (decide())                               │
│                                                                       │
│   ┌─────────────────────┐   ┌──────────────────────────────────────┐ │
│   │  Regex Fast-path    │   │  LLM Fallback (phi3:mini via Ollama) │ │
│   │  intent_classifier  │   │  extract_intent_and_entities()       │ │
│   └──────────┬──────────┘   └───────────────┬──────────────────────┘ │
│              └──────────────┬───────────────┘                        │
│                             ▼                                         │
│              ┌──────────────────────────┐                            │
│              │   Intent Router          │                            │
│              │  (8 routing paths)       │                            │
│              └──────────────────────────┘                            │
└──────┬──────────┬──────────┬──────────┬──────────┬───────────────────┘
       │          │          │          │          │
       ▼          ▼          ▼          ▼          ▼
  ┌─────────┐ ┌───────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐
  │ Report  │ │Generate│ │ Schedule │ │ Compare  │ │  DB Q&A      │
  │ Status  │ │Instance│ │  Report  │ │  XBRL    │ │  (XML / SQL) │
  │ Lookup  │ │  API   │ │  Engine  │ │Comparator│ │  Agents      │
  └────┬────┘ └───┬───┘ └────┬─────┘ └────┬─────┘ └──────┬───────┘
       │          │          │             │              │
       ▼          ▼          ▼             ▼              ▼
  Returns.xml  .NET API  period.xml   Arelle XBRL    XMLStore /
  InstanceLog  (httpx)   PeriodMaster  + mistral     Oracle DB
```

### Module Responsibility Map

| Module | Responsibility |
|---|---|
| `backend/main.py` | FastAPI entry point, ASGI lifespan, all endpoint definitions, startup warm-up |
| `backend/agent/__init__.py` | Main orchestrator — session state, intent routing, multi-turn state machine |
| `backend/guided.py` | Button-driven guided workflow state machine (5 actions, 6 stages) |
| `backend/llm_extractor.py` | Ollama phi3:mini — intent/entity JSON extraction, date parsing |
| `backend/services/llm_service.py` | Async httpx Ollama client, model config, keep-alive management |
| `backend/tools/report_lookup.py` | 11-stage fuzzy report-name matching, status resolution, download URL builder |
| `backend/tools/instance_generator.py` | Report generation: date validation → .NET API call via httpx |
| `backend/tools/xbrl_comparator.py` | Arelle XBRL parse → fact extraction → variance computation → mistral narrative |
| `backend/tools/xbrl_normalizer.py` | XBRL fact canonicalisation, anomaly detection |
| `backend/sql_agent/` | Schema parsing → FAISS indexing → semantic SQL generation → Oracle execution |
| `backend/db_qa/xml_store.py` | In-memory XML data layer with O(1) indexed lookups |
| `backend/db_qa/intent_classifier.py` | Regex-only intent classifier (300+ patterns, zero latency) |
| `backend/db_qa/router.py` | Modular DBQA router — normalize → match → extract → guard → invoke |
| `backend/db_qa/query_handlers.py` | One handler per intent (35+ handlers), access-control enforced |
| `backend/db_qa/beautifier.py` | LLM-powered structured-data → natural-language formatter |
| `backend/utils/logger.py` | Rotating file logger (app.log + error.log, 10 MB × 5 backups) |

---

## 5. API Endpoints

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `POST` | `/chat` | Main conversational endpoint — all intents routed here | Session cookie |
| `POST` | `/guided` | Guided workflow step handler | Session cookie |
| `POST` | `/compare` | Direct XBRL comparison execution (bypasses intent detection) | Session cookie |
| `POST` | `/speech-to-text` | Audio file upload → Ollama Whisper transcription | Session cookie |
| `GET` | `/health` | Liveness check — returns `{"status":"ok"}` | None |
| `GET` | `/download-file` | Serve rendered or error file for download | Session cookie |

### Request / Response Schema (`/chat`)

**Request (`ChatRequest`)**
```
message              string  (1–2000 chars)   — User's natural language query
session_id           string  (optional)        — Stateful session identifier
asp_session          string  (optional)        — .AspNetCore.Session cookie forwarded for .NET API calls
login_id             string  (optional)        — User's login ID for report authorisation
user_id              string  (optional)        — Numeric user ID for DB Q&A role check
role_id              string  (optional)        — Role ID for admin access control
conversation_history list                      — Last 6–7 turns for LLM context
beautify             bool    (default: true)   — Enable LLM response beautification
```

**Response (`ChatResponse`)**
```
intent               string   — Detected intent (get_status, generate_instance, db_list_users…)
response_text        string   — Primary human-readable response
result_type          string   — final | variance_table | disambiguation | date_selection | error
db_columns / db_rows list     — Oracle query results (tabular)
db_records           list     — XML Q&A structured records
db_beautified        string   — LLM-formatted DB Q&A response
variance_data        list     — XBRL comparison rows for chart rendering
download_url         string   — Relative URL for report file download
instances_data       list     — Rich metadata for instance selection UI
```

---

## 6. AI / ML Stack

```
┌──────────────────────────────────────────────────────────────┐
│                    AI / ML COMPONENTS                        │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  LAYER 1 — Regex Engine (< 1 ms, zero GPU)            │  │
│  │  intent_classifier.py — 300+ compiled patterns        │  │
│  │  normalizer.py — typo correction, synonym expansion   │  │
│  └────────────────────────────────────────────────────────┘  │
│                         │ MISS                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  LAYER 2 — Small LLM  (3–8 s, phi3:mini, 3.8B)        │  │
│  │  Intent + entity extraction → structured JSON          │  │
│  │  DBQA result beautification                            │  │
│  └────────────────────────────────────────────────────────┘  │
│                         │ query_database intent              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  LAYER 3 — Semantic Search + LLM Reasoning             │  │
│  │  FAISS (BAAI/bge-large-en embeddings, 335M params)     │  │
│  │  → Retrieve top-K tables & columns                     │  │
│  │  mistral:latest (7B) → Generate Oracle SQL             │  │
│  └────────────────────────────────────────────────────────┘  │
│                         │ compare_reports intent             │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  LAYER 4 — XBRL Processing + Narrative                 │  │
│  │  Arelle → Parse XBRL instance files                    │  │
│  │  mistral:latest → Generate variance narrative          │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

---

## 7. LLM Model Details

| Model | Role | Parameters | Size Class | Deployment | Latency |
|---|---|---|---|---|---|
| **Microsoft phi3:mini** | Intent/entity extraction, DB Q&A beautification, conversational fallback | 3.8B | Small | Local — Ollama | 3–8 s (CPU) / < 1 s (GPU) |
| **Mistral 7B** (`mistral:latest`) | Oracle SQL generation, XBRL comparative narrative, complex reasoning | 7B | Medium | Local — Ollama | 10–30 s (CPU) / 3–8 s (GPU) |
| **BAAI/bge-large-en** | Sentence embedding for FAISS semantic search | 335M | Medium | Local — SentenceTransformers | < 100 ms |

> **Key design principle:** phi3:mini is the **fast path** for intent detection (30 s timeout). Mistral is used only for the compute-heavy SQL and XBRL tasks (180 s timeout). Models are pre-warmed at startup with `keep_alive=30m` to eliminate cold-start latency between requests.

### Model Configuration (via `.env`)

```env
OLLAMA_EXTRACT_MODEL=phi3:mini        # Intent + entity extraction
OLLAMA_MODEL=phi3:mini                # Conversational fallback
SQL_OLLAMA_MODEL=mistral              # SQL generation
SQL_EMBED_MODEL=BAAI/bge-large-en     # FAISS embedding
OLLAMA_TIMEOUT=180                    # Max seconds for chat/SQL calls
OLLAMA_EXTRACT_TIMEOUT=30             # Max seconds for intent extraction
OLLAMA_KEEP_ALIVE=30m                 # Models stay loaded between requests
```

---

## 8. Intent Routing Architecture

### Detection Priority Chain

```
User Query
    │
    ├─ 1. Session State Check   ─── Has active stage? (date/disambiguation/confirm)
    │                               → Resume multi-turn flow directly (no LLM call)
    │
    ├─ 2. Guided Workflow        ─── /guided endpoint, button-selected action
    │                               → Skip intent detection entirely
    │
    ├─ 3. Regex Fast-path        ─── intent_classifier.py (300+ patterns, < 1 ms)
    │                               Matches: status keywords, generate, schedule,
    │                               compare, user/dept/role/log domain keywords
    │
    ├─ 4. LLM Extraction         ─── phi3:mini via Ollama (< 30 s)
    │       Returns JSON:  { "intent": "...", "report_name": "...", ... }
    │
    └─ 5. Unknown / Fallback     ─── phi3:mini conversational response
```

### Intent → Handler Mapping

| Intent Group | Intents | Handler Path |
|---|---|---|
| **Report Workflow** | `get_status`, `generate_instance`, `schedule_report`, `compare_reports` | `backend/agent/__init__.py` → `tools/` |
| **Oracle SQL** | `query_database` | `backend/sql_agent/` → Oracle DB |
| **App DB Q&A (XML)** | `db_my_profile`, `db_list_users`, `db_list_departments`, `db_list_roles`, `db_user_info`, `db_department_info`, `db_my_role`, `db_my_permissions` + 30 more | `backend/db_qa/router.py` → `query_handlers.py` |
| **Unknown / Chat** | `unknown` | `llm_service.chat_response()` → phi3:mini |

### Multi-turn State Machine Stages

| Stage Constant | Description |
|---|---|
| `AWAITING_DATE_SELECTION` | User chose a report — now selecting a reporting date |
| `AWAITING_REPORT_SELECTION` | Disambiguating between multiple report name matches |
| `AWAITING_RUN_SELECTION` | Multiple runs found for a date — user selects one |
| `AWAITING_GEN_REPORT` | Generate flow — picking report from disambiguation |
| `AWAITING_GEN_DATE` | Generate flow — user enters reporting date |
| `AWAITING_SCHED_REPORT` | Schedule flow — disambiguating report name |
| `AWAITING_SCHED_DATETIME` | Schedule flow — user enters target date and time |
| `AWAITING_SCHED_CONFIRM` | Schedule flow — awaiting final yes/no confirmation |

---

## 9. XML / XBRL Processing

### Application XML Data Layer (`db_qa/xml_store.py`)

The `XMLStore` class loads all iDEAL application XML files once at startup and caches them as Python dicts in memory. Indexed lookups are built once per `XMLStore` lifetime.

| XML File | Data Stored | Index Type |
|---|---|---|
| `XML_User.xml` | User accounts, login history, status, email | `by_UserId` + `by_LoginId` (O(1)) |
| `XML_Dept.xml` | Departments, assigned return IDs, level emails | `by_DeptId` + `by_Name` (O(1)) |
| `XML_Role.xml` + `XML_RoleAccess.xml` | Roles and module-level permissions | `by_RoleId` + `by_Name` (O(1)) |
| `Returns.xml` + `NonXBRLReturns.xml` | XBRL and non-XBRL return definitions | `by_ReturnId` + `by_Name` (O(1)) |
| `XML_InstanceLog.xml` | Submission history, status codes, run timestamps | Linear scan (enriched per record) |
| `XML_Audit.xml` | Admin audit trail | Filtered by LoginId |
| `XML_UploadedFileLog.xml` | File upload records | Filtered by LoginId |
| `XML_CrossValidationLog.xml` | Cross-validation run results | Filtered by GeneratedBy |

**Security:** `_SENSITIVE_FIELDS = {Password, SecondPassword, …, Answer}` are stripped via `_safe()` before any data is returned to callers.

### Report Status XML Layer (`tools/report_lookup.py`)

| XML File | Usage |
|---|---|
| `Returns.xml` | Maps report names to ReturnId, AltName, period frequency |
| `XML_InstanceLog.xml` | Maps FormId → submission runs with status codes and file paths |

**Report Name Matching Pipeline (11 stages):**
1. Exact ReturnId / ReturnName / AltName match
2. Bidirectional partial contains
3. All-token substring match
4. Scored whole-word token loop (score ≥ 40 threshold)
5. Fuzzy fallback (`rapidfuzz partial_ratio ≥ 72`) for typos with no substring overlap

**Status Code → Label Mapping:**

| Code | Label |
|---|---|
| 11 | Success |
| 9 | Approved |
| 4, 6 | In Progress |
| 3, 5, 8, 10, 13 | Failed |
| 12 | Rejected |
| 0 | Not Started |

### XBRL Comparative Analysis (`tools/xbrl_comparator.py`)

1. **Instance resolution** — finds XBRL `.xml` files in `logs/` directory, cross-references with `XML_InstanceLog.xml`
2. **Arelle parsing** — parses XBRL instance files to extract typed/explicit dimensional fact values
3. **Canonicalisation** — `xbrl_normalizer.py` standardises fact labels; structural/text concepts excluded from comparison
4. **Variance computation** — period-over-period delta calculated per XBRL concept; tiered significance thresholds applied
5. **LLM narrative** — scale-aware prompt sent to `mistral:latest`; returns plain-English variance summary
6. **Frontend delivery** — `variance_data` array + `llm_summary` string returned to React for chart rendering

---

## 10. Vector Search Architecture (SQL Agent)

The SQL Agent enables natural-language Oracle database queries with no pre-defined query templates.

### Index Build Pipeline (one-time setup: `sql_agent/main.py`)

```
schema.sql  ──▶  [1] DDL Parse       ──▶  table/column structure
                 [2] Oracle verify   ──▶  remove ghost tables
mapping.json ──▶ [3] Load descriptions ──▶ excel_name / return_name per column
                 [4] Build schema.json (enriched)
                 [5] Embed with BAAI/bge-large-en ──▶ FAISS L1: table + column indexes
                 [6] Fetch distinct row labels from Oracle ──▶ FAISS L2/L3: row-label index
```

### Runtime Query Pipeline

```
User: "What is total NPA for Q3?"
         │
         ▼
[1] Extract search terms   (phi3:mini removes stop words, extracts key concepts)
         │
         ▼
[2] FAISS retrieval        (bge-large-en → semantic search)
    ├── TOP_K_TABLES = 5   (most relevant Oracle tables)
    └── TOP_K_COLUMNS = 5  (most relevant columns per table)
         │
         ▼
[3] Schema context built   (enriched with column descriptions + sample values)
         │
         ▼
[4] SQL generation         (mistral:latest → Oracle-compliant SELECT statement)
    ├── BANNED_KEYWORDS: DELETE, UPDATE, DROP, INSERT, TRUNCATE, ALTER, CREATE, EXEC
    ├── Unbalanced parenthesis auto-repair
    └── Column/table name validation against schema
         │
         ▼
[5] Oracle execution       (oracledb / cx_Oracle connection pool)
         │
         ▼
[6] Result formatting      (db_columns + db_rows → frontend table)
```

**FAISS Index Files:**

| File | Content |
|---|---|
| `table_index.faiss` | Table-level semantic embeddings |
| `column_index.faiss` | Column-level semantic embeddings |
| `row_label_index.faiss` | Distinct row values (for filter/groupby suggestions) |
| `schema.json` | Enriched DDL with descriptions and sample values |

---

## 11. Security

| Control | Implementation |
|---|---|
| **Sensitive field stripping** | `_SENSITIVE_FIELDS` set in `xml_store.py` — passwords and security answers are removed from all API responses at the data layer |
| **Role-based access control** | Every admin handler checks `is_admin` flag before returning data; non-admin requests receive a structured "Access Denied" response — never a stack trace |
| **SQL injection prevention** | `BANNED_KEYWORDS` list blocks all mutating SQL keywords; generated SQL is validated against the known schema before execution |
| **Read-only Oracle access** | Service account is granted SELECT privileges only — DML/DDL operations are structurally impossible |
| **No secrets in logs** | Logger sanitises output; sensitive fields never reach log files; LLM prompts are constructed from pre-filtered records |
| **LLM prompt isolation** | User input is never interpolated directly into system prompts; structured data is serialised to JSON first, then injected |
| **CORS policy** | Configured via `CORS_ORIGINS` env var; restricted to known frontend origins |
| **Error handling** | Global exception handler in `main.py` returns safe `500` responses; exception details are logged server-side only, never exposed to the client |
| **Session cookie forwarding** | `.AspNetCore.Session` cookie forwarded opaquely to .NET API — the Python backend never reads or stores its contents |
| **No cloud calls** | All LLM inferencing runs on-premise via Ollama; no query data or results leave the organisation's network |

---

## 12. Logging & Monitoring

### Log Configuration (`backend/utils/logger.py`)

| Output | Level | Path | Rotation |
|---|---|---|---|
| `app.log` | INFO and above | `logs/app.log` | 10 MB × 5 backups |
| `error.log` | ERROR and above | `logs/error.log` | 10 MB × 5 backups |
| Console (stdout) | DEBUG (dev) / INFO (prod) | — | — |

**Log format:**
```
2026-06-03 10:30:11 | INFO     | backend.agent | [INTENT] intent=get_status report_name=CIMS_LR
```

### Key Structured Log Events

| Tag | Module | Description |
|---|---|---|
| `[INTENT]` | `agent` | Detected intent and extracted entities |
| `[WARMUP]` | `main` | Startup model and index loading status |
| `[UNHANDLED_ERROR]` | `main` | Uncaught exceptions with method and path |
| `[ROUTER]` | `db_qa.router` | Normalised query, matched intent, extracted params |
| `[REGISTRY]` | `db_qa.intents.registry` | Per-pattern match debug output |
| `[DBQA]` | `db_qa_router` | DB Q&A routing decisions and handler dispatch |

### Health Check
`GET /health` returns `{"status": "ok", "version": "3.0.0"}` — suitable for load balancer liveness probes and uptime monitoring.

---

## 13. Deployment Architecture

### Runtime Environment

```
┌────────────────────────────────────────────────────────────────────────┐
│                          SERVER                                        │
│                                                                        │
│  ┌─────────────────────────────────────────────────┐                  │
│  │  Process 1: Uvicorn (ASGI)                      │                  │
│  │  uvicorn backend.main:app --host 0.0.0.0 --port 8001 --reload      │
│  │  Python 3.11 · FastAPI 3.0.0 · Virtual environment (.venv)         │
│  └─────────────────────────────────────────────────┘                  │
│                                                                        │
│  ┌─────────────────────────────────────────────────┐                  │
│  │  Process 2: Ollama                              │                  │
│  │  ollama serve  (port 11434)                     │                  │
│  │  Models: phi3:mini (3.8B), mistral:latest (7B)  │                  │
│  └─────────────────────────────────────────────────┘                  │
│                                                                        │
│  ┌─────────────────────────────────────────────────┐                  │
│  │  Process 3: Frontend Dev Server (development)   │                  │
│  │  Vite 5 (esbuild)  · port 3000                  │                  │
│  └─────────────────────────────────────────────────┘                  │
│                                                                        │
│  External connections:                                                 │
│    Oracle DB  ─────── oracledb / cx_Oracle  (port 1521)               │
│    iDEAL .NET API ─── httpx async (HTTPS, configurable port)          │
│    XML files ─────── Local filesystem (DB path via APP_DB_BASE_PATH)  │
└────────────────────────────────────────────────────────────────────────┘
```

### Key Environment Variables

| Variable | Purpose | Default |
|---|---|---|
| `APP_DB_BASE_PATH` | Path to iDEAL XML files directory | None (feature disabled if unset) |
| `OLLAMA_BASE_URL` | Ollama server endpoint | `http://127.0.0.1:11434` |
| `OLLAMA_EXTRACT_MODEL` | Intent extraction model | `phi3:mini` |
| `OLLAMA_MODEL` | Conversational fallback model | `phi3:mini` |
| `SQL_OLLAMA_MODEL` | SQL generation model | `mistral` |
| `SQL_EMBED_MODEL` | FAISS embedding model | `BAAI/bge-large-en` |
| `ORACLE_HOST / ORACLE_PORT / ORACLE_SERVICE` | Oracle connection | — |
| `DOTNET_API_URL` | iDEAL .NET API base URL | `https://localhost:5000` |
| `CORS_ORIGINS` | Allowed frontend origins (comma-separated) | `http://localhost:3000` |
| `APP_DB_ADMIN_ROLE_ID` | Admin role ID for access control | `101` |
| `APP_DB_ENABLE_BEAUTIFY` | Enable LLM beautification for DB Q&A | `true` |

### Startup Warm-up Sequence

On server start, the lifespan handler pre-loads all expensive resources before the first user request:

1. SentenceTransformer (`BAAI/bge-large-en`) loaded into memory
2. FAISS table + column indexes loaded and test-queried
3. Application XML store parsed and cached (`XML_User`, `XML_Dept`, etc.)
4. Ollama models pre-loaded with `keep_alive=30m`

---

## 14. Future Enhancements

| Priority | Enhancement | Benefit |
|---|---|---|
| **High** | **Hybrid NLP** — combine regex fast-path with a lightweight sentence-embedding classifier (e.g. `all-MiniLM-L6-v2`, 22M params) for intent confidence scoring on ambiguous queries | Reduce LLM calls by 40–60%, improve accuracy on edge-case queries |
| **High** | **Streaming responses** — implement SSE (Server-Sent Events) on `/chat` for progressive LLM output delivery | Eliminates perceived latency; users see partial answers immediately |
| **Medium** | **RAG (Retrieval-Augmented Generation)** — index XML application data into a vector store (ChromaDB / FAISS) so the LLM can answer open-ended questions directly against live data | Replace hard-coded handlers with dynamic document retrieval |
| **Medium** | **Fine-tuned NER** — replace regex anchor extraction with a domain-specific Named Entity Recogniser for report names, user names, and department names | Improved accuracy for partial names, multi-word entities, and mixed-script input |
| **Medium** | **Persistent session store** — move in-memory `_sessions` dict to Redis or a lightweight DB | Enables multi-instance horizontal scaling and session recovery after restart |
| **Medium** | **Audit trail for chatbot queries** — persist all query → intent → result tuples to SQLite | Enables usage analytics, intent distribution reporting, and model improvement feedback loop |
| **Low** | **Multi-language support** — add a translation pre-processing step (local NLLB model) | Support Hindi and regional languages common in regulatory environments |
| **Low** | **Semantic search over submission history** — embed XBRL fact labels and reporting notes into a vector index | Enable queries like "find all reports where NPA exceeded threshold in Q3" |

---

*Document generated from live codebase analysis — June 2026*  
*System: iDEAL Report Assistant v3.0.0 · FastAPI · Ollama · Oracle · React*
