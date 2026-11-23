"""Smoke tests that need no real return: address helpers and the equation solver."""
import os
import sys
from decimal import Decimal

from backend.error_improvement import explain_workbook as e                     # noqa: E402
from backend.error_improvement import fact_address as fa                        # noqa: E402


class _F:
    def __init__(self, v):
        self.value = v


class _L:
    def __init__(self, v):
        self.fact = _F(v)


def test_context_members_ignores_dates_and_tiebreaker():
    assert fa.context_members("asof_20260331_NBFCsMember_OOOOOOOO8") == {"NBFCsMember"}


def test_required_value_for_sum_rule():
    comp = e.fx.parse_formula("$V1 = $V2 + $V3 - $V4")
    loc = {"V1": [_L("10")], "V2": [_L("7")], "V3": [_L("5")], "V4": [_L("1")]}
    req = e.required_values(comp, loc)
    assert req["V1"] == (Decimal(10), Decimal(11))
    assert req["V4"] == (Decimal(1), Decimal(2))
