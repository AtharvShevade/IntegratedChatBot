# agent/__init__.py -- Pipeline: intent → entity resolution → lookup → response.
# Session tracks last_search_terms and multi-turn stage state.

from __future__ import annotations

import logging
import os
import re
import threading
import time
import uuid as _uuid_mod
from typing import Any

import uuid
import asyncio

from rapidfuzz import process as _fuzz
from backend.llm_extractor import (
    _STOP_WORDS,
    extract_intent_and_entities,
    parse_and_format_date,
    extract_schedule_datetime,
    extract_reporting_and_schedule_datetime,
    _extract_search_terms as extract_search_terms,
    _extract_date_from_query,
    _BROAD_DATE_RE as _DATE_STRIP_RE,
    preprocess_generate_query,
)
from backend.services.llm_service import chat_response, classify_conversational_intent
from backend.tools.instance_generator import (
    call_generate_api,
    call_generate_api_6_0,
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
    get_instance_by_dtc_fast,          # ← new
    get_report_status,
    get_report_status_fast,
    get_report_status_exact,
    get_report_status_exact_fast,      # ← new
    _FAILED_STATUSES,
    _get_download_info,
    get_instances_by_form_id,
    _safe_status,
    _dtc_sort_key,
)

# ── In-memory async error-enrichment job store ────────────────────────────────
# Structure: { job_id: {"status": "pending"|"done", "payload": dict|None} }
# For multi-worker deployments replace with Redis.
_error_jobs: dict[str, dict] = {}


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
        _error_jobs[job_id] = {
            "status": "done",
            "payload": {"error_messages": [], "error_details": []},
        }



def _get_instance_by_dtc_fast_with_bg_job(
    form_id: str, dtc: str, return_name: str, tenant_id: str | None = None
) -> dict:
    """Call get_instance_by_dtc_fast and kick off background LLM enrichment
    for failed statuses."""
    result = get_instance_by_dtc_fast(form_id, dtc, return_name, tenant_id)

    if (
        result.get("type") == "final"
        and result.get("status_code") in _FAILED_STATUSES
        and result.get("error_count", 0) > 0
    ):
        job_id = str(_uuid_mod.uuid4())
        _error_jobs[job_id] = {"status": "pending", "payload": None}

        instances   = get_instances_by_form_id(form_id, tenant_id)
        target_dtc  = result["dtc"]
        row         = next(
            (r for r in instances if r.get("DTC", "").strip() == target_dtc), None
        )
        if row:
            code = _safe_status(row)
            dl   = _get_download_info(row, form_id, tenant_id)
            thread = threading.Thread(
                target=_run_error_enrichment_async,
                args=(job_id, form_id, row, dl, code),
                daemon=True,
            )
            thread.start()
            result["job_id"] = job_id

    return result


def _get_instance_by_date_fast_with_bg_job(
    form_id: str, date_query: str, return_name: str, tenant_id: str | None = None
) -> dict:
    """Find instance by reporting date, then apply the fast+bg-job pattern."""
    rows = get_instances_by_form_id(form_id, tenant_id)
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
            "available_instances": get_available_instances(form_id, tenant_id),
        }
    dtc = row.get("DTC", "").strip()
    return _get_instance_by_dtc_fast_with_bg_job(form_id, dtc, return_name, tenant_id)


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


def _get_status_fast_with_bg_job(query: str, tenant_id: str | None = None) -> dict:
    """Call get_report_status_fast and, for failed statuses with errors, kick off
    background LLM enrichment.  Returns the result dict with job_id attached when
    a background job was started.
    """
    result = get_report_status_fast(query, tenant_id)


    if (
        result.get("type") in ("final", "latest_with_ask")
        and result.get("status_code") in _FAILED_STATUSES
        and result.get("error_count", 0) > 0
    ):
        job_id = str(_uuid_mod.uuid4())
        _error_jobs[job_id] = {"status": "pending", "payload": None}

        form_id     = result["form_id"]
        instances   = get_instances_by_form_id(form_id, tenant_id)
        sorted_rows = sorted(instances, key=_dtc_sort_key, reverse=True)
        latest_row  = sorted_rows[0]
        code        = _safe_status(latest_row)
        dl          = _get_download_info(latest_row, form_id, tenant_id)

        thread = threading.Thread(
            target=_run_error_enrichment_async,
            args=(job_id, form_id, latest_row, dl, code),
            daemon=True,
        )
        thread.start()

        result["job_id"]      = job_id
        result["result_type"] = result.get("result_type", "final")

    return result


logger = logging.getLogger(__name__)

# Stage constants -- stored in session under key "awaiting"
STAGE_DATE         = "AWAITING_DATE_SELECTION"    # status: picking a date
STAGE_REPORT       = "AWAITING_REPORT_SELECTION"  # status: picking from disambiguation
STAGE_GEN_REPORT   = "AWAITING_GEN_REPORT"        # generate: picking from disambiguation
STAGE_GEN_DATE     = "AWAITING_GEN_DATE"          # generate: providing reporting date
STAGE_RUN          = "AWAITING_RUN_SELECTION"      # status: picking a run by timestamp
STAGE_SCHED_REPORT = "AWAITING_SCHED_REPORT"      # schedule: picking from disambiguation
STAGE_SCHED_RPT_DATE = "AWAITING_SCHED_REPORTING_DATE"  # schedule: providing reporting (period) date
STAGE_SCHED_DT      = "AWAITING_SCHED_DATETIME"    # schedule: providing date and time
STAGE_SCHED_CONFIRM = "AWAITING_SCHED_CONFIRM"      # schedule: awaiting user confirmation
STAGE_SCHED_NAME    = "AWAITING_SCHED_NAME"          # schedule: re-entering report name after Change Data
STAGE_CMP_REPORT    = "AWAITING_CMP_REPORT"         # compare: picking report from disambiguation
STAGE_CMP_FILE     = "AWAITING_CMP_FILE"            # compare: confirming which 2 instances
STAGE_PREV_DATES   = "AWAITING_PREV_DATES_CONFIRM"  # status: yes/no for previous dates
STAGE_RETURN_QA = "AWAITING_RETURN_QA_SELECTION"  # db_qa: picking a return from disambiguation (any return-scoped intent)

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

