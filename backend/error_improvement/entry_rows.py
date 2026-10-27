"""Locate facts through the ENTRY they belong to.

Some sheets hold one row per entry (an officer, a counterparty) and the mapping's own cell cannot say which row. The
context does: its non-date members ('ChiefFinancialOfficer') are the entry's name, and the same name is the row label
in the sheet ('Chief Financial Officer'). For each context we take the rows whose label matches a member, count which
row holds the most of that context's reported values, and give each fact the cell in that row that holds its value.
A fact is placed only on a value match, and only when one row clearly wins and one column in it holds the value.
"""
from __future__ import annotations

import collections
import re

from . import fact_address as fa


def _norm(s) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower())


def rows_with_label(wb, sheet: str, member: str) -> set[int]:
    want = _norm(member)
    rows = set()
    for key, pos in wb.index(sheet).items():
        if not isinstance(key, str):
            continue
        k = _norm(key)
        if len(k) >= 8 and (k == want or (min(len(k), len(want)) >= 8 and (k in want or want in k))):
            rows |= {r for r, c in pos if c <= 3}
    return rows


def refine(analysed, wb, max_col: int = 80) -> int:
    """Give a cell to facts that have none, via their entry's row. Returns how many were placed."""
    if wb is None or getattr(wb, "is_template", False):
        return 0
    groups: dict[str, list] = collections.defaultdict(list)
    for _r, _e, _c, _k, findings in analysed:
        for _i, located, _ev in findings:
            for lcs in located.values():
                for lc in lcs:
                    t = fa._dec(lc.fact.value)
                    nonzero = (t is None and str(lc.fact.value).strip()) or (t is not None and t != 0)
                    if not lc.addr and lc.fact.concept and nonzero and lc.res.addresses:
                        groups[lc.fact.context].append(lc)
    placed = 0
    for ctx, lcs in groups.items():
        members = [m for m in fa.context_members(ctx) if len(_norm(m)) >= 8]
        if not members:
            continue
        sheets = {sh for lc in lcs for a in lc.res.addresses for sh in fa.sheet_family(wb, a.sheet)}
        candidates = {(sh, r) for sh in sheets for m in members for r in rows_with_label(wb, sh, m)}
        if not candidates:
            continue
        hits_by_row: dict[tuple, dict] = {}
        for sh, r in candidates:
            per_fact = {}
            for lc in lcs:
                src = lc.res.addresses[0]
                cols = []
                for c in range(0, max_col):
                    a = fa.Address(src.layout_id, src.layout_name, sh, r, c, src.cell_code, src.multiplier or 1, wb.value(sh, r, c))
                    if a.workbook_value is not None and fa.value_matches(a, lc.fact.value):
                        cols.append(a)
                if cols:
                    per_fact[id(lc)] = cols
            if per_fact:
                hits_by_row[(sh, r)] = per_fact
        if not hits_by_row:
            continue
        ranked = sorted(hits_by_row.items(), key=lambda kv: -len(kv[1]))
        if len(ranked) > 1 and len(ranked[0][1]) == len(ranked[1][1]):
            continue                                         # two rows hold equally many of this entry's values: unclear
        per_fact = ranked[0][1]
        for lc in lcs:
            cols = per_fact.get(id(lc))
            if not cols:
                continue
            if len(cols) > 1:                                # same value in several columns of the row: use the mapped column
                want = {a.col for a in lc.res.addresses}
                cols = [a for a in cols if a.col in want] or cols
            if len(cols) != 1:
                continue
            lc.addr = cols[0]
            lc.addr.label_ok = True
            lc.res = fa.Resolved("INFERRED", [cols[0]], "row found from the entry name in the context")
            lc.dynamic = False
            lc.reason = ""
            placed += 1
    return placed
