"""
Schema slicing — the minimum useful view of ONE physical table.

The problem this replaces
-------------------------
`sql_generator.build_prompt` rendered whole tables:

* every column, via `_load_all_columns(table_names)`. Column pruning existed but
  only fired when the selector's LLM returned a per-column selection — i.e.
  never on the four short-circuit paths (strong QA match, <2 candidates, score
  dominance, any failure), which are the common paths.
* every sampled row label, because the query-ranked `matched_labels` were
  SUPPLEMENTED from `description_samples.json` and then truncated at a fixed 14.
  The values kept were therefore in SAMPLE order, not relevance order: the
  literal the question needed could be truncated out while three irrelevant ones
  stayed. In the measured trace one column's label list was ~23% of the whole
  prompt.

Keep-set algebra
----------------
    KEEP =   REQUIRED            keys + the row-label column(s)
           ∪ BOUND               a ColumnBinding named it
           ∪ SIBLING_CLOSURE     the _DOM/_OVE partner of anything bound
           ∪ INTENT_EXTRAS       RDATE for a trend, the label column for a breakdown
           ∪ EVIDENCE[:k]        retrieved but unbound, lowest priority
           ∪ CORE                fallback only, when nothing was bound

Two rules make this safe rather than merely small:

* **Sibling closure is mandatory.** Keeping `EXPOSURE_DOM` while dropping
  `EXPOSURE_OVE` silently changes the answer to an unscoped "total exposure"
  question — a wrong number, not a missing one. Note the pairs are derived from
  the actual column names, because this schema spells overseas BOTH ways:
  `_ove` (8 columns) and `_o` (14, e.g. PROVISION_MADE_LOSSES_O). A fixed
  suffix list misses more pairs than it catches.
* **The row-label column is never droppable.** It is the only correct way to
  filter a vertical table, and `validate_sql`'s vertical guard rejects any
  aggregate that does not filter on it — dropping it would make a whole class of
  question unanswerable rather than merely less well-informed.

When nothing is confidently bound the slice widens instead of guessing, and the
tracker records `low_binding` — "sliced well" and "sliced blind" are
indistinguishable in a token count, so they must be distinguishable in eval.
"""

import logging
import re

from src import schema_store
from src.context.types import (
    INTENT_BREAKDOWN,
    INTENT_COMPARE,
    INTENT_MOVEMENT,
    INTENT_RANK,
    INTENT_TREND,
    ROLE_BOUND,
    ROLE_CORE,
    ROLE_EVIDENCE,
    ROLE_KEY,
    ROLE_LABEL,
    ROLE_SIBLING,
    SCOPE_DOM,
    SCOPE_OVE,
    LabelBinding,
    SlicedColumn,
    TableSlice,
)

log = logging.getLogger("context.slicer")

# Columns that identify the row's entity/period rather than a metric. Never
# dropped: without RDATE the "latest reporting period" filter every prompt style
# asks for cannot be written at all.
KEY_COLUMNS = ("code", "rdate")

# Overseas counterparts, longest first so `_ove` is tried before `_o` (otherwise
# `tot_expo_ove` would be read as base `tot_expo_ov` + suffix `_e`).
_DOM_SUFFIX = "dom"
_OVE_SUFFIXES = ("ove", "opr", "o")

# Priority tiers, lowest number = kept first when the column budget bites.
_TIER = {
    ROLE_KEY: 0,
    ROLE_LABEL: 0,
    ROLE_BOUND: 1,
    ROLE_SIBLING: 2,
    ROLE_CORE: 3,
    ROLE_EVIDENCE: 4,
}
# Roles the budget may never drop — dropping these changes the answer or makes
# the table unqueryable, rather than making the prompt shorter.
_UNDROPPABLE = (ROLE_KEY, ROLE_LABEL)


def _col_name(col: dict) -> str:
    return col.get("name") or col.get("column_name") or ""


