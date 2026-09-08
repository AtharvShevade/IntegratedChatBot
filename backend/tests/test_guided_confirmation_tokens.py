"""Deterministic Yes/No guided-confirmation handling.

Covers the three places that changed together (backend/guided.py's
CONFIRMATION_TOKENS + normalize_confirmation is the single source of truth):

  * normalize_confirmation() itself -- en/fr/ar/hi, case, whitespace
  * backend/i18n/boundary.py::_inbound_skip_reason() -- these tokens must
    bypass translation ("guided-confirmation"), exactly like GUIDED_ACTIONS
    already does for the 5-item menu
  * backend/agent/__init__.py's STAGE_PREV_DATES handler -- a typed French
    "Oui"/"Non" (not just the English tokens the old hardcoded check knew
    about) must take the correct branch

Free-form multilingual text must still be unaffected: a real sentence should
not be picked up as a confirmation token.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.guided import normalize_confirmation, CONFIRMATION_TOKENS
from backend.i18n.boundary import _inbound_skip_reason
from backend.agent import decide, _session_context, STAGE_PREV_DATES


# ── normalize_confirmation() ────────────────────────────────────────────────

class TestNormalizeConfirmation:
    def test_english_yes_variants(self):
        for token in ("yes", "y", "yeah", "yep", "Yes", "YES"):
            assert normalize_confirmation(token) == "YES"

    def test_english_no_variants(self):
        for token in ("no", "n", "nope", "nah", "No", "NO"):
            assert normalize_confirmation(token) == "NO"

    def test_french_oui_non(self):
        assert normalize_confirmation("Oui") == "YES"
        assert normalize_confirmation("Non") == "NO"

    def test_arabic_yes_no(self):
        assert normalize_confirmation("نعم") == "YES"
        assert normalize_confirmation("لا") == "NO"

    def test_hindi_yes_no(self):
        assert normalize_confirmation("हाँ") == "YES"
        assert normalize_confirmation("नहीं") == "NO"

    def test_case_normalization(self):
        for token in ("oui", "Oui", "OUI"):
            assert normalize_confirmation(token) == "YES"

    def test_surrounding_whitespace(self):
        assert normalize_confirmation(" oui") == "YES"
        assert normalize_confirmation("oui ") == "YES"
        assert normalize_confirmation("  Oui  ") == "YES"
        assert normalize_confirmation("  Non  ") == "NO"

    def test_unrelated_text_returns_none(self):
        assert normalize_confirmation("CIMS_ROR") is None
        assert normalize_confirmation("Je voudrais vérifier le statut du rapport CIMS_ROR") is None
        assert normalize_confirmation("") is None
        assert normalize_confirmation(None) is None

    def test_every_supported_language_present(self):
        for canonical in ("YES", "NO"):
            for lang in ("en", "fr", "ar", "hi"):
                assert CONFIRMATION_TOKENS[canonical].get(lang), (canonical, lang)


# ── _inbound_skip_reason(): these tokens must bypass translation ───────────

class TestInboundSkipReasonForConfirmations:
    def test_english_yes_no_skip_translation(self):
        assert _inbound_skip_reason("Yes") == "guided-confirmation"
        assert _inbound_skip_reason("No") == "guided-confirmation"

    def test_french_oui_non_skip_translation(self):
        assert _inbound_skip_reason("Oui") == "guided-confirmation"
        assert _inbound_skip_reason("Non") == "guided-confirmation"

    def test_arabic_skip_translation(self):
        assert _inbound_skip_reason("نعم") == "guided-confirmation"
        assert _inbound_skip_reason("لا") == "guided-confirmation"

    def test_hindi_skip_translation(self):
        assert _inbound_skip_reason("हाँ") == "guided-confirmation"
        assert _inbound_skip_reason("नहीं") == "guided-confirmation"

    def test_case_and_whitespace_insensitive(self):
        assert _inbound_skip_reason("  OUI  ") == "guided-confirmation"
        assert _inbound_skip_reason(" oui") == "guided-confirmation"

    def test_free_form_multilingual_text_not_skipped(self):
        """A real French sentence must still go through translation --
        only the exact static token set bypasses it."""
        assert _inbound_skip_reason(
            "Je voudrais vérifier le statut du rapport CIMS_ROR"
        ) is None

    def test_guided_menu_actions_still_skip_as_before(self):
        from backend.guided import GUIDED_ACTIONS
        assert _inbound_skip_reason(GUIDED_ACTIONS[0]) == "guided-action"


# ── STAGE_PREV_DATES via decide(): typed French Oui/Non take the right branch

def _seed_prev_dates_session(session_id: str, other_instances):
    _session_context[session_id] = {
        "awaiting":              STAGE_PREV_DATES,
        "pending_form_id":       "test-form-id",
        "pending_return_name":  "CIMS_ROR",
        "pending_other_instances": other_instances,
    }


class TestStagePrevDatesConfirmation:
    def test_typed_french_oui_continues_to_date_selection(self):
        session_id = "test-prev-dates-oui"
        _session_context.pop(session_id, None)
        other_instances = [{"label": "31-Mar-2026", "status": "In Queue"}]
        _seed_prev_dates_session(session_id, other_instances)

        result = asyncio.run(decide(
            "Oui", session_id=session_id, asp_session=None,
            login_id="iris810", user_id=None, role_id=None, conversation_history=[],
        ))

        assert result["result_type"] == "date_selection"
        assert result["options"] == ["31-Mar-2026"]
        assert _session_context.get(session_id, {}).get("awaiting") == "AWAITING_DATE_SELECTION"

    def test_typed_french_non_ends_the_flow(self):
        session_id = "test-prev-dates-non"
        _session_context.pop(session_id, None)
        _seed_prev_dates_session(session_id, [{"label": "31-Mar-2026", "status": "In Queue"}])

        result = asyncio.run(decide(
            "Non", session_id=session_id, asp_session=None,
            login_id="iris810", user_id=None, role_id=None, conversation_history=[],
        ))

        assert result["result_type"] == "final"
        assert session_id not in _session_context

    def test_typed_english_yes_no_unaffected(self):
        session_id = "test-prev-dates-yes-en"
        _session_context.pop(session_id, None)
        _seed_prev_dates_session(session_id, [{"label": "31-Mar-2026", "status": "In Queue"}])

        result = asyncio.run(decide(
            "yes", session_id=session_id, asp_session=None,
            login_id="iris810", user_id=None, role_id=None, conversation_history=[],
        ))
        assert result["result_type"] == "date_selection"

        session_id = "test-prev-dates-no-en"
        _session_context.pop(session_id, None)
        _seed_prev_dates_session(session_id, [{"label": "31-Mar-2026", "status": "In Queue"}])

        result = asyncio.run(decide(
            "no", session_id=session_id, asp_session=None,
            login_id="iris810", user_id=None, role_id=None, conversation_history=[],
        ))
        assert result["result_type"] == "final"
