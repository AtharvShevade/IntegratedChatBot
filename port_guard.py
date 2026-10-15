"""
port_guard.py -- fail fast when BACKEND_PORT and web.config disagree.

The frontend reaches this backend through the IIS reverse proxy rule in
frontend/public/web.config (copied verbatim into frontend/dist/ by the Vite
build). That rule names the port IIS forwards to; BACKEND_PORT in .env names
the port uvicorn opens. They are two files read by two different programs,
with nothing connecting them -- set one and forget the other and every request
through IIS 502s while the backend itself looks perfectly healthy.

This check runs before uvicorn binds and refuses to start on a mismatch, so the
failure shows up as one readable line at startup instead of as a dead site.

A missing or unparseable web.config is NOT an error: the file is part of the
frontend deployment and a backend-only host legitimately has no copy of it.
Set SKIP_PORT_CHECK=1 to bypass the check entirely.
"""

from __future__ import annotations

import os
import re
import sys
import xml.etree.ElementTree as ET

# Relative to the repo root. dist/ is what IIS actually serves; public/ is the
# source it is built from. Both are checked -- a stale dist/ is exactly the
# kind of drift this guard exists to catch.
_WEB_CONFIG_PATHS = (
    os.path.join("frontend", "dist", "web.config"),
    os.path.join("frontend", "public", "web.config"),
)


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


def assert_port_matches_web_config(backend_port: int, root_dir: str) -> None:
    """Exit with a diagnostic if any web.config forwards to a different port."""
    if os.environ.get("SKIP_PORT_CHECK", "").strip() in ("1", "true", "True"):
        return

    # The Vite build writes dist/web.config with the port of the APP_VERSION it
    # was built for (frontend/profiles/<version>.env), so dist/ is what IIS
    # serves and the only file that must agree. public/web.config is just the
    # source default the build starts from - it is checked only when there is no
    # dist/ yet.
    present = [rel for rel in _WEB_CONFIG_PATHS if os.path.exists(os.path.join(root_dir, rel))]

    mismatches = []
    for rel in present[:1]:
        port = _rewrite_port(os.path.join(root_dir, rel))
        if port is not None and port != backend_port:
            mismatches.append((rel, port))

    if not mismatches:
        return

    print(
        f"\n[PORT MISMATCH] BACKEND_PORT={backend_port}, but IIS forwards elsewhere:",
        file=sys.stderr,
    )
    for rel, port in mismatches:
        print(f"    {rel}  ->  127.0.0.1:{port}", file=sys.stderr)
    print(
        "\nEvery request through IIS would 502. Fix ONE of:\n"
        f"  - set BACKEND_PORT={mismatches[0][1]} in your .env, or\n"
        "  - rebuild the frontend for this APP_VERSION (npm run build), which writes\n"
        f"    frontend/dist/web.config with port {backend_port} from frontend/profiles/<version>.env\n"
        "\nSet SKIP_PORT_CHECK=1 to start anyway.\n",
        file=sys.stderr,
    )
    raise SystemExit(1)
