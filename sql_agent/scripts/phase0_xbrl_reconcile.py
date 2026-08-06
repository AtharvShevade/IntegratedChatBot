"""
Phase 0 of the XBRL-metadata integration: reconcile data/<return>.json against
the live Oracle schema and the scoped schema.json, and VALIDATE the two fields
that cannot be trusted on their face.

This script writes no artifacts the pipeline reads — it produces a report so the
later phases build on measured facts instead of assumptions. Run it before
Phase 1 and again whenever the taxonomy JSON or schema.json is regenerated.

Two things it exists to answer:

  1. `db_mapping.filter_column` is the string "Code" for every banded_union and
     narrow_keyvalue mapping, and `filter_value` is an internal metric code
     (1000, 1004, 1696...). But the PHYSICAL column named CODE in these tables
     is the reporting-entity (bank) code — src/selector.py tells the model
     exactly that. If we emitted `WHERE CODE = 1000` we would get zero rows,
     silently, with no error. So: probe the live table and find which physical
     column (if any) actually contains these filter values.

  2. `unit_multiplier` claims 100000 (values stored in Rs lakh) for 187
     concepts. Confirm empirically against live magnitudes rather than trusting
     the extractor.

Usage:
    python -m scripts.phase0_xbrl_reconcile
    python -m scripts.phase0_xbrl_reconcile --json out.json
"""
import argparse
import json
import os
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

TAXONOMY_PATH = os.path.join(ROOT, "data", "2065 1.json")
SCHEMA_PATH = os.path.join(ROOT, "embedding_building", "cims_raq_quarterly", "schema.json")

# Physical columns worth probing as the real home of `filter_value`. CODE is
# included deliberately — the point is to prove or disprove that it holds
# metric codes, not to assume either way.
FILTER_CANDIDATE_COLUMNS = ["TYPEID", "CODE", "ITEM_CODE", "ITEMCODE", "SR_NO", "SRNO"]


def load_taxonomy(path=TAXONOMY_PATH):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_schema(path=SCHEMA_PATH):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def confirmed_mappings(taxonomy):
    """The concepts that carry a usable DB binding: non-abstract, status confirmed."""
    out = []
    for c in taxonomy.get("concepts", []):
        m = c.get("db_mapping") or {}
        if m.get("status") == "confirmed" and not c.get("abstract"):
            out.append(c)
    return out


# ── Section 1: table coverage ────────────────────────────────────────────────
def table_coverage(taxonomy, schema, live_tables):
    xbrl_tables = {
        (c["db_mapping"]["table_name"] or "").upper()
        for c in confirmed_mappings(taxonomy)
        if c["db_mapping"].get("table_name")
    }
    schema_tables = {t["table"].upper() for t in schema}
    live = {t.upper() for t in live_tables if t.upper().startswith("CIMS_RAQ_Q")}
    live_real = {t for t in live if not t.endswith("_BKUP") and not t.endswith("_BACKUP")}

    rows = []
    for t in sorted(xbrl_tables | schema_tables | live_real):
        rows.append({
            "table": t,
            "in_xbrl": t in xbrl_tables,
            "in_schema_json": t in schema_tables,
            "live_in_oracle": t in live_real,
        })
    return rows, xbrl_tables, schema_tables, live_real


# ── Section 2: column agreement ──────────────────────────────────────────────
def column_agreement(taxonomy, schema):
    schema_cols = {
        t["table"].upper(): {c["name"].upper() for c in t["columns"]}
        for t in schema
    }
    stats = Counter()
    mismatches = []
    for c in confirmed_mappings(taxonomy):
        m = c["db_mapping"]
        table = (m.get("table_name") or "").upper()
        col = m.get("column_name") or m.get("value_column")
        if table not in schema_cols:
            stats["table_not_in_schema_json"] += 1
            continue
        if not col:
            stats["no_column_field"] += 1
            continue
        if col.upper() in schema_cols[table]:
            stats["column_confirmed"] += 1
        else:
            stats["column_MISMATCH"] += 1
            mismatches.append({"concept": c["concept_id"], "table": table, "column": col})
    return stats, mismatches


