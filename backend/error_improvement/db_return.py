"""Where a failing fact lives in the database, for returns whose data comes from data-prep (DP) tables.

An Excel return is located as sheet + cell. A DB return is located as table + column + row key. The path is the same
metadata the Excel path already reads, with the XML_Query row of the fact's layout giving the table instead of a sheet:

    fact (concept, context)
      -> Mapping row (layout/template id, Code)            cell_locator.resolve
      -> XML_Query row with TemplateId == layout id        its SQL names the table and the columns
      -> row key: the CODE value, or the typed member of the context (e.g. COUNTRY), plus the reporting date
      -> read-only lookup of that one cell                  db_source
      -> same value as the error file?                      CONFIRMED / INFERRED / MAPPED

Nothing is guessed: a query shape this module does not recognise is simply not located (the caller keeps the old
explanation). Table and column names come only from the repository's own XML_Query file and are checked against a strict
identifier pattern before they are ever used in SQL; values are always bound parameters.
"""
from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_$#]*$")
_EXCEL_RANGE = re.compile(r"\[[^\]]*\$[^\]]*\]")
_DATE_IN_CONTEXT = re.compile(r"(?<!\d)(\d{8})(?!\d)")
_BETWEEN = re.compile(r"([A-Za-z_][\w$#]*)\s+between\s+(\d+)\s+and\s+(\d+)", re.IGNORECASE)
_CODE_ARITH = re.compile(r"^([A-Z_][\w$#]*)((?:\s*[+-]\s*\d+)+)$")
_WRAPPED = re.compile(r"^\s*select\s+\*\s+from\s*\((.*)\)\s*\w*\s*$", re.IGNORECASE | re.DOTALL)
_LITERAL_FILTER = re.compile(r"\b([A-Za-z_][\w$#]*)\s*=\s*'([^']*)'", re.IGNORECASE)


def is_identifier(name: str) -> bool:
    return bool(name) and bool(_IDENT.match(name))


# ── parsing XML_Query ────────────────────────────────────────────────────────
def _split_top_level(text: str, sep: str = ",") -> list[str]:
    out, depth, cur, quote = [], 0, [], False
    for ch in text:
        if ch == "'":
            quote = not quote
        if not quote:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            elif ch == sep and depth == 0:
                out.append("".join(cur).strip())
                cur = []
                continue
        cur.append(ch)
    if "".join(cur).strip():
        out.append("".join(cur).strip())
    return out


def _split_union(sql: str) -> list[str]:
    parts = re.split(r"\bunion\s+all\b|\bunion\b", sql, flags=re.IGNORECASE)
    return [p.strip() for p in parts if p.strip()]


@dataclass
class Branch:
    table: str
    items: dict[str, str]                 # select alias (upper) -> source expression (upper, spaces collapsed)
    filters: dict[str, str] = field(default_factory=dict)   # extra  col = 'literal'  conditions (upper col)
    ranges: dict[str, tuple[int, int]] = field(default_factory=dict)   # col between a and b  (upper col)


@dataclass
class DbQuery:
    query_id: str
    name: str
    template_id: str
    provider_id: str
    branches: list[Branch]


def _top_level_from(sql: str, start: int) -> int | None:
    """Index of the FROM of the outermost SELECT (not one inside extract(... from ...) or a sub-select)."""
    depth, quote = 0, False
    for i in range(start, len(sql)):
        ch = sql[i]
        if ch == "'":
            quote = not quote
        elif not quote:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            elif (depth == 0 and sql[i:i + 4].lower() == "from" and (i == 0 or not (sql[i - 1].isalnum() or sql[i - 1] == "_"))
                  and (i + 4 >= len(sql) or not (sql[i + 4].isalnum() or sql[i + 4] == "_"))):
                return i
    return None


