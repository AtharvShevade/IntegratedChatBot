# instance_generator.py — Validate and trigger report instance generation.
# Pipeline: resolve return metadata → validate date per PeriodMaster frequency → call .NET API.

from __future__ import annotations

import calendar
import logging
import os
import time
import xml.etree.ElementTree as ET
from datetime import date, datetime
from typing import Any

import httpx

from backend import version_config
from backend import config as _config

logger = logging.getLogger(__name__)

_ROOT        = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PERIOD_FILE = os.path.join(_ROOT, "logs", "period.xml")  # 5.5 only — project-local, not under BASE_REPO_PATH
_DOTNET_URL            = os.getenv("DOTNET_API_URL",        "https://localhost:5000")
_DOTNET_CONTROLLER     = os.getenv("DOTNET_CONTROLLER",     "CreateInstance")
_DOTNET_SESSION_COOKIE = os.getenv("DOTNET_SESSION_COOKIE", "")

# 6.0 instance-generation API (CreateInstanceController.GenerateReportDB) —
# separate host/auth mechanism from the 5.5 .NET app above.
_DOTNET_V6_URL: str = os.getenv("DOTNET_V6_API_URL", "https://localhost:7072")
_DATE_FMT    = "%d-%b-%Y"
_EXTRA_FMTS  = ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d.%m.%Y"]

logger.info(
    "[GENERATE_CONFIG] DOTNET_API_URL=%s  DOTNET_CONTROLLER=%s  "
    "DOTNET_SESSION_COOKIE=%s",
    _DOTNET_URL,
    _DOTNET_CONTROLLER,
    "SET" if _DOTNET_SESSION_COOKIE else "NOT SET (will rely on forwarded aspSession)",
)

# Valid (day, month) terminal pairs per frequency type
_Q_ENDS    = {(31, 3), (30, 6), (30, 9), (31, 12)}   # Quarterly
_H_FY_ENDS = {(31, 3), (30, 9)}                        # Half-Yearly Financial Year
_H_CY_ENDS = {(30, 6), (31, 12)}                       # Half-Yearly Calendar Year


# -- Period master XML parser (TTL-cached, refreshes every 24 hours) ------------

_period_ttl    = float(os.getenv("PERIOD_TTL_SEC", "86400"))  # 24 hours
_period_caches: dict[str, dict] = {}  # path -> {"data": ..., "ts": ...} (path-keyed: 6.0 serves multiple tenants)


def _parse_period_master() -> dict[str, dict]:
    """Parse the period master and return {period_id: attrib_dict}.
    Cached for PERIOD_TTL_SEC seconds (default 24 hours).

    5.5 reads the project-local logs/period.xml (unchanged, pre-existing
    behavior — not under BASE_REPO_PATH). 6.0 has its own tenant-scoped
    Period.xml under {TenantId}\\DataBase\\, with different attribute names
    (Id instead of Period_Id) — confirmed against
    D:\\Repo6\\Repo6\\1001\\DataBase\\Period.xml.
    """
    if version_config.IS_V6:
        path = _config.period_xml_path()
        id_attr = "Id"
    else:
        path = _PERIOD_FILE
        id_attr = "Period_Id"
    label = os.path.basename(path)

    now = time.monotonic()
    cache = _period_caches.get(path)
    if cache is not None and (now - cache["ts"]) < _period_ttl:
        return cache["data"]

    if not os.path.exists(path):
        logger.warning("%s not found: %s", label, path)
        return {}
    try:
        root = ET.parse(path).getroot()
        out: dict[str, dict] = {}
        for el in root.findall("Row"):
            pid = el.attrib.get(id_attr, "").strip()
            if pid:
                out[pid] = el.attrib
        logger.info("Loaded %d period(s) from %s (cache refreshed)", len(out), label)
        _period_caches[path] = {"data": out, "ts": now}
        return out
    except ET.ParseError as exc:
        logger.error("XML parse error in %s: %s", label, exc)
        return {}


def get_period_info(period_id: str | int) -> dict | None:
    """Return period info dict for a given period id, or None."""
    return _parse_period_master().get(str(period_id).strip())


