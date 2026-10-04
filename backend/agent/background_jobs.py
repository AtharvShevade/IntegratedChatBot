"""backend/agent/background_jobs.py — fast status lookups + background
LLM error-enrichment jobs.

Every status-lookup fast-path here follows the same pattern: return the
status immediately, and if it's a failed run with errors, kick off error
explanation in a background thread rather than blocking the response on it
(the frontend polls /status-errors/{job_id} for the result).

Moved out of backend/agent/__init__.py verbatim — no logic changes.
"""

from __future__ import annotations

import contextvars
import logging
import os
import threading
import uuid as _uuid_mod
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from backend.tools.report_lookup import (
    _FAILED_STATUSES,
    _get_download_info,
    get_available_instances,
    get_instance_by_dtc_fast,
    get_instances_by_form_id,
    get_report_status_fast,
    get_report_status_exact_fast,
    _safe_status,
    _dtc_sort_key,
)
from backend.agent.state import _build, _error_jobs, _session_context, STAGE_PREV_DATES

logger = logging.getLogger(__name__)

# M-02: _start_error_enrichment_thread() previously spawned a brand-new
# threading.Thread(daemon=True) per call -- N concurrent status lookups with
# errors meant N concurrent threads, each making its own round of LLM calls,
# with no cap. A small bounded ThreadPoolExecutor replaces that: at most
# ERROR_ENRICHMENT_MAX_WORKERS enrichment jobs run at once; anything beyond
# that queues on the executor's own internal work queue (standard
# ThreadPoolExecutor behavior) instead of starting unboundedly many OS
# threads. Same "concurrency() -> max(1, int(os.getenv(...)))" convention
# already used by backend/stt/config.py's STT_CONCURRENCY.
def _enrichment_max_workers() -> int:
    try:
        return max(1, int(os.environ.get("ERROR_ENRICHMENT_MAX_WORKERS", "4")))
    except ValueError:
        return 4


_executor: ThreadPoolExecutor | None = None
_executor_lock = threading.Lock()


def _get_executor() -> ThreadPoolExecutor:
    """Lazily create the shared executor once (double-checked locking, same
    pattern as backend/db_qa/intents/embedding_index.py's L-12 fix) rather
    than creating a new one per request."""
    global _executor
    if _executor is None:
        with _executor_lock:
            if _executor is None:
                _executor = ThreadPoolExecutor(
                    max_workers=_enrichment_max_workers(),
                    thread_name_prefix="error-enrich",
                )
    return _executor


def shutdown_executor(wait: bool = False) -> None:
    """Called once from backend/main.py's lifespan at shutdown. wait=False
    (default) so application shutdown is never blocked on a slow in-flight
    Ollama call -- any enrichment job still running when the process exits
    is abandoned, exactly as the previous daemon-thread design already
    allowed (a daemon thread does not block process exit either)."""
    global _executor
    with _executor_lock:
        executor, _executor = _executor, None
    if executor is not None:
        executor.shutdown(wait=wait, cancel_futures=not wait)


def _get_instance_by_dtc_fast_with_bg_job(
    form_id: str, dtc: str, return_name: str, allowed_form_ids: set[str] | None = None,
) -> dict:
    """Call get_instance_by_dtc_fast and kick off background LLM enrichment
    for failed statuses.

    allowed_form_ids (H-10): when given, the enrichment thread is only
    started if form_id is in this set. Previously the thread (N Ollama
    calls) started unconditionally, and authorization was only applied to
    the RESULT afterwards (router.py's _apply_auth_to_status_result) --
    meaning an unauthorized caller could still trigger the full LLM cost,
    and other departments' error details still got computed and cached in
    _error_jobs, even though the final response was denied. None (the
    default) preserves the previous "no restriction" behavior exactly.
    """
    result = get_instance_by_dtc_fast(form_id, dtc, return_name)

    if (
        result.get("type") == "final"
        and result.get("status_code") in _FAILED_STATUSES
        and result.get("error_count", 0) > 0
        and (allowed_form_ids is None or form_id in allowed_form_ids)
    ):
        job_id = str(_uuid_mod.uuid4())
        # H-03: form_id stored on the job so /status-errors/{job_id} can
        # check the polling caller actually owns this form before returning
        # its (LLM-enriched) error details.
        _error_jobs[job_id] = {"status": "pending", "payload": None, "form_id": form_id}

        instances   = get_instances_by_form_id(form_id)
        target_dtc  = result["dtc"]
        row         = next(
            (r for r in instances if r.get("DTC", "").strip() == target_dtc), None
        )
        if row:
            code = _safe_status(row)
            dl   = _get_download_info(row, form_id)
            _start_error_enrichment_thread(job_id, form_id, row, dl, code)
            result["job_id"] = job_id

    return result


