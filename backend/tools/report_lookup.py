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
    """Lowercase, convert separators to spaces, and strip remaining special chars.
    Preserves word boundaries so fuzzy/token matching works correctly.
    'CIMS_LR (Quarterly)' → 'cims lr quarterly'
    'CIMS-RAQ'            → 'cims raq'
    'raq(monthly)'        → 'raq monthly'
    """
    s = s.lower()
    s = re.sub(r"[_()/\-]", " ", s)   # convert separators to spaces
    s = re.sub(r"[^a-z0-9 ]", "", s)  # remove remaining special chars
    s = re.sub(r" +", " ", s)          # collapse multiple spaces
    return s.strip()


def _normalised_returns() -> tuple[tuple[str, str, str, dict], ...]:
    """Pre-computed (norm_name, norm_return_id, norm_alt_name, attrib_dict) 4-tuples.
    Searching against Name, ReturnId, and AltName from Returns.xml.
    Automatically rebuilds whenever _parse_returns() refreshes its cache.
    """
    # If returns cache was refreshed more recently than norm cache, rebuild
    if _norm_cache.loaded_at < _returns_cache.loaded_at:
        _norm_cache._data = None
    cached = _norm_cache.get()
    if cached is not None:
        return cached
    result = tuple(
        (
            _normalise(r.get("Name", "")),
            _normalise(r.get("ReturnId", "")),
            _normalise(r.get("AltName", "")),
            r,
        )
        for r in _parse_returns()
        if r.get("Name", "")
    )
    return _norm_cache.set(result)


def find_matching_reports(user_input: str) -> list[dict]:
    """Multi-strategy, case-insensitive search against Name, ReturnId, and AltName.

    Search priority (returns on first non-empty result):
      1.  Exact ReturnId match
      2.  Exact Name match
      3.  Exact AltName match
      4.  Partial/bidirectional Name match
      5.  Partial/bidirectional AltName match
      6.  Partial/bidirectional ReturnId match
      7.  All-keyword token match against Name
      8.  All-keyword token match against AltName
      9+. Scored any-token fallback (whole-word preferred over substring):
          - whole-word matches score highest; pure substring-only matches score
            lowest and are suppressed when stronger matches exist.
          - Results sorted by score descending.

    All comparisons are case-insensitive (via _normalise) and trim-safe.
    Null/missing XML attributes are handled gracefully.

    Args:
        user_input: Free-text from the user (e.g. 'R091', 'CIMS_RAQ', 'raq quarterly').

    Returns:
        Deduplicated list of matching report attribute dicts from Returns.xml.
        Empty list means no match was found by any strategy.
    """
    needle = _normalise(user_input)
    if not needle:
        return []

    quads = _normalised_returns()  # (norm_name, norm_return_id, norm_alt_name, raw_dict)
    from rapidfuzz import fuzz as _fuzz  # used in stage 9+ ranking bonus and final fuzzy fallback

    def _dedup(lst: list[dict]) -> list[dict]:
        """Deduplicate by (Name, Id) pair while preserving order."""
        seen: set[str] = set()
        out: list[dict] = []
        for r in lst:
            key = r.get("Name", "") + "|" + r.get("Id", "")
            if key not in seen:
                seen.add(key)
                out.append(r)
        return out

    # ── Exact matches ────────────────────────────────────────────────────────
    # 1. Exact ReturnId  (e.g. user types "R091" → matches all reports with ReturnId=R091)
    exact_rid = [r for (_, nrid, _, r) in quads if nrid and nrid == needle]
    if exact_rid:
        return _dedup(exact_rid)

    # 2. Exact Name
    exact_name = [r for (nname, _, _, r) in quads if nname and nname == needle]
    if exact_name:
        return _dedup(exact_name)

    # 3. Exact AltName  (e.g. user types "CIMS_RAQ" → matches the AltName field)
    exact_alt = [r for (_, _, nalt, r) in quads if nalt and nalt == needle]
    if exact_alt:
        return _dedup(exact_alt)

    # ── Partial / bidirectional contains ────────────────────────────────────
    # 4. Partial Name  (needle ⊂ norm_name OR norm_name ⊂ needle)
    partial_name = [
        r for (nname, _, _, r) in quads
        if nname and (needle in nname or nname in needle)
    ]
    if partial_name:
        return _dedup(partial_name)

    # 5. Partial AltName
    partial_alt = [
        r for (_, _, nalt, r) in quads
        if nalt and (needle in nalt or nalt in needle)
    ]
    if partial_alt:
        return _dedup(partial_alt)

    # 6. Partial ReturnId
    partial_rid = [
        r for (_, nrid, _, r) in quads
        if nrid and (needle in nrid or nrid in needle)
    ]
    if partial_rid:
        return _dedup(partial_rid)

    # ── Keyword token matching ───────────────────────────────────────────────
    # Tokens: split on spaces (normalised form uses spaces as separators),
    # keep tokens with at least 2 chars
    tokens = [t for t in needle.split() if len(t) >= 2]
    if tokens:
        # 7. All tokens in Name
        all_name = [r for (nname, _, _, r) in quads if nname and all(t in nname for t in tokens)]
        if all_name:
            return _dedup(all_name)

        # 8. All tokens in AltName
        all_alt = [r for (_, _, nalt, r) in quads if nalt and all(t in nalt for t in tokens)]
        if all_alt:
            return _dedup(all_alt)

        # 9+. Scored any-token fallback
        # Whole-word matches score much higher than pure substring matches.
        # When whole-word matches exist (_WW_THRESHOLD), substring-only hits
        # are suppressed — this eliminates accidental AltName/ReturnId
        # collisions (e.g. "cims" matching ROF via an unrelated AltName).
        # When NO whole-word matches exist at all (e.g. "gold" → "importofgold"),
        # all substring matches are returned unchanged, preserving broad search.
        _WW_THRESHOLD = 40  # minimum score achievable only via ≥1 whole-word token hit
        n_tok = len(tokens)
        scored: list[tuple[int, dict]] = []
        seen_keys: set[str] = set()

        for (nname, nrid, nalt, r) in quads:
            name_words = set(nname.split()) if nname else set()
            alt_words  = set(nalt.split())  if nalt  else set()

            # Whole-word token counts (precise)
            name_ww  = sum(1 for t in tokens if t in name_words)
            alt_ww   = sum(1 for t in tokens if t in alt_words)
            # Substring token counts (broad, lower signal)
            name_sub = sum(1 for t in tokens if nname and t in nname)
            alt_sub  = sum(1 for t in tokens if nalt  and t in nalt)
            rid_sub  = sum(1 for t in tokens if nrid  and t in nrid)

            if not (name_ww or alt_ww or name_sub or alt_sub or rid_sub):
                continue

            score = 0
            # Name scoring: whole-word > all-substring > any-substring
            if   name_ww == n_tok:    score += 80
            elif name_ww > 0:         score += 40
            elif name_sub == n_tok:   score += 30
            elif name_sub > 0:        score += 10
            # AltName scoring (slightly lower priority than Name)
            if   alt_ww == n_tok:     score += 70
            elif alt_ww > 0:          score += 35
            elif alt_sub == n_tok:    score += 25
            elif alt_sub > 0:         score +=  8
            # ReturnId scoring (lowest; useful mainly for ID-style tokens)
            if rid_sub > 0:           score +=  5
            # Fuzzy ranking bonus: improves tie-breaking between structurally
            # similar candidates without overriding structural signal.
            # Capped at +25 (100 // 4) so it never promotes a weak match above
            # a strong one (strong structural scores are ≥ 40).
            fuzzy_bonus = max(
                _fuzz.partial_ratio(needle, nname) if nname else 0,
                _fuzz.partial_ratio(needle, nalt)  if nalt  else 0,
            ) // 4
            score += fuzzy_bonus

            key = r.get("Name", "") + "|" + r.get("Id", "")
            if key not in seen_keys:
                seen_keys.add(key)
                scored.append((score, r))

        if scored:
            scored.sort(key=lambda x: x[0], reverse=True)
            best = scored[0][0]
            if best >= _WW_THRESHOLD:
                # Strong whole-word matches exist — exclude pure-substring noise
                return [r for s, r in scored if s >= _WW_THRESHOLD]
            # No whole-word matches — return all substring matches
            # (preserves broad searches like "gold" → "importofgold")
            return [r for _, r in scored]

    # ── Final fuzzy fallback ──────────────────────────────────────────────────
    # Catches typos that have no substring overlap with any report name:
    # e.g. "phishing" vs report named "Phising", "quaaterly" vs "quarterly".
    # Only executes when ALL prior structural stages returned nothing.
    # Cutoff of 72 avoids spurious weak matches while catching close typos.
    _FUZZY_CUTOFF = 72
    fuzzy_scored: list[tuple[int, dict]] = []
    fuzzy_seen: set[str] = set()
    for (nname, nrid, nalt, r) in quads:
        name_score = _fuzz.partial_ratio(needle, nname) if nname else 0
        alt_score  = _fuzz.partial_ratio(needle, nalt)  if nalt  else 0
        best_fuzz  = max(name_score, alt_score)
        if best_fuzz >= _FUZZY_CUTOFF:
            key = r.get("Name", "") + "|" + r.get("Id", "")
            if key not in fuzzy_seen:
                fuzzy_seen.add(key)
                fuzzy_scored.append((best_fuzz, r))
    if fuzzy_scored:
        fuzzy_scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in fuzzy_scored]

    return []


