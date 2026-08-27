"""Regulatory importance for a comparison, read from the return's taxonomy JSON.

WHY THIS EXISTS
---------------
Importance is computed ONCE, during taxonomy-JSON generation, and stored in
each concept's `regulatory_importance` block. This module is the read side:
during a comparison it looks the values up and never re-derives them.

That is the whole point of the split. The previous path
(`xbrl_importance.get_importance_index`) walked the return's taxonomy folder on
every comparison — parsing role schemas, presentation, reference and formula
linkbases — which is slow, depends on the taxonomy being present on the serving
machine, and can silently disagree with what the generated JSON says. Reading
the JSON makes the generated file the single source of truth.

FILE LAYOUT
-----------
    <repo>/JSON/<form_id>.json          e.g. D:\\RepoCore_5.5\\JSON\\2065.json

`form_id` is `Return.Id` from Returns.xml — the same value the comparison flow
already carries as `session["cmp_form_id"]` / `get_form_id_by_name(name)`.
Flat files, no per-form subfolder.

MATCHING
--------
JSON concept ids are prefixed ("in-rbi-rep:Advances"); variance rows carry a
bare local name, sometimes with a dimension suffix ("Advances [OneMonth]").
Rows are matched on the LOCAL NAME only, whole-name — never by stem or
substring, because "Advances" and "AdvancesToIndividualsAgainstSharesMember"
are different concepts and a partial match would silently mis-rank one as the
other. Where two prefixed ids share one local name, neither is matched.

UNMATCHED IS NOT LOW
--------------------
A concept the JSON does not classify comes back `matched=False` with a null
score and an EMPTY tier — never "Low". Low is a real classification meaning
"found, and not important"; unmatched means "we do not know". The UI keeps
them apart so an unclassified concept is never filtered into a tier bucket or
presented as low-priority.
"""

from __future__ import annotations

import logging
import os
import threading

from backend import config

logger = logging.getLogger(__name__)

# What score_concept returns when the JSON has nothing for a concept. Mirrors
# the key set of the live-taxonomy profile so _tag_rows_with_importance needs
# no branch, but every value states "unknown" rather than "unimportant".
_UNMATCHED: dict = {
    "matched": False,
    # None, not 0.0 — 0.0 is a real score meaning "classified, nothing makes it
    # important". Callers that blend must be able to tell the two apart.
    "score": None,
    "tier": "",
    "section": "",
    "section_code": "",
    "section_ordinal": 999_999,
    "circulars": [],
    "blocking_rules": 0,
    "last_amended": None,
    "drivers": [],
}

# xbrl_importance.group_by_importance sorts and compares on the raw score, so
# an unclassified concept needs a numeric stand-in there even though `score`
# stays None everywhere the value itself is reported.
_UNMATCHED_GROUPING_SCORE = 0.0

_CACHE_LOCK = threading.Lock()
# form_id -> (mtime, JsonImportance). Keyed on mtime so a regenerated JSON is
# picked up without a restart.
_CACHE: dict[str, tuple[float, "JsonImportance"]] = {}


def json_path_for(form_id: str) -> str | None:
    """<repo>/JSON/<form_id>.json, or None when it does not exist.

    config.json_metadata_base_dir() resolves to '<root>/Json'; Windows paths
    are case-insensitive so a folder named 'JSON' matches. basename() strips
    any directory component from form_id so a malformed id cannot escape the
    folder.
    """
    if not form_id:
        return None
    fid = os.path.basename(str(form_id).strip())
    if not fid:
        return None
    path = os.path.join(config.json_metadata_base_dir(), f"{fid}.json")
    return path if os.path.isfile(path) else None


