# backend/tools/formula_expression.py — XBRL formula test-expression parser + evaluator.
#
# Replaces keyword-sniffing formula "classification" (contains "+" -> sum check,
# contains "round" -> ratio check) with an actual grammar. That classification
# approach cannot represent the expressions the real corpus contains, e.g.
#
#     round($V1 * 10) div 10 = round(($V2 + $V3 - $V4) * 10) div 10
#     round($V1 div 1000) * 1000 = round((sum ($V2)) div 1000 ) * 1000
#     $V1 = $V2 + $V3 - $V4
#     $V1 = sum ( $V2 )
#     not(empty( $V1))
#
# and mis-evaluates every one of them (subtraction summed as addition, rounding
# dropped, sum() collapsed to a single fact).
#
# Grammar (exactly the surface actually observed across the Instance corpus):
#
#     expr    := cmp
#     cmp     := add ( ('='|'!='|'<>'|'>='|'<='|'>'|'<') add )?
#     add     := mul ( ('+'|'-') mul )*
#     mul     := unary ( ('*'|'div'|'idiv'|'mod') unary )*
#     unary   := ('-'|'+')? primary
#     primary := NUMBER | '$'VAR | FUNC '(' args ')' | '(' expr ')'
#     FUNC    := sum | round | abs | min | max | count | number | not | empty
#
# Design rules this module holds to:
#   * Every number is a Decimal, never a float — regulatory values run to 12+
#     significant digits and float rounding flips pass/fail at the boundary.
#   * A variable binds to a LIST of facts, never a single one. Collapsing
#     duplicates is the bug that made sum($V2) over [177, 14, 3] evaluate as 3.
#   * Anything the grammar doesn't cover evaluates to MISSING, which propagates
#     to the top and makes the caller fall back to an evidence-only explanation.
#     It never guesses, and it never raises.

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation, localcontext

logger = logging.getLogger(__name__)

__all__ = [
    "MISSING", "Missing", "FormulaNode", "Comparison",
    "parse_formula", "evaluate", "describe",
    "COMPARISON_OPERATORS", "OPERATOR_MEANING",
]


# ─────────────────────────────────────────────────────────────────────────────
# Missing sentinel — "this operand had no usable value in the error file".
# Distinct from Decimal(0): a fact reported as 0 is a real 0, an absent fact is
# not, and the two must never be conflated in a difference calculation.
# ─────────────────────────────────────────────────────────────────────────────

class Missing:
    __slots__ = ()
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "MISSING"

    def __bool__(self) -> bool:
        return False


MISSING = Missing()

COMPARISON_OPERATORS = (">=", "<=", "<>", "!=", "=", ">", "<")

OPERATOR_MEANING = {
    "=":  "equal to",
    "<>": "not equal to",
    "!=": "not equal to",
    ">":  "greater than",
    ">=": "greater than or equal to",
    "<":  "less than",
    "<=": "less than or equal to",
}

_OPERATOR_FN = {
    "=":  lambda a, b: a == b,
    "<>": lambda a, b: a != b,
    "!=": lambda a, b: a != b,
    ">":  lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "<":  lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
}

# Functions this evaluator understands. Anything else parses (so the AST still
# shows the shape) but evaluates to MISSING rather than being silently ignored.
_KNOWN_FUNCTIONS = frozenset({
    "sum", "round", "abs", "min", "max", "count", "number", "not", "empty",
    "string-length", "normalize-space", "floor", "ceiling",
})


# ─────────────────────────────────────────────────────────────────────────────
# Tokenizer
# ─────────────────────────────────────────────────────────────────────────────

_TOKEN_RE = re.compile(
    r"""
      (?P<ws>\s+)
    | (?P<number>\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)
    | (?P<var>\$\s*[A-Za-z_][A-Za-z0-9_]*)
    | (?P<string>'[^']*'|"[^"]*")
    | (?P<name>[A-Za-z_][A-Za-z0-9_.\-]*)
    | (?P<op>>=|<=|<>|!=|=|>|<|\+|-|\*|/|\(|\)|,)
    """,
    re.VERBOSE,
)

# Word-operators in XPath are spelled as names, so the tokenizer emits them as
# NAME and this set promotes them to OP at parse time.
_WORD_OPERATORS = frozenset({"div", "idiv", "mod", "and", "or", "eq", "ne",
                             "lt", "le", "gt", "ge"})

