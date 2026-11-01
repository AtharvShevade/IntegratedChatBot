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
from . import currency as cur_
from . import root_cause as rcs
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
        return True                                          # ratios and counts: no amount is shown
    _CURRENCY.set("")
    return False


def money(inr: Decimal) -> str:
    """An amount in the rule's currency: ₹28,062,200,000 / QAR 70,000,000 (no decimals when whole)."""
    d = Decimal(inr)
    return _CURRENCY.get() + (f"{d:,.0f}" if d == d.to_integral() else f"{d:,.2f}")


def cell_money(value: Decimal, multiplier: int, unit: str) -> str:
    """A value in the sheet's own unit: ₹196,448.89 lakh. Non-monetary values (ratios, counts) stay plain."""
    d = Decimal(value)
    code = cur_.normalise(unit)
    pf = cur_.prefix(code) if code else (_CURRENCY.get() if not (unit or "").strip() else None)
    if pf is not None and multiplier in _UNIT_WORD:
        return f"{pf}{d:,.2f} {_UNIT_WORD[multiplier]}"
    if code:
        return f"{pf}{d:,.2f}"
    return et.fmt_exact(d)


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
        problem = "The left total is smaller than the right total."
        cause = f"Left total {r.facts.get('left_total')} is below right total {r.facts.get('right_total')} (short by {r.facts.get('shortfall')})."
        fix = "Correct the left cells (or the right ones if they are overstated); the rule alone does not say which category is short."
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
def build_cards(analysed, wb, rows, numbering: dict | None = None) -> dict[str, dict]:
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
                "cells": [], "calc": _calc_rows(verdict, kind, comp, ev, None),
                "instances": len(findings), "related": None, "other_cases": None}
        ev_key, ev_text = _evidence(located)
        card["evidence_key"], card["evidence"] = ev_key, ev_text
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
        card["view"] = _compact_view(card, data_groups, located, cell_money, comp, mine, wb, ev, rc=card["root_cause"])
        card["note"] = ("Explanation: generated by automated analysis of the error file and the workbook; "
                        f"location evidence: {ev_text}. The suggested correction should be verified against the underlying components.")
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


def _fact_text(lc) -> str:
    """A filed value for display: amounts as money, rates/ratios as the number the filing carries."""
    v = lc.fact.value
    if lc.fact.unit.upper() == "PURE" or not _num(v):
        return str(v)
    return money(Decimal(str(v)))


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
        out += (f" The reported {et.fmt_exact(R)} is the recalculated {et.fmt_exact(C)} rounded to {filed} decimal places: the figure is right "
                f"but too coarse for a check made at {dp}. Report it with at least {dp} decimal places ({et.fmt_exact(C.quantize(Decimal(1).scaleb(-dp)))}).")
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
                out += (f" Computed from the unrounded values in your workbook the rule passes, so the filing rounded {len(changed)} "
                        f"operand(s) ({shown}). Report those with more decimal places.")
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
    text = f"The reported value is {R}; {how} gives {C}."
    if dp is not None and kind in et._RATIO_KINDS:
        text += f" The rule compares both at {dp} decimal places."
        lv = [v.upper() for v in comp.lhs.variables()]
        fact = (located.get(lv[0]) or [None])[0] if lv else None
        try:
            filed = int(str(fact.fact.decimal)) if fact is not None else None
        except Exception:                                                                 # noqa: BLE001
            filed = None
        if filed is not None and 0 <= filed < dp:
            text += (f" The reported value is filed to {filed} decimal places, so rounding in the filed values can contribute "
                     "to the difference.")
            text += rounding_note(comp, located, ev, dp)
    if cv and cv.get("unlocated"):
        text += (f" {cv['unlocated']} operand(s) could not be located in the workbook; the calculation uses their values "
                 "from the error file.")
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


def _compact_view(card: dict, data_groups: list, located: dict, cell_money_fn, comp=None, mine=None, wb=None, ev=None, rc=None) -> dict:
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
            word = "at least" if comp.operator == ">=" else "at most"
            kv = [("Left total", money(lt), ""), ("Right total", money(rt), ""), ("Difference", money(abs(lt - rt)), "bad")]
            wrong = f"The left total {money(lt)} must be {word} the right total {money(rt)}, but it is off by {money(abs(lt - rt))}."
            terms = [money(lt), money(rt)]
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
            cmpd = cvw.comparison(comp, located, ev, pct_fmt)
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
        if comp.operator in (">", "<") and len(cmpd["rows"]) >= 3:
            word = {">": "greater than", "<": "smaller than"}[comp.operator]
            a, b = cmpd["rows"][0], cmpd["rows"][1]
            kv = kv[:-1] + [("Condition", f"{a['cell']} must be {word} {b['cell']}", "bad")]
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
            if why_calc and (not data_groups or mismatch):
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
    missing = sum(1 for lcs in located.values() for lc in lcs if not lc.addr)
    ev_short = _EVIDENCE_SHORT.get(card.get("evidence_key", ""), "")
    footer = f"Location evidence: {ev_short}." if ev_short else ""
    notes = []
    if card.get("instances", 0) > 1 and card["verdict"] in ("RULE", "COVER", "DATA"):
        notes.append(f"These cells are for the first failing case; the rule fails in {card['instances']} cases.")
    if missing and cv is None:
        notes.append(f"{missing} value(s) of this rule could not be located, so this list is incomplete.")
    if cv is not None and card.get("instances", 0) > 1:
        cv["note"] = (cv["note"] + " " if cv["note"] else "") + f"These cells are for the first failing case; the rule fails in {card['instances']} cases."
        notes = [n for n in notes if not n.startswith("These cells are for the first")]
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
    return {"title": title, "why_heading": extras.get("why_heading") or "Why did it happen?", "kv_code": extras.get("kv_code", []),
            "kv_cells": extras.get("kv_cells", {}),
            "steps": steps, "safety": extras.get("safety", ""), "codes": extras.get("codes", []),
            "captions": captions, "subtitle": f"{area} · Formula validation" if area else "Formula validation",
            "wrong": wrong, "terms": [t for t in terms if t], "kv": kv, "why": why, "fix": fix, "groups": groups,
            "more_cells": max(0, len(chips) - len(shown)), "footer": ("" if (card.get("evidence_key") == "CONFIRMED" and not (cv and cv.get("differing"))) else footer.strip()), "cells_note": " ".join(notes),
            "warnings": warnings, "related": related,
            "breakdown": (None if mismatch else cell_bd) or cv}


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
                     "sheet": v.get("kv_cells", {}).get(l, ("", ""))[0], "cell": v.get("kv_cells", {}).get(l, ("", ""))[1]}
                    for l, val, tone in v["kv"]],
             "kv_columns": ["Sheet Name", "Cell", "Value"] if v.get("kv_cells") else [],
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
        L += ["", "Sheet Name | Cell | Value"] + [
            (f"{v['kv_cells'][l][0]} | {v['kv_cells'][l][1]} | {val}" if l in v["kv_cells"] else f"{l} | | {val}") for l, val, _ in v["kv"]]
    elif v["kv"]:
        L += [""] + [f"{l}: {val}" + (f" ({v['captions'][l]})" if v.get("captions", {}).get(l) else "") for l, val, _ in v["kv"]]
    L += [f"  Warning: {w}" for w in v.get("warnings", [])]
    L += [f"  Related: {r}" for r in v.get("related", [])]
    L += ["", v.get("why_heading", "Why did it happen?"), v["why"], "", "What should you check?"]
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
