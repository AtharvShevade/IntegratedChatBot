"""The translation boundary itself: two functions, called from main.py.

    translate_inbound(user text)  ->  English   ->  decide()  unchanged
    decide() result               ->  translate_outbound()    ->  ChatResponse

Design constraints this module exists to satisfy:

  * The English pipeline never changes. decide() receives an ordinary English
    string and returns its ordinary dict. Nothing in backend/agent, db_qa,
    sql_agent or the 14 list-rendering sites is aware this module exists.

  * Disabled is byte-identical. MULTILINGUAL_ENABLED=false, or lang in
    ("", None, "en"), returns the input object itself -- not a copy, not a
    reconstruction, and with no metadata key added.

  * Inbound failure is FATAL, outbound failure is not. Routing a
    half-translated question produces a confidently wrong regulatory answer;
    an English answer to a French question is merely unhelpful. The asymmetry
    is deliberate and is the single most important rule here.

  * Identifiers cannot be corrupted, rather than being asked not to be.
    Option lists never reach the model at all -- payload.py masks them out and
    they are re-rendered from options[] afterwards.

Scope: the eight prose fields in TRANSLATABLE_FIELDS, plus the user-visible
prose nested inside error_details[] (see _nested_payload). Both go through the
same path -- catalogue first, model only for what the catalogue cannot resolve.
"""
from __future__ import annotations

import asyncio
import copy
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any

from backend.i18n import catalogue, config, payload, protect
from backend.i18n.translator import Translator, TranslationResult, get_translator

logger = logging.getLogger(__name__)

# The response fields a translation layer touches. Validated on the 24-case
# FR/AR/HI evaluation as eval/multilingual/pipeline.py:185.
#
# Everything NOT listed here passes through untouched, and that is the primary
# entity-protection mechanism: report_name, options, db_sql, db_columns,
# db_rows, db_records, db_qa_data, variance_data, variance_all, variance_meta,
# variance_label_a/b, instances_data, download_url, error_details, job_id.
# Every regulatory identifier the system emits (DBR01, CIMS_ROR,
# CIMS_RAQ(Monthly), RAQ(Quarterly), ...) travels in one of those.
#
# error_details is absent from this tuple because it is a LIST OF DICTS, not a
# string field -- its prose is handled by _nested_payload() below, which routes
# it through this same pipeline.
TRANSLATABLE_FIELDS: tuple[str, ...] = (
    "response_text",
    "llm_summary",
    "db_summary",
    "db_beautified",
    "status_note",
    "accuracy_hint",
    "more_info_hint",
    "download_label",
)

# Static, never model-generated. An error path that needs the model to report a
# model failure is not an error path.
_INBOUND_FAILURE_TEXT: dict[str, str] = {
    "en": "Sorry, your message could not be processed. Please try again.",
    "fr": "Désolé, votre message n'a pas pu être traité. Veuillez réessayer.",
    "ar": "عذرًا، تعذّرت معالجة رسالتك. يرجى المحاولة مرة أخرى.",
    "hi": "क्षमा करें, आपका संदेश संसाधित नहीं किया जा सका. कृपया पुनः प्रयास करें.",
}

# Appended when the answer is correct but could not be localized. Distinct from
# the inbound failure: the user still gets their answer.
_OUTBOUND_FALLBACK_NOTE: dict[str, str] = {
    "en": "",
    "fr": "(Réponse affichée en anglais : la traduction est momentanément indisponible.)",
    "ar": "(يتم عرض الرد بالإنجليزية: الترجمة غير متاحة مؤقتًا.)",
    "hi": "(उत्तर अंग्रेज़ी में दिखाया गया है: अनुवाद अस्थायी रूप से अनुपलब्ध है.)",
}

# Inbound skip rules. Each avoids a model call that could only do harm.
#
# A message with no letter at all -- "2", "01-01-2025", "3.5" -- is the
# disambiguation reply path (agent/__init__.py:1100-1114, which does
# int(raw_input)) and every date prompt. Language-neutral by construction, and
# the most latency-sensitive turn in the product.
_HAS_ALPHA_RE = re.compile(r"[^\W\d_]", re.UNICODE)

# An identifier the user typed back from an option list. ASCII, no whitespace,
# AND containing at least one digit, underscore or parenthesis: CIMS_ROR,
# DBR01, CIMS_RAQ(Monthly), RAQ(Quarterly), R149.
#
# Mixed case is required, not just upper: real return names embed capitalised
# words inside parentheses -- "CIMS_RAQ(Monthly)", "RAQ(Annually)".
#
# The digit/underscore/parenthesis requirement is what keeps this narrow enough
# to be safe. It must never match an ordinary word, so a bare "RAQ", "bonjour"
# or "OUI" is NOT skipped and goes through the model, where prompt rule 2
# protects it anyway. Non-ASCII input (Arabic, Hindi, accented French) can
# never match at all.
_IDENTIFIER_RE = re.compile(r"^(?=.*[\d_()])[A-Za-z0-9_()\-./]{2,64}$")

# The guided menu sentinel. Documented at main.py:726.
_GUIDED_SENTINEL = "__GUIDED_START__"


@dataclass
class InboundResult:
    """Outcome of user-language -> English.

    ``ok=False`` means the caller MUST NOT call decide(). ``text`` is then the
    untranslated original, kept only for logging.
    """

    text: str
    lang: str
    ok: bool = True
    translated: bool = False
    latency_ms: float = 0.0
    error: str | None = None
    skip_reason: str | None = None
    model: str = ""

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "translated": self.translated,
            "latency_ms": round(self.latency_ms, 1),
            "error": self.error,
            "skip_reason": self.skip_reason,
            "model": self.model,
        }


