"""Corpus-driven tests for the unified (V2) formula/dimension explanation flow.

These run against the REAL error files under D:\\Repo(new)\\Instance whenever
that repo is present, and skip cleanly when it is not — the point of the suite
is that the parsers are exercised on the actual structures, not on mocks. The
purely structural tests (expression grammar, message cleaning, header
detection, grounding gate) always run.

Every test below traces to a defect reproduced during the analysis, or to a
contract that must not regress (batch size, offsets, counts, no-hardcoding).
"""
from __future__ import annotations

import ast
import os
import re
import sys
from decimal import Decimal
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.tools import error_file_shape as shape           # noqa: E402
from backend.tools import error_llm                            # noqa: E402
from backend.tools import formula_error as fe                  # noqa: E402
from backend.tools import formula_expression as fx             # noqa: E402
from backend.tools import message_cleaner as mc                # noqa: E402
import backend.tools.report_lookup as rl                       # noqa: E402

CORPUS = Path(r"D:\Repo(new)\Instance")

# Named for readability only — every test resolves its file through the corpus
# root, and nothing in the production modules keys off any of these ids.
F_BT_4038   = CORPUS / "4038" / "IDIB250515R41915H_19-06-26_04-23-57_BTDetails.html"
F_BT_4080   = CORPUS / "4080" / "IDIB250515R41915H_19-06-26_04-23-57_BTDetails (5).html"
F_4044      = CORPUS / "4044" / "SMCB260630R25910Q_10-08-26_11-05-48_Instance.html"
F_4012      = CORPUS / "4012" / "ABPL220331R19704Q_11-06-26_03-30-51_Instance.html"
F_2065      = CORPUS / "2065" / "SOGE250331R10707A_25-04-25_05-23-47_Instance.html"
F_R162      = CORPUS / "R162" / "SHBK260331R16203Y_30-07-26_11-44-37_Instance (1) (1).html"
F_2047      = CORPUS / "2047" / "ICICI231231R21202Q_19-05-26_04-04-19_Instance.html"
F_2047_TYPED = CORPUS / "2047" / "SURY260630R21205Q_06-07-26_04-48-53_Instance.html"
F_2036      = CORPUS / "2036" / "CRLY260331R09605Q_15-04-26_08-14-12_Instance (1).html"
F_R376      = CORPUS / "R376" / "DOHB260531R37611M_30-06-26_10-20-56_Instance (2).html"

needs_corpus = pytest.mark.skipif(
    not CORPUS.is_dir(), reason=r"real repo data (D:\Repo(new)) not present",
)


@pytest.fixture(autouse=True)
def _deterministic(monkeypatch):
    """No LLM in tests: the whole suite must pass with Ollama unavailable, and
    every assertion below is about the deterministic layer.

    ERROR_CARD_V2 is pinned OFF for this whole file. This suite IS the
    specification of the legacy per-type section layout — it asserts headings
    ("How to Fix", "Dimensions involved"), their order, and the exact prose in
    them. The unified error card deliberately changes all three, so running it
    here would only re-assert v1's wording against v2's output.

    Keeping it pinned is what makes ERROR_CARD_V2=0 a real rollback rather than
    a hope: this file proves the old layout still builds correctly and is still
    reachable. The card's own contract is covered in test_error_card_v2.py.
    """
    monkeypatch.setenv("ERROR_EXPLAIN_LLM", "0")
    monkeypatch.setenv("ERROR_EXPLAIN_V2", "1")
    monkeypatch.setenv("ERROR_CARD_V2", "0")


def _explain(path, form_id, n=1):
    rules = fe.parse_formula_errors_v2(str(path))
    return rules, fe.explain_formula_rules(rules[:n], form_id=form_id, error_file_path=str(path))


# ═══════════════════════════════════════════════════════════════════════════
# 1. Expression grammar — the arithmetic defects
# ═══════════════════════════════════════════════════════════════════════════

class TestExpressionGrammar:
    def test_subtraction_is_not_summed(self):
        """'$V1 = $V2 + $V3 - $V4' was evaluated as V2+V3+V4."""
        c = fx.parse_formula("$V1 = $V2 + $V3 - $V4")
        r = fx.evaluate(c, {"V1": ["10"], "V2": ["10"], "V3": ["5"], "V4": ["3"]})
        assert r["rhs_value"] == Decimal(12)
        assert c.rhs.signed_variables() == [("V2", 1), ("V3", 1), ("V4", -1)]

    def test_sum_folds_every_fact_not_the_last(self):
        """'sum($V2)' over [177, 14, 3] collapsed to 3 under the old
        {var: fact} model."""
        c = fx.parse_formula("$V1 = sum ( $V2 )")
        r = fx.evaluate(c, {"V1": ["0"], "V2": ["177", "14", "3"]})
        assert r["rhs_value"] == Decimal(194)

    def test_bare_variable_with_several_facts_also_folds(self):
        c = fx.parse_formula("$V1 = $V2")
        r = fx.evaluate(c, {"V1": ["6"], "V2": ["1", "2", "3"]})
        assert r["rhs_value"] == Decimal(6) and r["passes"]

    def test_rounding_in_the_multiply_form_is_applied(self):
        """'round($V1 * 10) div 10' was ignored by the old divisor regex."""
        c = fx.parse_formula("round($V1 * 10) div 10 = round(($V2 + $V3 - $V4) * 10) div 10")
        r = fx.evaluate(c, {"V1": ["10.04"], "V2": ["10"], "V3": ["5"], "V4": ["5"]})
        assert r["uses_rounding"] and r["passes"]
        assert c.lhs.rounding_scale() == Decimal("0.1")

    def test_rounding_in_the_divide_form_is_applied(self):
        c = fx.parse_formula("round($V1 div 1000) * 1000 = round((sum ($V2)) div 1000 ) * 1000")
        assert c.lhs.rounding_scale() == Decimal(1000)
        r = fx.evaluate(c, {"V1": ["1000400"], "V2": ["1000000"]})
        assert r["uses_rounding"] and r["passes"]

    @pytest.mark.parametrize("op,lhs,rhs,passes", [
        ("=", "5", "5", True), ("=", "5", "6", False),
        (">", "6", "5", True), (">", "5", "5", False),
        (">=", "5", "5", True), (">=", "4", "5", False),
        ("<", "4", "5", True), ("<", "5", "5", False),
        ("<=", "5", "5", True), ("<=", "6", "5", False),
        ("!=", "5", "6", True), ("!=", "5", "5", False),
        ("<>", "5", "6", True), ("<>", "5", "5", False),
    ])
    def test_every_operator(self, op, lhs, rhs, passes):
        c = fx.parse_formula(f"$V1 {op} $V2")
        r = fx.evaluate(c, {"V1": [lhs], "V2": [rhs]})
        assert r["passes"] is passes

    def test_relationship_always_agrees_with_the_numbers(self):
        for a, b, expected in (("5", "4", "lhs_greater"), ("4", "5", "lhs_less"), ("5", "5", "lhs_equal")):
            r = fx.evaluate(fx.parse_formula("$V1 = $V2"), {"V1": [a], "V2": [b]})
            assert r["relationship"] == expected

    def test_nested_expression_and_precedence(self):
        c = fx.parse_formula("$V1 = ($V2 + $V3) * 2 div 4")
        r = fx.evaluate(c, {"V1": ["5"], "V2": ["4"], "V3": ["6"]})
        assert r["rhs_value"] == Decimal(5) and r["passes"]

    def test_missing_and_non_numeric_values_never_become_zero(self):
        for bad in ("#DIV/0!", "NA", "-84.55ab", "", "INF"):
            r = fx.evaluate(fx.parse_formula("$V1 > $V2"), {"V1": [bad], "V2": ["1"]})
            assert r is None, bad

    def test_thousands_separator_is_accepted(self):
        r = fx.evaluate(fx.parse_formula("$V1 = $V2"), {"V1": ["6,032"], "V2": ["6032"]})
        assert r["passes"]

    def test_zero_is_a_real_value_not_missing(self):
        r = fx.evaluate(fx.parse_formula("$V1 = $V2"), {"V1": ["0"], "V2": ["0"]})
        assert r is not None and r["passes"]

    def test_division_by_zero_yields_no_result_rather_than_a_number(self):
        assert fx.evaluate(fx.parse_formula("$V1 = $V2 div $V3"),
                           {"V1": ["1"], "V2": ["1"], "V3": ["0"]}) is None

    def test_presence_check_is_parsed_and_evaluated(self):
        c = fx.parse_formula("not(empty( $V1))")
        assert c.boolean_only
        assert fx.evaluate(c, {"V1": []})["passes"] is False
        assert fx.evaluate(c, {"V1": ["7"]})["passes"] is True

    def test_unmodelled_syntax_is_refused_not_guessed(self):
        assert fx.parse_formula("weird[$V1]/@thing") is None
        assert fx.parse_formula("") is None

    def test_xpath_round_half_goes_toward_positive_infinity(self):
        assert fx._round_half_up(Decimal("2.5")) == Decimal(3)
        assert fx._round_half_up(Decimal("-2.5")) == Decimal(-2)


# ═══════════════════════════════════════════════════════════════════════════
# 2. Message cleaning — the corrupted-label defects
# ═══════════════════════════════════════════════════════════════════════════

