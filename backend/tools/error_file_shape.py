# backend/tools/error_file_shape.py — structural inspection of a validation
# error file: which product it is, which panels it carries, and — the point of
# the module — whether a given table actually carries DB backtracking columns.
#
# WHY THIS EXISTS
# ---------------
# Routing used to be decided by `_is_4000_series(form_id)` (4000 <= id <= 4999)
# as a proxy for "this file has backtracking data". Measured against the real
# corpus the proxy is wrong in one direction for five files:
#
#   4038/IDIB…_BTDetails.html   4000-series, HAS backtracking   (11 columns)
#   4040/CREDITHAB…_BTDetails   4000-series, HAS backtracking   (12 columns)
#   4046, 4080  BTDetails       4000-series, HAS backtracking
#   4044/SMCB…_Instance.html    4000-series, NO backtracking    (7 columns)
#   4012, 4005, 4020            4000-series, NO backtracking
#   4038/ABPL…_Instance.html    4000-series, NO backtracking
#
# So backtracking is a property of the individual TABLE inside the file, never
# of the return. This module answers that question from the table's own <th>
# row, and nothing here reads a form id, a return id, or a filename.

from __future__ import annotations

import html as _html
import logging
import os
import re

logger = logging.getLogger(__name__)

__all__ = [
    "BACKTRACK_HEADER_TOKENS", "PLAIN_HEADER_TOKENS",
    "header_has_backtracking", "canonical_header_key",
    "read_error_file", "extract_tab_pane", "split_formula_panels",
    "split_spec_panels", "normalise_panel_name", "extract_tables", "extract_header_cells",
    "extract_body_rows", "strip_tags", "clean_cell",
    "describe_error_file",
]


# ─────────────────────────────────────────────────────────────────────────────
# Header vocabulary. Two disjoint sets, both drawn from the real files; a table
# is "backtracking-enabled" when enough of the DB-side vocabulary is present.
# ─────────────────────────────────────────────────────────────────────────────

BACKTRACK_HEADER_TOKENS = frozenset({
    "db tablename", "db table name", "cell code", "cell index",
    "variable id", "row label(s)", "column label(s)", "table header",
    "instance data(s)", "entered data(s)",
})

PLAIN_HEADER_TOKENS = frozenset({
    "variable", "name", "value", "context", "unit", "decimal", "precision",
})

# Column-name -> canonical field. Covers both table shapes in one map: header
# labels are unambiguous across shapes, so a single map is safe and means a
# new column ordering (or a new mixed shape) needs no code change.
_HEADER_FIELD_MAP: dict[str, str] = {
    # plain (validation-output) shape
    "variable":          "var",
    "name":              "concept",
    "value":             "value",
    "context":           "context",
    "unit":              "unit",
    "decimal":           "decimal",
    "precision":         "precision",
    # backtracking (BTDetails) shape
    "variable id":       "var",
    "db tablename":      "db_table",
    "db table name":     "db_table",
    "cell index":        "cell_index",
    "table header":      "table_header",
    "column label(s)":   "column_label",
    "column label":      "column_label",
    "row label(s)":      "row_label",
    "row label":         "row_label",
    "instance data(s)":  "value",
    "instance data":     "value",
    "entered data(s)":   "entered_value",
    "entered data":      "entered_value",
    "cell code":         "cell_code",
}

# At least this many distinct backtracking-only column labels must be present
# before a table is treated as backtracking-enabled. Two, not one, because
# "Table Header" and "Column Label(s)" alone would be a weak signal; the real
# backtracking tables carry six or more.
_MIN_BACKTRACK_TOKENS = 2

_BACKTRACK_ONLY_TOKENS = BACKTRACK_HEADER_TOKENS - PLAIN_HEADER_TOKENS


def canonical_header_key(header: str) -> str:
    """Canonical field name for one column header, or "" when unrecognised."""
    return _HEADER_FIELD_MAP.get((header or "").strip().lower(), "")


def header_has_backtracking(headers: list[str] | tuple[str, ...] | None) -> bool:
    """True when this table's own header row carries DB-backtracking columns.

    The single decision point for "can this error be explained with source
    data". Structural: no return id, no filename, no panel id is consulted.
    """
    if not headers:
        return False
    seen = {(h or "").strip().lower() for h in headers}
    return len(seen & _BACKTRACK_ONLY_TOKENS) >= _MIN_BACKTRACK_TOKENS


# ─────────────────────────────────────────────────────────────────────────────
# HTML helpers — shared by the formula and dimension flows so both agree on
# what a cell, a row, and a panel are.
# ─────────────────────────────────────────────────────────────────────────────

