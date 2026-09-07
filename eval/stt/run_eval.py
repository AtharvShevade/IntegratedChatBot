"""STT benchmark runner.

    # one-time: write the dataset TEMPLATE, then record audio + type transcripts
    python -m eval.stt.run_eval --init-dataset
    python -m eval.stt.run_eval --dataset-status

    # latency sweep -- works TODAY, needs no dataset
    python -m eval.stt.run_eval --latency

    # accuracy -- needs real recordings and hand-typed transcripts
    python -m eval.stt.run_eval --accuracy --resume
    python -m eval.stt.run_eval --accuracy --lang hi

    python -m eval.stt.report

Results are JSONL under eval/stt/results/, one object per clip, with a
``{"_meta": True, "config": {...}}`` first line -- the same shape and the same
--resume checkpointing as eval/multilingual, so a run killed halfway loses
nothing and two result files can always be told apart afterwards.
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from eval.stt import client, config, dataset, metrics


# ---------------------------------------------------------------------------
# Result files -- conventions copied from eval/multilingual/run_eval.py
# ---------------------------------------------------------------------------

def _slug(text: str) -> str:
    return text.replace(":", "-").replace("/", "-").replace(" ", "_")


def _result_path(kind: str, tag: str = "") -> Path:
    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    suffix = f"_{tag}" if tag else ""
    return config.RESULTS_DIR / f"{_slug(config.model())}_{kind}{suffix}.jsonl"


def _append(path: Path, record: dict) -> None:
    with open(path, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def _load_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    seen: set[str] = set()
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("id"):
                seen.add(record["id"])
    return seen


def _write_meta(path: Path, extra: dict) -> None:
    """First line of every result file. Without it two runs are
    indistinguishable a week later and the comparison is worthless."""
    _append(path, {
        "_meta": True,
        "config": config.run_config(),
        "health": client.health(),
        "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "host": {"platform": platform.platform(), "python": sys.version.split()[0]},
        **extra,
    })


def _verify_health() -> dict:
    """Cross-check the configured model against what the service reports.

    The harness cannot configure the remote service, so EVAL_STT_MODEL is a
    label. If it disagrees with /health the results are mislabelled, which is
    worse than having no label at all -- so say so loudly.
    """
    reported = client.health()
    configured = config.model()
    actual = reported.get("model")
    if actual and configured and actual != configured:
        print(f"  WARNING: EVAL_STT_MODEL={configured!r} but /health reports "
              f"{actual!r}. Results would be mislabelled.")
    if reported.get("error"):
        print(f"  WARNING: /health unreachable: {reported['error']}")
    return reported


# ---------------------------------------------------------------------------
# Latency sweep -- no dataset required
# ---------------------------------------------------------------------------

def run_latency(durations=None, repeats: int | None = None,
                resume: bool = False) -> Path:
    """Time the service across audio lengths.

    Uses synthetic tones, NOT speech: this answers "what does N seconds of
    audio cost" -- fixed overhead and encoder windows -- and deliberately not
    "how accurate is it". No WER is computed here and none should be.

    The first call at each duration is marked cold=True and reported
    separately, because a service that reloads its model per request has no
    warm path at all and that difference is the headline finding.
    """
    durations = durations or config.LATENCY_DURATIONS
    repeats = repeats or config.LATENCY_REPEATS
    path = _result_path("latency")
    done = _load_ids(path) if resume else set()
    if not resume and path.exists():
        path.unlink()
    if not done:
        _write_meta(path, {"kind": "latency", "durations": list(durations),
                           "repeats": repeats, "audio": "synthetic tone (not speech)"})

    print(f"Latency sweep -> {path.name}")
    _verify_health()
    tmp = config.RESULTS_DIR / "_tone"

    for seconds in durations:
        wav = client.make_tone_wav(seconds, tmp / f"tone_{seconds}s.wav")
        audio = wav.read_bytes()
        for attempt in range(1, repeats + 1):
            case_id = f"lat_{seconds}s_{attempt}"
            if case_id in done:
                continue
            response = client.transcribe(audio, f"tone_{seconds}s.wav")
            record = {
                "id": case_id,
                "kind": "latency",
                "audio_seconds": seconds,
                "attempt": attempt,
                "cold": attempt == 1,
                "ok": response.ok,
                "latency_ms": round(response.latency_ms, 1),
                "processing_ms": response.processing_ms,
                "rtf": metrics.rtf(response.processing_ms or response.latency_ms, seconds),
                "text": response.text,
                "language": response.language,
                "language_probability": response.language_probability,
                "status_code": response.status_code,
                "error": response.error,
            }
            _append(path, record)
            state = "cold" if record["cold"] else "warm"
            print(f"  {seconds:>3}s [{attempt}/{repeats}] {state:4s} "
                  f"{response.latency_ms/1000:6.2f}s  rtf={record['rtf'] or 0:.2f}  "
                  f"{'OK' if response.ok else 'FAIL: ' + str(response.error)[:40]}")

    for leftover in tmp.glob("*.wav"):
        leftover.unlink()
    if tmp.exists():
        tmp.rmdir()
    return path


# ---------------------------------------------------------------------------
# Accuracy -- requires real recordings
# ---------------------------------------------------------------------------

def run_accuracy(manifest: Path | None = None, lang: str | None = None,
                 resume: bool = False, limit: int | None = None) -> Path:
    """Transcribe every ready clip and score it.

    A clip is skipped, loudly, if its audio is missing or it has no hand-typed
    reference. Scoring a clip against an empty reference would produce a
    number, and that number would be meaningless.
    """
    clips = dataset.load(manifest)
    if lang:
        clips = [c for c in clips if c.language == lang]

    ready = [c for c in clips if c.audio_path().exists() and c.scorable]
    skipped = [c for c in clips if c not in ready]
    if limit:
        ready = ready[:limit]

    tag = lang or "all"
    path = _result_path("accuracy", tag)
    done = _load_ids(path) if resume else set()
    if not resume and path.exists():
        path.unlink()
    if not done:
        _write_meta(path, {"kind": "accuracy", "language_filter": lang,
                           "clips_total": len(clips), "clips_ready": len(ready),
                           "clips_skipped": len(skipped)})

    print(f"Accuracy run -> {path.name}")
    _verify_health()
    if skipped:
        print(f"  SKIPPING {len(skipped)} clip(s) with no audio or no reference "
              f"transcript: {', '.join(c.id for c in skipped[:6])}"
              f"{' ...' if len(skipped) > 6 else ''}")
    if not ready:
        print("  NOTHING TO SCORE. Record audio and type reference transcripts first:")
        print("    python -m eval.stt.run_eval --dataset-status")
        return path

    for clip in ready:
        if clip.id in done:
            continue
        audio = clip.audio_path().read_bytes()
        # The language hint is what the PRODUCT would send: the selected UI
        # language. Measuring with auto-detect instead would measure a
        # configuration we do not ship.
        response = client.transcribe(
            audio, clip.audio_path().name, lang=clip.language,
            initial_prompt=config.initial_prompt(),
        )
        duration = clip.duration or client.wav_duration(clip.audio_path())

        record = {
            "id": clip.id,
            "kind": "accuracy",
            "language": clip.language,
            "condition": clip.condition,
            "speaker": clip.speaker,
            "audio_seconds": duration,
            "reference": clip.reference_text,
            "hypothesis": response.text,
            "detected_language": response.language,
            "language_probability": response.language_probability,
            "latency_ms": round(response.latency_ms, 1),
            "processing_ms": response.processing_ms,
            "rtf": metrics.rtf(response.processing_ms or response.latency_ms, duration),
            "ok": response.ok,
            "error": response.error,
        }

        if response.ok:
            record["wer"] = metrics.wer(clip.reference_text, response.text, clip.language)
            record["cer"] = metrics.cer(clip.reference_text, response.text, clip.language)
            entity = metrics.entity_preservation(
                clip.reference_text, response.text, clip.entities or None)
            record.update({
                "entity_total": entity["total"],
                "entity_preserved": entity["preserved"],
                "entity_missing": entity["missing"],
                "entity_pct": entity["pct"],
                "translation_leak": metrics.translation_leak(
                    clip.reference_text, response.text, clip.language),
                "hallucination": metrics.is_hallucination(response.text, clip.condition),
            })

        _append(path, record)
        head = metrics.headline_metric(clip.language)
        value = record.get(head)
        print(f"  {clip.id:<24s} {clip.language} {head}="
              f"{value if value is None else f'{value:5.1f}%'} "
              f"{response.latency_ms/1000:6.2f}s "
              f"{'OK' if response.ok else 'FAIL'}")

    return path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--init-dataset", action="store_true",
                        help="write the dataset TEMPLATE (no transcripts)")
    parser.add_argument("--force", action="store_true",
                        help="allow --init-dataset to overwrite an existing manifest")
    parser.add_argument("--dataset-status", action="store_true",
                        help="how many clips have audio and a reference transcript")
    parser.add_argument("--latency", action="store_true",
                        help="latency sweep with synthetic audio (no dataset needed)")
    parser.add_argument("--accuracy", action="store_true",
                        help="transcribe and score the dataset")
    parser.add_argument("--lang", choices=sorted(config.LANGUAGES),
                        help="restrict an accuracy run to one language")
    parser.add_argument("--dataset", type=Path, help="path to a manifest.jsonl")
    parser.add_argument("--durations", type=int, nargs="+",
                        help=f"latency durations in seconds (default {list(config.LATENCY_DURATIONS)})")
    parser.add_argument("--repeats", type=int,
                        help=f"repeats per duration (default {config.LATENCY_REPEATS})")
    parser.add_argument("--limit", type=int, help="only the first N clips")
    parser.add_argument("--resume", action="store_true",
                        help="skip cases already present in the output file")
    parser.add_argument("--base-url", help="override EVAL_STT_BASE_URL for this run")
    parser.add_argument("--model", help="label for the model under test (stamped into results)")
    parser.add_argument("--runtime", help="faster-whisper | transformers | whisper.cpp")
    parser.add_argument("--compute-type", help="int8 | float16 | float32")
    parser.add_argument("--cpu-threads", help="threads the service is configured with")
    args = parser.parse_args(argv)

    # CLI overrides become environment so config.run_config() stamps them.
    import os
    for flag, key in (("base_url", "EVAL_STT_BASE_URL"), ("model", "EVAL_STT_MODEL"),
                      ("runtime", "EVAL_STT_RUNTIME"), ("compute_type", "EVAL_STT_COMPUTE_TYPE"),
                      ("cpu_threads", "EVAL_STT_CPU_THREADS")):
        value = getattr(args, flag, None)
        if value:
            os.environ[key] = str(value)

    if args.init_dataset:
        try:
            path = dataset.generate_manifest(args.dataset, overwrite=args.force)
        except FileExistsError as exc:
            print(f"REFUSED: {exc}")
            return 1
        clips = dataset.load(path)
        print(f"Wrote TEMPLATE manifest: {path}  ({len(clips)} clips)")
        print("Every reference_text is EMPTY by design. Record the audio, then type")
        print("what was actually said into reference_text. See eval/stt/README.md.")
        return 0

    if args.dataset_status:
        clips = dataset.load(args.dataset)
        state = dataset.status(clips)
        print(f"clips            : {state['clips']}")
        print(f"with audio       : {state['with_audio']}")
        print(f"with reference   : {state['with_reference']}")
        print(f"READY TO SCORE   : {state['ready_to_score']}")
        if state["missing_audio"]:
            print(f"missing audio    : {len(state['missing_audio'])} "
                  f"(e.g. {', '.join(state['missing_audio'][:5])})")
        if state["missing_reference"]:
            print(f"missing reference: {len(state['missing_reference'])} "
                  f"(e.g. {', '.join(state['missing_reference'][:5])})")
        return 0

    if args.latency:
        run_latency(args.durations, args.repeats, args.resume)
        return 0

    if args.accuracy:
        run_accuracy(args.dataset, args.lang, args.resume, args.limit)
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
