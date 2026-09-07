"""Renders the evaluation report from raw result files.

    python -m eval.multilingual.report --model gemma4:31b

Reads results/<model>_<lang>.jsonl plus baseline_variance.json and writes
results/report_<model>.md. Kept separate from the runner so a report can be
regenerated -- or the scoring changed -- without re-running the model.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from eval.multilingual import config, metrics
from eval.multilingual.score_judge import load_judge_scores


def _slug(text: str) -> str:
    return "".join(c if c.isalnum() or c in "-." else "-" for c in text)


def load_records(path: Path) -> tuple[list[dict], dict]:
    records, meta = [], {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if record.get("_meta"):
                meta = record
                continue
            records.append(record)
    return records, meta


def _fmt(value, suffix="") -> str:
    return "n/a" if value is None else f"{value}{suffix}"


def _ms(summary: dict, key: str) -> str:
    stats = summary.get("latency", {}).get(key) or {}
    p50, p95 = stats.get("p50"), stats.get("p95")
    if p50 is None:
        return "n/a"
    return f"{p50/1000:.2f}s / {p95/1000:.2f}s"


def _failure_rows(records: list[dict]) -> list[dict]:
    out = []
    for record in records:
        routing = record.get("routing") or {}
        preservation = record.get("preservation") or {}
        reasons = []
        if routing.get("baseline_stable") and not routing.get("routing_ok"):
            reasons.append("routing")
        if not preservation.get("passed", True):
            reasons.append("entity/number")
        if preservation.get("hallucination_count"):
            reasons.append("hallucination")
        if record.get("translation_error"):
            reasons.append("translation")
        if record.get("pipeline_error"):
            reasons.append("pipeline")
        if reasons:
            out.append({**record, "_reasons": reasons})
    return out


def _root_cause(record: dict) -> str:
    """Classify a failure so the report distinguishes a model problem from an
    architecture one -- the difference between 'try another model' and 'fix the
    pipeline'."""
    if record.get("pipeline_error"):
        return "infrastructure (pipeline exception)"
    if record.get("translation_error"):
        return "infrastructure (translation call failed)"
    preservation = record.get("preservation") or {}
    if preservation.get("hallucination_count"):
        return "entity corruption (model introduced content)"
    if not preservation.get("passed", True):
        return "entity corruption (model altered or dropped a value)"
    if record.get("multi_turn") and record.get("reply_mode") == "name":
        return ("architecture limitation - the model localised the option label and "
                "the staged matcher substring-matches the English name with no "
                "fallback (agent/__init__.py:1119-1123)")
    routing = record.get("routing") or {}
    if routing.get("baseline_stable") and not routing.get("routing_ok"):
        return "routing miss (translated query took a different path)"
    return "unclassified"


def _load_baseline_run1() -> dict[str, dict]:
    """Baseline run 1 keyed by case id, for post-hoc multi-turn selection
    comparison. Computed here rather than in the runner so the check could be
    added without re-running any model."""
    path = config.RESULTS_DIR / "baseline_en_run1.jsonl"
    if not path.exists():
        return {}
    out = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if not record.get("_meta") and record.get("id"):
                out[record["id"]] = record
    return out


