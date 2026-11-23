"""Tests for the return-independent helpers of the explainer engine (no repo data needed)."""
import datetime as dt
import os
import sys

from backend.error_improvement import direct_errors as de          # noqa: E402
from backend.error_improvement import fact_address as fa           # noqa: E402
from backend.error_improvement import match_upload as mu           # noqa: E402


def test_ranges_collapse_consecutive_rows_per_column():
    assert de.ranges(["G9", "G10", "G11", "H9", "G13"]) == "G9:G11, G13, H9"


def test_error_key_is_the_last_name_value_pair():
    e = de.DirectError("1", "S", "C", "", "", "Mandatory Fields Can't be Blank: Field:-Name,PAN:ABCDE1234F")
    assert e.key == ("PAN", "ABCDE1234F")
    assert e.kind == "Mandatory Fields Can't be Blank"


def test_number_words_beat_bare_digits_in_a_context():
    assert fa.number_hints({"1", "OTCDerivatives", "QCCPTwo"}) == {2}
    assert fa.number_hints({"1", "OTCDerivatives"}) == {1}
    assert fa.number_hints({"One"}) == set()           # a bare number word is a member name, not an entry number


class _Wb:
    sheets = ["CR-QCCP (1)", "CR-QCCP (2)", "CR-QCCPs", "Other"]


def test_sheet_family_groups_numbered_copies_only():
    assert fa.sheet_family(_Wb(), "CR-QCCP (1)") == ["CR-QCCP (1)", "CR-QCCP (2)"]
    assert fa._pick_sheets(_Wb(), "CR-QCCP (1)", {2}) == ["CR-QCCP (2)"]
    assert fa._pick_sheets(_Wb(), "Other", {2}) == ["Other"]


def test_match_upload_picks_latest_upload_before_the_error_file(tmp_path):
    for d in ("21-10-26-13-45-51", "21-10-26-13-00-00", "21-10-26-15-00-00"):
        (tmp_path / "UploadedFiles" / d).mkdir(parents=True)
        (tmp_path / "UploadedFiles" / d / "book.xlsx").write_bytes(b"x")
    got = mu.match_upload(str(tmp_path), "ABPL_21-10-26_01-48-12_Instance.html")     # 13:48:12 on a 12-hour clock
    assert got and "13-45-51" in got
    assert mu.match_upload(str(tmp_path), "ABPL_21-10-26_05-00-00_Instance.html") is None


def test_value_matches_numbers_with_multiplier_and_text():
    a = fa.Address("1", "", "S", 1, 1, "c", 1000, 12.5)
    assert fa.value_matches(a, "12500")
    assert not fa.value_matches(a, "12501")
    t = fa.Address("1", "", "S", 1, 1, "c", 1, "Anand Shinde")
    assert fa.value_matches(t, "anand shinde")


def test_formula_signed_refs_read_a_plain_signed_sum(tmp_path):
    import openpyxl
    from backend.error_improvement import formula_graph as fg
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "S"
    ws["B21"] = "=ROUND(B19-B20,2)"
    ws["B22"] = "=IF(B19>0,B20,0)"
    ws["C5"] = "=C1+C2-C3"
    p = tmp_path / "t.xlsx"
    wb.save(p)
    g = fg.FormulaGraph(str(p))
    assert g.signed_refs("S", 21, 1) == [(19, 1, 1), (20, 1, -1)]
    assert g.signed_refs("S", 22, 1) is None
    assert g.signed_refs("S", 5, 2) == [(1, 2, 1), (2, 2, 1), (3, 2, -1)]


def test_absent_operand_title_split():
    from backend.error_improvement import absent_operands as ao
    assert ao.split_terms("A = (B + C - D)") == ["A", "B", "C", "D"]


def test_label_agreement_ignores_numbering_and_punctuation():
    from backend.error_improvement import absent_operands as ao
    assert ao._agree("I. Excess/Deficit in Provisions Held (G-F)", "10.Excess/deficit in provisions held (8-9) - (estimate)")
    assert ao._agree("2.3 Medium", "2.3 Medium")
    assert not ao._agree("I.   Gross Advances (II + III)", "Gross NPAs at begining of the Year")
    assert not ao._agree("I.   Gross Advances (II + III)", "Total")


_FORMULA = """<root xmlns:va="http://xbrl.org/2008/assertion/value" xmlns:variable="http://xbrl.org/2008/variable"
 xmlns:cf="http://xbrl.org/2008/filter/concept" xmlns:df="http://xbrl.org/2008/filter/dimension"
 xmlns:xlink="http://www.w3.org/1999/xlink">
 <va:valueAssertion xlink:label="R1" id="R1" test="$V1 = $V2 + $V3"/>
 <variable:variableArc xlink:from="R1" xlink:to="Var_1" name="V1"/>
 <variable:factVariable xlink:label="Var_1"/>
 <variable:variableFilterArc xlink:from="Var_1" xlink:to="c1" complement="false"/>
 <cf:conceptName xlink:label="c1"><cf:concept><cf:qname>p:Total</cf:qname></cf:concept></cf:conceptName>
 <variable:variableArc xlink:from="R1" xlink:to="Var_3" name="V3"/>
 <variable:factVariable xlink:label="Var_3" fallbackValue="0"/>
 <variable:variableFilterArc xlink:from="Var_3" xlink:to="d3" complement="false"/>
 <df:explicitDimension xlink:label="d3"><df:dimension><df:qname>p:RegionAxis</df:qname></df:dimension>
   <df:member><df:qname>p:NorthMember</df:qname></df:member></df:explicitDimension>
</root>"""


def test_formula_defs_read_operands_and_pinned_dimensions(tmp_path):
    from backend.error_improvement import formula_defs as fd
    f = tmp_path / "x-formula.xml"
    f.write_text(_FORMULA, encoding="utf-8")
    d = fd.load(str(tmp_path))["R1"]
    assert d["test"] == "$V1 = $V2 + $V3"
    assert d["vars"]["V1"]["concepts"] == ["Total"]
    assert d["vars"]["V3"]["dims"] == {"RegionAxis": ["NorthMember"]}
    assert d["vars"]["V3"]["fallback"] == "0"


def test_reported_facts_distinguish_reported_zero_from_unreported(tmp_path):
    from backend.error_improvement import reported_facts as rf
    xml = ("<xbrli:xbrl xmlns:xbrli='http://www.xbrl.org/2003/instance' xmlns:xbrldi='http://xbrl.org/2006/xbrldi' xmlns:p='urn:p'>"
           "<xbrli:context id='c1'><xbrli:entity/><xbrli:period><xbrli:instant>2026-03-31</xbrli:instant></xbrli:period>"
           "<xbrli:scenario><xbrldi:explicitMember dimension='p:RegionAxis'>p:NorthMember</xbrldi:explicitMember></xbrli:scenario>"
           "</xbrli:context><p:Total contextRef='c1' unitRef='u'>0</p:Total></xbrli:xbrl>")
    (tmp_path / "A_Instance.xml").write_text(xml, encoding="utf-8")
    r = rf.load(str(tmp_path / "A_Instance.html"))
    assert r.ctx_dims("c1") == {"RegionAxis": "NorthMember"}
    assert r.value("Total", "c1") == "0"            # reported zero
    assert r.value("Other", "c1") is None           # never reported


def test_ratio_numbers_keep_their_digits_and_amounts_keep_grouping():
    from decimal import Decimal
    from backend.error_improvement import explain_table as et
    assert et.fmt_exact(Decimal("0.0312")) == "0.0312"
    assert et.fmt_exact(Decimal("0.07")) == "0.07"
    assert et.fmt_exact(Decimal("0")) == "0"
    assert et.fmt_exact(Decimal("1234567.5")) == et.num(Decimal("1234567.5"))


def test_member_names_compare_without_punctuation():
    # context ids drop the dot the mapping keeps: 'PPIsUptoRs.2Lakh...' vs 'PPIsUptoRs2Lakh...'
    assert fa._alnum("PPIsUptoRs.2LakhWithKYCMember") == fa._alnum("PPIsUptoRs2LakhWithKYCMember")


