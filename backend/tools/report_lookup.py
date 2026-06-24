import logging
import os
import re
import time
from datetime import datetime


logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# SHARED HELPERS  (NEW — from improved file)
# ─────────────────────────────────────────────────────────────────────────────

def _camel_to_words(name: str) -> str:
    """CamelCase → 'Camel Case' (used in formula variable labels)."""
    s = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
    s = re.sub(r'([A-Za-z])(\d)', r'\1 \2', s)
    s = re.sub(r'(\d)([A-Za-z])', r'\1 \2', s)
    return s.strip()


def _decompose_context(ctx: str) -> dict:
    """Decompose an iDeal context identifier into human-readable parts.

    Handles two forms:
      fromto_YYYYMMDD_YYYYMMDD_Member1_Member2_OOOOOOOOx
      asof_YYYYMMDD_...

    Returns dict with keys: raw, period_from, period_to, members (list),
    is_duplicate (True when OOOOO suffix present), type ('period'|'instant'|'unknown')
    """
    result: dict = {"raw": ctx, "members": [], "is_duplicate": False, "type": "unknown"}
    if not ctx:
        return result

    result["is_duplicate"] = bool(re.search(r'_OOOOO+\w*$', ctx))

    if ctx.startswith("fromto_"):
        result["type"] = "period"
        rest = ctx[len("fromto_"):]
        parts = rest.split("_", 2)
        if len(parts) >= 2:
            try:
                from datetime import date as _dt
                def _fmt(s: str) -> str:
                    return _dt(int(s[:4]), int(s[4:6]), int(s[6:8])).strftime("%d-%b-%Y")
                result["period_from"] = _fmt(parts[0])
                result["period_to"]   = _fmt(parts[1])
            except (ValueError, IndexError):
                result["period_from"] = parts[0]
                result["period_to"]   = parts[1] if len(parts) > 1 else ""
        if len(parts) >= 3:
            remainder = re.sub(r'_OOOOO+\w*$', '', parts[2])
            result["members"] = [m for m in remainder.split("_") if m]
    elif ctx.startswith("asof_"):
        result["type"] = "instant"
        rest = ctx[len("asof_"):]
        parts = rest.split("_", 1)
        if parts:
            try:
                from datetime import date as _dt
                s = parts[0]
                result["instant_date"] = _dt(int(s[:4]), int(s[4:6]), int(s[6:8])).strftime("%d-%b-%Y")
            except (ValueError, IndexError):
                result["instant_date"] = parts[0]
        if len(parts) > 1:
            remainder = re.sub(r'_OOOOO+\w*$', '', parts[1])
            result["members"] = [m for m in remainder.split("_") if m and not re.match(r'^[A-Z0-9]{8,}$', m)]

    return result


def _context_label(ctx: str) -> str:
    """Return a short human-readable label for a context id."""
    d = _decompose_context(ctx)
    parts = []
    if d.get("period_from") and d.get("period_to"):
        parts.append(f"{d['period_from']} to {d['period_to']}")
    elif d.get("instant_date"):
        parts.append(d["instant_date"])
    if d.get("members"):
        clean = [re.sub(r'Member$', '', m) for m in d["members"]]
        parts.append("[" + ", ".join(clean) + "]")
    if d.get("is_duplicate"):
        parts.append("(duplicate context)")
    return " ".join(parts) if parts else ctx


def _to_iso_date(date_str: str) -> str:
    """Convert DD-MM-YYYY to YYYY-MM-DD hint, or return example if unparseable."""
    m = re.match(r'^(\d{2})[.\-/](\d{2})[.\-/](\d{4})$', (date_str or "").strip())
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    return "YYYY-MM-DD"


# ─────────────────────────────────────────────────────────────────────────────
# IMPORTS & CONFIG  (from original file 1)
# ─────────────────────────────────────────────────────────────────────────────

from backend.config import (
    RETURNS_XML_PATH      as _RETURNS_FILE,
    INSTANCE_LOG_XML_PATH as _INSTANCE_FILE,
    INSTANCE_BASE_DIR     as _INSTANCE_BASE_DIR,
    RENDER_BASE_DIR       as _RENDER_BASE_DIR,
)

from backend.tools.xml_loader import load_xml_tree

_STATUS_LABELS: dict[int, str] = {
    11: "Success",
    3:  "Failed",
    5:  "Failed",
    8:  "Failed",
    10: "Failed",
    13: "Failed",
    4:  "In Progress",
    6:  "In Progress",
    9:  "Approved",
    12: "Rejected",
    0:  "Not Started",
}

_FAILED_STATUSES:  frozenset[int] = frozenset({3, 5, 8, 10, 13})
_SUCCESS_STATUSES: frozenset[int] = frozenset({9, 11})

_returns_ttl   = float(os.getenv("RETURNS_TTL_SEC",   "3600"))
_instances_ttl = float(os.getenv("INSTANCES_TTL_SEC", "120"))


class _TTLCache:
    __slots__ = ("_ttl", "_data", "_ts", "_file_path", "_file_mtime")

    def __init__(self, ttl: float, file_path: str = "") -> None:
        self._ttl        = ttl
        self._data       = None
        self._ts         = 0.0
        self._file_path  = file_path
        self._file_mtime = 0.0

    @property
    def loaded_at(self) -> float:
        return self._ts

    def _file_changed(self) -> bool:
        """Return True if the tracked file has been modified since last cache load."""
        if not self._file_path or self._data is None:
            return False
        try:
            return os.path.getmtime(self._file_path) != self._file_mtime
        except OSError:
            return False

    def get(self):
        if self._data is None:
            return None
        if self._file_changed():
            logger.info(
                "[cache] %s changed on disk — invalidating cache",
                os.path.basename(self._file_path),
            )
            self._data = None
            return None
        if (time.monotonic() - self._ts) >= self._ttl:
            return None
        return self._data

    def set(self, data, *, cache_empty: bool = True):
        if not cache_empty and not data:
            return data
        self._data = data
        self._ts   = time.monotonic()
        if self._file_path:
            try:
                self._file_mtime = os.path.getmtime(self._file_path)
            except OSError:
                self._file_mtime = 0.0
        return data


_returns_cache   = _TTLCache(ttl=_returns_ttl,   file_path=_RETURNS_FILE)
_instances_cache = _TTLCache(ttl=_instances_ttl,  file_path=_INSTANCE_FILE)
_norm_cache      = _TTLCache(ttl=_returns_ttl,    file_path=_RETURNS_FILE)


def _parse_returns() -> tuple[dict, ...]:
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
    cached = _instances_cache.get()
    if cached is not None:
        return cached
    logger.debug("[report_lookup] _parse_instances: loading from %s", _INSTANCE_FILE)
    root = load_xml_tree(_INSTANCE_FILE, "XML_InstanceLog.xml")
    if root is None:
        logger.error(
            "[report_lookup] _parse_instances: XML_InstanceLog.xml could not be loaded. Path: %s",
            _INSTANCE_FILE,
        )
        return ()
    rows = [el.attrib for el in root.findall("Row")]
    result = tuple(rows)
    if not result:
        logger.warning(
            "[report_lookup] _parse_instances: 0 <Row> elements. Path: %s", _INSTANCE_FILE
        )
        return _instances_cache.set(result, cache_empty=False)
    logger.info(
        "[report_lookup] _parse_instances: loaded %d instance(s) (cache refreshed)", len(rows)
    )
    return _instances_cache.set(result)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1: DIMENSIONAL ERROR PARSER + EXPLAINER  (IMPROVED)
# ══════════════════════════════════════════════════════════════════════════════

def _read_dimension_badge_from_html(html: str) -> int:
    """Return the integer badge count from the DIMENSION panel, or 0."""
    m = re.search(
        r'id=["\']DIMENSIONErrorNum["\'][^>]*>\s*(\d+)\s*<',
        html, re.IGNORECASE,
    )
    if m:
        return int(m.group(1))
    m = re.search(
        r'assertionLabel[^>]*>\s*DIMENSION\s*</div>'
        r'.*?class=["\'][^"\']*badge[^"\']*["\'][^>]*>\s*(\d+)\s*<',
        html, re.DOTALL | re.IGNORECASE,
    )
    if m:
        return int(m.group(1))
    return 0


def _extract_dimension_panel_html(html: str) -> str:
    """Return the innerHTML of the DIMENSION panel body, or '' if absent/empty."""
    m = re.search(
        r'id=["\']DIMENSIONErrorContent["\'][^>]*>(.*?)</div>',
        html, re.DOTALL | re.IGNORECASE,
    )
    if m:
        body = m.group(1).strip()
        if body and body not in ('-', ''):
            return body
    m2 = re.search(
        r'id=["\']dimentionError["\'][^>]*>(.*?)</div>\s*</div>\s*</div>',
        html, re.DOTALL | re.IGNORECASE,
    )
    if m2:
        inner = re.search(
            r'class=["\'][^"\']*panel-body[^"\']*["\'][^>]*>(.*)',
            m2.group(1), re.DOTALL | re.IGNORECASE,
        )
        content = (inner.group(1) if inner else m2.group(1)).strip()
        if content and content not in ('-', ''):
            return content
    return ''


def _parse_dimension_panel_direct_msg(panel_html: str) -> list[dict]:
    """Parse directMsg <td> rows from the DIMENSION panel body.

    Handles two sub-formats within the DIMENSION panel:
      A. xbrldie entries: "3.1.1 [xbrldie:PrimaryItemDimensionallyInvalidError] : ...
            name = X value = Y context = Z unit = W decimal = D precision ="
      B. IllegalTypedDimensionContentError: includes "dimension = DateAxis" attr
      C. Legacy "Parameter with name = X" (FORMULA panel spillover — guarded upstream)

    For each entry extracts: error_class, section_ref, concept, value, context,
    context_label, unit, decimal, dimension, typed_dim_value, error_code,
    line_no, col_no, is_duplicate_context, raw_message.
    """
    import re as _re

    entries: list[dict] = []
    tag_re  = _re.compile(r'<[^>]+>')
    nbsp_re = _re.compile(r'&nbsp;|&#160;', _re.IGNORECASE)

    def _strip_tags(s: str) -> str:
        s = nbsp_re.sub(' ', s)
        s = tag_re.sub(' ', s)
        return _re.sub(r'\s+', ' ', s).strip()

    direct_msg_re = _re.compile(
        r'<td[^>]+class="[^"]*directMsg[^"]*"[^>]*>(.*?)</td>',
        _re.DOTALL | _re.IGNORECASE,
    )
    details_re = _re.compile(
        r'<span[^>]+class="[^"]*msgDetails[^"]*"[^>]*>(.*?)</span>',
        _re.DOTALL | _re.IGNORECASE,
    )

    # Attr pattern: matches "name = X" "value = Y" "context = Z" etc.
    attr_re = _re.compile(
        r'\b(name|value|context|unit|decimal|precision|dimension|typeDomainRefSchema|typeDomainRefInstance)\s*=\s*(\S+)',
        _re.IGNORECASE,
    )

    for dm_m in direct_msg_re.finditer(panel_html):
        cell_html = dm_m.group(1)

        details_m   = details_re.search(cell_html)
        details_txt = _strip_tags(details_m.group(1)) if details_m else ""
        main_html   = details_re.sub('', cell_html)
        main_text   = _strip_tags(main_html).strip()

        if not main_text:
            continue

        # ── Extract error class from [xbrldie:XxxError] or [ErrorCode] ──────
        error_class = ""
        class_m = _re.search(r'\[([^\]]+)\]', main_text)
        if class_m:
            error_class = class_m.group(1).strip()

        # ── Extract section reference (e.g. "3.1.1", "3.1.4.4.3") ──────────
        section_ref = ""
        sec_m = _re.search(r'^([\d]+(?:\.[\d]+)+)\s*\[', main_text.strip())
        if sec_m:
            section_ref = sec_m.group(1)

        # ── Extract all key=value attributes ─────────────────────────────────
        attrs = {}
        for k, v in attr_re.findall(main_text):
            attrs[k.lower()] = v.strip().rstrip(',')

        # ── Concept: prefer attr "name", fall back to prose "concept 'X'" ───
        concept = attrs.get("name", "")
        if not concept:
            prose_m = _re.search(r"concept\s+'([^']+)'", main_text)
            if prose_m:
                concept = prose_m.group(1)

        value   = attrs.get("value", "")
        context = attrs.get("context", "")

        # ── Dimension (for IllegalTypedDimensionContentError) ─────────────────
        dimension = attrs.get("dimension", "")
        if not dimension:
            tdim_m = _re.search(r"typed dimension\s+'([^']+)'", main_text)
            if tdim_m:
                dimension = tdim_m.group(1)

        # ── Typed dimension invalid value ─────────────────────────────────────
        typed_dim_value = ""
        if "IllegalTypedDimension" in error_class:
            tv_m = _re.search(r"Value\s+'([^']+)'\s+provided", main_text)
            if tv_m:
                typed_dim_value = tv_m.group(1)

        # ── Parse msgDetails span ─────────────────────────────────────────────
        error_code = line_no = col_no = filename = ""
        if details_txt:
            ec_m   = _re.search(r'(?:Error|Warning)\s+Code\s*:\s*(\S+)', details_txt, _re.IGNORECASE)
            fn_m   = _re.search(r'FileName\s*:\s*([^\s]+\.xml)', details_txt, _re.IGNORECASE)
            line_m = _re.search(r'LineNo\s*:\s*(\d+)', details_txt, _re.IGNORECASE)
            col_m  = _re.search(r'ColumnNo\s*:\s*(\d+)', details_txt, _re.IGNORECASE)
            if ec_m:   error_code = ec_m.group(1)
            if fn_m:   filename   = fn_m.group(1)
            if line_m: line_no    = line_m.group(1)
            if col_m:  col_no     = col_m.group(1)

        # ── Build prose description ───────────────────────────────────────────
        prose_only = _re.split(r'\n\s*name\s*=|\s{4,}name\s*=', main_text, maxsplit=1)[0].strip()
        raw_message = _re.sub(r'^[\d\.]+\s*\[[^\]]*\]\s*:\s*', '', prose_only).strip()

        ctx_label  = _context_label(context) if context else ""
        is_dup_ctx = bool(context and _re.search(r'_OOOOO+\w*$', context))

        entry = {
            "error_class":          error_class,
            "section_ref":          section_ref,
            "concept":              concept,
            "value":                value,
            "context":              context,
            "context_label":        ctx_label,
            "is_duplicate_context": is_dup_ctx,
            "unit":                 attrs.get("unit", ""),
            "decimal":              attrs.get("decimal", ""),
            "precision":            attrs.get("precision", ""),
            "dimension":            dimension,
            "typed_dim_value":      typed_dim_value,
            "error_code":           error_code,
            "filename":             filename,
            "line_no":              line_no,
            "col_no":               col_no,
            "raw_message":          raw_message,
        }
        entries.append(entry)

    return entries


