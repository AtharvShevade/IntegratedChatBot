"""New-taxonomy handlers — AUDIT_SECURITY category."""
from __future__ import annotations

from backend.db_qa.xml_store import XMLStore


def _result(intent: str, label: str, records: list, summary: str, **meta) -> dict:
    return {"intent": intent, "label": label, "found": bool(records), "records": records, "summary": summary, "meta": meta}


def _not_found(intent: str, label: str, msg: str) -> dict:
    return _result(intent, label, [], msg)


def _login_ids_for(store: XMLStore, login_id: str, user_id: str | None) -> set[str]:
    u = store.user_by_id(user_id or login_id) or store.user_by_name(login_id)
    ids = {login_id}
    if user_id:
        ids.add(str(user_id))
    if u:
        ids.add(u.get("LoginId", ""))
        ids.add(u.get("UserId", ""))
    return {i for i in ids if i}


def handle_audit_history(scope: dict, entities: dict, store: XMLStore) -> dict:
    entries = [store.enrich_log_entry(e) for e in store.audit_log()]

    if scope["target_type"] == "self":
        ids = _login_ids_for(store, scope["login_id"], scope.get("user_id"))
        entries = [e for e in entries if e.get("UserId", "") in ids]
        label = "My Activity History"
    else:
        target_user = entities.get("target_user", "")
        if target_user:
            u = store.resolve_user(target_user)
            if not u:
                return _not_found("audit_history", "Audit History", f"User '{target_user}' not found.")
            ids = _login_ids_for(store, u.get("LoginId", ""), u.get("UserId"))
            entries = [e for e in entries if e.get("UserId", "") in ids]
            label = f"Activity History: {u.get('Name', target_user)}"
        else:
            label = "All Activity History"

    entries.sort(key=lambda e: e.get("AuditDateTime", ""), reverse=True)
    days_n = entities.get("days_n")
    if days_n:
        entries = entries[: int(days_n) * 10]  # rough recency cap without a date-parsing dependency

    return _result("audit_history", label, entries, f"Found {len(entries)} audit record(s).", count=len(entries))


def handle_audit_entity_trail(scope: dict, entities: dict, store: XMLStore) -> dict:
    target_department = entities.get("target_department", "")
    target_return = entities.get("target_return", "")
    entries = [store.enrich_log_entry(e) for e in store.audit_log()]

    if target_department:
        entries = [e for e in entries if target_department.lower() in e.get("Remark", "").lower()]
        label = f"Audit Trail: {target_department}"
    elif target_return:
        entries = [e for e in entries if target_return.lower() in e.get("Remark", "").lower()]
        label = f"Audit Trail: {target_return}"
    else:
        label = "Audit Trail"

    entries.sort(key=lambda e: e.get("AuditDateTime", ""), reverse=True)
    return _result("audit_entity_trail", label, entries, f"Found {len(entries)} audit record(s).", count=len(entries))


def handle_security_events(scope: dict, entities: dict, store: XMLStore) -> dict:
    query_type = (entities.get("query_type") or "").lower()

    if query_type == "failed_login_exceeded":
        users = [u for u in store.users() if int(u.get("FailedLoginCount", "0") or "0") >= 5]
        return _result("security_events", "Users Exceeding Failed Login Limit",
                       [store.enrich_user(u) for u in users],
                       f"{len(users)} user(s) have exceeded the failed-login threshold.", count=len(users))

    if query_type == "deactivated":
        users = [u for u in store.users() if u.get("Status", "").lower() != "true"]
        return _result("security_events", "Deactivated Users",
                       [store.enrich_user(u) for u in users], f"{len(users)} user(s) are deactivated.", count=len(users))

    if scope["target_type"] == "self":
        u = store.user_by_id(scope.get("user_id") or scope["login_id"]) or store.user_by_name(scope["login_id"])
        if not u:
            return _not_found("security_events", "My Security Status", "Your profile could not be found.")
        locked = int(u.get("FailedLoginCount", "0") or "0") >= 5
        return _result("security_events", "My Security Status",
                       [{"FailedLoginCount": u.get("FailedLoginCount", "0"), "Locked": locked}],
                       f"Your account has {u.get('FailedLoginCount', '0')} failed login attempt(s)"
                       + (" and appears locked." if locked else "."))

    target_user = entities.get("target_user", "")
    if target_user:
        u = store.resolve_user(target_user)
        if not u:
            return _not_found("security_events", "Security Status", f"User '{target_user}' not found.")
        return _result("security_events", f"Security Status: {u.get('Name')}", [store.enrich_user(u)],
                       f"Security details for '{u.get('Name')}'.")

    return _not_found("security_events", "Security Events", "Please specify a user or a query type.")


def handle_log_query(scope: dict, entities: dict, store: XMLStore) -> dict:
    log_type = (entities.get("log_type") or "").lower()
    target_return = entities.get("target_return", "")
    submission_id = entities.get("submission_id", "")

    if log_type == "cross_validation" or target_return and not submission_id:
        entries = [store.enrich_cross_val_entry(e) for e in store.cross_validation_log()]
        if target_return:
            t = target_return.lower()
            entries = [e for e in entries
                       if t in e.get("FirstReportName", "").lower() or t in e.get("SecondReportName", "").lower()]
        failed = [e for e in entries if e.get("Status", "").lower() == "fail"]
        return _result("log_query", "Cross-Validation Log", entries,
                       f"Found {len(entries)} cross-validation record(s); {len(failed)} failure(s).",
                       count=len(entries), failed=len(failed))

    # default: upload failures
    ids = None
    if scope["target_type"] == "self":
        u = store.user_by_id(scope.get("user_id") or scope["login_id"]) or store.user_by_name(scope["login_id"])
        ids = {scope["login_id"]}
        if u:
            ids.add(u.get("LoginId", ""))
            ids.add(u.get("UserId", ""))
        ids = {i for i in ids if i}

    entries = [store.enrich_log_entry(e) for e in store.upload_file_log()]
    if ids is not None:
        entries = [e for e in entries if e.get("UserId", "") in ids]
    label = "My Upload Failures" if scope["target_type"] == "self" else "Upload Log"
    return _result("log_query", label, entries, f"Found {len(entries)} upload log record(s).", count=len(entries))
