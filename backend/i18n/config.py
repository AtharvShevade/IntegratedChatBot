"""Configuration for the multilingual translation boundary.

Follows the repo's existing convention (backend/services/llm_service.py:21-35,
backend/config.py): plain os.getenv with a literal default, *_ENABLED booleans.

One deliberate deviation: every value is read PER CALL rather than frozen at
import time the way llm_service.py:21 freezes OLLAMA_BASE_URL. Two reasons.

  1. TRANSLATION_MODEL is the single knob the Qwen-vs-Gemma comparison turns
     on. A frozen module constant would make swapping models a restart, and
     would make a monkeypatched test silently exercise the wrong model.
  2. MULTILINGUAL_ENABLED must be flippable as a kill switch. A frozen flag
     turns "disable the feature" into "redeploy".

Nothing here imports backend.* — the package must be importable before the
agent is, and must cost nothing when the feature is off.
"""
from __future__ import annotations

import os

# Languages the boundary will translate. Anything outside this set is treated
# as English (see boundary.normalize_lang) rather than rejected: the pipeline
# can still answer the question in English, and refusing a serviceable request
# is a worse failure than not localizing it.
_DEFAULT_LANGUAGES = "en,fr,ar,hi"

# Human-readable names for the prompt. The model is told "translate from
# {src_name} to {tgt_name}", so these strings are load-bearing, not cosmetic.
LANGUAGE_NAMES: dict[str, str] = {
    "en": "English",
    "fr": "French",
    "ar": "Arabic",
    "hi": "Hindi",
}

# Right-to-left scripts. Recorded on the response metadata so the frontend can
# set `dir="rtl"` without having to hardcode a language list of its own.
RTL_LANGUAGES: frozenset[str] = frozenset({"ar"})


def is_enabled() -> bool:
    """Master switch. False => the boundary is a no-op and no model is called."""
    return os.getenv("MULTILINGUAL_ENABLED", "false").lower() == "true"


def translation_model() -> str:
    """THE model seam. Switching Qwen for Gemma is this variable and nothing
    else -- same code, same prompt, same masking, same tests."""
    return os.getenv("TRANSLATION_MODEL", "qwen3:14b")


def translation_base_url() -> str:
    """Endpoint for the translation model.

    Blank/unset inherits OLLAMA_BASE_URL so a normal deployment needs no extra
    configuration. It is separable because the translation model does not have
    to live where the app's own models live -- e.g. a locally pulled candidate
    served beside a proxy-hosted extract model.
    """
    explicit = os.getenv("TRANSLATION_BASE_URL", "").strip()
    base = explicit or os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    return base.rstrip("/")


def translation_timeout() -> float:
    """Deliberately NOT OLLAMA_TIMEOUT (300s in this deployment's .env).

    This call sits on the user-facing /chat path. The same reasoning produced
    CHAT_FALLBACK_TIMEOUT at llm_service.py:33: a request a human is waiting on
    must fail fast rather than hang.
    """
    return float(os.getenv("TRANSLATION_TIMEOUT", "60"))


def translation_temperature() -> float:
    return float(os.getenv("TRANSLATION_TEMPERATURE", "0"))


def translation_num_predict() -> int:
    """-1 = unbounded. llm_service pins num_predict at 256 (llm_service.py:212),
    which silently truncates anything longer than a couple of sentences -- a
    truncated translation is indistinguishable from a bad one downstream."""
    return int(os.getenv("TRANSLATION_NUM_PREDICT", "-1"))


def translation_max_chars() -> int:
    """Budget, in characters, for what actually reaches the model.

    Applied PER FIELD and only to what the catalogue could not already
    resolve, so a large response is trimmed rather than abandoned: fields that
    do not fit keep their English text and the rest is still localized.
    """
    return int(os.getenv("TRANSLATION_MAX_CHARS", "4000"))


def translation_concurrency() -> int:
    """How many translation calls may be in flight at once.

    The proxy is shared and serves a few requests at a time, while the timeout
    runs per call from the moment it is issued. Dispatching every field at once
    therefore makes the queued calls time out on their own budget; admitting a
    few at a time is what keeps each one inside it. Minimum 1.
    """
    return max(1, int(os.getenv("TRANSLATION_CONCURRENCY", "4")))


def keep_alive() -> str:
    """Mirrors llm_service._KEEP_ALIVE. Without it every translation after a
    30-minute idle gap pays a 60-80s cold start."""
    return os.getenv("OLLAMA_KEEP_ALIVE", "30m")


def supported_languages() -> frozenset[str]:
    raw = os.getenv("SUPPORTED_LANGUAGES", _DEFAULT_LANGUAGES)
    return frozenset(part.strip().lower() for part in raw.split(",") if part.strip())


def language_name(lang: str) -> str:
    return LANGUAGE_NAMES.get(lang, lang)


def runtime_config() -> dict[str, object]:
    """Everything that could change a measurement, for logging and for stamping
    into a comparison run. An A/B pair that silently ran under different
    settings is worse than no result at all."""
    return {
        "enabled": is_enabled(),
        "model": translation_model(),
        "base_url": translation_base_url(),
        "timeout": translation_timeout(),
        "temperature": translation_temperature(),
        "num_predict": translation_num_predict(),
        "max_chars": translation_max_chars(),
        "concurrency": translation_concurrency(),
        "supported": sorted(supported_languages()),
    }
