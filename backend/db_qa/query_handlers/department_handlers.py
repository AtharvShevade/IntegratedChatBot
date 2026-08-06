"""New-taxonomy handlers — DEPARTMENT category."""
from __future__ import annotations

from collections import Counter

from backend.db_qa.xml_store import XMLStore, get_attr, is_active_status
from backend.db_qa.query_handlers._return_resolution import resolve_named_return


def _result(intent: str, label: str, records: list, summary: str, **meta) -> dict:
    return {"intent": intent, "label": label, "found": bool(records), "records": records, "summary": summary, "meta": meta}


def _not_found(intent: str, label: str, msg: str) -> dict:
    return _result(intent, label, [], msg)


_UNDERSTAND_FAILURE_MSG = "Sorry, I couldn't understand your request. Could you rephrase it?"


def _department_not_found(intent: str, label: str, scope: dict, entities: dict) -> dict:
    """Shared not-found response for every handler that resolves a target
    department. Two genuinely different situations, both of which used to
    produce the same confusing message built from whatever the entity
    extractor happened to capture (e.g. "'ID of department dept1' department
    could not be found." when extraction mis-parsed the sentence, or "''
    department could not be found." when nothing was extracted at all) —
    internal parser output should never reach the user:

      1. Nothing was extracted (empty/whitespace-only target_department) —
         this means the QUESTION itself wasn't understood, not that a real
         department name came back empty-handed. Ask the user to rephrase
         rather than reporting a not-found on a blank name.
      2. A real name WAS extracted but no such department exists — report
         exactly that name, quoted, and nothing else.

    Self-scoped lookups ("my department") are a different failure mode
    entirely (the caller's own department couldn't be resolved from
    XML_User.xml — a data/session issue, not a user-input issue) and keep
    their own message.
    """
    if scope.get("target_type") == "self":
        return _not_found(intent, label, "Your department could not be found.")
    name = (entities.get("target_department") or "").strip()
    if not name:
        return _not_found(intent, label, _UNDERSTAND_FAILURE_MSG)
    return _not_found(intent, label, f"Department '{name}' was not found.")


def _return_counts_for_dept(store: XMLStore, dept: dict) -> tuple[int, int]:
    form_ids = {f.strip() for f in dept.get("Forms", "").split("|") if f.strip()}
    nx_ids = {f.strip() for f in dept.get("NXForms", "").split("|") if f.strip()}
    xbrl_count = sum(1 for r in store.returns() if r.get("Id") in form_ids or r.get("ReturnId") in form_ids)
    non_xbrl_count = sum(1 for r in store.non_xbrl_returns() if r.get("Id") in nx_ids or r.get("ReturnId") in nx_ids)
    return xbrl_count, non_xbrl_count


def _resolve_target_department(store: XMLStore, scope: dict, entities: dict) -> dict | None:
    if scope["target_type"] == "self":
        u = store.user_by_id(scope.get("user_id") or scope["login_id"]) or store.user_by_name(scope["login_id"])
        if not u:
            return None
        dept_id = get_attr(u, "DepartmentId", "DeptId", default="")
        return store.dept_by_id(dept_id) if dept_id else None
    target = entities.get("target_department", "")
    return store.resolve_dept(target) if target else None


