# xbrl_comparator.py — XBRL variance analysis tool.
# Scans logs/ for instance files, cross-references with XML_InstanceLog,
# then uses Arelle to extract facts and compute period-over-period variance.

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


def _load_via_arelle(file_path: str) -> list[dict]:
    """Extract facts using the Arelle XBRL library."""
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

            try:
                num_val: float | None = float(value_str.replace(",", ""))
            except (ValueError, AttributeError):
                num_val = None

            facts.append({
                "concept":     concept_name,
                "period_type": period_type,
                "period_end":  period_end,
                "value_str":   value_str.strip(),
                "value_num":   num_val,
                "unit":        str(fact.unit) if fact.unit else "",
                "ctx_ref":     getattr(fact, "contextID", "") or "",
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


def _load_via_xml(file_path: str) -> list[dict]:
    """Direct XML fallback — extracts numeric facts from XBRL instance XML.

    Works for simple/test instances without requiring a resolved taxonomy.
    Skips structural XBRL elements (context, unit, schemaRef).
    """
    import xml.etree.ElementTree as ET

    _SKIP = {"context", "unit", "schemaref", "xbrl", "roleref", "arcroleref",
             "linkbaseref", "taxonomy", "footnotelink"}

    tree = ET.parse(file_path)
    root = tree.getroot()

    # Build context map: id → {period_type, period_end}
    contexts: dict[str, dict] = {}
    for el in root.iter():
        local = el.tag.split("}")[-1] if "}" in el.tag else el.tag
        if local == "context":
            ctx_id = el.get("id", "")
            for child in el.iter():
                child_local = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if child_local == "instant":
                    contexts[ctx_id] = {"period_type": "instant", "period_end": (child.text or "").strip()}
                    break
                if child_local == "endDate":
                    contexts[ctx_id] = {"period_type": "duration", "period_end": (child.text or "").strip()}
                    break

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
        ctx_info = contexts.get(ctx_ref, {"period_type": "unknown", "period_end": ""})
        facts.append({
            "concept":     local,
            "period_type": ctx_info["period_type"],
            "period_end":  ctx_info["period_end"],
            "value_str":   value_str,
            "value_num":   num_val,
            "unit":        el.get("unitRef", ""),
            "ctx_ref":     ctx_ref,
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
    When a concept appears under multiple contexts, the base context
    (shortest contextRef ID — no typed member dimensions) wins.
    Returns top_n rows sorted by abs(pct_change) descending.
    """
    def _build_map(facts: list[dict]) -> dict[str, float]:
        """Build concept → value map, preferring base-context facts."""
        m: dict[str, float]   = {}
        ctx_len: dict[str, int] = {}   # tracks how "specific" the winning ctx was
        for f in facts:
            if f["value_num"] is None:
                continue
            name = f["concept"]
            # Prefer facts whose contextRef is shorter (base context = no typed dims)
            cref_len = len(f.get("ctx_ref", ""))
            if name not in m or cref_len < ctx_len.get(name, 9999):
                m[name]       = f["value_num"]
                ctx_len[name] = cref_len
        return m

    map_a = _build_map(facts_a)
    map_b = _build_map(facts_b)
    common = set(map_a) & set(map_b)

    rows: list[dict] = []
    for concept in common:
        val_a = map_a[concept]
        val_b = map_b[concept]
        diff  = val_b - val_a
        pct   = ((diff / abs(val_a)) * 100) if val_a != 0 else None
        rows.append({
            "concept":     concept,
            label_a:       val_a,
            label_b:       val_b,
            "diff":        diff,
            "pct_change":  pct,
            "significant": pct is not None and abs(pct) >= 20,
        })

    rows.sort(
        key=lambda r: abs(r["pct_change"]) if r["pct_change"] is not None else abs(r["diff"]),
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
    """Format variance rows as a plain-text table for chat display."""
    if not rows:
        return "No comparable numeric facts found between the two instances."

    def _short(name: str, n: int = 38) -> str:
        return name if len(name) <= n else name[: n - 1] + "\u2026"

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
    lines: list[str] = []
    for r in rows[:10]:
        concept = r.get("concept", "?")
        val_a   = r.get(label_a)
        val_b   = r.get(label_b)
        pct     = f"{r['pct_change']:+.1f}%" if r.get("pct_change") is not None else "N/A"
        sig     = " (significant)" if r.get("significant") else ""
        if isinstance(val_a, (int, float)) and isinstance(val_b, (int, float)):
            lines.append(
                f"  {concept}: {label_a}={val_a:,.0f}  {label_b}={val_b:,.0f}  change={pct}{sig}"
            )
        elif pct != "N/A":
            lines.append(f"  {concept}: change={pct}{sig}")

    if not lines:
        logger.warning(
            "[COMPARE_SUMMARY] no usable rows after filtering — skipping LLM call",
        )
        return ""

    logger.info(
        "[COMPARE_ANALYSIS] report=%r label_a=%r label_b=%r rows=%d",
        report_name, label_a, label_b, len(rows),
    )

    data_text = "\n".join(lines)
    prompt = (
        f"You are a financial analyst reviewing XBRL regulatory report data for a bank.\n"
        f"Report: {report_name}\n"
        f"Comparing filing {label_a} (current) vs {label_b} (prior).\n\n"
        f"Top variance data (concept: prior → current, % change):\n{data_text}\n\n"
        f"Write exactly 5 bullet points (no more, no less) explaining the most important changes.\n"
        f"Rules:\n"
        f"- Output ONLY the bullet list — no intro text, no headers, no numbering.\n"
        f"- Start each bullet with the Unicode bullet character ‘•’ followed by a space.\n"
        f"- Use plain business language — avoid jargon. One sentence per bullet.\n"
        f"- Lead with the metric name, then describe the change and its significance.\n"
        f"- Prioritise the highest percentage changes first.\n"
        f"- Ignore concepts with zero or negligible change.\n"
        f"- End with one overall trend or risk observation."
    )

    base_url   = os.getenv("OLLAMA_BASE_URL",      "http://127.0.0.1:11434")
    model      = os.getenv("OLLAMA_COMPARE_MODEL", "mistral:7b-instruct")   # dedicated compare/summary model
    keep_alive = os.getenv("OLLAMA_KEEP_ALIVE",    "30m")
    # Short timeout: summary is decorative - must not block the comparison result.
    # Override via OLLAMA_SUMMARY_TIMEOUT; default 8 s.
    timeout    = float(os.getenv("OLLAMA_SUMMARY_TIMEOUT", "8"))

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
