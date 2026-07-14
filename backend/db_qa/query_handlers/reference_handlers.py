"""New-taxonomy handlers — BANK_SEGMENT, SCHEDULER_NOTIFICATIONS categories.

Reference data — no admin tiering (single-tenant/global facts), matching
the legacy handle_bank_info/handle_segment_info behavior.
"""
from __future__ import annotations

from backend.db_qa.xml_store import XMLStore


def _result(intent: str, label: str, records: list, summary: str, **meta) -> dict:
    return {"intent": intent, "label": label, "found": bool(records), "records": records, "summary": summary, "meta": meta}


def _not_found(intent: str, label: str, msg: str) -> dict:
    return _result(intent, label, [], msg)


def handle_bank_info(scope: dict, entities: dict, store: XMLStore) -> dict:
    banks = list(store.bank_details())
    summary = (f"Bank details: {banks[0].get('BankName', 'N/A')} — {banks[0].get('BankType', '')}."
               if banks else "No bank details found.")
    return _result("bank_info", "Bank Details", banks, summary)


def handle_segment_info(scope: dict, entities: dict, store: XMLStore) -> dict:
    segs = list(store.segments())
    summary = (f"There are {len(segs)} segment type(s): {', '.join(s.get('SegmentName', '') for s in segs)}."
               if segs else "No segment types are configured in this system.")
    return _result("segment_info", "Segment Types", segs, summary)


def handle_notification_query(scope: dict, entities: dict, store: XMLStore) -> dict:
    target_return = entities.get("target_return", "")
    notification_type = entities.get("notification_type", "")
    notifs = list(store.notifications())
    details = list(store.notification_details())

    if notification_type:
        notifs = [n for n in notifs if n.get("NotificationType", "").lower() == notification_type.lower()]

    if target_return:
        ret = store.resolve_return(target_return)
        ret_id = (ret.get("ReturnId") or ret.get("Id")) if ret else None
        if ret_id:
            details = [d for d in details if d.get("ReturnId") == ret_id or d.get("FormId") == ret_id]
            notifs = [n for n in notifs if n.get("ReturnId") == ret_id or n.get("FormId") == ret_id]

    records = notifs + details
    if not records:
        return _not_found("notification_query", "Notifications",
                          "No notification configuration found" +
                          (f" for return '{target_return}'." if target_return else "."))

    label = "My Notifications" if scope["target_type"] == "self" else "Notification Configuration"
    return _result("notification_query", label, records,
                   f"Found {len(records)} notification setting(s)" +
                   (f" for return '{target_return}'." if target_return else "."),
                   count=len(records))