_TAG_RE = re.compile(r"<[^>]+>")
_BR_RE = re.compile(r"<br\s*/?>|</br>", re.IGNORECASE)


def strip_tags(fragment: str) -> str:
    text = _BR_RE.sub(" ", fragment or "")
    text = _TAG_RE.sub(" ", text)
    return _html.unescape(text).replace(" ", " ")


def clean_cell(fragment: str) -> str:
    """One table cell's display text.

    The leading-quote strip matters: the plain shape writes its variable ids as
    `"V2` (a stray opening quote from the generator's own string building), and
    leaving it in place meant every `$V2` lookup in the formula missed.
    """
    text = re.sub(r"\s+", " ", strip_tags(fragment)).strip()
    return text.lstrip('"').strip()


def read_error_file(path: str) -> str:
    """Whole-file read with the encoding discipline the corpus needs (French
    accents, '≤', '▼', NBSP). Returns "" rather than raising for any I/O
    problem — every caller treats "" as "nothing to explain"."""
    if not path or not os.path.isfile(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError as exc:
        logger.warning("[error_file_shape] cannot read %s: %s", path, exc)
        return ""


def extract_tab_pane(raw_html: str, tab_id: str = "1") -> str:
    """Isolate one Bootstrap tab-pane. The three tabs reuse the same CSS
    classes, so a whole-document scan for `assertionLabel` picks up unrelated
    errors from the other two (measured: >2x over-count on real files).

    Both quoting styles occur — `id="1"` in validation output, `id='1'` in
    BTDetails — and the tab panes are NOT in numeric order in BTDetails
    (3, 2, 1), so this bounds on "the next tab-pane div", whichever it is,
    rather than on tab_id + 1.
    """
    if not raw_html:
        return ""
    open_re = re.compile(
        r"""<div[^>]*class=["'][^"']*tab-pane[^"']*["'][^>]*id=["']""" + re.escape(tab_id) + r"""["'][^>]*>"""
        r"""|<div[^>]*id=["']""" + re.escape(tab_id) + r"""["'][^>]*class=["'][^"']*tab-pane[^"']*["'][^>]*>""",
        re.IGNORECASE,
    )
    m = open_re.search(raw_html)
    if not m:
        return ""
    rest = raw_html[m.end():]
    nxt = re.search(
        r"""<div[^>]*class=["'][^"']*tab-pane[^"']*["']""", rest, re.IGNORECASE,
    )
    return rest[: nxt.start()] if nxt else rest


# Formula panels are `errorPanelN` in validation output and `formulaErrorPanelN`
# in BTDetails. The class-based alternative catches any future id scheme.
_PANEL_SPLIT_RE = re.compile(
    r"""(?=<div[^>]*class=["'][^"']*panel-default[^"']*["'][^>]*id=["'](?:formulaError|error)Panel\d+["'])"""
    r"""|(?=<div[^>]*id=["'](?:formulaError|error)Panel\d+["'][^>]*class=["'][^"']*panel-default[^"']*["'])""",
    re.IGNORECASE,
)

_GENERIC_PANEL_SPLIT_RE = re.compile(
    r"""(?=<div[^>]*class=["'][^"']*panel\s+panel-default[^"']*["'])""", re.IGNORECASE,
)


def split_formula_panels(tab_html: str) -> list[str]:
    """One string per formula-error panel, id-scheme agnostic."""
    if not tab_html:
        return []
    parts = _PANEL_SPLIT_RE.split(tab_html)
    panels = [p for p in parts if p and "assertionLabel" in p]
    if panels:
        return panels
    # Fall back to a purely class-based split for any file whose panel ids
    # don't follow either known scheme.
    parts = _GENERIC_PANEL_SPLIT_RE.split(tab_html)
    return [p for p in parts if p and "assertionLabel" in p]


_SPEC_PANEL_ID_RE = re.compile(r"""<div[^>]*id=["']([A-Za-z_]+)Panel["']""", re.IGNORECASE)

# The generator spells the same panel differently across products
# ('dimentionPanel' in validation output, 'DIMENSIONPanel' in BTDetails) while
# its badge is always 'DIMENSIONErrorNum'. Normalising both onto one key is
# what lets a single lookup work for either product. Keys are the misspelling
# actually present in the files, not a guess at what it should be.
_PANEL_NAME_ALIASES = {
    "DIMENTION": "DIMENSION",
    "CONSCALC": "CONSCALC",
    "INCONSCALC": "INCONSCALC",
}


def normalise_panel_name(name: str) -> str:
    key = (name or "").strip().upper()
    return _PANEL_NAME_ALIASES.get(key, key)


def split_spec_panels(raw_html: str) -> dict[str, str]:
    """SPECIFICATION_ERROR panels keyed by their normalised name.

    Every spec panel (XBRL_SCHEMA, DIMENSION, TABLE, FORMULA, …) uses the SAME
    `<td class="directMsg">` markup, so bounding by panel is the only thing
    that stops a TABLE-panel warning from being reported as a dimension error.
    Bounding here is done by "up to the next panel div", which is exact for
    this generator's flat panel layout and never depends on `</div>` counting.

    Panel ids are inconsistently spelled across products ('dimentionPanel' in
    validation output, 'DIMENSIONPanel' in BTDetails) so keys are uppercased
    and the caller matches on a normalised name.
    """
    if not raw_html:
        return {}
    marks = [(m.start(), m.group(1)) for m in _SPEC_PANEL_ID_RE.finditer(raw_html)]
    out: dict[str, str] = {}
    for i, (pos, name) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(raw_html)
        key = normalise_panel_name(name)
        out[key] = out.get(key, "") + raw_html[pos:end]
    return out


_TABLE_RE = re.compile(r"<table[^>]*>(.*?)</table>", re.S | re.IGNORECASE)
_HEADER_CELL_RE = re.compile(r"""<t[hd][^>]*class=["'][^"']*headerCell[^"']*["'][^>]*>(.*?)</t[hd]>""",
                             re.S | re.IGNORECASE)
_ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.IGNORECASE)
_CELL_RE = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S | re.IGNORECASE)
_FV_ROW_RE = re.compile(r"""<tr[^>]*class=["'][^"']*\bfv\b[^"']*["'][^>]*>(.*?)</tr>""",
                        re.S | re.IGNORECASE)


