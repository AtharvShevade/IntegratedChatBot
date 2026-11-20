"""One explanation CARD per failing rule, in the format the product shows to the user:

    N. <rule name>
    Checks:          what the rule compares, in the rule's own words
    Problem:         what does not match
    Cause:           why (the cell(s) and numbers behind it, or why a calculated cell shows what it shows)
    Fix:             what to verify / correct
    Related impact:  other failing rules that use the same cell (only when there are any)
    Cell details     table: Item | Sheet | Cell | Row label | Current value
    Calculation details  table: Description | Amount
    Explanation:     how the text was produced, and the evidence behind the cell locations

The card is built from what the table code (explain_table) already worked out for the rule, so the wording of the cause and
fix never says more than the evidence supports: a located, value-confirmed cell is stated; an inferred one says so; when an
operand could not be placed the card says the difference cannot be pinned on one cell.

    build_cards(analysed, wb, rows)  -> {rule name: card}
    card_to_sections(card)           -> list of UI sections (headline / labeled_text / table / note)
    card_to_text(card)               -> plain text with the same content
"""
from __future__ import annotations

import collections
import contextvars
import re
from decimal import Decimal

from . import absent_operands as ao
from . import calc_view as cvw
from . import bt_cells
from . import cell_context as cc
from . import table_titles as _tt
from . import conditional_rules as cond
from . import currency as cur_
from . import root_cause as rcs
from . import rule_findings as rfd
from . import explain_table as et
from . import explain_workbook as ew
from . import fact_address as fa
from .workbook import index_to_col

_UNIT_WORD = {1000: "thousand", 100000: "lakh", 10000000: "crore"}
_EVIDENCE_TEXT = {
    "CONFIRMED": "verified against your workbook (the return's mapping and the cell value agree)",
    "MAPPED": "taken from the return's mapping; the workbook values were not checked",
    "INFERRED": "inferred from the workbook (value and labels), not checked against the return's mapping",
    "LIKELY": "a likely match from the workbook alone (moderate confidence): please check the cells",
}


# ── number formatting ───────────────────────────────────────────────────────────────────────────────────────────
def _plain(d: Decimal, places: int = 2) -> str:
    d = Decimal(d)
    s = f"{d:,.{places}f}"
    return s


# What goes in front of an amount. Set per rule from the unit of the rule's own facts (see _set_currency); '₹' only until a rule sets it.
_CURRENCY = contextvars.ContextVar("ei_currency", default="₹")


def _set_currency(located) -> bool:
    """Take the currency of this rule's amounts from its facts' units. False when it cannot be established (amounts are then shown
    without a symbol and the card says so). A rule whose facts carry no unit information at all keeps the previous symbol."""
    facts = [lc.fact for lcs in located.values() for lc in lcs]
    if not facts or not any(hasattr(f, "unit") for f in facts):
        return True
    code = cur_.of_facts(facts)
    units = {cur_.normalise(getattr(f, "unit", "")) for f in facts} - {""}
    if code:
        _CURRENCY.set(cur_.prefix(code))
        return True
    if not units and all((getattr(f, "unit", "") or "").strip().upper() in ("PURE", "SHARES", "INF", "") for f in facts) and \
            any((getattr(f, "unit", "") or "").strip().upper() in ("PURE", "SHARES") for f in facts):
        _CURRENCY.set("")                                    # ratios and counts: never a currency symbol (not the one a previous rule set)
        return True
    _CURRENCY.set("")
    return False


def money(inr: Decimal) -> str:
    """An amount in the rule's currency: ₹28,062,200,000 / QAR 70,000,000 (no decimals when whole)."""
    d = Decimal(inr)
    if not _CURRENCY.get():
        return et.fmt_exact(d)                               # no currency: the number with the digits it has (a rate 0.1511 stays 0.1511)
    return _CURRENCY.get() + (f"{d:,.0f}" if d == d.to_integral() else f"{d:,.2f}")


def cell_money(value: Decimal, multiplier: int, unit: str) -> str:
    """A value in the sheet's own unit: ₹196,448.89 lakh. Non-monetary values (ratios, counts) stay plain."""
    d = Decimal(value)
    code = cur_.normalise(unit)
    pf = cur_.prefix(code) if code else None                 # a symbol only for a unit that is a currency; no unit, no assumption
    if pf is not None and multiplier in _UNIT_WORD:
        return f"{pf}{d:,.2f} {_UNIT_WORD[multiplier]}"
    if code:
        return f"{pf}{d:,.2f}"
    return et.fmt_exact(d)


def _fmt_code(code: str):
    """A formatter for amounts in one currency (its symbol) or, for '', plain numbers."""
    if code:
        pf = cur_.prefix(code)
        return lambda d: pf + (f"{Decimal(d):,.0f}" if Decimal(d) == Decimal(d).to_integral() else f"{Decimal(d):,.2f}")
    return lambda d: _plain(d, 0 if Decimal(d) == Decimal(d).to_integral() else 2)


def _side_code(node, located):
    """The currency of one side of a rule, from the units of the facts it is made of: 'INR' when every fact of the side is in INR; ''
    (plain numbers) when they show no monetary unit or mix units; None when the facts carry no unit information at all."""
    facts = [lc.fact for v in node.variables() for lc in (located.get(v.upper()) or located.get(v) or [])]
    if not facts or not all(hasattr(f, "unit") for f in facts):
        return None
    codes = {cur_.normalise(getattr(f, "unit", "")) for f in facts}
    return next(iter(codes)) if len(codes) == 1 else ""


def _side_scale(node, located):
    """The sheet's unit of one side (cell value x scale = filed value) when every located cell of the side has the same one, else None."""
    scales = {lc.addr.multiplier or 1 for v in node.variables() for lc in (located.get(v.upper()) or located.get(v) or []) if lc.addr}
    return next(iter(scales)) if len(scales) == 1 else None


def _compare_fmts(comp, located):
    """(left, right, difference) formatters for a rule that compares two sides: each side in its own unit, the difference in the unit
    both share and plain when they differ (a count compared with an amount has no currency of its difference). None when the facts say
    nothing about units."""
    if comp is None or comp.rhs is None:
        return None
    lc, rc = _side_code(comp.lhs, located), _side_code(comp.rhs, located)
    if lc is None or rc is None:
        return None
    ml, mr = _side_scale(comp.lhs, located), _side_scale(comp.rhs, located)
    if ml and ml == mr and ml != 1:                                    # both sides are kept in lakh / crore ...: show the figures as the sheet does
        plain = _fmt_code("")
        scaled = lambda d: plain(Decimal(d) / ml)                       # noqa: E731
        return scaled, scaled, scaled
    fl, fr = _fmt_code(lc), _fmt_code(rc)
    return fl, fr, (fl if lc == rc else _fmt_code(""))


def _side_name(node, located) -> str:
    """What one side of the rule is called: the measure's own name when the side is one measure, else '' (the caller says 'total')."""
    concepts = {lc.fact.concept for v in node.variables() for lc in (located.get(v.upper()) or located.get(v) or []) if lc.fact.concept}
    return et.words(next(iter(concepts))).lower() if len(concepts) == 1 else ""


def _cmp_sentence(op: str, lt: Decimal, rt: Decimal, ln: str, rn: str, fl, fr, fd) -> str:
    """The failed comparison in words that agree with the numbers: 'The A (54) exceeds the B (34) by 20.' / 'is below ... by'."""
    gap = abs(lt - rt)
    a, b = f"The {ln} ({fl(lt)})", f"the {rn} ({fr(rt)})"
    if op in ("<=", "<") and lt > rt:
        return f"{a} exceeds {b} by {fd(gap)}."
    if op in (">=", ">") and lt < rt:
        return f"{a} is less than {rn} ({fr(rt)}) by {fd(gap)}."
    if lt == rt and op in ("<", ">"):
        return f"{a} equals {b}, but the rule needs it to be {'smaller' if op == '<' else 'greater'}."
    return f"{a} and {b} differ by {fd(gap)}."


def _raw(v) -> str:
    if v is None or v == "":
        return "(blank)"
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, (int, float)):
        return f"{v:.2f}"
    return str(v).strip()


def _end(text: str) -> str:
    t = (text or "").strip()
    return t if not t or t[-1] in ".!?" else t + "."


def _clean(text: str) -> str:
    return re.sub(r"\*\*", "", text or "").strip()


# ── pieces ──────────────────────────────────────────────────────────────────────────────────────────────────────
def _order(comp) -> list[str]:
    if comp is None:
        return []
    return [v.upper() for v, _ in comp.lhs.signed_variables()] + \
           [v.upper() for v, _ in (comp.rhs.signed_variables() if comp.rhs is not None else [])]


def _item_name(f) -> str:
    """'Gross Advances (Standard Advances)': the dimension members name the row's meaning, the concept names the measure."""
    members = sorted(fa.context_members(f.context))
    meaning = " ".join(re.sub(r"Member$", "", et.words(m)).strip() for m in members[:2]).strip()
    measure = et.words(f.concept).strip()
    return f"{meaning} ({measure})" if meaning and measure else (meaning or measure)


def _cell_rows(wb, located, comp, culprit=None, limit: int = 10) -> list[dict]:
    order = _order(comp)
    var_order = list(dict.fromkeys(order + [v.upper() for v in located]))
    items = [(lc, var) for var in var_order for lc in located.get(var, [])[:2]]
    if culprit:                                                   # the cell the explanation is about goes first
        items.sort(key=lambda t: 0 if (t[0].addr and (t[0].addr.sheet, t[0].addr.a1) == culprit) else 1)
    rows = []
    for lc, var in items[:limit]:
        f = lc.fact
        if lc.addr:
            a = lc.addr
            rows.append({"item": _item_name(f), "sheet": a.sheet, "cell": a.a1,
                         "row_label": (ew._label(wb, a) or "").strip(), "current": _raw(a.workbook_value)})
        else:
            rows.append({"item": _item_name(f) or f.var, "sheet": "—", "cell": "not located", "row_label": "",
                         "current": f"{money(Decimal(str(f.value)))} (reported in the filing)" if _num(f.value) else str(f.value)})
    more = len(items) - len(rows)
    if more > 0:
        rows.append({"item": f"… and {more} more value(s) in this rule", "sheet": "", "cell": "", "row_label": "", "current": ""})
    return rows


