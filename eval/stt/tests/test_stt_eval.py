"""Tests for the STT evaluation harness.

None of these touch the network. A benchmark whose own scoring is wrong is
worse than no benchmark, because it produces confident numbers, so the metrics
are tested against cases where the right answer is arithmetic rather than
opinion.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval.stt import client, config, dataset, metrics, report, run_eval


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def test_normalization_is_case_and_punctuation_insensitive():
    assert metrics.normalize("Hello, World!") == metrics.normalize("hello world")


def test_normalization_unifies_digit_shapes():
    """Devanagari and Arabic-Indic digits must compare equal to ASCII, or CER
    for Hindi and Arabic would be dominated by digit rendering."""
    assert metrics.normalize("31", "hi") == metrics.normalize("३१", "hi")
    assert metrics.normalize("31", "ar") == metrics.normalize("٣١", "ar")


def test_normalization_strips_arabic_diacritics():
    assert metrics.normalize("مَرْحَبًا", "ar") == metrics.normalize("مرحبا", "ar")


def test_devanagari_danda_is_punctuation():
    assert metrics.normalize("नमस्ते।", "hi") == metrics.normalize("नमस्ते", "hi")


def test_normalization_does_not_destroy_content():
    assert metrics.normalize("CIMS_ROR", "en") == "cims_ror"


# ---------------------------------------------------------------------------
# WER / CER
# ---------------------------------------------------------------------------

def test_wer_is_zero_for_an_exact_match():
    assert metrics.wer("what is the status", "what is the status") == 0.0


def test_wer_counts_one_substitution_in_four_words():
    assert metrics.wer("what is the status", "what is the state") == pytest.approx(25.0)


def test_wer_counts_deletions_and_insertions():
    assert metrics.wer("a b c d", "a b c") == pytest.approx(25.0)      # 1 deletion
    assert metrics.wer("a b c d", "a b c d e") == pytest.approx(25.0)  # 1 insertion


def test_wer_is_none_without_a_reference():
    """No reference means no score -- never a zero, which would read as perfect."""
    assert metrics.wer("", "anything") is None


def test_cer_is_zero_for_an_exact_match():
    assert metrics.cer("मुझे स्थिति चाहिए", "मुझे स्थिति चाहिए", "hi") == 0.0


def test_cer_ignores_word_segmentation():
    """Devanagari and Arabic may be written joined or split for the same
    utterance; CER must not punish that."""
    assert metrics.cer("नमस्ते दुनिया", "नमस्तेदुनिया", "hi") == 0.0


def test_cer_counts_a_single_character_error():
    # 4 reference characters, one substituted.
    assert metrics.cer("abcd", "abce", "en") == pytest.approx(25.0)


def test_headline_metric_per_language():
    assert metrics.headline_metric("en") == "wer"
    assert metrics.headline_metric("fr") == "wer"
    assert metrics.headline_metric("hi") == "cer"
    assert metrics.headline_metric("ar") == "cer"


# ---------------------------------------------------------------------------
# Entity preservation
# ---------------------------------------------------------------------------

def test_entities_are_found_by_the_apps_own_definition():
    found = metrics.entities_in("status of CIMS_ROR on 31-Mar-2026")
    assert "CIMS_ROR" in found
    assert "31-Mar-2026" in found


def test_entity_preservation_is_exact_not_fuzzy():
    """The whole point: 'cims ror' will not match a report name downstream, so
    it must not score as preserved."""
    result = metrics.entity_preservation("status of CIMS_ROR", "status of cims ror")
    assert result["pct"] == 0.0
    assert result["missing"] == ["CIMS_ROR"]


def test_entity_preservation_full_marks_when_carried_through():
    result = metrics.entity_preservation("status of CIMS_ROR", "the status of CIMS_ROR please")
    assert result["pct"] == 100.0
    assert result["missing"] == []


def test_entity_preservation_uses_declared_entities_when_given():
    result = metrics.entity_preservation("anything at all", "R009 is here",
                                         declared=["R009", "R149"])
    assert result["total"] == 2
    assert result["preserved"] == 1
    assert result["missing"] == ["R149"]


def test_entity_preservation_is_none_when_there_are_no_entities():
    """No entities means no opinion -- not 100%, which would inflate the pool."""
    assert metrics.entity_preservation("hello there", "hello there")["pct"] is None


def test_repeated_entity_counts_once():
    result = metrics.entity_preservation("R009 and R009", "nothing", declared=["R009", "R009"])
    assert result["total"] == 1


# ---------------------------------------------------------------------------
# Translation leakage
# ---------------------------------------------------------------------------

def test_hindi_transcribed_as_english_is_a_leak():
    assert metrics.translation_leak(
        "मुझे अपने रिपोर्ट का स्टेटस जानना है",
        "I want to know the status of my report", "hi") is True


def test_hindi_kept_in_devanagari_is_not_a_leak():
    assert metrics.translation_leak(
        "मुझे अपने रिपोर्ट का स्टेटस जानना है",
        "मुझे अपने रिपोर्ट का स्टेटस जानना है", "hi") is False


def test_code_switched_hindi_is_not_a_leak():
    """English nouns inside Devanagari are normal and correct -- exactly the
    output we want for 'मुझे अपने CIMS_ROR report का status जानना है'."""
    assert metrics.translation_leak(
        "मुझे अपने CIMS_ROR report का status जानना है",
        "मुझे अपने CIMS_ROR report का status जानना है", "hi") is False


def test_arabic_transcribed_as_english_is_a_leak():
    assert metrics.translation_leak(
        "أريد معرفة حالة التقرير الخاص بي",
        "I want to know the status of my report", "ar") is True


def test_french_translated_to_english_is_a_leak():
    assert metrics.translation_leak(
        "Je voudrais connaître le statut de mon rapport",
        "I would like to know the status of my report", "fr") is True


def test_french_kept_in_french_is_not_a_leak():
    assert metrics.translation_leak(
        "Je voudrais connaître le statut de mon rapport",
        "Je voudrais connaître le statut de mon rapport", "fr") is False


def test_english_has_nothing_to_leak_to():
    assert metrics.translation_leak("hello", "hello", "en") is None


def test_empty_transcript_is_not_scored_as_a_leak():
    """Silence is a hallucination question, not a translation question."""
    assert metrics.translation_leak("मुझे स्थिति चाहिए", "", "hi") is None


# ---------------------------------------------------------------------------
# Hallucination
# ---------------------------------------------------------------------------

def test_words_on_a_silent_clip_are_a_hallucination():
    """Reproduces the measured behaviour: silence returned "You"."""
    assert metrics.is_hallucination("You", "silence") is True
    assert metrics.is_hallucination("Thank you.", "noise") is True


def test_empty_output_on_silence_is_correct():
    assert metrics.is_hallucination("", "silence") is False
    assert metrics.is_hallucination("   ", "silence") is False


def test_punctuation_only_is_not_a_hallucination():
    """A lone full stop carries no words; counting it would make the metric
    unreachable and therefore useless."""
    assert metrics.is_hallucination(".", "silence") is False


def test_hallucination_does_not_apply_to_speech_clips():
    assert metrics.is_hallucination("hello", "clean") is None


# ---------------------------------------------------------------------------
# RTF and latency aggregation
# ---------------------------------------------------------------------------

def test_rtf_is_processing_over_audio():
    assert metrics.rtf(2500, 5.0) == pytest.approx(0.5)


def test_rtf_needs_both_numbers():
    assert metrics.rtf(None, 5.0) is None
    assert metrics.rtf(2500, None) is None


def test_latency_aggregation_splits_cold_from_warm():
    records = [
        {"audio_seconds": 5, "latency_ms": 14000, "cold": True},
        {"audio_seconds": 5, "latency_ms": 2000, "cold": False},
        {"audio_seconds": 5, "latency_ms": 2200, "cold": False},
    ]
    out = metrics.aggregate_latency(records)
    assert out["5"]["cold_ms"]["p50"] == 14000
    assert out["5"]["warm_ms"]["p50"] == 2100
    assert out["5"]["n"] == 3


def test_latency_aggregation_ignores_the_meta_line():
    out = metrics.aggregate_latency([{"_meta": True, "config": {}},
                                     {"audio_seconds": 1, "latency_ms": 100}])
    assert list(out) == ["1"]


# ---------------------------------------------------------------------------
# Roll-up
# ---------------------------------------------------------------------------

def _clip_record(**kw):
    base = {"language": "en", "condition": "clean", "wer": 10.0, "cer": 5.0,
            "latency_ms": 1000, "entity_total": 0, "entity_preserved": 0}
    base.update(kw)
    return base


def test_aggregate_pools_entities_rather_than_averaging_clips():
    """A clip with six identifiers must weigh more than a clip with one."""
    records = [
        _clip_record(entity_total=6, entity_preserved=3),
        _clip_record(entity_total=1, entity_preserved=1),
    ]
    summary = metrics.aggregate(records)
    assert summary["entity_total"] == 7
    assert summary["entity_preserved"] == 4
    assert summary["entity_preservation"] == pytest.approx(100.0 * 4 / 7)


def test_aggregate_splits_headline_accuracy_by_language_group():
    records = [
        _clip_record(language="en", wer=10.0),
        _clip_record(language="fr", wer=20.0),
        _clip_record(language="hi", cer=8.0),
        _clip_record(language="ar", cer=12.0),
    ]
    summary = metrics.aggregate(records)
    assert summary["wer_en_fr_pct"] == pytest.approx(15.0)
    assert summary["cer_hi_ar_pct"] == pytest.approx(10.0)


def test_aggregate_excludes_errored_clips():
    records = [_clip_record(), _clip_record(error="timeout")]
    summary = metrics.aggregate(records)
    assert summary["clips_scored"] == 1
    assert summary["clips_errored"] == 1


def test_aggregate_percentages_are_over_decidable_clips_only():
    records = [
        _clip_record(translation_leak=True),
        _clip_record(translation_leak=False),
        _clip_record(translation_leak=None),   # English: not decidable
    ]
    summary = metrics.aggregate(records)
    assert summary["translation_leak_n"] == 2
    assert summary["translation_leak_pct"] == pytest.approx(50.0)


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------

def test_planned_dataset_matches_the_specification():
    clips = dataset.planned_clips()
    assert len(clips) == 74, "48 core + 10 code-switch + 10 entity + 6 robustness"
    for lang in ("en", "fr", "ar", "hi"):
        assert len([c for c in clips if c.language == lang and
                    c.id.startswith(f"{lang}_")]) == 12
    assert len([c for c in clips if c.condition == "codeswitch"]) == 10
    assert len([c for c in clips if c.id.startswith("rob_")]) == 6


def test_template_has_no_invented_transcripts():
    """The single most important property of the generator."""
    for clip in dataset.planned_clips():
        assert clip.reference_text == ""
        assert clip.entities == []


def test_speech_clips_are_not_scorable_without_a_reference():
    clip = dataset.Clip(id="x", audio_file="x.wav", language="en", condition="clean")
    assert clip.scorable is False
    clip.reference_text = "hello"
    assert clip.scorable is True


def test_non_speech_clips_are_scorable_with_no_transcript():
    """Silence has no transcript; saying nothing is precisely the pass."""
    clip = dataset.Clip(id="s", audio_file="s.wav", language="en", condition="silence")
    assert clip.scorable is True


def test_manifest_roundtrip(tmp_path):
    path = tmp_path / "manifest.jsonl"
    dataset.generate_manifest(path)
    clips = dataset.load(path)
    assert len(clips) == 74
    assert clips[0].id


def test_generate_refuses_to_clobber_hand_typed_work(tmp_path):
    path = tmp_path / "manifest.jsonl"
    dataset.generate_manifest(path)
    path.write_text('{"id":"a","audio_file":"a.wav","language":"en",'
                    '"condition":"clean","reference_text":"typed by hand"}\n',
                    encoding="utf-8")
    with pytest.raises(FileExistsError):
        dataset.generate_manifest(path)
    assert "typed by hand" in path.read_text(encoding="utf-8")
    dataset.generate_manifest(path, overwrite=True)      # explicit opt-in
    assert "typed by hand" not in path.read_text(encoding="utf-8")


def test_loader_rejects_a_duplicate_id(tmp_path):
    path = tmp_path / "m.jsonl"
    row = '{"id":"a","audio_file":"a.wav","language":"en","condition":"clean"}'
    path.write_text(row + "\n" + row + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate id"):
        dataset.load(path)


def test_loader_rejects_unknown_language_and_condition(tmp_path):
    path = tmp_path / "m.jsonl"
    path.write_text('{"id":"a","audio_file":"a.wav","language":"de","condition":"clean"}\n',
                    encoding="utf-8")
    with pytest.raises(ValueError, match="unknown language"):
        dataset.load(path)
    path.write_text('{"id":"a","audio_file":"a.wav","language":"en","condition":"weird"}\n',
                    encoding="utf-8")
    with pytest.raises(ValueError, match="unknown condition"):
        dataset.load(path)


def test_loader_reports_a_missing_field(tmp_path):
    path = tmp_path / "m.jsonl"
    path.write_text('{"id":"a","language":"en","condition":"clean"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="missing required field"):
        dataset.load(path)


def test_status_counts_what_actually_exists(tmp_path):
    clips = [
        dataset.Clip(id="a", audio_file="a.wav", language="en", condition="clean",
                     reference_text="hello"),
        dataset.Clip(id="b", audio_file="b.wav", language="en", condition="clean"),
    ]
    state = dataset.status(clips)
    assert state["clips"] == 2
    assert state["with_reference"] == 1
    assert state["ready_to_score"] == 0          # no audio on disk
    assert "b" in state["missing_reference"]


# ---------------------------------------------------------------------------
# Checkpointing and config stamping
# ---------------------------------------------------------------------------

def test_resume_skips_ids_already_written(tmp_path):
    path = tmp_path / "out.jsonl"
    run_eval._append(path, {"id": "lat_5s_1"})
    run_eval._append(path, {"id": "lat_5s_2"})
    assert run_eval._load_ids(path) == {"lat_5s_1", "lat_5s_2"}


def test_load_ids_survives_a_truncated_final_line(tmp_path):
    """A run killed mid-write must still resume -- that is the whole point."""
    path = tmp_path / "out.jsonl"
    path.write_text('{"id": "a"}\n{"id": "b"}\n{"id": "trunc', encoding="utf-8")
    assert run_eval._load_ids(path) == {"a", "b"}


def test_load_ids_on_a_missing_file_is_empty(tmp_path):
    assert run_eval._load_ids(tmp_path / "nope.jsonl") == set()


def test_run_config_stamps_everything_needed_to_tell_runs_apart(monkeypatch):
    monkeypatch.setenv("EVAL_STT_MODEL", "large-v3")
    monkeypatch.setenv("EVAL_STT_RUNTIME", "faster-whisper")
    monkeypatch.setenv("EVAL_STT_COMPUTE_TYPE", "int8")
    monkeypatch.setenv("EVAL_STT_CPU_THREADS", "8")
    cfg = config.run_config()
    assert cfg["model"] == "large-v3"
    assert cfg["runtime"] == "faster-whisper"
    assert cfg["compute_type"] == "int8"
    assert cfg["cpu_threads"] == "8"
    assert cfg["base_url"]


def test_cli_flags_override_config(monkeypatch, tmp_path):
    monkeypatch.setattr(run_eval.dataset, "generate_manifest", lambda p, overwrite: tmp_path / "m.jsonl")
    monkeypatch.setattr(run_eval.dataset, "load", lambda p: [])
    run_eval.main(["--init-dataset", "--model", "medium", "--compute-type", "int8"])
    assert config.model() == "medium"
    assert config.compute_type() == "int8"


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def test_missing_data_is_not_measured_never_pass():
    """The most dangerous possible bug in this file."""
    assert report.grade("wer_en_fr_pct", None) == "NOT MEASURED"
    assert report.grade("hallucination_pct", None) == "NOT MEASURED"


def test_grading_respects_direction():
    assert report.grade("wer_en_fr_pct", 10.0) == "PASS"      # <= 15
    assert report.grade("wer_en_fr_pct", 20.0) == "FAIL"
    assert report.grade("entity_preservation", 97.0) == "PASS"  # >= 95
    assert report.grade("entity_preservation", 90.0) == "FAIL"


def test_hallucination_target_is_exactly_zero():
    assert report.grade("hallucination_pct", 0.0) == "PASS"
    assert report.grade("hallucination_pct", 0.1) == "FAIL"


def test_acceptance_table_covers_every_criterion():
    rows = report.acceptance_rows({}, {})
    assert len(rows) == len(config.ACCEPTANCE)
    assert all(r[3] == "NOT MEASURED" for r in rows)


def test_report_on_an_empty_results_dir_says_not_measured(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "RESULTS_DIR", tmp_path)
    text = report.build_report("nothing")
    assert "NOT MEASURED" in text
    assert "Overall: INCOMPLETE" in text
    assert "has **not** passed" in text


def test_report_renders_latency_and_flags_missing_server_timing(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "RESULTS_DIR", tmp_path)
    path = tmp_path / "m_latency.jsonl"
    rows = [{"_meta": True, "config": {"model": "m", "base_url": "u"}, "health": {}}]
    rows += [{"id": f"lat_5s_{i}", "audio_seconds": 5, "latency_ms": 14000,
              "cold": i == 1} for i in (1, 2, 3)]
    path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    text = report.build_report("m")
    assert "## Latency" in text
    assert "does not report" in text, "must say network and compute cannot be separated"


# ---------------------------------------------------------------------------
# Synthetic audio helper
# ---------------------------------------------------------------------------

def test_tone_wav_has_the_requested_duration(tmp_path):
    path = client.make_tone_wav(2, tmp_path / "t.wav")
    assert client.wav_duration(path) == pytest.approx(2.0, abs=0.01)


def test_wav_duration_returns_none_for_a_non_wav(tmp_path):
    path = tmp_path / "x.webm"
    path.write_bytes(b"not a wav")
    assert client.wav_duration(path) is None


# ---------------------------------------------------------------------------
# Whisper model selection (eval/stt/service_reference/model_config.py)
#
# Tested through the standalone module rather than the service: importing
# app_instrumented calls WhisperModel(...) at import time, which downloads
# ~1.5 GB and takes minutes. Validation must be checkable in milliseconds.
# ---------------------------------------------------------------------------

def _model_config():
    """Import the service-side validator without importing the service."""
    import importlib.util
    from eval.stt import config as stt_cfg
    path = stt_cfg.PACKAGE_DIR / "service_reference" / "model_config.py"
    spec = importlib.util.spec_from_file_location("stt_model_config", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_default_model_is_large_v3_turbo(monkeypatch):
    """Production default must not move. The whole point of making the model
    switchable was to benchmark, not to change what ships."""
    mc = _model_config()
    monkeypatch.delenv("WHISPER_MODEL", raising=False)
    assert mc.resolve_model() == "large-v3-turbo"
    assert mc.DEFAULT_MODEL == "large-v3-turbo"


def test_empty_or_whitespace_falls_back_to_the_default(monkeypatch):
    """An unset variable in a .env file often arrives as "" rather than absent."""
    mc = _model_config()
    for value in ("", "   "):
        monkeypatch.setenv("WHISPER_MODEL", value)
        assert mc.resolve_model() == "large-v3-turbo"


def test_medium_is_selected_when_configured(monkeypatch):
    mc = _model_config()
    monkeypatch.setenv("WHISPER_MODEL", "medium")
    assert mc.resolve_model() == "medium"


def test_large_v3_is_selected_when_configured(monkeypatch):
    mc = _model_config()
    monkeypatch.setenv("WHISPER_MODEL", "large-v3")
    assert mc.resolve_model() == "large-v3"


def test_surrounding_whitespace_is_tolerated(monkeypatch):
    mc = _model_config()
    monkeypatch.setenv("WHISPER_MODEL", "  medium  ")
    assert mc.resolve_model() == "medium"


@pytest.mark.parametrize("bad", ["medum", "large-v2", "small", "tiny", "Medium",
                                 "openai/whisper-medium", "large-v3-turbo "  + "x"])
def test_unsupported_values_are_rejected_before_the_model_loads(monkeypatch, bad):
    """faster-whisper treats an unknown name as a HuggingFace repo id, so
    without this a typo dies seconds later inside the library with an HTTP 401
    that never mentions the typo. Case-sensitive on purpose: 'Medium' is not a
    real model id, and silently accepting it would hide a config error."""
    mc = _model_config()
    monkeypatch.setenv("WHISPER_MODEL", bad)
    with pytest.raises(mc.UnsupportedModelError) as excinfo:
        mc.resolve_model()
    message = str(excinfo.value)
    assert bad.strip() in message, "the error must quote the offending value"
    assert "large-v3-turbo" in message and "large-v3" in message and "medium" in message, \
        "the error must name the allowed values"


def test_explicit_argument_beats_the_environment(monkeypatch):
    """Lets a caller (and these tests) validate without touching os.environ."""
    mc = _model_config()
    monkeypatch.setenv("WHISPER_MODEL", "large-v3-turbo")
    assert mc.resolve_model("medium") == "medium"


def test_supported_set_is_exactly_the_three_benchmark_models():
    mc = _model_config()
    assert mc.SUPPORTED_MODELS == ("large-v3-turbo", "large-v3", "medium")


def test_only_the_model_is_configurable_by_this_module():
    """Guards requirement 8: beam size, threads, VAD and quantization must NOT
    have become switchable as a side effect of this change."""
    mc = _model_config()
    source = (mc.__file__ and open(mc.__file__, encoding="utf-8").read()) or ""
    for setting in ("BEAM", "CPU_THREADS", "COMPUTE_TYPE", "VAD", "DEVICE"):
        assert setting not in source, f"{setting} must not be handled here"
