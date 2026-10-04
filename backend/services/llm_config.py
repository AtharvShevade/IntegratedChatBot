"""L-02: single authoritative source for Ollama model-name configuration.

Before this module, OLLAMA_BASE_URL/OLLAMA_MODEL were each re-read from the
environment with their own hardcoded fallback default in several files
(services/llm_service.py, tools/error_llm.py, tools/formula_error_generic.py,
tools/report_lookup.py, tools/variance_explain.py, tools/xbrl_comparator.py),
and the fallbacks had drifted apart (llm_service.py defaulted OLLAMA_MODEL to
"phi3:mini" while every other call site defaulted the same env var to
"llama3.1:latest", matching .env.example). Centralizing here makes that
divergence structurally impossible going forward. Every one of these env vars
is explicitly set in this deployment's real .env already, so this change has
no effect on current runtime behavior -- it only fixes what a fresh checkout
with no .env would fall back to.

One function per env var, read at call time (same convention as
backend/stt/config.py and backend/i18n/config.py), so tests can monkeypatch
the environment without reimporting the module.

Does not cover backend/sql_agent/sqlcore/config.py's OLLAMA_MODEL -- that package
is deliberately self-contained (no backend.* imports) and resolves its OWN
model name via a separate env-var remapping documented in
backend/sql_agent/_bootstrap.py.
"""
from __future__ import annotations

import os


def base_url() -> str:
    """Root of the Ollama (or Ollama-compatible proxy) endpoint."""
    return os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")


def chat_model() -> str:
    """Conversational fallback model, and the model used by the
    error-explanation / formula-explanation call sites (they all read the
    same OLLAMA_MODEL env var historically)."""
    return os.getenv("OLLAMA_MODEL", "llama3.1:latest")


def extract_model() -> str:
    """Intent/entity extraction model."""
    return os.getenv("OLLAMA_EXTRACT_MODEL", "phi3:mini")


def compare_model() -> str:
    """Comparative-analysis / variance-explanation summary model."""
    return os.getenv("OLLAMA_COMPARE_MODEL", "llama3.1:latest")


# M-26: OLLAMA_TIMEOUT/OLLAMA_KEEP_ALIVE/OLLAMA_MAX_CONCURRENCY were each
# re-read with their own copy-pasted literal default in 6 separate files
# (services/llm_service.py, tools/error_llm.py, tools/formula_error_generic.py,
# tools/report_lookup.py twice, tools/xbrl_comparator.py, tools/variance_explain.py)
# -- all 7 call sites happened to agree on "180"/"30m"/"2" today, but nothing
# structurally prevented them from drifting apart the way OLLAMA_MODEL's
# defaults already had (see module docstring above). Same env var names and
# defaults as before -- this only removes the duplication, it does not
# change what an unset .env falls back to.

def request_timeout() -> float:
    """Request timeout (seconds) for a direct Ollama chat/summary call."""
    return float(os.getenv("OLLAMA_TIMEOUT", "180"))


def keep_alive() -> str:
    """Ollama `keep_alive` value, controlling how long a model stays loaded
    in memory between requests."""
    return os.getenv("OLLAMA_KEEP_ALIVE", "30m")


def max_concurrency() -> int:
    """Upper bound on simultaneous in-flight Ollama requests from this
    process (used to size a bounded ThreadPoolExecutor/semaphore)."""
    try:
        return max(1, int(os.getenv("OLLAMA_MAX_CONCURRENCY", "2")))
    except ValueError:
        return 2
