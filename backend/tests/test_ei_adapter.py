"""The chatbot side of the error-improvement integration: the hook in formula_error, the adapter's switches, the card's UI
sections and the new `table` section's text. They use fakes, so no repo or workbook is needed.

A data-dependent smoke test runs only when ERROR_IMPROVEMENT_TEST_FILE (an error report) and ERROR_IMPROVEMENT_TEST_REPO
(its repo root) are set.
"""
from __future__ import annotations

import os

import pytest

from backend.error_improvement import adapter, rule_cards
from backend.tools import error_card, formula_error

_UI_KINDS = {"headline", "labeled_text", "table", "note", "locator", "rule", "matrix", "fix", "details", "issue_card"}


def _card(name="R1", number=1):
    c = {"rule_name": name, "number": number, "checks": "A = B + C", "problem": "A does not equal B + C.",
            "cause": "B is 0.", "fix": "Correct B.", "related": "May also resolve rule 2.", "other_cases": None,
            "cells": [{"item": "A", "sheet": "S", "cell": "K7", "row_label": "Total", "current": "10.00"}],
            "calc": [("Left side", "₹10"), ("Right side", "₹5"), ("Difference", "₹5")],
            "evidence_key": "CONFIRMED", "evidence": "verified", "note": "Explanation: automated.", "kind": "ratio"}
    c["view"] = rule_cards._compact_view(c, [], {}, rule_cards.cell_money)
    return c


# ── the card's UI sections ──────────────────────────────────────────────────────────────────────────────────────
def test_card_sections_use_only_kinds_the_frontend_renders():
    card = _card()
    card["cells"] = [{"item": "A", "sheet": "S", "cell": "K7", "row_label": "1. Total", "current": "10.00"}]
    card["view"] = rule_cards._compact_view(card, [], {}, rule_cards.cell_money)
    secs = rule_cards.card_to_sections(card)
    assert [s["kind"] for s in secs] == ["issue_card"] and {s["kind"] for s in secs} <= _UI_KINDS
    s0 = secs[0]
    assert [k["label"] for k in s0["kv"]] == ["Reported value", "Calculated value", "Difference"]
    assert s0["cells"]["groups"][0]["cells"] == [{"cell": "K7", "label": "Total"}]


def test_table_section_renders_as_aligned_text():
    sec = error_card.table("Cell details", ["Item", "Cell"], [["Gross Advances", "K7"], ["Sub-total B", "K105"]])
    text = error_card.sections_to_text("t", [sec])
    assert "Cell details" in text and "Gross Advances" in text and "K105" in text
    assert error_card.sections_to_text("t", [error_card.table("Empty", ["a"], [])]).count("Empty") == 1


# ── the adapter's switches ───────────────────────────────────────────────────────────────────────────────────────
def test_adapter_is_on_by_default_and_off_with_the_switch(monkeypatch):
    monkeypatch.delenv("ERROR_IMPROVEMENT", raising=False)
    assert adapter.enabled()
    for off in ("0", "false", "no", "off"):
        monkeypatch.setenv("ERROR_IMPROVEMENT", off)
        assert not adapter.enabled()


def test_adapter_returns_nothing_when_off_missing_file_or_not_english(monkeypatch, tmp_path):
    f = tmp_path / "e.html"
    f.write_text("<html/>", encoding="utf-8")
    rules = [{"rule_name": "R1"}]
    monkeypatch.setattr(adapter, "_result_for", lambda *a, **k: {"cards": {"R1": _card()}, "info": {}})
    monkeypatch.setenv("ERROR_IMPROVEMENT", "1")
    assert set(adapter.explain_batch(rules, str(f))) == {"R1"}                       # works
    assert adapter.explain_batch(rules, str(f), lang="hi") == {}                      # English only
    assert adapter.explain_batch(rules, str(tmp_path / "missing.html")) == {}         # no file
    monkeypatch.setenv("ERROR_IMPROVEMENT", "0")
    assert adapter.explain_batch(rules, str(f)) == {}                                 # switched off


def test_adapter_fills_the_chatbots_rule_dict_and_never_raises(monkeypatch, tmp_path):
    f = tmp_path / "e.html"
    f.write_text("<html/>", encoding="utf-8")
    monkeypatch.setattr(adapter, "_result_for", lambda *a, **k: {"cards": {"R1": _card()}, "info": {"basis": "x", "seconds": 1}})
    out = adapter.explain_batch([{"rule_name": "R1", "instances": [1]}, {"rule_name": "NoCard"}], str(f))
    assert set(out) == {"R1"}
    item = out["R1"]
    assert item["instances"] == [1] and item["_error_category"] == "formula_error" and item["_improved"] is True
    assert item["explanation_sections"][0]["kind"] == "issue_card" and "What went wrong?" in item["explanation"]

    def boom(*a, **k):
        raise RuntimeError("engine failure")
    monkeypatch.setattr(adapter, "_result_for", boom)
    assert adapter.explain_batch([{"rule_name": "R1"}], str(f)) == {}                  # a failure means "use the old explanation"