def fuzzy_report_suggestions(user_input: str, n: int = 5, cutoff: float = 0.35) -> list[str]:
    """Return up to *n* report names whose normalised form is similar to *user_input*.

    Uses rapidfuzz partial_ratio as a last-resort fallback when
    find_matching_reports returns nothing.  Returns original (non-normalised)
    report names suitable for display.

    Args:
        user_input: Raw user-provided text.
        n:          Maximum number of suggestions to return.
        cutoff:     Minimum similarity ratio (0–1).  0.35 is intentionally
                    permissive to surface near-misses.
    """
    from rapidfuzz import fuzz, process as rf_process
    needle = _normalise(user_input)
    if not needle:
        return []
    norm_to_orig = {norm_name: r.get("Name", "") for (norm_name, _, _, r) in _normalised_returns()}
    matches = rf_process.extract(
        needle,
        list(norm_to_orig.keys()),
        scorer=fuzz.partial_ratio,
        limit=n,
        score_cutoff=cutoff * 100,
    )
    return [norm_to_orig[m[0]] for m in matches if norm_to_orig.get(m[0])]


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


def _extract_error_summary_from_xml(error_file_path: str) -> dict:
    """Parse an error XML file and extract up to 5 unique <ErrorMessage> values.

    Returns:
        {"messages": [...]}  — list of unique error strings in document order.
        Falls back to {"messages": ["Detailed error information could not be extracted."]}
        on missing file, invalid XML, parse errors, or empty results.
    """
    import xml.etree.ElementTree as ET

    _FALLBACK = {"messages": ["Detailed error information could not be extracted."]}
    _MAX_MSGS = 5

    if not error_file_path or not os.path.isfile(error_file_path):
        logger.warning(
            "[extract_error_summary] Error XML file not found: %s", error_file_path
        )
        return _FALLBACK

    try:
        tree = ET.parse(error_file_path)
        root = tree.getroot()
    except ET.ParseError as exc:
        logger.warning(
            "[extract_error_summary] Error XML parsing failed: %s — %s", error_file_path, exc
        )
        return _FALLBACK
    except OSError as exc:
        logger.warning(
            "[extract_error_summary] Cannot read error XML: %s — %s", error_file_path, exc
        )
        return _FALLBACK

    messages: list[str] = []
    seen: set[str] = set()
    for el in root.iter("ErrorMessage"):
        msg = (el.text or "").strip()
        if msg and msg not in seen:
            seen.add(msg)
            messages.append(msg)
            if len(messages) >= _MAX_MSGS:
                break

    if not messages:
        logger.warning(
            "[extract_error_summary] No <ErrorMessage> nodes found in: %s", error_file_path
        )
        return _FALLBACK

    logger.info(
        "[extract_error_summary] Extracted %d error message(s) from XML: %s",
        len(messages), error_file_path,
    )
    return {"messages": messages}


