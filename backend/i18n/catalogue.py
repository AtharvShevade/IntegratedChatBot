"""Pre-translated message catalogue and the resolver that applies it.

The audit found that 141 of the ~190 user-facing string sites in the pipeline
are STATIC literals or f-string TEMPLATES -- deterministic text with values
substituted in. None of it needs a language model, and sending it to one costs
~20s per turn, risks word-sense drift ("Fortnightly" -> "mensuels") and can fail
outright on a proxy timeout.

So: catalogue the English, hand-translate it once, and resolve locally.

    English pipeline  ->  finished English response  ->  resolver  ->  localized
                                                              |
                                                    no match -> runtime LLM

The business logic is untouched. Not one of the 141 call sites gains a message
ID; the pipeline keeps emitting exactly the English it always did, and this
module reverse-matches the finished string. That is what makes the change a
presentation layer rather than a second, parallel flow.

── How matching works ──────────────────────────────────────────────────────

Matching on raw text would be hopeless: every message carries report names,
dates and numbers that differ per call. So both sides are reduced to a
STRUCTURAL KEY first, using the same entity masker the runtime translator uses:

    "Generating instance for 'CIMS_ROR'"   ->  key "Generating instance for '\\x01'"
                                               values ["CIMS_ROR"]
    catalogue en "Generating instance for '{0}'"
                                           ->  key "Generating instance for '\\x01'"

Equal keys, so the French template is selected and the ORIGINAL values are
formatted back into it. The report name never passes through anything but
str.format -- it cannot be altered.

Every protected entity becomes a slot, including ones that look like fixed
words ("XBRL"), which is deliberate: a slot is a guarantee, a translated word
is a hope.

── Guards against a loose match ────────────────────────────────────────────

  * Keys are exact after whitespace normalisation -- no fuzzy matching.
  * Slot count in the target template must equal the number of captured
    values, or the entry is refused and the text falls through to the LLM.
  * Resolution is all-or-nothing per field. A message whose lines resolve only
    partially would render half French and half English, so it is rejected
    whole and handed to the translator instead.
"""
from __future__ import annotations

import json
import logging
import re
from functools import lru_cache
from pathlib import Path

from backend.i18n import protect

logger = logging.getLogger(__name__)

MESSAGES_DIR = Path(__file__).resolve().parent / "messages"

# Stands in for one protected value inside a structural key. A control
# character, so it can never occur in real pipeline text or in a translation.
SLOT = "\x01"

_SLOT_RE = re.compile(r"\{(\d+)\}")
_WS_RE = re.compile(r"[ \t]+")

# "Report Name    : CIMS_ROR" -- a label/value line. The label is prose and is
# catalogued; the value is data and is never touched. Split out separately
# because the alignment padding differs between call sites, which would
# otherwise make every one of them a distinct catalogue entry.
_LABEL_RE = re.compile(r"^([ \t]*)([^:\n]{1,48}?)([ \t]*):([ \t]*)(.*)$")

# "• 31-Mar" / "1. CIMS_ROR" -- list items. The marker is preserved and the
# content resolved on its own.
_BULLET_RE = re.compile(r"^([ \t]*)([•\-\*]|\d{1,3}\.)([ \t]+)(.*)$")


def _normalise(text: str) -> str:
    """Collapse runs of spaces/tabs and strip line-trailing whitespace.

    Column alignment ("Status         :" vs "Status :") differs between call
    sites for the same message; it is presentation, not identity.
    """
    return "\n".join(_WS_RE.sub(" ", line).rstrip() for line in text.split("\n"))


def structure(text: str, extra=()) -> tuple[str, list[str]]:
    """Reduce runtime text to (structural key, ordered protected values).

    ``extra`` names literals the CARD declared as data (the concept labels in a
    section's ``terms``). No regex can recognise an ordinary noun phrase like
    "Weighted average interest rate", so the pipeline has to say which they are.
    """
    masked, tokens = protect.mask_entities(text, extra)
    ordered = [tokens[k] for k in sorted(tokens, key=lambda k: int(re.search(r"\d+", k).group()))]
    # Placeholders appear in the masked text in first-use order; replace each
    # with the same SLOT so the key describes shape only.
    key = re.sub(r"\[\[E\d+\]\]", SLOT, masked)
    # A repeated value shares one placeholder, so expand back to one value per
    # occurrence -- str.format() on the target needs positional parity.
    values: list[str] = []
    for placeholder in re.findall(r"\[\[E(\d+)\]\]", masked):
        values.append(ordered[int(placeholder) - 1])
    return _normalise(key), values


def template_key(template: str) -> tuple[str, int]:
    """Reduce a catalogue template to (structural key, slot count)."""
    slots = [int(n) for n in _SLOT_RE.findall(template)]
    return _normalise(_SLOT_RE.sub(SLOT, template)), len(slots)


