"""backend/i18n/protect.py -- entity masking/restoration.

Focused on the _ORDINARY_ACRONYMS exclusion: "AI"/"NPA" must never be masked
(they measurably increased aya-expanse:8b's placeholder-drop rate on real
/compare-summary narratives), while the bare-acronym pattern's general shape
-- the only thing protecting 27 real bare-uppercase report/return codes in
returns.xml -- must remain exactly as strict as before for everything else.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.i18n import protect

# A sample of the real bare-uppercase report/return codes this pattern must
# keep protecting (verified present in returns.xml during this change).
REAL_REPORT_CODES = (
    "ROR", "CRILC", "RBS", "IRS", "FCY", "LOU", "CEM", "BBSD", "BEF", "ALO",
    "CPR", "FVCI", "MTSS", "OCB", "PCI", "RCL", "RDA", "RDB", "RLC", "RLE",
    "ROC", "ROF", "ROP", "ROS", "SIR", "SSL", "STDL",
)


class TestOrdinaryAcronymsExcluded:
    def test_ai_is_not_masked(self):
        masked, tokens = protect.mask_entities("AI Summary: results below.")
        assert masked == "AI Summary: results below."
        assert "AI" not in tokens.values()

    def test_npa_is_not_masked(self):
        masked, tokens = protect.mask_entities("Gross NPA rose this quarter.")
        assert masked == "Gross NPA rose this quarter."
        assert "NPA" not in tokens.values()

    def test_ai_and_npa_together_in_a_real_shaped_narrative(self):
        text = (
            "AI Summary:\n"
            "• Gross NPA To Gross Advances Ratio rose from 4.1 to 3.2 (+28.1%).\n"
        )
        masked, tokens = protect.mask_entities(text)
        assert "AI" not in tokens.values()
        assert "NPA" not in tokens.values()
        # The real numbers must still be masked.
        assert "4.1" in tokens.values()
        assert "3.2" in tokens.values()
        assert "28.1" in tokens.values()


class TestRealReportCodesStillProtected:
    """The general bare-acronym shape must remain exactly as strict as
    before for every code that is NOT in _ORDINARY_ACRONYMS."""

    def test_every_real_report_code_is_still_masked(self):
        for code in REAL_REPORT_CODES:
            masked, tokens = protect.mask_entities(f"Report {code} filed on time.")
            assert code in tokens.values(), f"{code} lost protection"
            assert code not in masked, f"{code} leaked into the masked text"

    def test_report_code_and_ordinary_acronym_in_the_same_sentence(self):
        """AI/NPA must be excluded WITHOUT affecting a real code sitting
        right next to them."""
        masked, tokens = protect.mask_entities("AI flagged that ROR's NPA ratio moved.")
        assert "AI" not in tokens.values()
        assert "NPA" not in tokens.values()
        assert "ROR" in tokens.values()
        assert "AI flagged that" in masked
        assert "NPA ratio moved" in masked


class TestMaskRestoreRoundTrip:
    def test_round_trip_preserves_everything(self):
        text = (
            "AI Summary for CIMS_ROR:\n"
            "• Gross NPA ratio rose from 4.1% to 3.2% on 31-Mar-2026.\n"
            "• Report ROR Request ID abc123def456ghi789jklmno01234567 filed."
        )
        masked, tokens = protect.mask_entities(text)
        restored, missing = protect.restore_entities(masked, tokens)
        assert missing == []
        assert restored == text

    def test_no_regression_for_dates_ids_and_amounts(self):
        text = "Amount Rs 5,061 Cr changed by 4.2% on 30-Sep-2026 for CIMS_ROR."
        masked, tokens = protect.mask_entities(text)
        for value in ("5,061", "4.2", "30-Sep-2026", "CIMS_ROR"):
            assert value in tokens.values(), f"{value} lost protection"
        restored, missing = protect.restore_entities(masked, tokens)
        assert missing == []
        assert restored == text
