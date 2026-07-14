"""New-taxonomy handlers — ROLE, ROLE_ACCESS, USER_LEVEL categories."""
from __future__ import annotations

from collections import Counter

from backend.db_qa.versions.loader import build_index
from backend.db_qa.xml_store import XMLStore, get_attr

_ACTION_MAP: dict[str, str] = {
    "new": "HasNew", "create": "HasNew", "add": "HasNew",
    "edit": "HasEdit", "update": "HasEdit", "modify": "HasEdit",
    "view": "HasView", "see": "HasView", "read": "HasView",
    "approve": "HasApprove", "approval": "HasApprove",
}


def _result(intent: str, label: str, records: list, summary: str, **meta) -> dict:
    return {"intent": intent, "label": label, "found": bool(records), "records": records, "summary": summary, "meta": meta}


def _not_found(intent: str, label: str, msg: str) -> dict:
    return _result(intent, label, [], msg)


def _resolve_target_role(store: XMLStore, scope: dict, entities: dict) -> dict | None:
    if scope["target_type"] == "self":
        u = store.user_by_id(scope.get("user_id") or scope["login_id"]) or store.user_by_name(scope["login_id"])
        if not u:
            return None
        role_id = get_attr(u, "RoleId", "Role_Id", default="")
        return store.role_by_id(role_id) if role_id else None
    target = entities.get("target_role", "")
    return store.resolve_role(target) if target else None


def handle_role_list(scope: dict, entities: dict, store: XMLStore) -> dict:
    query_type = (entities.get("query_type") or "all").lower()
    roles = store.roles()

    if query_type == "count":
        active = sum(1 for r in roles if r.get("Status", "").lower() == "true")
        return _result("role_list", "Role Count",
                       [{"total": len(roles), "active": active, "inactive": len(roles) - active}],
                       f"Total roles: {len(roles)} ({active} active, {len(roles) - active} inactive).",
                       total=len(roles), active=active)
    elif query_type == "active_count":
        n = sum(1 for r in roles if r.get("Status", "").lower() == "true")
        return _result("role_list", "Active Role Count", [{"active": n}], f"Active roles: {n}.", active=n)
    elif query_type == "inactive_count":
        n = sum(1 for r in roles if r.get("Status", "").lower() != "true")
        return _result("role_list", "Inactive Role Count", [{"inactive": n}], f"Inactive roles: {n}.", inactive=n)
    elif query_type == "active":
        rows = [r for r in roles if r.get("Status", "").lower() == "true"]
        label, summary = "Active Roles", f"There are {len(rows)} active roles."
    elif query_type == "inactive":
        rows = [r for r in roles if r.get("Status", "").lower() != "true"]
        label, summary = "Inactive Roles", f"There are {len(rows)} inactive roles."
    elif query_type in ("most_users", "with_counts"):
        counts = Counter(get_attr(u, "RoleId", "Role_Id", default="") for u in store.users())
        enriched = []
        for r in roles:
            row = dict(r)
            row["UserCount"] = counts.get(get_attr(r, "RoleId", "Role_Id", default=""), 0)
            enriched.append(row)
        if query_type == "most_users":
            enriched.sort(key=lambda r: r["UserCount"], reverse=True)
            rows = enriched[:1]
            label = "Role With Most Users"
            summary = f"'{rows[0].get('Name')}' has the most users ({rows[0]['UserCount']})." if rows else "No roles found."
        else:
            rows = enriched
            label, summary = "All Roles (With User Counts)", f"There are {len(rows)} roles."
    elif query_type == "exists":
        target = entities.get("target_role", "")
        match = store.role_by_name(target) if target else None
        rows = [match] if match else []
        label = "Role Existence Check"
        summary = (f"Yes, role '{target}' exists." if match else f"No role named '{target}' was found.")
    else:
        rows = roles
        label, summary = "All Roles", f"There are {len(rows)} roles defined in the system."

    return _result("role_list", label, rows, summary, count=len(rows))


def handle_role_profile(scope: dict, entities: dict, store: XMLStore) -> dict:
    role = _resolve_target_role(store, scope, entities)
    if not role:
        who = "Your" if scope["target_type"] == "self" else f"'{entities.get('target_role', '')}'"
        return _not_found("role_profile", "Role Profile", f"{who} role could not be found.")
    label = "My Role" if scope["target_type"] == "self" else f"Role: {role.get('Name')}"
    who_phrase = "Your" if scope["target_type"] == "self" else "The"
    return _result("role_profile", label, [role],
                   f"{who_phrase} role is '{role.get('Name')}' (id {get_attr(role, 'RoleId', 'Role_Id', default='')}).")


