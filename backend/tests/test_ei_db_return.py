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


import base64

PASS = "x9" * 22          # a made-up 44-character key for the tests (the real one is never stored in the repository)


def _encrypt(text: str) -> str:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    iv, key = PASS[:12].encode(), PASS[12:44].encode()
    return base64.b64encode(iv + AESGCM(key).encrypt(iv, text.encode(), None)).decode()


def _repo(tmp_path, providers, queries):
    """A repository: DataBase/XML_Providers.xml (id, type) and DataBase/4100/XML_Query.xml (provider id, sql)."""
    db = tmp_path / "DataBase"
    (db / "4100").mkdir(parents=True)
    rows = "".join(f'<Row ProviderId="{i}" ProviderName="n{i}" ProviderType="{t}" IsActive="true">'
                   f"<ConnectionString>{_encrypt(cs)}</ConnectionString></Row>" for i, t, cs in providers)
    (db / "XML_Providers.xml").write_text(f"<Document>{rows}</Document>", encoding="utf-8")
    qrows = "".join(f'<Row QueryId="{n}" TemplateId="{n}" ProviderId="{pid}"><SelectQuery>{sql}</SelectQuery></Row>'
                    for n, (pid, sql) in enumerate(queries, 1))
    (db / "4100" / "XML_Query.xml").write_text(f"<Document>{qrows}</Document>", encoding="utf-8")
    return _cl.FormMeta("4100", str(db / "4100")), str(db / "4100")


DBQ = "Select CODE as Code, VALUE as Val From T1 Where RDATE = ##"
XLQ = "Select F1 As A From [Sheet1$A1:B5]"


def test_the_providers_of_the_queries_say_whether_a_return_is_excel_or_database(tmp_path):
    prov = [("1", "Oracle", "User Id=u;Password=p;Data Source=d"), ("2", "Excel", "C:/x.xls")]
    assert dr.return_kind(_repo(tmp_path / "a", prov, [("1", DBQ)])[0]) is False          # only database queries
    assert dr.return_kind(_repo(tmp_path / "b", prov, [("2", XLQ)])[0]) is True           # only Excel queries
    assert dr.return_kind(_repo(tmp_path / "c", prov, [("1", DBQ), ("2", XLQ)])[0]) is None   # both: decided per layout
    assert dr.return_kind(_repo(tmp_path / "d", prov, [("2", DBQ)])[0]) is True           # table SQL but an Excel provider: not a database


def test_an_unknown_or_ambiguous_provider_falls_back_on_what_the_sql_says(tmp_path):
    prov = [("3", "Oracle", "x"), ("3", "Excel", "y")]                                     # the same id listed for both kinds
    meta, folder = _repo(tmp_path, prov, [("3", DBQ), ("9", DBQ)])                         # 9 is not in the provider file at all
    assert set(dr.load_db_queries(folder)) == {"1", "2"}
    assert dr.return_kind(meta) is False


def test_the_provider_row_gives_the_connection_and_a_wrong_key_gives_nothing(tmp_path, monkeypatch):
    from backend.error_improvement import db_source as ds
    cs = "User Id=scott;Password=tiger;Data Source=(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=h)(PORT=1521))(CONNECT_DATA=(SID=xe)));"
    other = cs.replace("scott", "other")
    _meta, folder = _repo(tmp_path, [("1", "Oracle", cs), ("2", "Excel", "C:/x.xls"), ("3", "Oracle", cs), ("3", "Excel", "y"),
                                     ("4", "Oracle", cs), ("4", "Oracle", other)], [("1", DBQ)])
    monkeypatch.setenv("IDEAL_AES_PASSPHRASE", PASS)
    got = ds.provider_connection(folder, "1")
    assert got == {"user": "scott", "password": "tiger", "dsn": "(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=h)(PORT=1521))(CONNECT_DATA=(SID=xe)))"}
    assert ds.provider_connection(folder, "2") is None          # an Excel provider is not a database
    assert ds.provider_connection(folder, "3") == got           # the id is also an Excel source: the Oracle row serves a table query
    assert ds.provider_connection(folder, "4") is None          # two different databases under one id: never guessed
    monkeypatch.setenv("IDEAL_AES_PASSPHRASE", "z" * 44)
    assert ds.provider_connection(folder, "1") is None          # the wrong key decrypts nothing
    monkeypatch.delenv("IDEAL_AES_PASSPHRASE")
    assert ds.provider_connection(folder, "1") is None          # no key at all


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


