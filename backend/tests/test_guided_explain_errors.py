"""Tests for the "Explain Report Errors" guided-menu shortcut.

The shortcut is a focused ENTRY POINT into the error explanation flow that
already exists:

    Return -> FAILED instances only -> select instance -> existing flow

so these tests assert two things above all else:

  1. the new path never shows a non-failed instance, and
  2. "Check report status" is completely unchanged — it still resolves every
     status and still lists every instance.

Covers:
  - menu registration (present, and NOT permission-gated)
  - _handle_action_selected sets the new guided stage
  - get_failed_instances filters on the PARSED status int, sorts newest-first,
    and honours its limit
  - zero / one / many failed instances
  - the terminal payload carries everything the existing error UI consumes
    (status_code, error_category_counts, form_id, is_4000_series)
  - the "Initiated On:" label trap that would otherwise be eaten by
    _looks_like_new_query
  - a failed run whose error file is missing on disk
  - regression: the status flow still reports every status
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import backend.agent as agent
import backend.guided as guided
from backend.tools import report_lookup


def _run(coro):
    return asyncio.run(coro)


def _row(dtc: str, status: int, reporting_date: str = "31-Mar-2026") -> dict:
    """One InstanceLog row, in the raw shape get_instances_by_form_id yields."""
    return {"DTC": dtc, "Status": str(status), "ReportingDate": reporting_date}


# DTCs in _dtc_sort_key's format ("%d-%b-%Y %I:%M:%S %p"), deliberately not in
# chronological order so the newest-first sort is actually exercised.
_DTC_OLD = "01-Mar-2026 09:00:00 AM"
_DTC_MID = "15-Jun-2026 10:30:00 AM"
_DTC_NEW = "20-Jul-2026 04:15:00 PM"


# ═════════════════════════════════════════════════════════════════════════════
# 1. Menu registration
# ═════════════════════════════════════════════════════════════════════════════

class TestMenuRegistration:
    ACTION = "Explain Report Errors"

    def test_action_is_in_guided_actions(self):
        assert self.ACTION in guided.GUIDED_ACTIONS

    def test_action_is_not_permission_gated(self):
        """Explaining errors is read-only — same permission class as status,
        compare and DB Q&A. Gating it would hide it from users who can view a
        return but cannot generate instances."""
        assert self.ACTION not in guided._ACTIONS_REQUIRING_INSTANCE_GENERATION

    def test_visible_without_login(self):
        assert self.ACTION in guided._allowed_actions(None)

    def test_visible_to_user_without_instance_generation(self, monkeypatch):
        monkeypatch.setattr(
            "backend.services.auth_service.can_generate_instance", lambda _: False
        )
        allowed = guided._allowed_actions("someone")
        assert self.ACTION in allowed
        # sanity: the gated actions really are filtered out for this user
        assert "Generate instance for a report" not in allowed

    def test_existing_actions_are_untouched(self):
        """The five original actions must keep their exact strings — the
        frontend filters the menu by string equality."""
        assert guided.GUIDED_ACTIONS[:5] == [
            "Check report status",
            "Generate instance for a report",
            "Schedule a report",
            "Perform comparative analysis",
            "Retrieve data from database",
        ]


class TestActionSelected:
    ACTION = "Explain Report Errors"
    SESSION = "test-session-explain-errors-step1"

    def setup_method(self):
        guided._guided_sessions.clear()
        agent._session_context.clear()

    def teardown_method(self):
        guided._guided_sessions.clear()
        agent._session_context.clear()

    def test_sets_err_report_stage_and_prompts(self):
        result = guided._handle_action_selected(self.ACTION, self.SESSION)
        assert result["result_type"] == "guided_input"
        assert guided._guided_sessions[self.SESSION]["stage"] == guided.STAGE_ERR_REPORT
        assert "report name" in result["response_text"].lower()

    def test_status_action_still_sets_its_own_stage(self):
        """Regression: the new branch must not shadow the status branch."""
        result = guided._handle_action_selected("Check report status", self.SESSION)
        assert result["result_type"] == "guided_input"
        assert guided._guided_sessions[self.SESSION]["stage"] == guided.STAGE_STATUS_REPORT


# ═════════════════════════════════════════════════════════════════════════════
# 2. get_failed_instances — the failed-only filter
# ═════════════════════════════════════════════════════════════════════════════

class TestGetFailedInstances:
    def _patch_rows(self, monkeypatch, rows):
        monkeypatch.setattr(report_lookup, "get_instances_by_form_id", lambda _fid: list(rows))

    @pytest.mark.parametrize("code", sorted(report_lookup._FAILED_STATUSES))
    def test_failed_codes_are_included(self, monkeypatch, code):
        self._patch_rows(monkeypatch, [_row(_DTC_NEW, code)])
        assert len(report_lookup.get_failed_instances("4046")) == 1

    @pytest.mark.parametrize("code", [0, 4, 6, 9, 11, 12])
    def test_non_failed_codes_are_excluded(self, monkeypatch, code):
        """In Queue / In Process / Approved / Approval Pending / Rejected must
        never appear in this flow."""
        assert code not in report_lookup._FAILED_STATUSES  # guards the fixture
        self._patch_rows(monkeypatch, [_row(_DTC_NEW, code)])
        assert report_lookup.get_failed_instances("4046") == []

    def test_mixed_list_keeps_only_failed(self, monkeypatch):
        self._patch_rows(monkeypatch, [
            _row(_DTC_NEW, 11),   # Success
            _row(_DTC_MID, 8),    # Failed
            _row(_DTC_OLD, 9),    # Approved
            _row("02-Mar-2026 09:00:00 AM", 3),   # Failed
        ])
        failed = report_lookup.get_failed_instances("4046")
        assert len(failed) == 2
        assert all(int(f["status"]) in report_lookup._FAILED_STATUSES for f in failed)

    def test_sorted_newest_first(self, monkeypatch):
        self._patch_rows(monkeypatch, [
            _row(_DTC_OLD, 3), _row(_DTC_NEW, 5), _row(_DTC_MID, 8),
        ])
        dtcs = [f["dtc"] for f in report_lookup.get_failed_instances("4046")]
        assert dtcs == [_DTC_NEW, _DTC_MID, _DTC_OLD]

    def test_limit_is_honoured(self, monkeypatch):
        rows = [_row(f"{d:02d}-Mar-2026 09:00:00 AM", 3) for d in range(1, 16)]
        self._patch_rows(monkeypatch, rows)
        assert len(report_lookup.get_failed_instances("4046")) == 10          # default
        assert len(report_lookup.get_failed_instances("4046", limit=3)) == 3

    def test_status_shape_matches_get_available_instances(self, monkeypatch):
        """`status` must be the RAW XML string, exactly as
        get_available_instances emits it, so the existing InstanceDropdown
        receives identical data from both flows."""
        self._patch_rows(monkeypatch, [_row(_DTC_NEW, 8)])
        failed = report_lookup.get_failed_instances("4046")[0]
        available = report_lookup.get_available_instances("4046")[0]
        assert failed["status"] == "8"
        assert failed == available          # identical dict for a failed row
        assert sorted(failed) == sorted(available)

    def test_label_matches_the_shared_formatter(self, monkeypatch):
        """The label must be produced by _fmt_instance_label so
        _parse_dtc_from_label can read the user's pick back."""
        self._patch_rows(monkeypatch, [_row(_DTC_NEW, 8, "30-Jun-2026")])
        entry = report_lookup.get_failed_instances("4046")[0]
        assert entry["label"] == report_lookup._fmt_instance_label(_DTC_NEW, "30-Jun-2026")
        assert agent._parse_dtc_from_label(entry["label"]) == _DTC_NEW

    def test_label_and_parser_stay_in_sync(self):
        """_fmt_instance_label and _parse_dtc_from_label are a matched pair:
        the label is echoed back by the user's click and parsed with a regex.
        Renaming the prefix in one without the other silently breaks EVERY
        instance dropdown (status flow included) — the click stops resolving
        and the picker just re-prompts. This asserts the round trip rather than
        the literal wording, so the pair can be renamed again safely."""
        label = report_lookup._fmt_instance_label(_DTC_NEW, "30-Jun-2026")
        assert agent._parse_dtc_from_label(label) == _DTC_NEW
        # the pre-rename wording must keep parsing: labels rendered before the
        # change are still sitting in users' localStorage chat history
        assert agent._parse_dtc_from_label(
            f"Generated On: {_DTC_NEW} | Reporting Date: 30-Jun-2026"
        ) == _DTC_NEW

    def test_get_available_instances_still_returns_every_status(self, monkeypatch):
        """Regression: the status flow's own helper is untouched."""
        self._patch_rows(monkeypatch, [
            _row(_DTC_NEW, 11), _row(_DTC_MID, 8), _row(_DTC_OLD, 0),
        ])
        assert len(report_lookup.get_available_instances("4046")) == 3


