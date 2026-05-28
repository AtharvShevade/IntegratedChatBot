# agent/__init__.py -- Pipeline: intent → entity resolution → lookup → response.
# Session tracks last_search_terms and multi-turn stage state.

from __future__ import annotations

import logging
import re
import time
from typing import Any

from rapidfuzz import process as _fuzz
from backend.llm_extractor import extract_intent_and_entities, parse_and_format_date, extract_schedule_datetime
from backend.services.llm_service import chat_response
from backend.tools.instance_generator import (
    call_generate_api,
    resolve_return_exact,
    validate_reporting_date,
)
from backend.tools.report_lookup import (
    _parse_returns,
    find_matching_reports,
    fuzzy_report_suggestions,
    get_available_instances,
    get_form_id_by_name,
    get_instance_by_date,
    get_instance_by_dtc,
    get_report_status,
    get_report_status_exact,
)

logger = logging.getLogger(__name__)

# Stage constants -- stored in session under key "awaiting"
STAGE_DATE         = "AWAITING_DATE_SELECTION"    # status: picking a date
STAGE_REPORT       = "AWAITING_REPORT_SELECTION"  # status: picking from disambiguation
STAGE_GEN_REPORT   = "AWAITING_GEN_REPORT"        # generate: picking from disambiguation
STAGE_GEN_DATE     = "AWAITING_GEN_DATE"          # generate: providing reporting date
STAGE_RUN          = "AWAITING_RUN_SELECTION"      # status: picking a run by timestamp
STAGE_SCHED_REPORT = "AWAITING_SCHED_REPORT"      # schedule: picking from disambiguation
STAGE_SCHED_DT      = "AWAITING_SCHED_DATETIME"    # schedule: providing date and time
STAGE_SCHED_CONFIRM = "AWAITING_SCHED_CONFIRM"      # schedule: awaiting user confirmation
STAGE_SCHED_NAME    = "AWAITING_SCHED_NAME"          # schedule: re-entering report name after Change Data
STAGE_CMP_REPORT    = "AWAITING_CMP_REPORT"         # compare: picking report from disambiguation
STAGE_CMP_FILE     = "AWAITING_CMP_FILE"            # compare: confirming which 2 instances
STAGE_PREV_DATES   = "AWAITING_PREV_DATES_CONFIRM"  # status: yes/no for previous dates

# In-memory session store per session_id
_session_context: dict[str, dict[str, Any]] = {}

# Phrases that explicitly signal the user wants to start a new report query
_NEW_REPORT_KWS = frozenset({
    "new report", "different report", "another report",
    "reset", "start over", "new query", "change report",
})

_STATUS_KW_RE   = re.compile(r'\b(status|state|progress|check|details|info)\b', re.I)
_STATUS_OF_RE   = re.compile(
    r'\b(status|state|check|details|info)\s+(of|for|about)\s+\S+', re.I
)
_GEN_KW_RE      = re.compile(
    r'\b(generate|create\s+instance|trigger\s+instance|run\s+report|produce\s+instance|new\s+instance)\b',
    re.I,
)
_SCHED_KW_RE    = re.compile(r'\b(schedule|scheduled|scheduling)\b', re.I)

# DB query keyword detector — catches data-fetch queries regardless of LLM classification
_DB_QUERY_KW_RE = re.compile(
    r'\b(fetch|retrieve|show|list|display|get|select|query|how\s+many|what\s+is\s+the|'
    r'total|sum|count|average|npa|gnpa|nnpa|sma|car|slr|crr|psl|rwa|pcr|'
    r'exposure|provision|capital|loan|deposit|asset|liability|'
    r'gross|net|outstanding|balance|amount|value|data|records?|figures?|'
    r'from\s+(the\s+)?(database|db|oracle|table))\b',
    re.I,
)

# Detect ASP.NET / browser session GUIDs forwarded as user_id by the .NET iframe.
# These are 32-char hex strings (UUID without dashes) or standard UUID format.
# When matched the value is NOT a real user identifier — fall back to login_id.
_SESSION_GUID_RE = re.compile(
    r'^[0-9a-fA-F]{32}$'                                                     # 32-hex no dashes
    r'|^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'  # UUID
)


def _is_real_user_id(uid: str | None) -> bool:
    """Return True when *uid* looks like a genuine user/login identifier.

    Returns False for:
    * None / empty string
    * "0"  (sentinel from older .NET pages)
    * 32-char hex GUID (ASP.NET session UID forwarded by the iframe)
    * Standard UUID format  (same reason)
    """
    if not uid or uid == "0":
        return False
    return not _SESSION_GUID_RE.match(uid)


# Fuzzy keyword sets — catches typos like "stats", "staus", "gnearte", "gnerate"
_STATUS_FUZZY_KWS = ["status", "state", "progress", "check", "details", "info"]
_GEN_FUZZY_KWS    = ["generate", "create", "trigger", "run", "produce", "kick", "start", "launch", "execute", "fire"]
_SCHED_FUZZY_KWS  = ["schedule", "scheduled"]
_FUZZY_THRESHOLD  = 78  # 0-100; 78 allows transposition typos like 'gnearte'/'gnerate', rejects clearly unrelated words

# Stem prefixes — word starts with these 4+ chars → treat as that keyword
# Handles inflections: 'generating'→generate, 'checking'→check, 'triggered'→trigger
_STATUS_STEMS = ['stat', 'chec', 'prog', 'deta', 'info']
_GEN_STEMS    = ['gene', 'crea', 'trig', 'prod', 'kick', 'laun', 'exec', 'star', 'fire']
_SCHED_STEMS  = ['sche']


def _fuzzy_has_status(text: str) -> bool:
    """True if any word in text fuzzy-matches or stem-matches a status keyword."""
    if _STATUS_KW_RE.search(text):
        return True
    words = re.findall(r'[a-zA-Z]{3,}', text.lower())
    for w in words:
        # Stem/prefix match: 'generating' starts with 'gene' → generate
        if any(w.startswith(s) for s in _STATUS_STEMS):
            return True
        # Fuzzy edit-distance match: catches transpositions/substitutions
        if _fuzz.extractOne(w, _STATUS_FUZZY_KWS, score_cutoff=_FUZZY_THRESHOLD):
            return True
    return False


def _fuzzy_has_generate(text: str) -> bool:
    """True if any word in text fuzzy-matches or stem-matches a generate keyword."""
    if _GEN_KW_RE.search(text):
        return True
    words = re.findall(r'[a-zA-Z]{3,}', text.lower())
    for w in words:
        if any(w.startswith(s) for s in _GEN_STEMS):
            return True
        if _fuzz.extractOne(w, _GEN_FUZZY_KWS, score_cutoff=_FUZZY_THRESHOLD):
            return True
    return False


def _fuzzy_has_schedule(text: str) -> bool:
    """True if any word in text fuzzy-matches or stem-matches a schedule keyword."""
    if _SCHED_KW_RE.search(text):
        return True
    words = re.findall(r'[a-zA-Z]{4,}', text.lower())
    for w in words:
        if any(w.startswith(s) for s in _SCHED_STEMS):
            return True
        if _fuzz.extractOne(w, _SCHED_FUZZY_KWS, score_cutoff=_FUZZY_THRESHOLD):
            return True
    return False
