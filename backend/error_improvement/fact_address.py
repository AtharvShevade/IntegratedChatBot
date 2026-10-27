"""From one failing fact (concept + context id + reported value) to its cell in the user's workbook.

Uses ONLY the return's metadata folder (PreLnkBases / Mapping_N / XML_Query), the fact itself, and - to
CONFIRM the answer - the workbook:

    1. context id        -> dimension members named in it             (asof_20260331_GrossAdvancesMember)
    2. concept + members -> Mapping_N rows that hold it               (cell "r~c" inside a layout)
    3. layout            -> sheet and range                           (XML_Query.xml: [Sheet$B7:AF20])
    4. "r~c" + range     -> Excel address                             (row = first row + r - 1, column = first column + c)
    5. workbook value x template multiplier  must equal the fact's reported value - that is the check that
       the address is right. A fact is CONFIRMED only when it does; otherwise the candidates are listed as
       UNCONFIRMED and nothing is claimed.

Nothing is specific to one return. The address rule in (4) was verified against this return's own values.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from . import cell_locator as cl
from .workbook import Workbook, index_to_col, split_range

_DATE = re.compile(r"^\d{8}$")
_UNIQUE_SUFFIX = re.compile(r"^O+\d*$")      # 'OOOOOOOO8': the generator's tie-breaker for duplicate contexts


def context_members(ctx_id: str) -> set[str]:
    """The member names a context id spells out. 'asof_20260331_NBFCsMember_OOOOOOOO8' -> {'NBFCsMember'}."""
    out = set()
    for tok in (ctx_id or "").split("_"):
        if not tok or tok in ("asof", "fromto") or _DATE.match(tok) or _UNIQUE_SUFFIX.match(tok):
            continue
        out.add(tok)
    return out


def _alnum(x) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", str(x or ""))


def _dec(v) -> Decimal | None:
    try:
        return Decimal(str(v).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        return None


@dataclass
class Address:
    layout_id: str
    layout_name: str
    sheet: str
    row: int
    col: int                       # 0-based
    cell_code: str
    multiplier: int
    workbook_value: object = None
    label_ok: object = None        # True when the row's label in the sheet equals the mapping row's label

    @property
    def a1(self) -> str:
        return f"{index_to_col(self.col)}{self.row}"

    @property
    def scaled(self) -> Decimal | None:
        d = _dec(self.workbook_value)
        return d * self.multiplier if d is not None else None


@dataclass
class Resolved:
    status: str                    # CONFIRMED | UNCONFIRMED | UNRESOLVED
    addresses: list[Address]       # CONFIRMED: the matching ones; UNCONFIRMED: all candidates
    note: str = ""


_TRAIL = re.compile(r"\s*\(?(\d+)\)?\s*$")
_NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
                 "ten": 10, "eleven": 11, "twelve": 12}


def number_hints(members) -> set[int]:
    """Entry numbers a context names. A member ending in a number word ('QCCPTwo' -> 2) names the entry; bare digit
    tokens ('1') are only used when no member does, because they are often an item number."""
    words, digits = set(), set()
    for m in members:
        if m.isdigit():
            digits.add(int(m))
            continue
        low = m.lower()
        for w in sorted(_NUMBER_WORDS, key=len, reverse=True):      # 'QCCPTwo' ends in 'two'; 'ten' before 'one' etc.
            if low.endswith(w) and low != w:
                words.add(_NUMBER_WORDS[w])
                break
    return words or digits


def sheet_family(wb, sheet: str) -> list[str]:
    """The sheet plus its numbered copies ('X (1)', 'X (2)' ... or 'X3'): same name once the trailing number is removed."""
    base = _TRAIL.sub("", sheet).strip()
    fam = [sh for sh in wb.sheets if _TRAIL.sub("", sh).strip() == base]
    return fam or [sheet]


def _pick_sheets(wb, sheet: str, hints: set[int]) -> list[str]:
    fam = sheet_family(wb, sheet)
    if len(fam) > 1 and hints:
        hit = [sh for sh in fam if (_TRAIL.search(sh) and int(_TRAIL.search(sh).group(1)) in hints)]
        if hit:
            return hit
    return [sheet]


def _norm_label(t) -> str:
    return re.sub(r"\s+", " ", str(t or "")).strip().lower()


def _row_by_label(meta: cl.FormMeta, wb: Workbook, layout_id: str, code: str, sheet: str, rng: str, col: int, guess: int):
    """The sheet row whose first-column text is this mapping row's label (Staging CodeDescription minus its
    '_SUFFIX'). Mapping 'r~c' indexes can skip rows, so arithmetic alone may land on a neighbour row."""
    desc = meta.staging.get((layout_id, code), "")
    suffixes = [c[0] for c in meta.columns.get(layout_id, []) if c[2] == sheet]
    label = ""
    for sfx in sorted(suffixes, key=len, reverse=True):
        if sfx and desc.endswith(sfx):
            label = desc[: -len(sfx)]
            break
    if not label.strip():
        return None
    first_row, first_col = split_range(rng)
    last_row = int(re.search(r"(\d+)$", rng).group(1))
    want = _norm_label(label)
    hits = [r for r in range(first_row, last_row + 1) if _norm_label(wb.value(sheet, r, first_col)) == want]
    if not hits:
        return None
    return min(hits, key=lambda r: abs(r - guess))


def candidates(meta: cl.FormMeta, wb: Workbook, concept: str, ctx_id: str, members: set | None = None) -> list[Address]:
    members = set(members) if members is not None else context_members(ctx_id)
    out: list[Address] = []
    seen = set()
    members_n = {_alnum(m) for m in members}                # context ids drop punctuation the mapping keeps ('Rs.2Lakh')
    for r in meta.rows_by_concept.get(cl.local(concept), []):
        row_members = {_alnum(m) for _, m in r.explicit}
        if not row_members <= members_n:
            continue
        unexplained = members_n - row_members
        m = re.match(r"(\d+)~(\d+)$", r.cell or "")
        if not m:
            continue
        rr, cc = int(m.group(1)), int(m.group(2))
        for base_sheet, rng in meta.sheets.get(r.layout_id, []):
          if not wb.has_sheet(base_sheet):
              continue
          for sheet in _pick_sheets(wb, base_sheet, number_hints(members)):
            first_row, first_col = split_range(rng)
            dr, dc = getattr(meta, "offsets", {}).get(r.layout_id, (0, 0))
            guess = first_row + rr - 1 + dr
            rows = [guess]
            by_label = _row_by_label(meta, wb, r.layout_id, r.code, sheet, rng, first_col, guess)
            if by_label is not None and by_label != guess:
                rows = [by_label, guess]       # label-matched row first, arithmetic row as fallback
            for row in rows:
                label_ok = None if by_label is None else (row == by_label)
                key = (r.layout_id, sheet, row, first_col + cc + dc, r.code)
                if key in seen:
                    continue
                seen.add(key)
                a = Address(r.layout_id, meta.layouts.get(r.layout_id, ""), sheet, row, first_col + cc + dc,
                            r.code, r.multiplier)
                a.label_ok = label_ok
                a.workbook_value = wb.value(sheet, a.row, a.col)
                out.append((len(unexplained), a))
    out.sort(key=lambda t: (t[0], t[1].layout_id))
    return [a for _, a in out]


def value_matches(a: "Address", value: str) -> bool:
    """Does the workbook cell hold this fact's value? Numbers compare after the template multiplier, text as text."""
    target = _dec(value)
    cell = a.workbook_value
    if target is None:
        return isinstance(cell, str) and cell.strip().lower() == str(value).strip().lower() and bool(str(value).strip())
    scaled = a.scaled
    if scaled is not None and abs(scaled - target) <= max(Decimal("0.5"), abs(target) * Decimal("1e-9")):
        return True
    return target == 0 and cell in (None, "", 0, 0.0)