def parse_dimensional_html_errors(html_path: str) -> list[dict]:
    """Parse dimensional validity errors — panel-aware, full-field extraction.

    KEY FIX: Only parses content from the DIMENSION panel.
    If the DIMENSION badge is 0, returns [] immediately without touching
    any other panel content (e.g. FORMULA, TABLE), preventing false positives.

    Returns list of fully-populated dicts.
    """
    import re as _re
    from html.parser import HTMLParser

    _FALLBACK: list[dict] = []

    if not html_path or not os.path.isfile(html_path):
        logger.warning("[parse_dimensional_html] file not found: %s", html_path)
        return _FALLBACK

    try:
        with open(html_path, "r", encoding="utf-8", errors="replace") as fh:
            raw = fh.read()
    except OSError as exc:
        logger.warning("[parse_dimensional_html] cannot read: %s — %s", html_path, exc)
        return _FALLBACK

    badge_count = _read_dimension_badge_from_html(raw)
    logger.info("[parse_dimensional_html] DIMENSION badge=%d path=%s", badge_count, html_path)

    if badge_count == 0:
        has_xbrldie = "xbrldie" in raw.lower() or "DimensionallyInvalid" in raw
        if not has_xbrldie:
            logger.info("[parse_dimensional_html] badge=0, no xbrldie markers — returning []")
            return _FALLBACK
        panel_html = ""
        use_panel  = False
    else:
        panel_html = _extract_dimension_panel_html(raw)
        use_panel  = bool(panel_html)

    # ── iDeal panel directMsg path ────────────────────────────────────────────
    if use_panel:
        entries = _parse_dimension_panel_direct_msg(panel_html)
        if entries:
            logger.info("[parse_dimensional_html] extracted %d errors from panel directMsg: %s", len(entries), html_path)
            return entries
        text_source = panel_html
    else:
        text_source = raw  # legacy path — only when xbrldie confirmed

    # ── Legacy regex path (BTDetails / free-text xbrldie format) ─────────────
    class _StripHTML(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.parts: list[str] = []
        def handle_data(self, data):
            self.parts.append(data)
        def get_text(self):
            return "\n".join(self.parts)

    stripper = _StripHTML()
    stripper.feed(text_source)
    text = stripper.get_text()
    text = _re.sub(r'[ \t]+', ' ', text)

    block_pattern_a = _re.compile(
        r'(\d+\.\d+(?:\.\d+)?\s*\[[^\]]+\]\s*:.*?)(?=\n\s*\d+\.\d+\s*\[|\Z)', _re.DOTALL,
    )
    blocks = [m.group(1).strip() for m in block_pattern_a.finditer(text) if m.group(1).strip()]

    if not blocks:
        block_pattern_b = _re.compile(
            r'(\[[^\]]*(?:Dimension|xbrldie)[^\]]*\].*?)'
            r'(?=\n\s*(?:\d+\.\d+\s*)?\[[^\]]*(?:Dimension|xbrldie)[^\]]*\]|\Z)',
            _re.DOTALL | _re.IGNORECASE,
        )
        blocks = [m.group(1).strip() for m in block_pattern_b.finditer(text) if m.group(1).strip()]

    if not blocks:
        logger.info("[parse_dimensional_html] no blocks found: %s", html_path)
        return _FALLBACK

    attr_pattern  = _re.compile(r'@?\b(name|value|context|unit|decimal|precision)\b\s*[:=]\s*["\']?([^\s@|,"\']+)["\']?', _re.IGNORECASE)
    meta_pattern  = _re.compile(r'Error\s*Code\s*:\s*(\S+)(?:.*?LineNo\s*:\s*(\d+))?(?:.*?ColumnNo\s*:\s*(\d+))?', _re.IGNORECASE | _re.DOTALL)
    class_pattern = _re.compile(r'\[([^\]]+)\]')

    errors: list[dict] = []
    seen: set[str] = set()

    for block in blocks:
        class_m     = class_pattern.search(block)
        error_class = class_m.group(1) if class_m else ""
        attrs       = {k.lower(): v for k, v in attr_pattern.findall(block)}
        meta_m      = meta_pattern.search(block)
        error_code  = meta_m.group(1) if meta_m else ""
        line_no     = meta_m.group(2) if (meta_m and meta_m.group(2)) else ""
        col_no      = meta_m.group(3) if (meta_m and meta_m.group(3)) else ""
        pipe_idx    = block.find("|")
        raw_msg     = block[:pipe_idx].strip() if pipe_idx != -1 else block.strip()
        raw_msg     = _re.split(r'Error\s*Code\s*:', raw_msg, flags=_re.IGNORECASE)[0].strip()
        concept     = attrs.get("name", "")
        if not concept:
            pm = _re.search(r"concept\s+'([^']+)'", block)
            if pm: concept = pm.group(1)
        context = attrs.get("context", "")
        value   = attrs.get("value", "")
        entry = {
            "error_class":          error_class,
            "section_ref":          "",
            "concept":              concept,
            "value":                value,
            "context":              context,
            "context_label":        _context_label(context),
            "is_duplicate_context": bool(context and _re.search(r'_OOOOO+\w*$', context)),
            "unit":                 attrs.get("unit", ""),
            "decimal":              attrs.get("decimal", ""),
            "precision":            attrs.get("precision", ""),
            "dimension":            "",
            "typed_dim_value":      "",
            "error_code":           error_code,
            "filename":             "",
            "line_no":              line_no,
            "col_no":               col_no,
            "raw_message":          raw_msg,
        }
        key = f"{error_class}|{concept}|{context}" if (concept or context) else f"{error_class}|{hash(raw_msg)}"
        if key not in seen:
            seen.add(key)
            errors.append(entry)

    logger.info("[parse_dimensional_html] extracted %d errors (legacy): %s", len(errors), html_path)
    return errors


def explain_dimensional_errors(errors: list[dict]) -> list[dict]:
    """
    Explain dimensional errors one-at-a-time.
    Prompts are strictly evidence-based — no inference of duplicate context,
    date format issues, missing members, or taxonomy expectations unless the
    parsed validator message explicitly states them.
    """
    import json as _json
    import httpx as _httpx
 
    if not errors:
        return errors
 
    ollama_base = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    model       = os.getenv("OLLAMA_MODEL", "llama3.1:latest")
    timeout     = float(os.getenv("OLLAMA_TIMEOUT", "180"))
    keep_alive  = os.getenv("OLLAMA_KEEP_ALIVE", "30m")
 
    results: list[dict] = []
 
    for err in errors:
        # ------------------------------------------------------------------
        # Build the payload from ONLY what the parser extracted.
        # We deliberately EXCLUDE is_duplicate_context and typed_dim_value
        # as they lead the LLM to infer causes not stated by the validator.
        # The raw_message IS included because it is the verbatim validator text.
        # ------------------------------------------------------------------
        raw_msg = err.get("raw_message", "")
        # Strip section refs so the model sees the actual message text
        clean_raw = re.sub(r'^[\d\.]+\s*\[[^\]]*\]\s*:\s*', '', raw_msg).strip() if raw_msg else ""
 
        payload: dict = {}
 
        if err.get("error_class"):
            payload["error_class"] = err["error_class"]
        if err.get("section_ref"):
            payload["section_ref"] = err["section_ref"]
        if err.get("concept"):
            payload["concept"] = err["concept"]
        if err.get("value"):
            payload["reported_value"] = err["value"]
        if err.get("context_label"):
            payload["context_description"] = err["context_label"]
        elif err.get("context"):
            payload["context_description"] = err["context"]
        if err.get("dimension"):
            payload["dimension"] = err["dimension"]
        if err.get("error_code"):
            payload["error_code"] = err["error_code"]
        if err.get("line_no"):
            payload["line_number"] = err["line_no"]
        # Include the verbatim validator message — this is the only factual anchor
        if clean_raw:
            payload["validator_message"] = clean_raw
 
        payload_json = _json.dumps(payload, indent=2, ensure_ascii=False)
 
        prompt = (
            "You are a regulatory XBRL reporting assistant. "
            "Your task is to explain a dimensional validation error to a business user.\n\n"
            "The validation error details are provided as JSON below. "
            "These fields are the ONLY source of truth you have.\n\n"
            f"{payload_json}\n\n"
            "Write ONE plain-English paragraph (maximum 70 words) explaining this error.\n\n"
            "ABSOLUTE RULES — any violation makes the explanation wrong and harmful:\n"
            "1. Use ONLY the fields present in the JSON. Do not infer or assume anything "
            "   that is not explicitly stated in the JSON.\n"
            "2. If 'validator_message' is present, it is the verbatim text from the validator. "
            "   Base your explanation on it. Do not paraphrase it in a way that adds meaning.\n"
            "3. If 'concept' is present, name it. If absent, do NOT guess a concept name.\n"
            "4. If 'reported_value' is present, quote it exactly. If absent, do NOT invent a value.\n"
            "5. If 'dimension' is present, mention it by name. Do NOT assume which dimension "
            "   is wrong if it is not in the JSON.\n"
            "6. Do NOT state that the context is a duplicate unless the validator_message "
            "   explicitly says 'duplicate'.\n"
            "7. Do NOT state that a date format is wrong unless the validator_message "
            "   explicitly says the date format is invalid.\n"
            "8. Do NOT state that a member is missing or incorrect unless the validator_message "
            "   explicitly says so.\n"
            "9. Do NOT use phrases like 'it appears', 'seems', 'may be', 'possibly', "
            "   'likely', or 'probably'.\n"
            "10. Do NOT mention 'XBRL', 'taxonomy', 'schema', 'cvc-', or technical codes.\n"
            "11. If the validator message says 'invalid combination of dimensions and members', "
            "    say exactly that — do NOT speculate on which dimension or member is wrong.\n"
            "12. If the validator message says 'does not match the typeDomainRef', say that "
            "    the value does not match the definition — do NOT assume the cause.\n"
            "13. End with exactly: 'The report cannot be submitted until this is corrected.'\n"
            "14. One paragraph only. No bullet points. No markdown.\n\n"
            "Return only the explanation paragraph."
        )
 
        explanation = ""
        try:
            api_payload = {
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a regulatory reporting assistant. "
                            "Explain validation errors using ONLY the JSON fields provided. "
                            "NEVER infer causes, duplicate contexts, date format problems, "
                            "missing members, or taxonomy expectations unless the "
                            "validator_message field explicitly states them. "
                            "Return one plain-text paragraph. No markdown. No preamble."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
                "keep_alive": keep_alive,
                "options": {"temperature": 0.0, "num_predict": 200},
            }
            with _httpx.Client(timeout=timeout) as client:
                resp = client.post(f"{ollama_base}/api/chat", json=api_payload)
                resp.raise_for_status()
            explanation = resp.json()["message"]["content"].strip()
            logger.info(
                "[DIM_LLM] concept=%r explanation=%r",
                err.get("concept", ""),
                explanation[:80],
            )
        except Exception as exc:
            logger.warning("[DIM_LLM] LLM failed: %s — using fallback", exc)
 
        if not explanation or len(explanation) < 20:
            explanation = _fallback(err)
 
        merged = dict(err)
        merged["explanation"] = explanation
        results.append(merged)
 
    return results


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2: XBRL SCHEMA PARSER + ROOT-CAUSE GROUPER + EXPLAINER  (IMPROVED)
# ══════════════════════════════════════════════════════════════════════════════

def parse_backtrack_html_errors(html_path: str) -> list[dict]:
    """Parse a backtrack HTML validation report (BTDetails / 4000-series).

    Handles two table formats:
    1. Header+data rows (BTDetails format): th headers + td data rows
    2. directMsg rows (iDeal SPECIFICATION_ERROR format): single-column td.directMsg rows
    """
    from html.parser import HTMLParser
    import re as _re_dm

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

    _HEADER_MAP: dict[str, str] = {
        "error category": "errorType", "category": "errorType",
        "error type": "errorType", "type": "errorType",
        "title": "title", "error title": "title", "validation name": "title", "name": "title",
        "rule": "rule", "rule name": "rule", "formula": "rule",
        "formula expression": "rule", "expression": "rule",
        "validation rule": "rule", "constraint": "rule",
        "error message": "message", "message": "message", "description": "message",
        "error description": "message", "validation message": "message",
        "detail": "message", "details": "message",
        "table": "table", "table name": "table", "sheet": "table",
        "cell code": "cellCode", "cell": "cellCode", "cell name": "cellCode",
        "cell reference": "cellCode", "ref": "cellCode",
        "context": "context", "period": "context",
        "entered value": "actualValue", "value": "actualValue",
        "actual value": "actualValue", "actual": "actualValue", "reported value": "actualValue",
        "expected value": "expectedValue", "expected": "expectedValue",
        "data type": "expectedValue", "expected value / data type": "expectedValue",
        "type restriction": "expectedValue",
        "unit": "unit",
        "assertion label": "assertionLabel", "assertion": "assertionLabel", "label": "assertionLabel",
        "severity": "severity",
        "suggestion": "suggestion", "fix": "suggestion",
        "corrective action": "suggestion", "resolution": "suggestion",
        "variable": "variableName", "variable name": "variableName",
        "var name": "variableName", "var": "variableName",
        "variable value": "variableValue", "var value": "variableValue",
        "sr. no.": "_srNo", "sr no": "_srNo", "s. no.": "_srNo",
        "s.no": "_srNo", "no.": "_srNo", "#": "_srNo",
        "sl. no.": "_srNo", "sr.no.": "_srNo",
        "db tablename": "db_tablename", "db table name": "db_tablename",
        "cell index": "cellIndex", "table header": "tableHeader",
        "column label(s)": "columnLabel", "column label": "columnLabel",
        "variable id": "variableId",
        "row label(s)": "row_label", "row label": "row_label",
        "instance data(s)": "instance_data", "instance data": "instance_data",
        "entered data(s)": "actualValue", "entered data": "actualValue",
        "decimal": "decimal",
    }

    def _canonical_key(raw_hdr: str) -> str:
        return _HEADER_MAP.get(raw_hdr.lower().strip(), raw_hdr.lower().strip().replace(" ", "_"))

    def _infer_severity(section: str) -> str:
        s = section.upper()
        if any(k in s for k in ("FORMULA", "SPECIFICATION", "SCHEMA", "ERROR")):
            return "error"
        if any(k in s for k in ("QUALITY", "WARNING", "WARN", "CHECK")):
            return "warning"
        return "error"

    def _generate_suggestion(entry: dict) -> str:
        actual   = (entry.get("actualValue") or entry.get("entered_data(s)") or
                    entry.get("instance_data(s)") or entry.get("instance_data") or "")
        expected = entry.get("expectedValue") or entry.get("decimal") or ""
        err_type = entry.get("errorType", "")
        rule     = entry.get("rule", "")
        cell     = entry.get("cellCode", "")
        cell_hint = f" in cell {cell}" if cell else ""
        if actual and expected:
            return f"Replace '{actual}' with a valid {expected} value{cell_hint}."
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
        return bool(h_lower & {"variable", "variable name", "var name", "var"})

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
            if val and not key.startswith("_"):
                entry[key] = val
        useful = {k for k in entry if k not in ("errorType", "severity")}
        if not useful:
            return None
        if "severity" not in entry:
            entry["severity"] = _infer_severity(entry.get("errorType", ""))
        if "suggestion" not in entry:
            entry["suggestion"] = _generate_suggestion(entry)
        return entry

    def _parse_direct_msg_entries(html: str) -> list[dict]:
        import re as _re_dm
        entries: list[dict] = []

        tag_re  = _re_dm.compile(r'<[^>]+>')
        nbsp_re = _re_dm.compile(r'&nbsp;|&#160;', _re_dm.IGNORECASE)

        def _strip_tags(s: str) -> str:
            s = nbsp_re.sub(' ', s)
            s = tag_re.sub(' ', s)
            return _re_dm.sub(r'\s+', ' ', s).strip()

        panel_re = _re_dm.compile(
            r'<div[^>]+class="[^"]*panel[^"]*panel-default[^"]*"[^>]*>(.*?)'
            r'(?=<div[^>]+class="[^"]*panel[^"]*panel-default[^"]*"[^>]*>|\Z)',
            _re_dm.DOTALL | _re_dm.IGNORECASE,
        )
        label_re = _re_dm.compile(
            r'class="[^"]*assertionLabel[^"]*"[^>]*>(.*?)</div>',
            _re_dm.DOTALL | _re_dm.IGNORECASE,
        )
        badge_re = _re_dm.compile(
            r'class="[^"]*badge[^"]*"[^>]*>\s*(\d+)\s*<',
            _re_dm.IGNORECASE,
        )
        direct_msg_re = _re_dm.compile(
            r'<td[^>]+class="[^"]*directMsg[^"]*"[^>]*>(.*?)</td>',
            _re_dm.DOTALL | _re_dm.IGNORECASE,
        )
        details_re = _re_dm.compile(
            r'<span[^>]+class="[^"]*msgDetails[^"]*"[^>]*>(.*?)</span>',
            _re_dm.DOTALL | _re_dm.IGNORECASE,
        )

        for panel_m in panel_re.finditer(html):
            panel_html = panel_m.group(1)
            label_m = label_re.search(panel_html)
            panel_label = _strip_tags(label_m.group(1)).strip() if label_m else ""
            if not panel_label:
                continue
            badge_m = badge_re.search(panel_html)
            badge_count = int(badge_m.group(1)) if badge_m else 0
            if badge_count == 0:
                continue
            for dm_m in direct_msg_re.finditer(panel_html):
                cell_html = dm_m.group(1)
                details_m   = details_re.search(cell_html)
                details_txt = _strip_tags(details_m.group(1)) if details_m else ""
                main_html   = details_re.sub('', cell_html)
                main_text   = _strip_tags(main_html).strip()
                if not main_text:
                    continue
                entered_value = ""
                expected_type = ""
                val_m = _re_dm.search(
                    r"['\u2018\u2019\u201c\u201d]([^'\"]+)['\u2018\u2019\u201c\u201d]"
                    r".*?(?:is not a valid value for|not valid for)"
                    r"\s*['\u2018\u2019\u201c\u201d]([^'\"]+)['\u2018\u2019\u201c\u201d]",
                    main_text, _re_dm.IGNORECASE,
                )
                if val_m:
                    entered_value = val_m.group(1).strip()
                    expected_type = val_m.group(2).strip()
                else:
                    first_q = _re_dm.search(r"'([^']+)'", main_text)
                    if first_q:
                        entered_value = first_q.group(1).strip()
                line_no = col_no = ""
                line_m = _re_dm.search(r'LineNo\s*:\s*(\d+)', details_txt, _re_dm.IGNORECASE)
                col_m  = _re_dm.search(r'ColumnNo\s*:\s*(\d+)', details_txt, _re_dm.IGNORECASE)
                if line_m: line_no = line_m.group(1)
                if col_m:  col_no  = col_m.group(1)
                # Extract filename from msgDetails
                fn_m = _re_dm.search(r'FileName\s*:\s*([^\s]+\.xml)', details_txt, _re_dm.IGNORECASE)
                filename = fn_m.group(1) if fn_m else ""
                entry: dict = {
                    "errorType":     panel_label,
                    "severity":      _infer_severity(panel_label),
                    "message":       main_text,
                    "actualValue":   entered_value,
                    "expectedValue": expected_type,
                    "line_no":       line_no,
                    "col_no":        col_no,
                    "filename":      filename,
                    "_source":       "directMsg",
                }
                if entered_value and expected_type:
                    entry["suggestion"] = f"Replace '{entered_value}' with a valid {expected_type} value."
                else:
                    entry["suggestion"] = _generate_suggestion(entry)
                entries.append(entry)
        return entries

    direct_msg_entries = _parse_direct_msg_entries(raw)

    class _TableParser(HTMLParser):
        def __init__(self) -> None:
            super().__init__(convert_charrefs=True)
            self.errors: list[dict] = []
            self._current_section: str = ""
            self._in_heading         = False
            self._in_assertion_label = False
            self._in_table        = False
            self._in_tr           = False
            self._in_cell         = False
            self._is_hdr_row      = False
            self._cell_texts: list[str] = []
            self._headers:    list[str] = []
            self._buf = ""
            self._table_is_var = False
            self._pending_vars: list[dict] = []
            self._is_direct_msg_row = False

        def _attr(self, attrs: list, name: str) -> str:
            for k, v in attrs:
                if k == name: return v or ""
            return ""

        def _has_class(self, attrs: list, *cls_names: str) -> bool:
            classes = set(self._attr(attrs, "class").split())
            return bool(classes & set(cls_names))

        def handle_starttag(self, tag: str, attrs: list) -> None:
            tag = tag.lower()
            if tag in ("h1", "h2", "h3", "h4", "h5", "caption"):
                self._buf = ""; self._in_heading = True; self._in_cell = True
            elif tag == "div" and self._has_class(attrs, "assertionLabel"):
                self._buf = ""; self._in_assertion_label = True; self._in_cell = True
            elif tag == "table":
                self._in_table = True; self._headers = []
                self._table_is_var = False; self._pending_vars = []
            elif tag == "tr":
                self._in_tr = True; self._is_hdr_row = False
                self._cell_texts = []; self._is_direct_msg_row = False
            elif tag in ("td", "th"):
                if tag == "td" and self._has_class(attrs, "directMsg"):
                    self._is_direct_msg_row = True
                self._in_cell = True; self._buf = ""
                if tag == "th": self._is_hdr_row = True
            elif tag == "br" and self._in_cell:
                self._buf += "\n"

        def handle_endtag(self, tag: str) -> None:
            tag = tag.lower()
            if tag in ("h1", "h2", "h3", "h4", "h5", "caption"):
                txt = self._buf.strip().upper()
                if txt: self._current_section = txt
                self._in_heading = False; self._in_cell = False; self._buf = ""
            elif tag == "div" and self._in_assertion_label:
                txt = self._buf.strip().upper()
                if txt: self._current_section = txt
                self._in_assertion_label = False; self._in_cell = False; self._buf = ""
            elif tag in ("td", "th"):
                self._cell_texts.append(self._buf.strip())
                self._in_cell = False; self._buf = ""
            elif tag == "tr":
                self._in_tr = False
                cells = self._cell_texts
                if self._is_direct_msg_row:
                    self._cell_texts = []
                    self._is_direct_msg_row = False
                    return
                if self._is_hdr_row and cells:
                    self._headers = [c.strip() for c in cells]
                    self._table_is_var = _is_variable_table(self._headers)
                elif cells and any(cells):
                    if self._table_is_var:
                        ve = _build_var_entry(self._headers, cells)
                        if ve: self._pending_vars.append(ve)
                    else:
                        entry = _build_entry(self._current_section, self._headers, cells)
                        if entry: self.errors.append(entry)
                self._cell_texts = []
            elif tag == "table":
                self._in_table = False
                if self._pending_vars and self.errors:
                    if "variables" not in self.errors[-1]:
                        self.errors[-1]["variables"] = []
                    self.errors[-1]["variables"].extend(self._pending_vars)
                self._table_is_var = False; self._pending_vars = []

        def handle_data(self, data: str) -> None:
            if self._in_cell or self._in_assertion_label:
                self._buf += data

    parser = _TableParser()
    try:
        parser.feed(raw)
    except Exception as exc:
        logger.warning("[parse_backtrack_html] parse error: %s — %s", html_path, exc)
        return _FALLBACK

    def _merge_title_and_data_rows(raw_rows: list[dict]) -> list[dict]:
        merged: list[dict] = []
        i = 0
        while i < len(raw_rows):
            row = raw_rows[i]
            is_title_row = (
                "col_0" in row
                and "cellCode" not in row
                and "actualValue" not in row
                and "db_tablename" not in row
            )
            if is_title_row and i + 1 < len(raw_rows):
                combined = dict(raw_rows[i + 1])
                import re as _re_merge
                raw_title   = row["col_0"].replace("\u00a0", " ").lstrip("▼").strip()
                clean_title = _re_merge.split("cvc-", raw_title, maxsplit=1)[0].split("\n")[0].strip().rstrip(".")
                if clean_title:
                    combined["message"] = clean_title
                merged.append(combined)
                i += 2
            else:
                merged.append(row)
                i += 1
        return merged

    merged_errors = _merge_title_and_data_rows(parser.errors)

    for err in merged_errors:
        if "severity" not in err:
            err["severity"] = _infer_severity(err.get("errorType", ""))
        if "suggestion" not in err:
            err["suggestion"] = _generate_suggestion(err)

    all_errors = direct_msg_entries + [e for e in merged_errors if e.get("_source") != "directMsg"]

    logger.info("[parse_backtrack_html] extracted %d error(s) from: %s", len(all_errors), html_path)
    return all_errors


def _group_schema_errors_by_root_cause(errors: list[dict]) -> list[dict]:
    """Group XBRL schema directMsg errors that share the same file + line number.

    Errors at the same line are a cascade: the first is the root cause,
    subsequent errors at the same line are downstream consequences.
    """
    if not errors:
        return errors

    from collections import defaultdict
    line_groups: dict[str, list[dict]] = defaultdict(list)
    passthrough: list[dict] = []

    for err in errors:
        if err.get("_source") == "directMsg" and err.get("line_no"):
            key = f"{err.get('filename','unknown')}:{err['line_no']}"
            line_groups[key].append(err)
        else:
            passthrough.append(err)

    result: list[dict] = []

    for key, group in line_groups.items():
        if len(group) == 1:
            result.append(group[0])
            continue

        base = dict(group[0])
        cascade_messages = []
        all_values: list[str] = []
        all_elements: list[str] = []
        for g in group:
            raw = g.get("message", "") or g.get("raw_message", "") or ""
            if raw:
                cascade_messages.append(raw)
            v = g.get("actualValue", "") or g.get("entered_value", "")
            if v and v not in all_values:
                all_values.append(v)
            em = re.search(r"[Ee]lement\s+'([^']+)'", raw)
            if em and em.group(1) not in all_elements:
                all_elements.append(em.group(1))

        base["cascade_errors"]     = cascade_messages
        base["all_invalid_values"] = all_values
        base["all_element_names"]  = all_elements
        base["cascade_count"]      = len(group)
        if all_elements and all_values:
            base["suggestion"] = (
                f"The field(s) {', '.join(all_elements)} contain the value "
                f"'{all_values[0]}' which is not a valid date. "
                f"Use format YYYY-MM-DD (e.g. {_to_iso_date(all_values[0])})."
            )
        result.append(base)

    result.extend(passthrough)
    return result


def _build_root_cause_analysis(
    schema_errors: list[dict],
    formula_rules: list[dict],
    dim_errors: list[dict],
) -> list[dict]:
    """Cross-category root cause analysis.

    Detects when XBRL Schema date errors are the upstream cause of:
      - FORMULA errors (refPeriodEndDate format error → formula can't evaluate)
      - DIMENSION errors (bad date embedded in context ID → typed dimension invalid)
    """
    if not schema_errors:
        return schema_errors

    bad_dates: dict[str, list[str]] = {}
    for err in schema_errors:
        val = (err.get("actualValue") or err.get("entered_value") or
               (err.get("all_invalid_values") or [None])[0] or "")
        if val and re.match(r'^\d{2}[.\-/]\d{2}[.\-/]\d{4}$', val):
            elems = err.get("all_element_names", [])
            if val not in bad_dates:
                bad_dates[val] = []
            bad_dates[val].extend(elems)

    formula_affected: list[str] = []
    for rule in formula_rules:
        for inst in rule.get("instances", []):
            biz_msg = inst.get("business_message", "")
            if "refPeriodEndDate" in biz_msg or "refPeriodEndDate" in rule.get("rule_name", ""):
                formula_affected.append(rule.get("rule_name", ""))
                break
        for inst in rule.get("instances", []):
            for var in inst.get("variables", []):
                if "refPeriodEndDate" in var.get("concept", ""):
                    if rule.get("rule_name") not in formula_affected:
                        formula_affected.append(rule.get("rule_name", ""))

    dim_affected: list[str] = []
    for err in dim_errors:
        ec = err.get("error_class", "")
        if "IllegalTypedDimension" in ec:
            ctx = err.get("context", "")
            for bad_date in bad_dates:
                iso = _to_iso_date(bad_date).replace("-", "")
                if iso in ctx:
                    label = err.get("dimension", "") or "DateAxis"
                    if label not in dim_affected:
                        dim_affected.append(label)

    if not (formula_affected or dim_affected):
        return schema_errors

    result = []
    for err in schema_errors:
        err = dict(err)
        downstream = []
        val = (err.get("actualValue") or err.get("entered_value") or
               (err.get("all_invalid_values") or [None])[0] or "")
        if val in bad_dates:
            if formula_affected:
                downstream.append(
                    f"This date error prevents evaluation of formula rule(s): "
                    f"{', '.join(formula_affected[:3])}."
                )
            if dim_affected:
                downstream.append(
                    f"The same date value embedded in context identifiers causes dimensional "
                    f"validation failures for typed dimension(s): {', '.join(dim_affected)}."
                )
        if downstream:
            err["downstream_effects"] = downstream
        result.append(err)

    return result


def _build_fallback_business_explanation(err: dict) -> str:
    """
    Evidence-based fallback for XBRL schema errors.
    Derives text only from parsed fields.
    Never asserts date format, business meaning, or downstream effects
    unless they are present in the parsed dict.
    """
    import re as _re_fb
 
    is_direct = err.get("_source") == "directMsg"
 
    # Identify the subject from parsed fields only
    cell = err.get("cellCode") or err.get("cell", "")
    if cell and not is_direct:
        subject = f"Cell {cell}"
    else:
        em = _re_fb.search(
            r"[Ee]lement\s+'([^']+)'",
            err.get("message", "") or err.get("validation_message", ""),
        )
        if em:
            subject = f"The field \"{em.group(1)}\""
        elif err.get("all_element_names"):
            names = err["all_element_names"]
            subject = f"The field(s) {', '.join(names)}"
        else:
            subject = "A reported value"
 
    # Invalid value — from parsed fields only
    actual = (
        err.get("entered_data(s)")
        or err.get("actualValue")
        or err.get("instance_data(s)")
        or (err.get("all_invalid_values") or [None])[0]
        or ""
    ).strip()
 
    if not actual and is_direct:
        raw = err.get("message", "")
        m = _re_fb.search(
            r"['\u2018\u2019\u201c\u201d]([^'\"]+)['\u2018\u2019\u201c\u201d]", raw
        )
        if m:
            actual = m.group(1).strip()
 
    expected = (err.get("expectedValue") or err.get("decimal") or "").strip()
 
    # Use validator message as the factual anchor
    raw_validator_msg = (
        err.get("validation_message")
        or err.get("message")
        or err.get("col_0")
        or ""
    ).strip()
    # Strip cvc- codes — they are technical noise
    clean_validator_msg = _re_fb.sub(r"^cvc-[\w\.\-]+:\s*", "", raw_validator_msg).strip()
    # Strip duplicate cell prefix
    clean_validator_msg = _re_fb.sub(
        r"^Cell\s+\S+\s+failed\s+validation\s*:\s*", "", clean_validator_msg,
        flags=_re_fb.IGNORECASE,
    ).strip()
 
    lines = []
 
    if actual and expected:
        lines.append(
            f"{subject} contains the value '{actual}', "
            f"which is not a valid {expected} value."
        )
    elif actual and clean_validator_msg:
        lines.append(
            f"{subject} contains the value '{actual}'. "
            f"The validator reports: \"{clean_validator_msg}\"."
        )
    elif actual:
        lines.append(f"{subject} contains the value '{actual}', which failed validation.")
    elif clean_validator_msg:
        lines.append(f"{subject} failed validation. The validator reports: \"{clean_validator_msg}\".")
    else:
        lines.append(f"{subject} failed validation.")
 
    # Downstream effects — include only if explicitly populated by root-cause analysis
    if err.get("downstream_effects"):
        for effect in err["downstream_effects"][:2]:
            lines.append(effect)
 
    lines.append("The report cannot be submitted until this is corrected.")
    return " ".join(lines)


def _normalize_error_for_llm(err: dict) -> dict:
    """
    Build a fully-populated LLM payload for one XBRL schema error.
    Strips speculative keys; keeps only what the parser directly extracted.
    """
    import re as _re
 
    normalized: dict = {}
    is_direct = err.get("_source") == "directMsg"
 
    # Cell code — only for non-directMsg entries
    if not is_direct:
        for src in ("cellCode", "cell"):
            val = (err.get(src) or "").strip()
            if val:
                normalized["cell"] = val
                break
 
    def _set(key: str, *sources: str) -> None:
        for src in sources:
            val = (err.get(src) or "").strip()
            if val:
                normalized[key] = val
                return
 
    _set("entered_value", "entered_data(s)", "instance_data(s)", "actualValue", "enteredValue")
    _set("expected_type", "expectedValue")
 
    if not is_direct:
        _set("row_label", "row_label(s)", "row_label")
 
    # Validator message — verbatim from parser, strip cvc- codes
    raw_msg = (err.get("message") or err.get("col_0") or err.get("title") or "").strip()
    if raw_msg:
        raw_msg = raw_msg.replace("\u00a0", " ").lstrip("▼").strip()
        if is_direct:
            cleaned = re.sub(r"^cvc-[\w\.\-]+:\s*", "", raw_msg).strip()
            if cleaned:
                normalized["validator_message"] = cleaned
                cvc_m = re.match(r"(cvc-[\w\.\-]+):", raw_msg)
                if cvc_m:
                    normalized["validator_rule_code"] = cvc_m.group(1)
        else:
            cleaned = re.split("cvc-", raw_msg, maxsplit=1)[0].split("\n")[0].strip().rstrip(".")
            cleaned = re.sub(
                r"^Cell\s+\S+\s+failed\s+validation\s*:\s*", "", cleaned,
                flags=re.IGNORECASE,
            ).strip()
            if cleaned:
                normalized["validator_message"] = cleaned
 
    # Element name from validator text
    for text_src in (raw_msg, err.get("message", "")):
        em = re.search(r"[Ee]lement\s+'([^']+)'", text_src or "")
        if em:
            normalized["element_name"] = em.group(1)
            break
 
    # File location
    if is_direct:
        line_no  = err.get("line_no", "")
        col_no   = err.get("col_no", "")
        filename = err.get("filename", "")
        if line_no:
            loc = f"Line {line_no}"
            if col_no:
                loc += f", Column {col_no}"
            normalized["file_location"] = loc
        if filename:
            normalized["filename"] = filename
 
    # Cascade errors at the same location
    if err.get("cascade_errors"):
        # Strip cvc- prefixes from each cascade message too
        cleaned_cascade = [
            re.sub(r"^cvc-[\w\.\-]+:\s*", "", m).strip()
            for m in err["cascade_errors"]
            if m.strip()
        ]
        if cleaned_cascade:
            normalized["related_errors_at_same_location"] = cleaned_cascade
 
    if err.get("all_element_names"):
        normalized["affected_elements"] = err["all_element_names"]
    if err.get("all_invalid_values"):
        normalized["all_invalid_values"] = err["all_invalid_values"]
 
    # Downstream effects — only if populated by root-cause analysis
    if err.get("downstream_effects"):
        normalized["downstream_effects"] = err["downstream_effects"]
 
    # NOTE: is_duplicate_context is intentionally NOT included.
    # The LLM was using it to assert "duplicate context" even when the
    # validator message did not say so. The _OOOOO suffix is an internal
    # implementation detail, not a validated fact.
 
    return normalized


def _extract_raw_validation_message(err: dict) -> str:
    """Verbatim copy from original — included here so the module is self-contained."""
    import re as _re_msg
    raw = (err.get("message") or err.get("col_0") or err.get("title") or "").strip()
    if raw:
        raw = raw.replace("\u00a0", " ").lstrip("▼").strip()
        raw = _re_msg.split("cvc-", raw, maxsplit=1)[0].split("\n")[0].strip().rstrip(".")
        if raw:
            return raw
    actual   = (err.get("actualValue") or err.get("entered_data(s)") or "").strip()
    expected = (err.get("expectedValue") or "").strip()
    if actual and expected:
        return f"'{actual}' is not a valid value for '{expected}'"
    if actual:
        return f"Invalid value: '{actual}'"
    return ""


def _explain_single_error(
    err: dict, ollama_base: str, model: str, timeout: float, keep_alive: str
) -> str:
    """
    Call LLM for one XBRL schema error.
    Strict evidence-only prompt — no inference of date format, duplicates,
    or business meaning beyond what the validator explicitly states.
    """
    import json as _json
    import httpx as _httpx
 
    payload_item = _normalize_error_for_llm(err)
    error_json   = _json.dumps(payload_item, indent=2, ensure_ascii=False)
    cell         = payload_item.get("cell", "")
    is_direct    = err.get("_source") == "directMsg"
 
    # Opening instruction — determines subject reference
    if cell:
        opening_rule = (
            f"1. Start with the exact cell code: 'Cell {cell} contains ...'\n"
            f"   CORRECT: 'Cell {cell} contains ...'\n"
            f"   WRONG: Referring to the cell in any other way or inventing a different cell."
        )
    elif payload_item.get("affected_elements"):
        elems = payload_item["affected_elements"]
        opening_rule = (
            f"1. Start by referencing the field(s) involved: {', '.join(elems)}\n"
            "   Do NOT invent a cell reference code."
        )
    elif payload_item.get("element_name"):
        elem = payload_item["element_name"]
        opening_rule = (
            f"1. Start by referencing the field: \"{elem}\"\n"
            "   Do NOT invent a cell reference code."
        )
    elif payload_item.get("entered_value") or payload_item.get("all_invalid_values"):
        val = payload_item.get("entered_value") or payload_item["all_invalid_values"][0]
        opening_rule = (
            f"1. Start by referencing the value that failed: '{val}'\n"
            "   Do NOT invent a cell reference code."
        )
    else:
        opening_rule = (
            "1. Start by describing what failed using the 'validator_message' field.\n"
            "   Do NOT invent a cell reference code."
        )
 
    has_cascade    = bool(payload_item.get("related_errors_at_same_location"))
    has_downstream = bool(payload_item.get("downstream_effects"))
 
    cascade_instruction = ""
    if has_cascade:
        cascade_instruction = (
            "\n10. 'related_errors_at_same_location' lists additional errors triggered by "
            "the same location. Describe them as a chain without speculating on root causes "
            "beyond what the messages state.\n"
        )
 
    downstream_instruction = ""
    if has_downstream:
        downstream_instruction = (
            "\n11. 'downstream_effects' lists errors in other validation categories caused by "
            "this problem. Mention them briefly using only the text provided.\n"
        )
 
    prompt = (
        "You are a regulatory reporting assistant helping a business user understand "
        "why their report submission was rejected.\n\n"
        "A validation error is provided as JSON. "
        "These fields are the ONLY source of truth you have.\n\n"
        f"{error_json}\n\n"
        "Write ONE plain-English paragraph (maximum 80 words) explaining this error.\n\n"
        f"STRICT RULES:\n"
        f"{opening_rule}\n"
        "2. Quote 'entered_value' or 'all_invalid_values' exactly — do not alter them.\n"
        "3. Do not invent any field, value, element name, or cell code not in the JSON.\n"
        "4. If 'validator_message' is present, use it as your primary factual basis. "
        "   Do not add meaning beyond what it states.\n"
        "5. If the validator_message says 'is not a valid value for date', say that. "
        "   Do NOT additionally claim the format should be YYYY-MM-DD unless "
        "   the validator_message explicitly states a required format.\n"
        "6. Do NOT state that a context is a duplicate unless the validator_message "
        "   explicitly uses the word 'duplicate'.\n"
        "7. Do NOT suggest what the corrected value should be.\n"
        "8. No bullet points, headers, or markdown.\n"
        "9. Do NOT use: 'invalid value', 'validation failed', 'schema', 'XML', "
        "   'XBRL', 'cvc-', 'it appears', 'seems', 'may be', 'possibly', 'likely'.\n"
        "10. Do not repeat any element name more than once.\n"
        f"{cascade_instruction}"
        f"{downstream_instruction}"
        "End with: 'The report cannot be submitted until this is corrected.'\n\n"
        "Output the explanation paragraph only. No JSON. No markdown. No preamble."
    )
 
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a regulatory reporting assistant. "
                    "Explain validation errors in plain English using ONLY the information "
                    "in the JSON. "
                    "NEVER state that a context is a duplicate, that a date format is wrong, "
                    "or that a member is incorrect unless the validator_message explicitly "
                    "states this. "
                    "NEVER invent a cell reference, element name, or value not in the JSON. "
                    "Return exactly one plain-text paragraph. No JSON. No markdown."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "keep_alive": keep_alive,
        "options": {"temperature": 0.0, "num_predict": 250},
    }
 
    try:
        import httpx as _httpx
        with _httpx.Client(timeout=timeout) as client:
            resp = client.post(f"{ollama_base}/api/chat", json=payload)
            resp.raise_for_status()
        explanation = resp.json()["message"]["content"].strip()
        logger.info(
            "[LLM_RETRY] cell=%r  parsed=%r", cell or "(no cell)", explanation[:80]
        )
        return explanation
    except Exception as exc:
        logger.warning("[LLM_RETRY] cell=%r  failed: %s", cell or "(no cell)", exc)
        return ""


