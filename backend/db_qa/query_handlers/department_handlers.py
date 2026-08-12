"""New-taxonomy handlers — DEPARTMENT category."""
from __future__ import annotations

from collections import Counter

from backend.db_qa.xml_store import XMLStore, get_attr, is_active_status
from backend.db_qa.query_handlers._return_resolution import resolve_named_return
from backend.db_qa.query_handlers._extraction_guard import looks_like_extraction_garbage


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
    # Case 1 also covers an extraction that captured sentence grammar
    # instead of a name ("has most return", "are currently active"): quoting
    # it back reads as though we searched for a department by that name, and
    # tells the user their own parser mis-fired. See _extraction_guard.
    if not name or looks_like_extraction_garbage(name):
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

    if query_type == "ambiguous_quantity":
        # "few"/"some"/"several" returns has no fixed threshold — unlike
        # "fewest" (a ranking) or "no returns" (a count of exactly zero),
        # there's no deterministic answer to compute here, so ask the user
        # to be specific rather than silently guessing what "few" means.
        return _not_found(
            "department_list", "Departments",
            "Could you clarify what you mean by 'few'? For example, ask for the department "
            "with the fewest returns, departments with no returns assigned, or a specific count.",
        )

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
            label = "All Departments (With Return Counts)"
            total = sum(d["TotalReturnCount"] for d in rows)
            # "There are 15 departments." reads as the answer to "how many
            # departments are there" — the very question this branch exists
            # to be distinguished from. Say what the table below actually
            # shows instead.
            summary = (f"{len(rows)} department(s), with XBRL, non-XBRL and total return "
                       f"counts for each ({total} assignments in total).")
    else:
        rows = depts
        label, summary = "All Departments", f"There are {len(rows)} departments in the system."

    return _result("department_list", label, rows, summary, count=len(rows),
                   show_dept_id=bool(entities.get("want_dept_id")))


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
                   f"{xbrl_count + non_xbrl_count} return(s) assigned ({xbrl_count} XBRL, {non_xbrl_count} non-XBRL).",
                   show_dept_id=bool(entities.get("want_dept_id")))


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


def _handle_departments_with_type_access(xbrl_type: str | None, store: XMLStore, want_dept_id: bool) -> dict:
    """"Which departments can access non-XBRL returns?" — the type-level
    form of this intent: no single return is named, so the answer is every
    department holding at least one return of that TYPE.

    Kept inside departments_with_return_access rather than given its own
    intent because it is the same question ("which departments can access
    <X>") with a category in place of a name; the classifier drops the
    generic phrase from target_return (see _clean_extracted_return_name)
    and flags the category as xbrl_type instead.
    """
    # xbrl_type None = BOTH, matching _extract_xbrl_type's contract: "which
    # departments can access returns?" with no type named previously fell to
    # the named-return path with no name and answered "0 departments".
    label_phrase = {"non_xbrl": "non-XBRL ", "xbrl": "XBRL "}.get(xbrl_type, "")
    if xbrl_type == "non_xbrl":
        attrs, rows = ("NXForms",), list(store.non_xbrl_returns())
    elif xbrl_type == "xbrl":
        attrs, rows = ("Forms",), list(store.returns())
    else:
        attrs, rows = ("Forms", "NXForms"), list(store.returns()) + list(store.non_xbrl_returns())
    # Membership is resolved against the real return rows of that type, not
    # just "the access list is non-empty" — a department's list can carry a
    # stale code for a return that no longer exists, which would otherwise
    # count as access to a return nobody can actually file.
    type_ids = {v for r in rows for v in (r.get("Id", ""), r.get("ReturnId", "")) if v}
    matches = []
    for d in store.departments():
        ids = {f.strip() for a in attrs for f in (d.get(a) or "").split("|") if f.strip()}
        if ids & type_ids:
            matches.append(d)
    return _result(
        "departments_with_return_access", f"Departments With Access to {label_phrase}Returns".replace("  ", " "),
        matches, f"{len(matches)} department(s) have access to at least one {label_phrase}return.".replace("  ", " ")
        if matches else f"No department currently has access to any {label_phrase}return.".replace("  ", " "),
        count=len(matches), show_dept_id=want_dept_id, xbrl_type=xbrl_type,
    )


