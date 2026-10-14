"""Scheduling date rules.

* Schedule date/time: must be in the future.
* Reporting date: must satisfy the return's frequency, may be in the past or
  the future, but must not be after the schedule date.
* Generate-instance is unchanged: its reporting date still cannot be future.
"""
from __future__ import annotations

import calendar
from datetime import date, timedelta

import pytest

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
        # the three latest quarter-ends before 31-Mar-2030, oldest first
        assert sugg == ["30-Jun-2029", "30-Sep-2029", "31-Dec-2029"]

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
            f"**{sched.strftime(FMT)}**.\nPlease enter or choose a reporting date before **{sched.strftime(FMT)}**")

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


class TestSuggestedReportingDates:
    """Three frequency-valid reporting dates, strictly before the schedule date."""

    SCHEDULE = date(2026, 12, 15)
    ALL_FREQS = ["D", "W", "F", "M", "Q", "H", "C", "Y", "A", "B", "G", "HM", "Z", ""]

    def _suggest(self, freq, schedule=None):
        from backend.agent.scheduling import _suggest_reporting_dates_before
        return _suggest_reporting_dates_before(schedule or self.SCHEDULE, freq)

    def test_daily_example_from_the_requirements(self):
        assert self._suggest("D") == ["12-Dec-2026", "13-Dec-2026", "14-Dec-2026"]

    def test_weekly_gives_the_last_three_fridays(self):
        assert self._suggest("W") == ["27-Nov-2026", "04-Dec-2026", "11-Dec-2026"]

    def test_monthly_gives_the_last_three_month_ends(self):
        assert self._suggest("M") == ["30-Sep-2026", "31-Oct-2026", "30-Nov-2026"]

    def test_fortnightly_gives_15th_and_month_end_dates(self):
        assert self._suggest("F") == ["31-Oct-2026", "15-Nov-2026", "30-Nov-2026"]

    def test_quarterly_half_yearly_and_yearly_use_their_period_ends(self):
        assert self._suggest("Q") == ["31-Mar-2026", "30-Jun-2026", "30-Sep-2026"]
        assert self._suggest("H") == ["30-Sep-2025", "31-Mar-2026", "30-Sep-2026"]
        assert self._suggest("C") == ["30-Jun-2025", "31-Dec-2025", "30-Jun-2026"]
        assert self._suggest("Y") == ["31-Mar-2024", "31-Mar-2025", "31-Mar-2026"]
        assert self._suggest("B") == ["31-Dec-2023", "31-Dec-2024", "31-Dec-2025"]

    def test_every_frequency_gives_three_unique_valid_dates_before_the_schedule(self):
        from backend.tools.instance_generator import parse_date_flexible
        for freq in self.ALL_FREQS:
            sugg = self._suggest(freq)
            assert len(sugg) == 3, freq
            assert len(set(sugg)) == 3, freq
            assert sugg == sorted(sugg, key=parse_date_flexible), freq
            for ds in sugg:
                assert parse_date_flexible(ds) < self.SCHEDULE, (freq, ds)
                assert validate_reporting_date(ds, freq, allow_future=True)["valid"], (freq, ds)

    def test_a_date_equal_to_the_schedule_date_is_never_suggested(self):
        # Yearly return scheduled on its own period end: that date is excluded.
        assert "31-Mar-2026" not in self._suggest("Y", date(2026, 3, 31))
        assert self._suggest("Y", date(2026, 3, 31)) == ["31-Mar-2023", "31-Mar-2024", "31-Mar-2025"]

    def test_boundaries_across_month_and_year_ends_and_leap_days(self):
        assert self._suggest("D", date(2027, 1, 1)) == ["29-Dec-2026", "30-Dec-2026", "31-Dec-2026"]
        assert self._suggest("D", date(2028, 3, 1)) == ["27-Feb-2028", "28-Feb-2028", "29-Feb-2028"]

    def test_suggestions_follow_the_schedule_date(self):
        assert self._suggest("D", date(2027, 6, 10)) == ["07-Jun-2027", "08-Jun-2027", "09-Jun-2027"]

    def test_the_validation_message_is_unchanged_and_options_carry_the_suggestions(self):
        sched = date.today() + timedelta(days=30)
        out = _finalize_schedule(
            _ret("D"), (sched + timedelta(days=5)).strftime(FMT), sched.strftime(FMT), "16:00", None,
            session_id=None, login_id=None,
        )
        rpt = (sched + timedelta(days=5)).strftime(FMT)
        assert out["result_type"] == "sched_awaiting_rpt_date"
        assert out["response_text"] == (
            f"The reporting date **{rpt}** must be before the schedule date "
            f"**{sched.strftime(FMT)}**.\nPlease enter or choose a reporting date before **{sched.strftime(FMT)}**")
        assert out["options"] == [(sched - timedelta(days=n)).strftime(FMT) for n in (3, 2, 1)]

    def test_a_reporting_date_equal_to_the_schedule_date_also_gets_suggestions(self):
        sched = date.today() + timedelta(days=30)
        out = _finalize_schedule(
            _ret("D"), sched.strftime(FMT), sched.strftime(FMT), "16:00", None,
            session_id=None, login_id=None,
        )
        assert out["result_type"] == "sched_awaiting_rpt_date"
        assert len(out["options"]) == 3


