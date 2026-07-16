"""Phase 1 data-layer tests — run against the REAL 5.5 data tree on this
machine, not fixtures. Skips (not fails) when the tree isn't present, so
this suite is safe to run on a machine without the real repo mounted.

Real path:
  D:\\Repo(new)\\DataBase
"""
from __future__ import annotations

from pathlib import Path

import pytest

from backend.db_qa.versions import v5_5_schema
from backend.db_qa.versions.loader import load_entity

PATH_5_5 = Path(r"D:\Repo(new)\DataBase")

_need_5_5 = pytest.mark.skipif(not PATH_5_5.is_dir(), reason="5.5 real data tree not present on this machine")

CREDENTIAL_FIELDS = {
    "Password", "SecondPassword", "ThirdPassword", "FourthPassword", "FifthPassword",
    "Answer", "RefreshToken", "RefreshTokenExpiryTime",
    "ConnectionString",
    "UserNameOrac", "PasswordOrac", "HostNameOrac",
    "PassKey", "Key", "Iv", "RsaPublicKey", "RsaPrivateKey",
}


def _load_all(base_dir: Path, schema: dict) -> dict[str, list[dict]]:
    return {name: load_entity(name, base_dir, schema=schema) for name in schema}


@_need_5_5
def test_load_all_entities_5_5_no_error():
    result = _load_all(PATH_5_5, v5_5_schema.SCHEMA)
    assert set(result.keys()) == set(v5_5_schema.SCHEMA.keys())
    # Every entity should either have rows or (for the tiny reference
    # tables) at least not have blown up — no exceptions is the main bar.
    assert isinstance(result["users"], list) and len(result["users"]) > 0
    assert isinstance(result["departments"], list) and len(result["departments"]) > 0


def test_attribute_map_excludes_credentials():
    """Schema-only check — no real data needed."""
    for entity_name, spec in v5_5_schema.SCHEMA.items():
        raw_values = {v for v in spec.attribute_map.values() if v is not None}
        leaked = raw_values & CREDENTIAL_FIELDS
        assert not leaked, (
            f"v5_5.{entity_name}.attribute_map maps a credential field: {leaked}"
        )


@_need_5_5
def test_no_credential_key_in_any_row_5_5():
    result = _load_all(PATH_5_5, v5_5_schema.SCHEMA)
    for entity_name, rows in result.items():
        for row in rows:
            leaked = set(row.keys()) & CREDENTIAL_FIELDS
            assert not leaked, f"credential key leaked into {entity_name}: {leaked}"


@_need_5_5
def test_dept_forms_is_string_not_list_5_5():
    rows = load_entity("departments", PATH_5_5, schema=v5_5_schema.SCHEMA)
    assert rows
    for row in rows:
        assert isinstance(row["Forms"], str)
        assert isinstance(row["NXForms"], str)
