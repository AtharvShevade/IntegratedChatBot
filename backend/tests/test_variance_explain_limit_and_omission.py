"""AI-analysis fact selection: default target of 8, Critical never cut, Low only as a
fallback, significant Medium first, and an exact "N not explained" note.

The selection is pure Python (no LLM), so these tests are deterministic. The one
end-to-end test mocks the model call.
"""
from __future__ import annotations

import asyncio
import importlib

import pytest

from backend import version_config
from backend.tools import variance_explain as ve
from backend.tools.variance_explain import select_facts, select_facts_ex


@pytest.fixture(params=[False, True], ids=["v5.5", "v6.0"], autouse=True)
def _version(request, monkeypatch):
    """The selection has no version branch; prove it by running everything under both."""
    monkeypatch.setattr(version_config, "IS_V6", request.param)


_n = 0


def _row(tier, name, *, priority=1.0, section=None, significant=False, matched=True, diff=100.0, val=1000.0):
    global _n
    _n += 1
    return {
        "concept": name, "concept_base": name, "context_key": "BASE",
        "importance_tier": tier, "importance_matched": matched,
        "priority": priority, "significant": significant,
        "section_code": section if section is not None else f"S{_n}",   # distinct section unless given
        "diff": diff, "A": val, "B": val + diff, "pct_change": 10.0,
    }


def _sel(rows, **kw):
    return select_facts_ex(rows, label_a="A", label_b="B", **kw)


# ── 1/2. default and override ────────────────────────────────────────────────
class TestLimitConfiguration:
    def test_default_is_8_when_unset(self, monkeypatch):
        monkeypatch.delenv("VARIANCE_EXPLAIN_LIMIT", raising=False)
        try:
            assert importlib.reload(ve).SUMMARY_CONCEPT_LIMIT == 8
        finally:
            monkeypatch.delenv("VARIANCE_EXPLAIN_LIMIT", raising=False)
            importlib.reload(ve)

    def test_env_override_to_20_is_honoured(self, monkeypatch):
        monkeypatch.setenv("VARIANCE_EXPLAIN_LIMIT", "20")
        try:
            assert importlib.reload(ve).SUMMARY_CONCEPT_LIMIT == 20
        finally:
            monkeypatch.delenv("VARIANCE_EXPLAIN_LIMIT", raising=False)
            importlib.reload(ve)

    def test_limit_20_applies_to_non_critical_facts(self):
        rows = [_row("High", f"h{i}", priority=50 - i) for i in range(25)]
        picked, omitted = _sel(rows, limit=20)
        assert len(picked) == 20 and omitted == 5

    def test_default_param_is_the_single_constant(self):
        assert select_facts_ex.__defaults__[0] == ve.SUMMARY_CONCEPT_LIMIT


# ── 3/4. Critical is never cut ───────────────────────────────────────────────
class TestCriticalNeverOmitted:
    def test_ten_critical_facts_all_kept_over_the_limit_of_8(self):
        rows = [_row("Critical", f"c{i}", priority=100 - i) for i in range(10)]
        picked, omitted = _sel(rows, limit=8)
        assert len(picked) == 10 and omitted == 0
        assert {r["concept"] for r in picked} == {f"c{i}" for i in range(10)}

    def test_critical_kept_even_with_extra_high_facts_and_those_are_omitted(self):
        rows = [_row("Critical", f"c{i}", priority=100 - i) for i in range(10)]
        rows += [_row("High", f"h{i}", priority=10 - i * 0.1) for i in range(4)]
        picked, omitted = _sel(rows, limit=8)
        assert sum(r["importance_tier"] == "Critical" for r in picked) == 10
        assert not any(r["importance_tier"] == "High" for r in picked)
        assert omitted == 4          # the High facts that did not fit; no Critical is counted

    def test_five_critical_use_the_remaining_capacity_for_high(self):
        rows = [_row("Critical", f"c{i}", priority=100 - i) for i in range(5)]
        rows += [_row("High", f"h{i}", priority=50 - i) for i in range(10)]
        picked, omitted = _sel(rows, limit=8)
        tiers = [r["importance_tier"] for r in picked]
        assert len(picked) == 8 and tiers.count("Critical") == 5 and tiers.count("High") == 3
        assert omitted == 7

    def test_presented_in_priority_order(self):
        rows = [_row("Critical", "c", priority=10), _row("High", "h", priority=90)]
        picked, _ = _sel(rows, limit=8)
        assert [r["priority"] for r in picked] == sorted((r["priority"] for r in picked), reverse=True)


# ── 5/6. Low only as a fallback ──────────────────────────────────────────────
class TestLowTier:
    def test_low_selected_when_nothing_higher_qualifies(self):
        rows = [_row("Low", f"l{i}") for i in range(5)]
        picked, omitted = _sel(rows, limit=8)
        assert len(picked) == 5 and omitted == 0

    @pytest.mark.parametrize("top", ["Critical", "High", "Medium"])
    def test_low_is_never_mixed_with_a_higher_tier(self, top):
        rows = [_row(top, "top", priority=50)]
        rows += [_row("Low", f"l{i}", priority=40) for i in range(5)]
        if top == "Critical":
            rows += [_row("High", "hi", priority=45)]
        picked, _ = _sel(rows, limit=8)
        assert picked and all(r["importance_tier"] != "Low" for r in picked)

    def test_unclassified_rows_are_never_eligible(self):
        rows = [_row("", f"x{i}", matched=False) for i in range(4)]
        assert _sel(rows) == ([], 0)