# Date pattern -- used to extract a date from free-text messages in STAGE_GEN_DATE
_DATE_RE = re.compile(
    r'\b(\d{1,2}-(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)-\d{4})\b', re.I
)

# Stop words used when checking if a query has meaningful non-intent tokens
_QUERY_STOP = frozenset({
    "status", "state", "progress", "check", "details", "info",
    "generate", "create", "trigger", "run", "produce",
    "the", "of", "for", "a", "an", "is", "it", "this", "that",
    "what", "how", "has", "did", "been", "done",
})


def _extract_status_search_terms(text: str) -> str:
    """Extract likely report-identifying tokens from a status-style query."""
    clean = re.sub(r"[?!.,:;|()\[\]{}]+", " ", text)
    words = [
        w for w in clean.split()
        if w and w.lower() not in _QUERY_STOP and len(w) > 1
    ]
    return " ".join(words).strip()


def _is_staged_session(session: dict[str, Any] | None) -> bool:
    """Return True if session is awaiting user input for a specific workflow.
    
    Staged sessions (comparison, generation, scheduling) block fast-path processing
    like DB Q&A and SQL agent keyword matching. General conversation history does not.
    """
    if not session:
        return False
    awaiting_state = session.get("awaiting")
    staged_states = {
        STAGE_DATE, STAGE_REPORT, STAGE_GEN_REPORT, STAGE_GEN_DATE,
        STAGE_RUN, STAGE_SCHED_REPORT, STAGE_SCHED_DT, STAGE_SCHED_CONFIRM,
        STAGE_SCHED_NAME, STAGE_CMP_REPORT, STAGE_CMP_FILE, STAGE_PREV_DATES,
    }
    return awaiting_state in staged_states


def _parse_dtc_from_label(text: str) -> str | None:
    """Extract the DTC portion from a formatted instance label.

    Expects the format produced by _fmt_instance_label:
        'Generated On: <DTC> | Reporting Date: <date>'
    Returns the DTC string, or None if the format is not recognised.
    """
    m = re.search(r'Generated On:\s*(.+?)\s*\|', text)
    return m.group(1).strip() if m else None


def _is_plausible_date(text: str) -> bool:
    """Return True if text contains something that looks like a date.

    Uses a lightweight signal check (regex) + dateutil as fallback.
    Rejects pure prose like "hey" or "do one thingg" without calling the embedding model.
    """
    # Fast path: known date-like patterns (DD-MMM-YYYY, DD/MM/YYYY, ISO, month name + year, etc.)
    _DATE_SIGNAL = re.compile(
        r'\b(\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4}'           # 31/03/2024, 31-03-2024
        r'|\d{4}[/.\-]\d{1,2}[/.\-]\d{1,2}'               # 2024-03-31
        r'|\d{1,2}\s*-?\s*(?:Jan|Feb|Mar|Apr|May|Jun'      # 31-Mar-2024 / 31 Mar 2024
        r'|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s\-,]*\d{4}'
        r'|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*'
        r'\s+\d{4})\b',                                     # March 2024
        re.I,
    )
    if _DATE_SIGNAL.search(text):
        return True

    # Reject input that has no digits at all — cannot be a date
    if not re.search(r'\d', text):
        return False

    # Require at least 4 digits (minimum for a year) before trying dateutil,
    # otherwise single-digit inputs like "1" or "2" get parsed as day numbers.
    if len(re.findall(r'\d', text)) < 4:
        return False

    # Reject a bare 4-digit year (e.g. "2024") — not a complete date
    if re.fullmatch(r'\s*\d{4}\s*', text):
        return False

    # Last resort: try dateutil — if it raises, it's not a date
    try:
        from dateutil import parser as _du
        _du.parse(text, fuzzy=False)
        return True
    except Exception:
        return False


