"""Run every arm over every query and write raw results.

Arms are INTERLEAVED per query, not run one after the other. Running all of A
then all of B lets machine load, proxy queueing and network drift land on one
arm and get read as a model difference -- a trap this repo has already fallen
into once while benchmarking Whisper. Interleaving spreads any drift evenly.

    python -m eval.model_bench.run_bench
    python -m eval.model_bench.run_bench --arms deployed,gemma_cloud --limit 5
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from eval.model_bench import scoring
from eval.model_bench.client import CLOUD_BASE, DEPLOYED_BASE, extract
from eval.model_bench.dataset import load_cases

RESULTS = Path(__file__).resolve().parent / "results"

ARMS = {
    # The baseline: exactly what OLLAMA_EXTRACT_MODEL is set to in .env, on the
    # endpoint OLLAMA_BASE_URL points at.
    "deployed":     {"model": "qwen2.5:7b",       "base": DEPLOYED_BASE, "where": "deployed proxy"},
    "gemma_cloud":  {"model": "gemma4:31b-cloud", "base": CLOUD_BASE,    "where": "Ollama Cloud"},
    # Qwen 3 14B has NO cloud tag (see README). qwen3:14b already exists on the
    # deployed proxy as TRANSLATION_MODEL, so it is run as an explicitly
    # labelled self-hosted stand-in -- NOT as a silent substitute for the
    # cloud model that was asked for.
    "qwen3_14b":    {"model": "qwen3:14b",        "base": DEPLOYED_BASE, "where": "deployed proxy (NOT cloud)", "timeout": 300.0},
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", default=",".join(ARMS))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default="run")
    args = ap.parse_args()

    arms = [a.strip() for a in args.arms.split(",") if a.strip()]
    unknown = [a for a in arms if a not in ARMS]
    if unknown:
        print(f"unknown arm(s): {unknown}. known: {list(ARMS)}", file=sys.stderr)
        return 2

    cases = load_cases()
    if args.limit:
        cases = cases[: args.limit]

    # One warm-up per arm, discarded. The deployed proxy showed a ~5.9s model
    # load on a cold first call; counting that against one arm's latency would
    # measure who happened to go first.
    for arm in arms:
        cfg = ARMS[arm]
        t0 = time.perf_counter()
        warm = extract("hello", cfg["model"], cfg["base"], cfg.get("timeout", 120.0))
        print(f"warm-up {arm:<12} {(time.perf_counter()-t0)*1000:8.0f}ms "
              f"ok={warm['ok']} {warm['error'] or ''}")

    rows: dict[str, list[dict]] = {a: [] for a in arms}
    raw: list[dict] = []

    for n, case in enumerate(cases, 1):
        record = {"id": case["id"], "category": case["category"], "grade": case["grade"],
                  "query": case["query"], "expected_intent": case.get("intent")}
        line = f"[{n:>2}/{len(cases)}] {case['id']:<5} {case['category']:<17}"
        for arm in arms:                              # interleaved
            cfg = ARMS[arm]
            result = extract(case["query"], cfg["model"], cfg["base"], cfg.get("timeout", 120.0))
            row = scoring.score_case(case, result)
            rows[arm].append(row)
            record[f"{arm}_intent"] = row["intent"]
            record[f"{arm}_report_name"] = row["report_name"]
            record[f"{arm}_latency_ms"] = row["latency_ms"]
            record[f"{arm}_correct"] = row["intent_correct"]
            record[f"{arm}_error"] = row["error"]
            record[f"{arm}_raw"] = result.get("raw")
            mark = {True: "OK", False: "XX", None: "--"}[row["intent_correct"]]
            line += f"  {arm}={mark}/{row['latency_ms']/1000:5.1f}s"
        print(line, flush=True)
        raw.append(record)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    RESULTS.mkdir(exist_ok=True)
    raw_path = RESULTS / f"{args.out}_{stamp}_raw.jsonl"
    with open(raw_path, "w", encoding="utf-8", newline="\n") as fh:
        for record in raw:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    summary = {
        "timestamp": stamp,
        "cases": len(cases),
        "arms": {a: {**ARMS[a],
                     "summary": scoring.aggregate(rows[a]),
                     "by_category": scoring.by_category(rows[a])} for a in arms},
        "rows": rows,
    }
    sum_path = RESULTS / f"{args.out}_{stamp}_summary.json"
    sum_path.write_text(json.dumps(summary, indent=1, ensure_ascii=False),
                        encoding="utf-8", newline="\n")
    print(f"\nraw     -> {raw_path}\nsummary -> {sum_path}")
    for arm in arms:
        s = summary["arms"][arm]["summary"]
        print(f"{arm:<12} intent {s['intent_accuracy_pct']}%  "
              f"entity {s['entity_accuracy_pct']}%  fail {s['failure_rate_pct']}%  "
              f"median {s['median_ms']}ms  p95 {s['p95_ms']}ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
