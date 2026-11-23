"""DB-backed returns: reading XML_Query and finding the table cell behind a mapping row (no database needed)."""
import os

from backend.error_improvement import db_return as dr
from backend.error_improvement.db_source import DbReader, Reading, decrypt


def _folder(tmp_path, xml_query, tabel_mapping=""):
    (tmp_path / "XML_Query.xml").write_text(xml_query, encoding="utf-8")
    if tabel_mapping:
        (tmp_path / "TabelMapping.xml").write_text(tabel_mapping, encoding="utf-8")
    return str(tmp_path)


Q = """<Document>
 <Row QueryId="1000" QueryName="Filing" TemplateId="1" ProviderId="1003"><SelectQuery>Select DESCRIPTION as Description, VALUE as Val, CODE as Code, RDATE From CIMS_FILING_INFO Where TO_DATE(RDATE,'DD-MON-RR') = ## AND RETURN_CODE = '401'</SelectQuery></Row>
 <Row QueryId="1002" QueryName="PartA" TemplateId="3" ProviderId="1003"><SelectQuery>Select DESCRIPTION as DESCRIPTION, DESCRIPTION || '_X010' as CODE, NAME_X010 as VAL from CIMS_PART_A Where RDATE = ## UNION ALL Select DESCRIPTION as DESCRIPTION, DESCRIPTION || '_X020' as CODE, NAME_X020 as VAL from CIMS_PART_A Where RDATE = ##</SelectQuery></Row>
 <Row QueryId="1003" QueryName="Wide" TemplateId="4" ProviderId="1003"><SelectQuery>Select COUNTRY, SOVEREIGNS, TOTAL, RDATE FROM QCB_BREAK WHERE RDATE = ##</SelectQuery></Row>
 <Row QueryId="1004" QueryName="Excel" TemplateId="5" ProviderId="7"><SelectQuery>Select F1 As A From [Sheet1$A1:B5]</SelectQuery></Row>
</Document>"""
TM = """<Document><Row PriID="4" TableName="QCB_BREAK" PrimaryColumn="COUNTRY|RDATE" FilterColumn="RDATE"/></Document>"""


def test_excel_range_queries_are_left_to_the_excel_path(tmp_path):
    q = dr.load_db_queries(_folder(tmp_path, Q))
    assert set(q) == {"1", "3", "4"}


def test_code_row_table_finds_the_row_by_code_and_keeps_the_literal_filter(tmp_path):
    folder = _folder(tmp_path, Q)
    cell = dr.locate_cell(dr.load_db_queries(folder)["1"], {}, "1", "1014", {})
    assert (cell.table, cell.column, cell.kind) == ("CIMS_FILING_INFO", "VAL", "code-row") or cell.column in ("VAL", "VALUE")
    assert cell.key["CODE"] == "1014" and cell.key["RETURN_CODE"] == "401"


def test_suffixed_code_in_a_union_picks_the_branch_whose_suffix_matches(tmp_path):
    q = dr.load_db_queries(_folder(tmp_path, Q))["3"]
    cell = dr.locate_cell(q, {}, "3", "Y020_X020", {})
    assert cell.table == "CIMS_PART_A" and cell.column == "NAME_X020" and cell.key == {"DESCRIPTION": "Y020"}


def test_wide_table_uses_the_typed_member_as_the_row_key(tmp_path):
    folder = _folder(tmp_path, Q, TM)
    cell = dr.locate_cell(dr.load_db_queries(folder)["4"], dr.load_table_mapping(folder), "4", "SOVEREIGNS", {"DT": "Australia"})
    assert (cell.table, cell.column, cell.key, cell.kind) == ("QCB_BREAK", "SOVEREIGNS", {"COUNTRY": "Australia"}, "wide-row")


def test_wide_table_without_a_row_key_is_not_guessed(tmp_path):
    folder = _folder(tmp_path, Q, TM)
    assert dr.locate_cell(dr.load_db_queries(folder)["4"], dr.load_table_mapping(folder), "4", "SOVEREIGNS", {}) is None


def test_unknown_code_is_not_located(tmp_path):
    q = dr.load_db_queries(_folder(tmp_path, Q))["3"]
    assert dr.locate_cell(q, {}, "3", "Y020_X999", {}) is None


def test_identifiers_are_checked_before_they_can_reach_sql():
    assert dr.is_identifier("CIMS_PART_A") and not dr.is_identifier("A; DROP TABLE X") and not dr.is_identifier("")
    cell = dr.DbCell("T", "C; DROP TABLE X", {"CODE": "1"}, "RDATE", "1", "code-row")
    assert DbReader().read(cell, "2026-01-01").state == "unavailable"


def test_reporting_date_uses_the_period_end_and_never_guesses():
    assert dr.reporting_date("asof_20260430_Australia") == "2026-04-30"
    assert dr.reporting_date("fromto_20180901_20180930_Intrabank") == "2018-09-30"
    assert dr.reporting_date("ctx_1") is None and dr.reporting_date("asof_99999999") is None


