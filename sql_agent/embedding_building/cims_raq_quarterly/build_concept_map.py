"""
Phase 1 of the XBRL-metadata integration: distil data/<return>.json into a
compact `concept_map.json` that the runtime can load cheaply.

The taxonomy export is 3.3 MB of XBRL machinery — 774 concepts, 528 of them
abstract presentation scaffolding, plus role URIs, join provenance and local
filesystem paths. None of that belongs in a request path. This script keeps only
the facts that change an answer, resolves every QName to the human label a user
would actually type, and writes one flat artifact.

What it keeps, and why (see scripts/phase0_xbrl_reconcile.py for the evidence):

  * label -> physical table + column        the business-vocabulary binding
  * row_code_column / row_code             CODE is a per-table ROW code, not the
                                           reporting entity. Phase 0 proved this:
                                           CODE 1000 <-> '1. Transport and adjoining
                                           Infrastructure'. So a concept's filter_value
                                           is a DETERMINISTIC row selector - far more
                                           robust than string-matching a row label.
  * unit_multiplier                        taxonomy-declared reporting unit
  * period_type                            instant (stock) vs duration (flow) ->
                                           whether summing across RDATE is ever valid
  * mapping_type / value_column            the physical shape of the metric
  * axes + members                         dimension vocabulary and filter literals
  * formulas                               derivation for metrics with no column

Everything else is dropped: see the module docstring of src/concept_map.py for
the consumer side.

Run after the taxonomy JSON changes:
    python embedding_building/cims_raq_quarterly/build_concept_map.py
    python embedding_building/cims_raq_quarterly/build_concept_map.py --taxonomy "data/2065 1.json"
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TAXONOMY = os.path.join(ROOT, "data", "2065 1.json")
OUT_PATH = os.path.join(OUT_DIR, "concept_map.json")

# Rule categories worth carrying. `unclassified_or_reserved` (96 of 346) is
# exactly what its name says and carries no trustworthy meaning, so it is
# dropped rather than shipped as if it were a real business rule.
USEFUL_RULE_CATEGORIES = {
    "cross_concept_rollup",
    "business_threshold",
    "conditional_mandatory",
    "unconditional_mandatory",
}

# XBRL data types -> the one word that matters for SQL: how to aggregate and
# how to render. Anything not listed is carried through as "other".
_MEASURE_KIND = {
    "xbrli:monetaryItemType": "monetary",
    "num:percentItemType": "percent",
    "xbrli:pureItemType": "ratio",
    "xbrli:integerItemType": "count",
    "xbrli:stringItemType": "text",
    "xbrli:dateItemType": "date",
    "xbrli:dateTimeItemType": "date",
}

_ACRONYMS = (
    "NPA", "NPAs", "SMA", "MFIs", "SHGs", "IRAC", "RBI", "FCNRB", "LC", "BG",
    "MSME", "PSL", "CC", "OD", "AUC", "FY", "UCA",
)


def strip_prefix(qname: str) -> str:
    """'in-rbi-rep:AssetClassificationAxis' -> 'AssetClassificationAxis'."""
    return (qname or "").split(":")[-1]


def humanise(qname: str) -> str:
    """
    Turn a CamelCase QName into readable words, so an embedding sees English
    instead of one giant token: 'AssetClassificationAxis' -> 'asset classification'.

    Trailing Axis/Domain/Member/Hypercube/LineItems are structural suffixes, not
    part of the business name, so they go. Known acronyms stay upper-case.
    """
    name = strip_prefix(qname)
    name = re.sub(r"(Axis|Domain|Member|Members|Hypercube|LineItems|Table)$", "", name)
    # split on camel boundaries, keeping runs of capitals together (NPAs, MFIs)
    words = re.findall(r"[A-Z]+(?![a-z])|[A-Z][a-z']*|\d+", name)
    if not words:
        return name.lower()
    out = []
    for w in words:
        out.append(w if w in _ACRONYMS or (w.isupper() and len(w) > 1) else w.lower())
    return " ".join(out).strip()


def _label_of(concept_id, label_index):
    """Prefer the taxonomy's own label; fall back to humanising the QName."""
    lbl = label_index.get(concept_id)
    if lbl:
        # Labels carry XBRL role suffixes like '[member]' that add no meaning.
        return re.sub(r"\s*\[(member|axis|domain|abstract|line items)\]\s*$", "",
                      lbl, flags=re.IGNORECASE).strip()
    return humanise(concept_id)


