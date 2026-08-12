# backend/tools/message_cleaner.py — quote-aware normalisation of validator
# business messages, and safe extraction of operand labels from them.
#
# The messages in the real corpus follow several authoring conventions and
# routinely contain nested, unbalanced quotes plus free text carrying the same
# characters the formula uses:
#
#   '▼ "en:Identity "Total Term Loans Sanctioned > Total Term Loans Disbursed" do not tally."'
#   '▼ "en:Identity " Closing balance of provisions held ( = Opening balance … .)" do not tally. "'
#   '▼ "en:Identity "Total NPA - Closing Balance" or "Total - Closing Balance" ( = Opening …)" do not tally."'
#   '▼ "en:Validation not satisfied: Complaints pending … = Pendency for less than 1 month + …"'
#   '▼ "en:Reporting of " \'Dates for Half Month" is mandatory."'
#   '▼ "en:Identity "1. Agriculture and Allied Activites &gt;= Piority Sector …(a+b=i+ii) " do not tally."'
#
# Prefix/suffix stripping with str.strip('"') plus a "$ do not tally" anchor —
# what this module replaces — fails on every one of the awkward examples above
# and leaks fragments like 'Loss for the previous year.)" do not tally.' into
# what is then displayed to the user as a concept name.
#
# Two guarantees this module provides instead:
#   1. Entities are unescaped BEFORE any operator scanning, so '&gt;=' is seen
#      as '>=' and never split as '&gt' + '='.
#   2. An operand split is only ever RETURNED when its arity matches the number
#      of variables the parsed formula actually has on that side. A message we
#      cannot split confidently yields None, and the caller falls back to a
#      taxonomy label — it never yields a half-parsed fragment.

from __future__ import annotations

import html as _html
import re

__all__ = [
    "normalise_message", "extract_quoted_core", "split_operands",
    "looks_like_label",
]

# Leading wrappers, stripped structurally and repeatedly (a message can carry
# several: '▼ " en : Identity " …'). These are validator/framework scaffolding,
# not business text — none of them names a concept, a rule, or a return.
_LEADING_WRAPPERS = (
    re.compile(r"^\s*[▼▶►•\-–—]+\s*"),
    re.compile(r"^\s*[\"'`]+\s*"),
    re.compile(r"^\s*[a-z]{2}\s*:\s*", re.IGNORECASE),          # 'en:' language tag
    re.compile(r"^\s*Identity\b\s*", re.IGNORECASE),
    re.compile(r"^\s*Validation\s+not\s+satisfied\s*:\s*", re.IGNORECASE),
    re.compile(r"^\s*Validation\s+failed\s*:\s*", re.IGNORECASE),
    re.compile(r"^\s*Reporting\s+of\b\s*", re.IGNORECASE),
    re.compile(r"^\s*Value\s+of\b\s*", re.IGNORECASE),
    re.compile(r"^\s*Error\s*:\s*", re.IGNORECASE),
)

# Trailing verdict clauses. Anchored to allow arbitrary trailing quote/space/
# punctuation debris after them — the exact debris that defeated the previous
# '\s*do not tally\.?"?\s*$' anchor on 'do not tally. "'.
_TRAILING_CLAUSES = (
    re.compile(r"[\s\"'`]*\bdo(?:es)?\s+not\s+tally\b\s*\.?\s*[\"'`]*\s*$", re.IGNORECASE),
    re.compile(r"[\s\"'`]*\bis\s+mandatory\b\s*\.?\s*[\"'`]*\s*$", re.IGNORECASE),
    re.compile(r"[\s\"'`]*\bshould\s+not\s+be\s+(?:blank|empty)\b\s*\.?\s*[\"'`]*\s*$", re.IGNORECASE),
    re.compile(r"[\s\"'`]*\bdoes\s+not\s+match\b\s*\.?\s*[\"'`]*\s*$", re.IGNORECASE),
)

_NBSP = " "


def _unescape(text: str) -> str:
    return _html.unescape(text or "").replace(_NBSP, " ")