def test_numbers_match_applies_the_multiplier_and_compares_text_exactly():
    assert dr.numbers_match("4172.0", "4172") and dr.numbers_match(5, "5000", 1000)
    assert not dr.numbers_match("4172", "4173")
    assert dr.numbers_match("true", "true") and not dr.numbers_match("true", "false")


def test_a_wrong_passphrase_never_decrypts():
    import pytest
    with pytest.raises(Exception):
        decrypt("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", "x" * 44)


ROW_Q = """<Document><Row QueryId="1" QueryName="SecA" TemplateId="10" ProviderId="1005"><SelectQuery>Select ITEM as Description, DOM_CURR_QTR as CQ_DO, OVER_CURR_QTR as CQ_OS, GLB_CURR_QTR as CQ_GO, CODE, RDATE From CIMS_ROR_Q_SEC_A where CODE between 1000 and 1110 and TO_DATE(RDATE,'DD-MON-RR') = ## order by code</SelectQuery></Row></Document>"""


def test_code_row_with_several_value_columns_offers_them_and_is_never_decided_from_metadata(tmp_path):
    q = dr.load_db_queries(_folder(tmp_path, ROW_Q))["10"]
    cell = dr.locate_cell(q, {}, "10", "1028", {})
    assert cell.kind == "code-multi" and cell.key == {"CODE": "1028"} and cell.provider_id == "1005"
    assert cell.alternatives == ["DOM_CURR_QTR", "OVER_CURR_QTR", "GLB_CURR_QTR"]
    assert dr.locate_cell(q, {}, "10", "2000", {}) is None          # outside the query's CODE range


def test_the_figure_itself_picks_the_column_and_a_tie_is_not_resolved():
    row = {"DOM_CURR_QTR": 260299.2, "OVER_CURR_QTR": 314478.45, "GLB_CURR_QTR": 368657.7}
    assert dr.pick_column(row, "26029920000", 100000) == ("DOM_CURR_QTR", "")
    col, why = dr.pick_column({"A": 5, "B": 5}, "5")
    assert col is None and "2 columns" in why
    assert dr.pick_column(row, "1")[0] is None


def test_inactive_queries_are_ignored(tmp_path):
    xml = ROW_Q.replace('ProviderId="1005"', 'ProviderId="1005" IsActive="false"')
    assert dr.load_db_queries(_folder(tmp_path, xml)) == {}


# ── IsExcel switch and the standard DB card table ────────────────────────────
from backend.error_improvement import calc_view as _cv, cell_locator as _cl, rule_cards as _rc


def _repo(tmp_path, flag):
    db = tmp_path / "DataBase"
    (db / "4100").mkdir(parents=True)
    attr = "" if flag is None else f' IsExcel="{flag}"'
    (db / "Returns.xml").write_text(f'<Returns><Return Id="4100" Name="X"{attr}/><Return Id="9"/></Returns>', encoding="utf-8")
    return _cl.FormMeta("4100", str(db / "4100"))


def test_returns_xml_says_whether_a_return_is_excel_or_database(tmp_path):
    assert dr.return_kind(_repo(tmp_path / "a", "true")) is True
    assert dr.return_kind(_repo(tmp_path / "b", "False")) is False
    assert dr.return_kind(_repo(tmp_path / "c", None)) is None          # older repository: the row says nothing


def test_a_database_cell_table_is_table_name_column_row_value():
    a = dr.DbAddress("1", "L", "CIMS_ROR_Q_SEC_A", 1, 0, "1028", 1, None, None, table="CIMS_ROR_Q_SEC_A", column="DOM_CURR_QTR",
                     key={"CODE": "1028"}, key_text="CODE = 1028", row_label="(ii) Non-SLR Investments")

    class _Lc:
        addr, res = a, None

    view = {"kv_cells": {"x": ("CIMS_ROR_Q_SEC_A", a.a1)}}
    _rc._mark_db(view, {"V1": [_Lc()]})
    assert _rc.kv_columns(view) == ["Table Name", "Column", "Row", "Value"]
    assert _rc.kv_fields(view) == ["sheet", "column", "cell", "value"]
    assert view["kv_cells"]["x"] == ("CIMS_ROR_Q_SEC_A", "CODE = 1028 · (ii) Non-SLR Investments")


def test_an_excel_cell_table_keeps_its_columns():
    view = {"kv_cells": {"x": ("Sheet1", "B3")}, "kv_where": {"x": {"table": "", "column": ""}}}
    assert _rc.kv_columns(view) == ["Sheet Name", "Cell", "Value"]
    assert _rc.kv_fields(view) == ["sheet", "cell", "value"]


def test_summed_database_cells_read_as_one_column_and_a_run_of_codes():
    cells = [("T", f"COL (CODE = {n})") for n in (1029, 1030, 1031, 1034)]
    assert _cv.cell_ref(cells) == ("T", "COL (CODE = 1029-1031, 1034)")
