# backend/sql_agent/semantic_layer.py
#
# Re-export of the vendored agent's semantic layer (semantic_layer.yaml in
# EMBEDDING_DIR): declared joins, vertical-table specs and metric definitions.
# The selector needs load_join_graph() to know which table pairs may legally be
# joined at all.

from __future__ import annotations

from backend.sql_agent import _bootstrap

_bootstrap.ensure()

from src.semantic_layer import (                                 # noqa: E402,F401
    clear_cache,
    load_join_graph,
    load_semantic_layer,
)
