"""Multilingual evaluation runner.

    # 1. Baseline: English through the unmodified pipeline, repeated, to
    #    establish how much the pipeline disagrees with itself.
    python -m eval.multilingual.run_eval --baseline --runs 3

    # 2. Pre-flight: round-trip English through the model and back, then run
    #    the pipeline. Isolates damage caused purely by passing text through
    #    the model, before any language change is in play.
    python -m eval.multilingual.run_eval --self-check

    # 3. The real thing, one language at a time.
    python -m eval.multilingual.run_eval --lang fr
    python -m eval.multilingual.run_eval --lang ar --judge

    # 4. Report.
    python -m eval.multilingual.report --model gemma4:31b

Results are appended line-by-line to results/<model>_<lang>.jsonl, so a run
killed by the shared Ollama proxy going down loses nothing; --resume skips
cases already present. Every file carries a _meta header line stamping the
model and the full run config, because an A/B pair that silently ran under
different settings is worse than no result at all.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from eval.multilingual import config, masking, metrics, payload, pipeline
from eval.multilingual.dataset import build_dataset
from eval.multilingual.translator import IdentityTranslator, OllamaTranslator, warmup


def _slug(text: str) -> str:
    return "".join(c if c.isalnum() or c in "-." else "-" for c in text)


def _result_path(model: str, lang: str, tag: str = "") -> Path:
    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    suffix = f"_{tag}" if tag else ""
    return config.RESULTS_DIR / f"{_slug(model)}_{lang}{suffix}.jsonl"


def _baseline_path(run_index: int) -> Path:
    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    return config.RESULTS_DIR / f"baseline_en_run{run_index}.jsonl"


def _append(path: Path, record: dict) -> None:
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def _load_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    seen = set()
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
    _append(path, {"_meta": True, "config": config.run_config(), **extra})


# --------------------------------------------------------------------------
# Baseline
# --------------------------------------------------------------------------

def run_baseline(runs: int, resume: bool, limit: int | None = None,
                 subset: bool = False) -> None:
    cases = build_dataset.load("en", subset=subset)
    if limit:
        cases = cases[:limit]
    for run_index in range(1, runs + 1):
        path = _baseline_path(run_index)
        done = _load_ids(path) if resume else set()
        if not resume and path.exists():
            path.unlink()
        if not path.exists():
            _write_meta(path, {"kind": "baseline", "run_index": run_index})
        print(f"\n=== baseline run {run_index}/{runs} ===")
        for i, case in enumerate(cases, 1):
            if case["id"] in done:
                continue
            record = _run_baseline_case(case)
            _append(path, record)
            print(f"  [{i}/{len(cases)}] {case['id']:6s} {record.get('intent','')}"
                  f"/{record.get('result_type','')}  {record.get('_duration_ms',0):.0f}ms")


def _run_baseline_case(case: dict) -> dict:
    session_id = pipeline.new_session_id()
    pipeline.clear_session(session_id)
    try:
        if case.get("multi_turn"):
            turns_out = []
            previous: dict = {}
            for turn in case["turns"]:
                text = _resolve_turn_text(turn, previous, translator=None, lang="en")
                if text is None:
                    break
                result = pipeline.run_turn(text, session_id=session_id)
                previous = result.response
                turns_out.append(result.to_dict())
            record = dict(previous)
            record["_turns"] = turns_out
        else:
            result = pipeline.run_turn(case["text"], session_id=session_id)
            record = result.to_dict()
        record["id"] = case["id"]
        record["category"] = case["category"]
        record["expected_tier"] = case["expected_tier"]
        return record
    finally:
        pipeline.clear_session(session_id)


def _resolve_turn_text(turn: dict, previous: dict, translator, lang: str) -> str | None:
    """Text for one turn.

    A ``from_options`` turn replays what a real user does when shown a
    localised option list: take the option the UI displayed and type it back.
    In a translated run the displayed option is the TRANSLATED report name --
    which is exactly the case expected to fail, because the staged matcher at
    agent/__init__.py:1119-1123 substring-matches against the English name.
    """
    if "text" in turn:
        return turn["text"]
    index = turn.get("from_options", 0)
    options = (previous or {}).get("options") or []
    if index >= len(options):
        return None
    option = options[index]
    if translator is None or lang == "en":
        return option
    translated = translator.translate(option, "en", lang)
    return translated.text if translated.ok else option


def load_baselines(runs: int) -> tuple[dict[str, metrics.BaselineCase], list[dict[str, dict]]]:
    per_run: list[dict[str, dict]] = []
    for run_index in range(1, runs + 1):
        path = _baseline_path(run_index)
        if not path.exists():
            continue
        run_map: dict[str, dict] = {}
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                if record.get("_meta") or not record.get("id"):
                    continue
                run_map[record["id"]] = record
        per_run.append(run_map)
    if not per_run:
        raise SystemExit(
            "No baseline found. Run:  python -m eval.multilingual.run_eval --baseline --runs 3"
        )
    return metrics.build_baseline(per_run), per_run


# --------------------------------------------------------------------------
# Translated run
# --------------------------------------------------------------------------

def run_language(
    lang: str,
    translator,
    baseline_cases: dict[str, metrics.BaselineCase],
    baseline_first: dict[str, dict],
    lexicon: set[str],
    resume: bool,
    judge=None,
    tag: str = "",
    limit: int | None = None,
    subset: bool = False,
    screen: bool = False,
) -> Path:
    cases = build_dataset.load(lang, subset=subset, screen=screen)
    if limit:
        cases = cases[:limit]
    path = _result_path(translator.name, lang, tag or ("screen" if screen else ""))
    done = _load_ids(path) if resume else set()
    if not resume and path.exists():
        path.unlink()
    if not path.exists():
        _write_meta(path, {"kind": "translated_run", "lang": lang, "model": translator.name})

    print(f"\n=== {translator.name} / {lang} ({len(cases)} cases) ===")
    for i, case in enumerate(cases, 1):
        if case["id"] in done:
            continue
        record = _run_translated_case(
            case, lang, translator, baseline_cases, baseline_first, lexicon, judge
        )
        _append(path, record)
        pres = record.get("preservation", {})
        flag = "ok " if record.get("routing", {}).get("routing_ok") else "MISS"
        gate = "ok " if pres.get("passed") else f"{pres.get('violation_count', 0)} viol"
        print(f"  [{i}/{len(cases)}] {case['id']:6s} route={flag} entities={gate} "
              f"in={record.get('inbound_ms') or 0:.0f}ms out={record.get('outbound_ms') or 0:.0f}ms")
    return path


def _run_translated_case(
    case: dict,
    lang: str,
    translator,
    baseline_cases: dict[str, metrics.BaselineCase],
    baseline_first: dict[str, dict],
    lexicon: set[str],
    judge,
) -> dict:
    case_id = case["id"]
    record: dict = {
        "id": case_id,
        "lang": lang,
        "category": case["category"],
        "expected_tier": case.get("expected_tier"),
        "model": translator.name,
        "multi_turn": bool(case.get("multi_turn")),
        "reply_mode": case.get("reply_mode"),
    }
    baseline = baseline_cases.get(case_id)
    if baseline is None:
        record["skipped"] = "no baseline for this case"
        return record

    session_id = pipeline.new_session_id()
    pipeline.clear_session(session_id)
    inbound_ms = 0.0
    outbound_ms = 0.0
    try:
        turns_detail: list[dict] = []
        response: dict = {}
        previous: dict = {}
        source_turns = case["turns"] if case.get("multi_turn") else [{"text": case["text"]}]

        for turn in source_turns:
            localized_input = _resolve_turn_text(turn, previous, translator, lang)
            if localized_input is None:
                turns_detail.append({"error": "no option to select from previous turn"})
                break

            # --- inbound: user language -> English -------------------------
            inbound = translator.translate(localized_input, lang, "en")
            inbound_ms += inbound.latency_ms
            if not inbound.ok:
                record["translation_error"] = f"inbound: {inbound.error}"

            result = pipeline.run_turn(inbound.text, session_id=session_id)
            if result.error:
                record["pipeline_error"] = result.error
            previous = result.response
            response = result.response
            turns_detail.append({
                "localized_input": localized_input,
                "english_input": inbound.text,
                "inbound": inbound.to_dict(),
                "intent": result.field("intent"),
                "result_type": result.field("result_type"),
                "pipeline_ms": round(result.duration_ms, 1),
            })

        record["pipeline_ms"] = sum(t.get("pipeline_ms", 0) for t in turns_detail)

        # --- outbound: English response -> user language -------------------
        # The rendered option list is masked out before translation and
        # re-inserted verbatim afterwards, so the model never sees report
        # identifiers. See payload.py for why: every payload >= 3,294 chars
        # 502'd on the shared proxy, and the bulk of those chars were 150+
        # report names the model only had to copy.
        english_payload = pipeline.translatable_payload(response)
        options = response.get("options") or []
        to_translate, blocks, passthrough = payload.split_payload(english_payload, options)

        translated: dict[str, str] = {}
        outbound_detail: dict[str, dict] = {}
        for name, text in to_translate.items():
            out = translator.translate(text, "en", lang)
            outbound_ms += out.latency_ms
            translated[name] = out.text
            outbound_detail[name] = out.to_dict()
            if not out.ok:
                record["translation_error"] = f"outbound.{name}: {out.error}"
        for name in passthrough:
            # Nothing but the option list -- no model call at all.
            outbound_detail[name] = {"skipped": "options-only field, not translated"}

        localized_payload = payload.reassemble(translated, blocks, passthrough)

        # Evidence for the regression tests and the report: what the model was
        # actually asked to translate, versus what the response contained.
        record["outbound_chars_sent"] = sum(len(t) for t in to_translate.values())
        record["outbound_chars_total"] = sum(len(t) for t in english_payload.values())
        record["options_masked"] = sorted(blocks)
        record["options_count"] = len(options)

        # --- scoring -------------------------------------------------------
        record["routing"] = metrics.routing_match(baseline, response)
        record["sql_match"] = metrics.sql_match(
            (baseline_first.get(case_id) or {}).get("db_sql"), response.get("db_sql")
        )

        english_blob = "\n".join(english_payload.values())
        localized_blob = "\n".join(localized_payload.values())
        record["preservation"] = masking.check_preservation(
            english_blob, localized_blob, lexicon
        ).to_dict()

        record["inbound_ms"] = round(inbound_ms, 1)
        record["outbound_ms"] = round(outbound_ms, 1)
        record["added_ms"] = round(inbound_ms + outbound_ms, 1)
        record["turns"] = turns_detail
        record["english_payload"] = english_payload
        record["localized_payload"] = localized_payload
        record["outbound_detail"] = outbound_detail

        if judge is not None:
            scores = {}
            first = turns_detail[0] if turns_detail else {}
            if first.get("localized_input") and first.get("english_input"):
                inbound_scores = judge.score(
                    first["localized_input"], first["english_input"], lang, "en"
                )
                scores.update({f"inbound_{k}": v for k, v in inbound_scores.items()
                               if k in ("adequacy", "fluency", "terminology")})
                if inbound_scores.get("note"):
                    scores["inbound_note"] = inbound_scores["note"]
            if english_blob and localized_blob:
                outbound_scores = judge.score(english_blob, localized_blob, "en", lang)
                scores.update({f"outbound_{k}": v for k, v in outbound_scores.items()
                               if k in ("adequacy", "fluency", "terminology")})
                if outbound_scores.get("note"):
                    scores["outbound_note"] = outbound_scores["note"]
            record["judge"] = scores

        return record
    finally:
        pipeline.clear_session(session_id)


# --------------------------------------------------------------------------
# Self-check
# --------------------------------------------------------------------------

def run_self_check(translator, baseline_cases, baseline_first, lexicon, pivot: str,
                   resume: bool, limit: int | None, subset: bool = False) -> Path:
    """English -> pivot -> English -> pipeline.

    Deviation from the original plan, which specified an identity translation
    (en -> en). That turned out to be untestable: a same-language call is a
    no-op the translator short-circuits, so it would measure nothing. A pivot
    round-trip is the closest meaningful equivalent -- it exercises both
    translation directions and lands back in English, where the result can be
    compared against the baseline directly, with no human-authored input in
    the loop to confound it. A model that damages routing here will damage it
    in every language.
    """
    cases = build_dataset.load("en", subset=subset)
    if limit:
        cases = cases[:limit]
    path = _result_path(translator.name, "en", f"selfcheck-{pivot}")
    done = _load_ids(path) if resume else set()
    if not resume and path.exists():
        path.unlink()
    if not path.exists():
        _write_meta(path, {"kind": "self_check", "pivot": pivot, "model": translator.name})

    print(f"\n=== self-check {translator.name}: en -> {pivot} -> en ({len(cases)} cases) ===")
    for i, case in enumerate(cases, 1):
        if case["id"] in done:
            continue
        if case.get("multi_turn"):
            continue
        baseline = baseline_cases.get(case["id"])
        if baseline is None:
            continue
        session_id = pipeline.new_session_id()
        pipeline.clear_session(session_id)
        try:
            out = translator.translate(case["text"], "en", pivot)
            back = translator.translate(out.text, pivot, "en")
            result = pipeline.run_turn(back.text, session_id=session_id)
            record = {
                "id": case["id"],
                "lang": "en",
                "category": case["category"],
                "model": translator.name,
                "original": case["text"],
                "pivot_text": out.text,
                "round_trip_text": back.text,
                "round_trip_identical": back.text.strip().lower() == case["text"].strip().lower(),
                "inbound_ms": round(out.latency_ms + back.latency_ms, 1),
                "outbound_ms": 0.0,
                "pipeline_ms": round(result.duration_ms, 1),
                "routing": metrics.routing_match(baseline, result.response),
                "preservation": masking.check_preservation(
                    case["text"], back.text, lexicon
                ).to_dict(),
                "sql_match": None,
            }
            if not out.ok or not back.ok:
                record["translation_error"] = out.error or back.error
            if result.error:
                record["pipeline_error"] = result.error
            _append(path, record)
            flag = "ok " if record["routing"]["routing_ok"] else "MISS"
            print(f"  [{i}/{len(cases)}] {case['id']:6s} route={flag} "
                  f"identical={record['round_trip_identical']}")
        finally:
            pipeline.clear_session(session_id)
    return path


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--baseline", action="store_true",
                        help="capture the English baseline through the unmodified pipeline")
    parser.add_argument("--runs", type=int, default=3,
                        help="baseline repeat count (default 3; measures pipeline noise)")
    parser.add_argument("--self-check", action="store_true",
                        help="round-trip English through the model via --pivot, then run")
    parser.add_argument("--pivot", default="fr", help="pivot language for --self-check")
    parser.add_argument("--lang", help="target language for a translated run (fr|ar|hi)")
    parser.add_argument("--model", help="override EVAL_TRANSLATE_MODEL")
    parser.add_argument("--judge", action="store_true", help="also run LLM-as-judge scoring")
    parser.add_argument("--resume", action="store_true", help="skip cases already in the output")
    parser.add_argument("--limit", type=int, help="only the first N cases (smoke testing)")
    parser.add_argument("--subset", action="store_true",
                        help="run the frozen 24-case stratified subset (build_dataset.SUBSET_24)")
    parser.add_argument("--screen", action="store_true",
                        help="run the 5-case screening suite (build_dataset.SCREEN_5)")
    parser.add_argument("--identity", action="store_true",
                        help="use the identity translator (harness self-test, no model calls)")
    args = parser.parse_args(argv)

    pipeline.bootstrap()

    if args.baseline:
        run_baseline(args.runs, args.resume, args.limit, args.subset)
        baseline_cases, _ = load_baselines(args.runs)
        variance = metrics.baseline_variance(baseline_cases)
        variance["runs"] = args.runs
        variance["subset"] = bool(args.subset)
        out = config.RESULTS_DIR / "baseline_variance.json"
        out.write_text(json.dumps(variance, indent=2), encoding="utf-8")
        print(f"\nBaseline self-agreement: {variance['self_agreement_pct']}% "
              f"({variance['stable_cases']}/{variance['cases']} cases stable)")
        if variance["unstable_case_ids"]:
            print(f"Unstable (excluded from headline fidelity): "
                  f"{', '.join(variance['unstable_case_ids'])}")
        print(f"Wrote {out}")
        return 0

    if not (args.self_check or args.lang):
        parser.error("choose --baseline, --self-check, or --lang")

    translator = IdentityTranslator() if args.identity else OllamaTranslator(model=args.model)
    lexicon = masking.load_lexicon(config.DATASET_DIR / "entities.json")
    baseline_cases, per_run = load_baselines(args.runs)
    baseline_first = per_run[0]

    if not args.identity:
        # Say which endpoint the model under test is served from -- a local and
        # a shared-proxy run are not latency comparable, and that must be
        # visible in the log rather than inferred later.
        print(f"translator endpoint: {config.translate_base_url()}")
        print(f"pipeline endpoint:   {config.ollama_base_url()}")
        ms = warmup(translator)
        print(f"warm-up: {ms:.0f}ms ({translator.name})")

    judge = None
    if args.judge:
        from eval.multilingual.judge import Judge

        judge = Judge()
        print(f"judge model: {judge.model}")

    if args.self_check:
        path = run_self_check(translator, baseline_cases, baseline_first, lexicon,
                              args.pivot, args.resume, args.limit, args.subset)
    else:
        path = run_language(args.lang, translator, baseline_cases, baseline_first,
                            lexicon, args.resume, judge, limit=args.limit,
                            subset=args.subset, screen=args.screen)
    print(f"\nWrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
