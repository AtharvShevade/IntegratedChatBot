"""Tests for /speech-to-text and the STT client seam.

No network. Every test drives StubSttClient, which is itself the point:
STT_BASE_URL is the only network seam, so nothing else in backend/stt can
reach out on its own. Mirrors the IdentityTranslator convention in
test_i18n_boundary.py.
"""
from __future__ import annotations

import asyncio
import io
import threading

import pytest
from fastapi import UploadFile
from fastapi.testclient import TestClient

from backend import main as main_module
from backend.stt import config as stt_config
from backend.stt import vocabulary
from backend.stt.client import StubSttClient, WhisperHttpClient


@pytest.fixture(autouse=True)
def _enabled(monkeypatch):
    monkeypatch.setenv("STT_ENABLED", "true")
    monkeypatch.setenv("STT_LANGUAGE_MODE", "ui")
    monkeypatch.setenv("STT_LANGUAGES", "en,fr,ar,hi")
    monkeypatch.setenv("STT_VOCABULARY_ENABLED", "false")


@pytest.fixture
def client():
    return TestClient(main_module.app)


def _post(client, stub, *, lang="en", data=b"RIFFfake", filename="recording.webm"):
    """Drive the endpoint with a stub client injected at the seam."""
    import backend.stt as stt_pkg
    original = stt_pkg.get_client
    main_original = main_module.stt.get_client
    stt_pkg.get_client = lambda: stub
    main_module.stt.get_client = lambda: stub
    try:
        return client.post(
            "/speech-to-text",
            files={"file": (filename, io.BytesIO(data), "audio/webm")},
            data={"lang": lang},
        )
    finally:
        stt_pkg.get_client = original
        main_module.stt.get_client = main_original


# ---------------------------------------------------------------------------
# A. The happy path and language propagation
# ---------------------------------------------------------------------------

def test_transcript_is_returned(client):
    stub = StubSttClient(text="what is the status of CIMS_ROR")
    res = _post(client, stub)
    assert res.status_code == 200
    assert res.json()["transcript"] == "what is the status of CIMS_ROR"


@pytest.mark.parametrize("lang", ["en", "fr", "ar", "hi"])
def test_selected_language_reaches_the_client(client, lang):
    """Including English. STT has no 'leave it alone' default the way
    translation does -- it must be told what is being spoken."""
    stub = StubSttClient()
    res = _post(client, stub, lang=lang)
    assert res.status_code == 200
    assert stub.calls[0]["lang"] == lang


def test_task_is_always_transcribe(client):
    """The whole multilingual design depends on STT NOT translating: the text
    pipeline expects the user's own language."""
    stub = StubSttClient()
    _post(client, stub, lang="hi")
    assert stub.calls[0]["task"] == "transcribe"


def test_unsupported_language_falls_back_to_detection(client):
    stub = StubSttClient()
    _post(client, stub, lang="de")
    assert stub.calls[0]["lang"] is None, "unknown language must not be forced"


def test_auto_mode_never_forces_a_language(client, monkeypatch):
    monkeypatch.setenv("STT_LANGUAGE_MODE", "auto")
    stub = StubSttClient()
    _post(client, stub, lang="fr")
    assert stub.calls[0]["lang"] is None


def test_filename_is_forwarded(client):
    """The service validates by EXTENSION -- measured: a .txt upload is
    rejected with the allowed list -- so the name is not cosmetic."""
    stub = StubSttClient()
    _post(client, stub, filename="recording.webm")
    assert stub.calls[0]["filename"] == "recording.webm"


# ---------------------------------------------------------------------------
# B. Failure handling -- a failed transcription has nothing to degrade to
# ---------------------------------------------------------------------------

def test_empty_upload_is_rejected(client):
    stub = StubSttClient()
    res = _post(client, stub, data=b"")
    assert res.status_code == 400
    assert stub.calls == [], "an empty upload must not reach the service"


def test_oversize_upload_is_rejected(client, monkeypatch):
    monkeypatch.setenv("STT_MAX_BYTES", "100")
    stub = StubSttClient()
    res = _post(client, stub, data=b"x" * 500)
    assert res.status_code == 413
    assert stub.calls == [], "an oversize upload must not reach the service"


def test_service_failure_becomes_a_clean_503(client):
    stub = StubSttClient(ok=False, error="timeout")
    res = _post(client, stub)
    assert res.status_code == 503
    body = res.json()
    assert "detail" in body, "frontend _err() reads .detail"
    assert "timeout" not in body["detail"].lower(), "no internals in a user message"


def test_disabled_short_circuits(client, monkeypatch):
    monkeypatch.setenv("STT_ENABLED", "false")
    stub = StubSttClient()
    res = _post(client, stub)
    assert res.status_code == 503
    assert stub.calls == [], "disabled must not call the service"


def test_empty_transcript_is_not_an_error(client):
    """Silence is a legitimate outcome; the frontend shows voice.notHeard."""
    stub = StubSttClient(text="")
    res = _post(client, stub)
    assert res.status_code == 200
    assert res.json()["transcript"] == ""


