"""New-taxonomy handlers — CROSS_ENTITY category (multi-entity joins)."""
from __future__ import annotations

from backend.db_qa.versions.loader import build_index
from backend.db_qa.xml_store import XMLStore, get_attr
from backend.db_qa.query_handlers._extraction_guard import not_found_summary
from backend.db_qa.query_handlers._return_resolution import resolve_named_return


def _result(intent: str, label: str, records: list, summary: str, **meta) -> dict:
    return {"intent": intent, "label": label, "found": bool(records), "records": records, "summary": summary, "meta": meta}


def _not_found(intent: str, label: str, msg: str) -> dict:
    return _result(intent, label, [], msg)


def _full_access_summary(store: XMLStore, u: dict) -> dict:
    role_id = get_attr(u, "RoleId", "Role_Id", default="")
    dept_id = get_attr(u, "DepartmentId", "DeptId", default="")
    role = store.role_by_id(role_id)
    dept = store.dept_by_id(dept_id)
    accesses = [store.enrich_role_access(a) for a in store.role_access()
                if get_attr(a, "RoleId", "Role_Id") == role_id]
    can_approve = any(a.get("HasApprove", "false").lower() == "true" for a in accesses)
    can_create = any(a.get("HasNew", "false").lower() == "true" for a in accesses)
    form_ids = {f.strip() for f in (dept or {}).get("Forms", "").split("|") if f.strip()}
    return {
        "Name": u.get("Name", ""),
        "LoginId": u.get("LoginId", ""),
        "RoleName": role.get("Name", "") if role else "",
        "DeptName": dept.get("Name", "") if dept else "",
        "CanApprove": can_approve,
        "CanCreate": can_create,
        "AccessibleReturnCount": len(form_ids),
        "ModulePermissionCount": len(accesses),
    }


def handle_user_access_summary(scope: dict, entities: dict, store: XMLStore) -> dict:
    if scope["target_type"] == "self":
        u = store.user_by_id(scope.get("user_id") or scope["login_id"]) or store.user_by_name(scope["login_id"])
        label = "My Access Summary"
    else:
        target = entities.get("target_user", "")
        u = store.resolve_user(target) if target else None
        label = f"Access Summary: {target}"
    if not u:
        return _not_found("user_access_summary", "Access Summary", "User profile could not be found.")

    summary_row = _full_access_summary(store, u)
    who_phrase = "You" if scope["target_type"] == "self" else summary_row["Name"] or "This user"
    return _result("user_access_summary", label, [summary_row],
                   f"{who_phrase} — role: {summary_row['RoleName']}, department: {summary_row['DeptName']}, "
                   f"access to {summary_row['AccessibleReturnCount']} return(s), "
                   f"{'can' if summary_row['CanApprove'] else 'cannot'} approve.",
                   **summary_row)


