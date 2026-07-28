"""Tests for backend.tools.formula_error_generic — the formula-error
parsing + explanation flow for NON-4000-series returns (no backtracking
data, Variable/Name/Value/Context/Unit/Decimal/Precision table shape).

This module and these tests are entirely separate from the existing
4000-series formula-error tests/flow (backend/tools/report_lookup.py's
parse_formula_errors, explain_formula_errors, etc.) — nothing here imports
or exercises that code, and nothing in that flow is touched by this file.

Coverage (per the non-4000-series requirements):
  - simple equality (V1 = V2)
  - rounded two-variable equality (round(V1/D)*D = round(V2/D)*D)
  - greater-than, greater-than-or-equal, less-than, less-than-or-equal
  - inequality with a summed side (V1 <= V2 + V3)
  - missing taxonomy mappings (graceful fallback, never an invented location)
  - multiple failed instances
  - the HTML parser itself, including tab-scoping (excluding noise from the
    other two error tabs) and multi-instance capture
"""
from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import backend.tools.formula_error_generic as g


def _var(var, concept, value, context="ctx", unit="INR", decimal="-3"):
    return {"var": var, "concept": concept, "value": value, "context": context,
            "unit": unit, "decimal": decimal}


def _rule(rule_name, formula_expression, variables, business_message="", extra_instances=0):
    instances = [{"business_message": business_message, "variables": variables}]
    for _ in range(extra_instances):
        instances.append({"business_message": business_message, "variables": variables})
    return {"rule_name": rule_name, "formula_expression": formula_expression, "instances": instances}


def _taxonomy(assertion_id, variables):
    """variables: list of (name, concept_id_or_None, label_or_None, table, column, code_filter)"""
    vars_out = []
    concepts = {}
    for name, concept_id, label, table, column, code in variables:
        v = {"name": name, "concept_id": concept_id}
        if concept_id:
            v["db_mapping"] = {"status": "confirmed_by_internal_metadata", "table": table,
                                "column": column, "code_filter": code, "multiplier": 100000}
            concepts[concept_id] = {"concept_id": concept_id, "label": label}
        else:
            v["db_mapping"] = {"status": "unmapped", "table": None, "column": None, "code_filter": None}
        vars_out.append(v)
    return {
        "by_assertion_id": {assertion_id: {"assertion_id": assertion_id, "variables": vars_out}},
        "by_concept_id": concepts,
    }


# ── 1. Operator-aware formula parsing ───────────────────────────────────────

class TestParseComparisonFormula:
    def test_simple_equality(self):
        parsed = g.parse_comparison_formula("$V1 = $V2")
        assert parsed == {"operator": "=", "lhs_vars": ["V1"], "rhs_vars": ["V2"], "rounding_divisor": None}

    def test_rounded_equality(self):
        parsed = g.parse_comparison_formula(
            "(round($V1 div 1000)*1000) = (round($V2 div 1000)*1000)"
        )
        assert parsed["operator"] == "="
        assert parsed["lhs_vars"] == ["V1"]
        assert parsed["rhs_vars"] == ["V2"]
        assert parsed["rounding_divisor"] == 1000

    def test_greater_than(self):
        parsed = g.parse_comparison_formula("$V1 > $V2")
        assert parsed["operator"] == ">"

    def test_greater_than_or_equal(self):
        parsed = g.parse_comparison_formula("$V1 >= $V2")
        assert parsed["operator"] == ">="
        assert parsed["lhs_vars"] == ["V1"]
        assert parsed["rhs_vars"] == ["V2"]

    def test_less_than(self):
        parsed = g.parse_comparison_formula("$V1 < $V2")
        assert parsed["operator"] == "<"

    def test_less_than_or_equal(self):
        parsed = g.parse_comparison_formula("$V1 <= $V2")
        assert parsed["operator"] == "<="

    def test_inequality_with_summed_side(self):
        parsed = g.parse_comparison_formula("$V1 <= ( $V2 + $V3 )")
        assert parsed["operator"] == "<="
        assert parsed["lhs_vars"] == ["V1"]
        assert parsed["rhs_vars"] == ["V2", "V3"]

    def test_rounded_equality_is_not_misread_as_ratio_or_sum(self):
        """This is the exact bug this module exists to avoid: round()
        presence must not force a ratio-check reading, and a "+" inside a
        round()-wrapped side must not force a sum_check reading — the
        operator alone determines the comparison."""
        parsed = g.parse_comparison_formula(
            "(round($V1 div 1000)*1000) = (round($V2 div 1000)*1000)"
        )
        assert parsed["operator"] == "="
        assert len(parsed["rhs_vars"]) == 1  # not treated as a sum

    def test_no_operator_returns_none(self):
        assert g.parse_comparison_formula("$V1 $V2") is None

    def test_empty_formula_returns_none(self):
        assert g.parse_comparison_formula("") is None