def _looks_like_new_query(text: str) -> bool:
    """True when the message looks like a fresh status, generate, or schedule intent.

    Uses fuzzy matching so typos like 'stats of raq', 'gnearte cims', 'schdule raq' still work.
    """
    if _STATUS_OF_RE.search(text):
        return True
    if _fuzzy_has_generate(text):
        return True
    if _fuzzy_has_schedule(text):
        return True
    # Fuzzy status keyword + at least one meaningful non-stop word
    if _fuzzy_has_status(text):
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        return any(w not in _QUERY_STOP for w in words)
    return False


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
    # set   = restrict to this user’s department forms
    allowed_form_ids: set[str] | None = None
    if login_id:
        from backend.services.auth_service import get_allowed_form_ids as _get_auth
        allowed_form_ids = _get_auth(login_id)
        if allowed_form_ids is None:
            logger.warning(
                "[AUTH_DENY] User not found: login_id=%r session=%s", login_id, session_id
            )
            return _build(
                intent="unknown",
                report_name=None,
                response_text="Your account was not recognised. Please contact your administrator.",
                result_type="error",
            )
        logger.info(
            "[AUTH] login_id=%r allowed_forms=%d session=%s",
            login_id, len(allowed_form_ids), session_id,
        )

    # ── Auth: resolve CreateInstance role-based access ────────────────────────
    # True when no login_id is present (dev / backward compat — allow all).
    # False when the user's role does not have HasNew=true for CreateInstance.
    _create_access: bool = True
    if login_id:
        from backend.services.auth_service import can_generate_instance as _chk_create
        _create_access = _chk_create(login_id)
        logger.info(
            "[AUTH_ROLE] login_id=%r can_generate_instance=%s session=%s",
            login_id, _create_access, session_id,
        )

    # ── Auth: resolve role_id from XML_User.xml when caller didn't supply it ──
    # The .NET app only passes loginId/uid — it never sends roleId.
    # Use auth_service.get_user_role_id() (same XML read already cached) so
    # every downstream handler (DB Q&A, SQL agent, etc.) sees the correct role.
    if login_id and (not role_id or role_id == "0"):
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

    # Persist the live cookie so staged flows (multi-turn generate) can use it
    if asp_session and session_id:
        session["asp_session"] = asp_session
        _session_context[session_id] = session

    # Prefer the freshly-forwarded cookie; fall back to one stored earlier in session
    effective_asp = asp_session or session.get("asp_session")
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
        # Labels like "Generated On: X | Reporting Date: Y" contain the word
        # "Generated" which falsely triggers _looks_like_new_query (generate stem).
        # This is the same issue as STAGE_CMP_FILE with the word "run".
        dtc_from_label = _parse_dtc_from_label(user_query)
        if dtc_from_label:
            form_id     = session["pending_form_id"]
            return_name = session["pending_return_name"]
            result = get_instance_by_dtc(form_id, dtc_from_label, return_name)
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
                except Exception:
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
                result = get_instance_by_date(form_id, user_query.strip(), return_name)

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
            lower           = lower_q.strip()
            form_id         = session.get("pending_form_id", "")
            return_name     = session.get("pending_return_name", "")
            other_instances = session.get("pending_other_instances", [])
            if lower in ("yes", "y", "yeah", "yep"):
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
                # Keyword / partial selection: try to find the option that best matches
                raw_lower = raw_input.lower()
                keyword_match = next(
                    (name for name in pending_options if raw_lower in name.lower() or name.lower() in raw_lower),
                    None,
                )
                resolved_name = keyword_match if keyword_match else raw_input

            if session_id:
                _session_context.pop(session_id, None)
            auth_err = _check_name_auth(resolved_name, allowed_form_ids, "get_status")
            if auth_err:
                return auth_err
            result = get_report_status_exact(resolved_name)
            return _from_result(result, intent="get_status", session_id=session_id)

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
            if not _create_access:
                return _build(
                    intent="generate_instance", report_name=None,
                    response_text="Sorry, you do not have access to generate report instances.",
                    result_type="error",
                )
            # Always ask for date after disambiguation — never use a pre-extracted
            # date from the original query (prevents stale/hallucinated date validation).
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
                # Normalize any natural format (e.g. 31/03/2021, 2021-03-31)
                date_str = parse_and_format_date(user_query.strip()) or user_query.strip()
            if not _create_access:
                return _build(
                    intent="generate_instance", report_name=None,
                    response_text="Sorry, you do not have access to generate report instances.",
                    result_type="error",
                )
            return await _handle_gen_date(date_str, session, session_id, effective_asp)

    # -- Schedule: re-enter report name after "Change Data" --------------------
    if not is_reset and session.get("awaiting") == STAGE_SCHED_NAME:
        if session_id:
            _session_context.pop(session_id, None)
        return _handle_schedule(user_query.strip(), None, None, None, session_id)

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
            return _finalize_schedule(ret, saved_sched_date, saved_sched_time, saved_sched_dt, session_id)

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
                "form_id": session["sched_form_id"],
                "name":    session["sched_return_name"],
            }
            if session_id:
                _session_context.pop(session_id, None)
            return _finalize_schedule(sched_ret, schedule_date, schedule_time, scheduled_dt, session_id)

    # -- Schedule: user confirmation (Schedule / Change Data) ------------------
    if not is_reset and session.get("awaiting") == STAGE_SCHED_CONFIRM:
        raw = user_query.strip().lower()
        sched_name = session.get("sched_return_name", "")
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
                    "No problem! Let\u2019s start over.\n"
                    "Please provide the report name for scheduling."
                ),
                result_type="sched_awaiting_name",
            )
        # "Schedule" button or any confirmation → finalize
        if session_id:
            _session_context.pop(session_id, None)
        logger.info(
            "[SCHEDULE_CONFIRMED] report=%r date=%s time=%s session=%s",
            sched_name, sched_date, sched_time, session_id,
        )
        return _build(
            intent="schedule_report",
            report_name=sched_name,
            response_text=(
                f"Schedule confirmed:\n"
                f"Report     : {sched_name}\n"
                f"Date       : {sched_date}\n"
                f"Time       : {sched_time}\n"
                f"Scheduled  : {sched_dt or f'{sched_date} {sched_time}'}"
            ),
            result_type="schedule_parsed",
            scheduled_datetime=sched_dt,
            schedule_date=sched_date,
            schedule_time=sched_time,
        )

    # -- Compare: report disambiguation ----------------------------------------
    if not is_reset and session.get("awaiting") == STAGE_CMP_REPORT:
        if _looks_like_new_query(user_query):
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
    if not is_reset and session.get("awaiting") == STAGE_CMP_FILE:
        return await _run_comparison(session, user_query, session_id)

    # -- Application Database Q&A (regex-based intent classification) -----------
    # Checks for DB Q&A intents (user management, returns, roles, etc.) before
    # invoking the main LLM OR SQL agent. This is fast (no LLM call) and works offline.
    # Gracefully skipped if APP_DB_BASE_PATH is not configured.
    # MUST come before SQL agent check to take priority
    # Works in: (1) first message (empty session) (2) multi-turn chat (general session)
    # Blocked in: staged sessions (comparison/generation/scheduling in progress)
    if not _is_staged_session(session) and not is_reset:
        from backend.agent.db_qa_router import check_db_qa_intent, handle_db_qa_query
        
        db_intent, db_params = check_db_qa_intent(user_query)
        # ── Debug trace: log DB Q&A intent detection result ───────────────────────────
        if db_intent:
            debug_log(
                "DECIDE — DB QA ROUTING",
                question=user_query,
                detected_intent=db_intent,
                extracted_params=db_params or "{}",
                raw_user_id=user_id or "MISSING",
                login_id=login_id or "MISSING",
            )
        else:
            debug_log(
                "DECIDE — NO DB Q&A MATCH",
                question=user_query,
                fallback_reason="No DB Q&A regex matched — will try SQL agent or LLM",
            )
        if db_intent:
            logger.info(
                "[INTENT] db_qa_intent=%s params=%s session=%s user=%s role=%s",
                db_intent, db_params, session_id, user_id, role_id,
            )
            # Prefer login_id when user_id is missing, "0", or a session GUID
            # (the .NET iframe forwards uid=<ASP session GUID> which is not a real user ID)
            final_user_id = user_id if _is_real_user_id(user_id) else (login_id or "0")
            final_role_id = role_id if role_id and role_id != "0" else "0"
            
            return handle_db_qa_query(
                message=user_query,
                intent=db_intent,
                params=db_params,
                user_id=final_user_id,
                role_id=final_role_id,
                beautify=True,  # Use LLM for formatting by default
                model="phi3:mini",  # Match env default
            )

    # -- Keyword fast-path: DB queries (skip LLM for clear data-fetch requests) --
    # Catches queries like "total loan from cims raq", "show NPA for FY2024",
    # "what is the gross NPA" without waiting for LLM intent extraction.
    # Only fires when no staged session is active (i.e. not in workflow).
    if not _is_staged_session(session) and not is_reset and _DB_QUERY_KW_RE.search(user_query):
        # Make sure it doesn't look like a status/generate/schedule query first
        if not _fuzzy_has_status(user_query) and not _fuzzy_has_generate(user_query) and not _fuzzy_has_schedule(user_query):
            logger.info("[INTENT] keyword fast-path → query_database session=%s", session_id)
            from backend.sql_agent import handle_db_query
            return await handle_db_query(user_query, session_id=session_id)

    # -- Keyword fast-path: status lookups (skip LLM on obvious status phrasing) --
    if not _is_staged_session(session) and not is_reset and _fuzzy_has_status(user_query):
        raw_query = user_query.strip()
        extracted_query = _extract_status_search_terms(raw_query)
        for candidate in (raw_query, extracted_query):
            if not candidate:
                continue
            matches = find_matching_reports(candidate)
            if matches:
                logger.info(
                    "[INTENT] status fast-path query=%r matched %d report(s) session=%s",
                    candidate, len(matches), session_id,
                )
                if session_id:
                    _session_context[session_id] = {"last_search_terms": candidate}
                result = get_report_status(candidate)
                if allowed_form_ids is not None:
                    result = _apply_auth_to_status_result(result, allowed_form_ids)
                return _from_result(result, intent="get_status", session_id=session_id)

    # -- Normal intent extraction ---------------------------------------------
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
            return handle_db_qa_query(
                message=user_query,
                intent=intent,
                params=extracted,  # Contains all LLM-extracted entities
                user_id=final_user_id,
                role_id=final_role_id,
                beautify=False,  # Disabled for speed
            )
        except Exception as exc:
            logger.exception("[DB_QA_ERROR] intent=%s error=%s", intent, exc)
            return {
                "result": f"Error processing database query: {str(exc)}",
                "db_found": False,
                "result_type": "error",
            }

    if intent == "query_database":
        logger.info("[INTENT] routing to SQL agent for session=%s", session_id)
        from backend.sql_agent import handle_db_query
        return await handle_db_query(user_query, session_id=session_id)

    if intent == "unknown":
        # Before falling back to the LLM, run the raw input through the backend
        # report resolver. This handles short identifiers like "r091" or "raq"
        # that small LLMs mis-classify as unknown but are valid report queries.
        _fallback_query = search_terms or user_query.strip()
        if _fallback_query:
            _fallback_matches = find_matching_reports(_fallback_query)
            if _fallback_matches:
                logger.info(
                    "[UNKNOWN_FALLBACK] query=%r matched %d report(s) — routing to get_status",
                    _fallback_query, len(_fallback_matches),
                )
                if session_id:
                    _session_context[session_id] = {"last_search_terms": _fallback_query}
                result = get_report_status(_fallback_query)
                if allowed_form_ids is not None:
                    result = _apply_auth_to_status_result(result, allowed_form_ids)
                return _from_result(result, intent="get_status", session_id=session_id)
        try:
            reply = await chat_response(user_query, history=conversation_history)
        except Exception as exc:
            logger.warning("chat_response failed (%s)", exc)
            reply = (
                'I can help with report status, generation, or scheduling. '
                'Try: "Status of CIMS_RAQ", "Generate CIMS_RAQ for 30-Jun-2024", '
                'or "Schedule RAQ for 15-Apr-2026 at 4 PM".'
            )
        # ── Debug trace: LLM generic fallback is firing ──────────────────────────────
        debug_log(
            "LLM GENERIC FALLBACK",
            question=user_query,
            fallback_reason="intent='unknown' — no DB Q&A match, no report name resolved, using LLM answer",
            response_preview=reply[:100],
        )
        return _build(intent="unknown", report_name=None, response_text=reply)

    # Fall back to session cache for follow-up turns (e.g. user just says "status?")
    if not search_terms and intent == "get_status":
        search_terms = session.get("last_search_terms", "")

    if not search_terms:
        # Before showing a clarification prompt, try the full raw query against
        # the backend resolver. This catches cases where the LLM failed to extract
        # search_terms but the query itself is a valid identifier (e.g. "r091").
        _direct_matches = find_matching_reports(user_query.strip())
        if _direct_matches:
            search_terms = user_query.strip()
            logger.info(
                "[DIRECT_MATCH] LLM extracted no search_terms but backend matched %d "
                "report(s) for %r — using raw query",
                len(_direct_matches), search_terms,
            )
        else:
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

    if intent == "generate_instance":
        logger.info("[GENERATE_START] report=%r session=%s", search_terms, session_id)
        if not _create_access:
            return _build(
                intent="generate_instance", report_name=None,
                response_text="Sorry, you do not have access to generate report instances.",
                result_type="error",
            )
        return await _handle_generate(search_terms, reporting_date, session_id, effective_asp, allowed_form_ids)

    if intent == "schedule_report":
        logger.info("[SCHEDULE_START] report=%r session=%s", search_terms, session_id)
        return _handle_schedule(
            report_ident=search_terms,
            schedule_date=extracted.get("schedule_date"),
            schedule_time=extracted.get("schedule_time"),
            scheduled_datetime=extracted.get("scheduled_datetime"),
            session_id=session_id,
            allowed_form_ids=allowed_form_ids,
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
    result = get_report_status(search_terms or user_query)
    if allowed_form_ids is not None:
        result = _apply_auth_to_status_result(result, allowed_form_ids)
    _decide_elapsed = time.monotonic() - _decide_start
    logger.info(
        "[PERF] operation=decide intent=%s duration=%.2fs session=%s",
        intent, _decide_elapsed, session_id,
    )
    return _from_result(result, intent=intent, session_id=session_id)


# ---------------------------------------------------------------------------
# Compare helpers
# ---------------------------------------------------------------------------

async def _handle_compare(report_ident: str, session_id: str | None, allowed_form_ids: set[str] | None = None) -> dict[str, Any]:
    """Entry point for compare_reports intent — handles disambiguation."""
    from backend.tools.xbrl_comparator import find_instances_by_prefix

    matches = find_matching_reports(report_ident)
    if allowed_form_ids is not None:
        matches = [m for m in matches if m.get("Id", "").strip() in allowed_form_ids]

    if not matches:
        # Before giving up, check if there are instance files in logs/ whose
        # filenames start with this prefix (e.g. HDFC files not in returns.xml)
        direct_files = find_instances_by_prefix(report_ident)
        if len(direct_files) >= 2:
            if allowed_form_ids is not None:
                fid = get_form_id_by_name(report_ident) or ""
                if fid and fid not in allowed_form_ids:
                    return _build(
                        intent="compare_reports", report_name=report_ident,
                        response_text="You are not authorised to access this report.",
                        result_type="error",
                    )
            return await _compare_with_name(report_ident, session_id)
        if len(direct_files) == 1:
            return _build(
                intent="compare_reports", report_name=report_ident,
                response_text=(
                    f"Only one instance file found for '{report_ident}' — "
                    "at least 2 are needed for comparison."
                ),
                result_type="error",
            )

        suggestions = fuzzy_report_suggestions(report_ident)
        if allowed_form_ids is not None:
            suggestions = _filter_names_by_auth(suggestions, allowed_form_ids)
        if suggestions:
            opts_text = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(suggestions))
            if session_id:
                _session_context[session_id] = {
                    "awaiting": STAGE_CMP_REPORT, "pending_options": suggestions,
                }
            return _build(
                intent="compare_reports", report_name=None,
                response_text=(
                    f"No exact match for '{report_ident}'. Did you mean:\n\n"
                    f"{opts_text}\n\nReply with the number."
                ),
                result_type="disambiguation", options=suggestions,
            )
        return _build(
            intent="compare_reports", report_name=None,
            response_text=f"No matching reports found for '{report_ident}'.",
            result_type="error",
        )

    if len(matches) > 1:
        names = list(dict.fromkeys(m.get("Name", "") for m in matches if m.get("Name")))
        opts_text = "\n".join(f"{i + 1}. {n}" for i, n in enumerate(names))
        if session_id:
            _session_context[session_id] = {
                "awaiting": STAGE_CMP_REPORT, "pending_options": names,
            }
        return _build(
            intent="compare_reports", report_name=None,
            response_text=(
                f"I found {len(names)} matching reports. Which one to compare?\n\n"
                f"{opts_text}\n\nReply with the number or part of the name."
            ),
            result_type="disambiguation", options=names,
        )

    return await _compare_with_name(matches[0].get("Name", report_ident), session_id)


