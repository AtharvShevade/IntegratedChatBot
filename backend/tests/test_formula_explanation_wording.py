"""Formula-type-aware explanation wording — regression suite.

Every test here traces to a real explanation defect observed on returns R025,
R034, R061, R090 and R096, or to a contract that must not regress while fixing
them. The defects, in the words of the report they came from:

  * "X is higher than the sum of its parts" printed for a ratio, a percentage,
    a weighted average and a conditional — none of which sum anything;
  * raw V1…V6 shown to the user on a mandatory-field rule;
  * "a value the validation output does not name" where the validator's own
    message spelled the operand out;
  * "not reported" for an operand the output never carried a row for;
  * ₹ printed on ratios, percentages and rounding steps.

Nothing here asserts on an arithmetic result that this change was allowed to
alter — the numeric assertions exist precisely to prove the arithmetic did NOT
move. These tests are self-contained (no corpus, no Ollama) so they run
everywhere.
"""
from __future__ import annotations

import os
import sys
from decimal import Decimal
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.tools import error_card                       # noqa: E402
from backend.tools import formula_error as fe              # noqa: E402
from backend.tools import formula_expression as fx         # noqa: E402
from backend.tools import formula_kind as fk               # noqa: E402


@pytest.fixture(autouse=True)
def _deterministic(monkeypatch):
    """No LLM, card v2 on — this suite specifies the deterministic card."""
    monkeypatch.setenv("ERROR_EXPLAIN_LLM", "0")
    monkeypatch.setenv("ERROR_CARD_V2", "1")


# ═══════════════════════════════════════════════════════════════════════════
# Fixture builder — mirrors what parse_formula_errors_v2 hands the explainer
# ═══════════════════════════════════════════════════════════════════════════

def build(expression, values, *, message="", units=None, concepts=None,
          name="Rule", instances=1):
    units = units or {}
    concepts = concepts or {}
    facts = [
        {"var": var, "value": value, "unit": units.get(var, ""),
         "context": f"ctx_{var}", "concept": concepts.get(var, "")}
        for var, entries in values.items() for value in entries
    ]
    rule = {
        "rule_name": name, "formula_expression": expression,
        "instances": [{"facts": facts, "business_message": message}] * instances,
    }
    comparison, result = fe.evaluate_instance(rule, rule["instances"][0])
    labels, sources = fe.resolve_labels(rule, comparison)
    sections = fe.build_card_sections(rule, comparison, result, labels)
    return {
        "rule": rule, "comparison": comparison, "result": result,
        "labels": labels, "sources": sources, "sections": sections,
        "text": fe.render_card(rule, comparison, result, labels),
        "kind": fk.classify(comparison),
    }


def section(built, kind):
    return next((s for s in built["sections"] if s.get("kind") == kind), None)


def heading(built, name):
    for s in built["sections"]:
        if s.get("heading") == name:
            return s
        if s.get("kind") == "details":
            for nested in s.get("sections") or []:
                if nested.get("heading") == name:
                    return nested
    return None


def rows(built):
    matrix = section(built, "matrix")
    return matrix["rows"] if matrix else []


# ═══════════════════════════════════════════════════════════════════════════
# 1 — classification covers every formula type in the brief
# ═══════════════════════════════════════════════════════════════════════════

class TestClassification:
    @pytest.mark.parametrize("expression,expected", [
        # AGGREGATE
        ("$V2 = sum($V1) + sum($V3)", fk.AGGREGATE),
        ("$V1 = $V2 + $V3 - $V4", fk.AGGREGATE),
        ("round($V2 div 100000)*100000 = round((sum($V1)+sum($V3)) div 100000)*100000",
         fk.AGGREGATE),
        # RATIO
        ("$V3 = $V1 div $V2", fk.RATIO),
        ("round(abs($V3*10000)) div 10000 = round(abs(($V1 div $V2)*10000)) div 10000",
         fk.RATIO),
        ("round($V4*10000) div 10000 = round((($V1) div ($V5+$V6))*10000) div 10000",
         fk.RATIO),
        # PERCENTAGE — the *100 is part of the rule, not a rounding scale
        ("$V4 = ($V1 * 100) div ($V5 + $V6)", fk.PERCENTAGE),
        # WEIGHTED AVERAGE
        ("round($V6*10000) div 10000 = round(((( $V1 * $V2 )+( $V3 * $V4 ))"
         " div( $V1 + $V3 ))*10000) div 10000", fk.WEIGHTED_AVERAGE),
        # EQUALITY
        ("$V1 = $V2", fk.EQUALITY),
        # THRESHOLD
        ("$V1 >= 0.1", fk.THRESHOLD),
        ("$V1 >= 0", fk.THRESHOLD),
        ("$V1 <= $V2", fk.THRESHOLD),
        # COUNT
        ("count($V1) >= 50", fk.COUNT),
        # MANDATORY
        ("not(empty($V1))", fk.MANDATORY),
        ("not(empty($V1)) and not(empty($V2))", fk.MANDATORY),
        # CONDITIONAL
        ("if ($V2 = 0) then ($V1 = 0) else ($V1 = $V2)", fk.CONDITIONAL),
    ])
    def test_kind(self, expression, expected):
        assert fk.classify(fx.parse_formula(expression)) == expected

    def test_a_rounding_idiom_using_100_is_not_read_as_a_percentage(self):
        """`round($V1*100) div 100` scales for tolerance; there is no division
        by a reported value, so nothing about it is a percentage."""
        assert fk.classify(fx.parse_formula(
            "round($V1*100) div 100 = round($V2*100) div 100")) == fk.EQUALITY

    def test_an_unparseable_formula_classifies_as_unknown_not_a_guess(self):
        assert fk.classify(None) == fk.UNKNOWN
        assert fk.classify(fx.parse_formula("")) == fk.UNKNOWN

    def test_unknown_offers_no_wording_so_callers_keep_their_own(self):
        assert fk.result_subject(fk.UNKNOWN) == ""
        assert fk.expected_column(fk.UNKNOWN) == ""
        assert fk.is_unitless(fk.UNKNOWN) is False
        assert fk.describes_a_calculation(fk.UNKNOWN) is False


# ═══════════════════════════════════════════════════════════════════════════
# 2 — "sum of its parts" only where something is actually summed
# ═══════════════════════════════════════════════════════════════════════════

_SUM_LANGUAGE = ("sum of its parts", "combined value", "together come to")


