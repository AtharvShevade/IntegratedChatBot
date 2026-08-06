# backend/sql_agent/retriever.py
#
# Re-export of the vendored agent's retrieval layer.
#
# Note for callers used to the old agent: search() now takes a PRE-COMPUTED
# query embedding rather than a query string, and get_relevant_schema() returns
# FOUR values — (tables, columns, matched_labels, qa_example) — not three.
# Embed once with compute_query_embedding() and pass the vector around; the
# retrieval signals all reuse it.

from __future__ import annotations

from backend.sql_agent import _bootstrap

_bootstrap.ensure()

from src.retriever import (                                      # noqa: E402,F401
    STRONG_MATCH_MIN_RATIO,
    compute_query_embedding,
    find_exact_qa_match,
    get_relevant_schema,
    search,
    search_concepts,
    search_members,
    search_qa,
)
