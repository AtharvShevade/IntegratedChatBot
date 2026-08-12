# backend/tools/error_llm.py — the single grounded LLM phrasing layer shared by
# the formula-error and dimension-error explainers.
#
# CONTRACT
# --------
# The LLM receives ONLY an already-verified structured payload. It never sees
# raw HTML, never sees a taxonomy file, and is never asked to compute anything.
# Every number, label, member list, verdict and location in the payload was
# produced deterministically before this module is called.
#
# Whatever it returns is then re-checked against that same payload by
# is_grounded(), and rejected wholesale on any of:
#
#   * a business label from the payload missing from the text
#   * a variable id (V1/V2/…) leaking through
#   * a NUMBER that is not in the payload  — the check that stops an invented
#     amount, which is the highest-consequence hallucination here
#   * wording that contradicts the computed relationship
#   * a member/dimension name not present in the payload
#
# On rejection the caller falls back to its deterministic template, so the
# explanation is never less than correct — only sometimes less fluent.
#
# This generalises the grounding gate that previously lived (formula-only) in
# formula_error_generic._llm_output_is_grounded, rather than duplicating it.

from __future__ import annotations

import json as _json
import logging
import os
import re

logger = logging.getLogger(__name__)

__all__ = ["llm_settings", "phrase", "is_grounded", "collect_numbers"]


def llm_settings() -> dict:
    """Ollama connection settings, read from the same environment variables the
    existing explainers already use — no new configuration is introduced."""
    try:
        max_concurrency = max(1, int(os.getenv("OLLAMA_MAX_CONCURRENCY", "2")))
    except ValueError:
        max_concurrency = 2
    return {
        "base": os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
        "model": os.getenv("OLLAMA_MODEL", "llama3.1:latest"),
        "timeout": float(os.getenv("OLLAMA_TIMEOUT", "180")),
        "keep_alive": os.getenv("OLLAMA_KEEP_ALIVE", "30m"),
        "max_concurrency": max_concurrency,
        "enabled": os.getenv("ERROR_EXPLAIN_LLM", "1").strip().lower()
                   not in ("0", "false", "no", "off"),
    }


_NUMBER_RE = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


def collect_numbers(value) -> set[str]:
    """Every numeric token appearing anywhere in a payload, normalised so
    '1,234.50', '1234.5' and '1234.50' compare equal.

    Normalising matters because the model is told to quote figures verbatim but
    will legitimately re-format them with thousands separators; without
    normalisation every such answer would be rejected as "invented".
    """
    out: set[str] = set()

    def norm(token: str) -> str:
        text = token.replace(",", "").lstrip("+")
        if text.startswith("-"):
            sign, text = "-", text[1:]
        else:
            sign = ""
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        text = text.lstrip("0") or "0"
        return sign + text if text != "0" else "0"

    def walk(node) -> None:
        if node is None or isinstance(node, bool):
            return
        if isinstance(node, (int, float)):
            out.add(norm(str(node)))
            return
        if isinstance(node, dict):
            for v in node.values():
                walk(v)
            return
        if isinstance(node, (list, tuple, set)):
            for v in node:
                walk(v)
            return
        for match in _NUMBER_RE.findall(str(node)):
            out.add(norm(match))

    walk(value)
    return out


_VAR_REF_RE = re.compile(r"\bV\d+\b")

# "0 + 0 + 34000, which equals 0" / "1 + 2 = 4" — an arithmetic assertion the
# model made up. Checked for internal consistency, not against the payload,
# because a correct restatement of payload numbers is fine.
_INLINE_SUM_RE = re.compile(
    r"(-?\d[\d,]*(?:\.\d+)?(?:\s*[+\-]\s*-?\d[\d,]*(?:\.\d+)?)+)"
    r"\s*[,)]?\s*(?:=|equals|equalling|which equals|totals?|totalling|"
    r"adds? up to|sums? to|giving|for a total of)\s*"
    r"(-?\d[\d,]*(?:\.\d+)?)",
    re.IGNORECASE,
)