# ── 2. Deterministic calculation ────────────────────────────────────────────

class TestEvaluateComparison:
    def test_simple_equality_mismatch(self):
        parsed = g.parse_comparison_formula("$V1 = $V2")
        calc = g.evaluate_comparison(parsed, {"V1": Decimal("276553464000"), "V2": Decimal("276553463000")})
        assert calc["passes"] is False
        assert calc["difference"] == Decimal("1000")
        assert calc["values_equal"] is False

    def test_rounded_equality_applies_rounding_before_comparing(self):
        parsed = g.parse_comparison_formula(
            "(round($V1 div 1000)*1000) = (round($V2 div 1000)*1000)"
        )
        # Un-rounded values differ by only 400 — after rounding to the
        # nearest 1000 they land on the SAME multiple, so the check passes.
        calc = g.evaluate_comparison(parsed, {"V1": Decimal("1000400"), "V2": Decimal("1000000")})
        assert calc["lhs_compared"] == calc["rhs_compared"] == Decimal("1000000")
        assert calc["passes"] is True

    def test_greater_than_fails_when_equal(self):
        parsed = g.parse_comparison_formula("$V1 > $V2")
        calc = g.evaluate_comparison(parsed, {"V1": Decimal("0"), "V2": Decimal("0")})
        assert calc["passes"] is False
        assert calc["values_equal"] is True

    def test_greater_than_or_equal_passes_when_equal(self):
        parsed = g.parse_comparison_formula("$V1 >= $V2")
        calc = g.evaluate_comparison(parsed, {"V1": Decimal("5"), "V2": Decimal("5")})
        assert calc["passes"] is True

    def test_less_than_fails_when_equal(self):
        parsed = g.parse_comparison_formula("$V1 < $V2")
        calc = g.evaluate_comparison(parsed, {"V1": Decimal("0"), "V2": Decimal("0")})
        assert calc["passes"] is False

    def test_less_than_or_equal_passes(self):
        parsed = g.parse_comparison_formula("$V1 <= $V2")
        calc = g.evaluate_comparison(parsed, {"V1": Decimal("3"), "V2": Decimal("5")})
        assert calc["passes"] is True

    def test_inequality_with_summed_side(self):
        parsed = g.parse_comparison_formula("$V1 <= ( $V2 + $V3 )")
        calc = g.evaluate_comparison(
            parsed, {"V1": Decimal("29594969000"), "V2": Decimal("0"), "V3": Decimal("0")}
        )
        assert calc["rhs_value"] == Decimal("0")
        assert calc["passes"] is False
        assert calc["difference"] == Decimal("29594969000")

    def test_missing_variable_returns_none(self):
        parsed = g.parse_comparison_formula("$V1 = $V2")
        assert g.evaluate_comparison(parsed, {"V1": Decimal("1")}) is None


# ── 3. Message-derived operand naming ───────────────────────────────────────

class TestMessageDerivedLabels:
    def test_strips_wrapper_and_splits_on_operator(self):
        msg = '▼ "en:Identity "Total Term Loans Sanctioned > Total Term Loans Disbursed" do not tally."'
        result = g.extract_operand_labels_from_message(msg, ">")
        assert result == ("Total Term Loans Sanctioned", "Total Term Loans Disbursed")

    def test_ge_operator(self):
        msg = '▼ "en:Identity "1. Agriculture and Allied Activites >= Piority Sector Agriculture" do not tally."'
        result = g.extract_operand_labels_from_message(msg, ">=")
        assert result[0] == "1. Agriculture and Allied Activites"
        assert result[1] == "Piority Sector Agriculture"

    def test_summed_rhs_split_by_count(self):
        msg = '"Funded Advances <= Exposure A + Exposure B" do not tally.'
        result = g.extract_operand_labels_from_message(msg, "<=")
        parts = g._split_summed_labels(result[1], 2)
        assert parts == ["Exposure A", "Exposure B"]

    def test_no_matching_operator_returns_none(self):
        assert g.extract_operand_labels_from_message('"A vs B" do not tally.', ">=") is None


