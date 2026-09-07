"""Structural protection for regulatory entities INSIDE translated prose.

payload.py protects the option LIST: a rendered block is masked out whole and
re-rendered from options[]. That covers disambiguation, but not the far more
common case -- an identifier, a date or a number sitting inside a sentence:

    "Please enter the reporting date for **CIMS_ROR**."
    "Enter the report name, ReturnId, or short name (e.g. CIMS_FormGPB, R009):"
    "Generating instance for 'CIMS_ROR'\\nReporting Date : 31-Mar-2026"

Until this module existed those tokens were protected only by rule 2 of the
translation prompt -- an instruction the model is asked to follow, not a
guarantee. A model that renders CIMS_ROR as "CIMS_RVR", turns 31-Mar-2026 into
31-mars-2026, or transliterates R009 into Arabic digits produces a confidently
wrong regulatory instruction, and nothing downstream would notice.

So: mask every protected token to a placeholder, translate the prose around it,
then restore the ORIGINAL bytes. The identifier the user sees is the pipeline's
own string; the model never handled it and therefore cannot have altered it.

    "date for **CIMS_ROR**."  ->  "date for [[E1]]."
                             ->  "date pour [[E1]]."          (model)
                             ->  "date pour **CIMS_ROR**."    (restored)

If a placeholder does not come back, restore() reports it and the caller keeps
the ENGLISH text for that field. A vanished report name is worse than an
untranslated sentence.
"""
from __future__ import annotations

import re

# Placeholder shape mirrors payload.OPTIONS_PLACEHOLDER: bracketed, upper-case,
# no spaces -- it reads as structure rather than prose, so a translator is
# unlikely to render it into the target language.
_PLACEHOLDER = "[[E{n}]]"

# Tolerate a model that alters the marker's punctuation, spacing or case but
# keeps the token, e.g. "[ E1 ]" or "[[e1]]".
_RESTORE_RE = re.compile(r"\[{1,2}\s*E(\d+)\s*\]{1,2}", re.IGNORECASE)

# Domain field names the patterns below cannot catch: no digit, no underscore,
# not all-caps. They are labels the .NET app and the repository XML use, so a
# translated "ReturnId" would leave the user hunting for a field that does not
# exist in the UI they are looking at. Listed longest-first.
_GLOSSARY = (
    "Request ID", "ReturnId", "InstanceId", "RequestId", "FormId",
    "Instance ID", "Form ID", "Return ID",
)

