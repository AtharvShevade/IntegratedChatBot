"""Regression tests for Schedule Report date validation (instance_generator.py).

Covers two bugs reported after the 6.0 migration:

1. Frequency validation was silently skipped for some Yearly (and
   potentially other) reports because 6.0's Period.xml carries no
   Frequency attribute — resolution fell back to the return's own
   RepFreq field, which uses inconsistent codes across returns sharing
   the same PeriodId (e.g. 'A' vs 'Y' both appear under PeriodId 107
   "Yearly"). 'A' isn't a code the validator recognises, so it fell
   through to the unrestricted catch-all and accepted any date.
   Fixed via _PERIOD_ID_TO_FREQUENCY, a version-stable PeriodId->Frequency
   fallback sourced from 5.5's own (correct) Period.xml mapping.

2. Schedule Date used a separate, less capable validator
   (_validate_future_schedule_date) that only tried a single strptime
   format and had no frequency check at all — any structurally-unparsable
   date (including calendar-invalid ones like 31-Nov-2026, which
   strptime also rejects) surfaced a generic "Cannot parse" message
   instead of a specific "not a valid calendar date" explanation, and
   any future date was accepted regardless of frequency. Fixed by
   having _validate_future_schedule_date delegate to
   validate_reporting_date(require_future=True), so both dates share
   one implementation.
"""
from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from datetime import date, timedelta
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.tools.instance_generator import validate_reporting_date, resolve_return_exact
from backend.agent import _validate_future_schedule_date

PATH_5_5 = Path(r"D:\Repo(new)\DataBase")
PATH_6_0_1001 = Path(r"D:\Repo6\Repo6\1001\DataBase")

_need_5_5 = pytest.mark.skipif(not PATH_5_5.is_dir(), reason="5.5 real data tree not present")
_need_6_0_1001 = pytest.mark.skipif(not PATH_6_0_1001.is_dir(), reason="6.0 tenant 1001 real data tree not present")


def _future_year() -> int:
    """A year far enough ahead that frequency-valid dates in it are
    guaranteed future, regardless of when this test runs."""
    return date.today().year + 2


def _past_year() -> int:
    return date.today().year - 2


# ── Issue 1: frequency validation for Reporting Date (all frequencies) ──────

class TestReportingDateFrequencyValidation:
    def test_quarterly_accepts_quarter_end_dates(self):
        y = _past_year()
        for d in (f"31-Mar-{y}", f"30-Jun-{y}", f"30-Sep-{y}", f"31-Dec-{y}"):
            assert validate_reporting_date(d, "Q")["valid"] is True, d

    def test_quarterly_rejects_non_quarter_end(self):
        y = _past_year()
        result = validate_reporting_date(f"15-Mar-{y}", "Q")
        assert result["valid"] is False
        assert "quarter-end" in result["error"]

    def test_monthly_accepts_last_day_of_month(self):
        y = _past_year()
        result = validate_reporting_date(f"30-Apr-{y}", "M")
        assert result["valid"] is True

    def test_monthly_rejects_non_last_day(self):
        y = _past_year()
        result = validate_reporting_date(f"15-Apr-{y}", "M")
        assert result["valid"] is False
        assert "last day" in result["error"]

    def test_half_yearly_financial_year_accepts_mar_sep(self):
        y = _past_year()
        assert validate_reporting_date(f"31-Mar-{y}", "H")["valid"] is True
        assert validate_reporting_date(f"30-Sep-{y}", "H")["valid"] is True

    def test_half_yearly_financial_year_rejects_jun_dec(self):
        y = _past_year()
        result = validate_reporting_date(f"30-Jun-{y}", "H")
        assert result["valid"] is False
        assert "Half-Yearly" in result["error"]

    def test_half_yearly_calendar_year_accepts_jun_dec(self):
        y = _past_year()
        assert validate_reporting_date(f"30-Jun-{y}", "C")["valid"] is True
        assert validate_reporting_date(f"31-Dec-{y}", "C")["valid"] is True

    def test_yearly_financial_year_accepts_only_31_mar(self):
        y = _past_year()
        assert validate_reporting_date(f"31-Mar-{y}", "Y")["valid"] is True

    def test_yearly_financial_year_rejects_non_31_mar(self):
        y = _past_year()
        result = validate_reporting_date(f"30-Nov-{y}", "Y")
        assert result["valid"] is False
        assert "Yearly" in result["error"]

    def test_yearly_calendar_year_accepts_only_31_dec(self):
        y = _past_year()
        assert validate_reporting_date(f"31-Dec-{y}", "B")["valid"] is True
        result = validate_reporting_date(f"30-Jun-{y}", "B")
        assert result["valid"] is False


