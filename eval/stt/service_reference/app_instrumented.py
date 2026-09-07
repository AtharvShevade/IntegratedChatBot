"""Instrumented Whisper service — REFERENCE IMPLEMENTATION, NOT DEPLOYED.

Drop-in replacement for the current service, to be run on **port 8081** beside
the live one on 8080 so timings can be compared without taking voice input
down. Nothing in this repo deploys it; it is here to be reviewed and run by
whoever owns the service.

Its whole purpose is to answer one question with evidence rather than
inference: **where do the ~8 seconds of per-request overhead go?**

The current service reports only `text`, so every measurement we have is wall
clock from the client and cannot separate network, decode, encode and
generation. This version reports a `timings` block breaking one request into:

    request_ms      IIS -> app, multipart parse, bytes in hand
    save_ms         writing the temp file faster-whisper reads
    decode_ms       PyAV/ffmpeg: container -> 16kHz mono float32
    detect_ms       language detection (SUSPECTED to be the big one)
    transcribe_ms   model.transcribe() generator fully consumed
    response_ms     assembling and serialising the reply
    total_ms        everything the app can see

Run it, hit it with eval/stt/run_eval.py --base-url http://127.0.0.1:8081, and
the numbers say which optimisation is worth doing.

    python -m uvicorn app_instrumented:app --host 127.0.0.1 --port 8081

Environment (all optional, defaults match the live service):
    WHISPER_MODEL=large-v3-turbo   WHISPER_DEVICE=cpu        # or: large-v3, medium
    WHISPER_COMPUTE_TYPE=int8      WHISPER_CPU_THREADS=8
    WHISPER_BEAM_SIZE=5            WHISPER_VAD=false
"""
from __future__ import annotations

import logging
import os
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from faster_whisper import WhisperModel, decode_audio

from model_config import SUPPORTED_MODELS, resolve_model

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("whisper-api")

# Validated before the model loads, so a typo fails immediately with a
# message naming the fix, instead of several seconds later inside
# faster-whisper as a HuggingFace 401. Default is unchanged.
MODEL_SIZE = resolve_model()
DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
CPU_THREADS = int(os.getenv("WHISPER_CPU_THREADS", "8"))
BEAM_SIZE = int(os.getenv("WHISPER_BEAM_SIZE", "5"))
VAD_DEFAULT = os.getenv("WHISPER_VAD", "false").lower() in ("1", "true", "yes", "on")

ALLOWED = {".flac", ".m4a", ".mp3", ".ogg", ".wav", ".webm"}

# Loaded ONCE at import, as the live service does. Confirmed resident.
_t0 = time.perf_counter()
model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE,
                     cpu_threads=CPU_THREADS)
MODEL_LOAD_MS = (time.perf_counter() - _t0) * 1000.0
logger.info("model=%s device=%s compute=%s threads=%d loaded in %.0fms",
            MODEL_SIZE, DEVICE, COMPUTE_TYPE, CPU_THREADS, MODEL_LOAD_MS)

app = FastAPI(title="Whisper Speech-to-Text API (instrumented)", version="0.2.0")


class Timer:
    """Accumulates named phase timings for one request."""

    def __init__(self) -> None:
        self.started = time.perf_counter()
        self.phases: dict[str, float] = {}

    @contextmanager
    def phase(self, name: str):
        start = time.perf_counter()
        try:
            yield
        finally:
            self.phases[f"{name}_ms"] = round((time.perf_counter() - start) * 1000.0, 1)

    def total(self) -> dict:
        self.phases["total_ms"] = round((time.perf_counter() - self.started) * 1000.0, 1)
        return self.phases


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "model": MODEL_SIZE,
        "device": DEVICE,
        "compute_type": COMPUTE_TYPE,
        "cpu_threads": CPU_THREADS,
        "beam_size": BEAM_SIZE,
        "vad_default": VAD_DEFAULT,
        "model_load_ms": round(MODEL_LOAD_MS, 1),
        "supported_models": list(SUPPORTED_MODELS),
        "instrumented": True,
    }


