"""Scoring rules, and the reasons they are drawn where they are.

Three deliberate choices:

1. **Only `grade == "strict"` counts toward accuracy.** Ambiguous and
   taxonomy-gap cases are recorded in full and reported for manual review. A
   model cannot be marked wrong against an answer that does not exist.

2. **Date/time entities are graded on PRESENCE, not text.** The production
   prompt says "preserve exact date text as written", but "31st march 2025"
   vs "31 March 2025" is a normalisation difference the downstream parser
   absorbs, not a model error. Grading the string would measure formatting.

3. **Hallucination is defined narrowly and mechanically**: a report_name the
   model returned whose letters do not appear in the query. That is an entity
   the model invented, which is the failure that actually hurts here -- it
   sends the pipeline to look up a report the user never named.
"""
from __future__ import annotations

import re

VALID_INTENTS = {
    "get_status", "generate_instance", "schedule_report", "compare_reports",
    "query_database", "db_my_profile", "db_my_department", "db_my_role",
    "db_my_permissions", "db_list_users", "db_list_departments", "db_list_roles",
    "db_user_info", "db_department_info", "unknown",
}
SCHEMA_KEYS = ("intent", "report_name", "reporting_date", "schedule_date",
               "schedule_time", "target_user", "target_department", "target_role",
               "query_type")
DATE_FIELDS = ("reporting_date", "schedule_date", "schedule_time")


def _norm(value) -> str:
    """Fold case and drop separators: CIMS_ROR, cims ror and cims-ror are one name."""
    return re.sub(r"[^a-z0-9]", "", str(value).lower()) if value is not None else ""


def score_case(case: dict, result: dict) -> dict:
    """Score one model's answer to one query. Returns flags, never raises."""
    out = {
        "id": case["id"], "category": case["category"], "grade": case["grade"],
        "query": case["query"], "latency_ms": round(result["latency_ms"], 1),
        "failed": not result["ok"], "error": result.get("error"),
        "strict_json_ok": result.get("strict_json_ok", False),
        "intent": None, "intent_correct": None, "valid_intent": None,
        "schema_ok": None, "report_name": None, "report_name_correct": None,
        "dates_correct": None, "hallucinated_entity": None,
    }
    if not result["ok"]:
        return out

    got = result["parsed"]
    intent = got.get("intent")
    out["intent"] = intent
    out["valid_intent"] = intent in VALID_INTENTS
    out["schema_ok"] = all(k in got for k in SCHEMA_KEYS)
    out["report_name"] = got.get("report_name")

    # An entity is invented if its letters are nowhere in what the user said.
    name = got.get("report_name")
    if name:
        out["hallucinated_entity"] = _norm(name) not in _norm(case["query"])
    else:
        out["hallucinated_entity"] = False

    if case["grade"] != "strict":
        return out                                   # recorded, not scored

    out["intent_correct"] = intent == case["intent"]

    if "report_name" in case:                        # absent => not graded
        out["report_name_correct"] = _norm(name) == _norm(case["report_name"])

    graded_dates = [f for f in DATE_FIELDS if f in case]
    if graded_dates:
        out["dates_correct"] = all(
            bool(got.get(f)) == (case[f] == "*") for f in graded_dates
        )
    return out


def _pct(hits: int, total: int) -> float | None:
    return round(100.0 * hits / total, 1) if total else None


def aggregate(rows: list[dict]) -> dict:
    """Roll scored rows into the headline numbers."""
    strict = [r for r in rows if r["grade"] == "strict"]
    ok = [r for r in rows if not r["failed"]]
    lat = sorted(r["latency_ms"] for r in ok)

    def p(pct: float):
        if not lat:
            return None
        rank = max(1, min(len(lat), int(round(pct / 100.0 * len(lat) + 0.5))))
        return round(lat[rank - 1], 1)

    intent_graded = [r for r in strict if r["intent_correct"] is not None]
    name_graded = [r for r in strict if r["report_name_correct"] is not None]
    date_graded = [r for r in strict if r["dates_correct"] is not None]
    return {
        "cases": len(rows),
        "strict_cases": len(strict),
        "failures": sum(1 for r in rows if r["failed"]),
        "failure_rate_pct": _pct(sum(1 for r in rows if r["failed"]), len(rows)),
        "intent_accuracy_pct": _pct(sum(1 for r in intent_graded if r["intent_correct"]),
                                    len(intent_graded)),
        "intent_correct": sum(1 for r in intent_graded if r["intent_correct"]),
        "intent_graded": len(intent_graded),
        "entity_accuracy_pct": _pct(sum(1 for r in name_graded if r["report_name_correct"]),
                                    len(name_graded)),
        "entity_graded": len(name_graded),
        "date_accuracy_pct": _pct(sum(1 for r in date_graded if r["dates_correct"]),
                                  len(date_graded)),
        "invalid_intent_pct": _pct(sum(1 for r in ok if not r["valid_intent"]), len(ok)),
        "schema_ok_pct": _pct(sum(1 for r in ok if r["schema_ok"]), len(ok)),
        # Production-compatible: parsed by a bare json.loads, exactly as
        # llm_service.py does. A model can answer perfectly and still score 0
        # here by fencing its JSON -- that is a real deployment blocker, and
        # hiding it behind a lenient parser would be dishonest about the cost
        # of switching.
        "prod_parse_ok_pct": _pct(sum(1 for r in rows if r["strict_json_ok"]), len(rows)),
        "prod_usable": sum(1 for r in rows if r["strict_json_ok"]),
        "hallucination_pct": _pct(sum(1 for r in ok if r["hallucinated_entity"]), len(ok)),
        "median_ms": round(lat[len(lat) // 2], 1) if lat else None,
        "mean_ms": round(sum(lat) / len(lat), 1) if lat else None,
        "p95_ms": p(95),
        "min_ms": round(lat[0], 1) if lat else None,
        "max_ms": round(lat[-1], 1) if lat else None,
    }


def by_category(rows: list[dict]) -> dict[str, dict]:
    cats: dict[str, list[dict]] = {}
    for row in rows:
        cats.setdefault(row["category"], []).append(row)
    return {c: aggregate(rs) for c, rs in sorted(cats.items())}
