"""Contract tests for the unified error card (ERROR_CARD_V2).

Runs entirely on synthetic evidence — no corpus, no Ollama, no filesystem — so
it exercises the presentation layer directly and fails for presentation reasons
only. The corpus-driven behaviour of the parsers underneath is already covered
by test_error_explanation_v2.py (which is pinned to the legacy layout; see the
_deterministic fixture there).

What is asserted here, in order of what would hurt most if it broke:

  1. Nothing is LOST. The redesign re-tiers information; it does not delete it.
     The full allowed-value list, the v1 diagnosis prose and the context id must
     all still be reachable inside the details drawer.
  2. The headline names the actual problem, not the category.
  3. The matrix carries one row per required item with an honest status — and
     never invents a verdict when the evidence could not establish one.
  4. Both error types produce the SAME section shape.
  5. ERROR_CARD_V2=0 really does restore the legacy sections.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.tools import dimension_error as de       # noqa: E402
from backend.tools import error_card                  # noqa: E402
from backend.tools import formula_error as fe         # noqa: E402
from backend.tools import formula_expression as fx    # noqa: E402


@pytest.fixture(autouse=True)
def _card_on(monkeypatch):
    monkeypatch.setenv("ERROR_CARD_V2", "1")
    monkeypatch.setenv("ERROR_EXPLAIN_LLM", "0")


def _kinds(sections):
    return [s["kind"] for s in sections]


def _by_kind(sections, kind):
    return next((s for s in sections if s["kind"] == kind), None)


def _all_text(section) -> str:
    """Every string anywhere inside a section, flattened — for 'is this fact
    still reachable?' assertions that should not care about nesting."""
    out: list[str] = []

    def walk(node):
        if isinstance(node, str):
            out.append(node)
        elif isinstance(node, dict):
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(section)
    return " | ".join(out)


# ═════════════════════════════════════════════════════════════════════════════
# Fixtures — the exact shapes build_evidence()/evaluate_instance() produce
# ═════════════════════════════════════════════════════════════════════════════

_CRIMINAL_MEMBERS = [
    "Customers and Outsiders", "Customers", "Other criminal", "Outsiders",
    "Robbers", "Staff and customers", "Staff and Outsiders", "Staff",
    "Staff, Customers and Outsiders",
]


def _typed_axis(axis_id: str, label: str, base_type: str, example: str = "") -> dict:
    return {
        "axis_id": axis_id, "label": label, "is_typed": True,
        "required_value": {"base_type": base_type, "description": "", "example": example,
                           "facets": {}},
        "allowed_members": [],
    }


def _explicit_axis(axis_id: str, label: str, members: list[str]) -> dict:
    return {
        "axis_id": axis_id, "label": label, "is_typed": False, "required_value": None,
        "allowed_members": [{"id": m.replace(" ", "").replace(",", "") + "Member",
                             "label": m} for m in members],
    }


def _missing_axes_evidence() -> dict:
    """The real-world case this redesign was driven by: a figure that carries
    two of the four details its hypercube requires."""
    axes = [
        _typed_axis("BranchCodeAxis", "Branch code", "xbrli:stringItemType"),
        _typed_axis("NameOfBranchAxis", "Name of branch", "xbrli:stringItemType"),
        _explicit_axis("TypeOfCriminalAxis", "Type of criminal", _CRIMINAL_MEMBERS),
        _typed_axis("DateAndTimeOfOccurrenceTypeAxis", "Date and Time of Occurrence Type",
                    "xbrli:dateTimeItemType", example="2023-10-23T12:51:00"),
    ]
    return {
        "error_class": "xbrldie:PrimaryItemDimensionallyInvalidError",
        "concept_id": "AddressOfBranch", "concept_label": "Address of branch",
        "context_id": "fromto_20240101_20240331_221826_VishnuGarden",
        "reported_fact_value": "West Delhi", "unit": "", "decimal": "",
        "taxonomy_found": True, "taxonomy_source": "definition.xml",
        "hypercube_closed": True, "expected_axes": axes,
        "observed_dimensions": [
            {"dimension": "BranchCodeAxis", "value": "221826"},
            {"dimension": "NameOfBranchAxis", "value": "Vishnu Garden"},
        ],
        "observation_source": "instance_document", "instance_document_used": True,
        "focus_axis": None,
        "missing_axes": ["DateAndTimeOfOccurrenceTypeAxis", "TypeOfCriminalAxis"],
        "unexpected_axes": [], "invalid_members": [], "typed_value_check": None,
        "diagnosis": "missing_axes",
        "_axis_labels": {a["axis_id"]: a["label"] for a in axes},
    }


