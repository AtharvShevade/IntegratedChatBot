"""Tests for the per-rule decision (full card or existing explanation plus findings): built from small fake facts, no return data."""
import importlib.util
import os
import sys
from decimal import Decimal
from types import SimpleNamespace as NS

from backend.error_improvement import explain_workbook as ew       # noqa: E402
from backend.error_improvement import fact_address as fa           # noqa: E402
from backend.error_improvement import rule_findings as rfd         # noqa: E402

try:                                                    # inside the chatbot the adapter is a package module
    from backend.error_improvement import adapter       # noqa: E402
except ImportError:                                     # standalone: it lives in integration/
    _spec = importlib.util.spec_from_file_location("ei_adapter", os.path.join(os.path.dirname(os.path.abspath(__file__)), "integration", "adapter.py"))
    adapter = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(adapter)


def _addr(a1="C5", value=1, sheet="S", multiplier=1):
    col = ord(a1[0]) - 65
    return fa.Address("L", "L", sheet, int(a1[1:]), col, "c", multiplier, value)


def _lc(var, status, addr=None, value="10", concept="Amount", decimal="2", candidates=None):
    fact = NS(var=var, concept=concept, value=value, decimal=decimal, context="fromto_20250101_20250331")
    res = fa.Resolved(status, [addr] if addr is not None else (candidates or []))
    return ew.Located(fact, res)


def _comp(*lhs):
    return NS(lhs=NS(signed_variables=lambda: [(v, 1) for v in lhs], variables=lambda: list(lhs)))


def test_full_card_when_the_reported_side_is_placed_with_good_evidence():
    located = {"V1": [_lc("V1", "INFERRED", _addr("C5", 10))], "V2": [_lc("V2", "CONFIRMED", _addr("B7", 10))]}
    assert rfd.decide(located, _comp("V1"), None) == (True, "")


def test_no_full_card_when_the_reported_cell_is_not_placed():
    located = {"V1": [_lc("V1", "UNCONFIRMED")], "V2": [_lc("V2", "CONFIRMED", _addr("B7", 10))]}
    full, why = rfd.decide(located, _comp("V1"), None)
    assert not full and "no cell" in why


def test_a_variable_spelled_with_a_stray_quote_is_still_the_rules_variable():
    located = {'"V1': [_lc("V1", "INFERRED", _addr("C5", 10))]}
    assert rfd.decide(located, _comp("V1"), None) == (True, "")


def test_a_cell_from_the_return_mapping_alone_is_good_enough_when_there_is_no_upload():
    located = {"V1": [_lc("V1", "MAPPED", _addr("C5", None))]}
    assert rfd.decide(located, _comp("V1"), None)[0] is True


def test_a_likely_cell_is_not_good_enough_to_name():
    located = {"V1": [_lc("V1", "LIKELY", _addr("C5", 10))]}
    assert rfd.decide(located, _comp("V1"), None)[0] is False


def test_a_proven_culprit_is_a_target_even_when_the_reported_cell_is_unplaced():
    located = {"V1": [_lc("V1", "UNCONFIRMED")], "V2": [_lc("V2", "CONFIRMED", _addr("B7", 10))]}
    assert rfd.decide(located, _comp("V1"), ("S", "B7"))[0] is True


def test_no_full_card_when_most_values_could_not_be_placed(monkeypatch):
    located = {"V1": [_lc("V1", "INFERRED", _addr("C5", 10))],
               "V2": [_lc("V2", "UNCONFIRMED"), _lc("V2", "UNCONFIRMED"), _lc("V2", "UNCONFIRMED")]}
    full, why = rfd.decide(located, _comp("V1"), None)
    assert not full and "25%" in why
    monkeypatch.setenv("ERROR_IMPROVEMENT_MIN_COVERAGE", "0.2")
    assert rfd.decide(located, _comp("V1"), None)[0] is True


def test_values_the_filing_does_not_carry_are_not_counted_against_coverage():
    located = {"V1": [_lc("V1", "INFERRED", _addr("C5", 10))], "V2": [_lc("V2", "UNRESOLVED", concept="")]}
    assert rfd.coverage(located) == 1.0


class _Book:
    """A workbook that holds the numbers in `has` somewhere (what ew._value_known looks up)."""
    is_template = False
    path = "upload.xlsx"

    def __init__(self, has=()):
        self._cache = {}
        self.sheets = ["S"]
        self._has = {round(float(v), 4) for v in has}

    def index(self, sheet):
        return self._has


