# auth_service.py — User → Department → Allowed FormIds lookup.
#
# Flow:
#   1. Parse XML_User.xml  : LoginId  → DeptId
#   2. Parse XML_Dept.xml  : DeptId   → pipe-separated FormIds  (e.g. "2001|2007|2035")
#   3. Return set[str] of allowed FormIds for the user.
#
# Returns:
#   None         — user not found in XML_User.xml (caller should deny access)
#   set[str]     — allowed FormId strings (may be empty if dept has no Forms)
#
# Results are TTL-cached per login_id (default 1 hour) to avoid repeated XML reads.
#
# Attribute names can be overridden via environment variables if your XML schema differs:
#   XML_USER_LOGIN_ATTR  (default: "LoginId")   — attribute holding the login identifier
#   XML_USER_DEPT_ATTR   (default: "DeptId")    — attribute holding the department ID

from __future__ import annotations

import logging
import os
import time

from backend.config import (
    XML_DEPT_PATH,
    XML_USER_PATH,
    XML_ROLE_ACCESS_PATH,
    get_dept_xml_path,
    get_user_xml_path,
    get_role_access_xml_path,
    get_option_xml_path,
)
from backend.tools.xml_loader import load_xml_tree

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configurable attribute names
# ---------------------------------------------------------------------------
_USER_LOGIN_ATTR: str = os.getenv("XML_USER_LOGIN_ATTR", "LoginId")
_USER_DEPT_ATTR:  str = os.getenv("XML_USER_DEPT_ATTR",  "DepartmentId")
_USER_ROLE_ATTR:  str = os.getenv("XML_USER_ROLE_ATTR",  "RoleId")

# TTL in seconds — override via AUTH_TTL_SEC env var (default 1 hour)
_AUTH_TTL: float = float(os.getenv("AUTH_TTL_SEC", "3600"))

# Enable or disable authorization checks entirely. Defaults to true.
AUTHORIZATION_ENABLED: bool = os.getenv("AUTHORIZATION_ENABLED", "true").lower() == "true"

# Cache keyed by (tenant_id, login_id) — tenant_id is "" for 5.5 traffic,
# which is equivalent to the old bare login_id key (no collisions introduced).
# { (tenant_id, login_id): (result, monotonic_ts, xml_mtime) }
_cache: dict[tuple[str, str], tuple[set[str] | None, float, float]] = {}

# Per-(tenant_id, login_id) cache for role-based CreateInstance access.
_create_cache: dict[tuple[str, str], tuple[bool, float]] = {}


def _cache_key(tenant_id: str | None, login_id: str) -> tuple[str, str]:
    return (tenant_id or "", login_id)


def _auth_xml_mtime(tenant_id: str | None = None) -> float:
    """Return the max mtime of XML_User.xml and XML_Dept.xml for this tenant.

    If either file changes, the auth cache is considered stale regardless of TTL.
    """
    mtime = 0.0
    paths = (
        (get_user_xml_path(tenant_id), get_dept_xml_path(tenant_id))
        if tenant_id
        else (XML_USER_PATH, XML_DEPT_PATH)
    )
    for path in paths:
        try:
            mtime = max(mtime, os.path.getmtime(path))
        except OSError:
            pass
    return mtime


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_allowed_form_ids(login_id: str, tenant_id: str | None = None) -> set[str] | None:
    """Return the set of FormIds this user may access.

    Parameters
    ----------
    login_id:
        The login identifier sent from the .NET application (``loginId`` URL param).
    tenant_id:
        Optional 6.0 tenant ID. ``None`` (5.5 traffic) resolves XML_User.xml/
        XML_Dept.xml from the global BASE_REPO_PATH exactly as before.

    Returns
    -------
    ``None``
        User was not found in XML_User.xml — caller should deny access.
    ``set[str]``
        Set of FormId strings the user's department is allowed to access.
        An empty set means the department exists but has no forms assigned.
    """
    if not AUTHORIZATION_ENABLED:
        logger.debug(
            "[AUTH_BYPASS] Authorization disabled by AUTHORIZATION_ENABLED=false — allowing all forms for login_id=%r",
            login_id,
        )
        return None

    clean = login_id.strip()
    if not clean:
        return None

    key = _cache_key(tenant_id, clean)
    current_mtime = _auth_xml_mtime(tenant_id)
    entry = _cache.get(key)
    if entry:
        result, ts, cached_mtime = entry
        if current_mtime != cached_mtime:
            logger.info(
                "[AUTH_CACHE] XML_User.xml or XML_Dept.xml changed on disk — "
                "invalidating cache for login_id=%r tenant_id=%r", clean, tenant_id,
            )
        elif (time.monotonic() - ts) < _AUTH_TTL:
            return result

    result = _lookup(clean, tenant_id)
    _cache[key] = (result, time.monotonic(), current_mtime)
    logger.info(
        "[AUTH_CACHE] login_id=%r tenant_id=%r result=%s",
        clean, tenant_id,
        f"{len(result)} forms" if result is not None else "NOT FOUND",
    )
    return result