def normalise_message(message: str) -> str:
    """Unescape, collapse whitespace, and strip framework scaffolding from both
    ends. Structural only — no rule, concept, or return text is matched by
    name, so this behaves identically for a message it has never seen."""
    text = _unescape(message)
    text = re.sub(r"\s+", " ", text).strip()

    # Repeat until stable: wrappers nest ('▼ "en:Identity "').
    for _ in range(8):
        before = text
        for pattern in _LEADING_WRAPPERS:
            text = pattern.sub("", text, count=1)
        for pattern in _TRAILING_CLAUSES:
            text = pattern.sub("", text, count=1)
        text = text.strip()
        if text == before:
            break

    return text.strip().strip("\"'` ").strip()


def _balanced_quote_spans(text: str) -> list[tuple[int, int]]:
    """Spans between paired double quotes, outermost pairs first, scanning
    left to right. Unpaired quotes are ignored rather than treated as
    delimiters — that is what keeps 'Total NPA" or "Total" (' from being read
    as a delimiter pair straddling unrelated text."""
    spans: list[tuple[int, int]] = []
    open_at: int | None = None
    for i, ch in enumerate(text):
        if ch not in ('"', "“", "”"):
            continue
        if open_at is None:
            open_at = i
        else:
            spans.append((open_at + 1, i))
            open_at = None
    return spans


def extract_quoted_core(message: str, operator: str = "") -> str | None:
    """Candidate rule-statement spans carved out of a quoted message.

    Quote nesting in these messages is genuinely ambiguous — 'Identity "A > B"
    do not tally.' pairs its quotes such that a strict left-to-right pairing
    lands on 'en:Identity ' and ' do not tally.' rather than on 'A > B'. So
    rather than trusting one pairing, this returns the widest span (first
    quote to last quote), which always contains the statement; the caller
    normalises it and, if that fails, falls back to the whole message.

    Returns None when the message carries no quotes at all, which is the
    correct answer for the 'Validation not satisfied: …' convention where the
    statement is unquoted and normalise_message already exposes it.
    """
    text = _unescape(message)
    positions = [i for i, ch in enumerate(text) if ch in ('"', "“", "”")]
    if len(positions) < 2:
        return None
    span = text[positions[0] + 1:positions[-1]].strip()
    if operator and operator not in span:
        # The widest span lost the operator (unusual, but possible when the
        # statement itself is unquoted) — prefer a balanced span that keeps it.
        for a, b in _balanced_quote_spans(text):
            candidate = text[a:b].strip()
            if operator in candidate:
                return candidate
    return span or None


# A usable operand label: has letters, isn't pure punctuation, and does not
# still carry validator scaffolding. This is the gate that stops
# 'Loss for the previous year.)" do not tally.' from ever being used as a name.
_SCAFFOLD_TOKENS = re.compile(
    r"\b(do(?:es)? not tally|is mandatory|identity|validation not satisfied|en\s*:)\b",
    re.IGNORECASE,
)


def looks_like_label(text: str) -> bool:
    candidate = (text or "").strip()
    if len(candidate) < 2 or len(candidate) > 200:
        return False
    if not re.search(r"[A-Za-z]", candidate):
        return False
    if _SCAFFOLD_TOKENS.search(candidate):
        return False
    # Unbalanced brackets mean we cut through the middle of a phrase.
    if candidate.count("(") != candidate.count(")"):
        return False
    # A business label never contains a double quote. When one survives, the
    # message nested quoted alternatives ('"Total NPA" or "Total"') and the
    # split landed across them — reject and let the taxonomy name it instead.
    if '"' in candidate or "“" in candidate or "”" in candidate:
        return False
    return True


