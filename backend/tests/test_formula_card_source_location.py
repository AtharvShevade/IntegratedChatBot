"""Formula-error card: DB TableName / Table Header / Cell Code (from the error file's
backtracking columns) are shown after "Validation Rule", for the rule's first variable,
only when the file carries them. Built from synthetic files shaped like a real
BTDetails.html - no external data needed."""
from __future__ import annotations

import pytest

from backend.tools import error_card
from backend.tools import formula_error as fe

HEADER_ROW = (
    '<tr class="hide"><th class="headerCell">DB TableName</th><th class="headerCell">Table Header</th>'
    '<th class="headerCell">Column Label(s)</th><th class="headerCell">Variable Id</th>'
    '<th class="headerCell">Row Label(s)</th><th class="headerCell">Instance Data(s)</th>'
    '<th class="headerCell">Entered Data(s)</th><th class="headerCell">Unit</th>'
    '<th class="headerCell">Decimal</th><th class="headerCell">Context</th>'
    '<th class="headerCell">Cell Code</th></tr>'
)


def _row(table, header, var, value, context, cell, row_label=""):
    return (
        '<tr class="hide fv">'
        f'<td class="msgBodyCell">{table} </td><td class="msgBodyCell">{header}</td>'
        '<td class="msgBodyCell"></td>'
        f'<td class="msgBodyCell">{var}</td><td class="msgBodyCell">{row_label}</td>'
        f'<td class="msgBodyCell">{value}</td><td class="msgBodyCell"></td>'
        '<td class="msgBodyCell">INR</td><td class="msgBodyCell">-3</td>'
        f'<td class="longMsgBodyCell">{context}</td><td class="msgBodyCell">{cell}</td></tr>'
    )


def _panel(n, name, formula, title, rows, with_header=True):
    return (
        f'<div class="panel panel-default" id="formulaErrorPanel{n}"><div class="panel-heading formula-panel-heading" '
        f'id="formulaErrorLink{n}" data-toggle="collapse" data-target="#formulaError{n}">'
        f'<div class="assertionLabel">{name}</div>'
        f'<div class="formulaErrorTest" title="formula expression"> {formula}</div>'
        '<div class="badge badge-danger">1</div></div>'
        f'<div id="formulaError{n}" class="panel-collapse collapse"><table class=\'table table-condensed table-striped\'><tbody>'
        f'<tr class="msgHead"><td class="formulaErrorTitle" colspan="11"> ▼ &nbsp;"{title}"</td></tr>'
        + (HEADER_ROW if with_header else "") + "".join(rows) + '</tbody></table></div></div>'
    )


def _file(tmp_path, panels):
    html = (
        "<!DOCTYPE html><html><body><div class='tab-pane fade in active' id='1'>"
        "<div class='panel-group' id='accordionFormula'>" + "".join(panels) + "</div></div></body></html>"
    )
    path = tmp_path / "X_BTDetails.html"
    path.write_text(html, encoding="utf-8")
    return path


TOTAL_FORMULA = "round($V1 div 1000) * 1000 = round((sum ($V2))   div 1000 ) * 1000"
TOTAL_TITLE = "en:Identity  Value of Total of average cash reserves (Total = Sum of all its child elements )do not tally."


def _total_rule_rows(v1_header="Table 2 - Cash Reserves with RBI"):
    rows = [_row("CIMS_MPD03_CRR_LAYOUT3_HM", v1_header, "V1", "134592420000", "fromto_20250501_20250515", "Y250_X030", "Y250")]
    for day in ("01", "02", "03"):
        rows.append(_row("CIMS_MPD03_CRR_LAYOUT2_HM", "Table 2 - Cash Reserves with RBI", "V2",
                         "8972828000", f"asof_20250515_{day}052025", "Ave_Cash_X030"))
    return rows


@pytest.fixture(autouse=True)
def _no_llm(monkeypatch):
    # Explanations fall back to deterministic text when the model call fails.
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:9")
    monkeypatch.setenv("OLLAMA_TIMEOUT", "2")


def _explain(path, n=1):
    rules = fe.parse_formula_errors_v2(str(path))
    out = fe.explain_formula_rules(rules[:n], form_id="4038", error_file_path=str(path))
    return rules, out


def _locators(out):
    return [s for s in out["explanation_sections"] if s.get("kind") == "locator" and not s.get("heading")]


