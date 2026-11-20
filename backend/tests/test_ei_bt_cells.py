"""The validator's backtracking record as the primary location: joined to the report's facts, turned into one cell, never guessed."""
import os
import sys
from types import SimpleNamespace as NS

from backend.error_improvement import bt_cells as bt           # noqa: E402
from backend.error_improvement import error_html as eh         # noqa: E402
from backend.error_improvement import fact_address as fa       # noqa: E402
from backend.error_improvement import explain_workbook as ew   # noqa: E402


def _lc(value="5", extra=None, addr=None):
    fact = eh.Fact("V1", "Concept", value, "ctx", decimal="2", extra=extra if extra is not None else {"Excel SheetName": "S", "Cell Code": "Y10_X20"})
    lc = ew.Located(fact, fa.Resolved("UNRESOLVED", []))
    if addr:
        lc.res, lc.addr = fa.Resolved("CONFIRMED", [addr]), addr
    return lc


def _cell(row, col, value, code="Y10_X20"):
    a = fa.Address("L", "Layout1", "S", row, col, code, 1, value)
    return a


def _apply(monkeypatch, lc, cands, template=False):
    monkeypatch.setattr(fa, "candidates", lambda *a, **k: cands)
    return bt.apply({"V1": [lc]}, NS(), NS(is_template=template)), lc


def test_the_cell_the_backtracking_record_names_is_the_location_and_the_workbook_confirms_it(monkeypatch):
    n, lc = _apply(monkeypatch, _lc("5"), [_cell(4, 1, 5), _cell(9, 3, 7, "Y99_X20"), _cell(4, 1, 5)])
    assert n == 1 and lc.bt and lc.res.status == "CONFIRMED" and lc.where == "S!B4" and not getattr(lc, "bt_other", "")


def test_a_workbook_that_disagrees_keeps_the_backtracking_cell_but_is_not_called_confirmed(monkeypatch):
    n, lc = _apply(monkeypatch, _lc("5"), [_cell(4, 1, 99)])
    assert lc.bt and lc.res.status == "MAPPED" and lc.where == "S!B4"


def test_our_own_choice_that_differs_is_recorded_and_the_backtracking_cell_wins(monkeypatch):
    mine = _cell(4, 3, 5, "Y77_X20")
    n, lc = _apply(monkeypatch, _lc("5", addr=mine), [_cell(4, 1, 5)])
    assert lc.where == "S!B4" and lc.bt_other == "S!D4"
    assert bt.card_source({"V1": [lc]}) == (True, ["S!B4 (BT) vs S!D4 (our search)"])


def test_nothing_is_placed_without_a_sheet_a_unique_cell_or_a_record(monkeypatch):
    for extra in ({}, {"DB TableName": "T", "Cell Code": "Y10_X20"}):                # a database table is not a sheet
        n, lc = _apply(monkeypatch, _lc(extra=extra), [_cell(4, 1, 5)])
        assert n == 0 and not getattr(lc, "bt", False) and lc.addr is None
    n, lc = _apply(monkeypatch, _lc(), [_cell(4, 1, 5), _cell(8, 1, 5)])               # the code fits two cells: not guessed
    assert n == 0 and lc.addr is None
    n, lc = _apply(monkeypatch, _lc(), [_cell(4, 1, 5, "Y99_X99")])                    # no candidate carries the code
    assert n == 0


def test_a_template_basis_is_mapped_never_confirmed(monkeypatch):
    n, lc = _apply(monkeypatch, _lc("5"), [_cell(4, 1, None)], template=True)
    assert lc.res.status == "MAPPED" and lc.addr.workbook_value == 5.0


def test_the_card_is_backtracking_sourced_only_when_every_cell_is(monkeypatch):
    a, b = _lc(), _lc()
    a.bt, a.addr = True, _cell(4, 1, 5)
    b.addr = _cell(5, 1, 5)
    assert bt.card_source({"V1": [a], "V2": [b]})[0] is False and bt.card_source({"V1": [a]}) == (True, []) and bt.card_source({})[0] is False


def test_the_backtracking_file_beside_a_report_is_joined_by_rule_context_and_value(tmp_path, monkeypatch):
    rep, bt_file = tmp_path / "X_Instance.html", tmp_path / "X_BTDetails.html"
    rep.write_text("r")
    bt_file.write_text("b")
    extra = {"Excel SheetName": "S", "Cell Code": "Y10_X20"}
    mk = lambda facts: [eh.Rule("R1", "e", 1, [eh.Instance("t", facts)])]                              # noqa: E731
    mine = [eh.Fact("V1", "C", "1,234.50", "ctx"), eh.Fact("V2", "C", "9", "ctx2")]
    theirs = [eh.Fact("V1", "", "1234.50", "ctx", extra=extra), eh.Fact("V2", "", "9", "ctx2", extra=extra),
              eh.Fact("V2", "", "9", "ctx2", extra={"Excel SheetName": "S", "Cell Code": "OTHER"})]
    monkeypatch.setattr(eh, "parse_rules", lambda html: mk(theirs))
    rules = mk(mine)
    assert bt.attach(rules, str(rep)) == 1                                  # V2 fits two different BT rows: left alone
    assert mine[0].extra == extra and mine[1].extra == {}
    assert bt.attach(mk(mine), str(tmp_path / "Y_Instance.html")) == 0     # no BT file beside it
    assert bt.attach(mk(mine), str(bt_file)) == 0                          # the BT file itself is not joined to itself


def test_a_database_table_in_the_backtracking_record_names_its_layouts_through_tabelmapping(tmp_path, monkeypatch):
    (tmp_path / "TabelMapping.xml").write_text('<Document><Row PriID="1" TableName="CIMS_FILING_INFO"/><Row PriID="3|8" TableName="CIMS_X_TABLE_1"/></Document>',
                                               encoding="utf-8")
    meta = NS(folder=str(tmp_path))
    assert bt.table_layouts(meta, "CIMS_X_TABLE_1") == {"3", "8"} and bt.table_layouts(meta, "cims_filing_info") == {"1"}
    assert bt.table_layouts(meta, "NOPE") == set() and bt.table_layouts(NS(folder=str(tmp_path / "none")), "CIMS_X_TABLE_1") == set()
    db = {"DB TableName": "CIMS_X_TABLE_1", "Cell Code": "Y10_X20"}
    other = fa.Address("9", "Layout9", "S", 4, 1, "Y10_X20", 1, 5)            # same code in a layout the table does not serve
    mine = fa.Address("3", "Layout3", "S", 6, 2, "Y10_X20", 1, 5)
    monkeypatch.setattr(fa, "candidates", lambda *a, **k: [other, mine])
    lc = _lc("5", extra=db)
    assert bt.apply({"V1": [lc]}, meta, NS(is_template=False)) == 1 and lc.where == "S!C6" and lc.res.status == "CONFIRMED"
    lc2 = _lc("5", extra={"DB TableName": "UNKNOWN_TABLE", "Cell Code": "Y10_X20"})
    assert bt.apply({"V1": [lc2]}, meta, NS(is_template=False)) == 0 and lc2.addr is None