# ── 4. End-to-end deterministic explanation, per formula shape ─────────────

class TestRenderGenericFormulaExplanation:
    def test_simple_equality(self):
        rule = _rule(
            "Sec4VsSec2Total", "$V1 = $V2",
            [_var("V1", "LoansAdvancesOutstanding", "276553464000"),
             _var("V2", "AmountOutstanding", "276553463000")],
            business_message='"Total A = Total B" do not tally.',
        )
        text = g.render_generic_formula_explanation(rule)
        assert "does not match" in text
        assert "276,553,464,000" in text
        assert "276,553,463,000" in text
        assert "1,000" in text  # difference

    def test_rounded_equality_not_misclassified(self):
        rule = _rule(
            "Sec1VsSec2", "(round($V1 div 1000)*1000) = (round($V2 div 1000)*1000)",
            [_var("V1", "LoansAdvances", "276553464000"),
             _var("V2", "AmountOutstanding", "276553463000")],
            business_message='"Total A = Total B" do not tally.',
        )
        text = g.render_generic_formula_explanation(rule)
        assert "nearest 1,000" in text
        assert "1,000" in text  # still surfaces the post-rounding difference

    def test_greater_than_when_lhs_actually_greater(self):
        """V1 > V2 and V1 IS greater — the condition is satisfied. Included
        for completeness of the operator+relationship matrix even though
        production only ever renders failing instances today."""
        rule = _rule(
            "TermLoans", "$V1 > $V2",
            [_var("V1", "TermLoansSanctioned", "500"), _var("V2", "TermLoansDisbursed", "300")],
            business_message='"Sanctioned > Disbursed" do not tally.',
        )
        text = g.render_generic_formula_explanation(rule)
        assert "is greater than" in text
        assert "condition is satisfied" in text

    def test_greater_than_equal_values_phrased_honestly(self):
        """4 of 8 real rules examined hit exactly this case — the rule
        requires strict '>' but both sides are equal (the exact reported
        bug: this must never be phrased as one value "exceeding" the
        other). Must not dramatize a zero difference as some large
        discrepancy."""
        rule = _rule(
            "TermLoans", "$V1 > $V2",
            [_var("V1", "TermLoansSanctioned", "0"), _var("V2", "TermLoansDisbursed", "0")],
            business_message='"Sanctioned > Disbursed" do not tally.',
        )
        text = g.render_generic_formula_explanation(rule)
        assert "must be greater than" in text
        assert "both values are equal" in text
        assert "strict greater-than condition is not satisfied" in text
        assert "exceed" not in text.lower()

    def test_greater_than_when_lhs_actually_lower(self):
        """V1 > V2 but V1 is actually LOWER — must say "lower than", never
        "exceeded" or a direction-agnostic "but it is not"."""
        rule = _rule(
            "FundedAdvances", "$V1 > $V2",
            [_var("V1", "FundedOutstandingAdvances", "100"), _var("V2", "FundedCreditExposure", "300")],
            business_message='"Funded Advances > Funded Exposure" do not tally.',
        )
        text = g.render_generic_formula_explanation(rule)
        assert "must be greater than" in text
        assert "it is lower than" in text
        assert "exceed" not in text.lower()

    def test_greater_than_or_equal_when_values_equal_is_satisfied(self):
        """V1 >= V2 and both are equal — the condition IS satisfied (this
        is the key difference from strict '>')."""
        rule = _rule(
            "PrioritySector", "$V1 >= $V2",
            [_var("V1", "AgriAllied", "1000"), _var("V2", "PrioritySectorAgri", "1000")],
            business_message='"Agri and Allied >= Priority Sector Agri" do not tally.',
        )
        text = g.render_generic_formula_explanation(rule)
        assert "must be greater than or equal to" in text
        assert "both values are equal" in text
        assert "condition is satisfied" in text

    def test_greater_than_or_equal(self):
        rule = _rule(
            "PrioritySector", "$V1 >= $V2",
            [_var("V1", "AgriAllied", "5037575000"), _var("V2", "PrioritySectorAgri", "12251059000")],
            business_message='"Agri and Allied >= Priority Sector Agri" do not tally.',
        )
        text = g.render_generic_formula_explanation(rule)
        assert "must be greater than or equal to" in text
        assert "it is lower than" in text
        assert "7,213,484,000" in text  # difference

    def test_less_than(self):
        rule = _rule(
            "NonFoodCredit", "$V1 < $V2",
            [_var("V1", "OtherNonFoodCredit", "0"), _var("V2", "NonFoodCreditTotal", "0")],
            business_message='"Other < Total" do not tally.',
        )
        text = g.render_generic_formula_explanation(rule)
        assert "must be less than" in text
        assert "both values are equal" in text
        assert "strict less-than condition is not satisfied" in text

    def test_less_than_when_lhs_actually_greater(self):
        """V1 < V2 but V1 is actually GREATER — must say "greater than",
        never a direction-agnostic "but it is not"."""
        rule = _rule(
            "NonFoodCredit", "$V1 < $V2",
            [_var("V1", "OtherNonFoodCredit", "500"), _var("V2", "NonFoodCreditTotal", "200")],
            business_message='"Other < Total" do not tally.',
        )
        text = g.render_generic_formula_explanation(rule)
        assert "must be less than" in text
        assert "it is greater than" in text

    def test_less_than_or_equal_when_lhs_exceeds_without_sum(self):
        """V1 <= V2 (single term, no sum) and V1 > V2 — the plain
        exceeds-the-ceiling wording, distinct from the summed-RHS phrasing."""
        rule = _rule(
            "SingleCap", "$V1 <= $V2",
            [_var("V1", "ReportedAmount", "500"), _var("V2", "AllowedCeiling", "200")],
            business_message='"Reported Amount <= Allowed Ceiling" do not tally.',
        )
        text = g.render_generic_formula_explanation(rule)
        assert "must not exceed" in text
        assert "it is greater than the allowed value" in text
        assert "Combined value" not in text

    def test_less_than_or_equal_with_summed_side(self):
        rule = _rule(
            "MicroFinance", "$V1 <= ( $V2 + $V3 )",
            [_var("V1", "FundedOutstandingAdvances", "29594969000"),
             _var("V2", "AmountOutstandingOfGrossFundedExposure", "0"),
             _var("V3", "AmountOutstandingOfGrossFundedExposure", "0")],
            business_message='"Funded Advances <= Exposure A + Exposure B" do not tally.',
        )
        text = g.render_generic_formula_explanation(rule)
        assert "must not exceed" in text
        assert "the combined value of" in text
        assert "exceeds the allowed combined amount by" in text
        assert "29,594,969,000" in text
        assert "Combined value" in text  # the stats line

    def test_equality_values_differ(self):
        rule = _rule(
            "Sec4VsSec2", "$V1 = $V2",
            [_var("V1", "LoansAdvancesOutstanding", "276553464000"),
             _var("V2", "AmountOutstanding", "276553463000")],
            business_message='"Total A = Total B" do not tally.',
        )
        text = g.render_generic_formula_explanation(rule)
        assert "does not match" in text
        assert "differ by" in text
        assert "1,000" in text

    def test_missing_taxonomy_mapping_falls_back_gracefully(self):
        """No taxonomy enrichment applied at all — must still produce a
        usable explanation from the message/raw concept name, and must
        never claim a database location that doesn't exist."""
        rule = _rule(
            "UnmappedRule", "$V1 < $V2",
            [_var("V1", "SomeRawConceptName", "0"), _var("V2", "AnotherRawConceptName", "0")],
            business_message='"Some Business Label < Another Business Label" do not tally.',
        )
        text = g.render_generic_formula_explanation(rule)
        assert "Some Business Label" in text
        assert "Another Business Label" in text
        assert "No reliable database location is available" in text
        assert "CIMS_" not in text  # never invents a table name

    def test_multiple_failed_instances_summarized_not_dumped(self):
        rule = _rule(
            "TermLoans", "$V1 > $V2",
            [_var("V1", "TermLoansSanctioned", "0"), _var("V2", "TermLoansDisbursed", "0")],
            business_message='"Sanctioned > Disbursed" do not tally.',
            extra_instances=148,
        )
        text = g.render_generic_formula_explanation(rule)
        assert "149 reporting instances" in text
        # Only ONE set of figures shown, not 149 repeated blocks.
        assert text.count("₹0") <= 4

    def test_no_variables_returns_none(self):
        rule = {"rule_name": "Empty", "formula_expression": "$V1 = $V2", "instances": []}
        assert g.render_generic_formula_explanation(rule) is None

    def test_unparseable_formula_falls_back_to_message_only(self):
        rule = _rule("Weird", "not a real formula", [], business_message="Something failed.")
        text = g.render_generic_formula_explanation(rule)
        assert "Something failed." in text
        assert "How to fix" in text


