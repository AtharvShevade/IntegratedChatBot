"""
Runtime access to the XBRL-derived business semantic layer.

Reads `concept_map.json` from config.EMBEDDING_DIR — the artifact produced by
embedding_building/cims_raq_quarterly/build_concept_map.py out of the taxonomy
export in data/. That builder's docstring explains what was kept and dropped;
this module is the read side and adds nothing the artifact does not contain.

What this layer answers that schema.json cannot
-----------------------------------------------
schema.json describes the DB: column names, types, and a short header string
lifted from the source spreadsheet. It has no notion of what a number MEANS. So
four facts that change whether generated SQL is correct had no source at all:

  1. The reporting UNIT. The taxonomy declares unit_multiplier=100000 (Rs lakh)
     for 187 concepts. Any question phrased "in crore" was previously answered
     with the raw stored number.
  2. Stock vs flow (period_type instant/duration). Summing a point-in-time
     balance across RDATE is always wrong; summing a period flow may be right.
  3. The deterministic ROW SELECTOR. CODE is a per-table line-item code, not the
     reporting entity (proved in scripts/phase0_xbrl_reconcile.py: CODE 1000 <->
     '1. Transport and adjoining Infrastructure'). The taxonomy gives the exact
     CODE per business concept, which is a far more robust filter than
     string-matching a whitespace-sensitive row label.
  4. Derivation. 180 mapped concepts participate in a formula, so a metric with
     no column of its own can be computed instead of guessed at.

Everything here degrades to empty. A missing or unbuildable concept_map.json
makes every function return nothing, and callers render no business-semantics
block — the pipeline behaves exactly as it did before this layer existed.
"""
import json
import logging
import os
import re

import src.config as config

log = logging.getLogger("concept_map")

# Cache keyed by resolved path so a scope switch (different EMBEDDING_DIR) gets
# its own entry instead of serving another return's map. Mirrors the index cache
# in src/retriever.py.
_cache: dict = {}

# Generic words that carry no discriminating power when matching a question
# against a concept label. Deliberately shorter than retriever._STOPWORDS: this
# is matching against LABELS, not whole questions, so verbs like "show"/"give"
# never appear on the label side anyway.
_STOP = {
    "a", "an", "the", "of", "for", "to", "in", "on", "and", "or", "at", "as",
    "is", "are", "by", "from", "with", "during", "which", "other", "others",
    "total", "amount", "value",
}


def _norm_tokens(text: str) -> set:
    """Lower-cased word set with light plural stripping, for label overlap scoring."""
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    out = set()
    for w in words:
        if w in _STOP or len(w) < 3:
            continue
        if len(w) > 4 and w.endswith("s"):
            w = w[:-1]
        out.add(w)
    return out


def concept_map_path() -> str:
    return os.path.join(config.EMBEDDING_DIR, "concept_map.json")


def load_concept_map() -> dict:
    """
    Load and cache concept_map.json. Returns an EMPTY map (not None) when the
    artifact is absent or unreadable, so every caller can treat the result
    uniformly and the pipeline simply loses the enrichment rather than failing.
    """
    path = concept_map_path()
    if path in _cache:
        return _cache[path]

    empty = {"return_code": None, "metrics": [], "axes": [], "member_axes": {},
             "formulas": {}, "table_profiles": {}}
    if not os.path.exists(path):
        log.info("no concept_map.json at %s - business semantics disabled", path)
        _cache[path] = empty
        return empty
    try:
        with open(path, encoding="utf-8") as f:
            cm = json.load(f)
    except Exception as e:
        log.warning("could not read %s (%s) - business semantics disabled", path, e)
        _cache[path] = empty
        return empty

    # Index by physical table once, at load time, rather than scanning 245
    # metrics on every request.
    by_table: dict = {}
    for m in cm.get("metrics", []):
        by_table.setdefault((m.get("table") or "").upper(), []).append(m)
    cm["_metrics_by_table"] = by_table
    _cache[path] = cm
    return cm


