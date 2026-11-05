"""Read values from the user's workbook by sheet and A1 address (.xls via xlrd, .xlsx via openpyxl).

xlrd is needed only for the old .xls format; it is looked up in ./_libs when it is not
installed in the active environment (normally it is: pip install -r requirements.txt).
"""
from __future__ import annotations

import io
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))


def col_to_index(letters: str) -> int:
    n = 0
    for ch in letters.upper():
        n = n * 26 + ord(ch) - 64
    return n - 1


def index_to_col(i: int) -> str:
    s, i = "", i + 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def split_range(rng: str) -> tuple[int, int]:
    """'B7:AF20' -> (first row 7, first column index 1)."""
    m = re.match(r"([A-Za-z]+)(\d+)", rng)
    return int(m.group(2)), col_to_index(m.group(1))


class Workbook:
    def __init__(self, path: str):
        self.path = path
        self.is_template = False        # True when this is the blank template (labels only, no filed values)
        ext = os.path.splitext(path)[1].lower()
        self._xls = None
        self._xlsx = None
        with open(path, "rb") as fh:
            is_zip = fh.read(2) == b"PK"            # real format, whatever the extension says
        if ext == ".xls" and not is_zip:
            if os.path.join(_HERE, "_libs") not in sys.path:
                sys.path.insert(0, os.path.join(_HERE, "_libs"))
            import xlrd                                  # noqa: PLC0415
            self._xls = xlrd.open_workbook(path)
            self.sheets = self._xls.sheet_names()
        else:
            import openpyxl                              # noqa: PLC0415
            self._xlsx = openpyxl.load_workbook(io.BytesIO(open(path, "rb").read()), data_only=True, read_only=False)
            self.sheets = self._xlsx.sheetnames
        self._cache: dict[str, object] = {}

    def has_sheet(self, name: str) -> bool:
        return name in self.sheets

    def value(self, sheet: str, row: int, col: int):
        """Cell value at 1-based row and 0-based column index, or None when empty / outside the sheet / no such sheet."""
        if sheet not in self.sheets:
            return None
        if self._xls is not None:
            sh = self._cache.get(sheet) or self._xls.sheet_by_name(sheet)
            self._cache[sheet] = sh
            if row - 1 >= sh.nrows or col >= sh.ncols or row < 1 or col < 0:
                return None
            v = sh.cell_value(row - 1, col)
            return None if v == "" else v
        grid = self._cache.get(("grid", sheet))
        if grid is None:                                   # one pass per sheet, then plain dict lookups
            grid = {}
            for r in self._xlsx[sheet].iter_rows():
                for c in r:
                    if c.value is not None:
                        grid[(c.row, c.column - 1)] = c.value
            self._cache[("grid", sheet)] = grid
        return grid.get((row, col))

    def index(self, sheet: str) -> dict:
        """value -> [(row, col)] for one sheet: numbers rounded to 4 places, text lower-cased. Built once, then cached."""
        key = ("idx", sheet)
        if key in self._cache:
            return self._cache[key]
        idx: dict = {}

        def add(v, r, c):
            if isinstance(v, bool) or v is None or v == "":
                return
            k = round(float(v), 4) if isinstance(v, (int, float)) else str(v).strip().lower()
            idx.setdefault(k, []).append((r, c))

        if self._xls is not None:
            sh = self._xls.sheet_by_name(sheet)
            for r in range(sh.nrows):
                for c in range(sh.ncols):
                    add(sh.cell_value(r, c), r + 1, c)
        else:
            for row in self._xlsx[sheet].iter_rows():
                for cell in row:
                    add(cell.value, cell.row, cell.column - 1)
        self._cache[key] = idx
        return idx

    def merged(self, sheet: str) -> list[tuple[int, int, int, int]]:
        """The merged ranges of a sheet as (first row, first col, last row, last col): rows 1-based, columns 0-based. A merged heading
        holds its text in the first cell only; this says which other cells it covers. Empty when they cannot be read."""
        key = ("merged", sheet)
        if key in self._cache:
            return self._cache[key]
        out: list = []
        try:
            if self._xlsx is not None:
                out = [(r.min_row, r.min_col - 1, r.max_row, r.max_col - 1) for r in self._xlsx[sheet].merged_cells.ranges]
            else:
                if "xls_fmt" not in self._cache:                   # merged ranges of an .xls need the formatting pass: read it once, lazily
                    import xlrd                                    # noqa: PLC0415
                    self._cache["xls_fmt"] = xlrd.open_workbook(self.path, formatting_info=True)
                sh = self._cache["xls_fmt"].sheet_by_name(sheet)
                out = [(rlo + 1, clo, rhi, chi - 1) for rlo, rhi, clo, chi in sh.merged_cells]
        except Exception:                                          # noqa: BLE001  unreadable merges just mean no merged headings
            out = []
        self._cache[key] = out
        return out

    def text_row(self, sheet: str, row: int, first_col: int = 0, last_col: int = 6) -> str:
        """The label text of a row (first few columns), for human-readable reports."""
        parts = []
        for c in range(first_col, last_col + 1):
            v = self.value(sheet, row, c)
            if isinstance(v, str) and v.strip():
                parts.append(v.strip())
        return " | ".join(parts)


def sheet_names(path: str) -> list[str]:
    """Sheet names without loading the cells (xlsx: read workbook.xml; old xls: xlrd on demand)."""
    with open(path, "rb") as fh:
        is_zip = fh.read(2) == b"PK"
    if is_zip:
        import re as _re
        import zipfile
        with zipfile.ZipFile(path) as z:
            xml = z.read("xl/workbook.xml").decode("utf-8", "ignore")
        import html as _html
        return [_html.unescape(n) for n in _re.findall(r"<sheet [^>]*?name=\"([^\"]+)\"", xml)]
    if os.path.join(_HERE, "_libs") not in sys.path:
        sys.path.insert(0, os.path.join(_HERE, "_libs"))
    import xlrd                                              # noqa: PLC0415
    return xlrd.open_workbook(path, on_demand=True).sheet_names()


def pick_template_path(meta, folder: str) -> str | None:
    """The template workbook in a return's metadata folder that holds most of the sheets the layouts read."""
    wanted = {sheet for rngs in meta.sheets.values() for sheet, _ in rngs}
    best, best_n = None, 0
    for name in sorted(os.listdir(folder)):
        if not name.lower().endswith((".xls", ".xlsx", ".xlsm")) or name.startswith("~"):
            continue
        try:
            n = len(wanted & set(sheet_names(os.path.join(folder, name))))
        except Exception:                                    # noqa: BLE001 - unreadable template: try the next
            continue
        if n > best_n:
            best, best_n = os.path.join(folder, name), n
    return best


def pick_template(meta, folder: str) -> "Workbook | None":
    """The same template, opened as a Workbook flagged as blank (labels only, no filed values)."""
    path = pick_template_path(meta, folder)
    if path is None:
        return None
    wb = Workbook(path)
    wb.is_template = True
    return wb


class EmptyWorkbook:
    """Stands in when no workbook or template is available, so every stage runs and simply finds no cells."""
    sheets: list = []
    is_template = False
    path = ""
    formulas = None

    def has_sheet(self, name):
        return False

    def value(self, sheet, row, col):
        return None

    def index(self, sheet):
        return {}

    def merged(self, sheet):
        return []

    def text_row(self, *a, **k):
        return ""