@lru_cache(maxsize=None)
def load(lang: str) -> dict[str, str]:
    """Message id -> template, for one language. Cached per process."""
    path = MESSAGES_DIR / f"{lang}.json"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def english_index() -> dict[str, str]:
    """Structural key -> message id, built from en.json.

    A duplicate key means two catalogue entries are indistinguishable once
    their values are masked out; keeping the first would resolve one of them to
    the other's wording, so both are dropped and fall through to the LLM.
    """
    index: dict[str, str] = {}
    duplicates: set[str] = set()
    for message_id, template in load("en").items():
        if message_id.startswith("_"):
            continue  # "_comment" and friends are documentation, not messages
        key, _ = template_key(template)
        if key in index and index[key] != message_id:
            duplicates.add(key)
        index[key] = message_id
    for key in duplicates:
        logger.warning(
            "[I18N_CAT] ambiguous template key removed (matches >1 entry): %r", key
        )
        index.pop(key, None)
    return index


def _apply(message_id: str, values: list[str], lang: str) -> str | None:
    """Format the localized template, or None if it cannot be trusted."""
    template = load(lang).get(message_id)
    if template is None:
        return None
    _, slot_count = template_key(template)
    if slot_count != len(values):
        # A translation that dropped or invented a slot would lose a report
        # name or raise IndexError at the user. Refuse it.
        logger.warning(
            "[I18N_CAT] %s/%s expects %d slots but %d values captured",
            lang, message_id, slot_count, len(values),
        )
        return None
    try:
        return template.format(*values)
    except (IndexError, KeyError) as exc:
        logger.warning("[I18N_CAT] %s/%s format failed: %s", lang, message_id, exc)
        return None


def _resolve_fragment(text: str, lang: str, extra=()) -> str | None:
    """Resolve one line or whole message by exact structural match."""
    if not text.strip():
        return text
    key, values = structure(text, extra)
    message_id = english_index().get(key)
    if message_id is None:
        return None
    return _apply(message_id, values, lang)


def _is_pure_data(text: str, extra=()) -> bool:
    """True when nothing is left but protected values and punctuation.

    Such a fragment -- "CIMS_ROR", "31-Mar-2026", "1. CIMS_ROR" -- has no prose
    to translate and is returned verbatim rather than treated as unresolved.
    """
    if not text.strip():
        return True
    masked, tokens = protect.mask_entities(text, extra)
    if not tokens:
        return False
    residue = re.sub(r"\[\[E\d+\]\]", "", masked)
    return not re.search(r"[^\W\d_]", residue, re.UNICODE)


def _resolve_line(line: str, lang: str, extra=()) -> str | None:
    """Resolve a single line, trying progressively looser structures."""
    if not line.strip() or _is_pure_data(line, extra):
        return line

    direct = _resolve_fragment(line, lang, extra)
    if direct is not None:
        return direct

    # "Label : value" -- translate the label, leave the value alone.
    label_match = _LABEL_RE.match(line)
    if label_match:
        indent, label, pad, gap, value = label_match.groups()
        localized_label = _resolve_fragment(label.strip(), lang, extra)
        if localized_label is not None:
            if _is_pure_data(value, extra):
                localized_value: str | None = value
            else:
                localized_value = _resolve_fragment(value, lang, extra)
            if localized_value is not None:
                return f"{indent}{localized_label}{pad}:{gap}{localized_value}"

    # "• content" / "1. content" -- keep the marker, resolve the content.
    bullet_match = _BULLET_RE.match(line)
    if bullet_match:
        indent, marker, gap, content = bullet_match.groups()
        if _is_pure_data(content, extra):
            return line
        localized = _resolve_fragment(content, lang, extra)
        if localized is not None:
            return f"{indent}{marker}{gap}{localized}"

    return None


def resolve(text: str, lang: str, extra=()) -> str | None:
    """Localize a finished English message from the catalogue.

    Returns None when the message is not fully covered, so the caller falls
    through to the runtime translator. All-or-nothing: a partial resolution
    would render half in each language.
    """
    if not text or not text.strip() or lang == "en":
        return None
    if not load(lang):
        return None

    whole = _resolve_fragment(text, lang, extra)
    if whole is not None:
        return whole

    lines = text.split("\n")
    if len(lines) == 1:
        return _resolve_line(text, lang, extra)

    out: list[str] = []
    for line in lines:
        localized = _resolve_line(line, lang, extra)
        if localized is None:
            return None
        out.append(localized)
    return "\n".join(out)


def stats() -> dict[str, object]:
    """Catalogue size and coverage, for logging and tests."""
    english = load("en")
    return {
        "entries": len(english),
        "indexed": len(english_index()),
        "languages": {
            lang: len(load(lang)) for lang in ("en", "fr", "ar", "hi")
        },
    }
