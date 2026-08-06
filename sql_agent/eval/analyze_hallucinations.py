"""
Summarizes src/sql_generator.py's live hallucination log
(eval/results/hallucination_log.jsonl) — every generation that was STILL
invalid after the automatic retry, logged in production/eval use, not just
in a benchmark run.

Usage:
    python -m eval.analyze_hallucinations
"""
import json
import os
from collections import Counter

LOG_PATH = os.path.join(os.path.dirname(__file__), "results", "hallucination_log.jsonl")


def load_records():
    if not os.path.exists(LOG_PATH):
        return []
    records = []
    with open(LOG_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def main():
    records = load_records()
    if not records:
        print(f"No hallucination log found at {LOG_PATH} (or it's empty). Nothing to analyze yet.")
        return

    print(f"Total logged failures (still invalid after retry): {len(records)}\n")

    by_category = Counter(r["final_category"] for r in records)
    print("By category:")
    for cat, n in by_category.most_common():
        print(f"  {n:4d}  {cat}")
    print()

    retry_helped = sum(1 for r in records if r["retry_changed_sql"])
    print(f"Retry produced a DIFFERENT SQL (but still invalid): {retry_helped}/{len(records)}")
    print(f"Retry was a no-op (identical SQL both times):        {len(records) - retry_helped}/{len(records)}\n")

    table_combo_counts = Counter()
    for r in records:
        table_combo_counts[tuple(sorted(r["matched_tables"]))] += 1

    print("Most common matched-table combinations behind failures:")
    for combo, n in table_combo_counts.most_common(10):
        print(f"  {n:4d}  {', '.join(combo) if combo else '(none)'}")
    print()

    print("Most recent 5 failures (question + final category):")
    for r in records[-5:]:
        print(f"  [{r['final_category']}] {r['question'][:80]}")


if __name__ == "__main__":
    main()