def handle_cross_entity_query(scope: dict, entities: dict, store: XMLStore) -> dict:
    target_department = entities.get("target_department", "")
    target_role = entities.get("target_role", "")
    target_return = entities.get("target_return", "")
    days_n = entities.get("days_n")

    # "who in department X can approve"
    if target_department and not target_role and not target_return:
        dept = store.dept_by_name(target_department)
        if not dept:
            return _not_found("cross_entity_query", "Cross-Entity Query", not_found_summary("Department '{name}' not found.", target_department, "Please specify a department name."))
        dept_id = get_attr(dept, "DeptId", "Id", default="")
        role_access_by_role = {}
        for a in store.role_access():
            rid = get_attr(a, "RoleId", "Role_Id", default="")
            if a.get("HasApprove", "false").lower() == "true":
                role_access_by_role[rid] = True
        matches = [store.enrich_user(u) for u in store.users()
                   if get_attr(u, "DepartmentId", "DeptId") == dept_id
                   and role_access_by_role.get(get_attr(u, "RoleId", "Role_Id", default=""))]
        return _result("cross_entity_query", f"Approvers in {dept.get('Name')}", matches,
                       f"{len(matches)} user(s) in '{dept.get('Name')}' can approve.", count=len(matches))

    # "users with role R AND department D"
    if target_role and target_department:
        role = store.role_by_name(target_role)
        dept = store.dept_by_name(target_department)
        if not role or not dept:
            missing = target_role if not role else target_department
            return _not_found("cross_entity_query", "Cross-Entity Query", not_found_summary("'{name}' not found.", missing, "Please specify a role and a department."))
        role_id = get_attr(role, "RoleId", "Role_Id", default="")
        dept_id = get_attr(dept, "DeptId", "Id", default="")
        matches = [store.enrich_user(u) for u in store.users()
                   if get_attr(u, "RoleId", "Role_Id") == role_id and get_attr(u, "DepartmentId", "DeptId") == dept_id]
        return _result("cross_entity_query", f"{role.get('Name')} + {dept.get('Name')}", matches,
                       f"{len(matches)} user(s) have role '{role.get('Name')}' in department '{dept.get('Name')}'.",
                       count=len(matches))

    # "role R with access to return X"
    if target_role and target_return:
        role = store.role_by_name(target_role)
        if not role:
            return _not_found("cross_entity_query", "Cross-Entity Query", not_found_summary("'{name}' not found.", target_role, "Please specify a role name."))
        ret, early = resolve_named_return(store, scope, target_return, intent="cross_entity_query", label="Cross-Entity Query")
        if early:
            return early
        role_id = get_attr(role, "RoleId", "Role_Id", default="")
        ret_id, ret_code = ret.get("Id", ""), ret.get("ReturnId", "")
        dept_index = {get_attr(d, "DeptId", "Id", default=""): d for d in store.departments()}
        matching_depts = {
            did for did, d in dept_index.items()
            if ret_id in {f.strip() for f in d.get("Forms", "").split("|")}
            or ret_code in {f.strip() for f in d.get("Forms", "").split("|")}
        }
        matches = [store.enrich_user(u) for u in store.users()
                   if get_attr(u, "RoleId", "Role_Id") == role_id
                   and get_attr(u, "DepartmentId", "DeptId") in matching_depts]
        return _result("cross_entity_query", f"{role.get('Name')} users with access to {ret.get('Name')}", matches,
                       f"{len(matches)} user(s) with role '{role.get('Name')}' have access to '{ret.get('Name')}'.",
                       count=len(matches))

    # "most recent submitter of return X"
    if target_return:
        ret, early = resolve_named_return(store, scope, target_return, intent="cross_entity_query", label="Cross-Entity Query")
        if early:
            return early
        form_id = ret.get("ReturnId") or ret.get("Id", "")
        logs = [store.enrich_instance_log_entry(l) for l in store.instance_log() if l.get("FormId") == form_id]
        logs.sort(key=lambda l: l.get("DTC", ""), reverse=True)
        if not logs:
            return _not_found("cross_entity_query", "Cross-Entity Query", f"No submissions found for '{ret.get('Name')}'.")
        recent = logs[0]
        return _result("cross_entity_query", f"Most Recent Submitter: {ret.get('Name')}", [recent],
                       f"{recent.get('UserName', '')} most recently submitted '{ret.get('Name')}' "
                       f"({recent.get('StatusLabel', '')}).")

    # "active users not logged in for more than N days" — best-effort without a
    # date-parsing dependency: treat blank LastLoginDT as "never", not "recent".
    if days_n:
        active = [u for u in store.users() if u.get("Status", "").lower() == "true"]
        stale = [u for u in active if not u.get("LastLoginDT", "").strip()]
        return _result("cross_entity_query", "Active Users With No Recent Login",
                       [store.enrich_user(u) for u in stale],
                       f"{len(stale)} active user(s) have no recorded login "
                       f"(exact day-count comparison requires date parsing not yet implemented).",
                       count=len(stale))

    return _not_found("cross_entity_query", "Cross-Entity Query",
                      "Please specify at least one of: department, role, return.")
