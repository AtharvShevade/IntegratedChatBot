"""The table title and column header shown beside a cell. Small workbooks built in the test: no return data."""
import os
import sys

import openpyxl

from backend.error_improvement import cell_context as cc           # noqa: E402
from backend.error_improvement import rule_cards as rc             # noqa: E402
from backend.error_improvement.workbook import Workbook       # noqa: E402


def _wb(tmp_path, build):
    book = openpyxl.Workbook()
    ws = book.active
    ws.title = "T"
    build(ws)
    p = tmp_path / "w.xlsx"
    book.save(p)
    return Workbook(str(p))


def test_the_column_header_and_table_title_are_read_from_the_sheet(tmp_path):
    def build(ws):
        ws["A1"] = "Table 3: Group exposure"
        ws["A3"], ws["B3"], ws["C3"] = "Item", "Amount", "Percentage of exposure"
        ws["A4"], ws["B4"], ws["C4"] = "Group A", 100, 0.1254
        ws["A5"], ws["B5"], ws["C5"] = "Group B", 200, 0.1096
    wb = _wb(tmp_path, build)
    assert cc.describe(wb, "T", "C5") == {"table": "Table 3: Group exposure", "column": "Percentage of exposure"}
    assert cc.describe(wb, "T", "B4")["column"] == "Amount"


def test_the_headers_above_the_cell_are_read_as_a_path_top_to_bottom(tmp_path):
    def build(ws):
        ws["A1"] = "Part C - Rates"
        ws["B3"], ws["C3"] = "Item", "Rate"
        ws["B4"], ws["C4"] = "Y110", "X170"
        ws["B5"], ws["C5"] = "USD", 4.3456
    assert cc.describe(_wb(tmp_path, build), "T", "C5")["column"] == "Rate > X170"


def test_a_merged_group_heading_covers_every_column_it_spans(tmp_path):
    def build(ws):
        ws["A1"] = "Table 2: Details of transactions"
        ws["A3"], ws["C3"], ws["E3"] = "Item", "Using Mobile App", "Using Internet"
        ws.merge_cells("C3:D3")
        ws.merge_cells("E3:F3")
        ws["A4"], ws["C4"], ws["D4"], ws["E4"], ws["F4"] = "Row", "Volume", "Value", "Volume", "Value"
        ws["A5"], ws["C5"], ws["D5"], ws["E5"], ws["F5"] = "Code", "X380", "X390", "X400", "X410"
        ws["A6"], ws["C6"], ws["D6"], ws["E6"], ws["F6"] = "Y010", 5, 6, 7, 8
        ws["A7"], ws["C7"], ws["D7"], ws["E7"], ws["F7"] = "Y020", 5, 6, 7, 8
    wb = _wb(tmp_path, build)
    assert cc.describe(wb, "T", "C7") == {"table": "Table 2: Details of transactions", "column": "Using Mobile App > Volume > X380"}
    assert cc.describe(wb, "T", "D7")["column"] == "Using Mobile App > Value > X390"       # the second column of the merge
    assert cc.describe(wb, "T", "F6")["column"] == "Using Internet > Value > X410"


def test_a_bare_column_letter_does_not_hide_the_heading_above_it(tmp_path):
    def build(ws):
        ws["A1"] = "Section 8: Sectoral Credit"
        ws["A3"], ws["C3"] = "Sector", "Total Term Loans Sanctioned till date in the FY"
        ws["D3"] = "Total Term Loans Disbursed"
        ws["C4"], ws["D4"] = "Y", "Z"                                    # a row of column letters, as the sheet carries them
        ws["A5"], ws["C5"] = "Agriculture", 10
    assert cc.describe(_wb(tmp_path, build), "T", "C5")["column"] == "Total Term Loans Sanctioned till date in the FY > Y"


def test_a_code_header_is_used_when_there_is_nothing_better(tmp_path):
    def build(ws):
        ws["A1"] = "Part C - Rates"
        ws["B4"], ws["C4"] = "Item", "X170"
        ws["B5"], ws["C5"] = "USD", 4.3456
    assert cc.describe(_wb(tmp_path, build), "T", "C5") == {"table": "Part C - Rates", "column": "X170"}


def test_nothing_is_shown_when_the_sheet_does_not_make_it_clear(tmp_path):
    def build(ws):
        ws["A1"], ws["B1"] = 5, 6
        ws["A2"], ws["B2"] = 7, 8
    wb = _wb(tmp_path, build)
    assert cc.describe(wb, "T", "B2") == {"table": "", "column": ""}
    assert cc.describe(wb, "Nope", "B2") == {"table": "", "column": ""}       # no such sheet
    assert cc.describe(wb, "T", "Sum of B3:B12") == {"table": "", "column": ""}   # not a cell address


