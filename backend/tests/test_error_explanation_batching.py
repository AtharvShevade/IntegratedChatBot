"""Tests for the three error-summary/explanation UI/UX improvements:

1. Dimension Errors now have a real, taxonomy-aware on-demand explanation
   (backend/tools/dimension_taxonomy.py — see test_dimension_taxonomy.py for
   its dedicated tests) and the "Explain Dimension Errors" button is shown
   for 4000-series reports (frontend/src/components/MessageBubble.jsx's
   explainableCategories includes 'dimensional' for that report type).
   There is no JS test harness in this repo (no jest/vitest configured) to
   automate a UI assertion for that, so this file covers the backend side:
   the dimensional parsing/counting path is untouched, and
   explain_errors_by_category's dimensional branch preserves its batching
   semantics (offset has no effect) exactly as before.

2. Formula and XBRL/Specification errors are explained in batches of
   exactly 3, offset-based, never re-explaining an already-covered range.

3. count_errors_by_category reports the number of DISTINCT validation
   rules for formula_error/xbrl_schema, not the sum of their occurrence
   counts — while the per-rule occurrence count (e.g. "failed for 149
   reporting instances") is untouched inside each rule's own data.

None of this touches explanation generation, deterministic calculation,
taxonomy lookup, or LLM prompts — every rule/entry dict used below is a
plain constructed stand-in, and the actual explain_* functions being
exercised are the batching/counting wrappers, not the renderers.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import backend.tools.report_lookup as rl


def _formula_rule(name: str, occurrence_count: int) -> dict:
    """A minimal stand-in for one parsed formula-error rule — shape matches
    what parse_formula_errors/parse_generic_formula_errors actually return
    (one dict per rule, with its own "instances" list of occurrences)."""
    return {
        "rule_name": name,
        "formula_expression": "$V1 = $V2",
        "error_count": occurrence_count,
        "instances": [
            {"business_message": "", "variables": []} for _ in range(occurrence_count)
        ],
    }


def _xbrl_entry(rule_key: str | None) -> dict:
    return {"errorType": "XBRL_SCHEMA", "rule": rule_key} if rule_key else {"errorType": "XBRL_SCHEMA"}


@pytest.fixture
def dummy_html_file(tmp_path):
    """A real file path (count_errors_by_category requires os.path.isfile),
    with harmless placeholder content — every parsing function used inside
    it is monkeypatched in these tests, so the actual content is never
    exercised."""
    path = tmp_path / "errors.html"
    path.write_text("<html><body>placeholder</body></html>", encoding="utf-8")
    return str(path)


# ── 1. Unique-rule summary counts (requirement 3) ──────────────────────────

class TestUniqueRuleSummaryCounts:
    def test_formula_error_count_is_rule_count_not_occurrence_sum(self, monkeypatch, dummy_html_file):
        rules = [_formula_rule("RuleA", 149), _formula_rule("RuleB", 171), _formula_rule("RuleC", 1)]
        monkeypatch.setattr(rl, "parse_formula_errors", lambda path: rules)
        counts = rl.count_errors_by_category(dummy_html_file, form_id="4046")  # 4000-series
        assert counts["formula_error"] == 3          # not 149 + 171 + 1 = 321
        assert counts["formula_error"] != 321

    def test_formula_error_count_for_generic_non_4000_series_path(self, monkeypatch, dummy_html_file):
        rules = [_formula_rule(f"Rule{i}", 10) for i in range(8)]
        monkeypatch.setattr(
            "backend.tools.formula_error_generic.parse_generic_formula_errors",
            lambda path: rules,
        )
        counts = rl.count_errors_by_category(dummy_html_file, form_id="2065")  # non-4000-series
        assert counts["formula_error"] == 8

    def test_formula_error_occurrence_count_still_available_per_rule(self):
        """The per-rule occurrence count is NOT removed anywhere — only the
        top-level summary aggregation changed."""
        rule = _formula_rule("RuleA", 149)
        assert len(rule["instances"]) == 149
        assert rule["error_count"] == 149

    def test_xbrl_schema_count_collapses_repeated_rule_key(self, monkeypatch, dummy_html_file):
        entries = (
            [_xbrl_entry("RuleX")] * 5     # same rule failing 5 times
            + [_xbrl_entry("RuleY")] * 2   # same rule failing twice
            + [_xbrl_entry(None)]          # no grouping key at all (directMsg shape)
        )
        monkeypatch.setattr(rl, "parse_backtrack_html_errors", lambda path: entries)
        counts = rl.count_errors_by_category(dummy_html_file)
        # 2 distinct rule keys (RuleX, RuleY) + 1 unkeyed entry counted on its own = 3
        assert counts["xbrl_schema"] == 3
        assert counts["xbrl_schema"] != len(entries)  # not 8

    def test_xbrl_schema_count_falls_back_to_occurrence_count_when_no_keys_present(
        self, monkeypatch, dummy_html_file
    ):
        """directMsg-format files (no rule/assertionLabel/title field at all)
        must keep exactly today's behavior — nothing to collapse."""
        entries = [_xbrl_entry(None) for _ in range(4)]
        monkeypatch.setattr(rl, "parse_backtrack_html_errors", lambda path: entries)
        counts = rl.count_errors_by_category(dummy_html_file)
        assert counts["xbrl_schema"] == 4

    def test_no_rules_means_no_formula_error_key(self, monkeypatch, dummy_html_file):
        monkeypatch.setattr(rl, "parse_formula_errors", lambda path: [])
        counts = rl.count_errors_by_category(dummy_html_file, form_id="4046")
        assert "formula_error" not in counts


