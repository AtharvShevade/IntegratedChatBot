"""Phase 1 XMLStore-level integration tests — confirm XMLStore (schema-driven)
behaves correctly end-to-end against real data, and that existing accessor
signatures/return shapes are unchanged.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from backend.db_qa.xml_store import XMLStore, _SENSITIVE_FIELDS

PATH_5_5 = Path(r"D:\Repo(new)\DataBase")

_need_5_5 = pytest.mark.skipif(not PATH_5_5.is_dir(), reason="5.5 real data tree not present")


def test_sensitive_fields_includes_refresh_token():
    assert "RefreshToken" in _SENSITIVE_FIELDS
    assert "RefreshTokenExpiryTime" in _SENSITIVE_FIELDS


@_need_5_5
def test_xmlstore_5_5_all_accessors_work():
    store = XMLStore(str(PATH_5_5))
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


@_need_5_5
def test_get_app_db_base_path_default_ctor_5_5(monkeypatch):
    """XMLStore() with no db_path resolves via config.APP_DB_BASE_PATH."""
    monkeypatch.setenv("BASE_REPO_PATH", str(PATH_5_5.parent))
    store = XMLStore()
    assert store._db == PATH_5_5


@_need_5_5
def test_no_credential_field_via_public_accessors():
    """Even ignoring _safe()'s stripping, the raw accessor output must never
    contain a credential key — this is enforced at the schema layer."""
    cred_fields = {
        "Password", "SecondPassword", "ThirdPassword", "FourthPassword",
        "FifthPassword", "Answer", "RefreshToken", "RefreshTokenExpiryTime",
    }
    store = XMLStore(str(PATH_5_5))
    for u in store.users():
        assert not (set(u.keys()) & cred_fields)