# PeriodId -> Frequency fallback, sourced from 5.5's Period.xml (which has a
# real Frequency attribute per period). Used when Period.xml's own Frequency
# attribute is absent, since a Return's own RepFreq can be inconsistent across
# returns sharing the same period (e.g. PeriodId 107 "Yearly" appears with
# RepFreq 'Y' on most returns but 'A' on others, such as CIMS_RAQ(Annually)/
# RAQ(Annually)). PeriodId is the canonical key, so resolving frequency from
# it (when Period.xml's own Frequency is absent) avoids silently accepting
# any date because 'A' isn't a code the validator recognises.
_PERIOD_ID_TO_FREQUENCY: dict[str, str] = {
    "101": "D",   # Daily
    "102": "W",   # Weekly
    "103": "F",   # Fortnightly
    "104": "M",   # Monthly
    "105": "Q",   # Quarterly
    "106": "H",   # Half Yearly
    "107": "Y",   # Yearly
    "108": "C",   # Half Yearly (Calendar Year)
    "109": "Z",   # Fortnightly + Monthly
    "111": "HM",  # Half Monthly
    "113": "G",   # As An When
}


# -- Return resolver (exact match, used post-disambiguation) --------------------

def resolve_return_exact(report_name: str) -> dict | None:
    """Exact-name lookup returning generation metadata for a return.

    Tries: exact Name match, case-insensitive Name, AltName.
    Returns: {form_id, name, period_id, frequency, period_name} or None.
    """
    from backend.tools.report_lookup import _parse_returns  # cached; no re-parse

    name_str = report_name.strip()
    returns  = _parse_returns()

    match = (
        next((r for r in returns if r.get("Name",     "").strip()           == name_str),         None)
        or next((r for r in returns if r.get("Name",  "").strip().lower()   == name_str.lower()), None)
        or next((r for r in returns if r.get("AltName","").strip().lower()  == name_str.lower()), None)
        or next((r for r in returns if r.get("ReturnId","").strip().lower() == name_str.lower()), None)
    )
    if not match:
        return None

    period_id   = match.get("PeriodId", "").strip()
    period_info = get_period_info(period_id) or {}
    # Frequency resolution, in priority order:
    #   1. Period.xml's own Frequency attribute (canonical).
    #   2. _PERIOD_ID_TO_FREQUENCY[period_id] — fallback when absent.
    #   3. The Return's own RepFreq — last resort only, since it can be
    #      inconsistent across returns sharing the same PeriodId (e.g. 'A'
    #      vs 'Y' both appearing under PeriodId 107 "Yearly").
    frequency = (
        period_info.get("Frequency")
        or _PERIOD_ID_TO_FREQUENCY.get(period_id)
        or match.get("RepFreq", "")
    ).strip().upper()
    period_name = period_info.get("PeriodName", "").strip()

    return {
        "form_id":     match.get("Id", "").strip(),
        "name":        match.get("Name", report_name),
        "period_id":   period_id,
        "frequency":   frequency,
        "period_name": period_name,
    }


# -- Date validation ------------------------------------------------------------

def _hint_dates(frequency: str, year: int, *, filter_future: bool = True, filter_past: bool = False) -> list[str]:
    """Return a short list of example valid dates for a frequency.

    *filter_future* (default True) — exclude dates after today (generate-instance mode).
    *filter_past*   (default False) — exclude dates on or before today (scheduling mode).
    Both flags are mutually exclusive; *filter_past* takes priority when both are set.
    """
    freq = (frequency or "").upper()
    today = date.today()

    candidates: list[str] = []
    if freq == "Q":
        candidates = [f"31-Mar-{year}", f"30-Jun-{year}", f"30-Sep-{year}", f"31-Dec-{year}"]
        # Also include previous year quarter-ends for more options
        candidates += [f"31-Mar-{year - 1}", f"30-Jun-{year - 1}", f"30-Sep-{year - 1}", f"31-Dec-{year - 1}"]
    elif freq == "H":
        candidates = [f"31-Mar-{year}", f"30-Sep-{year}", f"31-Mar-{year - 1}", f"30-Sep-{year - 1}"]
    elif freq == "C":
        candidates = [f"30-Jun-{year}", f"31-Dec-{year}", f"30-Jun-{year - 1}", f"31-Dec-{year - 1}"]
    elif freq == "Y":
        candidates = [f"31-Mar-{year}", f"31-Mar-{year - 1}"]
    elif freq == "B":
        candidates = [f"31-Dec-{year}", f"31-Dec-{year - 1}"]
    elif freq == "M":
        # Last day of the current and previous month
        prev_month = today.replace(day=1) - __import__("datetime").timedelta(days=1)
        last_curr = calendar.monthrange(today.year, today.month)[1]
        mname_curr = today.strftime("%b")
        mname_prev = prev_month.strftime("%b")
        candidates = [
            f"{last_curr:02d}-{mname_curr}-{today.year}",
            f"{prev_month.day:02d}-{mname_prev}-{prev_month.year}",
        ]
    else:
        return []

    if not filter_future and not filter_past:
        return candidates

    # filter_past (scheduling): keep only strictly future dates.
    # filter_future (generate, default): keep only past/current dates.
    valid: list[str] = []
    for ds in candidates:
        try:
            d = datetime.strptime(ds, _DATE_FMT).date()
            if filter_past:
                if d > today:
                    valid.append(ds)
            else:  # filter_future
                if d <= today:
                    valid.append(ds)
        except ValueError:
            continue

    logger.debug("[VALID_SUGGESTIONS_FILTERED] freq=%s candidates=%d valid=%d filter_past=%s", freq, len(candidates), len(valid), filter_past)
    return valid


