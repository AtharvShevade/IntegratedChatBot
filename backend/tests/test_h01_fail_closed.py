"""Regression tests for the H-01 fix (doc/CRITICAL_FIXES_LOG.md): every
module that checks authorization must deny -- not silently allow -- when
REQUIRE_AUTH is set and no login_id is present, the same guarantee C-02
already gave backend/agent/router.py's decide(). Covers the three places
that were still fail-open:

  - backend/guided.py's guided_step()
  - backend/agent/generation.py's _finalize_generation() instance-generation
    permission check
  - backend/db_qa/access_control.py's scope_query() "return" branch, which
    conflated "AUTHORIZATION_ENABLED=false" (deliberate bypass) with "login_id
    doesn't resolve in XML_User.xml" (unknown/unauthenticated caller) --
    both returned None, so an unresolvable login_id was silently treated as
    "no filtering" instead of being denied.

login_id itself remains client-asserted/unverified (C-02's still-open item)
-- these tests only cover what H-01 actually closes: consistent fail-closed
behavior across modules when identity is entirely absent or unresolvable.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.guided import guided_step, _guided_sessions
from backend.agent.generation import _finalize_generation
from backend.db_qa import access_control
from backend.services import auth_service


class TestGuidedStepFailsClosed:
    def test_no_login_id_denied_when_require_auth_unset(self, monkeypatch):
        monkeypatch.delenv("REQUIRE_AUTH", raising=False)
        monkeypatch.delenv("AUTHORIZATION_ENABLED", raising=False)
        session_id = "test-h01-guided-1"
        _guided_sessions.pop(session_id, None)

        result = asyncio.run(guided_step("hello", session_id, None, login_id=None))
        assert result["result_type"] == "error"
        assert "authentication required" in result["response_text"].lower()

    def test_no_login_id_still_allowed_when_require_auth_false(self, monkeypatch):
        monkeypatch.setenv("REQUIRE_AUTH", "false")
        session_id = "test-h01-guided-2"
        _guided_sessions.pop(session_id, None)

        result = asyncio.run(guided_step("hello", session_id, None, login_id=None))
        assert result["result_type"] != "error" or "authentication required" not in result["response_text"].lower()

    def test_known_login_id_unaffected(self, monkeypatch):
        """Sanity check: a resolvable login_id must behave exactly as before."""
        monkeypatch.setenv("REQUIRE_AUTH", "true")
        monkeypatch.setattr(auth_service, "AUTHORIZATION_ENABLED", True)
        monkeypatch.setattr(auth_service, "get_allowed_form_ids", lambda login_id: set())
        session_id = "test-h01-guided-3"
        _guided_sessions.pop(session_id, None)

        result = asyncio.run(guided_step("hello", session_id, None, login_id="someuser"))
        assert "authentication required" not in result["response_text"].lower()


class TestGenerationFailsClosed:
    _RET = {"name": "TEST_REPORT", "form_id": "9999", "frequency": "monthly"}

    def test_no_login_id_denied_when_require_auth_unset(self, monkeypatch):
        monkeypatch.delenv("REQUIRE_AUTH", raising=False)
        monkeypatch.delenv("AUTHORIZATION_ENABLED", raising=False)

        result = asyncio.run(_finalize_generation(self._RET, "31-Mar-2026", None, login_id=None))
        assert result["result_type"] == "error"
        assert "authentication required" in result["response_text"].lower()

    def test_no_login_id_still_allowed_when_require_auth_false(self, monkeypatch):
        monkeypatch.setenv("REQUIRE_AUTH", "false")

        result = asyncio.run(_finalize_generation(self._RET, "31-Mar-2026", None, login_id=None))
        # Must proceed past the auth gate -- whatever it returns next
        # (date validation, staged flow, etc.) must not be the auth denial.
        assert "authentication required" not in result.get("response_text", "").lower()

    def test_known_login_id_lacking_permission_still_denied(self, monkeypatch):
        """Sanity check: the existing login_id-present denial path (a real
        user without Instance Generation rights) must be unaffected."""
        monkeypatch.setattr(
            "backend.agent.generation.can_generate_instance", lambda login_id: False, raising=False,
        )
        from backend.services import auth_service as _auth_service
        monkeypatch.setattr(_auth_service, "can_generate_instance", lambda login_id: False)

        result = asyncio.run(_finalize_generation(self._RET, "31-Mar-2026", None, login_id="someuser"))
        assert result["result_type"] == "error"
        assert "do not have access" in result["response_text"].lower()


class TestAccessControlDistinguishesBypassFromUnknownUser:
    def test_authorization_disabled_still_allows_unfiltered_return_query(self, monkeypatch):
        monkeypatch.setattr(auth_service, "AUTHORIZATION_ENABLED", False)
        monkeypatch.setattr(auth_service, "get_allowed_form_ids", lambda login_id: None)
        monkeypatch.setattr(auth_service, "get_allowed_nx_form_ids", lambda login_id: None)

        scope = access_control.scope_query(
            {"login_id": "anyone", "user_id": "1"}, "some_intent", {"target_type": "return"},
        )
        assert scope["allowed_form_ids"] is None

    def test_unresolvable_login_id_with_auth_enabled_is_denied_not_allowed(self, monkeypatch):
        """The core H-01 bug: AUTHORIZATION_ENABLED=true but login_id isn't
        in XML_User.xml -- both underlying lookups return None, but this
        must now raise PermissionError (deny), never silently allow."""
        monkeypatch.setattr(auth_service, "AUTHORIZATION_ENABLED", True)
        monkeypatch.setattr(auth_service, "get_allowed_form_ids", lambda login_id: None)
        monkeypatch.setattr(auth_service, "get_allowed_nx_form_ids", lambda login_id: None)

        with pytest.raises(PermissionError):
            access_control.scope_query(
                {"login_id": "unknown_user", "user_id": "1"}, "some_intent", {"target_type": "return"},
            )

    def test_known_user_with_real_forms_unaffected(self, monkeypatch):
        monkeypatch.setattr(auth_service, "AUTHORIZATION_ENABLED", True)
        monkeypatch.setattr(auth_service, "get_allowed_form_ids", lambda login_id: {"101", "102"})
        monkeypatch.setattr(auth_service, "get_allowed_nx_form_ids", lambda login_id: set())

        scope = access_control.scope_query(
            {"login_id": "realuser", "user_id": "1"}, "some_intent", {"target_type": "return"},
        )
        assert scope["allowed_form_ids"] == {"101", "102"}
