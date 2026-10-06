"""Regression tests: the AI variance narrative's fact selection follows the
SAME dynamic regulatory-importance tier fallback as the chat table
(frontend's selectHeadlineTiers), instead of a hardcoded Critical+High set.

Bug: backend/tools/variance_explain.py's select_facts() filtered rows by a
fixed ELIGIBLE_TIERS = ("Critical", "High"). Once the frontend was fixed to
dynamically send whichever tier is actually highest-available (e.g. 110
Medium/Low rows when a comparison has zero Critical/High changes), this
backend filter independently discarded all of them -- select_facts()
returned [], generate_explanations() logged "no Critical/High facts to
explain" and returned "", and /compare-summary came back with chars=0 even
though real rows were sent and real changes existed. The user saw "AI
analysis is unavailable" despite a table full of real Medium/Low variance.

Fix: _select_eligible_tiers(rows) computes the same highest-available-tier
window (TIER_ORDER = Critical > High > Medium > Low, anchored at the top
tier with at least one changed concept, plus the next tier down) that
frontend/src/components/MessageBubble.jsx's selectHeadlineTiers() computes,
and select_facts() uses it instead of a fixed tuple.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.tools.variance_explain import _select_eligible_tiers, select_facts


def _row(tier, concept, priority=1.0, matched=True, **overrides):
    base = {
        "importance_matched": matched,
        "importance_tier": tier,
        "concept": concept,
        "concept_base": concept,
        "priority": priority,
        "section_code": "S1",
    }
    base.update(overrides)
    return base


class TestSelectEligibleTiers:
    def test_critical_and_high_present_selects_critical_high(self):
        rows = [_row("Critical", "c1"), _row("High", "h1"), _row("Medium", "m1"), _row("Low", "l1")]
        assert _select_eligible_tiers(rows) == ("Critical", "High")

    def test_no_critical_selects_high_medium(self):
        rows = [_row("High", "h1"), _row("Medium", "m1"), _row("Low", "l1")]
        assert _select_eligible_tiers(rows) == ("High", "Medium")

    def test_no_critical_or_high_selects_medium_low(self):
        rows = [_row("Medium", "m1"), _row("Low", "l1")]
        assert _select_eligible_tiers(rows) == ("Medium", "Low")

    def test_only_low_selects_just_low(self):
        rows = [_row("Low", "l1")]
        assert _select_eligible_tiers(rows) == ("Low",)

    def test_nothing_classified_selects_nothing(self):
        assert _select_eligible_tiers([]) == ()
        assert _select_eligible_tiers([_row("", "x", matched=False)]) == ()

    def test_unmatched_rows_never_satisfy_a_tier(self):
        rows = [_row("Critical", "c1", matched=False), _row("Low", "l1")]
        assert _select_eligible_tiers(rows) == ("Low",)


class TestSelectFactsUsesDynamicTiers:
    def test_medium_low_rows_are_not_discarded(self):
        """The exact reported bug: 110 real Medium/Low rows with zero
        Critical/High must still produce selected facts, not an empty list."""
        rows = [_row("Medium", f"m{i}", priority=10.0 - i) for i in range(5)]
        rows += [_row("Low", f"l{i}", priority=1.0 - i * 0.01) for i in range(60)]
        selected = select_facts(rows, label_a="A", label_b="B")
        assert len(selected) > 0
        assert all(r["importance_tier"] in ("Medium", "Low") for r in selected)

    def test_critical_high_still_preferred_when_present(self):
        rows = [_row("Critical", "c1", priority=100.0)]
        rows += [_row("Medium", f"m{i}", priority=1.0) for i in range(5)]
        selected = select_facts(rows, label_a="A", label_b="B")
        tiers = {r["importance_tier"] for r in selected}
        # Critical is present -> window is Critical+High, Medium excluded.
        assert tiers == {"Critical"}

    def test_exactly_seven_low_concepts_are_explainable(self):
        """Requirement 11: 7 Decreased, no Critical/High -> those 7 must be
        selectable/explainable, not treated as nothing to analyse."""
        rows = [_row("Low", f"l{i}", priority=1.0 - i * 0.01) for i in range(7)]
        selected = select_facts(rows, label_a="A", label_b="B")
        assert len(selected) > 0
        assert all(r["importance_tier"] == "Low" for r in selected)

    def test_nothing_classified_still_returns_empty(self):
        """Genuine 'nothing to analyse' must still behave as before."""
        rows = [_row("", f"x{i}", matched=False) for i in range(5)]
        assert select_facts(rows, label_a="A", label_b="B") == []
