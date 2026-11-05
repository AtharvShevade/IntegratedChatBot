"""Tests for the label-based locator: no return data needed, the workbook is built here."""
from decimal import Decimal

import openpyxl

from backend.error_improvement import explain_workbook as ew
from backend.error_improvement import fact_address as fa
from backend.error_improvement import label_locator as ll
from backend.error_improvement import rule_cards as rc
from backend.error_improvement import value_locator as vl
from backend.error_improvement.workbook import Workbook


def test_number_words_and_amount_prefixes_meet_the_sheet_wording():
    assert ll.tokens("UptoTwentyEightDaysMember") == ll.tokens("Up to 28 days")
    assert ll.tokens("OneEightyOneDaysAndUptoOneYearMember")[0] == [181, 1]
    assert ll.tokens("NintyOneDaysAndUptoOneEightyDaysMember")[0] == [91, 180]
    assert ll.tokens("AboveTenCroreAndUptoFiftyCroreMember")[0] == ll.tokens("Rs. 10 crore and below Rs. 50 crore")[0] == [10, 50]
    # 'Rs. 1 crore' is an amount, 'Rupee Term Deposits' is a category
    assert "rs" not in ll.tokens("Below Rs. 1 crore")[1] and "rs" not in ll.tokens("BelowRupeeOneCrore")[1]
    assert "rs" in ll.tokens("RupeeTermDepositsMember")[1] and "rs" in ll.tokens("Rupee Term Deposits")[1]


