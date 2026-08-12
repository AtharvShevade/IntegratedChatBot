"""Database Q&A router — bridges LLM intent detection and query execution.

This module handles:
1. LLM-extracted intent validation
2. XML data fetching via XMLStore
3. Query handler dispatch
4. Optional LLM beautification
5. Response population

The DB Q&A pipeline is invoked early in the decision pipeline when the LLM
detects intents starting with "db_" (db_my_profile, db_list_users, etc.).
"""
from __future__ import annotations

import logging
from typing import Generator

import backend.config as config
from backend.db_qa import access_control, query_handlers, templates, xml_store
from backend.db_qa.intent_classifier import classify
from backend.db_qa.beautifier import beautify_stream
from backend.models import ChatResponse
from backend.utils.debug import debug_log
from backend.utils.intent_log import log_intent_outcome

logger = logging.getLogger(__name__)


# Map regex-classifier intents to unified db_* intents used by query_handlers.
_CLASSIFIER_TO_DB_INTENT = {
    "MY_PROFILE":           "db_my_profile",
    "MY_DEPARTMENT":        "db_my_department",
    "MY_ROLE":              "db_my_role",
    "MY_ROLE_PERMISSIONS":  "db_my_permissions",
    "MY_EMAIL":             "db_my_email",
    "MY_MOBILE":            "db_my_mobile",
    "MY_STATUS":            "db_my_status",
    "MY_CREATED_DATE":      "db_my_created_date",
    "MY_PASSWORD_DATE":     "db_my_password_date",
    "MY_LOGIN_ID":          "db_my_login_id",
    "MY_USER_CODE":         "db_my_user_code",
    "MY_USER_LEVEL":        "db_my_user_level",
    "MY_ROLE_PEER_COUNT":   "db_my_role_peers",
    "MY_LAST_LOGIN":        "db_my_last_login",
    "MY_FAILED_LOGINS":     "db_my_failed_logins",
    "MY_SUBMISSIONS":       "db_my_submissions",
    "MY_DEPT_RETURNS":      "db_my_dept_returns",
    # Audit / logs (self-service)
    "MY_AUDIT_LOG":         "db_my_audit",
    "MY_UPLOAD_LOG":        "db_my_uploads",
    "MY_CROSS_VAL_LOG":     "db_my_cross_val",
    # User lists
    "USER_LIST":            "db_list_users",
    "USER_LIST_ACTIVE":     "db_list_users",
    "USER_LIST_INACTIVE":   "db_list_users",
    "USER_COUNT":           "db_list_users",
    "USER_LEVEL_LIST":      "db_user_levels",
    "USER_BY_DEPT":         "db_user_by_dept",
    "USER_BY_ROLE":         "db_user_by_role",
    "USER_NEVER_LOGIN":     "db_user_never_login",
    "USER_FAILED_LOGIN":    "db_user_failed_login",
    "USER_DUPLICATE_EMAIL": "db_user_dupe_email",
    # Reference data
    "DEPT_LIST":            "db_list_departments",
    "DEPT_INFO":            "db_department_info",
    "DEPT_RETURNS":         "db_dept_returns",
    "ROLE_LIST":            "db_list_roles",
    "ROLE_PERMISSIONS":     "db_role_info",
    "ROLE_USERS":           "db_role_users",
    "PERMISSION_CHECK":     "db_permission_check",
    "RETURNS_LIST":         "db_list_returns",          # fixed (was RETURN_LIST)
    "NON_XBRL_LIST":        "db_non_xbrl_list",
    "RETURNS_BY_PERIOD":    "db_returns_by_period",
    "RETURNS_DETAILS":      "db_list_returns",
    "VALIDATION_RETURNS":   "db_validation_returns",
    "PERIOD_LIST":          "db_period_list",
    "MENU_LIST":            "db_menu_list",
    "NOTIFICATION_LIST":    "db_notifications",
    "BANK_INFO":            "db_bank_info",
    "SEGMENT_INFO":         "db_segment_info",
    # Lookup by target
    "USER_PROFILE":         "db_user_info",
    # Submission / instance log
    "SUBMISSION_LIST":      "db_submission_list",
    "SUBMISSION_PENDING":   "db_my_submissions",
    "SUBMISSION_APPROVED":  "db_my_submissions",
    "SUBMISSION_STATUS":    "db_my_submissions",
    # Admin audit / logs
    "AUDIT_LOG":            "db_audit_log",
    "CROSS_VAL_LOG":        "db_cross_val_log",
    "UPLOAD_LOG":           "db_upload_log",
}


