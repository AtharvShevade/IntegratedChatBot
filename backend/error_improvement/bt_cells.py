"""The validator's own backtracking (BT) record as the primary cell location.

A `*_BTDetails.html` error file carries, for each failing value, the Excel sheet and the cell code the validator traced it to
(`Excel SheetName`, `Cell Code`: error_html keeps them on `Fact.extra`). When a fact has both, the cell is the one the return's mapping
gives for that code on that sheet: the validator's answer is used and the workbook only confirms it. A fact without them, or whose code
the mapping cannot turn into exactly one cell, is left to the engine's own search; nothing here guesses.

    apply(located, meta, wb)   marks each fact it places with `lc.bt = True`; `lc.bt_other` names the cell our own search had chosen
                               when that is a different one
"""
from __future__ import annotations

import re

from . import fact_address as fa


def _norm(s) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower())


def attach(rules, error_file: str) -> int:
    """The BT file of the same run (`<stem>_BTDetails.html` beside `<stem>_Instance.html`) names no item, only where each value came from.
    Join its rows to the ordinary report's facts by rule, context and value; a fact gets the BT record only when exactly one BT row fits
    it. Returns how many facts got one."""
    import os
    from . import error_html as eh
    stem = re.sub(r"_(Instance|BTDetails)(\s*\(\d+\))?\.html$", "", error_file, flags=re.I)
    path = stem + "_BTDetails.html"
    if stem == error_file or not os.path.isfile(path) or os.path.abspath(path) == os.path.abspath(error_file):
        return 0
    try:
        bt_rules = eh.parse_rules(open(path, encoding="utf-8", errors="ignore").read())
    except OSError:
        return 0
    truth: dict = {}
    for r in bt_rules:
        for inst in r.instances:
            for f in inst.facts:
                if f.extra.get("Cell Code"):
                    truth.setdefault((r.name, f.context, _norm(f.value)), []).append(f.extra)
    n = 0
    for r in rules:
        for inst in r.instances:
            for f in inst.facts:
                rows = truth.get((r.name, f.context, _norm(f.value)), [])
                if len({(x.get("Excel SheetName"), x.get("Cell Code")) for x in rows}) == 1:
                    f.extra, n = dict(rows[0]), n + 1
    return n


def table_layouts(meta, table: str) -> set:
    """Layout ids whose data a database table holds (`TabelMapping.xml`: PriID is the layout id, 'a|b' when one table serves several
    layouts, e.g. a standalone and a consolidated sheet). Empty when the return has no such file or table."""
    cache = meta.__dict__.setdefault("_bt_tables", {}) if hasattr(meta, "__dict__") else {}
    if not cache:
        import os
        import xml.etree.ElementTree as ET
        path = os.path.join(getattr(meta, "folder", "") or "", "TabelMapping.xml")
        try:
            for row in ET.parse(path).getroot().iter("Row"):
                ids = {i.strip() for i in (row.get("PriID") or "").split("|") if i.strip()}
                cache.setdefault(_norm(row.get("TableName")), set()).update(ids)
        except (OSError, ET.ParseError):
            cache["<none>"] = set()                                       # looked, nothing there: do not read the file again
    return cache.get(_norm(table), set())


def _unique(cands) -> "fa.Address | None":
    cells = {(a.sheet, a.row, a.col): a for a in cands}
    return next(iter(cells.values())) if len(cells) == 1 else None


def apply(located: dict, meta, wb) -> int:
    """Place every fact the BT record names. Returns how many were placed (or confirmed) from it."""
    placed = 0
    template = getattr(wb, "is_template", False)
    for lcs in located.values():
        for lc in lcs:
            ex = getattr(lc.fact, "extra", None) or {}
            if getattr(lc.addr, "is_db", False):
                # A database location of ours: the validator's own record is only compared with it. Agreement is evidence; a
                # difference makes our location uncertain (it is not silently replaced and not asserted).
                tbl, cc = _norm(ex.get("DB TableName")), _norm(ex.get("Cell Code"))
                if tbl and cc:
                    if tbl == _norm(lc.addr.table) and cc == _norm(lc.addr.cell_code):
                        lc.bt = True
                    else:
                        lc.bt_db_other = f"{ex.get('DB TableName')} / cell code {ex.get('Cell Code')}"
                        lc.uncertain = ("the validator's backtracking record names " + lc.bt_db_other
                                        + ", which is not the table and cell code found from the return's metadata")
                continue
            code, sheet = _norm(ex.get("Cell Code")), _norm(ex.get("Excel SheetName"))
            layouts = table_layouts(meta, ex.get("DB TableName")) if not sheet and ex.get("DB TableName") else set()
            if not code or not (sheet or layouts) or not lc.fact.concept:
                continue                                              # no BT record for this fact, or none that names a sheet or a known table
            try:
                cands = [a for a in fa.candidates(meta, wb, lc.fact.concept, lc.fact.context)
                         if _norm(a.cell_code) == code and (_norm(a.sheet) == sheet if sheet else a.layout_id in layouts)]
            except Exception:                                         # noqa: BLE001  never lose the explanation over the BT record
                continue
            a = _unique(cands)
            if a is None:
                continue                                              # the code does not name one cell here: our own search stays
            before = lc.addr
            if template:
                target = fa._dec(lc.fact.value)
                if target is not None and a.multiplier:
                    a.workbook_value = float(target / a.multiplier)
                status = "MAPPED"
            else:
                status = "CONFIRMED" if fa.value_matches(a, lc.fact.value, lc.fact.decimal) else "MAPPED"
            lc.res = fa.Resolved(status, [a], "the validator's backtracking record")
            lc.addr, lc.bt, lc.dynamic, lc.uncertain = a, True, False, ""
            if before is not None and (before.sheet, before.row, before.col) != (a.sheet, a.row, a.col):
                lc.bt_other = f"{before.sheet}!{before.a1}"
            placed += 1
    return placed


def card_source(located: dict) -> tuple[bool, list[str]]:
    """(every located value of the card came from the BT record, the cells our own search would have put elsewhere)."""
    lcs = [lc for v in located.values() for lc in v if lc.addr]
    if not lcs or not all(getattr(lc, "bt", False) for lc in lcs):
        return False, []
    return True, [f"{lc.where} (BT) vs {lc.bt_other} (our search)" for lc in lcs if getattr(lc, "bt_other", "")]
