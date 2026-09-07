"""The one network seam for speech-to-text.

Mirrors backend/i18n/translator.py: a Protocol, one HTTP implementation, and a
stub the tests drive so nothing in the suite reaches the network.

    SttClient.transcribe(audio, filename, lang) -> TranscriptionResult

The client is deliberately FORWARD-COMPATIBLE with the service contract. The
deployed service declares only `file` and, as measured, silently ignores extra
multipart fields -- sending language=hi still came back language=en with HTTP
200. So language / task / initial_prompt are sent now, do nothing yet, and
start working the moment the service is upgraded, with no change here.

`task` is pinned to "transcribe" and is never configurable. Translation is the
job of backend/i18n; a Whisper deployment that translates would silently
produce English for a French speaker and defeat the entire text pipeline.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Protocol

import httpx

from backend.stt import config

logger = logging.getLogger(__name__)

# Never anything else. See the module docstring.
_TASK = "transcribe"


@dataclass
class TranscriptionResult:
    """One transcription call.

    ``ok=False`` means the caller must not present ``text`` as a transcript.
    Unlike the translation boundary there is no useful fallback -- a failed
    transcription has nothing to degrade to -- so the endpoint turns this into
    a user-facing error rather than inventing content.
    """

    text: str
    latency_ms: float
    ok: bool = True
    error: str | None = None
    language: str = ""
    language_probability: float = 0.0
    duration: float = 0.0
    model: str = ""

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "latency_ms": round(self.latency_ms, 1),
            "error": self.error,
            "language": self.language,
            "language_probability": round(self.language_probability, 3),
            "duration": round(self.duration, 2),
            "model": self.model,
        }


class SttClient(Protocol):
    """The one model seam. Implementations must be side-effect free."""

    name: str

    async def transcribe(
        self, audio: bytes, filename: str, lang: str | None = None,
        initial_prompt: str | None = None,
    ) -> TranscriptionResult: ...


class WhisperHttpClient:
    """Client for the Whisper FastAPI service.

    Every parameter defaults to its config function, read at construction, so a
    test can pin one without touching the environment.
    """

    name = "whisper-http"

    def __init__(
        self,
        url: str | None = None,
        timeout_s: float | None = None,
        send_hints: bool | None = None,
    ) -> None:
        self.url = url if url is not None else config.transcribe_url()
        self.timeout_s = timeout_s if timeout_s is not None else config.timeout()
        self.send_hints = send_hints if send_hints is not None else config.send_hints()

    async def transcribe(
        self, audio: bytes, filename: str, lang: str | None = None,
        initial_prompt: str | None = None,
    ) -> TranscriptionResult:
        started = time.perf_counter()

        def _elapsed() -> float:
            return (time.perf_counter() - started) * 1000.0

        # The service validates by FILENAME EXTENSION, not content type
        # (measured: a .txt upload returns 400 naming the allowed extensions),
        # so the name matters and is not cosmetic.
        files = {"file": (filename, audio, "application/octet-stream")}
        data: dict[str, str] = {}
        if self.send_hints:
            data["task"] = _TASK
            if lang:
                data["language"] = lang
            if initial_prompt:
                data["initial_prompt"] = initial_prompt

        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                response = await client.post(self.url, files=files, data=data)
        except httpx.TimeoutException as exc:
            logger.warning("[STT] timeout after %.0fms url=%s", _elapsed(), self.url)
            return TranscriptionResult(
                text="", latency_ms=_elapsed(), ok=False, error=f"timeout: {exc}",
            )
        except httpx.RequestError as exc:
            logger.warning("[STT] unreachable url=%s error=%s", self.url, exc)
            return TranscriptionResult(
                text="", latency_ms=_elapsed(), ok=False, error=f"unreachable: {exc}",
            )

        if response.status_code != 200:
            # The service reports problems as {"detail": "..."} -- the same
            # shape the frontend's _err() already understands.
            detail = ""
            try:
                detail = str(response.json().get("detail", ""))
            except Exception:
                detail = response.text[:200]
            logger.warning("[STT] HTTP %d detail=%r", response.status_code, detail)
            return TranscriptionResult(
                text="", latency_ms=_elapsed(), ok=False,
                error=f"http {response.status_code}: {detail}",
            )

        try:
            body = response.json()
        except ValueError as exc:
            return TranscriptionResult(
                text="", latency_ms=_elapsed(), ok=False, error=f"bad json: {exc}",
            )

        # duration / processing_ms / model are part of the EXTENDED contract and
        # are absent from the service as deployed; default rather than fail.
        return TranscriptionResult(
            text=(body.get("text") or "").strip(),
            latency_ms=_elapsed(),
            ok=True,
            language=(body.get("language") or "").strip(),
            language_probability=float(body.get("language_probability") or 0.0),
            duration=float(body.get("duration") or 0.0),
            model=(body.get("model") or "").strip(),
        )


class StubSttClient:
    """Returns a scripted transcript. Proves in tests that STT_BASE_URL is the
    only network seam -- nothing else in the package reaches out."""

    name = "stub"

    def __init__(self, text: str = "stub transcript", ok: bool = True,
                 error: str | None = None) -> None:
        self.text = text
        self._ok = ok
        self._error = error
        self.calls: list[dict] = []

    async def transcribe(
        self, audio: bytes, filename: str, lang: str | None = None,
        initial_prompt: str | None = None,
    ) -> TranscriptionResult:
        self.calls.append({
            "bytes": len(audio), "filename": filename, "lang": lang,
            "initial_prompt": initial_prompt, "task": _TASK,
        })
        return TranscriptionResult(
            text=self.text if self._ok else "",
            latency_ms=0.0, ok=self._ok, error=self._error,
            language=lang or "en", model="stub",
        )


def get_client() -> SttClient:
    """Build the client for one request from current configuration."""
    return WhisperHttpClient()