def check_new_taxonomy_intent(message: str) -> tuple[str | None, dict]:
    """Detect a new-taxonomy (backend.db_qa.intents.taxonomy.Intent) match
    via REGEX ONLY — fast, synchronous, no LLM call.

    Used by decide()'s cheap look-ahead routing probes (deciding whether a
    message even looks like a DB Q&A question, before choosing between
    SQL/conversational/DB-QA branches) where a synchronous, low-latency
    check is required. For the actual dispatch call site that executes a
    DB Q&A handler, use check_new_taxonomy_intent_full() instead, which
    adds the embedding-similarity + LLM-disambiguation tiers on a regex
    miss.

    Returns (intent_value, params) with params already containing
    "target_type", or (None, {}) if nothing in the new rule set matched —
    callers should fall back to check_db_qa_intent() in that case.
    """
    from backend.db_qa.new_intent_classifier import classify_new
    intent, params, _target_type = classify_new(message)
    log_intent_outcome(
        query=message, tier="regex_new_taxonomy",
        intent=intent.value if intent is not None else None,
        found=intent is not None,
    )
    if intent is None:
        return None, {}
    return intent.value, params


async def check_new_taxonomy_intent_full(message: str) -> tuple[str | None, dict]:
    """Detect a new-taxonomy Intent match via the FULL tiered pipeline:
    regex -> embedding similarity -> narrow LLM disambiguation.

    Unlike check_new_taxonomy_intent() (regex only, sync, cheap), this is
    async and may issue an embedding lookup and/or a narrow LLM call —
    use it only at the actual dispatch call site where a DB Q&A result is
    about to be executed, not in cheap routing probes.

    Returns (intent_value, params), or (None, {}) if nothing matched at
    any tier — callers should fall back to check_db_qa_intent() in that
    case, same as check_new_taxonomy_intent().
    """
    from backend.db_qa.new_intent_classifier import classify_new_with_semantic_tiers
    intent, params, _target_type, tier = await classify_new_with_semantic_tiers(message)
    log_intent_outcome(
        query=message, tier=tier,
        intent=intent.value if intent is not None else None,
        found=intent is not None,
    )
    if intent is None:
        return None, {}
    return intent.value, params


def check_db_qa_intent(message: str) -> tuple[str | None, dict]:
    """Detect DB Q&A intent using regex classifier and map to db_* schema.

    Returns:
        (db_intent, params) where db_intent is None when no DB intent matches.
    """
    raw_intent, params = classify(message)
    # ── Debug trace: classifier result ─────────────────────────────────────────
    _mapped = _CLASSIFIER_TO_DB_INTENT.get(raw_intent or "", "NOT MAPPED") if raw_intent else "N/A"
    _status = (
        "OK" if (raw_intent and raw_intent != "UNKNOWN" and _mapped != "NOT MAPPED")
        else ("no regex pattern matched" if (not raw_intent or raw_intent == "UNKNOWN")
              else f"raw intent {raw_intent!r} has no db_* handler mapping")
    )
    debug_log(
        "DB QA ROUTER — check_db_qa_intent",
        question=message[:120],
        raw_intent=raw_intent or "NONE",
        db_intent_mapped=_mapped,
        status=_status,
    )
    if not raw_intent or raw_intent == "UNKNOWN":
        log_intent_outcome(query=message, tier="regex_legacy", intent=None, found=False)
        return None, {}

    db_intent = _CLASSIFIER_TO_DB_INTENT.get(raw_intent)
    if not db_intent:
        log_intent_outcome(
            query=message, tier="regex_legacy", intent=None, found=False,
            raw_intent=raw_intent,
        )
        return None, {}

    mapped_params = dict(params or {})

    # Keep parameter shape compatible with current handler wrappers.
    if raw_intent == "USER_LIST_ACTIVE":
        mapped_params["query_type"] = "active"
    elif raw_intent == "USER_LIST_INACTIVE":
        mapped_params["query_type"] = "inactive"
    elif raw_intent == "USER_COUNT":
        mapped_params["query_type"] = "count"
    elif raw_intent == "USER_LIST":
        mapped_params["query_type"] = "all"
    elif raw_intent == "USER_NEVER_LOGIN":
        mapped_params["query_type"] = "never_login"
    elif raw_intent == "USER_FAILED_LOGIN":
        mapped_params["query_type"] = "failed_login"
    elif raw_intent == "USER_DUPLICATE_EMAIL":
        mapped_params["query_type"] = "duplicate_email"
    elif raw_intent == "NON_XBRL_LIST":
        mapped_params["xbrl_type"] = "non_xbrl"
    elif raw_intent == "SUBMISSION_PENDING":
        mapped_params["query_type"] = "pending"
    elif raw_intent == "SUBMISSION_APPROVED":
        mapped_params["query_type"] = "approved"

    # Normalize department key used by the db_* flow.
    if "target_dept" in mapped_params and "target_department" not in mapped_params:
        mapped_params["target_department"] = mapped_params["target_dept"]

    log_intent_outcome(
        query=message, tier="regex_legacy", intent=db_intent, found=True,
        raw_intent=raw_intent,
    )
    return db_intent, mapped_params


