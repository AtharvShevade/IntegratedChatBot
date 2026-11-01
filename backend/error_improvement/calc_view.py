"""One explanation structure for every calculation-type rule (totals, weighted averages, ratios, percentages, equalities, comparisons).

The rule's own parsed formula says what each operand IS (an amount and its rate, a numerator, a denominator, a component of a total,
the left or right side). This module turns that, plus the located cells, into the "Contributing cells" block the card shows:
the formula in plain words, then every operand with its role, cell, label, value and status. Nothing here evaluates or locates
anything new; it only names what the engine already found, and it says which operands it could not place.
"""
from __future__ import annotations

import re
from decimal import Decimal

CALC_KINDS = ("aggregate", "ratio", "percentage", "weighted_average", "equality", "threshold")
_WRAP = {"round", "abs", "floor", "ceiling", "number"}
_PREC = {"+": 1, "-": 1, "*": 2, "div": 2, "idiv": 2}
_SYM = {"+": "+", "-": "−", "*": "×", "div": "÷", "idiv": "÷"}


def _strip(node):
    """Look through rounding/abs wrappers and a division by a plain number (`round(x*10000) div 10000`)."""
    while node is not None:
        if node.kind == "func" and node.name in _WRAP and node.args:
            node = node.args[0]
        elif node.kind == "binop" and node.op in ("*", "div", "idiv") and len(node.args) == 2:
            l, r = node.args
            if r.kind == "num" and l.variables():
                node = l
            elif l.kind == "num" and r.variables() and node.op == "*":
                node = r
            else:
                return node
        else:
            return node
    return node


def _terms(node, sign=1):
    """[(node, sign)] of an additive expression."""
    node = _strip(node) if node is not None and node.kind == "func" else node
    if node is not None and node.kind == "binop" and node.op in ("+", "-") and len(node.args) == 2:
        return _terms(node.args[0], sign) + _terms(node.args[1], sign if node.op == "+" else -sign)
    if node is not None and node.kind == "unary" and node.args:
        return _terms(node.args[0], -sign)
    return [(node, sign)]


_RATE_WORD = re.compile(r"rate|percent|ratio|yield|cost", re.I)


def _pairs(num, den_vars, concepts):
    """[(amount_var, rate_var)] when every numerator term is amount x rate (two variables multiplied); else None."""
    pairs = []
    for term, _sg in _terms(num):
        term = _strip(term)
        tv = [v.upper() for v in term.variables()]
        if term.kind != "binop" or term.op != "*" or len(set(tv)) != 2:
            return None
        a, b = tv[0], tv[1]
        rate_a, rate_b = bool(_RATE_WORD.search(concepts.get(a, ""))), bool(_RATE_WORD.search(concepts.get(b, "")))
        if rate_a and not rate_b:
            a, b = b, a
        elif not rate_a and not rate_b and b in den_vars and a not in den_vars:
            a, b = b, a
        pairs.append((a, b))
    return pairs or None


