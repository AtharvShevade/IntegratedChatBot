"""Query handlers — one function per intent.

Each handler receives:
    store     XMLStore    — in-memory XML data
    params    dict        — extracted entities from the question
    user_id   str         — current user's UserId
    is_admin  bool        — True if the user has an admin role

Returns a ``QueryResult`` dict::

    {
        "intent":   str,           # echo of the intent name
        "label":    str,           # human-readable category label
        "found":    bool,          # False → empty result
        "records":  list[dict],    # structured rows (safe, no passwords)
        "summary":  str,           # one-sentence plain text fallback
        "meta":     dict,          # extra context (counts, warnings, …)
    }
"""
from __future__ import annotations

from backend.db_qa.xml_store import XMLStore, SUBMISSION_STATUS_LABELS, _safe, get_attr
from backend.db_qa.query_handlers._extraction_guard import not_found_summary

# ── helpers ──────────────────────────────────────────────────────────────────

def _resolve_user(store: XMLStore, user_id: str) -> dict | None:
    """Look up a user by numeric UserId first, then by LoginId/Name string.

    This defensive fallback ensures self-service handlers work regardless of
    whether the caller passed the numeric UserId ('104') or the login string
    ('iris810'). Both forms arrive depending on what the .NET app forwards.
    """
    return store.user_by_id(user_id) or store.user_by_name(user_id)


def _result(intent: str, label: str, records: list, summary: str, **meta) -> dict:
    return {
        "intent": intent,
        "label": label,
        "found": bool(records),
        "records": records,
        "summary": summary,
        "meta": meta,
    }


def _not_found(intent: str, label: str, msg: str) -> dict:
    return _result(intent, label, [], msg)


def _admin_denied(intent: str) -> dict:
    return _result(
        intent, "Access Denied", [],
        "You do not have permission to view this information. "
        "Please contact your system administrator."
    )


# ── USER handlers ─────────────────────────────────────────────────────────────