# ── Section 3: live validation of filter_column / filter_value ───────────────
def validate_filter_column(taxonomy, live_tables):
    """
    For each table with banded_union / narrow_keyvalue mappings, take the set of
    filter_values the taxonomy expects and ask the live DB which physical column
    actually contains them. A candidate column "explains" the mapping only if the
    expected values are genuinely present in it.
    """
    try:
        import oracledb
        from src.config import DB_HOST, DB_PORT, DB_SERVICE, DB_USER, DB_PASSWORD
    except Exception as e:
        return {"error": f"oracledb/config unavailable: {e}"}

    by_table = defaultdict(set)
    for c in confirmed_mappings(taxonomy):
        m = c["db_mapping"]
        if m.get("filter_column") and m.get("filter_value") is not None:
            by_table[(m["table_name"] or "").upper()].add(str(m["filter_value"]))

    live = {t.upper() for t in live_tables}
    dsn = oracledb.makedsn(DB_HOST, DB_PORT, service_name=DB_SERVICE)
    try:
        conn = oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=dsn)
    except Exception as e:
        return {"error": f"DB connection failed: {e}"}

    findings = {}
    try:
        cur = conn.cursor()
        for table, expected in sorted(by_table.items()):
            if table not in live:
                findings[table] = {"status": "table_not_live"}
                continue

            # Which of the candidate columns exist on this table?
            cur.execute(
                "SELECT column_name FROM all_tab_columns WHERE table_name = :t",
                {"t": table},
            )
            present = {r[0].upper() for r in cur.fetchall()}
            probes = [c for c in FILTER_CANDIDATE_COLUMNS if c in present]

            per_column = {}
            for col in probes:
                try:
                    cur.execute(f"SELECT DISTINCT {col} FROM {table} WHERE {col} IS NOT NULL")
                    actual = {str(r[0]).strip() for r in cur.fetchall()}
                except Exception as e:
                    per_column[col] = {"error": str(e)[:120]}
                    continue
                overlap = expected & actual
                per_column[col] = {
                    "distinct_live_values": len(actual),
                    "expected_values": len(expected),
                    "overlap": len(overlap),
                    "coverage": round(len(overlap) / len(expected), 3) if expected else 0.0,
                    "sample_live": sorted(actual)[:8],
                }

            # The winner is the column that covers the most expected values —
            # and only counts as an explanation if coverage is non-trivial.
            best = max(
                (c for c in per_column if "coverage" in per_column[c]),
                key=lambda c: per_column[c]["coverage"],
                default=None,
            )
            findings[table] = {
                "status": "probed",
                "expected_filter_values": sorted(expected)[:8],
                "columns_probed": per_column,
                "best_candidate": best,
                "best_coverage": per_column[best]["coverage"] if best else 0.0,
                "verdict": (
                    f"{best} explains the filter values"
                    if best and per_column[best]["coverage"] >= 0.5
                    else "NO physical column explains filter_value - keep quarantined"
                ),
            }
    finally:
        conn.close()
    return findings


