"""Regression test for a production crash: an Ollama transport/HTTP
failure (connection refused, timeout, or an upstream proxy returning
502/503/etc.) during LLM intent disambiguation propagated all the way up
through classify_new_with_semantic_tiers() -> check_new_taxonomy_intent_full()
-> decide() -> the /chat FastAPI endpoint, crashing the entire request with
an unhandled 500 instead of degrading gracefully.

backend.services.llm_service.disambiguate_intent()'s own documented
contract is: return None when the model declines or answers unexpectedly,
and callers should "treat None the same as 'still no confident match' and
fall through to the next tier." A transport/HTTP failure is a stronger
version of the same "no confident answer" case and must degrade the same
way — classify_new_with_semantic_tiers() is deep inside decide()'s STEP 2,
with STEP 3 (SQL) and STEP 4 (LLM fallback) still available above it, so
there was never a reason for this specific failure to be fatal.

Fixed by wrapping the disambiguate_intent() call in
classify_new_with_semantic_tiers() with a try/except that logs and treats
any exception as a declined answer (chosen_value = None).
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.db_qa import new_intent_classifier as nic
from backend.db_qa.intents.taxonomy import Intent

_FAKE_AMBIGUOUS_RESULT = {
    "tier": "embedding_ambiguous",
    "candidates": [
        (Intent.USER_FIELD, 0.83, "what is my email"),
        (Intent.USER_PROFILE, 0.82, "my profile"),
    ],
}


def _http_error(status_code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("POST", "http://example.invalid/api/chat")
    response = httpx.Response(status_code, request=request)
    return httpx.HTTPStatusError(f"{status_code} error", request=request, response=response)


class TestLLMDisambiguationFailureDegradesGracefully:
    @pytest.mark.parametrize("exc", [
        _http_error(502),
        _http_error(503),
        httpx.ConnectError("connection refused"),
        httpx.TimeoutException("timed out"),
    ])
    def test_transport_failure_does_not_raise(self, exc):
        async def _run():
            with patch(
                "backend.db_qa.intents.embedding_index.classify_by_embedding",
                return_value=_FAKE_AMBIGUOUS_RESULT,
            ), patch(
                "backend.services.llm_service.disambiguate_intent",
                AsyncMock(side_effect=exc),
            ):
                return await nic.classify_new_with_semantic_tiers(
                    "some ambiguous question with enough words in it"
                )

        intent, params, target_type, tier = asyncio.run(_run())
        # Must degrade to "no confident match", never propagate the exception.
        assert intent is None
        assert params == {}
        assert target_type is None
        assert tier == "llm_disambiguation"

    def test_declined_answer_still_behaves_as_before(self):
        # Sanity check that the try/except doesn't change the pre-existing
        # "model declined" behavior (returns None without raising) — only
        # adds a NEW path for actual exceptions.
        async def _run():
            with patch(
                "backend.db_qa.intents.embedding_index.classify_by_embedding",
                return_value=_FAKE_AMBIGUOUS_RESULT,
            ), patch(
                "backend.services.llm_service.disambiguate_intent",
                AsyncMock(return_value=None),
            ):
                return await nic.classify_new_with_semantic_tiers(
                    "some ambiguous question with enough words in it"
                )

        intent, params, target_type, tier = asyncio.run(_run())
        assert intent is None
        assert tier == "llm_disambiguation"

    def test_successful_disambiguation_still_resolves_intent(self):
        async def _run():
            with patch(
                "backend.db_qa.intents.embedding_index.classify_by_embedding",
                return_value=_FAKE_AMBIGUOUS_RESULT,
            ), patch(
                "backend.services.llm_service.disambiguate_intent",
                AsyncMock(return_value="user_field"),
            ):
                return await nic.classify_new_with_semantic_tiers(
                    "some ambiguous question with enough words in it"
                )

        intent, params, target_type, tier = asyncio.run(_run())
        assert intent == Intent.USER_FIELD
        assert tier == "llm_disambiguation"
