"""Make a template's formulas readable: convert a binary .xls to .xlsx once, keep the copy in a cache.

openpyxl reads formulas only from .xlsx; the old binary format keeps them in a form no library we have can decode. So a
binary template is converted by a program that can open it - Microsoft Excel (COM, Windows) or LibreOffice (headless) -
and the converted copy is cached outside the repo, keyed by the template's path, size and modified time. The original file
is only ever opened read-only and is never overwritten. If neither program is available the function returns None and
the caller simply goes without formula reasoning.

    readable_template(path) -> path of an .xlsx with formulas, or None
Environment: TEMPLATE_CACHE_DIR overrides the cache folder; TEMPLATE_CONVERT_TIMEOUT (seconds, default 180).
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_EXCEL_PS = r"""
$ErrorActionPreference = 'Stop'
$xl = New-Object -ComObject Excel.Application
$xl.Visible = $false; $xl.DisplayAlerts = $false; $xl.AutomationSecurity = 3
try {
  $wb = $xl.Workbooks.Open($env:TPL_SRC, 0, $true)
  $wb.SaveAs($env:TPL_DST, 51)
  $wb.Close($false)
} finally { $xl.Quit(); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($xl) }
"""


def is_xlsx(path: str) -> bool:
    try:
        with open(path, "rb") as fh:
            return fh.read(2) == b"PK"
    except OSError:
        return False


def cache_dir() -> str:
    d = os.environ.get("TEMPLATE_CACHE_DIR") or os.path.join(_HERE, ".template_cache")
    os.makedirs(d, exist_ok=True)
    return d


def cache_path(src: str) -> str:
    st = os.stat(src)
    key = hashlib.sha1(f"{os.path.abspath(src)}|{st.st_size}|{int(st.st_mtime)}".encode()).hexdigest()[:16]
    return os.path.join(cache_dir(), f"{os.path.splitext(os.path.basename(src))[0]}_{key}.xlsx")


def _excel_exe() -> str | None:
    if sys.platform != "win32":
        return None
    for root in (os.environ.get("ProgramFiles", r"C:\Program Files"), os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")):
        for rel in (r"Microsoft Office\root\Office16\EXCEL.EXE", r"Microsoft Office\Office16\EXCEL.EXE",
                    r"Microsoft Office\root\Office15\EXCEL.EXE", r"Microsoft Office\Office15\EXCEL.EXE"):
            p = os.path.join(root, rel)
            if os.path.isfile(p):
                return p
    return None


def _soffice() -> str | None:
    found = shutil.which("soffice") or shutil.which("libreoffice")
    if found:
        return found
    for root in (os.environ.get("ProgramFiles", r"C:\Program Files"), os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")):
        p = os.path.join(root, "LibreOffice", "program", "soffice.exe")
        if os.path.isfile(p):
            return p
    return None


def _timeout() -> int:
    try:
        return int(os.environ.get("TEMPLATE_CONVERT_TIMEOUT", "180"))
    except ValueError:
        return 180


def _convert_with_excel(src: str, dst: str) -> bool:
    if _excel_exe() is None:
        return False
    env = {**os.environ, "TPL_SRC": src, "TPL_DST": dst}
    try:
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", _EXCEL_PS],
                       env=env, capture_output=True, timeout=_timeout(), check=True)
    except (subprocess.SubprocessError, OSError):
        return False
    return os.path.isfile(dst) and is_xlsx(dst)


def _convert_with_libreoffice(src: str, dst: str) -> bool:
    exe = _soffice()
    if exe is None:
        return False
    out = os.path.join(os.path.dirname(dst), "_lo_out")
    os.makedirs(out, exist_ok=True)
    try:
        subprocess.run([exe, "--headless", "--convert-to", "xlsx", "--outdir", out, src],
                       capture_output=True, timeout=_timeout(), check=True)
        produced = os.path.join(out, os.path.splitext(os.path.basename(src))[0] + ".xlsx")
        if os.path.isfile(produced):
            shutil.move(produced, dst)
    except (subprocess.SubprocessError, OSError):
        return False
    return os.path.isfile(dst) and is_xlsx(dst)


CONVERTERS = (_convert_with_excel, _convert_with_libreoffice)


def readable_template(path: str | None) -> str | None:
    """Path of an .xlsx (the template itself, or its cached conversion) whose formulas openpyxl can read; None if impossible."""
    if not path or not os.path.isfile(path):
        return None
    if is_xlsx(path):
        return path
    dst = cache_path(path)
    if os.path.isfile(dst) and is_xlsx(dst):
        return dst
    tmp = dst + ".part.xlsx"
    for convert in CONVERTERS:
        if os.path.isfile(tmp):
            os.remove(tmp)
        if convert(path, tmp):
            os.replace(tmp, dst)                  # the cache entry appears only when the conversion finished
            return dst
    return None
