# backend/tools/formula_error_generic.py
"""
Formula-error parsing + explanation for NON-4000-series returns — returns
whose HTML error file has NO backtracking data (no DB TableName/Cell Code
columns), just a plain Variable/Name/Value/Context/Unit/Decimal/Precision
table. Confirmed shape for return 2065 (in-rbi-raq) via real error files.

This module is entirely independent of backend/tools/report_lookup.py's
4000-series formula-error flow (parse_formula_errors, _classify_formula_type,
_compute_sum_discrepancy/_compute_ratio_discrepancy, explain_formula_errors,
_render_sum_check_explanation_detailed, etc.). None of that is imported,
called, or modified here — this module has its own parser, its own
operator-aware formula evaluator, its own deterministic renderer, and its
own (optional) LLM-phrasing hook. The only shared dependency is
backend.tools.taxonomy_lookup, which is already a generic, return-agnostic
utility (JSON loading + assertion/concept lookup) used the same way by both
flows — reusing it is not "touching 4000-series logic".

Routing between the two flows is done by the caller (report_lookup.py's
explain_errors_by_category), keyed on _is_4000_series(form_id) — the same
existing helper already used to distinguish 4000-series from other returns
for xbrl_schema category tagging.
"""

from __future__ import annotations

import logging
import os
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

logger = logging.getLogger(__name__)

_MAX_EXPLAIN_GENERIC = 5

# ══════════════════════════════════════════════════════════════════════════
# SECTION 1: HTML PARSING — Variable/Name/Value/Context/Unit/Decimal/Precision
# ══════════════════════════════════════════════════════════════════════════

# Header aliases for this table shape only. Deliberately separate from
# report_lookup.py's _FORMULA_VAR_HEADER_MAP (which is for the 11-column
# backtracking layout) — the two must never be merged, since a return using
# one shape should never accidentally pick up header names meant for the
# other.
_GENERIC_VAR_HEADER_MAP: dict[str, str] = {
    "variable":  "var",
    "name":      "concept",
    "value":     "value",
    "context":   "context",
    "unit":      "unit",
    "decimal":   "decimal",
    "precision": "precision",
}


def _unescape(text: str) -> str:
    import html as _html
    return _html.unescape(text or "").replace(" ", " ")


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", _unescape(text)).strip()


def _extract_tab_pane(raw_html: str, tab_id: str = "1") -> str:
    """Isolate one Bootstrap tab-pane's content (FORMULA_ERROR is id="1").

    The error file's three tabs (FORMULA_ERROR / QUALITY-CHECK_ERROR /
    SPECIFICATION_ERROR) all reuse the same "assertionLabel" CSS class for
    their entries, so anything reusing a naive whole-document scan (e.g.
    searching for every "assertionLabel" div) picks up unrelated errors from
    the other two tabs. Scoping to this tab's own content is what avoids
    that — confirmed empirically: a whole-file scan over-counts by more than
    2x on real files.
    """
    next_id = str(int(tab_id) + 1)
    m = re.search(
        rf'id="{tab_id}">(.*?)<div class="tab-pane fade" id="{next_id}"',
        raw_html, re.S,
    )
    if m:
        return m.group(1)
    # Last tab in the file has no "next" sibling to bound against.
    m = re.search(rf'id="{tab_id}">(.*)', raw_html, re.S)
    return m.group(1) if m else ""


def _split_error_panels(tab_html: str) -> list[str]:
    """One string per <div class="panel panel-default" id="errorPanelN">."""
    if not tab_html:
        return []
    parts = re.split(r'(?=<div class="panel panel-default" id="errorPanel)', tab_html)
    return [p for p in parts if 'class="assertionLabel"' in p]


def _parse_variable_row(cells: list[str], headers: list[str] | None) -> dict:
    """Map one <tr class="hide fv"> row's cells to canonical fields.

    Header-driven when a header row was captured (this table's header order
    isn't guaranteed any more than the 4000-series table's is); falls back
    to the known fixed column order (Variable, Name, Value, Context, Unit,
    Decimal, Precision) only if no header row was found.
    """
    if headers and len(headers) == len(cells):
        out: dict[str, str] = {}
        for hdr, cell in zip(headers, cells):
            key = _GENERIC_VAR_HEADER_MAP.get(hdr.strip().lower())
            if key:
                out[key] = cell
        return out
    padded = cells + [""] * max(0, 6 - len(cells))
    return {
        "var": padded[0], "concept": padded[1], "value": padded[2],
        "context": padded[3], "unit": padded[4], "decimal": padded[5],
    }