@app.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    language: str | None = Form(None),
    task: str = Form("transcribe"),
    initial_prompt: str | None = Form(None),
    beam_size: int | None = Form(None),
    vad: bool | None = Form(None),
    temperature: float | None = Form(None),
) -> dict:
    timer = Timer()

    suffix = Path(file.filename or "audio.wav").suffix.lower()
    if suffix not in ALLOWED:
        raise HTTPException(400, f"Unsupported file type '{suffix}'. "
                                 f"Allowed: {sorted(ALLOWED)}")

    # ── 1. request: multipart parse + bytes in hand ──────────────────────────
    with timer.phase("request"):
        audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(400, "Empty audio file received.")

    # ── 2. save: the temp file faster-whisper reads ──────────────────────────
    with timer.phase("save"):
        handle = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        handle.write(audio_bytes)
        handle.close()
        temp_path = handle.name

    try:
        # ── 3. decode: container -> 16kHz mono float32 (PyAV) ────────────────
        # Done explicitly rather than letting transcribe() do it, so decoding
        # is measured separately instead of hiding inside transcribe_ms.
        with timer.phase("decode"):
            audio = decode_audio(temp_path, sampling_rate=16000)
        audio_seconds = len(audio) / 16000.0

        # ── 4a. language detection, measured ON ITS OWN ──────────────────────
        # THE PRIMARY SUSPECT. With language=None, faster-whisper must run the
        # encoder over the first 30s window purely to pick a language, before
        # transcription encodes it again. That is a whole extra encoder pass on
        # every request, and it is independent of how long the audio is --
        # which is exactly the shape of the ~8s fixed cost measured from the
        # client (5s and 30s audio both cost ~14s; a second 30s window adds
        # only ~6.5s).
        detected_language = language
        language_probability = 1.0 if language else 0.0
        if not language:
            with timer.phase("detect"):
                detected_language, language_probability, _ = model.detect_language(audio)
        else:
            timer.phases["detect_ms"] = 0.0

        # ── 4b. transcription ────────────────────────────────────────────────
        with timer.phase("transcribe"):
            segments, info = model.transcribe(
                audio,
                language=detected_language,
                task="transcribe",              # never "translate"
                beam_size=beam_size or BEAM_SIZE,
                initial_prompt=initial_prompt or None,
                vad_filter=VAD_DEFAULT if vad is None else vad,
                temperature=temperature if temperature is not None else 0.0,
                condition_on_previous_text=False,
            )
            # The generator is lazy: nothing is computed until it is consumed,
            # so this list() IS the inference and must be inside the timer.
            collected = list(segments)

        # ── 5. response ──────────────────────────────────────────────────────
        with timer.phase("response"):
            text = "".join(segment.text for segment in collected).strip()
            payload = {
                "text": text,
                "language": info.language,
                "language_probability": round(float(info.language_probability), 3),
                "duration": round(audio_seconds, 2),
                "model": MODEL_SIZE,
            }
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass

    timings = timer.total()
    payload["processing_ms"] = timings["total_ms"]
    payload["timings"] = timings
    payload["config"] = {
        "beam_size": beam_size or BEAM_SIZE,
        "vad": VAD_DEFAULT if vad is None else vad,
        "language_forced": bool(language),
        "cpu_threads": CPU_THREADS,
        "compute_type": COMPUTE_TYPE,
    }

    logger.info(
        "audio=%.1fs total=%.0fms | request=%.0f save=%.0f decode=%.0f "
        "detect=%.0f transcribe=%.0f response=%.0f | lang=%s forced=%s beam=%d",
        audio_seconds, timings["total_ms"], timings["request_ms"],
        timings["save_ms"], timings["decode_ms"], timings["detect_ms"],
        timings["transcribe_ms"], timings["response_ms"],
        info.language, bool(language), beam_size or BEAM_SIZE,
    )
    return payload
