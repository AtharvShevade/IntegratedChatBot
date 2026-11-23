"""The table titles a return's taxonomy gives its layouts.

`*-table-TableModel.xml` lists `<table label="ExternalBenchmark_Layout1" header="C1: Data on External Benchmark based Lending Rate"/>`:
the layout name the mapping uses and the title the return shows for it. The exact title, where the workbook's own text would only
be a guess.

    load(taxonomy_dir) -> {layout name: title}     (empty when the return carries no such file)
"""
from __future__ import annotations

import glob
import os
import re
from xml.sax.saxutils import unescape

_TABLE = re.compile(r"<table\b[^>]*?\blabel=\"([^\"]+)\"[^>]*?\bheader=\"([^\"]*)\"", re.S)
_ENTITIES = {"&quot;": '"', "&apos;": "'"}


def load(taxonomy_dir: str) -> dict[str, str]:
    out: dict[str, str] = {}
    try:
        paths = sorted(glob.glob(os.path.join(taxonomy_dir, "**", "*-table-TableModel.xml"), recursive=True))
    except OSError:
        return out
    for p in paths:                                  # a later version of the taxonomy replaces an earlier one
        try:
            text = open(p, encoding="utf-8-sig", errors="replace").read()
        except OSError:
            continue
        for label, header in _TABLE.findall(text):
            header = re.sub(r"\s+", " ", unescape(header, _ENTITIES)).strip()
            if header:
                out[label] = header
    return out


# ── which layout a cell lies in ───────────────────────────────────────────────────────────────────────────────────
_RANGE = re.compile(r"^\s*([A-Za-z]{1,3})(\d+):([A-Za-z]{1,3})(\d+)\s*$")
_CELL = re.compile(r"^([A-Za-z]{1,3})(\d+)$")


def layout_ranges(meta) -> list[tuple[str, str, int, int, int, int]]:
    """(layout name, sheet, first row, first col, last row, last col) for every range the return's query gives its layouts."""
    from .workbook import col_to_index
    out = []
    for lid, ranges in (getattr(meta, "sheets", None) or {}).items():
        name = (getattr(meta, "layouts", None) or {}).get(lid, "")
        for sheet, rng in ranges:
            m = _RANGE.match(rng or "")
            if name and m:
                out.append((name, sheet, int(m.group(2)), col_to_index(m.group(1)), int(m.group(4)), col_to_index(m.group(3))))
    return out


def layout_at(ranges, sheet: str, a1: str) -> str:
    """The one layout whose range holds this cell, or '' when none or several do (never a guess)."""
    from .workbook import col_to_index
    m = _CELL.match(a1 or "")
    if not m:
        return ""
    row, col = int(m.group(2)), col_to_index(m.group(1))
    names = {n for n, sh, r1, c1, r2, c2 in ranges if sh == sheet and r1 <= row <= r2 and c1 <= col <= c2}
    return next(iter(names)) if len(names) == 1 else ""