def handle_department_list(scope: dict, entities: dict, store: XMLStore) -> dict:
    query_type = (entities.get("query_type") or "all").lower()
    depts = store.departments()

    if query_type == "count":
        active = sum(1 for d in depts if is_active_status(d.get("Status")))
        return _result("department_list", "Department Count",
                       [{"total": len(depts), "active": active, "inactive": len(depts) - active}],
                       f"Total departments: {len(depts)} ({active} active, {len(depts) - active} inactive).",
                       total=len(depts), active=active)
    elif query_type == "active_count":
        n = sum(1 for d in depts if is_active_status(d.get("Status")))
        return _result("department_list", "Active Department Count", [{"active": n}],
                       f"Active departments: {n}.", active=n)
    elif query_type == "inactive_count":
        n = sum(1 for d in depts if not is_active_status(d.get("Status")))
        return _result("department_list", "Inactive Department Count", [{"inactive": n}],
                       f"Inactive departments: {n}.", inactive=n)
    elif query_type == "active":
        rows = [d for d in depts if is_active_status(d.get("Status"))]
        label, summary = "Active Departments", f"There are {len(rows)} active departments."
    elif query_type == "inactive":
        rows = [d for d in depts if not is_active_status(d.get("Status"))]
        label, summary = "Inactive Departments", f"There are {len(rows)} inactive departments."
    elif query_type in ("most", "fewest", "no_returns", "with_counts", "top_n"):
        # Split XBRL/Non-XBRL counts, not just a combined total — added so
        # a "list departments with return count" table can show both
        # breakdowns (previously only TotalReturnCount was kept, so the
        # per-type counts _return_counts_for_dept already computes were
        # silently thrown away here).
        enriched = []
        for d in depts:
            xbrl, nx = _return_counts_for_dept(store, d)
            row = dict(d)
            row["XbrlReturnCount"] = xbrl
            row["NonXbrlReturnCount"] = nx
            row["TotalReturnCount"] = xbrl + nx
            enriched.append(row)
        if query_type == "no_returns":
            rows = [d for d in enriched if d["TotalReturnCount"] == 0]
            label, summary = "Departments With No Returns Assigned", f"Found {len(rows)} department(s) with no returns."
        elif query_type == "most":
            enriched.sort(key=lambda d: d["TotalReturnCount"], reverse=True)
            rows = enriched[:1]
            label = "Department With Most Returns"
            summary = (f"'{rows[0].get('Name')}' has the most returns assigned ({rows[0]['TotalReturnCount']})."
                       if rows else "No departments found.")
        elif query_type == "fewest":
            enriched.sort(key=lambda d: d["TotalReturnCount"])
            rows = enriched[:1]
            label = "Department With Fewest Returns"
            summary = (f"'{rows[0].get('Name')}' has the fewest returns assigned ({rows[0]['TotalReturnCount']})."
                       if rows else "No departments found.")
        elif query_type == "top_n":
            n = entities.get("top_n") or 5
            enriched.sort(key=lambda d: d["TotalReturnCount"], reverse=True)
            rows = enriched[:n]
            label = f"Top {n} Departments By Return Count"
            summary = (f"Top {len(rows)} department(s) by return count: " +
                       ", ".join(f"{r.get('Name')} ({r['TotalReturnCount']})" for r in rows) + "."
                       if rows else "No departments found.")
        else:  # with_counts
            rows = enriched
            label, summary = "All Departments (With Return Counts)", f"There are {len(rows)} departments."
    else:
        rows = depts
        label, summary = "All Departments", f"There are {len(rows)} departments in the system."

    return _result("department_list", label, rows, summary, count=len(rows))


def handle_department_profile(scope: dict, entities: dict, store: XMLStore) -> dict:
    dept = _resolve_target_department(store, scope, entities)
    if not dept:
        return _department_not_found("department_profile", "Department Profile", scope, entities)
    dept_id = get_attr(dept, "DeptId", "Id", default="")
    user_count = sum(1 for u in store.users() if get_attr(u, "DepartmentId", "DeptId") == dept_id)
    xbrl_count, non_xbrl_count = _return_counts_for_dept(store, dept)
    enriched = dict(dept)
    enriched["UserCount"] = user_count
    enriched["XbrlReturnCount"] = xbrl_count
    enriched["NonXbrlReturnCount"] = non_xbrl_count
    enriched["TotalReturnCount"] = xbrl_count + non_xbrl_count
    label = "My Department" if scope["target_type"] == "self" else f"Department: {dept.get('Name')}"
    return _result("department_profile", label, [enriched],
                   f"Department '{dept.get('Name')}' (id {dept_id}) has {user_count} user(s) and "
                   f"{xbrl_count + non_xbrl_count} return(s) assigned ({xbrl_count} XBRL, {non_xbrl_count} non-XBRL).")


def _return_access_row(ret: dict) -> dict:
    """Return-Code / Return-Name / Return-ID row for a department's
    accessible-returns table.

    ReturnCode is the raw code the department's Forms/NXForms list
    references (Returns.xml's "Id" attribute, e.g. "2030" — distinct from
    the human-facing ReturnId code, e.g. "R009"). On 6.0 there is no
    separate ReturnId attribute at all (v6_0_schema.py maps it to None), so
    `ret.get("ReturnId") or ret.get("Id", "")` falls back to the same code
    shown in ReturnCode — same fallback pattern used everywhere else in
    this codebase that needs a return's "ReturnId for this FormId".
    """
    return {
        "ReturnCode": ret.get("Id", ""),
        "ReturnLabel": ret.get("Name", ""),
        "ReturnId": ret.get("ReturnId") or ret.get("Id", ""),
    }


