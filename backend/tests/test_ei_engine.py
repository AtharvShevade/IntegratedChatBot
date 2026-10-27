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
    assert "weighted average of the amounts and rates" in v["why"] and "filed to 2 decimal places" in v["why"]
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
