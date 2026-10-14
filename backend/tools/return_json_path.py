# backend/tools/return_json_path.py
#
# One place that answers "which JSON file belongs to this return?" for the flat
# layout the JSON generator writes:
#
#     <repo root>/Json/<form_id>.json        (6.0: <APP_600_REPO_ROOT>/<TenantId>/Json/)
#
# Used by importance_json (instance comparison) and taxonomy_lookup (error
# explanation) so the two cannot drift apart again.
#
# Rules:
#   * the file is chosen by the EXACT form id only - no "closest" or "any other
#     return" fallback, so one return's metadata can never be applied to another;
#   * the id is reduced to a bare filename first, so a malformed id cannot walk
#     out of the folder;
#   * the folder name is matched case-insensitively ("Json" in code, "JSON" on
#     disk) so the lookup does not depend on the filesystem's case rules;
#   * the base directory still comes from config.json_metadata_base_dir(), which
#     follows the active (tenant-scoped) repo root - nothing here is hardcoded.

from __future__ import annotations

import logging
import os

from backend import config

logger = logging.getLogger(__name__)

__all__ = ["flat_return_json_path"]


def _existing_dir(path: str) -> str | None:
    """*path* if it is a directory, else a case-insensitive sibling match."""
    if os.path.isdir(path):
        return path
    parent, name = os.path.split(path)
    try:
        for entry in os.listdir(parent):
            if entry.lower() == name.lower() and os.path.isdir(os.path.join(parent, entry)):
                return os.path.join(parent, entry)
    except OSError:
        pass
    return None


def flat_return_json_path(form_id: str | None) -> str | None:
    """Absolute path of ``<json dir>/<form_id>.json`` for the active repo root,
    or None when the id is blank or the file does not exist."""
    if not form_id:
        return None
    fid = os.path.basename(str(form_id).strip())
    if not fid:
        return None
    base = _existing_dir(config.json_metadata_base_dir())
    if base is None:
        return None
    path = os.path.join(base, f"{fid}.json")
    return path if os.path.isfile(path) else None
