"""Presence rules: "this value must be reported" / "if A is 'false' then B must be reported".

The validator only says that a required value is missing. The rule's own expression says which one: it is read here, evaluated
against what the filing does carry, and probed (which missing value, once reported, makes the rule hold; which other value of a
condition would also make it hold). The rule's definition (concept + dimensions) and the return's mapping then say where the
missing value belongs in the workbook, and the workbook says what that cell holds.

Nothing here knows a return, a sheet or a rule name: the expression, the definition and the mapping are all read.

    analyse(expr, present, variables)   -> {"required": [vars], "alternatives": [(var, literal)], "conditions": [vars]} or None
    grid_cell(wb, sheet, code, near_row) -> (row, col) from the sheet's own row and column codes, or None
    place(meta, wb, var_def, base_members) -> {"sheet", "row", "col", "cell", "code", "how", "workbook_value"} or None
"""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from . import fact_address as fa
from .workbook import index_to_col

_TOKEN = re.compile(r"""\s*(?:
    (?P<var>\$\w+)
  | (?P<str>"[^"]*"|'[^']*')
  | (?P<num>\d+(?:\.\d+)?)
  | (?P<op><=|>=|!=|=|<|>)
  | (?P<punct>[(),])
  | (?P<name>[A-Za-z_][\w\-]*)
)""", re.X)


class _Parse(Exception):
    pass


def _tokens(text: str) -> list[tuple[str, str]]:
    out, pos = [], 0
    text = text.strip()
    while pos < len(text):
        m = _TOKEN.match(text, pos)
        if not m or m.end() == pos:
            raise _Parse(text[pos:pos + 12])
        pos = m.end()
        kind = m.lastgroup
        out.append((kind, m.group(kind)))
    return out


class _Parser:
    def __init__(self, toks):
        self.t, self.i = toks, 0

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else (None, None)

    def take(self, kind=None, val=None):
        k, v = self.peek()
        if k is None or (kind and k != kind) or (val and v.lower() != val):
            raise _Parse(f"expected {val or kind}, got {v}")
        self.i += 1
        return v

    def _is(self, val):
        k, v = self.peek()
        return k == "name" and v.lower() == val

    def expr(self):
        node = self.and_()
        while self._is("or"):
            self.take()
            node = ("or", node, self.and_())
        return node

    def and_(self):
        node = self.cmp()
        while self._is("and"):
            self.take()
            node = ("and", node, self.cmp())
        return node

    def cmp(self):
        left = self.primary()
        k, v = self.peek()
        if k == "op":
            self.take()
            return ("cmp", v, left, self.primary())
        return left

    def primary(self):
        k, v = self.peek()
        if k == "punct" and v == "(":
            self.take()
            node = self.expr()
            self.take("punct", ")")
            return node
        if k == "var":
            self.take()
            return ("var", v[1:].upper())
        if k == "str":
            self.take()
            return ("str", v[1:-1])
        if k == "num":
            self.take()
            return ("num", Decimal(v))
        if k == "name":
            low = v.lower()
            if low == "if":
                self.take()
                self.take("punct", "(")
                cond = self.expr()
                self.take("punct", ")")
                self.take("name", "then")
                then = self.expr()
                self.take("name", "else")
                return ("if", cond, then, self.expr())
            self.take()
            self.take("punct", "(")
            args = []
            if self.peek() != ("punct", ")"):
                args.append(self.expr())
                while self.peek() == ("punct", ","):
                    self.take()
                    args.append(self.expr())
            self.take("punct", ")")
            return ("call", low, args)
        raise _Parse(f"unexpected {v}")


def parse(expr: str):
    """The expression as a tree, or None when it is not one of the forms understood here."""
    try:
        p = _Parser(_tokens(expr))
        node = p.expr()
        return node if p.i == len(p.t) else None
    except (_Parse, InvalidOperation):
        return None


def _ebv(v) -> bool:
    """XPath effective boolean value: an empty sequence is false, a non-empty string is true (including the string "false")."""
    if v is None:
        return False
    if isinstance(v, bool):
        return v
    if isinstance(v, Decimal):
        return v != 0
    return len(str(v)) > 0


def _num(v):
    try:
        return Decimal(str(v).strip())
    except (InvalidOperation, ValueError):
        return None


