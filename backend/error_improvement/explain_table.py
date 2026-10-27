"""Error-file explanation as an action table:  # | Error (short) | Where in Excel | Solution

    python explain_table.py <metadata folder> <workbook> <error .html> [--out file.md] [--llm] [--model qwen2.5:7b]

Everything in the table is produced by code from the return's metadata, the user's workbook and the error file:
  * which cells are involved           (explain_workbook / fact_address: mapping + workbook value confirmation)
  * which cell is the likely culprit   (a cell row that sits in the most failing rules; ties -> prefer filling an empty cell)
  * the value it should hold           (the failing equation solved for that cell, in the sheet's own unit)
  * data error vs rule behaviour       (equal sides under a strict comparison, one-sided blanks, consistent direction)
No rule name, cell address, sheet name or number is written in this file. With --llm each row also gets a short
plain-language paragraph; every number in it must come from the row's facts or the text is dropped.
"""
from __future__ import annotations

import argparse
import collections
import datetime
import os
import re
import sys
from decimal import Decimal

from . import cell_locator as cl          # noqa: E402
from . import error_html as eh            # noqa: E402
from . import excel_eval as xe            # noqa: E402
from . import explain_llm as el           # noqa: E402
from . import explain_workbook as ew      # noqa: E402
from .direct_errors import ranges      # noqa: E402
from .workbook import Workbook, index_to_col, pick_template      # noqa: E402

D0 = Decimal(0)


# ------------------------------------------------------------------------------------------ formatting
NUMBER_STYLE = "western"        # "western": 1,234,567.89   |   "indian": 12,34,567.89


def num(d: Decimal) -> str:
    """Digit grouping per NUMBER_STYLE, no trailing .00 (196,448.89 / 12,010)."""
    s = f"{abs(d):.2f}"
    ip, _, fp = s.partition(".")
    if NUMBER_STYLE == "indian" and len(ip) > 3:
        head, tail = ip[:-3], ip[-3:]
        ip = re.sub(r"(\d)(?=(\d\d)+$)", r",", head) + "," + tail
    elif NUMBER_STYLE != "indian":
        ip = f"{int(ip):,}"
    out = ip + ("" if fp == "00" else "." + fp)
    return ("-" if d < 0 else "") + out


def _date(s: str) -> str:
    return datetime.datetime.strptime(s, "%Y%m%d").strftime("%d-%b-%Y")


def period(ctx: str) -> str:
    m = re.match(r"asof_(\d{8})", ctx or "")
    if m:
        return f"as on {_date(m.group(1))}"
    m = re.match(r"fromto_(\d{8})_(\d{8})", ctx or "")
    return f"{_date(m.group(1))} to {_date(m.group(2))}" if m else ""


def words(concept: str) -> str:
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", cl.local(concept))


def identity(title: str) -> str:
    t = ew._unescape(title).replace("▼", "")
    t = re.sub(r'^\s*"?en:"?\s*Identity\s*"*', "", t.strip(), flags=re.I)
    t = re.sub(r'"?\s*do not tally\.?"?\s*$', "", t, flags=re.I)
    return t.strip(' "')


def cell_of(lc) -> str:
    return lc.addr.a1 if lc.addr else "?"


