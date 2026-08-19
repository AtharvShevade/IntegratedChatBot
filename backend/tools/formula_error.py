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
from backend.tools import (
    error_card, error_llm, formula_expression, formula_kind, message_cleaner,
    taxonomy_index,
)

logger = logging.getLogger(__name__)

__all__ = [
    "parse_formula_errors_v2", "explain_formula_error_file",
    "explain_formula_rules", "build_llm_payload", "render_explanation",
    "build_sections", "sections_to_text", "resolve_labels",
    # v2 unified error card — see backend/tools/error_card.py
    "build_card_sections", "render_card",
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
            label, source = _UNNAMED_LABEL, "unnamed"

        hint = _qualification_hint(meta.get("dimensional_qualification") or [])
        if hint and hint.lower() not in label.lower():
            label = f"{label} ({hint})"

        labels[var] = label
        sources[var] = source

    # The rule's own terminology for the figure it constrains, when the
    # validator states it and the assertion name confirms it.
    _prefer_rule_terminology(labels, sources, comparison, rule, message_lhs)

    # Variables the cascade above could not name — either because they have no
    # row in the table, or because their side of the formula is not additive
    # and the existing message split therefore never ran for them.
    _name_unlabelled_variables(
        labels, sources, comparison, by_var,
        instances[0].get("business_message", ""),
    )

    # Still unnamed after every naming source: say what the value DOES in the
    # rule rather than repeating that it has no name. See _apply_role_labels.
    _apply_role_labels(labels, sources, comparison, by_var, index)

    _prefer_message_when_labels_collide(
        labels, sources, lhs_vars, rhs_vars, message_lhs, message_rhs,
    )
    _disambiguate(labels, sources, by_var, index,
                  protect=set(lhs_vars) if len(lhs_vars) == 1 else None)
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


# Shortest message-derived name that can be trusted as a substring match against
# an assertion id. Below this, a coincidental hit is likely ("Total", "Amount").
_MIN_RULE_TERM_CHARS = 12


def _flat(text: str) -> str:
    """Case-folded, whitespace-collapsed text — for matching a human-written
    phrase against another human-written phrase.

    Deliberately NOT punctuation-stripped or space-stripped. A compacted match
    ("totaltermloanssanctioned") also hits camel-case assertion IDS like
    'Sec-8_SectoralCredit_TotalTermLoansSanctionedAndTotalTermLoansDisbursed',
    which embed concept names without being a statement of the rule — and on
    those files the taxonomy label is the better name, not the message's.
    """
    import re as _re
    return _re.sub(r"\s+", " ", str(text or "")).strip().lower()


def _prefer_rule_terminology(labels, sources, comparison, rule, message_lhs) -> None:
    """Use the rule's OWN name for the figure it constrains, when the validator
    message names it and the assertion label confirms that name.

    R061 is the case: the assertion is literally

        TCE as % of Capital Funds = TCE * 100/ ([Regulatory Capital …])

    and its message repeats "TCE as % of Capital Funds", while the taxonomy
    label for the same concept is "Aggregate credit exposure as percentage of
    capital funds". Both are correct, but only one is the terminology the rule,
    the message and the form all use, so a headline built from the other reads
    as though it were about a different figure.

    Deliberately narrow. It applies to the LEFT-hand variable only, and only
    when the message's wording is present in the assertion name — two
    independent sources agreeing. A label with no such corroboration keeps
    whatever the taxonomy cascade produced, so nothing else in the corpus moves.
    """
    if not message_lhs or comparison is None or not comparison.lhs_vars:
        return
    var = comparison.lhs_vars[0]
    current = labels.get(var) or ""
    if current == message_lhs:
        return
    term = _flat(message_lhs)
    if len(term) < _MIN_RULE_TERM_CHARS or " " not in term:
        return
    name = _flat(rule.get("rule_name", ""))
    # The assertion must STATE the name, not merely contain its letters: an
    # identifier has no spaces, so requiring the spaced phrase verbatim is what
    # separates 'TCE as % of Capital Funds = …' from 'Sec-8_SectoralCredit_…'.
    if " " not in name or term not in name:
        return
    labels[var] = message_lhs
    sources[var] = "rule_name"


def _message_label(var, lhs_vars, rhs_vars, message_lhs, message_rhs) -> tuple[str, str] | None:
    if var in lhs_vars and message_lhs:
        return message_lhs, "message"
    if var in rhs_vars and message_rhs:
        position = rhs_vars.index(var)
        if position < len(message_rhs):
            return message_rhs[position], "message"
    return None


# The honest last resort when no source names a variable. Reached far less often
# now that the two resolvers below run, but never removed: printing a raw '$V8'
# tells the reader nothing, and inventing a name would be worse than either.
_UNNAMED_LABEL = "a value not named in the validation output"


# ─────────────────────────────────────────────────────────────────────────────
# Two additional, strictly-gated label sources.
#
# Both exist because the existing message split (message_cleaner.split_operands)
# is driven by `rhs.signed_variables()`, which is [] for any right-hand side
# that is not purely additive. Every ratio, percentage and weighted-average rule
# therefore reached the fallback with no name at all, even when the validator's
# own message spelled every operand out:
#
#   '"TCE as % of Capital Funds" = TCE * 100/ ([Regulatory Capital (Tier I +
#    Tier II) of Previous March) + (Capital Infusion during the period)]'
#
# Neither resolver ever runs for a variable that already has a label, and both
# refuse the whole message unless the operand count matches the formula exactly
# — the same arity gate the existing message path uses. A mismatch keeps the
# previous behaviour rather than assigning names by guesswork.
# ─────────────────────────────────────────────────────────────────────────────

_ENUMERATED_FIELD_RE = __import__("re").compile(r"\d+\s*[.)]\s*([^;]+?)\s*(?=;|$)")


def _enumerated_message_fields(message: str) -> list[str]:
    """Field names from a '1.Foo; 2.Bar; 3.Baz;' enumeration, or [].

    This is the shape the validator uses for mandatory-field rules, whose
    variables have no rows in the error table at all — so this is the ONLY
    source that can name them.
    """
    import re as _re
    text = _re.sub(r"\s+", " ", message or "").strip()
    if not text:
        return []
    names = [_tidy_operand(n) for n in _ENUMERATED_FIELD_RE.findall(text)]
    names = [n for n in names if n]
    if len(names) < 2:
        return []
    if not all(message_cleaner.looks_like_label(n) for n in names):
        return []
    return names


# ─────────────────────────────────────────────────────────────────────────────
# Semantic role fallback.
#
# When no source can NAME a variable, the previous fallback repeated one
# sentence for every such operand:
#
#   "… must be equal to the total of a value not named in the validation output
#    + the total of a value not named in the validation output"
#
# which tells the reader nothing and, with two or more of them, reads as if the
# same value appeared twice. The role a variable plays in its own formula IS
# evidence — an operand of a sum is a component, an operand of `empty()` is a
# required field — so that is what is said instead. Nothing here is invented:
# every phrase below is a statement about the parsed expression, not about the
# taxonomy or the filing.
# ─────────────────────────────────────────────────────────────────────────────

# Every phrase the role fallback can produce, so a fallback label can be told
# apart from a real business name later (the LLM must not be required to quote
# one, and a naming source must still be allowed to overwrite it).
_ROLE_PHRASES = (
    "Component amount", "Component value", "Reported total", "Reported value",
    "Required value", "Value checked by this rule",
)

_CURRENCY_UNITS = frozenset(_CURRENCY_SYMBOLS)


def _is_fallback_label(label: str) -> bool:
    text = (label or "").strip()
    if not text:
        return True
    if text.startswith(_UNNAMED_LABEL):
        return True
    return any(text.startswith(phrase) for phrase in _ROLE_PHRASES)


def _role_phrase(var, comparison, kind, by_var) -> str:
    """What this variable DOES in its rule, in two or three words."""
    if kind == formula_kind.MANDATORY:
        return "Required value"

    has_facts = bool(by_var.get(var))
    on_the_left = comparison is not None and var in (comparison.lhs_vars or [])

    if on_the_left:
        return "Reported total" if kind == formula_kind.AGGREGATE else "Reported value"

    if formula_kind.describes_a_calculation(kind):
        # A monetary operand of a calculation is an amount; a rate or a count
        # inside the same expression is not, and calling it one would be wrong.
        monetary = any((f.get("unit") or "").strip().upper() in _CURRENCY_UNITS
                       for f in by_var.get(var, []))
        return "Component amount" if monetary else "Component value"

    if has_facts:
        return "Reported value"
    return "Value checked by this rule"


def _context_member_hint(var, by_var, index) -> str:
    """A dimensional qualifier taken from the fact's own context id, resolved
    through the taxonomy — 'asof_20260630_InfrastructureSectorMember' ->
    'Infrastructure Sector'.

    Only segments the TAXONOMY can name are used. Without an index this returns
    "", because CamelCase-splitting an unrecognised segment would dress up a
    guess as a name. The period segments are skipped: they are not what
    distinguishes one operand from another.
    """
    if index is None:
        return ""
    seen: list[str] = []
    for fact in by_var.get(var, []) or []:
        for token in (fact.get("context") or "").split("_"):
            token = token.strip()
            if not token or token.isdigit() or token.lower() in ("asof", "fromto"):
                continue
            try:
                label = _strip_role_suffix((index.concept_label(token) or "").strip())
            except Exception:                      # a broken index must not break the card
                label = ""
            if label and label not in seen:
                seen.append(label)
    return ", ".join(seen[:2])


def _apply_role_labels(labels, sources, comparison, by_var, index=None) -> None:
    """Give every still-unnamed variable a role phrase, numbered when several
    share one, in the order the formula references them.

    Numbering matters: two operands labelled identically read as one value
    counted twice, and it is also what stops _disambiguate() from pinning a raw
    context segment onto them.
    """
    kind = formula_kind.classify(comparison)
    # With no parsed expression there is no formula order to follow, so the
    # variables are taken in the order the error file listed them. They still
    # get a role — "a value this rule checks" is true of every one of them.
    ordered = comparison.variables() if comparison is not None else list(by_var)
    targets = [v for v in ordered if _is_fallback_label(labels.get(v, ""))]
    if not targets:
        return

    phrases = {var: _role_phrase(var, comparison, kind, by_var) for var in targets}
    counts: dict[str, int] = {}
    for phrase in phrases.values():
        counts[phrase] = counts.get(phrase, 0) + 1

    used: dict[str, int] = {}
    for var in targets:
        phrase = phrases[var]
        if counts[phrase] > 1:
            used[phrase] = used.get(phrase, 0) + 1
            phrase = f"{phrase} {used[phrase]}"
        hint = _context_member_hint(var, by_var, index)
        if hint and hint.lower() not in phrase.lower():
            phrase = f"{phrase} ({hint})"
        labels[var] = phrase
        sources[var] = "role"


_ARITHMETIC_SPLIT_CHARS = "+*/×÷"


def _split_top_level(text: str) -> list[str]:
    """Split on arithmetic operators that are not inside brackets.

    Depth is clamped at zero because these messages are routinely unbalanced
    ('([A (x + y) of March) + (B)]'), and a negative depth would make every
    later operator look nested and split nothing.
    """
    parts: list[str] = []
    current: list[str] = []
    depth = 0
    for ch in text or "":
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth = max(0, depth - 1)
        if depth == 0 and ch in _ARITHMETIC_SPLIT_CHARS:
            parts.append("".join(current))
            current = []
            continue
        current.append(ch)
    parts.append("".join(current))
    return [p for p in (p.strip() for p in parts) if p]


def _tidy_operand(text: str) -> str:
    """Trim quotes and the unmatched brackets left behind by splitting through
    a message whose own bracketing is unbalanced."""
    candidate = (text or "").strip().strip("\"'`“” \t")
    for _ in range(8):
        before = candidate
        if candidate.count("(") > candidate.count(")") and candidate.startswith("("):
            candidate = candidate[1:].strip()
        if candidate.count(")") > candidate.count("(") and candidate.endswith(")"):
            candidate = candidate[:-1].strip()
        if candidate.count("[") > candidate.count("]") and candidate.startswith("["):
            candidate = candidate[1:].strip()
        if candidate.count("]") > candidate.count("[") and candidate.endswith("]"):
            candidate = candidate[:-1].strip()
        candidate = candidate.strip("\"'`“” \t")
        if candidate == before:
            break
    return candidate.strip(" -–—:")


def _operand_names_from_message(message: str, expected: int) -> list[str]:
    """The right-hand operand names a formula-shaped validator message states,
    in the order they appear, or [] when they cannot be recovered confidently.

    Returns [] unless exactly *expected* usable names come out — an off-by-one
    would silently attach the wrong business name to a figure, which is worse
    than leaving it unnamed.
    """
    import re as _re
    text = message_cleaner.normalise_message(message)
    if not text or expected <= 0:
        return []

    # The statement's own '=' separates the reported figure from the expression
    # that produces it; only the right side names the operands.
    head, sep, tail = text.partition("=")
    body = tail if sep and tail.strip() else text

    chunks = _flatten_operands(body)
    names: list[str] = []
    for chunk in chunks:
        cleaned = _tidy_operand(chunk)
        if not cleaned:
            continue
        # Bare scale factors ('100', '10000') are part of the arithmetic, not
        # operands anyone reported.
        if not _re.search(r"[A-Za-z]", cleaned):
            continue
        names.append(cleaned)

    if len(names) != expected:
        return []
    if not all(message_cleaner.looks_like_label(n) for n in names):
        return []
    return names


def _strip_enclosing_bracket(text: str) -> str:
    """The inside of a chunk that is wholly wrapped in one bracket pair, or "".

    Bracket TYPES are deliberately not matched against each other: these
    messages mix them freely and unbalanced ('([A) + (B)]'), so pairing by type
    would refuse to open the very groups that need opening. Depth alone is
    enough to tell "this whole chunk is one group" from "this chunk contains
    several".
    """
    candidate = (text or "").strip()
    if len(candidate) < 3 or candidate[0] not in "([{":
        return ""
    depth = 0
    for i, ch in enumerate(candidate):
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
            if depth == 0:
                # Closed before the end -> the chunk is a group followed by
                # more text, not one enclosing group.
                return candidate[1:i].strip() if i == len(candidate) - 1 else ""
    # Never closed (the messages are routinely unbalanced): still one group.
    return candidate[1:].strip()


def _flatten_operands(text: str, depth: int = 0) -> list[str]:
    """Operand chunks of *text*, descending through bracket groups that hold
    more than one operand."""
    if depth > 6:
        return [text]
    out: list[str] = []
    for part in _split_top_level(text):
        inner = _tidy_operand(part)
        sub = _split_top_level(inner)
        if len(sub) > 1:
            for piece in sub:
                out.extend(_flatten_operands(piece, depth + 1))
            continue
        # A single chunk that is one big bracket group ('([A) + (B)]') hides its
        # operators one level down; open it and try again.
        unwrapped = _tidy_operand(_strip_enclosing_bracket(inner))
        if unwrapped and unwrapped != inner and len(_split_top_level(unwrapped)) > 1:
            out.extend(_flatten_operands(unwrapped, depth + 1))
            continue
        out.append(inner or part)
    return out


def _name_unlabelled_variables(labels, sources, comparison, by_var, message) -> None:
    """Fill in variables the cascade left unnamed, from the validator message.

    Two cases, both gated on an exact count match:

      * variables with NO row in the error table (mandatory-field rules, whose
        message enumerates the fields);
      * variables on a non-additive right-hand side (ratio / percentage /
        weighted average), whose operands the message states in formula order.

    A variable that already resolved keeps its label; nothing here overwrites a
    taxonomy- or backtracking-derived name.
    """
    if comparison is None or not message:
        return

    def named(var: str) -> bool:
        """A role phrase counts as UNNAMED here: a real business name from the
        message must still be able to replace it."""
        return not _is_fallback_label(labels.get(var, ""))

    all_vars = comparison.variables()

    # ── mandatory-style: nothing in the table at all ────────────────────────
    unrowed = [v for v in all_vars if not by_var.get(v) and not named(v)]
    if unrowed:
        fields = _enumerated_message_fields(message)
        if len(fields) == len(unrowed):
            for var, name in zip(unrowed, fields):
                labels[var] = name
                sources[var] = "message_fields"

    # ── non-additive right-hand side ────────────────────────────────────────
    rhs_vars = comparison.rhs_vars
    if not rhs_vars or all(named(v) for v in rhs_vars):
        return
    names = _operand_names_from_message(message, len(rhs_vars))
    if not names:
        return
    for var, name in zip(rhs_vars, names):
        if not named(var):
            labels[var] = name
            sources[var] = "message_operands"


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
    by_var: dict[str, list[dict]], index=None, protect: set[str] | None = None,
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
    unresolved: list[str] = []
    for var in [v for v in by_var if v in colliding] + sorted(colliding - set(by_var)):
        qualifier = qualifiers.get(var) or _backtracking_qualifier(by_var.get(var))
        if qualifier:
            labels[var] = f"{labels[var]} — {qualifier}"
            sources[var] = f"{sources.get(var, '')}+context"
        else:
            unresolved.append(var)

    # Nothing in the evidence separates these. Numbering them is not a claim
    # about what they are — it is the minimum needed to stop five identical
    # labels reading as one value counted five times, which is exactly how the
    # weighted-average rule came out ("Amount outstanding × Weighted average
    # rate + Amount outstanding × Weighted average rate"). Positions follow the
    # order the error file listed the facts, so they are stable across runs.
    still_colliding: dict[str, int] = {}
    for var in unresolved:
        still_colliding[labels[var]] = still_colliding.get(labels[var], 0) + 1
    used: dict[str, int] = {}
    for var in unresolved:
        if var in (protect or ()):
            # The figure the rule constrains is already distinguished by its
            # role — it is the subject of every sentence on the card — and
            # "Weighted average interest rate 1 is 0.0001 higher than …" reads
            # as though it were one of the components.
            continue
        label = labels[var]
        if still_colliding.get(label, 0) < 2:
            continue
        used[label] = used.get(label, 0) + 1
        labels[var] = f"{label} {used[label]}"
        sources[var] = f"{sources.get(var, '')}+position"


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


# ═════════════════════════════════════════════════════════════════════════════
# The Rule sentence, in business words rather than AST syntax.
#
# WHY THIS EXISTS
# ---------------
# _rule_sentence() above renders the parsed tree through
# formula_expression.describe(), which is a faithful AST printer. Faithful is
# the problem:
#
#   * core() peels round/floor/ceiling/number and constant scaling, but NOT
#     abs() and NOT if — so `round(($V2 div $V3)*10000) div 10000` inside a
#     conditional reaches the reader complete with "× 10,000 ÷ 10,000";
#   * it prints operators as symbols (×, ÷, +);
#   * count() prints as "the number of reported values for X", which describes
#     the function rather than the requirement;
#   * it repeats whatever label each variable carries, so a weighted average
#     whose five variables resolve to two labels names those two four times.
#
# Everything below composes a sentence from the resolved labels instead, one
# shape at a time, and returns "" the moment it is not certain — the caller
# then keeps _readable_rule_sentence() exactly as it is today.
#
# DELIBERATELY NOT HANDLED: aggregate and equality. Their existing sentences
# ("… must be equal to the total of A + the total of B") name every component
# correctly and leak no implementation syntax, and the aggregate case is a
# verified-good output that must not move.
# ═════════════════════════════════════════════════════════════════════════════

_WORD_OPERATORS = {
    "+": "plus", "-": "minus", "*": "multiplied by",
    "div": "divided by", "idiv": "divided by",
}

# Wrappers that carry no business meaning of their own once the rule is stated
# in words: the rounding is reported separately and abs() is a comparison
# detail, not part of what the figure IS.
_TRANSPARENT_FUNCS = frozenset({"round", "floor", "ceiling", "number", "abs", "sum"})

_MAX_WORD_DEPTH = 4


def _is_additive(node) -> bool:
    return node is not None and node.kind == "binop" and node.op in ("+", "-")


def _words(node, labels: dict[str, str], depth: int = 0) -> str | None:
    """One subtree in business words, or None when it cannot be said safely.

    None is returned for any shape this renderer does not model — a nested
    conditional, an unknown function, a variable with no label. The caller
    treats None as "keep the existing sentence", so an unmodelled expression is
    never half-translated.
    """
    if node is None or depth > _MAX_WORD_DEPTH:
        return None

    if node.kind == "num":
        return _format_amount(node.value, "")
    if node.kind == "str":
        return f"“{node.name}”"
    if node.kind == "var":
        # Never a raw variable id: an unnamed operand means the sentence cannot
        # be built, not that 'V4' should be printed.
        return labels.get(node.name) or None
    if node.kind == "func":
        if node.name in _TRANSPARENT_FUNCS and len(node.args) == 1:
            return _words(node.args[0], labels, depth)
        return None
    if node.kind == "unary":
        inner = _words(node.args[0], labels, depth + 1) if node.args else None
        return f"minus {inner}" if inner else None
    if node.kind == "binop" and node.op in _WORD_OPERATORS:
        left, right = node.args
        left_text = _grouped_words(left, labels, depth + 1, node.op)
        right_text = _grouped_words(right, labels, depth + 1, node.op)
        if not left_text or not right_text:
            return None
        return f"{left_text} {_WORD_OPERATORS[node.op]} {right_text}"
    return None


def _grouped_words(node, labels, depth: int, parent_op: str) -> str | None:
    """An operand of *parent_op*, phrased so the grouping is unambiguous.

    An additive group under a division reads as a total — "divided by the total
    of A and B" — which says what brackets would say without stacking a second
    set of parentheses inside labels that already contain their own.
    """
    if parent_op in ("div", "idiv", "*") and _is_additive(node):
        parts = _additive_word_terms(node, labels, depth)
        if parts is None:
            return None
        return f"the total of {_join(parts)}"
    return _words(node, labels, depth)


def _additive_word_terms(node, labels, depth: int) -> list[str] | None:
    """The terms of a '+' chain as separate phrases, or None. Any subtraction
    makes a plain list wrong, so those fall back to the general renderer."""
    if node is None or depth > _MAX_WORD_DEPTH:
        return None
    if node.kind == "binop" and node.op == "+":
        left = _additive_word_terms(node.args[0], labels, depth + 1)
        right = _additive_word_terms(node.args[1], labels, depth + 1)
        if left is None or right is None:
            return None
        return left + right
    if node.kind == "binop" and node.op == "-":
        return None
    single = _words(node, labels, depth)
    return [single] if single else None


# ── conditional branch resolution ────────────────────────────────────────────

def _condition_holds(node, by_var: dict) -> bool | None:
    """Whether one condition is true on the reported facts, or None.

    Evaluated by the SAME public evaluator the verdict came from, as a
    boolean-only comparison. Nothing about the rule's own verdict, values or
    difference is taken from here — this only decides which branch of an
    if/then/else the explanation should describe.
    """
    if node is None:
        return None
    try:
        probe = formula_expression.Comparison(
            operator="", lhs=node, rhs=None, source="", boolean_only=True)
        evaluated = formula_expression.evaluate(probe, _raw_values_by_var(by_var))
    except Exception as exc:                       # a display aid must not raise
        logger.debug("[formula_error] condition not resolvable: %s", exc)
        return None
    if not evaluated:
        return None
    passes = evaluated.get("passes")
    return bool(passes) if isinstance(passes, bool) else None


def _if_node(rhs):
    """The if/then/else at the top of *rhs* once wrappers are peeled, or None."""
    node = formula_kind.business_node(rhs)
    if node is not None and node.kind == "if" and len(node.args) == 3:
        return node
    return None


def _applied_branch(rhs, by_var: dict):
    """(branch, reasons) — the branch the reported facts select, and the parts
    of the condition that made it so. (None, []) when it cannot be resolved."""
    node = _if_node(rhs)
    if node is None:
        return None, []
    holds = _condition_holds(node.args[0], by_var)
    if holds is None:
        return None, []
    reasons = _true_conditions(node.args[0], by_var) if holds else []
    return (node.args[1] if holds else node.args[2]), reasons


def _true_conditions(condition, by_var: dict) -> list:
    """The individual disjuncts of an `or` condition that actually hold.

    A rule guarded by "if A = 0 or B = 0" fails for a specific reason, and
    naming the one that applies is the difference between explaining the outcome
    and reciting the condition.
    """
    if condition is None:
        return []
    if condition.kind == "binop" and condition.op == "or":
        out = []
        for side in condition.args:
            out.extend(_true_conditions(side, by_var))
        return out
    return [condition] if _condition_holds(condition, by_var) else []


def _substantive_branch(node):
    """The branch that carries the rule's actual calculation — the one that is
    not a bare constant. None when both or neither are."""
    then_branch, else_branch = node.args[1], node.args[2]
    then_const = not then_branch.variables()
    else_const = not else_branch.variables()
    if then_const and not else_const:
        return else_branch
    if else_const and not then_const:
        return then_branch
    return None


# ── the sentence ─────────────────────────────────────────────────────────────

def _business_rule_sentence(comparison, labels: dict[str, str], kind: str,
                            by_var: dict) -> str:
    """The rule in business words for the shapes we classify confidently, or ""
    to keep the existing AST restatement."""
    if comparison is None:
        return ""
    if comparison.boolean_only and kind == formula_kind.CONDITIONAL:
        return _boolean_conditional_sentence(comparison, labels, by_var)
    if comparison.rhs is None or not comparison.operator:
        return ""
    lhs_vars = comparison.lhs_vars
    if len(lhs_vars) != 1:
        return ""
    subject = labels.get(lhs_vars[0])
    if not subject:
        return ""

    if kind == formula_kind.COUNT:
        sentence = _count_rule_sentence(comparison, labels)
    elif kind == formula_kind.WEIGHTED_AVERAGE:
        sentence = _weighted_average_rule_sentence(comparison, labels, subject)
    elif kind in (formula_kind.RATIO, formula_kind.PERCENTAGE):
        body = _words(formula_kind.business_node(comparison.rhs), labels)
        sentence = f"{subject} must equal {body}." if body else ""
    elif kind == formula_kind.CONDITIONAL:
        sentence = _conditional_rule_sentence(comparison, labels, subject)
    else:
        return ""

    if not sentence or len(sentence) > _MAX_RULE_SENTENCE_CHARS:
        return ""
    return sentence


def _count_rule_sentence(comparison, labels) -> str:
    """'At least 50 Sector Code records must be reported.'

    Only for a literal limit — a count compared against another reported figure
    is a different statement and is left to the existing sentence.
    """
    rhs = comparison.rhs
    if rhs is None or rhs.kind != "num" or rhs.value is None:
        return ""
    phrase, verb = _count_requirement(comparison.operator, rhs.value)
    subject = _count_subject(comparison, labels)
    if not subject or subject == "records":
        return ""
    modal = "must be reported" if verb == "required" else "may be reported"
    return f"{phrase[:1].upper()}{phrase[1:]} {subject} {modal}."


def _base_label(label: str | None) -> str:
    """A label without the positional suffix _disambiguate() may have added.

    'Amount outstanding term deposit 2' -> 'Amount outstanding term deposit'.
    The suffix exists to tell two identically-named facts apart in a table; it
    is not part of the concept, and a sentence about what they all ARE should
    not be defeated by it.
    """
    import re as _re
    return _re.sub(r"\s+\d+$", "", (label or "").strip()).strip()


def _weighted_average_rule_sentence(comparison, labels, subject: str) -> str:
    """'X must equal the weighted average of the component rates, using each
    Amount outstanding as its weight.'

    The weights are the variables the denominator adds up; the rates are the
    other factor in each numerator product. Naming the operands individually is
    what produced "Amount outstanding × Weighted average rate + Amount
    outstanding × Weighted average rate" — the same two labels four times.
    """
    node = formula_kind.business_node(comparison.rhs)
    if node is None or node.kind != "binop" or node.op not in ("div", "idiv"):
        return ""
    numerator, denominator = node.args
    weight_vars = denominator.variables()
    if len(weight_vars) < 2:
        return ""
    weight_labels = {_base_label(labels.get(v)) for v in weight_vars}
    if None in weight_labels or "" in weight_labels or not weight_labels:
        return ""
    weight = (weight_labels.pop() if len(weight_labels) == 1
              else "component amount")
    return (f"{subject} must equal the weighted average of the component rates, "
            f"using each {weight} as its weight.")


# A condition that did NOT hold is far clearer stated as its own negation
# ("is greater than or equal to 0") than as a denial of the original
# ("is less than 0 does not hold here").
_NEGATED_OPERATOR = {"<": ">=", "<=": ">", ">": "<=", ">=": "<",
                     "=": "!=", "!=": "=", "<>": "="}


def _describe_requirement(node, labels) -> str:
    """One branch of a conditional in business language.

    A branch is often itself a comparison whose sides carry the rule's own
    ÷1,000 ×1,000 scaling. business_node() peels a bare expression but not a
    comparison, so each side is peeled separately here — otherwise the scaling
    reappears in the very sentence written to remove it.
    """
    node = formula_kind.business_node(node)
    if node is None:
        return ""
    if node.kind == "binop" and node.op in formula_expression.COMPARISON_OPERATORS:
        left = formula_expression.describe(formula_kind.business_node(node.args[0]), labels)
        right = formula_expression.describe(formula_kind.business_node(node.args[1]), labels)
        meaning = formula_expression.OPERATOR_MEANING.get(node.op, node.op)
        return f"{left} is {meaning} {right}" if left and right else ""
    return formula_expression.describe(node, labels)


def _negated_condition_text(condition, labels) -> str:
    """The condition restated as its own opposite, or "" when it cannot be
    negated exactly (an `or` chain has no single negation to state)."""
    if condition is None or condition.kind != "binop":
        return ""
    flipped = _NEGATED_OPERATOR.get(condition.op)
    if not flipped:
        return ""
    left = formula_expression.describe(formula_kind.business_node(condition.args[0]), labels)
    right = formula_expression.describe(formula_kind.business_node(condition.args[1]), labels)
    meaning = formula_expression.OPERATOR_MEANING.get(flipped, flipped)
    return f"{left} is {meaning} {right}" if left and right else ""


def _boolean_conditional_sentence(comparison, labels, by_var: dict) -> str:
    """A conditional rule that yields a verdict rather than two comparable
    figures — 'if A is less than 0 then X = 0, otherwise X = Y'.

    Only the branch the reported facts actually select is stated, so the reader
    is told what this rule required of THEIR data instead of being handed the
    rule's whole decision tree.
    """
    node = _if_node(comparison.lhs)
    if node is None:
        return ""
    holds = _condition_holds(node.args[0], by_var)
    if holds is None:
        return ""
    requirement = _describe_requirement(node.args[1] if holds else node.args[2], labels)
    if not requirement:
        return ""

    if holds:
        reasons = [t for t in (_describe_requirement(r, labels)
                               for r in _true_conditions(node.args[0], by_var)) if t]
        if not reasons:
            return ""
        return f"Because {' and '.join(reasons)}, this rule requires that {requirement}."

    negated = _negated_condition_text(node.args[0], labels)
    if not negated:
        return ""
    return f"Because {negated}, this rule requires that {requirement}."


def _conditional_rule_sentence(comparison, labels, subject: str) -> str:
    """The relationship the rule enforces, taken from the branch that actually
    calculates something — not the if/then/else scaffolding around it."""
    node = _if_node(comparison.rhs)
    if node is None:
        return ""
    branch = _substantive_branch(node)
    if branch is None:
        return ""
    body = _words(formula_kind.business_node(branch), labels)
    return f"{subject} must equal {body}." if body else ""


def _how_to_fix(comparison, result: dict, labels: dict[str, str], kind: str = "") -> str:
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
    if kind == formula_kind.COUNT:
        return (f"Check how many {_count_subject(comparison, labels)} are present in the "
                f"source data, then regenerate and revalidate the return.")
    lhs_label = labels.get(comparison.lhs_vars[0], "the total") if comparison.lhs_vars else "the total"
    rhs_labels = [_label_of(labels, v) for v in comparison.rhs_vars]

    if kind == formula_kind.WEIGHTED_AVERAGE and rhs_labels:
        return (f"Check the amounts and the rates used to calculate {lhs_label} in the "
                f"source data, correct whichever is wrong, then regenerate and "
                f"revalidate the return.")
    if kind in (formula_kind.RATIO, formula_kind.PERCENTAGE) and rhs_labels:
        noun = "percentage" if kind == formula_kind.PERCENTAGE else "value"
        return (f"Check {lhs_label} and the values it is calculated from "
                f"({_join(rhs_labels)}) in the source data — the reported {noun} does "
                f"not match the one calculated from them. Then regenerate and "
                f"revalidate the return.")
    if kind == formula_kind.CONDITIONAL and rhs_labels:
        return (f"Check {lhs_label} and the values this rule's condition depends on "
                f"({_join(rhs_labels)}) in the source data, correct whichever is wrong, "
                f"then regenerate and revalidate the return.")

    if len(rhs_labels) > 1:
        # "components" is only true of an addition. A ratio's operands are not
        # components of it, and calling them that misdescribes the rule.
        basis = ("its components"
                 if kind in ("", formula_kind.UNKNOWN, formula_kind.AGGREGATE)
                 else "the values it is calculated from")
        return (f"Check {lhs_label} against {basis} ({_join(rhs_labels)}) in the source "
                f"data, correct whichever is wrong, then regenerate and revalidate the return.")
    other = rhs_labels[0] if rhs_labels else "the compared value"
    return (f"Review {lhs_label} and {other} in the source data to determine which needs "
            f"correcting, then regenerate and revalidate the return.")


# ─────────────────────────────────────────────────────────────────────────────
# Record-count rules.
#
# `count($V1) >= 50` constrains HOW MANY $V1 rows exist, not the value of any of
# them. Describing it with the ordinary comparison wording produced
#
#   "Sector code is 40 lower than the required number of values."
#
# which reads as a statement about the sector code itself — a field that has no
# numeric magnitude at all. Everything below only rewords the same three figures
# the engine already produced (the count, the limit, the gap).
#
# Nothing here claims the rule checks UNIQUENESS: fn:count counts rows, and no
# wording in this module says otherwise unless the expression itself says so.
# ─────────────────────────────────────────────────────────────────────────────

_COUNT_REQUIREMENT = {
    ">=": ("at least {n}", "required"),
    ">":  ("more than {n}", "required"),
    "<=": ("at most {n}", "allowed"),
    "<":  ("fewer than {n}", "allowed"),
    "=":  ("exactly {n}", "required"),
    "!=": ("a number other than {n}", "required"),
    "<>": ("a number other than {n}", "required"),
}


def _count_requirement(operator: str, limit) -> tuple[str, str]:
    """('at least 50', 'required') for the rule's own operator and limit."""
    template, verb = _COUNT_REQUIREMENT.get(operator or "=", ("{n}", "required"))
    return template.format(n=_format_amount(limit, "")), verb


def _record_noun(count) -> str:
    try:
        return "record" if Decimal(str(count)) == 1 else "records"
    except (InvalidOperation, TypeError, ValueError):
        return "records"


def _count_subject(comparison, labels) -> str:
    """'Sector code records' — what is being counted, in the plural."""
    counted = comparison.lhs_vars[0] if comparison and comparison.lhs_vars else ""
    label = _label_of(labels, counted) if counted else ""
    return f"{label} records" if label else "records"


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

    business_labels = [_label_of(labels, v) for v in comparison.variables()]
    labels_are_ambiguous = len(set(business_labels)) < len(business_labels)

    def emit(var: str, sign: int = 1) -> None:
        facts = by_var.get(var, [])
        prefix = "" if sign > 0 else "less "
        label = f"{prefix}{_label_of(labels, var)}"
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
    business_labels = [_label_of(labels, v) for v in comparison.variables()]
    ambiguous = len(set(business_labels)) < len(business_labels)
    for var in comparison.variables():
        for fact in by_var.get(var, []):
            entry = {
                "label": _label_of(labels, var),
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


def _comparison_items(comparison, result: dict, labels: dict[str, str], unit: str,
                      kind: str = "", raw_pair: tuple | None = None) -> list[dict]:
    """The two compared sides plus the difference, with raw and rounded kept
    apart so a rounded figure is never presented as the reported one.

    *kind* names the row after what the rule actually computes ("Calculated
    ratio", "Calculated total"). It defaults to "" — the v1 sections pass
    nothing and keep the original "Calculated/Combined" wording exactly.
    """
    rounded = bool(result.get("rounding_changed_a_value"))
    is_combination = (
        len(comparison.rhs_vars) > 1
        or (comparison.rhs is not None and comparison.rhs.uses_aggregation())
    )
    right_label = (formula_kind.expected_column(kind)
                   or ("Calculated/Combined" if is_combination else "Compared with"))

    def side(raw, compared) -> str:
        if raw is not None and compared is not None and (raw < 0) != (compared < 0):
            # The rule compares absolute values; pairing '-0.0279' with '0.0279'
            # as if one rounded to the other states a falsehood about the sign.
            return _format_amount(compared, unit)
        if rounded and raw is not None and raw != compared:
            raw_text = _format_precise(raw, unit)
            compared_text = _format_amount(compared, unit)
            # The two can differ in the 12th decimal and still format
            # identically; "0.0599 → rounds to 0.0599" says nothing.
            if raw_text != compared_text:
                return f"{raw_text} → rounds to {compared_text}"
        return _format_amount(compared, unit)

    # *raw_pair* carries the de-scaled (business-level) operand values for a
    # rule whose expression multiplies by 10,000 internally. Without it this
    # block reported "Reported: 300 → rounds to 0.03" — 300 being the scaled
    # intermediate, not anything the filer entered.
    lhs_raw, rhs_raw = raw_pair if raw_pair is not None else (
        result.get("lhs_raw"), result.get("rhs_raw"))

    items = [
        {"label": "Reported", "value": side(lhs_raw, result["lhs_value"])},
        {"label": right_label, "value": side(rhs_raw, result["rhs_value"])},
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


def _why_failed_points(comparison, result, labels, unit, llm_text,
                       kind: str = "", concise: bool = False,
                       omit_requirement: bool = False,
                       rule_sentence: str = "") -> list[str]:
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
        return _boolean_points(comparison, result, labels, kind, rule_sentence)

    points: list[str] = []
    lhs_var = comparison.lhs_vars[0] if comparison.lhs_vars else ""
    lhs_label = labels.get(lhs_var) or "The reported value"
    rhs_labels = [_label_of(labels, v) for v in comparison.rhs_vars]

    # How the right-hand side should be NAMED in prose. Formula-type-aware:
    # "the sum of the component values" is only true of an addition, and saying
    # it of a ratio or a weighted average misdescribes the rule. "" from
    # formula_kind means "nothing better to offer" and keeps the v1 wording.
    subject_phrase = formula_kind.result_subject(kind) or (
        "the combined value" if len(rhs_labels) > 1
        else (rhs_labels[0] if rhs_labels else "the compared value")
    )

    if kind == formula_kind.COUNT:
        return _count_points(comparison, result, labels, concise)

    lhs_raw = result.get("lhs_raw")
    rhs_raw = result.get("rhs_raw")

    # *concise* is set only by the v2 card, whose matrix already prints every
    # one of these figures immediately above this block. Repeating them there
    # made the reader check the same two numbers three times (matrix,
    # Comparison, Why It Failed). v1 keeps the full sequence.
    if not concise:
        points.append(f"{lhs_label} is reported as "
                      f"{_format_amount(lhs_raw if lhs_raw is not None else result['lhs_value'], unit)}.")

        if len(rhs_labels) > 1:
            combined = _format_amount(rhs_raw if rhs_raw is not None else result['rhs_value'], unit)
            if formula_kind.describes_a_calculation(kind) and kind != formula_kind.AGGREGATE:
                points.append(f"{_join(rhs_labels)} give {subject_phrase} of {combined}.")
            else:
                points.append(f"{_join(rhs_labels)} together come to {combined}.")
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

    if not omit_requirement:
        # Suppressed when the card's Rule line already states the requirement in
        # business words — saying it twice, once in each vocabulary, is the
        # repetition this section is meant to avoid.
        meaning = formula_expression.OPERATOR_MEANING.get(result["operator"], result["operator"])
        points.append(f"The rule requires {lhs_label} to be {meaning} {subject_phrase}.")

    if result.get("passes"):
        points.append("Re-checking the reported values satisfies that condition, so the "
                      "reason this check failed is not visible in the values shown.")
    elif result.get("values_equal"):
        points.append("The two values are exactly equal, which does not satisfy the "
                      "condition this rule requires.")
    else:
        direction = "higher" if result["relationship"] == "lhs_greater" else "lower"
        points.append(f"They differ by {_format_amount(abs(result['difference']), unit)} "
                      f"({lhs_label} is {direction}), so the check fails.")
    return points


def _count_points(comparison, result, labels, concise: bool = False) -> list[str]:
    """Points for a record-count rule.

    Stated as a count throughout: the field being counted has no numeric
    magnitude, so "Sector code is 40 lower" is not a fact about anything.
    """
    points: list[str] = []
    subject = _count_subject(comparison, labels)
    phrase, verb = _count_requirement(result.get("operator", ""), result["rhs_value"])

    if not concise:
        points.append(f"{_format_amount(result['lhs_value'], '')} {subject} "
                      f"are reported.")
    points.append(f"The rule requires {phrase}.")

    if result.get("passes"):
        points.append("Re-checking the reported values satisfies that condition, so the "
                      "reason this check failed is not visible in the values shown.")
    elif result.get("values_equal"):
        points.append(f"The number reported is exactly {phrase.split(' ')[-1]}, which "
                      f"does not satisfy the condition this rule requires.")
    else:
        short = result.get("relationship") == "lhs_less"
        direction = "fewer" if short else "more"
        points.append(f"That is {_format_amount(abs(result['difference']), '')} "
                      f"{direction} than {verb}, so the check fails.")
    return points


def _boolean_points(comparison, result, labels, kind: str = "",
                    rule_sentence: str = "") -> list[str]:
    """Points for a rule that yields a verdict rather than two comparable
    numbers — a presence check, a conditional, or a boolean combination.

    The condition is described from the AST, so the wording follows whatever
    the rule actually says instead of assuming it is a presence check (the
    corpus contains 'not(empty($V))', 'if (X = 0) then (Y = 0) else …' and
    'A or B' forms, and they mean different things).
    """
    points: list[str] = []
    # The card supplies its own business-worded sentence when it has one, so
    # the drawer does not re-print the raw if/then/otherwise beneath it.
    condition = rule_sentence or _readable_rule_sentence(comparison, labels)
    if rule_sentence:
        points.append(rule_sentence)
        condition = ""
    if kind == formula_kind.MANDATORY:
        # "it is not the case that X is not reported" is a literal reading of
        # empty() that helps nobody. Same plain sentence the Rule section uses.
        condition = "every value this rule checks is reported"

    if condition:
        points.append(f"This rule requires that {condition}.")
    if result.get("passes"):
        points.append("Re-checking the reported values satisfies that condition, so the "
                      "reason this check failed is not visible in the values shown.")
    else:
        missing = result.get("missing_vars") or []
        named = [labels.get(v) for v in missing if labels.get(v)]
        if named:
            points.append(f"No value was reported for {_join(named)}.")
        points.append("The reported data does not satisfy the condition this rule checks, "
                      "so the check fails.")
    return points or ["The reported data does not satisfy the condition this rule checks."]


def _how_to_fix_points(comparison, result, labels, llm_text, kind: str = "") -> list[str]:
    llm_points = _llm_points((llm_text or {}).get("how_to_fix"))
    if llm_points:
        return llm_points
    return [_how_to_fix(comparison, result, labels, kind)]


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


def _fact_display(fact: dict, unit: str) -> str:
    """One fact's value as the card should show it.

    A reported value that is not a number is still a REPORTED value: the corpus
    carries dates, codes and category names, and _format_amount() renders every
    one of them as "not reported" because _decimal_or_none() returns None. That
    tells the reader their filing is missing something it actually contains.
    """
    number = _decimal_or_none(fact.get("value"))
    if number is not None:
        return _format_amount(number, fact.get("unit") or unit)
    raw = str(fact.get("value") or "").strip()
    return raw or "not reported"


def _unit_of(by_var, var, default) -> str:
    for fact in by_var.get(var, []):
        if fact.get("unit"):
            return fact["unit"]
    return default


def _label_of(labels: dict[str, str], var: str) -> str:
    """A variable's business label, never its raw id.

    `labels.get(var, var)` returned 'V1' for any variable the cascade could not
    name — which is exactly the internal handle resolve_labels exists to keep
    out of the user's sight. It surfaced on mandatory-field rules, whose
    variables have no rows and so never entered the label map at all.
    """
    return labels.get(var) or _UNNAMED_LABEL


def _card_unit(facts: list[dict], kind: str) -> str:
    """Fallback unit for facts that carry none of their own.

    For a ratio, a percentage or a weighted average there is NO such fallback:
    the result of dividing two rupee amounts is not rupees. Inheriting a
    monetary unit from whichever fact in the table happened to declare one
    first is what printed a percentage as '₹0.03' and a rounding step as
    'nearest ₹0.0001'. Each fact still shows its own declared unit, so nothing
    that was correctly labelled loses its symbol.
    """
    if formula_kind.is_unitless(kind):
        return ""
    units = {(f.get("unit") or "").strip() for f in facts}
    if len(units) == 1:
        # Homogeneous table — every fact already agrees, so the shared unit is
        # a safe default and behaviour is unchanged for the monetary rules that
        # make up most of the corpus.
        return units.pop()
    # Mixed table: some facts declare a unit and some do not. Lending one
    # fact's unit to another is precisely how '$1.9969' was printed for a
    # ratio sitting beside a dollar amount.
    return ""


def _result_unit(comparison, by_var: dict, default: str, kind: str) -> str:
    """Unit for the compared / expected / difference figures.

    Taken from the LEFT-hand variable's own facts — that variable is the figure
    the rule constrains, and on a ratio rule its unit differs from the monetary
    components it is derived from.
    """
    if formula_kind.is_unitless(kind) or kind == formula_kind.COUNT:
        # A count of rows has no unit, whatever the counted facts are measured
        # in — "₹10 records" would be nonsense.
        return ""
    if comparison is not None and comparison.lhs_vars:
        own = _unit_of(by_var, comparison.lhs_vars[0], "")
        if own:
            return own
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
        items.append({"label": _label_of(labels, var), "value": location})
    return items


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 4b — the unified error card (v2)
#
# Same evaluation, re-tiered into the generic card shared with dimension
# errors:
#
#   headline  the size and direction of the gap, in words
#   locator   the rule, and the source table/cell to go and edit
#   rule      the AST restated in business language (unchanged from v1)
#   matrix    each component's reported value, then the result row carrying
#             expected vs. reported
#   fix       the action
#   details   the rounding/comparison breakdown, the v1 "Why It Failed" prose,
#             the validator message
#
# v1 split the numbers across "Reported Values" (what you gave) and
# "Comparison" (expected vs actual vs difference) — two halves of one table
# that the reader had to join mentally. The matrix joins them.
#
# Everything below is additive; build_sections() above is untouched and is
# still what runs when ERROR_CARD_V2=0.
# ═════════════════════════════════════════════════════════════════════════════


def _is_combination(comparison) -> bool:
    """Whether the right-hand side is built from several reported figures.

    Same test _comparison_items() uses. When true, the right side is a
    CALCULATED expectation and the left side is the figure that should have
    matched it — which is what lets the card put a real value in the Expected
    column. When false, both sides are just reported figures being compared.
    """
    if comparison is None:
        return False
    return (
        len(comparison.rhs_vars) > 1
        or (comparison.rhs is not None and comparison.rhs.uses_aggregation())
    )


def _expected_cell(comparison, result, unit: str, kind: str = "") -> str:
    """The Expected cell for the result row.

    For a non-equality operator the threshold alone would be ambiguous
    (is 100 a floor or a ceiling?), so the operator's meaning is carried with
    it — 'greater than or equal to ₹100'.
    """
    amount = _format_amount(result["rhs_value"], unit)
    operator = result.get("operator", "=")
    if kind == formula_kind.COUNT:
        # "at least 50" is what the rule says; "greater than or equal to 50" is
        # the same requirement restated in operator language.
        return _count_requirement(operator, result["rhs_value"])[0]
    if operator in ("=", "eq"):
        return amount
    meaning = formula_expression.OPERATOR_MEANING.get(operator, operator)
    return f"{meaning} {amount}"


def _fact_rows(var, by_var, labels, unit, rule, *, sign: int = 1,
               status: str = error_card.STATUS_NEUTRAL,
               aggregated=None, absent_mode: str = "required") -> list[dict]:
    """Matrix rows for ONE variable — the same fact/aggregate/multi-value
    handling _reported_value_items() applies, expressed as table rows.

    Components carry no Expected value of their own: the rule constrains the
    RESULT, not the inputs, and inventing an expectation for an input would be
    a claim the evidence does not support.
    """
    facts = by_var.get(var, [])
    prefix = "" if sign > 0 else "less "
    label = f"{prefix}{_label_of(labels, var)}"

    if not facts:
        # Two different situations that read identically as "not reported":
        #   required    — the rule exists to demand this value (a mandatory
        #                 field check), so its absence IS the error;
        #   unavailable — the rule needs the value to compute a result and the
        #                 validation output simply does not carry it. Calling
        #                 that "not reported" asserts something about the
        #                 filing that the evidence does not support.
        if absent_mode == "unavailable":
            return [error_card.row(label, "", "— not available in the validation output",
                                   error_card.STATUS_UNKNOWN)]
        return [error_card.row(label, "must be reported", "— not reported",
                               error_card.STATUS_BAD)]

    if len(facts) > 1 and aggregated and len(aggregated) == len(facts):
        return [
            error_card.row(
                f"{prefix}{name}", "", _fact_display(fact, unit), status,
            )
            for fact, name in zip(facts, aggregated)
        ]

    if len(facts) > 1:
        return [error_card.row(
            label, "",
            _format_amount(_var_total(by_var, var), _unit_of(by_var, var, unit)),
            status, note=f"total of {len(facts)} reported values",
        )]

    fact = facts[0]
    return [error_card.row(
        label, "", _fact_display(fact, unit),
        status, note=_entered_note(fact, rule),
    )]


def _fill_literal_expectation(rows, comparison, result, labels, unit) -> None:
    """Put the rule's own fixed limit in the Expected cell of the left-hand
    variable's row, when the rule compares against a constant.

    Only ever states what the expression literally says ("greater than or equal
    to 0.1"). No verdict is attached: the row keeps whatever status it had,
    because a value that could not be read as a number cannot be judged.
    """
    if comparison is None or comparison.rhs is None or not comparison.operator:
        return
    if comparison.rhs.variables():
        return                                  # not a fixed limit
    if result is not None and not result.get("boolean_only"):
        return                                  # the result row already says it
    meaning = formula_expression.OPERATOR_MEANING.get(
        comparison.operator, comparison.operator)
    try:
        limit = formula_expression.describe(comparison.rhs)
    except Exception:                           # pragma: no cover - safety net
        return
    if not limit:
        return
    lhs_var = comparison.lhs_vars[0] if comparison.lhs_vars else ""
    target = _label_of(labels, lhs_var) if lhs_var else ""
    for row in rows:
        if target and row.get("label") == target and not row.get("expected"):
            row["expected"] = f"{meaning} {limit}"
            return


def _uncomparable_threshold_note(comparison, result, by_var, labels) -> str:
    """The reported value exists but is not a plain number, so the rule could
    not be re-checked here. Says exactly that, and nothing about pass or fail.
    """
    if comparison is None or result is not None or not comparison.operator:
        return ""
    if comparison.rhs is None or comparison.rhs.variables():
        return ""
    lhs_var = comparison.lhs_vars[0] if comparison.lhs_vars else ""
    facts = by_var.get(lhs_var) or []
    if not facts:
        return ""
    raw = str(facts[0].get("value") or "").strip()
    if not raw or _decimal_or_none(raw) is not None:
        return ""
    label = _label_of(labels, lhs_var)
    return (f"{label} is reported as “{raw}”, which is not a plain number in the "
            f"validation output, so this check could not be re-calculated here. "
            f"The reported value and the rule's limit are shown above for comparison.")


def _card_matrix_rows_formula(comparison, result, by_var, labels, unit, rule,
                              kind: str = "") -> list[dict]:
    """Components first, then the result row that carries the verdict.

    Reading order is deliberately 'here are the parts -> here is the total that
    should have followed', which is the order the reader will have to work in
    to fix it.
    """
    if comparison is None:
        # The expression could not be parsed, so there is no expectation to
        # state — but the facts the error file reported are still evidence, and
        # showing them beats showing nothing. Every row is neutral: without the
        # rule there is no verdict to attach to any of them.
        rows: list[dict] = []
        for var, facts in by_var.items():
            for fact in facts:
                rows.append(error_card.row(
                    _label_of(labels, var), "", _fact_display(fact, unit),
                    error_card.STATUS_NEUTRAL,
                    note=_entered_note(fact, rule),
                ))
        return rows

    aggregated = labels.get("_aggregated_fact_labels")
    absent_mode = formula_kind.absent_operand_means(kind)

    # ── verdict-style rules (presence checks, conditionals, boolean combos) ──
    # There are no two comparable totals, so there is no result row; the table
    # degrades to "what this rule looks at, and what was reported for it".
    if result is None or result.get("boolean_only"):
        missing = set((result or {}).get("missing_vars") or [])
        rows: list[dict] = []
        for var in comparison.variables():
            status = error_card.STATUS_BAD if var in missing else error_card.STATUS_NEUTRAL
            rows += _fact_rows(var, by_var, labels, unit, rule,
                               status=status, aggregated=aggregated,
                               absent_mode=absent_mode)
        # A rule that compares against a fixed limit HAS a stateable
        # expectation even when the reported value could not be turned into a
        # number (the corpus reports '12.54%' with the sign attached, which
        # _to_decimal correctly refuses). Leaving the Expected column blank
        # then loses the one thing the rule does say.
        _fill_literal_expectation(rows, comparison, result, labels, unit)
        return rows

    rows = []

    # Right-hand components — the basis the expectation is computed from.
    signed = comparison.rhs.signed_variables() if comparison.rhs is not None else []
    for var, sign in (signed or [(v, 1) for v in comparison.rhs_vars]):
        rows += _fact_rows(var, by_var, labels, unit, rule, sign=sign,
                           aggregated=aggregated, absent_mode=absent_mode)

    # A left side built from several variables is shown term by term too;
    # otherwise the single left variable IS the result row below.
    if len(comparison.lhs_vars) > 1:
        for var in comparison.lhs_vars:
            rows += _fact_rows(var, by_var, labels, unit, rule, aggregated=aggregated,
                               absent_mode=absent_mode)

    # ── the result row ───────────────────────────────────────────────────────
    lhs_var = comparison.lhs_vars[0] if comparison.lhs_vars else ""
    result_label = (labels.get(lhs_var) if len(comparison.lhs_vars) == 1 else "") \
        or "Total of the above"
    if kind == formula_kind.COUNT:
        result_label = _count_subject(comparison, labels)

    # The compared figures carry the LEFT-hand variable's unit, not whichever
    # component happened to declare one first.
    result_unit = _result_unit(comparison, by_var, unit, kind)

    note = ""
    if not result.get("values_equal") and not result.get("passes"):
        # formula_expression.evaluate() reports "lhs_greater" / "lhs_less" /
        # "lhs_equal" (or "n/a" when the sides were not comparable). The gap is
        # only a shortfall/excess when the rule was actually breached — on a
        # threshold the reported value clears by design, and "over by" would
        # read as a fault.
        direction = "short by" if result.get("relationship") == "lhs_less" else "over by"
        note = f"{direction} {_format_amount(abs(result['difference']), result_unit)}"
    if result.get("rounding_changed_a_value"):
        note = (note + ", " if note else "") + "after rounding"

    rows.append(error_card.row(
        result_label,
        _expected_cell(comparison, result, result_unit, kind),
        _format_amount(result["lhs_value"], result_unit),
        error_card.STATUS_OK if result.get("passes") else error_card.STATUS_BAD,
        note=note,
        emphasis=True,
    ))
    return rows


def rows_expected(comparison, by_var: dict) -> bool:
    """Whether the matrix will actually list the values a mandatory rule names.
    Without rows to point at, "listed below" would point at nothing."""
    if comparison is None:
        return bool(by_var)
    return bool(comparison.variables())


def _card_headline_formula(rule, comparison, result, labels, unit,
                           kind: str = "", by_var: dict | None = None) -> str:
    """A headline that states the gap, not the category.

    v1 says '<RuleName> did not pass validation', which tells the reader only
    that they are looking at a failure they already knew about. Where the
    numbers were established, the size and direction of the miss are known and
    are said here instead.
    """
    fallback = f"{_humanize_rule_name(rule.get('rule_name', ''))} did not pass validation."

    if result is None or comparison is None:
        return fallback

    if result.get("passes"):
        # Requirement: do NOT declare the validator wrong, and do not imply the
        # data was already fixed. State the inconsistency; the note section
        # below names the possible causes.
        return ("The reported values appear to satisfy this rule, but the validator "
                "reported it as failed.")

    if result.get("boolean_only"):
        missing = [labels.get(v) for v in (result.get("missing_vars") or []) if labels.get(v)]
        if not missing and kind == formula_kind.MANDATORY and by_var is not None:
            # A mandatory-field rule states its requirement through empty(),
            # which never populates missing_vars — the absent values are the
            # expression's variables that have no row in the table at all.
            missing = [labels[v] for v in comparison.variables()
                       if not by_var.get(v) and labels.get(v)]
        if missing:
            # Six field names read as a wall, and a list of role phrases says
            # nothing at all — in both cases the count is the headline and the
            # names are already one row each in the matrix below.
            if len(missing) > 3 or any(_is_fallback_label(m) for m in missing):
                noun, verb = ("value", "is") if len(missing) == 1 else ("values", "are")
                return f"{len(missing)} required {noun} {verb} not reported."
            verb, pronoun = ("is", "it") if len(missing) == 1 else ("are", "them")
            return f"{_join(missing)} {verb} not reported, and this rule requires {pronoun}."
        return fallback

    lhs_var = comparison.lhs_vars[0] if comparison.lhs_vars else ""
    lhs_label = labels.get(lhs_var) or "The reported value"
    rhs_labels = [_label_of(labels, v) for v in comparison.rhs_vars]

    if kind == formula_kind.COUNT:
        # The subject is the NUMBER of rows, not the field being counted.
        reported = _format_amount(result["lhs_value"], "")
        phrase, verb = _count_requirement(result.get("operator", ""), result["rhs_value"])
        noun = _record_noun(result["lhs_value"])
        label = _label_of(labels, lhs_var) if lhs_var else ""
        return (f"{reported} {label} {noun} are reported, but {phrase} are {verb}."
                if label else
                f"{reported} {noun} are reported, but {phrase} are {verb}.")

    # "the sum of its parts" is only true of an addition. formula_kind returns
    # "" for a shape it cannot place, which keeps the previous wording.
    subject = formula_kind.result_subject(kind)
    if not subject:
        if _is_combination(comparison) and rhs_labels:
            subject = "the sum of its parts"
        elif rhs_labels:
            subject = rhs_labels[0]
        else:
            subject = "the value this rule requires"

    if result.get("values_equal"):
        return f"{lhs_label} is exactly equal to {subject}, which this rule does not allow."

    gap = _format_amount(abs(result["difference"]),
                         _result_unit(comparison, by_var or {}, unit, kind))
    direction = "lower" if result.get("relationship") == "lhs_less" else "higher"
    return f"{lhs_label} is {gap} {direction} than {subject}."


# Longest calculation line still worth showing. Past this the substituted
# arithmetic is harder to follow than the values listed above it.
_MAX_CALCULATION_CHARS = 320


def _format_precise(value, unit: str = "", places: int = 10) -> str:
    """Like _format_amount but keeping enough decimals to show an unrounded
    ratio.

    _format_amount trims at four decimals, which is exactly the tolerance these
    rules round to — so the unrounded ratio and the rounded one printed
    identically ('0.0279 = 0.0279') and the rounding step looked like a no-op.
    """
    if value is None:
        return "not reported"
    try:
        dec = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return _format_amount(value, unit)
    if dec == dec.to_integral_value():
        return _format_amount(dec, unit)
    try:
        text = f"{dec:,.{places}f}".rstrip("0").rstrip(".")
    except (InvalidOperation, ValueError):
        return _format_amount(dec, unit)
    symbol = _CURRENCY_SYMBOLS.get((unit or "").strip().upper())
    if symbol:
        return f"{symbol}{text}"
    unit_text = (unit or "").strip()
    if unit_text and unit_text.upper() not in ("PURE", "INF"):
        return f"{text} {unit_text}"
    return text


def _raw_values_by_var(by_var: dict) -> dict[str, list[str]]:
    return {var: [f.get("value", "") for f in facts] for var, facts in by_var.items()}


def _value_of(node, by_var: dict):
    """The value of one sub-expression, computed by the SAME public evaluator
    the verdict came from.

    Used only to show a business-level figure for an expression whose internal
    ×10,000 scaling has been peeled off for display. Nothing about the verdict,
    the compared values or the difference is taken from here — those stay
    exactly as formula_expression.evaluate() reported them for the WHOLE rule.
    Re-deriving the arithmetic by hand instead would be a second implementation
    of the semantics this module is not allowed to own.
    """
    if node is None:
        return None
    try:
        probe = formula_expression.Comparison(
            operator="=", lhs=node,
            rhs=formula_expression.FormulaNode(kind="num", value=Decimal(0)),
            source="", boolean_only=False,
        )
        evaluated = formula_expression.evaluate(probe, _raw_values_by_var(by_var))
    except Exception as exc:                    # never let a display aid raise
        logger.debug("[formula_error] sub-expression value unavailable: %s", exc)
        return None
    if not evaluated:
        return None
    value = evaluated.get("lhs_value")
    return value if isinstance(value, Decimal) else None


def _internal_scaling_hidden(comparison, kind: str) -> bool:
    """Whether this rule's expression carries scaling that the user-facing
    calculation should leave out.

    True only when peeling the wrappers actually changes the tree — so an
    aggregate like `round($V2 div 100000)*100000`, whose core() is already the
    bare variable, is completely unaffected.
    """
    if comparison is None or comparison.rhs is None:
        return False
    if not formula_kind.describes_a_calculation(kind):
        return False
    business = formula_kind.business_node(comparison.rhs)
    return _node_text(business) != _node_text(comparison.rhs.core())


def _scaling_factor_text(result: dict) -> str:
    """The internal scale factor named from the rounding step the engine already
    reported (a step of 0.0001 is produced by a ×10,000), or a neutral phrase
    when the step is not a clean reciprocal."""
    step = result.get("rounding_step") if result else None
    try:
        if step is not None and 0 < Decimal(str(step)) < 1:
            factor = Decimal(1) / Decimal(str(step))
            if factor == factor.to_integral_value():
                return f"{factor:,.0f}"
    except (InvalidOperation, TypeError, ArithmeticError, ZeroDivisionError):
        pass
    return "a fixed factor"


def _node_text(node) -> str:
    """A structural fingerprint for comparing two subtrees cheaply."""
    if node is None:
        return ""
    parts = [node.kind, node.op, node.name, str(node.value)]
    return "|".join(parts) + "(" + ",".join(_node_text(a) for a in node.args) + ")"


def _calculation_points(comparison, result, by_var, labels, unit, kind) -> list[str]:
    """The rule's own arithmetic with the reported figures substituted in.

    Built by handing formula_expression.describe() a value map instead of a
    label map — the SAME renderer that produces the rule sentence, so there is
    no second expression printer to keep in step with the grammar.

    Returns [] rather than a partial line whenever any operand has no reported
    value: a calculation with a hole in it would either mislead or invite the
    reader to assume a zero.
    """
    if comparison is None or result is None or result.get("boolean_only"):
        return []
    if comparison.rhs is None or not formula_kind.describes_a_calculation(kind):
        return []

    if kind == formula_kind.CONDITIONAL:
        return _conditional_calculation_points(comparison, result, by_var, labels,
                                               unit, kind)

    # For a rule whose expression carries an internal ×10,000 (a precision
    # device, not part of the ratio), the user-facing line is built from the
    # de-scaled tree so the reader is not asked to read 279.0095 as a ratio.
    # The rounded expectation and the reported value still come straight from
    # the engine's result, unchanged.
    hides_scaling = _internal_scaling_hidden(comparison, kind)
    core = formula_kind.business_node(comparison.rhs) if hides_scaling else comparison.rhs.core()
    needed = core.variables()
    # One operand renders as a bare figure ('194 = 194'), which restates the
    # matrix row above it. The breakdown of a single aggregated variable is
    # already carried there as "total of N reported values".
    if len(needed) < 2:
        return []

    values: dict[str, str] = {}
    for var in needed:
        total = _var_total(by_var, var)
        if total is None:
            return []                     # never invent, never assume zero
        values[var] = _format_amount(total, _unit_of(by_var, var, unit))

    # phrase_vars suppresses describe()'s "the total of …" narration: the value
    # substituted for an aggregated variable IS already its total.
    expression = formula_expression.describe(core, values, set(needed))
    if not expression:
        return []

    result_unit = _result_unit(comparison, by_var, unit, kind)

    if hides_scaling:
        # The de-scaled expression's own value, from the same evaluator.
        business = _value_of(core, by_var)
        calculated = (_format_precise(business, result_unit) if business is not None
                      else _format_amount(result["rhs_value"], result_unit))
    else:
        raw = result.get("rhs_raw")
        calculated = _format_amount(raw if raw is not None else result["rhs_value"], result_unit)

    line = f"{expression} = {calculated}"
    if len(line) > _MAX_CALCULATION_CHARS:
        return []

    points = [line]
    if result.get("rounding_changed_a_value") or hides_scaling:
        step = result.get("rounding_step")
        step_text = f" to the nearest {_format_amount(step, result_unit)}" if step else ""
        points.append(
            f"Rounded{step_text}: "
            f"{_format_amount(result['rhs_value'], result_unit)} expected, "
            f"{_format_amount(result['lhs_value'], result_unit)} reported."
        )
    return points


# ─────────────────────────────────────────────────────────────────────────────
# What the rule checks, from the validator's own message.
#
# Used when the expression could not be parsed. The previous fallback said only
# "This rule's expression could not be interpreted here", which is honest but
# throws away the one thing that IS available: the validator states the rule in
# business language. Restating that is not evaluation and invents nothing — the
# expected value is still never shown.
# ─────────────────────────────────────────────────────────────────────────────

_MAX_RULE_MESSAGE_CHARS = 400

_AGGREGATOR_WORDS = {"max": "the larger of", "maximum": "the larger of",
                     "min": "the smaller of", "minimum": "the smaller of"}

_AGGREGATOR_RE = __import__("re").compile(
    r"\b(max|maximum|min|minimum)\s*\(", __import__("re").IGNORECASE)


def _message_rule_points(message: str) -> list[str]:
    """The validator's rule statement as readable bullets, or [].

    A MAX(a, b) / MIN(a, b) group is opened into "the larger of:" plus one
    bullet per alternative, because that is the part of these messages a reader
    most often has to unpick. Anything the split cannot handle confidently is
    left as the validator's own sentence — never rewritten into a claim it did
    not make.
    """
    text = message_cleaner.normalise_message(message)
    if not text or len(text) > _MAX_RULE_MESSAGE_CHARS:
        return []

    match = _AGGREGATOR_RE.search(text)
    if not match:
        return [text]

    inner, after = _balanced_group(text, match.end() - 1)
    if inner is None:
        return [text]

    alternatives = [_tidy_operand(part) for part in _split_top_level_commas(inner)]
    alternatives = [a for a in alternatives if a and message_cleaner.looks_like_label(a)]
    if len(alternatives) < 2:
        return [text]

    lead = (text[:match.start()].strip() + " "
            + _AGGREGATOR_WORDS[match.group(1).lower()]).strip()
    points = [f"{lead}:"] + list(alternatives)
    tail = (after or "").strip(" .")
    if tail and message_cleaner.looks_like_label(tail):
        points.append(tail)
    return points


def _balanced_group(text: str, open_at: int) -> tuple[str | None, str]:
    """(inside, remainder) for the bracket group opening at *open_at*."""
    depth = 0
    for i in range(open_at, len(text)):
        if text[i] in "([{":
            depth += 1
        elif text[i] in ")]}":
            depth -= 1
            if depth == 0:
                return text[open_at + 1:i], text[i + 1:]
    return None, ""


def _split_top_level_commas(text: str) -> list[str]:
    parts, current, depth = [], [], 0
    for ch in text or "":
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            parts.append("".join(current))
            current = []
            continue
        current.append(ch)
    parts.append("".join(current))
    return [p for p in (p.strip() for p in parts) if p]


def _conditional_calculation_points(comparison, result, by_var, labels, unit,
                                    kind) -> list[str]:
    """The calculation for a conditional rule — the branch that ACTUALLY
    applies, not the if/then/else scaffolding.

    Rendering the whole conditional produced

        if 0 is equal to 0 or $75,190,000 is equal to 0 then 0, otherwise
        0 ÷ $75,190,000 × 10,000 ÷ 10,000 = 0

    when the facts had already settled the question: the first operand is 0, so
    the rule requires 0. Which branch applies is decided by the same public
    evaluator, and the compared figures below still come from the engine's own
    result for the whole rule.
    """
    branch, reasons = _applied_branch(comparison.rhs, by_var)
    if branch is None:
        return []

    result_unit = _result_unit(comparison, by_var, unit, kind)
    subject = _label_of(labels, comparison.lhs_vars[0]) if comparison.lhs_vars else "this value"

    points: list[str] = []
    reason_text = " and ".join(
        t for t in (_describe_requirement(r, labels) for r in reasons) if t)
    if reason_text:
        points.append(f"Because {reason_text}, this rule requires {subject} to be "
                      f"{_format_amount(result['rhs_value'], result_unit)}.")

    if branch.variables():
        # The applied branch does compute something — show it with the reported
        # figures substituted, de-scaled the same way every other kind is.
        core = formula_kind.business_node(branch)
        needed = core.variables()
        values: dict[str, str] = {}
        for var in needed:
            total = _var_total(by_var, var)
            if total is None:
                values = {}
                break
            values[var] = _format_amount(total, _unit_of(by_var, var, unit))
        if values:
            expression = formula_expression.describe(core, values, set(needed))
            business = _value_of(core, by_var)
            if expression and business is not None:
                line = f"{expression} = {_format_precise(business, result_unit)}"
                if len(line) <= _MAX_CALCULATION_CHARS:
                    points.append(line)
    elif not points:
        # A constant branch with no stateable reason still has a requirement.
        points.append(f"This rule requires {subject} to be "
                      f"{_format_amount(result['rhs_value'], result_unit)}.")

    if points:
        points.append(f"{_format_amount(result['lhs_value'], result_unit)} was reported.")
    return points


def _unavailable_operand_note(comparison, by_var, labels, kind) -> str:
    """A note naming the operands the validation output does not carry.

    Stated only when at least one operand IS present — when nothing at all was
    parsed the card has a different problem, and this sentence would misdescribe
    it. Never invents the missing figure, and never calls it zero.
    """
    if comparison is None or not formula_kind.describes_a_calculation(kind):
        return ""
    variables = comparison.variables()
    absent = [v for v in variables if not by_var.get(v)]
    if not absent or len(absent) == len(variables):
        return ""
    named = [labels[v] for v in absent if labels.get(v)]
    if not named:
        return ""
    subject = formula_kind.result_subject(kind) or "the expected value"
    verb = "is" if len(named) == 1 else "are"
    return (f"{_join(named)} {verb} not available in the validation output, so "
            f"{subject} cannot be independently calculated from the values shown here.")


def _validator_disagreement_note(result, comparison=None, labels=None,
                                 unit: str = "") -> str:
    """The validator failed this rule but the displayed values satisfy it.

    The validator is never declared wrong. The two figures are named — "12.54
    satisfies the displayed threshold (greater than or equal to 0.1)" — and the
    possible causes are listed, because the validator works on an internal
    representation the error file does not show.
    """
    if not result or not result.get("passes"):
        return ""

    detail = ""
    if comparison is not None and not result.get("boolean_only"):
        reported = _format_amount(result.get("lhs_value"), unit)
        meaning = formula_expression.OPERATOR_MEANING.get(
            result.get("operator", ""), result.get("operator", ""))
        required = _format_amount(result.get("rhs_value"), unit)
        if reported and required and meaning:
            label = ""
            if comparison.lhs_vars and labels:
                label = _label_of(labels, comparison.lhs_vars[0])
            subject = f"The reported {label}" if label else "The reported value"
            detail = (f"{subject} ({reported}) satisfies the displayed requirement "
                      f"({meaning} {required}), but the validator reported this check "
                      f"as failed. ")

    return (detail or "The values shown here satisfy this rule, but the validator "
                      "reported it as failed. ") + (
        "The discrepancy may be due to the underlying value, its scaling, precision or "
        "representation, or to another value used during validation — check the source "
        "data before changing the reported figures.")


def _card_locator_items_formula(rule, by_var, labels) -> list[dict]:
    """The rule's identity plus any source location the evidence carries.

    _where_to_check_items() synthesises nothing — when the file has no
    backtracking columns and no db_mapping it returns [], and the card then
    shows the rule alone rather than a made-up location.
    """
    items: list[dict] = []
    name = _humanize_rule_name(rule.get("rule_name", ""))
    if name:
        items.append({"label": "Validation rule", "value": name})
    for item in _where_to_check_items(by_var, labels, rule):
        items.append({"label": item["label"], "value": item["value"], "mono": True})
    return items


def _card_details_sections_formula(comparison, result, by_var, labels, unit,
                                   rule, llm_text, kind: str = "",
                                   omit_requirement: bool = False,
                                   rule_sentence: str = "") -> list[dict]:
    """The drawer — the breakdown the card body no longer leads with.

    Nothing here is new and nothing here is lost: it is v1's Comparison block
    (raw vs rounded, the explicit difference, the rounding step), v1's "Why It
    Failed" prose, and the validator's own message.
    """
    sections: list[dict] = []

    if comparison is not None and result is not None and not result.get("boolean_only"):
        # De-scaled operand values for a rule that multiplies by 10,000
        # internally; None keeps the engine's own raw pair, so aggregates and
        # every other shape are untouched.
        raw_pair = None
        if _internal_scaling_hidden(comparison, kind):
            raw_pair = (_value_of(formula_kind.business_node(comparison.lhs), by_var),
                        _value_of(formula_kind.business_node(comparison.rhs), by_var))
        comparison_items = _comparison_items(
            comparison, result, labels,
            _result_unit(comparison, by_var, unit, kind), kind, raw_pair,
        )
        if comparison_items:
            sections.append({"kind": "values", "heading": "Comparison",
                             "items": comparison_items})
            if raw_pair is not None:
                comparison_items.append({
                    "label": "Note",
                    "value": (f"the rule scales both sides by "
                              f"{_scaling_factor_text(result)} before rounding; that "
                              f"scaling is a precision device and is not shown above"),
                })

    sections.append({
        "kind": "points", "heading": "Why It Failed",
        # concise: the card body's matrix has already printed both figures and
        # the gap, so this block states what the rule required and how the
        # values fell short rather than repeating the numbers a third time.
        "bullets": _why_failed_points(comparison, result, labels,
                                      _result_unit(comparison, by_var, unit, kind),
                                      llm_text, kind, concise=True,
                                      omit_requirement=omit_requirement,
                                      rule_sentence=rule_sentence),
    })

    instances = rule.get("instances") or []
    instance = instances[0] if instances else {"business_message": ""}
    cleaned = message_cleaner.normalise_message(instance.get("business_message", ""))
    if cleaned:
        sections.append({"kind": "rule", "heading": "Validator Message", "text": cleaned})

    return sections


def _emphasis_terms_formula(comparison, labels: dict[str, str]) -> list[str]:
    """The business labels this rule's prose will contain.

    Taken from the resolved label map rather than from the sentence text, so a
    label is highlighted because it IS a label — not because it happened to
    look like one.
    """
    if comparison is None:
        return []
    terms = [labels.get(var) for var in comparison.variables()]
    # Aggregated fact labels appear in the matrix and can appear in prose too.
    terms += list(labels.get("_aggregated_fact_labels") or [])
    return [t for t in terms if t]


def _emphasis_ops_formula() -> list[str]:
    """Every relation the card or the AST could assert.

    The whole set is offered rather than just this rule's operator: the
    renderer highlights only what it actually finds, and a nested expression
    can restate more than one relation in a single sentence.
    """
    return list(formula_expression.OPERATOR_MEANING.values()) + list(error_card.RELATION_PHRASES)


def build_card_sections(
    rule: dict, comparison, result: dict | None, labels: dict[str, str],
    llm_text: dict | None = None,
) -> list[dict]:
    """The v2 unified error card for one formula rule."""
    instances = rule.get("instances") or []
    instance = instances[0] if instances else {"facts": [], "business_message": ""}
    facts = instance.get("facts") or []

    by_var: dict[str, list[dict]] = {}
    for fact in facts:
        by_var.setdefault(fact["var"], []).append(fact)

    # What KIND of check this is, decided once from the AST and threaded into
    # every wording decision below. UNKNOWN keeps the previous wording, so an
    # unrecognised shape is a no-op rather than a regression.
    kind = formula_kind.classify(comparison)
    unit = _card_unit(facts, kind)

    terms = _emphasis_terms_formula(comparison, labels)
    ops = _emphasis_ops_formula()

    sections: list[dict] = [
        error_card.attach_emphasis(
            error_card.headline(
                _card_headline_formula(rule, comparison, result, labels, unit,
                                       kind, by_var)),
            terms, ops,
        ),
    ]

    locator_items = _card_locator_items_formula(rule, by_var, labels)
    if locator_items:
        sections.append(error_card.locator(locator_items))

    # A business-worded sentence for the shapes we classify confidently; ""
    # means "not certain", and the AST restatement below stands unchanged.
    business_sentence = _business_rule_sentence(comparison, labels, kind, by_var)
    rule_sentence = business_sentence or _readable_rule_sentence(comparison, labels)
    if kind == formula_kind.MANDATORY and rows_expected(comparison, by_var):
        # "it is not the case that X is not reported and it is not the case
        # that Y is not reported" is a literal reading of empty() that no
        # reader benefits from. The matrix lists exactly which values.
        rule_sentence = "Every value listed below must be reported."
    if rule_sentence:
        sections.append(error_card.attach_emphasis(
            error_card.rule(rule_sentence), terms, ops))
    elif comparison is None:
        # No parsed expression, so no restatement from the AST — but the
        # validator's own message describes the rule, and saying what is being
        # checked beats saying only that we could not read the formula.
        message_points = _message_rule_points(
            instance.get("business_message", ""))
        if message_points:
            sections.append({"kind": "points", "heading": "What the rule checks",
                             "bullets": message_points})

    rows = _card_matrix_rows_formula(comparison, result, by_var, labels, unit, rule, kind)
    if rows:
        sections.append(error_card.matrix(
            rows, heading="Values",
            label_col="Item", expected_col="Expected", actual_col="You reported",
        ))

    # The rule's arithmetic with the reported figures substituted in, so the
    # reader never has to reconstruct it from the rows above. Emitted as a
    # "points" section: the UI already renders that kind, and it stays out of
    # the headline/locator/rule/matrix/fix/details spine both error types share.
    calculation = _calculation_points(comparison, result, by_var, labels, unit, kind)
    if calculation:
        sections.append(error_card.attach_emphasis(
            {"kind": "points", "heading": "Calculation", "bullets": calculation},
            terms, ops,
        ))

    unavailable = _unavailable_operand_note(comparison, by_var, labels, kind)
    if unavailable:
        sections.append({"kind": "note", "text": unavailable})

    if comparison is None:
        # Says WHY there is no expected column, instead of leaving the reader
        # to wonder. Nothing is guessed about the rule, and no expected value
        # is shown or implied.
        sections.append({"kind": "note", "text": (
            "The expression could not be independently calculated from the available "
            "formula representation, so the expected value is not shown. The values "
            "the validation output reported are listed above."
            if facts else
            "The expression could not be independently calculated from the available "
            "formula representation, so the expected value is not shown."
        )})

    uncomparable = _uncomparable_threshold_note(comparison, result, by_var, labels)
    if uncomparable:
        sections.append({"kind": "note", "text": uncomparable})

    disagreement = _validator_disagreement_note(
        result, comparison, labels, _result_unit(comparison, by_var, unit, kind))
    if disagreement:
        sections.append({"kind": "note", "text": disagreement})

    # Batch scope belongs in the body, not the drawer: a reader who fixes the
    # one shown item needs to know another eleven are waiting.
    if len(instances) > 1:
        sections.append({
            "kind": "note",
            "text": (f"This rule failed for {len(instances)} reported items; "
                     f"the first is shown above."),
        })

    sections.append(error_card.attach_emphasis(
        error_card.fix(_how_to_fix_points(comparison, result, labels, llm_text, kind)),
        terms, ops,
    ))

    drawer_sections = _card_details_sections_formula(
        comparison, result, by_var, labels, unit, rule, llm_text, kind,
        omit_requirement=bool(business_sentence),
        rule_sentence=business_sentence,
    )
    # "Why It Failed" restates the same labels and relation as the body, so it
    # gets the same treatment — the drawer is where the reader goes when the
    # summary was not enough, which is exactly when legibility matters most.
    for section in drawer_sections:
        if section.get("kind") == "points":
            error_card.attach_emphasis(section, terms, ops)

    drawer = error_card.details(drawer_sections)
    if drawer:
        sections.append(drawer)
    return sections


def render_card(
    rule: dict, comparison, result: dict | None, labels: dict[str, str],
    llm_text: dict | None = None,
) -> str:
    """Plain-text form of the v2 card."""
    header = f"⚙ Formula Error — {rule.get('rule_name', '')}".rstrip(" —")
    return error_card.sections_to_text(
        header, build_card_sections(rule, comparison, result, labels, llm_text),
    )


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 5 — LLM payload
# ═════════════════════════════════════════════════════════════════════════════

# Vocabulary guidance handed to the model alongside the verified facts. It
# constrains WORDING only — every number and the verdict itself are computed
# before this payload is built and are not the model's to change.
_LLM_KIND_GUIDANCE_DEFAULT = (
    "Describe this as a comparison between the reported value and the value the rule "
    "requires. Do not call it a sum or a total unless the rule adds values together."
)

_LLM_KIND_GUIDANCE = {
    formula_kind.AGGREGATE: (
        "This rule adds values together. 'sum of the component values' and "
        "'calculated total' are correct here."
    ),
    formula_kind.RATIO: (
        "This rule DIVIDES one value by another. Call the result a ratio or a "
        "calculated value. Never call it a sum, a total, or 'the sum of its parts', "
        "and never attach a currency symbol to it."
    ),
    formula_kind.PERCENTAGE: (
        "This rule computes a PERCENTAGE. Call the result a calculated percentage. "
        "Never call it a sum or a total, and never attach a currency symbol to it."
    ),
    formula_kind.WEIGHTED_AVERAGE: (
        "This rule computes a WEIGHTED AVERAGE. Call the result a calculated weighted "
        "average. Never call it a sum or a total, and never attach a currency symbol "
        "to it."
    ),
    formula_kind.EQUALITY: (
        "This rule requires two reported values to match. Say they must be equal."
    ),
    formula_kind.THRESHOLD: (
        "This rule sets a limit. State it as the reported value having to stay above "
        "or below the given figure, using the operator meaning supplied."
    ),
    formula_kind.COUNT: (
        "This rule counts reported records. Talk about the number of values reported."
    ),
    formula_kind.MANDATORY: (
        "This rule requires values to be present. Say the required values are missing."
    ),
    formula_kind.CONDITIONAL: (
        "This rule applies a condition. Explain the condition in plain words; do not "
        "call the result a sum or a total."
    ),
}


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
    lhs_label = _label_of(labels, lhs_var) if lhs_var else ""
    signed = comparison.rhs.signed_variables() if comparison.rhs is not None else []
    terms = signed or [(v, 1) for v in comparison.rhs_vars]
    kind = formula_kind.classify(comparison)

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
            "label": _label_of(labels, var),
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

    required = [lhs_label] + [_label_of(labels, v) for v, _s in terms]
    # A label the cascade could not resolve is not a term the model can be
    # required to quote — demanding it would reject every answer.
    # A role phrase ("Component amount 1") is not a business name the model can
    # be required to quote verbatim — demanding it would reject every answer.
    required = [t for t in required if t and not _is_fallback_label(t)]

    payload = {
        "formula": comparison.source,
        "rule": _rule_sentence(comparison, labels),
        "operator_meaning": result["operator_meaning"],
        "relationship": result["relationship"],
        "relationship_meaning": _relationship_sentence(
            result["relationship"], lhs_label, [_label_of(labels, v) for v, _s in terms]),

        # What the rule DOES, so the model does not describe a ratio or a
        # weighted average as a sum. The verdict and every figure below are
        # still the backend's — this only constrains vocabulary.
        "formula_type": kind,
        "how_to_describe_the_calculation": _LLM_KIND_GUIDANCE.get(
            kind, _LLM_KIND_GUIDANCE_DEFAULT),

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
    return payload, required


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

        # v2 = the unified error card shared with dimension errors; v1 = the
        # original per-type sections. Chosen per request (not at import) so
        # ERROR_CARD_V2 can be flipped with a restart and no code change.
        if error_card.v2_enabled():
            sections = build_card_sections(rule, comparison, result, labels, llm_text)
            out["explanation"] = render_card(rule, comparison, result, labels, llm_text)
        else:
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