def parse_branch(sql: str) -> Branch | None:
    head = re.match(r"\s*select\s+", sql, flags=re.IGNORECASE)
    cut = _top_level_from(sql, head.end()) if head else None
    if cut is None:
        return None
    cols = sql[head.end():cut].strip()
    m = re.match(r"from\s+([A-Za-z_][\w$#.]*)\b(.*)$", sql[cut:], flags=re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    table, rest = m.group(1), m.group(2)
    if "." in table or not is_identifier(table):
        return None
    items: dict[str, str] = {}
    for item in _split_top_level(cols):
        am = re.match(r"(.*?)\s+(?:as\s+)?([A-Za-z_][\w$#]*)\s*$", item, flags=re.IGNORECASE | re.DOTALL)
        if am and not re.search(r"[(),|]\s*$", am.group(1)) and am.group(1).strip():
            expr, alias = am.group(1).strip(), am.group(2)
        else:
            expr = alias = item.strip()
        items[alias.upper()] = re.sub(r"\s+", " ", expr).upper()
    where = re.search(r"\bwhere\b(.*)$", rest, flags=re.IGNORECASE | re.DOTALL)
    filters = {c.upper(): v for c, v in _LITERAL_FILTER.findall(where.group(1))} if where else {}
    ranges = {c.upper(): (int(a), int(b)) for c, a, b in _BETWEEN.findall(where.group(1))} if where else {}
    return Branch(table.upper(), items, filters, ranges)


def provider_types(folder: str) -> dict[str, set]:
    """{ProviderId: {'oracle'|'excel'|...}} from XML_Providers.xml (next to the return folders). More than one type for an id means
    the file is ambiguous about it."""
    base = os.path.dirname((folder or "").rstrip(os.sep + "/"))
    path = os.path.join(base, "XML_Providers.xml")
    out: dict[str, set] = {}
    if not os.path.isfile(path):
        return out
    try:
        for el in ET.parse(path).getroot().iter("Row"):
            out.setdefault(el.get("ProviderId", ""), set()).add((el.get("ProviderType") or "").strip().lower())
    except ET.ParseError:
        pass
    return out


def _db_eligible(provider_id: str, types: dict[str, set]) -> bool:
    """A query written against a table is used as a database query unless its provider is, unambiguously, not a database
    (e.g. an Excel provider). Unknown or ambiguous providers fall back on what the SQL itself says."""
    if provider_id and os.environ.get(f"EI_DB_PROVIDER_{provider_id}"):
        return True                           # someone named the database for this id outright
    t = types.get(provider_id)
    return not t or len(t) > 1 or "oracle" in t


def load_db_queries(folder: str) -> dict[str, list[DbQuery]]:
    """{template id: its DB queries} from XML_Query.xml; Excel-range rows are skipped (the Excel path owns those)."""
    path = os.path.join(folder, "XML_Query.xml")
    out: dict[str, list[DbQuery]] = {}
    if not os.path.isfile(path):
        return out
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return out
    types = provider_types(folder)
    for el in root.iter("Row"):
        sql = el.findtext("SelectQuery") or ""
        if not sql.strip() or _EXCEL_RANGE.search(sql):
            continue
        if (el.get("IsActive") or "true").strip().lower() == "false":
            continue                          # a switched-off query is not where the data came from
        if not _db_eligible(el.get("ProviderId", ""), types):
            continue                          # its provider says this is not a database (e.g. Excel)
        wrapped = _WRAPPED.match(sql)
        if wrapped:
            sql = wrapped.group(1)
        branches = [b for b in (parse_branch(p) for p in _split_union(sql)) if b]
        if not branches:
            continue
        q = DbQuery(el.get("QueryId", ""), el.get("QueryName", ""), el.get("TemplateId", ""),
                    el.get("ProviderId", ""), branches)
        out.setdefault(q.template_id, []).append(q)
    return out


def load_table_mapping(folder: str) -> dict[str, dict]:
    """{table (upper): {"primary": [...], "filter": str, "edits": n}} from TabelMapping.xml / TableMapping.xml."""
    out: dict[str, dict] = {}
    for name in ("TabelMapping.xml", "TableMapping.xml"):
        path = os.path.join(folder, name)
        if not os.path.isfile(path):
            continue
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError:
            continue
        for el in root.iter("Row"):
            table = (el.get("TableName") or "").upper()
            if not table:
                continue
            primary = [c.strip().upper() for c in (el.get("PrimaryColumn") or "").split("|") if c.strip()]
            meta = list(el.iter("MetaData"))
            out[table] = {
                "primary": primary,
                "filter": (el.get("FilterColumn") or "").upper(),
                "edits": sum(1 for m in meta if m.get("IsEdited") == "true"),
                "last_pull": (meta[-1].get("UpdateDateTime") if meta else ""),
            }
        break
    return out


# ── locating ─────────────────────────────────────────────────────────────────
@dataclass
class DbCell:
    table: str
    column: str
    key: dict[str, str]                   # column -> value that identifies the row (never the date)
    date_column: str
    layout_id: str
    kind: str                             # "code-row" | "wide-row"
    notes: list[str] = field(default_factory=list)
    provider_id: str = ""                 # the XML_Query row's ProviderId: which database holds the table
    alternatives: list[str] = field(default_factory=list)   # value columns the row offers when the mapping alone cannot pick one
    label_column: str = ""                # the row's own description column (ITEM / DESCRIPTION), when the query selects one


def reporting_date(context_id: str) -> str | None:
    """YYYY-MM-DD from a context id such as asof_20260430_Australia, else None (never guessed).
    A period context (fromto_20180901_20180930) reports for its END date, the date the data is stored under."""
    found = _DATE_IN_CONTEXT.findall(context_id or "")
    if not found:
        return None
    s = found[-1]
    if not ("1990" <= s[:4] <= "2100" and "01" <= s[4:6] <= "12" and "01" <= s[6:8] <= "31"):
        return None
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}"


