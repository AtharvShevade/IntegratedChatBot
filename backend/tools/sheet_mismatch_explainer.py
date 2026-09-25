# backend/tools/sheet_mismatch_explainer.py — explains the "no error file"
# failure mode for Repo 5.5 returns: an instance-log Comment reporting
# "Cannot find table 0." for one or more query names, which means the query's
# expected Excel sheet was not found in the user's uploaded workbook.
#
# Repo 6.0 is explicitly OUT OF SCOPE: its query layer reads from
# pre-populated staging DB tables, not directly from Excel, so there is no
# sheet-name mapping to recover there. A query that resolves only to a
# DB-staging row (FROM <TABLE>, no [Sheet$Range]) is reported as
# unresolvable rather than guessed at — see resolve_query_to_sheet().
#
# Pipeline (see explain()):
#   1. parse_failed_query_names   — pull query names out of the log Comment
#   2. resolve_query_to_sheet     — QueryName -> expected sheet + range
#   3. find_sample_workbook       — which sample *.xlsx actually has that sheet
#      find_latest_upload         — which uploaded *.xlsx is the current one
#   4. diff_sheet                 — is the sheet present in the upload?
#   5. explain                    — compose the human-readable message

from __future__ import annotations

import difflib
import glob
import logging
import os
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

import openpyxl

logger = logging.getLogger(__name__)

__all__ = [
    "parse_failed_query_names", "resolve_query_to_sheet",
    "find_sample_workbook", "find_latest_upload", "diff_sheet",
    "explain", "QueryResolution", "SheetDiff",
]

REPO_5_5_ROOT_DEFAULT = r"D:\RepoCore_5.5\Database"


# ═════════════════════════════════════════════════════════════════════════════
# STEP 1 — pull failing query names out of the instance-log Comment
# ═════════════════════════════════════════════════════════════════════════════

# Bounded on the left by "successfully:" (the first failure after the summary
# sentence) or "line <N>," (the stack-trace line preceding the NEXT failure in
# a multi-failure comment), and on the right by ": Cannot find table 0.".
# Deliberately NOT a naive split on "," — .NET's own parameter list
# (InsertInstanceLog(Int32 DDLFormId, DateTime ParamDTRptDate, ...)) contains
# commas that would fragment one failure into bogus query names.
_FAILED_QUERY_RE = re.compile(
    r"(?:successfully:\s*|line\s+\d+,\s*)([^:]+?):\s*Cannot find table 0\.",
    re.IGNORECASE,
)


def parse_failed_query_names(comment: str) -> list[str]:
    """Every QueryName reported as 'Cannot find table 0.' in *comment*, in the
    order they appear. [] when the comment doesn't match this failure shape."""
    if not comment:
        return []
    names = [m.group(1).strip() for m in _FAILED_QUERY_RE.finditer(comment)]
    return [n for n in names if n]


# ═════════════════════════════════════════════════════════════════════════════
# STEP 2 — QueryName -> expected sheet + range
# ═════════════════════════════════════════════════════════════════════════════

# Jet/ACE "Excel as database" syntax: FROM [SheetName$CellRange]. The sheet
# name never contains ']' or '$', so this is unambiguous even when the sheet
# name itself has spaces or punctuation ('Nominated Agencies', 'AnnexB-Non Bank').
_EXCEL_RANGE_RE = re.compile(r"FROM\s*\[([^\]$]+)\$([^\]]+)\]", re.IGNORECASE)


@dataclass
class QueryResolution:
    query_name: str
    resolvable: bool
    sheet: str = ""
    cell_range: str = ""
    source_file: str = ""
    reason: str = ""   # set when resolvable is False


def _find_query_row(xml_path: str, query_name: str) -> str | None:
    """The <SelectQuery> text of the <Row> matching *query_name* in *xml_path*,
    or None if the file doesn't exist or has no such row."""
    if not xml_path or not os.path.isfile(xml_path):
        return None
    try:
        tree = ET.parse(xml_path)
    except ET.ParseError as exc:
        logger.warning("[sheet_mismatch] cannot parse %s: %s", xml_path, exc)
        return None

    target = query_name.strip().lower()
    for row in tree.iter("Row"):
        name = (row.get("QueryName") or "").strip().lower()
        if name != target:
            continue
        select_el = row.find("SelectQuery")
        if select_el is not None and select_el.text:
            return select_el.text
    return None


