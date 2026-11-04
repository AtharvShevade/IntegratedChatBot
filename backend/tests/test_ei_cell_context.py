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


def test_a_descriptive_header_is_preferred_to_a_bare_code(tmp_path):
    def build(ws):
        ws["A1"] = "Part C - Rates"
        ws["B3"], ws["C3"] = "Item", "Rate"
        ws["B4"], ws["C4"] = "Y110", "X170"
        ws["B5"], ws["C5"] = "USD", 4.3456
    assert cc.describe(_wb(tmp_path, build), "T", "C5")["column"] == "Rate"


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
