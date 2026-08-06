"""
Stage 1 — Intent detection.

What kind of question is this, and what does that imply for the prompt?

Rules first, not a model
------------------------
This is a deliberate rules-first classifier, for the same reason the resolver is
deterministic-first: the failure mode this pipeline actually suffers from is an
extra LLM call that silently degrades (the selector model returns 404 on the
configured proxy and falls back to top-1 with no reasoning at all — see §3/§9 of
scratch/sql_generation_context_report.md). A regex that fires on "top 5" is
worth more than a classification call that might not happen.

Every intent here must change something CONCRETE downstream — a rule pack, a
column keep-rule, or which example shape is preferred. Classifications that
change nothing are not worth detecting:

    kind=rank        -> ranking rule pack; the ordered metric survives slicing
    kind=trend       -> RDATE is kept; dates pack; prefer a time-series example
    kind=breakdown   -> the row-label column and its axis literals are kept
    kind=aggregate   -> multipart pack when the table has declared siblings
    kind=compare     -> BOTH sides of a DOM/OVE pair are kept
    kind=movement    -> the movement label column is kept
    needs_total_row  -> the TOTAL row literal is pinned, never budget-dropped
    scope            -> whether a _DOM/_OVE pair is kept whole or narrowed

Matching runs on the ABBREVIATION-EXPANDED query (src.retriever._expand_query),
so "dom"/"ove"/"sec3"/"parta" normalise before any pattern is applied — the same
text the embedding sees.
"""

import re

from src.context.types import (
    INTENT_AGGREGATE,
    INTENT_BREAKDOWN,
    INTENT_COMPARE,
    INTENT_LOOKUP,
    INTENT_MOVEMENT,
    INTENT_RANK,
    INTENT_TREND,
    SCOPE_BOTH,
    SCOPE_DOM,
    SCOPE_OVE,
    Intent,
)

# Rule-pack ids that intent alone can decide. Shape-derived packs (vertical,
# dom_ove, multipart, units, join) are added by the resolver, which is the first
# stage that knows what the committed table actually looks like.
PACK_CORE = "core"
PACK_DATES = "dates"
PACK_RANKING = "ranking"
PACK_TREND = "trend"

_WORD_NUM = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "twenty": 20, "fifty": 50, "hundred": 100,
}
_N = r"(\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|twenty|fifty|hundred)"


def _num(token: str) -> int | None:
    if token is None:
        return None
    return int(token) if token.isdigit() else _WORD_NUM.get(token.lower())


# ── Pattern sets ─────────────────────────────────────────────────────────────
# Each entry is (name, compiled pattern). `name` is recorded on Intent.signals so
# a misclassification is diagnosable from the request log rather than by
# re-running the regexes by hand.

_RANK_RE = [
    ("top_n", re.compile(rf"\b(?:top|highest|largest|biggest|best)\s+{_N}\b", re.I)),
    ("bottom_n", re.compile(rf"\b(?:bottom|lowest|smallest|worst|least)\s+{_N}\b", re.I)),
    ("rank_verb", re.compile(r"\b(rank|ranked|ranking|order(?:ed)?\s+by|sort(?:ed)?\s+by)\b", re.I)),
    ("superlative", re.compile(r"\b(highest|lowest|maximum|minimum|largest|smallest)\b", re.I)),
]

_COMPARE_RE = [
    ("compare_verb", re.compile(r"\b(compare|comparing|comparison|versus|vs\.?|against)\b", re.I)),
    ("side_by_side", re.compile(r"\b(side by side|difference between|gap between)\b", re.I)),
]

_TREND_RE = [
    ("trend_word", re.compile(r"\b(trend|trending|over time|time series|historical|history)\b", re.I)),
    ("period_by_period", re.compile(r"\b(quarter[\s-]on[\s-]quarter|year[\s-]on[\s-]year|"
                                    r"quarter[\s-]by[\s-]quarter|month[\s-]by[\s-]month|"
                                    r"qoq|yoy|growth|change over)\b", re.I)),
    ("multi_period", re.compile(rf"\b(?:last|previous|past|trailing)\s+{_N}\s+"
                                r"(?:quarters?|months?|years?|periods?)\b", re.I)),
]

# Movement/flow vocabulary. This schema has whole tables built on it
# (movement_from, movement_provision_npa, movement_restructure_std_la), and the
# distinguishing feature is that the ROW LABEL is the flow step — so the label
# column must survive slicing even when the question names no literal.
_MOVEMENT_RE = [
    ("movement_word", re.compile(r"\b(movement|opening|closing|addition|additions|"
                                 r"reduction|reductions|slipp(?:ed|age)|upgrad(?:ed|ation)|"
                                 r"recover(?:ed|y|ies)|written[\s-]off|write[\s-]off|"
                                 r"fresh\s+(?:npa|slippage|addition))\b", re.I)),
]

_BREAKDOWN_RE = [
    ("by_dimension", re.compile(r"\b(?:by|per|across|for each|split by|grouped by|"
                                r"broken down by)\s+(?!the\s+(?:latest|last|most)\b)[a-z]", re.I)),
    ("wise", re.compile(r"\b\w+[\s-]wise\b", re.I)),
    ("breakdown_word", re.compile(r"\b(breakdown|break[\s-]up|brkup|distribution|composition)\b", re.I)),
]

_TOTAL_RE = [
    ("total_word", re.compile(r"\b(total|overall|aggregate|grand\s+total|sum|combined|"
                              r"consolidated|gross\s+total)\b", re.I)),
]

_AGGREGATE_RE = [
    ("agg_verb", re.compile(r"\b(sum|sum of|add up|how much|how many|count of|"
                            r"average|avg|mean)\b", re.I)),
]