def _num(v) -> bool:
    try:
        Decimal(str(v))
        return True
    except Exception:                                              # noqa: BLE001
        return False


def _calc_rows(verdict: str, kind: str, comp, ev, row) -> list[tuple[str, str]]:
    if not ev:
        return []
    l = ew._dec(ev.get("lhs_value", ev.get("lhs")))
    r = ew._dec(ev.get("rhs_value", ev.get("rhs")))
    if l is None or r is None:
        return []
    if kind in et._RATIO_KINDS:
        dp = et.decimals_of(comp)
        out = [("Reported value", et.fmt_exact(l)), ("Recalculated from its components", et.fmt_exact(r)),
               ("Difference", et.fmt_exact(l - r))]
        if dp is not None:
            out.append(("Compared at", f"{dp} decimal places"))
        return out
    if kind == "count":
        needed = int(comp.rhs.value) if comp.rhs is not None and comp.rhs.kind == "num" else None
        out = [("Entries reported", str(int(l)))]
        if needed is not None:
            out += [("Entries required", str(needed)), ("Short by", str(max(0, needed - int(l))))]
        return out
    op = comp.operator
    if verdict == "RULE":
        return [("Left side", money(l)), ("Right side", money(r)), ("The rule requires left " + {">": "greater than", "<": "smaller than"}.get(op, op) + " right", "not met")]
    return [("Left side", money(l)), ("Right side", money(r)), ("Difference", money(l - r))]


def _evidence(located) -> tuple[str, str]:
    st = [lc.res.status for lcs in located.values() for lc in lcs if lc.addr]
    if not st:
        return "none", "the cells could not be located in the workbook"
    for k in ("LIKELY", "INFERRED", "MAPPED"):
        if k in st:
            return k, _EVIDENCE_TEXT[k]
    return "CONFIRMED", _EVIDENCE_TEXT["CONFIRMED"]


def _phrase_rhs(terms: list[str]) -> str:
    rest = terms[1:]
    if not rest:
        return "the other side of the rule"
    if len(rest) == 1:
        return rest[0]
    shown = ", ".join(rest[:3]) + (" and others" if len(rest) > 3 else "")
    return f"the sum of {shown}"


def _row_triple(r, lhs_term, terms_list, eq_problem, located, ev):
    """(problem, cause, fix) for one table row of a rule."""
    k = r.facts.get("kind", "")
    sol = _clean(r.solution)
    problem = cause = fix = ""
    if k in ("total mismatch", "ratio mismatch"):
        ratio = k == "ratio mismatch"
        problem = (f"{lhs_term} does not match its recalculation." if ratio else
                   (eq_problem or f"{lhs_term} does not match {_phrase_rhs(terms_list)}."))
        missing = sum(1 for lcs in located.values() for lc in lcs if not lc.addr)
        if ratio:
            ex0 = (r.facts.get("examples") or [""])[0]
            cause = "The reported value differs from the value recalculated from its components. " + (_clean(ex0) + "." if ex0 else "")
            dp = r.facts.get("decimals")
            fix = "Correct the components, or the reported cell, so that the two agree" + (
                f" (the check is made at {dp} decimal places)." if dp is not None else ".")
        else:
            diff = ""
            if ev and ew._dec(ev.get("lhs_value", ev.get("lhs"))) is not None and ew._dec(ev.get("rhs_value", ev.get("rhs"))) is not None:
                diff = f" by {money(abs(ew._dec(ev.get('lhs_value', ev.get('lhs'))) - ew._dec(ev.get('rhs_value', ev.get('rhs')))))}"
            cause = ("The two sides differ" + diff + "."
                     + (f" {missing} operand(s) could not be located in the workbook (they are 0, or their cell is not shown), so the "
                        "difference cannot be pinned on one cell." if missing else ""))
            fix = ("Compare the cells in the table with your source data and fill any operand that should not be 0; "
                   "the two sides must be equal." if missing else "Make the cells add up.")
    elif k == "rule behaviour":
        problem = f"The rule's comparison fails for these values ({_clean(r.error).split(':')[0][:120]})."
        cause = sol.replace("No data change.", "").strip()
        fix = "No data change is needed for the equal-valued cases if these values are correct: the rule is written as a strict comparison."
        if "wrong way round" in sol:
            fix += " If the left item is normally not above the right one, raise the rule with the taxonomy owner."
    elif k == "record count":
        problem = f"The number of entries is below what the rule requires ({r.facts.get('found')} of {r.facts.get('needed')})."
        cause = sol
        fix = "Add the missing entries (or correct the condition the rule depends on)."
    elif k == "coverage":
        ln, rn = r.facts.get("left_name") or "left total", r.facts.get("right_name") or "right total"
        over = r.facts.get("direction") == "exceeds"
        problem = f"The {ln} is {'greater' if over else 'smaller'} than the {rn}."
        lp, rp = r.facts.get("left_prefix", ""), r.facts.get("right_prefix", "")
        cause = (f"The {ln} ({lp}{r.facts.get('left_total')}) {'exceeds' if over else 'is less than'} the {rn} ({rp}{r.facts.get('right_total')}) "
                 f"by {lp if lp == rp else ''}{r.facts.get('shortfall')}.")
        fix = ("Correct the left cells (or the right ones if they are understated); the rule alone does not say which category is off."
               if over else
               "Correct the left cells (or the right ones if they are overstated); the rule alone does not say which category is short.")
    elif k == "missing entries":
        problem = "An entry is empty although the other side has a value."
        cause = "Some cells are empty/0 while the cells they are compared with are filled."
        fix = sol
    else:
        problem = "A presence or consistency condition of the rule is not met."
        cause = "The cells listed hold a combination of filled and empty values that the rule does not allow."
        fix = "Review them against the rule text."
    return problem, cause, fix


# ── the card ────────────────────────────────────────────────────────────────────────────────────────────────────
def _CASE_WORD(card: dict) -> str:
    """Which failing case the cells belong to: the first, or the one whose cells could be placed when the first's could not."""
    return "one of the failing cases (the first could not be placed in the workbook)" if card.get("case_moved") else "the first failing case"


def _coverage(finding) -> float:
    """How well one failing case's values are placed: a cell the evidence settles counts 1, a weak match from the workbook alone a quarter."""
    lcs = [lc for v in finding[1].values() for lc in v]
    firm = lambda lc: lc.res.status in ("CONFIRMED", "MAPPED", "INFERRED") and not lc.uncertain                  # noqa: E731
    return sum((1.0 if firm(lc) else 0.25) for lc in lcs if lc.addr) / len(lcs) if lcs else 0.0


def _best_first(findings: list) -> tuple[list, bool]:
    """A rule that fails in many cases is explained through one of them. The first case is the one shown unless some other case has more of
    its values placed in the workbook (a total whose cells repeat elsewhere cannot be pinned down, while a case in a particular column
    can): then that case leads. -> (findings, whether another case now leads)."""
    if len(findings) < 2:
        return findings, False
    best = max(range(len(findings)), key=lambda i: (_coverage(findings[i]), -i))
    if best and _coverage(findings[best]) > _coverage(findings[0]):
        return [findings[best]] + findings[:best] + findings[best + 1:], True
    return findings, False


