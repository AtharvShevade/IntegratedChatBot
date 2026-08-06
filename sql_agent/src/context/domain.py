"""
Stage 3 — Domain detection: which slice of the catalog may answer this question.

Why this is a PRE-filter
------------------------
The pre-context pipeline had an explicit-section signal but applied it as a
POST-filter: `src.retriever.get_relevant_schema` computed a full global ranking
over every table, then re-ordered it so a named section's table jumped to rank 0
(src/retriever.py, "Applied last so it outranks even the QA strong-match tier").

That works at 26 tables, where the correct table is almost always somewhere in
the shortlist to be promoted. It stops working at multi-return scale: with 500+
tables the section's table can fall outside `top_k * 3` before the section
signal is ever consulted, and a post-filter cannot promote what was never
retrieved. So the gate must narrow the candidate space BEFORE the channels
search it.

The emptiness rule
------------------
A gate that would eliminate every candidate is dropped, not honoured. An
unfiltered search is always better than a search over nothing, and inferred
signals (periodicity wording, return names) are exactly the kind that
mis-fire — "quarterly" in a question about a monthly return should cost nothing.
Explicit references narrow; inference only ever narrows when something survives.

What this reuses
----------------
`src.section_alias.detect_section_reference` already resolves "Section 12 Misc
T4" against real table names, with its own cached index and its own
disambiguation scoring. This module does not reimplement any of that — it
converts that result into a DomainGate and adds the two axes section_alias does
not cover (part A/B, and periodicity/return).
"""

import logging
import re

from src import schema_store
from src.context.types import (
    GATE_EXPLICIT,
    GATE_INFERRED,
    GATE_NONE,
    DomainGate,
)
from src.section_alias import detect_section_reference

log = logging.getLogger("context.domain")

# Periodicity is encoded in the table-name prefix throughout this schema
# (cims_raq_q_ / _m_ / _a_) and repeated in schema.json's return_name
# ("CIMS_RAQ(Quarterly)"), so it is derivable without a hand-maintained map.
_PERIODICITY_PREFIXES = {
    "quarterly": ("_q_",),
    "monthly": ("_m_",),
    "annual": ("_a_",),
}
_PERIODICITY_RE = {
    "quarterly": re.compile(r"\b(quarterly|per\s+quarter|each\s+quarter)\b", re.I),
    "monthly": re.compile(r"\b(monthly|per\s+month|each\s+month)\b", re.I),
    "annual": re.compile(r"\b(annual|annually|yearly|per\s+year|each\s+year)\b", re.I),
}

# "part A" / "part B" — matched on the expanded query, where "parta" has already
# become "part A" (src.retriever._QUERY_EXPANSIONS).
_PART_RE = re.compile(r"\bpart\s*([a-d])\b", re.I)
_PART_TABLE_RE = re.compile(r"_part_?([a-d])(?:_|$)", re.I)


def _tables_matching(names, predicate) -> set:
    return {n.lower() for n in names if predicate(n.lower())}


def detect_parts(query: str) -> frozenset:
    """{'a', 'b', ...} for every part letter the question names."""
    return frozenset(m.group(1).lower() for m in _PART_RE.finditer(query))


def detect_periodicity(query: str) -> frozenset:
    """{'quarterly', ...} — usually empty, and empty is the common, correct case."""
    return frozenset(
        name for name, rx in _PERIODICITY_RE.items() if rx.search(query)
    )


def explicit_pin(query: str, schema_path: str | None = None) -> tuple:
    """
    (table, reason) when the question names a section that resolves to exactly
    ONE table, else (None, "").

    This is the hardest routing signal available — the user named the table — and
    it is kept separate from the gate on purpose. The gate restricts the search
    SPACE to that section; the pin says which table wins inside it. Collapsing
    the two would mean a question that names a section but needs a sibling table
    (a real case: "Section 1" spans parts A, B and C) could never reach it.
    """
    ref = detect_section_reference(query, schema_path)
    if ref and ref.get("resolved"):
        return ref["resolved"], f"explicit section {ref['section_number']} reference"
    return None, ""


