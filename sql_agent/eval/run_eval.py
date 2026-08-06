"""
Accuracy benchmark harness for the NL -> SQL pipeline.

Runs every question in table_qa.json through the real pipeline (retriever ->
sql_generator -> executor) and scores it against the hand-written gold SQL,
producing:
  - retrieval accuracy   (did the right table/columns get matched?)
  - SQL validity rate    (did validate_sql accept the generated SQL?)
  - execution success    (did it run against Oracle without error?)
  - execution accuracy   (did it return the SAME rows as the gold SQL?)

Usage:
  python -m eval.run_eval                  # full run, with DB execution
  python -m eval.run_eval --no-exec        # skip DB execution (retrieval/validity only)
  python -m eval.run_eval --table CIMS_RAQ_M_SEC1_PART_A_DOM
  python -m eval.run_eval --limit 20

  # Score the QUARTERLY scope (the default EMBEDDING_DIR). The default
  # table_qa.json dataset is monthly-only and scores 0 there — see --dataset.
  QA_SIGNAL_WEIGHT=0 python -m eval.run_eval --dataset qa_pairs

  # A/B whole-table prompts against sliced ones:
  CONTEXT_PIPELINE=legacy QA_SIGNAL_WEIGHT=0 python -m eval.run_eval --dataset qa_pairs
  CONTEXT_PIPELINE=slice  QA_SIGNAL_WEIGHT=0 python -m eval.run_eval --dataset qa_pairs

Results land in eval/results/:
  run_<timestamp>.json   — full per-question detail, for later inspection
  latest_summary.md      — human-readable aggregate + per-table breakdown
                           (OVERWRITTEN each run — copy it before an A/B pair)
"""
import argparse
import json
import os
import time
from collections import defaultdict

import src.config as config
from eval.dataset import load_dataset
from eval.metrics import table_hit, column_recall, rows_equal
from src.retriever import compute_query_embedding, get_relevant_schema
from src.sql_generator import generate_sql, validate_sql

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")


def _try_execute(sql):
    """Best-effort DB execution; returns (columns, rows, error) or (None, None, reason) if unavailable."""
    try:
        from src.executor import execute_query
    except Exception as e:
        return None, None, f"executor unavailable: {e}"
    try:
        cols, rows, err = execute_query(sql)
        if err:
            return None, None, err
        return cols, rows, None
    except Exception as e:
        return None, None, f"execution raised: {e}"


