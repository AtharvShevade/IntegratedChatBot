"""New-taxonomy handlers — USER category.

Signature: handle_X(scope: dict, entities: dict, store: XMLStore) -> dict.
`scope` comes from access_control.scope_query() — target_type/tenant_id/
login_id/is_admin/allowed_form_ids are all already resolved and authorized
by the time a handler runs; handlers never re-check admin status themselves.

Returns the same QueryResult shape as the legacy handlers
({intent, label, found, records, summary, meta}) so beautifier.py/
_format_plain()/_build_db_qa_data() in agent/db_qa_router.py keep working
unchanged for these intents too.
"""
from __future__ import annotations

from backend.db_qa.versions.loader import build_index
from backend.db_qa.xml_store import XMLStore, get_attr, is_active_status

_USER_FIELD_LABELS: dict[str, str] = {
    "email": "email address",
    "mobile": "mobile number",
    "login_id": "login ID",
    "user_code": "user code",
    "created_date": "account creation date",
    "created_by": "created-by",
    "last_login": "last login time",
    "failed_login_count": "failed login count",
    "status": "account status",
    "password_date": "password last-updated date",
}

_USER_FIELD_ATTR: dict[str, str] = {
    "email": "EmailId",
    "mobile": "MobileNumber",
    "login_id": "LoginId",
    "user_code": "Code",
    "created_date": "UserCreationDate",
    "created_by": "CreatedBy",
    "last_login": "LastLoginDT",
    "failed_login_count": "FailedLoginCount",
    "status": "Status",
    "password_date": "PasswordUpdateDate",
}


def _result(intent: str, label: str, records: list, summary: str, **meta) -> dict:
    return {"intent": intent, "label": label, "found": bool(records), "records": records, "summary": summary, "meta": meta}


def _not_found(intent: str, label: str, msg: str) -> dict:
    return _result(intent, label, [], msg)


def _resolve_target_user(store: XMLStore, scope: dict, entities: dict) -> dict | None:
    """self -> the caller's own user row; other_user -> the named target_user."""
    if scope["target_type"] == "self":
        return store.user_by_id(scope.get("user_id") or scope["login_id"]) or store.user_by_name(scope["login_id"])
    target = entities.get("target_user", "")
    if not target:
        return None
    return store.resolve_user(target)


def handle_user_profile(scope: dict, entities: dict, store: XMLStore) -> dict:
    u = _resolve_target_user(store, scope, entities)
    if not u:
        who = "Your" if scope["target_type"] == "self" else f"'{entities.get('target_user', '')}'"
        return _not_found("user_profile", "User Profile", f"{who} profile could not be found.")
    label = "My Profile" if scope["target_type"] == "self" else f"Profile: {u.get('Name', '')}"
    return _result("user_profile", label, [store.enrich_user(u)],
                   f"Profile for {u.get('Name', scope['login_id'])}.")


def handle_user_field(scope: dict, entities: dict, store: XMLStore) -> dict:
    field = entities.get("field", "")
    field_label = _USER_FIELD_LABELS.get(field, field or "field")
    attr = _USER_FIELD_ATTR.get(field)
    if not attr:
        return _not_found("user_field", "User Field", f"Unrecognized user field {field!r}.")

    u = _resolve_target_user(store, scope, entities)
    if not u:
        who = "Your" if scope["target_type"] == "self" else f"'{entities.get('target_user', '')}'"
        return _not_found("user_field", "User Field", f"{who} profile could not be found.")

    value = u.get(attr, "").strip() or "Not set"
    who_phrase = "Your" if scope["target_type"] == "self" else f"{u.get('Name', '')}'s"
    if field == "status":
        display = "Yes, active" if is_active_status(value) else "No, inactive"
        return _result("user_field", field_label.title(), [{attr: value}],
                       f"{who_phrase} account is active: {display}.")
    return _result("user_field", field_label.title(), [{attr: value}],
                   f"{who_phrase} {field_label} is: {value}.")


