# backend/tools/dimension_error.py — the generic dimension-error explainer (V2).
#
#   panel-bounded extraction
#     -> per-error facts (concept / context / dimension / value / class)
#     -> taxonomy resolution (hypercube, axes, typed vs explicit, members)
#     -> observation of what was actually reported (the run's InstanceDocPath
#        instance document, when the log records one and it exists)
#     -> deterministic diff (missing axis / invalid member / bad typed value)
#     -> grounded LLM phrasing
#     -> user-facing explanation
#
# Nothing here keys off a form id, a concept name, a dimension name, a member
# name, or an error message. The error class routes the diff, the taxonomy
# supplies the expectation, and the instance document (when available) supplies
# the observation.
#
# Fixes carried over from the analysis, all reproduced on real files:
#   * attribute tail parsing: 'value = 2. In ATM' was truncated to '2.', and
#     'unit = decimal = precision =' (empty unit) yielded unit='decimal'.
#     Both come from '(\S+)' value capture; this module scans key boundaries.
#   * 2047's 23 errors all returned "Cannot be determined" because the
#     definition linkbase could not be located by filename. taxonomy_index
#     finds it by content.
#   * the typed-dimension "reported value" was the CONTEXT ID, because that is
#     what the validator message quotes. The instance document named by the
#     run's InstanceDocPath has the real value; without it, NO value is
#     asserted — a context concatenates every dimension it carries, so picking
#     one of its segments would name the wrong axis' value more often than not.

from __future__ import annotations

import logging
import re

from backend.tools import error_file_shape as shape
from backend.tools import error_llm, instance_context, taxonomy_index

logger = logging.getLogger(__name__)

__all__ = [
    "parse_dimension_errors", "build_evidence", "render_explanation",
    "build_sections", "sections_to_text", "explain_dimension_errors",
]

_NOT_DETERMINABLE = "Cannot be determined from the available data."

# Attribute keys the validator appends to a dimension message, in either the
# bare ('name = X') or BTDetails ('@name = X') spelling.
_ATTR_KEYS = (
    "name", "value", "context", "unit", "decimal", "precision", "dimension",
    "typedomainrefschema", "typedomainrefinstance",
)
_ATTR_KEY_RE = re.compile(
    r"@?\b(" + "|".join(_ATTR_KEYS) + r")\s*=", re.IGNORECASE,
)

_DIRECT_MSG_RE = re.compile(
    r"""<td[^>]*class=["'][^"']*directMsg[^"']*["'][^>]*>(.*?)</td>""",
    re.S | re.IGNORECASE,
)
_DETAILS_RE = re.compile(
    r"""<span[^>]*class=["'][^"']*msgDetails[^"']*["'][^>]*>(.*?)</span>""",
    re.S | re.IGNORECASE,
)

_PLACEHOLDER_SUFFIX_RE = re.compile(r"_OOOOO+\w*$")


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 1 — extraction
# ═════════════════════════════════════════════════════════════════════════════

def _parse_attribute_tail(text: str) -> dict[str, str]:
    """Split the 'name = X value = Y context = Z unit = decimal = …' tail by
    KEY BOUNDARIES rather than by whitespace.

    Each value runs to the start of the next recognised key (or end of text),
    so a value containing spaces survives intact and an empty value stays
    empty instead of swallowing the following key's name. That is the whole
    fix for both attribute bugs; nothing about the key list is return-specific.
    """
    matches = list(_ATTR_KEY_RE.finditer(text or ""))
    out: dict[str, str] = {}
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        key = m.group(1).lower()
        value = text[m.end():end].strip().strip("|").strip()
        out.setdefault(key, value)
    return out


def _parse_direct_messages(panel_html: str) -> list[dict]:
    entries: list[dict] = []
    for cell in _DIRECT_MSG_RE.findall(panel_html or ""):
        details_m = _DETAILS_RE.search(cell)
        details = shape.strip_tags(details_m.group(1)) if details_m else ""
        main = re.sub(r"\s+", " ", shape.strip_tags(_DETAILS_RE.sub("", cell))).strip()
        if not main:
            continue

        error_class_m = re.search(r"\[([^\]]+)\]", main)
        error_class = error_class_m.group(1).strip() if error_class_m else ""
        section_m = re.match(r"^\s*(\d+(?:\.\d+)+)\s*\[", main)

        attrs = _parse_attribute_tail(main)

        concept = attrs.get("name", "")
        if not concept:
            prose = re.search(r"concept\s+'([^']+)'", main)
            concept = prose.group(1) if prose else ""

        dimension = attrs.get("dimension", "")
        if not dimension:
            prose = re.search(r"(?:typed|explicit)?\s*dimension\s+'([^']+)'", main)
            dimension = prose.group(1) if prose else ""

        quoted_value = ""
        vm = re.search(r"Value\s+'([^']*)'\s+provided", main)
        if vm:
            quoted_value = vm.group(1)

        # The prose part is everything before the attribute tail.
        first_key = _ATTR_KEY_RE.search(main)
        prose_only = main[: first_key.start()] if first_key else main
        prose_only = re.sub(r"^[\d.]+\s*\[[^\]]*\]\s*:\s*", "", prose_only).strip().rstrip("|").strip()

        details_of = lambda pat: (re.search(pat, details, re.IGNORECASE).group(1)
                                  if re.search(pat, details, re.IGNORECASE) else "")
        context = attrs.get("context", "")
        entries.append({
            "error_class":          error_class,
            "section_ref":          section_m.group(1) if section_m else "",
            "concept":              concept,
            "value":                attrs.get("value", ""),
            "context":              context,
            "unit":                 attrs.get("unit", ""),
            "decimal":              attrs.get("decimal", ""),
            "precision":            attrs.get("precision", ""),
            "dimension":            dimension,
            "message_quoted_value": quoted_value,
            "typed_domain_schema":  attrs.get("typedomainrefschema", ""),
            "typed_domain_instance": attrs.get("typedomainrefinstance", ""),
            "is_duplicate_context": bool(context and _PLACEHOLDER_SUFFIX_RE.search(context)),
            "error_code":           details_of(r"(?:Error|Warning)\s*Code\s*:\s*(\S+?)(?:LineNo|$)"),
            "filename":             details_of(r"FileName\s*:\s*(\S+\.xml)"),
            "line_no":              details_of(r"LineNo\s*:\s*(\d+)"),
            "col_no":               details_of(r"ColumnNo\s*:\s*(\d+)"),
            "raw_message":          prose_only,
        })
    return entries


