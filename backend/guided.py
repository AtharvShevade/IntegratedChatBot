# guided.py -- Guided workflow state machine.
# Step 1: captures the user's chosen action and asks for a report name.
# Step 2: intent is already known from the button pressed, so the user input is
#         treated directly as the report name and passed to the appropriate
#         agent handler via fuzzy matching — NO LLM call is made.
# Step 3+: disambiguation / date / confirmation are handled by the existing
#          decide() pipeline via session state (also no extra LLM calls because
#          decide() checks session state before reaching the LLM extractor).

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ── Stage constants ────────────────────────────────────────────────────────────
STAGE_MENU         = "MENU"
STAGE_STATUS_REPORT = "STATUS_REPORT"
STAGE_GEN_REPORT   = "GEN_REPORT"
STAGE_SCHED_REPORT = "SCHED_REPORT"
STAGE_CMP_REPORT   = "CMP_REPORT"
STAGE_DB_QUERY     = "DB_QUERY"

# Action labels shown as clickable buttons
GUIDED_ACTIONS: list[str] = [
    "Check report status",
    "Generate instance for a report",
    "Schedule a report",
    "Perform comparative analysis",
    "Retrieve data from database",
]

# ── Per-session guided state ───────────────────────────────────────────────────
_guided_sessions: dict[str, dict[str, Any]] = {}


# ── Helpers ────────────────────────────────────────────────────────────────────
def _build(
    response_text: str,
    result_type:   str,
    options:       list[str] | None = None,
    report_name:   str | None = None,
) -> dict[str, Any]:
    return {
        "intent":             "guided",
        "report_name":        report_name,
        "response_text":      response_text,
        "need_clarification": False,
        "result_type":        result_type,
        "options":            options or [],
        "variance_data":      [],
        "variance_label_a":   "",
        "variance_label_b":   "",
        "llm_summary":        "",
        "instances_data":     [],
    }


def _menu() -> dict[str, Any]:
    return _build(
        response_text="What would you like to do? Select an action to get started:",
        result_type="guided_menu",
        options=GUIDED_ACTIONS,
    )