@dataclass
class OutboundResult:
    """Outcome of English -> user language, per response."""

    ok: bool = True
    translated: bool = False
    latency_ms: float = 0.0
    fields: list[str] = field(default_factory=list)
    options_masked: list[str] = field(default_factory=list)
    options_count: int = 0
    chars_sent: int = 0
    chars_total: int = 0
    # How many report names / IDs / dates / numbers were masked out of the
    # prose, and how many the model failed to give back.
    entities_masked: int = 0
    entities_lost: int = 0
    # Model calls actually dispatched, after identical fields are deduplicated.
    calls: int = 0
    # Fields localized from the pre-translated catalogue -- zero model calls.
    catalogued: list[str] = field(default_factory=list)
    # Prose strings localized inside error_details[].
    nested_fields: int = 0
    # Fields left English because the model budget could not fit them.
    deferred: list[str] = field(default_factory=list)
    # error_details[].explanation blobs rebuilt from already-localized section
    # prose -- no model call of their own.
    derived: int = 0
    # Fields that are pure data once masked (arithmetic), so never sent.
    data_only: list[str] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)
    model: str = ""

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "translated": self.translated,
            "latency_ms": round(self.latency_ms, 1),
            "fields": self.fields,
            "deferred": self.deferred,
            "derived": self.derived,
            "data_only": self.data_only,
            "options_masked": self.options_masked,
            "options_count": self.options_count,
            "chars_sent": self.chars_sent,
            "chars_total": self.chars_total,
            "entities_masked": self.entities_masked,
            "entities_lost": self.entities_lost,
            "calls": self.calls,
            "catalogued": self.catalogued,
            "nested_fields": self.nested_fields,
            "errors": self.errors,
            "model": self.model,
        }


# ---------------------------------------------------------------------------
# Language handling
# ---------------------------------------------------------------------------

def normalize_lang(lang: str | None) -> str:
    """Reduce a client-supplied tag to a language this boundary handles.

    Accepts BCP-47 ("fr-CA" -> "fr"). Anything unsupported becomes "en":
    English is always serviceable, and refusing a request the pipeline can
    answer is a worse failure than not localizing it. Logged, not raised.
    """
    if not lang:
        return "en"
    base = str(lang).strip().lower().replace("_", "-").split("-")[0]
    if not base:
        return "en"
    if base not in config.supported_languages():
        logger.info("[I18N] unsupported lang=%r -> falling back to English", lang)
        return "en"
    return base


def should_translate(lang: str | None) -> bool:
    """True only when the feature is on AND a non-English language was asked
    for. This is the single gate; both boundary functions consult it first."""
    return config.is_enabled() and normalize_lang(lang) != "en"


def is_rtl(lang: str | None) -> bool:
    return normalize_lang(lang) in config.RTL_LANGUAGES


# ---------------------------------------------------------------------------
# Inbound: user language -> English
# ---------------------------------------------------------------------------

def _inbound_skip_reason(message: str) -> str | None:
    """Why this message must not be sent to the translation model, or None.

    Each rule prevents a call that could only corrupt the message, and each
    also removes latency from the turn.
    """
    text = (message or "").strip()
    if not text:
        return "empty"
    if text == _GUIDED_SENTINEL:
        return "guided-sentinel"
    if not _HAS_ALPHA_RE.search(text):
        # Numeric disambiguation reply, a date, an amount. int(raw_input) at
        # agent/__init__.py:1103 would break on a translated digit shape.
        return "no-letters"
    if _IDENTIFIER_RE.match(text):
        # A report/return/instance identifier typed back verbatim. The staged
        # matcher at agent/__init__.py:1119-1122 is a raw ASCII substring test
        # against the English name -- a transliterated identifier cannot match.
        return "identifier"
    try:
        from backend.guided import GUIDED_ACTIONS, normalize_confirmation
        if text in GUIDED_ACTIONS:
            # Matched exactly, in English, at guided.py:179-180.
            return "guided-action"
        if normalize_confirmation(text) is not None:
            # A static guided yes/no reply (any supported language, case- and
            # whitespace-insensitive) -- consumed deterministically by
            # STAGE_PREV_DATES via the same normalize_confirmation() call.
            return "guided-confirmation"
    except Exception:  # noqa: BLE001 - the skip is an optimisation, not a gate
        pass
    return None


async def translate_inbound(
    message: str,
    lang: str | None,
    translator: Translator | None = None,
) -> InboundResult:
    """Translate a user message into English for the pipeline.

    On ANY failure this returns ok=False and the caller must abandon the turn.
    A timed-out or truncated translation looks exactly like a valid short
    question to decide(), which would then route it confidently and wrongly --
    the failure mode this whole design is built to prevent.
    """
    resolved = normalize_lang(lang)
    if not should_translate(lang):
        return InboundResult(text=message, lang=resolved, ok=True, skip_reason="disabled-or-english")

    skip = _inbound_skip_reason(message)
    if skip:
        logger.info("[I18N_IN] skip=%s lang=%s", skip, resolved)
        return InboundResult(text=message, lang=resolved, ok=True, skip_reason=skip)

    started = time.perf_counter()
    client = translator or get_translator()
    result = await client.translate(message, resolved, "en")
    elapsed = (time.perf_counter() - started) * 1000.0

    if not result.ok:
        logger.warning(
            "[I18N_IN] FAILED lang=%s model=%s error=%s -- request refused, "
            "pipeline NOT called", resolved, result.model, result.error,
        )
        return InboundResult(
            text=message, lang=resolved, ok=False, latency_ms=elapsed,
            error=result.error, model=result.model,
        )

    logger.info(
        "[I18N_IN] lang=%s->en model=%s %.0fms chars=%d->%d",
        resolved, result.model, elapsed, len(message), len(result.text),
    )
    return InboundResult(
        text=result.text, lang=resolved, ok=True, translated=True,
        latency_ms=elapsed, model=result.model,
    )