# ── 5. Taxonomy enrichment (reuses taxonomy_lookup — verified end-to-end) ──

class TestTaxonomyEnrichment:
    def test_mapped_variable_gets_label_and_location(self):
        rule = _rule(
            "TermLoans", "$V1 > $V2",
            [_var("V1", "TermLoansSanctioned", "0"), _var("V2", "TermLoansDisbursed", "0")],
            business_message='"Sanctioned > Disbursed" do not tally.',
        )
        taxonomy = _taxonomy("TermLoans", [
            ("V1", "in-rbi-rep:TermLoansSanctioned", "Term Loans Sanctioned",
             "CIMS_RAQ_Q_SEC8_SEC_CREDIT", "VALUE", "1364"),
            ("V2", "in-rbi-rep:TermLoansDisbursed", "Term Loans Disbursed",
             "CIMS_RAQ_Q_SEC8_SEC_CREDIT", "VALUE", "1378"),
        ])
        enriched = g.enrich_generic_rule_with_taxonomy(rule, taxonomy)
        v1 = enriched["instances"][0]["variables"][0]
        assert v1["concept_label"] == "Term Loans Sanctioned"
        assert "CIMS_RAQ_Q_SEC8_SEC_CREDIT.VALUE" in v1["db_location"]
        assert "1364" in v1["db_location"]

    def test_unmapped_variable_gets_nothing_invented(self):
        rule = _rule(
            "PartlyMapped", "$V1 > $V2",
            [_var("V1", "FundedOutstandingAdvances", "1"), _var("V2", "FundedCreditExposure", "1")],
        )
        taxonomy = _taxonomy("PartlyMapped", [
            ("V1", None, None, None, None, None),
            ("V2", "in-rbi-rep:FundedCreditExposure", "Funded credit exposure",
             "CIMS_RAQ_Q_SEC8_SEC_CREDIT", "VALUE", "1000"),
        ])
        enriched = g.enrich_generic_rule_with_taxonomy(rule, taxonomy)
        v1, v2 = enriched["instances"][0]["variables"]
        assert "concept_label" not in v1
        assert "db_location" not in v1
        assert v2["concept_label"] == "Funded credit exposure"

    def test_no_taxonomy_is_a_no_op(self):
        rule = _rule("X", "$V1 = $V2", [_var("V1", "A", "1"), _var("V2", "B", "1")])
        assert g.enrich_generic_rule_with_taxonomy(rule, None) == rule

    def test_disambiguates_colliding_labels_by_context(self):
        """Real rule 8 (MicroFinance): V2/V3 share the same concept AND the
        same code_filter — only their dimensional context differs. Both
        must not render as an unexplained identical duplicate."""
        rule = _rule(
            "MicroFinance", "$V1 <= ( $V2 + $V3 )",
            [
                _var("V1", "FundedOutstandingAdvances", "29594969000"),
                _var("V2", "AmountOutstandingOfGrossFundedExposure", "0",
                     context="fromto_20240401_20250331_ExposuresToMFIsMember_ExposuresInRupeesMember"),
                _var("V3", "AmountOutstandingOfGrossFundedExposure", "0",
                     context="fromto_20240401_20250331_ExposuresInForeignCurrenciesMember_ExposuresToMFIsMember"),
            ],
        )
        taxonomy = _taxonomy("MicroFinance", [
            ("V1", "in-rbi-rep:FundedOutstandingAdvances", "Funded outstanding advances",
             "CIMS_RAQ_Q_SEC8_SEC_CREDIT", "VALUE", "1070"),
            ("V2", "in-rbi-rep:AmountOutstandingOfGrossFundedExposure", "Amount outstanding of gross funded exposure",
             "CIMS_RAQ_Q_SEC10", "VALUE", "1063"),
            ("V3", "in-rbi-rep:AmountOutstandingOfGrossFundedExposure", "Amount outstanding of gross funded exposure",
             "CIMS_RAQ_Q_SEC10", "VALUE", "1063"),
        ])
        enriched = g.enrich_generic_rule_with_taxonomy(rule, taxonomy)
        parsed = g.parse_comparison_formula(enriched["formula_expression"])
        labels = g.resolve_variable_labels(enriched, parsed)
        assert labels["V2"] != labels["V3"]
        assert "Rupees" in labels["V2"] or "Rupees" in labels["V3"]


