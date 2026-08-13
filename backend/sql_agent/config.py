# backend/sql_agent/config.py
#
# Re-exports the vendored agent's settings (sql_agent/src/config.py, populated
# from this project's .env by _bootstrap) under the import path the chatbot has
# always used: `backend.sql_agent.config`.
#
# It also re-derives the individual artefact paths (TABLE_INDEX_PATH & co). The
# new agent resolves those inline from config.EMBEDDING_DIR instead of exporting
# constants, but backend/main.py's startup warm-up still wants them by name, and
# naming them here keeps that call site readable.

from __future__ import annotations

import os

from backend.sql_agent import _bootstrap

_bootstrap.ensure()

from src.config import (                                        # noqa: E402
    BUSINESS_SEMANTICS_LEVEL,
    DB_HOST,
    DB_MAX_ROWS,
    DB_PASSWORD,
    DB_PORT,
    DB_SERVICE,
    DB_USER,
    EMBED_MODEL,
    EMBEDDING_DIR,
    MODEL_PROFILES,
    OLLAMA_KEEP_ALIVE,
    OLLAMA_MODEL,
    OLLAMA_NUM_CTX,
    OLLAMA_URL,
    QUERY_PREFIX,
    SHORTLIST_K,
    TOP_K_COLUMNS,
    TOP_K_TABLES,
)
import src.config as _src_config                                # noqa: E402

# The live settings module. Read mutable settings through this (the agent's own
# modules read `config.EMBEDDING_DIR` at call time on purpose) rather than
# relying on the constants imported above, which are snapshots.
SRC_CONFIG = _src_config

# ── Derived artefact paths ───────────────────────────────────────────────────
TABLE_INDEX_PATH     = os.path.join(EMBEDDING_DIR, "table_index.faiss")
TABLE_META_PATH      = os.path.join(EMBEDDING_DIR, "table_meta.pkl")
COLUMN_INDEX_PATH    = os.path.join(EMBEDDING_DIR, "column_index.faiss")
COLUMN_META_PATH     = os.path.join(EMBEDDING_DIR, "column_meta.pkl")
ROW_LABEL_INDEX_PATH = os.path.join(EMBEDDING_DIR, "row_label_index.faiss")
ROW_LABEL_META_PATH  = os.path.join(EMBEDDING_DIR, "row_label_meta.pkl")
QA_INDEX_PATH        = os.path.join(EMBEDDING_DIR, "qa_index.faiss")
QA_META_PATH         = os.path.join(EMBEDDING_DIR, "qa_meta.pkl")
SCHEMA_JSON_PATH     = os.path.join(EMBEDDING_DIR, "schema.json")
DESC_SAMPLES_PATH    = os.path.join(EMBEDDING_DIR, "description_samples.json")

# Kept for the old name; the agent no longer writes a separate output/ folder.
FAISS_OUTPUT_DIR = EMBEDDING_DIR

# Checked-in Oracle DDL — the column-type source for the generated prompt.
DDL_SCHEMA_PATH = _bootstrap.DDL_SCHEMA_PATH