def _get_instance_by_date_fast_with_bg_job(
    form_id: str, date_query: str, return_name: str, allowed_form_ids: set[str] | None = None,
) -> dict:
    """Find instance by reporting date, then apply the fast+bg-job pattern."""
    rows = get_instances_by_form_id(form_id)
    date_clean = date_query.strip()
    row = next(
        (r for r in rows if r.get("ReportingDate", "").strip() == date_clean), None
    ) or next(
        (r for r in rows if date_clean.lower() in r.get("ReportingDate", "").lower()), None
    )
    if not row:
        return {
            "type":                "date_not_found",
            "message":             f"No instance found for '{date_clean}'.",
            "form_id":             form_id,
            "return_name":         return_name,
            "available_instances": get_available_instances(form_id),
        }
    dtc = row.get("DTC", "").strip()
    return _get_instance_by_dtc_fast_with_bg_job(form_id, dtc, return_name, allowed_form_ids)


def _run_error_enrichment_async(job_id: str, form_id: str, latest_row: dict, dl: dict, code: int) -> None:
    """Runs in a background thread. Calls existing LLM enrichment and stores result."""
    try:
        from backend.tools.report_lookup import _enrich_error_info
        error_messages, error_details = _enrich_error_info(code, dl, form_id)
        _error_jobs[job_id] = {
            "status": "done",
            "form_id": form_id,
            "payload": {
                "error_messages": error_messages,
                "error_details":  error_details,
            },
        }
    except Exception as exc:
        import logging as _logging
        _logging.getLogger(__name__).warning("[BG_ENRICH] job=%s failed: %s", job_id, exc)
        _error_jobs[job_id] = {
            "status": "done",
            "form_id": form_id,
            "payload": {"error_messages": [], "error_details": []},
        }


def _start_error_enrichment_thread(
    job_id: str, form_id: str, row: dict, dl: dict, code: int
) -> None:
    """Submit _run_error_enrichment_async to the bounded enrichment executor
    (M-02), WITH the calling request's contextvars (version_config's active
    repo root / tenant_id / jwt) copied across.

    threading.Thread/ThreadPoolExecutor do NOT inherit contextvars the way
    asyncio.Task does -- a plain worker thread starts with a fresh, empty
    Context. Under APP_VERSION=6.0 that meant this background enrichment
    silently read config._active_root() as unset and fell back to
    BASE_REPO_PATH (the 5.5 repo), regardless of which tenant's request
    started it. Running the target through contextvars.copy_context().run(...)
    carries the calling request's active root/tenant forward into the worker
    thread, exactly as if it had inherited it -- and is a no-op under 5.5,
    where that context is always empty anyway.

    Submitting to a bounded ThreadPoolExecutor (instead of starting a brand
    new daemon thread every call) caps how many enrichment jobs run
    concurrently; a call beyond the limit queues on the executor's own
    internal work queue rather than spawning an unbounded number of OS
    threads. Exceptions inside the submitted work are already fully caught
    inside _run_error_enrichment_async itself (it never lets one propagate
    out), so a failed enrichment cannot crash the executor or orphan a
    worker thread.
    """
    ctx = contextvars.copy_context()
    _get_executor().submit(
        ctx.run, _run_error_enrichment_async, job_id, form_id, row, dl, code
    )