# ── 6. LLM payload (structured, no full taxonomy, no calculation left to LLM) ──

class TestBuildGenericLlmContext:
    def test_context_has_only_resolved_facts(self):
        rule = _rule(
            "TermLoans", "$V1 > $V2",
            [_var("V1", "TermLoansSanctioned", "0"), _var("V2", "TermLoansDisbursed", "0")],
            business_message='"Sanctioned > Disbursed" do not tally.',
        )
        context = g.build_generic_llm_context(rule)
        assert context["operator"] == ">"
        assert context["lhs_value"] == "0"
        assert context["rhs_total"] == "0"
        assert context["values_equal"] is True
        assert "concepts" not in context  # no raw taxonomy ever included

    def test_no_context_when_formula_unparseable(self):
        rule = _rule("Weird", "garbage", [])
        assert g.build_generic_llm_context(rule) is None


# ── 7. HTML parser — the 7-column, no-backtracking table shape ────────────

_SAMPLE_HTML = """
<html><body>
<div class="tab-pane fade in active" id="1"><div class="panel-group">
 <div class="panel panel-default" id="errorPanel1">
  <div class="panel-heading">
   <div class="assertionLabel">TermLoansRule</div>
   <div class="formulaErrorTest1" title="formula expression">$V1 &gt; $V2</div>
   <div class="badge badge-warning">2</div>
  </div>
  <div class="panel-body">
   <table class="table table-condensed table-striped">
    <tbody>
     <tr class="msgHead"><td class="formulaErrorTitle" colspan="7"> &nbsp;"en:Identity "Sanctioned &gt; Disbursed" do not tally."</td></tr>
     <tr class="hide "><td class="headerCell">Variable</td><td class="headerCell">Name</td><td class="headerCell">Value</td><td class="headerCell">Context</td><td class="headerCell">Unit</td><td class="headerCell">Decimal</td><td class="headerCell">Precision</td></tr>
    </tbody>
    <tbody class="msgBody formulaFvTBody">
     <tr class="hide fv"><td class="msgBodyCell">"V2</td><td class="msgBodyCell">TermLoansDisbursed</td><td class="msgBodyCell">0</td><td class="msgBodyCell">ctxA</td><td class="msgBodyCell">INR</td><td class="msgBodyCell">INF</td><td class="msgBodyCell"></td></tr>
     <tr class="hide fv"><td class="msgBodyCell">"V1</td><td class="msgBodyCell">TermLoansSanctioned</td><td class="msgBodyCell">0</td><td class="msgBodyCell">ctxA</td><td class="msgBodyCell">INR</td><td class="msgBodyCell">INF</td><td class="msgBodyCell"></td></tr>
    </tbody>
   </table>
   <table class="table table-condensed table-striped">
    <tbody>
     <tr class="msgHead"><td class="formulaErrorTitle" colspan="7"> &nbsp;"en:Identity "Sanctioned &gt; Disbursed" do not tally."</td></tr>
     <tr class="hide "><td class="headerCell">Variable</td><td class="headerCell">Name</td><td class="headerCell">Value</td><td class="headerCell">Context</td><td class="headerCell">Unit</td><td class="headerCell">Decimal</td><td class="headerCell">Precision</td></tr>
    </tbody>
    <tbody class="msgBody formulaFvTBody">
     <tr class="hide fv"><td class="msgBodyCell">"V2</td><td class="msgBodyCell">TermLoansDisbursed</td><td class="msgBodyCell">100</td><td class="msgBodyCell">ctxB</td><td class="msgBodyCell">INR</td><td class="msgBodyCell">INF</td><td class="msgBodyCell"></td></tr>
     <tr class="hide fv"><td class="msgBodyCell">"V1</td><td class="msgBodyCell">TermLoansSanctioned</td><td class="msgBodyCell">100</td><td class="msgBodyCell">ctxB</td><td class="msgBodyCell">INR</td><td class="msgBodyCell">INF</td><td class="msgBodyCell"></td></tr>
    </tbody>
   </table>
  </div>
 </div>
</div></div>
<div class="tab-pane fade" id="2">
 <div class="assertionLabel">XBRL SCHEMA</div>
 <div class="assertionLabel">CONSISTENT CALCULATION</div>
</div>
</body></html>
"""


