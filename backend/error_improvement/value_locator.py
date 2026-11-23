"""Locate a failing value using only the user's workbook and what the error file says about it.

No mapping metadata is needed. Evidence, in order of strength:
  1. the value itself: the cells that hold it (numbers are tried at the usual template scalings 1, 10^3, 10^5, 10^6, 10^7)
  2. the row label next to the cell shares words with the item / dimension members / the rule's wording for that operand
  3. the column header above the cell shares words with the item name
  4. the sheet name shares words with the rule's name
A cell is named only when it is the single hit, or clearly the best-scoring hit; otherwise the hits are returned as candidates.
The result is INFERRED, never verified: nothing here has been checked against the return's own mapping.
Zero values carry no evidence (every empty cell is a zero) and are never located this way.
"""
from __future__ import annotations

import bisect
import re
from decimal import Decimal, InvalidOperation

from . import fact_address as fa

MULT = (1, 1000, 100000, 1000000, 10000000)
_STOP = {"member", "axis", "domain", "the", "and", "for", "total", "amount", "number", "with", "from", "that", "this", "value"}


def words(text) -> set[str]:
    t = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", str(text or ""))
    return {w for w in re.findall(r"[a-z]{3,}", t.lower()) if w not in _STOP}


def _dec(v):
    return fa._dec(v)


