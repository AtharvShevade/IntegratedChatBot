"""backend/agent/conversational.py — fuzzy workflow-keyword detection,
search-term extraction, staged-session gating, and small-talk handling.

Moved out of backend/agent/__init__.py verbatim — no logic changes.

Note: the original file defined _normalise_conversational and
_get_conversational_response TWICE (an accidental duplicate later in the
file silently shadowed the first, identical, definition at import time).
Only one copy is kept here — this removes dead code without changing
behavior, since the second definition already won at runtime before this
split.
"""

from __future__ import annotations

import re
import logging
from typing import Any

from rapidfuzz import process as _fuzz

from backend.llm_extractor import (
    _STOP_WORDS,
    _extract_search_terms as extract_search_terms,
    _BROAD_DATE_RE as _DATE_STRIP_RE,
)
# Imported as a package reference (not `from ... import classify_conversational_intent`)
# so that tests patching `backend.agent.classify_conversational_intent` — matching
# this name's original home as a top-level attribute of backend/agent/__init__.py
# — still take effect here. Safe despite looking circular: this module is only ever
# loaded FROM backend/agent/__init__.py, which sets that attribute before importing
# this module, and the attribute is only accessed later, inside a function body.
import backend.agent as _agent_pkg
from backend.agent.state import (
    STAGE_DATE, STAGE_REPORT, STAGE_GEN_REPORT, STAGE_GEN_DATE, STAGE_RUN,
    STAGE_SCHED_REPORT, STAGE_SCHED_RPT_DATE, STAGE_SCHED_DT, STAGE_SCHED_CONFIRM,
    STAGE_SCHED_NAME, STAGE_CMP_REPORT, STAGE_CMP_FILE, STAGE_PREV_DATES, STAGE_RETURN_QA,
    _STATUS_KW_RE, _STATUS_OF_RE, _GEN_KW_RE, _SCHED_KW_RE, _CMP_KW_RE,
)

logger = logging.getLogger(__name__)

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

# "created"/"creation" stem-match the 'crea' prefix in _GEN_STEMS, so a db_qa
# identity question like "who created my account" was fuzzy-matching
# _fuzzy_has_generate() and getting misrouted into the report-generation flow
# (self-test: doc/INTENT_GAP_ANALYSIS.md, "who created my account" → asked
# for a reporting date to generate an unrelated report). This should already
# be caught earlier by STEP2's db_qa USER_FIELD "who created my" rule — this
# is a defence-in-depth guard for whenever that rule doesn't fire (a
# rephrasing it doesn't cover, or db_qa disabled) so a 'created' stem-match
# alone can't win without an actual generate/instance-creation verb nearby.
_CREATED_NOT_GENERATE_RE = re.compile(
    r'\bwho\s+creat\w*\b|\bcreat\w*\s+(by|my)\b|\baccount\s+creat\w*\b',
    re.I,
)

# "Can I create new users?" / "Am I allowed to approve submissions?" / "Do I
# have permission to edit department settings?" are self-PERMISSION
# questions (db_qa's PERMISSION_CHECK intent — already has this exact
# phrasing as an exemplar in exemplars.py) but "create"/"approve"/"edit" all
# stem/keyword-match _fuzzy_has_generate or _fuzzy_has_schedule, so STEP1's
# report-workflow gate was winning before db_qa ever got a turn (self-test:
# doc/INTENT_GAP_ANALYSIS.md — "can I create new users" was misrouted to
# generate_instance, "I couldn't find any report matching 'users'"). A
# leading "can/could I", "am/are I allowed to", or "do I have permission to"
# is never itself a command to generate/schedule a report — it is always
# someone asking what THEY are permitted to do.
_PERMISSION_QUESTION_RE = re.compile(
    r'^\s*(can|could)\s+i\s+\w+'
    r'|\b(am|are)\s+i\s+allowed\s+to\b'
    r'|\bdo\s+i\s+have\s+permission\s+to\b',
    re.I,
)


# "checker"/"checkers" stem-match the 'chec' prefix in _STATUS_STEMS (meant
# for "check"/"checking" as in "check status"), but Checker is a real ROLE
# NAME in this domain's Maker-Checker workflow — "what access does the
# checker role have" was hijacked into the report-status fast-path at STEP1,
# short-circuiting before it ever reached db_qa/the embedding tier at all
# (found via the embedding-index self-test round, doc/INTENT_GAP_ANALYSIS.md
# — this was NOT a missing db_qa rule as earlier rounds assumed; the query
# never got that far).
def _fuzzy_has_status(text: str) -> bool:
    """True if any word in text fuzzy-matches or stem-matches a status keyword."""
    if _STATUS_KW_RE.search(text):
        return True
    words = re.findall(r'[a-zA-Z]{3,}', text.lower())
    for w in words:
        # Stem/prefix match: 'generating' starts with 'gene' → generate
        if any(w.startswith(s) for s in _STATUS_STEMS):
            if w in ("checker", "checkers"):
                continue
            return True
        # Fuzzy edit-distance match: catches transpositions/substitutions
        if _fuzz.extractOne(w, _STATUS_FUZZY_KWS, score_cutoff=_FUZZY_THRESHOLD):
            return True
    return False


def _fuzzy_has_generate(text: str) -> bool:
    """True if any word in text fuzzy-matches or stem-matches a generate keyword."""
    if _GEN_KW_RE.search(text):
        return True
    # See _CREATED_NOT_GENERATE_RE above — an identity/authorship question
    # about "who created my account" must not win on the 'crea' stem alone.
    if _CREATED_NOT_GENERATE_RE.search(text):
        return False
    # See _PERMISSION_QUESTION_RE above — "can I create new users" is a
    # self-permission question, not a create-a-report-instance command.
    if _PERMISSION_QUESTION_RE.search(text):
        return False
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
    # See _PERMISSION_QUESTION_RE above — "can I schedule this return" is a
    # self-permission question, not a scheduling command.
    if _PERMISSION_QUESTION_RE.search(text):
        return False
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
        'Initiated On: <DTC> | Reporting Date: <date>'
    Returns the DTC string, or None if the format is not recognised.

    The older 'Generated On:' spelling is still accepted so labels already
    rendered into a user's chat history (App.jsx persists messages to
    localStorage) keep resolving after the rename — otherwise their next click
    would silently fail to match and the picker would re-prompt.
    """
    m = re.search(r'(?:Initiated|Generated) On:\s*(.+?)\s*\|', text)
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
        category = await _agent_pkg.classify_conversational_intent(text, history=history)
    except Exception as exc:
        logger.warning('[CONVERSATIONAL_CLASSIFIER_FAIL] %s', exc)
        return None
    if category in {'greeting', 'acknowledgement'}:
        return category
    return None


__all__ = [
    "_fuzzy_has_status", "_fuzzy_has_generate", "_fuzzy_has_schedule", "_fuzzy_has_compare",
    "_normalise_conversational", "_get_conversational_response",
    "_DATE_RE", "_STATUS_GENERIC_TERMS",
    "_extract_status_search_terms", "_is_generic_status_terms", "_is_meaningful_report_terms",
    "_extract_schedule_search_terms",
    "_is_staged_session", "_parse_dtc_from_label", "_is_plausible_date", "_looks_like_new_query",
    "_get_conversational_response_for_category", "_classify_conversational",
]