class TestSumLanguageIsNotUniversal:
    def test_aggregate_keeps_summation_language(self):
        """R025. The aggregate case was already correct and must stay so."""
        built = build(
            "round($V2 div 100000)*100000 = round((sum($V1)+sum($V3)) div 100000)*100000",
            {"V2": ["1004500000"], "V1": ["402000000"], "V3": ["401200000"]},
            units={"V1": "INR", "V2": "INR", "V3": "INR"},
            concepts={"V2": "LimitTotal", "V1": "LimitA", "V3": "LimitB"},
            message="Total of all groups should be summation of the values reported",
        )
        assert built["kind"] == fk.AGGREGATE
        assert "sum of the component values" in section(built, "headline")["text"]
        # …and the numbers are the ones the engine computed, untouched.
        assert built["result"]["rhs_value"] == Decimal("803200000")
        assert built["result"]["lhs_value"] == Decimal("1004500000")
        assert built["result"]["difference"] == Decimal("201300000")
        assert "₹803,200,000" in built["text"] and "₹1,004,500,000" in built["text"]

    @pytest.mark.parametrize("expression,values,units", [
        # ratio (R096)
        ("round(abs($V3*10000)) div 10000 = round(abs(($V1 div $V2)*10000)) div 10000",
         {"V3": ["-0.03"], "V1": ["-495956792000"], "V2": ["17775625211000"]},
         {"V1": "INR", "V2": "INR"}),
        # percentage
        ("$V4 = ($V1 * 100) div ($V5 + $V6)",
         {"V4": ["0.02"], "V1": ["0"], "V5": ["309671000000"], "V6": ["0"]},
         {"V1": "INR", "V5": "INR", "V6": "INR"}),
        # weighted average
        ("round($V6*10000) div 10000 = round(((( $V1 * $V2 )+( $V3 * $V4 ))"
         " div( $V1 + $V3 ))*10000) div 10000",
         {"V6": ["0.06"], "V1": ["356802987000"], "V2": ["0.06"],
          "V3": ["2297563000"], "V4": ["0.05"]},
         {"V1": "INR", "V3": "INR"}),
    ])
    def test_non_additive_rules_never_claim_a_summation(self, expression, values, units):
        built = build(expression, values, units=units)
        lowered = built["text"].lower()
        for phrase in _SUM_LANGUAGE:
            assert phrase not in lowered, (built["kind"], phrase)

    def test_each_kind_names_its_own_calculation(self):
        cases = {
            fk.RATIO: "calculated ratio",
            fk.PERCENTAGE: "calculated percentage",
            fk.WEIGHTED_AVERAGE: "calculated weighted average",
            fk.AGGREGATE: "calculated total",
        }
        for kind, phrase in cases.items():
            assert phrase in fk.expected_column(kind).lower(), kind


# ═══════════════════════════════════════════════════════════════════════════
# 3 — units
# ═══════════════════════════════════════════════════════════════════════════

class TestUnits:
    def test_a_ratio_of_two_rupee_amounts_is_not_rupees(self):
        """R096 printed '₹0.03', '₹279.0095' and 'nearest ₹0.0001'."""
        built = build(
            "round(abs($V3*10000)) div 10000 = round(abs(($V1 div $V2)*10000)) div 10000",
            {"V3": ["-0.03"], "V1": ["-495956792000"], "V2": ["17775625211000"]},
            units={"V1": "INR", "V2": "INR"},
            concepts={"V3": "MismatchPercentage", "V1": "NetInflow", "V2": "NetOutflows"},
        )
        result_row = rows(built)[-1]
        assert "₹" not in result_row["actual"] and "₹" not in result_row["expected"]
        assert "₹" not in (result_row.get("note") or "")
        comparison = heading(built, "Comparison")
        assert all("₹" not in i["value"] for i in comparison["items"]), comparison
        # The monetary components keep their own symbol.
        assert any("₹" in r["actual"] for r in rows(built)[:-1])

    def test_a_component_never_borrows_another_facts_unit(self):
        """R034 printed '$1.9969' for a ratio because a dollar amount sat in
        the same table."""
        built = build(
            "$V1 = $V3", {"V1": ["1.9969"], "V3": ["75190000"]},
            units={"V3": "USD"},
            concepts={"V1": "LiquidityCoverageRatio", "V3": "NetCashOutflows"},
        )
        by_label = {r["label"]: r for r in rows(built)}
        assert "$" not in by_label["Liquidity Coverage Ratio"]["actual"]
        assert by_label["Net Cash Outflows"]["actual"] == "$75,190,000"

    def test_a_homogeneous_monetary_table_is_unchanged(self):
        built = build(
            "$V1 = $V2 + $V3",
            {"V1": ["2360000"], "V2": ["450000"], "V3": ["1200000"]},
            units={"V1": "INR", "V2": "INR", "V3": "INR"},
            concepts={"V1": "TotalAssets", "V2": "Cash", "V3": "Investments"},
        )
        assert all("₹" in r["actual"] for r in rows(built))
        assert "₹710,000" in section(built, "headline")["text"]


# ═══════════════════════════════════════════════════════════════════════════
# 4 — concept resolution: no raw ids, no unnamed values we could have named
# ═══════════════════════════════════════════════════════════════════════════

_R061_MESSAGE = (
    'TCE as % of Capital Funds" = TCE * 100/ ([Regulatory Capital (Tier I + Tier II) of '
    'Previous March) + (Capital Infusion during the period (April to date))]'
)

_R090_MESSAGE = (
    "Value for following field(s) is/are not present:- 1.Outstanding Unsecured Guarantees "
    "with Domestic; 2.Outstanding Unsecured Advances with Domestic; 3.Guarantees issued to "
    "non-residents on behalf of residents with Domestic; 4.Guarantees issued to "
    "non-residents on behalf of non-residents with Domestic; 5.Amount of External "
    "Commercial Borrowings (ECBs) with Domestic; 6.Bills for Collection with Domestic;"
)


