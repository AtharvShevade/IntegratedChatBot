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
from collections import OrderedDict

logger = logging.getLogger(__name__)

_CACHE: "OrderedDict[tuple, dict]" = OrderedDict()
_LOCK = threading.Lock()
_MAX_ENTRIES = 3


def enabled() -> bool:
    return os.getenv("ERROR_IMPROVEMENT", "1").strip().lower() not in ("0", "false", "no", "off")


def gate_enabled() -> bool:
    return os.environ.get("ERROR_IMPROVEMENT_GATE", "1").strip().lower() not in ("0", "false", "no", "off")


def findings_enabled() -> bool:
    return enabled() and os.environ.get("ERROR_IMPROVEMENT_FINDINGS", "1").strip().lower() not in ("0", "false", "no", "off")


FINDINGS_HEADING = "What we found in your workbook"


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
        if hit is not None:
            _CACHE.move_to_end(key)
            return hit
    from . import explain as ex                    # imported late: the engine is only loaded when it is used
    result = ex.explain_file(error_file, repo, numbering=numbering)
    slim = {"cards": result.get("cards") or {}, "info": result.get("info") or {}}
    with _LOCK:
        _CACHE[key] = slim
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
    sections = list(out.get("explanation_sections") or [])
    sections.append({"kind": "fix", "heading": FINDINGS_HEADING, "steps": list(findings)})
    out["explanation_sections"] = sections
    text = (out.get("explanation") or "").rstrip()
    out["explanation"] = text + chr(10) * 2 + FINDINGS_HEADING + chr(10) + chr(10).join(f"  - {f}" for f in findings)
    out["_findings"] = True
    return out
