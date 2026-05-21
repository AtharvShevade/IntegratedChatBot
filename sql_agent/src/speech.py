import os
import tempfile
import threading

import numpy as np
import requests
import sounddevice as sd
import soundfile as sf

from src.config import SARVAM_API_KEY

# ── Tunable constants ─────────────────────────────────────────────────────────
SAMPLE_RATE       = 16000    # Hz — Sarvam AI expects 16 kHz mono
MAX_DURATION      = 20 * 60  # 20-minute hard cap
CHUNK_SEC         = 0.5      # read audio in 0.5-second chunks
SILENCE_THRESHOLD = 0.010    # RMS below this → silence
SILENCE_SEC       = 2.5      # seconds of continuous silence → auto-stop

# Sarvam AI endpoint
# saaras:v2  → transcribe + translate to English (multilingual input)
_SARVAM_URL   = "https://api.sarvam.ai/speech-to-text-translate"
_SARVAM_MODEL = "saaras:v2.5"
# ──────────────────────────────────────────────────────────────────────────────


def listen_from_microphone():
    """
    Record from the microphone, then send audio to Sarvam AI
    speech-to-text-translate API which returns English text regardless
    of the spoken language (supports Indian + global languages).

    Stops when:
      - User presses Enter           (manual stop)
      - Silence lasts >= SILENCE_SEC  (auto-stop)
      - MAX_DURATION is reached

    Returns:
        (english_text: str | None, error: str | None)
    """
    if not SARVAM_API_KEY or SARVAM_API_KEY == "your_sarvam_api_key":
        return None, "SARVAM_API_KEY is not set in src/config.py"

    print("\n  [REC] Recording started.")
    print("        • Press ENTER to stop manually")
    print(f"        • Auto-stops after {SILENCE_SEC}s of silence")
    print(f"        • Hard cap: {MAX_DURATION // 60} minutes\n")

    stop_event = threading.Event()

    def _wait_for_enter():
        input()          # blocks until user presses Enter
        stop_event.set()

    enter_thread = threading.Thread(target=_wait_for_enter, daemon=True)
    enter_thread.start()

    chunk_size    = int(SAMPLE_RATE * CHUNK_SEC)
    max_chunks    = int(MAX_DURATION / CHUNK_SEC)
    silence_limit = int(SILENCE_SEC / CHUNK_SEC)

    chunks        = []
    silence_count = 0
    stop_reason   = "max duration reached"

    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32") as stream:
            for _ in range(max_chunks):
                if stop_event.is_set():
                    stop_reason = "manual stop"
                    break

                data, _ = stream.read(chunk_size)
                chunks.append(data.copy())

                rms = float(np.sqrt(np.mean(data ** 2)))
                if rms < SILENCE_THRESHOLD:
                    silence_count += 1
                    if silence_count >= silence_limit:
                        stop_reason = "silence detected"
                        break
                else:
                    silence_count = 0
    except Exception as exc:
        return None, f"Microphone error: {exc}"

    print(f"\n  [REC] Stopped — {stop_reason}.")

    if not chunks:
        return None, "No audio was recorded."

    audio_np = np.concatenate(chunks, axis=0).squeeze()

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        sf.write(tmp_path, audio_np, SAMPLE_RATE)

        print("  Sending to Sarvam AI (transcribe + translate to English)...")
        with open(tmp_path, "rb") as audio_file:
            response = requests.post(
                _SARVAM_URL,
                headers={"api-subscription-key": SARVAM_API_KEY},
                files={"file": ("audio.wav", audio_file, "audio/wav")},
                data={"model": _SARVAM_MODEL},
                timeout=60,
            )

        if response.status_code != 200:
            return None, f"Sarvam AI API error {response.status_code}: {response.text}"

        result = response.json()
        text = result.get("transcript", "").strip()

        if not text:
            return None, "No speech detected in the recording."
        return text, None

    except requests.exceptions.ConnectionError:
        return None, "Cannot reach Sarvam AI API. Check your internet connection."
    except requests.exceptions.Timeout:
        return None, "Sarvam AI API timed out (60s)."
    except Exception as exc:
        return None, f"Transcription error: {exc}"
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