def explain_validation_errors(errors: list[dict]) -> list[dict]:
    """
    Explain XBRL schema errors with root-cause grouping.
    Unchanged orchestration; updated to use new _explain_single_error
    and _build_fallback_business_explanation.
    """
    if not errors:
        return errors
 
    ollama_base = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    model       = os.getenv("OLLAMA_MODEL", "llama3.1:latest")
    timeout     = float(os.getenv("OLLAMA_TIMEOUT", "180"))
    keep_alive  = os.getenv("OLLAMA_KEEP_ALIVE", "30m")
 
    logger.info(
        "[STATUS_FLOW] Starting XBRL schema LLM enrichment, errors=%d", len(errors)
    )
 
    # Group cascades before explaining (calls original helper — unchanged)
    from backend.tools.report_lookup import _group_schema_errors_by_root_cause
    grouped = _group_schema_errors_by_root_cause(errors)
 
    def _build_table_info(err: dict, cell: str) -> dict:
        return {
            "db_table_name": (err.get("db_tablename") or err.get("table") or "").strip(),
            "row_label":     (err.get("row_label") or err.get("row_label(s)") or "").strip(),
            "context":       err.get("context", "").strip(),
            "cell_code":     (cell or err.get("cellCode", "") or err.get("cell", "")).strip(),
            "validation_error": (
                _extract_raw_validation_message(err)
                or (
                    f"'{err['actualValue']}' is not a valid value for '{err['decimal']}'"
                    if err.get("actualValue") and err.get("decimal") else ""
                )
                or err.get("actualValue", "")
            ).strip(),
        }
 
    start   = time.perf_counter()
    results: list[dict] = []
 
    for i, err in enumerate(grouped):
        cell        = err.get("cellCode", "") or err.get("cell", "")
        explanation = _explain_single_error(err, ollama_base, model, timeout, keep_alive)
        if not explanation or len(explanation) < 10:
            logger.warning(
                "[LLM_RETRY] index=%d cell=%r — using fallback", i, cell
            )
            explanation = _build_fallback_business_explanation(err)
        merged = dict(err)
        merged["explanation"] = explanation
        merged.setdefault("cell", cell)
        merged["table_info"]  = _build_table_info(err, cell)
        results.append(merged)
 
    logger.info(
        "[STATUS_FLOW] XBRL schema enrichment complete — populated=%d  elapsed=%.3fs",
        len(results),
        time.perf_counter() - start,
    )
    return results


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3: FORMULA_ERROR PARSER + ENRICHER + EXPLAINER  (IMPROVED)
# ══════════════════════════════════════════════════════════════════════════════