def _split_on_operator(text: str, operator: str, max_depth: int = 0) -> tuple[str, str] | None:
    """Split once on *operator* at parenthesis depth <= *max_depth*.

    max_depth=0 (the default) keeps '…Activities(a+b=i+ii)' from being split
    on its internal '=' — a real message in the corpus.

    max_depth=1 is the retry for the equally real 'X ( = A + B - C)' authoring
    convention, where the statement's own operator sits inside a parenthetical
    gloss. _rebalance() then repairs the orphaned bracket on each side.
    """
    depth = 0
    i, n, oplen = 0, len(text), len(operator)
    while i < n:
        ch = text[i]
        if ch == "(":
            depth += 1
            i += 1
            continue
        if ch == ")":
            depth = max(0, depth - 1)
            i += 1
            continue
        if depth <= max_depth and text.startswith(operator, i):
            # Don't match '>' inside '>=' (or '<' inside '<='), and don't match
            # '=' that is the tail of '>=' / '<=' / '!=' / '<>'.
            if oplen == 1 and i + 1 < n and text[i + 1] == "=":
                i += 1
                continue
            if oplen == 1 and operator == "=" and i > 0 and text[i - 1] in "><!":
                i += 1
                continue
            return text[:i], text[i + oplen:]
        i += 1
    return None


def _rebalance(fragment: str) -> str:
    """Repair a fragment whose brackets were orphaned by a depth-1 split.

    An unmatched trailing '(' means the split cut into a parenthetical gloss —
    everything from that bracket on is scaffolding, so it is dropped. An
    unmatched leading/trailing ')' is simply removed. Anything still
    unbalanced afterwards is left as-is and will be rejected by
    looks_like_label, rather than being trimmed until it happens to look
    plausible.
    """
    text = (fragment or "").strip()

    # Drop from the last unmatched '(' onward.
    depth = 0
    cut = None
    for i, ch in enumerate(text):
        if ch == "(":
            if depth == 0:
                cut = i
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth <= 0:
                depth = 0
                cut = None
    if depth > 0 and cut is not None:
        text = text[:cut]

    # Drop unmatched ')' characters.
    if text.count(")") > text.count("("):
        out, extra = [], text.count(")") - text.count("(")
        for ch in reversed(text):
            if ch == ")" and extra > 0:
                extra -= 1
                continue
            out.append(ch)
        text = "".join(reversed(out))

    return text.strip().strip(" .,;:-–—").strip()


def split_operands(
    message: str,
    operator: str,
    lhs_arity: int,
    rhs_terms: list[tuple[str, int]] | None,
) -> tuple[str | None, list[str] | None]:
    """Recover per-side operand labels from a business message.

    *rhs_terms* is the (variable, sign) list the parsed formula produced for
    the right-hand side; its length is the arity the message must match.

    Returns (lhs_label, rhs_labels). Either element is None when this message
    cannot be split into that side confidently. Nothing partial is ever
    returned: an rhs whose term count disagrees with the formula's is rejected
    wholesale rather than assigning the leftover text to the last variable —
    the specific failure that produced
    'Loss for the previous year.)" do not tally.' as a concept name.
    """
    if not message or not operator:
        return None, None

    # Try the quoted core first, then the whole normalised message. Both are
    # normalised the same way; whichever yields a usable split wins, and
    # neither is trusted enough to suppress the other.
    core = extract_quoted_core(message, operator)
    candidates = [normalise_message(core)] if core else []
    whole = normalise_message(message)
    if whole and whole not in candidates:
        candidates.append(whole)

    best: tuple[str | None, list[str] | None] = (None, None)
    for text in candidates:
        if not text:
            continue
        for max_depth in (0, 1):
            parts = _split_on_operator(text, operator, max_depth=max_depth)
            if not parts:
                continue
            lhs_label, rhs_labels = _labels_from_parts(parts, lhs_arity, rhs_terms,
                                                       rebalance=max_depth > 0)
            # Prefer a split that resolved both sides; keep a half-split only
            # if nothing better turns up.
            if lhs_label and rhs_labels:
                return lhs_label, rhs_labels
            if (lhs_label or rhs_labels) and not any(best):
                best = (lhs_label, rhs_labels)

    if best[1] is None:
        # Some messages state the relation in prose rather than with the
        # formula's operator symbol ("Assets should be sum of (A + B + …)").
        # The bracketed component list is still unambiguous, so it is used for
        # the right-hand side — under the same arity-and-sign gate — while the
        # left-hand side is left to the other label sources.
        for text in candidates:
            components = _components_from_bracketed_list(text, rhs_terms)
            if components:
                return best[0], components

    return best


