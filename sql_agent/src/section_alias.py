"""
Detects an explicit section/table reference in the user's question — e.g.
"Section 10", "Section 12 Misc T4" — and resolves it against the real table
names in schema.json, with no hand-maintained alias file.

Why this exists: a batch of 11 real question/SQL pairs showed 5 failures (45%)
where the question named a section explicitly and the pipeline still picked a
different, unrelated table whose COLUMNS happened to resemble the question's
wording more than the section name did (embedding retrieval has no lexical
short-circuit for an explicit, unambiguous reference). Every table name in this
schema carries an extractable section number (`cims_raq_q_sec10` -> 10,
`cims_raq_q_sec_12_misc_t4` -> 12 + sub-id "t4"), so this is a deterministic
pre-filter, not a guess.

This mirrors the existing QA strong-match mechanism in src/retriever.py (a
near-duplicate prior question pins its table to rank 0) — same idea, a
different, even harder signal: an explicit section reference beats a fuzzy
text match.

Known simplification: if a question mentions more than one distinct section
number, only the first is used. None of the traced failures needed more than
one, and a genuine cross-section question is rare enough to not special-case
yet — revisit if it shows up in practice.
"""

import os
import re

from src import config

# "section 10", "section10", "sec 10", "sec_10", "sec10" — case-insensitive.
# \b after \d+ stops "section 1" from swallowing "12"/"10" etc when the actual
# text is "section 12"; \d+ is greedy so it captures the full number first.
_SECTION_QUERY_RE = re.compile(r"\bsec(?:tion)?s?[\s_-]*(\d+)\b", re.IGNORECASE)

# Table-name-side: matches the "sec10", "sec_12" prefix immediately after the
# common "cims_raq_q_" return prefix (stripped separately, see _strip_prefix).
_SECTION_TABLE_RE = re.compile(r"^sec_?(\d+)")

# Splits a run-together "part" + single letter ("parta" -> "part a") so it
# tokenizes the same way "part_a" would. Deliberately does NOT split "t2"/"t3"/
# "t4" style sub-ids (letter+digit) — those are meaningful as one token (the
# established "Misc T4" naming), unlike "part<letter>".
_PART_LETTER_RE = re.compile(r"\bpart([a-d])\b")

_cache: dict = {}


def _strip_prefix(table_lower: str) -> str:
    """Remove the common return prefix so section-number extraction only looks
    at the part of the name that varies per table."""
    for prefix in ("cims_raq_q_", "cims_raq_m_", "cims_raq_a_"):
        if table_lower.startswith(prefix):
            return table_lower[len(prefix):]
    return table_lower


def _suffix_tokens(remainder: str) -> list:
    """
    Turn whatever's left of a table name after the section number into
    independent, whole-word tokens usable for disambiguation — e.g.
    "_sensec_parta" -> ["sensec", "part", "a"], "_misc_t4" -> ["misc", "t4"].
    """
    text = remainder.strip("_")
    if not text:
        return []
    text = text.replace("_", " ")
    text = _PART_LETTER_RE.sub(r"part \1", text)
    return [t for t in text.split() if t]


def _build_section_index(schema_path: str | None = None) -> dict:
    """
    {"by_number": {10: [{"table": "...", "suffix_tokens": [...]}, ...], ...}}

    Cached for the process lifetime, keyed by schema_path — same convention as
    the FAISS index caches elsewhere in this codebase: a schema rebuild needs a
    process restart to be picked up, it does not silently serve stale data
    forever, it just isn't hot-reloaded.
    """
    if schema_path is None:
        schema_path = os.path.join(config.EMBEDDING_DIR, "schema.json")

    if schema_path in _cache:
        return _cache[schema_path]

    import json
    by_number: dict = {}
    try:
        with open(schema_path, encoding="utf-8") as f:
            schema = json.load(f)
    except FileNotFoundError:
        _cache[schema_path] = {"by_number": {}}
        return _cache[schema_path]

    for entry in schema:
        if entry.get("is_backup"):
            continue
        table = entry.get("table") or entry.get("table_name")
        if not table:
            continue
        remainder = _strip_prefix(table.lower())
        m = _SECTION_TABLE_RE.match(remainder)
        if not m:
            continue  # no section-number pattern in this table name — not indexed
        number = int(m.group(1))
        suffix = remainder[m.end():]
        by_number.setdefault(number, []).append({
            "table": table,
            "suffix_tokens": _suffix_tokens(suffix),
        })

    _cache[schema_path] = {"by_number": by_number}
    return _cache[schema_path]


def clear_cache():
    """Drop the cached section index (call after a schema rebuild + restart is
    inconvenient to test without) — same affordance the FAISS caches have."""
    _cache.clear()


def detect_section_reference(query: str, schema_path: str | None = None):
    """
    Look for an explicit section reference in `query` and resolve it against
    the real tables in schema.json.

    Returns None if no section number is mentioned, or if one is mentioned but
    schema.json has no table with that number (nothing to act on either way).

    Otherwise returns:
        {
            "section_number": int,
            "candidates": [table_name, ...],   # every table sharing that number
            "resolved": table_name or None,     # set when exactly one table
                                                 # survives disambiguation
        }

    Resolution logic:
      1. Extract the section number from the query (first mention only).
      2. Gather every table sharing that number from schema.json.
      3. If exactly one — resolved immediately, no further checks needed
         (this is what fires for "Section 10", which only ever has one table).
      4. If more than one (e.g. "Section 12" spans 4 sub-tables), score each
         candidate by how many of ITS OWN distinguishing suffix tokens
         ("misc", "t4", "part", "a", ...) appear as whole words anywhere in the
         query, and keep only the candidate(s) achieving the maximum score.
         A genuine tie (including 0-0, meaning no candidate's suffix words
         appear at all) leaves multiple candidates and `resolved=None` — the
         question was honestly ambiguous ("Section 12" alone can't tell misc
         from misc_t4), and the caller should narrow retrieval to just the
         candidate set rather than guess.
    """
    m = _SECTION_QUERY_RE.search(query)
    if not m:
        return None
    number = int(m.group(1))

    index = _build_section_index(schema_path)
    candidates = index["by_number"].get(number)
    if not candidates:
        return None  # section mentioned, but no table in this build has it

    if len(candidates) == 1:
        table = candidates[0]["table"]
        return {"section_number": number, "candidates": [table], "resolved": table}

    lowered_query = query.lower()
    scored = []
    for c in candidates:
        score = sum(
            1 for tok in c["suffix_tokens"]
            if re.search(rf"\b{re.escape(tok)}\b", lowered_query)
        )
        scored.append((score, c["table"]))

    max_score = max(s for s, _ in scored)
    survivors = [t for s, t in scored if s == max_score]
    # max_score == 0 means no candidate's suffix words matched anything — every
    # candidate "survives" by that measure, which is really just the original
    # unresolved set; only treat it as a real narrowing when max_score > 0.
    if max_score > 0 and len(survivors) == 1:
        return {"section_number": number, "candidates": [c["table"] for c in candidates],
                "resolved": survivors[0]}
    if max_score > 0 and len(survivors) < len(candidates):
        # Narrowed, but not to exactly one — still ambiguous, but a smaller set.
        return {"section_number": number, "candidates": survivors, "resolved": None}

    return {"section_number": number, "candidates": [c["table"] for c in candidates],
            "resolved": None}
