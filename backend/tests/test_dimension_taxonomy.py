"""Tests for backend.tools.dimension_taxonomy — the taxonomy-aware
DIMENSION-error explainer, and its wiring into
report_lookup.explain_dimensional_errors.

Uses synthetic taxonomy JSON/XML fixtures (not the real D:\\Repo(new) data)
so these tests are portable and don't depend on an external drive — this
also proves the module makes no return-specific assumptions: the fixture
below uses made-up concept/dimension/member names ("Widget"/"Gadget"/...)
and the module still produces a correctly-worded, evidence-based
explanation, exactly as it does for the real RBI mpd03 concepts.

One additional test (TestRealRepoIntegration) runs the exact same pipeline
against the real repo data and is skipped automatically when that drive
isn't present (e.g. in CI), rather than failing.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import backend.tools.dimension_taxonomy as dt
import backend.tools.report_lookup as rl


_DEFINITION_XML_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
                xmlns:xlink="http://www.w3.org/1999/xlink"
                xmlns:xbrldt="http://xbrl.org/2005/xbrldt">
  <link:definitionLink xlink:type="extended" xlink:role="http://example.org/roles/WidgetTable">
    <link:loc xlink:type="locator" xlink:href="core.xsd#ex_AB1" xlink:label="loc_AB1" xlink:title="AB1" />
    <link:loc xlink:type="locator" xlink:href="core.xsd#ex_LI1" xlink:label="loc_LI1" xlink:title="LI1" />
    <link:loc xlink:type="locator" xlink:href="core.xsd#ex_WidgetCount" xlink:label="loc_WidgetCount" xlink:title="WidgetCount" />
    <link:definitionArc xlink:arcrole="http://xbrl.org/int/dim/arcrole/domain-member" xlink:from="loc_LI1" xlink:to="loc_WidgetCount" order="1" />
    <link:definitionArc xlink:arcrole="http://xbrl.org/int/dim/arcrole/domain-member" xlink:from="loc_AB1" xlink:to="loc_LI1" order="2" />
    <link:loc xlink:type="locator" xlink:href="core.xsd#ex_HY1" xlink:label="loc_HY1" xlink:title="HY1" />
    <link:definitionArc xlink:arcrole="http://xbrl.org/int/dim/arcrole/all" xlink:from="loc_AB1" xlink:to="loc_HY1"
                         order="1" xbrldt:closed="true" xbrldt:contextElement="segment" />
    <link:loc xlink:type="locator" xlink:href="core.xsd#ex_GadgetDimension" xlink:label="loc_GadgetDimension" xlink:title="GadgetDimension" />
    <link:loc xlink:type="locator" xlink:href="core.xsd#ex_GadgetDomain" xlink:label="loc_GadgetDomain" xlink:title="GadgetDomain" />
    <link:definitionArc xlink:arcrole="http://xbrl.org/int/dim/arcrole/dimension-domain" xlink:from="loc_GadgetDimension" xlink:to="loc_GadgetDomain" order="1" />
    <link:loc xlink:type="locator" xlink:href="core.xsd#ex_GadgetOne" xlink:label="loc_GadgetOne" xlink:title="GadgetOne" />
    <link:definitionArc xlink:arcrole="http://xbrl.org/int/dim/arcrole/domain-member" xlink:from="loc_GadgetDomain" xlink:to="loc_GadgetOne" order="1" />
    <link:loc xlink:type="locator" xlink:href="core.xsd#ex_GadgetTwo" xlink:label="loc_GadgetTwo" xlink:title="GadgetTwo" />
    <link:definitionArc xlink:arcrole="http://xbrl.org/int/dim/arcrole/domain-member" xlink:from="loc_GadgetDomain" xlink:to="loc_GadgetTwo" order="2" />
    <link:definitionArc xlink:arcrole="http://xbrl.org/int/dim/arcrole/hypercube-dimension" xlink:from="loc_HY1" xlink:to="loc_GadgetDimension" order="1" />
  </link:definitionLink>
</link:linkbase>
"""


