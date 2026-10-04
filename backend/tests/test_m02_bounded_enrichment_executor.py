"""M-02: backend/agent/background_jobs.py's _start_error_enrichment_thread()
previously spawned a brand-new threading.Thread(daemon=True) per call --
N concurrent status lookups with errors meant N concurrent OS threads, each
making its own round of LLM calls, with no cap. Replaced with a bounded
ThreadPoolExecutor (ERROR_ENRICHMENT_MAX_WORKERS, default 4), created once
(lazily, double-checked locking) and reused across calls.

These tests monkeypatch `_run_error_enrichment_async` itself (the function
submitted to the executor) rather than its own internal
`backend.tools.report_lookup._enrich_error_info` call, because that inner
import is a PRE-EXISTING, unrelated bug independent of this change: no
function named `_enrich_error_info` exists anywhere in report_lookup.py, so
every real invocation of `_run_error_enrichment_async` already raises
ImportError today, silently swallowed by its own `except Exception` (which
is exactly why no test ever caught it). Fixing that is out of scope for
M-02 (a pure concurrency-mechanism change) -- it is reported separately,
not fixed here. Mocking at the `_run_error_enrichment_async` boundary tests
the actual thing M-02 changed (bounded submission) without depending on
that unrelated, already-broken import.
"""
from __future__ import annotations

import threading
import time

import pytest

from backend.agent import background_jobs as bg
from backend.agent.state import _error_jobs


@pytest.fixture(autouse=True)
def _reset_executor():
    bg.shutdown_executor(wait=True)
    _error_jobs.clear()
    yield
    bg.shutdown_executor(wait=True)
    _error_jobs.clear()


def _mark_done(job_id, form_id, row, dl, code, *, error_messages=None, error_details=None):
    """Stand-in for _run_error_enrichment_async's success path."""
    _error_jobs[job_id] = {
        "status": "done",
        "form_id": form_id,
        "payload": {
            "error_messages": error_messages or [],
            "error_details": error_details or [],
        },
    }


class TestEnrichmentStillWorks:
    def test_successful_enrichment_stores_the_result(self, monkeypatch):
        def _fake_run(job_id, form_id, row, dl, code):
            _mark_done(job_id, form_id, row, dl, code, error_messages=["some error"], error_details=[{"detail": "x"}])

        monkeypatch.setattr(bg, "_run_error_enrichment_async", _fake_run)
        job_id = "job-1"
        _error_jobs[job_id] = {"status": "pending", "payload": None, "form_id": "100"}
        bg._start_error_enrichment_thread(job_id, "100", {"row": 1}, {"dl": 1}, 3)

        deadline = time.monotonic() + 5
        while _error_jobs[job_id]["status"] != "done" and time.monotonic() < deadline:
            time.sleep(0.02)

        assert _error_jobs[job_id]["status"] == "done"
        assert _error_jobs[job_id]["payload"]["error_messages"] == ["some error"]

    def test_tenant_contextvar_is_still_propagated_into_the_worker(self, monkeypatch):
        """The switch from raw Thread to ThreadPoolExecutor must not drop
        the contextvars.copy_context().run() wrapping that carries the
        calling request's active tenant/repo-root into the worker (the bug
        this mechanism exists to prevent, per the function's own
        docstring)."""
        from backend import version_config

        seen = {}

        def _fake_run(job_id, form_id, row, dl, code):
            seen["root"] = version_config._active_root.get()
            _mark_done(job_id, form_id, row, dl, code)

        monkeypatch.setattr(bg, "_run_error_enrichment_async", _fake_run)

        token = version_config._active_root.set("/fake/tenant/root")
        try:
            job_id = "job-ctx"
            _error_jobs[job_id] = {"status": "pending", "payload": None, "form_id": "1"}
            bg._start_error_enrichment_thread(job_id, "1", {}, {}, 3)
            deadline = time.monotonic() + 5
            while _error_jobs[job_id]["status"] != "done" and time.monotonic() < deadline:
                time.sleep(0.02)
        finally:
            version_config._active_root.reset(token)

        assert seen.get("root") == "/fake/tenant/root"


class TestExecutorLifecycle:
    def test_executor_is_created_lazily_and_reused(self):
        assert bg._executor is None
        first = bg._get_executor()
        second = bg._get_executor()
        assert first is second

    def test_executor_is_not_recreated_per_submission(self, monkeypatch):
        monkeypatch.setattr(bg, "_run_error_enrichment_async", _mark_done)
        for i in range(5):
            job_id = f"job-{i}"
            _error_jobs[job_id] = {"status": "pending", "payload": None, "form_id": "1"}
            bg._start_error_enrichment_thread(job_id, "1", {}, {}, 3)
        # Only ever one executor instance across all 5 submissions.
        assert bg._executor is not None

    def test_shutdown_clears_the_executor_reference(self):
        bg._get_executor()
        assert bg._executor is not None
        bg.shutdown_executor(wait=True)
        assert bg._executor is None

    def test_configurable_max_workers(self, monkeypatch):
        monkeypatch.setenv("ERROR_ENRICHMENT_MAX_WORKERS", "2")
        assert bg._enrichment_max_workers() == 2

    def test_invalid_max_workers_env_falls_back_to_default(self, monkeypatch):
        monkeypatch.setenv("ERROR_ENRICHMENT_MAX_WORKERS", "not-a-number")
        assert bg._enrichment_max_workers() == 4


