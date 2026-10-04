# 2. Vendor the SQL Agent as a self-contained sub-package

## Status
Accepted

## Date
2026-10-04 (ADR written retroactively, describing a decision already
implemented in the codebase; the original decision date is not recorded
anywhere in the repository)

## Context

The natural-language-to-SQL engine used for the "SQL Agent" chat feature
originated as an independent project ("CIMS Banking Regulatory Reporting"
query generator, referenced in `doc/APP_OVERVIEW.md` as a standalone
`sql_agent/` project with its own FastAPI app, `src/` pipeline, and
schema-embedding builder). That standalone project is **not present in
this checkout** at the time of writing — only its vendored copy exists,
under `backend/sql_agent/`.

The vendored copy consists of:
- `backend/sql_agent/sqlcore/` — the engine's own internal package, imported
  internally as the top-level name `sqlcore` (not `backend.sql_agent.sqlcore`).
  Originally named the generic `src` (renamed as part of a 2026 hardening
  review, "L-11" — see Consequences below for why).
- `backend/sql_agent/_bootstrap.py` — translates this project's `.env`
  variable names (`ORACLE_*`, `OLLAMA_BASE_URL`, `SQL_OLLAMA_MODEL`) into
  the names the vendored engine's own `sqlcore/config.py` expects (`DB_*`,
  `OLLAMA_URL`, `OLLAMA_MODEL`), puts `backend/sql_agent/` on `sys.path`,
  then restores the process environment once the engine's config has been
  read.
- A set of thin re-export shim modules at `backend/sql_agent/*.py`
  (`config.py`, `executor.py`, `retriever.py`, `selector.py`,
  `semantic_layer.py`, `vectorizer.py`, `sql_generator.py`) — each imports
  from the vendored `sqlcore.*` package and re-exports under the import path
  this project's own code uses (`backend.sql_agent.config`, etc.), and each
  documents in its own header comment why it exists.
- Pre-built retrieval artifacts (`embeddings_5.5/`, `embeddings_6.0/` —
  separate FAISS indexes and metadata per application version, since the
  5.5 and 6.0 database schemas differ) and the Oracle DDL fallback
  (`data/schema.sql`), checked into the repository rather than rebuilt at
  install/startup time.

## Decision

Vendor a full copy of the engine's code and prebuilt artifacts directly
into `backend/sql_agent/`, rather than depending on the standalone
`sql_agent/` project as an external package (e.g. via `pip install -e` or
a git submodule), and rather than rewriting the engine's logic natively
into `backend/`'s own module structure.

The vendored engine originally kept its own internal package name (`src`,
renamed to `sqlcore` — see Consequences) and its
own environment-variable names, with `_bootstrap.py` acting as the
translation/adapter layer between the two projects' independently-chosen
naming conventions, rather than renaming the vendored engine's internals
to match this project's conventions throughout.

## Alternatives considered

No in-repo record of an alternatives-considered discussion for this
decision was found. Alternatives one would normally weigh for this kind of
vendoring decision — a git submodule, a published/installable package
dependency, or a full rewrite into native `backend/` modules — are not
discussed anywhere in the repository; they are listed here only as the
standard alternatives to vendoring, not as options this project is known
to have evaluated and rejected.

## Consequences

- The vendored engine can evolve independently of its original project,
  but also means the two can drift apart with no automated way to detect
  or re-sync divergence — the original standalone project is not even
  present in this checkout to diff against.
- `src` as a vendored-package top-level name was originally a generic,
  collision-prone choice: if any other top-level `src` package were ever
  imported in the same Python process, `sys.modules['src']` would already
  hold whichever one imported first, silently resolving the other's
  `from src.xxx import` statements to the wrong module. This was identified
  as part of a 2026 hardening review ("L-11"), initially left unaddressed as
  an architecture-level change outside the scope of incremental hardening
  work, and later carried out as a dedicated cleanup: the package was
  renamed to `sqlcore` across every file in the vendored engine, the
  `backend/sql_agent/*.py` shims, and this project's test suite. The
  namespace-collision risk is closed; the package's module contents and
  every existing public import path into it (`backend.sql_agent.*`) are
  unchanged.
- `_bootstrap.ensure()` is idempotent and restores the process environment
  after reading the vendored engine's config, specifically so the vendored
  engine's own model/DB settings (which reuse some of this project's own
  environment-variable names for different purposes, e.g. `OLLAMA_MODEL`)
  never leak into the rest of the process.
- The 5.5/6.0 embedding split means an operator must keep both artifact
  sets in sync with their respective live schemas by hand; there is no
  rebuild tooling for these specific artifacts within this repository (see
  `doc/runbooks/rebuild-embeddings.md`).