async def _compare_with_name(name: str, session_id: str | None) -> dict[str, Any]:
    """Resolve Report ID → scan instance folder → present selection.

    Primary path  : Returns.xml → Report ID → {INSTANCE_BASE_DIR}/{id}/ → *.xml
    Fallback path : XML_InstanceLog lookup, then logs/ prefix scan
                    (keeps backward-compat for HDFC test files).
    """
    from backend.services.instance_service import get_instances_for_report
    from backend.tools.xbrl_comparator import find_comparable_instances, find_instances_by_prefix

    # 1 ── Primary: report name → Report ID → repository instance folder
    form_id  = get_form_id_by_name(name)
    instances: list[dict] = []

    if form_id:
        instances = get_instances_for_report(form_id)
        if not instances:
            logger.info(
                "_compare_with_name: instance folder empty for form_id=%s — trying XML_InstanceLog",
                form_id,
            )
            instances = find_comparable_instances(form_id)   # fallback to log file
    else:
        logger.info("_compare_with_name: '%s' not in Returns.xml — scanning logs/ by prefix", name)

    # 2 ── Fallback: scan logs/ for filenames starting with the search term
    if not instances:
        instances = find_instances_by_prefix(name)

    # ── Error guards ──────────────────────────────────────────────────────────
    if not instances:
        return _build(
            intent="compare_reports", report_name=name,
            response_text=(
                f"No instance files found for '{name}'. "
                "Ensure the report has been generated and the instance folder exists."
            ),
            result_type="error",
        )

    if len(instances) < 2:
        return _build(
            intent="compare_reports", report_name=name,
            response_text=(
                f"'{name}' has only {len(instances)} instance file — "
                "at least 2 are needed for comparison."
            ),
            result_type="error",
        )

    # ── Build rich metadata for the interactive frontend selector ─────────────
    instances_meta = [
        {
            "index":          i,
            "filename":       inst["instance_path"],
            "reporting_date": inst["reporting_date"],
            "run_at":         inst["dtc"],
            "label":          inst.get("label") or f"{inst['reporting_date']} | Generated: {inst['dtc']}",
            "status":         inst.get("status", ""),
        }
        for i, inst in enumerate(instances)
    ]

    msg = (
        f"'{name}' \u2014 {len(instances)} instance file(s) found.\n"
        "Select exactly 2 instances to compare."
    )
    if session_id:
        _session_context[session_id] = {
            "awaiting":        STAGE_CMP_FILE,
            "cmp_instances":   instances,
            "cmp_return_name": name,
            "auto_a":          0,
            "auto_b":          1,
        }
    return _build(
        intent="compare_reports", report_name=name,
        response_text=msg, result_type="instance_selection",
        options=[f"{inst['reporting_date']} (run: {inst['dtc']})" for inst in instances],
        instances_data=instances_meta,
    )