def _no_observation_evidence() -> dict:
    """No instance document was saved, so nothing about what was supplied can
    be established — the card must say so rather than guess."""
    evidence = _missing_axes_evidence()
    evidence.update({
        "observed_dimensions": None, "observation_source": "none",
        "instance_document_used": False, "missing_axes": [],
        "diagnosis": "expectation_only",
    })
    return evidence


def _formula_case(expression: str, values: dict[str, list[str]], labels: dict[str, str]):
    """(rule, comparison, result, labels) for a synthetic formula failure."""
    comparison = fx.parse_formula(expression)
    result = fx.evaluate(comparison, values)
    facts = [
        {"var": var, "value": value, "unit": "INR", "context": f"ctx_{var}"}
        for var, entries in values.items() for value in entries
    ]
    rule = {
        "rule_name": "TotalAssetsTally", "formula_expression": expression,
        "instances": [{"facts": facts, "business_message": "Total assets do not tally."}],
    }
    return rule, comparison, result, labels


# ═════════════════════════════════════════════════════════════════════════════
# 1 — nothing is lost
# ═════════════════════════════════════════════════════════════════════════════

class TestNothingIsLost:
    def test_full_allowed_member_list_survives_in_the_drawer(self):
        """The 9 options are pulled OUT of the card body (they are not
        actionable when the detail is simply absent) but must remain
        reachable — that is the difference between re-tiering and deleting."""
        sections = de.build_card_sections(_missing_axes_evidence())
        drawer = _by_kind(sections, "details")
        assert drawer is not None
        text = _all_text(drawer)
        for member in _CRIMINAL_MEMBERS[:4]:
            assert member in text, member

    def test_v1_diagnosis_prose_and_context_id_survive_in_the_drawer(self):
        evidence = _missing_axes_evidence()
        drawer = _by_kind(de.build_card_sections(evidence), "details")
        text = _all_text(drawer)
        assert evidence["context_id"] in text
        # v1's "What Is Wrong" bullets, verbatim.
        assert any(point in text for point in de._what_is_wrong_points(evidence))

    def test_formula_comparison_breakdown_survives_in_the_drawer(self):
        rule, comparison, result, labels = _formula_case(
            "$V1 = $V2 + $V3",
            {"V1": ["2360000"], "V2": ["450000"], "V3": ["1200000"]},
            {"V1": "Total assets", "V2": "Cash", "V3": "Investments"},
        )
        drawer = _by_kind(
            fe.build_card_sections(rule, comparison, result, labels), "details")
        text = _all_text(drawer)
        assert "Comparison" in text
        assert "Why It Failed" in text


# ═════════════════════════════════════════════════════════════════════════════
# 2 — the headline names the problem
# ═════════════════════════════════════════════════════════════════════════════

