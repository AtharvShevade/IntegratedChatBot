"""Regression tests for Schedule Report date validation (instance_generator.py).

Covers:

1. Frequency validation was silently skipped for some Yearly (and
   potentially other) reports when a return's RepFreq field used
   inconsistent codes across returns sharing the same PeriodId (e.g. 'A'
   vs 'Y' both appear under PeriodId 107 "Yearly"). 'A' isn't a code the
   validator recognises, so it fell through to the unrestricted catch-all
   and accepted any date. Fixed via _PERIOD_ID_TO_FREQUENCY, a
   PeriodId->Frequency fallback sourced from Period.xml's own mapping.

2. Schedule Date parsing: multiple input formats (dd-MMM-yyyy, dd/mm/yyyy,
   dd-mm-yyyy, yyyy-mm-dd, dd.mm.yyyy) must be accepted, and
   calendar-invalid dates (e.g. 31-Nov-2026) must get a specific "not a
   valid calendar date" message rather than a generic "Cannot parse" one.
   _validate_future_schedule_date delegates to
   validate_reporting_date(require_future=True) for this shared parsing.

3. Schedule Date must NOT be constrained to the report's frequency
   period-end (unlike Reporting Date, which IS the reporting period and
   must land on a period-end). The Schedule Date is only "when the .NET
   job should run" — any real, future calendar date/time is valid
   regardless of frequency. This reverses an earlier, stricter fix that
   had required Schedule Date to satisfy the same period-end rules as
   Reporting Date; that turned out to be the wrong behavior; the fix now
   is validate_reporting_date(..., skip_frequency_check=True) for the
   Schedule Date call site only — Reporting Date's own validation is
   completely unaffected.

4. Reporting-date validation for annual (6.0) reports was silently
   unrestricted. Root causes, both fixed in instance_generator.py:
     a. _parse_period_master() read a hardcoded project-local
        logs/period.xml snapshot on 5.5 instead of the real, live,
        version/tenant-aware config.period_xml_path() — so an edit to the
        actual repo's Period.xml could go unnoticed. It now always reads
        config.period_xml_path().
     b. 6.0's real Period.xml uses frequency code "A" for BOTH PeriodId
        107 "Yearly" and PeriodId 113 "As An When" — a code the Q/M/Y/H/
        C/B/W/F period-end checks didn't recognise, so it fell through to
        the "any valid past date accepted" catch-all. _FREQUENCY_ALIASES
        now aliases "A" onto "B" (Yearly/Calendar-Year, 31-Dec) so both
        PeriodIds sharing that code get one consistent "annually" rule.
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import backend.tools.instance_generator as ig
from backend.tools.instance_generator import validate_reporting_date, resolve_return_exact
from backend.agent import _validate_future_schedule_date

PATH_5_5 = Path(r"D:\Repo(new)\DataBase")
PATH_6_0_TENANT_1001 = Path(r"D:\Repo6\Repo6\1001\DataBase")

_need_5_5 = pytest.mark.skipif(not PATH_5_5.is_dir(), reason="5.5 real data tree not present")
_need_6_0 = pytest.mark.skipif(not PATH_6_0_TENANT_1001.is_dir(), reason="6.0 real tenant data tree not present")


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
    """The actual bug: a return with RepFreq='A' under PeriodId 107
    ("Yearly") must resolve to frequency 'Y' (financial-year, 31-Mar),
    same as every other return sharing that PeriodId — not fall through
    to the unrestricted "any date accepted" catch-all."""

    def test_rep_freq_a_resolves_to_yearly_not_unrestricted(self):
        from backend.tools.instance_generator import _PERIOD_ID_TO_FREQUENCY
        assert _PERIOD_ID_TO_FREQUENCY["107"] == "Y"

    def test_yearly_return_with_repfreq_a_rejects_invalid_date(self):
        """Simulates resolve_return_exact's fallback chain directly: when
        RepFreq='A', the PeriodId fallback must still produce a
        frequency-validated 'Y', not let 'A' fall through unrecognised."""
        from backend.tools.instance_generator import _PERIOD_ID_TO_FREQUENCY
        frequency = (None or _PERIOD_ID_TO_FREQUENCY.get("107") or "A" or "").strip().upper()
        assert frequency == "Y"
        y = _past_year()
        result = validate_reporting_date(f"30-Nov-{y}", frequency)
        assert result["valid"] is False


# ── Issue 1: frequency validation for Schedule Date (all frequencies) ───────

class TestScheduleDateFrequencyValidation:
    """Schedule Date has NO frequency/period-end constraint — it's just when
    the job should run, not the reporting period. Any real future date, for
    any frequency, must be accepted (contrast with Reporting Date, which
    IS constrained — see TestInvalidCalendarDateMessages /
    test_reporting_date_gives_calendar_explanation_not_cannot_parse below,
    and instance_generator.py's own validate_reporting_date tests)."""

    def test_quarterly_schedule_accepts_future_quarter_end(self):
        y = _future_year()
        valid, err = _validate_future_schedule_date(f"31-Dec-{y}", None, "Q")
        assert valid is True, err

    def test_quarterly_schedule_accepts_future_non_quarter_end(self):
        y = _future_year()
        valid, err = _validate_future_schedule_date(f"15-Dec-{y}", None, "Q")
        assert valid is True, err

    def test_yearly_schedule_accepts_future_31_mar(self):
        y = _future_year()
        valid, err = _validate_future_schedule_date(f"31-Mar-{y}", None, "Y")
        assert valid is True, err

    def test_yearly_schedule_accepts_future_30_nov(self):
        """A Yearly report's Schedule Date is not required to be 31-Mar —
        only Reporting Date is."""
        y = _future_year()
        valid, err = _validate_future_schedule_date(f"30-Nov-{y}", None, "Y")
        assert valid is True, err

    def test_half_yearly_schedule_accepts_any_future_month(self):
        y = _future_year()
        valid, err = _validate_future_schedule_date(f"30-Nov-{y}", None, "H")
        assert valid is True, err

    def test_monthly_schedule_accepts_non_last_day(self):
        y = _future_year()
        valid, err = _validate_future_schedule_date(f"15-Jun-{y}", None, "M")
        assert valid is True, err

    def test_schedule_date_still_rejects_past_dates(self):
        y = _past_year()
        valid, err = _validate_future_schedule_date(f"31-Mar-{y}", None, "Y")
        assert valid is False
        assert "future" in err.lower()

    @pytest.mark.parametrize("fmt_date", [
        "{d}/05/{y}", "{d}-05-{y}", "{y}-05-{d}", "{d}.05.{y}",
    ])
    def test_schedule_date_accepts_multiple_formats(self, fmt_date):
        y = _future_year()
        valid, err = _validate_future_schedule_date(
            fmt_date.format(d="15", y=y), None, "Q",
        )
        assert valid is True, err


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
    """CIMS_RAQ(Annually) / RAQ(Annually) exist under PeriodId 107 ("Yearly"),
    with RepFreq='A' on the return itself. Period.xml has a real Frequency
    attribute (107 -> 'Y'), so it always resolves correctly."""

    @_need_5_5
    def test_5_5_annually_return_resolves_to_yearly_frequency(self):
        ret = resolve_return_exact("CIMS_RAQ(Annually)")
        assert ret is not None
        assert ret["frequency"] == "Y"

    @_need_6_0
    def test_6_0_period_xml_gives_period_107_frequency_a(self, monkeypatch):
        """6.0's real Period.xml gives PeriodId 107 "Yearly" the code "A"
        (not 5.5's "Y") — confirmed directly against the real tenant file
        rather than through the full APP_VERSION/repo_scope machinery
        (which relies on module-load-time constants elsewhere in
        backend.config that a mid-session monkeypatch can't safely flip
        without leaking state into every other test in this session).
        _normalize_frequency() is what applies the "A"->"B" alias; this
        only confirms the raw code get_period_info() surfaces."""
        monkeypatch.setattr(ig, "_period_caches", {})
        monkeypatch.setattr(
            ig._config, "period_xml_path",
            lambda: str(PATH_6_0_TENANT_1001 / "Period.xml"),
        )
        monkeypatch.setattr(ig.version_config, "IS_V6", True)
        info = ig.get_period_info("107")
        assert info is not None
        assert info.get("Frequency") == "A"
        assert info.get("PeriodName", "").strip() == "Yearly"


# ── Issue 4: Period.xml path resolution + "A" frequency alias ───────────────

class TestFrequencyAlias:
    def test_a_aliases_to_b(self):
        assert ig._normalize_frequency("A") == "B"
        assert ig._normalize_frequency("a") == "B"  # case-insensitive

    @pytest.mark.parametrize("freq", ["Q", "M", "Y", "H", "C", "B", "W", "F", "D", "G", "HM"])
    def test_other_codes_pass_through_unchanged(self, freq):
        assert ig._normalize_frequency(freq) == freq

    def test_empty_or_none_frequency_is_untouched(self):
        assert ig._normalize_frequency("") == ""
        assert ig._normalize_frequency(None) == ""


class TestAnnualFrequencyCodeAValidation:
    """Frequency "A" (6.0's real code for both PeriodId 107 "Yearly" and
    PeriodId 113 "As An When") must validate as an annual/Calendar-Year
    period-end (31-Dec) — the exact bug-report scenario: a report the
    system used to accept on 31-Mar must now be rejected, with 31-Dec
    accepted and suggested instead."""

    def test_accepts_31_dec(self):
        y = _past_year()
        result = validate_reporting_date(f"31-Dec-{y}", "A")
        assert result["valid"] is True

    def test_rejects_31_mar_with_31_dec_suggestion(self):
        y = _past_year()
        result = validate_reporting_date(f"31-Mar-{y}", "A")
        assert result["valid"] is False
        assert "31-Dec" in result["error"]
        assert f"31-Dec-{y}" in result["suggestions"]

    def test_matches_plain_b_frequency_behavior(self):
        """"A" must be indistinguishable from "B" for validation purposes —
        same accept/reject outcome for the same input."""
        y = _past_year()
        for d in (f"31-Dec-{y}", f"31-Mar-{y}", f"30-Jun-{y}"):
            assert validate_reporting_date(d, "A")["valid"] == validate_reporting_date(d, "B")["valid"]


class TestPeriodMasterReadsConfiguredPath:
    """_parse_period_master() must resolve the period file through
    config.period_xml_path() (version/tenant-aware, honors
    version_config.repo_scope's per-request root override) — never a
    hardcoded project-local path — so an edit to the real repo's
    Period.xml/XML_Period.xml is always picked up."""

    def test_reads_from_config_period_xml_path(self, tmp_path, monkeypatch):
        period_file = tmp_path / "XML_Period.xml"
        period_file.write_text(
            '<?xml version="1.0"?>\n<Document>\n'
            '<Row Period_Id="999" Frequency="Q" PeriodName="Test Quarter"/>\n'
            "</Document>",
            encoding="utf-8",
        )
        monkeypatch.setattr(ig._config, "period_xml_path", lambda: str(period_file))
        monkeypatch.setattr(ig.version_config, "IS_V6", False)
        info = ig.get_period_info("999")
        assert info is not None
        assert info["Frequency"] == "Q"
        assert info["PeriodName"] == "Test Quarter"

    def test_uses_id_attribute_name_for_6_0(self, tmp_path, monkeypatch):
        period_file = tmp_path / "Period.xml"
        period_file.write_text(
            '<?xml version="1.0"?>\n<Document>\n'
            '<Row Id="999" Frequency="A" PeriodName="Test Annual"/>\n'
            "</Document>",
            encoding="utf-8",
        )
        monkeypatch.setattr(ig._config, "period_xml_path", lambda: str(period_file))
        monkeypatch.setattr(ig.version_config, "IS_V6", True)
        info = ig.get_period_info("999")
        assert info is not None
        assert info["Frequency"] == "A"