def roles(comp, kind: str, concepts: dict | None = None) -> tuple[dict[str, str], str]:
    """({VAR: role}, shape) from the shape of the rule. shape: pairs | ratio | sum | sides.
    Variables the shape does not explain get 'Left side' / 'Right side'."""
    concepts = {k.upper(): v for k, v in (concepts or {}).items()}
    shape = "sides"
    out: dict[str, str] = {}
    lhs, rhs = comp.lhs, comp.rhs
    lvars = [v.upper() for v in lhs.variables()]
    rvars = [v.upper() for v in (rhs.variables() if rhs is not None else [])]
    core = _strip(rhs) if rhs is not None else None
    ratio_kinds = ("ratio", "percentage", "weighted_average")
    if kind in ratio_kinds and core is not None and core.kind == "binop" and core.op in ("div", "idiv") and len(core.args) == 2:
        num, den = core.args
        den_vars = {v.upper() for v in den.variables()}
        name = {"weighted_average": "Reported average", "percentage": "Reported percentage"}.get(kind, "Reported ratio")
        pairs = _pairs(num, den_vars, concepts) if kind in ("ratio", "weighted_average") else None
        if pairs:
            shape = "pairs"
            name = "Reported average"
            for i, (a, b) in enumerate(pairs, 1):
                out.setdefault(a, f"Amount {i}")
                out.setdefault(b, f"Rate {i}")
            for v in den_vars:
                out.setdefault(v, "Total amount")
        for v in lvars:
            out[v] = name
        if pairs:
            pass
        elif kind == "weighted_average":
            n = 0
            for term, _sg in _terms(num):
                term = _strip(term)
                tv = [v.upper() for v in term.variables()]
                amt = [v for v in tv if v in den_vars]
                rate = [v for v in tv if v not in den_vars]
                if amt and rate:
                    n += 1
                    out.setdefault(amt[0], f"Amount {n}")
                    out.setdefault(rate[0], f"Rate {n}")
        else:
            shape = "ratio"
            for v in (x.upper() for x in num.variables()):
                out.setdefault(v, "Numerator")
            for v in den_vars:
                out.setdefault(v, "Denominator")
    elif kind == "aggregate" and rhs is not None and len(lvars) == 1:
        shape = "sum"
        out[lvars[0]] = "Reported total"
        n = 0
        for v, sg in core.signed_variables() if core is not None else []:
            n += 1
            out.setdefault(v.upper(), f"Component {n}" + ("" if sg > 0 else " (subtracted)"))
    for v in lvars:
        out.setdefault(v, "Left side")
    for v in rvars:
        out.setdefault(v, "Right side")
    return out, shape


def render_formula(comp, names: dict[str, str], limit: int = 240) -> str:
    """The rule in words: variables replaced by their roles, rounding wrappers dropped. Cut at `limit` characters."""
    def r(n, parent=0):
        if n is None:
            return ""
        if n.kind == "var":
            return names.get(n.name.upper(), n.name)
        if n.kind == "num":
            return format(n.value.normalize(), "f") if n.value is not None else "?"
        if n.kind == "func":
            if n.name in _WRAP and n.args:
                return r(n.args[0], parent)
            return f"{n.name}(" + ", ".join(r(a) for a in n.args) + ")"
        if n.kind == "unary":
            return "−" + r(n.args[0], 3)
        if n.kind == "binop" and len(n.args) == 2:
            if n.op in ("div", "idiv", "*") and n.args[1].kind == "num" and n.args[0].variables():
                return r(n.args[0], parent)                        # rounding scale such as `div 10000`
            p = _PREC.get(n.op, 0)
            s = f"{r(n.args[0], p)} {_SYM.get(n.op, n.op)} {r(n.args[1], p + (1 if n.op in ('-', 'div', 'idiv') else 0))}"
            return f"({s})" if p < parent else s
        return "?"
    left = r(comp.lhs)
    right = r(comp.rhs) if comp.rhs is not None else ""
    text = f"{left} {comp.operator} {right}".strip() if right else left
    text = re.sub(r"^\((.*)\)$", r"\1", text) if text.count("(") == text.count(")") else text
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


_A1 = re.compile(r"^([A-Z]+)(\d+)$")


def _col_n(col: str) -> int:
    n = 0
    for ch in col:
        n = n * 26 + ord(ch) - 64
    return n


def cell_ref(cells: list[tuple[str, str]], limit: int = 6) -> tuple[str, str]:
    """([(sheet, a1)]) -> (sheet text, cell text): 'B3:B12' when the cells are consecutive in one column or row, else a short list."""
    sheets = list(dict.fromkeys(s for s, _a in cells))
    one = len(sheets) == 1
    a1s = [a for _s, a in cells]
    m = [_A1.match(a) for a in a1s]
    if len(a1s) > 1 and all(m) and one:
        cols, rows = [x.group(1) for x in m], [int(x.group(2)) for x in m]
        if len(set(cols)) == 1 and sorted(rows) == list(range(min(rows), min(rows) + len(rows))):
            return sheets[0], f"{cols[0]}{min(rows)}:{cols[0]}{max(rows)}"
        if len(set(rows)) == 1:
            ns = sorted(_col_n(c) for c in cols)
            if ns == list(range(ns[0], ns[0] + len(ns))):
                lo = min(cols, key=_col_n)
                hi = max(cols, key=_col_n)
                return sheets[0], f"{lo}{rows[0]}:{hi}{rows[0]}"
    shown = a1s[:limit] if one else [f"{s}!{a}" for s, a in cells[:limit]]
    text = ", ".join(shown) + (f" +{len(cells) - limit} more" if len(cells) > limit else "")
    return (sheets[0] if one else "Several sheets"), text


