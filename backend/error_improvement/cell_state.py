"""What a cell really is in the filer's workbook: a formula, a typed input, or a template formula that was typed over.

The template says which cells are calculated. The filer's own workbook says which of them still are. A cell the template
calculates but the filer typed a number into is an 'overwritten formula': the typed number no longer follows its inputs, which is
a very common reason for a total that does not add up. A cell is called calculated only when the uploaded workbook holds a formula.

    state(wb, sheet, row, col0) -> {state, formula, template_formula, inspected}
      state:  'formula'           the uploaded workbook holds a formula
              'overwritten'       the template has a formula here, the uploaded workbook holds a typed value
              'blank_formula'     the template has a formula here, the uploaded workbook has nothing
              'input'             no formula in either
              'template_formula'  the template has a formula; the uploaded workbook's formulas cannot be inspected
                                  (a legacy .xls, or no filed workbook): only the template is known
              'unknown'           nothing is known (no template formula, uploaded formulas not inspectable)
      inspected: True when the uploaded workbook's own formulas were read.
"""
from __future__ import annotations

import os

from .formula_graph import FormulaGraph


def upload_graph(path: str | None) -> FormulaGraph | None:
    """The uploaded workbook's own formulas (openpyxl, data_only=False). None for a file that cannot hold readable formulas
    (a legacy binary .xls), so the caller says 'from the template' instead of claiming the upload has the formula."""
    if not path or not os.path.isfile(path):
        return None
    try:
        with open(path, "rb") as fh:
            if fh.read(2) != b"PK":
                return None
    except OSError:
        return None
    return FormulaGraph(path=path)


def state(wb, sheet: str, row: int, col0: int) -> dict:
    tpl = getattr(wb, "formulas", None)
    tf = tpl.formula(sheet, row, col0) if tpl is not None and tpl.readable() else None
    up = getattr(wb, "upload_formulas", None)
    if getattr(wb, "is_template", False) or up is None or not up.readable():
        return {"state": "template_formula" if tf else "unknown", "formula": None, "template_formula": tf, "inspected": False}
    uf = up.formula(sheet, row, col0)
    if uf:
        return {"state": "formula", "formula": uf, "template_formula": tf, "inspected": True}
    value = wb.value(sheet, row, col0)
    if tf:
        return {"state": "overwritten" if value not in (None, "") else "blank_formula", "formula": None, "template_formula": tf,
                "inspected": True}
    return {"state": "input", "formula": None, "template_formula": None, "inspected": True}
