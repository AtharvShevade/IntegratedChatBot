"""Place an operand the filer never reported.

A rule variable with no item and value 0 is an absent fact: the cell was left empty, so no file records where it is.
The rule's own title does name the operands in formula order ('C. Beverages = C.1 Tobacco + C.2 Others'), and the facts
that ARE present sit in rows with those labels. So the absent operand is the row carrying its title label, in the same
column as the present ones. This is used only when every present operand's row label agrees with its own title
segment, which is the check that the title order really follows the formula order.
"""
from __future__ import annotations

import re

from . import fact_address as fa


def _norm(s) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower())


def split_terms(title: str) -> list[str]:
    """'A = (B + C - D)' -> ['A', 'B', 'C', 'D'] (top-level '=', '+', ' - ' only; brackets inside a label are kept)."""
    def top_split(s: str, seps: tuple[str, ...]) -> list[str]:
        out, depth, cur, i = [], 0, "", 0
        while i < len(s):
            ch = s[i]
            depth += ch in "([" ; depth -= ch in ")]"
            hit = next((sp for sp in seps if depth == 0 and s.startswith(sp, i)), None)
            if hit:
                out.append(cur.strip())
                cur, i = "", i + len(hit)
                continue
            cur += ch
            i += 1
        out.append(cur.strip())
        return out

    sides = top_split(title, ("=",))
    if len(sides) != 2:
        return []
    rhs = sides[1].strip()
    while rhs.startswith("(") and rhs.endswith(")") and len(top_split(rhs[1:-1], (" + ",))) >= 1 and \
            _balanced(rhs[1:-1]):
        rhs = rhs[1:-1].strip()
    terms = top_split(rhs, (" + ", " - "))
    return [t.strip().strip('"') for t in [sides[0]] + terms if t.strip()]


def _balanced(s: str) -> bool:
    d = 0
    for ch in s:
        d += ch in "(["
        d -= ch in ")]"
        if d < 0:
            return False
    return d == 0


def _row_label(wb, sheet: str, row: int) -> str:
    return " ".join(str(wb.value(sheet, row, c) or "") for c in range(0, 4))


def _words(s) -> set[str]:
    """Alphabetic words of a label, without numbering ('10.', 'I.', '3.5.2') and short filler."""
    return {w for w in re.findall(r"[a-z]{3,}", str(s or "").lower())}


def _agree(label: str, segment: str) -> bool:
    """Do a sheet row label and a rule-title segment name the same thing? Same text, one inside the other, or most of the
    smaller one's words shared (numbering and punctuation differ between the two sources)."""
    a, b = _norm(label), _norm(segment)
    if not a or not b:
        return False
    if (b in a or a in b) and min(len(a), len(b)) >= 4:
        return True
    wa, wb_ = _words(label), _words(segment)
    small = min(len(wa), len(wb_))
    return small >= 2 and len(wa & wb_) / small >= 0.6


def _find_row(wb, sheet: str, segment: str):
    want = _norm(segment)
    if len(want) < 4:
        return None
    hits = set()
    for key, pos in wb.index(sheet).items():
        if isinstance(key, str) and _norm(key) == want:
            hits |= {r for r, c in pos if c <= 3}
    if not hits:
        for key, pos in wb.index(sheet).items():
            if isinstance(key, str) and len(_norm(key)) >= 6 and (_norm(key) in want or want in _norm(key)):
                hits |= {r for r, c in pos if c <= 3}
    return next(iter(hits)) if len(hits) == 1 else None


def _place(lc, src, sheet, row, col, wb, why):
    a = fa.Address(src.layout_id, src.layout_name, sheet, row, col, "", src.multiplier, wb.value(sheet, row, col))
    a.label_ok = True
    lc.addr = a
    lc.res = fa.Resolved("INFERRED", [a], why)
    lc.inferred = True


def _by_identical_formula(located, comp, order, absent, present, cells, sheet, wb, graph, src) -> int:
    """The rule 'V1 = V2 + V3 - V4' against the template cell formula '=ROUND(B19+B20-B21,2)' of the located total:
    same number of operands and the same signs in the same order -> the absent operands are the cells at their positions.
    Every present operand must already sit at its own position (that is the check that the two really are one equation)."""
    lhs = [(v.upper(), sg) for v, sg in comp.lhs.signed_variables()]
    rhs = [(v.upper(), sg) for v, sg in (comp.rhs.signed_variables() if comp.rhs is not None else [])]
    if len(lhs) != 1 or not rhs:
        return 0
    total = lhs[0][0]
    if total not in present:
        return 0
    refs = graph.signed_refs(sheet, *cells[total])
    if not refs or len(refs) != len(rhs) or [r[2] for r in refs] != [sg for _v, sg in rhs]:
        return 0
    pos = {v: (r[0], r[1]) for (v, _sg), r in zip(rhs, refs)}
    if any(cells[v] != pos[v] for v in present if v in pos):
        return 0
    placed = 0
    for v in absent:
        if v in pos:
            r, c = pos[v]
            _place(located[v][0], src, sheet, r, c, wb, "operand not reported; same equation as the template's formula for the total")
            placed += 1
    return placed