def _plain_column(expr: str) -> str | None:
    return expr if is_identifier(expr) else None


def locate_cell(queries: list[DbQuery], mapping: dict[str, dict], layout_id: str, code: str, typed: dict[str, str]) -> DbCell | None:
    """The table cell behind a mapping row (layout id + Code) for a context with these typed members, or None."""
    code_u = (code or "").upper()
    for q in queries:
        for b in q.branches:
            date_col = (mapping.get(b.table, {}).get("filter") or "RDATE")
            if not is_identifier(date_col):
                continue
            # (1) code-row table:  CODE [|| '_SUFFIX'] as Code ,  <column> as Val
            code_expr, val_expr = b.items.get("CODE"), b.items.get("VAL") or b.items.get("VALUE")
            if code_expr and val_expr and _plain_column(val_expr):
                key_col, key_val = None, None
                if _plain_column(code_expr):
                    key_col, key_val = code_expr, code
                sm = re.match(r"^([A-Z_][\w$#]*)\s*\|\|\s*'([^']*)'$", code_expr)
                if sm:
                    suffix = sm.group(2)
                    if code_u.endswith(suffix.upper()) and len(code) > len(suffix):
                        key_col, key_val = sm.group(1), code[:-len(suffix)]
                # CODE-65+10 as Code: the mapping Code is the stored CODE plus that offset, so invert it. When the query
                # limits CODE to a range (code between a and b) the branch only owns the codes inside it.
                am = _CODE_ARITH.match(code_expr)
                if am and code.strip().lstrip("-").isdigit():
                    offset = sum(int(n.replace(" ", "")) for n in re.findall(r"[+-]\s*\d+", am.group(2)))
                    source = int(code) - offset
                    rng = b.ranges.get(am.group(1))
                    if rng is None and len(q.branches) > 1:
                        continue                      # several UNION branches and nothing says which owns this code: never guess
                    if rng and not (rng[0] <= source <= rng[1]):
                        continue
                    key_col, key_val = am.group(1), str(source)
                if key_col and is_identifier(key_col):
                    key = {key_col: key_val, **{c: v for c, v in b.filters.items() if is_identifier(c)}}
                    return DbCell(b.table, val_expr, key, date_col, layout_id, "code-row", provider_id=q.provider_id, label_column=_label_col(b))
            # (3) one row per CODE with several value columns (current quarter / year, domestic / overseas / global ...): the mapping
            #     Code is the CODE value, and which column holds the fact is decided by reading the row (see resolve_db)
            code_src = b.items.get("CODE")
            if code_src and _plain_column(code_src) and code.strip().isdigit():
                skip = {"CODE", "RDATE", "DESCRIPTION", "ITEM", "SR_NO", date_col}
                values = [src for alias, src in b.items.items()
                          if alias not in skip and _plain_column(src) and src not in skip and alias != "CODE"]
                rng = b.ranges.get(code_src)
                in_range = rng is None or rng[0] <= int(code) <= rng[1]
                if len(values) >= 2 and in_range:
                    key = {code_src: code.strip(), **{c: v for c, v in b.filters.items() if is_identifier(c)}}
                    return DbCell(b.table, values[0], key, date_col, layout_id, "code-multi", provider_id=q.provider_id,
                                  alternatives=values, label_column=_label_col(b))
            # (2) wide table: the mapping Code is a column alias; rows are told apart by the typed member(s)
            src = b.items.get(code_u)
            if src and _plain_column(src) and code_u not in ("CODE", "VAL", "VALUE", "DESCRIPTION"):
                primary = [c for c in mapping.get(b.table, {}).get("primary", []) if c != date_col]
                key: dict[str, str] = {}
                notes: list[str] = []
                if primary and len(typed) == 1 and len(primary) == 1:
                    key[primary[0]] = next(iter(typed.values()))
                elif primary:
                    if len(typed) != len(primary):
                        notes.append("row key not fully determined by the context")
                    else:
                        key = dict(zip(primary, typed.values()))
                key.update({c: v for c, v in b.filters.items() if is_identifier(c)})
                if key and not notes:
                    return DbCell(b.table, src, key, date_col, layout_id, "wide-row", provider_id=q.provider_id, label_column=_label_col(b))
    return None