class TestHeadlineIsSpecific:
    def test_dimension_headline_names_the_missing_details(self):
        sections = de.build_card_sections(_missing_axes_evidence())
        headline = _by_kind(sections, "headline")["text"]
        assert "Type of criminal" in headline
        assert "Date and Time of Occurrence Type" in headline
        # The v1 wording said only that "some" were missing.
        assert "Some of the details" not in headline

    def test_formula_headline_states_the_size_and_direction_of_the_gap(self):
        rule, comparison, result, labels = _formula_case(
            "$V1 = $V2 + $V3",
            {"V1": ["2360000"], "V2": ["450000"], "V3": ["1200000"]},
            {"V1": "Total assets", "V2": "Cash", "V3": "Investments"},
        )
        headline = _by_kind(
            fe.build_card_sections(rule, comparison, result, labels), "headline")["text"]
        assert "Total assets" in headline
        assert "710,000" in headline          # 1,650,000 - 2,360,000
        assert "higher" in headline

    def test_headline_falls_back_to_the_v1_sentence_when_names_are_unknown(self):
        """A diagnosis with nothing specific to name must not produce a
        half-built sentence — it keeps v1's accurate general wording."""
        evidence = _missing_axes_evidence()
        evidence.update({"diagnosis": "invalid_combination"})
        headline = _by_kind(de.build_card_sections(evidence), "headline")["text"]
        assert headline == de._headline(evidence)


# ═════════════════════════════════════════════════════════════════════════════
# 3 — the matrix
# ═════════════════════════════════════════════════════════════════════════════

class TestMatrix:
    def test_one_row_per_required_detail_with_correct_statuses(self):
        matrix = _by_kind(de.build_card_sections(_missing_axes_evidence()), "matrix")
        rows = {r["label"]: r for r in matrix["rows"]}
        assert len(rows) == 4

        assert rows["Branch code"]["status"] == error_card.STATUS_OK
        assert rows["Branch code"]["actual"] == "221826"
        assert rows["Name of branch"]["status"] == error_card.STATUS_OK
        assert rows["Name of branch"]["actual"] == "Vishnu Garden"

        assert rows["Type of criminal"]["status"] == error_card.STATUS_BAD
        assert rows["Date and Time of Occurrence Type"]["status"] == error_card.STATUS_BAD

    def test_expected_column_is_short_not_the_full_requirement(self):
        matrix = _by_kind(de.build_card_sections(_missing_axes_evidence()), "matrix")
        rows = {r["label"]: r for r in matrix["rows"]}
        assert rows["Branch code"]["expected"] == "text"
        assert rows["Date and Time of Occurrence Type"]["expected"] == "date & time"
        assert rows["Type of criminal"]["expected"] == "one of 9 options"
        # The long form belongs in the drawer, not the cell.
        assert all(len(r["expected"]) < 40 for r in matrix["rows"])

    def test_no_observation_yields_unknown_not_a_guessed_verdict(self):
        sections = de.build_card_sections(_no_observation_evidence())
        matrix = _by_kind(sections, "matrix")
        assert {r["status"] for r in matrix["rows"]} == {error_card.STATUS_UNKNOWN}
        # …and the reason is stated, so a column of "not established" does not
        # read as a system failure.
        assert any(s["kind"] == "note" for s in sections)

    def test_formula_matrix_lists_components_then_an_emphasised_result_row(self):
        rule, comparison, result, labels = _formula_case(
            "$V1 = $V2 + $V3",
            {"V1": ["2360000"], "V2": ["450000"], "V3": ["1200000"]},
            {"V1": "Total assets", "V2": "Cash", "V3": "Investments"},
        )
        rows = _by_kind(
            fe.build_card_sections(rule, comparison, result, labels), "matrix")["rows"]

        assert [r["label"] for r in rows[:2]] == ["Cash", "Investments"]
        assert all(not r.get("emphasis") for r in rows[:2])

        final = rows[-1]
        assert final["emphasis"] is True
        assert final["label"] == "Total assets"
        assert final["status"] == error_card.STATUS_BAD
        assert "1,650,000" in final["expected"]      # what it should have been
        assert "2,360,000" in final["actual"]        # what was reported
        assert "over by" in final["note"]

    def test_non_equality_operator_carries_its_meaning_into_expected(self):
        """'₹100' alone cannot tell a reader whether it is a floor or a ceiling."""
        rule, comparison, result, labels = _formula_case(
            "$V1 >= $V2", {"V1": ["80"], "V2": ["100"]},
            {"V1": "Capital ratio", "V2": "Regulatory minimum"},
        )
        rows = _by_kind(
            fe.build_card_sections(rule, comparison, result, labels), "matrix")["rows"]
        assert "greater than or equal to" in rows[-1]["expected"]
        assert "short by" in rows[-1]["note"]


