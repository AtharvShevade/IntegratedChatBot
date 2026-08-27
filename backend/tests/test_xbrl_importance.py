# Tests for xbrl_importance — the regulatory-importance view of a comparison.
#
# The fixture below is a miniature but structurally REAL taxonomy: a role
# schema with [NNNN] sections, a presentation linkbase mapping concepts into
# them, a reference linkbase carrying a circular, and two formula linkbases —
# one blocking, one named as warnings. Every signal the scorer reads is present,
# so these tests exercise the actual parsers rather than a mocked index.

from __future__ import annotations

import os
import textwrap

import pytest

from backend.tools import xbrl_comparator as xc
from backend.tools.xbrl_importance import (
    ImportanceIndex,
    format_importance_report,
    group_by_importance,
)

NS_ROLE = "http://example.org/rbi/test"

ROLE_XSD = f"""<?xml version="1.0" encoding="utf-8"?>
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:link="http://www.xbrl.org/2003/linkbase">
  <xsd:annotation><xsd:appinfo>
    <link:roleType roleURI="{NS_ROLE}/RiskAssets" id="RiskAssets">
      <link:definition>[1900] Classification of risk assets</link:definition>
      <link:usedOn>link:presentationLink</link:usedOn>
    </link:roleType>
    <link:roleType roleURI="{NS_ROLE}/GeneralInfo" id="GeneralInfo">
      <link:definition>[1000] General information about reporting institution</link:definition>
      <link:usedOn>link:presentationLink</link:usedOn>
    </link:roleType>
    <link:roleType roleURI="{NS_ROLE}/GoldLoans" id="GoldLoans">
      <link:definition>[3800] Table 1 - Data on gold loans</link:definition>
      <link:usedOn>link:presentationLink</link:usedOn>
    </link:roleType>
    <link:roleType roleURI="{NS_ROLE}/Layout" id="Layout">
      <link:definition>Layout only - no section code</link:definition>
      <link:usedOn>link:presentationLink</link:usedOn>
    </link:roleType>
  </xsd:appinfo></xsd:annotation>
</xsd:schema>
"""

PRESENTATION_XML = f"""<?xml version="1.0" encoding="utf-8"?>
<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
               xmlns:xlink="http://www.w3.org/1999/xlink">
  <link:presentationLink xlink:type="extended" xlink:role="{NS_ROLE}/RiskAssets">
    <link:loc xlink:type="locator" xlink:href="core.xsd#in-rbi-rep_GrossNPAs"
              xlink:label="in-rbi-rep_GrossNPAs"/>
    <link:loc xlink:type="locator" xlink:href="core.xsd#in-rbi-rep_ProvisionHeld"
              xlink:label="in-rbi-rep_ProvisionHeld"/>
  </link:presentationLink>
  <link:presentationLink xlink:type="extended" xlink:role="{NS_ROLE}/GeneralInfo">
    <link:loc xlink:type="locator" xlink:href="core.xsd#in-rbi-rep_BranchCount"
              xlink:label="in-rbi-rep_BranchCount"/>
    <link:loc xlink:type="locator" xlink:href="core.xsd#in-rbi-rep_OfficeArea"
              xlink:label="in-rbi-rep_OfficeArea"/>
  </link:presentationLink>
  <link:presentationLink xlink:type="extended" xlink:role="{NS_ROLE}/GoldLoans">
    <link:loc xlink:type="locator" xlink:href="core.xsd#in-rbi-rep_GoldLoanBalance"
              xlink:label="in-rbi-rep_GoldLoanBalance"/>
  </link:presentationLink>
  <link:presentationLink xlink:type="extended" xlink:role="{NS_ROLE}/Layout">
    <link:loc xlink:type="locator" xlink:href="core.xsd#in-rbi-rep_LayoutOnlyItem"
              xlink:label="in-rbi-rep_LayoutOnlyItem"/>
  </link:presentationLink>
</link:linkbase>
"""

