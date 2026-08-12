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

# ── Central action → permission mapping ────────────────────────────────────────
# Actions not listed here require no permission beyond return access (Status,
# Compare, DB Q&A) — only actions that need a role-level check (backed by
# RoleAccess.xml, resolved via auth_service.can_generate_instance) are listed.
# Scheduling performs instance generation internally, so it reuses the same
# permission.
# To gate a future action, add its label here — no other code changes needed
# for the menu-filtering side (backend enforcement still belongs in that
# action's own handler, same pattern as _finalize_generation/_finalize_schedule).
_ACTIONS_REQUIRING_INSTANCE_GENERATION: frozenset[str] = frozenset({
    "Generate instance for a report",
    "Schedule a report",
})

# ── Per-session guided state ───────────────────────────────────────────────────
_guided_sessions: dict[str, dict[str, Any]] = {}

# ── Request ID (Instance ID) detection for the status report-name step ────────
# A real Request ID is a 32-char hex string or a hyphenated UUID (see
# backend.db_qa.new_intent_classifier._INSTANCE_ID_RE, reused below for the
# exact-shape check). Report names/ReturnIds/short names in this system
# (e.g. "CIMS_ROR", "R149", "RAQ") always contain at least one non-hex
# letter, and bare numeric form_ids are consistently 3-4 digits — so
# "hex-only characters AND at least 6 of them" cleanly identifies an
# attempted Request ID (complete or not) without ever matching a real
# report name/ReturnId/short name input, leaving that lookup path untouched.
import re as _re_guided
_HEX_ONLY_RE = _re_guided.compile(r"^[0-9a-f]+$", _re_guided.IGNORECASE)
_MIN_REQUEST_ID_ATTEMPT_LEN = 6


def _looks_like_request_id_attempt(text: str) -> bool:
    """True if *text* is plausibly an attempt at a Request ID (complete or
    not) — used only to decide whether to try an exact-ID lookup instead of
    the existing report-name/ReturnId/short-name fuzzy match, never to
    accept a partial ID as a match itself."""
    return bool(_HEX_ONLY_RE.match(text)) and len(text) >= _MIN_REQUEST_ID_ATTEMPT_LEN


def _allowed_actions(login_id: str | None) -> list[str]:
    """Return the subset of GUIDED_ACTIONS this user may see/perform.

    No login_id (dev / backward-compat) -> all actions shown, matching the
    existing "no identity, no restriction" convention used elsewhere
    (get_allowed_form_ids, can_generate_instance).
    """
    if not login_id:
        return list(GUIDED_ACTIONS)

    from backend.services.auth_service import can_generate_instance
    can_generate = can_generate_instance(login_id)

    if can_generate:
        return list(GUIDED_ACTIONS)
    return [a for a in GUIDED_ACTIONS if a not in _ACTIONS_REQUIRING_INSTANCE_GENERATION]


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


