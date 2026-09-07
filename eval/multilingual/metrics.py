"""Scorers for the twelve evaluation metrics.

The one non-obvious piece is ``baseline_variance``. The pipeline is not
deterministic: any query that falls past the regex tiers calls an LLM
(backend/agent/__init__.py:1958) on a shared remote proxy, so the same English
question can route differently on two consecutive runs. This is not
speculative -- the repo's own archived artifacts show it: results_selftest.jsonl
and results_selftest_round2.jsonl are the same query set, and
'hey can u tell me abt returns pls' resolves to intent=unknown in one and
intent=return_list in the other.

Scoring a translated run against a single baseline capture would therefore
charge the model for the pipeline's own noise. So the baseline is captured N
times, cases that disagree with themselves are identified, and routing fidelity
is reported both raw and restricted to the stable subset. The stable-subset
number is the one that means anything.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from statistics import median

# Routing fields compared against baseline. These are protocol values the
# frontend branches on, so any change is a real behavioural difference.
ROUTING_FIELDS = ("intent", "result_type", "db_intent")


def percentile(values: list[float], pct: float) -> float | None:
    """Nearest-rank percentile. Small samples make interpolation misleading."""
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = max(1, min(len(ordered), int(round(pct / 100.0 * len(ordered) + 0.5))))
    return ordered[rank - 1]


def latency_summary(values: list[float]) -> dict:
    clean = [v for v in values if v is not None]
    return {
        "n": len(clean),
        "p50": round(median(clean), 1) if clean else None,
        "p95": round(percentile(clean, 95), 1) if clean else None,
        "max": round(max(clean), 1) if clean else None,
        "mean": round(sum(clean) / len(clean), 1) if clean else None,
    }


# --------------------------------------------------------------------------
# Baseline variance (Adjustment 1)
# --------------------------------------------------------------------------

@dataclass
class BaselineCase:
    """One case's baseline across N repeat runs."""

    case_id: str
    signatures: list[tuple] = field(default_factory=list)

    @property
    def stable(self) -> bool:
        """True when every repeat run produced the same routing signature."""
        return len(set(self.signatures)) <= 1

    @property
    def modal(self) -> tuple:
        """Most common signature -- the reference a translated run is scored
        against for unstable cases, where scoring is indicative only."""
        return Counter(self.signatures).most_common(1)[0][0] if self.signatures else ()


def routing_signature(response: dict) -> tuple:
    return tuple((response or {}).get(f, "") or "" for f in ROUTING_FIELDS)


def build_baseline(runs: list[dict[str, dict]]) -> dict[str, BaselineCase]:
    """``runs`` is one dict per repeat run, mapping case_id -> response."""
    cases: dict[str, BaselineCase] = {}
    for run in runs:
        for case_id, response in run.items():
            cases.setdefault(case_id, BaselineCase(case_id)).signatures.append(
                routing_signature(response)
            )
    return cases


def baseline_variance(cases: dict[str, BaselineCase]) -> dict:
    """The noise floor: how much the pipeline disagrees with itself."""
    total = len(cases)
    unstable = [c.case_id for c in cases.values() if not c.stable]
    return {
        "cases": total,
        "stable_cases": total - len(unstable),
        "unstable_cases": len(unstable),
        "unstable_case_ids": sorted(unstable),
        "self_agreement_pct": round(100.0 * (total - len(unstable)) / total, 1) if total else None,
    }


# --------------------------------------------------------------------------
# Routing fidelity (metrics 2 and 3)
# --------------------------------------------------------------------------

def routing_match(baseline: BaselineCase, response: dict) -> dict:
    """Per-field comparison of one localised response against its baseline."""
    got = routing_signature(response)
    expected = baseline.modal
    per_field = {
        field_name: (expected[i] if i < len(expected) else "") == got[i]
        for i, field_name in enumerate(ROUTING_FIELDS)
    }
    return {
        "expected": dict(zip(ROUTING_FIELDS, expected)),
        "actual": dict(zip(ROUTING_FIELDS, got)),
        "per_field": per_field,
        # Metric 2 is intent+result_type (what the user actually experiences);
        # metric 3 additionally requires db_intent to line up.
        "routing_ok": per_field["intent"] and per_field["result_type"],
        "all_fields_ok": all(per_field.values()),
        "baseline_stable": baseline.stable,
    }