def _mark_row_code_usability(metrics):
    """
    Decide, per metric, whether its `row_code` actually SELECTS that metric's row
    — and record the answer as `row_code_selects_metric` so the runtime never has
    to re-derive it.

    This distinction is not cosmetic; getting it wrong produces confidently wrong
    SQL. Two different things wear the same `filter_value` field:

      narrow_keyvalue  The table is vertical: one VALUE column, and CODE says
                       which metric the row holds. CODE 1004 on GEN_INFO IS
                       'Address'. Always a selector.

      banded_union     The table is wide: one row per dimension member, one
                       column per metric. Here `filter_value` is the START OF THE
                       CODE BAND for the whole table, not a per-metric row. On
                       CIMS_RAQ_Q_SEC8_INFRA_BRKUP all 24 concepts carry
                       filter_value 1000, and CODE 1000 is the row
                       '1. Transport and adjoining Infrastructure'. Telling the
                       model to filter CODE = 1000 for 'Actual recoveries' would
                       silently restrict every answer to the Transport row.

    So a banded_union code counts as a selector only when the table's banded_union
    concepts genuinely disagree about it (>= 2 distinct codes). One code shared by
    several concepts is a band start. A lone banded_union concept is
    indistinguishable from either case on this evidence, so it is treated as a
    band start — the conservative choice, which costs only the row hint and falls
    back to the row-label literal the prompt already carries.
    """
    distinct_banded = {}
    for m in metrics:
        if m["mapping_type"] == "banded_union" and m["row_code"] is not None:
            distinct_banded.setdefault(m["table"], set()).add(m["row_code"])

    for m in metrics:
        if m["row_code"] is None or not m["row_code_column"]:
            m["row_code_selects_metric"] = False
        elif m["mapping_type"] == "narrow_keyvalue":
            m["row_code_selects_metric"] = True
        elif m["mapping_type"] == "banded_union":
            m["row_code_selects_metric"] = len(distinct_banded.get(m["table"], ())) >= 2
        else:  # wide_column carries no filter at all
            m["row_code_selects_metric"] = False


