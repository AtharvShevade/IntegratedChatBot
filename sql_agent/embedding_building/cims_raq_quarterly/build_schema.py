"""
Builds a scoped schema.json for exactly one return: CIMS_RAQ(Quarterly).

Pipeline (all scoped to this one return, nothing else touched):
  1. Parse data/schema.sql (whole-DB DDL, already extracted) into {table: [{name,type}]}.
  2. Load column descriptions from data/.json-formatted (the Excel-sourced source of truth).
  3. Determine which tables belong to "CIMS_RAQ(Quarterly)" from the descriptions map itself
     (a table belongs to this return if ANY of its columns are tagged with this return_name
     in .json-formatted) — with a consistency check: if a table's columns disagree on
     return_name, it's flagged rather than silently resolved.
  4. Cross-check against tables that are actually live in Oracle right now (skip DDL-only
     ghost tables, and separately report tables that ARE live but have NO Excel description
     at all — these still get a schema entry, just without excel_name enrichment).
  5. Write the result to embedding_building/cims_raq_quarterly/schema.json

Step 4 previously EXCLUDED live-but-undescribed tables despite what this docstring
said, which left 15 live CIMS_RAQ_Q_* tables out of the index entirely —
CIMS_RAQ_Q_SEC11, CIMS_RAQ_Q_GEN_INFO, CIMS_RAQ_Q_SIGNATORY among them. A question
about one of those cannot be answered correctly; retrieval just returns the nearest
described table instead, which is worse than returning nothing. They are now
included by default with descriptions synthesised from their names and columns
(embedding_building/generators.py), and backup tables stay excluded.

Usage:
    python embedding_building/cims_raq_quarterly/build_schema.py
    python embedding_building/cims_raq_quarterly/build_schema.py --described-only
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from embedding_building.parser import parse_schema_and_constraints
from embedding_building.formatter import load_descriptions, build_schema_json
from src.executor import get_accessible_tables

RETURN_NAME = "CIMS_RAQ(Quarterly)"
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEMA_SQL_PATH = os.path.join(ROOT, "data", "schema.sql")
DESCRIPTIONS_PATH = os.path.join(ROOT, "data", ".json-formatted")


def tables_for_return(descriptions: dict, return_name: str):
    """
    Determine table -> set(return_names seen) from the descriptions map,
    restricted to tables that have at least one column tagged with return_name.
    Returns (matched_table_names, inconsistent) where inconsistent is
    {table: {return_name, ...}} for any matched table whose columns disagree.
    """
    table_returns = {}
    for (table, _col), info in descriptions.items():
        rn = info.get("return_name", "").strip()
        if rn:
            table_returns.setdefault(table, set()).add(rn)

    matched = {t for t, rns in table_returns.items() if return_name in rns}
    inconsistent = {t: rns for t, rns in table_returns.items() if t in matched and len(rns) > 1}
    return matched, inconsistent


def main():
    # Live tables with no Excel description are included by default; they are real
    # data users ask about, and leaving them out guarantees a wrong-table answer
    # rather than no answer.
    described_only = "--described-only" in sys.argv

    print(f"Building scoped schema for return: {RETURN_NAME!r}"
          f"{'  (described tables only)' if described_only else ''}\n")

    with open(SCHEMA_SQL_PATH, encoding="utf-8") as f:
        all_tables, ddl_constraints = parse_schema_and_constraints(f.read())
    print(f"Parsed {len(all_tables)} tables total from {SCHEMA_SQL_PATH}")

    # PK/FK/NOT NULL: prefer Oracle's dictionary (data/constraints.json, written
    # by embedding_building/extract_constraints.py) over whatever the checked-in
    # DDL happens to declare — extract_schema.py emits columns only, so the DDL
    # usually declares nothing.
    constraints_path = os.path.join(ROOT, "data", "constraints.json")
    if os.path.exists(constraints_path):
        with open(constraints_path, encoding="utf-8") as f:
            constraints = json.load(f)
        print(f"Key metadata for {len(constraints)} tables from data/constraints.json")
    else:
        constraints = ddl_constraints
        print("No data/constraints.json — run embedding_building/extract_constraints.py "
              "so PK/FK reach the prompt")

    descriptions = load_descriptions(DESCRIPTIONS_PATH)
    described_table_names, inconsistent = tables_for_return(descriptions, RETURN_NAME)
    print(f"Tables tagged {RETURN_NAME!r} in .json-formatted: {len(described_table_names)}")

    if inconsistent:
        print(f"\n[WARN] {len(inconsistent)} table(s) have columns disagreeing on return_name "
              f"(possible Excel copy-paste mistagging) — kept in scope, but review these:")
        for t, rns in sorted(inconsistent.items()):
            print(f"    {t}: {sorted(rns)}")

    try:
        live_tables = get_accessible_tables()
        print(f"\nLive tables in Oracle: {len(live_tables)}")
    except Exception as e:
        print(f"\n[WARN] Could not reach Oracle to cross-check live tables ({e}); "
              f"proceeding without live-table filtering.")
        live_tables = None

    # Scope = described-as-Quarterly-RAQ tables that exist in the parsed DDL.
    # Also surface live CIMS_RAQ_Q_* tables that have NO Excel description at all,
    # so nothing silently goes missing from the scoped build.
    scoped_table_names = {t for t in described_table_names if t.lower() in all_tables}
    missing_from_ddl = described_table_names - scoped_table_names
    if missing_from_ddl:
        print(f"\n[WARN] {len(missing_from_ddl)} described table(s) not found in parsed DDL "
              f"(schema.sql may be stale): {sorted(missing_from_ddl)}")

    if live_tables is not None:
        live_undescribed = {
            t for t in live_tables
            if t.startswith("CIMS_RAQ_Q_") and t not in described_table_names
        }
        # Backup tables are excluded regardless — build_vector_records skips them
        # anyway, and they must never be queried.
        _BACKUP_SUFFIXES = ("_bk", "_bkup", "_bckup", "_backup")
        live_backups = {t for t in live_undescribed if t.lower().endswith(_BACKUP_SUFFIXES)}
        live_undescribed -= live_backups

        if live_undescribed:
            verb = "EXCLUDED" if described_only else "INCLUDED"
            print(f"\n[INFO] {len(live_undescribed)} live CIMS_RAQ_Q_* table(s) have NO Excel "
                  f"description at all -> {verb}"
                  f"{' (descriptions synthesised from names/columns)' if not described_only else ''}:")
            for t in sorted(live_undescribed):
                print(f"    {t}")
            if described_only:
                print("    Questions about these tables CANNOT be answered: retrieval will "
                      "return the nearest described table instead.")
            else:
                print("    Add them to .json-formatted for better descriptions; "
                      "re-run with --described-only to leave them out.")

            if not described_only:
                addable = {t for t in live_undescribed if t.lower() in all_tables}
                if addable != live_undescribed:
                    print(f"    [WARN] {len(live_undescribed - addable)} of these are not in "
                          f"data/schema.sql (stale DDL — re-run extract_schema.py): "
                          f"{sorted(live_undescribed - addable)}")
                scoped_table_names |= addable

        if live_backups:
            print(f"\n[INFO] {len(live_backups)} backup table(s) always excluded: "
                  f"{sorted(live_backups)}")

        before = len(scoped_table_names)
        scoped_table_names = {t for t in scoped_table_names if t in live_tables}
        dropped = before - len(scoped_table_names)
        if dropped:
            print(f"\n[INFO] Dropped {dropped} table(s) not currently live in Oracle (DDL-only/ghost).")

    scoped_tables = {t.lower(): all_tables[t.lower()] for t in scoped_table_names}
    print(f"\nFinal scoped table count: {len(scoped_tables)}")

    schema = build_schema_json(scoped_tables, descriptions, constraints=constraints)

    # Tables added without Excel metadata have no return_name, because that field
    # is derived from the descriptions map. Everything in this build belongs to
    # this return by construction, so tag them — retrieval embeds return_name, and
    # the planned multi-return routing filters on it.
    untagged = [t for t in schema if not t.get("return_name")]
    for entry in untagged:
        entry["return_name"] = RETURN_NAME
        if RETURN_NAME not in entry["text"]:
            entry["text"] = f"{entry['table']} | {RETURN_NAME} | " + entry["text"].split(" | ", 1)[-1]
        if entry.get("summary_text") and RETURN_NAME not in entry["summary_text"]:
            entry["summary_text"] = f"{entry['table']} | {RETURN_NAME} | " + \
                entry["summary_text"].split(" | ", 1)[-1]
    if untagged:
        print(f"\n[INFO] Tagged {len(untagged)} table(s) with return_name {RETURN_NAME!r} "
              f"(no Excel metadata of their own).")

    schema.sort(key=lambda t: t["table"])

    out_path = os.path.join(OUT_DIR, "schema.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)
    print(f"\n-> {out_path} ({len(schema)} tables)")


if __name__ == "__main__":
    main()
