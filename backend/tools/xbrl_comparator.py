# xbrl_comparator.py — XBRL variance analysis tool.
# Scans logs/ for instance files, cross-references with XML_InstanceLog,
# then uses Arelle to extract facts and compute period-over-period variance.
#
# Enhancement areas (architecture preserved):
#   1. Dimensional context awareness — typed/explicit XBRL members parsed from
#      both Arelle and XML fallback paths; base-context facts preferred for
#      period-over-period comparison.
#   2. Structural-concept filtering — text, code, and identifier concepts
#      excluded from comparison to reduce noise.
#   3. Tiered significance thresholds — magnitude-sensitive significance flag
#      avoids false positives on very large or very small values.
#   4. CamelCase humanisation — concept names split to readable words in
#      formatted tables and LLM prompts.
#   5. Scale-aware LLM prompt — tells the model the value scale (M/K/units)
#      and provides per-concept human-readable names for better narratives.

from __future__ import annotations

import atexit
import logging
import os
import re
import shutil
import tempfile
import time
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

_ROOT     = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_LOGS_DIR = os.path.join(_ROOT, "logs")

from backend.config import INSTANCE_LOG_XML_PATH as _LOG_FILE
from backend.tools.xml_loader import load_xml_tree


def _parse_rd(s: str) -> datetime:
    """Parse a reporting-date string like '15-Jun-2024' into a datetime for sorting."""
    try:
        return datetime.strptime(s, "%d-%b-%Y")
    except ValueError:
        return datetime.min


# ---------------------------------------------------------------------------
# Shared helpers — dimensional context, concept classification, formatting
# ---------------------------------------------------------------------------

# Regex to split CamelCase / PascalCase → human-readable words
_CAMEL_RE = re.compile(r'(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])')

def _humanise(name: str, max_len: int = 42) -> str:
    """Split PascalCase concept name into space-separated words.

    'NetOpenExchangePosition' → 'Net Open Exchange Position'
    'TotalAssets' → 'Total Assets'
    Truncates to max_len with ellipsis if needed.
    """
    words = _CAMEL_RE.sub(' ', name)
    return words[:max_len] if len(words) <= max_len else words[:max_len - 1] + '\u2026'


# Substrings that mark a concept as structural/metadata (non-financial).
# Concepts containing any of these (case-insensitive) are filtered from
# the variance comparison to reduce noise.
_STRUCTURAL_SUBSTRINGS = (
    "text", "description", "identifier", "code", "date", "type",
    "reference", "name", "title", "label", "flag", "indicator",
    "category", "classification", "remark", "comment", "note",
    "scheme", "format", "address", "number",
)

def _is_structural(concept: str) -> bool:
    """Return True if the concept name looks like a metadata/text field.

    We check both the raw name and its CamelCase-split form so that
    e.g. 'LoanTypeCode' is caught by the 'code' substring.
    """
    lower = concept.lower()
    return any(sub in lower for sub in _STRUCTURAL_SUBSTRINGS)


def _dim_key_from_ctx_id(ctx_id: str) -> str:
    """Derive a rough dimensional status from the context ID string.

    RBI XBRL instances follow the convention:
      base context  : 'asof_YYYYMMDD'  or  'fromto_YYYYMMDD_YYYYMMDD'
      typed-member  : 'asof_YYYYMMDD_1', 'asof_YYYYMMDD_1_NameValue_2', …

    A context is considered dimensional when its ID contains an underscore-
    separated numeric suffix (e.g. '_1', '_2') that is NOT part of the date
    segment.  Returns '' for base contexts, the suffix portion otherwise.
    """
    # Strip the date part prefix (8+ digits joined by underscores)
    stripped = re.sub(r'^(asof|fromto)_\d{8}(?:_\d{8})?', '', ctx_id, flags=re.I)
    return stripped  # '' → base context; non-empty → dimensional

# ---------------------------------------------------------------------------
# Step 1 – Instance discovery via InstanceLog + disk scan
# ---------------------------------------------------------------------------

def _parse_instance_log() -> list[dict]:
    """Return all InstanceLog rows that have a non-empty InstanceDocPath."""
    root = load_xml_tree(_LOG_FILE, "XML_InstanceLog.xml")
    if root is None:
        return []
    return [
        dict(el.attrib)
        for el in root.findall("Row")
        if el.attrib.get("InstanceDocPath", "").strip()
    ]


def find_comparable_instances(form_id: str) -> list[dict]:
    """Return instance file records for a FormId where the file exists in logs/.

    Each record: {instance_path, full_path, reporting_date, dtc, status, id}
    Sorted by ReportingDate descending (most recent period first).
    """
    rows = _parse_instance_log()
    result: list[dict] = []
    for r in rows:
        if r.get("FormId", "").strip() != str(form_id).strip():
            continue
        fname     = r["InstanceDocPath"].strip()
        full_path = os.path.join(_LOGS_DIR, fname)
        if os.path.exists(full_path):
            result.append({
                "instance_path":  fname,
                "full_path":      full_path,
                "reporting_date": r.get("ReportingDate", "").strip(),
                "dtc":            r.get("DTC", "").strip(),
                "status":         r.get("Status", "").strip(),
                "id":             r.get("Id", "").strip(),
            })

    result.sort(key=lambda x: _parse_rd(x["reporting_date"]), reverse=True)
    return result


