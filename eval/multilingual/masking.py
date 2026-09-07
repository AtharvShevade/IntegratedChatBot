"""Entity / number preservation checking -- the hard gate of this evaluation.

A translation that reads beautifully but renames ``CIMS_RAQ(Monthly)`` or turns
``1,234.50`` into ``1.234,50`` produces a confidently wrong regulatory answer.
No fluency score redeems that, so metrics 5-8 are scored here as pass/fail on
exact token preservation rather than as a similarity percentage.

Digit shapes are the subtle case. Gemma may render numbers in Arabic-Indic
(٠١٢٣) for Arabic or Devanagari (०१२३) for Hindi. For the *preservation*
verdict those are normalised to ASCII before comparison -- the value is intact,
so failing it would be a false positive. But the shape change is recorded
separately as a warning, because the production system round-trips numbers into
prompts and comparisons that assume ASCII.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field

# Digit families we expect from the target languages, mapped to ASCII.
_DIGIT_MAPS = {
    "arabic-indic": dict(zip("٠١٢٣٤٥٦٧٨٩", "0123456789")),
    "eastern-arabic-indic": dict(zip("۰۱۲۳۴۵۶۷۸۹", "0123456789")),
    "devanagari": dict(zip("०१२३४५६७८९", "0123456789")),
}
_ALL_DIGIT_MAP = {k: v for m in _DIGIT_MAPS.values() for k, v in m.items()}

# A "numeric token" is any run of digits with optional grouping/decimal marks
# and an optional trailing percent. Currency symbols are captured separately so
# that "₹1,200" and "1,200" are distinguishable.
_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)*%?")
_CURRENCY_RE = re.compile(r"[₹$€£¥]|\b(?:INR|USD|EUR|GBP|Cr|Lakh|Lakhs)\b")

# Dates in the formats the app actually emits (dd-mm-yyyy, dd/mm/yyyy,
# yyyy-mm-dd). Checked as whole tokens so a reordered date is caught even
# though its digit multiset is unchanged.
_DATE_RE = re.compile(
    r"\b(?:\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2})\b"
)

# GUIDs and instance IDs.
_GUID_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)

# Identifier-shaped tokens: uppercase codes, underscored names, alphanumeric
# report codes. This is the net that catches report/return/form names and XBRL
# concepts without needing them all enumerated up front.
_CODE_RE = re.compile(r"\b(?=[A-Za-z0-9_]*[A-Z])(?=[A-Za-z0-9_]*\d|[A-Z_]{3,})[A-Za-z0-9_]{2,}\b")


def normalize_digits(text: str) -> tuple[str, set[str]]:
    """Fold non-ASCII digit shapes to ASCII. Returns (text, families_found)."""
    families: set[str] = set()
    if not text:
        return text, families
    out = []
    for ch in text:
        mapped = _ALL_DIGIT_MAP.get(ch)
        if mapped is None:
            out.append(ch)
            continue
        for family, table in _DIGIT_MAPS.items():
            if ch in table:
                families.add(family)
                break
        out.append(mapped)
    return "".join(out), families


def _canonical(text: str) -> str:
    """NFKC so that full-width and compatibility forms compare equal."""
    return unicodedata.normalize("NFKC", text or "")


def numeric_tokens(text: str) -> Counter:
    """Multiset of numeric tokens, digit-shape normalised."""
    folded, _ = normalize_digits(_canonical(text))
    return Counter(_NUMBER_RE.findall(folded))


def currency_tokens(text: str) -> Counter:
    return Counter(_CURRENCY_RE.findall(_canonical(text)))


def date_tokens(text: str) -> Counter:
    folded, _ = normalize_digits(_canonical(text))
    return Counter(_DATE_RE.findall(folded))


def guid_tokens(text: str) -> Counter:
    return Counter(g.lower() for g in _GUID_RE.findall(_canonical(text)))


def code_tokens(text: str) -> Counter:
    """Identifier-shaped tokens (report codes, form names, XBRL concepts)."""
    return Counter(_CODE_RE.findall(_canonical(text)))


_lexicon_re_cache: dict[str, re.Pattern] = {}


def _entity_re(entity: str) -> re.Pattern:
    """Word-bounded matcher for one entity.

    Plain ``str.count`` over-counts badly here: three-letter return codes like
    ROP, LOU and CEM occur inside ordinary words, so a substring match would
    report entities that were never there and then "lose" them on the localised
    side. Boundaries are asserted only where the adjacent character is
    word-forming, so names containing punctuation -- ``CIMS_RAQ(Monthly)``,
    ``Form IX`` -- still match.
    """
    cached = _lexicon_re_cache.get(entity)
    if cached is None:
        left = r"\b" if entity[:1].isalnum() or entity[:1] == "_" else ""
        right = r"\b" if entity[-1:].isalnum() or entity[-1:] == "_" else ""
        cached = re.compile(f"{left}{re.escape(entity)}{right}")
        _lexicon_re_cache[entity] = cached
    return cached


def lexicon_hits(text: str, lexicon: set[str]) -> Counter:
    """Occurrences of known do-not-translate entities, matched case-sensitively
    because ``FormA`` and ``FORMA`` are different things in the repo."""
    canon = _canonical(text)
    hits: Counter = Counter()
    for entity in lexicon:
        if not entity:
            continue
        n = len(_entity_re(entity).findall(canon))
        if n:
            hits[entity] = n
    return hits


@dataclass
class Violation:
    kind: str          # number | currency | date | guid | code | entity
    expected: str
    actual: str
    detail: str

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "expected": self.expected,
            "actual": self.actual,
            "detail": self.detail,
        }


@dataclass
class PreservationReport:
    """Result of comparing the English pipeline output against the localised
    output. ``passed`` is the hard gate; ``hallucinations`` is metric 8."""

    passed: bool = True
    violations: list[Violation] = field(default_factory=list)
    hallucinations: list[Violation] = field(default_factory=list)
    digit_shape_warnings: set[str] = field(default_factory=set)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "violations": [v.to_dict() for v in self.violations],
            "hallucinations": [h.to_dict() for h in self.hallucinations],
            "digit_shape_warnings": sorted(self.digit_shape_warnings),
            "violation_count": len(self.violations),
            "hallucination_count": len(self.hallucinations),
        }


def _diff(kind: str, src: Counter, dst: Counter) -> tuple[list[Violation], list[Violation]]:
    """(dropped-or-altered, introduced) between two token multisets."""
    lost = src - dst
    gained = dst - src
    violations = [
        Violation(kind, token, "<missing>", f"present {count}x in English output, missing from localised output")
        for token, count in sorted(lost.items())
    ]
    halluc = [
        Violation(kind, "<absent>", token, f"appears {count}x in localised output but not in English source")
        for token, count in sorted(gained.items())
    ]
    return violations, halluc


def check_preservation(
    english: str,
    localized: str,
    lexicon: set[str] | None = None,
) -> PreservationReport:
    """Compare an English pipeline output with its localised counterpart.

    Metrics 5, 6, 7 (preservation) become ``report.violations``; metric 8
    (hallucination) becomes ``report.hallucinations``. Both are exact multiset
    comparisons -- deliberately strict, because the failure mode we are hunting
    is a silently altered figure, not a clumsy phrase.
    """
    report = PreservationReport()
    if english is None or localized is None:
        return report

    _, families = normalize_digits(_canonical(localized))
    report.digit_shape_warnings |= families

    checks = [
        ("number", numeric_tokens),
        ("currency", currency_tokens),
        ("date", date_tokens),
        ("guid", guid_tokens),
        ("code", code_tokens),
    ]
    for kind, extract in checks:
        violations, halluc = _diff(kind, extract(english), extract(localized))
        report.violations.extend(violations)
        report.hallucinations.extend(halluc)

    if lexicon:
        violations, _ = _diff("entity", lexicon_hits(english, lexicon), lexicon_hits(localized, lexicon))
        report.violations.extend(violations)

    report.passed = not report.violations
    return report


def load_lexicon(path) -> set[str]:
    """Do-not-translate entities from dataset/entities.json.

    Underscore-prefixed keys are metadata, not entities: ``_note`` is a string
    (iterating it would add every individual character as an "entity") and
    ``_excluded_ambiguous`` holds the names deliberately kept OUT of the
    lexicon. Only list-valued, non-underscore keys are real categories.
    """
    import json

    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    out: set[str] = set()
    for key, values in data.items():
        if key.startswith("_") or not isinstance(values, list):
            continue
        out.update(v for v in values if isinstance(v, str) and v)
    return out
