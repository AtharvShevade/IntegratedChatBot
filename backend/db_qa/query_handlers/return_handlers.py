"""New-taxonomy handlers — PERIOD, XBRL_RETURNS, NON_XBRL_RETURNS,
DEPT_RETURN_MAPPING categories."""
from __future__ import annotations

from collections import Counter

from backend.db_qa.xml_store import XMLStore, get_attr


def _result(intent: str, label: str, records: list, summary: str, **meta) -> dict:
    return {"intent": intent, "label": label, "found": bool(records), "records": records, "summary": summary, "meta": meta}


def _not_found(intent: str, label: str, msg: str) -> dict:
    return _result(intent, label, [], msg)


def _resolve_target_department(store: XMLStore, scope: dict, entities: dict) -> dict | None:
    if scope["target_type"] == "self":
        u = store.user_by_id(scope.get("user_id") or scope["login_id"]) or store.user_by_name(scope["login_id"])
        if not u:
            return None
        dept_id = get_attr(u, "DepartmentId", "DeptId", default="")
        return store.dept_by_id(dept_id) if dept_id else None
    target = entities.get("target_department", "")
    return store.resolve_dept(target) if target else None


# ── PERIOD ───────────────────────────────────────────────────────────────

def handle_period_list(scope: dict, entities: dict, store: XMLStore) -> dict:
    periods = list(store.periods())
    return _result("period_list", "Reporting Periods", periods,
                   f"There are {len(periods)} reporting period(s) configured.", count=len(periods))


def handle_period_lookup(scope: dict, entities: dict, store: XMLStore) -> dict:
    period_name = entities.get("period_name", "")
    period_id = entities.get("period_id", "")
    periods = store.periods()
    match = None
    if period_id:
        match = next((p for p in periods if get_attr(p, "Period_Id", "Id", default="") == str(period_id)), None)
    elif period_name:
        match = next((p for p in periods if p.get("PeriodName", "").lower() == period_name.lower()), None)
    if not match:
        return _not_found("period_lookup", "Period Lookup",
                          "Please specify a period name or id." if not (period_name or period_id)
                          else f"No period found matching {period_name or period_id!r}.")
    return _result("period_lookup", f"Period: {match.get('PeriodName')}", [match],
                   f"Period '{match.get('PeriodName')}' has id {get_attr(match, 'Period_Id', 'Id', default='')}.")


def handle_returns_by_frequency(scope: dict, entities: dict, store: XMLStore) -> dict:
    period_name = entities.get("period_name", "")
    periods = store.periods()
    period_id = None
    for p in periods:
        if p.get("PeriodName", "").lower() == period_name.lower():
            period_id = get_attr(p, "Period_Id", "Id", default="")
            break
    if not period_id:
        return _not_found("returns_by_frequency", "Returns by Frequency",
                          f"Period '{period_name}' not found." if period_name else "Please specify a period.")

    rets = [store.enrich_return(r) for r in store.returns() if r.get("PeriodId") == period_id]
    if scope["target_type"] == "self":
        dept = _resolve_target_department(store, scope, entities)
        if dept:
            form_ids = {f.strip() for f in dept.get("Forms", "").split("|") if f.strip()}
            rets = [r for r in rets if r.get("Id") in form_ids or r.get("ReturnId") in form_ids]
    label = f"{period_name} Returns" + (" (Mine)" if scope["target_type"] == "self" else "")
    return _result("returns_by_frequency", label, rets, f"Found {len(rets)} {period_name} return(s).", count=len(rets))


# ── XBRL_RETURNS ─────────────────────────────────────────────────────────

