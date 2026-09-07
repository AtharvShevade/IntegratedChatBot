"""Configuration for the STT evaluation harness.

Every knob is an environment variable or a CLI flag so that swapping the model
under test is a config change, never a code edit -- the same rule that lets the
multilingual harness compare gemma4 against qwen3 without touching code:

    EVAL_STT_BASE_URL=http://localhost:9000  python -m eval.stt.run_eval --latency
    EVAL_STT_MODEL=large-v3  EVAL_STT_COMPUTE_TYPE=int8  python -m eval.stt.run_eval ...

The model/runtime/compute-type values are DESCRIPTIVE, not instructions: this
harness cannot change how the remote service is configured. They are stamped
into the results so that two result files can be told apart afterwards, which
is the whole point of a comparison harness. Whoever runs a benchmark is
responsible for setting them to match the service actually deployed --
``--verify-health`` cross-checks them against what /health reports.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env so the harness sees the same STT_BASE_URL the backend does.
# Idempotent, so entry points may call it again.
load_dotenv()

PACKAGE_DIR = Path(__file__).resolve().parent
DATASET_DIR = PACKAGE_DIR / "dataset"
AUDIO_DIR = DATASET_DIR / "audio"
RESULTS_DIR = PACKAGE_DIR / "results"
PROJECT_ROOT = PACKAGE_DIR.parent.parent

# Languages under test. Matches SUPPORTED_LANGUAGES in the app.
LANGUAGES = {"en": "English", "fr": "French", "ar": "Arabic", "hi": "Hindi"}

# Scripts, used by the translation-leak metric: a Devanagari or Arabic
# reference that comes back in Latin script is a leak, and that is decidable
# without a language model.
SCRIPTS = {"hi": "devanagari", "ar": "arabic", "en": "latin", "fr": "latin"}

# Conditions a clip may be recorded under. `silence` and `noise` are the
# hallucination probes: ANY non-empty transcript for these is a failure.
CONDITIONS = (
    "clean", "entity", "noisy", "quiet", "fast", "pause",
    "codeswitch", "silence", "mic_bump", "two_speakers", "long",
)
NON_SPEECH_CONDITIONS = ("silence", "noise")

# Latency sweep durations, in seconds. Chosen to expose Whisper's 30s window
# boundary: if 5s and 30s cost the same, the fixed per-request overhead
# dominates, and the second window's marginal cost isolates decode speed.
LATENCY_DURATIONS = (1, 5, 10, 15, 30, 60)
LATENCY_REPEATS = 3


def _env(name: str, default: str) -> str:
    return os.getenv(name, default)


def base_url() -> str:
    """Root of the service under test.

    Falls back to the app's own STT_BASE_URL so a benchmark run and the running
    backend cannot silently disagree about which service was measured.
    """
    return _env("EVAL_STT_BASE_URL",
                _env("STT_BASE_URL", "http://3.109.51.228/whisper-api")).rstrip("/")


def transcribe_url() -> str:
    return f"{base_url()}/transcribe"


def health_url() -> str:
    return f"{base_url()}/health"


def timeout() -> float:
    """Generous: the service measured at ~14-17s for short clips and ~23s for
    60s audio. A benchmark must not turn a slow answer into a missing one."""
    return float(_env("EVAL_STT_TIMEOUT", "300"))


def model() -> str:
    return _env("EVAL_STT_MODEL", "large-v3-turbo")


def runtime() -> str:
    """faster-whisper | transformers | whisper.cpp | unknown."""
    return _env("EVAL_STT_RUNTIME", "unknown")


def compute_type() -> str:
    """int8 | float16 | float32 | unknown."""
    return _env("EVAL_STT_COMPUTE_TYPE", "unknown")


def cpu_threads() -> str:
    return _env("EVAL_STT_CPU_THREADS", "unknown")


def send_hints() -> bool:
    """Send language / task / initial_prompt.

    MEASURED on the service deployed today: it declares only `file` and
    silently ignores extra multipart fields, so these are inert until the
    service is upgraded. Sending them anyway means the same harness measures
    the upgraded service without a code change.
    """
    return _env("EVAL_STT_SEND_HINTS", "true").strip().lower() in ("1", "true", "yes", "on")


def initial_prompt() -> str | None:
    """Optional vocabulary hint, for the A/B in Phase 6. Empty = not sent."""
    value = _env("EVAL_STT_INITIAL_PROMPT", "").strip()
    return value or None


def run_config() -> dict:
    """Stamped into every result file's _meta line.

    Same convention as eval/multilingual: without this, two result files are
    indistinguishable a week later and the comparison is worthless.
    """
    return {
        "base_url": base_url(),
        "model": model(),
        "runtime": runtime(),
        "compute_type": compute_type(),
        "cpu_threads": cpu_threads(),
        "send_hints": send_hints(),
        "initial_prompt": initial_prompt(),
        "timeout": timeout(),
    }


# ── Acceptance thresholds ────────────────────────────────────────────────────
# The gate for choosing a production STT configuration. Kept here, not in
# report.py, so a threshold change is visible in one obvious place.
ACCEPTANCE = {
    "wer_en_fr_pct":        {"target": 15.0, "cmp": "<=", "label": "EN/FR WER"},
    "cer_hi_ar_pct":        {"target": 15.0, "cmp": "<=", "label": "HI/AR CER"},
    "entity_preservation":  {"target": 95.0, "cmp": ">=", "label": "Entity Preservation"},
    "translation_leak_pct": {"target": 0.0,  "cmp": "<=", "label": "Translation leakage"},
    "hallucination_pct":    {"target": 0.0,  "cmp": "<=", "label": "Silence/noise hallucination"},
    "p95_5s_ms":            {"target": 3000.0, "cmp": "<=", "label": "p95 latency, 5s"},
    "p95_15s_ms":           {"target": 6000.0, "cmp": "<=", "label": "p95 latency, 15s"},
    "warm_rtf":             {"target": 0.5,  "cmp": "<=", "label": "Warm RTF"},
}