class TestMessageCleaning:
    CORRUPTING = [
        ('▼ &nbsp;"en:Identity " Closing balance of provisions held ( = Opening balance of '
         'provisions held + Fresh provisions made during the year - Excess provision reversed/ '
         'Write-off loans for the previous year.)" do not tally. "',
         "round($V1 * 10) div 10 = round(($V2 + $V3 - $V4) * 10) div 10"),
        ('▼ &nbsp;"en:Identity "Provisions (excluding Floating Provisions) ( = Sub-standard + '
         'Doubtful + Loss for the previous year.)" do not tally. "',
         "round($V1 * 10) div 10 = round(($V2 + $V3+ $V4) * 10) div 10"),
        ('▼ &nbsp;"en:Identity "Total NPA - Closing Balance" or "Total - Closing Balance" '
         '( = Opening Balance + Additions during the year - Reductions during the year for the '
         'previous year.)" do not tally."',
         "round($V1 * 10) div 10 = round(($V2 + $V3 - $V4) * 10) div 10"),
    ]

    @pytest.mark.parametrize("message,expr", CORRUPTING)
    def test_no_scaffolding_survives_into_a_label(self, message, expr):
        c = fx.parse_formula(expr)
        lhs, rhs = mc.split_operands(message, c.operator, len(c.lhs.variables()),
                                     c.rhs.signed_variables())
        for label in [lhs] + (rhs or []):
            if label is None:
                continue
            assert "do not tally" not in label.lower()
            assert "identity" not in label.lower()
            assert '"' not in label
            assert label.count("(") == label.count(")")
            assert not label.endswith("(")

    def test_validation_not_satisfied_prefix_is_stripped(self):
        text = mc.normalise_message(
            '▼ &nbsp;"en:Validation not satisfied: Complaints pending at the end of the period '
            'for 3. Other complaints = Pendency for less than 1 month"')
        assert text.startswith("Complaints pending at the end")

    def test_entities_are_decoded_before_the_operator_scan(self):
        lhs, rhs = mc.split_operands(
            '▼ "en:Identity "Gross advances &gt;= Net advances" do not tally."',
            ">=", 1, [("V2", 1)])
        assert (lhs, rhs) == ("Gross advances", ["Net advances"])

    def test_operator_inside_parentheses_is_not_a_split_point(self):
        lhs, rhs = mc.split_operands(
            '▼ "en:Identity "1. Agriculture &gt;= Priority Sector Agriculture(a+b=i+ii) " do not tally."',
            ">=", 1, [("V2", 1)])
        assert lhs == "1. Agriculture"
        assert rhs == ["Priority Sector Agriculture(a+b=i+ii)"]

    def test_split_is_rejected_when_its_arity_disagrees_with_the_formula(self):
        """Three message terms cannot label two formula variables — returning
        a partial split is what leaked the leftover text into the last label."""
        _lhs, rhs = mc.split_operands(
            '▼ "en:Identity "X = A + B + C" do not tally."', "=", 1, [("V2", 1), ("V3", 1)])
        assert rhs is None

    def test_split_is_rejected_when_the_sign_pattern_disagrees(self):
        _lhs, rhs = mc.split_operands(
            '▼ "en:Identity "X = A + B + C" do not tally."',
            "=", 1, [("V2", 1), ("V3", 1), ("V4", -1)])
        assert rhs is None

    def test_aggregate_terms_are_recovered_when_the_count_matches(self):
        terms = mc.split_aggregated_terms(
            '▼ "en:Validation not satisfied: Pending = Under 1 month + 1-3 months + Over 3 months"',
            "=", 3)
        assert terms == ["Under 1 month", "1-3 months", "Over 3 months"]

    def test_label_quality_gate(self):
        assert mc.looks_like_label("Total Term Loans Sanctioned")
        assert not mc.looks_like_label('Loss Advances" do not tally.')
        assert not mc.looks_like_label("Closing balance held (")
        assert not mc.looks_like_label("123")
        assert not mc.looks_like_label("")


# ═══════════════════════════════════════════════════════════════════════════
# 3. Backtracking detection — structural, never by form id
# ═══════════════════════════════════════════════════════════════════════════

class TestBacktrackingDetection:
    def test_header_vocabulary_decides(self):
        assert shape.header_has_backtracking(
            ["DB TableName", "Table Header", "Column Label(s)", "Variable Id",
             "Row Label(s)", "Instance Data(s)", "Entered Data(s)", "Unit",
             "Decimal", "Context", "Cell Code"])
        assert shape.header_has_backtracking(
            ["DB TableName", "Cell Index", "Table Header", "Column Label(s)",
             "Variable Id", "Row Label(s)", "Instance Data(s)", "Entered Data(s)",
             "Unit", "Decimal", "Context", "Cell Code"])
        assert not shape.header_has_backtracking(
            ["Variable", "Name", "Value", "Context", "Unit", "Decimal", "Precision"])
        assert not shape.header_has_backtracking([])
        assert not shape.header_has_backtracking(None)

    def test_column_order_does_not_matter(self):
        assert shape.header_has_backtracking(["Cell Code", "Unit", "DB TableName"])

    @needs_corpus
    @pytest.mark.parametrize("path,expected", [
        (F_BT_4038, True), (F_BT_4080, True),
        (F_4044, False),   # 4000-series WITHOUT backtracking — the mis-routed case
        (F_4012, False), (F_2065, False), (F_R162, False),
    ])
    def test_detection_on_real_files(self, path, expected):
        if not Path(path).is_file():
            pytest.skip(f"{path} absent")
        assert shape.describe_error_file(str(path))["formula_has_backtracking"] is expected

    def test_no_form_id_range_check_remains_in_the_v2_routing(self):
        """The unified flow must not consult the 4000-series range anywhere.

        Comments are stripped first — both modules document WHY the old
        form-id proxy was wrong, and that prose must not fail the check.
        """
        for name in ("formula_error", "dimension_error", "error_file_shape"):
            path = PROJECT_ROOT / "backend" / "tools" / f"{name}.py"
            code = "\n".join(
                line for line in path.read_text(encoding="utf-8").splitlines()
                if not line.lstrip().startswith("#")
            )
            assert "_is_4000_series" not in code, name
            assert not re.search(r"form_id\s*==", code), name
            assert not re.search(r"4\d{3}\s*<=", code), name


# ═══════════════════════════════════════════════════════════════════════════
# 4. Formula explanation on the real corpus
# ═══════════════════════════════════════════════════════════════════════════

@needs_corpus
class TestFormulaOnRealFiles:
    def test_4000_series_with_backtracking_uses_the_source_data(self):
        if not F_BT_4038.is_file():
            pytest.skip("file absent")
        rules, out = _explain(F_BT_4038, "4038", 1)
        assert rules[0]["has_backtracking"] is True
        text = out[0]["explanation"]
        assert "CIMS_MPD03_CRR_LAYOUT3_HM" in text        # DB table from the BT row
        assert "Y250_X030" in text                        # cell code
        assert "13459.2420" in text                       # the value the user typed
        assert "134,592,420,000" in text                  # the value in the instance
        assert "8,972,828,000" in text                    # the verified difference
        assert "nearest ₹1,000" in text

    def test_aggregate_over_many_facts_is_summed_not_collapsed(self):
        if not F_BT_4038.is_file():
            pytest.skip("file absent")
        _rules, out = _explain(F_BT_4038, "4038", 1)
        # 14 daily values; the previous model kept only the last one.
        assert "total of 14 reported values" in out[0]["explanation"]

    def test_presence_check_rule_does_not_crash_and_says_something_useful(self):
        if not F_BT_4038.is_file():
            pytest.skip("file absent")
        rules = fe.parse_formula_errors_v2(str(F_BT_4038))
        presence = [r for r in rules if "empty" in r["formula_expression"]]
        assert presence, "expected a not(empty(...)) rule in this file"
        out = fe.explain_formula_rules(presence, form_id="4038", error_file_path=str(F_BT_4038))
        text = out[0]["explanation"].lower()
        assert "does not satisfy the condition" in text
        assert "how to fix" in text

    def test_4000_series_without_backtracking_still_explains(self):
        if not F_4044.is_file():
            pytest.skip("file absent")
        rules, out = _explain(F_4044, "4044", 3)
        assert all(r["has_backtracking"] is False for r in rules)
        text = out[0]["explanation"]
        assert "⚙ Formula Error" in text
        assert "Reported Values" in text
        assert "Where to Check" not in text   # nothing to point at — not invented

    def test_variable_ids_carry_no_stray_quote(self):
        if not F_4044.is_file():
            pytest.skip("file absent")
        rules = fe.parse_formula_errors_v2(str(F_4044))
        for rule in rules:
            for instance in rule["instances"]:
                for fact in instance["facts"]:
                    assert re.fullmatch(r"V\d+", fact["var"]), fact["var"]

    def test_aggregate_components_are_named_individually(self):
        if not F_4044.is_file():
            pytest.skip("file absent")
        _rules, out = _explain(F_4044, "4044", 1)
        text = out[0]["explanation"]
        assert "Pendency for less than 1 month" in text
        assert "Pendency for 1-3 months" in text
        assert "Pendency for greater than 3 months" in text

    @pytest.mark.parametrize("path,form_id", [
        (F_2065, "2065"), (F_R162, "R162"), (F_4044, "4044"), (F_4012, "4012"),
    ])
    def test_no_corrupted_text_reaches_the_user(self, path, form_id):
        if not Path(path).is_file():
            pytest.skip("file absent")
        rules = fe.parse_formula_errors_v2(str(path))
        out = fe.explain_formula_rules(rules, form_id=form_id, error_file_path=str(path))
        for item in out:
            text = item["explanation"]
            assert "do not tally" not in text.lower()
            assert "en:Identity" not in text
            assert "BeginningBalance)" not in text
            assert not re.search(r"\bV\d+\b", text), text[:200]

    def test_json_enrichment_is_used_when_present(self):
        if not F_2065.is_file():
            pytest.skip("file absent")
        _rules, out = _explain(F_2065, "2065", 3)
        assert all(item["_error_category"] == "formula_error" for item in out)

    def test_missing_json_does_not_break_explanation(self):
        """R162 and 4044 have no Json/<form_id> extract at all."""
        for path, form_id in ((F_R162, "R162"), (F_4044, "4044")):
            if not Path(path).is_file():
                continue
            _rules, out = _explain(path, form_id, 2)
            assert out and all(item["explanation"].strip() for item in out)

    def test_comparison_operators_appear_across_the_corpus(self):
        if not F_2065.is_file():
            pytest.skip("file absent")
        rules = fe.parse_formula_errors_v2(str(F_2065))
        operators = set()
        for rule in rules:
            c = fx.parse_formula(rule["formula_expression"])
            if c:
                operators.add(c.operator)
        assert {">", ">=", "="} & operators

    def test_multi_instance_rule_reports_its_count(self):
        if not F_2065.is_file():
            pytest.skip("file absent")
        rules = fe.parse_formula_errors_v2(str(F_2065))
        many = [r for r in rules if len(r["instances"]) > 1]
        assert many, "expected a rule failing more than once"
        out = fe.explain_formula_rules(many[:1], form_id="2065", error_file_path=str(F_2065))
        assert "reported items" in out[0]["explanation"]