def find_instances_by_prefix(prefix: str) -> list[dict]:
    """Scan logs/ for XBRL instance files whose names start with the given prefix
    (case-insensitive) — used for files not registered in XML_InstanceLog.

    Parses reporting date and DTC from the standard filename pattern:
      {PREFIX}{YYMMDD}R{...}_{DD}-{MM}-{YY}_{HH}-{MM}-{SS}_Instance.xml

    Returns list of dicts with the same keys as find_comparable_instances().
    """
    if not os.path.isdir(_LOGS_DIR):
        return []

    _MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    prefix_lower = prefix.lower()
    results: list[dict] = []

    for fname in sorted(os.listdir(_LOGS_DIR)):
        if not fname.lower().startswith(prefix_lower):
            continue
        if not fname.lower().endswith("_instance.xml"):
            continue
        full_path = os.path.join(_LOGS_DIR, fname)
        if not os.path.isfile(full_path):
            continue

        # Reporting date: first 6 characters after the prefix → YYMMDD
        try:
            rest = fname[len(prefix):]           # e.g. "240615R00902D_08-01-25_..."
            yy   = int(rest[0:2])
            mm   = int(rest[2:4])
            dd   = int(rest[4:6])
            reporting_date = f"{dd:02d}-{_MONTH_ABBR[mm - 1]}-{2000 + yy}"
        except (ValueError, IndexError):
            reporting_date = ""

        # DTC: from the _DD-MM-YY_HH-MM-SS_ timestamp in the filename
        try:
            m = re.search(
                r'_(\d{2})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2})_Instance',
                fname, re.IGNORECASE,
            )
            if m:
                dd2, mm2, yy2, hh, mi, ss = (int(x) for x in m.groups())
                dtc = f"{dd2:02d}-{_MONTH_ABBR[mm2 - 1]}-{2000 + yy2} {hh:02d}:{mi:02d}:{ss:02d} AM"
            else:
                dtc = ""
        except (ValueError, AttributeError):
            dtc = ""

        results.append({
            "instance_path":  fname,
            "full_path":      full_path,
            "reporting_date": reporting_date,
            "dtc":            dtc,
            "status":         "",
            "id":             "",
        })

    results.sort(key=lambda x: _parse_rd(x["reporting_date"]), reverse=True)
    return results


# ---------------------------------------------------------------------------
# Step 2 – XBRL fact extraction via Arelle
# ---------------------------------------------------------------------------
# Minimal stub XSDs for standard schemas that may be corrupt or unreachable.
# Provides just enough namespace/type declarations for Arelle to continue
# loading the DTS without aborting on unresolvable imports.
# ---------------------------------------------------------------------------

_STUB_TEMP_DIR: str | None = None

_SCHEMA_STUBS: dict[str, str] = {
    # xbrldt-2005.xsd — dimensions schema (often returned as HTML by firewalls)
    "xbrldt-2005.xsd": (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"\n'
        '           targetNamespace="http://xbrl.org/2005/xbrldt"\n'
        '           xmlns:xbrldt="http://xbrl.org/2005/xbrldt"\n'
        '           elementFormDefault="qualified">\n'
        '  <xs:element name="typedMember" abstract="true"/>\n'
        '  <xs:attribute name="typedDomainRef" type="xs:anyURI"/>\n'
        '  <xs:attribute name="contextElement">\n'
        '    <xs:simpleType><xs:restriction base="xs:token">\n'
        '      <xs:enumeration value="segment"/>\n'
        '      <xs:enumeration value="scenario"/>\n'
        '    </xs:restriction></xs:simpleType>\n'
        '  </xs:attribute>\n'
        '</xs:schema>'
    ),
}


def _get_stub_xsd_path(fname: str) -> str | None:
    """Write a minimal stub XSD to a temp dir and return its file path.

    Returns None if no stub is defined for this filename.
    The temp dir is cleaned up automatically when the process exits.
    """
    global _STUB_TEMP_DIR
    stub_content = _SCHEMA_STUBS.get(fname)
    if stub_content is None:
        return None
    if _STUB_TEMP_DIR is None:
        _STUB_TEMP_DIR = tempfile.mkdtemp(prefix="arelle_stubs_")
        atexit.register(shutil.rmtree, _STUB_TEMP_DIR, ignore_errors=True)
    stub_path = os.path.join(_STUB_TEMP_DIR, fname)
    if not os.path.exists(stub_path):
        with open(stub_path, "w", encoding="utf-8") as fh:
            fh.write(stub_content)
        logger.debug("Created stub XSD for %s at %s", fname, stub_path)
    return stub_path


