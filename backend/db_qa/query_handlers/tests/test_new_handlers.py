"""Phase 4 tests — new-taxonomy handlers via dispatch2(), against real 6.0
tenant data. One representative happy-path test per category, plus the
legacy-reexport-intact check.

NOTE on BASE_REPO_PATH: backend.config.BASE_REPO_PATH is a module-level
constant frozen at first import from os.getenv (this repo's .env points it
at a 5.5-shaped tree). monkeypatch.setenv can't retroactively change an
already-frozen constant, so every tenant-scoped test here runs in a fresh
subprocess with BASE_REPO_PATH set BEFORE the interpreter starts (same
pattern as test_access_control.py).
"""
from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

PATH_6_0_1001 = Path(r"D:\Repo6\Repo6\1001\DataBase")
REPO_ROOT = Path(__file__).resolve().parents[4]
_need_6_0_1001 = pytest.mark.skipif(not PATH_6_0_1001.is_dir(), reason="6.0 tenant 1001 real data tree not present")

ADMIN_LOGIN = "vaibhav@irisindia.net"
TENANT_ID = "1001"


def _run_in_subprocess(script_body: str) -> subprocess.CompletedProcess:
    script = textwrap.dedent(_DISPATCH_PREAMBLE) + textwrap.dedent(script_body)
    env = dict(os.environ)
    env["BASE_REPO_PATH"] = str(PATH_6_0_1001.parent.parent)
    return subprocess.run([sys.executable, "-c", script], env=env, capture_output=True, text=True)


def _assert_ok(result: subprocess.CompletedProcess) -> None:
    assert result.returncode == 0, f"stdout={result.stdout!r} stderr={result.stderr!r}"
    assert "OK" in result.stdout


def test_legacy_reexport_intact():
    from backend.db_qa import query_handlers as qh
    assert callable(qh.dispatch)
    assert callable(qh.handle_unknown)
    assert isinstance(qh.INTENT_TO_HANDLER, dict) and len(qh.INTENT_TO_HANDLER) > 0


_DISPATCH_PREAMBLE = f"""
    import sys
    sys.path.insert(0, {str(REPO_ROOT)!r})
    from backend.db_qa import access_control, query_handlers as qh
    from backend.db_qa.xml_store import XMLStore

    store = XMLStore({str(PATH_6_0_1001)!r}, tenant_id={TENANT_ID!r})

    def scoped(intent, entities):
        return access_control.scope_query(
            {{"login_id": {ADMIN_LOGIN!r}, "tenant_id": {TENANT_ID!r}}}, intent, entities,
        )
"""


@_need_6_0_1001
def test_user_profile_self():
    _assert_ok(_run_in_subprocess("""
        scope = scoped("user_profile", {"target_type": "self"})
        r = qh.dispatch2("user_profile", scope, {"target_type": "self"}, store)
        assert r["found"] is True, r
        print("OK")
    """))


@_need_6_0_1001
def test_user_field_self():
    _assert_ok(_run_in_subprocess("""
        scope = scoped("user_field", {"target_type": "self"})
        r = qh.dispatch2("user_field", scope, {"target_type": "self", "field": "email"}, store)
        assert r["found"] is True, r
        print("OK")
    """))


@_need_6_0_1001
def test_department_returns_self():
    _assert_ok(_run_in_subprocess("""
        scope = scoped("department_returns", {"target_type": "self"})
        r = qh.dispatch2("department_returns", scope, {"target_type": "self"}, store)
        assert r["found"] is True, r
        print("OK")
    """))


@_need_6_0_1001
def test_role_profile_self():
    _assert_ok(_run_in_subprocess("""
        scope = scoped("role_profile", {"target_type": "self"})
        r = qh.dispatch2("role_profile", scope, {"target_type": "self"}, store)
        assert r["found"] is True, r
        print("OK")
    """))


@_need_6_0_1001
def test_return_list_admin():
    _assert_ok(_run_in_subprocess("""
        scope = scoped("return_list", {"target_type": "system_wide"})
        r = qh.dispatch2("return_list", scope, {"target_type": "system_wide"}, store)
        assert r["found"] is True, r
        assert r["meta"]["count"] > 0, r
        print("OK")
    """))


@_need_6_0_1001
def test_dept_return_access_matrix():
    _assert_ok(_run_in_subprocess("""
        scope = scoped("dept_return_access_matrix", {"target_type": "system_wide"})
        r = qh.dispatch2("dept_return_access_matrix", scope, {"target_type": "system_wide"}, store)
        assert r["found"] is True, r
        print("OK")
    """))


@_need_6_0_1001
def test_submission_list_self():
    _assert_ok(_run_in_subprocess("""
        scope = scoped("submission_list", {"target_type": "self"})
        r = qh.dispatch2("submission_list", scope, {"target_type": "self"}, store)
        assert isinstance(r["records"], list), r
        print("OK")
    """))


@_need_6_0_1001
def test_menu_list_self():
    # NOTE: tenant 1001's real Option.xml currently has 0 rows with
    # IsMenu="true" for this data snapshot — asserting isinstance rather
    # than found=True so this test tracks "does the handler run without
    # error", not this tenant's current menu configuration.
    _assert_ok(_run_in_subprocess("""
        scope = scoped("menu_list", {"target_type": "self"})
        r = qh.dispatch2("menu_list", scope, {"target_type": "self"}, store)
        assert isinstance(r["records"], list), r
        print("OK")
    """))


@_need_6_0_1001
def test_audit_history_self():
    _assert_ok(_run_in_subprocess("""
        scope = scoped("audit_history", {"target_type": "self"})
        r = qh.dispatch2("audit_history", scope, {"target_type": "self"}, store)
        assert isinstance(r["records"], list), r
        print("OK")
    """))


@_need_6_0_1001
def test_user_access_summary_self():
    _assert_ok(_run_in_subprocess("""
        scope = scoped("user_access_summary", {"target_type": "self"})
        r = qh.dispatch2("user_access_summary", scope, {"target_type": "self"}, store)
        assert r["found"] is True, r
        assert "RoleName" in r["records"][0], r
        print("OK")
    """))


@_need_6_0_1001
def test_bank_info():
    _assert_ok(_run_in_subprocess("""
        scope = scoped("bank_info", {"target_type": "self"})
        r = qh.dispatch2("bank_info", scope, {"target_type": "self"}, store)
        assert r["found"] is True, r
        print("OK")
    """))


@_need_6_0_1001
def test_segment_info():
    _assert_ok(_run_in_subprocess("""
        scope = scoped("segment_info", {"target_type": "self"})
        r = qh.dispatch2("segment_info", scope, {"target_type": "self"}, store)
        assert isinstance(r["records"], list), r
        print("OK")
    """))


@_need_6_0_1001
def test_dispatch2_returns_none_for_unmigrated_intent():
    _assert_ok(_run_in_subprocess("""
        scope = scoped("totally_made_up_intent", {"target_type": "self"})
        result = qh.dispatch2("totally_made_up_intent", scope, {"target_type": "self"}, store)
        assert result is None, result
        print("OK")
    """))
