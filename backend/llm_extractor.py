# llm_extractor.py — Intent extraction via LLM + flexible date/entity parsing.
# Pipeline: LLM (intent + report name) → dateutil (date normalization) → token fuzzy match (entity resolution).
# Requires Ollama running; configure extraction model via OLLAMA_EXTRACT_MODEL env var.

from __future__ import annotations

import calendar
import logging
import re
import time
from datetime import date, datetime, timedelta
from typing import Any, Optional

from dateutil import parser as _du_parser
from dateutil.parser import ParserError

logger = logging.getLogger(__name__)



# ---------------------------------------------------------------------------
# Date/time regex patterns — normalization and extraction helpers.
# Intent and report name are extracted by the LLM (extract_intent_and_entities).
# Entity resolution uses token-based fuzzy matching (resolve_entities below).
# ---------------------------------------------------------------------------
_DATE_RE = re.compile(
    r"\b(\d{1,2}-(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)-\d{4})\b", re.I
)

# Month-only pattern: "March 2026", "Mar 2026", "march 2026"
_MONTH_YEAR_RE = re.compile(
    r"\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?"
    r"|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\s+(\d{4})\b",
    re.I,
)
# Year-only pattern: a standalone 4-digit year
_YEAR_ONLY_RE = re.compile(r"(?<![\d\-/])(\d{4})(?![\d\-/])")

def _next_weekday(weekday: int) -> date:
    """Return the next future occurrence of *weekday* (0=Mon … 6=Sun).

    Always returns a date that is strictly after today, even if today is
    already that weekday (so "next Monday" spoken on Monday means 7 days ahead).
    """
    today = date.today()
    days_ahead = weekday - today.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return today + timedelta(days=days_ahead)


# Relative-date tokens → resolve at call time.
# Longer tokens ("next monday") must precede shorter overlapping ones so the
# in-string search finds the most-specific match first.
_RELATIVE_DATES: dict[str, Any] = {
    "next monday":    lambda: _next_weekday(0),
    "next tuesday":   lambda: _next_weekday(1),
    "next wednesday": lambda: _next_weekday(2),
    "next thursday":  lambda: _next_weekday(3),
    "next friday":    lambda: _next_weekday(4),
    "next saturday":  lambda: _next_weekday(5),
    "next sunday":    lambda: _next_weekday(6),
    "tomorrow":       lambda: date.today() + timedelta(days=1),
    "today":          lambda: date.today(),
    "yesterday":      lambda: date.today() - timedelta(days=1),
    "last month":     lambda: (
        date.today().replace(day=1)
        if date.today().month == 1
        else date.today().replace(month=date.today().month - 1, day=1)
    ),
}

# ---------------------------------------------------------------------------
# Time regex — matches: "4 PM", "4:30 PM", "16:00", "10 AM", "6:30PM" etc.
# Used by parse_schedule_time() and extract_schedule_datetime().
# ---------------------------------------------------------------------------
_TIME_RE = re.compile(
    r'\b(\d{1,2}:\d{2}\s*[AP]M|\d{1,2}:\d{2}|\d{1,2}\s*[AP]M)\b', re.I
)


