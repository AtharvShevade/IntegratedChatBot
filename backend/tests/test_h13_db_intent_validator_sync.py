"""H-13: the LLM intent-extraction prompt (backend/services/llm_service.py)
told the model it could return 9 ``db_*`` intents, but the post-call
validator in ``backend/llm_extractor.py`` hard-coded its OWN, separate
6-value set with no ``db_*`` names at all. Any DB Q&A question the LLM
correctly classified was silently reset to "unknown" before
``agent/router.py``'s ``if intent.startswith("db_")`` branch ever got a
chance to run — that whole branch was dead code.

The fix: ``VALID_INTENTS`` in ``llm_service.py`` is extracted directly from
the same prompt text shown to the LLM (one source, not two independently
maintained lists), and ``llm_extractor.py`` imports it instead of hard-coding
its own set. Additionally, since the entity fields (target_user,
target_department, query_type) the db_* handlers need were never actually
populated by the old code (the final return dict simply didn't include
them), deterministic regex-based extraction for those fields was added
(mirroring the existing STEP-2 regex classifier's approach — the LLM is
still only ever trusted for intent, never entity values).

These tests mock out only the network call (``extract_intent_entities_llm``)
so they never hit a real Ollama endpoint. Async calls are driven with
``asyncio.run()`` from plain sync test functions, matching this codebase's
existing convention (no pytest-asyncio plugin is installed here).
"""
from __future__ import annotations

import asyncio

import pytest

from backend.services.llm_service import VALID_INTENTS
import backend.llm_extractor as llm_extractor


def _stub(intent: str):
    async def _fake(*args, **kwargs):
        return {"intent": intent}
    return _fake


def _extract(question: str) -> dict:
    return asyncio.run(llm_extractor.extract_intent_and_entities(question))


class TestSharedSourceOfTruth:
    def test_valid_intents_includes_every_db_qa_intent_from_the_prompt(self):
        expected_db_intents = {
            "db_my_profile", "db_my_department", "db_my_role", "db_my_permissions",
            "db_list_users", "db_list_departments", "db_list_roles",
            "db_user_info", "db_department_info",
        }
        assert expected_db_intents.issubset(VALID_INTENTS)

    def test_valid_intents_includes_every_report_intent(self):
        expected_report_intents = {
            "get_status", "generate_instance", "schedule_report",
            "compare_reports", "query_database",
        }
        assert expected_report_intents.issubset(VALID_INTENTS)

    def test_valid_intents_includes_unknown(self):
        assert "unknown" in VALID_INTENTS

    def test_exactly_fifteen_intents_total(self):
        assert len(VALID_INTENTS) == 15  # 5 report + 9 db_qa + 1 unknown


@pytest.mark.parametrize("intent", [
    "db_my_profile", "db_my_department", "db_my_role", "db_my_permissions",
    "db_list_users", "db_list_departments", "db_list_roles",
    "db_user_info", "db_department_info",
])
class TestEveryDbQaIntentIsAccepted:
    def test_db_qa_intent_survives_validation(self, monkeypatch, intent):
        monkeypatch.setattr(
            "backend.services.llm_service.extract_intent_entities_llm", _stub(intent)
        )
        result = _extract("some question")
        assert result["intent"] == intent, (
            f"{intent!r} was rejected by the validator -- this is exactly the H-13 bug"
        )


@pytest.mark.parametrize("intent", [
    "get_status", "generate_instance", "schedule_report",
    "compare_reports", "query_database",
])
class TestEveryReportIntentStillAccepted:
    def test_report_intent_still_accepted(self, monkeypatch, intent):
        monkeypatch.setattr(
            "backend.services.llm_service.extract_intent_entities_llm", _stub(intent)
        )
        result = _extract("some question")
        assert result["intent"] == intent


