# report_lookup.py â€” Multi-step pipeline: report name â†’ returns.xml â†’ instance.xml â†’ status.
# Modules: parse_returns, find_matching_reports, get_instances_by_form_id, map_status.

from __future__ import annotations

import logging
import os
import re
import time
from datetime import datetime

logger = logging.getLogger(__name__)

from backend.config import (
    RETURNS_XML_PATH      as _RETURNS_FILE,
    INSTANCE_LOG_XML_PATH as _INSTANCE_FILE,
    INSTANCE_BASE_DIR     as _INSTANCE_BASE_DIR,
    RENDER_BASE_DIR       as _RENDER_BASE_DIR,
)
from backend.tools.xml_loader import load_xml_tree

_STATUS_LABELS: dict[int, str] = {
    # Success
    11: "Success",
    # Failed
    3:  "Failed",
    5:  "Failed",
    8:  "Failed",
    10: "Failed",
    13: "Failed",
    # In Progress
    4:  "In Progress",
    6:  "In Progress",
    # Approved
    9:  "Approved",
    # Rejected
    12: "Rejected",

    0: "Not Started",
}

# Statuses that should prefer ErrorDocPath for download
_FAILED_STATUSES: frozenset[int] = frozenset({3, 5, 8, 10, 13})
# Statuses that should prefer RenderedExcelDocPath for download
_SUCCESS_STATUSES: frozenset[int] = frozenset({9, 11})

# â”€â”€ Parsers (cached once per server lifetime) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

# TTL values — can be overridden via environment variables.
_returns_ttl   = float(os.getenv("RETURNS_TTL_SEC",   "3600"))   # 1 hour
_instances_ttl = float(os.getenv("INSTANCES_TTL_SEC", "120"))    # 2 minutes


class _TTLCache:
    """Simple TTL cache: returns cached data until TTL expires, then re-fetches."""
    __slots__ = ("_ttl", "_data", "_ts")

    def __init__(self, ttl: float) -> None:
        self._ttl  = ttl
        self._data = None
        self._ts   = 0.0

    @property
    def loaded_at(self) -> float:
        return self._ts

    def get(self):
        if self._data is not None and (time.monotonic() - self._ts) < self._ttl:
            return self._data
        return None

    def set(self, data, *, cache_empty: bool = True):
        """Store data.  If cache_empty=False and data is empty/falsy, do NOT
        cache — this lets the next call retry the source (e.g. XML file).
        """
        if not cache_empty and not data:
            return data          # return the empty value without storing it
        self._data = data
        self._ts   = time.monotonic()
        return data


_returns_cache   = _TTLCache(ttl=_returns_ttl)
_instances_cache = _TTLCache(ttl=_instances_ttl)
_norm_cache      = _TTLCache(ttl=_returns_ttl)


def _parse_returns() -> tuple[dict, ...]:
    """Parse returns.xml - uses <Return> elements with Id and Name attributes.
    Duplicates (same Name) are deduplicated; first occurrence wins.
    Cached for RETURNS_TTL_SEC seconds (default 1 hour).
    """
    cached = _returns_cache.get()
    if cached is not None:
        return cached
    root = load_xml_tree(_RETURNS_FILE, "Returns.xml")
    if root is None:
        return ()
    seen_names: set[str] = set()
    rows: list[dict] = []
    for el in root.findall("Return"):
        name = el.attrib.get("Name", "").strip()
        if name and name not in seen_names:
            seen_names.add(name)
            rows.append(el.attrib)
    result = tuple(rows)
    logger.info("Loaded %d unique return(s) from Returns.xml (cache refreshed)", len(rows))
    return _returns_cache.set(result)