def handle_role_users(scope: dict, entities: dict, store: XMLStore) -> dict:
    target = entities.get("target_role", "")
    role = store.role_by_name(target) if target else None
    if not role:
        return _not_found("role_users", "Users With Role",
                          f"Role '{target}' not found." if target else "Please specify a role name.")
    role_id = get_attr(role, "RoleId", "Role_Id", default="")
    users = [store.enrich_user(u) for u in store.users() if get_attr(u, "RoleId", "Role_Id") == role_id]
    return _result("role_users", f"Users with Role: {role.get('Name')}", users,
                   f"Found {len(users)} user(s) with role '{role.get('Name')}'.",
                   role_name=role.get("Name"), count=len(users))


def handle_role_peer_count(scope: dict, entities: dict, store: XMLStore) -> dict:
    u = store.user_by_id(scope.get("user_id") or scope["login_id"]) or store.user_by_name(scope["login_id"])
    if not u:
        return _not_found("role_peer_count", "Users with My Role", "Your profile could not be found.")
    role_id = get_attr(u, "RoleId", "Role_Id", default="")
    my_uid = u.get("UserId", "")
    peers = [pu for pu in store.users()
             if get_attr(pu, "RoleId", "Role_Id") == role_id and pu.get("UserId") != my_uid]
    role_name = store.role_name_by_id(role_id)
    return _result("role_peer_count", f"Users with Role: {role_name}",
                   [store.enrich_user(p) for p in peers],
                   f"{len(peers)} other user(s) share the '{role_name}' role with you.",
                   role_name=role_name, count=len(peers))


def handle_permission_profile(scope: dict, entities: dict, store: XMLStore) -> dict:
    role = _resolve_target_role(store, scope, entities)
    if not role:
        who = "Your" if scope["target_type"] == "self" else f"'{entities.get('target_role', '')}'"
        return _not_found("permission_profile", "Permission Profile", f"{who} role could not be found.")
    role_id = get_attr(role, "RoleId", "Role_Id", default="")
    accesses = [store.enrich_role_access(a) for a in store.role_access()
                if get_attr(a, "RoleId", "Role_Id") == role_id]
    who_phrase = "Your role" if scope["target_type"] == "self" else f"Role '{role.get('Name')}'"
    label = "My Permissions" if scope["target_type"] == "self" else f"Permissions for Role: {role.get('Name')}"
    return _result("permission_profile", label, accesses,
                   f"{who_phrase} has access to {len(accesses)} module(s).",
                   role_name=role.get("Name"), count=len(accesses))


def handle_permission_check(scope: dict, entities: dict, store: XMLStore) -> dict:
    role = _resolve_target_role(store, scope, entities)
    if not role:
        who = "Your" if scope["target_type"] == "self" else f"'{entities.get('target_role', '')}'"
        return _not_found("permission_check", "Permission Check", f"{who} role could not be found.")
    action_word = entities.get("action", "")
    attr = _ACTION_MAP.get(action_word.lower(), "")
    if not attr:
        return _not_found("permission_check", "Permission Check", f"Unrecognized action {action_word!r}.")
    role_id = get_attr(role, "RoleId", "Role_Id", default="")
    module = entities.get("module", "")
    accesses = [store.enrich_role_access(a) for a in store.role_access()
                if get_attr(a, "RoleId", "Role_Id") == role_id]
    if module:
        accesses = [a for a in accesses if module.lower() in a.get("OptionName", "").lower()]
    allowed = [a for a in accesses if a.get(attr, "false").lower() == "true"]
    who_phrase = "You" if scope["target_type"] == "self" else role.get("Name", "")
    can = "can" if allowed else "cannot"
    module_phrase = f" on {module}" if module else ""
    return _result("permission_check", f"Permission Check: {action_word}{module_phrase}",
                   allowed, f"{who_phrase} {can} {action_word}{module_phrase}.",
                   action=action_word, module=module, count=len(allowed))


def handle_roles_with_permission(scope: dict, entities: dict, store: XMLStore) -> dict:
    action_word = entities.get("action", "")
    attr = _ACTION_MAP.get(action_word.lower(), "")
    if not attr:
        return _not_found("roles_with_permission", "Roles With Permission", f"Unrecognized action {action_word!r}.")
    module = entities.get("module", "")
    role_index = build_index(store.roles(), "RoleId")
    matches = []
    for a in store.role_access():
        if a.get(attr, "false").lower() != "true":
            continue
        if module and module.lower() not in store.option_name_by_id(a.get("OptionId", "")).lower():
            continue
        role = role_index.get(get_attr(a, "RoleId", "Role_Id", default=""))
        if role:
            matches.append(role)
    # de-dup by RoleId while preserving order
    seen: set[str] = set()
    unique = []
    for r in matches:
        rid = get_attr(r, "RoleId", "Role_Id", default="")
        if rid not in seen:
            seen.add(rid)
            unique.append(r)
    module_phrase = f" on {module}" if module else ""
    return _result("roles_with_permission", f"Roles That Can {action_word}{module_phrase}",
                   unique, f"{len(unique)} role(s) can {action_word}{module_phrase}.", count=len(unique))


