"""L-16: /feedback hardening.

/feedback has no object-level data access (it only appends a quality-signal
record — see submit_feedback's docstring in main.py for why it is
deliberately NOT gated behind REQUIRE_AUTH/login_id like /chat or
/download-file). Its abuse surface -- unauthenticated, high-volume,
unbounded log growth -- is addressed instead by:
  1. rate limiting (added to _RATE_LIMITED_PATHS),
  2. FeedbackRequest's existing per-field max_length validation, and
  3. log_feedback()'s new size-based rotation of feedback.jsonl.
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from backend import main as main_module
from backend.utils import intent_log


@pytest.fixture
def client():
    return TestClient(main_module.app)


@pytest.fixture(autouse=True)
def _reset_limiter():
    main_module.rate_limit.limiter.reset()
    yield
    main_module.rate_limit.limiter.reset()


class TestValidFeedbackStillWorks:
    def test_minimal_valid_feedback_is_accepted(self, client):
        res = client.post("/feedback", json={"rating": "up"})
        assert res.status_code == 200
        assert res.json() == {"ok": True}

    def test_full_valid_feedback_is_accepted(self, client):
        res = client.post("/feedback", json={
            "rating": "down", "query": "who owns this report?",
            "intent": "report_owner", "result_type": "db_qa_result",
            "session_id": "abc123",
        })
        assert res.status_code == 200


class TestMalformedBodyRejected:
    def test_invalid_rating_value_is_rejected(self, client):
        res = client.post("/feedback", json={"rating": "sideways"})
        assert res.status_code == 422

    def test_missing_rating_is_rejected(self, client):
        res = client.post("/feedback", json={})
        assert res.status_code == 422

    def test_oversized_query_field_is_rejected(self, client):
        res = client.post("/feedback", json={"rating": "up", "query": "x" * 3000})
        assert res.status_code == 422

    def test_oversized_session_id_is_rejected(self, client):
        res = client.post("/feedback", json={"rating": "up", "session_id": "x" * 200})
        assert res.status_code == 422


class TestNoAuthRequiredByDesign:
    """/feedback intentionally carries no login_id/REQUIRE_AUTH gate (see
    docstring) -- this is a documented decision, not an oversight. This test
    pins that decision so a future change to it is deliberate, not silent."""

    def test_unauthenticated_request_still_succeeds(self, client, monkeypatch):
        monkeypatch.setenv("REQUIRE_AUTH", "true")
        res = client.post("/feedback", json={"rating": "up"})
        assert res.status_code == 200


class TestRateLimiting:
    def test_feedback_is_in_the_rate_limited_path_set(self):
        assert "/feedback" in main_module._RATE_LIMITED_PATHS

    def test_exceeding_limit_returns_429(self, client, monkeypatch):
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
        monkeypatch.setenv("RATE_LIMIT_MAX_REQUESTS", "2")
        monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")

        r1 = client.post("/feedback", json={"rating": "up"})
        r2 = client.post("/feedback", json={"rating": "up"})
        r3 = client.post("/feedback", json={"rating": "up"})

        assert r1.status_code != 429
        assert r2.status_code != 429
        assert r3.status_code == 429
        assert int(r3.headers["Retry-After"]) >= 1

    def test_disabled_by_default(self, client, monkeypatch):
        monkeypatch.delenv("RATE_LIMIT_ENABLED", raising=False)
        for _ in range(10):
            res = client.post("/feedback", json={"rating": "up"})
            assert res.status_code == 200


class TestFeedbackLogRotation:
    def test_log_rotates_when_oversized(self, tmp_path, monkeypatch):
        log_path = tmp_path / "feedback.jsonl"
        log_path.write_bytes(b"x" * 1000)
        monkeypatch.setattr(intent_log, "FEEDBACK_LOG_PATH", str(log_path))
        monkeypatch.setattr(intent_log, "FEEDBACK_LOG_MAX_BYTES", 500)

        intent_log.log_feedback(rating="up")

        rotated = log_path.with_suffix(".jsonl.1")
        assert rotated.exists()
        assert rotated.read_bytes() == b"x" * 1000
        # the new record was written to a fresh (small) file, not appended
        # onto the rotated-out 1000 bytes
        new_content = log_path.read_text(encoding="utf-8")
        assert json.loads(new_content.strip())["rating"] == "up"

    def test_log_does_not_rotate_when_under_threshold(self, tmp_path, monkeypatch):
        log_path = tmp_path / "feedback.jsonl"
        log_path.write_bytes(b"x" * 100)
        monkeypatch.setattr(intent_log, "FEEDBACK_LOG_PATH", str(log_path))
        monkeypatch.setattr(intent_log, "FEEDBACK_LOG_MAX_BYTES", 500)

        intent_log.log_feedback(rating="up")

        rotated = log_path.with_suffix(".jsonl.1")
        assert not rotated.exists()
        content = log_path.read_text(encoding="utf-8")
        assert content.startswith("x" * 100)

    def test_log_feedback_works_when_file_does_not_exist_yet(self, tmp_path, monkeypatch):
        log_path = tmp_path / "feedback.jsonl"
        monkeypatch.setattr(intent_log, "FEEDBACK_LOG_PATH", str(log_path))
        monkeypatch.setattr(intent_log, "FEEDBACK_LOG_MAX_BYTES", 500)

        intent_log.log_feedback(rating="down")

        assert log_path.exists()
        assert json.loads(log_path.read_text(encoding="utf-8").strip())["rating"] == "down"
