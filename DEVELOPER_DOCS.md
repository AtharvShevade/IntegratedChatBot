# AI Report Assistant — Developer Documentation

---

## 1. Project Overview

The AI Report Assistant is an enterprise-grade chatbot embedded inside a .NET web application via an `<iframe>`. It allows users to:

1. **Fetch report status** — query the processing state of any regulatory/financial report instance.
2. **Generate a report instance** — trigger creation of a new report instance via the .NET backend.

The system uses sentence embeddings (not a cloud LLM) for real-time intent classification, XML files as its data source, and Ollama (local LLaMA 3.1) only as a conversational fallback for unrecognised queries.

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Browser (.NET iframe)                        │
│                                                                     │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │                    React Frontend (Vite)                    │   │
│   │  App.jsx → ChatWindow → MessageBubble → VoiceInput          │   │
│   │  services/api.js  POST /chat | POST /speech-to-text         │   │
│   └────────────────────────┬────────────────────────────────────┘   │
└────────────────────────────│────────────────────────────────────────┘
                             │ HTTP (proxied by Vite in dev)
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend (Uvicorn)                        │
│                                                                     │
│  main.py                                                            │
│  ├── POST /chat           → agent/decide()                          │
│  ├── POST /speech-to-text → Sarvam AI proxy                        │
│  └── GET  /health         → {"status":"ok"}                        │
│                                                                     │
│  agent/__init__.py  (session state + routing)                       │
│  ├── llm_extractor.py     (embeddings intent + entity extraction)   │
│  ├── tools/report_lookup.py  (XML status lookup + TTL cache)        │
│  ├── tools/instance_generator.py  (date validation + .NET API call) │
│  └── services/llm_service.py  (Ollama fallback for unknown intent)  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          ▼                    ▼                     ▼
   logs/returns.xml   logs/XML_InstanceLog 2.xml  logs/period.xml
   (report master)    (instance run history)      (frequency rules)
```

### Request Lifecycle Summary

```
User message
    ↓
agent/decide()
    ├── [Stage check] — is there a pending multi-turn stage?
    │       STAGE_DATE       → user picking a reporting date
    │       STAGE_REPORT     → user picking from disambiguated reports (status)
    │       STAGE_GEN_REPORT → user picking from disambiguated reports (generate)
    │       STAGE_GEN_DATE   → user providing a date for generation
    │
    ├── [Escape guard] — does the user want to start a new query?
    │       _looks_like_new_query() using rapidfuzz + stem matching
    │
    └── [Fresh query]
            llm_extractor.extract_intent_and_entities()
            │   ├── embeddings  → intent
            │   ├── regex/dateutil → reporting_date
            │   └── token match → search_terms (report name)
            │
            intent == "get_status"       → report_lookup.get_report_status()
            intent == "generate_instance"→ instance_generator + .NET API
            intent == "unknown"          → llm_service.chat_response() (Ollama)
