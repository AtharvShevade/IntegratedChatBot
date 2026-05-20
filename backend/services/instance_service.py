# instance_service.py — Scan the repository instance folder for a given Report ID.
#
# Flow:
#   report_id  →  {INSTANCE_BASE_DIR}/{report_id}/  →  *.xml files
#   Each filename is parsed by instance_label_parser to produce a display label.
#   No XML file contents are read — filenames only, for performance.

from __future__ import annotations

import logging
import os

from backend.config import INSTANCE_BASE_DIR
from backend.utils.instance_label_parser import parse_instance_filename

logger = logging.getLogger(__name__)


def get_instances_for_report(report_id: str) -> list[dict]:
    """Return a sorted list of instance file records for the given Report ID.

    Scans ``{INSTANCE_BASE_DIR}/{report_id}/`` for ``.xml`` files and parses
    each filename to extract reporting/generated dates.  No XML content is
    read — filename parsing only.

    Returns
    -------
    List of dicts (newest generated date first)::

        {
            "instance_path":  "HDFC200522R00002M_30-09-24_12-43-45_Instance.xml",
            "full_path":      "D:\\...\\Instance\\2001\\HDFC200522R..._Instance.xml",
            "reporting_date": "22-May-2020",
            "dtc":            "30-Sep-2024 12:43:45 PM",
            "label":          "22-May-2020 | Generated: 30-Sep-2024 12:43:45 PM",
            "status":         "",
            "id":             "",
        }

    Empty list on any error (folder missing, no XML files, all filenames
    unparseable).  Errors are logged so callers can surface them.
    """
    folder = os.path.join(INSTANCE_BASE_DIR, str(report_id).strip())

    if not os.path.isdir(folder):
        logger.warning(
            "[instance_service] Folder not found for report_id=%s: %s  "
            "(check INSTANCE_BASE_DIR in config.py)",
            report_id, folder,
        )
        return []

    results: list[dict] = []
    unparseable = 0

    for fname in os.listdir(folder):
        if not fname.lower().endswith(".xml"):
            continue
        full_path = os.path.join(folder, fname)
        if not os.path.isfile(full_path):
            continue

        parsed = parse_instance_filename(fname)
        if parsed is None:
            logger.debug("[instance_service] Skipping unparseable filename: %s", fname)
            unparseable += 1
            continue

        results.append({
            "instance_path":  fname,
            "full_path":      full_path,
            "reporting_date": parsed["reporting_date"],
            "dtc":            parsed["generated_dt"],
            "label":          parsed["label"],
            "status":         "",
            "id":             "",
            "_sort_key":      parsed["sort_key"],   # removed before returning
        })

    if unparseable:
        logger.info(
            "[instance_service] report_id=%s: %d file(s) skipped (filename did not match pattern)",
            report_id, unparseable,
        )

    # Sort newest generated-datetime first
    results.sort(key=lambda x: x["_sort_key"], reverse=True)
    for item in results:
        del item["_sort_key"]

    logger.info(
        "[instance_service] report_id=%s: found %d instance file(s) in %s",
        report_id, len(results), folder,
    )
    return results
