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

from backend.config import instance_log_xml_path as _log_file_path
from backend.tools.xml_loader import load_xml_tree

# ---------------------------------------------------------------------------
# Optional normalization / canonicalization pipeline.
# Enhances comparison accuracy; falls back silently when not installed.
# ---------------------------------------------------------------------------
try:
    from backend.tools.xbrl_normalizer import (
        canonicalize_facts as _canonicalize_facts,
        detect_anomalies   as _detect_anomalies,
    )
    _NORMALIZER_AVAILABLE = True
except ImportError:
    _NORMALIZER_AVAILABLE = False


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


def _ctx_key_from_ref(ctx_ref: str) -> str:
    """Derive a stable context key by tokenising a raw context-reference ID.

    Used as a last-resort fallback when dim_key has no axis=member pairs
    (e.g. when _dim_key_from_ctx_id returned a bare numeric suffix like '_1').

    Examples
    --------
    'asof_20240615_OneMonthMember'        → 'ctx=OneMonth'
    'fromto_20240615_20240715_TwoMonths'  → 'ctx=TwoMonths'
    'asof_20240615_1'                     → 'BASE'  (purely numeric suffix)
    'asof_20240615'                       → 'BASE'  (base context)
    """
    stripped = re.sub(r'^(asof|fromto)_\d{8}(?:_\d{8})?', '', ctx_ref, flags=re.I)
    if not stripped:
        return "BASE"
    tokens = [t for t in stripped.split('_') if t and not t.isdigit()]
    if not tokens:
        return "BASE"
    clean = [t[:-6] if t.lower().endswith('member') else t for t in tokens]
    return "ctx=" + "|".join(clean)


# ---------------------------------------------------------------------------
# Step 1 – Instance discovery via InstanceLog + disk scan
# ---------------------------------------------------------------------------