_UNIVERSAL_CLAIM_RE = re.compile(
    r"\b(all|each|every|both)\b[^.;]{0,90}?"
    r"\b(are|is|have|has|equal|equals|identical|the same|zero)\b",
    re.IGNORECASE,
)


def _incorrect_inline_arithmetic(text: str) -> str:
    """The first arithmetic assertion in *text* whose stated result is wrong,
    or "" when every one of them checks out."""
    from decimal import Decimal, InvalidOperation

    for expression, stated in _INLINE_SUM_RE.findall(text or ""):
        tokens = re.findall(r"[+\-]?\s*\d[\d,]*(?:\.\d+)?", expression)
        try:
            total = Decimal(0)
            for i, token in enumerate(tokens):
                cleaned = token.replace(",", "").replace(" ", "")
                if i and cleaned[0] not in "+-":
                    cleaned = "+" + cleaned
                total += Decimal(cleaned)
            claimed = Decimal(stated.replace(",", ""))
        except (InvalidOperation, ValueError, IndexError):
            continue
        if total != claimed:
            return f"{expression.strip()} = {stated}"
    return ""
_CONTRADICTION_RE = re.compile(
    r"\b(exceed(?:s|ed)?|greater than|higher than|larger than|lower than|"
    r"less than|smaller than|short(?:fall)? of|falls short)\b",
    re.IGNORECASE,
)


# Longest first, so "greater than or equal to" is matched before "greater than".
_COMPARISON_PHRASES = (
    "greater than or equal to", "less than or equal to", "not equal to",
    "greater than", "less than", "equal to",
)


def _misstates_the_requirement(body: str, operator_meaning: str | None) -> str:
    """A comparison phrase in *body* that contradicts the rule's own operator,
    or "" when the wording is consistent with it."""
    if not operator_meaning:
        return ""
    lowered = body.lower()
    meaning = operator_meaning.lower()
    remaining = lowered
    for phrase in _COMPARISON_PHRASES:
        if phrase in meaning:
            # Blank out the rule's own phrasing so a longer phrase containing
            # it ("greater than" inside "greater than or equal to") does not
            # register as a different comparison.
            remaining = remaining.replace(phrase, " ")
    for phrase in _COMPARISON_PHRASES:
        if phrase in meaning:
            continue
        if phrase in remaining:
            return phrase
    return ""