def build(taxonomy):
    concepts = taxonomy.get("concepts", [])
    label_index = {c["concept_id"]: c.get("label") for c in concepts}
    return_code = taxonomy.get("return_metadata", {}).get("return_code", "unknown")

    # ── role URI -> human role name, from structure.tables ───────────────────
    role_names = {}
    for t in taxonomy.get("structure", {}).get("tables", []):
        role_names[t["role_uri"]] = humanise(t["table_role"])

    # ── axes -> members, both humanised ──────────────────────────────────────
    axes = []
    member_to_axes = {}
    for a in taxonomy.get("structure", {}).get("axes", []):
        axis_label = _label_of(a["axis_name"], label_index) or humanise(a["axis_name"])
        members = []
        for m in a.get("members", []):
            m_label = _label_of(m, label_index)
            members.append({"member_id": m, "label": m_label})
            member_to_axes.setdefault(m, []).append(axis_label)
        axes.append({
            "axis_id": a["axis_name"],
            "label": axis_label,
            "domain": a.get("domain"),
            "domain_label": _label_of(a.get("domain", ""), label_index),
            "members": members,
        })
    axis_label_by_id = {a["axis_id"]: a["label"] for a in axes}

    # ── formulas, keyed by assertion id ──────────────────────────────────────
    formulas = {}
    for r in taxonomy.get("validation_rules", []):
        if r.get("rule_category") not in USEFUL_RULE_CATEGORIES:
            continue
        formulas[r["assertion_id"]] = {
            "category": r["rule_category"],
            "expression": r.get("expression"),
            "severity": r.get("severity"),
            "concepts": [
                {
                    "concept_id": ci.get("concept_id"),
                    "label": _label_of(ci.get("concept_id", ""), label_index),
                    "variable": ci.get("variable_name"),
                    "role": ci.get("role"),
                }
                for ci in (r.get("concepts_involved") or [])
            ],
        }

    # ── the metric dictionary: confirmed, non-abstract concepts ──────────────
    metrics = []
    for c in concepts:
        m = c.get("db_mapping") or {}
        if m.get("status") != "confirmed" or c.get("abstract"):
            continue
        table = (m.get("table_name") or "").upper() or None
        if not table:
            continue

        # banded_union / wide_column carry column_name; narrow_keyvalue puts the
        # number in value_column and identifies the metric by the row code.
        column = (m.get("column_name") or "").upper() or None
        value_column = (m.get("value_column") or "").upper() or None

        # filter_column is the string "Code" for every mapping that has one, and
        # Phase 0 confirmed it is the physical CODE column holding a row code.
        # Normalise the name to upper case; keep the value verbatim but typed.
        row_code_column = (m.get("filter_column") or "").upper() or None
        row_code = m.get("filter_value")
        if isinstance(row_code, str):
            row_code = int(row_code.strip()) if row_code.strip().isdigit() else None
        elif not isinstance(row_code, int):
            row_code = None
        # A non-numeric filter_value ('BankCode', 'FCE') is the extractor's
        # internal identifier leaking through, not a value present in the CODE
        # column — every live CODE observed is numeric. Dropping it is the only
        # safe reading: shipping it would produce `WHERE CODE = BankCode`, which
        # is either a syntax error or a zero-row match.
        if row_code is None:
            row_code_column = None

        axis_ids = c.get("dimensional_context_required") or []
        metrics.append({
            "concept_id": c["concept_id"],
            "label": (c.get("label") or "").strip() or humanise(c["concept_id"]),
            "table": table,
            "column": column,
            "value_column": value_column,
            "mapping_type": m.get("mapping_type"),
            "row_code_column": row_code_column,
            "row_code": row_code,
            "unit_multiplier": m.get("unit_multiplier"),
            "measure": _MEASURE_KIND.get(c.get("data_type"), "other"),
            "period_type": c.get("period_type"),
            "balance_type": c.get("balance_type"),
            "is_core": bool((c.get("importance") or {}).get("is_core")),
            "score": (c.get("importance") or {}).get("score"),
            "axes": [axis_label_by_id.get(a) or humanise(a) for a in axis_ids],
            "reported_in": [
                role_names.get(u) or humanise(u.rstrip("/").split("/")[-1])
                for u in ((c.get("presentation") or {}).get("tables") or [])
            ],
            "formulas": [
                f["assertion_id"] for f in (c.get("formula_participation") or [])
                if f.get("assertion_id") in formulas
            ],
        })

    _mark_row_code_usability(metrics)

    # ── physical table -> business role(s) + concept labels ───────────────────
    table_profiles = {}
    for mt in metrics:
        prof = table_profiles.setdefault(mt["table"], {
            "table": mt["table"],
            "roles": [],
            "concept_labels": [],
            "axes": [],
            "unit_multipliers": [],
        })
        for r in mt["reported_in"]:
            if r and r not in prof["roles"]:
                prof["roles"].append(r)
        if mt["label"] not in prof["concept_labels"]:
            prof["concept_labels"].append(mt["label"])
        for a in mt["axes"]:
            if a not in prof["axes"]:
                prof["axes"].append(a)
        if mt["measure"] == "monetary" and mt["unit_multiplier"] is not None:
            prof["unit_multipliers"].append(mt["unit_multiplier"])

    # Collapse each table's monetary multipliers to the single dominant value,
    # and flag disagreement rather than silently picking one — a table whose
    # columns are in different units cannot get one blanket UNITS line.
    for prof in table_profiles.values():
        mults = prof.pop("unit_multipliers")
        distinct = sorted(set(mults))
        prof["unit_multiplier"] = distinct[-1] if len(distinct) == 1 else (
            max(set(mults), key=mults.count) if mults else None
        )
        prof["unit_multiplier_consistent"] = len(distinct) <= 1
        prof["monetary_concept_count"] = len(mults)

    # Every record carries its return_code. That is what lets a second return's
    # taxonomy be merged into this same artifact later without ambiguity about
    # which return a metric, axis or formula came from — retrofitting the tag
    # afterwards would mean re-deriving provenance that is free to record now.
    for m in metrics:
        m["return_code"] = return_code
    for a in axes:
        a["return_code"] = return_code
    for f in formulas.values():
        f["return_code"] = return_code
    for p in table_profiles.values():
        p["return_code"] = return_code

    return {
        "return_code": return_code,
        "return_codes": [return_code],
        "source": os.path.basename(taxonomy.get("return_metadata", {})
                                   .get("taxonomy_path", "")) or "taxonomy",
        "metrics": metrics,
        "axes": axes,
        "member_axes": {m: sorted(set(v)) for m, v in member_to_axes.items()},
        "formulas": formulas,
        "table_profiles": table_profiles,
    }