def _extract_error_summary_from_html(error_file_path: str) -> dict:
    """Parse a backtrack HTML validation report and return a readable summary.

    Used for 4000-series returns where the error file is a BTDetails.html
    generated by the .NET backtracking mechanism.  Delegates to
    ``parse_backtrack_html_errors`` (which uses stdlib html.parser) to extract
    structured error dicts, then converts them into a list of concise strings
    in the same ``{"messages": [...]}`` format as the XML parser.

    Fallback behaviour mirrors the XML path.
    """
    _FALLBACK = {"messages": ["Detailed error information could not be extracted."]}
    _MAX_MSGS = 5

    logger.info(
        "[extract_error_summary] HTML validation report detected: %s", error_file_path
    )
    logger.info("[extract_error_summary] Using HTML parser")

    errors = parse_backtrack_html_errors(error_file_path)
    if not errors:
        logger.warning(
            "[extract_error_summary] HTML parser returned no errors from: %s", error_file_path
        )
        return _FALLBACK

    logger.info(
        "[extract_error_summary] Extracted %d validation section(s) from HTML: %s",
        len(errors), error_file_path,
    )

    # Convert structured error dicts → concise readable strings.
    # Priority for the human-readable text:
    #   1. "message" field (direct validation message)
    #   2. Compose from errorType + rule + cell when message is absent
    messages: list[str] = []
    seen: set[str] = set()
    for err in errors:
        msg = err.get("message") or err.get("error_message", "")
        if not msg:
            parts = []
            if err.get("errorType"):
                parts.append(err["errorType"].replace("_", " ").title())
            if err.get("rule"):
                parts.append(f"rule: {err['rule']}")
            if err.get("table"):
                parts.append(f"table {err['table']}")
            if err.get("cellCode"):
                parts.append(f"cell {err['cellCode']}")
            actual = err.get("actualValue") or err.get("enteredValue", "")
            if actual:
                parts.append(f"entered: {actual}")
            if err.get("expectedValue"):
                parts.append(f"expected: {err['expectedValue']}")
            msg = " — ".join(parts) if parts else str(err)
        msg = msg.strip()
        if msg and msg not in seen:
            seen.add(msg)
            messages.append(msg)
            if len(messages) >= _MAX_MSGS:
                break

    if not messages:
        return _FALLBACK

    return {"messages": messages}


def extract_error_summary(error_file_path: str) -> dict:
    """Route to the appropriate parser based on the error file extension.

    - ``.html`` → ``_extract_error_summary_from_html`` (BTDetails / backtrack reports)
    - ``.xml``  → ``_extract_error_summary_from_xml``  (standard XBRL error XML)
    - other     → fallback message

    Returns:
        {"messages": [...]}  — list of readable error strings.
    """
    _FALLBACK = {"messages": ["Detailed error information could not be extracted."]}

    if not error_file_path:
        return _FALLBACK

    ext = os.path.splitext(error_file_path)[1].lower()

    logger.info(
        "[extract_error_summary] Extracting error summary from %s: %s",
        ext.upper() if ext else "unknown", error_file_path,
    )

    if ext == ".html":
        return _extract_error_summary_from_html(error_file_path)

    if ext == ".xml":
        return _extract_error_summary_from_xml(error_file_path)

    logger.warning(
        "[extract_error_summary] Unsupported error file type '%s': %s", ext, error_file_path
    )
    return _FALLBACK


def _get_return_id_for_form(form_id: str) -> str:
    """Look up the ReturnId attribute for a given Id (form_id) from Returns.xml."""
    fid = str(form_id).strip()
    for r in _parse_returns():
        if r.get("Id", "").strip() == fid:
            return r.get("ReturnId", "").strip()
    return ""


def _is_4000_series(return_id: str) -> bool:
    """Return True when ReturnId is a numeric value in the 4000–4999 range."""
    try:
        return 4000 <= int(return_id) <= 4999
    except (ValueError, TypeError):
        return False


