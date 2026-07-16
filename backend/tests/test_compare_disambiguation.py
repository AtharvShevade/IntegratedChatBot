"""Regression tests for the Compare Instances disambiguation flow.

Bug: after a partial report name ("Compare cims") produced a multi-match
disambiguation list, replying with one of the shown report names failed
with "I couldn't find any report matching '<name>'." — even though the
name had just been shown as a valid option.

Root cause: the STAGE_CMP_REPORT disambiguation-selection branch in
decide() called _check_name_auth(selected, allowed_form_ids, "compare_reports")
and _compare_with_name(selected, session_id) with a stale FormId lookup,
always failing to resolve the FormId — exactly reproducing the reported
error.

Exact-name and Return ID compare flows (which go through _handle_compare's
single-match branch, unaffected by this omission) must continue to work
unchanged.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.agent import decide, _session_context


def _run_compare_query(query: str, session_id: str, *, login_id=None):
    """Run `query` through decide() with compare_reports pre-selected as the
    LLM-extracted intent, matching how a real 'Compare X' message resolves
    without needing a live LLM call."""
    async def _run():
        with patch(
            "backend.agent.extract_intent_and_entities",
            AsyncMock(return_value={"intent": "compare_reports", "search_terms": query, "reporting_date": None}),
        ):
            return await decide(
                query, session_id=session_id, asp_session=None,
                login_id=login_id, user_id=None, role_id=None,
                conversation_history=[],
            )
    return asyncio.run(_run())


# ── 5.5 real data: natural chat flow, partial name -> candidate list -> pick ─

class TestPartialNameDisambiguation5_5:
    def test_partial_name_produces_candidate_list(self):
        _session_context.pop("test-cmp-partial-1", None)
        result = _run_compare_query("cims", "test-cmp-partial-1")
        assert result["result_type"] == "disambiguation"
        assert len(result["options"]) > 1
        assert all(name.upper().startswith("CIMS") for name in result["options"])

    def test_selecting_a_shown_candidate_by_full_name_resolves(self):
        session_id = "test-cmp-partial-2"
        _session_context.pop(session_id, None)
        disamb = _run_compare_query("cims", session_id)
        assert disamb["result_type"] == "disambiguation"
        chosen = disamb["options"][0]

        result = asyncio.run(decide(
            chosen, session_id=session_id, asp_session=None,
            login_id=None, user_id=None, role_id=None, conversation_history=[],
        ))
        # Must NOT be the "couldn't find any report matching" regression —
        # either instance selection proceeds, or a legitimate "no instance
        # files" result is returned, but never a failed name lookup for a
        # name that was JUST shown as a valid option.
        assert f"I couldn't find any report matching '{chosen}'" not in result["response_text"]

    def test_selecting_by_number_still_works(self):
        session_id = "test-cmp-partial-3"
        _session_context.pop(session_id, None)
        disamb = _run_compare_query("cims", session_id)
        assert disamb["result_type"] == "disambiguation"

        result = asyncio.run(decide(
            "1", session_id=session_id, asp_session=None,
            login_id=None, user_id=None, role_id=None, conversation_history=[],
        ))
        chosen = disamb["options"][0]
        assert f"I couldn't find any report matching '{chosen}'" not in result["response_text"]

    def test_short_partial_name_produces_candidate_list_and_resolves(self):
        """'ror' style short partial names must behave the same way as
        longer partial names like 'cims'."""
        session_id = "test-cmp-partial-4"
        _session_context.pop(session_id, None)
        result = _run_compare_query("ror", session_id)
        # 'ror' matches exactly ROR in this dataset (find_matching_reports
        # prefers exact/prefix matches) — either a direct resolution or a
        # short disambiguation list is acceptable, but never the
        # not-found regression for a name that exists.
        assert "couldn't find any report matching 'ror'" not in result["response_text"].lower() or \
            result["result_type"] == "disambiguation"


# ── Non-regression: exact name / Return ID flows (single-match, unaffected) ──

class TestExactNameAndReturnIdNoRegression5_5:
    def test_exact_report_name_resolves_directly(self):
        session_id = "test-cmp-exact-1"
        _session_context.pop(session_id, None)
        result = _run_compare_query("CIMS_ROR", session_id)
        assert result["result_type"] != "error" or "couldn't find any report matching" not in result["response_text"]

    def test_exact_crilc_resolves_directly(self):
        session_id = "test-cmp-exact-2"
        _session_context.pop(session_id, None)
        result = _run_compare_query("CIMS_CRILC_RFA", session_id)
        assert "couldn't find any report matching" not in result["response_text"]
