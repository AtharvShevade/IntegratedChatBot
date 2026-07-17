"""Canonical ~48-intent catalog for the expanded db_qa Q&A layer.

Source: the user-supplied access-tiered question catalog (also saved
verbatim at backend/db_qa/app_db_questions.json), collapsed so each
admin/self question pair becomes ONE intent plus a `target_type` entity,
instead of two separate intents.

target_type values:
    self         — asking about the caller's own record. Always allowed.
    other_user   — asking about a specific OTHER user. Admin only.
    department   — asking about a specific (or all) department(s). Admin only.
    role         — asking about a specific (or all) role(s). Admin only.
    return       — reference data about a return/report. Generally allowed;
                   department-level access questions still scope through
                   auth_service.get_allowed_form_ids().
    system_wide  — system-wide aggregate/list question with no single-entity
                   target. Admin only.

This module is pure data (no regex, no handler wiring) — intent_classifier.py
still owns pattern matching; access_control.py and query_handlers/ consume
Intent/IntentSpec by name.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Intent(str, Enum):
    # USER
    USER_PROFILE = "user_profile"
    USER_FIELD = "user_field"
    USER_LIST = "user_list"
    USERS_BY_DEPARTMENT = "users_by_department"
    USERS_BY_ROLE = "users_by_role"
    USERS_WITH_ROLES_AND_DEPARTMENTS = "users_with_roles_and_departments"

    # DEPARTMENT
    DEPARTMENT_LIST = "department_list"
    DEPARTMENT_PROFILE = "department_profile"
    DEPARTMENT_RETURNS = "department_returns"
    DEPARTMENTS_WITH_RETURN_ACCESS = "departments_with_return_access"
    DEPARTMENT_HAS_RETURN = "department_has_return"

    # ROLE
    ROLE_LIST = "role_list"
    ROLE_PROFILE = "role_profile"
    ROLE_USERS = "role_users"
    ROLE_PEER_COUNT = "role_peer_count"

    # ROLE_ACCESS
    PERMISSION_PROFILE = "permission_profile"
    PERMISSION_CHECK = "permission_check"
    ROLES_WITH_PERMISSION = "roles_with_permission"
    ROLE_MODULE_ACCESS = "role_module_access"
    ROLE_PERMISSION_DIFF = "role_permission_diff"

    # USER_LEVEL
    USER_LEVEL_LIST = "user_level_list"
    USER_LEVEL_SELF = "user_level_self"

    # PERIOD
    PERIOD_LIST = "period_list"
    PERIOD_LOOKUP = "period_lookup"
    RETURNS_BY_FREQUENCY = "returns_by_frequency"

    # XBRL_RETURNS
    RETURN_LIST = "return_list"
    RETURN_PROFILE = "return_profile"
    RETURN_FIELD = "return_field"
    RETURN_VALIDATION_CONFIG = "return_validation_config"
    RETURNS_SUBMITTABLE_BY_DEPT = "returns_submittable_by_dept"
    NEXT_REPORTING_DATE = "next_reporting_date"
    REPORTS_FILED_IN_RANGE = "reports_filed_in_range"
    REPORTS_UPCOMING_IN_RANGE = "reports_upcoming_in_range"
    MONTHLY_FILING_STATUS = "monthly_filing_status"

    # NON_XBRL_RETURNS
    NONXBRL_RETURN_LIST = "nonxbrl_return_list"
    NONXBRL_RETURN_PROFILE = "nonxbrl_return_profile"

    # DEPT_RETURN_MAPPING
    DEPT_RETURN_ACCESS_MATRIX = "dept_return_access_matrix"
    MY_RETURN_ACCESS = "my_return_access"
    DEPT_FULL_RETURN_LIST = "dept_full_return_list"

    # INSTANCE_LOG
    SUBMISSION_STATUS = "submission_status"
    SUBMISSION_LIST = "submission_list"
    SUBMISSION_DETAIL = "submission_detail"
    SUBMISSIONS_FOR_RETURN = "submissions_for_return"
    MY_SUBMISSION_HISTORY = "my_submission_history"

    # MENU_OPTIONS
    MENU_LIST = "menu_list"
    MODULE_DETAIL = "module_detail"
    MODULE_CHILDREN = "module_children"

    # AUDIT_SECURITY
    AUDIT_HISTORY = "audit_history"
    AUDIT_ENTITY_TRAIL = "audit_entity_trail"
    SECURITY_EVENTS = "security_events"
    LOG_QUERY = "log_query"

    # CROSS_ENTITY
    USER_ACCESS_SUMMARY = "user_access_summary"
    CROSS_ENTITY_QUERY = "cross_entity_query"

    # Reference data — kept as-is, no admin tiering
    BANK_INFO = "bank_info"
    SEGMENT_INFO = "segment_info"
    NOTIFICATION_QUERY = "notification_query"


@dataclass(frozen=True)
class IntentSpec:
    description: str
    target_types: tuple[str, ...] = ()
    required_entities: tuple[str, ...] = ()
    optional_entities: tuple[str, ...] = ()


INTENT_SPECS: dict[Intent, IntentSpec] = {

    # ── USER ─────────────────────────────────────────────────────────────
    Intent.USER_PROFILE: IntentSpec(
        "Full profile for self or another user",
        target_types=("self", "other_user"),
        optional_entities=("target_user",),
    ),
    Intent.USER_FIELD: IntentSpec(
        "A single field of self or another user's profile "
        "(email, mobile, login_id, user_code, created_date, created_by, "
        "last_login, failed_login_count, status, password_date)",
        target_types=("self", "other_user"),
        required_entities=("field",),
        optional_entities=("target_user",),
    ),
    Intent.USER_LIST: IntentSpec(
        "List/count users — all, active, inactive, never logged in, "
        "failed login, duplicate email, stale password",
        target_types=("system_wide",),
        optional_entities=("query_type",),
    ),
    Intent.USERS_BY_DEPARTMENT: IntentSpec(
        "Which users belong to a given department",
        target_types=("department",),
        required_entities=("target_department",),
    ),
    Intent.USERS_BY_ROLE: IntentSpec(
        "Which users are assigned a given role",
        target_types=("role",),
        required_entities=("target_role",),
    ),
    Intent.USERS_WITH_ROLES_AND_DEPARTMENTS: IntentSpec(
        "All users with their role and department in one list",
        target_types=("system_wide",),
    ),

    # ── DEPARTMENT ───────────────────────────────────────────────────────
    Intent.DEPARTMENT_LIST: IntentSpec(
        "List/count departments — all, active, inactive, most/fewest "
        "returns, no returns, with return counts",
        target_types=("system_wide",),
        optional_entities=("query_type",),
    ),
    Intent.DEPARTMENT_PROFILE: IntentSpec(
        "Department id/email/info for self's or a named department",
        target_types=("self", "department"),
        optional_entities=("target_department",),
    ),
    Intent.DEPARTMENT_RETURNS: IntentSpec(
        "XBRL/non-XBRL returns (and counts) accessible to self's or a "
        "named department",
        target_types=("self", "department"),
        optional_entities=("target_department", "xbrl_type"),
    ),
    Intent.DEPARTMENTS_WITH_RETURN_ACCESS: IntentSpec(
        "Which departments (and how many) have access to a given return",
        target_types=("return",),
        required_entities=("target_return",),
    ),
    Intent.DEPARTMENT_HAS_RETURN: IntentSpec(
        "Does self's or a named department have access to a given return",
        target_types=("self", "department"),
        required_entities=("target_return",),
        optional_entities=("target_department",),
    ),

    # ── ROLE ─────────────────────────────────────────────────────────────
    Intent.ROLE_LIST: IntentSpec(
        "List/count roles — all, active, inactive, most users, per-role "
        "user counts, existence check",
        target_types=("system_wide",),
        optional_entities=("query_type", "target_role"),
    ),
    Intent.ROLE_PROFILE: IntentSpec(
        "Role name/id/active status for self's or a named role",
        target_types=("self", "role"),
        optional_entities=("target_role",),
    ),
    Intent.ROLE_USERS: IntentSpec(
        "Which users (and how many) have a given role",
        target_types=("role",),
        required_entities=("target_role",),
    ),
    Intent.ROLE_PEER_COUNT: IntentSpec(
        "How many other users share my role",
        target_types=("self",),
    ),

    # ── ROLE_ACCESS ──────────────────────────────────────────────────────
    Intent.PERMISSION_PROFILE: IntentSpec(
        "All permissions/modules for self or a named role, incl. "
        "'what do I NOT have access to'",
        target_types=("self", "role"),
        optional_entities=("target_role",),
    ),
    Intent.PERMISSION_CHECK: IntentSpec(
        "Can self or a named role perform a given action on a given module",
        target_types=("self", "role"),
        required_entities=("action",),
        optional_entities=("module", "target_role"),
    ),
    Intent.ROLES_WITH_PERMISSION: IntentSpec(
        "Which roles can perform a given action (optionally on a given "
        "module) — full access, view-only, no edit/create, etc.",
        target_types=("system_wide",),
        required_entities=("action",),
        optional_entities=("module",),
    ),
    Intent.ROLE_MODULE_ACCESS: IntentSpec(
        "Role<->module access — list modules for a role, or which roles "
        "access a named module (NXQueryBuilder, SDMX, Balance Sheet, etc.)",
        target_types=("role", "system_wide"),
        optional_entities=("target_role", "module"),
    ),
    Intent.ROLE_PERMISSION_DIFF: IntentSpec(
        "Difference in permissions between two named roles",
        target_types=("role",),
        required_entities=("target_role", "role_b"),
    ),

    # ── USER_LEVEL ───────────────────────────────────────────────────────
    Intent.USER_LEVEL_LIST: IntentSpec(
        "User levels defined, count, active status, or users at a given "
        "level (L1/L2/L3)",
        target_types=("system_wide",),
        optional_entities=("level",),
    ),
    Intent.USER_LEVEL_SELF: IntentSpec(
        "My own user level, its meaning, or its level id",
        target_types=("self",),
    ),

    # ── PERIOD ───────────────────────────────────────────────────────────
    Intent.PERIOD_LIST: IntentSpec(
        "All reporting periods/frequencies, count, EBR codes, or "
        "QF-vs-QAD comparison",
        target_types=("system_wide",),
    ),
    Intent.PERIOD_LOOKUP: IntentSpec(
        "Period name/id lookup, EBR code, advance-notification days for "
        "a named period, or the id for a named frequency",
        target_types=("system_wide",),
        optional_entities=("period_name", "period_id"),
    ),
    Intent.RETURNS_BY_FREQUENCY: IntentSpec(
        "Which returns (mine or all) are filed monthly/quarterly/annually",
        target_types=("self", "system_wide"),
        required_entities=("period_name",),
    ),

    # ── XBRL_RETURNS ─────────────────────────────────────────────────────
    Intent.RETURN_LIST: IntentSpec(
        "List/count XBRL returns — all, active, inactive, CIMS-enabled, "
        "IsTBL, by category (DPSS/DBS/DBR), due > N days; or which "
        "returns I can submit",
        target_types=("self", "system_wide"),
        optional_entities=("query_type", "category"),
    ),
    Intent.RETURN_PROFILE: IntentSpec(
        "Full detail for a named return — version, XSD path, base excel, "
        "table linkbase path, alt name, namespaces, due days, encryption, "
        "formula/schema-calc flags, CIMS flag, frequency, internal form id",
        target_types=("return",),
        required_entities=("target_return",),
    ),
    Intent.RETURN_FIELD: IntentSpec(
        "A single field of a named return (return id, internal form id, "
        "reporting period/frequency, due days, version, xsd path) — NOT "
        "the full profile dump",
        target_types=("return",),
        required_entities=("target_return", "field"),
    ),
    Intent.RETURN_VALIDATION_CONFIG: IntentSpec(
        "Validation configuration for a return or system-wide — formula, "
        "schema-calc, RBI validation, large-validator, cross-report "
        "validation, business rules, BSR mandatory header fields",
        target_types=("self", "system_wide"),
        optional_entities=("target_return", "detail_type"),
    ),
    Intent.RETURNS_SUBMITTABLE_BY_DEPT: IntentSpec(
        "Which XBRL returns can self or a named department submit; which "
        "departments can submit a named return (e.g. DPSS09, DBR01)",
        target_types=("self", "department", "return"),
        optional_entities=("target_department", "target_return"),
    ),
    Intent.NEXT_REPORTING_DATE: IntentSpec(
        "Next reporting/period-end date and submission due date for a named "
        "return, computed from its period frequency (period.xml) and DueDays",
        target_types=("return",),
        required_entities=("target_return",),
    ),
    Intent.REPORTS_FILED_IN_RANGE: IntentSpec(
        "Which XBRL or non-XBRL returns were actually submitted (InstanceLog "
        "entries) between two dates — scoped to the caller's own department "
        "for regular users; admins may additionally ask about a named "
        "department or system-wide across all departments — "
        "'show me all reports filed between X and Y'",
        target_types=("self", "department", "system_wide"),
        required_entities=("date_from", "date_to"),
        optional_entities=("target_department", "xbrl_type"),
    ),
    Intent.REPORTS_UPCOMING_IN_RANGE: IntentSpec(
        "Which XBRL or non-XBRL returns have a computed next reporting/due "
        "date falling between two dates — scoped to the caller's own "
        "department for regular users; admins may additionally ask about a "
        "named department or system-wide across all departments — "
        "'what reports are coming up between X and Y'",
        target_types=("self", "department", "system_wide"),
        required_entities=("date_from", "date_to"),
        optional_entities=("target_department", "xbrl_type"),
    ),
    Intent.MONTHLY_FILING_STATUS: IntentSpec(
        "Per-return filed/not-filed roll-up for a single named or relative "
        "calendar month (e.g. 'June 2025', 'this month', 'last month') — "
        "only returns whose reporting frequency has a period-end in that "
        "month are considered due, each shown as Filed (an InstanceLog "
        "entry exists for that period) or Not Filed — scoped to the "
        "caller's own department for regular users; admins may "
        "additionally ask about a named department or system-wide across "
        "all departments — 'what's my XBRL filing status for June 2025?', "
        "'what's the non-XBRL status for this month?'",
        target_types=("self", "department", "system_wide"),
        required_entities=("month_year",),
        optional_entities=("target_department", "xbrl_type"),
    ),

    # ── NON_XBRL_RETURNS ─────────────────────────────────────────────────
    Intent.NONXBRL_RETURN_LIST: IntentSpec(
        "List/count non-XBRL returns — no due days, with ids+frequencies, "
        "folder structure, or which departments can access a named one; "
        "or how many non-XBRL returns I can access",
        target_types=("self", "department", "system_wide"),
        optional_entities=("query_type", "target_department"),
    ),
    Intent.NONXBRL_RETURN_PROFILE: IntentSpec(
        "Detail for a named non-XBRL return — base template, period, due "
        "days, CIMS flag, job processing id",
        target_types=("self", "return"),
        optional_entities=("target_return",),
    ),

    # ── DEPT_RETURN_MAPPING ──────────────────────────────────────────────
    Intent.DEPT_RETURN_ACCESS_MATRIX: IntentSpec(
        "Cross-department ranking — which return is accessible by the "
        "most/all departments, which department has the most returns",
        target_types=("system_wide",),
    ),
    Intent.MY_RETURN_ACCESS: IntentSpec(
        "My department's full accessible-return list, count, or whether "
        "it has access to a specific return",
        target_types=("self",),
        optional_entities=("target_return",),
    ),
    Intent.DEPT_FULL_RETURN_LIST: IntentSpec(
        "Complete XBRL + non-XBRL return list for a named department",
        target_types=("department",),
        required_entities=("target_department",),
    ),

    # ── INSTANCE_LOG ─────────────────────────────────────────────────────
    Intent.SUBMISSION_STATUS: IntentSpec(
        "Status of a specific submission id, mine or another user's",
        target_types=("self", "other_user"),
        required_entities=("submission_id",),
        optional_entities=("target_user",),
    ),
    Intent.SUBMISSION_LIST: IntentSpec(
        "Filtered submission list — pending/approved/audited/rejected, "
        "CIMS ok/failed, un-audited, has-error-doc, by return, by period, "
        "by date range, by user, count",
        target_types=("self", "other_user", "return", "system_wide"),
        optional_entities=("status", "target_return", "date_range", "target_user", "period_name"),
    ),
    Intent.SUBMISSION_DETAIL: IntentSpec(
        "Full detail for a specific submission — instance doc path, "
        "rendered path, CIMS status, rejection reason, comments, error "
        "doc, approved by/when",
        target_types=("self", "other_user"),
        required_entities=("submission_id",),
        optional_entities=("target_user",),
    ),
    Intent.SUBMISSIONS_FOR_RETURN: IntentSpec(
        "Who submitted a named return, most-recent submission + outcome, "
        "count this quarter",
        target_types=("return",),
        required_entities=("target_return",),
    ),
    Intent.MY_SUBMISSION_HISTORY: IntentSpec(
        "Which returns I've submitted so far, or whether I've ever "
        "submitted a named return",
        target_types=("self",),
        optional_entities=("target_return",),
    ),

    # ── MENU_OPTIONS ─────────────────────────────────────────────────────
    Intent.MENU_LIST: IntentSpec(
        "Top-level menu count, all modules, new-tab modules, my visible "
        "menu, or modules under a named section (ETL/Workflow, Data "
        "Management)",
        target_types=("self", "system_wide"),
        optional_entities=("section",),
    ),
    Intent.MODULE_DETAIL: IntentSpec(
        "Rank, resource label, icon, parent module, or availability of a "
        "named module/option id",
        target_types=("self", "system_wide"),
        optional_entities=("module", "option_id"),
    ),
    Intent.MODULE_CHILDREN: IntentSpec(
        "Child modules under a named parent module",
        target_types=("system_wide",),
        required_entities=("module",),
    ),

    # ── AUDIT_SECURITY ───────────────────────────────────────────────────
    Intent.AUDIT_HISTORY: IntentSpec(
        "My own recent changes, or a named user's changes/profile-change "
        "history in the last N days",
        target_types=("self", "other_user"),
        optional_entities=("target_user", "days_n"),
    ),
    Intent.AUDIT_ENTITY_TRAIL: IntentSpec(
        "Audit trail for a department or return, or who last modified a "
        "module/entity, or who last approved/actioned a submission",
        target_types=("department", "return", "system_wide"),
        optional_entities=("target_department", "target_return", "submission_id"),
    ),
    Intent.SECURITY_EVENTS: IntentSpec(
        "Password resets, pending reset requests, exceeded failed-login "
        "counts, deactivated users+when, or my own account-lock status",
        target_types=("self", "other_user", "system_wide"),
        optional_entities=("target_user", "query_type"),
    ),
    Intent.LOG_QUERY: IntentSpec(
        "Upload failures (mine/all/last N days), SDMX logs for a return, "
        "cross-validation errors for a return, or errors for a submission",
        target_types=("self", "other_user", "return", "system_wide"),
        optional_entities=("target_return", "submission_id", "days_n", "log_type"),
    ),

    # ── CROSS_ENTITY ─────────────────────────────────────────────────────
    Intent.USER_ACCESS_SUMMARY: IntentSpec(
        "Full profile summary (role + department + accessible returns) "
        "for self or a named user; what a user can do / approve / create",
        target_types=("self", "other_user"),
        optional_entities=("target_user",),
    ),
    Intent.CROSS_ENTITY_QUERY: IntentSpec(
        "Multi-entity joins — who in a department can approve, role+dept "
        "combo, role+return access, broadest-access combo, "
        "audit-approval rights across departments, active users not "
        "logged in > N days, most recent submitter of a return, users who "
        "can generate SDMX for a return, users with both data-prep and "
        "approval rights",
        target_types=("department", "role", "return", "system_wide"),
        optional_entities=("target_department", "target_role", "target_return", "days_n"),
    ),

    # ── Reference data (no admin tiering — single-tenant/global facts) ──
    Intent.BANK_INFO: IntentSpec(
        "Bank name/code/type/CRR configured in the system",
        target_types=("self",),
    ),
    Intent.SEGMENT_INFO: IntentSpec(
        "Segment types defined in the system",
        target_types=("self",),
    ),
    Intent.NOTIFICATION_QUERY: IntentSpec(
        "Notification configuration — which returns have notifications, "
        "email/SMS format for a type, users receiving notifications for "
        "a return; or my own notification settings for a return",
        target_types=("self", "return", "system_wide"),
        optional_entities=("target_return", "notification_type"),
    ),
}


# Sanity: every Intent member has a spec, and vice versa.
assert set(Intent) == set(INTENT_SPECS.keys()), (
    "Intent enum and INTENT_SPECS must define exactly the same members"
)
