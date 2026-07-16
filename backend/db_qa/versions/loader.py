"""Entity loader — the parsing engine behind XMLStore.

Given an EntitySpec (filename, row tag, attribute_map, list_fields) and a
base directory, load_entity() returns a list of plain dicts keyed by
*logical* field names, regardless of which raw XML attribute names the
underlying file actually uses.

Kept independent of XMLStore so it can be unit-tested directly against
real data directories without constructing a store.
"""
from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

logger = logging.getLogger("db_qa.versions.loader")


@dataclass(frozen=True)
class EntitySpec:
    """Declarative mapping from one logical entity to its on-disk representation.

    attribute_map:  logical_name -> raw XML attribute name. Only keys
                    listed here are ever read from the source file — this is
                    what guarantees credential attributes (Password, etc.)
                    can never leak into a loaded row: simply never list them.
    list_fields:    logical names whose raw value is a pipe-delimited string
                    that should become an actual Python list (empty string
                    becomes an empty list, not [""]).
    """

    filename: str
    row_tag: str
    attribute_map: dict[str, str | None]
    list_fields: tuple[str, ...] = ()


def _split_list_field(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [part.strip() for part in raw.split("|") if part.strip()]


def _project_row(raw_attrs: dict[str, str], attribute_map: dict[str, str | None],
                  list_fields: tuple[str, ...]) -> dict:
    """Build one logical-keyed row dict from a raw attribute dict.

    Every logical key in attribute_map is present in the output, even when
    the raw attribute is absent from this particular row, or when the
    schema explicitly maps a logical field to `None` (no equivalent raw
    attribute exists at all) — either way the value is None.
    """
    row: dict = {}
    for logical_name, raw_name in attribute_map.items():
        value = raw_attrs.get(raw_name) if raw_name is not None else None
        if logical_name in list_fields:
            row[logical_name] = _split_list_field(value)
        else:
            row[logical_name] = value
    return row


def _parse_xml_rows(path: Path, row_tag: str) -> list[dict[str, str]] | None:
    """Return raw attribute dicts for every <row_tag> element, or None if
    the file doesn't exist. Mirrors xml_store._parse_xml's BOM/encoding
    tolerance.
    """
    if not path.exists():
        return None
    try:
        with path.open("rb") as fh:
            raw = fh.read()
        try:
            root = ET.fromstring(raw)
        except ET.ParseError:
            raw = raw.lstrip(b"\xef\xbb\xbf")
            root = ET.fromstring(raw)
        return [dict(el.attrib) for el in root.findall(row_tag)]
    except ET.ParseError as exc:
        logger.error("Failed to parse %s: %s", path, exc)
        return []


def load_entity(
    entity_name: str,
    base_dir: str | Path,
    *,
    schema: dict[str, EntitySpec],
    normalize: Callable[[list[dict]], list[dict]] | None = None,
) -> list[dict]:
    """Load one entity's rows as logical-keyed dicts.

    Returns [] if the entity isn't in *schema* or the file isn't present.
    """
    spec = schema.get(entity_name)
    if spec is None:
        logger.warning("[loader] Unknown entity_name=%r — returning []", entity_name)
        return []

    base = Path(base_dir)
    xml_path = base / spec.filename
    raw_rows = _parse_xml_rows(xml_path, spec.row_tag)

    if raw_rows is None:
        logger.warning(
            "[loader] %s: %s not found under %s",
            entity_name, spec.filename, base,
        )
        return []

    rows = [_project_row(r, spec.attribute_map, spec.list_fields) for r in raw_rows]

    if normalize is not None:
        rows = normalize(rows)

    return rows


def build_index(rows: list[dict], key_field: str) -> dict[str, dict]:
    """Generic single-key index: {str(row[key_field]).strip(): row}.

    Last row wins on duplicate keys. Rows missing/blank key_field are
    skipped. Intended for NEW entities added alongside the ~48-intent
    catalog — XMLStore's existing user/dept/role/return indexes have their
    own by-name+by-id nuances and are left as-is.
    """
    index: dict[str, dict] = {}
    for row in rows:
        key = row.get(key_field)
        if key is None:
            continue
        key = str(key).strip()
        if not key:
            continue
        index[key] = row
    return index
