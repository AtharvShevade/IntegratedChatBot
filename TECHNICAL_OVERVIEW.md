# iDEAL DBQA Chatbot — Technical Overview
**Document Type:** Internal Technical Summary  
**Audience:** Senior Management, Technical Leads, Reviewers  
**Date:** June 2026  

---

## 1. Project Overview

### Purpose
The **iDEAL DBQA Chatbot** is an enterprise AI assistant embedded in the iDEAL regulatory reporting platform. It allows both admin users and regular employees to query live application data — users, departments, roles, reports, and submission logs — using natural language, without accessing the database directly or raising IT support tickets.

### Business Problem Solved
| Before | After |
|---|---|
| Users emailed IT/Admin for basic info ("how many active users?") | Instant self-service via chat |
| No visibility into submission status without navigating multiple screens | Ask in plain English: "status of RAQ" |
| Finding who uploaded a file required manual log inspection | Answered in seconds |
| Admin queries required SQL/XML knowledge | Available to non-technical staff |

### Main Features
- **Role-aware responses** — regular users see only their own data; admins see everything
- **Report status queries** — check XBRL report submission status, download links, and run history
- **User & department management Q&A** — profile lookup, department info, login history
- **Multi-turn conversations** — handles disambiguation ("which CIMS report?") and date selection
- **Voice input** — browser microphone via Web Speech API
- **Variance chart visualisation** — renders period-over-period comparison charts
- **LLM-enhanced formatting** — optional Ollama-powered response beautification

---

## 2. System Workflow

```
User types / speaks query
        │
        ▼
 ┌──────────────────────┐
 │  Frontend (React)    │  — Voice → text, chat UI, Recharts charts
 └────────┬─────────────┘
          │  POST /chat
          ▼
 ┌──────────────────────────────────────────────────┐
 │  FastAPI Backend  (backend/main.py, port 8001)   │
 │                                                  │
 │  1. Intent Detection                             │
 │     ├─ Fast-path regex classifier                │
 │     │   (intent_classifier.py — 300+ patterns)  │
 │     └─ LLM fallback: Ollama phi3:mini            │
 │         (extract_intent_and_entities)            │
 │                                                  │
 │  2. Entity Extraction                            │
 │     ├─ Regex anchors (after/of/for keywords)     │
 │     ├─ Quoted/bracketed terms                    │
 │     └─ Fuzzy matching (rapidfuzz / difflib)      │
 │                                                  │
 │  3. Data Lookup                                  │
 │     ├─ DBQA path: XMLStore (in-memory XML cache) │
 │     └─ Report path: Returns.xml + InstanceLog    │
 │                                                  │
 │  4. Response Generation                          │
 │     ├─ Structured QueryResult dict               │
 │     └─ Optional LLM beautifier (phi3:mini)       │
 └──────────────────────────────────────────────────┘
          │
          ▼
 ┌──────────────────────┐
 │  Frontend renders    │  — Markdown tables, charts, download links
 └──────────────────────┘
```

**Two distinct query paths run in parallel:**

| Path | Trigger | Data Source |
|---|---|---|
| **DBQA** (app database Q&A) | `db_*` intents — users, roles, departments, logs | XML flat files (XML_User, XML_Dept, Returns, etc.) |
| **Report Status** | Report name detected in query | Returns.xml + XML_InstanceLog.xml |

---

## 3. Tech Stack

| Layer | Technology |
|---|---|
| **Backend Language** | Python 3.11 |
| **API Framework** | FastAPI + Uvicorn (ASGI) |
| **Frontend** | React 18 + Vite 5 |
| **Chart Library** | Recharts 3 |
| **Markdown Rendering** | react-markdown 10 |
| **LLM Runtime** | Ollama (local, self-hosted) |
| **LLM Model** | phi3:mini (3.8B parameters — Microsoft Phi-3) |
| **Fuzzy Matching** | rapidfuzz 3 (report lookup) + difflib stdlib (DBQA) |
| **XML Parsing** | Python stdlib `xml.etree.ElementTree` |
| **Logging** | Python `logging` + custom structured logger (`utils/logger.py`) |
| **Env Config** | python-dotenv |
| **HTTP Client** | httpx (async, for Ollama API calls) |
| **Speech Input** | Browser Web Speech API |
| **Data Storage** | XML flat files (no SQL database) |

---

## 4. Models & NLP