def parse_and_format_date(user_input: str) -> Optional[str]:
    """Parse a date string in any natural format and return DD-MMM-YYYY.

    Supports:
      - Strict format already in DD-MMM-YYYY  : "31-Mar-2026"  → "31-Mar-2026"
      - Full date, any order                  : "26 January 2021" → "26-Jan-2021"
      - Short month                           : "31 Mar 2025"  → "31-Mar-2025"
      - Numeric formats                       : "01/04/2024"   → "01-Apr-2024"
      - ISO format                            : "2026-03-31"   → "31-Mar-2026"
      - Month + Year only                     : "March 2026"   → "31-Mar-2026"
      - Year only                             : "2026"         → "31-Dec-2026"
      - Relative                              : "today"        → today's date

    Returns None if the input cannot be resolved to a date.
    """
    if not user_input or not user_input.strip():
        return None

    text = user_input.strip()

    # 1. Already in the target format — fast path, validate and return
    m = _DATE_RE.search(text)
    if m:
        candidate = m.group(1)
        try:
            from datetime import datetime as _dt
            validated = _dt.strptime(candidate, "%d-%b-%Y")
            return validated.strftime("%d-%b-%Y")
        except ValueError:
            pass  # invalid calendar date (e.g. 31-Feb-2026), fall through

    # 2. Relative date tokens
    lower = text.lower()
    for token, resolver in _RELATIVE_DATES.items():
        if token in lower:
            try:
                return resolver().strftime("%d-%b-%Y")
            except Exception:
                pass

    # Day-number pattern: digit(s) before a month name means a full date is present
    _HAS_DAY_RE = re.compile(
        r"\b\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?"
        r"|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?"
        r"|Nov(?:ember)?|Dec(?:ember)?)\b",
        re.I,
    )
    has_day = bool(_HAS_DAY_RE.search(text))

    # 3. Month + Year only (no leading day number) — resolve to last day of month
    if not has_day:
        m = _MONTH_YEAR_RE.search(text)
        if m:
            try:
                dt = _du_parser.parse(f"1 {m.group(0)}", dayfirst=True)
                last_day = calendar.monthrange(dt.year, dt.month)[1]
                return dt.replace(day=last_day).strftime("%d-%b-%Y")
            except (ParserError, ValueError, OverflowError):
                pass

        # 4. Year only — resolve to 31-Dec-<year>
        m = _YEAR_ONLY_RE.search(text)
        if m and text.strip() == m.group(1):
            try:
                year = int(m.group(1))
                if 1900 <= year <= 2100:
                    return f"31-Dec-{year}"
            except ValueError:
                pass

    # 5. Full date — use dateutil fuzzy parsing
    try:
        dt = _du_parser.parse(text, fuzzy=True, dayfirst=True)
        return dt.strftime("%d-%b-%Y")
    except (ParserError, ValueError, OverflowError):
        pass

    logger.debug("parse_and_format_date: could not parse %r", user_input)
    return None


def _extract_date_from_query(query: str) -> Optional[str]:
    """Extract and normalise a date from a query string.

    Strategy:
      1. Try the strict DD-MMM-YYYY regex first (fastest, most precise).
      2. Fall back to parse_and_format_date on the full query (fuzzy).
         Only accept the fuzzy result when it looks like the query genuinely
         contains date-like tokens (digits or month names) to avoid false
         positives from report names like 'CIMS_RAQ'.
    """
    # Fast path: strict regex
    m = _DATE_RE.search(query)
    if m:
        return m.group(1)

    # Fuzzy path: only attempt when there's a plausible date signal
    _DATE_SIGNAL_RE = re.compile(
        r"\b(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}"        # numeric separators
        r"|\d{4}[/\-.]\d{1,2}[/\-.]\d{1,2}"             # ISO style
        r"|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"  # "26 Jan"
        r"|\d{1,2}\s+(?:January|February|March|April|June|July|August"     # "26 January"
        r"|September|October|November|December)"
        r"|(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May"        # "March 2026"
        r"|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?"
        r"|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d"
        r"|today|yesterday|last\s+month)\b",
        re.I,
    )
    if not _DATE_SIGNAL_RE.search(query):
        return None

    return parse_and_format_date(query)

# Words stripped when extracting report search terms from a query.
# These are intent/action/filler words that carry no report-identity info.
_STOP_WORDS: frozenset[str] = frozenset({
    # intent / action
    "status", "state", "progress", "show", "check", "details", "info",
    "generate", "create", "trigger", "run", "produce", "make", "kick",
    "off", "initiate", "launch", "start", "submit", "build", "execute",
    "fire", "let", "us",
    # scheduling
    "schedule", "scheduled", "scheduling", "book", "plan", "queue", "set",
    "at", "pm", "am",
    # question / filler
    "what", "how", "has", "did", "been", "done", "is", "it",
    "this", "that", "about", "can", "you", "i", "we", "me",
    "give", "tell", "get", "fetch", "find",
    # prepositions / articles
    "of", "for", "the", "a", "an", "on",
    # domain stop words
    "instance", "report", "new", "please",
})



