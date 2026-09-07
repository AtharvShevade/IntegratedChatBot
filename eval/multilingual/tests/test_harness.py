"""Unit tests for the multilingual evaluation harness.

These test the harness itself, not the chatbot. They run offline: no Ollama, no
Oracle, no XML repo. Anything here that needs the pipeline uses the identity
translator so that the model seam is exercised without a network call.
"""
from __future__ import annotations

import json

import pytest

from eval.multilingual import masking, metrics, translator as tr
from eval.multilingual.dataset import build_dataset


# --------------------------------------------------------------------------
# masking: the hard gate
# --------------------------------------------------------------------------

def test_identical_text_preserves_everything():
    text = "RAQ shows 1,234.50 on 31-03-2025 (12% change)"
    report = masking.check_preservation(text, text)
    assert report.passed
    assert report.violations == []
    assert report.hallucinations == []


def test_dropped_number_is_a_violation():
    english = "Total is 1,234.50 as of 31-03-2025"
    localized = "Le total est de 1 234,50 au 31-03-2025"
    report = masking.check_preservation(english, localized)
    assert not report.passed
    assert any(v.kind == "number" and v.expected == "1,234.50" for v in report.violations)


def test_altered_report_name_is_a_violation():
    lexicon = {"CIMS_RAQ(Monthly)"}
    english = "Status of CIMS_RAQ(Monthly) is Filed"
    localized = "Le statut de CIMS_RAQ(Mensuel) est Déposé"
    report = masking.check_preservation(english, localized, lexicon)
    assert not report.passed
    assert any(v.kind == "entity" for v in report.violations)


def test_invented_number_is_a_hallucination():
    report = masking.check_preservation("There are 3 reports", "Il y a 3 rapports sur 7")
    assert any(h.kind == "number" and h.actual == "7" for h in report.hallucinations)


@pytest.mark.parametrize(
    "localized,family",
    [
        ("المجموع ١٢٣٤", "arabic-indic"),
        ("कुल १२३४", "devanagari"),
    ],
)
def test_localised_digit_shapes_pass_but_warn(localized, family):
    """A digit-shape change preserves the value, so failing it would be a false
    positive -- but production code assumes ASCII, so it must still surface."""
    report = masking.check_preservation("Total 1234", localized)
    assert report.passed
    assert family in report.digit_shape_warnings


def test_lexicon_matching_is_word_bounded():
    """Three-letter return codes occur inside ordinary words; substring
    counting would report entities that were never there."""
    assert masking.lexicon_hits("europe interrop dropped", {"ROP"}) == {}
    assert masking.lexicon_hits("the ROP return", {"ROP"}) == {"ROP": 1}


def test_lexicon_matching_handles_punctuated_names():
    hits = masking.lexicon_hits("status of CIMS_RAQ(Monthly) today", {"CIMS_RAQ(Monthly)"})
    assert hits == {"CIMS_RAQ(Monthly)": 1}


def test_date_reordering_is_caught_despite_same_digits():
    report = masking.check_preservation("due 31-03-2025", "échéance 03-31-2025")
    assert not report.passed
    assert any(v.kind == "date" for v in report.violations)


# --------------------------------------------------------------------------
# translator: thinking-trace stripping and the model seam
# --------------------------------------------------------------------------

def test_clean_strips_thinking_block():
    raw = "<think>The user wants French. Let me translate.</think>\nBonjour"
    text, had = tr._clean(raw)
    assert text == "Bonjour"
    assert had


def test_clean_strips_unterminated_thinking_without_inventing_content():
    text, had = tr._clean("<think>reasoning that never closes")
    assert text == ""
    assert had


def test_clean_strips_fences_and_preamble():
    assert tr._clean("```\nBonjour\n```")[0] == "Bonjour"
    assert tr._clean("Here is the translation: Bonjour")[0] == "Bonjour"
    assert tr._clean("Translation: Bonjour")[0] == "Bonjour"


def test_clean_leaves_ordinary_output_alone():
    assert tr._clean("Le statut de RAQ est Déposé")[0] == "Le statut de RAQ est Déposé"