def extract_tables(panel_html: str) -> list[str]:
    """Each <table> in a panel is one failing instance of that rule."""
    return _TABLE_RE.findall(panel_html or "")


def extract_header_cells(table_html: str) -> list[str]:
    """The table's own header labels, in document order. [] when the table has
    no header row — the caller must then NOT fall back to a positional
    mapping, because column counts differ between the 11- and 12-column
    backtracking layouts."""
    return [clean_cell(c) for c in _HEADER_CELL_RE.findall(table_html or "")]


def extract_body_rows(table_html: str) -> list[list[str]]:
    """Variable rows (`<tr class="… fv …">`) as lists of cell texts."""
    rows: list[list[str]] = []
    for row_html in _FV_ROW_RE.findall(table_html or ""):
        cells = [clean_cell(c) for c in _CELL_RE.findall(row_html)]
        if cells:
            rows.append(cells)
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# Whole-file description — used for logging/diagnostics and by the router to
# decide, per file, what is worth parsing.
# ─────────────────────────────────────────────────────────────────────────────

_BADGE_RE = re.compile(r"""id=["']([A-Za-z_]+)ErrorNum["'][^>]*>\s*(\d+)\s*<""", re.IGNORECASE)


def describe_error_file(path: str) -> dict:
    """Structural profile of one error file. Never raises.

    {
      "path", "exists", "kind": "html"|"xml"|"missing",
      "tabs": [...],
      "formula_panel_count": int,
      "formula_has_backtracking": bool,   # any formula table carries DB columns
      "spec_panels": {NAME: badge_count},
      "badges": {NAME: count},
    }
    """
    info: dict = {
        "path": path, "exists": False, "kind": "missing", "tabs": [],
        "formula_panel_count": 0, "formula_has_backtracking": False,
        "spec_panels": {}, "badges": {},
    }
    if not path or not os.path.isfile(path):
        return info
    info["exists"] = True

    if os.path.splitext(path)[1].lower() != ".html":
        info["kind"] = "xml"
        return info
    info["kind"] = "html"

    raw = read_error_file(path)
    if not raw:
        return info

    info["tabs"] = [t.strip() for t in re.findall(
        r"""data-toggle=["']tab["']>\s*([^<]*?)\s*<""", raw, re.IGNORECASE)]
    info["badges"] = {normalise_panel_name(name): int(count) for name, count in _BADGE_RE.findall(raw)}
    info["spec_panels"] = {
        name: info["badges"].get(name, 0) for name in split_spec_panels(raw)
    }

    panels = split_formula_panels(extract_tab_pane(raw, "1"))
    info["formula_panel_count"] = len(panels)
    for panel in panels:
        for table in extract_tables(panel):
            if header_has_backtracking(extract_header_cells(table)):
                info["formula_has_backtracking"] = True
                break
        if info["formula_has_backtracking"]:
            break

    return info
