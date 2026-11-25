"""Bridge between the chatbot's formula-error explanation and the error-improvement engine.

The chatbot calls `explain_batch(...)` with the rules it is about to explain (it pages through them three at a time). For each
rule the engine can explain, this returns the chatbot's usual per-rule dict with the new card in `explanation_sections` (and the
same content as plain text in `explanation`). Rules the engine cannot explain are simply absent from the result, so the caller
explains those the old way. Nothing here raises: any problem is logged and means "use the old explanation".

Switches (environment):
    ERROR_IMPROVEMENT=0             turn the whole thing off (default: on)
    ERROR_IMPROVEMENT_REPO=<path>   repo root to read (default: the chatbot's current repo root: 5.5, or the 6.0 tenant root)
    ERROR_IMPROVEMENT_GATE=0        show every card the engine builds, even when it could not name a cell (default: 1 = a rule gets the
                                    full card only when the analysis names a cell to correct; otherwise the existing explanation)
    ERROR_IMPROVEMENT_FINDINGS=0    do not add the "What we found in your workbook" note to an existing explanation (default: on)
    ERROR_IMPROVEMENT_MIN_COVERAGE  share of a rule's values that must be placed in the workbook for a full card (default 0.5)
The engine only reads files; it never writes into the repo (its template-conversion cache is kept inside its own folder).
"""
from __future__ import annotations

import logging
import os
import threading
import time
from collections import OrderedDict

logger = logging.getLogger(__name__)

_CACHE: "OrderedDict[tuple, tuple]" = OrderedDict()       # key -> (stored at, result, read the database)
_LOCK = threading.Lock()
_MAX_ENTRIES = 3


def _db_ttl() -> float:
    """Seconds a card that was built from database reads may be reused (0 = never). An Excel card's inputs are files that
    do not change, so it is kept; a database card must show a corrected table on the next view, so it is kept only briefly
    (long enough that repeated clicks on one error file do not read the tables again)."""
    try:
        return max(0.0, float(os.getenv("EI_DB_CARD_CACHE_SECONDS", "30")))
    except ValueError:
        return 30.0


def _read_database(cards: dict) -> bool:
    return any(isinstance(c, dict) and (c.get("db") or c.get("where_to_look")) for c in (cards or {}).values())


def enabled() -> bool:
    return os.getenv("ERROR_IMPROVEMENT", "1").strip().lower() not in ("0", "false", "no", "off")


def gate_enabled() -> bool:
    return os.environ.get("ERROR_IMPROVEMENT_GATE", "1").strip().lower() not in ("0", "false", "no", "off")


def findings_enabled() -> bool:
    return enabled() and os.environ.get("ERROR_IMPROVEMENT_FINDINGS", "1").strip().lower() not in ("0", "false", "no", "off")


FINDINGS_HEADING = "What we found in your workbook"
DB_FINDINGS_HEADING = "Where to look"


def _repo_root() -> str | None:
    override = os.getenv("ERROR_IMPROVEMENT_REPO", "").strip()
    if override:
        return override
    try:
        from backend import config
        return config._active_root() or None       # 5.5 root, or the 6.0 tenant root: both hold DataBase/<id> and Instance/<id>
    except Exception:                              # noqa: BLE001
        return None


def _result_for(error_file: str, repo: str | None, numbering: dict | None) -> dict | None:
    key = (os.path.abspath(error_file), os.path.getmtime(error_file), repo)
    with _LOCK:
        hit = _CACHE.get(key)
        if hit is not None and hit[2] and time.monotonic() - hit[0] > _db_ttl():
            _CACHE.pop(key, None)                  # built from the tables: read them again so a corrected table shows
            hit = None
        if hit is not None:
            _CACHE.move_to_end(key)
            return hit[1]
    from . import explain as ex                    # imported late: the engine is only loaded when it is used
    result = ex.explain_file(error_file, repo, numbering=numbering)
    slim = {"cards": result.get("cards") or {}, "info": result.get("info") or {}}
    with _LOCK:
        _CACHE[key] = (time.monotonic(), slim, _read_database(slim["cards"]))
        while len(_CACHE) > _MAX_ENTRIES:
            _CACHE.popitem(last=False)
    return slim


def explain_batch(rules: list[dict], error_file: str, form_id: str = "", numbering: dict | None = None,
                  lang: str = "en") -> dict[str, dict]:
    """{rule_name: explained rule dict} for the rules the engine can explain; {} when it is off or has nothing to say."""
    if not enabled() or not rules or not error_file or not os.path.isfile(error_file):
        return {}
    if (lang or "en").strip().lower() not in ("", "en", "english"):
        return {}                                   # the cards are English; other languages keep the existing translated path
    try:
        repo = _repo_root()
        result = _result_for(error_file, repo, numbering)
        cards = (result or {}).get("cards") or {}
        if not cards:
            logger.info("[error_improvement] no cards for %s (format: %s; notes: %s)", os.path.basename(error_file),
                        result["info"].get("format", ""), "; ".join(result["info"].get("notes", [])) or "none")
            return {}
        from . import rule_cards as rc
        out: dict[str, dict] = {}
        for rule in rules:
            name = rule.get("rule_name", "")
            card = cards.get(name)
            if not card:
                continue
            if gate_enabled() and not card.get("full", True):
                logger.info("[error_improvement] rule %s keeps the existing explanation: %s", name, card.get("why_not_full", ""))
                continue
            item = dict(rule)
            sections, text = rc.card_to_sections(card), rc.card_to_text(card)
            if rule.get("severity") == "warning":              # a yellow/orange rule is a warning, not an error to be corrected
                for s in sections:
                    if s.get("kind") == "issue_card":
                        s["badge"], s["tone"] = "Warning", "warning"
                text = text.replace("[Failed]", "[Warning]", 1)
            item["explanation_sections"] = sections
            item["explanation"] = text
            item["_error_category"] = "formula_error"
            item["_improved"] = True
            item["_evidence"] = card.get("evidence_key", "")
            out[name] = item
        if out:
            logger.info("[error_improvement] explained %d/%d rule(s) of %s (basis: %s, %ss)", len(out), len(rules),
                        os.path.basename(error_file), result["info"].get("basis", ""), result["info"].get("seconds", ""))
        return out
    except Exception as exc:                        # noqa: BLE001 - never let the improvement break the existing explanation
        logger.warning("[error_improvement] fell back to the existing explanation for %s: %s: %s",
                       os.path.basename(error_file), type(exc).__name__, exc)
        return {}


