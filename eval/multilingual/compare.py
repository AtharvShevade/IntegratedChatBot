"""Side-by-side model comparison for the screening suite.

    python -m eval.multilingual.compare --models gemma4:31b qwen2.5:7b

Reads results/<model>_<lang>_screen.jsonl for each model and renders one table.
Because every model runs the identical frozen SCREEN_5 case ids in the identical
three languages against the identical English baseline, the columns are
genuinely comparable.

A screening run is a go/no-go filter, not a measurement. Five cases per language
cannot support a confident routing-fidelity percentage -- the sample is far too
small and a single case swings it 20 points. What it can do is separate a model
that corrupts report codes, or takes two minutes per call, from one that does
not. The output says so rather than dressing 15 data points up as statistics.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from eval.multilingual import config, metrics
from eval.multilingual.dataset.build_dataset import DEGENERATE_BASELINE
from eval.multilingual.score_judge import load_judge_scores

LANGS = ("fr", "ar", "hi")


def _slug(text: str) -> str:
    return "".join(c if c.isalnum() or c in "-." else "-" for c in text)


def _screen_path(model: str, lang: str) -> Path:
    return config.RESULTS_DIR / f"{_slug(model)}_{lang}_screen.jsonl"


def load_model(model: str) -> dict[str, list[dict]]:
    """Screening records per language, with judge scores merged in."""
    out: dict[str, list[dict]] = {}
    for lang in LANGS:
        path = _screen_path(model, lang)
        if not path.exists():
            continue
        judged = load_judge_scores(path)
        records = []
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                if record.get("_meta"):
                    continue
                record["lang"] = lang
                if record["id"] in judged:
                    record["judge"] = {**(record.get("judge") or {}), **judged[record["id"]]}
                records.append(record)
        out[lang] = records
    return out


def _clean_pass(record: dict) -> bool:
    """A case passes screening only if routing AND entity preservation hold and
    nothing errored. Deliberately strict: this is a filter."""
    routing_ok = (record.get("routing") or {}).get("routing_ok", False)
    preserved = (record.get("preservation") or {}).get("passed", False)
    errored = bool(record.get("translation_error") or record.get("pipeline_error"))
    return bool(routing_ok and preserved and not errored)


def summarise(by_lang: dict[str, list[dict]]) -> dict:
    all_records = [r for records in by_lang.values() for r in records]
    if not all_records:
        return {}
    # A case whose ENGLISH baseline is itself wrong cannot fairly score a
    # translation, so it is excluded from every rate and reported apart.
    everything = [r for r in all_records if r["id"] not in DEGENERATE_BASELINE]
    excluded = [r for r in all_records if r["id"] in DEGENERATE_BASELINE]
    if not everything:
        return {}

    def pct(n, d):
        return round(100.0 * n / d, 1) if d else None

    added = [r["added_ms"] for r in everything if r.get("added_ms") is not None]
    pipeline_ms = [r["pipeline_ms"] for r in everything if r.get("pipeline_ms") is not None]
    inbound = [r["inbound_ms"] for r in everything if r.get("inbound_ms") is not None]
    outbound = [r["outbound_ms"] for r in everything if r.get("outbound_ms") is not None]
    end_to_end = [
        r["added_ms"] + r["pipeline_ms"]
        for r in everything
        if r.get("added_ms") is not None and r.get("pipeline_ms") is not None
    ]

    judge_axes: dict[str, list[float]] = {}
    for record in everything:
        for key, value in (record.get("judge") or {}).items():
            if isinstance(value, (int, float)) and key.endswith(
                ("adequacy", "fluency", "terminology")
            ):
                judge_axes.setdefault(key, []).append(float(value))
    quality = [v for values in judge_axes.values() for v in values]

    routing_ok = sum(1 for r in everything if (r.get("routing") or {}).get("routing_ok"))
    preserved = sum(1 for r in everything if (r.get("preservation") or {}).get("passed"))
    errors = sum(
        1 for r in everything if r.get("translation_error") or r.get("pipeline_error")
    )

    return {
        "cases": len(everything),
        "excluded_degenerate": sorted({r["id"] for r in excluded}),
        "per_lang": {
            lang: {
                "n": len([r for r in records if r["id"] not in DEGENERATE_BASELINE]),
                "clean": sum(
                    1 for r in records
                    if r["id"] not in DEGENERATE_BASELINE and _clean_pass(r)
                ),
                "added_p50": metrics.latency_summary(
                    [r["added_ms"] for r in records if r.get("added_ms") is not None]
                )["p50"],
            }
            for lang, records in by_lang.items()
        },
        "routing_pct": pct(routing_ok, len(everything)),
        "routing_n": f"{routing_ok}/{len(everything)}",
        "preservation_pct": pct(preserved, len(everything)),
        "preservation_n": f"{preserved}/{len(everything)}",
        "errors": errors,
        "latency": {
            "inbound": metrics.latency_summary(inbound),
            "outbound": metrics.latency_summary(outbound),
            "added": metrics.latency_summary(added),
            "pipeline": metrics.latency_summary(pipeline_ms),
            "end_to_end": metrics.latency_summary(end_to_end),
        },
        "quality_mean": round(sum(quality) / len(quality), 2) if quality else None,
        "quality_axes": {
            key: round(sum(values) / len(values), 2)
            for key, values in sorted(judge_axes.items())
        },
        "digit_shape_warnings": sorted(
            {
                w
                for r in everything
                for w in (r.get("preservation") or {}).get("digit_shape_warnings", [])
            }
        ),
    }


def _sec(ms) -> str:
    return "n/a" if ms is None else f"{ms/1000:.1f}s"


def _lang_cell(summary: dict, lang: str) -> str:
    entry = (summary.get("per_lang") or {}).get(lang)
    if not entry:
        return "-"
    return f"{entry['clean']}/{entry['n']} ({_sec(entry['added_p50'])})"


def build(models: list[str]) -> Path:
    summaries = {model: summarise(load_model(model)) for model in models}
    live = {m: s for m, s in summaries.items() if s}

    lines: list[str] = []
    add = lines.append
    add("# Quick screening: model comparison\n")
    add("Identical frozen case set (`SCREEN_5`) x 3 languages = 15 queries per "
        "model, scored against the same 3x English baseline.\n")
    add("**This is a filter, not a measurement.** Five cases per language cannot "
        "support a confident percentage -- one case moves any rate by 20 points. "
        "It is here to decide which model earns a full 60-query run.\n")

    add("## Comparison\n")
    add("| Model | FR | AR | HI | Avg Latency | Routing | Entity Preservation | "
        "Translation Quality | Errors |")
    add("|---|---|---|---|---|---|---|---|---|")
    for model, summary in summaries.items():
        if not summary:
            add(f"| `{model}` | - | - | - | not run | - | - | - | - |")
            continue
        quality = summary["quality_mean"]
        add(
            f"| `{model}` "
            f"| {_lang_cell(summary, 'fr')} "
            f"| {_lang_cell(summary, 'ar')} "
            f"| {_lang_cell(summary, 'hi')} "
            f"| {_sec(summary['latency']['added']['p50'])} added / "
            f"{_sec(summary['latency']['end_to_end']['p50'])} total "
            f"| {summary['routing_pct']}% ({summary['routing_n']}) "
            f"| {summary['preservation_pct']}% ({summary['preservation_n']}) "
            f"| {f'{quality}/5' if quality is not None else 'not scored'} "
            f"| {summary['errors']} |"
        )
    add("")
    add("Language cells show *clean passes* (routing **and** entity preservation, "
        "no errors) out of cases scored, with median added latency in brackets. "
        "Latency still reflects every case run.\n")
    if DEGENERATE_BASELINE:
        add("### Excluded from scoring\n")
        for case_id, reason in DEGENERATE_BASELINE.items():
            add(f"- **`{case_id}`** - {reason}\n")

    add("## Latency detail (p50 / p95)\n")
    add("| Model | Inbound | Outbound | Total added | Pipeline | End-to-end |")
    add("|---|---|---|---|---|---|")
    for model, summary in live.items():
        lat = summary["latency"]
        def cell(key):
            stats = lat[key]
            return f"{_sec(stats['p50'])} / {_sec(stats['p95'])}"
        add(f"| `{model}` | {cell('inbound')} | {cell('outbound')} | "
            f"**{cell('added')}** | {cell('pipeline')} | {cell('end_to_end')} |")
    add("")

    if any(s.get("quality_axes") for s in live.values()):
        add("## Translation quality by axis (LLM-as-judge, 1-5)\n")
        axes = sorted({a for s in live.values() for a in s.get("quality_axes", {})})
        add("| Model | " + " | ".join(axes) + " |")
        add("|---" * (len(axes) + 1) + "|")
        for model, summary in live.items():
            row = [str(summary.get("quality_axes", {}).get(a, "-")) for a in axes]
            add(f"| `{model}` | " + " | ".join(row) + " |")
        add("\n_Judged by a third model, different family from both candidates, so "
            "neither is marking its own homework. Advisory only._\n")

    # Judge-vs-objective disagreement. Surfaced automatically because it is the
    # difference between "the judge is a useful signal" and "the judge is
    # actively misleading" -- and a reader comparing two near-identical quality
    # means would otherwise never know which one applies.
    blind_spots = []
    for model in models:
        for lang, records in load_model(model).items():
            for record in records:
                judge = record.get("judge") or {}
                adequacy = judge.get("outbound_adequacy")
                violations = (record.get("preservation") or {}).get("violation_count", 0)
                if adequacy is not None and adequacy >= 4 and violations > 0:
                    blind_spots.append((model, lang, record, adequacy, violations))
    if blind_spots:
        add("## Judge blind spots\n")
        add("Cases the objective checks failed but the LLM judge rated 4+ for "
            "adequacy. Where these exist, the Translation Quality column is not "
            "trustworthy and the objective columns must carry the decision.\n")
        add("| Model | Case | Lang | Judge adequacy | Objective violations | Actual output |")
        add("|---|---|---|---|---|---|")
        for model, lang, record, adequacy, violations in blind_spots:
            payload = record.get("localized_payload") or {}
            text = next(iter(payload.values()), "")
            snippet = text[:60].replace("\n", " ").replace("|", "\\|")
            add(f"| `{model}` | `{record['id']}` | {lang} | {adequacy}/5 | "
                f"{violations} | `{snippet}` |")
        add("")

    for model, summary in live.items():
        warnings = summary.get("digit_shape_warnings")
        if warnings:
            add(f"- `{model}` emitted non-ASCII digit shapes: "
                f"{', '.join(warnings)}. Values are intact, but production code "
                f"assumes ASCII digits.\n")

    add("## Per-case detail\n")
    for model in models:
        by_lang = load_model(model)
        if not by_lang:
            continue
        add(f"### `{model}`\n")
        add("| Case | Lang | Routing | Entities | Added | Notes |")
        add("|---|---|---|---|---|---|")
        for lang in LANGS:
            for record in by_lang.get(lang, []):
                routing = record.get("routing") or {}
                preservation = record.get("preservation") or {}
                notes = []
                if not routing.get("routing_ok"):
                    notes.append(
                        f"{routing.get('expected', {}).get('intent')}"
                        f" -> {routing.get('actual', {}).get('intent')}"
                    )
                for violation in preservation.get("violations", [])[:3]:
                    notes.append(f"{violation['kind']} `{violation['expected']}` lost")
                for h in preservation.get("hallucinations", [])[:2]:
                    notes.append(f"invented {h['kind']} `{h['actual']}`")
                if record.get("translation_error"):
                    notes.append(f"translation error: {record['translation_error'][:80]}")
                if record.get("pipeline_error"):
                    notes.append(f"pipeline error: {record['pipeline_error'][:80]}")
                add(f"| `{record['id']}` | {lang} "
                    f"| {'ok' if routing.get('routing_ok') else '**MISS**'} "
                    f"| {'ok' if preservation.get('passed') else '**FAIL**'} "
                    f"| {_sec(record.get('added_ms'))} "
                    f"| {'; '.join(notes) or '-'} |")
        add("")

    out = config.RESULTS_DIR / "screening_comparison.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--models", nargs="+", required=True)
    args = parser.parse_args(argv)
    path = build(args.models)
    print(f"Wrote {path}")
    print(path.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