# ═══════════════════════════════════════════════════════════════════════════
# 5. Dimension explanation on the real corpus
# ═══════════════════════════════════════════════════════════════════════════

@needs_corpus
class TestDimensionOnRealFiles:
    def _errors(self, path):
        from backend.tools.dimension_error import parse_dimension_errors
        return parse_dimension_errors(str(path))

    def _explained(self, path, form_id, n=1):
        from backend.tools.dimension_error import explain_dimension_errors
        errors = self._errors(path)
        return errors, explain_dimension_errors(errors[:n], form_id=form_id,
                                                error_file_path=str(path))

    def test_attribute_values_with_spaces_are_not_truncated(self):
        """'value = 2. In ATM' used to be captured as '2.'."""
        if not F_2047.is_file():
            pytest.skip("file absent")
        errors = self._errors(F_2047)
        assert any(e["value"] == "2. In ATM" for e in errors)

    def test_empty_unit_does_not_swallow_the_next_key(self):
        """'unit = decimal = precision =' used to yield unit='decimal'."""
        if not F_2047.is_file():
            pytest.skip("file absent")
        for err in self._errors(F_2047):
            assert err["unit"] != "decimal"

    def test_2047_resolves_its_taxonomy_instead_of_giving_up(self):
        """All 23 of 2047's dimension errors previously returned
        'Cannot be determined' because the definition linkbase
        (in-rbi-rep-fmr4_def1.xml) could not be found by filename."""
        if not F_2047.is_file():
            pytest.skip("file absent")
        errors, out = self._explained(F_2047, "2047", 3)
        assert len(errors) == 23
        for item in out:
            evidence = item["_dimension_evidence"]
            assert evidence["taxonomy_found"] is True
            assert evidence["expected_axes"], item["concept"]
            assert "Cannot be determined" not in item["explanation"]

    def test_explicit_dimension_lists_its_allowed_members(self):
        if not F_2047.is_file():
            pytest.skip("file absent")
        _errors, out = self._explained(F_2047, "2047", 1)
        axes = out[0]["_dimension_evidence"]["expected_axes"]
        explicit = [a for a in axes if not a["is_typed"]]
        assert explicit and explicit[0]["allowed_members"]
        assert explicit[0]["allowed_members"][0]["label"] in out[0]["explanation"]

    def test_typed_dimension_states_the_required_value_type(self):
        if not F_2047_TYPED.is_file():
            pytest.skip("file absent")
        _errors, out = self._explained(F_2047_TYPED, "2047", 1)
        text = out[0]["explanation"]
        sections = {s["heading"]: s for s in out[0]["explanation_sections"] if s.get("heading")}
        kinds = {i["label"]: i["value"] for i in sections["Details This Figure Must Carry"]["items"]}
        assert set(kinds.values()) == {"You enter the value"}
        assert "YYYY-MM-DDThh:mm:ss" in text          # from xsd:dateTime, not hardcoded
        evidence = out[0]["_dimension_evidence"]
        assert evidence["focus_axis"]["required_value"]["base_type"].endswith("dateTime")

    def test_typed_dimension_of_a_different_base_type(self):
        """A second, structurally different typed axis (xsd:date, not
        dateTime) must be described from its own declaration."""
        if not F_4012.is_file():
            pytest.skip("file absent")
        from backend.tools.dimension_error import explain_dimension_errors
        errors = self._errors(F_4012)
        typed = [e for e in errors if "IllegalTypedDimension" in e["error_class"]]
        assert typed
        out = explain_dimension_errors(typed[:1], form_id="4012",
                                       error_file_path=str(F_4012))
        required = out[0]["_dimension_evidence"]["focus_axis"]["required_value"]
        assert required["base_type"].endswith("date")
        assert "YYYY-MM-DD" in out[0]["explanation"]

    def test_multi_axis_concept_names_every_required_axis(self):
        if not F_4012.is_file():
            pytest.skip("file absent")
        from backend.tools.dimension_error import explain_dimension_errors
        errors = self._errors(F_4012)
        primary = [e for e in errors if "PrimaryItem" in e["error_class"]]
        out = explain_dimension_errors(primary[:1], form_id="4012",
                                       error_file_path=str(F_4012))
        axes = out[0]["_dimension_evidence"]["expected_axes"]
        assert len(axes) >= 3
        for axis in axes:
            assert axis["label"] in out[0]["explanation"]

    def test_context_id_segment_is_never_presented_as_a_dimension_value(self):
        """A context concatenates every dimension it carries; its trailing
        segment frequently belongs to a different axis (4012's DateAxis error
        ends in 'FluctuationOfPriceAndFreightRiskMember')."""
        if not F_4012.is_file():
            pytest.skip("file absent")
        from backend.tools.dimension_error import explain_dimension_errors
        errors = self._errors(F_4012)
        typed = [e for e in errors if "IllegalTypedDimension" in e["error_class"]]
        out = explain_dimension_errors(typed[:1], form_id="4012",
                                       error_file_path=str(F_4012))
        check = out[0]["_dimension_evidence"]["typed_value_check"]
        assert check["reported_source"] in ("instance_document", "validator_message", "unavailable")
        assert check["reported_source"] != "context_id_suffix"

    def test_no_instance_document_degrades_honestly(self):
        if not F_4012.is_file():
            pytest.skip("file absent")
        _errors, out = self._explained(F_4012, "4012", 1)
        evidence = out[0]["_dimension_evidence"]
        assert evidence["instance_document_used"] is False
        assert "no generated return file was saved for this run" in out[0]["explanation"]

    def test_panel_bounding_stops_table_warnings_being_read_as_dimension_errors(self):
        """2036 has a DIMENSION badge of 0 and a TABLE badge of 42; an
        unbounded directMsg scan returns all 42."""
        if not F_2036.is_file():
            pytest.skip("file absent")
        assert self._errors(F_2036) == []

    def test_counts_match_the_legacy_parser_across_the_corpus(self):
        """The underlying validation result must not change — only the
        explanation of it."""
        for path in CORPUS.rglob("*.html"):
            assert len(self._errors(path)) == len(
                rl.parse_dimensional_html_errors(str(path))), path

    def test_a_second_return_with_many_errors_is_fully_explained(self):
        if not F_R376.is_file():
            pytest.skip("file absent")
        errors, out = self._explained(F_R376, "R376", 3)
        assert len(errors) == 31
        assert all(item["explanation"].strip() for item in out)

    def test_same_file_under_different_form_ids_explains_identically(self):
        """The identical BTDetails file exists under 4038, 4046 and 4080 —
        proof that form_id is not load-bearing for the explanation itself."""
        from backend.tools.dimension_error import explain_dimension_errors
        if not (F_BT_4038.is_file() and F_BT_4080.is_file()):
            pytest.skip("files absent")
        a = explain_dimension_errors(self._errors(F_BT_4038)[:1], form_id="4038",
                                     error_file_path=str(F_BT_4038))
        b = explain_dimension_errors(self._errors(F_BT_4080)[:1], form_id="4080",
                                     error_file_path=str(F_BT_4080))
        assert a[0]["concept"] == b[0]["concept"]
        assert a[0]["context"] == b[0]["context"]


# ═══════════════════════════════════════════════════════════════════════════
# 6. Malformed / partial input
# ═══════════════════════════════════════════════════════════════════════════

class TestMalformedInput:
    def test_missing_file(self, tmp_path):
        from backend.tools.dimension_error import parse_dimension_errors
        assert fe.parse_formula_errors_v2(str(tmp_path / "nope.html")) == []
        assert parse_dimension_errors(str(tmp_path / "nope.html")) == []
        assert shape.describe_error_file(str(tmp_path / "nope.html"))["exists"] is False

    def test_empty_file(self, tmp_path):
        path = tmp_path / "empty.html"
        path.write_text("", encoding="utf-8")
        assert fe.parse_formula_errors_v2(str(path)) == []

    def test_truncated_mid_table(self, tmp_path):
        path = tmp_path / "cut.html"
        path.write_text(
            '<div class="tab-pane" id="1"><div class="panel panel-default" id="errorPanel1">'
            '<div class="assertionLabel">R</div><div class="formulaErrorTest">$V1 = $V2</div>'
            '<table><tr class="hide"><td class="headerCell">Variable</td></tr>'
            '<tr class="hide fv"><td class="msgBodyCell">V1',
            encoding="utf-8")
        assert fe.parse_formula_errors_v2(str(path)) == []   # no complete table, nothing invented

    def test_header_row_without_body_rows(self, tmp_path):
        path = tmp_path / "hdr.html"
        path.write_text(
            '<div class="tab-pane" id="1"><div class="panel panel-default" id="errorPanel1">'
            '<div class="assertionLabel">R</div><div class="formulaErrorTest">$V1 = $V2</div>'
            '<table><tr class="msgHead"><td class="formulaErrorTitle">"en:Identity "A = B" do not tally."</td></tr>'
            '<tr class="hide"><td class="headerCell">Variable</td><td class="headerCell">Value</td></tr>'
            '</table></div></div>', encoding="utf-8")
        rules = fe.parse_formula_errors_v2(str(path))
        assert len(rules) == 1 and rules[0]["instances"][0]["facts"] == []
        out = fe.explain_formula_rules(rules, form_id="", error_file_path=str(path))
        assert out[0]["explanation"].strip()

    def test_cell_count_not_matching_header_count_drops_the_row(self, tmp_path):
        path = tmp_path / "mismatch.html"
        path.write_text(
            '<div class="tab-pane" id="1"><div class="panel panel-default" id="errorPanel1">'
            '<div class="assertionLabel">R</div><div class="formulaErrorTest">$V1 = $V2</div>'
            '<table><tr class="hide"><td class="headerCell">Variable</td><td class="headerCell">Value</td></tr>'
            '<tr class="hide fv"><td class="msgBodyCell">V1</td><td class="msgBodyCell">1</td>'
            '<td class="msgBodyCell">extra</td></tr></table></div></div>', encoding="utf-8")
        # No mappable row and no message leaves nothing to explain, so the
        # rule is dropped rather than reported with invented/shifted fields.
        assert fe.parse_formula_errors_v2(str(path)) == []

    def test_non_numeric_badge(self, tmp_path):
        path = tmp_path / "badge.html"
        path.write_text(
            '<div class="tab-pane" id="1"><div class="panel panel-default" id="errorPanel1">'
            '<div class="assertionLabel">R</div><div class="formulaErrorTest">$V1 = $V2</div>'
            '<div class="badge">many</div>'
            '<table><tr class="hide"><td class="headerCell">Variable</td><td class="headerCell">Value</td></tr>'
            '<tr class="hide fv"><td class="msgBodyCell">V1</td><td class="msgBodyCell">1</td></tr>'
            '</table></div></div>', encoding="utf-8")
        assert fe.parse_formula_errors_v2(str(path))[0]["error_count"] == 1

    def test_xml_only_error_file(self, tmp_path):
        path = tmp_path / "x.xml"
        path.write_text("<Errors><ErrorMessage>bad</ErrorMessage></Errors>", encoding="utf-8")
        assert shape.describe_error_file(str(path))["kind"] == "xml"
        assert fe.parse_formula_errors_v2(str(path)) == []


