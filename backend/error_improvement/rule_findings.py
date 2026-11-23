"""Per-rule decision, made at run time from what the analysis found for THAT rule: a full backtracking card, or the plain explanation
plus the few findings that are proven.

A rule gets the full card when the analysis can name where to correct it:
  * a target cell: the culprit proven by cross-rule arithmetic, or a cell of the reported (left) side, placed with CONFIRMED, INFERRED
    or MAPPED evidence (MAPPED = the return's own mapping + template, checked against the validator's answer key at 747/748; never a
    guess from the workbook alone), and
  * enough of the rule's other values placed (COVERAGE) that the cell table is not mostly "not located".
Nothing here knows a return, a sheet or a rule: it reads the Located facts the analysis already built.

Otherwise the rule is explained the existing way and `findings()` supplies what is still proven, as plain sentences built from fixed
wording with the real values filled in (never written by a model):
  * the cell a fact is mapped to holds another value than the filing reports (the workbook is not what was filed);
  * a filed value is nowhere in the uploaded workbook;
  * a rounding failure (the figure is right, the filing was too coarse);
  * where some of the rule's values do sit.
"""
from __future__ import annotations

import os
import re
from decimal import Decimal

from . import explain_table as et
from . import explain_workbook as ew
from . import fact_address as fa

GOOD = ("CONFIRMED", "INFERRED", "MAPPED")       # evidence good enough to tell a user which cell to correct (LIKELY is a guess: never)
MAX_FINDINGS = 5


def min_coverage() -> float:
    try:
        return min(1.0, max(0.0, float(os.environ.get("ERROR_IMPROVEMENT_MIN_COVERAGE", "0.5"))))
    except ValueError:
        return 0.5


def _lhs_vars(comp) -> list[str]:
    try:
        return [v.upper() for v, _ in comp.lhs.signed_variables()]
    except Exception:                                                                       # noqa: BLE001
        return []


def _key(var) -> str:
    """A variable name as the rule writes it: the error file's own spelling can carry stray quotes or spaces (`"V3`)."""
    return re.sub(r"[^A-Za-z0-9_]", "", str(var)).upper()


def target(located: dict, comp, culprit, any_operand: bool = False) -> tuple[str, str] | None:
    """(sheet, cell) the rule's correction is about, or None. any_operand: the rule is a per-unit conditional (see conditional_rules),
    which has no left side: the first placed and verified operand stands for it."""
    if culprit:
        return culprit
    by_name: dict[str, list] = {}
    for var, lcs in located.items():
        by_name.setdefault(_key(var), []).extend(lcs)
    lhs_vars = _lhs_vars(comp)
    for var in lhs_vars:
        for lc in by_name.get(_key(var), []):
            if lc.addr is not None and lc.res.status in GOOD:
                return lc.addr.sheet, lc.addr.a1
    if any_operand and not lhs_vars and not getattr(comp, "operator", "x"):
        # "if A > 0 then B div A >= T" has no left side to take the cell from; every operand it checks is equally part of it.
        for lcs in located.values():
            for lc in lcs:
                if lc.addr is not None and lc.res.status in GOOD:
                    return lc.addr.sheet, lc.addr.a1
    return None


def coverage(located: dict) -> float:
    """Share of the rule's reported values that were placed in a cell (facts the filing does not carry are not counted:
    the rule counts them as 0 and no cell exists for them)."""
    real = [lc for lcs in located.values() for lc in lcs if lc.fact.concept]
    if not real:
        return 1.0
    return sum(1 for lc in real if lc.addr is not None) / len(real)


def decide(located: dict, comp, culprit, conditional: bool = False) -> tuple[bool, str]:
    """(full card?, why not). Computed per rule from this rule's own data. conditional: a per-unit conditional rule (see target)."""
    if target(located, comp, culprit, conditional) is None:
        return False, "no cell could be named for the reported value"
    cov = coverage(located)
    if cov < min_coverage():
        return False, f"only {cov:.0%} of the rule's values could be placed in the workbook"
    return True, ""