# ---------------------------------------------------------------------------
# C. Vocabulary hint -- off until measured
# ---------------------------------------------------------------------------

def test_vocabulary_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("STT_VOCABULARY_ENABLED", raising=False)
    assert vocabulary.initial_prompt() is None


def test_vocabulary_when_enabled_is_short_and_carries_domain_terms(monkeypatch):
    monkeypatch.setenv("STT_VOCABULARY_ENABLED", "true")
    prompt = vocabulary.initial_prompt()
    assert prompt and "CIMS_ROR" in prompt
    assert len(prompt) <= 240, "a long prompt eats decoder context"


def test_no_vocabulary_reaches_the_client_when_disabled(client):
    stub = StubSttClient()
    _post(client, stub)
    assert stub.calls[0]["initial_prompt"] is None


# ---------------------------------------------------------------------------
# D. The client itself
# ---------------------------------------------------------------------------

def test_client_reports_unreachable_rather_than_raising():
    """A dead service must degrade to ok=False, never propagate a raw error."""
    bad = WhisperHttpClient(url="http://127.0.0.1:9/transcribe", timeout_s=1.0)
    result = asyncio.run(bad.transcribe(b"x", "recording.webm", lang="fr"))
    assert result.ok is False
    assert result.text == ""
    assert result.error


def test_hints_can_be_switched_off():
    """A future gateway that rejects unknown multipart fields must be
    survivable by configuration, not a code change."""
    quiet = WhisperHttpClient(url="http://example.invalid", send_hints=False)
    assert quiet.send_hints is False


def test_config_defaults_are_sane(monkeypatch):
    for key in ("STT_BASE_URL", "STT_TIMEOUT", "STT_CONCURRENCY", "STT_MAX_SECONDS"):
        monkeypatch.delenv(key, raising=False)
    assert stt_config.transcribe_url().endswith("/transcribe")
    assert stt_config.concurrency() >= 1
    assert stt_config.max_seconds() > 0
    assert stt_config.supported_languages() == {"en", "fr", "ar", "hi"}


# ---------------------------------------------------------------------------
# E. Cancelling an in-flight transcription
#
# Transcription takes seconds, so the mic button stays live and becomes a stop
# control. Aborting the fetch stops the UI waiting, but the SERVICE keeps
# working unless it is told otherwise -- and it transcribes one clip at a
# time, so an abandoned request delays the next user. /stop must actually
# cancel the backend task.
# ---------------------------------------------------------------------------

class _JsonRequest:
    """Minimal stand-in for fastapi.Request: /stop only calls .json()."""

    def __init__(self, payload: dict) -> None:
        self._payload = payload

    async def json(self) -> dict:
        return self._payload


class SlowSttClient:
    """Blocks until cancelled, so /stop has something to interrupt."""

    name = "slow"

    def __init__(self) -> None:
        self.started = threading.Event()
        self.cancelled = False

    async def transcribe(self, audio, filename, lang=None, initial_prompt=None):
        from backend.stt.client import TranscriptionResult
        self.started.set()
        try:
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            self.cancelled = True
            raise
        return TranscriptionResult(text="too late", latency_ms=0.0, ok=True)


def test_stop_cancels_an_in_flight_transcription():
    """Driven with asyncio rather than TestClient: TestClient serialises every
    request through one portal, so a /stop issued WHILE a transcription is in
    flight deadlocks the test harness -- not the app. This exercises the same
    code path the HTTP route does (_run_cancellable + the /stop task lookup)."""
    stub = SlowSttClient()

    async def scenario():
        upload = UploadFile(filename="recording.webm", file=io.BytesIO(b"RIFFfake"))
        request_id = "stt-cancel-1"

        original = main_module.stt.get_client
        main_module.stt.get_client = lambda: stub
        try:
            call = asyncio.ensure_future(main_module.speech_to_text(
                file=upload, lang="en", request_id=request_id))

            # Wait for the transcription to be genuinely under way, otherwise
            # /stop would find nothing and the test would pass vacuously.
            for _ in range(100):
                if stub.started.is_set():
                    break
                await asyncio.sleep(0.05)
            assert stub.started.is_set(), "transcription never started"

            stopped = await main_module.stop_request(
                _JsonRequest({"request_id": request_id}))
            assert stopped["stopped"] is True, "/stop did not find the task"

            return await asyncio.wait_for(call, timeout=10)
        finally:
            main_module.stt.get_client = original

    body = asyncio.run(scenario())
    assert body["transcript"] == ""
    assert body.get("stopped") is True, "a user cancel is not an error"
    assert stub.cancelled, "the client coroutine was never actually cancelled"


def test_stop_on_an_unknown_request_is_harmless(client):
    """The frontend fires /stop best-effort; a late or duplicate call must not
    500."""
    response = client.post("/stop", json={"request_id": "never-existed"})
    assert response.status_code == 200
    assert response.json()["stopped"] is False


def test_request_id_is_optional(client):
    """Omitting it must still transcribe -- it only forfeits cancellation."""
    stub = StubSttClient(text="fine")
    res = _post(client, stub)
    assert res.status_code == 200
    assert res.json()["transcript"] == "fine"
