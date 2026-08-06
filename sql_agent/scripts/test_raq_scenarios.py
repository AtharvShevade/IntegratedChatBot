"""
Curated test scenarios for the CIMS_RAQ(Quarterly) NL->SQL pipeline — one file
per accuracy dimension that matters for this return, runnable with or without
Ollama available.

Each scenario is tagged with which STAGE it exercises (retrieval / selection /
generation / execution) and what would make it wrong even if the SQL "validates".
Retrieval-stage scenarios run standalone (no LLM, no DB) in a few seconds.
Generation-stage scenarios need a reachable Ollama backend and are skipped with
a clear message if it is not.

Usage:
    python -m scripts.test_raq_scenarios                # retrieval-only (fast)
    python -m scripts.test_raq_scenarios --with-llm      # + generation scenarios
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.retriever import compute_query_embedding, find_exact_qa_match, get_relevant_schema

# ── Retrieval-stage scenarios: (category, question, expected_table_or_None, why) ──
RETRIEVAL_CASES = [
    (
        "exact-replay",
        "What is the total SLR investment for RAQ?",
        "CIMS_RAQ_Q_SEC6_PART_A",
        "Near-identical to a qa_pairs.json entry — should route straight to the "
        "verified table with no ambiguity.",
    ),
    (
        "dom-vs-overseas",
        "Show the overseas loans and advances by period of delinquency.",
        "CIMS_RAQ_Q_SEC1_PART_C_O",
        "The _DOM / _O table split is a common failure axis — wording "
        "'overseas' must not fall back to the domestic table.",
    ),
    (
        "explicit-section",
        "Show data from Section 10 for MFIs and SHGs",
        "CIMS_RAQ_Q_SEC10",
        "A user who names the section number outranks every embedding score.",
    ),
    (
        "vertical-total",
        "What is the total loan assets for domestic operations?",
        "CIMS_RAQ_Q_SEC1_PART_A_DOM",
        "KNOWN MISS as of this audit — ranks #2 behind SEC1_PART_B_DOM. "
        "Selector should recover it; if the selector is down (see selection "
        "scenarios below) this reaches the SQL model on the wrong table.",
    ),
    (
        "part-b-routing",
        "What is the loss provision held against notes and bonds, domestic operations?",
        "CIMS_RAQ_Q_SEC2_PART_B",
        "KNOWN MISS — the sheet is internally named 'Section2PartB' in the "
        "source Excel but its own header reads 'Part C', so neither wording "
        "routes reliably. Not in the shortlist at all today.",
    ),
    (
        "cross-part-caution",
        "Compare Section 1 Part A with Part B for domestic operations",
        None,
        "No fixed expectation — this is the ADVERSARIAL case. If two tables "
        "are selected, the resulting join MUST NOT rely on CODE=CODE "
        "(semantic_layer.yaml declares exactly this pair joined on CODE, "
        "which is a per-row line-item code, not a shared key — see audit).",
    ),
]


def run_retrieval_cases():
    print("=" * 78)
    print("RETRIEVAL-STAGE SCENARIOS  (no LLM, no DB)")
    print("=" * 78)
    passed = failed = 0
    for cat, q, expect, why in RETRIEVAL_CASES:
        vec = compute_query_embedding(q)
        exact = find_exact_qa_match(q, query_vec=vec)
        tables, columns, labels, qa = get_relevant_schema(q, query_vec=vec, shortlist_k=8)
        names = [t["table"] for t in tables]
        top1 = names[0].upper() if names else None

        if expect is None:
            verdict = "REVIEW"
        else:
            verdict = "PASS" if top1 == expect.upper() else "FAIL"
            passed += verdict == "PASS"
            failed += verdict == "FAIL"

        print(f"\n[{cat}] {verdict}")
        print(f"  Q: {q}")
        print(f"  why it matters: {why}")
        print(f"  exact-match hit: {'yes -> ' + exact['table'] if exact else 'no'}")
        print(f"  top-1: {top1}   (expected: {expect or 'n/a'})")
        print(f"  shortlist: {names}")

    print(f"\n{'-' * 78}")
    print(f"retrieval scenarios: {passed} passed, {failed} failed, "
          f"{len(RETRIEVAL_CASES) - passed - failed} for manual review")
    return failed == 0


# ── Generation-stage scenarios: need a live Ollama backend ──────────────────
GENERATION_CASES = [
    (
        "vertical-double-count",
        "What is the total loan assets across all delinquency buckets, domestic operations?",
        "Must filter to the pre-aggregated TOTAL row (or an equivalent single "
        "value), never SUM() the whole column — that double-counts the total "
        "row against its own components. This is the single most-documented "
        "failure mode in the codebase's own comments.",
    ),
    (
        "unit-conversion",
        "What were the total actual recoveries on infrastructure exposure in crore?",
        "Requires BUSINESS_SEMANTICS_LEVEL>=units. Values are stored in Rs "
        "lakh (confirmed against the RAQBaseFile.xlsx form itself); the "
        "correct answer divides the stored value by 100. Pair with the same "
        "question WITHOUT 'in crore' and confirm the two results are exactly "
        "100x apart.",
    ),
    (
        "stock-vs-flow",
        "What is the total funded advances outstanding on infrastructure across all reporting quarters?",
        "FUN_ADV_OUT is a point-in-time balance (XBRL period_type=instant). "
        "Summing it across RDATE adds March to June. Should warn (with "
        "BUSINESS_SEMANTICS_LEVEL on) or, at minimum, filter to one RDATE.",
    ),
    (
        "code-not-entity",
        "What is the actual recoveries figure for CODE 1000 on the infrastructure table?",
        "CODE is a per-table LINE-ITEM code (1000 = '1. Transport and "
        "adjoining Infrastructure' on SEC8_INFRA_BRKUP), not a bank/entity "
        "id. A correct answer treats it as a row selector; a wrong one "
        "explains it as identifying a reporting entity, per the (currently "
        "incorrect) claim in selector.py's own prompt text.",
    ),
]


def run_generation_cases():
    print("\n" + "=" * 78)
    print("GENERATION-STAGE SCENARIOS  (requires Ollama)")
    print("=" * 78)
    try:
        import requests
        from src import config
        requests.post(config.OLLAMA_URL, json={"model": config.OLLAMA_MODEL,
                      "prompt": "1", "stream": False, "options": {"num_predict": 1}},
                      timeout=(3, 10)).raise_for_status()
    except Exception as e:
        print(f"\n[skip] Ollama backend unreachable ({e}).")
        print("These scenarios describe the EXPECTED behaviour; run manually "
              "against the API once the backend is back:\n")
        for cat, q, why in GENERATION_CASES:
            print(f"  [{cat}]")
            print(f"    Q: {q}")
            print(f"    expect: {why}\n")
        return None

    from src.selector import select_tables
    from src.semantic_layer import load_join_graph
    from src.sql_generator import generate_sql, validate_sql

    for cat, q, why in GENERATION_CASES:
        vec = compute_query_embedding(q)
        tables, columns, labels, qa = get_relevant_schema(q, query_vec=vec, shortlist_k=8)
        tables, selection = select_tables(q, tables, matched_labels=labels,
                                          join_graph=load_join_graph())
        result = generate_sql(q, tables, columns, matched_labels=labels,
                              qa_example=qa, selection=selection)
        sql = result.get("sql", "")
        is_valid, reason = validate_sql(sql, tables, columns)
        print(f"\n[{cat}]")
        print(f"  Q: {q}")
        print(f"  expect: {why}")
        print(f"  table(s): {[t['table'] for t in tables]}")
        print(f"  SQL: {sql}")
        print(f"  valid: {is_valid}  reason: {reason}")
        print(f"  warnings: {result.get('warnings')}")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--with-llm", action="store_true",
                    help="also run generation-stage scenarios (needs Ollama)")
    args = ap.parse_args()

    ok = run_retrieval_cases()
    if args.with_llm:
        run_generation_cases()

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