def pick_column(row_values: dict, instance_value: str, multiplier: int = 1) -> tuple[str | None, str]:
    """Which value column of a row holds the reported figure: ("COLUMN", "") when exactly one does, (None, reason) otherwise. The
    figure itself is the evidence, so two columns holding the same number are never resolved by guessing."""
    hits = [c for c, v in row_values.items() if v is not None and numbers_match(v, instance_value, multiplier)]
    if len(hits) == 1:
        return hits[0], ""
    if not hits:
        return None, "no column of the row holds this value"
    return None, f"{len(hits)} columns of the row hold this value ({', '.join(hits)})"


def _label_col(b: "Branch") -> str:
    for alias in ("DESCRIPTION", "ITEM"):
        src = b.items.get(alias)
        if src and _plain_column(src):
            return src
    return ""


def numbers_match(db_value, instance_value: str, multiplier: int = 1) -> bool:
    try:
        a = Decimal(str(db_value)) * Decimal(multiplier or 1)
        b = Decimal(str(instance_value).replace(",", ""))
    except (InvalidOperation, ValueError):
        return str(db_value).strip() == str(instance_value).strip()
    return abs(a - b) <= Decimal("0.01") + abs(b) * Decimal("1e-9")


# ── plugging into the cell pipeline ──────────────────────────────────────────
# The rest of the engine speaks "Address" (sheet, row, col). A DB address is the same thing with the table as the sheet; the
# row and column numbers are only stable identifiers (so two different cells never look like one), they are never shown.
from . import cell_locator as _cl
from . import fact_address as _fa


@dataclass
class DbAddress(_fa.Address):
    table: str = ""
    column: str = ""
    key: dict = field(default_factory=dict)
    key_text: str = ""
    row_label: str = ""
    reporting_date: str = ""
    kind: str = ""
    verified: bool = False

    is_db = True

    @property
    def a1(self) -> str:                  # what the cards print where an Excel return prints "D32"
        return f"{self.column} ({self.key_text})" if self.key_text else self.column

    @property
    def display(self) -> str:
        return f"{self.table}!{self.a1}"          # same "sheet!cell" shape the rest of the engine splits on


def return_kind(meta) -> bool | None:
    """True = Excel return, False = database return, None = both kinds of query (or nothing to go on).

    Decided from the return's active XML_Query rows: each is a database query (its SQL reads a table and its provider is an Oracle
    source, or is not known to be anything else) or an Excel query (its SQL reads a sheet range, or its provider is an Excel
    source). Only database queries -> a database return, located in its tables and with no workbook to look for. Only Excel
    queries -> an Excel return. Both -> None: each layout is decided by its own query.
    """
    if "_return_kind" in meta.__dict__:
        return meta.__dict__["_return_kind"]
    folder = getattr(meta, "folder", "") or ""
    path = os.path.join(folder, "XML_Query.xml")
    kinds: set = set()
    if os.path.isfile(path):
        types = provider_types(folder)
        try:
            for el in ET.parse(path).getroot().iter("Row"):
                sql = el.findtext("SelectQuery") or ""
                if not sql.strip() or (el.get("IsActive") or "true").strip().lower() == "false":
                    continue
                kinds.add("db" if (not _EXCEL_RANGE.search(sql) and _db_eligible(el.get("ProviderId", ""), types)) else "excel")
        except ET.ParseError:
            pass
    kind = False if kinds == {"db"} else True if kinds == {"excel"} else None
    meta.__dict__["_return_kind"] = kind
    return kind


def enabled() -> bool:
    return os.environ.get("ERROR_IMPROVEMENT_DB", "1").strip().lower() not in ("0", "false", "no", "off")


