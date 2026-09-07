"""Configuration for the multilingual evaluation harness.

Every knob is an environment variable so that swapping the model under test is
a config change, never a code change:

    EVAL_TRANSLATE_MODEL=gemma4:31b   python -m eval.multilingual.run_eval ...
    EVAL_TRANSLATE_MODEL=qwen3:30b-a3b python -m eval.multilingual.run_eval ...

Two of these are load-bearing and easy to get wrong:

  * REQUIRE_AUTH / AUTHORIZATION_ENABLED must be forced off *before*
    ``backend.agent`` is imported. ``decide()`` reads REQUIRE_AUTH per call
    (backend/agent/__init__.py:841) but auth_service freezes
    AUTHORIZATION_ENABLED at import time (backend/services/auth_service.py:55),
    and with the repo's real .env both are "true" -- so a harness that imports
    first and sets env second gets the canned "Authentication required."
    response for all 60 questions and scores a clean, meaningless zero.

  * BASE_REPO_PATH must point at a populated repo. Missing XML degrades to
    empty results rather than raising (backend/config.py:16-18), so the run
    still "succeeds" while every report lookup answers "No matching reports
    found" -- valid responses, useless signal.

apply_eval_env() handles both and must be called before importing backend.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env at import so EVERY entry point sees the real OLLAMA_BASE_URL, not
# just the ones that go through pipeline.bootstrap(). score_judge.py does not
# touch the pipeline, so without this it silently fell back to the
# 127.0.0.1:11434 default and every judge call 404'd -- producing a file full
# of errors rather than scores. Idempotent, so bootstrap() may still call it.
load_dotenv()

PACKAGE_DIR = Path(__file__).resolve().parent
DATASET_DIR = PACKAGE_DIR / "dataset"
RESULTS_DIR = PACKAGE_DIR / "results"
PROJECT_ROOT = PACKAGE_DIR.parent.parent

# Languages the harness knows how to drive. "en" is the baseline/self-check
# pseudo-language: it goes through the translator only in --self-check mode.
LANGUAGES = {
    "en": "English",
    "fr": "French",
    "ar": "Arabic",
    "hi": "Hindi",
}

# Right-to-left scripts, recorded on results so the report can flag rendering
# concerns that are invisible in a JSONL diff.
RTL_LANGUAGES = {"ar"}


def _env(name: str, default: str) -> str:
    return os.getenv(name, default)


def translate_model() -> str:
    return _env("EVAL_TRANSLATE_MODEL", "gemma4:31b")


def translate_timeout() -> float:
    # Deliberately not OLLAMA_CHAT_FALLBACK_TIMEOUT (12s). A 31B model
    # translating a long variance summary blows straight through that; see
    # translator.py for why llm_service._call_ollama is not reused.
    return float(_env("EVAL_TRANSLATE_TIMEOUT", "300"))


def translate_temperature() -> float:
    return float(_env("EVAL_TRANSLATE_TEMPERATURE", "0"))


def translate_num_predict() -> int:
    # -1 = unbounded. llm_service pins this at 256, which silently truncates
    # any translation longer than a couple of sentences.
    return int(_env("EVAL_TRANSLATE_NUM_PREDICT", "-1"))


def ollama_base_url() -> str:
    """Endpoint for the PIPELINE and the judge -- i.e. the app's real Ollama."""
    return _env("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")


def translate_base_url() -> str:
    """Endpoint for the TRANSLATION model only.

    Defaults to the pipeline's endpoint, so existing runs are unaffected. It is
    separable because the model under test does not have to live where the app's
    models live: the chatbot's own extract/chat models (qwen2.5:7b, llama3.1)
    are on the shared remote proxy, so pointing OLLAMA_BASE_URL at a local
    Ollama to test a locally-pulled translator would break the pipeline itself
    and invalidate every routing measurement.

    Note when comparing across models: a translator served from a dedicated
    local Ollama and one served from the shared proxy are NOT latency
    comparable. Accuracy still is -- it does not depend on where the model runs.
    """
    return _env("EVAL_TRANSLATE_BASE_URL", ollama_base_url()).rstrip("/")


def judge_model() -> str:
    # Judging with the model under test would be marking its own homework.
    # Default to a different family than the usual candidate set.
    return _env("EVAL_JUDGE_MODEL", "qwen2.5:14b")


def apply_eval_env() -> dict[str, str]:
    """Force the harness-local environment. Call BEFORE importing backend.*.

    Returns the overrides applied, so the runner can stamp them into the result
    file -- an A/B pair that silently ran under different auth settings is
    worse than no result at all.
    """
    overrides = {
        "REQUIRE_AUTH": "false",
        "AUTHORIZATION_ENABLED": "false",
    }
    for key, value in overrides.items():
        os.environ[key] = value
    return overrides


def run_config() -> dict[str, object]:
    """Everything that could change a number, stamped into every result file."""
    return {
        "translate_model": translate_model(),
        "translate_temperature": translate_temperature(),
        "translate_num_predict": translate_num_predict(),
        "translate_timeout": translate_timeout(),
        "judge_model": judge_model(),
        "ollama_base_url": ollama_base_url(),
        "app_version": os.getenv("APP_VERSION", ""),
        "base_repo_path": os.getenv("BASE_REPO_PATH", ""),
        "ollama_extract_model": os.getenv("OLLAMA_EXTRACT_MODEL", ""),
        "ollama_model": os.getenv("OLLAMA_MODEL", ""),
        "require_auth": os.getenv("REQUIRE_AUTH", ""),
        "authorization_enabled": os.getenv("AUTHORIZATION_ENABLED", ""),
    }