# ── Main entry point ───────────────────────────────────────────────────────────
async def guided_step(
    message:     str,
    session_id:  str | None,
    asp_session: str | None,
    login_id:    str | None = None,
) -> dict[str, Any]:
    """Handle one step of the guided workflow.

    Step 1 (action selection): captures the chosen action, sets guided stage,
    returns a prompt asking for the report name.

    Step 2 (report name): the intent is already known from the selected action,
    so the user input is treated directly as the report name.  The appropriate
    agent handler is called WITHOUT any LLM call — fuzzy matching against the
    returns.xml master list is used instead.

    Step 3+ (disambiguation / date / confirmation): the agent handlers set
    session state in _session_context.  Subsequent messages arrive via /chat
    (isGuidedFlow becomes false after step 2) and decide() handles them
    deterministically via session-state checks before any LLM extraction.
    """
    # Lazy imports keep startup fast and avoid circular-import issues.
    from backend.agent import (
        _handle_compare,
        _handle_generate,
        _handle_schedule,
        _from_result,
    )
    from backend.tools.report_lookup import get_report_status

    session = _guided_sessions.get(session_id, {}) if session_id else {}
    stage   = session.get("stage", STAGE_MENU)
    msg     = message.strip()

    # ── Auth: resolve allowed FormIds for this user ────────────────────────
    allowed_form_ids: set[str] | None = None  # None = no restriction
    if login_id:
        from backend.services.auth_service import get_allowed_form_ids as _get_auth
        allowed_form_ids = _get_auth(login_id)
        if allowed_form_ids is None:
            logger.warning("[AUTH_DENY] guided: user not found login_id=%r session=%s", login_id, session_id)
            return _build(
                response_text="Your account was not recognised. Please contact your administrator.",
                result_type="error",
            )

    # ── Step 1: action selection ───────────────────────────────────────────────
    if stage == STAGE_MENU or msg in GUIDED_ACTIONS:
        if msg in GUIDED_ACTIONS:
            logger.info("[GUIDED_ACTION] action=%r session=%s", msg, session_id)
            return _handle_action_selected(msg, session_id)
        if session_id:
            _guided_sessions.pop(session_id, None)
        return _menu()

    # ── Step 2: report name received — deterministic routing, no LLM ──────────
    # Clear guided state now; downstream handlers own all subsequent
    # multi-turn state via _session_context.
    if session_id:
        _guided_sessions.pop(session_id, None)

    logger.info(
        "[GUIDED_STEP2] stage=%s report_input=%r session=%s — routing without LLM",
        stage, msg, session_id,
    )

    if stage == STAGE_STATUS_REPORT:
        # Fuzzy-match the input directly against returns.xml — no LLM needed.
        logger.info("[GUIDED_STATUS_LOOKUP] input=%r session=%s", msg, session_id)
        result = get_report_status(msg)
        if allowed_form_ids is not None:
            from backend.agent import _apply_auth_to_status_result
            result = _apply_auth_to_status_result(result, allowed_form_ids)
        return _from_result(result, intent="get_status", session_id=session_id)

    if stage == STAGE_GEN_REPORT:
        # _handle_generate runs find_matching_reports + fuzzy suggestions — no LLM.
        logger.info("[GUIDED_GENERATE_LOOKUP] input=%r session=%s", msg, session_id)
        return await _handle_generate(
            report_name=msg,
            reporting_date=None,
            session_id=session_id,
            asp_session=asp_session,
            allowed_form_ids=allowed_form_ids,
        )

    if stage == STAGE_SCHED_REPORT:
        # _handle_schedule runs find_matching_reports + fuzzy suggestions — no LLM.
        logger.info("[GUIDED_SCHEDULE_LOOKUP] input=%r session=%s", msg, session_id)
        return _handle_schedule(
            report_ident=msg,
            schedule_date=None,
            schedule_time=None,
            scheduled_datetime=None,
            session_id=session_id,
            allowed_form_ids=allowed_form_ids,
        )

    if stage == STAGE_CMP_REPORT:
        # _handle_compare runs find_matching_reports + fuzzy suggestions — no LLM.
        logger.info("[GUIDED_COMPARE_LOOKUP] input=%r session=%s", msg, session_id)
        return await _handle_compare(report_ident=msg, session_id=session_id, allowed_form_ids=allowed_form_ids)

    if stage == STAGE_DB_QUERY:
        logger.info("[GUIDED_DB_QUERY] input=%r session=%s", msg, session_id)
        from backend.sql_agent import handle_db_query
        return await handle_db_query(msg, session_id=session_id)

    return _menu()


def _handle_action_selected(action: str, session_id: str | None) -> dict[str, Any]:
    """Set the first guided stage and return the report-name prompt."""
    if action == "Check report status":
        if session_id:
            _guided_sessions[session_id] = {"stage": STAGE_STATUS_REPORT}
        return _build(
            response_text="Enter the report name (e.g. CIMS_RAQ, APBL, RAQ):",
            result_type="guided_input",
            options=[],
        )

    if action == "Generate instance for a report":
        if session_id:
            _guided_sessions[session_id] = {"stage": STAGE_GEN_REPORT}
        return _build(
            response_text="Enter the report name:",
            result_type="guided_input",
            options=[],
        )

    if action == "Schedule a report":
        if session_id:
            _guided_sessions[session_id] = {"stage": STAGE_SCHED_REPORT}
        return _build(
            response_text="Enter the report name:",
            result_type="guided_input",
            options=[],
        )

    if action == "Perform comparative analysis":
        if session_id:
            _guided_sessions[session_id] = {"stage": STAGE_CMP_REPORT}
        return _build(
            response_text="Enter the report name to compare (e.g. HDFC, CIMS_RAQ):",
            result_type="guided_input",
            options=[],
        )

    if action == "Retrieve data from database":
        if session_id:
            _guided_sessions[session_id] = {"stage": STAGE_DB_QUERY}
        return _build(
            response_text="What data would you like to query? Describe in detail (e.g. 'Show gross NPA for Q1 FY2024'):",
            result_type="guided_input",
            options=[],
        )

    return _menu()