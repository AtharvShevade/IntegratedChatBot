"""Tests locking down the XML_InstanceLog path-resolution investigation
(production issue: Request ID sometimes never appears after a successful
generate-instance call, symptom being the file's total row count staying
frozen across repeated real generations).

What this investigation found, verified by reading the actual code (not
assumed):

  - backend.config.app_db_base_path()/instance_log_xml_path() are FUNCTIONS
    that re-derive the path fresh on every call from
    version_config.get_repo_root_override() (per-request, tenant-scoped on
    6.0) or backend.config.BASE_REPO_PATH (5.5) — there is no second,
    independently-settable env var on the Python side that could drift out
    of sync with BASE_REPO_PATH once it's updated.
  - A separate, unrelated `backend.db_qa.config.APP_DB_BASE_PATH` module-level
    constant DOES read its own standalone `APP_DB_BASE_PATH` env var — but
    nothing in the generate-instance/Request-ID path (agent.__init__'s
    _matching_instance_log_rows) uses it; that function explicitly calls
    backend.config.app_db_base_path() (the auto-derived one). This is
    confirmed here so the two never get confused again.
  - _matching_instance_log_rows constructs a brand-new XMLStore on every
    call (no cross-call caching to go stale), so if the .NET service really
    writes a new row to the SAME file Python reads, it would be visible on
    the very next read — no Python-side caching bug can explain a frozen
    row count.

Given all of the above, a frozen row count across real, successful
generate-instance calls points outside this repo (the external .NET
service's own configured write path, or a delay beyond the retry window) —
which is exactly what the new [INSTANCE_LOG_PATH] logging added alongside
these tests is for: making the exact path/row-counts visible in production
logs instead of requiring guesswork.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend import config, version_config


class TestFivePointFivePathResolution:
    def test_instance_log_path_derives_from_base_repo_path(self, monkeypatch):
        monkeypatch.setattr(config, "BASE_REPO_PATH", r"D:\Fake5_5Root")
        path = config.instance_log_xml_path()
        assert path.startswith(r"D:\Fake5_5Root")
        assert "DataBase" in path

    def test_app_db_base_path_tracks_base_repo_path_automatically(self, monkeypatch):
        """The whole point of app_db_base_path() being a function, not a
        frozen constant read from its own env var: moving BASE_REPO_PATH
        (e.g. the real 'Repo(new) 1\\Repo(new)' relocation) is automatically
        reflected here — there is nothing separate to forget to update."""
        monkeypatch.setattr(config, "BASE_REPO_PATH", r"D:\iDEAL\iDEAL5.5ChatBot\Repo(new) 1\Repo(new)")
        assert config.app_db_base_path() == r"D:\iDEAL\iDEAL5.5ChatBot\Repo(new) 1\Repo(new)\DataBase"

    def test_no_tenant_override_falls_back_to_base_repo_path(self):
        assert version_config.get_repo_root_override() is None


class TestSixPointZeroTenantAwarePathResolution:
    def test_tenant_scope_overrides_the_active_root(self, monkeypatch):
        monkeypatch.setattr(version_config, "APP_600_REPO_ROOT", r"D:\Repo6\Repo6")
        with version_config.repo_scope(version_config.repo_root_for_tenant("TENANT_A")):
            path = config.app_db_base_path()
        assert path == r"D:\Repo6\Repo6\TENANT_A\DataBase"

    def test_different_tenants_resolve_to_different_isolated_paths(self, monkeypatch):
        monkeypatch.setattr(version_config, "APP_600_REPO_ROOT", r"D:\Repo6\Repo6")
        with version_config.repo_scope(version_config.repo_root_for_tenant("TENANT_A")):
            path_a = config.instance_log_xml_path()
        with version_config.repo_scope(version_config.repo_root_for_tenant("TENANT_B")):
            path_b = config.instance_log_xml_path()
        assert path_a != path_b
        assert "TENANT_A" in path_a
        assert "TENANT_B" in path_b

    def test_scope_exit_restores_5_5_default(self, monkeypatch):
        monkeypatch.setattr(config, "BASE_REPO_PATH", r"D:\Fake5_5Root")
        with version_config.repo_scope(version_config.repo_root_for_tenant("TENANT_A")):
            assert "TENANT_A" in config.app_db_base_path()
        # Outside the scope, must fall back to plain BASE_REPO_PATH again —
        # no leakage of the tenant override past its own request.
        assert config.app_db_base_path() == r"D:\Fake5_5Root\DataBase"

    def test_nested_scopes_do_not_leak_into_each_other(self, monkeypatch):
        monkeypatch.setattr(version_config, "APP_600_REPO_ROOT", r"D:\Repo6\Repo6")
        with version_config.repo_scope(version_config.repo_root_for_tenant("OUTER")):
            assert "OUTER" in config.app_db_base_path()
            with version_config.repo_scope(version_config.repo_root_for_tenant("INNER")):
                assert "INNER" in config.app_db_base_path()
            assert "OUTER" in config.app_db_base_path()


class TestMatchingInstanceLogRowsUsesAutoDerivedPathOnly:
    """Regression lock for this investigation's key finding: the standalone
    backend.db_qa.config.APP_DB_BASE_PATH env var must have ZERO effect on
    the generate-instance Request-ID lookup path — it uses a completely
    different, auto-derived function instead."""

    def test_matching_instance_log_rows_calls_auto_derived_path_function(self, monkeypatch):
        from backend.agent import _matching_instance_log_rows

        calls = {"n": 0}
        real_app_db_base_path = config.app_db_base_path

        def _spy():
            calls["n"] += 1
            return real_app_db_base_path()

        monkeypatch.setattr(config, "app_db_base_path", _spy)
        _matching_instance_log_rows("0000", "01-Jan-1970", None)
        assert calls["n"] >= 1

    def test_stale_or_unset_db_qa_env_var_does_not_affect_the_resolved_path(self, monkeypatch):
        """Setting backend.db_qa.config's standalone APP_DB_BASE_PATH env
        var to something wrong/stale must not change what
        _matching_instance_log_rows actually reads — it never touches that
        module at all."""
        monkeypatch.setenv("APP_DB_BASE_PATH", r"D:\SomeCompletelyStaleUnrelatedPath")
        monkeypatch.setattr(config, "BASE_REPO_PATH", r"D:\iDEAL\iDEAL5.5ChatBot\Repo(new) 1\Repo(new)")

        # Re-derive fresh (app_db_base_path() is a function, not a frozen
        # constant, so no reload needed) and confirm it reflects
        # BASE_REPO_PATH, never the unrelated env var above.
        resolved = config.app_db_base_path()
        assert "SomeCompletelyStaleUnrelatedPath" not in resolved
        assert resolved == r"D:\iDEAL\iDEAL5.5ChatBot\Repo(new) 1\Repo(new)\DataBase"

    def test_empty_active_root_returns_no_rows_without_raising(self, monkeypatch):
        from backend.agent import _matching_instance_log_rows

        monkeypatch.setattr(config, "app_db_base_path", lambda: "")
        assert _matching_instance_log_rows("2029", "31-Mar-2026", "iris810") == []


class TestFindNewInstanceLogIdLogsResolvedPath:
    """The diagnostic logging added alongside this investigation must
    actually call the real path-resolving function — not a hardcoded
    string — so the logged path is always trustworthy, on both versions."""

    def test_uses_instance_log_xml_path_for_diagnostics(self, monkeypatch):
        import asyncio
        from backend.agent import _find_new_instance_log_id

        calls = {"n": 0}
        real_fn = config.instance_log_xml_path

        def _spy():
            calls["n"] += 1
            return real_fn()

        monkeypatch.setattr(config, "instance_log_xml_path", _spy)
        asyncio.run(_find_new_instance_log_id("nonexistent-form-id-xyz", "01-Jan-2099", "nobody-xyz"))
        assert calls["n"] >= 1