def esc(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", " ")


def units(lc, inr: Decimal) -> Decimal:
    return ew._units(lc, inr)


# ------------------------------------------------------------------------------------------ equation tools
def coefficients(comp) -> dict[str, int]:
    coef: dict[str, int] = {}
    for var, sg in comp.lhs.signed_variables():
        coef[var.upper()] = coef.get(var.upper(), 0) + sg
    for var, sg in comp.rhs.signed_variables():
        coef[var.upper()] = coef.get(var.upper(), 0) - sg
    return coef


def candidates(comp, located):
    """[(var, Located, current INR, needed INR)] for cells that could be the wrong one."""
    req = ew.required_values(comp, located)
    out = []
    for var, (cur, need) in sorted(req.items()):
        lc = located[var][0]
        if lc.addr is None or abs(cur - need) < Decimal("0.5") or need < 0:
            continue
        out.append((var, lc, cur, need))
    if len([c for c in out if c[2] == 0]) > 1:      # several identical empty siblings: none can be singled out
        out = [c for c in out if c[2] != 0]
    return out


def composition(comp, located, var):
    """'K96 18,500 + K100 1,77,948.89' - the other cells (non-zero) that give `var` its required value."""
    coef = coefficients(comp)
    parts = []
    for other, c in coef.items():
        if other == var or c == 0:
            continue
        lc = located[other][0]
        val = ew._dec(lc.fact.value) or D0
        if val == 0:
            continue
        if lc.addr is None:
            return ""                         # a term with no known cell: do not print a half-known sum
        sign = -c // coef[var] if coef[var] else 1
        parts.append((sign, f"{cell_of(lc)} {num(units(lc, val))}"))
    if not parts:
        return ""
    txt = ""
    for i, (sg, t) in enumerate(parts):
        txt += (t if i == 0 and sg > 0 else (("- " if sg < 0 else "+ ") + t if i else "-" + t)) + " "
    return txt.strip().replace("+ -", "- ")


# ------------------------------------------------------------------------------------------ rows
class Row:
    def __init__(self, kind, error, where, solution, facts=None):
        self.kind, self.error, self.where, self.solution = kind, error, where, solution
        self.facts = facts or {}
        self.explanation = ""


def a1_(lc) -> str:
    return lc.addr.a1


def _cells_text(cells, wb, sheet, limit=6) -> str:
    """'K96 18,500 + K100 1,77,948.89' - the non-zero cells among `cells`, with their values (other sheets qualified)."""
    parts = []
    for sh, r, c in cells:
        v = wb.value(sh, r, c)
        if isinstance(v, (int, float)) and v:
            ref = f"{index_to_col(c)}{r}" if sh == sheet else f"{sh}!{index_to_col(c)}{r}"
            parts.append(f"{ref} {num(Decimal(str(round(v, 2))))}")
    return " + ".join(parts[:limit]) + (" + ..." if len(parts) > limit else "") if parts else "all empty/0"


def calculated_cell_parts(wb, sheet: str, row: int, col: int, need_units: Decimal | None, short: bool = False):
    """If the template makes this cell a formula: (cause, fix) in plain words, from the user's own numbers; else None.
    `short` gives the one-line version used by the compact card (no cell lists)."""
    graph = getattr(wb, "formulas", None)
    f = graph.formula(sheet, row, col) if graph is not None else None
    if not f:
        return None
    a1 = f"{index_to_col(col)}{row}"
    info = xe.explain_cell(f, sheet, wb.value)
    if not info:
        return (f"{a1} is a calculated cell (formula in the template).",
                "Typing in it is overwritten; correct the cells it is built from.")
    D = lambda x: Decimal(str(round(x, 2)))     # noqa: E731
    if info["kind"] == "check":
        left, right = info["check_left"], info["check_right"]
        if abs(left - right) > 0.004 and info["value"] == info["else"]:
            if short:
                return (f"{a1} is a calculated cell, not an input. It shows {num(D(info['value']))} because its own check fails: "
                        f"the two totals it compares are {num(D(left))} and {num(D(right))} (difference {num(D(left - right))}).",
                        f"Make the two totals equal by correcting their input cells; {a1} then fills itself.")
            return (f"{a1} is a calculated cell, not an input. It shows {num(D(info['value']))} because its own check fails: "
                    f"{_cells_text(info['left_cells'], wb, sheet)} = **{num(D(left))}** but "
                    f"{_cells_text(info['right_cells'], wb, sheet)} = **{num(D(right))}** (difference {num(D(left - right))}).",
                    f"Make the two totals equal by correcting the input cells above; {a1} then fills itself.")
        more = f" It needs {num(need_units - D(info['value']))} more from its inputs." if need_units is not None else ""
        if short:
            return (f"{a1} is a calculated cell built from other cells; its own check holds.",
                    f"Change the cells it is built from, not {a1}.{more}")
        return (f"{a1} is a calculated cell = {_cells_text(info['right_cells'], wb, sheet)}. Its check holds.",
                f"Change the input cells it is built from, not the cell itself.{more}")
    if short:
        return (f"{a1} is a calculated cell built from other cells.",
                (f"To reach {num(need_units)} change those input cells, not {a1}." if need_units is not None
                 else f"Change the input cells it is built from, not {a1}."))
    same = [f"{index_to_col(c)}{r}" for sh, r, c in info["inputs"] if sh == sheet]
    rng = f" (it is built from {ranges(same)})" if same else ""
    return (f"{a1} is a calculated cell = {_cells_text(info['inputs'], wb, sheet)}{rng}.",
            (f"To reach {num(need_units)} change those input cells, not {a1}." if need_units is not None
             else f"Change the input cells it is built from, not {a1}."))


_NUMBERING = re.compile(r"^\s*(?:[IVX]+|\d+(?:\.\d+)*|[a-z])[.)]\s*")


def _component(wb, home: str, ref, verified: bool) -> dict:
    c = _component_raw(wb, home, ref, verified)
    c['status'] = 'Check' if c['state'] in ('empty', 'zero') else ''
    return c


def _component_raw(wb, home: str, ref, verified: bool) -> dict:
    sh, r, c = ref
    a1 = f"{index_to_col(c)}{r}" if sh == home else f"{sh}!{index_to_col(c)}{r}"
    label = _NUMBERING.sub("", wb.text_row(sh, r, 1, 2) or wb.text_row(sh, r, 0, 3) or "").strip()
    label = re.sub(r"\s+", " ", label)[:60]
    if not verified:
        return {"cell": a1, "label": label, "value": "", "state": "unknown"}
    v = wb.value(sh, r, c)
    if v is None or (isinstance(v, str) and not v.strip()):
        return {"cell": a1, "label": label, "value": "empty", "state": "empty"}
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        if v == 0:
            return {"cell": a1, "label": label, "value": "0", "state": "zero"}
        return {"cell": a1, "label": label, "value": num(Decimal(str(round(v, 2)))) if v >= 0 else "-" + num(Decimal(str(round(-v, 2)))),
                "state": "value"}
    return {"cell": a1, "label": label, "value": str(v)[:30], "state": "value"}


def calculated_cell_breakdown(wb, sheet: str, row: int, col: int, limit: int = 6) -> dict | None:
    """How a total cell is built, from the TEMPLATE's own formula (never from row labels or positions).

    None when `wb` has no formula machinery or the cell is a plain input (and not a "total" by its label).
    Otherwise {a1, status, formula, summary, groups[{label, items[{cell,label,value,state}], more, more_blank}], note}.
    status: 'ok' (evaluated), 'unsupported' (formula shown, not evaluated), 'no_formula' (a total without a formula),
    'unreadable' (the template's formulas could not be read). Values are the user's; without the user's workbook they
    are not shown and the note says so."""
    graph = getattr(wb, "formulas", None)
    if wb is None or graph is None:
        return None
    a1 = f"{index_to_col(col)}{row}"
    if not graph.readable():
        return {"a1": a1, "status": "unreadable", "formula": "", "groups": [],
                "summary": f"The template's formulas could not be read, so how {a1} is built is not known.", "note": ""}
    f = graph.formula(sheet, row, col)
    label = wb.text_row(sheet, row, 1, 2)
    if not f:
        if re.search(r"\btotal\b", label or "", re.I):
            return {"a1": a1, "status": "no_formula", "formula": "", "groups": [],
                    "summary": f"No formula is available in the template for {a1}, so its components cannot be listed.", "note": ""}
        return None
    verified = not getattr(wb, "is_template", False)
    text = f.lstrip("=").replace("$", "")
    shown = text if len(text) <= 700 else text[:697] + "..."
    out = {"a1": a1, "formula": f"{a1} = {shown}", "groups": [],
           "note": "" if verified else "The user's workbook is not available, so the values could not be verified."}

    def group(label_, refs):
        items = [_component(wb, sheet, rf, verified) for rf in refs]
        items.sort(key=lambda i: i["state"] in ("empty", "zero"))              # the cells that carry a value first
        head, tail = items[:limit], items[limit:]
        blank = sum(1 for i in tail if i["state"] in ("empty", "zero"))
        return {"label": label_, "items": head, "more": len(tail), "more_blank": blank,
                "more_text": (f"+{len(tail)} more" + (f" ({blank} empty or 0)" if blank else "")) if tail else ""}

    info = xe.explain_cell(f, sheet, wb.value) if verified else None
    if verified and info is None:
        out.update(status="unsupported", summary=f"The formula of {a1} could not be evaluated here, so no calculated value is shown.")
        out["groups"] = [group("", list(dict.fromkeys(xe.refs_of(text, sheet))))]
        return out
    if not verified:
        out.update(status="unsupported", summary=f"{a1} is calculated by the template formula below; values could not be checked.")
        out["groups"] = [group("", list(dict.fromkeys(xe.refs_of(text, sheet))))]
        return out
    D = lambda x: Decimal(str(round(x, 2)))                                     # noqa: E731
    shown_now = wb.value(sheet, row, col)
    now = D(shown_now) if isinstance(shown_now, (int, float)) and not isinstance(shown_now, bool) else None
    out["status"] = "ok"
    out["consistent"] = now is None or abs(now - D(info["value"])) <= Decimal("0.005")
    out["now"] = num(now) if now is not None else ""
    out["calc_value"] = num(D(info["value"]))
    if info["kind"] == "check":
        left, right = info["check_left"], info["check_right"]
        if abs(left - right) > 0.004:
            out["summary"] = (f"{a1} shows {num(D(info['value']))} because its own check fails: the first total is {num(D(left))} "
                              f"but the second is {num(D(right))} (difference {num(D(left - right))}). "
                              "This is a failed comparison of two totals, not a wrong sum.")
        else:
            out["summary"] = f"{a1} = {num(D(info['value']))}: its check holds (both totals are {num(D(left))})."
        out["groups"] = [group("First total", list(dict.fromkeys(info["left_cells"]))),
                         group("Second total", list(dict.fromkeys(info["right_cells"])))]
    else:
        calc = D(info["value"])
        if now is not None and abs(now - calc) > Decimal("0.005"):
            out["summary"] = (f"{a1} shows {num(now)} but its components add up to {num(calc)} "
                              f"(difference {num(now - calc)}).") if info["kind"] == "sum" else \
                             f"{a1} shows {num(now)} but its formula gives {num(calc)} on the workbook's values."
        else:
            out["summary"] = f"{a1} = {num(calc)}: it matches its formula" + (" (the sum of its components)." if info["kind"] == "sum" else ".")
        out["groups"] = [group("", list(dict.fromkeys(info["inputs"])))]
    return out


def calculated_cell_text(wb, sheet: str, row: int, col: int, need_units: Decimal | None):
    parts = calculated_cell_parts(wb, sheet, row, col, need_units)
    return " ".join(parts) if parts else None


_EVIDENCE = {"CONFIRMED": "verified: mapping + workbook value", "MAPPED": "from the mapping; workbook values not checked",
             "INFERRED": "inferred from the workbook / rule definition", "LIKELY": "likely: moderate confidence, please check"}


def data_rows(analysed, wb=None):
    items = [it for it in analysed if it[4] and ew.verdict(it[2], it[4][0][2]) == "DATA"]
    # how many failing rules each (sheet,row) takes part in
    row_hits: collections.Counter = collections.Counter()
    for _r, _e, _c, _k, findings in items:
        for _i, located, _ev in findings:
            row_hits.update({(lc.addr.sheet, lc.addr.row) for v in located.values() for lc in v if lc.addr})
    groups: dict[tuple, dict] = {}
    unfixed: dict[str, list] = {}
    for rule, expr, comp, kind, findings in items:
        for inst, located, ev in findings:
            cands = candidates(comp, located)
            partial = [v for v, l in located.items() if l and not l[0].addr]
            if partial or not cands:                    # an operand we could not place: no single cell can be blamed honestly
                unfixed.setdefault(rule.name, []).append((rule, expr, comp, inst, located, ev))
                continue
            best = max(row_hits[(c[1].addr.sheet, c[1].addr.row)] for c in cands)
            top = [c for c in cands if row_hits[(c[1].addr.sheet, c[1].addr.row)] == best]
            if len(top) > 1:                                  # tie: filling an empty cell beats overwriting a filled one
                empty = [c for c in top if c[2] == 0]
                top = empty or top
            key = tuple(sorted((c[1].addr.sheet, c[1].addr.a1) for c in top))
            lhs, rhs = ew._dec(ev.get("lhs_value", ev.get("lhs"))), ew._dec(ev.get("rhs_value", ev.get("rhs")))
            g = groups.setdefault(key, {"cards": [], "top": top})
            g["cards"].append({"rule": rule.name, "title": identity(inst.title), "comp": comp, "located": located,
                               "lhs": lhs, "rhs": rhs, "top": top, "all": cands, "ctx": inst.facts[0].context,
                               "concept": inst.facts[0].concept})
    rows = []
    for key, g in groups.items():
        first = g["cards"][0]
        titles = list(dict.fromkeys(c["title"] for c in g["cards"]))
        err = f"{titles[0]} does not tally ({words(first['concept'])}, {period(first['ctx'])})"
        if len(g["cards"]) > 1:
            err += f"; the same cell also breaks {len(g['cards']) - 1} other rule(s)"
        if len(err) > 230:
            err = err[:227] + "..."
        involved = []
        for c in g["cards"]:
            for v in sorted(c["located"]):
                for lc in c["located"][v]:
                    if lc.addr and lc.where not in involved:
                        involved.append(lc.where)
        culprits = [f"{c[1].addr.sheet} -> {c[1].addr.a1}" for c in g["top"]]
        doubts = [(c[1].where, c[1].uncertain) for c in g["top"] if c[1].uncertain]
        where = " or ".join(f"{x}?" if c[1].uncertain else x for x, c in zip(culprits, g["top"]))
        ev = sorted({_EVIDENCE.get(c[1].res.status, "") for c in g["top"]} - {""})
        if ev:
            where += "  [" + "; ".join(ev) + "]"
        sol_parts, cinfo = [], []
        for var, lc, cur, need in g["top"]:
            chosen = next((c for c in g["cards"] if any(t[1].where == lc.where for t in c["top"])), g["cards"][0])
            comp_txt = composition(chosen["comp"], chosen["located"], next(t[0] for t in chosen["top"] if t[1].where == lc.where))
            parts = calculated_cell_parts(wb, lc.addr.sheet, lc.addr.row, lc.addr.col, units(lc, need)) if wb is not None else None
            calc = " ".join(parts) if parts else None
            cinfo.append({"sheet": lc.addr.sheet, "a1": lc.addr.a1, "cur": units(lc, cur), "need": units(lc, need),
                          "multiplier": lc.addr.multiplier or 1, "unit": lc.fact.unit, "calc": parts, "status": lc.res.status,
                          "calc_short": (calculated_cell_parts(wb, lc.addr.sheet, lc.addr.row, lc.addr.col, units(lc, need), short=True)
                                         if parts else None),
                          "breakdown": calculated_cell_breakdown(wb, lc.addr.sheet, lc.addr.row, lc.addr.col, limit=500) if wb is not None else None,
                          "uncertain": lc.uncertain, "label": ew._label(wb, lc.addr) if wb is not None else "",
                          "composition": composition(chosen["comp"], chosen["located"],
                                                     next(t[0] for t in chosen["top"] if t[1].where == lc.where))})
            if calc:
                sol_parts.append(calc + f" The rule needs {a1_(lc)} = {num(units(lc, need))} (now {num(units(lc, cur)) if cur else 'empty/0'}).")
                continue
            line = f"Enter **{num(units(lc, need))}** in {lc.addr.a1} (now {num(units(lc, cur)) if cur else 'empty/0'})"
            if comp_txt:
                line += f" = {comp_txt}"
            sol_parts.append(line)
        solution = " ; or ".join(sol_parts)
        if doubts:
            solution += " **Location uncertain** (" + "; ".join(f"{w}: {why}" for w, why in doubts[:2]) + ")."
        alt = [c for c in g["cards"][0]["all"] if (c[1].addr.sheet, c[1].addr.a1) not in
               {(t[1].addr.sheet, t[1].addr.a1) for t in g["top"]}]
        facts = {"kind": "data error", "failing_rules": titles, "culprit_info": cinfo,
                 "rules": list(dict.fromkeys(c["rule"] for c in g["cards"])), "culprit_cells": culprits,
                 "solution": solution, "other_possible_cells": [f"{a[1].where} would need {num(units(a[1], a[3]))}" for a in alt],
                 "involved_cells": involved[:12], "rules_sharing_this_cell": len(g["cards"])}
        rows.append(Row("DATA", err, f"{where}  (involved: {', '.join(i.split('!')[1] for i in involved[:10])})", solution, facts))
    rows.extend(_unfixed_rows(unfixed))
    return rows


def _cells_by_sheet(located):
    by: dict[str, list[str]] = collections.OrderedDict()
    for v in sorted(located):
        for lc in located[v]:
            if lc.addr:
                by.setdefault(lc.addr.sheet, []).append(lc.addr.a1)
    if not by:
        dyn = any(getattr(lc, "dynamic", False) for v in located.values() for lc in v)
        return ("exact row not determinable from the metadata (the sheet adds rows per entry) - needs the filled workbook"
                if dyn else "(not located)")
    return "; ".join(f"{sh} -> {ranges(c)[:110]}" for sh, c in by.items())


def fmt_exact(d: Decimal, places: int = 6) -> str:
    """Ratios and percentages need their digits ('0.0312', not '0.03'); large amounts keep Indian grouping."""
    if abs(d) >= 1000:
        return num(d)
    return (f"{d:.{places}f}".rstrip("0").rstrip(".") or "0")


def decimals_of(comp) -> int | None:
    """How many decimal places the rule compares at, from its own ROUND(... * 10^n) / DIV scaling (None if it has none)."""
    try:
        sc = comp.lhs.rounding_scale()
    except Exception:                                        # noqa: BLE001
        sc = None
    if sc is None or sc <= 0 or sc >= 1:
        return None
    return max(0, -int(sc.log10().to_integral_value(rounding="ROUND_FLOOR")))


_RATIO_KINDS = ("ratio", "percentage", "weighted_average")


def _unfixed_rows(unfixed):
    """Failing identities with no single cell to blame (a variable is a SUM over many facts, or the shape is not
    linear). One row per rule: how many instances, and the left/right values of the first few. The wording follows the
    kind of rule: a ratio is recalculated from its components, a plain total is made to add up."""
    rows = []
    for name, lst in unfixed.items():
        rule, expr, comp, inst0, _lo, _ev = lst[0]
        kind = ew.fk.classify(comp)
        is_ratio = kind in _RATIO_KINDS
        dp = decimals_of(comp) if is_ratio else None
        ex, within_rounding, unlocated = [], 0, 0
        for _r, _e, _c, inst, located, ev in lst:
            l = ew._dec(ev.get("lhs_value", ev.get("lhs"))) if ev else None
            r = ew._dec(ev.get("rhs_value", ev.get("rhs"))) if ev else None
            if l is None or r is None:
                continue
            if is_ratio and dp is not None and abs(l - r) <= Decimal(2) / (Decimal(10) ** dp):
                within_rounding += 1
            if len(ex) >= 3:
                continue
            lc = next((x for v in located.values() for x in v if x.addr), None)
            linear = bool(comp.lhs.signed_variables()) and bool(comp.rhs.signed_variables()) and \
                {v.upper() for v in comp.variables()} == set(coefficients(comp))
            m = lc.addr.multiplier if linear and lc and lc.addr.multiplier else 1       # ratios are not rupee amounts
            if is_ratio:
                ex.append(f"{_cells_by_sheet(located)}: reported {fmt_exact(l / m)}, recalculated {fmt_exact(r / m)} "
                          f"(difference {fmt_exact((l - r) / m)})")
            else:
                miss = sum(1 for v in located.values() if v and not v[0].addr)
                ex.append(f"{_cells_by_sheet(located)}: left {num(l / m)} vs right {num(r / m)} (difference {num((l - r) / m)})"
                          + (f"; {miss} operand(s) not located" if miss else ""))
                unlocated += bool(miss)
        where = "; ".join(dict.fromkeys(_cells_by_sheet(lo) for _r, _e, _c, _i, lo, _v in lst[:3]))
        if not ex:
            sol = "The rule failed but could not be evaluated from the facts in the error file."
        elif is_ratio:
            sol = ("The reported value does not match the value recalculated from its components"
                   + (f" (the check is made at {dp} decimal places)" if dp is not None else "") + ". "
                   + (f"In {within_rounding} of {len(lst)} instance(s) the two differ only in the last rounded digit: check whether "
                      "the reported cell was typed rounded, or calculated with a different rounding. " if within_rounding else "")
                   + "Correct the components, or the reported cell, so that the two agree. First instances: " + " | ".join(ex))
        else:
            sol = ("The totals differ; make the cells add up."
                   + (" Some operands could not be located (they are 0, or the workbook does not show where they are), so the cell "
                      "to correct cannot be singled out: the difference may belong to one of them or to a located cell." if unlocated else "")
                   + " First instances: " + " | ".join(ex))
        label = "does not match its recalculation" if is_ratio else "does not tally"
        rows.append(Row("DATA", f"{identity(inst0.title) or name} {label} ({len(lst)} instance(s))", where, sol,
                        {"kind": "ratio mismatch" if is_ratio else "total mismatch", "rules": [name], "rule_text": expr, "instances": len(lst),
                         "examples": ex, "decimals": dp}))
    return rows


def other_rows(analysed):
    """Rules the code could not classify (presence checks, shapes it does not evaluate)."""
    rows = []
    for rule, expr, comp, kind, findings in analysed:
        if findings and ew.verdict(comp, findings[0][2]) == "UNKNOWN":
            cells = _cells_by_sheet(findings[0][1])
            shown = ew._unescape(expr)
            rows.append(Row("DATA", f"{identity(findings[0][0].title) or rule.name}: check fails in {len(findings)} instance(s) "
                            f"(`{shown}`)", cells,
                            "Presence/consistency check: the cells listed hold a combination of filled and empty values that the "
                            "rule does not allow. Review them against the rule text.",
                            {"kind": "other check", "rules": [rule.name], "rule_text": shown, "instances": len(findings)}))
    return rows


def _cols(located_by_var):
    return ", ".join(f"{v}: {index_to_col(c)}" for v, c in sorted(located_by_var.items()))


def rule_rows(wb, analysed, taken=frozenset()):
    """One row per strict-comparison rule. `taken` = cells already named as culprits in data rows."""
    rows = []
    for rule, expr, comp, kind, findings in analysed:
        if not findings or ew.verdict(comp, findings[0][2]) != "RULE":
            continue
        op = comp.operator
        shown = expr.replace("&gt;", ">").replace("&lt;", "<")
        classes: dict[str, list] = {"equal": [], "missing": [], "reverse": []}
        for inst, located, ev in findings:
            l, r = ew._dec(ev.get("lhs_value", ev.get("lhs"))), ew._dec(ev.get("rhs_value", ev.get("rhs")))
            if l is None or r is None:
                continue
            if l == r:
                classes["equal"].append((located, l, r))
            elif (op == ">" and l == 0 and r > 0) or (op == "<" and r == 0 and l > 0):
                classes["missing"].append((located, l, r))
            else:
                classes["reverse"].append((located, l, r))
        # A rule that mostly fails with the data on the SAME side (left smaller everywhere, non-zero) is behaving
        # as a direction problem; one-sided blanks in that rule are then part of the same pattern, not data gaps.
        if classes["reverse"]:
            classes["reverse"] += classes["missing"]
            classes["missing"] = []
        title = identity(findings[0][0].title)
        name = {v: words(lcs[0].fact.concept) for v, lcs in findings[0][1].items()}

        def where_for(items):
            by_sheet: dict[str, dict[str, set]] = collections.defaultdict(lambda: collections.defaultdict(set))
            for located, _l, _r in items:
                for v, lcs in located.items():
                    for lc in lcs:
                        if lc.addr:
                            by_sheet[lc.addr.sheet][v].add(index_to_col(lc.addr.col))
            return "; ".join(f"{s}: " + " vs ".join(f"{name.get(v, v)} col {'/'.join(sorted(c))}" for v, c in sorted(d.items()))
                             for s, d in by_sheet.items())

        if classes["missing"]:
            items = classes["missing"]
            lhs_var = "V1" if op == ">" else "V2"
            other_var = "V2" if op == ">" else "V1"
            lines, cells = [], []
            for located, l, r in items:
                lc, o = located[lhs_var][0], located[other_var][0]
                if not (lc.addr and o.addr):
                    continue
                big = r if op == ">" else l
                if (lc.addr.sheet, lc.addr.a1) in taken:
                    lines.append(f"{lc.addr.a1}: see the correction above")
                else:
                    lines.append(f"{lc.addr.a1} must be above {num(units(lc, big))} (the value in {o.addr.a1})")
                cells.append(lc.addr.a1)
            rows.append(Row("DATA", f"{title}: entry empty/0 although the other side has a value ({len(items)} instances)",
                            (f"{next(x[0][lhs_var][0] for x in items if x[0][lhs_var][0].addr).addr.sheet} -> {', '.join(cells)}"
                             if cells else "(cells not located)"),
                            "Fill the cells: " + "; ".join(lines),
                            {"kind": "missing entries", "rules": [rule.name], "rule_text": shown, "cells": lines}))
        if classes["equal"] or classes["reverse"]:
            eq, rv = classes["equal"], classes["reverse"]
            zeros = sum(1 for _l, l, _r in eq if l == 0)
            nonzero_eq = [(lo, l) for lo, l, _r in eq if l != 0]
            parts = []
            if eq:
                p = (f"{len(eq)} have equal sides ({zeros} are 0 = 0"
                     + (f"; {len(nonzero_eq)} are equal non-zero values, e.g. "
                        + ", ".join(f"{lo['V1'][0].where} = {num(units(lo['V1'][0], l))}" for lo, l in list({lo['V1'][0].where: (lo, l) for lo, l in nonzero_eq}.values())[:3]) if nonzero_eq else "")
                     + f") - a strict `{op}` cannot hold for equal values")
                parts.append(p)
            if rv:
                side = "smaller" if op == ">" else "larger"
                parts.append(f"{len(rv)} have the left side {side} than the right, and none has it the other way")
            sol = "**No data change.** " + "; ".join(parts) + "."
            if rv:
                sol += (" If the left item is normally " + ("not above" if op == ">" else "not below") +
                        " the right one, the rule itself is written the wrong way round - raise it with the taxonomy owner.")
            rows.append(Row("RULE", f"{title}: fails in {len(eq) + len(rv)} instances",
                            where_for(eq + rv), sol,
                            {"kind": "rule behaviour", "rules": [rule.name], "rule_text": shown, "operator": op, "equal": len(eq),
                             "equal_both_zero": zeros, "sides_differ": len(rv)}))
    return rows


def _sheet_for_rule(rule_name: str, sheets: list[str]) -> list[str]:
    """Of several candidate sheets, the one(s) whose name shares the most words with the rule's name."""
    rn = re.sub(r"[^a-z0-9]", "", rule_name.lower())
    named = [s for s in sheets if len(re.sub(r"[^a-z0-9]", "", s.lower())) >= 4 and re.sub(r"[^a-z0-9]", "", s.lower()) in rn]
    if len(named) == 1:                                     # the rule's own name spells the sheet ('SectionB-...' / 'Section-B')
        return named
    toks = ew._name_tokens(rule_name)
    score = {s: sum(1 for t in toks if t in re.sub(r"[^a-z0-9]", "", s.lower())) for s in sheets}
    best = max(score.values(), default=0)
    return [s for s in sheets if score[s] == best] if best else sheets


def _count_row(rule, expr, comp, inst, located, found: int, needed: int) -> "Row":
    """A rule that counts entries (`count($V1) >= N`): say how many were reported against how many are required, where the
    counted entries are, and what else the rule's facts show (a condition fact is not a total)."""
    in_expr = {v.upper() for v in comp.variables()}
    counted = [lc for v in in_expr for lc in located.get(v, [])]
    sheets = list(dict.fromkeys([a.sheet for lc in counted for a in ([lc.addr] if lc.addr else []) + (lc.res.addresses if lc.res else [])]))
    sheets = _sheet_for_rule(rule.name, sheets) if sheets else []
    where = " or ".join(sheets) + (" (the table that holds these entries)" if sheets else "")
    conds = []
    for v, lcs in located.items():
        if v.upper() not in in_expr and lcs:
            f = lcs[0].fact
            conds.append(f"{words(f.concept)} is {f.value}" + (f" at {lcs[0].where}" if lcs[0].addr else ""))
    op = {">=": "at least", ">": "more than", "<=": "at most", "<": "fewer than", "=": "exactly"}.get(comp.operator, comp.operator)
    gap = needed - found
    sol = f"The rule needs {op} {needed} entries here, but {found} were reported" + \
        (f": add {gap} more." if gap > 0 and comp.operator in (">=", ">") else ".")
    if conds:
        sol += " The rule applies because " + "; ".join(conds) + "."
    return Row("DATA", f"{(identity(inst.title) or rule.name).rstrip('.: ')}: {found} entries reported, {op} {needed} required",
               where or "(table not located)", sol,
               {"kind": "record count", "rules": [rule.name], "rule_text": expr, "found": found, "needed": needed, "conditions": conds})


def cover_rows(analysed):
    rows = []
    for rule, expr, comp, kind, findings in analysed:
        if not findings or ew.verdict(comp, findings[0][2]) != "COVER":
            continue
        for inst, located, ev in findings:
            l, r = ew._dec(ev.get("lhs_value", ev.get("lhs"))), ew._dec(ev.get("rhs_value", ev.get("rhs")))
            if kind == "count" and comp.rhs is not None and comp.rhs.kind == "num" and l is not None:
                rows.append(_count_row(rule, expr, comp, inst, located, int(l), int(comp.rhs.value)))
                continue
            cells = [lc for v in sorted(located) for lc in located[v] if lc.addr]
            left = [lc for lc in located.get("V1", []) if lc.addr]
            right = [lc for lc in located.get("V2", []) if lc.addr]
            mult = left[0].addr.multiplier if left else 1
            short = (r - l) if l is not None and r is not None else None
            where = "; ".join(f"{s} -> {', '.join(c.addr.a1 for c in cs)}" for s, cs in
                              collections.OrderedDict((s, [c for c in cells if c.addr.sheet == s])
                                                      for s in dict.fromkeys(c.addr.sheet for c in cells)).items())
            sol = (f"Total on the left ({', '.join(c.addr.a1 for c in left)}) = {num(l / mult)} must be at least the total on the right "
                   f"({', '.join(c.addr.a1 for c in right)}) = {num(r / mult)}: short by **{num(short / mult)}**. "
                   "Correct the left cells (or the right ones if they are overstated); the code cannot tell which "
                   "category inside the total is short from this rule alone.")
            rows.append(Row("DATA", f"{identity(inst.title)} - left total smaller than right total", where, sol,
                            {"kind": "coverage", "rules": [rule.name], "rule_text": expr, "shortfall": num(short / mult) if short is not None else "",
                             "left_total": num(l / mult), "right_total": num(r / mult)}))
    return rows


def spec_row(spec):
    if not spec:
        return []
    detail = "; ".join(f"{n} x {name.split(':')[-1]} ({msg[:60]})" for name, msg, _c, n in spec)
    return [Row("SPEC", f"SPECIFICATION_ERROR -> TABLE ({sum(x[3] for x in spec)} warnings)",
                "Not in Excel (template/taxonomy table definition)",
                f"**Ignore** - these are warnings about the table definition, not about your data. ({detail})",
                {"kind": "specification", "count": sum(x[3] for x in spec)})]


# ------------------------------------------------------------------------------------------ output
def build(folder, workbook, html_path, use_llm, model):
    meta = cl.load_form_folder(folder, os.path.basename(folder.rstrip("/\\")))
    wb = Workbook(workbook) if workbook else pick_template(meta, folder)
    html = open(html_path, encoding="utf-8", errors="ignore").read()
    analysed = ew.analyse(meta, wb, eh.parse_rules(html))
    data = data_rows(analysed)
    taken = {tuple(c.split(" -> ")) for r in data for c in r.facts.get("culprit_cells", [])}
    rows = data + cover_rows(analysed) + other_rows(analysed) + rule_rows(wb, analysed, taken) + spec_row(eh.spec_warnings(html))
    rows.sort(key=lambda r: {"DATA": 0, "RULE": 1, "SPEC": 2}[r.kind])
    if use_llm:
        for r in rows:
            out = el.ask(model, {**r.facts, "task": "Explain this row in 2 sentences for the filer: put it in 'problem'; "
                                                   "'why' = why it fails; 'action' = what to do."})
            if out and all(out.values()) and el.guard(" ".join(out.values()), {**r.facts, "s": r.solution, "e": r.error}):
                r.explanation = f"{out['problem']} {out['why']} {out['action']}"
    return rows, analysed


def render(rows, analysed, meta_name, wb_name):
    n_inst = sum(len(a[4]) for a in analysed)
    L = [f"# Error explanation - {wb_name}", f"{len(analysed)} failing rules, {n_inst} failing instances, "
         f"metadata folder {meta_name}.\n",
         "| # | Error (short) | Where in Excel | Solution (what to correct) |", "|---|---|---|---|"]
    for i, r in enumerate(rows, 1):
        L.append(f"| {i} | {esc(r.error)} | {esc(r.where)} | {esc(r.solution)} |")
    data = sum(1 for r in rows if r.kind == "DATA")
    L.append(f"\nRows 1-{data} need corrections in the Excel; the remaining {len(rows) - data} need no data change.")
    if any(r.explanation for r in rows):
        L.append("\n## Plain-language notes (LLM wording, numbers checked against the facts)\n")
        for i, r in enumerate(rows, 1):
            if r.explanation:
                L.append(f"{i}. {r.explanation}")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--workbook", default=None, help="filed workbook; omit to run from the metadata + template only")
    ap.add_argument("html")
    ap.add_argument("--out")
    ap.add_argument("--llm", action="store_true")
    ap.add_argument("--model", default="qwen2.5:7b")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    rows, analysed = build(a.folder, a.workbook, a.html, a.llm, a.model)
    text = render(rows, analysed, os.path.basename(a.folder.rstrip("/\\")), os.path.basename(a.workbook or a.html))
    if a.out:
        open(a.out, "w", encoding="utf-8").write(text)
    print(text)


if __name__ == "__main__":
    main()
