"""Tests for the variance comparison / visualisation split.

The contract these lock down:

    all extracted facts
        -> compare ALL (compute_variance top_n=None)
            |- variance_data  : top 30            -> frontend table
            |- variance_all   : every row         -> visualisation + HTML export
            `- variance_meta  : coverage counts   -> "all N facts across M concepts"

so the two failure modes that motivated the change cannot come back:

  1. the visualisation being handed the table's 30-row slice, and
  2. the serialiser silently dropping the five enrichment fields the table and
     chart are both written to read (unit / sign_change / anomaly_flags /
     severity / context_key), which made those features inert.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import backend.agent as agent
from backend.models import ChatResponse
from backend.tools import xbrl_comparator as xc

LABEL_A = "Mar-2026"
LABEL_B = "Dec-2025"


def _facts(n_concepts: int, mult: float, members: int = 1) -> list[dict]:
    """Synthetic fact list: n_concepts, optionally across `members` contexts."""
    out: list[dict] = []
    for i in range(1, n_concepts + 1):
        for m in range(members):
            out.append({
                "concept":     f"Concept{i:03d}",
                "value_num":   100.0 * i * mult + m,
                "value_str":   str(100.0 * i * mult + m),
                "unit":        "INR",
                "period_end":  "2026-03-31",
                "period_type": "instant",
                "context_ref": f"ctx{m}",
            })
    return out


# ═════════════════════════════════════════════════════════════════════════════
# 1. compute_variance caps the RETURN, never the comparison
# ═════════════════════════════════════════════════════════════════════════════

class TestUncappedComparison:
    def test_default_still_returns_thirty(self):
        """Existing callers must be untouched — the default is still 30."""
        rows = xc.compute_variance(_facts(100, 1.5), LABEL_A, _facts(100, 1.0), LABEL_B)
        assert len(rows) == 30

    def test_top_n_none_returns_everything(self):
        rows = xc.compute_variance(
            _facts(100, 1.5), LABEL_A, _facts(100, 1.0), LABEL_B, top_n=None,
        )
        assert len(rows) == 100

    @pytest.mark.parametrize("n", [1, 30, 31, 100, 250])
    def test_no_hidden_cap_at_any_size(self, n):
        rows = xc.compute_variance(
            _facts(n, 1.5), LABEL_A, _facts(n, 1.0), LABEL_B, top_n=None,
        )
        assert len(rows) == n

    def test_explicit_top_n_still_slices(self):
        rows = xc.compute_variance(
            _facts(100, 1.5), LABEL_A, _facts(100, 1.0), LABEL_B, top_n=10,
        )
        assert len(rows) == 10

    def test_table_slice_is_a_prefix_of_the_full_set(self):
        """The table must be the top of the SAME ranked result, not a
        separately-ranked list — otherwise row 31 could outrank row 1."""
        full = xc.compute_variance(
            _facts(100, 1.5), LABEL_A, _facts(100, 1.0), LABEL_B, top_n=None,
        )
        top = xc.compute_variance(_facts(100, 1.5), LABEL_A, _facts(100, 1.0), LABEL_B)
        assert [r["concept"] for r in top] == [r["concept"] for r in full[:30]]


# ═════════════════════════════════════════════════════════════════════════════
# 1b. Only facts present in BOTH periods are compared
# ═════════════════════════════════════════════════════════════════════════════

class TestIntersectionOnly:
    """compute_variance keys on `set(map_a) & set(map_b)`, so a fact reported in
    one period only can never produce a row. These lock that in, because
    treating missing-vs-present as a movement would invent variance that the
    filing does not contain."""

    def _rows(self, fa, fb):
        return xc.compute_variance(fa, LABEL_A, fb, LABEL_B, top_n=None)

    def test_extra_fact_in_current_is_excluded(self):
        fa = _facts(12, 1.5)                     # Concept001..012
        fb = _facts(10, 1.0)                     # Concept001..010
        rows = self._rows(fa, fb)
        names = {r["concept_base"] for r in rows}
        assert len(rows) == 10
        assert "Concept011" not in names and "Concept012" not in names

    def test_extra_fact_in_previous_is_excluded(self):
        rows = self._rows(_facts(10, 1.5), _facts(12, 1.0))
        assert len(rows) == 10
        assert "Concept011" not in {r["concept_base"] for r in rows}

    def test_one_sided_facts_never_enter_direction_counts(self):
        fa, fb = _facts(12, 1.5), _facts(10, 1.0)
        rows = self._rows(fa, fb)
        meta = xc.variance_meta(rows, fa, fb, 10)
        # 10 comparable, not 12 — and the two extras are in neither direction.
        assert meta["compared"] == 10
        assert meta["increases"] + meta["decreases"] + meta["unchanged"] == 10

    def test_disjoint_instances_compare_nothing(self):
        fa = [{**f, "concept": f"OnlyA{i}"} for i, f in enumerate(_facts(5, 1.5))]
        fb = [{**f, "concept": f"OnlyB{i}"} for i, f in enumerate(_facts(5, 1.0))]
        assert self._rows(fa, fb) == []

    def test_stats_out_param_reports_the_exclusion(self):
        """The counts existed only in a debug log; the out-param surfaces them
        so the UI can say what was left out."""
        stats: dict = {}
        xc.compute_variance(
            _facts(12, 1.5), LABEL_A, _facts(10, 1.0), LABEL_B,
            top_n=None, stats=stats,
        )
        assert stats["matched"] == 10
        assert stats["only_in_a"] == 2      # Concept011, Concept012
        assert stats["only_in_b"] == 0
        assert stats["one_sided"] == 2

    def test_stats_is_optional(self):
        """Omitting it must behave exactly as before."""
        assert len(xc.compute_variance(
            _facts(10, 1.5), LABEL_A, _facts(10, 1.0), LABEL_B, top_n=None,
        )) == 10

    def test_payload_meta_carries_the_exclusion(self):
        fa, fb = _facts(12, 1.5), _facts(10, 1.0)
        _raw, all_s, _tbl, meta, _t = agent._build_variance_payload(
            fa, LABEL_A, fb, LABEL_B,
        )
        assert meta["compared"] == 10
        assert meta["one_sided"] == 2
        assert len(all_s) == 10, "visualisation must not receive one-sided facts"


# ═════════════════════════════════════════════════════════════════════════════
# 2. Coverage metadata
# ═════════════════════════════════════════════════════════════════════════════

class TestVarianceMeta:
    def test_counts_describe_the_full_comparison(self):
        fa, fb = _facts(40, 1.5), _facts(40, 1.0)
        rows = xc.compute_variance(fa, LABEL_A, fb, LABEL_B, top_n=None)
        meta = xc.variance_meta(rows, fa, fb, table_rows=30)
        assert meta["compared"] == 40          # not 30
        assert meta["concepts"] == 40
        assert meta["table_rows"] == 30
        assert meta["facts_a"] == len(fa)
        assert meta["facts_b"] == len(fb)

    def test_direction_counts_partition_the_rows(self):
        fa, fb = _facts(40, 1.5), _facts(40, 1.0)
        rows = xc.compute_variance(fa, LABEL_A, fb, LABEL_B, top_n=None)
        meta = xc.variance_meta(rows, fa, fb, 30)
        assert meta["increases"] + meta["decreases"] + meta["unchanged"] == meta["compared"]

    def test_concepts_counted_on_the_bare_name(self):
        """concept_base exists so one concept across many dimension members
        counts once. `concept` has the member suffix concatenated in, so
        counting on it would report members as concepts."""
        fa, fb = _facts(5, 1.5), _facts(5, 1.0)
        rows = xc.compute_variance(fa, LABEL_A, fb, LABEL_B, top_n=None)
        assert all("concept_base" in r for r in rows)
        assert all(
            r["concept"].startswith(r["concept_base"]) for r in rows
        )
        meta = xc.variance_meta(rows, fa, fb, 5)
        assert meta["concepts"] == 5


# ═════════════════════════════════════════════════════════════════════════════
# 3. The two datasets, as the frontend receives them
# ═════════════════════════════════════════════════════════════════════════════

class TestPayloadSplit:
    def _payload(self, n_concepts=100):
        fa, fb = _facts(n_concepts, 1.5), _facts(n_concepts, 1.0)
        return fa, fb, agent._build_variance_payload(fa, LABEL_A, fb, LABEL_B)

    def test_table_is_thirty_and_chart_is_everything(self):
        _, _, (raw, all_s, tbl_s, meta, _text) = self._payload(100)
        assert len(raw) == 100
        assert len(all_s) == 100, "visualisation must get every comparable row"
        assert len(tbl_s) == 30, "table keeps its existing 30-row size"

    def test_chart_dataset_is_not_the_table_slice(self):
        """The regression this whole change exists to prevent."""
        _, _, (_raw, all_s, tbl_s, _m, _t) = self._payload(100)
        assert all_s is not tbl_s
        assert len(all_s) > len(tbl_s)

    def test_small_comparison_gives_identical_lengths(self):
        """Under 30 rows both datasets are the same size — and that must not
        be mistaken for the truncation bug."""
        _, _, (_raw, all_s, tbl_s, meta, _t) = self._payload(12)
        assert len(all_s) == len(tbl_s) == 12
        assert meta["compared"] == 12

    ENRICHMENT = ("context_key", "unit", "anomaly_flags", "sign_change", "severity")

    def test_enrichment_fields_survive_serialisation(self):
        """These were computed and then dropped, leaving the sign-reversal
        highlight, anomaly badge, unit tooltip and severity chip inert."""
        _, _, (_raw, all_s, tbl_s, _m, _t) = self._payload(40)
        for dataset, name in ((all_s, "variance_all"), (tbl_s, "variance_data")):
            for field in self.ENRICHMENT:
                assert field in dataset[0], f"{field} missing from {name}"

    def test_core_fields_unchanged(self):
        """Backward compatibility: the six original keys keep their names."""
        _, _, (_raw, _all, tbl_s, _m, _t) = self._payload(40)
        for field in ("concept", "val_a", "val_b", "diff", "pct_change", "significant"):
            assert field in tbl_s[0]

    def test_text_table_still_reflects_the_top_slice(self):
        """The plain-text chat table stays the 30-row view it has always been —
        widening it would flood the bubble."""
        _, _, (_raw, _all, _tbl, _m, text) = self._payload(100)
        assert text.count("\n") < 60


# ═════════════════════════════════════════════════════════════════════════════
# 4. Survives the response model
# ═════════════════════════════════════════════════════════════════════════════

class TestChatResponseCarriesBoth:
    def test_both_datasets_and_meta_are_declared_fields(self):
        """ChatResponse(**result) DROPS undeclared keys, so an undeclared field
        would vanish silently between the agent and the browser."""
        fa, fb = _facts(100, 1.5), _facts(100, 1.0)
        raw, all_s, tbl_s, meta, text = agent._build_variance_payload(
            fa, LABEL_A, fb, LABEL_B,
        )
        built = agent._build(
            intent="compare_reports", report_name="R", response_text=text,
            result_type="variance_table", variance_data=tbl_s,
            variance_all=all_s, variance_meta=meta,
            variance_label_a=LABEL_A, variance_label_b=LABEL_B, llm_summary="",
        )
        out = ChatResponse(**built).model_dump()
        assert len(out["variance_data"]) == 30
        assert len(out["variance_all"]) == 100
        assert out["variance_meta"]["compared"] == 100
        assert out["variance_meta"]["concepts"] == 100

    def test_meta_is_set_independently_of_variance_data(self):
        """The chart dataset must not be gated on the table's presence."""
        built = agent._build(
            intent="compare_reports", report_name="R", response_text="t",
            result_type="variance_table",
            variance_all=[{"concept": "A"}], variance_meta={"compared": 1},
        )
        assert built["variance_all"] == [{"concept": "A"}]
        assert built["variance_meta"] == {"compared": 1}
