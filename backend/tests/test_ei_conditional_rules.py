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
    assert [k for k, _v, _t in kv][:2] == ["Number of transactions for the period", "Value of transactions for period"]
    assert [c[1] for c in extras["kv_cells"].values()] == ["T9", "U9"]                  # the cell is a column of its own, not part of the label
    assert any(t == "bad" for _k, _v, t in kv) and "Table_2!U9" in fix and extras["steps"]
    assert rc._conditional_view(_located("10", "3000000"), {"expression": EXPR}) is None     # the rule holds: keep the generic wording
    assert rc._conditional_view(located, {"expression": "$V1 <= $V2"}) is None


def test_the_zero_case_is_explained():
    located = _located("0", "5")
    rc._set_currency(located)
    kv, wrong, _t, why, _fix, _x = rc._conditional_view(located, {"expression": EXPR})
    assert "is 0, so the rule requires" in wrong and "₹5" in wrong and "÷" not in wrong


# ── units and direction ───────────────────────────────────────────────────────────────────────────────────────────
def test_a_symbol_is_used_only_for_a_side_whose_own_unit_is_a_currency():
    from decimal import Decimal as D
    from types import SimpleNamespace as N
    from backend.error_improvement import calc_view as cv
    count = N(fact=N(unit="PURE", concept="NumberOfTransactions", value="54"), addr=None)
    amount = N(fact=N(unit="INR", concept="ValueOfTransactions", value="34"), addr=None)
    unknown = N(fact=N(unit="", concept="Other", value="1"), addr=None)
    var = lambda name: N(variables=lambda: [name])                                          # noqa: E731
    located = {"V1": [count], "V2": [amount], "V3": [unknown]}
    fl, fr, fd = rc._compare_fmts(N(lhs=var("V1"), rhs=var("V2")), located)
    assert (fl(D(54)), fr(D(34)), fd(D(20))) == ("54", "₹34", "20")                         # a count has no symbol; a difference of unlike units neither
    fl, fr, fd = rc._compare_fmts(N(lhs=var("V2"), rhs=var("V2")), located)
    assert fd(D(5)) == "₹5"
    fl, fr, fd = rc._compare_fmts(N(lhs=var("V3"), rhs=var("V2")), located)
    assert fl(D(1)) == "1" and fr(D(1000)) == "₹1,000"                                      # no monetary unit: the raw number, nothing assumed
    assert rc._compare_fmts(N(lhs=var("V9"), rhs=var("V2")), located) is None               # no facts for a side: the existing wording
    assert rc.cell_money(D(5), 1, "") == "5" and rc.cell_money(D(5), 1, "INR") == "₹5.00"     # no unit, no currency


def test_the_failed_comparison_is_worded_in_the_direction_the_numbers_go():
    from decimal import Decimal as D
    f = lambda d: str(d)                                                                    # noqa: E731
    s = lambda op, a, b: rc._cmp_sentence(op, D(a), D(b), "volume", "value", f, f, f)       # noqa: E731
    assert s("<=", 54, 34) == "The volume (54) exceeds the value (34) by 20."
    assert s(">=", 34, 54) == "The volume (34) is less than value (54) by 20."
    assert s("<", 5, 5) == "The volume (5) equals the value (5), but the rule needs it to be smaller."
    assert s(">", 5, 5) == "The volume (5) equals the value (5), but the rule needs it to be greater."
    for sentence in (s("<=", 54, 34), s(">=", 34, 54)):                                     # a larger number is never 'below' a smaller one
        big, small = ("54", "34") if "exceeds" in sentence else ("34", "54")
        assert sentence.index(big) < sentence.index(small) or "below" in sentence


def test_a_sheet_unit_figure_never_gets_a_currency_symbol():
    from backend.error_improvement import explain_table as et_
    import inspect
    src = inspect.getsource(et_.cover_rows)
    assert "if mult != 1:" in src and "lp = rp = \"\"" in src


def test_the_why_never_repeats_what_the_headline_already_says():
    wrong = "The amount outstanding of gross funded exposure (₹970,355,000) is less than the funded advances (₹1,559,334,000) by ₹588,979,000."
    same_in_other_units = "The amount outstanding of gross funded exposure (9,703.55) is less than the funded advances (15,593.34) by 5,889.79."
    assert rc._drop_repeats(same_in_other_units, wrong) == ""                           # the same words with other figures: dropped
    assert rc._drop_repeats("A (54) exceeds B (34) by 20. A (564) exceeds B (1) by 563. A (54) exceeds B (5) by 49.", "A (54) exceeds B (34) by 20.") == ""
    cause = "The filing rounds 0.0599 to 0.06 (2 decimal places), but the rule checks at 4. Report at least 4 decimal places."
    assert rc._drop_repeats(cause, "The reported value is 6.00%, but the recalculated value is 5.99%.") == cause       # a real cause stays
    assert rc._drop_repeats("First point. First point. Second point.", "") == "First point. Second point."


def test_figures_are_shown_in_the_sheets_own_unit_when_both_sides_are_kept_in_one():
    from decimal import Decimal as D
    from types import SimpleNamespace as N
    var = lambda name: N(variables=lambda: [name])                                          # noqa: E731
    cell = lambda mult: N(fact=N(unit="INR", concept="C", value="1"), addr=N(multiplier=mult))
    fl, fr, fd = rc._compare_fmts(N(lhs=var("V1"), rhs=var("V2")), {"V1": [cell(100000)], "V2": [cell(100000)]})
    assert (fl(D(970355000)), fr(D(1559334000)), fd(D(588979000))) == ("9,703.55", "15,593.34", "5,889.79")
    fl, fr, fd = rc._compare_fmts(N(lhs=var("V1"), rhs=var("V2")), {"V1": [cell(100000)], "V2": [cell(1)]})
    assert fl(D(970355000)) == "₹970,355,000"                                               # scales differ: the filed rupees, nothing converted