def parse_backtrack_html_errors(html_path: str) -> list[dict]:
    """Parse a backtrack HTML validation report and return structured errors.

    Extracts rich information from every error row:
        errorType, title, message, rule, cellCode, table, context,
        actualValue, expectedValue, unit, assertionLabel, severity,
        suggestion, variables (list of variable-substitution sub-rows).

    Supports:
    - Section headings h1–h5 / caption → errorType / severity
    - Standard error tables (th header row + td data rows)
    - Variable-substitution tables (header contains "variable"/"var name")
    - <br> within cells → preserved as newlines
    - Malformed / partial HTML → graceful fallback to empty list

    Returns an empty list when the file is missing, unreadable, or contains no
    parseable error rows.
    """
    import html as _html_module
    from html.parser import HTMLParser

    _FALLBACK: list[dict] = []

    if not html_path or not os.path.isfile(html_path):
        logger.warning("[parse_backtrack_html] file not found: %s", html_path)
        return _FALLBACK

    try:
        with open(html_path, "r", encoding="utf-8", errors="replace") as fh:
            raw = fh.read()
    except OSError as exc:
        logger.warning("[parse_backtrack_html] cannot read: %s — %s", html_path, exc)
        return _FALLBACK

    # ── Comprehensive header → canonical key map ──────────────────────────────
    _HEADER_MAP: dict[str, str] = {
        # Error category / type
        "error category":           "errorType",
        "category":                 "errorType",
        "error type":               "errorType",
        "type":                     "errorType",
        # Title / name
        "title":                    "title",
        "error title":              "title",
        "validation name":          "title",
        "name":                     "title",
        # Rule / formula
        "rule":                     "rule",
        "rule name":                "rule",
        "formula":                  "rule",
        "formula expression":       "rule",
        "expression":               "rule",
        "validation rule":          "rule",
        "constraint":               "rule",
        # Message / description
        "error message":            "message",
        "message":                  "message",
        "description":              "message",
        "error description":        "message",
        "validation message":       "message",
        "detail":                   "message",
        "details":                  "message",
        # Table
        "table":                    "table",
        "table name":               "table",
        "sheet":                    "table",
        # Cell code
        "cell code":                "cellCode",
        "cell":                     "cellCode",
        "cell name":                "cellCode",
        "cell reference":           "cellCode",
        "ref":                      "cellCode",
        # Context / period
        "context":                  "context",
        "period":                   "context",
        # Actual / entered value
        "entered value":            "actualValue",
        "value":                    "actualValue",
        "actual value":             "actualValue",
        "actual":                   "actualValue",
        "reported value":           "actualValue",
        # Expected value / data type
        "expected value":           "expectedValue",
        "expected":                 "expectedValue",
        "data type":                "expectedValue",
        "expected value / data type": "expectedValue",
        "type restriction":         "expectedValue",
        # Unit
        "unit":                     "unit",
        # Assertion label
        "assertion label":          "assertionLabel",
        "assertion":                "assertionLabel",
        "label":                    "assertionLabel",
        # Severity
        "severity":                 "severity",
        # Suggestion / fix
        "suggestion":               "suggestion",
        "fix":                      "suggestion",
        "corrective action":        "suggestion",
        "resolution":               "suggestion",
        # Variable substitution columns
        "variable":                 "variableName",
        "variable name":            "variableName",
        "var name":                 "variableName",
        "var":                      "variableName",
        "variable value":           "variableValue",
        "var value":                "variableValue",
        # Serial number — normalised away from output
        "sr. no.":  "_srNo",  "sr no":    "_srNo",  "s. no.":  "_srNo",
        "s.no":     "_srNo",  "no.":      "_srNo",  "#":       "_srNo",
        "sl. no.":  "_srNo",  "sr.no.":   "_srNo",
    }

    def _canonical_key(raw: str) -> str:
        return _HEADER_MAP.get(raw.lower().strip(), raw.lower().strip().replace(" ", "_"))

    def _infer_severity(section: str) -> str:
        s = section.upper()
        if any(k in s for k in ("FORMULA", "SPECIFICATION", "SCHEMA", "ERROR")):
            return "error"
        if any(k in s for k in ("QUALITY", "WARNING", "WARN", "CHECK")):
            return "warning"
        return "error"

    def _generate_suggestion(entry: dict) -> str:
        actual    = entry.get("actualValue", "")
        expected  = entry.get("expectedValue", "")
        err_type  = entry.get("errorType", "")
        rule      = entry.get("rule", "")
        cell      = entry.get("cellCode", "")
        cell_hint = f" in cell {cell}" if cell else ""
        if actual and expected:
            return (
                f"Replace '{actual}' with a valid {expected} value{cell_hint}."
            )
        if "FORMULA" in err_type:
            rule_hint = f" (rule: {rule})" if rule else ""
            return (
                f"Verify source data and formula inputs{rule_hint}{cell_hint}. "
                "Ensure all referenced values are correctly mapped and totals balance."
            )
        if "SPECIFICATION" in err_type or "SCHEMA" in err_type:
            return (
                f"Check the data type and format of the reported value{cell_hint}. "
                "It must conform to the field specification."
            )
        if "QUALITY" in err_type or "CHECK" in err_type:
            return (
                f"Review data quality rules{cell_hint} and ensure "
                "the reported value meets all validation criteria."
            )
        return (
            f"Review and correct the reported value{cell_hint} "
            "according to the applicable validation rule."
        )

    def _is_variable_table(headers: list[str]) -> bool:
        h_lower = {h.lower().strip() for h in headers}
        return bool(
            h_lower & {"variable", "variable name", "var name", "var"}
        )

    def _build_var_entry(headers: list[str], cells: list[str]) -> dict | None:
        if not any(c.strip() for c in cells):
            return None
        entry: dict = {}
        for i, cell in enumerate(cells):
            hdr = headers[i] if i < len(headers) else f"col_{i}"
            key = _canonical_key(hdr)
            val = cell.strip()
            if val and not key.startswith("_"):
                entry[key] = val
        return entry if entry else None

    def _build_entry(section: str, headers: list[str], cells: list[str]) -> dict | None:
        if not any(c.strip() for c in cells):
            return None
        entry: dict = {}
        if section:
            entry["errorType"] = section
            entry["severity"]  = _infer_severity(section)
        for i, cell in enumerate(cells):
            hdr = headers[i] if i < len(headers) else f"col_{i}"
            key = _canonical_key(hdr)
            val = cell.strip()
            if val and not key.startswith("_"):          # drop srNo etc.
                entry[key] = val
        # Require at least one meaningful field beyond errorType / severity
        useful = {k for k in entry if k not in ("errorType", "severity")}
        if not useful:
            return None
        # Ensure severity & suggestion are present
        if "severity" not in entry:
            entry["severity"] = _infer_severity(entry.get("errorType", ""))
        if "suggestion" not in entry:
            entry["suggestion"] = _generate_suggestion(entry)
        return entry

    # ── Streaming HTML parser ─────────────────────────────────────────────────
    class _TableParser(HTMLParser):
        def __init__(self) -> None:
            super().__init__(convert_charrefs=True)   # handles &amp; &#xNN; etc.
            self.errors: list[dict] = []
            self._current_section: str = ""
            self._in_heading  = False
            self._in_table    = False
            self._in_tr       = False
            self._in_cell     = False
            self._is_hdr_row  = False
            self._cell_texts: list[str] = []
            self._headers:    list[str] = []
            self._buf = ""
            self._table_is_var = False
            self._pending_vars: list[dict] = []

        def handle_starttag(self, tag: str, attrs: list) -> None:
            tag = tag.lower()
            if tag in ("h1", "h2", "h3", "h4", "h5", "caption"):
                self._buf = ""
                self._in_heading = True
                self._in_cell    = True
            elif tag == "table":
                self._in_table   = True
                self._headers    = []
                self._table_is_var = False
                self._pending_vars = []
            elif tag == "tr":
                self._in_tr      = True
                self._is_hdr_row = False
                self._cell_texts = []
            elif tag in ("td", "th"):
                self._in_cell    = True
                self._buf        = ""
                if tag == "th":
                    self._is_hdr_row = True
            elif tag == "br" and self._in_cell:
                self._buf += "\n"

        def handle_endtag(self, tag: str) -> None:
            tag = tag.lower()
            if tag in ("h1", "h2", "h3", "h4", "h5", "caption"):
                txt = self._buf.strip().upper()
                if txt:
                    self._current_section = txt
                self._in_heading = False
                self._in_cell    = False
                self._buf        = ""
            elif tag in ("td", "th"):
                self._cell_texts.append(self._buf.strip())
                self._in_cell = False
                self._buf     = ""
            elif tag == "tr":
                self._in_tr = False
                cells = self._cell_texts
                if self._is_hdr_row and cells:
                    self._headers      = [c.strip() for c in cells]
                    self._table_is_var = _is_variable_table(self._headers)
                elif cells and any(cells):
                    if self._table_is_var:
                        ve = _build_var_entry(self._headers, cells)
                        if ve:
                            self._pending_vars.append(ve)
                    else:
                        entry = _build_entry(
                            self._current_section, self._headers, cells
                        )
                        if entry:
                            self.errors.append(entry)
                self._cell_texts = []
            elif tag == "table":
                self._in_table = False
                if self._pending_vars and self.errors:
                    if "variables" not in self.errors[-1]:
                        self.errors[-1]["variables"] = []
                    self.errors[-1]["variables"].extend(self._pending_vars)
                self._table_is_var = False
                self._pending_vars = []

        def handle_data(self, data: str) -> None:
            if self._in_cell:
                self._buf += data

    parser = _TableParser()
    try:
        parser.feed(raw)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[parse_backtrack_html] parse error: %s — %s", html_path, exc)
        return _FALLBACK

    # Post-process: guarantee every entry has severity + suggestion
    for err in parser.errors:
        if "severity" not in err:
            err["severity"] = _infer_severity(err.get("errorType", ""))
        if "suggestion" not in err:
            err["suggestion"] = _generate_suggestion(err)

    errors = parser.errors
    logger.info(
        "[parse_backtrack_html] extracted %d error(s) from: %s", len(errors), html_path
    )
    return errors