def inbound_failure_response(lang: str | None, error: str | None = None) -> dict[str, Any]:
    """The response for a request whose translation failed.

    Shaped exactly like agent._build()'s error output so the frontend needs no
    special case. Deliberately NOT routed: the pipeline was never called.
    """
    resolved = normalize_lang(lang)
    return {
        "intent": "unknown",
        "report_name": None,
        "response_text": _INBOUND_FAILURE_TEXT.get(resolved, _INBOUND_FAILURE_TEXT["en"]),
        "need_clarification": False,
        "result_type": "error",
        "options": [],
        "download_url": "",
        "download_label": "",
        "status_note": "",
        "data": {
            "i18n": {
                "lang": resolved,
                "rtl": is_rtl(resolved),
                "inbound": {"ok": False, "error": error},
            }
        },
    }


# ---------------------------------------------------------------------------
# Outbound: English -> user language
# ---------------------------------------------------------------------------

def translatable_payload(result: dict[str, Any]) -> dict[str, str]:
    """The subset of a response the boundary will actually translate."""
    return {
        name: value
        for name in TRANSLATABLE_FIELDS
        if isinstance((value := result.get(name)), str) and value.strip()
    }


# ---------------------------------------------------------------------------
# Nested prose inside error_details[]
# ---------------------------------------------------------------------------
#
# error_details is a LIST OF DICTS, so it cannot sit in TRANSLATABLE_FIELDS.
# The user-visible prose inside it is flattened to dotted pseudo-field names,
# joined to the ordinary payload, and put back afterwards. Doing it that way
# means these strings get the whole existing pipeline for free: catalogue
# resolution first (0 model calls), then entity masking, deduplication and one
# concurrent batch -- no second translation mechanism.
#
# WHAT IS TAKEN (prose the user reads):
#     explanation                      the rendered card, mixed template + LLM
#     explanation_sections[].heading   "Where", "Rule", "How to fix", ...
#     explanation_sections[].text      the LLM-authored body
#     explanation_sections[].items[].label
#
# WHAT IS NOT (data, and translating it would corrupt the report):
#     explanation_sections[].items[].value   concept names, figures, contexts
#     message / col_0 / title / business_rule / rule_name / concept
#         raw validator output and XBRL identifiers, not authored prose
_NESTED_ROOT = "error_details"


def _nested_payload(result: dict[str, Any]) -> tuple[dict[str, str], dict[str, tuple[str, ...]]]:
    """Flatten the prose inside error_details[] to dotted pseudo-field keys.

    Walks the full error-card schema (backend/tools/error_card.py:36-46):

        headline  text
        locator   heading, items[].label            items[].value is DATA
        rule      heading, text
        matrix    heading, columns.{label,          rows[].{label,expected,
                  expected,actual}, rows[].note      actual,status} are DATA
        fix       heading, steps[]
        points    heading, bullets[]
        details   heading, sections[]  (recurses -- v1 sections nested in v2)
    """
    out: dict[str, str] = {}
    # field key -> the concept labels its section published in `terms`. These
    # are DATA (see protect._extra_pattern) and are masked out of the prose
    # before it is catalogued or translated.
    terms: dict[str, tuple[str, ...]] = {}
    current: tuple[str, ...] = ()

    def take(key: str, value: Any) -> None:
        if isinstance(value, str) and value.strip():
            out[key] = value
            if current:
                terms[key] = current

    def walk_section(base: str, section: Any, parent_kind: str | None = None) -> None:
        if not isinstance(section, dict):
            return
        nonlocal current
        kind = section.get("kind")
        outer = current
        # error_card.attach_emphasis() already deduped these longest-first.
        section_terms = tuple(t for t in (section.get("terms") or ()) if isinstance(t, str))
        if section_terms:
            current = section_terms
        # The heading is a UI label on every kind, so it always translates.
        take(f"{base}.heading", section.get("heading"))
        # `text` is authored prose EXCEPT where the schema marks it raw:
        #
        #   * mono=True -- error_card.py:104 documents this as "a raw
        #     identifier"; MessageBubble.jsx:496 renders it inside <code>.
        #   * a `rule` section nested inside `details` -- this is the
        #     VALIDATOR'S OWN message, e.g. "Weighted Average Interest Rate (%)
        #     = If (Rupee Term Deposits(Total outstanding)+...)>0 then ...".
        #     It is a formula expression, not a sentence, and is kept
        #     byte-identical for the same reason error_details[].message is.
        #
        # Both tests are STRUCTURAL (kind / mono), never a match on the English
        # heading text, so a heading may be translated freely without changing
        # which text is protected.
        raw_text = bool(section.get("mono")) or (kind == "rule" and parent_kind == "details")
        if not raw_text:
            take(f"{base}.text", section.get("text"))
        # Bullet/step lists are authored prose.
        for name in ("steps", "bullets"):
            for n, entry in enumerate(section.get(name) or []):
                take(f"{base}.{name}.{n}", entry)
        # Matrix COLUMN HEADERS are labels; the rows under them are values.
        columns = section.get("columns")
        if isinstance(columns, dict):
            for name in ("label", "expected", "actual"):
                take(f"{base}.columns.{name}", columns.get(name))
        # locator items: the label is prose, the value is the concept/figure.
        for n, item in enumerate(section.get("items") or []):
            if isinstance(item, dict):
                take(f"{base}.items.{n}.label", item.get("label"))
        # matrix rows: only the explanatory note, never label/expected/actual.
        for n, row in enumerate(section.get("rows") or []):
            if isinstance(row, dict):
                take(f"{base}.rows.{n}.note", row.get("note"))
        # `details` nests whole v1 sections inside a v2 card.
        for n, nested in enumerate(section.get("sections") or []):
            walk_section(f"{base}.sections.{n}", nested, kind)
        current = outer

    for i, detail in enumerate(result.get(_NESTED_ROOT) or []):
        if not isinstance(detail, dict):
            continue
        sections = detail.get("explanation_sections") or []
        # `explanation` is the same card flattened into one 2-3 KB string. When
        # the sections are present it is pure duplication, so it is NOT sent to
        # the model: _derive_explanations() rebuilds it from the localized
        # sections afterwards, for free and word-for-word consistent with them.
        # Without sections (v1 producers, and the error-path fallback at
        # formula_error.py:3326) it is the only prose there is, so it goes
        # through normally.
        if not sections:
            take(f"{_NESTED_ROOT}.{i}.explanation", detail.get("explanation"))
        for j, section in enumerate(sections):
            walk_section(f"{_NESTED_ROOT}.{i}.explanation_sections.{j}", section)
    return out, terms