async def _run_comparison(
    session:    dict[str, Any],
    user_query: str,
    session_id: str | None,
) -> dict[str, Any]:
    """Execute the actual XBRL variance analysis once files are confirmed."""
    from backend.tools.xbrl_comparator import (
        load_xbrl_facts, compute_variance, format_variance_table, generate_llm_summary,
    )

    instances = session.get("cmp_instances", [])
    name      = session.get("cmp_return_name", "")
    idx_a     = session.get("auto_a", 0)
    idx_b     = session.get("auto_b", 1)

    raw = user_query.strip().lower()

    # Match by option label text — user may click an option button in the UI
    # e.g. "30-Sep-2021 (run: 11-Jun-2025 05:43:52 PM)" selects that instance.
    label_match = next(
        (i for i, inst in enumerate(instances)
         if inst["reporting_date"] in user_query or user_query.strip() in inst.get("dtc", "")
         or user_query.strip() == f"{inst['reporting_date']} (run: {inst['dtc']})"),
        None,
    )
    if label_match is not None:
        idx_a = label_match
        idx_b = (label_match + 1) % len(instances)
        # Produce final comparison directly
        inst_a  = instances[idx_a]
        inst_b  = instances[idx_b]
        label_a = inst_a["reporting_date"]
        label_b = inst_b["reporting_date"]
        if label_a == label_b:
            def _run_time(inst: dict) -> str:
                dtc = inst.get("dtc", "")
                parts = dtc.split(" ")
                return parts[1] if len(parts) >= 2 else "?"
            label_a = f"{label_a} (run {_run_time(inst_a)})"
            label_b = f"{label_b} (run {_run_time(inst_b)})"
        if session_id:
            _session_context.pop(session_id, None)
        try:
            facts_a = load_xbrl_facts(inst_a["full_path"])
            facts_b = load_xbrl_facts(inst_b["full_path"])
        except ImportError as exc:
            return _build(intent="compare_reports", report_name=name,
                          response_text=f"XBRL analysis unavailable: {exc}", result_type="error")
        except Exception as exc:
            logger.error("XBRL load error: %s", exc, exc_info=True)
            return _build(intent="compare_reports", report_name=name,
                          response_text="Failed to load XBRL instance files. Check server logs.",
                          result_type="error")
        variance_rows = compute_variance(facts_a, label_a, facts_b, label_b)
        table = format_variance_table(variance_rows, label_a, label_b)
        serialized = [
            {
                "concept":     r["concept"],
                "val_a":       r[label_a],
                "val_b":       r[label_b],
                "diff":        r["diff"],
                "pct_change":  r["pct_change"],
                "significant": r["significant"],
            }
            for r in variance_rows
        ]
        llm_summary = await generate_llm_summary(variance_rows, label_a, label_b, name)
        return _build(intent="compare_reports", report_name=name,
                      response_text=(f"Variance Analysis \u2014 {name}\n"
                                     f"Comparing: {label_a}  vs  {label_b}\n\n{table}"),
                      result_type="variance_table",
                      variance_data=serialized,
                      variance_label_a=label_a,
                      variance_label_b=label_b,
                      llm_summary=llm_summary)

    # Parse "1 vs 3", "2 and 1", "1, 2", etc.
    nums = re.findall(r"\d+", user_query)
    if len(nums) >= 2:
        a, b = int(nums[0]) - 1, int(nums[1]) - 1
        if 0 <= a < len(instances) and 0 <= b < len(instances) and a != b:
            idx_a, idx_b = a, b
        else:
            return _build(
                intent="compare_reports", report_name=name,
                response_text=(
                    f"Invalid selection. Pick two different numbers between 1 and {len(instances)}."
                ),
                result_type="error",
            )
    elif raw not in ("confirm", "yes", "ok", "proceed", "y"):
        opts_text = "\n".join(
            f"{i + 1}. {inst['reporting_date']} (run: {inst['dtc']})"
            for i, inst in enumerate(instances)
        )
        return _build(
            intent="compare_reports", report_name=name,
            response_text=(
                f"Type 'confirm' to compare "
                f"{instances[idx_a]['reporting_date']} vs {instances[idx_b]['reporting_date']}, "
                f"or pick two numbers (e.g. '1 vs 3').\n\n{opts_text}"
            ),
            result_type="instance_selection",
            options=[f"{inst['reporting_date']} (run: {inst['dtc']})" for inst in instances],
        )

    inst_a  = instances[idx_a]
    inst_b  = instances[idx_b]
    label_a = inst_a["reporting_date"]
    label_b = inst_b["reporting_date"]
    if label_a == label_b:
        def _run_time(inst: dict) -> str:
            dtc = inst.get("dtc", "")
            parts = dtc.split(" ")
            return parts[1] if len(parts) >= 2 else "?"
        label_a = f"{label_a} (run {_run_time(inst_a)})"
        label_b = f"{label_b} (run {_run_time(inst_b)})"

    if session_id:
        _session_context.pop(session_id, None)

    try:
        facts_a = load_xbrl_facts(inst_a["full_path"])
        facts_b = load_xbrl_facts(inst_b["full_path"])
    except ImportError as exc:
        return _build(
            intent="compare_reports", report_name=name,
            response_text=f"XBRL analysis unavailable: {exc}", result_type="error",
        )
    except Exception as exc:
        logger.error("XBRL load error: %s", exc, exc_info=True)
        return _build(
            intent="compare_reports", report_name=name,
            response_text="Failed to load XBRL instance files. Check server logs.",
            result_type="error",
        )

    variance_rows = compute_variance(facts_a, label_a, facts_b, label_b)
    table = format_variance_table(variance_rows, label_a, label_b)
    serialized = [
        {
            "concept":     r["concept"],
            "val_a":       r[label_a],
            "val_b":       r[label_b],
            "diff":        r["diff"],
            "pct_change":  r["pct_change"],
            "significant": r["significant"],
        }
        for r in variance_rows
    ]
    llm_summary = await generate_llm_summary(variance_rows, label_a, label_b, name)

    return _build(
        intent="compare_reports", report_name=name,
        response_text=(
            f"Variance Analysis — {name}\n"
            f"Comparing: {label_a}  vs  {label_b}\n\n"
            f"{table}"
        ),
        result_type="variance_table",
        variance_data=serialized,
        variance_label_a=label_a,
        variance_label_b=label_b,
        llm_summary=llm_summary,
    )