def _parse_instances() -> tuple[dict, ...]:
    """Parse XML_InstanceLog - uses <Row> elements.
    Cached for INSTANCES_TTL_SEC seconds (default 2 minutes).
    Empty results are NOT cached so a retry happens on the next call
    (avoids stale empty-cache locking out all instance lookups).
    """
    cached = _instances_cache.get()
    if cached is not None:
        return cached
    logger.debug("[report_lookup] _parse_instances: loading from %s", _INSTANCE_FILE)
    root = load_xml_tree(_INSTANCE_FILE, "XML_InstanceLog.xml")
    if root is None:
        logger.error(
            "[report_lookup] _parse_instances: XML_InstanceLog.xml could not be loaded "
            "(file missing or parse error). Path: %s", _INSTANCE_FILE
        )
        # Do NOT cache the failure so the next request will retry
        return ()
    rows = [el.attrib for el in root.findall("Row")]
    result = tuple(rows)
    if not result:
        logger.warning(
            "[report_lookup] _parse_instances: XML_InstanceLog.xml loaded but contains "
            "0 <Row> elements. Path: %s", _INSTANCE_FILE
        )
        # Do NOT cache empty result — allow retry on next request
        return _instances_cache.set(result, cache_empty=False)
    logger.info(
        "[report_lookup] _parse_instances: loaded %d instance(s) from XML_InstanceLog.xml "
        "(cache refreshed)", len(rows)
    )
    return _instances_cache.set(result)


# Public pipeline functions

def _normalise(s: str) -> str:
    """Lowercase and strip every non-alphanumeric character for matching.
    'CIMS_RAQ(Quarterly)' → 'cimsraqquarterly'
    'raq(monthly)'        → 'raqmonthly'
    """
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _normalised_returns() -> tuple[tuple[str, dict], ...]:
    """Pre-computed (normalised_name, attrib_dict) pairs.
    Automatically rebuilds whenever _parse_returns() refreshes its cache.
    """
    # If returns cache was refreshed more recently than norm cache, rebuild
    if _norm_cache.loaded_at < _returns_cache.loaded_at:
        _norm_cache._data = None
    cached = _norm_cache.get()
    if cached is not None:
        return cached
    result = tuple(
        (_normalise(r.get("Name", "")), r)
        for r in _parse_returns()
        if r.get("Name", "")
    )
    return _norm_cache.set(result)


def find_matching_reports(user_input: str) -> list[dict]:
    """Multi-strategy, case-insensitive matching for flexible user-friendly lookup.

    Strategies (applied in order, returns on first non-empty result):
      1. Bidirectional substring  –  'raq(monthly)' finds 'CIMS_RAQ(Monthly)'
      2. All-keyword token match  –  'raq monthly'  requires every token to appear
      3. Any-keyword token match  –  'raq'           matches every CIMS_RAQ(*)

    Input is normalised (lowercased, special chars stripped) before matching.
    All report names are pre-normalised at startup so matching is O(n).

    Args:
        user_input: Free-text report name from the user (e.g. '  RAQ monthly  ').

    Returns:
        Deduplicated list of matching report attribute dicts from returns.xml.
        Empty list means no match was found by any strategy.
    """
    needle = _normalise(user_input)
    if not needle:
        return []

    pairs = _normalised_returns()

    # Strategy 1: bidirectional substring (needle ⊂ name OR name ⊂ needle)
    substring_matches = [
        r for (norm_name, r) in pairs
        if needle in norm_name or norm_name in needle
    ]
    if substring_matches:
        return substring_matches

    # Strategy 2 & 3: keyword token matching
    # Tokens: split on non-alphanumeric, keep tokens with at least 2 chars
    tokens = [t for t in re.split(r"[^a-z0-9]+", needle) if len(t) >= 2]
    if tokens:
        # All keywords must appear in the report name
        all_token_matches = [
            r for (norm_name, r) in pairs
            if all(t in norm_name for t in tokens)
        ]
        if all_token_matches:
            return all_token_matches

        # At least one keyword must appear in the report name
        any_token_matches = [
            r for (norm_name, r) in pairs
            if any(t in norm_name for t in tokens)
        ]
        if any_token_matches:
            return any_token_matches

    return []


