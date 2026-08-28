"""The variance AI summary is fetched AFTER the table, not inline with it.

The inline summary in /compare-execute has an 8-second budget so the
comparison result is never held up. On a CPU-hosted Ollama that budget
cannot be met — the same prompt measured ~140s against llama3.1 — so the
panel came back empty on every single comparison, and because the chart's
Visualize button lived inside that same empty panel in the UI, the chart
disappeared with it.

/compare-summary runs the same generator with a realistic budget once the
table is already on screen. These tests pin the contract that makes that
safe: it never raises, never blocks on an absent LLM, and maps the row
shape the frontend actually holds.

No real Ollama is contacted — the HTTP layer is monkeypatched throughout.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import backend.tools.xbrl_comparator as xc
# The /compare-summary endpoint generates explanations through
# variance_explain now; xbrl_comparator is still imported for the
# direct-generator test below.
import backend.tools.variance_explain as ve


_ROWS = [
    {"concept": "ForeignCurrencyBalances", "val_a": 2970000.0, "val_b": 889680.0,
     "diff": 2080320.0, "pct_change": 233.3, "significant": True},
    {"concept": "ValueatRiskMaintained", "val_a": 37000000.0, "val_b": 74000000.0,
     "diff": -37000000.0, "pct_change": -50.0, "significant": True},
]


def _client():
    from fastapi.testclient import TestClient
    import backend.main as main
    return TestClient(main.app)


# ── the timeout override ─────────────────────────────────────────────────

class _CapturingClient:
    """Records the timeout it was built with, then fails fast."""
    captured: list = []

    def __init__(self, timeout=None, **kw):
        _CapturingClient.captured.append(timeout)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, json=None):
        raise RuntimeError("simulated network failure")


class TestSummaryTimeoutOverride:
    def setup_method(self):
        _CapturingClient.captured.clear()

    def _run(self, monkeypatch, **kwargs):
        import httpx
        monkeypatch.setattr(httpx, "AsyncClient", _CapturingClient)
        rows = [{"concept": "TotalAssets", "A": 100, "B": 90, "pct_change": 11.1, "significant": True}]
        return asyncio.run(xc.generate_llm_summary(rows, "A", "B", "RPT", **kwargs))

    def test_inline_default_is_still_the_short_budget(self, monkeypatch):
        """The inline caller must keep its 8s budget — that is what stops a
        hung Ollama holding the comparison response open for minutes."""
        monkeypatch.delenv("OLLAMA_SUMMARY_TIMEOUT", raising=False)
        self._run(monkeypatch)
        assert _CapturingClient.captured == [8.0]

    def test_explicit_timeout_overrides_the_env_default(self, monkeypatch):
        monkeypatch.delenv("OLLAMA_SUMMARY_TIMEOUT", raising=False)
        self._run(monkeypatch, timeout=300)
        assert _CapturingClient.captured == [300.0]

    def test_env_override_still_respected_when_no_explicit_timeout(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_SUMMARY_TIMEOUT", "3")
        self._run(monkeypatch)
        assert _CapturingClient.captured == [3.0]


# ── the endpoint ─────────────────────────────────────────────────────────

class TestCompareSummaryEndpoint:
    def test_returns_the_generated_summary(self, monkeypatch):
        async def _fake(rows, label_a, label_b, report_name="", timeout=None, **kw):
            return "AI Summary:\n• **Foreign Currency Balances** rose **+233.3%**."

        monkeypatch.setattr(ve, "generate_explanations", _fake)
        res = _client().post("/compare-summary", json={
            "rows": _ROWS, "label_a": "run A", "label_b": "run B",
            "report_name": "CIMS_FormGPB",
        })
        assert res.status_code == 200
        assert "+233.3%" in res.json()["llm_summary"]

    def test_rows_are_remapped_to_the_label_keys_the_generator_reads(self, monkeypatch):
        """The frontend holds val_a/val_b; generate_llm_summary reads each
        row by the LABEL keys. Without the remap every row is silently
        dropped as having no numeric values and the summary comes back
        empty for a table that is full of data."""
        seen: dict = {}

        async def _fake(rows, label_a, label_b, report_name="", timeout=None, **kw):
            seen["rows"] = rows
            seen["timeout"] = timeout
            return "ok"

        monkeypatch.setattr(ve, "generate_explanations", _fake)
        _client().post("/compare-summary", json={
            "rows": _ROWS, "label_a": "run A", "label_b": "run B",
            "report_name": "CIMS_FormGPB",
        })
        first = seen["rows"][0]
        assert first["run A"] == 2970000.0
        assert first["run B"] == 889680.0
        assert first["concept"] == "ForeignCurrencyBalances"

    def test_uses_a_budget_long_enough_to_actually_finish(self, monkeypatch):
        """The whole point of the second request: the 8s inline budget is
        unreachable on a CPU host, so this path must pass its own."""
        seen: dict = {}

        async def _fake(rows, label_a, label_b, report_name="", timeout=None, **kw):
            seen["timeout"] = timeout
            return "ok"

        monkeypatch.setattr(ve, "generate_explanations", _fake)
        monkeypatch.delenv("OLLAMA_SUMMARY_ASYNC_TIMEOUT", raising=False)
        _client().post("/compare-summary", json={
            "rows": _ROWS, "label_a": "A", "label_b": "B", "report_name": "R",
        })
        assert seen["timeout"] >= 60, "async summary needs a realistic budget"

    def test_generator_failure_is_not_an_error_response(self, monkeypatch):
        """A missing summary must never surface as a failed request — the
        table and chart on screen are complete without it."""
        async def _boom(rows, label_a, label_b, report_name="", timeout=None, **kw):
            raise RuntimeError("ollama is down")

        monkeypatch.setattr(ve, "generate_explanations", _boom)
        res = _client().post("/compare-summary", json={
            "rows": _ROWS, "label_a": "A", "label_b": "B", "report_name": "R",
        })
        assert res.status_code == 200
        assert res.json()["llm_summary"] == ""

    def test_empty_rows_short_circuit_without_calling_the_model(self, monkeypatch):
        called = []

        async def _fake(rows, label_a, label_b, report_name="", timeout=None, **kw):
            called.append(True)
            return "should not happen"

        monkeypatch.setattr(ve, "generate_explanations", _fake)
        res = _client().post("/compare-summary", json={
            "rows": [], "label_a": "A", "label_b": "B", "report_name": "R",
        })
        assert res.status_code == 200
        assert res.json()["llm_summary"] == ""
        assert not called

    def test_missing_labels_do_not_500(self):
        """label_a/label_b are optional in the model; the endpoint falls back
        to A/B rather than building rows keyed by an empty string."""
        res = _client().post("/compare-summary", json={"rows": []})
        assert res.status_code == 200