def _classify_formula_type(formula: str) -> str:
    f = formula.lower()
    if "if(" in f or "if (" in f:
        return "ratio_check"
    if "round(" in f:
        return "rounded_equality"
    if re.search(r'\$v\d+\s*\+\s*\$v\d+', f):
        return "sum_check"
    if re.search(r'not\s*\(\s*empty', f):
        return "presence_check"
    return "general"


def _extract_context_hint(context: str) -> str:
    if not context:
        return ""
    d = _decompose_context(context)
    members = d.get("members", [])
    clean_members = [re.sub(r'Member$', '', m) for m in members if m]
    period = ""
    if d.get("period_from") and d.get("period_to"):
        period = f"{d['period_from']} to {d['period_to']}"
    elif d.get("instant_date"):
        period = d["instant_date"]
    parts = []
    if period:
        parts.append(period)
    if clean_members:
        parts.append(", ".join(clean_members))
    return " / ".join(parts) if parts else context[:60]


def _compute_sum_discrepancy(instances: list[dict]) -> list[dict]:
    from decimal import Decimal, InvalidOperation
    enriched = []
    for inst in instances:
        vars_by_id = {v["var"]: v for v in inst.get("variables", [])}
        lhs_var  = vars_by_id.get("V1")
        rhs_vars = [v for k, v in sorted(vars_by_id.items()) if k != "V1"]
        inst = dict(inst)
        inst["lhs_var"] = lhs_var; inst["rhs_vars"] = rhs_vars
        if lhs_var:
            try:
                reported = Decimal(str(lhs_var.get("value", "0")).replace(",", ""))
                calc     = sum(
                    Decimal(str(v.get("value", "0")).replace(",", ""))
                    for v in rhs_vars if v.get("value", "").strip()
                )
                diff = reported - calc
                inst.update({
                    "reported_total": str(reported),
                    "calculated_sum": str(calc),
                    "difference":     str(diff),
                    "unit":           lhs_var.get("unit", ""),
                })
            except (InvalidOperation, ValueError):
                pass
        enriched.append(inst)
    return enriched


