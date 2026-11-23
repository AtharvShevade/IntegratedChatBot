"""Structured, LLM-worded explanation of one return's error file.

    python explain_llm.py <metadata folder> <workbook> <error .html> [--out report.md] [--model qwen2.5:7b] [--no-llm]

Layering (the LLM never decides anything):
  1. explain_workbook   locates every fact in the workbook, evaluates every rule, solves the fix amounts
  2. this file          turns each finding into a FACT SHEET (plain dict of verified numbers/cells)
  3. LLM (Ollama)       words each fact sheet: what is wrong, why it matters, what to do
  4. guard              every number in the LLM text must come from the fact sheet, otherwise the
                        deterministic wording is used instead (and the card says so)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from decimal import Decimal

from . import cell_locator as cl          # noqa: E402
from . import error_html as eh            # noqa: E402
from . import explain_workbook as ew      # noqa: E402
from .workbook import Workbook      # noqa: E402

OLLAMA = os.environ.get("OLLAMA_URL", "http://localhost:11434")

_SYSTEM = (
    "You explain regulatory return validation failures to the person who filled the Excel return. "
    "Use ONLY the facts in the JSON. Never calculate, never invent a cell, number or rule. Copy cell "
    "addresses and numbers exactly as given. Plain business language, no XBRL jargon. "
    "When fix options are listed, present them as alternatives and name the one with also_in_failing_rules as the likely root cause. Reply as JSON: {\"problem\": \"1-2 sentences\", \"why\": \"1 sentence\", \"action\": \"1-2 sentences\"}."
)


def _num(s) -> str:
    return re.sub(r"[,\s]", "", str(s))


def _numbers_in(text: str) -> set[str]:
    return {_num(n).rstrip(".") for n in re.findall(r"\d[\d,]*\.?\d*", text)}


def _allowed(facts: dict) -> set[str]:
    blob = json.dumps(facts, ensure_ascii=False)
    out = _numbers_in(blob)
    extra = set()
    for n in out:                                   # 18500.0 == 18,500 == 18500
        try:
            d = Decimal(n)
            extra |= {str(d.normalize()), f"{d:.2f}", f"{d:.1f}", str(int(d)) if d == d.to_integral() else n}
        except Exception:
            pass
    return out | extra


def guard(text: str, facts: dict) -> bool:
    ok = _allowed(facts)
    for n in _numbers_in(text):
        if n in ok or len(n.replace(".", "")) <= 1:
            continue
        try:
            d = Decimal(n)
            if str(d.normalize()) in ok or f"{d:.2f}" in ok:
                continue
        except Exception:
            pass
        return False
    return True


def ask(model: str, facts: dict, timeout: int = 120) -> dict | None:
    body = {"model": model, "stream": False, "format": "json", "options": {"temperature": 0},
            "messages": [{"role": "system", "content": _SYSTEM},
                         {"role": "user", "content": json.dumps(facts, ensure_ascii=False)}]}
    req = urllib.request.Request(OLLAMA + "/api/chat", json.dumps(body).encode(), {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            msg = json.loads(r.read())["message"]["content"]
        data = json.loads(msg)
        return {k: str(data.get(k, "")).strip() for k in ("problem", "why", "action")}
    except Exception as exc:                        # noqa: BLE001
        print(f"  (llm unavailable: {exc})", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------------------------------------
# fact sheets
# ---------------------------------------------------------------------------------------------------------
def _cell_rows(wb, located):
    rows = []
    for var in sorted(located):
        for lc in located[var]:
            a = lc.addr
            rows.append({"variable": var, "item": lc.fact.concept, "cell": lc.where,
                         "row_label": ew._label(wb, a) if a else "",
                         "cell_value": None if a is None else ("blank" if a.workbook_value in (None, "") else a.workbook_value),
                         "amount_inr": lc.fact.value})
    return rows


def _fix_candidates(comp, located):
    """Cells that could be the wrong one, each with the value that would balance this rule alone.
    A cell qualifies when the needed value is not negative and it is either non-zero now or the only
    zero/empty cell with that need (several identical zero siblings are ambiguous, so none is blamed)."""
    cands = []
    for var, (cur, need) in sorted(ew.required_values(comp, located).items()):
        lc = located[var][0]
        if lc.addr is None or abs(cur - need) < Decimal("0.5") or need < 0:
            continue
        cands.append((lc, cur, need))
    if len([c for c in cands if c[1] == 0]) > 1:
        cands = [c for c in cands if c[1] != 0]
    return [{"cell": lc.where, "now": str(ew._units(lc, cur)), "would_need_to_be": str(ew._units(lc, need))}
            for lc, cur, need in cands]


def data_sheets(wb, item, cell_counts=None):
    rule, expr, comp, kind, findings = item
    for inst, located, ev in findings:
        lhs, rhs = ew._dec(ev.get("lhs_value", ev.get("lhs"))), ew._dec(ev.get("rhs_value", ev.get("rhs")))
        fix = _fix_candidates(comp, located)
        for x in fix:
            n = (cell_counts or {}).get(x["cell"], 0)
            if n > 1:
                x["also_in_failing_rules"] = n - 1
        yield {
            "kind": "DATA", "rule": rule.name, "rule_text": expr,
            "meaning": inst.title,
            "left_side_inr": str(lhs), "right_side_inr": str(rhs),
            "difference_inr": str(lhs - rhs) if lhs is not None and rhs is not None else None,
            "cells": _cell_rows(wb, located), "fix_options_each_alone": fix,
            "note": "cell_value is in the template unit, amount_inr the same value in rupees. Each fix option balances this "
                    "rule if that ONE cell is changed and the others are right; options are alternatives. A cell with "
                    "also_in_failing_rules appears in other failing rules too and is the most likely root cause.",
        }


def rule_sheet(wb, item):
    rule, expr, comp, kind, findings = item
    eq = lt = 0
    differing = []
    for inst, located, ev in findings:
        l, r = ew._dec(ev.get("lhs_value", ev.get("lhs"))), ew._dec(ev.get("rhs_value", ev.get("rhs")))
        if l is None or r is None:
            continue
        if l == r:
            eq += 1
        else:
            lt += 1
            differing.append({"cells": [f"{lc.where}={lc.fact.value}" for v in sorted(located) for lc in located[v]]})
    return {"kind": "RULE", "rule": rule.name, "rule_text": expr, "meaning": findings[0][0].title if findings else "",
            "operator": comp.operator, "failing_instances": len(findings),
            "sides_equal": eq, "sides_differ": lt, "differing_examples": differing[:6]}


def cover_sheets(wb, item):
    rule, expr, comp, kind, findings = item
    for inst, located, ev in findings:
        lhs, rhs = ew._dec(ev.get("lhs_value", ev.get("lhs"))), ew._dec(ev.get("rhs_value", ev.get("rhs")))
        yield {"kind": "COVER", "rule": rule.name, "rule_text": expr, "meaning": inst.title,
               "left_sum_inr": str(lhs), "right_sum_inr": str(rhs),
               "shortfall_inr": str(rhs - lhs) if lhs is not None and rhs is not None else None,
               "cells": _cell_rows(wb, located)}


# ---------------------------------------------------------------------------------------------------------
# deterministic wording (fallback and cross-check)
# ---------------------------------------------------------------------------------------------------------
def fallback(f: dict) -> dict:
    if f["kind"] == "DATA":
        fx = f["fix_options_each_alone"]
        act = " or ".join(f"{x['cell']} would need to be {x['would_need_to_be']} (now {x['now']})" for x in fx) or \
              "Re-check the cells listed so that the parts add up to the total."
        return {"problem": f"The two sides of the rule differ by {f['difference_inr']} INR.",
                "why": "The return fails this validation until both sides agree.", "action": act}
    if f["kind"] == "RULE":
        return {"problem": f"{f['sides_equal']} of {f['failing_instances']} failures have equal sides; "
                           f"{f['sides_differ']} have different sides.",
                "why": f"The rule uses a strict '{f['operator']}', so equal values (for example 0 and 0) fail.",
                "action": "Review the instances where the sides really differ; equal ones follow from the rule wording."}
    return {"problem": f"The right-hand total exceeds the left by {f['shortfall_inr']} INR.",
            "why": "The left group must be at least as large as the right group.",
            "action": "Compare the listed cells on both sides."}


def word(model, f, use_llm):
    if not use_llm:
        return fallback(f), "deterministic"
    out = ask(model, f)
    if out and all(out.values()) and guard(" ".join(out.values()), f):
        return out, f"LLM {model} (numbers verified)"
    return fallback(f), "deterministic (LLM text rejected by number check or unavailable)"


# ---------------------------------------------------------------------------------------------------------
def build(folder, workbook_path, html_path, model, use_llm):
    meta = cl.load_form_folder(folder, os.path.basename(folder.rstrip("/\\")))
    wb = Workbook(workbook_path)
    html = open(html_path, encoding="utf-8", errors="ignore").read()
    analysed = ew.analyse(meta, wb, eh.parse_rules(html))
    cards = []
    cell_counts: dict[str, int] = {}
    for item in analysed:
        if item[4] and ew.verdict(item[2], item[4][0][2]) == "DATA":
            for _inst, located, _ev in item[4]:
                for w in {lc.where for v in located.values() for lc in v if lc.addr}:
                    cell_counts[w] = cell_counts.get(w, 0) + 1
    for item in analysed:
        rule, expr, comp, kind, findings = item
        v = ew.verdict(comp, findings[0][2] if findings else None)
        if v == "RULE":
            cards.append(rule_sheet(wb, item))
        elif v == "COVER":
            cards.extend(cover_sheets(wb, item))
        else:
            cards.extend(data_sheets(wb, item, cell_counts))
    for c in cards:
        c["wording"], c["source"] = word(model, c, use_llm)
    return cards, eh.spec_warnings(html), sum(len(r[4]) for r in analysed), meta, wb


def summary(model, cards, use_llm):
    facts = {"data_errors": [{"rule": c["rule"], "difference_inr": c["difference_inr"], "cells": [x["cell"] for x in c["cells"]][:4]}
                             for c in cards if c["kind"] == "DATA"],
             "rule_wording_failures": [{"rule": c["rule"], "failing": c["failing_instances"], "equal_sides": c["sides_equal"],
                                        "different_sides": c["sides_differ"]} for c in cards if c["kind"] == "RULE"],
             "coverage_failures": [c["rule"] for c in cards if c["kind"] == "COVER"]}
    if use_llm:
        out = ask(model, {**facts, "task": "Write the executive summary in the 'problem' field (3 sentences); "
                                           "put the most important fix in 'action'; 'why' = impact."})
        if out and all(out.values()) and guard(" ".join(out.values()), facts):
            return out
    return {"problem": f"{len(facts['data_errors'])} identity checks fail on the data, {len(facts['rule_wording_failures'])} "
                       f"rules fail mostly because of strict comparisons, {len(facts['coverage_failures'])} coverage check fails.",
            "why": "The return cannot be accepted until the data errors are fixed.",
            "action": "Start with the data errors in section 2."}


def render(cards, spec, total_instances, meta, wb, model, use_llm) -> str:
    L = ["# Return validation explanation\n"]
    L.append(f"Return metadata: form {meta.form_id} | workbook: {os.path.basename(wb.path)} | "
             f"{len(cards)} findings from {total_instances} failing instances | wording: "
             f"{model if use_llm else 'deterministic'}\n")
    s = summary(model, cards, use_llm)
    L += ["## 1. Summary", s["problem"], "", f"**Impact:** {s['why']}", "", f"**First action:** {s['action']}", ""]

    data = [c for c in cards if c["kind"] == "DATA"]
    L.append(f"## 2. Data errors - fix in the workbook ({len(data)})\n")
    for i, c in enumerate(data, 1):
        L += [f"### 2.{i} {c['rule']}", f"*Checks:* {c['meaning']}", "", f"**Problem.** {c['wording']['problem']}",
              f"**Why it fails.** {c['wording']['why']}", f"**What to do.** {c['wording']['action']}", "",
              f"Left = {ew._money(Decimal(c['left_side_inr']))} INR, right = {ew._money(Decimal(c['right_side_inr']))} INR, "
              f"difference = {ew._money(Decimal(c['difference_inr']))} INR", "",
              "| Var | Item | Cell | Row label | Cell value | INR |", "|---|---|---|---|---|---|"]
        L += [f"| {x['variable']} | {x['item']} | {x['cell']} | {x['row_label']} | {x['cell_value']} | {x['amount_inr']} |"
              for x in c["cells"]]
        L += ["", f"<sub>wording: {c['source']}</sub>", ""]

    rules = [c for c in cards if c["kind"] == "RULE"]
    L.append(f"## 3. Failures caused by how the rule is written ({len(rules)})\n")
    for i, c in enumerate(rules, 1):
        L += [f"### 3.{i} {c['rule']}", f"*Checks:* {c['meaning']}", f"Rule: `{c['rule_text']}` - {c['failing_instances']} failing instances", "",
              f"**Problem.** {c['wording']['problem']}", f"**Why it fails.** {c['wording']['why']}",
              f"**What to do.** {c['wording']['action']}", ""]
        if c["differing_examples"]:
            L.append("Instances where the sides really differ (first few):")
            L += [f"- {', '.join(e['cells'])}" for e in c["differing_examples"]]
        L += ["", f"<sub>wording: {c['source']}</sub>", ""]

    cov = [c for c in cards if c["kind"] == "COVER"]
    L.append(f"## 4. Coverage checks ({len(cov)})\n")
    for i, c in enumerate(cov, 1):
        L += [f"### 4.{i} {c['rule']}", f"*Checks:* {c['meaning']}", "", f"**Problem.** {c['wording']['problem']}",
              f"**Why it fails.** {c['wording']['why']}", f"**What to do.** {c['wording']['action']}", "",
              "| Var | Item | Cell | Cell value | INR |", "|---|---|---|---|---|"]
        L += [f"| {x['variable']} | {x['item']} | {x['cell']} | {x['cell_value']} | {x['amount_inr']} |" for x in c["cells"]]
        L += ["", f"<sub>wording: {c['source']}</sub>", ""]

    L.append("## 5. Specification warnings - not about the Excel file\n")
    L.append(f"{sum(x[3] for x in spec)} warnings about the table definition (taxonomy/template); nothing to change in the workbook.")
    L += [f"- {n} x {name} ({code}): {msg}" for name, msg, code, n in spec]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("workbook")
    ap.add_argument("html")
    ap.add_argument("--out")
    ap.add_argument("--model", default="qwen2.5:7b")
    ap.add_argument("--no-llm", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    use_llm = not a.no_llm
    cards, spec, total, meta, wb = build(a.folder, a.workbook, a.html, a.model, use_llm)
    text = render(cards, spec, total, meta, wb, a.model, use_llm)
    if a.out:
        open(a.out, "w", encoding="utf-8").write(text)
    print(text)


if __name__ == "__main__":
    main()