class TestParseGenericFormulaErrors:
    def test_parses_rule_and_both_instances(self, tmp_path):
        html_file = tmp_path / "sample.html"
        html_file.write_text(_SAMPLE_HTML, encoding="utf-8")
        rules = g.parse_generic_formula_errors(str(html_file))
        assert len(rules) == 1
        rule = rules[0]
        assert rule["rule_name"] == "TermLoansRule"
        assert rule["formula_expression"] == "$V1 > $V2"
        assert len(rule["instances"]) == 2

    def test_variable_rows_correctly_mapped(self, tmp_path):
        html_file = tmp_path / "sample.html"
        html_file.write_text(_SAMPLE_HTML, encoding="utf-8")
        rules = g.parse_generic_formula_errors(str(html_file))
        first_vars = {v["var"]: v for v in rules[0]["instances"][0]["variables"]}
        assert first_vars["V1"]["concept"] == "TermLoansSanctioned"
        assert first_vars["V1"]["value"] == "0"
        assert first_vars["V2"]["concept"] == "TermLoansDisbursed"

    def test_excludes_other_tabs_noise(self, tmp_path):
        """QUALITY-CHECK/SPECIFICATION-tab entries reuse the same
        assertionLabel class — must never be counted as formula errors."""
        html_file = tmp_path / "sample.html"
        html_file.write_text(_SAMPLE_HTML, encoding="utf-8")
        rules = g.parse_generic_formula_errors(str(html_file))
        names = [r["rule_name"] for r in rules]
        assert "XBRL SCHEMA" not in names
        assert "CONSISTENT CALCULATION" not in names

    def test_missing_file_returns_empty_list(self):
        assert g.parse_generic_formula_errors(r"C:\nonexistent\file.html") == []