def _compute_ratio_discrepancy(instances: list[dict]) -> list[dict]:
    from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
    enriched = []
    for inst in instances:
        vars_by_id = {v["var"]: v for v in inst.get("variables", [])}
        v1 = vars_by_id.get("V1"); v2 = vars_by_id.get("V2"); v3 = vars_by_id.get("V3")
        inst = dict(inst)
        inst["lhs_var"] = v1; inst["numerator_var"] = v2; inst["denominator_var"] = v3
        if v1 and v2 and v3:
            try:
                reported    = Decimal(str(v1.get("value", "0")))
                numerator   = Decimal(str(v2.get("value", "0")))
                denominator = Decimal(str(v3.get("value", "0")))
                calculated  = (
                    (numerator / denominator * 100).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
                    if denominator != 0 else Decimal("0")
                )
                inst.update({
                    "reported_value":    str(reported),
                    "numerator_value":   str(numerator),
                    "denominator_value": str(denominator),
                    "calculated_value":  str(calculated),
                    "numerator_unit":    v2.get("unit", ""),
                    "denominator_unit":  v3.get("unit", ""),
                })
            except (InvalidOperation, ValueError):
                pass
        enriched.append(inst)
    return enriched


def parse_formula_errors(html_path: str) -> list[dict]:
    """Parse formula errors — FIXED multi-instance collection.

    KEY FIX: The original parser only captured the LAST instance per rule when
    badge > 1 because _cur_instance was replaced at the start of each new table
    without first committing the previous one. Fixed by flushing _cur_instance
    into rule["instances"] at the START of each new table (if it has variables).
    """
    from html.parser import HTMLParser

    _FALLBACK: list[dict] = []

    if not html_path or not os.path.isfile(html_path):
        logger.warning("[parse_formula_errors] file not found: %s", html_path)
        return _FALLBACK

    try:
        with open(html_path, "r", encoding="utf-8", errors="replace") as fh:
            raw = fh.read()
    except OSError as exc:
        logger.warning("[parse_formula_errors] cannot read: %s — %s", html_path, exc)
        return _FALLBACK

    class _FormulaParser(HTMLParser):
        def __init__(self) -> None:
            super().__init__(convert_charrefs=True)
            self.rules: list[dict] = []
            self._in_accordion    = False
            self._in_panel        = False
            self._in_panel_body   = False
            self._depth           = 0
            self._cap_label       = False
            self._cap_formula     = False
            self._cap_badge       = False
            self._buf             = ""
            self._cur_rule: dict | None = None
            self._in_table        = False
            self._in_tr           = False
            self._in_cell         = False
            self._is_msghead      = False
            self._is_fv_row       = False
            self._cell_texts: list[str] = []
            self._cur_instance: dict | None = None

        def _attr(self, attrs, name):
            for k, v in attrs:
                if k == name: return v or ""
            return ""

        def _has_class(self, attrs, *cls_names):
            classes = set(self._attr(attrs, "class").split())
            return bool(classes & set(cls_names))

        def _flush_instance(self):
            """Commit _cur_instance to current rule if it has content."""
            if (self._cur_instance is not None
                    and self._cur_rule is not None
                    and self._cur_instance.get("variables")):
                self._cur_rule["instances"].append(self._cur_instance)
            self._cur_instance = None

        def handle_starttag(self, tag, attrs):
            tag = tag.lower()
            if tag == "div":
                div_id = self._attr(attrs, "id")
                if div_id == "accordionFormula":
                    self._in_accordion = True; self._depth = 0; return
                if not self._in_accordion: return
                self._depth += 1
                if self._has_class(attrs, "panel-default") and "panel" in self._attr(attrs, "class"):
                    # Commit any pending rule before starting a new one
                    if self._cur_rule is not None:
                        self._flush_instance()
                        if self._cur_rule.get("rule_name") and (self._cur_rule["instances"] or self._cur_rule.get("error_count", 0) > 0):
                            self.rules.append(self._cur_rule)
                    self._cur_rule = {"rule_name": "", "formula_expression": "", "formula_type": "general", "error_count": 0, "instances": []}
                    self._in_panel = True; return
                if self._has_class(attrs, "panel-collapse") or self._has_class(attrs, "panel-body"):
                    if self._in_panel: self._in_panel_body = True; return
                if self._has_class(attrs, "assertionLabel") and self._in_panel:
                    self._cap_label = True; self._buf = ""; return
                if self._has_class(attrs, "formulaErrorTest") and self._in_panel:
                    self._cap_formula = True; self._buf = ""; return
                cls = self._attr(attrs, "class")
                if "badge" in cls and self._in_panel and not self._in_panel_body:
                    self._cap_badge = True; self._buf = ""
            elif tag == "table" and self._in_panel_body:
                # KEY FIX: flush the PREVIOUS instance before starting a new table
                self._flush_instance()
                self._in_table = True
                self._cur_instance = {"business_message": "", "variables": []}
            elif tag == "tr" and self._in_table:
                self._in_tr = True; self._cell_texts = []
                self._is_msghead = self._has_class(attrs, "msgHead")
                self._is_fv_row  = self._has_class(attrs, "fv") or "fv" in self._attr(attrs, "class").split()
            elif tag in ("td", "th") and self._in_tr:
                self._in_cell = True; self._buf = ""
            elif tag == "br" and self._in_cell:
                self._buf += " "

        def handle_endtag(self, tag):
            tag = tag.lower()
            if tag == "div":
                if not self._in_accordion: return
                if self._cap_label:
                    if self._cur_rule is not None: self._cur_rule["rule_name"] = self._buf.strip()
                    self._cap_label = False; self._buf = ""; return
                if self._cap_formula:
                    if self._cur_rule is not None:
                        expr = self._buf.strip()
                        self._cur_rule["formula_expression"] = expr
                        self._cur_rule["formula_type"] = _classify_formula_type(expr)
                    self._cap_formula = False; self._buf = ""; return
                if self._cap_badge:
                    if self._cur_rule is not None:
                        try: self._cur_rule["error_count"] = int(self._buf.strip())
                        except (ValueError, TypeError): pass
                    self._cap_badge = False; self._buf = ""; return
                self._depth -= 1
                if self._depth <= 0:
                    self._in_accordion = self._in_panel = self._in_panel_body = False
            elif tag == "table" and self._in_table:
                self._flush_instance()
                self._in_table = False
            elif tag in ("td", "th") and self._in_cell:
                self._cell_texts.append(self._buf.strip()); self._in_cell = False; self._buf = ""
            elif tag == "tr" and self._in_tr:
                self._in_tr = False
                cells = self._cell_texts
                if self._is_msghead and cells and self._cur_instance is not None:
                    raw_msg = " ".join(c for c in cells if c).strip()
                    raw_msg = raw_msg.replace("\u00a0", " ").lstrip("▼").strip()
                    raw_msg = re.sub(r'^en\s*:\s*', '', raw_msg, flags=re.IGNORECASE)
                    raw_msg = raw_msg.strip('"').strip("'").strip()
                    self._cur_instance["business_message"] = raw_msg
                elif self._is_fv_row and len(cells) >= 3 and self._cur_instance is not None:
                    var_id  = cells[0].strip() if len(cells) > 0 else ""
                    concept = cells[1].strip() if len(cells) > 1 else ""
                    value   = cells[2].strip() if len(cells) > 2 else ""
                    context = cells[3].strip() if len(cells) > 3 else ""
                    unit    = cells[4].strip() if len(cells) > 4 else ""
                    decimal = cells[5].strip() if len(cells) > 5 else ""
                    if var_id:
                        self._cur_instance["variables"].append({
                            "var":                var_id,
                            "concept":            concept,
                            "concept_label":      _camel_to_words(concept),
                            "value":              value,
                            "context":            context,
                            "context_hint":       _extract_context_hint(context),
                            "context_decomposed": _decompose_context(context),
                            "unit":               unit,
                            "decimal":            decimal,
                        })
                self._cell_texts = []

        def handle_data(self, data):
            if self._cap_label or self._cap_formula or self._cap_badge or self._in_cell:
                self._buf += data

        def finalize(self):
            self._flush_instance()
            if self._cur_rule is not None and self._cur_rule.get("rule_name"):
                if self._cur_rule["instances"] or self._cur_rule.get("error_count", 0) > 0:
                    self.rules.append(self._cur_rule)

    fp = _FormulaParser()
    try:
        fp.feed(raw); fp.finalize()
    except Exception as exc:
        logger.warning("[parse_formula_errors] parse error: %s — %s", html_path, exc)
        return _FALLBACK

    rules = fp.rules
    if not rules:
        rules = _parse_formula_errors_regex_fallback(raw)

    logger.info("[parse_formula_errors] extracted %d rule(s) from: %s", len(rules), html_path)
    return rules


def _parse_formula_errors_regex_fallback(raw: str) -> list[dict]:
    """Regex fallback — also fixed to capture ALL instances per rule."""
    from html.parser import HTMLParser

    class _TextExtractor(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True); self._buf = ""
        def handle_data(self, data): self._buf += data
        def get(self): return self._buf.strip()

    def _strip(html_fragment):
        e = _TextExtractor(); e.feed(html_fragment); return e.get()

    rules: list[dict] = []
    panel_pattern = re.compile(
        r'<div[^>]+id="errorPanel\d+"[^>]*>(.*?)</div>\s*</div>\s*</div>',
        re.DOTALL | re.IGNORECASE,
    )
    for panel_m in panel_pattern.finditer(raw):
        panel_html = panel_m.group(0)
        name_m = re.search(r'class="assertionLabel"[^>]*>(.*?)</div>', panel_html, re.DOTALL | re.IGNORECASE)
        rule_name = _strip(name_m.group(1)) if name_m else ""
        if not rule_name: continue
        formula_m = re.search(r'class="formulaErrorTest"[^>]*>(.*?)</div>', panel_html, re.DOTALL | re.IGNORECASE)
        formula_expr = _strip(formula_m.group(1)) if formula_m else ""
        badge_m = re.search(r'class="badge[^"]*"[^>]*>\s*(\d+)\s*<', panel_html, re.IGNORECASE)
        error_count = int(badge_m.group(1)) if badge_m else 0
        instances: list[dict] = []
        cell_pattern = re.compile(r'<td[^>]*>(.*?)</td>', re.DOTALL | re.IGNORECASE)
        for table_m in re.finditer(r'<table[^>]*>(.*?)</table>', panel_html, re.DOTALL | re.IGNORECASE):
            table_html = table_m.group(1)
            head_m = re.search(r'class="[^"]*msgHead[^"]*"[^>]*>(.*?)</tr>', table_html, re.DOTALL | re.IGNORECASE)
            if not head_m: continue
            raw_msg = _strip(head_m.group(1)).replace("\u00a0", " ").lstrip("▼").strip()
            raw_msg = re.sub(r'^en\s*:\s*', '', raw_msg, flags=re.IGNORECASE).strip('"').strip("'").strip()
            variables: list[dict] = []
            fv_row_pattern = re.compile(r'class="[^"]*\bfv\b[^"]*"[^>]*>(.*?)</tr>', re.DOTALL | re.IGNORECASE)
            for fv_m in fv_row_pattern.finditer(table_html):
                cells = [_strip(c.group(1)) for c in cell_pattern.finditer(fv_m.group(1))]
                if len(cells) >= 3 and cells[0]:
                    concept = cells[1] if len(cells) > 1 else ""
                    context = cells[3] if len(cells) > 3 else ""
                    variables.append({
                        "var":                cells[0],
                        "concept":            concept,
                        "concept_label":      _camel_to_words(concept),
                        "value":              cells[2] if len(cells) > 2 else "",
                        "context":            context,
                        "context_hint":       _extract_context_hint(context),
                        "context_decomposed": _decompose_context(context),
                        "unit":               cells[4] if len(cells) > 4 else "",
                        "decimal":            cells[5] if len(cells) > 5 else "",
                    })
            if variables:
                instances.append({"business_message": raw_msg, "variables": variables})
        if instances or error_count > 0:
            rules.append({
                "rule_name":       rule_name,
                "formula_expression": formula_expr,
                "formula_type":    _classify_formula_type(formula_expr),
                "error_count":     error_count,
                "instances":       instances,
            })
    return rules


def enrich_formula_errors(rules: list[dict]) -> list[dict]:
    enriched_rules = []
    for rule in rules:
        rule  = dict(rule)
        ftype = rule.get("formula_type", "general")
        instances = rule.get("instances", [])
        if ftype == "sum_check":
            rule["instances"] = _compute_sum_discrepancy(instances)
        elif ftype in ("ratio_check", "rounded_equality"):
            rule["instances"] = _compute_ratio_discrepancy(instances)
        enriched_rules.append(rule)
    return enriched_rules


def _extract_missing_fields_from_formula(formula: str) -> list[str]:
    """Extract variable IDs from a presence-check formula."""
    vars_found = re.findall(r'\$V(\d+)', formula, re.IGNORECASE)
    return [f"V{v}" for v in vars_found] if vars_found else []


def _build_formula_llm_payload(rule: dict) -> dict:
    """Build LLM payload including ALL instances, not just the first."""
    ftype     = rule.get("formula_type", "general")
    rule_name = rule.get("rule_name", "")
    instances = rule.get("instances", [])
    formula   = rule.get("formula_expression", "")

    biz_msg = next(
        (inst.get("business_message", "").strip() for inst in instances if inst.get("business_message", "").strip()),
        ""
    )
    biz_msg = re.sub(r'^en\s*:\s*(?:Identity\s*)?', '', biz_msg, flags=re.IGNORECASE).strip('"').strip("'").strip()

    payload: dict = {
        "rule_name":               rule_name,
        "formula_type":            ftype,
        "formula_expression":      formula,
        "business_rule":           biz_msg,
        "total_failing_instances": len(instances),
    }

    if ftype == "presence_check":
        failing_items = []
        for inst in instances:
            vars_by_id = {v["var"]: v for v in inst.get("variables", [])}
            v1 = vars_by_id.get("V1", {})
            if v1:
                failing_items.append({
                    "commodity":      v1.get("value", ""),
                    "concept":        v1.get("concept_label") or v1.get("concept", ""),
                    "context":        v1.get("context_hint", "") or v1.get("context", ""),
                    "missing_fields": _extract_missing_fields_from_formula(formula),
                })
        if failing_items:
            payload["all_failing_instances"] = failing_items

    elif ftype == "sum_check" and instances:
        inst = instances[0]
        lhs  = inst.get("lhs_var") or {}
        rhs  = inst.get("rhs_vars") or []
        unit = inst.get("unit") or lhs.get("unit", "")
        payload.update({
            "total_field":    lhs.get("concept_label") or lhs.get("concept", ""),
            "reported_total": inst.get("reported_total", ""),
            "calculated_sum": inst.get("calculated_sum", ""),
            "difference":     inst.get("difference", ""),
            "unit":           unit,
            "components":     [
                {"label": v.get("concept_label") or v.get("concept", ""), "value": v.get("value", ""), "context": v.get("context_hint", "")}
                for v in rhs if v.get("value")
            ],
        })
        if len(instances) > 1:
            payload["additional_failing_instances"] = [
                {
                    "context":    inst2.get("lhs_var", {}).get("context_hint", "") or (inst2.get("lhs_var") or {}).get("context", ""),
                    "difference": inst2.get("difference", ""),
                }
                for inst2 in instances[1:] if inst2.get("lhs_var")
            ]

    elif ftype in ("ratio_check", "rounded_equality") and instances:
        inst = instances[0]
        v1 = inst.get("lhs_var") or {}; v2 = inst.get("numerator_var") or {}; v3 = inst.get("denominator_var") or {}
        payload.update({
            "result_field":      v1.get("concept_label") or v1.get("concept", ""),
            "reported_value":    inst.get("reported_value", ""),
            "numerator_field":   v2.get("concept_label") or v2.get("concept", ""),
            "numerator_value":   inst.get("numerator_value", ""),
            "numerator_unit":    inst.get("numerator_unit", ""),
            "denominator_field": v3.get("concept_label") or v3.get("concept", ""),
            "denominator_value": inst.get("denominator_value", ""),
            "denominator_unit":  inst.get("denominator_unit", ""),
            "calculated_value":  inst.get("calculated_value", ""),
        })
        if len(instances) > 1:
            payload["additional_failing_instances"] = len(instances) - 1

    else:
        all_inst_data = []
        for inst in instances:
            all_inst_data.append({
                "business_message": inst.get("business_message", ""),
                "variables": [
                    {"label": v.get("concept_label") or v.get("concept", ""), "value": v.get("value", ""), "unit": v.get("unit", ""), "context": v.get("context_hint", "")}
                    for v in inst.get("variables", []) if v.get("value")
                ],
            })
        if all_inst_data:
            payload["all_instances"] = all_inst_data

    return payload


