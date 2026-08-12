# backend/tools/instance_context.py — optional observation of what a filing
# ACTUALLY reported, read from the XBRL instance document that the instance log
# records for that run.
#
# WHY
# ---
# For xbrldie:IllegalTypedDimensionContentError the validator writes the
# CONTEXT ID into the "Value '…' provided for the typed dimension" slot, so the
# error file alone can only ever say
#
#   reported value = asof_20220331_12112018_AABCW3241P_WELSPUN…_Fluctuation…Member
#
# which is not a dimension value at all. The instance document says it exactly:
#
#   <xbrli:context id='fromto_20231001_20231231_0510003_20231023T125100_OOOOOOOO9'>
#     <xbrldi:typedMember dimension='in-rbi-rep:DateAndTimeOfOccurrenceTypeAxis'>
#       <in-rbi-rep-par:DateAndTimeOfOccurrenceTypeDomain>2023-10-23T12:51:00</…>
#
# WHICH FILE
# ----------
# The document is identified ONLY by the run's own `InstanceDocPath` in the
# instance log — the same field family that already yields the error file via
# `ErrorDocPath` — and only when that file exists on disk. Instance/<form_id>/
# is never scanned for a likely-looking .xml: the folder holds every run for
# the form, so a neighbouring run's document would attribute one filing's
# reported dimension values to a different filing.
#
# STRICTLY OPTIONAL
# -----------------
# Many failed runs record no InstanceDocPath at all. Every function here returns
# None/{}/[] when the file is missing, unreadable, or malformed, and the
# dimension explainer treats a result of None as "fall back to HTML + taxonomy"
# rather than as an error. Nothing in this module is ever on a required path.

from __future__ import annotations

import logging
import os
import re
import threading
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

__all__ = ["find_instance_document", "load_contexts", "context_dimensions",
           "schema_refs"]

_XBRLI = "{http://www.xbrl.org/2003/instance}"
_XBRLDI = "{http://xbrl.org/2006/xbrldi}"
_LINK = "{http://www.xbrl.org/2003/linkbase}"
_XLINK = "{http://www.w3.org/1999/xlink}"

# Instance documents run to megabytes (2033's is 1.2 MB, and larger ones exist).
# Parsing is capped and cached so an explanation batch reads each file once.
_MAX_INSTANCE_BYTES = 96 * 1024 * 1024

_CACHE_LOCK = threading.Lock()
_CACHE: dict[tuple[str, float], dict] = {}


def _local(qname: str) -> str:
    text = (qname or "").strip()
    if "}" in text:
        text = text.rsplit("}", 1)[-1]
    if "#" in text:
        text = text.rsplit("#", 1)[-1]
    if ":" in text:
        text = text.rsplit(":", 1)[-1]
    return text


def find_instance_document(error_file_path: str, form_id: str = "") -> str | None:
    """The XBRL instance document for the run that produced this error file.

    Resolved ONLY from that run's own `InstanceDocPath` in the instance log —
    the same mechanism that already resolves `ErrorDocPath` into the error file
    path — and only when the named file actually exists on disk.

    Instance/<form_id>/ is deliberately NOT scanned for a plausible .xml. One
    folder holds every run for the form, so a neighbouring run's instance
    document would silently attribute one filing's reported dimension values to
    a different filing. If the log records no InstanceDocPath for this run, the
    correct answer is None and the explanation proceeds on HTML + taxonomy.

    None is a completely normal outcome, never an error.
    """
    if not error_file_path:
        return None

    try:
        from backend.tools.report_lookup import resolve_instance_doc_path
        path = resolve_instance_doc_path(error_file_path, form_id)
    except Exception as exc:
        logger.warning("[instance_context] InstanceDocPath lookup failed: %s", exc)
        return None

    if not path:
        return None
    if not _looks_like_instance(path):
        logger.info("[instance_context] %s is not an XBRL instance document", path)
        return None
    return path


