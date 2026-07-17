"""Phase 1 XMLStore-level integration tests — confirm the migrated XMLStore
(schema-driven, tenant-aware) behaves correctly end-to-end against real
data, and that existing accessor signatures/return shapes are unchanged.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from backend.db_qa.xml_store import XMLStore, _SENSITIVE_FIELDS

PATH_6_0_1001 = Path(r"D:\Repo6\Repo6\1001\DataBase")
PATH_6_0_1002 = Path(r"D:\Repo6\Repo6\1002\DataBase")

_need_6_0_1001 = pytest.mark.skipif(not PATH_6_0_1001.is_dir(), reason="6.0 tenant 1001 real data tree not present")
_need_6_0_1002 = pytest.mark.skipif(not PATH_6_0_1002.is_dir(), reason="6.0 tenant 1002 real data tree not present")


def test_sensitive_fields_includes_refresh_token():
    assert "RefreshToken" in _SENSITIVE_FIELDS
    assert "RefreshTokenExpiryTime" in _SENSITIVE_FIELDS


@_need_6_0_1001
def test_xmlstore_6_0_1001_all_accessors_work():
    store = XMLStore(str(PATH_6_0_1001), tenant_id="1001")
    assert len(store.users()) > 0
    assert len(store.departments()) > 0
    assert len(store.roles()) > 0
    assert len(store.role_access()) > 0
    assert len(store.returns()) > 0
    assert len(store.options()) > 0
    assert len(store.periods()) > 0
    assert len(store.instance_log()) > 0
    # Confirmed absent in 6.0 entirely — must degrade to [], not error.
    assert store.segments() == []
    assert store.cross_validation_log() == []
    assert store.upload_file_log() == []


@_need_6_0_1002
def test_xmlstore_6_0_1002_json_fallback():
    store = XMLStore(str(PATH_6_0_1002), tenant_id="1002")
    assert len(store.departments()) > 0
    assert len(store.roles()) > 0
    assert len(store.role_access()) > 0
    assert len(store.options()) > 0
    assert len(store.non_xbrl_returns()) > 0
    # Return.json is malformed on disk — real data issue, not a code bug;
    # confirm graceful degradation rather than a crash.
    assert store.returns() == []


@_need_6_0_1001
def test_no_credential_field_via_public_accessors():
    """Even ignoring _safe()'s stripping, the raw accessor output must never
    contain a credential key — this is enforced at the schema layer."""
    cred_fields = {
        "Password", "SecondPassword", "ThirdPassword", "FourthPassword",
        "FifthPassword", "Answer", "RefreshToken", "RefreshTokenExpiryTime",
    }
    store_6_0 = XMLStore(str(PATH_6_0_1001), tenant_id="1001")
    for u in store_6_0.users():
        assert not (set(u.keys()) & cred_fields)
