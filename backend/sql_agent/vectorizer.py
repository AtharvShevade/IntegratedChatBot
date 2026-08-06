# backend/sql_agent/vectorizer.py
#
# Re-export of the vendored agent's embedding helpers under the import path the
# chatbot uses. backend/db_qa/intents/embedding_index.py deliberately reuses this
# module's single SentenceTransformer instance instead of loading a second copy
# of BGE-large into memory, and backend/main.py imports it at startup purely to
# pay the model-load cost before the first request.

from __future__ import annotations

from backend.sql_agent import _bootstrap

_bootstrap.ensure()

from src.vectorizer import (                                     # noqa: E402,F401
    build_faiss_index,
    build_row_label_index,
    embed_documents,
    embed_query,
    model,
    normalize_text,
    save_index,
)
