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


_DUMMY_FORM_ID = "4046"
_DUMMY_FILENAME = "errors.html"


@pytest.fixture
def dummy_html_file(tmp_path, monkeypatch):
    """A real file path (count_errors_by_category requires os.path.isfile),
    with harmless placeholder content — every parsing function used inside
    it is monkeypatched in these tests, so the actual content is never
    exercised.

    explain_category_for_report() now takes (filename, form_id) and rebuilds
    the real path via report_lookup.build_error_file_path() (L-17 fix)
    rather than a client-sent path -- that helper's layout is
    instance_base_dir()/form_id/filename, so the fixture writes the file at
    that same nested location (using _DUMMY_FORM_ID/_DUMMY_FILENAME) while
    still returning the full path string for the many tests here that only
    exercise the lower-level count_errors_by_category()/
    explain_errors_by_category() functions directly with a path, unaffected
    by the L-17 signature change.

    Two separate bindings of instance_base_dir must both be patched:
    build_error_file_path (report_lookup.py) reads it via `config.
    instance_base_dir()` (module attribute access, patchable on
    backend.config directly), while error_explanation.py's containment
    check imported the name directly (`from backend.config import
    instance_base_dir`), which captured its own local reference at import
    time and needs patching on that module instead.
    """
    from backend import config as _config_module
    monkeypatch.setattr(_config_module, "instance_base_dir", lambda: str(tmp_path))
    monkeypatch.setattr("backend.agent.error_explanation.instance_base_dir", lambda: str(tmp_path))
    form_dir = tmp_path / _DUMMY_FORM_ID
    form_dir.mkdir()
    path = form_dir / _DUMMY_FILENAME
    path.write_text("<html><body>placeholder</body></html>", encoding="utf-8")
    return str(path)


@pytest.fixture
def legacy_flow(monkeypatch):
    """Pin these tests to the LEGACY explanation flow.

    They monkeypatch legacy seams (rl.parse_formula_errors,
    formula_error_generic.*, rl.parse_dimensional_html_errors) to assert the
    batching/counting contract. Under ERROR_EXPLAIN_V2 the wrappers call the
    unified flow instead, so those patches would no longer be reached — the
    contract itself is unchanged and is asserted for the V2 flow in
    TestUnifiedFlowBatching below.
    """
    monkeypatch.setenv("ERROR_EXPLAIN_V2", "0")


# ── 0. count_errors_by_category exposes only a filename (L-17) ────────────

class TestCountErrorsByCategoryNeverLeaksAbsolutePath:
    def test_result_carries_bare_filename_not_absolute_path(self, monkeypatch, dummy_html_file):
        """count_errors_by_category()'s result dict becomes
        error_category_counts in the /chat, /guided, etc. API responses --
        it must carry only the bare filename (L-17), never the absolute
        server path (drive letter, tenant folder layout) it used to."""
        counts = rl.count_errors_by_category(dummy_html_file, form_id=_DUMMY_FORM_ID)
        assert counts["filename"] == _DUMMY_FILENAME
        assert "error_file_path" not in counts
        assert "\\" not in counts["filename"] and "/" not in counts["filename"]

    def test_empty_input_still_returns_empty_filename(self):
        counts = rl.count_errors_by_category("", form_id="4046")
        assert counts["filename"] == ""


# ── 1. Unique-rule summary counts (requirement 3) ──────────────────────────

class TestUniqueRuleSummaryCounts:
    def test_formula_error_count_is_rule_count_not_occurrence_sum(self, legacy_flow, monkeypatch, dummy_html_file):
        rules = [_formula_rule("RuleA", 149), _formula_rule("RuleB", 171), _formula_rule("RuleC", 1)]
        monkeypatch.setattr(rl, "parse_formula_errors", lambda path: rules)
        counts = rl.count_errors_by_category(dummy_html_file, form_id="4046")  # 4000-series
        assert counts["formula_error"] == 3          # not 149 + 171 + 1 = 321
        assert counts["formula_error"] != 321

    def test_formula_error_count_for_generic_non_4000_series_path(self, legacy_flow, monkeypatch, dummy_html_file):
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

    def test_no_rules_means_no_formula_error_key(self, legacy_flow, monkeypatch, dummy_html_file):
        monkeypatch.setattr(rl, "parse_formula_errors", lambda path: [])
        counts = rl.count_errors_by_category(dummy_html_file, form_id="4046")
        assert "formula_error" not in counts


# ── 2. Batch size 3 / offset-based, never repeating (requirement 2) ───────