def invalidate(login_id: str, tenant_id: str | None = None) -> None:
    """Remove a cached entry so the next request re-reads the XML."""
    _cache.pop(_cache_key(tenant_id, login_id.strip()), None)


# ---------------------------------------------------------------------------
# Internal lookup
# ---------------------------------------------------------------------------

def _lookup(login_id: str, tenant_id: str | None = None) -> set[str] | None:
    """Read XML files and resolve allowed FormIds. Not cached — use get_allowed_form_ids."""
    user_xml_path = get_user_xml_path(tenant_id) if tenant_id else XML_USER_PATH
    dept_xml_path = get_dept_xml_path(tenant_id) if tenant_id else XML_DEPT_PATH

    # ── Step 1: resolve DepartmentId from XML_User.xml ──────────────────────
    user_root = load_xml_tree(user_xml_path, "XML_User.xml")
    if user_root is None:
        logger.error(
            "[AUTH] Cannot load XML_User.xml (path=%s) — denying all access", user_xml_path
        )
        return None

    login_lower = login_id.lower()
    dept_id: str | None = None

    for el in user_root.findall("Row"):
        if el.attrib.get(_USER_LOGIN_ATTR, "").strip().lower() == login_lower:
            dept_id = el.attrib.get(_USER_DEPT_ATTR, "").strip()
            logger.info(
                "[AUTH] Step 1 | LoginId: %r  →  DepartmentId (attr=%r): %r",
                login_id, _USER_DEPT_ATTR, dept_id,
            )
            break

    if dept_id is None:
        logger.warning(
            "[AUTH] Step 1 FAILED | LoginId %r not found in XML_User.xml "
            "(looking for attr=%r)",
            login_id, _USER_LOGIN_ATTR,
        )
        return None

    if not dept_id:
        logger.error(
            "[AUTH] Step 1 FAILED | LoginId %r found but attr %r is empty. "
            "Check XML_USER_DEPT_ATTR env var (current=%r). "
            "Possible values: 'DepartmentId', 'DeptId'",
            login_id, _USER_DEPT_ATTR, _USER_DEPT_ATTR,
        )
        return set()  # deny rather than allow

    # ── Step 2: resolve Forms from XML_Dept.xml / Department.xml ────────────
    dept_root = load_xml_tree(dept_xml_path, "XML_Dept.xml")
    if dept_root is None:
        logger.error(
            "[AUTH] Step 2 FAILED | Cannot load XML_Dept.xml (path=%s) — "
            "denying access for LoginId=%r",
            dept_xml_path, login_id,
        )
        return None

    # 6.0's Department.xml uses "Id" for the department key and splits forms
    # into "ReturnId" (XBRL) + "NXReturnId" (non-XBRL) instead of 5.5's single
    # "DeptId" + "Forms" pair.
    if tenant_id:
        from backend import config_6_0
        dept_key_attr = "Id"
        forms_attrs = (config_6_0.DEPT_FORMS_ATTR, config_6_0.DEPT_NX_FORMS_ATTR)
    else:
        dept_key_attr = "DeptId"
        forms_attrs = ("Forms",)

    for el in dept_root.findall("Row"):
        if el.attrib.get(dept_key_attr, "").strip() == dept_id:
            form_ids: set[str] = set()
            for attr in forms_attrs:
                forms_raw = el.attrib.get(attr, "")
                form_ids |= {f.strip() for f in forms_raw.split("|") if f.strip()}
            logger.info(
                "[AUTH] SUMMARY | LoginId: %r | DepartmentId: %r | "
                "Allowed FormIds: %d forms loaded | Sample (first 5): %s",
                login_id, dept_id, len(form_ids), sorted(form_ids)[:5],
            )
            return form_ids

    logger.warning(
        "[AUTH] Step 2 FAILED | DepartmentId %r not found in XML_Dept.xml "
        "for LoginId=%r",
        dept_id, login_id,
    )
    return set()  # user exists but dept entry is missing → no access