REFERENCE_XML = """<?xml version="1.0" encoding="utf-8"?>
<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
               xmlns:xlink="http://www.w3.org/1999/xlink"
               xmlns:par="http://www.rbi.org/in-rbi-rep-par">
  <link:referenceLink xlink:type="extended" xlink:role="http://www.xbrl.org/2003/role/link">
    <link:loc xlink:type="locator" xlink:href="core.xsd#in-rbi-rep_GrossNPAs"
              xlink:label="loc_gross"/>
    <link:reference xlink:type="resource" xlink:label="res_1">
      <par:Circular>DBOD.NO.BP.BC.12/21.04.048/2011-12</par:Circular>
    </link:reference>
    <link:referenceArc xlink:type="arc" xlink:from="loc_gross" xlink:to="res_1"/>
  </link:referenceLink>
</link:linkbase>
"""

# Blocking rules, dated so recency scores. Names both risk-asset concepts.
FORMULA_BLOCKING = """<?xml version="1.0" encoding="utf-8"?>
<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
               xmlns:va="http://xbrl.org/2008/assertion/value"
               xmlns:cf="http://xbrl.org/2008/filter/concept">
  <va:valueAssertion id="a1" test="$V1 = $V2"/>
  <va:valueAssertion id="a2" test="$V1 &gt;= 0"/>
  <cf:qname>in-rbi-rep:GrossNPAs</cf:qname>
  <cf:qname>in-rbi-rep:ProvisionHeld</cf:qname>
</link:linkbase>
"""

# Advisory only — the filename is what marks it, matching how RBI ships them.
FORMULA_WARNING = """<?xml version="1.0" encoding="utf-8"?>
<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
               xmlns:va="http://xbrl.org/2008/assertion/value"
               xmlns:cf="http://xbrl.org/2008/filter/concept">
  <va:valueAssertion id="w1" test="$V1 &gt; 0"/>
  <cf:qname>in-rbi-rep:GoldLoanBalance</cf:qname>
</link:linkbase>
"""

# One format check on General Info — enough that it is not evidence-free, which
# is exactly the case a naive ordinal ranking gets wrong.
FORMULA_GENINFO = """<?xml version="1.0" encoding="utf-8"?>
<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
               xmlns:va="http://xbrl.org/2008/assertion/value"
               xmlns:cf="http://xbrl.org/2008/filter/concept">
  <va:valueAssertion id="g1" test="$V1 &gt; 0"/>
  <cf:qname>in-rbi-rep:BranchCount</cf:qname>
</link:linkbase>
"""


@pytest.fixture(scope="module")
def taxonomy_dir(tmp_path_factory) -> str:
    root = tmp_path_factory.mktemp("taxonomy")
    (root / "test-role.xsd").write_text(ROLE_XSD, encoding="utf-8")
    (root / "test-presentation.xml").write_text(PRESENTATION_XML, encoding="utf-8")
    (root / "test-reference.xml").write_text(REFERENCE_XML, encoding="utf-8")
    formula = root / "formula"
    formula.mkdir()
    (formula / "in-rbi-test-Mar2022.xml").write_text(FORMULA_BLOCKING, encoding="utf-8")
    (formula / "in-rbi-test-Warnings.xml").write_text(FORMULA_WARNING, encoding="utf-8")
    (formula / "in-rbi-GenInfo-formula.xml").write_text(FORMULA_GENINFO, encoding="utf-8")
    return str(root)


@pytest.fixture(scope="module")
def index(taxonomy_dir) -> ImportanceIndex:
    return ImportanceIndex((taxonomy_dir,))


class TestTaxonomyParsing:
    def test_index_is_usable(self, index):
        assert index.is_usable

    def test_only_coded_roles_become_sections(self, index):
        index._build()
        codes = {s["code"] for s in index._sections.values()}
        assert codes == {"1900", "1000", "3800"}, (
            "layout roles carry no [NNNN] code and are not business sections"
        )

    def test_concept_is_attributed_to_its_section(self, index):
        assert index.score_concept("GrossNPAs")["section_code"] == "1900"
        assert index.score_concept("GoldLoanBalance")["section_code"] == "3800"

    def test_circular_reference_is_read_through_the_arc(self, index):
        assert index.score_concept("GrossNPAs")["circulars"] == [
            "DBOD.NO.BP.BC.12/21.04.048/2011-12"
        ]
        assert index.score_concept("ProvisionHeld")["circulars"] == []

    def test_warning_linkbase_counts_as_advisory_not_blocking(self, index):
        gold = index.score_concept("GoldLoanBalance")
        assert gold["blocking_rules"] == 0
        assert gold["advisory_rules"] >= 1

        npa = index.score_concept("GrossNPAs")
        assert npa["blocking_rules"] >= 1

    def test_amendment_year_is_read_from_the_filename(self, index):
        assert index.score_concept("GrossNPAs")["last_amended"] == 2022

    def test_unknown_concept_degrades_to_zero_not_an_exception(self, index):
        profile = index.score_concept("NoSuchConceptAnywhere")
        assert profile["score"] == 0.0
        assert profile["tier"] == "Low"
        assert profile["section"] == "Unclassified"


