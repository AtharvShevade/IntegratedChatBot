"""The validator caps a panel's badge at "100+" once it has more than 100 errors.

Every badge reader matched digits followed directly by "<", so "100+" read as
0: a DIMENSION panel with 100+ errors looked empty (no dimension errors found,
nothing explained) and an XBRL_SCHEMA panel with 100+ errors was skipped.
Real 6.0 files hit this far more often than the 5.5 ones (20 of the 6.0 HTML
error files carry an "N+" badge).
"""
from __future__ import annotations

import pytest

from backend.tools.error_file_shape import describe_error_file
from backend.tools.report_lookup import (
    _read_dimension_badge_from_html,
    count_errors_by_category,
    parse_backtrack_html_errors,
)

_PANEL = """<div class="panel panel-default" id="{name}Panel">
 <div class="panel-heading"><div class="assertionLabel"> {name} </div>
 <div id="{name}ErrorNum" class="badge"> {badge} </div></div>
 <div id="{name}ErrorContent"><table><tbody>
 <tr><td class="directMsg">cvc-complex-type.2.4.a: Invalid content was found starting with element 'PE002514'.<br><span class="msgDetails">LineNo: 5 ColumnNo: 7 FileName: a.xml</span></td></tr>
 </tbody></table></div></div>"""


def _html(name, badge):
    return ("<html><body><div class='tab-pane fade' id='3'><div class='panel-group' id='accordionSpecs'>"
            + _PANEL.format(name=name, badge=badge) + "</div></div></body></html>")


class TestDimensionBadge:
    @pytest.mark.parametrize("badge,expected", [("0", 0), ("7", 7), ("100", 100), ("100+", 100)])
    def test_reads_the_count_with_or_without_a_plus(self, badge, expected):
        assert _read_dimension_badge_from_html(_html("DIMENSION", badge)) == expected

    def test_second_pattern_also_accepts_a_plus(self):
        # No id on the badge element: the fallback pattern is used.
        html = '<div class="assertionLabel"> DIMENSION </div><div class="badge"> 100+ </div>'
        assert _read_dimension_badge_from_html(html) == 100


class TestSchemaPanelWithCappedBadge:
    def test_schema_entries_are_parsed_when_the_badge_is_100_plus(self, tmp_path):
        f = tmp_path / "capped_schema.html"
        f.write_text(_html("XBRL_SCHEMA", "100+"), encoding="utf-8")
        entries = [e for e in parse_backtrack_html_errors(str(f)) if e.get("errorType") == "XBRL_SCHEMA"]
        assert len(entries) == 1

    def test_count_reports_schema_errors_for_a_capped_panel(self, tmp_path):
        f = tmp_path / "capped_schema2.html"
        f.write_text(_html("XBRL_SCHEMA", "100+"), encoding="utf-8")
        assert count_errors_by_category(str(f), "4113").get("xbrl_schema", 0) > 0

    def test_plain_badge_still_works(self, tmp_path):
        f = tmp_path / "plain_schema.html"
        f.write_text(_html("XBRL_SCHEMA", "21"), encoding="utf-8")
        assert count_errors_by_category(str(f), "4092").get("xbrl_schema", 0) > 0


def test_error_file_shape_reads_a_capped_badge(tmp_path):
    f = tmp_path / "shape.html"
    f.write_text(_html("DIMENSION", "100+"), encoding="utf-8")
    assert describe_error_file(str(f))["badges"].get("DIMENSION") == 100