# ── Root-cause regression: RepFreq 'A' under PeriodId 107 ("Yearly") ────────

class TestPeriodIdFrequencyFallback:
    """The actual bug: a 6.0 return with RepFreq='A' under PeriodId 107
    ("Yearly") must resolve to frequency 'Y' (financial-year, 31-Mar),
    same as every other return sharing that PeriodId — not fall through
    to the unrestricted "any date accepted" catch-all."""

    def test_rep_freq_a_resolves_to_yearly_not_unrestricted(self):
        from backend.tools.instance_generator import _PERIOD_ID_TO_FREQUENCY
        assert _PERIOD_ID_TO_FREQUENCY["107"] == "Y"

    def test_yearly_return_with_repfreq_a_rejects_invalid_date(self):
        """Simulates resolve_return_exact's fallback chain directly: when
        Period.xml has no Frequency attribute (6.0) and RepFreq='A', the
        PeriodId fallback must still produce a frequency-validated 'Y',
        not let 'A' fall through unrecognised."""
        from backend.tools.instance_generator import _PERIOD_ID_TO_FREQUENCY
        frequency = (None or _PERIOD_ID_TO_FREQUENCY.get("107") or "A" or "").strip().upper()
        assert frequency == "Y"
        y = _past_year()
        result = validate_reporting_date(f"30-Nov-{y}", frequency)
        assert result["valid"] is False


# ── Issue 1: frequency validation for Schedule Date (all frequencies) ───────

class TestScheduleDateFrequencyValidation:
    def test_quarterly_schedule_accepts_future_quarter_end(self):
        y = _future_year()
        valid, err = _validate_future_schedule_date(f"31-Dec-{y}", None, "Q")
        assert valid is True, err

    def test_quarterly_schedule_rejects_future_non_quarter_end(self):
        y = _future_year()
        valid, err = _validate_future_schedule_date(f"15-Dec-{y}", None, "Q")
        assert valid is False
        assert "quarter-end" in err

    def test_yearly_schedule_accepts_future_31_mar(self):
        y = _future_year()
        valid, err = _validate_future_schedule_date(f"31-Mar-{y}", None, "Y")
        assert valid is True, err

    def test_yearly_schedule_rejects_future_30_nov(self):
        """Exact scenario from the bug report: a Yearly report must not
        accept 30-Nov as a schedule date."""
        y = _future_year()
        valid, err = _validate_future_schedule_date(f"30-Nov-{y}", None, "Y")
        assert valid is False
        assert "Yearly" in err

    def test_half_yearly_schedule_rejects_wrong_month(self):
        y = _future_year()
        valid, err = _validate_future_schedule_date(f"30-Nov-{y}", None, "H")
        assert valid is False

    def test_monthly_schedule_rejects_non_last_day(self):
        y = _future_year()
        valid, err = _validate_future_schedule_date(f"15-Jun-{y}", None, "M")
        assert valid is False
        assert "last day" in err

    def test_schedule_date_still_rejects_past_dates(self):
        y = _past_year()
        valid, err = _validate_future_schedule_date(f"31-Mar-{y}", None, "Y")
        assert valid is False
        assert "future" in err.lower()


# ── Issue 2: invalid calendar date message (vs "Cannot parse") ──────────────

class TestInvalidCalendarDateMessages:
    @pytest.mark.parametrize("bad_date,month_name", [
        ("31-Nov-2026", "November"),
        ("30-Feb-2026", "February"),
        ("29-Feb-2025", "February"),  # 2025 is not a leap year
    ])
    def test_reporting_date_gives_calendar_explanation_not_cannot_parse(self, bad_date, month_name):
        result = validate_reporting_date(bad_date, "Q")
        assert result["valid"] is False
        assert "Cannot parse" not in result["error"]
        assert "not a valid calendar date" in result["error"]
        assert month_name in result["error"]

    @pytest.mark.parametrize("bad_date", [
        "31-Nov-2026",
        "30-Feb-2026",
        "29-Feb-2025",
    ])
    def test_schedule_date_gives_calendar_explanation_not_cannot_parse(self, bad_date):
        valid, err = _validate_future_schedule_date(bad_date, None, "Q")
        assert valid is False
        assert "Cannot parse" not in err
        assert "not a valid calendar date" in err

    def test_29_feb_leap_year_is_accepted(self):
        """29-Feb IS a real calendar date in a leap year — must be accepted
        (frequency rules may still reject it for Q/M/Y/H, but it must not
        be flagged as calendar-invalid). Picks the most recent past leap
        year so the date is never rejected as "future" instead."""
        y = _past_year()
        leap_year = next(yr for yr in range(y, y - 8, -1) if yr % 4 == 0 and (yr % 100 != 0 or yr % 400 == 0))
        result = validate_reporting_date(f"29-Feb-{leap_year}", "D")
        assert result["valid"] is True

    def test_genuinely_unparsable_input_still_says_cannot_parse(self):
        for bad in ("not a date", "banana", "abc-def-ghij"):
            result = validate_reporting_date(bad, "Q")
            assert result["valid"] is False
            assert "Cannot parse" in result["error"], bad

    def test_genuinely_unparsable_schedule_date_still_says_cannot_parse(self):
        valid, err = _validate_future_schedule_date("not a date", None, "Q")
        assert valid is False