def _linear(node) -> bool:
    """Only variables, + / -, sign flips, sum() and rounding wrappers: the side is a plain total of cells."""
    if node is None:
        return False
    if node.kind == "var":
        return True
    if node.kind == "func" and node.name in _WRAP | {"sum"} and len(node.args) == 1:
        return _linear(node.args[0])
    if node.kind == "unary" and node.args:
        return _linear(node.args[0])
    if node.kind == "binop" and node.op in ("+", "-") and len(node.args) == 2:
        return _linear(node.args[0]) and _linear(node.args[1])
    return False


def _dec(v):
    try:
        return Decimal(str(v))
    except Exception:                                              # noqa: BLE001
        return None


def _side(node, located: dict, counts: dict) -> dict:
    """What one side of the rule stands for: its located cells, how many cells the filing has for it, and how to name it."""
    core = _strip(node)                                            # look through round(... * 10000) div 10000 and abs()
    linear = _linear(core)
    signed = []
    if linear:
        try:
            signed = [(v.upper(), sg) for v, sg in core.signed_variables()]
        except Exception:                                          # noqa: BLE001
            linear = False
    variables = [v.upper() for v in node.variables()] if not signed else [v for v, _ in signed]
    variables = list(dict.fromkeys(variables))
    cells, expected, partial = [], 0, Decimal(0)
    signs = dict(signed)
    for v in variables:
        lcs = located.get(v) or located.get(v.lower()) or []
        expected += int(counts.get(v, len(lcs)) or 0)
        for lc in lcs:
            if lc.addr is None:
                continue
            cells.append((lc.addr.sheet, lc.addr.a1))
            val = _dec(lc.fact.value)
            if val is not None:
                partial += val * (signs.get(v, 1) if linear else 1)
    single = bool(core is not None and core.kind == "var" and expected == 1 and len(cells) == 1)
    return {"cells": cells, "expected": expected, "found": len(cells), "linear": linear, "single": single,
            "all_plus": linear and all(sg > 0 for _v, sg in signed), "partial": partial,
            "missing": max(0, expected - len(cells))}


