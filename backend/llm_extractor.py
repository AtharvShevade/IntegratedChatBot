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

# Broad multi-format date regex — strips date tokens from user queries before
# report-name matching.  Covers all commonly used formats:
#   31 May 2025   (day month-name year — space-separated)
#   May 31 2025   (month-name day year)
#   31/05/2025    (numeric slash)
#   31-05-2025    (numeric hyphen)
#   31-May-2025   (DD-MMM-YYYY — already in _DATE_RE but included for completeness)
_BROAD_DATE_RE = re.compile(
    r"\b(?:"
    # DD/MM/YYYY or DD-MM-YYYY  (numeric)
    r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}"
    # 31 May 2025  (day SP month-name SP year)
    r"|\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May"
    r"|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?"
    r"|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}"
    # May 31 2025 / May 31, 2025  (month-name SP day [,SP] year)
    r"|(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May"
    r"|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?"
    r"|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2}[,\s]+\d{4}"
    # 31-May-2025  (DD-MMM-YYYY)
    r"|\d{1,2}-(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)-\d{4}"
    r")\b",
    re.I,
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


def _this_or_coming_weekday(weekday: int) -> date:
    """Return the next occurrence of *weekday*, including today if it matches
    (unlike _next_weekday, which always skips to the following week)."""
    today = date.today()
    days_ahead = weekday - today.weekday()
    if days_ahead < 0:
        days_ahead += 7
    return today + timedelta(days=days_ahead)


# Relative-date tokens → resolve at call time.
# Longer/more-specific tokens ("day after tomorrow", "next monday") must
# precede shorter overlapping ones ("tomorrow") so the in-string search finds
# the most-specific match first.
_RELATIVE_DATES: dict[str, Any] = {
    "day after tomorrow": lambda: date.today() + timedelta(days=2),
    "next monday":    lambda: _next_weekday(0),
    "next tuesday":   lambda: _next_weekday(1),
    "next wednesday": lambda: _next_weekday(2),
    "next thursday":  lambda: _next_weekday(3),
    "next friday":    lambda: _next_weekday(4),
    "next saturday":  lambda: _next_weekday(5),
    "next sunday":    lambda: _next_weekday(6),
    "this monday":    lambda: _this_or_coming_weekday(0),
    "this tuesday":   lambda: _this_or_coming_weekday(1),
    "this wednesday": lambda: _this_or_coming_weekday(2),
    "this thursday":  lambda: _this_or_coming_weekday(3),
    "this friday":    lambda: _this_or_coming_weekday(4),
    "this saturday":  lambda: _this_or_coming_weekday(5),
    "this sunday":    lambda: _this_or_coming_weekday(6),
    "coming monday":    lambda: _this_or_coming_weekday(0),
    "coming tuesday":   lambda: _this_or_coming_weekday(1),
    "coming wednesday": lambda: _this_or_coming_weekday(2),
    "coming thursday":  lambda: _this_or_coming_weekday(3),
    "coming friday":    lambda: _this_or_coming_weekday(4),
    "coming saturday":  lambda: _this_or_coming_weekday(5),
    "coming sunday":    lambda: _this_or_coming_weekday(6),
    "next week":      lambda: date.today() + timedelta(days=7),
    "next month":     lambda: (
        date.today().replace(day=1).replace(year=date.today().year + 1, month=1)
        if date.today().month == 12
        else date.today().replace(day=1, month=date.today().month + 1)
    ),
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
    r'\b(\d{1,2}:\d{2}(?::\d{2})?\s*[AP]M|\d{1,2}:\d{2}(?::\d{2})?|\d{1,2}\s*[AP]M)\b', re.I
)

# ---------------------------------------------------------------------------
# Natural-language time expressions — word numbers, "half past", "quarter to",
# "noon"/"midnight", "o'clock", morning/evening/night qualifiers, and the
# filler words "around"/"about". Tried ONLY when _TIME_RE (numeric/AM-PM,
# the existing working fast path) finds nothing, so existing behaviour for
# already-supported formats is completely unchanged.
# ---------------------------------------------------------------------------
_WORD_NUMBERS: dict[str, int] = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
}
_WORD_MINUTES: dict[str, int] = {
    "half": 30, "quarter": 15,
}
_NUM_WORD_RE = "(?:" + "|".join(_WORD_NUMBERS) + ")"

