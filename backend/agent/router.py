"""backend/agent/router.py — decide(): the central intent dispatcher.

Moved out of backend/agent/__init__.py verbatim — no logic changes. This is
the one function deliberately NOT split further: it is tightly coupled to
per-session multi-turn state and doing so safely was out of scope for this
structural pass.
"""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any

from backend.llm_extractor import (
    parse_and_format_date,
    extract_schedule_datetime,
    extract_reporting_and_schedule_datetime,
    _extract_date_from_query,
    _extract_search_terms as extract_search_terms,
    _BROAD_DATE_RE as _DATE_STRIP_RE,
    preprocess_generate_query,
)
from backend import version_config  # noqa: F401  (kept for parity with original import block)
from backend import config as _config
from backend.tools.instance_generator import resolve_return_exact
from backend.tools.report_lookup import find_matching_reports, get_available_instances

from backend.agent.state import *  # noqa: F401,F403
from backend.agent.background_jobs import *  # noqa: F401,F403
from backend.agent.auth_filters import *  # noqa: F401,F403
from backend.agent.conversational import *  # noqa: F401,F403
from backend.agent.report_resolution import *  # noqa: F401,F403
from backend.agent.comparison import *  # noqa: F401,F403
from backend.agent.scheduling import *  # noqa: F401,F403
from backend.agent.generation import *  # noqa: F401,F403

import logging
# Imported as a package reference (not `from ... import extract_intent_and_entities`)
# so that tests patching `backend.agent.extract_intent_and_entities` — matching
# this name's original home as a top-level attribute of backend/agent/__init__.py
# — still take effect here. The module is already in sys.modules by the time any
# of these functions actually run (this module is itself imported FROM
# backend/agent/__init__.py), so this is safe despite looking circular.
import backend.agent as _agent_pkg

logger = logging.getLogger(__name__)


def extract_intent_and_entities(*args, **kwargs):
    return _agent_pkg.extract_intent_and_entities(*args, **kwargs)


