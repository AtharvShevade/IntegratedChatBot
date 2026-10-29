"""Only RED validator items are errors. Yellow (and orange) items are warnings: still listed and explainable, never counted as errors.

The count is the number of red rule panels. The number inside a badge (164, 5, ...) is how many times that rule failed, so it is
never added up. 5.5 and 6.0 share one counting path (report_lookup.count_errors_by_category), so they share the semantics.

Fixtures are built in the real validator-output shape (`errorPanel<N>` / `formulaErrorNum<N>` with `badge badge-danger|warning`);
when the demo repos exist on the machine, real error files are checked too.
"""
from __future__ import annotations

import os
import re

import pytest

from backend.agent import error_explanation
from backend.tools import error_severity as esv
from backend.tools import formula_error as fe
from backend.tools import report_lookup as rl

HEADER = (
    '<tr class="hide"><th class="headerCell">DB TableName</th><th class="headerCell">Table Header</th>'
    '<th class="headerCell">Column Label(s)</th><th class="headerCell">Variable Id</th>'
    '<th class="headerCell">Row Label(s)</th><th class="headerCell">Instance Data(s)</th>'
    '<th class="headerCell">Entered Data(s)</th><th class="headerCell">Unit</th>'
    '<th class="headerCell">Decimal</th><th class="headerCell">Context</th>'
    '<th class="headerCell">Cell Code</th></tr>'
)


def _fact(var, value):
    return ('<tr class="hide fv"><td class="msgBodyCell">T </td><td class="msgBodyCell">H</td><td class="msgBodyCell"></td>'
            f'<td class="msgBodyCell">{var}</td><td class="msgBodyCell">row</td><td class="msgBodyCell">{value}</td>'
            '<td class="msgBodyCell"></td><td class="msgBodyCell">INR</td><td class="msgBodyCell">-3</td>'
            '<td class="longMsgBodyCell">asof_20260331</td><td class="msgBodyCell">C1</td></tr>')


def _panel(n, name, shown, cls="badge badge-danger"):
    """One rule panel exactly as the validator writes it: the badge carries the colour class and the failure count."""
    return (
        f'<div class="panel panel-default" id="errorPanel{n}">'
        f'<div class="panel-heading formula-panel-heading" id="formulaErrorLink{n}" data-toggle="collapse" data-target="#formulaError{n}">'
        f'<div id="errorLink{n}" class="assertionLabel">{name}</div>'
        f'<div id="formulaErrorTest{n}" class="formulaErrorTest" title="formula expression">$V1 = $V2</div>'
        f'<div id="formulaErrorNum{n}" class="{cls}">{shown}</div></div>'
        f'<div id="formulaError{n}" class="panel-collapse collapse"><div id="formulaErrorContent{n}" class="panel-body">'
        '<table class="table table-condensed table-striped"><tbody>'
        '<tr class="msgHead"><td class="formulaErrorTitle" colspan="11"> ▼ &nbsp;"en:A does not equal B"</td></tr>'
        + HEADER + _fact("V1", 10) + _fact("V2", 20) + '</tbody></table></div></div></div>'
    )


RED, YELLOW, ORANGE = "badge badge-danger", "badge badge-warning", "badge badge-orange"


def _file(tmp_path, panels, name="E_Instance.html"):
    html = ("<!DOCTYPE html><html><body><div class=\"panel with-nav-tabs\"><ul class=\"nav nav-tabs\"><li class=\"active\">"
            '<a href="#1" data-toggle="tab">FORMULA_ERROR</a></li></ul><div class="tab-content">'
            '<div class="tab-pane fade in active" id="1"><div class="panel-group" id="accordionFormula">'
            + "".join(panels) + "</div></div></div></div></body></html>")
    p = tmp_path / name
    p.write_text(html, encoding="utf-8")
    return str(p)


def _items(tmp_path, spec):
    """spec: [(badge class, number shown in the badge)] -> an error file with one panel each."""
    return _file(tmp_path, [_panel(i, f"Rule{i}", shown, cls) for i, (cls, shown) in enumerate(spec, 1)])


