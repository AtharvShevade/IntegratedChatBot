"""An equality rule that fails only because a value is stored with more decimals than it shows must say so, never 'X but X'."""
from decimal import Decimal as D
from types import SimpleNamespace as NS

from backend.error_improvement import rule_cards as rc


def _fmt(d):
    return f"{D(d):.2f}"


def test_float_noise_is_called_a_precision_gap():
    g = rc._precision_gap(NS(operator="="), {"left": D("0.009999999999999787"), "right": D("0.01")}, _fmt)
    assert g and "look the same" in g["wrong"] and "0.0000000000000002" in g["gap"]
    assert "ROUND" in g["steps"][0]


def test_same_when_shown_is_a_precision_gap_for_any_equality_rule():
    assert rc._precision_gap(NS(operator="="), {"left": D("10.004"), "right": D("10.001")}, _fmt)


def test_real_differences_and_inequalities_are_untouched():
    assert rc._precision_gap(NS(operator="="), {"left": D("10"), "right": D("12")}, _fmt) is None
    assert rc._precision_gap(NS(operator=">="), {"left": D("0.00999999999999979"), "right": D("0.01")}, _fmt) is None
    assert rc._precision_gap(NS(operator="="), {"left": D("5"), "right": D("5")}, _fmt) is None