def dom_ove_pairs(entry: dict) -> dict:
    """
    {column_lower: partner_column_lower} for every DOM/OVE pair on this table,
    derived from the real column names.

    Derived rather than declared because `semantic_layer.dom_ove_pairs` is
    authored per table and currently covers one; the naming convention covers
    all of them. The semantic layer still wins where it IS authored (see
    `_declared_pairs`).
    """
    by_base: dict = {}
    for col in entry.get("columns") or []:
        name = _col_name(col).lower()
        if not name:
            continue
        if name.endswith(f"_{_DOM_SUFFIX}"):
            by_base.setdefault(name[: -(len(_DOM_SUFFIX) + 1)], {})["dom"] = name
            continue
        for suf in _OVE_SUFFIXES:
            if name.endswith(f"_{suf}"):
                by_base.setdefault(name[: -(len(suf) + 1)], {})["ove"] = name
                break

    pairs: dict = {}
    for sides in by_base.values():
        dom, ove = sides.get("dom"), sides.get("ove")
        if dom and ove:
            pairs[dom] = ove
            pairs[ove] = dom
    return pairs


def _declared_pairs(table: str) -> dict:
    """Pairs the semantic layer declares, which override the derived ones."""
    try:
        from src.semantic_layer import dom_ove_pairs as declared
    except ImportError:
        return {}
    out: dict = {}
    for dom, ove in declared(table):
        out[dom] = ove
        out[ove] = dom
    return out


def label_columns_for(table: str, entry: dict) -> set:
    """
    Lowercase names of this table's row-label columns.

    Sourced from the SAMPLED values (description_samples.json), intersected with
    the columns the table really has — which is exactly how `build_prompt`
    decided a table was "vertical", so the vertical/non-vertical verdict does not
    move as part of this refactor.
    """
    sampled = set(schema_store.labels_for(table))
    real = {_col_name(c).lower() for c in entry.get("columns") or []}
    return sampled & real


def resolve_needs_trim(table: str, label_cols: set) -> frozenset:
    """
    Which label columns must be filtered through TRIM().

    Three sources, unioned, because each one alone has been observed wrong:

    * a LIVE padding check over the sampled values — what `build_table_ddl`
      does today, and the only source that reflects the data as it is now;
    * `needs_trim.json` — written by the sampler, frequently absent (it does not
      exist in this build);
    * the semantic layer's authored `vertical.needs_trim` flag.

    A missed TRIM() is a silent WRONG ANSWER, not an error: the stored value
    '     C2. Slipped to NPAs' compared with `= 'C2. Slipped to NPAs'` matches
    zero rows and returns an empty result set with no complaint. Unioning is the
    safe direction — an unnecessary TRIM() is still correct SQL.
    """
    out = set()
    samples = schema_store.labels_for(table)
    for col in label_cols:
        values = samples.get(col) or []
        if any(v != v.strip() for v in values):
            out.add(col)

    out |= (schema_store.needs_trim().get(table.lower()) or set()) & label_cols

    try:
        from src.semantic_layer import vertical_spec
        spec = vertical_spec(table)
        if spec.get("needs_trim") and spec.get("label_column"):
            declared = str(spec["label_column"]).lower()
            if declared in label_cols:
                out.add(declared)
    except ImportError:
        pass

    return frozenset(out)


def _unit_multiplier(table: str):
    try:
        from src.concept_map import unit_multiplier_for_table
        return unit_multiplier_for_table(table)
    except Exception:                                  # concept_map absent/malformed
        return None


def _core_metric_columns(table: str, real_cols: set, limit: int) -> list:
    """Fallback column names when nothing was bound — the table's own core
    metrics per the XBRL concept map, which is a better guess than 'the first N
    columns in schema order'."""
    try:
        from src.concept_map import core_metrics
    except Exception:
        return []
    out = []
    for m in core_metrics(table, top_n=limit) or []:
        name = (m.get("value_column") if m.get("mapping_type") == "narrow_keyvalue"
                else m.get("column"))
        if name and name.lower() in real_cols and name.lower() not in out:
            out.append(name.lower())
    return out