# ---------------------------------------------------------------------------
# Direct comparison executor — called by /compare-execute endpoint.
# Bypasses all intent detection and session routing.
# ---------------------------------------------------------------------------

async def execute_comparison(
    session_id: str,
    idx_a: int,
    idx_b: int,
) -> dict[str, Any]:
    """Execute XBRL variance analysis for the two selected instances.

    Reads instance file paths from the server-side session that was set when
    the instance-selection UI was presented.  If the session has expired (e.g.
    the dev server restarted between showing the dropdowns and clicking
    Compare), returns a clear error so the user can restart the flow.
    """
    session = _session_context.get(session_id, {})

    if session.get("awaiting") != STAGE_CMP_FILE:
        return _build(
            intent="compare_reports",
            report_name=None,
            response_text=(
                "Comparison session not found or expired. "
                "Please start the comparison again by entering the report name."
            ),
            result_type="error",
        )

    instances = session.get("cmp_instances", [])
    if idx_a < 0 or idx_a >= len(instances) or idx_b < 0 or idx_b >= len(instances):
        return _build(
            intent="compare_reports",
            report_name=session.get("cmp_return_name"),
            response_text=(
                f"Invalid instance indices ({idx_a + 1}, {idx_b + 1}). "
                f"Valid range: 1–{len(instances)}."
            ),
            result_type="error",
        )

    if idx_a == idx_b:
        return _build(
            intent="compare_reports",
            report_name=session.get("cmp_return_name"),
            response_text="Please select two different instances to compare.",
            result_type="error",
        )

    # Delegate to _run_comparison; pass a synthetic "X vs Y" string so the
    # existing regex parser selects the correct indices cleanly.
    session_copy = dict(session)
    session_copy["auto_a"] = idx_a
    session_copy["auto_b"] = idx_b
    return await _run_comparison(
        session_copy,
        f"{idx_a + 1} vs {idx_b + 1}",
        session_id,
    )


# ---------------------------------------------------------------------------
# Result helpers
# ---------------------------------------------------------------------------

def _from_result(
    result: dict[str, Any],
    intent: str = "get_status",
    session_id: str | None = None,
    keep_date_ctx: bool = False,
) -> dict[str, Any]:
    rtype = result["type"]

    if rtype == "latest_with_ask":
        ret_name        = result.get("return_name", result.get("report_name", ""))
        rep_date        = result.get("reporting_date", "")
        status          = result.get("status", "")
        run_time        = result.get("run_time", "")
        other_instances = result.get("other_instances", [])
        status_note     = result.get("status_note", "")
        text = (
            f"{ret_name}\n"
            f"Latest Reporting Date : {rep_date}\n"
            f"Status                : {status}"
        )
        if run_time:
            text += f"\nGenerated On          : {run_time}"
        if status_note:
            text += f"\n{status_note}"
        if other_instances:
            if session_id:
                _session_context[session_id] = {
                    "awaiting":                STAGE_PREV_DATES,
                    "pending_form_id":         result["form_id"],
                    "pending_return_name":      ret_name,
                    "pending_other_instances": other_instances,
                }
            return _build(
                intent=intent, report_name=ret_name,
                response_text=text,
                result_type="ask_previous",
                options=["Yes", "No"],
                download_url=result.get("download_url", ""),
                download_label=result.get("download_label", ""),
            )
        # No other instances — just show final status
        return _build(intent=intent, report_name=ret_name,
                      response_text=text, result_type="final",
                      download_url=result.get("download_url", ""),
                      download_label=result.get("download_label", ""))

    if rtype == "final":
        dtc = result.get("dtc", "")
        text = (
            f"{result['report_name']}\n"
            f"Reporting Date : {result['reporting_date']}\n"
        )
        if dtc:
            text += f"Generated On   : {dtc}\n"
        text += f"Status         : {result['status']}"
        status_note = result.get("status_note", "")
        if status_note:
            text += f"\n{status_note}"
        if keep_date_ctx:
            text += '\n\nYou can select another reporting date, or say "new report" to switch reports.'
        return _build(intent=intent, report_name=result["report_name"],
                      response_text=text, result_type="final",
                      download_url=result.get("download_url", ""),
                      download_label=result.get("download_label", ""))

    if rtype == "disambiguation":
        opts = result.get("options", [])
        opts_text = "\n".join(f"{i + 1}. {n}" for i, n in enumerate(opts))
        msg = (
            f"I found {len(opts)} matching reports. Which one are you looking for?\n\n"
            f"{opts_text}\n\n"
            "Reply with the number or part of the name."
        )
        if session_id:
            _session_context[session_id] = {
                "awaiting":        STAGE_REPORT,
                "pending_options": opts,
            }
        return _build(intent=intent, report_name=None,
                      response_text=msg,
                      result_type="disambiguation",
                      options=opts)

    if rtype == "date_selection":
        ret_name = result.get("return_name", "this report")
        opts     = result.get("options", [])
        msg = f"Select a reporting date for '{ret_name}':"
        if session_id:
            _session_context[session_id] = {
                "awaiting":            STAGE_DATE,
                "pending_form_id":     result["form_id"],
                "pending_return_name": ret_name,
            }
        return _build(intent=intent, report_name=ret_name,
                      response_text=msg,
                      result_type="date_selection",
                      options=opts)

    if rtype == "run_selection":
        ret_name = result.get("return_name", "this report")
        rep_date = result.get("reporting_date", "")
        opts     = result.get("options", [])  # list of {"id", "label", "status", "dtc"}
        opts_text = "\n".join(f"{i + 1}. {o['label']}" for i, o in enumerate(opts))
        msg = (
            f"'{ret_name}' has {len(opts)} runs for {rep_date}. "
            f"Which run would you like to view?\n\n{opts_text}\n\n"
            "Reply with the number to select."
        )
        if session_id:
            _session_context[session_id] = {
                "awaiting":               STAGE_RUN,
                "pending_form_id":        result.get("form_id"),
                "pending_return_name":    ret_name,
                "pending_reporting_date": rep_date,
                "pending_runs":           opts,
            }
        return _build(
            intent=intent,
            report_name=ret_name,
            response_text=msg,
            result_type="run_selection",
            options=[o["label"] for o in opts],
        )

    # error — make message more conversational
    raw = result.get("message", "Something went wrong. Please try again.")
    msg = re.sub(
        r"No exact match found for '(.+?)'. Did you mean",
        r"I couldn't find '\1' exactly. Did you mean",
        raw,
    )
    msg = re.sub(
        r"No matching reports found for '(.+?)'",
        r"I couldn't find any report called '\1'",
        msg,
    )
    msg = re.sub(
        r"Found multiple matching reports\. Which one do you mean\?",
        "I found multiple matching reports. Which one are you looking for?",
        msg,
    )
    return _build(intent=intent, report_name=None, response_text=msg, result_type="error")


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
        text += f"Generated On   : {dtc}\n"
    text += f"Status         : {result['status']}"
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
    return _build(
        intent=intent,
        report_name=return_name,
        response_text=text,
        result_type="ask_previous",
        options=["Yes", "No"],
        download_url=result.get("download_url", ""),
        download_label=result.get("download_label", ""),
    )