# ── Real-data end-to-end: the actual return that exposed the regression ─────

class TestRealDataFrequencyResolution:
    """CIMS_RAQ(Annually) / RAQ(Annually) exist under PeriodId 107 ("Yearly")
    in BOTH 5.5 and 6.0 data, with RepFreq='A' on the return itself. 5.5's
    Period.xml has a real Frequency attribute (107 -> 'Y'), so it always
    resolved correctly. 6.0's Period.xml has no Frequency attribute at all,
    so before the fix it fell back straight to RepFreq='A' — a code the
    validator doesn't recognise — silently accepting any date."""

    @_need_5_5
    def test_5_5_annually_return_resolves_to_yearly_frequency(self):
        ret = resolve_return_exact("CIMS_RAQ(Annually)", tenant_id=None)
        assert ret is not None
        assert ret["frequency"] == "Y"

    @_need_6_0_1001
    def test_6_0_annually_return_resolves_to_yearly_frequency(self):
        # tenant_id resolution reads backend.config.BASE_REPO_PATH, a
        # module-level constant frozen at first import from os.getenv —
        # this test process may already have it pointed at the 5.5 tree
        # (per the real .env), and monkeypatch.setenv can't retroactively
        # change an already-frozen constant. A fresh subprocess with the
        # right env vars set BEFORE the interpreter starts is the only way
        # to genuinely exercise a different BASE_REPO_PATH in-process (same
        # pattern as test_access_control.py::test_tenant_id_present_allows_6_0_admin).
        script = textwrap.dedent(f"""
            import sys
            sys.path.insert(0, {str(PROJECT_ROOT)!r})
            from backend.tools.instance_generator import resolve_return_exact
            ret = resolve_return_exact("CIMS_RAQ(Annually)", tenant_id="1001")
            assert ret is not None, "return not found"
            assert ret["frequency"] == "Y", ret
            print("OK")
        """)
        env = dict(os.environ)
        env["BASE_REPO_PATH"] = str(PATH_6_0_1001.parent.parent)
        result = subprocess.run([sys.executable, "-c", script], env=env, capture_output=True, text=True)
        assert result.returncode == 0, f"stdout={result.stdout!r} stderr={result.stderr!r}"
        assert "OK" in result.stdout

    @_need_6_0_1001
    def test_6_0_annually_return_rejects_invalid_reporting_date(self):
        y = _past_year()
        script = textwrap.dedent(f"""
            import sys
            sys.path.insert(0, {str(PROJECT_ROOT)!r})
            from backend.tools.instance_generator import resolve_return_exact, validate_reporting_date
            ret = resolve_return_exact("CIMS_RAQ(Annually)", tenant_id="1001")
            result = validate_reporting_date("30-Nov-{y}", ret["frequency"])
            assert result["valid"] is False, result
            print("OK")
        """)
        env = dict(os.environ)
        env["BASE_REPO_PATH"] = str(PATH_6_0_1001.parent.parent)
        result = subprocess.run([sys.executable, "-c", script], env=env, capture_output=True, text=True)
        assert result.returncode == 0, f"stdout={result.stdout!r} stderr={result.stderr!r}"
        assert "OK" in result.stdout

    @_need_6_0_1001
    def test_6_0_annually_return_rejects_invalid_schedule_date(self):
        y = _future_year()
        script = textwrap.dedent(f"""
            import sys
            sys.path.insert(0, {str(PROJECT_ROOT)!r})
            from backend.tools.instance_generator import resolve_return_exact
            from backend.agent import _validate_future_schedule_date
            ret = resolve_return_exact("CIMS_RAQ(Annually)", tenant_id="1001")
            valid, err = _validate_future_schedule_date("30-Nov-{y}", None, ret["frequency"])
            assert valid is False, err
            print("OK")
        """)
        env = dict(os.environ)
        env["BASE_REPO_PATH"] = str(PATH_6_0_1001.parent.parent)
        result = subprocess.run([sys.executable, "-c", script], env=env, capture_output=True, text=True)
        assert result.returncode == 0, f"stdout={result.stdout!r} stderr={result.stderr!r}"
        assert "OK" in result.stdout
