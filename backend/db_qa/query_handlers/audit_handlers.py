"""New-taxonomy handlers — AUDIT_SECURITY category."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from backend.db_qa import access_control
from backend.db_qa.xml_store import XMLStore
from backend.db_qa.query_handlers._return_resolution import check_return_auth

# L-08: was hardcoded as a bare `>= 5` at both call sites below -- a single
# named constant so the two copies can never silently drift apart.
FAILED_LOGIN_LOCK_THRESHOLD = 5

# Same date-part-only formats already used for log dates elsewhere in this
# package (submission_handlers.py's _parse_log_date) -- AuditDateTime carries
# a time component ("05-Jun-2023 06:39:42 AM") that a "last N days" filter
# doesn't need, so only the date portion (first whitespace-separated token)
# is parsed.
_AUDIT_DATE_FMTS = ("%d-%b-%Y", "%d/%m/%Y", "%Y-%m-%d")


def _safe_int(v, default: int = 0) -> int:
    """L-08: `int(v)` raises on malformed/non-numeric data (e.g. a blank or
    corrupted FailedLoginCount attribute) -- this degrades to *default*
    instead of crashing the whole request."""
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return default


def _parse_audit_date(s: str) -> date | None:
    s = (s or "").strip().split(" ")[0]
    for fmt in _AUDIT_DATE_FMTS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


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
        # L-08: was `entries[: int(days_n) * 10]` -- an approximation
        # ("assume ~10 entries/day") that could both over- and under-include
        # real entries depending on actual daily volume. Filters by the
        # entry's own parsed date against today - N days instead. An entry
        # whose date can't be parsed is excluded (fails safe: never shown as
        # if it were within the requested window) rather than crashing.
        n = _safe_int(days_n, default=None)
        if n is not None:
            cutoff = date.today() - timedelta(days=n)
            entries = [e for e in entries if (_parse_audit_date(e.get("AuditDateTime", "")) or date.min) >= cutoff]

    return _result("audit_history", label, entries, f"Found {len(entries)} audit record(s).", count=len(entries))


def handle_audit_entity_trail(scope: dict, entities: dict, store: XMLStore) -> dict:
    target_department = entities.get("target_department", "")
    target_return = entities.get("target_return", "")
    entries = [store.enrich_log_entry(e) for e in store.audit_log()]

    if target_department:
        entries = [e for e in entries if target_department.lower() in e.get("Remark", "").lower()]
        label = f"Audit Trail: {target_department}"
    elif target_return:
        # H-11: target_type=="return" (the only non-admin-reachable target_type
        # this intent has for a named return) populates
        # scope["allowed_form_ids"] via access_control.scope_query() -- reuse
        # the same check_return_auth() membership check every other
        # return-scoped handler uses, rather than filtering Remark text
        # without ever consulting scope.
        ret = store.resolve_return(target_return)
        if ret is not None:
            denied = check_return_auth(ret, scope)
            if denied:
                return denied
        entries = [e for e in entries if target_return.lower() in e.get("Remark", "").lower()]
        label = f"Audit Trail: {target_return}"
    else:
        label = "Audit Trail"

    entries.sort(key=lambda e: e.get("AuditDateTime", ""), reverse=True)
    return _result("audit_entity_trail", label, entries, f"Found {len(entries)} audit record(s).", count=len(entries))


def handle_security_events(scope: dict, entities: dict, store: XMLStore) -> dict:
    query_type = (entities.get("query_type") or "").lower()

    if query_type == "failed_login_exceeded":
        users = [u for u in store.users() if _safe_int(u.get("FailedLoginCount", "0")) >= FAILED_LOGIN_LOCK_THRESHOLD]
        # show_failed_logins: the count is hidden from ordinary user tables
        # (agent/db_qa_router._CONDITIONAL_FIELDS); this question is about it.
        return _result("security_events", "Users Exceeding Failed Login Limit",
                       [store.enrich_user(u) for u in users],
                       f"{len(users)} user(s) have exceeded the failed-login threshold.",
                       count=len(users), show_failed_logins=True)

    if query_type == "deactivated":
        users = [u for u in store.users() if u.get("Status", "").lower() != "true"]
        return _result("security_events", "Deactivated Users",
                       [store.enrich_user(u) for u in users], f"{len(users)} user(s) are deactivated.", count=len(users))

    if scope["target_type"] == "self":
        u = store.user_by_id(scope.get("user_id") or scope["login_id"]) or store.user_by_name(scope["login_id"])
        if not u:
            return _not_found("security_events", "My Security Status", "Your profile could not be found.")
        locked = _safe_int(u.get("FailedLoginCount", "0")) >= FAILED_LOGIN_LOCK_THRESHOLD
        return _result("security_events", "My Security Status",
                       [{"FailedLoginCount": u.get("FailedLoginCount", "0"), "Locked": locked}],
                       f"Your account has {u.get('FailedLoginCount', '0')} failed login attempt(s)"
                       + (" and appears locked." if locked else "."),
                       show_failed_logins=True)

    target_user = entities.get("target_user", "")
    if target_user:
        u = store.resolve_user(target_user)
        if not u:
            return _not_found("security_events", "Security Status", f"User '{target_user}' not found.")
        return _result("security_events", f"Security Status: {u.get('Name')}", [store.enrich_user(u)],
                       f"Security details for '{u.get('Name')}'.",
                       show_failed_logins=True)

    return _not_found("security_events", "Security Events", "Please specify a user or a query type.")


def handle_log_query(scope: dict, entities: dict, store: XMLStore) -> dict:
    log_type = (entities.get("log_type") or "").lower()
    target_return = entities.get("target_return", "")
    submission_id = entities.get("submission_id", "")

    if log_type == "cross_validation" or target_return and not submission_id:
        entries = [store.enrich_cross_val_entry(e) for e in store.cross_validation_log()]
        if target_return:
            # H-11: same department-scoping membership check every other
            # named-return handler applies, reused here since cross-validation
            # rows have no FormId of their own to check directly.
            ret = store.resolve_return(target_return)
            if ret is not None:
                denied = check_return_auth(ret, scope)
                if denied:
                    return denied
            t = target_return.lower()
            entries = [e for e in entries
                       if t in e.get("FirstReportName", "").lower() or t in e.get("SecondReportName", "").lower()]
        elif not scope.get("is_admin"):
            # H-11: no named return (e.g. a bare "show cross validation log"
            # self-scoped query) previously returned every department's
            # records unfiltered -- scope["allowed_form_ids"] is only
            # populated for target_type=="return" queries, so this reuses
            # the same resolution access_control.scope_query() does rather
            # than inventing a second authorization path.
            allowed = scope.get("allowed_form_ids")
            if allowed is None:
                allowed = access_control.resolve_allowed_form_ids(scope["login_id"])
            if allowed is not None:
                name_to_ids: dict[str, set[str]] = {}
                for r in list(store.returns()) + list(store.non_xbrl_returns()):
                    name = r.get("Name", "")
                    if name:
                        name_to_ids.setdefault(name, set()).update(
                            {v for v in (r.get("Id", ""), r.get("ReturnId", "")) if v}
                        )
                entries = [
                    e for e in entries
                    if (name_to_ids.get(e.get("FirstReportName", ""), set()) & allowed)
                    or (name_to_ids.get(e.get("SecondReportName", ""), set()) & allowed)
                ]
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