# Conditional keywords. A meaningful share of the corpus states its rule
# conditionally ("if the denominator is 0 then the ratio must be 0, else …"),
# and refusing those expressions outright loses a real verdict.
_KEYWORDS = frozenset({"if", "then", "else"})

_WORD_OPERATOR_ALIAS = {
    "eq": "=", "ne": "!=", "lt": "<", "le": "<=", "gt": ">", "ge": ">=",
}


@dataclass(frozen=True)
class _Token:
    kind: str   # "NUMBER" | "VAR" | "NAME" | "OP" | "END"
    text: str
    pos: int


def _tokenize(text: str) -> list[_Token] | None:
    tokens: list[_Token] = []
    i, n = 0, len(text)
    while i < n:
        m = _TOKEN_RE.match(text, i)
        if not m:
            # An unrecognised character means this expression uses syntax we
            # have not modelled. Refuse the whole parse rather than skipping
            # it and producing a subtly wrong AST.
            logger.debug("[formula_expression] unexpected char %r at %d in %r",
                         text[i], i, text)
            return None
        i = m.end()
        kind = m.lastgroup
        if kind == "ws":
            continue
        raw = m.group()
        if kind == "number":
            tokens.append(_Token("NUMBER", raw, m.start()))
        elif kind == "var":
            tokens.append(_Token("VAR", raw[1:].strip().upper(), m.start()))
        elif kind == "string":
            tokens.append(_Token("STRING", raw[1:-1], m.start()))
        elif kind == "name":
            low = raw.lower()
            if low in _KEYWORDS:
                tokens.append(_Token("KEYWORD", low, m.start()))
            elif low in _WORD_OPERATORS:
                tokens.append(_Token("OP", _WORD_OPERATOR_ALIAS.get(low, low), m.start()))
            else:
                tokens.append(_Token("NAME", raw, m.start()))
        else:
            op = raw
            if op == "/":
                op = "div"      # some authors write '/' for division
            tokens.append(_Token("OP", op, m.start()))
    tokens.append(_Token("END", "", n))
    return tokens