def run(limit=None, table_filter=None, do_exec=True, dataset="table_qa"):
    qa_rows = load_dataset(dataset)
    if table_filter:
        qa_rows = [r for r in qa_rows if r["table"].upper() == table_filter.upper()]
    if limit:
        qa_rows = qa_rows[:limit]

    # Two ways to get a meaningless number out of this harness, both of which
    # used to be silent. Say so up front instead.
    if dataset == "table_qa":
        from src import schema_store
        live = {t.upper() for t in schema_store.all_table_names()}
        gold = {r["table"].upper() for r in qa_rows}
        if gold and not (gold & live):
            print(f"\n  [WARN] none of this dataset's {len(gold)} gold tables exist in "
                  f"{config.EMBEDDING_DIR} — every metric will be 0 by construction.")
            print(f"  [WARN] use --dataset qa_pairs for this scope.\n")
    if dataset == "qa_pairs" and config.QA_SIGNAL_WEIGHT:
        print("\n  [WARN] scoring qa_pairs.json with the qa signal ENABLED — this "
              "dataset IS the qa_index,\n  so retrieval measures memorisation. "
              "Re-run with QA_SIGNAL_WEIGHT=0.\n")

    print(f"  dataset={dataset}  questions={len(qa_rows)}  "
          f"CONTEXT_PIPELINE={config.CONTEXT_PIPELINE}  "
          f"EMBEDDING_DIR={config.EMBEDDING_DIR}\n")

    results = []
    for i, row in enumerate(qa_rows, 1):
        question, gold_table, gold_sql = row["question"], row["table"], row["gold_sql"]
        print(f"[{i}/{len(qa_rows)}] {gold_table} :: {question[:70]}")

        # Embed once and reuse, exactly as api/routes/query.py does, so this
        # harness exercises the real request path rather than a variant of it.
        tables, columns, matched_labels, qa_example = get_relevant_schema(
            question, query_vec=compute_query_embedding(question))
        matched_table_names = [t["table"] for t in tables]

        hit, rank = table_hit(gold_table, matched_table_names)
        col_recall = column_recall(gold_table, gold_sql, columns)

        record = {
            "question": question,
            "gold_table": gold_table,
            "gold_sql": gold_sql,
            "matched_tables": matched_table_names,
            "table_hit": hit,
            "table_rank": rank,
            "column_recall": col_recall,
            "pred_sql": None,
            "sql_valid": False,
            "validation_reason": None,
            "warnings": [],
            "exec_success": None,
            "exec_match": None,
            "exec_error": None,
            "generation_error": None,
        }

        if not tables:
            results.append(record)
            _checkpoint(results)
            continue

        # The Ollama endpoint is a shared remote proxy and occasionally throws
        # a transient 502/timeout mid-run. A single flaky call shouldn't nuke
        # every result already computed in a ~150-question run — retry once,
        # then record the failure on this question and move on.
        gen = None
        gen_error = None
        for attempt in range(2):
            try:
                gen = generate_sql(question, tables, columns, matched_labels=matched_labels, qa_example=qa_example)
                gen_error = None
                break
            except Exception as e:
                gen_error = str(e)
                print(f"  [warn] generate_sql failed (attempt {attempt + 1}/2): {gen_error}")

        if gen is None:
            record["generation_error"] = gen_error
            results.append(record)
            _checkpoint(results)
            continue

        pred_sql = gen.get("sql", "")
        record["pred_sql"] = pred_sql
        record["warnings"] = gen.get("warnings", [])

        is_valid, reason = validate_sql(pred_sql, tables, columns)
        record["sql_valid"] = is_valid
        record["validation_reason"] = reason

        if do_exec and is_valid:
            pred_cols, pred_rows, pred_err = _try_execute(pred_sql)
            gold_cols, gold_rows, gold_err = _try_execute(gold_sql)
            record["exec_success"] = pred_err is None
            record["exec_error"] = pred_err
            if pred_err is None and gold_err is None:
                record["exec_match"] = rows_equal(pred_cols, pred_rows, gold_cols, gold_rows)
            elif gold_err is not None:
                record["exec_error"] = f"gold SQL also failed: {gold_err}"

        results.append(record)
        _checkpoint(results)

    return results


def _checkpoint(results):
    """
    Overwrite a running checkpoint after every question so a crash partway
    through a long run (e.g. the remote Ollama proxy going down) doesn't
    discard everything already computed — resume by re-running with a
    smaller --limit past the last completed question, or just inspect what's
    here.
    """
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "_checkpoint.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)


def summarize(results):
    n = len(results)
    hits = [r for r in results if r["table_hit"]]
    recalls = [r["column_recall"] for r in results if r["column_recall"] is not None]
    valid = [r for r in results if r["sql_valid"]]
    exec_attempted = [r for r in results if r["exec_success"] is not None]
    exec_ok = [r for r in exec_attempted if r["exec_success"]]
    exec_matched = [r for r in results if r["exec_match"] is True]
    exec_match_attempted = [r for r in results if r["exec_match"] is not None]

    gen_errors = [r for r in results if r.get("generation_error")]

    summary = {
        "total_questions": n,
        "table_retrieval_accuracy": len(hits) / n if n else None,
        "avg_column_recall": sum(recalls) / len(recalls) if recalls else None,
        "sql_validity_rate": len(valid) / n if n else None,
        "execution_success_rate": (len(exec_ok) / len(exec_attempted)) if exec_attempted else None,
        "execution_match_accuracy": (len(exec_matched) / len(exec_match_attempted)) if exec_match_attempted else None,
        "generation_errors": len(gen_errors),
        # Recorded so an A/B pair cannot be mixed up after the fact: the two
        # runs differ ONLY in these, and latest_summary.md is overwritten.
        "config": {
            "CONTEXT_PIPELINE": config.CONTEXT_PIPELINE,
            "EMBEDDING_DIR": config.EMBEDDING_DIR,
            "OLLAMA_MODEL": config.OLLAMA_MODEL,
            "QA_SIGNAL_WEIGHT": config.QA_SIGNAL_WEIGHT,
        },
    }

    per_table = defaultdict(lambda: {"n": 0, "hits": 0, "valid": 0, "exec_match": 0, "exec_match_n": 0})
    for r in results:
        t = per_table[r["gold_table"]]
        t["n"] += 1
        t["hits"] += int(r["table_hit"])
        t["valid"] += int(r["sql_valid"])
        if r["exec_match"] is not None:
            t["exec_match_n"] += 1
            t["exec_match"] += int(r["exec_match"])

    return summary, per_table