def _eval(node, env: dict):
    kind = node[0]
    if kind == "var":
        v = env.get(node[1])
        return None if v in (None, "") else v
    if kind == "str":
        return node[1]
    if kind == "num":
        return node[1]
    if kind == "if":
        return _eval(node[2], env) if _ebv(_eval(node[1], env)) else _eval(node[3], env)
    if kind == "and":
        return _ebv(_eval(node[1], env)) and _ebv(_eval(node[2], env))
    if kind == "or":
        return _ebv(_eval(node[1], env)) or _ebv(_eval(node[2], env))
    if kind == "cmp":
        a, b = _eval(node[2], env), _eval(node[3], env)
        if a is None or b is None:
            return False                                      # a comparison with an empty sequence is false
        na, nb = _num(a), _num(b)
        if na is not None and nb is not None:
            a, b = na, nb
        else:
            a, b = str(a), str(b)
        return {"=": a == b, "!=": a != b, "<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}[node[1]]
    if kind == "call":
        name, args = node[1], node[2]
        if name == "empty":
            return not _ebv(_eval(args[0], env)) if args else True
        if name == "exists":
            return _ebv(_eval(args[0], env)) if args else False
        if name == "not":
            return not _ebv(_eval(args[0], env))
        if name == "true":
            return True
        if name == "false":
            return False
    raise _Parse(f"cannot evaluate {kind}")


def _vars(node, acc: set | None = None) -> set:
    acc = set() if acc is None else acc
    if node[0] == "var":
        acc.add(node[1])
    for child in node[1:]:
        if isinstance(child, tuple):
            _vars(child, acc)
        elif isinstance(child, list):
            for c in child:
                _vars(c, acc)
    return acc


def _compared_literals(node, acc: dict | None = None) -> dict:
    """{var: {literals it is compared with}}: the values a condition can take."""
    acc = {} if acc is None else acc
    if node[0] == "cmp" and node[1] in ("=", "!="):
        a, b = node[2], node[3]
        for x, y in ((a, b), (b, a)):
            if x[0] == "var" and y[0] in ("str", "num"):
                acc.setdefault(x[1], set()).add(str(y[1]))
    for child in node[1:]:
        if isinstance(child, tuple):
            _compared_literals(child, acc)
        elif isinstance(child, list):
            for c in child:
                _compared_literals(c, acc)
    return acc


def analyse(expr: str, present: dict, variables) -> dict | None:
    """present: {var: reported value} for the variables the filing carries. variables: every variable the rule defines.
    None unless the expression fails on this data and reporting some missing value would make it hold."""
    tree = parse(expr)
    if tree is None:
        return None
    env = {v.upper(): val for v, val in present.items()}
    try:
        if _ebv(_eval(tree, env)):
            return None                                       # the rule holds on this data: nothing to explain
        used = _vars(tree)
        absent = sorted(v for v in (x.upper() for x in variables) if v in used and v not in env)
        required = [v for v in absent if _ebv(_eval(tree, {**env, v: "x"}))]
        if not required and absent and _ebv(_eval(tree, {**env, **{v: "x" for v in absent}})):
            required = absent
        if not required:
            return None
        alternatives = []
        for var, lits in _compared_literals(tree).items():
            if var in env:
                for lit in sorted(lits - {str(env[var])}):
                    if _ebv(_eval(tree, {**env, var: lit})):
                        alternatives.append((var, lit))
        conditions = sorted(v for v in _compared_vars(tree) if v in env)
        return {"required": required, "alternatives": alternatives, "conditions": conditions}
    except (_Parse, KeyError):
        return None


def _compared_vars(node, acc: set | None = None) -> set:
    acc = set() if acc is None else acc
    if node[0] == "cmp":
        for side in node[2:4]:
            if side[0] == "var":
                acc.add(side[1])
    for child in node[1:]:
        if isinstance(child, tuple):
            _compared_vars(child, acc)
        elif isinstance(child, list):
            for c in child:
                _compared_vars(c, acc)
    return acc


# ── where the missing value belongs ───────────────────────────────────────────────────────────────────────────────
def grid_cell(wb, sheet: str, code: str, near_row: int | None = None):
    """Sheets that label their rows and columns with codes ('Y110' down the side, 'X170' across the top) name a cell by the two:
    the mapping's cell code 'Y110_X170' is the cell where that row and that column meet. (row, col) or None when the sheet does
    not carry both codes unambiguously."""
    parts = (code or "").split("_")
    if len(parts) != 2 or not all(parts):
        return None
    try:
        idx = wb.index(sheet)
    except Exception:                                          # noqa: BLE001
        return None
    rows = [(r, c) for r, c in idx.get(parts[0].lower(), []) if c <= 3]
    heads = idx.get(parts[1].lower(), [])
    found = set()
    for rr, _rc in rows:
        above = [(cr, cc) for cr, cc in heads if cr < rr]
        if above:
            found.add((rr, max(above)[1]))                    # the nearest column header above the row
    if len(found) > 1 and near_row is not None:
        closest = min(abs(r - near_row) for r, _c in found)
        found = {rc for rc in found if abs(rc[0] - near_row) == closest}
    return next(iter(found)) if len(found) == 1 else None


def place(meta, wb, var_def: dict, base_members=()) -> dict | None:
    """The cell where a value the filing does not carry belongs: concept and pinned dimensions from the rule's definition, the
    mapping for the layout and cell code, and the sheet's own row and column codes for the exact cell. None when it is not
    unambiguous."""
    concepts = var_def.get("concepts") or []
    if len(concepts) != 1:
        return None
    members = set(base_members) | {ms[0] for ms in (var_def.get("dims") or {}).values() if len(ms) == 1}
    cands = fa.candidates(meta, wb, concepts[0], "", members=members)
    if not cands:
        return None
    verified = {}
    for a in cands:
        cell = grid_cell(wb, a.sheet, a.cell_code, a.row)
        if cell is not None:
            verified[(a.sheet, cell[0], cell[1])] = a
    if len(verified) == 1:
        (sheet, row, col), a = next(iter(verified.items()))
        how = "the sheet's own row and column codes"
    elif len(verified) > 1:
        return None
    else:
        # The mapping counts columns from the code column: it lands on the cell that holds the row's own code, and the value is
        # in the next column. Only taken when the cell really holds that code.
        beside = {(a.sheet, a.row, a.col + 1): a for a in cands
                  if str(wb.value(a.sheet, a.row, a.col) or "").strip().lower() == str(a.cell_code).strip().lower()}
        uniq = {(a.sheet, a.row, a.col): a for a in cands if a.label_ok}
        if len(beside) == 1 and not uniq:
            (sheet, row, col), a = next(iter(beside.items()))
            how = "the mapping: the cell next to the row's code"
        elif len(uniq) == 1:
            (sheet, row, col), a = next(iter(uniq.items()))
            how = "the return's mapping and the row label"
        else:
            return None
    return {"sheet": sheet, "row": row, "col": col, "cell": f"{index_to_col(col)}{row}", "code": a.cell_code, "how": how,
            "workbook_value": wb.value(sheet, row, col), "concept": concepts[0]}
