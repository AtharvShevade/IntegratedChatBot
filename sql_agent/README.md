# NL-to-SQL Query Generator — CIMS Banking Regulatory Reporting

A natural-language-to-SQL system built for South Indian Bank's **CIMS** (Centralised Information Management System) regulatory reporting database. Type or speak a question in plain English and get live Oracle query results instantly.

---

## Features

- **Natural language queries** — ask questions in plain English, get SQL + results
- **Voice input** — speak your query via microphone (transcribed via Sarvam AI)
- **Semantic retrieval** — FAISS vector indexes find the right tables and columns from 1,900+ CIMS tables
- **Banking domain awareness** — understands NPA, SMA, GNPA, SEC1/SEC2/SEC8, domestic/overseas splits, vertical-format tables, and RBI reporting conventions
- **Relative time resolution** — "last quarter", "this financial year", "Q1 FY2024" are automatically resolved to exact date ranges before the LLM sees the query
- **SQL validation** — generated SQL is checked against the schema before execution; dangerous DML/DDL is blocked
- **Dark mode** UI

---

## Architecture

```
User query (text / voice)
        │
        ▼
  [FastAPI backend]
        │
        ├─ Sarvam AI (voice → text)
        │
        ├─ FAISS retriever
        │   ├─ table_index   (BAAI/bge-large-en embeddings)
        │   ├─ column_index
        │   └─ row_label_index
        │
        ├─ Ollama LLM  (SQL generation)
        │
        ├─ SQL validator
        │
        └─ Oracle DB  (oracledb thin mode)
                │
                ▼
        [React + Vite frontend]
```

---

## Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.11+ |
| Node.js | 18+ |
| Oracle Database | XE / any edition |
| [Ollama](https://ollama.ai) | latest |
| Ollama model | `gpt-oss:120b-cloud` (or any capable model) |

---

## Setup

### 1. Clone and create virtual environment

```bash
git clone <repo-url>
cd "sql query gen"
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure credentials

Edit `src/config.py`:

```python
DB_HOST     = "your-oracle-host"
DB_PORT     = 1521
DB_SERVICE  = "XE"
DB_USER     = "your_schema_user"
DB_PASSWORD = "your_password"

OLLAMA_MODEL   = "gpt-oss:120b-cloud"   # or any model you have pulled
SARVAM_API_KEY = "your_sarvam_key"       # only needed for voice input
```

### 4. Build the vector indexes

Run **once** before starting the API (and again whenever `data/schema.sql` changes):

```bash
python main.py
```

This parses `data/schema.sql`, generates descriptions, embeds all tables/columns, and writes the FAISS indexes to `output/`.

### 5. Start the API server

```bash
uvicorn api.main:app --reload --port 8000
```

### 6. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

---

## Project Structure

```
├── api/                    FastAPI application
│   ├── main.py             App setup, CORS, router registration
│   ├── schemas.py          Pydantic request/response models
│   ├── utils.py            Oracle row serialization helpers
│   └── routes/
│       ├── query.py        POST /api/query
│       ├── voice.py        POST /api/voice
│       └── health.py       GET  /api/health
├── src/                    Core pipeline
│   ├── config.py           All settings (DB, LLM, embedding)
│   ├── parser.py           Parses CREATE TABLE DDL from schema.sql
│   ├── generators.py       Token-expansion description generator
│   ├── formatter.py        Builds schema.json and vector records
│   ├── vectorizer.py       FAISS index builder (bge-large-en)
│   ├── retriever.py        RRF-fused semantic retrieval
│   ├── sql_generator.py    LLM prompt builder + SQL validator
│   ├── executor.py         Oracle query execution
│   ├── description_fetcher.py  Row-label value fetcher
│   └── speech.py           Microphone recording (CLI mode)
├── data/
│   ├── schema.sql          Oracle DDL for all CIMS tables
│   └── .json-formatted     Human-readable column label mappings
├── output/                 Generated artifacts (rebuilt by main.py)
│   ├── schema.json
│   ├── description_samples.json
│   ├── *.faiss             FAISS vector indexes (git-ignored)
│   └── *.pkl               Index metadata (git-ignored)
├── frontend/               React + Vite + Tailwind CSS UI
├── main.py                 Index builder entry point
└── requirements.txt
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/query` | Run a text query |
| `POST` | `/api/voice` | Run a voice query (multipart audio upload) |

### POST /api/query

```json
// Request
{ "query": "Show total NPA for all banks in Q1 FY2024" }

// Response
{
  "query": "...",
  "matched_tables": ["cims_raq_q_sec1_part_a_dom"],
  "matched_columns": ["cims_raq_q_sec1_part_a_dom.period_delinquency", ...],
  "sql": "SELECT ...",
  "is_valid": true,
  "validation_reason": null,
  "columns": ["PERIOD_DELINQUENCY", "TOTAL_LOAN_ASSETS"],
  "rows": [["C. Total ( A + B)", 123456.78]],
  "db_error": null,
  "needs_more_info": false,
  "more_info_hint": null,
  "accuracy_hint": null
}
```

---

## Rebuilding Indexes

Whenever you update `data/schema.sql` or `data/.json-formatted`, rebuild the indexes:

```bash
python main.py
```

---

## Notes

- Queries shorter than 20 characters are rejected with a prompt to add more detail.
- The system detects missing time context and shows a soft hint to include a date/quarter/year.
- Relative time phrases ("last quarter", "this financial year", "Q3") are resolved to exact date ranges using India's April–March financial year convention.
- Backup tables (`_bk`, `_bkup`, `_backup` suffixes) are excluded from the search index automatically.