def build_cards(analysed, wb, rows, numbering: dict | None = None) -> dict[str, dict]:
    reordered = set()
    fixed = []
    for rule, expr, comp, kind, findings in analysed:
        findings, moved = _best_first(findings)
        if moved:
            reordered.add(rule.name)
        fixed.append((rule, expr, comp, kind, findings))
    analysed = fixed
    by_rule: dict[str, list] = collections.defaultdict(list)
    for r in rows:
        for rn in r.facts.get("rules", []):
            by_rule[rn].append(r)
    number = dict(numbering) if numbering else {}
    for i, it in enumerate(analysed):
        number.setdefault(it[0].name, i + 1)
    cards = {}
    try:
        roots = rcs.analyse(analysed, wb)                 # the cells that actually break the rules, proven by arithmetic
    except Exception:                                      # noqa: BLE001 - an extra analysis; never lose the cards over it
        roots = {}
    for rule, expr, comp, kind, findings in analysed:
        if not findings:
            continue
        inst, located, ev = findings[0]
        currency_known = _set_currency(located)
        verdict = ew.verdict(comp, ev) if ev else "UNKNOWN"
        title_raw = ew._title_of(inst)
        terms_list = ao.split_terms(title_raw)
        order = _order(comp)
        terms = dict(zip(order, terms_list)) if order and len(terms_list) == len(order) else {}
        checks = et.identity(inst.title) or rule.name
        card = {"rule_name": rule.name, "number": number[rule.name], "checks": checks[:260], "kind": kind, "verdict": verdict,
                "case_moved": rule.name in reordered,
                "cells": [], "calc": _calc_rows(verdict, kind, comp, ev, None),
                "instances": len(findings), "related": None, "other_cases": None}
        ev_key, ev_text = _evidence(located)
        card["evidence_key"], card["evidence"] = ev_key, ev_text
        card["bt"], card["bt_differs"] = bt_cells.card_source(located)
        lhs_term = terms_list[0] if terms_list else (et.words(inst.facts[0].concept) if inst.facts else "The reported value")
        mine = by_rule.get(rule.name, [])
        data_groups = [r for r in mine if r.facts.get("kind") == "data error"]
        problem = cause = fix = ""
        culprit = ((data_groups[0].facts["culprit_info"][0]["sheet"], data_groups[0].facts["culprit_info"][0]["a1"])
                   if data_groups else None)
        card["cells"] = _cell_rows(wb, located, comp, culprit)
        lhs_raw, _, rhs_raw = checks.partition("=")
        eq_problem = (f"{lhs_raw.strip()} does not equal {rhs_raw.strip()}." if rhs_raw.strip() else "")

        if data_groups:                                   # a single culprit cell was found by cross-rule evidence
            g = data_groups[0]
            ci = g.facts["culprit_info"][0]
            problem = eq_problem or f"{lhs_term} does not match {_phrase_rhs(terms_list)}."
            cell = f"{ci['sheet']}!{ci['a1']}"
            cur = cell_money(ci["cur"], ci["multiplier"], ci["unit"])
            need = cell_money(ci["need"], ci["multiplier"], ci["unit"])
            if ci["calc"]:
                cause = f"{ci['calc'][0]} For this rule {ci['a1']} must be {need} (it is {cur})."
                fix = ci["calc"][1]
            else:
                lab = f"{ci['label']} " if ci["label"] else ""
                comp_txt = f" ({ci['composition']})" if ci.get("composition") else ""
                cause = (f"{lab}{cell} is {cur}, but the other values in this rule require {need}{comp_txt}.").strip()
                fix = f"Verify and correct {cell} to {need}, assuming the other cell values are correct."
            if len(g.facts["culprit_info"]) > 1:
                alt = "; ".join(f"{c['sheet']}!{c['a1']} to {cell_money(c['need'], c['multiplier'], c['unit'])}"
                                for c in g.facts["culprit_info"][1:3])
                fix += f" Alternatively correct {alt}."
            if ci.get("uncertain"):
                fix += f" Location uncertain: {_clean(ci['uncertain'])}."
            others = [n for n in g.facts.get("rules", []) if n != rule.name]
            if others:
                card["related"] = ("May also resolve " + ", ".join(f"rule {number.get(n, '?')} ({n})" for n in others[:4])
                                   + ", which use" + ("s" if len(others) == 1 else "") + " the same cell.")
            more = [x for x in data_groups[1:] if x is not g]
            if more:
                card["other_cases"] = "Also failing for: " + "; ".join(
                    f"{x.facts['culprit_info'][0]['sheet']}!{x.facts['culprit_info'][0]['a1']} "
                    f"(needs {cell_money(x.facts['culprit_info'][0]['need'], x.facts['culprit_info'][0]['multiplier'], x.facts['culprit_info'][0]['unit'])})"
                    for x in more[:4])
        elif mine:
            triples = []
            for r in mine:
                t = _row_triple(r, lhs_term, terms_list, eq_problem, located, ev)
                if t:
                    triples.append(t)
            if triples:
                problem = triples[0][0]
                cause = " ".join(dict.fromkeys(_end(t[1]) for t in triples if t[1]))
                fix = " ".join(dict.fromkeys(_end(t[2]) for t in triples if t[2]))
        else:
            problem = "The rule's condition is not met."
            cause = "The explanation could not be refined further from the data available."
            fix = "Review the values in the table against the rule."

        card.update(problem=_clean(problem), cause=_clean(cause), fix=_clean(fix))
        card["currency_known"] = currency_known
        card["root_cause"] = roots.get(rule.name)
        pres = (ev or {}).get("presence") if isinstance(ev, dict) else None
        if _presence_named(pres) and (ev or {}).get("count_missing"):         # the blank cell is the whole answer: no other cells
            card["cells"] = _presence_cell_rows(wb, pres)
        elif _presence_named(pres):                       # the cell the missing value belongs in is one of the card's cells
            card["cells"] = _presence_cell_rows(wb, pres) + card["cells"]
        if _satisfied_cases(comp, findings) is not None:    # every failing case has its own cell
            card["cells"] = _case_cell_rows(wb, findings) or card["cells"]
        card["view"] = _compact_view(card, data_groups, located, cell_money, comp, mine, wb, ev, rc=card["root_cause"], findings=findings)
        card["view"]["kv_where"] = _kv_where(card["view"], wb, located)
        if card["bt"] and card["bt_differs"]:
            card["view"]["warnings"] = list(card["view"].get("warnings") or []) + [
                "The validator's backtracking record and our own search place a value in different cells: " + "; ".join(card["bt_differs"][:3])
                + ". The backtracking record is shown."]
        card["note"] = ("Explanation: generated by automated analysis of the error file and the workbook; "
                        f"location evidence: {ev_text}. The suggested correction should be verified against the underlying components.")
        if _presence_named(pres) and ((ev or {}).get("message_only") or (ev or {}).get("count_missing")):           # the missing value's cell is the whole answer
            card["full"], card["why_not_full"] = True, ""
        else:
            card["full"], card["why_not_full"] = rfd.decide(located, comp, culprit, conditional=cond.parse((ev or {}).get("expression")) is not None or _presence_named(pres))
        card["findings"] = [] if card["full"] else rfd.findings(located, wb, comp, ev, et.decimals_of(comp) if comp is not None else None, terms)
        cards[rule.name] = card
    return cards


# ── presentation ────────────────────────────────────────────────────────────────────────────────────────────────
def card_to_sections_detailed(card: dict) -> list[dict]:
    secs = [{"kind": "headline", "text": f"{card['number']}. {card['rule_name']}"},
            {"kind": "labeled_text", "heading": "Checks", "text": card["checks"]},
            {"kind": "labeled_text", "heading": "Problem", "text": card["problem"]},
            {"kind": "labeled_text", "heading": "Cause", "text": card["cause"]},
            {"kind": "labeled_text", "heading": "Fix", "text": card["fix"]}]
    if card.get("related"):
        secs.append({"kind": "labeled_text", "heading": "Related impact", "text": card["related"]})
    if card.get("other_cases"):
        secs.append({"kind": "labeled_text", "heading": "Other cases of this rule", "text": card["other_cases"]})
    if card["cells"]:
        secs.append({"kind": "table", "heading": "Cell details",
                     "columns": ["Item", "Sheet", "Cell", "Row label", "Current value"],
                     "rows": [[c["item"], c["sheet"], c["cell"], c["row_label"], c["current"]] for c in card["cells"]]})
    if card["calc"]:
        secs.append({"kind": "table", "heading": "Calculation details", "columns": ["Description", "Amount"],
                     "rows": [[d, a] for d, a in card["calc"]]})
    secs.append({"kind": "note", "text": card["note"]})
    return secs


def card_to_text_detailed(card: dict) -> str:
    L = [f"{card['number']}. {card['rule_name']}", f"Checks: {card['checks']}", f"Problem: {card['problem']}",
         f"Cause: {card['cause']}", f"Fix: {card['fix']}"]
    if card.get("related"):
        L.append(f"Related impact: {card['related']}")
    if card.get("other_cases"):
        L.append(card["other_cases"])
    if card["cells"]:
        L += ["", "Cell details", "Item | Sheet | Cell | Row label | Current value"]
        L += [" | ".join([c["item"], c["sheet"], c["cell"], c["row_label"], c["current"]]) for c in card["cells"]]
    if card["calc"]:
        L += ["", "Calculation details"] + [f"{d}: {a}" for d, a in card["calc"]]
    L += ["", card["note"]]
    return "\n".join(L)


# ── the compact card (the format shown in the chat) ─────────────────────────────────────────────────────────────
_KV_RENAME = {"Left side": "Reported value", "Right side": "Calculated value",
              "Recalculated from its components": "Calculated value"}
_BAD = {"Difference", "Short by"}
_NOISE_TAIL = re.compile(r"^(va|v\d+|\d+)$", re.I)
_EVIDENCE_SHORT = {"CONFIRMED": "workbook verified", "MAPPED": "from the return's mapping, workbook values not checked",
                   "INFERRED": "inferred from the workbook", "LIKELY": "likely match from the workbook, please check",
                   "none": "cells could not be located"}