def handle_return_list(scope: dict, entities: dict, store: XMLStore) -> dict:
    query_type = (entities.get("query_type") or "all").lower()
    category = entities.get("category", "")
    returns = [store.enrich_return(r) for r in store.returns()]

    if scope["target_type"] == "self":
        dept = _resolve_target_department(store, scope, entities)
        if dept:
            form_ids = {f.strip() for f in dept.get("Forms", "").split("|") if f.strip()}
            returns = [r for r in returns if r.get("Id") in form_ids or r.get("ReturnId") in form_ids]

    if category:
        returns = [r for r in returns if category.lower() in r.get("Name", "").lower()
                   or category.lower() in r.get("ReturnId", "").lower()]

    if query_type == "active":
        returns = [r for r in returns if r.get("Status", "").lower() == "true"]
    elif query_type == "inactive":
        returns = [r for r in returns if r.get("Status", "").lower() != "true"]
    elif query_type == "cims":
        returns = [r for r in returns if r.get("IsCims", "").lower() == "true"]
    elif query_type == "istbl":
        returns = [r for r in returns if r.get("IsTBL", "").lower() == "true"]

    label = "My XBRL Returns" if scope["target_type"] == "self" else "XBRL Returns"
    active_count = sum(1 for r in returns if r.get("Status", "").lower() == "true")
    return _result("return_list", label, returns,
                   f"There are {len(returns)} XBRL returns ({active_count} active).",
                   count=len(returns), active=active_count)


def handle_return_profile(scope: dict, entities: dict, store: XMLStore) -> dict:
    target = entities.get("target_return", "")
    ret = store.resolve_return(target) if target else None
    if not ret:
        return _not_found("return_profile", "Return Profile",
                          f"Return '{target}' not found." if target else "Please specify a return name.")
    return _result("return_profile", f"Return: {ret.get('Name')}", [store.enrich_return(ret)],
                   f"Details for return '{ret.get('Name')}'.")


def handle_return_validation_config(scope: dict, entities: dict, store: XMLStore) -> dict:
    target = entities.get("target_return", "")
    detail_type = (entities.get("detail_type") or "").lower()

    if target:
        ret = store.resolve_return(target)
        if not ret:
            return _not_found("return_validation_config", "Validation Configuration", f"Return '{target}' not found.")
        row = store.enrich_return(ret)
        row["HasFormulaValidation"] = ret.get("IsFormulaValidation", "false")
        row["HasSchCalcValidation"] = ret.get("IsSchCalValidation", "false")
        row["HasRBIValidation"] = ret.get("IsRBIValidation", "false")
        return _result("return_validation_config", f"Validation Config: {ret.get('Name')}", [row],
                       f"Validation configuration for return '{ret.get('Name')}'.")

    results = []
    for r in store.returns():
        row = store.enrich_return(r)
        row["HasFormulaValidation"] = r.get("IsFormulaValidation", "false")
        row["HasSchCalcValidation"] = r.get("IsSchCalValidation", "false")
        row["HasLargeValidator"] = r.get("IsLargeValidator", "false")
        row["HasRBIValidation"] = r.get("IsRBIValidation", "false")
        row["IsCIMS"] = r.get("IsCims", "false")
        results.append(row)

    if detail_type == "formula":
        results = [r for r in results if r["HasFormulaValidation"].lower() == "true"]
        label = "Returns with Formula Validation"
    elif detail_type in ("schema", "sch"):
        results = [r for r in results if r["HasSchCalcValidation"].lower() == "true"]
        label = "Returns with Schema-Calculation Validation"
    elif detail_type == "rbi":
        results = [r for r in results if r["HasRBIValidation"].lower() == "true"]
        label = "Returns with RBI Validation"
    elif detail_type == "large":
        results = [r for r in results if r["HasLargeValidator"].lower() == "true"]
        label = "Returns Using Large Validator"
    else:
        label = "Returns with Validation Settings"

    return _result("return_validation_config", label, results,
                   f"Found {len(results)} return(s) matching validation criteria.", count=len(results))


