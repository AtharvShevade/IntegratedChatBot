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
    # Notifications.xml / NotificationReturnDetails.xml have no 6.0
    # equivalent at all — they aren't in v6_0_schema.py's SCHEMA, and no
    # matching file exists anywhere in the real 6.0 tenant folder structure
    # (checked against tenant 1001/1002 data). store.notifications()/
    # notification_details() therefore always return [], which would
    # otherwise be indistinguishable from "checked and none are configured"
    # — say plainly that this data isn't available instead of implying a
    # real (negative) answer was found.
    return _not_found(
        "notification_query", "Notifications",
        "Notification configuration is not available in this version of the application.",
    )
