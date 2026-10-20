"""6.0: a request with no body jwt falls back to the host's accessToken cookie
(set by the host, sent by the browser to the chatbot on the same domain)."""
from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient

from backend import main, version_config
from backend.utils import request_context

COOKIE_JWT = "header.payload.cookie-signature"
BODY_JWT = "header.payload.body-signature"


@pytest.fixture(scope="module")
def client():
    if not any(getattr(r, "path", "") == "/__jwt_probe" for r in main.app.routes):
        @main.app.get("/__jwt_probe")
        async def _probe():
            return {"cookie_jwt": request_context.get_cookie_jwt()}
    return TestClient(main.app)


@pytest.fixture(autouse=True)
def _v6(monkeypatch):
    monkeypatch.setattr(version_config, "IS_V6", True)
    monkeypatch.delenv("JWT_COOKIE_FALLBACK", raising=False)


def _probe(client, cookie=None):
    cookies = {request_context.JWT_COOKIE_NAME: cookie} if cookie else None
    return client.get("/__jwt_probe", cookies=cookies).json()["cookie_jwt"]


# ── the middleware ───────────────────────────────────────────────────────────
def test_cookie_is_read_in_6_0(client):
    assert _probe(client, COOKIE_JWT) == COOKIE_JWT


def test_no_cookie_means_none(client):
    assert _probe(client) is None


def test_the_cookie_is_ignored_in_5_5(client, monkeypatch):
    monkeypatch.setattr(version_config, "IS_V6", False)
    assert _probe(client, COOKIE_JWT) is None


def test_fallback_can_be_switched_off(client, monkeypatch):
    monkeypatch.setenv("JWT_COOKIE_FALLBACK", "false")
    assert _probe(client, COOKIE_JWT) is None


def test_the_value_does_not_leak_into_the_next_request(client):
    assert _probe(client, COOKIE_JWT) == COOKIE_JWT
    assert _probe(client) is None
    assert request_context.get_cookie_jwt() is None


# ── _make_repo_scope ─────────────────────────────────────────────────────────
@pytest.fixture
def tenant(monkeypatch):
    monkeypatch.setattr(version_config, "resolve_tenant_id", lambda t, d: "1001")
    monkeypatch.setattr(version_config, "repo_root_for_tenant", lambda t: "C:/repo/1001")


def _active_jwt(body_jwt, cookie_jwt):
    token = request_context.set_cookie_jwt(cookie_jwt)
    try:
        with main._make_repo_scope("1001", None, body_jwt, "admin@x"):
            return version_config.get_active_jwt()
    finally:
        request_context.reset_cookie_jwt(token)


def test_cookie_is_used_when_the_body_has_no_jwt(tenant):
    assert _active_jwt(None, COOKIE_JWT) == COOKIE_JWT
    assert _active_jwt("", COOKIE_JWT) == COOKIE_JWT


def test_the_token_from_the_host_message_still_wins(tenant):
    assert _active_jwt(BODY_JWT, COOKIE_JWT) == BODY_JWT


def test_no_token_anywhere_stays_none(tenant):
    assert _active_jwt(None, None) is None


def test_cookie_used_even_when_the_tenant_cannot_be_resolved(monkeypatch):
    monkeypatch.setattr(version_config, "resolve_tenant_id", lambda t, d: None)
    assert _active_jwt(None, COOKIE_JWT) == COOKIE_JWT


def test_5_5_never_touches_a_token(monkeypatch):
    monkeypatch.setattr(version_config, "IS_V6", False)
    token = request_context.set_cookie_jwt(COOKIE_JWT)
    try:
        with main._make_repo_scope(None, None, None, "x"):
            assert version_config.get_active_jwt() is None
    finally:
        request_context.reset_cookie_jwt(token)


def test_the_token_value_is_never_logged(tenant, caplog):
    caplog.set_level(logging.DEBUG)
    _active_jwt(None, COOKIE_JWT)
    assert "accessToken cookie" in caplog.text
    assert COOKIE_JWT not in caplog.text