def handle_returns_submittable_by_dept(scope: dict, entities: dict, store: XMLStore) -> dict:
    target_return = entities.get("target_return", "")
    if target_return:
        # "which departments can submit return X" — same as departments_with_return_access
        ret = store.resolve_return(target_return)
        if not ret:
            return _not_found("returns_submittable_by_dept", "Departments That Can Submit",
                              f"Return '{target_return}' not found.")
        ret_id, ret_code = ret.get("Id", ""), ret.get("ReturnId", "")
        matches = []
        for d in store.departments():
            form_ids = {f.strip() for f in d.get("Forms", "").split("|") if f.strip()}
            if ret_id in form_ids or ret_code in form_ids:
                matches.append(d)
        return _result("returns_submittable_by_dept", f"Departments That Can Submit {ret.get('Name')}",
                       matches, f"{len(matches)} department(s) can submit '{ret.get('Name')}'.", count=len(matches))

    dept = _resolve_target_department(store, scope, entities)
    if not dept:
        who = "Your" if scope["target_type"] == "self" else f"'{entities.get('target_department', '')}'"
        return _not_found("returns_submittable_by_dept", "Submittable Returns", f"{who} department could not be found.")
    form_ids = [f.strip() for f in dept.get("Forms", "").split("|") if f.strip()]
    rets = [store.enrich_return(r) for r in store.returns() if r.get("Id") in form_ids or r.get("ReturnId") in form_ids]
    who_phrase = "You can" if scope["target_type"] == "self" else f"Department '{dept.get('Name')}' can"
    return _result("returns_submittable_by_dept", "Submittable XBRL Returns",
                   rets, f"{who_phrase} submit {len(rets)} XBRL return(s).", count=len(rets))


# ── NON_XBRL_RETURNS ─────────────────────────────────────────────────────

def handle_nonxbrl_return_list(scope: dict, entities: dict, store: XMLStore) -> dict:
    query_type = (entities.get("query_type") or "all").lower()
    target_department = entities.get("target_department", "")
    returns = list(store.non_xbrl_returns())

    if target_department:
        dept = store.dept_by_name(target_department)
        if not dept:
            return _not_found("nonxbrl_return_list", "Non-XBRL Returns", f"Department '{target_department}' not found.")
        nx_ids = {f.strip() for f in dept.get("NXForms", "").split("|") if f.strip()}
        returns = [r for r in returns if r.get("Id") in nx_ids or r.get("ReturnId") in nx_ids]
    elif scope["target_type"] == "self":
        dept = _resolve_target_department(store, scope, entities)
        if dept:
            nx_ids = {f.strip() for f in dept.get("NXForms", "").split("|") if f.strip()}
            returns = [r for r in returns if r.get("Id") in nx_ids or r.get("ReturnId") in nx_ids]

    if query_type == "no_due_days":
        returns = [r for r in returns if not r.get("DueDays", "").strip()]
    elif query_type == "has_folder":
        returns = [r for r in returns if r.get("HasFolder", "").lower() == "true"]

    label = "My Non-XBRL Returns" if scope["target_type"] == "self" else "Non-XBRL Returns"
    return _result("nonxbrl_return_list", label, returns,
                   f"There are {len(returns)} non-XBRL returns.", count=len(returns))


def handle_nonxbrl_return_profile(scope: dict, entities: dict, store: XMLStore) -> dict:
    target = entities.get("target_return", "")
    ret = None
    for r in store.non_xbrl_returns():
        if target and (r.get("Name", "").lower() == target.lower() or r.get("ReturnId", "") == target or r.get("Id", "") == target):
            ret = r
            break
    if not ret:
        return _not_found("nonxbrl_return_profile", "Non-XBRL Return Profile",
                          f"Non-XBRL return '{target}' not found." if target else "Please specify a return name.")
    return _result("nonxbrl_return_profile", f"Non-XBRL Return: {ret.get('Name')}", [ret],
                   f"Details for non-XBRL return '{ret.get('Name')}'.")


# ── DEPT_RETURN_MAPPING ──────────────────────────────────────────────────

