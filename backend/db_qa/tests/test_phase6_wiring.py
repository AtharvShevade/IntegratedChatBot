"""Phase 6 wiring tests — new_intent_classifier + db_qa_router integration,
and decide()'s dispatch2-then-legacy-fallback behavior, against real 5.5 data.
"""
from __future__ import annotations

from pathlib import Path

import pytest

PATH_5_5 = Path(r"D:\Repo(new)\DataBase")
_need_5_5 = pytest.mark.skipif(not PATH_5_5.is_dir(), reason="5.5 real data tree not present")

ADMIN_LOGIN = "iris810"
NON_ADMIN_LOGIN = "test810"


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


@_need_5_5
def test_handle_db_qa_query_new_taxonomy_self_service():
    from backend.agent.db_qa_router import handle_db_qa_query
    r = handle_db_qa_query(
        message="what is my email", intent="user_field",
        params={"target_type": "self", "field": "email"},
        user_id=ADMIN_LOGIN, role_id="101", beautify=False, login_id=ADMIN_LOGIN,
    )
    assert r["db_found"] is True
    assert r["result_type"] == "db_qa_result"


@_need_5_5
def test_handle_db_qa_query_new_taxonomy_denies_non_admin():
    from backend.agent.db_qa_router import handle_db_qa_query
    r = handle_db_qa_query(
        message="list all users", intent="user_list",
        params={"target_type": "system_wide"},
        user_id=NON_ADMIN_LOGIN, role_id="104", beautify=False, login_id=NON_ADMIN_LOGIN,
    )
    assert r["db_found"] is False
    assert "admin" in r["response_text"].lower() or "self-service" in r["response_text"].lower() \
        or "your own" in r["response_text"].lower()


@_need_5_5
def test_handle_db_qa_query_legacy_path_still_works():
    from backend.agent.db_qa_router import handle_db_qa_query
    r = handle_db_qa_query(
        message="what is my department", intent="db_my_department",
        params={}, user_id=ADMIN_LOGIN, role_id="101", beautify=False, login_id=ADMIN_LOGIN,
    )
    assert r["db_found"] is True
    assert r["result_type"] == "db_qa_result"


@_need_5_5
def test_decide_end_to_end_new_taxonomy():
    import asyncio
    from backend.agent import decide

    async def run():
        return await decide(
            "what is my email", session_id="pytest-session-a",
            login_id=ADMIN_LOGIN, user_id=ADMIN_LOGIN, role_id="101",
        )

    result = asyncio.run(run())
    assert result.get("intent") == "user_field"


@_need_5_5
def test_decide_end_to_end_denies_non_admin():
    import asyncio
    from backend.agent import decide

    async def run():
        return await decide(
            "list all users", session_id="pytest-session-b",
            login_id=NON_ADMIN_LOGIN, user_id=NON_ADMIN_LOGIN, role_id="104",
        )

    result = asyncio.run(run())
    response_text = (result.get("response_text") or "").lower()
    assert "admin" in response_text or "your own" in response_text