# ── Module-level formatting helpers shared by _format_plain and _build_db_qa_data ─
_FRIENDLY_NAMES: dict[str, str] = {
    "Name":             "Name",
    "LoginId":          "Login ID",
    "UserId":           "User ID",
    "EmailId":          "Email",
    "MobileNo":         "Mobile",
    "RoleName":         "Role",
    "DeptName":         "Department",
    "Status":           "Status",
    "LastLoginDT":      "Last Login",
    "CreatedDate":      "Created On",
    "FailedLoginCount": "Failed Logins",
    "UserCode":         "User Code",
    "ReturnName":       "Return",
    "ReturnCode":       "Return Code",
    "ReturnLabel":      "Return Name",
    "ReturnId":         "Return ID",
    "PeriodName":       "Period",
    "Description":      "Description",
    "OptionName":       "Module",
    "AccessType":       "Access",
    "MenuName":         "Menu",
    "UserName":         "User",
    "GeneratedBy":      "Generated By",
    "StatusLabel":      "Status",
    "SubmittedAt":      "Submitted At",
    "ApprovedBy":       "Approved By",
    "total":            "Total",
    "active":           "Active",
    "inactive":         "Inactive",
    "Frequency":        "Frequency",
    "ExpectedDate":     "Expected Date",
    "Filed":            "Filed",
    "FiledOn":          "Filed On",
    "AuditDateTime":    "Date/Time",
    "AuditType":        "Action",
    "Remark":           "Remark",
    "ReportingDate":    "Reporting Date",
    "GeneratedOn":      "Generated On",
    "Email":            "Email",
    "DeptId":           "Department ID",
    "UserCount":        "User Count",
    # A ranking answer ("which frequency has the most returns") carries its
    # count in the row; without a friendly name and a place in
    # _PRIORITY_COLS the column was silently dropped from the table and the
    # count survived only in the summary sentence.
    "ReturnCount":      "Returns",
    "Frequency":        "Frequency",
    "FrequencyCount":   "Reporting Frequencies",
    "RoleId":           "Role ID",
    "XbrlReturnCount":  "XBRL Returns",
    "NonXbrlReturnCount": "Non-XBRL Returns",
    "TotalReturnCount": "Total Returns",
}

_SKIP_FIELDS: frozenset[str] = frozenset({
    "RoleId", "DeptId", "DepartmentId", "OptionId",
    "FormId", "PeriodId", "Password", "PasswordHash",
    # Raw pipe-delimited return-code lists off Department.xml (e.g.
    # "2014|2033|1032|..."). Never meant for display — department handlers
    # already expand these into proper return rows / XbrlReturnCount /
    # NonXbrlReturnCount / TotalReturnCount, so showing the raw string too
    # just leaks internal storage format alongside the real answer.
    "Forms", "NXForms",
})