def fuzzy_report_suggestions(user_input: str, n: int = 5, cutoff: float = 0.35) -> list[str]:
    """Return up to *n* report names whose normalised form is similar to *user_input*.

    Uses difflib.get_close_matches (SequenceMatcher ratio) as a last-resort
    fallback when find_matching_reports returns nothing.  Returns original
    (non-normalised) report names suitable for display.

    Args:
        user_input: Raw user-provided text.
        n:          Maximum number of suggestions to return.
        cutoff:     Minimum similarity ratio (0–1).  0.35 is intentionally
                    permissive to surface near-misses.
    """
    import difflib
    needle = _normalise(user_input)
    if not needle:
        return []
    norm_to_orig = {norm: r.get("Name", "") for norm, r in _normalised_returns()}
    close_norms  = difflib.get_close_matches(needle, list(norm_to_orig.keys()), n=n, cutoff=cutoff)
    return [norm_to_orig[c] for c in close_norms if norm_to_orig[c]]


def get_instances_by_form_id(form_id: str) -> list[dict]:
    fid = str(form_id).strip()
    all_rows = _parse_instances()
    matches = [r for r in all_rows if r.get("FormId", "").strip() == fid]
    logger.debug(
        "[report_lookup] get_instances_by_form_id(form_id=%r): "
        "total rows in log=%d, matched=%d",
        fid, len(all_rows), len(matches),
    )
    return matches


def get_available_dates(form_id: str) -> list[str]:
    """Return deduplicated, chronologically sorted reporting dates for a form."""
    seen: set[str] = set()
    unique: list[str] = []
    for r in get_instances_by_form_id(form_id):
        d = r.get("ReportingDate", "").strip()
        if d and d not in seen:
            seen.add(d)
            unique.append(d)
    def _key(d: str) -> datetime:
        try:
            return datetime.strptime(d, "%d-%b-%Y")
        except ValueError:
            return datetime.min
    unique.sort(key=_key, reverse=True)  # latest first
    return unique


def _get_runs_for_date(form_id: str, reporting_date: str) -> list[dict]:
    """Return all instances for (form_id, reporting_date), sorted by DTC ascending."""
    rows = [
        r for r in get_instances_by_form_id(form_id)
        if r.get("ReportingDate", "").strip() == reporting_date
    ]
    rows.sort(key=_dtc_sort_key)
    return rows


def get_instance_by_row_id(row_id: str, form_id: str) -> dict | None:
    """Return the instance row matching the given Id attribute, or None."""
    for r in get_instances_by_form_id(form_id):
        if r.get("Id", "").strip() == str(row_id).strip():
            return r
    return None


def _is_known_date(date_str: str, form_id: str) -> bool:
    """Return True if date_str matches one of the known reporting dates."""
    dates = get_available_dates(form_id)
    ds = date_str.strip()
    return ds in dates or any(ds.lower() in d.lower() for d in dates)


def map_status(code: int) -> str:
    return _STATUS_LABELS.get(code, "Unknown")


def _dtc_sort_key(r: dict) -> datetime:
    """Sort key: parse DTC as datetime so instances sort chronologically.
    Rows with unparseable DTCs sort to datetime.min (oldest).
    """
    try:
        return datetime.strptime(r.get("DTC", ""), "%d-%b-%Y %I:%M:%S %p")
    except ValueError:
        return datetime.min


def _safe_status(row: dict) -> int:
    try:
        return int(row.get("Status", -1))
    except (ValueError, TypeError):
        return -1


# ── File download helpers ──────────────────────────────────────────────────────

def build_render_file_path(form_id: str, filename: str) -> str:
    """Construct an absolute path to a render file under RENDER_BASE_DIR/{form_id}/."""
    safe_fid  = os.path.basename(form_id)
    safe_name = os.path.basename(filename)
    return os.path.join(_RENDER_BASE_DIR, safe_fid, safe_name)


def build_error_file_path(form_id: str, filename: str) -> str:
    """Construct an absolute path to an error file under INSTANCE_BASE_DIR/{form_id}/."""
    safe_fid  = os.path.basename(form_id)
    safe_name = os.path.basename(filename)
    return os.path.join(_INSTANCE_BASE_DIR, safe_fid, safe_name)


def file_exists(path: str) -> bool:
    return os.path.isfile(path)