# ── Last-resort fallback — used ONLY when Ollama is completely unreachable ───
def _build_fallback_business_explanation(err: dict) -> str:
    """Minimal last-resort explanation used ONLY when Ollama is completely unreachable.

    No regex, no rule-based logic, no template sentences.
    Surfaces the raw validation message so the user sees *something* rather
    than nothing.  All normal explanation paths go through the LLM.
    """
    cell    = err.get("cellCode") or err.get("cell", "")
    cell_str = f"Cell {cell}" if cell else "A reported field"
    message = (
        err.get("message") or err.get("col_0") or err.get("title") or ""
    ).strip()
    if message:
        return f"{cell_str} failed validation: {message[:200].rstrip('.')}."
    return (
        f"{cell_str} did not pass validation. "
        "Please review the reported value and correct it before resubmitting."
    )


def _normalize_error_for_llm(err: dict) -> dict:
    """Map the raw parsed HTML error dict into a clean, rich payload for the LLM.

    The HTML parser produces field names that depend on the column headings in
    the BTDetails.html file (e.g. ``col_0``, ``entered_data(s)``, ``db_tablename``).
    This function normalises those into a consistent set of human-readable keys
    that give the LLM maximum context.

    Only non-empty values are included in the returned dict.
    """
    normalized: dict = {}

    def _set(key: str, *sources: str) -> None:
        for src in sources:
            val = err.get(src, "")
            if isinstance(val, str):
                val = val.strip()
            if val:
                normalized[key] = val
                return

    _set("cell",          "cellCode",      "cell")
    _set("message",       "message",       "col_0",          "title")
    _set("entered_value", "entered_data(s)", "instance_data(s)", "actualValue", "enteredValue")
    _set("expected_value","expectedValue")
    _set("table",         "db_tablename",  "table")
    _set("row_label",     "row_label(s)",  "row_label")
    _set("unit",          "unit")
    _set("decimal",       "decimal")
    _set("context",       "context")
    _set("severity",      "severity")
    _set("rule",          "rule")

    # Variable substitutions as compact facts dict
    if err.get("variables"):
        facts = {
            v.get("variableName", f"V{i}"): v.get("variableValue", "")
            for i, v in enumerate(err["variables"])
            if v.get("variableName")
        }
        if facts:
            normalized["facts"] = facts

    return normalized