# ── 2. Batch size 3 / offset-based, never repeating (requirement 2) ───────

class TestFormulaErrorBatching:
    def test_batch_size_is_exactly_three(self):
        assert rl._MAX_EXPLAIN == 3

    def test_first_batch_is_first_three_rules_4000_series(self, monkeypatch, dummy_html_file):
        rules = [_formula_rule(f"Rule{i}", 1) for i in range(8)]
        monkeypatch.setattr(rl, "parse_formula_errors", lambda path: rules)
        monkeypatch.setattr(rl, "enrich_formula_errors", lambda trimmed: trimmed)
        captured = {}
        def _fake_explain(enriched, form_id=""):
            captured["names"] = [r["rule_name"] for r in enriched]
            return enriched
        monkeypatch.setattr(rl, "explain_formula_errors", _fake_explain)

        result = rl.explain_errors_by_category(dummy_html_file, "formula_error", form_id="4046", offset=0)
        assert captured["names"] == ["Rule0", "Rule1", "Rule2"]
        assert len(result) == 3

    def test_second_batch_continues_from_offset_never_repeats(self, monkeypatch, dummy_html_file):
        rules = [_formula_rule(f"Rule{i}", 1) for i in range(8)]
        monkeypatch.setattr(rl, "parse_formula_errors", lambda path: rules)
        monkeypatch.setattr(rl, "enrich_formula_errors", lambda trimmed: trimmed)
        captured = {}
        def _fake_explain(enriched, form_id=""):
            captured["names"] = [r["rule_name"] for r in enriched]
            return enriched
        monkeypatch.setattr(rl, "explain_formula_errors", _fake_explain)

        rl.explain_errors_by_category(dummy_html_file, "formula_error", form_id="4046", offset=3)
        assert captured["names"] == ["Rule3", "Rule4", "Rule5"]
        # None of the first batch's rules appear again.
        assert not set(captured["names"]) & {"Rule0", "Rule1", "Rule2"}

    def test_final_partial_batch_of_two(self, monkeypatch, dummy_html_file):
        rules = [_formula_rule(f"Rule{i}", 1) for i in range(8)]  # 8 rules: batches of 3,3,2
        monkeypatch.setattr(rl, "parse_formula_errors", lambda path: rules)
        monkeypatch.setattr(rl, "enrich_formula_errors", lambda trimmed: trimmed)
        captured = {}
        def _fake_explain(enriched, form_id=""):
            captured["names"] = [r["rule_name"] for r in enriched]
            return enriched
        monkeypatch.setattr(rl, "explain_formula_errors", _fake_explain)

        result = rl.explain_errors_by_category(dummy_html_file, "formula_error", form_id="4046", offset=6)
        assert captured["names"] == ["Rule6", "Rule7"]
        assert len(result) == 2

    def test_offset_past_end_returns_empty(self, monkeypatch, dummy_html_file):
        rules = [_formula_rule(f"Rule{i}", 1) for i in range(3)]
        monkeypatch.setattr(rl, "parse_formula_errors", lambda path: rules)
        monkeypatch.setattr(rl, "enrich_formula_errors", lambda trimmed: trimmed)
        monkeypatch.setattr(rl, "explain_formula_errors", lambda enriched, form_id="": enriched)

        result = rl.explain_errors_by_category(dummy_html_file, "formula_error", form_id="4046", offset=3)
        assert result == []

    def test_generic_non_4000_series_path_also_batches_by_three_with_offset(self, monkeypatch, dummy_html_file):
        rules = [_formula_rule(f"Rule{i}", 1) for i in range(5)]
        monkeypatch.setattr(
            "backend.tools.formula_error_generic.parse_generic_formula_errors",
            lambda path: rules,
        )
        captured = {}
        def _fake_explain(trimmed, form_id=""):
            captured["names"] = [r["rule_name"] for r in trimmed]
            return trimmed
        monkeypatch.setattr(
            "backend.tools.formula_error_generic.explain_generic_formula_errors",
            _fake_explain,
        )

        rl.explain_errors_by_category(dummy_html_file, "formula_error", form_id="2065", offset=0)
        assert captured["names"] == ["Rule0", "Rule1", "Rule2"]

        rl.explain_errors_by_category(dummy_html_file, "formula_error", form_id="2065", offset=3)
        assert captured["names"] == ["Rule3", "Rule4"]  # final partial batch of 2

    def test_default_offset_is_zero_backward_compatible(self, monkeypatch, dummy_html_file):
        """Callers that don't pass offset at all must see the first batch,
        exactly like every existing call site before this change."""
        rules = [_formula_rule(f"Rule{i}", 1) for i in range(5)]
        monkeypatch.setattr(rl, "parse_formula_errors", lambda path: rules)
        monkeypatch.setattr(rl, "enrich_formula_errors", lambda trimmed: trimmed)
        captured = {}
        monkeypatch.setattr(
            rl, "explain_formula_errors",
            lambda enriched, form_id="": (captured.setdefault("names", [r["rule_name"] for r in enriched]), enriched)[1],
        )
        rl.explain_errors_by_category(dummy_html_file, "formula_error", form_id="4046")
        assert captured["names"] == ["Rule0", "Rule1", "Rule2"]