def _get_download_info(row: dict, form_id: str) -> dict:
    """Return download_url, download_label, status_note for a given instance row.

    File selection is based on the row's status code:
    - Failed statuses (3,5,8,10,13) → ErrorDocPath  → "Download Error File"
    - Success/Approved (9,11)       → RenderedExcelDocPath → "Download Render File"
    - Other statuses                → render first, error as fallback
    """
    code = _safe_status(row)

    def _try_render() -> dict | None:
        path_str = row.get("RenderedExcelDocPath", "").strip()
        if not path_str:
            return None
        filename = os.path.basename(path_str)
        if not filename:
            return None
        full_path = build_render_file_path(form_id, filename)
        if file_exists(full_path):
            url = f"/download-file?form_id={form_id}&type=render&filename={filename}"
            logger.info("[download_info] render file found: %s", full_path)
            return {"download_url": url, "download_label": "Download Render File", "status_note": ""}
        logger.info("[download_info] render file NOT found: %s", full_path)
        return {"download_url": "", "download_label": "", "status_note": "Render file not found."}

    def _try_error() -> dict | None:
        path_str = row.get("ErrorDocPath", "").strip()
        if not path_str:
            return None
        filename = os.path.basename(path_str)
        if not filename:
            return None
        full_path = build_error_file_path(form_id, filename)
        if file_exists(full_path):
            url = f"/download-file?form_id={form_id}&type=error&filename={filename}"
            logger.info("[download_info] error file found: %s", full_path)
            return {"download_url": url, "download_label": "Download Error File", "status_note": ""}
        logger.info("[download_info] error file NOT found: %s", full_path)
        return {"download_url": "", "download_label": "", "status_note": "Error file not found."}

    if code in _FAILED_STATUSES:
        # For failed/error runs always prefer the error document
        result = _try_error()
        return result if result is not None else {"download_url": "", "download_label": "", "status_note": ""}

    if code in _SUCCESS_STATUSES:
        # For success/approved runs always prefer the rendered file
        result = _try_render()
        return result if result is not None else {"download_url": "", "download_label": "", "status_note": ""}

    # Rejected / In-Progress / Not-Started / Unknown: render first, error as fallback
    result = _try_render()
    if result is not None:
        return result
    result = _try_error()
    return result if result is not None else {"download_url": "", "download_label": "", "status_note": ""}


# â”€â”€ Main entry points â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


# ── Instance-based selection helpers ─────────────────────────────────────────

def _fmt_instance_label(dtc: str, reporting_date: str) -> str:
    """Human-readable single-line label for a generated instance."""
    return f"Generated On: {dtc} | Reporting Date: {reporting_date}"


def get_available_instances(form_id: str) -> list[dict]:
    """Return ALL instances for a form, sorted by DTC descending.

    Each entry: {"dtc": str, "reporting_date": str, "status": str, "label": str}
    Unlike get_available_dates(), this keeps duplicate ReportingDate entries so
    the user can distinguish multiple runs for the same reporting period.
    """
    rows = list(get_instances_by_form_id(form_id))
    rows.sort(key=_dtc_sort_key, reverse=True)
    return [
        {
            "dtc":            r.get("DTC", "").strip(),
            "reporting_date": r.get("ReportingDate", "").strip(),
            "status":         r.get("Status", "").strip(),
            "label":          _fmt_instance_label(
                                  r.get("DTC", "").strip(),
                                  r.get("ReportingDate", "").strip(),
                              ),
        }
        for r in rows
        if r.get("DTC", "").strip() or r.get("ReportingDate", "").strip()
    ]


def get_instance_by_dtc(form_id: str, dtc: str, return_name: str) -> dict:
    """Resolve a single instance by exact DTC match.

    Used when the user clicks a chip whose label encodes both DTC and
    ReportingDate (e.g. 'Generated On: X | Reporting Date: Y').
    """
    rows = get_instances_by_form_id(form_id)
    dtc_clean = dtc.strip()
    row = next((r for r in rows if r.get("DTC", "").strip() == dtc_clean), None)
    if not row:
        return {
            "type":                "date_not_found",
            "message":             f"No instance found for DTC '{dtc_clean}'.",
            "form_id":             form_id,
            "return_name":         return_name,
            "available_instances": get_available_instances(form_id),
        }
    code = _safe_status(row)
    dl   = _get_download_info(row, form_id)
    return {
        "type":           "final",
        "report_name":    return_name,
        "reporting_date": row.get("ReportingDate", "").strip(),
        "dtc":            row.get("DTC", "").strip(),
        "status":         map_status(code),
        "status_code":    code,
        "download_url":   dl["download_url"],
        "download_label": dl["download_label"],
        "status_note":    dl["status_note"],
    }


