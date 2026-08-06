"""
Retrieval-only accuracy harness — no LLM, no DB.

eval/run_eval.py is the full pipeline benchmark, but every question there costs
one to four Ollama round trips (measured at 20-95s each against the remote
proxy), so a 144-question run takes hours. That is far too slow a loop for tuning
retrieval, where nothing downstream of get_relevant_schema is even involved.

This harness scores ONLY the retrieval stage and finishes in seconds, so a signal
weight can be tuned in one sitting.

Metrics, all reusing eval/metrics.py so numbers stay comparable to run_eval:
    top1      gold table ranked first
    hit@k     gold table anywhere in the shortlist  <- what retrieval owns; the
              selector narrows the shortlist to one table afterwards
    MRR       mean reciprocal rank of the gold table
    col_recall  fraction of gold-SQL columns present in retrieved columns
              (only where the dataset carries gold SQL)

Three datasets, see load_dataset() for why they are not interchangeable:
    raq_form  RECOMMENDED. eval/raq_user_queries.json — leak-free, quarterly.
    qa_pairs  quarterly but feeds the qa_index; needs QA_SIGNAL_WEIGHT=0.
    table_qa  the legacy benchmark; MONTHLY tables, so it scores 0.0 here.

Usage:
    python -m scripts.eval_retrieval --dataset raq_form
    python -m scripts.eval_retrieval --dataset raq_form --json after.json
    python -m scripts.eval_retrieval --dataset raq_form --compare before.json

    # A/B the XBRL concept signal without touching any index file:
    CONCEPT_SIGNAL_WEIGHT=0 python -m scripts.eval_retrieval --dataset raq_form
"""
import argparse
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from eval.dataset import load_qa_pairs
from eval.metrics import table_hit, column_recall
import src.config as config
from src.retriever import compute_query_embedding, get_relevant_schema


def load_dataset(name):
    """
    Ground truth, from one of three sources. They are NOT interchangeable.

    table_qa.json (eval.dataset.load_qa_pairs) is the documented benchmark, but
    every one of its 144 questions targets a CIMS_RAQ_M_* (monthly) table, while
    the active EMBEDDING_DIR is the CIMS_RAQ(Quarterly) scope. Scored against the
    quarterly indexes it reports 0.0 on every metric by construction — the gold
    tables are not in the index at all. So it cannot measure this scope.

    qa_pairs.json IS quarterly, but it is also the SOURCE of the qa_index, so it
    must be scored with QA_SIGNAL_WEIGHT=0; otherwise each question retrieves
    itself and the number measures memorisation.

    raq_user_queries.json is the one to use: quarterly, and it feeds no index, so
    it can be scored in full production config.
    """
    if name == "qa_pairs":
        path = os.path.join(config.EMBEDDING_DIR, "qa_pairs.json")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return [{"question": e["question"], "table": e["table"], "gold_sql": e["sql"]}
                for e in data]

    if name == "raq_form":
        # Questions written from the wording on the RAQ return form itself
        # (D:/Repo5.5/Database/2065/RAQBaseFile.xlsx), so they exercise the
        # regulatory vocabulary a bank user actually reads rather than DB column
        # names. Unlike qa_pairs.json this set feeds NO index, so it is the only
        # leak-free ground truth available and can be scored in production config
        # with the qa signal enabled.
        #
        # Rows flagged answerable_today=false expect a table missing from
        # schema.json; they are excluded here so the score measures retrieval
        # rather than the known coverage gap. Pass --include-blocked to see them.
        path = os.path.join(ROOT, "eval", "raq_user_queries.json")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return [{"question": q["question"], "table": q["expected_table"],
                 "gold_sql": "", "answerable_today": q["answerable_today"],
                 "id": q["id"], "tests": q.get("tests", "")}
                for q in data["queries"]]

    return load_qa_pairs()


