"""HTTP client for the STT service under test.

Deliberately INDEPENDENT of backend/stt/client.py. The harness must be able to
benchmark a service the backend has never heard of -- a second instance, a
colleague's laptop, a candidate build -- and it must not start passing or
failing because someone changed the app's client. Two small clients that can
disagree is the right shape here; a shared one would couple the measurement to
the thing being measured.

Synchronous on purpose: a benchmark that fires requests concurrently would
measure queueing, and this service is already known to serialize.
"""
from __future__ import annotations

import json
import math
import struct
import time
import wave
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from eval.stt import config


@dataclass
class SttResponse:
    """One /transcribe call, as measured from the client side."""

    ok: bool
    text: str = ""
    language: str = ""
    language_probability: float = 0.0
    # Wall clock at the client: network + queueing + inference.
    latency_ms: float = 0.0
    # Server-side inference time, IF the service reports it. Absent from the
    # contract as deployed, so it is usually None -- which is itself worth
    # recording, because without it network and compute cannot be separated.
    processing_ms: float | None = None
    duration: float | None = None
    model: str = ""
    status_code: int | None = None
    error: str | None = None
    raw: dict = field(default_factory=dict)


def health() -> dict:
    """Whatever /health reports. Used to stamp results and to cross-check that
    the model being benchmarked is the model that was configured."""
    try:
        response = httpx.get(config.health_url(), timeout=15.0)
        response.raise_for_status()
        return response.json()
    except Exception as exc:  # noqa: BLE001 - a probe must never abort a run
        return {"error": str(exc)}


def transcribe(audio: bytes, filename: str, lang: str | None = None,
               initial_prompt: str | None = None,
               url: str | None = None, timeout_s: float | None = None) -> SttResponse:
    """One transcription, timed at the client.

    The service validates by FILENAME EXTENSION (measured: a .txt upload is
    rejected with the allowed list), so ``filename`` is load-bearing.
    """
    target = url or config.transcribe_url()
    files = {"file": (filename, audio, "application/octet-stream")}
    data: dict[str, str] = {}
    if config.send_hints():
        data["task"] = "transcribe"          # never "translate"
        if lang:
            data["language"] = lang
        if initial_prompt:
            data["initial_prompt"] = initial_prompt

    started = time.perf_counter()
    try:
        response = httpx.post(target, files=files, data=data,
                              timeout=timeout_s or config.timeout())
    except Exception as exc:  # noqa: BLE001
        return SttResponse(ok=False, latency_ms=(time.perf_counter() - started) * 1000.0,
                           error=f"{type(exc).__name__}: {exc}")
    elapsed = (time.perf_counter() - started) * 1000.0

    if response.status_code != 200:
        detail = ""
        try:
            detail = str(response.json().get("detail", ""))
        except Exception:  # noqa: BLE001
            detail = response.text[:200]
        return SttResponse(ok=False, latency_ms=elapsed,
                           status_code=response.status_code, error=detail)

    try:
        body = response.json()
    except json.JSONDecodeError as exc:
        return SttResponse(ok=False, latency_ms=elapsed,
                           status_code=200, error=f"bad json: {exc}")

    return SttResponse(
        ok=True,
        text=(body.get("text") or "").strip(),
        language=(body.get("language") or "").strip(),
        language_probability=float(body.get("language_probability") or 0.0),
        latency_ms=elapsed,
        # Part of the EXTENDED contract; absent today.
        processing_ms=(float(body["processing_ms"]) if body.get("processing_ms") else None),
        duration=(float(body["duration"]) if body.get("duration") else None),
        model=(body.get("model") or "").strip(),
        status_code=200,
        raw=body,
    )


# ---------------------------------------------------------------------------
# Synthetic audio, for the latency sweep only
# ---------------------------------------------------------------------------

def make_tone_wav(seconds: float, path: Path, freq: int = 220,
                  sample_rate: int = 16000) -> Path:
    """A mono 16 kHz tone of a known length.

    For LATENCY ONLY, and the distinction matters. A tone contains no speech,
    so the decoder emits almost no tokens -- this measures the fixed
    per-request cost plus the encoder, not realistic decoding. That is exactly
    the right probe for the two questions the sweep asks (is there a fixed
    overhead, and does cost scale with Whisper's 30s windows), and exactly the
    wrong input for an accuracy number. Nothing here is ever scored for WER.

    16 kHz mono is Whisper's native rate, so no resampling is involved.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = int(sample_rate * seconds)
    with wave.open(str(path), "w") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(b"".join(
            struct.pack("<h", int(8000 * math.sin(2 * math.pi * freq * i / sample_rate)))
            for i in range(frames)
        ))
    return path


def wav_duration(path: Path) -> float | None:
    """Length of a WAV in seconds, or None for any other container.

    Only WAV is read here on purpose: parsing webm/ogg/m4a would mean ffmpeg or
    PyAV, and this harness deliberately has no media dependencies. For those
    formats the duration comes from the manifest, where the recordist put it.
    """
    try:
        with wave.open(str(path), "r") as handle:
            return handle.getnframes() / float(handle.getframerate())
    except Exception:  # noqa: BLE001
        return None
