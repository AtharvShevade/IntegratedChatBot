"""Version-agnostic entity loader — the parsing engine behind XMLStore.

Given an EntitySpec (filename, row tag, attribute_map, list_fields, JSON
fallback info) and a base directory, load_entity() returns a list of plain
dicts keyed by *logical* field names, regardless of which raw XML/JSON
attribute names the underlying file actually uses.

Kept independent of XMLStore so it can be unit-tested directly against
real data directories without constructing a store.
"""
from __future__ import annotations

import json
import logging
import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

logger = logging.getLogger("db_qa.versions.loader")


@dataclass(frozen=True)
class EntitySpec:
    """Declarative mapping from one logical entity to its on-disk representation.

    attribute_map:  logical_name -> raw XML/JSON attribute name. Only keys
                    listed here are ever read from the source file — this is
                    what guarantees credential attributes (Password, etc.)
                    can never leak into a loaded row: simply never list them.
    list_fields:    logical names whose raw value is a pipe-delimited string
                    that should become an actual Python list (empty string
                    becomes an empty list, not [""]).
    json_fallback:  if True and the .xml file is missing on disk, fall back
                    to reading json_filename (same attribute_map applies —
                    6.0 JSON twins use the same raw attribute names as the
                    6.0 XML).
    """

    filename: str
    row_tag: str
    attribute_map: dict[str, str | None]
    json_fallback: bool = False
    json_filename: str | None = None
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
    attribute exists in this version at all) — either way the value is
    None, which is what gives column parity across 5.5/6.0 loads.
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


def _parse_json_rows(path: Path) -> list[dict[str, str]] | None:
    """Return raw attribute-like dicts from a JSON array file, or None if
    the file doesn't exist.

    JSON twins are expected to be a list of flat objects using the same
    raw attribute names as the corresponding 6.0 XML file, so the same
    attribute_map can project them. Values are coerced to str to match the
    XML-derived dict shape (ElementTree attributes are always strings).
    """
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8-sig") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Failed to parse %s: %s", path, exc)
        return []
    if not isinstance(data, list):
        logger.error("Expected a JSON array in %s, got %s", path, type(data).__name__)
        return []
    rows: list[dict[str, str]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        rows.append({k: ("" if v is None else str(v)) for k, v in item.items()})
    return rows


def load_entity(
    entity_name: str,
    base_dir: str | Path,
    *,
    schema: dict[str, EntitySpec],
    is_6_0: bool = False,
    normalize: Callable[[list[dict]], list[dict]] | None = None,
) -> list[dict]:
    """Load one entity's rows as logical-keyed dicts.

    Resolution order: parse <filename> as XML; if missing on disk and
    spec.json_fallback and is_6_0, parse spec.json_filename as JSON instead.
    Returns [] if the entity isn't in *schema* or neither file is present.
    """
    spec = schema.get(entity_name)
    if spec is None:
        logger.warning("[loader] Unknown entity_name=%r — returning []", entity_name)
        return []

    base = Path(base_dir)
    xml_path = base / spec.filename
    raw_rows = _parse_xml_rows(xml_path, spec.row_tag)

    if raw_rows is None:
        if spec.json_fallback and is_6_0 and spec.json_filename:
            json_path = base / spec.json_filename
            raw_rows = _parse_json_rows(json_path)
            if raw_rows is not None:
                logger.info(
                    "[loader] %s: .xml missing, used JSON fallback %s (%d rows)",
                    entity_name, json_path, len(raw_rows),
                )
        if raw_rows is None:
            logger.warning(
                "[loader] %s: neither %s nor a JSON fallback found under %s",
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