def handle_role_module_access(scope: dict, entities: dict, store: XMLStore) -> dict:
    module = entities.get("module", "")
    target_role = entities.get("target_role", "")
    if target_role:
        role = store.role_by_name(target_role)
        if not role:
            return _not_found("role_module_access", "Role Module Access", f"Role '{target_role}' not found.")
        role_id = get_attr(role, "RoleId", "Role_Id", default="")
        accesses = [store.enrich_role_access(a) for a in store.role_access()
                    if get_attr(a, "RoleId", "Role_Id") == role_id]
        return _result("role_module_access", f"Modules Accessible to {role.get('Name')}",
                       accesses, f"Role '{role.get('Name')}' has access to {len(accesses)} module(s).",
                       role_name=role.get("Name"), count=len(accesses))
    if module:
        role_index = build_index(store.roles(), "RoleId")
        matches = []
        for a in store.role_access():
            if module.lower() not in store.option_name_by_id(a.get("OptionId", "")).lower():
                continue
            role = role_index.get(get_attr(a, "RoleId", "Role_Id", default=""))
            if role:
                matches.append(role)
        return _result("role_module_access", f"Roles With Access to {module}",
                       matches, f"{len(matches)} role(s) have access to '{module}'.", count=len(matches))
    return _not_found("role_module_access", "Role Module Access", "Please specify a role or a module.")


def handle_role_permission_diff(scope: dict, entities: dict, store: XMLStore) -> dict:
    role_a_name = entities.get("target_role", "")
    role_b_name = entities.get("role_b", "")
    role_a = store.role_by_name(role_a_name) if role_a_name else None
    role_b = store.role_by_name(role_b_name) if role_b_name else None
    if not role_a or not role_b:
        missing = role_a_name if not role_a else role_b_name
        return _not_found("role_permission_diff", "Role Permission Diff", f"Role '{missing}' not found.")

    a_id = get_attr(role_a, "RoleId", "Role_Id", default="")
    b_id = get_attr(role_b, "RoleId", "Role_Id", default="")
    a_access = build_index(
        [store.enrich_role_access(x) for x in store.role_access() if get_attr(x, "RoleId", "Role_Id") == a_id],
        "OptionId",
    )
    b_access = build_index(
        [store.enrich_role_access(x) for x in store.role_access() if get_attr(x, "RoleId", "Role_Id") == b_id],
        "OptionId",
    )
    all_options = set(a_access) | set(b_access)
    rows = []
    for opt_id in all_options:
        a_row, b_row = a_access.get(opt_id), b_access.get(opt_id)
        name = (a_row or b_row or {}).get("OptionName", opt_id)
        rows.append({
            "Module": name,
            f"{role_a.get('Name')}_HasNew": (a_row or {}).get("HasNew", "false"),
            f"{role_b.get('Name')}_HasNew": (b_row or {}).get("HasNew", "false"),
            f"{role_a.get('Name')}_HasEdit": (a_row or {}).get("HasEdit", "false"),
            f"{role_b.get('Name')}_HasEdit": (b_row or {}).get("HasEdit", "false"),
            f"{role_a.get('Name')}_HasView": (a_row or {}).get("HasView", "false"),
            f"{role_b.get('Name')}_HasView": (b_row or {}).get("HasView", "false"),
            f"{role_a.get('Name')}_HasApprove": (a_row or {}).get("HasApprove", "false"),
            f"{role_b.get('Name')}_HasApprove": (b_row or {}).get("HasApprove", "false"),
        })
    return _result("role_permission_diff", f"{role_a.get('Name')} vs {role_b.get('Name')}",
                   rows, f"Compared {len(rows)} module(s) between '{role_a.get('Name')}' and '{role_b.get('Name')}'.",
                   role_a=role_a.get("Name"), role_b=role_b.get("Name"))


def handle_user_level_list(scope: dict, entities: dict, store: XMLStore) -> dict:
    level = entities.get("level", "")
    levels = list(store.user_levels())
    if not levels:
        return _not_found("user_level_list", "User Levels",
                          "No user levels (L1/L2/L3) are configured in this system.")
    if level:
        levels = [lv for lv in levels if lv.get("Name", "").upper() == level.upper()]
    return _result("user_level_list", "User Levels", levels,
                   f"There are {len(levels)} user level(s) defined in the system.", count=len(levels))


def handle_user_level_self(scope: dict, entities: dict, store: XMLStore) -> dict:
    u = store.user_by_id(scope.get("user_id") or scope["login_id"]) or store.user_by_name(scope["login_id"])
    if not u:
        return _not_found("user_level_self", "My User Level", "Your profile could not be found.")
    level_name, level_id = store.user_level_for_user(u)
    if not level_name:
        return _not_found("user_level_self", "My User Level",
                          "No user level (L1/L2/L3) is assigned to your account in this department.")
    return _result("user_level_self", "My User Level",
                   [{"LevelName": level_name, "LevelId": level_id}],
                   f"Your user level is: {level_name}.")