class ValueLocator:
    def __init__(self, wb):
        self.wb = wb
        self._prior_mult: int | None = None
        self.min_score = 2                  # evidence needed to name a cell
        self.margin = 1                     # by how much the best hit must beat the second
        self._label_cache: dict = {}
        self._header_cache: dict = {}
        self._sheet_cache: dict = {}
        self._hits_cache: dict = {}         # (value, decimals) -> hits: the same value is asked for by every pass of one analysis

    # -- evidence -------------------------------------------------------------------------------------------------
    def hits(self, value: str, decimals=None) -> list[tuple[str, int, int, int]]:
        key = (str(value), str(decimals))
        found = self._hits_cache.get(key)
        if found is None:
            found = self._hits_cache[key] = self._find(value, decimals)
        return list(found)                  # a copy: callers may sort or trim what they get

    def _sheet_index(self, sh):
        """One sheet's numeric cells bucketed by key (the value rounded to 4 places): (sorted keys, {key: (cells, values, same)}).
        Built once per analysis. `same` is the one value when every cell of the bucket holds it (the 0.0 bucket is thousands of empty
        cells), so the tolerance test runs once for the bucket instead of once per cell."""
        built = self._sheet_cache.get(sh)
        if built is None:
            buckets = {}
            for key, cells in self.wb.index(sh).items():
                rcs, dvs = [], []
                for r, c in cells:
                    v = self.wb.value(sh, r, c)
                    if isinstance(v, (int, float)) and not isinstance(v, bool):
                        rcs.append((r, c))
                        dvs.append(Decimal(str(v)))
                if rcs:
                    buckets[key] = (rcs, dvs, dvs[0] if all(d == dvs[0] for d in dvs) else None)
            built = self._sheet_cache[sh] = (sorted(buckets), buckets)
        return built

    def _find(self, value: str, decimals=None) -> list[tuple[str, int, int, int]]:
        """(sheet, row, col, scaling) of the cells holding the value. The index is keyed on values rounded to 4 places, which at a large
        scaling turns a small number (a rate of 0.06 at 10^7) into 0.0 and "finds" every empty cell. So each hit is checked against the
        cell's own value: it must equal the fact within the fact's own precision. A fact filed to d places is also looked for at the
        cells within half a unit of its last place (a range of keys, found by bisection)."""
        t = _dec(value)
        if t is None or t == 0:
            return []
        tol = fa.tolerance(t, decimals)
        out = []
        for sh in self.wb.sheets:
            keys, buckets = self._sheet_index(sh)
            for m in MULT:
                base = float(t / m)
                reach = int(tol / m / Decimal("0.0001"))
                if 0 < reach <= 200:
                    centre, span = round(base, 4), reach * 0.0001 + 0.00005
                    cand = keys[bisect.bisect_left(keys, centre - span):bisect.bisect_right(keys, centre + span)]
                else:
                    k = round(base, 4)
                    cand = [k] if k in buckets else []
                for key in cand:
                    rcs, dvs, same = buckets[key]
                    if same is not None:
                        if abs(same * m - t) <= tol:
                            out.extend((sh, r, c, m) for r, c in rcs)
                    else:
                        out.extend((sh, r, c, m) for (r, c), dv in zip(rcs, dvs) if abs(dv * m - t) <= tol)
        return out

    def row_label(self, sheet: str, row: int) -> str:
        k = (sheet, row)
        if k not in self._label_cache:
            self._label_cache[k] = " ".join(str(self.wb.value(sheet, row, c) or "") for c in range(0, 4)
                                            if isinstance(self.wb.value(sheet, row, c), str))
        return self._label_cache[k]

    def header(self, sheet: str, row: int, col: int, depth: int = 25) -> str:
        k = (sheet, row, col)
        if k not in self._header_cache:
            parts = []
            for r in range(row - 1, max(0, row - depth), -1):
                v = self.wb.value(sheet, r, col)
                if isinstance(v, str) and v.strip():
                    parts.append(v)
            self._header_cache[k] = " ".join(parts)
        return self._header_cache[k]

    def learn_scaling(self, values: list[str]) -> None:
        """The scaling most often seen among values that hit exactly one cell: the workbook's usual unit."""
        votes: dict[int, int] = {}
        for v in values:
            h = self.hits(v)
            if len(h) == 1:
                votes[h[0][3]] = votes.get(h[0][3], 0) + 1
        self._prior_mult = max(votes, key=votes.get) if votes else None

    # -- decision -------------------------------------------------------------------------------------------------
    def locate(self, concept: str, members, value: str, hint_words: set[str], rule_name: str = "", decimals=None):
        """-> (best hit | None, [candidate hits], why, strength) ; a hit is (sheet, row, col, multiplier)."""
        hs = self.hits(value, decimals)
        if not hs:
            return None, [], "value not found in the workbook", ""
        if self._prior_mult is not None:
            same = [h for h in hs if h[3] == self._prior_mult]
            hs = same or hs
        if len(hs) == 1:
            return hs[0], hs, "the only cell holding this value", "strong"
        item = words(concept) | set().union(*(words(m) for m in members)) if members else words(concept)
        hint = item | hint_words
        rn = re.sub(r"[^a-z0-9]", "", rule_name.lower())

        def score(h):
            sh, r, c, _m = h
            s_row = len(words(self.row_label(sh, r)) & hint)
            s_head = len(words(self.header(sh, r, c)) & words(concept))
            s_sheet = 1 if len(re.sub(r"[^a-z0-9]", "", sh.lower())) >= 4 and re.sub(r"[^a-z0-9]", "", sh.lower()) in rn else 0
            return 2 * s_row + s_head + s_sheet

        scored = sorted(((score(h), h) for h in hs), key=lambda x: -x[0])
        best, second = scored[0][0], scored[1][0]
        top6 = [h for _s, h in scored[:6]]
        if best >= 4 and best - second >= 3:
            return scored[0][1], top6, "best match on row label, column header and sheet name", "strong"
        if best >= self.min_score and best - second >= self.margin:
            return scored[0][1], top6, "best match on row label, column header and sheet name (moderate confidence)", "weak"
        return None, top6, "several cells hold this value and the labels do not decide", ""

    def resolve(self, fact, hint_words: set[str], rule_name: str = ""):
        """Same shape as fact_address.resolve_fact: Resolved(status, addresses, note)."""
        members = fa.context_members(fact.context)
        best, cands, why, strength = self.locate(fact.concept, members, fact.value, hint_words, rule_name, fact.decimal)
        if not cands:
            return None

        def addr(h):
            sh, r, c, m = h
            return fa.Address("", "", sh, r, c, "", m, self.wb.value(sh, r, c))
        if best is not None:
            a = addr(best)
            a.label_ok = True
            return fa.Resolved("INFERRED" if strength == "strong" else "LIKELY", [a] + [addr(h) for h in cands if h != best],
                               "located from the workbook alone: " + why)
        return fa.Resolved("UNCONFIRMED", [addr(h) for h in cands], why)