class TestSelectingASuggestedDate:
    """Clicking a suggestion sends its text as the next reporting-date input;
    the flow validates it like any typed date and then moves on."""

    SID = "sched-suggest-session"

    def _flow(self, freq, schedule_offset=40):
        from backend.agent.state import _session_context
        _session_context.pop(self.SID, None)
        sched = date.today() + timedelta(days=schedule_offset)
        first = _finalize_schedule(
            _ret(freq), (sched + timedelta(days=60)).strftime(FMT), sched.strftime(FMT), "16:00",
            None, session_id=self.SID, login_id=None,
        )
        return sched, first, _session_context.pop(self.SID)

    def _pick(self, ctx, text):
        return _finalize_schedule(
            {"form_id": ctx["sched_form_id"], "name": ctx["sched_return_name"],
             "frequency": ctx["sched_frequency"], "period_name": ctx["sched_period_name"]},
            text, ctx["sched_schedule_date"], ctx["sched_schedule_time"], None,
            session_id=None, login_id=None,
        )

    def test_every_suggestion_for_every_frequency_is_accepted_when_picked(self):
        for freq in ["D", "W", "F", "M", "Q", "H", "C", "Y", "B", "G"]:
            _, first, ctx = self._flow(freq)
            assert len(first["options"]) == 3, freq
            for choice in first["options"]:
                assert self._pick(ctx, choice)["result_type"] == "sched_confirm", (freq, choice)

    def test_manual_entry_of_another_valid_date_still_works(self):
        sched, _, ctx = self._flow("D")
        manual = (sched - timedelta(days=20)).strftime(FMT)
        assert self._pick(ctx, manual)["result_type"] == "sched_confirm"

    def test_manual_entry_of_an_invalid_date_is_still_rejected_with_suggestions(self):
        sched, _, ctx = self._flow("M")
        not_month_end = (sched - timedelta(days=45)).replace(day=15).strftime(FMT)
        out = self._pick(ctx, not_month_end)
        assert out["result_type"] == "sched_awaiting_rpt_date"

    def test_the_schedule_date_and_time_are_kept_while_choosing(self):
        sched, _, ctx = self._flow("D")
        assert ctx["sched_schedule_date"] == sched.strftime(FMT)
        assert ctx["sched_schedule_time"] == "16:00"