def _write_synthetic_taxonomy(tmp_path, form_id: str, axis_is_typed: bool = False):
    """Creates tmp_path/Json/<form_id>/widget-entry-n_1.0.0.json and
    tmp_path/DataBase/<form_id>/Taxonomy/widget-definition.xml, mirroring the
    real repo's layout closely enough for the module's discovery logic to
    find both generically."""
    json_dir = tmp_path / "Json" / form_id
    json_dir.mkdir(parents=True)
    json_path = json_dir / "widget-entry-n_1.0.0.json"
    json_path.write_text(
        f"""{{
  "return_metadata": {{
    "entry_point_path": "D:\\\\Repo\\\\DataBase\\\\9999\\\\Taxonomy\\\\widget-n\\\\1.0.0\\\\widget-entry-n.xsd"
  }},
  "structure": {{
    "axes": [
      {{
        "axis_id": "ex:GadgetDimension",
        "is_typed": {str(axis_is_typed).lower()},
        "tables": ["http://example.org/roles-n/WidgetTable"]
      }}
    ]
  }},
  "concepts": []
}}""",
        encoding="utf-8",
    )

    xml_dir = tmp_path / "DataBase" / form_id / "Taxonomy"
    xml_dir.mkdir(parents=True)
    (xml_dir / "widget-definition.xml").write_text(_DEFINITION_XML_TEMPLATE, encoding="utf-8")

    return json_path


def _write_error_html(tmp_path, good_context: str, bad_context: str) -> str:
    html_path = tmp_path / "fake_BTDetails.html"
    html_path.write_text(
        f"""<html><body>
        <td class="directMsg"><b>3.1.1 [xbrldie:PrimaryItemDimensionallyInvalidError]</b> :
        Fact value reported for concept 'WidgetCount' for the context '{bad_context}' ...
        @name = WidgetCount @value = 42 @context = {bad_context} @unit = INR @decimal = 0 @precision =
        </td>
        <td class="longMsgBodyCell">{good_context}</td>
        </body></html>""",
        encoding="utf-8",
    )
    return str(html_path)


class TestBuildExplanationWithFullEvidence:
    def test_names_the_dimension_and_mentions_siblings(self, tmp_path, monkeypatch):
        _write_synthetic_taxonomy(tmp_path, "9999", axis_is_typed=False)
        html_path = _write_error_html(tmp_path, "asof_20250101_02", "asof_20250101_OOOOOOOO1")

        monkeypatch.setattr(dt.config, "_active_root", lambda: str(tmp_path))
        dt._find_definition_linkbases.cache_clear()

        err = {"concept": "WidgetCount", "context": "asof_20250101_OOOOOOOO1", "value": "42"}
        explanation, evidence = dt.build_explanation(err, "9999", html_path)

        assert explanation is not None
        assert "gadget" in explanation.lower()
        assert "OOOOOOOO1" in explanation
        assert "**Reported value/member:** `OOOOOOOO1`" in explanation
        assert "**Concept:** WidgetCount" in explanation
        assert evidence["hypercube_found"] is True
        assert evidence["axis_hint_found"] is True
        assert evidence["sibling_contexts_found"] == 1

    def test_prefers_json_axis_over_stale_xml_dimension_name(self, tmp_path, monkeypatch):
        """When the JSON confirms the axis is typed, the module must not
        present the XML's (possibly older-version) explicit member names as
        if they were the current valid values — it should still name the
        dimension (from the JSON), just without claiming a fixed member list."""
        _write_synthetic_taxonomy(tmp_path, "9999", axis_is_typed=True)
        html_path = _write_error_html(tmp_path, "asof_20250101_02", "asof_20250101_OOOOOOOO1")

        monkeypatch.setattr(dt.config, "_active_root", lambda: str(tmp_path))
        dt._find_definition_linkbases.cache_clear()

        err = {"concept": "WidgetCount", "context": "asof_20250101_OOOOOOOO1", "value": "42"}
        explanation, evidence = dt.build_explanation(err, "9999", html_path)

        assert evidence["axis_is_typed"] is True
        assert "gadget" in explanation.lower()
        assert "GadgetOne" not in explanation and "GadgetTwo" not in explanation