def write_reports(results, summary, per_table):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")

    detail_path = os.path.join(RESULTS_DIR, f"run_{stamp}.json")
    with open(detail_path, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "results": results}, f, indent=2)

    cfg = summary.get("config", {})
    lines = [
        f"# Accuracy Report — {stamp}",
        "",
        f"`CONTEXT_PIPELINE={cfg.get('CONTEXT_PIPELINE')}` · "
        f"`QA_SIGNAL_WEIGHT={cfg.get('QA_SIGNAL_WEIGHT')}` · "
        f"`{cfg.get('EMBEDDING_DIR')}` · `{cfg.get('OLLAMA_MODEL')}`",
        "",
        "## Overall",
        f"- Questions evaluated: **{summary['total_questions']}**",
        f"- Table retrieval accuracy: **{_pct(summary['table_retrieval_accuracy'])}**",
        f"- Avg. column recall: **{_pct(summary['avg_column_recall'])}**",
        f"- SQL validity rate: **{_pct(summary['sql_validity_rate'])}**",
        f"- Execution success rate (of valid SQL run against DB): **{_pct(summary['execution_success_rate'])}**",
        f"- Execution match accuracy (rows == gold SQL's rows): **{_pct(summary['execution_match_accuracy'])}**",
        "",
        "## Per-table breakdown",
        "",
        "| Table | N | Table Hit % | SQL Valid % | Exec Match % |",
        "|---|---|---|---|---|",
    ]
    for table, t in sorted(per_table.items()):
        hit_pct = _pct(t["hits"] / t["n"]) if t["n"] else "-"
        valid_pct = _pct(t["valid"] / t["n"]) if t["n"] else "-"
        exec_pct = _pct(t["exec_match"] / t["exec_match_n"]) if t["exec_match_n"] else "n/a"
        lines.append(f"| {table} | {t['n']} | {hit_pct} | {valid_pct} | {exec_pct} |")

    summary_path = os.path.join(RESULTS_DIR, "latest_summary.md")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    return detail_path, summary_path


def _pct(x):
    return "n/a" if x is None else f"{x * 100:.1f}%"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--table", type=str, default=None)
    parser.add_argument("--no-exec", action="store_true", help="skip DB execution, only score retrieval + SQL validity")
    parser.add_argument("--dataset", default="table_qa", choices=["table_qa", "qa_pairs"],
                        help="table_qa=table_qa.json (MONTHLY tables — scores 0 against "
                             "the quarterly build); qa_pairs=<EMBEDDING_DIR>/qa_pairs.json "
                             "(quarterly; needs QA_SIGNAL_WEIGHT=0 to be leak-free)")
    args = parser.parse_args()

    results = run(limit=args.limit, table_filter=args.table, do_exec=not args.no_exec,
                  dataset=args.dataset)
    summary, per_table = summarize(results)
    detail_path, summary_path = write_reports(results, summary, per_table)

    print("\n=== SUMMARY ===")
    for k, v in summary.items():
        if k == "config":
            continue
        print(f"{k}: {_pct(v) if isinstance(v, float) else v}")
    print(f"\nDetail:  {detail_path}")
    print(f"Summary: {summary_path}")
