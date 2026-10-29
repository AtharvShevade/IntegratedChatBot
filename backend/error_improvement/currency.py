"""The currency of a return's amounts, read from the unit of the facts in the error file (never assumed).

An XBRL monetary fact carries its unit ('INR', 'QAR', ...). A rule's amounts are in one currency when every monetary fact of the
rule has the same unit. Ratios and counts ('pure', 'shares', empty) are not amounts and are ignored.

    of_facts(facts)  -> 'QAR' | None        (None: no monetary unit, or the units disagree)
    prefix(code)     -> '₹' | 'QAR ' | ''   (what goes before a number; '' for an unknown currency)
"""
from __future__ import annotations

import re

SYMBOLS = {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥"}
_NOT_MONEY = {"", "PURE", "SHARES", "NONE", "INF", "COUNT", "NUMBER", "PERCENT"}
_CODE = re.compile(r"^[A-Z]{3}$")


def normalise(unit: str | None) -> str:
    """'iso4217:QAR' / 'u_qar' / ' QAR ' -> 'QAR'; anything that is not a three-letter code -> ''."""
    u = (unit or "").strip().upper().split(":")[-1]
    u = re.sub(r"^U[_-]", "", u)
    return u if _CODE.match(u) and u not in _NOT_MONEY else ""


def of_facts(facts) -> str | None:
    codes = {normalise(getattr(f, "unit", "")) for f in facts}
    codes.discard("")
    return next(iter(codes)) if len(codes) == 1 else None


def prefix(code: str | None) -> str:
    if not code:
        return ""
    return SYMBOLS.get(code, code + " ")
