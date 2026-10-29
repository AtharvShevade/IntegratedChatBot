"""A request rejected by pydantic never reaches the endpoint, so it used to
leave nothing in the log (/compare-summary 422 -> silent "AI analysis is
unavailable"). The handler must log the failing field and keep the 422 body.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend import main


def test_422_is_logged_with_field_path_and_no_values(caplog):
    client = TestClient(main.app, raise_server_exceptions=False)
    rows = [{"concept": "c", "importance_tier": "X" * 40} for _ in range(3)]
    with caplog.at_level(logging.WARNING, logger="backend.main"):
        resp = client.post("/compare-summary", json={"rows": rows})
    assert resp.status_code == 422
    assert resp.json()["detail"][0]["loc"][0] == "body"

    logged = " ".join(r.getMessage() for r in caplog.records)
    assert "[VALIDATION_422]" in logged
    assert "/compare-summary" in logged
    assert "rows.*.importance_tier" in logged
    assert "x3" in logged          # de-duplicated across the 3 rows
    assert "X" * 40 not in logged  # submitted values are never logged
