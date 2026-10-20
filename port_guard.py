"""
port_guard.py -- fail fast when BACKEND_PORT and web.config disagree.

The frontend reaches this backend through the IIS reverse proxy rule in the
web.config that ships with the built frontend. That rule names the port IIS
forwards to; BACKEND_PORT in .env names the port uvicorn opens. They are two
files read by two different programs, with nothing connecting them -- set one
and forget the other and every request through IIS 502s while the backend
itself looks perfectly healthy.

This check runs before uvicorn binds and refuses to start on a mismatch, so the
failure shows up as one readable line at startup instead of as a dead site.

WHICH web.config is checked (first one that applies):
  1. WEB_CONFIG_PATH in .env -- the web.config inside the IIS site folder the
     built frontend was deployed to. This is the file IIS really reads, and the
     one to use on a server (where frontend/dist is not kept in the project).
  2. frontend/dist/web.config -- a frontend built on this machine (npm run
     build writes the port of the selected APP_VERSION into it).
  3. Neither -> nothing is checked. frontend/public/web.config is NEVER checked:
     it is only the template the build starts from, and APP_VERSION does not
     change it.

A missing or unparseable web.config is NOT an error: the file is part of the
frontend deployment and a backend-only host legitimately has no copy of it. A
WEB_CONFIG_PATH that does not exist prints a warning and skips the check.
Set SKIP_PORT_CHECK=1 to bypass the check entirely.
"""

from __future__ import annotations

import os
import re
import sys
import xml.etree.ElementTree as ET

# Relative to the repo root: a frontend built on this machine. public/web.config is
# deliberately absent - it is the build's source template, not a deployed file.
_LOCAL_DIST_WEB_CONFIG = os.path.join("frontend", "dist", "web.config")


def _rewrite_port(path: str) -> int | None:
    """Port from the reverse-proxy rewrite rule in one web.config, or None."""
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        return None

    for action in root.iter("action"):
        if (action.get("type") or "").lower() != "rewrite":
            continue
        match = re.search(r"^https?://[^/:]+:(\d+)", action.get("url") or "")
        if match:
            return int(match.group(1))
    return None


def _web_config_to_check(root_dir: str) -> tuple[str, str] | None:
    """(label, absolute path) of the web.config to compare, or None."""
    configured = os.environ.get("WEB_CONFIG_PATH", "").strip().strip('"')
    if configured:
        path = configured if os.path.isabs(configured) else os.path.join(root_dir, configured)
        if os.path.isfile(path):
            return "WEB_CONFIG_PATH", path
        print(
            f"[port_guard] WEB_CONFIG_PATH={configured} does not exist - port check skipped.",
            file=sys.stderr,
        )
        return None
    local = os.path.join(root_dir, _LOCAL_DIST_WEB_CONFIG)
    if os.path.isfile(local):
        return _LOCAL_DIST_WEB_CONFIG, local
    return None


def assert_port_matches_web_config(backend_port: int, root_dir: str) -> None:
    """Exit with a diagnostic if the deployed web.config forwards to a different port."""
    if os.environ.get("SKIP_PORT_CHECK", "").strip() in ("1", "true", "True"):
        return

    target = _web_config_to_check(root_dir)
    if target is None:
        return
    label, path = target

    port = _rewrite_port(path)
    if port is None or port == backend_port:
        return

    print(
        f"\n[PORT MISMATCH] BACKEND_PORT={backend_port}, but IIS forwards elsewhere:",
        file=sys.stderr,
    )
    print(f"    {label}: {path}  ->  127.0.0.1:{port}", file=sys.stderr)
    if label == "WEB_CONFIG_PATH":
        fix = (
            f"  - set BACKEND_PORT={port} in your .env, or\n"
            "  - redeploy the frontend built for this APP_VERSION (npm run build) to that IIS site, so its\n"
            f"    web.config forwards to port {backend_port} (from frontend/profiles/<version>.env)\n"
        )
    else:
        fix = (
            f"  - set BACKEND_PORT={port} in your .env, or\n"
            "  - rebuild the frontend for this APP_VERSION (npm run build), which writes\n"
            f"    frontend/dist/web.config with port {backend_port} from frontend/profiles/<version>.env\n"
        )
    print(
        "\nEvery request through IIS would 502. Fix ONE of:\n" + fix +
        "\nSet SKIP_PORT_CHECK=1 to start anyway.\n",
        file=sys.stderr,
    )
    raise SystemExit(1)