def parse_generic_formula_errors(html_path: str) -> list[dict]:
    """Parse formula errors from the non-backtracking (7-column) table shape.

    Returns a list of rule dicts:
        {
            "rule_name": str, "formula_expression": str,
            "instances": [
                {"business_message": str,
                 "variables": [{"var": "V1", "concept": "...",
                                 "value": "...", "context": "...",
                                 "unit": "...", "decimal": "..."}]},
                ...
            ],
        }

    Every failing instance the file actually contains is kept (a rule with
    badge count 149 has 149 separate <table> blocks in the real files this
    was verified against, one per instance) — never just the first.
    """
    if not html_path or not os.path.isfile(html_path):
        logger.warning("[formula_error_generic] file not found: %s", html_path)
        return []

    try:
        with open(html_path, "r", encoding="utf-8", errors="replace") as fh:
            raw_html = fh.read()
    except OSError as exc:
        logger.warning("[formula_error_generic] cannot read: %s — %s", html_path, exc)
        return []

    formula_tab = _extract_tab_pane(raw_html, "1")
    panels = _split_error_panels(formula_tab)

    rules: list[dict] = []
    for panel in panels:
        name_m = re.search(r'class="assertionLabel">\s*(.*?)\s*</div>', panel, re.S)
        if not name_m:
            continue
        rule_name = _clean_text(name_m.group(1))
        if not rule_name:
            continue

        formula_m = re.search(
            r'class="formulaErrorTest\d*"[^>]*>\s*(.*?)\s*</div>', panel, re.S
        )
        formula_expression = _clean_text(formula_m.group(1)) if formula_m else ""

        # Each <table> block is one failing instance: one msgHead (business
        # message) + one header row + one msgBody tbody of variable rows.
        table_blocks = re.findall(
            r'<table class="table table-condensed table-striped">(.*?)</table>',
            panel, re.S,
        )

        instances: list[dict] = []
        for block in table_blocks:
            msg_m = re.search(
                r'class="formulaErrorTitle"[^>]*>(.*?)</td>', block, re.S
            )
            business_message = _clean_text(msg_m.group(1)) if msg_m else ""

            header_cells = re.findall(r'class="headerCell">(.*?)</td>', block, re.S)
            headers = [_clean_text(h) for h in header_cells] if header_cells else None

            body_m = re.search(
                r'<tbody class="msgBody formulaFvTBody">(.*?)</tbody>', block, re.S
            )
            variables: list[dict] = []
            if body_m:
                rows = re.findall(r'<tr class="hide fv">(.*?)</tr>', body_m.group(1), re.S)
                for row in rows:
                    cells = re.findall(r'class="msgBodyCell">(.*?)</td>', row, re.S)
                    cells = [_clean_text(c).lstrip('"') for c in cells]
                    if not cells:
                        continue
                    mapped = _parse_variable_row(cells, headers)
                    if mapped.get("var"):
                        mapped["var"] = mapped["var"].upper()
                        variables.append(mapped)

            if variables or business_message:
                instances.append({
                    "business_message": business_message,
                    "variables": variables,
                })

        if instances:
            rules.append({
                "rule_name": rule_name,
                "formula_expression": formula_expression,
                "instances": instances,
            })

    return rules


# ══════════════════════════════════════════════════════════════════════════
# SECTION 2: OPERATOR-AWARE FORMULA PARSING (=, >, >=, <, <=, <>, !=)
# ══════════════════════════════════════════════════════════════════════════

# Order matters: two-character operators must be tried before their
# one-character prefix (">=" before ">", "<=" before "<") so a single scan
# never mis-splits "V1 >= V2" into "V1 >" + "= V2".
_COMPARISON_OP_RE = re.compile(r"(>=|<=|<>|!=|=|>|<)")