class TestGracefulFallback:
    def test_no_form_id_falls_back_generic(self, tmp_path):
        err = {"concept": "WidgetCount", "context": "asof_20250101_OOOOOOOO1", "value": "42"}
        explanation, evidence = dt.build_explanation(err, "", "")
        assert explanation is None  # build_explanation itself reports "no evidence"
        result = dt.explain_dimensional_errors_taxonomy_aware([err], form_id="", error_file_path="")
        assert "do not provide enough detail" in result[0]["explanation"]
        assert "**Reported value/member:** `42`" in result[0]["explanation"]
        assert "Cannot be determined from the available data." in result[0]["explanation"]

    def test_unknown_form_id_does_not_crash(self, tmp_path, monkeypatch):
        monkeypatch.setattr(dt.config, "_active_root", lambda: str(tmp_path))
        dt._find_definition_linkbases.cache_clear()
        err = {"concept": "WidgetCount", "context": "asof_20250101_OOOOOOOO1", "value": "42"}
        result = dt.explain_dimensional_errors_taxonomy_aware(
            [err], form_id="does-not-exist", error_file_path="",
        )
        assert result[0]["explanation"].startswith("**Dimension Error:**")

    def test_malformed_definition_xml_does_not_crash(self, tmp_path, monkeypatch):
        json_path = _write_synthetic_taxonomy(tmp_path, "9999")
        (tmp_path / "DataBase" / "9999" / "Taxonomy" / "widget-definition.xml").write_text(
            "<not-well-formed-xml", encoding="utf-8",
        )
        monkeypatch.setattr(dt.config, "_active_root", lambda: str(tmp_path))
        dt._find_definition_linkbases.cache_clear()

        err = {"concept": "WidgetCount", "context": "asof_20250101_OOOOOOOO1", "value": "42"}
        result = dt.explain_dimensional_errors_taxonomy_aware([err], form_id="9999", error_file_path="")
        assert result[0]["explanation"].startswith("**Dimension Error:**")

    def test_missing_error_file_does_not_crash(self, tmp_path, monkeypatch):
        _write_synthetic_taxonomy(tmp_path, "9999")
        monkeypatch.setattr(dt.config, "_active_root", lambda: str(tmp_path))
        dt._find_definition_linkbases.cache_clear()

        err = {"concept": "WidgetCount", "context": "asof_20250101_OOOOOOOO1", "value": "42"}
        result = dt.explain_dimensional_errors_taxonomy_aware(
            [err], form_id="9999", error_file_path=str(tmp_path / "does_not_exist.html"),
        )
        assert result[0]["explanation"].startswith("**Dimension Error:**")

    def test_empty_errors_list_returns_empty(self):
        assert dt.explain_dimensional_errors_taxonomy_aware([], form_id="9999") == []


class TestReportLookupWiring:
    def test_explain_dimensional_errors_default_signature_still_works(self):
        """Existing/older callers passing only `errors` (no form_id/
        error_file_path) must still work — same backward-compatible
        contract as before this change."""
        errors = [{"concept": "X", "context": "asof_20250101_OOOOOOOO1", "value": "1"}]
        result = rl.explain_dimensional_errors(errors)
        assert len(result) == 1
        assert result[0]["explanation"].startswith("**Dimension Error:**")

    def test_explain_dimensional_errors_forwards_to_taxonomy_module(self, tmp_path, monkeypatch):
        _write_synthetic_taxonomy(tmp_path, "9999", axis_is_typed=False)
        html_path = _write_error_html(tmp_path, "asof_20250101_02", "asof_20250101_OOOOOOOO1")
        monkeypatch.setattr(dt.config, "_active_root", lambda: str(tmp_path))
        dt._find_definition_linkbases.cache_clear()

        errors = [{"concept": "WidgetCount", "context": "asof_20250101_OOOOOOOO1", "value": "42"}]
        result = rl.explain_dimensional_errors(errors, form_id="9999", error_file_path=html_path)
        assert "gadget" in result[0]["explanation"].lower()