class TestScoring:
    def test_mandated_and_blocking_beats_advisory(self, index):
        assert (
            index.score_concept("GrossNPAs")["score"]
            > index.score_concept("GoldLoanBalance")["score"]
        )

    def test_general_information_does_not_outrank_a_risk_section(self, index):
        """The bug a raw ordinal ranking has: [1000] General Information sorts
        first by ordinal but is administrative preamble, not the return's
        purpose. It must lose to [1900] on evidence density."""
        assert (
            index.score_concept("BranchCount")["score"]
            < index.score_concept("GrossNPAs")["score"]
        )

    def test_drivers_explain_the_score(self, index):
        drivers = index.score_concept("GrossNPAs")["drivers"]
        assert any("Mandated by circular" in d for d in drivers)
        assert any("blocking" in d.lower() for d in drivers)


def _facts(values: dict[str, float]) -> list[dict]:
    return [
        {
            "concept": name,
            "period_type": "instant",
            "period_end": "2024-03-31",
            "period_start": "",
            "value_str": str(v),
            "value_num": v,
            "unit": "INR",
            "decimals": "0",
            "ctx_ref": "asof_20240331",
            "dim_key": "",
            "is_dimensional": False,
        }
        for name, v in values.items()
    ]


class TestComparatorIntegration:
    A = _facts({"GrossNPAs": 1_200_000.0, "ProvisionHeld": 500_000.0,
                "GoldLoanBalance": 90_000.0, "BranchCount": 1_100.0})
    B = _facts({"GrossNPAs": 1_000_000.0, "ProvisionHeld": 500_000.0,
                "GoldLoanBalance": 10_000.0, "BranchCount": 1_000.0})

    def test_without_an_index_no_importance_keys_appear(self):
        rows = xc.compute_variance(self.A, "A", self.B, "B", top_n=None)
        assert rows
        assert all("importance" not in r for r in rows)

    def test_with_an_index_every_row_is_tagged(self, index):
        rows = xc.compute_variance(
            self.A, "A", self.B, "B", top_n=None, importance=index,
        )
        assert rows
        for r in rows:
            assert "importance" in r and "importance_tier" in r
            assert "section" in r and "priority" in r

    def test_unchanged_rows_never_head_a_variance_table(self, index):
        """ProvisionHeld is in the most-regulated section and did not move.
        It must not outrank a figure that actually changed."""
        rows = xc.compute_variance(
            self.A, "A", self.B, "B", top_n=None, importance=index,
        )
        assert rows[0]["diff"] != 0
        unchanged = [r for r in rows if r["diff"] == 0]
        moved = [r for r in rows if r["diff"] != 0]
        assert rows.index(moved[-1]) < rows.index(unchanged[0])

    def test_importance_outranks_raw_percentage(self, index):
        """GoldLoanBalance moved +800%; GrossNPAs moved +20%. Ranked by
        magnitude alone gold wins — which is the behaviour this whole feature
        exists to replace."""
        rows = xc.compute_variance(
            self.A, "A", self.B, "B", top_n=None, importance=index,
        )
        order = [r["concept_base"] for r in rows]
        assert order.index("GrossNPAs") < order.index("GoldLoanBalance")

    def test_meta_reports_importance_only_when_available(self, index):
        plain = xc.compute_variance(self.A, "A", self.B, "B", top_n=None)
        assert "importance_available" not in xc.variance_meta(plain, self.A, self.B, 5)

        tagged = xc.compute_variance(
            self.A, "A", self.B, "B", top_n=None, importance=index,
        )
        meta = xc.variance_meta(tagged, self.A, self.B, 5)
        assert meta["importance_available"] is True
        assert meta["sections"] >= 2
        assert meta["mandated"] >= 1

    def test_a_tagging_failure_falls_back_to_magnitude_ranking(self):
        """An index that raises must never break a comparison."""
        class Exploding:
            def score_concept(self, concept):
                raise RuntimeError("taxonomy went missing mid-request")

        rows = xc.compute_variance(
            self.A, "A", self.B, "B", top_n=None, importance=Exploding(),
        )
        assert rows, "comparison still produced rows"
        assert all("priority" not in r for r in rows)


