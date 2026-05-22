# config.py — SQL agent settings, read entirely from environment variables.
# All values that were previously hardcoded in sql_agent/src/config.py are
# now controlled via .env so credentials are never committed to source control.

from __future__ import annotations

import os

# ── Paths ──────────────────────────────────────────────────────────────────────
_HERE         = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_HERE))   # IntegratedChatBot/

# Directory containing schema.sql and .json-formatted mapping file.
SQL_AGENT_DATA_DIR: str = os.path.join(_PROJECT_ROOT, "sql_agent", "data")

# Directory where main.py writes FAISS indexes and schema artifacts.
# Defaults to <project_root>/sql_agent/output so the gitignore rules
# already in place continue to work without any change.
FAISS_OUTPUT_DIR: str = os.getenv(
    "FAISS_OUTPUT_DIR",
    os.path.join(_PROJECT_ROOT, "sql_agent", "output"),
)

# ── Derived artifact paths (use these instead of hardcoded "output/...") ──────
TABLE_INDEX_PATH    = os.path.join(FAISS_OUTPUT_DIR, "table_index.faiss")
TABLE_META_PATH     = os.path.join(FAISS_OUTPUT_DIR, "table_meta.pkl")
COLUMN_INDEX_PATH   = os.path.join(FAISS_OUTPUT_DIR, "column_index.faiss")
COLUMN_META_PATH    = os.path.join(FAISS_OUTPUT_DIR, "column_meta.pkl")
ROW_LABEL_INDEX_PATH = os.path.join(FAISS_OUTPUT_DIR, "row_label_index.faiss")
ROW_LABEL_META_PATH  = os.path.join(FAISS_OUTPUT_DIR, "row_label_meta.pkl")
SCHEMA_JSON_PATH    = os.path.join(FAISS_OUTPUT_DIR, "schema.json")
DESC_SAMPLES_PATH   = os.path.join(FAISS_OUTPUT_DIR, "description_samples.json")

# ── Embedding model ────────────────────────────────────────────────────────────
EMBED_MODEL  = os.getenv("SQL_EMBED_MODEL",  "BAAI/bge-large-en")
QUERY_PREFIX = os.getenv(
    "SQL_QUERY_PREFIX",
    "Represent this sentence for searching relevant passages: ",
)

# ── FAISS retrieval settings ───────────────────────────────────────────────────
TOP_K_TABLES  = int(os.getenv("SQL_TOP_K_TABLES",  "5"))
TOP_K_COLUMNS = int(os.getenv("SQL_TOP_K_COLUMNS", "5"))

# ── Ollama settings ────────────────────────────────────────────────────────────
_ollama_base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_URL   = f"{_ollama_base}/api/generate"
OLLAMA_MODEL = os.getenv("SQL_OLLAMA_MODEL", os.getenv("OLLAMA_MODEL", "mistral"))

# ── Oracle DB connection settings ──────────────────────────────────────────────
# Use individual ORACLE_HOST / ORACLE_PORT / ORACLE_SERVICE env vars.
# If ORACLE_HOST is not set we fall back to parsing the existing ORACLE_DSN
# format  "host:port/service"  already present in .env.example.
def _parse_dsn(dsn: str):
    """Parse 'host:port/service' → (host, port, service)."""
    try:
        host_port, service = dsn.split("/", 1)
        host, port = host_port.rsplit(":", 1)
        return host.strip(), int(port.strip()), service.strip()
    except Exception:
        return "localhost", 1521, "XE"

_dsn = os.getenv("ORACLE_DSN", "localhost:1521/XE")
_default_host, _default_port, _default_service = _parse_dsn(_dsn)

DB_HOST    = os.getenv("ORACLE_HOST",    _default_host)
DB_PORT    = int(os.getenv("ORACLE_PORT", str(_default_port)))
DB_SERVICE = os.getenv("ORACLE_SERVICE", _default_service)
DB_USER    = os.getenv("ORACLE_USER",    "")
DB_PASSWORD = os.getenv("ORACLE_PASSWORD", "")
DB_MAX_ROWS = int(os.getenv("ORACLE_MAX_ROWS", "100"))

# ── Sarvam AI ─────────────────────────────────────────────────────────────────
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
