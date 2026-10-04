"""M-03: the STT admission-control semaphore (`_stt_slots` in backend/main.py)
previously used `async with _stt_slots:`, which QUEUES a caller indefinitely
once the configured concurrency is exhausted -- directly contradicting its
own comment ("a third caller is told to retry instead of queueing
invisibly"). The fix checks `_stt_slots.locked()` first and returns 429
immediately instead of silently waiting.
"""
from __future__ import annotations

import asyncio
import io

import pytest
from fastapi.testclient import TestClient

from backend import main as main_module
from backend.stt.client import StubSttClient

client = TestClient(main_module.app)


@pytest.fixture(autouse=True)
def _enabled(monkeypatch):
    monkeypatch.setenv("STT_ENABLED", "true")
    monkeypatch.setenv("STT_LANGUAGE_MODE", "ui")
    monkeypatch.setenv("STT_LANGUAGES", "en,fr,ar,hi")
    monkeypatch.setenv("STT_VOCABULARY_ENABLED", "false")


def _post(stub):
    import backend.stt as stt_pkg
    original = stt_pkg.get_client
    main_original = main_module.stt.get_client
    stt_pkg.get_client = lambda: stub
    main_module.stt.get_client = lambda: stub
    try:
        return client.post(
            "/speech-to-text",
            files={"file": ("recording.webm", io.BytesIO(b"RIFFfake"), "audio/webm")},
            data={"lang": "en"},
        )
    finally:
        stt_pkg.get_client = original
        main_module.stt.get_client = main_original


class TestNormalRequestsStillWork:
    def test_single_request_within_limit_succeeds(self):
        stub = StubSttClient(text="hello")
        res = _post(stub)
        assert res.status_code == 200
        assert res.json()["transcript"] == "hello"

    def test_slot_is_released_after_a_request_completes(self):
        # Two SEQUENTIAL requests (not concurrent) must both succeed --
        # confirms the semaphore slot is actually released, not leaked.
        stub1 = StubSttClient(text="first")
        res1 = _post(stub1)
        assert res1.status_code == 200

        stub2 = StubSttClient(text="second")
        res2 = _post(stub2)
        assert res2.status_code == 200


class TestOverCapacityIsRejectedNotQueued:
    def test_exceeding_concurrency_returns_429_immediately(self, monkeypatch):
        # Simulate the semaphore already being fully exhausted by real
        # in-flight requests, without needing to actually race coroutines --
        # directly exercises the same `.locked()` check the endpoint uses.
        monkeypatch.setattr(
            main_module, "_stt_slots", asyncio.Semaphore(0)  # 0 free slots
        )
        stub = StubSttClient(text="should not be reached")
        res = _post(stub)
        assert res.status_code == 429
        assert "retry-after" in {k.lower() for k in res.headers.keys()}
        assert stub.calls == [], "an over-capacity request must never reach the STT service"

    def test_real_concurrency_exhaustion_rejects_the_extra_caller(self):
        """End-to-end proof using the REAL semaphore (STT_CONCURRENCY=2 by
        default in this environment's .env) and genuinely concurrent asyncio
        tasks, not just a locked() simulation."""
        import backend.stt as stt_pkg

        class _SlowStub:
            name = "slow-stub"

            def __init__(self):
                self.started = 0

            async def transcribe(self, audio, filename, lang=None, initial_prompt=None):
                from backend.stt.client import TranscriptionResult
                self.started += 1
                await asyncio.sleep(0.3)
                return TranscriptionResult(text="done", latency_ms=0.0, ok=True)

        stub = _SlowStub()
        original = stt_pkg.get_client
        main_original = main_module.stt.get_client
        stt_pkg.get_client = lambda: stub
        main_module.stt.get_client = lambda: stub

        concurrency = main_module.stt_config.concurrency()

        async def scenario():
            # Launch (concurrency + 1) genuinely concurrent requests directly
            # against the async endpoint function.
            from fastapi import UploadFile
            tasks = []
            for _ in range(concurrency + 1):
                upload = UploadFile(filename="recording.webm", file=io.BytesIO(b"RIFFfake"))
                tasks.append(asyncio.ensure_future(
                    main_module.speech_to_text(file=upload, lang="en", request_id=None)
                ))
                await asyncio.sleep(0)  # let each task start acquiring before the next launches
            results = []
            for t in tasks:
                try:
                    results.append(await t)
                except Exception as exc:
                    results.append(exc)
            return results

        try:
            results = asyncio.run(scenario())
        finally:
            stt_pkg.get_client = original
            main_module.stt.get_client = main_original

        from fastapi import HTTPException
        rejected = [r for r in results if isinstance(r, HTTPException) and r.status_code == 429]
        succeeded = [r for r in results if isinstance(r, dict)]
        assert len(rejected) >= 1, "at least one over-capacity caller must be rejected with 429"
        assert len(succeeded) == concurrency, f"exactly {concurrency} should have been admitted"
