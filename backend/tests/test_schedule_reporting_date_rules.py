"""Scheduling date rules.

* Schedule date/time: must be in the future.
* Reporting date: must satisfy the return's frequency, may be in the past or
  the future, but must not be after the schedule date.
* Generate-instance is unchanged: its reporting date still cannot be future.
"""
from __future__ import annotations

import calendar
from datetime import date, timedelta

from backend.agent.scheduling import _finalize_schedule, _reporting_date_after_schedule
from backend.tools.instance_generator import validate_reporting_date

FMT = "%d-%b-%Y"


def _ret(freq):
    return {"form_id": "9999", "name": "Test Return", "frequency": freq, "period_name": ""}


def _month_end(d: date) -> date:
    return date(d.year, d.month, calendar.monthrange(d.year, d.month)[1])


def _next_month_end() -> date:
    first_next = _month_end(date.today()) + timedelta(days=1)
    return _month_end(first_next)


def _run(freq, rpt, sched, time="16:00"):
    return _finalize_schedule(
        _ret(freq), rpt, sched, time, None, session_id=None, login_id=None,
    )


class TestScheduleDate:
    def test_past_schedule_date_is_rejected(self):
        past = (date.today() - timedelta(days=3)).strftime(FMT)
        out = _run("D", (date.today() - timedelta(days=5)).strftime(FMT), past)
        assert out["result_type"] == "sched_awaiting_dt"

    def test_future_schedule_date_is_accepted(self):
        out = _run("D", date.today().strftime(FMT), (date.today() + timedelta(days=3)).strftime(FMT))
        assert out["result_type"] == "sched_confirm"


class TestReportingDateVsScheduleDate:
    def test_past_reporting_date_is_accepted(self):
        out = _run("D", (date.today() - timedelta(days=20)).strftime(FMT),
                   (date.today() + timedelta(days=2)).strftime(FMT))
        assert out["result_type"] == "sched_confirm"

    def test_future_reporting_date_before_schedule_date_is_accepted(self):
        out = _run("D", (date.today() + timedelta(days=4)).strftime(FMT),
                   (date.today() + timedelta(days=6)).strftime(FMT))
        assert out["result_type"] == "sched_confirm"

    def test_reporting_date_equal_to_schedule_date_is_rejected(self):
        d = (date.today() + timedelta(days=5)).strftime(FMT)
        out = _run("D", d, d)
        assert out["result_type"] == "sched_awaiting_rpt_date"
        assert "must be before the schedule date" in out["response_text"]

    def test_reporting_date_the_day_before_schedule_date_is_accepted(self):
        out = _run("D", (date.today() + timedelta(days=4)).strftime(FMT),
                   (date.today() + timedelta(days=5)).strftime(FMT))
        assert out["result_type"] == "sched_confirm"

    def test_reporting_date_after_schedule_date_is_rejected(self):
        out = _run("D", (date.today() + timedelta(days=9)).strftime(FMT),
                   (date.today() + timedelta(days=5)).strftime(FMT))
        assert out["result_type"] == "sched_awaiting_rpt_date"
        assert "must be before the schedule date" in out["response_text"]


class TestFrequencyStillApplies:
    def test_monthly_future_period_end_before_schedule_is_accepted(self):
        pe = _next_month_end()
        out = _run("M", pe.strftime(FMT), (pe + timedelta(days=3)).strftime(FMT))
        assert out["result_type"] == "sched_confirm"

    def test_monthly_future_date_that_is_not_month_end_is_rejected(self):
        pe = _next_month_end()
        bad = pe - timedelta(days=2)
        out = _run("M", bad.strftime(FMT), (pe + timedelta(days=3)).strftime(FMT))
        assert out["result_type"] == "sched_awaiting_rpt_date"

    def test_yearly_rule_rejects_a_non_31_mar_date(self):
        out = _run("Y", (date.today() + timedelta(days=2)).strftime("%d-%b-%Y")
                   if (date.today() + timedelta(days=2)).strftime("%d-%b") != "31-Mar" else "01-Jan-2030",
                   (date.today() + timedelta(days=9)).strftime(FMT))
        assert out["result_type"] == "sched_awaiting_rpt_date"


class TestHelpersAndGenerateUnchanged:
    def test_after_schedule_helper_suggests_period_ends_on_or_before_schedule(self):
        after, err, sugg = _reporting_date_after_schedule("30-Sep-2030", "31-Mar-2030", "Q")
        assert after and "must be before" in err
        assert sugg and sugg[0] == "31-Dec-2029" and "31-Mar-2030" not in sugg

    def test_helper_accepts_only_a_strictly_earlier_reporting_date(self):
        assert _reporting_date_after_schedule("30-Mar-2030", "31-Mar-2030", "D")[0] is False
        assert _reporting_date_after_schedule("31-Mar-2030", "31-Mar-2030", "Q")[0] is True
        assert _reporting_date_after_schedule("garbage", "31-Mar-2030", "Q")[0] is False

    def test_generate_mode_still_rejects_future_reporting_date(self):
        fut = (date.today() + timedelta(days=4)).strftime(FMT)
        res = validate_reporting_date(fut, "D")
        assert res["valid"] is False and "future" in res["error"].lower()

    def test_allow_future_accepts_it_for_scheduling(self):
        fut = (date.today() + timedelta(days=4)).strftime(FMT)
        assert validate_reporting_date(fut, "D", allow_future=True)["valid"] is True


