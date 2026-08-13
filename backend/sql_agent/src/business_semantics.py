"""
Renders the XBRL business-semantics block that gets injected into the SQL
generation prompt.

src/concept_map.py is the data layer; this module is presentation only. It exists
separately from src/sql_generator.py because build_prompt is already long and
this block has its own inclusion rules, its own caps, and its own staged rollout.

Staged rollout
--------------
Prompt changes to a 7B model are NOT additive — the codebase already documents
cases where a prose instruction had no measurable effect at this size
(src/selector.py's module docstring, on why table pruning had to become
structural). So each layer of this block is separately switchable via
config.BUSINESS_SEMANTICS_LEVEL, and the intended rollout is one level at a time
with an eval run between each:

    off        nothing rendered; byte-identical prompts to before this module
    units      the reporting-unit line only          <- start here
    metrics    + business label -> column cards
    aggregation+ stock/flow SUM guidance
    dimensions + usable dimension axes and their live literals
    derivation + a rollup formula in physical columns   <- full block

Levels are cumulative and ordered by (value / risk): `units` fixes a silent
100000x error and cannot mislead about schema, whereas `derivation` puts an
arithmetic expression in front of the model and carries the most risk of being
copied when it was not asked for.
"""
import logging

import src.config as config
from src.concept_map import (
    axes_present_in,
    core_metrics,
    formula_for,
    metrics_for_table,
    rank_metrics,
    unit_multiplier_for_table,
)

log = logging.getLogger("business_semantics")

LEVELS = ["off", "units", "metrics", "aggregation", "dimensions", "derivation"]

MAX_METRIC_CARDS = 5

# Rs 1 lakh = 1e5, Rs 1 crore = 1e7. Only these two are ever declared by the
# taxonomy (unit_multiplier is 100000 or 1), but the mapping is written out so an
# unexpected multiplier renders honestly instead of being mislabelled.
_UNIT_NAMES = {
    100000: "Rs LAKH",
    10000000: "Rs CRORE",
    1000: "Rs THOUSAND",
    1: "the base unit (rupees, counts or text as applicable)",
}


def _level_at_least(level: str) -> bool:
    """True when the configured level includes `level` (levels are cumulative)."""
    current = (getattr(config, "BUSINESS_SEMANTICS_LEVEL", "off") or "off").lower()
    if current not in LEVELS:
        log.warning("unknown BUSINESS_SEMANTICS_LEVEL=%r - treating as 'off'", current)
        return False
    return LEVELS.index(current) >= LEVELS.index(level)


def enabled() -> bool:
    return _level_at_least("units")


def _measure_phrase(metric: dict) -> str:
    """How to describe the metric's nature in one short clause."""
    kind = metric.get("measure") or "other"
    period = metric.get("period_type")
    if kind == "monetary":
        base = "monetary"
    elif kind == "percent":
        base = "percentage"
    elif kind == "ratio":
        base = "ratio"
    elif kind == "count":
        base = "count"
    elif kind == "text":
        return "text"
    elif kind == "date":
        return "date"
    else:
        base = "numeric"
    if period == "instant":
        return f"{base}, point-in-time balance"
    if period == "duration":
        return f"{base}, period flow"
    return base


def _metric_target(metric: dict) -> str | None:
    """
    The physical thing to SELECT for this concept, phrased per mapping_type.

    narrow_keyvalue tables hold every metric in one VALUE column and identify
    which metric a row is by its CODE, so naming the column alone would be
    useless — the row selector is the whole point.
    """
    target = metric.get("value_column") if metric.get("mapping_type") == "narrow_keyvalue" \
        else metric.get("column")
    if not target:
        return None
    # Only append the row filter when the concept_map has certified that this
    # code actually selects THIS metric's row. On a wide table the same code is
    # just the start of the table's code band, and filtering on it would pin
    # every answer to one arbitrary dimension row — see
    # _mark_row_code_usability in build_concept_map.py.
    if metric.get("row_code_selects_metric"):
        return f"{target} on the row where {metric['row_code_column']} = {metric['row_code']}"
    return target


