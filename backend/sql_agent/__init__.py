# backend/sql_agent/__init__.py
#
# Chatbot-side adapter package for the SQL agent vendored at
# <project_root>/sql_agent. The actual pipeline (handle_db_query and its
# helpers) lives in query_handler.py; this file only runs the required
# bootstrap step and re-exports the public entry point, so that
# `from backend.sql_agent import handle_db_query` keeps working for
# backend/guided.py and backend/agent/__init__.py unchanged.

from __future__ import annotations

from backend.sql_agent import _bootstrap

# Runs before any `src.*` import anywhere in this package: puts the vendored
# agent on sys.path and maps this project's .env names onto the ones it reads.
_bootstrap.ensure()

from backend.sql_agent.query_handler import handle_db_query  # noqa: E402,F401

__all__ = ["handle_db_query"]
