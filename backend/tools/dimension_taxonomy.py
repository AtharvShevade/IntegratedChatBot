# backend/tools/dimension_taxonomy.py — taxonomy-aware DIMENSION-error explanation.
#
# Builds a client-friendly explanation for xbrldie dimensional-validity errors
# (as parsed by report_lookup.parse_dimensional_html_errors) using ONLY:
#   1. the return's own taxonomy JSON metadata, when present  (Json/<form_id>/*.json)
#   2. the return's own taxonomy definition linkbase(s), located generically
#      from a taxonomy "stem" (e.g. 'mpd03', 'fmrd10') derived at runtime from
#      whichever of these is available — no return code is hardcoded:
#        - the JSON's own entry_point_path, when a JSON extract exists, and/or
#        - filenames/labels already present in the SAME error file (e.g. a
#          FORMULA/TABLE panel referencing '<code>-table.xml' or an
#          assertionLabel like 'FMRD10-Table1-...') — this is what lets the
#          module find the right taxonomy even when Json/<form_id> doesn't
#          exist and the form_id's own DataBase/<form_id>/Taxonomy folder
#          currently holds a different (unrelated, reused) return's files.
#   3. the same error file's OTHER dimension-error entries and other context
#      ids appearing in it (used only to compare against contexts already
#      known to be valid/invalid in this same filing — never a raw instance).
#
# Deliberately does NOT read InstanceDocPath / a raw XBRL instance file —
# failed returns frequently have neither (confirmed empty for real filings),
# and this module must still produce a useful explanation without it.
#
# Handles more than one dimensional error shape:
#   - xbrldie:PrimaryItemDimensionallyInvalidError — cross-referenced against
#     the concept's hypercube (arbitrary number of dimensions; a concept
#     requiring several axes together, e.g. fmrd10's CommodityQuantity, is
#     described by naming all of them, not just the first one found).
#   - xbrldie:IllegalTypedDimensionContentError — needs no taxonomy lookup at
#     all: the validator message itself already names the exact dimension
#     and the invalid value (report_lookup's parser already extracts these
#     into the `dimension`/`typed_dim_value` fields), so this is used directly.
#   - anything else — falls back to the sibling-only or fully generic wording.
#
# Every fact used in the generated explanation is traced back to one of the
# sources above. When the evidence is insufficient to name the specific
# dimension, build_explanation() returns None and the caller (report_lookup's
# explain_dimensional_errors) substitutes a generic-but-accurate fallback —
# this module never guesses at a concept/dimension/member it hasn't found in
# real data.

from __future__ import annotations

import json
import logging
import os
import re
import xml.etree.ElementTree as ET
from functools import lru_cache

from backend import config
from backend.tools.taxonomy_lookup import _find_taxonomy_json_path  # path resolution reuse only

logger = logging.getLogger(__name__)

_XLINK = "{http://www.w3.org/1999/xlink}"
_XBRLDT = "{http://xbrl.org/2005/xbrldt}"
_LINK_NS = {"link": "http://www.xbrl.org/2003/linkbase"}

# Same placeholder-suffix convention report_lookup._decompose_context already
# treats as "duplicate/auto-generated" context id (a run of the letter 'O'
# followed by digits, e.g. '_OOOOOOOO1').
_PLACEHOLDER_SUFFIX_RE = re.compile(r'_OOOOO+\w*$')

_ENTRY_STEM_RE = re.compile(r'^(.*?)-entry', re.IGNORECASE)
_DEFINITION_TAXONOMY_ROOTS = ("DataBase", "conf", "confCims")

# Generic patterns for recovering a taxonomy "stem" straight out of the error
# file itself, when there's no per-form JSON extract to read it from. Both are
# conventions this filer's own taxonomy packages already follow (a table
# linkbase named '<code>-table.xml', and assertion/table labels shaped like
# '<CODE>-Table<N>-...') — no specific return code is baked in here.
_STEM_FROM_FILENAME_RE = re.compile(
    r'\b([a-z][a-z0-9]{2,})-(?:table|definition|formula|entry)(?:-[a-z0-9]+)*\.xml\b',
    re.IGNORECASE,
)
_STEM_FROM_LABEL_RE = re.compile(r'\b([A-Za-z][A-Za-z0-9]{2,})-Table\d+', re.IGNORECASE)


