"""Query handlers package — dual dispatch during incremental migration.

Historically this was a single flat module (query_handlers.py) holding ~90
handler functions, one per db_* intent, plus a dispatch(intent, params,
user_id, role_id, is_admin, store) entry point and an INTENT_TO_HANDLER
dict. That code is now query_handlers/legacy.py, moved VERBATIM (byte-for-
byte reflow into the new package, no logic changes) — every symbol it
exported is re-exported here so existing importers
(backend/agent/db_qa_router.py, backend/db_qa/__init__.py) keep working
with zero changes: `from backend.db_qa import query_handlers` then
`query_handlers.dispatch(...)`, `query_handlers.INTENT_TO_HANDLER`,
`query_handlers.handle_unknown` all still resolve exactly as before.

New category handler files (user_handlers.py, department_handlers.py, etc.)
implement the ~48-intent catalog from backend.db_qa.intents.taxonomy using
the (scope, entities, store) -> dict signature — access_control.py's
scope_query() output feeds `scope` directly, so these handlers never see
raw is_admin bools or need to re-derive them.

dispatch2() is the new intent-scoped entry point. The live router (Phase 6,
backend/agent/db_qa_router.py) tries dispatch2() first for any intent that
has been migrated to the new taxonomy, and falls back to the legacy
dispatch() for anything not yet ported — this is what makes the migration
incremental and safe (an intent is either fully on the new path or fully
on the old one, never half-migrated).
"""
from __future__ import annotations

from typing import Callable

from backend.db_qa.xml_store import XMLStore

# ── Legacy re-exports (zero behavior change for existing importers) ────────
from backend.db_qa.query_handlers.legacy import (  # noqa: F401
    dispatch,
    HANDLERS,
    INTENT_TO_HANDLER,
    handle_unknown,
    # Individual handle_* functions are NOT all re-exported by name here —
    # any caller needing one directly should import
    # backend.db_qa.query_handlers.legacy explicitly. dispatch()/
    # INTENT_TO_HANDLER/handle_unknown are the only symbols the live
    # request path (agent/db_qa_router.py) actually touches (confirmed by
    # grep), so those are the compatibility surface that matters.
)

# ── New taxonomy-based handlers ─────────────────────────────────────────────
from backend.db_qa.intents.taxonomy import Intent
from backend.db_qa.query_handlers import (
    user_handlers,
    department_handlers,
    role_handlers,
    return_handlers,
    submission_handlers,
    cross_entity_handlers,
    menu_handlers,
    audit_handlers,
    reference_handlers,
)

NewHandler = Callable[[dict, dict, XMLStore], dict]