def handle_department_returns(scope: dict, entities: dict, store: XMLStore) -> dict:
    dept = _resolve_target_department(store, scope, entities)
    if not dept:
        return _department_not_found("department_returns", "Department Returns", scope, entities)

    # dept.get(...) may list the same code more than once (e.g.
    # "2014|2033|...|2033") — harmless here since xbrl/non_xbrl are built by
    # filtering the master returns list (one entry per real return), not by
    # iterating the code list, so a repeated code can never produce a
    # duplicate row.
    form_ids = [f.strip() for f in dept.get("Forms", "").split("|") if f.strip()]
    nx_ids = [f.strip() for f in dept.get("NXForms", "").split("|") if f.strip()]
    xbrl_type = entities.get("xbrl_type")

    xbrl = [store.enrich_return(r) for r in store.returns() if r.get("ReturnId") in form_ids or r.get("Id") in form_ids]
    non_xbrl = [dict(r) for r in store.non_xbrl_returns() if r.get("ReturnId") in nx_ids or r.get("Id") in nx_ids]

    if xbrl_type == "non_xbrl":
        records = [_return_access_row(r) for r in non_xbrl]
    elif xbrl_type == "xbrl":
        records = [_return_access_row(r) for r in xbrl]
    else:
        records = [_return_access_row(r) for r in xbrl] + [_return_access_row(r) for r in non_xbrl]

    dept_name = dept.get("Name", "")
    who_phrase = "Your department" if scope["target_type"] == "self" else f"Department '{dept_name}'"
    label = "Returns Accessible To Your Department" if scope["target_type"] == "self" else f"Returns of {dept_name}"
    if xbrl_type == "xbrl":
        label += " (XBRL)"
    elif xbrl_type == "non_xbrl":
        label += " (Non-XBRL)"

    if xbrl_type == "xbrl":
        summary = (f"{who_phrase} has access to {len(xbrl)} XBRL return(s)." if xbrl
                    else f"{who_phrase} does not currently have access to any XBRL returns.")
    elif xbrl_type == "non_xbrl":
        summary = (f"{who_phrase} has access to {len(non_xbrl)} non-XBRL return(s)." if non_xbrl
                    else f"{who_phrase} does not currently have access to any non-XBRL returns.")
    elif len(xbrl) + len(non_xbrl) == 0:
        summary = f"{who_phrase} does not currently have access to any returns."
    else:
        summary = f"{who_phrase} has access to {len(xbrl)} XBRL and {len(non_xbrl)} non-XBRL return(s) ({len(xbrl) + len(non_xbrl)} total)."
    return _result("department_returns", label, records, summary,
                   dept_name=dept_name, xbrl_count=len(xbrl), non_xbrl_count=len(non_xbrl))


def handle_departments_with_return_access(scope: dict, entities: dict, store: XMLStore) -> dict:
    target = entities.get("target_return", "")
    ret, early = resolve_named_return(store, scope, target, intent="departments_with_return_access", label="Departments With Return Access")
    if early:
        return early
    ret_id = ret.get("Id", "")
    ret_code = ret.get("ReturnId", "")
    matches = []
    for d in store.departments():
        form_ids = {f.strip() for f in d.get("Forms", "").split("|") if f.strip()}
        nx_ids = {f.strip() for f in d.get("NXForms", "").split("|") if f.strip()}
        if ret_id in form_ids or ret_code in form_ids or ret_id in nx_ids or ret_code in nx_ids:
            matches.append(d)
    return _result("departments_with_return_access", f"Departments With Access to {ret.get('Name')}",
                   matches, f"{len(matches)} department(s) have access to return '{ret.get('Name')}'.",
                   return_name=ret.get("Name"), count=len(matches))


def handle_department_has_return(scope: dict, entities: dict, store: XMLStore) -> dict:
    dept = _resolve_target_department(store, scope, entities)
    if not dept:
        return _department_not_found("department_has_return", "Department Return Access", scope, entities)
    target = entities.get("target_return", "")
    # enforce_department_auth=False: this answers "does department Y have
    # access to X" — a return outside the ASKING user's own allowed set is
    # still a valid, truthful question about ANOTHER department's access,
    # not something to deny (unlike return_profile/next_reporting_date/
    # etc., which would leak the return's own content).
    ret, early = resolve_named_return(
        store, scope, target, intent="department_has_return", label="Department Return Access",
        enforce_department_auth=False,
    )
    if early:
        return early
    form_ids = {f.strip() for f in dept.get("Forms", "").split("|") if f.strip()}
    nx_ids = {f.strip() for f in dept.get("NXForms", "").split("|") if f.strip()}
    has_access = ret.get("Id", "") in form_ids or ret.get("ReturnId", "") in form_ids \
        or ret.get("Id", "") in nx_ids or ret.get("ReturnId", "") in nx_ids
    dept_name = dept.get("Name", "")
    who_phrase = "Your department" if scope["target_type"] == "self" else f"Department '{dept_name}'"
    verb = "does" if has_access else "does not"
    return _result("department_has_return", f"{dept_name} <-> {ret.get('Name')}",
                   [{"DeptName": dept_name, "ReturnName": ret.get("Name"), "HasAccess": has_access}],
                   f"{who_phrase} {verb} have access to return '{ret.get('Name')}'.",
                   has_access=has_access)
