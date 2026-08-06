"""
Data structures exchanged between the context stages.

Everything here is a FROZEN dataclass built from tuples rather than lists, for
three reasons that all showed up as real bugs or real costs in the pre-context
pipeline:

1. **No accidental sharing.** The retriever's FAISS metadata dicts come from a
   module-level pickle cache reused across requests, and the code carries an
   explicit comment about copying them rather than annotating them in place.
   Frozen dataclasses make that class of bug unrepresentable.
2. **Serializable end to end.** `PromptContext.to_dict()` means context quality
   can be measured offline over a question set with no LLM and no DB, the same
   way scripts/eval_retrieval.py measures ranking.
3. **A single source of truth for the renderer.** The renderer takes a
   PromptContext and nothing else, so "why was this column in the prompt" is
   answerable from `trace` instead of by re-deriving five loaders.
"""

from dataclasses import asdict, dataclass, field, replace

# ── Intent ────────────────────────────────────────────────────────────────────

# Question kinds. Deliberately small: each one must change something concrete
# downstream (a rule pack, a column keep-rule, or an example shape). A taxonomy
# finer than what the prompt actually varies on is just unused classification.
INTENT_LOOKUP = "lookup"        # a single stored figure
INTENT_AGGREGATE = "aggregate"  # a total/sum spanning rows, parts or periods
INTENT_TREND = "trend"          # over time; RDATE must survive slicing
INTENT_COMPARE = "compare"      # two scopes/entities side by side
INTENT_RANK = "rank"            # top/bottom N, ordering
INTENT_BREAKDOWN = "breakdown"  # "by <dimension>" — needs the label column
INTENT_MOVEMENT = "movement"    # opening/closing/additions/slippage flows

ALL_INTENTS = (
    INTENT_LOOKUP, INTENT_AGGREGATE, INTENT_TREND, INTENT_COMPARE,
    INTENT_RANK, INTENT_BREAKDOWN, INTENT_MOVEMENT,
)

# Scope of a DOM/OVE question.
SCOPE_DOM = "dom"
SCOPE_OVE = "ove"
SCOPE_BOTH = "both"


@dataclass(frozen=True)
class Intent:
    """What kind of question this is, and what that implies for the prompt."""
    kind: str = INTENT_LOOKUP
    needs_time_resolution: bool = False   # a relative time phrase was detected
    needs_total_row: bool = False         # "total"/"overall"/"grand total"
    wants_breakdown: bool = False         # "by <dimension>", "per <dimension>"
    top_n: int | None = None
    scope: str | None = None              # SCOPE_DOM | SCOPE_OVE | SCOPE_BOTH | None
    rule_packs: tuple = ()                # ids consumed by src.prompting.rule_packs
    signals: tuple = ()                   # the phrases that fired, for the trace

    def to_dict(self) -> dict:
        return asdict(self)


# ── Domain gate ───────────────────────────────────────────────────────────────

GATE_EXPLICIT = "explicit_reference"   # the user named a section/part/return
GATE_INFERRED = "inferred"             # deduced from wording (periodicity, etc.)
GATE_NONE = "none"


@dataclass(frozen=True)
class DomainGate:
    """
    Which slice of the catalog may answer this question.

    Applied as a PRE-filter inside each retrieval channel rather than as a
    re-ordering of a finished global ranking. At 26 tables the difference is
    cosmetic; across multiple returns and 500+ tables it is the difference
    between the correct table being rank 3 and never being retrieved at all.

    An EMPTY `table_allow` means "no constraint" — never "nothing is allowed".
    A gate that would eliminate every candidate must be dropped by whoever built
    it (see domain.py), because an empty candidate set is always worse than an
    unfiltered one.
    """
    returns: frozenset = frozenset()
    sections: frozenset = frozenset()
    parts: frozenset = frozenset()
    table_allow: frozenset = frozenset()   # resolved lowercase table names
    source: str = GATE_NONE
    note: str = ""

    @property
    def active(self) -> bool:
        return bool(self.table_allow)

    def allows(self, table: str) -> bool:
        if not self.table_allow:
            return True
        return table.lower() in self.table_allow

    def to_dict(self) -> dict:
        return {
            "returns": sorted(self.returns),
            "sections": sorted(self.sections),
            "parts": sorted(self.parts),
            "table_allow": sorted(self.table_allow),
            "source": self.source,
            "note": self.note,
        }