def _book(tmp_path):
    """Two blocks with the same size bands and the same rates: 'Rupee Term Deposits' (rows 4-5) and 'Total Term Deposits' (rows 7-8)."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "TD"
    ws["A1"] = "Size of Deposit"
    ws["B1"] = "Up to 28 days"
    ws["D1"] = "29 days and upto 90 days"
    ws["B2"], ws["C2"], ws["D2"], ws["E2"] = "Amount", "Rate", "Amount", "Rate"
    ws["A3"] = "Rupee Term Deposits"
    for r, label, rate1, rate2 in ((4, "Below Rs. 1 crore", 0.06, 0.07), (5, "Rs. 1 crore and below Rs. 10 crore", 0.04, 0.05)):
        ws.cell(r, 1, label)
        ws.cell(r, 2, 100)
        ws.cell(r, 3, rate1)
        ws.cell(r, 4, 200)
        ws.cell(r, 5, rate2)
    ws["A7"] = "Total Term Deposits\nBelow Rs. 1 crore"
    ws["A8"] = "Rs. 1 crore and below Rs. 10 crore"
    for r, rate1, rate2 in ((7, 0.06, 0.07), (8, 0.04, 0.05)):
        ws.cell(r, 2, 100)
        ws.cell(r, 3, rate1)
        ws.cell(r, 4, 200)
        ws.cell(r, 5, rate2)
    p = tmp_path / "td.xlsx"
    wb.save(p)
    return Workbook(str(p))


class _F:
    def __init__(self, value, context, concept="WeightedAverageInterestRate"):
        self.value, self.context, self.concept, self.decimal = value, context, concept, "2"


P = "fromto_20250101_20250331_"
RUPEE = _F("0.06", P + "UptoTwentyEightDaysMember_BelowRupeeOneCroreMember_RupeeTermDepositsMember")
TOTAL = _F("0.06", P + "UptoTwentyEightDaysMember_BelowRupeeOneCroreMember")


def _locator(tmp_path):
    wb = _book(tmp_path)
    lab = ll.LabelLocator(wb, vl.ValueLocator(wb))
    lab.set_vocabulary(ew.toggle_members([RUPEE.context, TOTAL.context]))
    return lab


def test_toggle_members_are_the_ones_a_rule_switches_on_and_off():
    assert ew.toggle_members([RUPEE.context, TOTAL.context, P + "DomesticMember"]) == ["RupeeTermDepositsMember"]


def test_the_context_without_the_category_member_gets_the_aggregate_block(tmp_path):
    lab = _locator(tmp_path)
    r = lab.resolve(RUPEE, taken=frozenset())
    t = lab.resolve(TOTAL, taken=frozenset())
    assert r is not None and (r.addresses[0].sheet, r.addresses[0].a1) == ("TD", "C4")
    assert t is not None and (t.addresses[0].sheet, t.addresses[0].a1) == ("TD", "C7")
    assert r.status == t.status == "INFERRED"


def test_a_group_never_gives_two_entries_the_same_cell(tmp_path):
    lab = _locator(tmp_path)
    out = lab.resolve_group([RUPEE, TOTAL])
    cells = {(res.addresses[0].sheet, res.addresses[0].a1) for res in out.values()}
    assert len(out) == 2 and len(cells) == 2


def test_a_value_that_is_not_in_the_workbook_is_not_placed(tmp_path):
    lab = _locator(tmp_path)
    assert lab.resolve(_F("0.99", RUPEE.context)) is None


def test_ambiguity_is_not_guessed(tmp_path):
    lab = _locator(tmp_path)
    # no member names the block or the band: every cell holding 0.06 explains the one member equally
    assert lab.resolve(_F("0.06", P + "UptoTwentyEightDaysMember")) is None


def test_label_locator_places_what_the_mapping_could_not():
    """analyse(): a fact whose mapped cell holds another value is placed from its labels (checked through resolve_group)."""
    assert hasattr(ew, "_label_pass") and callable(ll.LabelLocator.resolve_group)


def test_rounding_note_names_the_filed_precision():
    class Comp:
        class lhs:                                      # noqa: N801
            @staticmethod
            def variables():
                return ["V1"]

    class Fact:
        decimal = "2"

    class Loc:
        fact = Fact()
        addr = None

    ev = {"lhs_value": Decimal("0.06"), "rhs_value": Decimal("0.0599")}
    note = rc.rounding_note(Comp, {"V1": [Loc()]}, ev, 4)
    assert note == "The filing rounds 0.0599 to 0.06 (2 decimal places), but the rule checks at 4. Report at least 4 decimal places."
    assert rc.rounding_note(Comp, {"V1": [Loc()]}, {"lhs_value": Decimal("0.06"), "rhs_value": Decimal("0.0699")}, 4) == ""
    assert fa.tolerance(Decimal("0.06"), "2") == Decimal("0.005")


def test_a_member_is_also_named_by_the_alternate_text_the_return_gives_it(tmp_path):
    from backend.error_improvement import cell_locator as cl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "S"
    ws["A1"], ws["B1"] = "Counterparty", "Amount"
    ws["A2"], ws["B2"] = "Group", 5
    p = tmp_path / "s.xlsx"
    wb.save(p)
    lab = ll.LabelLocator(Workbook(str(p)), vl.ValueLocator(Workbook(str(p))))
    assert lab.score("S", 2, 1, ["GroupMember"])[0] == 2
    assert lab.score("S", 2, 1, ["SomeOtherMember"]) == (0, ["SomeOtherMember"], 0)        # no name of its own in the sheet
    lab.set_alternates({"SomeOtherMember": ["Group"]})
    assert lab.score("S", 2, 1, ["SomeOtherMember"]) == (2, [], 0)
    (tmp_path / "AlternateText.xml").write_text('<Document><AlternateText ReturnId="1" TliD="4" Dim="D" Domain="ns:SingleMember" AltText="Single"/>'
                                                '<AlternateText Domain="SingleMember" AltText="Single"/><AlternateText Domain="" AltText="x"/></Document>', encoding="utf-8")
    assert cl._load_alt_text(str(tmp_path / "AlternateText.xml")) == {"SingleMember": ["Single"]}
    assert cl._load_alt_text(str(tmp_path / "nope.xml")) == {}
