# backend/sql_agent/executor.py
#
# Re-export of the vendored agent's Oracle execution layer. Connections come
# from a pool created on first use with the ORACLE_* credentials in .env (mapped
# to the agent's DB_* names by _bootstrap).

from __future__ import annotations

from backend.sql_agent import _bootstrap

_bootstrap.ensure()

from src.executor import (                                       # noqa: E402,F401
    dry_run_sql,
    execute_query,
    get_accessible_tables,
    get_connection,
)