# "8 in the morning", "6 tomorrow evening", "9 tonight", "10 this evening",
# "seven in the evening" — captures the hour (digit or word) + period qualifier.
_QUALIFIED_HOUR_RE = re.compile(
    rf"\b(?:around|about)?\s*(\d{{1,2}}|{_NUM_WORD_RE})(?::(\d{{2}}))?\s*"
    r"(?:o'?\s?clock\s*)?"
    r"(?:in\s+the\s+|at\s+|(?:tomorrow|this|today)\s+)?"
    r"(morning|afternoon|evening|night|tonight)\b",
    re.I,
)

# "half past five", "quarter past five", "quarter to six"
_RELATIVE_MINUTE_RE = re.compile(
    rf"\b(half|quarter)\s+(past|to)\s+({_NUM_WORD_RE}|\d{{1,2}})\b", re.I,
)

# "five thirty pm", "eleven thirty at night", "five thirty in the evening"
_WORD_HOUR_MINUTE_RE = re.compile(
    rf"\b({_NUM_WORD_RE})\s+thirty\b"
    r"(?:\s*([AP]M)"
    r"|\s+(?:at\s+|in\s+the\s+)?(morning|afternoon|evening|night|tonight))?",
    re.I,
)

# "five pm", "seven in the evening" (bare word-number + meridiem, no digits)
_WORD_HOUR_RE = re.compile(
    rf"\b({_NUM_WORD_RE})\s*([AP]M)\b", re.I,
)

# "7 o'clock", "about 4 o'clock" — bare hour, no explicit AM/PM.
_OCLOCK_RE = re.compile(
    rf"\b(?:around|about)?\s*(\d{{1,2}}|{_NUM_WORD_RE})\s*o'?\s?clock\b", re.I,
)

_NOON_RE     = re.compile(r"\bnoon\b", re.I)
_MIDNIGHT_RE = re.compile(r"\bmidnight\b", re.I)

# Union of all natural-language time patterns, used only to strip a matched
# time phrase out of a query before date extraction runs (mirrors the existing
# _TIME_RE-based stripping for the numeric/AM-PM fast path).
_NATURAL_TIME_STRIP_RE = re.compile(
    "|".join(
        p.pattern for p in (
            _NOON_RE, _MIDNIGHT_RE, _RELATIVE_MINUTE_RE,
            _WORD_HOUR_MINUTE_RE, _QUALIFIED_HOUR_RE, _WORD_HOUR_RE, _OCLOCK_RE,
        )
    ),
    re.I,
)


def _period_to_24h(hour_12: int, period: str) -> int:
    """Map an hour (1-12) + a loose period word to a 24-hour hour value.

    'morning' -> AM; 'afternoon'/'evening'/'night'/'tonight' -> PM, except a
    small hour written as "12 ..." is left to normal 12h wraparound rules.
    """
    period = period.lower()
    if period == "morning":
        return hour_12 % 12
    # afternoon / evening / night / tonight all imply PM
    if hour_12 == 12:
        return 12
    return (hour_12 % 12) + 12