# Fields hidden from every table unless the question specifically asked for
# them. Each is paired with the result-meta flag that unhides it (set by the
# handlers that answer that specific question — see _skip_fields).
#
# FailedLoginCount is an operational security counter, not part of a user's
# identity: a general "list all users" table showed a Failed Logins column
# for all 37 rows, which is noise next to Name/Login ID/Email/Department/
# Role/Status/Last Login and reads as an accusation on every row. It is
# still returned in full for the questions that actually ask about it
# ("how many failed login attempts does user X have", "which users have
# failed login attempts"), whose handlers set show_failed_logins.
_CONDITIONAL_FIELDS: dict[str, str] = {
    "DeptId": "show_dept_id",
    "FailedLoginCount": "show_failed_logins",
    # Same story as DeptId: an internal key most questions never ask about,
    # but "what is the role ID of Tester?" asks for exactly this and was
    # answered with a Name/Status row that never showed it.
    "RoleId": "show_role_id",
}


def _skip_fields(sample_record: dict | None = None, show_dept_id: bool = False,
                 show_failed_logins: bool = False, show_role_id: bool = False) -> frozenset[str]:
    # InstanceLog-derived records (submissions) carry both a raw numeric
    # "Status" code (0-11) and a human "StatusLabel" ("New / Pending",
    # "Approved", ...). Displaying both duplicates the "Status" header
    # AND runs the raw code through the User/Department Active/Inactive
    # boolean formatter below (_fmt_val's _STATUS_COLS branch), which is
    # meaningless for a status CODE and rendered almost every row as
    # "Inactive" regardless of its real status. StatusLabel supersedes
    # Status whenever both are present, so skip the raw field.
    # Each conditional field is hidden unless its own meta flag is set —
    # DeptId via "want_dept_id" on the handler's entities, FailedLoginCount
    # via the failed-login handlers. See _CONDITIONAL_FIELDS above.
    shown = {"show_dept_id": show_dept_id, "show_failed_logins": show_failed_logins,
             "show_role_id": show_role_id}
    skip = (_SKIP_FIELDS | set(_CONDITIONAL_FIELDS)) - {
        field for field, flag in _CONDITIONAL_FIELDS.items() if shown[flag]
    }
    if sample_record and "StatusLabel" in sample_record:
        skip = skip | {"Status"}
    return skip

_PRIORITY_COLS: list[str] = [
    "Name", "LoginId", "EmailId", "Email", "MobileNo",
    "DeptName", "RoleName", "Status", "LastLoginDT",
    "ReturnName", "ReturnCode", "ReturnLabel", "ReturnId", "PeriodName",
    "OptionName", "MenuName", "AccessType",
    "UserName", "AuditDateTime", "AuditType", "Remark",
    # FailedLoginCount deliberately absent — it is re-added by _select_cols
    # only when the question asked about it (see _CONDITIONAL_FIELDS).
    "StatusLabel", "CreatedDate",
    "Frequency", "ExpectedDate", "Filed", "FiledOn",
    "UserCount", "ReturnCount", "XbrlReturnCount", "NonXbrlReturnCount", "TotalReturnCount",
]

_COUNT_KEYS: frozenset[str] = frozenset({"total", "active", "inactive"})


def _friendly(key: str) -> str:
    return _FRIENDLY_NAMES.get(key, key.replace("_", " ").title())


_STATUS_COLS: frozenset[str] = frozenset({"Status"})


def _fmt_val(v, col: str | None = None) -> str:
    if v is None or v == "" or v == []:
        return "\u2014"
    s = str(v).strip()
    if col == "Filed":
        # Checked before the generic true/false->Active/Inactive mapping
        # below \u2014 that mapping is meant for Status-style fields and would
        # otherwise render a not-filed return as "Inactive", which reads
        # as the return itself being disabled rather than simply not yet
        # filed for the period in question.
        return "Filed" if s.lower() == "true" else "Not Filed"
    if col in _STATUS_COLS:
        from backend.db_qa.xml_store import is_active_status
        return "Active" if is_active_status(s) else "Inactive"
    if s.lower() == "true":
        return "Active"
    if s.lower() == "false":
        return "Inactive"
    return s or "\u2014"