def metrics_for_table(table: str) -> list:
    """Every mapped business concept that lives on this physical table."""
    cm = load_concept_map()
    return cm.get("_metrics_by_table", {}).get((table or "").upper(), [])


def table_profile(table: str) -> dict:
    cm = load_concept_map()
    return (cm.get("table_profiles") or {}).get((table or "").upper()) or {}


def unit_multiplier_for_table(table: str):
    """
    The taxonomy-declared multiplier for this table's monetary columns, or None
    when the table has no monetary concepts or its columns disagree on the unit.
    Disagreement returns None deliberately: one blanket UNITS line would be wrong
    for at least some columns, and a wrong unit is worse than no unit.
    """
    prof = table_profile(table)
    if not prof or not prof.get("monetary_concept_count"):
        return None
    if not prof.get("unit_multiplier_consistent"):
        return None
    return prof.get("unit_multiplier")


def rank_metrics(query: str, table: str, top_n: int = 5) -> list:
    """
    The concepts on `table` most likely to be what the question is about, by
    token overlap between the question and the concept label.

    Deliberately lexical, not embedding-based. This runs AFTER the selector has
    already committed to one table, so the job is no longer retrieval — it is
    picking which of that table's ~10-30 concepts to describe. Token overlap is
    predictable and free here, whereas a cosine score over near-identically
    worded sibling labels ("Substandard advances" / "Doubtful advances" /
    "Loss advances") discriminates poorly, which is the same effect already
    documented for table descriptions in src/retriever.py.

    Ties break toward is_core then score, so a scaffolding concept never outranks
    a headline metric on an equal word match.
    """
    metrics = metrics_for_table(table)
    if not metrics:
        return []
    q = _norm_tokens(query)
    if not q:
        return []

    scored = []
    for m in metrics:
        lbl = _norm_tokens(m.get("label"))
        if not lbl:
            continue
        overlap = len(q & lbl)
        if not overlap:
            continue
        # Normalise by label length so a long label does not win on sheer size.
        scored.append((overlap / len(lbl), overlap, m.get("is_core"), m.get("score") or 0, m))

    scored.sort(key=lambda t: (t[0], t[1], t[2], t[3]), reverse=True)
    return [t[4] for t in scored[:top_n]]


def core_metrics(table: str, top_n: int = 5) -> list:
    """
    Fallback when the question matches no concept label on the selected table:
    describe the table's headline metrics instead of nothing. A vague question
    ("show the totals") still benefits from knowing the unit and whether the
    figures are stocks or flows.
    """
    metrics = metrics_for_table(table)
    ranked = sorted(
        metrics,
        key=lambda m: (bool(m.get("is_core")), m.get("score") or 0),
        reverse=True,
    )
    return ranked[:top_n]


