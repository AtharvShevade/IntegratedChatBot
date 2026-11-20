"""Locate a fact from the LABELS its context names, when the mapping's own cell does not hold the filed value.

A context id spells out the entry it belongs to ('UptoTwentyEightDays', 'AboveTenCroreAndUptoFiftyCrore', 'RupeeTermDeposits').
The same words are in the sheet: the column header ('Up to 28 days'), the row label ('Rs. 10 crore and below Rs. 50 crore') and
the section the row sits in ('Rupee Term Deposits'). This module reads those labels, turns number words into digits so that
'TwentyEight' and '28' meet, and scores every cell that holds the fact's value by how many of the context's members its row,
section and column labels explain. A cell is named only when one cell clearly explains the most.

Nothing is specific to one return: it needs only the workbook, the fact (value, decimals, context) and the sheet(s) to look in.
The answer is INFERRED (every member explained) or LIKELY (best, with a margin): never verified.
"""
from __future__ import annotations

import re

from . import fact_address as fa

_UNITS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
          "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
          "seventeen": 17, "eighteen": 18, "nineteen": 19}
_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90, "ninty": 90}
_HUNDRED = {"hundred", "hundered", "hundreds"}
_SYNONYM = {"rupee": "rs", "rupees": "rs", "inr": "rs", "rs": "rs", "upto": "upto", "lakhs": "lakh", "crores": "crore",
            "days": "day", "years": "year", "months": "month", "weeks": "week", "deposits": "deposit", "loans": "loan",
            "accounts": "account", "banks": "bank", "above": "above", "over": "above", "below": "below", "under": "below"}
_STOP = {"member", "axis", "domain", "the", "and", "of", "for", "to", "a", "an", "in", "on", "than", "more", "less", "up",
         "total", "amount", "item", "items", "other", "others"}
_MIN_NUMBER_UNITS = {"crore", "lakh", "day", "year", "month", "week", "thousand", "million", "billion", "percent"}
MAX_UP, MAX_LEFT = 60, 8


def _split(text) -> list[str]:
    t = re.sub(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Za-z])(?=\d)|(?<=\d)(?=[A-Za-z])", " ", str(text or ""))
    return re.findall(r"[a-z]+|\d+(?:[.,]\d+)*", t.lower())


def tokens(text) -> tuple[list[int], list[str]]:
    """-> (numbers in order of appearance, content words). Number words become digits ('TwentyEight' -> 28, 'OneHundred' -> 100,
    'OneEightyOne' -> 181); 'up to' / 'upto' meet; plurals and rupee spellings are normalised; filler words are dropped."""
    raw = _split(text)
    nums: list[int] = []
    words: list[str] = []
    i = 0
    while i < len(raw):
        w = raw[i]
        if w[0].isdigit():
            try:
                nums.append(int(float(w.replace(",", ""))))
            except ValueError:
                pass
            i += 1
        elif w in _UNITS or w in _TENS:
            n, j = 0, i
            if w in _UNITS and j + 2 < len(raw) and raw[j + 1] in _TENS and raw[j + 2] in _UNITS and 0 < _UNITS[w] < 10:
                n, j = _UNITS[w] * 100 + _TENS[raw[j + 1]] + _UNITS[raw[j + 2]], j + 3        # 'one eighty one' = 181
            elif w in _UNITS and j + 1 < len(raw) and raw[j + 1] in _TENS and 0 < _UNITS[w] < 10:
                n, j = _UNITS[w] * 100 + _TENS[raw[j + 1]], j + 2                              # 'one eighty' = 180
            else:
                n = _UNITS.get(w) if w in _UNITS else _TENS[w]
                j += 1
                if w in _TENS and j < len(raw) and raw[j] in _UNITS and 0 < _UNITS[raw[j]] < 10:
                    n, j = n + _UNITS[raw[j]], j + 1                                           # 'twenty eight' = 28
                if j < len(raw) and raw[j] in _HUNDRED:
                    n, j = n * 100, j + 1
            nums.append(n)
            i = j
        elif w in _HUNDRED:
            nums.append(100)
            i += 1
        else:
            if w == "up" and i + 1 < len(raw) and raw[i + 1] == "to":
                w, i = "upto", i + 1
            nxt = raw[i + 1] if i + 1 < len(raw) else ""
            amount_follows = bool(nxt) and (nxt[0].isdigit() or nxt in _UNITS or nxt in _TENS or nxt in _HUNDRED)
            w = _SYNONYM.get(w, w)
            if w == "rs" and amount_follows:
                pass                                   # 'Rs. 1 crore' / 'RupeeOneCrore': an amount prefix, not a category
            elif w not in _STOP and len(w) > 1:
                words.append(w)
            i += 1
    return nums, words