# ── the hook in formula_error.explain_formula_error_file ─────────────────────────────────────────────────────────
def _hook_env(monkeypatch, improved):
    rules = [{"rule_name": f"R{i}"} for i in range(1, 5)]
    monkeypatch.setattr(formula_error, "parse_formula_errors_v2", lambda p: rules)
    calls = []

    def old(batch, form_id="", error_file_path="", lang="en"):
        calls.append([r["rule_name"] for r in batch])
        return [{"rule_name": r["rule_name"], "explanation": "old"} for r in batch]
    monkeypatch.setattr(formula_error, "explain_formula_rules", old)
    monkeypatch.setattr(formula_error, "_explain_with_error_improvement", lambda *a, **k: improved)
    return calls


def test_hook_keeps_batch_order_and_explains_the_rest_the_old_way(monkeypatch):
    calls = _hook_env(monkeypatch, {"R2": {"rule_name": "R2", "explanation": "new"}})
    out = formula_error.explain_formula_error_file("x.html", max_rules=3, offset=0)
    assert [(o["rule_name"], o["explanation"]) for o in out] == [("R1", "old"), ("R2", "new"), ("R3", "old")]
    assert calls == [["R1", "R3"]]                      # the old path only sees what the engine did not explain


def test_hook_uses_the_old_path_for_everything_when_the_engine_has_nothing(monkeypatch):
    calls = _hook_env(monkeypatch, {})
    out = formula_error.explain_formula_error_file("x.html", max_rules=3, offset=1)
    assert [o["rule_name"] for o in out] == ["R2", "R3", "R4"] and all(o["explanation"] == "old" for o in out)
    assert calls == [["R2", "R3", "R4"]]


def test_hook_skips_the_old_path_when_the_engine_explained_every_rule(monkeypatch):
    calls = _hook_env(monkeypatch, {f"R{i}": {"rule_name": f"R{i}", "explanation": "new"} for i in (1, 2, 3)})
    out = formula_error.explain_formula_error_file("x.html", max_rules=3)
    assert [o["explanation"] for o in out] == ["new"] * 3 and calls == []


def test_helper_returns_nothing_when_the_adapter_import_or_call_fails(monkeypatch):
    monkeypatch.setattr(adapter, "explain_batch", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")))
    assert formula_error._explain_with_error_improvement([{"rule_name": "R1"}], [{"rule_name": "R1"}], "x.html", "", "en") == {}
    assert formula_error._explain_with_error_improvement([], [], "x.html", "", "en") == {}


# ── optional real-data smoke test ────────────────────────────────────────────────────────────────────────────────
@pytest.mark.skipif(not (os.getenv("ERROR_IMPROVEMENT_TEST_FILE") and os.getenv("ERROR_IMPROVEMENT_TEST_REPO")),
                    reason="set ERROR_IMPROVEMENT_TEST_FILE and ERROR_IMPROVEMENT_TEST_REPO to run against real data")
def test_real_error_file_gets_cards_through_the_chatbot_entry_point(monkeypatch):
    monkeypatch.setenv("ERROR_IMPROVEMENT", "1")
    monkeypatch.setenv("ERROR_IMPROVEMENT_REPO", os.environ["ERROR_IMPROVEMENT_TEST_REPO"])
    out = formula_error.explain_formula_error_file(os.environ["ERROR_IMPROVEMENT_TEST_FILE"], max_rules=3)
    assert out
    improved = [o for o in out if o.get("_improved")]
    assert improved, "the engine explained none of the first rules"
    for o in improved:
        kinds = {s["kind"] for s in o["explanation_sections"]}
        assert "issue_card" in kinds


# ── a card built from database reads is not kept for long; an Excel card is ──────────────────────────────────────
def _cached_calls(monkeypatch, tmp_path, db, ttl, clock):
    import time
    from backend.error_improvement import explain as ex
    f = tmp_path / "x_Instance.html"
    f.write_text("x")
    adapter._CACHE.clear()
    calls = []
    card = {"db": True} if db else {"db": False}
    monkeypatch.setattr(ex, "explain_file", lambda *a, **k: calls.append(1) or {"cards": {"R": card}, "info": {}})
    monkeypatch.setenv("EI_DB_CARD_CACHE_SECONDS", str(ttl))
    monkeypatch.setattr(time, "monotonic", lambda: clock[0])
    adapter._result_for(str(f), "repo", None)
    clock[0] += 31
    adapter._result_for(str(f), "repo", None)
    return len(calls)


def test_database_card_is_read_again_after_the_short_window(monkeypatch, tmp_path):
    assert _cached_calls(monkeypatch, tmp_path, db=True, ttl=30, clock=[1000.0]) == 2


def test_excel_card_stays_cached(monkeypatch, tmp_path):
    assert _cached_calls(monkeypatch, tmp_path, db=False, ttl=30, clock=[1000.0]) == 1


def test_database_card_is_reused_inside_the_window(monkeypatch, tmp_path):
    assert _cached_calls(monkeypatch, tmp_path, db=True, ttl=60, clock=[1000.0]) == 1
