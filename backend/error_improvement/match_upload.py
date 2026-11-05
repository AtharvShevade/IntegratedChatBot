"""Pair an error file with the workbook the user uploaded for the run that made it
(repo layout: <form>/UploadedFiles/<dd-mm-yy-HH-MM-SS>/<file>, newer returns <form>/UploadedFiles/<yyyymmddHHMMSS>/<file>).

Two ways, in this order:
  1. the application's own record: XML_InstanceLog.xml has a row per run with the error file's name and the time of the upload it
     used (FileUploadDT), so the upload folder is named exactly, however long the user waited between uploading and validating;
  2. otherwise the upload made in the 30 minutes before the error file (the time is in the error file's name)."""
import datetime as dt
import os
import re
import xml.etree.ElementTree as ET

_NAME = re.compile(r"_(\d\d-\d\d-\d\d)_(\d\d-\d\d-\d\d)_")


def _stamp(folder_name: str) -> dt.datetime:
    """The time an upload folder is named after: dd-mm-yy-HH-MM-SS, else yyyymmddHHMMSS. ValueError when it is neither."""
    try:
        return dt.datetime.strptime(folder_name, "%d-%m-%y-%H-%M-%S")
    except ValueError:
        return dt.datetime.strptime(folder_name, "%Y%m%d%H%M%S")


_UPLOAD_TIME_FORMATS = ("%d-%b-%Y %I:%M:%S %p", "%d-%b-%Y %H:%M:%S", "%Y-%m-%d-%H-%M-%S", "%Y-%m-%d %H:%M:%S", "%d-%m-%Y %H:%M:%S")
_LOG_CACHE: dict = {}


def _when(text: str):
    for fmt in _UPLOAD_TIME_FORMATS:
        try:
            return dt.datetime.strptime((text or "").strip(), fmt)
        except ValueError:
            continue
    return None


def _log_rows(db_folder: str) -> dict:
    """{error file name (lower case): [(form id, upload time)]} from DataBase/XML_InstanceLog.xml; {} when there is no such file."""
    path = os.path.join(db_folder, "XML_InstanceLog.xml")
    try:
        stamp = os.path.getmtime(path)
    except OSError:
        return {}
    hit = _LOG_CACHE.get(path)
    if hit and hit[0] == stamp:
        return hit[1]
    rows: dict = {}
    try:
        for el in ET.parse(path).getroot().iter("Row"):
            name = os.path.basename((el.get("ErrorDocPath") or "").replace("\\", "/")).lower()
            when = _when(el.get("FileUploadDT"))
            if name and when:
                rows.setdefault(name, []).append(((el.get("FormId") or "").strip(), when))
    except (ET.ParseError, OSError):
        rows = {}
    _LOG_CACHE[path] = (stamp, rows)
    return rows


def log_upload(form_folder: str, error_file: str):
    """The workbook the application's own log says this run used, or None (no log, no row for this error file, or the upload is gone)."""
    root = os.path.join(form_folder, "UploadedFiles")
    if not os.path.isdir(root):
        return None
    form = os.path.basename(os.path.normpath(form_folder))
    rows = _log_rows(os.path.dirname(os.path.normpath(form_folder))).get(os.path.basename(error_file).lower(), [])
    for fid, when in reversed(rows):                                   # the latest row for this error file
        if fid and fid != form:
            continue
        for name in (when.strftime("%d-%m-%y-%H-%M-%S"), when.strftime("%Y%m%d%H%M%S")):
            folder = os.path.join(root, name)
            if os.path.isdir(folder):
                files = [f for f in os.listdir(folder) if f.lower().endswith((".xls", ".xlsx", ".xlsm"))]
                if files:
                    return os.path.join(folder, files[0])
    return None


def ranked_uploads(form_folder: str, error_file: str, window_min: int = 180, limit: int = 3) -> list[str]:
    """Uploads made 0..window_min minutes before the error file, nearest first (workbook path each)."""
    m = _NAME.search(os.path.basename(error_file))
    root = os.path.join(form_folder, "UploadedFiles")
    if not m or not os.path.isdir(root):
        return []
    t = dt.datetime.strptime(m.group(1) + "-" + m.group(2), "%d-%m-%y-%H-%M-%S")
    found = []
    for d in os.listdir(root):
        try:
            u = _stamp(d)
        except ValueError:
            continue
        for cand in (t, t + dt.timedelta(hours=12)):
            gap = cand - u
            if dt.timedelta(0) <= gap <= dt.timedelta(minutes=window_min):
                files = [f for f in os.listdir(os.path.join(root, d)) if f.lower().endswith((".xls", ".xlsx", ".xlsm"))]
                if files:
                    found.append((gap, os.path.join(root, d, files[0])))
                break
    return [p for _g, p in sorted(found)[:limit]]


def match_upload(form_folder: str, error_file: str, window_min: int = 30):
    """Path of the upload this error file's run used: the one the instance log names, else the upload made 0..window_min minutes before the
    error file, else None. The error file's clock is 12-hour without am/pm, so both readings are tried."""
    logged = log_upload(form_folder, error_file)
    if logged:
        return logged
    m = _NAME.search(os.path.basename(error_file))
    root = os.path.join(form_folder, "UploadedFiles")
    if not m or not os.path.isdir(root):
        return None
    t = dt.datetime.strptime(m.group(1) + "-" + m.group(2), "%d-%m-%y-%H-%M-%S")
    ups = {}
    for d in os.listdir(root):
        try:
            ups[_stamp(d)] = os.path.join(root, d)
        except ValueError:
            continue
    for cand in (t, t + dt.timedelta(hours=12)):
        near = [(cand - u, u) for u in ups if dt.timedelta(0) <= cand - u <= dt.timedelta(minutes=window_min)]
        if near:
            folder = ups[min(near)[1]]
            files = [f for f in os.listdir(folder) if f.lower().endswith((".xls", ".xlsx", ".xlsm"))]
            if files:
                return os.path.join(folder, files[0])
    return None
