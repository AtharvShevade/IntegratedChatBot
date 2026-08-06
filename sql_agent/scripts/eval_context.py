"""
Context-quality harness — no LLM, no DB.

`scripts/eval_retrieval.py` measures RANKING (did the right table come back).
`eval/run_eval.py` measures the end-to-end answer but costs one to four Ollama
round trips per question. Neither one can answer the question schema slicing
actually raises:

    we cut the prompt in half — did we cut anything the query needed?

That is what this measures, over a question set with gold SQL, in seconds:

    col_recall      of the columns the GOLD SQL references, how many survived
                    slicing. This is the SAFETY metric and it must stay ~1.0 —
                    a drop here means the slice made a correct answer
                    unwritable, which no token saving justifies.
    col_precision   of the columns we kept, how many the gold SQL actually
                    used. This is the metric slicing is supposed to move.
    label_recall    of the row-label LITERALS the gold SQL filters on, how many
                    are present in the slice. A missing literal is the silent
                    empty-result failure: the model cannot invent
                    'C. Total ( A + B)' character-for-character.
    tokens          rendered DDL size, legacy vs sliced, same estimator as
                    scratch/sql_generation_context_report.md (chars ÷ 4).
    low_binding     fraction of slices built with no confident column binding —
                    "sliced well" and "sliced blind" look identical in a token
                    count, so they are reported separately.

Slicing is scored against the GOLD table by default, which deliberately isolates
slicing quality from retrieval quality (use --retrieved to score the composite
instead, which is what a user actually gets).

Usage:
    python -m scripts.eval_context
    python -m scripts.eval_context --dataset qa_pairs --json after.json
    python -m scripts.eval_context --compare before.json
    python -m scripts.eval_context --retrieved      # score the real pipeline table
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import src.config as config
from src import schema_store
from src.context.budget import BudgetTracker, ContextBudget
from src.context.intent import detect_intent
from src.context.slicer import slice_table
from src.context.types import LabelBinding
from src.retriever import compute_query_embedding, get_relevant_schema
from src.sql_generator import build_table_ddl


def load_dataset(name):
    """qa_pairs.json is the only set carrying gold SQL, which every column/label
    metric here needs. eval/raq_user_queries.json holds expected TABLES only, so
    it can score retrieval but not slicing."""
    if name == "qa_pairs":
        path = os.path.join(config.EMBEDDING_DIR, "qa_pairs.json")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return [{"question": e["question"], "table": e["table"], "gold_sql": e["sql"]}
                for e in data]
    raise SystemExit(f"dataset {name!r} has no gold SQL — nothing to score slicing against")


def gold_columns(table, gold_sql):
    """Real columns of `table` that the gold SQL names. Same approach as
    eval.metrics.column_recall, so the numbers stay comparable."""
    real = {c["column"].lower() for c in schema_store.columns_for([table])}
    upper = gold_sql.upper()
    return {c for c in real if re.search(rf'\b{re.escape(c.upper())}\b', upper)}


def gold_label_literals(table, gold_sql):
    """
    Quoted literals in the gold SQL that are REAL sampled row-label values of
    `table`. Compared on the stripped form, because a padded stored value is
    offered to the model trimmed with a TRIM() instruction.
    """
    quoted = {m.group(1) for m in re.finditer(r"'([^']+)'", gold_sql)}
    if not quoted:
        return set()
    known = {
        v.strip()
        for values in schema_store.labels_for(table).values()
        for v in values
    }
    return {q.strip() for q in quoted if q.strip() in known}


def render(table, selected_columns=None, label_values=None):
    entry = schema_store.table_entries([table]).get(table.lower())
    if entry is None:
        return ""
    return build_table_ddl(entry, label_values=label_values or {},
                           selected_tables=[table], selected_columns=selected_columns)


def legacy_label_values(table):
    """
    What the legacy path put in front of the model: every sampled value for the
    table, which build_table_ddl then truncates at MAX_LABELS_DDL in sample
    order. Reproduced here so the comparison is against real behaviour rather
    than an idealised baseline.
    """
    return {col: list(vals) for col, vals in schema_store.labels_for(table).items()}


def run(dataset="qa_pairs", limit=None, use_retrieved=False):
    rows = load_dataset(dataset)
    if limit:
        rows = rows[:limit]

    budget = ContextBudget.from_config()
    per_q = []

    for i, r in enumerate(rows, 1):
        q, gold_table, gold_sql = r["question"], r["table"], r["gold_sql"]

        vec = compute_query_embedding(q)
        tables, columns, matched_labels, _qa = get_relevant_schema(
            q, query_vec=vec, shortlist_k=config.SHORTLIST_K)
        retrieved_top = tables[0]["table"] if tables else None
        target = (retrieved_top or gold_table) if use_retrieved else gold_table

        intent = detect_intent(q)
        tracker = BudgetTracker(budget)
        evidence = [c["column"] for c in columns if c["table"].lower() == target.lower()]
        label_bindings = [
            LabelBinding(table=target, column=l["column"], value=l["value"],
                         confidence=max(0.05, 1.0 - n * 0.05))
            for n, l in enumerate(l for l in matched_labels
                                  if l["table"].lower() == target.lower())
        ]

        sliced = slice_table(target, intent, bindings=(),
                             matched_labels=label_bindings,
                             evidence_columns=evidence,
                             budget=budget, tracker=tracker, query=q)
        report = tracker.report()

        if sliced is None:
            per_q.append({"question": q, "gold_table": gold_table, "skipped": "no schema entry"})
            continue

        kept = {c.name.lower() for c in sliced.columns}
        want_cols = gold_columns(gold_table, gold_sql) if target.lower() == gold_table.lower() else set()
        want_labels = gold_label_literals(gold_table, gold_sql) if target.lower() == gold_table.lower() else set()
        have_labels = {l.value.strip() for l in sliced.labels}

        legacy_ddl = render(target)
        sliced_ddl = render(target, selected_columns=list(sliced.column_names),
                            label_values=sliced.labels_by_column())
        # The legacy prompt supplements the ranked labels with every sampled
        # value before truncating, so its label block is the full sample list.
        legacy_ddl_full = render(target, label_values=legacy_label_values(target))

        per_q.append({
            "question": q,
            "gold_table": gold_table,
            "target": target,
            "retrieved_top": retrieved_top,
            "top1": bool(retrieved_top and retrieved_top.upper() == gold_table.upper()),
            "intent": intent.kind,
            "cols_kept": len(kept),
            "cols_total": sliced.total_columns,
            "col_recall": (len(want_cols & kept) / len(want_cols)) if want_cols else None,
            "col_precision": (len(want_cols & kept) / len(kept)) if (want_cols and kept) else None,
            "missed_columns": sorted(want_cols - kept),
            "label_recall": (len(want_labels & have_labels) / len(want_labels)) if want_labels else None,
            "missed_labels": sorted(want_labels - have_labels),
            "labels_kept": len(sliced.labels),
            "tokens_legacy": (len(legacy_ddl_full) + 3) // 4,
            "tokens_sliced": (len(sliced_ddl) + 3) // 4,
            "low_binding": report.low_binding,
            "drops": len(report.drops),
        })
        if i % 25 == 0:
            print(f"  ... {i}/{len(rows)}")

    scored = [p for p in per_q if not p.get("skipped")]
    n = len(scored) or 1

    def mean(key):
        vals = [p[key] for p in scored if p.get(key) is not None]
        return (sum(vals) / len(vals)) if vals else 0.0

    tok_legacy = sum(p["tokens_legacy"] for p in scored)
    tok_sliced = sum(p["tokens_sliced"] for p in scored)
    summary = {
        "questions": len(scored),
        "skipped": len(per_q) - len(scored),
        "col_recall": mean("col_recall"),
        "col_precision": mean("col_precision"),
        "label_recall": mean("label_recall"),
        "col_recall_perfect": sum(1 for p in scored if p.get("col_recall") == 1.0) / n,
        "label_recall_perfect": sum(1 for p in scored
                                    if p.get("label_recall") in (None, 1.0)) / n,
        "avg_cols_kept": mean("cols_kept"),
        "avg_cols_total": mean("cols_total"),
        "avg_labels_kept": mean("labels_kept"),
        "tokens_legacy_avg": tok_legacy / n,
        "tokens_sliced_avg": tok_sliced / n,
        "token_reduction": (1 - tok_sliced / tok_legacy) if tok_legacy else 0.0,
        "low_binding_rate": sum(1 for p in scored if p["low_binding"]) / n,
        "config": {
            "dataset": dataset,
            "scored_on": "retrieved_top1" if use_retrieved else "gold_table",
            "EMBEDDING_DIR": config.EMBEDDING_DIR,
            "budget": budget.__dict__,
        },
    }
    return summary, per_q


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="qa_pairs", choices=["qa_pairs"])
    ap.add_argument("--limit", type=int)
    ap.add_argument("--retrieved", action="store_true",
                    help="slice the RETRIEVED top-1 table instead of the gold table "
                         "(scores retrieval and slicing together)")
    ap.add_argument("--json")
    ap.add_argument("--compare")
    args = ap.parse_args()

    summary, per_q = run(dataset=args.dataset, limit=args.limit,
                         use_retrieved=args.retrieved)

    print("\n=== context quality ===")
    print(f"  scored on         {summary['config']['scored_on']}  ({summary['questions']} questions)")
    print(f"  col_recall        {summary['col_recall']:.4f}   <- SAFETY: must stay ~1.0")
    print(f"  col_precision     {summary['col_precision']:.4f}")
    print(f"  label_recall      {summary['label_recall']:.4f}")
    print(f"  perfect col_recall    {summary['col_recall_perfect']:.4f}")
    print(f"  perfect label_recall  {summary['label_recall_perfect']:.4f}")
    print(f"  columns kept      {summary['avg_cols_kept']:.1f} of {summary['avg_cols_total']:.1f}")
    print(f"  labels kept       {summary['avg_labels_kept']:.1f}")
    print(f"  DDL tokens        {summary['tokens_legacy_avg']:.0f} -> "
          f"{summary['tokens_sliced_avg']:.0f}  ({summary['token_reduction']:.1%} saved)")
    print(f"  low_binding rate  {summary['low_binding_rate']:.4f}")

    lost = [p for p in per_q if p.get("col_recall") is not None and p["col_recall"] < 1.0]
    if lost:
        print(f"\n  !! {len(lost)} question(s) lost a gold column to slicing:")
        for p in lost[:15]:
            print(f"    - {p['gold_table']}: missing {p['missed_columns']}  | {p['question'][:70]}")

    lost_lbl = [p for p in per_q if p.get("label_recall") is not None and p["label_recall"] < 1.0]
    if lost_lbl:
        print(f"\n  !! {len(lost_lbl)} question(s) lost a gold row-label literal:")
        for p in lost_lbl[:15]:
            print(f"    - {p['gold_table']}: missing {p['missed_labels']}  | {p['question'][:70]}")

    if args.compare and os.path.exists(args.compare):
        with open(args.compare, encoding="utf-8") as f:
            before = json.load(f)["summary"]
        print(f"\n=== vs {args.compare} ===")
        print(f"  {'metric':<20}{'before':>10}{'after':>10}{'delta':>10}")
        for k in ("col_recall", "col_precision", "label_recall",
                  "tokens_sliced_avg", "low_binding_rate"):
            print(f"  {k:<20}{before[k]:>10.4f}{summary[k]:>10.4f}{summary[k]-before[k]:>+10.4f}")

    if args.json:
        os.makedirs(os.path.dirname(args.json) or ".", exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump({"summary": summary, "per_question": per_q}, f, indent=1)
        print(f"\n[ok] wrote {args.json}")


if __name__ == "__main__":
    main()