def _fallback_formula_explanation(rule: dict) -> str:
    """
    Evidence-based fallback for formula errors.
    Uses only the parsed payload — no invented field names or assumed values.
    """
    ftype     = rule.get("formula_type", "general")
    instances = rule.get("instances", [])
    rule_name = rule.get("rule_name", "")
 
    # Extract business message from first instance that has one
    biz_msg = next(
        (
            inst.get("business_message", "").strip()
            for inst in instances
            if inst.get("business_message", "").strip()
        ),
        "",
    )
    biz_msg = re.sub(
        r'^en\s*:\s*(?:Identity\s*)?', '', biz_msg, flags=re.IGNORECASE
    ).strip('"').strip("'").strip()
 
    if ftype == "presence_check":
        commodities: list[str] = []
        contexts: list[str] = []
        for inst in instances:
            for v in inst.get("variables", []):
                if v.get("var") == "V1":
                    val = v.get("value", "")
                    if val and val not in commodities:
                        commodities.append(val)
                    ctx_hint = v.get("context_hint", "") or v.get("context", "")
                    if ctx_hint and ctx_hint not in contexts:
                        contexts.append(ctx_hint)
 
        comm_str = (
            ", ".join(f'"{c}"' for c in commodities)
            if commodities
            else "one or more items"
        )
        parts = [f"The business validation failed for {comm_str}."]
        if biz_msg:
            parts.append(biz_msg)
        if contexts:
            ctx_sample = "; ".join(contexts[:3])
            suffix = "..." if len(contexts) > 3 else ""
            parts.append(
                f"The failure was reported for {len(instances)} context(s): {ctx_sample}{suffix}."
            )
        parts.append(
            "Please ensure all required fields are populated for each listed item "
            "before resubmitting."
        )
        return " ".join(parts)
 
    if ftype == "sum_check":
        inst       = instances[0] if instances else {}
        lhs        = inst.get("lhs_var") or {}
        total_lbl  = lhs.get("concept_label") or lhs.get("concept", "the total field")
        unit       = inst.get("unit", "")
        reported   = inst.get("reported_total", "")
        calculated = inst.get("calculated_sum", "")
        diff       = inst.get("difference", "")
 
        parts = [
            f"The reported {total_lbl} does not match the sum of its components."
        ]
        if reported and calculated:
            unit_str = f" {unit}" if unit else ""
            parts.append(
                f"The submitted total is {reported}{unit_str} but the calculated "
                f"sum of components is {calculated}{unit_str} (difference: {diff}{unit_str})."
            )
        if len(instances) > 1:
            parts.append(
                f"This mismatch was reported across {len(instances)} contexts."
            )
        parts.append(
            "Please review each component and ensure they add up to the reported "
            "total before resubmitting."
        )
        return " ".join(parts)
 
    if ftype in ("ratio_check", "rounded_equality"):
        inst   = instances[0] if instances else {}
        v1     = inst.get("lhs_var") or {}
        v2     = inst.get("numerator_var") or {}
        v3     = inst.get("denominator_var") or {}
        lbl_v1 = v1.get("concept_label") or v1.get("concept", "the reported value")
        lbl_v2 = v2.get("concept_label") or v2.get("concept", "the numerator")
        lbl_v3 = v3.get("concept_label") or v3.get("concept", "the denominator")
        rep    = inst.get("reported_value", "")
        calc   = inst.get("calculated_value", "")
 
        parts = [
            f"The reported {lbl_v1} does not match the value calculated from "
            f"the submitted data."
        ]
        if rep and calc:
            parts.append(
                f"The submitted value is {rep} but the calculated value based on "
                f"{lbl_v2} and {lbl_v3} is {calc}."
            )
        parts.append(
            f"Please verify {lbl_v1}, {lbl_v2}, and {lbl_v3} before resubmitting."
        )
        return " ".join(parts)
 
    # General fallback
    if biz_msg:
        return (
            f"A business validation check failed: {biz_msg} "
            f"Please review and correct before resubmitting."
        )
    rule_ref = f" '{rule_name}'" if rule_name else ""
    return (
        f"The validation rule{rule_ref} failed. "
        f"Please review the reported figures before resubmitting."
    )
 
 
def explain_formula_errors(rules: list[dict]) -> list[dict]:
    """
    Explain formula errors — evidence-only prompts.
    The LLM must not claim fields are empty unless the payload proves they are.
    ALL failing instances are included in the payload.
    """
    import json as _json
    import httpx as _httpx
 
    if not rules:
        return rules
 
    ollama_base = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    model       = os.getenv("OLLAMA_MODEL", "llama3.1:latest")
    timeout     = float(os.getenv("OLLAMA_TIMEOUT", "180"))
    keep_alive  = os.getenv("OLLAMA_KEEP_ALIVE", "30m")
 
    logger.info(
        "[STATUS_FLOW] Starting FORMULA_ERROR LLM enrichment, rules=%d", len(rules)
    )
    start   = time.perf_counter()
    results: list[dict] = []
 
    for rule in rules:
        rule           = dict(rule)
        ftype          = rule.get("formula_type", "general")
        rule_name      = rule.get("rule_name", "")
        payload        = _build_formula_llm_payload(rule)  # existing function — unchanged
        instance_count = len(rule.get("instances", []))
 
        # ------------------------------------------------------------------
        # Type-specific instruction — describes what IS in the payload,
        # not what the LLM should assume
        # ------------------------------------------------------------------
        if ftype == "sum_check":
            type_instruction = (
                "This is a SUM CHECK error. The payload contains 'reported_total', "
                "'calculated_sum', 'difference', and 'components'. "
                "State that the reported total does not equal the sum of the components. "
                "Quote 'reported_total' and 'calculated_sum' if they are present in the payload. "
                "Do not invent component values that are not in the payload."
            )
        elif ftype in ("ratio_check", "rounded_equality"):
            type_instruction = (
                "This is a RATIO or PERCENTAGE CHECK error. The payload contains "
                "'result_field', 'numerator_field', 'denominator_field', "
                "'reported_value', and 'calculated_value'. "
                "State that the reported value does not match the calculated value. "
                "Quote 'reported_value' and 'calculated_value' if present. "
                "Do not claim the formula or arithmetic is wrong beyond what the payload states."
            )
        elif ftype == "presence_check":
            type_instruction = (
                "This is a MANDATORY FIELD CHECK error. The payload contains "
                "'all_failing_instances' which lists every commodity and context "
                "where the check failed, and 'business_rule' which is the exact "
                "rule text from the validator. "
                "YOU MUST mention EVERY commodity listed in 'all_failing_instances'. "
                "Use the 'business_rule' text verbatim to explain what is required. "
                "Do NOT claim specific fields are empty unless the business_rule "
                "explicitly states which fields are required."
            )
        else:
            type_instruction = (
                "Explain the error using only the variable names, values, and "
                "business message in the payload. "
                "If 'all_instances' is present, address each one. "
                "Do not infer causes beyond what the payload states."
            )
 
        multi_instance_note = ""
        if instance_count > 1:
            multi_instance_note = (
                f"\nThis rule failed for {instance_count} separate instances. "
                "Address ALL of them — do not limit the explanation to the first instance."
            )
 
        prompt = (
            "You are a regulatory reporting assistant explaining a business validation "
            "failure to a business user.\n\n"
            "The following JSON contains all relevant information about the failing rule. "
            "These fields are the ONLY source of truth.\n\n"
            f"{_json.dumps(payload, indent=2, ensure_ascii=False)}\n\n"
            f"{type_instruction}\n"
            f"{multi_instance_note}\n\n"
            "Write ONE plain-English paragraph (maximum 120 words).\n\n"
            "STRICT RULES:\n"
            "1. Use ONLY values from the JSON. Never invent commodity names, "
            "   field names, or values not present.\n"
            "2. Use business field names — never V1, V2, V3, etc.\n"
            "3. If 'total_failing_instances' > 1, name every failing item explicitly "
            "   using the values in 'all_failing_instances'.\n"
            "4. Do NOT claim a field is empty or missing unless 'business_rule' or "
            "   'business_message' explicitly states which field is required and absent.\n"
            "5. Do not mention formulas, XBRL, taxonomy, schema, or technical details.\n"
            "6. Do not perform arithmetic yourself.\n"
            "7. Do not use: 'it appears', 'seems', 'may be', 'possibly', 'likely'.\n"
            "8. No bullet points, markdown, or headings.\n"
            "9. End with: 'The report cannot be submitted until this is corrected.'\n\n"
            "Return only the explanation paragraph."
        )
 
        api_payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a regulatory reporting assistant. "
                        "Explain business validation failures in plain English using "
                        "ONLY the JSON provided. "
                        "When multiple instances fail, address ALL of them. "
                        "NEVER claim a field is empty or missing unless the "
                        "business_rule or business_message explicitly states it. "
                        "Never use V1, V2, V3. Never invent values. "
                        "One plain-text paragraph. No markdown."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "keep_alive": keep_alive,
            "options": {"temperature": 0.0, "num_predict": 300},
        }
 
        explanation = ""
        try:
            with _httpx.Client(timeout=timeout) as client:
                resp = client.post(f"{ollama_base}/api/chat", json=api_payload)
                resp.raise_for_status()
            explanation = resp.json()["message"]["content"].strip()
            logger.info(
                "[FORMULA_LLM] rule=%r  explanation=%r", rule_name, explanation[:80]
            )
        except Exception as exc:
            logger.warning(
                "[FORMULA_LLM] rule=%r  LLM failed: %s — using fallback", rule_name, exc
            )
 
        if not explanation or len(explanation) < 15:
            explanation = _fallback_formula_explanation(rule)
 
        rule["explanation"] = explanation
        results.append(rule)
 
    logger.info(
        "[STATUS_FLOW] FORMULA_ERROR enrichment complete — rules=%d  elapsed=%.3fs",
        len(results),
        time.perf_counter() - start,
    )
    return results


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4: ERROR CATEGORY CLASSIFIER
# ══════════════════════════════════════════════════════════════════════════════

def _classify_error_category(html_path: str) -> str:
    """Classify the primary error category from the error HTML.

    NOTE: A single file can contain MULTIPLE categories. This function
    returns the PRIMARY category for legacy routing only.
    count_errors_by_category() handles multi-category parsing independently.

    Returns one of:
        "formula_error"  — iDeal output with a non-empty FORMULA_ERROR accordion
        "dimensional"    — DIMENSION panel badge > 0 OR xbrldie: markers present
        "xbrl_schema"    — structured table errors (BTDetails / 4000-series)
        "unknown"        — fallback, treated like xbrl_schema
    """
    if not html_path or not os.path.isfile(html_path):
        return "unknown"

    try:
        with open(html_path, "r", encoding="utf-8", errors="replace") as fh:
            head = fh.read(8192)
    except OSError:
        return "unknown"

    # Check dimensional FIRST using badge (not mere token presence)
    dim_badge = _read_dimension_badge_from_html(head)
    if dim_badge > 0:
        return "dimensional"

    # xbrldie markers in the text are a reliable legacy signal
    if "xbrldie" in head.lower() or "DimensionallyInvalid" in head:
        return "dimensional"

    accordion_has_content = bool(
        re.search(r"""id=["']accordionFormula["'][^>]*>\s*<div""", head)
    )
    if accordion_has_content:
        return "formula_error"

    if "accordionFormula" in head:
        try:
            with open(html_path, "r", encoding="utf-8", errors="replace") as fh:
                extended = fh.read(65536)
            dim_badge_ext = _read_dimension_badge_from_html(extended)
            if dim_badge_ext > 0:
                return "dimensional"
            if "xbrldie" in extended.lower() or "DimensionallyInvalid" in extended:
                return "dimensional"
            if re.search(r"""id=["']accordionFormula["'][^>]*>\s*<div""", extended):
                return "formula_error"
        except OSError:
            pass

    tokens = set(re.findall(r"\b([A-Z][A-Z0-9_\-]{3,})\b", head))

    if "DIMENSION" in tokens:
        return "dimensional"

    if "XBRL_SCHEMA" in tokens or tokens & {
        "FORMULA_ERROR", "QUALITY-CHECK_ERROR", "SPECIFICATION_ERROR"
    }:
        return "xbrl_schema"

    return "unknown"


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5: XBRL SCHEMA SUPPORT UTILITIES
# ══════════════════════════════════════════════════════════════════════════════

def _extract_error_summary_from_xml(error_file_path: str) -> dict:
    import xml.etree.ElementTree as ET
    _FALLBACK = {"messages": ["Detailed error information could not be extracted."]}
    if not error_file_path or not os.path.isfile(error_file_path):
        return _FALLBACK
    try:
        tree = ET.parse(error_file_path); root = tree.getroot()
    except (ET.ParseError, OSError) as exc:
        logger.warning("[extract_error_summary] XML error: %s — %s", error_file_path, exc)
        return _FALLBACK
    messages: list[str] = []; seen: set[str] = set()
    for el in root.iter("ErrorMessage"):
        msg = (el.text or "").strip()
        if msg and msg not in seen:
            seen.add(msg); messages.append(msg)
            if len(messages) >= 5: break
    return {"messages": messages} if messages else _FALLBACK


def _extract_error_summary_from_html(error_file_path: str) -> dict:
    _FALLBACK = {"messages": ["Detailed error information could not be extracted."]}
    errors = parse_backtrack_html_errors(error_file_path)
    if not errors:
        return _FALLBACK
    messages: list[str] = []; seen: set[str] = set()
    for err in errors:
        msg = err.get("message") or err.get("error_message", "")
        if not msg:
            parts = []
            if err.get("errorType"): parts.append(err["errorType"].replace("_", " ").title())
            if err.get("rule"):     parts.append(f"rule: {err['rule']}")
            if err.get("cellCode"): parts.append(f"cell {err['cellCode']}")
            actual = err.get("actualValue") or err.get("enteredValue", "")
            if actual: parts.append(f"entered: {actual}")
            if err.get("expectedValue"): parts.append(f"expected: {err['expectedValue']}")
            msg = " — ".join(parts) if parts else str(err)
        msg = msg.strip()
        if msg and msg not in seen:
            seen.add(msg); messages.append(msg)
            if len(messages) >= 5: break
    return {"messages": messages} if messages else _FALLBACK


def extract_error_summary(error_file_path: str) -> dict:
    _FALLBACK = {"messages": ["Detailed error information could not be extracted."]}
    if not error_file_path: return _FALLBACK
    ext = os.path.splitext(error_file_path)[1].lower()
    if ext == ".html": return _extract_error_summary_from_html(error_file_path)
    if ext == ".xml":  return _extract_error_summary_from_xml(error_file_path)
    return _FALLBACK


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6: ERROR COUNT BY CATEGORY
# ══════════════════════════════════════════════════════════════════════════════