class TestGrouping:
    def test_rows_collapse_into_ranked_sections(self, index):
        rows = xc.compute_variance(
            TestComparatorIntegration.A, "A",
            TestComparatorIntegration.B, "B",
            top_n=None, importance=index,
        )
        groups = group_by_importance(rows, "A", "B", index)
        codes = [g["section_code"] for g in groups]
        assert codes.index("1900") < codes.index("3800")

    def test_group_totals_are_the_sum_of_their_rows(self, index):
        rows = xc.compute_variance(
            TestComparatorIntegration.A, "A",
            TestComparatorIntegration.B, "B",
            top_n=None, importance=index,
        )
        groups = group_by_importance(rows, "A", "B", index)
        assert sum(g["row_count"] for g in groups) == len(rows)
        risk = next(g for g in groups if g["section_code"] == "1900")
        # GrossNPAs +200,000; ProvisionHeld unchanged.
        assert risk["net_diff"] == pytest.approx(200_000.0)
        assert risk["moved_count"] == 1

    def test_unchanged_section_is_not_stamped_critical(self, index):
        """compute_variance grades a zero-baseline row 'critical' because it has
        no percentage to judge. For a 0 → 0 row that is nothing happening, and
        it must not colour the whole section."""
        a = _facts({"GrossNPAs": 0.0, "ProvisionHeld": 0.0})
        b = _facts({"GrossNPAs": 0.0, "ProvisionHeld": 0.0})
        rows = xc.compute_variance(a, "A", b, "B", top_n=None, importance=index)
        groups = group_by_importance(rows, "A", "B", index)
        risk = next(g for g in groups if g["section_code"] == "1900")
        assert risk["moved_count"] == 0
        assert risk["max_severity"] == "low"

    def test_report_names_the_section_and_why_it_ranks(self, index):
        rows = xc.compute_variance(
            TestComparatorIntegration.A, "A",
            TestComparatorIntegration.B, "B",
            top_n=None, importance=index,
        )
        groups = group_by_importance(rows, "A", "B", index)
        text = format_importance_report(groups, "A", "B")
        assert "[1900] Classification of risk assets" in text
        assert "DBOD.NO.BP.BC.12/21.04.048/2011-12" in text
        assert "blocking rule" in text

    def test_empty_groups_render_without_raising(self):
        assert format_importance_report([], "A", "B")


class TestResolutionFailsSoft:
    def test_no_form_id_yields_no_index(self):
        from backend.tools.xbrl_importance import get_importance_index

        assert get_importance_index(None) is None
        assert get_importance_index("") is None

    def test_folder_without_coded_roles_yields_no_index(self, tmp_path, monkeypatch):
        """A taxonomy with no [NNNN] sections cannot rank anything, so the
        comparison must fall back rather than present an empty view."""
        from backend.tools import xbrl_importance

        empty = tmp_path / "Taxonomy"
        empty.mkdir()
        (empty / "stub.xsd").write_text(
            '<?xml version="1.0"?><xsd:schema '
            'xmlns:xsd="http://www.w3.org/2001/XMLSchema"/>',
            encoding="utf-8",
        )
        monkeypatch.setattr(
            "backend.tools.taxonomy_index._candidate_roots",
            lambda form_id, extra_roots=(): (str(empty),),
        )
        assert xbrl_importance.get_importance_index("9999") is None