_MULTI_DIM_DEFINITION_XML = """<?xml version="1.0" encoding="utf-8"?>
<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
                xmlns:xlink="http://www.w3.org/1999/xlink"
                xmlns:xbrldt="http://xbrl.org/2005/xbrldt">
  <link:definitionLink xlink:type="extended" xlink:role="http://example.org/roles/SprocketTable">
    <link:loc xlink:type="locator" xlink:href="core.xsd#ex_AB1" xlink:label="loc_AB1" xlink:title="AB1" />
    <link:loc xlink:type="locator" xlink:href="core.xsd#ex_LI1" xlink:label="loc_LI1" xlink:title="LI1" />
    <link:loc xlink:type="locator" xlink:href="core.xsd#ex_SprocketCount" xlink:label="loc_SprocketCount" xlink:title="SprocketCount" />
    <link:definitionArc xlink:arcrole="http://xbrl.org/int/dim/arcrole/domain-member" xlink:from="loc_LI1" xlink:to="loc_SprocketCount" order="1" />
    <link:definitionArc xlink:arcrole="http://xbrl.org/int/dim/arcrole/domain-member" xlink:from="loc_AB1" xlink:to="loc_LI1" order="2" />
    <link:loc xlink:type="locator" xlink:href="core.xsd#ex_HY2" xlink:label="loc_HY2" xlink:title="HY2" />
    <link:definitionArc xlink:arcrole="http://xbrl.org/int/dim/arcrole/all" xlink:from="loc_AB1" xlink:to="loc_HY2"
                         order="1" xbrldt:closed="true" xbrldt:contextElement="segment" />
    <link:loc xlink:type="locator" xlink:href="core.xsd#ex_GizmoAxis" xlink:label="loc_GizmoAxis" xlink:title="GizmoAxis" />
    <link:definitionArc xlink:arcrole="http://xbrl.org/int/dim/arcrole/hypercube-dimension" xlink:from="loc_HY2" xlink:to="loc_GizmoAxis" order="1" />
    <link:loc xlink:type="locator" xlink:href="core.xsd#ex_CogAxis" xlink:label="loc_CogAxis" xlink:title="CogAxis" />
    <link:definitionArc xlink:arcrole="http://xbrl.org/int/dim/arcrole/hypercube-dimension" xlink:from="loc_HY2" xlink:to="loc_CogAxis" order="2" />
  </link:definitionLink>
</link:linkbase>
"""


class TestMultiDimensionHypercube:
    """A concept requiring SEVERAL axes together (like fmrd10's
    CommodityQuantity, which needs three) must name all of them, not just
    the first one found."""

    def test_names_all_required_dimensions_together(self, tmp_path, monkeypatch):
        xml_dir = tmp_path / "DataBase" / "8888" / "Taxonomy"
        xml_dir.mkdir(parents=True)
        (xml_dir / "sprocket-definition.xml").write_text(_MULTI_DIM_DEFINITION_XML, encoding="utf-8")
        html_path = tmp_path / "fake_BTDetails.html"
        html_path.write_text(
            "<html><body><td class='directMsg'>no siblings here</td></body></html>",
            encoding="utf-8",
        )
        monkeypatch.setattr(dt.config, "_active_root", lambda: str(tmp_path))
        dt._find_definition_linkbases.cache_clear()

        err = {
            "concept": "SprocketCount",
            "context": "fromto_20220101_20220331_SomeMember",
            "value": "7",
        }
        explanation, evidence = dt.build_explanation(
            err, "", str(html_path),
        )
        # No JSON exists for form "" — the file-derived stem path won't find
        # anything either since the html has no taxonomy filename hints, so
        # exercise the lookup directly via the stems list instead:
        hc = dt._find_hypercube_for_concept(["sprocket"], "SprocketCount")
        assert hc is not None
        assert set(hc["dimensions"].keys()) == {"GizmoAxis", "CogAxis"}