# ── severity from the badge class ─────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("css,expected", [
    ("badge badge-danger", "error"), ("badge badge-warning", "warning"), ("badge badge-orange", "warning"),
    ("badge badge-yellow", "warning"), ("badge badge-ok", "unknown"), ("badge", "unknown"), ("", "unknown"), (None, "unknown"),
    ("badge badge-danger badge-warning", "warning"),                 # a doubt never inflates the error count
])
def test_severity_is_read_from_the_badge_class(css, expected):
    assert esv.severity_from_class(css) == expected


# ── the counting rule: red only ───────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("spec,errors,warnings", [
    ([(RED, 1), (RED, 1), (YELLOW, 1)], 2, 1),
    ([(RED, 1), (YELLOW, 1), (ORANGE, 1)], 1, 2),
    ([(YELLOW, 1), (ORANGE, 1)], 0, 2),
    ([(RED, 1), (RED, 1), (RED, 1)], 3, 0),
    ([], 0, 0),
])
def test_counts_follow_the_colour_table(tmp_path, spec, errors, warnings):
    counts = rl.count_errors_by_category(_items(tmp_path, spec), form_id="2065")
    assert counts.get("formula_error", 0) == errors
    assert counts.get("formula_warning", 0) == warnings
    assert counts.get("formula_total", 0) == len(spec)              # everything stays listed, for paging


def test_red_164_red_5_yellow_counts_two_not_the_numbers_in_the_badges(tmp_path):
    path = _items(tmp_path, [(RED, 164), (RED, 5), (YELLOW, 1)])
    counts = rl.count_errors_by_category(path, form_id="2065")
    assert counts["formula_error"] == 2                              # not 3, and not 164 + 5
    assert counts["formula_warning"] == 1 and counts["formula_total"] == 3
    assert [r["error_count"] for r in fe.parse_formula_errors_v2(path)] == [164, 5, 1]   # the failure counts are untouched


def test_a_section_with_only_warnings_has_no_error_count_but_stays_listed(tmp_path):
    counts = rl.count_errors_by_category(_items(tmp_path, [(YELLOW, 3), (ORANGE, 2)]), form_id="2065")
    assert "formula_error" not in counts and counts["formula_warning"] == 2 and counts["formula_total"] == 2


def test_an_unrecognised_colour_is_not_counted_as_an_error(tmp_path):
    counts = rl.count_errors_by_category(_items(tmp_path, [(RED, 1), ("badge badge-ok", 1), ("badge", 1)]), form_id="2065")
    assert counts["formula_error"] == 1 and "formula_warning" not in counts and counts["formula_total"] == 3


def test_counting_the_same_file_again_never_double_counts(tmp_path):
    path = _items(tmp_path, [(RED, 164), (RED, 5), (YELLOW, 1)])
    first = rl.count_errors_by_category(path, form_id="2065")
    for _ in range(3):                                               # refreshes, repeated renders, cached parses
        assert rl.count_errors_by_category(path, form_id="2065") == first
        assert len(fe.parse_formula_errors_v2(path)) == 3
    assert first["formula_error"] == 2


# ── warnings stay visible ─────────────────────────────────────────────────────────────────────────────────────────
def test_warnings_are_still_parsed_and_listed_after_the_errors(tmp_path):
    path = _items(tmp_path, [(YELLOW, 1), (RED, 164), (ORANGE, 1), (RED, 5)])
    rules = fe.parse_formula_errors_v2(path)
    assert [r["rule_name"] for r in rules] == ["Rule2", "Rule4", "Rule1", "Rule3"]      # red first, file order inside each group
    assert [r["severity"] for r in rules] == ["error", "error", "warning", "warning"]
    assert len(rules) == 4                                           # nothing is dropped