def validate_reporting_date(
    date_str: str, frequency: str, *, require_future: bool = False, time_str: str | None = None,
) -> dict[str, Any]:
    """Validate a reporting date against frequency rules.

    Args:
        require_future: When True (scheduling mode) only strictly future dates are
                        accepted — past/current dates are rejected.  When False
                        (default, generate-instance mode) only past/current dates
                        are accepted — future dates are rejected.
                        All frequency/period checks (Q/M/Y/H/…) are applied in both modes.
        time_str:       Optional "HH:MM" schedule time. When the date resolves to
                        today and a time is given, the current-day check compares
                        the full datetime (so a later time today is accepted)
                        instead of rejecting today's date outright.

    Returns: {"valid": bool, "error": str | None, "suggestions": list[str]}
    """
    import re as _re
    ds = date_str.strip()

    # ---- Early year sanity check (catches 3-digit years before strptime) ----
    # Extract the year portion from any recognised date format
    _year_from_numeric = _re.match(r'^\d{1,2}[/.-]\d{1,2}[/.-](\d+)$', ds)
    _year_from_alpha   = _re.match(r'^\d{1,2}-[A-Za-z]{3}-(\d+)$', ds)
    _raw_year = int((_year_from_numeric or _year_from_alpha).group(1)) \
        if (_year_from_numeric or _year_from_alpha) else None
    if _raw_year is not None and not (1900 <= _raw_year <= 2099):
        return {
            "valid":       False,
            "error":       (
                f"'{ds}' has an invalid year ({_raw_year}). "
                f"Please enter a 4-digit year between 1900 and 2099 "
                f"(e.g. 31-Mar-2024)."
            ),
            "suggestions": _hint_dates(frequency, date.today().year),
        }
    # -------------------------------------------------------------------------

    parsed = None

    # Try primary format first
    try:
        parsed = datetime.strptime(ds, _DATE_FMT).date()
    except ValueError:
        pass

    # Try common numeric formats (DD/MM/YYYY etc.) so they reach proper validation
    if parsed is None:
        for fmt in _EXTRA_FMTS:
            try:
                parsed = datetime.strptime(ds, fmt).date()
                break
            except ValueError:
                pass

    if parsed is None:
        # Attempt to detect impossible-day-of-month (e.g. 31 April → clamp to 30 April)
        import re as _re2
        _impossible_match = _re2.match(r'^(\d{1,2})-([A-Za-z]{3})-(\d{4})$', ds)
        if _impossible_match:
            _d, _m, _y = int(_impossible_match.group(1)), _impossible_match.group(2), int(_impossible_match.group(3))
            try:
                _month_num = datetime.strptime(_m, "%b").month
                _last_day = calendar.monthrange(_y, _month_num)[1]
                if _d > _last_day:
                    clamped = f"{_last_day:02d}-{_m.capitalize()}-{_y}"
                    return {
                        "valid":       False,
                        "error":       (
                            f"'{ds}' is not a valid calendar date. "
                            f"{datetime(2000, _month_num, 1).strftime('%B')} has only {_last_day} days.\n"
                            f"Did you mean **{clamped}**?"
                        ),
                        "suggestions": [clamped],
                    }
            except ValueError:
                pass

        # Distinguish "right format, wrong calendar date" from "unrecognised input"
        if _re.match(r"^\d{1,2}[-/.\s]\d{1,2}[-/.\s]\d{2,4}$", ds) or \
           _re.match(r"^\d{1,2}-[A-Za-z]{3}-\d{4}$", ds):
            error_msg = (
                f"'{ds}' is not a valid calendar date "
                f"(e.g. February only has 28 or 29 days). "
                f"Please enter a valid date."
            )
        else:
            error_msg = f"Cannot parse '{ds}'. Please enter a date like 31-Mar-2024, 31/03/2024, or 31 March 2024."
        logger.debug("[DATE_VALIDATION_FAIL] unparsable=%r", ds)
        return {
            "valid":       False,
            "error":       error_msg,
            "suggestions": _hint_dates(frequency, date.today().year),
        }

    # Reject implausible years (must be 4-digit year between 1900 and 2099)
    if not (1900 <= parsed.year <= 2099):
        return {
            "valid":       False,
            "error":       (
                f"'{ds}' has an invalid year ({parsed.year}). "
                f"Please enter a 4-digit year between 1900 and 2099 "
                f"(e.g. 31-Mar-2024)."
            ),
            "suggestions": _hint_dates(frequency, date.today().year),
        }

    today_date = date.today()

    if require_future:
        # Scheduling mode: require a strictly future date — except when the date
        # is today and a schedule time is given, in which case a later time
        # today is allowed (e.g. Daily reports scheduled later the same day).
        is_past = parsed < today_date
        is_today_and_not_later = False
        is_today_past_time = False
        if parsed == today_date:
            if time_str:
                try:
                    sched_time = datetime.strptime(time_str.strip(), "%H:%M").time()
                    is_today_and_not_later = sched_time <= datetime.now().time()
                    is_today_past_time = is_today_and_not_later
                except ValueError:
                    is_today_and_not_later = True  # unparsable time — fall back to rejecting "today"
            else:
                is_today_and_not_later = True  # no time yet — can't confirm it's later today

        if is_past or is_today_and_not_later:
            logger.debug("[PAST_DATE_REJECTED_SCHEDULE] date=%s time=%s today=%s", ds, time_str, today_date)
            # Suggest the next valid future dates for this frequency.
            future_hints = _hint_dates(frequency, today_date.year, filter_past=True)
            if not future_hints:
                # All current-year dates have passed — pull from next year.
                future_hints = _hint_dates(frequency, today_date.year + 1, filter_past=True)
            error_msg = (
                "The scheduled time must be in the future for today's date."
                if is_today_past_time else
                f"'{ds}' is not a future date. Scheduling requires a future reporting date."
            )
            return {
                "valid":       False,
                "error":       error_msg,
                "suggestions": future_hints,
            }
    else:
        # Generate-instance mode: reject future dates.
        if parsed > today_date:
            logger.debug("[FUTURE_DATE_REJECTED] date=%s today=%s", ds, today_date)
            past_suggestions = _hint_dates(frequency, today_date.year)
            return {
                "valid":       False,
                "error":       f"'{ds}' is a future date. Future reporting dates are not allowed.",
                "suggestions": past_suggestions,
            }

    freq = (frequency or "").strip().upper()
    day, month, year = parsed.day, parsed.month, parsed.year

    def _filter_future(suggestions: list[str]) -> list[str]:
        """Filter suggestions to match the validation mode.

        Generate mode (require_future=False): keep only past/current dates.
        Schedule mode  (require_future=True):  keep only strictly future dates.
        """
        today_ = date.today()
        result = []
        for s in suggestions:
            try:
                d = datetime.strptime(s, _DATE_FMT).date()
                if require_future:
                    if d > today_:
                        result.append(s)
                else:
                    if d <= today_:
                        result.append(s)
            except ValueError:
                continue
        return result

    if freq == "Q":
        if (day, month) not in _Q_ENDS:
            return {
                "valid":       False,
                "error":       (
                    f"'{ds}' is not a valid quarter-end date.\n"
                    "Quarterly reports must be dated 31-Mar, 30-Jun, 30-Sep, or 31-Dec."
                ),
                "suggestions": _filter_future([f"31-Mar-{year}", f"30-Jun-{year}", f"30-Sep-{year}", f"31-Dec-{year}"]),
            }

    elif freq == "M":
        last_day = calendar.monthrange(year, month)[1]
        if day != last_day:
            mname = parsed.strftime("%b")
            return {
                "valid":       False,
                "error":       (
                    f"'{ds}' is not the last day of {parsed.strftime('%B %Y')}.\n"
                    "Monthly reports must use the last day of the month."
                ),
                "suggestions": _filter_future([f"{last_day:02d}-{mname}-{year}"]),
            }

    elif freq == "Y":
        if (day, month) != (31, 3):
            return {
                "valid":       False,
                "error":       f"'{ds}' is not valid for a Yearly (Financial Year) report. Must be 31-Mar.",
                "suggestions": _filter_future([f"31-Mar-{year}", f"31-Mar-{year - 1}"]),
            }

    elif freq == "H":
        if (day, month) not in _H_FY_ENDS:
            return {
                "valid":       False,
                "error":       (
                    f"'{ds}' is not valid for a Half-Yearly (Financial Year) report.\n"
                    "Valid dates: 31-Mar or 30-Sep."
                ),
                "suggestions": _filter_future([f"31-Mar-{year}", f"30-Sep-{year}"]),
            }

    elif freq == "C":
        if (day, month) not in _H_CY_ENDS:
            return {
                "valid":       False,
                "error":       (
                    f"'{ds}' is not valid for a Half-Yearly (Calendar Year) report.\n"
                    "Valid dates: 30-Jun or 31-Dec."
                ),
                "suggestions": _filter_future([f"30-Jun-{year}", f"31-Dec-{year}"]),
            }

    elif freq == "B":
        if (day, month) != (31, 12):
            return {
                "valid":       False,
                "error":       f"'{ds}' is not valid for a Yearly (Calendar Year) report. Must be 31-Dec.",
                "suggestions": _filter_future([f"31-Dec-{year}", f"31-Dec-{year - 1}"]),
            }

    elif freq == "W":
        if parsed.weekday() != 4:  # 0 = Monday, 4 = Friday
            return {
                "valid":       False,
                "error":       f"'{ds}' is not a Friday. Weekly reports must use Fridays.",
                "suggestions": [],
            }

    elif freq == "F":
        last_day = calendar.monthrange(year, month)[1]
        if day not in (15, last_day):
            mname = parsed.strftime("%b")
            return {
                "valid":       False,
                "error":       (
                    f"'{ds}' is not valid for a Fortnightly report.\n"
                    "Valid: 15th or last day of month."
                ),
                "suggestions": _filter_future([f"15-{mname}-{year}", f"{last_day:02d}-{mname}-{year}"]),
            }

    # D, G (as-and-when), HM, and unrecognised frequencies: any valid past date accepted
    return {"valid": True, "error": None, "suggestions": []}


