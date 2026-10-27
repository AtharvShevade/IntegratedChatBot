"""Readers and explanations for the error-file formats that are not validator formula reports.

    duplicate        <InstanceErrorDetails><ErrorDetails><DuplicateElementList><Element PrimaryElement ContextRef SheetOrTableName>
                     the same item/period was reported twice
    dynamic_domain   <InstanceErrorDetails><Row Error="Dynamic Domain: 'x' is not a valid value. Please choose from the given list: ...
                     a drop-down column holds a value that is not on its list
    service_failure  <Error>System.IO.InvalidDataException: Instance validation API Failed ...
                     the validation service itself failed: nothing to correct in the data
    crilc_report     <Document><Report Id Rule Type><detail PAN=... MONTH1=... />
                     month-on-month comparison report of a data-prep (CRILC-style) return

Each explainer returns rows for the common table. Where a filled workbook exists the exact cell is looked up in it;
nothing is invented when it does not.
"""
from __future__ import annotations

import collections
import difflib
import os
import re
import xml.etree.ElementTree as ET

from . import direct_errors as de
from .workbook import Workbook, index_to_col


def detect(path: str) -> str | None:
    try:
        with open(path, encoding="utf-8-sig", errors="ignore") as fh:
            head = fh.read(3000)
    except OSError:
        return None
    if not path.lower().endswith(".xml"):
        return None
    if "<InstanceErrorDetails" in head:
        if "DuplicateElementList" in head or "Duplicate of" in head:
            return "duplicate"
        if "<Row " in head and "Dynamic Domain" in head:
            return "dynamic_domain"
    if re.search(r"<Error>\s*System\.", head):
        return "service_failure"
    if "<Document" in head and "<Report " in head and "<detail" in head:
        return "crilc_report"
    return None


def explain(kind: str, path: str, wb: "Workbook | None", Row, meta=None, fa=None):
    return {"duplicate": _duplicates, "dynamic_domain": _dynamic_domain, "service_failure": _service_failure,
            "crilc_report": _crilc}[kind](path, wb, Row, meta, fa)


# ── duplicates ──────────────────────────────────────────────────────────────────────────────────────────────────
def _duplicates(path, wb, Row, meta, fa):
    rows, located = [], 0
    root = ET.parse(path).getroot()
    for el in root.iter("Element"):
        concept, ctx, sheet = el.get("PrimaryElement", ""), el.get("ContextRef", ""), el.get("SheetOrTableName", "")
        values = [d.get("Value", "") for d in el.iter("DuplicateElement")]
        where = sheet or "(sheet not named)"
        cells = []
        if meta is not None and fa is not None and wb is not None:
            real = de._sheet(wb, sheet) if sheet else None
            cands = [a for a in fa.candidates(meta, wb, concept, ctx) if real is None or a.sheet == real]
            cells = list(dict.fromkeys(f"{a.sheet}!{a.a1}" for a in cands))[:6]
        if cells:
            located += 1
            where = f"{sheet}: " + ", ".join(cells) + (" (cells where this item sits)" if len(cells) > 1 else "")
        vals = " and ".join(f"'{v}'" for v in values) or "more than one value"
        rows.append(Row("DATA", f"{_words(concept)} is reported {len(values) or 2} times for the same period and dimensions ({vals})",
                        where,
                        f"Each item may be reported once per period and set of dimensions. The file holds {vals}: keep the correct "
                        "one and remove the other (a repeated row, or the same item filled in two places).",
                        {"kind": "duplicate", "concept": concept, "context": ctx, "values": values, "sheet": sheet}))
    return rows, located


# ── dynamic domain (drop-down values) ───────────────────────────────────────────────────────────────────────────
_DD = re.compile(r"Dynamic Domain: '(?P<val>.*?)' is not a valid value\. Please choose from the given list: '(?P<lst>.*?)' for "
                 r"Column '(?P<col>[^']*)'(?: with PL_ID - (?P<pl>\S+))?(?: And SheetOrTable Name - (?P<sheet>\S+))?")