class TestConceptResolution:
    def test_ratio_operands_are_named_from_the_validator_message(self):
        """R061 named all three operands 'a value the validation output does
        not name' even though the message spells each of them out. The existing
        message split could not reach them: signed_variables() is [] for a
        division, so its arity gate never had anything to match."""
        built = build(
            "round($V4*10000) div 10000 = round((($V1) div ($V5+$V6))*10000) div 10000",
            {"V4": ["0.02"], "V1": ["0"], "V5": ["309671000000"], "V6": ["0"]},
            message=_R061_MESSAGE,
            concepts={"V4": "AggregateCreditExposureAsPercentageOfCapitalFunds"},
        )
        labels = built["labels"]
        assert labels["V1"] == "TCE"
        assert labels["V5"] == "Regulatory Capital (Tier I + Tier II) of Previous March"
        assert labels["V6"] == "Capital Infusion during the period (April to date)"
        assert built["sources"]["V1"] == "message_operands"
        assert fe._UNNAMED_LABEL not in built["text"]

    def test_mandatory_fields_are_named_from_the_enumerated_message(self):
        """R090 showed six rows labelled V1…V6 — the raw ids resolve_labels
        exists to keep out of sight. Those variables have no rows in the error
        table, so the label map never held an entry for them at all."""
        built = build(
            " and ".join(f"not(empty($V{i}))" for i in range(1, 7)),
            {}, message=_R090_MESSAGE, name="Sec2PartAMemoMandatory",
        )
        assert built["kind"] == fk.MANDATORY
        labels = [r["label"] for r in rows(built)]
        assert labels[0] == "Outstanding Unsecured Guarantees with Domestic"
        assert labels[-1] == "Bills for Collection with Domestic"
        assert len(labels) == 6

    def test_no_raw_variable_id_survives_anywhere_in_the_card(self):
        import re
        built = build(
            " and ".join(f"not(empty($V{i}))" for i in range(1, 7)),
            {}, message=_R090_MESSAGE,
        )
        assert not re.search(r"\bV\d+\b", built["text"]), built["text"]

    def test_a_message_that_does_not_match_the_formula_is_refused_wholesale(self):
        """The arity gate: two operands named for a three-operand rule must
        assign NOTHING rather than two-thirds of a mapping."""
        message = "Ratio = Numerator / Denominator"
        assert fe._operand_names_from_message(message, 3) == []
        assert fe._operand_names_from_message(message, 1) == []
        assert fe._operand_names_from_message(message, 2) == ["Numerator", "Denominator"]

    def test_an_enumeration_shorter_than_the_variable_list_is_refused(self):
        built = build(
            " and ".join(f"not(empty($V{i}))" for i in range(1, 7)),
            {}, message="Value for following field(s):- 1.Alpha; 2.Beta;",
        )
        # Six variables, two names -> no assignment, and still no raw id.
        assert all(r["label"] not in ("Alpha", "Beta") for r in rows(built))
        assert "V1" not in built["text"]

    def test_taxonomy_labels_are_never_overwritten_by_the_message(self):
        built = build(
            "$V1 = $V2 div $V3",
            {"V1": ["1"], "V2": ["10"], "V3": ["5"]},
            message="Ratio = Numerator / Denominator",
            concepts={"V1": "ReportedRatio", "V2": "TotalIncome", "V3": "TotalAssets"},
        )
        # Concept-derived names win; the message never displaces them.
        assert built["labels"]["V2"] == "Total Income"
        assert built["labels"]["V3"] == "Total Assets"


# ═══════════════════════════════════════════════════════════════════════════
# 5 — missing vs. unavailable
# ═══════════════════════════════════════════════════════════════════════════

class TestMissingValues:
    def test_a_mandatory_rule_says_not_reported(self):
        built = build("not(empty($V1)) and not(empty($V2))", {},
                      message="Value for following field(s) is/are not present:- "
                              "1.Alpha Holdings; 2.Beta Holdings;")
        for row in rows(built):
            assert row["actual"] == "— not reported"
            assert row["status"] == error_card.STATUS_BAD

    def test_a_calculation_operand_with_no_row_is_unavailable_not_unreported(self):
        """Saying 'not reported' asserts something about the FILING. The
        evidence only supports a statement about the validation OUTPUT."""
        built = build(
            "$V1 = $V2 div $V3",
            {"V1": ["1.9969"], "V3": ["75190000"]},          # V2 has no row at all
            units={"V3": "USD"},
            concepts={"V1": "LiquidityCoverageRatio", "V3": "NetCashOutflows"},
            message="Liquidity Coverage Ratio = High Quality Liquid Assets / "
                    "Net Cash Outflows Weighted Amount",
        )
        by_label = {r["label"]: r for r in rows(built)}
        absent = by_label["High Quality Liquid Assets"]
        assert absent["actual"] == "— not available in the validation output"
        assert absent["status"] == error_card.STATUS_UNKNOWN
        assert "not reported" not in built["text"]

        note = " ".join(s["text"] for s in built["sections"] if s.get("kind") == "note")
        assert "High Quality Liquid Assets" in note
        assert "not available in the validation output" in note
        assert "cannot be independently calculated" in note

    def test_a_missing_operand_produces_no_calculation_rather_than_a_guess(self):
        built = build(
            "$V1 = $V2 div $V3", {"V1": ["1.9969"], "V3": ["75190000"]},
            message="Ratio = Numerator / Denominator",
        )
        assert heading(built, "Calculation") is None
        assert "= 0" not in built["text"]          # never assumes an absent value is zero

    def test_a_non_numeric_reported_value_is_shown_not_called_missing(self):
        """The corpus reports dates, codes and category names. Rendering them
        through the numeric formatter turned every one into 'not reported',
        which tells the reader their filing is missing something it contains."""
        built = build(
            "$V1 = $V2", {"V1": ["West Delhi"], "V2": ["2023-10-23T12:51:00"]},
            concepts={"V1": "AddressOfBranch", "V2": "DateAndTimeOfOccurrence"},
        )
        shown = " ".join(r["actual"] for r in rows(built))
        assert "West Delhi" in shown
        assert "2023-10-23T12:51:00" in shown
        assert "not reported" not in shown

    def test_never_says_not_reported_when_a_value_is_present(self):
        """R061's operands all had values; the card must use them."""
        built = build("$V1 >= 0.1", {"V1": ["12.54"]},
                      concepts={"V1": "PercentageOfExposureToTier1Capital"})
        assert "not reported" not in built["text"]
        assert "12.54" in built["text"]


# ═══════════════════════════════════════════════════════════════════════════
# 6 — threshold, count, conditional
# ═══════════════════════════════════════════════════════════════════════════

class TestOtherKinds:
    def test_threshold_states_the_limit_with_its_direction(self):
        built = build("$V1 >= 0.1", {"V1": ["0.05"]},
                      concepts={"V1": "PercentageOfExposureToTier1Capital"})
        assert built["kind"] == fk.THRESHOLD
        assert "greater than or equal to 0.1" in rows(built)[-1]["expected"]
        assert "sum" not in built["text"].lower()

    def test_a_rule_the_displayed_values_satisfy_is_flagged_not_explained_away(self):
        """R025-style invention is the risk here: the validator failed the rule
        and the displayed values pass it. Name the possibilities; invent
        nothing."""
        built = build("$V1 >= 0.1", {"V1": ["12.54"]},
                      concepts={"V1": "PercentageOfExposureToTier1Capital"})
        assert built["result"]["passes"] is True
        notes = " ".join(s["text"] for s in built["sections"] if s.get("kind") == "note")
        assert "validator reported this check as failed" in notes
        assert "scaling" in notes and "precision" in notes
        # The two figures are named, so the reader can see the inconsistency.
        assert "12.54" in notes and "greater than or equal to 0.1" in notes
        # The validator is never declared wrong, and the data is not claimed
        # to have been fixed already.
        assert "already have been corrected" not in notes
        # A rule that passes has no shortfall — "over by" would read as a fault.
        assert "over by" not in rows(built)[-1].get("note", "")

    def test_count_rule_is_classified_and_worded_as_a_count(self):
        comparison = fx.parse_formula("count($V1) >= 50")
        assert fk.classify(comparison) == fk.COUNT
        assert "count" in fk.expected_column(fk.COUNT).lower()

    def test_conditional_is_not_described_as_a_sum(self):
        built = build(
            "if ($V2 = 0) then ($V1 = 0) else ($V1 = $V2)",
            {"V1": ["500"], "V2": ["0"]},
            concepts={"V1": "ReportedValue", "V2": "Denominator"},
        )
        assert built["kind"] == fk.CONDITIONAL
        assert "sum of its parts" not in built["text"].lower()


