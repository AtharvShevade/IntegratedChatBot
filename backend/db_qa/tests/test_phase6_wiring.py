"""Phase 6 wiring tests — new_intent_classifier + db_qa_router integration,
and decide()'s dispatch2-then-legacy-fallback behavior, against real 6.0
tenant data.

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
REPO_ROOT = Path(__file__).resolve().parents[3]
_need_6_0_1001 = pytest.mark.skipif(not PATH_6_0_1001.is_dir(), reason="6.0 tenant 1001 real data tree not present")

ADMIN_LOGIN = "vaibhav@irisindia.net"
TENANT_ID = "1001"


def _run_in_subprocess(script_body: str) -> subprocess.CompletedProcess:
    script = textwrap.dedent(f"""
        import sys
        sys.path.insert(0, {str(REPO_ROOT)!r})
    """) + textwrap.dedent(script_body)
    env = dict(os.environ)
    env["BASE_REPO_PATH"] = str(PATH_6_0_1001.parent.parent)
    return subprocess.run([sys.executable, "-c", script], env=env, capture_output=True, text=True)


def _assert_ok(result: subprocess.CompletedProcess) -> None:
    assert result.returncode == 0, f"stdout={result.stdout!r} stderr={result.stderr!r}"
    assert "OK" in result.stdout


def test_new_intent_classifier_matches_representative_questions():
    from backend.db_qa.new_intent_classifier import classify_new
    from backend.db_qa.intents.taxonomy import Intent

    cases = [
        ("what is my email", Intent.USER_FIELD, "self"),
        ("list all users", Intent.USER_LIST, "system_wide"),
        ("what is my role", Intent.ROLE_PROFILE, "self"),
        ("what permissions do I have", Intent.PERMISSION_PROFILE, "self"),
        ("show bank details", Intent.BANK_INFO, "self"),
    ]
    for question, expected_intent, expected_tt in cases:
        intent, params, tt = classify_new(question)
        assert intent == expected_intent, f"{question!r} -> {intent}, expected {expected_intent}"
        assert tt == expected_tt


def test_new_intent_classifier_returns_none_for_gibberish():
    from backend.db_qa.new_intent_classifier import classify_new
    intent, params, tt = classify_new("completely unrelated gibberish xyz123")
    assert intent is None
    assert params == {}
    assert tt is None


def test_check_new_taxonomy_intent_wraps_classify_new():
    from backend.agent.db_qa_router import check_new_taxonomy_intent
    intent, params = check_new_taxonomy_intent("what is my email")
    assert intent == "user_field"
    assert params.get("target_type") == "self"


@_need_6_0_1001
def test_handle_db_qa_query_new_taxonomy_self_service():
    _assert_ok(_run_in_subprocess(f"""
        from backend.agent.db_qa_router import handle_db_qa_query
        r = handle_db_qa_query(
            message="what is my email", intent="user_field",
            params={{"target_type": "self", "field": "email"}},
            user_id={ADMIN_LOGIN!r}, role_id="101", beautify=False, login_id={ADMIN_LOGIN!r},
            tenant_id={TENANT_ID!r},
        )
        assert r["db_found"] is True, r
        assert r["result_type"] == "db_qa_result", r
        print("OK")
    """))


@_need_6_0_1001
def test_handle_db_qa_query_legacy_path_still_works():
    _assert_ok(_run_in_subprocess(f"""
        from backend.agent.db_qa_router import handle_db_qa_query
        r = handle_db_qa_query(
            message="what is my department", intent="db_my_department",
            params={{}}, user_id={ADMIN_LOGIN!r}, role_id="101", beautify=False, login_id={ADMIN_LOGIN!r},
            tenant_id={TENANT_ID!r},
        )
        assert r["db_found"] is True, r
        assert r["result_type"] == "db_qa_result", r
        print("OK")
    """))


@_need_6_0_1001
def test_decide_end_to_end_new_taxonomy():
    _assert_ok(_run_in_subprocess(f"""
        import asyncio
        from backend.agent import decide

        async def run():
            return await decide(
                "what is my email", session_id="pytest-session-a",
                login_id={ADMIN_LOGIN!r}, user_id={ADMIN_LOGIN!r}, role_id="101",
                tenant_id={TENANT_ID!r},
            )

        result = asyncio.run(run())
        assert result.get("intent") == "user_field", result
        print("OK")
    """))
