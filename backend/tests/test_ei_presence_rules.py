"""Tests for presence rules ("must be reported"), percentage values and rules that the reported values already satisfy.
Built from small workbooks and fake facts: no return data."""
import os
import sys
from decimal import Decimal
from types import SimpleNamespace as NS

import openpyxl

from backend.error_improvement import explain_workbook as ew       # noqa: E402
from backend.error_improvement import fact_address as fa           # noqa: E402
from backend.error_improvement import presence_rules as pr         # noqa: E402
from backend.error_improvement import rule_cards as rc             # noqa: E402
from backend.error_improvement import value_locator as vl          # noqa: E402
from backend.error_improvement.workbook import Workbook       # noqa: E402

CONDITIONAL = ('(if ($V1 = "false") then (not(empty($V2))) else "false") and '
               '(if ($V1 = "true") then (empty($V2)) else "false")')


# ── the expression ────────────────────────────────────────────────────────────────────────────────────────────────
def test_a_required_value_is_found_from_the_expression_alone():
    assert pr.analyse("(not(empty( $V2 )))", {"V1": "true"}, ["V1", "V2"]) == {"required": ["V2"], "alternatives": [], "conditions": []}
    assert pr.analyse("not(empty($A))", {}, ["A"])["required"] == ["A"]
    assert pr.analyse("exists($A)", {}, ["A"])["required"] == ["A"]


def test_a_condition_names_the_value_that_would_lift_the_requirement():
    res = pr.analyse(CONDITIONAL, {"V1": "false"}, ["V1", "V2"])
    assert res == {"required": ["V2"], "alternatives": [("V1", "true")], "conditions": ["V1"]}
    assert pr.analyse(CONDITIONAL, {"V1": "true"}, ["V1", "V2"]) is None                   # that case holds: nothing to explain
    assert pr.analyse(CONDITIONAL, {"V1": "false", "V2": "4.3"}, ["V1", "V2"]) is None     # reported: nothing to explain


def test_only_what_it_can_prove_is_claimed():
    assert pr.analyse("empty($V1)", {"V1": "5"}, ["V1"]) is None            # a value that must be EMPTY is not a missing value
    assert pr.analyse("$V1 >= 0.1", {"V1": "0.05"}, ["V1"]) is None         # nothing absent: not a presence rule
    assert pr.analyse("sum($V1) = 3", {"V1": "1"}, ["V1"]) is None          # a form that is not understood is left alone
    assert pr.analyse("not(empty($V2)) and not(empty($V3))", {"V1": "1"}, ["V1", "V2", "V3"])["required"] == ["V2", "V3"]


def test_the_string_false_is_true_in_xpath_and_a_comparison_with_nothing_is_false():
    tree = pr.parse('if ($A = "x") then "a" else "false"')
    assert pr._ebv(pr._eval(tree, {})) is True
    assert pr._eval(pr.parse("$A = 1"), {}) is False and pr._eval(pr.parse("$A = 1"), {"A": "1.0"}) is True


# ── the cell where the missing value belongs ──────────────────────────────────────────────────────────────────────
def _sheet(tmp_path, tables):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "T"
    for header_row, rows in tables:
        ws.cell(header_row, 3, "X170")
        ws.cell(header_row, 4, "X180")
        for r, code, value in rows:
            ws.cell(r, 2, code)
            ws.cell(r, 3, value)
    p = tmp_path / "w.xlsx"
    wb.save(p)
    return Workbook(str(p))


def test_the_row_and_column_codes_meet_in_one_cell(tmp_path):
    wb = _sheet(tmp_path, [(5, [(7, "Y110", 4.3), (8, "Y120", 9)])])
    assert pr.grid_cell(wb, "T", "Y110_X170") == (7, 2)           # row 7, column C
    assert pr.grid_cell(wb, "T", "Y110_X999") is None             # a column code the sheet does not carry
    assert pr.grid_cell(wb, "T", "Y110") is None                  # a row code alone does not name a column


def test_repeated_tables_are_told_apart_by_the_row_the_mapping_expects(tmp_path):
    wb = _sheet(tmp_path, [(5, [(7, "Y110", 1)]), (15, [(17, "Y110", 2)])])
    assert pr.grid_cell(wb, "T", "Y110_X170") is None             # two equally good cells and no hint: not guessed
    assert pr.grid_cell(wb, "T", "Y110_X170", near_row=16) == (17, 2)


# ── percentages ───────────────────────────────────────────────────────────────────────────────────────────────────
def test_a_percentage_printed_by_the_validator_is_the_fraction_the_instance_holds():
    assert fa.plain_number("12.54%") == "0.1254" and fa._dec("12.54%") == Decimal("0.1254") and vl._dec("10.96%") == Decimal("0.1096")
    assert fa.plain_number("1,234") == "1,234" and fa._dec("1,234") == Decimal("1234")        # unchanged
    assert fa.plain_number("x%") == "x%" and fa._dec("x%") is None
    assert fa._dec("100%") == Decimal("1") and fa._dec("0%") == 0


# ── the cards ─────────────────────────────────────────────────────────────────────────────────────────────────────
def _card():
    return {"rule_name": "PartC_USDConversionRate_SQ", "cells": [], "evidence_key": "CONFIRMED"}