# ── Evidence from retrieval ───────────────────────────────────────────────────

# ColumnBinding origins, strongest first. `concept` outranks the rest because a
# concept hit resolves one (table, column) through a mapping verified by a
# deterministic 4-hop join — it is an answer, not a vote. The pre-context
# pipeline threw that column away and kept only the table vote.
ORIGIN_CONCEPT = "concept"
ORIGIN_SEMANTIC_LAYER = "semantic_layer"
ORIGIN_QA_SQL = "qa_sql"
ORIGIN_BM25 = "bm25"
ORIGIN_COLUMN_INDEX = "column_index"

# Origins whose column identity is trustworthy enough to PIN a table, not merely
# vote for it.
VERIFIED_ORIGINS = frozenset({ORIGIN_CONCEPT, ORIGIN_SEMANTIC_LAYER})


@dataclass(frozen=True)
class ColumnBinding:
    """A claim that `table.column` is what the question is asking for."""
    table: str
    column: str
    confidence: float = 0.0
    origin: str = ORIGIN_COLUMN_INDEX
    # (label_column, literal) when the mapping certifies that a specific row
    # selects this metric. Only set for narrow key-value tables, where naming
    # the column alone would be useless because every metric lives in one VALUE
    # column and the row identifies which metric it is.
    row_selector: tuple | None = None
    why: str = ""

    @property
    def key(self) -> tuple:
        return (self.table.lower(), self.column.lower())

    @property
    def verified(self) -> bool:
        return self.origin in VERIFIED_ORIGINS

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class LabelBinding:
    """One row-label literal that the question plausibly needs."""
    table: str
    column: str
    value: str
    confidence: float = 0.0
    needs_trim: bool = False
    is_total_row: bool = False
    origin: str = ORIGIN_COLUMN_INDEX

    @property
    def key(self) -> tuple:
        return (self.table.lower(), self.column.lower(), self.value)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class QAExample:
    """A prior question with verified SQL, for few-shot grounding."""
    question: str
    sql: str
    table: str
    score: float = 0.0              # embedding cosine
    text_similarity: float = 0.0    # literal character overlap
    token_similarity: float = 0.0   # token-set / paraphrase overlap
    shape: str = ""                 # vertical_filter|union_all|window|plain — see examples.py

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Evidence:
    """
    What fusion hands the resolver. Deliberately TYPED and un-collapsed: the
    pre-context retriever reduced six signals to one float per table, which
    threw away exactly the information the resolver needs (which column, which
    literal, which example shape).
    """
    table_votes: tuple = ()          # ((table, fused_score), ...) rank order
    column_bindings: tuple = ()      # (ColumnBinding, ...) confidence order
    label_bindings: tuple = ()       # (LabelBinding, ...) confidence order
    examples: tuple = ()             # (QAExample, ...) best first
    pinned_table: str | None = None  # strong QA paraphrase or explicit section ref
    pin_reason: str = ""
    gate: DomainGate = field(default_factory=DomainGate)

    def bindings_for(self, table: str) -> tuple:
        low = table.lower()
        return tuple(b for b in self.column_bindings if b.table.lower() == low)

    def labels_for(self, table: str) -> tuple:
        low = table.lower()
        return tuple(l for l in self.label_bindings if l.table.lower() == low)

    def to_dict(self) -> dict:
        return {
            "table_votes": [list(v) for v in self.table_votes],
            "column_bindings": [b.to_dict() for b in self.column_bindings],
            "label_bindings": [l.to_dict() for l in self.label_bindings],
            "examples": [e.to_dict() for e in self.examples],
            "pinned_table": self.pinned_table,
            "pin_reason": self.pin_reason,
            "gate": self.gate.to_dict(),
        }


# ── The slice ─────────────────────────────────────────────────────────────────

# Why a column survived slicing. Carried through to the trace so a wrong answer
# can be diagnosed as "the right column was dropped" vs "the right column was
# never bound".
ROLE_KEY = "key"              # CODE / RDATE / declared PK — never dropped
ROLE_LABEL = "label"          # the row-label column of a vertical table
ROLE_BOUND = "bound"          # a ColumnBinding named it
ROLE_SIBLING = "sibling"      # _DOM/_OVE partner of a bound column
ROLE_EVIDENCE = "evidence"    # retrieved, but not bound
ROLE_CORE = "core"            # fallback: a core metric of the table