def run(limit=None, shortlist_k=None, dataset="table_qa", include_blocked=False):
    rows = load_dataset(dataset)
    if not include_blocked:
        blocked = [r for r in rows if r.get("answerable_today") is False]
        if blocked:
            print(f"[info] excluding {len(blocked)} question(s) whose expected table is "
                  f"missing from schema.json (the coverage gap, not a retrieval "
                  f"failure). Use --include-blocked to score them.")
            rows = [r for r in rows if r.get("answerable_today") is not False]
    if limit:
        rows = rows[:limit]

    if dataset == "qa_pairs" and config.QA_SIGNAL_WEIGHT:
        print("[warn] scoring qa_pairs.json with the qa signal ENABLED — this "
              "measures memorisation, not retrieval. Re-run with QA_SIGNAL_WEIGHT=0.")

    per_q = []
    t0 = time.time()
    for i, r in enumerate(rows, 1):
        q, gold = r["question"], r["table"]
        # Reuse ONE embedding per question, exactly as api/routes/query.py does,
        # so the timing here reflects the real request path.
        vec = compute_query_embedding(q)
        tables, columns, _labels, qa_example = get_relevant_schema(
            q, query_vec=vec, shortlist_k=shortlist_k
        )
        names = [t["table"] for t in tables]
        hit, rank = table_hit(gold, names)
        per_q.append({
            "question": q,
            "gold_table": gold,
            "retrieved": names,
            "hit": bool(hit),
            "rank": rank,
            "top1": bool(names and names[0].upper() == gold.upper()),
            # No gold SQL means there is nothing to compute column recall against
            # (the raq_form set carries expected TABLES only), so report None
            # rather than a misleading 0.0.
            "column_recall": (column_recall(gold, r["gold_sql"], columns)
                              if r.get("gold_sql") else None),
            "qa_example_table": (qa_example or {}).get("table"),
            "id": r.get("id"),
            "tests": r.get("tests"),
        })
        if i % 25 == 0:
            print(f"  ... {i}/{len(rows)}")

    n = len(per_q) or 1
    # column_recall is None when the gold table is unknown to schema.json — that
    # is a coverage gap, not a column-retrieval failure, so those questions are
    # excluded from the mean rather than scored as zero.
    recalls = [p["column_recall"] for p in per_q if p["column_recall"] is not None]
    summary = {
        "questions": len(per_q),
        "top1": sum(p["top1"] for p in per_q) / n,
        "hit_at_k": sum(p["hit"] for p in per_q) / n,
        # rank is 1-indexed from table_hit; a miss has rank None.
        "mrr": sum(1.0 / p["rank"] for p in per_q if p["rank"]) / n,
        "column_recall": (sum(recalls) / len(recalls)) if recalls else 0.0,
        "column_recall_scored": len(recalls),
        "elapsed_s": round(time.time() - t0, 1),
        "config": {
            "dataset": dataset,
            "EMBEDDING_DIR": config.EMBEDDING_DIR,
            "QA_SIGNAL_WEIGHT": config.QA_SIGNAL_WEIGHT,
            "CONCEPT_SIGNAL_WEIGHT": config.CONCEPT_SIGNAL_WEIGHT,
            "MEMBER_SIGNAL_WEIGHT": config.MEMBER_SIGNAL_WEIGHT,
            "TOP_K_TABLES": config.TOP_K_TABLES,
            "shortlist_k": shortlist_k,
        },
    }
    return summary, per_q


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--dataset", default="table_qa",
                    choices=["table_qa", "qa_pairs", "raq_form"],
                    help="table_qa=eval/table_qa.json (monthly scope); "
                         "qa_pairs=<EMBEDDING_DIR>/qa_pairs.json (quarterly scope); "
                         "raq_form=eval/raq_user_queries.json (from the RAQ "
                         "Excel form; leak-free)")
    ap.add_argument("--include-blocked", action="store_true",
                    help="also score questions whose expected table is absent from schema.json")
    ap.add_argument("--shortlist-k", type=int,
                    help="evaluate the selector's recall stage instead of the default top_k")
    ap.add_argument("--json", help="write summary + per-question detail here")
    ap.add_argument("--compare", help="a previous --json file to diff against")
    args = ap.parse_args()

    summary, per_q = run(limit=args.limit, shortlist_k=args.shortlist_k,
                         dataset=args.dataset, include_blocked=args.include_blocked)

    print("\n=== retrieval accuracy ===")
    for k in ("questions", "top1", "hit_at_k", "mrr", "column_recall", "elapsed_s"):
        v = summary[k]
        print(f"  {k:<15} {v:.4f}" if isinstance(v, float) else f"  {k:<15} {v}")
    print(f"  concept_weight  {summary['config']['CONCEPT_SIGNAL_WEIGHT']}")
    print(f"  member_weight   {summary['config']['MEMBER_SIGNAL_WEIGHT']}")
    print(f"  qa_weight       {summary['config']['QA_SIGNAL_WEIGHT']}")
    print(f"  dataset         {summary['config']['dataset']}")

    if args.compare and os.path.exists(args.compare):
        with open(args.compare, encoding="utf-8") as f:
            before = json.load(f)
        b, a = before["summary"], summary
        print(f"\n=== vs {args.compare} ===")
        print(f"  {'metric':<15}{'before':>10}{'after':>10}{'delta':>10}")
        for k in ("top1", "hit_at_k", "mrr", "column_recall"):
            print(f"  {k:<15}{b[k]:>10.4f}{a[k]:>10.4f}{a[k] - b[k]:>+10.4f}")

        # Name the questions that actually changed verdict — an aggregate that
        # moves by one or two questions is noise, and only the list shows which.
        before_by_q = {p["question"]: p for p in before["per_question"]}
        gained = [p["question"] for p in per_q
                  if p["top1"] and not before_by_q.get(p["question"], {}).get("top1", False)]
        lost = [p["question"] for p in per_q
                if not p["top1"] and before_by_q.get(p["question"], {}).get("top1", False)]
        print(f"\n  gained top1 ({len(gained)}):")
        for q in gained[:20]:
            print(f"    + {q[:100]}")
        print(f"  lost top1 ({len(lost)}):")
        for q in lost[:20]:
            print(f"    - {q[:100]}")

    if args.json:
        os.makedirs(os.path.dirname(args.json) or ".", exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump({"summary": summary, "per_question": per_q}, f, indent=1)
        print(f"\n[ok] wrote {args.json}")


if __name__ == "__main__":
    main()