# ── Section 4: live validation of unit_multiplier ────────────────────────────
def validate_unit_multiplier(taxonomy, schema, live_tables, per_table_limit=3):
    """
    Sample live magnitudes for monetary columns the taxonomy says are in lakh.
    A bank's balance-sheet line in Rs lakh sits in the 1e2..1e7 range; the same
    figure stored in absolute rupees would be 1e7..1e12. The order of magnitude
    is the evidence, so report it rather than asserting a conclusion.
    """
    try:
        import oracledb
        from src.config import DB_HOST, DB_PORT, DB_SERVICE, DB_USER, DB_PASSWORD
    except Exception as e:
        return {"error": f"oracledb/config unavailable: {e}"}

    schema_cols = {
        t["table"].upper(): {c["name"].upper() for c in t["columns"]}
        for t in schema
    }
    live = {t.upper() for t in live_tables}

    targets = defaultdict(list)
    for c in confirmed_mappings(taxonomy):
        m = c["db_mapping"]
        table = (m.get("table_name") or "").upper()
        col = (m.get("column_name") or "").upper()
        if (
            m.get("unit_multiplier") == 100000
            and col
            and table in live
            and col in schema_cols.get(table, set())
            and len(targets[table]) < per_table_limit
        ):
            targets[table].append((c["label"], col))

    dsn = oracledb.makedsn(DB_HOST, DB_PORT, service_name=DB_SERVICE)
    try:
        conn = oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=dsn)
    except Exception as e:
        return {"error": f"DB connection failed: {e}"}

    out = []
    try:
        cur = conn.cursor()
        for table, cols in sorted(targets.items()):
            for label, col in cols:
                try:
                    cur.execute(
                        f"SELECT MIN({col}), MAX({col}), AVG({col}), COUNT({col}) "
                        f"FROM {table} WHERE {col} IS NOT NULL AND {col} <> 0"
                    )
                    mn, mx, avg, cnt = cur.fetchone()
                except Exception as e:
                    out.append({"table": table, "column": col, "error": str(e)[:120]})
                    continue
                out.append({
                    "table": table,
                    "column": col,
                    "concept_label": label,
                    "non_zero_rows": int(cnt or 0),
                    "min": float(mn) if mn is not None else None,
                    "max": float(mx) if mx is not None else None,
                    "avg": float(avg) if avg is not None else None,
                    "max_order_of_magnitude": (
                        len(str(int(abs(mx)))) - 1 if mx else None
                    ),
                })
    finally:
        conn.close()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", help="also write the full report as JSON to this path")
    ap.add_argument("--no-db", action="store_true", help="skip live DB validation")
    args = ap.parse_args()

    taxonomy = load_taxonomy()
    schema = load_schema()
    mapped = confirmed_mappings(taxonomy)
    ret = taxonomy.get("return_metadata", {}).get("return_code", "?")

    live_tables = []
    if not args.no_db:
        try:
            from src.executor import get_accessible_tables
            live_tables = list(get_accessible_tables())
        except Exception as e:
            print(f"[warn] could not list live tables: {e}")

    print(f"=== Phase 0 reconciliation — return {ret} ===\n")
    print(f"concepts total            : {len(taxonomy.get('concepts', []))}")
    print(f"confirmed + non-abstract  : {len(mapped)}")
    print(f"schema.json tables        : {len(schema)}")
    print(f"live CIMS_RAQ_Q tables    : "
          f"{len([t for t in live_tables if t.upper().startswith('CIMS_RAQ_Q')])}\n")

    # 1. coverage
    rows, xbrl_t, schema_t, live_t = table_coverage(taxonomy, schema, live_tables)
    print("--- 1. TABLE COVERAGE MATRIX ---")
    print(f"{'table':<38} {'xbrl':>5} {'schema':>7} {'live':>5}")
    for r in rows:
        print(f"{r['table']:<38} {'Y' if r['in_xbrl'] else '-':>5} "
              f"{'Y' if r['in_schema_json'] else '-':>7} "
              f"{'Y' if r['live_in_oracle'] else '-':>5}")
    invisible = sorted(live_t - schema_t)
    print(f"\nlive but MISSING from schema.json (invisible to retrieval): {len(invisible)}")
    for t in invisible:
        print(f"    {t}{'   <- has XBRL mappings' if t in xbrl_t else ''}")
    print(f"XBRL-mapped but not live : {sorted(xbrl_t - live_t)}")
    print(f"schema.json but not XBRL : {sorted(schema_t - xbrl_t)}\n")

    # 2. column agreement
    stats, mismatches = column_agreement(taxonomy, schema)
    print("--- 2. COLUMN AGREEMENT (vs schema.json) ---")
    for k, v in stats.most_common():
        print(f"    {k:<28} {v}")
    if mismatches:
        print("    MISMATCHES:")
        for m in mismatches[:20]:
            print(f"      {m}")
    print()

    # 3 + 4. live validation
    filter_findings, unit_findings = {}, {}
    if not args.no_db and live_tables:
        print("--- 3. filter_column / filter_value VALIDATION (live) ---")
        filter_findings = validate_filter_column(taxonomy, live_tables)
        if "error" in filter_findings:
            print(f"    {filter_findings['error']}")
        else:
            for table, f in sorted(filter_findings.items()):
                if f.get("status") != "probed":
                    print(f"    {table:<36} {f.get('status')}")
                    continue
                print(f"    {table:<36} best={f['best_candidate']} "
                      f"coverage={f['best_coverage']}  -> {f['verdict']}")
        print()

        print("--- 4. unit_multiplier VALIDATION (live magnitudes) ---")
        unit_findings = validate_unit_multiplier(taxonomy, schema, live_tables)
        if isinstance(unit_findings, dict) and "error" in unit_findings:
            print(f"    {unit_findings['error']}")
        else:
            print(f"    {'table.column':<52} {'rows':>6} {'max':>18} {'10^':>4}")
            for f in unit_findings:
                if "error" in f:
                    print(f"    {f['table']}.{f['column']}: {f['error']}")
                    continue
                print(f"    {f['table']}.{f['column']:<{max(1, 52-len(f['table'])-1)}} "
                      f"{f['non_zero_rows']:>6} {f['max']:>18,.2f} "
                      f"{f['max_order_of_magnitude']:>4}")
        print()

    if args.json:
        report = {
            "return_code": ret,
            "coverage": rows,
            "live_missing_from_schema_json": invisible,
            "column_agreement": dict(stats),
            "column_mismatches": mismatches,
            "filter_column_validation": filter_findings,
            "unit_multiplier_validation": unit_findings,
        }
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"[ok] wrote {args.json}")


if __name__ == "__main__":
    main()