# ═══════════════════════════════════════════════════════════════════════════
# 7. LLM grounding gate
# ═══════════════════════════════════════════════════════════════════════════

class TestGroundingGate:
    PAYLOAD = {
        "checked_value": {"label": "Total advances", "value": "100"},
        "compared_against": [{"label": "Secured advances", "value": "60"}],
        "difference": "40",
        "relationship": "lhs_greater",
    }
    TERMS = ["Total advances", "Secured advances"]

    def _ok(self, text):
        return error_llm.is_grounded(text, self.PAYLOAD, self.TERMS)[0]

    def test_accepts_grounded_text(self):
        assert self._ok("Total advances of 100 exceeds Secured advances of 60 by 40.")

    def test_rejects_an_invented_number(self):
        assert not self._ok("Total advances of 100 exceeds Secured advances by 4321.")

    def test_rejects_a_dropped_label(self):
        assert not self._ok("The total exceeds the secured amount by 40.")

    def test_rejects_a_leaked_variable_id(self):
        assert not self._ok("Total advances (V1) exceeds Secured advances (V2) by 40.")

    def test_rejects_contradicting_an_equal_relationship(self):
        payload = dict(self.PAYLOAD, relationship="lhs_equal")
        ok, _ = error_llm.is_grounded(
            "Total advances exceeds Secured advances.", payload, self.TERMS)
        assert not ok

    def test_rejects_an_invented_taxonomy_member(self):
        payload = {"_allowed_member_terms": ["OTCMember"], "relationship": None}
        ok, _ = error_llm.is_grounded("Use ExchangeTradedMember instead.", payload, [])
        assert not ok

    def test_small_integers_in_prose_are_allowed(self):
        assert self._ok("Both Total advances and Secured advances appear in 2 places; "
                        "the gap is 40 between 100 and 60.")

    def test_number_formatting_variants_compare_equal(self):
        payload = {"difference": "1234567.50", "relationship": None}
        ok, _ = error_llm.is_grounded("The gap is 1,234,567.5.", payload, [])
        assert ok

    def test_phrase_returns_none_when_disabled(self, monkeypatch):
        monkeypatch.setenv("ERROR_EXPLAIN_LLM", "0")
        assert error_llm.phrase(self.PAYLOAD, self.TERMS, {"why_failed": "x"}) is None


# ═══════════════════════════════════════════════════════════════════════════
# 8. Routing, batching and counting contracts under V2
# ═══════════════════════════════════════════════════════════════════════════

class TestUnifiedFlowBatching:
    """The same batching/counting contract the legacy tests assert, proven for
    the unified flow (which those tests can no longer reach)."""

    def _rules(self, n):
        return [{"rule_name": f"Rule{i}", "formula_expression": "$V1 = $V2",
                 "error_count": 1, "has_backtracking": False,
                 "instances": [{"business_message": "", "facts": []}]} for i in range(n)]

    @pytest.fixture
    def html(self, tmp_path):
        path = tmp_path / "errors.html"
        path.write_text("<html><body>placeholder</body></html>", encoding="utf-8")
        return str(path)

    def test_batch_size_and_offset(self, monkeypatch, html):
        rules = self._rules(8)
        monkeypatch.setattr("backend.tools.formula_error.parse_formula_errors_v2",
                            lambda path: rules)
        captured = {}
        monkeypatch.setattr(
            "backend.tools.formula_error.explain_formula_rules",
            lambda trimmed, form_id="", error_file_path="": captured.setdefault(
                "names", [r["rule_name"] for r in trimmed]) or trimmed,
        )
        rl.explain_errors_by_category(html, "formula_error", form_id="4046", offset=0)
        assert captured["names"] == ["Rule0", "Rule1", "Rule2"]
        captured.clear()
        rl.explain_errors_by_category(html, "formula_error", form_id="4046", offset=6)
        assert captured["names"] == ["Rule6", "Rule7"]

    def test_offset_past_end_returns_empty(self, monkeypatch, html):
        monkeypatch.setattr("backend.tools.formula_error.parse_formula_errors_v2",
                            lambda path: self._rules(3))
        assert rl.explain_errors_by_category(html, "formula_error", form_id="4046", offset=3) == []

    def test_count_is_distinct_rules_not_occurrences(self, monkeypatch, html):
        rules = self._rules(3)
        for rule in rules:
            rule["error_count"] = 149
        monkeypatch.setattr("backend.tools.formula_error.parse_formula_errors_v2",
                            lambda path: rules)
        assert rl.count_errors_by_category(html, form_id="4046")["formula_error"] == 3

    def test_count_uses_the_same_parser_regardless_of_form_id(self, monkeypatch, html):
        """The legacy path chose its counting parser from form_id, so a caller
        that omitted form_id counted with a different parser than the one that
        later explained."""
        monkeypatch.setattr("backend.tools.formula_error.parse_formula_errors_v2",
                            lambda path: self._rules(5))
        assert (rl.count_errors_by_category(html, form_id="")["formula_error"]
                == rl.count_errors_by_category(html, form_id="2065")["formula_error"]
                == rl.count_errors_by_category(html, form_id="4046")["formula_error"] == 5)

    def test_dimensional_batching_applies_offset(self, monkeypatch, html):
        errors = [{"concept": f"C{i}", "context": f"ctx{i}", "error_class": "x"} for i in range(8)]
        monkeypatch.setattr("backend.tools.dimension_error.parse_dimension_errors",
                            lambda path: errors)
        captured = {}
        monkeypatch.setattr(
            "backend.tools.dimension_error.explain_dimension_errors",
            lambda trimmed, form_id="", error_file_path="": captured.setdefault(
                "ids", [e["concept"] for e in trimmed]) or trimmed,
        )
        rl.explain_errors_by_category(html, "dimensional", form_id="2047", offset=3)
        assert captured["ids"] == ["C3", "C4", "C5"]

    def test_legacy_flow_is_still_reachable(self, monkeypatch, html):
        monkeypatch.setenv("ERROR_EXPLAIN_V2", "0")
        called = {}
        monkeypatch.setattr(rl, "parse_formula_errors",
                            lambda path: called.setdefault("legacy", True) or [])
        rl.explain_errors_by_category(html, "formula_error", form_id="4046")
        assert called.get("legacy") is True


# ═══════════════════════════════════════════════════════════════════════════
# 9. Instance-document resolution (InstanceDocPath only)
# ═══════════════════════════════════════════════════════════════════════════

class TestInstanceDocResolution:
    def test_resolved_from_the_instance_log_row_for_this_error_file(self, monkeypatch, tmp_path):
        instance_dir = tmp_path / "Instance" / "2047"
        instance_dir.mkdir(parents=True)
        (instance_dir / "RUN_Instance.xml").write_text(
            "<xbrli:xbrl xmlns:xbrli='http://www.xbrl.org/2003/instance'></xbrli:xbrl>",
            encoding="utf-8")
        (instance_dir / "RUN_Instance.html").write_text("<html></html>", encoding="utf-8")

        monkeypatch.setattr("backend.config.instance_base_dir",
                            lambda: str(tmp_path / "Instance"))
        monkeypatch.setattr(rl, "_parse_instances", lambda: (
            {"FormId": "2047", "ErrorDocPath": "RUN_Instance.html",
             "InstanceDocPath": "RUN_Instance.xml"},
        ))
        resolved = rl.resolve_instance_doc_path(str(instance_dir / "RUN_Instance.html"), "2047")
        assert resolved == str(instance_dir / "RUN_Instance.xml")

    def test_empty_when_the_row_records_no_instance_doc(self, monkeypatch, tmp_path):
        monkeypatch.setattr(rl, "_parse_instances", lambda: (
            {"FormId": "2047", "ErrorDocPath": "RUN_Instance.html", "InstanceDocPath": ""},
        ))
        assert rl.resolve_instance_doc_path("/x/RUN_Instance.html", "2047") == ""

    def test_empty_when_the_named_file_is_absent(self, monkeypatch, tmp_path):
        monkeypatch.setattr("backend.config.instance_base_dir", lambda: str(tmp_path))
        monkeypatch.setattr(rl, "_parse_instances", lambda: (
            {"FormId": "2047", "ErrorDocPath": "RUN_Instance.html",
             "InstanceDocPath": "GONE.xml"},
        ))
        assert rl.resolve_instance_doc_path("/x/RUN_Instance.html", "2047") == ""

    def test_a_neighbouring_runs_document_is_never_picked_up(self, monkeypatch, tmp_path):
        """The folder holds every run for the form; only this run's own
        InstanceDocPath may be used."""
        folder = tmp_path / "Instance" / "2047"
        folder.mkdir(parents=True)
        (folder / "OTHER_Instance.xml").write_text(
            "<xbrli:xbrl xmlns:xbrli='http://www.xbrl.org/2003/instance'></xbrli:xbrl>",
            encoding="utf-8")
        (folder / "MINE_Instance.html").write_text("<html></html>", encoding="utf-8")
        monkeypatch.setattr("backend.config.instance_base_dir",
                            lambda: str(tmp_path / "Instance"))
        monkeypatch.setattr(rl, "_parse_instances", lambda: (
            {"FormId": "2047", "ErrorDocPath": "OTHER_Instance.html",
             "InstanceDocPath": "OTHER_Instance.xml"},
        ))
        from backend.tools import instance_context
        assert instance_context.find_instance_document(
            str(folder / "MINE_Instance.html"), "2047") is None


# âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
# 10. Fact-to-variable grounding
#
# Regression cover for the case where several variables of one formula bind to
# the SAME concept name and are separated only by their dimensional context.
# Collapsing them loses real values (one of five SubstandardAdvances facts is
# 82,556,000 while the other four are 0), and printing only rounded totals next
# to raw component rows makes the explanation contradict its own evidence.
# âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ

F_2041 = CORPUS / "2041" / "CLBL260630R09101Q_21-07-26_10-17-15_Instance (1).html"

RULE_SIMPLE   = "Sec-8_SectoralCredit_TotalTermLoansSanctionedAndTotalTermLoansDisbursed"
RULE_REPEATED = "SectoralCredit_OtherThanPrioritySectorMicroMedLar"
RULE_ROUNDING = "Sec-8ndustryBreakupNPABreakup"


def _rule_named(path, name):
    for rule in fe.parse_formula_errors_v2(str(path)):
        if rule["rule_name"] == name:
            return rule
    pytest.skip(f"{name} not present in {path}")


class TestFactBindingUnit:
    """Structural, corpus-independent: the same guarantees on synthetic facts."""

    def _rule(self):
        contexts = ["asof_1_TotalMember", "asof_1_AMember", "asof_1_BMember",
                    "asof_1_CMember", "asof_1_DMember"]
        values = ["0", "0", "0", "0", "82556000"]
        return {
            "rule_name": "R", "has_backtracking": False, "error_count": 1,
            "formula_expression":
                "round($V1 div 100000) * 100000 = round(($V2 + $V3 + $V4 + $V5) div 100000) * 100000",
            "instances": [{
                "business_message": "",
                "facts": [
                    {"var": f"V{i + 1}", "concept": "SameConcept", "value": v,
                     "context": c, "unit": "INR", "decimal": "-3", "precision": ""}
                    for i, (v, c) in enumerate(zip(values, contexts))
                ],
            }],
        }

    def test_every_variable_keeps_its_own_value(self):
        rule = self._rule()
        comparison, result = fe.evaluate_instance(rule, rule["instances"][0])
        labels, _sources = fe.resolve_labels(rule, comparison)
        text = fe.render_explanation(rule, comparison, result, labels)
        assert "82,556,000" in text          # the one non-zero fact survives
        assert text.count("₹0") >= 4       # and all four zeros are shown

    def test_identical_concepts_get_distinct_labels_from_context(self):
        rule = self._rule()
        comparison, _result = fe.evaluate_instance(rule, rule["instances"][0])
        labels, sources = fe.resolve_labels(rule, comparison)
        business = [labels[v] for v in comparison.variables()]
        assert len(set(business)) == len(business), business
        for var in comparison.variables():
            assert "context" in sources[var]

    def test_labels_stay_identical_when_nothing_distinguishes_them(self):
        """No fabricated qualifier: identical contexts must not invent one."""
        rule = self._rule()
        for fact in rule["instances"][0]["facts"]:
            fact["context"] = "asof_1_SameMember"
        comparison, _result = fe.evaluate_instance(rule, rule["instances"][0])
        labels, _sources = fe.resolve_labels(rule, comparison)
        assert len({labels[v] for v in comparison.variables()}) == 1

    def test_context_is_shown_only_when_labels_cannot_distinguish_the_facts(self):
        """Raw context ids are internal detail. They appear only in the one
        case where they are genuinely needed — when the resolved labels are
        still identical — and are suppressed once a business qualifier has
        been derived."""
        rule = self._rule()
        comparison, result = fe.evaluate_instance(rule, rule["instances"][0])
        labels, _ = fe.resolve_labels(rule, comparison)
        text = fe.render_explanation(rule, comparison, result, labels)
        assert all(f["context"] not in text for f in rule["instances"][0]["facts"])

        # Identical contexts -> no qualifier can be derived -> show the context.
        for fact in rule["instances"][0]["facts"]:
            fact["context"] = "asof_1_SameMember"
        comparison, result = fe.evaluate_instance(rule, rule["instances"][0])
        labels, _ = fe.resolve_labels(rule, comparison)
        text = fe.render_explanation(rule, comparison, result, labels)
        assert "asof_1_SameMember" in text

    def test_raw_and_rounded_are_both_reported(self):
        rule = self._rule()
        comparison, result = fe.evaluate_instance(rule, rule["instances"][0])
        assert result["rhs_raw"] == Decimal(82556000)
        assert result["rhs_value"] == Decimal(82600000)
        assert result["rounding_changed_a_value"] is True
        text = fe.render_explanation(rule, comparison, result,
                                     fe.resolve_labels(rule, comparison)[0])
        assert "₹82,556,000 → rounds to ₹82,600,000" in text

    def test_llm_payload_preserves_the_variable_to_fact_mapping(self):
        rule = self._rule()
        comparison, result = fe.evaluate_instance(rule, rule["instances"][0])
        labels, _ = fe.resolve_labels(rule, comparison)
        payload, _terms = fe.build_llm_payload(rule, comparison, result, labels)
        by_var = {entry["variable"]: entry for entry in payload["variables"]}
        assert set(by_var) == {"V1", "V2", "V3", "V4", "V5"}
        assert by_var["V5"]["facts"][0]["value"] == "82556000"
        assert by_var["V5"]["facts"][0]["context"] == "asof_1_DMember"
        assert by_var["V2"]["facts"][0]["value"] == "0"
        for entry in payload["variables"]:
            fact = entry["facts"][0]
            assert set(fact) == {"value", "context", "unit", "decimal", "precision"}
        assert payload["_values_are_uniform"] is False
        assert payload["left_side"]["raw_value"] == "0"
        assert payload["right_side"]["raw_value"] == "82556000"
        assert payload["right_side"]["compared_value"] == "82600000"

    def test_rounding_that_changes_nothing_is_not_dressed_up(self):
        rule = self._rule()
        for fact, value in zip(rule["instances"][0]["facts"],
                               ["100000", "100000", "0", "0", "0"]):
            fact["value"] = value
        comparison, result = fe.evaluate_instance(rule, rule["instances"][0])
        assert result["rounding_changed_a_value"] is False
        text = fe.render_explanation(rule, comparison, result,
                                     fe.resolve_labels(rule, comparison)[0])
        assert "→ rounds to" not in text


@needs_corpus
class TestFactBindingOnRealFiles:
    def test_simple_comparison_binds_both_variables(self):
        rule = _rule_named(F_2041, RULE_SIMPLE)
        facts = {f["var"]: f for f in rule["instances"][0]["facts"]}
        assert facts["V1"]["concept"] == "TermLoansSanctioned"
        assert facts["V2"]["concept"] == "TermLoansDisbursed"
        out = fe.explain_formula_rules([rule], form_id="2041", error_file_path=str(F_2041))
        text = out[0]["explanation"]
        assert "Term Loans Sanctioned must be greater than Term Loans Disbursed" in text
        sections = {s["heading"]: s for s in out[0]["explanation_sections"] if s.get("heading")}
        values = {i["label"]: i["value"] for i in sections["Reported Values"]["items"]}
        assert values == {"Term Loans Sanctioned": "₹7,945,932,000",
                          "Term Loans Disbursed": "₹7,945,932,000"}

    def test_repeated_concept_keeps_five_distinct_facts(self):
        rule = _rule_named(F_2041, RULE_REPEATED)
        facts = {f["var"]: f for f in rule["instances"][0]["facts"]}
        assert len(facts) == 5
        assert {f["concept"] for f in facts.values()} == {"SubstandardAdvances"}
        assert facts["V5"]["value"] == "82556000"
        assert all(facts[v]["value"] == "0" for v in ("V1", "V2", "V3", "V4"))

        out = fe.explain_formula_rules([rule], form_id="2041", error_file_path=str(F_2041))
        text = out[0]["explanation"]
        assert "₹82,556,000 → rounds to ₹82,600,000" in text

        sections = {s["heading"]: s for s in out[0]["explanation_sections"] if s.get("heading")}
        items = sections["Reported Values"]["items"]
        # Five facts, five distinct labels, five distinct values preserved.
        assert len(items) == 5
        assert len({i["label"] for i in items}) == 5
        assert sum(1 for i in items if i["value"] == "₹82,556,000") == 1
        assert sum(1 for i in items if i["value"] == "₹0") == 4
        rule_text = sections["Validation Rule"]["text"]
        assert rule_text.count("Substandard advances — ") == 5
        assert "Other" in rule_text and "PSUs" in rule_text

    def test_rounding_case_never_calls_a_raw_value_by_its_rounded_figure(self):
        rule = _rule_named(F_2041, RULE_ROUNDING)
        out = fe.explain_formula_rules([rule], form_id="2041", error_file_path=str(F_2041))
        text = out[0]["explanation"]
        sections = {s["heading"]: s for s in out[0]["explanation_sections"] if s.get("heading")}
        reported = {i["label"]: i["value"] for i in sections["Reported Values"]["items"]}
        assert reported["Loss advances"] == "₹34,000"        # raw component, not 0
        compared = {i["label"]: i["value"] for i in sections["Comparison"]["items"]}
        assert compared["Reported"] == "₹608,709,000 → rounds to ₹608,700,000"
        assert compared["Calculated/Combined"] == "₹34,000 → rounds to ₹0"
        assert compared["Difference (after rounding)"] == "₹608,700,000"
        assert compared["Rounding"] == "nearest ₹100,000"
        # The old failure: a combined value of 0 printed beside components that
        # visibly add to 34,000, with no stated reason.
        assert "₹34,000" in text and "rounds to ₹0" in text

    def test_arithmetic_is_internally_consistent_across_the_corpus(self):
        """Whatever is reported as the combined right-hand value must equal the
        signed sum of the component facts printed above it."""
        for path in CORPUS.rglob("*.html"):
            for rule in fe.parse_formula_errors_v2(str(path)):
                comparison, result = fe.evaluate_instance(rule, rule["instances"][0])
                if not comparison or not result or result.get("boolean_only"):
                    continue
                by_var = {}
                for fact in rule["instances"][0]["facts"]:
                    by_var.setdefault(fact["var"], []).append(fact)
                signed = comparison.rhs.signed_variables() if comparison.rhs is not None else []
                if not signed:
                    continue
                expected, usable = Decimal(0), True
                for var, sign in signed:
                    total = fe._var_total(by_var, var)
                    if total is None:
                        usable = False
                        break
                    expected += total * sign
                if usable and result["rhs_raw"] is not None:
                    assert result["rhs_raw"] == expected, (path, rule["rule_name"])


