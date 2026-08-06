"""
Live verification: run this where the Ollama proxy and Oracle are reachable.

It answers the questions the offline tests cannot:
  1. Does the first generation attempt still come back EMPTY?
     (All 36 records in eval/results/hallucination_log.jsonl had
      first_attempt_sql == "". If num_predict 128 -> 512 fixed it, that stops.)
  2. How many tables reach the SQL model — is it 1 now instead of 3?
  3. Does the Oracle EXPLAIN PLAN dry run work, and does it catch bad SQL?
  4. Does the corrected SQL execute and return rows?

Usage:
    python -m scripts.verify_live
    python -m scripts.verify_live "your own question here" "and another"

Reads nothing but the schema/indexes and writes nothing except the normal
hallucination log; every DB statement is a SELECT or an EXPLAIN PLAN.
"""

import os
import socket
import sys
import time
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import config
from src.retriever import get_relevant_schema, compute_query_embedding, find_exact_qa_match
from src.selector import select_tables
from src.semantic_layer import load_join_graph
from src.sql_generator import generate_sql, validate_sql

DEFAULT_QUESTIONS = [
    # Questions taken from eval/results/hallucination_log.jsonl — every one of
    # these previously produced an empty first attempt and then invalid SQL.
    "show total loan from cims raq",
    "give me risk exposure for domestic",
    "give me total risk exposure from raq",
    "What is the outstanding amount and provision made for each risk category, domestic vs overseas?",
    "total loan assets for the latest quarter",
]


def _reachable(host, port, timeout=5):
    sock = socket.socket()
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
        return True
    except Exception:
        return False
    finally:
        sock.close()


def preflight():
    print("Preflight")
    print("-" * 60)

    parsed = urlparse(config.OLLAMA_URL)
    ollama_ok = _reachable(parsed.hostname, parsed.port or 80)
    print(f"  Ollama  {parsed.hostname}:{parsed.port or 80}  "
          f"{'reachable' if ollama_ok else 'UNREACHABLE'}")

    db_ok = _reachable(config.DB_HOST, config.DB_PORT)
    print(f"  Oracle  {config.DB_HOST}:{config.DB_PORT}  "
          f"{'reachable' if db_ok else 'UNREACHABLE'}")

    print(f"  Model        : {config.OLLAMA_MODEL}")
    print(f"  Selector     : {config.SELECTOR_MODEL}")
    print(f"  num_predict  : {config.MODEL_PROFILES.get(config.OLLAMA_MODEL, {}).get('num_predict')}")
    print(f"  prompt_style : {config.MODEL_PROFILES.get(config.OLLAMA_MODEL, {}).get('prompt_style')}")
    print(f"  SHORTLIST_K  : {config.SHORTLIST_K}")
    print(f"  embeddings   : {config.EMBEDDING_DIR}")
    print(f"  join edges   : {len(load_join_graph())}")

    if not ollama_ok:
        print("\n  Cannot verify generation without Ollama. Stopping.")
        sys.exit(1)
    if not db_ok:
        print("\n  NOTE: Oracle unreachable — the dry run will report 'skipped' and "
              "execution will fail. Generation checks below are still valid.")
    return db_ok


def check_dry_run():
    """Prove the dry run accepts good SQL and rejects a nonexistent column."""
    from src.executor import dry_run_sql

    print("\nOracle dry run (EXPLAIN PLAN)")
    print("-" * 60)

    good = "SELECT CODE, RDATE FROM CIMS_RAQ_Q_SEC1_PART_A_DOM"
    ok, err = dry_run_sql(good)
    print(f"  valid SQL          -> ok={ok}  {err or ''}")
    if err and "skipped" in str(err):
        print("  Dry run unavailable in this environment; it fails open by design.")
        return False

    bad_column = "SELECT NO_SUCH_COLUMN FROM CIMS_RAQ_Q_SEC1_PART_A_DOM"
    ok_bad, err_bad = dry_run_sql(bad_column)
    print(f"  nonexistent column -> ok={ok_bad}  {str(err_bad)[:80]}")

    bad_date = ("SELECT CODE FROM CIMS_RAQ_Q_SEC1_PART_A_DOM "
                "WHERE RDATE = '2023-04-05'")
    ok_date, err_date = dry_run_sql(bad_date)
    print(f"  bare date literal  -> ok={ok_date}  {str(err_date)[:80]}")

    if ok and not ok_bad:
        print("  Working: real errors are caught before the user sees them.")
    else:
        print("  UNEXPECTED: check PLAN_TABLE exists and is writable for this user.")
    return True


