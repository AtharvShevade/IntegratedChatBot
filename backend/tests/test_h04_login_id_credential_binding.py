"""Regression tests for the H-04 login_id-binding fix
(doc/CRITICAL_FIXES_LOG.md): backend/agent/router.py's decide() now binds a
cached .NET session cookie (asp_session) to the login_id that supplied it,
so a request presenting only a matching session_id -- with a DIFFERENT or
missing login_id -- can no longer retrieve another user's cached credential.

login_id itself remains client-supplied and cryptographically UNVERIFIED
(same standing caveat as C-02) -- this is a mitigation that closes the
"session_id alone is enough" hijack path, not real identity verification.

These tests exercise decide() end-to-end with extract_intent_and_entities
and _handle_generate mocked at the same seams test_compare_disambiguation.py
already uses, so the real report/date resolution, XML lookups and the .NET
call itself are never reached -- only the credential-selection logic in
decide() (the two lines this fix touches) is under test.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.agent import decide, _session_context
from backend.services import auth_service


@pytest.fixture(autouse=True)
def _resolvable_identity(monkeypatch):
    """These tests exercise the credential-caching logic, not identity
    resolution (already covered by test_auth_identity_resolution.py) --
    make every login_id used here resolve successfully so the C-02/H-01
    fail-closed gate (which runs BEFORE the caching code under test) never
    blocks these calls."""
    monkeypatch.setattr(auth_service, "AUTHORIZATION_ENABLED", True)
    monkeypatch.setattr(auth_service, "get_allowed_form_ids", lambda login_id: set())
    monkeypatch.setattr(auth_service, "get_user_role_id", lambda login_id: "100")
    monkeypatch.setenv("REQUIRE_AUTH", "false")  # allows the login_id=None dev-mode test too


def _run_generate_query(query, session_id, *, asp_session=None, login_id=None):
    """Run *query* through decide() with generate_instance pre-selected as
    the LLM-extracted intent, and _handle_generate mocked to capture the
    exact (session_id, asp_session, login_id) it's called with instead of
    actually resolving a report/date or calling .NET."""
    captured = {}

    async def _fake_handle_generate(search_terms, reporting_date, session_id_arg,
                                     asp_session_arg=None, allowed_form_ids=None, login_id_arg=None):
        captured["session_id"] = session_id_arg
        captured["asp_session"] = asp_session_arg
        captured["login_id"] = login_id_arg
        return {
            "intent": "generate_instance", "report_name": None,
            "response_text": "stub", "result_type": "final", "options": [],
        }

    async def _run():
        with patch(
            "backend.agent.extract_intent_and_entities",
            AsyncMock(return_value={
                "intent": "generate_instance", "search_terms": query, "reporting_date": "31-Mar-2026",
            }),
        ), patch("backend.agent.router._handle_generate", _fake_handle_generate):
            await decide(
                query, session_id=session_id, asp_session=asp_session,
                login_id=login_id, user_id=None, role_id=None,
                conversation_history=[],
            )
    asyncio.run(_run())
    return captured


class TestLoginIdBoundCredentialCache:
    def test_same_session_same_login_id_reuses_cached_credential(self):
        """1. Legitimate case: the SAME user's follow-up turn (no fresh
        asp_session, e.g. the staged date-reply) still gets the credential
        it cached earlier under the same login_id."""
        session_id = "test-h04-same-login"
        _session_context.pop(session_id, None)

        # Turn 1: fresh asp_session + login_id -- gets cached.
        _run_generate_query("generate CIMS_RAQ", session_id, asp_session="real-cookie", login_id="alice")
        assert _session_context[session_id]["asp_session"] == "real-cookie"
        assert _session_context[session_id]["asp_session_login_id"] == "alice"

        # Turn 2: same session_id, same login_id, NO fresh asp_session.
        captured = _run_generate_query("generate CIMS_RAQ", session_id, asp_session=None, login_id="alice")
        assert captured["asp_session"] == "real-cookie"

    def test_same_session_different_login_id_does_not_reuse_credential(self):
        """2 & 3. The core fix: a different (or attacker-supplied) login_id
        presenting the SAME session_id must NOT get alice's cached cookie --
        covers both 'different login_id' and 'stolen session_id without the
        matching login_id' (same code path)."""
        session_id = "test-h04-diff-login"
        _session_context.pop(session_id, None)

        _run_generate_query("generate CIMS_RAQ", session_id, asp_session="alices-real-cookie", login_id="alice")
        assert _session_context[session_id]["asp_session"] == "alices-real-cookie"

        # Attacker/different user: knows session_id, but is "mallory", not "alice".
        captured = _run_generate_query("generate CIMS_RAQ", session_id, asp_session=None, login_id="mallory")
        assert captured["asp_session"] is None

    def test_stolen_session_id_with_no_login_id_at_all_does_not_reuse_credential(self):
        """3 (variant): presenting the stolen session_id with NO login_id at
        all must also fail to retrieve the cached credential."""
        session_id = "test-h04-no-login"
        _session_context.pop(session_id, None)

        _run_generate_query("generate CIMS_RAQ", session_id, asp_session="alices-real-cookie", login_id="alice")

        captured = _run_generate_query("generate CIMS_RAQ", session_id, asp_session=None, login_id=None)
        assert captured["asp_session"] is None

    def test_staged_multiturn_flow_still_works_end_to_end(self):
        """4. The exact legitimate scenario the whole investigation was
        about: report+date resolved across two separate turns by the same
        user, same login_id both times -- must still successfully carry the
        credential across to the second turn."""
        session_id = "test-h04-staged-flow"
        _session_context.pop(session_id, None)

        # Turn 1: user says "generate CIMS_RAQ" (asp_session sent, as the
        # frontend always does), bot would normally ask for a date -- here
        # we just confirm the credential gets cached under this login_id.
        _run_generate_query("generate CIMS_RAQ", session_id, asp_session="freds-cookie", login_id="fred")
        assert _session_context[session_id]["asp_session_login_id"] == "fred"

        # Turn 2: user's follow-up (e.g. just the date) -- frontend resends
        # login_id (confirmed in frontend/src/App.jsx: identical on every
        # call) but the in-memory asp_session const may or may not still be
        # fresh; either way, same login_id must recover the credential.
        captured = _run_generate_query("generate CIMS_RAQ", session_id, asp_session=None, login_id="fred")
        assert captured["asp_session"] == "freds-cookie"

    def test_fresh_asp_session_with_correct_login_id_caches_correctly(self):
        """5. A fresh, correctly-identified credential is stored under the
        right login_id (the write half of the fix)."""
        session_id = "test-h04-fresh-cache"
        _session_context.pop(session_id, None)

        _run_generate_query("generate CIMS_RAQ", session_id, asp_session="carols-cookie", login_id="carol")
        assert _session_context[session_id]["asp_session"] == "carols-cookie"
        assert _session_context[session_id]["asp_session_login_id"] == "carol"

    def test_dev_mode_no_login_id_at_all_remains_compatible(self):
        """6. Existing dev-mode behaviour (REQUIRE_AUTH=false, no login_id
        ever sent by anyone) must be unaffected: None caches/matches None
        exactly as before, so a purely anonymous staged flow keeps working."""
        session_id = "test-h04-dev-mode"
        _session_context.pop(session_id, None)

        _run_generate_query("generate CIMS_RAQ", session_id, asp_session="dev-cookie", login_id=None)
        assert _session_context[session_id]["asp_session_login_id"] is None

        captured = _run_generate_query("generate CIMS_RAQ", session_id, asp_session=None, login_id=None)
        assert captured["asp_session"] == "dev-cookie"