def calibrate(meta: cl.FormMeta, wb: Workbook, facts) -> dict:
    """Per layout, find the (row, column) shift of the mapping's r~c that makes the most fact values land on
    cells holding them. Ranges and indexes are not read the same way by every return, so the shift is learned
    from the file's own facts instead of assumed. facts = [(concept, context id, value)]."""
    meta.offsets = {}
    score: dict[str, dict[tuple, int]] = {}
    saved = {}
    shifts = [(dr, dc) for dc in range(-3, 4) for dr in range(-2, 3)]
    for concept, ctx, value in facts:
        if _dec(value) is not None and _dec(value) == 0:
            continue                                         # zeros match any empty cell: no evidence
        members = context_members(ctx)
        for r in meta.rows_by_concept.get(cl.local(concept), []):
            if not {_alnum(m) for _, m in r.explicit} <= {_alnum(x) for x in members}:
                continue
            m = re.match(r"(\d+)~(\d+)$", r.cell or "")
            if not m:
                continue
            rr, cc = int(m.group(1)), int(m.group(2))
            for sheet, rng in meta.sheets.get(r.layout_id, []):
                if not wb.has_sheet(sheet):
                    continue
                fr, fc = split_range(rng)
                for dr, dc in shifts:
                    a = Address(r.layout_id, "", sheet, fr + rr - 1 + dr, fc + cc + dc, r.code, r.multiplier)
                    if a.row < 1 or a.col < 0:
                        continue
                    a.workbook_value = wb.value(sheet, a.row, a.col)
                    if a.workbook_value is not None and value_matches(a, value):
                        score.setdefault(r.layout_id, {}).setdefault((dr, dc), 0)
                        score[r.layout_id][(dr, dc)] += 1
    for lid, sc in score.items():
        best, n = max(sc.items(), key=lambda kv: (kv[1], -(abs(kv[0][0]) + abs(kv[0][1]))))
        if n >= 3 and n > sc.get((0, 0), 0):
            meta.offsets[lid] = best
    return meta.offsets


