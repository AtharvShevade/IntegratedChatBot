# backend/env_loader.py -- one place that loads the process's .env files.
#
# Before: main.py, dev_server.py and service_server.py each carried the same
# five-line "ENV_FILE or load_dotenv()" block. This module keeps that exact
# behaviour and adds ONE thing: a per-version overlay.
#
#   .env                 shared + machine-specific settings, holds APP_VERSION
#   .env.<APP_VERSION>   (optional) the settings that differ per version -
#                        BACKEND_PORT, LOG_DIR, BASE_REPO_PATH / APP_600_REPO_ROOT,
#                        CORS_ORIGINS, ... Loaded after .env, so it wins over it.
#
# Changing APP_VERSION in .env therefore selects the matching overlay.
#
# Rules (all deliberately conservative):
#   * ENV_FILE set  -> exactly the old behaviour: that one file, override=True,
#                      no overlay. An explicit file stays authoritative.
#   * overlay file missing -> nothing happens (a deployment without overlays
#                      behaves exactly as before).
#   * real process environment variables always beat both files, as they did
#                      for .env alone.
#   * the overlay can never change APP_VERSION itself (.env is the single
#                      switch); a mismatch is reported, not applied.
#   * only KEY NAMES are ever reported - never values - so no secret reaches a
#                      log line.

from __future__ import annotations

import os
from typing import Any

from dotenv import dotenv_values, find_dotenv, load_dotenv

DEFAULT_VERSION = "5.5"

# Filled in by load_env() so the app can log what was loaded once logging exists.
LAST_LOAD: dict[str, Any] = {}


def overlay_path(base_env_path: str, version: str) -> str:
    """Where the per-version overlay for *version* lives (next to the base .env)."""
    return os.path.join(os.path.dirname(os.path.abspath(base_env_path)), f".env.{version}")


def merged_values(base_env_path: str, version: str | None = None) -> dict[str, str]:
    """The base file's values with its version overlay applied, as a plain dict.

    Never touches os.environ. Used by code that needs the file's contents
    without loading them (the SQL agent's bootstrap).
    """
    values = {k: v for k, v in dotenv_values(base_env_path).items() if v is not None}
    ver = (version or values.get("APP_VERSION") or os.environ.get("APP_VERSION") or DEFAULT_VERSION).strip()
    path = overlay_path(base_env_path, ver)
    if os.path.isfile(path):
        for k, v in dotenv_values(path).items():
            if v is not None and k != "APP_VERSION":
                values[k] = v
    return values


def load_env(base_env_path: str | None = None) -> dict[str, Any]:
    """Load .env (or ENV_FILE) and then the version overlay. Returns a summary
    (also kept in LAST_LOAD): base file, version, overlay file and the key names
    the overlay changed. *base_env_path* names the .env explicitly (tests);
    normally it is found by searching upward, as load_dotenv() always did."""
    explicit = os.environ.get("ENV_FILE", "").strip()
    real_env = set(os.environ)          # variables that were already set by the caller

    if explicit:
        load_dotenv(explicit, override=True)
        info = {"base": explicit, "version": os.environ.get("APP_VERSION", DEFAULT_VERSION).strip(),
                "overlay": None, "overridden": [], "note": "ENV_FILE set - no overlay"}
        LAST_LOAD.clear()
        LAST_LOAD.update(info)
        return info

    if base_env_path:
        base = base_env_path
        load_dotenv(base_env_path)
    else:
        base = find_dotenv()
        load_dotenv()
    version = os.environ.get("APP_VERSION", DEFAULT_VERSION).strip() or DEFAULT_VERSION

    overlay = None
    overridden: list[str] = []
    mismatch = False
    if base:
        path = overlay_path(base, version)
        if os.path.isfile(path):
            overlay = path
            for key, value in dotenv_values(path).items():
                if value is None:
                    continue
                if key == "APP_VERSION":
                    mismatch = mismatch or value.strip() != version
                    continue
                if key in real_env:      # a real environment variable wins over any file
                    continue
                if os.environ.get(key) != value:
                    overridden.append(key)
                os.environ[key] = value

    info = {"base": base or None, "version": version, "overlay": overlay,
            "overridden": sorted(overridden), "note": "overlay APP_VERSION ignored" if mismatch else ""}
    LAST_LOAD.clear()
    LAST_LOAD.update(info)
    return info


def describe() -> str:
    """One log line about the last load: key names only, never values."""
    if not LAST_LOAD:
        return "[ENV] not loaded through env_loader"
    ov = LAST_LOAD.get("overlay")
    return (
        f"[ENV] version={LAST_LOAD.get('version')} base={LAST_LOAD.get('base')} "
        f"overlay={ov or 'none'} overlay_keys={LAST_LOAD.get('overridden') or []}"
        + (f" note={LAST_LOAD['note']}" if LAST_LOAD.get("note") else "")
    )