class TestGroundingGateArithmetic:
    def test_rejects_a_sum_that_does_not_add_up(self):
        ok, reason = error_llm.is_grounded(
            "The components 0 + 0 + 34000, which equals 0, fall short.",
            {"relationship": None, "values": ["0", "34000"]}, [])
        assert not ok and "arithmetic" in reason

    def test_accepts_a_sum_that_does_add_up(self):
        ok, _ = error_llm.is_grounded("0 + 0 + 34000 equals 34000.",
                                      {"relationship": None, "values": ["0", "34000"]}, [])
        assert ok

    def test_rejects_a_false_claim_that_all_values_are_the_same(self):
        ok, reason = error_llm.is_grounded(
            "Since all of these values are 0, the total is 0.",
            {"_values_are_uniform": False, "relationship": None, "values": ["0"]}, [])
        assert not ok and "same" in reason

    def test_allows_the_claim_when_the_values_really_are_uniform(self):
        ok, _ = error_llm.is_grounded("All of these values are 0.",
                                      {"_values_are_uniform": True, "relationship": None,
                                       "values": ["0"]}, [])
        assert ok


# âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
# 11. Presentation contract
#
# The UI renders headings as real elements from `explanation_sections`, so the
# text form must carry no markdown emphasis markers at all â a literal '**'
# reaching the user is a defect, not a styling preference.
# âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ

_SECTION_ORDER = ["Validation Rule", "Reported Values", "Comparison",
                  "Validator Message", "Why It Failed", "Where to Check",
                  "How to Fix"]


class TestPresentationContract:
    def _any_rule(self):
        return {
            "rule_name": "R", "has_backtracking": False, "error_count": 1,
            "formula_expression": "$V1 > $V2",
            "instances": [{"business_message": "", "facts": [
                {"var": "V1", "concept": "AlphaValue", "value": "10", "context": "c1",
                 "unit": "INR", "decimal": "0", "precision": ""},
                {"var": "V2", "concept": "BetaValue", "value": "20", "context": "c2",
                 "unit": "INR", "decimal": "0", "precision": ""},
            ]}],
        }

    def test_text_contains_no_markdown_emphasis(self):
        rule = self._any_rule()
        comparison, result = fe.evaluate_instance(rule, rule["instances"][0])
        labels, _ = fe.resolve_labels(rule, comparison)
        text = fe.render_explanation(rule, comparison, result, labels)
        assert "**" not in text
        assert "__" not in text

    def test_sections_are_typed_and_well_formed(self):
        rule = self._any_rule()
        comparison, result = fe.evaluate_instance(rule, rule["instances"][0])
        labels, _ = fe.resolve_labels(rule, comparison)
        sections = fe.build_sections(rule, comparison, result, labels)
        kinds = {s["kind"] for s in sections}
        assert kinds <= {"headline", "rule", "values", "points", "note"}
        assert sections[0]["kind"] == "headline"
        for section in sections:
            if section["kind"] == "values":
                assert section["items"] and all("value" in i for i in section["items"])
            if section["kind"] == "points":
                assert section["bullets"] and all(b.strip() for b in section["bullets"])
            if section.get("heading"):
                assert "**" not in section["heading"]

    def test_why_it_failed_is_point_wise_not_one_paragraph(self):
        rule = self._any_rule()
        comparison, result = fe.evaluate_instance(rule, rule["instances"][0])
        labels, _ = fe.resolve_labels(rule, comparison)
        sections = {s.get("heading"): s for s in fe.build_sections(rule, comparison, result, labels)}
        bullets = sections["Why It Failed"]["bullets"]
        assert len(bullets) >= 3
        assert all(len(b) < 220 for b in bullets)

    def test_section_headings_appear_in_a_stable_order(self):
        rule = self._any_rule()
        comparison, result = fe.evaluate_instance(rule, rule["instances"][0])
        labels, _ = fe.resolve_labels(rule, comparison)
        headings = [s["heading"] for s in fe.build_sections(rule, comparison, result, labels)
                    if s.get("heading")]
        assert headings == [h for h in _SECTION_ORDER if h in headings]

    def test_llm_prose_is_split_into_points(self):
        assert fe._llm_points("One thing happened. Then another thing happened.") == [
            "One thing happened.", "Then another thing happened."]
        assert fe._llm_points("Line one\nLine two") == ["Line one.", "Line two."]
        assert fe._llm_points("") == []
        assert fe._llm_points(None) == []


@needs_corpus
class TestPresentationAcrossCorpus:
    def test_no_markdown_markers_in_any_formula_explanation(self):
        checked = 0
        for path in CORPUS.rglob("*.html"):
            rules = fe.parse_formula_errors_v2(str(path))
            if not rules:
                continue
            for item in fe.explain_formula_rules(
                    rules, form_id=path.parent.name, error_file_path=str(path)):
                checked += 1
                text = item["explanation"]
                assert "**" not in text, (path, item["rule_name"])
                assert "__" not in text, (path, item["rule_name"])
        assert checked > 50, checked

    def test_every_explanation_carries_structured_sections(self):
        for path in CORPUS.rglob("*.html"):
            rules = fe.parse_formula_errors_v2(str(path))
            if not rules:
                continue
            for item in fe.explain_formula_rules(
                    rules, form_id=path.parent.name, error_file_path=str(path)):
                sections = item.get("explanation_sections")
                assert isinstance(sections, list) and sections, (path, item["rule_name"])
                assert sections[0]["kind"] == "headline"
                headings = [s["heading"] for s in sections if s.get("heading")]
                assert "How to Fix" in headings
                assert headings == [h for h in _SECTION_ORDER if h in headings]

    def test_the_same_parser_and_explainer_handles_every_file(self):
        """One code path for the whole corpus: same parse entry point, same
        explain entry point, regardless of return, product or backtracking."""
        seen_backtracking, seen_plain = 0, 0
        for path in CORPUS.rglob("*.html"):
            for rule in fe.parse_formula_errors_v2(str(path)):
                if rule["has_backtracking"]:
                    seen_backtracking += 1
                else:
                    seen_plain += 1
        assert seen_backtracking > 0 and seen_plain > 0


class TestNoHardcodedIdentifiers:
    """No return id, assertion name, concept name, dimension or member may
    influence behaviour anywhere in the explanation modules.

    The audit is AST-based and inspects EXECUTABLE string literals only.
    Docstrings and comments are excluded on purpose: they document why the old
    form-id proxy was wrong and necessarily name the examples that proved it,
    which is documentation rather than logic.
    """

    MODULES = ["formula_error", "formula_expression", "message_cleaner",
               "error_file_shape", "taxonomy_index", "instance_context",
               "dimension_error", "error_llm"]

    # Vocabulary drawn from the corpus used during development. None of it may
    # appear in code that runs.
    VOCABULARY = [
        "Sec-8", "SectoralCredit", "NPABreakup", "TermLoansSanctioned",
        "SubstandardAdvances", "GrossNPAs", "LossAdvances", "DoubtfulAdvances",
        "ComplaintsPending", "TotalOfAverageCashReserves", "CommodityHedges",
        "PlaceOfOccurence", "DateAndTimeOfOccurrence", "in-rbi-rep",
        "CIMS_MPD03", "OtherThanPrioritySector", "DateAxis", "OtherMember",
        "fmrd10", "mpd03", "raq", "BTDetails",
    ]

    def _tree(self, name):
        path = PROJECT_ROOT / "backend" / "tools" / f"{name}.py"
        return ast.parse(path.read_text(encoding="utf-8"))

    def _executable_string_literals(self, tree):
        """Every string constant except docstrings."""
        docstrings = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                                 ast.AsyncFunctionDef)):
                body = getattr(node, "body", None)
                if (body and isinstance(body[0], ast.Expr)
                        and isinstance(body[0].value, ast.Constant)
                        and isinstance(body[0].value.value, str)):
                    docstrings.add(id(body[0].value))
        return [
            node.value for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstrings
        ]

    def test_no_identifier_from_the_corpus_appears_in_running_code(self):
        for name in self.MODULES:
            literals = self._executable_string_literals(self._tree(name))
            for literal in literals:
                for token in self.VOCABULARY:
                    assert token.lower() not in literal.lower(), (
                        f"{name}.py has a literal containing {token!r}: {literal!r}")

    def test_no_branch_compares_against_a_form_or_return_id(self):
        pattern = re.compile(r"^[A-Z]?\d{3,4}$")
        for name in self.MODULES:
            tree = self._tree(name)
            for node in ast.walk(tree):
                if not isinstance(node, ast.Compare):
                    continue
                for operand in [node.left, *node.comparators]:
                    if isinstance(operand, ast.Constant) and isinstance(operand.value, str):
                        assert not pattern.match(operand.value), (
                            f"{name}.py branches on the literal {operand.value!r}")

    def test_the_legacy_form_id_range_check_is_not_referenced(self):
        for name in self.MODULES:
            names = {n.id for n in ast.walk(self._tree(name)) if isinstance(n, ast.Name)}
            attrs = {n.attr for n in ast.walk(self._tree(name)) if isinstance(n, ast.Attribute)}
            assert "_is_4000_series" not in (names | attrs), name

    def test_taxonomy_example_values_are_keyed_by_xsd_type_not_by_dimension(self):
        """taxonomy_index does carry illustrative values ('2018-11-12'), but
        they are keyed by XSD primitive, so they generalise to any typed
        dimension in any taxonomy rather than naming one."""
        from backend.tools import taxonomy_index as ti
        assert set(ti._BASE_TYPE_EXAMPLES) >= {"date", "datetime", "decimal", "string"}
        for key in ti._BASE_TYPE_EXAMPLES:
            assert key.isalnum(), key


