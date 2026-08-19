"""Tests for the generate-instance / status-by-id flow.

1. A successful generate-instance call now echoes back the newly created
   InstanceLog row's Id (agent._find_new_instance_log_id) — the .NET
   FunPubInsertInstanceLog response never includes it (see
   call_generate_api's own docstring), so it must be looked up separately
   from a fresh read of XML_InstanceLog.xml.

2. "What is the status of <that id>" / "...of id: <that id>" now reuses
   the SAME rich status-checking pipeline as a report-name lookup
   (error extraction, 4000-series gating, the "check another reporting
   date" follow-up) — NOT a plain db_qa summary — via a new STEP-1
   fast-path in decide() (_has_guid_status) that runs BEFORE the generic
   name-search status path, seeded from the already-known row instead of
   a name-driven "pick the latest instance" search:
     - report_lookup._build_status_result_from_row / get_report_status_by_id_fast
     - agent._get_status_by_id_fast_with_bg_job
   This required its own fixes along the way:
     a. A workflow-gate override (_has_guid_status) so a bare GUID (no
        report name for find_matching_reports() to match) is routed to
        the NEW by-id fast-path instead of failing name search.
     b. db_qa's SUBMISSION_STATUS ALSO recognises a bare GUID (new
        regex + submission_id extraction + a target_type refinement
        defaulting to "self") as a redundant fallback path — reachable
        directly via classify_new()/dispatch2() in the tests below, even
        though the live chat pipeline now resolves GUID-status via STEP 1
        before db_qa (STEP 2) ever sees it.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.db_qa.new_intent_classifier import (
    classify_new, classify_new_with_semantic_tiers, _INSTANCE_ID_RE, _extract_submission_id,
)
from backend.db_qa.intents.taxonomy import Intent
from backend.agent import _fuzzy_has_status, decide

PATH_5_5 = Path(r"D:\Repo(new)\DataBase")
_need_5_5 = pytest.mark.skipif(not PATH_5_5.is_dir(), reason="5.5 real data tree not present")

# A real InstanceLog row present in the fixture data (FormId=2029/CIMS_ROR,
# UserId=iris810, Status=0/"New / Pending").
_REAL_GUID = "f7593ff72d644345865eaa84ae0b3073"


# ── _extract_submission_id ──────────────────────────────────────────────────

class TestExtractSubmissionId:
    def test_bare_guid_anywhere_in_text(self):
        assert _extract_submission_id(f"what is the status of {_REAL_GUID}") == _REAL_GUID

    def test_guid_with_id_label(self):
        assert _extract_submission_id(f"what is the status of id : {_REAL_GUID}") == _REAL_GUID
        assert _extract_submission_id(f"what is the status of id: {_REAL_GUID}") == _REAL_GUID
        assert _extract_submission_id(f"what is the status of id {_REAL_GUID}") == _REAL_GUID

    def test_dashed_guid_form(self):
        dashed = "f7593ff7-2d64-4345-865e-aa84ae0b3073"
        assert _extract_submission_id(f"status of {dashed}") == dashed

    def test_legacy_numeric_submission_id_still_works(self):
        assert _extract_submission_id("What is the status of my submission ID 4021?") == "4021"
        assert _extract_submission_id("What is the status of submission 4021 made by jsmith?") == "4021"


# ── Intent classification ───────────────────────────────────────────────────

class TestGuidStatusClassification:
    @pytest.mark.parametrize("q", [
        f"what is the status of {_REAL_GUID}",
        f"what is the status of id : {_REAL_GUID}",
        f"what is the status of id: {_REAL_GUID}",
        f"What is the status of {_REAL_GUID}?",
    ])
    def test_matches_submission_status(self, q):
        intent, params, target_type = classify_new(q)
        assert intent == Intent.SUBMISSION_STATUS, f"{q!r} -> {intent}"
        assert params.get("submission_id") == _REAL_GUID

    def test_defaults_to_self_scope_not_other_user(self):
        # No self-referential word ("my"/"I") AND no named other user —
        # must default to "self", not fall back to the admin-gated
        # "other_user" _infer_target_type would otherwise pick.
        intent, params, target_type = classify_new(f"what is the status of {_REAL_GUID}")
        assert target_type == "self"

    def test_named_other_user_still_routes_to_other_user(self):
        intent, params, target_type = classify_new(
            "What is the status of submission 4021 made by jsmith?"
        )
        assert intent == Intent.SUBMISSION_STATUS
        assert target_type == "other_user"
        assert params.get("target_user") == "jsmith"


class TestGuidStatusNotHijackedByReportStatusWorkflow:
    """Regression test for the same class of STEP-1-gate bug fixed twice
    already for date-range and monthly-status questions: _fuzzy_has_status
    fires on the word "status" and would otherwise send this into the
    legacy single-report-name status workflow, where a bare GUID has
    nothing to match against."""

    def test_guid_status_trips_fuzzy_has_status(self):
        q = f"what is the status of {_REAL_GUID}"
        assert _fuzzy_has_status(q), "precondition: override would be dead code otherwise"

    def test_instance_id_re_matches_bare_and_dashed_guid(self):
        assert _INSTANCE_ID_RE.search(_REAL_GUID)
        assert _INSTANCE_ID_RE.search("f7593ff7-2d64-4345-865e-aa84ae0b3073")
        assert not _INSTANCE_ID_RE.search("what is my email address")


# ── Handler + authorization, against real data ──────────────────────────────

@_need_5_5
class TestSubmissionStatusByGuidHandler:
    def test_owner_can_check_own_submission(self):
        async def _run():
            intent, params, tt, tier = await classify_new_with_semantic_tiers(
                f"what is the status of {_REAL_GUID}"
            )
            from backend.db_qa.xml_store import XMLStore
            from backend.db_qa import access_control
            from backend.db_qa.query_handlers import dispatch2

            store = XMLStore(str(PATH_5_5))
            scope = access_control.scope_query({"login_id": "iris810"}, intent.value, params)
            return dispatch2(intent, scope, params, store)

        result = asyncio.run(_run())
        assert result["found"]
        # Uses report_lookup._STATUS_LABELS' vocabulary (In Queue/In
        # Progress/Success/Failed/...), NOT db_qa's own broader
        # SUBMISSION_STATUS_LABELS ("New / Pending") — so the same
        # submission reads identically whether looked up by name or by id.
        assert "In Queue" in result["summary"]

    def test_only_curated_fields_shown_not_full_raw_dump(self):
        # Regression test for a real bug: the answer used to dump every
        # raw InstanceLog attribute (Dtc, Fileuploaddt, Reportstartdt,
        # Isextract, Iscims, Isaudited, Approveddt, Cimsuploaddt, ...) —
        # only Return / Reporting Date / Status / Initiated On should
        # appear, matching the report-name-based status flow's compact
        # view.
        async def _run():
            intent, params, tt, tier = await classify_new_with_semantic_tiers(
                f"what is the status of {_REAL_GUID}"
            )
            from backend.db_qa.xml_store import XMLStore
            from backend.db_qa import access_control
            from backend.db_qa.query_handlers import dispatch2
            from backend.agent.db_qa_router import _build_db_qa_data

            store = XMLStore(str(PATH_5_5))
            scope = access_control.scope_query({"login_id": "iris810"}, intent.value, params)
            result = dispatch2(intent, scope, params, store)
            return _build_db_qa_data(result, intent=intent.value)

        data = asyncio.run(_run())
        assert set(data["cols"]) == {"ReturnName", "ReportingDate", "StatusLabel", "GeneratedOn"}
        assert data["headers"] == ["Return", "Reporting Date", "Status", "Initiated On"]

    def test_non_owner_denied_ownership_not_permission_error(self):
        # Scope resolves to "self" (allowed — no PermissionError), but the
        # handler's own ownership check inside the "self" branch correctly
        # reports the submission isn't theirs, rather than leaking it.
        async def _run():
            intent, params, tt, tier = await classify_new_with_semantic_tiers(
                f"what is the status of {_REAL_GUID}"
            )
            from backend.db_qa.xml_store import XMLStore
            from backend.db_qa import access_control
            from backend.db_qa.query_handlers import dispatch2

            store = XMLStore(str(PATH_5_5))
            scope = access_control.scope_query({"login_id": "test810"}, intent.value, params)
            return dispatch2(intent, scope, params, store)

        result = asyncio.run(_run())
        assert not result["found"]
        assert "does not belong to your account" in result["summary"]


class TestParseDtc:
    """Regression test for a real bug: sorting DTC strings lexicographically
    ("DD-Mon-YYYY HH:MM:SS AM/PM") does NOT reflect chronological order —
    e.g. "Jul" sorts before "Jun" alphabetically (backwards from calendar
    order), and dates across a year boundary can sort wrong too. Any
    "most recent" selection must parse DTC into a real datetime first."""

    def test_month_name_ordering_bug_would_have_misled_string_sort(self):
        from backend.agent import _parse_dtc

        june = _parse_dtc("15-Jun-2026 10:00:00 AM")
        july = _parse_dtc("15-Jul-2026 10:00:00 AM")
        assert july > june, "parsed datetimes must reflect real calendar order"
        # The bug this guards against: as plain strings, "Jul" < "Jun".
        assert "15-Jul-2026 10:00:00 AM" < "15-Jun-2026 10:00:00 AM"

    def test_year_boundary_ordering(self):
        from backend.agent import _parse_dtc

        dec_2026 = _parse_dtc("31-Dec-2026 11:59:00 PM")
        jan_2027 = _parse_dtc("01-Jan-2027 12:00:01 AM")
        assert jan_2027 > dec_2026

    def test_unparseable_dtc_returns_none(self):
        from backend.agent import _parse_dtc

        assert _parse_dtc("not a date") is None
        assert _parse_dtc("") is None


@_need_5_5
class TestFindNewInstanceLogId:
    """Regression test for a real bug: a (FormId, ReportingDate, UserId)
    combination commonly accumulates many rows across repeated testing —
    without a before/after diff, "pick whichever matching row looks most
    recent" could return a stale row from a much earlier generation
    (compounded by the string-sort bug covered above), unrelated to the
    generate-instance call that had just been made."""

    def test_no_new_activity_returns_none(self):
        from backend.agent import _find_new_instance_log_id, _matching_instance_log_rows

        existing_ids = frozenset(
            r["Id"] for r in _matching_instance_log_rows("2029", "31-Mar-2026", "iris810")
            if r.get("Id")
        )
        assert existing_ids, "expected pre-existing rows for this (FormId, ReportingDate, UserId) in fixture data"

        # Passing the CURRENT full set of matching ids as "before" means
        # nothing new has happened since — must return None, never one of
        # the pre-existing (stale) ids.
        found_id = asyncio.run(
            _find_new_instance_log_id("2029", "31-Mar-2026", "iris810", existing_ids)
        )
        assert found_id is None

    def test_a_row_absent_from_before_ids_is_found(self):
        from backend.agent import _find_new_instance_log_id, _matching_instance_log_rows

        rows = _matching_instance_log_rows("2029", "31-Mar-2026", "iris810")
        assert rows, "expected pre-existing rows for this (FormId, ReportingDate, UserId) in fixture data"

        # Simulate "this call created row X" by excluding just one real
        # row's Id from the before-set — that row must be the one found,
        # not silently ignored or replaced by a different stale row.
        target = rows[0]
        before_ids = frozenset(
            r["Id"] for r in rows if r.get("Id") and r["Id"] != target["Id"]
        )
        found_id = asyncio.run(
            _find_new_instance_log_id("2029", "31-Mar-2026", "iris810", before_ids)
        )
        assert found_id == target["Id"]

    def test_no_match_returns_none_not_an_error(self):
        from backend.agent import _find_new_instance_log_id

        found_id = asyncio.run(
            _find_new_instance_log_id("nonexistent-form-id", "01-Jan-2099", "nobody")
        )
        assert found_id is None


@_need_5_5
class TestReportLookupStatusByRow:
    """report_lookup._build_status_result_from_row / get_report_status_by_id_fast —
    the row-based status builder that both the by-id lookup AND the
    refactored by-name lookup (_build_status_result_fast) now share, so
    the two produce byte-identical output for the same underlying row."""

    def test_by_id_matches_by_name_for_the_same_row(self):
        from backend.tools.report_lookup import (
            get_report_status_by_id_fast, get_instances_by_form_id, _build_status_result_fast,
        )

        by_id = get_report_status_by_id_fast(_REAL_GUID)
        assert by_id.get("type") in ("final", "latest_with_ask")

        # The name-based builder picks "the latest instance" for the form,
        # which may or may not be THIS row — so compare the shared fields
        # that don't depend on which row won ("latest"), confirming both
        # paths go through the exact same downstream logic (status
        # vocabulary, keys present) rather than comparing values that are
        # legitimately row-specific.
        instances = get_instances_by_form_id(by_id["form_id"])
        by_name = _build_status_result_fast(by_id["form_id"], by_id["report_name"], instances)
        assert set(by_id.keys()) == set(by_name.keys())
        assert by_id["report_name"] == by_name["report_name"]

    def test_unknown_id_returns_error_type(self):
        from backend.tools.report_lookup import get_report_status_by_id_fast

        result = get_report_status_by_id_fast("0000000000000000000000000000dead")
        assert result["type"] == "error"
        assert "not found" in result["message"].lower()

    def test_known_row_reports_correct_return_and_status(self):
        from backend.tools.report_lookup import get_report_status_by_id_fast

        result = get_report_status_by_id_fast(_REAL_GUID)
        assert result["report_name"] == "CIMS_ROR"
        assert result["reporting_date"] == "31-Mar-2026"
        assert result["status"] == "In Queue"  # Status="0" via _STATUS_LABELS


@_need_5_5
class TestGuidStatusFullPipelineViaDecide:
    """End-to-end: "what is the status of <id>" through the real decide()
    entry point must use the rich status-workflow pipeline (STEP 1),
    never db_qa's plain summary — same text/format as a report-name
    status lookup, including the "check another reporting date" follow-up
    (result_type="ask_previous" when other instances exist for the form)."""

    def test_full_pipeline_produces_workflow_style_answer(self):
        result = asyncio.run(
            decide(f"what is the status of {_REAL_GUID}", session_id="guid-status-test-owner", login_id="iris810")
        )
        text = result.get("result") or result.get("response_text") or ""
        assert "CIMS_ROR" in text
        assert "Reporting Date" in text
        assert "Status" in text
        assert "Initiated On" in text

    def test_non_owner_denied_via_form_auth(self):
        result = asyncio.run(
            decide(f"what is the status of {_REAL_GUID}", session_id="guid-status-test-other", login_id="test810")
        )
        text = result.get("result") or result.get("response_text") or ""
        assert "not authorised" in text.lower()
