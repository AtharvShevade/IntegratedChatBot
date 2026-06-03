# Deployment Document
## AI-Powered SQL Agent Chatbot Application
### iDEAL Report Management & Database Intelligence Platform

---

| Field               | Details                                |
|---------------------|----------------------------------------|
| **Document Title**  | Deployment Document — SQL Agent Chatbot |
| **Version**         | 3.0.0                                  |
| **Prepared By**     | [Author Name]                          |
| **Reviewed By**     | [Reviewer Name]                        |
| **Approved By**     | [Approver Name]                        |
| **Date**            | June 3, 2026                           |
| **Classification**  | Confidential — Client Restricted       |
| **Status**          | Release Candidate                      |

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Technology Stack](#3-technology-stack)
4. [AI Model Details](#4-ai-model-details)
5. [SQL Agent Design](#5-sql-agent-design)
6. [Database Requirements](#6-database-requirements)
7. [Infrastructure Requirements](#7-infrastructure-requirements)
8. [Software Prerequisites](#8-software-prerequisites)
9. [Environment Variables](#9-environment-variables)
10. [Deployment Procedure](#10-deployment-procedure)
11. [API Documentation](#11-api-documentation)
12. [Security Configuration](#12-security-configuration)
13. [Logging and Monitoring](#13-logging-and-monitoring)
14. [Backup and Recovery](#14-backup-and-recovery)
15. [Testing and Validation](#15-testing-and-validation)
16. [Operational Support](#16-operational-support)
17. [Required Supporting Documents](#17-required-supporting-documents)
18. [Assumptions and Constraints](#18-assumptions-and-constraints)
19. [Deployment Checklist](#19-deployment-checklist)
20. [Production Readiness Checklist](#20-production-readiness-checklist)

---

## 1. Project Overview

### 1.1 Purpose

The AI-Powered SQL Agent Chatbot is an intelligent conversational interface deployed within the iDEAL Report Management System. It enables authorised banking institution users to query Oracle databases, manage regulatory report instances, and interrogate application metadata — all through a natural-language chat interface without requiring knowledge of SQL or database schema.

The system integrates a locally hosted Large Language Model (LLM) via the Ollama runtime to perform intent classification, entity extraction, dynamic SQL generation, and conversational response formatting. It functions as a supplementary intelligence layer on top of an existing .NET regulatory reporting platform.

### 1.2 Scope

This document covers the complete production deployment of the following components:

- **Chat-System Backend** — FastAPI (Python) REST API service
- **Chat-System Frontend** — React.js single-page application (SPA) served via Vite build
- **SQL Agent Engine** — FAISS vector search + Ollama LLM SQL generation pipeline
- **Application Database Q&A Module** — XML-backed user/role/department lookup service
- **XBRL Variance Analysis Module** — Arelle-powered comparative report analysis
- **Speech-to-Text Integration** — Sarvam AI voice query pipeline
- **Ollama LLM Runtime** — Local model inference server

**Out of Scope:**
- The parent .NET regulatory reporting platform (iDEAL application)
- Oracle Database installation and schema migration
- Corporate network firewall and proxy configuration
- SSL/TLS certificate procurement

### 1.3 Key Features

| Feature                          | Description                                                                                 |
|----------------------------------|---------------------------------------------------------------------------------------------|
| Natural Language SQL Query       | Converts plain English questions into validated Oracle SQL and returns structured results    |
| Multi-Intent Recognition         | Classifies user queries into 20+ intent categories (report workflows, DB queries, app Q&A)  |
| Report Instance Management       | Generate, schedule, and check status of XBRL regulatory report instances                    |
| XBRL Variance Analysis           | Side-by-side comparison of two report instances with variance highlighting                  |
| Application Database Q&A         | Query user profiles, department information, role permissions from XML configuration         |
| Speech-to-Text                   | Voice query support via Sarvam AI multilingual speech recognition                           |
| Session-Based Conversation       | Maintains multi-turn conversation context (last 7 messages) per user session                |
| Role-Based Access Control        | Enforces department and role permissions from XML authorization configuration                |
| Warm-Start Optimization          | Pre-loads LLM models and FAISS indexes at startup to eliminate cold-start latency            |

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Client Layer                                  │
│  ┌───────────────────────────────────────────────────────────────┐   │
│  │           React.js SPA (Vite Build — Port 3000)               │   │
│  │   ChatWindow │ MessageBubble │ VarianceChartModal │ VoiceInput │   │
│  └───────────────────────────┬───────────────────────────────────┘   │
└──────────────────────────────┼───────────────────────────────────────┘
                               │ HTTPS REST (JSON)
┌──────────────────────────────▼───────────────────────────────────────┐
│                      API Gateway / Reverse Proxy                     │
│                   (Nginx — Port 443 → Port 8001)                     │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────────────┐
│                     FastAPI Backend (Port 8001)                      │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐  ┌──────────┐  │
│  │ /chat       │  │ /compare-    │  │ /speech-    │  │ /health  │  │
│  │ endpoint    │  │ execute      │  │ to-text     │  │ /guided  │  │
│  └──────┬──────┘  └──────┬───────┘  └──────┬──────┘  └──────────┘  │
│         │                │                  │                        │
│  ┌──────▼──────────────────────────────────▼──────────────────────┐ │
│  │                    Agent Decision Layer                         │ │
│  │  ┌────────────────┐  ┌────────────────┐  ┌──────────────────┐  │ │
│  │  │ LLM Extractor  │  │ Intent Router  │  │  Auth Service    │  │ │
│  │  │ (phi3:mini)    │  │ (20+ intents)  │  │  (XML-based)     │  │ │
│  │  └────────────────┘  └────────────────┘  └──────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                               │                                      │
│  ┌────────────────────────────▼────────────────────────────────────┐ │
│  │                    Service Modules                               │ │
│  │  ┌───────────┐  ┌────────────┐  ┌──────────┐  ┌────────────┐  │ │
│  │  │ SQL Agent │  │ DB Q&A     │  │ XBRL     │  │ Instance   │  │ │
│  │  │ (FAISS +  │  │ (XML Store)│  │ Comparator│ │ Service    │  │ │
│  │  │  Ollama)  │  │            │  │ (Arelle) │  │            │  │ │
│  │  └─────┬─────┘  └─────┬──────┘  └────┬─────┘  └─────┬──────┘  │ │
│  └────────┼──────────────┼───────────────┼──────────────┼─────────┘ │
└───────────┼──────────────┼───────────────┼──────────────┼────────────┘
            │              │               │              │
┌───────────▼──────┐  ┌────▼──────┐  ┌────▼──────┐  ┌────▼──────────┐
│  Oracle DB       │  │ XML Config │  │ XBRL/XML  │  │ Ollama LLM   │
│  (Port 1521)     │  │ Files      │  │ Repo Files│  │ (Port 11434)  │
│  oracledb thin   │  │ (User/Dept)│  │           │  │ phi3:mini     │
│  Connection Pool │  │            │  │           │  │ mistral:7b    │
└──────────────────┘  └────────────┘  └───────────┘  └───────────────┘
```

### 2.2 Component Interaction Flow

**Standard SQL Query Flow:**

```
User Input (Natural Language)
        │
        ▼
[1] Frontend → POST /chat  (message, session_id, login_id, asp_session)
        │
        ▼
[2] FastAPI /chat endpoint receives ChatRequest
        │
        ▼
[3] LLM Extractor → Ollama phi3:mini (EXTRACT_MODEL)
    → Returns: { intent, report_name, entities... } as JSON
        │
        ▼
[4] Intent Router dispatches to:
    ├── "query_database"    → SQL Agent Pipeline (Sections 5.1–5.7)
    ├── "get_status"        → Instance Service
    ├── "generate_instance" → Instance Generator (auth-gated)
    ├── "compare_reports"   → XBRL Comparator (Arelle)
    ├── "db_*"              → DB Q&A Router → XML Store
    └── "unknown"           → Conversational LLM (OLLAMA_MODEL)
        │
        ▼
[5] Response assembled as ChatResponse (Pydantic)
        │
        ▼
[6] Frontend renders: text / table / variance chart / disambiguation UI
```

---

## 3. Technology Stack

### 3.1 Frontend

| Component       | Technology        | Version   | Notes                                      |
|-----------------|-------------------|-----------|--------------------------------------------|
| UI Framework    | React.js          | ^18.3.1   | Functional components with hooks           |
| Build Tool      | Vite              | ^5.4.0    | HMR dev server, optimised production build |
| Charting        | Recharts          | ^3.8.1    | Variance chart rendering                   |
| Markdown        | react-markdown    | ^10.1.0   | LLM response formatting                    |
| HTTP Client     | Fetch API (native)| —         | REST calls to FastAPI backend              |
| Dev Proxy       | Vite Proxy        | —         | Forwards /chat, /guided, /health etc.      |

### 3.2 Backend

| Component            | Technology          | Version     | Notes                                       |
|----------------------|---------------------|-------------|---------------------------------------------|
| Web Framework        | FastAPI             | >=0.111.0   | Async, ASGI-based                           |
| ASGI Server          | Uvicorn (standard)  | >=0.29.0    | httptools + uvloop for performance          |
| Data Validation      | Pydantic            | >=2.7.0     | Request/response schema enforcement         |
| Async HTTP Client    | httpx               | >=0.27.0    | Ollama and Sarvam AI communication          |
| Date Parsing         | python-dateutil     | >=2.9.0     | Fuzzy date recognition                      |
| Fuzzy Matching       | rapidfuzz           | >=3.0.0     | Keyword escape guard in SQL validator       |
| XBRL Toolkit         | Arelle              | latest      | XBRL instance comparison and validation     |
| Data Manipulation    | pandas              | >=2.0.0     | Variance DataFrame processing               |
| Config Management    | python-dotenv       | >=1.0.0     | .env file loading                           |
| File Upload          | python-multipart    | >=0.0.9     | Speech-to-text audio upload                 |

### 3.3 Database

| Component             | Technology         | Version   | Notes                                    |
|-----------------------|--------------------|-----------|------------------------------------------|
| Database Engine       | Oracle Database    | XE / EE   | Primary data store                       |
| Python Driver         | oracledb           | >=2.2.0   | Thin mode — no Oracle Client required    |
| Connection Model      | Connection Pool    | —         | min=1, max=5, increment=1                |
| Locale Configuration  | NLS_DATE_LANGUAGE  | AMERICAN  | Set via session callback on pool init    |


### 3.4 AI/LLM Components

| Component              | Technology                | Notes                                        |
|------------------------|---------------------------|----------------------------------------------|
| LLM Runtime            | Ollama                    | Local inference server (port 11434)          |
| Intent/Extraction LLM  | phi3:mini (default)       | Fast, low-latency intent + entity extraction |
| Conversational LLM     | Configurable (see §4)     | Chat fallback and response beautification    |
| SQL Generation LLM     | mistral (default)         | Configured via SQL_OLLAMA_MODEL              |
| Embedding Model        | BAAI/bge-large-en         | SentenceTransformer for FAISS vector search  |
| Vector Search Engine   | FAISS (CPU)               | >=1.7.4 — schema table/column retrieval      |
| Speech-to-Text         | Sarvam AI API             | Cloud API, API key required                  |

### 3.5 Infrastructure

| Component        | Technology                | Notes                                           |
|------------------|---------------------------|-------------------------------------------------|
| Web Server       | Nginx                     | Reverse proxy, static file serving, SSL         |
| Containerisation | Docker / Docker Compose   | Optional; recommended for production            |
| Process Manager  | Uvicorn / systemd         | Service lifecycle management                    |
| Source Control   | Git                       | Feature-branch workflow                         |
| OS               | Linux (Ubuntu 22.04 LTS)  | Primary deployment target                       |

---

## 4. AI Model Details

### 4.1 Primary Models

| Role                     | Model Name            | Provider  | Context Window | Temperature | Notes                                    |
|--------------------------|-----------------------|-----------|----------------|-------------|------------------------------------------|
| Intent Extraction        | `phi3:mini`           | Ollama    | 4K tokens      | 0.0         | Structured JSON-only output; deterministic |
| Conversational Fallback  | `phi3:mini` (default) | Ollama    | 4K tokens      | 0.7         | Configurable via `OLLAMA_MODEL`           |
| SQL Generation           | `mistral:7b` (default)| Ollama    | 8K tokens      | 0.1         | Configurable via `SQL_OLLAMA_MODEL`       |
| XBRL Comparative Summary | `mistral:latest`      | Ollama    | 8K tokens      | 0.5         | Configured in `xbrl_comparator.py`        |
| Response Beautification  | Same as OLLAMA_MODEL  | Ollama    | 4K tokens      | 0.7         | DB Q&A result formatting                  |
| Embedding                | `BAAI/bge-large-en`   | HuggingFace | 512 tokens   | N/A         | SentenceTransformer; CPU inference        |

> **Note:** The deployment environment at time of writing uses `gpt-oss:120b-cloud` as `OLLAMA_MODEL` for higher-quality conversational responses. See `OLLAMA_MODEL` in §9.

### 4.2 Model Resource Requirements

| Model               | Approx. VRAM | Approx. Host RAM | Mode         |
|---------------------|--------------|------------------|--------------|
| phi3:mini           | 2 GB         | 4 GB             | GPU / CPU    |
| mistral:7b          | 7 GB         | 8 GB             | GPU preferred|
| BAAI/bge-large-en   | N/A (CPU)    | 2 GB             | CPU          |
| gpt-oss:120b-cloud  | Provider     | N/A              | Cloud API    |

### 4.3 Token Limits

| Endpoint / Context           | Max Input Tokens | Max Output Tokens | Timeout     |
|------------------------------|------------------|-------------------|-------------|
| Intent extraction            | ~500             | ~200              | 30 s        |
| Conversational chat          | ~2000            | ~1000             | 180 s       |
| SQL generation               | ~3000            | ~500              | 60 s        |
| DB Q&A beautification        | ~1500            | ~500              | 60 s        |
| User message (API boundary)  | 2000 chars       | N/A               | N/A         |

### 4.4 Prompt Templates Used

| Template Name              | Location                                  | Purpose                                              |
|----------------------------|-------------------------------------------|------------------------------------------------------|
| Intent Extraction Prompt   | `backend/services/llm_service.py`         | Structured JSON intent + entity extraction           |
| SQL Generation Prompt      | `backend/sql_agent/sql_generator.py`      | Oracle SQL generation from schema + user query       |
| DB Q&A Beautification      | `backend/db_qa/beautifier.py`             | Human-readable formatting of XML lookup results      |
| Comparative Summary Prompt | `backend/tools/xbrl_comparator.py`        | XBRL variance narrative generation                   |
| Conversational Fallback    | `backend/services/llm_service.py`         | General Q&A and help responses                       |

### 4.5 SQL Agent Workflow

```
User Query (NL)
    │
    ▼
[1] Intent = "query_database" confirmed by LLM Extractor
    │
    ▼
[2] L1 Vector Search (FAISS table_index + column_index)
    → Embed query with BAAI/bge-large-en
    → Retrieve top-K=5 tables, top-K=5 columns
    │
    ▼
[3] L2/L3 Vector Search (row_label_index)
    → Retrieve matching row-label values
    │
    ▼
[4] Build SQL Prompt
    → Inject retrieved schema fragment + column descriptions
    → Append user query + conversation history context
    │
    ▼
[5] Ollama SQL Generation (mistral / configured model)
    → Returns raw SQL string
    │
    ▼
[6] SQL Validation
    → Banned keyword check (DELETE/UPDATE/DROP/INSERT/TRUNCATE/ALTER/CREATE/EXEC)
    → Table/column name cross-validation against schema.json
    → Unbalanced parenthesis auto-correction
    │
    ▼
[7] Oracle Execution
    → Connection acquired from pool
    → NLS session parameters applied
    → Results limited to ORACLE_MAX_ROWS (default 100)
    │
    ▼
[8] Response Assembly
    → db_columns, db_rows, db_sql populated in ChatResponse
    → accuracy_hint injected if query lacks time context
    → db_error populated on execution failure
```

---

## 5. SQL Agent Design

### 5.1 User Query Processing Flow

All incoming messages arrive at `POST /chat`. The `ChatRequest` Pydantic model enforces:
- `message`: 1–2000 characters (required)
- `session_id`: optional, max 128 chars
- `login_id`: forwarded from parent .NET application
- `conversation_history`: last 6–7 turns for context

### 5.2 Intent Detection

Intent classification is performed by the LLM in a single API call to Ollama (`OLLAMA_EXTRACT_MODEL`). The system prompt instructs the model to return only a valid JSON object with the following fields:

| Field           | Type     | Description                              |
|-----------------|----------|------------------------------------------|
| `intent`        | string   | One of 20+ defined intent strings        |
| `report_name`   | string?  | Extracted report/institution identifier  |
| `reporting_date`| string?  | Reporting period (preserved as-is)       |
| `schedule_date` | string?  | Scheduled execution date                 |
| `schedule_time` | string?  | Scheduled execution time                 |
| `target_user`   | string?  | Specific user mentioned                  |
| `target_department` | string? | Specific department mentioned         |
| `query_type`    | string?  | Filter: "active"/"inactive"/"all"/"count"|

**Intent Priority Order:**
1. **Workflow Intents** — report status, generation, scheduling, comparison
2. **App Q&A Intents** (`db_*`) — user/department/role/permission queries against XML config
3. **SQL Agent Intent** (`query_database`) — Oracle banking data analytics
4. **Unknown** — greetings, small talk

A secondary regex-based classifier (`backend/db_qa/intent_classifier.py`) provides a fallback and fine-grained sub-intent mapping for DB Q&A queries.

### 5.3 Schema Retrieval

FAISS vector indexes are pre-built from Oracle DDL (`sql_agent/data/schema.sql`) and column descriptions. At query time:

| Index           | Content                        | Retrieval (Top-K) |
|-----------------|--------------------------------|--------------------|
| `table_index`   | Table names + descriptions     | 5                  |
| `column_index`  | Column names + types + context | 5                  |
| `row_label_index` | Distinct row-label values    | 5                  |

The embedding model (`BAAI/bge-large-en`) with prefix `"Represent this sentence for searching relevant passages: "` is applied to both index-build and query-time vectors for consistent cosine similarity search.

### 5.4 SQL Generation

Retrieved schema fragments (table names, column names, types, sample values) are assembled into a structured prompt sent to `OLLAMA_MODEL` (configured as SQL generation model via `SQL_OLLAMA_MODEL`). The prompt enforces:
- Oracle SQL syntax only (no ANSI-only constructs)
- Single SELECT statement
- Use of schema-verified table and column names
- Date formatting using Oracle's `TO_DATE` / `NLS_DATE_FORMAT`

### 5.5 Query Validation

Before execution, every LLM-generated SQL is checked:

| Validation                | Logic                                               |
|---------------------------|-----------------------------------------------------|
| Banned keyword guard      | Rejects DML/DDL keywords (case-insensitive)         |
| Table name verification   | Cross-checks against `schema.json` + `USER_TABLES` |
| Column name verification  | Cross-checks against extracted schema fragment      |
| Paren balancing           | Auto-removes unmatched closing parentheses          |
| Oracle pseudo-table guard | Allows `DUAL` unconditionally                       |

### 5.6 Query Execution

Queries execute via the `oracledb` connection pool:
- **Pool config**: min=1, max=5, increment=1
- **Row limit**: `ORACLE_MAX_ROWS` env var (default 100)
- **NLS settings**: Applied once per connection via `session_callback`
  - `NLS_DATE_LANGUAGE = 'AMERICAN'`
  - `NLS_DATE_FORMAT = 'DD-MON-YYYY'`
  - `NLS_NUMERIC_CHARACTERS = '.,'`
- All query results are serialised to JSON-safe Python types before response

### 5.7 Response Generation

The `ChatResponse` Pydantic model carries:
- `db_columns` — list of column header strings
- `db_rows` — list of serialised result rows
- `db_sql` — the validated SQL sent to Oracle (shown to user)
- `db_error` — Oracle error message if execution fails
- `accuracy_hint` — soft suggestion if query lacks temporal context
- `needs_more_info` / `more_info_hint` — triggered for ambiguous queries

### 5.8 Error Handling

| Error Type                   | Behaviour                                                  |
|------------------------------|------------------------------------------------------------|
| Ollama unavailable           | HTTP 503 returned; user sees "AI model unavailable" message|
| Oracle connection failure    | Pool falls back to direct connect; error logged            |
| SQL execution error          | `db_error` populated; no exception raised to user          |
| Invalid SQL (banned keyword) | Query rejected before Oracle; safe error response returned |
| Unknown intent               | Routed to conversational LLM fallback                      |
| Unhandled exception          | Caught by global exception handler; HTTP 500 returned      |

---

## 6. Database Requirements

### 6.1 Oracle Version

| Item              | Requirement                                          |
|-------------------|------------------------------------------------------|
| Oracle Version    | Oracle Database 21c XE or Oracle Database 19c+       |
| Driver            | `oracledb` >= 2.2.0 (Python thin mode — no OCI required) |
| Port              | 1521 (default, configurable)                         |
| Protocol          | TCP/IP                                               |
| Connection Model  | Service Name (not SID)                               |

### 6.2 Required Schemas

| Schema / User     | Purpose                                         |
|-------------------|-------------------------------------------------|
| Application schema (e.g., `SOUTHINDIANBANK`) | Primary data schema containing all business tables |
| DDL Definition    | Tables must match `sql_agent/data/schema.sql`   |

### 6.3 Database Permissions

The Oracle user configured in `ORACLE_USER` requires the following minimum grants:

```sql
-- SELECT access on all application tables
GRANT SELECT ON <schema>.* TO <oracle_user>;

-- Read USER_TABLES for accessible table discovery
GRANT SELECT ON USER_TABLES TO <oracle_user>;

-- Optionally: read ALL_TAB_COLUMNS for column metadata
GRANT SELECT ON ALL_TAB_COLUMNS TO <oracle_user>;
```

**Important:** The Oracle user must NOT be granted DML privileges (INSERT/UPDATE/DELETE/TRUNCATE). The SQL Agent enforces a banned-keyword check, but principle of least privilege requires database-level enforcement as well.

### 6.4 Connection Pool Configuration

| Parameter         | Default | Override Env Var     |
|-------------------|---------|----------------------|
| Host              | localhost | `ORACLE_HOST`      |
| Port              | 1521    | `ORACLE_PORT`        |
| Service Name      | XE      | `ORACLE_SERVICE`     |
| Username          | —       | `ORACLE_USER`        |
| Password          | —       | `ORACLE_PASSWORD`    |
| Pool Min          | 1       | N/A (hardcoded)      |
| Pool Max          | 5       | N/A (hardcoded)      |
| Pool Increment    | 1       | N/A (hardcoded)      |
| Max Result Rows   | 100     | `ORACLE_MAX_ROWS`    |

### 6.5 Security Requirements

- Oracle password must be stored only in `.env` file with `600` file permissions
- `.env` file must never be committed to version control
- Oracle user should be a read-only service account
- Oracle connection must be made over an internal private network (no direct internet exposure)
- Consider Oracle Wallet or Vault-based credential storage for high-security deployments

---

## 7. Infrastructure Requirements

### 7.1 Minimum Server Specification

| Component          | Minimum                     | Recommended (Production)           |
|--------------------|-----------------------------|------------------------------------|
| **CPU**            | 8 vCPU                      | 16 vCPU                            |
| **Memory (RAM)**   | 16 GB                       | 32 GB                              |
| **Storage (OS)**   | 50 GB SSD                   | 100 GB SSD                         |
| **Storage (Models)**| 20 GB                      | 50 GB (multiple model variants)    |
| **Storage (Logs)** | 10 GB                       | 50 GB with log rotation            |
| **GPU**            | Optional (CPU mode supported)| NVIDIA GPU ≥8 GB VRAM (for speed) |
| **Network**        | 1 Gbps LAN                  | 10 Gbps LAN                        |

> **Note:** The BAAI/bge-large-en embedding model runs entirely on CPU. An Ollama LLM such as `mistral:7b` requires approximately 7 GB RAM (CPU-only quantized) or 7 GB VRAM (GPU). Larger models such as `gpt-oss:120b-cloud` or `llama2:70b` require substantially more resources or cloud API access.

### 7.2 Operating System

| Requirement       | Specification                              |
|-------------------|--------------------------------------------|
| Primary OS        | Ubuntu 22.04 LTS (or RHEL 8+ / CentOS 8+) |
| Architecture      | x86_64 (AMD64)                             |
| Kernel            | 5.15+                                      |
| SELinux / AppArmor| Configured to allow Ollama and uvicorn     |
| Time Sync         | NTP / chrony configured (Oracle dependency)|

### 7.3 Network Requirements

| Port   | Protocol | Service            | Direction         | Notes                            |
|--------|----------|--------------------|-------------------|----------------------------------|
| 443    | HTTPS    | Nginx (Frontend)   | Client → Server   | Production HTTPS entry point     |
| 8001   | HTTP     | FastAPI (Backend)  | Nginx → Backend   | Internal only; not exposed       |
| 3000   | HTTP     | Vite Dev Server    | Dev only          | Not exposed in production        |
| 11434  | HTTP     | Ollama LLM         | Backend → Ollama  | Internal loopback only           |
| 1521   | TCP      | Oracle DB          | Backend → Oracle  | Internal / VPN network           |
| 443    | HTTPS    | Sarvam AI API      | Backend → Cloud   | Outbound for speech-to-text      |

---

## 8. Software Prerequisites

### 8.1 Python

| Requirement       | Version          |
|-------------------|------------------|
| Python            | 3.10 or 3.11 (recommended) |
| pip               | Latest           |
| Virtual environment| venv / virtualenv |

### 8.2 Node.js

| Requirement       | Version          |
|-------------------|------------------|
| Node.js           | 18.x LTS or 20.x LTS |
| npm               | 9.x+             |

### 8.3 Oracle Client

The `oracledb` driver operates in **thin mode** — no Oracle Client (OCI) installation is required on the application server.

> **Exception:** If the deployment requires Oracle Wallet authentication or advanced Oracle features, the Oracle Instant Client 21.x must be installed and `oracledb.init_oracle_client()` called at startup.

### 8.4 Ollama Runtime

| Requirement       | Details                                         |
|-------------------|-------------------------------------------------|
| Ollama            | Latest stable (https://ollama.ai)               |
| Installation      | `curl -fsSL https://ollama.ai/install.sh | sh`  |
| Models required   | `phi3:mini`, `mistral:latest` (minimum)         |
| Service           | Must be running before FastAPI starts           |

### 8.5 Required Python Packages

All packages are declared in `requirements.txt`. Key dependencies:

```
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
oracledb>=2.2.0
httpx>=0.27.0
pydantic>=2.7.0
python-dotenv>=1.0.0
python-dateutil>=2.9.0
rapidfuzz>=3.0.0
sentence-transformers==2.7.0
faiss-cpu>=1.7.4
scipy
scikit-learn
arelle-release
pandas>=2.0.0
regex
tqdm
python-multipart>=0.0.9
```

### 8.6 Required Frontend Packages

All packages are declared in `frontend/package.json`:

```json
{
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-markdown": "^10.1.0",
    "recharts": "^3.8.1"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.1",
    "vite": "^5.4.0"
  }
}
```

---

## 9. Environment Variables

Create a `.env` file in the project root (`d:\IntegratedChatBot\.env` or `/opt/chatbot/.env` on Linux). This file must never be committed to source control.

### 9.1 Database Configuration

| Variable         | Required | Default         | Description                        |
|------------------|----------|-----------------|------------------------------------|
| `ORACLE_DSN`     | Yes*     | localhost:1521/XE | Full DSN (if not using individual vars) |
| `ORACLE_HOST`    | Yes      | localhost       | Oracle database hostname/IP        |
| `ORACLE_PORT`    | No       | 1521            | Oracle listener port               |
| `ORACLE_SERVICE` | Yes      | XE              | Oracle service name                |
| `ORACLE_USER`    | Yes      | —               | Oracle login username              |
| `ORACLE_PASSWORD`| Yes      | —               | Oracle login password              |
| `ORACLE_MAX_ROWS`| No       | 100             | Maximum rows returned per query    |

### 9.2 LLM Configuration

| Variable               | Required | Default                  | Description                             |
|------------------------|----------|--------------------------|-----------------------------------------|
| `OLLAMA_BASE_URL`      | Yes      | http://127.0.0.1:11434  | Ollama API base URL                     |
| `OLLAMA_EXTRACT_MODEL` | No       | phi3:mini               | Model for intent/entity extraction      |
| `OLLAMA_MODEL`         | No       | phi3:mini               | Model for conversational chat           |
| `SQL_OLLAMA_MODEL`     | No       | mistral                 | Model for SQL generation                |
| `OLLAMA_TIMEOUT`       | No       | 60                      | Chat response timeout (seconds)         |
| `OLLAMA_EXTRACT_TIMEOUT`| No      | 30                      | Extraction response timeout (seconds)   |
| `OLLAMA_KEEP_ALIVE`    | No       | 30m                     | Duration to keep models in memory       |

### 9.3 Embedding and Vector Search

| Variable            | Required | Default            | Description                             |
|---------------------|----------|--------------------|-----------------------------------------|
| `SQL_EMBED_MODEL`   | No       | BAAI/bge-large-en  | SentenceTransformer embedding model     |
| `SQL_QUERY_PREFIX`  | No       | (see config.py)    | Query prefix for BGE embedding          |
| `SQL_TOP_K_TABLES`  | No       | 5                  | FAISS top-K tables retrieved            |
| `SQL_TOP_K_COLUMNS` | No       | 5                  | FAISS top-K columns retrieved           |
| `FAISS_OUTPUT_DIR`  | No       | sql_agent/output/  | Directory for FAISS index artifacts     |

### 9.4 API Keys

| Variable          | Required | Default | Description                              |
|-------------------|----------|---------|------------------------------------------|
| `SARVAM_API_KEY`  | Yes*     | —       | Sarvam AI API key for speech-to-text     |

> * Required only if speech-to-text (`/speech-to-text`) endpoint will be used.

### 9.5 API and CORS Configuration

| Variable         | Required | Default                  | Description                              |
|------------------|----------|--------------------------|------------------------------------------|
| `CORS_ORIGINS`   | Yes      | http://localhost:3000    | Comma-separated list of allowed origins  |

### 9.6 Authentication Configuration

| Variable            | Required | Default | Description                                     |
|---------------------|----------|---------|-------------------------------------------------|
| `XML_USER_PATH`     | Yes      | —       | Absolute path to XML_User.xml                   |
| `XML_DEPT_PATH`     | Yes      | —       | Absolute path to XML_Dept.xml                   |
| `XML_ROLE_ACCESS_PATH` | Yes   | —       | Absolute path to XML_RoleAccess.xml             |
| `APP_DB_BASE_PATH`  | No       | —       | Base path for DB Q&A XML files                  |
| `AUTH_TTL_SEC`      | No       | 3600    | Auth cache TTL in seconds                       |
| `XML_USER_LOGIN_ATTR` | No    | LoginId | Attribute name for user login ID in XML         |
| `XML_USER_DEPT_ATTR`  | No    | DepartmentId | Attribute name for department ID in XML   |
| `XML_USER_ROLE_ATTR`  | No    | RoleId  | Attribute name for role ID in XML               |

### 9.7 Logging Configuration

| Variable         | Required | Default | Description                              |
|------------------|----------|---------|------------------------------------------|
| `LOG_DIR`        | No       | logs/   | Log file output directory                |

### 9.8 Sample .env File

```env
# ── Oracle Database ────────────────────────────────────────────────────────────
ORACLE_HOST=<db-server-ip>
ORACLE_PORT=1521
ORACLE_SERVICE=<service_name>
ORACLE_USER=<db_user>
ORACLE_PASSWORD=<db_password>
ORACLE_MAX_ROWS=100

# ── Ollama LLM ─────────────────────────────────────────────────────────────────
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_EXTRACT_MODEL=phi3:mini
OLLAMA_MODEL=mistral:latest
SQL_OLLAMA_MODEL=mistral:latest
OLLAMA_TIMEOUT=180
OLLAMA_EXTRACT_TIMEOUT=30
OLLAMA_KEEP_ALIVE=30m

# ── Sarvam AI (Speech-to-Text) ─────────────────────────────────────────────────
SARVAM_API_KEY=<your_api_key>

# ── FastAPI / CORS ─────────────────────────────────────────────────────────────
CORS_ORIGINS=https://<your-domain.com>

# ── Auth / XML Config ──────────────────────────────────────────────────────────
XML_USER_PATH=/opt/chatbot/config/XML_User.xml
XML_DEPT_PATH=/opt/chatbot/config/XML_Dept.xml
XML_ROLE_ACCESS_PATH=/opt/chatbot/config/XML_RoleAccess.xml
APP_DB_BASE_PATH=/opt/chatbot/config/
AUTH_TTL_SEC=3600
```

---

## 10. Deployment Procedure

### 10.1 Pre-Deployment Checklist

- [ ] Linux server provisioned and SSH access confirmed
- [ ] Oracle Database accessible from application server
- [ ] `.env` file prepared with all required values
- [ ] XML configuration files (User, Dept, RoleAccess) placed in target paths
- [ ] Ollama installed and required models pulled
- [ ] SSL certificate available for Nginx
- [ ] Git access to repository confirmed
- [ ] FAISS output directory (`sql_agent/output/`) populated or index build planned

---

### 10.2 Backend Deployment Steps

#### Step 1 — Clone Repository

```bash
cd /opt
git clone <repository-url> chatbot
cd /opt/chatbot
git checkout main   # or the release tag
```

#### Step 2 — Create and Activate Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### Step 3 — Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### Step 4 — Create Environment File

```bash
cp .env.example .env
nano .env          # fill in all required values
chmod 600 .env     # restrict read access
```

#### Step 5 — Build FAISS Indexes (One-Time Setup)

This step must be run once before the application starts and re-run whenever the Oracle schema changes.

```bash
source .venv/bin/activate
python backend/sql_agent/main.py
```

Expected output:
```
[1/6] Parsing schema SQL...       → N tables parsed from DDL
[1/6] Fetching accessible tables from Oracle...
[2/6] Loading column descriptions...
[3/6] Building enriched schema.json...
[4/6] Embedding table records...
[4/6] Embedding column records...
[5/6] Building FAISS indexes...
✅ L1 Vector DB (tables + columns) built successfully
[5/6] Fetching row-label samples from Oracle DB...
[6/6] Building row-label FAISS index...
✅ L2/L3 Row-label index built successfully
```

#### Step 6 — Create systemd Service

Create `/etc/systemd/system/chatbot-backend.service`:

```ini
[Unit]
Description=AI SQL Agent Chatbot — FastAPI Backend
After=network.target ollama.service

[Service]
User=chatbot
Group=chatbot
WorkingDirectory=/opt/chatbot
EnvironmentFile=/opt/chatbot/.env
ExecStart=/opt/chatbot/.venv/bin/uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port 8001 \
    --workers 2 \
    --log-level info
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable chatbot-backend
sudo systemctl start chatbot-backend
sudo systemctl status chatbot-backend
```

#### Step 7 — Verify Backend Health

```bash
curl http://localhost:8001/health
# Expected: {"status": "ok", ...}
```

---

### 10.3 Frontend Deployment Steps

#### Step 1 — Install Node.js Dependencies

```bash
cd /opt/chatbot/frontend
npm install
```

#### Step 2 — Configure API Base URL

For production, the frontend communicates directly through Nginx (no Vite proxy). Set the API base URL appropriately in `frontend/src/services/api.js` or via an environment variable.

#### Step 3 — Build Production Bundle

```bash
npm run build
```

Output will be placed in `frontend/dist/`.

#### Step 4 — Configure Nginx

Create `/etc/nginx/sites-available/chatbot`:

```nginx
server {
    listen 80;
    server_name <your-domain.com>;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name <your-domain.com>;

    ssl_certificate     /etc/ssl/certs/<cert>.pem;
    ssl_certificate_key /etc/ssl/private/<key>.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    # Serve React SPA static files
    root /opt/chatbot/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy API calls to FastAPI backend
    location ~ ^/(chat|compare-execute|guided|reports|speech-to-text|health|download-file) {
        proxy_pass         http://127.0.0.1:8001;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/chatbot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

### 10.4 Docker Deployment Steps

#### Step 1 — Backend Dockerfile

Create `Dockerfile.backend` in the project root:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY sql_agent/ ./sql_agent/

EXPOSE 8001
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "2"]
```

#### Step 2 — Frontend Dockerfile

Create `Dockerfile.frontend` in `frontend/`:

```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

#### Step 3 — Docker Compose

Create `docker-compose.yml` in the project root:

```yaml
version: "3.9"

services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    env_file: .env
    ports:
      - "8001:8001"
    volumes:
      - ./sql_agent/output:/app/sql_agent/output:ro
      - ./logs:/app/logs
    depends_on:
      - ollama
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.frontend
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - /etc/ssl:/etc/ssl:ro
    depends_on:
      - backend
    restart: unless-stopped

  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    restart: unless-stopped

volumes:
  ollama_data:
```

#### Step 4 — Pull Ollama Models and Start

```bash
docker compose up -d ollama
docker exec -it <ollama_container> ollama pull phi3:mini
docker exec -it <ollama_container> ollama pull mistral:latest
docker compose up -d
```

---

### 10.5 Ollama Setup

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull required models
ollama pull phi3:mini      # intent extraction (~2 GB)
ollama pull mistral:latest # SQL generation + chat (~7 GB)

# Verify
ollama list
ollama run phi3:mini "Hello"

# Enable as system service (auto-starts on boot)
sudo systemctl enable ollama
sudo systemctl start ollama
```

---

## 11. API Documentation

### 11.1 Base URL

| Environment | Base URL                         |
|-------------|----------------------------------|
| Development | `http://localhost:8001`          |
| Production  | `https://<your-domain.com>`      |

### 11.2 Chat API

#### `POST /chat`

Primary conversational endpoint. Handles all user messages, routes to appropriate agent, and returns structured response.

**Request Body:**

```json
{
  "message": "Show me the NPA data for March 2026",
  "session_id": "abc123",
  "asp_session": "<forwarded-session-cookie>",
  "login_id": "user001",
  "conversation_history": [
    {"role": "user", "text": "Previous message"},
    {"role": "assistant", "text": "Previous response"}
  ],
  "beautify": true,
  "user_id": "USR001",
  "role_id": "ADMIN"
}
```

| Field                  | Type    | Required | Description                            |
|------------------------|---------|----------|----------------------------------------|
| `message`              | string  | Yes      | User query (1–2000 characters)         |
| `session_id`           | string  | No       | Session identifier for multi-turn state|
| `asp_session`          | string  | No       | Forwarded .NET session cookie          |
| `login_id`             | string  | No       | User login ID for authorization        |
| `conversation_history` | array   | No       | Last 6–7 conversation turns            |
| `beautify`             | boolean | No       | Enable LLM response formatting (default: true) |
| `user_id`              | string  | No       | User ID for DB Q&A role check          |
| `role_id`              | string  | No       | Role ID for permission enforcement     |

**Response (ChatResponse):**

```json
{
  "intent": "query_database",
  "report_name": null,
  "response_text": "Here are the NPA records for March 2026:",
  "need_clarification": false,
  "result_type": "final",
  "options": [],
  "db_columns": ["ACCOUNT_NO", "NPA_AMOUNT", "NPA_DATE"],
  "db_rows": [["ACC001", 150000, "31-MAR-2026"]],
  "db_sql": "SELECT ACCOUNT_NO, NPA_AMOUNT, NPA_DATE FROM NPA_MASTER WHERE ...",
  "db_error": null,
  "accuracy_hint": null,
  "needs_more_info": false
}
```

**Status Codes:**

| Code | Meaning                                      |
|------|----------------------------------------------|
| 200  | Success                                      |
| 400  | Validation error (message too long/short)    |
| 503  | Ollama unavailable                           |
| 500  | Internal server error                        |

---

#### `POST /compare-execute`

Execute a pre-staged XBRL report comparison. Called after the user selects two instances from the disambiguation UI.

**Request Body:**

```json
{
  "session_id": "abc123",
  "instance_a": 0,
  "instance_b": 1
}
```

---

### 11.3 Speech-to-Text API

#### `POST /speech-to-text`

Accepts an audio file upload and returns the transcribed text via Sarvam AI.

**Request:** `multipart/form-data` with field `file` (audio file, e.g., WAV/MP3)

**Response:**

```json
{
  "text": "Show me NPA data for last quarter"
}
```

---

### 11.4 Health Check API

#### `GET /health`

Returns the application health status. Used by load balancers and monitoring tools.

**Response:**

```json
{
  "status": "ok",
  "version": "3.0.0",
  "timestamp": "2026-06-03T10:30:00Z"
}
```

---

### 11.5 File Download API

#### `GET /download-file`

Returns a generated file (render document, export) as a binary response.

**Query Parameters:** `path` — relative file path within the configured render directory.

---

### 11.6 Guided Flow API

#### `POST /guided`

Handles multi-step guided workflows (report generation wizard, scheduling confirmation).

---

## 12. Security Configuration

### 12.1 Authentication

The application integrates with the parent iDEAL .NET platform's authentication system:

- The `.NET` application authenticates users and forwards the `login_id` and `asp_session` cookie with each API request
- The `auth_service.py` module reads XML-based user/department/role configuration files to resolve permissions for each `login_id`
- Auth lookups are TTL-cached (default 1 hour) to avoid repeated XML file reads
- All auth checks occur server-side; the frontend does not perform authorization decisions

**Session Security:**
- Session IDs are UUIDs generated per user interaction
- Maximum session ID length enforced: 128 characters (Pydantic validation)
- No sensitive data is persisted in server-side session storage beyond report-staging metadata

### 12.2 Authorization

| Operation               | Enforcement                                              |
|-------------------------|----------------------------------------------------------|
| Report access           | FormId allowlist from `XML_Dept.xml` per department      |
| Instance generation     | `HasNew` flag from `XML_RoleAccess.xml` per role         |
| Database Q&A admin ops  | Admin `role_id` check in DB Q&A router                   |
| SQL query execution     | Banned keyword check + read-only Oracle user             |

### 12.3 SQL Injection Prevention

The application implements multiple layers of SQL injection defense:

1. **LLM-Generated SQL** — The LLM generates SQL from schema only; no user input is interpolated directly into SQL strings
2. **Banned Keyword Filter** — All LLM-generated SQL is scanned for DML/DDL keywords before execution:
   `DELETE`, `UPDATE`, `DROP`, `INSERT`, `TRUNCATE`, `ALTER`, `CREATE`, `EXEC`
3. **Schema Validation** — Table and column names are cross-validated against `schema.json` before execution
4. **Read-Only Database User** — The Oracle user has SELECT-only privileges at the database level
5. **Row Limit** — Queries are capped at `ORACLE_MAX_ROWS` rows, preventing data exfiltration via bulk retrieval

> **Note:** User-supplied natural language text is never directly concatenated into SQL strings. All SQL is generated by the LLM from a schema context prompt.

### 12.4 Prompt Injection Protection

| Threat                                      | Mitigation                                                   |
|---------------------------------------------|--------------------------------------------------------------|
| User input overriding system prompt         | System prompt is prepended server-side; user input is appended as a separate "user" role message |
| Jailbreak attempts in message text          | rapidfuzz keyword escape guard in agent pipeline             |
| Malicious JSON in LLM extraction response  | JSON parse failure falls back to `"unknown"` intent silently |
| Path traversal via report names            | Entity resolution uses fuzzy matching against allow-listed report names only |

### 12.5 Secrets Management

| Secret               | Storage Location    | Access Control         |
|----------------------|---------------------|------------------------|
| Oracle password      | `.env` file         | `chmod 600 .env`       |
| Sarvam AI API key    | `.env` file         | `chmod 600 .env`       |
| Oracle DSN           | `.env` file         | `chmod 600 .env`       |
| XML config file paths| `.env` file         | Read at startup only   |

**Production Recommendation:** Use a secrets manager (HashiCorp Vault, AWS Secrets Manager, or Linux `systemd` credential store) rather than a plaintext `.env` file. Never commit `.env` to version control.

### 12.6 HTTPS Configuration

- All traffic must be served over TLS 1.2+ in production
- Nginx is configured with `ssl_protocols TLSv1.2 TLSv1.3`
- HTTP traffic redirected to HTTPS with 301 permanent redirect
- HSTS header recommended: `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- CORS origins must be explicitly set to the production domain via `CORS_ORIGINS` env var

### 12.7 File System Security

```bash
# Application directory permissions
chown -R chatbot:chatbot /opt/chatbot
chmod 750 /opt/chatbot
chmod 600 /opt/chatbot/.env

# Log directory
chmod 750 /opt/chatbot/logs

# FAISS index directory (write-protected after initial build)
chmod 550 /opt/chatbot/sql_agent/output
```

---

## 13. Logging and Monitoring

### 13.1 Log Files

| File            | Level        | Max Size | Rotation | Content                               |
|-----------------|--------------|----------|----------|---------------------------------------|
| `logs/app.log`  | INFO+        | 10 MB    | 5 copies | All application events                |
| `logs/error.log`| ERROR+       | 10 MB    | 5 copies | Errors and exceptions only            |
| stdout          | DEBUG (dev) / INFO (prod) | N/A | N/A | Console output for systemd journal |

### 13.2 Log Format

```
2026-06-03 10:30:11 | INFO     | backend.agent | [INTENT] intent=query_database
2026-06-03 10:30:11 | INFO     | backend.main  | [PERF] endpoint=/chat intent=query_database duration=2.34s session=abc123
2026-06-03 10:30:12 | ERROR    | backend.sql_agent.executor | Oracle error: ORA-00942 table or view does not exist
```

### 13.3 Key Log Tags

| Tag                   | Module            | Description                                         |
|-----------------------|-------------------|-----------------------------------------------------|
| `[REQUEST]`           | main.py           | Incoming API request with session and query preview |
| `[INTENT]`            | agent             | Classified intent for a user query                  |
| `[PERF]`              | main.py           | Request duration and endpoint                       |
| `[AUTH]`              | auth_service.py   | Authorization lookup results                        |
| `[AUTH_CACHE]`        | auth_service.py   | Cache hit/miss for auth lookups                     |
| `[LLM_UNAVAILABLE]`   | main.py           | Ollama connection errors                            |
| `[UNHANDLED_ERROR]`   | main.py           | Uncaught exceptions                                 |
| `[WARMUP]`            | main.py           | Startup model pre-loading events                    |
| `[SQL_AGENT]`         | sql_agent         | SQL generation and execution events                 |
| `[DB_QA]`             | db_qa_router      | Database Q&A routing events                         |

### 13.4 SQL Query Logging

Every SQL query executed against Oracle is logged:
- The generated SQL is returned to the user in `db_sql`
- Errors are captured in `db_error`
- Query duration can be derived from `[PERF]` log entries

### 13.5 Agent Execution Logs

The debug trace module (`backend/utils/debug.py`) logs:
- Full `/chat` API hit details (message, login_id, session_id)
- Full `/chat` response summary (intent, result_type, elapsed time)

### 13.6 Monitoring Tools

| Tool              | Purpose                          | Setup Notes                          |
|-------------------|----------------------------------|--------------------------------------|
| `systemd journal` | Service start/stop events        | `journalctl -u chatbot-backend -f`   |
| Nginx access logs | HTTP request/response logging    | `/var/log/nginx/access.log`          |
| Uptime Kuma / Prometheus | API health and latency   | Monitor `/health` endpoint           |
| Grafana Loki      | Centralised log aggregation      | Point to `logs/app.log`              |

---

## 14. Backup and Recovery

### 14.1 What Requires Backup

| Artifact                  | Frequency  | Notes                                              |
|---------------------------|------------|----------------------------------------------------|
| `.env` file               | On change  | Store encrypted in secrets manager                 |
| XML config files          | On change  | XML_User.xml, XML_Dept.xml, XML_RoleAccess.xml     |
| `sql_agent/output/`       | On change  | FAISS indexes + schema.json                        |
| `sql_agent/data/schema.sql`| On change | Schema DDL used to build indexes                   |
| `logs/`                   | Daily      | Rotate and archive to object storage               |
| Oracle Database           | Per Oracle DBA policy | Application does not own the database   |

### 14.2 FAISS Index Backup

The FAISS indexes are build artifacts and can be fully regenerated by re-running `python backend/sql_agent/main.py`. However, backing them up avoids the ~10–30 minute rebuild time on recovery.

```bash
# Backup FAISS output directory
tar -czf faiss_backup_$(date +%Y%m%d).tar.gz sql_agent/output/
```

### 14.3 Configuration Backup

```bash
# Backup all configuration files
tar -czf config_backup_$(date +%Y%m%d).tar.gz \
    .env \
    sql_agent/data/ \
    backend/config/
```

> **Security note:** The `.env` backup must be encrypted. Use GPG or an equivalent:
> ```bash
> gpg --symmetric --cipher-algo AES256 config_backup_$(date +%Y%m%d).tar.gz
> ```

### 14.4 Recovery Procedures

**Scenario 1: Application server failure**

1. Provision new Linux server
2. Install Python 3.11, Node.js 20, Ollama
3. Clone repository and checkout correct tag
4. Restore `.env` and XML config files from backup
5. Install Python and Node.js dependencies
6. Restore FAISS indexes (or rebuild with `python backend/sql_agent/main.py`)
7. Build frontend (`npm run build`)
8. Configure Nginx and systemd service
9. Start Ollama, pull models, start backend service
10. Verify `/health` endpoint returns `{"status": "ok"}`

**Scenario 2: FAISS index corruption**

```bash
# Rebuild all indexes from scratch
source .venv/bin/activate
python backend/sql_agent/main.py
sudo systemctl restart chatbot-backend
```

**Scenario 3: Ollama model corruption**

```bash
ollama rm phi3:mini
ollama rm mistral:latest
ollama pull phi3:mini
ollama pull mistral:latest
sudo systemctl restart chatbot-backend
```

**Estimated Recovery Time Objective (RTO):** 2–4 hours (index rebuild included)
**Recovery Point Objective (RPO):** ≤ 24 hours (log loss only; no user data stored by application)

---

## 15. Testing and Validation

### 15.1 Functional Testing

| Test Case                              | Method                       | Expected Result                                        |
|----------------------------------------|------------------------------|--------------------------------------------------------|
| Health check endpoint                  | `GET /health`                | `{"status": "ok"}` with HTTP 200                       |
| Natural language SQL query             | `POST /chat` with DB query   | `db_columns`, `db_rows` populated; `db_error` null     |
| Intent detection — get_status          | `POST /chat`                 | `intent=get_status` in response                        |
| Intent detection — query_database      | `POST /chat`                 | `intent=query_database`, valid SQL returned            |
| Banned SQL keyword rejection           | `POST /chat` with "delete..." | `db_error` populated, no Oracle execution              |
| Speech-to-text                         | `POST /speech-to-text`       | Transcribed text returned                              |
| XBRL comparison                        | `POST /chat` with compare    | `variance_data` array populated                        |
| DB Q&A — list users                    | `POST /chat`                 | `db_intent=db_list_users`, `db_records` populated      |
| Auth deny — unknown user               | `POST /chat` unknown login_id| Access denied response                                 |

**Test scripts available in:**
- `test_api.py` — API integration tests
- `test_arelle.py` — XBRL comparison tests
- `test_llm_db_qa_integration.py` — DB Q&A integration tests
- `backend/tests/test_db_qa_integration.py` — DB Q&A unit tests
- `scripts/dbqa_test.py` — DB Q&A script tests

### 15.2 Performance Testing

| Metric                          | Target              | Method                              |
|---------------------------------|---------------------|-------------------------------------|
| Intent extraction latency       | < 3 s               | Timed POST /chat requests           |
| SQL query end-to-end latency    | < 10 s              | Timed POST /chat (query_database)   |
| Concurrent users                | 10 concurrent       | Load test with `locust` or `k6`     |
| FAISS index load time           | < 5 s at startup    | Verify warmup log entries           |
| Ollama warm response time       | < 5 s (warm)        | After first request with keep_alive |

### 15.3 Security Testing

| Test                              | Approach                                                   |
|-----------------------------------|------------------------------------------------------------|
| SQL injection via chat message    | Send raw SQL keywords; verify banned keyword rejection     |
| Prompt injection                  | Send "Ignore previous instructions..." in message field    |
| Oversized input                   | Send 2001+ character message; verify 422 Pydantic error    |
| Unauthorized FormId access        | Use login_id without permission; verify denial             |
| `.env` exposure                   | Verify no secrets in API responses or error messages       |
| DML via SQL Agent                 | Confirm UPDATE/DELETE queries never reach Oracle           |
| CORS misconfiguration             | Send requests from non-whitelisted origins; verify 403     |

### 15.4 UAT Checklist

- [ ] User can type a natural language question and receive an Oracle data table response
- [ ] Generated SQL is displayed correctly in the chat UI
- [ ] Voice input transcribes correctly and submits to chat
- [ ] Report status queries return correct instance status
- [ ] Report generation is restricted to authorized users
- [ ] XBRL comparison produces a variance chart
- [ ] DB Q&A returns correct user profile information
- [ ] Conversation history context is maintained across turns
- [ ] Error messages are user-friendly (no stack traces exposed)
- [ ] Application is accessible over HTTPS
- [ ] Session handling works correctly after 30+ minutes of inactivity

---

## 16. Operational Support

### 16.1 Support Contacts

| Role                     | Contact              | Responsibility                              |
|--------------------------|----------------------|---------------------------------------------|
| Application Owner        | [Name / Email]       | Business escalations, feature requests      |
| Backend Developer        | [Name / Email]       | FastAPI, SQL Agent, LLM integration         |
| Frontend Developer       | [Name / Email]       | React UI, build issues                      |
| Infrastructure / DevOps  | [Name / Email]       | Server, Nginx, Ollama, Docker, SSL          |
| Database Administrator   | [Name / Email]       | Oracle access, schema changes               |
| AI/LLM Lead              | [Name / Email]       | Model updates, FAISS index rebuilds         |

### 16.2 Incident Management

| Severity | Response Time | Description                                        |
|----------|---------------|----------------------------------------------------|
| P1       | 30 minutes    | Application completely unavailable                 |
| P2       | 2 hours       | Major feature broken (SQL Agent, XBRL comparison)  |
| P3       | 8 hours       | Minor feature degraded, workaround available       |
| P4       | Next business day | Cosmetic issues, logging gaps               |

### 16.3 Troubleshooting Guide

#### Problem: Backend returns HTTP 503

**Cause:** Ollama is not running or not reachable.

```bash
systemctl status ollama
curl http://localhost:11434/api/tags   # list loaded models
systemctl restart ollama
ollama pull phi3:mini                  # re-pull if model missing
systemctl restart chatbot-backend
```

#### Problem: SQL Agent returns no results / empty table

**Cause:** FAISS indexes may be stale or schema has changed.

```bash
source .venv/bin/activate
python backend/sql_agent/main.py    # rebuild indexes
systemctl restart chatbot-backend
```

#### Problem: Intent always returns "unknown"

**Cause:** Ollama extraction model is returning malformed JSON.

```bash
# Test model directly
curl http://localhost:11434/api/generate \
  -d '{"model":"phi3:mini","prompt":"Return JSON: {\"test\": 1}","stream":false}'

# Check backend logs for extraction errors
tail -f logs/app.log | grep -i "extract"
```

#### Problem: Oracle connection failure

**Cause:** Credentials wrong, Oracle service down, or network issue.

```bash
# Verify Oracle connectivity
python3 -c "
import oracledb
conn = oracledb.connect(user='USER', password='PASS', dsn='HOST:1521/SERVICE')
print('OK', conn.version)
conn.close()
"

# Check Oracle connection logs
grep -i "oracle\|ORA-" logs/app.log | tail -20
```

#### Problem: Authentication always denies access

**Cause:** XML_User.xml path is wrong or user login_id not present in file.

```bash
# Verify XML file paths
ls -la $XML_USER_PATH $XML_DEPT_PATH $XML_ROLE_ACCESS_PATH

# Check auth logs
grep "\[AUTH\]" logs/app.log | tail -20
```

#### Problem: FAISS index build fails

**Cause:** Oracle unreachable during index build, or schema.sql is missing.

```bash
# Verify data files exist
ls sql_agent/data/schema.sql

# Run with verbose output
python backend/sql_agent/main.py 2>&1 | tee index_build.log
```

---

## 17. Required Supporting Documents

The following documents should be prepared and maintained alongside this deployment document:

| Document                           | Purpose                                                           | Status          |
|------------------------------------|-------------------------------------------------------------------|-----------------|
| **High-Level Design (HLD)**        | System architecture, component overview, data flow               | [Pending/Done]  |
| **Low-Level Design (LLD)**         | Module-level design, class diagrams, sequence diagrams           | [Pending/Done]  |
| **API Documentation**              | OpenAPI / Swagger spec (available at `/docs` when running)       | Auto-generated  |
| **Database Schema Document**       | Oracle table definitions, column descriptions, relationships      | [Pending/Done]  |
| **Security Assessment**            | OWASP threat model, pen test results, vulnerability findings      | [Pending/Done]  |
| **User Guide**                     | End-user instructions for the chat interface                      | [Pending/Done]  |
| **Runbook**                        | Operational procedures, escalation paths, restart procedures      | [Pending/Done]  |
| **FAISS Index Build Guide**        | When and how to rebuild vector indexes                            | This document §10.2 Step 5 |
| **LLM Model Registry**             | Supported models, resource requirements, configuration            | `backend/config/llm_models.yml` |

---

## 18. Assumptions and Constraints

### 18.1 Assumptions

| #  | Assumption                                                                                      |
|----|-------------------------------------------------------------------------------------------------|
| A1 | The Oracle Database is already installed, provisioned, and accessible from the application server |
| A2 | The parent iDEAL .NET application is deployed and handles primary user authentication           |
| A3 | XML configuration files (XML_User.xml, XML_Dept.xml, XML_RoleAccess.xml) are maintained by the .NET platform team |
| A4 | The `sql_agent/data/schema.sql` file accurately reflects the deployed Oracle schema             |
| A5 | Outbound internet access is available for Sarvam AI API calls (speech-to-text)                  |
| A6 | The deployment server has sufficient hardware to run Ollama models in CPU mode at minimum       |
| A7 | The client's network allows TCP port 1521 between the application server and Oracle host        |
| A8 | An SSL certificate has been procured for the production domain                                  |
| A9 | A Git-based deployment pipeline or manual deployment process is agreed upon                     |

### 18.2 Constraints

| #  | Constraint                                                                                        |
|----|---------------------------------------------------------------------------------------------------|
| C1 | The SQL Agent is read-only; it cannot perform data modification operations                       |
| C2 | The system depends on Ollama being running; Ollama unavailability causes HTTP 503 responses       |
| C3 | LLM response quality and SQL accuracy depend on the quality of schema DDL and column descriptions |
| C4 | FAISS indexes must be rebuilt manually when the Oracle schema changes                             |
| C5 | Speech-to-text requires a valid Sarvam AI API key and outbound internet access                    |
| C6 | The maximum query result set is limited to `ORACLE_MAX_ROWS` (default 100 rows)                   |
| C7 | The application retains no user data beyond the current request; there is no persistent chat history storage |

---

## 19. Deployment Checklist

### Pre-Deployment

- [ ] Code reviewed and merged to release branch
- [ ] All unit tests and integration tests passing
- [ ] `.env` file prepared with production values
- [ ] Oracle credentials validated (connection test successful)
- [ ] XML configuration files validated and placed in target paths
- [ ] Ollama installed and required models pulled (`phi3:mini`, `mistral:latest`)
- [ ] SSL certificate installed in Nginx
- [ ] FAISS indexes built successfully (`python backend/sql_agent/main.py`)
- [ ] Log directory created with correct permissions
- [ ] `CORS_ORIGINS` set to production domain only

### Backend Deployment

- [ ] Python virtual environment created
- [ ] All Python dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` file in place with `chmod 600`
- [ ] `systemd` service created, enabled, and started
- [ ] `GET /health` returns `{"status": "ok"}`
- [ ] Backend logs show successful warmup of FAISS indexes and LLM models

### Frontend Deployment

- [ ] Node.js dependencies installed (`npm install`)
- [ ] Production build successful (`npm run build`)
- [ ] Nginx configured and reloaded
- [ ] Frontend accessible at `https://<domain>/`
- [ ] Chat interface loads and sends a test message successfully

### Post-Deployment Verification

- [ ] End-to-end SQL query test (natural language → Oracle results)
- [ ] Intent detection test (status, generate, compare, db_* intents)
- [ ] Auth enforcement test (authorised and unauthorised user)
- [ ] Speech-to-text test (if Sarvam AI key configured)
- [ ] XBRL comparison test
- [ ] Log files rotating correctly
- [ ] No secrets appearing in API responses or logs
- [ ] HTTP → HTTPS redirect working

---

## 20. Production Readiness Checklist

| Category               | Item                                                                 | Status       |
|------------------------|----------------------------------------------------------------------|--------------|
| **Security**           | HTTPS enforced (TLS 1.2+)                                            | [ ] Complete |
| **Security**           | `.env` file with `chmod 600`; never in version control               | [ ] Complete |
| **Security**           | Oracle user is read-only (SELECT only)                               | [ ] Complete |
| **Security**           | DML keywords blocked at application level                            | [ ] Complete |
| **Security**           | CORS restricted to production domain                                 | [ ] Complete |
| **Security**           | Prompt injection mitigation in place                                 | [ ] Complete |
| **Availability**       | Ollama configured to start on boot                                   | [ ] Complete |
| **Availability**       | FastAPI service configured as systemd service with auto-restart      | [ ] Complete |
| **Availability**       | Nginx reverse proxy configured and running                           | [ ] Complete |
| **Performance**        | FAISS indexes built and loaded (warmup confirmed in logs)            | [ ] Complete |
| **Performance**        | Ollama models warm (keep_alive configured)                           | [ ] Complete |
| **Performance**        | Connection pool configured (min=1, max=5)                            | [ ] Complete |
| **Reliability**        | Rotating log files configured (10 MB × 5 copies)                    | [ ] Complete |
| **Reliability**        | Oracle connection fallback to direct connect on pool failure         | [ ] Complete |
| **Observability**      | `[PERF]` and `[REQUEST]` log tags visible in app.log                 | [ ] Complete |
| **Observability**      | Health check endpoint responding                                     | [ ] Complete |
| **Data Integrity**     | `ORACLE_MAX_ROWS` set to appropriate limit                           | [ ] Complete |
| **Compliance**         | No user PII stored by application beyond session scope               | [ ] Complete |
| **Handover**           | All support contacts documented                                      | [ ] Complete |
| **Handover**           | Runbook available to operations team                                 | [ ] Complete |
| **Handover**           | This deployment document reviewed and signed off                     | [ ] Complete |

---

## Document Sign-Off

| Role                 | Name              | Signature        | Date         |
|----------------------|-------------------|------------------|--------------|
| Prepared By          |                   |                  |              |
| Technical Lead       |                   |                  |              |
| QA Lead              |                   |                  |              |
| Client Representative|                   |                  |              |
| Approved By          |                   |                  |              |

---

*End of Deployment Document — AI-Powered SQL Agent Chatbot v3.0.0*
*Classification: Confidential — Client Restricted*