def findings_batch(rules: list[dict], error_file: str, numbering: dict | None = None, lang: str = "en") -> dict[str, list[str]]:
    """{rule_name: proven findings} for the rules that keep the existing explanation. {} when off, not English, or nothing is proven.
    Reads the same cached analysis as explain_batch, so it costs nothing extra. Never raises."""
    if not findings_enabled() or not gate_enabled() or not rules or not error_file or not os.path.isfile(error_file):
        return {}
    if (lang or "en").strip().lower() not in ("", "en", "english"):
        return {}
    try:
        cards = (_result_for(error_file, _repo_root(), numbering) or {}).get("cards") or {}
        out = {}
        for rule in rules:
            card = cards.get(rule.get("rule_name", ""))
            if card and not card.get("full", True) and card.get("findings"):
                out[rule["rule_name"]] = list(card["findings"])
        return out
    except Exception as exc:                        # noqa: BLE001 - the existing explanation stands without the note
        logger.warning("[error_improvement] findings skipped for %s: %s: %s", os.path.basename(error_file), type(exc).__name__, exc)
        return {}


def attach_findings(item: dict, findings: list[str]) -> dict:
    """The existing explanation, unchanged, plus one headed list of proven findings after it (in the sections and in the text)."""
    if not findings:
        return item
    out = dict(item)
    heading = DB_FINDINGS_HEADING if all(f.startswith("Not confirmed") for f in findings) else FINDINGS_HEADING
    sections = list(out.get("explanation_sections") or [])
    sections.append({"kind": "fix", "heading": heading, "steps": list(findings)})
    out["explanation_sections"] = sections
    text = (out.get("explanation") or "").rstrip()
    out["explanation"] = text + chr(10) * 2 + heading + chr(10) + chr(10).join(f"  - {f}" for f in findings)
    out["_findings"] = True
    return out



def where_to_look_batch(rules: list[dict], error_file: str, numbering: dict | None = None, lang: str = "en") -> dict[str, dict]:
    """{rule_name: {'reason', 'rows'}} for the database-return rules that keep the existing explanation but have table cells worth
    checking. {} when off, not English, or nothing to name. Reads the same cached analysis; never raises."""
    if not findings_enabled() or not gate_enabled() or not rules or not error_file or not os.path.isfile(error_file):
        return {}
    if (lang or "en").strip().lower() not in ("", "en", "english"):
        return {}
    try:
        cards = (_result_for(error_file, _repo_root(), numbering) or {}).get("cards") or {}
        out = {}
        for rule in rules:
            card = cards.get(rule.get("rule_name", ""))
            if card and not card.get("full", True) and card.get("where_to_look"):
                out[rule["rule_name"]] = dict(card["where_to_look"])
        return out
    except Exception as exc:                        # noqa: BLE001 - the existing explanation stands without the table
        logger.warning("[error_improvement] where-to-look skipped for %s: %s: %s", os.path.basename(error_file), type(exc).__name__, exc)
        return {}


WHERE_TO_LOOK_COLUMNS = ["Table Name", "Column", "Code", "Row"]


def attach_where_to_look(item: dict, where: dict) -> dict:
    """The existing explanation with a 'Where to look' table right after its rule and condition, before the values:

        title / problem / Validation Rule / Satisfactory condition / i.e. ...
        Where to look (not confirmed: <reason>)   Table Name | Column | Code | Row
        This rule failed for N items ... / Values / Fix
    """
    rows = [list(r) for r in (where or {}).get("rows") or []]
    if not rows:
        return item
    reason = (where or {}).get("reason") or ""
    heading = "Where to look (not confirmed" + (f": {reason})" if reason else ")")
    columns = list(WHERE_TO_LOOK_COLUMNS) + (["Table holds"] if rows and len(rows[0]) > 4 else [])
    out = dict(item)
    sections = list(out.get("explanation_sections") or [])
    table = {"kind": "table", "heading": heading, "columns": columns, "rows": rows}
    at = next((i + 1 for i, s in enumerate(sections) if s.get("kind") == "rule" and not s.get("heading")), None)
    if at is None:
        at = next((i for i, s in enumerate(sections) if s.get("kind") in ("note", "matrix")), len(sections))
    sections.insert(at, table)
    out["explanation_sections"] = sections
    text = (out.get("explanation") or "")
    block = heading + chr(10) + "  " + " | ".join(columns) + chr(10) + chr(10).join("  " + " | ".join(r) for r in rows)
    marker = text.find("This rule failed for")
    if marker < 0:
        marker = text.find(chr(10) + "Values")
        marker = marker + 1 if marker >= 0 else -1
    out["explanation"] = (text[:marker] + block + chr(10) * 2 + text[marker:]) if marker >= 0 else text.rstrip() + chr(10) * 2 + block
    out["_where_to_look"] = True
    return out