# ─────────────────────────────────────────────────────────────────────────────
# AST
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class FormulaNode:
    """One node of the parsed expression.

    kind:
        "num"   value: Decimal
        "var"   name:  "V1"
        "func"  name:  "round" / "sum" / ...   args: [FormulaNode]
        "unary" op:    "-"                     args: [FormulaNode]
        "binop" op:    "+" "-" "*" "div" ...   args: [lhs, rhs]
    """
    kind: str
    op: str = ""
    name: str = ""
    value: Decimal | None = None
    args: list["FormulaNode"] = field(default_factory=list)

    # ── introspection used by the renderer/LLM payload ────────────────────
    def variables(self) -> list[str]:
        """Variable ids referenced by this subtree, in first-appearance order."""
        seen: list[str] = []

        def walk(node: "FormulaNode") -> None:
            if node.kind == "var":
                if node.name not in seen:
                    seen.append(node.name)
            for a in node.args:
                walk(a)

        walk(self)
        return seen

    def signed_variables(self, sign: int = 1) -> list[tuple[str, int]]:
        """(variable, +1/-1) pairs — the sign each variable carries within this
        subtree's additive structure. This is what makes "$V2 + $V3 - $V4"
        render as three terms with the right signs instead of a blind sum.

        Returns [] when the subtree isn't purely additive over variables (e.g.
        a division), because there is then no honest per-term sign to report.
        """
        if self.kind == "var":
            return [(self.name, sign)]
        if self.kind == "unary" and self.op == "-":
            return self.args[0].signed_variables(-sign)
        if self.kind == "unary":
            return self.args[0].signed_variables(sign)
        if self.kind == "binop" and self.op in ("+", "-"):
            lhs = self.args[0].signed_variables(sign)
            rhs = self.args[1].signed_variables(sign if self.op == "+" else -sign)
            if lhs is None or rhs is None:
                return []
            return lhs + rhs
        if self.kind == "func" and self.name in ("sum", "round", "abs", "number",
                                                 "floor", "ceiling"):
            # These wrap without altering the additive sign of what's inside.
            inner: list[tuple[str, int]] = []
            for a in self.args:
                inner.extend(a.signed_variables(sign))
            return inner
        if self.kind == "binop" and self.op in ("*", "div", "idiv"):
            # Scaling by a constant (the "round(X div 100000) * 100000"
            # idiom that dominates this corpus) preserves each term's sign,
            # so the additive structure underneath stays reportable. Scaling
            # by anything variable does not, and yields no signed terms.
            left, right = self.args
            if right.kind == "num" and not left.variables():
                return []
            if right.kind == "num":
                return left.signed_variables(sign)
            if left.kind == "num" and self.op == "*":
                return right.signed_variables(sign)
        return []

    def core(self) -> "FormulaNode":
        """The meaningful operand tree with rounding/constant-scaling wrappers
        peeled off — 'round($V1 div 100000) * 100000' reduces to '$V1'.

        Used only for human-readable rendering: the scaling is an artefact of
        how the rule expresses its tolerance, not something a reader needs to
        see. The tolerance itself is reported separately (see
        rounding_scale()), so nothing is hidden, only relocated."""
        node = self
        while True:
            if node.kind == "func" and node.name in ("round", "floor", "ceiling", "number") and node.args:
                node = node.args[0]
                continue
            if node.kind == "binop" and node.op in ("*", "div", "idiv"):
                left, right = node.args
                if right.kind == "num" and left.variables():
                    node = left
                    continue
                if left.kind == "num" and right.variables() and node.op == "*":
                    node = right
                    continue
            return node

    def rounding_scale(self) -> Decimal | None:
        """The effective comparison tolerance implied by a
        'round(X div N) * N' or 'round(X * N) div N' wrapper, as a Decimal
        step — N and 1/N respectively. None when the expression rounds in a
        shape we can't state exactly, or doesn't round at all; the caller then
        just says values are compared after rounding, without a figure."""
        def scan(n: "FormulaNode") -> Decimal | None:
            if n.kind == "binop" and n.op in ("*", "div", "idiv"):
                left, right = n.args
                inner = left if left.kind != "num" else right
                factor = right if right.kind == "num" else (left if left.kind == "num" else None)
                if factor is not None and inner.uses_rounding():
                    try:
                        if n.op == "*":
                            return factor.value
                        if factor.value and factor.value != 0:
                            return Decimal(1) / factor.value
                    except (InvalidOperation, TypeError, ArithmeticError):
                        return None
            for a in n.args:
                found = scan(a)
                if found is not None:
                    return found
            return None

        return scan(self) if self.uses_rounding() else None

    def uses_rounding(self) -> bool:
        if self.kind == "func" and self.name in ("round", "floor", "ceiling"):
            return True
        return any(a.uses_rounding() for a in self.args)

    def uses_aggregation(self) -> bool:
        if self.kind == "func" and self.name in ("sum", "count", "min", "max"):
            return True
        return any(a.uses_aggregation() for a in self.args)


@dataclass
class Comparison:
    """A parsed test expression.

    `operator` is "" for a non-comparison expression (e.g. `not(empty($V1))`),
    in which case only `lhs` is populated and `boolean_only` is True.
    """
    operator: str
    lhs: FormulaNode
    rhs: FormulaNode | None
    source: str
    boolean_only: bool = False

    def variables(self) -> list[str]:
        out = self.lhs.variables()
        if self.rhs is not None:
            for v in self.rhs.variables():
                if v not in out:
                    out.append(v)
        return out

    @property
    def lhs_vars(self) -> list[str]:
        return self.lhs.variables()

    @property
    def rhs_vars(self) -> list[str]:
        return self.rhs.variables() if self.rhs is not None else []


# ─────────────────────────────────────────────────────────────────────────────
# Recursive-descent parser
# ─────────────────────────────────────────────────────────────────────────────

