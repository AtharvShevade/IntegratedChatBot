"""Phase 3 access-control tests — run against real 6.0 tenant data.

Real login_ids used (confirmed present in the real data tree):
  6.0 tenant 1001 (D:\\Repo6\\Repo6\\1001\\DataBase): vaibhav@irisindia.net (RoleId=101, admin)

NOTE on BASE_REPO_PATH: backend.config.BASE_REPO_PATH is read once, at
first import, from os.getenv. Because of this, tests that need a
DIFFERENT BASE_REPO_PATH than whatever this test session's process
happened to import backend.config with cannot use monkeypatch.setenv (it's
too late — the module-level constant is already frozen). Where that
matters, the test below runs in a subprocess with the env var set BEFORE
the interpreter starts, which is the only way to genuinely exercise a
different BASE_REPO_PATH in-process.
"""
from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from backend.db_qa import access_control

PATH_6_0_1001 = Path(r"D:\Repo6\Repo6\1001\DataBase")
REPO_ROOT = Path(__file__).resolve().parents[3]

_need_6_0_1001 = pytest.mark.skipif(not PATH_6_0_1001.is_dir(), reason="6.0 tenant 1001 real data tree not present")

ADMIN_LOGIN_6_0 = "vaibhav@irisindia.net"


def test_is_admin_false_for_unknown_login():
    assert access_control.is_admin("no-such-user-xyz", tenant_id=None) is False


def test_is_admin_false_for_empty_login():
    assert access_control.is_admin("", tenant_id=None) is False


def test_unrecognized_target_type_denied():
    with pytest.raises(PermissionError):
        access_control.scope_query(
            {"login_id": "whoever", "tenant_id": "1001"}, "user_list", {"target_type": "totally_bogus"},
        )


def test_tenant_id_enforced():
    with pytest.raises(PermissionError):
        access_control.scope_query(
            {"login_id": ADMIN_LOGIN_6_0},  # tenant_id deliberately omitted
            "user_list", {"target_type": "system_wide"},
        )


@_need_6_0_1001
def test_tenant_id_present_allows_6_0_admin():
    # backend.config.BASE_REPO_PATH is a module-level constant frozen at
    # first import from os.getenv — this test process may have already
    # imported it (e.g. transitively, via access_control -> auth_service ->
    # config) with BASE_REPO_PATH pointed elsewhere per the real .env.
    # monkeypatch.setenv can't retroactively change an already-frozen
    # constant, so this genuinely needs a fresh subprocess with the right
    # env vars set BEFORE the interpreter starts.
    script = textwrap.dedent(f"""
        import sys
        sys.path.insert(0, {str(REPO_ROOT)!r})
        from backend.db_qa import access_control
        scope = access_control.scope_query(
            {{"login_id": {ADMIN_LOGIN_6_0!r}, "tenant_id": "1001"}},
            "user_list", {{"target_type": "system_wide"}},
        )
        assert scope["is_admin"] is True, scope
        assert scope["tenant_id"] == "1001", scope
        print("OK")
    """)
    env = dict(os.environ)
    env["BASE_REPO_PATH"] = str(PATH_6_0_1001.parent.parent)
    result = subprocess.run(
        [sys.executable, "-c", script], env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, f"stdout={result.stdout!r} stderr={result.stderr!r}"
    assert "OK" in result.stdout


def test_tenant_id_never_sourced_from_entities():
    """Even if a malicious/confused caller puts tenant_id in `entities`
    (which would come from LLM-extracted chat text), scope_query must
    never read it from there — only from session_user."""
    with pytest.raises(PermissionError):
        access_control.scope_query(
            {"login_id": "whoever", "tenant_id": None},
            "user_field",
            {"target_type": "self", "tenant_id": "attacker-supplied-tenant"},
        )