def test_count_rule_sheet_is_the_one_the_rule_name_spells():
    from backend.error_improvement import explain_table as et
    assert et._sheet_for_rule("SectionB-NumberOfRecordsCheck", ["Section-A", "Section-B"]) == ["Section-B"]
    assert et._sheet_for_rule("SectionA-NumberOfRecordsCheck", ["Section-A", "Section-B"]) == ["Section-A"]


def test_readable_template_leaves_xlsx_alone_and_caches_conversions(tmp_path, monkeypatch):
    import openpyxl
    from backend.error_improvement import template_converter as tc
    monkeypatch.setenv("TEMPLATE_CACHE_DIR", str(tmp_path / "cache"))
    # an .xlsx is returned as is
    x = tmp_path / "a.xlsx"
    openpyxl.Workbook().save(x)
    assert tc.readable_template(str(x)) == str(x)
    # a binary file is converted once, the cache is reused, the original is untouched
    b = tmp_path / "b.xls"
    b.write_bytes(b"\xd0\xcf\x11\xe0 binary")
    calls = []

    def fake(src, dst):
        calls.append(src)
        openpyxl.Workbook().save(dst)
        return True

    monkeypatch.setattr(tc, "CONVERTERS", (fake,))
    out = tc.readable_template(str(b))
    assert out and out.endswith(".xlsx") and out != str(b)
    assert tc.readable_template(str(b)) == out and len(calls) == 1
    assert b.read_bytes().startswith(b"\xd0\xcf")


def test_readable_template_gives_none_when_no_converter_works(tmp_path, monkeypatch):
    from backend.error_improvement import template_converter as tc
    monkeypatch.setenv("TEMPLATE_CACHE_DIR", str(tmp_path / "cache"))
    b = tmp_path / "c.xls"
    b.write_bytes(b"\xd0\xcf\x11\xe0 binary")
    monkeypatch.setattr(tc, "CONVERTERS", (lambda s, d: False,))
    assert tc.readable_template(str(b)) is None
    assert tc.readable_template(str(tmp_path / "missing.xls")) is None


def test_other_error_formats_are_recognised_and_explained(tmp_path):
    from backend.error_improvement import other_errors as oe
    from backend.error_improvement import explain_table as et
    dup = tmp_path / "XBRLError_X_Instance.xml"
    dup.write_text('<InstanceErrorDetails><ErrorDetails><ErrorMessage>Duplicate of following elements are found in XBRL document.</ErrorMessage>'
                   '<DuplicateElementList><Element PrimaryElement="TotalDeposits" ContextRef="asof_20230331" UnitRef="INR" SheetOrTableName="Sheet1">'
                   '<DuplicateElement LineNumber="1" Value="5"/><DuplicateElement LineNumber="2" Value="0"/></Element></DuplicateElementList>'
                   '</ErrorDetails></InstanceErrorDetails>', encoding="utf-8")
    assert oe.detect(str(dup)) == "duplicate"
    rows, _ = oe.explain("duplicate", str(dup), None, et.Row)
    assert "Total Deposits is reported 2 times" in rows[0].error and "'5' and '0'" in rows[0].error

    dd = tmp_path / "XBRLError_Y_Instance.xml"
    dd.write_text("<InstanceErrorDetails><Row Error=\"Dynamic Domain: 'Equity shares' is not a valid value. Please choose from the given list: "
                  "'Aggregate,Equity Shares' for Column 'TYPE' with PL_ID - 15 And SheetOrTable Name - SHEET9 !!!\" /></InstanceErrorDetails>",
                  encoding="utf-8")
    assert oe.detect(str(dd)) == "dynamic_domain"
    rows, _ = oe.explain("dynamic_domain", str(dd), None, et.Row)
    assert "'Equity shares' -> 'Equity Shares' (the same text with different capital letters)" in rows[0].solution

    svc = tmp_path / "XBRLError_Z_Instance.xml"
    svc.write_text("<Error>System.IO.InvalidDataException: Instance validation API Failed !!! at A.B.ValidateInstace(String x)</Error>", encoding="utf-8")
    assert oe.detect(str(svc)) == "service_failure"
    rows, _ = oe.explain("service_failure", str(svc), None, et.Row)
    assert rows[0].kind == "SPEC" and "No change to the data" in rows[0].solution

    rep = tmp_path / "Report_1.xml"
    rep.write_text('<Document><Report Id="1" Rule="Industry Code for four Months" Type="NF"><detail PAN="AAAAA1111A" MONTH1="1" MONTH2="2"/></Report></Document>',
                   encoding="utf-8")
    assert oe.detect(str(rep)) == "crilc_report"
    rows, _ = oe.explain("crilc_report", str(rep), None, et.Row)
    assert "AAAAA1111A" in rows[0].where and rows[0].kind == "RULE"


def _book(tmp_path, rows):
    import openpyxl
    from backend.error_improvement.workbook import Workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    for r, row in enumerate(rows, 1):
        for c, v in enumerate(row, 1):
            ws.cell(row=r, column=c, value=v)
    p = tmp_path / "b.xlsx"
    wb.save(p)
    return Workbook(str(p))


def test_value_locator_names_a_unique_value_and_uses_labels_to_break_ties(tmp_path):
    from backend.error_improvement import value_locator as vl
    from backend.error_improvement.error_html import Fact
    wb = _book(tmp_path, [["", "Item", "Amount"],
                          ["", "Gross Advances", 1250],
                          ["", "Export Trade", 1250],
                          ["", "Banks", 777]])
    loc = vl.ValueLocator(wb)
    # a value held by one cell: that cell, strong
    r = loc.resolve(Fact("V1", "StandardAdvances", "777", "asof_20260331_BanksMember"), set(), "")
    assert r.status == "INFERRED" and (r.addresses[0].row, r.addresses[0].col) == (4, 2)
    # a value held by two cells: the row label that matches the item/member wins
    r = loc.resolve(Fact("V2", "StandardAdvances", "1250", "asof_20260331_ExportTradeMember"), vl.words("Export Trade"), "")
    assert r.status in ("INFERRED", "LIKELY") and r.addresses[0].row == 3
    # nothing to match on: candidates only, no cell named
    r = loc.resolve(Fact("V3", "Other", "1250", "asof_20260331"), set(), "")
    assert r.status == "UNCONFIRMED" and len(r.addresses) == 2
    # zero is never located by value
    assert loc.resolve(Fact("V4", "X", "0", "asof_20260331"), set(), "") is None


def test_empty_workbook_lets_every_stage_run_with_no_cells():
    from backend.error_improvement.workbook import EmptyWorkbook
    wb = EmptyWorkbook()
    assert wb.sheets == [] and wb.value("S", 1, 0) is None and wb.index("S") == {} and not wb.has_sheet("S")


def test_rule_card_helpers_work_as_a_package_import():
    """Exercises the helpers that import sibling modules lazily (a flat `__import__` once broke the chatbot copy)."""
    from decimal import Decimal
    from backend.error_improvement import rule_cards as rc
    from backend.error_improvement.error_html import Fact
    f = Fact("V1", "StandardAdvances", "1000", "asof_20260331_GrossAdvancesMember")
    assert rc._item_name(f) == "Gross Advances (Standard Advances)"
    assert rc.money(Decimal("28062200000")) == "₹28,062,200,000"
    assert rc.cell_money(Decimal("196448.89"), 100000, "INR") == "₹196,448.89 lakh"
    card = {"rule_name": "TermDeposit-WeightedAverageRate-VA", "number": 2, "checks": "a", "problem": "p", "cause": "c", "fix": "f",
            "related": "May also resolve rule 7 (X), which use the same cell.", "other_cases": None, "kind": "ratio", "evidence_key": "CONFIRMED",
            "cells": [{"item": "Rupee deposit amount", "sheet": "TermDeposit", "cell": "B7", "row_label": "1. Rupee deposit amount", "current": "1"}],
            "calc": [("Left side", "2.61%"), ("Right side", "2.62%"), ("Difference", "-0.01%")]}
    card["view"] = rc._compact_view(card, [], {}, rc.cell_money)
    v = card["view"]
    assert (v["title"], v["subtitle"]) == ("Weighted Average Rate", "Term Deposit · Formula validation")
    assert [k[0] for k in v["kv"]] == ["Reported value", "Calculated value", "Difference"] and v["kv"][2][2] == "bad"
    assert "Fixing it may also resolve rule 7." in v["fix"] and v["groups"][0]["cells"][0] == {"cell": "B7", "label": "Rupee deposit amount"}
    secs = rc.card_to_sections(card)
    assert [s["kind"] for s in secs] == ["issue_card"] and "What went wrong?" in rc.card_to_text(card)


