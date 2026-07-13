# scheduler_queue_service.py — Append confirmed schedule entries to SchedulerQueue.xml.
#
# Flow:
#   append_schedule_entry(...)
#     → load SchedulerQueue.xml  (create with empty root if not found)
#     → auto-generate next incremental Id
#     → append new <Schedule> element with Status=PENDING
#     → pretty-print and save XML back in place
#
# The XML path is read from config.SCHEDULER_QUEUE_XML_PATH so there are no
# hardcoded paths in this file.

from __future__ import annotations

import logging
import os
import xml.etree.ElementTree as ET
from typing import Tuple

from backend.config import SCHEDULER_QUEUE_XML_PATH, get_scheduler_queue_xml_path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ROOT_TAG:  str = "SchedulerQueue"
_ENTRY_TAG: str = "Schedule"

# Minimal well-formed XML written when the file does not yet exist.
_INITIAL_XML: str = '<?xml version="1.0" encoding="utf-8"?>\n<SchedulerQueue />\n'


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _sub(parent: ET.Element, tag: str, text: str) -> ET.Element:
    """Create a child element with the given text and attach it to *parent*."""
    el = ET.SubElement(parent, tag)
    el.text = text
    return el


def _indent_tree(elem: ET.Element, level: int = 0, space: str = "  ") -> None:
    """Recursively add pretty-print indentation in-place (Python < 3.9 fallback).

    Mirrors the behaviour of ``xml.etree.ElementTree.indent`` added in 3.9.
    """
    indent       = "\n" + space * level
    child_indent = "\n" + space * (level + 1)
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = child_indent
        for child in elem[:-1]:
            _indent_tree(child, level + 1, space)
            if not child.tail or not child.tail.strip():
                child.tail = child_indent
        _indent_tree(elem[-1], level + 1, space)
        if not elem[-1].tail or not elem[-1].tail.strip():
            elem[-1].tail = indent
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = indent


def _pretty_print(root: ET.Element) -> None:
    """Apply 2-space indentation to *root* — uses stdlib ET.indent (3.9+) or fallback."""
    try:
        ET.indent(root, space="  ")          # Python 3.9+
    except AttributeError:
        _indent_tree(root)                   # Python < 3.9


def _ensure_parent_dir(path: str) -> None:
    """Create all parent directories for *path* if they do not already exist."""
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def _create_empty_xml(path: str) -> None:
    """Write a minimal SchedulerQueue XML skeleton to *path*."""
    _ensure_parent_dir(path)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(_INITIAL_XML)
    logger.info("[scheduler_queue] Created new SchedulerQueue.xml at %s", path)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def append_schedule_entry(
    report_name: str,
    form_id: str,
    reporting_date: str,
    schedule_dt: str,
    user_id: str,
    tenant_id: str | None = None,
) -> Tuple[bool, str]:
    """Append a new PENDING schedule entry to SchedulerQueue.xml.

    Parameters
    ----------
    report_name:
        Display name of the report (e.g. ``"CIMS_RAQ(Quarterly)"``).
    form_id:
        Internal FormId of the report (e.g. ``"1234"``).
    reporting_date:
        Schedule date shown to the user (e.g. ``"31-Dec-2027"``).
    schedule_dt:
        ISO-format scheduled datetime string (e.g. ``"2027-12-31T12:00:00"``).
    user_id:
        Login ID of the user who confirmed the schedule.
    tenant_id:
        6.0 only. Resolves to <tenant_repo>\\DataBase\\SchedulerQueue.xml via the
        existing tenant-aware path resolution (get_scheduler_queue_xml_path).
        Auto-created for tenants that don't have one yet, same as 5.5.

    Returns
    -------
    Tuple of ``(success: bool, schedule_id: str)``.
    On failure *success* is ``False`` and *schedule_id* is an empty string.
    """
    try:
        path = get_scheduler_queue_xml_path(tenant_id) if tenant_id else SCHEDULER_QUEUE_XML_PATH
    except NotImplementedError as exc:
        logger.error("[scheduler_queue] %s", exc)
        return False, ""

    try:
        # ── Initialise the file if it does not exist ──────────────────────────
        if not os.path.isfile(path):
            _create_empty_xml(path)

        # ── Parse the file ────────────────────────────────────────────────────
        try:
            tree = ET.parse(path)
        except ET.ParseError as exc:
            logger.error(
                "[scheduler_queue] XML parse error in %s: %s — cannot append entry.",
                path, exc,
            )
            return False, ""

        root = tree.getroot()

        if root.tag != _ROOT_TAG:
            logger.error(
                "[scheduler_queue] Unexpected root tag <%s> in %s — expected <%s>. "
                "Cannot append entry.",
                root.tag, path, _ROOT_TAG,
            )
            return False, ""

        # ── Auto-generate next incremental Id ─────────────────────────────────
        existing_ids: list[int] = [
            int(entry.findtext("Id", "0"))
            for entry in root.findall(_ENTRY_TAG)
            if (entry.findtext("Id") or "").strip().isdigit()
        ]
        next_id  = (max(existing_ids) + 1) if existing_ids else 1
        str_id   = str(next_id)

        # ── Build new <Schedule> element ──────────────────────────────────────
        entry = ET.SubElement(root, _ENTRY_TAG)
        _sub(entry, "Id",               str_id)
        _sub(entry, "ReportName",       report_name)
        _sub(entry, "FormId",           form_id)
        _sub(entry, "ReportingDate",    reporting_date)
        _sub(entry, "ScheduleDateTime", schedule_dt)
        _sub(entry, "UserId",           user_id)
        _sub(entry, "Status",           "PENDING")

        # ── Pretty-print and persist ───────────────────────────────────────────
        _pretty_print(root)
        tree = ET.ElementTree(root)
        with open(path, "wb") as fh:
            tree.write(fh, encoding="utf-8", xml_declaration=True)

        logger.info(
            "[scheduler_queue] Appended entry id=%s report=%r form_id=%r user=%r to %s",
            str_id, report_name, form_id, user_id, path,
        )
        return True, str_id

    except OSError as exc:
        logger.error(
            "[scheduler_queue] File I/O error while updating %s: %s",
            path, exc,
        )
        return False, ""
    except Exception as exc:
        logger.exception(
            "[scheduler_queue] Unexpected error appending entry for report=%r: %s",
            report_name, exc,
        )
        return False, ""