class TestIllegalTypedDimensionContent:
    def test_uses_validator_fields_directly_no_taxonomy_lookup_needed(self):
        err = {
            "error_class": "xbrldie:IllegalTypedDimensionContentError",
            "dimension": "DateAxis",
            "typed_dim_value": "not-a-real-date",
            "context": "asof_20220331_not-a-real-date",
            "value": "",
        }
        explanation, evidence = dt.build_explanation(err, form_id="", error_file_path="")
        assert explanation is not None
        assert "date" in explanation.lower()
        assert "not-a-real-date" in explanation
        assert evidence["source"] == "validator_message_direct"

    def test_missing_dimension_field_falls_back_generic(self):
        err = {
            "error_class": "xbrldie:IllegalTypedDimensionContentError",
            "dimension": "",
            "typed_dim_value": "",
            "context": "asof_20220331_x",
            "value": "",
        }
        explanation, evidence = dt.build_explanation(err, form_id="", error_file_path="")
        assert explanation is None


class TestSiblingSafety:
    """Regression coverage for two real-world false-positive risks found
    while testing against an actual fmrd10 filing: (1) a context with no
    recognized placeholder suffix must not have an arbitrary trailing
    segment stripped off and treated as a safe prefix, and (2) a "sibling"
    context that is itself one of the other errors in this same file must
    not be counted as proof a valid context exists."""

    def test_no_placeholder_suffix_yields_no_siblings(self, tmp_path):
        html_path = tmp_path / "f.html"
        html_path.write_text(
            "<html>fromto_20220101_20220331_SomeExposureMember and "
            "fromto_20220101_20220331_OtherExposureMember</html>",
            encoding="utf-8",
        )
        siblings = dt._find_sibling_contexts(
            str(html_path), "fromto_20220101_20220331_SomeExposureMember",
        )
        assert siblings == []

    def test_sibling_that_is_itself_a_known_error_context_is_excluded(self, tmp_path):
        html_path = tmp_path / "f.html"
        html_path.write_text(
            "<html>fromto_20220101_20220331_ExposureMember_OOOOOOOO1 and "
            "fromto_20220101_20220331_ExposureMember</html>",
            encoding="utf-8",
        )
        known_invalid = frozenset({"fromto_20220101_20220331_ExposureMember"})
        siblings = dt._find_sibling_contexts(
            str(html_path),
            "fromto_20220101_20220331_ExposureMember_OOOOOOOO1",
            known_invalid,
        )
        assert siblings == []


_REAL_REPO_ROOT = r"D:\Repo(new)"
_REAL_BTDETAILS = (
    r"D:\Repo(new)\Instance\4046\IDIB250515R41915H_19-06-26_04-23-57_BTDetails (5).html"
)
_REAL_FMRD10_HTML = (
    r"D:\Repo(new)\Instance\4012\ABPL220331R19704Q_11-06-26_03-30-51_Instance.html"
)