NEW_INTENT_TO_HANDLER: dict[Intent, NewHandler] = {
    # USER
    Intent.USER_PROFILE: user_handlers.handle_user_profile,
    Intent.USER_FIELD: user_handlers.handle_user_field,
    Intent.USER_LIST: user_handlers.handle_user_list,
    Intent.USERS_BY_DEPARTMENT: user_handlers.handle_users_by_department,
    Intent.USERS_BY_ROLE: user_handlers.handle_users_by_role,
    Intent.USERS_WITH_ROLES_AND_DEPARTMENTS: user_handlers.handle_users_with_roles_and_departments,

    # DEPARTMENT
    Intent.DEPARTMENT_LIST: department_handlers.handle_department_list,
    Intent.DEPARTMENT_PROFILE: department_handlers.handle_department_profile,
    Intent.DEPARTMENT_RETURNS: department_handlers.handle_department_returns,
    Intent.DEPARTMENTS_WITH_RETURN_ACCESS: department_handlers.handle_departments_with_return_access,
    Intent.DEPARTMENT_HAS_RETURN: department_handlers.handle_department_has_return,

    # ROLE
    Intent.ROLE_LIST: role_handlers.handle_role_list,
    Intent.ROLE_PROFILE: role_handlers.handle_role_profile,
    Intent.ROLE_USERS: role_handlers.handle_role_users,
    Intent.ROLE_PEER_COUNT: role_handlers.handle_role_peer_count,
    Intent.PERMISSION_PROFILE: role_handlers.handle_permission_profile,
    Intent.PERMISSION_CHECK: role_handlers.handle_permission_check,
    Intent.ROLES_WITH_PERMISSION: role_handlers.handle_roles_with_permission,
    Intent.ROLE_MODULE_ACCESS: role_handlers.handle_role_module_access,
    Intent.ROLE_PERMISSION_DIFF: role_handlers.handle_role_permission_diff,
    Intent.USER_LEVEL_LIST: role_handlers.handle_user_level_list,
    Intent.USER_LEVEL_SELF: role_handlers.handle_user_level_self,

    # RETURN / PERIOD
    Intent.PERIOD_LIST: return_handlers.handle_period_list,
    Intent.PERIOD_LOOKUP: return_handlers.handle_period_lookup,
    Intent.RETURNS_BY_FREQUENCY: return_handlers.handle_returns_by_frequency,
    Intent.RETURN_LIST: return_handlers.handle_return_list,
    Intent.RETURN_PROFILE: return_handlers.handle_return_profile,
    Intent.RETURN_FIELD: return_handlers.handle_return_field,
    Intent.RETURN_VALIDATION_CONFIG: return_handlers.handle_return_validation_config,
    Intent.RETURNS_SUBMITTABLE_BY_DEPT: return_handlers.handle_returns_submittable_by_dept,
    Intent.NEXT_REPORTING_DATE: return_handlers.handle_next_reporting_date,
    Intent.REPORTS_FILED_IN_RANGE: return_handlers.handle_reports_filed_in_range,
    Intent.REPORTS_UPCOMING_IN_RANGE: return_handlers.handle_reports_upcoming_in_range,
    Intent.NONXBRL_RETURN_LIST: return_handlers.handle_nonxbrl_return_list,
    Intent.NONXBRL_RETURN_PROFILE: return_handlers.handle_nonxbrl_return_profile,
    Intent.DEPT_RETURN_ACCESS_MATRIX: return_handlers.handle_dept_return_access_matrix,
    Intent.MY_RETURN_ACCESS: return_handlers.handle_my_return_access,
    Intent.DEPT_FULL_RETURN_LIST: return_handlers.handle_dept_full_return_list,

    # INSTANCE_LOG
    Intent.SUBMISSION_STATUS: submission_handlers.handle_submission_status,
    Intent.SUBMISSION_LIST: submission_handlers.handle_submission_list,
    Intent.SUBMISSION_DETAIL: submission_handlers.handle_submission_detail,
    Intent.SUBMISSIONS_FOR_RETURN: submission_handlers.handle_submissions_for_return,
    Intent.MY_SUBMISSION_HISTORY: submission_handlers.handle_my_submission_history,

    # MENU_OPTIONS
    Intent.MENU_LIST: menu_handlers.handle_menu_list,
    Intent.MODULE_DETAIL: menu_handlers.handle_module_detail,
    Intent.MODULE_CHILDREN: menu_handlers.handle_module_children,

    # AUDIT_SECURITY
    Intent.AUDIT_HISTORY: audit_handlers.handle_audit_history,
    Intent.AUDIT_ENTITY_TRAIL: audit_handlers.handle_audit_entity_trail,
    Intent.SECURITY_EVENTS: audit_handlers.handle_security_events,
    Intent.LOG_QUERY: audit_handlers.handle_log_query,

    # CROSS_ENTITY
    Intent.USER_ACCESS_SUMMARY: cross_entity_handlers.handle_user_access_summary,
    Intent.CROSS_ENTITY_QUERY: cross_entity_handlers.handle_cross_entity_query,

    # Reference data
    Intent.BANK_INFO: reference_handlers.handle_bank_info,
    Intent.SEGMENT_INFO: reference_handlers.handle_segment_info,
    Intent.NOTIFICATION_QUERY: reference_handlers.handle_notification_query,
}


def handle_unknown_new(scope: dict, entities: dict, store: XMLStore) -> dict:
    return {
        "intent": "UNKNOWN", "label": "Unknown Intent", "found": False, "records": [],
        "summary": (
            "I wasn't able to determine what data you're looking for from the "
            "application database. Try rephrasing, or use the XBRL knowledge-base "
            "chat for taxonomy questions."
        ),
        "meta": {},
    }


def dispatch2(intent: Intent | str, scope: dict, entities: dict, store: XMLStore) -> dict | None:
    """New-taxonomy dispatch. Returns None (not a result dict) if *intent*
    hasn't been migrated to the new handler set yet — callers should fall
    back to the legacy dispatch() in that case, not treat None as a result.
    """
    if isinstance(intent, str):
        try:
            intent = Intent(intent)
        except ValueError:
            return None
    handler = NEW_INTENT_TO_HANDLER.get(intent)
    if handler is None:
        return None
    return handler(scope, entities, store)


__all__ = [
    "dispatch", "HANDLERS", "INTENT_TO_HANDLER", "handle_unknown",
    "dispatch2", "NEW_INTENT_TO_HANDLER", "handle_unknown_new",
]
