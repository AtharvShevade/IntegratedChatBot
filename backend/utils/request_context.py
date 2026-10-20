"""M-28: a per-request correlation ID, available throughout the request
(any module can call get_request_id()) and automatically attached to every
log record via RequestIdFilter -- without threading an explicit parameter
through every function call.

Set by backend/main.py's request-id middleware at the very start of each
request and cleared in its finally block. A contextvar (not a plain module
global) because FastAPI/Starlette run concurrent requests on the same event
loop -- a plain global would leak one request's ID into another's logs.
"""
from __future__ import annotations

import contextvars
import logging
import uuid

_request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="-"
)


def new_request_id() -> str:
    return uuid.uuid4().hex


def set_request_id(request_id: str) -> contextvars.Token:
    return _request_id_var.set(request_id)


def reset_request_id(token: contextvars.Token) -> None:
    _request_id_var.reset(token)


def get_request_id() -> str:
    """The current request's correlation ID, or "-" outside any request
    (startup/shutdown logs, background sweeps)."""
    return _request_id_var.get()


class RequestIdFilter(logging.Filter):
    """Attaches the current request_id to every log record as
    `record.request_id`, so %(request_id)s can appear in the log format
    string for every call site with no per-call-site change needed."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = get_request_id()
        return True


# ── 6.0: the host's login token, when the browser sends it as a cookie ────────
# The 6.0 host sets its JWT as the "accessToken" cookie (Domain=<host>, Path=/,
# Secure, HttpOnly). When the chatbot is served from that same domain the
# browser sends the cookie along with every chatbot request, so a chatbot opened
# on its own (no CHATBOT_AUTH message from a host page) can still act as the
# logged-in user. Set by main.py's request middleware, read by _make_repo_scope
# only when the request body carries no jwt. Never logged.
JWT_COOKIE_NAME = "accessToken"

_cookie_jwt_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "cookie_jwt", default=None
)


def set_cookie_jwt(value: str | None) -> contextvars.Token:
    return _cookie_jwt_var.set(value or None)


def reset_cookie_jwt(token: contextvars.Token) -> None:
    _cookie_jwt_var.reset(token)


def get_cookie_jwt() -> str | None:
    """The accessToken cookie of the current request, or None."""
    return _cookie_jwt_var.get()
