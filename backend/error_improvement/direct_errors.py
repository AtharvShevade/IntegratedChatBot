"""Explain error files that already name a sheet and a column (<Error Sheet= ColumnName= ReportedValue= ExpectedValue= Description=>).

There is no rule to evaluate here, so the work is: group the errors, find the exact cell in the user's workbook, and say
what is wrong from the SHAPE of each error:
    expected value given            -> a total does not match: reported vs expected, difference
    reported empty                  -> a required entry is blank
    reported given, no expected     -> a value is not accepted (the description says why)
The column is found by matching ColumnName with the header text of the sheet; the row by looking for the entry's key
(the 'Name:value' at the end of the description) in the sheet. Nothing is specific to one return.
"""
from __future__ import annotations

import collections
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from .workbook import Workbook, index_to_col

_KEY = re.compile(r"(\w+):([^\s:,]+)\s*$")


def _norm(s) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower())


@dataclass
class DirectError:
    no: str
    sheet: str
    column: str
    reported: str
    expected: str
    description: str

    @property
    def key(self) -> tuple[str, str] | None:
        m = _KEY.search(self.description)
        return (m.group(1), m.group(2)) if m else None

    @property
    def kind(self) -> str:
        d = _KEY.sub("", self.description).strip(" ,:\x01")
        d = re.sub(r"\s*Field:-\w+,?\s*$", "", d).strip(" ,:")
        return d or self.description


def is_direct_error_file(path: str) -> bool:
    try:
        with open(path, encoding="utf-8-sig", errors="ignore") as fh:
            head = fh.read(4000)
    except OSError:
        return False
    return "<Error " in head and "Sheet=" in head and "ColumnName=" in head


def parse(path: str) -> list[DirectError]:
    root = ET.parse(path).getroot()
    return [DirectError(e.get("ErrorNo", ""), e.get("Sheet", ""), e.get("ColumnName", ""), e.get("ReportedValue", ""),
                        e.get("ExpectedValue", ""), e.get("Description", "")) for e in root.iter("Error")]


def _sheet(wb: Workbook, name: str) -> str | None:
    want = _norm(name)
    for sh in wb.sheets:
        if _norm(sh) == want:
            return sh
    for sh in wb.sheets:
        if want and (_norm(sh).startswith(want) or want.startswith(_norm(sh))):
            return sh
    return None


def _column(wb: Workbook, sheet: str, column: str, scan_rows: int = 40) -> int | None:
    want = _norm(column)
    if not want:
        return None
    for r in range(1, scan_rows + 1):
        for c in range(0, 60):
            v = wb.value(sheet, r, c)
            if isinstance(v, str) and _norm(v) == want:
                return c
    for r in range(1, scan_rows + 1):                 # header text may carry extra words ('PAN (Permanent ...)')
        for c in range(0, 60):
            v = wb.value(sheet, r, c)
            if isinstance(v, str) and want in _norm(v) and len(_norm(v)) <= len(want) + 40:
                return c
    return None


def _row(wb: Workbook, sheet: str, key: tuple[str, str] | None) -> int | None:
    if not key:
        return None
    hits = wb.index(sheet).get(key[1].strip().lower(), [])
    return hits[0][0] if hits else None


def ranges(cells: list[str]) -> str:
    """['G9','G10','G11','H9'] -> 'G9:G11, H9' (consecutive rows of one column collapse)."""
    by_col: dict[str, list[int]] = collections.OrderedDict()
    for c in cells:
        m = re.match(r"([A-Z]+)(\d+)$", c)
        if m:
            by_col.setdefault(m.group(1), []).append(int(m.group(2)))
    out = []
    for col, rows in by_col.items():
        rows = sorted(set(rows))
        start = prev = rows[0]
        for r in rows[1:] + [None]:
            if r is not None and r == prev + 1:
                prev = r
                continue
            out.append(f"{col}{start}" if start == prev else f"{col}{start}:{col}{prev}")
            if r is not None:
                start = prev = r
    return ", ".join(out)


def _dec(v):
    try:
        return Decimal(str(v).replace(",", ""))
    except (InvalidOperation, ValueError):
        return None


def explain(errors: list[DirectError], wb: Workbook | None, Row):
    groups: dict[tuple, list[DirectError]] = collections.OrderedDict()
    for e in errors:
        groups.setdefault((e.sheet, e.column, e.kind), []).append(e)
    rows, located = [], 0
    for (sheet, column, kind), items in groups.items():
        real = _sheet(wb, sheet) if wb else None
        col = _column(wb, real, column) if real else None
        cells, missing_row = [], 0
        for e in items:
            r = _row(wb, real, e.key) if real else None
            if r is None and real and col is not None and not e.key and _dec(e.reported) is not None:
                # no entry key (a column total): the reported number itself, in this column, is the cell
                hits = [h for h in wb.index(real).get(round(float(_dec(e.reported)), 4), []) if h[1] == col]
                r = hits[0][0] if len(hits) == 1 else None
            if r is None or col is None:
                missing_row += 1
            else:
                cells.append(f"{index_to_col(col)}{r}")
        located += len(cells)
        where = f"{real or sheet} -> " + (ranges(cells) if cells else f"column {column}")
        if col is not None and not cells:
            where = f"{real} -> column {index_to_col(col)} (row not found)"
        if missing_row and cells:
            where += f" (+{missing_row} not found)"
        first = items[0]
        if first.expected:
            rep, exp = _dec(first.reported), _dec(first.expected)
            diff = f", difference {rep - exp:,.2f}" if rep is not None and exp is not None else ""
            sol = (f"Reported **{first.reported}** but the entries add up to **{first.expected}**{diff}. "
                   "Correct the column total or the entries above it.")
            tag = "total does not match"
        elif not first.reported:
            keys = ", ".join(dict.fromkeys(f"{e.key[0]} {e.key[1]}" for e in items if e.key))[:160]
            sol = f"Fill the empty {column} for the entries listed" + (f" ({keys})" if keys else "") + "."
            tag = "required entry blank"
        else:
            vals = ", ".join(dict.fromkeys(e.reported for e in items))[:120]
            sol = (f"The value(s) entered ({vals}) are not accepted: {kind}. Replace them with an accepted value "
                   "or correct the related master data.")
            tag = "value not accepted"
        rows.append(Row("DATA", f"{kind} - {column} ({len(items)} case(s), {tag})", where, sol,
                        {"kind": tag, "sheet": sheet, "column": column, "cases": len(items)}))
    return rows, located