def parse_dimension_errors(html_path: str) -> list[dict]:
    """Dimension errors from the DIMENSION panel only.

    Panel bounding is not optional: every SPECIFICATION_ERROR panel uses the
    same `directMsg` markup, so an unbounded scan reports TABLE-panel warnings
    as dimension errors (measured: 2036 has a DIMENSION badge of 0 and a TABLE
    badge of 42, and an unbounded scan returns all 42).
    """
    raw = shape.read_error_file(html_path)
    if not raw:
        return []

    panels = shape.split_spec_panels(raw)
    panel_html = panels.get("DIMENSION", "")
    if not panel_html:
        return []

    entries = _parse_direct_messages(panel_html)
    logger.info("[dimension_error] %d dimension error(s) parsed from %s",
                len(entries), html_path)
    return entries


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 2 — evidence assembly
# ═════════════════════════════════════════════════════════════════════════════

def _observed_dimensions(error_file_path: str, context_id: str, form_id: str = "") -> tuple[list[dict] | None, str]:
    """(dimensions, source). dimensions is None when nothing could be observed.

    'instance_document' is a real observation. 'context_id_suffix' is a
    labelled inference from the context naming convention, and callers must
    present it as such — the two are never conflated.
    """
    try:
        observed = instance_context.context_dimensions(error_file_path, context_id, form_id)
    except Exception as exc:
        logger.warning("[dimension_error] instance observation failed: %s", exc)
        observed = None
    if observed is not None:
        return observed, "instance_document"
    return None, "context_id_suffix"




def _value_matches_base_type(value: str, base_type: str, facets: dict) -> bool | None:
    """Does *value* satisfy the typed domain's declared XSD type?

    None means "cannot be checked" (an unmodelled base type, or an empty
    value) and must never be reported as "invalid". Only the primitives the
    corpus actually constrains on are checked; the rest degrade to None
    rather than to a guess.
    """
    text = (value or "").strip()
    if not text:
        return None
    base = taxonomy_index.local_name(base_type).lower()

    patterns = {
        "date": r"^-?\d{4}-\d{2}-\d{2}(?:Z|[+-]\d{2}:\d{2})?$",
        "datetime": r"^-?\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?$",
        "gyearmonth": r"^-?\d{4}-\d{2}$",
        "gyear": r"^-?\d{4}$",
        "time": r"^\d{2}:\d{2}:\d{2}(?:\.\d+)?$",
        "boolean": r"^(?:true|false|0|1)$",
        "integer": r"^[+-]?\d+$",
        "int": r"^[+-]?\d+$",
        "long": r"^[+-]?\d+$",
        "nonnegativeinteger": r"^\+?\d+$",
        "decimal": r"^[+-]?(?:\d+\.?\d*|\.\d+)$",
        "double": r"^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$",
        "float": r"^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$",
    }

    ok: bool | None = None
    if base in patterns:
        ok = bool(re.match(patterns[base], text))
    elif base in ("string", "normalizedstring", "token", "anyuri"):
        ok = True

    # A declared pattern facet is stricter than the primitive, so it decides.
    for declared in (facets or {}).get("pattern", []):
        try:
            if not re.match(f"^(?:{declared})$", text):
                return False
            ok = True if ok is None else ok
        except re.error:
            continue

    enumerations = (facets or {}).get("enumeration", [])
    if enumerations:
        return text in enumerations

    return ok


