"""Where a cell sits on its sheet: the table it belongs to and the column headers above it, top to bottom.

Read from the workbook's own text, nothing about a return is assumed:
  * column: the header rows stacked above the cell, read in the cell's own column from the top heading down to the one nearest the
    cell ('Using Mobile App > Volume > X380'). A heading merged across several columns counts for every column it covers. A header row
    is a row of several text cells and no numbers; the rows of data between it and the cell are skipped.
  * table name: above that header band, the nearest row holding a single text cell (a title line).
Either is left empty when the sheet does not make it clear: nothing is guessed.

    describe(wb, sheet, a1) -> {"table": str, "column": str}
"""
from __future__ import annotations

import re

from .workbook import col_to_index

_A1 = re.compile(r"^([A-Za-z]{1,3})(\d{1,6})$")
_REACH = 60                      # rows looked at above the cell
_WIDTH = 60                      # columns read per row
_DEPTH = 6                       # header rows read at most
_PART = 100                      # longest heading shown whole
_MAX = 110                       # longest table title shown
_PATH_MAX = 170                  # longest column path shown


def _text(v) -> str:
    return re.sub(r"\s+", " ", v).strip() if isinstance(v, str) else ""


def _short(s: str, n: int = _MAX) -> str:
    return s if len(s) <= n else s[:n - 1].rstrip() + "…"


def _row(wb, sheet: str, r: int, merges: list) -> tuple[dict, int]:
    """({col: heading text} for the text the row shows in each column, merged headings included; how many cells hold numbers)."""
    texts, numbers = {}, 0
    for c in range(_WIDTH):
        v = wb.value(sheet, r, c)
        if isinstance(v, bool) or v is None:
            continue
        if isinstance(v, (int, float)):
            numbers += 1
        elif _text(v):
            texts[c] = _text(v)
    for r1, c1, r2, c2 in merges:
        if r1 <= r <= r2:
            top = _text(wb.value(sheet, r1, c1))
            if top:
                for c in range(c1, min(c2, _WIDTH - 1) + 1):
                    texts.setdefault(c, top)                      # the heading covers every column of its merge, not only the first
    return texts, numbers


def _distinct(texts: dict) -> int:
    return len(set(texts.values()))


_UNIT_NOTE = re.compile(r"^\(.{1,30}\)$")                            # '(Rs. Lakh)' beside a title


def _title_row(texts: dict, merges: list, r: int) -> str:
    """The title a row carries, or ''. A title row is one heading that runs across the sheet (a heading merged over three or more
    columns from the first columns on), alone or with a unit note such as '(Rs. Lakh)'; a single text cell is a title too."""
    if not texts:
        return ""
    first = min(texts)
    lead = texts[first]
    if _distinct(texts) == 1:
        return lead
    rest = [t for c, t in texts.items() if t != lead]
    wide = any(r1 <= r <= r2 and c1 <= 1 and c2 - c1 >= 2 for r1, c1, r2, c2 in merges)
    if (wide or len(lead) >= 25) and rest and all(_UNIT_NOTE.match(t) for t in rest):
        return lead
    return ""


def describe(wb, sheet: str, a1: str) -> dict:
    m = _A1.match((a1 or "").strip())
    out = {"table": "", "column": ""}
    if not m or not sheet or not wb.has_sheet(sheet):
        return out
    col, row = col_to_index(m.group(1)), int(m.group(2))
    try:
        merges = wb.merged(sheet)
    except Exception:                                              # noqa: BLE001  a workbook that cannot say has no merged headings
        merges = []
    band: list[str] = []                                           # headings, nearest the cell first
    band_top, gap = None, 0
    r = row - 1
    while r >= 1 and row - r <= _REACH:
        texts, numbers = _row(wb, sheet, r, merges)
        title = _title_row(texts, merges, r) if numbers == 0 else ""
        key_value = set(texts) == {0, 1} and _distinct(texts) == 2               # 'label | value' pairs are a form, not a header row
        header_like = numbers == 0 and _distinct(texts) >= 2 and not title and not key_value
        if band_top is None:
            if header_like and col in texts:
                band, band_top = [texts[col]], r                   # the header row nearest the cell; rows of data above the cell are skipped
        elif header_like:
            if col in texts:
                band.append(texts[col])
            band_top, gap = r, 0
            if len(band) >= _DEPTH:
                break
        elif not texts and numbers == 0 and gap < 2:
            gap += 1                                               # a blank row between two stacked header rows does not end the band
        else:
            break                                                  # the stacked header rows end where something else begins (a title line, data)
        r -= 1
    path: list[str] = []
    for part in reversed(band):                                    # top heading first
        if not path or path[-1] != part:
            path.append(part)
    if path:
        out["column"] = _short(" > ".join(_short(p, _PART) for p in path), _PATH_MAX)
        for r in range(band_top - 1, max(band_top - _REACH, 0), -1):
            texts, numbers = _row(wb, sheet, r, merges)
            title = _title_row(texts, merges, r) if numbers == 0 else ""
            if len(title) >= 4:
                out["table"] = _short(title)
                break
    return out