# ═══════════════════════════════════════════════════════════════════════════
# 12. The LLM-enabled path
#
# Every test above runs with ERROR_EXPLAIN_LLM=0, which is exactly why a
# production defect survived them: the model returned "why_failed" as a JSON
# ARRAY, phrase() called .strip() on a list OUTSIDE its try/except, and the
# exception propagated to explain_one_rule's handler — replacing a complete,
# correct explanation with a one-line "review the values" fallback in the UI.
#
# These tests exercise the enabled path with a stubbed transport.
# ═══════════════════════════════════════════════════════════════════════════

class _FakeResponse:
    def __init__(self, content):
        self._content = content

    def raise_for_status(self):
        return None

    def json(self):
        return {"message": {"content": self._content}}


class _FakeClient:
    def __init__(self, content, *a, **kw):
        self._content = content

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def post(self, *a, **kw):
        return _FakeResponse(self._content)


def _stub_llm(monkeypatch, content):
    import httpx
    monkeypatch.setattr(httpx, "Client",
                        lambda *a, **kw: _FakeClient(content), raising=True)
    monkeypatch.setenv("ERROR_EXPLAIN_LLM", "1")


FALLBACK_MARKER = "This validation rule did not pass."


class TestLlmEnabledPath:
    def _rule(self):
        return {
            "rule_name": "R", "has_backtracking": False, "error_count": 1,
            "formula_expression": "$V1 = $V2 + $V3",
            "instances": [{"business_message": "", "facts": [
                {"var": "V1", "concept": "AlphaTotal", "value": "100", "context": "c1",
                 "unit": "INR", "decimal": "0", "precision": ""},
                {"var": "V2", "concept": "BetaPart", "value": "60", "context": "c2",
                 "unit": "INR", "decimal": "0", "precision": ""},
                {"var": "V3", "concept": "GammaPart", "value": "30", "context": "c3",
                 "unit": "INR", "decimal": "0", "precision": ""},
            ]}],
        }

    def _explain(self):
        from backend.tools import error_llm
        rule = self._rule()
        return fe.explain_one_rule(rule, None, None, error_llm.llm_settings())

    def test_array_valued_field_does_not_destroy_the_explanation(self, monkeypatch):
        """The exact production failure: 'why_failed' returned as a JSON array."""
        _stub_llm(monkeypatch, '{"why_failed": ["A happened.", "B happened."], '
                               '"how_to_fix": "Review the totals."}')
        out = self._explain()
        assert FALLBACK_MARKER not in out["explanation"]
        assert out.get("explanation_sections")

    def test_malformed_json_does_not_destroy_the_explanation(self, monkeypatch):
        _stub_llm(monkeypatch, "not json at all")
        out = self._explain()
        assert FALLBACK_MARKER not in out["explanation"]
        assert out.get("explanation_sections")

    def test_transport_failure_does_not_destroy_the_explanation(self, monkeypatch):
        import httpx

        def boom(*a, **kw):
            raise httpx.ConnectError("connection refused")

        monkeypatch.setattr(httpx, "Client", boom, raising=True)
        monkeypatch.setenv("ERROR_EXPLAIN_LLM", "1")
        out = self._explain()
        assert FALLBACK_MARKER not in out["explanation"]
        assert out.get("explanation_sections")

    def test_phrase_raising_outright_does_not_destroy_the_explanation(self, monkeypatch):
        from backend.tools import error_llm
        monkeypatch.setenv("ERROR_EXPLAIN_LLM", "1")
        monkeypatch.setattr(error_llm, "phrase",
                            lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("boom")))
        out = self._explain()
        assert FALLBACK_MARKER not in out["explanation"]
        assert out.get("explanation_sections")

    def test_the_deterministic_facts_survive_llm_wording(self, monkeypatch):
        _stub_llm(monkeypatch, '{"how_to_fix": "Review Alpha Total and its components."}')
        out = self._explain()
        sections = {s.get("heading"): s for s in out["explanation_sections"]}
        values = {i["label"]: i["value"] for i in sections["Reported Values"]["items"]}
        assert values["Alpha Total"] == "₹100"
        assert values["Beta Part"] == "₹60"
        assert values["Gamma Part"] == "₹30"
        assert "**" not in out["explanation"]

    def test_why_it_failed_is_deterministic_by_default(self, monkeypatch):
        """The model is not asked to restate the arithmetic unless
        ERROR_EXPLAIN_LLM_WHY is set, so its wording cannot reshape the
        point-wise facts."""
        _stub_llm(monkeypatch, '{"why_failed": "totally wrong wording", '
                               '"how_to_fix": "Review Alpha Total."}')
        out = self._explain()
        sections = {s.get("heading"): s for s in out["explanation_sections"]}
        bullets = sections["Why It Failed"]["bullets"]
        assert not any("totally wrong wording" in b for b in bullets)
        assert any("Alpha Total" in b for b in bullets)


class TestTextNormalisation:
    def test_as_text_handles_every_container_a_model_returns(self):
        from backend.tools.error_llm import _as_text
        assert _as_text("  hi  ") == "hi"
        assert _as_text(["a", "b"]) == "a\nb"
        assert _as_text({"x": "a", "y": "b"}) == "a\nb"
        assert _as_text(["a", ["b", "c"]]) == "a\nb\nc"
        assert _as_text(None) == ""
        assert _as_text([]) == ""
        assert _as_text(12) == "12"


class TestRequirementIsNotMisstated:
    def test_rejects_a_fix_that_restates_equality_as_an_inequality(self):
        ok, reason = error_llm.is_grounded(
            "Ensure the total is reported as greater than the sum of its parts.",
            {"operator_meaning": "equal to", "relationship": "lhs_greater"}, [])
        assert not ok and "restates" in reason

    def test_accepts_a_fix_that_uses_the_rules_own_comparison(self):
        ok, _ = error_llm.is_grounded(
            "Ensure the exposure is greater than or equal to the funded amount.",
            {"operator_meaning": "greater than or equal to", "relationship": "lhs_less"}, [])
        assert ok

    def test_accepts_a_fix_that_states_no_comparison(self):
        ok, _ = error_llm.is_grounded(
            "Review both reported figures in the source data and revalidate.",
            {"operator_meaning": "equal to", "relationship": "lhs_greater"}, [])
        assert ok


@needs_corpus
class TestLlmEnabledAcrossCorpus:
    def test_no_rule_falls_back_when_the_model_misbehaves(self, monkeypatch):
        """A misbehaving model must never cost a rule its explanation."""
        _stub_llm(monkeypatch, '{"why_failed": ["x"], "how_to_fix": ["y", "z"]}')
        checked = 0
        for path in CORPUS.rglob("*.html"):
            rules = fe.parse_formula_errors_v2(str(path))
            if not rules:
                continue
            for item in fe.explain_formula_rules(
                    rules, form_id=path.parent.name, error_file_path=str(path)):
                checked += 1
                assert FALLBACK_MARKER not in item["explanation"], (path, item["rule_name"])
                assert item.get("explanation_sections"), (path, item["rule_name"])
        assert checked > 50, checked


# ═══════════════════════════════════════════════════════════════════════════
# 13. Dimension-error presentation and evidence separation
#
# The reported FACT value and the reported DIMENSION MEMBERS are different
# things from different sources. Conflating them produced an explanation that
# said "Reported value/member: Not available" while the same error displayed
# "concept: PlaceOfOccurence, value: 2. In ATM".
# ═══════════════════════════════════════════════════════════════════════════