def build_report(model: str) -> Path:
    results_dir = config.RESULTS_DIR
    baseline_run1 = _load_baseline_run1()
    variance_path = results_dir / "baseline_variance.json"
    variance = json.loads(variance_path.read_text(encoding="utf-8")) if variance_path.exists() else {}

    lang_files: dict[str, Path] = {}
    for lang in ("fr", "ar", "hi"):
        path = results_dir / f"{_slug(model)}_{lang}.jsonl"
        if path.exists():
            lang_files[lang] = path
    self_check = list(results_dir.glob(f"{_slug(model)}_en_selfcheck-*.jsonl"))

    all_records: list[dict] = []
    per_lang: dict[str, dict] = {}
    meta: dict = {}
    for lang, path in lang_files.items():
        records, file_meta = load_records(path)
        meta = meta or file_meta
        # Judge scores are produced out of band by score_judge.py, so a report
        # can be regenerated with or without them without re-running anything.
        judged = load_judge_scores(path)
        for record in records:
            record["lang"] = lang
            if record["id"] in judged:
                record["judge"] = {**(record.get("judge") or {}), **judged[record["id"]]}
            if record.get("multi_turn") and record["id"] in baseline_run1:
                english_text = (record.get("english_payload") or {}).get("response_text", "")
                sel = metrics.selection_match(baseline_run1[record["id"]], english_text)
                if sel:
                    record["selection"] = sel
        all_records.extend(records)
        per_lang[lang] = metrics.aggregate(records)

    overall = metrics.aggregate(all_records)
    grade, reasons = metrics.verdict(overall)
    per_task = metrics.aggregate_by(all_records, "category")

    lines: list[str] = []
    add = lines.append

    add(f"# Multilingual Evaluation - `{model}`\n")
    add(f"**Verdict: {grade}** - {'; '.join(reasons)}\n")
    add(f"Languages: {', '.join(sorted(lang_files)) or 'none'}  |  "
        f"Cases scored: {overall['cases']}\n")

    cfg = meta.get("config", {})
    if cfg:
        add("## Run configuration\n")
        add("| Setting | Value |")
        add("|---|---|")
        for key in sorted(cfg):
            add(f"| `{key}` | `{cfg[key]}` |")
        add("")

    # ---------------------------------------------------------------- noise
    add("## Baseline noise floor\n")
    if variance:
        add(f"The pipeline was run against the English set "
            f"{variance.get('runs', 3)} times. It agreed with itself on "
            f"**{_fmt(variance.get('self_agreement_pct'), '%')}** of cases "
            f"({variance.get('stable_cases')}/{variance.get('cases')}).\n")
        unstable = variance.get("unstable_case_ids") or []
        if unstable:
            add(f"Cases that route differently run-to-run, excluded from the "
                f"headline fidelity number because the model cannot be held "
                f"responsible for them: `{'`, `'.join(unstable)}`\n")
    else:
        add("_No baseline variance file found - run `--baseline` first._\n")

    # -------------------------------------------------------------- overall
    add("## Overall\n")
    add("| Metric | Value |")
    add("|---|---|")
    add(f"| Routing fidelity (stable baseline subset) | {_fmt(overall['routing_fidelity_pct'], '%')} |")
    add(f"| Routing fidelity (raw, all cases) | {_fmt(overall['routing_fidelity_raw_pct'], '%')} |")
    add(f"| intent + result_type + db_intent all match | {_fmt(overall['all_routing_fields_pct'], '%')} |")
    add(f"| Entity / number preservation (hard gate) | {_fmt(overall['entity_preservation_pct'], '%')} |")
    add(f"| Hallucination-free | {_fmt(overall['hallucination_free_pct'], '%')} |")
    add(f"| SQL consistency | {_fmt(overall['sql_consistency_pct'], '%')} ({overall['sql_cases']} cases) |")
    add(f"| Translation call failures | {overall['translation_failures']} |")
    add(f"| Pipeline errors | {overall['pipeline_errors']} |")
    add("")
    add("### Latency (p50 / p95)\n")
    add("| Stage | p50 / p95 |")
    add("|---|---|")
    add(f"| Inbound translation | {_ms(overall, 'inbound_ms')} |")
    add(f"| Outbound translation | {_ms(overall, 'outbound_ms')} |")
    add(f"| **Total added** | **{_ms(overall, 'added_ms')}** |")
    add(f"| Pipeline itself (unchanged) | {_ms(overall, 'pipeline_ms')} |")
    add("")
    if overall.get("judge"):
        add("### Translation quality (LLM-as-judge, 1-5)\n")
        add("| Axis | Mean |")
        add("|---|---|")
        for key, value in overall["judge"].items():
            add(f"| {key} | {value} |")
        add("\n_Advisory only; not part of the verdict. Calibrate against "
            "native-speaker review before relying on it._\n")

    # ---------------------------------------------------------- per language
    add("## Per language\n")
    add("| Lang | Cases | Routing | Preservation | Halluc-free | Added p50/p95 |")
    add("|---|---|---|---|---|---|")
    for lang, summary in sorted(per_lang.items()):
        add(f"| {lang} | {summary['cases']} | {_fmt(summary['routing_fidelity_pct'], '%')} | "
            f"{_fmt(summary['entity_preservation_pct'], '%')} | "
            f"{_fmt(summary['hallucination_free_pct'], '%')} | {_ms(summary, 'added_ms')} |")
    add("")

    # -------------------------------------------------------------- per task
    add("## Per task category\n")
    add("| Category | Cases | Routing | Preservation | Halluc-free |")
    add("|---|---|---|---|---|")
    for name, summary in per_task.items():
        add(f"| {name} | {summary['cases']} | {_fmt(summary['routing_fidelity_pct'], '%')} | "
            f"{_fmt(summary['entity_preservation_pct'], '%')} | "
            f"{_fmt(summary['hallucination_free_pct'], '%')} |")
    add("")

    # ------------------------------------------------------------ multi-turn
    numeric = [r for r in all_records if r.get("multi_turn") and r.get("reply_mode") == "numeric"]
    named = [r for r in all_records if r.get("multi_turn") and r.get("reply_mode") == "name"]
    if numeric or named:
        add("## Multi-turn option selection\n")
        add("Split deliberately. Numeric replies are language-neutral and are the "
            "real signal on the model. Name replies depend on the model leaving the "
            "report name byte-identical, because the staged matcher at "
            "`agent/__init__.py:1119-1123` substring-matches against the English "
            "name and has no fallback - so 9b measures how fragile the staged flow "
            "is rather than how good the model is, and is excluded from the "
            "verdict.\n")
        add("Scored on the RESOLVED OPTION, not the routing signature: a staged "
            "status flow ends in `get_status/error` whenever the chosen report has "
            "no instances, so a run that picked the wrong report would otherwise "
            "score as a pass.\n")
        add("| Mode | Cases | Same option resolved as baseline |")
        add("|---|---|---|")
        for label, group in (("9a numeric", numeric), ("9b name", named)):
            scored = [r for r in group if r.get("selection")]
            ok = sum(1 for r in scored if r["selection"]["selection_ok"])
            pct = f"{100.0*ok/len(scored):.0f}% ({ok}/{len(scored)})" if scored else "n/a"
            add(f"| {label} | {len(group)} | {pct} |")
        add("")
        for record in (numeric + named):
            sel = record.get("selection")
            if sel and not sel["selection_ok"]:
                add(f"- `{record['id']}` / {record.get('lang')}: expected "
                    f"`{sel['expected_selection']}`, resolved "
                    f"`{sel['actual_selection']}`")
        add("")

    # ----------------------------------------------------------- self-check
    if self_check:
        add("## Self-check (English -> pivot -> English)\n")
        for path in self_check:
            records, _ = load_records(path)
            if not records:
                continue
            summary = metrics.aggregate(records)
            identical = sum(1 for r in records if r.get("round_trip_identical"))
            add(f"`{path.name}`: routing {_fmt(summary['routing_fidelity_pct'], '%')}, "
                f"preservation {_fmt(summary['entity_preservation_pct'], '%')}, "
                f"round-trip textually identical {identical}/{len(records)}.\n")
            add("Round-trip rarely returns identical text and does not need to - "
                "routing fidelity is what matters here.\n")

    # -------------------------------------------------------------- failures
    failures = _failure_rows(all_records)
    add(f"## Failures ({len(failures)})\n")
    if not failures:
        add("_None._\n")
    else:
        add("| Case | Lang | Category | Reasons | Root cause |")
        add("|---|---|---|---|---|")
        for record in failures:
            add(f"| `{record['id']}` | {record.get('lang')} | {record.get('category')} | "
                f"{', '.join(record['_reasons'])} | {_root_cause(record)} |")
        add("")
        add("### Failure detail\n")
        for record in failures:
            add(f"#### `{record['id']}` / {record.get('lang')} - {record.get('category')}\n")
            add(f"- **Root cause:** {_root_cause(record)}")
            turns = record.get("turns") or []
            if turns:
                first = turns[0]
                add(f"- **Localised input:** `{first.get('localized_input', '')}`")
                add(f"- **Translated to English:** `{first.get('english_input', '')}`")
            routing = record.get("routing") or {}
            if routing:
                add(f"- **Expected routing:** `{routing.get('expected')}`")
                add(f"- **Actual routing:** `{routing.get('actual')}`")
            for violation in (record.get("preservation") or {}).get("violations", [])[:10]:
                add(f"- **{violation['kind']} violation:** `{violation['expected']}` "
                    f"-> `{violation['actual']}` ({violation['detail']})")
            for h in (record.get("preservation") or {}).get("hallucinations", [])[:10]:
                add(f"- **hallucinated {h['kind']}:** `{h['actual']}` ({h['detail']})")
            if record.get("translation_error"):
                add(f"- **Translation error:** `{record['translation_error']}`")
            if record.get("pipeline_error"):
                add(f"- **Pipeline error:** `{record['pipeline_error']}`")
            english = record.get("english_payload") or {}
            localized = record.get("localized_payload") or {}
            for name in english:
                add(f"- **`{name}` (English):** {english[name][:400]!r}")
                add(f"- **`{name}` ({record.get('lang')}):** {localized.get(name, '')[:400]!r}")
            add("")

    add("---\n")
    add("Raw results are in `eval/multilingual/results/`. The same suite runs "
        "against any other model with `EVAL_TRANSLATE_MODEL=<model> "
        "python -m eval.multilingual.run_eval --lang <lang>` - no code changes.\n")

    out = results_dir / f"report_{_slug(model)}.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", default=config.translate_model())
    args = parser.parse_args(argv)
    path = build_report(args.model)
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
