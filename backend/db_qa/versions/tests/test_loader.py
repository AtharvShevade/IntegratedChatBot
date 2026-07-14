"""Phase 1 data-layer tests — run against the REAL 5.5/6.0 data trees on
this machine, not fixtures. Skips (not fails) when a tree isn't present,
so this suite is safe to run on a machine without the real repos mounted.

Real paths:
  5.5           D:\\Repo(new)\\DataBase
  6.0 tenant 1001  D:\\Repo6\\Repo6\\1001\\DataBase   (full .xml set)
  6.0 tenant 1002  D:\\Repo6\\Repo6\\1002\\DataBase   (partial — some entities JSON-only)
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from backend.db_qa.versions import v5_5_schema, v6_0_schema
from backend.db_qa.versions.loader import load_entity

PATH_5_5 = Path(r"D:\Repo(new)\DataBase")
PATH_6_0_1001 = Path(r"D:\Repo6\Repo6\1001\DataBase")
PATH_6_0_1002 = Path(r"D:\Repo6\Repo6\1002\DataBase")

_need_5_5 = pytest.mark.skipif(not PATH_5_5.is_dir(), reason="5.5 real data tree not present on this machine")
_need_6_0_1001 = pytest.mark.skipif(not PATH_6_0_1001.is_dir(), reason="6.0 tenant 1001 real data tree not present")
_need_6_0_1002 = pytest.mark.skipif(not PATH_6_0_1002.is_dir(), reason="6.0 tenant 1002 real data tree not present")

CREDENTIAL_FIELDS = {
    "Password", "SecondPassword", "ThirdPassword", "FourthPassword", "FifthPassword",
    "Answer", "RefreshToken", "RefreshTokenExpiryTime",
    "ConnectionString",
    "UserNameOrac", "PasswordOrac", "HostNameOrac",
    "PassKey", "Key", "Iv", "RsaPublicKey", "RsaPrivateKey",
}

# Entities confirmed json-only on tenant 1002 (no .xml counterpart there).
# Return.xml -- Return.json is malformed on disk (real data-quality issue,
# not a loader bug); loader correctly logs and degrades to [] rather than
# raising or guessing at repair. Excluded from the "loads > 0 rows" assertion
# accordingly, but still covered by the graceful-degradation test below.
JSON_ONLY_ENTITIES_1002 = ["departments", "roles", "role_access", "options", "nonxbrl_returns"]


def _load_all(base_dir: Path, schema: dict, is_6_0: bool) -> dict[str, list[dict]]:
    return {name: load_entity(name, base_dir, schema=schema, is_6_0=is_6_0) for name in schema}


@_need_5_5
def test_load_all_entities_5_5_no_error():
    result = _load_all(PATH_5_5, v5_5_schema.SCHEMA, is_6_0=False)
    assert set(result.keys()) == set(v5_5_schema.SCHEMA.keys())
    # Every entity should either have rows or (for the tiny reference
    # tables) at least not have blown up — no exceptions is the main bar.
    assert isinstance(result["users"], list) and len(result["users"]) > 0
    assert isinstance(result["departments"], list) and len(result["departments"]) > 0


@_need_6_0_1001
def test_load_all_entities_6_0_1001_no_error():
    result = _load_all(PATH_6_0_1001, v6_0_schema.SCHEMA, is_6_0=True)
    assert set(result.keys()) == set(v6_0_schema.SCHEMA.keys())
    assert isinstance(result["users"], list) and len(result["users"]) > 0
    assert isinstance(result["departments"], list) and len(result["departments"]) > 0


@_need_5_5
@_need_6_0_1001
def test_column_parity_5_5_vs_6_0():
    r5 = _load_all(PATH_5_5, v5_5_schema.SCHEMA, is_6_0=False)
    r6 = _load_all(PATH_6_0_1001, v6_0_schema.SCHEMA, is_6_0=True)
    shared_entities = set(v5_5_schema.SCHEMA.keys()) & set(v6_0_schema.SCHEMA.keys())
    assert shared_entities, "expected at least some entities defined in both schemas"
    for entity in shared_entities:
        rows5, rows6 = r5[entity], r6[entity]
        if not rows5 or not rows6:
            continue  # can't compare keys on an empty result
        assert set(rows5[0].keys()) == set(rows6[0].keys()), (
            f"column mismatch for entity={entity!r}: "
            f"5.5={sorted(rows5[0].keys())} vs 6.0={sorted(rows6[0].keys())}"
        )


def test_attribute_map_excludes_credentials():
    """Schema-only check — no real data needed."""
    for schema_name, schema in (("v5_5", v5_5_schema.SCHEMA), ("v6_0", v6_0_schema.SCHEMA)):
        for entity_name, spec in schema.items():
            raw_values = {v for v in spec.attribute_map.values() if v is not None}
            leaked = raw_values & CREDENTIAL_FIELDS
            assert not leaked, (
                f"{schema_name}.{entity_name}.attribute_map maps a credential field: {leaked}"
            )


@_need_5_5
def test_no_credential_key_in_any_row_5_5():
    result = _load_all(PATH_5_5, v5_5_schema.SCHEMA, is_6_0=False)
    for entity_name, rows in result.items():
        for row in rows:
            leaked = set(row.keys()) & CREDENTIAL_FIELDS
            assert not leaked, f"credential key leaked into {entity_name}: {leaked}"


@_need_6_0_1001
def test_no_credential_key_in_any_row_6_0():
    result = _load_all(PATH_6_0_1001, v6_0_schema.SCHEMA, is_6_0=True)
    for entity_name, rows in result.items():
        for row in rows:
            leaked = set(row.keys()) & CREDENTIAL_FIELDS
            assert not leaked, f"credential key leaked into {entity_name}: {leaked}"


@_need_6_0_1002
def test_json_fallback_tenant_1002():
    """Entities that only have a .json file on tenant 1002 still load."""
    for entity_name in JSON_ONLY_ENTITIES_1002:
        spec = v6_0_schema.SCHEMA[entity_name]
        xml_path = PATH_6_0_1002 / spec.filename
        assert not xml_path.exists(), (
            f"expected {entity_name}'s .xml to be absent on tenant 1002 for this test to be meaningful"
        )
        rows = load_entity(entity_name, PATH_6_0_1002, schema=v6_0_schema.SCHEMA, is_6_0=True)
        assert len(rows) > 0, f"expected JSON fallback to yield rows for {entity_name}"
        # Same logical keys as the 1001 tenant's .xml-backed load.
        rows_1001 = load_entity(entity_name, PATH_6_0_1001, schema=v6_0_schema.SCHEMA, is_6_0=True)
        assert rows_1001, f"1001 comparison data missing for {entity_name}"
        assert set(rows[0].keys()) == set(rows_1001[0].keys())


@_need_6_0_1002
def test_json_fallback_degrades_gracefully_on_malformed_json():
    """Return.json on tenant 1002 is malformed on disk (real data issue, not
    a loader bug) — confirm this degrades to [] rather than raising."""
    spec = v6_0_schema.SCHEMA["returns"]
    xml_path = PATH_6_0_1002 / spec.filename
    assert not xml_path.exists()
    rows = load_entity("returns", PATH_6_0_1002, schema=v6_0_schema.SCHEMA, is_6_0=True)
    assert rows == []


@_need_6_0_1001
def test_period_frequency_present_but_none_6_0():
    rows = load_entity("periods", PATH_6_0_1001, schema=v6_0_schema.SCHEMA, is_6_0=True)
    assert rows, "expected at least one period row"
    for row in rows:
        assert "Frequency" in row
        assert row["Frequency"] in (None, "")


@_need_6_0_1001
def test_frequency_fallback_uses_repfreq():
    """6.0's returns schema exposes RepFreq precisely so callers can fall
    back to it when the period's own Frequency is absent."""
    rows = load_entity("returns", PATH_6_0_1001, schema=v6_0_schema.SCHEMA, is_6_0=True)
    assert rows
    assert "RepFreq" in rows[0]


@_need_5_5
def test_dept_forms_is_string_not_list_5_5():
    rows = load_entity("departments", PATH_5_5, schema=v5_5_schema.SCHEMA, is_6_0=False)
    assert rows
    for row in rows:
        assert isinstance(row["Forms"], str)
        assert isinstance(row["NXForms"], str)


@_need_6_0_1001
def test_dept_forms_is_string_not_list_6_0():
    rows = load_entity("departments", PATH_6_0_1001, schema=v6_0_schema.SCHEMA, is_6_0=True)
    assert rows
    for row in rows:
        assert isinstance(row["Forms"], str)
        assert isinstance(row["NXForms"], str)