# Relative/absolute time phrasing. Broader than sql_generator._resolve_relative_time's
# vocabulary ON PURPOSE: the report's finding #4 is that "latest quarter" matched
# nothing there, so no RESOLVED TIME CONTEXT block was emitted and the model had
# to fall back on a general rule unaided. Intent detection catching "latest" means
# the dates rule pack still fires even when there is no concrete range to resolve.
_TIME_RE = [
    ("relative_period", re.compile(r"\b(?:this|current|last|previous|past|trailing)\s+"
                                   r"(?:\d+\s+)?(?:week|month|quarter|year|fy|financial\s+year|"
                                   r"fiscal\s+year|period|reporting\s+period)s?\b", re.I)),
    ("latest", re.compile(r"\b(latest|most\s+recent|newest|as\s+of\s+now|currently)\b", re.I)),
    ("named_period", re.compile(r"\b(q[1-4]|h[12]|fy\s?\d{2,4}|\d{4}[-/]\d{2,4})\b", re.I)),
    ("month_name", re.compile(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)"
                              r"(?:uary|ruary|ch|il|e|y|ust|tember|ober|ember)?\b", re.I)),
    ("year", re.compile(r"\b(?:19|20)\d{2}\b")),
    ("explicit_date", re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b")),
    ("as_at", re.compile(r"\b(as\s+(?:of|at|on)|ending|ended)\b", re.I)),
]

# Scope. Runs on the expanded query, where "dom" is already "domestic" and "ove"
# is already "overseas".
_DOM_RE = re.compile(r"\bdomestic\b", re.I)
_OVE_RE = re.compile(r"\b(overseas|foreign|offshore|abroad)\b", re.I)
_BOTH_RE = re.compile(r"\b(both|combined|domestic\s+and\s+overseas|"
                      r"overseas\s+and\s+domestic|global|worldwide|total)\b", re.I)


def _fired(patterns, text: str) -> list:
    return [name for name, rx in patterns if rx.search(text)]


def _detect_scope(text: str) -> str | None:
    """
    dom / ove / both / None.

    None is NOT the same as `both`: it means the question never mentioned scope,
    so the slicer keeps a DOM/OVE pair whole (dropping one half of a pair the
    user didn't choose between silently changes the answer) but the prompt does
    not claim the user asked to combine them.
    """
    has_dom, has_ove = bool(_DOM_RE.search(text)), bool(_OVE_RE.search(text))
    if has_dom and has_ove:
        return SCOPE_BOTH
    if has_dom:
        return SCOPE_DOM
    if has_ove:
        return SCOPE_OVE
    if _BOTH_RE.search(text):
        return SCOPE_BOTH
    return None


def _detect_top_n(text: str) -> int | None:
    for name, rx in _RANK_RE[:2]:
        m = rx.search(text)
        if m:
            n = _num(m.group(1))
            if n:
                return n
    return None


def detect_intent(query: str, expanded: str | None = None) -> Intent:
    """
    Classify `query`. `expanded` is the abbreviation-expanded form; when omitted
    it is computed here so callers that have it already (the request path always
    does) avoid the duplicate work.

    Precedence is ordered by how strongly the signal constrains SQL SHAPE, not by
    how confident the match is. `rank` outranks everything because "top 5 banks
    by NPA" needs ORDER BY + FETCH FIRST no matter what else it also asks for;
    `lookup` is the floor.
    """
    if expanded is None:
        from src.retriever import _expand_query
        expanded = _expand_query(query)
    text = expanded

    rank_sig = _fired(_RANK_RE, text)
    compare_sig = _fired(_COMPARE_RE, text)
    trend_sig = _fired(_TREND_RE, text)
    movement_sig = _fired(_MOVEMENT_RE, text)
    breakdown_sig = _fired(_BREAKDOWN_RE, text)
    total_sig = _fired(_TOTAL_RE, text)
    agg_sig = _fired(_AGGREGATE_RE, text)
    time_sig = _fired(_TIME_RE, text)

    top_n = _detect_top_n(text)
    # A bare superlative ("highest NPA") is a ranking question with an implied
    # N of 1; an explicit "top 5" carries its own N.
    is_rank = bool(rank_sig) and (top_n is not None or "rank_verb" in rank_sig
                                 or "superlative" in rank_sig)

    if is_rank:
        kind = INTENT_RANK
    elif compare_sig:
        kind = INTENT_COMPARE
    elif trend_sig:
        kind = INTENT_TREND
    elif movement_sig:
        kind = INTENT_MOVEMENT
    elif breakdown_sig:
        kind = INTENT_BREAKDOWN
    elif total_sig or agg_sig:
        kind = INTENT_AGGREGATE
    else:
        kind = INTENT_LOOKUP

    packs = [PACK_CORE]
    if time_sig:
        packs.append(PACK_DATES)
    if kind == INTENT_RANK:
        packs.append(PACK_RANKING)
    if kind == INTENT_TREND:
        packs.append(PACK_TREND)

    signals = tuple(
        f"{group}:{name}"
        for group, names in (
            ("rank", rank_sig), ("compare", compare_sig), ("trend", trend_sig),
            ("movement", movement_sig), ("breakdown", breakdown_sig),
            ("total", total_sig), ("agg", agg_sig), ("time", time_sig),
        )
        for name in names
    )

    return Intent(
        kind=kind,
        needs_time_resolution=bool(time_sig),
        needs_total_row=bool(total_sig),
        # A comparison or a ranking across a dimension needs the label column for
        # the same reason an explicit "by X" does.
        wants_breakdown=bool(breakdown_sig) or kind in (INTENT_RANK, INTENT_COMPARE),
        top_n=top_n if top_n is not None else (1 if kind == INTENT_RANK else None),
        scope=_detect_scope(text),
        rule_packs=tuple(packs),
        signals=signals,
    )