# ── the "how is this total calculated" breakdown ────────────────────────────────────────────────────────────────
class _Graph:
    def __init__(self, formulas, readable=True):
        self.f, self._r = formulas, readable

    def readable(self):
        return self._r

    def formula(self, sheet, row, col):
        return self.f.get((sheet, row, col))


class _Book:
    """cells: {(row, col0): value}; labels: {row: text}; the total sits in K (col 10)."""
    def __init__(self, cells, formulas, labels=None, template=False, readable=True):
        self.cells, self.labels, self.is_template = cells, labels or {}, template
        self.formulas = _Graph(formulas, readable)

    def value(self, sheet, row, col):
        return self.cells.get((row, col))

    def text_row(self, sheet, row, a=0, b=6):
        return self.labels.get(row, "")


def _bd(cells, formula, labels=None, row=10, **kw):
    from backend.error_improvement import explain_table as et
    wb = _Book(cells, {("S", row, 10): formula} if formula else {}, labels or {}, **kw)
    return et.calculated_cell_breakdown(wb, "S", row, 10)


def test_breakdown_sum_that_matches_its_components():
    b = _bd({(1, 10): 5, (2, 10): 7, (10, 10): 12}, "=SUM(K1:K2)", {1: "A | Rent", 2: "Fees"})
    assert b["status"] == "ok" and b["formula"] == "K10 = SUM(K1:K2)"
    assert "matches" in b["summary"] and "12" in b["summary"]
    assert [(c["cell"], c["value"]) for c in b["groups"][0]["items"]] == [("K1", "5"), ("K2", "7")]


def test_breakdown_says_the_sum_is_wrong_only_when_the_numbers_show_it():
    b = _bd({(1, 10): 5, (2, 10): 7, (10, 10): 10}, "=K1+K2")
    assert "shows 10 but its components add up to 12" in b["summary"] and "difference -2" in b["summary"]


def test_breakdown_failed_comparison_of_two_totals_is_not_called_a_wrong_sum():
    f = "=ROUND(IF(ROUND(K1+K2,2)=ROUND(K3+K4,2),K3+K4,0),2)"
    b = _bd({(1, 10): 10, (2, 10): 5, (3, 10): 10, (4, 10): 5.05, (10, 10): 0}, f)
    assert "its own check fails" in b["summary"] and "not a wrong sum" in b["summary"]
    assert [g["label"] for g in b["groups"]] == ["First total", "Second total"]
    ok = _bd({(1, 10): 10, (2, 10): 5, (3, 10): 10, (4, 10): 5, (10, 10): 15}, f)
    assert "check holds" in ok["summary"]


def test_breakdown_marks_empty_and_zero_components_and_lists_valued_ones_first():
    b = _bd({(1, 10): 0, (2, 10): None, (3, 10): 9, (10, 10): 9}, "=SUM(K1:K3)")
    items = b["groups"][0]["items"]
    assert [(c["cell"], c["state"]) for c in items] == [("K3", "value"), ("K1", "zero"), ("K2", "empty")]
    assert items[1]["value"] == "0" and items[2]["value"] == "empty"


def test_breakdown_shows_about_six_components_then_a_count_of_the_rest():
    cells = {(r, 10): (r if r < 9 else 0) for r in range(1, 11)}
    b = _bd(cells, "=SUM(K1:K9)", row=11)
    g = b["groups"][0]
    assert len(g["items"]) == 6 and g["more"] == 3 and g["more_text"] == "+3 more (1 empty or 0)"


def test_breakdown_without_a_template_formula():
    assert "No formula is available in the template" in _bd({}, None, {10: "Sub-total | Total"})["summary"]
    assert _bd({}, None, {10: "Export trade"}) is None                  # a plain input cell is not a total


def test_breakdown_formula_that_cannot_be_evaluated_shows_the_text_without_numbers():
    b = _bd({(1, 10): 5, (10, 10): 5}, '=INDEX(K1:K2,1)')
    assert b["status"] == "unsupported" and "could not be evaluated" in b["summary"] and b["formula"].startswith("K10 = INDEX")
    assert b["groups"][0]["items"][0]["value"] == "5"                    # the real cell value, no invented result


def test_breakdown_without_the_users_workbook_says_values_are_unverified():
    b = _bd({(1, 10): 5, (2, 10): 7}, "=K1+K2", template=True)
    assert "could not be verified" in b["note"] and all(c["value"] == "" and c["state"] == "unknown" for c in b["groups"][0]["items"])
    assert "calculated" not in b["summary"].replace("is calculated by", "")


def test_breakdown_when_the_templates_formulas_are_unreadable():
    b = _bd({}, "=K1+K2", readable=False)
    assert b["status"] == "unreadable" and "could not be read" in b["summary"]


def test_card_text_and_sections_carry_the_breakdown():
    from backend.error_improvement import rule_cards as rc
    b = _bd({(1, 10): 5, (2, 10): 7, (10, 10): 12}, "=K1+K2", {1: "Rent"})
    card = {"rule_name": "S-X-Y", "number": 1, "checks": "a", "problem": "p", "cause": "c", "fix": "f", "related": None,
            "other_cases": None, "kind": "ratio", "evidence_key": "CONFIRMED", "cells": [], "calc": []}
    card["view"] = rc._compact_view(card, [], {}, rc.cell_money)
    card["view"]["breakdown"] = b
    sec = rc.card_to_sections(card)[0]["breakdown"]
    assert sec["heading"] == "Contributing cells" and sec["toggle"] == "View all 2 contributing cells" and sec["groups"][0]["items"][0]["cell"] == "K1"
    text = rc.card_to_text(card)
    assert "Contributing cells" in text and "K10 = K1+K2" in text and "K1  Rent  5" in text and "What should you check?" in text


# ── rule-specific wording ───────────────────────────────────────────────────────────────────────────────────────
class _Lc:
    def __init__(self, sheet, a1, value):
        from types import SimpleNamespace as N
        self.addr = N(sheet=sheet, a1=a1)
        self.fact = N(value=value)


class _Side:
    def __init__(self, var):
        self.var = var

    def signed_variables(self):
        return [(self.var, 1)]


class _Cmp:
    def __init__(self, op):
        self.operator, self.lhs, self.rhs = op, _Side("V1"), _Side("V2")


def _row(**facts):
    from types import SimpleNamespace as N
    return N(facts=facts)


def _view(op, mine, instances=10, kind="identity", verdict="RULE", located=None):
    from backend.error_improvement import rule_cards as rc
    located = located or {"V1": [_Lc("S", "J7", 6)], "V2": [_Lc("S", "D7", 20)]}
    card = {"rule_name": "S-X-Y", "number": 1, "problem": "p", "cause": "c", "fix": "f", "related": None, "other_cases": None,
            "kind": kind, "verdict": verdict, "evidence_key": "CONFIRMED", "cells": [], "calc": [], "instances": instances}
    return rc._compact_view(card, [], located, rc.cell_money, _Cmp(op), mine)