# ═══════════════════════════════════════════════════════════════════════════
# 7 — the calculation line
# ═══════════════════════════════════════════════════════════════════════════

class TestCalculation:
    def test_aggregate_shows_the_substituted_addition(self):
        built = build(
            "round($V2 div 100000)*100000 = round((sum($V1)+sum($V3)) div 100000)*100000",
            {"V2": ["1004500000"], "V1": ["402000000"], "V3": ["401200000"]},
            units={"V1": "INR", "V2": "INR", "V3": "INR"},
        )
        line = heading(built, "Calculation")["bullets"][0]
        assert line == "₹402,000,000 + ₹401,200,000 = ₹803,200,000"

    def test_weighted_average_shows_the_whole_expression_with_values(self):
        built = build(
            "round($V6*10000) div 10000 = round(((( $V1 * $V2 )+( $V3 * $V4 ))"
            " div( $V1 + $V3 ))*10000) div 10000",
            {"V6": ["0.06"], "V1": ["356802987000"], "V2": ["0.06"],
             "V3": ["2297563000"], "V4": ["0.05"]},
            units={"V1": "INR", "V3": "INR"},
        )
        bullets = heading(built, "Calculation")["bullets"]
        assert bullets[0] == (
            "(₹356,802,987,000 × 0.06 + ₹2,297,563,000 × 0.05) ÷ "
            "(₹356,802,987,000 + ₹2,297,563,000) = 0.0599"
        )
        assert "Rounded to the nearest 0.0001" in bullets[1]
        assert "₹" not in bullets[1]        # the average itself is not currency

    def test_no_variable_id_appears_in_a_calculation(self):
        import re
        built = build("$V1 = $V2 div $V3", {"V1": ["2"], "V2": ["10"], "V3": ["5"]},
                      concepts={"V1": "Ratio", "V2": "Income", "V3": "Assets"})
        assert not re.search(r"\bV\d+\b", heading(built, "Calculation")["bullets"][0])

    def test_a_single_operand_gets_no_calculation_section(self):
        """'194 = 194' restates the matrix row. The breakdown of one
        aggregated variable is already shown there as 'total of N reported
        values'."""
        built = build("$V1 = sum($V2)", {"V1": ["0"], "V2": ["177", "14", "3"]},
                      concepts={"V1": "OtherComplaints", "V2": "Pendency"})
        assert built["result"]["rhs_value"] == Decimal(194)   # engine unchanged
        assert heading(built, "Calculation") is None
        assert "total of 3 reported values" in built["text"]

    def test_equality_and_threshold_get_no_calculation_section(self):
        """'₹100 = ₹100' restates the row above it."""
        for expression, values in (("$V1 = $V2", {"V1": ["100"], "V2": ["90"]}),
                                   ("$V1 >= $V2", {"V1": ["80"], "V2": ["100"]})):
            built = build(expression, values, concepts={"V1": "Alpha", "V2": "Beta"})
            assert heading(built, "Calculation") is None, expression


# ═══════════════════════════════════════════════════════════════════════════
# 8 — nothing that already worked was lost
# ═══════════════════════════════════════════════════════════════════════════

class TestNoRegression:
    def _aggregate(self):
        return build(
            "$V1 = $V2 + $V3",
            {"V1": ["2360000"], "V2": ["450000"], "V3": ["1200000"]},
            units={"V1": "INR", "V2": "INR", "V3": "INR"},
            concepts={"V1": "TotalAssets", "V2": "Cash", "V3": "Investments"},
        )

    def test_the_card_still_emits_the_shared_section_spine(self):
        kinds = [s["kind"] for s in self._aggregate()["sections"]]
        spine = ["headline", "locator", "rule", "matrix", "fix", "details"]
        assert [k for k in kinds if k in spine] == spine

    def test_the_matrix_still_ends_in_an_emphasised_result_row(self):
        final = rows(self._aggregate())[-1]
        assert final["emphasis"] is True
        assert final["label"] == "Total Assets"
        assert final["status"] == error_card.STATUS_BAD
        assert "1,650,000" in final["expected"] and "2,360,000" in final["actual"]

    def test_the_drawer_still_carries_comparison_and_why_it_failed(self):
        built = self._aggregate()
        assert heading(built, "Comparison") is not None
        assert heading(built, "Why It Failed") is not None

    def test_the_v1_sections_are_untouched_by_all_of_this(self):
        """ERROR_CARD_V2=0 is the rollback path and is specified elsewhere; it
        must not have moved. v1 keeps its own wording, including
        'Calculated/Combined'."""
        built = self._aggregate()
        v1 = fe.build_sections(built["rule"], built["comparison"],
                               built["result"], built["labels"])
        headings = [s["heading"] for s in v1 if s.get("heading")]
        assert headings == ["Validation Rule", "Reported Values", "Comparison",
                            "Why It Failed", "How to Fix"]
        comparison = next(s for s in v1 if s.get("heading") == "Comparison")
        assert any(i["label"] == "Calculated/Combined" for i in comparison["items"])
        # v1's Why It Failed keeps the full point sequence, values included.
        why = next(s for s in v1 if s.get("heading") == "Why It Failed")
        assert any("is reported as" in b for b in why["bullets"])

    def test_the_card_drawer_does_not_repeat_the_matrix_figures(self):
        """Problem 6: the same two numbers were stated in the matrix, in
        Comparison and again in Why It Failed."""
        why = heading(self._aggregate(), "Why It Failed")["bullets"]
        assert not any("is reported as" in b for b in why)
        assert any("The rule requires" in b for b in why)
        assert any("so the check fails" in b for b in why)

    def test_emphasis_hints_still_accompany_the_prose(self):
        rule_section = section(self._aggregate(), "rule")
        assert "Total Assets" in rule_section["terms"]
        assert "equal to" in rule_section["ops"]

    def test_plain_text_form_carries_no_markdown(self):
        text = self._aggregate()["text"]
        assert "**" not in text and "##" not in text


# ═══════════════════════════════════════════════════════════════════════════
# 9 — the arithmetic is the engine's, and this change did not touch it
# ═══════════════════════════════════════════════════════════════════════════