def is_grounded(text: str, payload: dict, required_terms: list[str]) -> tuple[bool, str]:
    """Check LLM output against the payload it was given.

    Returns (ok, reason). *reason* names the first failed check so rejections
    are diagnosable in the log rather than silently degrading to the template.
    """
    body = (text or "").strip()
    if not body:
        return False, "empty"

    lowered = body.lower()

    for term in required_terms:
        term = (term or "").strip()
        if term and term.lower() not in lowered:
            return False, f"missing required term: {term!r}"

    if _VAR_REF_RE.search(body):
        return False, "leaked a variable id (V1/V2/…)"

    # Inline arithmetic the model wrote itself ("0 + 0 + 34000, which equals 0")
    # is checked for its own internal consistency. The model is never asked to
    # compute anything, so any sum it states must at least be right.
    bad_sum = _incorrect_inline_arithmetic(body)
    if bad_sum:
        return False, f"states arithmetic that does not hold: {bad_sum}"

    allowed_numbers = collect_numbers(payload)
    for token in _NUMBER_RE.findall(body):
        normalised = next(iter(collect_numbers(token)), None)
        if normalised is None:
            continue
        # Small integers are almost always prose ("both values", "3 of them",
        # a year, a list index) rather than a reported amount, and rejecting
        # them makes the gate unusable. Anything larger must be in the payload.
        if normalised.lstrip("-").replace(".", "").isdigit() and len(normalised.lstrip("-")) <= 2:
            continue
        if normalised not in allowed_numbers:
            return False, f"number not present in verified facts: {token!r}"

    relationship = payload.get("relationship")
    if relationship == "lhs_equal" and _CONTRADICTION_RE.search(body):
        return False, "claims a difference where the verified values are equal"

    # The rule's own comparison must not be restated as a different one. A fix
    # sentence saying a total should be "greater than" its components, for a
    # rule that requires them to be EQUAL, tells the user to do the wrong
    # thing — the highest-consequence error this field can contain.
    wrong = _misstates_the_requirement(body, payload.get("operator_meaning"))
    if wrong:
        return False, f"restates the rule's comparison as {wrong!r}"

    # A false universal claim ("all of these values are zero") is the failure
    # mode when several variables share a concept name but hold different
    # values. Driven entirely by the payload's own values, not by any concept.
    if payload.get("_values_are_uniform") is False and _UNIVERSAL_CLAIM_RE.search(body):
        return False, "claims the values are all the same when the verified facts differ"

    # Technical identifiers are context for the model, not vocabulary for the
    # reader: quoting one back exposes XBRL internals instead of the business
    # name the label already provides.
    for technical in payload.get("_technical_names") or []:
        if technical and technical in body:
            return False, f"quoted an internal technical name: {technical!r}"

    # Dimension payloads carry a closed set of member names; anything that
    # looks like a member but was not offered is an invented taxonomy fact.
    allowed_members = payload.get("_allowed_member_terms")
    if allowed_members is not None:
        for match in re.findall(r"\b[A-Za-z][A-Za-z0-9]*(?:Member|Axis|Domain)\b", body):
            if match.lower() not in {m.lower() for m in allowed_members}:
                return False, f"named a taxonomy item not in the verified facts: {match!r}"

    return True, ""


_SYSTEM_PROMPT = (
    "You explain already-verified regulatory validation results in natural business "
    "language. Every fact you are given is authoritative ground truth, produced by "
    "deterministic code — you never calculate, recalculate, or infer a number, a "
    "relationship, a taxonomy rule, or a database location yourself. You only phrase "
    "what you are told. Quote the given business labels exactly. Never write V1, V2, "
    "V3. Never state a number that is not in the facts. Never contradict the given "
    "relationship. Write naturally, not from a fixed template."
)