def _derive_explanations(
    localized: dict[str, Any],
    english: dict[str, str],
    nested_out: dict[str, str],
    lang: str,
) -> int:
    """Rebuild each error_details[].explanation from its localized sections.

    ``explanation`` is the whole card re-rendered as one string (2-3 KB per
    error). MessageBubble.jsx:693-696 draws the card from
    ``explanation_sections`` and only falls back to this string, but the string
    IS shown on the report-status path (MessageBubble.jsx:1009), so it cannot
    just be left English.

    Translating it would mean sending the same prose to the model a second
    time, tripling both the cost and the latency of an error card -- and
    risking a second, differently-worded rendering of sentences the sections
    already localized. Instead the blob is REBUILT: every section fragment that
    was localized is substituted into it, longest first so a short fragment
    cannot cut into a longer one. No model call, and the blob is guaranteed to
    agree word-for-word with the card above it.

    A fragment that is not found is simply not substituted, so scaffolding the
    sections do not carry (list markers, blank lines) survives untouched.
    Returns how many explanations were rebuilt.
    """
    pairs: dict[int, list[tuple[str, str]]] = {}
    for key, localized_text in nested_out.items():
        parts = key.split(".")
        # error_details . <i> . explanation_sections . ...
        if len(parts) < 4 or parts[2] != "explanation_sections":
            continue
        source = english.get(key)
        if source and source != localized_text:
            pairs.setdefault(int(parts[1]), []).append((source, localized_text))

    details = localized.get(_NESTED_ROOT)
    if not isinstance(details, list):
        return 0

    rebuilt = 0
    for index, fragments in pairs.items():
        if index >= len(details) or not isinstance(details[index], dict):
            continue
        # Only rebuild what the model did NOT already translate; a blob that
        # fit the budget keeps the model's own rendering.
        if f"{_NESTED_ROOT}.{index}.explanation" in nested_out:
            continue
        blob = details[index].get("explanation")
        if not isinstance(blob, str) or not blob.strip():
            continue
        updated = blob
        for source, target in sorted(fragments, key=lambda p: -len(p[0])):
            updated = updated.replace(source, target)
        # The card's own scaffolding is not a section: the blob opens with
        # "⚙ Formula Error — <rule>" (formula_error.py:1645), which no section
        # carries. Those lines are catalogue templates, so resolve them
        # line-by-line -- still no model call.
        lines = updated.split("\n")
        for n, line in enumerate(lines):
            if not line.strip():
                continue
            hit = catalogue.resolve(line, lang)
            if hit is not None:
                lines[n] = hit
        updated = "\n".join(lines)
        if updated != blob:
            details[index]["explanation"] = updated
            rebuilt += 1
    return rebuilt


def _inject_nested(result: dict[str, Any], values: dict[str, str]) -> None:
    """Write localized prose back into a DEEP COPY of error_details.

    The pipeline's own list is never mutated -- translating in place would
    change the object the agent still holds, and an English re-render of the
    same response would then come back localized.
    """
    if not values:
        return
    details = copy.deepcopy(result.get(_NESTED_ROOT) or [])
    for key, text in values.items():
        # Generic path walk, so this can never drift out of step with
        # _nested_payload: the same dotted path that produced the value is
        # followed back to the exact slot it came from.
        parts = key.split(".")[1:]          # drop the "error_details" root
        try:
            node: Any = details
            for step in parts[:-1]:
                node = node[int(step)] if step.isdigit() else node[step]
            leaf = parts[-1]
            if leaf.isdigit():
                node[int(leaf)] = text     # steps[] / bullets[] entry
            else:
                node[leaf] = text          # heading / text / label / note
        except (IndexError, KeyError, ValueError, TypeError):
            # A shape that does not match is left as the pipeline produced it
            # rather than raising at the user.
            logger.warning("[I18N_OUT] could not inject %s", key)
    result[_NESTED_ROOT] = details