def test_identity_translator_is_a_drop_in_translator():
    """Proves EVAL_TRANSLATE_MODEL is the only model seam: anything satisfying
    the protocol substitutes cleanly."""
    t = tr.IdentityTranslator()
    result = t.translate("what is the status of RAQ", "fr", "en")
    assert result.ok and result.text == "what is the status of RAQ"
    assert isinstance(result, tr.TranslationResult)


def test_same_language_translation_short_circuits():
    t = tr.OllamaTranslator(model="unused", base_url="http://127.0.0.1:1")
    result = t.translate("hello", "en", "en")
    assert result.ok and result.latency_ms == 0.0


def test_translation_failure_falls_back_to_source_and_reports_error():
    """A dead endpoint must degrade, not abort the run -- but it must be
    recorded, so the case is not silently scored on untranslated text."""
    t = tr.OllamaTranslator(model="nope", base_url="http://127.0.0.1:1", timeout=0.2)
    result = t.translate("bonjour", "fr", "en")
    assert not result.ok
    assert result.error
    assert result.text == "bonjour"


# --------------------------------------------------------------------------
# metrics
# --------------------------------------------------------------------------

def test_baseline_variance_detects_an_unstable_case():
    runs = [
        {"a": {"intent": "get_status", "result_type": "final"},
         "b": {"intent": "unknown", "result_type": ""}},
        {"a": {"intent": "get_status", "result_type": "final"},
         "b": {"intent": "return_list", "result_type": "db_qa_result"}},
    ]
    cases = metrics.build_baseline(runs)
    variance = metrics.baseline_variance(cases)
    assert variance["unstable_case_ids"] == ["b"]
    assert variance["stable_cases"] == 1
    assert cases["a"].stable and not cases["b"].stable


def test_routing_match_flags_baseline_stability():
    runs = [{"a": {"intent": "get_status", "result_type": "final", "db_intent": ""}}]
    cases = metrics.build_baseline(runs)
    match = metrics.routing_match(
        cases["a"], {"intent": "get_status", "result_type": "final", "db_intent": ""}
    )
    assert match["routing_ok"] and match["all_fields_ok"] and match["baseline_stable"]


def test_routing_match_detects_a_miss():
    runs = [{"a": {"intent": "get_status", "result_type": "final"}}]
    cases = metrics.build_baseline(runs)
    match = metrics.routing_match(cases["a"], {"intent": "unknown", "result_type": ""})
    assert not match["routing_ok"]
    assert match["expected"]["intent"] == "get_status"
    assert match["actual"]["intent"] == "unknown"


def test_sql_match_normalises_whitespace_and_case():
    assert metrics.sql_match("select A from T", "SELECT   a\nFROM t;") is True
    assert metrics.sql_match("select A from T", "select B from T") is False
    assert metrics.sql_match(None, None) is None


def test_percentile_and_latency_summary():
    assert metrics.percentile([1, 2, 3, 4, 5], 50) == 3
    summary = metrics.latency_summary([100.0, 200.0, 300.0])
    assert summary["n"] == 3 and summary["p50"] == 200.0 and summary["max"] == 300.0


def test_aggregate_excludes_unstable_baselines_from_headline_fidelity():
    """The whole point of Adjustment 1: a case the pipeline cannot reproduce
    must not count against the model."""
    records = [
        {"routing": {"routing_ok": True, "all_fields_ok": True, "baseline_stable": True},
         "preservation": {"passed": True, "hallucination_count": 0}},
        {"routing": {"routing_ok": False, "all_fields_ok": False, "baseline_stable": False},
         "preservation": {"passed": True, "hallucination_count": 0}},
    ]
    summary = metrics.aggregate(records)
    assert summary["routing_fidelity_pct"] == 100.0   # stable subset only
    assert summary["routing_fidelity_raw_pct"] == 50.0
    assert summary["stable_baseline_cases"] == 1


def test_verdict_grades():
    good = {"routing_fidelity_pct": 99.0, "entity_preservation_pct": 100.0,
            "latency": {"added_ms": {"p95": 3000.0}}}
    assert metrics.verdict(good)[0] == "PASS"

    mid = {"routing_fidelity_pct": 96.0, "entity_preservation_pct": 99.5,
           "latency": {"added_ms": {"p95": 6000.0}}}
    assert metrics.verdict(mid)[0] == "CONDITIONAL"

    bad = {"routing_fidelity_pct": 80.0, "entity_preservation_pct": 90.0,
           "latency": {"added_ms": {"p95": 20000.0}}}
    assert metrics.verdict(bad)[0] == "FAIL"