def test_strict_comparison_uses_left_right_wording_and_separates_the_kinds_of_case():
    v = _view(">", [_row(kind="rule behaviour", equal=8, equal_both_zero=7, sides_differ=1),
                    _row(kind="missing entries", cells=["AB18 must be above 7,400 (the value in AC18)"])])
    assert "left value to be greater than the right value" in v["wrong"] and "fails in 10 case(s)" in v["wrong"]
    assert [k[0] for k in v["kv"]] == ["Left value · J7", "Right value · D7", "Condition"]
    assert "components add up" not in v["wrong"] and "Reported" not in " ".join(k[0] for k in v["kv"])
    assert "Equal values: no data change" in v["fix"] and "taxonomy owner" in v["fix"] and "Empty entry next to a filled cell: AB18" in v["fix"]
    assert "first failing case; the rule fails in 10 cases" in v["cells_note"]


def test_equality_of_two_single_cells_names_both_cells_not_reported_and_calculated():
    v = _view("=", [], kind="identity", verdict="DATA", located={"V1": [_Lc("Sec8", "AC16", 1450000000)], "V2": [_Lc("Ind", "AB47", 0)]})
    assert v["wrong"] == "These two values must be equal, but they do not match." and v["kv_code"] == ["Sec8!AC16", "Ind!AB47"]
    assert [k[0] for k in v["kv"]] == ["Sec8!AC16", "Ind!AB47", "Difference"]


def test_cell_list_says_when_it_is_incomplete():
    v = _view(">", [_row(kind="rule behaviour", equal=1, equal_both_zero=1, sides_differ=0)],
              located={"V1": [_Lc("S", "J7", 0)], "V2": [_Lc("S", "D7", 0), type("X", (), {"addr": None, "fact": None})()]})
    assert "could not be located, so this list is incomplete" in v["cells_note"]


def test_calculated_total_equality_gets_steps_and_a_do_not_edit_note():
    from backend.error_improvement import rule_cards as rc
    from types import SimpleNamespace as N
    bd = {"a1": "AB47", "status": "ok", "groups": [{"items": [{"state": "zero"}]}]}
    ci = {"a1": "AB47", "sheet": "Ind", "breakdown": bd, "cur": 0, "need": 1, "multiplier": 1, "unit": "INR"}
    dg = [N(facts={"culprit_info": [ci]})]
    located = {"V1": [_Lc("Sec8", "AC16", 1450000000)], "V2": [_Lc("Ind", "AB47", 0)]}
    card = {"rule_name": "S-X-Y", "number": 1, "problem": "p", "cause": "c", "fix": "f", "related": None, "other_cases": None,
            "kind": "identity", "verdict": "DATA", "evidence_key": "CONFIRMED", "instances": 1, "calc": [],
            "cells": [{"item": "x", "sheet": "Ind", "cell": "AB47", "row_label": "All Industries", "current": "0"}]}
    v = rc._compact_view(card, dg, located, rc.cell_money, _Cmp("="), [])
    assert v["steps"][:2] == ["Verify the contributing input values against the source data.", "Check whether zero or empty values are expected."]
    assert "AC16" in v["steps"][2] and v["why_heading"] == "Why is AB47 zero?" or v["why_heading"].startswith("Why is AB47")
    assert v["safety"] == "Do not edit AB47 directly. Correct the underlying inputs only after confirming the cause."
    assert v["captions"]["Ind!AB47"] == "All Industries"
    sec = rc.card_to_sections({**card, "view": v})[0]
    assert sec["badge"] == "Failed" and sec["fix"]["heading"] == "What should you check?" and len(sec["fix"]["steps"]) == 3


# ── the shared 'Contributing cells' structure (calc_view) ────────────────────────────────────────────────────────
def _parse(text):
    from backend.error_improvement import explain_workbook as ew
    return ew.fx.parse_formula(text)


def _flc(var, concept, value, unit="INR", decimal="-3", addr=None):
    from types import SimpleNamespace as N
    return N(fact=N(var=var, concept=concept, value=value, unit=unit, decimal=decimal), addr=addr, res=N(status="CONFIRMED"))


def _addr(sheet, a1, wv, mult=1):
    from types import SimpleNamespace as N
    return N(sheet=sheet, a1=a1, workbook_value=wv, multiplier=mult)


_WAVG = ("round( $V6*10000) div 10000 = round(((( $V1 * $V2 )+( $V3 * $V4 ))div( $V1 + $V3 ))*10000) div 10000")


def test_roles_name_amount_rate_pairs_numerator_denominator_and_components():
    from backend.error_improvement import calc_view as cv
    names, shape = cv.roles(_parse(_WAVG), "weighted_average", {"V1": "AmountOutstanding", "V2": "WeightedAverageInterestRate",
                                                                "V3": "AmountOutstanding", "V4": "WeightedAverageInterestRate"})
    assert shape == "pairs" and names["V1"] == "Amount 1" and names["V2"] == "Rate 1" and names["V4"] == "Rate 2" and names["V6"] == "Reported average"
    names, shape = cv.roles(_parse("round(abs($V3*10000)) div 10000 = round(abs(($V1 div $V2)*10000)) div 10000"), "ratio", {})
    assert shape == "ratio" and (names["V1"], names["V2"], names["V3"]) == ("Numerator", "Denominator", "Reported ratio")
    names, shape = cv.roles(_parse("$V1 = $V2 + $V3 - $V4"), "aggregate", {})
    assert shape == "sum" and names["V1"] == "Reported total" and names["V4"] == "Component 3 (subtracted)"


def test_formula_is_rendered_in_words_and_cut_when_long():
    from backend.error_improvement import calc_view as cv
    comp = _parse(_WAVG)
    names, _ = cv.roles(comp, "weighted_average", {"V2": "Rate", "V4": "Rate"})
    assert cv.render_formula(comp, names) == "Reported average = (Amount 1 × Rate 1 + Amount 2 × Rate 2) ÷ (Amount 1 + Amount 2)"
    assert cv.render_formula(comp, names, limit=20).endswith("…")


def _located(**over):
    base = {"V6": [_flc("V6", "WeightedAverageInterestRate", "0.06", "PURE", "2", _addr("S", "C23", 0.06))],
            "V1": [_flc("V1", "AmountOutstanding", "1000", addr=_addr("S", "B7", 1000))],
            "V2": [_flc("V2", "WeightedAverageInterestRate", "0.05", "PURE", "2", _addr("S", "C9", 0.05))],
            "V3": [_flc("V3", "AmountOutstanding", "0", addr=_addr("S", "B8", 0))],
            "V4": [_flc("V4", "WeightedAverageInterestRate", "0.07", "PURE", "2", _addr("S", "C10", 0.07))]}
    base.update(over)
    return base


def _contrib(located):
    from backend.error_improvement import calc_view as cv
    return cv.contributing(_parse(_WAVG), "weighted_average", located, None, lambda w, a: "Row " + a.a1,
                           lambda lc, a: str(a.workbook_value) if a is not None else lc.fact.value + " (error file)")


def test_contributing_cells_complete_evidence_lists_every_operand_with_role_and_flags_zero():
    b = _contrib(_located())
    items = b["groups"][0]["items"]
    assert [i["cell"] for i in items] == ["C23", "B7", "C9", "B8", "C10"]
    assert items[1]["label"] == "Amount 1 · Row B7" and items[3]["state"] == "zero" and items[3]["status"] == "Check"
    assert b["unlocated"] == 0 and b["differing"] == 0 and "could not be located" not in b["status_sub"]
    assert b["toggle"] == "View all 5 contributing cells" and b["shape"] == "pairs"


def test_contributing_cells_incomplete_evidence_names_the_unlocated_operands():
    b = _contrib(_located(V2=[_flc("V2", "WeightedAverageInterestRate", "0.05", "PURE", "2", None)]))
    assert b["unlocated"] == 1 and "1 could not be located" in b["status_sub"] and "Rate 1" in b["note"]
    item = next(i for i in b["groups"][0]["items"] if i["status"] == "Not located")
    assert item["value"] == "0.05 (error file)"                            # the filing's value, never invented