class TestFormulaErrorBatching:
    def test_batch_size_is_exactly_three(self):
        assert rl._MAX_EXPLAIN == 3

    def test_first_batch_is_first_three_rules_4000_series(self, legacy_flow, monkeypatch, dummy_html_file):
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

    def test_second_batch_continues_from_offset_never_repeats(self, legacy_flow, monkeypatch, dummy_html_file):
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

    def test_final_partial_batch_of_two(self, legacy_flow, monkeypatch, dummy_html_file):
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

    def test_offset_past_end_returns_empty(self, legacy_flow, monkeypatch, dummy_html_file):
        rules = [_formula_rule(f"Rule{i}", 1) for i in range(3)]
        monkeypatch.setattr(rl, "parse_formula_errors", lambda path: rules)
        monkeypatch.setattr(rl, "enrich_formula_errors", lambda trimmed: trimmed)
        monkeypatch.setattr(rl, "explain_formula_errors", lambda enriched, form_id="": enriched)

        result = rl.explain_errors_by_category(dummy_html_file, "formula_error", form_id="4046", offset=3)
        assert result == []

    def test_generic_non_4000_series_path_also_batches_by_three_with_offset(self, legacy_flow, monkeypatch, dummy_html_file):
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

    def test_default_offset_is_zero_backward_compatible(self, legacy_flow, monkeypatch, dummy_html_file):
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
    def test_dimensional_branch_applies_offset(self, legacy_flow, monkeypatch, dummy_html_file):
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

        def _fake_explain_for_form_sync(path, category, form_id="", offset=0, lang="en"):
            rules = [_formula_rule(f"Rule{i}", 1) for i in range(8)]
            return rules[offset:offset + 3]

        monkeypatch.setattr(rl, "explain_errors_by_category_for_form", _fake_explain_for_form_sync)
        monkeypatch.setattr(rl, "count_errors_by_category", lambda path, form_id="": {"formula_error": 8})

        result = self._run(agent.explain_category_for_report(
            _DUMMY_FILENAME, "formula_error", form_id=_DUMMY_FORM_ID, offset=0,
        ))
        assert result["data"]["has_more"] is True
        assert result["data"]["next_offset"] == 3
        assert result["data"]["total_count"] == 8
        assert len(result["error_details"]) == 3

    def test_has_more_false_on_last_batch(self, monkeypatch, dummy_html_file):
        import backend.agent as agent

        def _fake_explain_for_form_sync(path, category, form_id="", offset=0, lang="en"):
            rules = [_formula_rule(f"Rule{i}", 1) for i in range(8)]
            return rules[offset:offset + 3]

        monkeypatch.setattr(rl, "explain_errors_by_category_for_form", _fake_explain_for_form_sync)
        monkeypatch.setattr(rl, "count_errors_by_category", lambda path, form_id="": {"formula_error": 8})

        result = self._run(agent.explain_category_for_report(
            _DUMMY_FILENAME, "formula_error", form_id=_DUMMY_FORM_ID, offset=6,
        ))
        assert result["data"]["has_more"] is False
        assert result["data"]["next_offset"] == 8
        assert len(result["error_details"]) == 2

    def test_no_further_errors_message_when_offset_past_end(self, monkeypatch, dummy_html_file):
        import backend.agent as agent

        monkeypatch.setattr(rl, "explain_errors_by_category_for_form", lambda *a, **k: [])
        monkeypatch.setattr(rl, "count_errors_by_category", lambda path, form_id="": {"formula_error": 8})

        result = self._run(agent.explain_category_for_report(
            _DUMMY_FILENAME, "formula_error", form_id=_DUMMY_FORM_ID, offset=8,
        ))
        assert result["result_type"] == "error"
        assert "no further" in result["response_text"].lower()


# ── 4. filename/form_id containment (C-04 fix, updated for L-17) ──────────
#
# L-17 changed the client-facing contract: the client no longer sends any
# path at all, only a bare filename + form_id. explain_category_for_report()
# rebuilds the real path server-side via report_lookup.build_error_file_path
# (the same helper /download-file already uses: os.path.basename() on both
# inputs, then joined under instance_base_dir()/form_id/). These tests cover
# what a malicious filename/form_id can and cannot still do to that rebuild,
# plus the _is_contained_error_file() containment check (C-04) as the
# second, independent layer behind it.

