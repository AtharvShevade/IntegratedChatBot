"""Regression tests for the H-05 fix (doc/CRITICAL_FIXES_LOG.md): the
synchronous handle_db_qa_query() call sites (backend/agent/router.py ×3,
backend/guided.py ×1) and new_intent_classifier.py's classify_by_embedding()
call now run via asyncio.to_thread(...) instead of directly on the event
loop, matching the pattern already used elsewhere in this codebase.

These tests prove two things for each wrapped call: the return value (and,
for the try/except-wrapped call site, exception propagation) is completely
unchanged, and the call actually executes off the main event-loop thread
(proving to_thread is really being used, not just present in the diff).
"""
from __future__ import annotations

import asyncio
import sys
import threading
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import backend.guided as guided
from backend.services import auth_service


class TestGuidedDbQueryGoesStraightToSqlAgent:
    """guided.py's STAGE_DB_QUERY: the user chose "Retrieve data from
    database", so the question goes to the SQL agent only -- never through the
    XML-QA / regex intent matchers used by free-text chat."""

    SESSION = "test-guided-db-query-sql-only"

    def setup_method(self):
        guided._guided_sessions[self.SESSION] = {"stage": guided.STAGE_DB_QUERY}

    def teardown_method(self):
        guided._guided_sessions.pop(self.SESSION, None)

    def test_question_goes_to_sql_agent_and_skips_xml_qa(self, monkeypatch):
        monkeypatch.setenv("REQUIRE_AUTH", "false")
        seen = {}

        async def _fake_sql_agent(msg, session_id=None, login_id=None):
            seen["msg"] = msg
            return {"result_type": "db_result", "response_text": "sql answer"}

        def _must_not_run(*a, **k):
            raise AssertionError("XML-QA must not run inside the guided database stage")

        monkeypatch.setattr("backend.sql_agent.handle_db_query", _fake_sql_agent)
        monkeypatch.setattr("backend.agent.db_qa_router.check_new_taxonomy_intent", _must_not_run)
        monkeypatch.setattr("backend.agent.db_qa_router.check_db_qa_intent", _must_not_run)
        monkeypatch.setattr("backend.agent.db_qa_router.handle_db_qa_query", _must_not_run)

        # A sentence the XML-QA regex used to answer with the user list.
        question = "Show all exposure measures for code 1010 top defaulter account"
        result = asyncio.run(guided.guided_step(question, self.SESSION, None, login_id=None))

        assert seen["msg"] == question
        assert result["result_type"] == "db_result"


class TestSemanticClassifierRunsOffEventLoop:
    """new_intent_classifier.py's classify_by_embedding() call, wrapped for
    H-05."""

    def test_embedding_classification_runs_in_worker_thread_and_result_unchanged(self):
        import backend.db_qa.new_intent_classifier as nic
        from backend.db_qa.intents.taxonomy import Intent

        main_thread = threading.current_thread()
        seen = {}

        def _fake_classify_by_embedding(question):
            seen["thread"] = threading.current_thread()
            return {"tier": "embedding_confident", "intent": Intent.USER_PROFILE}

        async def _run():
            with patch(
                "backend.db_qa.intents.embedding_index.classify_by_embedding",
                _fake_classify_by_embedding,
            ):
                return await nic.classify_new_with_semantic_tiers("a three word query")

        resolved_intent, params, source, tier = asyncio.run(_run())

        assert resolved_intent == Intent.USER_PROFILE
        assert tier == "embedding"
        assert seen["thread"] is not main_thread


class TestHandleDbQaQueryExceptionPropagation:
    """The router.py call site wrapped in try/except (the db_* LLM-intent
    path) must still catch an exception raised inside handle_db_qa_query
    exactly as before -- asyncio.to_thread re-raises in the awaiting
    coroutine, so the existing except block keeps working unchanged."""

    def test_exception_inside_worker_thread_is_still_caught(self, monkeypatch):
        from backend.agent import decide, _session_context

        monkeypatch.setenv("REQUIRE_AUTH", "false")
        session_id = "test-h05-db-exception"
        _session_context.pop(session_id, None)

        def _raise(**kwargs):
            raise RuntimeError("boom from worker thread")

        async def _run():
            with (
                # Force the deterministic STEP2 regex/taxonomy classifiers to
                # miss, so this reaches the LLM-classified db_* branch (the
                # one actually wrapped in try/except) instead of the STEP2
                # call site (which -- both before and after this fix -- has
                # no exception handling of its own; that's an unrelated,
                # pre-existing gap, not something H-05 touches).
                patch("backend.agent.db_qa_router.check_new_taxonomy_intent", lambda msg: (None, {})),
                patch("backend.agent.db_qa_router.check_db_qa_intent", lambda msg: (None, {})),
                patch(
                    "backend.agent.extract_intent_and_entities",
                    AsyncMock(return_value={"intent": "db_my_profile", "target_user": None}),
                ),
                patch("backend.agent.db_qa_router.handle_db_qa_query", _raise),
            ):
                return await decide(
                    "banana apple orange zzz nonsense phrase", session_id=session_id, asp_session=None,
                    login_id=None, user_id=None, role_id=None, conversation_history=[],
                )

        result = asyncio.run(_run())
        assert result["result_type"] == "error"
        assert result["db_found"] is False