def handle_dept_return_access_matrix(scope: dict, entities: dict, store: XMLStore) -> dict:
    depts = store.departments()
    all_return_ids = [r.get("Id", "") for r in store.returns() if r.get("Id")]
    access_counter: Counter = Counter()
    for d in depts:
        form_ids = {f.strip() for f in d.get("Forms", "").split("|") if f.strip()}
        for rid in form_ids:
            access_counter[rid] += 1

    return_index = {r.get("Id", ""): r for r in store.returns()}
    rows = []
    for rid, count in access_counter.most_common():
        ret = return_index.get(rid)
        rows.append({"ReturnId": rid, "ReturnName": ret.get("Name", "") if ret else "", "DepartmentCount": count})

    dept_counts = []
    for d in depts:
        form_ids = {f.strip() for f in d.get("Forms", "").split("|") if f.strip()}
        dept_counts.append({"DeptName": d.get("Name", ""), "ReturnCount": len(form_ids)})
    dept_counts.sort(key=lambda x: x["ReturnCount"], reverse=True)

    return _result("dept_return_access_matrix", "Department <-> Return Access Matrix",
                   rows, f"{len(rows)} return(s) have at least one department with access; "
                         f"'{dept_counts[0]['DeptName']}' has the most returns ({dept_counts[0]['ReturnCount']})."
                         if rows and dept_counts else "No department-return mappings found.",
                   top_department=dept_counts[0] if dept_counts else None)


def handle_my_return_access(scope: dict, entities: dict, store: XMLStore) -> dict:
    dept = _resolve_target_department(store, scope, entities)
    if not dept:
        return _not_found("my_return_access", "My Return Access", "Your department could not be found.")
    target_return = entities.get("target_return", "")
    form_ids = {f.strip() for f in dept.get("Forms", "").split("|") if f.strip()}
    nx_ids = {f.strip() for f in dept.get("NXForms", "").split("|") if f.strip()}

    if target_return:
        ret = store.resolve_return(target_return)
        if not ret:
            return _not_found("my_return_access", "My Return Access", f"Return '{target_return}' not found.")
        has_access = ret.get("Id", "") in form_ids or ret.get("ReturnId", "") in form_ids \
            or ret.get("Id", "") in nx_ids or ret.get("ReturnId", "") in nx_ids
        verb = "does" if has_access else "does not"
        return _result("my_return_access", f"My Access: {ret.get('Name')}",
                       [{"ReturnName": ret.get("Name"), "HasAccess": has_access}],
                       f"Your department {verb} have access to return '{ret.get('Name')}'.", has_access=has_access)

    xbrl = [store.enrich_return(r) for r in store.returns() if r.get("Id") in form_ids or r.get("ReturnId") in form_ids]
    non_xbrl = [dict(r) for r in store.non_xbrl_returns() if r.get("Id") in nx_ids or r.get("ReturnId") in nx_ids]
    records = [{"type": "XBRL", **r} for r in xbrl] + [{"type": "Non-XBRL", **r} for r in non_xbrl]
    return _result("my_return_access", "My Return Access", records,
                   f"You have access to {len(xbrl)} XBRL and {len(non_xbrl)} non-XBRL returns "
                   f"({len(xbrl) + len(non_xbrl)} total).",
                   total=len(xbrl) + len(non_xbrl))


def handle_dept_full_return_list(scope: dict, entities: dict, store: XMLStore) -> dict:
    target = entities.get("target_department", "")
    dept = store.resolve_dept(target) if target else None
    if not dept:
        return _not_found("dept_full_return_list", "Department Return List",
                          f"Department '{target}' not found." if target else "Please specify a department name.")
    form_ids = [f.strip() for f in dept.get("Forms", "").split("|") if f.strip()]
    nx_ids = [f.strip() for f in dept.get("NXForms", "").split("|") if f.strip()]
    xbrl = [store.enrich_return(r) for r in store.returns() if r.get("Id") in form_ids or r.get("ReturnId") in form_ids]
    non_xbrl = [dict(r) for r in store.non_xbrl_returns() if r.get("Id") in nx_ids or r.get("ReturnId") in nx_ids]
    records = [{"type": "XBRL", **r} for r in xbrl] + [{"type": "Non-XBRL", **r} for r in non_xbrl]
    return _result("dept_full_return_list", f"Complete Return List: {dept.get('Name')}", records,
                   f"Department '{dept.get('Name')}' has {len(xbrl)} XBRL and {len(non_xbrl)} non-XBRL returns "
                   f"({len(records)} total).", total=len(records))