def _build_status_result(form_id: str, ret_name: str, instances: list[dict]) -> dict:
    """Core status-result builder shared by get_report_status / get_report_status_exact.

    Selects the TRUE latest instance by DTC timestamp (not by ReportingDate),
    collects all other instances for the "check another date?" dropdown, and
    returns either a 'latest_with_ask' or 'final' result dict.
    """
    # Sort ALL instances by DTC descending — index 0 is always the true latest run
    sorted_rows = sorted(instances, key=_dtc_sort_key, reverse=True)
    latest_row  = sorted_rows[0]

    code        = _safe_status(latest_row)
    dl          = _get_download_info(latest_row, form_id)
    current_dtc = latest_row.get("DTC", "").strip()
    rep_date    = latest_row.get("ReportingDate", "").strip()

    logger.info(
        "[_build_status_result] form_id=%r  latest DTC=%r  ReportingDate=%r  Status=%r",
        form_id, current_dtc, rep_date, map_status(code),
    )

    # All instances except the one we're about to display
    all_instances   = get_available_instances(form_id)  # already sorted DTC desc
    other_instances = [i for i in all_instances if i["dtc"] != current_dtc]

    if other_instances:
        return {
            "type":            "latest_with_ask",
            "report_name":     ret_name,
            "form_id":         form_id,
            "return_name":     ret_name,
            "reporting_date":  rep_date,
            "status":          map_status(code),
            "status_code":     code,
            "run_time":        current_dtc,
            "other_instances": other_instances,
            "download_url":    dl["download_url"],
            "download_label":  dl["download_label"],
            "status_note":     dl["status_note"],
        }

    return {
        "type":           "final",
        "report_name":    ret_name,
        "reporting_date": rep_date,
        "dtc":            current_dtc,
        "status":         map_status(code),
        "status_code":    code,
        "download_url":   dl["download_url"],
        "download_label": dl["download_label"],
        "status_note":    dl["status_note"],
    }


def get_report_status(report_name: str) -> dict:
    """Full pipeline: name -> return match -> instances -> status.

    Matching is flexible and case-insensitive.  Users do NOT need to type the
    exact report name.  The pipeline tries (in order):
      1. find_matching_reports  -- substring + keyword strategies
      2. fuzzy_report_suggestions -- difflib similarity as a last resort

    Returns a dict with 'type' in {"final", "disambiguation", "date_selection", "error"}.
    """
    # Normalise input: trim whitespace (special chars handled inside _normalise)
    clean_input = report_name.strip()

    matches = find_matching_reports(clean_input)

    if not matches:
        # Last resort: fuzzy similarity suggestions
        suggestions = fuzzy_report_suggestions(clean_input)
        if suggestions:
            opts_text = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(suggestions))
            return {
                "type":    "disambiguation",
                "message": (
                    f"No exact match found for '{clean_input}'. Did you mean one of these?\n\n"
                    f"{opts_text}\n\n"
                    "Reply with the number or name to select."
                ),
                "options": suggestions,
            }
        return {
            "type":    "error",
            "message": (
                f"No matching reports found for '{clean_input}'. "
                "Please try a different name."
            ),
        }

    if len(matches) > 1:
        # Deduplicate option names while preserving order
        seen_opts: dict[str, None] = {}
        for m in matches:
            n = m.get("Name", "")
            if n:
                seen_opts[n] = None
        opts = list(seen_opts.keys())
        opts_text = "\n".join(f"{i + 1}. {name}" for i, name in enumerate(opts))
        return {
            "type":    "disambiguation",
            "message": (
                "Found multiple matching reports. Which one do you mean?\n\n"
                f"{opts_text}\n\n"
                "Reply with the number or name to select."
            ),
            "options": opts,
        }

    match    = matches[0]
    # returns.xml: Id="2041" maps to FormId="2041" in instance log
    form_id  = match.get("Id", "").strip()
    ret_name = match.get("Name", report_name)

    logger.info(
        "[get_report_status] matched report: name=%r  form_id=%r",
        ret_name, form_id,
    )

    instances = get_instances_by_form_id(form_id)

    logger.info(
        "[get_report_status] total instances for form_id=%r: %d",
        form_id, len(instances),
    )

    if not instances:
        logger.warning(
            "[get_report_status] NO instances found for form_id=%r (name=%r). "
            "Check that INSTANCE_LOG_XML_PATH points to the correct file and "
            "that <Row FormId=%r .../> entries exist.",
            form_id, ret_name, form_id,
        )
        return {
            "type":    "error",
            "message": f"Report '{ret_name}' exists but no instances have been generated yet.",
        }

    return _build_status_result(form_id, ret_name, instances)