def _humanize(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", s)).strip()


def _cut(text: str, n: int) -> str:
    if len(text) <= n:
        return text
    return text[:n].rsplit(" ", 1)[0].rstrip(",;:-") + "…"


def title_parts(rule_name: str) -> tuple[str, str]:
    """('Weighted Average Interest Rate', 'Term Deposit') from 'TermDeposit-WeightedAverageInterestRate-VA'."""
    parts = [p for p in re.split(r"[-_]+", rule_name or "") if p]
    while len(parts) > 2 and _NOISE_TAIL.match(parts[-1]):
        parts.pop()
    if len(parts) < 2:
        return _cut(_humanize(rule_name or "Validation rule"), 90), ""
    i = 1
    while i < len(parts) - 1 and (parts[i].isdigit() or len(parts[i]) <= 3):
        i += 1
    return _cut(" ".join(_humanize(p) for p in parts[i:]), 90), " ".join(_humanize(p) for p in parts[:i])


def _chip_label(c: dict) -> str:
    label = re.sub(r"^\s*(?:[IVX]+|\d+(?:\.\d+)*|[a-z])[.)]\s*", "", (c.get("row_label") or "").strip())
    label = re.sub(r"\s+", " ", label).strip()
    if not label:
        label = re.sub(r"\s*\(.*$", "", c.get("item", "")).strip()
    return _cut(label, 60)


def _side_cells(comp, located):
    """(left LocatedCell, right LocatedCell) when each side of an `=`/`>`/`<` rule is one variable that has a cell; else None."""
    try:
        lv, rv = comp.lhs.signed_variables(), comp.rhs.signed_variables()
    except Exception:                                              # noqa: BLE001
        return None
    if len(lv) != 1 or len(rv) != 1 or lv[0][1] != 1 or rv[0][1] != 1:
        return None
    a, b = located.get(lv[0][0].upper(), []), located.get(rv[0][0].upper(), [])
    if len(a) != 1 or len(b) != 1 or not a[0].addr or not b[0].addr:                     # sum($V2) over many cells is not one cell
        return None
    return a[0], b[0]


def _fact_money(lc) -> str:
    return money(Decimal(str(lc.fact.value))) if _num(lc.fact.value) else str(lc.fact.value)


def _special_view(card, comp, located, mine, data_groups, cell_money_fn):
    """Rule-specific wording for strict comparisons (> <) and for an equality between two single cells.
    Returns (kv, wrong, terms, why, fix) or None to keep the generic wording."""
    if comp is None or card["kind"] in et._RATIO_KINDS or card["kind"] == "count":
        return None
    pair = _side_cells(comp, located)
    op = comp.operator
    if op in (">", "<") and pair:
        word = {">": "greater than", "<": "smaller than"}[op]
        l, r = pair
        beh = next((x for x in mine if x.facts.get("kind") == "rule behaviour"), None)
        miss = next((x for x in mine if x.facts.get("kind") == "missing entries"), None)
        n = card.get("instances", 0)
        wrong = f"The rule requires the left value to be {word} the right value, but it fails in {n} case(s)."
        kv = [(f"Left value · {l.addr.a1}", _fact_money(l), ""), (f"Right value · {r.addr.a1}", _fact_money(r), ""),
              ("Condition", f"Left must be {word} Right", "bad")]
        why_parts, fix_parts = [], []
        if beh is not None:
            eq, diff, z = beh.facts.get("equal", 0), beh.facts.get("sides_differ", 0), beh.facts.get("equal_both_zero", 0)
            if eq:
                why_parts.append(f"{eq} case(s) have equal sides ({z} are 0 = 0): a strict comparison cannot hold for equal values.")
                fix_parts.append("Equal values: no data change is needed if they are correct, because the rule is a strict comparison.")
            if diff:
                why_parts.append(f"{diff} case(s) have the left value on the wrong side of the right value.")
                fix_parts.append("Left value on the wrong side: this may be a rule definition issue. Confirm with the taxonomy owner "
                                 "before changing any data.")
        if miss is not None:
            lines = miss.facts.get("cells", [])
            why_parts.append(f"{len(lines)} other case(s) have an empty entry while the cell it is compared with is filled.")
            fix_parts.append("Empty entry next to a filled cell: " + "; ".join(lines[:3]) + (f"; and {len(lines) - 3} more." if len(lines) > 3 else "."))
        if not why_parts:
            return None
        return kv, wrong, [], " ".join(why_parts), " ".join(fix_parts), {"steps": fix_parts}
    if op == "=" and pair:
        l, r = pair
        lv, rv = _fact_money(l), _fact_money(r)
        la, ra = f"{l.addr.sheet}!{l.addr.a1}", f"{r.addr.sheet}!{r.addr.a1}"
        try:
            diff = money(Decimal(str(l.fact.value)) - Decimal(str(r.fact.value)))
        except Exception:                                          # noqa: BLE001
            diff = ""
        culprit_a1 = data_groups[0].facts["culprit_info"][0]["a1"] if data_groups else None
        kv = [(la, lv, "bad" if culprit_a1 == l.addr.a1 else ""), (ra, rv, "bad" if culprit_a1 == r.addr.a1 else "")] + \
             ([("Difference", diff, "")] if diff else [])
        wrong = "These two values must be equal, but they do not match."
        why = fix = None
        extras = {"kv_code": [la, ra], "why_heading": None,
                  "kv_cells": {la: (l.addr.sheet, l.addr.a1), ra: (r.addr.sheet, r.addr.a1)}}
        if data_groups:
            ci = data_groups[0].facts["culprit_info"][0]
            bd = ci.get("breakdown")
            if bd and bd.get("status") in ("ok", "unsupported") and ci["a1"] in (l.addr.a1, r.addr.a1):
                is_left = ci["a1"] == l.addr.a1
                other, other_v, now = (ra, rv, lv) if is_left else (la, lv, rv)
                if bd.get("status") == "ok" and bd.get("consistent", True):
                    why = (f"{ci['a1']} is a calculated cell. Its current value of {now} matches the result of its formula, so the "
                           "calculation itself has not been shown to be incorrect. The underlying input values need to be investigated.")
                elif bd.get("status") == "ok":
                    why = (f"{ci['a1']} is a calculated cell. The workbook shows {bd.get('now')}, but its formula gives "
                           f"{bd.get('calc_value')} on the workbook's values, so the workbook may need recalculating.")
                else:
                    why = f"{ci['a1']} is a calculated cell, so it cannot be typed into. The rule needs it to equal {other} ({other_v})."
                fix = f"Verify the input cells {ci['a1']} is built from; the rule needs it to reach {other_v}."
                blank = any(c["state"] in ("empty", "zero") for g in bd["groups"] for c in g["items"])
                steps = ["Verify the contributing input values against the source data."]
                if blank:
                    steps.append("Check whether zero or empty values are expected.")
                steps.append(f"Confirm that {other.split('!')[-1]} is the value the rule should compare {ci['a1']} against.")
                extras["steps"] = steps
                extras["safety"] = f"Do not edit {ci['a1']} directly. Correct the underlying inputs only after confirming the cause."
                now_zero = bd.get("now") in ("0", "", None) and bd.get("status") == "ok"
                extras["why_heading"] = f"Why is {ci['a1']} {'zero' if now_zero else 'not equal to ' + other.split('!')[-1]}?"
        return kv, wrong, [], why, fix, extras
    return None


def _conditional_view(located, ev):
    """Wording for a rule of the form "if A > 0 then B div A >= T, and if A = 0 then B = 0" (a per-unit limit): the two cells, the
    figure per unit against the limit, and the value that would satisfy it. None when the rule is not of that form or holds."""
    spec = cond.parse((ev or {}).get("expression"))
    if spec is None:
        return None
    a, b = (located.get(spec["count"]) or [None])[0], (located.get(spec["amount"]) or [None])[0]
    if a is None or b is None:
        return None
    res = cond.evaluate(spec, a.fact.value, b.fact.value)
    if res is None or not res["fails"]:
        return None
    count_name, amount_name = et.words(a.fact.concept).capitalize(), et.words(b.fact.concept).capitalize()
    amount_is_money = bool(cur_.normalise(getattr(b.fact, "unit", "")))
    fmt = money if amount_is_money else (lambda d: _plain(d, 0 if d == d.to_integral() else 2))
    n, v, per = res["count"], res["amount"], res["per_unit"]
    n_text = f"{n:,.0f}" if n == n.to_integral() else _plain(n, 2)
    if per is None:
        per_text = ""
    else:
        places = 2 if per >= 1 else 4                       # 0.1511 per transaction, not 0.15
        per_text = (_CURRENCY.get() if amount_is_money else "") + _plain(per, places).rstrip("0").rstrip(".")
    word = cond.WORD[spec["op"]]
    limit = fmt(spec["threshold"])

    def label(name, lc):
        return name

    def where(name, lc):
        return f"{name.lower()} ({lc.addr.sheet}!{lc.addr.a1})" if lc.addr else name.lower()

    kv = [(label(count_name, a), n_text, "bad" if res["zero_case"] else ""), (label(amount_name, b), fmt(v), "bad" if res["zero_case"] else "")]
    if res["zero_case"]:
        wrong = f"{count_name} is 0, so the rule requires {amount_name.lower()} to be 0, but it is {fmt(v)}."
        why = (f"When {count_name.lower()} is 0 there is nothing to value, so {amount_name.lower()} has to be 0 as well; "
               f"the filing reports {fmt(v)}.")
        steps = [f"Verify {where(count_name, a)} and {where(amount_name, b)} against the source data.",
                 f"Either report the transactions that produce {fmt(v)}, or report {amount_name.lower()} as 0."]
    else:
        kv += [(f"{amount_name} ÷ {count_name.lower()}", per_text, "bad"), (f"Required ({word})", limit, "")]
        wrong = f"The rule requires {amount_name.lower()} ÷ {count_name.lower()} to be {word} {limit}, but {fmt(v)} ÷ {n_text} is {per_text}."
        why = (f"With {count_name.lower()} at {n_text}, {amount_name.lower()} would have to be {word} {fmt(res['required_amount'])}; "
               f"the filing reports {fmt(v)}, which is {per_text} per unit.")
        steps = [f"Verify {where(count_name, a)} and {where(amount_name, b)} against the source data.",
                 f"Check whether {amount_name.lower()} is reported in the unit the rule expects."]
    steps.append("Correct the figure that is wrong, then regenerate and revalidate the return.")
    cells = {kv[i][0]: (lc.addr.sheet, lc.addr.a1) for i, lc in ((0, a), (1, b)) if lc.addr}
    return kv, wrong, [], why, " ".join(steps), {"steps": steps, "kv_cells": cells}


_INEQ_WORD = {">=": "at least", ">": "more than", "<=": "at most", "<": "less than"}


def _pretty(name: str) -> str:
    """'USDToINRExchangeRateMember' -> 'USD To INR Exchange Rate'; 'Tier1Capital' -> 'Tier 1 Capital'."""
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|(?<=[A-Za-z])(?=\d)|(?<=\d)(?=[A-Za-z])", " ", name or "")
    return re.sub(r"\s+", " ", re.sub(r"\bMember$", "", s)).strip()


def _simple_view(card: dict, kv: list, wrong: str, why: str, steps: list, kv_cells: dict | None = None, footer: str = "",
                 note: str = "") -> dict:
    """The view of a card whose wording is built in one piece (no calculation breakdown): the cells as chips, the facts as rows."""
    chips = [c for c in card["cells"] if c.get("sheet") not in ("—", "") and c.get("cell") not in ("not located", "")]
    shown, groups = chips[:6], []
    for c in shown:
        if not groups or groups[-1]["sheet"] != c["sheet"]:
            groups.append({"sheet": c["sheet"], "cells": []})
        groups[-1]["cells"].append({"cell": c["cell"], "label": _chip_label(c)})
    title, area = title_parts(card["rule_name"])
    return {"title": title, "why_heading": "Why did it happen?", "kv_code": list(kv_cells or {}), "kv_cells": kv_cells or {},
            "steps": steps, "safety": "", "codes": [], "captions": {}, "subtitle": f"{area} · Formula validation" if area else "Formula validation",
            "wrong": wrong, "terms": [], "kv": kv, "why": why, "fix": " ".join(steps), "groups": groups,
            "more_cells": max(0, len(chips) - len(shown)), "footer": footer, "cells_note": note, "warnings": [], "related": [],
            "breakdown": None}


def _presence_named(pres) -> bool:
    return bool(pres and any(r.get("cell") for r in pres.get("required", [])))


def _presence_cell_rows(wb, pres) -> list[dict]:
    rows = []
    for r in pres.get("required", []):
        if r.get("cell"):
            label = (wb.text_row(r["sheet"], r["row"], 0, 1) if wb is not None and hasattr(wb, "text_row") else "") or ""
            rows.append({"item": _pretty(r["concept"]), "sheet": r["sheet"], "cell": r["cell"], "row_label": label.split(" | ")[0],
                         "current": _raw(r.get("workbook_value")) if r.get("workbook_value") is not None else "(blank)"})
    return rows


def _presence_view(card: dict, pres: dict) -> dict:
    """A rule that says a value must be reported, where the filing carries no value for it: what is required, the condition behind
    it, the cell it belongs in, and what the uploaded workbook holds there."""
    kv, kv_cells, steps = [], {}, []
    req_names = []
    for r in pres["required"]:
        name = _pretty(r["concept"])
        meaning = " ".join(_pretty(m) for m in r.get("dims", {}).values())
        name = f"{name} ({meaning})" if meaning else name
        req_names.append(name)
        if r.get("cell"):
            label = f"{name} · {r['sheet']}!{r['cell']}"
            kv.append((label, "Not reported", "bad"))
            kv_cells[label] = (r["sheet"], r["cell"])
        else:
            kv.append((name, "Not reported", "bad"))
    conds = pres.get("conditions", [])
    for c in conds:
        cname = _pretty(c["concept"])
        if c.get("cell"):
            label = f"{cname} · {c['sheet']}!{c['cell']}"
            kv.append((label, c["value"], ""))
            kv_cells[label] = (c["sheet"], c["cell"])
        else:
            kv.append((cname, c["value"], ""))
    first = next((r for r in pres["required"] if r.get("cell")), None)
    held = None if first is None or first.get("workbook_value") in (None, "") else first["workbook_value"]
    unchecked = first is not None and first.get("checked") is False            # no uploaded workbook: the place is known, not what it holds
    if first is not None and not unchecked:
        kv.append((f"Uploaded workbook holds at {first['sheet']}!{first['cell']}", str(held) if held is not None else "(blank)", ""))
    because = ""
    alt_vars = {a["var"] for a in pres.get("alternatives", [])}
    cond_now = [c for c in conds if c["var"] in alt_vars]
    if cond_now:
        c = cond_now[0]
        because = f" because {_pretty(c['concept'])} is {c['value']}"
    wrong = f"{', '.join(req_names)} must be reported{because}, but the filing has no value for it."
    if unchecked:
        why = f"This value belongs at {first['sheet']}!{first['cell']} (from the return's mapping), and the filing has no value for it."
        steps = [f"Check {first['sheet']}!{first['cell']} in your workbook and enter the value there if it applies.",
                 "Regenerate the instance and validate again."]
    elif first is not None and held is not None:
        why = (f"The uploaded workbook holds {held} at {first['sheet']}!{first['cell']}, where this value belongs, but the filing "
               "that was validated carries no value for it.")
        steps = [f"Confirm the filing was generated from this workbook: {first['sheet']}!{first['cell']} is filled, yet the filing has no value for it.",
                 "Regenerate the instance from this workbook and validate again."]
    elif first is not None:
        why = f"The cell where this value belongs, {first['sheet']}!{first['cell']}, is empty in the uploaded workbook."
        steps = [f"Enter the value in {first['sheet']}!{first['cell']}.", "Regenerate the instance and validate again."]
    else:
        why = "The filing has no value for it."
        steps = ["Report the value, then regenerate the instance and validate again."]
    for a in pres.get("alternatives", [])[:2]:
        where = f" ({a['sheet']}!{a['cell']}, now {a['value']})" if a.get("cell") else ""
        steps.append(f"If no value applies, the rule is also satisfied when {_pretty(a['concept'])} is {a['literal']}{where}.")
    how = first.get("how") if first else ""
    footer = f"Location of the missing value: from {how}." if how else ""
    if unchecked:
        footer = "Location of the missing value: from the return's mapping; no uploaded workbook to check it against."
    return _simple_view(card, kv, wrong, why, steps, kv_cells, footer=footer)


def _case_cell_rows(wb, findings, limit: int = 6) -> list[dict]:
    """One row per failing case: the cell of the first reported value of each."""
    rows = []
    for _inst, located, _ev in findings[:limit]:
        lc = next((lcs[0] for lcs in located.values() if lcs and lcs[0].fact.concept and lcs[0].addr), None)
        if lc is not None:
            a = lc.addr
            rows.append({"item": _item_name(lc.fact), "sheet": a.sheet, "cell": a.a1, "row_label": (ew._label(wb, a) or "").strip(),
                         "current": _raw(a.workbook_value)})
    return rows


def _satisfied_cases(comp, findings):
    """The cases of an inequality rule that the validator reports as failing although every one meets the condition as written."""
    if comp is None or getattr(comp, "operator", "") not in _INEQ_WORD or not findings:
        return None
    return findings if all(isinstance(f[2], dict) and f[2].get("passes") is True for f in findings) else None


def _satisfied_view(card: dict, comp, findings) -> dict:
    word = _INEQ_WORD[comp.operator]
    kv, kv_cells = [], {}
    shown_pct = False
    for inst, located, ev in findings[:4]:
        first = next(((v, lcs[0]) for v, lcs in located.items() if lcs and lcs[0].fact.concept), None)
        if first is None:
            continue
        _v, lc = first
        text = str(lc.fact.value)
        shown_pct = shown_pct or text.endswith("%")
        label = f"{lc.addr.sheet}!{lc.addr.a1}" if lc.addr else _pretty(lc.fact.concept)
        kv.append((label, text, ""))
        if lc.addr:
            kv_cells[label] = (lc.addr.sheet, lc.addr.a1)
    rhs = ew._dec(findings[0][2].get("rhs_value", findings[0][2].get("rhs")))
    limit = (format((rhs * 100).normalize(), "f") + "%" if shown_pct else et.fmt_exact(rhs)) if rhs is not None else "the limit"
    kv.append(("Condition", f"must be {word} {limit}", ""))
    n = len(findings)
    ex = kv[0][1] if kv else ""
    wrong = (f"{'All ' + str(n) + ' reported values meet' if n > 1 else 'The reported value meets'} the rule as written "
             f"(for example {ex} is {word} {limit}), yet the validator reports a failure.")
    why = ("Each reported value satisfies the condition, so this failure is not explained by the values themselves. The rule may use a "
           "different limit or scale than the filing, or the validator may have run on data other than this workbook.")
    steps = ["No correction to these values is indicated by this rule: each one already meets the condition.",
             "Check that the rule's limit and the values use the same scale.",
             "If the rule itself looks wrong, raise it with the taxonomy owner; otherwise regenerate the instance and validate again."]
    return _simple_view(card, kv, wrong, why, steps, kv_cells,
                        note=f"Cells shown are for the first {min(n, 4)} of {n} failing cases." if n > 4 else "")


def _fact_text(lc) -> str:
    """A filed value for display: amounts as money, rates/ratios as the number the filing carries."""
    v = lc.fact.value
    if lc.fact.unit.upper() == "PURE" or not _num(v):
        return str(v)
    code = cur_.normalise(lc.fact.unit)
    return _fmt_code(code)(Decimal(str(v))) if (code or lc.fact.unit.strip()) else str(v)       # no monetary unit: the number as filed


def _value_fmt(card, comp, located):
    """How a value of this rule is shown: percentages (at the rule's precision) for ratio rules on pure numbers, rupees otherwise."""
    if card["kind"] in et._RATIO_KINDS and comp is not None:
        lv = [v.upper() for v in comp.lhs.variables()]
        first = (located.get(lv[0]) or [None])[0] if lv else None
        if first is not None and first.fact.unit.upper() == "PURE":
            dp = et.decimals_of(comp)
            places = max(2, (dp if dp is not None else 4) - 2)
            return lambda d: f"{d * 100:.{places}f}%"
    return money


def _bd_matches(bd, culprit_a1: str, located) -> bool:
    """The calculated cell's template formula is built from (some of) the cells the rule compares it with, so it explains the card.
    A formula over a completely different set of cells (K13 = SUM(K3:K12) against a rule adding B13:J13) does not."""
    in_formula = {i["cell"] for g in bd.get("groups", []) for i in g["items"]}
    in_rule = {lc.addr.a1 for lcs in located.values() for lc in lcs if lc.addr}
    return bool(in_formula & (in_rule - {culprit_a1}))


def _mismatch_why(a1: str, bd, cmpd, fmt) -> str | None:
    """The culprit is a calculated cell, but the rule adds different cells than its template formula does."""
    if not cmpd:
        return None
    sides = cmpd["sides"]
    mine = 0 if any(a == a1 for _s, a in sides[0]["cells"]) else 1
    other = 1 - mine
    vals = (cmpd["left"], cmpd["right"])
    label = sides[other].get("label") or "the other side"
    text = (f"This rule expects {a1} to equal {label} ({fmt(vals[other])}), but {a1} is {fmt(vals[mine])}; the two differ by "
            f"{fmt(cmpd['diff'])}.")
    formula = (bd or {}).get("formula", "")
    state = (bd or {}).get("state")
    shown = f" ({formula})" if formula else ""
    if state in ("overwritten", "blank_formula"):                      # never call a typed cell calculated
        text += f" The template calculates {a1}{shown}, but your workbook holds a typed value there."
    elif state == "template_formula":
        text += f" The template calculates {a1}{shown} from different cells than the ones this rule adds."
    else:
        text += f" In the workbook {a1} is a calculated cell{shown}, built from different cells than the ones this rule adds."
    return text


def _pct_rows(card, comp, ev, located):
    """Reported / Calculated / Difference as percentages with the precision the rule compares at; None when it is not a percent-like rule."""
    if card["kind"] not in et._RATIO_KINDS or not ev or comp is None:
        return None
    lv = [v.upper() for v in comp.lhs.variables()]
    first = (located.get(lv[0]) or [None])[0] if lv else None
    if first is None or first.fact.unit.upper() != "PURE":
        return None
    l, r = ew._dec(ev.get("lhs_value", ev.get("lhs"))), ew._dec(ev.get("rhs_value", ev.get("rhs")))
    if l is None or r is None:
        return None
    dp = et.decimals_of(comp)
    places = max(2, (dp if dp is not None else 4) - 2)
    f = lambda d: f"{d * 100:.{places}f}%"                                               # noqa: E731
    return [("Reported value", f(l), ""), ("Calculated value", f(r), ""), ("Difference", f(l - r), "bad")]


def rounding_note(comp, located, ev, dp) -> str:
    """Why a ratio fails by a rounding amount, and what to change. Two proofs, both computed:
      1. the reported value equals the recalculated one rounded to the places it was filed at (0.06 against 0.0599 at 2 places): the
         figure is right but too coarse for a check made at `dp` places;
      2. the rule passes when computed from the unrounded values the workbook itself holds: the filing rounded those operands.
    Returns '' when neither is proven."""
    try:
        R, C = ew._dec(ev.get("lhs_value", ev.get("lhs"))), ew._dec(ev.get("rhs_value", ev.get("rhs")))
        lv = [v.upper() for v in comp.lhs.variables()]
        first = (located.get(lv[0]) or [None])[0] if lv else None
        filed = int(str(first.fact.decimal)) if first is not None else None
    except Exception:                                                                     # noqa: BLE001
        return ""
    if R is None or C is None or filed is None or dp is None or not 0 <= filed < dp or abs(R - C) > Decimal(2) / (Decimal(10) ** dp):
        return ""
    out = ""
    if C.quantize(Decimal(1).scaleb(-filed)) == R.quantize(Decimal(1).scaleb(-filed)):
        out = (f"The filing rounds {et.fmt_exact(C)} to {et.fmt_exact(R)} ({filed} decimal places), but the rule checks at {dp}. "
               f"Report at least {dp} decimal places.")
    try:
        sub, changed = {}, []
        for var, lcs in located.items():
            vals = []
            for lc in lcs:
                v = ew._dec(lc.fact.value)
                cell = lc.addr.scaled if lc.addr is not None else None
                if v is not None and cell is not None and cell != v and abs(cell - v) <= fa.tolerance(v, lc.fact.decimal):
                    changed.append((lc, v, cell))
                    v = cell
                vals.append(v)
            sub[var] = vals
        if changed:
            ev2 = ew.fx.evaluate(comp, sub)
            if ev2 and ev2.get("passes"):
                shown = "; ".join(f"{lc.addr.a1} holds {et.fmt_exact(c)} but was filed as {et.fmt_exact(v)}" for lc, v, c in changed[:3])
                out = f"{shown}; the rule checks at {dp} decimal places. Report at least {dp} decimal places."
    except Exception:                                                                     # noqa: BLE001
        pass
    return out


def _calc_why(card, comp, located, ev, cv, vals) -> str | None:
    """Plain-language 'why' from the rule's actual formula, for the calculation kinds."""
    kind = card["kind"]
    R, C = vals.get("Reported value"), vals.get("Calculated value")
    if not (R and C) or kind not in ("weighted_average", "ratio", "percentage", "aggregate"):
        return None
    dp = et.decimals_of(comp) if comp is not None else None
    shape = (cv or {}).get("shape", "")
    how = {"pairs": "the weighted average of the amounts and rates listed below",
           "ratio": "the numerator divided by the denominator listed below",
           "sum": "the sum of the components listed below"}.get(shape) or {
           "weighted_average": "the weighted average of the amounts and rates listed below",
           "percentage": "the numerator divided by the denominator, as a percentage, from the cells listed below",
           "ratio": "the numerator divided by the denominator listed below",
           "aggregate": "the sum of the components listed below"}[kind]
    text = ""                                                  # the headline already gives both figures; only the cause belongs here
    if dp is not None and kind in et._RATIO_KINDS:
        lv = [v.upper() for v in comp.lhs.variables()]
        fact = (located.get(lv[0]) or [None])[0] if lv else None
        try:
            filed = int(str(fact.fact.decimal)) if fact is not None else None
        except Exception:                                                                 # noqa: BLE001
            filed = None
        if filed is not None and 0 <= filed < dp:
            text = rounding_note(comp, located, ev, dp) or (
                f"The rule checks at {dp} decimal places but the value was filed to {filed}, so rounding can cause the difference.")
    if cv and cv.get("unlocated"):
        text = (text + " " if text else "") + (f"{cv['unlocated']} operand(s) could not be located in the workbook; "
                                               "their values come from the error file.")
    return text


def _rc_view(rc: dict, cmpd, fmt, card: dict) -> dict | None:
    """Wording for a rule whose cause has been proven (root_cause): what the cell is in the filer's workbook, what its own formula
    gives, what the rule needs, the arithmetic check, and the other rules the same cell breaks. None when nothing was proven."""
    fx = rc.get("fix")
    if not fx:
        if rc.get("ambiguous"):
            return {"warnings": [f"More than one cell could make this rule pass ({', '.join(rc['ambiguous'])}); "
                                 "the data alone does not show which one is wrong."]}
        return None
    a, mult = fx["a1"], fx["multiplier"]
    cur, rep = fmt(fx["current"] * mult), fmt(fx["replacement"] * mult)
    f = (fx["formula"] or "").replace("$", "")
    typed = fx["state"] == "overwritten"
    ev2 = rc.get("ev") or {}
    l2, r2 = ew._dec(ev2.get("lhs_value")), ew._dec(ev2.get("rhs_value"))
    verified = rc.get("verified")
    proof = (f" Verified: with {a} set to {rep}, this rule passes ({fmt(l2)} = {fmt(r2)})."
             if verified and l2 is not None and r2 is not None else "")
    warnings = []
    if not verified and rc.get("problems"):
        warnings.append("This fix could not be fully verified: " + "; ".join(rc["problems"]) + ".")
    sides = (cmpd or {}).get("sides", [])
    vals = ((cmpd or {}).get("left"), (cmpd or {}).get("right"))
    mine_i = next((i for i, s in enumerate(sides) if any(x == a for _sh, x in s["cells"])), None)
    own = mine_i is not None and sides[mine_i]["single"]
    other = sides[1 - mine_i] if mine_i is not None and len(sides) == 2 else None
    out: dict = {"cell": a, "warnings": warnings}
    held = (f"{a} contains a typed number ({cur}), but the template calculates this cell with {f}, which gives {rep} on your "
            f"workbook's values." if typed else
            f"{a} holds the formula {f}, but its stored value is {cur} while the formula gives {rep}; the workbook needs recalculating.")
    if own:
        why = held + (f" The rule compares {a} with {other['label']} ({fmt(vals[1 - mine_i])})." if other and other.get("label") else "") + proof
    else:
        cons = [c for c in rc.get("consistent", []) if sides and any(s["single"] and any(x == c["a1"] for _sh, x in s["cells"]) for s in sides)]
        mine_label = (sides[mine_i].get("ref") if mine_i is not None else "") or "the cells it adds"
        lead = next((s for s in sides if s["single"] and s is not (sides[mine_i] if mine_i is not None else None)), None)
        lead_cell = next((x for _sh, x in lead["cells"]), "") if lead else ""
        why = (f"This rule compares {lead_cell} with the sum of {mine_label}. The sum is {fmt(vals[mine_i])} because "
               + (f"{a} contains a typed number ({cur}), but the template calculates it with {f}, which gives {rep}." if typed else
                  f"{a} holds the formula {f}, but its stored value is {cur} while the formula gives {rep}.")) if lead_cell and mine_i is not None \
            else held
        for c in cons[:1]:
            tf = (c["formula"] or "").replace("$", "")
            when = f"matches what its own formula {tf} gives once {a} is corrected" if c.get("after_fix") else \
                f"is consistent with what its own formula {tf} gives"
            why += f" {c['a1']} ({fmt(c['current'] * c['multiplier'])}) {when}, so it does not look like the cause."
        why += proof
        if cons:
            out["safety"] = f"Do not change {cons[0]['a1']} to match the sum; it is consistent with its own components."
    if verified:
        if typed:
            steps = ([f"Restore the formula {f} in {a} instead of typing a number (it gives {rep}).", "Recheck this rule after restoring it."]
                     if own else
                     [f"Fix {a} first: restore the formula {f} (it gives {rep}), as described for {rc['primary']}.",
                      "Then recheck this rule: it passes once " + a + " is fixed."])
        else:
            steps = ["Recalculate the workbook and save it, then upload it again.", "Recheck this rule."]
        out.setdefault("safety", f"Do not type a number into {a}. Restore its formula so it follows its components." if typed and own else "")
    else:
        steps = [f"Check whether the value in {a} is intended; its formula {f} would give {rep}.",
                 "Confirm the cells it depends on against the source data."]
        out["safety"] = f"Do not change {a} until the evidence above is confirmed."
    out.update(why=why, steps=steps)
    rel = []
    if rc["role"] == "primary" and rc.get("others"):
        rel.append(f"Fixing {a} also clears {', '.join(rc['others'])} (each rule was evaluated again with {a} = {rep}).")
    elif rc["role"] == "secondary":
        rel.append(f"Same root cause as {rc['primary']}: {a}.")
    if rc.get("not_cleared"):
        rel.append(f"{', '.join(rc['not_cleared'])} also use {a} but would still need checking after the fix.")
    out["related"] = rel
    return out


def _precision_gap(comp, cmpd: dict, fmt) -> dict | None:
    """When an equality rule fails but both sides read the same as shown (or differ only by floating-point noise), the cause is not
    the figures: it is a value stored with more decimals than it displays. Returns the honest wording, or None for a real difference.
    Rules that compare with <, >, <= or >= are never treated this way."""
    if comp is None or getattr(comp, "operator", "") in ("<", ">", "<=", ">="):
        return None
    left, right = cmpd.get("left"), cmpd.get("right")
    if not isinstance(left, Decimal) or not isinstance(right, Decimal):
        return None
    diff = abs(left - right)
    if diff == 0:
        return None
    noise = diff <= Decimal("1e-9") * max(Decimal(1), abs(left), abs(right))
    if not noise and fmt(left) != fmt(right):
        return None
    gap = format(diff, "f")
    if "." in gap:
        gap = gap.rstrip("0").rstrip(".") or "0"
    if len(gap) > 24:
        gap = format(diff, ".3e")
    l, r = fmt(left), fmt(right)
    return {
        "left": l, "right": r, "gap": gap,
        "wrong": (f"The reported value ({l}) and the calculated value ({r}) look the same, but the rule compares exact values "
                  f"and they differ by {gap}."),
        "why": ("The figures are correct to the decimals shown. One of them is stored with more decimals than it displays (usually a "
                "calculated cell whose result was not rounded), so the exact comparison fails by a tiny gap."),
        "steps": ["Round the reported cell to the precision of the return, for example =ROUND(formula, 2), or enter the rounded figure.",
                  "Recalculate the workbook, save it and upload it again."],
    }


def _compact_view(card: dict, data_groups: list, located: dict, cell_money_fn, comp=None, mine=None, wb=None, ev=None, rc=None,
                  findings=None) -> dict:
    pres = (ev or {}).get("presence") if isinstance(ev, dict) else None
    if _presence_named(pres):
        return _presence_view(card, pres)
    if _satisfied_cases(comp, findings) is not None:
        return _satisfied_view(card, comp, findings)
    currency_known = _set_currency(located)
    kv =[(_KV_RENAME.get(d, d), a, "bad" if d in _BAD else "") for d, a in card["calc"] if d != "Compared at"]
    vals = {l: v for l, v, _ in kv}
    terms: list[str] = []
    if "Reported value" in vals and "Calculated value" in vals:
        word = "recalculated" if card["kind"] in et._RATIO_KINDS else "the components add up to"
        wrong = (f"The reported value is {vals['Reported value']}, but the recalculated value is {vals['Calculated value']}."
                 if word == "recalculated" else
                 f"The reported value is {vals['Reported value']}, but the components add up to {vals['Calculated value']}.")
        terms = [vals["Reported value"], vals["Calculated value"]]
    elif "Entries reported" in vals and "Entries required" in vals:
        wrong = f"{vals['Entries reported']} entries were reported, but at least {vals['Entries required']} are required."
        terms = [vals["Entries reported"], vals["Entries required"]]
    else:
        wrong = card["problem"]
    if card.get("verdict") == "COVER" and comp is not None and ev:
        lt, rt = ew._dec(ev.get("lhs_value", ev.get("lhs"))), ew._dec(ev.get("rhs_value", ev.get("rhs")))
        if lt is not None and rt is not None:
            fl, fr, fd = _compare_fmts(comp, located) or (money, money, money)
            ln, rn = _side_name(comp.lhs, located) or "left total", _side_name(comp.rhs, located) or "right total"
            kv = [(ln.capitalize(), fl(lt), ""), (rn.capitalize(), fr(rt), ""), ("Difference", fd(abs(lt - rt)), "bad")]
            wrong = _cmp_sentence(comp.operator, lt, rt, ln, rn, fl, fr, fd)
            terms = [fl(lt), fr(rt)]
    why, fix = card["cause"], card["fix"]
    if data_groups:
        ci = data_groups[0].facts["culprit_info"][0]
        short = ci.get("calc_short")
        if short:
            need = cell_money_fn(ci["need"], ci["multiplier"], ci["unit"])
            cur = cell_money_fn(ci["cur"], ci["multiplier"], ci["unit"])
            why = f"{short[0]} For this rule {ci['a1']} must be {need} (it is {cur})."
            fix = short[1]
    if card["kind"] in et._RATIO_KINDS and not data_groups and why.startswith("The reported value differs"):
        why = "The reported value differs from the value recalculated from its components, at the rule's precision."
    extras: dict = {}
    sp = _special_view(card, comp, located, mine or [], data_groups, cell_money_fn)
    if sp is None and card["kind"] == "conditional":
        sp = _conditional_view(located, ev)
    if sp is not None:
        kv, wrong, terms, why_sp, fix_sp, extras = sp
        why, fix = why_sp or why, fix_sp or fix
    cell_bd = data_groups[0].facts["culprit_info"][0].get("breakdown") if data_groups else None
    cv = None
    if comp is not None and card["kind"] in cvw.CALC_KINDS:
        def _label(w, a):
            return re.sub(r"\s+", " ", et._NUMBERING.sub("", ew._label(w, a))).strip()[:60] if w is not None else ""

        def _value(lc, a):
            if a is not None and a.workbook_value not in (None, ""):
                return _raw(a.workbook_value)
            return _fact_text(lc) + (" (error file)" if a is None else "")
        try:
            cv = cvw.contributing(comp, card["kind"], located, wb, _label, _value)
        except Exception:                                                                 # noqa: BLE001 - never lose the card over this
            cv = None
    # The calculated cell's own template formula explains the card only when it is built from the very cells the rule compares
    # it with (or the rule's other side is one cell). Otherwise the rule's own operands are the contributing cells.
    pair = _side_cells(comp, located) if comp is not None else None
    ci0 = data_groups[0].facts["culprit_info"][0] if data_groups else None
    pct_fmt = _value_fmt(card, comp, located)
    cmpd = None
    if comp is not None and card["kind"] in cvw.CALC_KINDS:
        try:
            cmpd = cvw.comparison(comp, located, ev, pct_fmt, fmts=_compare_fmts(comp, located) if pct_fmt is money else None)
        except Exception:                                                                 # noqa: BLE001 - never lose the card over this
            cmpd = None
    # Only when the calculated cell is the one reported cell and the rule adds OTHER cells than its formula does is the formula
    # not the explanation; a calculated cell that is itself one of the rule's components keeps its own formula explanation.
    culprit_is_reported = bool(cmpd and ci0 and any(s["single"] and (ci0["a1"] in [a for _sh, a in s["cells"]]) for s in cmpd["sides"]))
    keep_bd = bool(cell_bd) and (pair is not None or cv is None or not culprit_is_reported or _bd_matches(cell_bd, ci0["a1"], located))
    mismatch = bool(cell_bd) and not keep_bd
    if cell_bd and not mismatch:
        cv = None
    warnings: list[str] = []
    if cmpd is not None:
        if ci0 and any(r["cell"] == ci0["a1"] for r in cmpd["rows"]):                   # the cell the explanation is about is marked
            for r in cmpd["rows"]:
                r["tone"] = "bad" if r["cell"] == ci0["a1"] else ("" if r["label"] == "Difference" else r["tone"])
        kv = [(r["label"], r["value"], r["tone"]) for r in cmpd["rows"]]
        cells_map = {r["label"]: (r["sheet"], r["cell"]) for r in cmpd["rows"] if r["cell"]}
        if comp.operator in (">", "<") and len(cmpd["rows"]) >= 3 and all(s.get("label") for s in cmpd["sides"]):
            word = {">": "greater than", "<": "smaller than"}[comp.operator]
            kv = kv[:-1] + [("Condition", f"{cmpd['sides'][0]['label']} must be {word} {cmpd['sides'][1]['label']}", "bad")]
        extras = {**extras, "kv_cells": cells_map, "kv_code": list(cells_map)}
        warnings = list(cmpd["notes"])
    if cv is not None and cmpd is not None and card["kind"] in et._RATIO_KINDS and pct_fmt is not money:
        wrong = f"The reported value is {pct_fmt(cmpd['left'])}, but the recalculated value is {pct_fmt(cmpd['right'])}."
        terms = [pct_fmt(cmpd["left"]), pct_fmt(cmpd["right"])]
    if cmpd is not None and card["kind"] == "aggregate" and sp is None:
        wrong = f"The reported value is {pct_fmt(cmpd['left'])}, but the components add up to {pct_fmt(cmpd['right'])}."
        terms = [pct_fmt(cmpd["left"]), pct_fmt(cmpd["right"])]
    if cv is not None:
        if sp is None:
            vals3 = ({"Reported value": pct_fmt(cmpd["left"]), "Calculated value": pct_fmt(cmpd["right"])} if cmpd is not None else vals)
            why_calc = _calc_why(card, comp, located, ev, cv, vals3)
            if mismatch:
                why_calc = _mismatch_why(ci0["a1"], cell_bd, cmpd, pct_fmt) or why_calc
            if why_calc is not None and (not data_groups or mismatch):
                why = why_calc
            if not data_groups or mismatch:
                blank = any(i["state"] in ("empty", "zero") for g in cv["groups"] for i in g["items"])
                extras = {**extras, "steps": cvw.steps_for(card["kind"], cv.get("shape", ""), blank, bool(cv["differing"]), bool(cv["unlocated"]))}
                if mismatch:
                    extras["safety"] = (f"Do not edit {ci0['a1']} directly. It is calculated in the workbook; correct the underlying "
                                        "inputs only after confirming the cause.")
                    fix = " ".join(extras["steps"])
    related: list[str] = []
    rcv = _rc_view(rc, cmpd, pct_fmt, card) if rc else None
    if rcv:
        warnings += rcv.get("warnings", [])
        related = rcv.get("related", [])
        if rcv.get("why"):
            why = rcv["why"]
            if rcv.get("steps"):
                extras = {**extras, "steps": rcv["steps"], "safety": rcv.get("safety", "")}
                fix = " ".join(rcv["steps"])
            fix_cell = rcv.get("cell")
            for b in [x for x in (cv, cell_bd) if x and x.get("kind") == "operands"]:     # the cell proven to be the cause is marked
                for g in b["groups"]:
                    for it in g["items"]:
                        if it.get("cell") == fix_cell:
                            it["status"] = "Root cause"
    gap = _precision_gap(comp, cmpd, pct_fmt) if cmpd is not None else None
    if gap:                                                      # generic: any equality rule whose two sides look the same when shown
        wrong, why = gap["wrong"], gap["why"]
        terms = [gap["left"], gap["right"]]
        extras = {**extras, "steps": gap["steps"], "safety": "", "why_heading": "Why did it happen?"}
        fix = " ".join(gap["steps"])
        kv = [(l, (gap["gap"] if l == "Difference" else v), t) for l, v, t in kv]
        related = []
    if not currency_known and kv:
        warnings.append("The currency could not be established from the filing, so amounts are shown without a currency.")
    extra = []
    nums = re.findall(r"rule (\d+)", card.get("related") or "") if not (rcv and rcv.get("why")) else []
    if nums:
        extra.append("Fixing it may also resolve rule" + ("s " if len(nums) > 1 else " ") + ", ".join(nums) + ".")
    if len(data_groups) > 1 and not (rcv and rcv.get("why")):
        cells = ", ".join(g.facts["culprit_info"][0]["a1"] for g in data_groups[1:4])
        extra.append(f"The same check also fails at {cells}.")
    fix = " ".join([_end(fix)] + extra).strip()
    chips = [c for c in card["cells"] if c.get("sheet") not in ("—", "") and c.get("cell") not in ("not located", "")]
    shown, groups = chips[:6], []
    for c in shown:
        if not groups or groups[-1]["sheet"] != c["sheet"]:
            groups.append({"sheet": c["sheet"], "cells": []})
        groups[-1]["cells"].append({"cell": c["cell"], "label": _chip_label(c)})
    chips_hidden = False
    listed = set((extras.get("kv_cells") or {}).values())
    if listed and all((c["sheet"], c["cell"]) in listed for c in chips):          # the table above already names every one of these cells
        shown, groups, chips_hidden = [], [], True
    missing = sum(1 for lcs in located.values() for lc in lcs if not lc.addr)
    ev_short = _EVIDENCE_SHORT.get(card.get("evidence_key", ""), "")
    if card.get("bt"):
        ev_short = ("validator backtracking record, workbook verified" if card.get("evidence_key") == "CONFIRMED"
                    else "validator backtracking record, workbook values not matched or not checked")
    footer = f"Location evidence: {ev_short}." if ev_short else ""
    notes = []
    if card.get("instances", 0) > 1 and card["verdict"] in ("RULE", "COVER", "DATA"):
        notes.append(f"These cells are for {_CASE_WORD(card)}; the rule fails in {card['instances']} cases.")
    if missing and cv is None:
        notes.append(f"{missing} value(s) of this rule could not be located, so this list is incomplete.")
    if cv is not None and card.get("instances", 0) > 1:
        cv["note"] = (cv["note"] + " " if cv["note"] else "") + f"These cells are for {_CASE_WORD(card)}; the rule fails in {card['instances']} cases."
        notes = [n for n in notes if not n.startswith("These cells are for ")]
    if cv is not None and cv.get("differing"):
        footer = "Location evidence: some workbook values differ from the error file."
    steps = extras.get("steps") or [x.strip() for x in re.split(r"(?<=[.;])\s+(?=[A-Z])", fix) if x.strip()]
    captions = {}
    for l, _v, _t in kv:
        for c in chips:
            if re.search(r"(?:^|[!· ])" + re.escape(c["cell"]) + r"$", l):
                captions[l] = _chip_label(c)
                break
    title, area = title_parts(card["rule_name"])
    why = _drop_repeats(why, wrong)
    return {"title": title, "why_heading": extras.get("why_heading") or "Why did it happen?", "kv_code": extras.get("kv_code", []),
            "kv_cells": extras.get("kv_cells", {}),
            "steps": steps, "safety": extras.get("safety", ""), "codes": extras.get("codes", []),
            "captions": captions, "subtitle": f"{area} · Formula validation" if area else "Formula validation",
            "wrong": wrong, "terms": [t for t in terms if t], "kv": kv, "why": why, "fix": fix, "groups": groups,
            "more_cells": 0 if chips_hidden else max(0, len(chips) - len(shown)), "footer": footer.strip(), "cells_note": " ".join(notes),
            "warnings": warnings, "related": related,
            "breakdown": (None if mismatch else cell_bd) or cv}


def _layouts_of(located: dict) -> dict:
    """{(sheet, cell): the mapping's layout name} for every cell the card's values were located in."""
    out = {}
    for lcs in located.values():
        for lc in lcs:
            for a in ([lc.addr] if getattr(lc, "addr", None) else []) + list(getattr(getattr(lc, "res", None), "addresses", []) or []):
                if a.layout_name:
                    out.setdefault((a.sheet, a.a1), a.layout_name)
    return out


def _kv_where(view: dict, wb, located: dict | None = None) -> dict:
    """{label: {"table", "column"}} for the table's located cells. The table title is the taxonomy's own for the cell's layout when the
    return carries it; otherwise (and always for the column) what the workbook's text above the cell says."""
    out, titles, layouts = {}, getattr(wb, "table_titles", None) or {}, _layouts_of(located or {})
    for label, (sheet, cell) in (view.get("kv_cells") or {}).items():
        try:
            w = cc.describe(wb, sheet, cell)
        except Exception:                                      # noqa: BLE001  a sheet that cannot be read just has no table / column shown
            w = {"table": "", "column": ""}
        exact = titles.get(layouts.get((sheet, cell)) or _tt.layout_at(getattr(wb, "layout_ranges", None) or [], sheet, cell))
        if exact:
            w = {**w, "table": exact}
        if w["table"] or w["column"]:
            out[label] = w
    return out


def kv_columns(view: dict) -> list[str]:
    """The columns of the cell table: Sheet Name, Table and Column only when the workbook gave some, then Cell and Value."""
    if not view.get("kv_cells"):
        return []
    where = view.get("kv_where") or {}
    return (["Sheet Name"] + (["Table"] if any(w["table"] for w in where.values()) else [])
            + (["Column"] if any(w["column"] for w in where.values()) else []) + ["Cell", "Value"])


def _kv_row(view: dict, label: str, value: str) -> list[str]:
    """The cell values of one table row, in kv_columns order ('' where there is nothing to show)."""
    sheet, cell = view["kv_cells"].get(label, ("", ""))
    w = (view.get("kv_where") or {}).get(label, {})
    by_name = {"Sheet Name": sheet, "Table": w.get("table", ""), "Column": w.get("column", ""), "Cell": cell, "Value": value}
    return [by_name[c] for c in kv_columns(view)]


_SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


def _drop_repeats(why: str, wrong: str) -> str:
    """The 'why' without the sentences the headline already says (the same words with other figures or units) and without repeats of its own:
    one statement is made once."""
    letters = lambda s: re.sub(r"[^a-z]+", " ", s.lower()).strip()           # noqa: E731  figures and symbols differ between units, the words do not
    seen = {letters(s) for s in _SENTENCE.split(wrong or "")}
    kept = []
    for s in _SENTENCE.split(why or ""):
        k = letters(s)
        if k and k not in seen:
            kept.append(s)
            seen.add(k)
    return " ".join(kept)


def _breakdown_section(b: dict | None) -> dict | None:
    """The 'contributing cells' block: an evaluation status line, then (collapsed) the formula and every component with its state."""
    if not b:
        return None
    if b.get("kind") == "operands":
        return b
    items = [c for g in b.get("groups", []) for c in g["items"]]
    n = len(items) + sum(g.get("more", 0) for g in b.get("groups", []))
    blank = sum(1 for c in items if c["state"] in ("empty", "zero"))
    st = b.get("status")
    title = {"ok": "Formula evaluated successfully", "unsupported": "The formula could not be evaluated here",
             "no_formula": "No formula available in the template", "unreadable": "The template's formulas could not be read"}.get(st, "")
    if st == "ok" and b.get("state") == "template_formula":
        title = "Template formula evaluated successfully"            # the filer's own formulas could not be inspected
    elif st == "ok" and b.get("state") in ("overwritten", "blank_formula"):
        title = "Template formula (your workbook holds a typed value here)"
    if not items:
        sub = ""
    elif st == "unsupported" and b.get("note"):
        sub = f"{n} contributing cells identified · values could not be verified"
    elif blank == len(items):
        sub = f"{n} contributing cells identified · Current component values are zero"
    elif blank:
        sub = f"{n} contributing cells identified · {blank} of them are empty or zero"
    else:
        sub = f"{n} contributing cells identified"
    return {"heading": "Contributing cells", "status_title": title, "status_sub": sub,
            "toggle": f"View all {n} contributing cells", "toggle_sub": "Cell references, labels, values and formula",
            "formula": b.get("formula", ""), "summary": b.get("summary", ""), "groups": b.get("groups", []), "note": b.get("note", "")}


def card_to_sections(card: dict) -> list[dict]:
    """The compact card as one section (kind `issue_card`) that the chat renders."""
    v = card["view"]
    return [{"kind": "issue_card", "title": v["title"], "subtitle": v["subtitle"], "badge": "Failed",
             "wrong": {"heading": "What went wrong?", "text": v["wrong"], "terms": v["terms"], "codes": v.get("codes", [])},
             "kv": [{"label": l, "value": val, "tone": tone, "caption": v.get("captions", {}).get(l, ""), "code": l in v.get("kv_code", []),
                     "sheet": v.get("kv_cells", {}).get(l, ("", ""))[0], "cell": v.get("kv_cells", {}).get(l, ("", ""))[1],
                     "table": v.get("kv_where", {}).get(l, {}).get("table", ""), "column": v.get("kv_where", {}).get(l, {}).get("column", "")}
                    for l, val, tone in v["kv"]],
             "kv_columns": kv_columns(v),
             "why": {"heading": v.get("why_heading", "Why did it happen?"), "text": v["why"]},
             "fix": {"heading": "What should you check?", "text": v["fix"], "steps": v.get("steps", []), "note": v.get("safety", "")},
             "cells": {"heading": "Relevant cells", "groups": v["groups"], "more": v["more_cells"], "note": v.get("cells_note", "")},
             "warnings": v.get("warnings", []), "related": v.get("related", []),
             "breakdown": _breakdown_section(v.get("breakdown")),
             "footer": v["footer"]}]


def card_to_text(card: dict) -> str:
    v = card["view"]
    L = [f"{v['title']}  [Failed]", v["subtitle"], "", "What went wrong?", v["wrong"]]
    if v["kv"] and v.get("kv_cells"):
        L += ["", " | ".join(kv_columns(v))] + [
            (" | ".join(_kv_row(v, l, val)) if l in v["kv_cells"] else f"{l} | | {val}") for l, val, _ in v["kv"]]
    elif v["kv"]:
        L += [""] + [f"{l}: {val}" + (f" ({v['captions'][l]})" if v.get("captions", {}).get(l) else "") for l, val, _ in v["kv"]]
    L += [f"  Warning: {w}" for w in v.get("warnings", [])]
    L += [f"  Related: {r}" for r in v.get("related", [])]
    L += (["", v.get("why_heading", "Why did it happen?"), v["why"]] if v["why"] else []) + ["", "What should you check?"]
    L += [f"  {i}. {t}" for i, t in enumerate(v.get("steps") or [v["fix"]], 1)]
    if v.get("safety"):
        L.append(f"  {v['safety']}")
    if v["groups"] and not v.get("breakdown"):
        L += ["", "Relevant cells"]
        for g in v["groups"]:
            L.append(g["sheet"])
            L += [f"  {c['cell']} · {c['label']}" if c["label"] else f"  {c['cell']}" for c in g["cells"]]
        if v["more_cells"]:
            L.append(f"  … and {v['more_cells']} more")
        if v.get("cells_note"):
            L.append(f"  {v['cells_note']}")
    b = v.get("breakdown")
    if b:
        bs = _breakdown_section(b)
        L += ["", "Contributing cells"] + ([b["summary"]] if b.get("summary") else []) + \
             ([b["formula"]] if b.get("formula") else [])
        for g in b["groups"]:
            if g["label"]:
                L.append(f"  {g['label']}")
            for c in g["items"]:
                L.append(f"    {c['cell']}  {c['label']}  {c['value']}  {c.get('status', '')}".rstrip())
            if g.get("more_text"):
                L.append("    " + g["more_text"])
        if b.get("note"):
            L.append(b["note"])
    if v["footer"]:
        L += ["", v["footer"]]
    return "\n".join(L)
