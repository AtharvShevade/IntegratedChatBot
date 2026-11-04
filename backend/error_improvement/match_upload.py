"""Pair an error file with the workbook the user uploaded just before it
(repo layout: <form>/UploadedFiles/<dd-mm-yy-HH-MM-SS>/<file>, newer returns <form>/UploadedFiles/<yyyymmddHHMMSS>/<file>)."""
import datetime as dt
import os
import re

_NAME = re.compile(r"_(\d\d-\d\d-\d\d)_(\d\d-\d\d-\d\d)_")


def _stamp(folder_name: str) -> dt.datetime:
    """The time an upload folder is named after: dd-mm-yy-HH-MM-SS, else yyyymmddHHMMSS. ValueError when it is neither."""
    try:
        return dt.datetime.strptime(folder_name, "%d-%m-%y-%H-%M-%S")
    except ValueError:
        return dt.datetime.strptime(folder_name, "%Y%m%d%H%M%S")


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
    """Path of the upload made 0..window_min minutes before the error file, or None.
    The error file's clock is 12-hour without am/pm, so both readings are tried."""
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