def axes_present_in(table: str, label_values: dict, max_axes: int = 3,
                    max_members: int = 5) -> list:
    """
    The dimension axes that are genuinely usable on this table, i.e. whose member
    labels actually appear among the live row-label values sampled from the DB.

    A concept's `dimensional_context_required` is the union of every axis across
    every reporting table it appears in — up to 15 entries, most irrelevant to
    the one physical table in play. Listing all of them would be noise, and
    naming a dimension the table cannot filter on invites a fabricated WHERE
    clause. So an axis earns its place only by matching real stored values.

    label_values: {column_lower: [stored value, ...]} as already assembled by
    build_prompt / build_table_ddl.
    """
    cm = load_concept_map()
    if not cm.get("axes") or not label_values:
        return []

    # Flatten the live row labels once, keeping the column they came from.
    live = []
    for col, values in (label_values or {}).items():
        for v in values:
            live.append((col, str(v)))
    if not live:
        return []
    live_tokens = [(col, v, _norm_tokens(v)) for col, v in live]

    # Only consider axes that the table's own concepts actually reference.
    wanted = set()
    for m in metrics_for_table(table):
        wanted.update(m.get("axes") or [])
    if not wanted:
        return []

    results = []
    for axis in cm["axes"]:
        if axis["label"] not in wanted:
            continue
        # Key by the stored value, not by the member: several members of one axis
        # routinely match the SAME row ('Name of industry' has both a generic and
        # a specific member matching '2.1 Electricity Generation'), and emitting
        # the same literal three times is pure prompt noise.
        matched = {}
        for mem in axis.get("members", []):
            mtok = _norm_tokens(mem.get("label"))
            if not mtok:
                continue
            for col, value, vtok in live_tokens:
                # Require a substantial share of the member's words to appear in
                # the stored value, so 'Doubtful assets two' matches
                # 'D2. Doubtful Assets 2' but not every row mentioning 'assets'.
                if len(mtok & vtok) >= max(1, len(mtok) - 1):
                    matched.setdefault((col.upper(), value),
                                       {"member": mem["label"], "column": col.upper(),
                                        "value": value})
                    break
        if matched:
            results.append({
                "axis": axis["label"],
                "matches": list(matched.values())[:max_members],
                "match_count": len(matched),
            })

    results.sort(key=lambda a: a["match_count"], reverse=True)

    # Several axes can resolve to the SAME physical column — an industry table
    # legitimately satisfies 'Name of industry', 'Name of infrastructure' and
    # 'Distribution of loans assets' all at once. To the SQL model these are one
    # filterable column, so keep only the best-matching axis per column and
    # spend the budget on distinct columns instead of synonyms.
    seen_columns, deduped = set(), []
    for a in results:
        cols = frozenset(m["column"] for m in a["matches"])
        if cols & seen_columns:
            continue
        seen_columns |= cols
        deduped.append(a)
    return deduped[:max_axes]


def formula_for(metric: dict, table: str) -> dict | None:
    """
    A rollup formula for this metric, translated into the physical columns of
    `table`, or None when it cannot be fully translated.

    Partial translation is refused on purpose: a formula with two of its five
    operands still as XBRL concept names is worse than no formula, because the
    model will happily invent columns for the untranslated ones. All-or-nothing.
    """
    cm = load_concept_map()
    formulas = cm.get("formulas") or {}
    # Column per concept_id, restricted to this table.
    col_by_concept = {
        m["concept_id"]: m["column"]
        for m in metrics_for_table(table) if m.get("column")
    }
    row_by_concept = {
        m["concept_id"]: m.get("row_code")
        for m in metrics_for_table(table)
    }

    for fid in metric.get("formulas") or []:
        f = formulas.get(fid)
        if not f or f.get("category") != "cross_concept_rollup":
            continue
        involved = f.get("concepts") or []
        if not involved:
            continue
        if not all(ci.get("concept_id") in col_by_concept for ci in involved):
            continue

        # A rollup is only expressible in COLUMN arithmetic when its operands are
        # actually different columns. On a vertical table every concept shares one
        # value column and differs by row, so substituting columns collapses the
        # formula into nonsense like `STANDARD_DOM = STANDARD_DOM + STANDARD_DOM
        # - STANDARD_DOM`. That is a cross-ROW rollup; expressing it correctly
        # needs per-row-code arithmetic, so refuse rather than emit an identity.
        used = [col_by_concept[ci["concept_id"]] for ci in involved]
        if len(set(used)) < len(used):
            continue

        # Column arithmetic is only valid WITHIN one row. If the operands sit on
        # different reported rows, `TOTAL_DOM = LOSS_DOM + STANDARD_DOM` reads as
        # a single-row identity when the real relationship spans rows — the model
        # would emit arithmetic that silently mixes unrelated line items.
        rows = {row_by_concept.get(ci["concept_id"]) for ci in involved}
        if len(rows) > 1:
            continue

        expr = f.get("expression") or ""
        # The taxonomy expression is XBRL formula syntax ('round($V1 div 100000)
        # * 100000 = ...'). Strip the rounding wrapper the regulator uses for
        # tolerance and keep the arithmetic relationship, then substitute
        # physical columns for the $Vn variables.
        expr = re.sub(r"round\s*\(\s*", "(", expr)
        expr = re.sub(r"\s*div\s+100000\s*\)\s*\*\s*100000", ")", expr)
        for ci in involved:
            expr = re.sub(
                rf"\${re.escape(ci['variable'])}\b",
                col_by_concept[ci["concept_id"]],
                expr,
            )
        if "$" in expr:  # an unsubstituted variable remains - do not ship it
            continue
        return {
            "assertion_id": fid,
            "expression": expr.strip(),
            "columns": [col_by_concept[ci["concept_id"]] for ci in involved],
        }
    return None


