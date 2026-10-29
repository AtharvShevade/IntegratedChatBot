"""Regression: /compare-summary rejected a large variance table with 422.

Once a return's importance JSON is loaded the frontend posts every eligible
row (~14k for BLS0100), but CompareSummaryRequest capped rows at 2000, so
FastAPI refused the request before the endpoint ran and the panel showed
"AI analysis is unavailable" with nothing in the app log.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.models import CompareSummaryRequest


def _rows(n: int) -> list[dict]:
    return [{"concept": f"c{i}", "importance_matched": True, "importance_tier": "Medium"} for i in range(n)]


def test_accepts_full_eligible_set():
    req = CompareSummaryRequest(rows=_rows(14268), label_a="A", label_b="B")
    assert len(req.rows) == 14268


def test_still_bounded():
    with pytest.raises(ValidationError):
        CompareSummaryRequest(rows=_rows(20001))
