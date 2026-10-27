"""Explain an error file the way a person with the workbook open would: which rule failed, on which cells,
with which numbers, and whether the data or the rule is at fault.

    python explain_workbook.py <metadata folder> <workbook .xls/.xlsx> <error .html> [--out report.md]

Everything numeric is computed here (formula_expression.evaluate for the rule, Decimal arithmetic for
differences); nothing is guessed and no LLM is involved. Facts are located with fact_address (metadata +
workbook value confirmation); a fact that cannot be confirmed is reported WITHOUT an address.

Verdict per failing rule (code decides, from the rule's shape and the numbers):
  DATA    an identity / sum rule whose two sides differ        -> real data error, cells + amount to fix
  RULE    a strict comparison (> or <) that fails on equal values (0 = 0) or on values that are normal
          (e.g. outstanding < exposure)                         -> the rule behaviour, not the filer's data
  COVER   sum(A) >= sum(B) style rules                          -> shortfall and the cells on each side
"""
from __future__ import annotations

import argparse
import collections
import importlib.util
import os
import sys
from decimal import Decimal

HERE = os.path.dirname(os.path.abspath(__file__))

from . import cell_locator as cl          # noqa: E402
from . import error_html as eh            # noqa: E402
from . import absent_operands as ao        # noqa: E402
from . import entry_rows as er            # noqa: E402
from . import rule_operands as ro         # noqa: E402
from . import value_locator as vl         # noqa: E402
from . import fact_address as fa          # noqa: E402
from .workbook import Workbook      # noqa: E402


from backend.tools import formula_expression as fx, formula_kind as fk   # the chatbot's own modules


def _unescape(s: str) -> str:
    return s.replace("&gt;", ">").replace("&lt;", "<").replace("&amp;", "&")


def _money(d: Decimal) -> str:
    return f"{d:,.2f}"


class Located:
    """One fact with the cell it came from (None when it could not be confirmed)."""

    def __init__(self, fact: eh.Fact, res: fa.Resolved):
        self.fact = fact
        self.res = res
        self.dynamic = False
        self.inferred = False
        self.reason = ""
        self.uncertain = ""
        self.addr = res.addresses[0] if res.status in ("CONFIRMED", "MAPPED", "INFERRED", "LIKELY") and res.addresses else None
        if res.status == "LIKELY":
            self.uncertain = "chosen from the workbook alone (value and labels), with moderate confidence"

    @property
    def where(self) -> str:
        return f"{self.addr.sheet}!{self.addr.a1}" if self.addr else "(cell not confirmed)"

    @property
    def cell_value(self):
        return self.addr.workbook_value if self.addr else None


def _label(wb: Workbook, a: fa.Address) -> str:
    return wb.text_row(a.sheet, a.row, 1, 2)[:60]


def _prefer_sibling_layout(located) -> None:
    """A fact that several cells could hold (duplicate contexts, equal values) takes the cell in the layout
    the instance's unambiguous facts sit in; otherwise the first candidate stays and the rest are noted."""
    votes = collections.Counter(lc.res.addresses[0].layout_id for v in located.values() for lc in v
                                if lc.res.status in ("CONFIRMED", "MAPPED") and len({(a.sheet, a.a1) for a in lc.res.addresses}) == 1)
    for v in located.values():
        for lc in v:
            if lc.res.status in ("CONFIRMED", "MAPPED") and len(lc.res.addresses) > 1 and votes:
                lc.res.addresses.sort(key=lambda a: -votes.get(a.layout_id, 0))
                lc.addr = lc.res.addresses[0]


def _value_known(wb, value) -> bool:
    """Is this reported value anywhere in the workbook (any sheet, any template multiplier)?"""
    t = fa._dec(value)
    keys = wb._cache.get("all_keys")
    if keys is None:
        keys = set()
        for sh in wb.sheets:
            keys |= set(wb.index(sh))
        wb._cache["all_keys"] = keys
    if t is None:
        return str(value).strip().lower() in keys
    return any(round(float(t / m), 4) in keys for m in (1, 1000, 100000, 10000000))