def handle_user_list(scope: dict, entities: dict, store: XMLStore) -> dict:
    query_type = (entities.get("query_type") or "all").lower()
    users = store.users()

    if query_type == "active":
        rows = [u for u in users if is_active_status(u.get("Status"))]
        label, summary = "Active Users", f"There are {len(rows)} active users."
    elif query_type == "inactive":
        rows = [u for u in users if not is_active_status(u.get("Status"))]
        label, summary = "Inactive / Disabled Users", f"There are {len(rows)} inactive users."
    elif query_type == "never_login":
        rows = [u for u in users if not u.get("LastLoginDT", "").strip()]
        label, summary = "Users Who Never Logged In", f"Found {len(rows)} users who have never logged in."
    elif query_type == "failed_login":
        rows = [u for u in users if int(u.get("FailedLoginCount", "0") or "0") > 0]
        rows.sort(key=lambda u: int(u.get("FailedLoginCount", "0") or "0"), reverse=True)
        label, summary = "Users with Failed Login Attempts", f"Found {len(rows)} users with failed login attempts."
    elif query_type == "duplicate_email":
        from collections import Counter
        emails = [u.get("EmailId", "").lower() for u in users if u.get("EmailId")]
        dup_emails = {e for e, cnt in Counter(emails).items() if cnt > 1}
        rows = [u for u in users if u.get("EmailId", "").lower() in dup_emails]
        label = "Users Sharing Email Addresses"
        summary = (f"Found {len(rows)} user records sharing {len(dup_emails)} email address(es)."
                   if rows else "No duplicate email addresses found. All user emails are unique.")
    elif query_type == "count":
        active = [u for u in users if is_active_status(u.get("Status"))]
        return _result("user_list", "User Count",
                       [{"total": len(users), "active": len(active), "inactive": len(users) - len(active)}],
                       f"Total users: {len(users)} ({len(active)} active, {len(users) - len(active)} inactive).",
                       total=len(users), active=len(active))
    elif query_type == "active_count":
        n = sum(1 for u in users if is_active_status(u.get("Status")))
        return _result("user_list", "Active User Count", [{"active": n}],
                       f"Active users: {n}.", active=n)
    elif query_type == "inactive_count":
        n = sum(1 for u in users if not is_active_status(u.get("Status")))
        return _result("user_list", "Inactive User Count", [{"inactive": n}],
                       f"Inactive users: {n}.", inactive=n)
    else:
        rows = users
        label, summary = "All Users", f"There are {len(rows)} users in the system."

    return _result("user_list", label, [store.enrich_user(u) for u in rows], summary, count=len(rows))


def handle_users_by_department(scope: dict, entities: dict, store: XMLStore) -> dict:
    target = entities.get("target_department", "")
    dept = store.dept_by_name(target) if target else None
    if not dept:
        return _not_found("users_by_department", "Users by Department",
                          f"Department '{target}' not found." if target else "Please specify a department name.")
    dept_id = get_attr(dept, "DeptId", "Id", default="")
    users = [store.enrich_user(u) for u in store.users() if get_attr(u, "DepartmentId", "DeptId") == dept_id]
    return _result("users_by_department", f"Users in {dept.get('Name')}", users,
                   f"Found {len(users)} users in department '{dept.get('Name')}'.",
                   dept_name=dept.get("Name"), count=len(users))


def handle_users_by_role(scope: dict, entities: dict, store: XMLStore) -> dict:
    target = entities.get("target_role", "")
    role = store.role_by_name(target) if target else None
    if not role:
        return _not_found("users_by_role", "Users by Role",
                          f"Role '{target}' not found." if target else "Please specify a role name.")
    role_id = get_attr(role, "RoleId", "Role_Id", default="")
    users = [store.enrich_user(u) for u in store.users() if get_attr(u, "RoleId", "Role_Id") == role_id]
    return _result("users_by_role", f"Users with Role: {role.get('Name')}", users,
                   f"Found {len(users)} users with role '{role.get('Name')}'.",
                   role_name=role.get("Name"), count=len(users))


def handle_users_with_roles_and_departments(scope: dict, entities: dict, store: XMLStore) -> dict:
    role_index = build_index(store.roles(), "RoleId")
    dept_index = build_index(store.departments(), "DeptId")
    rows = []
    for u in store.users():
        row = store.enrich_user(u)
        role_id = get_attr(u, "RoleId", "Role_Id", default="")
        dept_id = get_attr(u, "DepartmentId", "DeptId", default="")
        role = role_index.get(role_id)
        dept = dept_index.get(dept_id)
        row["RoleName"] = role.get("Name") if role else row.get("RoleName", "")
        row["DeptName"] = dept.get("Name") if dept else row.get("DeptName", "")
        rows.append(row)
    return _result("users_with_roles_and_departments", "All Users (Role + Department)",
                   rows, f"There are {len(rows)} users, each with their role and department.", count=len(rows))
