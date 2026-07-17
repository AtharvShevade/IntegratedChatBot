"""Centralized access control for the expanded db_qa Q&A layer.

Replaces the flat `effective_role_id == config.APP_DB_ADMIN_ROLE_ID` string
comparison previously done ad-hoc in backend/agent/db_qa_router.py and the
scattered `if not is_admin: return _admin_denied(...)` guards duplicated
across ~40 handlers in query_handlers.py. Both call sites should migrate to
scope_query() (Phase 6 wires the router; the legacy handlers keep their own
is_admin parameter for now, fed by the same is_admin() function below, so
nothing needs to change in query_handlers.py itself).

auth_service.py has no existing generic "is this role an admin" concept
(it only exposes get_allowed_form_ids/can_generate_instance/
get_user_role_id) — is_admin() below is the one new, centralized piece of
logic this task adds, built on top of auth_service.get_user_role_id()
rather than re-parsing XML_User.xml itself.
"""
from __future__ import annotations

from backend import config
from backend.services import auth_service

# target_type values a caller may pass. Kept as plain strings (not the
# Intent enum) so this module has no dependency on backend.db_qa.intents.
TARGET_TYPES_REQUIRING_ADMIN = frozenset({"other_user", "department", "role", "system_wide"})

# Self-service suggestion shown to a denied non-admin caller, keyed by the
# target_type they attempted. Deliberately generic (not per-intent) — Phase
# 6's router can layer a more specific per-intent hint on top if desired.
_SELF_SUGGESTION: dict[str, str] = {
    "other_user": "You can ask about your own profile instead — try \"what is my email\" or \"what is my role\".",
    "department": "You can ask about your own department instead — try \"which returns does my department have access to\".",
    "role": "You can ask about your own role instead — try \"what is my role\" or \"what permissions do I have\".",
    "system_wide": "This is an admin-only, system-wide question. Try asking about your own account, department, or role instead.",
}


def is_admin(login_id: str, tenant_id: str | None = None) -> bool:
    """Return True if *login_id*'s role is the configured admin role.

    Reuses auth_service.get_user_role_id() for role resolution (the same
    XML_User.xml lookup used everywhere else in the app) rather than
    re-implementing it; the only new logic here is the comparison against
    config.APP_DB_ADMIN_ROLE_ID, centralized so it happens in exactly one
    place instead of being duplicated per-handler.
    """
    if not login_id:
        return False
    role_id = auth_service.get_user_role_id(login_id, tenant_id)
    if role_id is None:
        return False
    return role_id == config.APP_DB_ADMIN_ROLE_ID


def scope_query(session_user: dict, intent: str, entities: dict) -> dict:
    """Authorize *intent* for *session_user* and return a scope dict.

    Parameters
    ----------
    session_user:
        Identity resolved from the authenticated session/request — NEVER
        from LLM-extracted chat entities. Expected keys: "login_id",
        "user_id" (optional), "tenant_id" (required).
    intent:
        The resolved Intent name (string value).
    entities:
        Entities extracted from the user's message (may include a
        `target_type` key chosen by the classifier, plus any
        target_user/target_department/target_role/target_return values).

    Returns
    -------
    dict
        {
          "target_type": str,
          "tenant_id": str | None,      # sourced ONLY from session_user
          "login_id": str,
          "user_id": str | None,
          "is_admin": bool,
          "allowed_form_ids": set[str] | None,  # populated for return-scoped queries
        }

    Raises
    ------
    PermissionError
        If *session_user* is not authorized for the requested target_type,
        or if tenant_id is missing from the session.
    """
    login_id = session_user.get("login_id") or ""
    tenant_id = session_user.get("tenant_id")  # session only — never entities
    target_type = entities.get("target_type", "self")

    if not tenant_id:
        raise PermissionError(
            "A tenant context is required to answer this question."
        )

    scope: dict = {
        "target_type": target_type,
        "tenant_id": tenant_id,
        "login_id": login_id,
        "user_id": session_user.get("user_id"),
        "is_admin": False,
        "allowed_form_ids": None,
    }

    if target_type == "self":
        # Always allowed — no admin check needed.
        scope["is_admin"] = is_admin(login_id, tenant_id)
        return scope

    if target_type in TARGET_TYPES_REQUIRING_ADMIN:
        admin = is_admin(login_id, tenant_id)
        scope["is_admin"] = admin
        if not admin:
            suggestion = _SELF_SUGGESTION.get(target_type, "Try asking about your own account instead.")
            raise PermissionError(suggestion)
        return scope

    if target_type == "return":
        # Reference data — generally allowed for anyone. Department-level
        # ACCESS to a specific return is scoped via the same allowed-FormIds
        # set used everywhere else in the app (auth_service), not a
        # separate reimplementation.
        scope["is_admin"] = is_admin(login_id, tenant_id)
        scope["allowed_form_ids"] = auth_service.get_allowed_form_ids(login_id, tenant_id)
        return scope

    # Unknown/unrecognized target_type — deny by default rather than
    # silently falling through to an unscoped query.
    raise PermissionError(
        f"Unrecognized target_type {target_type!r} — cannot authorize this question."
    )