def resolve_query_to_sheet(form_id: str | int, query_name: str,
                           repo_root: str = REPO_5_5_ROOT_DEFAULT) -> QueryResolution:
    """Resolve *query_name* to its expected Excel sheet + range for *form_id*.

    Checks XML_Query_Excel.xml first, then falls back to XML_Query.xml — and
    within EITHER file, only accepts a row whose SelectQuery actually contains
    FROM [Sheet$Range] syntax. A same-named row that queries a DB staging
    table instead (the Repo 6.0-shaped pattern) is not a match; resolution
    keeps looking in the other file, and if neither yields a real Excel-range
    row, this is reported as unresolvable rather than guessed at.
    """
    form_dir = os.path.join(repo_root, str(form_id))
    candidates = [
        ("XML_Query_Excel.xml", os.path.join(form_dir, "XML_Query_Excel.xml")),
        ("XML_Query.xml", os.path.join(form_dir, "XML_Query.xml")),
    ]

    for label, path in candidates:
        select_query = _find_query_row(path, query_name)
        if select_query is None:
            continue
        m = _EXCEL_RANGE_RE.search(select_query)
        if m:
            return QueryResolution(
                query_name=query_name, resolvable=True,
                sheet=m.group(1).strip(), cell_range=m.group(2).strip(),
                source_file=label,
            )
        # Row exists under this name but isn't the Excel-range shape (e.g. the
        # DB-staging duplicate confirmed on 2043's Annex B_GenInfo) — keep
        # looking in the other file rather than accepting it.

    return QueryResolution(
        query_name=query_name, resolvable=False,
        reason=(
            "No [Sheet$Range] query found for this name in either "
            "XML_Query_Excel.xml or XML_Query.xml — this return may use the "
            "DB-staging pattern (Repo 6.0-shaped), which this explainer does "
            "not cover."
        ),
    )


# ═════════════════════════════════════════════════════════════════════════════
# STEP 3 — locate the sample workbook and the uploaded workbook
# ═════════════════════════════════════════════════════════════════════════════

def _sheet_names(xlsx_path: str) -> list[str]:
    wb = openpyxl.load_workbook(xlsx_path, read_only=True)
    try:
        return list(wb.sheetnames)
    finally:
        wb.close()


def find_sample_workbook(form_id: str | int, sheet_name: str,
                         repo_root: str = REPO_5_5_ROOT_DEFAULT) -> list[str]:
    """Every *.xlsx directly in the return's DataBase folder whose own sheet
    list actually contains *sheet_name* — Excel lock files (~$...) skipped.

    A return can carry more than one sample file (e.g. Monthly vs HY variant);
    the caller decides what to do with more than one match — this function
    does not guess.
    """
    form_dir = os.path.join(repo_root, str(form_id))
    matches: list[str] = []
    for path in glob.glob(os.path.join(form_dir, "*.xlsx")):
        base = os.path.basename(path)
        if base.startswith("~$"):
            continue
        try:
            if sheet_name in _sheet_names(path):
                matches.append(path)
        except Exception as exc:                       # a locked/corrupt sample must not abort the scan
            logger.warning("[sheet_mismatch] cannot open sample %s: %s", path, exc)
    return matches


def find_latest_upload(form_id: str | int, repo_root: str = REPO_5_5_ROOT_DEFAULT,
                       instance_log_upload_dt: float | None = None) -> dict:
    """The most recent upload for *form_id*.

    Folder-naming isn't consistent across returns (YYYYMMDDHHMMSS vs
    dash-separated, not mutually sortable as strings), so "latest" is decided
    by folder mtime, never by parsing the folder name.

    Returns:
        {"path": str|None, "folder": str|None, "warning": str|None}
    'path' is None when UploadedFiles is missing or empty — reported as "no
    upload found", not an error. 'warning' is set when *instance_log_upload_dt*
    (an epoch timestamp from the instance log's FileUploadDT) diverges
    noticeably from the chosen folder's own mtime.
    """
    uploads_dir = os.path.join(repo_root, str(form_id), "UploadedFiles")
    if not os.path.isdir(uploads_dir):
        return {"path": None, "folder": None, "warning": "No UploadedFiles folder for this return."}

    subfolders = [
        os.path.join(uploads_dir, name) for name in os.listdir(uploads_dir)
        if os.path.isdir(os.path.join(uploads_dir, name))
    ]
    if not subfolders:
        return {"path": None, "folder": None, "warning": "UploadedFiles folder exists but has no uploads."}

    latest_folder = max(subfolders, key=os.path.getmtime)
    xlsx_files = [
        p for p in glob.glob(os.path.join(latest_folder, "*.xlsx"))
        if not os.path.basename(p).startswith("~$")
    ]
    if not xlsx_files:
        return {"path": None, "folder": latest_folder,
                "warning": "Latest upload folder contains no .xlsx file."}

    warning = None
    if instance_log_upload_dt is not None:
        drift = abs(os.path.getmtime(latest_folder) - instance_log_upload_dt)
        if drift > 3600:  # more than an hour apart is worth flagging
            warning = (
                f"Chosen upload folder's mtime differs from the instance log's "
                f"FileUploadDT by {drift / 60:.0f} minutes — this return may have "
                f"multiple upload attempts; verify this is the right one."
            )

    return {"path": xlsx_files[0], "folder": latest_folder, "warning": warning}