# ---------------------------------------------------------------------------
# Role-based access: CreateInstance
# ---------------------------------------------------------------------------

def get_user_role_id(login_id: str, tenant_id: str | None = None) -> str | None:
    """Return the RoleId for the given login_id from XML_User.xml.

    Returns
    -------
    ``str``
        The RoleId attribute value for the matched user row.
    ``None``
        User not found or XML unavailable.
    """
    user_xml_path = get_user_xml_path(tenant_id) if tenant_id else XML_USER_PATH
    user_root = load_xml_tree(user_xml_path, "XML_User.xml")
    if user_root is None:
        logger.error(
            "[AUTH_ROLE] Cannot load XML_User.xml (path=%s) — cannot resolve RoleId",
            user_xml_path,
        )
        return None

    login_lower = login_id.strip().lower()
    for el in user_root.findall("Row"):
        if el.attrib.get(_USER_LOGIN_ATTR, "").strip().lower() == login_lower:
            role_id = el.attrib.get(_USER_ROLE_ATTR, "").strip()
            logger.debug("[AUTH_ROLE] login_id=%r → role_id=%r", login_id, role_id)
            return role_id if role_id else None

    logger.warning(
        "[AUTH_ROLE] login_id=%r not found in XML_User.xml (attr=%s)",
        login_id, _USER_LOGIN_ATTR,
    )
    return None


def load_role_access_xml(tenant_id: str | None = None):
    """Load and return the root element of XML_RoleAccess.xml."""
    path = get_role_access_xml_path(tenant_id) if tenant_id else XML_ROLE_ACCESS_PATH
    return load_xml_tree(path, "XML_RoleAccess.xml")


# ---------------------------------------------------------------------------
# Option.xml resolution (6.0 only) — generic ResourceId -> OptionId lookup.
#
# 6.0's RoleAccess.xml references permissions by numeric OptionId, which is
# meaningless on its own. Option.xml is the menu/permission registry that
# names each OptionId (Id -> Name/ResourceId). This resolver is generic so
# any feature needing a specific permission (not just Instance Generation)
# can reuse it by ResourceId instead of a hardcoded number.
# ---------------------------------------------------------------------------

# Per-tenant cache: { tenant_id: (mtime, {resource_id: option_id}) }
_option_cache: dict[str, tuple[float, dict[str, str]]] = {}


def _load_option_map(tenant_id: str) -> dict[str, str]:
    """Return {ResourceId: OptionId} for this tenant's Option.xml, mtime-cached."""
    from backend import config_6_0

    path = get_option_xml_path(tenant_id)
    try:
        current_mtime = os.path.getmtime(path)
    except OSError:
        current_mtime = 0.0

    cached = _option_cache.get(tenant_id)
    if cached and cached[0] == current_mtime:
        return cached[1]

    root = load_xml_tree(path, "Option.xml")
    option_map: dict[str, str] = {}
    if root is not None:
        for el in root.findall("Row"):
            option_id = el.attrib.get(config_6_0.OPTION_ID_ATTR, "").strip()
            resource_id = el.attrib.get(config_6_0.OPTION_RESOURCE_ID_ATTR, "").strip()
            if option_id and resource_id:
                option_map[resource_id] = option_id
    else:
        logger.error("[AUTH_OPTION] Cannot load Option.xml (path=%s) tenant_id=%r", path, tenant_id)

    _option_cache[tenant_id] = (current_mtime, option_map)
    logger.info(
        "[AUTH_OPTION] Loaded %d option(s) from Option.xml tenant_id=%r", len(option_map), tenant_id,
    )
    return option_map


def resolve_option_id_by_resource_id(resource_id: str, tenant_id: str) -> str | None:
    """Return the numeric OptionId in Option.xml whose ResourceId matches *resource_id*.

    6.0 only. Returns None if Option.xml is unavailable or no row matches.
    """
    option_map = _load_option_map(tenant_id)
    option_id = option_map.get(resource_id)
    if option_id is None:
        logger.warning(
            "[AUTH_OPTION] No Option.xml row with ResourceId=%r found tenant_id=%r",
            resource_id, tenant_id,
        )
    return option_id


def invalidate_option_cache(tenant_id: str) -> None:
    """Remove a cached Option.xml map so the next request re-reads the XML."""
    _option_cache.pop(tenant_id, None)


