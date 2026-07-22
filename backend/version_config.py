# version_config.py — APP_VERSION routing and 6.0 tenant resolution.
#
# APP_VERSION=5.5 (default): everything below is inert. get_active_root()
# always returns backend.config.BASE_REPO_PATH, exactly as before this file
# existed.
#
# APP_VERSION=6.0: a request resolves a TenantId (either forwarded directly
# by the frontend, or looked up from a domain via XML_Tenant.xml), then sets
# the active repo root to D:\Repo6\Repo6\{TenantId} for the duration of that
# request via repo_scope(). Every path built downstream (DataBase\, Instance\,
# Render\, ...) is rooted there — never under the bare APP_600_REPO_ROOT,
# which only holds the tenant registry plus legacy/vestigial top-level files.
from __future__ import annotations

import contextvars
import logging
import os
import time
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

APP_VERSION: str = os.getenv("APP_VERSION", "5.5").strip()
IS_V6: bool = APP_VERSION == "6.0"

APP_600_REPO_ROOT: str = os.getenv("APP_600_REPO_ROOT", r"D:\Repo6\Repo6")
APP_600_TENANT_XML_PATH: str = os.path.join(APP_600_REPO_ROOT, "XML_Tenant.xml")

_TENANT_TTL: float = float(os.getenv("TENANT_REGISTRY_TTL_SEC", "3600"))
_tenant_cache: dict[str, str] | None = None
_tenant_cache_ts: float = 0.0
_tenant_cache_mtime: float = 0.0


def _tenant_xml_mtime() -> float:
    try:
        return os.path.getmtime(APP_600_TENANT_XML_PATH)
    except OSError:
        return 0.0


def _load_tenant_registry() -> dict[str, str]:
    """Parse XML_Tenant.xml -> {domain_lower: TenantId}."""
    registry: dict[str, str] = {}
    try:
        root = ET.parse(APP_600_TENANT_XML_PATH).getroot()
    except (ET.ParseError, OSError) as exc:
        logger.error(
            "[version_config] Cannot load XML_Tenant.xml (path=%s): %s",
            APP_600_TENANT_XML_PATH, exc,
        )
        return registry

    for el in root.findall("Row"):
        domain = el.attrib.get("DomainId", "").strip().lower()
        tenant_id = el.attrib.get("TenantId", "").strip()
        status = el.attrib.get("Status", "true").strip().lower()
        if domain and tenant_id and status != "false":
            registry[domain] = tenant_id
    return registry


def _get_tenant_registry() -> dict[str, str]:
    global _tenant_cache, _tenant_cache_ts, _tenant_cache_mtime

    current_mtime = _tenant_xml_mtime()
    if (
        _tenant_cache is not None
        and current_mtime == _tenant_cache_mtime
        and (time.monotonic() - _tenant_cache_ts) < _TENANT_TTL
    ):
        return _tenant_cache

    _tenant_cache = _load_tenant_registry()
    _tenant_cache_ts = time.monotonic()
    _tenant_cache_mtime = current_mtime
    return _tenant_cache


def resolve_tenant_id(tenant_id: str | None, domain: str | None) -> str | None:
    """Resolve the active TenantId for a 6.0 request.

    An explicit tenant_id — already resolved server-side by the .NET login
    flow and forwarded by the React frontend (see ChatbotIframe.jsx /
    tokenService.js) — is trusted as-is. Falls back to a domain -> TenantId
    lookup in XML_Tenant.xml only when tenant_id is absent.
    """
    if tenant_id and tenant_id.strip():
        return tenant_id.strip()
    if domain and domain.strip():
        return _get_tenant_registry().get(domain.strip().lower())
    return None


def repo_root_for_tenant(tenant_id: str) -> str:
    """D:\\Repo6\\Repo6\\{TenantId} — the tenant-scoped repo root.

    Every subsequent path (DataBase\\, Instance\\, Render\\, ...) is built
    under THIS root, never under the bare APP_600_REPO_ROOT (which is a
    legacy/shared staging area, not per-tenant master data).
    """
    return os.path.join(APP_600_REPO_ROOT, tenant_id)


# ---------------------------------------------------------------------------
# Per-request active repo root.
#
# contextvars are the correct per-request-scoped mechanism under FastAPI's
# asyncio event loop: each request's coroutine gets its own context, so
# concurrent requests for different tenants never see each other's override.
# ---------------------------------------------------------------------------

_active_root: "contextvars.ContextVar[str | None]" = contextvars.ContextVar(
    "active_repo_root", default=None
)

# Per-request 6.0 identity — the resolved TenantId and the short-lived JWT
# forwarded from the chatbot iframe's CHATBOT_AUTH postMessage handshake.
# Exposed via contextvars (like the repo root override above) rather than
# threaded as explicit parameters through agent/__init__.py's deep call
# chain (decide() -> several nested handlers -> _finalize_generation()) —
# only the one or two call sites that actually need them
# (instance_generator.call_generate_api_v6's caller) read these; everything
# else in that call chain is unaffected, so 5.5's existing signatures don't
# need to change at all.
_active_tenant_id: "contextvars.ContextVar[str | None]" = contextvars.ContextVar(
    "active_tenant_id", default=None
)
_active_jwt: "contextvars.ContextVar[str | None]" = contextvars.ContextVar(
    "active_jwt", default=None
)


def get_active_tenant_id() -> str | None:
    return _active_tenant_id.get()


def get_active_jwt() -> str | None:
    return _active_jwt.get()


def get_repo_root_override() -> str | None:
    """Return the per-request repo root override, or None if unset.

    Used by backend.config._active_root() alongside its own BASE_REPO_PATH
    global, so there's no re-import of backend.config from here.
    """
    return _active_root.get()


def get_active_root() -> str:
    """Return the repo root active for the current request.

    Falls back to backend.config.BASE_REPO_PATH when no override is set —
    which is always the case under APP_VERSION=5.5, so 5.5 path resolution
    is completely unchanged. Prefer backend.config's own path helpers
    (returns_xml_path(), instance_base_dir(), ...) over calling this
    directly — this is exposed mainly for non-config callers that need the
    raw active root.
    """
    override = _active_root.get()
    if override:
        return override
    from backend import config  # local import avoids a circular import at module load time
    return config.BASE_REPO_PATH


class repo_scope:
    """Context manager: sets the active repo root (and, for 6.0, the
    resolved tenant_id / forwarded jwt) for one request.

    Usage::

        with version_config.repo_scope(root, tenant_id=tenant_id, jwt=jwt):
            ... handle the request ...

    Passing root=None is a no-op (used for APP_VERSION=5.5, where nothing
    should ever override BASE_REPO_PATH).
    """

    def __init__(self, root: str | None, tenant_id: str | None = None, jwt: str | None = None):
        self._root = root
        self._tenant_id = tenant_id
        self._jwt = jwt
        self._tokens: list = []

    def __enter__(self) -> "repo_scope":
        self._tokens.append((_active_root, _active_root.set(self._root)))
        self._tokens.append((_active_tenant_id, _active_tenant_id.set(self._tenant_id)))
        self._tokens.append((_active_jwt, _active_jwt.set(self._jwt)))
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        for var, token in reversed(self._tokens):
            var.reset(token)
        return False
