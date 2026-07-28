"""Tests for the Guided Status workflow's new Request ID (Instance ID)
support — added alongside the existing report name / ReturnId / short name
lookup, which must remain completely unaffected.

Covers:
  - a complete, valid Request ID resolves via EXACT match and continues the
    normal status workflow
  - incomplete/malformed ID-shaped input is rejected outright (never
    partial/fuzzy/prefix matched, never falls through to report-name search)
  - a well-shaped but non-existent Request ID is also rejected (exact match
    only — "looks right" is not enough)
  - ordinary report name / ReturnId / short name inputs are completely
    unaffected (still reach the existing get_report_status fuzzy path)
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import backend.guided as guided


def _run(coro):
    return asyncio.run(coro)


class TestLooksLikeRequestIdAttempt:
    def test_full_32_hex_id_is_an_attempt(self):
        assert guided._looks_like_request_id_attempt("d06f09e00a0044118e7dcd2e1d8a93f3") is True

    def test_incomplete_23_char_fragment_is_an_attempt(self):
        assert guided._looks_like_request_id_attempt("d06f09e00a0044118e7dcd2") is True

    def test_short_6_char_fragment_is_an_attempt(self):
        assert guided._looks_like_request_id_attempt("d06f09") is True

    def test_5_char_fragment_is_not_an_attempt(self):
        """Below the minimum length — treated as ordinary input, not an ID
        fragment (avoids misclassifying very short tokens)."""
        assert guided._looks_like_request_id_attempt("d06f0") is False

    @pytest.mark.parametrize("name", ["CIMS_ROR", "R149", "RAQ", "CIMS_RAQ(Annually)"])
    def test_real_report_names_are_never_treated_as_id_attempts(self, name):
        assert guided._looks_like_request_id_attempt(name) is False

    @pytest.mark.parametrize("form_id", ["4046", "2065", "107"])
    def test_short_numeric_form_ids_are_never_treated_as_id_attempts(self, form_id):
        assert guided._looks_like_request_id_attempt(form_id) is False


class TestGuidedStatusRequestIdLookup:
    SESSION = "test-session-request-id"

    def setup_method(self):
        guided._guided_sessions[self.SESSION] = {"stage": guided.STAGE_STATUS_REPORT}

    def teardown_method(self):
        guided._guided_sessions.pop(self.SESSION, None)

    def test_valid_complete_id_resolves_via_exact_match(self, monkeypatch):
        valid_id = "d06f09e00a0044118e7dcd2e1d8a93f3"
        seen = {}

        def _fake_lookup(instance_id):
            seen["called_with"] = instance_id
            return {"type": "final", "report_name": "CIMS_MPD03", "status": "Passed",
                    "reporting_date": "31-Mar-2026"}

        monkeypatch.setattr(
            "backend.tools.report_lookup.get_report_status_by_id_fast", _fake_lookup
        )
        # get_report_status must NEVER be called for a recognised ID attempt.
        def _should_not_be_called(msg):
            raise AssertionError("get_report_status must not be called for a Request ID input")
        monkeypatch.setattr("backend.tools.report_lookup.get_report_status", _should_not_be_called)

        result = _run(guided.guided_step(valid_id, session_id=self.SESSION, asp_session=None))

        assert seen["called_with"] == valid_id
        assert result["result_type"] == "final"

    def test_incomplete_fragment_rejected_without_fallback_to_name_search(self, monkeypatch):
        fragment = "d06f09e00a0044118e7dcd2"  # 23 chars — hex-looking but not a valid shape

        def _should_not_be_called(*args, **kwargs):
            raise AssertionError("no lookup should be attempted for an incomplete ID fragment")

        monkeypatch.setattr("backend.tools.report_lookup.get_report_status_by_id_fast", _should_not_be_called)
        monkeypatch.setattr("backend.tools.report_lookup.get_report_status", _should_not_be_called)

        result = _run(guided.guided_step(fragment, session_id=self.SESSION, asp_session=None))

        assert result["result_type"] == "error"
        assert "no matching request id" in result["response_text"].lower()
        assert "complete request id" in result["response_text"].lower()

    def test_short_fragment_rejected_without_fallback(self, monkeypatch):
        fragment = "d06f09"

        def _should_not_be_called(*args, **kwargs):
            raise AssertionError("no lookup should be attempted for a short ID fragment")

        monkeypatch.setattr("backend.tools.report_lookup.get_report_status_by_id_fast", _should_not_be_called)
        monkeypatch.setattr("backend.tools.report_lookup.get_report_status", _should_not_be_called)

        result = _run(guided.guided_step(fragment, session_id=self.SESSION, asp_session=None))

        assert result["result_type"] == "error"
        assert "no matching request id" in result["response_text"].lower()

    def test_well_shaped_but_nonexistent_id_is_rejected_exact_match_only(self, monkeypatch):
        """A syntactically valid 32-hex/UUID string that simply doesn't
        exist must be rejected — "looks right" never substitutes for an
        actual exact match."""
        valid_shape_but_missing = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

        monkeypatch.setattr(
            "backend.tools.report_lookup.get_report_status_by_id_fast",
            lambda instance_id: {"type": "error", "message": f"Submission '{instance_id}' not found."},
        )

        result = _run(guided.guided_step(valid_shape_but_missing, session_id=self.SESSION, asp_session=None))

        assert result["result_type"] == "error"
        assert "no matching request id" in result["response_text"].lower()

    def test_ordinary_report_name_input_unaffected(self, monkeypatch):
        """The existing report name / ReturnId / short name path must be
        completely untouched — same function, same call, for non-ID input."""
        seen = {}

        def _fake_get_report_status(name):
            seen["called_with"] = name
            return {"type": "final", "report_name": "CIMS_ROR", "status": "Passed",
                    "reporting_date": "31-Mar-2026"}

        monkeypatch.setattr("backend.tools.report_lookup.get_report_status", _fake_get_report_status)

        result = _run(guided.guided_step("CIMS_ROR", session_id=self.SESSION, asp_session=None))

        assert seen["called_with"] == "CIMS_ROR"
        assert result["result_type"] == "final"

    def test_return_id_short_name_input_unaffected(self, monkeypatch):
        seen = {}

        def _fake_get_report_status(name):
            seen["called_with"] = name
            return {"type": "error", "message": f"No matching reports found for '{name}'."}

        monkeypatch.setattr("backend.tools.report_lookup.get_report_status", _fake_get_report_status)

        result = _run(guided.guided_step("RAQ", session_id=self.SESSION, asp_session=None))

        assert seen["called_with"] == "RAQ"
        assert result["result_type"] == "error"
        assert "no matching request id" not in result["response_text"].lower()
