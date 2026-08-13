# backend/sql_agent/sql_generator.py
#
# Re-export of the vendored agent's prompt-building / SQL-generation layer,
# plus the one path fix-up it needs: priming the Oracle DDL column-type cache
# with this package's own absolute data/schema.sql path.
#
# There is no legacy schema.json fallback to configure any more — the
# consolidated package has exactly one schema.json, under embeddings/, and no
# embedding_building/output/ tree exists anywhere in this deployment.

from __future__ import annotations

import logging

from backend.sql_agent import _bootstrap

_bootstrap.ensure()

import src.sql_generator as _sql_generator                       # noqa: E402
from src.sql_generator import (                                  # noqa: E402,F401
    build_prompt,
    build_table_ddl,
    generate_sql,
    validate_sql,
)

logger = logging.getLogger(__name__)

# _load_ddl_types() memoises into a module global on first call, so priming it
# here with the absolute path means every later no-arg call inside the agent
# gets the parsed types instead of an empty dict.
_ddl_types = _sql_generator._load_ddl_types(_bootstrap.DDL_SCHEMA_PATH)
if not _ddl_types:
    logger.warning(
        "[SQL_AGENT] No column types parsed from %s — the prompt will fall back "
        "to name-based type inference.", _bootstrap.DDL_SCHEMA_PATH,
    )