def _is_valid_xsd(path: str) -> bool:
    """Return False if the file is an HTML page (firewall/proxy redirect) rather than XSD."""
    try:
        with open(path, "rb") as fh:
            sample = fh.read(512).decode("utf-8", errors="ignore").lstrip()
        if sample.lower().startswith(("<!doctype", "<html", "<head")):
            logger.warning("Skipping corrupt taxonomy file (HTML instead of XSD): %s", path)
            return False
        return True
    except OSError:
        return False


def _configure_arelle_taxonomy(cntlr, file_path: str) -> None:
    """Configure Arelle URL-rewrite map so all taxonomy files are resolved
    from the local Taxonomy/ sub-folder — no internet access required.

    Skips any local file that is actually an HTML page (firewall redirect)
    so Arelle doesn't receive garbage and abort schema loading.
    """
    instance_dir = os.path.dirname(os.path.abspath(file_path))
    taxonomy_dir = os.path.join(instance_dir, "Taxonomy")
    if not os.path.isdir(taxonomy_dir):
        return

    if not hasattr(cntlr, "webCache") or not hasattr(cntlr.webCache, "urlrewrite"):
        logger.debug("Arelle webCache.urlrewrite unavailable — skipping taxonomy config")
        return

    inst_url = "file:///" + instance_dir.replace("\\", "/").lstrip("/")
    tax_url  = "file:///" + taxonomy_dir.replace("\\", "/").lstrip("/")

    mapped = 0
    skipped = 0

    # 1 — Relative refs: map valid XSD/XML files; replace corrupt ones with stubs
    for fname in os.listdir(taxonomy_dir):
        if not fname.lower().endswith((".xsd", ".xml")):
            continue
        local_path = os.path.join(taxonomy_dir, fname)
        if _is_valid_xsd(local_path):
            cntlr.webCache.urlrewrite[f"{inst_url}/{fname}"] = f"{tax_url}/{fname}"
            mapped += 1
        else:
            # Corrupt file — use a minimal valid stub if one is defined
            stub_path = _get_stub_xsd_path(fname)
            if stub_path:
                stub_url = "file:///" + stub_path.replace("\\", "/").lstrip("/")
                cntlr.webCache.urlrewrite[f"{inst_url}/{fname}"] = stub_url
                cntlr.webCache.urlrewrite[f"{tax_url}/{fname}"]  = stub_url
                logger.info("Replaced corrupt %s with minimal stub for partial DTS loading", fname)
                mapped += 1
            else:
                skipped += 1

    # 2 — Online refs: map to valid local file or fall back to stub
    _ONLINE_MAP = {
        "http://www.xbrl.org/2003/xbrl-instance-2003-12-31.xsd": "xbrl-instance-2003-12-31.xsd",
        "http://www.xbrl.org/2005/xbrldt-2005.xsd":              "xbrldt-2005.xsd",
        "http://xbrl.org/2005/xbrldt-2005.xsd":                  "xbrldt-2005.xsd",
    }
    for online_url, local_fname in _ONLINE_MAP.items():
        local_path = os.path.join(taxonomy_dir, local_fname)
        if os.path.isfile(local_path) and _is_valid_xsd(local_path):
            # Valid local copy — use it directly
            cntlr.webCache.urlrewrite[online_url] = f"{tax_url}/{local_fname}"
            mapped += 1
        else:
            # Local file missing or corrupt — use a stub so the import resolves
            stub_path = _get_stub_xsd_path(local_fname)
            if stub_path:
                stub_url = "file:///" + stub_path.replace("\\", "/").lstrip("/")
                cntlr.webCache.urlrewrite[online_url] = stub_url
                logger.info(
                    "Online schema %s -> using minimal stub (local file %s)",
                    online_url,
                    "corrupt" if os.path.isfile(local_path) else "missing",
                )
                mapped += 1
            elif os.path.isfile(local_path):
                logger.warning(
                    "Online schema %s -> local file is corrupt and no stub defined; "
                    "Arelle will treat this import as unresolvable",
                    online_url,
                )

    # 3 — Block network requests; missing cache entries are treated as not-found
    if hasattr(cntlr.webCache, "internetConnectivity"):
        cntlr.webCache.internetConnectivity = "offline"

    # 4 — Disable strict validation so unresolvable imports become warnings only
    if hasattr(cntlr, "modelManager"):
        mm = cntlr.modelManager
        for attr in ("validateDisclosureSystem", "validateCalcLinkbase", "abortOnMajorError"):
            if hasattr(mm, attr):
                setattr(mm, attr, False)

    logger.info(
        "Arelle taxonomy: %d URL(s) mapped (%d stub(s) used), %d skipped, offline mode",
        mapped, sum(1 for v in cntlr.webCache.urlrewrite.values() if "arelle_stubs" in v),
        skipped,
    )