class JsonImportance:
    """Lookup over one return's taxonomy JSON.

    Exposes score_concept() with the same shape the live ImportanceIndex used,
    so it is a drop-in for the tagging step.
    """

    def __init__(self, form_id: str, path: str, payload: dict) -> None:
        self.form_id = form_id
        self.path = path

        meta = (payload.get("return_metadata") or {})
        status = (meta.get("regulatory_importance_status") or {})
        self.status = status
        self.available = bool(status.get("available"))
        self.scorer_version = status.get("scorer_version") or ""
        # section_code -> title, held once at file level so each concept needs
        # only the 4-character code.
        self.sections: dict[str, str] = dict(status.get("sections") or {})

        # local name -> regulatory_importance block. Built once per file load.
        by_local: dict[str, dict] = {}
        collisions: set[str] = set()
        for concept in payload.get("concepts") or []:
            cid = concept.get("concept_id") or ""
            if not cid:
                continue
            local = cid.split(":")[-1]
            if local in by_local:
                collisions.add(local)
                continue
            reg = concept.get("regulatory_importance")
            if isinstance(reg, dict):
                by_local[local] = reg
        # Ambiguous names are dropped entirely rather than resolved by guess.
        for name in collisions:
            by_local.pop(name, None)
        self._by_local = by_local
        self._collisions = collisions

        self._cache: dict[str, dict] = {}

    # ── lookup ──────────────────────────────────────────────────────────────
    @staticmethod
    def _local_name(concept: str) -> str:
        """'in-rbi-rep:Advances [OneMonth]' -> 'Advances'.

        Strips the prefix and the dimension suffix compute_variance appends for
        display, leaving the bare concept name the JSON is keyed on.
        """
        name = str(concept or "")
        if " [" in name:
            name = name[: name.index(" [")]
        return name.split(":")[-1].strip()

    def score_concept(self, concept: str) -> dict:
        """Regulatory profile for one concept. Always a dict, never None."""
        local = self._local_name(concept)
        cached = self._cache.get(local)
        if cached is not None:
            return cached

        reg = self._by_local.get(local)
        if not reg or not reg.get("matched"):
            result = dict(_UNMATCHED)
        else:
            code = reg.get("section_code") or ""
            title = self.sections.get(code, "") if code else ""
            result = {
                "matched": True,
                "score": reg.get("score"),
                "tier": reg.get("tier") or "",
                "section_code": code,
                "section": title or "Unclassified",
                # Section codes are the numeric [NNNN] role identifiers, so the
                # code doubles as the ordinal the grouped view sorts on.
                "section_ordinal": int(code) if code.isdigit() else 999_999,
                # Deliberately not persisted per-concept: circulars, rule
                # counts, amendment years and driver prose are validator
                # output, kept out of the generated JSON to hold it small.
                # Empty values keep the downstream row shape stable.
                "circulars": [],
                "blocking_rules": 0,
                "last_amended": None,
                "drivers": [],
            }
        self._cache[local] = result
        return result

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        return (
            f"<JsonImportance form_id={self.form_id} available={self.available} "
            f"concepts={len(self._by_local)} sections={len(self.sections)}>"
        )


def get_importance_from_json(form_id: str | None) -> JsonImportance | None:
    """The importance lookup for a return, or None when unavailable.

    Returns None — never raises — when the file is missing, unreadable, or
    reports `available: false` (a taxonomy with no numbered role sections, so
    nothing in it could be classified). The caller treats None as "importance
    unavailable" and keeps the existing movement-only behaviour.
    """
    if not form_id:
        return None
    path = json_path_for(form_id)
    if not path:
        logger.info(
            "[IMPORTANCE_JSON] no JSON for form_id=%s under %s",
            form_id, config.json_metadata_base_dir(),
        )
        return None

    try:
        mtime = os.path.getmtime(path)
    except OSError as exc:
        logger.warning("[IMPORTANCE_JSON] cannot stat %s: %s", path, exc)
        return None

    with _CACHE_LOCK:
        hit = _CACHE.get(str(form_id))
        if hit is not None and hit[0] == mtime:
            return hit[1]

    try:
        import json

        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except Exception as exc:
        logger.warning("[IMPORTANCE_JSON] cannot read %s: %s", path, exc)
        return None

    index = JsonImportance(str(form_id), path, payload)
    if not index.available:
        logger.info(
            "[IMPORTANCE_JSON] form_id=%s has regulatory_importance_status."
            "available=false (%s) — importance unavailable for this return",
            form_id, index.status.get("reason"),
        )
        return None
    if not index._by_local:
        logger.info("[IMPORTANCE_JSON] form_id=%s carries no scored concepts", form_id)
        return None

    logger.info(
        "[IMPORTANCE_JSON] loaded form_id=%s concepts=%d sections=%d "
        "scorer=%s collisions=%d path=%s",
        form_id, len(index._by_local), len(index.sections),
        index.scorer_version, len(index._collisions), path,
    )
    with _CACHE_LOCK:
        _CACHE[str(form_id)] = (mtime, index)
    return index