def _looks_like_instance(path: str) -> bool:
    """An XBRL instance declares <xbrl> as its root. Checked by reading the
    head only, so the validator's own error XML (root <Errors>) is rejected
    without paying to parse it."""
    try:
        if os.path.getsize(path) > _MAX_INSTANCE_BYTES:
            return False
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            head = fh.read(4096)
    except OSError:
        return False
    return bool(re.search(r"<(?:\w+:)?xbrl\b", head))


def _load(path: str) -> dict | None:
    """Parse one instance document into {contexts, schema_refs}. Cached on
    (path, mtime)."""
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return None

    key = (os.path.normcase(path), mtime)
    with _CACHE_LOCK:
        cached = _CACHE.get(key)
    if cached is not None:
        return cached

    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError, ValueError) as exc:
        logger.warning("[instance_context] cannot parse %s: %s", path, exc)
        return None

    contexts: dict[str, dict] = {}
    for ctx in root.iter(f"{_XBRLI}context"):
        ctx_id = ctx.get("id")
        if not ctx_id:
            continue
        dimensions: list[dict] = []
        for member in ctx.iter(f"{_XBRLDI}typedMember"):
            child = next(iter(member), None)
            dimensions.append({
                "dimension": _local(member.get("dimension") or ""),
                "kind": "typed",
                "value": ((child.text or "").strip() if child is not None
                          else (member.text or "").strip()),
                "element": _local(child.tag) if child is not None else "",
            })
        for member in ctx.iter(f"{_XBRLDI}explicitMember"):
            dimensions.append({
                "dimension": _local(member.get("dimension") or ""),
                "kind": "explicit",
                "value": _local((member.text or "").strip()),
                "element": "",
            })
        period = ctx.find(f"{_XBRLI}period")
        contexts[ctx_id] = {
            "context_id": ctx_id,
            "dimensions": dimensions,
            "period": _period_of(period),
        }

    refs = [
        (ref.get(f"{_XLINK}href") or "")
        for ref in root.iter(f"{_LINK}schemaRef")
    ]

    data = {
        "path": path,
        "contexts": contexts,
        "schema_refs": [r for r in refs if r],
    }
    with _CACHE_LOCK:
        _CACHE[key] = data
    logger.info("[instance_context] loaded %s — %d contexts, schemaRefs=%s",
                path, len(contexts), data["schema_refs"])
    return data


def _period_of(period: ET.Element | None) -> dict:
    if period is None:
        return {}
    instant = period.find(f"{_XBRLI}instant")
    if instant is not None:
        return {"instant": (instant.text or "").strip()}
    start = period.find(f"{_XBRLI}startDate")
    end = period.find(f"{_XBRLI}endDate")
    out = {}
    if start is not None:
        out["start"] = (start.text or "").strip()
    if end is not None:
        out["end"] = (end.text or "").strip()
    return out


def load_contexts(error_file_path: str, form_id: str = "") -> dict | None:
    """{context_id: {dimensions, period}} for the filing this error file
    describes, or None when no instance document is available."""
    path = find_instance_document(error_file_path, form_id)
    if not path:
        return None
    data = _load(path)
    return data["contexts"] if data else None


def context_dimensions(error_file_path: str, context_id: str, form_id: str = "") -> list[dict] | None:
    """The axis/value pairs actually carried by one context.

    None means "no observation available" (no instance document, or that
    context isn't in it) and must be reported as such — never as "the context
    has no dimensions", which is a different and much stronger claim.
    """
    contexts = load_contexts(error_file_path, form_id)
    if not contexts:
        return None
    entry = contexts.get(context_id)
    if entry is None:
        return None
    return entry.get("dimensions") or []


def schema_refs(error_file_path: str, form_id: str = "") -> list[str]:
    """Entry-point schema hrefs declared by the filing — the strongest signal
    available for which taxonomy to explain this error against. [] when there
    is no instance document."""
    path = find_instance_document(error_file_path, form_id)
    if not path:
        return []
    data = _load(path)
    return list(data["schema_refs"]) if data else []