def get_instance_by_date(form_id: str, date_query: str, return_name: str) -> dict:
    """Resolve a single instance by exact ReportingDate match."""
    rows = get_instances_by_form_id(form_id)
    date_query = date_query.strip()
    # Exact match first, then case-insensitive partial match as fallback
    row = next(
        (r for r in rows if r.get("ReportingDate", "").strip() == date_query),
        None,
    ) or next(
        (r for r in rows if date_query.lower() in r.get("ReportingDate", "").lower()),
        None,
    )
    if not row:
        return {
            "type":           "date_not_found",
            "message":        f"No instance found for '{date_query}'.",
            "form_id":        form_id,
            "return_name":    return_name,
            "available_dates": get_available_dates(form_id),
        }
    code = _safe_status(row)
    dl   = _get_download_info(row, form_id)
    return {
        "type":           "final",
        "report_name":    return_name,
        "reporting_date": row.get("ReportingDate", "").strip(),        "dtc":            row.get("DTC", "").strip(),        "status":         map_status(code),
        "status_code":    code,
        "download_url":   dl["download_url"],
        "download_label": dl["download_label"],
        "status_note":    dl["status_note"],
    }


def get_report_status_exact(report_name: str) -> dict:
    """Exact Name= lookup (no fuzzy). Used after user selects from a disambiguation list."""
    returns = _parse_returns()
    match = next((r for r in returns if r.get("Name", "").strip() == report_name.strip()), None)
    if not match:
        match = next(
            (r for r in returns if r.get("Name", "").strip().lower() == report_name.strip().lower()),
            None,
        )
    if not match:
        return {
            "type":    "error",
            "message": f"Report '{report_name}' not found. Please try again.",
        }
    form_id  = match.get("Id", "").strip()
    ret_name = match.get("Name", report_name)

    logger.info(
        "[get_report_status_exact] matched report: name=%r  form_id=%r",
        ret_name, form_id,
    )

    instances = get_instances_by_form_id(form_id)

    logger.info(
        "[get_report_status_exact] total instances for form_id=%r: %d",
        form_id, len(instances),
    )

    if not instances:
        logger.warning(
            "[get_report_status_exact] NO instances found for form_id=%r (name=%r). "
            "Check that INSTANCE_LOG_XML_PATH points to the correct file and "
            "that <Row FormId=%r .../> entries exist.",
            form_id, ret_name, form_id,
        )
        return {
            "type":    "error",
            "message": f"Report '{ret_name}' exists but no instances have been generated yet.",
        }

    return _build_status_result(form_id, ret_name, instances)


def get_form_id_by_name(report_name: str) -> str | None:
    """Return the Id (Report ID / FormId) for an exact report-name match.

    Matching is case-insensitive.  Returns `None` if the report is not
    found in Returns.xml so the caller can handle the missing-report case.
    Used by the comparison flow: report name -> Report ID -> instance folder.
    """
    name_clean = report_name.strip().lower()
    match = next(
        (r for r in _parse_returns() if r.get("Name", "").strip().lower() == name_clean),
        None,
    )
    return match.get("Id", "").strip() if match else None