### Language Model
| Property | Value |
|---|---|
| Model | **Microsoft Phi-3 Mini** (`phi3:mini`) |
| Parameter Count | **3.8 billion** |
| Size Classification | Small |
| Deployment | Local via Ollama (no internet, no API costs) |
| Role | Intent extraction fallback + response beautification |
| Latency | ~3–8 seconds on CPU, < 1 second on GPU |

> The LLM is the **last resort**, not the primary path. Regex handles the vast majority of queries instantly.

### NLP Pipeline (No Cloud, No Embeddings)

```
Raw Query
   │
   ▼
Normalisation       lowercase → punctuation stripping → typo correction → synonym expansion
   │                ("dept" → "department", "actv" → "active", "loging" → "login")
   ▼
Regex Classifier    300+ compiled patterns in intent_classifier.py
   │                Matches in < 1 ms. Returns (intent_name, params).
   ▼
Entity Extraction   Anchored regex ("users in [X]", "status of [X]")
   │                + fuzzy fallback (rapidfuzz partial_ratio / difflib get_close_matches)
   ▼
[LLM fallback]      Only if regex produces UNKNOWN. phi3:mini via Ollama.
```

### Fuzzy Matching (Report Lookup)
The report lookup pipeline uses an 11-stage cascade:

1. Exact ReturnId / Name / AltName match
2. Bidirectional partial contains match
3. All-token substring match
4. **Scored any-token loop** — whole-word hits score ≥ 40 (suppress pure-substring noise)
5. **Final fuzzy fallback** — `partial_ratio ≥ 72` catches typos with no substring overlap  
   _Example: "phisin" → "Phising", "quaaterly" → "quarterly"_

---

## 5. Important Files

| File | Role |
|---|---|
| `backend/db_qa/xml_store.py` | **Central data layer.** Parses all iDEAL XML files once on startup and caches them in-memory. Provides indexed O(1) lookups for users, departments, roles, and returns. Filters sensitive fields (passwords) from all output. |
| `backend/db_qa/intent_classifier.py` | **Regex intent detector.** 300+ compiled patterns, zero latency, pure Python. Returns `(intent_name, params)` for ~40 intent categories. |
| `backend/tools/report_lookup.py` | **Report matching engine.** Maps free-text report names to Returns.xml entries using an 11-stage pipeline (exact → partial → fuzzy). Resolves report status codes to human labels. |
| `backend/db_qa/query_handlers.py` | **Business logic layer.** One function per intent (35+ handlers). Queries XMLStore, applies access control, and returns a structured `QueryResult` dict. |
| `backend/db_qa/router.py` | **Modular DBQA router.** Normalize → match → extract entities → admin guard → invoke handler. Provides `debug_query()` for diagnostics. |
| `backend/db_qa/utils/normalizer.py` | **Query normaliser.** Typo correction, synonym expansion, stopword filtering — all compiled regex, no ML. |
| `backend/db_qa/formatters.py` | **Display layer.** Converts raw XML attribute dicts into clean display dicts. Strips sensitive fields. Translates boolean Status to "Active / Inactive". |
| `backend/db_qa/filters.py` | **Filter engine.** Composable filters: `StatusFilter`, `FieldFilter`, `ContainsFilter`, `RegexFilter`, `CompositeAndFilter`. Chainable API. |
| `backend/db_qa/intents/registry.py` | **Intent registry.** `IntentPattern` dataclass + priority-ordered registry with auto `/help` generation. |
| `backend/llm_extractor.py` | **LLM bridge.** Calls Ollama phi3:mini for intent extraction when regex has no match. Also handles date parsing. |
| `backend/agent/__init__.py` | **Main orchestrator.** Session management, multi-turn state machine, routing between DBQA and report-status paths. |
| `backend/db_qa/beautifier.py` | **LLM formatter.** Takes structured data + user question → asks phi3:mini to produce a friendly natural language response. |

---

## 6. Performance Optimisations

| Optimisation | Detail |
|---|---|
| **XML file caching (TTL)** | Returns.xml cached for 1 hour; InstanceLog.xml for 2 minutes. Files are parsed once — not on every request. |
| **In-memory storage** | `XMLStore._cache` holds all parsed XML as Python dicts. Zero disk I/O after cold start. |
| **Indexed O(1) lookups** | `_user_index`, `_dept_index`, `_role_index`, `_return_index` — built once per `XMLStore` lifetime. Eliminates repeated O(n) linear scans. |
| **Compiled regex cache** | All intent patterns and normaliser rules are compiled to `re.Pattern` objects at module import time — not at query time. |
| **Regex-first, LLM-last** | The LLM is invoked only when regex cannot classify the query. Typical queries return in < 50 ms without Ollama. |
| **SentenceTransformer pre-warm** | SQL agent FAISS indexes and the embedding model are loaded during server startup, not on first request. |
| **rapidfuzz over difflib** | For report name fuzzy matching, `rapidfuzz` (C-extension, ~10× faster than difflib) is used for high-volume lookups. |