class TestArithmeticIsUnchanged:
    @pytest.mark.parametrize("expression,values,lhs,rhs,passes", [
        ("$V1 = $V2 + $V3 - $V4",
         {"V1": ["10"], "V2": ["10"], "V3": ["5"], "V4": ["3"]}, "10", "12", False),
        ("$V1 = sum ( $V2 )", {"V1": ["0"], "V2": ["177", "14", "3"]}, "0", "194", False),
        ("round($V1 * 10) div 10 = round(($V2 + $V3 - $V4) * 10) div 10",
         {"V1": ["10.04"], "V2": ["10"], "V3": ["5"], "V4": ["5"]}, "10", "10", True),
        ("round($V1 div 1000) * 1000 = round((sum ($V2)) div 1000 ) * 1000",
         {"V1": ["1000400"], "V2": ["1000000"]}, "1000000", "1000000", True),
        ("$V1 >= 0.1", {"V1": ["12.54"]}, "12.54", "0.1", True),
    ])
    def test_the_card_reports_exactly_what_evaluate_computed(
            self, expression, values, lhs, rhs, passes):
        comparison = fx.parse_formula(expression)
        engine = fx.evaluate(comparison, values)
        assert engine["lhs_value"] == Decimal(lhs)
        assert engine["rhs_value"] == Decimal(rhs)
        assert engine["passes"] is passes

        built = build(expression, values)
        for key in ("lhs_value", "rhs_value", "difference", "passes",
                    "values_equal", "relationship", "uses_rounding"):
            assert built["result"][key] == engine[key], key

    def test_classification_never_mutates_the_ast(self):
        comparison = fx.parse_formula("$V1 = $V2 + $V3 - $V4")
        before = (comparison.operator, comparison.source,
                  comparison.lhs.variables(), comparison.rhs.variables(),
                  comparison.rhs.signed_variables())
        for _ in range(3):
            fk.classify(comparison)
        after = (comparison.operator, comparison.source,
                 comparison.lhs.variables(), comparison.rhs.variables(),
                 comparison.rhs.signed_variables())
        assert before == after
        # …and the verdict is identical afterwards.
        assert fx.evaluate(comparison, {"V1": ["10"], "V2": ["10"],
                                        "V3": ["5"], "V4": ["3"]})["rhs_value"] == Decimal(12)


# ═══════════════════════════════════════════════════════════════════════════
# 10 — the LLM payload constrains vocabulary without touching the numbers
# ═══════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════
# 11 — second refinement pass (A–F): the remaining presentation gaps
# ═══════════════════════════════════════════════════════════════════════════

class TestSemanticRoleFallback:
    """A/F — when no source can NAME an operand, say what it DOES.

    The old fallback repeated one sentence per operand: "must be equal to the
    total of a value not named in the validation output + the total of a value
    not named in the validation output", which reads as one value counted twice.
    """

    def test_unnamed_aggregate_operands_become_numbered_components(self):
        built = build(
            "round($V2 div 100000)*100000 = round((sum($V1)+sum($V3)) div 100000)*100000",
            {"V2": ["1004500000"], "V1": ["0"], "V3": ["0"]},
            units={"V1": "INR", "V2": "INR", "V3": "INR"},
            concepts={"V2": "AmountOfFundedExposureInInfrastructureSector"},
            message="Total of all groups should be summation of the values reported",
        )
        assert built["labels"]["V1"] == "Component amount 1"
        assert built["labels"]["V3"] == "Component amount 2"
        assert built["sources"]["V1"] == "role"
        # The resolvable name is untouched.
        assert built["labels"]["V2"] == "Amount Of Funded Exposure In Infrastructure Sector"
        assert fe._UNNAMED_LABEL not in built["text"]

    def test_a_non_monetary_operand_is_a_value_not_an_amount(self):
        """Calling a rate an "amount" would be a claim the units contradict."""
        built = build(
            "$V1 = $V2 div $V3", {"V1": ["2"], "V2": ["10"], "V3": ["5"]},
            concepts={"V1": "Ratio"},
        )
        assert built["labels"]["V2"] == "Component value 1"
        assert built["labels"]["V3"] == "Component value 2"

    def test_a_single_unnamed_component_is_not_numbered(self):
        built = build("$V1 = sum($V2)", {"V1": ["5"], "V2": ["3"]},
                      concepts={"V1": "Total"})
        assert built["labels"]["V2"] == "Component value"

    def test_mandatory_fields_with_no_recoverable_names_say_required_value(self):
        """'Memorandum TGAResidual Mandatory' — the validator gives no names."""
        built = build("not(empty($V1)) and not(empty($V2))", {},
                      message="Validation not satisfied: value is mandatory",
                      name="MemorandumTGAResidualMandatory")
        assert [r["label"] for r in rows(built)] == ["Required value 1", "Required value 2"]
        assert fe._UNNAMED_LABEL not in built["text"]
        # The headline counts them rather than listing meaningless phrases.
        assert section(built, "headline")["text"] == "2 required values are not reported."
        # …and the rule is stated plainly instead of as a literal empty() chain.
        assert section(built, "rule")["text"] == "Every value listed below must be reported."
        assert "it is not the case that" not in built["text"]

    def test_a_recoverable_name_still_beats_a_role_phrase(self):
        """R090 must not regress: real names win over the role fallback."""
        built = build(
            " and ".join(f"not(empty($V{i}))" for i in range(1, 7)),
            {}, message=_R090_MESSAGE,
        )
        assert built["labels"]["V1"] == "Outstanding Unsecured Guarantees with Domestic"
        assert all(built["sources"][f"V{i}"] == "message_fields" for i in range(1, 7))
        assert not any(r["label"].startswith("Required value") for r in rows(built))

    def test_role_phrases_are_not_demanded_of_the_llm(self):
        built = build("$V1 = $V2 + $V3", {"V1": ["10"], "V2": ["4"], "V3": ["3"]})
        _payload, required = fe.build_llm_payload(
            built["rule"], built["comparison"], built["result"], built["labels"])
        assert all(not fe._is_fallback_label(t) for t in required), required


