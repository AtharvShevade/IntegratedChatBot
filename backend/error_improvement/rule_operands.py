"""Place an operand the filer never reported, using the rule's own definition and the reported instance.

The rule says what the operand is (concept + pinned dimensions); a present operand of the same rule gives the rest of
the context (implicit filtering: all variables share every aspect a filter does not pin). Concept and members then go
through the normal mapping to a cell. Used only when exactly one cell in the present operands' sheet fits.
"""
from __future__ import annotations

from . import fact_address as fa


def place(located: dict, rule_name: str, meta, wb) -> int:
    defs = getattr(meta, "formula_defs", None)
    rep = getattr(meta, "reported", None)
    d = (defs or {}).get(rule_name)
    if not d or rep is None or wb is None or getattr(wb, "is_template", False):
        return 0
    absent = [v for v, l in located.items() if l and not l[0].fact.concept and not l[0].addr]
    sibs = [v for v, l in located.items() if l and l[0].fact.concept and l[0].addr]
    if not absent or not sibs:
        return 0
    s = sibs[0]
    sfact, saddr = located[s][0].fact, located[s][0].addr
    sdims = rep.ctx_dims(sfact.context)
    if sdims is None:
        return 0
    pinned_by_sibling = set(d["vars"].get(s.upper(), {}).get("dims", {}))
    base = {a: m for a, m in sdims.items() if a not in pinned_by_sibling}
    placed = 0
    for v in absent:
        vd = d["vars"].get(v.upper())
        if not vd:
            continue
        concepts = vd["concepts"]
        concept = concepts[0] if len(concepts) == 1 else (sfact.concept if not concepts else None)
        if concept is None:
            continue
        dims = dict(base)
        dims.update({a: ms[0] for a, ms in {**d.get("set_dims", {}), **vd["dims"]}.items() if len(ms) == 1})
        cands = fa.candidates(meta, wb, concept, "", members=set(dims.values()))
        cands = [a for a in cands if a.sheet == saddr.sheet] or cands
        cands = [a for a in cands if a.label_ok] or cands
        uniq = {(a.sheet, a.row, a.col): a for a in cands}
        if len(uniq) != 1:
            continue
        a = next(iter(uniq.values()))
        lc = located[v][0]
        lc.addr = a
        lc.res = fa.Resolved("INFERRED", [a], f"operand not reported; {concept} from the rule's own definition, placed through the mapping")
        lc.inferred = True
        placed += 1
    return placed