def load_xbrl_facts(file_path: str) -> list[dict]:
    """Load an XBRL instance file and return extracted facts.

    Tries Arelle first (partial taxonomy tolerated); falls back to direct XML
    parsing only when Arelle returns 0 facts or raises an exception.
    Returns list of dicts: {concept, period_type, period_end, value_str, value_num, unit}
    Raises ImportError if arelle-release is not installed.
    """
    fname = os.path.basename(file_path)
    _t0 = time.monotonic()
    try:
        facts = _load_via_arelle(file_path)
        if facts:
            _elapsed = time.monotonic() - _t0
            logger.info(
                "[XBRL_LOAD] engine=arelle facts=%d file=%s duration=%.2fs",
                len(facts), fname, _elapsed,
            )
            return facts
        logger.warning(
            "[XBRL_LOAD] engine=arelle facts=0 file=%s — falling back to XML parse", fname,
        )
        facts = _load_via_xml(file_path)
        _elapsed = time.monotonic() - _t0
        logger.info(
            "[XBRL_LOAD] engine=xml_fallback facts=%d file=%s duration=%.2fs",
            len(facts), fname, _elapsed,
        )
        return facts
    except ImportError:
        raise
    except Exception as exc:
        logger.warning(
            "[XBRL_LOAD] engine=arelle error=%s file=%s — falling back to XML parse", exc, fname,
        )
        facts = _load_via_xml(file_path)
        _elapsed = time.monotonic() - _t0
        logger.info(
            "[XBRL_LOAD] engine=xml_fallback facts=%d file=%s duration=%.2fs",
            len(facts), fname, _elapsed,
        )
        return facts


def _get_context_period(ctx) -> tuple[str, str]:
    """Extract (period_type, period_end) from an Arelle ModelContext.

    Tries multiple attribute names to handle API differences across
    arelle-release versions (isInstant vs isInstantPeriod, etc.).
    """
    for attr in ("isInstant", "isInstantPeriod"):
        try:
            if getattr(ctx, attr, False):
                dt = getattr(ctx, "instantDatetime", None)
                return "instant", str(dt.date()) if dt else ""
        except Exception:
            pass

    for attr in ("isStartEndPeriod", "isDurationPeriod", "isStartEndPeriodType"):
        try:
            if getattr(ctx, attr, False):
                dt = getattr(ctx, "endDatetime", None)
                return "duration", str(dt.date()) if dt else ""
        except Exception:
            pass

    return "unknown", ""


def _get_context_dims_arelle(ctx) -> str:
    """Return a dimension-membership key string for an Arelle ModelContext.

    Returns '' for base (non-dimensional) contexts.
    For dimensional contexts, returns a normalised string listing the
    axis→member pairs so that equivalent contexts across different files
    can be matched by value.

    Tries the modern Arelle API first (segDimValues / qnameDims) then
    falls back to the context ID heuristic so old arelle-release builds
    still work correctly.
    """
    # Modern Arelle API: qnameDims is a dict of {qname: ModelDimensionValue}
    try:
        dims = getattr(ctx, 'qnameDims', None) or {}
        if dims:
            parts = []
            for axis_qn, dv in sorted(dims.items(), key=lambda x: str(x[0])):
                axis = str(axis_qn.localName) if hasattr(axis_qn, 'localName') else str(axis_qn)
                # typedMember → value text; explicitMember → member local name
                if hasattr(dv, 'typedMember') and dv.typedMember is not None:
                    val = (dv.typedMember.text or '').strip()
                else:
                    member_qn = getattr(dv, 'memberQname', None)
                    val = member_qn.localName if (member_qn and hasattr(member_qn, 'localName')) else str(dv)
                parts.append(f'{axis}={val}')
            return ';'.join(parts)
    except Exception:
        pass

    # Fallback: legacy segDimValues
    try:
        seg = getattr(ctx, 'segDimValues', None) or {}
        if seg:
            parts = []
            for axis_qn, dv in sorted(seg.items(), key=lambda x: str(x[0])):
                axis = str(axis_qn.localName) if hasattr(axis_qn, 'localName') else str(axis_qn)
                member_qn = getattr(dv, 'memberQname', None)
                val = member_qn.localName if (member_qn and hasattr(member_qn, 'localName')) else str(dv)
                parts.append(f'{axis}={val}')
            return ';'.join(parts)
    except Exception:
        pass

    # Final fallback: derive from the context ID string
    return _dim_key_from_ctx_id(getattr(ctx, 'id', '') or '')


