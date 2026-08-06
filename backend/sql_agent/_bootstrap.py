# backend/sql_agent/_bootstrap.py
#
# Makes the vendored SQL agent at <project_root>/sql_agent importable as `src`
# (its own internal package name) and translates this project's .env variable
# names into the ones its src/config.py reads.
#
# Why a bootstrap instead of copying its source into backend/:
#   * src/sql_generator.py imports `embedding_building.parser`, and every
#     retrieval path resolves artefacts under config.EMBEDDING_DIR — both live
#     in the sql_agent tree. Keeping one copy on sys.path keeps those working,
#     keeps the rebuild scripts (embedding_building/, scripts/, eval/) working,
#     and means the next `git pull` of that repo is a drop-in.
#   * Nothing here edits its source, so we never have to re-apply patches.
#
# Env translation is required because the two projects independently named the
# same settings: this project has used ORACLE_* / OLLAMA_BASE_URL /
# SQL_OLLAMA_MODEL since the old agent, while sql_agent/src/config.py reads
# DB_* / OLLAMA_URL / OLLAMA_MODEL. Rather than duplicate credentials in .env
# under two names, we map them here, before src.config is ever imported.
#
# Import this module (or anything in this package — __init__ does it) before
# touching `src.*`.

from __future__ import annotations

import logging
import os
import sys

logger = logging.getLogger(__name__)

_HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(_HERE))

# Root of the vendored SQL agent checkout (the newly cloned implementation).
SQL_AGENT_ROOT = os.path.join(PROJECT_ROOT, "sql_agent")

# Retrieval artefacts (FAISS indexes, schema.json, qa_pairs.json,
# semantic_layer.yaml, concept_map.json). This is the scope the clone ships
# built and defaults to; kept in place rather than copied so a rebuild via
# embedding_building/ is immediately live for the chatbot too.
EMBEDDING_DIR = os.path.join(SQL_AGENT_ROOT, "embedding_building", "cims_raq_quarterly")

# Checked-in Oracle DDL, the authoritative column-type source for the prompt.
DDL_SCHEMA_PATH = os.path.join(SQL_AGENT_ROOT, "data", "schema.sql")

_done = False

# Every process-env key this module writes, recorded with its pre-existing value
# so it can be put back — see _restore_env() for why that matters.
_saved_env: dict = {}


def _setenv(name: str, value: str | None, *, override: bool) -> None:
    """Set os.environ[name] from `value`, skipping blanks. With override=False a
    value already in the real environment wins (same precedence rule the agent's
    own config documents for .env)."""
    if value is None or str(value).strip() == "":
        return
    if not override and os.environ.get(name, "").strip() != "":
        return
    if name not in _saved_env:
        _saved_env[name] = os.environ.get(name)      # None == was not set
    os.environ[name] = str(value)


def _restore_env() -> None:
    """Undo every _setenv() write, once src.config has read them.

    This is not tidiness — it is required for correctness. The agent's settings
    live under names the chatbot ALSO uses for different things: OLLAMA_MODEL is
    the SQL model here and the error-explanation/conversational model there, and
    it is read via os.getenv() on every call in backend/tools/report_lookup.py
    and backend/tools/formula_error_generic.py (and at import in
    backend/services/llm_service.py). Leaving SQLCoder in the process env would
    silently hand those features a model that can only emit SQL.

    Safe to restore immediately, because sql_agent/src/config.py snapshots every
    value into module-level constants at import time and nothing downstream in
    the agent re-reads os.environ.
    """
    for name, previous in _saved_env.items():
        if previous is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = previous


