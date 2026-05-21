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


def parse_sql_schema(sql_text):
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
            })

    return tables
