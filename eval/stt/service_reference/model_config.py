"""Which Whisper model the service loads, and nothing else.

Split into its own module for one reason: importing app_instrumented triggers
`WhisperModel(...)` at import time, which downloads ~1.5 GB and takes minutes.
Validation has to be testable without that. Fifteen lines here buys a test
suite that runs in milliseconds.

Only the two models under benchmark are accepted. An allow-list rather than a
free-form string because the failure mode otherwise is bad: faster-whisper
treats an unknown name as a HuggingFace repo id, so `WHISPER_MODEL=medum`
does not fail fast -- it tries to download a repo that does not exist and dies
several seconds later inside a library, with a message about HTTP 401s that
says nothing about the typo.
"""
from __future__ import annotations

import os

# The benchmark set. large-v3-turbo is production; medium is the lighter
# candidate; large-v3 is turbo's parent -- same encoder, but a full 32-layer
# decoder instead of turbo's distilled 4-layer one, so it is slower per
# request but is the accuracy ceiling turbo was distilled from. Relevant to
# the Hindi/Arabic accuracy question turbo's distillation raised (see
# eval/stt/service_reference/README.md).
SUPPORTED_MODELS: tuple[str, ...] = ("large-v3-turbo", "large-v3", "medium")

# Absent or empty WHISPER_MODEL keeps today's behaviour exactly.
DEFAULT_MODEL = "large-v3-turbo"


class UnsupportedModelError(ValueError):
    """Raised at startup, before the model loads, for an unusable value."""


def resolve_model(value: str | None = None) -> str:
    """Return the model to load, or raise with a message that names the fix.

    ``value`` is read from WHISPER_MODEL when not passed, so a caller can test
    this without touching the environment.
    """
    raw = value if value is not None else os.getenv("WHISPER_MODEL", "")
    name = (raw or "").strip()
    if not name:
        return DEFAULT_MODEL
    if name not in SUPPORTED_MODELS:
        raise UnsupportedModelError(
            f"WHISPER_MODEL={name!r} is not supported. "
            f"Use one of: {', '.join(SUPPORTED_MODELS)}. "
            f"Omit the variable to get the default ({DEFAULT_MODEL})."
        )
    return name