def comparison(comp, located: dict, ev: dict | None, fmt, names=("Reported", "Calculated")) -> dict | None:
    """The one table every calculation card shows: Sheet Name | Cell | Value for each side of the rule, then the difference.

    Values are the rule's own (from the error file), so the table, the difference and the explanation always agree. A side that
    is one cell shows that cell; a total shows 'Sum of B3:B12'; anything else shows 'Calculated from N cells'. When some cells of
    a side could not be located, the rule's own value is still shown, the located cells are shown separately with their own sum,
    and a warning says how many are missing. Returns None when the rule has no numbers to compare.
    """
    if comp is None or not ev or comp.rhs is None:
        return None
    lv, rv = _dec(ev.get("lhs_value", ev.get("lhs"))), _dec(ev.get("rhs_value", ev.get("rhs")))
    if lv is None or rv is None:
        return None
    counts = {str(k).upper(): v for k, v in (ev.get("fact_counts") or {}).items()} if isinstance(ev.get("fact_counts"), dict) else {}
    sides = [_side(comp.lhs, located, counts), _side(comp.rhs, located, counts)]
    if not sides[0]["cells"]:
        return None
    rows, notes = [], []
    for i, (side, val) in enumerate(zip(sides, (lv, rv))):
        role = names[i]
        if not side["cells"]:
            if side["expected"] == 0 and not side["linear"]:
                continue
            rows.append({"label": f"{role} value", "sheet": "", "cell": "", "value": fmt(val), "tone": "", "code": False})
            if side["expected"]:
                notes.append(f"None of the {side['expected']} cell(s) behind the {role.lower()} value could be located; "
                             "the value shown is the rule's own.")
            continue
        sheet, ref = cell_ref(side["cells"])
        side["ref"] = ref
        if side["single"]:
            cell = ref
        elif side["linear"] and side["all_plus"]:
            cell = f"Sum of {ref}"
        elif side["linear"]:
            cell = f"Calculated from {ref}"
        else:
            cell = f"Calculated from {len(side['cells'])} cells"
        side["label"] = cell
        rows.append({"label": f"{sheet}!{cell}", "sheet": sheet, "cell": cell, "value": fmt(val), "tone": "", "code": True})
        if side["missing"]:
            rows[-1]["partial"] = True
            n, m = side["missing"], side["expected"]
            notes.append(f"{n} of {m} components of the {role.lower()} value could not be located, so the cells listed are incomplete.")
            if side["linear"] and not side["single"]:
                rows.append({"label": f"{sheet}!located:{cell}", "sheet": sheet, "cell": f"Located cells only ({side['found']} of {m})",
                             "value": fmt(side["partial"]), "tone": "", "code": False})
                notes.append(f"The value above is the rule's own. The {side['found']} located cell(s) alone add up to {fmt(side['partial'])}, "
                             "so that is not the full total.")
        elif side["linear"] and not side["single"] and abs(side["partial"] - val) > max(
                Decimal("0.0005") * abs(val), Decimal("0.005") * len(side["cells"])):          # filed figures are rounded (to thousands, lakhs...)
            notes.append(f"The listed cells add up to {fmt(side['partial'])}, but the rule calculated {fmt(val)} for the {role.lower()} "
                         "value. The workbook and the error file may disagree on some of these cells.")
    absent = [v for v in (ev.get("missing_vars") or [])]
    if absent:
        notes.append(f"{len(absent)} operand(s) of the rule are not in the filing; the rule counts them as 0.")
    diff = abs(lv - rv)
    rows.append({"label": "Difference", "sheet": "", "cell": "", "value": fmt(diff), "tone": "bad", "code": False})
    return {"rows": rows, "diff": diff, "left": lv, "right": rv, "notes": notes, "sides": sides,
            "complete": not any(s["missing"] for s in sides)}


def _differs(lc) -> bool:
    """The workbook cell holds a different number than the filing, beyond the rounding the filing's own decimals allow."""
    a = lc.addr
    if a is None or a.workbook_value is None:
        return False
    try:
        wv = Decimal(str(a.workbook_value)) * Decimal(a.multiplier or 1)
        fv = Decimal(str(lc.fact.value))
    except Exception:                                              # noqa: BLE001
        return False
    d = None
    try:
        d = int(str(lc.fact.decimal))
    except Exception:                                              # noqa: BLE001
        pass
    tol = (Decimal(5) / (Decimal(10) ** (d + 1)) if d is not None and d >= 0 else Decimal(0)) + Decimal("0.0000001") * (abs(fv) + 1)
    if d is not None and d < 0:
        tol = Decimal(5) * (Decimal(10) ** (-d - 1)) + tol
    return abs(wv - fv) > tol