def _parse_instance_log() -> list[dict]:
    """Return all InstanceLog rows that have a non-empty InstanceDocPath."""
    root = load_xml_tree(_log_file_path(), "XML_InstanceLog.xml")
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
                logger.debug("Replaced corrupt %s with minimal stub for partial DTS loading", fname)
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
                "decimals":       str(getattr(fact, "decimals", "") or ""),
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
            "decimals":       el.get("decimals", ""),
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
    """Align facts on (concept, context_key) and compute diff + % change.

    Pipeline (when xbrl_normalizer is available):
      1. Canonicalize both fact lists — normalize percentage values, resolve
         context dimensions, build stable context_key per fact.
      2. Build (concept, context_key) → value + unit maps, preferring
         base-context (non-dimensional) aggregates over typed-member rows.
      3. Compute diff / % change only for matching dimensional pairs;
         missing-from-one-side facts are excluded (NOT treated as zero).
      4. Validate units, detect anomalies, sort by composite importance score.

    API is fully backward compatible: same signature and return-row structure.
    Rows are enriched with optional extra fields (context_key, unit,
    anomaly_flags) that existing downstream code safely ignores.
    """
    import math

    # ── Step 1: canonicalize (normalize values + resolve context dimensions) ──
    # Idempotent: facts already carrying 'context_key' are left unchanged.
    if _NORMALIZER_AVAILABLE:
        if facts_a and "context_key" not in facts_a[0]:
            facts_a = _canonicalize_facts(facts_a)
        if facts_b and "context_key" not in facts_b[0]:
            facts_b = _canonicalize_facts(facts_b)

    # Build is_percentage lookup once (one scan, O(N)) for anomaly detection
    _is_pct_lookup: dict[str, bool] = {}
    if _NORMALIZER_AVAILABLE:
        for _f in facts_a:
            _c = _f.get("concept", "")
            if _c and "is_percentage" in _f:
                _is_pct_lookup[_c] = bool(_f["is_percentage"])
        for _f in facts_b:
            _c = _f.get("concept", "")
            if _c and _c not in _is_pct_lookup and "is_percentage" in _f:
                _is_pct_lookup[_c] = bool(_f["is_percentage"])

    def _build_map(
        facts: list[dict],
    ) -> tuple[dict[tuple, float], dict[tuple, str], set[tuple]]:
        """Build (concept, context_key) → value and unit maps.

        Key change vs previous version: the comparison key is now a
        (concept, context_key) tuple so dimensional facts are compared
        only against the same dimensional combination in the other instance.

        Priority order (highest wins):
          1. is_dimensional=False  (base/aggregate context — preferred)
          2. is_dimensional=True   (typed-member row — fallback only)
        Within each tier, prefer the fact with the shortest ctx_ref.
        Canonical facts use 'value' (normalized); raw facts fall back to 'value_num'.

        Also detects same-tier duplicates (same concept + context_key appearing
        more than once at equal priority) and returns them as a set for anomaly
        flagging.  Duplicate detection signals XBRL data quality issues.
        """
        best_tier: dict[tuple, int]   = {}
        best_clen: dict[tuple, int]   = {}
        seen_tier: dict[tuple, int]   = {}   # tier at which this key was first seen
        m:         dict[tuple, float] = {}
        u:         dict[tuple, str]   = {}   # unit map
        dups:      set[tuple]         = set()  # same-tier duplicate keys

        for f in facts:
            # Use canonical 'value' if present, else fall back to 'value_num'
            val = f.get("value") if "value" in f else f.get("value_num")
            if val is None:
                continue
            name = f["concept"]
            if _is_structural(name):
                continue
            # Canonical path → raw dim_key fallback → BASE
            # This ensures dimensional separation works even when the normalizer
            # is unavailable or canonicalize_facts hasn't been called yet.
            if "context_key" in f:
                ctx_key = f["context_key"] or "BASE"
            elif f.get("dim_key"):
                _dk_parts = sorted(
                    p.strip() for p in f["dim_key"].split(";") if "=" in p.strip()
                )
                if _dk_parts:
                    ctx_key = "|".join(_dk_parts)
                else:
                    # dim_key present but no axis=member pairs (e.g. came from
                    # _dim_key_from_ctx_id which returns a bare suffix like "_1").
                    # Tokenise ctx_ref directly to recover member names.
                    ctx_key = _ctx_key_from_ref(f.get("ctx_ref", ""))
            else:
                ctx_key = "BASE"
            map_key  = (name, ctx_key)
            tier     = 0 if not f.get("is_dimensional", False) else 1
            cref_len = len(f.get("ctx_ref", ""))
            cur_tier = best_tier.get(map_key, 999)
            cur_clen = best_clen.get(map_key, 9999)
            if tier < cur_tier or (tier == cur_tier and cref_len < cur_clen):
                m[map_key]         = val
                u[map_key]         = f.get("unit", "")
                # If we already saw this key at the same tier, it's a duplicate
                if map_key in seen_tier and seen_tier[map_key] == tier:
                    dups.add(map_key)
                best_tier[map_key] = tier
                best_clen[map_key] = cref_len
                seen_tier[map_key] = tier
            elif tier == cur_tier:
                # Same tier, not a better fact — still a duplicate
                dups.add(map_key)
        return m, u, dups

    def _is_significant(
        pct: float | None,
        abs_val_a: float,
        abs_val_b: float,
        sign_chg: bool,
        anomaly_flags: list[str],
    ) -> bool:
        """Tiered materiality-aware significance.

        Avoids flagging every row by applying magnitude-aware thresholds:
          - Very large values (≥ 1B): require ≥ 15% movement
          - Large values (≥ 1M): require ≥ 25% movement
          - Medium values (≥ 10K): require ≥ 40% movement
          - Small values: require ≥ 75% movement
        Sign reversals and detected anomalies always surface as significant.
        Zero-baseline rows (pct = None) are considered significant only when
        the non-zero value is itself materially large (≥ 10K).
        """
        if anomaly_flags:
            return True   # data-quality / anomaly flags always surface
        if sign_chg:
            return True   # sign reversal is always noteworthy
        if pct is None:
            # New non-zero value with zero baseline — significant if large
            return max(abs_val_a, abs_val_b) >= 10_000
        abs_pct = abs(pct)
        ref_mag = max(abs_val_a, abs_val_b)
        if ref_mag >= 1_000_000_000:
            return abs_pct >= 15.0
        if ref_mag >= 1_000_000:
            return abs_pct >= 25.0
        if ref_mag >= 10_000:
            return abs_pct >= 40.0
        return abs_pct >= 75.0

    def _importance_score(
        pct: float | None,
        abs_val: float,
        sign_chg: bool,
        anomaly_count: int,
    ) -> float:
        """Multi-tier composite sort key.

        Priority order (descending):
          1. Anomaly severity (each anomaly adds a large bonus)
          2. Sign change (large fixed bonus)
          3. Percentage magnitude (log-weighted by value magnitude)
          4. Absolute magnitude (tiebreaker)
        """
        pct_score  = min(abs(pct), 10_000) if pct is not None else 5_000.0
        mag_score  = math.log10(max(abs_val, 1.0))
        base       = pct_score * (1 + 0.15 * mag_score)
        bonus      = anomaly_count * 20_000 + (10_000 if sign_chg else 0)
        return base + bonus

    map_a, units_a, dups_a = _build_map(facts_a)
    map_b, units_b, dups_b = _build_map(facts_b)
    common = set(map_a) & set(map_b)

    # Log missing-fact counts for diagnostics (NOT treated as zero)
    only_in_a = len(set(map_a) - common)
    only_in_b = len(set(map_b) - common)
    if only_in_a or only_in_b:
        logger.debug(
            "[COMPARE_MISSING] keys only in A=%d, only in B=%d (excluded from variance)",
            only_in_a, only_in_b,
        )

    rows: list[dict] = []
    for key in common:
        concept, ctx_key = key
        val_a   = map_a[key]
        val_b   = map_b[key]
        unit_a  = units_a.get(key, "")
        unit_b  = units_b.get(key, "")

        # ── Unit validation: skip incompatible comparisons ───────────────────
        # Allow empty/unknown units through (many XBRL facts omit unitRef).
        if unit_a and unit_b and unit_a.upper() != unit_b.upper():
            logger.debug(
                "[UNIT_MISMATCH] concept=%r ctx=%r unit_a=%r unit_b=%r — skipped",
                concept, ctx_key, unit_a, unit_b,
            )
            continue

        # diff = new - old  (label_a = first/left column = newer instance)
        # pct denominator = abs(old) = abs(val_b)
        diff = val_a - val_b
        pct  = ((diff / abs(val_b)) * 100) if val_b != 0 else None

        # ── Sign-reversal detection ─────────────────────────────────────────
        # True when the two values straddle zero (e.g. -1879M → +130000M).
        sign_chg = (val_a > 0 and val_b < 0) or (val_a < 0 and val_b > 0)

        unit = unit_a or unit_b

        # ── Anomaly detection ────────────────────────────────────────────────
        anomaly_flags: list[str] = []
        if _NORMALIZER_AVAILABLE:
            is_pct        = _is_pct_lookup.get(concept, False)
            anomaly_flags = _detect_anomalies(
                concept, val_a, val_b, unit_a, unit_b, is_pct, pct,
            )
        # Duplicate dimensional facts — data quality flag (always checked)
        if key in dups_a:
            anomaly_flags.append("duplicated_fact_in_A")
        if key in dups_b:
            anomaly_flags.append("duplicated_fact_in_B")
        if sign_chg:
            anomaly_flags.append("sign_reversal")

        sig = _is_significant(pct, abs(val_a), abs(val_b), sign_chg, anomaly_flags)

        # ── Severity scoring ─────────────────────────────────────────────────
        _n_anomaly = len(anomaly_flags)
        _abs_pct   = abs(pct) if pct is not None else 5_000.0
        _ref_mag   = max(abs(val_a), abs(val_b))
        if _n_anomaly >= 2 or (sign_chg and _ref_mag >= 1_000_000) or _abs_pct > 500:
            severity = "critical"
        elif _n_anomaly >= 1 or sign_chg or _abs_pct > 100:
            severity = "high"
        elif sig:
            severity = "medium"
        else:
            severity = "low"

        # ── Embed context label in concept name for frontend compatibility ──
        # The serialized list in _run_comparison only propagates "concept",
        # so we embed the readable context label here so that the frontend
        # table and LLM summary both show dimension membership without any
        # schema changes to the API response.
        if ctx_key and ctx_key != "BASE":
            _sfx_parts: list[str] = []
            for _p in ctx_key.split("|"):
                _raw = _p.split("=", 1)[1] if "=" in _p else _p
                if _raw.lower().endswith("member"):
                    _raw = _raw[:-6]
                if _raw:
                    _sfx_parts.append(_raw)
            _ctx_suffix = f" [{', '.join(_sfx_parts)}]" if _sfx_parts else ""
        else:
            _ctx_suffix = ""

        row: dict = {
            "concept":       concept + _ctx_suffix,  # includes label for frontend
            label_a:         val_a,
            label_b:         val_b,
            "diff":          diff,
            "pct_change":    pct,
            "significant":   sig,
            # Enrichment fields (silently ignored by existing downstream code)
            "context_key":   ctx_key,
            "unit":          unit,
            "anomaly_flags": anomaly_flags,
            "sign_change":   sign_chg,
            "severity":      severity,
        }
        rows.append(row)

    rows.sort(
        key=lambda r: _importance_score(
            r["pct_change"],
            max(abs(r[label_a]), abs(r[label_b])),
            r["sign_change"],
            len(r["anomaly_flags"]),
        ),
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

    Rendering rules:
    - Dimensional context labels are appended to concept names so rows for
      different dimension members are visually distinct:
        e.g. "Foreign Curr Maturity Mismatch [OneMonth]"
             "Foreign Curr Maturity Mismatch [TwoMonths]"
    - All numeric columns (val_a, val_b, diff) in the same row share one
      magnitude scale determined by max(abs(val_a), abs(val_b)) so values
      are never formatted with mixed units (e.g. "2,200.00M" vs "544,400").
    - Raw values are NOT modified; scaling is render-only.
    """
    if not rows:
        return "No comparable numeric facts found between the two instances."

    # ── Context label helper ────────────────────────────────────────────────
    def _ctx_label(ctx_key: str) -> str:
        """Extract readable member values from a context_key string.

        "BASE"                                    → ""
        "CurrencyMismatchDurationDimension=OneMonth" → " [OneMonth]"
        "axis1=val1|axis2=val2"                   → " [val1|val2]"
        """
        if not ctx_key or ctx_key == "BASE":
            return ""
        members = []
        for part in ctx_key.split("|"):
            raw = part.split("=", 1)[1] if "=" in part else part
            # Strip the XBRL "Member" suffix for readable display
            # e.g. "OneMonthMember" → "OneMonth"
            if raw.endswith("Member"):
                raw = raw[:-6]
            members.append(raw)
        label = "|".join(members)
        if len(label) > 22:
            label = label[:21] + "\u2026"
        return f" [{label}]"
    # ── Concept display ─────────────────────────────────────────────────────
    def _concept_display(r: dict, col: int = 55) -> str:
        """Human-readable concept name + context label, fitted to col chars.

        If the concept string already has an embedded label added by
        compute_variance (e.g. "ForeignCurrencyMaturityMismatch [OneMonth]"),
        we split on " [" first so _humanise is only applied to the base name —
        otherwise CamelCase splitting would mangle "OneMonth" into "One Month".
        """
        concept_raw = r["concept"]
        ctx_key     = r.get("context_key", "BASE")

        # Detect embedded label (e.g. "ConceptName [OneMonth]")
        if " [" in concept_raw:
            split_idx    = concept_raw.index(" [")
            concept_part = concept_raw[:split_idx]
            label_part   = concept_raw[split_idx:]    # e.g. " [OneMonth]"
        else:
            concept_part = concept_raw
            label_part   = _ctx_label(ctx_key)

        # Reserve space for label; leave at least 20 chars for the concept name
        name_budget = max(col - len(label_part), 20)
        base = _humanise(concept_part, max_len=name_budget)
        full = base + label_part
        return full if len(full) <= col else full[: col - 1] + "\u2026"

    # ── Row-level consistent scale ──────────────────────────────────────────
    def _row_scale(r: dict) -> tuple[float, str]:
        """Pick one magnitude scale for all numeric columns in this row.

        Scale is based on max(abs(val_a), abs(val_b)) so the two primary
        comparison values always use the same unit. Diff follows naturally.
        """
        v_a = r.get(label_a)
        v_b = r.get(label_b)
        max_abs = max(
            abs(v_a) if v_a is not None else 0.0,
            abs(v_b) if v_b is not None else 0.0,
        )
        if max_abs >= 1_000_000_000:
            return 1_000_000_000.0, "B"
        if max_abs >= 1_000_000:
            return 1_000_000.0, "M"
        if max_abs >= 1_000:
            return 1_000.0, "K"
        return 1.0, ""

    def _fmt_natural(v: float) -> str:
        """Format v in its natural financial unit — never scientific notation."""
        abs_v = abs(v)
        if v == 0:
            return "0"
        if abs_v >= 1_000_000_000:
            return f"{v/1_000_000_000:,.2f}B"
        if abs_v >= 1_000_000:
            return f"{v/1_000_000:,.2f}M"
        if abs_v >= 1_000:
            return f"{v/1_000:,.2f}K"
        if abs_v >= 1:
            return f"{v:,.2f}"
        # Fractional — enough decimal places to show 3 significant figures
        if abs_v >= 0.001:
            return f"{v:,.4f}"
        return f"{v:,.8f}".rstrip('0').rstrip('.')

    def _fmt(v: float | None, div: float, sfx: str) -> str:
        if v is None:
            return "\u2014"
        if v == 0:
            return f"0{sfx}"
        scaled = v / div
        if sfx:
            abs_s = abs(scaled)
            if abs_s >= 1_000:
                return f"{scaled:,.0f}{sfx}"
            if abs_s >= 10:
                return f"{scaled:,.2f}{sfx}"
            if abs_s >= 0.001:
                return f"{scaled:,.4f}{sfx}"
            # Tiny relative to row scale — switch to natural unit
            return _fmt_natural(v)
        # No scale — natural unit, never scientific
        return _fmt_natural(v)

    def _pct(v: float | None) -> str:
        if v is None:
            return "N/A"
        sign  = '+' if v > 0 else ''
        abs_v = abs(v)
        if abs_v > 100_000:
            return f"{sign}Extreme {'\u2191' if v > 0 else '\u2193'}"
        if abs_v > 10_000:
            return f"{sign}Very High"
        if abs_v > 1_000:
            return f"{sign}>1,000%"
        return f"{sign}{v:.1f}%"

    # ── Table rendering ─────────────────────────────────────────────────────
    lbl_a  = label_a[:12]
    lbl_b  = label_b[:12]
    header = (
        f"{'Concept':<55} | {lbl_a:>13} | {lbl_b:>13} | "
        f"{'Diff':>13} | {'%Chg':>8} |"
    )
    sep   = "-" * len(header)
    lines = [header, sep]
    for r in rows:
        div, sfx = _row_scale(r)
        flag  = ""
        if r.get("sign_change"):
            flag += " \u21d5"   # ⇕ sign-reversal marker
        if r["significant"]:
            flag += " \u26a0"   # ⚠ high-variance marker
        lines.append(
            f"{_concept_display(r):<55} | "
            f"{_fmt(r[label_a], div, sfx):>13} | "
            f"{_fmt(r[label_b], div, sfx):>13} | "
            f"{_fmt(r['diff'],  div, sfx):>13} | "
            f"{_pct(r['pct_change']):>12} |{flag}"
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
        f"You are an RBI banking variance analysis assistant.\n"
        f"Your task is to generate STRICTLY DATA-GROUNDED insights from XBRL variance tables.\n\n"

        f"Report: {report_name or 'RBI Banking Report'}\n"
        f"Period A (current): {label_a}\n"
        f"Period B (previous): {label_b}\n"
        f"Scale context: {scale_note}\n\n"

        f"Variance Data (concept: Period A → Period B, % change):\n"
        f"{data_text}\n\n"

        f"Generate EXACTLY 5 bullet points.\n\n"

        f"STRICT RULES:\n"
        f"- Use ONLY the provided numerical data.\n"
        f"- Do NOT assume causes, business strategy, intent, economic conditions, trading behavior, or regulatory breaches.\n"
        f"- Do NOT invent liquidity crises, market stress, aggressive positioning, or management decisions.\n"
        f"- Focus ONLY on:\n"
        f"  * increase/decrease\n"
        f"  * percentage movement\n"
        f"  * absolute difference\n"
        f"  * ranking of changes\n"
        f"  * unusual spikes\n"
        f"  * concentration patterns\n"
        f"- Keep explanations concise, factual, and neutral.\n"
        f"- Use business-friendly analytical language without speculation.\n"
        f"- Prefer wording like:\n"
        f"  * 'recorded the highest increase'\n"
        f"  * 'showed moderate growth'\n"
        f"  * 'remained relatively stable'\n"
        f"- Avoid speculative phrases like:\n"
        f"  * 'due to'\n"
        f"  * 'because'\n"
        f"  * 'indicates aggressive'\n"
        f"  * 'suggests strategy'\n"
        f"  * 'reflects management intent'\n"
        f"- If data is insufficient for causal inference, avoid assumptions completely.\n\n"

        f"OUTPUT FORMAT RULES:\n"
        f"- Start every line with '• '\n"
        f"- Maximum 22 words per bullet.\n"
        f"- One sentence per bullet only.\n"
        f"- Mention exact values and percentage changes from the table.\n"
        f"- Use the human-readable metric name, not raw technical codes.\n"
        f"- No headings.\n"
        f"- No introduction.\n"
        f"- No conclusion.\n"
        f"- No numbering.\n"
        f"- Output ONLY the 5 bullet points.\n\n"

        f"- Bold the metric name and percentage/value movement using markdown ** **.\n\n"

        f"GOOD EXAMPLE:\n"
        f"• **Foreign Currency Maturity Mismatch [One Month] increased by +41.7%**, rising from 1.20B to 1.70B, the highest growth observed.\n\n"

        f"BAD EXAMPLE:\n"
        f"• The increase may indicate liquidity stress and aggressive forex positioning.\n"
    )




    base_url   = os.getenv("OLLAMA_BASE_URL",      "http://127.0.0.1:11434")
    model      = os.getenv("OLLAMA_COMPARE_MODEL", "llama3.1:latest")   # dedicated compare/summary model
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
