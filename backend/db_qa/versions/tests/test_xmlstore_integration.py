"""Phase 1 XMLStore-level integration tests — confirm the migrated XMLStore
(schema-driven, tenant-aware) behaves correctly end-to-end against real
data, and that existing accessor signatures/return shapes are unchanged.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from backend.db_qa.xml_store import XMLStore, _SENSITIVE_FIELDS

PATH_5_5 = Path(r"D:\Repo(new)\DataBase")
PATH_6_0_1001 = Path(r"D:\Repo6\Repo6\1001\DataBase")
PATH_6_0_1002 = Path(r"D:\Repo6\Repo6\1002\DataBase")

_need_5_5 = pytest.mark.skipif(not PATH_5_5.is_dir(), reason="5.5 real data tree not present")
_need_6_0_1001 = pytest.mark.skipif(not PATH_6_0_1001.is_dir(), reason="6.0 tenant 1001 real data tree not present")
_need_6_0_1002 = pytest.mark.skipif(not PATH_6_0_1002.is_dir(), reason="6.0 tenant 1002 real data tree not present")


def test_sensitive_fields_includes_refresh_token():
    assert "RefreshToken" in _SENSITIVE_FIELDS
    assert "RefreshTokenExpiryTime" in _SENSITIVE_FIELDS


@_need_5_5
def test_xmlstore_5_5_all_accessors_work():
    store = XMLStore(str(PATH_5_5), tenant_id=None)
    assert len(store.users()) > 0
    assert len(store.departments()) > 0
    assert len(store.roles()) > 0
    assert len(store.role_access()) > 0
    assert len(store.returns()) > 0
    assert len(store.non_xbrl_returns()) > 0
    assert len(store.options()) > 0
    assert len(store.periods()) > 0
    assert len(store.instance_log()) > 0
    assert len(store.audit_log()) > 0
    # Entity genuinely absent on disk (confirmed in the audit) degrades to [].
    assert store.user_levels() == []


@_need_6_0_1001
def test_xmlstore_6_0_1001_all_accessors_work(monkeypatch):
    # APP_VERSION is a deployment-level switch (see version_mode.py) — a
    # real 6.0 backend process always has this set; tests must too.
    monkeypatch.setenv("APP_VERSION", "6.0")
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
def test_xmlstore_6_0_1002_json_fallback(monkeypatch):
    monkeypatch.setenv("APP_VERSION", "6.0")
    store = XMLStore(str(PATH_6_0_1002), tenant_id="1002")
    assert len(store.departments()) > 0
    assert len(store.roles()) > 0
    assert len(store.role_access()) > 0
    assert len(store.options()) > 0
    assert len(store.non_xbrl_returns()) > 0
    # Return.json is malformed on disk — real data issue, not a code bug;
    # confirm graceful degradation rather than a crash.
    assert store.returns() == []


@_need_5_5
def test_get_app_db_base_path_default_ctor_5_5(monkeypatch):
    """XMLStore() with no db_path resolves via config.get_app_db_base_path."""
    monkeypatch.setenv("BASE_REPO_PATH", str(PATH_5_5.parent))
    monkeypatch.setenv("APP_VERSION", "5.5")
    store = XMLStore(tenant_id=None)
    assert store._db == PATH_5_5


@_need_5_5
@_need_6_0_1001
def test_no_credential_field_via_public_accessors():
    """Even ignoring _safe()'s stripping, the raw accessor output must never
    contain a credential key — this is enforced at the schema layer."""
    cred_fields = {
        "Password", "SecondPassword", "ThirdPassword", "FourthPassword",
        "FifthPassword", "Answer", "RefreshToken", "RefreshTokenExpiryTime",
    }
    store_5_5 = XMLStore(str(PATH_5_5), tenant_id=None)
    for u in store_5_5.users():
        assert not (set(u.keys()) & cred_fields)

    store_6_0 = XMLStore(str(PATH_6_0_1001), tenant_id="1001")
    for u in store_6_0.users():
        assert not (set(u.keys()) & cred_fields)
