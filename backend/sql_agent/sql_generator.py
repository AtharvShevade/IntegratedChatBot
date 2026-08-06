# backend/sql_agent/sql_generator.py
#
# Re-export of the vendored agent's prompt-building / SQL-generation layer, plus
# the two path fix-ups it needs when driven from this project.
#
# Both settings below are relative paths in the agent's source, resolved against
# the current working directory — correct when it runs standalone from its own
# repo root, wrong when the chatbot process runs from the project root. They are
# repointed here (at runtime, so the vendored source stays unmodified) rather
# than left to fail silently: the DDL file is the authoritative column-type
# source for the prompt, and without it every column type falls back to the
# name-based guesser.

from __future__ import annotations

import logging

from backend.sql_agent import _bootstrap

_bootstrap.ensure()

import src.schema_store as _schema_store                         # noqa: E402
import src.sql_generator as _sql_generator                       # noqa: E402
from src.sql_generator import (                                  # noqa: E402,F401
    build_prompt,
    build_table_ddl,
    generate_sql,
    validate_sql,
)

logger = logging.getLogger(__name__)

# ── 1. Oracle DDL (data/schema.sql) ──────────────────────────────────────────
# _load_ddl_types() memoises into a module global on first call, so priming it
# here with the absolute path means every later no-arg call inside the agent
# gets the parsed types instead of an empty dict.
_ddl_types = _sql_generator._load_ddl_types(_bootstrap.DDL_SCHEMA_PATH)
if not _ddl_types:
    logger.warning(
        "[SQL_AGENT] No column types parsed from %s — the prompt will fall back "
        "to name-based type inference.", _bootstrap.DDL_SCHEMA_PATH,
    )

# ── 2. Legacy schema.json fallback ───────────────────────────────────────────
# Consulted only for tables missing from the active EMBEDDING_DIR schema.json. A
# missing file is handled gracefully by the agent, so this is best-effort.
_schema_store.LEGACY_SCHEMA_PATH = "/".join(
    [_bootstrap.SQL_AGENT_ROOT.replace("\\", "/"), "embedding_building/output/schema.json"]
)
