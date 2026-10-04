"""M-08: verify a file's integrity (via its recorded SHA-256 checksum)
BEFORE ever unpickling it.

``pickle.load()`` does not just deserialize data -- it can execute arbitrary
code embedded in the file. Anyone who can write to one of this app's
retrieval-artifact directories (SQL Agent embeddings, DB Q&A intent index)
gets remote code execution the moment this process next loads it.

Replacing pickle with a safer format (JSON) outright is not done here: these
files are written by an external build tool (see ``build_stamp.json``'s own
``src``/``dest`` fields -- they point at a separate "Embedding maker" tool,
not this repo), so changing the runtime READ format without a corresponding
WRITE-side change in that external tool would simply break every deployment
outright. This module implements the fallback the review itself names
instead: verify an existing checksum before ever handing the bytes to
``pickle.load()``, and refuse (never silently load) on a mismatch.

Lives under ``src/`` (not ``backend/utils/``) so it stays importable the same
self-contained way the rest of this vendored ``src`` package is -- nothing
here imports back into ``backend.*``.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import pickle

logger = logging.getLogger(__name__)

__all__ = [
    "IntegrityError",
    "sha256_of_file",
    "verify_checksum",
    "checksum_from_build_stamp",
    "safe_pickle_load",
]


class IntegrityError(RuntimeError):
    """A file's checksum did not match its recorded stamp -- the file is
    missing its expected content, corrupted, stale, or tampered with. Must
    never be silently unpickled when this is raised."""


def sha256_of_file(path: str) -> str:
    """Stream the file in chunks rather than reading it whole -- these
    artifacts can be tens of MB, and this runs on every cold load."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_checksum(path: str, expected_sha256: str | None) -> None:
    """Raise ``IntegrityError`` if *expected_sha256* is given and does not
    match the actual file at *path*.

    A no-op (verification skipped, not failed) when *expected_sha256* is
    ``None`` -- there is nothing recorded to check against (e.g. this
    artifact predates checksum tracking, as is currently the case for the
    5.5 embeddings set, which has no ``build_stamp.json`` at all). This
    preserves today's behavior for deployments without a stamp, while
    actively protecting any deployment that has one.
    """
    if expected_sha256 is None:
        logger.debug(
            "No recorded checksum for %s -- loading without integrity verification.", path,
        )
        return
    actual = sha256_of_file(path)
    if actual != expected_sha256:
        raise IntegrityError(
            f"Checksum mismatch for {path}: expected {expected_sha256}, got {actual}. "
            f"Refusing to load -- the file may be corrupted, stale, or tampered with. "
            f"Rebuild or restore it from a trusted source before restarting."
        )


def checksum_from_build_stamp(stamp_path: str, filename: str) -> str | None:
    """Look up *filename*'s recorded SHA-256 in a ``build_stamp.json``-shaped
    file (the ``{"checksums": {filename: sha256, ...}}`` convention already
    used by ``backend/sql_agent/embeddings_6.0/build_stamp.json``).

    Returns ``None`` if the stamp file doesn't exist, can't be parsed, or
    doesn't list this filename -- callers pass that straight to
    ``verify_checksum()``, which treats ``None`` as "nothing to verify
    against", not an error.
    """
    if not os.path.exists(stamp_path):
        return None
    try:
        with open(stamp_path, "r", encoding="utf-8") as f:
            stamp = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning(
            "Could not read build stamp %s (%s) -- loading %s without integrity verification.",
            stamp_path, exc, filename,
        )
        return None
    return (stamp.get("checksums") or {}).get(filename)


def safe_pickle_load(path: str, stamp_path: str | None = None):
    """Verify *path* against a build stamp's recorded checksum (if one
    exists and lists this file) before unpickling it.

    *stamp_path* defaults to ``build_stamp.json`` in the same directory as
    *path* -- the existing convention this repo's embeddings sets already
    use. Raises ``IntegrityError`` on a mismatch instead of ever calling
    ``pickle.load()`` on unverified bytes; raises the normal
    ``FileNotFoundError``/``pickle.UnpicklingError`` unchanged for a missing
    or genuinely corrupt file, exactly as a bare ``pickle.load()`` call
    would have before this existed.
    """
    if stamp_path is None:
        stamp_path = os.path.join(os.path.dirname(path), "build_stamp.json")
    expected = checksum_from_build_stamp(stamp_path, os.path.basename(path))
    verify_checksum(path, expected)
    with open(path, "rb") as f:
        return pickle.load(f)