# ── wording of a database card ───────────────────────────────────────────────
import types as _types


def _mismatch_row():
    return _types.SimpleNamespace(facts={"kind": "total mismatch"}, solution="", error="")


class _NoCell:
    addr = None


def test_a_variable_the_formula_does_not_use_is_not_a_missing_operand():
    ev = {"lhs_value": 150, "rhs_value": 160}
    located = {"V4": [_NoCell()]}                       # V4 is reported but the formula only compares V2 and V3
    _p, cause, _f = _rc._row_triple(_mismatch_row(), "x", [], "", {}, ev)
    assert "could not be located" not in cause
    _p, cause, _f = _rc._row_triple(_mismatch_row(), "x", [], "", located, ev)          # a used operand with no cell is reported
    assert "could not be located in the workbook" in cause


def test_a_database_card_says_check_the_data_and_regenerate():
    ev = {"lhs_value": 150, "rhs_value": 160}
    _p, _c, fix = _rc._row_triple(_mismatch_row(), "x", [], "", {}, ev, db=True)
    assert "regenerate the instance" in fix and "workbook" not in fix and "Make the cells add up" not in fix


def test_excel_nouns_become_database_nouns_only_on_a_database_card():
    text = {"a": ["1 operand(s) could not be located in the workbook (they are 0, or their cell is not shown)"],
            "b": "(the first could not be placed in the workbook)", "c": "workbook verified"}
    got = _rc._db_words(text)
    assert got["a"] == ["1 operand(s) could not be located in the table (they are 0, empty or not in the database)"]
    assert got["b"] == "(the first could not be placed in the table)" and got["c"] == "verified against the database"


# ── three tiers: confirmed / "check this or this" / nothing ─────────────────
SEC_C = ("select * from ( select COUNTRY_NAME as CountryName, COUNTRY_CODE as CountryCode, LINE_ITEM as Description, OVR_BR_NO as OB, "
         "TOTAL_NO as GrandTot, RDATE, CODE+999 as Code from T_C union select COUNTRY_NAME as CountryName, COUNTRY_CODE as CountryCode, "
         "LINE_ITEM as Description, OVR_BR_AMT as OB, TOTAL_AMT as GrandTot, RDATE, CODE+1018 as Code from T_C ) "
         "where CountryName {op} 'ALL Countries' and TO_DATE(RDATE,'DD-MON-RR') = ## order by CODE")


def _sec_c(tmp_path, op):
    xml = f'<Document><Row QueryId="1" TemplateId="5" ProviderId="9"><SelectQuery>{SEC_C.format(op=op)}</SelectQuery></Row></Document>'
    return dr.load_db_queries(_folder(tmp_path, xml))["5"]


def test_a_wrapped_union_with_code_offsets_gives_one_candidate_per_branch_and_the_entry_key(tmp_path):
    q = _sec_c(tmp_path, "!=")
    typed = {"CountryCodeAxis": "SG", "CountryNameAxis": "SG - Singapore"}
    assert dr.locate_cell(q, {}, "5", "1019", typed) is None                       # strict: nothing says which branch owns 1019
    cells = dr.locate_cells(q, {}, "5", "1019", typed)
    assert [c.key["CODE"] for c in cells] == ["20", "1"]                             # CODE+999 and CODE+1018
    assert cells[1].key == {"CODE": "1", "COUNTRY_CODE": "SG", "COUNTRY_NAME": "SG - Singapore"}
    assert cells[1].alternatives == ["OVR_BR_AMT", "TOTAL_AMT"]


def test_an_equality_on_the_outer_where_picks_the_total_row(tmp_path):
    cell = dr.locate_cells(_sec_c(tmp_path, "="), {}, "9", "1019", {})[1]
    assert cell.key == {"CODE": "1", "COUNTRY_NAME": "ALL Countries"}


def test_a_typed_member_that_matches_no_column_gives_no_candidate(tmp_path):
    assert dr.locate_cells(_sec_c(tmp_path, "!="), {}, "5", "1019", {"SomethingElseAxis": "x"}) == []