def handle_user_list(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    if not is_admin:
        return _admin_denied("USER_LIST")
    users = [store.enrich_user(u) for u in store.users()]
    return _result("USER_LIST", "All Users", users,
                   f"There are {len(users)} users in the system.", count=len(users))


def handle_user_list_active(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    if not is_admin:
        return _admin_denied("USER_LIST_ACTIVE")
    active = [store.enrich_user(u) for u in store.users() if u.get("Status", "").lower() == "true"]
    return _result("USER_LIST_ACTIVE", "Active Users", active,
                   f"There are {len(active)} active users.", count=len(active))


def handle_user_list_inactive(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    if not is_admin:
        return _admin_denied("USER_LIST_INACTIVE")
    inactive = [store.enrich_user(u) for u in store.users() if u.get("Status", "").lower() != "true"]
    return _result("USER_LIST_INACTIVE", "Inactive / Disabled Users", inactive,
                   f"There are {len(inactive)} inactive users.", count=len(inactive))


def handle_user_count(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    if not is_admin:
        return _admin_denied("USER_COUNT")
    all_users = store.users()
    active = [u for u in all_users if u.get("Status", "").lower() == "true"]
    return _result("USER_COUNT", "User Count",
                   [{"total": len(all_users), "active": len(active), "inactive": len(all_users) - len(active)}],
                   f"Total users: {len(all_users)} ({len(active)} active, {len(all_users) - len(active)} inactive).",
                   total=len(all_users), active=len(active))


def handle_user_profile(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    if not is_admin:
        return _admin_denied("USER_PROFILE")
    target = params.get("target_user", "")
    if not target:
        return _not_found("USER_PROFILE", "User Profile", "Please specify the user name or ID.")
    u = store.user_by_name(target) or store.user_by_id(target)
    if not u:
        return _not_found("USER_PROFILE", "User Profile", f"No user found matching '{target}'.")
    return _result("USER_PROFILE", "User Profile", [store.enrich_user(u)],
                   f"Profile for {u.get('Name', target)}.")


def handle_user_by_dept(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    if not is_admin:
        return _admin_denied("USER_BY_DEPT")
    target = params.get("target_dept", "")
    dept = store.dept_by_name(target) if target else None
    if not dept:
        return _not_found("USER_BY_DEPT", "Users by Department",
                          f"Department '{target}' not found. Check spelling." if target else
                          "Please specify the department name.")
    dept_id = get_attr(dept, "DeptId", "Id", default="")
    users = [store.enrich_user(u) for u in store.users()
             if get_attr(u, "DepartmentId", "DeptId") == dept_id]
    return _result("USER_BY_DEPT", f"Users in {dept.get('Name')}",
                   users, f"Found {len(users)} users in department '{dept.get('Name')}'.",
                   dept_name=dept.get("Name"), count=len(users))


def handle_user_by_role(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    if not is_admin:
        return _admin_denied("USER_BY_ROLE")
    target = params.get("target_role", "")
    role = store.role_by_name(target) if target else None
    if not role:
        return _not_found("USER_BY_ROLE", "Users by Role",
                          not_found_summary("Role '{name}' not found.", target, "Please specify the role name."))
    role_id = role.get("RoleId", "")
    users = [store.enrich_user(u) for u in store.users() if u.get("RoleId") == role_id]
    return _result("USER_BY_ROLE", f"Users with Role: {role.get('Name')}",
                   users, f"Found {len(users)} users with role '{role.get('Name')}'.",
                   role_name=role.get("Name"), count=len(users))


def handle_user_never_login(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    if not is_admin:
        return _admin_denied("USER_NEVER_LOGIN")
    never = [store.enrich_user(u) for u in store.users()
             if not u.get("LastLoginDT", "").strip()]
    return _result("USER_NEVER_LOGIN", "Users Who Never Logged In",
                   never, f"Found {len(never)} users who have never logged in.", count=len(never))


def handle_user_failed_login(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    if not is_admin:
        return _admin_denied("USER_FAILED_LOGIN")
    failed = [store.enrich_user(u) for u in store.users()
              if int(u.get("FailedLoginCount", "0") or "0") > 0]
    failed.sort(key=lambda u: int(u.get("FailedLoginCount", "0") or "0"), reverse=True)
    # show_failed_logins: the count is hidden from ordinary user tables
    # (agent/db_qa_router._CONDITIONAL_FIELDS); this question is about it.
    return _result("USER_FAILED_LOGIN", "Users with Failed Login Attempts",
                   failed, f"Found {len(failed)} users with failed login attempts.",
                   count=len(failed), show_failed_logins=True)


def handle_user_duplicate_email(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    if not is_admin:
        return _admin_denied("USER_DUPLICATE_EMAIL")
    from collections import Counter
    emails = [u.get("EmailId", "").lower() for u in store.users() if u.get("EmailId")]
    dup_emails = {e for e, cnt in Counter(emails).items() if cnt > 1}
    dupes = [store.enrich_user(u) for u in store.users()
             if u.get("EmailId", "").lower() in dup_emails]
    if not dupes:
        return _result("USER_DUPLICATE_EMAIL", "Duplicate Email Check",
                       [], "No duplicate email addresses found. All user emails are unique.")
    return _result("USER_DUPLICATE_EMAIL", "Users Sharing Email Addresses",
                   dupes, f"Found {len(dupes)} user records sharing {len(dup_emails)} email address(es).",
                   dup_count=len(dup_emails))


# ── MY PROFILE (self-service) ─────────────────────────────────────────────────

def handle_my_profile(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    u = _resolve_user(store, user_id)
    if not u:
        return _not_found("MY_PROFILE", "My Profile", "Your profile could not be found.")
    return _result("MY_PROFILE", "My Profile", [store.enrich_user(u)],
                   f"Profile for {u.get('Name', user_id)}.")


def handle_my_department(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    u = _resolve_user(store, user_id)
    if not u:
        return _not_found("MY_DEPARTMENT", "My Department", "Your profile could not be found.")
    dept_id = get_attr(u, "DepartmentId", "DeptId", default="")
    if not dept_id:
        return _not_found("MY_DEPARTMENT", "My Department",
                          "No department is assigned to your account. Contact your administrator.")
    dept = store.dept_by_id(dept_id)
    if not dept:
        return _not_found("MY_DEPARTMENT", "My Department",
                          f"Department ID '{dept_id}' exists in your profile but was not found in the system.")
    dept_name = dept.get("Name", dept_id)
    return _result("MY_DEPARTMENT", "My Department",
                   [{"DeptName": dept_name, "DeptId": dept_id}],
                   f"You are in the '{dept_name}' department.")


def handle_my_role(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    u = _resolve_user(store, user_id)
    if not u:
        return _not_found("MY_ROLE", "My Role", "Your profile could not be found.")
    role_id = get_attr(u, "RoleId", "Role_Id", default="")
    role_name = store.role_name_by_id(role_id)
    return _result("MY_ROLE", "My Role",
                   [{"RoleName": role_name, "RoleId": role_id}],
                   f"Your role is '{role_name}'.")


def handle_my_email(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    u = _resolve_user(store, user_id)
    if not u:
        return _not_found("MY_EMAIL", "My Email", "Your profile could not be found.")
    return _result("MY_EMAIL", "My Email",
                   [{"EmailId": u.get("EmailId", "Not set")}],
                   f"Your email address is: {u.get('EmailId', 'not set')}.")


def handle_my_mobile(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    u = _resolve_user(store, user_id)
    if not u:
        return _not_found("MY_MOBILE", "My Mobile", "Your profile could not be found.")
    mob = u.get("MobileNumber", "").strip() or "Not set"
    return _result("MY_MOBILE", "My Mobile Number",
                   [{"MobileNumber": mob}], f"Your mobile number: {mob}.")


def handle_my_last_login(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    u = _resolve_user(store, user_id)
    if not u:
        return _not_found("MY_LAST_LOGIN", "My Last Login", "Your profile could not be found.")
    last = u.get("LastLoginDT", "").strip() or "Never"
    return _result("MY_LAST_LOGIN", "My Last Login",
                   [{"LastLoginDT": last}], f"Your last login was: {last}.")


def handle_my_failed_logins(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    u = _resolve_user(store, user_id)
    if not u:
        return _not_found("MY_FAILED_LOGINS", "My Failed Logins", "Your profile could not be found.")
    count = u.get("FailedLoginCount", "0")
    return _result("MY_FAILED_LOGINS", "My Failed Login Count",
                   [{"FailedLoginCount": count, "LastFailedLoginDT": u.get("LastFailedLoginDT", "")}],
                   f"Your account has {count} failed login attempt(s).",
                   show_failed_logins=True)


def handle_my_status(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    u = _resolve_user(store, user_id)
    if not u:
        return _not_found("MY_STATUS", "My Account Status", "Your profile could not be found.")
    active = u.get("Status", "").lower() == "true"
    label = "Active" if active else "Inactive / Disabled"
    return _result("MY_STATUS", "My Account Status",
                   [{"Status": label}], f"Your account is currently {label}.")


def handle_my_created_date(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    u = _resolve_user(store, user_id)
    if not u:
        return _not_found("MY_CREATED_DATE", "My Account Creation", "Your profile could not be found.")
    created = u.get("UserCreationDate", "").strip() or "Not recorded"
    created_by = u.get("CreatedBy", "").strip() or "Not recorded"
    return _result("MY_CREATED_DATE", "My Account Creation",
                   [{"UserCreationDate": created, "CreatedBy": created_by}],
                   f"Your account was created on {created}" + (f" by {created_by}." if created_by != "Not recorded" else "."))


def handle_my_login_id(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    u = _resolve_user(store, user_id)
    if not u:
        return _not_found("MY_LOGIN_ID", "My Login ID", "Your profile could not be found.")
    return _result("MY_LOGIN_ID", "My Login ID",
                   [{"LoginId": u.get("LoginId", ""), "UserId": u.get("UserId", "")}],
                   f"Your login ID is: {u.get('LoginId', 'not set')}.")


def handle_my_user_code(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    u = _resolve_user(store, user_id)
    if not u:
        return _not_found("MY_USER_CODE", "My User Code", "Your profile could not be found.")
    code = u.get("Code", "").strip() or "Not set"
    return _result("MY_USER_CODE", "My User Code",
                   [{"Code": code}], f"Your user code is: {code}.")


def handle_my_password_date(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    u = _resolve_user(store, user_id)
    if not u:
        return _not_found("MY_PASSWORD_DATE", "My Password Update", "Your profile could not be found.")
    # XML_User.xml stores password date in PasswordUpdateDate (ActionDate is a different field)
    pwd_date = u.get("PasswordUpdateDate", "").strip() or "Not recorded"
    return _result("MY_PASSWORD_DATE", "My Last Password Update",
                   [{"PasswordUpdateDate": pwd_date}],
                   f"Your password was last updated on: {pwd_date}.")


def handle_my_user_level(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    u = _resolve_user(store, user_id)
    if not u:
        return _not_found("MY_USER_LEVEL", "My User Level", "Your profile could not be found.")
    # XML_User.xml has no LevelId field — levels are assigned via Level1/2/3UserEmails in XML_Dept.xml
    level_name, level_id = store.user_level_for_user(u)
    if not level_name:
        return _not_found("MY_USER_LEVEL", "My User Level",
                          "No user level (L1/L2/L3) is assigned to your account in this department.")
    return _result("MY_USER_LEVEL", "My User Level",
                   [{"LevelName": level_name, "LevelId": level_id}],
                   f"Your user level is: {level_name}.")


def handle_my_role_peer_count(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    u = _resolve_user(store, user_id)
    if not u:
        return _not_found("MY_ROLE_PEER_COUNT", "Users with My Role", "Your profile could not be found.")
    role_id = get_attr(u, "RoleId", "Role_Id", default="")
    my_uid = u.get("UserId", "")
    peers = [pu for pu in store.users()
             if get_attr(pu, "RoleId", "Role_Id") == role_id and pu.get("UserId") != my_uid]
    role_name = store.role_name_by_id(role_id)
    return _result("MY_ROLE_PEER_COUNT", f"Users with Role: {role_name}",
                   [_safe(p) for p in peers],
                   f"{len(peers)} other user(s) share the '{role_name}' role with you.",
                   role_name=role_name, count=len(peers))


def handle_user_level_list(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    if not is_admin:
        return _admin_denied("USER_LEVEL_LIST")
    levels = list(store.user_levels())
    return _result("USER_LEVEL_LIST", "User Levels",
                   levels, f"There are {len(levels)} user level(s) defined in the system.",
                   count=len(levels))


def handle_my_role_permissions(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    u = _resolve_user(store, user_id)
    if not u:
        return _not_found("MY_ROLE_PERMISSIONS", "My Permissions", "Your profile could not be found.")
    role_id = get_attr(u, "RoleId", "Role_Id", default="")
    role_name = store.role_name_by_id(role_id)

    target_action = params.get("target_action")
    accesses = [store.enrich_role_access(a)
                for a in store.role_access()
                if get_attr(a, "RoleId", "Role_Id") == role_id]

    if target_action:
        allowed = [a for a in accesses if a.get(target_action, "false").lower() == "true"]
        return _result("MY_ROLE_PERMISSIONS", f"My '{target_action}' Permissions",
                       allowed, f"Your role '{role_name}' has {target_action} access on {len(allowed)} module(s).",
                       role_name=role_name, action=target_action)

    return _result("MY_ROLE_PERMISSIONS", f"My Role Permissions ({role_name})",
                   accesses, f"Your role '{role_name}' has access to {len(accesses)} module(s).",
                   role_name=role_name)


def handle_my_dept_returns(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    u = _resolve_user(store, user_id)
    if not u:
        return _not_found("MY_DEPT_RETURNS", "My Department Returns", "Your profile could not be found.")
    dept_id = get_attr(u, "DepartmentId", "DeptId", default="")
    if not dept_id:
        return _not_found("MY_DEPT_RETURNS", "My Department Returns",
                          "No department is assigned to your account.")
    dept = store.dept_by_id(dept_id)
    if not dept:
        return _not_found("MY_DEPT_RETURNS", "My Department Returns",
                          f"Department ID '{dept_id}' not found in the system.")

    form_ids = [f.strip() for f in dept.get("Forms", "").split("|") if f.strip()]
    nx_ids = [f.strip() for f in dept.get("NXForms", "").split("|") if f.strip()]

    xbrl_returns = [store.enrich_return(r) for r in store.returns()
                    if r.get("ReturnId") in form_ids or r.get("Id") in form_ids]
    non_xbrl = [dict(r) for r in store.non_xbrl_returns()
                if r.get("ReturnId") in nx_ids or r.get("Id") in nx_ids]

    records = [{"type": "XBRL", **r} for r in xbrl_returns] + \
              [{"type": "Non-XBRL", **r} for r in non_xbrl]

    dept_name = dept.get("Name", dept_id)
    return _result("MY_DEPT_RETURNS", f"Returns for My Department ({dept_name})",
                   records,
                   f"Your department '{dept_name}' has {len(xbrl_returns)} XBRL returns and {len(non_xbrl)} non-XBRL returns.",
                   dept_name=dept_name, xbrl_count=len(xbrl_returns), non_xbrl_count=len(non_xbrl))


def handle_my_submissions(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    u = _resolve_user(store, user_id)
    # XML_InstanceLog stores LoginId (not numeric UserId) in its UserId field
    # e.g. UserId="iris810" — so match against LoginId as primary key
    login_id = u.get("LoginId", user_id) if u else user_id
    numeric_id = u.get("UserId", user_id) if u else user_id
    match_ids = {str(login_id), str(numeric_id), str(user_id)}
    enriched = [
        store.enrich_instance_log_entry(l)
        for l in store.instance_log()
        if l.get("UserId") in match_ids
    ]
    pending = sum(1 for e in enriched if e.get("Status", "") in ("0", "1", "2"))
    approved = sum(1 for e in enriched if e.get("Status", "") in ("9", "11"))
    return _result("MY_SUBMISSIONS", "My Submissions",
                   enriched,
                   f"You have {len(enriched)} submission record(s): {approved} approved, {pending} pending.",
                   count=len(enriched), approved=approved, pending=pending)


# ── DEPARTMENT ────────────────────────────────────────────────────────────────

def handle_dept_list(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    if not is_admin:
        return _admin_denied("DEPT_LIST")
    depts = list(store.departments())
    return _result("DEPT_LIST", "All Departments", depts,
                   f"There are {len(depts)} departments in the system.", count=len(depts))


def handle_dept_info(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    if not is_admin:
        return _admin_denied("DEPT_INFO")
    target = params.get("target_dept", "")
    dept = store.dept_by_name(target) if target else None
    if not dept:
        return _not_found("DEPT_INFO", "Department Info",
                          not_found_summary("Department '{name}' not found.", target, "Please specify a department name."))
    dept_id = get_attr(dept, "DeptId", "Id", default="")
    user_count = sum(1 for u in store.users() if get_attr(u, "DepartmentId", "DeptId") == dept_id)
    form_ids   = {f.strip() for f in dept.get("Forms",   "").split("|") if f.strip()}
    nx_ids     = {f.strip() for f in dept.get("NXForms", "").split("|") if f.strip()}
    xbrl_count = sum(1 for r in store.returns()
                     if r.get("Id") in form_ids or r.get("ReturnId") in form_ids)
    non_xbrl_count = sum(1 for r in store.non_xbrl_returns()
                         if r.get("Id") in nx_ids or r.get("ReturnId") in nx_ids)
    enriched = dict(dept)
    enriched["UserCount"]          = user_count
    enriched["XBRLReturnCount"]    = xbrl_count
    enriched["NonXBRLReturnCount"] = non_xbrl_count
    enriched["TotalReturnCount"]   = xbrl_count + non_xbrl_count
    dept_name = dept.get("Name", target)
    return _result("DEPT_INFO", f"Department: {dept_name}", [enriched],
                   f"Department '{dept_name}' has {user_count} user(s) and {xbrl_count + non_xbrl_count} assigned return(s).")


def handle_dept_returns(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    if not is_admin:
        return _admin_denied("DEPT_RETURNS")
    target = params.get("target_dept", "")
    dept = store.dept_by_name(target) if target else None
    if not dept:
        return _not_found("DEPT_RETURNS", "Department Returns",
                          not_found_summary("Department '{name}' not found.", target, "Please specify a department name."))

    form_ids = [f.strip() for f in dept.get("Forms", "").split("|") if f.strip()]
    nx_ids = [f.strip() for f in dept.get("NXForms", "").split("|") if f.strip()]
    xbrl = [store.enrich_return(r) for r in store.returns()
            if r.get("ReturnId") in form_ids or r.get("Id") in form_ids]
    non_xbrl = [dict(r) for r in store.non_xbrl_returns()
                if r.get("ReturnId") in nx_ids or r.get("Id") in nx_ids]
    records = [{"type": "XBRL", **r} for r in xbrl] + [{"type": "Non-XBRL", **r} for r in non_xbrl]
    dept_name = dept.get("Name", target)
    return _result("DEPT_RETURNS", f"Returns of {dept_name}",
                   records,
                   f"Department '{dept_name}' has {len(xbrl)} XBRL and {len(non_xbrl)} non-XBRL returns.",
                   dept_name=dept_name)


# ── ROLE ──────────────────────────────────────────────────────────────────────

def handle_role_list(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    if not is_admin:
        return _admin_denied("ROLE_LIST")
    roles = list(store.roles())
    return _result("ROLE_LIST", "All Roles", roles,
                   f"There are {len(roles)} roles defined in the system.", count=len(roles))


def handle_role_permissions(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    if not is_admin:
        return _admin_denied("ROLE_PERMISSIONS")
    target = params.get("target_role", "")
    role = store.role_by_name(target) if target else None
    if not role:
        return _not_found("ROLE_PERMISSIONS", "Role Permissions",
                          not_found_summary("Role '{name}' not found.", target, "Please specify a role name."))
    role_id = get_attr(role, "RoleId", "Role_Id", default="")
    accesses = [store.enrich_role_access(a)
                for a in store.role_access()
                if get_attr(a, "RoleId", "Role_Id") == role_id]
    return _result("ROLE_PERMISSIONS", f"Permissions for Role: {role.get('Name')}",
                   accesses,
                   f"Role '{role.get('Name')}' has permissions on {len(accesses)} module(s).",
                   role_name=role.get("Name"), count=len(accesses))


def handle_role_users(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    if not is_admin:
        return _admin_denied("ROLE_USERS")
    target = params.get("target_role", "")
    role = store.role_by_name(target) if target else None
    if not role:
        return _not_found("ROLE_USERS", "Users with Role",
                          not_found_summary("Role '{name}' not found.", target, "Please specify a role name."))
    role_id = get_attr(role, "RoleId", "Role_Id", default="")
    users = [store.enrich_user(u) for u in store.users()
             if get_attr(u, "RoleId", "Role_Id") == role_id]
    return _result("ROLE_USERS", f"Users with Role: {role.get('Name')}",
                   users, f"Found {len(users)} user(s) with role '{role.get('Name')}'.",
                   role_name=role.get("Name"), count=len(users))


def handle_permission_check(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    if not is_admin:
        return _admin_denied("PERMISSION_CHECK")
    target_role = params.get("target_role", "")
    target_action = params.get("target_action", "")
    role = store.role_by_name(target_role) if target_role else None
    if not role:
        return _not_found("PERMISSION_CHECK", "Permission Check",
                          not_found_summary("Role '{name}' not found.", target_role, "Please specify a role and action."))
    role_id = get_attr(role, "RoleId", "Role_Id", default="")
    accesses = [store.enrich_role_access(a)
                for a in store.role_access()
                if get_attr(a, "RoleId", "Role_Id") == role_id]
    if target_action:
        allowed = [a for a in accesses if a.get(target_action, "false").lower() == "true"]
        return _result("PERMISSION_CHECK",
                       f"Permission: {role.get('Name')} → {target_action}",
                       allowed,
                       f"Role '{role.get('Name')}' has '{target_action}' on {len(allowed)} module(s).",
                       role_name=role.get("Name"), action=target_action)
    return _result("PERMISSION_CHECK", f"All Permissions: {role.get('Name')}",
                   accesses, f"Role '{role.get('Name')}' has {len(accesses)} module permissions.",
                   role_name=role.get("Name"))


# ── PERIOD ────────────────────────────────────────────────────────────────────

def handle_period_list(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    periods = list(store.periods())
    return _result("PERIOD_LIST", "Reporting Periods", periods,
                   f"There are {len(periods)} reporting period(s) configured.", count=len(periods))


# ── RETURNS ───────────────────────────────────────────────────────────────────

def handle_returns_list(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    returns = [store.enrich_return(r) for r in store.returns()]
    active = [r for r in returns if r.get("Status", "").lower() == "true"]
    return _result("RETURNS_LIST", "XBRL Returns", returns,
                   f"There are {len(returns)} XBRL returns ({len(active)} active).",
                   count=len(returns), active=len(active))


def handle_returns_details(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    target = params.get("target_return", "")
    ret = store.return_by_name(target) if target else None
    if not ret:
        return _not_found("RETURNS_DETAILS", "Return Details",
                          not_found_summary("Return '{name}' not found.", target, "Please specify a return name."))
    return _result("RETURNS_DETAILS", f"Return: {ret.get('Name')}", [store.enrich_return(ret)],
                   f"Details for return '{ret.get('Name')}'.")


def handle_returns_by_period(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    period_name = params.get("period_name", "")
    periods = store.periods()
    period_id = None
    if period_name:
        for p in periods:
            if p.get("PeriodName", "").lower() == period_name.lower():
                period_id = p.get("Period_Id")
                break
    if not period_id:
        return _not_found("RETURNS_BY_PERIOD", "Returns by Period",
                          not_found_summary("Period '{name}' not found.", period_name, "Please specify a period."))
    rets = [store.enrich_return(r) for r in store.returns() if r.get("PeriodId") == period_id]
    return _result("RETURNS_BY_PERIOD", f"{period_name} Returns",
                   rets, f"Found {len(rets)} {period_name} XBRL return(s).", count=len(rets))


def handle_validation_returns(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    q_lower = " ".join(str(v) for v in params.values()).lower()
    results = []
    for r in store.returns():
        row = store.enrich_return(r)
        row["HasFormulaValidation"] = r.get("IsFormulaValidation", "false")
        row["HasSchCalcValidation"] = r.get("IsSchCalValidation", "false")
        row["HasLargeValidator"] = r.get("IsLargeValidator", "false")
        row["IsCIMS"] = r.get("IsCims", "false")
        results.append(row)

    # Filter based on what was asked
    if "formula" in q_lower:
        results = [r for r in results if r["HasFormulaValidation"].lower() == "true"]
        label = "Returns with Formula Validation"
    elif "schema" in q_lower or "sch" in q_lower:
        results = [r for r in results if r["HasSchCalcValidation"].lower() == "true"]
        label = "Returns with Schema-Calculation Validation"
    elif "large" in q_lower:
        results = [r for r in results if r["HasLargeValidator"].lower() == "true"]
        label = "Returns Using Large Validator"
    elif "cims" in q_lower:
        results = [r for r in results if r["IsCIMS"].lower() == "true"]
        label = "CIMS-Enabled Returns"
    else:
        label = "Returns with Validation Settings"

    return _result("VALIDATION_RETURNS", label, results,
                   f"Found {len(results)} return(s) matching validation criteria.", count=len(results))


def handle_non_xbrl_list(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    returns = list(store.non_xbrl_returns())
    return _result("NON_XBRL_LIST", "Non-XBRL Returns", returns,
                   f"There are {len(returns)} non-XBRL returns.", count=len(returns))


# ── INSTANCE LOG (submissions) ────────────────────────────────────────────────

def _enrich_log(store: XMLStore, log: dict) -> dict:
    """Delegate to XMLStore so all enrichment logic stays in one place."""
    return store.enrich_instance_log_entry(log)


def handle_submission_list(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    if not is_admin:
        return _admin_denied("SUBMISSION_LIST")
    logs = [_enrich_log(store, l) for l in store.instance_log()]
    return _result("SUBMISSION_LIST", "All Submissions",
                   logs, f"There are {len(logs)} submission records in total.", count=len(logs))


def handle_submission_status(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    if not is_admin:
        return _admin_denied("SUBMISSION_STATUS")
    target = params.get("target_return", "")
    ret = store.return_by_name(target) if target else None
    if not ret:
        return _not_found("SUBMISSION_STATUS", "Submission Status",
                          not_found_summary("Return '{name}' not found.", target, "Please specify a return name."))
    form_id = ret.get("ReturnId") or ret.get("Id", "")
    logs = [_enrich_log(store, l) for l in store.instance_log()
            if l.get("FormId") == form_id]
    return _result("SUBMISSION_STATUS", f"Submissions for: {ret.get('Name')}",
                   logs, f"Found {len(logs)} submission(s) for return '{ret.get('Name')}'.",
                   return_name=ret.get("Name"), count=len(logs))


def handle_submission_pending(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    if not is_admin:
        return _admin_denied("SUBMISSION_PENDING")
    pending = [_enrich_log(store, l) for l in store.instance_log()
               if l.get("Status") in ("0", "1", "2")]
    return _result("SUBMISSION_PENDING", "Pending Submissions",
                   pending, f"There are {len(pending)} pending submission(s).", count=len(pending))


def handle_submission_approved(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    if not is_admin:
        return _admin_denied("SUBMISSION_APPROVED")
    approved = [_enrich_log(store, l) for l in store.instance_log()
                if l.get("Status") in ("9", "11")]
    return _result("SUBMISSION_APPROVED", "Approved / Audited Submissions",
                   approved, f"Found {len(approved)} approved/audited submission(s).", count=len(approved))


# ── MENU ──────────────────────────────────────────────────────────────────────

def handle_menu_list(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    options = [o for o in store.options() if o.get("IsMenu", "").lower() == "true"]
    return _result("MENU_LIST", "System Menu & Modules",
                   options, f"There are {len(options)} menu items in the system.", count=len(options))


def handle_notification_list(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    """Return notification configuration from Notifications.xml / NotificationReturnDetails.xml."""
    target_return = params.get("target_return", "")
    notifs = list(store.notifications())
    details = list(store.notification_details())

    if target_return:
        ret = store.return_by_name(target_return)
        ret_id = ret.get("ReturnId") or ret.get("Id") if ret else None
        if ret_id:
            details = [d for d in details if d.get("ReturnId") == ret_id or d.get("FormId") == ret_id]
            notifs  = [n for n in notifs  if n.get("ReturnId") == ret_id or n.get("FormId") == ret_id]

    if not notifs and not details:
        return _not_found("NOTIFICATION_LIST", "Notifications",
                          f"No notification configuration found" +
                          (not_found_summary(" for return '{name}'.", target_return, ".")))

    records = notifs + details
    return _result("NOTIFICATION_LIST", "Notification Configuration",
                   records,
                   f"Found {len(records)} notification setting(s)" +
                   (not_found_summary(" for return '{name}'.", target_return, ".")),
                   count=len(records))


# ── AUDIT_SECURITY handlers ───────────────────────────────────────────────────
# XML_Audit.xml attrs:    OptionId, AuditDateTime, AuditType, UserId (=LoginId), Remark
# XML_UploadedFileLog.xml attrs: Id, FileName, DateTime, UserId (=LoginId)
# XML_CrossValidationLog.xml attrs: Id, FirstReportName, SecondReportName, Status, GeneratedBy (=LoginId)

def _audit_login_ids(store: XMLStore, user_id: str) -> set[str]:
    """Return the set of identifiers to match against audit/log UserId fields.

    Audit/log XMLs store LoginId (not numeric UserId) in their UserId/GeneratedBy fields.
    """
    u = _resolve_user(store, user_id)
    ids = {str(user_id)}
    if u:
        ids.add(u.get("LoginId", ""))
        ids.add(u.get("UserId", ""))
    return {i for i in ids if i}


def handle_my_audit_log(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    """What changes have I made in the system? — XML_Audit.xml filtered by LoginId."""
    ids = _audit_login_ids(store, user_id)
    entries = [store.enrich_log_entry(e)
               for e in store.audit_log()
               if e.get("UserId", "") in ids]
    entries.sort(key=lambda e: e.get("AuditDateTime", ""), reverse=True)
    return _result("MY_AUDIT_LOG", "My Activity History",
                   entries,
                   f"Found {len(entries)} audit record(s) for your account.",
                   count=len(entries))


def handle_my_upload_log(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    """Have any of my file uploads failed recently? — XML_UploadedFileLog.xml."""
    ids = _audit_login_ids(store, user_id)
    entries = [store.enrich_log_entry(e)
               for e in store.upload_file_log()
               if e.get("UserId", "") in ids]
    return _result("MY_UPLOAD_LOG", "My File Uploads",
                   entries,
                   f"Found {len(entries)} file upload record(s) for your account.",
                   count=len(entries))


def handle_my_cross_validation_log(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    """What cross-validation errors were recorded for my submissions?"""
    ids = _audit_login_ids(store, user_id)
    entries = [store.enrich_cross_val_entry(e)
               for e in store.cross_validation_log()
               if e.get("GeneratedBy", "") in ids]
    failed = [e for e in entries if e.get("Status", "").lower() == "fail"]
    return _result("MY_CROSS_VAL_LOG", "My Cross-Validation Results",
                   entries,
                   f"Found {len(entries)} cross-validation run(s); {len(failed)} failure(s).",
                   count=len(entries), failed=len(failed))


def handle_audit_log(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    """Admin: show all audit records, optionally filtered by target_user."""
    if not is_admin:
        return _admin_denied("AUDIT_LOG")
    target = params.get("target_user", "")
    entries = [store.enrich_log_entry(e) for e in store.audit_log()]
    if target:
        t = target.lower()
        entries = [e for e in entries
                   if t in e.get("UserId", "").lower()
                   or t in e.get("UserName", "").lower()]
    entries.sort(key=lambda e: e.get("AuditDateTime", ""), reverse=True)
    return _result("AUDIT_LOG", "Audit Log",
                   entries,
                   f"Found {len(entries)} audit record(s)" + (not_found_summary(" for '{name}'.", target, ".")),
                   count=len(entries))


def handle_cross_validation_log(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    """Admin: cross-validation errors, optionally filtered by return name."""
    if not is_admin:
        return _admin_denied("CROSS_VAL_LOG")
    target = params.get("target_return", "")
    entries = [store.enrich_cross_val_entry(e) for e in store.cross_validation_log()]
    if target:
        t = target.lower()
        entries = [e for e in entries
                   if t in e.get("FirstReportName", "").lower()
                   or t in e.get("SecondReportName", "").lower()]
    failed = [e for e in entries if e.get("Status", "").lower() == "fail"]
    return _result("CROSS_VAL_LOG", "Cross-Validation Log",
                   entries,
                   f"Found {len(entries)} cross-validation record(s); {len(failed)} failure(s)" +
                   (not_found_summary(" for return '{name}'.", target, ".")),
                   count=len(entries), failed=len(failed))


def handle_upload_log(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    """Admin: all uploaded file logs."""
    if not is_admin:
        return _admin_denied("UPLOAD_LOG")
    entries = [store.enrich_log_entry(e)
               for e in store.upload_file_log()
               if e.get("FileName", "").strip()]
    return _result("UPLOAD_LOG", "Uploaded File Log",
                   entries,
                   f"Found {len(entries)} file upload record(s).",
                   count=len(entries))


# ── BANK & SEGMENT ────────────────────────────────────────────────────────────

def handle_bank_info(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    banks = list(store.bank_details())
    return _result("BANK_INFO", "Bank Details",
                   banks, f"Bank details: {banks[0].get('BankName', 'N/A')} — {banks[0].get('BankType', '')}." if banks else "No bank details found.")


def handle_segment_info(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    segs = list(store.segments())
    return _result("SEGMENT_INFO", "Segment Types",
                   segs, f"There are {len(segs)} segment type(s): {', '.join(s.get('SegmentName', '') for s in segs)}.")


def handle_unknown(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    return _result("UNKNOWN", "Unknown Intent", [],
                   "I wasn't able to determine what data you're looking for from the application database. "
                   "Try rephrasing, or use the XBRL knowledge-base chat for taxonomy questions.")


# ── Wrapper handlers for LLM-based query_type routing ───────────────────────

def handle_db_list_users_wrapper(store: XMLStore, params: dict, user_id: str, is_admin: bool) -> dict:
    """Route db_list_users to appropriate handler based on query_type parameter."""
    query_type = params.get("query_type", "all").lower() if params else "all"
    
    if query_type == "active":
        return handle_user_list_active(store, params, user_id, is_admin)
    elif query_type == "inactive":
        return handle_user_list_inactive(store, params, user_id, is_admin)
    elif query_type == "count":
        return handle_user_count(store, params, user_id, is_admin)
    else:  # "all" or anything else
        return handle_user_list(store, params, user_id, is_admin)


# ── dispatch table ────────────────────────────────────────────────────────────

HANDLERS: dict[str, object] = {
    "USER_LIST":             handle_user_list,
    "USER_LIST_ACTIVE":      handle_user_list_active,
    "USER_LIST_INACTIVE":    handle_user_list_inactive,
    "USER_COUNT":            handle_user_count,
    "USER_PROFILE":          handle_user_profile,
    "USER_BY_DEPT":          handle_user_by_dept,
    "USER_BY_ROLE":          handle_user_by_role,
    "USER_NEVER_LOGIN":      handle_user_never_login,
    "USER_FAILED_LOGIN":     handle_user_failed_login,
    "USER_DUPLICATE_EMAIL":  handle_user_duplicate_email,
    "MY_PROFILE":            handle_my_profile,
    "MY_DEPARTMENT":         handle_my_department,
    "MY_ROLE":               handle_my_role,
    "MY_EMAIL":              handle_my_email,
    "MY_MOBILE":             handle_my_mobile,
    "MY_LAST_LOGIN":         handle_my_last_login,
    "MY_FAILED_LOGINS":      handle_my_failed_logins,
    "MY_STATUS":             handle_my_status,
    "MY_CREATED_DATE":       handle_my_created_date,
    "MY_LOGIN_ID":           handle_my_login_id,
    "MY_USER_CODE":          handle_my_user_code,
    "MY_PASSWORD_DATE":      handle_my_password_date,
    "MY_USER_LEVEL":         handle_my_user_level,
    "MY_ROLE_PEER_COUNT":    handle_my_role_peer_count,
    "MY_ROLE_PERMISSIONS":   handle_my_role_permissions,
    "MY_DEPT_RETURNS":       handle_my_dept_returns,
    "MY_SUBMISSIONS":        handle_my_submissions,
    "DEPT_LIST":             handle_dept_list,
    "DEPT_INFO":             handle_dept_info,
    "DEPT_RETURNS":          handle_dept_returns,
    "ROLE_LIST":             handle_role_list,
    "ROLE_PERMISSIONS":      handle_role_permissions,
    "ROLE_USERS":            handle_role_users,
    "MY_ROLE_PEER_COUNT":    handle_my_role_peer_count,
    "PERMISSION_CHECK":      handle_permission_check,
    "PERIOD_LIST":           handle_period_list,
    "USER_LEVEL_LIST":       handle_user_level_list,
    "RETURNS_LIST":          handle_returns_list,
    "RETURNS_DETAILS":       handle_returns_details,
    "RETURNS_BY_PERIOD":     handle_returns_by_period,
    "VALIDATION_RETURNS":    handle_validation_returns,
    "NON_XBRL_LIST":         handle_non_xbrl_list,
    "SUBMISSION_LIST":       handle_submission_list,
    "SUBMISSION_STATUS":     handle_submission_status,
    "SUBMISSION_PENDING":    handle_submission_pending,
    "SUBMISSION_APPROVED":   handle_submission_approved,
    "MENU_LIST":             handle_menu_list,
    "NOTIFICATION_LIST":     handle_notification_list,
    "MY_AUDIT_LOG":          handle_my_audit_log,
    "MY_UPLOAD_LOG":         handle_my_upload_log,
    "MY_CROSS_VAL_LOG":      handle_my_cross_validation_log,
    "AUDIT_LOG":             handle_audit_log,
    "CROSS_VAL_LOG":         handle_cross_validation_log,
    "UPLOAD_LOG":            handle_upload_log,
    "BANK_INFO":             handle_bank_info,
    "SEGMENT_INFO":          handle_segment_info,
    "UNKNOWN":               handle_unknown,
}

# ── LLM Intent Mapping (from unified intent extraction) ───────────────────
# Maps LLM-detected intents (db_*) to handler functions
# This enables both regex-based and LLM-based intent classification to use 
# the same query handlers
INTENT_TO_HANDLER: dict[str, object] = {
    # My-info queries (self-service, no admin check)
    "db_my_profile":        handle_my_profile,
    "db_my_department":     handle_my_department,
    "db_my_role":           handle_my_role,
    "db_my_permissions":    handle_my_role_permissions,
    "db_my_email":          handle_my_email,
    "db_my_mobile":         handle_my_mobile,
    "db_my_login_id":       handle_my_login_id,
    "db_my_user_code":      handle_my_user_code,
    "db_my_created_date":   handle_my_created_date,
    "db_my_password_date":  handle_my_password_date,
    "db_my_user_level":     handle_my_user_level,
    "db_my_role_peers":     handle_my_role_peer_count,
    "db_my_audit":          handle_my_audit_log,
    "db_my_uploads":        handle_my_upload_log,
    "db_my_cross_val":      handle_my_cross_validation_log,
    "db_my_status":         handle_my_status,
    "db_my_last_login":     handle_my_last_login,
    "db_my_failed_logins":  handle_my_failed_logins,
    "db_my_submissions":    handle_my_submissions,
    "db_my_dept_returns":   handle_my_dept_returns,

    # List queries (admin-only, routes based on query_type parameter)
    "db_list_users":        handle_db_list_users_wrapper,  # query_type: "all", "active", "inactive", "count"
    "db_list_departments":  handle_dept_list,
    "db_list_roles":        handle_role_list,
    "db_list_returns":      handle_returns_list,
    "db_user_levels":       handle_user_level_list,
    "db_menu_list":         handle_menu_list,
    "db_notifications":     handle_notification_list,
    "db_bank_info":         handle_bank_info,

    # Admin user lookups (extended)
    "db_user_by_dept":      handle_user_by_dept,
    "db_user_by_role":      handle_user_by_role,
    "db_user_never_login":  handle_user_never_login,
    "db_user_failed_login": handle_user_failed_login,
    "db_user_dupe_email":   handle_user_duplicate_email,

    # Returns / periods
    "db_non_xbrl_list":     handle_non_xbrl_list,
    "db_returns_by_period": handle_returns_by_period,
    "db_validation_returns": handle_validation_returns,
    "db_period_list":       handle_period_list,

    # Submissions
    "db_submission_list":   handle_submission_list,

    # Admin audit / log queries
    "db_audit_log":         handle_audit_log,
    "db_cross_val_log":     handle_cross_validation_log,
    "db_upload_log":        handle_upload_log,

    # Info queries (admin-only or self-service depending on target)
    "db_user_info":         handle_user_profile,       # target_user parameter
    "db_department_info":   handle_dept_info,          # target_department parameter
    "db_role_info":         handle_role_permissions,   # target_role parameter
    "db_dept_returns":      handle_dept_returns,       # which returns a dept has
    "db_role_users":        handle_role_users,         # which users have a role
    "db_permission_check":  handle_permission_check,   # can role X do action Y
    "db_segment_info":      handle_segment_info,       # bank segment info
}


# ── Auto-apply @trace to all handle_* functions for debug tracing ─────────────
# This adds ENTER/EXIT console output to every handler without touching each
# function individually.  The dispatch() below wraps the handler at call time
# so the traced version is always used regardless of dict reference timing.
import sys as _sys
from backend.utils.tracer import trace as _trace

_mod = _sys.modules[__name__]
for _fn_name in list(vars(_mod)):
    if _fn_name.startswith("handle_") and callable(getattr(_mod, _fn_name)):
        _fn = getattr(_mod, _fn_name)
        if not getattr(_fn, "__traced__", False):
            _t = _trace(_fn)
            _t.__traced__ = True          # prevent double-wrapping
            setattr(_mod, _fn_name, _t)
del _mod, _trace, _sys, _fn_name, _fn, _t   # keep module namespace clean


def dispatch(intent: str, params: dict, user_id: str, role_id: str, is_admin: bool, store: XMLStore) -> dict:
    """Run the handler for *intent* and return a QueryResult dict.
    
    Args:
        intent: LLM-detected intent (e.g., "db_list_users", "db_my_department")
        params: LLM-extracted parameters dict
        user_id: Current user's ID
        role_id: Current user's role ID
        is_admin: Whether user has admin privileges
        store: XMLStore instance with data
    
    Returns:
        QueryResult dict with intent, label, found, records, summary, meta
    """
    from backend.utils.debug import debug_log

    # Look up the original handler — then fetch the (possibly traced) version
    # from the module so @trace applied above is always called.
    _base_handler = INTENT_TO_HANDLER.get(intent, handle_unknown)
    _fn_name = getattr(_base_handler, "__name__",
                       getattr(getattr(_base_handler, "__wrapped__", None), "__name__", None))
    _this = sys.modules[__name__] if "sys" in dir() else __import__("sys").modules[__name__]
    handler = getattr(_this, _fn_name, _base_handler) if _fn_name else _base_handler

    debug_log(
        "QUERY HANDLER DISPATCH",
        intent=intent,
        handler=_fn_name or "handle_unknown",
        user_id=user_id,
        is_admin=is_admin,
        params=params or "{}",
    )
    return handler(store, params, user_id, is_admin)  # type: ignore[call-arg]

