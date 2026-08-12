# backend/tools/formula_error.py — the unified formula-error explainer (V2).
#
#   shape-tolerant HTML parse  (both table shapes, one parser)
#     -> facts as a LIST per variable      (never {var: fact}, which loses duplicates)
#     -> expression AST + Decimal evaluation
#     -> label cascade: JSON -> label linkbase -> backtracking row -> message -> CamelCase
#     -> backtracking enrichment when the table actually carries it
#     -> grounded LLM phrasing
#     -> user-facing explanation
#
# Replaces the fork between report_lookup.parse_formula_errors (the
# "4000-series" path) and formula_error_generic (everything else). That fork
# was keyed on `_is_4000_series(form_id)`, a numeric range check standing in
# for "this file has backtracking columns" — a proxy that mis-routes five files
# in the real corpus (see error_file_shape). Here there is ONE parser and ONE
# explainer, and backtracking is per-table enrichment rather than a routing
# decision.
#
# Bugs from the analysis that this module fixes, each reproduced on real files:
#   * '$V1 = $V2 + $V3 - $V4' evaluated as V2+V3+V4  (sum() over rhs_vars)
#   * 'sum($V2)' over three facts evaluated as the LAST fact  ({var: fact} dict)
#   * 'round($V1 * 10) div 10' ignored rounding entirely      (divisor regex)
#   * '"V2' variable ids with a stray quote never matched the formula
#   * 'Loss for the previous year.)" do not tally.' used as a concept name
#   * '(BeginningBalance)' appended onto a label that was already a sentence

from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation

from backend.tools import error_file_shape as shape
from backend.tools import error_llm, formula_expression, message_cleaner, taxonomy_index

logger = logging.getLogger(__name__)

__all__ = [
    "parse_formula_errors_v2", "explain_formula_error_file",
    "explain_formula_rules", "build_llm_payload", "render_explanation",
    "build_sections", "sections_to_text", "resolve_labels",
]

