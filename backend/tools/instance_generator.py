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

logger = logging.getLogger(__name__)

_ROOT        = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PERIOD_FILE = os.path.join(_ROOT, "logs", "period.xml")
_DOTNET_URL            = os.getenv("DOTNET_API_URL",        "https://localhost:5000")
_DOTNET_CONTROLLER     = os.getenv("DOTNET_CONTROLLER",     "CreateInstance")
_DOTNET_SESSION_COOKIE = os.getenv("DOTNET_SESSION_COOKIE", "")
_DATE_FMT    = "%d-%b-%Y"
_EXTRA_FMTS  = ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d.%m.%Y"]

# 6.0 — separate endpoint, separate auth model (JWT Bearer via claims, not an
# ASP.NET session cookie). Confirmed via the real 6.0 controller: 5.5's
# FunPubInsertInstanceLog route (session-based) is NOT reachable in 6.0 —
# it 404s there. The real 6.0 action is GenerateReportDB, POST
# /api/CreateInstance/GenerateReportDB, form fields {ReturnId, RptDate, AuditType}
# (iDeal.Api.Common.DTO.ReportDto), auth via [FromHeader] JWT claims (LoginId,
# TenantId) rather than session state.
_DOTNET_6_0_CONTROLLER = os.getenv("XML_6_0_DOTNET_CONTROLLER", "api/CreateInstance")
_DOTNET_6_0_ACTION     = os.getenv("XML_6_0_DOTNET_GENERATE_ACTION", "GenerateReportDB")
# AuditType's meaning is NOT confirmed against the .NET source — this default
# mirrors 5.5's "-1 = not applicable" convention for AuditDataFilterValue.
# Override via env var once the correct value/logic is confirmed.
_DOTNET_6_0_DEFAULT_AUDIT_TYPE = os.getenv("XML_6_0_DEFAULT_AUDIT_TYPE", "-1")

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

_period_ttl   = float(os.getenv("PERIOD_TTL_SEC", "86400"))  # 24 hours
# Per-tenant period cache. 5.5 traffic (tenant_id=None) uses key "" and reads
# the project-relative logs/period.xml (unchanged from before tenant support).
# 6.0 tenants each get their own cache entry, reading <tenant>/DataBase/Period.xml.
_period_caches: dict[str, dict] = {}


def _period_cache_key(tenant_id: str | None) -> str:
    return tenant_id or ""


def _parse_period_master(tenant_id: str | None = None) -> dict[str, dict]:
    """Parse period.xml/Period.xml and return {period_id: attrib_dict}.
    Cached per-tenant for PERIOD_TTL_SEC seconds (default 24 hours).
    """
    key = _period_cache_key(tenant_id)
    cache = _period_caches.setdefault(key, {"data": None, "ts": 0.0})
    now = time.monotonic()
    if cache["data"] is not None and (now - cache["ts"]) < _period_ttl:
        return cache["data"]

    if tenant_id:
        from backend.config import get_period_xml_path
        from backend import config_6_0
        path = get_period_xml_path(tenant_id)
        id_attr = config_6_0.PERIOD_ID_ATTR
        label = "Period.xml"
    else:
        path = _PERIOD_FILE
        id_attr = "Period_Id"
        label = "period.xml"

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
        logger.info("Loaded %d period(s) from %s (tenant_id=%r, cache refreshed)", len(out), label, tenant_id)
        cache["data"] = out
        cache["ts"]   = now
        return out
    except ET.ParseError as exc:
        logger.error("XML parse error in %s: %s", label, exc)
        return {}


def get_period_info(period_id: str | int, tenant_id: str | None = None) -> dict | None:
    """Return period info dict for a given period id, or None."""
    return _parse_period_master(tenant_id).get(str(period_id).strip())


# -- Return resolver (exact match, used post-disambiguation) --------------------

def resolve_return_exact(report_name: str, tenant_id: str | None = None) -> dict | None:
    """Exact-name lookup returning generation metadata for a return.

    Tries: exact Name match, case-insensitive Name, AltName.
    Returns: {form_id, name, period_id, frequency, period_name} or None.
    """
    from backend.tools.report_lookup import _parse_returns  # cached; no re-parse

    name_str = report_name.strip()
    returns  = _parse_returns(tenant_id)

    match = (
        next((r for r in returns if r.get("Name",     "").strip()           == name_str),         None)
        or next((r for r in returns if r.get("Name",  "").strip().lower()   == name_str.lower()), None)
        or next((r for r in returns if r.get("AltName","").strip().lower()  == name_str.lower()), None)
        or next((r for r in returns if r.get("ReturnId","").strip().lower() == name_str.lower()), None)
    )
    if not match:
        return None

    period_id   = match.get("PeriodId", "").strip()
    period_info = get_period_info(period_id, tenant_id) or {}
    # PeriodMaster Frequency is canonical; RepFreq on Return element is fallback.
    # 6.0's Period.xml has no Frequency attribute at all — always falls back to RepFreq.
    frequency   = (period_info.get("Frequency") or match.get("RepFreq", "")).strip().upper()
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


# -- .NET API call (6.0 only) ----------------------------------------------------

