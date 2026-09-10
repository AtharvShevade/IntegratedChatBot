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


def compare_summary_translation_model() -> str:
    """Model override for /compare-summary's AI-narrative translation ONLY.

    Benchmarked against qwen3:14b (translation_model()'s default) on realistic
    comparison-analysis text: qwen3:14b reliably exceeded even a 180s budget on
    the shared proxy, while aya-expanse:8b finished in 81-157s with every
    [[E#]] placeholder preserved. Every OTHER translation path (/chat,
    /guided, ...) keeps calling translation_model() unchanged -- this is a
    single endpoint's override, not a global model swap.
    """
    return os.getenv("COMPARE_SUMMARY_TRANSLATION_MODEL", "aya-expanse:8b")


def compare_execute_translation_timeout() -> float:
    """Dedicated timeout for /compare-execute's outbound translation ONLY.

    /compare-execute can return a much larger payload than /chat or /guided --
    a full comparison card's rendered prose plus its error_details[] cards --
    and it inherited the general TRANSLATION_TIMEOUT (150s) purely because it
    called translate_outbound() with no override. Measured in production
    logs: this response (~4,000 chars, ~50 protected entities) reliably hit
    ReadTimeout at ~150s on aya-expanse:8b, in both French and Hindi, while
    the comparison computation itself completed in 3s. This mirrors
    COMPARE_SUMMARY_TRANSLATION_TIMEOUT's reasoning exactly: a bigger prose
    payload gets its own longer budget rather than raising the general one,
    which would also slow down every /chat failure-detection timeout.
    """
    try:
        return float(os.getenv("COMPARE_EXECUTE_TRANSLATION_TIMEOUT", "240"))
    except ValueError:
        return 240.0


def error_explanation_translation_timeout() -> float:
    """Dedicated timeout for the batched error-explanation translation calls
    used by /explain-category (and any other endpoint carrying error_details).

    A batch call carries the combined prose of up to
    error_explanation_translation_batch_size() whole error cards, so it is
    larger than a single ordinary field and gets more time, same reasoning as
    compare_execute_translation_timeout().
    """
    try:
        return float(os.getenv("ERROR_EXPLANATION_TRANSLATION_TIMEOUT", "180"))
    except ValueError:
        return 180.0


def error_explanation_translation_batch_size() -> int:
    """How many COMPLETE error-explanation objects (error_details[] entries)
    are joined into one translation call.

    Previously every prose fragment inside every error card (heading, text,
    each bullet, each locator label) was dispatched as its own model call,
    bounded only by the global TRANSLATION_CONCURRENCY semaphore -- a report
    with several errors could fan out into dozens of small calls. Grouping
    whole error objects into batches of a few cuts the call count sharply
    while keeping each call's payload a bounded, predictable size. Minimum 1.
    """
    try:
        return max(1, int(os.getenv("ERROR_EXPLANATION_TRANSLATION_BATCH_SIZE", "3")))
    except ValueError:
        return 3


def compare_summary_translation_base_url() -> str:
    """Where compare_summary_translation_model() is served.

    Falls back to translation_base_url() (TRANSLATION_BASE_URL / OLLAMA_BASE_URL)
    if unset. Set this explicitly if aya-expanse:8b is not pulled on whatever
    host/proxy qwen3:14b uses -- it was benchmarked against a LOCAL Ollama
    instance, not the shared remote proxy.
    """
    explicit = os.getenv("COMPARE_SUMMARY_TRANSLATION_BASE_URL", "").strip()
    return explicit.rstrip("/") if explicit else translation_base_url()


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
        "compare_execute_timeout": compare_execute_translation_timeout(),
        "error_explanation_timeout": error_explanation_translation_timeout(),
        "error_explanation_batch_size": error_explanation_translation_batch_size(),
    }
