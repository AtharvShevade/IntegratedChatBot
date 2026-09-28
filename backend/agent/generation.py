"""backend/agent/generation.py — instance generation: report resolution,
reporting-date prompts/validation, and the .NET generate-instance API call.

Moved out of backend/agent/__init__.py verbatim — no logic changes.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from backend import version_config
from backend.tools.instance_generator import (
    call_generate_api, call_generate_api_v6, resolve_return_exact, validate_reporting_date,
)
from backend.tools.report_lookup import find_matching_reports, fuzzy_report_suggestions
from backend.agent.state import _build, _session_context, STAGE_GEN_REPORT, STAGE_GEN_DATE
from backend.agent.auth_filters import _filter_names_by_auth

logger = logging.getLogger(__name__)


def _matching_instance_log_rows(
    form_id: str, reporting_date: str, login_id: str | None,
) -> list[dict]:
    from backend import config
    from backend.db_qa.xml_store import XMLStore

    if not config.app_db_base_path():
        logger.warning(
            "[INSTANCE_LOG_PATH] config.app_db_base_path() is empty — "
            "cannot look up instance log rows (BASE_REPO_PATH/tenant root unresolved?)"
        )
        return []
    resolved_path = config.instance_log_xml_path()
    store = XMLStore(config.app_db_base_path())
    all_rows = store.instance_log()
    matches = [
        l for l in all_rows
        if l.get("FormId", "") == str(form_id)
        and l.get("ReportingDate", "").strip().lower() == reporting_date.strip().lower()
        and (not login_id or l.get("UserId", "") == login_id)
    ]
    logger.debug(
        "[INSTANCE_LOG_PATH] path=%s total_rows=%d matching_rows=%d form_id=%s reporting_date=%s",
        resolved_path, len(all_rows), len(matches), form_id, reporting_date,
    )
    return matches


def _parse_dtc(dtc: str):
    from datetime import datetime as _datetime
    try:
        return _datetime.strptime(dtc.strip(), "%d-%b-%Y %I:%M:%S %p")
    except (ValueError, AttributeError):
        return None


async def _find_new_instance_log_id(
    form_id: str, reporting_date: str, login_id: str | None,
    before_ids: frozenset[str] = frozenset(),
) -> str | None:
    """Best-effort lookup of the just-created InstanceLog row's Id after a
    successful generate-instance call.

    call_generate_api's .NET response array never includes the new row's
    Id (see its own docstring — only a bool/date/message tuple) — only a
    fresh read of XML_InstanceLog.xml has it. The row may not be flushed
    to disk the instant the API responds, so this retries briefly before
    giving up. A miss here must never fail the (already successful)
    generation — the caller only omits the ID line, it doesn't surface an
    error for what's otherwise a completed action.

    *before_ids* — the set of matching rows' Ids captured BEFORE the
    generate-instance call was made — is required, not optional in
    practice: a return/reporting-date combination commonly gets
    generated repeatedly across testing/real use, so many OLD rows can
    already match (FormId, ReportingDate, UserId) by the time this looks
    up "the new one". Without a before/after diff, "pick whichever
    matching row looks most recent" can return a stale row from a much
    earlier generation — worse, it did so via a plain string sort on DTC
    ("DD-Mon-YYYY ..."), which isn't even chronologically correct (e.g.
    "Jul" sorts before "Jun" alphabetically, backwards from calendar
    order) on top of not being scoped to "since this call" at all. Only
    a row whose Id wasn't already present before the call can be the one
    this call created.
    """
    from backend import config
    resolved_path = config.instance_log_xml_path()
    logger.info(
        "[INSTANCE_LOG_PATH] polling path=%s form_id=%s reporting_date=%s before_ids=%d "
        "(this is the exact file Python reads — compare against wherever the .NET "
        "generation service is configured to write XML_InstanceLog.xml if the "
        "Request ID never appears)",
        resolved_path, form_id, reporting_date, len(before_ids),
    )
    first_seen_total: int | None = None
    for attempt in range(8):
        if attempt:
            await asyncio.sleep(1.0)
        rows = _matching_instance_log_rows(form_id, reporting_date, login_id)
        if first_seen_total is None:
            first_seen_total = len(rows)
        new_rows = [r for r in rows if r.get("Id") and r["Id"] not in before_ids]
        if not new_rows:
            continue
        if len(new_rows) == 1:
            return new_rows[0]["Id"]
        # More than one new row appeared (e.g. a rapid double-submit) —
        # break the tie with an actually-parsed datetime, not a string
        # sort, so month-name ordering can't scramble the result.
        from datetime import datetime as _datetime
        new_rows.sort(key=lambda r: _parse_dtc(r.get("DTC", "")) or _datetime.min, reverse=True)
        return new_rows[0]["Id"]

    last_total = len(_matching_instance_log_rows(form_id, reporting_date, login_id))
    logger.warning(
        "[INSTANCE_LOG_PATH] gave up after 8 attempts (~7s) — path=%s "
        "matching_rows_first_seen=%s matching_rows_last_seen=%s. If these two "
        "counts are EQUAL, no new row ever appeared in this file during the "
        "retry window — check whether the .NET generation service is writing "
        "XML_InstanceLog.xml to a DIFFERENT path than the one logged above.",
        resolved_path, first_seen_total, last_total,
    )
    return None


async def _finalize_generation(
    ret: dict[str, Any],
    reporting_date: str,
    session_id: str | None,
    asp_session: str | None = None,
    login_id: str | None = None,
) -> dict[str, Any]:
    """Validate date and call the .NET API for a fully-resolved (report, date) pair."""
    # ── Auth: role-based Instance Generation permission ───────────────────────
    # Single enforcement point for generate_instance — every path (guided menu,
    # free-text, staged date-entry) converges here before the .NET API call.
    if login_id:
        from backend.services.auth_service import can_generate_instance as _chk_create
        if not _chk_create(login_id):
            logger.warning(
                "[AUTH_DENY] generate_instance: login_id=%r lacks Instance Generation permission",
                login_id,
            )
            return _build(
                intent="generate_instance", report_name=ret.get("name"),
                response_text="Sorry, you do not have access to generate report instances.",
                result_type="error",
            )

    validation = validate_reporting_date(reporting_date, ret["frequency"])
    if not validation["valid"]:
        logger.debug(
            "[DATE_VALIDATION_FAIL] date=%r freq=%r error=%r suggestions=%r",
            reporting_date, ret["frequency"], validation["error"], validation["suggestions"],
        )
        # Keep context so user can retry with a corrected date
        if session_id:
            _session_context[session_id] = {
                "awaiting":        STAGE_GEN_DATE,
                "gen_form_id":     ret["form_id"],
                "gen_return_name": ret["name"],
                "gen_frequency":   ret["frequency"],
                "gen_period_name": ret.get("period_name", ""),
            }
        error_msg   = validation["error"]
        suggestions = validation.get("suggestions") or []

        # Filter out the same date the user entered — never echo back an invalid
        # date as a suggestion (e.g. "Did you mean 31-May-2026?" when it's future).
        suggestions = [s for s in suggestions if s.lower() != reporting_date.lower()]

        # Near-miss hint: single suggestion that is DIFFERENT from the input
        if len(suggestions) == 1:
            error_msg = f"Did you mean **{suggestions[0]}**?\n\n{error_msg}"

        return _build(
            intent="generate_instance", report_name=ret["name"],
            response_text=error_msg,
            result_type="gen_awaiting_date",
            options=suggestions if suggestions else None,
        )

    # Snapshot which rows already match (FormId, ReportingDate, UserId)
    # BEFORE calling the API — the same (return, reporting date) is
    # routinely generated more than once across testing/real use, so
    # several old rows can already satisfy this filter. Only a row whose
    # Id wasn't in this snapshot can be the one THIS call creates.
    before_ids = frozenset(
        r["Id"] for r in _matching_instance_log_rows(ret["form_id"], reporting_date, login_id)
        if r.get("Id")
    )

    if version_config.IS_V6:
        api_result = await call_generate_api_v6(
            ret["form_id"], reporting_date,
            tenant_id=version_config.get_active_tenant_id() or "",
            jwt=version_config.get_active_jwt(),
        )
    else:
        api_result = await call_generate_api(ret["form_id"], reporting_date, asp_session)
    if session_id:
        _session_context.pop(session_id, None)

    if api_result["success"]:
        logger.info(
            "[GENERATE_SUCCESS] report=%r date=%s session=%s",
            ret["name"], reporting_date, session_id,
        )
        instance_id = await _find_new_instance_log_id(ret["form_id"], reporting_date, login_id, before_ids)
        id_line = f"\nRequest ID     : {instance_id}" if instance_id else ""
        return _build(
            intent="generate_instance", report_name=ret["name"],
            response_text=(
                f"Generating instance for '{ret['name']}'"
                f"\nReporting Date : {reporting_date}"
                f"\nStatus         : {api_result['message']}"
                f"{id_line}"
            ),
            result_type="gen_success",
        )
    logger.error(
        "[GENERATE_FAIL] report=%r date=%s message=%r session=%s",
        ret["name"], reporting_date, api_result["message"], session_id,
    )
    return _build(
        intent="generate_instance", report_name=ret["name"],
        response_text=(
            f"Instance generation failed: {api_result['message']}\n"
            "Please check the XBRL generation service on the server."
        ),
        result_type="error",
    )


async def _handle_gen_date(
    date_str: str,
    session: dict[str, Any],
    session_id: str | None,
    asp_session: str | None = None,
    login_id: str | None = None,
) -> dict[str, Any]:
    """Thin wrapper: assemble ret dict from session and delegate to _finalize_generation."""
    ret = {
        "form_id":     session["gen_form_id"],
        "name":        session["gen_return_name"],
        "frequency":   session["gen_frequency"],
        "period_name": session.get("gen_period_name", ""),
    }
    return await _finalize_generation(ret, date_str, session_id, asp_session, login_id)


_MONTH_NUM = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}


def _example_date(day: int, mon_abbr: str, year: int) -> str:
    """'31-Mar-2026/31-03-2026' -- both the DD-Mon-YYYY and DD-MM-YYYY shapes
    for one date, side by side, so a user who prefers typing the numeric form
    sees it's accepted too. Both halves are independently protected from
    translation garbling by i18n/protect.py's existing date patterns."""
    return f"{day:02d}-{mon_abbr}-{year}/{day:02d}-{_MONTH_NUM[mon_abbr]:02d}-{year}"