class _Parser:
    def __init__(self, tokens: list[_Token]) -> None:
        self.tokens = tokens
        self.i = 0

    def peek(self) -> _Token:
        return self.tokens[self.i]

    def next(self) -> _Token:
        tok = self.tokens[self.i]
        self.i += 1
        return tok

    def accept_op(self, *ops: str) -> str | None:
        tok = self.peek()
        if tok.kind == "OP" and tok.text in ops:
            self.next()
            return tok.text
        return None

    def accept_keyword(self, word: str) -> bool:
        tok = self.peek()
        if tok.kind == "KEYWORD" and tok.text == word:
            self.next()
            return True
        return False

    def expect_keyword(self, word: str) -> None:
        if not self.accept_keyword(word):
            raise _ParseError(f"expected {word!r}")

    # expr := ifexpr | orexpr
    def parse_expr(self) -> FormulaNode:
        if self.accept_keyword("if"):
            if self.accept_op("(") is None:
                raise _ParseError("expected '(' after if")
            condition = self.parse_expr()
            if self.accept_op(")") is None:
                raise _ParseError("unbalanced parenthesis in if-condition")
            self.expect_keyword("then")
            then_branch = self.parse_expr()
            self.expect_keyword("else")
            else_branch = self.parse_expr()
            return FormulaNode(kind="if", args=[condition, then_branch, else_branch])
        return self.parse_or()

    def parse_or(self) -> FormulaNode:
        node = self.parse_and()
        while self.accept_op("or"):
            node = FormulaNode(kind="binop", op="or", args=[node, self.parse_and()])
        return node

    def parse_and(self) -> FormulaNode:
        node = self.parse_cmp()
        while self.accept_op("and"):
            node = FormulaNode(kind="binop", op="and", args=[node, self.parse_cmp()])
        return node

    def parse_cmp(self) -> FormulaNode:
        lhs = self.parse_add()
        op = self.accept_op(*COMPARISON_OPERATORS)
        if op is None:
            return lhs
        return FormulaNode(kind="binop", op=op, args=[lhs, self.parse_add()])

    # Top level: a bare comparison keeps its two sides separate (so the
    # explanation can report each), anything richer is carried whole and
    # evaluated to a pass/fail verdict.
    def parse_comparison(self) -> tuple[str, FormulaNode, FormulaNode | None]:
        node = self.parse_expr()
        if node.kind == "binop" and node.op in COMPARISON_OPERATORS:
            return node.op, node.args[0], node.args[1]
        return "", node, None

    def parse_add(self) -> FormulaNode:
        node = self.parse_mul()
        while True:
            op = self.accept_op("+", "-")
            if op is None:
                return node
            node = FormulaNode(kind="binop", op=op, args=[node, self.parse_mul()])

    def parse_mul(self) -> FormulaNode:
        node = self.parse_unary()
        while True:
            op = self.accept_op("*", "div", "idiv", "mod")
            if op is None:
                return node
            node = FormulaNode(kind="binop", op=op, args=[node, self.parse_unary()])

    def parse_unary(self) -> FormulaNode:
        op = self.accept_op("-", "+")
        if op == "-":
            return FormulaNode(kind="unary", op="-", args=[self.parse_unary()])
        if op == "+":
            return self.parse_unary()
        return self.parse_primary()

    def parse_primary(self) -> FormulaNode:
        tok = self.next()
        if tok.kind == "NUMBER":
            try:
                return FormulaNode(kind="num", value=Decimal(tok.text))
            except InvalidOperation as exc:
                raise _ParseError(f"bad number {tok.text!r}") from exc
        if tok.kind == "VAR":
            return FormulaNode(kind="var", name=tok.text)
        if tok.kind == "STRING":
            return FormulaNode(kind="str", name=tok.text)
        if tok.kind == "NAME":
            name = tok.text.lower()
            if self.accept_op("(") is None:
                raise _ParseError(f"bare name {tok.text!r} is not callable")
            args: list[FormulaNode] = []
            if self.accept_op(")") is None:
                while True:
                    args.append(self.parse_expr())
                    if self.accept_op(",") is not None:
                        continue
                    if self.accept_op(")") is not None:
                        break
                    raise _ParseError("unterminated argument list")
            return FormulaNode(kind="func", name=name, args=args)
        if tok.kind == "OP" and tok.text == "(":
            # A parenthesised group may hold any expression, including a
            # comparison or a conditional.
            inner = self.parse_expr()
            if self.accept_op(")") is None:
                raise _ParseError("unbalanced parenthesis")
            return inner
        raise _ParseError(f"unexpected token {tok.kind}:{tok.text!r}")


class _ParseError(ValueError):
    pass