# Order matters: alternation is leftmost-first, so the more specific patterns
# must come first or a shorter one will claim part of a longer token.
_PATTERNS = (
    # Exact domain terms, before anything generic can split them.
    "|".join(re.escape(term) for term in _GLOSSARY),
    # Markdown-emphasised identifier -- keeps the ** ** so the bold survives
    # exactly as the pipeline wrote it: **CIMS_ROR**
    r"\*\*[A-Za-z0-9_()./\-]*[\d_(][A-Za-z0-9_()./\-]*\*\*",
    # Request IDs: UUID and bare 32-hex (see guided.py _INSTANCE_ID_RE)
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
    r"\b[0-9a-fA-F]{32}\b",
    # Dates, in every shape the pipeline emits. 31-Mar-2026 must not become
    # 31-mars-2026: the .NET API parses this string back.
    #
    # ISO datetime first, as ONE token: agent/__init__.py:1493 emits
    # "Scheduled : 2026-12-12T17:00:00". Split across the date and time
    # patterns it masked as "[[E1]]T[[E2]]", leaving the bare "T" separator
    # exposed to the model to translate, drop or space out.
    r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2})?\b",
    r"\b\d{1,2}-[A-Za-z]{3}-\d{4}\b",
    r"\b\d{1,2}-[A-Za-z]{3}\b",
    r"\b\d{1,2}-\d{1,2}-\d{4}\b",
    r"\b\d{4}-\d{2}-\d{2}\b",
    r"\b\d{1,2}:\d{2}(?::\d{2})?\b",
    # Report / return / form identifiers: a word containing a digit,
    # underscore or parenthesis. CIMS_ROR, CIMS_RAQ(Monthly), DBR01, R009,
    # FMRD09_FTD. Requires the digit/underscore/paren so it can never match an
    # ordinary English, French, Arabic or Hindi word.
    #
    # Split into two alternatives so parentheses are only consumed when they
    # BELONG to the name:
    #
    #   1. balanced form -- CIMS_RAQ(Monthly), RAQ(Quarterly)
    #   2. plain form    -- CIMS_ROR, DBR01, R009
    #
    # A single pattern ending on [A-Za-z0-9)] got "R009)" out of the prose
    # "(e.g. CIMS_FormGPB, R009):", protecting a closing parenthesis that is
    # part of the sentence, not of the identifier. The balanced alternative
    # must be tried first or the plain one claims the stem and leaves "(Monthly)"
    # exposed.
    r"\b[A-Za-z][A-Za-z0-9_./\-]*\([A-Za-z0-9_./\- ]+\)",
    r"\b(?=[A-Za-z0-9_./\-]*[\d_])[A-Za-z][A-Za-z0-9_./\-]*[A-Za-z0-9]",
    # XBRL concept / element names, which are CamelCase and carry no digit or
    # underscore, so the rule above misses them entirely:
    # TotalOfAverageCashReserves, FormGPB, DeferredTaxAssets.
    #
    # Requires TWO humps -- an initial capitalised chunk followed by at least
    # one more capital. That is what separates an identifier from an ordinary
    # capitalised word: "Where", "Difference" and "Concept" have one hump and
    # are correctly left alone, so section headings still translate.
    # Hyphens and dots may JOIN humps, so a formula rule name stays one token:
    # TermDeposit-WeightedAverageInterestRateByClassificationOfTermDeposits,
    # LR-PartA1B1B2AndC-MismatchAsPercentageToOutflows. Split at the hyphen it
    # would mask as two entities, and the template that carries it could then
    # only match rule names with exactly that many hyphens.
    r"\b[A-Z][a-zA-Z0-9]*(?:[-.][A-Z0-9][a-zA-Z0-9]*)+\b",
    r"\b[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]*)+\b",
    # Bare acronyms: RAQ, XBRL, SQL, ROR. Report short names carry no digit,
    # so the rule above misses them.
    r"\b[A-Z]{2,16}\b",
    # Numbers, amounts, percentages. Protected mainly for digit SHAPE: an
    # Arabic-Indic ٣١ would break every downstream parse.
    r"\b\d[\d,]*(?:\.\d+)?%?\b",
)

_MASK_RE = re.compile("|".join(f"(?:{p})" for p in _PATTERNS))


# How a card joins a list of concept labels (formula_error.py:_join).
_TERM_JOINERS = (", and ", ", ", " and ")


def _extra_pattern(extra) -> str | None:
    """One alternation matching a RUN of the given literals, or a single one.

    ``extra`` is the concept labels the card itself published for a section
    (``terms``). They are ordinary English noun phrases -- "Weighted average
    interest rate", "Amount outstanding term deposit 2" -- so no regex can
    recognise them; the pipeline has to say which they are, and it does.

    A RUN is matched as ONE token on purpose. The fix sentence embeds a
    variable-length list:

        "Check X and the values it is calculated from (A, B, C) in the source
         data -- the reported value does not match ..."

    Masking A, B and C separately would make the structural key depend on how
    many operands the rule happens to have, so a catalogue template could only
    ever match one arity. Masked as a single token the sentence has the same
    shape for every rule, and one template covers them all.

    Longest-first, so a label that is a prefix of another cannot claim it.
    """
    literals = {t.strip() for t in (extra or ()) if t and t.strip()}

    # The card lists indexed labels ("Amount outstanding term deposit 1" ..
    # "... 6") but the rule sentence names the family once, unnumbered:
    # "using each Amount outstanding term deposit as its weight". Protect the
    # stem too, or that concept name is the one thing in the sentence a
    # translation would rewrite.
    #
    # Guarded at three words so this can only ever add a genuine concept
    # phrase. A one-word stem ("Difference 1" -> "Difference") would match
    # ordinary prose -- including catalogue headings, which would then look
    # like pure data and silently stop being translated.
    for term in list(literals):
        stem = re.sub(r"\s+\d+$", "", term).strip()
        if stem != term and len(stem.split()) >= 3:
            literals.add(stem)

    literals = sorted(literals, key=len, reverse=True)
    if not literals:
        return None
    one = "|".join(re.escape(t) for t in literals)
    joiner = "|".join(re.escape(j) for j in _TERM_JOINERS)
    return f"(?:{one})(?:(?:{joiner})(?:{one}))*"