PRES = {"required": [{"var": "V2", "concept": "CurrencyConversionRate", "dims": {"ExchangeRateAxis": "USDToINRExchangeRateMember"},
                      "sheet": "FED02", "row": 37, "col": 2, "cell": "C37", "code": "Y110_X170", "workbook_value": "4.3456",
                      "how": "the sheet's own row and column codes"}],
        "conditions": [{"var": "V1", "concept": "WhetherNilReporting", "value": "false", "sheet": "FilingInfo", "cell": "B23"}],
        "alternatives": [{"var": "V1", "concept": "WhetherNilReporting", "value": "false", "sheet": "FilingInfo", "cell": "B23", "literal": "true"}]}


def test_a_missing_value_that_the_workbook_holds_says_it_did_not_reach_the_filing():
    v = rc._presence_view(_card(), PRES)
    assert v["wrong"] == ("Currency Conversion Rate (USD To INR Exchange Rate) must be reported because Whether Nil Reporting is false, "
                          "but the filing has no value for it.")
    assert "holds 4.3456 at FED02!C37" in v["why"] and "no value for it" in v["why"]
    assert any("Regenerate" in s for s in v["steps"]) and any("also satisfied when Whether Nil Reporting is true" in s for s in v["steps"])
    assert ("FED02!C37" in dict((k.split(" · ")[-1], t) for k, _v, t in v["kv"] if " · " in k)) or v["kv_cells"]


def test_a_missing_value_in_an_empty_cell_says_to_enter_it():
    pres = {**PRES, "required": [{**PRES["required"][0], "workbook_value": None}], "alternatives": []}
    v = rc._presence_view(_card(), pres)
    assert "is empty in the uploaded workbook" in v["why"] and v["steps"][0] == "Enter the value in FED02!C37."
    assert "because" not in v["wrong"]                           # no alternative value: the condition is not claimed as the reason


def test_a_requirement_with_no_cell_keeps_the_existing_explanation():
    assert rc._presence_named({"required": [{"var": "V2", "cell": None}]}) is False
    assert rc._presence_named(None) is False and rc._presence_named(PRES) is True


def _lc(value, a1, concept="PercentageOfExposure"):
    fact = NS(var="V1", concept=concept, value=value, unit="PURE", decimal="4", context="asof_20251231_GroupMember_X")
    addr = fa.Address("L", "L", "Table_3", int(a1[1:]), ord(a1[0]) - 65, "c", 1, 0.1254)
    return ew.Located(fact, fa.Resolved("CONFIRMED", [addr]))


def test_a_failing_rule_whose_values_all_meet_it_says_so():
    comp = NS(operator=">=")
    ev = {"passes": True, "lhs_value": "0.1254", "rhs_value": "0.1"}
    findings = [(None, {"V1": [_lc("12.54%", "E9")]}, ev), (None, {"V1": [_lc("10.96%", "E10")]}, {**ev, "lhs_value": "0.1096"})]
    assert rc._satisfied_cases(comp, findings) is findings
    v = rc._satisfied_view({"rule_name": "DBS13_Percent", "cells": []}, comp, findings)
    assert v["wrong"].startswith("All 2 reported values meet the rule as written (for example 12.54% is at least 10%)")
    assert [row[1] for row in v["kv"]] == ["12.54%", "10.96%", "must be at least 10%"] and "Table_3!E9" in v["kv_cells"]
    assert "not explained by the values" in v["why"]
    # one case that does fail, or a rule that is not an inequality: the existing card
    assert rc._satisfied_cases(comp, findings + [(None, {}, {**ev, "passes": False})]) is None
    assert rc._satisfied_cases(NS(operator="="), findings) is None
    assert rc._satisfied_cases(comp, [(None, {}, None)]) is None


def test_the_error_files_spelling_of_a_variable_name_does_not_matter(monkeypatch):
    """The report can print a variable as `"V1` (stray quote): the rule's own $V1 must still be the same variable."""
    fact = NS(var='"V1', concept="WhetherNilReporting", value="false", unit="", decimal="", context="fromto_20230902_20230908")
    located = {'"V1': [ew.Located(fact, fa.Resolved("CONFIRMED", [fa.Address("L", "L", "FilingInfo", 23, 1, "X010", 1, "false")]))]}
    meta = NS(formula_defs={"R": {"vars": {"V1": {"concepts": ["WhetherNilReporting"], "dims": {}},
                                           "V2": {"concepts": ["CurrencyConversionRate"], "dims": {"ExchangeRateAxis": ["USDToINRExchangeRateMember"]}}}}},
              reported=None)
    monkeypatch.setattr(pr, "place", lambda m, w, vd, base: {"sheet": "S", "row": 5, "col": 2, "cell": "C5", "code": "Y1_X1", "how": "test",
                                                             "workbook_value": 7, "concept": vd["concepts"][0]})
    out = ew._presence(NS(name="R"), CONDITIONAL, located, meta, NS(is_template=False))
    assert [r["var"] for r in out["required"]] == ["V2"] and out["required"][0]["cell"] == "C5" and out["required"][0]["workbook_value"] == "7"
    assert out["conditions"][0]["cell"] == "B23" and out["alternatives"][0]["literal"] == "true"
    # a rule whose definition is not in the return's metadata, or a template instead of a workbook, is left alone
    assert ew._presence(NS(name="other"), CONDITIONAL, located, meta, NS(is_template=False)) is None
    assert ew._presence(NS(name="R"), CONDITIONAL, located, meta, NS(is_template=True)) is None
    assert ew._presence(NS(name="R"), "$V1 >= 0.1", located, meta, NS(is_template=False)) is None