def _lexical_scores(query: str, values: list) -> dict:
    """
    {value: 0..1} literal token overlap between the question and each row-label
    value.

    Row-label literals are simultaneously what dense retrieval is worst at and
    what the model most needs verbatim: it cannot invent 'v) Loss' or
    'C.2 Due to Actual Recoveries' character for character, so a literal that is
    not shown produces a query returning zero rows — silently, with no error.
    Token overlap is the signal that actually discriminates here, and it is a
    cheap stand-in for the BM25 label channel.

    Scored as (fraction of the LABEL's tokens matched), so a short precise label
    beats a long one that merely shares a word: for "…falls under Loss
    classification", 'v) Loss' scores 1.0 while
    'ii.b) Loans and Advances where 90 day norms…' scores ~0.1.
    """
    q_tokens = {t for t in re.findall(r"[a-z0-9]+", query.lower()) if len(t) > 2}
    if not q_tokens:
        return {}

    scores = {}
    for value in values:
        v_tokens = {t for t in re.findall(r"[a-z0-9]+", value.lower()) if len(t) > 2}
        if v_tokens:
            scores[value] = len(q_tokens & v_tokens) / len(v_tokens)
    return scores


def _rank_labels(table: str, label_cols: set, matched, intent, budget, tracker,
                 query: str = "") -> tuple:
    """
    Ranked, capped row-label values for one table.

    Every candidate value is scored ONCE on both available signals and then
    sorted, rather than being concatenated in tiers:

        score = dense retrieval confidence  +  LEXICAL_WEIGHT x token overlap

    Tiering was measured to be the wrong shape. With retrieved values placed
    ahead of everything else, the dense hits filled all six slots on their own
    and the lexical pass never ran — so 'v) Loss' stayed missing for "how much of
    the overseas loan book falls under Loss classification" even though it is a
    verbatim token match, because six vaguer values outranked it by arriving
    first. Scoring the combined set lets an exact lexical match displace a weak
    dense one, which is the entire reason to have two signals.

    The TOTAL row is pinned outside the cap either way — RULE V2 and
    `validate_sql`'s vertical guard both point at it, so a prompt that omits it
    asks the model to satisfy a rule with nothing to satisfy it with.
    """
    from src.sql_generator import _find_total_row

    samples = schema_store.labels_for(table)
    needs_trim = resolve_needs_trim(table, label_cols)
    out: list = []

    # How much an exact token match is worth against a dense hit. 1.0 means a
    # full lexical match can outrank any dense hit, which is the intended
    # behaviour for literals the model has to copy character for character.
    LEXICAL_WEIGHT = 1.0

    for col in sorted(label_cols):
        values = list(samples.get(col) or [])
        if not values:
            continue
        padded = col in needs_trim
        total_row = _find_total_row(values)

        dense = {}
        for lbl in matched:
            if lbl.column.lower() == col:
                dense[lbl.value] = max(dense.get(lbl.value, 0.0), lbl.confidence)
        lexical = _lexical_scores(query, values)

        # Candidates = every sampled value, plus any retrieved value not present
        # in the samples (the sample cap is per column, so retrieval can surface
        # a value the sampler did not store).
        candidates = list(values) + [v for v in dense if v not in values]

        scored = []
        for v in candidates:
            score = dense.get(v, 0.0) + LEXICAL_WEIGHT * lexical.get(v, 0.0)
            scored.append((score, v))
        # Sort by score, then by the original sample order for a stable tie-break
        # (so an unscored table renders the same values it always did).
        position = {v: i for i, v in enumerate(candidates)}
        scored.sort(key=lambda pair: (-pair[0], position[pair[1]]))

        def _mk(value, confidence, is_total=False):
            return LabelBinding(
                table=table,
                column=col,
                value=value.strip() if padded else value,
                confidence=confidence,
                needs_trim=padded,
                is_total_row=is_total,
            )

        pinned, rest = [], []
        want_total = intent.needs_total_row or total_row is not None
        if want_total and total_row:
            pinned.append(_mk(total_row, 1.0, is_total=True))
        for score, v in scored:
            if total_row and v == total_row and pinned:
                continue
            rest.append(_mk(v, score))

        kept = tracker.cap(
            "labels", rest,
            max(budget.max_labels_per_column - len(pinned), 0),
            label=lambda l: f"{table}.{col}={l.value!r}",
        )
        out.extend(kept + pinned)

    return tuple(out)