def next_reporting_date(frequency: str, due_days: str | int | None = None, *, after: date | None = None) -> dict[str, Any]:
    """Compute the next period-end reporting date for *frequency*, plus its
    submission due date (period-end + due_days), relative to *after* (default:
    today). Reuses the same frequency period-end tables as
    validate_reporting_date()/_hint_dates() so "what counts as a valid date"
    and "what's the next one" never disagree.

    Returns: {"period_end": "DD-Mon-YYYY", "due_date": "DD-Mon-YYYY" | None}
    or {"period_end": None, "error": str} if the frequency has no fixed
    period-end (e.g. daily, as-and-when).
    """
    today = after or date.today()
    freq = (frequency or "").strip().upper()

    def _next_from_ends(ends: set[tuple[int, int]]) -> date:
        candidates = sorted(
            date(y, m, d) for y in (today.year, today.year + 1) for (d, m) in ends
        )
        return next(d for d in candidates if d > today)

    if freq == "Q":
        period_end = _next_from_ends(_Q_ENDS)
    elif freq == "H":
        period_end = _next_from_ends(_H_FY_ENDS)
    elif freq == "C":
        period_end = _next_from_ends(_H_CY_ENDS)
    elif freq == "Y":
        period_end = _next_from_ends({(31, 3)})
    elif freq == "B":
        period_end = _next_from_ends({(31, 12)})
    elif freq == "M":
        y, m = today.year, today.month
        last_day = calendar.monthrange(y, m)[1]
        period_end = date(y, m, last_day)
        if period_end <= today:
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)
            last_day = calendar.monthrange(y, m)[1]
            period_end = date(y, m, last_day)
    elif freq == "W":
        days_ahead = (4 - today.weekday()) % 7  # 4 = Friday
        period_end = today + __import__("datetime").timedelta(days=days_ahead or 7)
    elif freq == "F":
        y, m = today.year, today.month
        last_day = calendar.monthrange(y, m)[1]
        for candidate in (date(y, m, 15), date(y, m, last_day)):
            if candidate > today:
                period_end = candidate
                break
        else:
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)
            period_end = date(y, m, 15)
    else:
        return {
            "period_end": None,
            "due_date": None,
            "error": f"Frequency {frequency!r} has no fixed period-end date (daily/as-and-when returns are due continuously).",
        }

    due_date = None
    if due_days is not None:
        try:
            due_date = period_end + __import__("datetime").timedelta(days=int(due_days))
        except (TypeError, ValueError):
            due_date = None

    return {
        "period_end": period_end.strftime(_DATE_FMT),
        "due_date": due_date.strftime(_DATE_FMT) if due_date else None,
        "error": None,
    }