# --------------------------------------------------------------------------
# Multi-turn selection correctness (metric 9)
# --------------------------------------------------------------------------

def resolved_selection(response_text: str, options: list[str]) -> str | None:
    """Which of the offered options the pipeline actually resolved to.

    Comparing routing signatures is not sufficient for metric 9. A staged
    status flow ends in ``get_status/error`` whenever the chosen report has no
    generated instances -- so a translated run that selected the WRONG report
    would produce an identical signature to the baseline and score as a pass.
    The selected name has to be compared directly.

    ``report_name`` is null on these responses, but the resolver names its
    choice in the prose ("Report 'RAQ(Monthly)' exists but no instances
    generated."), so the option list from turn 1 is used as the candidate set.
    Longest match wins, because option names overlap heavily -- 'RAQ(Monthly)'
    contains 'RAQ', and matching the short one first would be ambiguous.
    """
    if not response_text or not options:
        return None
    hits = [opt for opt in options if opt and opt in response_text]
    if not hits:
        return None
    return max(hits, key=len)


def selection_match(
    baseline_record: dict, actual_english_text: str
) -> dict | None:
    """Compare the resolved option of a translated run against the baseline.

    ``actual_english_text`` is the final ENGLISH response of the translated
    run, so this is an English-to-English comparison and is unaffected by
    outbound translation quality.
    """
    turns = baseline_record.get("_turns") or []
    if len(turns) < 2:
        return None
    options = turns[0].get("options") or []
    if not options:
        return None
    expected = resolved_selection(turns[-1].get("response_text") or "", options)
    actual = resolved_selection(actual_english_text or "", options)
    if expected is None:
        return None
    return {
        "expected_selection": expected,
        "actual_selection": actual,
        "selection_ok": expected == actual,
        "offered_options": options[:10],
    }


# --------------------------------------------------------------------------
# SQL consistency (metric 4)
# --------------------------------------------------------------------------

_SQL_WS = re.compile(r"\s+")
_SQL_COMMENT = re.compile(r"--[^\n]*|/\*.*?\*/", re.DOTALL)


def normalize_sql(sql: str | None) -> str:
    """Whitespace/case/comment-insensitive form for comparing two SQL strings.

    Deliberately not a parser. We are asking "did translating the question
    change the query the system decided to run", and a textual comparison after
    trivial normalisation answers that without pulling in a SQL dialect
    dependency for Oracle-flavoured text.
    """
    if not sql:
        return ""
    out = _SQL_COMMENT.sub(" ", sql)
    out = _SQL_WS.sub(" ", out)
    return out.strip().rstrip(";").upper()


def sql_match(baseline_sql: str | None, actual_sql: str | None) -> bool | None:
    """None when neither side produced SQL -- the case simply did not route to
    the SQL agent, which is not a SQL failure."""
    a, b = normalize_sql(baseline_sql), normalize_sql(actual_sql)
    if not a and not b:
        return None
    return a == b


# --------------------------------------------------------------------------
# Aggregation
# --------------------------------------------------------------------------

def _pct(numerator: int, denominator: int) -> float | None:
    return round(100.0 * numerator / denominator, 1) if denominator else None