# ─────────────────────────────────────────────────────────────────────────────
# Taxonomy JSON (optional enhancement — reuses taxonomy_lookup's path
# resolver; does not duplicate or modify its caching/indexing logic).
# ─────────────────────────────────────────────────────────────────────────────

def _load_taxonomy_json(form_id: str) -> dict | None:
    if not form_id:
        return None
    try:
        path = _find_taxonomy_json_path(form_id)
    except Exception as exc:
        logger.warning("[dimension_taxonomy] taxonomy path lookup failed for form_id=%s: %s", form_id, exc)
        return None
    if not path:
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:
        logger.warning("[dimension_taxonomy] failed to load %s: %s", path, exc)
        return None
    return data


def _derive_taxonomy_stem_from_json(entry_point_path: str) -> str | None:
    if not entry_point_path:
        return None
    base = os.path.basename(entry_point_path.replace("\\", "/"))
    m = _ENTRY_STEM_RE.match(base)
    stem = m.group(1) if m else os.path.splitext(base)[0]
    return stem or None


def _derive_stems_from_error_file(html_path: str) -> list[str]:
    """Recover candidate taxonomy stems from filenames/labels already present
    in this same error file (see module docstring). Returns [] if the file is
    missing/unreadable — callers must treat that as "no candidates", not an
    error."""
    if not html_path or not os.path.isfile(html_path):
        return []
    try:
        with open(html_path, "r", encoding="utf-8", errors="replace") as fh:
            raw = fh.read()
    except OSError as exc:
        logger.warning("[dimension_taxonomy] cannot read %s: %s", html_path, exc)
        return []

    stems: set[str] = set()
    for m in _STEM_FROM_FILENAME_RE.finditer(raw):
        stems.add(m.group(1).lower())
    for m in _STEM_FROM_LABEL_RE.finditer(raw):
        stems.add(m.group(1).lower())
    return sorted(stems)


@lru_cache(maxsize=256)
def _find_definition_linkbases(active_root: str, stem: str) -> tuple[str, ...]:
    """Search this deployment's known taxonomy roots for '*<stem>*-definition.xml'
    files. Returns every match (sorted, for reproducible ordering) — the caller
    tries each until one actually declares the concept in question, so version
    ambiguity is handled by evidence, not by silently guessing one file."""
    if not stem:
        return ()
    pattern = re.compile(re.escape(stem) + r'.*-definition\.xml$', re.IGNORECASE)
    matches: list[str] = []
    for sub in _DEFINITION_TAXONOMY_ROOTS:
        root_dir = os.path.join(active_root, sub)
        if not os.path.isdir(root_dir):
            continue
        for dirpath, _dirnames, filenames in os.walk(root_dir):
            for fname in filenames:
                if pattern.match(fname):
                    matches.append(os.path.join(dirpath, fname))
    return tuple(sorted(matches))


# ─────────────────────────────────────────────────────────────────────────────
# Parse ONE definition linkbase and, if it declares `concept_local` as a
# primary item of some hypercube, return that hypercube's FULL structure
# (every dimension attached to it, not just one) — no hypercube/table role,
# and no assumption about how many dimensions it has, is hardcoded.
# ─────────────────────────────────────────────────────────────────────────────

