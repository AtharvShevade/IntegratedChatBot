# tenant_repo_service.py — Tenant ID → repository base path resolution (6.0 only).
#
# 6.0 introduces a Tenant ID layer above the repo root: multiple tenants share
# one BASE_REPO_PATH, each with its own subtree at BASE_REPO_PATH/<TenantId>/.
# The tenant registry (XML_Tenant.xml) lives at the repo root, one <Row> per tenant:
#   <Row TenantId="1001" Name="Tenant 1" DomainId="irisindia.net" Status="true" />
#
# 5.5 requests never carry a tenant_id — get_repo_base_path(None) returns the
# unmodified BASE_REPO_PATH so 5.5 behaviour is completely unaffected.

from __future__ import annotations

import logging
import os
import threading
import time

from backend.config import BASE_REPO_PATH
from backend.tools.xml_loader import load_xml_tree

logger = logging.getLogger(__name__)

_XML_TENANT_PATH: str = os.getenv(
    "XML_TENANT_PATH",
    os.path.join(BASE_REPO_PATH, "XML_Tenant.xml"),
)

_TENANT_CACHE_TTL: float = float(os.getenv("TENANT_CACHE_TTL_SEC", "300"))

_lock = threading.Lock()
_tenant_map: dict[str, str] | None = None
_tenant_map_ts: float = 0.0


class UnknownTenantError(ValueError):
    """Raised when a tenant_id is supplied but not found in the tenant registry."""


def _build_tenant_map() -> dict[str, str]:
    root = load_xml_tree(_XML_TENANT_PATH, "XML_Tenant.xml")
    mapping: dict[str, str] = {}
    if root is None:
        logger.error(
            "[TENANT] Cannot load XML_Tenant.xml (path=%s) — tenant resolution unavailable",
            _XML_TENANT_PATH,
        )
        return mapping

    for el in root.findall("Row"):
        tenant_id = el.attrib.get("TenantId", "").strip()
        if not tenant_id:
            continue
        status = el.attrib.get("Status", "true").strip().lower()
        if status != "true":
            logger.info("[TENANT] Skipping inactive tenant_id=%r (Status=%r)", tenant_id, status)
            continue
        candidate = os.path.join(BASE_REPO_PATH, tenant_id)
        if not os.path.isdir(candidate):
            logger.warning(
                "[TENANT] tenant_id=%r registered but folder missing on disk: %s",
                tenant_id, candidate,
            )
            continue
        mapping[tenant_id] = candidate

    logger.info("[TENANT] Loaded %d active tenant(s) from %s", len(mapping), _XML_TENANT_PATH)
    return mapping


def _get_tenant_map() -> dict[str, str]:
    global _tenant_map, _tenant_map_ts
    with _lock:
        if _tenant_map is not None and (time.monotonic() - _tenant_map_ts) < _TENANT_CACHE_TTL:
            return _tenant_map
        _tenant_map = _build_tenant_map()
        _tenant_map_ts = time.monotonic()
        return _tenant_map


def get_repo_base_path(tenant_id: str | None) -> str:
    """Resolve the repository base path for a request.

    ``tenant_id`` is ``None`` for 5.5 traffic — returns the unmodified
    ``BASE_REPO_PATH`` (no behaviour change from today).

    For 6.0 traffic (``tenant_id`` provided), resolves
    ``BASE_REPO_PATH/<tenant_id>`` via the XML_Tenant.xml registry.
    Raises ``UnknownTenantError`` if the tenant is not registered/active —
    no silent fallback to a default tenant.
    """
    if not tenant_id:
        return BASE_REPO_PATH

    clean = str(tenant_id).strip()
    mapping = _get_tenant_map()
    base_path = mapping.get(clean)
    if base_path is None:
        logger.error("[TENANT] Unknown or inactive tenant_id=%r", clean)
        raise UnknownTenantError(f"Unknown or inactive tenant_id: {clean!r}")

    return os.path.normpath(base_path)


def invalidate() -> None:
    """Force the next call to re-read XML_Tenant.xml from disk."""
    global _tenant_map
    with _lock:
        _tenant_map = None