class TestExplainCategoryPathContainment:
    def _run(self, coro):
        return asyncio.run(coro)

    def _patch_instance_base_dir(self, monkeypatch, path):
        from backend import config as _config_module
        monkeypatch.setattr(_config_module, "instance_base_dir", lambda: str(path))
        monkeypatch.setattr("backend.agent.error_explanation.instance_base_dir", lambda: str(path))

    def test_traversal_in_filename_is_stripped_to_a_bare_name(self, monkeypatch, tmp_path):
        """os.path.basename() strips any directory component from filename
        before it's ever joined -- a traversal attempt collapses to a plain
        filename inside the legitimate form_id folder, never escaping it.
        Since that stripped name has a disallowed extension here, it's
        rejected anyway (this is the common case: traversal payloads target
        a specific real file, which rarely happens to end in .xml/.html)."""
        import backend.agent as agent

        base = tmp_path / "Instance"
        base.mkdir()
        self._patch_instance_base_dir(monkeypatch, base)

        called = {"n": 0}
        monkeypatch.setattr(
            rl, "explain_errors_by_category_for_form",
            lambda *a, **k: called.__setitem__("n", called["n"] + 1) or [],
        )

        for bad_filename in (
            "../../../Windows/win.ini",
            r"..\..\Windows\win.ini",
            r"\\evilhost\share\x.ini",
        ):
            result = self._run(agent.explain_category_for_report(bad_filename, "formula_error", form_id="9999"))
            assert result["result_type"] == "error"
        assert called["n"] == 0

    def test_traversal_in_filename_with_allowed_extension_still_lands_inside_base(self, monkeypatch, tmp_path):
        """Even when the stripped basename DOES have an allowed extension,
        it can only ever resolve to instance_base_dir()/form_id/<basename>
        -- there is no way for a value with no real path separator survival
        (basename already stripped them) to escape that folder. This is
        the containment check confirming success, not failure -- the fix
        does not merely reject traversal, it makes it structurally
        impossible to reach anywhere outside the form's own folder."""
        import backend.agent as agent

        base = tmp_path / "Instance"
        form_dir = base / "9999"
        form_dir.mkdir(parents=True)
        (form_dir / "win.xml").write_text("<x/>", encoding="utf-8")
        self._patch_instance_base_dir(monkeypatch, base)

        monkeypatch.setattr(rl, "explain_errors_by_category_for_form", lambda *a, **k: [])
        result = self._run(agent.explain_category_for_report(
            "../../../Windows/win.xml", "formula_error", form_id="9999",
        ))
        # Reaches the real pipeline (file found inside form 9999's own
        # folder), not the containment-rejection branch.
        assert "no error file is available" not in result["response_text"].lower()

    def test_form_id_escape_attempt_is_rejected_by_containment_check(self, monkeypatch, tmp_path):
        """form_id="..' has no separator, so os.path.basename() leaves it
        unchanged -- build_error_file_path would join base/../secret.xml,
        landing in base's PARENT. The _is_contained_error_file() containment
        check (C-04) is the layer that catches this, independent of
        basename()'s inability to help here."""
        import backend.agent as agent

        base = tmp_path / "Instance"
        base.mkdir()
        (tmp_path / "secret.xml").write_text("<x/>", encoding="utf-8")
        self._patch_instance_base_dir(monkeypatch, base)

        called = {"n": 0}
        monkeypatch.setattr(
            rl, "explain_errors_by_category_for_form",
            lambda *a, **k: called.__setitem__("n", called["n"] + 1) or [],
        )

        result = self._run(agent.explain_category_for_report("secret.xml", "formula_error", form_id=".."))
        assert result["result_type"] == "error"
        assert called["n"] == 0

    def test_form_id_with_separators_collapses_to_its_last_segment(self, monkeypatch, tmp_path):
        """A multi-segment form_id also only ever survives as its LAST
        component through os.path.basename() -- it cannot be used to
        reconstruct a multi-level traversal in one shot either."""
        import backend.agent as agent

        base = tmp_path / "Instance"
        form_dir = base / "9999"
        form_dir.mkdir(parents=True)
        (form_dir / "errors.xml").write_text("<x/>", encoding="utf-8")
        self._patch_instance_base_dir(monkeypatch, base)

        monkeypatch.setattr(rl, "explain_errors_by_category_for_form", lambda *a, **k: [])
        result = self._run(agent.explain_category_for_report(
            "errors.xml", "formula_error", form_id=r"..\9999",
        ))
        assert "no error file is available" not in result["response_text"].lower()

    def test_rejects_disallowed_extension_even_for_a_real_in_tree_file(self, monkeypatch, tmp_path):
        import backend.agent as agent

        base = tmp_path / "Instance"
        form_dir = base / _DUMMY_FORM_ID
        form_dir.mkdir(parents=True)
        (form_dir / "not_really_an_error_file.exe").write_text("x", encoding="utf-8")
        self._patch_instance_base_dir(monkeypatch, base)

        result = self._run(agent.explain_category_for_report(
            "not_really_an_error_file.exe", "formula_error", form_id=_DUMMY_FORM_ID,
        ))
        assert result["result_type"] == "error"

    def test_missing_filename_or_form_id_returns_friendly_error(self, monkeypatch, dummy_html_file):
        import backend.agent as agent

        result = self._run(agent.explain_category_for_report("", "formula_error", form_id=_DUMMY_FORM_ID))
        assert result["result_type"] == "error"
        result = self._run(agent.explain_category_for_report(_DUMMY_FILENAME, "formula_error", form_id=""))
        assert result["result_type"] == "error"

    def test_allows_legitimate_in_tree_file(self, monkeypatch, dummy_html_file):
        import backend.agent as agent

        monkeypatch.setattr(rl, "explain_errors_by_category_for_form", lambda *a, **k: [])
        result = self._run(agent.explain_category_for_report(
            _DUMMY_FILENAME, "formula_error", form_id=_DUMMY_FORM_ID,
        ))
        # Reaches the "no rules parsed" branch, not the containment-rejection
        # branch -- i.e. the file was actually opened/processed.
        assert result["result_type"] == "error"
        assert "no formula errors could be parsed" in result["response_text"].lower()