class TestUninterpretableExpressionFallback:
    """B — state the business rule from the validator message; invent nothing."""

    _MESSAGE = ("if Total Credit Exposure is 150% of MAX( Total Limit Sanctioned to the "
                "Borrower, Total Amount Outstanding (Funded + Non Funded) ).")

    def _built(self):
        # `$V1 = if (…) then … else …` is outside the parser's grammar, so the
        # expression genuinely does not parse. That is the case under test.
        return build(
            "$V1 = if ($V2 >= 1.5) then $V2 else $V3",
            {"V1": ["5000000"], "V2": ["3000000"], "V3": ["2500000"]},
            units={"V1": "INR", "V2": "INR", "V3": "INR"},
            concepts={"V1": "TotalCreditExposure"},
            message=self._MESSAGE,
        )

    def test_the_expression_really_is_unparseable(self):
        assert self._built()["comparison"] is None

    def test_the_business_rule_is_restated_from_the_message(self):
        checks = heading(self._built(), "What the rule checks")
        assert checks is not None
        assert "Total Credit Exposure" in checks["bullets"][0]
        assert "the larger of" in checks["bullets"][0]
        assert "Total Limit Sanctioned to the Borrower" in checks["bullets"]
        assert "Total Amount Outstanding (Funded + Non Funded)" in checks["bullets"]

    def test_the_reported_values_are_shown_but_no_expectation_is_invented(self):
        built = self._built()
        shown = {r["label"]: r for r in rows(built)}
        assert shown["Total Credit Exposure"]["actual"] == "₹5,000,000"
        assert all(not r["expected"] for r in rows(built))
        text = built["text"]
        assert "The expression could not be independently calculated" in text
        assert "over by" not in text and "short by" not in text

    def test_operands_still_get_a_role_when_nothing_parsed(self):
        built = self._built()
        assert built["labels"]["V2"] == "Reported value 1"
        assert fe._UNNAMED_LABEL not in built["text"]

    def test_a_message_without_a_max_group_is_left_as_the_validators_sentence(self):
        points = fe._message_rule_points("Total assets must equal total liabilities.")
        assert points == ["Total assets must equal total liabilities."]

    def test_an_unsplittable_max_group_is_not_rewritten(self):
        """One alternative is not a choice; the sentence stays as written."""
        points = fe._message_rule_points("Exposure is 150% of MAX( 100 ).")
        assert points == ["Exposure is 150% of MAX( 100 )."]


class TestInternalScalingIsNotShownAsTheResult:
    """C — the × 10,000 is a precision device, not part of the ratio."""

    def _built(self):
        return build(
            "round(abs($V1*10000)) div 10000 = round(abs(($V2 div $V3)*10000)) div 10000",
            {"V1": ["0.03"], "V2": ["-495956792000"], "V3": ["17775625211000"]},
            units={"V2": "INR", "V3": "INR"},
            concepts={"V1": "MismatchAsPercentageToOutflows", "V2": "NetInflowOutflow",
                      "V3": "NetOutflows"},
            message="Mismatch as % to Outflows = Mismatch / Total Outflows",
        )

    def test_the_calculation_shows_the_ratio_not_the_scaled_intermediate(self):
        bullets = heading(self._built(), "Calculation")["bullets"]
        assert bullets[0] == ("₹-495,956,792,000 ÷ ₹17,775,625,211,000 = -0.0279009478")
        assert "× 10,000" not in bullets[0]
        assert "279.0095" not in bullets[0]

    def test_the_rounded_comparison_follows_it(self):
        bullets = heading(self._built(), "Calculation")["bullets"]
        assert bullets[1] == ("Rounded to the nearest 0.0001: 0.0279 expected, "
                              "0.03 reported.")

    def test_the_scaled_intermediate_is_gone_from_the_comparison_block(self):
        items = {i["label"]: i["value"] for i in heading(self._built(), "Comparison")["items"]}
        assert "279.0095" not in " ".join(items.values())
        assert "300" not in " ".join(items.values())
        # The scaling is acknowledged as a secondary note, not as a result.
        assert "precision device" in items["Note"]
        assert "10,000" in items["Note"]

    def test_a_sign_flip_is_never_presented_as_a_rounding_step(self):
        """The rule compares absolute values; '-0.0279 → rounds to 0.0279'
        would state a falsehood about the sign."""
        items = {i["label"]: i["value"] for i in heading(self._built(), "Comparison")["items"]}
        assert items["Calculated ratio"] == "0.0279"

    def test_the_engines_own_figures_are_untouched(self):
        result = self._built()["result"]
        engine = fx.evaluate(
            fx.parse_formula(
                "round(abs($V1*10000)) div 10000 = round(abs(($V2 div $V3)*10000)) div 10000"),
            {"V1": ["0.03"], "V2": ["-495956792000"], "V3": ["17775625211000"]})
        for key in ("lhs_value", "rhs_value", "difference", "passes", "rhs_raw"):
            assert result[key] == engine[key], key

    def test_an_unscaled_aggregate_keeps_the_engines_raw_pair(self):
        """The de-scaling path must not touch a rule that has no such scaling."""
        built = build(
            "round($V1 div 100000)*100000 = round(($V2 + $V3) div 100000)*100000",
            {"V1": ["608709000"], "V2": ["34000"], "V3": ["0"]},
            units={"V1": "INR", "V2": "INR", "V3": "INR"},
            concepts={"V1": "Total", "V2": "LossAdvances", "V3": "Other"},
        )
        assert fe._internal_scaling_hidden(built["comparison"], built["kind"]) is False
        items = {i["label"]: i["value"] for i in heading(built, "Comparison")["items"]}
        assert items["Reported"] == "₹608,709,000 → rounds to ₹608,700,000"
        assert items["Calculated total"] == "₹34,000 → rounds to ₹0"
        assert "Note" not in items


class TestValidatorMessageVersusAst:
    """D — the AST stays the source of truth for the mathematics."""

    def test_a_percent_in_the_message_does_not_make_a_ratio_a_percentage(self):
        """R061: the message says 'TCE * 100 / (…)' but the formula in the error
        file has no × 100. Calling the result a percentage would assert a
        calculation the expression does not perform."""
        built = build(
            "round($V4*10000) div 10000 = round((($V1) div ($V5+$V6))*10000) div 10000",
            {"V4": ["0.02"], "V1": ["0"], "V5": ["309671000000"], "V6": ["0"]},
            message=_R061_MESSAGE,
            concepts={"V4": "AggregateCreditExposureAsPercentageOfCapitalFunds"},
        )
        assert built["kind"] == fk.RATIO
        assert "calculated ratio" in built["text"]
        assert "calculated percentage" not in built["text"]
        # The business terminology still reaches the reader — through the
        # resolved names, which is where it is safe.
        assert "% of Capital Funds" in built["text"]
        assert built["labels"]["V1"] == "TCE"

    def test_a_formula_that_does_multiply_by_100_is_called_a_percentage(self):
        built = build(
            "$V4 = ($V1 * 100) div ($V5 + $V6)",
            {"V4": ["0.02"], "V1": ["0"], "V5": ["309671000000"], "V6": ["0"]},
            concepts={"V4": "TcePercentage"},
        )
        assert built["kind"] == fk.PERCENTAGE
        assert "calculated percentage" in built["text"]