class TestScheduleTimeWithSeconds:
    def test_hh_mm_ss_is_parsed_and_kept_in_the_iso_datetime(self):
        from backend.llm_extractor import extract_schedule_datetime
        r = extract_schedule_datetime("15-Oct-2030 at 16:05:30")
        assert r["schedule_time"] == "16:05:30"
        assert r["scheduled_datetime"] == "2030-10-15T16:05:30"

    def test_zero_seconds_keep_the_previous_hh_mm_form(self):
        from backend.llm_extractor import extract_schedule_datetime
        r = extract_schedule_datetime("15-Oct-2030 at 16:00:00")
        assert r["schedule_time"] == "16:00"
        assert r["scheduled_datetime"] == "2030-10-15T16:00:00"

    def test_existing_time_forms_are_unchanged(self):
        from backend.llm_extractor import extract_schedule_datetime
        assert extract_schedule_datetime("15-Oct-2030 at 4 PM")["schedule_time"] == "16:00"
        assert extract_schedule_datetime("15-Oct-2030 at 09:05")["scheduled_datetime"] == "2030-10-15T09:05:00"

    def test_schedule_time_with_seconds_is_accepted_for_a_future_date(self):
        d = (date.today() + timedelta(days=3)).strftime(FMT)
        out = _run("D", date.today().strftime(FMT), d, time="16:05:30")
        assert out["result_type"] == "sched_confirm"

    def test_today_with_a_seconds_time_compares_correctly(self):
        res = validate_reporting_date(date.today().strftime(FMT), "D", require_future=True,
                                      time_str="00:00:01", skip_frequency_check=True)
        assert res["valid"] is False   # earlier today


class TestReenteredReportingDateIsValidatedAgain:
    """After the 'must be before the schedule date' prompt the next input is
    validated afresh (frequency AND the schedule-date rule), keeping the
    schedule date and time already given."""

    SID = "sched-test-session"

    def _first_attempt(self, rpt, sched):
        from backend.agent.state import _session_context
        _session_context.pop(self.SID, None)
        out = _finalize_schedule(_ret("M"), rpt, sched, "16:00", None,
                                 session_id=self.SID, login_id=None)
        return out, _session_context.get(self.SID)

    def _retry(self, new_rpt):
        # what the router does for the STAGE_SCHED_RPT_DATE turn
        from backend.agent.state import _session_context
        s = _session_context.pop(self.SID)
        return _finalize_schedule(
            {"form_id": s["sched_form_id"], "name": s["sched_return_name"],
             "frequency": s["sched_frequency"], "period_name": s["sched_period_name"]},
            new_rpt, s["sched_schedule_date"], s["sched_schedule_time"], None,
            session_id=self.SID, login_id=None)

    def test_message_is_two_short_lines(self):
        sched = date.today() + timedelta(days=40)
        pe = _month_end(sched + timedelta(days=40))
        out, _ = self._first_attempt(pe.strftime(FMT), sched.strftime(FMT))
        assert out["response_text"] == (
            f"The reporting date **{pe.strftime(FMT)}** must be before the schedule date "
            f"**{sched.strftime(FMT)}**.\nPlease enter a reporting date before {sched.strftime(FMT)}")

    def test_retry_is_checked_against_the_frequency(self):
        sched = date.today() + timedelta(days=40)
        pe = _month_end(sched + timedelta(days=40))
        _, ctx = self._first_attempt(pe.strftime(FMT), sched.strftime(FMT))
        assert ctx["sched_schedule_date"] == sched.strftime(FMT) and ctx["sched_schedule_time"] == "16:00"
        not_month_end = (sched - timedelta(days=45)).replace(day=15)
        assert self._retry(not_month_end.strftime(FMT))["result_type"] == "sched_awaiting_rpt_date"

    def test_retry_is_checked_against_the_schedule_date_again(self):
        sched = date.today() + timedelta(days=40)
        pe = _month_end(sched + timedelta(days=40))
        self._first_attempt(pe.strftime(FMT), sched.strftime(FMT))
        later = _month_end(sched + timedelta(days=80))
        out = self._retry(later.strftime(FMT))
        assert out["result_type"] == "sched_awaiting_rpt_date"
        assert "must be before the schedule date" in out["response_text"]

    def test_valid_retry_goes_on_to_confirmation(self):
        sched = date.today() + timedelta(days=40)
        pe = _month_end(sched + timedelta(days=40))
        self._first_attempt(pe.strftime(FMT), sched.strftime(FMT))
        ok = _month_end(sched - timedelta(days=40))
        assert self._retry(ok.strftime(FMT))["result_type"] == "sched_confirm"
