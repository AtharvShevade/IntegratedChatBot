"""
Per-axis context budgets, and the accounting that reports what they dropped.

Why per-axis caps rather than one token limit
---------------------------------------------
A single "keep the prompt under N tokens" rule degrades badly, because the axes
are not interchangeable. The measured trace in
scratch/sql_generation_context_report.md shows ONE column's row-label list at
~23% of the whole prompt: a flat token cap would have cut that list by dropping
whichever values came last, which is exactly the pre-context failure — the
values were kept in SAMPLE order, so the literal the question actually needed
could be truncated out while three irrelevant ones stayed.

So each axis gets its own cap, applied after that axis has been RANKED, and a
total-token ceiling acts only as a backstop. When the backstop does fire it
sheds in a fixed, published order (lowest marginal value first) instead of
truncating whatever happens to be at the end of the string.

Why every drop is recorded
--------------------------
`BudgetReport` is carried on the PromptContext and logged per request. "Why was
this column not in the prompt" has to be answerable from a log line — the old
blind truncation was invisible both to logs and to eval.
"""

import logging
from dataclasses import dataclass

import src.config as config

from src.context.types import BudgetReport, Drop

log = logging.getLogger("context.budget")

# Shed order when the total-token backstop fires: semantics first (advisory
# prose), then the second example, then unbound evidence columns, then labels.
# Keys, the row-label column, bound columns and the TOTAL row are never shed —
# dropping those changes the answer rather than shortening the prompt.
SHED_ORDER = ("semantics", "examples", "evidence_columns", "labels")

# Reasons, kept as constants so eval can group by them.
REASON_OVER_BUDGET = "over_budget"
REASON_LOW_CONFIDENCE = "low_confidence"
REASON_OUT_OF_SCOPE = "out_of_scope"
REASON_UNBOUND = "unbound"


@dataclass(frozen=True)
class ContextBudget:
    """
    Caps on what may reach the SQL model.

    Defaults are chosen against the measured baseline, not guessed:

    max_columns_per_table=12
        The widest table in the active schema has 34 columns and the median has
        8-9, so 12 keeps every median table whole while capping the outliers
        that dominate the prompt. The pre-context path rendered ALL columns
        whenever the selector short-circuited, which is the common path.

    max_labels_per_column=6
        Replaces MAX_LABELS_DDL=14 applied to an unranked list. Six RANKED
        values plus a pinned TOTAL row carries more usable information than
        fourteen sample-ordered ones, at ~40% of the tokens.

    max_examples=2
        One paraphrase-nearest example, plus one that demonstrates the required
        SQL shape when that differs. The old path allowed exactly one, chosen
        for topical similarity only.

    max_total_tokens=1800
        A backstop well inside OLLAMA_NUM_CTX=8192 — the retry path resends the
        schema plus the bad SQL plus the reason, so the ceiling has to leave
        room for a correction round.
    """
    max_tables: int = 2
    max_columns_per_table: int = 12
    max_labels_per_column: int = 6
    max_examples: int = 2
    max_rule_lines: int = 12
    max_semantic_lines: int = 6
    max_total_tokens: int = 1800

    @classmethod
    def from_config(cls) -> "ContextBudget":
        """Build from config, which reads the env. Every field is overridable so
        a deployment can retune without editing code — the same pattern
        MODEL_PROFILES' numeric knobs already follow."""
        return cls(
            max_tables=config.CTX_MAX_TABLES,
            max_columns_per_table=config.CTX_MAX_COLUMNS_PER_TABLE,
            max_labels_per_column=config.CTX_MAX_LABELS_PER_COLUMN,
            max_examples=config.CTX_MAX_EXAMPLES,
            max_rule_lines=config.CTX_MAX_RULE_LINES,
            max_semantic_lines=config.CTX_MAX_SEMANTIC_LINES,
            max_total_tokens=config.CTX_MAX_TOTAL_TOKENS,
        )


def estimate_tokens(text: str) -> int:
    """
    Characters ÷ 4.

    Deliberately the same rough heuristic the context report used, so budget
    numbers stay directly comparable to the ~764-token baseline measured there.
    It is not a tokenizer: for identifier-dense DDL it tends to UNDER-count, so
    treat the ceiling as approximate and leave headroom (see max_total_tokens).
    """
    return (len(text) + 3) // 4


class BudgetTracker:
    """
    Mutable accumulator used while a context is being assembled; emits a frozen
    BudgetReport at the end.

    Separate from ContextBudget (the caps) because one is configuration and the
    other is per-request accounting.
    """

    def __init__(self, budget: ContextBudget):
        self.budget = budget
        self._drops: list = []
        self.est_tokens = 0
        self.low_binding = False
        self.over_budget = False

    def drop(self, axis: str, item: str, reason: str = REASON_OVER_BUDGET):
        self._drops.append(Drop(axis=axis, item=str(item), reason=reason))

    def drop_many(self, axis: str, items, reason: str = REASON_OVER_BUDGET):
        for item in items:
            self.drop(axis, item, reason)

    def cap(self, axis: str, items: list, limit: int, label=str) -> list:
        """
        Truncate a RANKED list to `limit`, recording everything removed.

        `items` must already be in priority order — this function does not rank,
        and applying it to an unranked list reproduces exactly the bug it exists
        to prevent.
        """
        if limit is None or len(items) <= limit:
            return items
        kept, removed = items[:limit], items[limit:]
        self.drop_many(axis, (label(i) for i in removed))
        return kept

    def note_low_binding(self, table: str):
        """No column binding survived for this table, so the slice is inferred
        rather than resolved. Recorded so eval can separate 'sliced well' from
        'sliced blind' — the two look identical in a token count."""
        self.low_binding = True
        log.info("no confident column binding for %s — slice is inferred", table)

    def report(self, est_tokens: int | None = None) -> BudgetReport:
        if est_tokens is not None:
            self.est_tokens = est_tokens
        self.over_budget = self.est_tokens > self.budget.max_total_tokens
        if self.over_budget:
            log.warning(
                "context is ~%d tokens, over the %d budget after %d drops",
                self.est_tokens, self.budget.max_total_tokens, len(self._drops),
            )
        return BudgetReport(
            drops=tuple(self._drops),
            est_tokens=self.est_tokens,
            over_budget=self.over_budget,
            low_binding=self.low_binding,
        )