def test_columns_whose_words_match_the_members_come_first():
    ctx = _cl.Context("c", frozenset({("IndustryAndServicesAxis", "MediumServicesMember")}), frozenset())
    assert dr._rank_columns(["IND_MICRO", "IND_MEDIUM", "SER_MEDIUM", "TOT_MEDIUM"], ctx)[0] == "SER_MEDIUM"


def test_the_row_text_is_short():
    assert dr._key_text({"CODE": "1", "COUNTRY_CODE": "SG", "COUNTRY_NAME": "SG - Singapore"}) == "CODE = 1, SG - Singapore"


class _FakeReader:
    def __init__(self, state, row=None):
        self.state, self.row = state, row or {}

    def read_row(self, cell, columns, date):
        return self.state, dict(self.row)


def _meta_with_one_cell(tmp_path, reader):
    xml = ('<Document><Row QueryId="1" TemplateId="10" ProviderId="9"><SelectQuery>Select ITEM as Description, DOM_Q as CQ_DO, '
           "OVR_Q as CQ_OS, CODE, RDATE From T1 where CODE between 1000 and 1110 and TO_DATE(RDATE,'DD-MON-RR') = ##"
           "</SelectQuery></Row></Document>")
    meta = _cl.FormMeta("4100", _folder(tmp_path, xml))
    meta.layouts = {"10": "L"}
    meta.layout_axes = {"10": set()}
    meta.rows_by_concept = {"Concept": [_cl.MapRow("10", "1~1", "1028", "Concept", frozenset(), frozenset(), 100000)]}
    meta.__dict__["_db_reader"] = reader
    return meta


def test_tier_one_a_row_that_holds_the_value_confirms_the_column(tmp_path):
    res = dr.resolve_db(_meta_with_one_cell(tmp_path, _FakeReader("ok", {"DOM_Q": 1, "OVR_Q": 260299.2, "ITEM": "x"})),
                        "Concept", "asof_20250331", "26029920000")
    assert res.status == "CONFIRMED" and res.addresses[0].column == "OVR_Q" and res.addresses[0].verified


def test_tier_two_a_row_without_the_value_names_cells_to_check_but_confirms_nothing(tmp_path):
    res = dr.resolve_db(_meta_with_one_cell(tmp_path, _FakeReader("ok", {"DOM_Q": 1, "OVR_Q": 2})), "Concept", "asof_20250331", "999")
    assert res.status == "GUESS" and 1 <= len(res.addresses) <= 3
    assert all(not a.verified and a.state == "differs" for a in res.addresses)
    assert _rc._db_guess_note({"V1": [_types.SimpleNamespace(res=res)]}).startswith("Not confirmed (the row holds another value). Check: T1.")


def test_tier_two_also_applies_when_the_database_cannot_be_read_and_the_column_is_open(tmp_path):
    res = dr.resolve_db(_meta_with_one_cell(tmp_path, _FakeReader("unavailable")), "Concept", "asof_20250331", "5")
    assert res.status == "GUESS" and res.addresses[0].state == "unread"        # two value columns: the metadata cannot pick one


def test_one_clear_cell_is_the_location_even_when_it_cannot_be_confirmed(tmp_path):
    xml = ("<Document><Row QueryId=\"1\" TemplateId=\"10\" ProviderId=\"9\"><SelectQuery>Select CODE as Code, VALUE as Val "
           "From T1 Where RDATE = ##</SelectQuery></Row></Document>")
    (tmp_path / "x").mkdir()
    (tmp_path / "y").mkdir()
    meta = _meta_with_one_cell(tmp_path / "x", _FakeReader("unavailable"))
    meta.__dict__["_db_state"] = {"queries": dr.load_db_queries(_folder(tmp_path / "y", xml)), "mapping": {}, "rows": {}, "cols": {}}
    res = dr.resolve_db(meta, "Concept", "asof_20250331", "5")
    assert res.status == "MAPPED" and len(res.addresses) == 1 and res.addresses[0].state == "unread"
    meta.__dict__["_db_reader"] = _FakeReader("no-row")                          # the database says the row is not there: only a guess
    meta.__dict__["_db_state"]["rows"] = {}
    assert dr.resolve_db(meta, "Concept", "asof_20250331", "5").status == "GUESS"


def test_tier_three_nothing_to_name_gives_none(tmp_path):
    meta = _meta_with_one_cell(tmp_path, _FakeReader("ok"))
    assert dr.resolve_db(meta, "NoSuchConcept", "asof_20250331", "5") is None