def merge(maps):
    """
    Combine per-return concept maps into one artifact.

    Physical tables are namespaced per return in this schema (CIMS_RAQ_Q_* vs
    CIMS_RAQ_M_*), so table_profiles cannot collide. Concepts CAN repeat across
    returns — the same in-rbi-rep concept is reported in several returns — so
    metrics are keyed by (return_code, concept_id, table) and a genuine
    cross-return duplicate is kept as two entries pointing at two tables, which
    is the truth. Axes and formulas dedupe on (return_code, id).
    """
    if len(maps) == 1:
        return maps[0]

    merged = {
        "return_code": None,
        "return_codes": [],
        "source": "merged",
        "metrics": [], "axes": [], "member_axes": {},
        "formulas": {}, "table_profiles": {},
    }
    seen_metrics, seen_axes = set(), set()
    for cm in maps:
        merged["return_codes"].append(cm["return_code"])
        for m in cm["metrics"]:
            key = (m["return_code"], m["concept_id"], m["table"])
            if key in seen_metrics:
                continue
            seen_metrics.add(key)
            merged["metrics"].append(m)
        for a in cm["axes"]:
            key = (a["return_code"], a["axis_id"])
            if key in seen_axes:
                continue
            seen_axes.add(key)
            merged["axes"].append(a)
        for member, axis_labels in cm["member_axes"].items():
            existing = merged["member_axes"].setdefault(member, [])
            for lbl in axis_labels:
                if lbl not in existing:
                    existing.append(lbl)
        # Assertion ids are taxonomy-scoped, so qualify them to stay unique.
        for fid, f in cm["formulas"].items():
            merged["formulas"][f"{f['return_code']}:{fid}"] = f
        for table, prof in cm["table_profiles"].items():
            if table in merged["table_profiles"]:
                print(f"[warn] table {table} is claimed by more than one return "
                      f"- keeping the first")
                continue
            merged["table_profiles"][table] = prof

    # Formula ids on each metric must be requalified to match the merged keys.
    for m in merged["metrics"]:
        m["formulas"] = [f"{m['return_code']}:{fid}" for fid in m.get("formulas") or []]

    return merged


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--taxonomy", action="append", default=None,
                    help="taxonomy export to distil; repeat to merge several returns")
    ap.add_argument("--out", default=OUT_PATH)
    args = ap.parse_args()

    paths = args.taxonomy or [DEFAULT_TAXONOMY]
    maps = []
    for path in paths:
        with open(path, encoding="utf-8") as f:
            maps.append(build(json.load(f)))
        print(f"  parsed {os.path.basename(path)} -> return "
              f"{maps[-1]['return_code']}, {len(maps[-1]['metrics'])} metrics")
    cm = merge(maps)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(cm, f, indent=1, ensure_ascii=False)

    src_mb = sum(os.path.getsize(p) for p in paths) / 1e6
    out_mb = os.path.getsize(args.out) / 1e6
    print(f"return_code(s)   : {', '.join(str(r) for r in cm['return_codes'])}")
    print(f"metrics          : {len(cm['metrics'])}")
    print(f"axes             : {len(cm['axes'])}")
    print(f"distinct members : {len(cm['member_axes'])}")
    print(f"formulas kept    : {len(cm['formulas'])}")
    print(f"table profiles   : {len(cm['table_profiles'])}")
    print(f"size             : {src_mb:.2f} MB taxonomy -> {out_mb:.2f} MB concept_map")
    print(f"[ok] wrote {args.out}")

    inconsistent = [t for t, p in cm["table_profiles"].items()
                    if not p["unit_multiplier_consistent"]]
    if inconsistent:
        print(f"[warn] mixed unit_multiplier within a table (no blanket UNITS line): "
              f"{inconsistent}")


if __name__ == "__main__":
    main()