class TestFrequencyInvalidDateGetsSuggestionsToo:
    def test_weekly_non_friday_with_a_known_schedule_date_gets_three_fridays(self):
        sched = date.today() + timedelta(days=30)
        d = sched - timedelta(days=10)
        while d.weekday() == 4:                       # make sure it is NOT a Friday
            d -= timedelta(days=1)
        out = _finalize_schedule(_ret("W"), d.strftime(FMT), sched.strftime(FMT), "16:00", None,
                                 session_id=None, login_id=None)
        assert out["result_type"] == "sched_awaiting_rpt_date"
        assert "Friday" in out["response_text"]          # the frequency message is unchanged
        assert len(out["options"]) == 3
        from backend.tools.instance_generator import parse_date_flexible
        for ds in out["options"]:
            assert parse_date_flexible(ds).weekday() == 4 and parse_date_flexible(ds) < sched

    def test_without_a_schedule_date_the_frequency_suggestions_are_untouched(self):
        pe = _next_month_end()
        bad = (pe - timedelta(days=2)).strftime(FMT)
        out = _finalize_schedule(_ret("M"), bad, None, None, None, session_id=None, login_id=None)
        expected = [s for s in validate_reporting_date(bad, "M", allow_future=True)["suggestions"]
                    if s.lower() != bad.lower()]
        assert out["result_type"] == "sched_awaiting_rpt_date"
        assert (out.get("options") or []) == expected


class TestReportingDatePrompt:
    """Scheduling accepts past AND future reporting dates (only before the schedule
    date), so its prompt must not say Daily reports accept "past" dates only.
    Generate-instance keeps its wording."""

    def test_scheduling_prompt_for_daily_has_no_past_only_sentence(self):
        out = _finalize_schedule(_ret("D"), None, None, None, None, session_id=None, login_id=None)
        assert out["result_type"] == "sched_awaiting_rpt_date"
        assert "past" not in out["response_text"].lower()
        assert out["response_text"].startswith("Please enter the reporting date for **Test Return**.")
        assert "Example:" in out["response_text"]

    def test_generate_prompt_for_daily_is_unchanged(self):
        from backend.agent.generation import _date_ask_prompt
        assert "Daily reports accept any valid past date." in _date_ask_prompt("X", "D", "Daily")

    def test_every_other_frequency_prompt_is_identical_for_scheduling_and_generation(self):
        from backend.agent.generation import _date_ask_prompt
        # Daily and Weekly are the only prompts with a past-only line; the rest are shared as is.
        for f in ["Q", "M", "H", "C", "Y", "B", "F", "HM", "E", ""]:
            assert _date_ask_prompt("X", f, "P") == _date_ask_prompt("X", f, "P", allow_future=True), f


class TestSchedulingNeverSteersTowardPastDatesOnly:
    def test_weekly_scheduling_example_does_not_say_past_but_generation_still_does(self):
        from backend.agent.generation import _date_ask_prompt
        assert "past" not in _date_ask_prompt("X", "W", "Weekly", allow_future=True).lower()
        assert "Example: the nearest past Friday." in _date_ask_prompt("X", "W", "Weekly")
        assert "Example: the nearest Friday." in _date_ask_prompt("X", "W", "Weekly", allow_future=True)

    def test_no_scheduling_prompt_for_any_frequency_mentions_past_dates(self):
        from backend.agent.generation import _date_ask_prompt
        for f in ["D", "W", "F", "M", "Q", "H", "C", "Y", "B", "HM", "E", ""]:
            assert "past" not in _date_ask_prompt("X", f, "P", allow_future=True).lower(), f

    def test_suggestions_after_a_mistyped_date_include_future_dates_when_scheduling(self):
        cur_end = _month_end(date.today())
        if cur_end <= date.today():
            pytest.skip("this month's end is not in the future today")
        sched = validate_reporting_date("not a date", "M", allow_future=True)["suggestions"]
        gen = validate_reporting_date("not a date", "M")["suggestions"]
        assert cur_end.strftime(FMT) in sched          # scheduling may use this month's end
        assert cur_end.strftime(FMT) not in gen        # generate-instance still may not

    def test_a_mistyped_reporting_date_in_scheduling_is_offered_future_valid_dates(self):
        cur_end = _month_end(date.today())
        if cur_end <= date.today():
            pytest.skip("this month's end is not in the future today")
        out = _finalize_schedule(_ret("M"), "31-13-2026", None, None, None, session_id=None, login_id=None)
        assert out["result_type"] == "sched_awaiting_rpt_date"
        assert cur_end.strftime(FMT) in (out.get("options") or [])
