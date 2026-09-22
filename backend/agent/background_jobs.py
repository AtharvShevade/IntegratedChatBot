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
import threading
import uuid as _uuid_mod
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


async def _run_error_enrichment(job_id: str, form_id: str, ret_name: str, instances: list[dict]):
    from backend.tools.report_lookup import _build_status_result
    try:
        result = _build_status_result(form_id, ret_name, instances)

        _error_jobs[job_id] = {
            "status": "done",
            "payload": {
                "error_messages": result.get("error_messages", []),
                "error_details": result.get("error_details", []),
            },
        }

    except Exception as exc:
        logger.error(
            "[BG_ENRICH] error enrichment failed | job=%s form_id=%s report=%r | error=%s",
            job_id, form_id, ret_name, exc, exc_info=True,
        )
        _error_jobs[job_id] = {
            "status": "done",
            "payload": {"error_messages": [], "error_details": []},
        }



def _get_instance_by_dtc_fast_with_bg_job(
    form_id: str, dtc: str, return_name: str
) -> dict:
    """Call get_instance_by_dtc_fast and kick off background LLM enrichment
    for failed statuses."""
    result = get_instance_by_dtc_fast(form_id, dtc, return_name)

    if (
        result.get("type") == "final"
        and result.get("status_code") in _FAILED_STATUSES
        and result.get("error_count", 0) > 0
    ):
        job_id = str(_uuid_mod.uuid4())
        _error_jobs[job_id] = {"status": "pending", "payload": None}

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
    form_id: str, date_query: str, return_name: str
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
    return _get_instance_by_dtc_fast_with_bg_job(form_id, dtc, return_name)


def _run_error_enrichment_async(job_id: str, form_id: str, latest_row: dict, dl: dict, code: int) -> None:
    """Runs in a background thread. Calls existing LLM enrichment and stores result."""
    try:
        from backend.tools.report_lookup import _enrich_error_info
        error_messages, error_details = _enrich_error_info(code, dl, form_id)
        _error_jobs[job_id] = {
            "status": "done",
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
            "payload": {"error_messages": [], "error_details": []},
        }


def _start_error_enrichment_thread(
    job_id: str, form_id: str, row: dict, dl: dict, code: int
) -> None:
    """Start _run_error_enrichment_async in a background thread, WITH the
    calling request's contextvars (version_config's active repo root /
    tenant_id / jwt) copied across.

    threading.Thread does NOT inherit contextvars the way asyncio.Task does
    -- a plain Thread starts with a fresh, empty Context. Under
    APP_VERSION=6.0 that meant this background enrichment silently read
    config._active_root() as unset and fell back to BASE_REPO_PATH (the 5.5
    repo), regardless of which tenant's request started it. Running the
    target through contextvars.copy_context().run(...) carries the calling
    request's active root/tenant forward into the thread, exactly as if it
    had inherited it -- and is a no-op under 5.5, where that context is
    always empty anyway.
    """
    ctx = contextvars.copy_context()
    thread = threading.Thread(
        target=ctx.run,
        args=(_run_error_enrichment_async, job_id, form_id, row, dl, code),
        daemon=True,
    )
    thread.start()


def _get_status_fast_with_bg_job(query: str) -> dict:
    """Call get_report_status_fast and, for failed statuses with errors, kick off
    background LLM enrichment.  Returns the result dict with job_id attached when
    a background job was started.
    """
    result = get_report_status_fast(query)


    if (
        result.get("type") in ("final", "latest_with_ask")
        and result.get("status_code") in _FAILED_STATUSES
        and result.get("error_count", 0) > 0
    ):
        job_id = str(_uuid_mod.uuid4())
        _error_jobs[job_id] = {"status": "pending", "payload": None}

        form_id     = result["form_id"]
        instances   = get_instances_by_form_id(form_id)
        sorted_rows = sorted(instances, key=_dtc_sort_key, reverse=True)
        latest_row  = sorted_rows[0]
        code        = _safe_status(latest_row)
        dl          = _get_download_info(latest_row, form_id)

        _start_error_enrichment_thread(job_id, form_id, latest_row, dl, code)

        result["job_id"]      = job_id
        result["result_type"] = result.get("result_type", "final")

    return result


def _get_status_by_id_fast_with_bg_job(instance_id: str) -> dict:
    """Same fast+bg-job pattern as _get_status_fast_with_bg_job, for a
    status lookup by a known InstanceLog Id rather than a report name —
    "what is the status of <id>". The background error-enrichment job
    (when applicable) targets THIS specific row, not "the latest instance
    for this form", since the whole point of an id-based lookup is a
    specific submission, not whichever happens to be newest.
    """
    from backend.tools.report_lookup import get_report_status_by_id_fast, _parse_instances

    result = get_report_status_by_id_fast(instance_id)

    if (
        result.get("type") in ("final", "latest_with_ask")
        and result.get("status_code") in _FAILED_STATUSES
        and result.get("error_count", 0) > 0
    ):
        job_id = str(_uuid_mod.uuid4())
        _error_jobs[job_id] = {"status": "pending", "payload": None}

        form_id = result["form_id"]
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
    else:
        # Synchronous path — error_messages already populated
        error_messages = result.get("error_messages", [])
        if error_messages:
            text += "\n\nFailure Reason(s):\n"
            text += "\n".join(f"• {m}" for m in error_messages)

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


def _get_status_exact_fast_with_bg_job(report_name: str) -> dict:
    """Call get_report_status_exact_fast and kick off background LLM enrichment
    for failed statuses, exactly like _get_status_fast_with_bg_job."""
    result = get_report_status_exact_fast(report_name)

    if (
        result.get("type") in ("final", "latest_with_ask")
        and result.get("status_code") in _FAILED_STATUSES
        and result.get("error_count", 0) > 0
    ):
        job_id = str(_uuid_mod.uuid4())
        _error_jobs[job_id] = {"status": "pending", "payload": None}

        form_id     = result["form_id"]
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
    "_run_error_enrichment",
    "_get_instance_by_dtc_fast_with_bg_job",
    "_get_instance_by_date_fast_with_bg_job",
    "_run_error_enrichment_async",
    "_start_error_enrichment_thread",
    "_get_status_fast_with_bg_job",
    "_get_status_by_id_fast_with_bg_job",
    "_ask_another_date",
    "_get_status_exact_fast_with_bg_job",
]