```

---

## 3. Tech Stack

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| Frontend | React | 18.3.x | Chat UI |
| Frontend build | Vite + `@vitejs/plugin-react` | 5.4.x | Dev server + production bundle |
| Backend framework | FastAPI | ≥0.111.0 | REST API |
| ASGI server | Uvicorn (standard) | ≥0.29.0 | Production/dev HTTP server |
| Intent classification | sentence-transformers | ≥3.0.0 | `all-MiniLM-L6-v2` embeddings |
| Numeric computation | NumPy | ≥1.20.0 | Cosine similarity via dot product |
| Date parsing | python-dateutil | ≥2.9.0 | Fuzzy natural-language date parsing |
| Fuzzy keyword matching | rapidfuzz | ≥3.0.0 | Typo-tolerant escape guard |
| LLM fallback | Ollama + LLaMA 3.1 | local | Conversational fallback only |
| Speech-to-text | Sarvam AI (saaras:v3) | cloud API | Voice input transcription |
| HTTP client | httpx | ≥0.27.0 | Async calls to Ollama + Sarvam AI + .NET |
| Data validation | Pydantic | ≥2.7.0 | Request/response schema |
| Env config | python-dotenv | ≥1.0.0 | `.env` loading |

---

## 4. Features and Capabilities

- **Natural-language report status queries** — "status of CIMS_RAQ", "staus of raq monthly" (typos tolerated)
- **Report instance generation** — multi-turn flow: report disambiguation → date prompt → frequency validation → .NET API call
- **Multi-turn conversation** — session state tracks where the user is in a flow across multiple messages
- **Report disambiguation** — when multiple reports match, presents a numbered list; user replies with number or partial name
- **Date disambiguation** — when a report has multiple run dates, presents a chronological list for selection
- **Flexible date input** — accepts `31-Mar-2024`, `31/03/2024`, `2024-03-31`, `31 March 2024`, `March 2024`, `2024`
- **Frequency-aware date validation** — validates against rules (Quarterly must be quarter-end, Monthly must be month-end, etc.)
- **Year sanity check** — rejects 3-digit years (e.g. `31/05/204`) before they silently pass `strptime`
- **Typo-tolerant keyword detection** — `"gnearte"`, `"staus"`, `"generating"`, `"triggered"` all resolved correctly
- **Voice input** — push-to-talk microphone, transcribed via Sarvam AI
- **Session escape** — user can start a new query mid-flow by typing a new intent ("status of X" abandons pending date selection)
- **TTL-based XML caching** — live data refreshes without server restart
- **CORS middleware** — configurable allowed origins for embedding in .NET iframe

---

## 5. Detailed System Flow

### 5.1 Status Query — Happy Path

```
1. User: "status of raq monthly"

2. agent/decide()
   → No active session stage
   → extract_intent_and_entities("status of raq monthly")
       → embeddings → intent = "get_status" (score 0.84)
       → _extract_search_terms → "raq monthly"
       → _extract_date_from_query → None

3. resolve_entities("status of raq monthly", "get_status", report_list)
   → _norm("raq monthly") = "raqmonthly"
   → substring match against pre-normalised report names
   → best_match = "CIMS_RAQ(Monthly)", confidence = 0.8

4. get_report_status("CIMS_RAQ(Monthly)")
   → find_matching_reports → matches [{"Id": "2041", "Name": "CIMS_RAQ(Monthly)", ...}]
   → get_instances_by_form_id("2041") → 3 instances found
   → len(instances) > 1 → return type="date_selection"

5. agent sets session: STAGE_DATE, pending_form_id="2041"

6. Response to user:
   result_type = "date_selection"
   options = ["31-Mar-2024", "30-Jun-2024", "30-Sep-2024"]

7. User: "30-Jun-2024"
   → STAGE_DATE handler
   → get_instance_by_date("2041", "30-Jun-2024", "CIMS_RAQ(Monthly)")
   → Returns: {report_name, reporting_date, status: "Success"}

8. Final response:
   "CIMS_RAQ(Monthly)
   Reporting Date : 30-Jun-2024
   Status         : Success"
```

### 5.2 Generation Flow — Happy Path

```
1. User: "generate CIMS_RAQ for 31-Mar-2024"

2. intent = "generate_instance"
   reporting_date = "31-Mar-2024"
   search_terms = "CIMS_RAQ"

3. resolve_return_exact("CIMS_RAQ")
   → returns.xml lookup → form_id, frequency="Q", period_name="Quarterly"

4. validate_reporting_date("31-Mar-2024", "Q")
   → year 2024: valid (1900–2099)
   → parsed: 31 March 2024
   → not future
   → Quarterly: (31, 3) ∈ _Q_ENDS → valid ✓

5. call_generate_api(form_id, "31-Mar-2024", asp_session)
   → POST https://localhost:5000/CreateInstance
   → body: {FormId: "2041", ReportingDate: "31-Mar-2024"}
   → cookie: .AspNetCore.Session=<value>

6. Response:
   "Instance generation triggered for 'CIMS_RAQ(Quarterly)'
   Reporting Date: 31-Mar-2024. The request has been submitted."
```

### 5.3 Disambiguation Flow

```
1. User: "status of cims"

2. find_matching_reports("cims") → 4 matches (cims raq monthly, quarterly, etc.)

3. Response: numbered list, result_type="disambiguation"
   Session stage: STAGE_REPORT

4. User: "2"
   → resolve pending_options[1]
   → get_report_status_exact(name)