def scan_for(wb: Workbook, cands: list, value: str):
    """Fallback when the mapped cells do not hold the value: sheets built per entry (extra rows, numbered copies of a
    sheet) put the fact somewhere the template row does not point to. Search the candidate sheets and their copies
    for the value; the column the mapping predicts breaks ties. Zero / empty facts carry no evidence and are skipped."""
    target = _dec(value)
    if target is not None and target == 0:
        return []
    names = {a.sheet for a in cands}
    fam = {sh for n in names for sh in sheet_family(wb, n)}
    sheets = [sh for sh in wb.sheets if sh in names or sh in fam or any(sh.startswith(n) for n in names)]
    cols = {a.col for a in cands}
    mults = {a.multiplier or 1 for a in cands}
    hits = []
    for sh in sheets:
        idx = wb.index(sh)
        if target is None:
            keys = [str(value).strip().lower()]
            mults_ = {1}
        else:
            keys, mults_ = [], mults
        for m in mults_:
            k = str(value).strip().lower() if target is None else round(float(target / m), 4)
            for (r, c) in idx.get(k, []):
                src = next((a for a in cands if (a.multiplier or 1) == m), cands[0])
                hits.append(Address(src.layout_id, src.layout_name, sh, r, c, src.cell_code, m, wb.value(sh, r, c)))
    on_col = [h for h in hits if h.col in cols]
    return on_col or hits


def resolve_fact(meta: cl.FormMeta, wb: Workbook, concept: str, ctx_id: str, value: str) -> Resolved:
    cands = candidates(meta, wb, concept, ctx_id)
    if not cands:
        return Resolved("UNRESOLVED", [], "no mapping row carries this concept with these members")
    target = _dec(value)
    if getattr(wb, "is_template", False):
        # No filled workbook: the template only supplies row labels. The fact's own value is the cell's value,
        # so the answer rests on the mapping alone and is reported as MAPPED, never as confirmed.
        pick = [a for a in cands if a.label_ok] or cands
        top = pick[0]
        for a in pick:
            if target is not None and a.multiplier:
                a.workbook_value = float(target / a.multiplier)
        return Resolved("MAPPED", pick[:6], "" if len(pick) == 1 else f"{len(pick)} candidate cells; best by mapping rank first")
    confirmed = [a for a in cands if value_matches(a, value)]
    if not confirmed:
        found = scan_for(wb, cands, value)
        if found and len({(h.sheet, h.row, h.col) for h in found}) <= 3:
            return Resolved("CONFIRMED", found, "located by value search (the sheet has rows the template does not)")
    if confirmed:
        # an exact-zero fact can match many empty candidates; prefer those whose layout explains every member
        return Resolved("CONFIRMED", confirmed, "" if len(confirmed) == 1 else f"{len(confirmed)} cells hold this value")
    return Resolved("UNCONFIRMED", cands, "the workbook value does not equal the reported value at any candidate cell")