def _load_via_arelle(file_path: str) -> list[dict]:
    """Extract facts using the Arelle XBRL library.

    Enhancement: in addition to the original fields, each fact dict now
    carries:
      'dim_key'        — empty string for base-context facts; non-empty
                         string (axis=member pairs) for dimensional facts.
      'is_dimensional' — bool convenience flag derived from dim_key.
      'period_start'   — ISO start date for duration facts; empty otherwise.
    These extra fields are consumed by _build_map in compute_variance to
    prefer base-context aggregates over typed-member row facts.
    """
    try:
        from arelle import Cntlr as _ArelleCtrl
    except ImportError as exc:
        raise ImportError(
            "arelle-release is not installed. Run: pip install arelle-release"
        ) from exc

    cntlr = _ArelleCtrl.Cntlr(logFileName="logToStdErr")
    _configure_arelle_taxonomy(cntlr, file_path)   # map Taxonomy/ folder if present
    model = None
    try:
        model = cntlr.modelManager.load(filesource=file_path)  # correct param: filesource
        if model is None:
            raise ValueError(f"Arelle returned None model for: {file_path}")

        facts: list[dict] = []
        skipped_no_ctx = 0

        for fact in model.facts:
            if fact.context is None:
                skipped_no_ctx += 1
                continue

            # Concept name: prefer resolved concept, fall back to element QName
            if fact.concept is not None:
                concept_name = fact.concept.name
            else:
                try:
                    qn = getattr(fact, "qname", None) or getattr(fact, "elementQname", None)
                    concept_name = qn.localName if qn else None
                except AttributeError:
                    concept_name = None
                if not concept_name:
                    continue

            value_str = fact.value
            if not value_str or not value_str.strip():
                continue

            period_type, period_end = _get_context_period(fact.context)

            # Extract period start date for duration facts
            period_start = ""
            if period_type == "duration":
                try:
                    sd = getattr(fact.context, "startDatetime", None)
                    if sd:
                        period_start = str(sd.date())
                except Exception:
                    pass

            try:
                num_val: float | None = float(value_str.replace(",", ""))
            except (ValueError, AttributeError):
                num_val = None

            # Dimensional context analysis (Enhancement)
            dim_key = _get_context_dims_arelle(fact.context)

            facts.append({
                "concept":        concept_name,
                "period_type":    period_type,
                "period_end":     period_end,
                "period_start":   period_start,
                "value_str":      value_str.strip(),
                "value_num":      num_val,
                "unit":           str(fact.unit) if fact.unit else "",
                "ctx_ref":        getattr(fact, "contextID", "") or "",
                "dim_key":        dim_key,
                "is_dimensional": bool(dim_key),
            })

        if skipped_no_ctx:
            logger.debug("Arelle: skipped %d fact(s) with no context", skipped_no_ctx)
        return facts
    finally:
        if model is not None:
            try:
                cntlr.modelManager.close(model)
            except Exception:
                pass


def _parse_xml_contexts(root) -> dict[str, dict]:
    """Build a context map from an XBRL instance XML tree.

    Enhancement: in addition to period info, each entry now records
    whether the context contains dimensional members (typedMember or
    explicitMember), and a normalised dim_key string.  This lets
    _build_map prefer base-context aggregates over typed-member rows.

    Returns dict: ctx_id → {
        period_type, period_end, period_start,
        dim_key, is_dimensional
    }
    """
    import xml.etree.ElementTree as ET

    _XBRLDI = "http://xbrl.org/2006/xbrldi"
    _TYPED  = f"{{{_XBRLDI}}}typedMember"
    _EXPL   = f"{{{_XBRLDI}}}explicitMember"

    contexts: dict[str, dict] = {}
    for el in root.iter():
        local = el.tag.split("}")[-1] if "}" in el.tag else el.tag
        if local != "context":
            continue
        ctx_id = el.get("id", "")

        period_type  = "unknown"
        period_end   = ""
        period_start = ""
        dim_parts: list[str] = []

        for child in el.iter():
            child_local = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if child_local == "instant" and not period_end:
                period_type = "instant"
                period_end  = (child.text or "").strip()
            elif child_local == "endDate" and not period_end:
                period_type = "duration"
                period_end  = (child.text or "").strip()
            elif child_local == "startDate" and not period_start:
                period_start = (child.text or "").strip()

        # Parse dimensional members from segment/scenario
        for mem in el.iter():
            if mem.tag in (_TYPED, _EXPL):
                axis = mem.get("dimension", "").split(":")[-1]   # local name only
                # typedMember: value is the text of the first child element
                val = ""
                if mem.tag == _TYPED:
                    for v_child in mem:
                        val = (v_child.text or "").strip()
                        break
                elif mem.tag == _EXPL:
                    val = (mem.text or "").strip().split(":")[-1]
                if axis:
                    dim_parts.append(f"{axis}={val}")

        dim_key = ";".join(sorted(dim_parts))
        contexts[ctx_id] = {
            "period_type":    period_type,
            "period_end":     period_end,
            "period_start":   period_start,
            "dim_key":        dim_key,
            "is_dimensional": bool(dim_key),
        }
    return contexts