def ensure() -> None:
    """Idempotent: put sql_agent/ on sys.path, apply the agent's env long enough
    for its config module to load, then hand the process env back untouched."""
    global _done
    if _done:
        return

    if not os.path.isdir(SQL_AGENT_ROOT):
        raise RuntimeError(
            f"SQL agent not found at {SQL_AGENT_ROOT} — the chatbot's DB-query "
            "path needs that checkout present."
        )

    # ── .env files, in precedence order ──────────────────────────────────────
    # 1. The chatbot's own .env — read into a LOCAL dict via dotenv_values(),
    #    never written into the real process environment. This module only
    #    ever needs a handful of keys from it (ORACLE_*, OLLAMA_BASE_URL,
    #    SQL_*, below); a plain load_dotenv(override=False) used to sit here
    #    instead, and it silently set EVERY OTHER key in that file too —
    #    REQUIRE_AUTH, AUTHORIZATION_ENABLED, CORS_ORIGINS, etc. — for the
    #    rest of the process, with no corresponding entry in _saved_env to
    #    revert. Harmless in the real app (main.py already loads the same
    #    .env at startup, before anything else runs), but a real hazard for
    #    any test process where this module's ensure() is the FIRST thing to
    #    touch .env at all: it would permanently flip those flags for every
    #    test that runs afterward in the same process, regardless of module.
    #    (Confirmed directly: a test exercising this module's embedding path
    #    made REQUIRE_AUTH visible to unrelated backend.agent tests later in
    #    the same pytest run, which had never observed a "true" value before
    #    because nothing upstream of them had loaded .env yet.)
    chatbot_env: dict = {}
    try:
        from dotenv import dotenv_values
        chatbot_env = {k: v for k, v in dotenv_values(os.path.join(PROJECT_ROOT, ".env")).items() if v is not None}
    except Exception as exc:                      # pragma: no cover - optional
        logger.debug("[SQL_AGENT] .env load skipped: %s", exc)

    def _chatbot_env(name: str) -> str | None:
        """Real environment wins; the chatbot .env file is only a fallback —
        same precedence as everywhere else in this module, and still never
        writes to os.environ itself."""
        return os.environ.get(name) or chatbot_env.get(name)

    # 2. sql_agent/.env — the agent's OWN settings file, and authoritative for
    #    the keys it defines. It has to override, not defer, because the two
    #    projects independently use some of the same variable names: the
    #    chatbot's .env sets OLLAMA_MODEL to its error-explanation model
    #    (llama3.1), which is already in os.environ by the time we get here, so
    #    a non-overriding load could never let this file's OLLAMA_MODEL
    #    (SQLCoder) win. Any key absent here still falls back to the chatbot .env
    #    mapping further down, so this file is entirely optional — and DB
    #    credentials in particular are meant to stay in the chatbot .env only,
    #    under their ORACLE_* names, rather than be duplicated here.
    agent_env: dict = {}
    agent_env_path = os.path.join(SQL_AGENT_ROOT, ".env")
    if os.path.isfile(agent_env_path):
        try:
            from dotenv import dotenv_values
            agent_env = {k: v for k, v in dotenv_values(agent_env_path).items() if v is not None}
        except Exception as exc:                  # pragma: no cover - optional
            logger.warning("[SQL_AGENT] Could not read %s: %s", agent_env_path, exc)

        for key, value in agent_env.items():
            _setenv(key, value, override=True)

    # Real env / sql_agent/.env (already applied above via _setenv, so already
    # in os.environ) still wins; the chatbot .env dict is consulted only as a
    # fallback, and only through this function — never written to os.environ.
    env = _chatbot_env

    # ── Retrieval artefacts + DDL ────────────────────────────────────────────
    # The agent's own EMBEDDING_DIR values are relative to ITS repo root, but the
    # chatbot process runs from the project root — so resolve a relative value
    # (from sql_agent/.env or a real env var) against SQL_AGENT_ROOT rather than
    # letting it silently resolve to a nonexistent directory and degrade every
    # answer with no error.
    configured_dir = (env("EMBEDDING_DIR") or "").strip()
    if configured_dir:
        if not os.path.isabs(configured_dir):
            _setenv("EMBEDDING_DIR", os.path.join(SQL_AGENT_ROOT, configured_dir), override=True)
    else:
        _setenv("EMBEDDING_DIR", EMBEDDING_DIR, override=False)

    # ── Embedding model ──────────────────────────────────────────────────────
    _setenv("EMBED_MODEL", env("SQL_EMBED_MODEL"), override=False)
    _setenv("QUERY_PREFIX", env("SQL_QUERY_PREFIX"), override=False)

    # ── Ollama ───────────────────────────────────────────────────────────────
    # Only consulted when sql_agent/.env did not set these itself. SQL_OLLAMA_MODEL
    # still overrides the chatbot's OLLAMA_MODEL for the same reason described
    # above — the inherited value would be the error-explanation model.
    base = (env("OLLAMA_BASE_URL") or "").rstrip("/")
    if base:
        _setenv("OLLAMA_URL", f"{base}/api/generate", override=False)
    if "OLLAMA_MODEL" not in agent_env:
        _setenv("OLLAMA_MODEL", env("SQL_OLLAMA_MODEL"), override=True)

    # Selector is a separate INSTRUCT model (SQLCoder cannot follow prose). The
    # agent's default (qwen2.5-coder:7b) is not necessarily served by this
    # deployment's Ollama, so fall back to the instruct model this project
    # already pulls for intent extraction.
    _setenv(
        "SELECTOR_MODEL",
        env("SQL_SELECTOR_MODEL") or env("OLLAMA_EXTRACT_MODEL"),
        override=False,
    )

    # ── Oracle ───────────────────────────────────────────────────────────────
    # Single source of truth is the chatbot's .env, under ORACLE_*. Mapped here
    # so the credentials are not duplicated into sql_agent/.env; if that file
    # does define DB_* itself, those values were already applied above and these
    # non-overriding calls leave them alone.
    _setenv("DB_HOST", env("ORACLE_HOST"), override=False)
    _setenv("DB_PORT", env("ORACLE_PORT"), override=False)
    _setenv("DB_SERVICE", env("ORACLE_SERVICE"), override=False)
    _setenv("DB_USER", env("ORACLE_USER"), override=False)
    _setenv("DB_PASSWORD", env("ORACLE_PASSWORD"), override=False)
    _setenv("DB_MAX_ROWS", env("ORACLE_MAX_ROWS"), override=False)

    # ORACLE_DSN ("host:port/service") is the older single-line form; only used
    # to fill in whichever of the three parts above is missing.
    if not os.environ.get("DB_HOST"):
        dsn = env("ORACLE_DSN") or ""
        try:
            host_port, service = dsn.split("/", 1)
            host, port = host_port.rsplit(":", 1)
            _setenv("DB_HOST", host.strip(), override=False)
            _setenv("DB_PORT", port.strip(), override=False)
            _setenv("DB_SERVICE", service.strip(), override=False)
        except ValueError:
            pass

    # ── sys.path ─────────────────────────────────────────────────────────────
    # Appended, not prepended: this project's own packages must keep winning if
    # a name ever collides.
    if SQL_AGENT_ROOT not in sys.path:
        sys.path.append(SQL_AGENT_ROOT)

    # ── Load the agent's config, then hand the process env back ──────────────
    # Imported HERE, explicitly, rather than left to whichever shim gets imported
    # first: src.config snapshots os.environ at import time, so the read has to
    # happen while the agent's values are in place and before _restore_env().
    embedding_dir = os.environ.get("EMBEDDING_DIR")
    sql_model = os.environ.get("OLLAMA_MODEL")
    selector_model = os.environ.get("SELECTOR_MODEL")
    try:
        import src.config  # noqa: F401
    finally:
        _restore_env()

    _done = True
    logger.info(
        "[SQL_AGENT] bootstrapped root=%s embedding_dir=%s model=%s selector=%s",
        SQL_AGENT_ROOT, embedding_dir, sql_model, selector_model,
    )