# -- .NET API call --------------------------------------------------------------

async def call_generate_api(
    form_id: str,
    reporting_date: str,
    asp_session: str | None = None,
) -> dict[str, Any]:
    """POST to the .NET FunPubInsertInstanceLog action.

    asp_session — live .AspNetCore.Session cookie value forwarded from the browser.
                  Falls back to DOTNET_SESSION_COOKIE env var if not provided.
    
        FunPubInsertInstanceLog(int DDLFormId, string ReportType,
            DateTime ParamDTRptDate, bool PropPubBoolIsExtract,
            bool PropPubBoolIsInstance, ClsParameters[] Param,
            string FilingIndicators)

    Response is a JSON array:
        [false, 0]                                     → server-side date validation failed
        [true, date, XBRL_GENERATION_FAILED]           → scheduler/log insert error
        [true, date, XBRL_GENERATION_SUBMITTED, true,
         REPORT_ADDED_SUCCESS]                         → submitted successfully
    """
    url = f"{_DOTNET_URL}/{_DOTNET_CONTROLLER}/FunPubInsertInstanceLog"

    # Form-encoded parameters matching the C# action parameters exactly
    form_data = {
        "DDLFormId":             str(form_id),
        "ReportType":            "",
        "ParamDTRptDate":        reporting_date,   # dd-MMM-yyyy
        "PropPubBoolIsExtract":  "true",
        "PropPubBoolIsInstance": "true",
        "FilingIndicators":      "",
    }

    # ASP.NET Core session auth — prefer live cookie forwarded from browser,
    # fall back to static env var (useful for manual testing via .env)
    cookies: dict[str, str] = {}
    cookie_value = asp_session or _DOTNET_SESSION_COOKIE
    if cookie_value:
        # URL-decode in case the value arrived percent-encoded (from .env or URL param)
        import urllib.parse
        cookie_value = urllib.parse.unquote(cookie_value)
        cookies[".AspNetCore.Session"] = cookie_value
        logger.info(
            "[GENERATE_API] session cookie present (first 16 chars): %s", cookie_value[:16],
        )
    else:
        logger.warning(
            "[GENERATE_API] No .AspNetCore.Session cookie — request will likely be rejected",
        )

    logger.info(
        "[GENERATE_API_CALL] url=%s form_id=%s date=%s session_src=%s",
        url, form_id, reporting_date, "forwarded" if asp_session else "env",
    )
    _t0 = time.time()
    try:
        # verify=False bypasses the self-signed dev certificate on localhost.
        # follow_redirects=False so we can distinguish an HTTPS-upgrade redirect
        # (HTTP→HTTPS, safe to follow) from a Login-page redirect (auth failure).
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            follow_redirects=False,
            verify=False,
        ) as client:
            resp = await client.post(
                url,
                data=form_data,
                cookies=cookies,
                headers={"X-Requested-With": "XMLHttpRequest"},
            )

        _elapsed = time.time() - _t0
        logger.info(
            "[PERF] operation=generate_api http_status=%s duration=%.2fs form_id=%s",
            resp.status_code, _elapsed, form_id,
        )

        # Handle redirects — two distinct cases:
        #   1. HTTP→HTTPS upgrade (EnableHttpsRedirection):
        #      location is the same path but on https://  → retry once over HTTPS
        #   2. Session expired / unauthenticated:
        #      location points to a login path  → auth failure
        if resp.status_code in (301, 302):
            location = resp.headers.get("location", "")
            logger.info("[GENERATE_API] Redirect → %s", location)

            # Case 1: HTTPS upgrade — location starts with https:// and same host
            if location.lower().startswith("https://") and "/account" not in location.lower() and "/login" not in location.lower():
                logger.info("[GENERATE_API] HTTP→HTTPS redirect detected — retrying over HTTPS")
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(30.0),
                    follow_redirects=False,
                    verify=False,
                ) as client2:
                    resp = await client2.post(
                        location,
                        data=form_data,
                        cookies=cookies,
                        headers={"X-Requested-With": "XMLHttpRequest"},
                    )
                logger.info(
                    "[GENERATE_API] HTTPS retry status=%s", resp.status_code
                )
                # If the HTTPS response is also a redirect it's an auth failure
                if resp.status_code in (301, 302):
                    loc2 = resp.headers.get("location", "")
                    logger.error("[API_FAILURE] HTTPS retry redirected to %s — auth failure", loc2)
                    return {
                        "success": False,
                        "message": (
                            "Authentication failed. Your session may have expired. "
                            "Please try again."
                        ),
                    }
            else:
                # Case 2: login redirect
                logger.error(
                    "[API_FAILURE] Generate API redirect to login → %s "
                    "(session not authenticated)", location,
                )
                return {
                    "success": False,
                    "message": (
                        "Authentication failed. Your session may have expired. "
                        "Please try again."
                    ),
                }

        if resp.status_code not in (200, 201, 202):
            logger.error(
                "[API_FAILURE] Generate API returned HTTP %s: %s",
                resp.status_code, resp.text[:200],
            )
            return {"success": False, "message": "Instance generation failed. Please try again."}

        # Parse response array: [bool, date, message, bool?, successMsg?]
        try:
            data = resp.json()
        except Exception:
            # Non-JSON 200 — likely the login page returned instead of API response.
            snippet = resp.text[:120].strip()
            logger.error(
                "[API_FAILURE] Generate API returned non-JSON (session expired?): %s", snippet,
            )
            return {
                "success": False,
                "message": (
                    "Authentication failed — session may have expired. "
                    "Please login again and try generating the instance once more."
                ),
            }
            

        if isinstance(data, list) and len(data) >= 1:
            first = data[0]
            # [false, 0] → server-side date validation rejected the date
            if first is False or first == 0:
                logger.warning(
                    "[GENERATE_REJECTED] server rejected date=%s form_id=%s", reporting_date, form_id,
                )
                return {"success": False, "message": "The server rejected the reporting date. Please verify and try again."}
            # [true, date, msg, true, successMsg] → submitted
            if len(data) >= 4 and data[3] is True:
                success_msg = str(data[4]) if len(data) > 4 else "Instance generation submitted successfully."
                logger.info(
                    "[GENERATE_SUBMITTED] form_id=%s date=%s message=%r",
                    form_id, reporting_date, success_msg,
                )
                return {"success": True, "message": success_msg}
            # [true, date, failMsg, ...] → scheduler/log error
            fail_msg = str(data[2]) if len(data) >= 3 else "Instance generation failed."
            logger.error(
                "[GENERATE_FAIL] form_id=%s response=%r", form_id, data,
            )
            return {"success": False, "message": fail_msg}

        # Unexpected shape — assume success on HTTP 200
        return {"success": True, "message": "Instance generation started successfully."}

    except httpx.ConnectError:
        logger.error(
            "[API_FAILURE] Cannot connect to .NET API at %s — "
            "check DOTNET_API_URL in .env (current value: %s)",
            url, _DOTNET_URL,
        )
        return {
            "success": False,
            "message": "Unable to process the request right now. Please try again.",
        }
    except httpx.TimeoutException:
        logger.error("[API_FAILURE] Timeout calling .NET API at %s", url)
        return {"success": False, "message": "Generation service timed out. Please try again."}
    except Exception as exc:
        logger.exception("[API_FAILURE] Unexpected error calling generate API: %s", exc)
        return {"success": False, "message": "Instance generation failed. Please try again."}