def test_findings_say_which_cell_holds_another_value_than_the_filing():
    held = _addr("E59", 0, sheet="LR-Part C")                  # the cell the mapping points to holds 0
    located = {"V1": [_lc("V1", "UNCONFIRMED", value="-495956792000", candidates=[held])]}
    out = rfd.findings(located, _Book(), _comp("V1"), None, 4)
    assert any("LR-Part C!E59" in f and "holds 0 " in f and "reports -495,956,792,000" in f for f in out)
    assert any("may not be the file that was filed" in f for f in out)


def test_findings_say_when_a_filed_value_is_not_in_the_workbook():
    located = {"V1": [_lc("V1", "UNRESOLVED", value="12345")]}
    out = rfd.findings(located, _Book(), _comp("V1"), None, 4)
    assert any("12,345 is not anywhere in the uploaded workbook" in f for f in out)


def test_numbers_read_plainly_and_a_ratio_is_not_shown_as_money():
    assert rfd._plain("-495956792000.00") == "-495,956,792,000"
    assert rfd._plain("0.0300") == "0.03" and rfd._plain(Decimal("7772036.52")) == "7,772,036.52" and rfd._plain("n/a") == "n/a"


def test_the_rules_own_term_names_the_item_and_long_names_are_cut():
    from backend.error_improvement import rule_cards as rc
    lc = _lc("V1", "UNRESOLVED", value="12345")
    assert rfd._name(rc, lc, {"V1": "Net outflows"}) == "Net outflows"
    assert len(rfd._name(rc, lc, {"V1": "x" * 200})) == 90


def test_no_claim_when_the_template_is_the_only_workbook():
    book = _Book()
    book.is_template = True
    located = {"V1": [_lc("V1", "UNRESOLVED", value="12345")]}
    assert rfd.findings(located, book, _comp("V1"), None, 4) == []


def test_a_zero_or_matching_value_is_never_called_a_mismatch():
    same = _addr("E59", 10, sheet="S")
    located = {"V1": [_lc("V1", "UNCONFIRMED", value="10", candidates=[same])],
               "V2": [_lc("V2", "UNCONFIRMED", value="0", candidates=[_addr("E60", 5)])]}
    assert rfd.findings(located, _Book(has=[10]), _comp("V1"), None, 4) == []


def test_where_the_other_values_sit_is_shown_only_next_to_a_real_finding():
    placed = _lc("V2", "CONFIRMED", _addr("M10", Decimal("177756252.11")), concept="Denominator")
    alone = {"V1": [_lc("V1", "UNCONFIRMED")], "V2": [placed]}
    assert rfd.findings(alone, _Book(has=[10]), _comp("V1"), None, 4) == []
    held = _addr("E59", 0, sheet="LR-Part C")
    with_mismatch = {"V1": [_lc("V1", "UNCONFIRMED", value="-495956792000", candidates=[held])], "V2": [placed]}
    out = rfd.findings(with_mismatch, _Book(has=[10]), _comp("V1"), None, 4)
    assert any("S!M10" in f and "177,756,252.11" in f for f in out)


def test_a_cell_value_is_given_in_the_units_of_the_filing():
    lakhs = _addr("C13", Decimal("-10.12"), multiplier=100000)
    assert rfd._plain(rfd._held(lakhs)) == "-1,012,000"


def test_a_long_name_is_cut_at_the_bracket_not_inside_it():
    from backend.error_improvement import rule_cards as rc
    lc = _lc("V1", "UNRESOLVED", value="1")
    long = "Aggregate Financial Assets Acquired (" + "Financial Assets Acquired And Resolved " * 4 + ")"
    assert rfd._name(rc, lc, {"V1": long}) == "Aggregate Financial Assets Acquired"


def test_attach_adds_one_headed_list_and_leaves_the_explanation_alone():
    item = {"explanation": "Old text.", "explanation_sections": [{"kind": "headline", "text": "x"}], "rule_name": "R"}
    out = adapter.attach_findings(item, ["a", "b"])
    assert out["explanation_sections"][0] == {"kind": "headline", "text": "x"}
    assert out["explanation_sections"][-1] == {"kind": "fix", "heading": adapter.FINDINGS_HEADING, "steps": ["a", "b"]}
    assert out["explanation"].startswith("Old text.") and out["explanation"].endswith("  - a\n  - b")
    assert item["explanation"] == "Old text." and len(item["explanation_sections"]) == 1      # the input is not modified
    assert adapter.attach_findings(item, []) is item


def test_switches(monkeypatch):
    assert adapter.gate_enabled()
    monkeypatch.setenv("ERROR_IMPROVEMENT_GATE", "0")
    assert not adapter.gate_enabled() and adapter.findings_batch([{"rule_name": "R"}], __file__) == {}