def test_contributing_cells_flags_a_workbook_value_that_disagrees_with_the_filing_but_allows_rounding():
    ok = _contrib(_located(V2=[_flc("V2", "WeightedAverageInterestRate", "0.05", "PURE", "2", _addr("S", "C9", 0.0499))]))
    assert ok["differing"] == 0                                             # 0.0499 filed to 2 decimals is 0.05
    bad = _contrib(_located(V2=[_flc("V2", "WeightedAverageInterestRate", "0.06", "PURE", "2", _addr("S", "C9", 0.04))]))
    assert bad["differing"] == 1 and "Differs from filing" in [i["status"] for i in bad["groups"][0]["items"]]
    assert "this cell is not the one the rule reads" in bad["note"]


def test_contributing_cells_without_any_located_operand_is_none():
    from backend.error_improvement import calc_view as cv
    assert cv.contributing(_parse(_WAVG), "weighted_average", {}, None, lambda *a: "", lambda *a: "") is None


def _card(kind, verdict="DATA", calc=None):
    return {"rule_name": "TermDeposit-WeightedAverageRate", "number": 1, "problem": "p", "cause": "c", "fix": "f", "related": None,
            "other_cases": None, "kind": kind, "verdict": verdict, "evidence_key": "CONFIRMED", "cells": [], "calc": calc or [],
            "instances": 9}


def test_ratio_card_uses_the_shared_structure_with_percent_values_and_the_filing_precision():
    from backend.error_improvement import rule_cards as rc
    from decimal import Decimal
    ev = {"lhs_value": Decimal("0.06"), "rhs_value": Decimal("0.0599")}
    v = rc._compact_view(_card("weighted_average", calc=[("Reported value", "0.06"), ("Recalculated from its components", "0.0599")]),
                         [], _located(), rc.cell_money, _parse(_WAVG), [], None, ev)
    assert [k[1] for k in v["kv"]] == ["6.00%", "5.99%", "0.01%"]
    assert v["why"] == "The filing rounds 0.0599 to 0.06 (2 decimal places), but the rule checks at 4. Report at least 4 decimal places."
    assert v["steps"][0] == "Verify each amount and rate pair against the source data." and v["breakdown"]["kind"] == "operands"
    assert "first failing case; the rule fails in 9 cases" in v["breakdown"]["note"]


def test_missing_workbook_and_template_do_not_crash_the_card():
    from backend.error_improvement import rule_cards as rc
    v = rc._compact_view(_card("weighted_average"), [], _located(), rc.cell_money, _parse(_WAVG), [], None, None)
    assert v["breakdown"]["groups"][0]["items"][1]["label"].startswith("Amount 1")


def test_non_calculation_rules_keep_their_own_format():
    from backend.error_improvement import rule_cards as rc
    for kind in ("count", "mandatory", "conditional", "unknown"):
        v = rc._compact_view(_card(kind), [], _located(), rc.cell_money, _parse(_WAVG), [], None, None)
        assert v["breakdown"] is None, kind


def test_ab47_style_calculated_cell_block_is_kept_not_replaced():
    from backend.error_improvement import rule_cards as rc
    from types import SimpleNamespace as N
    bd = {"a1": "AB47", "status": "ok", "consistent": True, "now": "0", "groups": [{"items": [{"state": "zero"}]}]}
    ci = {"a1": "AB47", "sheet": "Ind", "breakdown": bd, "cur": 0, "need": 1, "multiplier": 1, "unit": "INR"}
    located = {"V1": [_flc("V1", "A", "1450000000", addr=_addr("Sec8", "AC16", 1450000000))],
               "V2": [_flc("V2", "A", "0", addr=_addr("Ind", "AB47", 0))]}
    v = rc._compact_view(_card("equality"), [N(facts={"culprit_info": [ci]})], located, rc.cell_money, _parse("$V1 = $V2"), [], None, None)
    assert v["breakdown"] is bd and v["wrong"] == "These two values must be equal, but they do not match."


# ── one comparison table for every calculation card (Sheet Name | Cell | Value) ─────────────────────────────────
_SUM = "$V1 = sum($V2)"


def _sum_located(found=10, expected=10):
    cells = [("B3", 4172), ("B4", 4491), ("B5", 8498), ("B6", 8852), ("B7", 5791), ("B8", 7984), ("B9", 3051), ("B10", 8429),
             ("B11", 2228), ("B12", 7923)]
    v2 = [_flc("V2", "Exposure", str(v), "INR", "0", _addr("S", a1, v) if i < found else None) for i, (a1, v) in enumerate(cells[:expected])]
    return {"V1": [_flc("V1", "Exposure", "70000000", "INR", "0", _addr("S", "B13", 70000000))], "V2": v2}


def _sum_card(calc_l="₹70,000,000", calc_r="₹61,419"):
    return _card("aggregate", calc=[("Left side", calc_l), ("Right side", calc_r), ("Difference", "₹69,938,581")])


def _sum_ev(n=10):
    from decimal import Decimal
    return {"lhs_value": Decimal(70000000), "rhs_value": Decimal(61419), "fact_counts": {"V1": 1, "V2": n}, "missing_vars": []}


def _sum_view(located, ev, comp=None):
    from backend.error_improvement import rule_cards as rc
    return rc._compact_view(_sum_card(), [], located, rc.cell_money, comp or _parse(_SUM), [], None, ev)


def test_total_card_shows_the_reported_cell_and_the_sum_with_a_difference_that_matches():
    v = _sum_view(_sum_located(), _sum_ev())
    rows = {k[0]: k[1] for k in v["kv"]}
    assert list(v["kv_cells"].values()) == [("S", "B13")]                               # the sheet table holds only cells of the sheet
    assert [k[0] for k in v["kv"]][1].startswith("Sum of B3:B12")                        # the total is one of the figures listed below it
    assert [k[1] for k in v["kv"]] == ["₹70,000,000", "₹61,419", "₹69,938,581"]
    assert v["warnings"] == []
    assert "₹70,000,000" in v["wrong"] and "₹61,419" in v["wrong"]
    assert v["why"] == ""                                                                # the headline already says it: said once, not twice
    b = v["breakdown"]
    assert [i["cell"] for i in b["groups"][0]["items"]] == ["B13"] + [f"B{n}" for n in range(3, 13)]   # all 10 components, not B3 only
    assert b["unlocated"] == 0 and rows["Difference"] == "₹69,938,581"


def test_total_card_with_missing_components_never_presents_a_partial_sum_as_the_total():
    v = _sum_view(_sum_located(found=7), _sum_ev())
    kv = {k[0]: k[1] for k in v["kv"]}
    calc_row = next(k for k in v["kv"] if k[0].endswith("Sum of B3:B9"))
    assert calc_row[1] == "₹61,419"                                                      # the rule's own value, not the located sum
    part = next(k for k in v["kv"] if k[0] == "Located cells only (7 of 10)")
    assert part[0] not in v["kv_cells"] and part[1] == "₹42,839"                       # 4172+4491+8498+8852+5791+7984+3051
    assert any("3 of 10 components of the calculated value could not be located" in w for w in v["warnings"])
    assert any("not the full total" in w for w in v["warnings"])
    assert next(k for k in v["kv"] if k[0] == "Difference")[1] == "₹69,938,581"          # difference stays the rule's own
    assert v["breakdown"]["unlocated"] == 3 and "3 could not be located" in v["breakdown"]["status_sub"]
    assert not any(k[2] == "bad" and "Sum" in k[0] for k in v["kv"])


def test_single_cell_comparison_shows_both_cells_and_the_rules_difference():
    from decimal import Decimal
    located = {"V1": [_flc("V1", "A", "100", "INR", "0", _addr("S", "B13", 100))], "V2": [_flc("V2", "A", "60", "INR", "0", _addr("S", "B3", 60))]}
    ev = {"lhs_value": Decimal(100), "rhs_value": Decimal(60), "fact_counts": {"V1": 1, "V2": 1}, "missing_vars": []}
    from backend.error_improvement import rule_cards as rc
    v = rc._compact_view(_card("equality", calc=[("Left side", "₹100"), ("Right side", "₹60"), ("Difference", "₹40")]), [], located,
                         rc.cell_money, _parse("$V1 = $V2"), [], None, ev)
    assert list(v["kv_cells"].values()) == [("S", "B13"), ("S", "B3")]
    assert [k[1] for k in v["kv"]] == ["₹100", "₹60", "₹40"]


