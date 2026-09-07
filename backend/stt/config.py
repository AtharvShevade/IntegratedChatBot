"""Configuration seam for speech-to-text.

One function per environment variable, read at CALL time rather than import
time, so a test can monkeypatch the environment without reimporting the
package. This mirrors backend/i18n/config.py exactly; the two are deliberately
the same shape because they solve the same problem -- a remote model service
whose address, model and timeouts must be changeable without a code edit.
"""
from __future__ import annotations

import os

# Read from OLLAMA_BASE_URL's neighbour by default: the Whisper service is
# published on the same host as the Ollama proxy.
_DEFAULT_BASE_URL = "http://3.109.51.228/whisper-api"


def is_enabled() -> bool:
    """False turns voice input off without removing the UI.

    The mic button stays visible and reports that transcription is unavailable,
    which is a better failure than a button that appears to work.
    """
    return os.getenv("STT_ENABLED", "true").strip().lower() in ("1", "true", "yes", "on")


def base_url() -> str:
    """Root of the Whisper service. No trailing slash."""
    return os.getenv("STT_BASE_URL", _DEFAULT_BASE_URL).strip().rstrip("/")


def transcribe_url() -> str:
    return f"{base_url()}/transcribe"


def health_url() -> str:
    return f"{base_url()}/health"


def timeout() -> float:
    """Seconds to wait for one transcription.

    MEASURED against the deployed service: ~14s for any clip up to 30s and
    ~23s for 60s, because the model is reloaded per request (~6-7s fixed) and
    runs unquantized (~8s per 30s window). 120 covers the worst case with
    headroom; it is NOT a target, and it should come down substantially once
    the service keeps the model resident.
    """
    return float(os.getenv("STT_TIMEOUT", "120"))


def max_seconds() -> int:
    """Longest recording accepted. Enforced in the browser too."""
    return int(os.getenv("STT_MAX_SECONDS", "60"))


def max_bytes() -> int:
    """Upload ceiling. 60s of webm/opus is ~120 KB; 10 MB is generous and
    still bounds a malicious or malfunctioning client."""
    return int(os.getenv("STT_MAX_BYTES", str(10 * 1024 * 1024)))


def language_mode() -> str:
    """'ui' sends the selected interface language, 'auto' lets Whisper detect.

    Defaults to 'ui': Whisper's detection is unreliable on short or noisy
    clips -- measured language_probability of 0.35-0.63 on non-speech -- while
    a user who selected French is overwhelmingly likely to be speaking French.
    """
    return os.getenv("STT_LANGUAGE_MODE", "ui").strip().lower()


def send_hints() -> bool:
    """Whether to send language / task / initial_prompt at all.

    MEASURED: the service deployed today declares only `file` and silently
    IGNORES extra form fields (sending language=hi still returned language=en,
    HTTP 200). Sending them is therefore harmless now and takes effect the
    moment the service is upgraded, so this defaults on -- but it can be
    switched off if a future gateway starts rejecting unknown fields.
    """
    return os.getenv("STT_SEND_HINTS", "true").strip().lower() in ("1", "true", "yes", "on")


def concurrency() -> int:
    """How many transcriptions this backend will have in flight at once.

    MEASURED: the service serializes -- two concurrent 1s clips took 13.6s and
    27.2s. Queueing here rather than at the service lets us answer a third
    caller immediately with 503 instead of leaving them to wait behind two
    unbounded requests. Same reasoning as TRANSLATION_CONCURRENCY.
    """
    return max(1, int(os.getenv("STT_CONCURRENCY", "2")))


def supported_languages() -> set[str]:
    """Languages the UI may ask for. Mirrors SUPPORTED_LANGUAGES in i18n."""
    raw = os.getenv("STT_LANGUAGES", "en,fr,ar,hi")
    return {code.strip().lower() for code in raw.split(",") if code.strip()}


def runtime_config() -> dict:
    """Logged once at startup, like i18n.runtime_config()."""
    return {
        "enabled": is_enabled(),
        "base_url": base_url(),
        "timeout": timeout(),
        "max_seconds": max_seconds(),
        "max_bytes": max_bytes(),
        "language_mode": language_mode(),
        "send_hints": send_hints(),
        "concurrency": concurrency(),
        "languages": sorted(supported_languages()),
    }