def _load_hypercube_for_concept(xml_path: str, concept_local: str) -> dict | None:
    try:
        root = ET.parse(xml_path).getroot()
    except (ET.ParseError, OSError) as exc:
        logger.warning("[dimension_taxonomy] cannot parse %s: %s", xml_path, exc)
        return None

    for link in root.findall("link:definitionLink", _LINK_NS):
        locs: dict[str, str] = {}
        for loc in link.findall("link:loc", _LINK_NS):
            label = loc.get(f"{_XLINK}label")
            title = loc.get(f"{_XLINK}title")
            if label:
                locs[label] = title or ""

        if concept_local not in locs.values():
            continue  # this extended link doesn't even mention the concept

        arcs = []
        for arc in link.findall("link:definitionArc", _LINK_NS):
            arcs.append({
                "arcrole": arc.get(f"{_XLINK}arcrole") or "",
                "from": locs.get(arc.get(f"{_XLINK}from") or ""),
                "to": locs.get(arc.get(f"{_XLINK}to") or ""),
                "closed": arc.get(f"{_XBRLDT}closed"),
            })

        all_arc = next((a for a in arcs if a["arcrole"].endswith("/all")), None)
        if not all_arc:
            continue

        domain_member_arcs = [a for a in arcs if a["arcrole"].endswith("/domain-member")]
        dimension_domain_arcs = [a for a in arcs if a["arcrole"].endswith("/dimension-domain")]
        hypercube_dim_arcs = [a for a in arcs if a["arcrole"].endswith("/hypercube-dimension")]

        lineitems_arc = next((a for a in domain_member_arcs if a["from"] == all_arc["from"]), None)
        lineitems_id = lineitems_arc["to"] if lineitems_arc else None
        primary_items = sorted({
            a["to"] for a in domain_member_arcs if a["from"] == lineitems_id
        }) if lineitems_id else []

        if concept_local not in primary_items:
            continue  # concept appears in this link, but not as a primary item of THIS hypercube

        # A hypercube can have any number of dimensions (fmrd10's
        # CommodityQuantity has three, mpd03's daily CRR concepts have one) —
        # collect all of them, in declaration order.
        dimensions: dict[str, dict] = {}
        for hd in sorted(hypercube_dim_arcs, key=lambda a: a.get("order") or ""):
            dim_id = hd["to"]
            if not dim_id or dim_id in dimensions:
                continue
            dd = next((a for a in dimension_domain_arcs if a["from"] == dim_id), None)
            domain_id = dd["to"] if dd else None
            members = sorted({
                a["to"] for a in domain_member_arcs if a["from"] == domain_id
            }) if domain_id else []
            dimensions[dim_id] = {"domain": domain_id, "members": members}

        return {
            "source_file": xml_path,
            "role": link.get(f"{_XLINK}role") or "",
            "hypercube": all_arc["to"],
            "closed": all_arc.get("closed") == "true",
            "primary_items": primary_items,
            "dimensions": dimensions,
        }

    return None


def _prefer_current_form_paths(paths: tuple[str, ...], active_root: str, form_id: str) -> list[str]:
    """Reorder candidate definition-linkbase paths so the CURRENT return's own
    'DataBase/<form_id>/...' copy is tried before any other match — taxonomy
    folders get reused/repurposed across returns over time (see module
    docstring), and the same stem can legitimately match several different
    returns' files. Without this, plain alphabetical sort can silently pick a
    different return's (possibly older-version) taxonomy purely because its
    form_id sorts first, even when the current return's own file exists and
    declares the same concept. Falls back to the given order unchanged when
    form_id is empty or nothing matches it — no fallback behavior is removed,
    only reordered."""
    if not form_id:
        return list(paths)
    form_prefix = os.path.normcase(os.path.join(active_root, "DataBase", str(form_id)) + os.sep)
    preferred = [p for p in paths if os.path.normcase(p).startswith(form_prefix)]
    if not preferred:
        return list(paths)
    others = [p for p in paths if p not in preferred]
    return preferred + others


def _find_hypercube_for_concept(stems: list[str], concept_local: str, form_id: str = "") -> dict | None:
    active_root = config._active_root()
    tried: set[str] = set()
    for stem in stems:
        if not stem or stem in tried:
            continue
        tried.add(stem)
        candidates = _prefer_current_form_paths(
            _find_definition_linkbases(active_root, stem), active_root, form_id,
        )
        for def_path in candidates:
            hc = _load_hypercube_for_concept(def_path, concept_local)
            if hc:
                return hc
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Cross-reference the hypercube's table role against the JSON's own axes list
# (structure.axes), which reflects the EXACT entry point this filing actually
# used. Matched by the role URI's trailing path segment only (e.g.
# '.../mpd03-role-n/MPD03-Table2' vs '.../mpd03-role/MPD03-Table2' both end in
# 'MPD03-Table2') so version-prefix differences in the role URI don't block
# the match — no table/axis name is hardcoded.
# ─────────────────────────────────────────────────────────────────────────────