class TestThresholdPresentation:
    """E — show reported vs required, and flag inconsistency instead of
    inventing a failure."""

    def test_a_non_numeric_reported_value_still_gets_the_rules_limit(self):
        """'12.54%' is refused by _to_decimal (correctly — it is not a number),
        which left the Expected column empty and the card generic."""
        built = build("$V1 >= 0.1", {"V1": ["12.54%"]},
                      concepts={"V1": "PercentageOfExposureToTier1Capital"})
        assert built["result"] is None                 # engine unchanged
        row = rows(built)[0]
        assert row["actual"] == "12.54%"
        assert row["expected"] == "greater than or equal to 0.1"
        notes = " ".join(s["text"] for s in built["sections"] if s.get("kind") == "note")
        assert "not a plain number" in notes
        assert "could not be re-calculated" in notes
        # No verdict is fabricated from a value that could not be read.
        assert "over by" not in built["text"] and "short by" not in built["text"]

    def test_a_displayed_pass_is_reported_as_an_inconsistency(self):
        built = build("$V1 >= 0.1", {"V1": ["12.54"]},
                      concepts={"V1": "PercentageOfExposureToTier1Capital"})
        headline = section(built, "headline")["text"]
        assert headline == ("The reported values appear to satisfy this rule, but the "
                           "validator reported it as failed.")
        notes = " ".join(s["text"] for s in built["sections"] if s.get("kind") == "note")
        assert "12.54" in notes and "greater than or equal to 0.1" in notes
        assert "validator reported this check as failed" in notes
        # The validator is not declared wrong, and the data is not claimed fixed.
        assert "already have been corrected" not in built["text"]
        assert "over by" not in built["text"]

    def test_a_genuinely_breached_threshold_is_unaffected(self):
        built = build("$V1 >= 0.1", {"V1": ["0.05"]},
                      concepts={"V1": "PercentageOfExposureToTier1Capital"})
        row = rows(built)[-1]
        assert row["status"] == error_card.STATUS_BAD
        assert "greater than or equal to 0.1" in row["expected"]
        assert "short by" in row["note"]
        assert "appear to satisfy" not in built["text"]


# ═══════════════════════════════════════════════════════════════════════════
# 12 — record-count rules and rule-name terminology
# ═══════════════════════════════════════════════════════════════════════════

class TestCountRules:
    """`count($V1) >= 50` constrains how many rows exist, not the value of any
    of them. The old wording — "Sector code is 40 lower than the required
    number of values" — reads as a statement about a field that has no numeric
    magnitude at all.
    """

    def _short(self):
        return build("count($V1) >= 50", {"V1": ["101"] * 10},
                     units={"V1": "INR"}, concepts={"V1": "SectorCode"},
                     name="SectionA-NumberOfRecordsCheck",
                     message="At least 50 sector code records are required")

    def _over(self):
        return build("count($V1) <= 5", {"V1": ["7"] * 7},
                     concepts={"V1": "BranchCode"},
                     name="SectionB-NumberOfRecordsCheck")

    def test_headline_counts_records_instead_of_valuing_the_field(self):
        built = self._short()
        assert built["kind"] == fk.COUNT
        assert section(built, "headline")["text"] == (
            "10 Sector Code records are reported, but at least 50 are required.")
        # The old sentence must not survive anywhere.
        assert "is 40 lower" not in built["text"]
        assert "required number of values" not in built["text"]

    def test_the_row_shows_required_reported_and_the_shortfall(self):
        row = rows(self._short())[-1]
        assert row["label"] == "Sector Code records"
        assert row["expected"] == "at least 50"
        assert row["actual"] == "10"
        assert row["note"] == "short by 40"
        assert row["status"] == error_card.STATUS_BAD

    def test_a_count_is_never_formatted_as_currency(self):
        """The counted facts carry INR; the count of them does not."""
        built = self._short()
        assert "₹10" not in built["text"] and "₹50" not in built["text"]
        row = rows(built)[-1]
        assert "₹" not in row["actual"] and "₹" not in row["expected"]

    def test_the_prose_talks_about_records_throughout(self):
        why = heading(self._short(), "Why It Failed")["bullets"]
        joined = " ".join(why)
        assert "The rule requires at least 50." in joined
        assert "40 fewer than required" in joined
        assert "Sector Code is" not in joined            # not a value claim
        fix = section(self._short(), "fix")["steps"][0]
        assert "how many Sector Code records" in fix

    def test_a_maximum_count_is_worded_as_a_limit_not_a_requirement(self):
        built = self._over()
        assert section(built, "headline")["text"] == (
            "7 Branch Code records are reported, but at most 5 are allowed.")
        row = rows(built)[-1]
        assert row["expected"] == "at most 5" and row["note"] == "over by 2"
        assert "2 more than allowed" in " ".join(
            heading(built, "Why It Failed")["bullets"])

    def test_uniqueness_is_never_claimed(self):
        """fn:count counts rows. Nothing may imply it counts DISTINCT values."""
        for built in (self._short(), self._over()):
            lowered = built["text"].lower()
            assert "unique" not in lowered
            assert "distinct" not in lowered

    def test_the_engines_count_is_unchanged(self):
        built = self._short()
        engine = fx.evaluate(fx.parse_formula("count($V1) >= 50"), {"V1": ["101"] * 10})
        assert engine["lhs_value"] == Decimal(10) and engine["rhs_value"] == Decimal(50)
        for key in ("lhs_value", "rhs_value", "difference", "passes", "relationship"):
            assert built["result"][key] == engine[key], key