def _extract_search_terms(query: str) -> str:
    """Strip intent/filler words and dates — return only report-relevant tokens.

    Examples:
        "status of raq monthly"        → "raq monthly"
        "Generate CIMS_RAQ for 30-Jun" → "CIMS_RAQ"
        "check quarterly report"       → "quarterly"
        "is it finished processing?"   → ""
    """
    date_match = _DATE_RE.search(query)
    clean = query.replace(date_match.group(0), "") if date_match else query
    clean = re.sub(r"[?!.,]", " ", clean)
    words = [w for w in clean.split() if w.lower() not in _STOP_WORDS and len(w) > 1]
    return " ".join(words).strip()


def resolve_entities(
    user_input: str,
    intent: str,
    report_list: list[str],
) -> dict[str, Any]:
    """Token-based fuzzy matching of user input against a list of known report names.

    Does NOT require uppercase input or exact name matches.
    Works with: "raq monthly", "quarterly cims", "apbl annual", etc.

    Steps:
      1. Clean input → extract search terms (strip intent/filler words + dates)
      2. Normalise both input and report names (lowercase, alphanumeric only)
      3. Bidirectional substring check first (most confident)
      4. Token overlap scoring as fallback
      5. Keep only matches within 80 % of the best score

    Args:
        user_input:  Raw user message.
        intent:      Classified intent (influences which stop words are stripped).
        report_list: All known report name strings (e.g. loaded from returns.xml).

    Returns:
        {
            "search_terms":         str,        # cleaned tokens used for matching
            "matches":              list[str],  # strong-match report names (deduped)
            "best_match":           str | None, # highest-scoring name
            "confidence":           float,      # best match score  0.0–1.0
            "needs_disambiguation": bool,       # True when multiple strong matches
        }
    """
    search_terms = _extract_search_terms(user_input)
    _empty: dict[str, Any] = {
        "search_terms": search_terms, "matches": [], "best_match": None,
        "confidence": 0.0, "needs_disambiguation": False,
    }

    if not search_terms:
        return _empty

    def _norm(s: str) -> str:
        """Lowercase + alphanumeric only.  'CIMS_RAQ(Quarterly)' → 'cimsraqquarterly'"""
        return re.sub(r"[^a-z0-9]", "", s.lower())

    norm_input = _norm(search_terms)
    tokens     = [t for t in re.split(r"[^a-z0-9]+", norm_input) if len(t) >= 2]

    if not tokens:
        return _empty

    scored: list[tuple[float, str]] = []
    for name in report_list:
        if not name:
            continue
        norm_name = _norm(name)

        # Strategy 1: bidirectional substring (most confident — score = 1.0)
        if norm_input in norm_name or norm_name in norm_input:
            scored.append((1.0, name))
            continue

        # Strategy 2: token overlap  (score = matched_tokens / total_tokens)
        hits = sum(1 for t in tokens if t in norm_name)
        if hits:
            scored.append((hits / len(tokens), name))

    if not scored:
        return {**_empty, "search_terms": search_terms}

    scored.sort(key=lambda x: -x[0])
    best_score   = scored[0][0]

    # Keep only names within 80 % of the best score
    seen:    set[str]  = set()
    matches: list[str] = []
    for score, name in scored:
        if score < best_score * 0.8:
            break
        if name not in seen:
            seen.add(name)
            matches.append(name)

    logger.info(
        "[ENTITY_MATCH] search_terms=%r tokens=%r matches=%d best=%r confidence=%.2f",
        search_terms, tokens, len(matches), matches[0] if matches else None, best_score,
    )
    if best_score < 0.5 and matches:
        logger.warning(
            "[LOW_CONFIDENCE_MATCH] input=%r best_match=%r confidence=%.2f",
            search_terms, matches[0], best_score,
        )
    return {
        "search_terms":         search_terms,
        "matches":              matches,
        "best_match":           matches[0] if matches else None,
        "confidence":           best_score,
        "needs_disambiguation": len(matches) > 1,
    }