def test_all_three_lines_follow_the_validation_rule(tmp_path):
    path = _file(tmp_path, [_panel(1, "TotalOfAverageCashReserves", TOTAL_FORMULA, TOTAL_TITLE, _total_rule_rows())])
    rules, out = _explain(path)
    assert rules[0]["has_backtracking"] is True
    kinds = [(s["kind"], s.get("heading")) for s in out[0]["explanation_sections"]]
    i_rule = kinds.index(("labeled_text", "Validation Rule"))
    i_loc = kinds.index(("locator", ""))
    i_cond = kinds.index(("labeled_text", "Satisfactory condition"))
    assert i_rule < i_loc < i_cond                      # between the two, as asked
    items = _locators(out[0])[0]["items"]
    assert [(i["label"], i["value"]) for i in items] == [
        ("DB TableName", "CIMS_MPD03_CRR_LAYOUT3_HM"),
        ("Table Header", "Table 2 - Cash Reserves with RBI"),
        ("Cell Code", "Y250_X030"),
    ]


def test_it_is_V1s_location_not_a_child_variables(tmp_path):
    path = _file(tmp_path, [_panel(1, "TotalOfAverageCashReserves", TOTAL_FORMULA, TOTAL_TITLE, _total_rule_rows())])
    _rules, out = _explain(path)
    values = [i["value"] for i in _locators(out[0])[0]["items"]]
    assert "CIMS_MPD03_CRR_LAYOUT2_HM" not in values and "Ave_Cash_X030" not in values


def test_the_plain_text_card_shows_the_lines_in_the_requested_format(tmp_path):
    path = _file(tmp_path, [_panel(1, "TotalOfAverageCashReserves", TOTAL_FORMULA, TOTAL_TITLE, _total_rule_rows())])
    _rules, out = _explain(path)
    text = out[0]["explanation"]
    assert ("DB TableName : CIMS_MPD03_CRR_LAYOUT3_HM\n"
            "Table Header : Table 2 - Cash Reserves with RBI\n"
            "Cell Code : Y250_X030") in text
    assert text.index("Validation Rule") < text.index("DB TableName") < text.index("Satisfactory condition")


def test_a_blank_table_header_just_leaves_that_line_out(tmp_path):
    path = _file(tmp_path, [_panel(1, "TotalOfAverageCashReserves", TOTAL_FORMULA, TOTAL_TITLE, _total_rule_rows(v1_header=""))])
    _rules, out = _explain(path)
    labels = [i["label"] for i in _locators(out[0])[0]["items"]]
    assert labels == ["DB TableName", "Cell Code"]


def test_no_backtracking_columns_means_no_location_block(tmp_path):
    rows = [
        '<tr class="hide fv"><td class="msgBodyCell">V1</td><td class="msgBodyCell">134592420000</td></tr>',
        '<tr class="hide fv"><td class="msgBodyCell">V2</td><td class="msgBodyCell">8972828000</td></tr>',
    ]
    path = _file(tmp_path, [_panel(1, "SomeRule", "$V1 = sum($V2)", "does not tally", rows, with_header=False)])
    rules = fe.parse_formula_errors_v2(str(path))
    out = fe.explain_formula_rules(rules[:1], form_id="4044", error_file_path=str(path))
    assert rules[0]["has_backtracking"] is False
    assert _locators(out[0]) == []
    assert "DB TableName" not in out[0]["explanation"]


def test_helper_ignores_a_first_variable_without_a_row():
    rule = {"has_backtracking": True}
    by_var = {"V2": [{"db_table": "T2", "cell_code": "C2", "table_header": "H2"}]}
    # V2 exists but V1 does not: V2 is the lowest present variable, so it is used -
    # the helper never reaches for a *different* variable when the first has no data.
    assert error_card is not None
    section = fe._card_source_location_formula(rule, by_var)
    assert [i["value"] for i in section["items"]] == ["T2", "H2", "C2"]
    assert fe._card_source_location_formula(rule, {"V1": [{}], "V2": by_var["V2"]}) is None
    assert fe._card_source_location_formula({"has_backtracking": False}, by_var) is None
    assert fe._card_source_location_formula(rule, {}) is None


@pytest.mark.parametrize("lang", ["fr", "ar", "hi"])
def test_the_labels_are_translated_from_the_catalogue(lang):
    from backend.i18n import catalogue
    for label in ("Table Header", "Cell Code"):
        out = catalogue.resolve(label, lang)
        assert out and out != label, (lang, label)
    # "DB TableName" is the validator's own column name (a technical identifier): it stays as written.
    assert catalogue.resolve("DB TableName", lang) == "DB TableName"