def _resolve_index(form_id: str, error_file_path: str):
    """Taxonomy index for this error, preferring folders named by the filing's
    own schemaRef when an instance document is available.

    schemaRef is the strongest available signal for WHICH taxonomy a filing
    used, and it matters because a form's own DataBase/<form_id>/Taxonomy
    folder is not always the taxonomy the filing was validated against
    (measured: 4038's folder holds mpd07 while its error file is mpd03).
    """
    extra: list[str] = []
    try:
        for ref in instance_context.schema_refs(error_file_path, form_id):
            extra.extend(taxonomy_index.find_roots_for_schema(ref))
    except Exception as exc:
        logger.debug("[dimension_error] schemaRef resolution skipped: %s", exc)
    try:
        return taxonomy_index.get_index_for_form(form_id, tuple(extra))
    except Exception as exc:
        logger.warning("[dimension_error] taxonomy index unavailable: %s", exc)
        return None


def build_evidence(err: dict, form_id: str, error_file_path: str) -> dict:
    """All verified facts about one dimension error. Never raises.

    Keys are always present; a value of None/"" means "not established", and
    the renderer is responsible for saying so honestly rather than filling it
    in. This dict is also what the LLM payload is derived from — so anything
    the model can say has to be provable from here.
    """
    concept = (err.get("concept") or "").strip()
    context = (err.get("context") or "").strip()
    error_class = (err.get("error_class") or "").strip()

    evidence: dict = {
        "error_class": error_class,
        "concept_id": concept,
        "concept_label": "",
        "context_id": context,
        "reported_fact_value": (err.get("value") or "").strip(),
        "unit": (err.get("unit") or "").strip(),
        "decimal": (err.get("decimal") or "").strip(),
        "taxonomy_found": False,
        "taxonomy_source": "",
        "hypercube_closed": None,
        "expected_axes": [],
        "observed_dimensions": None,
        "observation_source": "",
        "instance_document_used": False,
        "focus_axis": None,
        "missing_axes": [],
        "unexpected_axes": [],
        "invalid_members": [],
        "typed_value_check": None,
        "diagnosis": "",
    }

    index = _resolve_index(form_id, error_file_path)
    if index is None:
        evidence["diagnosis"] = "no_taxonomy"
        return evidence

    if concept:
        evidence["concept_label"] = _clean_label(index.concept_label(concept))

    observed, observation_source = _observed_dimensions(error_file_path, context, form_id)
    evidence["observed_dimensions"] = observed
    evidence["observation_source"] = observation_source if observed is not None else "none"
    evidence["instance_document_used"] = observed is not None

    # ── the axis this error is about, when the validator named one ──────────
    named_axis = (err.get("dimension") or "").strip()
    if named_axis:
        axis = index.axis_info(named_axis)
        if axis:
            evidence["taxonomy_found"] = True
            evidence["taxonomy_source"] = axis.get("source_file", "")
            evidence["focus_axis"] = _axis_public(axis, index)

    # ── the axes this concept's hypercube requires ──────────────────────────
    expected = index.describe_axis_for_concept(concept) if concept else []
    # Taxonomy labels for whatever the instance document reports, so observed
    # members are named the same way the requirements are.
    axis_labels: dict[str, str] = {}
    for axis in expected:
        axis_labels[axis.get("axis_id", "")] = _clean_label(axis.get("label"))
    for entry in (observed or []):
        axis_id = taxonomy_index.local_name(entry.get("dimension", ""))
        if axis_id and not axis_labels.get(axis_id):
            info = index.axis_info(axis_id)
            if info and info.get("label"):
                axis_labels[axis_id] = _clean_label(info["label"])
    evidence["_axis_labels"] = {k: v for k, v in axis_labels.items() if k and v}

    if expected:
        evidence["taxonomy_found"] = True
        hypercube = index.hypercube_for_concept(concept) or {}
        evidence["taxonomy_source"] = hypercube.get("source_file", "") or evidence["taxonomy_source"]
        evidence["hypercube_closed"] = hypercube.get("closed")
        evidence["expected_axes"] = [_axis_public(a, index) for a in expected]

    _diagnose(evidence, err, index)
    return evidence


_ROLE_SUFFIX_RE = re.compile(
    r"\s*\[(member|axis|domain|line items|table|abstract|hypercube)\]\s*$",
    re.IGNORECASE,
)


def _clean_label(label: str) -> str:
    """Drop a taxonomy role marker from a label ('Other [member]' -> 'Other').

    These markers disambiguate roles inside the taxonomy; repeating them in a
    business explanation is noise, and the section already says whether a
    dimension is typed or explicit.
    """
    return _ROLE_SUFFIX_RE.sub("", (label or "").strip()).strip()


def _axis_public(axis: dict, index) -> dict:
    """One axis reduced to the facts an explanation may use."""
    typed = axis.get("typed_domain") or None
    return {
        "axis_id": axis.get("axis_id", ""),
        "label": _clean_label(axis.get("label")) or taxonomy_index.humanize_local_name(
            axis.get("axis_id", ""), ("Axis", "Dimension")),
        "is_typed": bool(axis.get("is_typed")),
        "required_value": None if not typed else {
            "base_type": typed.get("base_type", ""),
            "description": (typed.get("example") or {}).get("description", ""),
            "example": (typed.get("example") or {}).get("sample", ""),
            "facets": typed.get("facets") or {},
        },
        "allowed_members": [
            {"id": m.get("id", ""),
             "label": _clean_label(m.get("label")) or taxonomy_index.humanize_local_name(
                 m.get("id", ""), ("Member", "Domain"))}
            for m in (axis.get("members") or [])
        ],
    }


