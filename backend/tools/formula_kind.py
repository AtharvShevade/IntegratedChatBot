# backend/tools/formula_kind.py — what KIND of check a parsed formula is.
#
# WHY THIS EXISTS
# ---------------
# The card's wording was driven by a single test, formula_error._is_combination:
#
#     len(rhs_vars) > 1 or rhs.uses_aggregation()
#
# which is true for a genuine sum AND for a ratio like `$V1 div ($V5 + $V6)`.
# Everything downstream then spoke about "the sum of its parts" and "the
# combined value", so a ratio, a percentage, a weighted average and a
# conditional were all described as if they were additions:
#
#     "Net inflow outflow … is ₹0.0021 higher than the sum of its parts."
#     "Liquidity Coverage Ratio is 1.9969 higher than the sum of its parts."
#
# Both statements are wrong about what the rule does, even though the numbers
# behind them are right.
#
# This module answers "what shape is this rule?" from the AST alone. It is
# STRICTLY READ-ONLY: it never evaluates, never mutates a node, never touches a
# fact, and never influences a verdict. Its output only selects wording.
#
# Anything it cannot classify confidently returns UNKNOWN, and every caller
# treats UNKNOWN as "keep the previous behaviour" — so an unrecognised shape
# degrades to exactly what shipped before this module existed.

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

__all__ = [
    "AGGREGATE", "RATIO", "PERCENTAGE", "WEIGHTED_AVERAGE", "EQUALITY",
    "THRESHOLD", "COUNT", "MANDATORY", "CONDITIONAL", "UNKNOWN",
    "classify", "result_subject", "expected_column", "is_unitless",
    "describes_a_calculation", "absent_operand_means", "business_node",
]

AGGREGATE = "aggregate"
RATIO = "ratio"
PERCENTAGE = "percentage"
WEIGHTED_AVERAGE = "weighted_average"
EQUALITY = "equality"
THRESHOLD = "threshold"
COUNT = "count"
MANDATORY = "mandatory"
CONDITIONAL = "conditional"
UNKNOWN = "unknown"


# ─────────────────────────────────────────────────────────────────────────────
# AST inspection helpers — all read-only walks over FormulaNode
# ─────────────────────────────────────────────────────────────────────────────

# Wrappers that do not change what a rule IS. `abs` is included here (unlike in
# FormulaNode.core(), which this module deliberately does not touch) because
# `abs(($V1 div $V2) * 10000)` is still a ratio, and the classification must see
# through the wrapper to say so.
_WRAPPER_FUNCS = frozenset({"round", "floor", "ceiling", "number", "abs"})


def _walk(node):
    if node is None:
        return
    yield node
    for arg in getattr(node, "args", None) or ():
        yield from _walk(arg)


def _has_func(nodes, name: str) -> bool:
    return any(
        n.kind == "func" and n.name == name
        for root in nodes for n in _walk(root)
    )


def _has_kind(nodes, kind: str) -> bool:
    return any(n.kind == kind for root in nodes for n in _walk(root))


def _strip_wrappers(node):
    """Peel rounding / abs / constant-scaling wrappers to reach the operand
    tree that carries the rule's meaning.

    `round(($V1 div ($V5+$V6)) * 10000) div 10000`  ->  `$V1 div ($V5+$V6)`

    This is a LOCAL copy of the idea in FormulaNode.core(), kept here so this
    module can see through `abs` without altering core()'s behaviour — core()
    feeds the raw-vs-rounded display pair and is out of scope.
    """
    seen = 0
    while node is not None and seen < 64:      # depth guard, never a real limit
        seen += 1
        if node.kind == "func" and node.name in _WRAPPER_FUNCS and node.args:
            node = node.args[0]
            continue
        if node.kind == "binop" and node.op in ("*", "div", "idiv") and len(node.args) == 2:
            left, right = node.args
            # Scaling by a literal only — a division by a VARIABLE is the rule
            # itself and must never be stripped.
            if right.kind == "num" and left.variables():
                node = left
                continue
            if left.kind == "num" and right.variables() and node.op == "*":
                node = right
                continue
        return node
    return node


def _additive_terms(node) -> list:
    """A '+'/'-' chain flattened into its operand nodes (signs discarded — this
    is about shape, not value)."""
    if node is None:
        return []
    if node.kind == "binop" and node.op in ("+", "-"):
        return _additive_terms(node.args[0]) + _additive_terms(node.args[1])
    if node.kind == "unary":
        return _additive_terms(node.args[0]) if node.args else []
    return [node]


def _has_literal_factor(node, target) -> bool:
    """True when *target* appears as a multiplier anywhere in the subtree —
    the `* 100` that makes an expression a percentage rather than a plain
    ratio."""
    for n in _walk(node):
        if n.kind == "binop" and n.op == "*" and len(n.args) == 2:
            for side in n.args:
                if side.kind == "num" and side.value is not None:
                    try:
                        if side.value == target:
                            return True
                    except (TypeError, ArithmeticError):
                        continue
    return False


def _is_weighted_average(numerator, denominator) -> bool:
    """`((A*w1) + (B*w2)) div (A + B)` — every numerator term is a product, and
    each product carries one of the variables the denominator adds up.

    Requiring the overlap is what separates a weighted average from an
    unrelated division of two sums.
    """
    denominator_vars = set(denominator.variables())
    if len(denominator_vars) < 2:
        return False
    terms = _additive_terms(numerator)
    if len(terms) < 2:
        return False
    for term in terms:
        term = _strip_wrappers(term)
        if term.kind != "binop" or term.op != "*":
            return False
        if not (set(term.variables()) & denominator_vars):
            return False
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Classification
# ─────────────────────────────────────────────────────────────────────────────

