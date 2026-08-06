import re
from collections import defaultdict


TABLE_PATTERN = re.compile(
    r'CREATE\s+TABLE\s+(?:"(?P<quoted_table>[^"]+)"|(?P<plain_table>[\w.]+))\s*\((?P<body>.*?)\)\s*;',
    re.DOTALL | re.IGNORECASE,
)

COLUMN_PATTERN = re.compile(
    r'^(?:"(?P<quoted_column>[^"]+)"|(?P<plain_column>\w+))\s+(?P<column_type>[A-Za-z][A-Za-z0-9_]*(?:\s*\([^)]*\))?)',
    re.IGNORECASE,
)

CONSTRAINT_PREFIXES = (
    "constraint",
    "primary key",
    "foreign key",
    "unique",
    "check",
)

# ── Constraint patterns ──────────────────────────────────────────────────────
# Table-level constraints were previously skipped outright, which is why
# schema.json carried no PK/FK information at all. With nothing telling the
# model how tables relate, it fabricated join keys — the single largest failure
# category in eval/results/hallucination_log.jsonl (invented `..._fk`, `.id`).

_PK_PATTERN = re.compile(
    r'primary\s+key\s*\((?P<cols>[^)]*)\)',
    re.IGNORECASE,
)

_FK_PATTERN = re.compile(
    r'foreign\s+key\s*\((?P<cols>[^)]*)\)\s*references\s+'
    r'(?:"(?P<quoted_ref>[^"]+)"|(?P<plain_ref>[\w.]+))'
    r'(?:\s*\((?P<ref_cols>[^)]*)\))?',
    re.IGNORECASE,
)

_UNIQUE_PATTERN = re.compile(
    r'unique\s*\((?P<cols>[^)]*)\)',
    re.IGNORECASE,
)


def _split_column_defs(body: str) -> list:
    """
    Split a CREATE TABLE body into individual column definition strings,
    respecting nested parentheses (e.g. NUMBER(20,2), VARCHAR2(200)).
    Works whether the DDL is multi-line or all on a single line.
    """
    parts = []
    depth = 0
    current = []
    for ch in body:
        if ch == '(':
            depth += 1
            current.append(ch)
        elif ch == ')':
            depth -= 1
            current.append(ch)
        elif ch == ',' and depth == 0:
            token = ''.join(current).strip()
            if token:
                parts.append(token)
            current = []
        else:
            current.append(ch)
    tail = ''.join(current).strip()
    if tail:
        parts.append(tail)
    return parts


def _split_identifier_list(raw: str) -> list:
    """'CODE, "RDATE"' -> ['code', 'rdate']"""
    out = []
    for part in raw.split(","):
        name = part.strip().strip('"').strip().lower()
        if name:
            out.append(name)
    return out


def parse_sql_schema(sql_text):
    """
    Parse CREATE TABLE statements into {table: [column, ...]}.

    Each column carries:
        name        – lowercase column name
        type        – declared type, e.g. "number(20,2)", "varchar2(200)"
        nullable    – False when the definition says NOT NULL
        is_primary_key – True for an inline column-level PRIMARY KEY

    Table-level PRIMARY KEY / FOREIGN KEY constraints are returned separately by
    parse_constraints(); this function also back-fills is_primary_key from them
    when the same sql_text is parsed by parse_schema_and_constraints().
    """
    tables = defaultdict(list)

    for match in TABLE_PATTERN.finditer(sql_text):
        table_name = (match.group("quoted_table") or match.group("plain_table")).lower()
        cols_block = match.group("body")

        for column_line in _split_column_defs(cols_block):
            if not column_line:
                continue

            lowered_line = column_line.lower().lstrip()
            if lowered_line.startswith(CONSTRAINT_PREFIXES):
                continue

            column_match = COLUMN_PATTERN.match(column_line.lstrip())
            if not column_match:
                continue

            column_name = (column_match.group("quoted_column") or column_match.group("plain_column")).lower()
            column_type = column_match.group("column_type").lower()

            tables[table_name].append({
                "name": column_name,
                "type": column_type,
                "nullable": "not null" not in lowered_line,
                "is_primary_key": bool(re.search(r'\bprimary\s+key\b', lowered_line)),
            })

    return tables


def parse_constraints(sql_text):
    """
    Extract table-level constraints from CREATE TABLE statements.

    Returns {table: {"primary_key": [col, ...],
                     "foreign_keys": [{"columns": [...],
                                       "ref_table": str,
                                       "ref_columns": [...]}, ...],
                     "unique": [[col, ...], ...]}}

    Only tables that actually declare a constraint appear in the result. Oracle
    is the authoritative source for these (see extract_constraints.py); this
    parser only recovers what the checked-in DDL happens to declare.
    """
    constraints = {}

    for match in TABLE_PATTERN.finditer(sql_text):
        table_name = (match.group("quoted_table") or match.group("plain_table")).lower()
        entry = {"primary_key": [], "foreign_keys": [], "unique": []}

        for column_line in _split_column_defs(match.group("body")):
            lowered_line = column_line.lower().lstrip()
            if not lowered_line.startswith(CONSTRAINT_PREFIXES):
                # An inline column-level PRIMARY KEY still belongs in the PK list.
                col_match = COLUMN_PATTERN.match(column_line.lstrip())
                if col_match and re.search(r'\bprimary\s+key\b', lowered_line):
                    name = (col_match.group("quoted_column") or col_match.group("plain_column")).lower()
                    if name not in entry["primary_key"]:
                        entry["primary_key"].append(name)
                continue

            # A named constraint ("CONSTRAINT pk_x PRIMARY KEY (...)") carries its
            # kind after the name, so match against the whole line either way.
            fk_match = _FK_PATTERN.search(column_line)
            if fk_match:
                ref_table = (fk_match.group("quoted_ref") or fk_match.group("plain_ref")).lower()
                entry["foreign_keys"].append({
                    "columns": _split_identifier_list(fk_match.group("cols")),
                    "ref_table": ref_table,
                    "ref_columns": _split_identifier_list(fk_match.group("ref_cols") or ""),
                })
                continue

            pk_match = _PK_PATTERN.search(column_line)
            if pk_match:
                for col in _split_identifier_list(pk_match.group("cols")):
                    if col not in entry["primary_key"]:
                        entry["primary_key"].append(col)
                continue

            uq_match = _UNIQUE_PATTERN.search(column_line)
            if uq_match:
                cols = _split_identifier_list(uq_match.group("cols"))
                if cols:
                    entry["unique"].append(cols)

        if entry["primary_key"] or entry["foreign_keys"] or entry["unique"]:
            constraints[table_name] = entry

    return constraints


def parse_schema_and_constraints(sql_text):
    """
    Convenience wrapper: parse columns and constraints in one pass and reconcile
    them, so a column named by a table-level PRIMARY KEY is flagged
    is_primary_key=True on the column object itself. That flag is what the DDL
    serializer in src/sql_generator.py renders as "PRIMARY KEY".

    Returns (tables, constraints).
    """
    tables = parse_sql_schema(sql_text)
    constraints = parse_constraints(sql_text)

    for table, entry in constraints.items():
        pk_cols = set(entry["primary_key"])
        if not pk_cols:
            continue
        for col in tables.get(table, []):
            if col["name"] in pk_cols:
                col["is_primary_key"] = True

    return tables, constraints