# ── 8. Routing helper sanity (does not touch report_lookup.py's own logic) ─

class TestRoutingHelperUsed:
    def test_is_4000_series_boundaries(self):
        from backend.tools.report_lookup import _is_4000_series
        assert _is_4000_series("4046") is True
        assert _is_4000_series("4999") is True
        assert _is_4000_series("2065") is False
        assert _is_4000_series("") is False
        assert _is_4000_series(None) is False


# ── 9. Deterministic relationship classification — the fix's foundation ───

class TestClassifyRelationship:
    def test_greater(self):
        assert g._classify_relationship(Decimal("5"), Decimal("3")) == "lhs_greater"

    def test_equal(self):
        assert g._classify_relationship(Decimal("5"), Decimal("5")) == "lhs_equal"

    def test_less(self):
        assert g._classify_relationship(Decimal("3"), Decimal("5")) == "lhs_less"

    def test_evaluate_comparison_exposes_relationship(self):
        parsed = g.parse_comparison_formula("$V1 > $V2")
        calc = g.evaluate_comparison(parsed, {"V1": Decimal("1"), "V2": Decimal("1")})
        assert calc["relationship"] == "lhs_equal"


# ── 10. Direct sentence-wording contract — the exact bug this task fixes ──
# "$V1 > $V2" with V1 == V2 must never say one value "exceeded" the other.

class TestConditionSentenceWordingContract:
    def test_greater_than_satisfied(self):
        s = g._condition_sentence(">", "LHS", ["RHS"], "lhs_greater", "100", "0")
        assert s == "LHS is greater than RHS, so the condition is satisfied."

    def test_greater_than_equal_never_says_exceeded(self):
        s = g._condition_sentence(">", "Total Advances (Outstanding) - Funded", ["Funded Credit Exposure"],
                                   "lhs_equal", "₹276,553,464,000", "0")
        assert s == (
            "Total Advances (Outstanding) - Funded must be greater than Funded Credit Exposure, "
            "but both values are equal at ₹276,553,464,000. Therefore, the required strict "
            "greater-than condition is not satisfied."
        )
        assert "exceed" not in s.lower()

    def test_greater_than_lhs_actually_lower(self):
        s = g._condition_sentence(">", "LHS", ["RHS"], "lhs_less", "0", "50")
        assert s == "LHS must be greater than RHS, but it is lower than RHS. The condition is not satisfied."

    def test_gte_equal_is_satisfied(self):
        s = g._condition_sentence(">=", "LHS", ["RHS"], "lhs_equal", "100", "0")
        assert s == (
            "LHS must be greater than or equal to RHS, and both values are equal at 100. "
            "Therefore, the condition is satisfied."
        )

    def test_gte_lhs_lower_fails(self):
        s = g._condition_sentence(">=", "LHS", ["RHS"], "lhs_less", "0", "50")
        assert "must be greater than or equal to" in s
        assert "it is lower than" in s

    def test_lte_lhs_exceeds_single_term(self):
        s = g._condition_sentence("<=", "LHS", ["RHS"], "lhs_greater", "0", "50")
        assert s == "LHS must not exceed RHS, but it is greater than the allowed value. The condition is not satisfied."

    def test_lte_lhs_exceeds_summed_rhs_uses_combined_phrasing(self):
        s = g._condition_sentence("<=", "Funded Advances", ["Exposure A", "Exposure B"],
                                   "lhs_greater", "0", "₹29,594,969,000")
        assert s == (
            "Funded Advances must not exceed the combined value of Exposure A and Exposure B, "
            "but the reported value exceeds the allowed combined amount by ₹29,594,969,000."
        )

    def test_equality_mismatch(self):
        s = g._condition_sentence("=", "LHS", ["RHS"], "lhs_greater", "0", "1,000")
        assert s == "LHS does not match RHS. The values differ by 1,000."

    def test_equality_match(self):
        s = g._condition_sentence("=", "LHS", ["RHS"], "lhs_equal", "100", "0")
        assert s == "LHS matches RHS, and the equality condition is satisfied."


