"""Regression tests for the H-03 fix (doc/CRITICAL_FIXES_LOG.md): object-level
authorization on /download-file, /reports, and /status-errors/{job_id}.

Before this fix, all three endpoints checked only that the request was
well-formed (numeric form_id, basename-only filename, a real job_id) --
never whether the caller's department was actually allowed to see that
specific form_id. This file locks in the fix without touching SQL Agent
behavior (H-02 was explicitly out of scope for this change; handle_db_query
is untouched).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend import main as main_module
from backend.services import auth_service


@pytest.fixture
def client():
    return TestClient(main_module.app)


@pytest.fixture(autouse=True)
def _auth_enabled(monkeypatch):
    monkeypatch.setattr(auth_service, "AUTHORIZATION_ENABLED", True)
    monkeypatch.setenv("REQUIRE_AUTH", "true")


class TestDownloadFileObjectLevelAcl:
    def _make_file(self, tmp_path, monkeypatch, form_id, filename):
        from backend import config as config_module
        base = tmp_path / "Instance"
        form_dir = base / form_id
        form_dir.mkdir(parents=True)
        (form_dir / filename).write_text("<x/>", encoding="utf-8")
        monkeypatch.setattr(config_module, "instance_base_dir", lambda: str(base))
        monkeypatch.setattr(config_module, "render_base_dir", lambda: str(base))

    def test_denied_when_form_id_not_in_allowed_set(self, client, monkeypatch, tmp_path):
        self._make_file(tmp_path, monkeypatch, "4046", "errors.xml")
        monkeypatch.setattr(auth_service, "get_allowed_form_ids", lambda login_id: {"9999"})

        resp = client.get("/download-file", params={
            "form_id": "4046", "type": "error", "filename": "errors.xml", "login_id": "someuser",
        })
        assert resp.status_code == 403

    def test_allowed_when_form_id_in_allowed_set(self, client, monkeypatch, tmp_path):
        self._make_file(tmp_path, monkeypatch, "4046", "errors.xml")
        monkeypatch.setattr(auth_service, "get_allowed_form_ids", lambda login_id: {"4046", "9999"})

        resp = client.get("/download-file", params={
            "form_id": "4046", "type": "error", "filename": "errors.xml", "login_id": "someuser",
        })
        assert resp.status_code == 200

    def test_denied_when_login_id_missing(self, client, monkeypatch, tmp_path):
        self._make_file(tmp_path, monkeypatch, "4046", "errors.xml")

        resp = client.get("/download-file", params={
            "form_id": "4046", "type": "error", "filename": "errors.xml",
        })
        assert resp.status_code == 403

    def test_denied_when_login_id_unresolvable(self, client, monkeypatch, tmp_path):
        self._make_file(tmp_path, monkeypatch, "4046", "errors.xml")
        monkeypatch.setattr(auth_service, "get_allowed_form_ids", lambda login_id: None)

        resp = client.get("/download-file", params={
            "form_id": "4046", "type": "error", "filename": "errors.xml", "login_id": "unknown",
        })
        assert resp.status_code == 403

    def test_still_allowed_in_explicit_dev_bypass(self, client, monkeypatch, tmp_path):
        self._make_file(tmp_path, monkeypatch, "4046", "errors.xml")
        monkeypatch.setenv("REQUIRE_AUTH", "false")

        resp = client.get("/download-file", params={
            "form_id": "4046", "type": "error", "filename": "errors.xml",
        })
        assert resp.status_code == 200

    def test_path_traversal_protection_unchanged(self, client, monkeypatch, tmp_path):
        """Sanity check: the pre-existing containment check (unrelated to
        H-03) must still fire regardless of the new ACL check."""
        self._make_file(tmp_path, monkeypatch, "4046", "errors.xml")
        monkeypatch.setattr(auth_service, "get_allowed_form_ids", lambda login_id: {"4046"})

        resp = client.get("/download-file", params={
            "form_id": "4046", "type": "error", "filename": "../../../../windows/win.ini",
            "login_id": "someuser",
        })
        # basename() strips the traversal to "win.ini", which then 404s
        # (not found in the form's own folder) rather than escaping -- either
        # a 403 or 404 is an acceptable "did not serve the file" outcome; a
        # 200 would not be.
        assert resp.status_code in (403, 404)


class TestReportsObjectLevelAcl:
    def test_unfiltered_when_authorization_disabled(self, client, monkeypatch):
        monkeypatch.setattr(auth_service, "AUTHORIZATION_ENABLED", False)
        monkeypatch.setattr(
            "backend.tools.report_lookup._parse_returns",
            lambda: [{"Name": "REPORT_A"}, {"Name": "REPORT_B"}],
        )
        resp = client.get("/reports", params={"login_id": "someuser"})
        assert resp.status_code == 200
        assert set(resp.json()["reports"]) == {"REPORT_A", "REPORT_B"}

    def test_filtered_to_allowed_forms_only(self, client, monkeypatch):
        monkeypatch.setattr(
            "backend.tools.report_lookup._parse_returns",
            lambda: [{"Name": "REPORT_A"}, {"Name": "REPORT_B"}],
        )
        monkeypatch.setattr(auth_service, "get_allowed_form_ids", lambda login_id: {"101"})
        monkeypatch.setattr(
            "backend.agent.auth_filters.get_form_id_by_name",
            lambda name: {"REPORT_A": "101", "REPORT_B": "202"}.get(name),
        )
        resp = client.get("/reports", params={"login_id": "someuser"})
        assert resp.status_code == 200
        assert resp.json()["reports"] == ["REPORT_A"]

    def test_empty_when_login_id_missing(self, client, monkeypatch):
        monkeypatch.setattr(
            "backend.tools.report_lookup._parse_returns",
            lambda: [{"Name": "REPORT_A"}],
        )
        resp = client.get("/reports")
        assert resp.status_code == 200
        assert resp.json()["reports"] == []

    def test_empty_when_login_id_unresolvable(self, client, monkeypatch):
        monkeypatch.setattr(
            "backend.tools.report_lookup._parse_returns",
            lambda: [{"Name": "REPORT_A"}],
        )
        monkeypatch.setattr(auth_service, "get_allowed_form_ids", lambda login_id: None)
        resp = client.get("/reports", params={"login_id": "unknown"})
        assert resp.status_code == 200
        assert resp.json()["reports"] == []

    def test_unfiltered_in_explicit_dev_bypass(self, client, monkeypatch):
        monkeypatch.setenv("REQUIRE_AUTH", "false")
        monkeypatch.setattr(
            "backend.tools.report_lookup._parse_returns",
            lambda: [{"Name": "REPORT_A"}],
        )
        resp = client.get("/reports")
        assert resp.status_code == 200
        assert resp.json()["reports"] == ["REPORT_A"]


class TestStatusErrorsObjectLevelAcl:
    def test_unknown_job_id_returns_not_found(self, client):
        resp = client.get("/status-errors/does-not-exist")
        assert resp.status_code == 200
        assert resp.json()["status"] == "not_found"

    def test_denied_job_looks_identical_to_not_found(self, client, monkeypatch):
        """H-03: a job that exists but doesn't belong to the caller must be
        indistinguishable from an unknown job_id (no existence oracle)."""
        from backend.agent import _error_jobs
        _error_jobs["job-owned-by-other"] = {
            "status": "done", "form_id": "9999",
            "payload": {"error_messages": [], "error_details": []},
        }
        monkeypatch.setattr(auth_service, "get_allowed_form_ids", lambda login_id: {"101"})

        resp = client.get("/status-errors/job-owned-by-other", params={"login_id": "someuser"})
        assert resp.status_code == 200
        assert resp.json() == {"status": "not_found"}
        _error_jobs.pop("job-owned-by-other", None)

    def test_owner_can_poll_their_own_job(self, client, monkeypatch):
        from backend.agent import _error_jobs
        _error_jobs["job-owned-by-caller"] = {
            "status": "done", "form_id": "101",
            "payload": {"error_messages": ["msg"], "error_details": []},
        }
        monkeypatch.setattr(auth_service, "get_allowed_form_ids", lambda login_id: {"101"})

        resp = client.get("/status-errors/job-owned-by-caller", params={"login_id": "someuser"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "done"
        assert body["error_messages"] == ["msg"]
        _error_jobs.pop("job-owned-by-caller", None)

    def test_pending_job_also_checked(self, client, monkeypatch):
        from backend.agent import _error_jobs
        _error_jobs["job-pending-other"] = {"status": "pending", "payload": None, "form_id": "9999"}
        monkeypatch.setattr(auth_service, "get_allowed_form_ids", lambda login_id: {"101"})

        resp = client.get("/status-errors/job-pending-other", params={"login_id": "someuser"})
        assert resp.json() == {"status": "not_found"}
        _error_jobs.pop("job-pending-other", None)