def _state(meta) -> dict:
    st = meta.__dict__.get("_db_state")
    if st is None:
        folder = getattr(meta, "folder", "") or ""
        st = {"queries": load_db_queries(folder) if folder else {}, "mapping": load_table_mapping(folder) if folder else {},
              "rows": {}, "cols": {}}
        meta.__dict__["_db_state"] = st
    return st


def _slot(table: dict, name) -> int:
    return table.setdefault(name, len(table) + 1)


def _context_of(meta, ctx_id: str):
    rep = getattr(meta, "reported", None)
    if rep is None:
        return None
    dims = rep.ctx_dims(ctx_id)
    if dims is None:
        return None
    return _cl.Context(ctx_id, frozenset(dims.items()), frozenset(rep.typed_values(ctx_id).items()))


def resolve_db(meta, concept: str, ctx_id: str, value: str):
    """A Resolved("MAPPED", [DbAddress]) for a fact whose layout reads a database table, else None. Never guesses: a query
    shape or row key it cannot pin down gives None and the fact stays unlocated, as before."""
    if not enabled():
        return None
    st = _state(meta)
    if not st["queries"]:
        return None
    ctx = _context_of(meta, ctx_id)
    typed = dict(ctx.typed) if ctx else {}
    found = []
    for loc in _cl.resolve(meta, concept, ctx):
        cell = locate_cell(st["queries"].get(loc.layout_id, []), st["mapping"], loc.layout_id, loc.cell_code, typed)
        if cell is None:
            continue
        confirmed_by_db, db_label, state = False, "", "unread"
        mult0 = next((m.multiplier for m in meta.rows_by_concept.get(_cl.local(concept), [])
                      if m.layout_id == loc.layout_id and m.code == loc.cell_code), 1)
        reader, date = _reader_of(meta), reporting_date(ctx_id)
        cols = list(cell.alternatives) or [cell.column]
        want = cols + ([cell.label_column] if cell.label_column and cell.label_column not in cols else [])
        if reader is not None and date:
            state, row = reader.read_row(cell, want, date)
            if state == "ok":
                db_label = str(row.get(cell.label_column) or "").strip() if cell.label_column else ""
                column, _why = pick_column({c: row.get(c) for c in cols}, value, mult0)
                if column is not None:
                    cell.column, confirmed_by_db = column, True
                else:
                    state = "differs"
        if cell.alternatives and not confirmed_by_db:
            continue                                       # several value columns and the data did not settle it: never guess one
        if state == "no-row":
            continue                                       # the database has no such row: this is not where the fact lives
        rowmap = st["rows"].setdefault(cell.table, {})
        colmap = st["cols"].setdefault(cell.table, {})
        key_text = ", ".join(f"{c} = {v}" for c, v in cell.key.items())
        mult = next((m.multiplier for m in meta.rows_by_concept.get(_cl.local(concept), [])
                     if m.layout_id == loc.layout_id and m.code == loc.cell_code), 1)
        a = DbAddress(loc.layout_id, meta.layouts.get(loc.layout_id, ""), cell.table, _slot(rowmap, tuple(cell.key.items())),
                      _slot(colmap, cell.column) - 1, loc.cell_code, mult, None, None,
                      table=cell.table, column=cell.column, key=dict(cell.key), key_text=key_text,
                      row_label=db_label or meta.staging.get((loc.layout_id, loc.cell_code), ""),
                      reporting_date=reporting_date(ctx_id) or "", kind=cell.kind)
        target = _fa._dec(value)
        if target is not None and mult:
            a.workbook_value = float(target / mult)        # the fact's own value, as for a template: the location rests on the mapping
        a.verified = confirmed_by_db
        if all((x.table, x.column, tuple(x.key.items())) != (a.table, a.column, tuple(a.key.items())) for x in found):
            found.append(a)
    if not found:
        return None
    verified = [x for x in found if x.verified]
    if verified:
        found = verified                                   # a candidate the data confirms beats the ones it does not
    note = "" if len(found) == 1 else f"{len(found)} candidate table cells; best by mapping rank first"
    if all(getattr(x, "verified", False) for x in found):
        return _fa.Resolved("CONFIRMED", found[:6], (note + " " if note else "") + "the database row holds this value")
    return _fa.Resolved("MAPPED", found[:6], note)


def _reader_of(meta):
    """One read-only reader per run, or None when no connection can be made (then nothing is read)."""
    from .db_source import DbReader
    rd = meta.__dict__.get("_db_reader")
    if rd is None:
        rd = DbReader(getattr(meta, "folder", "") or "")
        meta.__dict__["_db_reader"] = rd
    return rd
