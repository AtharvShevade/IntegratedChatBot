# Runbook: Rebuild embeddings

This repository has **two independent** embedding systems. Confirm which
one you actually need before proceeding — the procedures are not
interchangeable.

## A. Intent-classification exemplar index (`backend/db_qa/intents/`)

This is the semantic-match tier of the DB Q&A intent classifier.

### Prerequisites
- A working Python environment with the project's dependencies installed
  (`pip install -r requirements.txt`).
- The embedding model used is whatever `backend.sql_agent.sqlcore.config.EMBED_MODEL`
  resolves to (the intent index deliberately reuses the SQL Agent's own
  loaded `SentenceTransformer` instance rather than loading a second copy —
  see `backend/db_qa/intents/embedding_index.py`'s module docstring).

### How to rebuild
```powershell
python -m backend.db_qa.intents.embedding_index
```
This writes `intent_exemplar_index.faiss`, `intent_exemplar_meta.pkl`, and
`intent_exemplar_manifest.json` under `backend/db_qa/intents/output/`.

### Automatic rebuild
The backend also auto-rebuilds this specific index on first use if it
detects the on-disk index is stale relative to the current exemplar
definitions/embedding model (`check_index_freshness()` in
`embedding_index.py`) — a logged warning
(`"Intent exemplar index is stale ... rebuilding automatically"`) means
this happened without operator action.

### How to verify
- Confirm the three output files above exist and have a fresh timestamp.
- Restart the backend and check the startup log for the intent-index
  warm-up step completing without an automatic-rebuild warning on the
  very next request.

### If the rebuild fails
Check the log line immediately following `"Automatic rebuild of the intent
exemplar index failed"` (or the direct command's own traceback if run
manually) — this is swallowed gracefully at runtime (the backend keeps
serving the existing, possibly-stale index rather than crashing), so a
failure will not take the service down, but intent matching quality may
degrade until it's fixed.

## B. SQL Agent schema-retrieval artifacts (`backend/sql_agent/embeddings_5.5/`, `embeddings_6.0/`)

**There is no rebuild script for these artifacts in this repository.**
`backend/sql_agent/_bootstrap.py`'s own comment states this explicitly:
these are pre-built, shipped-as-data-files artifacts; "refreshing them is:
replace the contents of the matching folder below and restart; no rebuild
step runs in this repo." `doc/APP_OVERVIEW.md` references an original,
independent `sql_agent/` project (with its own schema-embedding builder
under `embedding_building/`) as the source of these artifacts, but that
standalone project **is not present in this checkout** — confirm with
whoever maintains it whether/how to regenerate these artifacts; do not
attempt to improvise a rebuild procedure for them.

### 5.5 vs 6.0 locations
- `backend/sql_agent/embeddings_5.5/`
- `backend/sql_agent/embeddings_6.0/`

Which one is active is decided by `APP_VERSION` in `_bootstrap.py`
(`EMBEDDING_DIR_6_0` if `APP_VERSION == "6.0"`, else `EMBEDDING_DIR_5_5`) —
**do not** copy one version's folder over the other's; the two schemas are
not interchangeable (`_bootstrap.ensure()` deliberately raises a
`RuntimeError` at startup rather than silently falling back to the wrong
version's embeddings if the expected folder is missing).

### How to verify (if artifacts are replaced manually)
- Confirm the replaced folder contains, at minimum, the FAISS index/meta
  pairs the rest of the pipeline expects (`table_index.faiss`/`table_meta.pkl`,
  `column_index.faiss`/`column_meta.pkl`, etc. — see
  `backend/sql_agent/config.py`'s derived-path constants for the full list).
- Restart the backend and check the `"[SQL_AGENT] bootstrapped root=... embedding_dir=..."`
  startup log line to confirm it picked up the expected directory.
- Run a known-good SQL Agent query through the chatbot and confirm it still
  resolves tables/columns correctly.

### If the rebuild/replace fails
If the expected embeddings folder is missing or empty for the active
`APP_VERSION`, the backend will **fail to start** (an intentional
fail-closed `RuntimeError` from `_bootstrap.ensure()`) rather than degrade
silently — this is expected behavior, not a bug; restore a valid artifact
set before restarting.
