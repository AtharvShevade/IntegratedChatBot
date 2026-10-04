"""L-05: `backend/agent/background_jobs.py`'s `_ask_another_date()` appended
the "Failure Reason(s):" block twice on the synchronous (no background job)
path -- once unconditionally near the top of the function, and again in the
`else` branch further down using the exact same `error_messages`. Only the
duplicate append was removed; the first (and now only) append is unchanged.
"""
from __future__ import annotations

from backend.agent.background_jobs import _ask_another_date


def _base_result(**overrides):
    result = {
        "report_name": "CIMS_RAQ",
        "reporting_date": "31-Jan-2026",
        "status": "Failed",
        "error_messages": ["Formula rule X failed", "Formula rule Y failed"],
    }
    result.update(overrides)
    return result


class TestNoDuplicateFailureReasons:
    def test_synchronous_path_prints_failure_reasons_exactly_once(self):
        # No job_id in the result -> the synchronous path (previously the
        # one with the duplicate append).
        result = _base_result()
        response = _ask_another_date(result, form_id="1234", return_name="CIMS_RAQ", session_id=None)
        text = response.response_text if hasattr(response, "response_text") else response["response_text"]
        assert text.count("Failure Reason(s):") == 1, (
            f"expected exactly one 'Failure Reason(s):' block, got {text.count('Failure Reason(s):')}\n{text}"
        )

    def test_both_failure_reasons_still_present(self):
        result = _base_result()
        response = _ask_another_date(result, form_id="1234", return_name="CIMS_RAQ", session_id=None)
        text = response.response_text if hasattr(response, "response_text") else response["response_text"]
        assert "Formula rule X failed" in text
        assert "Formula rule Y failed" in text

    def test_background_job_path_still_shows_generating_marker_not_reasons(self):
        # With a job_id present, the "Generating error explanations..."
        # marker is shown instead -- this path was never duplicated, and
        # must be unaffected by the fix.
        result = _base_result(job_id="job-123", error_count=2)
        response = _ask_another_date(result, form_id="1234", return_name="CIMS_RAQ", session_id=None)
        text = response.response_text if hasattr(response, "response_text") else response["response_text"]
        assert "Generating error explanations" in text
        # The unconditional first append still fires once (error_messages
        # present in the result), so the count is still exactly 1, not 0 or 2.
        assert text.count("Failure Reason(s):") == 1

    def test_no_error_messages_produces_no_failure_reasons_block(self):
        result = _base_result(error_messages=[])
        response = _ask_another_date(result, form_id="1234", return_name="CIMS_RAQ", session_id=None)
        text = response.response_text if hasattr(response, "response_text") else response["response_text"]
        assert "Failure Reason(s):" not in text