# ---------------------------------------------------------------------------
# error_details[] batching -- whole objects, not one call per prose fragment
# ---------------------------------------------------------------------------
# Previously every prose fragment inside every error card (heading, text, each
# bullet, each locator label) was dispatched as its own model call, bounded
# only by the global TRANSLATION_CONCURRENCY admission semaphore -- a report
# with several errors could fan out into dozens of small calls. This groups
# COMPLETE error_details[] objects into batches of
# config.error_explanation_translation_batch_size() and sends each batch's
# fields as ONE combined translation call, cutting the call count sharply
# while keeping ordering, structure and entity protection intact.
_BATCH_SEP_MARK = "␟␟␟"  # control-picture run; never real prose


def _prepare_error_batch(
    names: list[str],
    masked: dict[str, str],
    entity_tokens: dict[str, dict[str, str]],
) -> tuple[str, dict[str, str], set[str], dict[str, list[str]]]:
    """Join several fields' already-masked texts into one payload.

    Each field's [[E#]] placeholders are RENUMBERED so none collide across
    fields once joined, and a placeholder-protected separator is inserted
    between fields so the batch can be split back apart after translation --
    the same [[E#]] shape the model has already been benchmarked to preserve,
    rather than an unproven marker of its own.

    Returns (combined_masked_text, combined_tokens, separator_keys,
    field_placeholder_keys). combined_tokens restores BOTH the real entities
    and the separators in one restore_entities() call; field_placeholder_keys
    attributes a lost entity back to the one field it belongs to.
    """
    combined_tokens: dict[str, str] = {}
    field_placeholder_keys: dict[str, list[str]] = {}
    separator_keys: set[str] = set()
    parts: list[str] = []
    counter = 0

    for i, name in enumerate(names):
        text = masked[name]
        own_tokens = entity_tokens.get(name) or {}
        keys_for_field: list[str] = []

        def _shift(match: re.Match, _own=own_tokens, _keys=keys_for_field) -> str:
            nonlocal counter
            counter += 1
            new_key = f"[[E{counter}]]"
            combined_tokens[new_key] = _own.get(match.group(0), match.group(0))
            _keys.append(new_key)
            return new_key

        shifted = re.sub(r"\[\[E\d+\]\]", _shift, text)
        field_placeholder_keys[name] = keys_for_field
        parts.append(shifted)

        if i < len(names) - 1:
            counter += 1
            sep_key = f"[[E{counter}]]"
            combined_tokens[sep_key] = _BATCH_SEP_MARK
            separator_keys.add(sep_key)
            parts.append(sep_key)

    return "\n".join(parts), combined_tokens, separator_keys, field_placeholder_keys


async def _translate_error_batch(
    names: list[str],
    masked: dict[str, str],
    to_translate: dict[str, str],
    entity_tokens: dict[str, dict[str, str]],
    client: Translator,
    resolved: str,
    meta: "OutboundResult",
    translated: dict[str, str],
    batch_no: int,
    total_batches: int,
    label: str = "error-explanation",
) -> None:
    """Translate one batch of whole "objects" (error-explanation cards, or --
    via translate_lines_in_batches -- prose lines) in a SINGLE model call,
    then split the result back into its individual fields.

    ``label`` only changes the log line's tag ("error-explanation" vs
    "compare-summary" etc.) so production logs stay readable about which
    caller a batch belongs to; the mechanism itself is generic.

    Never raises and never leaves a field unset: any failure -- the call
    itself, a lost batch separator, a segment-count mismatch -- keeps every
    field in the batch English, the same graceful-degradation guarantee the
    ordinary per-field path already gives (see translate_outbound's
    "keep English" fallback). A protected entity lost from just ONE field
    only falls that one field back to English; the rest of the batch keeps
    its translation.
    """
    combined_text, combined_tokens, separator_keys, field_keys = _prepare_error_batch(
        names, masked, entity_tokens,
    )
    started = time.perf_counter()
    tr = await client.translate(combined_text, "en", resolved)
    elapsed = time.perf_counter() - started
    logger.info(
        "[I18N_OUT] %s batch=%d/%d items=%d elapsed=%.2fs ok=%s",
        label, batch_no, total_batches, len(names), elapsed, tr.ok,
    )

    def _fall_back_all(reason: str) -> None:
        for name in names:
            translated[name] = to_translate[name]
            meta.ok = False
            meta.errors[name] = reason

    if not (tr.ok and tr.text.strip()):
        _fall_back_all(tr.error or "empty translation")
        return

    restored_whole, missing = protect.restore_entities(tr.text, combined_tokens)
    missing_set = set(missing)

    if missing_set & separator_keys:
        logger.warning(
            "[I18N_OUT] %s batch=%d/%d: lost a batch separator -- "
            "keeping English for all %d item(s) in this batch",
            label, batch_no, total_batches, len(names),
        )
        _fall_back_all("batch separator lost")
        return

    segments = restored_whole.split(_BATCH_SEP_MARK)
    if len(segments) != len(names):
        logger.warning(
            "[I18N_OUT] %s batch=%d/%d: split produced %d segment(s), "
            "expected %d -- keeping English for this batch",
            label, batch_no, total_batches, len(segments), len(names),
        )
        _fall_back_all("batch split mismatch")
        return

    for name, segment in zip(names, segments):
        lost_here = [k for k in field_keys[name] if k in missing_set]
        if lost_here:
            logger.warning(
                "[I18N_OUT] %s: translation lost %d protected entit%s in batch "
                "%d/%d -- keeping English", name, len(lost_here),
                "y" if len(lost_here) == 1 else "ies", batch_no, total_batches,
            )
            translated[name] = to_translate[name]
            meta.ok = False
            meta.errors[name] = f"lost {len(lost_here)} protected entities"
            meta.entities_lost += len(lost_here)
            continue
        translated[name] = segment.strip()
        meta.fields.append(name)


