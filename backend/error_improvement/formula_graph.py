"""The sum relations a template workbook already contains, read from its cell formulas.

The user's file is the template filled in, so '=K94+K95+...+K100' in the template says which cells feed that total.
Used to place an operand the filer never reported: it must be one of the cells the total is built from.
Only the template is read (a filed .xls has no readable formulas); references are same-sheet cells and ranges.
"""
from __future__ import annotations

import io
import re

from .workbook import col_to_index

_NUM_COPY = re.compile(r"\s*\(?(\d+)\)?\s*$")
_REF = re.compile(r"(?:(?:'([^']+)'|([A-Za-z_][\w\.\-]*))!)?\$?([A-Z]{1,3})\$?(\d+)(?::\$?([A-Z]{1,3})\$?(\d+))?")


class FormulaGraph:
    def __init__(self, path: str | None = None, resolve=None):
        self.path = path
        self._resolve = resolve                  # called on first use when the template path is not known yet
        self._loaded = False
        self._book = None
        self._pre: dict[str, dict] = {}
        self._post: dict[str, dict] = {}
        self._fcache: dict[str, dict] = {}
        self._xpost: dict | None = None

    @property
    def _wb(self):
        """The template is opened on first use only (streaming reader): most error files never need a formula."""
        if not self._loaded:
            self._loaded = True
            import openpyxl                                  # noqa: PLC0415
            if self.path is None and self._resolve:
                self.path = self._resolve()
            try:
                self._book = openpyxl.load_workbook(io.BytesIO(open(self.path, "rb").read()), data_only=False, read_only=True)
            except Exception:                                # noqa: BLE001 - a binary .xls has no formulas to read
                self._book = None
        return self._book

    def _template_sheet(self, sheet: str) -> str | None:
        """The template sheet that holds this sheet's formulas. A filed workbook repeats a sheet per entry ('CR-QCCP (1)', '(2)' ...)
        while the template keeps one: a numbered copy has the formulas of its un-numbered original."""
        names = self._wb.sheetnames if self._wb is not None else []
        if sheet in names:
            return sheet
        base = _NUM_COPY.sub("", sheet).strip()
        family = [n for n in names if _NUM_COPY.sub("", n).strip() == base]
        return next((n for n in family if n == base), family[0] if family else None)

    def _formulas(self, sheet: str) -> dict:
        """{(row, col0): formula text} for one sheet, read in a single pass and cached."""
        if sheet not in self._fcache:
            out = {}
            real = self._template_sheet(sheet) if self._wb is not None else None
            if real is not None:
                for row in self._wb[real].iter_rows():
                    for cell in row:
                        v = getattr(cell, "value", None)
                        if isinstance(v, str) and v.startswith("="):
                            out[(cell.row, cell.column - 1)] = v
            self._fcache[sheet] = out
        return self._fcache[sheet]

    def _build(self, sheet: str) -> None:
        pre, post = {}, {}
        if self._wb is not None and self._template_sheet(sheet) is not None:
            for (crow, ccol), v in self._formulas(sheet).items():
                if True:
                    refs = set()
                    for m in _REF.finditer(v):
                        other = m.group(1) or m.group(2)
                        if other and other != sheet:
                            continue                         # another sheet's cell: not a same-sheet relation
                        c1, r1 = col_to_index(m.group(3)), int(m.group(4))
                        c2, r2 = (col_to_index(m.group(5)), int(m.group(6))) if m.group(5) else (c1, r1)
                        if (r2 - r1 + 1) * (abs(c2 - c1) + 1) > 400:
                            continue
                        refs |= {(r, c) for r in range(min(r1, r2), max(r1, r2) + 1) for c in range(min(c1, c2), max(c1, c2) + 1)}
                    key = (crow, ccol)
                    refs.discard(key)
                    if refs:
                        pre[key] = refs
                        for r in refs:
                            post.setdefault(r, set()).add(key)
        self._pre[sheet], self._post[sheet] = pre, post

    def readable(self) -> bool:
        """False when the template's formulas could not be read at all (e.g. a binary .xls that was not converted)."""
        return self._wb is not None

    def formula(self, sheet: str, row: int, col: int) -> str | None:
        """The template's formula text for a cell (row 1-based, col 0-based), or None when it is a plain input."""
        return self._formulas(sheet).get((row, col))

    def signed_refs(self, sheet: str, row: int, col: int):
        """The cell's formula as an ordered list of (row, col, sign) when it is a plain signed sum of same-sheet cells
        (optionally wrapped in ROUND(...,n) or one pair of brackets); None for anything else (IF, ranges, other sheets)."""
        v = self._formulas(sheet).get((row, col))
        if not v:
            return None
        f = v[1:].replace(" ", "")
        m = re.fullmatch(r"ROUND\((.*),\d+\)", f, re.I)
        while m or (f.startswith("(") and f.endswith(")") and f[1:-1].count("(") == f[1:-1].count(")")):
            f = m.group(1) if m else f[1:-1]
            m = re.fullmatch(r"ROUND\((.*),\d+\)", f, re.I)
        if not re.fullmatch(r"[+-]?(\$?[A-Z]{1,3}\$?\d+)([+-]\$?[A-Z]{1,3}\$?\d+)*", f):
            return None
        out = []
        for sign, ref in re.findall(r"([+-]?)(\$?[A-Z]{1,3}\$?\d+)", f):
            m2 = re.match(r"\$?([A-Z]{1,3})\$?(\d+)", ref)
            out.append((int(m2.group(2)), col_to_index(m2.group(1)), -1 if sign == "-" else 1))
        return out

    def _cross_index(self) -> dict:
        """{(sheet, row, col0): {formula cells that read it}} over EVERY sheet, cross-sheet references included. Built once, on demand:
        a total that sums one cell per entry sheet ('=SUM(S (1)!D15 + S (2)!D15 + ...)') is only visible this way."""
        if self._xpost is None:
            post: dict = {}
            if self._wb is not None:
                for sh in self._wb.sheetnames:
                    for (crow, ccol), v in self._formulas(sh).items():
                        for m in _REF.finditer(v):
                            target = m.group(1) or m.group(2) or sh
                            if target not in self._wb.sheetnames:
                                continue
                            c1, r1 = col_to_index(m.group(3)), int(m.group(4))
                            c2, r2 = (col_to_index(m.group(5)), int(m.group(6))) if m.group(5) else (c1, r1)
                            if (r2 - r1 + 1) * (abs(c2 - c1) + 1) > 400:
                                continue
                            for r in range(min(r1, r2), max(r1, r2) + 1):
                                for c in range(min(c1, c2), max(c1, c2) + 1):
                                    if (target, r, c) != (sh, crow, ccol):
                                        post.setdefault((target, r, c), set()).add((sh, crow, ccol))
            self._xpost = post
        return self._xpost

    def cross_dependents(self, sheet: str, row: int, col: int) -> set:
        """Formula cells (sheet, row, col0), on any sheet, whose formula reads this cell. A numbered copy of a sheet is looked up
        under its template sheet's name."""
        real = self._template_sheet(sheet) if self._wb is not None else None
        return self._cross_index().get((real or sheet, row, col), set())

    def precedents(self, sheet: str, row: int, col: int) -> set:
        if sheet not in self._pre:
            self._build(sheet)
        return self._pre[sheet].get((row, col), set())

    def dependents(self, sheet: str, row: int, col: int) -> set:
        if sheet not in self._post:
            self._build(sheet)
        return self._post[sheet].get((row, col), set())