def run_question(question, db_ok):
    print(f"\n{'=' * 60}")
    print(f"Q: {question}")
    print("-" * 60)

    started = time.perf_counter()
    query_vec = compute_query_embedding(question)

    exact = find_exact_qa_match(question, query_vec=query_vec)
    if exact:
        print(f"  direct match (>=0.99) -> table {exact['table']}, LLM skipped")
        return {"question": question, "path": "direct_match", "valid": True}

    tables, columns, labels, qa = get_relevant_schema(
        question, query_vec=query_vec, shortlist_k=config.SHORTLIST_K,
    )
    print(f"  shortlist ({len(tables)}): {[t['table'] for t in tables]}")

    tables, selection = select_tables(question, tables, matched_labels=labels,
                                      join_graph=load_join_graph())
    print(f"  selected  ({len(tables)}): {[t['table'] for t in tables]}"
          f"{'' if selection else '   [short-circuit, no selector call]'}")
    if selection:
        for t in selection["tables"]:
            print(f"      {t['table']}: {t.get('why', '')}")
            for c in t.get("columns", []):
                print(f"        - {c['name']}: {c.get('why', '')}")

    selected = {t["table"] for t in tables}
    columns = [c for c in columns if c["table"] in selected]
    labels = [l for l in labels if l["table"] in selected]

    try:
        result = generate_sql(question, tables, columns, matched_labels=labels,
                              qa_example=qa, selection=selection)
    except RuntimeError as e:
        print(f"  GENERATION FAILED: {e}")
        return {"question": question, "path": "error", "valid": False}

    sql = result.get("sql", "")
    is_valid, reason = validate_sql(sql, tables, columns)
    elapsed = (time.perf_counter() - started) * 1000

    print(f"\n  SQL: {sql}")
    print(f"  valid={is_valid}  reason={reason}")
    for w in result.get("warnings") or []:
        print(f"  warning: {w}")

    rows_returned = None
    if is_valid and db_ok:
        from src.executor import execute_query
        cols, rows, db_error = execute_query(sql)
        rows_returned = len(rows)
        print(f"  executed: {rows_returned} row(s){'  ERROR: ' + db_error if db_error else ''}")
        # An empty result on a filtered query is the signature of the padded-label
        # bug — worth calling out, because it is not an error.
        if rows_returned == 0 and not db_error:
            print("  NOTE: zero rows with no error. If the query filters a row label, "
                  "check whether that column needs TRIM() (see needs_trim.json).")

    print(f"  total {elapsed:.0f}ms")
    return {
        "question": question,
        "path": "llm",
        "tables": len(tables),
        "valid": is_valid,
        "rows": rows_returned,
    }


def _questions_from_file(path):
    """One question per line; '#' comments and blank lines ignored."""
    with open(path, encoding="utf-8") as fh:
        return [
            line.strip() for line in fh
            if line.strip() and not line.lstrip().startswith("#")
        ]


def main():
    args = sys.argv[1:]
    if args and args[0] == "--file":
        if len(args) < 2:
            print("usage: python -m scripts.verify_live --file <path>")
            sys.exit(2)
        questions = _questions_from_file(args[1])
        print(f"Loaded {len(questions)} questions from {args[1]}\n")
    else:
        questions = args or DEFAULT_QUESTIONS
    db_ok = preflight()
    if db_ok:
        check_dry_run()

    results = [run_question(q, db_ok) for q in questions]

    print(f"\n{'=' * 60}")
    print("Summary")
    print("-" * 60)
    llm = [r for r in results if r.get("path") == "llm"]
    valid = sum(1 for r in results if r.get("valid"))
    multi = [r for r in llm if (r.get("tables") or 0) > 1]
    print(f"  questions            : {len(results)}")
    print(f"  valid SQL            : {valid}/{len(results)}")
    print(f"  >1 table in prompt   : {len(multi)}  (should only happen for declared joins)")
    print("\n  Now check eval/results/hallucination_log.jsonl:")
    print('    python -c "import json;'
          ' rs=[json.loads(l) for l in open(\'eval/results/hallucination_log.jsonl\')];'
          ' print(sum(1 for r in rs[-20:] if not r[\'first_attempt_sql\']), '
          '\'of the last 20 had an EMPTY first attempt\')"')
    print("  Before this change that count was 36 out of 36.")


if __name__ == "__main__":
    main()