# -- 6.0 .NET API call ------------------------------------------------------
#
# 6.0's CreateInstanceController is a different controller with a different
# DTO and auth mechanism than 5.5's FunPubInsertInstanceLog — this is a new,
# separate function; call_generate_api() above is untouched and still used
# for APP_VERSION=5.5.
#
#     POST /api/CreateInstance/GenerateReportDB
#     [FromForm] ReportDto { ReturnId, RptDate, AuditType }
#     Cookie: accessToken={jwt}   (confirmed: [Authorize] reads the JWT from
#         the same HttpOnly "accessToken" cookie the main React app relies on
#         via withCredentials — NOT an Authorization: Bearer header. The
#         ChatbotToken endpoint just echoes Request.Cookies["accessToken"]
#         back as JSON so the cross-origin chatbot iframe can obtain it via
#         postMessage and replay it here as a cookie.)
#
# Response: StatusCode(result.StatusCode, result.Success ? result.Data : result.Error)

_V6_ACCESS_TOKEN_COOKIE_NAME = "accessToken"

async def call_generate_api_v6(
    form_id: str,
    reporting_date: str,
    tenant_id: str,
    jwt: str | None = None,
    audit_type: int = 0,
    language: str = "en",
) -> dict[str, Any]:
    """POST to the 6.0 .NET CreateInstanceController.GenerateReportDB action.

    form_id        — maps to ReportDto.ReturnId (6.0's Return.xml Id serves
                      both the FormId and ReturnId role, see report_lookup.py).
    reporting_date — RptDate, expected as dd-MMM-yyyy (StandardDateFormat in
                      CreateInstanceModel.cs).
    tenant_id      — resolved TenantId for the current request; not sent on
                      the wire directly (the .NET side reads it from the JWT's
                      TenantId claim) — included here for logging only.
    jwt            — short-lived token from POST /api/Authentication/chatbotToken,
                      forwarded from the chatbot iframe's CHATBOT_AUTH postMessage.
                      Sent back as the "accessToken" cookie (see module comment above).
    """
    url = f"{_DOTNET_V6_URL}/api/CreateInstance/GenerateReportDB"

    form_data = {
        "ReturnId":   str(form_id),
        "RptDate":    reporting_date,
        "AuditType":  str(audit_type),
    }
    headers = {"language": language}
    cookies: dict[str, str] = {}
    if jwt:
        cookies[_V6_ACCESS_TOKEN_COOKIE_NAME] = jwt
    else:
        logger.warning(
            "[GENERATE_API_V6] No JWT provided for tenant_id=%s form_id=%s — "
            "request will likely be rejected (401)",
            tenant_id, form_id,
        )

    logger.info(
        "[GENERATE_API_V6_CALL] url=%s tenant_id=%s form_id=%s date=%s",
        url, tenant_id, form_id, reporting_date,
    )
    _t0 = time.time()
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            follow_redirects=False,
            verify=False,
        ) as client:
            resp = await client.post(url, data=form_data, headers=headers, cookies=cookies)

        _elapsed = time.time() - _t0
        logger.info(
            "[PERF] operation=generate_api_v6 http_status=%s duration=%.2fs form_id=%s",
            resp.status_code, _elapsed, form_id,
        )

        if resp.status_code == 401:
            logger.error("[API_FAILURE] 6.0 Generate API returned 401 — JWT invalid/expired")
            return {
                "success": False,
                "message": "Authentication failed. Your session may have expired. Please try again.",
            }

        try:
            data = resp.json()
        except Exception:
            snippet = resp.text[:200].strip()
            logger.error("[API_FAILURE] 6.0 Generate API returned non-JSON: %s", snippet)
            return {"success": False, "message": "Instance generation failed. Please try again."}

        if resp.status_code not in (200, 201, 202):
            message = data.get("message") if isinstance(data, dict) else None
            logger.error(
                "[API_FAILURE] 6.0 Generate API returned HTTP %s: %s",
                resp.status_code, data,
            )
            return {"success": False, "message": message or "Instance generation failed. Please try again."}

        # Success path — result.Data is the new InstanceLog Id (see
        # CreateInstanceModel.GenerateInstanceDBAsync -> OperationResult.Successful).
        new_id = data if not isinstance(data, dict) else data.get("data") or data.get("Data")
        logger.info(
            "[GENERATE_SUBMITTED_V6] tenant_id=%s form_id=%s date=%s new_instance_log_id=%s",
            tenant_id, form_id, reporting_date, new_id,
        )
        return {"success": True, "message": "Instance generation submitted successfully.", "instance_log_id": new_id}

    except httpx.ConnectError:
        logger.error(
            "[API_FAILURE] Cannot connect to 6.0 .NET API at %s — check DOTNET_V6_API_URL",
            url,
        )
        return {"success": False, "message": "Unable to process the request right now. Please try again."}
    except httpx.TimeoutException:
        logger.error("[API_FAILURE] Timeout calling 6.0 .NET API at %s", url)
        return {"success": False, "message": "Generation service timed out. Please try again."}
    except Exception as exc:
        logger.exception("[API_FAILURE] Unexpected error calling 6.0 generate API: %s", exc)
        return {"success": False, "message": "Instance generation failed. Please try again."}