def _date_ask_prompt(report_name: str, frequency: str, period_name: str) -> str:
    """Build a dynamic date-entry prompt based on the report's frequency."""
    import calendar as _cal
    from datetime import date as _date
    freq  = (frequency or "").upper()
    label = period_name or freq
    year  = _date.today().year

    lines = [f"Please enter the reporting date for **{report_name}**.", ""]

    if freq == "Q":
        lines += [
            "Quarterly reports must use:",
            "• 31-Mar", "• 30-Jun", "• 30-Sep", "• 31-Dec",
            "", f"Example: {_example_date(31, 'Mar', year)}",
        ]
    elif freq == "M":
        today = _date.today()
        last  = _cal.monthrange(today.year, today.month)[1]
        mname = today.strftime("%b")
        lines += [
            "Monthly reports must use the last day of the month.",
            "", f"Example: {_example_date(last, mname, year)}",
        ]
    elif freq == "H":
        lines += [
            "Half Yearly reports must use:",
            "• 31-Mar", "• 30-Sep",
            "", f"Example: {_example_date(31, 'Mar', year)}",
        ]
    elif freq == "C":
        lines += [
            "Half Yearly (Calendar Year) reports must use:",
            "• 30-Jun", "• 31-Dec",
            "", f"Example: {_example_date(30, 'Jun', year)}",
        ]
    elif freq == "Y":
        lines += [
            "Yearly (Financial Year) reports must use:",
            "• 31-Mar",
            "", f"Example: {_example_date(31, 'Mar', year)}",
        ]
    elif freq == "B":
        lines += [
            "Yearly (Calendar Year) reports must use:",
            "• 31-Dec",
            "", f"Example: {_example_date(31, 'Dec', year)}",
        ]
    elif freq == "W":
        lines += [
            "Weekly reports must use a Friday.",
            "", f"Example: the nearest past Friday.",
        ]
    elif freq in ("F", "HM"):
        today = _date.today()
        last  = _cal.monthrange(today.year, today.month)[1]
        mname = today.strftime("%b")
        freq_label = "Fortnightly" if freq == "F" else "Half Monthly"
        lines += [
            f"{freq_label} reports must use:",
            "• 15th of the month",
            "• Last day of the month",
            "", f"Example: {_example_date(15, mname, year)} or {_example_date(last, mname, year)}",
        ]
    elif freq == "E":
        lines += [
            "This report must use the last Friday of the month.",
        ]
    elif freq == "D":
        lines += [
            "Daily reports accept any valid past date.",
            "", f"Example: {_example_date(26, 'May', year)}",
        ]
    else:
        lines += [
            f"Enter a valid reporting date for this {label} report.",
            "", f"Example: {_example_date(31, 'Mar', year)}",
        ]

    return "\n".join(lines)