_SUPPORTED_ERROR_CATEGORIES = frozenset({"formula_error", "dimensional", "xbrl_schema"})


def count_errors_by_category(error_file_path: str) -> dict:
    """Parse the error file and return counts per supported category.

    Each category is parsed INDEPENDENTLY — a file can have nonzero counts
    in multiple categories simultaneously.

    DIMENSION gate: the DIMENSION panel badge is read first; if it is 0
    the dimensional parser is skipped entirely (no false positives).
    """
    result: dict = {"error_file_path": error_file_path}

    if not error_file_path or not os.path.isfile(error_file_path):
        logger.warning("[count_errors_by_category] file not found: %s", error_file_path)
        return result

    ext = os.path.splitext(error_file_path)[1].lower()

    if ext != ".html":
        try:
            import xml.etree.ElementTree as ET
            root = ET.parse(error_file_path).getroot()
            count = len(root.findall("ErrorMessage"))
            if count:
                result["xbrl_schema"] = count
        except Exception as exc:
            logger.warning("[count_errors_by_category] XML parse failed: %s", exc)
        return result

    try:
        with open(error_file_path, "r", encoding="utf-8", errors="replace") as fh:
            raw_html = fh.read()
    except OSError as exc:
        logger.warning("[count_errors_by_category] cannot read HTML: %s — %s", error_file_path, exc)
        return result

    html_category = _classify_error_category(error_file_path)
    result["html_category"] = html_category
    logger.info(
        "[count_errors_by_category] html_category=%s path=%s", html_category, error_file_path
    )

    # ── FORMULA_ERROR ──────────────────────────────────────────────────────────
    try:
        rules = parse_formula_errors(error_file_path)
        total = sum(r.get("error_count", len(r.get("instances", []))) for r in rules)
        if total:
            result["formula_error"] = total
    except Exception as exc:
        logger.warning("[count_errors_by_category] formula parse failed: %s", exc)

    # ── DIMENSION_ERROR — badge-gated ─────────────────────────────────────────
    try:
        dim_badge = _read_dimension_badge_from_html(raw_html)
        logger.info(
            "[count_errors_by_category] DIMENSION badge=%d path=%s",
            dim_badge, error_file_path,
        )
        if dim_badge > 0:
            dim_errors = parse_dimensional_html_errors(error_file_path)
            logger.info(
                "[count_errors_by_category] dimensional parse returned %d entries",
                len(dim_errors),
            )
            if dim_errors:
                result["dimensional"] = len(dim_errors)
            else:
                result["dimensional"] = dim_badge
        else:
            logger.info(
                "[count_errors_by_category] DIMENSION badge=0 — skipping dimensional parser"
            )
    except Exception as exc:
        logger.warning("[count_errors_by_category] dimensional parse failed: %s", exc)

    # ── XBRL_SCHEMA_ERROR ──────────────────────────────────────────────────────
    try:
        schema_errors = parse_backtrack_html_errors(error_file_path)
        xbrl_schema_count = sum(
            1 for e in schema_errors
            if (e.get("errorType") or "").strip().upper().replace(" ", "_").replace("-", "_")
            in ("XBRL_SCHEMA", "XBRL_SCHEMA_ERROR")
        )
        if xbrl_schema_count:
            result["xbrl_schema"] = xbrl_schema_count
    except Exception as exc:
        logger.warning("[count_errors_by_category] backtrack parse failed: %s", exc)

    logger.info("[count_errors_by_category] result=%r", result)
    return result


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 7: ON-DEMAND EXPLAIN BY CATEGORY
# ══════════════════════════════════════════════════════════════════════════════

_MAX_EXPLAIN = 5


def explain_errors_by_category(error_file_path: str, category: str) -> list[dict]:
    """Parse and explain up to _MAX_EXPLAIN errors with full context and root-cause linking.

    Parameters
    ----------
    error_file_path : str
        Absolute path to the error HTML/XML file.
    category : str
        One of "formula_error", "xbrl_schema", "dimensional".

    Returns
    -------
    list[dict]
        List of enriched + explained error dicts, each tagged with
        ``_error_category``.  Returns [] on any failure.
    """
    if not error_file_path or not os.path.isfile(error_file_path):
        logger.warning("[explain_errors_by_category] file not found: %s", error_file_path)
        return []

    if category not in _SUPPORTED_ERROR_CATEGORIES:
        logger.warning("[explain_errors_by_category] unsupported category: %s", category)
        return []

    logger.info(
        "[explain_errors_by_category] START category=%s path=%s", category, error_file_path
    )
    start = time.perf_counter()

    try:
        if category == "formula_error":
            raw_rules = parse_formula_errors(error_file_path)
            trimmed   = raw_rules[:_MAX_EXPLAIN]
            enriched  = enrich_formula_errors(trimmed)
            explained = explain_formula_errors(enriched)
            for rule in explained:
                rule["_error_category"] = "formula_error"
            logger.info(
                "[explain_errors_by_category] formula done rules=%d elapsed=%.3fs",
                len(explained), time.perf_counter() - start,
            )
            return explained

        elif category == "dimensional":
            errors    = parse_dimensional_html_errors(error_file_path)
            trimmed   = errors[:_MAX_EXPLAIN]
            explained = explain_dimensional_errors(trimmed)
            for err in explained:
                err["_error_category"] = "dimensional"
            logger.info(
                "[explain_errors_by_category] dimensional done count=%d elapsed=%.3fs",
                len(explained), time.perf_counter() - start,
            )
            return explained

        else:  # xbrl_schema
            errors = parse_backtrack_html_errors(error_file_path)
            _XBRL_SCHEMA_LABELS = {"XBRL_SCHEMA", "XBRL SCHEMA", "XBRL_SCHEMA_ERROR"}
            xbrl_only = [
                e for e in errors
                if (e.get("errorType") or "").strip().upper() in _XBRL_SCHEMA_LABELS
            ]
            trimmed = (xbrl_only or errors)[:_MAX_EXPLAIN]

            # Root-cause analysis: parse other categories for downstream linkage
            try:
                formula_rules = parse_formula_errors(error_file_path)
                dim_errors    = parse_dimensional_html_errors(error_file_path)
                trimmed       = _build_root_cause_analysis(trimmed, formula_rules, dim_errors)
            except Exception as exc:
                logger.warning("[explain_errors_by_category] root-cause analysis failed: %s", exc)

            enriched = explain_validation_errors(trimmed)
            for err in enriched:
                err.setdefault("_error_category", "xbrl_schema")
            logger.info(
                "[explain_errors_by_category] xbrl_schema done count=%d elapsed=%.3fs",
                len(enriched), time.perf_counter() - start,
            )
            return enriched

    except Exception as exc:
        logger.error(
            "[explain_errors_by_category] FAILED category=%s: %s", category, exc
        )
        return []


def explain_errors_by_category_for_form(
    error_file_path: str, category: str, form_id: str = ""
) -> list[dict]:
    """Like explain_errors_by_category but applies 4000-series tag for xbrl_schema."""
    results = explain_errors_by_category(error_file_path, category)

    if category == "xbrl_schema" and form_id:
        return_id    = _get_return_id_for_form(form_id)
        category_tag = "xbrl_schema_4000" if _is_4000_series(form_id) else "xbrl_schema_other"
        for err in results:
            err["_error_category"] = category_tag

    return results


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 8: MAIN ERROR INFO ROUTER
# ══════════════════════════════════════════════════════════════════════════════

def _get_error_counts(code: int, dl: dict) -> dict:
    """Return error category counts for a failed status result. No LLM invoked."""
    if code not in _FAILED_STATUSES:
        return {}
    path = dl.get("error_file_path", "")
    if not path:
        return {}
    return count_errors_by_category(path)


def _enrich_with_error_messages(code: int, dl: dict) -> list[str]:
    if code not in _FAILED_STATUSES: return []
    path = dl.get("error_file_path", "")
    if not path: return []
    return extract_error_summary(path).get("messages", [])


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 9: REPORT SEARCH / LOOKUP UTILITIES
# ══════════════════════════════════════════════════════════════════════════════

def _normalise(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[_()/\-]", " ", s)
    s = re.sub(r"[^a-z0-9 ]", "", s)
    s = re.sub(r" +", " ", s)
    return s.strip()


def _normalised_returns() -> tuple[tuple[str, str, str, dict], ...]:
    if _norm_cache.loaded_at < _returns_cache.loaded_at:
        _norm_cache._data = None
    cached = _norm_cache.get()
    if cached is not None:
        return cached
    result = tuple(
        (_normalise(r.get("Name", "")), _normalise(r.get("ReturnId", "")), _normalise(r.get("AltName", "")), r)
        for r in _parse_returns() if r.get("Name", "")
    )
    return _norm_cache.set(result)


def find_matching_reports(user_input: str) -> list[dict]:
    needle = _normalise(user_input)
    if not needle: return []
    quads = _normalised_returns()
    from rapidfuzz import fuzz as _fuzz

    def _dedup(lst):
        seen: set[str] = set(); out = []
        for r in lst:
            key = r.get("Name", "") + "|" + r.get("Id", "")
            if key not in seen: seen.add(key); out.append(r)
        return out

    exact_rid = [r for (_, nrid, _, r) in quads if nrid and nrid == needle]
    if exact_rid: return _dedup(exact_rid)
    exact_name = [r for (nname, _, _, r) in quads if nname and nname == needle]
    if exact_name: return _dedup(exact_name)
    exact_alt = [r for (_, _, nalt, r) in quads if nalt and nalt == needle]
    if exact_alt: return _dedup(exact_alt)
    partial_name = [r for (nname, _, _, r) in quads if nname and (needle in nname or nname in needle)]
    if partial_name: return _dedup(partial_name)
    partial_alt = [r for (_, _, nalt, r) in quads if nalt and (needle in nalt or nalt in needle)]
    if partial_alt: return _dedup(partial_alt)
    partial_rid = [r for (_, nrid, _, r) in quads if nrid and (needle in nrid or nrid in needle)]
    if partial_rid: return _dedup(partial_rid)

    tokens = [t for t in needle.split() if len(t) >= 2]
    if tokens:
        all_name = [r for (nname, _, _, r) in quads if nname and all(t in nname for t in tokens)]
        if all_name: return _dedup(all_name)
        all_alt = [r for (_, _, nalt, r) in quads if nalt and all(t in nalt for t in tokens)]
        if all_alt: return _dedup(all_alt)

        _WW_THRESHOLD = 40; n_tok = len(tokens)
        scored: list[tuple[int, dict]] = []; seen_keys: set[str] = set()
        for (nname, nrid, nalt, r) in quads:
            name_words = set(nname.split()) if nname else set()
            alt_words  = set(nalt.split())  if nalt  else set()
            name_ww  = sum(1 for t in tokens if t in name_words)
            alt_ww   = sum(1 for t in tokens if t in alt_words)
            name_sub = sum(1 for t in tokens if nname and t in nname)
            alt_sub  = sum(1 for t in tokens if nalt  and t in nalt)
            rid_sub  = sum(1 for t in tokens if nrid  and t in nrid)
            if not (name_ww or alt_ww or name_sub or alt_sub or rid_sub): continue
            score = 0
            if   name_ww == n_tok: score += 80
            elif name_ww > 0:      score += 40
            elif name_sub == n_tok: score += 30
            elif name_sub > 0:     score += 10
            if   alt_ww == n_tok:  score += 70
            elif alt_ww > 0:       score += 35
            elif alt_sub == n_tok: score += 25
            elif alt_sub > 0:      score +=  8
            if rid_sub > 0:        score +=  5
            score += max(_fuzz.partial_ratio(needle, nname) if nname else 0, _fuzz.partial_ratio(needle, nalt) if nalt else 0) // 4
            key = r.get("Name", "") + "|" + r.get("Id", "")
            if key not in seen_keys: seen_keys.add(key); scored.append((score, r))
        if scored:
            scored.sort(key=lambda x: x[0], reverse=True)
            best = scored[0][0]
            if best >= _WW_THRESHOLD: return [r for s, r in scored if s >= _WW_THRESHOLD]
            return [r for _, r in scored]

    _FUZZY_CUTOFF = 72; fuzzy_scored: list[tuple[int, dict]] = []; fuzzy_seen: set[str] = set()
    for (nname, nrid, nalt, r) in quads:
        best_fuzz = max(_fuzz.partial_ratio(needle, nname) if nname else 0, _fuzz.partial_ratio(needle, nalt) if nalt else 0)
        if best_fuzz >= _FUZZY_CUTOFF:
            key = r.get("Name", "") + "|" + r.get("Id", "")
            if key not in fuzzy_seen: fuzzy_seen.add(key); fuzzy_scored.append((best_fuzz, r))
    if fuzzy_scored:
        fuzzy_scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in fuzzy_scored]
    return []


def fuzzy_report_suggestions(user_input: str, n: int = 5, cutoff: float = 0.35) -> list[str]:
    from rapidfuzz import fuzz, process as rf_process
    needle = _normalise(user_input)
    if not needle: return []
    norm_to_orig = {norm_name: r.get("Name", "") for (norm_name, _, _, r) in _normalised_returns()}
    matches = rf_process.extract(needle, list(norm_to_orig.keys()), scorer=fuzz.partial_ratio, limit=n, score_cutoff=cutoff * 100)
    return [norm_to_orig[m[0]] for m in matches if norm_to_orig.get(m[0])]


def get_instances_by_form_id(form_id: str) -> list[dict]:
    fid = str(form_id).strip()
    all_rows = _parse_instances()
    matches  = [r for r in all_rows if r.get("FormId", "").strip() == fid]
    logger.debug("[report_lookup] get_instances_by_form_id(form_id=%r): total=%d matched=%d", fid, len(all_rows), len(matches))
    return matches


def get_available_dates(form_id: str) -> list[str]:
    seen: set[str] = set(); unique: list[str] = []
    for r in get_instances_by_form_id(form_id):
        d = r.get("ReportingDate", "").strip()
        if d and d not in seen: seen.add(d); unique.append(d)
    def _key(d):
        try: return datetime.strptime(d, "%d-%b-%Y")
        except ValueError: return datetime.min
    unique.sort(key=_key, reverse=True)
    return unique


def _get_runs_for_date(form_id: str, reporting_date: str) -> list[dict]:
    rows = [r for r in get_instances_by_form_id(form_id) if r.get("ReportingDate", "").strip() == reporting_date]
    rows.sort(key=_dtc_sort_key)
    return rows


def map_status(code: int) -> str:
    return _STATUS_LABELS.get(code, "Unknown")


def _dtc_sort_key(r: dict) -> datetime:
    try: return datetime.strptime(r.get("DTC", ""), "%d-%b-%Y %I:%M:%S %p")
    except ValueError: return datetime.min


def _safe_status(row: dict) -> int:
    try: return int(row.get("Status", -1))
    except (ValueError, TypeError): return -1


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 10: FILE DOWNLOAD HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def build_render_file_path(form_id: str, filename: str) -> str:
    return os.path.join(_RENDER_BASE_DIR, os.path.basename(form_id), os.path.basename(filename))

def build_error_file_path(form_id: str, filename: str) -> str:
    return os.path.join(_INSTANCE_BASE_DIR, os.path.basename(form_id), os.path.basename(filename))

