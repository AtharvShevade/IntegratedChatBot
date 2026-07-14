"""New-taxonomy handlers — INSTANCE_LOG category (submissions)."""
from __future__ import annotations

from backend.db_qa.xml_store import XMLStore, get_attr


def _result(intent: str, label: str, records: list, summary: str, **meta) -> dict:
    return {"intent": intent, "label": label, "found": bool(records), "records": records, "summary": summary, "meta": meta}


def _not_found(intent: str, label: str, msg: str) -> dict:
    return _result(intent, label, [], msg)


def _login_ids_for(store: XMLStore, login_id: str, user_id: str | None) -> set[str]:
    """XML_InstanceLog.xml stores LoginId (not numeric UserId) in its UserId
    field — match against every identifier we know for this person."""
    u = store.user_by_id(user_id or login_id) or store.user_by_name(login_id)
    ids = {login_id}
    if user_id:
        ids.add(str(user_id))
    if u:
        ids.add(u.get("LoginId", ""))
        ids.add(u.get("UserId", ""))
    return {i for i in ids if i}


def handle_submission_status(scope: dict, entities: dict, store: XMLStore) -> dict:
    submission_id = entities.get("submission_id", "")
    if not submission_id:
        return _not_found("submission_status", "Submission Status", "Please specify a submission id.")
    entry = next((l for l in store.instance_log() if l.get("Id") == submission_id), None)
    if not entry:
        return _not_found("submission_status", "Submission Status", f"Submission '{submission_id}' not found.")

    if scope["target_type"] == "self":
        ids = _login_ids_for(store, scope["login_id"], scope.get("user_id"))
        if entry.get("UserId", "") not in ids:
            return _not_found("submission_status", "Submission Status",
                              f"Submission '{submission_id}' does not belong to your account.")

    enriched = store.enrich_instance_log_entry(entry)
    return _result("submission_status", f"Submission {submission_id}", [enriched],
                   f"Submission '{submission_id}' status: {enriched.get('StatusLabel', 'Unknown')}.")


def handle_submission_list(scope: dict, entities: dict, store: XMLStore) -> dict:
    logs = [store.enrich_instance_log_entry(l) for l in store.instance_log()]

    if scope["target_type"] == "self":
        ids = _login_ids_for(store, scope["login_id"], scope.get("user_id"))
        logs = [l for l in logs if l.get("UserId", "") in ids]
    elif scope["target_type"] == "other_user" and entities.get("target_user"):
        u = store.resolve_user(entities["target_user"])
        if u:
            ids = _login_ids_for(store, u.get("LoginId", ""), u.get("UserId"))
            logs = [l for l in logs if l.get("UserId", "") in ids]

    status = (entities.get("status") or "").lower()
    _STATUS_GROUPS = {
        "pending": {"0", "1", "2"}, "approved": {"9", "11"}, "audited": {"11"},
        "rejected": {"4"},
    }
    if status in _STATUS_GROUPS:
        logs = [l for l in logs if l.get("Status", "") in _STATUS_GROUPS[status]]
    elif status == "cims_ok":
        logs = [l for l in logs if l.get("CIMSUploadStatus", "").lower() in ("success", "ok", "true")]
    elif status == "cims_failed":
        logs = [l for l in logs if l.get("CIMSUploadStatus", "").lower() in ("failed", "fail", "false")]
    elif status == "has_error_doc":
        logs = [l for l in logs if l.get("ErrorDocPath", "").strip()]

    target_return = entities.get("target_return", "")
    if target_return:
        ret = store.resolve_return(target_return)
        if ret:
            form_id = ret.get("ReturnId") or ret.get("Id", "")
            logs = [l for l in logs if l.get("FormId") == form_id]

    label = "My Submissions" if scope["target_type"] == "self" else "Submissions"
    return _result("submission_list", label, logs, f"Found {len(logs)} submission record(s).", count=len(logs))


def handle_submission_detail(scope: dict, entities: dict, store: XMLStore) -> dict:
    submission_id = entities.get("submission_id", "")
    if not submission_id:
        return _not_found("submission_detail", "Submission Detail", "Please specify a submission id.")
    entry = next((l for l in store.instance_log() if l.get("Id") == submission_id), None)
    if not entry:
        return _not_found("submission_detail", "Submission Detail", f"Submission '{submission_id}' not found.")

    if scope["target_type"] == "self":
        ids = _login_ids_for(store, scope["login_id"], scope.get("user_id"))
        if entry.get("UserId", "") not in ids:
            return _not_found("submission_detail", "Submission Detail",
                              f"Submission '{submission_id}' does not belong to your account.")

    enriched = store.enrich_instance_log_entry(entry)
    return _result("submission_detail", f"Submission {submission_id} Detail", [enriched],
                   f"Full detail for submission '{submission_id}'.")


def handle_submissions_for_return(scope: dict, entities: dict, store: XMLStore) -> dict:
    target = entities.get("target_return", "")
    ret = store.resolve_return(target) if target else None
    if not ret:
        return _not_found("submissions_for_return", "Submissions for Return",
                          f"Return '{target}' not found." if target else "Please specify a return name.")
    form_id = ret.get("ReturnId") or ret.get("Id", "")
    logs = [store.enrich_instance_log_entry(l) for l in store.instance_log() if l.get("FormId") == form_id]
    logs.sort(key=lambda l: l.get("DTC", ""), reverse=True)
    most_recent = logs[0] if logs else None
    return _result("submissions_for_return", f"Submissions for {ret.get('Name')}", logs,
                   f"Found {len(logs)} submission(s) for return '{ret.get('Name')}'."
                   + (f" Most recent: {most_recent.get('UserName', '')} ({most_recent.get('StatusLabel', '')})."
                      if most_recent else ""),
                   return_name=ret.get("Name"), count=len(logs))


def handle_my_submission_history(scope: dict, entities: dict, store: XMLStore) -> dict:
    ids = _login_ids_for(store, scope["login_id"], scope.get("user_id"))
    logs = [store.enrich_instance_log_entry(l) for l in store.instance_log() if l.get("UserId", "") in ids]

    target_return = entities.get("target_return", "")
    if target_return:
        ret = store.resolve_return(target_return)
        if ret:
            form_id = ret.get("ReturnId") or ret.get("Id", "")
            matches = [l for l in logs if l.get("FormId") == form_id]
            return _result("my_submission_history", f"My Submissions: {ret.get('Name')}", matches,
                           f"You have submitted return '{ret.get('Name')}' {len(matches)} time(s)."
                           if matches else f"You have not yet submitted return '{ret.get('Name')}'.",
                           count=len(matches))

    seen_returns = {l.get("ReturnName", "") for l in logs if l.get("ReturnName")}
    return _result("my_submission_history", "My Submission History", logs,
                   f"You have {len(logs)} submission(s) across {len(seen_returns)} distinct return(s).",
                   count=len(logs), distinct_returns=len(seen_returns))