# ═════════════════════════════════════════════════════════════════════════════
# STEP 4 — diff: is the expected sheet actually in the uploaded workbook?
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class SheetDiff:
    found: bool
    uploaded_sheets: list[str] = field(default_factory=list)
    suggested_match: str | None = None
    likely_cause: str = ""


def diff_sheet(sheet_name: str, uploaded_path: str) -> SheetDiff:
    uploaded_sheets = _sheet_names(uploaded_path)
    if sheet_name in uploaded_sheets:
        return SheetDiff(
            found=True, uploaded_sheets=uploaded_sheets,
            likely_cause=(
                "Sheet name matches - the failure is more likely a cell-range "
                "mismatch (the expected range doesn't line up with this sheet's "
                "actual layout) than a renamed/missing sheet."
            ),
        )
    close = difflib.get_close_matches(sheet_name, uploaded_sheets, n=1, cutoff=0.6)
    return SheetDiff(
        found=False, uploaded_sheets=uploaded_sheets,
        suggested_match=close[0] if close else None,
        likely_cause="Sheet not found in the uploaded file - likely renamed, removed, or misspelled.",
    )


# ═════════════════════════════════════════════════════════════════════════════
# STEP 5 — orchestration + human-readable explanation
# ═════════════════════════════════════════════════════════════════════════════

def explain(form_id: str | int, instance_log_comment: str,
           repo_root: str = REPO_5_5_ROOT_DEFAULT,
           instance_log_upload_dt: float | None = None) -> str:
    """Human-readable explanation of a 'Cannot find table 0.' instance-log
    failure for *form_id*, built entirely from XML query config + the sample
    and uploaded Excel files on disk. Never raises."""
    query_names = parse_failed_query_names(instance_log_comment)
    if not query_names:
        return "No 'Cannot find table 0.' failures found in this comment."

    upload = find_latest_upload(form_id, repo_root, instance_log_upload_dt)
    lines: list[str] = []

    for query_name in query_names:
        resolution = resolve_query_to_sheet(form_id, query_name, repo_root)
        if not resolution.resolvable:
            lines.append(f"Query '{query_name}': {resolution.reason}")
            continue

        header = f"Query '{query_name}' expects sheet '{resolution.sheet}' (range {resolution.cell_range})."

        if upload["path"] is None:
            lines.append(f"{header} {upload['warning']}")
            continue

        samples = find_sample_workbook(form_id, resolution.sheet, repo_root)
        if len(samples) > 1:
            lines.append(
                f"{header} Multiple sample templates in this return's folder contain a sheet "
                f"named '{resolution.sheet}' ({', '.join(os.path.basename(p) for p in samples)}) - "
                f"cannot determine which variant applies without more context (e.g. reporting "
                f"frequency/period)."
            )

        sheet_diff = diff_sheet(resolution.sheet, upload["path"])
        if sheet_diff.found:
            lines.append(f"{header} {sheet_diff.likely_cause}")
        else:
            suggestion = (
                f" Closest match: '{sheet_diff.suggested_match}' - likely a renamed sheet."
                if sheet_diff.suggested_match else
                " No similarly-named sheet found in the upload either."
            )
            lines.append(f"{header} Not found in your uploaded file.{suggestion}")

        if upload["warning"]:
            lines.append(f"Note: {upload['warning']}")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    form_id = sys.argv[1] if len(sys.argv) > 1 else "2043"
    comment = sys.argv[2] if len(sys.argv) > 2 else (
        "Some of the queries does not executed successfully: Annex B_GenInfo: "
        "Cannot find table 0.   at System.Data.DataTableCollection.get_Item(Int32 index) "
        "... at XBRLGenerationService.XBRLGenerationService.InsertInstanceLog"
        "(Int32 DDLFormId, DateTime ParamDTRptDate, String x, String y) in "
        "C:\\IRIS\\TFS79\\iDEAL\\iDEAL Banking 5.2\\XBRLGenerationService\\"
        "XBRLGenerationService.cs:line 889, AnnexB-Non Bank: Cannot find table 0."
    )
    print(explain(form_id, comment))