def _diagnose(evidence: dict, err: dict, index) -> None:
    """Compare expectation against observation and record what is wrong.

    Every branch either establishes a specific finding or leaves `diagnosis`
    at a value that tells the renderer exactly how much it may claim.
    """
    error_class = evidence["error_class"]
    expected_axes = evidence["expected_axes"]
    observed = evidence["observed_dimensions"]

    if "IllegalTypedDimensionContent" in error_class:
        _diagnose_typed_content(evidence, err, index)
        return

    if not expected_axes:
        evidence["diagnosis"] = "concept_not_in_taxonomy" if evidence["taxonomy_found"] \
            else "no_taxonomy"
        return

    expected_ids = {a["axis_id"] for a in expected_axes}

    if observed is None:
        # No observation: we can still state precisely what the taxonomy
        # requires, which is more than the previous "cannot be determined".
        evidence["diagnosis"] = "expectation_only"
        return

    observed_ids = {taxonomy_index.local_name(d.get("dimension", "")) for d in observed}
    evidence["missing_axes"] = sorted(expected_ids - observed_ids)
    evidence["unexpected_axes"] = sorted(observed_ids - expected_ids)

    invalid: list[dict] = []
    by_id = {a["axis_id"]: a for a in expected_axes}
    for item in observed:
        axis_id = taxonomy_index.local_name(item.get("dimension", ""))
        axis = by_id.get(axis_id)
        if not axis:
            continue
        value = (item.get("value") or "").strip()
        if axis["is_typed"]:
            required = axis.get("required_value") or {}
            ok = _value_matches_base_type(value, required.get("base_type", ""),
                                          required.get("facets") or {})
            if ok is False:
                invalid.append({"axis_id": axis_id, "axis_label": axis["label"],
                                "reported": value, "reason": "wrong_value_type"})
        else:
            allowed = {m["id"] for m in axis.get("allowed_members", [])}
            if allowed and value and value not in allowed:
                invalid.append({"axis_id": axis_id, "axis_label": axis["label"],
                                "reported": value, "reason": "member_not_allowed"})
    evidence["invalid_members"] = invalid

    if evidence["missing_axes"]:
        evidence["diagnosis"] = "missing_axes"
    elif invalid:
        evidence["diagnosis"] = "invalid_member"
    elif evidence["unexpected_axes"]:
        evidence["diagnosis"] = "unexpected_axes"
    else:
        # Every axis present and individually valid — the combination itself is
        # what the taxonomy rejects. Saying so is accurate; claiming a specific
        # culprit would not be.
        evidence["diagnosis"] = "invalid_combination"


def _diagnose_typed_content(evidence: dict, err: dict, index) -> None:
    """xbrldie:IllegalTypedDimensionContentError.

    The validator names the axis but quotes the CONTEXT ID where the offending
    value should be, so the reported value comes from the instance document
    when available and from the context suffix (clearly labelled) otherwise.
    """
    axis_name = (err.get("dimension") or "").strip()
    axis = index.axis_info(axis_name) if axis_name else None
    if not axis:
        evidence["diagnosis"] = "axis_not_in_taxonomy"
        return

    evidence["taxonomy_found"] = True
    evidence["taxonomy_source"] = axis.get("source_file", "") or evidence["taxonomy_source"]
    public = _axis_public(axis, index)
    evidence["focus_axis"] = public

    reported, source = "", "unavailable"
    observed = evidence.get("observed_dimensions")
    if observed:
        for item in observed:
            if taxonomy_index.local_name(item.get("dimension", "")) == public["axis_id"]:
                reported, source = (item.get("value") or "").strip(), "instance_document"
                break
    if not reported:
        # The validator quotes the CONTEXT ID in its "Value '…' provided" slot
        # for this error class, so that field is only usable when it is
        # something other than the context id echoed back.
        quoted = (err.get("message_quoted_value") or "").strip()
        if quoted and quoted != evidence["context_id"]:
            reported, source = quoted, "validator_message"
        # Deliberately NO fallback to the context id's trailing segment. A
        # context concatenates every dimension's value, and the trailing one
        # frequently belongs to a different axis entirely (measured: 4012's
        # DateAxis error ends in 'FluctuationOfPriceAndFreightRiskMember',
        # 2047's ends in '3InTransitCashVansetc'). Naming either as "the value
        # reported for this dimension" would be a confident falsehood, so the
        # value is simply reported as unavailable and the context is shown.

    required = public.get("required_value") or {}
    check = None
    if reported and required.get("base_type"):
        check = _value_matches_base_type(reported, required["base_type"],
                                         required.get("facets") or {})

    evidence["typed_value_check"] = {
        "reported": reported,
        "reported_source": source,
        "base_type": required.get("base_type", ""),
        "description": required.get("description", ""),
        "example": required.get("example", ""),
        "matches": check,
    }
    evidence["diagnosis"] = "typed_value_invalid" if check is False else "typed_value_unverified"


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 3 — deterministic rendering
#
# The explanation is built as typed SECTIONS first and serialised to text
# second, so the UI renders real headings and the text form carries no markdown
# emphasis markers. Each section has one job and does not restate another's:
#
#   Concept / Reported value       what the error file says was reported
#   Dimensions involved            which dimensions apply, and their kind
#   What the taxonomy requires     the rule for each dimension
#   Dimension members reported     what the instance document actually carried
#   What is wrong                  the diagnosis, without repeating requirements
#   How to fix                     the action, without repeating the diagnosis
# ═════════════════════════════════════════════════════════════════════════════

