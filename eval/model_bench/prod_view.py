"""Replay recorded model outputs through the REAL routing logic.

The raw metrics in scoring.py measure what the model emitted. This measures
what the app would have DONE with it, which is a different and more useful
number, because backend/llm_extractor.py throws most of the model's output
away before it reaches anything:

  1. `_PRECHECK_CMP_RE` (llm_extractor.py:995) classifies compare queries
     BEFORE the LLM is called. On those queries the model is not consulted at
     all, so it can neither win nor lose.
  2. `raw.get("intent", "unknown")` (:1048) -- missing keys are harmless, so
     the schema-completeness metric costs production nothing.
  3. The intent is whitelisted against SIX values (:1047). Every db_* intent
     in the extraction prompt is rejected and collapsed to "unknown".
  4. A keyword override (:1059) rewrites unknown/get_status to compare_reports
     when comparison words appear.
  5. "The LLM is ONLY trusted for intent classification. ALL other fields ...
     are extracted directly from the literal user query via regex" (:1063).
     report_name, dates and times from the model are DISCARDED.
  6. A parse exception is caught (:1032) and degrades to intent "unknown" --
     it does not crash the request, but it does lose the routing.

Consequence: a model that answers perfectly but fences its JSON does not
error; it silently routes every query to "unknown". That is worse than a
crash, because nothing alerts on it.

    python -m eval.model_bench.prod_view
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

RESULTS = Path(__file__).resolve().parent / "results"

# Copied deliberately from backend/llm_extractor.py -- this module models that
# file's behaviour, so the constants must match it, and a test asserts they do.
PROD_INTENTS = {"get_status", "generate_instance", "schedule_report",
                "compare_reports", "query_database", "unknown"}
PRECHECK_CMP = re.compile(r"\b(compare\b|compar\w+|comparative|comparison)\b", re.I)
CMP_OVERRIDE = re.compile(r"\b(compar|varianc|differ|vs\.?|versus|contrast|analys|side.by.side)", re.I)

# Categories whose queries actually reach this extractor. db_qa is routed by
# backend/db_qa/ on its own tier, so scoring the extractor on those queries
# would credit or blame a model for a decision it never makes in production.
REACHES_EXTRACTOR = {"status", "generate", "schedule", "compare", "sql_agent",
                     "conversational"}


def route(query: str, strict_json_ok: bool, intent: str | None) -> tuple[str, str]:
    """Return (final_intent, who_decided) the way llm_extractor.py would."""
    if PRECHECK_CMP.search(query):
        return "compare_reports", "regex (LLM skipped)"
    resolved = intent if (strict_json_ok and intent in PROD_INTENTS) else "unknown"
    decider = "model" if strict_json_ok else "parse failure -> unknown"
    if resolved in ("unknown", "get_status") and CMP_OVERRIDE.search(query):
        return "compare_reports", "keyword override"
    return resolved, decider


def expected(case_intent: str | None) -> str:
    """Collapse a label into the six intents production can actually produce."""
    return case_intent if case_intent in PROD_INTENTS else "unknown"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=None)
    # The counterfactual: assume llm_extractor.py gained fence-tolerant
    # parsing. Answers "would this model be good enough IF we fixed that?",
    # which is the only fair way to judge a model whose content is right and
    # whose packaging is wrong.
    ap.add_argument("--assume-parse-fix", action="store_true")
    args = ap.parse_args()
    path = Path(args.file) if args.file else sorted(RESULTS.glob("*_summary.json"))[-1]
    data = json.loads(path.read_text(encoding="utf-8"))
    arms = list(data["arms"])
    by_id = {a: {r["id"]: r for r in data["rows"][a]} for a in arms}

    mode = "WITH ASSUMED PARSE FIX" if args.assume_parse_fix else "AS DEPLOYED TODAY"
    print(f"# Production-effective routing [{mode}] -- {path.name}\n")
    print("Replays each recorded response through backend/llm_extractor.py's real")
    print("logic: strict parse, six-intent whitelist, compare pre-check and override.\n")

    tallies = {a: {"decided": 0, "correct": 0, "lost_to_parse": 0, "regex": 0} for a in arms}
    losses: list[str] = []

    for case_id in [r["id"] for r in data["rows"][arms[0]]]:
        base = by_id[arms[0]][case_id]
        if base["category"] not in REACHES_EXTRACTOR or base["grade"] != "strict":
            continue
        want = expected(_label_intent(data, case_id))
        line, differ = f"  {case_id} {base['query']!r}", False
        results = {}
        for arm in arms:
            row = by_id[arm][case_id]
            parse_ok = True if args.assume_parse_fix else row["strict_json_ok"]
            got, who = route(row["query"], parse_ok, row["intent"])
            results[arm] = (got, who)
            t = tallies[arm]
            if who.startswith("regex"):
                t["regex"] += 1
            else:
                t["decided"] += 1
                if who.startswith("parse"):
                    t["lost_to_parse"] += 1
                if got == want:
                    t["correct"] += 1
        if len({g for g, _ in results.values()}) > 1 or any(
                g != want for g, _ in results.values()):
            differ = True
        if differ:
            losses.append(line + f"\n      expected {want}\n" + "\n".join(
                f"      {a:<12} {g:<20} [{w}]" for a, (g, w) in results.items()))

    print("| Metric | " + " | ".join(arms) + " |")
    print("|---|" + "---|" * len(arms))
    for label, key in [("Queries reaching the extractor (graded)", "decided"),
                       ("Routed correctly", "correct"),
                       ("Routing lost to a JSON parse failure", "lost_to_parse"),
                       ("Decided by regex before the LLM", "regex")]:
        print(f"| {label} | " + " | ".join(str(tallies[a][key]) for a in arms) + " |")
    print("| **Production routing accuracy** | " + " | ".join(
        f"**{100.0*tallies[a]['correct']/tallies[a]['decided']:.1f}%**"
        if tallies[a]["decided"] else "n/a" for a in arms) + " |")

    print("\n## Queries where routing differs or is wrong\n")
    print("\n".join(losses) if losses else "  (none)")
    return 0


def _label_intent(data: dict, case_id: str) -> str | None:
    labels = json.loads((Path(__file__).parent / "labels.json").read_text(encoding="utf-8"))
    return labels.get(case_id, {}).get("intent")


if __name__ == "__main__":
    raise SystemExit(main())