def _select_cols(records: list[dict], show_dept_id: bool = False,
                 show_failed_logins: bool = False, show_role_id: bool = False) -> list[str]:
    skip   = _skip_fields(records[0], show_dept_id, show_failed_logins, show_role_id)
    sample = [k for k in records[0].keys() if k not in skip]
    cols   = [c for c in _PRIORITY_COLS if c in sample]
    # No conditional field is one of the curated _PRIORITY_COLS (they are
    # normally hidden), so each has to be added explicitly when a question
    # asked for it — placed first, since it was the thing the user actually
    # asked about.
    shown = {"show_dept_id": show_dept_id, "show_failed_logins": show_failed_logins,
             "show_role_id": show_role_id}
    for field, flag in _CONDITIONAL_FIELDS.items():
        if shown[flag] and field in sample and field not in cols:
            cols = [field] + cols
    return cols or sample[:5]


def _format_plain(result: dict) -> str:
    """Build a readable plain-text fallback when the LLM beautifier is disabled."""
    summary = result.get("summary", "No data found.")
    records = result.get("records", [])
    label   = result.get("label", "")
    show_dept_id = bool(result.get("meta", {}).get("show_dept_id"))
    show_failed_logins = bool(result.get("meta", {}).get("show_failed_logins"))
    show_role_id = bool(result.get("meta", {}).get("show_role_id"))

    if not records:
        return summary

    if len(records) == 1 and all(k in _COUNT_KEYS for k in records[0]):
        r = records[0]
        return (
            f"{label}\n\n"
            f"Total: {r.get('total', chr(8212))}   "
            f"Active: {r.get('active', chr(8212))}   "
            f"Inactive: {r.get('inactive', chr(8212))}"
        )

    if len(records) == 1:
        rec   = records[0]
        lines = [label, ""]
        skip  = _skip_fields(rec, show_dept_id, show_failed_logins, show_role_id)
        for k, v in rec.items():
            if k in skip:
                continue
            fv = _fmt_val(v, k)
            if fv != "\u2014":
                lines.append(f"  {_friendly(k)}: {fv}")
        return "\n".join(lines)

    cols   = _select_cols(records, show_dept_id, show_failed_logins, show_role_id)
    hdrs   = [_friendly(c) for c in cols]
    widths = [
        max(len(h), max((len(_fmt_val(r.get(c), c)) for r in records), default=0))
        for h, c in zip(hdrs, cols)
    ]

    def _row(vals: list[str]) -> str:
        return "| " + " | ".join(v.ljust(widths[i]) for i, v in enumerate(vals)) + " |"

    lines = [
        f"{label}  ({len(records)} records)", "",
        _row(hdrs),
        "|" + "|".join("-" * (w + 2) for w in widths) + "|",
        *[_row([_fmt_val(r.get(c), c) for c in cols]) for r in records],
        "", summary,
    ]
    return "\n".join(lines)


_LIST_SHAPED_INTENTS: frozenset[str] = frozenset({
    "users_by_department", "users_by_role", "role_users",
})


def _is_list_shaped(intent: str | None) -> bool:
    """True when *intent* always represents a filtered collection (even if
    it happens to match only one row right now) rather than a single-entity
    lookup — these must keep the compact multi-column table shape instead
    of falling into the single-record full-detail view."""
    if not intent:
        return False
    return intent.endswith("_list") or intent in _LIST_SHAPED_INTENTS


