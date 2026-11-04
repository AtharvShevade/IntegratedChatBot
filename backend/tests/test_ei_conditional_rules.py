"""Tests for rules of the form "if A > 0 then B div A >= T, and if A = 0 then B = 0": built from small fake facts, no return data."""
import os
import sys
from decimal import Decimal
from types import SimpleNamespace as NS

from backend.error_improvement import conditional_rules as cond    # noqa: E402
from backend.error_improvement import explain_workbook as ew       # noqa: E402
from backend.error_improvement import fact_address as fa           # noqa: E402
from backend.error_improvement import rule_cards as rc             # noqa: E402
from backend.error_improvement import rule_findings as rfd         # noqa: E402

EXPR = "(if ($V1>0) then (($V2 div $V1) >= 200000) else 'FALSE') and (if ($V1=0) then ($V2=0) else 'FALSE')"


def _lc(var, concept, value, unit, a1, status="CONFIRMED"):
    fact = NS(var=var, concept=concept, value=value, unit=unit, decimal="0", context="fromto_20180901_20180930")
    addr = fa.Address("L", "L", "Table_2", int(a1[1:]), ord(a1[0]) - 65, "c", 1, value)
    return ew.Located(fact, fa.Resolved(status, [addr]))


def _located(count, amount):
    return {"V1": [_lc("V1", "NumberOfTransactionsForThePeriod", count, "PURE", "T9")],
            "V2": [_lc("V2", "ValueOfTransactionsForPeriod", amount, "INR", "U9")]}


def test_the_rule_is_read_for_what_it_says():
    spec = cond.parse(EXPR)
    assert spec == {"count": "V1", "amount": "V2", "op": ">=", "threshold": Decimal("200000"), "zero_rule": True}
    assert cond.parse("$V1 <= $V2") is None
    assert cond.parse(EXPR.replace("div $V1", "div $V3")) is None                        # the divisor must be the variable tested for > 0
    assert cond.parse(EXPR.split(" and ")[0])["zero_rule"] is False                       # a rule without the zero clause


def test_evaluation_against_the_per_unit_limit():
    spec = cond.parse(EXPR)
    r = cond.evaluate(spec, "351", "53")
    assert r["fails"] and r["required_amount"] == Decimal(70200000) and round(r["per_unit"], 3) == Decimal("0.151")
    assert not cond.evaluate(spec, "10", "3000000")["fails"]                               # 300,000 per unit: the rule holds
    z = cond.evaluate(spec, "0", "5")
    assert z["zero_case"] and z["fails"] and not cond.evaluate(spec, "0", "0")["fails"]
    assert cond.evaluate(spec, "x", "5") is None and cond.evaluate(spec, "-1", "5") is None


def _comp(operator=""):
    return NS(operator=operator, lhs=NS(signed_variables=lambda: [], variables=lambda: []))


def test_a_rule_without_a_left_side_is_named_by_any_verified_operand():
    located = _located("351", "53")
    assert rfd.decide(located, _comp(""), None, conditional=True) == (True, "")
    assert rfd.target(located, _comp(""), None, any_operand=True) is not None
    # any other rule without a left side (a mandatory-field check, say) is not given the card: the existing explanation says more
    assert rfd.decide(located, _comp(""), None)[0] is False
    # a comparison whose left side merely has no variables keeps the old answer
    assert rfd.decide(located, _comp("="), None, conditional=True)[0] is False
    # nothing placed: still no card
    unplaced = {"V1": [ew.Located(NS(var="V1", concept="C", value="1", unit="PURE", decimal="0", context="x"), fa.Resolved("UNRESOLVED", []))]}
    assert rfd.decide(unplaced, _comp(""), None, conditional=True)[0] is False


def test_card_wording_states_the_cells_the_ratio_and_the_value_that_would_pass():
    located = _located("351", "53")
    rc._set_currency(located)
    kv, wrong, terms, why, fix, extras = rc._conditional_view(located, {"expression": EXPR})
    assert "₹53 ÷ 351 is ₹0.151" in wrong and "at least ₹200,000" in wrong
    assert "at least ₹70,200,000" in why
    assert [k for k, _v, _t in kv][0].endswith("T9") and [k for k, _v, _t in kv][1].endswith("U9")
    assert any(t == "bad" for _k, _v, t in kv) and "Table_2!U9" in fix and extras["steps"]
    assert rc._conditional_view(_located("10", "3000000"), {"expression": EXPR}) is None     # the rule holds: keep the generic wording
    assert rc._conditional_view(located, {"expression": "$V1 <= $V2"}) is None


def test_the_zero_case_is_explained():
    located = _located("0", "5")
    rc._set_currency(located)
    kv, wrong, _t, why, _fix, _x = rc._conditional_view(located, {"expression": EXPR})
    assert "is 0, so the rule requires" in wrong and "₹5" in wrong and "÷" not in wrong