def test_the_table_has_a_sheet_table_and_column_only_when_known():
    v = {"kv_cells": {"a": ("S", "B3"), "b": ("S", "B4")}, "kv_where": {}}
    assert rc.kv_columns(v) == ["Sheet Name", "Cell", "Value"]
    v["kv_where"] = {"a": {"table": "Table 3", "column": ""}}
    assert rc.kv_columns(v) == ["Sheet Name", "Table", "Cell", "Value"]
    v["kv_where"] = {"a": {"table": "Table 3", "column": "Amount"}}
    assert rc.kv_columns(v) == ["Sheet Name", "Table", "Column", "Cell", "Value"]
    assert rc._kv_row(v, "a", "₹5") == ["S", "Table 3", "Amount", "B3", "₹5"]
    assert rc._kv_row(v, "b", "₹6") == ["S", "", "", "B4", "₹6"]
    assert rc.kv_columns({"kv_cells": {}}) == []


# ── the taxonomy's own table title ────────────────────────────────────────────────────────────────────────────────
def test_table_titles_are_read_from_the_taxonomy_and_a_later_version_wins(tmp_path):
    from backend.error_improvement import table_titles as tt
    for ver, head in (("1.0.0", "Old title"), ("1.1.0", "C1: Data &amp; Rates")):
        d = tmp_path / "reports" / "x" / ver
        d.mkdir(parents=True)
        (d / "x-table-TableModel.xml").write_text(f'<tableModel><tableSet label="S"><table label="S_Layout1" header="{head}"/></tableSet></tableModel>',
                                                  encoding="utf-8")
    assert tt.load(str(tmp_path)) == {"S_Layout1": "C1: Data & Rates"}
    assert tt.load(str(tmp_path / "missing")) == {}


def test_the_taxonomy_title_is_preferred_and_the_sheet_text_is_the_fallback(tmp_path):
    from types import SimpleNamespace as NS
    from backend.error_improvement import fact_address as fa

    def build(ws):
        ws["A1"] = "Sheet's own heading"
        ws["B3"], ws["C3"] = "Item", "Rate"
        ws["B4"], ws["C4"] = "USD", 4.3
    wb = _wb(tmp_path, build)
    view = {"kv_cells": {"a": ("T", "C4")}}
    located = {"V1": [NS(addr=fa.Address("L", "T_Layout1", "T", 4, 2, "c", 1), res=NS(addresses=[]))]}
    assert rc._kv_where(view, wb, located)["a"] == {"table": "Sheet's own heading", "column": "Rate"}       # no titles: the sheet's text
    wb.table_titles = {"T_Layout1": "C1: The taxonomy title"}
    assert rc._kv_where(view, wb, located)["a"] == {"table": "C1: The taxonomy title", "column": "Rate"}
    assert rc._kv_where(view, wb, {})["a"]["table"] == "Sheet's own heading"                              # a cell with no known layout


def test_a_confirmed_location_says_so_and_the_other_states_keep_their_wording():
    assert rc._EVIDENCE_SHORT["CONFIRMED"] == "workbook verified" and rc._EVIDENCE_SHORT["INFERRED"] == "inferred from the workbook"
    assert "Location evidence" in rc.card_to_text({"view": {"title": "t", "subtitle": "s", "wrong": "w", "kv": [], "why": "y", "steps": ["a"], "fix": "f",
                                                            "groups": [], "footer": "Location evidence: workbook verified."}})


def test_a_cell_with_no_known_layout_is_placed_by_the_ranges_of_the_returns_layouts():
    from backend.error_improvement import table_titles as tt
    meta = NS_meta = type("M", (), {})()
    meta.layouts = {"1": "A_Layout1", "2": "A_Layout2", "3": "B_Layout1"}
    meta.sheets = {"1": [("A", "A9:C9")], "2": [("A", "A15:E50000")], "3": [("B", "A9:E50000"), ("B", "A12:C12")]}
    ranges = tt.layout_ranges(meta)
    assert tt.layout_at(ranges, "A", "B9") == "A_Layout1" and tt.layout_at(ranges, "A", "E20") == "A_Layout2"
    assert tt.layout_at(ranges, "A", "B12") == ""                      # in no layout's range
    assert tt.layout_at(ranges, "B", "B12") == "B_Layout1"             # two ranges of ONE layout still name one layout
    assert tt.layout_at(ranges, "A", "Sum of B3") == "" and tt.layout_at([], "A", "B9") == ""