def mask_entities(text: str, extra=()) -> tuple[str, dict[str, str]]:
    """Replace protected tokens with placeholders.

    Returns ``(masked_text, tokens)`` where ``tokens`` maps placeholder ->
    original text. Identical tokens share one placeholder, which keeps the
    prompt short and the substitution consistent.

    ``extra`` adds literal strings to protect ahead of the patterns -- the
    concept labels a card carries in ``terms``. They are data under the same
    rule as a report name: the user must be able to find "Weighted average
    interest rate" in the application, and a translated label sends them
    looking for a field that does not exist.

    Single-pass: the replacement is built by scanning the ORIGINAL string, so a
    placeholder can never itself be re-matched and masked again.
    """
    if not text or not text.strip():
        return text, {}

    tokens: dict[str, str] = {}
    seen: dict[str, str] = {}

    def _swap(match: re.Match) -> str:
        original = match.group(0)
        if original in seen:
            return seen[original]
        placeholder = _PLACEHOLDER.format(n=len(tokens) + 1)
        tokens[placeholder] = original
        seen[original] = placeholder
        return placeholder

    pattern = _MASK_RE
    extra_pattern = _extra_pattern(extra)
    if extra_pattern:
        # Extra literals come FIRST in the alternation: a label such as
        # "Weighted average interest rate 1" ends in a digit, which the
        # identifier pattern would otherwise split off on its own.
        pattern = re.compile(f"(?:{extra_pattern})|{_MASK_RE.pattern}")
    return pattern.sub(_swap, text), tokens


def restore_entities(translated: str, tokens: dict[str, str]) -> tuple[str, list[str]]:
    """Put the original tokens back.

    Returns ``(restored_text, missing)``. ``missing`` lists any placeholder the
    model dropped; a non-empty list means the translation LOST a protected
    entity and the caller must fall back to English rather than show a
    sentence with a report name silently missing from it.
    """
    if not tokens:
        return translated, []
    if not translated:
        return translated, sorted(tokens)

    by_index = {
        int(re.search(r"\d+", key).group()): value  # type: ignore[union-attr]
        for key, value in tokens.items()
    }
    found: set[int] = set()

    def _swap(match: re.Match) -> str:
        index = int(match.group(1))
        if index in by_index:
            found.add(index)
            return by_index[index]
        return match.group(0)

    restored = _RESTORE_RE.sub(_swap, translated)
    missing = sorted(
        placeholder
        for placeholder, _ in tokens.items()
        if int(re.search(r"\d+", placeholder).group()) not in found  # type: ignore[union-attr]
    )
    return restored, missing


def has_translatable_prose(text: str, extra=()) -> bool:
    """True if anything is left to translate once protected tokens are masked.

    A formula error's calculation bullet is arithmetic and nothing else:

        "(₹356,802,987,000 × 0.06 + ₹2,297,563,000 × 0.05) ÷ (₹356,802,987,000 ...)"
        "₹-495,956,792,000 ÷ ₹17,775,625,211,000 = -0.0279009478"

    Every token in those is a protected amount, so masking leaves only
    operators and brackets. Sending one to the model spends a call and a
    timeout to be handed back a string it must not have altered -- and gives it
    an opportunity to alter one anyway.

    The test is EXACT, not a ratio: a string is skipped only when masking
    leaves NO LETTER AT ALL. A sentence that merely contains many figures still
    has words between them and is translated normally. (A ratio threshold was
    tried first and rejected: two validator messages of the same kind scored
    0.27 and 0.94, so no cut-off separated them. Requiring a two-letter word
    was rejected too -- it silently skipped one-letter prose.)
    """
    if not text or not text.strip():
        return False
    masked, _ = mask_entities(text, extra)
    residue = re.sub(r"\[\[E\d+\]\]", " ", masked)
    return bool(re.search(r"[^\W\d_]", residue, re.UNICODE))


def protected_tokens(text: str) -> list[str]:
    """Every token mask_entities() would protect. For tests and diagnostics."""
    return _MASK_RE.findall(text) and [m.group(0) for m in _MASK_RE.finditer(text)] or []