# ── findings ────────────────────────────────────────────────────────────────────────────────────────────────────
def _num(v):
    return fa._dec(v)


def _plain(v) -> str:
    """A number as the user reads it: thousands separators, no trailing zeros, no currency (a ratio is not money)."""
    d = _num(v)
    if d is None:
        return str(v)
    q = d.normalize()
    return f"{q:,.{max(0, -q.as_tuple().exponent)}f}"


def _name(rc, lc, names) -> str:
    """The item as the rule's own wording calls it, else the context-based name; kept short and never cut inside a bracket."""
    n = (names or {}).get(lc.fact.var.upper()) or rc._item_name(lc.fact) or lc.fact.var
    if len(n) <= 90:
        return n
    base = n.split(" (")[0].strip()                         # 'Domestic (Gross Advances (Standard))' -> keep the part before the bracket
    if 0 < len(base) <= 90:
        return base
    return n[:87].rstrip(" ,(") + "..."


def _held(a):
    """What a cell holds, in the units the filing uses (a sheet in lakhs holds 10.12 where the filing reports 1,012,000)."""
    return a.scaled if a.scaled is not None else a.workbook_value


def _differs(lc):
    """(sheet, cell, workbook value) when the cell this fact is mapped to holds another value than the filing reports."""
    if lc.addr is not None or lc.res.status != "UNCONFIRMED":
        return None
    want = _num(lc.fact.value)
    if want is None or want == 0:
        return None
    for a in lc.res.addresses or []:
        if a.workbook_value in (None, "") or isinstance(a.workbook_value, str):
            continue
        have = a.scaled
        if have is not None and abs(have - want) > fa.tolerance(want, lc.fact.decimal):
            return a.sheet, a.a1, have
    return None


def findings(located: dict, wb, comp, ev, dp, names: dict | None = None) -> list[str]:
    """Proven statements about this rule, in plain words. [] when nothing is proven."""
    from . import rule_cards as rc
    out: list[str] = []
    guess = rc._db_guess_note(located)                      # database return: the table cells to look at, named but not confirmed
    if guess:
        out.append(guess)
    user_book = wb is not None and not getattr(wb, "is_template", False) and getattr(wb, "path", "")
    mapped, absent = [], []
    for lcs in located.values():
        for lc in lcs:
            if lc.addr is not None or not lc.fact.concept:
                continue
            d = _differs(lc)
            if d:
                mapped.append((lc, d))
            elif user_book and _num(lc.fact.value) not in (None, Decimal(0)) and not ew._value_known(wb, lc.fact.value):
                absent.append(lc)
    for lc, (sheet, a1, have) in mapped[:2]:
        out.append(f"{_name(rc, lc, names)}: the cell it is mapped to, {sheet}!{a1}, holds {_plain(have)} "
                   f"but the filing reports {_plain(lc.fact.value)}.")
    for lc in absent[:2]:
        out.append(f"{_name(rc, lc, names)}: the filed value {_plain(lc.fact.value)} is not anywhere in the uploaded workbook.")
    left = len(mapped) - min(2, len(mapped)) + len(absent) - min(2, len(absent))
    if left > 0:
        out.append(f"{left} more value(s) of this rule differ from the filing in the same way.")
    if mapped or absent:
        out.append("The uploaded workbook may not be the file that was filed, or it was changed (or not recalculated and saved) afterwards: "
                   "upload the filed version, or correct and file it again.")
    try:
        note = rc.rounding_note(comp, located, ev, dp).strip() if ev else ""
    except Exception:                                                                       # noqa: BLE001
        note = ""
    if note:
        out.append(note)
    if out:                                                  # where the other values sit helps only next to a real finding
        placed = [lc for lcs in located.values() for lc in lcs
                  if lc.addr is not None and lc.res.status in GOOD and lc.fact.concept and lc.addr.workbook_value not in (None, "")]
        for lc in placed[:3]:
            out.append(f"{_name(rc, lc, names)} is in {lc.addr.sheet}!{lc.addr.a1} (it holds {_plain(_held(lc.addr))}).")
    return out[:MAX_FINDINGS]