async def decide(
    user_query: str,
    session_id: str | None = None,
    asp_session: str | None = None,
    login_id: str | None = None,
    user_id: str | None = None,
    role_id: str | None = None,
    conversation_history: list[dict] | None = None,
) -> dict[str, Any]:
    _decide_start = time.monotonic()
    session = _session_context.get(session_id, {}) if session_id else {}
    lower_q = user_query.strip().lower()

    # ── Debug trace: log raw .NET input — role_id is ALWAYS empty here (resolved later) ──
    from backend.utils.debug import debug_log
    _uid_is_guid = bool(user_id and _SESSION_GUID_RE.match(user_id))
    debug_log(
        "DECIDE — .NET INPUT",
        question=user_query,
        login_id=login_id or "NOT PROVIDED",
        user_id=user_id   or "NOT PROVIDED",
        user_id_type="SESSION GUID — will use login_id instead" if _uid_is_guid else ("real user ID" if _is_real_user_id(user_id) else "sentinel/missing"),
        role_id_from_net="NOT SENT BY .NET — resolved from auth_service",
        session_id=session_id or "none",
        session_state=session.get("awaiting", "NONE"),
    )

    # ── Auth: resolve allowed FormIds for this user ───────────────────────────────
    # None  = no login_id provided — allow all (dev / backward compat)
    # set   = restrict to this user's department forms
    # SECURITY (C-02/H-01 interim fix): REQUIRE_AUTH now defaults to "true".
    # An operator who never sets REQUIRE_AUTH at all (it was previously absent
    # from .env.example, so a fresh deployment could silently ship wide open)
    # now gets the safe, fail-closed behavior by default; a real deployment
    # that intentionally wants unauthenticated access must opt in explicitly
    # with REQUIRE_AUTH=false. This deployment's own .env already sets
    # REQUIRE_AUTH=true, so this flip changes nothing here — it only changes
    # what happens where that variable is left unset.
    _REQUIRE_AUTH: bool = os.getenv("REQUIRE_AUTH", "true").lower() == "true"
    allowed_form_ids: set[str] | None = None
    if login_id:
        from backend.services.auth_service import get_allowed_form_ids as _get_auth
        from backend.services.auth_service import AUTHORIZATION_ENABLED as _AUTH_ENABLED
        allowed_form_ids = _get_auth(login_id)
        if not _AUTH_ENABLED:
            logger.info(
                "[AUTH_BYPASS] Authorization disabled; allowing all forms for login_id=%r session=%s",
                login_id, session_id,
            )
        elif allowed_form_ids is None:
            logger.warning(
                "[AUTH_DENY] User not found: login_id=%r session=%s", login_id, session_id
            )
            return _build(
                intent="unknown",
                report_name=None,
                response_text="Your account was not recognised. Please contact your administrator.",
                result_type="error",
            )
        else:
            logger.info(
                "[AUTH] login_id=%r allowed_forms=%d session=%s",
                login_id, len(allowed_form_ids), session_id,
            )

    elif _REQUIRE_AUTH and os.getenv("AUTHORIZATION_ENABLED", "true").lower() == "true":
        logger.warning(
            "[AUTH_DENY] No login_id provided and REQUIRE_AUTH=true, session=%s", session_id
        )
        return _build(
            intent="unknown",
            report_name=None,
            response_text="Authentication required. Please access this application through the authorised portal.",
            result_type="error",
        )
    # ── Auth: role_id is ALWAYS resolved server-side from XML_User.xml, never
    # taken from the client (C-02 interim fix) ────────────────────────────────
    # SECURITY: role_id used to be honoured as-given whenever the caller (the
    # client, not .NET -- the .NET app never sends roleId) supplied a non-empty
    # value, e.g. POST /chat {"role_id":"101"}. That let any caller assert an
    # arbitrary role -- including the admin role -- for any login_id, which is
    # a privilege-escalation vulnerability independent of whether login_id
    # itself is genuine (login_id remains client-asserted and unverified until
    # the .NET-issued JWT can be cryptographically checked -- see C-02 in
    # doc/CODE_REVIEW_REPORT_2026-09-29.md and doc/CRITICAL_FIXES_LOG.md for
    # what remains unresolved). Whatever role_id the client sent is discarded
    # here and replaced with the server-looked-up value for every downstream
    # handler (DB Q&A, SQL agent, etc.).
    if role_id:
        logger.warning(
            "[AUTH_ROLE_IGNORED] client-supplied role_id=%r discarded; role is always "
            "server-resolved from XML_User.xml. login_id=%r session=%s",
            role_id, login_id, session_id,
        )
    role_id = None
    if login_id:
        from backend.services.auth_service import get_user_role_id as _get_role
        _resolved_role = _get_role(login_id)
        if _resolved_role:
            role_id = _resolved_role
            logger.info(
                "[AUTH_ROLE] role_id resolved from XML: login_id=%r -> role_id=%r session=%s",
                login_id, role_id, session_id,
            )

    # ── Debug trace: log effective identity AFTER auth_service resolution ────
    debug_log(
        "DECIDE — RESOLVED IDENTITY",
        login_id=login_id or "NOT PROVIDED",
        user_id=user_id   or "NOT PROVIDED",
        role_id_resolved=role_id or "UNRESOLVED (no login_id or user not found)",
        role_source=("auth_service (XML_User.xml)" if login_id else "not resolved — no login_id"),
    )

    # Persist the live cookie so staged flows (multi-turn generate) can use it.
    # SECURITY (H-04): bind the cached credential to the login_id that
    # supplied it. Without this, knowing/guessing a victim's session_id
    # alone was enough to retrieve their cached .NET session cookie on a
    # later request -- session_id is a client-chosen conversation key (see
    # doc/CRITICAL_FIXES_LOG.md's H-04 entry), not a credential. login_id is
    # resent on every single frontend call identically to session_id/
    # asp_session (verified in frontend/src/App.jsx: all three of
    # submitMessage/submitGuidedStep/handleGuidedAction send it every time),
    # so a legitimate staged multi-turn flow (e.g. "generate X" -> bot asks
    # for a date -> user's date-only reply) always presents the same
    # login_id it started with, and is unaffected by this check.
    # NOTE: login_id itself remains client-supplied and unverified (same
    # standing caveat as C-02) -- this closes the "session_id alone is
    # enough" hijack path, it is not cryptographic identity verification.
    if asp_session and session_id:
        session["asp_session"] = asp_session
        session["asp_session_login_id"] = login_id
        _session_context[session_id] = session

    # Prefer the freshly-forwarded cookie; fall back to one stored earlier in
    # session ONLY if it was cached under this same login_id.
    effective_asp = asp_session or (
        session.get("asp_session") if session.get("asp_session_login_id") == login_id else None
    )
    logger.info("decide: asp_session=%s effective=%s",
                "provided" if asp_session else "MISSING",
                "yes" if effective_asp else "NONE — will use .env fallback")

    # -- Explicit reset -------------------------------------------------------
    is_reset = any(kw in lower_q for kw in _NEW_REPORT_KWS)
    if is_reset and session_id:
        _session_context.pop(session_id, None)
        session = {}

    # -- Status: date selection -----------------------------------------------
    if not is_reset and session.get("awaiting") == STAGE_DATE:
        # IMPORTANT: check for the formatted instance label FIRST.
        # Labels are now "Initiated On: X | Reporting Date: Y", which no longer
        # trips _looks_like_new_query — but the OLD "Generated On:" spelling
        # does (the word "Generated" stem-matches 'gene' in _GEN_STEMS), and
        # _parse_dtc_from_label still accepts it for labels sitting in a user's
        # saved chat history. So the label-first order still matters.
        # Same class of issue as STAGE_CMP_FILE with the word "run".
        dtc_from_label = _parse_dtc_from_label(user_query)
        if dtc_from_label:
            form_id     = session["pending_form_id"]
            return_name = session["pending_return_name"]
            result = _get_instance_by_dtc_fast_with_bg_job(
                form_id, dtc_from_label, return_name, allowed_form_ids,
            )
            if result["type"] == "date_not_found":
                available = get_available_instances(form_id)
                return _build(
                    intent="get_status",
                    report_name=return_name,
                    response_text=(
                        f"'{user_query.strip()}' did not match any instance for {return_name}. "
                        "Please select one of the available instances:"
                    ),
                    result_type="date_selection",
                    options=[i["label"] for i in available],
                    instances_data=[{"label": i["label"], "status": i["status"]} for i in available],
                )
            return _ask_another_date(result, form_id, return_name, session_id)
        elif _looks_like_new_query(user_query):
            if session_id:
                _session_context.pop(session_id, None)
            session = {}
        else:
            # Guard: check if input is a plausible date before treating it as one.
            # Inputs like "hey" or "do one thingg" are not dates — handle them gracefully.
            if not _is_plausible_date(user_query):
                try:
                    re_extracted = await extract_intent_and_entities(user_query)
                    re_intent = re_extracted.get("intent", "unknown")
                except Exception as exc:
                    logger.warning(
                        "[INTENT_EXTRACT_FAIL] re-extraction during STAGE_DATE fallback failed "
                        "session=%s | error=%s", session_id, exc,
                    )
                    re_intent = "unknown"

                if re_intent in ("get_status", "generate_instance"):
                    # Looks like a new query — reset stage and fall through to normal flow
                    if session_id:
                        _session_context.pop(session_id, None)
                    session = {}
                else:
                    # Truly unrelated input — return a polite fallback, keep stage intact
                    return _build(
                        intent="unknown",
                        report_name=None,
                        response_text=(
                            "Sorry, I can only help with report status or instance generation. "
                            "Please select one of the available dates to continue, or say "
                            "\"new report\" to start over."
                        ),
                    )
            else:
                form_id     = session["pending_form_id"]
                return_name = session["pending_return_name"]

                # Fallback: user typed a raw date string
                result = _get_instance_by_date_fast_with_bg_job(
                    form_id, user_query.strip(), return_name, allowed_form_ids,
                )

                if result["type"] == "date_not_found":
                    available = get_available_instances(form_id)
                    return _build(
                        intent="get_status",
                        report_name=return_name,
                        response_text=(
                            f"'{user_query.strip()}' did not match any instance for {return_name}. "
                            "Please select one of the available instances:"
                        ),
                        result_type="date_selection",
                        options=[i["label"] for i in available],
                        instances_data=[{"label": i["label"], "status": i["status"]} for i in available],
                    )
                return _ask_another_date(result, form_id, return_name, session_id)

    # -- Status: previous-dates yes/no prompt -----------------------------------
    if not is_reset and session.get("awaiting") == STAGE_PREV_DATES:
        if _looks_like_new_query(user_query):
            if session_id:
                _session_context.pop(session_id, None)
            session = {}
        else:
            form_id         = session.get("pending_form_id", "")
            return_name     = session.get("pending_return_name", "")
            other_instances = session.get("pending_other_instances", [])
            from backend.guided import normalize_confirmation
            if normalize_confirmation(user_query) == "YES":
                if session_id:
                    _session_context[session_id] = {
                        "awaiting":            STAGE_DATE,
                        "pending_form_id":     form_id,
                        "pending_return_name": return_name,
                    }
                return _build(
                    intent="get_status", report_name=return_name,
                    response_text=f"Select a reporting instance for '{return_name}':",
                    result_type="date_selection",
                    options=[i["label"] for i in other_instances],
                    instances_data=[{"label": i["label"], "status": i["status"]} for i in other_instances],
                )
            else:  # "No" or anything non-yes
                if session_id:
                    _session_context.pop(session_id, None)
                return _build(
                    intent="get_status", report_name=return_name,
                    response_text="Alright! Let me know if you need anything else.",
                    result_type="final",
                )

    # -- Status: run selection (same date, multiple runs) ----------------------
    if not is_reset and session.get("awaiting") == STAGE_RUN:
        if _looks_like_new_query(user_query):
            if session_id:
                _session_context.pop(session_id, None)
            session = {}
        else:
            pending_runs: list[dict] = session.get("pending_runs", [])
            raw_input = user_query.strip()

            selected_run: dict | None = None
            if raw_input.isdigit():
                idx = int(raw_input) - 1
                if 0 <= idx < len(pending_runs):
                    selected_run = pending_runs[idx]
                else:
                    opts_text = "\n".join(
                        f"{i + 1}. {r['label']}" for i, r in enumerate(pending_runs)
                    )
                    return _build(
                        intent="get_status",
                        report_name=session.get("pending_return_name"),
                        response_text=(
                            f"Please enter a number between 1 and {len(pending_runs)}.\n\n"
                            f"{opts_text}"
                        ),
                        result_type="run_selection",
                        options=[r["label"] for r in pending_runs],
                    )

            if selected_run is None:
                raw_lower = raw_input.lower()
                selected_run = next(
                    (r for r in pending_runs if raw_lower in r["label"].lower()),
                    pending_runs[-1],  # default: most recent run
                )

            return_name    = session.get("pending_return_name", "")
            reporting_date = session.get("pending_reporting_date", "")
            if session_id:
                _session_context.pop(session_id, None)

            return _build(
                intent="get_status",
                report_name=return_name,
                response_text=(
                    f"{return_name}\n"
                    f"Reporting Date : {reporting_date}\n"
                    f"Run Date/Time  : {selected_run.get('dtc', '')}\n"
                    f"Status         : {selected_run.get('status', '')}"
                ),
                result_type="final",
            )

    # -- Status: disambiguation -----------------------------------------------
    if not is_reset and session.get("awaiting") == STAGE_REPORT:
        # If user sends a fresh query, escape the staged flow
        if _looks_like_new_query(user_query):
            if session_id:
                _session_context.pop(session_id, None)
            session = {}
        else:
            pending_options: list[str] = session.get("pending_options", [])
            raw_input = user_query.strip()

            # Resolve numeric selection ("1", "2", ...)
            resolved_name: str | None = None
            if raw_input.isdigit():
                idx = int(raw_input) - 1
                if 0 <= idx < len(pending_options):
                    resolved_name = pending_options[idx]
                else:
                    # Out-of-range number -- re-display options
                    opts_text = "\n".join(f"{i + 1}. {n}" for i, n in enumerate(pending_options))
                    return _build(
                        intent="get_status", report_name=None,
                        response_text=(
                            f"Please enter a number between 1 and {len(pending_options)}.\n\n"
                            f"{opts_text}"
                        ),
                        result_type="disambiguation",
                        options=pending_options,
                    )

            if resolved_name is None:
                # Keyword / partial selection: try to find the option that best matches.
                # An exact (case-insensitive) match always wins first — e.g. selecting
                # "CIMS_LR (Quarterly)" must never resolve to a shorter, unrelated
                # option like "LR (Quarterly)" just because it appears earlier in the
                # list and the two strings happen to overlap as substrings.
                raw_lower = raw_input.lower()
                exact_match = next(
                    (name for name in pending_options if name.lower() == raw_lower),
                    None,
                )
                if exact_match:
                    resolved_name = exact_match
                else:
                    # No exact match: among substring matches, prefer the longest
                    # (most specific) option rather than the first one in list order.
                    substring_matches = [
                        name for name in pending_options
                        if raw_lower in name.lower() or name.lower() in raw_lower
                    ]
                    resolved_name = max(substring_matches, key=len) if substring_matches else raw_input

            if session_id:
                _session_context.pop(session_id, None)
            auth_err = _check_name_auth(resolved_name, allowed_form_ids, "get_status")
            if auth_err:
                return auth_err
            result = _get_status_exact_fast_with_bg_job(resolved_name, allowed_form_ids)
            if allowed_form_ids is not None:
                result = _apply_auth_to_status_result(result, allowed_form_ids)
            return _from_result(result, intent="get_status", session_id=session_id)

    # -- DB Q&A (e.g. next reporting date): disambiguation (user picks a return) --
    if not is_reset and session.get("awaiting") == STAGE_RETURN_QA:
        # A reply to "which return did you mean?" is normally just a bare
        # name or a number — but the user may instead type a brand-new,
        # self-contained question (e.g. "what is the next reporting date
        # for R018"). _looks_like_new_query() only recognizes status/
        # generate/schedule phrasing, so it misses that case and this
        # message would otherwise be forced through keyword-matching
        # against the STALE pending_options list, silently answering with
        # the wrong return. Re-run the db_qa classifier on the raw message
        # first: if it independently resolves to its OWN complete intent
        # (i.e. it already contains a concrete return name/id and isn't
        # just answering the pending prompt), treat this as a fresh
        # question and drop the stale disambiguation instead.
        from backend.agent.db_qa_router import check_new_taxonomy_intent, check_db_qa_intent
        _fresh_db_intent, _fresh_db_params = check_new_taxonomy_intent(user_query)
        if not _fresh_db_intent:
            _fresh_db_intent, _fresh_db_params = check_db_qa_intent(user_query)
        _looks_fresh = bool(_fresh_db_intent) and bool((_fresh_db_params or {}).get("target_return"))

        if _looks_like_new_query(user_query) or _looks_fresh:
            if session_id:
                _session_context.pop(session_id, None)
            session = {}
            if _looks_fresh:
                # Re-enter decide() as a normal fresh query so it goes
                # through the full STEP2 QA routing path.
                return await decide(
                    user_query, session_id=session_id, asp_session=asp_session,
                    login_id=login_id, user_id=user_id, role_id=role_id,
                    conversation_history=conversation_history,
                )
        else:
            pending_qa_options: list[str] = session.get("pending_options", [])
            raw_qa_input = user_query.strip()

            resolved_qa_name: str | None = None
            if raw_qa_input.isdigit():
                idx = int(raw_qa_input) - 1
                if 0 <= idx < len(pending_qa_options):
                    resolved_qa_name = pending_qa_options[idx]
                else:
                    opts_text = "\n".join(f"{i + 1}. {n}" for i, n in enumerate(pending_qa_options))
                    return _build(
                        intent=session.get("db_intent", "next_reporting_date"), report_name=None,
                        response_text=(
                            f"Please enter a number between 1 and {len(pending_qa_options)}.\n\n"
                            f"{opts_text}"
                        ),
                        result_type="disambiguation",
                        options=pending_qa_options,
                    )

            if resolved_qa_name is None:
                raw_qa_lower = raw_qa_input.lower()
                keyword_qa_match = next(
                    (name for name in pending_qa_options if raw_qa_lower in name.lower() or name.lower() in raw_qa_lower),
                    None,
                )
                resolved_qa_name = keyword_qa_match if keyword_qa_match else raw_qa_input

            db_intent = session.get("db_intent", "next_reporting_date")
            db_params = dict(session.get("db_params") or {})
            db_params["target_return"] = resolved_qa_name
            if session_id:
                _session_context.pop(session_id, None)

            from backend.agent.db_qa_router import handle_db_qa_query
            final_user_id = user_id if _is_real_user_id(user_id) else (login_id or "0")
            final_role_id = role_id if role_id and role_id != "0" else "0"
            # H-05: handle_db_qa_query is a synchronous function that can
            # reach the beautifier's blocking requests.post() (up to 120s) --
            # run it in a worker thread so it doesn't stall every other
            # in-flight request on this process.
            return await asyncio.to_thread(
                handle_db_qa_query,
                message=resolved_qa_name,
                intent=db_intent,
                params=db_params,
                user_id=final_user_id,
                role_id=final_role_id,
                beautify=True,
                # Was hardcoded to "phi3:mini" here, silently ignoring the
                # configured APP_DB_BEAUTIFY_MODEL env var entirely — phi3:mini
                # isn't even installed on this deployment's remote Ollama
                # proxy (see .env comment / doc/INTENT_GAP_ANALYSIS.md), so
                # beautify would degrade to raw output the moment
                # APP_DB_ENABLE_BEAUTIFY is turned on, no matter what the env
                # var said. Reading the configured value instead.
                model=_config.APP_DB_BEAUTIFY_MODEL,
                login_id=login_id,
            )

    # -- Generate: disambiguation (user picks a report) -----------------------
    if not is_reset and session.get("awaiting") == STAGE_GEN_REPORT:
        # If user sends a status query, escape to a fresh flow
        if _looks_like_new_query(user_query) and _STATUS_KW_RE.search(user_query):
            if session_id:
                _session_context.pop(session_id, None)
            session = {}
        else:
            pending_gen_options: list[str] = session.get("pending_options", [])
            raw_gen_input = user_query.strip()

            # Resolve numeric selection ("1", "2", ...)
            resolved_gen_name: str | None = None
            if raw_gen_input.isdigit():
                idx = int(raw_gen_input) - 1
                if 0 <= idx < len(pending_gen_options):
                    resolved_gen_name = pending_gen_options[idx]
                else:
                    opts_text = "\n".join(f"{i + 1}. {n}" for i, n in enumerate(pending_gen_options))
                    return _build(
                        intent="generate_instance", report_name=None,
                        response_text=opts_text,
                        result_type="disambiguation",
                        options=pending_gen_options,
                    )

            if resolved_gen_name is None:
                # Keyword/partial match against stored options
                raw_lower = raw_gen_input.lower()
                keyword_match = next(
                    (name for name in pending_gen_options if raw_lower in name.lower() or name.lower() in raw_lower),
                    None,
                )
                resolved_gen_name = keyword_match if keyword_match else raw_gen_input

            ret = resolve_return_exact(resolved_gen_name)
            if session_id:
                _session_context.pop(session_id, None)
            if not ret:
                return _build(
                    intent="generate_instance", report_name=None,
                    response_text=f"Report '{resolved_gen_name}' not found. Please try again.",
                    result_type="error",
                )
            auth_err = _check_name_auth(resolved_gen_name, allowed_form_ids, "generate_instance")
            if auth_err:
                return auth_err
            # If a reporting_date was pre-extracted and stored in session,
            # skip the date prompt and go directly to generation.
            stored_date = session.get("pending_reporting_date")
            if stored_date:
                logger.info(
                    "[AUTO_CONTINUE_GENERATION] report=%r date=%r session=%s — skipping date prompt",
                    ret["name"], stored_date, session_id,
                )
                return await _finalize_generation(ret, stored_date, session_id, effective_asp, login_id)
            # No pre-extracted date — ask the user for it.
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

    # -- Generate: date entry -------------------------------------------------
    if not is_reset and session.get("awaiting") == STAGE_GEN_DATE:
        if _looks_like_new_query(user_query):
            if session_id:
                _session_context.pop(session_id, None)
            session = {}
        else:
            # Extract date via regex so "the date is 30-Jun-2022" works too
            date_match = _DATE_RE.search(user_query)
            if date_match:
                date_str = date_match.group(1)
            else:
                # Normalize any natural format (e.g. 31/03/2021, 2021-03-31, "31 April 2026")
                date_str = parse_and_format_date(user_query.strip())
                if not date_str:
                    # parse_and_format_date failed — pass raw input to validator
                    # which will produce a meaningful error message
                    date_str = user_query.strip()
            logger.debug("[DATE_NORMALIZED] raw=%r → normalized=%r", user_query.strip(), date_str)
            return await _handle_gen_date(date_str, session, session_id, effective_asp, login_id)

    # -- Schedule: re-enter report name after "Change Data" --------------------
    if not is_reset and session.get("awaiting") == STAGE_SCHED_NAME:
        if session_id:
            _session_context.pop(session_id, None)
        return _handle_schedule(user_query.strip(), None, None, None, session_id, allowed_form_ids, login_id, None)

    # -- Schedule: disambiguation (user picks a report) -----------------------
    if not is_reset and session.get("awaiting") == STAGE_SCHED_REPORT:
        if _looks_like_new_query(user_query):
            if session_id:
                _session_context.pop(session_id, None)
            session = {}
        else:
            pending_sched_options: list[str] = session.get("pending_options", [])
            raw_sched_input = user_query.strip()

            resolved_sched_name: str | None = None
            if raw_sched_input.isdigit():
                idx = int(raw_sched_input) - 1
                if 0 <= idx < len(pending_sched_options):
                    resolved_sched_name = pending_sched_options[idx]
                else:
                    opts_text = "\n".join(f"{i + 1}. {n}" for i, n in enumerate(pending_sched_options))
                    return _build(
                        intent="schedule_report", report_name=None,
                        response_text=(
                            f"Please enter a number between 1 and {len(pending_sched_options)}.\n\n"
                            f"{opts_text}"
                        ),
                        result_type="disambiguation", options=pending_sched_options,
                    )

            if resolved_sched_name is None:
                raw_lower = raw_sched_input.lower()
                keyword_match = next(
                    (name for name in pending_sched_options
                     if raw_lower in name.lower() or name.lower() in raw_lower),
                    None,
                )
                resolved_sched_name = keyword_match if keyword_match else raw_sched_input

            saved_reporting_date = session.get("sched_reporting_date")
            saved_sched_date = session.get("sched_schedule_date")
            saved_sched_time = session.get("sched_schedule_time")
            saved_sched_dt   = session.get("sched_scheduled_dt")

            ret = resolve_return_exact(resolved_sched_name)
            if session_id:
                _session_context.pop(session_id, None)
            if not ret:
                return _build(
                    intent="schedule_report", report_name=None,
                    response_text=f"Report '{resolved_sched_name}' not found. Please try again.",
                    result_type="error",
                )
            auth_err = _check_name_auth(resolved_sched_name, allowed_form_ids, "schedule_report")
            if auth_err:
                return auth_err
            return _finalize_schedule(ret, saved_reporting_date, saved_sched_date, saved_sched_time, saved_sched_dt, session_id, login_id)

    # -- Schedule: reporting-date entry ----------------------------------------
    if not is_reset and session.get("awaiting") == STAGE_SCHED_RPT_DATE:
        if _looks_like_new_query(user_query):
            if session_id:
                _session_context.pop(session_id, None)
            session = {}
        else:
            date_str = parse_and_format_date(user_query.strip())
            if not date_str:
                # parse_and_format_date failed — pass raw input to the validator
                # so it can produce a specific "cannot parse" error message.
                date_str = user_query.strip()
            sched_ret = {
                "form_id":     session["sched_form_id"],
                "name":        session["sched_return_name"],
                "frequency":   session.get("sched_frequency", ""),
                "period_name": session.get("sched_period_name", ""),
            }
            saved_sched_date = session.get("sched_schedule_date")
            saved_sched_time = session.get("sched_schedule_time")
            if session_id:
                _session_context.pop(session_id, None)
            return _finalize_schedule(
                sched_ret, date_str, saved_sched_date, saved_sched_time, None,
                session_id, login_id,
            )

    # -- Schedule: date+time entry --------------------------------------------
    if not is_reset and session.get("awaiting") == STAGE_SCHED_DT:
        if _looks_like_new_query(user_query):
            if session_id:
                _session_context.pop(session_id, None)
            session = {}
        else:
            sched_info    = extract_schedule_datetime(user_query)
            # Merge freshly extracted values with any partially-saved ones
            schedule_date = sched_info["schedule_date"] or session.get("sched_schedule_date")
            schedule_time = sched_info["schedule_time"] or session.get("sched_schedule_time")
            reporting_date = session.get("sched_reporting_date")
            scheduled_dt: str | None = None
            if schedule_date and schedule_time:
                try:
                    from datetime import datetime as _sdt
                    scheduled_dt = _sdt.strptime(
                        f"{schedule_date} {schedule_time}", "%d-%b-%Y %H:%M"
                    ).strftime("%Y-%m-%dT%H:%M:00")
                except ValueError:
                    pass
            sched_ret = {
                "form_id":     session["sched_form_id"],
                "name":        session["sched_return_name"],
                "frequency":   session.get("sched_frequency", ""),
                "period_name": session.get("sched_period_name", ""),
            }
            if session_id:
                _session_context.pop(session_id, None)
            return _finalize_schedule(sched_ret, reporting_date, schedule_date, schedule_time, scheduled_dt, session_id, login_id)

    # -- Schedule: user confirmation (Schedule / Change Data) ------------------
    if not is_reset and session.get("awaiting") == STAGE_SCHED_CONFIRM:
        raw = user_query.strip().lower()
        sched_name = session.get("sched_return_name", "")
        sched_reporting_date = session.get("sched_reporting_date")
        sched_date = session.get("sched_schedule_date")
        sched_time = session.get("sched_schedule_time")
        sched_dt   = session.get("sched_scheduled_dt")
        if "change" in raw:
            if session_id:
                _session_context[session_id] = {"awaiting": STAGE_SCHED_NAME}
            logger.info(
                "[SCHEDULE_CHANGE] user requested data change session=%s", session_id,
            )
            return _build(
                intent="schedule_report",
                report_name=None,
                response_text=(
                    "No problem! Let’s start over.\n"
                    "Please provide the report name for scheduling."
                ),
                result_type="sched_awaiting_name",
            )
        if raw == "schedule":
            # Explicit "Schedule" button click → finalize
            sched_form_id = session.get("sched_form_id", "")
            if session_id:
                _session_context.pop(session_id, None)
            logger.info(
                "[SCHEDULE_CONFIRMED] report=%r reporting_date=%s date=%s time=%s session=%s",
                sched_name, sched_reporting_date, sched_date, sched_time, session_id,
            )
            # Append confirmed schedule entry to SchedulerQueue.xml
            from backend.services.scheduler_queue_service import append_schedule_entry
            _sq_ok, _sq_id = append_schedule_entry(
                report_name=sched_name,
                form_id=sched_form_id,
                reporting_date=sched_reporting_date or "",
                schedule_dt=sched_dt or f"{sched_date} {sched_time}",
                user_id=login_id or "",
            )
            if _sq_ok:
                logger.info(
                    "[SCHEDULER_QUEUE] Entry appended: id=%s report=%r session=%s",
                    _sq_id, sched_name, session_id,
                )
            else:
                logger.error(
                    "[SCHEDULER_QUEUE] Failed to append entry for report=%r session=%s",
                    sched_name, session_id,
                )
            return _build(
                intent="schedule_report",
                report_name=sched_name,
                response_text=(
                    f"Schedule confirmed:\n"
                    f"Report          : {sched_name}\n"
                    f"Reporting Date  : {sched_reporting_date}\n"
                    f"Schedule Date   : {sched_date}\n"
                    f"Schedule Time   : {sched_time}\n"
                    f"Scheduled       : {sched_dt or f'{sched_date} {sched_time}'}"
                ),
                result_type="schedule_parsed",
                scheduled_datetime=sched_dt,
                schedule_date=sched_date,
                schedule_time=sched_time,
                reporting_date_out=sched_reporting_date,
            )
        # Anything else — including an unrelated free-text query — is NOT a
        # confirmation. Do not execute, do not process it as a new query;
        # re-prompt with the same two options and leave the pending
        # confirmation session state untouched so the buttons still work.
        logger.info(
            "[SCHEDULE_CONFIRM_IGNORED] non-option input=%r while awaiting confirmation session=%s",
            user_query, session_id,
        )
        return _build(
            intent="schedule_report",
            report_name=sched_name,
            response_text="Please confirm the schedule first by selecting **Schedule** or **Change Data**.",
            result_type="sched_confirm",
            options=["Schedule", "Change Data"],
        )

    # -- Compare: report disambiguation ----------------------------------------
    if not is_reset and session.get("awaiting") == STAGE_CMP_REPORT:
        # Escape if the user starts a fresh compare query (e.g. "compare HDFC" while
        # ALE disambiguation is pending) OR any other new-intent query.
        # _fuzzy_has_compare covers: compare, comparative, comparative analysis, comparison.
        if _looks_like_new_query(user_query) or _fuzzy_has_compare(user_query):
            if session_id:
                _session_context.pop(session_id, None)
            session = {}
        else:
            pending: list[str] = session.get("pending_options", [])
            raw = user_query.strip()
            selected: str | None = None
            if raw.isdigit():
                idx = int(raw) - 1
                if 0 <= idx < len(pending):
                    selected = pending[idx]
            if selected is None:
                raw_lower = raw.lower()
                selected = next((n for n in pending if raw_lower in n.lower()), None)
            if selected is None:
                opts_text = "\n".join(f"{i + 1}. {n}" for i, n in enumerate(pending))
                return _build(
                    intent="compare_reports", report_name=None,
                    response_text=(
                        f"Please pick a number between 1 and {len(pending)}.\n\n{opts_text}"
                    ),
                    result_type="disambiguation", options=pending,
                )
            auth_err = _check_name_auth(selected, allowed_form_ids, "compare_reports")
            if auth_err:
                return auth_err
            return await _compare_with_name(selected, session_id)

    # -- Compare: instance file selection --------------------------------------
    # NOTE: use is_reset (not _looks_like_new_query) here — option labels contain
    # the word "run" which falsely triggers the generate-keyword detector.
    # However, a new compare/status/generate query should always start fresh.
    if not is_reset and session.get("awaiting") == STAGE_CMP_FILE:
        if _fuzzy_has_compare(user_query) or _looks_like_new_query(user_query):
            if session_id:
                _session_context.pop(session_id, None)
            session = {}
        else:
            return await _run_comparison(session, user_query, session_id)

    # ─────────────────────────────────────────────────────────────────────────
    # HIERARCHICAL INTENT FAST-PATHS
    #
    # Priority order (each tier blocks all lower tiers — no overlap):
    #   STEP 0 — Conversational: greetings / quick acknowledgements
    #   STEP 1 — Workflow  : status / generate / schedule / compare
    #   STEP 2 — App Q&A   : XML metadata — users, depts, roles, logs … (before SQL)
    #   STEP 3 — SQL agent : Oracle analytics, banking metrics (only when QA misses)
    #   STEP 4 — LLM       : fallback for everything not caught above
    #
    # IMPORTANT: STEP 2 (XML-QA) runs before STEP 3 (SQL).
    # Entity domain wins over action verb — "how many departments" → XML-QA,
    # not SQL, even though it contains the word "how many".
    # ─────────────────────────────────────────────────────────────────────────
    if not _is_staged_session(session) and not is_reset:
        convo_reply = _get_conversational_response(user_query)
        if convo_reply is not None:
            logger.info('[INTENT:STEP0] conversational reply session=%s', session_id)
            return _build(
                intent='conversational', report_name=None,
                response_text=convo_reply,
                result_type='final',
            )

        # A "between DATE and DATE" range is a strong, unambiguous signal
        # that this is a DB Q&A range question (reports_filed_in_range /
        # reports_upcoming_in_range), never a single-report workflow
        # request — get_status/generate_instance/schedule_report all take
        # at most ONE date, never a range. Without this override, a stem
        # like "generated"/"filed" (which _fuzzy_has_generate/_fuzzy_has_status
        # also match as report-workflow keywords) would incorrectly send
        # "what XBRL returns generated between 31-Jan-2026 and 15-Mar-2026"
        # into the generate-instance workflow instead of DB Q&A.
        from backend.db_qa.new_intent_classifier import _DATE_RANGE_RE, _INSTANCE_ID_RE, classify_new
        from backend.db_qa.intents.taxonomy import Intent as _Intent
        _has_date_range = bool(_DATE_RANGE_RE.search(user_query))

        # A submission-log GUID id in the question ("what is the status of
        # f7593ff72d644345865eaa84ae0b3073") is a status-by-id lookup —
        # it must use the SAME rich status-checking pipeline as a
        # report-name lookup (error extraction, 4000-series gating, the
        # "check another reporting date" follow-up), not db_qa's plain
        # summary. A GUID appearing anywhere in the question is
        # distinctive enough (32 hex chars) to trust as this signal
        # regardless of surrounding wording. See the STEP-1 workflow
        # block below, which branches on this BEFORE the generic
        # name-search status path (a bare GUID has no report name for
        # find_matching_reports() to match, so it must never reach that
        # branch).
        _has_guid_status = bool(_INSTANCE_ID_RE.search(user_query))

        # A monthly filing-status question ("what's my XBRL filing status
        # for June 2025?", "non-XBRL status for this month") is DB Q&A
        # (MONTHLY_FILING_STATUS), never the single-report status workflow
        # — but it has no two-date range for _has_date_range to catch, and
        # "filing status"/"status" is exactly what _fuzzy_has_status also
        # matches as a report-workflow keyword. Without this override every
        # monthly-status question was being sent into the single-report
        # get_status workflow (which then either fails auth against a
        # resolved single report or fuzzy-matches an unrelated report name)
        # instead of ever reaching STEP 2 (DB Q&A). Uses the regex tier
        # only (classify_new, not the async semantic-tiers classifier) —
        # cheap and synchronous, matching _has_date_range's own cost profile
        # for this pre-STEP-1 gate.
        # GENERALIZED, was two one-off special cases (MONTHLY_FILING_STATUS,
        # then SUBMISSION_*) added independently as each was discovered —
        # doc/INTENT_GAP_ANALYSIS.md's ongoing audit kept finding MORE common
        # words ("details", "info", "execute") that _fuzzy_has_status/
        # _fuzzy_has_generate's short stems ('deta', 'info', 'exec', ...)
        # deliberately match as status/generate synonyms, but which also
        # legitimately appear in everyday db_qa phrasing ("details of my
        # role", "is there a role called Executive") — one-off exclusions
        # don't scale to every future collision. classify_new() is a
        # confident, structural REGEX match (not a fuzzy/keyword heuristic
        # like the _fuzzy_has_* functions below it) — verified it stays
        # silent (None) on every genuine report-workflow phrasing tested
        # ("what is the status of my raq report", "generate the DBR01
        # report", "schedule DBR01...", etc.), so trusting ANY of its
        # matches over the fuzzy workflow gate is safe, not just for the
        # two intents previously special-cased one at a time.
        _probe_db_qa_intent, _, _ = classify_new(user_query)
        _looks_like_db_qa_shape = _probe_db_qa_intent is not None

        _has_workflow = not _has_date_range and not _looks_like_db_qa_shape and (
            _has_guid_status
            or _fuzzy_has_status(user_query)
            or _fuzzy_has_generate(user_query)
            or _fuzzy_has_schedule(user_query)
            or bool(_CMP_KW_RE.search(user_query))
        )
        _has_sql = bool(_DB_QUERY_KW_RE.search(user_query))

        # A confident match against the deterministic db_qa classifiers means
        # this is a real data question, not small talk — never let the LLM
        # conversational classifier (flaky on domain phrasing, e.g. it has
        # mis-labelled "what is my role?" as "acknowledgement") override that.
        _looks_like_db_qa = False
        if convo_reply is None and not _has_workflow and not _has_sql:
            from backend.agent.db_qa_router import check_new_taxonomy_intent, check_db_qa_intent
            _probe_intent, _ = check_new_taxonomy_intent(user_query)
            if not _probe_intent:
                _probe_intent, _ = check_db_qa_intent(user_query)
            _looks_like_db_qa = bool(_probe_intent)

        if convo_reply is None and not _has_workflow and not _has_sql and not _looks_like_db_qa:
            convo_category = await _classify_conversational(
                user_query,
                history=conversation_history,
            )
            if convo_category is not None:
                convo_reply = _get_conversational_response_for_category(convo_category)
                if convo_reply is not None:
                    logger.info(
                        '[INTENT:STEP0] conversational classifier reply category=%s session=%s',
                        convo_category, session_id,
                    )
                    return _build(
                        intent='conversational', report_name=None,
                        response_text=convo_reply,
                        result_type='final',
                    )

        # ── STEP 1 : Workflow ─────────────────────────────────────────────────
        # Any workflow keyword blocks SQL and QA fast-paths entirely.
        if _has_workflow:
            logger.info("[INTENT:STEP1] workflow signal detected session=%s", session_id)

            # ── Status-by-id fast-path: a known InstanceLog GUID always wins ──
            # "what is the status of <id>" already names the EXACT submission —
            # skip name search/disambiguation entirely and run the same
            # error-extraction/4000-series/"other reporting dates" pipeline a
            # report-name lookup gets, just seeded from the known row instead
            # of a name-driven "pick the latest instance" search.
            if _has_guid_status:
                _guid_match = _INSTANCE_ID_RE.search(user_query)
                _instance_id = _guid_match.group(0) if _guid_match else None
                if _instance_id:
                    logger.info(
                        "[INTENT:STEP1] status-by-id fast-path id=%s session=%s",
                        _instance_id, session_id,
                    )
                    result = _get_status_by_id_fast_with_bg_job(_instance_id, allowed_form_ids)
                    if allowed_form_ids is not None:
                        result = _apply_auth_to_status_result(result, allowed_form_ids)
                    return _from_result(result, intent="get_status", session_id=session_id)

            # ── Schedule fast-path: schedule beats generate / status ──────────
            # When schedule keyword is detected (and no status signal overrides),
            # extract report name + datetime deterministically — skip LLM entirely.
            # This ensures "schedule instance generation for CIMS_RAQ at 10 am"
            # always routes to schedule_report, never generate_instance.
            if _fuzzy_has_schedule(user_query) and not _fuzzy_has_status(user_query):
                _sched_terms = _extract_schedule_search_terms(user_query)
                # Handles messages that state BOTH dates explicitly, e.g.
                # "...reporting date 31-Mar-2026...schedule it to execute on
                # 31-Dec-2026 at 16:00" — falls back to single-date behaviour
                # (schedule_date/time only) when no reporting-date phrasing
                # is present, so ordinary "schedule X for 31-Dec-2026" is unaffected.
                _sched_dt    = extract_reporting_and_schedule_datetime(user_query)
                logger.info(
                    "[INTENT:STEP1] schedule fast-path report=%r reporting_date=%r date=%r time=%r session=%s",
                    _sched_terms, _sched_dt.get("reporting_date"), _sched_dt.get("schedule_date"),
                    _sched_dt.get("schedule_time"), session_id,
                )
                return _handle_schedule(
                    report_ident=_sched_terms,
                    schedule_date=_sched_dt.get("schedule_date"),
                    schedule_time=_sched_dt.get("schedule_time"),
                    scheduled_datetime=_sched_dt.get("scheduled_datetime"),
                    session_id=session_id,
                    allowed_form_ids=allowed_form_ids,
                    login_id=login_id,
                    reporting_date=_sched_dt.get("reporting_date"),
                )

            if _fuzzy_has_status(user_query):
                raw_query = user_query.strip()
                extracted_query = _extract_status_search_terms(raw_query)
                if extracted_query:
                    matches = find_matching_reports(extracted_query)
                    if matches:
                        logger.info(
                            "[INTENT:STEP1] status fast-path matched %d report(s) session=%s",
                            len(matches), session_id,
                        )
                        if session_id:
                            _session_context[session_id] = {"last_search_terms": extracted_query}
                        result = _get_status_fast_with_bg_job(extracted_query, allowed_form_ids)
                        if allowed_form_ids is not None:
                            result = _apply_auth_to_status_result(result, allowed_form_ids)
                        return _from_result(result, intent="get_status", session_id=session_id)
                    logger.debug(
                        "[INTENT:STEP1] status fast-path: extracted_query=%r had no matches, skipping raw query lookup",
                        extracted_query,
                    )
                elif _is_generic_status_terms(raw_query):
                    logger.debug(
                        "[INTENT:STEP1] status fast-path: raw_query=%r contains only generic status terms, skipping lookup",
                        raw_query,
                    )
                else:
                    logger.debug(
                        "[INTENT:STEP1] status fast-path: no extractable report terms in %r, skipping lookup",
                        raw_query,
                    )
            # Generate / schedule / compare, or status with no matching report:
            # SQL and QA checks are skipped — LLM extraction (STEP 4) resolves intent.
            debug_log(
                "DECIDE — STEP1 WORKFLOW (LLM fallback)",
                question=user_query,
                has_status=_fuzzy_has_status(user_query),
                has_generate=_fuzzy_has_generate(user_query),
                has_schedule=_fuzzy_has_schedule(user_query),
                has_compare=bool(_CMP_KW_RE.search(user_query)),
            )

        # ── STEP 2 : Application Q&A (XML-backed deterministic) ──────────────
        # XML domain check runs BEFORE SQL — entity domain wins over action verb.
        # "How many departments" → XML-QA even if it contains "how many".
        else:
            from backend.agent.db_qa_router import (
                check_db_qa_intent, check_new_taxonomy_intent_full, handle_db_qa_query,
            )
            db_intent, db_params = await check_new_taxonomy_intent_full(user_query)
            if not db_intent:
                db_intent, db_params = check_db_qa_intent(user_query)
            debug_log(
                "DECIDE — STEP2 QA ROUTING" if db_intent else "DECIDE — STEP2 NO QA MATCH",
                question=user_query,
                detected_intent=db_intent or "NONE",
                extracted_params=db_params or "{}",
                login_id=login_id or "MISSING",
            )
            if db_intent:
                logger.info(
                    "[INTENT:STEP2] QA intent=%s params=%s user=%s role=%s session=%s",
                    db_intent, db_params, user_id, role_id, session_id,
                )
                final_user_id = user_id if _is_real_user_id(user_id) else (login_id or "0")
                final_role_id = role_id if role_id and role_id != "0" else "0"
                # H-05: see the comment on the other handle_db_qa_query() call
                # above -- same blocking-beautifier concern, same fix.
                db_result = await asyncio.to_thread(
                    handle_db_qa_query,
                    message=user_query,
                    intent=db_intent,
                    params=db_params,
                    user_id=final_user_id,
                    role_id=final_role_id,
                    beautify=True,
                    # See the comment on the other handle_db_qa_query() call
                    # above — this was also hardcoded to "phi3:mini",
                    # bypassing APP_DB_BEAUTIFY_MODEL.
                    model=_config.APP_DB_BEAUTIFY_MODEL,
                    login_id=login_id,
                )
                # A partial return name (e.g. "cims") can match many returns —
                # stash the candidate list so the user's next message ("2" or
                # a fuller name) can be resolved, same disambiguation UX as
                # get_status/generate/schedule below (STAGE_REPORT et al.).
                if db_result.get("result_type") == "disambiguation" and session_id:
                    _session_context[session_id] = {
                        "awaiting":        STAGE_RETURN_QA,
                        "pending_options": db_result.get("options", []),
                        "db_intent":       db_intent,
                        "db_params":       db_params,
                    }
                return db_result

            # ── STEP 3 : SQL / Oracle analytics ──────────────────────────────
            # Runs only when both workflow AND XML-QA checks fail.
            # SQL keywords alone no longer win over XML domains.
            if _has_sql:
                logger.info("[INTENT:STEP3] SQL keyword fast-path session=%s", session_id)
                from backend.sql_agent import handle_db_query
                return await handle_db_query(user_query, session_id=session_id, login_id=login_id)

            debug_log(
                "DECIDE — STEP3 SQL+QA MISS → LLM fallback",
                question=user_query,
                fallback_reason="No workflow/XML-QA/SQL signal matched — LLM extraction next",
            )

    # -- STEP 4: LLM intent extraction (fallback for all non-fast-path queries) --
    try:
        extracted = await extract_intent_and_entities(user_query, history=conversation_history)
    except Exception as exc:
        logger.warning("[INTENT_EXTRACT_FAIL] Extraction failed — fallback to unknown: %s", exc)
        extracted = {"intent": "unknown", "search_terms": None, "reporting_date": None}

    intent         = extracted["intent"]
    search_terms   = extracted.get("search_terms") or ""
    reporting_date = extracted.get("reporting_date")

    logger.info(
        "[INTENT] intent=%s search_terms=%r reporting_date=%r session=%s",
        intent, search_terms, reporting_date, session_id,
    )

    # -- Database Q&A Routing (LLM-extracted intents starting with "db_") ------
    # Intents like db_my_profile, db_list_users, db_list_departments, etc.
    # are extracted by the LLM and contain DB Q&A-specific entities.
    if intent.startswith("db_"):
        logger.info(
            "[INTENT] db_qa_intent=%s target_user=%s target_dept=%s query_type=%s",
            intent, extracted.get("target_user"), extracted.get("target_department"),
            extracted.get("query_type"),
        )
        from backend.agent.db_qa_router import handle_db_qa_query
        try:
            # Prefer login_id when user_id is missing, "0", or a session GUID
            final_user_id = user_id if _is_real_user_id(user_id) else (login_id or "0")
            final_role_id = role_id if role_id and role_id != "0" else "0"
            # H-05: same blocking-call concern as the other handle_db_qa_query
            # call sites above, even with beautify=False here -- the XML
            # store reads/parses inside it are still synchronous work.
            return await asyncio.to_thread(
                handle_db_qa_query,
                message=user_query,
                intent=intent,
                params=extracted,  # Contains all LLM-extracted entities
                user_id=final_user_id,
                role_id=final_role_id,
                beautify=False,  # Disabled for speed
                login_id=login_id,
            )
        except Exception as exc:
            logger.exception("[DB_QA_ERROR] intent=%s error=%s", intent, exc)
            return {
                "result": "An error occurred while processing your database request. Please try again.",
                "db_found": False,
                "result_type": "error",
            }

    if intent == "query_database":
        logger.info("[INTENT] routing to SQL agent for session=%s", session_id)
        from backend.sql_agent import handle_db_query
        return await handle_db_query(user_query, session_id=session_id, login_id=login_id)

    if intent == "unknown":
        # Only attempt report lookup for unknown queries when the message
        # explicitly looks like a report workflow request.
        # This avoids treating greetings / random chatter as report requests.
        if not (
            _fuzzy_has_status(user_query)
            or _fuzzy_has_generate(user_query)
            or _fuzzy_has_schedule(user_query)
            or _fuzzy_has_compare(user_query)
        ):
            debug_log(
                "UNKNOWN INTENT FALLBACK",
                question=user_query,
                fallback_reason=(
                    "intent='unknown' — no report-related keywords detected, "
                    "skipping report lookup"
                ),
            )
            reply = (
                "Sorry, I didn't understand your query. "
                "I can help with report status, generation, scheduling, "
                "or data queries. "
                "Could you please rephrase?"
            )
            return _build(intent="unknown", report_name=None, response_text=reply)

        # Try backend report matching with stripped query first, then progressively
        # broader candidates. This handles short ids (r091, raq) AND full natural
        # sentences like "what is the status of emi laon" — where the raw query
        # would normalise to one unrecognisable token without stripping first.
        _stripped_q   = extract_search_terms(user_query)
        if not search_terms and not _stripped_q:
            debug_log(
                "UNKNOWN_FALLBACK_SKIPPED",
                question=user_query,
                fallback_reason=(
                    "intent='unknown' with status/generate/schedule keywords but no report-identifying tokens "
                    "found — skipping backend lookup"
                ),
            )
            reply = (
                "Sorry, I didn't understand your query. "
                "I can help with report status, generation, scheduling, "
                "or data queries. Could you please mention the report name?"
            )
            return _build(intent="unknown", report_name=None, response_text=reply)

        _matched_query: str | None = None
        for _candidate in filter(None, [search_terms, _stripped_q]):
            if _is_meaningful_report_terms(_candidate) and find_matching_reports(_candidate):
                _matched_query = _candidate
                logger.info(
                    "[UNKNOWN_FALLBACK] query=%r matched report(s) — re-classifying intent",
                    _candidate,
                )
                break

        if not _matched_query and _extract_status_search_terms(user_query):
            # If the extracted status search terms already produced no matches,
            # do not perform a second lookup on the full raw query. This avoids
            # reclassifying unknown report requests as get_status simply because
            # the raw sentence contains fuzzy tokens that accidentally match.
            logger.debug(
                "[UNKNOWN_FALLBACK] extracted status terms had no match, skipping raw query lookup"
            )

        if _matched_query:
            # Re-classify to the correct intent based on fuzzy keyword detection
            # so "generate cims", "create raq", "schedule raq", "compare hdfc" etc.
            # route correctly even when the LLM returned unknown or timed out.
            # Priority: compare > schedule > generate > status (default)
            if _fuzzy_has_compare(user_query):
                logger.info(
                    "[UNKNOWN_RECLASSIFY] → compare_reports for %r session=%s",
                    _matched_query, session_id,
                )
                return await _handle_compare(_matched_query, session_id, allowed_form_ids)
            if _fuzzy_has_schedule(user_query):
                logger.info(
                    "[UNKNOWN_RECLASSIFY] → schedule_report for %r session=%s",
                    _matched_query, session_id,
                )
                return _handle_schedule(
                    _matched_query, None, None, None, session_id, allowed_form_ids, login_id,
                )
            if _fuzzy_has_generate(user_query):
                logger.info(
                    "[UNKNOWN_RECLASSIFY] → generate_instance for %r session=%s",
                    _matched_query, session_id,
                )
                # Extract reporting date from the original query so users who
                # include a date ("generate CIMS RAQ for 31 march 2025") are not
                # asked for the date again even when the LLM returned unknown.
                _fallback_date = _extract_date_from_query(user_query)
                if _fallback_date:
                    logger.info(
                        "[REPORT_DATE_DETECTED] unknown-fallback path: date=%r in query=%r — skipping date prompt",
                        _fallback_date, user_query,
                    )
                return await _handle_generate(
                    _matched_query, _fallback_date, session_id, effective_asp, allowed_form_ids, login_id
                )
            # Default: treat as a status query
            if session_id:
                _session_context[session_id] = {"last_search_terms": _matched_query}
            result = _get_status_fast_with_bg_job(_matched_query, allowed_form_ids)
            if allowed_form_ids is not None:
                result = _apply_auth_to_status_result(result, allowed_form_ids)
            return _from_result(result, intent="get_status", session_id=session_id)

        # No backend match found. If the query looks report-related (status /
        # generate / schedule keywords detected), return a crisp "not found"
        # message instead of letting the LLM generate an off-topic explanation
        # (e.g. explaining what "EMI loans" are).
        _report_query = _stripped_q or search_terms
        if _report_query and (
            _fuzzy_has_status(user_query)
            or _fuzzy_has_generate(user_query)
            or _fuzzy_has_schedule(user_query)
        ):
            if _is_generic_status_terms(_report_query):
                return _build(
                    intent="unknown", report_name=None,
                    response_text=(
                        "Sorry, I didn't understand your query. "
                        "I can help with report status, generation, scheduling, "
                        "or data queries. Could you please mention the report name?"
                    ),
                )
            _fb_intent = (
                "generate_instance" if _fuzzy_has_generate(user_query) else
                "schedule_report"   if _fuzzy_has_schedule(user_query) else
                "get_status"
            )
            return _build(
                intent=_fb_intent, report_name=None,
                response_text=(
                    f"I couldn't find any report matching '{_report_query}'.\n"
                    "Please check the report name and try again."
                ),
                result_type="error",
            )

        # ── Debug trace: unknown intent, no report match ─────────────────────────────
        debug_log(
            "UNKNOWN INTENT FALLBACK",
            question=user_query,
            fallback_reason="intent='unknown' — no DB Q&A match, no report name resolved",
        )
        reply = (
            "Sorry, I didn't understand your query. "
            "I can help with report status, generation, scheduling, "
            "or data queries. "
            "Could you please rephrase?"
        )
        return _build(intent="unknown", report_name=None, response_text=reply)

    # Fall back to session cache for follow-up turns (e.g. user just says "status?")
    if not search_terms and intent == "get_status":
        search_terms = session.get("last_search_terms", "")

    if not search_terms or (intent == "get_status" and _is_generic_status_terms(search_terms)):
        if intent == "get_status":
            # Prefer deterministic status-term extraction for get_status.
            # This prevents LLM-generated generic search terms like "missing"
            # or "database" from being treated as report names.
            status_terms = _extract_status_search_terms(user_query)
            if status_terms:
                search_terms = status_terms
            else:
                return _build(
                    intent=intent, report_name=None,
                    response_text=(
                        'Please mention the report name. '
                        'For example: "Status of CIMS_RAQ" or "Status of RAQ monthly".'
                    ),
                    need_clarification=True,
                )

        if not search_terms:
            # Use the shared resolver: tries stripped query THEN raw query so that
            # filler words like "generate", "instance", "for" are stripped before
            # matching.  Without this, "generate instance for cims" normalises to
            # the single token "generateinstanceforcims" and finds nothing.
            search_terms, _direct_matches = _resolve_report_name(user_query)
            if not _direct_matches:
                search_terms = ""
                hint = (
                    'Please provide the report name. '
                    'For example: "Generate CIMS_RAQ for 30-Jun-2024".'
                    if intent == "generate_instance"
                    else (
                        'Please provide the report name and schedule datetime. '
                        'For example: "Schedule CIMS_RAQ for 15-Apr-2026 at 4 PM".'
                    ) if intent == "schedule_report"
                    else (
                        'Please mention the report name to compare. '
                        'For example: "Compare CIMS_RAQ" or "Variance analysis of RAQ".'
                    ) if intent == "compare_reports"
                    else (
                        'Please mention the report name. '
                        'For example: "Status of CIMS_RAQ" or "Status of RAQ monthly".'
                    )
                )
                return _build(intent=intent, report_name=None, response_text=hint, need_clarification=True)
            logger.info(
                "[RESOLVED_MATCH] LLM gave no search_terms; resolver matched %d report(s) "
                "for %r → using %r",
                len(_direct_matches), user_query, search_terms,
            )

    if intent == "generate_instance":
        # ── Deterministic preprocessing: extract date + clean report name ──
        # Runs before report matching, independently of the LLM.
        # Handles filler phrases ("for date", "dated", "for report") and all
        # natural-language date formats ("31 May 2025", "31/05/2025", etc.).
        _pre_report, _pre_date = preprocess_generate_query(user_query)
        logger.debug(
            "[QUERY_PREPROCESS] query=%r -> report=%r date=%r",
            user_query, _pre_report, _pre_date,
        )
        # Use preprocessed values only when extractor found nothing already.
        if _pre_date and not reporting_date:
            reporting_date = _pre_date
        if _pre_report and not search_terms:
            search_terms = _pre_report

        if reporting_date:
            logger.info(
                "[REPORT_DATE_DETECTED] date=%r extracted from query=%r — will skip date prompt if report resolves",
                reporting_date, user_query,
            )
        else:
            logger.debug("[REPORT_DATE_DETECTED] no date found in query=%r", user_query)

        # Build date-stripped query for the shared resolver (fuzzy + disambiguation)
        _clean_gen_query = _DATE_STRIP_RE.sub(" ", user_query).strip()
        logger.debug(
            "[GEN_CLEAN_QUERY] original=%r cleaned=%r search_terms=%r",
            user_query, _clean_gen_query, search_terms,
        )
        _gen_terms, _gen_matches = _resolve_report_name(_clean_gen_query, search_terms or None)
        if _gen_matches:
            search_terms = _gen_terms
        logger.info(
            "[GENERATE_START] report=%r date=%r (resolved) session=%s",
            search_terms, reporting_date, session_id,
        )
        return await _handle_generate(search_terms, reporting_date, session_id, effective_asp, allowed_form_ids, login_id)

    if intent == "schedule_report":
        # ── Deterministic preprocessing: extract datetime + clean report name ──
        # Mirrors generate_instance preprocessing — strips schedule/generate/time
        # tokens before report name lookup so LLM-polluted search_terms are corrected.
        # Uses the two-date-aware extractor so a message that states BOTH a
        # reporting date and a schedule date/time ("...reporting date
        # 31-Mar-2026...execute on 31-Dec-2026 at 16:00") doesn't misattribute
        # the reporting date as the schedule date; it falls back to the plain
        # single-date behaviour when no reporting-date phrasing is present.
        _sched_pre    = _extract_schedule_search_terms(user_query)
        _sched_pre_dt = extract_reporting_and_schedule_datetime(user_query)
        if _sched_pre and not search_terms:
            search_terms = _sched_pre
        _rpt_date   = _sched_pre_dt.get("reporting_date")
        _sched_date = _sched_pre_dt.get("schedule_date") or extracted.get("schedule_date")
        _sched_time = _sched_pre_dt.get("schedule_time") or extracted.get("schedule_time")
        _sched_cdt  = _sched_pre_dt.get("scheduled_datetime") or extracted.get("scheduled_datetime")
        logger.info(
            "[SCHEDULE_START] report=%r reporting_date=%r date=%r time=%r session=%s",
            search_terms, _rpt_date, _sched_date, _sched_time, session_id,
        )
        return _handle_schedule(
            report_ident=search_terms,
            schedule_date=_sched_date,
            schedule_time=_sched_time,
            scheduled_datetime=_sched_cdt,
            session_id=session_id,
            allowed_form_ids=allowed_form_ids,
            login_id=login_id,
            reporting_date=_rpt_date,
        )

    if intent == "compare_reports":
        logger.info("[COMPARE_START] report=%r session=%s", search_terms, session_id)
        return await _handle_compare(search_terms, session_id, allowed_form_ids)

    # get_status: cache search terms so follow-up turns work without a name
    if session_id:
        _session_context[session_id] = {"last_search_terms": search_terms}

    # Always pass the raw search_terms (the user's partial/keyword input) to
    # get_report_status so that find_matching_reports can detect multiple hits
    # and surface a disambiguation list. Using the entity resolver's resolved
    # name here bypasses that check and jumps directly to instance lookup,
    # which gives a misleading "No instances found" when the user typed only
    # a partial name like "raq".
    result = _get_status_fast_with_bg_job(search_terms or user_query, allowed_form_ids)
    if allowed_form_ids is not None:
        result = _apply_auth_to_status_result(result, allowed_form_ids)
    _decide_elapsed = time.monotonic() - _decide_start
    logger.info(
        "[PERF] operation=decide intent=%s duration=%.2fs session=%s",
        intent, _decide_elapsed, session_id,
    )
    return _from_result(result, intent=intent, session_id=session_id)


__all__ = ["decide"]
