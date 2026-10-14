"""The AI narrative must name concepts and members the way the table does.

/compare-summary is a separate request made after the table is on screen. Its row
used to omit concept_label / member_labels, so the sentences fell back to the
technical codes ("PE001504 - DM000012 decreased ...") although the table showed
"Loans And Advances - Private Sector SMEs [Total]".
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import backend.tools.variance_explain as ve

LABEL = "Loans And Advances - Private Sector SMEs"

_ROW = {
    "concept": "PE001504 [DM000012]", "concept_base": "PE001504", "context_key": "DE000004=DM000012",
    "val_a": 49507.0, "val_b": 4950700.0, "diff": -4901193.0, "pct_change": -99.0, "significant": True,
    "importance_matched": True, "importance_tier": "Medium", "importance": 39.1, "priority": 40.0,
    "section": "Breakdown of exposures by geography", "section_code": "ebg-table", "unit": "QAR",
}


def _client():
    from fastapi.testclient import TestClient
    import backend.main as main
    return TestClient(main.app)


@pytest.fixture(autouse=True)
def _no_auth(monkeypatch):
    monkeypatch.setenv("REQUIRE_AUTH", "false")


def _post(monkeypatch, row):
    seen = {}

    async def _fake(rows, label_a, label_b, report_name="", timeout=None, **kw):
        seen["rows"] = rows
        return "ok"

    monkeypatch.setattr(ve, "generate_explanations", _fake)
    res = _client().post("/compare-summary", json={
        "rows": [row], "label_a": "new", "label_b": "old", "report_name": "QCB_F013",
    })
    assert res.status_code == 200
    return seen["rows"][0]


class TestEndpointCarriesTheNames:
    def test_concept_label_and_member_labels_reach_the_generator(self, monkeypatch):
        got = _post(monkeypatch, {**_ROW, "concept_label": LABEL, "member_labels": ["Total"]})
        assert got["concept_label"] == LABEL
        assert got["member_labels"] == ["Total"]

    def test_older_clients_that_omit_them_still_work(self, monkeypatch):
        got = _post(monkeypatch, _ROW)
        assert got["concept_label"] == "" and got["member_labels"] == []

    def test_member_labels_are_length_capped(self, monkeypatch):
        got = _post(monkeypatch, {**_ROW, "member_labels": ["x" * 1000]})
        assert len(got["member_labels"][0]) == 256


class TestSentenceUsesTheNames:
    def _facts(self, row):
        rows = [{**row, "new": row["val_a"], "old": row["val_b"]}]
        return ve.select_facts(rows, label_a="new", label_b="old")

    def test_the_summary_sentence_names_the_concept_and_member_when_labels_are_sent(self, monkeypatch):
        got = _post(monkeypatch, {**_ROW, "concept_label": LABEL, "member_labels": ["Total"]})
        rows = [{**got, "new": got["new"], "old": got["old"]}]
        facts = ve.select_facts(rows, label_a="new", label_b="old")
        assert facts, "the row must be eligible for explanation"
        name = ve.business_name(facts[0]["concept"], facts[0].get("context_key", ""),
                                got["concept_label"], got["member_labels"])
        assert name == f"{LABEL} — Total"

    def test_without_labels_the_sentence_falls_back_to_the_codes_as_before(self):
        assert ve.business_name("PE001504", "DE000004=DM000012", "", []) == "PE001504 — DM000012"
