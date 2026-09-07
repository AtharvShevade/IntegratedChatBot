"""A fuzzy return-name match must never be treated as an exact one.

The bug: find_matching_reports() collapsed six resolution tiers -- exact id,
exact name, exact alt-name, prefix, substring, weighted fuzzy -- into one flat
list, so callers branched on the COUNT alone:

    if len(matches) > 1:  -> ask
    match = matches[0]    -> act

A single FUZZY hit was therefore indistinguishable from a single EXACT hit and
was acted on silently. Measured against the real repository: "FormGPBX"
resolved to "FormGPB" and "DBR01X" to "DBR01", with no confirmation.
"""
from __future__ import annotations

import pytest

from backend.tools import report_lookup
from backend.tools.report_lookup import (
    MATCH_EXACT, MATCH_FUZZY, find_matching_reports,
    find_matching_reports_tiered, get_report_status, get_report_status_fast,
)


def _returns(monkeypatch, rows):
    """Pin a tiny return set so the assertions do not depend on the repo."""
    monkeypatch.setattr(report_lookup, "_normalised_returns",
                        lambda: [(report_lookup._normalise(r["Name"]),
                                  report_lookup._normalise(r.get("ReturnId", "")),
                                  report_lookup._normalise(r.get("AltName", "")),
                                  r) for r in rows])


SAMPLE = [
    {"Name": "CIMS_RLE", "Id": "101", "ReturnId": "R101"},
    {"Name": "CIMS_ROR", "Id": "102", "ReturnId": "R102"},
    {"Name": "FormGPB",  "Id": "103", "ReturnId": "R103"},
]


# ---------------------------------------------------------------------------
# The tier signal itself
# ---------------------------------------------------------------------------

def test_exact_name_is_reported_as_exact(monkeypatch):
    _returns(monkeypatch, SAMPLE)
    matches, tier = find_matching_reports_tiered("CIMS_RLE")
    assert tier == MATCH_EXACT
    assert [m["Name"] for m in matches] == ["CIMS_RLE"]


def test_exact_return_id_is_reported_as_exact(monkeypatch):
    """R102 IS the identity of CIMS_ROR -- typing it is not a guess."""
    _returns(monkeypatch, SAMPLE)
    matches, tier = find_matching_reports_tiered("R102")
    assert tier == MATCH_EXACT
    assert [m["Name"] for m in matches] == ["CIMS_ROR"]


def test_near_miss_is_reported_as_fuzzy(monkeypatch):
    _returns(monkeypatch, SAMPLE)
    matches, tier = find_matching_reports_tiered("CIMSREQ")
    assert tier == MATCH_FUZZY, "a typo must never be classified exact"


def test_no_match_is_empty_and_fuzzy(monkeypatch):
    _returns(monkeypatch, SAMPLE)
    matches, tier = find_matching_reports_tiered("zzzz-not-a-return")
    assert matches == []
    assert tier == MATCH_FUZZY


def test_public_wrapper_still_returns_a_plain_list(monkeypatch):
    """~10 call sites depend on this signature; the fix must not move them."""
    _returns(monkeypatch, SAMPLE)
    result = find_matching_reports("CIMS_RLE")
    assert isinstance(result, list)
    assert [m["Name"] for m in result] == ["CIMS_RLE"]


# ---------------------------------------------------------------------------
# Status resolution: what the user actually experiences
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("status_fn", [get_report_status, get_report_status_fast])
def test_exact_match_proceeds_without_confirmation(monkeypatch, status_fn):
    _returns(monkeypatch, SAMPLE)
    monkeypatch.setattr(report_lookup, "get_instances_by_form_id", lambda fid: [])
    result = status_fn("CIMS_RLE")
    assert result["type"] != "disambiguation", "an exact name must not be questioned"


@pytest.mark.parametrize("status_fn", [get_report_status, get_report_status_fast])
def test_single_fuzzy_match_asks_for_confirmation(monkeypatch, status_fn):
    """THE REGRESSION. One candidate is still a guess."""
    _returns(monkeypatch, [{"Name": "FormGPB", "Id": "103", "ReturnId": "R103"}])
    called = []
    monkeypatch.setattr(report_lookup, "get_instances_by_form_id",
                        lambda fid: called.append(fid) or [])
    result = status_fn("FormGPBX")
    assert result["type"] == "disambiguation"
    assert result["options"] == ["FormGPB"]
    assert "FormGPB" in result["message"]
    assert "exact" in result["message"].lower()
    assert called == [], "the workflow must not run before the user confirms"


@pytest.mark.parametrize("status_fn", [get_report_status, get_report_status_fast])
def test_multiple_fuzzy_matches_list_the_candidates(monkeypatch, status_fn):
    _returns(monkeypatch, SAMPLE)
    monkeypatch.setattr(report_lookup, "get_instances_by_form_id", lambda fid: [])
    # A prefix shared by CIMS_RLE and CIMS_ROR: several candidates, none exact.
    result = status_fn("CIMS_R")
    assert result["type"] == "disambiguation"
    assert len(result["options"]) > 1
    assert all(name in result["message"] for name in result["options"])


@pytest.mark.parametrize("status_fn", [get_report_status, get_report_status_fast])
def test_no_match_selects_nothing(monkeypatch, status_fn):
    _returns(monkeypatch, SAMPLE)
    called = []
    monkeypatch.setattr(report_lookup, "get_instances_by_form_id",
                        lambda fid: called.append(fid) or [])
    result = status_fn("zzzz-not-a-return")
    assert result["type"] == "error"
    assert not result.get("options")
    assert called == [], "nothing may be invented when nothing matched"


@pytest.mark.parametrize("status_fn", [get_report_status, get_report_status_fast])
def test_confirming_the_suggestion_continues_the_workflow(monkeypatch, status_fn):
    """After the user picks the offered name it is EXACT, so it must not be
    questioned a second time -- otherwise confirmation loops forever."""
    _returns(monkeypatch, [{"Name": "FormGPB", "Id": "103", "ReturnId": "R103"}])
    reached = []
    monkeypatch.setattr(report_lookup, "get_instances_by_form_id",
                        lambda fid: reached.append(fid) or [])

    asked = status_fn("FormGPBX")
    confirmed = asked["options"][0]

    result = status_fn(confirmed)
    assert result["type"] != "disambiguation", "must not re-ask a confirmed name"
    assert reached == ["103"], "the confirmed return must reach the status lookup"


def test_single_fuzzy_wording_differs_from_the_multi_match_wording(monkeypatch):
    """With one candidate the honest question is 'did you mean this?'.
    Rendering it as a numbered menu of one invites a reflexive click."""
    _returns(monkeypatch, [{"Name": "FormGPB", "Id": "103", "ReturnId": "R103"}])
    monkeypatch.setattr(report_lookup, "get_instances_by_form_id", lambda fid: [])
    message = get_report_status("FormGPBX")["message"]
    assert "Are you referring to" in message
    assert "1." not in message, "a menu of one is not a question"