def test_the_pager_pages_through_errors_and_warnings_but_reports_both_counts(tmp_path, monkeypatch):
    import asyncio
    path = _items(tmp_path, [(RED, 164), (RED, 5), (YELLOW, 1), (ORANGE, 1)])
    everything = [{"rule_name": f"Rule{i}"} for i in range(1, 5)]
    monkeypatch.setattr(rl, "build_error_file_path", lambda form_id, fname: path)
    monkeypatch.setattr(error_explanation, "_is_contained_error_file", lambda p: True)
    monkeypatch.setattr(rl, "explain_errors_by_category_for_form",
                        lambda p, c, form_id="", offset=0, lang="en": everything[offset:offset + 3])

    first = asyncio.run(error_explanation.explain_category_for_report("E_Instance.html", "formula_error", "2065", offset=0))
    assert first["data"] == {"has_more": True, "next_offset": 3, "total_count": 4, "error_count": 2, "warning_count": 2}
    assert "showing 1-3 of 4 (2 errors, 2 warnings)" in first["response_text"]        # errors and warnings are named separately
    last = asyncio.run(error_explanation.explain_category_for_report("E_Instance.html", "formula_error", "2065", offset=3))
    assert last["data"]["has_more"] is False and last["data"]["next_offset"] == 4         # the warning is reached, then the end


# ── cards: a warning is not presented as a failure ────────────────────────────────────────────────────────────────
def test_a_warning_card_is_badged_warning_and_an_error_card_stays_failed(monkeypatch, tmp_path):
    from backend.error_improvement import adapter, rule_cards
    c = {"rule_name": "R", "number": 1, "checks": "A = B", "problem": "p", "cause": "c", "fix": "f", "related": None,
         "other_cases": None, "cells": [], "calc": [("Left side", "₹1"), ("Right side", "₹2"), ("Difference", "₹1")],
         "evidence_key": "CONFIRMED", "evidence": "v", "note": "n", "kind": "ratio"}
    c["view"] = rule_cards._compact_view(c, [], {}, rule_cards.cell_money)
    f = tmp_path / "e.html"
    f.write_text("<html/>", encoding="utf-8")
    monkeypatch.setattr(adapter, "_result_for", lambda *a, **k: {"cards": {"W": c, "E": c}, "info": {}})
    out = adapter.explain_batch([{"rule_name": "W", "severity": "warning"}, {"rule_name": "E", "severity": "error"}], str(f))
    w, e = out["W"], out["E"]
    assert w["explanation_sections"][0]["badge"] == "Warning" and w["explanation_sections"][0]["tone"] == "warning"
    assert "[Warning]" in w["explanation"] and "[Failed]" not in w["explanation"]
    assert e["explanation_sections"][0]["badge"] == "Failed" and "tone" not in e["explanation_sections"][0]
    assert w["explanation_sections"][0]["why"] == e["explanation_sections"][0]["why"]    # the explanation itself is unchanged


# ── the same semantics in 5.5 and 6.0 ─────────────────────────────────────────────────────────────────────────────
def test_5_5_and_6_0_count_the_same_way(tmp_path, monkeypatch):
    from backend import version_config
    path = _items(tmp_path, [(RED, 164), (RED, 5), (YELLOW, 1)])
    results = []
    for is_v6 in (False, True):
        monkeypatch.setattr(version_config, "IS_V6", is_v6, raising=False)
        results.append(rl.count_errors_by_category(path, form_id="2065"))
    assert results[0] == results[1] and results[0]["formula_error"] == 2


def _real(path):
    return pytest.mark.skipif(not os.path.isfile(path), reason="demo repo not on this machine")


R55 = r"D:\RepoCore_5.5\Instance\2041\ABPL260930R09107Q_21-10-26_06-50-39_Instance.html"
R60 = r"D:\Repo6.0\1001\Instance\4100\QCB_F013_Breakdown of exposures by geography_Excel_441_30-Apr-2026_22-07-26_12-54-36_Instance.html"


def _red_panels(path):
    html = open(path, encoding="utf-8", errors="ignore").read()
    return len(re.findall(r'id="formulaErrorNum\d+"\s+class="badge badge-danger"', html))


@pytest.mark.parametrize("path", [pytest.param(R55, marks=_real(R55)), pytest.param(R60, marks=_real(R60))])
def test_real_5_5_and_6_0_files_count_exactly_their_red_panels(path):
    counts = rl.count_errors_by_category(path, form_id="")
    total = len(fe.parse_formula_errors_v2(path))
    assert counts.get("formula_error", 0) == _red_panels(path)
    assert counts.get("formula_error", 0) + counts.get("formula_warning", 0) == total == counts["formula_total"]