_OPERATOR_MEANING = {
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

_ROUND_DIVISOR_RE = re.compile(r"round\s*\(\s*[^()]*?\bdiv\s*(\d+)\s*\)", re.IGNORECASE)
_VAR_REF_RE = re.compile(r"\$?(V\d+)\b", re.IGNORECASE)


def parse_comparison_formula(formula_expression: str) -> dict | None:
    """Understand the ACTUAL comparison — operator, which variables are on
    which side, and whether both sides are rounded — instead of classifying
    by keyword presence (a formula containing "round(" is not automatically
    a ratio/percentage check; a formula containing "+" is not automatically
    a sum_check; the operator is what determines meaning).

    Returns None if no recognisable "side OP side" shape is found.

    Known simplification: a side with more than one variable is treated as
    their SUM (matches every real formula seen: "$V2 + $V3"). A side using
    subtraction between variables is not currently supported — none of the
    real formulas examined use it, so this is a documented gap rather than
    a guess.
    """
    f = (formula_expression or "").strip()
    if not f:
        return None

    divisor_m = _ROUND_DIVISOR_RE.search(f)
    rounding_divisor = int(divisor_m.group(1)) if divisor_m else None

    op_m = _COMPARISON_OP_RE.search(f)
    if not op_m:
        return None
    operator = op_m.group(1)

    lhs_text, rhs_text = f[: op_m.start()], f[op_m.end():]
    lhs_vars = [v.upper() for v in _VAR_REF_RE.findall(lhs_text)]
    rhs_vars = [v.upper() for v in _VAR_REF_RE.findall(rhs_text)]
    if not lhs_vars or not rhs_vars:
        return None

    return {
        "operator": operator,
        "lhs_vars": lhs_vars,
        "rhs_vars": rhs_vars,
        "rounding_divisor": rounding_divisor,
    }


def _round_to_nearest(value: Decimal, divisor: int | None) -> Decimal:
    if not divisor:
        return value
    d = Decimal(divisor)
    return (value / d).to_integral_value(rounding=ROUND_HALF_UP) * d


def evaluate_comparison(parsed: dict, values_by_var: dict[str, Decimal]) -> dict | None:
    """Deterministically evaluate one comparison — the ONLY place numbers
    are computed or a pass/fail verdict is decided. Never delegated to an
    LLM. Returns None if any referenced variable's value isn't available
    (caller must fall back to a no-numbers explanation, never invent one).
    """
    try:
        lhs_raw = [values_by_var[v] for v in parsed["lhs_vars"]]
        rhs_raw = [values_by_var[v] for v in parsed["rhs_vars"]]
    except KeyError:
        return None

    lhs_value = sum(lhs_raw, Decimal(0))
    rhs_value = sum(rhs_raw, Decimal(0))

    divisor = parsed.get("rounding_divisor")
    lhs_compared = _round_to_nearest(lhs_value, divisor)
    rhs_compared = _round_to_nearest(rhs_value, divisor)

    op = parsed["operator"]
    op_fn = _OPERATOR_FN.get(op)
    if op_fn is None:
        return None
    passes = op_fn(lhs_compared, rhs_compared)

    return {
        "operator": op,
        "lhs_value": lhs_value,
        "rhs_value": rhs_value,
        "lhs_compared": lhs_compared,
        "rhs_compared": rhs_compared,
        "difference": lhs_compared - rhs_compared,
        "rounding_divisor": divisor,
        "passes": passes,
        "values_equal": lhs_compared == rhs_compared,
        # Deterministic relationship classification — computed ONCE here,
        # from the same compared (post-rounding) values used for the
        # pass/fail verdict, so the explanation sentence and the verdict can
        # never disagree about which side is actually larger. This is the
        # single source of truth _condition_sentence reads from; nothing
        # downstream (including any LLM phrasing) re-derives or overrides it.
        "relationship": _classify_relationship(lhs_compared, rhs_compared),
    }


def _classify_relationship(lhs_value: Decimal, rhs_value: Decimal) -> str:
    """One of "lhs_greater", "lhs_equal", "lhs_less" — the actual verified
    relationship between the two (already-rounded, already-summed) sides,
    independent of what the formula's operator required. Always computed
    from real numbers, never guessed or left to an LLM."""
    if lhs_value > rhs_value:
        return "lhs_greater"
    if lhs_value < rhs_value:
        return "lhs_less"
    return "lhs_equal"


# ══════════════════════════════════════════════════════════════════════════
# SECTION 3: TAXONOMY ENRICHMENT (reuses taxonomy_lookup.py — generic, shared)
# ══════════════════════════════════════════════════════════════════════════

def enrich_generic_rule_with_taxonomy(rule: dict, taxonomy: dict | None) -> dict:
    """Attach concept_label + db_location to each variable, when the
    taxonomy has a match for this assertion. A no-op when there's no
    taxonomy, no matching assertion, or a variable isn't in its map —
    never an error; callers already tolerate a missing concept_label/
    db_location and fall back to message-derived or raw names."""
    if not taxonomy:
        return rule

    from backend.tools import taxonomy_lookup

    var_meta = taxonomy_lookup.build_variable_metadata_map(taxonomy, rule.get("rule_name", ""))
    if not var_meta:
        return rule

    rule = dict(rule)
    rule["_taxonomy_matched"] = True
    for inst in rule.get("instances", []):
        for v in inst.get("variables", []):
            meta = var_meta.get(v.get("var", ""))
            if not meta:
                continue
            if meta.get("label"):
                v["concept_label"] = meta["label"]
            location = taxonomy_lookup.format_db_location(meta)
            if location:
                v["db_location"] = location
    return rule


# ══════════════════════════════════════════════════════════════════════════
# SECTION 4: MESSAGE-DERIVED OPERAND NAMING (fallback when unmapped)
# ══════════════════════════════════════════════════════════════════════════

def _clean_business_message(message: str) -> str:
    """Strip this file's message wrapper down to the bare operand text,
    e.g. '▼ "en:Identity "Total Term Loans Sanctioned > Total Term Loans
    Disbursed" do not tally."' -> 'Total Term Loans Sanctioned > Total Term
    Loans Disbursed'. Structural only — no per-rule text is hardcoded."""
    msg = (message or "").strip()
    msg = re.sub(r'^[▼\s]+', '', msg)
    msg = re.sub(r'^["\']+', '', msg)
    msg = re.sub(r'^en\s*:\s*', '', msg, flags=re.IGNORECASE)
    msg = re.sub(r'^Identity\s*', '', msg, flags=re.IGNORECASE)
    msg = re.sub(r'^["\']+', '', msg)
    msg = re.sub(r'\s*["\']?\s*do not tally\.?["\']?\s*$', '', msg, flags=re.IGNORECASE)
    return msg.strip().strip('"').strip("'").strip()


def extract_operand_labels_from_message(message: str, operator: str) -> tuple[str, str] | None:
    """This return's assertion messages follow one convention: 'Identity
    "<lhs label> <operator> <rhs label>" do not tally.' — the two operand
    phrases sit on either side of the SAME operator symbol the formula
    itself uses, so splitting on that operator names both sides directly.
    Purely structural — no per-rule hardcoding, works for any label text.

    Returns None if the message doesn't contain the expected operator
    (e.g. an unexpected message shape) — caller must fall back gracefully,
    never invent a label.
    """
    if not message or not operator:
        return None
    msg = _clean_business_message(message)
    parts = msg.split(operator, 1)
    if len(parts) != 2:
        return None
    lhs_label, rhs_label = parts[0].strip(" -"), parts[1].strip(" -")
    if not lhs_label or not rhs_label:
        return None
    return lhs_label, rhs_label


def _split_summed_labels(rhs_label: str, expected_count: int) -> list[str] | None:
    """Split a message's "A + B" RHS phrase into per-term labels, only when
    the count matches the number of summed variables — otherwise the whole
    phrase is kept as one combined label rather than guessing a split."""
    if expected_count <= 1:
        return None
    parts = [p.strip() for p in rhs_label.split(" + ")]
    return parts if len(parts) == expected_count and all(parts) else None


# Splits before an uppercase letter only when it follows a lowercase letter
# or digit — keeps acronym runs ("NPAs", "MFIs") intact as one token instead
# of shattering them into single letters the way a naive per-capital split
# would ("N P As", "M F Is").
_CAMEL_SPLIT_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def _humanize_concept_name(name: str) -> str:
    """Last-resort display name when neither the taxonomy nor the message
    yields one — e.g. "TermLoansSanctioned" -> "Term Loans Sanctioned"."""
    if not name:
        return "This value"
    words = _CAMEL_SPLIT_RE.sub(" ", name).split()
    return " ".join(words) if words else name


def resolve_variable_labels(rule: dict, parsed_formula: dict) -> dict[str, str]:
    """One display label per variable id, in priority order: taxonomy
    concept_label (when mapped) -> message-derived operand label (when the
    taxonomy has nothing) -> humanized raw XBRL concept name (last resort).
    Taxonomy is preferred when available since it's already the return's
    standardised naming; message-derived is the fallback specifically for
    the unmapped case, per the "gracefully fall back" requirement."""
    instances = rule.get("instances", [])
    if not instances:
        return {}
    first = instances[0]
    var_by_id = {v.get("var"): v for v in first.get("variables", [])}

    message_labels: dict[str, str] = {}
    operator = parsed_formula.get("operator") if parsed_formula else None
    if operator:
        split = extract_operand_labels_from_message(first.get("business_message", ""), operator)
        if split:
            lhs_label, rhs_label = split
            for v in parsed_formula.get("lhs_vars", []):
                message_labels.setdefault(v, lhs_label)
            rhs_vars = parsed_formula.get("rhs_vars", [])
            per_term = _split_summed_labels(rhs_label, len(rhs_vars))
            if per_term:
                for v, label in zip(rhs_vars, per_term):
                    message_labels[v] = label
            else:
                for v in rhs_vars:
                    message_labels.setdefault(v, rhs_label)

    labels: dict[str, str] = {}
    for var_id, v in var_by_id.items():
        labels[var_id] = (
            v.get("concept_label")
            or message_labels.get(var_id)
            or _humanize_concept_name(v.get("concept", ""))
        )
    return _disambiguate_labels(labels, var_by_id)


_CONTEXT_MEMBER_RE = re.compile(r"[A-Za-z0-9]+Member")


def _disambiguate_labels(labels: dict[str, str], var_by_id: dict[str, dict]) -> dict[str, str]:
    """Two variables can resolve to the identical label and DB location
    (e.g. rule 8's V2/V3 here: same concept, same code_filter, distinguished
    only by dimensional context — "Rupees" vs "Foreign Currency"). Appends a
    short distinguishing hint pulled from each variable's own context string
    when that happens, so they read as two different rows instead of an
    unexplained duplicate. Purely structural (symmetric difference of
    dimensional-member tokens) — no hardcoded dimension names."""
    counts: dict[str, int] = {}
    for lbl in labels.values():
        counts[lbl] = counts.get(lbl, 0) + 1

    out = dict(labels)
    for var_id, lbl in labels.items():
        if counts[lbl] <= 1:
            continue
        others = [o for o, ol in labels.items() if o != var_id and ol == lbl]
        my_members = set(_CONTEXT_MEMBER_RE.findall(var_by_id.get(var_id, {}).get("context", "")))
        other_members: set[str] = set()
        for o in others:
            other_members |= set(_CONTEXT_MEMBER_RE.findall(var_by_id.get(o, {}).get("context", "")))
        distinct = sorted(m[:-len("Member")] for m in (my_members - other_members))
        if distinct:
            out[var_id] = f"{lbl} ({', '.join(distinct)})"
    return out


# ══════════════════════════════════════════════════════════════════════════
# SECTION 5: DETERMINISTIC RENDERING
# ══════════════════════════════════════════════════════════════════════════

_CURRENCY_SYMBOLS = {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£"}


def _format_amount(value: Decimal, unit: str = "") -> str:
    try:
        formatted = f"{value:,.4f}".rstrip("0").rstrip(".") if value % 1 else f"{value:,.0f}"
    except InvalidOperation:
        return str(value)
    symbol = _CURRENCY_SYMBOLS.get((unit or "").strip().upper())
    return f"{symbol}{formatted}" if symbol else (f"{formatted} {unit}".strip() if unit else formatted)


def _humanize_rule_name(name: str) -> str:
    words = _CAMEL_SPLIT_RE.sub(" ", name.replace("_", " ").replace("-", " ")).split()
    return " ".join(words)


def _combined_rhs_phrase(rhs_label_parts: list[str]) -> str:
    """"the combined value of A and B" for a summed RHS, or just the single
    label when there's only one term — used so a V1 <= V2+V3 mismatch is
    described as an actual sum comparison, never as a plain equality."""
    if len(rhs_label_parts) > 1:
        return "the combined value of " + " and ".join(rhs_label_parts)
    return rhs_label_parts[0]


def _condition_sentence(
    operator: str,
    lhs_label: str,
    rhs_label_parts: list[str],
    relationship: str,
    equal_value_str: str,
    difference_str: str,
) -> str:
    """Phrase the ALREADY-VERIFIED operator + relationship as one accurate
    sentence. relationship ("lhs_greater"/"lhs_equal"/"lhs_less") always
    comes from evaluate_comparison's real Decimal comparison — this function
    only selects wording, it never re-derives or guesses which side is
    larger. That split is what guarantees the explanation can never claim a
    value is greater when the two are actually equal, or lower when it's
    actually greater — the exact bug this function replaces.
    """
    rhs_phrase = _combined_rhs_phrase(rhs_label_parts)
    is_summed = len(rhs_label_parts) > 1

    if operator == ">":
        if relationship == "lhs_greater":
            return f"{lhs_label} is greater than {rhs_phrase}, so the condition is satisfied."
        if relationship == "lhs_equal":
            return (
                f"{lhs_label} must be greater than {rhs_phrase}, but both values are "
                f"equal at {equal_value_str}. Therefore, the required strict greater-than "
                "condition is not satisfied."
            )
        return (
            f"{lhs_label} must be greater than {rhs_phrase}, but it is lower than "
            f"{rhs_phrase}. The condition is not satisfied."
        )

    if operator == ">=":
        if relationship == "lhs_equal":
            return (
                f"{lhs_label} must be greater than or equal to {rhs_phrase}, and both "
                f"values are equal at {equal_value_str}. Therefore, the condition is satisfied."
            )
        if relationship == "lhs_greater":
            return f"{lhs_label} is greater than {rhs_phrase}, so the condition is satisfied."
        return (
            f"{lhs_label} must be greater than or equal to {rhs_phrase}, but it is lower "
            f"than {rhs_phrase}. The condition is not satisfied."
        )

    if operator == "<":
        if relationship == "lhs_less":
            return f"{lhs_label} is less than {rhs_phrase}, so the condition is satisfied."
        if relationship == "lhs_equal":
            return (
                f"{lhs_label} must be less than {rhs_phrase}, but both values are equal "
                f"at {equal_value_str}. Therefore, the required strict less-than condition "
                "is not satisfied."
            )
        return (
            f"{lhs_label} must be less than {rhs_phrase}, but it is greater than "
            f"{rhs_phrase}. The condition is not satisfied."
        )

    if operator == "<=":
        if relationship == "lhs_equal":
            return (
                f"{lhs_label} must be less than or equal to {rhs_phrase}, and both "
                f"values are equal at {equal_value_str}. Therefore, the condition is satisfied."
            )
        if relationship == "lhs_less":
            return f"{lhs_label} is less than {rhs_phrase}, so the condition is satisfied."
        if is_summed:
            return (
                f"{lhs_label} must not exceed {rhs_phrase}, but the reported value "
                f"exceeds the allowed combined amount by {difference_str}."
            )
        return (
            f"{lhs_label} must not exceed {rhs_phrase}, but it is greater than the "
            "allowed value. The condition is not satisfied."
        )

    if operator == "=":
        if relationship == "lhs_equal":
            return f"{lhs_label} matches {rhs_phrase}, and the equality condition is satisfied."
        return f"{lhs_label} does not match {rhs_phrase}. The values differ by {difference_str}."

    if operator in ("<>", "!="):
        if relationship != "lhs_equal":
            return f"{lhs_label} does not equal {rhs_phrase}, so the condition is satisfied."
        return f"{lhs_label} must not equal {rhs_phrase}, but it does. The condition is not satisfied."

    return f"{lhs_label} does not satisfy the required comparison with {rhs_phrase}."


def _fix_sentence(operator: str, relationship: str, lhs_label: str, rhs_label_parts: list[str]) -> str:
    """Deterministic "how to fix" wording — never claims a specific field is
    wrong when the comparison only proves the rule failed; only names a
    field as the likely issue when the operator itself pins down which side
    has a hard ceiling (the summed <= case)."""
    rhs_phrase = _combined_rhs_phrase(rhs_label_parts)

    if operator == "=":
        return "Review both reported values and correct whichever value is inaccurate, then revalidate the report."

    if relationship == "lhs_equal" and operator in (">", "<"):
        word = "greater" if operator == ">" else "less"
        return (
            "Review both reported values and confirm whether the equality is expected. "
            f"The rule requires one value to be strictly {word} than the other."
        )

    return (
        f"Review the reported values for {lhs_label} and {rhs_phrase} to determine which "
        "value requires correction, then revalidate the report."
    )


def render_generic_formula_explanation(rule: dict, llm_text: dict | None = None) -> str | None:
    """Deterministic explanation — every number, location, and the
    pass/fail verdict always come from code.

    The condition sentence (what the rule checks and why it failed) is
    ALWAYS the deterministic wording from _condition_sentence — this is
    never handed to an LLM to rephrase. That sentence is exactly where a
    prior bug lived (claiming one value "exceeded" another when the two
    were actually equal); the fix is to stop that sentence from ever being
    LLM-influenced at all, not to add better instructions and hope an LLM
    follows them. Only the closing "how to fix" line may optionally be
    replaced by *llm_text['fix']* (validated — see
    explain_generic_context_via_llm) when supplied; otherwise it uses the
    deterministic default from _fix_sentence.

    Returns None if the rule doesn't have enough parsed/computed data
    (caller may still show a bare evidence-only fallback built from
    whatever text IS present)."""
    instances = rule.get("instances", [])
    if not instances:
        return None
    rule_name = rule.get("rule_name", "")
    parsed = parse_comparison_formula(rule.get("formula_expression", ""))
    first = instances[0]
    var_by_id = {v.get("var"): v for v in first.get("variables", [])}

    lines = [f"⚙ Formula Error — {rule_name}", ""]

    if not parsed:
        # No recognisable comparison structure — evidence-only, no numbers.
        biz_msg = first.get("business_message", "") or "This validation rule did not tally."
        lines.append(f"❌ **{_humanize_rule_name(rule_name)} does not tally**")
        lines.append("")
        lines.append(biz_msg)
        lines.append("")
        lines.append("**How to fix:** Review the values involved in this check and revalidate the report.")
        return "\n".join(lines)

    labels = resolve_variable_labels(rule, parsed)
    lhs_vars, rhs_vars = parsed["lhs_vars"], parsed["rhs_vars"]
    lhs_label = labels.get(lhs_vars[0], _humanize_concept_name(lhs_vars[0]))
    rhs_label_parts = [labels.get(v, _humanize_concept_name(v)) for v in rhs_vars]
    rhs_label = " + ".join(rhs_label_parts) if len(rhs_label_parts) > 1 else rhs_label_parts[0]

    values_by_var: dict[str, Decimal] = {}
    units_by_var: dict[str, str] = {}
    for var_id, v in var_by_id.items():
        try:
            values_by_var[var_id] = Decimal(str(v.get("value", "0")).replace(",", "") or "0")
        except InvalidOperation:
            continue
        units_by_var[var_id] = v.get("unit", "")

    calc = evaluate_comparison(parsed, values_by_var)

    lines.append(f"❌ **{_humanize_rule_name(rule_name)} does not tally**")
    lines.append("")

    if calc is None:
        lines.append(f"{lhs_label} does not satisfy the required comparison with {rhs_label}.")
    else:
        unit = units_by_var.get(lhs_vars[0], "")
        equal_value_str = _format_amount(calc["lhs_compared"], unit)
        difference_str = _format_amount(abs(calc["difference"]), unit)

        lines.append(
            _condition_sentence(
                calc["operator"], lhs_label, rhs_label_parts, calc["relationship"],
                equal_value_str, difference_str,
            )
        )
        lines.append("")
        lines.append(f"- **{lhs_label}:** {_format_amount(calc['lhs_value'], unit)}")
        if len(rhs_vars) > 1:
            for v, lbl in zip(rhs_vars, rhs_label_parts):
                lines.append(f"- **{lbl}:** {_format_amount(values_by_var.get(v, Decimal(0)), units_by_var.get(v, unit))}")
            lines.append(f"- **Combined value ({rhs_label}):** {_format_amount(calc['rhs_value'], unit)}")
        else:
            lines.append(f"- **{rhs_label}:** {_format_amount(calc['rhs_value'], units_by_var.get(rhs_vars[0], unit))}")
        if not calc["values_equal"]:
            lines.append(f"- **Difference:** {difference_str}")
        if calc["rounding_divisor"]:
            lines.append("")
            lines.append(f"Values are compared after rounding to the nearest {calc['rounding_divisor']:,}.")

    # Locations — only for variables the taxonomy actually resolved; never invented.
    loc_lines = []
    for var_id in [lhs_vars[0]] + rhs_vars:
        v = var_by_id.get(var_id)
        loc = v.get("db_location") if v else None
        lbl = labels.get(var_id, var_id)
        if loc:
            loc_lines.append(f"- **{lbl}:** `{loc}`")
    lines.append("")
    if loc_lines:
        lines.append("**Where to check:**")
        lines.extend(loc_lines)
    else:
        lines.append("No reliable database location is available for these fields in the current mapping.")

    if len(instances) > 1:
        lines.append("")
        lines.append(
            f"This rule failed for {len(instances)} reporting instances in total; "
            "only the first is shown in detail above."
        )

    lines.append("")
    if llm_text:
        lines.append(f"**How to fix:** {llm_text['fix']}")
    elif calc is not None:
        lines.append(f"**How to fix:** {_fix_sentence(calc['operator'], calc['relationship'], lhs_label, rhs_label_parts)}")
    else:
        lines.append(
            f"**How to fix:** Review {lhs_label} and {rhs_label}, correct whichever is "
            "wrong so the condition holds, then revalidate the report."
        )
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════
# SECTION 6: LLM PAYLOAD + OPTIONAL PHRASING (never calculates, never decides pass/fail)
# ══════════════════════════════════════════════════════════════════════════

def build_generic_llm_context(rule: dict) -> dict | None:
    """The ONLY thing that would be sent to an LLM for this rule — every
    field is already-verified structured data (computed above), never the
    taxonomy JSON, never the raw HTML. An LLM asked to phrase from this can
    only rearrange words; it cannot alter a number, a location, or the
    pass/fail verdict, all of which are already fixed by the time this
    payload is built."""
    instances = rule.get("instances", [])
    if not instances:
        return None
    parsed = parse_comparison_formula(rule.get("formula_expression", ""))
    if not parsed:
        return None
    first = instances[0]
    var_by_id = {v.get("var"): v for v in first.get("variables", [])}
    labels = resolve_variable_labels(rule, parsed)

    lhs_vars, rhs_vars = parsed["lhs_vars"], parsed["rhs_vars"]
    values_by_var: dict[str, Decimal] = {}
    for var_id, v in var_by_id.items():
        try:
            values_by_var[var_id] = Decimal(str(v.get("value", "0")).replace(",", "") or "0")
        except InvalidOperation:
            continue
    calc = evaluate_comparison(parsed, values_by_var)
    if calc is None:
        return None

    return {
        "rule_name": rule.get("rule_name", ""),
        "operator": calc["operator"],
        "operator_meaning": _OPERATOR_MEANING.get(calc["operator"], calc["operator"]),
        "relationship": calc["relationship"],
        "lhs_label": labels.get(lhs_vars[0], lhs_vars[0]),
        "lhs_value": str(calc["lhs_value"]),
        "rhs_terms": [
            {"label": labels.get(v, v), "value": str(values_by_var.get(v, Decimal(0)))}
            for v in rhs_vars
        ],
        "rhs_total": str(calc["rhs_value"]),
        "difference": str(calc["difference"]),
        "values_equal": calc["values_equal"],
        "rounding_divisor": calc["rounding_divisor"],
        "instance_count": len(instances),
    }


def explain_generic_context_via_llm(
    context: dict, ollama_base: str, model: str, timeout: float, keep_alive: str,
) -> dict | None:
    """Ask the LLM for exactly one short "how to fix" sentence, phrased
    from the already-verified context above.

    The condition/explanation sentence is deliberately NOT requested here
    any more — render_generic_formula_explanation always uses its own
    deterministic wording for that sentence (see _condition_sentence), since
    that is exactly where an earlier bug lived (an LLM-phrased sentence
    claiming one value "exceeded" another when the verified relationship
    was actually "equal"). Keeping the LLM out of that sentence entirely is
    the fix, not a stricter prompt.

    Rejects (returns None, triggering the deterministic fallback) unless
    the fix sentence mentions every resolved label verbatim, and — as a
    direct guard against the same class of bug — unless relationship is
    "lhs_equal", also rejects if the wording claims one side exceeded or
    fell short of the other.
    """
    import json as _json
    import httpx as _httpx

    required_names = [context["lhs_label"]] + [t["label"] for t in context["rhs_terms"]]

    prompt = (
        "You are a regulatory reporting assistant. Using ONLY the verified facts "
        "below (never invent numbers, names, locations, or which side is larger), "
        "write exactly one short plain-text sentence telling the user what to "
        "review and revalidate.\n\n"
        f"{_json.dumps(context, indent=2, ensure_ascii=False)}\n\n"
        "Return ONLY a single-line JSON object: "
        '{"fix": "one sentence telling the user what to review and revalidate, '
        'using the business names above, never V1/V2/V3"}. No other text.'
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Suggest a corrective action for a validation mismatch in plain business language using only the given facts. Never invent values or locations. Never state which value is larger — that is not your role. Never use V1, V2, V3."},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "keep_alive": keep_alive,
        "options": {"temperature": 0.0, "num_predict": 120},
    }
    try:
        with _httpx.Client(timeout=timeout) as client:
            resp = client.post(f"{ollama_base}/api/chat", json=payload)
            resp.raise_for_status()
        content = resp.json()["message"]["content"].strip()
        content = re.sub(r"^```(?:json)?|```$", "", content.strip(), flags=re.MULTILINE).strip()
        parsed = _json.loads(content)
        fix = (parsed.get("fix") or "").strip()
        if not fix:
            return None
        lowered = fix.lower()
        if not all(name.lower() in lowered for name in required_names if name):
            return None
        if re.search(r"\bv\d+\b", lowered):
            return None
        if context.get("relationship") == "lhs_equal" and re.search(
            r"\bexceed|exceeds|exceeded|is greater|is lower|is higher|is less than\b", lowered
        ):
            return None
        return {"fix": fix}
    except Exception as exc:
        logger.warning("[formula_error_generic] LLM phrasing failed/rejected: %s", exc)
        return None


# ══════════════════════════════════════════════════════════════════════════
# SECTION 7: ORCHESTRATION
# ══════════════════════════════════════════════════════════════════════════

def explain_one_generic_rule(
    rule: dict, taxonomy: dict | None, ollama_base: str, model: str, timeout: float, keep_alive: str,
) -> dict:
    """Per-rule orchestrator. Never raises: any failure — taxonomy join,
    payload building, or the Ollama call — falls through to the fully
    deterministic template."""
    rule = dict(rule)
    try:
        rule = enrich_generic_rule_with_taxonomy(rule, taxonomy)

        llm_text = None
        context = build_generic_llm_context(rule)
        if context:
            llm_text = explain_generic_context_via_llm(context, ollama_base, model, timeout, keep_alive)

        rendered = render_generic_formula_explanation(rule, llm_text=llm_text)
        if rendered:
            rule["explanation"] = rendered
            return rule

        rule["explanation"] = (
            f"⚙ Formula Error — {rule.get('rule_name', '')}\n\n"
            "This validation rule did not tally. Review the reported values for this "
            "check and revalidate the report."
        )
        return rule
    except Exception as exc:
        logger.error("[formula_error_generic] explain failed for %r: %s", rule.get("rule_name"), exc)
        rule["explanation"] = (
            f"⚙ Formula Error — {rule.get('rule_name', '')}\n\n"
            "This validation rule did not tally. Review the reported values for this "
            "check and revalidate the report."
        )
        return rule


def explain_generic_formula_errors(rules: list[dict], form_id: str = "") -> list[dict]:
    """Batch entry point — mirrors explain_formula_errors' signature so the
    router can call either flow interchangeably, but is otherwise a fully
    separate implementation."""
    import os as _os

    taxonomy = None
    if form_id:
        try:
            from backend.tools import taxonomy_lookup
            taxonomy = taxonomy_lookup.get_return_json(form_id)
        except Exception as exc:
            logger.warning("[formula_error_generic] taxonomy lookup failed for form_id=%s: %s", form_id, exc)

    ollama_base = _os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    model       = _os.getenv("OLLAMA_MODEL", "llama3.1:latest")
    timeout     = float(_os.getenv("OLLAMA_TIMEOUT", "180"))
    keep_alive  = _os.getenv("OLLAMA_KEEP_ALIVE", "30m")

    return [
        explain_one_generic_rule(rule, taxonomy, ollama_base, model, timeout, keep_alive)
        for rule in rules
    ]


def explain_generic_formula_error_file(html_path: str, form_id: str = "", max_rules: int = _MAX_EXPLAIN_GENERIC) -> list[dict]:
    """Top-level entry point: parse the non-backtracking HTML shape, then
    explain up to max_rules rules. What the router calls for any return
    that isn't in the 4000-series range."""
    rules = parse_generic_formula_errors(html_path)
    trimmed = rules[:max_rules]
    explained = explain_generic_formula_errors(trimmed, form_id=form_id)
    for rule in explained:
        rule["_error_category"] = "formula_error"
    return explained
