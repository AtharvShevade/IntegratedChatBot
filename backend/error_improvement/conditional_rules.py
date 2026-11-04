"""Rules of the form  "if A > 0 then B div A <op> T else FALSE  and  if A = 0 then B = 0 else FALSE"  (a per-unit minimum or maximum:
value per transaction, average per account, ...).

The rule has no left and right side to subtract, so the engine could not say how far off it was, nor name a cell. Here it is read
for what it says: with A units, B must stay on the right side of T per unit, and with no units B must be 0. Nothing is specific to one
return: the operands are the rule's own variables, the threshold is the number the rule carries.

    parse(expression)          -> {"count": "V1", "amount": "V2", "op": ">=", "threshold": Decimal, "zero_rule": True} or None
    evaluate(spec, count, amount) -> what the two filed numbers do against the rule, or None when they are not numbers
"""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

_IF = re.compile(
    r"if\s*\(\s*\$(\w+)\s*>\s*0\s*\)\s*then\s*\(\s*\(\s*\$(\w+)\s+div\s+\$(\w+)\s*\)\s*(>=|<=|>|<)\s*([0-9][0-9.,]*)\s*\)\s*else\s*'FALSE'",
    re.I)
_ZERO = re.compile(r"if\s*\(\s*\$(\w+)\s*=\s*0\s*\)\s*then\s*\(\s*\$(\w+)\s*=\s*0\s*\)\s*else\s*'FALSE'", re.I)

WORD = {">=": "at least", ">": "more than", "<=": "at most", "<": "less than"}


def parse(expression: str | None) -> dict | None:
    m = _IF.search(expression or "")
    if not m or m.group(1).upper() != m.group(3).upper():       # "$A > 0" and "div $A" must be the same variable
        return None
    try:
        threshold = Decimal(m.group(5).replace(",", ""))
    except InvalidOperation:
        return None
    z = _ZERO.search(expression)
    return {"count": m.group(1).upper(), "amount": m.group(2).upper(), "op": m.group(4), "threshold": threshold,
            "zero_rule": bool(z and z.group(1).upper() == m.group(1).upper() and z.group(2).upper() == m.group(2).upper())}


def _dec(v):
    try:
        return Decimal(str(v).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        return None


def _holds(value: Decimal, op: str, threshold: Decimal) -> bool:
    return {">=": value >= threshold, ">": value > threshold, "<=": value <= threshold, "<": value < threshold}[op]


def evaluate(spec: dict, count, amount) -> dict | None:
    """-> {"count", "amount", "per_unit", "required_amount", "fails", "zero_case"}; None when a number is missing."""
    n, v = _dec(count), _dec(amount)
    if n is None or v is None or n < 0:
        return None
    t, op = spec["threshold"], spec["op"]
    if n > 0:
        per = v / n
        return {"count": n, "amount": v, "per_unit": per, "required_amount": t * n, "fails": not _holds(per, op, t), "zero_case": False}
    return {"count": n, "amount": v, "per_unit": None, "required_amount": Decimal(0), "fails": bool(spec["zero_rule"] and v != 0),
            "zero_case": True}
