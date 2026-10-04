"""Regression tests for the H-10 fix (doc/CRITICAL_FIXES_LOG.md): the
form_id-in-allowed_form_ids authorization check now happens BEFORE the
background LLM error-enrichment thread is started, in every
backend/agent/background_jobs.py function that can start one -- previously
the thread always started unconditionally, and authorization was only
applied to the RESULT afterwards (router.py's _apply_auth_to_status_result),
so an unauthorized caller could still trigger the full LLM cost and have
another department's error details computed and cached.

The authorization decision itself (what allowed_form_ids means, who is
authorized) is completely unchanged -- these tests only prove WHEN the
enrichment thread starts relative to that decision.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import backend.agent.background_jobs as bg


_FAILED_RESULT = {
    "type": "final",
    "form_id": "4046",
    "status_code": 999,  # any code in _FAILED_STATUSES
    "error_count": 3,
}


@pytest.fixture(autouse=True)
def _failed_status_code(monkeypatch):
    # Make "999" a recognised failed status for these tests, independent of
    # whatever the real _FAILED_STATUSES set contains.
    monkeypatch.setattr(bg, "_FAILED_STATUSES", {999})


class TestGetStatusFastWithBgJob:
    def test_authorized_form_still_starts_enrichment_thread(self, monkeypatch):
        monkeypatch.setattr(bg, "get_report_status_fast", lambda query: dict(_FAILED_RESULT))
        monkeypatch.setattr(bg, "get_instances_by_form_id", lambda form_id: [{"DTC": "1", "Id": "row1"}])
        monkeypatch.setattr(bg, "_dtc_sort_key", lambda row: row["DTC"])
        monkeypatch.setattr(bg, "_safe_status", lambda row: 999)
        monkeypatch.setattr(bg, "_get_download_info", lambda row, form_id: {})

        started = {"called": False}
        monkeypatch.setattr(
            bg, "_start_error_enrichment_thread",
            lambda *a, **k: started.__setitem__("called", True),
        )

        result = bg._get_status_fast_with_bg_job("some query", allowed_form_ids={"4046", "9999"})

        assert started["called"] is True
        assert "job_id" in result

    def test_unauthorized_form_never_starts_enrichment_thread(self, monkeypatch):
        monkeypatch.setattr(bg, "get_report_status_fast", lambda query: dict(_FAILED_RESULT))
        monkeypatch.setattr(bg, "get_instances_by_form_id", lambda form_id: [{"DTC": "1", "Id": "row1"}])
        monkeypatch.setattr(bg, "_dtc_sort_key", lambda row: row["DTC"])
        monkeypatch.setattr(bg, "_safe_status", lambda row: 999)
        monkeypatch.setattr(bg, "_get_download_info", lambda row, form_id: {})

        started = {"called": False}
        monkeypatch.setattr(
            bg, "_start_error_enrichment_thread",
            lambda *a, **k: started.__setitem__("called", True),
        )

        # "4046" is NOT in the caller's allowed set -- e.g. a different
        # department's report.
        result = bg._get_status_fast_with_bg_job("some query", allowed_form_ids={"7777"})

        assert started["called"] is False
        assert "job_id" not in result

    def test_no_restriction_none_preserves_previous_unconditional_behavior(self, monkeypatch):
        """Regression check: allowed_form_ids=None (the default, and what
        every pre-H-10 call site effectively had) must behave exactly as
        before -- the thread always starts."""
        monkeypatch.setattr(bg, "get_report_status_fast", lambda query: dict(_FAILED_RESULT))
        monkeypatch.setattr(bg, "get_instances_by_form_id", lambda form_id: [{"DTC": "1", "Id": "row1"}])
        monkeypatch.setattr(bg, "_dtc_sort_key", lambda row: row["DTC"])
        monkeypatch.setattr(bg, "_safe_status", lambda row: 999)
        monkeypatch.setattr(bg, "_get_download_info", lambda row, form_id: {})

        started = {"called": False}
        monkeypatch.setattr(
            bg, "_start_error_enrichment_thread",
            lambda *a, **k: started.__setitem__("called", True),
        )

        result = bg._get_status_fast_with_bg_job("some query")  # no allowed_form_ids at all

        assert started["called"] is True
        assert "job_id" in result

    def test_successful_status_not_modified_by_the_auth_check(self, monkeypatch):
        """A status that ISN'T failed (no error enrichment applicable at
        all) must be completely unaffected by allowed_form_ids either way."""
        ok_result = {"type": "final", "form_id": "4046", "status_code": 1, "error_count": 0}
        monkeypatch.setattr(bg, "get_report_status_fast", lambda query: dict(ok_result))
        started = {"called": False}
        monkeypatch.setattr(
            bg, "_start_error_enrichment_thread",
            lambda *a, **k: started.__setitem__("called", True),
        )

        result = bg._get_status_fast_with_bg_job("some query", allowed_form_ids={"9999"})
        assert started["called"] is False
        assert result["status_code"] == 1


class TestGetStatusByIdFastWithBgJob:
    def test_unauthorized_form_never_starts_enrichment_thread(self, monkeypatch):
        monkeypatch.setattr(
            "backend.tools.report_lookup.get_report_status_by_id_fast",
            lambda instance_id: dict(_FAILED_RESULT),
        )
        monkeypatch.setattr(
            "backend.tools.report_lookup._parse_instances", lambda: [{"Id": "abc", "DTC": "1"}],
        )
        started = {"called": False}
        monkeypatch.setattr(
            bg, "_start_error_enrichment_thread",
            lambda *a, **k: started.__setitem__("called", True),
        )

        result = bg._get_status_by_id_fast_with_bg_job("abc", allowed_form_ids={"other-form"})

        assert started["called"] is False
        assert "job_id" not in result

    def test_authorized_form_still_starts_enrichment_thread(self, monkeypatch):
        monkeypatch.setattr(
            "backend.tools.report_lookup.get_report_status_by_id_fast",
            lambda instance_id: dict(_FAILED_RESULT),
        )
        monkeypatch.setattr(
            "backend.tools.report_lookup._parse_instances", lambda: [{"Id": "abc", "DTC": "1"}],
        )
        monkeypatch.setattr(bg, "_safe_status", lambda row: 999)
        monkeypatch.setattr(bg, "_get_download_info", lambda row, form_id: {})
        started = {"called": False}
        monkeypatch.setattr(
            bg, "_start_error_enrichment_thread",
            lambda *a, **k: started.__setitem__("called", True),
        )

        result = bg._get_status_by_id_fast_with_bg_job("abc", allowed_form_ids={"4046"})

        assert started["called"] is True
        assert "job_id" in result


class TestGetInstanceByDtcFastWithBgJob:
    def test_unauthorized_form_never_starts_enrichment_thread(self, monkeypatch):
        monkeypatch.setattr(bg, "get_instance_by_dtc_fast", lambda form_id, dtc, name: dict(_FAILED_RESULT, type="final"))
        monkeypatch.setattr(bg, "get_instances_by_form_id", lambda form_id: [{"DTC": "dtc1", "Id": "row1"}])
        started = {"called": False}
        monkeypatch.setattr(
            bg, "_start_error_enrichment_thread",
            lambda *a, **k: started.__setitem__("called", True),
        )

        result = bg._get_instance_by_dtc_fast_with_bg_job(
            "4046", "dtc1", "MY_REPORT", allowed_form_ids={"other-form"},
        )

        assert started["called"] is False
        assert "job_id" not in result

    def test_authorized_form_still_starts_enrichment_thread(self, monkeypatch):
        monkeypatch.setattr(bg, "get_instance_by_dtc_fast", lambda form_id, dtc, name: dict(_FAILED_RESULT, dtc="dtc1"))
        monkeypatch.setattr(bg, "get_instances_by_form_id", lambda form_id: [{"DTC": "dtc1", "Id": "row1"}])
        monkeypatch.setattr(bg, "_safe_status", lambda row: 999)
        monkeypatch.setattr(bg, "_get_download_info", lambda row, form_id: {})
        started = {"called": False}
        monkeypatch.setattr(
            bg, "_start_error_enrichment_thread",
            lambda *a, **k: started.__setitem__("called", True),
        )

        result = bg._get_instance_by_dtc_fast_with_bg_job(
            "4046", "dtc1", "MY_REPORT", allowed_form_ids={"4046"},
        )

        assert started["called"] is True
        assert "job_id" in result