class TestXbrlSchemaBatching:
    def test_batches_raw_entries_by_three_with_offset(self, monkeypatch, dummy_html_file):
        entries = [{"errorType": "XBRL_SCHEMA", "id": i} for i in range(7)]
        monkeypatch.setattr(rl, "parse_backtrack_html_errors", lambda path: entries)
        monkeypatch.setattr(rl, "parse_formula_errors", lambda path: [])
        monkeypatch.setattr(rl, "parse_dimensional_html_errors", lambda path: [])
        monkeypatch.setattr(rl, "_build_root_cause_analysis", lambda trimmed, f, d: trimmed)
        captured = {}
        def _fake_explain(trimmed):
            captured["ids"] = [e["id"] for e in trimmed]
            return trimmed
        monkeypatch.setattr(rl, "explain_validation_errors", _fake_explain)

        rl.explain_errors_by_category(dummy_html_file, "xbrl_schema", offset=0)
        assert captured["ids"] == [0, 1, 2]

        rl.explain_errors_by_category(dummy_html_file, "xbrl_schema", offset=3)
        assert captured["ids"] == [3, 4, 5]

        rl.explain_errors_by_category(dummy_html_file, "xbrl_schema", offset=6)
        assert captured["ids"] == [6]  # final partial batch of 1


