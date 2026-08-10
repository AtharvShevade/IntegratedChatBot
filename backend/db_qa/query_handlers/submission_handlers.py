"""New-taxonomy handlers — INSTANCE_LOG category (submissions)."""
from __future__ import annotations

from datetime import datetime, timedelta

from backend.db_qa.xml_store import XMLStore, get_attr
from backend.db_qa.query_handlers._return_resolution import resolve_named_return


def _result(intent: str, label: str, records: list, summary: str, **meta) -> dict:
    return {"intent": intent, "label": label, "found": bool(records), "records": records, "summary": summary, "meta": meta}


def _not_found(intent: str, label: str, msg: str) -> dict:
    return _result(intent, label, [], msg)


_LOG_DATE_FMTS = ["%d-%b-%Y", "%d/%m/%Y", "%Y-%m-%d"]


def _parse_log_date(s: str) -> object | None:
    s = (s or "").strip().split(" ")[0]
    for fmt in _LOG_DATE_FMTS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _compute_on_time_rate(logs: list[dict], due_days: str | None) -> dict:
    """Historical on-time submission rate: for each InstanceLog entry,
    the expected due date is its own ReportingDate + the return's
    DueDays (the same "period-end + due_days" rule next_reporting_date()
    uses going forward, applied retroactively here) — on-time if the
    actual filing timestamp (DTC) falls on or before that due date.
    Entries with no parseable ReportingDate/DTC are skipped (can't judge
    them either way) rather than counted as late."""
    days = int(due_days) if (due_days or "").strip().isdigit() else 0
    on_time = 0
    judged = 0
    for log in logs:
        reporting_date = _parse_log_date(log.get("ReportingDate", ""))
        filed_date = _parse_log_date(log.get("DTC", ""))
        if not reporting_date or not filed_date:
            continue
        judged += 1
        due_date = reporting_date + timedelta(days=days)
        if filed_date <= due_date:
            on_time += 1
    return {"judged": judged, "on_time": on_time, "late": judged - on_time}


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
    """Status for one specific submission, identified by its InstanceLog
    Id — e.g. "what is the status of f7593ff72d644345865eaa84ae0b3073".

    Shows the same compact 4-line view (Return / Reporting Date / Status
    / Generated On) as the report-name-based "what is the status of CIMS
    ROR" workflow, including its status label vocabulary (Not Started/In
    Progress/Success/Failed/Approved/Rejected via
    report_lookup._STATUS_LABELS) rather than db_qa's own broader
    InstanceLog status vocabulary — so the same underlying submission
    reads identically whether it's looked up by name or by id. Deliberately
    surfaces only these four fields, not every raw InstanceLog attribute
    (DTC/FileUploadDT/ReportStartDT/IsExtract/IsCims/...), which a generic
    full-record dump would otherwise show.
    """
    from backend.tools.report_lookup import _STATUS_LABELS

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

    return_name = store.return_name_by_id(entry.get("FormId", ""))
    try:
        status_code = int(entry.get("Status", ""))
    except (TypeError, ValueError):
        status_code = None
    status_label = _STATUS_LABELS.get(status_code, entry.get("Status") or "Unknown")

    row = {
        "ReturnName": return_name,
        "ReportingDate": entry.get("ReportingDate", ""),
        "StatusLabel": status_label,
        "GeneratedOn": entry.get("DTC", ""),
    }
    return _result("submission_status", return_name, [row],
                   f"Submission '{submission_id}' status: {status_label}.")


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
        # Optional filter, but still disambiguate on a partial/ambiguous
        # name rather than silently resolving to nothing and showing every
        # submission unfiltered.
        ret, early = resolve_named_return(store, scope, target_return, intent="submission_list", label="Submissions")
        if early:
            return early
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
    ret, early = resolve_named_return(store, scope, target, intent="submissions_for_return", label="Submissions for Return")
    if early:
        return early
    # InstanceLog.FormId stores the return's internal Id ("2029"), not its
    # external ReturnId code ("R018") — checking only "ReturnId or Id"
    # (falls back to Id ONLY when ReturnId is empty) silently missed every
    # submission for any return that HAS a ReturnId, since real data
    # never keys FormId by ReturnId at all. Checking both membership-style
    # (matching handle_departments_with_return_access's convention) is
    # correct regardless of which code happens to be populated.
    form_ids = {v for v in (ret.get("Id", ""), ret.get("ReturnId", "")) if v}
    logs = [store.enrich_instance_log_entry(l) for l in store.instance_log() if l.get("FormId") in form_ids]

    if entities.get("query_type") == "on_time_rate":
        due_days = (ret.get("DueDays") or "").strip() or None
        rate = _compute_on_time_rate(logs, due_days)
        if not rate["judged"]:
            return _not_found("submissions_for_return", f"On-Time Rate: {ret.get('Name')}",
                              f"No submission history with parseable dates was found for return '{ret.get('Name')}'.")
        pct = round(100 * rate["on_time"] / rate["judged"])
        return _result("submissions_for_return", f"On-Time Rate: {ret.get('Name')}",
                       [{"ReturnName": ret.get("Name"), **rate, "OnTimePercent": pct}],
                       f"'{ret.get('Name')}' was submitted on time {pct}% of the time "
                       f"({rate['on_time']} of {rate['judged']} judged submission(s)).")

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
        ret, early = resolve_named_return(store, scope, target_return, intent="my_submission_history", label="My Submission History")
        if early:
            return early
        form_ids = {v for v in (ret.get("Id", ""), ret.get("ReturnId", "")) if v}
        matches = [l for l in logs if l.get("FormId") in form_ids]

        if entities.get("query_type") == "on_time_rate":
            due_days = (ret.get("DueDays") or "").strip() or None
            rate = _compute_on_time_rate(matches, due_days)
            if not rate["judged"]:
                return _not_found("my_submission_history", f"My On-Time Rate: {ret.get('Name')}",
                                  f"You have no submission history with parseable dates for return '{ret.get('Name')}'.")
            pct = round(100 * rate["on_time"] / rate["judged"])
            return _result("my_submission_history", f"My On-Time Rate: {ret.get('Name')}",
                           [{"ReturnName": ret.get("Name"), **rate, "OnTimePercent": pct}],
                           f"You submitted '{ret.get('Name')}' on time {pct}% of the time "
                           f"({rate['on_time']} of {rate['judged']} judged submission(s)).")

        return _result("my_submission_history", f"My Submissions: {ret.get('Name')}", matches,
                       f"You have submitted return '{ret.get('Name')}' {len(matches)} time(s)."
                       if matches else f"You have not yet submitted return '{ret.get('Name')}'.",
                       count=len(matches))

    seen_returns = {l.get("ReturnName", "") for l in logs if l.get("ReturnName")}
    return _result("my_submission_history", "My Submission History", logs,
                   f"You have {len(logs)} submission(s) across {len(seen_returns)} distinct return(s).",
                   count=len(logs), distinct_returns=len(seen_returns))
