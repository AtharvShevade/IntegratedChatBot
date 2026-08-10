"""Stop Generation: /stop must end an in-flight request cleanly.

Before this, the endpoints logged the stop and then re-raised CancelledError,
which escaped into ASGI: uvicorn logged "Exception in ASGI application" with a
full traceback and the client got no HTTP response at all — just a dropped
connection — for what is a completely normal user action.

The distinction these tests protect is that a CancelledError arriving at the
endpoint has two very different meanings (user pressed Stop vs server
shutdown / client disconnect) and only the first may be turned into a
response. Swallowing the second would break shutdown.

Async tests drive an inner coroutine via asyncio.run(), matching the rest of
backend/tests — pytest-asyncio is not installed or configured here.
"""
from __future__ import annotations

import asyncio

import pytest

from backend import main as main_mod
from backend.main import (
    RequestStopped,
    _inflight_tasks,
    _run_cancellable,
    _stopped_request_ids,
    _stopped_response,
)


@pytest.fixture(autouse=True)
def _clean_registries():
    _inflight_tasks.clear()
    _stopped_request_ids.clear()
    yield
    _inflight_tasks.clear()
    _stopped_request_ids.clear()


async def _slow(seconds: float = 30):
    await asyncio.sleep(seconds)
    return {"never": "reached"}


async def _quick():
    return {"ok": True}


class _Req:
    """Minimal stand-in for the Request object /stop reads its body from."""

    def __init__(self, request_id):
        self._body = {"request_id": request_id}

    async def json(self):
        return self._body


# ── the user-Stop path ───────────────────────────────────────────────────

def test_request_stopped_is_not_a_cancelled_error_subclass():
    """If it were, an `except asyncio.CancelledError` handler would also
    catch it — and would then be suppressing genuine cancellation."""
    assert not issubclass(RequestStopped, asyncio.CancelledError)


def test_stop_surfaces_as_request_stopped():
    async def _run():
        task = asyncio.ensure_future(_run_cancellable("req-1", _slow()))
        await asyncio.sleep(0.05)  # let _run_cancellable register the inner task

        assert await main_mod.stop_request(_Req("req-1")) == {"stopped": True}

        with pytest.raises(RequestStopped):
            await task

    asyncio.run(_run())


def test_chat_endpoint_returns_a_clean_response_when_stopped(monkeypatch):
    """End-to-end through the real /chat handler: a stopped request returns a
    ChatResponse rather than propagating anything into ASGI."""
    from backend.models import ChatRequest, ChatResponse

    async def _never_finishes(*_a, **_kw):
        await asyncio.sleep(30)

    monkeypatch.setattr(main_mod, "decide", _never_finishes)

    async def _run():
        req = ChatRequest(message="which roles can create users",
                          session_id="s-1", request_id="req-chat")
        task = asyncio.ensure_future(main_mod.chat(req))
        await asyncio.sleep(0.05)

        assert await main_mod.stop_request(_Req("req-chat")) == {"stopped": True}

        result = await task  # must NOT raise
        assert isinstance(result, ChatResponse)
        assert result.result_type == "stopped"
        assert result.response_text == "Request stopped."

    asyncio.run(_run())


def test_stopped_response_shape():
    r = _stopped_response()
    assert r.result_type == "stopped"
    assert r.response_text
    # Nothing downstream should mistake this for real data.
    assert r.db_found is False and r.db_records == [] and r.options == []


# ── everything that is NOT a user Stop must still propagate ──────────────

def test_outer_cancellation_still_propagates():
    """Server shutdown / client disconnect cancels the OUTER task. That must
    still surface as CancelledError — converting it would break shutdown."""
    async def _run():
        task = asyncio.ensure_future(_run_cancellable("req-2", _slow()))
        await asyncio.sleep(0.05)

        task.cancel()  # nothing was registered in _stopped_request_ids
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(_run())


def test_inner_cancellation_without_stop_is_not_reported_as_stopped():
    """Same guard from the other direction: the inner task dying by some
    other means is not a user Stop either."""
    async def _run():
        task = asyncio.ensure_future(_run_cancellable("req-3", _slow()))
        await asyncio.sleep(0.05)

        _inflight_tasks["req-3"].cancel()  # cancelled, but /stop never ran
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(_run())


# ── bookkeeping ──────────────────────────────────────────────────────────

def test_registries_are_cleaned_up_after_a_stop():
    async def _run():
        task = asyncio.ensure_future(_run_cancellable("req-4", _slow()))
        await asyncio.sleep(0.05)
        await main_mod.stop_request(_Req("req-4"))
        with pytest.raises(RequestStopped):
            await task

        assert "req-4" not in _inflight_tasks
        assert "req-4" not in _stopped_request_ids, "stale id would mis-flag a later request"

    asyncio.run(_run())


def test_successful_request_leaves_no_residue():
    async def _run():
        assert await _run_cancellable("req-5", _quick()) == {"ok": True}
        assert "req-5" not in _inflight_tasks
        assert "req-5" not in _stopped_request_ids

    asyncio.run(_run())


def test_stop_on_an_unknown_or_finished_request_is_a_no_op():
    async def _run():
        assert await main_mod.stop_request(_Req("no-such-id")) == {"stopped": False}
        assert await main_mod.stop_request(_Req(None)) == {"stopped": False}
        # A no-op stop must not leave an id behind that could mis-flag a reused id.
        assert _stopped_request_ids == set()

    asyncio.run(_run())


def test_request_without_a_request_id_still_runs():
    async def _run():
        assert await _run_cancellable(None, _quick()) == {"ok": True}

    asyncio.run(_run())