def build_gate(query: str, expanded: str | None = None,
               schema_path: str | None = None) -> DomainGate:
    """
    Narrow the catalog to the tables that may answer `query`.

    Layers apply in order of how hard the signal is, each intersecting with what
    survived so far, and each SKIPPED if it would empty the set:

      1. section  (explicit — the user wrote "Section 9")
      2. part     (explicit — "part B")
      3. periodicity (inferred — "quarterly")

    Returns a gate whose `table_allow` is empty when nothing narrowed, which
    every consumer must read as "no constraint".
    """
    if expanded is None:
        from src.retriever import _expand_query
        expanded = _expand_query(query)

    all_names = schema_store.all_table_names(schema_path)
    if not all_names:
        return DomainGate(note="empty catalog")

    allow = {n.lower() for n in all_names}
    sections: set = set()
    parts: set = set()
    returns: set = set()
    source = GATE_NONE
    notes = []

    # ── 1. explicit section reference ────────────────────────────────────────
    ref = detect_section_reference(query, schema_path)
    if ref and ref.get("candidates"):
        candidates = {t.lower() for t in ref["candidates"]}
        narrowed = allow & candidates
        if narrowed:
            allow = narrowed
            sections.add(str(ref["section_number"]))
            source = GATE_EXPLICIT
            notes.append(f"section {ref['section_number']} -> {len(allow)} table(s)")
        else:
            notes.append(f"section {ref['section_number']} matched no live table - ignored")

    # ── 2. explicit part reference ───────────────────────────────────────────
    wanted_parts = detect_parts(expanded)
    if wanted_parts:
        def _is_part(name):
            m = _PART_TABLE_RE.search(name)
            return bool(m) and m.group(1).lower() in wanted_parts

        narrowed = _tables_matching(allow, _is_part)
        if narrowed:
            allow = narrowed
            parts |= wanted_parts
            source = GATE_EXPLICIT
            notes.append(f"part {'/'.join(sorted(wanted_parts))} -> {len(allow)} table(s)")
        else:
            # Common and harmless: many sections have no part split at all, and
            # the question's "part A" refers to a row label rather than a table.
            notes.append(f"part {'/'.join(sorted(wanted_parts))} matched no table - ignored")

    # ── 3. inferred periodicity ──────────────────────────────────────────────
    wanted_periods = detect_periodicity(expanded)
    if wanted_periods:
        prefixes = tuple(
            p for name in wanted_periods for p in _PERIODICITY_PREFIXES.get(name, ())
        )
        if prefixes:
            narrowed = _tables_matching(allow, lambda n: any(p in n for p in prefixes))
            # Inference only ever narrows when something survives. A single-scope
            # build (today: quarterly only) will routinely see "monthly" in a
            # question and must not filter itself down to nothing.
            if narrowed and len(narrowed) < len(allow):
                allow = narrowed
                returns |= wanted_periods
                if source == GATE_NONE:
                    source = GATE_INFERRED
                notes.append(f"periodicity {'/'.join(sorted(wanted_periods))} -> {len(allow)} table(s)")
            elif not narrowed:
                notes.append(f"periodicity {'/'.join(sorted(wanted_periods))} matched no table - ignored")

    # Nothing narrowed => no gate. Signalled by an EMPTY table_allow rather than
    # by an allow-set containing the whole catalog, so a consumer can cheaply
    # distinguish "unconstrained" from "constrained to everything".
    if len(allow) == len(all_names):
        return DomainGate(source=GATE_NONE, note="; ".join(notes))

    gate = DomainGate(
        returns=frozenset(returns),
        sections=frozenset(sections),
        parts=frozenset(parts),
        table_allow=frozenset(allow),
        source=source,
        note="; ".join(notes),
    )
    log.info("domain gate (%s): %d/%d tables — %s",
             gate.source, len(allow), len(all_names), gate.note)
    return gate