@dataclass(frozen=True)
class SlicedColumn:
    name: str
    type: str = ""
    description: str = ""
    nullable: bool = True
    is_primary_key: bool = False
    role: str = ROLE_EVIDENCE
    score: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class TableSlice:
    """
    The minimum useful view of ONE physical table: the columns the question
    needs, the row labels it needs, and the shape facts the prompt has to state
    (vertical? which total row? padded values? what unit?).
    """
    table: str
    columns: tuple = ()               # (SlicedColumn, ...) in render order
    labels: tuple = ()                # (LabelBinding, ...) capped and ranked
    label_columns: frozenset = frozenset()   # lowercase, the vertical keys
    is_vertical: bool = False
    total_row: str | None = None
    needs_trim: frozenset = frozenset()      # lowercase column names
    unit_multiplier: int | None = None
    description: str = ""
    dropped_columns: int = 0          # how many the slicer removed
    total_columns: int = 0            # how many the table actually has

    @property
    def column_names(self) -> tuple:
        return tuple(c.name for c in self.columns)

    def labels_by_column(self) -> dict:
        """{column_lower: [value, ...]} — the shape build_table_ddl expects."""
        out: dict = {}
        for lbl in self.labels:
            out.setdefault(lbl.column.lower(), []).append(lbl.value)
        return out

    def to_dict(self) -> dict:
        return {
            "table": self.table,
            "columns": [c.to_dict() for c in self.columns],
            "labels": [l.to_dict() for l in self.labels],
            "label_columns": sorted(self.label_columns),
            "is_vertical": self.is_vertical,
            "total_row": self.total_row,
            "needs_trim": sorted(self.needs_trim),
            "unit_multiplier": self.unit_multiplier,
            "dropped_columns": self.dropped_columns,
            "total_columns": self.total_columns,
        }


# ── Budget accounting ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Drop:
    """One thing the budget removed, and why. Silent truncation is what made the
    old blind 14-label cut invisible; a reported drop is auditable."""
    axis: str        # columns|labels|examples|semantics|rules|tables
    item: str
    reason: str      # over_budget|low_confidence|out_of_scope


@dataclass(frozen=True)
class BudgetReport:
    drops: tuple = ()
    est_tokens: int = 0
    over_budget: bool = False
    low_binding: bool = False   # nothing was confidently bound; the slice is a guess

    def to_dict(self) -> dict:
        return {
            "drops": [asdict(d) for d in self.drops],
            "est_tokens": self.est_tokens,
            "over_budget": self.over_budget,
            "low_binding": self.low_binding,
        }


# ── The prompt context ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PromptContext:
    """
    The ONLY input to prompt rendering. If it is not here, it cannot reach the
    model.
    """
    question: str
    intent: Intent
    slices: tuple = ()
    join_hint: str | None = None
    examples: tuple = ()
    rule_packs: tuple = ()
    semantics: tuple = ()          # rendered business-semantics lines
    semantic_rules: tuple = ()     # business-semantics lines that belong in RULES
    time_block: str | None = None
    confidence: float = 0.0
    budget_report: BudgetReport = field(default_factory=BudgetReport)
    trace: tuple = ()

    @property
    def table_names(self) -> tuple:
        return tuple(s.table for s in self.slices)

    def slice_for(self, table: str):
        low = table.lower()
        return next((s for s in self.slices if s.table.lower() == low), None)

    def with_trace(self, *lines: str) -> "PromptContext":
        return replace(self, trace=self.trace + tuple(lines))

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "intent": self.intent.to_dict(),
            "slices": [s.to_dict() for s in self.slices],
            "join_hint": self.join_hint,
            "examples": [e.to_dict() for e in self.examples],
            "rule_packs": list(self.rule_packs),
            "semantics": list(self.semantics),
            "semantic_rules": list(self.semantic_rules),
            "time_block": self.time_block,
            "confidence": self.confidence,
            "budget_report": self.budget_report.to_dict(),
            "trace": list(self.trace),
        }