@pytest.mark.skipif(
    not os.path.isfile(_REAL_BTDETAILS),
    reason="real repo data (D:\\Repo(new)) not present in this environment",
)
class TestRealRepoIntegration:
    def test_real_mpd03_dimension_errors_are_explained_with_the_real_axis(self):
        from backend.tools.report_lookup import parse_dimensional_html_errors

        errors = parse_dimensional_html_errors(_REAL_BTDETAILS)
        assert len(errors) == 4

        explained = rl.explain_dimensional_errors(
            errors, form_id="4046", error_file_path=_REAL_BTDETAILS,
        )
        assert len(explained) == 4
        for err in explained:
            explanation = err["explanation"]
            suffix = err["context"].rsplit("_", 1)[-1]
            assert explanation.startswith("**Dimension Error:**")
            assert "date of transaction" in explanation.lower()
            assert "**Dimension type:** Typed dimension" in explanation
            assert suffix in explanation  # the reported dimension value itself
            # Never invents a single expected value for a typed dimension —
            # only the real sibling-fact evidence found in this same filing.
            assert "Cannot be determined from the available data." in explanation
            ev = err["_dimension_evidence"]
            assert ev["hypercube_found"] is True
            assert ev["axis_id"] == "in-rbi-rep:DateOfTransactionAxis"
            assert ev["dimension_is_typed"] is True
            # 14 valid same-filing examples were found for this typed axis
            # (see the FORMULA panel's daily CRR variable rows) — the
            # explanation must surface some of them, not just a vague
            # "other facts use a properly formed context" sentence.
            assert ev.get("typed_value_examples")
            assert any(ex in explanation for ex in ev["typed_value_examples"])


@pytest.mark.skipif(
    not os.path.isfile(_REAL_FMRD10_HTML),
    reason="real repo data (D:\\Repo(new)) not present in this environment",
)
class TestRealRepoIntegrationFmrd10:
    """A second, structurally different real filing: form_id '4012' has no
    Json/ extract, so the concept-> hypercube lookup relies entirely on
    _find_hypercube_for_concept locating DataBase/4012/Taxonomy/reports/
    fmrd10/1.0.0/fmrd10-definition.xml directly (its own form-specific
    taxonomy folder). This exercises multi-dimension hypercubes and the
    IllegalTypedDimensionContentError path against real data."""

    def test_mixed_error_classes_and_multi_dimension_concepts(self):
        from backend.tools.report_lookup import parse_dimensional_html_errors

        errors = parse_dimensional_html_errors(_REAL_FMRD10_HTML)
        assert len(errors) == 13

        explained = rl.explain_dimensional_errors(
            errors, form_id="4012", error_file_path=_REAL_FMRD10_HTML,
        )
        assert len(explained) == 13

        typed_content = [e for e in explained if "IllegalTypedDimensionContentError" in e["error_class"]]
        assert len(typed_content) == 1
        assert "date" in typed_content[0]["explanation"].lower()
        assert typed_content[0]["_dimension_evidence"]["source"] == "validator_message_direct"

        primary_item = [e for e in explained if "PrimaryItemDimensionallyInvalidError" in e["error_class"]]
        assert len(primary_item) == 12
        for e in primary_item:
            ev = e["_dimension_evidence"]
            assert ev["hypercube_found"] is True, e["concept"]
            assert "fmrd10" in ev["hypercube_source_file"].lower()
            # Multi-axis concepts (CommodityQuantity/CommodityHedgesBookedQuantity)
            # must name every required axis, not just the first.
            if e["concept"] in ("CommodityQuantity", "CommodityHedgesBookedQuantity"):
                assert len(ev["hypercube_dimensions"]) >= 3
                assert " and " in e["explanation"] or ", and " in e["explanation"]

        # The no-placeholder-suffix GrossOutflow context must not claim
        # sibling evidence it can't actually prove (see TestSiblingSafety).
        no_suffix_gross_outflow = next(
            e for e in primary_item
            if e["concept"] == "GrossOutflow"
            and e["context"] == "fromto_20220101_20220331_FluctuationOfPriceAndFreightRiskMember"
        )
        assert no_suffix_gross_outflow["_dimension_evidence"]["sibling_contexts_found"] == 0
        assert "Other facts" not in no_suffix_gross_outflow["explanation"]
