"""Regression: parsers that share backend.tools.mtime_cache must not share results.

The cache used to be keyed by (path, mtime) only. count_errors_by_category()
runs parse_formula_errors_v2 first (ERROR_EXPLAIN_V2=1, the default) and then
parse_backtrack_html_errors on the SAME file; the formula parser's empty
result was cached under the path and handed back to the schema parser, so a
file with real XBRL_SCHEMA errors reported none.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from backend.tools.mtime_cache import cached_by_mtime
from backend.tools.formula_error import parse_formula_errors_v2
from backend.tools.report_lookup import (
    count_errors_by_category,
    parse_backtrack_html_errors,
)

# iDeal error report with a populated XBRL_SCHEMA panel and no formula errors.
_SCHEMA_ONLY_HTML = """<html><body><div class="tab-pane fade" id="3">
<div class="panel-group" id="accordionSpecs">
<div class="panel panel-default" id="XBRL_SCHEMAPanel">
 <div class="panel-heading"><div class="assertionLabel"> XBRL_SCHEMA </div>
 <div id="XBRL_SCHEMAErrorNum" class="badge"> 2 </div></div>
 <div id="XBRL_SCHEMAError"><div id="XBRL_SCHEMAErrorContent"><table><tbody>
 <tr><td class="directMsg">cvc-complex-type.2.4.a: Invalid content was found starting with element 'PE002514'.<br><span class="msgDetails">LineNo: 5 ColumnNo: 7 FileName: a.xml</span></td></tr>
 <tr><td class="directMsg">cvc-datatype-valid.1.2.1: 'abc' is not a valid value for 'decimal'.<br><span class="msgDetails">LineNo: 9 ColumnNo: 3 FileName: a.xml</span></td></tr>
 </tbody></table></div></div>
</div></div></div></body></html>"""


@pytest.fixture(autouse=True)
def _v2_on(monkeypatch):
    monkeypatch.setenv("ERROR_EXPLAIN_V2", "1")


@pytest.fixture
def schema_file(tmp_path):
    f = tmp_path / "schema_only.html"
    f.write_text(_SCHEMA_ONLY_HTML, encoding="utf-8")
    return str(f)


def _schema_entries(path):
    return [e for e in parse_backtrack_html_errors(path) if e.get("errorType") == "XBRL_SCHEMA"]


class TestParserIsolation:
    def test_formula_parser_first_does_not_hide_schema_errors(self, schema_file):
        assert parse_formula_errors_v2(schema_file) == []   # caches an empty list
        assert len(_schema_entries(schema_file)) == 2

    def test_schema_parser_first_does_not_hide_formula_result(self, schema_file):
        assert len(_schema_entries(schema_file)) == 2
        assert parse_formula_errors_v2(schema_file) == []

    def test_count_errors_by_category_reports_schema_errors(self, schema_file):
        counts = count_errors_by_category(schema_file, "4092")
        assert counts.get("xbrl_schema", 0) > 0
        assert not counts.get("formula_error")

    def test_namespaces_do_not_share_an_entry(self, tmp_path):
        f = tmp_path / "x.html"
        f.write_text("x")
        assert cached_by_mtime(str(f), lambda: "A", "parser_a") == "A"
        assert cached_by_mtime(str(f), lambda: "B", "parser_b") == "B"
        assert cached_by_mtime(str(f), lambda: "unused", "parser_a") == "A"

    def test_file_change_still_invalidates(self, schema_file):
        assert len(_schema_entries(schema_file)) == 2
        p = Path(schema_file)
        p.write_text(_SCHEMA_ONLY_HTML.replace("badge\"> 2 ", "badge\"> 0 "), encoding="utf-8")
        later = p.stat().st_mtime + 5
        os.utime(schema_file, (later, later))
        assert _schema_entries(schema_file) == []


_REAL = Path(r"D:\Repo6.0\1001\Instance\4092")


@pytest.mark.skipif(not _REAL.is_dir(), reason="6.0 repo data not available")
def test_real_4092_log_52_schema_errors_survive_formula_parse_first():
    import xml.etree.ElementTree as ET
    rows = ET.parse(r"D:\Repo6.0\1001\DataBase\InstanceLog.xml").getroot().findall("Row")
    doc = next(r.get("ErrorDoc") for r in rows if r.get("Id") == "52")
    path = str(_REAL / doc)
    parse_formula_errors_v2(path)            # formula parser runs first, as in count_errors_by_category
    assert len(_schema_entries(path)) > 0
    assert count_errors_by_category(path, "4092").get("xbrl_schema", 0) > 0