def build_block(user_query: str, table: str, label_values: dict | None = None,
                compact: bool = False) -> str:
    """
    Render the business-semantics block for ONE selected table, or "" when there
    is nothing trustworthy to say.

    table: the single physical table the selector committed to.
    label_values: {column_lower: [stored row-label value, ...]} as build_prompt
        already assembles it — used to prove a dimension axis is actually usable
        here before naming it.
    compact: cap the block at the `aggregation` level regardless of the configured
        level. Used by the "minimal" prompt style, whose whole purpose is a short
        prompt for small-context models — same reasoning as MAX_LABELS_MINIMAL.

    Returns a plain-text block WITHOUT a section header; the caller decides how to
    frame it for the prompt style in play.
    """
    if not enabled() or not table:
        return ""

    def at_least(level: str) -> bool:
        if compact and LEVELS.index(level) > LEVELS.index("aggregation"):
            return False
        return _level_at_least(level)

    metrics = metrics_for_table(table)
    if not metrics:
        return ""

    lines = []

    # ── units ────────────────────────────────────────────────────────────────
    mult = unit_multiplier_for_table(table)
    if mult and mult != 1:
        unit_name = _UNIT_NAMES.get(mult, f"units of {mult}")
        lines.append(f"Monetary amounts in this table are reported in {unit_name}.")
        if mult == 100000:
            lines.append("  To answer in crore divide by 100. To answer in rupees "
                         "multiply by 100000. Otherwise return the stored value.")
        else:
            lines.append(f"  Multiply by {mult} for the amount in rupees.")

    # The CODE correction. This is not cosmetic: CODE is a per-table LINE-ITEM
    # code (scripts/phase0_xbrl_reconcile.py; CODE 1000 <-> '1. Transport and
    # adjoining Infrastructure'), and every prompt before this said it identified
    # the reporting entity. A model told CODE is an entity id has no reason to
    # filter on it and every reason to GROUP BY it.
    if any(m.get("row_code_column") for m in metrics):
        lines.append("CODE identifies WHICH REPORTED LINE ITEM a row is - it is not "
                     "a bank or entity id. One CODE = one row of the return.")

    # ── metric cards ─────────────────────────────────────────────────────────
    if at_least("metrics"):
        chosen = rank_metrics(user_query, table, top_n=MAX_METRIC_CARDS)
        if not chosen:
            chosen = core_metrics(table, top_n=3)
        cards = []
        for m in chosen:
            target = _metric_target(m)
            if not target:
                continue
            cards.append(f'  "{m["label"]}" -> {target}   [{_measure_phrase(m)}]')
        if cards:
            lines.append("Business metrics on this table:")
            lines.extend(cards)

        # ── aggregation guidance ─────────────────────────────────────────────
        if at_least("aggregation"):
            has_instant = any(m.get("period_type") == "instant" for m in chosen)
            has_duration = any(m.get("period_type") == "duration" for m in chosen)
            agg = []
            if has_instant:
                agg.append("  A point-in-time balance must NOT be summed across RDATE. "
                           "Pick one RDATE (the latest unless the question says otherwise).")
            if has_duration:
                agg.append("  A period flow may be summed across RDATE only when the "
                           "question asks for a cumulative or year-to-date figure.")
            if agg:
                lines.append("Aggregation:")
                lines.extend(agg)

    # ── dimensions ───────────────────────────────────────────────────────────
    if at_least("dimensions"):
        axes = axes_present_in(table, label_values or {})
        if axes:
            lines.append("Dimensions available on this table (filter with the exact "
                         "stored value shown):")
            for a in axes:
                for match in a["matches"][:3]:
                    lines.append(f"  {a['axis']}: {match['column']} = '{match['value']}'")

    # ── derivation ───────────────────────────────────────────────────────────
    if at_least("derivation"):
        chosen = rank_metrics(user_query, table, top_n=2)
        for m in chosen:
            f = formula_for(m, table)
            if f:
                lines.append(f'Derivation of "{m["label"]}" from this table\'s columns:')
                lines.append(f"  {f['expression']}")
                break

    return "\n".join(lines).strip()


def build_rules(table: str) -> list:
    """
    Extra prompt RULES implied by the business layer, to append to the rule list
    the prompt already carries. Kept separate from build_block because rules must
    sit in the prompt's rules section, not in the descriptive block.
    """
    if not enabled() or not table:
        return []
    rules = []
    mult = unit_multiplier_for_table(table)
    if mult == 100000:
        rules.append(
            "- Amounts are stored in Rs lakh. If the question asks for crore, divide by 100; "
            "if it asks for rupees, multiply by 100000; otherwise return the stored value unchanged."
        )
    if _level_at_least("metrics") and any(
        m.get("row_code_selects_metric") for m in metrics_for_table(table)
    ):
        rules.append(
            "- CODE is the line-item code of a reported row, not an entity id. To select one "
            "reported item filter CODE = <that item's code>; never GROUP BY CODE to mean 'per bank'."
        )
    return rules