_CURRENCY_SYMBOLS = {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£"}


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 1 — parsing (one parser, both table shapes)
# ═════════════════════════════════════════════════════════════════════════════

def _map_row(headers: list[str], cells: list[str]) -> dict:
    """Map one variable row onto canonical fields, ALWAYS by header name.

    There is deliberately no positional fallback. Column counts differ between
    the 7-column plain shape, the 11-column backtracking shape and the
    12-column 'Cell Index' variant, so a positional guess silently shifts every
    field by one on the shape it wasn't written for. A row we cannot map by
    header is dropped and logged instead.
    """
    if not headers or len(headers) != len(cells):
        return {}
    out: dict[str, str] = {}
    for header, cell in zip(headers, cells):
        key = shape.canonical_header_key(header)
        if key:
            out[key] = cell
    return out


def parse_formula_errors_v2(html_path: str) -> list[dict]:
    """Formula errors from either error-file product.

    Returns one dict per assertion:
        {
          "rule_name", "formula_expression", "error_count",
          "has_backtracking": bool,
          "instances": [
             {"business_message": str,
              "facts": [ {var, concept, value, context, unit, decimal,
                          entered_value, db_table, table_header, row_label,
                          column_label, cell_code}, ... ]},
          ],
        }

    `facts` is a LIST: `$V1 = sum($V2)` legitimately binds three facts to V2,
    and keying them by variable id would keep only the last (measured on 4044:
    [177, 14, 3] collapsed to 3).
    """
    raw = shape.read_error_file(html_path)
    if not raw:
        return []

    formula_tab = shape.extract_tab_pane(raw, "1")
    panels = shape.split_formula_panels(formula_tab)

    rules: list[dict] = []
    for panel in panels:
        rule_name = _first_text(panel, "assertionLabel")
        if not rule_name:
            continue
        expression = _first_text(panel, "formulaErrorTest")
        badge = _first_text(panel, "badge")

        instances: list[dict] = []
        has_backtracking = False
        for table in shape.extract_tables(panel):
            headers = shape.extract_header_cells(table)
            if shape.header_has_backtracking(headers):
                has_backtracking = True

            message = _table_message(table)
            facts: list[dict] = []
            for cells in shape.extract_body_rows(table):
                mapped = _map_row(headers, cells)
                if not mapped:
                    if cells:
                        logger.debug(
                            "[formula_error] unmappable row (%d cells, %d headers) in %s",
                            len(cells), len(headers), html_path,
                        )
                    continue
                var = (mapped.get("var") or "").strip().upper()
                if not var:
                    continue
                mapped["var"] = var
                # The backtracking shape has no concept column at all; its
                # nearest equivalents are the table/column labels, which are
                # what the user actually sees in the input form.
                if not mapped.get("concept"):
                    mapped["concept"] = (mapped.get("column_label")
                                         or mapped.get("row_label")
                                         or mapped.get("table_header") or "")
                facts.append(mapped)

            if facts or message:
                instances.append({"business_message": message, "facts": facts})

        if instances:
            rules.append({
                "rule_name": rule_name,
                "formula_expression": expression,
                "error_count": _safe_int(badge, len(instances)),
                "has_backtracking": has_backtracking,
                "instances": instances,
            })

    logger.info("[formula_error] %d rule(s) parsed from %s (backtracking=%s)",
                len(rules), html_path, any(r["has_backtracking"] for r in rules))
    return rules


def _first_text(panel_html: str, css_class: str) -> str:
    import re
    m = re.search(
        rf"""<div[^>]*class=["'][^"']*\b{css_class}\b[^"']*["'][^>]*>(.*?)</div>""",
        panel_html, re.S | re.IGNORECASE,
    )
    if not m:
        m = re.search(
            rf"""<div[^>]*id=["']{css_class}\d*["'][^>]*>(.*?)</div>""",
            panel_html, re.S | re.IGNORECASE,
        )
    return shape.clean_cell(m.group(1)) if m else ""


def _table_message(table_html: str) -> str:
    import re
    m = re.search(
        r"""<td[^>]*class=["'][^"']*formulaErrorTitle[^"']*["'][^>]*>(.*?)</td>""",
        table_html, re.S | re.IGNORECASE,
    )
    return shape.strip_tags(m.group(1)).strip() if m else ""


def _safe_int(text: str, default: int) -> int:
    try:
        return int(str(text).strip())
    except (TypeError, ValueError):
        return default


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 2 — label resolution cascade
# ═════════════════════════════════════════════════════════════════════════════

def _json_variable_map(taxonomy_json: dict | None, rule_name: str) -> dict[str, dict]:
    """Per-variable metadata from the return's JSON extract, when one exists.

    Matched on assertion_id, exactly first and then on a normalised form,
    because HTML assertion labels and JSON assertion ids drift in punctuation.
    """
    if not taxonomy_json or not rule_name:
        return {}
    try:
        from backend.tools import taxonomy_lookup
    except Exception:
        return {}

    by_assertion = taxonomy_json.get("by_assertion_id") or {}
    rule = by_assertion.get(rule_name)
    if rule is None:
        def norm(text: str) -> str:
            return "".join(ch for ch in str(text).lower() if ch.isalnum())
        target = norm(rule_name)
        for key, value in by_assertion.items():
            if norm(key) == target:
                rule = value
                break
    if rule is None:
        return {}

    out: dict[str, dict] = {}
    for var in rule.get("variables") or []:
        name = (var.get("name") or "").strip().upper()
        if not name:
            continue
        concept_id = var.get("concept_id")
        db = var.get("db_mapping") or {}
        out[name] = {
            "concept_id": concept_id,
            "label": taxonomy_lookup.resolve_concept_label(taxonomy_json, concept_id),
            "dimensional_qualification": var.get("dimensional_qualification") or [],
            "db_location": taxonomy_lookup.format_db_location({
                "table": db.get("table"), "column": db.get("column"),
                "code_filter": db.get("code_filter"),
            }),
        }
    return out


def _qualification_hint(qualification: list[str]) -> str:
    """'AssetClassificationAxis=PerformingAssetsMember' -> 'Performing Assets'.

    This is what distinguishes two variables bound to the SAME concept — the
    common reason a JSON variable has no concept_id of its own (measured: 536
    of 2065's 1075 variables). Rendered as a parenthetical qualifier, never
    glued into the middle of a label.
    """
    parts: list[str] = []
    for entry in qualification or []:
        member = str(entry).split("=")[-1].strip()
        if not member:
            continue
        text = taxonomy_index.humanize_local_name(member, ("Member", "Domain"))
        if text:
            parts.append(text)
    return ", ".join(parts)


def resolve_labels(
    rule: dict,
    comparison,
    taxonomy_json: dict | None = None,
    index=None,
) -> tuple[dict[str, str], dict[str, str]]:
    """(labels, sources) — one business label per variable id, plus where each
    came from, in strict priority order:

      1. the return's JSON extract (authored variable -> concept binding)
      2. the taxonomy label linkbase, keyed by the HTML's own concept name
      3. the backtracking row/column labels (what the user sees in the form)
      4. the business message, split ONLY when its arity matches the formula
      5. the CamelCase-humanised concept name

    Message-derived labels are fourth, not first, precisely because that is the
    source that produced the corrupted names — and its result is now discarded
    unless the split's term count and sign pattern agree with the parsed
    formula.
    """
    labels: dict[str, str] = {}
    sources: dict[str, str] = {}

    instances = rule.get("instances") or []
    if not instances:
        return labels, sources
    facts = instances[0].get("facts") or []

    by_var: dict[str, list[dict]] = {}
    for fact in facts:
        by_var.setdefault(fact["var"], []).append(fact)

    json_map = _json_variable_map(taxonomy_json, rule.get("rule_name", ""))

    # ── 4. message-derived (computed up front, applied last) ────────────────
    message_lhs: str | None = None
    message_rhs: list[str] | None = None
    aggregated: list[str] | None = None
    if comparison is not None and comparison.operator:
        rhs_terms = comparison.rhs.signed_variables() if comparison.rhs is not None else []
        message_lhs, message_rhs = message_cleaner.split_operands(
            instances[0].get("business_message", ""),
            comparison.operator,
            len(comparison.lhs.variables()),
            rhs_terms,
        )
        # A single aggregate variable bound to N facts is often enumerated by
        # name in the message; those names label the FACTS, not the variable.
        rhs_vars = comparison.rhs_vars
        if len(rhs_vars) == 1:
            fact_count = len(by_var.get(rhs_vars[0], []))
            if fact_count > 1:
                aggregated = message_cleaner.split_aggregated_terms(
                    instances[0].get("business_message", ""),
                    comparison.operator, fact_count,
                )

    lhs_vars = comparison.lhs_vars if comparison is not None else []
    rhs_vars = comparison.rhs_vars if comparison is not None else []

    for var, var_facts in by_var.items():
        first = var_facts[0]
        concept = first.get("concept", "")

        meta = json_map.get(var) or {}
        label = (meta.get("label") or "").strip()
        source = "json" if label else ""

        if not label and index is not None and concept:
            label = (index.concept_label(concept) or "").strip()
            source = "label_linkbase" if label else source

        # Backtracking labels are only preferred over the message when they
        # read as a business name. A backtracking row label is frequently a
        # grid coordinate ('Y250') or a table caption, which names a location
        # rather than the value — those fall through to the message instead.
        if not label and rule.get("has_backtracking"):
            for candidate in (first.get("column_label"), first.get("row_label"),
                              first.get("table_header")):
                if _looks_like_business_name(candidate):
                    label, source = candidate.strip(), "backtracking"
                    break

        if not label:
            label, source = _message_label(var, lhs_vars, rhs_vars,
                                           message_lhs, message_rhs) or ("", source)

        # Any remaining backtracking text is better than nothing, even if it is
        # only a cell coordinate — it still tells the user where to look.
        if not label and rule.get("has_backtracking"):
            label = (first.get("column_label") or first.get("row_label")
                     or first.get("table_header") or "").strip()
            source = "backtracking" if label else source

        if not label and concept:
            label = taxonomy_index.humanize_local_name(concept)
            source = "concept_name"

        if not label:
            # Never surface a raw variable id: '$V8' is an internal handle,
            # and printing it tells the user nothing about which figure is
            # meant. Saying the validation output did not name it is both
            # honest and more useful.
            label, source = "a value the validation output does not name", "unnamed"

        hint = _qualification_hint(meta.get("dimensional_qualification") or [])
        if hint and hint.lower() not in label.lower():
            label = f"{label} ({hint})"

        labels[var] = label
        sources[var] = source

    _prefer_message_when_labels_collide(
        labels, sources, lhs_vars, rhs_vars, message_lhs, message_rhs,
    )
    _disambiguate(labels, sources, by_var, index)
    if aggregated:
        labels["_aggregated_fact_labels"] = aggregated  # type: ignore[assignment]
    # Variables whose label came from the message AND that the formula
    # aggregates: the message already worded the aggregation, so the renderer
    # must not narrate sum() a second time.
    if comparison is not None and comparison.rhs is not None and comparison.rhs.uses_aggregation():
        phrase_vars = {v for v in rhs_vars if sources.get(v) == "message"}
        if phrase_vars and not aggregated:
            labels["_aggregate_phrase_vars"] = phrase_vars  # type: ignore[assignment]
    return labels, sources


def _message_label(var, lhs_vars, rhs_vars, message_lhs, message_rhs) -> tuple[str, str] | None:
    if var in lhs_vars and message_lhs:
        return message_lhs, "message"
    if var in rhs_vars and message_rhs:
        position = rhs_vars.index(var)
        if position < len(message_rhs):
            return message_rhs[position], "message"
    return None


# A business name has a lowercase letter and either a space or enough length to
# be a word rather than a grid reference. 'Y250', 'X030', 'R0020_10' fail;
# 'Cash reserves with RBI', 'Complaints pending' pass.
def _looks_like_business_name(text: str | None) -> bool:
    candidate = (text or "").strip()
    if len(candidate) < 4:
        return False
    if not any(ch.islower() for ch in candidate):
        return False
    return " " in candidate


def _prefer_message_when_labels_collide(
    labels: dict[str, str], sources: dict[str, str],
    lhs_vars: list[str], rhs_vars: list[str],
    message_lhs: str | None, message_rhs: list[str] | None,
) -> None:
    """When both sides of a comparison resolve to the SAME label, prefer the
    message's own wording — it is the only source that distinguishes them.

    This is the case where two variables are the same XBRL concept separated
    only by dimensional context (measured on 4044: both sides are
    'ComplaintsPending', so the taxonomy label is identical for each and the
    explanation reads 'Complaints pending is 4 higher than Complaints
    pending'). The message says 'Complaints pending … for 3. Other complaints
    = Pendency for less than 1 month + …', which names them apart.

    Only applied when the message actually yields DIFFERENT labels — a swap
    that reintroduced the collision would gain nothing.
    """
    if not message_lhs or not message_rhs:
        return
    side_labels = {labels.get(v) for v in lhs_vars} & {labels.get(v) for v in rhs_vars}
    side_labels.discard(None)
    if not side_labels:
        return
    if message_lhs in message_rhs:
        return
    for var in lhs_vars:
        if labels.get(var) in side_labels:
            labels[var], sources[var] = message_lhs, "message"
    for position, var in enumerate(rhs_vars):
        if labels.get(var) in side_labels and position < len(message_rhs):
            labels[var], sources[var] = message_rhs[position], "message"


def _disambiguate(
    labels: dict[str, str], sources: dict[str, str],
    by_var: dict[str, list[dict]], index=None,
) -> None:
    """When several variables resolve to the SAME label, qualify each one from
    evidence that actually differs between them.

    This is not cosmetic. A rule like
        round($V1 div 100000)*100000 = round(($V2+$V3+$V4+$V5) div 100000)*100000
    can bind all five variables to one concept (SubstandardAdvances),
    separated only by their dimensional context. Rendered with five identical
    labels the explanation reads "Substandard advances must equal Substandard
    advances + Substandard advances + …", which invites the reader — and the
    LLM — to conclude the five are the same value.

    Qualifiers are DERIVED, never invented, in this order:
      1. the context segment unique to this variable, resolved to its taxonomy
         member label when the taxonomy knows it, otherwise CamelCase-split;
      2. the backtracking cell code / row label.
    When nothing distinguishes them, the labels are left identical — the
    renderer still prints each variable's own context on its own row, so the
    facts stay separable even then.
    """
    counts: dict[str, int] = {}
    for label in labels.values():
        counts[label] = counts.get(label, 0) + 1

    colliding = {var for var, label in labels.items() if counts.get(label, 0) > 1}
    if not colliding:
        return

    qualifiers = _context_qualifiers(colliding, by_var, index)
    for var in colliding:
        qualifier = qualifiers.get(var) or _backtracking_qualifier(by_var.get(var))
        if qualifier:
            labels[var] = f"{labels[var]} — {qualifier}"
            sources[var] = f"{sources.get(var, '')}+context"


def _context_qualifiers(
    variables: set[str], by_var: dict[str, list[dict]], index,
) -> dict[str, str]:
    """A short distinguishing phrase per variable, from the parts of its
    context id that no other colliding variable has.

    Context ids in this corpus concatenate period and dimension members with
    '_' ('asof_20260630_OtherMember'), so the set difference of segments is
    exactly the dimensional distinction between two otherwise identical facts.
    Segments shared by every variable (the period) drop out by construction.
    """
    segments: dict[str, set[str]] = {}
    for var in variables:
        tokens: set[str] = set()
        for fact in by_var.get(var) or []:
            context = (fact.get("context") or "").strip()
            if context:
                tokens.update(part for part in context.split("_") if part)
        segments[var] = tokens

    out: dict[str, str] = {}
    for var, tokens in segments.items():
        others: set[str] = set()
        for other, other_tokens in segments.items():
            if other != var:
                others |= other_tokens
        unique = sorted(tokens - others)
        if not unique:
            continue
        phrases = []
        for token in unique:
            label = ""
            if index is not None:
                label = (index.concept_label(token) or "").strip()
            phrases.append(_strip_role_suffix(label) or taxonomy_index.humanize_local_name(
                token, ("Member", "Domain", "Axis")))
        phrase = ", ".join(p for p in phrases if p)
        if phrase:
            out[var] = phrase
    return out


_ROLE_SUFFIX_RE = __import__("re").compile(r"\s*\[(member|axis|domain|line items|table|abstract)\]\s*$", __import__("re").IGNORECASE)


def _strip_role_suffix(label: str) -> str:
    """Drop a taxonomy role marker from a label ('Other [member]' -> 'Other').

    These markers exist to disambiguate roles inside the taxonomy; repeating
    them inside a business label just adds noise to every qualifier.
    """
    return _ROLE_SUFFIX_RE.sub("", (label or "").strip()).strip()


def _backtracking_qualifier(facts: list[dict] | None) -> str:
    for fact in facts or []:
        hint = (fact.get("cell_code") or fact.get("row_label") or "").strip()
        if hint:
            return hint
    return ""


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 3 — evaluation
# ═════════════════════════════════════════════════════════════════════════════

def _facts_by_var(instance: dict) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for fact in instance.get("facts") or []:
        out.setdefault(fact["var"], []).append(fact.get("value", ""))
    return out


def evaluate_instance(rule: dict, instance: dict):
    """(comparison, result) for one failing instance; result is None when the
    numbers could not be established."""
    comparison = formula_expression.parse_formula(rule.get("formula_expression", ""))
    if comparison is None:
        return None, None
    return comparison, formula_expression.evaluate(comparison, _facts_by_var(instance))


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 4 — rendering
# ═════════════════════════════════════════════════════════════════════════════

def _format_amount(value, unit: str = "") -> str:
    if value is None:
        return "not reported"
    try:
        dec = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return str(value)
    try:
        text = f"{dec:,.0f}" if dec == dec.to_integral_value() else f"{dec:,.4f}".rstrip("0").rstrip(".")
    except (InvalidOperation, ValueError):
        text = str(dec)
    symbol = _CURRENCY_SYMBOLS.get((unit or "").strip().upper())
    if symbol:
        return f"{symbol}{text}"
    unit_text = (unit or "").strip()
    if unit_text and unit_text.upper() not in ("PURE", "INF"):
        return f"{text} {unit_text}"
    return text


def _humanize_rule_name(name: str) -> str:
    return taxonomy_index.humanize_local_name(
        (name or "").replace("_", " ").replace("-", " ")
    ) or name


# Longest AST restatement that still reads as a sentence. Beyond this the
# expression is a nested conditional whose literal restatement is harder to
# follow than the rule's own authored message — which is displayed instead.
_MAX_RULE_SENTENCE_CHARS = 300


def _all_vars_labelled(comparison, labels: dict[str, str]) -> bool:
    """Whether every variable the expression references resolved to a business
    label. When one did not — most often because the rule has no variable rows
    at all (a presence check) — the rule is stated from the validator's own
    message instead of from the expression, so no raw 'V1' can reach the user.
    """
    if comparison is None:
        return False
    return all(labels.get(var) for var in comparison.variables())


def _readable_rule_sentence(comparison, labels: dict[str, str]) -> str:
    """The AST restatement, or "" when it would not help the reader.

    Suppressed when a variable has no business label (so no 'V1' can leak) or
    when the restatement grows past _MAX_RULE_SENTENCE_CHARS. Both are
    structural tests on the expression, not on any particular rule.
    """
    if not _all_vars_labelled(comparison, labels):
        return ""
    sentence = _rule_sentence(comparison, labels)
    return sentence if len(sentence) <= _MAX_RULE_SENTENCE_CHARS else ""


def _rule_sentence(comparison, labels: dict[str, str]) -> str:
    """The validation rule restated in business language, from the AST — never
    the raw XPath. Rounding is stated separately in words."""
    if comparison is None:
        return ""
    phrase_vars = labels.get("_aggregate_phrase_vars") or set()
    lhs = formula_expression.describe(comparison.lhs.core(), labels, phrase_vars)
    if comparison.boolean_only or comparison.rhs is None:
        return formula_expression.describe(comparison.lhs, labels, phrase_vars)
    rhs = formula_expression.describe(comparison.rhs.core(), labels, phrase_vars)
    meaning = formula_expression.OPERATOR_MEANING.get(comparison.operator, comparison.operator)
    return f"{lhs} must be {meaning} {rhs}"


def _how_to_fix(comparison, result: dict, labels: dict[str, str]) -> str:
    if result is None or comparison is None:
        return ("Review the values involved in this check in the source data and revalidate "
                "the return.")
    if result.get("boolean_only"):
        missing = result.get("missing_vars") or []
        named = [labels.get(v) for v in missing if labels.get(v)]
        if named:
            return (f"Report {_join(named)} in the source data, then regenerate and "
                    f"revalidate the return.")
        return ("Review the values this rule checks in the source data so the condition is "
                "met, then regenerate and revalidate the return.")
    lhs_label = labels.get(comparison.lhs_vars[0], "the total") if comparison.lhs_vars else "the total"
    rhs_labels = [labels.get(v, v) for v in comparison.rhs_vars]
    if len(rhs_labels) > 1:
        return (f"Check {lhs_label} against its components ({_join(rhs_labels)}) in the source "
                f"data, correct whichever is wrong, then regenerate and revalidate the return.")
    other = rhs_labels[0] if rhs_labels else "the compared value"
    return (f"Review {lhs_label} and {other} in the source data to determine which needs "
            f"correcting, then regenerate and revalidate the return.")


def _join(items: list[str]) -> str:
    items = [i for i in items if i]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def build_sections(
    rule: dict, comparison, result: dict | None, labels: dict[str, str],
    llm_text: dict | None = None,
) -> list[dict]:
    """The explanation as typed, presentation-free sections.

    This is the canonical form. render_explanation() serialises it to text and
    the UI renders it directly, so the two can never disagree about structure
    and no markdown markers have to survive a round-trip through a string
    parser. Section kinds:

        {"kind": "headline", "text": str}
        {"kind": "rule",     "heading": str, "text": str}
        {"kind": "values",   "heading": str,
         "items": [{"label", "value", "note"?, "context"?}]}
        {"kind": "points",   "heading": str, "bullets": [str, ...]}
        {"kind": "note",     "text": str}
    """
    instances = rule.get("instances") or []
    instance = instances[0] if instances else {"facts": [], "business_message": ""}
    facts = instance.get("facts") or []

    by_var: dict[str, list[dict]] = {}
    for fact in facts:
        by_var.setdefault(fact["var"], []).append(fact)

    unit = next((f["unit"] for f in facts if f.get("unit")), "")
    evaluated = comparison is not None and result is not None and not result.get("boolean_only")

    sections: list[dict] = [{
        "kind": "headline",
        "text": f"{_humanize_rule_name(rule.get('rule_name', ''))} did not pass validation.",
    }]

    rule_sentence = _readable_rule_sentence(comparison, labels)
    if rule_sentence:
        sections.append({"kind": "rule", "heading": "Validation Rule", "text": rule_sentence})

    if evaluated:
        items = _reported_value_items(comparison, by_var, labels, unit, rule)
        if items:
            sections.append({"kind": "values", "heading": "Reported Values", "items": items})
        comparison_items = _comparison_items(comparison, result, labels, unit)
        if comparison_items:
            sections.append({"kind": "values", "heading": "Comparison", "items": comparison_items})
    else:
        # A rule that yields a verdict rather than two comparable numbers still
        # has facts worth showing, and its authored message is often clearer
        # than any restatement of a nested conditional.
        if comparison is not None and facts:
            items = _plain_fact_items(comparison, by_var, labels, unit, rule)
            if items:
                sections.append({"kind": "values", "heading": "Reported Values", "items": items})
        cleaned = message_cleaner.normalise_message(instance.get("business_message", ""))
        if cleaned:
            sections.append({"kind": "rule", "heading": "Validator Message", "text": cleaned})

    sections.append({
        "kind": "points", "heading": "Why It Failed",
        "bullets": _why_failed_points(comparison, result, labels, unit, llm_text),
    })

    where = _where_to_check_items(by_var, labels, rule)
    if where:
        sections.append({"kind": "values", "heading": "Where to Check", "items": where})

    if len(instances) > 1:
        sections.append({
            "kind": "note",
            "text": (f"This rule failed for {len(instances)} reported items; "
                     f"the first is shown above."),
        })

    sections.append({
        "kind": "points", "heading": "How to Fix",
        "bullets": _how_to_fix_points(comparison, result, labels, llm_text),
    })
    return sections


def render_explanation(
    rule: dict, comparison, result: dict | None, labels: dict[str, str],
    llm_text: dict | None = None,
) -> str:
    """The explanation as plain text, serialised from build_sections().

    Deliberately free of markdown emphasis markers: the UI renders headings as
    real headings, and any consumer that shows the string as-is (logs, tests, a
    plain-text client) sees clean prose rather than literal '**'.
    """
    return sections_to_text(
        rule.get("rule_name", ""),
        build_sections(rule, comparison, result, labels, llm_text),
    )


def sections_to_text(rule_name: str, sections: list[dict]) -> str:
    lines: list[str] = [f"⚙ Formula Error — {rule_name}", ""]
    for section in sections:
        kind = section.get("kind")
        if kind == "headline":
            lines += [f"❌ {section['text']}", ""]
        elif kind == "rule":
            lines += [section["heading"], section["text"], ""]
        elif kind == "values":
            lines.append(section["heading"])
            for item in section["items"]:
                label = item.get("label", "")
                line = f"• {label}: {item.get('value', '')}" if label else f"• {item.get('value', '')}"
                if item.get("note"):
                    line += f" ({item['note']})"
                lines.append(line)
                if item.get("context"):
                    lines.append(f"   context: {item['context']}")
            lines.append("")
        elif kind == "points":
            lines.append(section["heading"])
            lines += [f"• {b}" for b in section["bullets"]]
            lines.append("")
        elif kind == "note":
            lines += [section["text"], ""]
    return "\n".join(lines).rstrip()


def _var_total(by_var: dict, var: str) -> Decimal | None:
    """The value bound to one variable: its single fact, or the sum when the
    variable legitimately binds several. Non-numeric facts are skipped, never
    read as 0."""
    total = Decimal(0)
    seen = False
    for fact in by_var.get(var, []):
        value = _decimal_or_none(fact.get("value"))
        if value is not None:
            total += value
            seen = True
    return total if seen else None


def _reported_value_items(comparison, by_var, labels, unit, rule) -> list[dict]:
    """One entry per FACT, never one per concept name.

    A rule can bind several variables to the same concept, separated only by
    dimensional context, each with its own value. The raw context id is only
    attached when the resolved labels are STILL identical after
    disambiguation — that is the one case where it is needed to tell the facts
    apart. When a business qualifier was derived, the label already carries the
    meaning and the internal id is noise.
    """
    items: list[dict] = []
    aggregated = labels.get("_aggregated_fact_labels")

    business_labels = [labels.get(v, v) for v in comparison.variables()]
    labels_are_ambiguous = len(set(business_labels)) < len(business_labels)

    def emit(var: str, sign: int = 1) -> None:
        facts = by_var.get(var, [])
        prefix = "" if sign > 0 else "less "
        label = f"{prefix}{labels.get(var, var)}"
        if not facts:
            items.append({"label": label, "value": "not reported"})
            return
        if len(facts) > 1 and aggregated and len(aggregated) == len(facts):
            for fact, name in zip(facts, aggregated):
                items.append({
                    "label": f"{prefix}{name}",
                    "value": _format_amount(_decimal_or_none(fact.get("value")),
                                            fact.get("unit") or unit),
                })
            return
        if len(facts) > 1:
            items.append({
                "label": label,
                "value": _format_amount(_var_total(by_var, var), _unit_of(by_var, var, unit)),
                "note": f"total of {len(facts)} reported values",
            })
            return
        fact = facts[0]
        entry = {
            "label": label,
            "value": _format_amount(_decimal_or_none(fact.get("value")), fact.get("unit") or unit),
        }
        note = _entered_note(fact, rule)
        if note:
            entry["note"] = note
        if labels_are_ambiguous and fact.get("context"):
            entry["context"] = fact["context"]
        items.append(entry)

    for var in comparison.lhs_vars:
        emit(var)
    signed = comparison.rhs.signed_variables() if comparison.rhs is not None else []
    for var, sign in (signed or [(v, 1) for v in comparison.rhs_vars]):
        emit(var, sign)
    return items


def _plain_fact_items(comparison, by_var, labels, unit, rule) -> list[dict]:
    """Every bound fact, in the order the expression references it — used for
    rules that produce a verdict rather than two comparable totals."""
    items: list[dict] = []
    business_labels = [labels.get(v, v) for v in comparison.variables()]
    ambiguous = len(set(business_labels)) < len(business_labels)
    for var in comparison.variables():
        for fact in by_var.get(var, []):
            entry = {
                "label": labels.get(var, var),
                "value": _format_amount(_decimal_or_none(fact.get("value")),
                                        fact.get("unit") or unit),
            }
            note = _entered_note(fact, rule)
            if note:
                entry["note"] = note
            if ambiguous and fact.get("context"):
                entry["context"] = fact["context"]
            items.append(entry)
    return items


def _comparison_items(comparison, result: dict, labels: dict[str, str], unit: str) -> list[dict]:
    """The two compared sides plus the difference, with raw and rounded kept
    apart so a rounded figure is never presented as the reported one."""
    rounded = bool(result.get("rounding_changed_a_value"))
    is_combination = (
        len(comparison.rhs_vars) > 1
        or (comparison.rhs is not None and comparison.rhs.uses_aggregation())
    )
    right_label = "Calculated/Combined" if is_combination else "Compared with"

    def side(raw, compared) -> str:
        if rounded and raw is not None and raw != compared:
            return f"{_format_amount(raw, unit)} → rounds to {_format_amount(compared, unit)}"
        return _format_amount(compared, unit)

    items = [
        {"label": "Reported", "value": side(result.get("lhs_raw"), result["lhs_value"])},
        {"label": right_label, "value": side(result.get("rhs_raw"), result["rhs_value"])},
    ]
    if not result.get("values_equal"):
        items.append({
            "label": "Difference" + (" (after rounding)" if rounded else ""),
            "value": _format_amount(abs(result["difference"]), unit),
        })
    if result.get("uses_rounding"):
        step = result.get("rounding_step")
        items.append({
            "label": "Rounding",
            "value": (f"nearest {_format_amount(step, unit)}" if step else "applied")
                     + ("" if rounded else " (does not change these values)"),
        })
    return items


def _why_failed_points(comparison, result, labels, unit, llm_text) -> list[str]:
    """Short, self-contained statements rather than one dense paragraph.

    Built from the AST and the verified result, so the wording adapts to the
    operator, the number of terms and whether rounding actually changed
    anything — no formula, concept or return is referenced by name.

    An LLM rewrite is used only when it passes the grounding gate; the
    deterministic points are always available underneath.
    """
    llm_points = _llm_points((llm_text or {}).get("why_failed"))
    if llm_points:
        return llm_points

    if result is None:
        return ["The values needed to check this rule could not be read from the "
                "validation output, so the size of the difference is not available."]
    if result.get("boolean_only"):
        return _boolean_points(comparison, result, labels)

    points: list[str] = []
    lhs_var = comparison.lhs_vars[0] if comparison.lhs_vars else ""
    lhs_label = labels.get(lhs_var, "The reported value")
    rhs_labels = [labels.get(v, v) for v in comparison.rhs_vars]

    lhs_raw = result.get("lhs_raw")
    rhs_raw = result.get("rhs_raw")
    points.append(f"{lhs_label} is reported as "
                  f"{_format_amount(lhs_raw if lhs_raw is not None else result['lhs_value'], unit)}.")

    if len(rhs_labels) > 1:
        points.append(f"{_join(rhs_labels)} together come to "
                      f"{_format_amount(rhs_raw if rhs_raw is not None else result['rhs_value'], unit)}.")
    elif rhs_labels:
        points.append(f"{rhs_labels[0]} is reported as "
                      f"{_format_amount(rhs_raw if rhs_raw is not None else result['rhs_value'], unit)}.")

    if result.get("rounding_changed_a_value"):
        step = result.get("rounding_step")
        step_text = f" to the nearest {_format_amount(step, unit)}" if step else ""
        points.append(
            f"This rule compares values after rounding{step_text}, which makes them "
            f"{_format_amount(result['lhs_value'], unit)} and "
            f"{_format_amount(result['rhs_value'], unit)}."
        )

    meaning = formula_expression.OPERATOR_MEANING.get(result["operator"], result["operator"])
    subject = "the combined value" if len(rhs_labels) > 1 else (rhs_labels[0] if rhs_labels else "the compared value")
    points.append(f"The rule requires {lhs_label} to be {meaning} {subject}.")

    if result.get("passes"):
        points.append("Re-checking the reported values satisfies that condition, so the "
                      "underlying data may already have been corrected.")
    elif result.get("values_equal"):
        points.append("The two values are exactly equal, which does not satisfy the "
                      "condition this rule requires.")
    else:
        direction = "higher" if result["relationship"] == "lhs_greater" else "lower"
        points.append(f"They differ by {_format_amount(abs(result['difference']), unit)} "
                      f"({lhs_label} is {direction}), so the check fails.")
    return points


def _boolean_points(comparison, result, labels) -> list[str]:
    """Points for a rule that yields a verdict rather than two comparable
    numbers — a presence check, a conditional, or a boolean combination.

    The condition is described from the AST, so the wording follows whatever
    the rule actually says instead of assuming it is a presence check (the
    corpus contains 'not(empty($V))', 'if (X = 0) then (Y = 0) else …' and
    'A or B' forms, and they mean different things).
    """
    points: list[str] = []
    condition = _readable_rule_sentence(comparison, labels)

    if condition:
        points.append(f"This rule requires that {condition}.")
    if result.get("passes"):
        points.append("Re-checking the reported values satisfies that condition, so the "
                      "underlying data may already have been corrected.")
    else:
        missing = result.get("missing_vars") or []
        named = [labels.get(v) for v in missing if labels.get(v)]
        if named:
            points.append(f"No value was reported for {_join(named)}.")
        points.append("The reported data does not satisfy the condition this rule checks, "
                      "so the check fails.")
    return points or ["The reported data does not satisfy the condition this rule checks."]


def _how_to_fix_points(comparison, result, labels, llm_text) -> list[str]:
    llm_points = _llm_points((llm_text or {}).get("how_to_fix"))
    if llm_points:
        return llm_points
    return [_how_to_fix(comparison, result, labels)]


def _llm_points(text: str | None) -> list[str]:
    """Split already-grounded LLM prose into short bullets on line and sentence
    boundaries. Returns [] when there is nothing usable, so the caller falls
    back to the deterministic points."""
    if not text:
        return []
    import re as _re
    raw = [part.strip(" •-\t") for part in str(text).splitlines() if part.strip()]
    if len(raw) == 1:
        raw = [s.strip() for s in _re.split(r"(?<=[.!?])\s+(?=[A-Z(])", raw[0]) if s.strip()]
    points = [p if p.endswith((".", "!", "?")) else p + "." for p in raw if len(p) > 1]
    return points[:6]


def _decimal_or_none(value):
    try:
        return Decimal(str(value).replace(",", "") or "0")
    except (InvalidOperation, TypeError, ValueError):
        return None


def _unit_of(by_var, var, default) -> str:
    for fact in by_var.get(var, []):
        if fact.get("unit"):
            return fact["unit"]
    return default


def _entered_note(fact: dict, rule: dict) -> str:
    """'entered as 13,459.2420 in cell Y250_X030' — only from a backtracking
    table, and only when the entered figure differs from the instance figure
    (they are on different scales). Never merged into the value itself."""
    if not rule.get("has_backtracking"):
        return ""
    entered = (fact.get("entered_value") or "").strip()
    cell = (fact.get("cell_code") or "").strip()
    if not entered or entered.replace(",", "") == str(fact.get("value", "")).replace(",", ""):
        return f"cell {cell}" if cell else ""
    return f"entered as {entered}" + (f" in cell {cell}" if cell else "")


def _where_to_check_items(by_var, labels, rule) -> list[dict]:
    """Source locations, only from evidence — backtracking DB table/cell, or a
    JSON db_mapping. Nothing is synthesised; the section is omitted when
    neither is available."""
    items: list[dict] = []
    seen: set[str] = set()
    for var, facts in by_var.items():
        if not facts:
            continue
        fact = facts[0]
        table = (fact.get("db_table") or "").strip()
        cell = (fact.get("cell_code") or "").strip()
        if table and cell:
            location = f"{table} — cell {cell}"
        elif table:
            location = table
        else:
            location = (fact.get("_db_location") or "").strip()
        if not location or location in seen:
            continue
        seen.add(location)
        items.append({"label": labels.get(var, var), "value": location})
    return items


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 5 — LLM payload
# ═════════════════════════════════════════════════════════════════════════════

def build_llm_payload(rule, comparison, result, labels) -> tuple[dict, list[str]] | None:
    if comparison is None or result is None or result.get("boolean_only"):
        return None

    instances = rule.get("instances") or []
    facts = instances[0].get("facts") if instances else []
    by_var: dict[str, list[dict]] = {}
    for fact in facts or []:
        by_var.setdefault(fact["var"], []).append(fact)

    def total(var: str):
        out = Decimal(0)
        seen = False
        for fact in by_var.get(var, []):
            value = _decimal_or_none(fact.get("value"))
            if value is not None:
                out += value
                seen = True
        return str(out) if seen else None

    lhs_var = comparison.lhs_vars[0] if comparison.lhs_vars else ""
    lhs_label = labels.get(lhs_var, lhs_var)
    signed = comparison.rhs.signed_variables() if comparison.rhs is not None else []
    terms = signed or [(v, 1) for v in comparison.rhs_vars]

    def describe_var(var: str, side: str, sign: int) -> dict:
        """One variable's COMPLETE binding: its own facts, each with the value,
        context, unit and decimals the error file reported for it.

        The variable id is carried so the mapping is unambiguous even when
        several variables resolve to the same concept name — the previous
        payload exposed only (label, total), which let a model reading five
        identically-labelled terms conclude they all held the same value.
        """
        var_facts = by_var.get(var, [])
        return {
            "variable": var,
            "side": side,
            "sign": "plus" if sign > 0 else "minus",
            "label": labels.get(var, var),
            "concept_name": (var_facts[0].get("concept") if var_facts else "") or "",
            "total_value": total(var),
            "facts": [
                {
                    "value": (f.get("value") or "").strip(),
                    "context": (f.get("context") or "").strip(),
                    "unit": (f.get("unit") or "").strip(),
                    "decimal": (f.get("decimal") or "").strip(),
                    "precision": (f.get("precision") or "").strip(),
                }
                for f in var_facts
            ],
        }

    variables = [describe_var(lhs_var, "left", 1)] if lhs_var else []
    variables += [describe_var(v, "right", s) for v, s in terms]

    required = [lhs_label] + [labels.get(v, v) for v, _s in terms]

    payload = {
        "formula": comparison.source,
        "rule": _rule_sentence(comparison, labels),
        "operator_meaning": result["operator_meaning"],
        "relationship": result["relationship"],
        "relationship_meaning": _relationship_sentence(
            result["relationship"], lhs_label, [labels.get(v, v) for v, _s in terms]),

        # Per-variable bindings — the authoritative fact-to-variable mapping.
        "variables": variables,
        "note_on_variables": (
            "Each entry above is a separate reported fact with its own value and "
            "context. Two entries may share a concept name and still hold "
            "different values; never assume otherwise."
        ),

        # Sides, with raw and rounded kept distinct.
        "left_side": {
            "label": lhs_label,
            "raw_value": None if result.get("lhs_raw") is None else str(result["lhs_raw"]),
            "compared_value": str(result["lhs_value"]),
        },
        "right_side": {
            "raw_value": None if result.get("rhs_raw") is None else str(result["rhs_raw"]),
            "compared_value": str(result["rhs_value"]),
            "is_a_combination_of_several_values": len(terms) > 1,
        },
        "difference_between_compared_values": str(result["difference"]),
        "raw_difference": (None if result.get("raw_difference") is None
                           else str(result["raw_difference"])),
        "values_are_equal": result["values_equal"],
        "rule_is_satisfied_by_these_values": result["passes"],
        "rounding": {
            "applied": result["uses_rounding"],
            "changed_a_value": result.get("rounding_changed_a_value", False),
            "step": None if result.get("rounding_step") is None else str(result["rounding_step"]),
        },
        "number_of_failing_items": len(instances),
    }
    # Drives the grounding gate's false-uniformity check: when the bound facts
    # do NOT all hold the same value, any claim that they do is a hallucination
    # regardless of how it is worded.
    distinct = {v["total_value"] for v in variables if v["total_value"] is not None}
    payload["_values_are_uniform"] = len(distinct) <= 1
    # Concept ids are supplied so the model can tell same-named variables
    # apart, but they are internal XBRL identifiers — quoting one back to the
    # user exposes implementation detail instead of business meaning.
    payload["_technical_names"] = [
        v["concept_name"] for v in variables
        if v.get("concept_name") and v["concept_name"] not in (v.get("label") or "")
    ]
    return payload, [t for t in required if t]


def _relationship_sentence(relationship: str, lhs_label: str, rhs_labels: list[str]) -> str:
    other = _join(rhs_labels) or "the compared value"
    if relationship == "lhs_greater":
        return f"{lhs_label} is actually GREATER than {other}"
    if relationship == "lhs_less":
        return f"{lhs_label} is actually LESS than {other}"
    return f"{lhs_label} and {other} are actually EQUAL"


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 6 — orchestration
# ═════════════════════════════════════════════════════════════════════════════

def _load_json(form_id: str) -> dict | None:
    if not form_id:
        return None
    try:
        from backend.tools import taxonomy_lookup
        return taxonomy_lookup.get_return_json(form_id)
    except Exception as exc:
        logger.info("[formula_error] no JSON extract for form_id=%s (%s)", form_id, exc)
        return None


def _load_index(form_id: str, error_file_path: str):
    extra: list[str] = []
    try:
        from backend.tools import instance_context
        for ref in instance_context.schema_refs(error_file_path, form_id):
            extra.extend(taxonomy_index.find_roots_for_schema(ref))
    except Exception as exc:
        logger.debug("[formula_error] schemaRef resolution skipped: %s", exc)
    try:
        return taxonomy_index.get_index_for_form(form_id, tuple(extra))
    except Exception as exc:
        logger.info("[formula_error] taxonomy index unavailable: %s", exc)
        return None


def explain_one_rule(rule: dict, taxonomy_json, index, settings) -> dict:
    """Never raises — any failure falls through to the deterministic template."""
    out = dict(rule)
    try:
        instances = rule.get("instances") or []
        instance = instances[0] if instances else {"facts": []}
        comparison, result = evaluate_instance(rule, instance)
        labels, sources = resolve_labels(rule, comparison, taxonomy_json, index)

        # LLM phrasing is OPTIONAL enrichment and is isolated accordingly: it
        # runs after the deterministic explanation is already computable, and
        # any failure inside it degrades to the deterministic wording rather
        # than discarding the whole explanation. Without this isolation a
        # malformed model response ('why_failed' returned as a JSON array)
        # propagated to the outer handler and replaced a complete, correct
        # explanation with a one-line "review the values" fallback.
        llm_text = _phrase_via_llm(rule, comparison, result, labels, settings)

        sections = build_sections(rule, comparison, result, labels, llm_text)
        out["explanation"] = sections_to_text(rule.get("rule_name", ""), sections)
        # Structured form for the UI, so headings/bullets are rendered as real
        # elements instead of being recovered by parsing the string back.
        out["explanation_sections"] = sections
        out["_label_sources"] = sources
        out["_evaluated"] = result is not None
        out["_error_category"] = "formula_error"
        return out
    except Exception as exc:
        logger.error("[formula_error] explain failed for %r: %s", rule.get("rule_name"), exc)
        out["explanation"] = (
            f"⚙ Formula Error — {rule.get('rule_name', '')}\n\n"
            "This validation rule did not pass. Review the values involved in this check "
            "in the source data and revalidate the return."
        )
        out["_error_category"] = "formula_error"
        return out


def _llm_may_phrase_why() -> bool:
    import os
    return os.getenv("ERROR_EXPLAIN_LLM_WHY", "0").strip().lower() in ("1", "true", "yes", "on")


def _phrase_via_llm(rule, comparison, result, labels, settings) -> dict | None:
    """Grounded LLM wording, or None. Never raises."""
    if not settings.get("enabled"):
        return None
    try:
        built = build_llm_payload(rule, comparison, result, labels)
        if not built:
            return None
        payload, required = built
        # "Why it failed" is deterministic by default. It is a sequence of
        # verified arithmetic facts, and the deterministic generator states
        # them as short, separate points; asking a model to restate them
        # reliably produced one dense line instead ("reported value:
        # 1240058000, compared value: 1274362000, outcome: not satisfied"),
        # which is strictly worse to read and adds a hallucination surface for
        # no gain. Set ERROR_EXPLAIN_LLM_WHY=1 to let the model phrase it.
        fields = {
            "how_to_fix": ("one short sentence telling the user what to review and "
                           "revalidate, in business terms"),
        }
        if _llm_may_phrase_why():
            fields["why_failed"] = (
                "3 to 5 VERY SHORT sentences, one per line, each stating one fact: "
                "the reported value, the compared value, any rounding, what the rule "
                "requires, and the outcome. No bullet characters, no paragraph."
            )
        return error_llm.phrase(payload, required, fields, settings)
    except Exception as exc:
        logger.warning(
            "[formula_error] LLM phrasing failed for %r (%s) — using deterministic wording",
            rule.get("rule_name"), exc,
        )
        return None


def explain_formula_rules(rules: list[dict], form_id: str = "", error_file_path: str = "") -> list[dict]:
    if not rules:
        return []
    taxonomy_json = _load_json(form_id)
    index = _load_index(form_id, error_file_path)
    settings = error_llm.llm_settings()

    def worker(rule: dict) -> dict:
        return explain_one_rule(rule, taxonomy_json, index, settings)

    workers = max(1, min(settings.get("max_concurrency", 2), len(rules)))
    if workers == 1 or not settings.get("enabled"):
        return [worker(rule) for rule in rules]

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=workers) as executor:
        return list(executor.map(worker, rules))


def explain_formula_error_file(
    html_path: str, form_id: str = "", max_rules: int = 3, offset: int = 0,
) -> list[dict]:
    """Top-level entry point: parse, then explain one batch starting at *offset*."""
    rules = parse_formula_errors_v2(html_path)
    offset = max(0, int(offset or 0))
    return explain_formula_rules(
        rules[offset:offset + max_rules], form_id=form_id, error_file_path=html_path,
    )