def _build_db_qa_data(result: dict, intent: str | None = None) -> dict:
    """Return structured table data consumed by the frontend DbQaResultBlock component.

    The frontend renders this as a proper HTML table rather than pre-formatted text.
    Schema::

        {
            label:    str,          # section title (suppressed in most chat views)
            summary:  str,          # one-line natural-language result description
            cols:     list[str],    # ordered internal column keys
            headers:  list[str],    # friendly display header labels
            records:  list[dict],   # filtered + formatted rows (keyed by cols)
            is_count: bool,         # True for USER_COUNT-style summary rows
        }
    """
    records = result.get("records", [])
    label   = result.get("label", "")
    summary = result.get("summary", "No data found.")
    show_dept_id = bool(result.get("meta", {}).get("show_dept_id"))
    show_failed_logins = bool(result.get("meta", {}).get("show_failed_logins"))
    show_role_id = bool(result.get("meta", {}).get("show_role_id"))

    if not records:
        return {
            "label": label, "summary": summary,
            "cols": [], "headers": [], "records": [], "is_count": False,
        }

    # Count-only result (e.g. USER_COUNT)
    if len(records) == 1 and all(k in _COUNT_KEYS for k in records[0]):
        r = records[0]
        return {
            "label":    label,
            "summary":  summary,
            "cols":     ["total", "active", "inactive"],
            "headers":  ["Total", "Active", "Inactive"],
            "records":  [{
                "total":    _fmt_val(r.get("total"), "total"),
                "active":   _fmt_val(r.get("active"), "active"),
                "inactive": _fmt_val(r.get("inactive"), "inactive"),
            }],
            "is_count": True,
        }

    # Single record — only non-empty, non-ID fields (skipped for list-shaped
    # intents, e.g. "list of active users" matching exactly one user must
    # still render as a compact one-row table, not a full profile dump).
    if len(records) == 1 and not _is_list_shaped(intent):
        rec  = records[0]
        skip = _skip_fields(rec, show_dept_id, show_failed_logins, show_role_id)
        cols = [k for k in rec if k not in skip and _fmt_val(rec.get(k), k) != "\u2014"]
        return {
            "label":    label,
            "summary":  summary,
            "cols":     cols,
            "headers":  [_friendly(c) for c in cols],
            "records":  [{c: _fmt_val(rec.get(c), c) for c in cols}],
            "is_count": False,
        }

    # Multiple records
    cols = _select_cols(records, show_dept_id, show_failed_logins, show_role_id)
    return {
        "label":    label,
        "summary":  summary,
        "cols":     cols,
        "headers":  [_friendly(c) for c in cols],
        "records":  [{c: _fmt_val(r.get(c), c) for c in cols} for r in records],
        "is_count": False,
    }