# Compare keyword detector — signals compare/variance/comparative-analysis workflow intent.
# Catches: compare, comparative, comparative analysis, comparison, comparing, variance, etc.
# Prevents compare queries from leaking into the SQL or QA fast-paths.
_CMP_KW_RE = re.compile(
    r'\b(compar\w*|versus|vs\.?|varianc\w*|contrast|differences?\s+between|side.?by.?side)\b',
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
_CMP_STEMS    = ['compar', 'varian']   # compare*, comparative*, comparison*, variance*
_CMP_FUZZY_KWS = ['compare', 'comparative', 'comparison', 'variance', 'contrast']


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


def _fuzzy_has_compare(text: str) -> bool:
    """True if any word in text fuzzy-matches or stem-matches a compare/comparative keyword.

    Catches: compare, comparative, comparison, comparing, variance, contrast
    and common typos (compar, comparitive, etc.).
    """
    if _CMP_KW_RE.search(text):
        return True
    words = re.findall(r'[a-zA-Z]{4,}', text.lower())
    for w in words:
        if any(w.startswith(s) for s in _CMP_STEMS):
            return True
        if _fuzz.extractOne(w, _CMP_FUZZY_KWS, score_cutoff=_FUZZY_THRESHOLD):
            return True
    return False


def _normalise_conversational(text: str) -> str:
    normalized = re.sub(r'[^a-zA-Z0-9 ]+', '', text.lower()).strip()
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized


def _get_conversational_response(text: str) -> str | None:
    normalized = _normalise_conversational(text)
    if not normalized:
        return None

    greetings = {
        'hi', 'hello', 'hey', 'good morning', 'good afternoon',
        'good evening', 'greetings',
    }
    acknowledgements = {
        'ok', 'okay', 'thanks', 'thank you', 'bye', 'goodbye',
        'good night', 'yes', 'no', 'sure', 'fine', 'cool', 'great',
        'nice', 'awesome', 'perfect',
    }

    if normalized in greetings:
        if normalized == 'good morning':
            return 'Good morning! How can I assist you with your reports today?'
        if normalized == 'good afternoon':
            return 'Good afternoon! How can I assist you with your reports today?'
        if normalized == 'good evening':
            return 'Good evening! How can I assist you with your reports today?'
        return (
            'Hello! How can I help you today? '
            'I can assist with report status, report generation, scheduling, '
            'and data-related queries.'
        )

    if normalized in acknowledgements:
        if normalized in {'thanks', 'thank you'}:
            return 'You\'re welcome! Let me know if you need any help with reports or data queries.'
        if normalized in {'bye', 'goodbye'}:
            return 'Goodbye! Have a great day.'
        if normalized == 'good night':
            return 'Good night! If you need anything else, I\'m here to help.'
        return 'Great! Let me know whenever you\'d like help with a report or data query.'

    return None
# Date pattern -- used to extract a date from free-text messages in STAGE_GEN_DATE
_DATE_RE = re.compile(
    r'\b(\d{1,2}-(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)-\d{4})\b', re.I
)

_STATUS_GENERIC_TERMS = frozenset({
    "database", "missing", "unknown", "not", "found", "any",
    "some", "all", "please", "tell", "me", "show", "give",
    "check", "status", "report", "reports", "instance", "instances",
})


def _extract_status_search_terms(text: str) -> str:
    """Extract likely report-identifying tokens from a status-style query.

    Uses the shared query extractor plus an additional generic-token filter
    so generic status requests do not trigger report lookup on words like
    "database" or "missing".
    """
    terms = extract_search_terms(text)
    if not terms:
        return ""

    tokens = terms.split()
    if all(token.lower() in _STATUS_GENERIC_TERMS for token in tokens):
        return ""
    return terms


def _is_generic_status_terms(terms: str) -> bool:
    """Return True when a status search string contains only generic tokens."""
    if not terms:
        return False
    tokens = terms.split()
    return bool(tokens) and all(token.lower() in _STATUS_GENERIC_TERMS for token in tokens)


def _is_meaningful_report_terms(terms: str | None) -> bool:
    """Return True when terms likely identify a report rather than generic status text."""
    if not terms:
        return False
    return not _is_generic_status_terms(terms)


# ---------------------------------------------------------------------------
# Schedule-specific search-term extraction helpers
# ---------------------------------------------------------------------------

# Month+day without year — "31 June", "Apr 15", "15 March" etc.
# Used in schedule term extraction to strip bare month/day references.
_MONTH_DAY_NO_YEAR_RE = re.compile(
    r'\b\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May'
    r'|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?'
    r'|Nov(?:ember)?|Dec(?:ember)?)\b'
    r'|\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May'
    r'|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?'
    r'|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2}\b',
    re.I,
)

# Time-expression pattern for schedule term extraction.
# Strips "10 am", "4 PM", "16:00", "10:30 am" etc.
_SCHED_TIME_RE = re.compile(
    r'\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\b|\b\d{1,2}:\d{2}\b', re.I
)

# Words that pollute report-name extraction in a scheduling context but are
# not already covered by the shared _STOP_WORDS in llm_extractor.py.
_SCHED_EXTRA_STOP = frozenset({
    "generation", "generating",
    "instances",
})


def _extract_schedule_search_terms(text: str) -> str:
    """Extract report-identifying tokens from a scheduling query.

    Strips: full dates (with year), time tokens, bare month/day pairs (no year),
    and all schedule/generate filler words so that a query like
    'schedule instance generation for cims raq at 10 am on 15 Apr 2026'
    correctly yields 'cims raq'.
    """
    # 1. Strip full date expressions (year present)
    clean = _DATE_STRIP_RE.sub(" ", text)
    # 2. Strip time tokens ("10 am", "4 PM", "16:00")
    clean = _SCHED_TIME_RE.sub(" ", clean)
    # 3. Strip bare month+day without year ("31 June", "Jun 15")
    clean = _MONTH_DAY_NO_YEAR_RE.sub(" ", clean)
    # 4. Use the shared extractor (already strips schedule/generate/filler words)
    terms = extract_search_terms(clean)
    # 5. Post-filter: remove any remaining schedule-context words
    words = [w for w in terms.split() if w.lower() not in _SCHED_EXTRA_STOP]
    terms = " ".join(words).strip()
    # 6. Treat generic status/report filler terms as no report name.
    if terms and all(token.lower() in _STATUS_GENERIC_TERMS for token in terms.split()):
        return ""
    return terms


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
        STAGE_RUN, STAGE_SCHED_REPORT, STAGE_SCHED_RPT_DATE, STAGE_SCHED_DT, STAGE_SCHED_CONFIRM,
        STAGE_SCHED_NAME, STAGE_CMP_REPORT, STAGE_CMP_FILE, STAGE_PREV_DATES,
        STAGE_RETURN_QA,
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
    """True when the message looks like a fresh status, generate, schedule,
    or db_qa (USER/DEPARTMENT/ROLE/ROLE_ACCESS/return-metadata, etc.) intent.

    Uses fuzzy matching so typos like 'stats of raq', 'gnearte cims', 'schdule raq' still work.
    This gates every "awaiting X" session stage below — without the db_qa
    check, a message like "what is the next reporting date for CIMS_DNBS4a"
    sent right after an unrelated report-status lookup gets misread as an
    answer to that stage's pending prompt (e.g. parsed as a generate-instance
    date) instead of being recognised as an unrelated fresh question.
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
        if any(w not in _STOP_WORDS for w in words):
            return True
    from backend.agent.db_qa_router import check_new_taxonomy_intent, check_db_qa_intent
    db_intent, _ = check_new_taxonomy_intent(text)
    if not db_intent:
        db_intent, _ = check_db_qa_intent(text)
    return bool(db_intent)


def _normalise_conversational(text: str) -> str:
    normalized = re.sub(r'[^a-zA-Z0-9 ]+', '', text.lower()).strip()
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized


def _get_conversational_response(text: str) -> str | None:
    normalized = _normalise_conversational(text)
    if not normalized:
        return None

    greetings = {
        'hi', 'hello', 'hey', 'good morning', 'good afternoon',
        'good evening', 'greetings',
    }
    acknowledgements = {
        'ok', 'okay', 'thanks', 'thank you', 'bye', 'goodbye',
        'good night', 'yes', 'no', 'sure', 'fine', 'cool', 'great',
        'nice', 'awesome', 'perfect',
    }

    if normalized in greetings:
        if normalized == 'good morning':
            return 'Good morning! How can I assist you with your reports today?'
        if normalized == 'good afternoon':
            return 'Good afternoon! How can I assist you with your reports today?'
        if normalized == 'good evening':
            return 'Good evening! How can I assist you with your reports today?'
        return (
            'Hello! How can I help you today? '
            'I can assist with report status, report generation, scheduling, '
            'and data-related queries.'
        )

    if normalized in acknowledgements:
        if normalized in {'thanks', 'thank you'}:
            return 'You\'re welcome! Let me know if you need any help with reports or data queries.'
        if normalized in {'bye', 'goodbye'}:
            return 'Goodbye! Have a great day.'
        if normalized == 'good night':
            return 'Good night! If you need anything else, I\'m here to help.'
        return 'Great! Let me know whenever you\'d like help with a report or data query.'

    return None


def _get_conversational_response_for_category(category: str) -> str | None:
    if category == 'greeting':
        return (
            'Hello! How can I help you today? '
            'I can assist with report status, report generation, scheduling, '
            'and data-related queries.'
        )
    if category == 'acknowledgement':
        return 'Great! Let me know whenever you\'d like help with a report or data query.'
    return None


async def _classify_conversational(text: str, history: list[dict] | None = None) -> str | None:
    try:
        category = await classify_conversational_intent(text, history=history)
    except Exception as exc:
        logger.warning('[CONVERSATIONAL_CLASSIFIER_FAIL] %s', exc)
        return None
    if category in {'greeting', 'acknowledgement'}:
        return category
    return None


def _resolve_report_name(
    user_query: str,
    llm_hint: str | None = None,
    tenant_id: str | None = None,
) -> tuple[str, list[dict]]:
    """Shared multi-candidate report name resolver used by ALL intents.

    Both status and generate flows call this so they get identical matching
    behaviour regardless of LLM extraction quality.

    Candidates are tried in priority order:
      1. LLM-extracted hint  (most precise when the model is correct)
      2. Intent/filler-stripped version  (_extract_search_terms)
         Strips words like "generate", "instance", "for" so that
         "generate instance for cims" → "cims" → matches CIMS_RAQ reports.
      3. Raw user query  (last resort — handles bare identifiers like "r091")

    Returns:
        (winning_candidate, matching_report_dicts)
        If no candidate produces a match, winning_candidate is the best
        non-empty candidate available (for use in error messages).
    """
    candidates: list[str] = []
    if llm_hint and llm_hint.strip():
        candidates.append(llm_hint.strip())
    stripped = extract_search_terms(user_query)
    if stripped and stripped not in candidates:
        candidates.append(stripped)
    raw = user_query.strip()
    if raw and raw not in candidates:
        candidates.append(raw)

    for candidate in candidates:
        matches = find_matching_reports(candidate, tenant_id)
        if matches:
            logger.debug(
                "[RESOLVE_REPORT] winner=%r matches=%d (llm_hint=%r)",
                candidate, len(matches), llm_hint,
            )
            return candidate, matches

    best = next((c for c in candidates if c), user_query.strip())
    return best, []


async def decide(
    user_query: str,
    session_id: str | None = None,
    asp_session: str | None = None,
    login_id: str | None = None,
    user_id: str | None = None,
    role_id: str | None = None,
    conversation_history: list[dict] | None = None,
    tenant_id: str | None = None,
    jwt: str | None = None,
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
    _REQUIRE_AUTH: bool = os.getenv("REQUIRE_AUTH", "false").lower() == "true"
    allowed_form_ids: set[str] | None = None
    if login_id:
        from backend.services.auth_service import get_allowed_form_ids as _get_auth
        from backend.services.auth_service import AUTHORIZATION_ENABLED as _AUTH_ENABLED
        allowed_form_ids = _get_auth(login_id, tenant_id)
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
    # ── Auth: resolve role_id from XML_User.xml when caller didn't supply it ──
    # The .NET app only passes loginId/uid — it never sends roleId.
    # Use auth_service.get_user_role_id() (same XML read already cached) so
    # every downstream handler (DB Q&A, SQL agent, etc.) sees the correct role.
    if login_id and (not role_id or role_id == "0"):
        from backend.services.auth_service import get_user_role_id as _get_role
        _resolved_role = _get_role(login_id, tenant_id)
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

    # Persist tenant_id (6.0) so staged flows keep it even if a later turn omits it
    if tenant_id and session_id:
        session["tenant_id"] = tenant_id
        _session_context[session_id] = session

    # Prefer the freshly-forwarded cookie; fall back to one stored earlier in session
    effective_asp = asp_session or session.get("asp_session")
    tenant_id = tenant_id or session.get("tenant_id")
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
            result = _get_instance_by_dtc_fast_with_bg_job(form_id, dtc_from_label, return_name, tenant_id)
            if result["type"] == "date_not_found":
                available = get_available_instances(form_id, tenant_id)
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
                result = _get_instance_by_date_fast_with_bg_job(form_id, user_query.strip(), return_name, tenant_id)

                if result["type"] == "date_not_found":
                    available = get_available_instances(form_id, tenant_id)
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
            auth_err = _check_name_auth(resolved_name, allowed_form_ids, "get_status", tenant_id)
            if auth_err:
                return auth_err
            result = _get_status_exact_fast_with_bg_job(resolved_name, tenant_id)
            if allowed_form_ids is not None:
                result = _apply_auth_to_status_result(result, allowed_form_ids, tenant_id)
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
                    conversation_history=conversation_history, tenant_id=tenant_id, jwt=jwt,
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
            return handle_db_qa_query(
                message=resolved_qa_name,
                intent=db_intent,
                params=db_params,
                user_id=final_user_id,
                role_id=final_role_id,
                beautify=True,
                model="phi3:mini",
                tenant_id=tenant_id,
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

            ret = resolve_return_exact(resolved_gen_name, tenant_id)
            if session_id:
                _session_context.pop(session_id, None)
            if not ret:
                return _build(
                    intent="generate_instance", report_name=None,
                    response_text=f"Report '{resolved_gen_name}' not found. Please try again.",
                    result_type="error",
                )
            auth_err = _check_name_auth(resolved_gen_name, allowed_form_ids, "generate_instance", tenant_id)
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
                return await _finalize_generation(ret, stored_date, session_id, effective_asp, tenant_id, jwt, login_id)
            # No pre-extracted date — ask the user for it.
            if session_id:
                _session_context[session_id] = {
                    "awaiting":        STAGE_GEN_DATE,
                    "gen_form_id":     ret["form_id"],
                    "gen_return_name": ret["name"],
                    "gen_frequency":   ret["frequency"],
                    "gen_period_name": ret["period_name"],
                    "tenant_id":       tenant_id,
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
            return await _handle_gen_date(date_str, session, session_id, effective_asp, tenant_id, jwt, login_id)

    # -- Schedule: re-enter report name after "Change Data" --------------------
    if not is_reset and session.get("awaiting") == STAGE_SCHED_NAME:
        if session_id:
            _session_context.pop(session_id, None)
        return _handle_schedule(user_query.strip(), None, None, None, session_id, allowed_form_ids, tenant_id, login_id, None)

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

            ret = resolve_return_exact(resolved_sched_name, tenant_id)
            if session_id:
                _session_context.pop(session_id, None)
            if not ret:
                return _build(
                    intent="schedule_report", report_name=None,
                    response_text=f"Report '{resolved_sched_name}' not found. Please try again.",
                    result_type="error",
                )
            auth_err = _check_name_auth(resolved_sched_name, allowed_form_ids, "schedule_report", tenant_id)
            if auth_err:
                return auth_err
            return _finalize_schedule(ret, saved_reporting_date, saved_sched_date, saved_sched_time, saved_sched_dt, session_id, tenant_id, login_id)

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
                session_id, tenant_id, login_id,
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
            return _finalize_schedule(sched_ret, reporting_date, schedule_date, schedule_time, scheduled_dt, session_id, tenant_id, login_id)

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
                    "No problem! Let\u2019s start over.\n"
                    "Please provide the report name for scheduling."
                ),
                result_type="sched_awaiting_name",
            )
        # "Schedule" button or any confirmation → finalize
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
            auth_err = _check_name_auth(selected, allowed_form_ids, "compare_reports", tenant_id)
            if auth_err:
                return auth_err
            return await _compare_with_name(selected, session_id, tenant_id)

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

        _has_workflow = (
            _fuzzy_has_status(user_query)
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
                    tenant_id=tenant_id,
                    login_id=login_id,
                    reporting_date=_sched_dt.get("reporting_date"),
                )

            if _fuzzy_has_status(user_query):
                raw_query = user_query.strip()
                extracted_query = _extract_status_search_terms(raw_query)
                if extracted_query:
                    matches = find_matching_reports(extracted_query, tenant_id)
                    if matches:
                        logger.info(
                            "[INTENT:STEP1] status fast-path matched %d report(s) session=%s",
                            len(matches), session_id,
                        )
                        if session_id:
                            _session_context[session_id] = {"last_search_terms": extracted_query, "tenant_id": tenant_id}
                        result = _get_status_fast_with_bg_job(extracted_query, tenant_id)
                        if allowed_form_ids is not None:
                            result = _apply_auth_to_status_result(result, allowed_form_ids, tenant_id)
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
                check_db_qa_intent, check_new_taxonomy_intent, handle_db_qa_query,
            )
            db_intent, db_params = check_new_taxonomy_intent(user_query)
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
                db_result = handle_db_qa_query(
                    message=user_query,
                    intent=db_intent,
                    params=db_params,
                    user_id=final_user_id,
                    role_id=final_role_id,
                    beautify=True,
                    model="phi3:mini",
                    tenant_id=tenant_id,
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
                return await handle_db_query(user_query, session_id=session_id)

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
            return handle_db_qa_query(
                message=user_query,
                intent=intent,
                params=extracted,  # Contains all LLM-extracted entities
                user_id=final_user_id,
                role_id=final_role_id,
                beautify=False,  # Disabled for speed
                tenant_id=tenant_id,
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
        return await handle_db_query(user_query, session_id=session_id)

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
            if _is_meaningful_report_terms(_candidate) and find_matching_reports(_candidate, tenant_id):
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
                return await _handle_compare(_matched_query, session_id, allowed_form_ids, tenant_id)
            if _fuzzy_has_schedule(user_query):
                logger.info(
                    "[UNKNOWN_RECLASSIFY] → schedule_report for %r session=%s",
                    _matched_query, session_id,
                )
                return _handle_schedule(
                    _matched_query, None, None, None, session_id, allowed_form_ids, tenant_id, login_id,
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
                    _matched_query, _fallback_date, session_id, effective_asp, allowed_form_ids, tenant_id, jwt, login_id
                )
            # Default: treat as a status query
            if session_id:
                _session_context[session_id] = {"last_search_terms": _matched_query, "tenant_id": tenant_id}
            result = _get_status_fast_with_bg_job(_matched_query, tenant_id)
            if allowed_form_ids is not None:
                result = _apply_auth_to_status_result(result, allowed_form_ids, tenant_id)
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
            search_terms, _direct_matches = _resolve_report_name(user_query, tenant_id=tenant_id)
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
        _gen_terms, _gen_matches = _resolve_report_name(_clean_gen_query, search_terms or None, tenant_id)
        if _gen_matches:
            search_terms = _gen_terms
        logger.info(
            "[GENERATE_START] report=%r date=%r (resolved) session=%s",
            search_terms, reporting_date, session_id,
        )
        return await _handle_generate(search_terms, reporting_date, session_id, effective_asp, allowed_form_ids, tenant_id, jwt, login_id)

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
            tenant_id=tenant_id,
            login_id=login_id,
            reporting_date=_rpt_date,
        )

    if intent == "compare_reports":
        logger.info("[COMPARE_START] report=%r session=%s", search_terms, session_id)
        return await _handle_compare(search_terms, session_id, allowed_form_ids, tenant_id)

    # get_status: cache search terms so follow-up turns work without a name
    if session_id:
        _session_context[session_id] = {"last_search_terms": search_terms, "tenant_id": tenant_id}

    # Always pass the raw search_terms (the user's partial/keyword input) to
    # get_report_status so that find_matching_reports can detect multiple hits
    # and surface a disambiguation list. Using the entity resolver's resolved
    # name here bypasses that check and jumps directly to instance lookup,
    # which gives a misleading "No instances found" when the user typed only
    # a partial name like "raq".
    result = _get_status_fast_with_bg_job(search_terms or user_query, tenant_id)
    if allowed_form_ids is not None:
        result = _apply_auth_to_status_result(result, allowed_form_ids, tenant_id)
    _decide_elapsed = time.monotonic() - _decide_start
    logger.info(
        "[PERF] operation=decide intent=%s duration=%.2fs session=%s",
        intent, _decide_elapsed, session_id,
    )
    return _from_result(result, intent=intent, session_id=session_id)


# ---------------------------------------------------------------------------
# Compare helpers
# ---------------------------------------------------------------------------

async def _handle_compare(report_ident: str, session_id: str | None, allowed_form_ids: set[str] | None = None, tenant_id: str | None = None) -> dict[str, Any]:
    """Entry point for compare_reports intent — handles disambiguation."""
    matches = find_matching_reports(report_ident, tenant_id)
    all_matches = matches
    if allowed_form_ids is not None:
        matches = [m for m in matches if m.get("Id", "").strip() in allowed_form_ids]

    if not matches:
        suggestions = fuzzy_report_suggestions(report_ident, tenant_id=tenant_id)
        if allowed_form_ids is not None:
            suggestions = _filter_names_by_auth(suggestions, allowed_form_ids)
        if suggestions:
            opts_text = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(suggestions))
            if session_id:
                _session_context[session_id] = {
                    "awaiting": STAGE_CMP_REPORT, "pending_options": suggestions, "tenant_id": tenant_id,
                }
            return _build(
                intent="compare_reports", report_name=None,
                response_text=(
                    f"No exact match for '{report_ident}'. Did you mean:\n\n"
                    f"{opts_text}\n\nReply with the number."
                ),
                result_type="disambiguation", options=suggestions,
            )
        if allowed_form_ids is not None and all_matches:
            return _build(
                intent="compare_reports", report_name=None,
                response_text="You are not authorised to access this report.",
                result_type="error",
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
                "awaiting": STAGE_CMP_REPORT, "pending_options": names, "tenant_id": tenant_id,
            }
        return _build(
            intent="compare_reports", report_name=None,
            response_text=(
                f"I found {len(names)} matching reports. Which one to compare?\n\n"
                f"{opts_text}\n\nReply with the name."
            ),
            result_type="disambiguation", options=names,
        )

    return await _compare_with_name(matches[0].get("Name", report_ident), session_id, tenant_id)


async def _compare_with_name(name: str, session_id: str | None, tenant_id: str | None = None) -> dict[str, Any]:
    """Resolve Report ID → scan instance folder → present selection.

    Only path: Returns.xml → Report ID → {INSTANCE_BASE_DIR}/{id}/ → *.xml
    No fallbacks to XML_InstanceLog or logs/ prefix scan.
    """
    from backend.services.instance_service import get_instances_for_report

    # ── Step 1: resolve report name to FormId via Returns.xml ─────────────────
    form_id = get_form_id_by_name(name, tenant_id)
    if not form_id:
        if session_id:
            _session_context.pop(session_id, None)
        return _build(
            intent="compare_reports", report_name=name,
            response_text=(
                f"Report '{name}' was not found in Returns.xml. "
                "Please check the report name and try again."
            ),
            result_type="error",
        )

    # ── Step 2: scan Instance/{FormId}/ — no fallbacks ────────────────────────
    instances = get_instances_for_report(form_id, tenant_id)

    # ── Error guards ──────────────────────────────────────────────────────────
    # Always clear session on error so stale STAGE_CMP_REPORT / STAGE_CMP_FILE
    # cannot interfere with the user's next request.
    if not instances:
        if session_id:
            _session_context.pop(session_id, None)
        return _build(
            intent="compare_reports", report_name=name,
            response_text=(
                f"No instance files found for '{name}' (FormId: {form_id}). "
                # f"The folder Instance/{form_id}/ does not exist or contains no XML files."
            ),
            result_type="error",
        )

    if len(instances) < 2:
        if session_id:
            _session_context.pop(session_id, None)
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
            "tenant_id":       tenant_id,
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
                          response_text="Unable to perform the comparison right now. Please try again.", result_type="error")
        except Exception as exc:
            logger.error("XBRL load error: %s", exc, exc_info=True)
            return _build(intent="compare_reports", report_name=name,
                          response_text="Unable to perform the comparison right now. Please try again.",
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
            response_text="Unable to perform the comparison right now. Please try again.", result_type="error",
        )
    except Exception as exc:
        logger.error("XBRL load error: %s", exc, exc_info=True)
        return _build(
            intent="compare_reports", report_name=name,
            response_text="Unable to perform the comparison right now. Please try again.",
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
    tenant_id: str | None = None,
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
    # instances[*]["full_path"] was already resolved tenant-aware by
    # _compare_with_name when the session was created — no further path
    # resolution is needed here. tenant_id is accepted for API consistency
    # with the other endpoints and kept in the session copy.
    session_copy = dict(session)
    session_copy["auto_a"] = idx_a
    session_copy["auto_b"] = idx_b
    session_copy["tenant_id"] = tenant_id or session.get("tenant_id")
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
        job_id          = result.get("job_id")
        status_code     = result.get("status_code")
        error_category_counts = result.get("error_category_counts") or None
        is_4000_series = result.get("is_4000_series", False)   # ADD THIS

        text = (
            f"{ret_name}\n"
            f"Latest Reporting Date : {rep_date}\n"
            f"Status                : {status}"
        )
        if run_time:
            text += f"\nGenerated On          : {run_time}"
        if job_id:
            error_count = result.get("error_count", 0)
            if error_count > 0:
                text += f"\n\nErrors Found : {error_count}\n\nGenerating error explanations\u2026"
        else:
            error_messages = result.get("error_messages", [])
            if error_messages:
                text += "\n\nFailure Reason(s):\n"
                text += "\n".join(f"\u2022 {m}" for m in error_messages)
        if status_note:
            text += f"\n{status_note}"

        response_data: dict[str, Any] = {}
        if status_code is not None:
            response_data["status_code"] = status_code
        if error_category_counts:
            response_data["error_category_counts"] = error_category_counts
        response_data["is_4000_series"] = is_4000_series   # ADD THIS
        response_data["form_id"] = result.get("form_id", "")   # ← ADD THIS LINE


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
                error_details=result.get("error_details") or None,
                job_id=job_id,
                data=response_data,
            )
        # No other instances — just show final status
        return _build(intent=intent, report_name=ret_name,
                      response_text=text, result_type="final",
                      download_url=result.get("download_url", ""),
                      download_label=result.get("download_label", ""),
                      error_details=result.get("error_details") or None,
                      job_id=job_id,
                      data=response_data)

    if rtype == "final":
        dtc    = result.get("dtc", "")
        job_id = result.get("job_id")
        status_code = result.get("status_code")
        error_category_counts = result.get("error_category_counts") or None
        is_4000_series = result.get("is_4000_series", False)   # ADD THIS

        text = (
            f"{result['report_name']}\n"
            f"Reporting Date : {result['reporting_date']}\n"
        )
        if dtc:
            text += f"Generated On   : {dtc}\n"
        text += f"Status         : {result['status']}"
        if job_id:
            error_count = result.get("error_count", 0)
            if error_count > 0:
                text += f"\n\nErrors Found : {error_count}\n\nGenerating error explanations\u2026"
        else:
            error_messages = result.get("error_messages", [])
            if error_messages:
                text += "\n\nFailure Reason(s):\n"
                text += "\n".join(f"\u2022 {m}" for m in error_messages)
        status_note = result.get("status_note", "")
        if status_note:
            text += f"\n{status_note}"
        if keep_date_ctx:
            text += '\n\nYou can select another reporting date, or say "new report" to switch reports.'

        response_data: dict[str, Any] = {}
        if status_code is not None:
            response_data["status_code"] = status_code
        if error_category_counts:
            response_data["error_category_counts"] = error_category_counts
        response_data["is_4000_series"] = is_4000_series   # ADD THIS
        response_data["form_id"] = result.get("form_id", "")   # ← ADD THIS LINE

        return _build(intent=intent, report_name=result["report_name"],
                      response_text=text, result_type="final",
                      download_url=result.get("download_url", ""),
                      download_label=result.get("download_label", ""),
                      error_details=result.get("error_details") or None,
                      job_id=job_id,
                      data=response_data)

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
    error_messages = result.get("error_messages", [])
    if error_messages:
        text += "\n\nFailure Reason(s):\n"
        text += "\n".join(f"\u2022 {m}" for m in error_messages)
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
            text += f"\n\nErrors Found : {error_count}\n\nGenerating error explanations\u2026"
    else:
        # Synchronous path — error_messages already populated
        error_messages = result.get("error_messages", [])
        if error_messages:
            text += "\n\nFailure Reason(s):\n"
            text += "\n".join(f"\u2022 {m}" for m in error_messages)

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


# ---------------------------------------------------------------------------
# Generate instance helpers
# ---------------------------------------------------------------------------

def _validate_future_schedule_date(
    schedule_date: str, schedule_time: str | None, frequency: str = "",
) -> tuple[bool, str]:
    """Validate that ``schedule_date`` (+ optional ``schedule_time``) is a
    real, future calendar date that ALSO falls on a valid period-end date
    for ``frequency`` (e.g. 31-Mar/30-Jun/30-Sep/31-Dec for Quarterly) — the
    schedule date is the reporting period the generated instance is for, so
    it must satisfy the same frequency rules as reporting_date, just
    requiring a future (not past/current) date.

    Delegates to validate_reporting_date (require_future=True) so both
    dates share one frequency-validation implementation rather than
    duplicating the per-frequency rules here.

    Returns ``(is_valid, error_message)``.
    """
    result = validate_reporting_date(
        schedule_date, frequency, require_future=True, time_str=schedule_time,
    )
    return result["valid"], (result["error"] or "")


def _finalize_schedule(
    ret: dict[str, Any],
    reporting_date: str | None,
    schedule_date: str | None,
    schedule_time: str | None,
    scheduled_datetime: str | None,
    session_id: str | None,
    tenant_id: str | None = None,
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
         should actually run and generate the instance. Schedule Date is
         validated against the same frequency/period-boundary rules as
         Reporting Date (via ``_validate_future_schedule_date``, which
         delegates to ``validate_reporting_date`` with
         ``require_future=True``) — only future dates are accepted, but
         they must still land on a valid period-end for the report's
         frequency. Schedule Time itself has no frequency restriction.
      4. Confirmation (Schedule / Change Data).

    Handles partial input gracefully at every stage and re-prompts for
    whatever is still missing without discarding what's already been given.
    """
    # ── Auth: scheduling performs instance generation internally, so it
    # requires the same Instance Generation permission — single enforcement
    # point, covers guided menu, free-text, and staged date/confirm turns.
    if login_id:
        from backend.services.auth_service import can_generate_instance as _chk_create
        if not _chk_create(login_id, tenant_id):
            logger.warning(
                "[AUTH_DENY] schedule_report: login_id=%r tenant_id=%r lacks Instance Generation permission",
                login_id, tenant_id,
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
                    "tenant_id":             tenant_id,
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
                "tenant_id":             tenant_id,
            }
        return _build(
            intent="schedule_report",
            report_name=ret["name"],
            response_text=_date_ask_prompt(ret["name"], frequency, period_name),
            result_type="sched_awaiting_rpt_date",
        )

    # ── Schedule-date validation — must be a future date AND satisfy the
    # same frequency/period-boundary rules as reporting_date (e.g. only
    # 31-Mar/30-Jun/30-Sep/31-Dec for Quarterly).
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
                    "tenant_id":           tenant_id,
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
                "tenant_id":           tenant_id,
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
            "tenant_id":           tenant_id,
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
    tenant_id: str | None = None,
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

    matches = find_matching_reports(report_ident, tenant_id)
    if allowed_form_ids is not None:
        matches = [m for m in matches if m.get("Id", "").strip() in allowed_form_ids]

    if not matches:
        suggestions = fuzzy_report_suggestions(report_ident, tenant_id=tenant_id)
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
                    "tenant_id":           tenant_id,
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
                "tenant_id":           tenant_id,
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
    ret = resolve_return_exact(matches[0].get("Name", report_ident), tenant_id)
    if not ret:
        return _build(
            intent="schedule_report", report_name=None,
            response_text=f'Report "{report_ident}" could not be resolved. Please try again.',
            result_type="error",
        )

    return _finalize_schedule(ret, reporting_date, schedule_date, schedule_time, scheduled_datetime, session_id, tenant_id, login_id)


async def _finalize_generation(
    ret: dict[str, Any],
    reporting_date: str,
    session_id: str | None,
    asp_session: str | None = None,
    tenant_id: str | None = None,
    jwt: str | None = None,
    login_id: str | None = None,
) -> dict[str, Any]:
    """Validate date and call the .NET API for a fully-resolved (report, date) pair."""
    # ── Auth: role-based Instance Generation permission ───────────────────────
    # Single enforcement point for generate_instance — every path (guided menu,
    # free-text, staged date-entry) converges here before the .NET API call.
    if login_id:
        from backend.services.auth_service import can_generate_instance as _chk_create
        if not _chk_create(login_id, tenant_id):
            logger.warning(
                "[AUTH_DENY] generate_instance: login_id=%r tenant_id=%r lacks Instance Generation permission",
                login_id, tenant_id,
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
                "tenant_id":       tenant_id,
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

    if tenant_id:
        api_result = await call_generate_api_6_0(ret["form_id"], reporting_date, tenant_id, jwt)
    else:
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
    tenant_id: str | None = None,
    jwt: str | None = None,
    login_id: str | None = None,
) -> dict[str, Any]:
    """Thin wrapper: assemble ret dict from session and delegate to _finalize_generation."""
    ret = {
        "form_id":     session["gen_form_id"],
        "name":        session["gen_return_name"],
        "frequency":   session["gen_frequency"],
        "period_name": session.get("gen_period_name", ""),
    }
    tenant_id = tenant_id or session.get("tenant_id")
    return await _finalize_generation(ret, date_str, session_id, asp_session, tenant_id, jwt, login_id)


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
    tenant_id: str | None = None,
    jwt: str | None = None,
    login_id: str | None = None,
) -> dict[str, Any]:
    """Entry point for generate_instance intent from the normal (non-staged) flow."""
    matches = find_matching_reports(report_name, tenant_id)
    original_matches = matches
    if allowed_form_ids is not None:
        matches = [m for m in matches if m.get("Id", "").strip() in allowed_form_ids]

    if not matches:
        suggestions = fuzzy_report_suggestions(report_name, tenant_id=tenant_id)
        if allowed_form_ids is not None:
            suggestions = _filter_names_by_auth(suggestions, allowed_form_ids)
        if suggestions:
            if session_id:
                _session_context[session_id] = {
                    "awaiting":               STAGE_GEN_REPORT,
                    "pending_reporting_date": reporting_date,
                    "pending_options":        suggestions,
                    "tenant_id":              tenant_id,
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
                "tenant_id":              tenant_id,
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
    ret = resolve_return_exact(matches[0].get("Name", report_name), tenant_id)
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
                "tenant_id":       tenant_id,
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
    return await _finalize_generation(ret, reporting_date, session_id, asp_session, tenant_id, jwt, login_id)


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
    reporting_date_out: str | None = None,
    variance_data:    list[dict] | None = None,
    variance_label_a: str | None = None,
    variance_label_b: str | None = None,
    llm_summary:      str | None = None,
    instances_data:   list[dict] | None = None,
    download_url:     str = "",
    download_label:   str = "",
    status_note:      str = "",
    error_details:    list[dict] | None = None,
    job_id:           str | None = None,
    data:             dict[str, Any] | None = None,
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
    if reporting_date_out is not None:
        out["reporting_date"] = reporting_date_out
    if variance_data is not None:
        out["variance_data"]    = variance_data
        out["variance_label_a"] = variance_label_a or ""
        out["variance_label_b"] = variance_label_b or ""
        out["llm_summary"]      = llm_summary or ""
    if instances_data is not None:
        out["instances_data"] = instances_data
    if error_details:
        out["error_details"] = error_details
    if job_id is not None:
        out["job_id"] = job_id
    if data:
        out["data"] = data
    return out


# ---------------------------------------------------------------------------
# Authorisation helpers
# ---------------------------------------------------------------------------

def _filter_names_by_auth(names: list[str], allowed: set[str] | None, tenant_id: str | None = None) -> list[str]:
    """Return only the report names whose FormId is in *allowed*.

    If *allowed* is ``None`` (no auth configured) all names pass through.
    """
    if allowed is None:
        return names
    result = []
    for name in names:
        fid = get_form_id_by_name(name, tenant_id) or ""
        if fid in allowed:
            result.append(name)
    return result


def _check_name_auth(report_name: str, allowed: set[str] | None, intent: str, tenant_id: str | None = None) -> dict[str, Any] | None:
    """Return an auth-error response dict if *report_name*'s FormId is not in *allowed*.

    Returns ``None`` when access is granted (either no auth configured, or
    the FormId is explicitly in the allowed set).
    """
    if allowed is None:
        return None
    fid = get_form_id_by_name(report_name, tenant_id)
    if not fid:
        logger.warning(
            "[AUTH_MISS] report=%r could not be resolved to a FormId before auth", report_name,
        )
        return _build(
            intent=intent,
            report_name=report_name,
            response_text=(
                f"I couldn't find any report matching '{report_name}'.\n"
                "Please check the report name and try again."
            ),
            result_type="error",
        )
    in_allowed = fid in allowed
    logger.info(
        "[AUTH_CHECK] Requested Return: %r | Resolved FormId: %r | "
        "Allowed Forms Contains %r: %s | Authorization: %s",
        report_name, fid, fid, str(in_allowed).upper(),
        "Allowed" if in_allowed else "DENIED",
    )
    if not in_allowed:
        logger.warning(
            "[AUTH_DENY] report=%r form_id=%r not in allowed set (allowed has %d entries)",
            report_name, fid, len(allowed),
        )
        return _build(
            intent=intent,
            report_name=report_name,
            response_text="You are not authorised to access this report.",
            result_type="error",
        )
    return None


def _apply_auth_to_status_result(result: dict[str, Any], allowed: set[str], tenant_id: str | None = None) -> dict[str, Any]:
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
        filtered = _filter_names_by_auth(result.get("options", []), allowed, tenant_id)
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
        fid = get_form_id_by_name(result.get("report_name", ""), tenant_id) or ""
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

def _get_status_exact_fast_with_bg_job(report_name: str, tenant_id: str | None = None) -> dict:
    """Call get_report_status_exact_fast and kick off background LLM enrichment
    for failed statuses, exactly like _get_status_fast_with_bg_job."""
    result = get_report_status_exact_fast(report_name, tenant_id)

    if (
        result.get("type") in ("final", "latest_with_ask")
        and result.get("status_code") in _FAILED_STATUSES
        and result.get("error_count", 0) > 0
    ):
        job_id = str(_uuid_mod.uuid4())
        _error_jobs[job_id] = {"status": "pending", "payload": None}

        form_id     = result["form_id"]
        instances   = get_instances_by_form_id(form_id, tenant_id)
        sorted_rows = sorted(instances, key=_dtc_sort_key, reverse=True)
        latest_row  = sorted_rows[0]
        code        = _safe_status(latest_row)
        dl          = _get_download_info(latest_row, form_id, tenant_id)

        thread = threading.Thread(
            target=_run_error_enrichment_async,
            args=(job_id, form_id, latest_row, dl, code),
            daemon=True,
        )
        thread.start()

        result["job_id"]      = job_id
        result["result_type"] = result.get("result_type", "final")

    return result

# ---------------------------------------------------------------------------
# On-demand error category explanation (new — triggered by ErrorSummaryPanel)
# ---------------------------------------------------------------------------

_CATEGORY_DISPLAY = {
    "formula_error": "Formula Errors",
    "xbrl_schema":    "XBRL Schema Errors",
    "dimensional":    "Dimension Errors",
}


async def explain_category_for_report(
    error_file_path: str,
    category: str,
    form_id: str | None = None,
    report_name: str | None = None,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    """Explain up to 5 errors for the given category from error_file_path.

    Runs the existing on-demand explanation pipeline
    (explain_errors_by_category_for_form, unchanged) in a background thread
    since it performs blocking LLM calls, then formats the result as a
    chat-style response so the frontend can append it as a new bubble.
    """
    from backend.tools.report_lookup import explain_errors_by_category_for_form

    category_label = _CATEGORY_DISPLAY.get(category, category)

    if category not in ("formula_error", "xbrl_schema", "dimensional"):
        return _build(
            intent="explain_errors",
            report_name=report_name,
            response_text=f"Unsupported error category: {category}",
            result_type="error",
        )

    if not error_file_path:
        return _build(
            intent="explain_errors",
            report_name=report_name,
            response_text="No error file is available for this report.",
            result_type="error",
        )

    loop = asyncio.get_event_loop()
    try:
        explained = await loop.run_in_executor(
            None,
            explain_errors_by_category_for_form,
            error_file_path,
            category,
            form_id or "",
            tenant_id,
        )
    except Exception as exc:
        logger.error(
            "[EXPLAIN_CATEGORY] category=%s path=%s failed: %s",
            category, error_file_path, exc,
        )
        return _build(
            intent="explain_errors",
            report_name=report_name,
            response_text=(
                f"Sorry, I couldn't generate explanations for {category_label} right now. "
                "Please try again."
            ),
            result_type="error",
        )

    if not explained:
        return _build(
            intent="explain_errors",
            report_name=report_name,
            response_text=f"No {category_label.lower()} could be parsed from the error file.",
            result_type="error",
        )

    n = len(explained)
    text = f"⚙ {category_label} — showing {n} of up to 5"

    return _build(
        intent="explain_errors",
        report_name=report_name,
        response_text=text,
        result_type="final",
        error_details=explained,
    )