def classify(comparison) -> str:
    """The kind of check *comparison* expresses, or UNKNOWN.

    Never raises: an unexpected AST shape yields UNKNOWN, and callers keep
    their previous wording for UNKNOWN.
    """
    if comparison is None:
        return UNKNOWN
    try:
        return _classify(comparison)
    except Exception as exc:                    # pragma: no cover - safety net
        logger.debug("[formula_kind] classification failed for %r: %s",
                     getattr(comparison, "source", ""), exc)
        return UNKNOWN


def _classify(comparison) -> str:
    lhs = comparison.lhs
    rhs = comparison.rhs
    sides = [n for n in (lhs, rhs) if n is not None]

    # Presence / emptiness checks first: `not(empty($V1))` is a mandatory-field
    # rule whatever else surrounds it.
    if _has_func(sides, "empty"):
        return MANDATORY
    if _has_func(sides, "count"):
        return COUNT
    if _has_kind(sides, "if"):
        return CONDITIONAL

    operator = comparison.operator or ""
    if not operator:
        # A boolean expression with no comparison and no empty()/count()/if —
        # nothing specific can be claimed about its shape.
        return UNKNOWN
    if operator in (">", ">=", "<", "<="):
        return THRESHOLD
    if operator not in ("=", "!=", "<>") or rhs is None:
        return UNKNOWN

    core = _strip_wrappers(rhs)

    if core.kind == "binop" and core.op in ("div", "idiv") and len(core.args) == 2:
        numerator, denominator = core.args
        if not denominator.variables():
            # Division by a constant the stripper did not remove — not a ratio
            # between two reported figures.
            return UNKNOWN
        if _is_weighted_average(numerator, denominator):
            return WEIGHTED_AVERAGE
        if _has_literal_factor(numerator, 100):
            return PERCENTAGE
        if numerator.variables():
            return RATIO
        return UNKNOWN

    if rhs.uses_aggregation() or len(core.signed_variables()) > 1:
        return AGGREGATE

    if len(rhs.variables()) == 1 and len(lhs.variables()) == 1:
        return EQUALITY

    return UNKNOWN


# ─────────────────────────────────────────────────────────────────────────────
# Wording
#
# "" always means "this kind has nothing better to offer than what the caller
# already does" — callers must treat it as keep-existing-behaviour, never as
# text to print.
# ─────────────────────────────────────────────────────────────────────────────

_SUBJECTS = {
    AGGREGATE:        "the sum of the component values",
    RATIO:            "the calculated ratio",
    PERCENTAGE:       "the calculated percentage",
    WEIGHTED_AVERAGE: "the calculated weighted average",
    CONDITIONAL:      "the value this rule calculates",
    COUNT:            "the required number of values",
}

_EXPECTED_COLUMNS = {
    AGGREGATE:        "Calculated total",
    RATIO:            "Calculated ratio",
    PERCENTAGE:       "Calculated percentage",
    WEIGHTED_AVERAGE: "Calculated weighted average",
    CONDITIONAL:      "Calculated value",
    COUNT:            "Required count",
    EQUALITY:         "Expected value",
}

# Kinds whose result is a pure number. A ratio of two rupee amounts is not
# rupees, and printing it as ₹0.03 misstates what the figure is.
_UNITLESS = frozenset({RATIO, PERCENTAGE, WEIGHTED_AVERAGE})

# Kinds where showing the substituted arithmetic helps. Equality and threshold
# are excluded: "₹100 = ₹100" restates the row above it and adds nothing.
_CALCULATED = frozenset({AGGREGATE, RATIO, PERCENTAGE, WEIGHTED_AVERAGE, CONDITIONAL})


def result_subject(kind: str) -> str:
    """How to refer to the right-hand side in prose, or "" to keep the
    caller's existing wording."""
    return _SUBJECTS.get(kind, "")


def expected_column(kind: str) -> str:
    """Label for the expected/calculated side, or "" to keep the caller's."""
    return _EXPECTED_COLUMNS.get(kind, "")


def is_unitless(kind: str) -> bool:
    return kind in _UNITLESS


def describes_a_calculation(kind: str) -> bool:
    return kind in _CALCULATED


def business_node(node):
    """The operand tree with the rule's internal scaling and abs() peeled off —
    what the rule means at business level.

    `round(abs(($V1 div $V2) * 10000)) div 10000` -> `$V1 div $V2`

    The × 10,000 in that expression exists to make fn:round truncate at four
    decimals; it is a precision device, not part of the ratio. Showing it in the
    user-facing calculation made the reader read 279.0095 as the ratio.

    Read-only, and NOT a replacement for FormulaNode.core(): core() feeds the
    engine's raw-vs-rounded pair and is untouched. This is for display only.
    """
    return _strip_wrappers(node) if node is not None else node


def absent_operand_means(kind: str) -> str:
    """What an operand with NO row in the error file means for this kind.

    "required"    the rule exists to demand it — say it was not reported
    "unavailable" the rule needs it to compute a result — say the validation
                  output does not carry it, and do not pretend it is zero
    """
    return "required" if kind in (MANDATORY, COUNT) else "unavailable"