def phrase(
    payload: dict,
    required_terms: list[str],
    fields: dict[str, str],
    settings: dict | None = None,
) -> dict | None:
    """Ask the LLM for one short piece of prose per entry in *fields*.

    *fields* maps output key -> instruction for that key, e.g.
    {"why_failed": "one or two sentences on why the check failed",
     "how_to_fix": "one sentence of conservative, actionable guidance"}.

    Returns the dict of fields, or None when the LLM is disabled, unreachable,
    returns malformed JSON, or fails grounding. None always means "use the
    deterministic template" — never "give up on explaining".
    """
    settings = settings or llm_settings()
    if not settings.get("enabled"):
        return None

    try:
        import httpx as _httpx
    except ImportError:
        return None

    field_spec = "\n".join(f"  {key} — {desc}" for key, desc in fields.items())
    prompt = (
        "Below is a VERIFIED, AUTHORITATIVE set of facts about one failed regulatory "
        "validation check. Every value, label, relationship and taxonomy detail has "
        "already been computed and confirmed by deterministic code. None of it is "
        "yours to calculate, re-derive, or second-guess. Explain these exact facts in "
        "clear business language, the way a knowledgeable colleague would say it — not "
        "by filling in a template. Vary your wording; do not reuse a fixed phrasing.\n\n"
        "VERIFIED FACTS (authoritative — do not recalculate, reinterpret or add to these):\n"
        f"{_json.dumps(_public(payload), indent=2, ensure_ascii=False, default=str)}\n\n"
        "STRICT GROUNDING RULES — breaking any of these makes your answer unusable:\n"
        "1. Quote every business label EXACTLY as spelled above. Do not paraphrase, "
        "   shorten, reorder or substitute a synonym.\n"
        "2. Never state a number that does not appear above — do not round, estimate, "
        "   convert, or restate a figure differently.\n"
        "3. Never invent a concept, dimension, member, table, column, report or "
        "   database location that is not explicitly present above.\n"
        "4. Never contradict the stated relationship or verdict.\n"
        "5. Never refer to a field as V1, V2, V3 — always use its given label.\n"
        "6. Do not mention XBRL, XPath, formulas, linkbases or internal rule ids.\n\n"
        f"Write these fields:\n{field_spec}\n\n"
        "Return ONLY a single-line JSON object with exactly those keys. "
        "No other text, no markdown, no code fences."
    )

    body = {
        "model": settings["model"],
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "keep_alive": settings["keep_alive"],
        "options": {"temperature": 0.2, "num_predict": 320},
    }

    try:
        with _httpx.Client(timeout=settings["timeout"]) as client:
            resp = client.post(f"{settings['base']}/api/chat", json=body)
            resp.raise_for_status()
        content = resp.json()["message"]["content"].strip()
        content = re.sub(r"^```(?:json)?|```$", "", content, flags=re.MULTILINE).strip()
        parsed = _parse_json_object(content, list(fields))
        if parsed is None:
            raise ValueError("no usable JSON object in response")
    except Exception as exc:
        logger.info("[error_llm] phrasing unavailable (%s) — using deterministic text", exc)
        return None

    out: dict[str, str] = {}
    for key in fields:
        value = _as_text(parsed.get(key)) if isinstance(parsed, dict) else ""
        if not value:
            logger.info("[error_llm] rejected: field %r missing", key)
            return None
        out[key] = value

    ok, reason = is_grounded(" ".join(out.values()), payload, required_terms)
    if not ok:
        logger.info("[error_llm] rejected: %s", reason)
        return None
    return out


def _as_text(value) -> str:
    """Normalise one model-returned field to text.

    A field asked for as "several short sentences, one per line" comes back as
    a JSON ARRAY about as often as a string, and nested objects turn up too.
    Coercing here rather than assuming `str` is what keeps a well-formed answer
    in an unexpected container from being thrown away — and, before this
    existed, from raising out of phrase() entirely and discarding the caller's
    finished deterministic explanation.
    """
    if value is None or isinstance(value, bool):
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (list, tuple)):
        parts = [_as_text(v) for v in value]
        return "\n".join(p for p in parts if p)
    if isinstance(value, dict):
        parts = [_as_text(v) for v in value.values()]
        return "\n".join(p for p in parts if p)
    return str(value).strip()


def _parse_json_object(content: str, keys: list[str]) -> dict | None:
    """Extract the requested fields from a model response.

    Strict json.loads first. Models routinely emit business labels containing
    an apostrophe or a quoted phrase without escaping it, which makes the
    object unparseable even though the content is fine — so the fallback pulls
    each field out by key, taking the closing quote to be the one followed by a
    comma or the closing brace.

    This only affects how the text is EXTRACTED. Whatever comes out still goes
    through is_grounded() before it can reach a user, so a lenient parse cannot
    weaken the correctness guarantee.
    """
    try:
        parsed = _json.loads(content)
        if isinstance(parsed, dict):
            return parsed
    except ValueError:
        pass

    out: dict[str, str] = {}
    for key in keys:
        m = re.search(
            rf'"{re.escape(key)}"\s*:\s*"(.*?)"\s*(?=,\s*"|\}}|$)',
            content, re.S,
        )
        if m:
            out[key] = m.group(1).replace('\\"', '"').replace("\\n", " ").strip()
    return out or None


def _public(payload: dict) -> dict:
    """Strip the internal keys (leading underscore) that exist only to drive
    the grounding gate and should never reach the prompt."""
    return {k: v for k, v in payload.items() if not str(k).startswith("_")}