class TestRuleNameTerminology:
    """The rule's own name for the figure it constrains, when the validator
    message states it and the assertion label confirms it."""

    _RULE_NAME = ("TCE as % of Capital Funds = TCE * 100/ [Regulatory Capital "
                  "(Tier I + Tier II) of Previous March + Capital Infusion during "
                  "the period (April to date)]")
    _TAXONOMY_LABEL = "Aggregate credit exposure as percentage of capital funds"

    class _Index:
        """Stands in for the taxonomy label linkbase."""
        def __init__(self, mapping):
            self._mapping = mapping

        def concept_label(self, concept):
            return self._mapping.get(concept, "")

    def _rule(self, name=None):
        return {
            "rule_name": name or self._RULE_NAME,
            "formula_expression": ("round($V4*10000) div 10000 = "
                                   "round((($V1) div ($V5+$V6))*10000) div 10000"),
            "instances": [{"business_message": _R061_MESSAGE, "facts": [
                {"var": "V4", "value": "0.02", "unit": "", "context": "c4",
                 "concept": "AggregateCreditExposureAsPercentageOfCapitalFunds"},
                {"var": "V1", "value": "0", "unit": "", "context": "c1", "concept": ""},
                {"var": "V5", "value": "309671000000", "unit": "", "context": "c5",
                 "concept": ""},
                {"var": "V6", "value": "0", "unit": "", "context": "c6", "concept": ""},
            ]}],
        }

    def _resolve(self, rule):
        index = self._Index({
            "AggregateCreditExposureAsPercentageOfCapitalFunds": self._TAXONOMY_LABEL})
        comparison, result = fe.evaluate_instance(rule, rule["instances"][0])
        labels, sources = fe.resolve_labels(rule, comparison, None, index)
        sections = fe.build_card_sections(rule, comparison, result, labels)
        return labels, sources, sections

    def test_the_rules_own_terminology_wins_over_the_taxonomy_label(self):
        """Both names are correct; only one is the wording the rule, the message
        and the form all use."""
        labels, sources, sections = self._resolve(self._rule())
        assert labels["V4"] == "TCE as % of Capital Funds"
        assert sources["V4"] == "rule_name"
        headline = next(s for s in sections if s["kind"] == "headline")["text"]
        assert headline.startswith("TCE as % of Capital Funds")
        assert self._TAXONOMY_LABEL not in headline

    def test_the_whole_card_uses_one_name_for_the_figure(self):
        _labels, _sources, sections = self._resolve(self._rule())
        rule_text = next(s for s in sections if s["kind"] == "rule")["text"]
        assert rule_text.startswith("TCE as % of Capital Funds must be equal to")
        row = next(s for s in sections if s["kind"] == "matrix")["rows"][-1]
        assert row["label"] == "TCE as % of Capital Funds"

    def test_an_uncorroborated_message_name_never_displaces_the_taxonomy(self):
        """The guard: without the assertion name agreeing, the taxonomy label
        stands. This is what stops the change reaching the rest of the corpus."""
        labels, sources, _sections = self._resolve(
            self._rule(name="LR-PartA1B1B2AndC-SomethingElseEntirely"))
        assert labels["V4"] == self._TAXONOMY_LABEL
        assert sources["V4"] == "label_linkbase"

    def test_a_camel_case_assertion_id_never_corroborates_a_name(self):
        """Regression: real 2041 assertions are IDENTIFIERS that embed concept
        names —
        'Sec-8_SectoralCredit_TotalTermLoansSanctionedAndTotalTermLoansDisbursed'
        contains the letters of 'Total Term Loans Sanctioned' but states
        nothing. On those files the taxonomy label is the better name, and a
        compacted match displaced it."""
        labels = {"V1": "Term Loans Sanctioned"}
        sources = {"V1": "label_linkbase"}
        comparison = fx.parse_formula("$V1 > $V2")
        fe._prefer_rule_terminology(
            labels, sources, comparison,
            {"rule_name": "Sec-8_SectoralCredit_TotalTermLoansSanctioned"
                          "AndTotalTermLoansDisbursed"},
            "Total Term Loans Sanctioned")
        assert labels["V1"] == "Term Loans Sanctioned"
        assert sources["V1"] == "label_linkbase"

    def test_a_short_message_name_is_never_matched_against_an_assertion_id(self):
        """'Total' would hit almost any assertion name by coincidence."""
        assert fe._MIN_RULE_TERM_CHARS >= 12
        labels, sources = {}, {}
        comparison = fx.parse_formula("$V1 = $V2")
        labels["V1"] = "Taxonomy name"
        fe._prefer_rule_terminology(labels, sources, comparison,
                                   {"rule_name": "TotalsCheck"}, "Total")
        assert labels["V1"] == "Taxonomy name"

    def test_the_operand_names_and_the_arithmetic_are_untouched(self):
        labels, _sources, sections = self._resolve(self._rule())
        assert labels["V1"] == "TCE"
        assert labels["V5"] == "Regulatory Capital (Tier I + Tier II) of Previous March"
        row = next(s for s in sections if s["kind"] == "matrix")["rows"][-1]
        assert row["expected"] == "0" and row["actual"] == "0.02"
        assert row["note"] == "over by 0.02"


CORPUS = Path(r"D:\Repo(new)\Instance")
needs_corpus = pytest.mark.skipif(
    not CORPUS.is_dir(), reason=r"real repo data (D:\Repo(new)) not present",
)


@needs_corpus
class TestOnTheRealCorpus:
    """The existing v2 suite pins ERROR_CARD_V2=0 (it specifies the legacy
    layout), so nothing else exercises the unified card against real files."""

    def _explained(self):
        out = []
        for path in CORPUS.rglob("*.html"):
            rules = fe.parse_formula_errors_v2(str(path))
            if not rules:
                continue
            for item in fe.explain_formula_rules(
                    rules[:3], form_id=path.parent.name, error_file_path=str(path)):
                comparison, _ = fe.evaluate_instance(item, item["instances"][0])
                out.append((path, item, fk.classify(comparison)))
        return out

    def test_every_real_rule_still_explains_without_raising(self):
        explained = self._explained()
        assert len(explained) >= 20, len(explained)
        for path, item, _kind in explained:
            assert item["explanation"].strip(), path
            assert item["explanation_sections"], path

    def test_no_variable_id_reaches_the_user_on_any_real_file(self):
        import re
        for path, item, _kind in self._explained():
            assert not re.search(r"\bV\d+\b", item["explanation"]), (path, item["rule_name"])

    def test_summation_language_appears_only_on_real_aggregates(self):
        for path, item, kind in self._explained():
            if kind == fk.AGGREGATE:
                continue
            lowered = item["explanation"].lower()
            for phrase in _SUM_LANGUAGE:
                assert phrase not in lowered, (path, item["rule_name"], kind, phrase)

    def test_no_markdown_leaks_into_the_card(self):
        for path, item, _kind in self._explained():
            assert "**" not in item["explanation"], path
            assert "###" not in item["explanation"], path


class TestLlmPayload:
    def _payload(self, expression, values, **kw):
        built = build(expression, values, **kw)
        return fe.build_llm_payload(built["rule"], built["comparison"],
                                    built["result"], built["labels"])

    def test_payload_carries_the_formula_type_and_its_vocabulary_rule(self):
        payload, _required = self._payload(
            "round(abs($V3*10000)) div 10000 = round(abs(($V1 div $V2)*10000)) div 10000",
            {"V3": ["-0.03"], "V1": ["-495956792000"], "V2": ["17775625211000"]},
            units={"V1": "INR", "V2": "INR"},
        )
        assert payload["formula_type"] == fk.RATIO
        guidance = payload["how_to_describe_the_calculation"].lower()
        assert "never call it a sum" in guidance
        assert "currency symbol" in guidance

    def test_payload_values_are_still_the_engines(self):
        payload, _ = self._payload(
            "$V1 = $V2 + $V3",
            {"V1": ["2360000"], "V2": ["450000"], "V3": ["1200000"]},
        )
        assert payload["left_side"]["compared_value"] == "2360000"
        assert payload["right_side"]["compared_value"] == "1650000"
        assert payload["difference_between_compared_values"] == "710000"
        assert payload["rule_is_satisfied_by_these_values"] is False

    def test_an_unresolved_label_is_not_demanded_of_the_model(self):
        """Requiring 'a value not named in the validation output' to appear
        verbatim would reject every answer the model could give."""
        _payload, required = self._payload(
            "$V1 = $V2 + $V3", {"V1": ["10"], "V2": ["4"], "V3": ["3"]},
        )
        assert all(not t.startswith(fe._UNNAMED_LABEL) for t in required)