# --------------------------------------------------------------------------
# dataset
# --------------------------------------------------------------------------

def test_all_language_sets_are_aligned():
    sets = {lang: build_dataset.load(lang) for lang in build_dataset.LANGS}
    ids = {lang: [row["id"] for row in rows] for lang, rows in sets.items()}
    reference = ids["en"]
    for lang, lang_ids in ids.items():
        assert lang_ids == reference, f"{lang} is not aligned with en"


def test_every_case_has_non_empty_text_in_every_language():
    for lang in build_dataset.LANGS:
        for row in build_dataset.load(lang):
            if row.get("multi_turn"):
                assert row["turns"]
            else:
                assert row["text"].strip(), f"{lang}/{row['id']} empty"


def test_non_english_sets_are_actually_translated():
    """Guards against a language file silently falling back to English."""
    english = {row["id"]: row.get("text") for row in build_dataset.load("en")}
    for lang in ("fr", "ar", "hi"):
        rows = [r for r in build_dataset.load(lang) if not r.get("multi_turn")]
        identical = [r["id"] for r in rows if r["text"] == english[r["id"]]]
        assert not identical, f"{lang} still English for: {identical}"


def test_entity_lexicon_excludes_ambiguous_plain_words():
    """'Admin', 'Daily' and 'All' are legitimately translatable prose; asserting
    they survive verbatim would manufacture false violations."""
    from eval.multilingual import config

    data = json.loads((config.DATASET_DIR / "entities.json").read_text(encoding="utf-8"))
    lexicon = masking.load_lexicon(config.DATASET_DIR / "entities.json")
    excluded = {n for names in data["_excluded_ambiguous"].values() for n in names}
    assert "Admin" in excluded and "Daily" in excluded
    assert not (lexicon & excluded)
    assert "DPSS09" in lexicon or any(e.startswith("DPSS") for e in lexicon)


# --------------------------------------------------------------------------
# multi-turn selection (metric 9) -- the check routing signatures cannot make
# --------------------------------------------------------------------------

_BASELINE_MT = {
    "id": "mt01",
    "_turns": [
        {"options": ["RAQ(Quarterly)", "RAQ(Monthly)", "RAQ(Annually)"],
         "response_text": "I found 7 matching reports. 1. RAQ(Quarterly)"},
        {"response_text": "Report 'RAQ(Monthly)' exists but no instances generated."},
    ],
}


def test_resolved_selection_prefers_the_longest_match():
    """Option names overlap: 'RAQ(Monthly)' contains 'RAQ', so a first-match
    scan would resolve the wrong one."""
    options = ["RAQ", "RAQ(Monthly)"]
    assert metrics.resolved_selection("Report 'RAQ(Monthly)' exists", options) == "RAQ(Monthly)"


def test_selection_match_passes_when_same_option_resolved():
    result = metrics.selection_match(
        _BASELINE_MT, "Report 'RAQ(Monthly)' exists but no instances generated."
    )
    assert result["selection_ok"]
    assert result["expected_selection"] == "RAQ(Monthly)"


def test_selection_match_catches_a_wrong_option_with_identical_routing():
    """The whole reason this metric exists: both runs end in get_status/error,
    so the routing signature matches -- but a different report was selected."""
    result = metrics.selection_match(
        _BASELINE_MT, "Report 'RAQ(Annually)' exists but no instances generated."
    )
    assert not result["selection_ok"]
    assert result["expected_selection"] == "RAQ(Monthly)"
    assert result["actual_selection"] == "RAQ(Annually)"


def test_selection_match_flags_a_lost_selection():
    result = metrics.selection_match(_BASELINE_MT, "I could not find that report.")
    assert not result["selection_ok"]
    assert result["actual_selection"] is None


def test_selection_match_is_none_for_single_turn_cases():
    assert metrics.selection_match({"id": "st01", "_turns": []}, "anything") is None