def _parse_natural_time(text: str) -> Optional[str]:
    """Best-effort parse of natural-language time phrases not covered by
    the numeric/AM-PM fast path (_TIME_RE). Returns "HH:MM" or None.

    Supports: noon, midnight, "5 o'clock", word numbers ("five pm"),
    "half past five", "quarter past five", "quarter to six", "five thirty pm",
    qualified hours ("8 in the morning", "9 tonight", "6 tomorrow evening"),
    and the filler words "around"/"about".
    """
    if _NOON_RE.search(text):
        return "12:00"
    if _MIDNIGHT_RE.search(text):
        return "00:00"

    def _to_num(tok: str) -> Optional[int]:
        tok = tok.lower()
        if tok.isdigit():
            return int(tok)
        return _WORD_NUMBERS.get(tok)

    # "half past five" / "quarter past five" / "quarter to six"
    m = _RELATIVE_MINUTE_RE.search(text)
    if m:
        unit, direction, hour_tok = m.group(1).lower(), m.group(2).lower(), m.group(3)
        hour = _to_num(hour_tok)
        minutes = _WORD_MINUTES[unit]
        if hour is not None:
            if direction == "to":
                hour = hour - 1 if hour > 1 else 12
                minutes = 60 - minutes
            # Ambiguous AM/PM with no other context — assume PM for a bare
            # relative-minute phrase (typical scheduling context), matching
            # the "5 PM" default rather than failing outright.
            hour24 = _period_to_24h(hour, "evening") if hour != 12 else 12
            return f"{hour24:02d}:{minutes:02d}"

    # "five thirty pm" / "eleven thirty at night" / "five thirty in the evening"
    m = _WORD_HOUR_MINUTE_RE.search(text)
    if m:
        hour = _to_num(m.group(1))
        meridiem = m.group(2)
        qualifier = m.group(3)
        if hour is not None:
            if meridiem:
                hour24 = hour % 12 if meridiem.upper() == "AM" else (hour % 12) + 12
                return f"{hour24:02d}:30"
            if qualifier:
                hour24 = _period_to_24h(hour, qualifier)
                return f"{hour24:02d}:30"
            # No explicit AM/PM — look for a trailing qualifier word elsewhere.
            qm = _QUALIFIED_HOUR_RE.search(text)
            if qm:
                hour24 = _period_to_24h(hour, qm.group(3))
                return f"{hour24:02d}:30"

    # "8 in the morning", "6 tomorrow evening", "9 tonight", "seven in the evening"
    m = _QUALIFIED_HOUR_RE.search(text)
    if m:
        hour = _to_num(m.group(1))
        minute = int(m.group(2)) if m.group(2) else 0
        period = m.group(3)
        if hour is not None:
            hour24 = _period_to_24h(hour, period)
            return f"{hour24:02d}:{minute:02d}"

    # "five pm" (bare word-number + meridiem)
    m = _WORD_HOUR_RE.search(text)
    if m:
        hour = _to_num(m.group(1))
        meridiem = m.group(2)
        if hour is not None:
            hour24 = hour % 12 if meridiem.upper() == "AM" else (hour % 12) + 12
            return f"{hour24:02d}:00"

    # "7 o'clock", "about 4 o'clock" — bare hour, default to PM (business-hours
    # scheduling convention), consistent with the relative-minute default above.
    m = _OCLOCK_RE.search(text)
    if m:
        hour = _to_num(m.group(1))
        if hour is not None:
            hour24 = _period_to_24h(hour, "evening") if hour != 12 else 12
            return f"{hour24:02d}:00"

    return None


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
      - Ordinal suffixes                      : "31st March 2024" → "31-Mar-2024"
      - 2-digit years                         : "31 mar 24"    → "31-Mar-2024"
      - Impossible dates                      : "31 April 2026" → "30-Apr-2026" (clamped)

    Returns None if the input cannot be resolved to a date.
    """
    if not user_input or not user_input.strip():
        return None

    text = user_input.strip()
    logger.debug("[DATE_PARSE_START] input=%r", text)

    # 0. Strip ordinal suffixes: "31st", "2nd", "3rd", "1st" → digit only
    text = re.sub(r'\b(\d{1,2})(?:st|nd|rd|th)\b', r'\1', text, flags=re.I)

    # 1. Already in the target format — fast path, validate and return
    m = _DATE_RE.search(text)
    if m:
        candidate = m.group(1)
        try:
            from datetime import datetime as _dt
            validated = _dt.strptime(candidate, "%d-%b-%Y")
            logger.debug("[DATE_PARSE_SUCCESS] fast-path=%r", validated.strftime("%d-%b-%Y"))
            return validated.strftime("%d-%b-%Y")
        except ValueError:
            # Invalid calendar date in correct format (e.g. 31-Feb-2026)
            # Try clamping below
            pass

    # 2. Relative date tokens
    lower = text.lower()
    for token, resolver in _RELATIVE_DATES.items():
        if token in lower:
            try:
                result = resolver().strftime("%d-%b-%Y")
                logger.debug("[DATE_PARSE_SUCCESS] relative=%r → %r", token, result)
                return result
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
                result = dt.replace(day=last_day).strftime("%d-%b-%Y")
                logger.debug("[DATE_PARSE_SUCCESS] month+year=%r → %r", m.group(0), result)
                return result
            except (ParserError, ValueError, OverflowError):
                pass

        # 4. Year only — resolve to 31-Dec-<year>
        m = _YEAR_ONLY_RE.search(text)
        if m and text.strip() == m.group(1):
            try:
                year = int(m.group(1))
                if 1900 <= year <= 2100:
                    result = f"31-Dec-{year}"
                    logger.debug("[DATE_PARSE_SUCCESS] year-only=%d → %r", year, result)
                    return result
            except ValueError:
                pass

    # 5. Full date — use dateutil fuzzy parsing
    try:
        dt = _du_parser.parse(text, fuzzy=True, dayfirst=True)
        result = dt.strftime("%d-%b-%Y")
        logger.debug("[DATE_PARSE_SUCCESS] dateutil=%r → %r", text, result)
        return result
    except (ParserError, ValueError, OverflowError):
        pass

    # 6. Impossible-date clamping: if the text looks like a date but has an
    #    invalid day (e.g. "31 April 2026"), try clamping to last day of month.
    clamped = _try_clamp_impossible_date(text)
    if clamped:
        logger.debug("[DATE_PARSE_SUCCESS] clamped=%r → %r", text, clamped)
        return clamped

    logger.debug("[DATE_PARSE_FAIL] could not parse %r", user_input)
    return None


# Regex to extract (day, month_name, year) from text that dateutil rejects
_IMPOSSIBLE_DATE_RE = re.compile(
    r"\b(\d{1,2})\s+"
    r"(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?"
    r"|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\s+(\d{2,4})\b",
    re.I,
)

_MONTH_ABBREV_MAP: dict[str, int] = {
    "jan": 1, "january": 1, "feb": 2, "february": 2,
    "mar": 3, "march": 3, "apr": 4, "april": 4,
    "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}


def _try_clamp_impossible_date(text: str) -> Optional[str]:
    """Attempt to clamp an impossible date to the last valid day of the month.

    E.g. "31 April 2026" → "30-Apr-2026" (April has only 30 days).
    """
    m = _IMPOSSIBLE_DATE_RE.search(text)
    if not m:
        return None

    day = int(m.group(1))
    month_str = m.group(2).lower()
    year_str = m.group(3)

    month_num = _MONTH_ABBREV_MAP.get(month_str)
    if not month_num:
        return None

    # Handle 2-digit year
    year = int(year_str)
    if year < 100:
        year += 2000

    if not (1900 <= year <= 2100):
        return None

    last_day = calendar.monthrange(year, month_num)[1]
    if day <= last_day:
        # It's actually a valid date — dateutil should have handled it
        return None

    # Clamp to last valid day
    clamped_date = date(year, month_num, last_day)
    return clamped_date.strftime("%d-%b-%Y")


# Module-level: compiled once for efficiency.
# Detects a plausible date signal in free-text before invoking fuzzy parsing.
# Covers all four user-requested formats plus numeric and ISO.
_DATE_SIGNAL_RE = re.compile(
    r"(?:"
    r"\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}"               # 31/03/2025  31-03-2025  31.03.2025
    r"|\d{4}[/\-.]\d{1,2}[/\-.]\d{1,2}"                 # 2025-03-31  (ISO)
    r"|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b"   # 31 Mar
    r"|\d{1,2}\s+(?:January|February|March|April|May|June|July|August"    # 31 March
    r"|September|October|November|December)\b"
    r"|(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May"           # March 31
    r"|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?"
    r"|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2}"
    r"|today|yesterday|last\s+month"
    r"|tomorrow|day\s+after\s+tomorrow"
    r"|(?:next|this|coming)\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
    r"|next\s+week|next\s+month"
    r")",
    re.I,
)


def _extract_date_from_query(query: str) -> Optional[str]:
    """Extract and normalise a date from a query string.

    Strategy:
      1. Try the strict DD-MMM-YYYY regex first (fastest, most precise).
      2. Fall back to parse_and_format_date on the full query (fuzzy).
         Only accept the fuzzy result when it looks like the query genuinely
         contains date-like tokens (digits or month names) to avoid false
         positives from report names like 'CIMS_RAQ'.

    Supports:
      - 31 March 2025  / 31 Mar 2025
      - 31-Mar-2025
      - March 31 2025
      - 31/03/2025  /  31-03-2025  /  31.03.2025
    """
    # Fast path: strict DD-MMM-YYYY regex
    m = _DATE_RE.search(query)
    if m:
        return m.group(1)

    # Fuzzy path: only invoke when a plausible date signal is present in the query
    if not _DATE_SIGNAL_RE.search(query):
        return None

    return parse_and_format_date(query)

# Words stripped when extracting report search terms from a query.
# These are intent/action/filler words that carry no report-identity info.
_STOP_WORDS: frozenset[str] = frozenset({
    # intent / action
    "status", "state", "progress", "show", "check", "details", "info",
    "generate", "generation", "create", "trigger", "run", "produce", "make", "kick",
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
    # date-lead contextual filler — prevent "date"/"dated" leaking into report names
    "date", "dated",
})



def _extract_search_terms(query: str) -> str:
    """Strip intent/filler words and dates — return only report-relevant tokens.

    Uses _BROAD_DATE_RE so ALL date formats are removed before tokenisation,
    not just DD-MMM-YYYY.  This prevents date tokens (e.g. "31", "May", "2025"
    from "generate instance for ale for 31 May 2025") from leaking into the
    report-name candidates passed to find_matching_reports().

    Examples:
        "status of raq monthly"                      → "raq monthly"
        "Generate CIMS_RAQ for 30-Jun-2024"          → "CIMS_RAQ"
        "generate instance for ale for 31 May 2025"  → "ale"
        "generate ale 31/05/2025"                    → "ale"
        "check quarterly report"                     → "quarterly"
        "is it finished processing?"                 → ""
    """
    # Strip ALL recognised date formats (not just DD-MMM-YYYY) so date tokens
    # like "31 May 2025" or "31/05/2025" never pollute report-name matching.
    clean = _BROAD_DATE_RE.sub(" ", query)
    clean = re.sub(r"[?!.,]", " ", clean)
    words = [w for w in clean.split() if w.lower() not in _STOP_WORDS and len(w) > 1]
    return " ".join(words).strip()


# ---------------------------------------------------------------------------
# Generate-instance preprocessing
# ---------------------------------------------------------------------------

# Filler phrases specific to generate-instance queries.  These are removed as
# complete phrases before word-level tokenisation so they cannot accidentally
# split into partial stop-word matches.
#   "for date"    e.g. "generate ale for date 31 May 2025"
#   "for report"  e.g. "generate instance for report ale"
#   "for the"     e.g. "generate instance for the ale report"
#   "dated"       e.g. "create abc dated 12 May 2026"
GEN_FILLER_PHRASES_RE = re.compile(
    r"\b(?:for\s+date|for\s+report|for\s+the|dated)\b",
    re.I,
)


def preprocess_generate_query(query: str) -> tuple[str, Optional[str]]:
    """Deterministic preprocessing for generate-instance queries.

    Runs fully independently of the LLM.  Called before ``_resolve_report_name``
    so natural-language date formats and filler phrases are removed BEFORE the
    report-name matching pipeline sees the query.

    Steps:
      1. Extract date using ``_extract_date_from_query`` (broad regex + fuzzy).
      2. Strip date tokens from query using ``_BROAD_DATE_RE``.
      3. Strip generate-specific filler phrases ("for date", "for report", "dated").
      4. Extract clean report name via ``_extract_search_terms``.

    Returns:
        ``(report_name, reporting_date)``  where either may be empty / None
        when no name / date can be isolated from the query.

    Examples::

        "generate instance for ale for 31 May 2025"
            → ("ale", "31-May-2025")
        "generate instance for report ale for date 31 May 2025"
            → ("ale", "31-May-2025")
        "create abc instance dated 12 may 2026"
            → ("abc", "12-May-2026")
        "generate report cims raq on 31 mar 2026"
            → ("cims raq", "31-Mar-2026")
    """
    # ── Step 1: Extract date (broad regex first; fuzzy parse as fallback) ────
    reporting_date: Optional[str] = _extract_date_from_query(query)
    if reporting_date:
        logger.debug("[DATE_EXTRACT_REGEX] reporting_date=%r from %r", reporting_date, query)

    # ── Step 2: Remove date tokens and generate-specific filler phrases ───────
    clean = _BROAD_DATE_RE.sub(" ", query)
    clean = GEN_FILLER_PHRASES_RE.sub(" ", clean)

    # ── Step 3: Extract clean report name via standard stop-word stripping ────
    report_name = _extract_search_terms(clean)
    logger.debug(
        "[REPORT_NAME_CLEANED] original=%r → report_name=%r reporting_date=%r",
        query, report_name, reporting_date,
    )
    return report_name, reporting_date


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

    Also supports natural-language expressions ("noon", "half past five",
    "quarter to six", "8 in the morning", "seven o'clock", "around 4 pm", …)
    via ``_parse_natural_time`` — tried only when the numeric/AM-PM fast
    path below finds nothing, so existing behaviour is unchanged.

    Returns None if no time expression can be confidently resolved.
    """
    m = _TIME_RE.search(text)
    if not m:
        return _parse_natural_time(text)
    raw = m.group(1).strip()
    # Normalise: collapse extra spaces, ensure single space before AM/PM
    raw = re.sub(r'\s+', ' ', re.sub(r'(?<=[0-9])([AP]M)', r' \1', raw, flags=re.I)).strip()
    upper = raw.upper()

    # Try HH:MM:SS AM/PM or 24-hour  (e.g. "17:30:00")
    try:
        return datetime.strptime(upper, '%H:%M:%S').strftime('%H:%M')
    except ValueError:
        pass
    try:
        return datetime.strptime(upper, '%I:%M:%S %p').strftime('%H:%M')
    except ValueError:
        pass

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

    return _parse_natural_time(text)


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
    date_query = query
    if schedule_time:
        date_query = _TIME_RE.sub(" ", date_query)
        date_query = _NATURAL_TIME_STRIP_RE.sub(" ", date_query).strip()

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