async def call_generate_api_6_0(
    form_id: str,
    reporting_date: str,
    tenant_id: str,
    jwt: str | None = None,
) -> dict[str, Any]:
    """POST to the 6.0 .NET GenerateReportDB action.

    6.0 is NOT a drop-in replacement for 5.5's FunPubInsertInstanceLog — it's a
    separate endpoint with a separate auth model:
      - Route:  POST {DOTNET_API_URL}/{XML_6_0_DOTNET_CONTROLLER}/{XML_6_0_DOTNET_GENERATE_ACTION}
                (default: /api/CreateInstance/GenerateReportDB)
      - Auth:   Authorization: Bearer <jwt> — the .NET action reads LoginId/TenantId
                from JWT claims (HttpContext.User), not a session cookie. There is
                no 6.0 equivalent of 5.5's .AspNetCore.Session forwarding.
      - Body (multipart/form-data, iDeal.Api.Common.DTO.ReportDto):
            ReturnId  (int)    — form_id
            RptDate   (string) — reporting_date
            AuditType (int)    — NOT CONFIRMED against .NET source; defaults to
                                  XML_6_0_DEFAULT_AUDIT_TYPE ("-1", mirroring 5.5's
                                  "not applicable" convention). Override once confirmed.
      - Response: StatusCode(result.StatusCode, result.Success ? result.Data : result.Error)
                  i.e. plain HTTP status + a bare JSON body — NOT the 5.5-style
                  [bool, date, message, ...] array. Confirmed success case returns
                  result.Data as a plain string (the new instance log id). Failure
                  shape (result.Error) is not confirmed — logged in full so it can
                  be refined once seen.

    Returns the same {"success": bool, "message": str} shape as call_generate_api()
    so callers (_finalize_generation) don't need version-specific handling.
    """
    if not jwt:
        logger.error(
            "[GENERATE_API_6_0] No JWT provided — GenerateReportDB requires a Bearer "
            "token (tenant_id=%s form_id=%s). Request will likely be rejected.",
            tenant_id, form_id,
        )

    url = f"{_DOTNET_URL}/{_DOTNET_6_0_CONTROLLER}/{_DOTNET_6_0_ACTION}"

    form_data = {
        "ReturnId":  str(form_id),
        "RptDate":   reporting_date,
        "AuditType": _DOTNET_6_0_DEFAULT_AUDIT_TYPE,
    }

    headers = {"X-Requested-With": "XMLHttpRequest"}
    if jwt:
        headers["Authorization"] = f"Bearer {jwt}"

    logger.info(
        "[GENERATE_API_6_0_CALL] url=%s form_id=%s date=%s tenant_id=%s jwt=%s",
        url, form_id, reporting_date, tenant_id, "provided" if jwt else "MISSING",
    )
    _t0 = time.time()
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            follow_redirects=False,
            verify=False,  # self-signed dev cert on localhost, same as 5.5's client
        ) as client:
            resp = await client.post(url, data=form_data, headers=headers)

        _elapsed = time.time() - _t0
        logger.info(
            "[PERF] operation=generate_api_6_0 http_status=%s duration=%.2fs form_id=%s tenant_id=%s",
            resp.status_code, _elapsed, form_id, tenant_id,
        )

        if resp.status_code in (401, 403):
            logger.error(
                "[API_FAILURE_6_0] Generate API returned HTTP %s (auth failure): %s",
                resp.status_code, resp.text[:200],
            )
            return {
                "success": False,
                "message": "Authentication failed. Your session may have expired. Please try again.",
            }

        if resp.status_code == 404:
            logger.error(
                "[API_FAILURE_6_0] Generate API returned HTTP 404 at %s — route not found. "
                "Check XML_6_0_DOTNET_CONTROLLER/XML_6_0_DOTNET_GENERATE_ACTION env vars.",
                url,
            )
            return {"success": False, "message": "Instance generation failed. Please try again."}

        if resp.status_code not in (200, 201, 202):
            logger.error(
                "[API_FAILURE_6_0] Generate API returned HTTP %s: %s",
                resp.status_code, resp.text[:300],
            )
            return {"success": False, "message": "Instance generation failed. Please try again."}

        try:
            data = resp.json()
        except Exception:
            snippet = resp.text[:200].strip()
            logger.error("[API_FAILURE_6_0] Generate API returned non-JSON: %s", snippet)
            return {"success": False, "message": "Instance generation failed. Please try again."}

        # Confirmed success shape: result.Data is a plain string (new InstanceLog id).
        # Any other 2xx body is logged in full and treated as success — failure
        # shapes (result.Error) are not yet confirmed against real error responses.
        if isinstance(data, str):
            logger.info(
                "[GENERATE_SUBMITTED_6_0] form_id=%s date=%s tenant_id=%s instance_log_id=%s",
                form_id, reporting_date, tenant_id, data,
            )
            return {"success": True, "message": "Instance generation submitted successfully."}

        logger.warning(
            "[GENERATE_API_6_0] Unrecognised 2xx response shape, treating as success: %r", data,
        )
        return {"success": True, "message": "Instance generation submitted successfully."}

    except httpx.ConnectError:
        logger.error(
            "[API_FAILURE_6_0] Cannot connect to .NET API at %s — check DOTNET_API_URL in .env "
            "(current value: %s)",
            url, _DOTNET_URL,
        )
        return {
            "success": False,
            "message": "Unable to process the request right now. Please try again.",
        }
    except httpx.TimeoutException:
        logger.error("[API_FAILURE_6_0] Timeout calling .NET API at %s", url)
        return {"success": False, "message": "Generation service timed out. Please try again."}
    except Exception as exc:
        logger.exception("[API_FAILURE_6_0] Unexpected error calling generate API: %s", exc)
        return {"success": False, "message": "Instance generation failed. Please try again."}