_NO_MEMBER_EVIDENCE = (
    "Not available — no generated return file was saved for this run, so the details "
    "that were actually supplied could not be read."
)


def _join_natural(items: list[str]) -> str:
    items = [i for i in items if i]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def _member_names(axis: dict, limit: int = 8) -> str:
    members = [m["label"] or m["id"] for m in axis.get("allowed_members", [])]
    if not members:
        return ""
    shown = ", ".join(members[:limit])
    if len(members) > limit:
        shown += f" (and {len(members) - limit} more — {len(members)} options in total)"
    return shown


def _axis_kind(axis: dict) -> str:
    """How a user supplies this detail, said the way they would say it.

    'Typed' and 'Explicit' are the taxonomy's own words for the distinction and
    mean nothing to someone filling in a return. What actually matters to them
    is whether they write the value themselves or choose it from a fixed list,
    so that is what the line says.
    """
    return "You enter the value" if axis.get("is_typed") else "Pick one from a fixed list"


def _axis_requirement(axis: dict) -> str:
    """What the taxonomy requires of ONE dimension, stated once."""
    if axis.get("is_typed"):
        required = axis.get("required_value") or {}
        description = required.get("description")
        base = required.get("base_type")
        example = required.get("example")
        if description:
            text = description[0].upper() + description[1:]
        elif base:
            text = f"Any value of type {base}"
        else:
            text = "A value in the format the taxonomy defines for it"
        facets = required.get("facets") or {}
        patterns = facets.get("pattern") or []
        if patterns:
            text += f", matching the pattern {patterns[0]}"
        if example:
            text += f" (example: {example})"
        return text
    members = _member_names(axis)
    if members:
        return f"Pick one of these: {members}"
    return "One of the options the taxonomy lists for it (none are listed here)"


def _display_axes(evidence: dict) -> list[dict]:
    """The dimensions this error is about: the one the validator named, or all
    of the ones the concept's hypercube requires."""
    focus = evidence.get("focus_axis")
    if focus:
        return [focus]
    return evidence.get("expected_axes") or []


def _concept_display(evidence: dict) -> str:
    label = (evidence.get("concept_label") or "").strip()
    concept_id = (evidence.get("concept_id") or "").strip()
    if label and concept_id and label.lower() != concept_id.lower():
        return f"{label} ({concept_id})"
    return label or concept_id


def _reported_value_display(evidence: dict) -> str:
    """The FACT's reported value, straight from the error file.

    This is distinct from the dimension members and must never be suppressed
    because the instance document is missing — the validator message itself
    carries it, and hiding it while the same error shows the concept it belongs
    to reads as a contradiction.
    """
    value = (evidence.get("reported_fact_value") or "").strip()
    if not value:
        return ""
    unit = (evidence.get("unit") or "").strip()
    if unit and unit.upper() not in ("PURE", "INF"):
        return f"{value} {unit}"
    return value


def _reported_members(evidence: dict) -> tuple[list[dict], str]:
    """(items, note) for what the context actually carried.

    Items come only from the instance document. When there is none, the items
    list is empty and the note says so — a guess derived from the context id
    would name the wrong axis more often than not.
    """
    observed = evidence.get("observed_dimensions")
    if observed:
        items = []
        for entry in observed:
            axis_id = taxonomy_index.local_name(entry.get("dimension", ""))
            label = evidence.get("_axis_labels", {}).get(axis_id) or \
                taxonomy_index.humanize_local_name(axis_id, ("Axis", "Dimension"))
            items.append({"label": label, "value": entry.get("value", "") or "(empty)"})
        return items, ""
    if observed == []:
        return [], "The generated return file shows this figure carries no details at all."
    return [], _NO_MEMBER_EVIDENCE


def _typed_value_line(evidence: dict) -> str:
    """The typed dimension's own reported value, when one could be established."""
    check = evidence.get("typed_value_check") or {}
    reported = (check.get("reported") or "").strip()
    if not reported:
        return ""
    if check.get("reported_source") == "instance_document":
        return f"{reported} (read from the generated return file)"
    if check.get("reported_source") == "validator_message":
        return f"{reported} (as quoted by the validator)"
    return reported