def handle_departments_with_return_access(scope: dict, entities: dict, store: XMLStore) -> dict:
    target = entities.get("target_return", "")
    xbrl_type = entities.get("xbrl_type")
    if not target:
        # No return NAMED at all -> this is the type-level form of the
        # question ("which departments can access [XBRL|Non-XBRL] returns?").
        # The untyped variant is included: it used to fall through to the
        # named-return path with an empty name and answer "0 departments",
        # even though the XBRL and Non-XBRL variants both answered fine.
        # A name that was given but is unrecognised still reaches the
        # resolver below (target is non-empty then), so this cannot swallow
        # a genuine "return not found".
        return _handle_departments_with_type_access(
            xbrl_type, store, bool(entities.get("want_dept_id")))
    # enforce_department_auth=False: this is a cross-department AUDIT
    # question ("which departments have access to X") — the caller's own
    # department's access to X is irrelevant to answering it truthfully,
    # and without this an admin asking about a return outside their own
    # department's Forms list would wrongly get "return not found" before
    # the audit logic ever ran (same exception as handle_department_has_
    # return's "does department Y have access" — see its comment).
    ret, early = resolve_named_return(
        store, scope, target, intent="departments_with_return_access", label="Departments With Return Access",
        enforce_department_auth=False,
    )
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

    if entities.get("query_type") == "missed_deadline":
        from datetime import date
        from backend.db_qa.query_handlers.return_handlers import (
            _resolve_return_frequency_code, _most_recently_completed_occurrence,
        )
        frequency, period_name = _resolve_return_frequency_code(store, ret)
        due_days = (ret.get("DueDays") or "").strip() or None
        occ = _most_recently_completed_occurrence(frequency, due_days, date.today())
        if not occ or not occ.get("period_end"):
            return _result("departments_with_return_access", f"Missed Deadline: {ret.get('Name')}", [],
                           f"'{ret.get('Name')}' has no fixed reporting period, so a missed-deadline check doesn't apply.")
        period_end = occ["period_end"]
        filed_user_ids = {
            log.get("UserId", "") for log in store.instance_log()
            if log.get("FormId") in (ret_id, ret_code) and log.get("ReportingDate") == period_end
        }
        filed_dept_ids = set()
        for u in store.users():
            if u.get("LoginId") in filed_user_ids or u.get("UserId") in filed_user_ids:
                dept_id = get_attr(u, "DepartmentId", "DeptId", default="")
                if dept_id:
                    filed_dept_ids.add(dept_id)
        missed = [d for d in matches if get_attr(d, "DeptId", "Id", default="") not in filed_dept_ids]
        if not missed:
            return _result("departments_with_return_access", f"Missed Deadline: {ret.get('Name')}", [],
                           f"No department missed the submission deadline ({period_end}) for return '{ret.get('Name')}'.")
        return _result("departments_with_return_access", f"Missed Deadline: {ret.get('Name')}", missed,
                       f"{len(missed)} department(s) missed the submission deadline ({period_end}) for return '{ret.get('Name')}'.",
                       return_name=ret.get("Name"), count=len(missed),
                       show_dept_id=bool(entities.get("want_dept_id")))

    return _result("departments_with_return_access", f"Departments With Access to {ret.get('Name')}",
                   matches, f"{len(matches)} department(s) have access to return '{ret.get('Name')}'.",
                   return_name=ret.get("Name"), count=len(matches),
                   show_dept_id=bool(entities.get("want_dept_id")))


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
    dept_id = get_attr(dept, "DeptId", "Id", default="")
    who_phrase = "Your department" if scope["target_type"] == "self" else f"Department '{dept_name}'"
    verb = "does" if has_access else "does not"
    row = {"DeptName": dept_name, "ReturnName": ret.get("Name"), "HasAccess": has_access}
    if entities.get("want_dept_id"):
        row["DeptId"] = dept_id
    return _result("department_has_return", f"{dept_name} <-> {ret.get('Name')}",
                   [row],
                   f"{who_phrase} {verb} have access to return '{ret.get('Name')}'.",
                   has_access=has_access, show_dept_id=bool(entities.get("want_dept_id")))
