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
# Additional numeric formats tried when DD-MMM-YYYY fails
_EXTRA_FMTS  = ["%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d.%m.%Y"]

# Valid (day, month) terminal pairs per frequency type
_Q_ENDS    = {(31, 3), (30, 6), (30, 9), (31, 12)}   # Quarterly
_H_FY_ENDS = {(31, 3), (30, 9)}                        # Half-Yearly Financial Year
_H_CY_ENDS = {(30, 6), (31, 12)}                       # Half-Yearly Calendar Year


# -- Period master XML parser (TTL-cached, refreshes every 24 hours) ------------

_period_ttl   = float(os.getenv("PERIOD_TTL_SEC", "86400"))  # 24 hours
_period_cache: dict = {"data": None, "ts": 0.0}


def _parse_period_master() -> dict[str, dict]:
    """Parse period.xml and return {Period_Id: attrib_dict}.
    Cached for PERIOD_TTL_SEC seconds (default 24 hours).
    """
    now = time.monotonic()
    if _period_cache["data"] is not None and (now - _period_cache["ts"]) < _period_ttl:
        return _period_cache["data"]
    if not os.path.exists(_PERIOD_FILE):
        logger.warning("period.xml not found: %s", _PERIOD_FILE)
        return {}
    try:
        root = ET.parse(_PERIOD_FILE).getroot()
        out: dict[str, dict] = {}
        for el in root.findall("Row"):
            pid = el.attrib.get("Period_Id", "").strip()
            if pid:
                out[pid] = el.attrib
        logger.info("Loaded %d period(s) from period.xml (cache refreshed)", len(out))
        _period_cache["data"] = out
        _period_cache["ts"]   = now
        return out
    except ET.ParseError as exc:
        logger.error("XML parse error in period.xml: %s", exc)
        return {}


def get_period_info(period_id: str | int) -> dict | None:
    """Return period info dict for a given Period_Id, or None."""
    return _parse_period_master().get(str(period_id).strip())


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
    # PeriodMaster Frequency is canonical; RepFreq on Return element is fallback
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

def _hint_dates(frequency: str, year: int) -> list[str]:
    """Return a short list of example valid dates for a frequency."""
    freq = (frequency or "").upper()
    if freq == "Q":
        return [f"31-Mar-{year}", f"30-Jun-{year}", f"30-Sep-{year}", f"31-Dec-{year}"]
    if freq == "H":
        return [f"31-Mar-{year}", f"30-Sep-{year}"]
    if freq == "C":
        return [f"30-Jun-{year}", f"31-Dec-{year}"]
    if freq == "Y":
        return [f"31-Mar-{year}", f"31-Mar-{year - 1}"]
    if freq == "B":
        return [f"31-Dec-{year}", f"31-Dec-{year - 1}"]
    today = date.today()
    last  = calendar.monthrange(today.year, today.month)[1]
    if freq == "M":
        mname = today.strftime("%b")
        return [f"{last:02d}-{mname}-{today.year}"]
    return []


def validate_reporting_date(date_str: str, frequency: str) -> dict[str, Any]:
    """Validate a reporting date against frequency rules.

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

    if parsed > date.today():
        return {
            "valid":       False,
            "error":       f"'{ds}' is a future date. Future reporting dates are not allowed.",
            "suggestions": _hint_dates(frequency, date.today().year),
        }

    freq = (frequency or "").strip().upper()
    day, month, year = parsed.day, parsed.month, parsed.year

    if freq == "Q":
        if (day, month) not in _Q_ENDS:
            return {
                "valid":       False,
                "error":       (
                    f"'{ds}' is not a valid quarter-end date.\n"
                    "Quarterly reports must be dated 31-Mar, 30-Jun, 30-Sep, or 31-Dec."
                ),
                "suggestions": [f"31-Mar-{year}", f"30-Jun-{year}", f"30-Sep-{year}", f"31-Dec-{year}"],
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
                "suggestions": [f"{last_day:02d}-{mname}-{year}"],
            }

    elif freq == "Y":
        if (day, month) != (31, 3):
            return {
                "valid":       False,
                "error":       f"'{ds}' is not valid for a Yearly (Financial Year) report. Must be 31-Mar.",
                "suggestions": [f"31-Mar-{year}", f"31-Mar-{year - 1}"],
            }

    elif freq == "H":
        if (day, month) not in _H_FY_ENDS:
            return {
                "valid":       False,
                "error":       (
                    f"'{ds}' is not valid for a Half-Yearly (Financial Year) report.\n"
                    "Valid dates: 31-Mar or 30-Sep."
                ),
                "suggestions": [f"31-Mar-{year}", f"30-Sep-{year}"],
            }

    elif freq == "C":
        if (day, month) not in _H_CY_ENDS:
            return {
                "valid":       False,
                "error":       (
                    f"'{ds}' is not valid for a Half-Yearly (Calendar Year) report.\n"
                    "Valid dates: 30-Jun or 31-Dec."
                ),
                "suggestions": [f"30-Jun-{year}", f"31-Dec-{year}"],
            }

    elif freq == "B":
        if (day, month) != (31, 12):
            return {
                "valid":       False,
                "error":       f"'{ds}' is not valid for a Yearly (Calendar Year) report. Must be 31-Dec.",
                "suggestions": [f"31-Dec-{year}", f"31-Dec-{year - 1}"],
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
                "suggestions": [f"15-{mname}-{year}", f"{last_day:02d}-{mname}-{year}"],
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
        # verify=False bypasses the self-signed dev certificate on localhost
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

        # ASP.NET redirects to Login page when session is not authenticated
        if resp.status_code in (301, 302):
            location = resp.headers.get("location", "")
            logger.error(
                "[API_FAILURE] Generate API redirect → %s (session not authenticated?)", location,
            )
            return {
                "success": False,
                "message": (
                    "Authentication failed. The .NET session cookie is missing or expired. "
                    "Please update DOTNET_SESSION_COOKIE in .env."
                ),
            }

        if resp.status_code not in (200, 201, 202):
            logger.error(
                "[API_FAILURE] Generate API returned HTTP %s: %s",
                resp.status_code, resp.text[:200],
            )
            return {"success": False, "message": f"Instance generation failed (HTTP {resp.status_code})."}

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
                    "Authentication failed — the .NET session may have expired. "
                    "Please update DOTNET_SESSION_COOKIE in .env and restart the server."
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
        logger.error("[API_FAILURE] Cannot connect to .NET API at %s", url)
        return {"success": False, "message": "Generation service is unavailable. Please try again later."}
    except Exception as exc:
        logger.exception("[API_FAILURE] Unexpected error calling generate API: %s", exc)
        return {"success": False, "message": "Instance generation failed. Please try again."}