class TestInvalidIntentsStillRejected:
    def test_hallucinated_intent_falls_back_to_unknown(self, monkeypatch):
        monkeypatch.setattr(
            "backend.services.llm_service.extract_intent_entities_llm",
            _stub("delete_all_users"),
        )
        result = _extract("some question")
        assert result["intent"] == "unknown"

    def test_empty_string_intent_falls_back_to_unknown(self, monkeypatch):
        monkeypatch.setattr(
            "backend.services.llm_service.extract_intent_entities_llm", _stub("")
        )
        result = _extract("some question")
        assert result["intent"] == "unknown"

    def test_missing_intent_key_falls_back_to_unknown(self, monkeypatch):
        async def _fake(*a, **kw):
            return {}
        monkeypatch.setattr(
            "backend.services.llm_service.extract_intent_entities_llm", _fake
        )
        result = _extract("some question")
        assert result["intent"] == "unknown"


class TestDbQaEntityExtraction:
    def test_db_user_info_extracts_target_user(self, monkeypatch):
        monkeypatch.setattr(
            "backend.services.llm_service.extract_intent_entities_llm", _stub("db_user_info")
        )
        result = _extract("tell me about user alice")
        assert result["intent"] == "db_user_info"
        assert result["target_user"] == "alice"

    def test_db_department_info_extracts_target_department(self, monkeypatch):
        monkeypatch.setattr(
            "backend.services.llm_service.extract_intent_entities_llm",
            _stub("db_department_info"),
        )
        result = _extract("show department finance")
        assert result["intent"] == "db_department_info"
        assert result["target_department"] == "finance"

    def test_db_list_users_defaults_query_type_all(self, monkeypatch):
        monkeypatch.setattr(
            "backend.services.llm_service.extract_intent_entities_llm", _stub("db_list_users")
        )
        result = _extract("who are all the users")
        assert result["query_type"] == "all"

    def test_db_list_users_detects_active(self, monkeypatch):
        monkeypatch.setattr(
            "backend.services.llm_service.extract_intent_entities_llm", _stub("db_list_users")
        )
        result = _extract("who are the active users")
        assert result["query_type"] == "active"

    def test_db_list_users_detects_inactive(self, monkeypatch):
        monkeypatch.setattr(
            "backend.services.llm_service.extract_intent_entities_llm", _stub("db_list_users")
        )
        result = _extract("show all inactive users")
        assert result["query_type"] == "inactive"

    def test_self_service_intents_need_no_entities(self, monkeypatch):
        monkeypatch.setattr(
            "backend.services.llm_service.extract_intent_entities_llm", _stub("db_my_profile")
        )
        result = _extract("who am i")
        assert result["intent"] == "db_my_profile"
        assert result["target_user"] is None
        assert result["target_department"] is None


class TestRouterDispatchesDbQaIntentsEndToEnd:
    """Confirms the previously-dead router.py branch actually fires now."""

    def test_router_routes_db_intent_to_db_qa_handler(self, monkeypatch):
        import backend.agent.router as router_module

        monkeypatch.setenv("REQUIRE_AUTH", "false")

        async def _fake_extract(*a, **kw):
            return {
                "intent": "db_my_profile", "search_terms": None, "reporting_date": None,
                "schedule_date": None, "schedule_time": None, "scheduled_datetime": None,
                "target_user": None, "target_department": None, "query_type": None,
            }
        monkeypatch.setattr(router_module, "extract_intent_and_entities", _fake_extract)

        called = {}

        def _fake_handle_db_qa_query(**kwargs):
            called.update(kwargs)
            return {"result": "ok", "db_found": True, "result_type": "db_qa_result"}

        monkeypatch.setattr(
            "backend.agent.db_qa_router.handle_db_qa_query", _fake_handle_db_qa_query
        )

        asyncio.run(router_module.decide(
            "some totally novel phrasing the regex classifiers all miss",
            session_id="s1", login_id=None,
        ))
        assert called.get("intent") == "db_my_profile", (
            "router.py's db_* branch must actually be reached once the intent "
            "survives validation -- this is the end-to-end proof H-13 is fixed"
        )
