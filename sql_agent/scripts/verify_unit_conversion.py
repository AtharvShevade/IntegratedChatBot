"""
End-to-end check of the one claim the business-semantics layer makes that is
purely a correctness fix: unit conversion.

The taxonomy declares monetary columns as Rs lakh (unit_multiplier 100000).
Nothing in the pipeline knew that before, so "in crore" was answered with the raw
stored number — wrong by a factor of 100. This script asks the same question two
ways and checks the arithmetic actually came out 100x apart against live Oracle.

It runs the REAL pipeline (retriever -> selector-free single table -> generate_sql
-> execute), so it also catches the case where the extra prompt block breaks
something that used to work.

Usage:
    BUSINESS_SEMANTICS_LEVEL=aggregation python -m scripts.verify_unit_conversion
    BUSINESS_SEMANTICS_LEVEL=off        python -m scripts.verify_unit_conversion
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import src.config as config
from src.retriever import compute_query_embedding, get_relevant_schema
from src.sql_generator import generate_sql

# Each pair is the SAME question with only the requested unit changed, so a
# correct pipeline must return values exactly 100x apart (1 crore = 100 lakh).
PAIRS = [
    ("What were the total actual recoveries on infrastructure exposure?",
     "What were the total actual recoveries on infrastructure exposure in crore?"),
    ("What is the total funded credit exposure in the infrastructure breakup?",
     "What is the total funded credit exposure in the infrastructure breakup in crore?"),
]


def _one(question):
    vec = compute_query_embedding(question)
    tables, columns, labels, qa = get_relevant_schema(question, query_vec=vec)
    # One table only — mirrors what the selector hands the SQL model in production.
    tables = tables[:1]
    try:
        out = generate_sql(question, tables, columns,
                           matched_labels=labels, qa_example=qa)
    except Exception as e:
        # The Ollama proxy 502s whenever its model backend is unloaded, which is
        # an infrastructure state, not a pipeline defect. Report it as such
        # instead of dying with a traceback halfway through the run.
        return None, None, f"LLM unavailable: {e}", []
    sql = out.get("sql") if isinstance(out, dict) else out
    warnings = out.get("warnings") if isinstance(out, dict) else []

    value, err = None, None
    try:
        from src.executor import execute_query
        cols, rows, err = execute_query(sql)
        if not err and rows:
            for cell in rows[0]:
                if isinstance(cell, (int, float)):
                    value = float(cell)
                    break
    except Exception as e:
        err = str(e)
    return sql, value, err, warnings


def main():
    print(f"BUSINESS_SEMANTICS_LEVEL = {config.BUSINESS_SEMANTICS_LEVEL}\n")
    passed = failed = inconclusive = 0

    for base_q, crore_q in PAIRS:
        print("=" * 78)
        for label, q in (("BASE ", base_q), ("CRORE", crore_q)):
            sql, value, err, warns = _one(q)
            print(f"[{label}] {q}")
            print(f"        SQL: {sql}")
            print(f"        value: {value}   err: {err}")
            for w in warns or []:
                print(f"        warn: {w}")
            if label == "BASE ":
                base_val, base_err = value, err
            else:
                crore_val, crore_err = value, err

        if base_err or crore_err or base_val is None or crore_val is None:
            print("  VERDICT: INCONCLUSIVE (a query did not execute or returned no number)")
            inconclusive += 1
        elif crore_val == 0 and base_val == 0:
            print("  VERDICT: INCONCLUSIVE (both zero - conversion is unobservable)")
            inconclusive += 1
        else:
            ratio = base_val / crore_val if crore_val else float("inf")
            ok = abs(ratio - 100.0) < 1.0
            print(f"  ratio base/crore = {ratio:.4f} (want 100.0)")
            print(f"  VERDICT: {'PASS' if ok else 'FAIL'}")
            passed += ok
            failed += (not ok)

    print("=" * 78)
    print(f"pass={passed} fail={failed} inconclusive={inconclusive}")
    if inconclusive and not passed and not failed:
        print("Nothing was proven. If the errors above say 'LLM unavailable', the "
              "Ollama backend is down (the proxy answers /api/tags but 502s on "
              "/api/generate) — re-run when it recovers.")
    # Inconclusive is not success: exit non-zero so this cannot look green in CI
    # when it actually proved nothing.
    sys.exit(0 if failed == 0 and inconclusive == 0 else 1)


if __name__ == "__main__":
    main()
