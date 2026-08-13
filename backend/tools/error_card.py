"""Shared "error card" presentation schema — ONE generic view for both formula
and dimension validation errors.

WHY THIS EXISTS
───────────────
Formula and dimension errors were each rendered as their own 7-8 section wall of
text, in two different vocabularies ("Reported Values / Comparison / Where to
Check" vs "Details This Figure Must Carry / What Each Detail Must Contain /
Details Actually Provided") — for what is structurally the SAME statement:

    here is what was expected, here is what you gave, here is the gap.

Both are an expected-vs-actual comparison. A formula error compares numbers; a
dimension error compares a required set of details against the supplied set.
Once that is seen, both fit one table and one reading order, so a user who
learns to read one error has learned to read all of them.

THE CARD — four visible slots and one drawer
────────────────────────────────────────────
    headline   What broke?  Names the actual thing, not the category.
    locator    Where in my data do I go?
    rule       What was supposed to be true?  One plain sentence.
    matrix     Expected vs. what I gave, row by row, with a per-row status.
    fix        What do I do now?
    details    Everything else, collapsed. Nothing is deleted — only re-tiered.

The old v1 sections are NOT deleted: they are nested inside the `details`
drawer, so every fact the previous layout showed is still one click away. This
is a re-tiering of the same information, not a reduction of it.

REVERTING
─────────
Set ERROR_CARD_V2=0 in the environment and both error types fall straight back
to their original build_sections()/sections_to_text() output with no code
change. See doc/ERROR_CARD_V2.md.

SECTION KINDS
─────────────
    {"kind": "headline", "text": str}
    {"kind": "locator",  "heading": str, "items": [{"label", "value", "mono"?}]}
    {"kind": "rule",     "heading": str, "text": str, "mono"?: bool}
    {"kind": "matrix",   "heading": str, "columns": {"label", "expected", "actual"},
                         "rows": [{"label", "expected", "actual", "status",
                                   "note"?, "emphasis"?}]}
    {"kind": "fix",      "heading": str, "steps": [str, ...]}
    {"kind": "details",  "heading": str, "sections": [ ...v1 sections... ]}

`rule` is deliberately the SAME kind name the v1 schema already uses, so the
existing frontend case renders it unchanged.

Row status vocabulary (drives the ✅/❌ affordance in the UI):
    "ok"       this row is fine
    "bad"      this row is why the error was raised
    "unknown"  could not be established from the available evidence
    "neutral"  informational — no verdict applies to this row on its own
"""
from __future__ import annotations

import os
import re

# ═════════════════════════════════════════════════════════════════════════════
# Feature flag
# ═════════════════════════════════════════════════════════════════════════════

# Default ON — the v2 card is the point of the change. Flipping this to "0"
# restores the previous layout for BOTH error types without touching code, so
# the rollout is reversible in production by an env edit and a restart.
_V2_DEFAULT = "1"


def v2_enabled() -> bool:
    """Whether to emit the unified error card instead of the legacy sections.

    Read at CALL time rather than import time so tests (and an operator editing
    .env between restarts) can flip it without reimporting the module.
    """
    return os.getenv("ERROR_CARD_V2", _V2_DEFAULT).strip().lower() in ("1", "true", "yes", "on")


# ═════════════════════════════════════════════════════════════════════════════
# Section constructors
#
# Thin by design: a builder should not have to remember key names, and a typo
# in one becomes a missing section in the UI rather than an exception.
# ═════════════════════════════════════════════════════════════════════════════

STATUS_OK = "ok"
STATUS_BAD = "bad"
STATUS_UNKNOWN = "unknown"
STATUS_NEUTRAL = "neutral"


def headline(text: str) -> dict:
    return {"kind": "headline", "text": text}


def locator(items: list[dict], heading: str = "Where") -> dict:
    """The 'where do I go in my data' slot. Items are label/value pairs; set
    mono=True on an item whose value is a raw identifier."""
    return {"kind": "locator", "heading": heading, "items": items}


def rule(text: str, heading: str = "Rule", mono: bool = False) -> dict:
    return {"kind": "rule", "heading": heading, "text": text, "mono": mono}


def matrix(rows: list[dict], heading: str, *,
           label_col: str, expected_col: str, actual_col: str) -> dict:
    """The expected-vs-actual table — the heart of the card.

    Column HEADERS are passed in rather than fixed, because the right wording
    differs by error type ("Detail / Expected / You provided" for dimensions,
    "Item / Expected / You reported" for formulas) even though the structure
    is identical.
    """
    return {
        "kind": "matrix",
        "heading": heading,
        "columns": {"label": label_col, "expected": expected_col, "actual": actual_col},
        "rows": rows,
    }


def row(label: str, expected: str, actual: str, status: str,
        note: str = "", emphasis: bool = False) -> dict:
    entry = {"label": label, "expected": expected, "actual": actual, "status": status}
    if note:
        entry["note"] = note
    if emphasis:
        # Renders with a rule above it — used for a formula's result row, which
        # is the consequence of the rows above rather than a peer of them.
        entry["emphasis"] = True
    return entry