# ═════════════════════════════════════════════════════════════════════════════
# 3. The shortcut's own branching
# ═════════════════════════════════════════════════════════════════════════════

class _Fixture:
    """Shared monkeypatching for the return-resolution + instance-listing path."""

    FORM_ID = "4046"
    NAME    = "CIMS_RAQ"

    @staticmethod
    def patch_single_match(monkeypatch, failed_rows):
        monkeypatch.setattr(
            agent, "find_matching_reports",
            lambda _q: [{"Id": _Fixture.FORM_ID, "Name": _Fixture.NAME}],
        )
        monkeypatch.setattr(agent, "get_failed_instances", lambda _fid, limit=10: list(failed_rows)[:limit])


def _failed_entry(dtc: str, status: int = 8, reporting_date: str = "30-Jun-2026") -> dict:
    return {
        "dtc": dtc,
        "reporting_date": reporting_date,
        "status": str(status),
        "label": report_lookup._fmt_instance_label(dtc, reporting_date),
    }


class TestExplainErrorsBranching:
    SESSION = "test-session-explain-errors-branch"

    def setup_method(self):
        guided._guided_sessions.clear()
        agent._session_context.clear()

    def teardown_method(self):
        guided._guided_sessions.clear()
        agent._session_context.clear()

    def test_zero_failed_instances_is_terminal_and_clears_session(self, monkeypatch):
        _Fixture.patch_single_match(monkeypatch, [])
        result = agent._handle_explain_errors("CIMS_RAQ", self.SESSION)
        assert result["result_type"] == "final"
        assert "no failed instances" in result["response_text"].lower()
        assert not result.get("data", {}).get("error_category_counts")
        assert self.SESSION not in agent._session_context

    def test_many_failed_instances_offers_a_dropdown(self, monkeypatch):
        entries = [_failed_entry(_DTC_NEW), _failed_entry(_DTC_MID, status=3)]
        _Fixture.patch_single_match(monkeypatch, entries)
        result = agent._handle_explain_errors("CIMS_RAQ", self.SESSION)

        assert result["result_type"] == "date_selection"
        assert len(result["options"]) == 2
        # InstanceDropdown looks its status dot up as statusMap[opt] — options[i]
        # and instances_data[i]["label"] must be string-identical.
        assert result["options"] == [d["label"] for d in result["instances_data"]]
        assert all(
            int(d["status"]) in report_lookup._FAILED_STATUSES for d in result["instances_data"]
        )

        session = agent._session_context[self.SESSION]
        assert session["awaiting"] == agent.STAGE_ERR_INSTANCE
        assert session["pending_form_id"] == _Fixture.FORM_ID
        assert session["pending_return_name"] == _Fixture.NAME
        assert len(session["pending_failed_instances"]) == 2

    def test_dropdown_payload_is_identical_to_the_status_flow(self, monkeypatch):
        """The shortcut must reuse the status flow's instance dropdown, not a
        variant of it: same result_type, same prompt wording, same option/label
        format, same instances_data shape. Only the DATA differs (failed-only).

        The reference payload is the one the status flow's STAGE_PREV_DATES
        "Yes" path emits — see the _build call in decide().
        """
        # <=5 so the payload must be byte-identical to the status flow's.
        entries = [_failed_entry(_DTC_NEW), _failed_entry(_DTC_MID, status=3)]
        _Fixture.patch_single_match(monkeypatch, entries)
        mine = agent._handle_explain_errors("CIMS_RAQ", self.SESSION)
        assert "use_search_dropdown" not in (mine.get("data") or {})

        reference = agent._build(
            intent="get_status", report_name=_Fixture.NAME,
            response_text=f"Select a reporting instance for '{_Fixture.NAME}':",
            result_type="date_selection",
            options=[i["label"] for i in entries],
            instances_data=[{"label": i["label"], "status": i["status"]} for i in entries],
        )

        for key in ("result_type", "response_text", "options", "instances_data",
                    "intent", "report_name"):
            assert mine[key] == reference[key], f"{key} diverges from the status flow"

    # ── expanded list vs collapsed dropdown threshold ───────────────────────
    # <=5 failed instances -> the EXPANDED InstanceDropdown row list, i.e. the
    #                         status flow's picker (flag absent)
    #  >5 failed instances -> collapsed searchable dropdown
    #                         (data.use_search_dropdown set)

    def _offer(self, monkeypatch, count):
        entries = [
            _failed_entry(f"{d:02d}-Mar-2026 09:00:00 AM") for d in range(1, count + 1)
        ]
        _Fixture.patch_single_match(monkeypatch, entries)
        return agent._handle_explain_errors("CIMS_RAQ", self.SESSION)

    # count=1 deliberately excluded: a single failed instance auto-proceeds
    # straight into the explanation flow, so no picker is rendered at all
    # (covered by test_single_failed_instance_skips_the_dropdown).
    @pytest.mark.parametrize("count", [2, 3, 4, 5])
    def test_five_or_fewer_uses_the_expanded_row_list(self, monkeypatch, count):
        """Flag ABSENT -> the frontend renders InstanceDropdown, the same
        expanded row list (status dot + Select button) the status flow uses."""
        result = self._offer(monkeypatch, count)
        assert result["result_type"] == "date_selection"
        assert "use_search_dropdown" not in (result.get("data") or {})
        assert len(result["options"]) == count
        # instances_data must still be present — the row list needs it for dots
        assert result["options"] == [d["label"] for d in result["instances_data"]]

    @pytest.mark.parametrize("count", [6, 7, 10])
    def test_more_than_five_collapses_into_a_search_dropdown(self, monkeypatch, count):
        result = self._offer(monkeypatch, count)
        assert result["result_type"] == "date_selection"
        assert result["data"]["use_search_dropdown"] is True
        assert len(result["options"]) == count

    def test_threshold_boundary_is_five(self, monkeypatch):
        """Exactly 5 -> expanded row list; exactly 6 -> collapsed dropdown."""
        assert "use_search_dropdown" not in (self._offer(monkeypatch, 5).get("data") or {})
        assert self._offer(monkeypatch, 6)["data"]["use_search_dropdown"] is True

    def test_search_dropdown_flag_never_set_by_the_status_flow(self, monkeypatch):
        """The status flow must never carry the flag, or its expanded list would
        collapse into a dropdown."""
        reference = agent._build(
            intent="get_status", report_name="CIMS_RAQ",
            response_text="Select a reporting instance for 'CIMS_RAQ':",
            result_type="date_selection",
            options=["a", "b"],
            instances_data=[{"label": "a", "status": "11"}, {"label": "b", "status": "0"}],
        )
        assert "use_search_dropdown" not in (reference.get("data") or {})

    def test_single_failed_instance_skips_the_dropdown(self, monkeypatch):
        _Fixture.patch_single_match(monkeypatch, [_failed_entry(_DTC_NEW)])
        captured = {}

        def _fake_lookup(form_id, dtc, return_name):
            captured.update(form_id=form_id, dtc=dtc, return_name=return_name)
            return {
                "type": "final", "report_name": return_name,
                "reporting_date": "30-Jun-2026", "dtc": dtc,
                "status": "Failed", "status_code": 8,
                "error_category_counts": {
                    "error_file_path": "C:/err.html", "formula_error": 4,
                },
                "is_4000_series": True,
                "download_url": "", "download_label": "", "status_note": "",
                "error_messages": [], "error_details": [],
            }

        monkeypatch.setattr(agent, "_get_instance_by_dtc_fast_with_bg_job", _fake_lookup)
        result = agent._handle_explain_errors("CIMS_RAQ", self.SESSION)

        assert result["result_type"] == "final"
        assert captured["dtc"] == _DTC_NEW
        assert captured["form_id"] == _Fixture.FORM_ID
        assert self.SESSION not in agent._session_context

    def test_terminal_payload_feeds_the_existing_error_ui(self, monkeypatch):
        """The handoff contract: everything ErrorSummaryPanel and
        /explain-category read must be present, with a NON-EMPTY form_id.

        get_instance_by_dtc_fast omits form_id, so this is the regression guard
        for the one-line injection in _explain_errors_for_instance.
        """
        monkeypatch.setattr(
            agent, "_get_instance_by_dtc_fast_with_bg_job",
            lambda form_id, dtc, return_name: {
                "type": "final", "report_name": return_name,
                "reporting_date": "30-Jun-2026", "dtc": dtc,
                "status": "Failed", "status_code": 8,
                "error_category_counts": {
                    "error_file_path": "C:/err.html",
                    "formula_error": 4, "dimensional": 23,
                },
                "is_4000_series": True,
                "download_url": "/download-file?x=1",
                "download_label": "Download Error File",
                "status_note": "", "error_messages": [], "error_details": [],
                "job_id": "job-123",
            },
        )
        result = agent._explain_errors_for_instance(
            form_id="4046", dtc=_DTC_NEW, return_name="CIMS_RAQ", session_id=self.SESSION,
        )
        data = result["data"]
        assert data["form_id"] == "4046"          # ← the omission guard
        assert data["status_code"] in report_lookup._FAILED_STATUSES
        assert data["error_category_counts"]["error_file_path"] == "C:/err.html"
        assert data["is_4000_series"] is True
        assert data["report_name"] == "CIMS_RAQ"
        assert result["job_id"] == "job-123"      # background polling still wired
        assert result["result_type"] == "final"

    def test_missing_error_file_adds_no_extra_paragraph(self, monkeypatch):
        monkeypatch.setattr(
            agent, "_get_instance_by_dtc_fast_with_bg_job",
            lambda form_id, dtc, return_name: {
                "type": "final", "report_name": return_name,
                "reporting_date": "30-Jun-2026", "dtc": dtc,
                "status": "Failed", "status_code": 8,
                "error_category_counts": {},          # error file absent on disk
                "is_4000_series": False,
                "download_url": "", "download_label": "",
                "status_note": "Error file not found.",
                "error_messages": [], "error_details": [],
            },
        )
        result = agent._explain_errors_for_instance(
            form_id="4046", dtc=_DTC_NEW, return_name="CIMS_RAQ", session_id=self.SESSION,
        )
        text = result["response_text"]
        # ONLY the existing status information — status_note and nothing else.
        assert "Error file not found." in text
        assert "isn't available on the server" not in text
        assert "administrator" not in text
        assert text.strip().endswith("Error file not found.")
        assert not result["data"].get("error_category_counts")
        assert result.get("job_id") is None

    # ── no-error-file cases ─────────────────────────────────────────────────
    #
    # _get_download_info._try_error has TWO no-error-file outcomes:
    #   (a) ErrorDocPath recorded but absent on disk -> status_note is set
    #   (b) ErrorDocPath empty / no basename         -> status_note is ""
    # (b) used to render as a bare status block with no explanation at all.
    # Both must now end in exactly "Error file not found.".

    @staticmethod
    def _patch_no_error_file(monkeypatch, status_note: str):
        """A failed instance with no usable error file.

        Mirrors what get_instance_by_dtc_fast really returns in that case:
        error_category_counts == {} (because _get_error_counts bails without an
        error_file_path) and no download link.
        """
        monkeypatch.setattr(
            agent, "_get_instance_by_dtc_fast_with_bg_job",
            lambda form_id, dtc, return_name: {
                "type": "final", "report_name": return_name,
                "reporting_date": "30-Jun-2021", "dtc": dtc,
                "status": "Failed", "status_code": 8,
                "error_category_counts": {},
                "is_4000_series": False,
                "download_url": "", "download_label": "",
                "status_note": status_note,
                "error_messages": [], "error_details": [],
            },
        )

    @pytest.mark.parametrize("status_note,case", [
        ("Error file not found.", "ErrorDocPath recorded, file absent on disk"),
        ("",                     "ErrorDocPath empty — previously silent"),
    ])
    def test_failed_instance_without_error_file_says_so(self, monkeypatch, status_note, case):
        self._patch_no_error_file(monkeypatch, status_note)
        result = agent._explain_errors_for_instance(
            form_id="4046", dtc=_DTC_NEW, return_name="CIMS_LR (Quarterly)",
            session_id=self.SESSION,
        )
        text = result["response_text"]

        # the message is present, and is the LAST thing shown
        assert "Error file not found." in text, case
        assert text.strip().endswith("Error file not found."), case
        # exactly once — never doubled by the normalisation
        assert text.count("Error file not found.") == 1, case
        # the normal instance details still precede it
        assert "CIMS_LR (Quarterly)" in text
        assert "Status         : Failed" in text
        # no extra explanatory prose
        assert "available on the server" not in text
        assert "administrator" not in text

    @pytest.mark.parametrize("status_note", ["Error file not found.", ""])
    def test_no_error_file_means_no_error_summary_panel(self, monkeypatch, status_note):
        """The frontend gates ErrorSummaryPanel on `isFailed &&
        errorCategoryCounts`, so the key must be ABSENT — otherwise an empty
        category panel renders. Also asserts no category counts leak through."""
        self._patch_no_error_file(monkeypatch, status_note)
        result = agent._explain_errors_for_instance(
            form_id="4046", dtc=_DTC_NEW, return_name="CIMS_LR (Quarterly)",
            session_id=self.SESSION,
        )
        data = result["data"]
        assert "error_category_counts" not in data
        for category in ("formula_error", "dimensional", "xbrl_schema"):
            assert category not in data
        assert not result.get("error_details")
        assert result.get("job_id") is None
        assert result["download_url"] == ""

    def test_both_no_error_file_cases_produce_the_same_message(self, monkeypatch):
        """Guards _ERROR_FILE_NOT_FOUND against drifting from the literal
        _get_download_info._try_error emits."""
        texts = []
        for note in ("Error file not found.", ""):
            self._patch_no_error_file(monkeypatch, note)
            texts.append(agent._explain_errors_for_instance(
                form_id="4046", dtc=_DTC_NEW, return_name="CIMS_LR (Quarterly)",
                session_id=self.SESSION,
            )["response_text"])
        assert texts[0] == texts[1]

    @pytest.mark.parametrize("counts,case", [
        ({"error_file_path": "C:/e.html"},
         "file parsed but produced no categories at all"),
        ({"error_file_path": "C:/e.html", "html_category": "xbrl_schema"},
         "file classified but every category count is zero"),
        ({"error_file_path": "C:/e.html", "formula_error": 0, "dimensional": 0},
         "explicit zero counts"),
    ])
    def test_error_file_present_but_nothing_explainable(self, monkeypatch, counts, case):
        """The third silent state: counts is TRUTHY (it always carries
        error_file_path) but no supported category has a nonzero count. That
        used to publish the counts, rendering an EMPTY ErrorSummaryPanel with
        no chips and no note."""
        monkeypatch.setattr(
            agent, "_get_instance_by_dtc_fast_with_bg_job",
            lambda form_id, dtc, return_name: {
                "type": "final", "report_name": return_name,
                "reporting_date": "30-Jun-2021", "dtc": dtc,
                "status": "Failed", "status_code": 8,
                "error_category_counts": dict(counts),
                "is_4000_series": False,
                "download_url": "", "download_label": "",
                "status_note": "", "error_messages": [], "error_details": [],
            },
        )
        result = agent._explain_errors_for_instance(
            form_id="4046", dtc=_DTC_NEW, return_name="CIMS_RLC_FIMD",
            session_id=self.SESSION,
        )
        text = result["response_text"]
        assert text.strip().endswith("Error file not found."), case
        assert text.count("Error file not found.") == 1, case
        # the panel must not render an empty shell
        assert "error_category_counts" not in result["data"], case

    def test_error_file_present_is_unaffected(self, monkeypatch):
        """Regression: an instance that DOES have an error file must not gain
        the note, and must still carry the counts into the existing flow."""
        monkeypatch.setattr(
            agent, "_get_instance_by_dtc_fast_with_bg_job",
            lambda form_id, dtc, return_name: {
                "type": "final", "report_name": return_name,
                "reporting_date": "30-Jun-2026", "dtc": dtc,
                "status": "Failed", "status_code": 8,
                "error_category_counts": {
                    "error_file_path": "C:/err.html", "formula_error": 4,
                },
                "is_4000_series": False,
                "download_url": "/download-file?x=1",
                "download_label": "Download Error File",
                "status_note": "", "error_messages": [], "error_details": [],
            },
        )
        result = agent._explain_errors_for_instance(
            form_id="4046", dtc=_DTC_NEW, return_name="CIMS_RAQ", session_id=self.SESSION,
        )
        assert "Error file not found." not in result["response_text"]
        assert result["data"]["error_category_counts"]["formula_error"] == 4
        assert result["download_label"] == "Download Error File"

    def test_ambiguous_return_offers_disambiguation(self, monkeypatch):
        monkeypatch.setattr(
            agent, "find_matching_reports",
            lambda _q: [{"Id": "1", "Name": "CIMS_RAQ"}, {"Id": "2", "Name": "CIMS_ROR"}],
        )
        result = agent._handle_explain_errors("cims", self.SESSION)
        assert result["result_type"] == "disambiguation"
        assert result["options"] == ["CIMS_RAQ", "CIMS_ROR"]
        assert agent._session_context[self.SESSION]["awaiting"] == agent.STAGE_ERR_REPORT

    def test_unknown_return_is_an_error(self, monkeypatch):
        monkeypatch.setattr(agent, "find_matching_reports", lambda _q: [])
        monkeypatch.setattr(agent, "fuzzy_report_suggestions", lambda _q: [])
        result = agent._handle_explain_errors("zzzz", self.SESSION)
        assert result["result_type"] == "error"
        assert "no matching reports" in result["response_text"].lower()

    def test_unauthorised_return_is_refused(self, monkeypatch):
        monkeypatch.setattr(
            agent, "find_matching_reports", lambda _q: [{"Id": "4046", "Name": "CIMS_RAQ"}],
        )
        monkeypatch.setattr(agent, "fuzzy_report_suggestions", lambda _q: [])
        result = agent._handle_explain_errors(
            "CIMS_RAQ", self.SESSION, allowed_form_ids={"9999"},
        )
        assert result["result_type"] == "error"
        assert "not authorised" in result["response_text"].lower()