async def translate_lines_in_batches(
    text: str,
    lang: str | None,
    translator: Translator | None,
    batch_size: int,
) -> tuple[str, bool]:
    """Translate a multi-line prose blob in batches of ``batch_size`` LINES
    per model call, instead of the whole blob as one call.

    Built for /compare-summary's bulleted AI narrative ("AI Summary:\\n"
    "• fact one\\n• fact two\\n...\\n\\nOverall pattern: ..."), which
    was measured in production reliably hitting ReadTimeout on
    COMPARE_SUMMARY_TRANSLATION_TIMEOUT (180s) for a 12-bullet/1092-char
    narrative -- the exact same "one giant call" failure mode error_details[]
    batching already fixed, just on a single free-form string instead of a
    list of objects. Reuses the SAME batch/separator/restore mechanism
    (_prepare_error_batch / _translate_error_batch): each non-blank line is
    catalogue-checked first (a line the catalogue already has costs no
    call), then the remaining lines are masked, grouped into batches of
    ``batch_size``, and each batch is one combined translation call.

    Returns (localized_text, ok). ok is False if ANY line ended up staying
    English due to a failure -- the caller decides what that means (here,
    /compare-summary falls back to the original English summary exactly as
    it already does for any other translation failure).

    Never raises. A batch that fails keeps its lines' original English text,
    the same per-batch graceful degradation _translate_error_batch already
    gives error_details[].
    """
    if not should_translate(lang) or not text or not text.strip():
        return text, True

    resolved = normalize_lang(lang)
    client = translator or get_translator()
    lines = text.split("\n")

    resolved_lines: dict[int, str] = {}
    to_translate: dict[str, str] = {}
    for i, line in enumerate(lines):
        if not line.strip():
            resolved_lines[i] = line
            continue
        hit = catalogue.resolve(line, resolved)
        if hit is not None:
            resolved_lines[i] = hit
            continue
        if not protect.has_translatable_prose(line):
            resolved_lines[i] = line
            continue
        to_translate[str(i)] = line

    if not to_translate:
        return "\n".join(resolved_lines[i] for i in range(len(lines))), True

    masked: dict[str, str] = {}
    entity_tokens: dict[str, dict[str, str]] = {}
    for key, line in to_translate.items():
        masked[key], entity_tokens[key] = protect.mask_entities(line)

    meta = OutboundResult(model=getattr(client, "name", ""))
    translated: dict[str, str] = {}
    names = list(to_translate)
    batches = [names[i:i + batch_size] for i in range(0, len(names), batch_size)]

    logger.info(
        "[I18N_OUT] compare-summary lang=%s model=%s lines=%d batch_size=%d "
        "batches=%d",
        resolved, meta.model, len(names), batch_size, len(batches),
    )

    limit = asyncio.Semaphore(config.translation_concurrency())

    async def _one_batch(batch_no: int, batch_names: list[str]) -> None:
        async with limit:
            await _translate_error_batch(
                batch_names, masked, to_translate, entity_tokens, client,
                resolved, meta, translated, batch_no, len(batches),
                label="compare-summary",
            )

    await asyncio.gather(*(_one_batch(n, b) for n, b in enumerate(batches, 1)))

    for i in range(len(lines)):
        key = str(i)
        if key in translated:
            resolved_lines[i] = translated[key]
        elif i not in resolved_lines:
            resolved_lines[i] = lines[i]

    return "\n".join(resolved_lines[i] for i in range(len(lines))), meta.ok


