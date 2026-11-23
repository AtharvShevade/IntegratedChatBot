"""Evaluate the Excel formulas of a template against the user's filed values, and explain a calculated cell.

A cell whose template formula is '=ROUND(IF(ROUND(A+B,2)=ROUND(C+D,2),C+D,0),2)' is not an input: typing into it is
overwritten. Its value is decided by other cells. Supported: + - * / ^ comparisons, ROUND, IF, SUM, ABS, MIN, MAX, AND, OR,
cell refs and ranges, other-sheet refs. Anything else (INDEX, whole columns, text functions) raises Unsupported and the
caller falls back to a plain statement.
"""
from __future__ import annotations

import re

from .workbook import col_to_index, index_to_col

_REF = re.compile(r"(?<![A-Za-z_\.\d])((?:'[^']+'|[A-Za-z_][\w\.]*)!)?\$?([A-Z]{1,3})\$?(\d+)(?::\$?([A-Z]{1,3})\$?(\d+))?(?![\w(])")


class Unsupported(Exception):
    pass


def _num(v):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else 0.0


def _flat(args):
    for a in args:
        if isinstance(a, list):
            yield from _flat(a)
        else:
            yield a


def _round(x, n=0):
    from decimal import ROUND_HALF_UP, Decimal
    return float(Decimal(str(x)).quantize(Decimal(1).scaleb(-int(n)), rounding=ROUND_HALF_UP))


FUNCS = {
    "ROUND": lambda x, n=0: _round(_num(x), n),
    "IF": lambda c, a=True, b=False: a if c else b,
    "SUM": lambda *a: sum(_num(x) for x in _flat(a)),
    "ABS": lambda x: abs(_num(x)),
    "MIN": lambda *a: min(_num(x) for x in _flat(a)),
    "MAX": lambda *a: max(_num(x) for x in _flat(a)),
    "AND": lambda *a: all(bool(x) for x in _flat(a)),
    "OR": lambda *a: any(bool(x) for x in _flat(a)),
}


def _to_python(formula: str, sheet: str) -> str:
    f = formula.lstrip("=")
    if re.search(r"\b(INDEX|OFFSET|INDIRECT|ROW|COLUMN|VLOOKUP|MATCH|TEXT|LEFT|RIGHT|MID|CONCATENATE)\s*\(|&|\"", f, re.I):
        raise Unsupported("function or operator not supported")

    def sub(m):
        sh = (m.group(1) or "")[:-1].strip("'") or sheet
        a = f"{m.group(2)}{m.group(3)}"
        if m.group(4):
            return f"_R({sh!r},{a!r},{m.group(4) + m.group(5)!r})"
        return f"_C({sh!r},{a!r})"

    f = _REF.sub(sub, f)
    f = re.sub(r"<>", "!=", f)
    f = re.sub(r"(?<![<>!=])=(?!=)", "==", f)
    return f.replace("^", "**")


def evaluate(formula: str, sheet: str, value) -> float:
    """value(sheet, row, col0) -> raw cell value (row 1-based, col 0-based)."""
    def cell(sh, a):
        m = re.match(r"([A-Z]+)(\d+)", a)
        return _num(value(sh, int(m.group(2)), col_to_index(m.group(1))))

    def rng(sh, a, b):
        m1, m2 = re.match(r"([A-Z]+)(\d+)", a), re.match(r"([A-Z]+)(\d+)", b)
        r1, r2 = sorted((int(m1.group(2)), int(m2.group(2))))
        c1, c2 = sorted((col_to_index(m1.group(1)), col_to_index(m2.group(1))))
        if (r2 - r1 + 1) * (c2 - c1 + 1) > 2000:
            raise Unsupported("range too large")
        return [value(sh, r, c) for r in range(r1, r2 + 1) for c in range(c1, c2 + 1)]

    ns = {"__builtins__": {}, "_C": cell, "_R": rng, **FUNCS}
    try:
        return eval(_to_python(formula, sheet), ns)          # noqa: S307 - restricted namespace, formula text from the template
    except Unsupported:
        raise
    except Exception as exc:                                 # noqa: BLE001
        raise Unsupported(str(exc)) from exc


def _split_top(s: str, sep: str) -> list[str]:
    out, depth, cur = [], 0, ""
    for ch in s:
        depth += ch == "("
        depth -= ch == ")"
        if ch == sep and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    return out + [cur]


def refs_of(expr: str, sheet: str) -> list[tuple[str, int, int]]:
    """Every cell an expression reads, as (sheet, row, col0), ranges expanded."""
    out = []
    for m in _REF.finditer(expr):
        sh = (m.group(1) or "")[:-1].strip("'") or sheet
        c1, r1 = col_to_index(m.group(2)), int(m.group(3))
        c2, r2 = (col_to_index(m.group(4)), int(m.group(5))) if m.group(4) else (c1, r1)
        out += [(sh, r, c) for r in range(min(r1, r2), max(r1, r2) + 1) for c in range(min(c1, c2), max(c1, c2) + 1)]
    return out


def explain_cell(formula: str, sheet: str, value) -> dict | None:
    """What a calculated cell does and why it shows its value.
    Returns {'kind': 'check'|'sum'|'calc', 'value': .., 'check_left': .., 'check_right': .., 'inputs': [(sheet,row,col,val)]}
    or None when the formula cannot be evaluated here."""
    f = formula.lstrip("=").replace(" ", "")
    try:
        total = evaluate(formula, sheet, value)
        m = re.fullmatch(r"ROUND\((.*),\d+\)", f, re.I)
        core = m.group(1) if m else f
        m = re.fullmatch(r"IF\((.*)\)", core, re.I)
        if m:
            args = _split_top(m.group(1), ",")
            if len(args) == 3:
                cond_sides = re.split(r"(?<![<>!=])=(?!=)", args[0])
                if len(cond_sides) == 2:
                    left = evaluate("=" + cond_sides[0], sheet, value)
                    right = evaluate("=" + cond_sides[1], sheet, value)
                    return {"kind": "check", "value": total, "check_left": left, "check_right": right,
                            "left_cells": refs_of(cond_sides[0], sheet), "right_cells": refs_of(cond_sides[1], sheet),
                            "then": evaluate("=" + args[1], sheet, value), "else": evaluate("=" + args[2], sheet, value)}
        cells = refs_of(core, sheet)
        return {"kind": "sum" if re.fullmatch(r"[\w\$!\.:'\+\-\(\) ]+", core) else "calc", "value": total, "inputs": cells}
    except Unsupported:
        return None