def _what_is_wrong_points(evidence: dict) -> list[str]:
    """The diagnosis. Deliberately does NOT restate the taxonomy requirements —
    those have their own section — and never claims a dimension is missing or
    invalid unless the evidence establishes it."""
    diagnosis = evidence.get("diagnosis")
    axes = _display_axes(evidence)
    points: list[str] = []

    if diagnosis == "typed_value_invalid":
        check = evidence["typed_value_check"]
        axis = axes[0]["label"] if axes else "this detail"
        points.append(f"The value entered for {axis} is {check.get('reported')}.")
        points.append("That is not written in the format this detail has to follow.")
        return points

    if diagnosis == "typed_value_unverified":
        axis = axes[0]["label"] if axes else "this detail"
        points.append(f"The value entered for {axis} on this figure was rejected.")
        line = _typed_value_line(evidence)
        if line:
            points.append(f"The value that could be recovered for it is {line}.")
        else:
            points.append(
                "The error file repeats the context id instead of the value itself, and no "
                "generated return file was saved for this run, so the exact value that was "
                "rejected could not be recovered."
            )
        return points

    if diagnosis == "missing_axes":
        missing = [a["label"] for a in axes if a["axis_id"] in (evidence.get("missing_axes") or [])]
        points.append(
            f"The generated return file does not include {_join_natural(missing)} for this figure."
        )
        points.append("Every figure has to carry all of the details listed above — none of "
                      "them can be left out.")
        return points

    if diagnosis == "invalid_member":
        for item in evidence.get("invalid_members") or []:
            if item["reason"] == "member_not_allowed":
                points.append(f"{item['axis_label']} was reported as {item['reported']}, "
                              f"which is not one of the options allowed for it.")
            else:
                points.append(f"{item['axis_label']} was reported as {item['reported']}, "
                              f"which is not written in the format it has to follow.")
        return points

    if diagnosis == "unexpected_axes":
        extra = _join_natural(evidence.get("unexpected_axes") or [])
        points.append(f"This figure carries {extra}, which does not belong to it.")
        return points

    if diagnosis == "invalid_combination":
        points.append("All of the required details are present, and each value on its own is "
                      "allowed.")
        points.append("It is these particular values used together that are not permitted for "
                      "this figure.")
        return points

    if diagnosis == "expectation_only":
        return [
            "This figure was reported against a set of details that is not allowed.",
            "The error file names the details this figure needs, but does not show which "
            "particular one is missing or wrong.",
            "So the exact detail at fault could not be pinned down from what is available.",
        ]

    if diagnosis == "concept_not_in_taxonomy":
        points.append("The details used for this figure were rejected.")
        points.append("The taxonomy found for this return does not list this item as one that "
                      "takes details at all — usually that means it does not belong in this "
                      "report, or the return was built against a different taxonomy version.")
        return points

    if diagnosis == "axis_not_in_taxonomy":
        points.append("The value used for one of this figure's details was rejected.")
        points.append("That detail is not defined in the taxonomy found for this return, which "
                      "usually means the return was built against a different taxonomy "
                      "version.")
        return points

    points.append("The set of details used for this figure was rejected.")
    points.append("No taxonomy could be found for this return, so which detail is at fault "
                  "could not be worked out.")
    return points


def _how_to_fix_points(evidence: dict) -> list[str]:
    """Actions only — no restatement of the diagnosis or the requirements."""
    diagnosis = evidence.get("diagnosis")
    axes = _display_axes(evidence)

    if diagnosis in ("typed_value_invalid", "typed_value_unverified"):
        axis = axes[0]["label"] if axes else "the detail"
        required = (axes[0].get("required_value") or {}) if axes else {}
        example = required.get("example")
        step = f"Correct the {axis} value in your source data"
        if example:
            step += f" so it is written like {example}"
        return [step + ".", "Generate the return again and re-run validation."]

    if diagnosis == "missing_axes":
        missing = [a["label"] for a in axes if a["axis_id"] in (evidence.get("missing_axes") or [])]
        return [f"Add {_join_natural(missing)} for this figure in your source data.",
                "Generate the return again and re-run validation."]

    if diagnosis == "invalid_member":
        names = _join_natural([i["axis_label"] for i in evidence.get("invalid_members") or []])
        return [f"Change the value reported for {names} to one of the allowed options.",
                "Generate the return again and re-run validation."]

    if diagnosis == "unexpected_axes":
        return ["Remove the details that do not belong to this figure.",
                "Generate the return again and re-run validation."]

    if diagnosis in ("concept_not_in_taxonomy", "axis_not_in_taxonomy"):
        return ["Check that the return is being generated against the taxonomy version this "
                "filing period expects.",
                "Generate the return again and re-run validation."]

    # Short, actionable steps. The enter-a-value / pick-from-a-list lines are
    # included only when the figure actually has a detail of that kind, so the
    # guidance always matches the details listed above it.
    steps = ["Check the details supplied for this figure in your source data."]
    if len(axes) > 1:
        steps.append("Make sure every detail listed above is filled in.")
    if any(a.get("is_typed") for a in axes):
        steps.append("For details you enter yourself, use the format shown above.")
    if any(not a.get("is_typed") for a in axes):
        steps.append("For details picked from a list, use one of the options shown above.")
    steps.append("Generate the return again and re-run validation.")
    return steps