def test_a_title_line_with_a_unit_note_is_the_table_name_not_a_column_heading(tmp_path):
    def build(ws):
        ws["A1"] = "Term Deposit-Amount wise"
        ws.merge_cells("A1:G1")
        ws["A3"], ws["G3"] = "Table I- Classification Term Deposit: Amount-wise (Domestic)", "(Rs. Lakh)"
        ws.merge_cells("A3:F3")
        ws["A4"], ws["B4"], ws["D4"] = "Tenor", "Up to 28 days", "29 days and upto 90 days"
        ws.merge_cells("B4:C4")
        ws.merge_cells("D4:E4")
        ws["A5"], ws["B5"], ws["C5"], ws["D5"], ws["E5"] = "Size", "Total Outstanding", "Weighted Average Interest Rate (%)", "Total Outstanding", "Rate"
        ws["A6"], ws["B6"], ws["C6"], ws["D6"], ws["E6"] = "Below Rs. 1 crore", 100, 0.06, 200, 0.07
        ws["A8"] = "Term Deposit-Amount wise (Domestic)"
        ws["A9"] = "Table II- Classification of Term Deposit - Interest Rate"
    wb = _wb(tmp_path, build)
    assert cc.describe(wb, "T", "C6") == {"table": "Table I- Classification Term Deposit: Amount-wise (Domestic)",
                                          "column": "Up to 28 days > Weighted Average Interest Rate (%)"}
    assert cc.describe(wb, "T", "E6")["column"] == "29 days and upto 90 days > Rate"


# ── the failing case a card explains ──────────────────────────────────────────────────────────────────────────────
def _finding(*statuses):
    from types import SimpleNamespace as N
    located = {f"V{i}": [N(addr=(object() if s else None), res=N(status=s or "UNCONFIRMED"), uncertain="")] for i, s in enumerate(statuses, 1)}
    return (None, located, None)


def test_a_case_whose_values_are_placed_leads_when_the_first_case_cannot_be_placed():
    first, second, third = _finding(None, None, "CONFIRMED"), _finding("CONFIRMED", "INFERRED", "CONFIRMED"), _finding("CONFIRMED", "MAPPED", "CONFIRMED")
    out, moved = rc._best_first([first, second, third])
    assert moved and out[0] is second and out[1:] == [first, third]                       # the earliest of the best, the others keep their order
    same, moved = rc._best_first([second, first])
    assert not moved and same[0] is second                                                # the first case already leads: nothing changes
    assert rc._best_first([first]) == ([first], False)


def test_a_weak_match_does_not_count_like_a_settled_cell():
    from types import SimpleNamespace as N
    weak = _finding("LIKELY", "CONFIRMED")
    firm = _finding("CONFIRMED", "CONFIRMED")
    assert rc._coverage(weak) < rc._coverage(firm) == 1.0
    out, moved = rc._best_first([weak, firm])
    assert moved and out[0] is firm
    assert "one of the failing cases" in rc._CASE_WORD({"case_moved": True}) and rc._CASE_WORD({}) == "the first failing case"


def test_a_blank_row_between_stacked_header_rows_does_not_end_the_path(tmp_path):
    def build(ws):
        ws["A1"] = "C1: Data on External Benchmark based Lending Rate"
        ws.merge_cells("A1:H1")
        ws["A3"], ws["C3"], ws["D3"] = "Sector", "Agriculture", "Infrastructure"
        ws["C4"], ws["D4"] = "X010", "X040"                                  # row 5 is blank
        ws["A6"], ws["C6"], ws["D6"] = "External Benchmark", "Repo", "Other"
        ws["A7"], ws["C7"], ws["D7"] = "Benchmark Rate", 0.1, 0.13
    wb = _wb(tmp_path, build)
    assert cc.describe(wb, "T", "D7") == {"table": "C1: Data on External Benchmark based Lending Rate", "column": "Infrastructure > X040 > Other"}
    assert cc.describe(wb, "T", "C7")["column"] == "Agriculture > X010 > Repo"