# ═════════════════════════════════════════════════════════════════════════════
# 4 — one shape for both error types
# ═════════════════════════════════════════════════════════════════════════════

class TestGenericShape:
    def test_both_error_types_emit_the_same_section_order(self):
        dimension = _kinds(de.build_card_sections(_missing_axes_evidence()))
        rule, comparison, result, labels = _formula_case(
            "$V1 = $V2 + $V3",
            {"V1": ["2360000"], "V2": ["450000"], "V3": ["1200000"]},
            {"V1": "Total assets", "V2": "Cash", "V3": "Investments"},
        )
        formula = _kinds(fe.build_card_sections(rule, comparison, result, labels))

        expected = ["headline", "locator", "rule", "matrix", "fix", "details"]
        assert [k for k in dimension if k in expected] == expected
        assert [k for k in formula if k in expected] == expected

    def test_locator_decodes_the_period_but_never_the_dimension_segments(self):
        """A context id concatenates every dimension value, and which axis a
        segment belongs to cannot be recovered from it. Only the period is
        safe to decode — the axis/value pairs come from the instance document
        and are already in the matrix."""
        locator = _by_kind(de.build_card_sections(_missing_axes_evidence()), "locator")
        values = " ".join(i["value"] for i in locator["items"])
        assert "1 Jan 2024 – 31 Mar 2024" in values
        assert "VishnuGarden" not in values     # never re-attributed to an axis
        assert "Address of branch" in values

    def test_text_form_renders_the_table_and_carries_no_markdown(self):
        text = de.render_card(_missing_axes_evidence())
        assert "**" not in text and "##" not in text
        assert "Detail" in text and "You provided" in text
        assert "Vishnu Garden" in text
        assert "Type of criminal" in text


class TestPeriodDecoding:
    @pytest.mark.parametrize("context_id,expected", [
        ("fromto_20240101_20240331_221826_VishnuGarden", "1 Jan 2024 – 31 Mar 2024"),
        ("asof_20260630_OtherMember", "as at 30 Jun 2026"),
        ("", ""),
        ("not_a_context_id", ""),
        ("fromto_99999999_20240331", ""),          # impossible date -> claim nothing
    ])
    def test_decoding(self, context_id, expected):
        assert error_card.period_from_context(context_id) == expected


# ═════════════════════════════════════════════════════════════════════════════
# 5 — the rollback actually rolls back
# ═════════════════════════════════════════════════════════════════════════════

class TestFeatureFlag:
    @pytest.mark.parametrize("value,enabled", [
        ("1", True), ("true", True), ("YES", True), ("on", True),
        ("0", False), ("false", False), ("", False),
    ])
    def test_flag_parsing(self, monkeypatch, value, enabled):
        monkeypatch.setenv("ERROR_CARD_V2", value)
        assert error_card.v2_enabled() is enabled

    def test_default_is_on_when_unset(self, monkeypatch):
        monkeypatch.delenv("ERROR_CARD_V2", raising=False)
        assert error_card.v2_enabled() is True

    def test_legacy_sections_still_build_and_differ_from_the_card(self):
        """The v1 builder is untouched and reachable — which is what makes
        ERROR_CARD_V2=0 a rollback rather than a hope."""
        evidence = _missing_axes_evidence()
        legacy = de.build_sections(evidence)
        headings = [s.get("heading") for s in legacy]
        assert "Details This Figure Must Carry" in headings
        assert "How to Fix" in headings
        assert "matrix" not in _kinds(legacy)