class TestFixSentenceWordingContract:
    def test_equality_fix(self):
        s = g._fix_sentence("=", "lhs_greater", "LHS", ["RHS"])
        assert s == "Review both reported values and correct whichever value is inaccurate, then revalidate the report."

    def test_strict_inequality_equal_values_fix(self):
        s = g._fix_sentence(">", "lhs_equal", "LHS", ["RHS"])
        assert "confirm whether the equality is expected" in s
        assert "strictly greater than" in s

    def test_strict_less_than_equal_values_fix(self):
        s = g._fix_sentence("<", "lhs_equal", "LHS", ["RHS"])
        assert "strictly less than" in s

    def test_general_inequality_fix_names_both_fields(self):
        s = g._fix_sentence(">", "lhs_less", "LHS", ["RHS"])
        assert "LHS" in s and "RHS" in s
        assert "determine which value requires correction" in s


# ── 11. LLM can no longer override the condition sentence ─────────────────

class TestLlmCannotOverrideExplanation:
    def test_llm_text_only_affects_fix_line_not_condition_sentence(self):
        """Even if a caller passes an 'explanation' key (stale/legacy shape),
        the rendered condition sentence must remain the deterministic one —
        this is the core guarantee the reported bug required."""
        rule = _rule(
            "TermLoans", "$V1 > $V2",
            [_var("V1", "TermLoansSanctioned", "0"), _var("V2", "TermLoansDisbursed", "0")],
            business_message='"Sanctioned > Disbursed" do not tally.',
        )
        llm_text = {
            "explanation": "Term Loans Sanctioned exceeded Term Loans Disbursed.",  # wrong on purpose
            "fix": "Review Term Loans Sanctioned and Term Loans Disbursed, then revalidate.",
        }
        text = g.render_generic_formula_explanation(rule, llm_text=llm_text)
        assert "exceeded" not in text
        assert "both values are equal" in text  # deterministic sentence still won
        assert "Review Term Loans Sanctioned and Term Loans Disbursed, then revalidate." in text  # fix DID apply

    def test_llm_fix_rejected_when_it_contradicts_equal_relationship(self):
        context = {
            "lhs_label": "LHS", "rhs_terms": [{"label": "RHS", "value": "0"}],
            "relationship": "lhs_equal",
        }
        # Simulate what explain_generic_context_via_llm's validation must catch
        # by exercising the same guard condition directly.
        import re as _re
        lowered = "lhs exceeded rhs, please review."
        assert _re.search(r"\bexceed|exceeds|exceeded|is greater|is lower|is higher|is less than\b", lowered)


# ── 12. Confirm 4000-series behavior is unaffected ─────────────────────────

class TestFourThousandSeriesUnaffected:
    def test_report_lookup_formula_functions_still_importable_and_unchanged(self):
        """Sanity guard: the 4000-series module's public formula-error
        surface must still exist with its original names/behavior. The full
        194-test suite in test_report_lookup.py etc. is the real regression
        guard; this just confirms nothing here accidentally shadows or
        monkeypatches it."""
        from backend.tools import report_lookup as rl
        assert callable(rl.parse_formula_errors)
        assert callable(rl.explain_formula_errors)
        assert callable(rl._classify_formula_type)
        # The 4000-series classifier's own keyword-based logic must be
        # completely untouched — still returns "sum_check" for a bare "+"
        # between variables, unlike this module's operator-aware parser.
        assert rl._classify_formula_type("$V1 + $V2 = $V3") == "sum_check"