# ---------------------------------------------------------------------------
# Generate instance helpers
# ---------------------------------------------------------------------------

def _finalize_schedule(
    ret: dict[str, Any],
    schedule_date: str | None,
    schedule_time: str | None,
    scheduled_datetime: str | None,
    session_id: str | None,
) -> dict[str, Any]:
    """Build a confirmed schedule response, or ask for the missing date/time."""
    if not schedule_date or not schedule_time:
        missing = []
        if not schedule_date:
            missing.append("date")
        if not schedule_time:
            missing.append("time")
        if session_id:
            _session_context[session_id] = {
                "awaiting":          STAGE_SCHED_DT,
                "sched_form_id":     ret["form_id"],
                "sched_return_name": ret["name"],
                "sched_schedule_date": schedule_date,
                "sched_schedule_time": schedule_time,
            }
        return _build(
            intent="schedule_report",
            report_name=ret["name"],
            response_text=(
                f"Report confirmed: '{ret['name']}'.\n"
                f"Please provide the schedule {' and '.join(missing)}.\n"
                'For example: "15-Apr-2026 at 4 PM".'
            ),
            result_type="sched_awaiting_dt",
        )

    # Both date and time present — show confirmation card before finalizing
    if session_id:
        _session_context[session_id] = {
            "awaiting":            STAGE_SCHED_CONFIRM,
            "sched_form_id":       ret["form_id"],
            "sched_return_name":   ret["name"],
            "sched_schedule_date": schedule_date,
            "sched_schedule_time": schedule_time,
            "sched_scheduled_dt":  scheduled_datetime,
        }
    return _build(
        intent="schedule_report",
        report_name=ret["name"],
        response_text=(
            f"We are going to generate the report instance with the following schedule details:\n\n"
            f"Report Name   : {ret['name']}\n"
            f"Schedule Date : {schedule_date}\n"
            f"Schedule Time : {schedule_time}"
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
) -> dict[str, Any]:
    """Validate report name against known definitions, then confirm the schedule.

    Mirrors _handle_generate:
      find_matching_reports → disambiguation → resolve_return_exact → _finalize_schedule
    """
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

    return _finalize_schedule(ret, schedule_date, schedule_time, scheduled_datetime, session_id)


async def _finalize_generation(
    ret: dict[str, Any],
    reporting_date: str,
    session_id: str | None,
    asp_session: str | None = None,
) -> dict[str, Any]:
    """Validate date and call the .NET API for a fully-resolved (report, date) pair."""
    validation = validate_reporting_date(reporting_date, ret["frequency"])
    if not validation["valid"]:
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
        suggestions = validation["suggestions"]
        # Near-miss hint: single suggestion -> "Did you mean X?"
        if len(suggestions) == 1:
            error_msg = f"Did you mean {suggestions[0]}?\n\n{error_msg}"
        return _build(
            intent="generate_instance", report_name=ret["name"],
            response_text=error_msg,
            result_type="gen_awaiting_date",
            options=suggestions,
        )

    api_result = await call_generate_api(ret["form_id"], reporting_date, asp_session)
    if session_id:
        _session_context.pop(session_id, None)

    if api_result["success"]:
        logger.info(
            "[GENERATE_SUCCESS] report=%r date=%s session=%s",
            ret["name"], reporting_date, session_id,
        )
        return _build(
            intent="generate_instance", report_name=ret["name"],
            response_text=(
                f"Generating instance for '{ret['name']}'"
                f"\nReporting Date : {reporting_date}"
                f"\nStatus         : {api_result['message']}"
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
) -> dict[str, Any]:
    """Thin wrapper: assemble ret dict from session and delegate to _finalize_generation."""
    ret = {
        "form_id":     session["gen_form_id"],
        "name":        session["gen_return_name"],
        "frequency":   session["gen_frequency"],
        "period_name": session.get("gen_period_name", ""),
    }
    return await _finalize_generation(ret, date_str, session_id, asp_session)


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
            "\u2022 31-Mar", "\u2022 30-Jun", "\u2022 30-Sep", "\u2022 31-Dec",
            "", f"Example: 31-Mar-{year}",
        ]
    elif freq == "M":
        today = _date.today()
        last  = _cal.monthrange(today.year, today.month)[1]
        mname = today.strftime("%b")
        lines += [
            "Monthly reports must use the last day of the month.",
            "", f"Example: {last:02d}-{mname}-{year}",
        ]
    elif freq == "H":
        lines += [
            "Half Yearly reports must use:",
            "\u2022 31-Mar", "\u2022 30-Sep",
            "", f"Example: 31-Mar-{year}",
        ]
    elif freq == "C":
        lines += [
            "Half Yearly (Calendar Year) reports must use:",
            "\u2022 30-Jun", "\u2022 31-Dec",
            "", f"Example: 30-Jun-{year}",
        ]
    elif freq == "Y":
        lines += [
            "Yearly (Financial Year) reports must use:",
            "\u2022 31-Mar",
            "", f"Example: 31-Mar-{year}",
        ]
    elif freq == "B":
        lines += [
            "Yearly (Calendar Year) reports must use:",
            "\u2022 31-Dec",
            "", f"Example: 31-Dec-{year}",
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
            "\u2022 15th of the month",
            "\u2022 Last day of the month",
            "", f"Example: 15-{mname}-{year} or {last:02d}-{mname}-{year}",
        ]
    elif freq == "E":
        lines += [
            "This report must use the last Friday of the month.",
        ]
    elif freq == "D":
        lines += [
            "Daily reports accept any valid past date.",
            "", f"Example: 26-May-{year}",
        ]
    else:
        lines += [
            f"Enter a valid reporting date for this {label} report.",
            "", f"Example: 31-Mar-{year}",
        ]

    return "\n".join(lines)


async def _handle_generate(
    report_name: str,
    reporting_date: str | None,
    session_id: str | None,
    asp_session: str | None = None,
    allowed_form_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Entry point for generate_instance intent from the normal (non-staged) flow."""
    matches = find_matching_reports(report_name)
    if allowed_form_ids is not None:
        matches = [m for m in matches if m.get("Id", "").strip() in allowed_form_ids]

    if not matches:
        suggestions = fuzzy_report_suggestions(report_name)
        if allowed_form_ids is not None:
            suggestions = _filter_names_by_auth(suggestions, allowed_form_ids)
        if suggestions:
            if session_id:
                _session_context[session_id] = {
                    "awaiting":           STAGE_GEN_REPORT,
                    "gen_reporting_date": None,
                    "pending_options":    suggestions,
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
        if allowed_form_ids is not None:
            return _build(
                intent="generate_instance", report_name=None,
                response_text="You are not authorised to access any matching reports.",
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
                "awaiting":           STAGE_GEN_REPORT,
                "gen_reporting_date": None,
                "pending_options":    names,
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
    return await _finalize_generation(ret, reporting_date, session_id, asp_session)


def _build(
    intent: str,
    report_name: str | None,
    response_text: str = "",
    need_clarification: bool = False,
    result_type: str = "",
    options: list[str] | None = None,
    scheduled_datetime: str | None = None,
    schedule_date: str | None = None,
    schedule_time: str | None = None,
    variance_data:    list[dict] | None = None,
    variance_label_a: str | None = None,
    variance_label_b: str | None = None,
    llm_summary:      str | None = None,
    instances_data:   list[dict] | None = None,
    download_url:     str = "",
    download_label:   str = "",
    status_note:      str = "",
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "intent":             intent,
        "report_name":        report_name,
        "response_text":      response_text,
        "need_clarification": need_clarification,
        "result_type":        result_type,
        "options":            options or [],
        "download_url":       download_url,
        "download_label":     download_label,
        "status_note":        status_note,
    }
    if scheduled_datetime is not None:
        out["scheduled_datetime"] = scheduled_datetime
    if schedule_date is not None:
        out["schedule_date"] = schedule_date
    if schedule_time is not None:
        out["schedule_time"] = schedule_time
    if variance_data is not None:
        out["variance_data"]    = variance_data
        out["variance_label_a"] = variance_label_a or ""
        out["variance_label_b"] = variance_label_b or ""
        out["llm_summary"]      = llm_summary or ""
    if instances_data is not None:
        out["instances_data"] = instances_data
    return out


# ---------------------------------------------------------------------------
# Authorisation helpers
# ---------------------------------------------------------------------------

def _filter_names_by_auth(names: list[str], allowed: set[str] | None) -> list[str]:
    """Return only the report names whose FormId is in *allowed*.

    If *allowed* is ``None`` (no auth configured) all names pass through.
    """
    if allowed is None:
        return names
    result = []
    for name in names:
        fid = get_form_id_by_name(name) or ""
        if fid in allowed:
            result.append(name)
    return result


def _check_name_auth(report_name: str, allowed: set[str] | None, intent: str) -> dict[str, Any] | None:
    """Return an auth-error response dict if *report_name*'s FormId is not in *allowed*.

    Returns ``None`` when access is granted (either no auth configured, or
    the FormId is explicitly in the allowed set).
    """
    if allowed is None:
        return None
    fid = get_form_id_by_name(report_name) or ""
    if fid not in allowed:
        logger.warning(
            "[AUTH_DENY] report=%r form_id=%r not in allowed set", report_name, fid
        )
        return _build(
            intent=intent,
            report_name=report_name,
            response_text="You are not authorised to access this report.",
            result_type="error",
        )
    return None


def _apply_auth_to_status_result(result: dict[str, Any], allowed: set[str]) -> dict[str, Any]:
    """Post-filter a ``get_report_status`` result dict through the auth set.

    Handles all result types returned by ``get_report_status``:
    - ``disambiguation``  — filter options list; error if none remain
    - ``date_selection``  — check form_id directly
    - ``run_selection``   — check form_id directly
    - ``final``           — look up FormId by report name and check
    - ``error``           — pass through unchanged
    """
    rtype = result.get("type", "")

    if rtype == "disambiguation":
        filtered = _filter_names_by_auth(result.get("options", []), allowed)
        if not filtered:
            return {
                "type":    "error",
                "message": "You are not authorised to access any of the matching reports.",
            }
        if len(filtered) < len(result.get("options", [])):
            opts_text = "\n".join(f"{i + 1}. {n}" for i, n in enumerate(filtered))
            return {
                **result,
                "options": filtered,
                "message": (
                    "Found multiple matching reports. Which one do you mean?\n\n"
                    f"{opts_text}"
                ),
            }
        return result

    if rtype in ("date_selection", "run_selection"):
        fid = result.get("form_id", "")
        if fid not in allowed:
            logger.warning("[AUTH_DENY] form_id=%r not in allowed set (status result)", fid)
            return {"type": "error", "message": "You are not authorised to access this report."}
        return result

    if rtype == "final":
        fid = get_form_id_by_name(result.get("report_name", "")) or ""
        if fid not in allowed:
            logger.warning(
                "[AUTH_DENY] report=%r form_id=%r not in allowed set (final result)",
                result.get("report_name"), fid,
            )
            return {"type": "error", "message": "You are not authorised to access this report."}
        return result

    if rtype == "latest_with_ask":
        # Result returned when report has multiple instances and user is shown the latest.
        # form_id is always present in this result type (set by _build_status_result).
        fid = result.get("form_id", "")
        if fid not in allowed:
            logger.warning(
                "[AUTH_DENY] form_id=%r not in allowed set (latest_with_ask result)", fid
            )
            return {"type": "error", "message": "You are not authorised to access this report."}
        return result

    # "error" type: check _form_id if present — avoids leaking that a report
    # exists (e.g. "Report X exists but no instances") to unauthorised users.
    fid = result.get("_form_id", "")
    if fid and fid not in allowed:
        logger.warning(
            "[AUTH_DENY] form_id=%r not in allowed set (error result with _form_id)", fid
        )
        return {"type": "error", "message": "You are not authorised to access this report."}
    return result  # generic error / unknown — pass through