def contributing(comp, kind, located, wb, label_fn, value_fn, limit: int = 60) -> dict | None:
    """The shared 'Contributing cells' block, or None when the rule has no operands to list."""
    concepts = {v.upper(): lcs[0].fact.concept for v, lcs in located.items() if lcs}
    names, shape = roles(comp, kind, concepts)
    order = [v.upper() for v in comp.variables()]
    every = {}
    for v in order:
        lcs = located.get(v) or located.get(v.lower()) or []
        if lcs:
            every[v] = list(lcs)
    if not every:
        return None
    # reported (left side) first, then the operands in the rule's own order; an operand that stands for many cells
    # (sum($V2) over a whole column) contributes every one of them
    lhs_vars = [v.upper() for v in comp.lhs.variables()]
    seq = lhs_vars + [v for v in order if v not in lhs_vars]
    pairs_ = []
    comp_n = 0
    for v in dict.fromkeys(seq):
        for k, lc in enumerate(every.get(v, []), 1):
            role = names.get(v, v)
            if len(every[v]) > 1:
                if role.startswith("Component"):
                    comp_n += 1
                    role = f"Component {comp_n}" + (" (subtracted)" if role.endswith("(subtracted)") else "")
                else:
                    role = f"{role} ({k})"
            elif role.startswith("Component"):
                comp_n += 1
                role = f"Component {comp_n}" + (" (subtracted)" if role.endswith("(subtracted)") else "")
            pairs_.append((role, lc))
    items, unlocated, differing, blank = [], [], 0, 0
    for role, lc in pairs_:
        if lc.addr is None:
            unlocated.append(role)
            items.append({"cell": role, "label": (getattr(lc, "reason", "") or "not located in the workbook")[:160], "value": value_fn(lc, None), "state": "unknown",
                          "status": "Not located", "role": role})
            continue
        label = label_fn(wb, lc.addr)
        val = value_fn(lc, lc.addr)
        empty = lc.addr.workbook_value in (None, "") or lc.addr.workbook_value == 0
        state = "zero" if lc.addr.workbook_value == 0 else ("empty" if lc.addr.workbook_value in (None, "") else "value")
        status = ""
        if _differs(lc):
            status, differing = "Differs from filing", differing + 1
        elif empty:
            status, blank = "Check", blank + 1
        items.append({"cell": lc.addr.a1 if True else "", "label": f"{role}" + (f" · {label}" if label else ""), "value": val,
                      "state": state, "status": status, "role": role, "sheet": lc.addr.sheet})
    shown = items[:limit]
    n = len(items)
    sub = f"{n} contributing cells identified"
    if unlocated:
        sub += f" · {len(unlocated)} could not be located"
    if differing:
        sub += f" · {differing} differ from the error file"
    elif blank:
        sub += f" · {blank} empty or zero"
    note = []
    if unlocated:
        note.append("Not located in the workbook (values are as in the error file): " + ", ".join(unlocated[:8])
                    + (f" and {len(unlocated) - 8} more" if len(unlocated) > 8 else "") + ".")
    if differing:
        note.append("Differs from filing: the workbook cell holds a different number than the error file reports, beyond rounding. "
                    "Either the workbook changed after the filing or this cell is not the one the rule reads; check before relying on it.")
    return {"heading": "Contributing cells", "status_title": "Formula read from the rule", "status_sub": sub,
            "toggle": f"View all {n} contributing cells", "toggle_sub": "Cell references, roles, values and status",
            "formula": render_formula(comp, names), "summary": "",
            "groups": [{"label": "", "items": shown, "more": n - len(shown),
                        "more_text": f"+{n - len(shown)} more" if n > len(shown) else ""}],
            "note": " ".join(note), "unlocated": len(unlocated), "differing": differing, "kind": "operands", "shape": shape}


def steps_for(kind: str, shape: str, blank: bool, differing: bool, unlocated: bool) -> list[str]:
    first = {"pairs": "Verify each amount and rate pair against the source data.",
             "ratio": "Verify the numerator and denominator values against the source data.",
             "sum": "Verify each component against the source data."}.get(shape, "Verify both values against the source data.")
    s = [first]
    if differing:
        s.append("Check the cells marked \"Differs from filing\": the workbook and the error file disagree on their values.")
    if blank:
        s.append("Check whether zero or empty values are expected.")
    if unlocated:
        s.append("Locate the operands marked \"Not located\" in the workbook; they could not be placed automatically.")
    s.append({"pairs": "Confirm that the reported average is the figure the return should show.",
              "ratio": "Confirm that the reported ratio is the figure the return should show.",
              "sum": "Confirm that the reported total is the figure the return should show."}.get(shape, "Confirm which of the compared values is intended."))
    return s
