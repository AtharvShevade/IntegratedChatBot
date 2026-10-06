# instance_service.py — Resolve instance records for a given Report ID from
# the authoritative instance log (XML_InstanceLog.xml for 5.5 / InstanceLog.xml
# for 6.0), instead of scanning the Instance folder and parsing filenames.
#
# Flow:
#   report_id -> report_lookup.get_instances_by_form_id(report_id)
#             -> each row already carries ReportingDate/Status/DTC/
#                InstanceDocPath, normalised to this same shape for both
#                versions by report_lookup._parse_instances()/
#                _normalize_v6_instance_row() -- the single place that already
#                reconciles 5.5's XML_InstanceLog.xml attribute names against
#                6.0's differently-named InstanceLog.xml ones.
#             -> full_path built via report_lookup.build_instance_doc_path()
#
# Previously this scanned {INSTANCE_BASE_DIR}/{report_id}/ directly and
# parsed each filename with a regex (instance_label_parser.py) to recover
# reporting/generated dates -- duplicating data the instance log already had
# as structured fields, and breaking outright for any filename shape the
# regex wasn't written for (confirmed: every 6.0 instance file failed to
# match the 5.5-only regex, so comparative analysis reported "No instance
# files found" even when the files were plainly on disk). Reading the log
# directly removes the filename-shape dependency entirely, for both versions.

from __future__ import annotations

import logging
import os
from datetime import datetime

from backend.tools.report_lookup import build_instance_doc_path, get_instances_by_form_id, map_status

logger = logging.getLogger(__name__)

# A real, comparable XBRL instance document -- not the .csv data-extract
# artifacts some InstanceDocPath rows point to (confirmed in real 6.0 data:
# most rows for a long-running report log an intermediate .csv, not the
# final .xml, as InstanceDocPath), and not case-sensitive since both
# conventions observed use this exact casing consistently but there is no
# reason to assume every deployment will.
_COMPARABLE_EXTENSIONS = (".xml",)


def _resolve_existing_doc_path(form_id: str, filename: str) -> tuple[str, str] | None:
    """(resolved_filename, full_path) for a log row's InstanceDocPath, or
    None if no real, comparable instance document can be found for it.

    A logged name ending in .csv is NEVER returned as-is, even when that
    exact .csv file exists on disk (confirmed in real 6.0 data that it
    usually does -- it's a genuine intermediate data-extract artifact, not
    an XBRL document load_xbrl_facts() can parse). Instead, the real
    instance document sitting right next to it is derived as
    "<base>_Instance.xml" -- confirmed against real 6.0 data as the actual
    naming relationship (e.g. "RUN123.csv" logged, "RUN123_Instance.xml" is
    the real file) -- and only THAT is checked for existence.

    Any other extension (chiefly .xml) is checked literally. If nothing
    resolves, the row is genuinely skipped rather than guessed further.
    """
    if filename.lower().endswith(".csv"):
        candidate = filename[: -len(".csv")] + "_Instance.xml"
        candidate_path = build_instance_doc_path(form_id, candidate)
        if os.path.isfile(candidate_path):
            return candidate, candidate_path
        return None

    literal_path = build_instance_doc_path(form_id, filename)
    if os.path.isfile(literal_path):
        return filename, literal_path
    return None


def _dtc_key(dtc: str) -> datetime:
    """Same format/parse as report_lookup._dtc_sort_key -- DTC is normalised
    to "%d-%b-%Y %I:%M:%S %p" for both 5.5 and 6.0 rows."""
    try:
        return datetime.strptime(dtc, "%d-%b-%Y %I:%M:%S %p")
    except ValueError:
        return datetime.min


def get_instances_for_report(report_id: str) -> list[dict]:
    """Return a sorted list of instance file records for the given Report ID,
    read from the instance log (not the filesystem), so the result carries
    the real Status/ReportingDate/DTC regardless of this deployment's
    instance filename convention.

    Returns
    -------
    List of dicts (newest DTC first)::

        {
            "instance_path":  "HDFC200522R00002M_30-09-24_12-43-45_Instance.xml",
            "full_path":      "D:\\...\\Instance\\2001\\HDFC200522R..._Instance.xml",
            "reporting_date": "22-May-2020",
            "dtc":            "30-Sep-2024 12:43:45 PM",
            "label":          "22-May-2020 | Generated: 30-Sep-2024 12:43:45 PM",
            "status":         "Approval Pending",
            "id":             "583",
        }

    Empty list if the form has no instance-log rows. A row is skipped (never
    returned as a comparison candidate) when:
      - InstanceDocPath is blank (a run that failed before producing a
        document -- there is no file to compare against), or
      - neither the logged path nor its derived ".csv" -> "_Instance.xml"
        variant (see _resolve_existing_doc_path) resolves to a real file on
        disk. The instance log is the authoritative SOURCE for which runs
        exist and their metadata, but it is not guaranteed to stay in sync
        with the filesystem forever (a logged document can be archived/
        deleted after the fact) -- this existence check is what stops a
        stale log entry from reaching the user as a selectable option and
        then failing deep inside the actual comparison a step later with a
        generic error.

    Nothing here parses a filename; the document name comes straight from
    the log (verbatim, or via the one documented derivation above).
    """
    fid = str(report_id).strip()
    rows = get_instances_by_form_id(fid)

    results: list[dict] = []
    skipped_no_doc = 0
    skipped_missing_file = 0

    for row in rows:
        logged_filename = (row.get("InstanceDocPath") or "").strip()
        if not logged_filename:
            skipped_no_doc += 1
            continue

        resolved = _resolve_existing_doc_path(fid, logged_filename)
        if resolved is None:
            skipped_missing_file += 1
            logger.debug(
                "[instance_service] report_id=%s: no real instance document "
                "found for logged InstanceDocPath=%r, skipping",
                fid, logged_filename,
            )
            continue
        filename, full_path = resolved

        reporting_date = (row.get("ReportingDate") or "").strip()
        dtc = (row.get("DTC") or "").strip()

        status_label = ""
        raw_status = row.get("Status", "")
        try:
            status_label = map_status(int(raw_status))
        except (TypeError, ValueError):
            pass

        label = f"{reporting_date} | Generated: {dtc}" if (reporting_date or dtc) else filename

        results.append({
            "instance_path":  filename,
            "full_path":      full_path,
            "reporting_date": reporting_date,
            "dtc":            dtc,
            "label":          label,
            "status":         status_label,
            "id":             (row.get("Id") or "").strip(),
        })

    if skipped_no_doc or skipped_missing_file:
        logger.info(
            "[instance_service] report_id=%s: skipped %d row(s) (no doc=%d, "
            "no resolvable file on disk=%d)",
            fid, skipped_no_doc + skipped_missing_file,
            skipped_no_doc, skipped_missing_file,
        )

    results.sort(key=lambda x: _dtc_key(x["dtc"]), reverse=True)

    logger.info(
        "[instance_service] report_id=%s: found %d instance(s) from the instance log",
        fid, len(results),
    )
    return results