def parse_schedule_time(text: str) -> Optional[str]:
    """Parse the first time expression in *text* and return HH:MM (24-hour).

    Supports:
      "4 PM"    → "16:00"
      "4:30 PM" → "16:30"
      "16:00"   → "16:00"
      "10 AM"   → "10:00"
      "6:30PM"  → "06:30"  (no space before AM/PM)

    Returns None if no time expression is found.
    """
    m = _TIME_RE.search(text)
    if not m:
        return None
    raw = m.group(1).strip()
    # Normalise: collapse extra spaces, ensure single space before AM/PM
    raw = re.sub(r'\s+', ' ', re.sub(r'(?<=[0-9])([AP]M)', r' \1', raw, flags=re.I)).strip()
    upper = raw.upper()

    # Try HH:MM AM/PM  (e.g. "4:30 PM", "10:00 AM")
    try:
        return datetime.strptime(upper, '%I:%M %p').strftime('%H:%M')
    except ValueError:
        pass

    # Try HH:MM  24-hour  (e.g. "16:00", "09:30")
    try:
        return datetime.strptime(upper, '%H:%M').strftime('%H:%M')
    except ValueError:
        pass

    # Try H AM/PM  no minutes  (e.g. "4 PM", "10 AM")
    try:
        return datetime.strptime(upper, '%I %p').strftime('%H:%M')
    except ValueError:
        pass

    return None


def extract_schedule_datetime(query: str) -> dict[str, Optional[str]]:
    """Extract schedule date and time from a natural-language query.

    Strategy:
      1. Parse time first with ``parse_schedule_time``.
      2. Strip time tokens from the query so they do not confuse date parsing
         (e.g. "4 PM" would otherwise be parsed as day-4 by dateutil).
      3. Parse the cleaned query for a date via ``_extract_date_from_query``
         which already handles relative tokens ("tomorrow", "next Monday").
      4. Combine into an ISO 8601 ``scheduled_datetime`` string.

    Returns::

        {
            "schedule_date":      str | None,  # DD-MMM-YYYY
            "schedule_time":      str | None,  # HH:MM  (24-hour)
            "scheduled_datetime": str | None,  # YYYY-MM-DDTHH:MM:00
        }
    """
    schedule_time = parse_schedule_time(query)

    # Remove time tokens before date parsing to prevent ambiguity
    date_query = _TIME_RE.sub(" ", query).strip() if schedule_time else query

    schedule_date = _extract_date_from_query(date_query)

    scheduled_datetime: Optional[str] = None
    if schedule_date and schedule_time:
        try:
            dt = datetime.strptime(f"{schedule_date} {schedule_time}", "%d-%b-%Y %H:%M")
            scheduled_datetime = dt.strftime("%Y-%m-%dT%H:%M:00")
        except ValueError:
            pass

    return {
        "schedule_date":      schedule_date,
        "schedule_time":      schedule_time,
        "scheduled_datetime": scheduled_datetime,
    }