def _get_status_fast_with_bg_job(query: str, allowed_form_ids: set[str] | None = None) -> dict:
    """Call get_report_status_fast and, for failed statuses with errors, kick off
    background LLM enrichment.  Returns the result dict with job_id attached when
    a background job was started.

    allowed_form_ids (H-10): see _get_instance_by_dtc_fast_with_bg_job's
    docstring -- same fix, same default (None = no restriction, unchanged).
    """
    result = get_report_status_fast(query)


    if (
        result.get("type") in ("final", "latest_with_ask")
        and result.get("status_code") in _FAILED_STATUSES
        and result.get("error_count", 0) > 0
        and (allowed_form_ids is None or result.get("form_id") in allowed_form_ids)
    ):
        job_id  = str(_uuid_mod.uuid4())
        form_id = result["form_id"]
        # H-03: form_id stored on the job for the ownership check in
        # /status-errors/{job_id}.
        _error_jobs[job_id] = {"status": "pending", "payload": None, "form_id": form_id}

        instances   = get_instances_by_form_id(form_id)
        sorted_rows = sorted(instances, key=_dtc_sort_key, reverse=True)
        latest_row  = sorted_rows[0]
        code        = _safe_status(latest_row)
        dl          = _get_download_info(latest_row, form_id)

        _start_error_enrichment_thread(job_id, form_id, latest_row, dl, code)

        result["job_id"]      = job_id
        result["result_type"] = result.get("result_type", "final")

    return result


def _get_status_by_id_fast_with_bg_job(instance_id: str, allowed_form_ids: set[str] | None = None) -> dict:
    """Same fast+bg-job pattern as _get_status_fast_with_bg_job, for a
    status lookup by a known InstanceLog Id rather than a report name —
    "what is the status of <id>". The background error-enrichment job
    (when applicable) targets THIS specific row, not "the latest instance
    for this form", since the whole point of an id-based lookup is a
    specific submission, not whichever happens to be newest.

    allowed_form_ids (H-10): see _get_instance_by_dtc_fast_with_bg_job's
    docstring -- same fix, same default (None = no restriction, unchanged).
    """
    from backend.tools.report_lookup import get_report_status_by_id_fast, _parse_instances

    result = get_report_status_by_id_fast(instance_id)

    if (
        result.get("type") in ("final", "latest_with_ask")
        and result.get("status_code") in _FAILED_STATUSES
        and result.get("error_count", 0) > 0
        and (allowed_form_ids is None or result.get("form_id") in allowed_form_ids)
    ):
        job_id  = str(_uuid_mod.uuid4())
        form_id = result["form_id"]
        _error_jobs[job_id] = {"status": "pending", "payload": None, "form_id": form_id}

        row = next((r for r in _parse_instances() if r.get("Id", "").strip() == instance_id.strip()), None)
        if row:
            code = _safe_status(row)
            dl   = _get_download_info(row, form_id)
            _start_error_enrichment_thread(job_id, form_id, row, dl, code)
            result["job_id"]      = job_id
            result["result_type"] = result.get("result_type", "final")

    return result