def why_unlocated(lc, wb, has_def=None, rep=None) -> str:
    """Plain reason a fact has no cell: which side of the pipeline ran out (file, metadata, workbook, ambiguity)."""
    if lc.addr:
        return ""
    f = lc.fact
    t = fa._dec(f.value)
    zero = t is not None and t == 0
    if not f.concept:
        base = ("operand not reported in the filing (no such fact in the instance; the rule counts it as 0)"
                if rep is not None else "operand not reported (empty in the filing)")
        if has_def is False:
            return base + "; the rule's definition is not in the taxonomy folder, so its item cannot be named"
        if has_def:
            return base + "; the rule's definition was found but no single cell fits it"
        return base + "; the error file names no item and its row could not be inferred"
    if zero:
        return "value is 0: many identical empty cells, so the entry cannot be told apart"
    if lc.res.status == "UNRESOLVED":
        return "no mapping row for this item and period in the return's metadata"
    if lc.dynamic:
        return "several facts land on one template cell: the sheet adds rows per entry"
    if wb is not None and not getattr(wb, "is_template", False) and not _value_known(wb, f.value):
        return "reported value is not in the uploaded workbook (edited after the upload, or a different upload)"
    return "value is in the workbook but could not be tied to one cell"


def _title_of(inst) -> str:
    import re
    t = _unescape(inst.title).replace("▼", "")
    t = re.sub(r'^\s*"?en:"?\s*Identity\s*"*', "", t.strip(), flags=re.I)
    return re.sub(r'"?\s*do not tally\.?"?\s*$', "", t, flags=re.I).strip(' "')


