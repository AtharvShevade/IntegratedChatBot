"""Where a cell sits on its sheet: the table it belongs to and the column header above it.

Read from the workbook's own text, nothing about a return is assumed:
  * column header: the nearest row above the cell that looks like a header band (several text cells, no numbers) and has text in the
    cell's own column. A descriptive header is preferred to a bare code ('X170') when one sits just above it.
  * table name: above that header band, the nearest row holding a single text cell (a title line).
Either is left empty when the sheet does not make it clear: nothing is guessed.

    describe(wb, sheet, a1) -> {"table": str, "column": str}
"""
from __future__ import annotations

import re

from .workbook import col_to_index

_A1 = re.compile(r"^([A-Za-z]{1,3})(\d{1,6})$")
_CODE = re.compile(r"^[A-Za-z]{1,2}\d{2,4}(?:[_.]\w+)?$")
_REACH = 60                      # rows looked at above the cell
_WIDTH = 40                      # columns read per row
_MAX = 110                      # longest text shown


def _text(v) -> str:
    return re.sub(r"\s+", " ", v).strip() if isinstance(v, str) else ""


def _row(wb, sheet: str, r: int) -> tuple[dict, int]:
    """{col: text} for the text cells of a row and how many number cells it holds."""
    texts, numbers = {}, 0
    for c in range(_WIDTH):
        v = wb.value(sheet, r, c)
        if isinstance(v, bool) or v is None:
            continue
        if isinstance(v, (int, float)):
            numbers += 1
        elif _text(v):
            texts[c] = _text(v)
    return texts, numbers


def _short(s: str) -> str:
    return s if len(s) <= _MAX else s[:_MAX - 1].rstrip() + "…"


def describe(wb, sheet: str, a1: str) -> dict:
    m = _A1.match((a1 or "").strip())
    out = {"table": "", "column": ""}
    if not m or not sheet or not wb.has_sheet(sheet):
        return out
    col, row = col_to_index(m.group(1)), int(m.group(2))
    column, header_row, bare = "", None, None
    for r in range(row - 1, max(row - _REACH, 0), -1):
        texts, numbers = _row(wb, sheet, r)
        if len(texts) >= 2 and numbers == 0 and col in texts:
            if _CODE.match(texts[col]):
                bare = bare or (r, texts[col])                 # a code row: keep looking for words just above it
                if header_row is None:
                    header_row = r
                continue
            column, header_row = texts[col], (header_row or r)
            break
        if bare and r < bare[0] - 3:
            break
    column = column or (bare[1] if bare else "")
    if header_row is None:
        header_row = row
    for r in range(header_row - 1, max(header_row - _REACH, 0), -1):
        texts, numbers = _row(wb, sheet, r)
        if len(texts) == 1 and numbers == 0:
            title = next(iter(texts.values()))
            if len(title) >= 4:
                out["table"] = _short(title)
                break
    out["column"] = _short(column)
    return out