def test_cell_ranges_are_compressed_only_when_consecutive():
    from backend.error_improvement import calc_view as cv
    assert cv.cell_ref([("S", f"K{n}") for n in range(3, 13)]) == ("S", "K3:K12")
    assert cv.cell_ref([("S", c) for c in ("B13", "C13", "D13")]) == ("S", "B13:D13")
    assert cv.cell_ref([("S", "B3"), ("S", "B5")]) == ("S", "B3, B5")                    # a gap is listed, not hidden by a range
    assert cv.cell_ref([("S", "B3"), ("T", "B4")])[0] == "Several sheets"


def test_calculated_cell_formula_is_used_only_when_it_is_built_from_the_cells_the_rule_adds():
    from backend.error_improvement import rule_cards as rc
    bd = {"groups": [{"items": [{"cell": "K3"}, {"cell": "K4"}]}], "formula": "K13 = SUM(K3:K4)"}
    same = {"V1": [_flc("V1", "A", "1", addr=_addr("S", "K13", 1))], "V2": [_flc("V2", "A", "1", addr=_addr("S", "K3", 1))],
            "V3": [_flc("V3", "A", "1", addr=_addr("S", "K4", 1))]}
    other = {"V1": [_flc("V1", "A", "1", addr=_addr("S", "K13", 1))], "V2": [_flc("V2", "A", "1", addr=_addr("S", "B13", 1))]}
    assert rc._bd_matches(bd, "K13", same) and not rc._bd_matches(bd, "K13", other)


# ── what the filer's workbook really holds, proven fixes, shared root causes, currency ─────────────────────────────
def _books(tmp_path):
    """A template whose row 6 holds formulas, and an upload where B6 and D6 were typed over (B6 wrongly: 100, not 60)."""
    import openpyxl
    tpl, up = openpyxl.Workbook(), openpyxl.Workbook()
    for wb_, typed in ((tpl, False), (up, True)):
        ws = wb_.active
        ws.title = "S"
        for r, (b, c) in enumerate(((10, 1), (20, 2), (30, 3)), start=3):
            ws[f"B{r}"], ws[f"C{r}"] = b, c
        ws["B6"] = 100 if typed else "=SUM(B3:B5)"
        ws["C6"] = 6 if typed else "=SUM(C3:C5)"
        ws["D6"] = 66 if typed else "=B6+C6"
        ws["F3"] = "=B3*2"                                                    # a formula that really is still a formula in the upload
    pt, pu = str(tmp_path / "template.xlsx"), str(tmp_path / "upload.xlsx")
    tpl.save(pt)
    up.save(pu)
    return pt, pu


def _wb(tmp_path):
    from backend.error_improvement.workbook import Workbook
    from backend.error_improvement.formula_graph import FormulaGraph
    from backend.error_improvement import cell_state as cs
    pt, pu = _books(tmp_path)
    wb = Workbook(pu)
    wb.formulas, wb.upload_formulas = FormulaGraph(path=pt), cs.upload_graph(pu)
    return wb


def test_cell_state_separates_formula_input_and_overwritten_template_formula(tmp_path):
    from backend.error_improvement import cell_state as cs
    wb = _wb(tmp_path)
    assert cs.state(wb, "S", 6, 1)["state"] == "overwritten"                 # B6: template formula, typed number uploaded
    assert cs.state(wb, "S", 6, 1)["template_formula"] == "=SUM(B3:B5)" and cs.state(wb, "S", 6, 1)["inspected"]
    assert cs.state(wb, "S", 3, 5)["state"] == "formula"                     # F3: still a formula in the upload
    assert cs.state(wb, "S", 3, 1)["state"] == "input"                       # B3: a plain input


def test_a_legacy_xls_is_never_said_to_hold_a_formula(tmp_path):
    from backend.error_improvement import cell_state as cs
    from types import SimpleNamespace as N
    old = tmp_path / "old.xls"
    old.write_bytes(b"\xd0\xcf\x11\xe0 not a zip")                           # a binary workbook: its formulas cannot be read
    assert cs.upload_graph(str(old)) is None
    from backend.error_improvement.formula_graph import FormulaGraph
    pt, _pu = _books(tmp_path)
    wb = N(formulas=FormulaGraph(path=pt), upload_formulas=None, is_template=False, value=lambda *a: 100)
    s = cs.state(wb, "S", 6, 1)
    assert s["state"] == "template_formula" and not s["inspected"]           # "the template says so", not "your workbook has it"


def test_replacement_is_the_template_formula_evaluated_on_the_filers_values(tmp_path):
    from backend.error_improvement import fix_check as fc
    from decimal import Decimal
    wb = _wb(tmp_path)
    f, v, why = fc.replacement(wb, "S", 6, 1)
    assert f == "=SUM(B3:B5)" and v == Decimal(60) and not why
    f, v, why = fc.replacement(wb, "S", 3, 1)                                # an input has no formula: nothing to restore
    assert v is None and why == "no formula"


def _rule(name, text, located):
    """An analysed item: (rule, expression, comparison, kind, [(instance, located, evaluation)])."""
    from types import SimpleNamespace as N
    from backend.error_improvement import explain_workbook as ew
    comp = ew.fx.parse_formula(text)
    by_var = {v: [str(lc.fact.value) for lc in lcs] for v, lcs in located.items()}
    ev = ew.fx.evaluate(comp, by_var)
    return (N(name=name), text, comp, "aggregate", [(None, located, ev)])


def _cell(var, a1, row, col, value, unit="QAR"):
    from types import SimpleNamespace as N
    addr = N(sheet="S", a1=a1, row=row, col=col, workbook_value=value, multiplier=1)
    return N(fact=N(var=var, concept="Amount", value=str(value), unit=unit, decimal="INF"), addr=addr, res=N(status="CONFIRMED"), where="S!" + a1)


def _scenario(tmp_path):
    wb = _wb(tmp_path)
    r1 = _rule("R1", "$V1 = sum($V2)", {"V1": [_cell("V1", "B6", 6, 1, 100)],
                                          "V2": [_cell("V2", f"B{r}", r, 1, v) for r, v in ((3, 10), (4, 20), (5, 30))]})
    r2 = _rule("R2", "$V1 = $V2 + $V3", {"V1": [_cell("V1", "D6", 6, 3, 66)], "V2": [_cell("V2", "B6", 6, 1, 100)],
                                          "V3": [_cell("V3", "C6", 6, 2, 6)]})
    return wb, [r1, r2]


def test_fix_is_verified_by_evaluating_the_whole_rule_again(tmp_path):
    from backend.error_improvement import fix_check as fc
    from decimal import Decimal
    wb, (r1, _r2) = _scenario(tmp_path)
    _r, _e, comp, _k, [(_i, located, ev)] = r1
    ok = fc.verify(comp, located, ev, located["V1"][0], wb, Decimal(60))
    assert ok["passes"] and ok["verified"] and not ok["problems"]
    bad = fc.verify(comp, located, ev, located["V1"][0], wb, Decimal(61))   # a number that does not make the rule pass
    assert not bad["passes"] and not bad["verified"]


def test_fix_stays_unverified_when_an_operand_is_unplaced_or_the_evidence_conflicts(tmp_path):
    from backend.error_improvement import fix_check as fc
    from decimal import Decimal
    wb, (r1, _r2) = _scenario(tmp_path)
    _r, _e, comp, _k, [(_i, located, ev)] = r1
    located["V2"][1].addr = None                                              # an operand that could not be placed
    v = fc.verify(comp, located, ev, located["V1"][0], wb, Decimal(60))
    assert v["passes"] and not v["verified"] and any("could not be located" in p for p in v["problems"])
    wb, (r1, _r2) = _scenario(tmp_path)
    _r, _e, comp, _k, [(_i, located, ev)] = r1
    located["V2"][0].addr.workbook_value = 11                                 # the workbook disagrees with the error file
    v = fc.verify(comp, located, ev, located["V1"][0], wb, Decimal(60))
    assert not v["verified"] and v["conflicts"] == ["B3"] and any("disagree" in p for p in v["problems"])