# Anchors used to disambiguate which of two dates in one scheduling message is
# the reporting date vs. the schedule date.  "reporting date"/"reporting
# period"/"for the period" mark the reporting date; "schedule"/"execute"/
# "run"/"generate it on" mark the schedule date.  Longer/more specific phrases
# first so the search prefers the most explicit anchor when both could match.
_REPORTING_DATE_ANCHOR_RE = re.compile(
    r"reporting\s+(?:date|period)|for\s+the\s+period|report(?:ing)?\s+period\s+ending",
    re.I,
)
_SCHEDULE_DATE_ANCHOR_RE = re.compile(
    r"schedule(?:d)?\s+(?:it\s+)?(?:to\s+)?(?:execute|run|generate)|execute\s+(?:it\s+)?on"
    r"|run\s+(?:it\s+)?on|generate\s+it\s+on|schedule\s+it\s+for|schedule\s+date",
    re.I,
)


def extract_reporting_and_schedule_datetime(query: str) -> dict[str, Optional[str]]:
    """Extract a DISTINCT reporting date and schedule date/time from one message.

    Scheduling requires two different dates that describe different things:
      - Reporting Date : the business/period date the instance is FOR
        (validated against the report's frequency elsewhere).
      - Schedule Date/Time : when the .NET job should actually run.

    A single free-text message can legitimately contain both, e.g.:
      "Use the reporting date 31-Mar-2026, and schedule it to execute on
       31-Dec-2026 at 16:00."
    ``extract_schedule_datetime`` only ever finds ONE date (the first one in
    the text) and would misattribute the reporting date as the schedule date.
    This function instead:
      1. Finds ALL date-like substrings in the query with their positions.
      2. Finds "reporting date"/"schedule ... execute" anchor phrases with
         their positions.
      3. Assigns each date to whichever anchor precedes it most closely.
      4. Falls back to ``extract_schedule_datetime``'s single-date behaviour
         when there's no explicit reporting-date anchor (the common case of
         "schedule CIMS_RAQ for 31-Dec-2026 at 4pm" — no ambiguity, no need
         for the two-anchor logic).

    Returns::

        {
            "reporting_date":     str | None,  # DD-MMM-YYYY
            "schedule_date":      str | None,  # DD-MMM-YYYY
            "schedule_time":      str | None,  # HH:MM (24-hour)
            "scheduled_datetime": str | None,  # YYYY-MM-DDTHH:MM:00
        }
    """
    rpt_anchor = _REPORTING_DATE_ANCHOR_RE.search(query)

    if not rpt_anchor:
        # No explicit reporting-date phrasing — behave exactly like before.
        sched = extract_schedule_datetime(query)
        return {"reporting_date": None, **sched}

    date_matches = list(_BROAD_DATE_RE.finditer(query)) + list(_DATE_RE.finditer(query))
    # De-duplicate overlapping matches (both regexes can match DD-MMM-YYYY).
    seen_spans: set[tuple[int, int]] = set()
    unique_matches = []
    for m in sorted(date_matches, key=lambda m: m.start()):
        span = (m.start(), m.end())
        if span in seen_spans:
            continue
        seen_spans.add(span)
        unique_matches.append(m)

    if len(unique_matches) < 2:
        # Only one date found despite a reporting-date anchor — nothing to
        # disambiguate; treat it as the reporting date and let the caller ask
        # for the schedule date/time separately.
        reporting_date = parse_and_format_date(unique_matches[0].group(0)) if unique_matches else None
        return {
            "reporting_date": reporting_date,
            "schedule_date": None, "schedule_time": None, "scheduled_datetime": None,
        }

    sched_anchor = _SCHEDULE_DATE_ANCHOR_RE.search(query)

    def _nearest_preceding_anchor_distance(pos: int, anchor_pos: int | None) -> int:
        if anchor_pos is None or anchor_pos > pos:
            return 10**9
        return pos - anchor_pos

    rpt_pos   = rpt_anchor.start()
    sched_pos = sched_anchor.start() if sched_anchor else None

    reporting_date: Optional[str] = None
    schedule_date:  Optional[str] = None
    best_rpt_dist   = 10**9
    best_sched_dist = 10**9
    for m in unique_matches:
        d_rpt   = _nearest_preceding_anchor_distance(m.start(), rpt_pos)
        d_sched = _nearest_preceding_anchor_distance(m.start(), sched_pos)
        if d_rpt < best_rpt_dist and d_rpt <= d_sched:
            best_rpt_dist = d_rpt
            reporting_date = parse_and_format_date(m.group(0))
        elif d_sched < best_sched_dist:
            best_sched_dist = d_sched
            schedule_date = parse_and_format_date(m.group(0))

    # Fallback: if the anchor-distance assignment above didn't confidently
    # resolve both dates (e.g. only one anchor present), assign in reading
    # order — first date is the reporting date, second is the schedule date
    # — which matches how users naturally phrase these messages.
    if reporting_date is None and schedule_date is None and len(unique_matches) >= 2:
        reporting_date = parse_and_format_date(unique_matches[0].group(0))
        schedule_date  = parse_and_format_date(unique_matches[1].group(0))
    elif reporting_date is None:
        remaining = [m for m in unique_matches if parse_and_format_date(m.group(0)) != schedule_date]
        if remaining:
            reporting_date = parse_and_format_date(remaining[0].group(0))
    elif schedule_date is None:
        remaining = [m for m in unique_matches if parse_and_format_date(m.group(0)) != reporting_date]
        if remaining:
            schedule_date = parse_and_format_date(remaining[-1].group(0))

    # Time: strip all date tokens first so parse_schedule_time doesn't pick up
    # stray digits from a date as an hour.
    time_query = _BROAD_DATE_RE.sub(" ", query)
    time_query = _DATE_RE.sub(" ", time_query)
    schedule_time = parse_schedule_time(time_query)

    scheduled_datetime: Optional[str] = None
    if schedule_date and schedule_time:
        try:
            dt = datetime.strptime(f"{schedule_date} {schedule_time}", "%d-%b-%Y %H:%M")
            scheduled_datetime = dt.strftime("%Y-%m-%dT%H:%M:00")
        except ValueError:
            pass

    logger.info(
        "[EXTRACT] two-date schedule message: reporting_date=%r schedule_date=%r "
        "schedule_time=%r",
        reporting_date, schedule_date, schedule_time,
    )
    return {
        "reporting_date":     reporting_date,
        "schedule_date":      schedule_date,
        "schedule_time":      schedule_time,
        "scheduled_datetime": scheduled_datetime,
    }


