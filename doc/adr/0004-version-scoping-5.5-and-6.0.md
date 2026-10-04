# 4. Coexistence of iDEAL versions 5.5 and 6.0 in one codebase

## Status
Accepted

## Date
2026-10-04 (ADR written retroactively, describing a decision already
implemented in the codebase; the original decision date is not recorded
anywhere in the repository)

## Context

This chatbot is embedded as an iframe inside a separate .NET web
application ("iDEAL"), which exists in two deployed versions — 5.5 and
6.0 — with materially different architectures the chatbot must each
integrate with correctly:

- **Repository layout**: 5.5 uses a single flat repo root
  (`BASE_REPO_PATH`, `DataBase\`/`Instance\`/`Render\` subfolders); 6.0 uses
  a per-tenant layout under `APP_600_REPO_ROOT` with an `XML_Tenant.xml`
  tenant map and numbered tenant folders (multi-tenant).
- **Identity/auth**: 5.5 passes identity via URL query params
  (`loginId`/`uid`/`roleId`/`aspSession`); 6.0 uses a `postMessage`
  handshake (`CHATBOT_READY` → parent replies `CHATBOT_AUTH`) carrying a
  JWT.
- **Instance generation API**: 5.5 calls a session-cookie-authenticated
  .NET endpoint (`DOTNET_API_URL`); 6.0 calls a separate JWT-bearer
  endpoint (`DOTNET_V6_API_URL`, `CreateInstanceController.GenerateReportDB`).
- **Database schema**: the SQL Agent's Oracle schema differs enough
  between the two versions that separate FAISS retrieval artifacts are
  maintained per version (`embeddings_5.5/`, `embeddings_6.0/` under
  `backend/sql_agent/`).
- **Frontend styling**: separate stylesheets (`App.5.5.css` /
  `App.6.0.css`), selected at runtime.

## Decision

Support both versions from a single codebase, switched by a single
process-level configuration value, `APP_VERSION` (`"5.5"` or `"6.0"`,
exposed as `version_config.IS_V6` and read in multiple places:
`backend/config.py`, `backend/version_config.py`,
`backend/sql_agent/_bootstrap.py`'s own independent re-check of the same
switch). A single running backend process serves exactly one version for
its entire lifetime — the switch is read once at/near startup, not
re-evaluated per request — rather than attempting to serve both versions
from one process, or running two entirely separate codebases/deployments.

Each version-dependent concern (repo path resolution, identity handling,
instance-generation API target, SQL Agent embeddings, frontend stylesheet)
branches independently on this one switch at the point where it actually
matters, rather than being centralized into one "version strategy" object
or abstraction layer.

## Alternatives considered

No in-repo record of alternatives considered was found. The standard
alternatives for this kind of situation — separate deployments/branches
per version, or a runtime multi-tenant-style switch evaluated per request
rather than per process — are not discussed anywhere in the repository;
they are listed here only as the standard alternatives, not as options
this project is known to have evaluated and rejected.

## Consequences

- Every version-dependent code path must be tested against both 5.5 and
  6.0 behavior; the backend test suite's baseline includes known
  pre-existing failures specific to one version's behavior assumptions
  (see `backend/tests/test_auth_service_dept_delimiter.py`'s 6.0-specific
  cases, for example), which is a direct consequence of maintaining both
  in parallel.
- A single running process cannot simultaneously serve both a 5.5 and a
  6.0 deployment — each deployment needs its own process (and its own
  `.env`/`APP_VERSION` value), consistent with this being a per-process,
  not per-request, switch.
- `backend/sql_agent/_bootstrap.py` re-derives the same `APP_VERSION`
  switch independently (reading it directly from the environment/`.env`,
  rather than importing `backend.version_config`) specifically so the
  vendored SQL Agent package's bootstrap does not require the rest of the
  application to already be initialized — this is a deliberate, narrow
  duplication of one config read, not an inconsistency to be "fixed" by
  centralizing it, since doing so would reintroduce an import-order
  dependency the vendored package's bootstrap was designed to avoid.
- Refusing to silently fall back to the other version's SQL Agent
  embeddings when the expected version's embedding folder is missing
  (`_bootstrap.py` raises `RuntimeError` rather than degrading) is a
  deliberate fail-closed choice: generating SQL against the wrong
  version's schema would produce queries referencing nonexistent
  tables/columns.
