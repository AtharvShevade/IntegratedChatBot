"""Check a proposed fix by arithmetic before anybody is told to make it.

A fix is "set this cell to the value its own formula gives". It is recommended only when the complete failing rule, evaluated again
with that one value replaced (the rule's own rounding, aggregation and comparison included), passes. Nothing here guesses a
number: the replacement is the template formula evaluated over the filer's own workbook values.

    replacement(wb, sheet, row, col0)           -> (formula text, Decimal) or (formula text, None, reason)
    re_evaluate(comp, located, {id(lc): value}) -> the rule's evaluation (dict with 'passes') with those facts replaced
    verify(comp, located, ev, lc, wb)           -> {passes, operands_ok, conflicts, replacement, current, ...}
"""
from __future__ import annotations

from decimal import Decimal

from . import calc_view as cvw
from . import cell_state as cs
from . import excel_eval as xe
from . import explain_workbook as ew

TOL = Decimal("0.005")


def _num(v):
    if isinstance(v, bool) or v is None or v == "":
        return None
    try:
        return Decimal(str(v))
    except Exception:                                              # noqa: BLE001
        return None


def replacement(wb, sheet: str, row: int, col0: int, override: dict | None = None):
    """The value the cell's own formula gives on the workbook's current values: (formula, value, reason).
    The filer's formula is used when the upload has one, else the template's. value is None when it cannot be evaluated here
    or when the formula is a comparison (IF) rather than a calculation. `override` {(sheet, row, col0): value} evaluates the
    formula as if those cells held other values (used to ask what a cell would give once another cell is corrected)."""
    st = cs.state(wb, sheet, row, col0)
    f = st.get("formula") or st.get("template_formula")
    if not f:
        return None, None, "no formula"
    over = {k: float(v) for k, v in (override or {}).items()}
    value = (lambda sh, r, c: over[(sh, r, c)] if (sh, r, c) in over else wb.value(sh, r, c)) if over else wb.value
    info = xe.explain_cell(f, sheet, value)
    if not info:
        return f, None, "the formula cannot be evaluated here"
    if info["kind"] == "check":
        return f, None, "the formula is a comparison of two totals, not a calculation"
    v = _num(info["value"])
    return f, (v.quantize(Decimal("0.000001")) if v is not None else None), "" if v is not None else "the formula gave no number"


def re_evaluate(comp, located: dict, replaced: dict[int, Decimal]) -> dict | None:
    """The rule evaluated again on the error file's facts, with some facts replaced. `replaced` maps id(Located) -> new fact value."""
    by_var: dict[str, list] = {}
    for var, lcs in located.items():
        by_var[var.upper()] = [str(replaced.get(id(lc), lc.fact.value)) for lc in lcs]
    return ew.fx.evaluate(comp, by_var) if comp is not None else None


def verify(comp, located: dict, ev: dict | None, lc, wb, formula_value: Decimal) -> dict:
    """Re-evaluate the whole rule with `lc` set to `formula_value` (workbook units; the template multiplier is applied)."""
    mult = lc.addr.multiplier or 1
    new_fact = formula_value * Decimal(mult)
    ev2 = re_evaluate(comp, located, {id(lc): new_fact})
    problems: list[str] = []
    if ev is not None and ev.get("missing_vars"):
        problems.append("operand(s) of the rule are not in the filing")
    unplaced = [v for v, lcs in located.items() for x in lcs if x.addr is None]
    if unplaced:
        problems.append(f"{len(unplaced)} operand(s) of the rule could not be located in the workbook")
    conflicts = [x.addr.a1 for lcs in located.values() for x in lcs if x.addr is not None and cvw._differs(x)]
    if conflicts:
        problems.append("the workbook and the error file disagree on " + ", ".join(conflicts[:4]))
    if ev2 is None or ev2.get("passes") is None:
        problems.append("the rule could not be evaluated again")
    return {"passes": bool(ev2 and ev2.get("passes")), "ev": ev2, "new_fact": new_fact, "conflicts": conflicts, "problems": problems,
            "verified": bool(ev2 and ev2.get("passes")) and not problems}