def _find_typed_axis_hint(taxonomy_json: dict, hypercube_role: str) -> dict | None:
    if not hypercube_role:
        return None
    role_tail = hypercube_role.rstrip("/").rsplit("/", 1)[-1].lower()
    axes = ((taxonomy_json or {}).get("structure") or {}).get("axes") or []
    for axis in axes:
        for table_role in axis.get("tables") or []:
            if table_role.rstrip("/").rsplit("/", 1)[-1].lower() == role_tail:
                return axis
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Pull sibling context ids straight out of the SAME error file (no raw
# instance XML needed). A "sibling" is any other context id sharing this
# context's prefix that is NOT itself known to be invalid — i.e. it neither
# carries the placeholder-suffix pattern NOR is the context of another error
# already parsed from this same file. That second check matters: in some
# filings both a placeholder-suffixed context AND its non-suffixed base are
# independently flagged as invalid for the same concept, so "lacks the
# placeholder suffix" alone is not sufficient proof a context is valid.
# ─────────────────────────────────────────────────────────────────────────────

def _find_sibling_contexts(
    html_path: str, context_id: str, known_invalid_contexts: frozenset[str] = frozenset(),
) -> list[str]:
    if not html_path or not context_id or not os.path.isfile(html_path):
        return []

    # Only derive a prefix when the context carries the recognized
    # placeholder-suffix marker — stripping an arbitrary trailing
    # underscore-segment otherwise risks cutting off a real dimension
    # member (not a placeholder) and matching unrelated contexts that
    # happen to share a shorter, coarser prefix. No marker -> no safe way
    # to derive a prefix, so return no siblings rather than guess one.
    m = _PLACEHOLDER_SUFFIX_RE.search(context_id)
    if not m:
        return []
    prefix = context_id[:m.start()]
    if not prefix:
        return []

    try:
        with open(html_path, "r", encoding="utf-8", errors="replace") as fh:
            raw = fh.read()
    except OSError as exc:
        logger.warning("[dimension_taxonomy] cannot read %s: %s", html_path, exc)
        return []

    pattern = re.compile(re.escape(prefix) + r'_[A-Za-z0-9]+')
    found = sorted(set(pattern.findall(raw)))
    return [
        c for c in found
        if c != context_id
        and not _PLACEHOLDER_SUFFIX_RE.search(c)
        and c not in known_invalid_contexts
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Humanize a taxonomy dimension/axis local name into a short, client-friendly
# phrase. Purely mechanical (CamelCase split + strip the generic
# 'Axis'/'Dimension' suffix) — no dimension name is hardcoded.
# ─────────────────────────────────────────────────────────────────────────────

def _humanize_dimension_name(local_name: str) -> str:
    if not local_name:
        return ""
    name = local_name.split(":")[-1]
    name = re.sub(r'(Axis|Dimension)$', '', name)
    words = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', name).strip()
    return words.lower()


def _sibling_typed_value(context_id: str) -> str:
    """Same convention used for the reported context's own 'suffix' — the
    last underscore-separated token is the part that actually varies between
    sibling contexts for a single-dimension case, so it's the best available
    stand-in for 'what value did this dimension actually take' when there is
    no enumerable taxonomy member list to compare against."""
    return context_id.rsplit("_", 1)[-1] if "_" in context_id else context_id


def _humanize_member_name(local_name: str) -> str:
    """Same mechanical CamelCase-split idea as _humanize_dimension_name, but
    for a taxonomy MEMBER local name — strips the generic 'Member'/'Domain'
    suffix instead of 'Axis'/'Dimension'. No member name is hardcoded."""
    if not local_name:
        return ""
    name = local_name.split(":")[-1]
    name = re.sub(r'(Member|Domain)$', '', name)
    words = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', name).strip()
    return words or name


def _format_examples_list(values: list[str], limit: int = 5) -> str:
    """Comma-joined preview of up to *limit* distinct example values, with
    the total count appended once there are more than shown — deliberately
    never dumps the full sibling/member list into the explanation text."""
    if not values:
        return ""
    shown = values[:limit]
    joined = ", ".join(f"`{v}`" for v in shown)
    if len(values) > limit:
        joined += f" (and {len(values) - limit} more — {len(values)} total)"
    return joined


def _describe_dimension_values(dim_id: str, info: dict) -> str:
    """One line describing a single hypercube dimension's valid values, for
    use inside a multi-dimension explanation's 'Valid values/examples'
    section — reuses the exact same evidence (members list) already
    resolved on the hypercube, never a separate lookup."""
    name = _humanize_dimension_name(dim_id)
    members = info.get("members") or []
    if members:
        return f"{name}: " + _format_examples_list([_humanize_member_name(m) for m in members], limit=8)
    return f"{name}: typed dimension — the taxonomy defines no fixed member list for it"


def _build_checklist(dim_phrase: str, kind: str, has_examples: bool = False) -> str:
    """Numbered, actionable 'what should be checked' steps — never a single
    generic 'check the context' sentence. *kind* is one of 'multi', 'typed',
    'enumerated', 'unknown'; *dim_phrase* is whatever was actually resolved
    for THIS error (never a hardcoded dimension name)."""
    dim_ref = dim_phrase if dim_phrase else "dimension"
    steps: list[str] = ["Find the context assigned to this fact."]
    if kind == "multi":
        steps.append(f"Check its reported values for each of the following dimensions: {dim_phrase}.")
        steps.append("Verify each dimension member is one the taxonomy allows for this concept.")
        steps.append("Correct whichever dimension(s) are missing or invalid, then regenerate the return.")
    elif kind == "typed":
        steps.append(f"Check its {dim_ref} value.")
        if has_examples:
            steps.append(f"Compare it with the valid {dim_ref} values used by other facts in the same filing.")
        steps.append(f"Verify the underlying data this {dim_ref} value is meant to represent.")
        steps.append("Correct the source data or context value and regenerate the return.")
    elif kind == "enumerated":
        steps.append(f"Check its {dim_ref} member against the taxonomy's allowed members below.")
        steps.append("Select the member from that list that correctly reflects this fact.")
        steps.append("Correct the context value and regenerate the return.")
    else:  # unknown — no dimension could be named at all
        steps.append("Compare it against other valid contexts used for the same or related concepts in this filing.")
        steps.append("Confirm with the taxonomy which dimension(s) apply to this concept.")
        steps.append(
            "Correct the context so it provides a valid combination of dimensions and "
            "members, then regenerate the return."
        )
    return "\n".join(f"{i + 1}. {s}" for i, s in enumerate(steps))


def _join_natural(phrases: list[str]) -> str:
    phrases = [p for p in phrases if p]
    if not phrases:
        return ""
    if len(phrases) == 1:
        return phrases[0]
    if len(phrases) == 2:
        return f"{phrases[0]} and {phrases[1]}"
    return ", ".join(phrases[:-1]) + f", and {phrases[-1]}"


# ─────────────────────────────────────────────────────────────────────────────
# Template rendering + generic fallback.
# ─────────────────────────────────────────────────────────────────────────────

_NOT_DETERMINABLE = "Cannot be determined from the available data."


def _render_structured_template(
    concept: str, dimension: str, reported: str, dimension_type: str,
    what_is_wrong: str, valid_values: str, what_to_check: str, expected_value: str,
) -> str:
    """Renders the evidence-first, section-wise markdown structure used for
    EVERY DIMENSION error, regardless of which builder below produced the
    content — one consistent shape so the frontend's generic
    '**Label:** content' section parser renders all of them the same way.
    This function only assembles already-decided text; it never fills in a
    missing piece with a guess — every caller is responsible for passing
    _NOT_DETERMINABLE explicitly when evidence doesn't support a field."""
    return (
        "**Dimension Error:** The reported fact has an invalid dimension/context combination.\n\n"
        f"**Concept:** {concept}\n\n"
        f"**Dimension:** {dimension}\n\n"
        f"**Reported value/member:** `{reported}`\n\n"
        f"**Dimension type:** {dimension_type}\n\n"
        f"**What is wrong:** {what_is_wrong}\n\n"
        f"**Valid values/examples:** {valid_values}\n\n"
        "**Result:** INVALID\n\n"
        f"**What should be checked:**\n{what_to_check}\n\n"
        f"**Exact expected value:** {expected_value}"
    )


def _generic_fallback_explanation(err: dict) -> str:
    concept = err.get("concept") or "Not identified by the validator message for this error type."
    reported = err.get("value", "") or err.get("context", "")
    return _render_structured_template(
        concept=concept,
        dimension=_NOT_DETERMINABLE,
        reported=reported,
        dimension_type=_NOT_DETERMINABLE,
        what_is_wrong=(
            "The context used for this fact has an invalid combination of dimensions and "
            "members, as reported by the taxonomy validator. The available filing and "
            "taxonomy data do not provide enough detail to confirm which specific "
            "dimension is affected."
        ),
        valid_values=_NOT_DETERMINABLE,
        what_to_check=_build_checklist("", "unknown"),
        expected_value=_NOT_DETERMINABLE,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Error-class-specific builders.
# ─────────────────────────────────────────────────────────────────────────────

def _build_typed_content_explanation(
    err: dict, error_file_path: str = "", known_invalid_contexts: frozenset[str] = frozenset(),
) -> tuple[str | None, dict]:
    """xbrldie:IllegalTypedDimensionContentError — the validator message
    itself already names the exact dimension and the invalid value (parsed
    into err['dimension'] / err['typed_dim_value'] by report_lookup's
    existing parser). No taxonomy file lookup is needed for the dimension
    name itself; the same-filing sibling-context check below is the same
    evidence source _build_primary_item_explanation uses, applied here too
    since it's available for any dimension error, not just this class."""
    dimension = (err.get("dimension") or "").strip()
    typed_value = (err.get("typed_dim_value") or "").strip()
    context = err.get("context", "")

    evidence = {
        "error_class": err.get("error_class"),
        "source": "validator_message_direct",
        "dimension": dimension,
        "typed_dim_value": typed_value,
    }

    if not dimension:
        return None, evidence

    dim_phrase = _humanize_dimension_name(dimension)
    evidence["dimension_phrase"] = dim_phrase

    siblings = _find_sibling_contexts(error_file_path, context, known_invalid_contexts) if context else []
    evidence["sibling_contexts_found"] = len(siblings)

    reported_value = typed_value or err.get("value", "")

    what_is_wrong = (
        f"The taxonomy requires the {dim_phrase} dimension on this fact's context to "
        f"contain a value in a specific format defined by the taxonomy."
    )
    if typed_value:
        what_is_wrong += f" The value currently used (`{typed_value}`) does not match that required format."
    else:
        what_is_wrong += " The value currently used does not match that required format."

    if siblings:
        examples = sorted({_sibling_typed_value(s) for s in siblings})
        evidence["typed_value_examples"] = examples
        valid_values = _format_examples_list(examples)
        what_is_wrong += (
            f" Other facts in this same filing use a properly formed {dim_phrase} value, "
            f"for example: {valid_values}."
        )
    else:
        valid_values = (
            f"No enumerable taxonomy member list applies to this dimension (it is typed by "
            f"definition for this error type), and no other valid example was found in this "
            f"filing to compare against."
        )

    explanation = _render_structured_template(
        concept=err.get("concept") or "Not identified by the validator message for this error type.",
        dimension=dim_phrase,
        reported=reported_value,
        dimension_type="Typed dimension",
        what_is_wrong=what_is_wrong,
        valid_values=valid_values,
        what_to_check=_build_checklist(dim_phrase, "typed", has_examples=bool(siblings)),
        expected_value=_NOT_DETERMINABLE,
    )
    return explanation, evidence


def _build_primary_item_explanation(
    err: dict, form_id: str, error_file_path: str, known_invalid_contexts: frozenset[str],
) -> tuple[str | None, dict]:
    """xbrldie:PrimaryItemDimensionallyInvalidError (and unrecognized classes
    with concept+context present) — cross-referenced against the concept's
    hypercube in its own taxonomy's definition linkbase, wherever that can be
    found (see module docstring for how the taxonomy stem is derived)."""
    concept = (err.get("concept") or "").strip()
    context = (err.get("context") or "").strip()
    concept_local = concept.split(":")[-1] if concept else ""

    evidence: dict = {
        "form_id": form_id,
        "concept": concept,
        "context": context,
        "taxonomy_json_found": False,
        "hypercube_found": False,
        "axis_hint_found": False,
        "sibling_contexts_found": 0,
    }

    if not concept_local or not context:
        return None, evidence

    siblings = _find_sibling_contexts(error_file_path, context, known_invalid_contexts)
    evidence["sibling_contexts_found"] = len(siblings)

    taxonomy_json = _load_taxonomy_json(form_id)
    stems: list[str] = []
    if taxonomy_json:
        evidence["taxonomy_json_found"] = True
        entry_point = (taxonomy_json.get("return_metadata") or {}).get("entry_point_path", "")
        json_stem = _derive_taxonomy_stem_from_json(entry_point)
        if json_stem:
            stems.append(json_stem)
    stems.extend(_derive_stems_from_error_file(error_file_path))
    evidence["taxonomy_stems_tried"] = stems

    hypercube = None
    axis_hint = None
    if stems:
        try:
            hypercube = _find_hypercube_for_concept(stems, concept_local, form_id)
        except Exception as exc:
            logger.warning("[dimension_taxonomy] hypercube lookup failed: %s", exc)
            hypercube = None
        if hypercube:
            evidence["hypercube_found"] = True
            evidence["hypercube_source_file"] = hypercube["source_file"]
            evidence["hypercube_closed"] = hypercube["closed"]
            evidence["hypercube_dimensions"] = list(hypercube["dimensions"].keys())
            if taxonomy_json:
                axis_hint = _find_typed_axis_hint(taxonomy_json, hypercube["role"])
                if axis_hint:
                    evidence["axis_hint_found"] = True
                    evidence["axis_id"] = axis_hint.get("axis_id")
                    evidence["axis_is_typed"] = axis_hint.get("is_typed")

    # A hypercube can require several dimensions together. When the JSON
    # confirms the table's CURRENT single typed/explicit axis identity (the
    # common case — one dimension per table), trust that name over the XML's
    # (possibly older-version) one. Otherwise name every dimension the XML
    # found on this hypercube, since any of them being wrong/missing is
    # exactly what "invalid combination of dimensions" means.
    if axis_hint and hypercube and len(hypercube.get("dimensions") or {}) <= 1:
        dim_names = [_humanize_dimension_name(axis_hint.get("axis_id", ""))]
    elif hypercube and hypercube.get("dimensions"):
        dim_names = [_humanize_dimension_name(d) for d in hypercube["dimensions"]]
    else:
        dim_names = []
    dim_names = [d for d in dim_names if d]
    dim_phrase = _join_natural(dim_names)
    evidence["dimension_phrase"] = dim_phrase

    if not dim_phrase and not siblings:
        return None, evidence  # nothing provable -- let caller use the generic fallback

    suffix = context.rsplit("_", 1)[-1] if "_" in context else context
    multi = len(dim_names) > 1

    # Typed dimensions (e.g. a date-of-transaction axis) have no enumerable
    # taxonomy member list at all — 'members: []' is the taxonomy's own
    # answer, not missing data — so they must never be explained the same
    # way as an explicit/enumerated dimension (which lists allowed members).
    # Prefer the JSON axis_hint's own is_typed flag when available; otherwise
    # fall back to the XML hypercube's own single-dimension entry having
    # neither a domain nor any members, which is the same signal at the
    # taxonomy-XML level.
    only_dim_info = None
    if hypercube and not multi and hypercube.get("dimensions"):
        only_dim_info = next(iter(hypercube["dimensions"].values()), None)
    is_typed_dimension = False
    if axis_hint is not None:
        is_typed_dimension = bool(axis_hint.get("is_typed"))
    elif only_dim_info is not None:
        is_typed_dimension = not only_dim_info.get("domain") and not only_dim_info.get("members")
    evidence["dimension_is_typed"] = is_typed_dimension

    expected_value = _NOT_DETERMINABLE

    if dim_phrase:
        if multi:
            dimension_type = "Multiple dimensions (required together)"
            valid_values = "; ".join(
                _describe_dimension_values(dim_id, info)
                for dim_id, info in (hypercube.get("dimensions") or {}).items()
            ) or _NOT_DETERMINABLE
            what_is_wrong = (
                f"The taxonomy requires this fact to be reported with a valid combination "
                f"of the following dimensions together: {dim_phrase}. The context used for "
                f"this fact does not provide a valid combination of these dimensions as "
                f"defined by the taxonomy."
            )
            what_to_check = _build_checklist(dim_phrase, "multi")
            # A valid combination across several dimensions can't be proven
            # from one dimension's sibling members in isolation.
        elif is_typed_dimension and siblings:
            # No enumerable member list exists for a typed dimension, but the
            # SAME filing's other valid facts show real examples of the value
            # pattern this dimension expects — surface those instead of the
            # generic "does not match" sentence, without ever claiming one of
            # them IS the exact value this fact should have used.
            examples = sorted({_sibling_typed_value(s) for s in siblings})
            evidence["typed_value_examples"] = examples
            valid_values = _format_examples_list(examples)
            dimension_type = "Typed dimension"
            what_is_wrong = (
                f"The taxonomy requires this fact to be reported with a valid {dim_phrase} "
                f"dimension. This dimension does not use a fixed list of taxonomy members "
                f"(it is a typed dimension), so its valid values cannot be listed directly "
                f"from the taxonomy. The context used for this fact contains `{suffix}`, "
                f"which does not match the value pattern used by other facts in this same "
                f"filing for the same dimension: {valid_values}."
            )
            what_to_check = _build_checklist(dim_phrase, "typed", has_examples=True)
        elif is_typed_dimension:
            dimension_type = "Typed dimension"
            valid_values = (
                "No enumerable taxonomy member list applies to this dimension (it is "
                "typed), and no other valid fact in this filing was found to confirm the "
                "expected value format."
            )
            what_is_wrong = (
                f"The taxonomy requires this fact to be reported with a valid {dim_phrase} "
                f"dimension. This dimension does not use a fixed list of taxonomy members "
                f"(it is a typed dimension), and no other valid fact in this filing was "
                f"found to confirm the expected value format. The context used for this "
                f"fact contains `{suffix}`, which does not match the valid dimension value "
                f"identified from the available taxonomy and filing data."
            )
            what_to_check = _build_checklist(dim_phrase, "typed", has_examples=False)
        else:
            dimension_type = "Enumerated dimension"
            members = (only_dim_info or {}).get("members") or []
            member_names = [_humanize_member_name(m) for m in members]
            valid_values = _format_examples_list(member_names, limit=8) if member_names else _NOT_DETERMINABLE
            what_is_wrong = (
                f"The taxonomy requires this fact to be reported with a valid {dim_phrase} "
                f"dimension. The context used for this fact contains `{suffix}`, which does "
                f"not match the valid dimension values identified from the available "
                f"taxonomy and filing data."
            )
            what_to_check = _build_checklist(dim_phrase, "enumerated")
            # The one case where a single exact value CAN be proven: the
            # taxonomy allows exactly one member for this dimension, so
            # there is no ambiguity about what it should have been.
            if len(members) == 1:
                expected_value = f"`{member_names[0]}` — the only member the taxonomy allows for this dimension."
            if siblings:
                what_is_wrong += (
                    f" Other facts in this same filing use a properly formed context for "
                    f"this same dimension."
                )
    else:
        dimension_type = _NOT_DETERMINABLE
        valid_values = _format_examples_list(siblings) if siblings else _NOT_DETERMINABLE
        what_is_wrong = (
            f"The context used for this fact (`{context}`) does not follow the same "
            f"pattern as other valid contexts found in this same filing."
        )
        what_to_check = _build_checklist("", "unknown")

    explanation = _render_structured_template(
        concept=concept,
        dimension=dim_phrase if dim_phrase else _NOT_DETERMINABLE,
        reported=suffix,
        dimension_type=dimension_type,
        what_is_wrong=what_is_wrong,
        valid_values=valid_values,
        what_to_check=what_to_check,
        expected_value=expected_value,
    )
    return explanation, evidence


def build_explanation(
    err: dict, form_id: str, error_file_path: str, known_invalid_contexts: frozenset[str] = frozenset(),
) -> tuple[str | None, dict]:
    """Returns (explanation_or_None, evidence). explanation is None when no
    usable evidence was found at all — caller must use the generic fallback
    in that case, never invent a specific-sounding explanation.

    Routes by error_class: IllegalTypedDimensionContentError is handled
    directly from the validator's own message fields (no taxonomy lookup
    needed); everything else (chiefly PrimaryItemDimensionallyInvalidError)
    goes through the hypercube cross-reference path.
    """
    error_class = err.get("error_class", "") or ""
    if "IllegalTypedDimensionContentError" in error_class:
        return _build_typed_content_explanation(err, error_file_path, known_invalid_contexts)
    return _build_primary_item_explanation(err, form_id, error_file_path, known_invalid_contexts)


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point used by report_lookup.explain_dimensional_errors.
# ─────────────────────────────────────────────────────────────────────────────

def explain_dimensional_errors_taxonomy_aware(
    errors: list[dict], form_id: str = "", error_file_path: str = "",
) -> list[dict]:
    if not errors:
        return errors

    # Contexts already known (from this same batch) to be invalid — used to
    # stop a sibling lookup from mistaking one broken context for proof
    # another is valid, just because it lacks the placeholder suffix.
    known_invalid_contexts = frozenset(
        e.get("context", "") for e in errors if e.get("context")
    )

    results: list[dict] = []
    for err in errors:
        try:
            explanation, evidence = build_explanation(
                err, form_id, error_file_path, known_invalid_contexts,
            )
        except Exception as exc:
            logger.warning("[dimension_taxonomy] build_explanation failed: %s", exc)
            explanation, evidence = None, {"error": str(exc)}

        merged = dict(err)
        merged["explanation"] = explanation or _generic_fallback_explanation(err)
        merged["_dimension_evidence"] = evidence
        results.append(merged)

    return results