def slice_table(table, intent, bindings=(), matched_labels=(), evidence_columns=(),
                budget=None, tracker=None, query: str = "") -> TableSlice | None:
    """
    Build the minimum slice of `table` for this question.

    bindings          ColumnBinding[] for this table (verified first)
    matched_labels    LabelBinding[] for this table, in retrieval-ranked order
    evidence_columns  lowercase column names retrieval surfaced but did not bind
    Returns None when the table has no schema entry — the caller then keeps its
    existing "columns only" fallback rather than emitting an empty CREATE TABLE.
    """
    from src.context.budget import BudgetTracker, ContextBudget

    budget = budget or ContextBudget.from_config()
    tracker = tracker or BudgetTracker(budget)

    entries = schema_store.table_entries([table])
    entry = entries.get(table.lower())
    if entry is None:
        return None

    schema_cols = [c for c in (entry.get("columns") or []) if _col_name(c)]
    order = {_col_name(c).lower(): i for i, c in enumerate(schema_cols)}
    real_cols = set(order)
    by_name = {_col_name(c).lower(): c for c in schema_cols}

    label_cols = label_columns_for(table, entry)
    pairs = {**dom_ove_pairs(entry), **_declared_pairs(table)}

    # role per column; first assignment wins, so a bound key column stays a key
    roles: dict = {}
    scores: dict = {}

    def assign(name, role, score=0.0):
        name = (name or "").lower()
        if name not in real_cols or name in roles:
            return
        roles[name] = role
        scores[name] = score

    # ── REQUIRED ─────────────────────────────────────────────────────────────
    for col in schema_cols:
        name = _col_name(col).lower()
        if name in KEY_COLUMNS or col.get("is_primary_key"):
            assign(name, ROLE_KEY, 1.0)
    for name in sorted(label_cols):
        assign(name, ROLE_LABEL, 1.0)

    # ── BOUND ────────────────────────────────────────────────────────────────
    bound_names = []
    for b in sorted(bindings, key=lambda b: (-int(b.verified), -b.confidence)):
        name = b.column.lower()
        if name in real_cols:
            assign(name, ROLE_BOUND, b.confidence)
            bound_names.append(name)
        # A narrow key-value mapping identifies its metric by ROW, so the row
        # selector's label column has to be present too.
        if b.row_selector:
            assign(str(b.row_selector[0]).lower(), ROLE_LABEL, 1.0)

    # ── INTENT EXTRAS ────────────────────────────────────────────────────────
    if intent.kind == INTENT_TREND:
        assign("rdate", ROLE_KEY, 1.0)
    if intent.wants_breakdown or intent.kind in (INTENT_BREAKDOWN, INTENT_MOVEMENT,
                                                 INTENT_RANK, INTENT_COMPARE):
        for name in sorted(label_cols):
            assign(name, ROLE_LABEL, 1.0)

    # ── FALLBACK when nothing was bound ──────────────────────────────────────
    # "Empty BOUND ⇒ widen, don't guess", and the widening has to be real:
    # measured over the 100 gold-SQL questions, slicing an UNBOUND table down to
    # its retrieved-evidence columns cost 12.5% column recall (35 of 100
    # questions lost a column the gold SQL needed) — e.g. TOTAL_LOAN_ASSETS was
    # simply not among the column-index hits for "how much of the domestic loan
    # book is classified as Doubtful".
    #
    # With no binding there is no evidence that a given column is safe to drop,
    # so on any table that FITS the budget the honest slice is the whole table:
    # the column axis saves nothing real, and the label axis (the larger cost —
    # ~23% of the traced prompt from one column) still gets sliced. Only tables
    # too wide to fit are narrowed, where keeping everything is not an option
    # anyway.
    core_names = []
    if not bound_names:
        tracker.note_low_binding(table)
        if len(real_cols) <= budget.max_columns_per_table:
            for name in sorted(real_cols, key=lambda n: order[n]):
                assign(name, ROLE_CORE, 0.5)
                core_names.append(name)
        else:
            for name in _core_metric_columns(table, real_cols, budget.max_columns_per_table):
                assign(name, ROLE_CORE, 0.5)
                core_names.append(name)

    # ── SIBLING CLOSURE ──────────────────────────────────────────────────────
    # Runs over the CORE fallback as well as the bound columns: the half-a-pair
    # risk does not go away just because the metric was inferred rather than
    # bound. An unscoped "total exposure" answered from EXPOSURE_DOM alone is a
    # wrong number either way.
    # Narrowed only when the question actually chose a side.
    narrow_to = intent.scope if intent.scope in (SCOPE_DOM, SCOPE_OVE) else None
    _ove_endings = tuple(f"_{s}" for s in _OVE_SUFFIXES)
    for name in bound_names + core_names:
        partner = pairs.get(name)
        if not partner:
            continue
        if narrow_to == SCOPE_DOM and partner.endswith(_ove_endings):
            continue
        if narrow_to == SCOPE_OVE and partner.endswith(f"_{_DOM_SUFFIX}"):
            continue
        assign(partner, ROLE_SIBLING, scores.get(name, 0.0) * 0.9)

    # ── EVIDENCE, lowest priority ────────────────────────────────────────────
    for i, name in enumerate(evidence_columns or ()):
        assign(name, ROLE_EVIDENCE, max(0.0, 0.4 - i * 0.01))

    # If NOTHING survived beyond keys, the slice would be unanswerable — widen to
    # the whole table rather than emit a keys-only CREATE TABLE. A too-wide prompt
    # is recoverable; a prompt with no metric column in it is not.
    if not any(r not in _UNDROPPABLE for r in roles.values()):
        for name in real_cols:
            assign(name, ROLE_EVIDENCE, 0.1)
        tracker.drop("columns", table, "unbound")

    # ── cap by priority tier, then restore schema order for rendering ─────────
    ranked = sorted(roles, key=lambda n: (_TIER[roles[n]], -scores[n], order[n]))
    keep_limit = max(budget.max_columns_per_table, sum(
        1 for n in ranked if roles[n] in _UNDROPPABLE
    ))
    kept = tracker.cap("columns", ranked, keep_limit,
                       label=lambda n: f"{table}.{n}")
    kept_set = set(kept)

    columns = tuple(
        SlicedColumn(
            name=_col_name(by_name[name]),
            type=(by_name[name].get("type") or "").upper(),
            description=by_name[name].get("description") or "",
            nullable=by_name[name].get("nullable", True),
            is_primary_key=bool(by_name[name].get("is_primary_key")),
            role=roles[name],
            score=scores[name],
        )
        for name in sorted(kept_set, key=lambda n: order[n])
    )

    # Only label columns that SURVIVED can carry literals.
    live_label_cols = {n for n in kept_set if roles[n] == ROLE_LABEL}
    labels = _rank_labels(table, live_label_cols, matched_labels, intent, budget,
                          tracker, query=query)
    total_row = next((l.value for l in labels if l.is_total_row), None)

    return TableSlice(
        table=entry.get("table") or table,
        columns=columns,
        labels=labels,
        label_columns=frozenset(live_label_cols),
        is_vertical=bool(live_label_cols and labels),
        total_row=total_row,
        needs_trim=resolve_needs_trim(table, live_label_cols),
        unit_multiplier=_unit_multiplier(table),
        description=entry.get("description") or "",
        dropped_columns=len(real_cols) - len(kept_set),
        total_columns=len(real_cols),
    )