def _name_tokens(text: str) -> set[str]:
    import re
    words = re.findall(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+", text or "")
    return {w.lower() for w in words if len(w) >= 4}


def _prefer_rule_context(located, comp, title: str, rule_name: str, wb, layouts: dict) -> None:
    """One item and value can sit in several sheets; the one the rule is about is the better answer. A candidate scores
    for each word of the rule's name found in its sheet or layout name, and double when its row label agrees with the
    rule title's segment for that operand. The first candidate is replaced only by a strictly better one."""
    if comp is None:
        return
    order = [v.upper() for v, _ in comp.lhs.signed_variables()] +             [v.upper() for v, _ in (comp.rhs.signed_variables() if comp.rhs is not None else [])]
    terms = ao.split_terms(title)
    seg = dict(zip(order, terms)) if order and len(terms) == len(order) else {}
    toks = _name_tokens(rule_name)

    def norm(x):
        import re
        return re.sub(r"[^a-z0-9]", "", str(x).lower())

    for var, lcs in located.items():
        for lc in lcs:
            if lc.res.status not in ("CONFIRMED", "MAPPED") or not lc.addr:
                continue
            cands = list({(a.sheet, a.row, a.col): a for a in lc.res.addresses}.values())
            if len(cands) < 2:
                continue

            def score(a):
                names = norm(a.sheet) + " " + norm(layouts.get(a.layout_id, ""))
                s1 = sum(1 for t in toks if t in names)
                s2 = 1 if seg.get(var.upper()) and ao._agree(ao._row_label(wb, a.sheet, a.row), seg[var.upper()]) else 0
                return s1 + 2 * s2

            scores = {id(a): score(a) for a in cands}
            best = max(cands, key=lambda a: scores[id(a)])
            top = [a for a in cands if scores[id(a)] == scores[id(best)]]
            cur = next(a for a in cands if (a.sheet, a.row, a.col) == (lc.addr.sheet, lc.addr.row, lc.addr.col))
            if len(top) == 1 and scores[id(best)] > scores[id(cur)]:
                lc.addr = best
                lc.res.addresses = [best] + [a for a in lc.res.addresses if a is not best]


def _flag_uncertain(located, comp, title: str, wb, rule_name: str = "", layouts: dict | None = None) -> None:
    """A cell whose row label disagrees with the wording the rule gives that operand may be a value that merely matches:
    mark it uncertain so the report does not state it as fact."""
    if comp is None:
        return
    order = [v.upper() for v, _ in comp.lhs.signed_variables()] +             [v.upper() for v, _ in (comp.rhs.signed_variables() if comp.rhs is not None else [])]
    terms = ao.split_terms(title)
    if not order or len(terms) != len(order):
        return
    for var, seg in zip(order, terms):
        for lc in located.get(var, []):
            if lc.addr and not lc.inferred and not ao._agree(ao._row_label(wb, lc.addr.sheet, lc.addr.row), seg):
                import re
                names = re.sub(r"[^a-z0-9]", "", (lc.addr.sheet + (layouts or {}).get(lc.addr.layout_id, "")).lower())
                if any(t in names for t in _name_tokens(rule_name)):
                    continue            # the sheet is the one the rule is named after: a different wording is not a doubt
                lc.uncertain = (f"row is '{ao._row_label(wb, lc.addr.sheet, lc.addr.row).strip()[:40]}' but the rule says '{seg[:40]}'; "
                               "the value matches that cell but its label does not match the rule, so check the right sheet")


def _drop_colliding(located) -> None:
    """Different facts (other concept/context) that land on ONE cell mean the layout has dynamic rows: the mapping
    names a template row, not the filer's row. Naming that cell would be wrong, so none of them gets an address."""
    seen: dict[tuple, set] = {}
    for v in located.values():
        for lc in v:
            if lc.addr:
                seen.setdefault((lc.addr.sheet, lc.addr.a1), set()).add((lc.fact.concept, lc.fact.context))
    for v in located.values():
        for lc in v:
            if lc.addr and len(seen[(lc.addr.sheet, lc.addr.a1)]) > 1:
                lc.addr = None
                lc.dynamic = True


def _segment_words(comp, title: str) -> dict:
    """Words of the rule title's segment for each operand (when the title lines up with the formula's operands)."""
    if comp is None:
        return {}
    order = [v.upper() for v, _ in comp.lhs.signed_variables()] +             [v.upper() for v, _ in (comp.rhs.signed_variables() if comp.rhs is not None else [])]
    terms = ao.split_terms(title)
    return {v: vl.words(t) for v, t in zip(order, terms)} if order and len(terms) == len(order) else {}


def analyse(meta, wb, rules):
    out = []
    locator = None
    if wb is not None and getattr(wb, "sheets", None) and not getattr(wb, "is_template", False):
        locator = vl.ValueLocator(wb)                       # evidence from the workbook alone, for items the mapping cannot place
        locator.learn_scaling(list(dict.fromkeys(f.value for r in rules for i in r.instances for f in i.facts if f.concept)))
    if not getattr(wb, "is_template", False):
        fa.calibrate(meta, wb, [(f.concept, f.context, f.value) for r in rules for i in r.instances for f in i.facts])
    for rule in rules:
        expr = _unescape(rule.expression)
        comp = fx.parse_formula(expr)
        kind = fk.classify(comp) if comp else "unknown"
        findings = []
        for inst in rule.instances:
            by_var: dict[str, list] = collections.defaultdict(list)
            seg_words = _segment_words(comp, _title_of(inst))
            located: dict[str, list[Located]] = collections.defaultdict(list)
            for f in inst.facts:
                by_var[f.var.upper()].append(f.value)
                res = fa.resolve_fact(meta, wb, f.concept, f.context, f.value)
                if locator is not None and f.concept and res.status in ("UNRESOLVED", "UNCONFIRMED"):
                    alt = locator.resolve(f, seg_words.get(f.var.upper(), set()), rule.name)
                    if alt is not None and (alt.status in ("INFERRED", "LIKELY") or res.status == "UNRESOLVED"):
                        res = alt
                located[f.var.upper()].append(Located(f, res))
            _prefer_sibling_layout(located)
            _prefer_rule_context(located, comp, _title_of(inst), rule.name, wb, meta.layouts)
            _flag_uncertain(located, comp, _title_of(inst), wb, rule.name, meta.layouts)
            _drop_colliding(located)
            ao.resolve(located, comp, _title_of(inst), wb, getattr(wb, "formulas", None))
            ro.place(located, rule.name, meta, wb)
            ev = fx.evaluate(comp, dict(by_var)) if comp else None
            findings.append((inst, located, ev))
        out.append((rule, expr, comp, kind, findings))
    er.refine(out, wb)
    defs, rep = getattr(meta, "formula_defs", None), getattr(meta, "reported", None)
    for _r, _e, _c, _k, fnd in out:
        has_def = (_r.name in defs) if defs else None
        for _i, lo, _ev in fnd:
            for lcs in lo.values():
                for lc in lcs:
                    if not lc.addr:
                        lc.reason = why_unlocated(lc, wb, has_def, rep)
    return out


def _dec(v):
    try:
        return Decimal(str(v))
    except Exception:
        return None


def verdict(comp, ev) -> str:
    if comp is None or ev is None:
        return "UNKNOWN"
    op = comp.operator
    lhs, rhs = _dec(ev.get("lhs_value", ev.get("lhs"))), _dec(ev.get("rhs_value", ev.get("rhs")))
    if op in (">", "<"):
        return "RULE"
    if op in (">=", "<="):
        return "COVER"
    if op == "=":
        return "DATA"
    return "UNKNOWN"


def required_values(comp, located):
    """Solve  sum(coef*value) = 0  for each variable in turn. Returns {var: (current INR, required INR)}.
    Only for plain '=' rules whose sides are sums of variables (rounding wrappers are looked through)."""
    try:
        lv, rv = comp.lhs.signed_variables(), comp.rhs.signed_variables()
    except Exception:
        return {}
    coef: dict[str, int] = {}
    for var, sg in lv:
        coef[var.upper()] = coef.get(var.upper(), 0) + sg
    for var, sg in rv:
        coef[var.upper()] = coef.get(var.upper(), 0) - sg
    used = {v.upper() for v in comp.variables()}
    if used != set(coef):            # a ratio / product hides some variables: not a linear identity, no fix to solve
        return {}
    val = {}
    for var in coef:
        facts = located.get(var, [])
        d = [_dec(lc.fact.value) for lc in facts]
        if len(facts) != 1 or d[0] is None:
            return {}
        val[var] = d[0]
    out = {}
    for var, c in coef.items():
        if c == 0:
            continue
        rest = sum((coef[o] * val[o] for o in coef if o != var), Decimal(0))
        out[var] = (val[var], -rest / c)
    return out


def _units(lc, inr: Decimal) -> Decimal:
    m = lc.addr.multiplier if lc.addr and lc.addr.multiplier else 1
    return inr / m


def render(meta, wb, analysed, html_counts, spec=()) -> str:
    L: list[str] = []
    total_inst = sum(len(r.instances) for r, *_ in analysed)
    L.append("# Error explanation (workbook-based, computed by code)\n")
    L.append(f"{len(analysed)} formula rules fail, {total_inst} failing instances.\n")

    data_rules, rule_rules, cover_rules = [], [], []
    for item in analysed:
        rule, expr, comp, kind, findings = item
        v = verdict(comp, findings[0][2] if findings else None)
        {"DATA": data_rules, "RULE": rule_rules, "COVER": cover_rules}.get(v, data_rules).append(item)

    # ---- A. real data errors ------------------------------------------------------------------------
    L.append("## A. Real data errors (the two sides of an identity differ)\n")
    n = 0
    for rule, expr, comp, kind, findings in data_rules:
        for inst, located, ev in findings:
            lhs = _dec(ev.get("lhs_value", ev.get("lhs"))) if ev else None
            rhs = _dec(ev.get("rhs_value", ev.get("rhs"))) if ev else None
            n += 1
            L.append(f"### A{n}. {rule.name}")
            L.append(f"Rule: `{expr}`")
            if ev:
                diff = (lhs - rhs) if lhs is not None and rhs is not None else None
                L.append(f"Left side = {_money(lhs)} | right side = {_money(rhs)}"
                         + (f" | difference = {_money(diff)} (INR)" if diff is not None else ""))
            L.append("")
            L.append("| Var | Concept | Context | Cell | Cell value | Label |")
            L.append("|---|---|---|---|---|---|")
            for var in sorted(located, key=lambda x: int(x[1:]) if x[1:].isdigit() else 0):
                for lc in located[var]:
                    a = lc.addr
                    L.append(f"| {var} | {lc.fact.concept} | {lc.fact.context[:60]} | {lc.where} | "
                             f"{'' if a is None else ('(blank)' if a.workbook_value in (None, '') else a.workbook_value)} | "
                             f"{_label(wb, a) if a else ''} |")
            req = required_values(comp, located)
            fixes = []
            for var, (cur, need) in sorted(req.items()):
                lc = located[var][0]
                if lc.addr is None or abs(cur - need) < Decimal("0.5"):
                    continue
                single = len(comp.lhs.signed_variables()) == 1 and var in {v.upper() for v, _ in comp.lhs.signed_variables()}
                blank = lc.addr.workbook_value in (None, "")
                if single or (blank and need >= 0):
                    fixes.append(f"- To balance this rule alone, **{lc.where}** would have to be "
                                 f"**{_money(_units(lc, need))}** (it is {_money(_units(lc, cur))} now; amounts in the sheet's own unit).")
            if fixes:
                L.append("\nHow to balance it (one cell at a time - the other cells are assumed right):")
                L.extend(fixes)
            blanks = [lc for v in located.values() for lc in v if lc.addr and lc.addr.workbook_value in (None, "")
                      and _dec(lc.fact.value) not in (None, Decimal(0))]
            for lc in blanks:
                L.append(f"\n- {lc.where} is blank in the workbook but the instance carries {lc.fact.value}.")
            L.append("")
    if n == 0:
        L.append("None.\n")

    # ---- B. rule behaviour ---------------------------------------------------------------------------
    L.append("## B. Failures caused by how the rule is written (not necessarily wrong data)\n")
    for rule, expr, comp, kind, findings in rule_rules:
        eq = lt = gt = 0
        examples = []
        for inst, located, ev in findings:
            if not ev:
                continue
            lhs = _dec(ev.get("lhs_value", ev.get("lhs")))
            rhs = _dec(ev.get("rhs_value", ev.get("rhs")))
            if lhs is None or rhs is None:
                continue
            if lhs == rhs:
                eq += 1
            elif lhs < rhs:
                lt += 1
            else:
                gt += 1
            if len(examples) < 3:
                examples.append((located, lhs, rhs))
        L.append(f"### {rule.name}")
        L.append(f"Rule: `{expr}`  ({len(findings)} failing instances)")
        L.append(f"- left side equals right side: {eq}  (strict `{comp.operator}` cannot hold when both are equal, e.g. 0 and 0)")
        L.append(f"- left side smaller than right side: {lt}")
        L.append(f"- left side larger than right side: {gt}")
        neq = [(lo, l, r) for _i, lo, ev2 in findings if ev2
               for l, r in [(_dec(ev2.get("lhs_value", ev2.get("lhs"))), _dec(ev2.get("rhs_value", ev2.get("rhs"))))]
               if l is not None and r is not None and l != r]
        if neq:
            L.append(f"- instances where the two sides really differ ({len(neq)}); first {min(len(neq), 8)}:")
            for located, lhs, rhs in neq[:8]:
                parts = [f"{var}={lc.fact.value} at {lc.where}" for var in sorted(located) for lc in located[var]]
                L.append(f"  - {'; '.join(parts)}")
        examples = examples[:1]
        for located, lhs, rhs in examples:
            parts = []
            for var in sorted(located):
                for lc in located[var]:
                    parts.append(f"{var}={lc.fact.value} at {lc.where}")
            L.append(f"  - e.g. {'; '.join(parts)}  (left {_money(lhs)}, right {_money(rhs)})")
        L.append("")
    if not rule_rules:
        L.append("None.\n")

    # ---- coverage rules -------------------------------------------------------------------------------
    L.append("## C. Coverage rules (sum of one group must be at least the sum of another)\n")
    for rule, expr, comp, kind, findings in cover_rules:
        for inst, located, ev in findings:
            lhs = _dec(ev.get("lhs_value", ev.get("lhs"))) if ev else None
            rhs = _dec(ev.get("rhs_value", ev.get("rhs"))) if ev else None
            L.append(f"### {rule.name}")
            L.append(f"Rule: `{expr}`")
            if lhs is not None and rhs is not None:
                L.append(f"Left sum = {_money(lhs)} | right sum = {_money(rhs)} | shortfall = {_money(rhs - lhs)} (INR)")
            for var in sorted(located):
                sub = Decimal(0)
                for lc in located[var]:
                    d = _dec(lc.fact.value) or Decimal(0)
                    sub += d
                    L.append(f"- {var}: {lc.fact.concept} [{lc.fact.context[:70]}] = {_money(d)} at {lc.where}")
            L.append("")
    if not cover_rules:
        L.append("None.\n")

    # ---- other tabs ------------------------------------------------------------------------------------
    L.append("## D. Other tabs of the error file (no Excel cells involved)\n")
    for k, v in html_counts.items():
        L.append(f"- {k}: {v}")
    if spec:
        L.append(f"- Specification (TABLE) warnings: {sum(x[3] for x in spec)} - problems in the template/table "
                 "definition itself, not in the workbook; nothing to fix in the file:")
        for name, msg, code, n in spec:
            L.append(f"  - {n} x {name} ({code}): {msg}")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("workbook")
    ap.add_argument("html")
    ap.add_argument("--out")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    meta = cl.load_form_folder(a.folder, os.path.basename(a.folder.rstrip("/\\")))
    wb = Workbook(a.workbook)
    html = open(a.html, encoding="utf-8", errors="ignore").read()
    rules = eh.parse_rules(html)
    text = render(meta, wb, analyse(meta, wb, rules), eh.other_tab_counts(html), eh.spec_warnings(html))
    if a.out:
        open(a.out, "w", encoding="utf-8").write(text)
    print(text)


if __name__ == "__main__":
    main()