def fix(steps: list[str], heading: str = "Fix") -> dict:
    return {"kind": "fix", "heading": heading, "steps": [s for s in steps if s]}


# ── Emphasis inside prose ────────────────────────────────────────────────────
#
# Concept labels in this domain are long and contain digits, commas, dots and
# parentheses — "5. Other Non-food Credit, if any, please specify", "III.
# Non-Food Credit ( 1 to 5)". Dropped into a sentence they are indistinguishable
# from the sentence's own wording, so
#
#   5. Other Non-food Credit, if any, please specify must be less than III.
#   Non-Food Credit ( 1 to 5)
#
# reads as one undifferentiated run and the reader cannot see where a label ends
# and the RULE begins.
#
# Rather than wrap the labels in markup (which would leak into the plain-text
# form and into every non-HTML consumer), a section may carry the exact
# substrings to highlight. The renderer finds and styles them; the text itself
# is unchanged, so sections_to_text() output is byte-identical either way.
#
#   "terms" — concept/axis labels          -> rendered bold
#   "ops"   — the relation being asserted  -> rendered in the accent colour
#
# With the labels bold, the relation word falls out naturally as the connective
# between them, which is exactly the distinction the reader needs.

# Relational wording the card itself composes, beyond the operator meanings the
# formula AST supplies. Longest forms first is handled by _dedup_longest_first.
RELATION_PHRASES: tuple[str, ...] = (
    "is exactly equal to", "exactly equal to",
    "higher than", "lower than", "over by", "short by",
    "are missing from this figure", "is missing from this figure",
    "not provided", "not established", "not reported",
    "is not one of the allowed options", "not one of the allowed options",
    "is not written in the required format", "not written in the required format",
    "does not belong to it", "not required for this figure",
)


def _dedup_longest_first(values) -> list[str]:
    """Unique, non-trivial, longest-first.

    Longest-first is load-bearing: the renderer builds one alternation out of
    these, and a regex alternation matches the FIRST branch that succeeds. With
    "equal to" ahead of "greater than or equal to", the longer phrase would
    never match as a whole.
    """
    seen: set[str] = set()
    out: list[str] = []
    for value in values or ():
        text = (value or "").strip()
        # Single characters and empty strings would match everywhere.
        if len(text) < 2 or text.lower() in seen:
            continue
        seen.add(text.lower())
        out.append(text)
    out.sort(key=len, reverse=True)
    return out


def attach_emphasis(section: dict, terms=(), ops=()) -> dict:
    """Attach highlight hints to a prose-bearing section, in place.

    Absent keys mean "highlight nothing", so this is safe to skip and safe to
    call with empty input — the renderer treats a section without them exactly
    as it did before.
    """
    cleaned_terms = _dedup_longest_first(terms)
    cleaned_ops = _dedup_longest_first(ops)
    if cleaned_terms:
        section["terms"] = cleaned_terms
    if cleaned_ops:
        section["ops"] = cleaned_ops
    return section


def details(sections: list[dict], heading: str = "Technical details") -> dict:
    """The collapsed drawer holding the full legacy sections.

    Returns None-equivalent (an empty dict is never emitted) when there is
    nothing to put in it — callers should skip a falsy return.
    """
    kept = [s for s in sections if s]
    if not kept:
        return {}
    return {"kind": "details", "heading": heading, "sections": kept}


# ═════════════════════════════════════════════════════════════════════════════
# Context id decoding
# ═════════════════════════════════════════════════════════════════════════════

# Context ids in this corpus are '_'-joined: a period marker followed by every
# dimension member's value, e.g.
#     fromto_20240101_20240331_221826_VishnuGarden
#     asof_20260630_OtherMember
_PERIOD_RE = re.compile(
    r"^(?P<kind>asof|fromto)_(?P<first>\d{8})(?:_(?P<second>\d{8}))?",
    re.IGNORECASE,
)

_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _pretty_date(yyyymmdd: str) -> str:
    """'20240101' -> '1 Jan 2024'. Returns "" for anything that isn't a real
    date, so a malformed segment is dropped rather than shown wrong."""
    try:
        year, month, day = int(yyyymmdd[:4]), int(yyyymmdd[4:6]), int(yyyymmdd[6:8])
    except (ValueError, IndexError):
        return ""
    if not (1 <= month <= 12 and 1 <= day <= 31 and 1900 <= year <= 2999):
        return ""
    return f"{day} {_MONTHS[month - 1]} {year}"


def period_from_context(context_id: str) -> str:
    """The human-readable PERIOD carried by a context id, or "".

    DELIBERATELY decodes only the period. The remaining '_' segments are
    dimension values, and which axis each belongs to cannot be recovered from
    the id — dimension_error._diagnose_typed_content documents two measured
    cases where the trailing segment belongs to a different axis entirely.
    Naming them here would be a confident falsehood; the verified axis/value
    pairs come from the instance document instead (observed_dimensions).
    """
    match = _PERIOD_RE.match((context_id or "").strip())
    if not match:
        return ""
    first = _pretty_date(match.group("first"))
    if not first:
        return ""
    second = _pretty_date(match.group("second") or "")
    if match.group("kind").lower() == "fromto" and second:
        return f"{first} – {second}"
    if match.group("kind").lower() == "asof":
        return f"as at {first}"
    return first


