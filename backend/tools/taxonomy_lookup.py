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

from backend import config

logger = logging.getLogger(__name__)

_CACHE_LOCK = threading.Lock()
_TAXONOMY_CACHE: dict[str, dict] = {}  # form_id -> index dict (see get_return_json)


def _find_taxonomy_json_path(form_id: str) -> str | None:
    """Json/<form_id>/ may contain any single .json file — pick whichever is there."""
    folder = os.path.join(config.json_metadata_base_dir(), os.path.basename(str(form_id).strip()))
    if not os.path.isdir(folder):
        return None
    try:
        names = sorted(n for n in os.listdir(folder) if n.lower().endswith(".json"))
    except OSError as exc:
        logger.warning("[taxonomy_lookup] cannot list %s: %s", folder, exc)
        return None
    return os.path.join(folder, names[0]) if names else None


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

    key = str(form_id).strip()
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
        entry = {
            "path": path,
            "mtime": mtime,
            "return_code": (data.get("return_metadata") or {}).get("return_code", ""),
            "by_assertion_id": by_assertion_id,
            "by_concept_id": by_concept_id,
        }
        _TAXONOMY_CACHE[key] = entry
        logger.info(
            "[taxonomy_lookup] loaded %s — %d assertions, %d concepts",
            path, len(by_assertion_id), len(by_concept_id),
        )
        return entry


def resolve_concept_label(taxonomy: dict | None, concept_id: str | None) -> str:
    if not taxonomy or not concept_id:
        return ""
    concept = taxonomy.get("by_concept_id", {}).get(concept_id)
    return (concept or {}).get("label", "") or ""


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
    for var in rule.get("variables", []) or []:
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
