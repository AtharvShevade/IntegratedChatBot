"""L-17: backend/tools/report_lookup.py's _get_download_info() previously
included the absolute server filesystem path under "error_file_path" in the
dict it returns -- a dict that (in several callers) becomes part of the
client-facing status response. The path is still resolved and used
server-side (via the new _resolve_error_file_path() helper, shared by the
download-link builder and the two internal consumers that need to actually
read the file), but it is no longer present in any dict handed back to a
caller outside this module.

This mirrors the already-existing, already-correct pattern in
count_errors_by_category() (its own L-17 fix): expose only a bare filename
(or, here, nothing at all) to the client; the safe download_url (built from
form_id + bare filename, verified server-side via build_error_file_path())
remains the only way to reach the file.
"""
from __future__ import annotations

import os

import pytest

import backend.tools.report_lookup as rl


def _row(error_doc_attr: str, filename: str, dtc: str = "01-Jan-2026 10:00:00 AM") -> dict:
    attrs = rl._instance_log_attrs()
    return {
        attrs["error_doc"]: filename,
        "DTC": dtc,
        "ReportingDate": "31-Dec-2025",
    }


class TestGetDownloadInfoNoLongerExposesThePath:
    def test_error_dict_has_no_error_file_path_key(self, monkeypatch, tmp_path):
        monkeypatch.setattr(rl, "build_error_file_path", lambda form_id, filename: str(tmp_path / filename))
        monkeypatch.setattr(rl, "file_exists", lambda path: True)

        row = _row(rl._instance_log_attrs()["error_doc"], "errors.xml")
        # Force the failed-status branch so _try_error() runs.
        monkeypatch.setattr(rl, "_safe_status", lambda r: next(iter(rl._FAILED_STATUSES)))

        result = rl._get_download_info(row, "1234")
        assert "error_file_path" not in result
        assert "download_url" in result
        assert "filename=errors.xml" in result["download_url"]

    def test_no_other_absolute_path_field_is_introduced_under_another_name(self, monkeypatch, tmp_path):
        monkeypatch.setattr(rl, "build_error_file_path", lambda form_id, filename: str(tmp_path / filename))
        monkeypatch.setattr(rl, "file_exists", lambda path: True)
        monkeypatch.setattr(rl, "_safe_status", lambda r: next(iter(rl._FAILED_STATUSES)))

        row = _row(rl._instance_log_attrs()["error_doc"], "errors.xml")
        result = rl._get_download_info(row, "1234")
        # No value anywhere in the dict should be an absolute filesystem path.
        for key, value in result.items():
            if isinstance(value, str):
                assert not os.path.isabs(value), f"field {key!r} leaks an absolute path: {value!r}"


class TestInternalProcessingStillWorks:
    """The path is still resolved and used server-side -- only removed from
    the client-facing dict."""

    def test_resolve_error_file_path_still_builds_the_real_path(self, monkeypatch, tmp_path):
        monkeypatch.setattr(rl, "build_error_file_path", lambda form_id, filename: str(tmp_path / form_id / filename))
        row = _row(rl._instance_log_attrs()["error_doc"], "errors.xml")
        path = rl._resolve_error_file_path(row, "1234")
        assert path == str(tmp_path / "1234" / "errors.xml")

    def test_resolve_error_file_path_empty_when_row_names_no_file(self):
        row = {"DTC": "01-Jan-2026"}
        assert rl._resolve_error_file_path(row, "1234") == ""

    def test_get_error_counts_still_works_via_row_not_dl(self, monkeypatch, tmp_path):
        error_file = tmp_path / "errors.xml"
        error_file.write_text(
            '<?xml version="1.0"?><Errors><ErrorMessage>bad thing</ErrorMessage></Errors>',
            encoding="utf-8",
        )
        row = _row(rl._instance_log_attrs()["error_doc"], "errors.xml")
        monkeypatch.setattr(rl, "build_error_file_path", lambda form_id, filename: str(error_file))
        monkeypatch.setattr(
            rl, "count_errors_by_category",
            lambda path, form_id="": {"filename": os.path.basename(path), "xbrl_schema": 1},
        )
        code = next(iter(rl._FAILED_STATUSES))
        counts = rl._get_error_counts(code, row, form_id="1234")
        assert counts == {"filename": "errors.xml", "xbrl_schema": 1}
        assert "error_file_path" not in counts

    def test_get_error_counts_returns_empty_for_non_failed_status(self):
        code = next(iter(rl._SUCCESS_STATUSES))
        row = _row(rl._instance_log_attrs()["error_doc"], "errors.xml")
        assert rl._get_error_counts(code, row, form_id="1234") == {}

    def test_enrich_with_error_messages_still_works_via_row(self, monkeypatch, tmp_path):
        error_file = tmp_path / "errors.xml"
        error_file.write_text(
            '<?xml version="1.0"?><Errors><ErrorMessage>bad thing</ErrorMessage></Errors>',
            encoding="utf-8",
        )
        row = _row(rl._instance_log_attrs()["error_doc"], "errors.xml")
        monkeypatch.setattr(rl, "build_error_file_path", lambda form_id, filename: str(error_file))
        code = next(iter(rl._FAILED_STATUSES))
        messages = rl._enrich_with_error_messages(code, row, form_id="1234")
        assert "bad thing" in messages


class TestEndToEndResponseShapes:
    """The 5 real status-result builders that call _get_error_counts must
    never surface an absolute path anywhere in their returned dict."""

    @staticmethod
    def _assert_no_absolute_paths(d: dict):
        for key, value in d.items():
            if isinstance(value, str):
                assert not os.path.isabs(value), f"field {key!r} leaks an absolute path: {value!r}"
            elif isinstance(value, dict):
                TestEndToEndResponseShapes._assert_no_absolute_paths(value)

    def test_build_status_result_from_row_has_no_absolute_paths(self, monkeypatch, tmp_path):
        monkeypatch.setattr(rl, "build_error_file_path", lambda form_id, filename: str(tmp_path / filename))
        monkeypatch.setattr(rl, "build_render_file_path", lambda form_id, filename: str(tmp_path / filename))
        monkeypatch.setattr(rl, "file_exists", lambda path: False)
        monkeypatch.setattr(rl, "get_available_instances", lambda form_id: [])
        monkeypatch.setattr(rl, "_get_return_id_for_form", lambda form_id: "R1")
        monkeypatch.setattr(rl, "_is_4000_series", lambda form_id: False)

        row = _row(rl._instance_log_attrs()["error_doc"], "errors.xml")
        result = rl._build_status_result_from_row("1234", "CIMS_RAQ", row)
        self._assert_no_absolute_paths(result)