---

## 7. Security

| Control | Implementation |
|---|---|
| **Sensitive field filtering** | `_SENSITIVE_FIELDS = {Password, SecondPassword, …, Answer}` stripped in `XMLStore._safe()` before any data leaves the data layer. |
| **Role-based access control** | Every admin handler checks `is_admin` before returning data. Non-admin callers receive an "Access Denied" result — not an error, never leaking stack traces. |
| **No SQL injection surface** | No SQL database. All data comes from XML flat files parsed via stdlib ET. |
| **No secrets in logs** | Custom logger sanitises output. LLM prompts never include raw user records with sensitive fields. |
| **LLM prompt boundaries** | Beautifier prompt is constructed from pre-filtered records only. User input is never interpolated directly into the LLM system prompt. |
| **CORS policy** | Configured in `main.py` — origins restricted to known frontend hosts. |
| **Error handling** | All handler invocations are wrapped in try/except. Errors return a safe user-facing message; the exception detail is logged server-side only. |

---

## 8. Example Query Walkthroughs

### Query: `"status of RAQ"`

```
1. Normalisation   → "status of raq"
2. Intent detect   → regex: r"\bstatus\b" → REPORT_STATUS intent
3. Entity extract  → "raq" extracted as report name token
4. Report lookup   → _normalise("raq") = "raq"
                     Stage 8 (any-token): "raq" is substring of "CIMS_RAQ"
                     Whole-word score ≥ 40 → match = CIMS_RAQ (Quarterly)
5. Data fetch      → get_instances_by_form_id(form_id) → InstanceLog entries
6. Status map      → Status code 11 → "Success"
7. Response        → Table: ReportingDate | Run | Status | Download link
```

---

### Query: `"failed reports"`

```
1. Normalisation   → "failed reports"
2. Intent detect   → regex: r"\bfailed\b" + r"\breports?\b" → SUBMISSION_PENDING/STATUS
3. Entity extract  → status_filter = "failed" (Status codes 3,5,8,10,13)
4. Data fetch      → XMLStore.instance_log() → all entries
5. Filter          → StatusFilter("failed").apply(records)
6. Enrich          → enrich_instance_log_entry(): adds ReturnName, StatusLabel, UserName
7. Response        → Table of all failed submission records
```

---

### Query: `"who uploaded file"`

```
1. Normalisation   → "who uploaded file"
2. Intent detect   → regex: r"\bupload(ed)?\s+(file\s+)?log\b" → UPLOAD_LOG
3. Admin check     → requires_admin=True → verified
4. Data fetch      → XMLStore.upload_file_log() → XML_UploadedFileLog.xml
5. Enrich          → enrich_log_entry(): resolves LoginId → display Name
6. Response        → Table: FileName | Uploaded By | Date
```

---

## 9. Future Improvements

| Area | Recommendation |
|---|---|
| **Hybrid NLP** | Combine current regex fast-path with a lightweight embedding model (e.g. `all-MiniLM-L6-v2`, 22M params) for intent similarity scoring on ambiguous queries |
| **Named Entity Recognition** | Replace regex anchors with a fine-tuned NER model to improve entity extraction accuracy for partial names, typos, and multi-word department/return names |
| **Semantic search** | Add a FAISS vector index over return names and user display names for fuzzy recall beyond difflib/rapidfuzz |
| **RAG (Retrieval-Augmented Generation)** | Index XML data into a vector store (e.g. ChromaDB) so the LLM can answer open-ended questions against live data without hand-coded handlers |
| **Intent confidence scoring** | Expose a confidence score per intent match so the UI can show "Did you mean…?" proactively rather than only on UNKNOWN |
| **Structured audit trail** | Persist all chatbot queries + intents matched to a lightweight SQLite DB for usage analytics and model improvement |
| **Multi-language support** | Add a translation pre-processing step (e.g. via a local NLLB model) to support Hindi, regional languages common in regulatory environments |

---

*Document generated from live codebase analysis — June 2026*