_HEADLINES = {
    "typed_value_invalid": "One of this figure's details is not written in the required format.",
    "typed_value_unverified": "The value entered for one of this figure's details was rejected.",
    "missing_axes": "Some of the details this figure must carry are missing.",
    "invalid_member": "One of this figure's details uses an option that is not allowed.",
    "unexpected_axes": "This figure carries an extra detail that does not belong to it.",
    "axis_not_in_taxonomy": ("One of the details used here is not defined in this return's "
                             "taxonomy."),
    "concept_not_in_taxonomy": ("This item is not one that takes details in this return's "
                                "taxonomy."),
}

_DEFAULT_HEADLINE = "This figure uses a set of details that is not allowed."


def _headline(evidence: dict) -> str:
    return _HEADLINES.get(evidence.get("diagnosis"), _DEFAULT_HEADLINE)


def build_sections(evidence: dict, llm_text: dict | None = None) -> list[dict]:
    """The explanation as typed, presentation-free sections.

    Section kinds match the formula-error flow so the UI renders both the same
    way: headline / rule / values / points / note.
    """
    axes = _display_axes(evidence)
    sections: list[dict] = [{"kind": "headline", "text": _headline(evidence)}]

    facts: list[dict] = []
    concept = _concept_display(evidence)
    if concept:
        facts.append({"label": "Concept", "value": concept})
    reported = _reported_value_display(evidence)
    if reported:
        facts.append({"label": "Reported value", "value": reported})
    typed_line = _typed_value_line(evidence)
    if typed_line and axes:
        facts.append({"label": f"Value entered for {axes[0]['label']}", "value": typed_line})
    if facts:
        sections.append({"kind": "values", "heading": "What Was Reported", "items": facts})

    if axes:
        sections.append({
            "kind": "values", "heading": "Details This Figure Must Carry",
            "items": [{"label": a["label"], "value": _axis_kind(a)} for a in axes],
        })
        sections.append({
            "kind": "values", "heading": "What Each Detail Must Contain",
            "items": [{"label": a["label"], "value": _axis_requirement(a)} for a in axes],
        })

    member_items, member_note = _reported_members(evidence)
    if member_items:
        sections.append({
            "kind": "values", "heading": "Details Actually Provided", "items": member_items,
        })
    elif member_note:
        # A standalone statement, not a label/value pair — there is no member
        # to put on the right-hand side.
        sections.append({
            "kind": "rule", "heading": "Details Actually Provided", "text": member_note,
        })

    sections.append({
        "kind": "points", "heading": "What Is Wrong",
        "bullets": _llm_points((llm_text or {}).get("why_failed")) or _what_is_wrong_points(evidence),
    })
    sections.append({
        "kind": "points", "heading": "How to Fix",
        "bullets": _llm_points((llm_text or {}).get("how_to_fix")) or _how_to_fix_points(evidence),
    })

    context = (evidence.get("context_id") or "").strip()
    if context:
        # The identifier goes on its own line under the heading, rather than
        # beside a redundant "Context:" label.
        sections.append({"kind": "rule", "heading": "Context Id (for reference)",
                         "text": context, "mono": True})
    return sections


def _llm_points(text) -> list[str]:
    """Split already-grounded LLM prose into short bullets. [] when unusable,
    so the caller falls back to the deterministic points."""
    if not text:
        return []
    raw = [part.strip(" •-\t") for part in str(text).splitlines() if part.strip()]
    if len(raw) == 1:
        raw = [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z(])", raw[0]) if s.strip()]
    points = [p if p.endswith((".", "!", "?")) else p + "." for p in raw if len(p) > 1]
    return points[:6]


def sections_to_text(title: str, sections: list[dict]) -> str:
    """Plain-text serialisation. Headings carry a trailing colon HERE only —
    the section data keeps them bare so the UI can style them as headings
    rather than inheriting punctuation meant for plain text."""
    lines: list[str] = [f"📐 Dimension Error — {title}".rstrip(" —"), ""]
    for section in sections:
        kind = section.get("kind")
        if kind == "headline":
            lines += [f"❌ {section['text']}", ""]
        elif kind == "rule":
            lines += [f"{section['heading']}:", section["text"], ""]
        elif kind == "values":
            lines.append(f"{section['heading']}:")
            for item in section["items"]:
                label = item.get("label", "")
                lines.append(f"• {label}: {item.get('value', '')}" if label
                             else f"• {item.get('value', '')}")
            lines.append("")
        elif kind == "points":
            lines.append(f"{section['heading']}:")
            lines += [f"• {b}" for b in section["bullets"]]
            lines.append("")
        elif kind == "note":
            lines += [section["text"], ""]
    return "\n".join(lines).rstrip()


def _display_title(evidence: dict) -> str:
    """Heading subject: the concept when the validator named one, otherwise the
    dimension it complained about (the typed-content class is raised against a
    context, not against a single fact)."""
    axes = _display_axes(evidence)
    return axes[0]["label"] if axes else "reporting context"