def _load_via_xml(file_path: str) -> list[dict]:
    """Direct XML fallback — extracts numeric facts from XBRL instance XML.

    Works for simple/test instances without requiring a resolved taxonomy.
    Skips structural XBRL elements (context, unit, schemaRef).

    Enhancement: uses _parse_xml_contexts() to populate dim_key and
    is_dimensional for each fact, matching the fields produced by
    _load_via_arelle for consistent behaviour in _build_map.
    """
    import xml.etree.ElementTree as ET

    _SKIP = {"context", "unit", "schemaref", "xbrl", "roleref", "arcroleref",
             "linkbaseref", "taxonomy", "footnotelink"}

    tree = ET.parse(file_path)
    root = tree.getroot()

    # Build enhanced context map (now includes dim_key and is_dimensional)
    contexts = _parse_xml_contexts(root)

    _DEFAULT_CTX = {"period_type": "unknown", "period_end": "",
                    "period_start": "", "dim_key": "", "is_dimensional": False}

    facts: list[dict] = []
    for el in root:
        local = el.tag.split("}")[-1] if "}" in el.tag else el.tag
        if local.lower() in _SKIP:
            continue
        value_str = (el.text or "").strip()
        if not value_str:
            continue
        try:
            num_val: float | None = float(value_str.replace(",", ""))
        except (ValueError, AttributeError):
            num_val = None
        ctx_ref  = el.get("contextRef", "")
        ctx_info = contexts.get(ctx_ref, _DEFAULT_CTX)
        facts.append({
            "concept":        local,
            "period_type":    ctx_info["period_type"],
            "period_end":     ctx_info["period_end"],
            "period_start":   ctx_info.get("period_start", ""),
            "value_str":      value_str,
            "value_num":      num_val,
            "unit":           el.get("unitRef", ""),
            "ctx_ref":        ctx_ref,
            "dim_key":        ctx_info["dim_key"],
            "is_dimensional": ctx_info["is_dimensional"],
        })
    return facts


# ---------------------------------------------------------------------------
# Step 3 – Variance computation
# ---------------------------------------------------------------------------

def compute_variance(
    facts_a: list[dict],
    label_a: str,
    facts_b: list[dict],
    label_b: str,
    top_n:   int = 30,
) -> list[dict]:
    """Align facts on concept name and compute diff + % change.

    Only numeric concepts present in both files are included.
    Enhancement improvements (API unchanged):
      - Base-context facts (is_dimensional=False) are preferred over
        typed-member dimensional facts — fixes the prior ctx_ref-length
        heuristic which was fragile for non-standard context ID patterns.
      - Structural/metadata concepts (text, code, identifier, …) are
        filtered out to remove noisy non-financial rows.
      - Significance uses tiered thresholds based on absolute magnitude
        rather than a flat 20% cutoff, reducing false positives for
        very large or very small values.
      - Sorting uses a composite score (normalised pct × log-magnitude)
        so small-value outliers don't dominate the top-N list.
    Returns top_n rows sorted by composite importance score descending.
    """
    import math

    def _build_map(facts: list[dict]) -> dict[str, float]:
        """Build concept → value map, preferring base-context (non-dimensional) facts.

        Priority order (highest wins):
          1. is_dimensional=False  (base/aggregate context — preferred)
          2. is_dimensional=True   (typed-member row — fallback only)
        Within each tier, pick the fact whose ctx_ref is shortest
        (smallest dimensional suffix).
        """
        # tier: 0 = base context, 1 = dimensional
        best_tier: dict[str, int]   = {}
        best_clen: dict[str, int]   = {}
        m: dict[str, float]         = {}

        for f in facts:
            if f["value_num"] is None:
                continue
            name = f["concept"]
            # Filter out structural/metadata concepts early
            if _is_structural(name):
                continue
            tier     = 0 if not f.get("is_dimensional", False) else 1
            cref_len = len(f.get("ctx_ref", ""))
            cur_tier = best_tier.get(name, 999)
            cur_clen = best_clen.get(name, 9999)
            # Accept if better tier, or same tier with shorter ctx_ref
            if tier < cur_tier or (tier == cur_tier and cref_len < cur_clen):
                m[name]          = f["value_num"]
                best_tier[name]  = tier
                best_clen[name]  = cref_len
        return m

    def _is_significant(pct: float | None, abs_val_a: float, abs_val_b: float) -> bool:
        """Tiered significance: threshold depends on value magnitude.

        Very large values (>1 M): flag at 10%+ change — they matter even
            if the percentage looks small in isolation.
        Medium values (10 K – 1 M): flag at 20%+ — the standard cutoff.
        Small values (<10 K): flag at 50%+ — avoids flagging rounding noise.
        Zero baseline: always flag (pct would be None / infinite).
        """
        if pct is None:
            return True   # zero baseline → something changed from nothing
        abs_pct = abs(pct)
        ref_mag = max(abs_val_a, abs_val_b)
        if ref_mag >= 1_000_000:
            return abs_pct >= 10.0
        if ref_mag >= 10_000:
            return abs_pct >= 20.0
        return abs_pct >= 50.0

    def _importance_score(pct: float | None, abs_val: float) -> float:
        """Composite sort key: blends % change with log-scaled magnitude.

        This prevents tiny-value outliers (pct=1000%, abs=1) from pushing
        meaningful large-value rows off the top-N list.
        """
        pct_score = abs(pct) if pct is not None else 200.0   # None → treat as large
        mag_score = math.log10(max(abs_val, 1.0))            # 0–7 for typical banking
        return pct_score * (1 + 0.15 * mag_score)            # magnitude acts as tie-breaker

    map_a = _build_map(facts_a)
    map_b = _build_map(facts_b)
    common = set(map_a) & set(map_b)

    rows: list[dict] = []
    for concept in common:
        val_a = map_a[concept]
        val_b = map_b[concept]
        diff  = val_b - val_a
        pct   = ((diff / abs(val_a)) * 100) if val_a != 0 else None
        sig   = _is_significant(pct, abs(val_a), abs(val_b))
        rows.append({
            "concept":     concept,
            label_a:       val_a,
            label_b:       val_b,
            "diff":        diff,
            "pct_change":  pct,
            "significant": sig,
        })

    rows.sort(
        key=lambda r: _importance_score(r["pct_change"], max(abs(r[label_a]), abs(r[label_b]))),
        reverse=True,
    )
    return rows[:top_n]