# ═════════════════════════════════════════════════════════════════════════════
# 4. decide() guard clauses
# ═════════════════════════════════════════════════════════════════════════════

class TestDecideGuards:
    SESSION = "test-session-explain-errors-decide"
    FORM_ID = "4046"
    NAME    = "CIMS_RAQ"

    def setup_method(self):
        agent._session_context.clear()

    def teardown_method(self):
        agent._session_context.clear()

    def _stage_instance_pick(self, entries):
        agent._session_context[self.SESSION] = {
            "awaiting":                 agent.STAGE_ERR_INSTANCE,
            "pending_form_id":          self.FORM_ID,
            "pending_return_name":      self.NAME,
            "pending_failed_instances": entries,
        }

    @staticmethod
    def _no_auth(monkeypatch):
        """decide() refuses anonymous callers when REQUIRE_AUTH is set in the
        environment, and that check runs before the stage guards. These tests
        exercise the guards, not auth."""
        monkeypatch.setenv("REQUIRE_AUTH", "false")

    def _patch_terminal(self, monkeypatch, captured):
        def _fake(form_id, dtc, return_name):
            captured.update(form_id=form_id, dtc=dtc)
            return {
                "type": "final", "report_name": return_name,
                "reporting_date": "30-Jun-2026", "dtc": dtc,
                "status": "Failed", "status_code": 8,
                "error_category_counts": {"error_file_path": "C:/e.html", "formula_error": 1},
                "is_4000_series": False,
                "download_url": "", "download_label": "", "status_note": "",
                "error_messages": [], "error_details": [],
            }
        monkeypatch.setattr(agent, "_get_instance_by_dtc_fast_with_bg_job", _fake)

    def test_staged_states_include_the_new_stages(self):
        """Without this, the DB-QA / SQL fast paths swallow the user's pick."""
        assert agent._is_staged_session({"awaiting": agent.STAGE_ERR_REPORT}) is True
        assert agent._is_staged_session({"awaiting": agent.STAGE_ERR_INSTANCE}) is True

    def test_current_label_no_longer_trips_the_generate_detector(self):
        """The label used to start with "Generated On:", and "Generated"
        stem-matches 'gene' in _GEN_STEMS — so clicking your own instance
        looked like a fresh "generate" request. Renaming to "Initiated On"
        removed that trap at the source ("Started On" would have kept it, via
        the 'star' stem). The label-first parse order in the guard stays as
        defence in depth, and is what still protects the legacy spelling below.
        """
        assert agent._looks_like_new_query(_failed_entry(_DTC_NEW)["label"]) is False
        assert agent._looks_like_new_query(
            f"Generated On: {_DTC_NEW} | Reporting Date: 30-Jun-2026"
        ) is True   # the legacy spelling still trips it — hence label-first

    @pytest.mark.parametrize("prefix,case", [
        ("Initiated On", "current label"),
        ("Generated On", "legacy label still in a user's chat history"),
    ])
    def test_instance_label_resolves_and_is_not_eaten(self, monkeypatch, prefix, case):
        """Both spellings must resolve to the DTC. The legacy one is the real
        test of the label-first ordering, since it still trips
        _looks_like_new_query."""
        self._no_auth(monkeypatch)
        entry = _failed_entry(_DTC_NEW)
        self._stage_instance_pick([entry])
        label = f"{prefix}: {_DTC_NEW} | Reporting Date: 30-Jun-2026"

        captured: dict = {}
        self._patch_terminal(monkeypatch, captured)
        result = _run(agent.decide(label, session_id=self.SESSION))

        assert captured["dtc"] == _DTC_NEW, case
        assert captured["form_id"] == self.FORM_ID, case
        assert result["result_type"] == "final", case
        assert self.SESSION not in agent._session_context, case

    def test_numeric_pick_resolves(self, monkeypatch):
        self._no_auth(monkeypatch)
        self._stage_instance_pick([_failed_entry(_DTC_NEW), _failed_entry(_DTC_MID)])
        captured: dict = {}
        self._patch_terminal(monkeypatch, captured)
        _run(agent.decide("2", session_id=self.SESSION))
        assert captured["dtc"] == _DTC_MID

    def test_unmatched_input_redisplays_failed_only_and_keeps_stage(self, monkeypatch):
        self._no_auth(monkeypatch)
        entries = [_failed_entry(_DTC_NEW), _failed_entry(_DTC_MID)]
        self._stage_instance_pick(entries)
        result = _run(agent.decide("nonsense zzz", session_id=self.SESSION))

        assert result["result_type"] == "date_selection"
        assert result["options"] == [e["label"] for e in entries]
        assert all(
            int(d["status"]) in report_lookup._FAILED_STATUSES for d in result["instances_data"]
        )
        # stage survives so the user can still pick
        assert agent._session_context[self.SESSION]["awaiting"] == agent.STAGE_ERR_INSTANCE

    def test_new_report_resets_the_stage(self, monkeypatch):
        self._no_auth(monkeypatch)
        self._stage_instance_pick([_failed_entry(_DTC_NEW)])
        _run(agent.decide("new report", session_id=self.SESSION))
        assert self.SESSION not in agent._session_context