def _menu(login_id: str | None = None) -> dict[str, Any]:
    return _build(
        response_text="What would you like to do? Select an action to get started:",
        result_type="guided_menu",
        options=_allowed_actions(login_id),
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
        from backend.services.auth_service import (
            AUTHORIZATION_ENABLED as _AUTH_ENABLED,
            get_allowed_form_ids as _get_auth,
        )
        allowed_form_ids = _get_auth(login_id)
        if not _AUTH_ENABLED:
            logger.info(
                "[AUTH_BYPASS] Authorization disabled; allowing all forms for login_id=%r session=%s",
                login_id, session_id,
            )
        elif allowed_form_ids is None:
            logger.warning("[AUTH_DENY] guided: user not found login_id=%r session=%s", login_id, session_id)
            return _build(
                response_text="Your account was not recognised. Please contact your administrator.",
                result_type="error",
            )

    # ── Step 1: action selection ───────────────────────────────────────────────
    if stage == STAGE_MENU or msg in GUIDED_ACTIONS:
        if msg in GUIDED_ACTIONS:
            logger.info("[GUIDED_ACTION] action=%r session=%s", msg, session_id)
            return _handle_action_selected(msg, session_id, login_id)
        if session_id:
            _guided_sessions.pop(session_id, None)
        return _menu(login_id)

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
        # Request ID (Instance ID) support: only attempted when the input
        # looks like an ID (hex-only, 6+ chars — see
        # _looks_like_request_id_attempt) so real report name/ReturnId/
        # short-name inputs are completely unaffected and fall through to
        # the existing fuzzy match below, unchanged.
        if _looks_like_request_id_attempt(msg):
            from backend.db_qa.new_intent_classifier import _INSTANCE_ID_RE
            from backend.tools.report_lookup import get_report_status_by_id_fast

            if _INSTANCE_ID_RE.fullmatch(msg):
                logger.info("[GUIDED_STATUS_ID_LOOKUP] id=%r session=%s", msg, session_id)
                result = get_report_status_by_id_fast(msg)
                if result.get("type") == "error":
                    # Exact match only — a well-shaped but non-existent ID
                    # gets the same "no match" wording as an incomplete one.
                    result = {
                        "type": "error",
                        "message": f"No matching Request ID found for '{msg}'. Please enter the complete Request ID.",
                    }
            else:
                # Hex-looking but not a complete/valid shape (e.g. a prefix
                # fragment) — never guess or partially match; do not fall
                # through to report-name matching for this input.
                logger.info("[GUIDED_STATUS_ID_LOOKUP] incomplete id=%r session=%s", msg, session_id)
                result = {
                    "type": "error",
                    "message": f"No matching Request ID found for '{msg}'. Please enter the complete Request ID.",
                }
            if allowed_form_ids is not None:
                from backend.agent import _apply_auth_to_status_result
                result = _apply_auth_to_status_result(result, allowed_form_ids)
            return _from_result(result, intent="get_status", session_id=session_id)

        # Fuzzy-match the input directly against returns.xml — no LLM needed.
        logger.info("[GUIDED_STATUS_LOOKUP] input=%r session=%s", msg, session_id)
        result = get_report_status(msg)
        if allowed_form_ids is not None:
            from backend.agent import _apply_auth_to_status_result
            result = _apply_auth_to_status_result(result, allowed_form_ids)
        return _from_result(result, intent="get_status", session_id=session_id)

    if stage == STAGE_GEN_REPORT:
        # _handle_generate runs find_matching_reports + fuzzy suggestions — no LLM.
        # Instance Generation permission is enforced inside _finalize_generation
        # (single enforcement point, shared with the free-text /chat path).
        logger.info("[GUIDED_GENERATE_LOOKUP] input=%r session=%s", msg, session_id)
        return await _handle_generate(
            report_name=msg,
            reporting_date=None,
            session_id=session_id,
            asp_session=asp_session,
            allowed_form_ids=allowed_form_ids,
            login_id=login_id,
        )

    if stage == STAGE_SCHED_REPORT:
        # _handle_schedule runs find_matching_reports + fuzzy suggestions — no LLM.
        # Scheduling performs instance generation internally, so it requires the
        # same permission — enforced inside _finalize_schedule.
        logger.info("[GUIDED_SCHEDULE_LOOKUP] input=%r session=%s", msg, session_id)
        return _handle_schedule(
            report_ident=msg,
            schedule_date=None,
            schedule_time=None,
            scheduled_datetime=None,
            session_id=session_id,
            allowed_form_ids=allowed_form_ids,
            login_id=login_id,
        )

    if stage == STAGE_CMP_REPORT:
        # _handle_compare runs find_matching_reports + fuzzy suggestions — no LLM.
        logger.info("[GUIDED_COMPARE_LOOKUP] input=%r session=%s", msg, session_id)
        return await _handle_compare(report_ident=msg, session_id=session_id, allowed_form_ids=allowed_form_ids)

    if stage == STAGE_DB_QUERY:
        logger.info("[GUIDED_DB_QUERY] input=%r session=%s", msg, session_id)
        from backend.agent.db_qa_router import (
            check_db_qa_intent, check_new_taxonomy_intent, handle_db_qa_query,
        )
        db_intent, db_params = check_new_taxonomy_intent(msg)
        if not db_intent:
            db_intent, db_params = check_db_qa_intent(msg)
        if db_intent:
            logger.info(
                "[GUIDED_DB_QUERY] XML-QA intent=%s params=%s session=%s",
                db_intent, db_params, session_id,
            )
            db_result = handle_db_qa_query(
                message=msg,
                intent=db_intent,
                params=db_params,
                user_id=login_id or "0",
                role_id="0",
                login_id=login_id,
            )
            # A partial return name (e.g. "cims") can match many returns.
            # The frontend hands off to /chat -> decide() for every message
            # after this one (isGuidedFlow flips off on any non-guided
            # result_type), so the pending-options state must be stashed in
            # agent/__init__.py's _session_context — the same store
            # decide()'s own STEP2 disambiguation branch uses — or decide()
            # has no memory of this prompt and misroutes the user's pick.
            if db_result.get("result_type") == "disambiguation" and session_id:
                from backend.agent import _session_context, STAGE_RETURN_QA
                _session_context[session_id] = {
                    "awaiting":        STAGE_RETURN_QA,
                    "pending_options": db_result.get("options", []),
                    "db_intent":       db_intent,
                    "db_params":       db_params,
                }
            return db_result
        logger.info("[GUIDED_DB_QUERY] no XML-QA match, falling back to SQL agent session=%s", session_id)
        from backend.sql_agent import handle_db_query
        return await handle_db_query(msg, session_id=session_id)

    return _menu(login_id)


def _handle_action_selected(
    action: str,
    session_id: str | None,
    login_id: str | None = None,
) -> dict[str, Any]:
    """Set the first guided stage and return the report-name prompt.

    Defense in depth: even though the frontend only shows buttons for
    _allowed_actions(), a client could still POST a hidden action's label
    directly. Re-check permission here so the guided flow never even starts
    for an action the user can't perform — the actual API-call enforcement
    still lives in _finalize_generation/_finalize_schedule regardless.
    """
    if action in _ACTIONS_REQUIRING_INSTANCE_GENERATION and action not in _allowed_actions(login_id):
        logger.warning(
            "[GUIDED_ACTION_DENY] action=%r login_id=%r session=%s — lacks Instance Generation permission",
            action, login_id, session_id,
        )
        return _build(
            response_text="Sorry, you do not have access to this action.",
            result_type="error",
        )

    if action == "Check report status":
        if session_id:
            _guided_sessions[session_id] = {"stage": STAGE_STATUS_REPORT}
        return _build(
            response_text="Enter the report name, ReturnId, or short name (e.g. CIMS_ROR, R149, RAQ):",
            result_type="guided_input",
            options=[],
        )

    if action == "Generate instance for a report":
        if session_id:
            _guided_sessions[session_id] = {"stage": STAGE_GEN_REPORT}
        return _build(
            response_text="Enter the report name, ReturnId, or short name (e.g. CIMS_FormGPB, R009):",
            result_type="guided_input",
            options=[],
        )

    if action == "Schedule a report":
        if session_id:
            _guided_sessions[session_id] = {"stage": STAGE_SCHED_REPORT}
        return _build(
            response_text="Enter the report name, ReturnId, or short name (e.g. CIMS_RAQ, R162):",
            result_type="guided_input",
            options=[],
        )

    if action == "Perform comparative analysis":
        if session_id:
            _guided_sessions[session_id] = {"stage": STAGE_CMP_REPORT}
        return _build(
            response_text="Enter the report name, ReturnId, or short name to compare (e.g. CIMS_RAQ, R009, RAQ):",
            result_type="guided_input",
            options=[],
        )

    if action == "Retrieve data from database":
        if session_id:
            _guided_sessions[session_id] = {"stage": STAGE_DB_QUERY}
        return _build(
            response_text=(
                "What data would you like to query? Please describe in detail "
                "(include report name, section, and time period).\n"
                "Examples:\n"
                "\u2022 What is the credit equivalent current credit exposure for domestic derivatives from ale?\n"
                "\u2022 Total loan assets from RAQ section 1 domestic latest\n"
                "\u2022 What is the loss provision held on an industry basis from ale?"
            ),
            result_type="guided_input",
            options=[],
        )

    return _menu(login_id)