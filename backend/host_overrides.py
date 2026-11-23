"""Process-wide host-name overrides (an in-process "hosts file").

HOST_OVERRIDES=ollama.irisregtech.com=3.109.51.228[,other.name=1.2.3.4]

The Ollama proxy on 3.109.51.228 serves HTTPS with a *.irisregtech.com certificate.
Called by IP, every client (httpx, requests, sync or async) rejects it — correctly —
because an IP does not match that name, and there is no DNS entry for a matching name.
With an override, OLLAMA_BASE_URL can name the server (https://ollama.irisregtech.com/...)
and the certificate is verified normally: trusted CA, expiry, and the name. Verification
is never disabled.

It works by resolving only the listed names to the given IPs in socket.getaddrinfo,
which every client in this process uses (asyncio's resolver calls it as well). Any
other name resolves exactly as before. Unset or empty = no change at all.
"""
from __future__ import annotations

import logging
import os
import socket

logger = logging.getLogger(__name__)

_installed = False


def _parse(raw: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for item in raw.split(","):
        name, sep, ip = item.strip().partition("=")
        if sep and name.strip() and ip.strip():
            mapping[name.strip().lower().rstrip(".")] = ip.strip()
    return mapping


def install() -> dict[str, str]:
    """Apply HOST_OVERRIDES from the environment. Idempotent; returns the mapping."""
    global _installed
    mapping = _parse(os.environ.get("HOST_OVERRIDES", ""))
    if not mapping or _installed:
        return mapping

    original = socket.getaddrinfo

    def getaddrinfo(host, *args, **kwargs):
        if isinstance(host, bytes):
            key = host.decode("ascii", "ignore")
        else:
            key = host or ""
        ip = mapping.get(key.lower().rstrip("."))
        return original(ip if ip else host, *args, **kwargs)

    socket.getaddrinfo = getaddrinfo
    _installed = True
    logger.info("[host_overrides] Resolving %s", ", ".join(f"{k} -> {v}" for k, v in mapping.items()))
    return mapping