def render_explanation(evidence: dict, llm_text: dict | None = None) -> str:
    """Plain-text form, serialised from build_sections(). No markdown emphasis
    markers: the UI styles the headings itself."""
    title = _concept_display(evidence) or _display_title(evidence)
    return sections_to_text(title, build_sections(evidence, llm_text))


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 4 — LLM payload + orchestration
# ═════════════════════════════════════════════════════════════════════════════

def build_llm_payload(evidence: dict) -> tuple[dict, list[str]] | None:
    """(payload, required_terms) for the grounded phrasing call, or None when
    there is too little established to phrase anything worth saying."""
    if evidence["diagnosis"] in ("no_taxonomy", ""):
        return None

    axes = evidence.get("expected_axes") or ([evidence["focus_axis"]] if evidence.get("focus_axis") else [])
    if not axes:
        return None

    concept_label = evidence["concept_label"] or evidence["concept_id"]
    required_terms = [t for t in [concept_label] if t]
    required_terms += [a["label"] for a in axes if a.get("label")][:3]

    allowed_member_terms = [a["axis_id"] for a in axes]
    for a in axes:
        allowed_member_terms += [m["id"] for m in a.get("allowed_members", [])]

    payload = {
        "what_the_validator_rejected": "the combination of dimensions used on this fact",
        "concept": concept_label,
        # The FACT's own value, from the error file. Distinct from the
        # dimension members below — conflating the two is what produced an
        # explanation claiming nothing was reported while the same error
        # displayed the concept's value.
        "reported_fact_value": evidence.get("reported_fact_value") or None,
        "unit": evidence.get("unit") or None,
        "diagnosis": evidence["diagnosis"],
        "dimensions_required_by_taxonomy": [
            {
                "name": a["label"],
                "kind": "typed" if a["is_typed"] else "explicit",
                "required_value": a.get("required_value"),
                "allowed_members": [m["label"] for m in a.get("allowed_members", [])][:12],
            }
            for a in axes
        ],
        "dimensions_actually_reported": evidence.get("observed_dimensions"),
        "observation_source": evidence.get("observation_source"),
        "missing_dimensions": [
            a["label"] for a in axes if a["axis_id"] in (evidence.get("missing_axes") or [])
        ],
        "invalid_values": evidence.get("invalid_members") or [],
        "typed_value_check": evidence.get("typed_value_check"),
        "dimension_members_are_known": bool(evidence.get("observed_dimensions")),
        "_allowed_member_terms": allowed_member_terms,
        # Internal identifiers are given for disambiguation only; quoting one
        # back exposes XBRL internals instead of the business label.
        "_technical_names": [
            n for n in [evidence.get("concept_id")] + [a["axis_id"] for a in axes]
            if n and n not in (concept_label or "")
        ],
    }
    return payload, required_terms


def explain_dimension_errors(
    errors: list[dict], form_id: str = "", error_file_path: str = "",
) -> list[dict]:
    """Explain a batch of dimension errors. Never raises: any failure in
    evidence assembly or phrasing degrades to the deterministic template for
    that one error and leaves the rest of the batch unaffected."""
    if not errors:
        return []

    settings = error_llm.llm_settings()
    results: list[dict] = []
    for err in errors:
        merged = dict(err)
        try:
            evidence = build_evidence(err, form_id, error_file_path)
        except Exception as exc:
            logger.error("[dimension_error] evidence build failed: %s", exc)
            evidence = {
                "diagnosis": "", "concept_id": err.get("concept", ""),
                "concept_label": "", "context_id": err.get("context", ""),
                "expected_axes": [], "focus_axis": None,
                "observed_dimensions": None, "typed_value_check": None,
                "reported_fact_value": err.get("value", ""),
                "error_class": err.get("error_class", ""),
            }

        llm_text = None
        try:
            built = build_llm_payload(evidence)
            if built and settings.get("enabled"):
                payload, required = built
                llm_text = error_llm.phrase(
                    payload, required,
                    {
                        # Plain, everyday wording is requested explicitly: the
                        # deterministic template these fields replace is written
                        # that way, and prose that slips back into "context",
                        # "dimension" or "typed member" reads as a different
                        # explanation sitting inside the same panel.
                        "why_failed": ("two short sentences in plain, everyday English saying "
                                       "what this figure needed and what was wrong with what "
                                       "was reported. Say 'figure' not 'fact', 'detail' not "
                                       "'dimension', and never say context, axis, member or "
                                       "taxonomy element"),
                        "how_to_fix": ("one short sentence of plain, practical guidance based "
                                       "only on the facts above, using the same everyday "
                                       "wording"),
                    },
                    settings,
                )
        except Exception as exc:
            logger.warning("[dimension_error] phrasing failed: %s", exc)

        sections = build_sections(evidence, llm_text)
        merged["explanation"] = sections_to_text(
            _concept_display(evidence) or _display_title(evidence), sections,
        )
        # Structured form for the UI, so headings/bullets render as real
        # elements instead of being recovered by parsing the string back.
        merged["explanation_sections"] = sections
        merged["_dimension_evidence"] = evidence
        merged["_error_category"] = "dimensional"
        results.append(merged)

    return results