async def _handle_generate(
    report_name: str,
    reporting_date: str | None,
    session_id: str | None,
    asp_session: str | None = None,
    allowed_form_ids: set[str] | None = None,
    login_id: str | None = None,
) -> dict[str, Any]:
    """Entry point for generate_instance intent from the normal (non-staged) flow."""
    # ── Auth: check BEFORE any report-name resolution/disambiguation so a
    # user without Instance Generation permission is told immediately,
    # instead of being walked through name/date prompts first. The check in
    # _finalize_generation remains as the backstop for staged-turn callers
    # (e.g. _handle_gen_date) that reach it without passing through here.
    if login_id:
        from backend.services.auth_service import can_generate_instance as _chk_create
        if not _chk_create(login_id):
            logger.warning(
                "[AUTH_DENY] generate_instance: login_id=%r lacks Instance Generation permission (pre-resolution)",
                login_id,
            )
            return _build(
                intent="generate_instance", report_name=None,
                response_text="Sorry, you do not have access to generate report instances.",
                result_type="error",
            )

    matches = find_matching_reports(report_name)
    original_matches = matches
    if allowed_form_ids is not None:
        matches = [m for m in matches if m.get("Id", "").strip() in allowed_form_ids]

    if not matches:
        suggestions = fuzzy_report_suggestions(report_name)
        if allowed_form_ids is not None:
            suggestions = _filter_names_by_auth(suggestions, allowed_form_ids)
        if suggestions:
            if session_id:
                _session_context[session_id] = {
                    "awaiting":               STAGE_GEN_REPORT,
                    "pending_reporting_date": reporting_date,
                    "pending_options":        suggestions,
                }
            opts_text = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(suggestions))
            return _build(
                intent="generate_instance", report_name=None,
                response_text=(
                    f"No exact match found for '{report_name}'. Did you mean one of these?\n\n"
                    f"{opts_text}"
                ),
                result_type="disambiguation", options=suggestions,
            )
        if allowed_form_ids is not None and original_matches:
            return _build(
                intent="generate_instance", report_name=None,
                response_text="You are not authorised to access this report.",
                result_type="error",
            )
        if allowed_form_ids is not None:
            return _build(
                intent="generate_instance", report_name=None,
                response_text=f"No matching reports found for '{report_name}'. Please try a different name.",
                result_type="error",
            )
        return _build(
            intent="generate_instance", report_name=None,
            response_text=f"No matching reports found for '{report_name}'. Please try a different name.",
            result_type="error",
        )

    if len(matches) > 1:
        names = list(dict.fromkeys(m.get("Name", "") for m in matches if m.get("Name")))
        opts_text = "\n".join(f"{i + 1}. {n}" for i, n in enumerate(names))
        if session_id:
            _session_context[session_id] = {
                "awaiting":               STAGE_GEN_REPORT,
                "pending_reporting_date": reporting_date,
                "pending_options":        names,
            }
        return _build(
            intent="generate_instance", report_name=None,
            response_text=(
                "Found multiple matching reports. Which one would you like to generate?\n\n"
                f"{opts_text}"
            ),
            result_type="disambiguation", options=names,
        )

    # Single match -- resolve full metadata
    ret = resolve_return_exact(matches[0].get("Name", report_name))
    if not ret:
        return _build(
            intent="generate_instance", report_name=None,
            response_text=f'Report "{report_name}" could not be resolved. Please try again.',
            result_type="error",
        )

    # Date not provided -- ask for it, save context
    if not reporting_date:
        logger.info(
            "[REPORT_DATE_DETECTED] no date in query — prompting user for reporting date (report=%r)",
            ret["name"],
        )
        if session_id:
            _session_context[session_id] = {
                "awaiting":        STAGE_GEN_DATE,
                "gen_form_id":     ret["form_id"],
                "gen_return_name": ret["name"],
                "gen_frequency":   ret["frequency"],
                "gen_period_name": ret["period_name"],
            }
        return _build(
            intent="generate_instance", report_name=ret["name"],
            response_text=_date_ask_prompt(ret["name"], ret["frequency"], ret["period_name"]),
            result_type="gen_awaiting_date",
        )

    # Both slots filled -- validate and trigger
    logger.info(
        "[SKIP_DATE_PROMPT] date=%r already known for report=%r — proceeding to generation",
        reporting_date, ret["name"],
    )
    return await _finalize_generation(ret, reporting_date, session_id, asp_session, login_id)


__all__ = [
    "_matching_instance_log_rows", "_parse_dtc", "_find_new_instance_log_id",
    "_finalize_generation", "_handle_gen_date", "_date_ask_prompt", "_handle_generate",
]
