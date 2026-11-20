"""Find the cell that actually breaks a failing rule, prove it by arithmetic, and link the rules that share it.

For each failing '=' rule: look at the cells the rule uses. A cell is a suspect only when it should be calculated (the filer's
workbook holds a formula, or the template does and the filer typed over it) AND the value its own formula gives differs from the
value it holds. Plain inputs are never suspects: nobody is told to change a valid input to make a rule pass.

A suspect is the root cause only if the whole rule, evaluated again with that one cell set to its formula's value, passes
(fix_check.verify). When one cell clears several rules, that cell is the shared root cause: the rule that is a restatement of the
cell's own formula is the primary error, the others are linked to it. Anything that cannot be shown this way is left alone, so
the card keeps its ordinary wording instead of asserting a fix.

    analyse(analysed, wb) -> {rule name: rc}
      rc: role ('primary' | 'secondary'), primary (rule name), others [rule names the same fix clears], fix {...}, verified, problems,
          consistent [calculated-looking cells of this rule that already equal their formula], not_cleared [rules that use the cell
          but would still fail], ambiguous (when several different cells would each clear the rule: nothing is asserted)
"""
from __future__ import annotations

from . import cell_state as cs
from . import excel_eval as xe
from . import fix_check as fc


def _candidates(comp, located: dict, wb):
    """([suspects], [consistent cells]) among the cells the rule uses."""
    suspects, consistent, seen = [], [], set()
    for var, lcs in located.items():
        for lc in lcs:
            a = lc.addr
            if a is None or (a.sheet, a.a1) in seen:
                continue
            seen.add((a.sheet, a.a1))
            st = cs.state(wb, a.sheet, a.row, a.col)
            if st["state"] not in ("overwritten", "formula"):
                continue
            formula, value, _why = fc.replacement(wb, a.sheet, a.row, a.col)
            cur = fc._num(a.workbook_value)
            if value is None or cur is None:
                continue
            item = {"lc": lc, "var": var.upper(), "state": st["state"], "formula": formula, "current": cur, "replacement": value,
                    "multiplier": a.multiplier or 1, "sheet": a.sheet, "a1": a.a1, "row": a.row, "col": a.col}
            (consistent if abs(cur - value) <= fc.TOL else suspects).append(item)
    return suspects, consistent


def _refs(item: dict) -> set:
    return set(xe.refs_of((item["formula"] or "").lstrip("=").replace("$", ""), item["sheet"]))


def _drop_downstream(fixers: list) -> list:
    """A cell whose own formula reads another fixer's cell only looks wrong because of that cell: keep the cells whose inputs are
    not themselves implicated, so the one actual root cause remains."""
    keep = [(s, v) for s, v in fixers
            if not any((o["sheet"], o["row"], o["col"]) in _refs(s) for o, _ in fixers if o is not s)]
    return keep or fixers


def _restates(p: dict, item: dict) -> bool:
    """The rule is the cell's own formula written as a rule: the cell on one side, exactly the formula's inputs on the other."""
    comp = p["comp"]
    try:
        sides = [{v.upper() for v in comp.lhs.variables()}, {v.upper() for v in comp.rhs.variables()}]
    except Exception:                                              # noqa: BLE001
        return False
    mine = next((i for i, s in enumerate(sides) if item["var"] in s), None)
    if mine is None or sides[mine] != {item["var"]}:
        return False
    other = sides[1 - mine]
    cells = {(a.sheet, a.row, a.col) for v in other for lc in p["located"].get(v, []) for a in [lc.addr] if a is not None}
    text = (item["formula"] or "").lstrip("=").replace("$", "")
    refs = set(xe.refs_of(text, item["sheet"]))
    return bool(cells) and cells == refs


def analyse(analysed, wb) -> dict[str, dict]:
    if wb is None or getattr(wb, "is_template", False) or getattr(wb, "upload_formulas", None) is None:
        return {}                                          # the filer's own formulas are needed to know what is calculated
    per: dict[str, dict] = {}
    for i, (rule, _expr, comp, _kind, findings) in enumerate(analysed):
        if not findings or comp is None or comp.operator != "=":
            continue
        _inst, located, ev = findings[0]
        if not ev or ev.get("boolean_only") or ev.get("passes") is not False:
            continue
        suspects, consistent = _candidates(comp, located, wb)
        fixers = []
        for s in suspects:
            v = fc.verify(comp, located, ev, s["lc"], wb, s["replacement"])
            if v["passes"]:
                fixers.append((s, v))
        per[rule.name] = {"name": rule.name, "order": i, "comp": comp, "located": located, "ev": ev, "consistent": consistent,
                          "suspects": suspects, "fixers": _drop_downstream(fixers)}
    out: dict[str, dict] = {}
    groups: dict[tuple, list[str]] = {}
    for name, p in per.items():
        cells = {(s["sheet"], s["a1"]) for s, _v in p["fixers"]}
        if len(cells) == 1:
            s, v = p["fixers"][0]
            p["fix"] = (s, v)
            for o in p["suspects"]:                         # other cells that only disagree with their formula because of the fix
                if o is s:
                    continue
                _f, val, _w = fc.replacement(wb, o["sheet"], o["row"], o["col"], {(s["sheet"], s["row"], s["col"]): s["replacement"]})
                if val is not None and abs(o["current"] - val) <= fc.TOL:
                    p["consistent"].append({**o, "after_fix": True})
            groups.setdefault((s["sheet"], s["a1"]), []).append(name)
        elif len(cells) > 1:
            out[name] = {"role": None, "ambiguous": sorted(a for _s, a in cells), "verified": False, "problems": [], "consistent": []}
    for key, names in groups.items():
        primary = max(names, key=lambda n: (_restates(per[n], per[n]["fix"][0]), -per[n]["order"]))
        uncleared = [n for n, p in per.items() if n not in names and any(
            lc.addr is not None and (lc.addr.sheet, lc.addr.a1) == key for lcs in p["located"].values() for lc in lcs)]
        for n in names:
            s, v = per[n]["fix"]
            out[n] = {"role": "primary" if n == primary else "secondary", "primary": primary,
                      "others": [m for m in names if m != n], "not_cleared": uncleared,
                      "fix": {"sheet": s["sheet"], "a1": s["a1"], "state": s["state"], "formula": s["formula"],
                              "current": s["current"], "replacement": s["replacement"], "multiplier": s["multiplier"], "var": s["var"]},
                      "verified": v["verified"], "problems": v["problems"], "ev": v["ev"],
                      "consistent": [{"sheet": c["sheet"], "a1": c["a1"], "state": c["state"], "formula": c["formula"],
                                      "current": c["current"], "multiplier": c["multiplier"], "var": c["var"],
                                      "after_fix": bool(c.get("after_fix"))}
                                     for c in per[n]["consistent"]]}
    return out


def cell_name(item: dict) -> str:
    return f"{item['sheet']}!{item['a1']}"


