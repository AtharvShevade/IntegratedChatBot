"""Turn STT result files into a markdown report with an acceptance table.

    python -m eval.stt.report
    python -m eval.stt.report --model large-v3-turbo --out report.md

The table is the point. Every criterion is graded PASS / FAIL / NOT MEASURED,
and NOT MEASURED is a first-class outcome: a benchmark that ran successfully
against a dataset with no transcripts has measured nothing about accuracy, and
saying "PASS" there would be the single most damaging thing this file could do.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from eval.stt import config, metrics


def load_records(path: Path) -> tuple[list[dict], dict]:
    """Read a result JSONL, splitting the _meta line from the data."""
    records: list[dict] = []
    meta: dict = {}
    if not path.exists():
        return records, meta
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("_meta"):
                meta = record
            else:
                records.append(record)
    return records, meta


def _find(kind: str, model: str) -> list[Path]:
    slug = model.replace(":", "-").replace("/", "-").replace(" ", "_")
    return sorted(config.RESULTS_DIR.glob(f"{slug}_{kind}*.jsonl"))


def _fmt(value, suffix="", nd=1) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.{nd}f}{suffix}"
    return f"{value}{suffix}"


def grade(key: str, value: float | None) -> str:
    """PASS / FAIL / NOT MEASURED for one acceptance criterion."""
    if value is None:
        return "NOT MEASURED"
    rule = config.ACCEPTANCE[key]
    ok = value <= rule["target"] if rule["cmp"] == "<=" else value >= rule["target"]
    return "PASS" if ok else "FAIL"


def acceptance_rows(summary: dict, latency: dict) -> list[tuple]:
    """(label, measured, target, verdict) for every criterion."""
    p95_5 = (latency.get("5") or {}).get("wall_ms", {}).get("p95")
    p95_15 = (latency.get("15") or {}).get("wall_ms", {}).get("p95")
    warm_rtf = None
    for seconds in ("5", "10", "15"):
        candidate = (latency.get(seconds) or {}).get("rtf")
        if candidate is not None:
            warm_rtf = candidate
            break

    values = {
        "wer_en_fr_pct": summary.get("wer_en_fr_pct"),
        "cer_hi_ar_pct": summary.get("cer_hi_ar_pct"),
        "entity_preservation": summary.get("entity_preservation"),
        "translation_leak_pct": summary.get("translation_leak_pct"),
        "hallucination_pct": summary.get("hallucination_pct"),
        "p95_5s_ms": p95_5,
        "p95_15s_ms": p95_15,
        "warm_rtf": warm_rtf,
    }
    units = {"p95_5s_ms": "ms", "p95_15s_ms": "ms", "warm_rtf": ""}

    rows = []
    for key, rule in config.ACCEPTANCE.items():
        value = values.get(key)
        unit = units.get(key, "%")
        target = f"{rule['cmp']} {rule['target']:g}{unit}"
        rows.append((rule["label"], _fmt(value, unit), target, grade(key, value)))
    return rows


def build_report(model: str) -> str:
    acc_paths = _find("accuracy", model)
    lat_paths = _find("latency", model)

    acc_records: list[dict] = []
    acc_meta: dict = {}
    for path in acc_paths:
        records, meta = load_records(path)
        acc_records.extend(records)
        acc_meta = acc_meta or meta

    lat_records: list[dict] = []
    lat_meta: dict = {}
    for path in lat_paths:
        records, meta = load_records(path)
        lat_records.extend(records)
        lat_meta = lat_meta or meta

    summary = metrics.aggregate(acc_records) if acc_records else {}
    latency = metrics.aggregate_latency(lat_records) if lat_records else {}
    meta = acc_meta or lat_meta
    cfg = meta.get("config", {})
    health = meta.get("health", {})

    out: list[str] = []
    add = out.append

    add(f"# STT benchmark — {cfg.get('model', model)}")
    add("")
    add(f"- **Service**: `{cfg.get('base_url', '—')}`")
    add(f"- **/health reports**: `{json.dumps(health, ensure_ascii=False)}`")
    add(f"- **Runtime / compute**: {cfg.get('runtime', 'unknown')} / "
        f"{cfg.get('compute_type', 'unknown')} · threads={cfg.get('cpu_threads', 'unknown')}")
    add(f"- **Hints sent**: {cfg.get('send_hints')} · "
        f"initial_prompt={'yes' if cfg.get('initial_prompt') else 'no'}")
    add(f"- **Run started**: {meta.get('started_at', '—')}")
    add("")

    # ── Acceptance table ─────────────────────────────────────────────────────
    add("## Acceptance")
    add("")
    add("| Metric | Measured | Target | Verdict |")
    add("|---|---:|---:|:---|")
    rows = acceptance_rows(summary, latency)
    for label, measured, target, verdict in rows:
        add(f"| {label} | {measured} | {target} | **{verdict}** |")
    add("")

    verdicts = [r[3] for r in rows]
    if "FAIL" in verdicts:
        overall = "FAIL"
    elif "NOT MEASURED" in verdicts:
        overall = "INCOMPLETE"
    else:
        overall = "PASS"
    add(f"**Overall: {overall}**")
    add("")
    if overall == "INCOMPLETE":
        add("> Criteria marked NOT MEASURED have no data behind them. This "
            "configuration has **not** passed; it has only been partially "
            "measured. Record the dataset and re-run before drawing a conclusion.")
        add("")

    # ── Latency ──────────────────────────────────────────────────────────────
    if latency:
        add("## Latency")
        add("")
        add("Synthetic tone audio — measures fixed overhead and encoder cost per "
            "30s window, **not** decoding of real speech.")
        add("")
        add("| Audio | n | Cold p50 | Warm p50 | Wall p95 | Server p50 | RTF |")
        add("|---:|---:|---:|---:|---:|---:|---:|")
        for key in sorted(latency, key=lambda k: float(k)):
            row = latency[key]
            add(f"| {row['audio_seconds']}s | {row['n']} "
                f"| {_fmt(row['cold_ms']['p50'], ' ms', 0)} "
                f"| {_fmt(row['warm_ms']['p50'], ' ms', 0)} "
                f"| {_fmt(row['wall_ms']['p95'], ' ms', 0)} "
                f"| {_fmt(row['server_ms']['p50'], ' ms', 0)} "
                f"| {_fmt(row['rtf'], '', 2)} |")
        add("")
        if not any((latency[k].get("server_ms") or {}).get("p50") for k in latency):
            add("> `Server p50` is empty because the service does not report "
                "`processing_ms`. Network time and inference time therefore "
                "cannot be separated — every figure above is wall clock.")
            add("")

    # ── Accuracy ─────────────────────────────────────────────────────────────
    add("## Accuracy")
    add("")
    if not summary or not summary.get("clips_scored"):
        add("**NOT MEASURED** — no scored clips.")
        add("")
        add("The dataset template exists but has no recorded audio and no "
            "hand-typed reference transcripts, so no accuracy figure can be "
            "produced. See `eval/stt/README.md`.")
        add("")
    else:
        add(f"{summary['clips_scored']} clip(s) scored, "
            f"{summary['clips_errored']} errored.")
        add("")
        add("| Language | n | WER | CER | Headline | Latency p50 |")
        add("|---|---:|---:|---:|:--|---:|")
        for lang, row in sorted(summary.get("by_language", {}).items()):
            add(f"| {config.LANGUAGES.get(lang, lang)} | {row['n']} "
                f"| {_fmt(row['wer'], '%')} | {_fmt(row['cer'], '%')} "
                f"| {row['headline'].upper()} "
                f"| {_fmt(row['latency_ms']['p50'], ' ms', 0)} |")
        add("")
        add(f"- **Entity preservation**: {_fmt(summary.get('entity_preservation'), '%')} "
            f"({summary.get('entity_preserved')}/{summary.get('entity_total')} entities kept verbatim)")
        add(f"- **Translation leakage**: {_fmt(summary.get('translation_leak_pct'), '%')} "
            f"over {summary.get('translation_leak_n')} decidable clip(s)")
        add(f"- **Hallucination**: {_fmt(summary.get('hallucination_pct'), '%')} "
            f"over {summary.get('hallucination_n')} non-speech clip(s)")
        add("")

        if summary.get("by_condition"):
            add("| Condition | n | WER | CER |")
            add("|---|---:|---:|---:|")
            for condition, row in sorted(summary["by_condition"].items()):
                add(f"| {condition} | {row['n']} | {_fmt(row['wer'], '%')} "
                    f"| {_fmt(row['cer'], '%')} |")
            add("")

        worst = sorted(
            (r for r in acc_records if r.get("entity_missing")),
            key=lambda r: -len(r["entity_missing"]))[:10]
        if worst:
            add("### Entities lost")
            add("")
            add("| Clip | Missing | Hypothesis |")
            add("|---|---|---|")
            for record in worst:
                add(f"| {record['id']} | `{'`, `'.join(record['entity_missing'])}` "
                    f"| {record.get('hypothesis', '')[:60]} |")
            add("")

    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", default=config.model(),
                        help="which result files to read (default: EVAL_STT_MODEL)")
    parser.add_argument("--out", type=Path, help="write markdown here instead of stdout")
    args = parser.parse_args(argv)

    text = build_report(args.model)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8", newline="\n")
        print(f"Wrote {args.out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
