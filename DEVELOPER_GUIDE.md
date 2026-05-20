# AI Report Assistant — Developer Guide

---

## 1. Overview

An AI-powered chatbot embedded in an enterprise .NET application via `<iframe>`. It allows users to check the status of regulatory/financial reports and trigger new report instance generation using natural language. Intent is classified using sentence embeddings (no cloud LLM). Data is sourced from local XML files. Ollama (LLaMA 3.1) is used only as a fallback for unrecognised queries.

---

## 2. Architecture

```
Browser (.NET iframe)
└── React Frontend (Vite, port 3000)
    └── POST /chat
            │
            ▼
    FastAPI Backend (Uvicorn, port 8000)
    ├── agent/           ← session state + routing
    ├── llm_extractor.py ← embeddings intent + entity extraction
    ├── tools/
    │   ├── report_lookup.py      ← XML status lookup (TTL cached)
    │   └── instance_generator.py ← date validation + .NET API call
    └── services/llm_service.py   ← Ollama fallback (unknown intent only)
            │
            ├── logs/returns.xml           (report master)
            ├── logs/XML_InstanceLog 2.xml (instance run history)
            └── logs/period.xml            (frequency rules)
```

---

## 3. Key Flow

1. **User sends a message** → React calls `POST /chat` with `{message, session_id, asp_session}`.
2. **Session check** → If a multi-turn stage is active (e.g. awaiting date selection or report disambiguation), handle that first. If the user starts a new query mid-flow, the stage is reset.
3. **Intent classification** → `all-MiniLM-L6-v2` embeddings compare the query against 44 pre-embedded prototype sentences. Result: `get_status`, `generate_instance`, or `unknown`.
4. **Entity extraction** → Report name extracted via token matching against `returns.xml`. Date extracted via regex + python-dateutil.
5. **Action execution**
   - `get_status` → look up `XML_InstanceLog` by `FormId` → return status.
   - `generate_instance` → validate date against `period.xml` rules → call `.NET API`.
   - `unknown` → forward to Ollama for a conversational reply.
6. **Response** → structured JSON returned to frontend and rendered as a chat bubble.

---

## 4. API — `POST /chat`

**Request**
```json
{
  "message":     "status of CIMS_RAQ",
  "session_id":  "user-uid-123",
  "asp_session": "CfDJ8..."
}
```

| Field | Required | Description |
|---|---|---|
| `message` | Yes | User's natural-language query (1–2000 chars) |
| `session_id` | No | Identifies the conversation session |
| `asp_session` | No | ASP.NET Core session cookie forwarded from parent page |

**Response**
```json
{
  "intent":             "get_status",
  "report_name":        "CIMS_RAQ(Monthly)",
  "response_text":      "CIMS_RAQ(Monthly)\nReporting Date : 30-Jun-2024\nStatus : Success",
  "need_clarification": false,
  "result_type":        "final",
  "options":            []
}
```

| Field | Description |
|---|---|
| `intent` | `get_status` \| `generate_instance` \| `unknown` |
| `report_name` | Resolved report name if identified, otherwise `null` |
| `response_text` | Human-readable reply to display in the chat |
| `need_clarification` | `true` when the report name was missing from the query |
| `result_type` | `final` \| `disambiguation` \| `date_selection` \| `gen_awaiting_date` \| `error` |
| `options` | Numbered choices shown when disambiguation or date selection is needed |

---

## 5. Setup

### Backend
```bash
cd "Chat-System - Copy"
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows — use source .venv/bin/activate on Linux/macOS
pip install -r requirements.txt
# Edit .env with your values (OLLAMA_BASE_URL, SARVAM_API_KEY, DOTNET_API_URL, etc.)
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev       # http://localhost:3000
```

### Ollama (fallback LLM)
```bash
ollama pull llama3.1
ollama serve
```

---

## 6. Key Design Decisions

| Decision | Reason |
|---|---|
| **Embeddings for intent** | Handles paraphrasing and novel phrasing that regex keyword lists cannot cover |
| **Hybrid approach (not LLM-only)** | LLM adds 500ms–2s latency per call; embeddings classify intent in ~50ms with no network dependency |
| **XML + TTL cache** | Data originates from the .NET system as XML exports; caching avoids redundant file reads (2 min for live status, 1 hr for report master) |
| **Local session state** | Single-instance deployment; an in-process dict is sufficient with zero external dependencies |
