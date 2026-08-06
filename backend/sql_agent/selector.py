# backend/sql_agent/selector.py
#
# Re-export of the vendored agent's table selector — the stage that narrows the
# retrieval shortlist to the one table the SQL model actually sees. It is not
# optional: handing the whole shortlist to a 7B model is what made it JOIN every
# candidate and invent the foreign key to do it. Never raises; falls back to the
# top-1 retrieved table.

from __future__ import annotations

from backend.sql_agent import _bootstrap

_bootstrap.ensure()

from src.selector import select_tables                           # noqa: E402,F401