async def extract_intent_and_entities(user_query: str, history: list[dict] | None = None) -> dict[str, Any]:
    """Classify intent via LLM; extract all entities deterministically from the query.

    The LLM (Ollama, OLLAMA_EXTRACT_MODEL) is called ONLY for intent classification.
    Report names, dates, and times are extracted from the literal user query text
    using regex/parser logic so hallucinated values can never reach downstream code.

    Pass *history* so the LLM can classify multi-turn references correctly.

    Returns::

        {
            "intent":             str,         # get_status | generate_instance | schedule_report | compare_reports | query_database | unknown
            "search_terms":       str | None,  # deterministic report name (stripped query tokens)
            "reporting_date":     str | None,  # DD-MMM-YYYY — only if literally in the query
            "schedule_date":      str | None,  # DD-MMM-YYYY — only if literally in the query
            "schedule_time":      str | None,  # HH:MM 24-hr — only if literally in the query
            "scheduled_datetime": str | None,  # YYYY-MM-DDTHH:MM:00
        }
    """
    from backend.services.llm_service import extract_intent_entities_llm

    # ── Pre-LLM compare shortcut ──────────────────────────────────────────────
    # When the query clearly signals a comparison intent, classify it immediately
    # without calling the LLM. This avoids the 60 s timeout when phi3:mini is
    # cold or overloaded, and guarantees consistent routing for all compare
    # phrasings: "compare hdfc", "comparative analysis of RAQ",
    # "give me comparative analysis for HDFC", "compare two instances of cims_raq".
    _PRECHECK_CMP_RE = re.compile(
        r'\b(compare\b|compar\w+|comparative|comparison)\b',
        re.I,
    )
    if _PRECHECK_CMP_RE.search(user_query):
        _CMP_STOP_PRE = re.compile(
            r'\b(compare|comparing|comparison|comparative|variance|variances'
            r'|diff(?:er(?:ence)?)?|vs\.?|versus|contrast|analys[ie]s?|give'
            r'|side|report[s]?|instance[s]?|these|those|me|the|a|an|of|for'
            r'|to|two|both|and|or|with)\b',
            re.I,
        )
        _pre_cleaned  = _CMP_STOP_PRE.sub(" ", user_query).strip()
        _pre_tokens   = [t for t in re.split(r'[\s,;]+', _pre_cleaned) if len(t) >= 2]
        _pre_report   = _pre_tokens[0] if _pre_tokens else _extract_search_terms(user_query) or None
        logger.info(
            "[PRE_LLM_SHORTCUT] compare keywords detected → compare_reports "
            "(report=%r) — LLM call skipped",
            _pre_report,
        )
        return {
            "intent":             "compare_reports",
            "search_terms":       _pre_report,
            "reporting_date":     None,
            "schedule_date":      None,
            "schedule_time":      None,
            "scheduled_datetime": None,
        }

    logger.info("[LLM_EXTRACT_START] query=%r history_len=%d", user_query, len(history or []))
    _t0 = time.monotonic()

    try:
        raw = await extract_intent_entities_llm(user_query, history=history)
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

    # ── Deterministic entity extraction ────────────────────────────────────────
    # The LLM is ONLY trusted for intent classification.
    # ALL other fields (report name, dates, times) are extracted directly from
    # the literal user query via regex/parser logic — LLM values are ignored so
    # hallucinated entities (e.g. a date invented for "generate instance for abc")
    # can never propagate into downstream handlers.

    # Report name ─────────────────────────────────────────────────────────────
    # compare_reports uses its own stop-word regex because comparison-intent words
    # like "compare", "variance", "vs" are not in the generic _STOP_WORDS set.
    _CMP_STOP = re.compile(
        r"\b(compare|comparing|comparison|comparative|variance|variances|diff(?:er(?:ence)?)?"
        r"|vs\.?|versus|contrast|analys[ie]s?|give|side|report[s]?|instance[s]?"
        r"|these|those|me|the|a|an|of|for|to|two|both|and|or|with)\b",
        re.I,
    )
    if intent == "compare_reports":
        _cmp_cleaned = _CMP_STOP.sub(" ", user_query).strip()
        _cmp_tokens  = [t for t in re.split(r"[\s,;]+", _cmp_cleaned) if len(t) >= 2]
        report_name: Optional[str] = _cmp_tokens[0] if _cmp_tokens else _extract_search_terms(user_query) or None
        if report_name:
            logger.info("[EXTRACT] compare_reports: report_name=%r from query", report_name)
    else:
        report_name = _extract_search_terms(user_query) or None

    # Date / time ─────────────────────────────────────────────────────────────
    # _extract_date_from_query() uses regex + a date-signal guard, so it only
    # returns a value when a date-like pattern is literally present in the query.
    # extract_schedule_datetime() uses the same signal-guarded approach for time.
    reporting_date:     Optional[str] = None
    schedule_date:      Optional[str] = None
    schedule_time:      Optional[str] = None
    scheduled_datetime: Optional[str] = None

    if intent == "schedule_report":
        _sched = extract_schedule_datetime(user_query)
        schedule_date      = _sched["schedule_date"]
        schedule_time      = _sched["schedule_time"]
        scheduled_datetime = _sched["scheduled_datetime"]

    elif intent == "generate_instance":
        reporting_date = _extract_date_from_query(user_query)
        # Reclassify: if the query contains both a date AND a clock time the user
        # is scheduling a future run, not just generating.
        _sched_check = extract_schedule_datetime(user_query)
        if _sched_check["schedule_date"] and _sched_check["schedule_time"]:
            logger.info("[EXTRACT] Reclassify generate_instance → schedule_report (time found in query)")
            intent             = "schedule_report"
            schedule_date      = _sched_check["schedule_date"]
            schedule_time      = _sched_check["schedule_time"]
            scheduled_datetime = _sched_check["scheduled_datetime"]
            reporting_date     = None

    logger.info(
        "[EXTRACT] intent=%s report_name=%r reporting_date=%r "
        "schedule_date=%r schedule_time=%r",
        intent, report_name, reporting_date, schedule_date, schedule_time,
    )
    return {
        "intent":             intent,
        "search_terms":       report_name,
        "reporting_date":     reporting_date,
        "schedule_date":      schedule_date,
        "schedule_time":      schedule_time,
        "scheduled_datetime": scheduled_datetime,
    }