def _closest(value: str, allowed: list[str]) -> tuple[str, str]:
    for a in allowed:
        if a.lower() == value.lower():
            return a, "the same text with different capital letters"
    m = difflib.get_close_matches(value, allowed, n=1, cutoff=0.6)
    return (m[0], "the closest allowed value") if m else ("", "")


def _dynamic_domain(path, wb, Row, meta, fa):
    groups: dict[tuple, list] = collections.OrderedDict()
    for el in ET.parse(path).getroot().iter("Row"):
        m = _DD.search(el.get("Error", ""))
        if m:
            groups.setdefault((m["sheet"] or "", m["col"], m["lst"]), []).append((m["val"], m["pl"] or ""))
    rows, located = [], 0
    for (sheet, col, lst), items in groups.items():
        allowed = [x.strip() for x in lst.split(",")]
        fixes, cells = [], []
        for val, pl in items:
            best, how = _closest(val, allowed)
            fixes.append(f"'{val}' -> '{best}' ({how})" if best else f"'{val}' is not on the list")
            if wb is not None and sheet:
                real = de._sheet(wb, sheet)
                for r, c in (wb.index(real).get(val.strip().lower(), []) if real else []):
                    cells.append(f"{index_to_col(c)}{r}")
        where = f"{sheet or '(sheet not named)'} -> column {col}"
        if cells:
            located += len(items)
            where = f"{sheet} -> {de.ranges(cells)} (column {col})"
        rows.append(Row("DATA", f"{len(items)} value(s) in column {col} are not on its drop-down list", where,
                        "Choose a value from the list (" + "; ".join(allowed[:8]) + ("; …" if len(allowed) > 8 else "") + "). "
                        "Suggested corrections: " + "; ".join(fixes[:6]) + ".",
                        {"kind": "dynamic domain", "sheet": sheet, "column": col, "allowed": allowed, "values": [v for v, _ in items]}))
    return rows, located


# ── service failure ─────────────────────────────────────────────────────────────────────────────────────────────
def _service_failure(path, wb, Row, meta, fa):
    text = open(path, encoding="utf-8-sig", errors="ignore").read()
    step = re.search(r"at \S*\.(\w+)\(", text)
    why = re.search(r"<Error>\s*([\w\.]+): (.*?)(?: at |\s*</Error>)", text, re.S)
    msg = f"{why.group(1).split('.')[-1]}: {why.group(2).strip()[:90]}" if why else "the validation service reported an error"
    return [Row("SPEC", f"The validator failed before checking the return ({msg})", "Not in the return's data",
                "**No change to the data.** The validation service itself did not complete"
                + (f" (it stopped in `{step.group(1)}`)" if step else "")
                + ", so no data check was made. Run the validation again; if it fails the same way, report it to the support team "
                  "together with this file.", {"kind": "service failure"})], 0


# ── CRILC month-on-month reports ───────────────────────────────────────────────────────────────────────────────
def _crilc(path, wb, Row, meta, fa):
    by = collections.OrderedDict()
    for rep in ET.parse(path).getroot().iter("Report"):
        for d in rep.iter("detail"):
            by.setdefault(rep.get("Rule", ""), []).append(dict(d.attrib))
    rows = []
    for rule, details in by.items():
        pans = [d.get("PAN", "") for d in details if d.get("PAN")]
        ex = []
        for d in details[:3]:
            vals = {k: v for k, v in d.items() if k != "PAN" and v != ""}
            ex.append(f"PAN {d.get('PAN', '?')}: " + ", ".join(f"{k}={v}" for k, v in list(vals.items())[:6]))
        rows.append(Row("RULE", f"{rule}: {len(details)} borrower row(s)",
                        f"borrower PANs: {', '.join(pans[:6])}{' …' if len(pans) > 6 else ''}" if pans else "(no borrower identifier)",
                        "**Comparison report, not a mandatory correction.** It lists the borrowers whose reported values differ across "
                        "the compared months, or are present in one month only. Check each borrower; correct the current month only "
                        "if the difference is not intended. First rows: " + " | ".join(ex),
                        {"kind": "month-on-month report", "rule": rule, "borrowers": len(details)}))
    return rows, 0


def _words(concept: str) -> str:
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", concept or "")