def test_shared_root_cause_is_found_proven_and_linked_without_naming_any_rule(tmp_path):
    from backend.error_improvement import root_cause as rcs
    wb, analysed = _scenario(tmp_path)
    out = rcs.analyse(analysed, wb)
    assert set(out) == {"R1", "R2"}
    assert out["R1"]["role"] == "primary" and out["R2"]["role"] == "secondary" and out["R2"]["primary"] == "R1"
    assert out["R1"]["fix"]["a1"] == out["R2"]["fix"]["a1"] == "B6" and str(out["R1"]["fix"]["replacement"]) == "60.000000"
    assert out["R1"]["others"] == ["R2"] and out["R1"]["verified"] and out["R2"]["verified"]
    assert {c["a1"] for c in out["R2"]["consistent"]} == {"D6", "C6"}
    assert [c["after_fix"] for c in out["R2"]["consistent"] if c["a1"] == "D6"] == [True]    # D6 only looks wrong because of B6
    assert all(r["fix"]["a1"] != "B3" for r in out.values())                  # a plain input is never the one to change


def test_a_shared_cell_that_does_not_clear_a_rule_is_not_claimed_to_clear_it(tmp_path):
    from backend.error_improvement import root_cause as rcs
    wb, analysed = _scenario(tmp_path)
    r3 = _rule("R3", "$V1 = $V2", {"V1": [_cell("V1", "B6", 6, 1, 100)], "V2": [_cell("V2", "C3", 3, 2, 1)]})   # 60 would still not be 1
    out = rcs.analyse(analysed + [r3], wb)
    assert "R3" not in out and out["R1"]["not_cleared"] == ["R3"]


def test_no_root_cause_is_asserted_without_the_filers_own_formulas(tmp_path):
    from backend.error_improvement import root_cause as rcs
    wb, analysed = _scenario(tmp_path)
    wb.upload_formulas = None                                                 # a legacy .xls upload: only the template is known
    assert rcs.analyse(analysed, wb) == {}                                     # previous behaviour is kept, nothing is asserted


def _rc_text(tmp_path, name):
    from backend.error_improvement import root_cause as rcs
    from backend.error_improvement import rule_cards as rc
    from backend.error_improvement import calc_view as cv
    wb, analysed = _scenario(tmp_path)
    out = rcs.analyse(analysed, wb)
    _r, _e, comp, _k, [(_i, located, ev)] = next(a for a in analysed if a[0].name == name)
    rc._CURRENCY.set("QAR ")
    cmpd = cv.comparison(comp, located, ev, rc.money)
    return rc._rc_view(out[name], cmpd, rc.money, {"rule_name": name})


def test_primary_card_says_to_restore_the_formula_not_to_type_the_number(tmp_path):
    v = _rc_text(tmp_path, "R1")
    assert v["steps"][0] == "Restore the formula =SUM(B3:B5) in B6 instead of typing a number (it gives QAR 60)."
    assert "typed number (QAR 100)" in v["why"] and "Verified: with B6 set to QAR 60" in v["why"]
    assert v["safety"].startswith("Do not type a number into B6")
    assert v["related"] == ["Fixing B6 also clears R2 (each rule was evaluated again with B6 = QAR 60)."]


def test_secondary_card_points_at_the_shared_cause_and_leaves_the_consistent_cell_alone(tmp_path):
    v = _rc_text(tmp_path, "R2")
    assert "Fix B6 first" in v["steps"][0] and "R1" in v["steps"][0]
    assert "D6 (QAR 66) matches what its own formula =B6+C6 gives once B6 is corrected, so it does not look like the cause" in v["why"]
    assert v["safety"] == "Do not change D6 to match the sum; it is consistent with its own components."
    assert v["related"] == ["Same root cause as R1: B6."]


def test_currency_comes_from_the_facts_unit_and_unknown_is_said_not_guessed():
    from backend.error_improvement import currency as cu
    from backend.error_improvement import rule_cards as rc
    from decimal import Decimal
    assert cu.of_facts([_flc("V", "A", "1", "QAR").fact, _flc("V", "A", "2", "QAR").fact]) == "QAR"
    assert cu.of_facts([_flc("V", "A", "1", "QAR").fact, _flc("V", "A", "2", "INR").fact]) is None     # mixed: not guessed
    assert cu.of_facts([_flc("V", "A", "1", "pure").fact]) is None and cu.normalise("iso4217:qar") == "QAR"
    rc._set_currency({"V1": [_flc("V1", "A", "1", "QAR")]})
    assert rc.money(Decimal(70000000)) == "QAR 70,000,000"
    rc._set_currency({"V1": [_flc("V1", "A", "1", "INR")]})
    assert rc.money(Decimal(70000000)) == "₹70,000,000"
    assert rc._set_currency({"V1": [_flc("V1", "A", "1", "")]}) is False and rc.money(Decimal(5)) == "5"   # unknown: no symbol
    rc._set_currency({"V1": [_flc("V1", "A", "1", "INR")]})


def test_a_card_with_an_unknown_currency_says_so():
    from backend.error_improvement import rule_cards as rc
    located = _sum_located()
    for lcs in located.values():
        for lc in lcs:
            lc.fact.unit = ""
    v = rc._compact_view(_sum_card("70,000,000", "61,419"), [], located, rc.cell_money, _parse(_SUM), [], None, _sum_ev())
    assert any("currency could not be established" in w for w in v["warnings"]) and "₹" not in " ".join(k[1] for k in v["kv"])
    rc._set_currency({"V1": [_flc("V1", "A", "1", "INR")]})


# ── cell-location accuracy: precision-aware matching, verified value hits, ranked ambiguous hits, numbered sheet copies ──────────
def test_tolerance_follows_the_precision_the_fact_was_filed_to():
    from backend.error_improvement import fact_address as fa
    from decimal import Decimal
    assert fa.tolerance(Decimal("0.06"), "2") == Decimal("0.005")             # a rate filed to 2 places: half a unit of the last place
    assert fa.tolerance(Decimal("17775625211000"), "-3") == Decimal("17775.625211000")   # large amounts keep a wide, relative allowance
    assert fa.tolerance(Decimal("4172"), "INF") == Decimal("0.5")             # rupee amounts keep the old +-0.5
    assert fa.tolerance(Decimal("0.06"), None) == Decimal("0.005")            # a small number without decimals is no longer matched at +-0.5


def test_a_rate_no_longer_matches_every_cell_within_half():
    from backend.error_improvement import fact_address as fa
    near = fa.Address("L", "", "S", 1, 1, "c", 1, 0.0645)                     # filed 0.06 to 2 places: 0.0645 is that value
    far = fa.Address("L", "", "S", 1, 1, "c", 1, 0.4)                         # the old +-0.5 accepted this
    assert fa.value_matches(near, "0.06", "2") and not fa.value_matches(far, "0.06", "2")
    assert not fa.value_matches(far, "0.06")
    amount = fa.Address("L", "", "S", 1, 1, "c", 100000, 125.0)               # amounts: unchanged
    assert fa.value_matches(amount, "12500000", "-3") and not fa.value_matches(amount, "12500500", "2")