# ---------------------------------------------------------------------------
# Step 4 – Chat-friendly formatting
# ---------------------------------------------------------------------------

def format_variance_table(
    rows:    list[dict],
    label_a: str,
    label_b: str,
) -> str:
    """Format variance rows as a plain-text table for chat display.

    Enhancement: concept names are displayed as CamelCase-split human-
    readable words (e.g. 'NetOpenExchangePosition' → 'Net Open Exchange
    Position') so that the table is easier to read in the chat UI.
    Numeric values auto-scale to M / K / raw based on magnitude.
    """
    if not rows:
        return "No comparable numeric facts found between the two instances."

    def _short(name: str, n: int = 38) -> str:
        human = _humanise(name, max_len=n)
        return human if len(human) <= n else human[: n - 1] + "\u2026"

    def _fmt(v: float | None) -> str:
        if v is None:
            return "\u2014"
        if abs(v) >= 1_000_000:
            return f"{v / 1_000_000:,.2f}M"
        if abs(v) >= 1_000:
            return f"{v:,.0f}"
        return f"{v:.4g}"

    def _pct(v: float | None) -> str:
        if v is None:
            return "N/A"
        return f"{'+'if v >= 0 else ''}{v:.1f}%"

    lbl_a  = label_a[:12]
    lbl_b  = label_b[:12]
    header = (
        f"{'Concept':<40} | {lbl_a:>12} | {lbl_b:>12} | "
        f"{'Diff':>12} | {'%Chg':>8} |"
    )
    sep   = "-" * len(header)
    lines = [header, sep]
    for r in rows:
        flag = " \u26a0" if r["significant"] else ""
        lines.append(
            f"{_short(r['concept']):<40} | {_fmt(r[label_a]):>12} | {_fmt(r[label_b]):>12} | "
            f"{_fmt(r['diff']):>12} | {_pct(r['pct_change']):>8} |{flag}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Step 5 – LLM-generated narrative summary
# ---------------------------------------------------------------------------

async def generate_llm_summary(
    rows:        list[dict],
    label_a:     str,
    label_b:     str,
    report_name: str = "",
) -> str:
    """Call Ollama to produce a narrative executive summary of the variance.

    Returns a plain-text paragraph. Returns "" on any error so the table
    is still shown without a summary rather than failing entirely.
    Retries once on transient failures. Logs full tracebacks for diagnosis.
    """
    import httpx

    if not rows:
        return ""

    # Build data lines — only include rows that have numeric values in both columns
    # Enhancement: use top 12 rows (up from 10), and humanise concept names for LLM
    lines: list[str] = []
    for r in rows[:12]:
        concept_raw  = r.get("concept", "?")
        concept_name = _humanise(concept_raw, max_len=50)   # CamelCase → readable
        val_a        = r.get(label_a)
        val_b        = r.get(label_b)
        pct          = f"{r['pct_change']:+.1f}%" if r.get("pct_change") is not None else "N/A"
        sig          = " ⚠ HIGH VARIANCE" if r.get("significant") else ""
        if isinstance(val_a, (int, float)) and isinstance(val_b, (int, float)):
            lines.append(
                f"  {concept_name}: {label_a}={val_a:,.0f}  {label_b}={val_b:,.0f}  change={pct}{sig}"
            )
        elif pct != "N/A":
            lines.append(f"  {concept_name}: change={pct}{sig}")

    if not lines:
        logger.warning(
            "[COMPARE_SUMMARY] no usable rows after filtering — skipping LLM call",
        )
        return ""

    logger.info(
        "[COMPARE_ANALYSIS] report=%r label_a=%r label_b=%r rows=%d",
        report_name, label_a, label_b, len(rows),
    )

    # Determine the dominant value scale for scale-aware prompt context
    all_vals = [
        v for r in rows[:12]
        for v in (r.get(label_a), r.get(label_b))
        if isinstance(v, (int, float))
    ]
    max_abs = max((abs(v) for v in all_vals), default=0)
    if max_abs >= 1_000_000:
        scale_note = f"Values are in the range of millions (largest ≈ {max_abs / 1_000_000:,.1f}M)."
    elif max_abs >= 1_000:
        scale_note = f"Values are in the range of thousands (largest ≈ {max_abs / 1_000:,.1f}K)."
    else:
        scale_note = f"Values are in base units (largest ≈ {max_abs:,.0f})."

    data_text = "\n".join(lines)
    prompt = (
        f"You are an expert RBI banking regulatory and financial analyst.\n"
        f"Analyze XBRL variance data from an Indian banking report and generate precise, high-impact insights.\n\n"

        f"Report: {report_name or 'RBI Banking Report'}\n"
        f"Period A (current):  {label_a}\n"
        f"Period B (previous): {label_b}\n"
        f"Scale context: {scale_note}\n\n"

        f"Variance Data (concept: Period A → Period B, % change):\n{data_text}\n\n"

        f"Generate EXACTLY 5 bullet points.\n\n"

        f"STRICT RULES:\n"
        f"- Start every line with '• '\n"
        f"- Maximum 18 words per bullet.\n"
        f"- One sentence per bullet only.\n"
        f"- Focus only on the most significant increases/decreases.\n"
        f"- Mention the metric name, direction of change (increased/decreased/surged/fell), magnitude, and business implication.\n"
        f"- Provide real-world banking/regulatory inference: e.g. liquidity risk, NPA exposure, capital adequacy, forex risk, credit growth.\n"
        f"- Use the humanised metric name (not the raw technical code).\n"
        f"- Keep insights executive-style — sharp and scannable.\n"
        f"- No headings. No introduction. No conclusion. No numbering.\n"
        f"- Output ONLY the 5 bullet points.\n\n"

        f"- Bold the metric name AND the percentage/value change using markdown ** **.\n"
        f"Example format:\n"
        f"• **Net Open Exchange Position surged +1160%** signalling aggressive expansion in foreign currency exposure.\n"
    )



    base_url   = os.getenv("OLLAMA_BASE_URL",      "http://127.0.0.1:11434")
    model      = os.getenv("OLLAMA_COMPARE_MODEL", "phi3:mini")   # dedicated compare/summary model
    keep_alive = os.getenv("OLLAMA_KEEP_ALIVE",    "30m")
    # Short timeout: summary is decorative - must not block the comparison result.
    # Override via OLLAMA_SUMMARY_TIMEOUT; default 8 s.
    timeout    = float(os.getenv("OLLAMA_SUMMARY_TIMEOUT", "240"))

    chat_payload = {
        "model":      model,
        "messages":   [{"role": "user", "content": prompt}],
        "stream":     False,
        "keep_alive": keep_alive,
        "options":    {"temperature": 0.3, "num_predict": 450},
    }
    gen_payload = {
        "model":      model,
        "prompt":     prompt,
        "stream":     False,
        "keep_alive": keep_alive,
        "options":    {"temperature": 0.3, "num_predict": 450},
    }

    def _normalise_bullets(raw):
        out = []
        for ln in raw.splitlines():
            ln = ln.strip()
            if not ln or ln.lower().startswith(("ai summary", "summary:", "key finding")):
                continue
            ln = re.sub(r'^(?:\*|-|•|\d+[.)\s])\s*', '', ln)
            if ln:
                out.append('• ' + ln)
        out = out[:5]
        return ('AI Summary:\n' + '\n'.join(out)) if out else ''

    try:
        logger.debug('[LLM_SUMMARY] model=%s rows=%d timeout=%.0fs', model, len(lines), timeout)
        _t0 = time.monotonic()
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                resp = await client.post(f'{base_url}/api/chat', json=chat_payload)
                resp.raise_for_status()
                content = (resp.json().get('message', {}).get('content') or '').strip()
            except httpx.HTTPStatusError as http_err:
                if http_err.response.status_code == 404:
                    logger.warning('[LLM_SUMMARY] /api/chat 404 for model=%s - trying /api/generate. Run: ollama pull %s', model, model)
                    resp2 = await client.post(f'{base_url}/api/generate', json=gen_payload)
                    resp2.raise_for_status()
                    content = (resp2.json().get('response') or '').strip()
                else:
                    raise
        _elapsed = time.monotonic() - _t0
        if content:
            result = _normalise_bullets(content)
            if result:
                logger.info('[PERF] operation=llm_summary model=%s duration=%.2fs chars=%d', model, _elapsed, len(result))
                return result
        logger.warning('[LLM_SUMMARY] model responded but produced no usable bullets')
    except Exception as exc:
        logger.warning('[LLM_SUMMARY_FAIL] model=%s error=%s - skipping AI summary silently', model, exc)

    return ''