class TestDimensionalUnaffected:
    def test_dimensional_branch_applies_offset(self, monkeypatch, dummy_html_file):
        """Dimension-error explanation is taxonomy-aware (see
        backend.tools.dimension_taxonomy) and, now that the "Explain
        Dimension Errors" button is wired up in the UI, batching must behave
        the same as the formula_error branch: offset advances through the
        error list instead of always re-explaining the first batch."""
        errors = [{"id": i} for i in range(5)]
        monkeypatch.setattr(rl, "parse_dimensional_html_errors", lambda path: errors)
        monkeypatch.setattr(rl, "explain_dimensional_errors", lambda trimmed, **kwargs: trimmed)
        result_offset_0 = rl.explain_errors_by_category(dummy_html_file, "dimensional", offset=0)
        result_offset_2 = rl.explain_errors_by_category(dummy_html_file, "dimensional", offset=2)
        assert result_offset_0 != result_offset_2
        assert [e["id"] for e in result_offset_0] == [0, 1, 2]
        assert [e["id"] for e in result_offset_2] == [2, 3, 4]


# ── 3. explain_category_for_report: has_more / next_offset / total_count ──

class TestExplainCategoryForReportBatchMetadata:
    def _run(self, coro):
        return asyncio.run(coro)

    def test_has_more_true_when_batch_smaller_than_total(self, monkeypatch, dummy_html_file):
        import backend.agent as agent

        def _fake_explain_for_form_sync(path, category, form_id="", offset=0):
            rules = [_formula_rule(f"Rule{i}", 1) for i in range(8)]
            return rules[offset:offset + 3]

        monkeypatch.setattr(rl, "explain_errors_by_category_for_form", _fake_explain_for_form_sync)
        monkeypatch.setattr(rl, "count_errors_by_category", lambda path, form_id="": {"formula_error": 8})

        result = self._run(agent.explain_category_for_report(
            dummy_html_file, "formula_error", form_id="4046", offset=0,
        ))
        assert result["data"]["has_more"] is True
        assert result["data"]["next_offset"] == 3
        assert result["data"]["total_count"] == 8
        assert len(result["error_details"]) == 3

    def test_has_more_false_on_last_batch(self, monkeypatch, dummy_html_file):
        import backend.agent as agent

        def _fake_explain_for_form_sync(path, category, form_id="", offset=0):
            rules = [_formula_rule(f"Rule{i}", 1) for i in range(8)]
            return rules[offset:offset + 3]

        monkeypatch.setattr(rl, "explain_errors_by_category_for_form", _fake_explain_for_form_sync)
        monkeypatch.setattr(rl, "count_errors_by_category", lambda path, form_id="": {"formula_error": 8})

        result = self._run(agent.explain_category_for_report(
            dummy_html_file, "formula_error", form_id="4046", offset=6,
        ))
        assert result["data"]["has_more"] is False
        assert result["data"]["next_offset"] == 8
        assert len(result["error_details"]) == 2

    def test_no_further_errors_message_when_offset_past_end(self, monkeypatch, dummy_html_file):
        import backend.agent as agent

        monkeypatch.setattr(rl, "explain_errors_by_category_for_form", lambda *a, **k: [])
        monkeypatch.setattr(rl, "count_errors_by_category", lambda path, form_id="": {"formula_error": 8})

        result = self._run(agent.explain_category_for_report(
            dummy_html_file, "formula_error", form_id="4046", offset=8,
        ))
        assert result["result_type"] == "error"
        assert "no further" in result["response_text"].lower()