def _components_from_bracketed_list(
    text: str, rhs_terms: list[tuple[str, int]] | None,
) -> list[str] | None:
    """Per-term labels from the LAST balanced parenthesised group in *text*,
    accepted only when its term count and sign pattern match the formula's
    right-hand side exactly."""
    signs = [s for _v, s in (rhs_terms or [])]
    if len(signs) < 2 or not text:
        return None

    start = end = -1
    depth = 0
    for i, ch in enumerate(text):
        if ch == "(":
            if depth == 0:
                start = i
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                end = i
    if start < 0 or end <= start:
        return None

    pieces = _split_signed_terms(text[start + 1:end].strip(), signs)
    if pieces and all(looks_like_label(p) for p in pieces):
        return pieces
    return None


def _labels_from_parts(
    parts: tuple[str, str],
    lhs_arity: int,
    rhs_terms: list[tuple[str, int]] | None,
    rebalance: bool,
) -> tuple[str | None, list[str] | None]:
    lhs_raw, rhs_raw = (p.strip(" \t-–—") for p in parts)
    if rebalance:
        lhs_raw, rhs_raw = _rebalance(lhs_raw), _rebalance(rhs_raw)

    lhs_label: str | None = lhs_raw.strip().strip("\"'` ").strip()
    if lhs_arity != 1 or not looks_like_label(lhs_label):
        lhs_label = None

    rhs_labels: list[str] | None = None
    expected = len(rhs_terms or [])
    if expected == 1:
        candidate = rhs_raw.strip().strip("\"'` ").strip()
        rhs_labels = [candidate] if looks_like_label(candidate) else None
    elif expected > 1:
        signs = [s for _v, s in (rhs_terms or [])]
        pieces = _split_signed_terms(rhs_raw, signs)
        if pieces and all(looks_like_label(p) for p in pieces):
            rhs_labels = pieces

    return lhs_label, rhs_labels


def split_aggregated_terms(
    message: str, operator: str, expected_count: int,
) -> list[str] | None:
    """For a one-variable aggregate side — 'sum($V2)' bound to N facts — the
    message often still enumerates the N components by name
    ('… = Pendency for less than 1 month + Pendency for 1-3 months + …').

    Returns those N labels only when the count matches exactly, so each
    reported fact can be named instead of showing N identical concept names.
    Returns None otherwise; the caller then labels the facts by their context
    rather than guessing.
    """
    if not message or not operator or expected_count < 2:
        return None

    core = extract_quoted_core(message, operator)
    for text in ([normalise_message(core)] if core else []) + [normalise_message(message)]:
        if not text:
            continue
        for max_depth in (0, 1):
            parts = _split_on_operator(text, operator, max_depth=max_depth)
            if not parts:
                continue
            rhs = _rebalance(parts[1]) if max_depth else parts[1]
            pieces = _split_signed_terms(rhs, [1] * expected_count)
            if pieces and all(looks_like_label(p) for p in pieces):
                return pieces
    return None


_TERM_SPLIT_RE = re.compile(r"\s([+\-−])\s")


def _split_signed_terms(text: str, expected_signs: list[int]) -> list[str] | None:
    """Split 'A + B - C' into its terms and require both the count AND the
    sign pattern to match what the formula says. Matching signs as well as
    count is what prevents a message that happens to contain the right number
    of '+' separators from being accepted for a formula that actually
    subtracts one of its terms."""
    if len(expected_signs) < 2:
        return None

    # Only split at depth 0 so '(a+b=i+ii)' stays intact.
    pieces: list[str] = []
    signs: list[int] = [1]
    depth = 0
    current = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if depth == 0 and i > 0 and i + 1 < n and text[i - 1] == " " and text[i + 1] == " " and ch in "+-−":
            pieces.append("".join(current).strip())
            signs.append(1 if ch == "+" else -1)
            current = []
            i += 2
            continue
        current.append(ch)
        i += 1
    pieces.append("".join(current).strip())

    if len(pieces) != len(expected_signs):
        return None
    if signs != expected_signs:
        return None
    cleaned = [p.strip().strip("\"'` ").strip() for p in pieces]
    return cleaned if all(cleaned) else None
