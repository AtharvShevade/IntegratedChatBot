"""M-24: /speech-to-text previously read the ENTIRE upload into memory
(``await file.read()``) before checking its size, had no content-type
allowlist, and forwarded the client-supplied filename as-is to the downstream
Whisper service.

``backend/main.py`` now: enforces the byte limit while reading
(``_read_upload_with_limit``, aborting as soon as the configured max is
exceeded instead of after the whole body is buffered); checks the upload's
content-type against ``_ALLOWED_AUDIO_CONTENT_TYPES`` before reading any
audio bytes; and replaces the client-supplied filename with a fixed,
server-controlled name via ``_safe_recording_filename`` (only a validated
extension survives, never the client's base name or any path component).
"""
from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient

from backend import main as main_module
from backend.main import _safe_recording_filename
from backend.stt.client import StubSttClient

client = TestClient(main_module.app)


@pytest.fixture(autouse=True)
def _enabled(monkeypatch):
    monkeypatch.setenv("STT_ENABLED", "true")
    monkeypatch.setenv("STT_LANGUAGE_MODE", "ui")
    monkeypatch.setenv("STT_LANGUAGES", "en,fr,ar,hi")
    monkeypatch.setenv("STT_VOCABULARY_ENABLED", "false")


def _post(stub, *, data=b"RIFFfake", filename="recording.webm", content_type="audio/webm"):
    import backend.stt as stt_pkg
    original = stt_pkg.get_client
    main_original = main_module.stt.get_client
    stt_pkg.get_client = lambda: stub
    main_module.stt.get_client = lambda: stub
    try:
        return client.post(
            "/speech-to-text",
            files={"file": (filename, io.BytesIO(data), content_type)},
            data={"lang": "en"},
        )
    finally:
        stt_pkg.get_client = original
        main_module.stt.get_client = main_original


class TestSafeFilenameHelper:
    def test_known_extension_is_preserved_on_fixed_base_name(self):
        assert _safe_recording_filename("recording.webm") == "recording.webm"
        assert _safe_recording_filename("myvoice.wav") == "recording.wav"
        assert _safe_recording_filename("clip.mp3") == "recording.mp3"

    def test_unknown_extension_falls_back_to_webm(self):
        assert _safe_recording_filename("payload.exe") == "recording.webm"
        assert _safe_recording_filename("notes.txt") == "recording.webm"

    def test_missing_filename_falls_back_to_webm(self):
        assert _safe_recording_filename(None) == "recording.webm"
        assert _safe_recording_filename("") == "recording.webm"

    def test_path_traversal_attempt_is_neutralised(self):
        # Only the extension ever survives -- no directory component, no
        # base name, from a malicious or accidental path-containing filename.
        assert _safe_recording_filename("../../etc/passwd") == "recording.webm"
        assert _safe_recording_filename("..\\..\\windows\\system32\\evil.wav") == "recording.wav"
        assert _safe_recording_filename("/etc/cron.d/evil.mp3") == "recording.mp3"


class TestEndToEndUploadHardening:
    def test_valid_supported_audio_is_accepted(self):
        stub = StubSttClient(text="hello world")
        res = _post(stub, content_type="audio/webm")
        assert res.status_code == 200
        assert res.json()["transcript"] == "hello world"
        # The filename actually forwarded downstream is the server-controlled
        # one, not whatever the client claimed.
        assert stub.calls[0]["filename"] == "recording.webm"

    def test_unsupported_mime_type_is_rejected(self):
        stub = StubSttClient()
        res = _post(stub, content_type="text/plain")
        assert res.status_code == 415
        assert stub.calls == [], "an unsupported content-type must never reach the service"

    def test_executable_content_type_is_rejected(self):
        stub = StubSttClient()
        res = _post(stub, content_type="application/x-msdownload", filename="virus.exe")
        assert res.status_code == 415
        assert stub.calls == []

    def test_file_exactly_at_limit_is_accepted(self, monkeypatch):
        monkeypatch.setenv("STT_MAX_BYTES", "100")
        stub = StubSttClient()
        res = _post(stub, data=b"x" * 100)
        assert res.status_code == 200
        assert stub.calls, "an upload exactly at the limit must still be transcribed"

    def test_file_over_limit_is_rejected_without_reaching_the_service(self, monkeypatch):
        monkeypatch.setenv("STT_MAX_BYTES", "100")
        stub = StubSttClient()
        res = _post(stub, data=b"x" * 101)
        assert res.status_code == 413
        assert stub.calls == [], "an oversize upload must never reach the service"

    def test_streaming_limit_aborts_before_reading_the_whole_body(self, monkeypatch):
        # Enforced during the read loop, not after -- a large payload sent
        # with a small limit must be rejected (not accepted only because the
        # whole thing was buffered first and then measured).
        monkeypatch.setenv("STT_MAX_BYTES", "1000")
        stub = StubSttClient()
        res = _post(stub, data=b"x" * (5 * 1024 * 1024))  # 5 MiB, far over the 1000-byte cap
        assert res.status_code == 413
        assert stub.calls == []

    def test_malicious_path_filename_never_reaches_the_service(self):
        stub = StubSttClient(text="ok")
        res = _post(stub, filename="../../../etc/passwd.wav")
        assert res.status_code == 200
        # Only a safe, fixed filename is ever forwarded -- never the raw
        # client-supplied path.
        assert stub.calls[0]["filename"] == "recording.wav"
        assert ".." not in stub.calls[0]["filename"]

    def test_empty_upload_is_still_rejected(self):
        stub = StubSttClient()
        res = _post(stub, data=b"")
        assert res.status_code == 400
        assert stub.calls == []

    def test_octet_stream_content_type_is_still_accepted(self):
        # Some browsers/tools send a generic content-type for a blob upload;
        # the extension-based downstream check is the real gate, so this must
        # not be rejected purely on a generic content-type.
        stub = StubSttClient(text="ok")
        res = _post(stub, content_type="application/octet-stream")
        assert res.status_code == 200
