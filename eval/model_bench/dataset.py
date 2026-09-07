"""Test set for the model comparison.

Deliberately authors NO new queries. The 56 single-turn English queries in
eval/multilingual/dataset/queries_en.jsonl already cover every category the
benchmark needs -- status, generate, schedule, compare, db Q&A, SQL analytics,
conversational -- and were written before any of these models were on the
table, so they cannot have been tuned to favour one.

labels.json adds the one thing that file lacks: the expected intent. It is
hand-written and every entry carries a `grade`, because a third of these
queries have no single defensible answer and scoring them would invent a
result rather than measure one.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
QUERIES = ROOT.parent / "multilingual" / "dataset" / "queries_en.jsonl"
LABELS = ROOT / "labels.json"


def load_cases() -> list[dict]:
    """Return the labelled cases, in file order.

    Multi-turn cases are excluded: they carry no `text` field because they are
    turn sequences, and giving one model conversation history that another
    does not get would break the fair-comparison rule.
    """
    labels = {k: v for k, v in json.loads(LABELS.read_text(encoding="utf-8")).items()
              if not k.startswith("_")}
    cases = []
    for line in QUERIES.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("multi_turn") or "text" not in row:
            continue
        label = labels.get(row["id"])
        if label is None:
            raise KeyError(f"{row['id']} has no entry in labels.json")
        cases.append({
            "id": row["id"],
            "category": row["category"],
            "expected_tier": row["expected_tier"],
            "query": row["text"],
            **label,
        })
    return cases