def resolve_by_formulas(located: dict, comp, title: str, wb, graph) -> int:
    """Place absent operands from the template's own sums. The total's formula lists the cells it is built from; the
    absent operand is one of them (restricted to the present operands' column; the title label picks it when several
    remain). If the TOTAL is the absent one, it is the cell whose formula sums all the present parts."""
    order = [v.upper() for v, _ in comp.lhs.signed_variables()] +             [v.upper() for v, _ in (comp.rhs.signed_variables() if comp.rhs is not None else [])]
    absent = [v for v in order if located.get(v) and not located[v][0].fact.concept and not located[v][0].addr]
    present = [v for v in order if located.get(v) and located[v][0].addr]
    if not absent or not present:
        return 0
    sheets = {located[v][0].addr.sheet for v in present}
    cols = {located[v][0].addr.col for v in present}
    if len(sheets) != 1 or len(cols) != 1:
        return 0
    sheet, col = next(iter(sheets)), next(iter(cols))
    cells = {v: (located[v][0].addr.row, located[v][0].addr.col) for v in present}
    src = located[present[0]][0].addr
    n = _by_identical_formula(located, comp, order, absent, present, cells, sheet, wb, graph, src)
    if n:
        return n
    terms = split_terms(title)
    seg = dict(zip(order, terms)) if len(terms) == len(order) else {}
    taken = set(cells.values())
    placed = 0
    for v in absent:
        cand: set = set()
        # absent part: sits under a present total's formula together with the other present parts
        for t in present:
            pres = graph.precedents(sheet, *cells[t])
            parts = [cells[o] for o in present if o != t]
            if pres and all(p in pres for p in parts):
                cand |= {c for c in pres if c[1] == col and c not in taken}
        # absent total: a cell whose formula sums every present part
        if not cand and len(present) >= 2:
            deps = None
            for p in present:
                d = {x for x in graph.dependents(sheet, *cells[p]) if x[1] == col and x not in taken}
                deps = d if deps is None else deps & d
            cand = deps or set()
        if len(cand) > 1 and seg.get(v):
            by_label = {c for c in cand if _agree(_row_label(wb, sheet, c[0]), seg[v])}
            if by_label:
                cand = by_label
        if len(cand) == 1:
            r, c = next(iter(cand))
            _place(located[v][0], src, sheet, r, c, wb, "operand not reported; found from the template's own sum formulas")
            taken.add((r, c))
            placed += 1
    return placed


def resolve(located: dict, comp, title: str, wb, graph=None):
    """Fill lc.addr for absent operands (in place). Returns how many were placed."""
    if wb is None or getattr(wb, "is_template", False) or comp is None:
        return 0
    if graph is not None:
        n = resolve_by_formulas(located, comp, title, wb, graph)
        if n:
            return n
    order = [v.upper() for v, _ in comp.lhs.signed_variables()] + \
            [v.upper() for v, _ in (comp.rhs.signed_variables() if comp.rhs is not None else [])]
    terms = split_terms(title)
    if not order or len(order) != len(terms):
        return 0
    absent = [v for v in order if located.get(v) and not located[v][0].fact.concept and not located[v][0].addr]
    present = [v for v in order if located.get(v) and located[v][0].addr]
    if not absent or not present:
        return 0
    seg = dict(zip(order, terms))
    sheets = {located[v][0].addr.sheet for v in present}
    cols = {located[v][0].addr.col for v in present}
    if len(sheets) != 1 or len(cols) != 1:
        return 0
    sheet, col = next(iter(sheets)), next(iter(cols))
    if not all(_agree(_row_label(wb, sheet, located[v][0].addr.row), seg[v]) for v in present):
        return 0
    placed = 0
    for v in absent:
        row = _find_row(wb, sheet, seg[v])
        lc = located[v][0]
        if row is None:
            continue
        src = located[present[0]][0].addr
        a = fa.Address(src.layout_id, src.layout_name, sheet, row, col, "", src.multiplier, wb.value(sheet, row, col))
        a.label_ok = True
        lc.addr = a
        lc.res = fa.Resolved("INFERRED", [a], f"operand not reported; row '{seg[v]}' found from the rule title")
        lc.inferred = True
        placed += 1
    return placed
