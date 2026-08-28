"""Share-of-total must survive a two-level dimension domain.

The numbers here are the real ones from the RAQ(Monthly) comparison
(form 1042, 30-Jun-2026 vs 30-Sep-2025), not invented fixtures:

    AmountOutstanding [Domestic]                     506,108 Cr / 4,855 Cr
      StandardAssets                                 425,621 Cr / 4,466 Cr
      SubStandardAssets                               14,284 Cr /    56 Cr
      DoubtfulAssets                                  66,030 Cr /   254 Cr   <- roll-up
        DoubtfulAssetsOne                             23,978 Cr /  29.5 Cr
        DoubtfulAssetsTwo                             21,839 Cr /    51 Cr
        DoubtfulAssetsThree                           20,213 Cr /   173 Cr
      LossAssets                                         173 Cr /    79 Cr

The four top-level categories partition the parent EXACTLY in both periods.
The three DoubtfulAssets children are also reported, so a naive sum of all
seven siblings reaches 113% of the parent and the additivity gate rejected a
denominator that is provably correct.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.tools import variance_explain as ve  # noqa: E402

LA, LB = "30-Jun-2026", "30-Sep-2025"
PARENT_A, PARENT_B = 5_061_076_134_000, 48_550_659_000

# concept, context suffix, current, previous  — raw rupees, as reported.
_ROWS = [
    (None,                  PARENT_A,          PARENT_B),          # the parent
    ("StandardAssets",      4_256_210_793_000, 44_659_353_000),
    ("SubStandardAssets",     142_837_000_000,    564_000_000),
    ("DoubtfulAssets",        660_299_018_000,  2_537_211_000),    # roll-up
    ("DoubtfulAssetsOne",     239_779_280_000,    295_025_000),
    ("DoubtfulAssetsTwo",     218_387_794_000,    510_540_000),
    ("DoubtfulAssetsThree",   202_131_944_000,  1_731_646_000),
    ("LossAssets",              1_729_800_000,    790_100_000),
]

_DOMESTIC = "RegionOfBusinessAxis=Domestic"


def _build_rows(members=None):
    """Variance rows in the shape compute_variance produces."""
    keep = members if members is not None else [m for m, _, _ in _ROWS]
    out = []
    for member, a, b in _ROWS:
        if member is not None and member not in keep:
            continue
        ck = _DOMESTIC if member is None else f"{_DOMESTIC}|RiskTypeDimension={member}"
        out.append({
            "concept": "AmountOutstanding",
            "concept_base": "AmountOutstanding",
            "context_key": ck,
            "unit": "INR",
            LA: a,
            LB: b,
            "diff": a - b,
            "pct_change": ((a - b) / abs(b) * 100) if b else None,
        })
    return out


def _share_for(member: str, rows=None):
    rows = rows if rows is not None else _build_rows()
    target = next(
        r for r in rows
        if r["context_key"].endswith(f"={member}")
    )
    return ve.compute_share(target, rows, ve._index_rows(rows), LA, LB)


class TestDoubtfulAssetsShare:
    """The reported example: 0.6% -> 4.7%."""

    def test_doubtful_assets_one_share_is_recovered(self):
        share = _share_for("DoubtfulAssetsOne")
        assert share is not None, (
            "no share produced — the roll-up sibling is still defeating the "
            "additivity gate"
        )
        assert share["share_b"] == 0.6
        assert share["share_a"] == 4.7

    def test_share_matches_the_raw_arithmetic(self):
        share = _share_for("DoubtfulAssetsOne")
        assert share["share_a"] == round(100.0 * 239_779_280_000 / PARENT_A, 1)
        assert share["share_b"] == round(100.0 * 295_025_000 / PARENT_B, 1)

    def test_delta_in_percentage_points(self):
        share = _share_for("DoubtfulAssetsOne")
        assert share["share_delta_pp"] == round(4.7 - 0.6, 1)

    def test_parent_is_named_from_the_taxonomy_context(self):
        share = _share_for("DoubtfulAssetsOne")
        assert "Domestic" in share["parent_name"]
        assert "Amount" in share["parent_name"]

    def test_other_categories_also_resolve(self):
        """Not a one-off for the reported member."""
        assert _share_for("StandardAssets")["share_a"] == 84.1
        assert _share_for("DoubtfulAssetsTwo")["share_a"] == 4.3


class TestRollupDetection:
    def test_the_rollup_sibling_is_identified(self):
        rows = _build_rows()
        sibs = [r for r in rows if r["context_key"] != _DOMESTIC]
        rolled = ve._rollup_members(sibs, LA)
        names = {
            r["context_key"].rsplit("=", 1)[-1] for r in sibs if id(r) in rolled
        }
        assert "DoubtfulAssets" in names, (
            "DoubtfulAssets is the sum of its three children and must be "
            f"detected as a roll-up; detected: {names}"
        )

    def test_naive_sum_really_does_overshoot(self):
        """Documents WHY the fix is needed, not just that it works."""
        rows = _build_rows()
        sibs = [r for r in rows if r["context_key"] != _DOMESTIC]
        total = sum(r[LA] for r in sibs)
        assert total > PARENT_A * (1 + ve.SHARE_TOLERANCE)
        assert round(100.0 * total / PARENT_A) == 113

    def test_the_four_top_level_categories_partition_the_parent(self):
        """The evidence that this parent really is the domestic total."""
        for label, parent in ((LA, PARENT_A), (LB, PARENT_B)):
            rows = _build_rows(
                ["StandardAssets", "SubStandardAssets", "DoubtfulAssets", "LossAssets"]
            )
            total = sum(r[label] for r in rows if r["context_key"] != _DOMESTIC)
            assert abs(total - parent) <= abs(parent) * 1e-6


class TestGateStillRejectsBadDenominators:
    """The relaxation must not become a way to divide by a non-total."""

    def test_non_additive_siblings_still_yield_no_share(self):
        rows = _build_rows(["StandardAssets", "DoubtfulAssets"])
        # These two do not sum to the parent and neither is a roll-up of the
        # other, so there is no partition and no share may be produced.
        assert _share_for("StandardAssets", rows) is None

    def test_a_single_sibling_yields_no_share(self):
        rows = _build_rows(["StandardAssets"])
        assert _share_for("StandardAssets", rows) is None

    def test_no_parent_row_yields_no_share(self):
        rows = [r for r in _build_rows() if r["context_key"] != _DOMESTIC]
        assert _share_for("DoubtfulAssetsOne", rows) is None

    def test_overlapping_categories_that_never_reconcile_are_rejected(self):
        """Overlapping exposure categories are not a partition at any level."""
        rows = [
            {"concept": "X", "concept_base": "X", "context_key": "A=Total",
             "unit": "INR", LA: 1_000, LB: 900, "diff": 100, "pct_change": 11.1},
            {"concept": "X", "concept_base": "X", "context_key": "A=Total|B=P",
             "unit": "INR", LA: 900, LB: 800, "diff": 100, "pct_change": 12.5},
            {"concept": "X", "concept_base": "X", "context_key": "A=Total|B=Q",
             "unit": "INR", LA: 800, LB: 700, "diff": 100, "pct_change": 14.3},
        ]
        target = next(r for r in rows if r["context_key"].endswith("=P"))
        assert ve.compute_share(target, rows, ve._index_rows(rows), LA, LB) is None


class TestPerformanceBounds:
    def test_wide_dimensions_skip_the_search(self):
        """Above the bound the search is skipped, not run slowly."""
        sibs = [
            {"concept_base": "X", "context_key": f"A=T|B=M{i}", LA: float(i + 1)}
            for i in range(ve._ROLLUP_MAX_SIBLINGS + 1)
        ]
        assert ve._rollup_members(sibs, LA) == set()

    def test_bounds_are_the_documented_values(self):
        assert ve._ROLLUP_MAX_SIBLINGS == 12
        assert ve._ROLLUP_MAX_COMBO == 5
        assert ve.SHARE_TOLERANCE == 0.02


class TestPercentageConceptsGetNoShare:
    """A share of a percentage restates the same quantity twice.

    PercentageOutstandingAmount [Domestic, DoubtfulAssetsOne] IS the share —
    0.0474 of the domestic book. Computing a share for it produced
    "moved from 0.01% to 0.05%, increasing its share of the domestic book from
    0.6% to 4.7%", which says the same thing in two units in one sentence.
    """

    @staticmethod
    def _pct_rows():
        """Same shape as the monetary family, but unit PURE and ratio values.

        Values are the real ones: the ratios mirror the amounts exactly, which
        is precisely why a share here is redundant rather than wrong.
        """
        out = []
        for member, a, b in _ROWS:
            ck = _DOMESTIC if member is None else f"{_DOMESTIC}|RiskTypeDimension={member}"
            out.append({
                "concept": "PercentageOutstandingAmount",
                "concept_base": "PercentageOutstandingAmount",
                "context_key": ck,
                "unit": "PURE",
                LA: a / PARENT_A,
                LB: b / PARENT_B,
                "diff": a / PARENT_A - b / PARENT_B,
                "pct_change": 677.0,
            })
        return out

    def test_percentage_concept_gets_no_share(self):
        rows = self._pct_rows()
        target = next(r for r in rows if r["context_key"].endswith("=DoubtfulAssetsOne"))
        assert ve.compute_share(target, rows, ve._index_rows(rows), LA, LB) is None

    def test_the_arithmetic_would_otherwise_have_succeeded(self):
        """Proves the guard is what stops it, not a failing additivity check."""
        rows = self._pct_rows()
        target = next(r for r in rows if r["context_key"].endswith("=DoubtfulAssetsOne"))
        monetary = dict(target, unit="INR")
        rows_inr = [dict(r, unit="INR") for r in rows]
        for r in rows_inr:
            if r["context_key"] == target["context_key"]:
                r.update(monetary)
        share = ve.compute_share(
            monetary, rows_inr, ve._index_rows(rows_inr), LA, LB
        )
        assert share is not None, "fixture is wrong — the maths must work"
        assert share["share_a"] == 4.7

    def test_eligibility_is_decided_on_unit(self):
        assert ve._is_share_eligible({"unit": "INR"}) is True
        assert ve._is_share_eligible({"unit": "PURE"}) is False
        assert ve._is_share_eligible({"unit": "pure"}) is False
        assert ve._is_share_eligible({"unit": "PERCENT"}) is False
        assert ve._is_share_eligible({"unit": "RATIO"}) is False

    def test_missing_unit_stays_eligible(self):
        """The additivity gate is still the arbiter; this guard only removes
        cases where a share could never be meaningful."""
        assert ve._is_share_eligible({}) is True
        assert ve._is_share_eligible({"unit": ""}) is True

    def test_a_rate_named_concept_with_a_monetary_unit_keeps_its_share(self):
        """The guard reads the UNIT, never the name.

        'MeanEffectiveInterestRateCharged' is declared monetaryItemType with
        unit INR in this taxonomy — a name-based rule would wrongly strip it.
        """
        assert ve._is_share_eligible(
            {"concept": "MeanEffectiveInterestRateCharged", "unit": "INR"}
        ) is True

    def test_monetary_family_is_unaffected(self):
        """The headline case must still work after the guard."""
        share = _share_for("DoubtfulAssetsOne")
        assert (share["share_b"], share["share_a"]) == (0.6, 4.7)
