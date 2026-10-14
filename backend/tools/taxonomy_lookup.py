# taxonomy_lookup.py — per-return taxonomy-metadata JSON resolver for 4000-series
# formula-error explanation.
#
# Flow: form_id -> Json/<form_id>/<*.json> -> {assertion_id: rule, concept_id: concept}
#
# The JSON files are large (return_metadata/structure/concepts/validation_rules/
# unmapped_summary) — this module never hands the whole file to a caller. It loads
# once per return (cached, mtime-checked) and exposes small, focused lookups keyed
# by assertion_id / concept_id so callers pull only the metadata relevant to one
# formula error at a time.
#
# Fails soft everywhere: a missing folder, missing JSON, or malformed JSON returns
# None/{} rather than raising, so formula-error explanation always falls back to
# its existing (pre-taxonomy) behavior when metadata isn't available.

from __future__ import annotations

import json
import logging
import os
import threading

from backend import config, version_config
from backend.tools.return_json_path import flat_return_json_path

logger = logging.getLogger(__name__)

_CACHE_LOCK = threading.Lock()
# (tenant_id, form_id) -> index dict (see get_return_json). tenant_id is
# folded into the key because two APP_VERSION=6.0 tenants can share the same
# form_id with DIFFERENT taxonomy JSON under their own repo root -- a bare
# form_id key would let tenant B's request return tenant A's cached
# taxonomy. Under 5.5, version_config.get_active_tenant_id() is always
# None, so every entry gets the same constant prefix -- byte-for-byte the
# same bucketing as a bare form_id key.
_TAXONOMY_CACHE: dict[tuple[str | None, str], dict] = {}


def _cache_key(form_id: str) -> tuple[str | None, str]:
    return (version_config.get_active_tenant_id(), str(form_id).strip())


def _find_taxonomy_json_path(form_id: str) -> str | None:
    """The JSON file for one return.

    1. Json/<form_id>/<any>.json  - the original per-return folder layout
       (unchanged, tried first for every version).
    2. Json/<form_id>.json        - the flat layout the JSON generator writes.
       6.0 only: 5.5 keeps resolving exactly as before.

    Always the file for THIS form id; never another return's as a fallback.
    """
    folder = os.path.join(config.json_metadata_base_dir(), os.path.basename(str(form_id).strip()))
    if os.path.isdir(folder):
        try:
            names = sorted(n for n in os.listdir(folder) if n.lower().endswith(".json"))
        except OSError as exc:
            logger.warning("[taxonomy_lookup] cannot list %s: %s", folder, exc)
            names = []
        if names:
            return os.path.join(folder, names[0])
    if version_config.IS_V6:
        return flat_return_json_path(form_id)
    return None


def get_return_json(form_id: str) -> dict | None:
    """Load + cache the taxonomy index for one return. None if unavailable.

    Returned dict shape (never the raw JSON — pre-indexed for O(1) lookup):
        {
          "path": str, "mtime": float, "return_code": str,
          "by_assertion_id": {assertion_id: validation_rule_dict, ...},
          "by_concept_id":   {concept_id: concept_dict, ...},
        }
    """
    if not form_id:
        return None
    path = _find_taxonomy_json_path(form_id)
    if not path:
        logger.info("[taxonomy_lookup] no JSON metadata for form_id=%s", form_id)
        return None

    try:
        mtime = os.path.getmtime(path)
    except OSError as exc:
        logger.warning("[taxonomy_lookup] cannot stat %s: %s", path, exc)
        return None

    key = _cache_key(form_id)
    with _CACHE_LOCK:
        cached = _TAXONOMY_CACHE.get(key)
        if cached and cached.get("path") == path and cached.get("mtime") == mtime:
            return cached

        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError) as exc:
            logger.warning("[taxonomy_lookup] failed to load %s: %s", path, exc)
            return None

        if version_config.IS_V6:
            file_code = str((data.get("return_metadata") or {}).get("return_code") or "").strip()
            if file_code and file_code != str(form_id).strip():
                logger.warning(
                    "[taxonomy_lookup] %s declares return_code=%s but was requested for form_id=%s "
                    "- refusing to use another return's metadata", path, file_code, form_id,
                )
                return None

        by_assertion_id = {
            r.get("assertion_id"): r
            for r in data.get("validation_rules", []) or []
            if r.get("assertion_id")
        }
        by_concept_id = {
            c.get("concept_id"): c
            for c in data.get("concepts", []) or []
            if c.get("concept_id")
        }
        # Top-level concept_labels (6.0 files): local name -> label for every
        # concept in the taxonomy package. Only real labels are kept; the
        # generator stores the qualified name where the taxonomy has none.
        from backend.tools.importance_json import usable_label
        labels_by_local = {}
        raw_labels = data.get("concept_labels")
        if isinstance(raw_labels, dict):
            for name, lbl in raw_labels.items():
                local = str(name).split(":")[-1]
                lbl = usable_label(lbl if isinstance(lbl, str) else "", local)
                if lbl:
                    labels_by_local[local] = lbl
        entry = {
            "path": path,
            "mtime": mtime,
            "return_code": (data.get("return_metadata") or {}).get("return_code", ""),
            "by_assertion_id": by_assertion_id,
            "by_concept_id": by_concept_id,
            "labels_by_local": labels_by_local,
        }
        _TAXONOMY_CACHE[key] = entry
        logger.info(
            "[taxonomy_lookup] loaded %s — %d assertions, %d concepts",
            path, len(by_assertion_id), len(by_concept_id),
        )
        return entry


