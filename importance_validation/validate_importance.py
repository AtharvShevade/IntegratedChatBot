#!/usr/bin/env python3
"""Standalone validator for XBRL concept regulatory-importance scoring.

WHAT THIS IS
------------
A validation and inspection tool. It reads one return's taxonomy folder,
extracts every declared concept, computes the five importance factors, and
writes a JSON file detailed enough to judge whether the ranking is sensible.

NOTHING AT RUNTIME DEPENDS ON THIS FILE. Importance is computed once during
taxonomy-JSON generation (Stage A) and baked into the per-return JSON; the
comparison analysis reads those fields and never re-derives them. This script
exists to check that what gets baked in is correct.

It does NOT carry its own copy of the algorithm. The maths lives in the JSON
generator's shared module — app/core/importance/scorer.py — and is imported
here, so this tool always reports exactly what the pipeline produces. A
re-implementation could drift and silently validate the wrong thing.

It imports nothing from the chatbot.

Use --cross-check to confirm the shared scorer still agrees with the chatbot's
backend/tools/xbrl_importance.py, when that module is importable.

THE FIVE FACTORS (weights sum to 100)
-------------------------------------
  Mandate   25  concept is named by a circular in the reference linkbase
  Rules     25  validation-assertion density, log-scaled
  Section   20  how central the concept's business section is to the return
  Blocking  15  has error-severity validation (not warning-only)
  Recency   15  touched by a recent regulatory amendment

  Tier: >=70 Critical, >=45 High, >=20 Medium, else Low

USAGE
-----
  # by explicit taxonomy folder
  python validate_importance.py --taxonomy "D:/Repo(new)/DataBase/2036/Taxonomy"

  # by form id, resolved as <repo-root>/DataBase/<form-id>/Taxonomy
  python validate_importance.py --repo-root "D:/Repo(new)" --form-id 2036

  # inspect on the console as well as writing JSON
  python validate_importance.py --form-id 2036 --repo-root "D:/Repo(new)" \
      --top 25 --out out/2036.json --csv out/2036.csv

  # score several returns in one run, one JSON each plus a comparison summary
  python validate_importance.py --repo-root "D:/Repo(new)" \
      --form-id 2036 --form-id 2037 --form-id 2029 --out-dir out/

  # confirm this file's maths matches the chatbot module
  python validate_importance.py --form-id 2036 --repo-root "D:/Repo(new)" --cross-check

EXIT CODE
---------
  0  scored at least one concept
  1  taxonomy unusable (no [NNNN] sections, or no concepts found)
  2  bad arguments / path not found
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter

# ─────────────────────────────────────────────────────────────────────────────
# Scoring algorithm — imported, never duplicated
# ─────────────────────────────────────────────────────────────────────────────
# The maths lives in ONE place: the JSON generator's shared scorer module,
# which Stage A uses during taxonomy-JSON creation. This validator imports the
# very same code, so what it reports is exactly what gets baked into the JSON —
# a re-implementation here could drift and silently validate the wrong thing.
#
# Point --scorer-path (or $JSON_EXTRACTOR_PATH) at the generator checkout if it
# does not live at the default location.
_SCORER_CANDIDATES = (
    os.environ.get("JSON_EXTRACTOR_PATH"),
    r"D:\TrendAnalysis_JSON_Extractor",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "TrendAnalysis_JSON_Extractor"),
)


def _load_scorer(explicit: str | None = None):
    for root in ((explicit,) if explicit else ()) + _SCORER_CANDIDATES:
        if not root:
            continue
        mod = os.path.join(root, "app", "core", "importance", "scorer.py")
        if not os.path.isfile(mod):
            continue
        if root not in sys.path:
            sys.path.insert(0, root)
        try:
            from app.core.importance import scorer as _s
            return _s, root
        except Exception:
            continue
    raise SystemExit(
        "Cannot find the shared scorer module "
        "(app/core/importance/scorer.py).\n"
        "Pass --scorer-path <TrendAnalysis_JSON_Extractor> or set "
        "$JSON_EXTRACTOR_PATH."
    )


_scorer, SCORER_ROOT = _load_scorer()

TaxonomyImportance = _scorer.TaxonomyImportance
SCORER_VERSION = _scorer.SCORER_VERSION
TIER_ORDER = _scorer.TIER_ORDER
W_MANDATE, W_RULES = _scorer.W_MANDATE, _scorer.W_RULES
W_SECTION, W_BLOCKING, W_RECENCY = (
    _scorer.W_SECTION, _scorer.W_BLOCKING, _scorer.W_RECENCY
)
humanise = _scorer.humanise
_tier_for = _scorer._tier_for
_local_name = _scorer._local_name
build_regulatory_importance = _scorer.build_regulatory_importance


# ─────────────────────────────────────────────────────────────────────────────
# Reporting
# ─────────────────────────────────────────────────────────────────────────────
def build_report(tax: TaxonomyImportance, rows: list[dict], form_id: str | None) -> dict:
    tiers = Counter(r["importance_tier"] for r in rows)
    scored = [r for r in rows if r["has_evidence"]]
    total = len(rows)

    # Per-section rollup — the quickest way to see whether section_core landed
    # sensibly, which is the factor most likely to be wrong.
    per_section: dict[str, dict] = {}
    for r in rows:
        ev = r["evidence"]
        key = ev["section_code"] or "UNCLASSIFIED"
        s = per_section.setdefault(key, {
            "section_code": ev["section_code"],
            "section_title": ev["section_title"],
            "section_ordinal": ev["section_ordinal"],
            "section_core": ev["section_core"],
            "concepts": 0, "mandated": 0, "with_blocking": 0,
            "score_sum": 0.0, "max_score": 0.0, "tiers": Counter(),
        })
        s["concepts"] += 1
        s["score_sum"] += r["importance_score"]
        s["max_score"] = max(s["max_score"], r["importance_score"])
        s["tiers"][r["importance_tier"]] += 1
        if ev["circulars"]:
            s["mandated"] += 1
        if ev["blocking_rules"] > 0:
            s["with_blocking"] += 1

    sections = []
    for s in per_section.values():
        sections.append({
            **{k: v for k, v in s.items() if k not in ("score_sum", "tiers")},
            "avg_score": round(s["score_sum"] / s["concepts"], 1) if s["concepts"] else 0,
            "tier_counts": dict(s["tiers"]),
        })
    sections.sort(key=lambda s: (-s["avg_score"], s["section_ordinal"]))

    return {
        "form_id": form_id,
        "taxonomy_roots": list(tax.roots),
        "generated_by": "importance_validation/validate_importance.py",
        "weights": {
            "mandate": W_MANDATE, "rules": W_RULES, "section": W_SECTION,
            "blocking": W_BLOCKING, "recency": W_RECENCY,
            "_total": W_MANDATE + W_RULES + W_SECTION + W_BLOCKING + W_RECENCY,
        },
        "tier_cutoffs": {"Critical": 70.0, "High": 45.0, "Medium": 20.0, "Low": 0.0},
        "parse_stats": tax.stats,
        "summary": {
            "concepts_total": total,
            # The number that decides whether a blended ranking can be the
            # default or has to stay an option.
            "concepts_with_evidence": len(scored),
            "coverage_pct": round(100.0 * len(scored) / total, 1) if total else 0.0,
            "concepts_no_evidence": total - len(scored),
            "tier_counts": {t: tiers.get(t, 0) for t in TIER_ORDER},
            "tier_pct": {
                t: (round(100.0 * tiers.get(t, 0) / total, 1) if total else 0.0)
                for t in TIER_ORDER
            },
            "score_min": min((r["importance_score"] for r in rows), default=0.0),
            "score_max": max((r["importance_score"] for r in rows), default=0.0),
            "score_mean": (
                round(sum(r["importance_score"] for r in rows) / total, 1)
                if total else 0.0
            ),
            "factor_contribution": {
                f: round(sum(r["factors"][f] for r in rows) / total, 2) if total else 0.0
                for f in ("mandate", "rules", "section", "blocking", "recency")
            },
        },
        "sections": sections,
        "concepts": rows,
    }


def print_console(report: dict, top: int, tier_filter: str | None) -> None:
    s = report["summary"]
    st = report["parse_stats"]
    print()
    print("=" * 92)
    print(f"  TAXONOMY IMPORTANCE — form_id={report['form_id'] or '(path)'}")
    print("=" * 92)
    for r in report["taxonomy_roots"]:
        print(f"  root: {r}")
    print(f"  files: {st.get('xsd_files', 0)} .xsd, {st.get('xml_files', 0)} .xml"
          f"   sections: {st.get('sections', 0)}")
    print()
    print(f"  concepts scored        {s['concepts_total']:>7,}")
    print(f"  with taxonomy evidence {s['concepts_with_evidence']:>7,}"
          f"   ({s['coverage_pct']}%  <- COVERAGE)")
    print(f"  no evidence (fallback) {s['concepts_no_evidence']:>7,}")
    print(f"  score  min/mean/max    {s['score_min']:>7} / {s['score_mean']} / {s['score_max']}")
    print()
    print("  tier distribution")
    for t in TIER_ORDER:
        n, pct = s["tier_counts"][t], s["tier_pct"][t]
        bar = "#" * int(pct / 2)
        print(f"    {t:<9} {n:>6,}  {pct:>5}%  {bar}")
    print()
    print("  mean factor contribution (of its max)")
    for f, v in s["factor_contribution"].items():
        mx = report["weights"][f]
        print(f"    {f:<9} {v:>6} / {mx:<3} {'#' * int(v / mx * 30) if mx else ''}")

    if report["sections"]:
        print()
        print("  sections by mean importance")
        print(f"    {'code':<7} {'core':>5} {'#':>5} {'mand':>5} {'blk':>5} {'avg':>6} {'max':>6}  title")
        for sec in report["sections"][:15]:
            print(f"    {(sec['section_code'] or '—'):<7} {sec['section_core']:>5} "
                  f"{sec['concepts']:>5} {sec['mandated']:>5} {sec['with_blocking']:>5} "
                  f"{sec['avg_score']:>6} {sec['max_score']:>6}  {sec['section_title'][:44]}")

    rows = report["concepts"]
    if tier_filter:
        rows = [r for r in rows if r["importance_tier"].lower() == tier_filter.lower()]
    if top:
        print()
        label = f"top {top}" + (f" in tier {tier_filter}" if tier_filter else "")
        print(f"  {label}")
        print(f"    {'#':>4} {'score':>6} {'tier':<9} {'mnd':>4} {'rul':>5} {'sec':>5} "
              f"{'blk':>4} {'rec':>4}  {'sect':<6} concept")
        print("    " + "-" * 86)
        for i, r in enumerate(rows[:top], 1):
            f = r["factors"]
            print(f"    {i:>4} {r['importance_score']:>6} {r['importance_tier']:<9} "
                  f"{f['mandate']:>4.0f} {f['rules']:>5.1f} {f['section']:>5.1f} "
                  f"{f['blocking']:>4.0f} {f['recency']:>4.1f}  "
                  f"{(r['evidence']['section_code'] or '—'):<6} {r['label'][:34]}")
        if not rows:
            print("    (none)")
    print()


def write_csv(path: str, rows: list[dict]) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow([
            "concept", "label", "importance_score", "importance_tier",
            "f_mandate", "f_rules", "f_section", "f_blocking", "f_recency",
            "section_code", "section_title", "section_core",
            "circulars", "blocking_rules", "advisory_rules", "last_amended",
            "has_evidence", "drivers",
        ])
        for r in rows:
            f, e = r["factors"], r["evidence"]
            w.writerow([
                r["concept"], r["label"], r["importance_score"], r["importance_tier"],
                f["mandate"], f["rules"], f["section"], f["blocking"], f["recency"],
                e["section_code"], e["section_title"], e["section_core"],
                "; ".join(e["circulars"]), e["blocking_rules"], e["advisory_rules"],
                e["last_amended"] if e["last_amended"] is not None else "",
                "yes" if r["has_evidence"] else "no",
                " | ".join(r["drivers"]),
            ])


def cross_check(tax: TaxonomyImportance, rows: list[dict], sample: int = 400) -> None:
    """Confirm this file's maths matches backend/tools/xbrl_importance.py.

    Read-only: imports the module and calls it. Nothing in backend/ is written.
    Skipped with a message when the module cannot be imported standalone.
    """
    print("  cross-check against backend.tools.xbrl_importance …")
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from backend.tools.xbrl_importance import ImportanceIndex  # noqa: PLC0415
    except Exception as exc:
        print(f"    SKIPPED — cannot import module ({type(exc).__name__}: {exc})")
        return

    ref = ImportanceIndex(tax.roots)
    checked = mismatch = 0
    for r in rows[:sample]:
        try:
            theirs = ref.score_concept(r["concept"])
        except Exception as exc:
            print(f"    ERROR scoring {r['concept']}: {exc}")
            return
        checked += 1
        if (abs(theirs["score"] - r["importance_score"]) > 0.05
                or theirs["tier"] != r["importance_tier"]):
            mismatch += 1
            if mismatch <= 10:
                print(f"    MISMATCH {r['concept']}: "
                      f"standalone={r['importance_score']}/{r['importance_tier']} "
                      f"module={theirs['score']}/{theirs['tier']}")
    verdict = "IDENTICAL" if mismatch == 0 else f"{mismatch} DIFFER"
    print(f"    checked {checked} concepts -> {verdict}")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────
# Where DataBase/<form_id>/Taxonomy lives. An env var wins so this stays
# portable; the literal fallbacks are only a convenience for the machines this
# was validated on, and are simply skipped when absent.
_KNOWN_REPO_ROOTS = (r"D:\Repo(new)", r"D:\Repo", r"C:\Repo(new)", r"C:\Repo")


def _repo_root_from_env_file() -> str | None:
    """BASE_REPO_PATH as set in the project's .env.

    This is the authority: backend/config.py reads the same variable, so
    honouring it keeps the validator pointed at whatever repo the app is
    actually serving. Parsed by hand rather than importing python-dotenv so
    the script stays dependency-free and standalone.

    Note config.py carries a hardcoded fallback (D:\\Repo(new)) for when the
    variable is unset — which is a genuinely different repo, so a run that
    misses .env reads a different taxonomy set entirely and gives different
    scores without saying so.
    """
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for name in (".env", ".env.local"):
        path = os.path.join(here, name)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, val = line.partition("=")
                    if key.strip() != "BASE_REPO_PATH":
                        continue
                    val = val.strip().strip('"').strip("'")
                    if val and os.path.isdir(os.path.join(val, "DataBase")):
                        return val
        except OSError:
            continue
    return None


def _default_repo_root() -> str | None:
    # Explicit env var wins, then the project's .env, then the known roots.
    for var in ("REPO_ROOT", "IMPORTANCE_REPO_ROOT", "BASE_REPO_PATH"):
        v = os.environ.get(var)
        if v and os.path.isdir(os.path.join(v, "DataBase")):
            return v
    from_env_file = _repo_root_from_env_file()
    if from_env_file:
        return from_env_file
    for r in _KNOWN_REPO_ROOTS:
        if os.path.isdir(os.path.join(r, "DataBase")):
            return r
    return None


def resolve_roots(args: argparse.Namespace, form_id: str | None) -> tuple[str, ...]:
    if args.taxonomy:
        return tuple(t for t in args.taxonomy if os.path.isdir(t))
    if form_id and args.repo_root:
        p = os.path.join(args.repo_root, "DataBase", str(form_id), "Taxonomy")
        return (p,) if os.path.isdir(p) else ()
    return ()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Validate XBRL concept regulatory-importance scoring.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("USAGE")[1] if "USAGE" in __doc__ else None,
    )
    src = ap.add_argument_group("taxonomy source")
    src.add_argument("--taxonomy", action="append", metavar="DIR",
                     help="Taxonomy folder. Repeatable. Overrides --form-id.")
    src.add_argument("--form-id", action="append", metavar="ID",
                     help="Form id, resolved as <repo-root>/DataBase/<ID>/Taxonomy. "
                          "Repeatable.")
    src.add_argument("--repo-root", metavar="DIR", default=_default_repo_root(),
                     help="Repo root holding DataBase/. Defaults to $REPO_ROOT, "
                          "$IMPORTANCE_REPO_ROOT, or the first of the known "
                          "roots that exists.")

    out = ap.add_argument_group("output")
    out.add_argument("--out", metavar="FILE", help="Write JSON here (single run).")
    out.add_argument("--out-dir", metavar="DIR",
                     help="Write <form_id>.json per run here (multi-run).")
    out.add_argument("--csv", metavar="FILE", help="Also write a flat CSV.")
    out.add_argument("--top", type=int, default=25,
                     help="Rows to print to console. 0 to suppress. Default 25.")
    out.add_argument("--tier", choices=[t.lower() for t in TIER_ORDER],
                     help="Restrict the printed list to one tier.")
    out.add_argument("--include-abstract", action="store_true",
                     help="Score abstract (presentation-only) elements too.")
    out.add_argument("--compact", action="store_true",
                     help="Omit per-concept schema/driver detail from the JSON.")
    out.add_argument("--cross-check", action="store_true",
                     help="Verify against backend.tools.xbrl_importance (read-only).")
    out.add_argument("-v", "--verbose", action="store_true")

    args = ap.parse_args(argv)

    if not args.taxonomy and not args.form_id:
        ap.error("give --taxonomy DIR or --form-id ID (with --repo-root)")
    if args.form_id and not args.taxonomy and not args.repo_root:
        ap.error("--form-id needs --repo-root")

    targets: list[str | None] = list(args.form_id) if args.form_id else [None]
    if args.taxonomy:
        targets = [args.form_id[0] if args.form_id else None]

    if len(targets) > 1 and args.out and not args.out_dir:
        ap.error("multiple --form-id needs --out-dir, not --out")

    overall: list[dict] = []
    exit_code = 1

    for form_id in targets:
        roots = resolve_roots(args, form_id)
        if not roots:
            print(f"  ! no taxonomy folder for "
                  f"{form_id or args.taxonomy}", file=sys.stderr)
            continue

        tax = TaxonomyImportance(roots, verbose=args.verbose)
        if not tax.is_usable:
            print(f"  ! taxonomy at {roots[0]} has no [NNNN] role sections — "
                  f"cannot rank", file=sys.stderr)
            continue

        rows = tax.score_all(include_abstract=args.include_abstract)
        if not rows:
            print(f"  ! no concepts found in {roots[0]}", file=sys.stderr)
            continue

        report = build_report(tax, rows, form_id)
        exit_code = 0

        if args.compact:
            for r in report["concepts"]:
                r.pop("schema", None)
                r.pop("factor_max", None)

        if args.top:
            print_console(report, args.top, args.tier)
        if args.cross_check:
            cross_check(tax, rows)

        dest = None
        if args.out_dir:
            os.makedirs(args.out_dir, exist_ok=True)
            dest = os.path.join(args.out_dir, f"{form_id or 'taxonomy'}.json")
        elif args.out:
            dest = args.out
        if dest:
            os.makedirs(os.path.dirname(os.path.abspath(dest)) or ".", exist_ok=True)
            with open(dest, "w", encoding="utf-8") as fh:
                json.dump(report, fh, indent=2, ensure_ascii=False)
            print(f"  -> {dest}  ({len(rows):,} concepts)")

        if args.csv and len(targets) == 1:
            write_csv(args.csv, rows)
            print(f"  -> {args.csv}")

        overall.append({
            "form_id": form_id,
            "concepts": report["summary"]["concepts_total"],
            "coverage_pct": report["summary"]["coverage_pct"],
            **report["summary"]["tier_counts"],
        })

    if len(overall) > 1:
        print()
        print("  " + "=" * 74)
        print("  COVERAGE ACROSS RETURNS")
        print(f"    {'form':<8} {'concepts':>9} {'cover%':>7} "
              f"{'Crit':>6} {'High':>6} {'Med':>6} {'Low':>6}")
        for o in overall:
            print(f"    {str(o['form_id']):<8} {o['concepts']:>9,} "
                  f"{o['coverage_pct']:>7} {o['Critical']:>6,} {o['High']:>6,} "
                  f"{o['Medium']:>6,} {o['Low']:>6,}")
        print()

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
