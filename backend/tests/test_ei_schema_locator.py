"""XBRL schema errors placed in a database table (error_improvement.schema_locator)."""
from types import SimpleNamespace as NS

from backend.error_improvement import schema_locator as sl


def test_fact_is_read_from_the_named_instance_line(tmp_path):
    p = tmp_path / "x_Instance.xml"
    p.write_text("<a>\n<in-rbi-rep:AggregateNumberOfStaffMembers contextRef='asof_20260930_DomesticMember' unitRef='PURE' "
                 "decimals='2'>11887.55</in-rbi-rep:AggregateNumberOfStaffMembers>\n</a>\n", encoding="utf-8")
    assert sl._fact_on_line(str(p), "2") == ("AggregateNumberOfStaffMembers", "asof_20260930_DomesticMember", "11887.55")
    assert sl._fact_on_line(str(p), "1") is None and sl._fact_on_line(str(p), "x") is None and sl._fact_on_line(str(p), 99) is None


def _meta(dims):
    return NS(reported=NS(ctx_dims=lambda c: dims))


def _cols(*names):
    return [NS(column=n) for n in names]


def test_region_member_names_the_column_and_no_region_is_global():
    cols = _cols("DOMESTIC", "OVERSEAS", "GLOBAL")
    assert [a.column for a in sl._by_region(cols, _meta({"RegionOfBusinessAxis": "DomesticMember"}), "c")] == ["DOMESTIC"]
    assert [a.column for a in sl._by_region(cols, _meta({"RegionOfBusinessAxis": "OverseasMember"}), "c")] == ["OVERSEAS"]
    assert [a.column for a in sl._by_region(cols, _meta({"StaffMembersAxis": "CEOsMember"}), "c")] == ["GLOBAL"]
    assert len(sl._by_region(_cols("A", "B"), _meta({}), "c")) == 2          # columns that are not regions are never narrowed


def test_apply_fills_the_table_info_and_says_what_the_table_holds(monkeypatch):
    loc = {"table": "T1", "column": "DOMESTIC", "row_label": "Total Number of Staff", "cell": "DOMESTIC (CODE = 1000)",
           "context": "RegionOfBusinessAxis: DomesticMember", "state": "GUESS", "held": 11876, "candidates": 1}
    monkeypatch.setattr(sl, "locate_all", lambda *a, **k: {0: loc})
    errs = [{"actualValue": "11887.55", "explanation": "Whole number needed.", "table_info": {"validation_error": "v"}},
            {"actualValue": "1", "explanation": "Other."}]
    out = sl.apply(errs, "f.html", "repo")
    ti = out[0]["table_info"]
    assert (ti["db_table_name"], ti["row_label"], ti["cell_code"], ti["validation_error"]) == ("T1", "Total Number of Staff", "DOMESTIC (CODE = 1000)", "v")
    assert out[0]["explanation"].endswith("The return has 11,887.55; the table holds 11,876 in T1.DOMESTIC.")
    assert out[1]["explanation"] == "Other." and "table_info" not in out[1]       # an error that cannot be placed is left alone


def test_nothing_is_located_for_an_excel_return_or_without_a_repository(monkeypatch):
    assert sl.locate_all([], "f.html", "repo") == {}
    assert sl.locate_all([{"line_no": 1}], "f.html", None) == {}