def aggregate(records: list[dict]) -> dict:
    """Roll per-case records up into the report's headline numbers."""
    scored = [r for r in records if not r.get("skipped")]
    n = len(scored)

    stable = [r for r in scored if r.get("routing", {}).get("baseline_stable")]
    routing_ok = [r for r in stable if r["routing"]["routing_ok"]]
    allfields_ok = [r for r in stable if r["routing"]["all_fields_ok"]]
    raw_routing_ok = [r for r in scored if r.get("routing", {}).get("routing_ok")]

    preserved = [r for r in scored if r.get("preservation", {}).get("passed")]
    halluc = [r for r in scored if r.get("preservation", {}).get("hallucination_count")]

    sql_cases = [r for r in scored if r.get("sql_match") is not None]
    sql_ok = [r for r in sql_cases if r["sql_match"]]

    translate_failures = [r for r in scored if r.get("translation_error")]
    pipeline_errors = [r for r in scored if r.get("pipeline_error")]

    inbound = [r["inbound_ms"] for r in scored if r.get("inbound_ms") is not None]
    outbound = [r["outbound_ms"] for r in scored if r.get("outbound_ms") is not None]
    added = [
        r["inbound_ms"] + r["outbound_ms"]
        for r in scored
        if r.get("inbound_ms") is not None and r.get("outbound_ms") is not None
    ]
    pipeline_ms = [r["pipeline_ms"] for r in scored if r.get("pipeline_ms") is not None]

    judge_scores: dict[str, list[float]] = {}
    for r in scored:
        for key, value in (r.get("judge") or {}).items():
            if isinstance(value, (int, float)):
                judge_scores.setdefault(key, []).append(float(value))

    return {
        "cases": n,
        "stable_baseline_cases": len(stable),
        # The headline. Restricted to cases where the pipeline agrees with
        # itself, so it measures translation damage rather than pipeline noise.
        "routing_fidelity_pct": _pct(len(routing_ok), len(stable)),
        "routing_fidelity_raw_pct": _pct(len(raw_routing_ok), n),
        "all_routing_fields_pct": _pct(len(allfields_ok), len(stable)),
        "entity_preservation_pct": _pct(len(preserved), n),
        "hallucination_free_pct": _pct(n - len(halluc), n),
        "sql_consistency_pct": _pct(len(sql_ok), len(sql_cases)),
        "sql_cases": len(sql_cases),
        "translation_failures": len(translate_failures),
        "pipeline_errors": len(pipeline_errors),
        "latency": {
            "inbound_ms": latency_summary(inbound),
            "outbound_ms": latency_summary(outbound),
            "added_ms": latency_summary(added),
            "pipeline_ms": latency_summary(pipeline_ms),
        },
        "judge": {
            key: round(sum(values) / len(values), 2)
            for key, values in sorted(judge_scores.items())
            if values
        },
    }


def aggregate_by(records: list[dict], key: str) -> dict[str, dict]:
    buckets: dict[str, list[dict]] = {}
    for record in records:
        buckets.setdefault(record.get(key, "?"), []).append(record)
    return {name: aggregate(rows) for name, rows in sorted(buckets.items())}


# --------------------------------------------------------------------------
# Verdict
# --------------------------------------------------------------------------

PASS_THRESHOLDS = {"routing": 98.0, "preservation": 100.0, "added_p95_ms": 5000.0}
CONDITIONAL_THRESHOLDS = {"routing": 95.0, "preservation": 99.0, "added_p95_ms": 8000.0}


def verdict(summary: dict) -> tuple[str, list[str]]:
    """PASS / CONDITIONAL / FAIL plus the reasons behind it."""
    routing = summary.get("routing_fidelity_pct")
    preservation = summary.get("entity_preservation_pct")
    added_p95 = (summary.get("latency", {}).get("added_ms") or {}).get("p95")
    reasons: list[str] = []

    if routing is None or preservation is None:
        return "FAIL", ["insufficient data to score"]

    def check(name, value, pass_v, cond_v, higher_better=True):
        if higher_better:
            if value >= pass_v:
                return "PASS"
            return "CONDITIONAL" if value >= cond_v else "FAIL"
        if value <= pass_v:
            return "PASS"
        return "CONDITIONAL" if value <= cond_v else "FAIL"

    grades = [
        ("routing fidelity", routing, check("routing", routing, 98.0, 95.0)),
        ("entity preservation", preservation, check("pres", preservation, 100.0, 99.0)),
    ]
    if added_p95 is not None:
        grades.append((
            "p95 added latency",
            added_p95,
            check("lat", added_p95, 5000.0, 8000.0, higher_better=False),
        ))

    order = {"PASS": 0, "CONDITIONAL": 1, "FAIL": 2}
    worst = max((g[2] for g in grades), key=lambda g: order[g])
    for name, value, grade in grades:
        if grade != "PASS":
            reasons.append(f"{name}={value} -> {grade}")
    if not reasons:
        reasons.append("all gates met")
    return worst, reasons