def test_value_hits_are_checked_against_the_cells_own_value(tmp_path):
    import openpyxl
    from backend.error_improvement import value_locator as vl
    from backend.error_improvement.workbook import Workbook
    book = openpyxl.Workbook()
    ws = book.active
    ws.title = "S"
    for r in range(1, 40):
        ws[f"A{r}"] = 0                                                       # a column of zeros
    ws["C3"], ws["C4"], ws["C5"] = 0.06, 0.0645, 0.4
    p = str(tmp_path / "w.xlsx")
    book.save(p)
    hits = vl.ValueLocator(Workbook(p)).hits("0.06", "2")
    assert {(h[1], h[2]) for h in hits if h[3] == 1} == {(3, 2), (4, 2)}       # the rate's own cells only
    assert not [h for h in hits if h[3] != 1]                                  # never the zeros reached by a 10^7 scaling


def test_several_cells_holding_the_value_are_ranked_by_the_mapping_row_label():
    from backend.error_improvement import fact_address as fa
    from types import SimpleNamespace as N
    meta = N(staging={("L", "C1"): "Total Advances_Amt"}, columns={"L": [("_Amt", "", "S")]})
    cands = [N(layout_id="L", cell_code="C1", sheet="S", col=3)]
    rows = {2: "Other", 5: "Total Advances", 9: "Other"}
    wb = N(value=lambda sh, r, c: rows.get(r) if c == 0 else None)
    hit = lambda r, c: N(sheet="S", row=r, col=c)                             # noqa: E731
    assert fa.rank_hits(meta, wb, cands, [hit(2, 3), hit(5, 3), hit(9, 3)]) == [hit(5, 3)] or \
        [(h.row, h.col) for h in fa.rank_hits(meta, wb, cands, [hit(2, 3), hit(5, 3), hit(9, 3)])] == [(5, 3)]
    rows[9] = "Total Advances"                                                # two rows carry the label: nothing is named
    assert fa.rank_hits(meta, wb, cands, [hit(2, 3), hit(5, 3), hit(9, 3)]) == []
    assert fa.rank_hits(meta, wb, cands, [hit(2, 3), hit(9, 3)])[0].row == 9   # one labelled hit among others is a clear winner
    assert fa.rank_hits(N(staging={}, columns={}), wb, cands, [hit(5, 3)]) == []   # no label from the mapping: no claim


def test_a_numbered_copy_of_a_sheet_uses_the_formulas_of_its_template_sheet(tmp_path):
    import openpyxl
    from backend.error_improvement.formula_graph import FormulaGraph
    book = openpyxl.Workbook()
    ws = book.active
    ws.title = "CR-QCCP"
    ws["D15"], ws["D16"], ws["D17"] = "=D16+D17", 1, 2
    p = str(tmp_path / "t.xlsx")
    book.save(p)
    g = FormulaGraph(path=p)
    assert g.formula("CR-QCCP (1)", 15, 3) == "=D16+D17" and g.formula("CR-QCCP (10)", 15, 3) == "=D16+D17"
    assert g.precedents("CR-QCCP (1)", 15, 3) == {(16, 3), (17, 3)}
    assert g.formula("Other (1)", 15, 3) is None                              # an unrelated sheet is not borrowed from


def test_a_mapped_cell_that_disagrees_with_the_filing_is_named_as_such():
    from backend.error_improvement import explain_workbook as ew
    from backend.error_improvement import fact_address as fa
    from types import SimpleNamespace as N
    a = fa.Address("L", "", "Term Deposit", 8, 4, "c", 1, 0.07)
    lc = N(addr=None, dynamic=False, fact=N(concept="Rate", value="0.06"), res=fa.Resolved("UNCONFIRMED", [a], "x"))
    why = ew.why_unlocated(lc, None)
    assert "mapped cell Term Deposit!E8 holds 0.07, but the filing reports 0.06" in why


# ── an unreported total over many sheets; which upload an error file came from ─────────────────────────────────────────────────
def _entry_books(tmp_path, extra_reader=True):
    """Template and upload with entry sheets 'S (1)' 'S (2)'; a totals sheet sums D15 of each; a decoy reads only the first."""
    import openpyxl
    book = openpyxl.Workbook()
    book.active.title = "Totals"
    for n, v in ((1, 10), (2, 20)):
        ws = book.create_sheet(f"S ({n})")
        ws["D15"] = v
    book["Totals"]["D15"] = "=SUM('S (1)'!D15+'S (2)'!D15)"
    if extra_reader:
        book.create_sheet("Decoy")["D15"] = "='S (1)'!D15*2"
    p = str(tmp_path / "w.xlsx")
    book.save(p)
    return p


def _total_case(tmp_path, extra_reader=True, unlocated=False):
    from types import SimpleNamespace as N
    from backend.error_improvement import explain_workbook as ew
    from backend.error_improvement import fact_address as fa
    from backend.error_improvement.formula_graph import FormulaGraph
    from backend.error_improvement.workbook import Workbook
    p = _entry_books(tmp_path, extra_reader)
    wb = Workbook(p)
    graph = FormulaGraph(path=p)
    comp = ew.fx.parse_formula("$V1 = sum($V2)")
    v2 = []
    for n, v in ((1, 10), (2, 20)):
        a = None if (unlocated and n == 2) else fa.Address("L", "", f"S ({n})", 15, 3, "c", 1, v)
        v2.append(N(fact=N(concept="Exposure", value=str(v), unit="INR", decimal="INF"), addr=a, res=N(status="CONFIRMED")))
    v1 = N(fact=N(concept="", value="0", unit="", decimal=""), addr=None, res=N(status="UNRESOLVED"))
    return wb, graph, comp, {"V1": [v1], "V2": v2}


def test_an_unreported_total_over_many_sheets_is_placed_at_the_cell_that_reads_them_all(tmp_path):
    from backend.error_improvement import absent_operands as ao
    wb, graph, comp, located = _total_case(tmp_path)
    assert ao.resolve(located, comp, "", wb, graph) == 1
    a = located["V1"][0].addr
    assert (a.sheet, a.a1) == ("Totals", "D15")                                # the decoy reads only one of the two cells
    assert located["V1"][0].res.status == "INFERRED" and "sums all 2 cells" in located["V1"][0].res.note


def test_the_total_is_not_placed_when_it_is_not_unique_or_an_operand_is_unplaced(tmp_path):
    from backend.error_improvement import absent_operands as ao
    from types import SimpleNamespace as N
    wb, graph, comp, located = _total_case(tmp_path, unlocated=True)
    assert ao.resolve(located, comp, "", wb, graph) == 0 and located["V1"][0].addr is None      # an operand has no cell: no claim
    wb, graph, comp, located = _total_case(tmp_path)
    from backend.error_improvement import formula_graph
    wb.formulas = N(readable=lambda: True, cross_dependents=lambda *a: {("Totals", 15, 3), ("Decoy", 15, 3)},
                    signed_refs=lambda *a: None, precedents=lambda *a: set(), dependents=lambda *a: set())
    assert ao.resolve(located, comp, "", wb, wb.formulas) == 0                  # two cells read both: not named
    assert formula_graph.FormulaGraph.cross_dependents is not None


def _fact_item(value, status, addr=True, concept="Exposure"):
    from types import SimpleNamespace as N
    return N(fact=N(concept=concept, value=value), addr=object() if addr else None, res=N(status=status))


def test_upload_evidence_counts_confirmed_and_contradicted_facts_but_not_zeros_or_unreported_operands():
    from backend.error_improvement import explain
    items = [_fact_item("100", "CONFIRMED"), _fact_item("200", "CONFIRMED"), _fact_item("0", "CONFIRMED"),
             _fact_item("300", "UNCONFIRMED", addr=False), _fact_item("5", "UNCONFIRMED", addr=False, concept=""),
             _fact_item("0", "UNCONFIRMED", addr=False), _fact_item("7", "INFERRED")]
    analysed = [(None, None, None, None, [(None, {"V1": items[:4], "V2": items[4:]}, None)])]
    assert explain._evidence(analysed) == (2, 1)


def test_the_upload_is_named_by_its_date_and_time():
    from backend.error_improvement import explain
    assert explain._upload_stamp(r"R\DataBase\2036\UploadedFiles\21-11-25-15-15-12\LRBase.xlsx", r"R\DataBase\2036") == "21 Nov 2025 15:15"