def parse_formula(expression: str) -> Comparison | None:
    """Parse one test expression. None when the expression is empty or uses
    syntax outside the modelled grammar — callers must then fall back to an
    evidence-only explanation rather than guessing at the structure."""
    text = (expression or "").strip()
    if not text:
        return None

    tokens = _tokenize(text)
    if tokens is None:
        return None

    parser = _Parser(tokens)
    try:
        operator, lhs, rhs = parser.parse_comparison()
    except (_ParseError, IndexError) as exc:
        logger.debug("[formula_expression] parse failed for %r: %s", text, exc)
        return None

    if parser.peek().kind != "END":
        logger.debug("[formula_expression] trailing input in %r at %d",
                     text, parser.peek().pos)
        return None

    if not lhs.variables() and (rhs is None or not rhs.variables()):
        return None  # nothing to bind facts to — not a usable rule

    return Comparison(
        operator=operator,
        lhs=lhs,
        rhs=rhs,
        source=text,
        boolean_only=not operator,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Evaluation
# ─────────────────────────────────────────────────────────────────────────────

def _to_decimal(raw) -> Decimal | Missing:
    """Parse one reported fact value. Returns MISSING — never 0 — for blanks
    and for the non-numeric junk the corpus actually contains ('#DIV/0!',
    'NA', '-84.55ab', '6,032' with a thousands separator is accepted)."""
    if raw is None:
        return MISSING
    if isinstance(raw, Decimal):
        return raw
    if isinstance(raw, bool):
        return MISSING
    if isinstance(raw, (int, float)):
        try:
            return Decimal(str(raw))
        except InvalidOperation:
            return MISSING
    text = str(raw).strip()
    if not text:
        return MISSING
    text = text.replace(",", "").replace(" ", "")
    if text.upper() in ("INF", "-INF", "NAN", "NA", "N/A"):
        return MISSING
    try:
        value = Decimal(text)
    except InvalidOperation:
        return MISSING
    if not value.is_finite():
        return MISSING
    return value


def _round_half_up(value: Decimal) -> Decimal:
    """XPath fn:round — half rounds toward positive infinity, which is not
    Python's default (banker's) rounding and not ROUND_HALF_UP for negatives
    either. -2.5 must round to -2, not -3."""
    floor_ = value.to_integral_value(rounding="ROUND_FLOOR")
    if value - floor_ >= Decimal("0.5"):
        return floor_ + 1
    return floor_


@dataclass
class _EvalState:
    facts_by_var: dict[str, list[Decimal]]
    fact_counts: dict[str, int]
    raw_by_var: dict[str, list[str]] = field(default_factory=dict)
    missing_vars: set[str] = field(default_factory=set)
    unsupported: set[str] = field(default_factory=set)


def _eval_node(node: FormulaNode, state: _EvalState):
    if node.kind == "num":
        return node.value

    if node.kind == "str":
        return node.name

    if node.kind == "if":
        condition = _eval_node(node.args[0], state)
        if isinstance(condition, Missing):
            return MISSING
        return _eval_node(node.args[1] if bool(condition) else node.args[2], state)

    if node.kind == "var":
        values = state.facts_by_var.get(node.name)
        if not values:
            # A fact whose value is not a number is still a value: some rules
            # compare a reported code or category against a string literal.
            raw = [r for r in state.raw_by_var.get(node.name, []) if str(r).strip()]
            if len(raw) == 1:
                return str(raw[0]).strip()
            state.missing_vars.add(node.name)
            return MISSING
        # A variable bound to several facts folds to their sum — the same
        # aggregation the validator performs when a variable's fact set has
        # more than one member. fact_count is kept so the renderer can say
        # "3 reported values" instead of silently presenting one number.
        total = Decimal(0)
        for v in values:
            total += v
        return total

    if node.kind == "unary":
        inner = _eval_node(node.args[0], state)
        if isinstance(inner, Missing):
            return MISSING
        if node.op == "-":
            return -inner
        return inner

    if node.kind == "binop":
        if node.op in ("and", "or"):
            left = _eval_node(node.args[0], state)
            right = _eval_node(node.args[1], state)
            if isinstance(left, Missing) or isinstance(right, Missing):
                return MISSING
            return (bool(left) and bool(right)) if node.op == "and" else (bool(left) or bool(right))

        left = _eval_node(node.args[0], state)
        right = _eval_node(node.args[1], state)
        if isinstance(left, Missing) or isinstance(right, Missing):
            return MISSING
        if node.op in COMPARISON_OPERATORS:
            fn = _OPERATOR_FN.get(node.op)
            if fn is None:
                return MISSING
            # Comparing a number with a string is not a meaningful ordering;
            # equality still is, so only equality is allowed across types.
            if isinstance(left, str) != isinstance(right, str):
                if node.op in ("=", "!=", "<>"):
                    return fn(str(left), str(right))
                return MISSING
            return fn(left, right)
        if isinstance(left, str) or isinstance(right, str):
            return MISSING
        try:
            with localcontext() as ctx:
                ctx.prec = 40
                if node.op == "+":
                    return left + right
                if node.op == "-":
                    return left - right
                if node.op == "*":
                    return left * right
                if node.op in ("div", "idiv"):
                    if right == 0:
                        return MISSING          # 0-divide is a data problem, not a number
                    result = left / right
                    return result.to_integral_value(rounding="ROUND_DOWN") if node.op == "idiv" else result
                if node.op == "mod":
                    if right == 0:
                        return MISSING
                    return left % right
        except (InvalidOperation, ArithmeticError) as exc:
            logger.debug("[formula_expression] arithmetic failed on %s: %s", node.op, exc)
            return MISSING
        state.unsupported.add(node.op)
        return MISSING

    if node.kind == "func":
        return _eval_func(node, state)

    return MISSING


def _eval_func(node: FormulaNode, state: _EvalState):
    name = node.name

    if name not in _KNOWN_FUNCTIONS:
        state.unsupported.add(name)
        return MISSING

    # empty()/count() must inspect the fact SET, not a folded value, so they
    # are handled before the generic argument evaluation below.
    if name in ("empty", "count"):
        total = 0
        for arg in node.args:
            for var in arg.variables():
                total += state.fact_counts.get(var, 0)
        return (total == 0) if name == "empty" else Decimal(total)

    if name == "not":
        if not node.args:
            return MISSING
        inner = _eval_node(node.args[0], state)
        if isinstance(inner, Missing):
            return MISSING
        return not bool(inner)

    if name == "sum":
        total = Decimal(0)
        saw_any = False
        for arg in node.args:
            if arg.kind == "var":
                values = state.facts_by_var.get(arg.name)
                if not values:
                    state.missing_vars.add(arg.name)
                    continue
                saw_any = True
                for v in values:
                    total += v
            else:
                value = _eval_node(arg, state)
                if isinstance(value, Missing):
                    continue
                saw_any = True
                total += value
        return total if saw_any else MISSING

    values = [_eval_node(a, state) for a in node.args]
    if any(isinstance(v, Missing) for v in values):
        return MISSING

    if name in ("round", "floor", "ceiling"):
        if not values:
            return MISSING
        value = values[0]
        if name == "round":
            return _round_half_up(value)
        rounding = "ROUND_FLOOR" if name == "floor" else "ROUND_CEILING"
        return value.to_integral_value(rounding=rounding)
    if name == "abs":
        return abs(values[0]) if values else MISSING
    if name in ("min", "max"):
        return (min(values) if name == "min" else max(values)) if values else MISSING
    if name == "number":
        return values[0] if values else MISSING
    if name in ("string-length", "normalize-space"):
        state.unsupported.add(name)
        return MISSING

    state.unsupported.add(name)
    return MISSING


def evaluate(comparison: Comparison, facts_by_var: dict[str, list]) -> dict | None:
    """Deterministically evaluate one parsed comparison against the facts the
    error file reported. The ONLY place a number or a pass/fail verdict is
    produced — never delegated to an LLM.

    *facts_by_var* maps "V1" -> [raw value, ...]. Raw values may be strings
    straight from the HTML; non-numeric ones are dropped as MISSING rather
    than coerced to 0.

    Returns None when either side could not be resolved to a number, so the
    caller renders an evidence-only explanation instead of inventing one.
    """
    if comparison is None:
        return None

    numeric: dict[str, list[Decimal]] = {}
    counts: dict[str, int] = {}
    unusable: dict[str, list[str]] = {}
    for var, raws in (facts_by_var or {}).items():
        key = str(var).strip().upper()
        parsed: list[Decimal] = []
        bad: list[str] = []
        for raw in (raws if isinstance(raws, (list, tuple)) else [raws]):
            value = _to_decimal(raw)
            if isinstance(value, Missing):
                if str(raw or "").strip():
                    bad.append(str(raw).strip())
                continue
            parsed.append(value)
        counts[key] = len(parsed) + len(bad)
        if parsed:
            numeric[key] = parsed
        if bad:
            unusable[key] = bad

    raw_by_var = {
        str(var).strip().upper(): [str(r) for r in (raws if isinstance(raws, (list, tuple)) else [raws])]
        for var, raws in (facts_by_var or {}).items()
    }
    state = _EvalState(facts_by_var=numeric, fact_counts=counts, raw_by_var=raw_by_var)

    lhs_value = _eval_node(comparison.lhs, state)
    rhs_value = _eval_node(comparison.rhs, state) if comparison.rhs is not None else None

    base = {
        "operator": comparison.operator,
        "operator_meaning": OPERATOR_MEANING.get(comparison.operator, comparison.operator),
        "expression": comparison.source,
        "fact_counts": counts,
        "missing_vars": sorted(state.missing_vars),
        "unusable_values": unusable,
        "uses_rounding": comparison.lhs.uses_rounding() or (
            comparison.rhs.uses_rounding() if comparison.rhs is not None else False
        ),
        "uses_aggregation": comparison.lhs.uses_aggregation() or (
            comparison.rhs.uses_aggregation() if comparison.rhs is not None else False
        ),
    }

    if comparison.boolean_only:
        if isinstance(lhs_value, Missing):
            return None
        passes = bool(lhs_value)
        base.update({
            "boolean_only": True,
            "lhs_value": None,
            "rhs_value": None,
            "difference": None,
            "passes": passes,
            "values_equal": None,
            "relationship": "n/a",
        })
        return base

    if isinstance(lhs_value, Missing) or isinstance(rhs_value, Missing) or rhs_value is None:
        return None
    if isinstance(lhs_value, bool) or isinstance(rhs_value, bool):
        return None
    if isinstance(lhs_value, str) or isinstance(rhs_value, str):
        # A genuine category comparison ("$V3 = 'SCHEDULED BANK'") has a
        # verdict but no difference to report. A mixed number/text comparison
        # is NOT that: it means one side's reported value was junk
        # ('#DIV/0!', '-84.55ab'), and comparing it lexically would invent a
        # verdict from unusable data.
        op_fn = _OPERATOR_FN.get(comparison.operator)
        if op_fn is None:
            return None
        if not (isinstance(lhs_value, str) and isinstance(rhs_value, str)):
            return None
        if comparison.operator not in ("=", "!=", "<>"):
            return None
        base.update({
            "boolean_only": True, "lhs_value": None, "rhs_value": None,
            "difference": None, "passes": bool(op_fn(str(lhs_value), str(rhs_value))),
            "values_equal": str(lhs_value) == str(rhs_value), "relationship": "n/a",
        })
        return base

    op_fn = _OPERATOR_FN.get(comparison.operator)
    if op_fn is None:
        return None

    # RAW values: the same operands with the rule's rounding/scaling wrappers
    # peeled off. A rule that compares to the nearest 100,000 turns a real
    # ₹34,000 into ₹0, and reporting only the rounded figure next to the
    # per-fact raw values makes the explanation self-contradictory ("the
    # components are 0, 0 and 34,000, the combined value is 0"). Both are kept
    # so the renderer can state the rounding as the reason for the gap.
    lhs_raw = _eval_node(comparison.lhs.core(), state)
    rhs_raw = _eval_node(comparison.rhs.core(), state)
    lhs_raw = None if isinstance(lhs_raw, (Missing, bool, str)) else lhs_raw
    rhs_raw = None if isinstance(rhs_raw, (Missing, bool, str)) else rhs_raw

    difference = lhs_value - rhs_value
    rounding_changed_a_value = bool(
        (lhs_raw is not None and lhs_raw != lhs_value)
        or (rhs_raw is not None and rhs_raw != rhs_value)
    )

    base.update({
        "boolean_only": False,
        # Compared (post-rounding) values — these decide the verdict.
        "lhs_value": lhs_value,
        "rhs_value": rhs_value,
        "difference": difference,
        # Raw (pre-rounding) values — reported alongside, never instead.
        "lhs_raw": lhs_raw,
        "rhs_raw": rhs_raw,
        "raw_difference": (lhs_raw - rhs_raw) if (lhs_raw is not None and rhs_raw is not None) else None,
        "rounding_changed_a_value": rounding_changed_a_value,
        "rounding_step": comparison.lhs.rounding_scale() or comparison.rhs.rounding_scale(),
        "passes": op_fn(lhs_value, rhs_value),
        "values_equal": lhs_value == rhs_value,
        "relationship": (
            "lhs_greater" if lhs_value > rhs_value
            else "lhs_less" if lhs_value < rhs_value
            else "lhs_equal"
        ),
    })
    return base


# ─────────────────────────────────────────────────────────────────────────────
# Human-readable rendering of the AST — used for the "Validation rule" line and
# for the LLM payload, so neither ever has to show raw XBRL/XPath syntax.
# ─────────────────────────────────────────────────────────────────────────────

def describe(
    node: FormulaNode,
    labels: dict[str, str] | None = None,
    phrase_vars: set[str] | None = None,
) -> str:
    """Render one subtree with variable ids replaced by their resolved business
    labels. Rounding/aggregation wrappers are described in words rather than
    reproduced as function calls.

    *phrase_vars* names variables whose resolved label ALREADY expresses the
    aggregation (because it came from the assertion's own message, e.g. "Sum of
    all its child elements"). For those, sum() is not narrated again — without
    this the rule reads "must equal the total of Sum of all its child
    elements".
    """
    labels = labels or {}
    phrase_vars = phrase_vars or set()

    # Precedence only, so a left-associative chain like "V2 + V3 + V4" renders
    # flat instead of as "((V2 + V3) + V4)".
    _PREC = {"+": 1, "-": 1, "*": 2, "div": 2, "idiv": 2, "mod": 2}

    def render(n: FormulaNode, parent_prec: int = 0, right_side: bool = False) -> str:
        if n.kind == "num":
            value = n.value
            try:
                return f"{value:,.0f}" if value == value.to_integral_value() else f"{value:,}"
            except (InvalidOperation, TypeError):
                return str(value)
        if n.kind == "str":
            return f"“{n.name}”"
        if n.kind == "if":
            return (f"if {render(n.args[0])} then {render(n.args[1])}, "
                    f"otherwise {render(n.args[2])}")
        if n.kind == "var":
            return labels.get(n.name) or n.name
        if n.kind == "unary":
            return f"-{render(n.args[0], 3)}"
        if n.kind == "binop":
            if n.op in COMPARISON_OPERATORS:
                meaning = OPERATOR_MEANING.get(n.op, n.op)
                return f"{render(n.args[0])} is {meaning} {render(n.args[1])}"
            if n.op in ("and", "or"):
                return f"{render(n.args[0])} {n.op} {render(n.args[1])}"
            symbol = {"+": " + ", "-": " − ", "*": " × ", "div": " ÷ ",
                      "idiv": " ÷ ", "mod": " mod "}.get(n.op, f" {n.op} ")
            prec = _PREC.get(n.op, 0)
            inner = (
                f"{render(n.args[0], prec)}{symbol}"
                f"{render(n.args[1], prec, right_side=True)}"
            )
            # Parenthesise only when the parent binds tighter, or when this is
            # the right operand of a same-precedence non-associative operator
            # ("A − (B − C)" must keep its parentheses; "A + B + C" must not).
            needs = prec < parent_prec or (prec == parent_prec and right_side)
            return f"({inner})" if needs else inner
        if n.kind == "func":
            inner = ", ".join(render(a) for a in n.args)
            if n.name == "sum":
                only = n.args[0] if len(n.args) == 1 else None
                if only is not None and only.kind == "var" and only.name in phrase_vars:
                    return inner
                return f"the total of {inner}"
            if n.name == "round":
                return inner              # rounding is stated separately, in words
            if n.name in ("floor", "ceiling"):
                return inner
            if n.name == "abs":
                return f"the absolute value of {inner}"
            if n.name == "count":
                return f"the number of reported values for {inner}"
            if n.name == "empty":
                return f"{inner} is not reported"
            if n.name == "not":
                return f"it is not the case that {inner}"
            return f"{n.name}({inner})"
        return ""

    return render(node)