def validate_create_instance_access(role_id: str, tenant_id: str | None = None) -> bool:
    """Return True if the role is permitted to create instances.

    5.5: looks for a ``<Row>`` in XML_RoleAccess.xml where ``RoleId`` ==
    *role_id*, ``OptionId`` == the literal string ``"CreateInstance"``, and
    ``HasNew`` == ``"true"``. Unchanged from before tenant support existed.

    6.0: RoleAccess.xml's ``OptionId`` is a numeric permission ID with no
    self-describing meaning. The OptionId for "Instance Generation" is
    resolved dynamically from Option.xml (matching
    ``config_6_0.RESOURCE_ID_INSTANCE_GENERATION`` against each row's
    ``ResourceId`` attribute) rather than hardcoded — see
    ``resolve_option_id_by_resource_id``. ``XML_6_0_ROLE_ACCESS_CREATE_INSTANCE_OPTION_ID``
    remains available as a manual override/fast-path; if set, it skips the
    Option.xml lookup entirely.

    Returns False if the XML is unavailable, the row is missing, the
    ResourceId can't be resolved, or ``HasNew`` is not ``"true"``.
    """
    if tenant_id:
        from backend import config_6_0
        option_id = config_6_0.ROLE_ACCESS_CREATE_INSTANCE_OPTION_ID
        if not option_id:
            option_id = resolve_option_id_by_resource_id(
                config_6_0.RESOURCE_ID_INSTANCE_GENERATION, tenant_id,
            )
        if not option_id:
            logger.error(
                "[AUTH_ROLE] 6.0 tenant_id=%r — could not resolve OptionId for "
                "ResourceId=%r from Option.xml — denying role_id=%r",
                tenant_id, config_6_0.RESOURCE_ID_INSTANCE_GENERATION, role_id,
            )
            return False
    else:
        option_id = "CreateInstance"

    root = load_role_access_xml(tenant_id)
    if root is None:
        logger.error(
            "[AUTH_ROLE] Cannot load XML_RoleAccess.xml — denying CreateInstance for role_id=%r",
            role_id,
        )
        return False

    for el in root.findall("Row"):
        if (
            el.attrib.get("RoleId", "").strip() == role_id
            and el.attrib.get("OptionId", "").strip() == option_id
        ):
            has_new = el.attrib.get("HasNew", "false").strip().lower()
            allowed = has_new == "true"
            logger.info(
                "[AUTH_ROLE] role_id=%r CreateInstance HasNew=%r → allowed=%s",
                role_id, has_new, allowed,
            )
            return allowed

    logger.warning(
        "[AUTH_ROLE] No CreateInstance row found in XML_RoleAccess.xml for role_id=%r",
        role_id,
    )
    return False


def can_generate_instance(login_id: str, tenant_id: str | None = None) -> bool:
    """Return True if the user has permission to generate report instances.

    Resolves: ``login_id`` → ``RoleId`` (XML_User.xml)
                           → ``HasNew`` for ``OptionId=CreateInstance`` (XML_RoleAccess.xml)

    Results are TTL-cached per (tenant_id, login_id) (same TTL as department access).
    Returns False on any lookup failure (user not found, XML missing, no access row).
    """
    if not AUTHORIZATION_ENABLED:
        logger.debug(
            "[AUTH_BYPASS] Authorization disabled by AUTHORIZATION_ENABLED=false — allowing report generation for login_id=%r",
            login_id,
        )
        return True

    clean = login_id.strip()
    if not clean:
        return False

    key = _cache_key(tenant_id, clean)
    entry = _create_cache.get(key)
    if entry and (time.monotonic() - entry[1]) < _AUTH_TTL:
        logger.debug("[AUTH_ROLE] cache hit login_id=%r tenant_id=%r can_generate=%s", clean, tenant_id, entry[0])
        return entry[0]

    role_id = get_user_role_id(clean, tenant_id)
    if role_id is None:
        result = False
    else:
        result = validate_create_instance_access(role_id, tenant_id)

    _create_cache[key] = (result, time.monotonic())
    logger.info(
        "[AUTH_ROLE] login_id=%r tenant_id=%r role_id=%r can_generate_instance=%s",
        clean, tenant_id, role_id, result,
    )
    return result


def invalidate_role_cache(login_id: str, tenant_id: str | None = None) -> None:
    """Remove a cached role-access entry so the next request re-reads the XML."""
    _create_cache.pop(_cache_key(tenant_id, login_id.strip()), None)
