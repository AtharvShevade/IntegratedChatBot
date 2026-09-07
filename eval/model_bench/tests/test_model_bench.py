"""Tests for the benchmark's own logic. No network: a benchmark whose scorer
is wrong produces confident nonsense, which is worse than no benchmark.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from eval.model_bench import scoring
from eval.model_bench.client import _lenient
from eval.model_bench.dataset import load_cases

FULL = {k: None for k in scoring.SCHEMA_KEYS}


def _result(parsed, ok=True, strict=True, ms=100.0):
    return {"ok": ok, "latency_ms": ms, "error": None if ok else "boom",
            "strict_json_ok": strict, "raw": "", "parsed": parsed}


# -- dataset -----------------------------------------------------------------

def test_every_case_is_labelled_and_multi_turn_excluded():
    cases = load_cases()
    assert len(cases) == 56
    assert all("grade" in c and c["query"] for c in cases)
    assert not any(c["id"].startswith("mt") for c in cases)


def test_only_strict_cases_carry_an_expected_intent():
    for case in load_cases():
        if case["grade"] == "gap":
            assert "intent" not in case, case["id"] + " invents an answer for a gap case"


def test_every_strict_intent_is_in_the_production_taxonomy():
    for case in load_cases():
        if case["grade"] == "strict":
            assert case["intent"] in scoring.VALID_INTENTS, case["id"]


def test_labels_cover_exactly_the_dataset():
    path = Path(scoring.__file__).parent / "labels.json"
    labels = json.loads(path.read_text(encoding="utf-8"))
    ids = {c["id"] for c in load_cases()}
    assert {k for k in labels if not k.startswith("_")} == ids


# -- entity normalisation ----------------------------------------------------

@pytest.mark.parametrize("a,b", [("CIMS_ROR", "cims ror"), ("CIMS_ROR", "cims-ror"),
                                 ("DBR01", "dbr01"), ("RAQ", "raq")])
def test_separators_and_case_do_not_count_as_entity_errors(a, b):
    assert scoring._norm(a) == scoring._norm(b)


def test_different_reports_are_not_folded_together():
    assert scoring._norm("CIMS_ROR") != scoring._norm("CIMS_RAQ")


# -- scoring -----------------------------------------------------------------

def test_ambiguous_and_gap_cases_are_recorded_but_never_scored():
    for grade in ("ambiguous", "gap"):
        case = {"id": "x", "category": "c", "grade": grade, "query": "q", "intent": "unknown"}
        row = scoring.score_case(case, _result({**FULL, "intent": "get_status"}))
        assert row["intent_correct"] is None
        assert row["intent"] == "get_status"          # still captured for review


def test_strict_case_is_scored_on_intent_and_entity():
    case = {"id": "x", "category": "status", "grade": "strict", "query": "status of RAQ",
            "intent": "get_status", "report_name": "RAQ"}
    good = scoring.score_case(case, _result({**FULL, "intent": "get_status",
                                             "report_name": "raq"}))
    assert good["intent_correct"] and good["report_name_correct"]
    bad = scoring.score_case(case, _result({**FULL, "intent": "generate_instance",
                                            "report_name": "DBR01"}))
    assert bad["intent_correct"] is False and bad["report_name_correct"] is False


def test_report_name_is_not_graded_when_the_label_omits_it():
    case = {"id": "x", "category": "c", "grade": "strict", "query": "q", "intent": "get_status"}
    row = scoring.score_case(case, _result({**FULL, "intent": "get_status",
                                            "report_name": "whatever"}))
    assert row["report_name_correct"] is None


def test_dates_are_graded_on_presence_not_wording():
    case = {"id": "x", "category": "generate", "grade": "strict",
            "query": "generate RAQ for q1", "intent": "generate_instance",
            "reporting_date": "*"}
    for text in ("q1", "Q1 2025", "2025-03-31"):
        row = scoring.score_case(case, _result({**FULL, "intent": "generate_instance",
                                                "reporting_date": text}))
        assert row["dates_correct"]
    missing = scoring.score_case(case, _result({**FULL, "intent": "generate_instance"}))
    assert missing["dates_correct"] is False


def test_a_date_invented_where_none_was_asked_for_is_wrong():
    case = {"id": "x", "category": "generate", "grade": "strict", "query": "run raq now",
            "intent": "generate_instance", "reporting_date": None}
    row = scoring.score_case(case, _result({**FULL, "intent": "generate_instance",
                                            "reporting_date": "31-03-2025"}))
    assert row["dates_correct"] is False


def test_hallucination_means_an_entity_absent_from_the_query():
    case = {"id": "x", "category": "conversational", "grade": "strict", "query": "hello",
            "intent": "unknown", "report_name": None}
    invented = scoring.score_case(case, _result({**FULL, "intent": "unknown",
                                                 "report_name": "CIMS_ROR"}))
    assert invented["hallucinated_entity"]
    clean = scoring.score_case(case, _result({**FULL, "intent": "unknown"}))
    assert not clean["hallucinated_entity"]


def test_an_entity_present_in_the_query_is_not_a_hallucination():
    case = {"id": "x", "category": "status", "grade": "strict",
            "query": "status of cims ror", "intent": "get_status",
            "report_name": "CIMS_ROR"}
    row = scoring.score_case(case, _result({**FULL, "intent": "get_status",
                                            "report_name": "CIMS_ROR"}))
    assert not row["hallucinated_entity"]


def test_an_intent_outside_the_taxonomy_is_flagged():
    case = {"id": "x", "category": "c", "grade": "strict", "query": "q", "intent": "unknown"}
    row = scoring.score_case(case, _result({**FULL, "intent": "explain_errors"}))
    assert row["valid_intent"] is False


def test_a_failed_call_scores_nothing_but_is_counted():
    case = {"id": "x", "category": "c", "grade": "strict", "query": "q", "intent": "unknown"}
    row = scoring.score_case(case, _result(None, ok=False, strict=False))
    assert row["failed"] and row["intent_correct"] is None


# -- aggregation -------------------------------------------------------------

def test_aggregate_counts_only_graded_cases_in_accuracy():
    case_s = {"id": "a", "category": "c", "grade": "strict", "query": "q", "intent": "unknown"}
    case_g = {"id": "b", "category": "c", "grade": "gap", "query": "q"}
    rows = [scoring.score_case(case_s, _result({**FULL, "intent": "unknown"})),
            scoring.score_case(case_g, _result({**FULL, "intent": "get_status"}))]
    agg = scoring.aggregate(rows)
    assert agg["cases"] == 2 and agg["intent_graded"] == 1
    assert agg["intent_accuracy_pct"] == 100.0


def test_prod_parse_rate_falls_when_json_is_fenced():
    case = {"id": "a", "category": "c", "grade": "strict", "query": "q", "intent": "unknown"}
    rows = [scoring.score_case(case, _result({**FULL, "intent": "unknown"}, strict=s))
            for s in (True, False)]
    agg = scoring.aggregate(rows)
    assert agg["prod_parse_ok_pct"] == 50.0
    assert agg["intent_accuracy_pct"] == 100.0        # content still right


def test_latency_percentiles_ignore_failed_calls():
    case = {"id": "a", "category": "c", "grade": "strict", "query": "q", "intent": "unknown"}
    rows = [scoring.score_case(case, _result({**FULL, "intent": "unknown"}, ms=ms))
            for ms in (100.0, 200.0, 300.0)]
    rows.append(scoring.score_case(case, _result(None, ok=False, ms=99999.0)))
    agg = scoring.aggregate(rows)
    assert agg["median_ms"] == 200.0 and agg["max_ms"] == 300.0
    assert agg["failures"] == 1


def test_empty_input_does_not_divide_by_zero():
    agg = scoring.aggregate([])
    assert agg["cases"] == 0 and agg["intent_accuracy_pct"] is None


# -- lenient JSON recovery ---------------------------------------------------

def test_fenced_json_is_recovered():
    fenced = "```json\n{\"intent\": \"get_status\"}\n```"
    assert _lenient(fenced) == {"intent": "get_status"}


def test_prose_padded_json_is_recovered():
    assert _lenient('Sure! {"intent": "unknown"} hope that helps') == {"intent": "unknown"}


def test_unrecoverable_output_returns_none():
    assert _lenient("I cannot answer that.") is None


def test_an_object_wrapped_in_an_array_is_still_recovered():
    # Array brackets are packaging, and the lenient path exists to look past
    # packaging. Production would still reject this -- strict_json_ok records
    # that separately -- so nothing is being hidden by recovering it here.
    assert _lenient('[{"intent": "unknown"}]') == {"intent": "unknown"}


def test_a_genuinely_shapeless_body_returns_none():
    assert _lenient('[{"a": 1}, {"b": 2}] and more') is None


# -- production routing replay -----------------------------------------------

def test_prod_intent_whitelist_matches_llm_extractor():
    """prod_view models llm_extractor.py. If that file's whitelist changes,
    this benchmark starts reporting a routing accuracy that is fiction."""
    from eval.model_bench import prod_view
    src = (Path(__file__).resolve().parents[3] / "backend" / "llm_extractor.py").read_text("utf-8")
    line = next(l for l in src.splitlines() if "_valid_intents" in l and "{" in l)
    found = set(re.findall(r'"([a-z_]+)"', line))
    assert found == prod_view.PROD_INTENTS


def test_compare_queries_never_reach_the_model():
    from eval.model_bench import prod_view
    got, who = prod_view.route("compare cims instances", strict_json_ok=False, intent=None)
    assert got == "compare_reports" and "regex" in who


def test_a_parse_failure_silently_becomes_unknown_not_an_error():
    from eval.model_bench import prod_view
    got, who = prod_view.route("what is the status of RAQ", False, "get_status")
    assert got == "unknown" and "parse failure" in who


def test_db_intents_are_collapsed_because_production_rejects_them():
    from eval.model_bench import prod_view
    got, _ = prod_view.route("what is my role", True, "db_my_role")
    assert got == "unknown"
    assert prod_view.expected("db_my_role") == "unknown"


def test_a_good_intent_survives_when_json_parses():
    from eval.model_bench import prod_view
    got, who = prod_view.route("run raq now", True, "generate_instance")
    assert got == "generate_instance" and who == "model"
