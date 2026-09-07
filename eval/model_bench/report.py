"""Turn a run's summary JSON into the comparison tables.

    python -m eval.model_bench.report                    # newest run
    python -m eval.model_bench.report --file <summary>

Prints an overall table, a per-category table, and the disagreement list --
every query where the arms answered differently, which is the only part of
the output that tells you WHY one model scored higher.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RESULTS = Path(__file__).resolve().parent / "results"

ROWS = [
    ("Test cases",                  "cases",               "{}"),
    ("Graded (strict) cases",       "intent_graded",       "{}"),
    ("Intent accuracy",             "intent_accuracy_pct", "{}%"),
    ("Report-name accuracy",        "entity_accuracy_pct", "{}%"),
    ("Date/time entity accuracy",   "date_accuracy_pct",   "{}%"),
    ("Invalid intent (off-taxonomy)", "invalid_intent_pct", "{}%"),
    ("Schema complete",             "schema_ok_pct",       "{}%"),
    ("Hallucinated entity",         "hallucination_pct",   "{}%"),
    ("Parses in production as-is",  "prod_parse_ok_pct",   "{}%"),
    ("Failure rate",                "failure_rate_pct",    "{}%"),
    ("Median latency",              "median_ms",           "{} ms"),
    ("Average latency",             "mean_ms",             "{} ms"),
    ("P95 latency",                 "p95_ms",              "{} ms"),
]


def _cell(value, fmt: str) -> str:
    return "n/a" if value is None else fmt.format(value)


def _table(header: list[str], rows: list[list[str]]) -> str:
    widths = [max(len(header[i]), *(len(r[i]) for r in rows)) for i in range(len(header))]
    out = ["| " + " | ".join(h.ljust(widths[i]) for i, h in enumerate(header)) + " |",
           "|" + "|".join("-" * (w + 2) for w in widths) + "|"]
    for row in rows:
        out.append("| " + " | ".join(row[i].ljust(widths[i]) for i in range(len(row))) + " |")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=None)
    args = ap.parse_args()

    if args.file:
        path = Path(args.file)
    else:
        found = sorted(RESULTS.glob("*_summary.json"))
        if not found:
            print("no summary files in eval/model_bench/results/", file=sys.stderr)
            return 1
        path = found[-1]

    data = json.loads(path.read_text(encoding="utf-8"))
    arms = list(data["arms"])
    print(f"# Model benchmark -- {path.name}\n")
    for arm in arms:
        cfg = data["arms"][arm]
        print(f"  {arm:<12} {cfg['model']:<18} {cfg['where']}")

    print("\n## Overall\n")
    print(_table(["Metric", *arms],
                 [[label, *[_cell(data["arms"][a]["summary"].get(key), fmt) for a in arms]]
                  for label, key, fmt in ROWS]))

    print("\n## Intent accuracy by category (graded cases only)\n")
    cats = sorted({c for a in arms for c in data["arms"][a]["by_category"]})
    rows = []
    for cat in cats:
        row = [cat]
        for arm in arms:
            cell = data["arms"][arm]["by_category"].get(cat, {})
            graded = cell.get("intent_graded") or 0
            row.append(f"{cell.get('intent_correct', 0)}/{graded}" if graded else "not graded")
        rows.append(row)
    print(_table(["Category", *arms], rows))

    print("\n## Disagreements (arms gave different intents)\n")
    by_id = {a: {r["id"]: r for r in data["rows"][a]} for a in arms}
    ids = [r["id"] for r in data["rows"][arms[0]]]
    shown = 0
    for case_id in ids:
        answers = {a: by_id[a][case_id]["intent"] for a in arms}
        if len(set(answers.values())) == 1:
            continue
        shown += 1
        first = by_id[arms[0]][case_id]
        print(f"  {case_id} [{first['grade']}] {first['query']!r}")
        for arm in arms:
            row = by_id[arm][case_id]
            mark = {True: "correct", False: "WRONG", None: "-"}[row["intent_correct"]]
            print(f"      {arm:<12} {str(row['intent']):<22} {mark}")
    if not shown:
        print("  (none)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