def _covers(member_words: list[str], label_words: list[str]) -> bool:
    """Every word of the member is in the label. A short label word that is the initials of consecutive member words stands for them
    ('FC' for 'Foreign Currency')."""
    left = list(member_words)
    for lw in label_words:
        if lw in left:
            left.remove(lw)
            continue
        if 2 <= len(lw) <= 4:
            for i in range(len(left) - len(lw) + 1):
                if all(left[i + j][0] == lw[j] for j in range(len(lw))):
                    del left[i:i + len(lw)]
                    break
    return not left


def _explains(member: tuple[list[int], list[str]], label: tuple[list[int], list[str]]) -> bool:
    """Does one label text spell out this context member? A member with numbers needs the same numbers in the label and at least one
    shared word (a unit such as crore / days); a member without numbers needs all its words in the label."""
    mn, mw = member
    ln, lw = label
    if mn:
        if mn != ln:
            return False
        shared = set(mw) & set(lw)
        return bool(shared) or not mw
    if not mw:
        return False
    return _covers(mw, lw)


class LabelLocator:
    def __init__(self, wb, value_locator):
        self.wb = wb
        self.vl = value_locator
        self._row_cache: dict = {}
        self._head_cache: dict = {}
        self._sec_cache: dict = {}
        self._tok_cache: dict = {}

    def _tok(self, text):
        if text not in self._tok_cache:
            self._tok_cache[text] = tokens(text)
        return self._tok_cache[text]

    def set_alternates(self, alt_text: dict) -> None:
        """{member: [other names the workbook shows for it]} (AlternateText.xml). A member counts as named when its own name or any of
        these is."""
        self.alt = {m: [a for a in alts if any(self._tok(a))] for m, alts in (alt_text or {}).items()}

    def _names(self, member):
        """The member's own tokens, then those of each alternate text."""
        return [self._tok(member)] + [self._tok(a) for a in getattr(self, "alt", {}).get(member, [])]

    # -- labels around a cell ---------------------------------------------------------------------------------------
    def _is_text(self, sheet, row, col) -> str:
        v = self.wb.value(sheet, row, col)
        return v.strip() if isinstance(v, str) and v.strip() else ""

    def row_labels(self, sheet: str, row: int) -> list[str]:
        """Text that names the row: the text cells left of the row's first number (a row without numbers: its first column only,
        because the other texts of a header row are column headers)."""
        k = (sheet, row)
        if k not in self._row_cache:
            first_num = next((c for c in range(0, 40) if isinstance(self.wb.value(sheet, row, c), (int, float))
                              and not isinstance(self.wb.value(sheet, row, c), bool)), None)
            last = min(first_num if first_num is not None else 1, 4)
            self._row_cache[k] = [t for c in range(0, max(last, 1)) if (t := self._is_text(sheet, row, c))]
        return self._row_cache[k]

    def _has_numbers(self, sheet, row) -> bool:
        return any(isinstance(self.wb.value(sheet, row, c), (int, float)) and not isinstance(self.wb.value(sheet, row, c), bool)
                   for c in range(1, 40))

    def section_labels(self, sheet: str, row: int) -> list[str]:
        """The block the row sits in. Walking up: a run of rows without numbers is the section header (and the titles above it); a data row
        whose label has several lines ('Total Term Deposits' / 'Below Rs. 1 crore') opens a new block, and its first lines are the title.
        The nearest of these wins, so a block that starts mid-sheet does not inherit the header of the block above it."""
        k = (sheet, row)
        if k not in self._sec_cache:
            out, started = [], False
            own = [ln.strip() for t in self.row_labels(sheet, row) for ln in t.split(chr(10)) if ln.strip()]
            if len(own) > 1:                           # the row opens its own block: nothing above it applies
                self._sec_cache[k] = own[:-1]
                return self._sec_cache[k]
            for r in range(row - 1, max(0, row - MAX_UP), -1):
                if not self._has_numbers(sheet, r):
                    out += self.row_labels(sheet, r)
                    started = True
                    continue
                if started:
                    break
                lines = [ln.strip() for t in self.row_labels(sheet, r) for ln in t.split(chr(10)) if ln.strip()]
                if len(lines) > 1:
                    out += lines[:-1]
                    break
            self._sec_cache[k] = out
        return self._sec_cache[k]

    def col_labels(self, sheet: str, row: int, col: int) -> list[str]:
        """Header texts above the cell in its column. A header that spans columns (merged, or written once on the left) is carried
        right until the next header in the same row."""
        k = (sheet, row, col)
        if k not in self._head_cache:
            out = []
            for r in range(row - 1, max(0, row - MAX_UP), -1):
                t = self._is_text(sheet, r, col)
                if not t and not self._has_numbers(sheet, r):
                    for c in range(col - 1, max(-1, col - MAX_LEFT), -1):
                        if self.wb.value(sheet, r, c) is not None:
                            t = self._is_text(sheet, r, c)          # nearest non-empty cell on the left, if it is text
                            break
                if t:
                    out.append(t)
            self._head_cache[k] = out
        return self._head_cache[k]

    # -- scoring ----------------------------------------------------------------------------------------------------
    def set_vocabulary(self, members) -> None:
        """Every member name the error file uses. A cell whose labels spell out a member the fact's context does NOT have (a cell under
        'Rupee Term Deposits' for a context without RupeeTermDeposits) belongs to another entry."""
        self.vocab = [m for m in dict.fromkeys(members) if any(self._tok(m))]

    def score(self, sheet: str, row: int, col: int, members: list) -> tuple[int, list[str], int]:
        """(weighted score, members left unexplained, vocabulary members the row side spells out that the context lacks). A member the
        row or its block names counts 2, one only the column header names counts 1: column headers are shared by every block."""
        row_side = [self._tok(t) for t in self.row_labels(sheet, row) + self.section_labels(sheet, row)]
        col_side = [self._tok(t) for t in self.col_labels(sheet, row, col)]
        own = set(members)
        left, weighted = [], 0
        for m in members:
            mt = self._tok(m)
            if not (mt[0] or mt[1]):
                continue
            names = self._names(m)
            if any(_explains(n, lt) for n in names for lt in row_side):
                weighted += 2
            elif any(_explains(n, lt) for n in names for lt in col_side):
                weighted += 1
            else:
                left.append(m)
        conflicts = sum(1 for m in getattr(self, "vocab", []) if m not in own and any(_explains(n, lt) for n in self._names(m) for lt in row_side))
        mtoks = [self._tok(m) for m in members]
        for t in self.row_labels(sheet, row):            # a size band / period the row names and the context does not: another entry's row
            nt = self._tok(t)
            if nt[0] and set(nt[1]) & _MIN_NUMBER_UNITS and not any(_explains(mt, nt) for mt in mtoks):
                conflicts += 1
        return weighted, left, conflicts

    def best(self, fact, prefer_sheets=None):
        """-> (score, members, [(sheet,row,col,mult)] tied at the best score, runner-up score) or None."""
        members = sorted(fa.context_members(fact.context))
        members = [m for m in members if any(self._tok(m))]
        if not members:
            return None
        hs = self.vl.hits(fact.value, fact.decimal)
        zero = fa._dec(fact.value) is not None and fa._dec(fact.value) == 0
        if zero and prefer_sheets:                 # a zero holds no value evidence: only the labels decide, in sheets the filing already uses
            hs = [(sh, r, c, 1) for sh in prefer_sheets for r, c in self.wb.index(sh).get(0.0, [])]
        if not hs:
            return None
        if prefer_sheets:
            hs = [h for h in hs if h[0] in prefer_sheets] or hs
        scored = {}
        for sh, r, c, m in hs:
            weighted, left, conf = self.score(sh, r, c, members)
            scored.setdefault((sh, r, c), (weighted - 2 * conf, m, not left and not conf))
        ranked = sorted(scored.items(), key=lambda kv: -kv[1][0])
        top = ranked[0][1][0]
        if top < 1:
            return None
        tied = [(k[0], k[1], k[2], v[1]) for k, v in ranked if v[0] == top]
        full = all(v[2] for k, v in ranked if v[0] == top)
        if zero and not full:
            return None
        second = next((v[0] for k, v in ranked if v[0] < top), -1)
        return top, members, tied, second, full

    def _result(self, fact, top, members, cell, others, full, claimed_by_elimination=False):
        def addr(h):
            sh, r, c, m = h
            return fa.Address("", "", sh, r, c, "", m, self.wb.value(sh, r, c))
        a = addr(cell)
        a.label_ok = True
        why = ("row, section and column labels spell out every part of the context (" + ", ".join(members) + ")" if full else
               f"row, section and column labels spell out most of the context ({', '.join(members)})")
        if claimed_by_elimination:
            why += "; the other cells with this value belong to other entries of the same filing"
        return fa.Resolved("INFERRED" if full else "LIKELY", [a] + [addr(h) for h in others if h != cell][:3],
                           "located by the labels the context names: " + why)

    def resolve(self, fact, prefer_sheets=None, taken=frozenset()):
        """Same shape as fact_address.resolve_fact: Resolved | None. Only cells that hold the fact's value are candidates. The best cell must be
        alone at the top (cells other entries already hold are not counted), and either explain every member or beat the next by a margin."""
        b = self.best(fact, prefer_sheets)
        if b is None:
            return None
        top, members, tied, second, full = b
        tied = [h for h in tied if (h[0], h[1], h[2]) not in taken]
        if len(tied) != 1:
            return None
        if not (full or (top >= 2 and top - second >= 1)):
            return None
        return self._result(fact, top, members, tied[0], [], full, bool(taken))

    def contradicts(self, fact, sheet: str, row: int, col: int) -> bool:
        """Do the labels around this cell contradict the fact's context? True when a member of the context is spelled out nowhere around
        the cell (a rate filed for 'Up to 28 days' that sits under '29 days and upto 90 days' holds the same number by coincidence), or
        the row names a band / another category the context does not."""
        members = [m for m in sorted(fa.context_members(fact.context)) if any(self._tok(m))]
        if not members:
            return False
        _w, left, conflicts = self.score(sheet, row, col, members)
        return bool(left) or conflicts > 0

    def resolve_group(self, facts, taken=frozenset()):
        """Locate several facts of ONE failing instance together. Distinct entries cannot share a cell, so cells a fact with a unique best
        match holds are taken away from the facts that tie on them (the aggregate 'no Rupee / FC member' context gets the cell the
        Rupee-specific fact did not claim). -> {id(fact): Resolved}."""
        out, taken = {}, set(taken)
        pend = {id(f): f for f in facts}
        for _ in range(4):
            moved = False
            for fid, f in list(pend.items()):
                res = self.resolve(f, prefer_sheets={t[0] for t in taken}, taken=taken)
                if res is not None:
                    a = res.addresses[0]
                    out[fid] = res
                    taken.add((a.sheet, a.row, a.col))
                    del pend[fid]
                    moved = True
            if not moved:
                break
        return out
