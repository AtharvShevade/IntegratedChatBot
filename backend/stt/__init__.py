"""Speech-to-text: a thin client to the remote Whisper service.

STT is treated exactly like Ollama -- a model served over HTTP behind a
configurable base URL. Nothing in this package loads a model, imports torch, or
touches ffmpeg; the FastAPI host stays free of heavy local compute, which is
what it was before voice input existed.

    /speech-to-text  ->  SttClient  ->  {STT_BASE_URL}/transcribe

The chat pipeline is not involved. A transcript is delivered to the frontend,
which puts it in the input box; the user presses Send and the ordinary /chat
path runs on ordinary text.
"""
from backend.stt.client import (  # noqa: F401
    SttClient,
    TranscriptionResult,
    WhisperHttpClient,
    StubSttClient,
    get_client,
)
from backend.stt.config import is_enabled, runtime_config  # noqa: F401