# ═════════════════════════════════════════════════════════════════════════════
# 5. Regression — Check report status is unchanged
# ═════════════════════════════════════════════════════════════════════════════

class TestStatusFlowUnchanged:
    SESSION = "test-session-status-unchanged"

    def setup_method(self):
        guided._guided_sessions.clear()
        agent._session_context.clear()

    def teardown_method(self):
        guided._guided_sessions.clear()
        agent._session_context.clear()

    @pytest.mark.parametrize("code,label", [
        (11, "Approval Pending"), (9, "Approved"), (12, "Rejected"),
        (6, "In Process"), (0, "In Queue"), (4, "Unknown"),
        (3, "Failed"), (5, "Failed"), (8, "Failed"), (10, "Failed"), (13, "Failed"),
    ])
    def test_every_status_still_maps(self, code, label):
        assert report_lookup.map_status(code) == label

    def test_status_flow_lists_every_instance(self, monkeypatch):
        """The status dropdown must keep showing non-failed instances."""
        rows = [_row(_DTC_NEW, 11), _row(_DTC_MID, 8), _row(_DTC_OLD, 0)]
        monkeypatch.setattr(report_lookup, "get_instances_by_form_id", lambda _fid: list(rows))
        statuses = {i["status"] for i in report_lookup.get_available_instances("4046")}
        assert statuses == {"11", "8", "0"}

    def test_status_flow_never_lands_in_an_explain_errors_stage(self, monkeypatch):
        """A status lookup that offers a dropdown must set STAGE_DATE, never
        one of the new stages."""
        guided._handle_action_selected("Check report status", self.SESSION)
        assert guided._guided_sessions[self.SESSION]["stage"] == guided.STAGE_STATUS_REPORT

        monkeypatch.setattr(
            report_lookup, "get_report_status",
            lambda _q: {
                "type": "date_selection", "return_name": "CIMS_RAQ", "form_id": "4046",
                "options": [report_lookup._fmt_instance_label(_DTC_NEW, "30-Jun-2026")],
                "available_instances": [_failed_entry(_DTC_NEW, status=11)],
            },
        )
        _run(guided.guided_step("CIMS_RAQ", self.SESSION, None))
        awaiting = agent._session_context.get(self.SESSION, {}).get("awaiting")
        assert awaiting not in (agent.STAGE_ERR_REPORT, agent.STAGE_ERR_INSTANCE)
