#!/usr/bin/env python3
"""Regression tests for backend report lookup matching behavior."""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.agent import decide
from backend.tools.report_lookup import find_matching_reports


def _names(q):
    return [r.get("Name") for r in find_matching_reports(q)]


def test_crilc_matches_exact_only():
    assert _names("status of crilc") == ["CRILC"]
    assert _names("crilc") == ["CRILC"]


def test_cims_prefix_matches():
    names = _names("status of cims")
    assert any(name.startswith("CIMS_") for name in names)
    assert "CIMS_ROR" in names
    assert any(name.startswith("CIMS_RAQ") for name in names)


def test_ror_matches_ror():
    assert _names("ror") == ["ROR"]


def test_raq_matches_raq():
    assert "RAQ(Quarterly)" in _names("raq")


def test_single_char_query_no_match():
    assert _names("c") == []
    assert _names("r") == []
    assert _names("a") == []


def test_cril_does_not_return_cims_lr():
    names = _names("cril")
    assert "CIMS_LR" not in names


def test_unknown_status_query_with_no_report_match():
    async def _run_query():
        with patch(
            "backend.agent.extract_intent_and_entities",
            AsyncMock(return_value={"intent": "unknown", "search_terms": "atharv", "reporting_date": None}),
        ):
            with patch(
                "backend.agent._get_status_fast_with_bg_job",
                side_effect=AssertionError("Raw query fallback should not be called"),
            ):
                return await decide(
                    "what is the status of atharv",
                    session_id=None,
                    asp_session=None,
                    login_id=None,
                    user_id=None,
                    role_id=None,
                    conversation_history=[],
                )

    result = asyncio.run(_run_query())
    assert result["result_type"] == "error"
    assert result["intent"] == "get_status"
    assert result["report_name"] is None
    assert "I couldn't find any report matching 'atharv'." in result["response_text"]
    assert "Please check the report name and try again." in result["response_text"]


if __name__ == "__main__":
    failures = 0
    for fn in [
        test_crilc_matches_exact_only,
        test_cims_prefix_matches,
        test_ror_matches_ror,
        test_raq_matches_raq,
        test_single_char_query_no_match,
        test_cril_does_not_return_cims_lr,
        test_unknown_status_query_with_no_report_match,
    ]:
        try:
            fn()
            print(f"✅ {fn.__name__}")
        except AssertionError as exc:
            failures += 1
            print(f"❌ {fn.__name__}: {exc}")
    if failures:
        raise SystemExit(1)