```

---

## 6. API Documentation

### `POST /chat`

**Request:**
```json
{
  "message":     "status of CIMS_RAQ",
  "session_id":  "user-uid-123",
  "asp_session": "CfDJ8IB0NN1c..."
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `message` | string | Yes | User's natural-language query (1–2000 chars) |
| `session_id` | string | No | Identifies the conversation session (uses `.NET` UID if embedded) |
| `asp_session` | string | No | ASP.NET Core session cookie forwarded from the parent page |

**Response:**
```json
{
  "intent":             "get_status",
  "report_name":        "CIMS_RAQ(Monthly)",
  "response_text":      "CIMS_RAQ(Monthly)\nReporting Date : 30-Jun-2024\nStatus         : Success",
  "need_clarification": false,
  "result_type":        "final",
  "options":            []
}
```

| Field | Type | Description |
|---|---|---|
| `intent` | string | `get_status` \| `generate_instance` \| `unknown` |
| `report_name` | string\|null | Resolved report name if identified |
| `response_text` | string | Human-readable reply to display |
| `need_clarification` | bool | True when the report name was missing |
| `result_type` | string | `final` \| `disambiguation` \| `date_selection` \| `gen_awaiting_date` \| `error` \| `""` |
| `options` | string[] | List of choices when `result_type` is `disambiguation` or `date_selection` |

**Error responses:**

| Status | Condition |
|---|---|
| 422 | Request validation failed (message too short/long) |
| 503 | Ollama unavailable (only affects `unknown` intent fallback) |
| 500 | Unhandled server error |

---

### `POST /speech-to-text`

**Request:** `multipart/form-data` with field `file` (audio blob: webm, ogg, mp4).

**Response:**
```json
{ "transcript": "status of CIMS RAQ quarterly" }
```

**Error responses:**

| Status | Condition |
|---|---|
| 400 | Empty audio file |
| 503 | `SARVAM_API_KEY` not configured |
| 502 | Sarvam AI returned an error or is unreachable |

---

### `GET /health`

```json
{ "status": "ok" }
```

---

## 7. Intent Classification — Embedding Design

### How it works

The system uses **cosine similarity against pre-embedded prototype sentences** — no LLM call required for intent classification.

```python
# At startup: embed 44 example sentences once
_proto_embeddings = _embed_model.encode(
    _proto_sentences,              # 44 strings
    normalize_embeddings=True,     # unit vectors → dot product == cosine similarity
)  # shape: (44, 384)

# Per query (~50ms):
query_vec = _embed_model.encode([user_query], normalize_embeddings=True)  # (1, 384)
similarities = np.dot(_proto_embeddings, query_vec.T).flatten()           # (44,)
best_intent  = _proto_labels[np.argmax(similarities)]
```

### Intent prototypes

Three intents are defined with representative sentences in `_INTENT_PROTOTYPES`:

```python
"get_status":        27 sentences  # "status of raq", "staus of cims_raq", "is it done?", ...
"generate_instance": 14 sentences  # "generate CIMS_RAQ", "kick off RAQ", "create instance", ...
"unknown":            8 sentences  # "Hello", "What can you do?", "Tell me a joke", ...
```

Sentences include intentional typos (e.g. `"staus of cims_raq"`) to broaden semantic coverage.

### Keyword boost override

After embedding, unambiguous action words override the embedding result:

```python
_STATUS_BOOST_KWS = {"status", "state", "progress", "check", "details"}
_GEN_BOOST_KWS    = {"generate", "create", "trigger", "produce", ...}

# If "generate" is present and embedding said "get_status" → force "generate_instance"
```

### Threshold

Score below `0.40` → classified as `unknown`, routed to Ollama fallback.

### Entity extraction (report name + date)

Intent is the only thing embeddings handle. Report name and date use deterministic methods:

| Entity | Method |
|---|---|
| Report name | `resolve_entities()` — token overlap + bidirectional substring match against XML list |
| Reporting date | Regex (`DD-MMM-YYYY`) → python-dateutil fuzzy parsing → month-only → year-only |

---

## 8. Data Sources — XML-based Knowledge System

There is no vector database or semantic retrieval. The system reads three local XML files:

### `logs/returns.xml` — Report Master

Attributes used: `Id`, `Name`, `AltName`, `PeriodId`, `RepFreq`

```xml
<Return Id="2041" Name="CIMS_RAQ(Monthly)" PeriodId="5" RepFreq="M" />
```

- Cached for **1 hour** (`RETURNS_TTL_SEC`).
- Powers: report name matching, `form_id` resolution, frequency lookup.

### `logs/XML_InstanceLog 2.xml` — Instance Run History

Attributes used: `FormId`, `ReportingDate`, `Status`, `ReportName`

```xml
<Row FormId="2041" ReportingDate="30-Jun-2024" Status="11" ReportName="CIMS_RAQ(Monthly)" />
```

- Cached for **2 minutes** (`INSTANCES_TTL_SEC`).
- Powers: status display, available date list.

### `logs/period.xml` — Frequency Rules (PeriodMaster)

Attributes used: `Period_Id`, `Frequency`, `PeriodName`

```xml
<Row Period_Id="5" Frequency="M" PeriodName="Monthly" />
```

- Cached for **24 hours** (`PERIOD_TTL_SEC`).
- Powers: date validation logic in `validate_reporting_date()`.

### TTL Cache Implementation

```python
class _TTLCache:
    def get(self):
        if self._data is not None and (time.monotonic() - self._ts) < self._ttl:
            return self._data
        return None  # stale or empty → caller must re-parse

    def set(self, data):
        self._data = data
        self._ts   = time.monotonic()
        return data
```

TTL values are overridable via environment variables at runtime without code changes.

### Report name matching pipeline (`find_matching_reports`)

Three strategies applied in order, returning on first non-empty result:

1. **Bidirectional substring** — `"raqmonthly"` in `"cimsraqmonthly"` → match
2. **All-keyword token match** — every token from query must appear in report name
3. **Any-keyword token match** — at least one token from query appears in report name

Fallback: `difflib.get_close_matches` (similarity ≥ 0.35) for near-miss suggestions.

---

## 9. Error Handling Strategy

| Layer | Approach |
|---|---|
| FastAPI global | `@app.exception_handler(Exception)` catches all unhandled exceptions → 500 JSON |
| Ollama connection | `httpx.ConnectError` / `httpx.TimeoutException` → 503 with actionable message |
| Sarvam AI | `httpx.HTTPStatusError` → 502 with Sarvam's error text; `RequestError` → 502 |
| Intent extraction | `try/except` around `extract_intent_and_entities()` → falls back to `unknown` intent |
| Ollama fallback | `try/except` around `chat_response()` → hardcoded help message |
| XML parsing | `ET.ParseError` caught per-file, logged, returns empty tuple — system keeps running |
| Date validation | Multi-layer: raw year regex → strptime → calendar check → frequency rule — each with specific error + suggestions |
| Report not found | Returns `type="error"` dict → user-facing message without raising exception |
| Out-of-range option | Re-presents options list with boundary message |
| .NET API call | `httpx` errors caught in `call_generate_api()` → error response dict |

---

## 10. Setup & Installation

### Prerequisites

- Python 3.11+
- Node.js 18+
- Ollama installed and running with `llama3.1` pulled
- Internet access (first run only — to download `all-MiniLM-L6-v2`, ~80 MB)

### Backend

```powershell
# From project root
cd "Chat-System - Copy"

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows PowerShell
# source .venv/bin/activate        # Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
copy .env.example .env             # then edit with your values

# Start backend (development, with hot reload)
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```powershell
cd frontend
npm install
npm run dev        # development server on http://localhost:3000
npm run build      # production build → dist/
```

### Ollama (LLM fallback)

```bash
ollama pull llama3.1
ollama serve       # starts on http://127.0.0.1:11434
```

---

## 11. Environment Variables

All variables are loaded from `.env` in the project root via `python-dotenv`.

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.1` | Model name for conversational fallback |
| `OLLAMA_TIMEOUT` | `120` | Request timeout (seconds) for Ollama calls |
| `SARVAM_API_KEY` | _(required for voice)_ | API key for Sarvam AI speech-to-text |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed frontend origins |
| `DOTNET_API_URL` | `https://localhost:5000` | Base URL of the .NET report generation API |
| `DOTNET_CONTROLLER` | `CreateInstance` | Controller name for instance creation endpoint |
| `DOTNET_SESSION_COOKIE` | `""` | Fallback ASP.NET Core session cookie (per-user value preferred via `asp_session` param) |
| `EMBED_MODEL` | `all-MiniLM-L6-v2` | Sentence-transformers model for intent embeddings |
| `EMBED_THRESHOLD` | `0.40` | Minimum cosine similarity to classify a non-unknown intent |
| `RETURNS_TTL_SEC` | `3600` | Cache TTL for `returns.xml` (seconds) |
| `INSTANCES_TTL_SEC` | `120` | Cache TTL for instance log XML (seconds) |
| `PERIOD_TTL_SEC` | `86400` | Cache TTL for `period.xml` (seconds) |
| `MAX_ERROR_BLOCKS` | `10` | (tools `__init__.py`) Max log error blocks returned |
| `ORACLE_DSN` | _(unused in active flow)_ | Oracle DB DSN — present in `.env` for future use |
| `ORACLE_USER` | _(unused in active flow)_ | Oracle DB username |
| `ORACLE_PASSWORD` | _(unused in active flow)_ | Oracle DB password |

**Frontend only:**

| Variable | Default | Description |
|---|---|---|
| `VITE_API_BASE_URL` | `""` (relative) | Production backend origin — empty means use Vite proxy |

---

## 12. Folder Structure

```
Chat-System - Copy/
│
├── .env                          # Environment variables (never commit secrets)
├── requirements.txt              # Python dependencies
├── DEVELOPER_DOCS.md             # This file
│
├── backend/
│   ├── __init__.py
│   ├── main.py                   # FastAPI app, routes: /chat, /speech-to-text, /health
│   ├── models.py                 # Pydantic: ChatRequest, ChatResponse
│   ├── llm_extractor.py          # Embedding model, intent classification, date parsing, entity extraction
│   │
│   ├── agent/
│   │   └── __init__.py           # Session state machine, multi-turn routing, escape guards
│   │
│   ├── services/
│   │   └── llm_service.py        # Async Ollama client (chat_response fallback)
│   │
│   └── tools/
│       ├── __init__.py           # Legacy tool registry (get_error_logs — not in active API path)
│       ├── report_lookup.py      # XML parsers + TTL cache + report/instance lookup pipeline
│       └── instance_generator.py # Date validation, frequency rules, .NET API call
│
├── frontend/
│   ├── package.json
│   ├── vite.config.js            # Dev proxy: /chat, /speech-to-text → localhost:8000
│   └── src/
│       ├── main.jsx              # React entry point
│       ├── App.jsx               # Root component: session management, submit handler
│       ├── App.css               # Global styles
│       ├── components/
│       │   ├── ChatWindow.jsx    # Message list + auto-scroll + typing indicator
│       │   ├── MessageBubble.jsx # Individual message render (user/assistant/error/welcome)
│       │   └── VoiceInput.jsx    # Push-to-talk: MediaRecorder → Sarvam AI → transcript
│       └── services/
│           └── api.js            # sendMessage(), transcribeAudio() — all HTTP calls
│
└── logs/
    ├── returns.xml               # Report master: Id, Name, PeriodId, RepFreq
    ├── XML_InstanceLog 2.xml     # Instance run history: FormId, ReportingDate, Status
    └── period.xml                # Period/frequency master: Period_Id, Frequency, PeriodName
```

---

## 13. Design Decisions

### Why embeddings for intent, not regex?

Purely regex-based intent detection requires an exhaustive list of keywords and fails on any phrasing variation. The embedding approach handles:
- Paraphrasing: `"how far along is the report"` → `get_status`
- Implicit queries: `"is it done yet"` → `get_status`
- Novel phrasing not in the keyword list

A pure LLM (Ollama) call for every query would add 500ms–2s latency. Embeddings are ~50ms on CPU with a pre-computed prototype matrix.

### Why keyword boost on top of embeddings?

Embeddings can mis-classify when an action keyword is present but the query is short (e.g. `"generate"`). The keyword boost layer ensures that unambiguous action words (`generate`, `trigger`, `status`) always win over the embedding score. This gives determinism where determinism is cheap.

### Why rapidfuzz for escape guards instead of more embeddings?

The escape guard (`_looks_like_new_query`) runs inside the session stage handlers before intent extraction. It only needs to answer: "is this word a status/generate keyword?". Running a full embedding pass here would double latency. rapidfuzz edit-distance + 4-char stem prefix matching handles `"gnearte"`, `"generating"`, `"staus"` at near-zero cost.

### Why XML files instead of a database?

The report data originates from a .NET system that exports XML. Parsing XML locally avoids network round-trips to Oracle at query time. The TTL cache means the XML is only re-read when it may have changed (2 minutes for live instance status, 1 hour for the static report master).

### Why two-layer date handling (regex fast path + dateutil fuzzy)?

The fast path (`DD-MMM-YYYY` regex) validates and returns in microseconds for the common case. dateutil fuzzy parsing is only invoked when the format is not the canonical one. This avoids dateutil's false positives (it can extract dates from report names like `"CIMS_RAQ"` if given free rein) by gating it behind a date-signal presence check.

### Why session state in-process dict?

The system is single-instance. An in-process `dict[session_id, state]` is sufficient and has zero external dependencies. A Redis store would be needed only if the deployment moves to multiple worker processes.

---

## 14. Performance Considerations

| Concern | Current approach | Measurement |
|---|---|---|
| Intent classification | Pre-computed 44×384 embedding matrix; dot product per query | ~50ms on CPU |
| XML parsing | TTL cache per file; re-parsed only on expiry | ~5ms on cache hit |
| Report name matching | Pre-normalised name pairs; O(n) substring scan | <1ms for ~100 reports |
| Ollama LLM (fallback) | Only invoked for `unknown` intent | 500ms–2s (local, model-dependent) |
| Sarvam AI (voice) | External API, async | 300ms–1s (network-dependent) |
| .NET API call | Async httpx with TLS; per-generation only | 200ms–2s (server-dependent) |
| Session state | Python dict, in-process | Sub-millisecond |
| Startup time | Model download once; weights load ~500ms after first download | ~2–3s cold start |

**Key optimisations already in place:**

- `all-MiniLM-L6-v2` is loaded once at import time (`SentenceTransformer` init at module level).
- Prototype embeddings are computed once at startup — not per query.
- All XML parsers use TTL cache with `time.monotonic()` (not wall clock, no clock-skew issues).
- `normalize_embeddings=True` pre-normalises vectors so cosine similarity is just a dot product (faster than full cosine formula).
- `_normalised_returns()` rebuilds only when `_returns_cache` is newer than `_norm_cache`, avoiding redundant string normalisation.

---

## 15. Future Improvements

| Area | Suggestion | Benefit |
|---|---|---|
| Intent prototypes | Load from a YAML/JSON file instead of hardcoded Python dict | Allows non-developer updates without code changes |
| Fine-tuned model | Fine-tune `all-MiniLM-L6-v2` on domain queries | Higher accuracy on regulatory report terminology |
| Session storage | Move `_session_context` to Redis | Supports multi-worker deployments, survives restarts |
| Authentication | Add JWT/API-key auth on `/chat` endpoint | Prevents unauthorised external access |
| Report name embeddings | Embed all report names at startup; use vector similarity for matching | Better fuzzy match on names with unusual abbreviations |
| OpenAI / cloud LLM | Replace Ollama with OpenAI API for the `unknown` fallback | Removes local GPU/CPU requirement for conversational quality |
| Streaming responses | Use FastAPI `StreamingResponse` + Ollama streaming | Reduces perceived latency for long conversational replies |
| Database-backed instances | Query Oracle directly instead of XML | Real-time status without polling; eliminates TTL lag |
| Audit logging | Persist all `decide()` calls to a log table | Traceability for enterprise compliance |
| Frontend session persistence | Store `session_id` in `sessionStorage` | Survives page reload without losing conversation context |
| Unit test coverage | Pytest suite for `validate_reporting_date`, `find_matching_reports`, `_classify_intent` | Prevents regressions on edge cases already encountered |