async def extract_intent_and_entities(user_query: str) -> dict[str, Any]:
    """Use LLM to extract intent and entities from a raw user query.

    Calls Ollama (OLLAMA_EXTRACT_MODEL, default phi4-mini) with a structured
    JSON prompt, then normalizes all extracted dates/times through the existing
    date and time parsers so downstream code receives a consistent format.

    Returns::

        {
            "intent":             str,         # get_status | generate_instance | schedule_report | unknown
            "search_terms":       str | None,  # LLM-extracted report name (used by resolve_entities)
            "reporting_date":     str | None,  # DD-MMM-YYYY  (generate_instance)
            "schedule_date":      str | None,  # DD-MMM-YYYY  (schedule_report)
            "schedule_time":      str | None,  # HH:MM 24-hr  (schedule_report)
            "scheduled_datetime": str | None,  # YYYY-MM-DDTHH:MM:00
        }
    """
    from backend.services.llm_service import extract_intent_entities_llm

    logger.info("[LLM_EXTRACT_START] query=%r", user_query)
    _t0 = time.monotonic()

    try:
        raw = await extract_intent_entities_llm(user_query)
    except Exception as exc:
        _elapsed = time.monotonic() - _t0
        logger.warning(
            "[LLM_EXTRACT_FAIL] duration=%.2fs error=%s — falling back to unknown",
            _elapsed, exc,
        )
        return {
            "intent": "unknown", "search_terms": None, "reporting_date": None,
            "schedule_date": None, "schedule_time": None, "scheduled_datetime": None,
        }

    _elapsed = time.monotonic() - _t0
    logger.info("[PERF] operation=llm_extract duration=%.2fs", _elapsed)

    # Validate intent — reject any value the LLM hallucinated
    _valid_intents = {"get_status", "generate_instance", "schedule_report", "compare_reports", "query_database", "unknown"}
    intent: str = raw.get("intent", "unknown")
    if intent not in _valid_intents:
        logger.warning("LLM returned unknown intent %r — defaulting to unknown", intent)
        intent = "unknown"

    # Keyword safety net — small models (phi3:mini) often miss compare_reports.
    # If the query contains clear comparison/variance keywords, override to compare_reports.
    _CMP_RE = re.compile(
        r"\b(compar|varianc|differ|vs\.?|versus|contrast|analys|side.by.side)",
        re.I,
    )
    if intent in ("unknown", "get_status") and _CMP_RE.search(user_query):
        logger.info("Keyword override: %r → compare_reports", intent)
        intent = "compare_reports"

    def _clean(v: Any) -> Optional[str]:
        """Return None for null/none/empty LLM outputs."""
        if v is None:
            return None
        s = str(v).strip()
        return None if s.lower() in ("null", "none", "") else s

    report_name = _clean(raw.get("report_name"))

    # Fallback: for compare_reports, if the LLM didn't extract a name (common with
    # short bank-prefix queries like "compare HDFC"), extract it directly from the query
    # by stripping comparison-intent words and taking the first meaningful token.
    if intent == "compare_reports" and not report_name:
        _CMP_STOP = re.compile(
            r"\b(compare|comparing|comparison|variance|variances|diff(?:er(?:ence)?)?"
            r"|vs\.?|versus|contrast|analys[ie]s?|side|report[s]?|instance[s]?"
            r"|these|those|me|the|a|an|of|for|to|two|both|and|or|with)\b",
            re.I,
        )
        cleaned = _CMP_STOP.sub(" ", user_query).strip()
        tokens = [t for t in re.split(r"[\s,;]+", cleaned) if len(t) >= 2]
        if tokens:
            report_name = tokens[0]
            logger.info(
                "compare_reports fallback: extracted report_name=%r from query", report_name
            )

    reporting_date:     Optional[str] = None
    schedule_date:      Optional[str] = None
    schedule_time:      Optional[str] = None
    scheduled_datetime: Optional[str] = None

    if intent == "schedule_report":
        raw_sdate = _clean(raw.get("schedule_date"))
        raw_stime = _clean(raw.get("schedule_time"))
        if raw_sdate:
            schedule_date = parse_and_format_date(raw_sdate) or raw_sdate
        if raw_stime:
            schedule_time = parse_schedule_time(raw_stime) or raw_stime
        if schedule_date and schedule_time:
            try:
                dt = datetime.strptime(f"{schedule_date} {schedule_time}", "%d-%b-%Y %H:%M")
                scheduled_datetime = dt.strftime("%Y-%m-%dT%H:%M:00")
            except ValueError:
                pass

    elif intent == "generate_instance":
        raw_date = _clean(raw.get("reporting_date"))
        raw_stime = _clean(raw.get("schedule_time"))
        if raw_date:
            reporting_date = parse_and_format_date(raw_date) or raw_date
        # Reclassify: generate + time-of-day → schedule_report
        if raw_stime:
            schedule_time = parse_schedule_time(raw_stime) or raw_stime
            if schedule_time:
                logger.info("Reclassify generate_instance → schedule_report (time component)")
                intent        = "schedule_report"
                schedule_date = reporting_date
                reporting_date = None
                raw_sdate = _clean(raw.get("schedule_date"))
                if raw_sdate:
                    schedule_date = parse_and_format_date(raw_sdate) or raw_sdate
                if schedule_date and schedule_time:
                    try:
                        dt = datetime.strptime(
                            f"{schedule_date} {schedule_time}", "%d-%b-%Y %H:%M"
                        )
                        scheduled_datetime = dt.strftime("%Y-%m-%dT%H:%M:00")
                    except ValueError:
                        pass

    logger.info(
        "LLM result: intent=%s report_name=%r reporting_date=%r "
        "schedule_date=%r schedule_time=%r",
        intent, report_name, reporting_date, schedule_date, schedule_time,
    )
    return {
        "intent":             intent,
        "search_terms":       report_name,  # passed to resolve_entities() by the agent
        "reporting_date":     reporting_date,
        "schedule_date":      schedule_date,
        "schedule_time":      schedule_time,
        "scheduled_datetime": scheduled_datetime,
    }