def stock_columns(table: str) -> dict:
    """
    {COLUMN: concept label} for every column on this table holding a
    point-in-time balance (XBRL period_type 'instant').

    Summing one of these across reporting periods is always wrong — adding March
    and June closing balances produces a number that describes no date. There was
    no source for this distinction before the taxonomy: the DB just says
    NUMBER(20,2) and the header text reads the same for a stock and a flow.
    """
    out = {}
    for m in metrics_for_table(table):
        if m.get("period_type") != "instant":
            continue
        col = m.get("column") or m.get("value_column")
        if col:
            out.setdefault(col.upper(), m.get("label"))
    return out


def check_stock_aggregation(sql: str, tables) -> list:
    """
    Warn when generated SQL aggregates a point-in-time balance across periods.

    Fires only when BOTH are true, which is what makes it a real signal rather
    than a nag:
      1. an aggregate wraps a column the taxonomy marks as a stock, and
      2. nothing pins the query to a single RDATE.

    A query that already filters to one RDATE (an equality, a MAX() subselect, or
    a BETWEEN) is aggregating within one period — across dimension rows, not
    across time — which is legitimate, so it is left alone.

    Returns a list of human-readable warnings; empty means nothing suspicious.
    This deliberately does NOT invalidate the SQL. "SUM of a stock" is wrong often
    enough to flag and rarely enough to be a legitimate intent, and turning it
    into a hard failure would burn correction rounds on queries that are fine.
    """
    if not sql:
        return []
    lowered = sql.lower()

    # Is the query pinned to one period? Any of these count.
    #
    # Confirmed live-model bug (caught by actually running this against
    # SQLCoder, not just hand-written unit tests): the previous version of
    # this check treated the bare SUBSTRING "max(rdate)" as proof of pinning,
    # regardless of the comparison operator next to it. SQLCoder produced
    # `RDATE <= (SELECT MAX(RDATE) FROM t)` for "across all reporting
    # quarters" — which spans EVERY period up to the max, the opposite of
    # pinning to one — and the bare substring match let it through with zero
    # warning. Every check below now requires the actual equality
    # relationship with RDATE, not just the MAX(...) subquery's presence
    # somewhere in the string.
    pinned = bool(
        re.search(r"rdate\s*=\s*'", lowered)                              # RDATE = '2024-...'
        or re.search(r"rdate\s*=\s*\(\s*select\s+max\s*\(\s*rdate\s*\)", lowered)  # RDATE = (SELECT MAX(RDATE)...)
        or re.search(r"rdate\s+between", lowered)
        or re.search(r"trunc\s*\(\s*rdate\s*\)\s*=", lowered)             # TRUNC(RDATE) = ...
    )
    if pinned:
        return []

    warnings = []
    for t in tables or []:
        name = (t.get("table") if isinstance(t, dict) else t) or ""
        for col, label in stock_columns(name).items():
            # `lowered` is lower-cased but stock_columns() returns upper-case
            # names, so the column must be lowered too or this never matches.
            if re.search(rf"\b(sum|avg)\s*\(\s*[\w.]*\b{re.escape(col.lower())}\b",
                         lowered):
                warnings.append(
                    f"{col} is a point-in-time balance (\"{label}\"), but the query "
                    f"aggregates it without restricting RDATE to one period - the "
                    f"result adds balances from different dates."
                )
    return warnings

