"""
Validate and merge new question/SQL pairs into a return's qa_pairs.json.

qa_pairs.json is not test data — it feeds three production paths at once: the
direct-match tier (>=0.99 similarity skips the LLM and runs the stored SQL
verbatim), the strong-match tier, and the retrieved few-shot example. A wrong
pair is therefore worse than a missing one: it gets retrieved and copied.

So nothing is merged without passing checks:
  * the table exists in schema.json
  * every column referenced exists on that table
  * the SQL passes the same validate_sql() the pipeline uses
  * with --execute, the SQL actually runs against Oracle and returns rows

Usage:
    python -m scripts.merge_qa_pairs                      # dry run, static checks
    python -m scripts.merge_qa_pairs --execute            # also run each SQL
    python -m scripts.merge_qa_pairs --execute --write    # merge the survivors
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import config
from src.sql_generator import _load_all_columns, validate_sql

TARGET_DIR = config.EMBEDDING_DIR
EXISTING = os.path.join(TARGET_DIR, "qa_pairs.json")
INCOMING = os.path.join(TARGET_DIR, "qa_pairs_new.json")

_SQL_WORDS = {
    "select", "from", "where", "and", "or", "not", "in", "is", "null", "as",
    "order", "by", "group", "having", "asc", "desc", "distinct", "case", "when",
    "then", "else", "end", "on", "join", "left", "inner", "outer", "union", "all",
    "max", "min", "sum", "avg", "count", "trim", "upper", "lower", "to_date",
    "to_char", "extract", "year", "month", "rownum", "fetch", "first", "rows",
    "only", "like", "between", "nvl", "coalesce", "round",
}


def _referenced_columns(sql):
    """Bare identifiers in the SQL that are not keywords, literals or numbers."""
    stripped = re.sub(r"'[^']*'", " ", sql)          # drop string literals
    tokens = re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", stripped)
    return {t.lower() for t in tokens if t.lower() not in _SQL_WORDS}


def main():
    execute = "--execute" in sys.argv
    write = "--write" in sys.argv

    with open(EXISTING, encoding="utf-8") as fh:
        existing = json.load(fh)
    with open(INCOMING, encoding="utf-8") as fh:
        incoming = json.load(fh)

    with open(os.path.join(TARGET_DIR, "schema.json"), encoding="utf-8") as fh:
        schema_tables = {t["table"].lower() for t in json.load(fh)}

    existing_questions = {p["question"].strip().lower() for p in existing}

    print(f"existing pairs : {len(existing)}")
    print(f"incoming pairs : {len(incoming)}")
    print(f"schema tables  : {len(schema_tables)}  ({TARGET_DIR})")
    print(f"mode           : {'EXECUTE' if execute else 'static only'}"
          f"{' + WRITE' if write else ' (dry run)'}\n")

    accepted, rejected = [], []

    for pair in incoming:
        table = pair["table"]
        label = f"{table}: {pair['question'][:58]}"

        if table.lower() not in schema_tables:
            rejected.append((label, "table not in schema.json — rebuild it first"))
            continue

        if pair["question"].strip().lower() in existing_questions:
            rejected.append((label, "duplicate question already in qa_pairs.json"))
            continue

        real_cols = {c["column"].lower() for c in _load_all_columns([table])}
        unknown = _referenced_columns(pair["sql"]) - real_cols - {table.lower()}
        if unknown:
            rejected.append((label, f"unknown identifiers: {sorted(unknown)}"))
            continue

        ok, reason = validate_sql(pair["sql"], [{"table": table}],
                                  _load_all_columns([table]))
        if not ok:
            rejected.append((label, f"validate_sql: {reason}"))
            continue

        if execute:
            from src.executor import execute_query
            _cols, rows, db_error = execute_query(pair["sql"])
            if db_error:
                rejected.append((label, f"execution failed: {db_error[:90]}"))
                continue
            if not rows:
                # Usually a label literal that does not match — the padded-value
                # trap. Valid SQL, useless example.
                rejected.append((label, "executed but returned ZERO rows"))
                continue
            print(f"  OK   {label}  ({len(rows)} rows)")
        else:
            print(f"  OK   {label}")

        accepted.append(pair)
        existing_questions.add(pair["question"].strip().lower())

    print(f"\n{'=' * 70}")
    if rejected:
        print(f"REJECTED {len(rejected)}:")
        for label, why in rejected:
            print(f"  - {label}\n      {why}")
    print(f"\naccepted {len(accepted)} / {len(incoming)}")

    if not write:
        print("\nDry run. Re-run with --execute --write to merge.")
        return
    if not accepted:
        print("\nNothing accepted; qa_pairs.json untouched.")
        return
    if not execute:
        print("\nRefusing to write without --execute: a pair that has never run "
              "against the database can be copied verbatim into a user's answer.")
        return

    backup = EXISTING + ".bak"
    with open(backup, "w", encoding="utf-8") as fh:
        json.dump(existing, fh, indent=2)

    merged = existing + accepted
    with open(EXISTING, "w", encoding="utf-8") as fh:
        json.dump(merged, fh, indent=2)

    print(f"\n  backup  -> {backup}")
    print(f"  merged  -> {EXISTING}  ({len(merged)} pairs)")
    print("\nRebuild the index so the new pairs are searchable:")
    print("  python embedding_building/cims_raq_quarterly/build_qa_index.py")


if __name__ == "__main__":
    main()