def resolve_concept_label(taxonomy: dict | None, concept_id: str | None) -> str:
    """Readable label for a concept id: the concept's own label when it is a real
    name, else the file's top-level concept_labels, else "" (callers then fall
    back to the taxonomy label linkbase / humanised name). An empty label or one
    that just echoes the technical id is never returned."""
    if not taxonomy or not concept_id:
        return ""
    from backend.tools.importance_json import usable_label
    local = str(concept_id).split(":")[-1]
    concept = taxonomy.get("by_concept_id", {}).get(concept_id)
    label = usable_label((concept or {}).get("label"), local)
    if label:
        return label
    return (taxonomy.get("labels_by_local") or {}).get(local, "")


def rule_variables(rule: dict | None, taxonomy: dict | None = None) -> list[dict]:
    """The variables of one validation rule in the shape the explainers read:
    [{name, concept_id, dimensional_qualification, db_mapping}].

    Two JSON generations exist:
      * older files carry rule["variables"] - returned as is;
      * 6.0 files carry rule["concepts_involved"] = [{concept_id, variable_name,
        role, dimensional_qualification}] - adapted here.

    Adapter notes (6.0):
      - dimensional_qualification holds bare AXIS ids ("qcb:DE000004"), with no
        member, so there is nothing to say about "which member"; entries are kept
        only when they carry axis=member, otherwise the label would gain a
        meaningless "(DE000004)" suffix.
      - the DB mapping lives on the concept (db_mapping: table_name,
        value_column/column_name, filter_value) and is translated to the
        table/column/code_filter keys format_db_location() reads; unmapped
        concepts get none.
    """
    if not rule:
        return []
    variables = rule.get("variables")
    if variables:
        return list(variables)

    by_concept = (taxonomy or {}).get("by_concept_id", {})
    out: list[dict] = []
    seen: set[str] = set()
    for item in rule.get("concepts_involved") or []:
        name = str(item.get("variable_name") or "").strip()
        if not name or name.upper() in seen:
            continue
        seen.add(name.upper())
        concept_id = item.get("concept_id")
        qualification = [q for q in (item.get("dimensional_qualification") or []) if "=" in str(q)]
        mapping = (by_concept.get(concept_id) or {}).get("db_mapping") or {}
        db_mapping: dict = {}
        if mapping.get("status") == "confirmed":
            db_mapping = {
                "status": mapping.get("status"),
                "table": mapping.get("table_name"),
                "column": mapping.get("value_column") or mapping.get("column_name"),
                "code_filter": mapping.get("filter_value"),
                "multiplier": mapping.get("unit_multiplier"),
            }
        out.append({
            "name": name,
            "concept_id": concept_id,
            "dimensional_qualification": qualification,
            "db_mapping": db_mapping,
        })
    return out


def build_variable_metadata_map(taxonomy: dict | None, assertion_id: str) -> dict[str, dict]:
    """Focused per-assertion extraction — the only "relevant JSON subset" a
    formula error ever needs, never the full taxonomy file.

    Returns {variable_name: {concept_id, label, dimensional_qualification,
    table, column, code_filter, multiplier, mapping_status}}. {} if the
    assertion isn't found (e.g. mismatched taxonomy version) or no taxonomy
    is loaded — callers must treat that as "no enrichment available", not
    an error.
    """
    if not taxonomy or not assertion_id:
        return {}
    rule = taxonomy.get("by_assertion_id", {}).get(assertion_id)
    if not rule:
        return {}

    out: dict[str, dict] = {}
    for var in rule_variables(rule, taxonomy):
        name = var.get("name")
        if not name:
            continue
        concept_id = var.get("concept_id")
        db_mapping = var.get("db_mapping") or {}
        out[name] = {
            "concept_id": concept_id,
            "label": resolve_concept_label(taxonomy, concept_id),
            "dimensional_qualification": var.get("dimensional_qualification") or [],
            "table": db_mapping.get("table"),
            "column": db_mapping.get("column"),
            "code_filter": db_mapping.get("code_filter"),
            "multiplier": db_mapping.get("multiplier"),
            "mapping_status": db_mapping.get("status"),
        }
    return out


def format_db_location(meta: dict | None) -> str:
    """Render one variable's resolved DB mapping as a short human string,
    e.g. "CIMS_RAQ_Q_SEC1_PART_C_O.VALUE (code 1052)" or "column F3" or "" if
    nothing is mapped."""
    if not meta:
        return ""
    table  = meta.get("table")
    column = meta.get("column")
    code   = meta.get("code_filter")
    if table and column:
        base = f"{table}.{column}"
    elif column:
        base = f"column {column}"
    elif table:
        base = table
    else:
        return ""
    return f"{base} (code {code})" if code else base