def handle_db_qa_query(
    message: str,
    intent: str,
    params: dict,
    user_id: str,
    role_id: str,
    beautify: bool = False,
    model: str = "phi3:mini",
    login_id: str | None = None,
) -> dict:
    """Execute DB Q&A intent using LLM-extracted parameters.

    This handler is called when the LLM detects an intent starting with "db_"
    (e.g., db_my_profile, db_list_users, db_list_departments), OR when a
    query has been classified onto one of the new backend.db_qa.intents.
    taxonomy.Intent names (e.g. "user_profile", "department_returns").

    Args:
        message: Original user question
        intent: LLM-detected legacy db_* intent, OR a new Intent.value string
        params: LLM-extracted entities dict containing:
                - target_user: username/user ID if asking about specific user
                - target_department: department name if mentioned
                - target_role: role name if mentioned
                - query_type: filter type ("active", "inactive", "all", "details", "count")
                - target_type: for new-taxonomy intents — self/other_user/
                  department/role/return/system_wide (see access_control.py)
        user_id: Current user's ID (for self-service checks)
        role_id: Current user's role ID (for admin access checks)
        beautify: Whether to use LLM for formatting results
        model: Ollama model to use for beautification
        login_id: Caller's LoginId string, when known independently of
                  user_id (some call sites only have a numeric UserId or a
                  session GUID in user_id — see agent/__init__.py's
                  final_user_id resolution). Falls back to user_id if omitted.

    Returns:
        Response dict compatible with ChatResponse model with db_* fields populated
    """
    try:
        # Feature gate: gracefully return if not configured
        if not config.app_db_base_path():
            logger.warning("[DB_QA] APP_DB_BASE_PATH not configured, returning disabled response")
            return {
                "result": "Database Q&A feature is not configured.",
                "db_found": False,
                "result_type": "db_disabled",
            }

        # Instantiate XML data store.
        store = xml_store.XMLStore(config.app_db_base_path())
        # ── Debug trace: log function entry with full identity context ───────────────
        debug_log(
            "DB QA ROUTER — handle_db_qa_query",
            question=message[:120],
            intent=intent,
            user_id_raw=user_id,
            role_id_raw=role_id,
            xml_base_path=config.app_db_base_path(),
        )
        
        # Resolve caller identity robustly: in some integrations user_id may carry
        # LoginId instead of numeric UserId, and role_id may be omitted.
        resolved_user = store.user_by_id(user_id) or store.user_by_name(user_id)
        effective_user_id = resolved_user.get("UserId", user_id) if resolved_user else user_id
        # Treat "0" (the default sentinel from agent/__init__.py) the same as
        # missing — always fall back to RoleId from XML_User.xml in that case.
        _provided_role = role_id if role_id and role_id != "0" else None
        effective_role_id = _provided_role or (resolved_user.get("RoleId", "0") if resolved_user else "0")

        # Determine admin access (role_id "101" = Admin User by default)
        is_admin = (effective_role_id == config.APP_DB_ADMIN_ROLE_ID)

        # ── Debug trace: log resolved identity and admin flag ────────────────────
        debug_log(
            "DB QA IDENTITY RESOLUTION",
            raw_user_id=user_id,
            raw_role_id=role_id,
            resolved_user=(
                f"LoginId={resolved_user.get('LoginId')} UserId={resolved_user.get('UserId')}"
                if resolved_user else "NOT FOUND"
            ),
            effective_user_id=effective_user_id,
            effective_role_id=effective_role_id,
            is_admin=is_admin,
        )

        # Always log identity resolution so issues are visible in uvicorn output
        logger.info(
            "[DB_QA] identity: raw_user=%s raw_role=%s -> effective_user=%s effective_role=%s is_admin=%s intent=%s",
            user_id, role_id, effective_user_id, effective_role_id, is_admin, intent,
        )

        # Self-service guard: db_my_* intents REQUIRE a resolved user.
        # When no identity is available (user_id="0" sentinel or completely absent),
        # return a friendly "login required" response instead of the confusing
        # "Your profile could not be found." that comes from the handler.
        if intent.startswith("db_my_") and not resolved_user:
            logger.warning(
                "[DB_QA] no identity for self-service intent=%s raw_user=%r — returning auth_required",
                intent, user_id,
            )
            return {
                "intent": intent,
                "response_text": (
                    "I can only answer personal questions when you're logged in. "
                    "Please access the chat through the application portal with your credentials."
                ),
                "result_type": "auth_required",
                "db_intent": intent,
                "db_found": False,
                "db_records": [],
                "db_summary": "Authentication required.",
                "db_beautified": "",
            }

        # ── New-taxonomy path (Phase 6) ──────────────────────────────────
        # Try the new Intent/scope_query/dispatch2 path first — only fires
        # for intents that are valid backend.db_qa.intents.taxonomy.Intent
        # values (legacy "db_*" names are not, so they fall straight
        # through to the untouched legacy dispatch below).
        from backend.db_qa.intents.taxonomy import Intent as _Intent
        try:
            _new_intent = _Intent(intent)
        except ValueError:
            _new_intent = None

        if _new_intent is not None:
            _effective_login_id = login_id or (resolved_user.get("LoginId") if resolved_user else user_id)
            session_user = {
                "login_id": _effective_login_id,
                "user_id": effective_user_id,
            }
            try:
                scope = access_control.scope_query(session_user, intent, params or {})
            except PermissionError as exc:
                logger.info("[DB_QA] new-taxonomy intent=%s denied: %s", intent, exc)
                return {
                    "intent": intent,
                    "response_text": str(exc),
                    "result_type": "db_qa_result",
                    "db_intent": intent,
                    "db_found": False,
                    "db_records": [],
                    "db_summary": str(exc),
                    "db_beautified": "",
                }

            new_result = query_handlers.dispatch2(_new_intent, scope, params or {}, store)
            if new_result is not None:
                debug_log(
                    "DB QA DISPATCH2 (new taxonomy)",
                    intent=intent, target_type=scope.get("target_type"),
                    is_admin=scope.get("is_admin"),
                )
                _meta = new_result.get("meta", {})
                _is_disambiguation = bool(_meta.get("disambiguation"))
                rendered = templates.render(intent, new_result)
                response_dict = {
                    "intent": intent,
                    "response_text": rendered,
                    "result_type": "disambiguation" if _is_disambiguation else "db_qa_result",
                    "options": _meta.get("options", []) if _is_disambiguation else [],
                    "db_intent": intent,
                    "db_found": new_result.get("found", False),
                    "db_records": new_result.get("records", []),
                    "db_summary": new_result.get("summary", ""),
                    "db_beautified": "",
                    "db_qa_data": _build_db_qa_data(new_result, intent),
                }
                # Disambiguation prompts are a menu of return names, not a
                # data result — beautification would only risk paraphrasing
                # the exact option strings the user needs to reply with.
                if _is_disambiguation:
                    return response_dict
                if beautify and config.APP_DB_ENABLE_BEAUTIFY:
                    try:
                        full_response = ""
                        for token in beautify_stream(message, new_result, model=model, ollama_url=None):
                            full_response += token
                        response_dict["db_beautified"] = full_response
                        response_dict["response_text"] = full_response
                    except Exception as exc:
                        logger.warning("[DB_QA] Beautifier failed on new-taxonomy result, using template: %s", exc)
                return response_dict
            # new_result is None -> intent isn't migrated to a handler yet;
            # fall through to legacy dispatch exactly as before.

        # Execute the query handler (routes intent to appropriate handler)
        # ── Debug trace: log which handler is about to be dispatched ──────────────
        _handler_fn = query_handlers.INTENT_TO_HANDLER.get(intent, query_handlers.handle_unknown)
        debug_log(
            "DB QA DISPATCH",
            intent=intent,
            handler=getattr(_handler_fn, "__name__", getattr(getattr(_handler_fn, "__wrapped__", None), "__name__", "?")).replace("<locals>.", ""),
            effective_user_id=effective_user_id,
            is_admin=is_admin,
            params=params or "{}",
        )
        result = query_handlers.dispatch(
            intent=intent,
            params=params,
            user_id=effective_user_id,
            role_id=effective_role_id,
            is_admin=is_admin,
            store=store,
        )
        
        logger.info(
            "[DB_QA] Dispatch result: intent=%s user=%s found=%s records=%d",
            intent, effective_user_id, result.get("found"), len(result.get("records", [])),
        )
        # ── Debug trace: log result summary ───────────────────────────────────
        debug_log(
            "DB QA RESULT",
            intent=intent,
            found=result.get("found", False),
            records_count=len(result.get("records", [])),
            summary=result.get("summary", "")[:120],
        )
        
        # Populate response dict
        response_dict = {
            "intent":      intent,
            "response_text": "",
            "result_type": "db_qa_result",
            "db_intent":   intent,
            "db_found":    result.get("found", False),
            "db_records":  result.get("records", []),
            "db_summary":  result.get("summary", ""),
            "db_beautified": "",
            "db_qa_data":  _build_db_qa_data(result, intent),
        }
        
        # Beautify if enabled and config allows
        if beautify and config.APP_DB_ENABLE_BEAUTIFY:
            try:
                logger.debug("[DB_QA] Beautifying response with model=%s", model)
                full_response = ""
                for token in beautify_stream(
                    message, result, model=model, ollama_url=None
                ):
                    full_response += token
                response_dict["db_beautified"] = full_response
                response_dict["response_text"] = full_response
                logger.debug("[DB_QA] Beautified response: %d chars", len(full_response))
            except Exception as exc:
                logger.warning("[DB_QA] Beautifier failed, using summary: %s", exc)
                response_dict["response_text"] = result.get("summary", "No data found.")
        else:
            # Beautify disabled — build a readable response from records directly
            response_dict["response_text"] = _format_plain(result)
        
        return response_dict
        
    except Exception as exc:
        logger.exception("db_qa_query: unhandled error")
        error_response = ChatResponse(
            intent="error",
            response_text="Unable to retrieve the requested information. Please try again.",
            result_type="error",
            db_intent=intent,
            db_found=False,
        )
        return error_response.model_dump()


def stream_db_qa_beautifier(
    message: str,
    result: dict,
    model: str = "phi3:mini",
) -> Generator[str, None, None]:
    """Stream beautified DB Q&A response as plain text tokens.
    
    Used for SSE endpoints where responses are streamed back to the client.
    """
    try:
        yield from beautify_stream(message, result, model=model)
    except Exception as exc:
        logger.error("stream_db_qa_beautifier: %s", exc)
        yield result.get("summary", "No data found.")