async def translate_outbound(
    result: dict[str, Any],
    lang: str | None,
    translator: Translator | None = None,
    english_message: str | None = None,
    inbound: InboundResult | None = None,
) -> dict[str, Any]:
    """Localize a pipeline response.

    Never raises and never returns a blank field. On any failure the English
    text is kept: a correct answer in the wrong language beats no answer.

    ``english_message`` and the English source text are echoed into
    data["i18n"]["english"] so the frontend can send ENGLISH conversation
    history back on the next turn. That keeps decide()'s classifier and LLM
    extractor on English context without spending seven extra model calls
    translating history.
    """
    if not should_translate(lang):
        # A request that ASKED for a language and got English back is the one
        # silent failure this design has: the response is valid, so nothing
        # downstream complains, and the user simply sees English. Say so
        # loudly and exactly once per request -- the usual cause is the
        # backend process having started before MULTILINGUAL_ENABLED was set,
        # since os.environ is fixed at process start.
        if lang and normalize_lang(lang) != "en" and not config.is_enabled():
            logger.warning(
                "[I18N_OUT] lang=%r requested but MULTILINGUAL_ENABLED is false "
                "in THIS process -- returning English. Set it in .env and "
                "RESTART the backend.", lang,
            )
        # Identity. The exact object in, the exact object out -- no copy, no
        # new keys. This is what makes MULTILINGUAL_ENABLED=false provably
        # byte-for-byte equivalent to the pre-feature behaviour.
        return result

    resolved = normalize_lang(lang)
    localized = dict(result)
    english_payload = translatable_payload(result)
    # Prose inside error_details[] is flattened in here so it goes through the
    # identical path; _inject_nested puts it back at the end.
    nested_keys = set()
    nested, field_terms = _nested_payload(result)
    if nested:
        english_payload.update(nested)
        nested_keys = set(nested)
    options = result.get("options") or []
    meta = OutboundResult(model=config.translation_model())

    # Split prose from the rendered option list BEFORE anything is sent.
    # For a 162-option disambiguation this is 3,446 -> 122 characters, and the
    # identifiers become impossible to corrupt because they are re-inserted
    # from options[] rather than translated.
    to_translate, blocks, passthrough = payload.split_payload(english_payload, options)
    meta.options_masked = sorted(blocks)
    meta.options_count = len(options)
    meta.chars_total = sum(len(v) for v in english_payload.values())

    # ── Pre-translation, before any model call ───────────────────────────────
    # 72% of what the pipeline says is a deterministic template. Resolve those
    # from the catalogue: no network, no latency, no word-sense drift, and no
    # way for a translation to fail. Anything not covered falls through to the
    # model below exactly as before.
    #
    # This runs BEFORE the size budget below, and must keep running before it.
    # A catalogue hit costs no call and no characters, so gating it on a model
    # budget makes no sense -- and doing so was a real bug: a 3-error formula
    # card is ~12,000 characters, so the whole response tripped a 2,000-char
    # backstop and came back English, including the 49 headings and templated
    # sentences the catalogue already had translations for.
    from_catalogue: dict[str, str] = {}
    for name in list(to_translate):
        hit = catalogue.resolve(to_translate[name], resolved, field_terms.get(name, ()))
        if hit is not None:
            from_catalogue[name] = hit
            to_translate.pop(name)
    meta.catalogued = sorted(from_catalogue)

    # Drop anything that is pure data once masked -- a calculation bullet is
    # arithmetic with no words in it, so there is nothing a translation could
    # add and one more chance for it to corrupt a figure. Keeps the field
    # exactly as the pipeline wrote it.
    for name in list(to_translate):
        if not protect.has_translatable_prose(to_translate[name], field_terms.get(name, ())):
            to_translate.pop(name)
            meta.data_only.append(name)

    # ── Model budget: PER FIELD, never the whole response ─────────────────────
    # What is left after the catalogue is what a model would actually be asked
    # to translate, so that -- not the response as a whole -- is what the
    # budget applies to.
    #
    # Fields are admitted SMALLEST FIRST. That maximises the number of fields
    # localized, and it means the long legacy blobs (error_details[].explanation
    # is the whole card re-rendered as one string, 2-3 KB each) yield their
    # budget to the short section prose the card is actually drawn from.
    # Anything not admitted keeps its English text; nothing else is affected.
    budget = config.translation_max_chars()
    spent = 0
    for name in sorted(to_translate, key=lambda n: (len(to_translate[n]), n)):
        size = len(to_translate[name])
        # A field carrying a masked option block must stay in the set:
        # payload.reassemble() re-inserts that block from options[] and needs
        # the field present to do it.
        if spent + size > budget and name not in blocks:
            meta.deferred.append(name)
            to_translate.pop(name)
            continue
        spent += size
    if meta.deferred:
        logger.warning(
            "[I18N_OUT] %d field(s) over TRANSLATION_MAX_CHARS=%d kept English: %s",
            len(meta.deferred), budget, sorted(meta.deferred),
        )
    meta.chars_sent = sum(len(v) for v in to_translate.values())

    # Mask every protected entity INSIDE the prose before it is sent: report
    # and return names, IDs, dates, times, numbers, and the markdown that wraps
    # them. They come back as the pipeline's own bytes, so the model cannot
    # alter them -- the same guarantee the option list already has.
    masked: dict[str, str] = {}
    entity_tokens: dict[str, dict[str, str]] = {}
    for name, text in to_translate.items():
        masked[name], entity_tokens[name] = protect.mask_entities(
            text, field_terms.get(name, ()))
    meta.entities_masked = sum(len(t) for t in entity_tokens.values())

    started = time.perf_counter()
    client = translator or get_translator()

    # error_details[] fields are dispatched separately, in BATCHES of whole
    # objects (see _translate_error_batch above); every other field
    # (response_text, llm_summary, ...) keeps the exact per-field path this
    # always had. Both share ONE semaphore, so total in-flight calls across
    # the two paths never exceeds TRANSLATION_CONCURRENCY.
    plain_masked = {n: t for n, t in masked.items() if n not in nested_keys}
    nested_masked = {n: t for n, t in masked.items() if n in nested_keys}
    limit = asyncio.Semaphore(config.translation_concurrency())

    # Deduplicate before dispatching. db_qa responses routinely carry the same
    # string in response_text and db_beautified (db_qa_router.py:762-763), which
    # was costing two identical calls for one piece of text.
    unique: dict[str, list[str]] = {}
    for name, text in plain_masked.items():
        unique.setdefault(text, []).append(name)
    meta.calls = len(unique)

    async def _one(text: str) -> TranslationResult:
        async with limit:
            return await client.translate(text, "en", resolved)

    # Concurrent, not sequential. The fields are independent, so wall-clock
    # is the slowest single call rather than their sum. A response with
    # response_text + llm_summary costs one call's latency, not two.
    # CancelledError propagates, so Stop Generation still works.
    #
    # BOUNDED, though. The translation model is a shared remote proxy that
    # serves requests a few at a time, and the timeout is measured per
    # call from the moment it is issued -- not from the moment the proxy
    # starts working on it. An unbounded fan-out therefore makes the calls
    # at the back of the queue spend their whole budget waiting: a
    # 12-field error card dispatched 11-wide had 4 of its calls return
    # ReadTimeout and fall back to English, while a bounded run of the same
    # card returns everything. Admission is what keeps each call's clock
    # meaningful.
    payloads = list(unique)
    plain_coro = asyncio.gather(*(_one(text) for text in payloads)) if payloads else None

    # Group error_details[] fields by object index (preserving the order
    # _nested_payload produced them in) and chunk into whole-object batches.
    batches: list[list[str]] = []
    if nested_masked:
        by_object: dict[int, list[str]] = {}
        for name in nested_masked:
            match = re.match(rf"{re.escape(_NESTED_ROOT)}\.(\d+)\.", name)
            index = int(match.group(1)) if match else -1
            by_object.setdefault(index, []).append(name)
        object_indices = sorted(by_object)
        batch_size = config.error_explanation_translation_batch_size()
        for start_i in range(0, len(object_indices), batch_size):
            chunk = object_indices[start_i:start_i + batch_size]
            names: list[str] = [n for idx in chunk for n in by_object[idx]]
            if names:
                batches.append(names)

        logger.info(
            "[I18N_OUT] error-explanation lang=%s model=%s errors=%d batch_size=%d "
            "batches=%d",
            resolved, client.name, len(object_indices), batch_size, len(batches),
        )

    translated: dict[str, str] = {}

    async def _one_batch(batch_no: int, names: list[str]) -> None:
        async with limit:
            await _translate_error_batch(
                names, nested_masked, to_translate, entity_tokens, client,
                resolved, meta, translated, batch_no, len(batches),
            )

    batch_coro = (
        asyncio.gather(*(_one_batch(n, b) for n, b in enumerate(batches, 1)))
        if batches else None
    )

    if plain_coro is not None and batch_coro is not None:
        results, _ = await asyncio.gather(plain_coro, batch_coro)
    elif plain_coro is not None:
        results = await plain_coro
    elif batch_coro is not None:
        await batch_coro
        results = []
    else:
        results = []

    meta.calls += len(batches)
    meta.latency_ms = (time.perf_counter() - started) * 1000.0

    for text, tr in zip(payloads, results):
        for name in unique[text]:
            english = to_translate[name]
            if not (tr.ok and tr.text.strip()):
                translated[name] = english
                meta.ok = False
                meta.errors[name] = tr.error or "empty translation"
                continue

            restored, missing = protect.restore_entities(tr.text, entity_tokens[name])
            if missing:
                # The model dropped a protected entity. A sentence with a
                # report name silently missing from it is worse than an
                # untranslated one, so this field stays English.
                logger.warning(
                    "[I18N_OUT] %s: translation lost %d protected entit%s %s "
                    "-- keeping English", name, len(missing),
                    "y" if len(missing) == 1 else "ies",
                    [entity_tokens[name][m] for m in missing],
                )
                translated[name] = english
                meta.ok = False
                meta.errors[name] = f"lost {len(missing)} protected entities"
                meta.entities_lost += len(missing)
                continue

            translated[name] = restored
            meta.fields.append(name)
    meta.translated = bool(meta.fields)

    # Catalogue hits and model output are reassembled together; both still
    # need their option block re-inserted.
    translated.update(from_catalogue)
    meta.translated = meta.translated or bool(from_catalogue)

    # Re-render the option list locally, byte-for-byte from options[].
    rebuilt = payload.reassemble(translated, blocks, passthrough)
    nested_out: dict[str, str] = {}
    for name, value in rebuilt.items():
        if name in nested_keys:
            nested_out[name] = value
        else:
            localized[name] = value
    _inject_nested(localized, nested_out)
    meta.nested_fields = len(nested_out)
    meta.derived = _derive_explanations(localized, english_payload, nested_out, resolved)

    if not meta.ok:
        note = _OUTBOUND_FALLBACK_NOTE.get(resolved, "")
        if note:
            existing = localized.get("status_note") or ""
            localized["status_note"] = f"{existing}\n{note}".strip() if existing else note

    logger.info(
        "[I18N_OUT] lang=en->%s model=%s %.0fms calls=%d catalogued=%s fields=%s "
        "chars=%d/%d options=%d entities=%d lost=%d",
        resolved, meta.model, meta.latency_ms, meta.calls, meta.catalogued,
        meta.fields,
        meta.chars_sent, meta.chars_total, meta.options_count,
        meta.entities_masked, meta.entities_lost,
    )
    return _finalize(localized, result, resolved, meta, english_message, inbound)


def _finalize(
    localized: dict[str, Any],
    original: dict[str, Any],
    lang: str,
    meta: OutboundResult,
    english_message: str | None,
    inbound: InboundResult | None,
) -> dict[str, Any]:
    """Attach i18n metadata under the EXISTING ``data`` field.

    Uses data rather than a new top-level key so ChatResponse keeps its exact
    current shape -- no field added, none renamed. ChatResponse.data is already
    a free-form dict ("generic status/error metadata for frontend").

    data["i18n"]["english"] is what makes the conversation-history decision
    work: the frontend stores these strings and sends them back as history, so
    decide() always sees English context without any extra model call.
    """
    english = {
        name: value
        for name in TRANSLATABLE_FIELDS
        if isinstance((value := original.get(name)), str) and value.strip()
    }
    if english_message is not None:
        english["user_message"] = english_message

    data = dict(localized.get("data") or {})
    data["i18n"] = {
        "lang": lang,
        "rtl": is_rtl(lang),
        "model": meta.model,
        "inbound": inbound.to_dict() if inbound else None,
        "outbound": meta.to_dict(),
        # English source, for the frontend to replay as conversation_history.
        "english": english,
    }
    localized["data"] = data
    return localized