# ═════════════════════════════════════════════════════════════════════════════
# Plain-text serialisation
#
# One serialiser for both error types, handling v2 kinds AND the v1 kinds that
# survive inside the details drawer — so the text form can never drift from
# what the UI shows.
# ═════════════════════════════════════════════════════════════════════════════

_STATUS_GLYPH = {
    STATUS_OK: "OK  ",
    STATUS_BAD: "->  ",
    STATUS_UNKNOWN: "?   ",
    STATUS_NEUTRAL: "    ",
}


def _matrix_lines(section: dict, indent: str = "") -> list[str]:
    """The table as fixed-width text. Column widths are computed from the
    content so nothing is truncated and nothing is padded to an arbitrary
    guess."""
    columns = section.get("columns") or {}
    rows = section.get("rows") or []
    if not rows:
        return []

    head_label = columns.get("label", "Item")
    head_expected = columns.get("expected", "Expected")
    head_actual = columns.get("actual", "Actual")

    w_label = max([len(head_label)] + [len(str(r.get("label", ""))) for r in rows])
    w_expected = max([len(head_expected)] + [len(str(r.get("expected", ""))) for r in rows])

    lines = [
        f"{indent}    {head_label.ljust(w_label)}  {head_expected.ljust(w_expected)}  {head_actual}",
        f"{indent}    {'-' * (w_label + w_expected + len(head_actual) + 4)}",
    ]
    for entry in rows:
        if entry.get("emphasis"):
            lines.append(f"{indent}    {'-' * (w_label + w_expected + len(head_actual) + 4)}")
        glyph = _STATUS_GLYPH.get(entry.get("status", STATUS_NEUTRAL), "    ")
        line = (f"{indent}{glyph}{str(entry.get('label', '')).ljust(w_label)}  "
                f"{str(entry.get('expected', '')).ljust(w_expected)}  "
                f"{entry.get('actual', '')}")
        if entry.get("note"):
            line += f"  ({entry['note']})"
        lines.append(line.rstrip())
    return lines


def _section_lines(section: dict, indent: str = "") -> list[str]:
    """Text for ONE section, v1 kind or v2 kind. Unknown kinds yield nothing
    rather than raising — a future kind renders as absent, not as a crash."""
    kind = section.get("kind")

    if kind == "headline":
        return [f"{indent}[X] {section.get('text', '')}", ""]

    if kind == "locator":
        lines = [f"{indent}{section.get('heading', 'Where')}"]
        for item in section.get("items") or []:
            label = item.get("label", "")
            lines.append(f"{indent}  - {label}: {item.get('value', '')}" if label
                         else f"{indent}  - {item.get('value', '')}")
        lines.append("")
        return lines

    if kind == "rule":
        return [f"{indent}{section.get('heading', 'Rule')}",
                f"{indent}  {section.get('text', '')}", ""]

    if kind == "matrix":
        heading = section.get("heading", "")
        lines = [f"{indent}{heading}"] if heading else []
        lines += _matrix_lines(section, indent)
        lines.append("")
        return lines

    if kind == "fix":
        lines = [f"{indent}{section.get('heading', 'Fix')}"]
        lines += [f"{indent}  - {s}" for s in section.get("steps") or []]
        lines.append("")
        return lines

    if kind == "details":
        lines = [f"{indent}{section.get('heading', 'Technical details')}"]
        for nested in section.get("sections") or []:
            lines += _section_lines(nested, indent + "  ")
        return lines

    # ── v1 kinds, reached only from inside the details drawer ────────────────
    if kind == "values":
        lines = [f"{indent}{section.get('heading', '')}"]
        for item in section.get("items") or []:
            label = item.get("label", "")
            line = (f"{indent}  - {label}: {item.get('value', '')}" if label
                    else f"{indent}  - {item.get('value', '')}")
            if item.get("note"):
                line += f" ({item['note']})"
            lines.append(line)
            if item.get("context"):
                lines.append(f"{indent}      context: {item['context']}")
        lines.append("")
        return lines

    if kind == "points":
        lines = [f"{indent}{section.get('heading', '')}"]
        lines += [f"{indent}  - {b}" for b in section.get("bullets") or []]
        lines.append("")
        return lines

    if kind == "note":
        return [f"{indent}{section.get('text', '')}", ""]

    return []


def sections_to_text(title: str, sections: list[dict]) -> str:
    """Serialise a whole card. *title* is the already-composed header line
    (icon + error type + subject) — this module does not decide it, because
    the two error types word it differently."""
    lines: list[str] = [title, ""]
    for section in sections:
        lines += _section_lines(section)
    return "\n".join(lines).rstrip()