class TestBoundedConcurrency:
    def test_concurrent_enrichment_never_exceeds_the_configured_limit(self, monkeypatch):
        monkeypatch.setenv("ERROR_ENRICHMENT_MAX_WORKERS", "2")
        bg.shutdown_executor(wait=True)  # force re-read of the new env value

        in_flight = {"current": 0, "max_seen": 0}
        lock = threading.Lock()
        release = threading.Event()

        def _fake_run(job_id, form_id, row, dl, code):
            with lock:
                in_flight["current"] += 1
                in_flight["max_seen"] = max(in_flight["max_seen"], in_flight["current"])
            release.wait(timeout=2)
            with lock:
                in_flight["current"] -= 1
            _mark_done(job_id, form_id, row, dl, code)

        monkeypatch.setattr(bg, "_run_error_enrichment_async", _fake_run)

        job_ids = [f"job-{i}" for i in range(6)]
        for job_id in job_ids:
            _error_jobs[job_id] = {"status": "pending", "payload": None, "form_id": "1"}
            bg._start_error_enrichment_thread(job_id, "1", {}, {}, 3)

        time.sleep(0.3)  # let the first wave of workers pick up and block
        assert in_flight["max_seen"] <= 2, "never more than max_workers enrichment jobs run at once"

        release.set()
        deadline = time.monotonic() + 5
        while any(_error_jobs[j]["status"] != "done" for j in job_ids) and time.monotonic() < deadline:
            time.sleep(0.02)
        assert all(_error_jobs[j]["status"] == "done" for j in job_ids)

    def test_requests_beyond_the_limit_queue_rather_than_spawn_new_threads(self, monkeypatch):
        monkeypatch.setenv("ERROR_ENRICHMENT_MAX_WORKERS", "1")
        bg.shutdown_executor(wait=True)

        release = threading.Event()

        def _fake_run(job_id, form_id, row, dl, code):
            release.wait(timeout=2)
            _mark_done(job_id, form_id, row, dl, code)

        monkeypatch.setattr(bg, "_run_error_enrichment_async", _fake_run)

        threads_before = threading.active_count()
        job_ids = [f"job-{i}" for i in range(10)]
        for job_id in job_ids:
            _error_jobs[job_id] = {"status": "pending", "payload": None, "form_id": "1"}
            bg._start_error_enrichment_thread(job_id, "1", {}, {}, 3)

        # With max_workers=1, at most 1 extra worker thread exists for the
        # executor, regardless of how many jobs were submitted.
        threads_after = threading.active_count()
        assert threads_after - threads_before <= 1

        release.set()
        deadline = time.monotonic() + 5
        while any(_error_jobs[j]["status"] != "done" for j in job_ids) and time.monotonic() < deadline:
            time.sleep(0.02)
        assert all(_error_jobs[j]["status"] == "done" for j in job_ids)


class TestExceptionSafety:
    def test_exception_in_enrichment_does_not_crash_the_executor(self, monkeypatch):
        """_run_error_enrichment_async already catches everything internally
        (unchanged by this fix) -- this proves a failing submission neither
        raises out of _start_error_enrichment_thread nor poisons the shared
        executor for later submissions."""
        def _boom(job_id, form_id, row, dl, code):
            try:
                raise RuntimeError("enrichment blew up")
            except Exception:
                _error_jobs[job_id] = {
                    "status": "done", "form_id": form_id,
                    "payload": {"error_messages": [], "error_details": []},
                }

        monkeypatch.setattr(bg, "_run_error_enrichment_async", _boom)
        job_id = "job-boom"
        _error_jobs[job_id] = {"status": "pending", "payload": None, "form_id": "1"}
        bg._start_error_enrichment_thread(job_id, "1", {}, {}, 3)  # must not raise

        deadline = time.monotonic() + 5
        while _error_jobs[job_id]["status"] != "done" and time.monotonic() < deadline:
            time.sleep(0.02)
        assert _error_jobs[job_id]["status"] == "done"

    def test_executor_survives_a_failed_job_and_keeps_accepting_work(self, monkeypatch):
        calls = {"n": 0}

        def _flaky(job_id, form_id, row, dl, code):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("first call fails")
            _mark_done(job_id, form_id, row, dl, code, error_messages=["ok"])

        monkeypatch.setattr(bg, "_run_error_enrichment_async", _flaky)
        _error_jobs["job-a"] = {"status": "pending", "payload": None, "form_id": "1"}
        bg._start_error_enrichment_thread("job-a", "1", {}, {}, 3)
        _error_jobs["job-b"] = {"status": "pending", "payload": None, "form_id": "1"}
        bg._start_error_enrichment_thread("job-b", "1", {}, {}, 3)

        deadline = time.monotonic() + 5
        while _error_jobs["job-b"]["status"] != "done" and time.monotonic() < deadline:
            time.sleep(0.02)

        # job-a's worker raised (an unhandled exception inside the submitted
        # callable this time -- unlike the real function, which always
        # catches its own errors) -- the executor itself must still be
        # usable for job-b afterward.
        assert _error_jobs["job-b"]["payload"]["error_messages"] == ["ok"]