class TestDimensionPresentation:
    def _sections(self, item):
        return {s["heading"]: s for s in item["explanation_sections"] if s.get("heading")}

    def _explain(self, path, form_id, n=1):
        from backend.tools.dimension_error import (explain_dimension_errors,
                                                   parse_dimension_errors)
        errors = parse_dimension_errors(str(path))
        return explain_dimension_errors(errors[:n], form_id=form_id,
                                        error_file_path=str(path))

    @needs_corpus
    def test_fact_value_from_the_html_is_never_suppressed(self):
        """The error file carries the concept and its value; a missing
        instance document must not hide them."""
        if not F_2047.is_file():
            pytest.skip("file absent")
        out = self._explain(F_2047, "2047", 1)
        sections = self._sections(out[0])
        reported = {i["label"]: i["value"] for i in sections["What Was Reported"]["items"]}
        assert reported["Reported value"] == "2. In ATM"
        assert "Place of occurence" in reported["Concept"]
        assert out[0]["_dimension_evidence"]["instance_document_used"] is False

    @needs_corpus
    def test_fact_value_and_dimension_members_are_separate_sections(self):
        if not F_2047.is_file():
            pytest.skip("file absent")
        out = self._explain(F_2047, "2047", 1)
        sections = self._sections(out[0])
        assert "What Was Reported" in sections and "Details Actually Provided" in sections
        members = sections["Details Actually Provided"]
        # No instance document for this run: members unavailable, value still shown.
        assert members["kind"] == "rule"
        assert "not available" in members["text"].lower()

    @needs_corpus
    def test_dimensions_involved_lists_each_dimension_and_its_kind(self):
        """Replaces the opaque '4 dimensions required together'."""
        if not F_2047.is_file():
            pytest.skip("file absent")
        out = self._explain(F_2047, "2047", 1)
        items = self._sections(out[0])["Details This Figure Must Carry"]["items"]
        assert len(items) == 4
        assert {i["value"] for i in items} <= {"You enter the value", "Pick one from a fixed list"}
        assert any(i["value"] == "Pick one from a fixed list" for i in items)
        assert any(i["value"] == "You enter the value" for i in items)

    @needs_corpus
    def test_taxonomy_role_markers_are_stripped_from_labels(self):
        if not F_2047.is_file():
            pytest.skip("file absent")
        out = self._explain(F_2047, "2047", 1)
        text = out[0]["explanation"]
        for marker in ("[axis]", "[member]", "[domain]", "[Axis]", "[Member]"):
            assert marker not in text, marker

    @needs_corpus
    def test_no_markdown_markers_and_stable_section_order(self):
        for path, form_id in ((F_2047, "2047"), (F_2047_TYPED, "2047"),
                              (F_4012, "4012"), (F_R376, "R376")):
            if not Path(path).is_file():
                continue
            for item in self._explain(path, form_id, 3):
                assert "**" not in item["explanation"]
                headings = [s["heading"] for s in item["explanation_sections"]
                            if s.get("heading")]
                order = ["What Was Reported", "Details This Figure Must Carry",
                         "What Each Detail Must Contain", "Details Actually Provided",
                         "What Is Wrong", "How to Fix", "Context Id (for reference)"]
                assert headings == [h for h in order if h in headings]

    @needs_corpus
    def test_unprovable_claims_are_not_made(self):
        """Without instance evidence the explanation must not assert which
        dimension is missing or invalid."""
        if not F_2047.is_file():
            pytest.skip("file absent")
        out = self._explain(F_2047, "2047", 1)
        bullets = self._sections(out[0])["What Is Wrong"]["bullets"]
        joined = " ".join(bullets).lower()
        assert "could not be pinned down" in joined
        assert "was not reported at all" not in joined
        # No specific dimension may be named as the culprit without evidence.
        for axis in out[0]["_dimension_evidence"]["expected_axes"]:
            assert f"{axis['label']} is missing" not in joined

    @needs_corpus
    def test_sections_do_not_repeat_each_other(self):
        """Requirements belong to one section; the diagnosis and the fix must
        not restate them."""
        if not F_2047.is_file():
            pytest.skip("file absent")
        out = self._explain(F_2047, "2047", 1)
        sections = self._sections(out[0])
        requirements = " ".join(i["value"] for i in
                                sections["What Each Detail Must Contain"]["items"])
        wrong = " ".join(sections["What Is Wrong"]["bullets"])
        fix = " ".join(sections["How to Fix"]["bullets"])
        # The member list appears exactly once, in the requirements section.
        for probe in ("Pick one of these:", "YYYY-MM-DDThh:mm:ss"):
            if probe in requirements:
                assert probe not in wrong
                assert probe not in fix

    def test_instance_xml_when_available_names_the_actual_members(self, monkeypatch):
        """The optional enrichment path: with the run's own InstanceDocPath
        recorded, the explanation reports the real members and pinpoints which
        required dimensions are absent."""
        if not F_2047.is_file():
            pytest.skip("file absent")
        monkeypatch.setattr(rl, "_parse_instances", lambda: (
            {"FormId": "2047",
             "ErrorDocPath": "ICICI231231R21202Q_19-05-26_04-04-19_Instance.html",
             "InstanceDocPath": "ICICI231231R21202Q_19-05-26_04-04-19_Instance.xml"},
        ))
        out = self._explain(F_2047, "2047", 1)
        evidence = out[0]["_dimension_evidence"]
        assert evidence["instance_document_used"] is True
        assert evidence["diagnosis"] == "missing_axes"
        sections = self._sections(out[0])
        members = {i["label"]: i["value"] for i in
                   sections["Details Actually Provided"]["items"]}
        assert members["Branch code"] == "0510003"
        assert members["Date and Time of Occurrence Type"] == "2023-10-23T12:51:00"
        wrong = " ".join(sections["What Is Wrong"]["bullets"])
        assert "Name of branch" in wrong and "Type of criminal" in wrong
        # The fact value from the HTML is still shown alongside.
        reported = {i["label"]: i["value"] for i in sections["What Was Reported"]["items"]}
        assert reported["Reported value"] == "2. In ATM"

    @needs_corpus
    def test_every_dimension_error_in_the_corpus_renders_sections(self):
        from backend.tools.dimension_error import (explain_dimension_errors,
                                                   parse_dimension_errors)
        checked = 0
        for path in CORPUS.rglob("*.html"):
            errors = parse_dimension_errors(str(path))
            if not errors:
                continue
            for item in explain_dimension_errors(errors[:3], form_id=path.parent.name,
                                                 error_file_path=str(path)):
                checked += 1
                sections = item.get("explanation_sections")
                assert isinstance(sections, list) and sections, path
                assert sections[0]["kind"] == "headline"
                assert "**" not in item["explanation"], path
                headings = [s["heading"] for s in sections if s.get("heading")]
                assert "What Is Wrong" in headings and "How to Fix" in headings
        assert checked >= 20, checked


# ═══════════════════════════════════════════════════════════════════════════
# 14. Dimension-error readability
#
# Label and value were two adjacent inline spans inside a row, with the grid
# on the row's PARENT — so nothing separated them and the UI rendered
# "Branch codeTyped". The separator now lives in the DOM, not in CSS.
# ═══════════════════════════════════════════════════════════════════════════

class TestDimensionReadability:
    def _sections(self, item):
        return {s["heading"]: s for s in item["explanation_sections"] if s.get("heading")}

    def _explain(self, path, form_id, n=1):
        from backend.tools.dimension_error import (explain_dimension_errors,
                                                   parse_dimension_errors)
        errors = parse_dimension_errors(str(path))
        return explain_dimension_errors(errors[:n], form_id=form_id,
                                        error_file_path=str(path))

    @needs_corpus
    def test_every_label_value_pair_is_separated_in_the_text_form(self):
        """Checked against the VALUES sections themselves, not by scanning
        bullets for a colon — prose legitimately contains colons (a timestamp
        example, for one), and matching those would be a false positive."""
        if not F_2047.is_file():
            pytest.skip("file absent")
        out = self._explain(F_2047, "2047", 1)
        text = out[0]["explanation"]
        pairs = 0
        for section in out[0]["explanation_sections"]:
            for entry in section.get("items", []):
                label, value = entry.get("label", ""), entry.get("value", "")
                if not label:
                    continue
                pairs += 1
                assert f"• {label}: {value}" in text, (label, value)
                assert f"• {label}{value}" not in text
        assert pairs >= 4, pairs

    @needs_corpus
    def test_context_is_on_its_own_line_not_glued_to_its_heading(self):
        if not F_2047.is_file():
            pytest.skip("file absent")
        out = self._explain(F_2047, "2047", 1)
        text = out[0]["explanation"]
        context = out[0]["_dimension_evidence"]["context_id"]
        assert f"Context Id (for reference):\n{context}" in text
        assert f"(for reference){context}" not in text

    @needs_corpus
    def test_requirements_read_as_sentences(self):
        if not F_2047.is_file():
            pytest.skip("file absent")
        items = self._sections(self._explain(F_2047, "2047", 1)[0])["What Each Detail Must Contain"]["items"]
        for item in items:
            assert item["value"][:1].isupper(), item
        assert any(i["value"].startswith("Pick one of these: ") for i in items)

    @needs_corpus
    def test_fix_steps_are_short_and_match_the_dimension_kinds_present(self):
        if not F_2047.is_file():
            pytest.skip("file absent")
        out = self._explain(F_2047, "2047", 1)
        bullets = self._sections(out[0])["How to Fix"]["bullets"]
        assert all(len(b) < 120 for b in bullets), bullets
        axes = out[0]["_dimension_evidence"]["expected_axes"]
        joined = " ".join(bullets).lower()
        assert ("details you enter yourself, use the format shown above" in joined) is any(
            a["is_typed"] for a in axes)
        assert ("details picked from a list, use one of the options shown above" in joined) is any(
            not a["is_typed"] for a in axes)

    @needs_corpus
    def test_no_markdown_or_glued_pairs_anywhere_in_the_corpus(self):
        from backend.tools.dimension_error import (explain_dimension_errors,
                                                   parse_dimension_errors)
        checked = 0
        for path in CORPUS.rglob("*.html"):
            errors = parse_dimension_errors(str(path))
            if not errors:
                continue
            for item in explain_dimension_errors(errors[:3], form_id=path.parent.name,
                                                 error_file_path=str(path)):
                checked += 1
                text = item["explanation"]
                assert "**" not in text and "###" not in text, path
                for section in item["explanation_sections"]:
                    for entry in section.get("items", []):
                        # Both halves must be non-empty; the renderer supplies
                        # the ":" between them.
                        assert str(entry.get("value", "")).strip(), (path, entry)
        assert checked >= 20, checked