def explain_validation_errors(errors: list[dict]) -> list[dict]:
    """Enrich parsed XBRL validation errors with a single LLM-generated explanation.

    Calls the configured Ollama model once with all errors batched.  For each
    error the LLM returns one clean ``explanation`` string that:
      - names the entered value
      - explains why it is invalid for that field/type
      - states what is expected
      - describes the impact on report submission

    No regex, no template sentences, no rule-based logic — the explanation is
    purely LLM-generated.  Falls back to ``_build_fallback_business_explanation``
    (minimal surface of raw validation text) only when Ollama is completely
    unreachable.

    The ``table_info`` dict (DB table, row label, context, cell code) is always
    populated from the parser output regardless of LLM success/failure.
    """
    import json as _json
    import httpx as _httpx

    if not errors:
        return errors

    ollama_base = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    model       = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:latest")
    timeout     = float(os.getenv("OLLAMA_TIMEOUT", "180"))
    keep_alive  = os.getenv("OLLAMA_KEEP_ALIVE", "30m")

    logger.info("[STATUS_FLOW] Starting LLM enrichment")
    logger.info("[STATUS_FLOW] Parsed validation errors=%d", len(errors))

    # ── Normalise errors for the LLM ─────────────────────────────────────────
    payload_items: list[dict] = [_normalize_error_for_llm(e) for e in errors]

    for i, item in enumerate(payload_items):
        if not {k for k in item if k not in ("severity", "cell")}:
            logger.warning(
                "[STATUS_FLOW] Error index=%d has no meaningful fields for LLM", i
            )

    errors_json = _json.dumps(payload_items, indent=2, ensure_ascii=False)
    n = len(errors)

    prompt = (
        "You are an enterprise regulatory reporting expert helping business users "
        "understand why their XBRL report submission failed validation.\n\n"
        f"The following {n} validation error(s) caused the submission to fail.\n\n"
        "Each error object may contain:\n"
        "  - cell:           the affected cell reference (e.g. R0020_10)\n"
        "  - message:        the raw validation message from the validator\n"
        "  - entered_value:  the value the user submitted\n"
        "  - expected_value / decimal: the required data type or format\n"
        "  - table:          the report table name\n"
        "  - row_label:      the business description of the row\n"
        "  - rule:           the validation rule name\n"
        "  - unit:           reporting currency or unit\n"
        "  - context:        reporting period/context\n\n"
        f"{errors_json}\n\n"
        "For EACH error write ONE plain-English explanation that:\n"
        "  1. States what value was entered (quote it exactly if available)\n"
        "  2. Explains why that value is wrong for this specific field or type\n"
        "  3. States what type or value IS expected\n"
        "  4. Describes the impact on the report submission\n\n"
        "RULES — follow strictly:\n"
        "  - Always mention the cell code when present\n"
        "  - Always quote the entered value when present\n"
        "  - Write in natural, professional business language\n"
        "  - NEVER use XML, XBRL, schema, or technical validator terminology\n"
        "  - NEVER generate generic phrases like 'invalid value', "
        "'validation failed', 'expected format', or 'datatype mismatch'\n"
        "  - NEVER produce duplicate or template-sounding sentences\n"
        "  - ONE explanation per error — no sub-sections, no bullet points\n"
        "  - Max 70 words per explanation\n\n"
        "GOOD EXAMPLE OUTPUT:\n"
        "\"The value 'abc' was entered in cell R0020_10, but this field is "
        "reserved for EUR monetary amounts. Because a text string was provided "
        "instead of a numeric figure, the report failed schema validation and "
        "cannot be submitted until a valid decimal amount is entered.\"\n\n"
        "Respond ONLY with a valid JSON array — no markdown, no extra text.\n"
        f"The array must contain exactly {n} object(s) in the same order as input.\n\n"
        "[\n"
        "  {\n"
        '    "cell": "<cell reference or empty string>",\n'
        '    "explanation": "<single plain-English explanation, max 70 words>"\n'
        "  }\n"
        "]\n\n"
        "Strictly return valid JSON only. No trailing commas. No comments."
    )

    logger.debug("[STATUS_FLOW] LLM prompt=\n%s", prompt)
    logger.info("[STATUS_FLOW] Sending %d error(s) to LLM: model=%s", n, model)

    payload = {
        "model":      model,
        "messages":   [
            {
                "role":    "system",
                "content": (
                    "You are an enterprise XBRL validation assistant. "
                    "Always respond with a valid JSON array only — "
                    "no markdown, no extra text before or after the JSON."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "stream":     False,
        "format":     "json",
        "keep_alive": keep_alive,
        "options":    {"temperature": 0.05, "num_predict": 1024},
    }

    start = time.perf_counter()

    _BAD_RESPONSES = {
        "no error information provided",
        "no information provided",
        "no context provided",
        "n/a",
        "none",
    }

    try:
        with _httpx.Client(timeout=timeout) as client:
            resp = client.post(f"{ollama_base}/api/chat", json=payload)
            resp.raise_for_status()

        raw_response: str = resp.json()["message"]["content"].strip()
        elapsed = time.perf_counter() - start
        logger.debug("[STATUS_FLOW] LLM raw response=%s", raw_response)
        logger.info("[STATUS_FLOW] LLM enrichment completed in %.3fs", elapsed)

        # ── Robust JSON extraction ────────────────────────────────────────────
        cleaned = raw_response
        if "```" in cleaned:
            cleaned = "\n".join(
                line for line in cleaned.splitlines()
                if not line.strip().startswith("```")
            ).strip()

        start_arr = cleaned.find("[")
        start_obj = cleaned.find("{")
        if start_arr != -1 and (start_obj == -1 or start_arr < start_obj):
            end_idx = cleaned.rfind("]")
            if end_idx > start_arr:
                cleaned = cleaned[start_arr : end_idx + 1]
        elif start_obj != -1:
            end_idx = cleaned.rfind("}")
            if end_idx > start_obj:
                cleaned = cleaned[start_obj : end_idx + 1]

        explained_raw = _json.loads(cleaned)

        if isinstance(explained_raw, dict):
            logger.warning("[STATUS_FLOW] LLM returned object instead of array — wrapping")
            explained_raw = [explained_raw]

        if not isinstance(explained_raw, list):
            raise ValueError(f"LLM returned {type(explained_raw).__name__}, expected list")

        explained: list[dict] = explained_raw
        logger.info("[STATUS_FLOW] Parsed LLM responses=%d", len(explained))

        # ── Reconcile count ───────────────────────────────────────────────────
        while len(explained) < n:
            missing_idx = len(explained)
            logger.warning("[STATUS_FLOW] Auto-filling missing explanation index=%d", missing_idx)
            explained.append({
                "cell":        errors[missing_idx].get("cellCode") or errors[missing_idx].get("cell", ""),
                "explanation": _build_fallback_business_explanation(errors[missing_idx]),
            })
        if len(explained) > n:
            explained = explained[:n]

        # ── Merge back into original error dicts ──────────────────────────────
        enriched: list[dict] = []
        for i, err in enumerate(errors):
            merged    = dict(err)
            llm_item  = explained[i] if i < len(explained) else {}

            # Extract the single explanation — accept common LLM key variations
            explanation = (
                str(
                    llm_item.get("explanation")
                    or llm_item.get("business_explanation")  # old key compat
                    or llm_item.get("business_explanature")  # known phi3 typo
                    or ""
                ).strip()
            )

            # Reject empty, too-short, or known boilerplate non-answers
            if not explanation or len(explanation) < 10 or explanation.lower().rstrip(".") in _BAD_RESPONSES:
                logger.warning(
                    "[STATUS_FLOW] Bad LLM explanation at index=%d ('%s') — using fallback",
                    i, explanation[:60],
                )
                explanation = _build_fallback_business_explanation(err)

            # Normalise cell reference
            cell = (
                str(llm_item.get("cell", "")).strip()
                or err.get("cellCode", "")
                or err.get("cell", "")
            )

            merged["explanation"] = explanation
            if cell:
                merged["cell"] = cell

            # ── table_info: 4 metadata fields shown as a summary table ────────
            merged["table_info"] = {
                "db_table_name": (
                    err.get("db_tablename") or err.get("table") or ""
                ).strip(),
                "row_label": (
                    err.get("row_label")
                    or err.get("row_label(s)")
                    or err.get("row_label(s) ")
                    or ""
                ).strip(),
                "context":   err.get("context", "").strip(),
                "cell_code": (
                    cell or err.get("cellCode", "") or err.get("cell", "")
                ).strip(),
            }

            enriched.append(merged)

        logger.info("[STATUS_FLOW] Final error_details populated=%d", len(enriched))
        return enriched

    except Exception as exc:  # noqa: BLE001
        elapsed = time.perf_counter() - start
        logger.warning("[STATUS_FLOW] LLM explanation failed: %s (%.3fs)", exc, elapsed)

        # ── Minimal fallback — surfaces raw validation text, no logic ─────────
        fallback: list[dict] = []
        for err in errors:
            merged = dict(err)
            cell   = err.get("cellCode", "") or err.get("cell", "")
            merged["explanation"] = _build_fallback_business_explanation(err)
            merged.setdefault("cell", cell)
            merged["table_info"] = {
                "db_table_name": (err.get("db_tablename") or err.get("table") or "").strip(),
                "row_label": (
                    err.get("row_label")
                    or err.get("row_label(s)")
                    or err.get("row_label(s) ")
                    or ""
                ).strip(),
                "context":   err.get("context", "").strip(),
                "cell_code": cell.strip(),
            }
            fallback.append(merged)

        logger.info("[STATUS_FLOW] Final error_details populated=%d (fallback)", len(fallback))
        return fallback


def _enrich_error_info(code: int, dl: dict, form_id: str = "") -> tuple[list[str], list[dict]]:
    """Return (human-readable messages, enriched error details) for a failed instance.

    Routing is based on **file extension**, not the ReturnId range:

    ``.html`` → parse_backtrack_html_errors → explain_validation_errors (LLM)
                → returns (bubble_msgs, enriched_error_dicts)

    ``.xml``  → extract_error_summary_from_xml → raw text messages
                → returns (messages, [])

    other/missing → extract_error_summary fallback → returns (messages, [])

    Returns ([], []) when the status is not in _FAILED_STATUSES or no error
    file path is present.
    """
    import json as _json

    if code not in _FAILED_STATUSES:
        return [], []

    path = dl.get("error_file_path", "")
    if not path:
        return [], []

    logger.info("[STATUS_FLOW] Error file detected: path=%r", path)

    ext = os.path.splitext(path)[1].lower()

    # ── HTML path: parse → LLM enrichment ───────────────────────────────────
    if ext == ".html" and os.path.isfile(path):
        _t_parse = time.perf_counter()
        errors = parse_backtrack_html_errors(path)
        _parse_elapsed = time.perf_counter() - _t_parse

        logger.info("[STATUS_FLOW] HTML parsing duration=%.3fs", _parse_elapsed)
        logger.info(
            "[STATUS_FLOW] Validation sections extracted: count=%d", len(errors)
        )
        logger.debug(
            "[VALIDATION_PARSED] %s",
            _json.dumps(errors, indent=2, ensure_ascii=False),
        )

        if errors:
            error_details = explain_validation_errors(errors)

            logger.info(
                "[STATUS_FLOW] Final error_details populated=%d", len(error_details)
            )

            # Build bubble messages from enriched results
            # Use the single LLM-generated explanation; fall back to raw message/title
            _BAD_BUBBLE = {
                "no error information provided",
                "no information provided",
                "no context provided",
                "n/a",
                "none",
            }
            bubble_msgs: list[str] = []
            seen: set[str] = set()
            for err in error_details:
                msg = (
                    err.get("explanation")
                    or err.get("message")
                    or err.get("col_0")
                    or err.get("title")
                    or ""
                ).strip()
                # Filter out useless LLM non-answers
                if msg and msg.lower().rstrip(".") not in _BAD_BUBBLE and msg not in seen:
                    seen.add(msg)
                    bubble_msgs.append(msg)
                    if len(bubble_msgs) >= 5:
                        break

            return (
                bubble_msgs or ["Validation failed — see Technical Details below."],
                error_details,
            )

        logger.warning(
            "[STATUS_FLOW] HTML parse yielded no errors, falling back: %s", path
        )

    # ── XML / fallback path ───────────────────────────────────────────────────
    messages = extract_error_summary(path).get("messages", [])
    return messages, []


def _enrich_with_error_messages(code: int, dl: dict) -> list[str]:
    """Return extracted error messages when status is Failed and error file exists.

    Kept for backward compatibility.  New callers should use _enrich_error_info
    so that error_details (structured technical errors) are also available.

    Args:
        code: numeric status code from the instance row.
        dl:   download-info dict returned by _get_download_info (may contain
              ``error_file_path`` when the error file was found on disk).

    Returns:
        List of error message strings (empty list when not applicable).
    """
    if code not in _FAILED_STATUSES:
        return []
    path = dl.get("error_file_path", "")
    if not path:
        return []
    return extract_error_summary(path).get("messages", [])


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
            return {
                "download_url":    url,
                "download_label":  "Download Error File",
                "status_note":     "",
                "error_file_path": full_path,
            }
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
    error_messages, error_details = _enrich_error_info(code, dl, form_id)
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
        "error_messages": error_messages,
        "error_details":  error_details,
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
    logger.info(
        "[STATUS_FLOW] Instance found: status=%r reporting_date=%r dtc=%r",
        map_status(code), rep_date, current_dtc,
    )

    # All instances except the one we're about to display
    all_instances   = get_available_instances(form_id)  # already sorted DTC desc
    other_instances = [i for i in all_instances if i["dtc"] != current_dtc]

    import json as _json_bs
    _t_pipeline = time.monotonic()
    error_messages, error_details = _enrich_error_info(code, dl, form_id)
    _pipeline_elapsed = time.monotonic() - _t_pipeline
    logger.info(
        "[STATUS_FLOW] Total error-enrichment pipeline duration=%.3fs "
        "error_messages=%d error_details=%d",
        _pipeline_elapsed, len(error_messages), len(error_details),
    )

    if other_instances:
        response_payload = {
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
            "error_messages":  error_messages,
            "error_details":   error_details,
        }
        logger.debug("[STATUS_RESPONSE] %s", _json_bs.dumps(response_payload, indent=2, ensure_ascii=False))
        return response_payload

    response_payload = {
        "type":           "final",
        "report_name":    ret_name,
        "reporting_date": rep_date,
        "dtc":            current_dtc,
        "status":         map_status(code),
        "status_code":    code,
        "download_url":   dl["download_url"],
        "download_label": dl["download_label"],
        "status_note":    dl["status_note"],
        "error_messages": error_messages,
        "error_details":  error_details,
    }
    logger.debug("[STATUS_RESPONSE] %s", _json_bs.dumps(response_payload, indent=2, ensure_ascii=False))
    return response_payload


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
                    f"{opts_text}"
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
                f"{opts_text}"
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
    logger.info(
        "[STATUS_FLOW] Report matched: report=%r form_id=%r",
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
            "type":     "error",
            "message":  f"Report '{ret_name}' exists but no instances have been generated yet.",
            "_form_id": form_id,  # used by auth post-filter to deny unauthorised users
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
    error_messages, error_details = _enrich_error_info(code, dl, form_id)
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
        "error_messages": error_messages,
        "error_details":  error_details,
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
            "type":     "error",
            "message":  f"Report '{ret_name}' exists but no instances have been generated yet.",
            "_form_id": form_id,  # used by auth post-filter to deny unauthorised users
        }

    return _build_status_result(form_id, ret_name, instances)


def get_form_id_by_name(report_name: str) -> str | None:
    """Return the Id (Report ID / FormId) for a report, matched by Name, AltName, or ReturnId.

    Matching is case-insensitive.  Returns `None` if the report is not
    found in Returns.xml so the caller can handle the missing-report case.
    Used by the comparison flow: report name -> Report ID -> instance folder.
    """
    name_clean = report_name.strip().lower()
    returns = _parse_returns()
    match = (
        next((r for r in returns if r.get("Name", "").strip().lower()     == name_clean), None)
        or next((r for r in returns if r.get("AltName", "").strip().lower()  == name_clean), None)
        or next((r for r in returns if r.get("ReturnId", "").strip().lower() == name_clean), None)
    )
    return match.get("Id", "").strip() if match else None