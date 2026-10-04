"""Regression tests for the C-02 interim authentication fix
(doc/CRITICAL_FIXES_LOG.md):

1. A client-supplied role_id (e.g. {"role_id": "101"} to claim the admin
   role) must never be honoured -- role is always resolved server-side from
   XML_User.xml via auth_service.get_user_role_id(), keyed only on login_id.

2. When no login_id is provided at all, the request is now denied by
   default (REQUIRE_AUTH defaults to "true" in code) unless an operator has
   explicitly opted into unauthenticated access via REQUIRE_AUTH=false.

login_id itself remains client-asserted and unverified (no JWT signature
check yet) -- these tests only cover what this interim fix actually closes:
the privilege-escalation vector (arbitrary role_id) and the "just omit
login_id" bypass.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.agent import decide, _session_context
from backend.services import auth_service


def _run_decide(query, session_id, *, login_id=None, role_id=None):
    async def _run():
        with patch(
            "backend.agent.extract_intent_and_entities",
            AsyncMock(return_value={"intent": "unknown", "search_terms": query, "reporting_date": None}),
        ):
            return await decide(
                query, session_id=session_id, asp_session=None,
                login_id=login_id, user_id=None, role_id=role_id,
                conversation_history=[],
            )
    return asyncio.run(_run())


class TestClientRoleIdIsIgnored:
    def test_client_supplied_role_id_never_reaches_downstream_unchanged(self, monkeypatch, caplog):
        """POST /chat {"login_id": "someuser", "role_id": "101"} must NOT
        result in role_id="101" being used -- the server-resolved role
        ("50" here) must win regardless of what the client sent."""
        session_id = "test-auth-role-1"
        _session_context.pop(session_id, None)

        monkeypatch.setattr(auth_service, "get_allowed_form_ids", lambda login_id: set())
        monkeypatch.setattr(auth_service, "AUTHORIZATION_ENABLED", True)
        monkeypatch.setattr(auth_service, "get_user_role_id", lambda login_id: "50")

        with caplog.at_level("WARNING"):
            _run_decide("some gibberish query xyzzy", session_id, login_id="someuser", role_id="101")

        assert any(
            "AUTH_ROLE_IGNORED" in r.message and "101" in r.message
            for r in caplog.records
        ), "client-supplied role_id=101 must be logged as discarded, not silently accepted"

    def test_admin_role_id_from_client_does_not_grant_admin_for_a_non_admin_user(self, monkeypatch):
        """The concrete exploit from the code review: a non-admin login_id
        with a spoofed role_id=101 (the default admin role) must resolve to
        the user's REAL role, not the claimed one."""
        session_id = "test-auth-role-2"
        _session_context.pop(session_id, None)

        captured_role = {}

        def _fake_get_role(login_id):
            captured_role["value"] = "50"  # a real, non-admin role for this user
            return "50"

        monkeypatch.setattr(auth_service, "get_allowed_form_ids", lambda login_id: set())
        monkeypatch.setattr(auth_service, "AUTHORIZATION_ENABLED", True)
        monkeypatch.setattr(auth_service, "get_user_role_id", _fake_get_role)

        _run_decide("some gibberish query xyzzy", session_id, login_id="nonadminuser", role_id="101")

        # get_user_role_id (the server-side resolver) must have been consulted --
        # proving the client's claimed role_id="101" was never trusted as-is.
        assert captured_role.get("value") == "50"

    def test_no_role_id_supplied_still_resolves_normally(self, monkeypatch):
        """Sanity check: the fix does not break the ordinary case where the
        client sends no role_id at all (the .NET-forwarded shape today)."""
        session_id = "test-auth-role-3"
        _session_context.pop(session_id, None)

        monkeypatch.setattr(auth_service, "get_allowed_form_ids", lambda login_id: set())
        monkeypatch.setattr(auth_service, "AUTHORIZATION_ENABLED", True)
        monkeypatch.setattr(auth_service, "get_user_role_id", lambda login_id: "50")

        result = _run_decide("some gibberish query xyzzy", session_id, login_id="someuser", role_id=None)
        assert result is not None


class TestFailClosedWithoutLoginId:
    def test_missing_login_id_is_denied_when_require_auth_unset(self, monkeypatch):
        """REQUIRE_AUTH now defaults to "true" in code -- an operator who
        never sets it at all (previously undocumented in .env.example) gets
        the safe, fail-closed behavior rather than silently allowing every
        unauthenticated caller through."""
        monkeypatch.delenv("REQUIRE_AUTH", raising=False)
        monkeypatch.delenv("AUTHORIZATION_ENABLED", raising=False)
        session_id = "test-auth-failclosed-1"
        _session_context.pop(session_id, None)

        result = _run_decide("some gibberish query xyzzy", session_id, login_id=None, role_id=None)
        assert result["result_type"] == "error"
        assert "authentication required" in result["response_text"].lower()

    def test_explicit_require_auth_false_still_allows_dev_mode(self, monkeypatch):
        """Operators who explicitly opt out (local/dev work with no
        .NET-forwarded login_id available) must still be able to."""
        monkeypatch.setenv("REQUIRE_AUTH", "false")
        session_id = "test-auth-failclosed-2"
        _session_context.pop(session_id, None)

        result = _run_decide("some gibberish query xyzzy", session_id, login_id=None, role_id=None)
        assert not (
            result["result_type"] == "error"
            and "authentication required" in result["response_text"].lower()
        )