# ── 7/8. significant preference inside Medium ────────────────────────────────
class TestSignificantMedium:
    def test_significant_medium_facts_come_first_without_changing_ranking(self):
        # Medium is the top tier here. Non-significant facts have the HIGHER priority.
        rows = [_row("Medium", f"n{i}", priority=90 - i, significant=False) for i in range(5)]
        rows += [_row("Medium", f"s{i}", priority=10 - i, significant=True) for i in range(3)]
        picked, omitted = _sel(rows, limit=4)
        names = {r["concept"] for r in picked}
        assert {"s0", "s1", "s2"} <= names            # all significant ones were chosen
        assert len(picked) == 4 and omitted == 4      # 1 non-significant fills the last slot
        assert [r["priority"] for r in picked] == sorted((r["priority"] for r in picked), reverse=True)

    def test_no_significant_rows_still_selects_eligible_facts(self):
        rows = [_row("Medium", f"m{i}", priority=20 - i) for i in range(6)]
        picked, omitted = _sel(rows, limit=4)
        assert len(picked) == 4 and omitted == 2

    def test_significance_does_not_shrink_the_selection_when_capacity_remains(self):
        rows = [_row("Medium", "s", significant=True), _row("Medium", "n", significant=False)]
        picked, omitted = _sel(rows, limit=8)
        assert len(picked) == 2 and omitted == 0

    def test_significance_only_orders_medium_not_high(self):
        rows = [_row("High", "h-nosig", priority=60, significant=False)]
        rows += [_row("Medium", f"m{i}", priority=10, significant=True) for i in range(5)]
        picked, _ = _sel(rows, limit=3)
        assert "h-nosig" in {r["concept"] for r in picked}


# ── 9/10/13. omission count is exact; diversity rules still hold ─────────────
class TestOmittedCount:
    def test_zero_when_everything_fits(self):
        picked, omitted = _sel([_row("High", f"h{i}") for i in range(5)], limit=8)
        assert omitted == 0 and len(picked) == 5

    def test_structural_concepts_are_not_counted(self):
        rows = [_row("High", f"h{i}", priority=50 - i) for i in range(9)]
        rows += [_row("High", "SomeTable [Table]", priority=99), _row("High", "XAxis", priority=98)]
        rows[-2]["concept_base"] = rows[-2]["concept"] = "ProfitAndLossAbstract"
        rows[-1]["concept_base"] = rows[-1]["concept"] = "ClassificationAxis"
        picked, omitted = _sel(rows, limit=8)
        assert len(picked) == 8 and omitted == 1       # only the 9th real fact is left out

    def test_other_tiers_are_not_counted(self):
        rows = [_row("Critical", f"c{i}") for i in range(3)]
        rows += [_row("High", f"h{i}") for i in range(2)]
        rows += [_row("Medium", f"m{i}") for i in range(10)]     # outside the Critical+High window
        rows += [_row("Low", f"l{i}") for i in range(10)]
        picked, omitted = _sel(rows, limit=8)
        assert len(picked) == 5 and omitted == 0

    def test_per_section_limit_is_still_enforced_and_not_counted_as_omitted(self):
        # 12 High facts, all in ONE section: the section cap (6) rejects 6 of them -
        # that is a diversity rejection, not a limit omission.
        rows = [_row("High", f"h{i}", priority=50 - i, section="ONE") for i in range(12)]
        picked, omitted = _sel(rows, limit=20)
        assert len(picked) == ve.MAX_PER_SECTION and omitted == 0

    def test_per_concept_limit_is_still_enforced(self):
        rows = []
        for i in range(6):                      # one concept, six dimensional variants
            r = _row("High", "AmountOutstanding", priority=50 - i, diff=(-1) ** i * 100 * (3 ** i))
            r["concept"] = f"AmountOutstanding [m{i}]"
            rows.append(r)
        picked, _ = _sel(rows, limit=20)
        assert len(picked) <= ve.MAX_DIMS_PER_CONCEPT

    def test_capped_selection_is_a_prefix_of_the_uncapped_one(self):
        rows = [_row("High", f"h{i}", priority=50 - i) for i in range(15)]
        small, om_small = _sel(rows, limit=5)
        big, om_big = _sel(rows, limit=20)
        assert {r["concept"] for r in small} <= {r["concept"] for r in big}
        assert len(small) + om_small == len(big) + om_big == 15

    def test_select_facts_keeps_its_list_return(self):
        rows = [_row("High", f"h{i}") for i in range(3)]
        assert isinstance(select_facts(rows, label_a="A", label_b="B"), list)


# ── the note itself, and the generated text ──────────────────────────────────
def _run_generate(rows, **kw):
    return asyncio.run(ve.generate_explanations(rows, "A", "B", "Rpt", polish=False, **kw))


class TestGeneratedText:
    """The omitted count is computed but NOT shown in the analysis text."""

    def _rows(self, n_high):
        return [_row("High", f"Concept{i}", priority=50 - i) for i in range(n_high)]

    def test_no_omission_note_is_shown_even_when_facts_are_left_out(self):
        text = _run_generate(self._rows(14), limit=8)       # polish=False: deterministic templates, no LLM
        assert len([l for l in text.splitlines() if l.startswith("\u2022")]) == 8
        assert "additional eligible" not in text
        assert "explanation limit" not in text

    def test_critical_over_the_limit_are_all_explained(self):
        rows = [_row("Critical", f"Crit{i}", priority=100 - i) for i in range(10)]
        text = _run_generate(rows, limit=8)
        assert len([l for l in text.splitlines() if l.startswith("\u2022")]) == 10

    def test_missing_json_means_no_tiers_and_no_explanation(self):
        rows = [_row("", f"x{i}", matched=False) for i in range(6)]      # what a missing/invalid JSON produces
        assert _run_generate(rows, limit=8) == ""