def _ask_another_date(
    result: dict,
    form_id: str,
    return_name: str,
    session_id: str | None,
    intent: str = "get_status",
) -> dict[str, Any]:
    """Show selected-instance status then ask whether to check another reporting date.

    Sets session to STAGE_PREV_DATES with the full instance list so the
    Yes-path can re-render the dropdown immediately without re-querying.
    """
    dtc = result.get("dtc", "")
    text = (
        f"{result['report_name']}\n"
        f"Reporting Date : {result['reporting_date']}\n"
    )
    if dtc:
        text += f"Initiated On   : {dtc}\n"
    text += f"Status         : {result['status']}"
    error_messages = result.get("error_messages", [])
    if error_messages:
        text += "\n\nFailure Reason(s):\n"
        text += "\n".join(f"• {m}" for m in error_messages)
    status_note = result.get("status_note", "")
    if status_note:
        text += f"\n{status_note}"

    all_instances = get_available_instances(form_id)
    if session_id:
        _session_context[session_id] = {
            "awaiting":                STAGE_PREV_DATES,
            "pending_form_id":         form_id,
            "pending_return_name":     return_name,
            "pending_other_instances": all_instances,
        }

    job_id = result.get("job_id")  # ★ FIX: propagate background job id
    status_code = result.get("status_code")
    error_category_counts = result.get("error_category_counts") or None
    is_4000_series = result.get("is_4000_series", False)   # ADD THIS



    # ★ FIX: if a bg job was kicked off, add the "Generating..." marker to text
    if job_id:
        error_count = result.get("error_count", 0)
        if error_count > 0:
            text += f"\n\nErrors Found : {error_count}\n\nGenerating error explanations…"
    # L-05: the synchronous (no bg job) path previously re-appended the same
    # "Failure Reason(s)" block here, duplicating the one already appended
    # unconditionally above (lines ~271-274) from the same error_messages --
    # removed rather than changed, since the first append already covers
    # this case correctly for both the job_id and no-job_id paths.

    response_data: dict[str, Any] = {}
    if status_code is not None:
        response_data["status_code"] = status_code
    if error_category_counts:
        response_data["error_category_counts"] = error_category_counts
    response_data["is_4000_series"] = is_4000_series   # ADD THIS
    response_data["form_id"] = form_id   # ← ADD THIS LINE



    return _build(
        intent=intent,
        report_name=return_name,
        response_text=text,
        result_type="ask_previous",
        options=["Yes", "No"],
        download_url=result.get("download_url", ""),
        download_label=result.get("download_label", ""),
        error_details=result.get("error_details") or None,  # ★ FIX
        job_id=job_id,                                       # ★ FIX
        data=response_data,                                  # ★ FIX
    )


def _get_status_exact_fast_with_bg_job(report_name: str, allowed_form_ids: set[str] | None = None) -> dict:
    """Call get_report_status_exact_fast and kick off background LLM enrichment
    for failed statuses, exactly like _get_status_fast_with_bg_job.

    allowed_form_ids (H-10): see _get_instance_by_dtc_fast_with_bg_job's
    docstring -- same fix, same default (None = no restriction, unchanged).
    """
    result = get_report_status_exact_fast(report_name)

    if (
        result.get("type") in ("final", "latest_with_ask")
        and result.get("status_code") in _FAILED_STATUSES
        and result.get("error_count", 0) > 0
        and (allowed_form_ids is None or result.get("form_id") in allowed_form_ids)
    ):
        job_id  = str(_uuid_mod.uuid4())
        form_id = result["form_id"]
        _error_jobs[job_id] = {"status": "pending", "payload": None, "form_id": form_id}

        instances   = get_instances_by_form_id(form_id)
        sorted_rows = sorted(instances, key=_dtc_sort_key, reverse=True)
        latest_row  = sorted_rows[0]
        code        = _safe_status(latest_row)
        dl          = _get_download_info(latest_row, form_id)

        _start_error_enrichment_thread(job_id, form_id, latest_row, dl, code)

        result["job_id"]      = job_id
        result["result_type"] = result.get("result_type", "final")

    return result


__all__ = [
    "_get_instance_by_dtc_fast_with_bg_job",
    "_get_instance_by_date_fast_with_bg_job",
    "_run_error_enrichment_async",
    "_start_error_enrichment_thread",
    "_get_status_fast_with_bg_job",
    "_get_status_by_id_fast_with_bg_job",
    "_ask_another_date",
    "_get_status_exact_fast_with_bg_job",
    "shutdown_executor",
]
