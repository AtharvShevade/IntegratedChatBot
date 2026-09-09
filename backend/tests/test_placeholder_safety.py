"""Guardrail for /compare-summary's per-endpoint translator override.

backend/i18n/translator.py::unsafe_translation_reason() / PlaceholderSafeTranslator
catch two failure modes measured on aya-expanse:8b during benchmarking that
protect.restore_entities() does not catch on its own:

  1. A placeholder reused for a second, different value ([[E7]] appearing
     where [[E8]] should) -- restore_entities() only checks that each
     placeholder was used at least once, so a duplicate is invisible to it.
  2. An invented illustrative figure in plain prose next to an otherwise
     intact placeholder (e.g. a fabricated "500 million rupees" that was
     never in the source). Every real number/amount/date is already masked
     by protect.mask_entities(), so a genuine translation has zero bare
     digits left; any digit outside a placeholder is invented.

A rejected translation must return ok=False -- the same signal any other
translation failure produces -- so boundary.translate_outbound's existing
"keep English" fallback handles it with no new code path.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.i18n.translator import (
    PlaceholderSafeTranslator,
    TranslationResult,
    unsafe_translation_reason,
)

SAFE_ORIGINAL = (
    "Variance analysis for [[E1]] comparing [[E2]] to [[E3]]: "
    "Gross NPA ratio rose from [[E4]]% to [[E5]]%."
)


class TestUnsafeTranslationReason:
    def test_exact_preservation_is_safe(self):
        translated = (
            "Analyse de variance pour [[E1]] comparant [[E2]] à [[E3]] : "
            "Le ratio NPA brut est passé de [[E4]]% à [[E5]]%."
        )
        assert unsafe_translation_reason(SAFE_ORIGINAL, translated) is None

    def test_reordered_placeholders_still_safe(self):
        """Placeholders may appear in a different ORDER (natural for some
        target languages) as long as the same multiset is present."""
        translated = "[[E3]] की तुलना [[E2]] से [[E1]] के लिए: [[E4]]% से [[E5]]%।"
        assert unsafe_translation_reason(SAFE_ORIGINAL, translated) is None

    def test_dropped_placeholder_is_unsafe(self):
        translated = "Analyse de variance pour [[E1]] comparant [[E2]] : de [[E4]]% à [[E5]]%."
        reason = unsafe_translation_reason(SAFE_ORIGINAL, translated)
        assert reason is not None
        assert "placeholder counts changed" in reason

    def test_duplicated_placeholder_is_unsafe(self):
        """[[E7]]/[[E8]] reused for a different metric -- NOT caught by
        protect.restore_entities() (it only checks 'used at least once'),
        which is exactly why this guardrail exists."""
        original = "Provisions rose from Rs [[E7]] Cr to Rs [[E8]] Cr. NIM moved from [[E7]]% to [[E8]]%."
        translated = "Les provisions ont augmenté de Rs [[E7]] Cr à Rs [[E8]] Cr. La marge a évolué de [[E7]]% à [[E8]]%."
        # Both appear twice each on both sides -- safe.
        assert unsafe_translation_reason(original, translated) is None

        bad_translated = "Les provisions ont augmenté de Rs [[E7]] Cr à Rs [[E8]] Cr. La marge a évolué de [[E9]]% à [[E8]]%."
        reason = unsafe_translation_reason(original, bad_translated)
        assert reason is not None
        assert "placeholder counts changed" in reason

    def test_invented_bare_number_is_unsafe(self):
        """The exact defect observed on aya-expanse:8b: an illustrative
        figure invented in prose, with the real placeholder left intact."""
        translated = (
            "زادت الاحتياطيات من 500 مليون روبية [[E7]] كر إلى 700 مليون روبية [[E8]] كر."
        )
        original = "Provisions rose from Rs [[E7]] Cr to Rs [[E8]] Cr."
        reason = unsafe_translation_reason(original, translated)
        assert reason is not None
        assert "number outside any protected placeholder" in reason

    def test_no_placeholders_at_all_is_safe(self):
        assert unsafe_translation_reason("Hello there.", "Bonjour.") is None

    def test_bracket_stripped_placeholder_is_unsafe(self):
        """The NLLB-200 failure mode: brackets stripped so [[E1]] becomes a
        bare 'E1' -- counted as a dropped placeholder here, correctly."""
        original = "Amount [[E1]] Cr for [[E2]]."
        translated = "Montant E1 Cr pour E2."
        reason = unsafe_translation_reason(original, translated)
        assert reason is not None


class _StubInner:
    name = "stub-inner"

    def __init__(self, response_text: str, ok: bool = True):
        self._response_text = response_text
        self._ok = ok

    async def translate(self, text, src, tgt):
        return TranslationResult(
            text=self._response_text, latency_ms=5.0, ok=self._ok, model=self.name,
        )


class TestPlaceholderSafeTranslator:
    def test_safe_translation_passes_through_unchanged(self):
        inner = _StubInner("Analyse de variance pour [[E1]] comparant [[E2]] à [[E3]] : "
                            "Le ratio NPA brut est passé de [[E4]]% à [[E5]]%.")
        wrapped = PlaceholderSafeTranslator(inner)
        result = asyncio.run(wrapped.translate(SAFE_ORIGINAL, "en", "fr"))
        assert result.ok is True
        assert result.text == inner._response_text

    def test_unsafe_translation_is_rejected_as_ok_false(self):
        inner = _StubInner("500 million rupees [[E7]] Cr to [[E8]] Cr.")
        wrapped = PlaceholderSafeTranslator(inner)
        result = asyncio.run(wrapped.translate(
            "Provisions rose from Rs [[E7]] Cr to Rs [[E8]] Cr.", "en", "ar",
        ))
        assert result.ok is False
        assert "placeholder safety check failed" in result.error

    def test_inner_failure_passes_through_unchanged(self):
        """A translator-level failure (timeout, etc.) is not our concern --
        it must propagate exactly as it already does, not be masked as a
        'safety' rejection."""
        inner = _StubInner("", ok=False)
        wrapped = PlaceholderSafeTranslator(inner)
        result = asyncio.run(wrapped.translate(SAFE_ORIGINAL, "en", "hi"))
        assert result.ok is False
