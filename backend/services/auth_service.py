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

from backend.config import XML_DEPT_PATH, XML_USER_PATH, XML_ROLE_ACCESS_PATH
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

# Per-login cache: { login_id: (result, monotonic_ts, xml_mtime) }
_cache: dict[str, tuple[set[str] | None, float, float]] = {}

# Per-login cache for role-based CreateInstance access: { login_id: (can_create, timestamp) }
_create_cache: dict[str, tuple[bool, float]] = {}


def _auth_xml_mtime() -> float:
    """Return the max mtime of XML_User.xml and XML_Dept.xml.

    If either file changes, the auth cache is considered stale regardless of TTL.
    """
    mtime = 0.0
    for path in (XML_USER_PATH, XML_DEPT_PATH):
        try:
            mtime = max(mtime, os.path.getmtime(path))
        except OSError:
            pass
    return mtime


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_allowed_form_ids(login_id: str) -> set[str] | None:
    """Return the set of FormIds this user may access.

    Parameters
    ----------
    login_id:
        The login identifier sent from the .NET application (``loginId`` URL param).

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

    current_mtime = _auth_xml_mtime()
    entry = _cache.get(clean)
    if entry:
        result, ts, cached_mtime = entry
        if current_mtime != cached_mtime:
            logger.info(
                "[AUTH_CACHE] XML_User.xml or XML_Dept.xml changed on disk — "
                "invalidating cache for login_id=%r", clean,
            )
        elif (time.monotonic() - ts) < _AUTH_TTL:
            return result

    result = _lookup(clean)
    _cache[clean] = (result, time.monotonic(), current_mtime)
    logger.info(
        "[AUTH_CACHE] login_id=%r result=%s",
        clean,
        f"{len(result)} forms" if result is not None else "NOT FOUND",
    )
    return result


def invalidate(login_id: str) -> None:
    """Remove a cached entry so the next request re-reads the XML."""
    _cache.pop(login_id.strip(), None)


# ---------------------------------------------------------------------------
# Internal lookup
# ---------------------------------------------------------------------------

def _lookup(login_id: str) -> set[str] | None:
    """Read XML files and resolve allowed FormIds. Not cached — use get_allowed_form_ids."""
    # ── Step 1: resolve DepartmentId from XML_User.xml ──────────────────────
    user_root = load_xml_tree(XML_USER_PATH, "XML_User.xml")
    if user_root is None:
        logger.error(
            "[AUTH] Cannot load XML_User.xml (path=%s) — denying all access", XML_USER_PATH
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

    # ── Step 2: resolve Forms from XML_Dept.xml ─────────────────────────────
    dept_root = load_xml_tree(XML_DEPT_PATH, "XML_Dept.xml")
    if dept_root is None:
        logger.error(
            "[AUTH] Step 2 FAILED | Cannot load XML_Dept.xml (path=%s) — "
            "denying access for LoginId=%r",
            XML_DEPT_PATH, login_id,
        )
        return None

    for el in dept_root.findall("Row"):
        if el.attrib.get("DeptId", "").strip() == dept_id:
            forms_raw = el.attrib.get("Forms", "")
            form_ids  = {f.strip() for f in forms_raw.split("|") if f.strip()}
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

def get_user_role_id(login_id: str) -> str | None:
    """Return the RoleId for the given login_id from XML_User.xml.

    Returns
    -------
    ``str``
        The RoleId attribute value for the matched user row.
    ``None``
        User not found or XML unavailable.
    """
    user_root = load_xml_tree(XML_USER_PATH, "XML_User.xml")
    if user_root is None:
        logger.error(
            "[AUTH_ROLE] Cannot load XML_User.xml (path=%s) — cannot resolve RoleId",
            XML_USER_PATH,
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


def load_role_access_xml():
    """Load and return the root element of XML_RoleAccess.xml."""
    return load_xml_tree(XML_ROLE_ACCESS_PATH, "XML_RoleAccess.xml")


def validate_create_instance_access(role_id: str) -> bool:
    """Return True if the role is permitted to create instances.

    Looks for a ``<Row>`` in XML_RoleAccess.xml where:
      * ``RoleId``   == *role_id*
      * ``OptionId`` == ``"CreateInstance"``
      * ``HasNew``   == ``"true"``

    Returns False if the XML is unavailable, the row is missing, or
    ``HasNew`` is not ``"true"``.
    """
    root = load_role_access_xml()
    if root is None:
        logger.error(
            "[AUTH_ROLE] Cannot load XML_RoleAccess.xml — denying CreateInstance for role_id=%r",
            role_id,
        )
        return False

    for el in root.findall("Row"):
        if (
            el.attrib.get("RoleId", "").strip() == role_id
            and el.attrib.get("OptionId", "").strip() == "CreateInstance"
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


def can_generate_instance(login_id: str) -> bool:
    """Return True if the user has permission to generate report instances.

    Resolves: ``login_id`` → ``RoleId`` (XML_User.xml)
                           → ``HasNew`` for ``OptionId=CreateInstance`` (XML_RoleAccess.xml)

    Results are TTL-cached per login_id (same TTL as department access).
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

    entry = _create_cache.get(clean)
    if entry and (time.monotonic() - entry[1]) < _AUTH_TTL:
        logger.debug("[AUTH_ROLE] cache hit login_id=%r can_generate=%s", clean, entry[0])
        return entry[0]

    role_id = get_user_role_id(clean)
    if role_id is None:
        result = False
    else:
        result = validate_create_instance_access(role_id)

    _create_cache[clean] = (result, time.monotonic())
    logger.info(
        "[AUTH_ROLE] login_id=%r role_id=%r can_generate_instance=%s",
        clean, role_id, result,
    )
    return result


def invalidate_role_cache(login_id: str) -> None:
    """Remove a cached role-access entry so the next request re-reads the XML."""
    _create_cache.pop(login_id.strip(), None)
