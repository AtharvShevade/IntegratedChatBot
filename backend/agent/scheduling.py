"""backend/agent/scheduling.py — report scheduling: reporting-date +
schedule-date/time collection, confirmation, and dispatch.

Moved out of backend/agent/__init__.py verbatim — no logic changes.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.tools.instance_generator import validate_reporting_date, resolve_return_exact
from backend.tools.report_lookup import find_matching_reports, fuzzy_report_suggestions
from backend.agent.state import (
    _build, _session_context,
    STAGE_SCHED_REPORT, STAGE_SCHED_RPT_DATE, STAGE_SCHED_DT, STAGE_SCHED_CONFIRM,
)
from backend.agent.auth_filters import _filter_names_by_auth
from backend.agent.generation import _date_ask_prompt

logger = logging.getLogger(__name__)


def _validate_future_schedule_date(
    schedule_date: str, schedule_time: str | None, frequency: str = "",
) -> tuple[bool, str]:
    """Validate that ``schedule_date`` (+ optional ``schedule_time``) is a
    real, future calendar date/time — this is simply when the .NET job
    should run, not the reporting period the generated instance is FOR, so
    it does NOT need to land on a frequency period-end (unlike
    reporting_date, which does). Any real future date in any of the
    supported formats (dd-MMM-yyyy, dd/mm/yyyy, dd-mm-yyyy, yyyy-mm-dd,
    dd.mm.yyyy) is accepted.

    Delegates to validate_reporting_date (require_future=True,
    skip_frequency_check=True) so date parsing and the future-date rule
    aren't duplicated here.

    Returns ``(is_valid, error_message)``.
    """
    result = validate_reporting_date(
        schedule_date, frequency, require_future=True, time_str=schedule_time,
        skip_frequency_check=True,
    )
    return result["valid"], (result["error"] or "")


def _finalize_schedule(
    ret: dict[str, Any],
    reporting_date: str | None,
    schedule_date: str | None,
    schedule_time: str | None,
    scheduled_datetime: str | None,
    session_id: str | None,
    login_id: str | None = None,
) -> dict[str, Any]:
    """Build a confirmed schedule response, or ask for whatever is still missing.

    Four mandatory inputs are collected, in order:
      1. Report name (resolved by the caller before this function is reached)
      2. Reporting Date — the business/period end-date the instance is FOR
         (e.g. 31-Mar-2026 for a Yearly return). Validated against the report's
         frequency via the same ``validate_reporting_date`` logic used by
         generate-instance, with ``require_future=False`` (past/current dates
         only) since a reporting period can never be in the future.
      3. Schedule Date + Schedule Time — the future date/time the .NET job
         should actually run and generate the instance. This is unrelated to
         the report's reporting period, so Schedule Date is only required to
         be a real, future calendar date (via ``_validate_future_schedule_date``,
         which delegates to ``validate_reporting_date`` with
         ``require_future=True, skip_frequency_check=True``) — no
         period-end/frequency constraint applies. Multiple input formats are
         accepted (dd-MMM-yyyy, dd/mm/yyyy, dd-mm-yyyy, yyyy-mm-dd, dd.mm.yyyy).
      4. Confirmation (Schedule / Change Data).

    Handles partial input gracefully at every stage and re-prompts for
    whatever is still missing without discarding what's already been given.
    """
    # ── Auth: scheduling performs instance generation internally, so it
    # requires the same Instance Generation permission — single enforcement
    # point, covers guided menu, free-text, and staged date/confirm turns.
    if login_id:
        from backend.services.auth_service import can_generate_instance as _chk_create
        if not _chk_create(login_id):
            logger.warning(
                "[AUTH_DENY] schedule_report: login_id=%r lacks Instance Generation permission",
                login_id,
            )
            return _build(
                intent="schedule_report", report_name=ret.get("name"),
                response_text="Sorry, you do not have access to schedule report generation.",
                result_type="error",
            )

    frequency   = ret.get("frequency", "")
    period_name = ret.get("period_name", "")

    # ── Reporting Date — mandatory, collected and validated before schedule
    # date/time. Reuses generate-instance's validation (require_future=False:
    # a reporting period can be the current period or any past period, never
    # a future one).
    if reporting_date and frequency:
        rpt_validation = validate_reporting_date(reporting_date, frequency)
        if not rpt_validation["valid"]:
            if session_id:
                _session_context[session_id] = {
                    "awaiting":              STAGE_SCHED_RPT_DATE,
                    "sched_form_id":         ret["form_id"],
                    "sched_return_name":     ret["name"],
                    "sched_frequency":       frequency,
                    "sched_period_name":     period_name,
                    "sched_reporting_date":  None,  # reject the invalid date
                    "sched_schedule_date":   schedule_date,
                    "sched_schedule_time":   schedule_time,
                }
            error_msg   = rpt_validation["error"]
            suggestions = [
                s for s in (rpt_validation.get("suggestions") or [])
                if s.lower() != reporting_date.lower()
            ]
            if len(suggestions) == 1:
                error_msg = f"Did you mean **{suggestions[0]}**?\n\n{error_msg}"
            return _build(
                intent="schedule_report",
                report_name=ret["name"],
                response_text=error_msg,
                result_type="sched_awaiting_rpt_date",
                options=suggestions if suggestions else None,
            )

    if not reporting_date:
        if session_id:
            _session_context[session_id] = {
                "awaiting":              STAGE_SCHED_RPT_DATE,
                "sched_form_id":         ret["form_id"],
                "sched_return_name":     ret["name"],
                "sched_frequency":       frequency,
                "sched_period_name":     period_name,
                "sched_schedule_date":   schedule_date,
                "sched_schedule_time":   schedule_time,
            }
        return _build(
            intent="schedule_report",
            report_name=ret["name"],
            response_text=_date_ask_prompt(ret["name"], frequency, period_name),
            result_type="sched_awaiting_rpt_date",
        )

    # ── Schedule-date validation — must simply be a real, future calendar
    # date/time (any supported format). No frequency/period-boundary
    # constraint — that only applies to reporting_date above.
    if schedule_date:
        _sched_valid, _sched_err = _validate_future_schedule_date(schedule_date, schedule_time, frequency)
        if not _sched_valid:
            if session_id:
                _session_context[session_id] = {
                    "awaiting":            STAGE_SCHED_DT,
                    "sched_form_id":       ret["form_id"],
                    "sched_return_name":   ret["name"],
                    "sched_frequency":     frequency,
                    "sched_period_name":   period_name,
                    "sched_reporting_date": reporting_date,
                    "sched_schedule_date": None,           # reject the invalid date
                    "sched_schedule_time": schedule_time,  # keep time if already given
                }
            return _build(
                intent="schedule_report",
                report_name=ret["name"],
                response_text=_sched_err,
                result_type="sched_awaiting_dt",
            )

    # ── Missing date or time — save what we have and ask for the rest ──────
    if not schedule_date or not schedule_time:
        if session_id:
            _session_context[session_id] = {
                "awaiting":            STAGE_SCHED_DT,
                "sched_form_id":       ret["form_id"],
                "sched_return_name":   ret["name"],
                "sched_frequency":     frequency,
                "sched_period_name":   period_name,
                "sched_reporting_date": reporting_date,
                "sched_schedule_date": schedule_date,
                "sched_schedule_time": schedule_time,
            }
        if not schedule_date and not schedule_time:
            prompt_text = (
                f"Reporting date confirmed: **{reporting_date}**.\n"
                "Please provide the schedule date and time.\n"
                'For example: "15-Apr-2026 at 4 PM".'
            )
        elif not schedule_date:
            prompt_text = (
                f"Time saved: **{schedule_time}**.\n"
                "Please provide the schedule date.\n"
                'For example: "15-Apr-2026".'
            )
        else:
            prompt_text = (
                f"Date saved: **{schedule_date}**.\n"
                "Please provide the schedule time.\n"
                'For example: "4 PM" or "16:00".'
            )
        return _build(
            intent="schedule_report",
            report_name=ret["name"],
            response_text=prompt_text,
            result_type="sched_awaiting_dt",
        )

    # Both date and time present — show confirmation card before finalizing
    if session_id:
        _session_context[session_id] = {
            "awaiting":            STAGE_SCHED_CONFIRM,
            "sched_form_id":       ret["form_id"],
            "sched_return_name":   ret["name"],
            "sched_reporting_date": reporting_date,
            "sched_schedule_date": schedule_date,
            "sched_schedule_time": schedule_time,
            "sched_scheduled_dt":  scheduled_datetime,
        }
    return _build(
        intent="schedule_report",
        report_name=ret["name"],
        response_text=(
            f"We are going to generate the report instance with the following schedule details:\n\n"
            f"Report Name    : {ret['name']}\n"
            f"Reporting Date : {reporting_date}\n"
            f"Schedule Date  : {schedule_date}\n"
            f"Schedule Time  : {schedule_time}"
        ),
        result_type="sched_confirm",
        options=["Schedule", "Change Data"],
    )


def _handle_schedule(
    report_ident: str,
    schedule_date: str | None,
    schedule_time: str | None,
    scheduled_datetime: str | None,
    session_id: str | None,
    allowed_form_ids: set[str] | None = None,
    login_id: str | None = None,
    reporting_date: str | None = None,
) -> dict[str, Any]:
    """Validate report name against known definitions, then confirm the schedule.

    Mirrors _handle_generate:
      find_matching_reports → disambiguation → resolve_return_exact → _finalize_schedule

    ``reporting_date`` (the business/period date the instance is FOR) is
    distinct from ``schedule_date``/``schedule_time`` (when the .NET job
    should run). It is optional here — free-text/guided callers rarely supply
    it up front — and _finalize_schedule will ask for it if missing.
    """
    # ── Auth: check BEFORE any report-name resolution/disambiguation — same
    # reasoning and permission as _handle_generate above. The check in
    # _finalize_schedule remains as the backstop for staged-turn callers.
    if login_id:
        from backend.services.auth_service import can_generate_instance as _chk_create
        if not _chk_create(login_id):
            logger.warning(
                "[AUTH_DENY] schedule_report: login_id=%r lacks Instance Generation permission (pre-resolution)",
                login_id,
            )
            return _build(
                intent="schedule_report", report_name=None,
                response_text="Sorry, you do not have access to schedule report generation.",
                result_type="error",
            )

    if not report_ident:
        return _build(
            intent="schedule_report",
            report_name=None,
            response_text=(
                "Please provide the report name and schedule datetime. "
                'For example: "Schedule CIMS_RAQ for 15-Apr-2026 at 4 PM".'
            ),
            need_clarification=True,
        )

    matches = find_matching_reports(report_ident)
    if allowed_form_ids is not None:
        matches = [m for m in matches if m.get("Id", "").strip() in allowed_form_ids]

    if not matches:
        suggestions = fuzzy_report_suggestions(report_ident)
        if allowed_form_ids is not None:
            suggestions = _filter_names_by_auth(suggestions, allowed_form_ids)
        if suggestions:
            if session_id:
                _session_context[session_id] = {
                    "awaiting":            STAGE_SCHED_REPORT,
                    "sched_reporting_date": reporting_date,
                    "sched_schedule_date": schedule_date,
                    "sched_schedule_time": schedule_time,
                    "sched_scheduled_dt":  scheduled_datetime,
                    "pending_options":     suggestions,
                }
            opts_text = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(suggestions))
            return _build(
                intent="schedule_report", report_name=None,
                response_text=(
                    f"No exact match found for '{report_ident}'. Did you mean one of these?\n\n"
                    f"{opts_text}"
                ),
                result_type="disambiguation", options=suggestions,
            )
        if allowed_form_ids is not None:
            return _build(
                intent="schedule_report", report_name=None,
                response_text="You are not authorised to access any matching reports.",
                result_type="error",
            )
        return _build(
            intent="schedule_report", report_name=None,
            response_text=f"No matching reports found for '{report_ident}'. Please try a different name.",
            result_type="error",
        )

    if len(matches) > 1:
        names = list(dict.fromkeys(m.get("Name", "") for m in matches if m.get("Name")))
        opts_text = "\n".join(f"{i + 1}. {n}" for i, n in enumerate(names))
        if session_id:
            _session_context[session_id] = {
                "awaiting":            STAGE_SCHED_REPORT,
                "sched_reporting_date": reporting_date,
                "sched_schedule_date": schedule_date,
                "sched_schedule_time": schedule_time,
                "sched_scheduled_dt":  scheduled_datetime,
                "pending_options":     names,
            }
        return _build(
            intent="schedule_report", report_name=None,
            response_text=(
                "Found multiple matching reports. Which one would you like to schedule?\n\n"
                f"{opts_text}"
            ),
            result_type="disambiguation", options=names,
        )

    # Single match — resolve full metadata and proceed
    ret = resolve_return_exact(matches[0].get("Name", report_ident))
    if not ret:
        return _build(
            intent="schedule_report", report_name=None,
            response_text=f'Report "{report_ident}" could not be resolved. Please try again.',
            result_type="error",
        )

    return _finalize_schedule(ret, reporting_date, schedule_date, schedule_time, scheduled_datetime, session_id, login_id)


__all__ = ["_validate_future_schedule_date", "_finalize_schedule", "_handle_schedule"]