def file_exists(path: str) -> bool:
    return os.path.isfile(path)

def _get_return_id_for_form(form_id: str) -> str:
    fid = str(form_id).strip()
    for r in _parse_returns():
        logger.info("Return attrs: %r", dict(r))
        if r.get("Id", "").strip() == fid: return r.get("ReturnId", "").strip()
    return ""

def _is_4000_series(return_id: str) -> bool:
    """Return True if the form Id is in 4000–4999.
    For this system, the Id attribute (e.g. '4046') is the 4000-series indicator,
    NOT the ReturnId (e.g. 'R162').
    """
    try:
        return 4000 <= int(str(return_id).strip()) <= 4999
    except (ValueError, TypeError):
        return False


def _get_download_info(row: dict, form_id: str) -> dict:
    code = _safe_status(row)

    def _try_render():
        path_str = row.get("RenderedExcelDocPath", "").strip()
        if not path_str: return None
        filename = os.path.basename(path_str)
        if not filename: return None
        full_path = build_render_file_path(form_id, filename)
        if file_exists(full_path):
            return {"download_url": f"/download-file?form_id={form_id}&type=render&filename={filename}", "download_label": "Download Render File", "status_note": ""}
        return {"download_url": "", "download_label": "", "status_note": "Render file not found."}

    def _try_error():
        path_str = row.get("ErrorDocPath", "").strip()
        if not path_str: return None
        filename = os.path.basename(path_str)
        if not filename: return None
        full_path = build_error_file_path(form_id, filename)
        if file_exists(full_path):
            return {"download_url": f"/download-file?form_id={form_id}&type=error&filename={filename}", "download_label": "Download Error File", "status_note": "", "error_file_path": full_path}
        return {"download_url": "", "download_label": "", "status_note": "Error file not found."}

    if code in _FAILED_STATUSES:
        result = _try_error()
        return result if result is not None else {"download_url": "", "download_label": "", "status_note": ""}
    if code in _SUCCESS_STATUSES:
        result = _try_render()
        return result if result is not None else {"download_url": "", "download_label": "", "status_note": ""}
    result = _try_render()
    if result is not None: return result
    result = _try_error()
    return result if result is not None else {"download_url": "", "download_label": "", "status_note": ""}


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 11: INSTANCE SELECTION HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _fmt_instance_label(dtc: str, reporting_date: str) -> str:
    return f"Generated On: {dtc} | Reporting Date: {reporting_date}"


def get_available_instances(form_id: str) -> list[dict]:
    rows = list(get_instances_by_form_id(form_id))
    rows.sort(key=_dtc_sort_key, reverse=True)
    return [
        {
            "dtc":            r.get("DTC", "").strip(),
            "reporting_date": r.get("ReportingDate", "").strip(),
            "status":         r.get("Status", "").strip(),
            "label":          _fmt_instance_label(r.get("DTC", "").strip(), r.get("ReportingDate", "").strip()),
        }
        for r in rows if r.get("DTC", "").strip() or r.get("ReportingDate", "").strip()
    ]


def get_instance_by_dtc(form_id: str, dtc: str, return_name: str) -> dict:
    rows = get_instances_by_form_id(form_id); dtc_clean = dtc.strip()
    row  = next((r for r in rows if r.get("DTC", "").strip() == dtc_clean), None)
    if not row:
        return {
            "type": "date_not_found",
            "message": f"No instance found for DTC '{dtc_clean}'.",
            "form_id": form_id,
            "return_name": return_name,
            "available_instances": get_available_instances(form_id),
        }
    code = _safe_status(row)
    dl   = _get_download_info(row, form_id)
    error_category_counts = _get_error_counts(code, dl)

    # ── 4000-series gate ──────────────────────────────────────────────────────
    return_id = _get_return_id_for_form(form_id)
    is_4000 = _is_4000_series(form_id)
    logger.info("DEBUG form_id=%r is_4000=%r", form_id, is_4000)


    return {
        "type":                   "final",
        "report_name":            return_name,
        "reporting_date":         row.get("ReportingDate", "").strip(),
        "dtc":                    row.get("DTC", "").strip(),
        "status":                 map_status(code),
        "status_code":            code,
        "download_url":           dl["download_url"],
        "download_label":         dl["download_label"],
        "status_note":            dl["status_note"],
        "error_category_counts":  error_category_counts,
        "is_4000_series":         is_4000,          # ← NEW
        "error_messages":         [],
        "error_details":          [],
    }


def get_instance_by_dtc_fast(form_id: str, dtc: str, return_name: str) -> dict:
    rows = get_instances_by_form_id(form_id); dtc_clean = dtc.strip()
    row  = next((r for r in rows if r.get("DTC", "").strip() == dtc_clean), None)
    if not row:
        return {
            "type": "date_not_found",
            "message": f"No instance found for DTC '{dtc_clean}'.",
            "form_id": form_id,
            "return_name": return_name,
            "available_instances": get_available_instances(form_id),
        }
    code = _safe_status(row)
    dl   = _get_download_info(row, form_id)
    error_category_counts = _get_error_counts(code, dl)

    # ── 4000-series gate ──────────────────────────────────────────────────────
    is_4000 = _is_4000_series(form_id)

    return {
        "type":                  "final",
        "report_name":           return_name,
        "reporting_date":        row.get("ReportingDate", "").strip(),
        "dtc":                   row.get("DTC", "").strip(),
        "status":                map_status(code),
        "status_code":           code,
        "error_category_counts": error_category_counts,
        "is_4000_series":        is_4000,          # ← NEW
        "download_url":          dl["download_url"],
        "download_label":        dl["download_label"],
        "status_note":           dl["status_note"],
        "error_messages":        [],
        "error_details":         [],
    }


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 12: STATUS RESULT BUILDERS
# ══════════════════════════════════════════════════════════════════════════════

def _build_status_result(form_id: str, ret_name: str, instances: list[dict]) -> dict:
    sorted_rows = sorted(instances, key=_dtc_sort_key, reverse=True)
    latest_row  = sorted_rows[0]
    code        = _safe_status(latest_row)
    dl          = _get_download_info(latest_row, form_id)
    current_dtc = latest_row.get("DTC", "").strip()
    rep_date    = latest_row.get("ReportingDate", "").strip()
    logger.info("[_build_status_result] form_id=%r DTC=%r Date=%r Status=%r", form_id, current_dtc, rep_date, map_status(code))
    all_instances   = get_available_instances(form_id)
    other_instances = [i for i in all_instances if i["dtc"] != current_dtc]

    _t = time.monotonic()
    error_category_counts = _get_error_counts(code, dl)
    logger.info("[STATUS_FLOW] error count duration=%.3fs counts=%r", time.monotonic() - _t, error_category_counts)

    # ── 4000-series gate ──────────────────────────────────────────────────────
    return_id       = _get_return_id_for_form(form_id)
    is_4000         = _is_4000_series(form_id)
    logger.info("[_build_status_result] form_id=%r return_id=%r is_4000_series=%r", form_id, return_id, is_4000)

    base = {
        "report_name":           ret_name,
        "reporting_date":        rep_date,
        "status":                map_status(code),
        "status_code":           code,
        "form_id":               form_id, 
        "download_url":          dl["download_url"],
        "download_label":        dl["download_label"],
        "status_note":           dl["status_note"],
        "error_category_counts": error_category_counts,
        "is_4000_series":        is_4000,          # ← NEW
        "error_messages":        [],
        "error_details":         [],
    }
    if other_instances:
        return {**base, "type": "latest_with_ask", "form_id": form_id, "return_name": ret_name,
                "run_time": current_dtc, "other_instances": other_instances}
    return {**base, "type": "final", "dtc": current_dtc}


def _build_status_result_fast(form_id: str, ret_name: str, instances: list[dict]) -> dict:
    sorted_rows = sorted(instances, key=_dtc_sort_key, reverse=True)
    latest_row  = sorted_rows[0]
    code        = _safe_status(latest_row)
    dl          = _get_download_info(latest_row, form_id)
    current_dtc = latest_row.get("DTC", "").strip()
    rep_date    = latest_row.get("ReportingDate", "").strip()
    all_instances   = get_available_instances(form_id)
    other_instances = [i for i in all_instances if i["dtc"] != current_dtc]

    error_category_counts = _get_error_counts(code, dl)

    # ── 4000-series gate ──────────────────────────────────────────────────────
    return_id = _get_return_id_for_form(form_id)
    logger.info("DEBUG form_id=%r return_id=%r is_4000=%r", form_id, return_id, _is_4000_series(return_id))
    is_4000   = _is_4000_series(form_id)
    logger.info("[_build_status_result_fast] form_id=%r return_id=%r is_4000_series=%r", form_id, return_id, is_4000)

    base = {
        "report_name":           ret_name,
        "form_id":               form_id,
        "reporting_date":        rep_date,
        "status":                map_status(code),
        "status_code":           code,
        "form_id":               form_id, 
        "run_time":              current_dtc,
        "download_url":          dl["download_url"],
        "download_label":        dl["download_label"],
        "status_note":           dl["status_note"],
        "error_category_counts": error_category_counts,
        "is_4000_series":        is_4000,          # ← NEW
        "error_messages":        [],
        "error_details":         [],
    }
    if other_instances:
        return {**base, "type": "latest_with_ask", "return_name": ret_name, "other_instances": other_instances}
    return {**base, "type": "final"}


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 13: PUBLIC ENTRY POINTS
# ══════════════════════════════════════════════════════════════════════════════

def get_report_status_exact_fast(report_name: str) -> dict:
    returns = _parse_returns()
    match = next((r for r in returns if r.get("Name", "").strip() == report_name.strip()), None)
    if not match:
        match = next((r for r in returns if r.get("Name", "").strip().lower() == report_name.strip().lower()), None)
    if not match:
        return {"type": "error", "message": f"Report '{report_name}' not found."}
    form_id = match.get("Id", "").strip(); ret_name = match.get("Name", report_name)
    instances = get_instances_by_form_id(form_id)
    if not instances:
        return {"type": "error", "message": f"Report '{ret_name}' exists but no instances generated.", "_form_id": form_id}
    return _build_status_result_fast(form_id, ret_name, instances)


def get_report_status_fast(report_name: str) -> dict:
    clean_input = report_name.strip()
    matches = find_matching_reports(clean_input)
    if not matches:
        suggestions = fuzzy_report_suggestions(clean_input)
        if suggestions:
            opts_text = "\n".join(f"{i+1}. {s}" for i, s in enumerate(suggestions))
            return {"type": "disambiguation", "message": f"No exact match found for '{clean_input}'. Did you mean one of these?\n\n{opts_text}", "options": suggestions}
        return {"type": "error", "message": f"No matching reports found for '{clean_input}'."}
    if len(matches) > 1:
        seen_opts: dict[str, None] = {}
        for m in matches:
            n = m.get("Name", "")
            if n: seen_opts[n] = None
        opts = list(seen_opts.keys())
        return {"type": "disambiguation", "message": "Found multiple matching reports. Which one do you mean?\n\n" + "\n".join(f"{i+1}. {name}" for i, name in enumerate(opts)), "options": opts}
    match = matches[0]; form_id = match.get("Id", "").strip(); ret_name = match.get("Name", report_name)
    instances = get_instances_by_form_id(form_id)
    if not instances:
        return {"type": "error", "message": f"Report '{ret_name}' exists but no instances generated.", "_form_id": form_id}
    return _build_status_result_fast(form_id, ret_name, instances)


def get_report_status(report_name: str) -> dict:
    clean_input = report_name.strip()
    matches = find_matching_reports(clean_input)
    if not matches:
        suggestions = fuzzy_report_suggestions(clean_input)
        if suggestions:
            opts_text = "\n".join(f"{i+1}. {s}" for i, s in enumerate(suggestions))
            return {"type": "disambiguation", "message": f"No exact match found for '{clean_input}'. Did you mean one of these?\n\n{opts_text}", "options": suggestions}
        return {"type": "error", "message": f"No matching reports found for '{clean_input}'."}
    if len(matches) > 1:
        seen_opts: dict[str, None] = {}
        for m in matches:
            n = m.get("Name", "")
            if n: seen_opts[n] = None
        opts = list(seen_opts.keys())
        return {"type": "disambiguation", "message": "Found multiple matching reports. Which one do you mean?\n\n" + "\n".join(f"{i+1}. {name}" for i, name in enumerate(opts)), "options": opts}
    match = matches[0]; form_id = match.get("Id", "").strip(); ret_name = match.get("Name", report_name)
    logger.info("[get_report_status] matched: name=%r form_id=%r", ret_name, form_id)
    instances = get_instances_by_form_id(form_id)
    if not instances:
        logger.warning("[get_report_status] NO instances for form_id=%r", form_id)
        return {"type": "error", "message": f"Report '{ret_name}' exists but no instances generated.", "_form_id": form_id}
    return _build_status_result(form_id, ret_name, instances)


def get_instance_by_date(form_id: str, date_query: str, return_name: str) -> dict:
    rows       = get_instances_by_form_id(form_id); date_query = date_query.strip()
    row = next(
        (r for r in rows if r.get("ReportingDate", "").strip() == date_query), None
    ) or next(
        (r for r in rows if date_query.lower() in r.get("ReportingDate", "").lower()), None
    )
    if not row:
        return {
            "type":            "date_not_found",
            "message":         f"No instance found for '{date_query}'.",
            "form_id":         form_id,
            "return_name":     return_name,
            "available_dates": get_available_dates(form_id),
        }
    code = _safe_status(row)
    dl   = _get_download_info(row, form_id)
    error_category_counts = _get_error_counts(code, dl)

    # ── 4000-series gate ──────────────────────────────────────────────────────
    return_id = _get_return_id_for_form(form_id)
    is_4000   = _is_4000_series(form_id)

    return {
        "type":                  "final",
        "report_name":           return_name,
        "reporting_date":        row.get("ReportingDate", "").strip(),
        "dtc":                   row.get("DTC", "").strip(),
        "status":                map_status(code),
        "status_code":           code,
        "download_url":          dl["download_url"],
        "download_label":        dl["download_label"],
        "status_note":           dl["status_note"],
        "error_category_counts": error_category_counts,
        "is_4000_series":        is_4000,          # ← NEW
        "error_messages":        [],
        "error_details":         [],
    }


def get_report_status_exact(report_name: str) -> dict:
    returns = _parse_returns()
    match = next((r for r in returns if r.get("Name", "").strip() == report_name.strip()), None)
    if not match:
        match = next((r for r in returns if r.get("Name", "").strip().lower() == report_name.strip().lower()), None)
    if not match:
        return {"type": "error", "message": f"Report '{report_name}' not found."}
    form_id = match.get("Id", "").strip(); ret_name = match.get("Name", report_name)
    instances = get_instances_by_form_id(form_id)
    if not instances:
        return {"type": "error", "message": f"Report '{ret_name}' exists but no instances generated.", "_form_id": form_id}
    return _build_status_result(form_id, ret_name, instances)


def get_form_id_by_name(report_name: str) -> str | None:
    name_clean = report_name.strip().lower()
    returns = _parse_returns()
    match = (
        next((r for r in returns if r.get("Name", "").strip().lower()     == name_clean), None) or
        next((r for r in returns if r.get("AltName", "").strip().lower()  == name_clean), None) or
        next((r for r in returns if r.get("ReturnId", "").strip().lower() == name_clean), None)
    )
    return match.get("Id", "").strip() if match else None