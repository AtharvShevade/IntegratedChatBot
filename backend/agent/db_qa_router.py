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
from backend.db_qa.intent_classifier import classify
from backend.db_qa import query_handlers, xml_store
from backend.db_qa.beautifier import beautify_stream
from backend.models import ChatResponse
from backend.utils.debug import debug_log

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
    # Reference data
    "DEPT_LIST":            "db_list_departments",
    "ROLE_LIST":            "db_list_roles",
    "RETURN_LIST":          "db_list_returns",
    "MENU_LIST":            "db_menu_list",
    "NOTIFICATION_LIST":    "db_notifications",
    "BANK_INFO":            "db_bank_info",
    # Lookup by target
    "USER_PROFILE":         "db_user_info",
    "DEPT_INFO":            "db_department_info",
    "ROLE_PERMISSIONS":     "db_role_info",
    # Admin audit / logs
    "AUDIT_LOG":            "db_audit_log",
    "CROSS_VAL_LOG":        "db_cross_val_log",
    "UPLOAD_LOG":           "db_upload_log",
}


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
        return None, {}

    db_intent = _CLASSIFIER_TO_DB_INTENT.get(raw_intent)
    if not db_intent:
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

    # Normalize department key used by the db_* flow.
    if "target_dept" in mapped_params and "target_department" not in mapped_params:
        mapped_params["target_department"] = mapped_params["target_dept"]

    return db_intent, mapped_params


def _format_plain(result: dict) -> str:
    """Build a human-readable text response from a QueryResult without using the LLM.

    When beautify is disabled this is shown instead of the bare one-liner summary.
    For a handful of records each field is printed as a bullet; for larger sets a
    compact table is produced; access-denied / not-found messages pass through as-is.
    """
    summary = result.get("summary", "No data found.")
    records = result.get("records", [])
    label   = result.get("label", "")

    if not records:
        return summary                                      # nothing to expand

    # Single record — show key: value pairs (e.g. MY_DEPARTMENT, MY_ROLE)
    if len(records) == 1:
        lines = [f"**{label}**", ""]
        for k, v in records[0].items():
            if v not in (None, "", []):
                lines.append(f"- **{k}**: {v}")
        return "\n".join(lines)

    # Multiple records — pick the most useful display columns automatically
    _PRIORITY_COLS = ["Name", "LoginId", "DeptName", "RoleName", "Status",
                      "EmailId", "RoleId", "DeptId", "ReturnName", "PeriodName"]
    sample_keys = list(records[0].keys())
    cols = [c for c in _PRIORITY_COLS if c in sample_keys]
    if not cols:
        cols = sample_keys[:4]                              # fallback: first 4 columns

    header = " | ".join(cols)
    sep    = " | ".join(["---"] * len(cols))
    rows   = []
    for r in records:
        rows.append(" | ".join(str(r.get(c, "")) for c in cols))

    table = f"**{label}** ({len(records)} records)\n\n"
    table += header + "\n" + sep + "\n"
    table += "\n".join(rows)
    table += f"\n\n_{summary}_"
    return table


def handle_db_qa_query(
    message: str,
    intent: str,
    params: dict,
    user_id: str,
    role_id: str,
    beautify: bool = False,
    model: str = "phi3:mini",
) -> dict:
    """Execute DB Q&A intent using LLM-extracted parameters.
    
    This handler is called when the LLM detects an intent starting with "db_"
    (e.g., db_my_profile, db_list_users, db_list_departments).
    
    Args:
        message: Original user question
        intent: LLM-detected intent (e.g., "db_list_users", "db_my_department")
        params: LLM-extracted entities dict containing:
                - target_user: username/user ID if asking about specific user
                - target_department: department name if mentioned
                - target_role: role name if mentioned
                - query_type: filter type ("active", "inactive", "all", "details", "count")
        user_id: Current user's ID (for self-service checks)
        role_id: Current user's role ID (for admin access checks)
        beautify: Whether to use LLM for formatting results
        model: Ollama model to use for beautification
        
    Returns:
        Response dict compatible with ChatResponse model with db_* fields populated
    """
    try:
        # Feature gate: gracefully return if not configured
        if not config.APP_DB_BASE_PATH:
            logger.warning("[DB_QA] APP_DB_BASE_PATH not configured, returning disabled response")
            return {
                "result": "Database Q&A feature is not configured.",
                "db_found": False,
                "result_type": "db_disabled",
            }
        
        # Instantiate XML data store
        store = xml_store.XMLStore(config.APP_DB_BASE_PATH)
        # ── Debug trace: log function entry with full identity context ───────────────
        debug_log(
            "DB QA ROUTER — handle_db_qa_query",
            question=message[:120],
            intent=intent,
            user_id_raw=user_id,
            role_id_raw=role_id,
            xml_base_path=config.APP_DB_BASE_PATH,
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
            "intent": intent,
            "response_text": "",
            "result_type": "db_result",
            "db_intent": intent,
            "db_found": result.get("found", False),
            "db_records": result.get("records", []),
            "db_summary": result.get("summary", ""),
            "db_beautified": "",
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
            response_text=f"Error querying database: {str(exc)}",
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
