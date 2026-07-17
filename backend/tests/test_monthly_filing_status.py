"""Tests for the MONTHLY_FILING_STATUS intent — per-return filed/not-filed
roll-up for a single calendar month, covering both XBRL and non-XBRL
returns ("what's my XBRL filing status for June 2025?", "what's the
non-XBRL status for this month?", "what dates are non-XBRL reports
expected in June 2025?").

Two layers:
  - Classifier-only tests (no XML data needed): verify intent detection,
    month/date-variation extraction, and xbrl_type detection across all
    the phrasings the feature request called out (explicit Month+Year,
    bare Month, relative month, natural-language connectors).
  - Handler tests against the real 5.5 data tree: verify the roll-up
    itself, and that authorization scoping (self vs department vs
    system_wide) matches the pattern already enforced for
    REPORTS_FILED_IN_RANGE / REPORTS_UPCOMING_IN_RANGE.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.db_qa.new_intent_classifier import classify_new, _extract_month_year, _DATE_RANGE_RE
from backend.db_qa.intents.taxonomy import Intent
from backend.agent import _fuzzy_has_status

PATH_5_5 = Path(r"D:\Repo(new)\DataBase")
_need_5_5 = pytest.mark.skipif(not PATH_5_5.is_dir(), reason="5.5 real data tree not present")


# ── Classifier: intent detection ────────────────────────────────────────────

class TestMonthlyFilingStatusIntentDetection:
    @pytest.mark.parametrize("q", [
        "What's my XBRL filing status for June 2025?",
        "What's my non-XBRL filing status for June 2025?",
        "What's the non-XBRL status for this month?",
        "What's my filing status for last month?",
        "What dates are non-XBRL reports expected in June 2025?",
        "What XBRL reports are expected in June 2025?",
        "What's my status for next month?",
        "filing status for June 2025",
        "What is my filing status for the current month?",
    ])
    def test_matches_monthly_filing_status(self, q):
        intent, params, target_type = classify_new(q)
        assert intent == Intent.MONTHLY_FILING_STATUS, f"{q!r} -> {intent}"

    def test_range_question_not_hijacked(self):
        # A genuine two-date range question (mentions a month inside a
        # date token) must still resolve to REPORTS_FILED_IN_RANGE, not
        # MONTHLY_FILING_STATUS — rule order in _NEW_RULES is what
        # prevents this collision.
        intent, params, target_type = classify_new(
            "Show me all XBRL reports filed between 01-Jun-2025 and 31-Aug-2025."
        )
        assert intent == Intent.REPORTS_FILED_IN_RANGE

    def test_upcoming_range_question_not_hijacked(self):
        intent, params, target_type = classify_new(
            "What XBRL reports are coming up between 01-Jun-2025 and 31-Aug-2025."
        )
        assert intent == Intent.REPORTS_UPCOMING_IN_RANGE

    def test_bare_filing_word_with_possessive_still_matches(self):
        # "my/our ... filing for <month>" with no "status" word at all —
        # a real phrasing a user tried that the original patterns missed.
        intent, params, target_type = classify_new(
            "What's my non-XBRL filing for June 2025?"
        )
        assert intent == Intent.MONTHLY_FILING_STATUS
        assert params.get("month_year") == "June 2025"

    @pytest.mark.parametrize("q", [
        "generate CIMS_RAQ filing for 31 march 2026",
        "schedule filing for CIMS_RAQ on 31 march 2026 at 10am",
    ])
    def test_bare_filing_word_does_not_hijack_single_report_requests(self, q):
        # The "my/our ... filing for <month>" pattern must stay narrow —
        # single-report generate/schedule requests that happen to name a
        # date near the word "filing" are NOT monthly-status questions.
        intent, params, target_type = classify_new(q)
        assert intent != Intent.MONTHLY_FILING_STATUS, f"{q!r} -> {intent}"


class TestMonthlyFilingStatusTargetType:
    def test_system_wide_wording_with_intervening_qualifier(self):
        # "status system-wide for <month>" — a qualifier phrase sits
        # between "status" and "for", the same adjacency gap that once
        # broke REPORTS_FILED_IN_RANGE/REPORTS_UPCOMING_IN_RANGE.
        intent, params, target_type = classify_new(
            "What's my XBRL filing status system-wide for March 2026?"
        )
        assert intent == Intent.MONTHLY_FILING_STATUS
        assert target_type == "system_wide"

    def test_named_department_does_not_swallow_trailing_month_clause(self):
        intent, params, target_type = classify_new(
            "What's the non-XBRL status for department Compliance for March 2026?"
        )
        assert intent == Intent.MONTHLY_FILING_STATUS
        assert target_type == "department"
        assert params.get("target_department") == "Compliance"
        assert params.get("month_year") == "March 2026"

    @pytest.mark.parametrize("q", [
        "What's my status during March 2026?",
        "What's my status in March 2026?",
    ])
    def test_during_and_in_connectors_not_hijacked_by_submission_status(self, q):
        # "status during/in <month>" once fell through to
        # MY_SUBMISSION_HISTORY via LLM disambiguation because the
        # MONTHLY_FILING_STATUS patterns only recognised "status ... for",
        # not "during"/"in" without a preceding literal "filing".
        intent, params, target_type = classify_new(q)
        assert intent == Intent.MONTHLY_FILING_STATUS
        assert params.get("month_year") == "March 2026"

    def test_submission_status_questions_still_win_over_monthly_status(self):
        intent, params, target_type = classify_new("status of my submission")
        assert intent == Intent.SUBMISSION_STATUS


# ── Classifier: xbrl_type extraction ────────────────────────────────────────

class TestMonthlyFilingStatusXbrlType:
    def test_xbrl_type_detected(self):
        _, params, _ = classify_new("What's my XBRL filing status for June 2025?")
        assert params.get("xbrl_type") == "xbrl"

    @pytest.mark.parametrize("q", [
        "What's my non-XBRL filing status for June 2025?",
        "What's my non XBRL filing status for June 2025?",
        "What's my nonxbrl filing status for June 2025?",
        "What's my NX filing status for June 2025?",
    ])
    def test_non_xbrl_type_detected_regardless_of_separator(self, q):
        _, params, _ = classify_new(q)
        assert params.get("xbrl_type") == "non_xbrl", q

    def test_no_type_means_both(self):
        _, params, _ = classify_new("What's my filing status for June 2025?")
        assert params.get("xbrl_type") is None


# ── Classifier: month/date-variation extraction ─────────────────────────────

class TestExtractMonthYear:
    def test_explicit_month_year_full_name(self):
        assert _extract_month_year("status for June 2025") == "June 2025"

    def test_explicit_month_year_abbreviated(self):
        assert _extract_month_year("status for Jun 2025") == "Jun 2025"

    def test_this_month(self):
        today = date.today()
        assert _extract_month_year("status for this month") == today.strftime("%B %Y")

    def test_current_month(self):
        today = date.today()
        assert _extract_month_year("status for the current month") == today.strftime("%B %Y")

    def test_last_month(self):
        today = date.today()
        year, month = (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)
        assert _extract_month_year("status for last month") == date(year, month, 1).strftime("%B %Y")

    def test_previous_month(self):
        today = date.today()
        year, month = (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)
        assert _extract_month_year("status for the previous month") == date(year, month, 1).strftime("%B %Y")

    def test_next_month(self):
        today = date.today()
        year, month = (today.year + 1, 1) if today.month == 12 else (today.year, today.month + 1)
        assert _extract_month_year("status for next month") == date(year, month, 1).strftime("%B %Y")

    def test_bare_month_defaults_to_current_year(self):
        today = date.today()
        assert _extract_month_year("status for June") == f"June {today.year}"

    def test_bare_year_alone_not_resolved(self):
        # A whole-year question isn't a single-month status question —
        # returning None here lets the handler's own "please specify a
        # month" message fire instead of guessing a month.
        assert _extract_month_year("filing status for 2025") is None

    def test_natural_language_connectors(self):
        assert _extract_month_year("during June 2025") == "June 2025"
        assert _extract_month_year("in June 2025") == "June 2025"
        assert _extract_month_year("for the month of June 2025") == "June 2025"

    def test_no_date_at_all(self):
        assert _extract_month_year("what's my filing status") is None


# ── Handler: roll-up + authorization, against real data ─────────────────────

class TestMonthlyFilingStatusNotHijackedByStatusWorkflowGate:
    """Regression test for a real bug: backend.agent.decide()'s STEP-1
    "_has_workflow" gate treats any _fuzzy_has_status() match as a
    single-report get_status workflow request UNLESS an override excludes
    it — _has_date_range already excludes two-date range questions this
    way. Monthly-status questions ("filing status for June 2025") also
    trip _fuzzy_has_status (the word "status") but have no two-date range
    for _has_date_range to catch, so before the fix every one of them was
    incorrectly sent into the single-report status workflow (which then
    either fuzzy-matched an unrelated report name or failed with "You are
    not authorised to access this report") instead of ever reaching DB Q&A.

    decide() computes its own _has_monthly_status override the same way
    this test does: `classify_new(q)[0] == Intent.MONTHLY_FILING_STATUS`.
    This test asserts the PRECONDITION the override depends on — that
    _fuzzy_has_status is True (so the old code path really would have
    misfired) AND classify_new correctly identifies MONTHLY_FILING_STATUS
    (so the override correctly fires) — for every phrasing in the bug
    report, without needing to invoke the full decide() pipeline (which
    requires live session/auth/XML-store setup).
    """

    @pytest.mark.parametrize("q", [
        "What's my non-XBRL filing status for June 2025?",
        "what is xbrl filing status for this month",
        "what is xbrl returns filing status for june",
        "What's my XBRL filing status for June 2025?",
    ])
    def test_status_gate_would_have_misfired_without_override(self, q):
        # "What's my non-XBRL filing for June 2025?" (no "status" word) is
        # deliberately excluded here — it never trips _fuzzy_has_status in
        # the first place, so it was never at risk from THIS gate; its bug
        # was a separate, already-covered classifier-regex gap (see
        # test_bare_filing_word_with_possessive_still_matches above).
        assert _fuzzy_has_status(q), f"{q!r} no longer trips _fuzzy_has_status — override may be dead code now"

    @pytest.mark.parametrize("q", [
        "What's my non-XBRL filing status for June 2025?",
        "what is xbrl filing status for this month",
        "what is xbrl returns filing status for june",
        "What's my XBRL filing status for June 2025?",
        "What's my non-XBRL filing for June 2025?",
    ])
    def test_override_correctly_identifies_monthly_status(self, q):
        intent, _, _ = classify_new(q)
        assert intent == Intent.MONTHLY_FILING_STATUS, f"{q!r} -> {intent}"
        # And never a two-date range (which uses the OTHER override) —
        # confirms these two overrides are non-overlapping.
        assert not _DATE_RANGE_RE.search(q)


@_need_5_5
class TestMonthlyFilingStatusHandler:
    @pytest.fixture
    def store(self):
        from backend.db_qa.xml_store import XMLStore
        return XMLStore(str(PATH_5_5))

    def test_self_scope_returns_department_rollup(self, store):
        from backend.db_qa.query_handlers.return_handlers import handle_monthly_filing_status

        scope = {"target_type": "self", "login_id": "test810", "user_id": None}
        entities = {"month_year": "March 2026", "xbrl_type": "xbrl"}
        result = handle_monthly_filing_status(scope, entities, store)
        assert result["intent"] == "monthly_filing_status"
        assert "count" in result["meta"]

    def test_missing_month_gives_helpful_message(self, store):
        from backend.db_qa.query_handlers.return_handlers import handle_monthly_filing_status

        scope = {"target_type": "self", "login_id": "test810", "user_id": None}
        result = handle_monthly_filing_status(scope, {}, store)
        assert result["found"] is False
        assert "month" in result["summary"].lower()

    def test_system_wide_scope_aggregates_across_departments(self, store):
        from backend.db_qa.query_handlers.return_handlers import handle_monthly_filing_status

        scope = {"target_type": "system_wide", "login_id": "iris810", "user_id": None}
        entities = {"month_year": "March 2026", "xbrl_type": "xbrl"}
        result = handle_monthly_filing_status(scope, entities, store)
        assert "all departments" in result["summary"]

    def test_department_scope_uses_named_department(self, store):
        from backend.db_qa.query_handlers.return_handlers import handle_monthly_filing_status

        depts = store.departments()
        assert depts, "no departments in test data"
        dept_name = depts[0].get("Name", "")
        scope = {"target_type": "department", "login_id": "iris810", "user_id": None}
        entities = {"month_year": "March 2026", "target_department": dept_name}
        result = handle_monthly_filing_status(scope, entities, store)
        assert dept_name in result["summary"]


@_need_5_5
class TestMonthlyFilingStatusAuthorization:
    """Non-admins may only ask about their own department; admins may ask
    about any named department or system-wide — same rule already enforced
    for REPORTS_FILED_IN_RANGE/REPORTS_UPCOMING_IN_RANGE via
    access_control.scope_query's TARGET_TYPES_REQUIRING_ADMIN."""

    def test_non_admin_denied_system_wide(self):
        from backend.db_qa import access_control

        with pytest.raises(PermissionError):
            access_control.scope_query(
                {"login_id": "test810"}, Intent.MONTHLY_FILING_STATUS.value,
                {"target_type": "system_wide"},
            )

    def test_non_admin_denied_named_department(self):
        from backend.db_qa import access_control

        with pytest.raises(PermissionError):
            access_control.scope_query(
                {"login_id": "test810"}, Intent.MONTHLY_FILING_STATUS.value,
                {"target_type": "department"},
            )

    def test_non_admin_allowed_self(self):
        from backend.db_qa import access_control

        scope = access_control.scope_query(
            {"login_id": "test810"}, Intent.MONTHLY_FILING_STATUS.value,
            {"target_type": "self"},
        )
        assert scope["target_type"] == "self"

    def test_admin_allowed_system_wide(self):
        from backend.db_qa import access_control

        scope = access_control.scope_query(
            {"login_id": "iris810"}, Intent.MONTHLY_FILING_STATUS.value,
            {"target_type": "system_wide"},
        )
        assert scope["target_type"] == "system_wide"
        assert scope["is_admin"] is True


@_need_5_5
class TestMonthlyFilingStatusTableDisplay:
    """Regression test for a real bug: the chat table renderer
    (backend.agent.db_qa_router._select_cols/_build_db_qa_data) restricts
    displayed columns to a fixed _PRIORITY_COLS allowlist tailored to
    user/department/role records. Since Frequency/ExpectedDate/Filed/
    FiledOn weren't in that allowlist, _select_cols returned only
    ["ReturnName"] (the one column that WAS on the allowlist) instead of
    falling back to all-columns, so the whole per-return filed/not-filed
    roll-up rendered as a bare list of return names with no way to tell
    which ones were filed — exactly what "what is the status of cims for
    june 2026?" showed: 21 rows, only 2 marked filed in the summary
    sentence, with no per-row indication of which 2.

    Also covers a second, related bug: even once Filed reached the table,
    _fmt_val's generic true/false -> Active/Inactive mapping would have
    rendered an unfiled return as "Inactive" (implying the return itself
    is disabled) rather than "Not Filed".
    """

    def test_all_five_columns_survive_to_the_table(self):
        from backend.agent.db_qa_router import _build_db_qa_data
        from backend.db_qa.query_handlers.return_handlers import handle_monthly_filing_status
        from backend.db_qa.xml_store import XMLStore
        from backend.db_qa import access_control

        store = XMLStore(str(PATH_5_5))
        scope = access_control.scope_query(
            {"login_id": "iris810"}, Intent.MONTHLY_FILING_STATUS.value, {"target_type": "self"},
        )
        result = handle_monthly_filing_status(scope, {"month_year": "June 2026"}, store)
        assert result["found"], "expected data present in test tree for iris810/June 2026"

        data = _build_db_qa_data(result, intent="monthly_filing_status")
        assert data["cols"] == ["ReturnName", "Frequency", "ExpectedDate", "Filed", "FiledOn"]
        assert data["headers"] == ["Return", "Frequency", "Expected Date", "Filed", "Filed On"]

    def test_filed_renders_as_filed_not_filed_not_active_inactive(self):
        from backend.agent.db_qa_router import _build_db_qa_data
        from backend.db_qa.query_handlers.return_handlers import handle_monthly_filing_status
        from backend.db_qa.xml_store import XMLStore
        from backend.db_qa import access_control

        store = XMLStore(str(PATH_5_5))
        scope = access_control.scope_query(
            {"login_id": "iris810"}, Intent.MONTHLY_FILING_STATUS.value, {"target_type": "self"},
        )
        result = handle_monthly_filing_status(scope, {"month_year": "June 2026"}, store)
        data = _build_db_qa_data(result, intent="monthly_filing_status")

        filed_values = {r["Filed"] for r in data["records"]}
        assert filed_values <= {"Filed", "Not Filed"}
        assert "Active" not in filed_values and "Inactive" not in filed_values
        # At least one of each, given the known iris810/June 2026 fixture
        # data has both filed (CIMS_MPD06, CIMS_RAQ) and unfiled returns.
        assert "Filed" in filed_values
        assert "Not Filed" in filed_values