def test_label_value_pairs_are_a_form_not_a_header_and_long_headings_are_kept(tmp_path):
    def build(ws):
        ws["A1"], ws["B1"] = "Name of the entity", "ABC Bank"
        ws["A2"], ws["B2"] = "Reporting date", "2023-09-09"
        ws["A3"], ws["B3"] = "Audited", "Yes"
        ws["A4"], ws["B4"] = "Remarks", "none"
    assert cc.describe(_wb(tmp_path, build), "T", "B4")["column"] == ""          # nothing is claimed for a form

    def build2(ws):
        ws["A1"] = "Part A: Sectoral Analysis"
        ws["A3"], ws["C3"] = "Sector", "Total Term Loans Sanctioned till date in the FY (April to Date)"
        ws["C4"], ws["D4"] = "Y", "Z"
        ws["A5"], ws["C5"] = "Agriculture", 10
    assert cc.describe(_wb(tmp_path, build2), "T", "C5")["column"] == "Total Term Loans Sanctioned till date in the FY (April to Date) > Y"


def test_the_filed_figure_and_the_workbook_cell_are_both_shown_only_when_they_differ():
    from backend.error_improvement import calc_view as cv
    from decimal import Decimal as D
    from types import SimpleNamespace as N
    pct = lambda d: f"{d * 100:.2f}%"                                                       # noqa: E731
    var = lambda name: N(variables=lambda: [name], kind="var", signed_variables=lambda: [(name, 1)])     # noqa: E731
    mk = lambda filed, held, mult=1: N(fact=N(value=str(filed), unit="PURE", decimal="2", concept="C"),
                                       addr=N(sheet="S", a1="C19", workbook_value=held, multiplier=mult))
    comp = N(lhs=var("V1"), rhs=var("V2"), operator="=")
    ev = {"lhs_value": "0.06", "rhs_value": "0.0599"}
    out = cv.comparison(comp, {"V1": [mk("0.06", 0.0599)], "V2": [mk("0.0599", 0.0599)]}, ev, pct)
    rows = [(r["label"], r["value"]) for r in out["rows"]]
    assert ("S!C19", "5.99%") in rows and ("Filed in the return", "6.00%") in rows                 # the sheet's figure first, the filed one below
    assert [r["label"] for r in out["rows"]][0] == "S!C19" and out["rows"][-1]["label"] == "Difference"
    same = cv.comparison(comp, {"V1": [mk("0.06", 0.06)], "V2": [mk("0.0599", 0.0599)]}, ev, pct)
    assert not any(r["label"].startswith("Filed in the return") for r in same["rows"]) and same["rows"][0]["value"] == "6.00%"
    neg = cv.comparison(comp, {"V1": [mk("-0.46", -0.4556)], "V2": [mk("0.4556", 0.4556)]}, {"lhs_value": "0.46", "rhs_value": "0.4556"}, pct)
    assert ("S!C19", "45.56%") in [(r["label"], r["value"]) for r in neg["rows"]]                  # the rule's size, not a sign it dropped


def test_a_total_the_table_already_shows_is_not_repeated_and_filed_figures_are_named_only_when_several():
    from backend.error_improvement import calc_view as cv
    from types import SimpleNamespace as N
    pct = lambda d: f"{d * 100:.2f}%"                                                       # noqa: E731
    var = lambda *names: N(variables=lambda: list(names), kind="var" if len(names) == 1 else "sum",       # noqa: E731
                           signed_variables=lambda: [(n, 1) for n in names])
    mk = lambda filed, held, a1="C12": N(fact=N(value=str(filed), unit="PURE", decimal="2", concept="C"),
                                         addr=N(sheet="S", a1=a1, workbook_value=held, multiplier=1))
    comp = N(lhs=var("V1"), rhs=var("V2", "V3"), operator="=")
    located = {"V1": [mk("0.06", 0.0592)], "V2": [mk("0.03", 0.03, "B1")], "V3": [mk("0.0292", 0.0292, "B2")]}
    out = cv.comparison(comp, located, {"lhs_value": "0.06", "rhs_value": "0.0592"}, pct)
    labels = [r["label"] for r in out["rows"]]
    assert labels == ["S!C12", "Filed in the return", "Difference"]                          # the 5.92% total repeats the cell's 5.92%: dropped
    out2 = cv.comparison(N(lhs=var("V1"), rhs=var("V2"), operator="="), {"V1": [mk("0.06", 0.0592)], "V2": [mk("0.07", 0.0699, "D5")]},
                         {"lhs_value": "0.06", "rhs_value": "0.07"}, pct)
    assert [r["label"] for r in out2["rows"]] == ["S!C12", "S!D5", "Filed in the return (C12)", "Filed in the return (D5)", "Difference"]
