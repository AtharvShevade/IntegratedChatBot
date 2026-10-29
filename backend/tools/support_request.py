"""Chatbot support requests: an issue a user reports from the chatbot, forwarded to the iDEAL .NET application.

Flow:  React chatbot -> POST /support-request (this module) -> POST {DOTNET_API_URL}/ChatbotSupport/SubmitRequest (WebiDEAL)
       -> NotificationIO.RaiseNotification -> Notifications.xml queue -> iDEALNotificationService -> SMTP.

This module only validates, forwards and classifies the answer. It sends no mail and keeps nothing.

Who the user is
    The WebiDEAL action takes the user from ITS OWN session (the .AspNetCore.Session cookie this module forwards). There is
    deliberately no login/user/email/recipient field in the request model: they are rejected, never read.

What "ok" means
    `ok: true` is returned ONLY when WebiDEAL itself answered that the request is in its notification queue (code `ok`) or that the
    same request was already queued (code `duplicate`). It does not mean the mail was sent or delivered: the notification service
    sends later, on its own timer, and delivery is not confirmed anywhere. Every other situation, including every situation where
    it is not known what happened, is `ok: false`.

No automatic retry
    One request is made. A timeout or a broken connection after the request left is `outcome_unknown`: it is NOT retried here.
    The caller may retry by sending the same `reference_id` again (the answer carries it): WebiDEAL recognises a repeat of a
    reference it already queued and answers `duplicate` instead of queuing twice. That protection lives in WebiDEAL's memory for
    10 minutes and is lost if the web app restarts, so it is a safeguard, not a guarantee.

Response codes (stable; `retryable` says whether sending the same request again, with the same reference_id, is reasonable)
    ok                  queued                                   duplicate           was already queued (reference_id is the original)
    invalid_input       a field is not acceptable (see `field`)  session_required    no session cookie was supplied
    session_expired     login again (expired, logged in elsewhere, redirected to login)      otp_required   finish the OTP step first
    not_available       the feature is off or not set up         rate_limited        too many requests; try later
    queue_failed        WebiDEAL could not queue it (not queued) unreachable         WebiDEAL could not be reached (not sent)
    upstream_error      WebiDEAL refused or answered unexpectedly; NOT queued
    outcome_unknown     the request may or may not have been queued: do not say it was submitted
    internal_error      a bug in this service before anything was sent
"""
from __future__ import annotations

import logging
import os
import re
import secrets
import time
import urllib.parse
from typing import Any, Optional

import httpx
from pydantic import BaseModel, ConfigDict, Field

from backend import version_config

logger = logging.getLogger(__name__)

# Same limits as the WebiDEAL notifier (ClsChatbotSupportNotifier). WebiDEAL stays the authority; these only keep an obviously
# unacceptable request from making the trip.
MIN_DESCRIPTION = 10
MAX_DESCRIPTION = 2000
MAX_SESSION_REF = 128
MAX_LAST_QUERY = 500
MAX_ANSWER = 1000
CATEGORIES = ("incorrect_answer", "technical_problem", "missing_information", "other")
_REFERENCE = re.compile(r"^SR-[A-Z0-9]{6,24}$")           # exactly what WebiDEAL accepts

_SESSION_COOKIE = ".AspNetCore.Session"
_DEFAULT_PATH = "/ChatbotSupport/SubmitRequest"

# Test hook: a transport (e.g. httpx.MockTransport) used when none is passed to submit(). Never set in production.
_DEFAULT_TRANSPORT: Optional[httpx.AsyncBaseTransport] = None


# -- models ----------------------------------------------------------------------------------------------------------------
class SupportRequest(BaseModel):
    """Body of POST /support-request. Unknown fields (login_id, user_id, email, recipient ...) are rejected with 422: the user is
    whoever owns the session cookie, as established by WebiDEAL, never a value the browser claims."""
    model_config = ConfigDict(extra="forbid")

    description: str = Field(..., max_length=10000)                 # hard cap only; the real limits are checked in validate()
    category: Optional[str] = Field(None, max_length=64)
    reference_id: Optional[str] = Field(None, max_length=64)        # send the one from a previous answer when retrying
    session_ref: Optional[str] = Field(None, max_length=1000)       # chat session id, for the support team
    last_query: Optional[str] = Field(None, max_length=10000)
    chatbot_answer: Optional[str] = Field(None, max_length=20000)
    asp_session: Optional[str] = Field(None, max_length=1024)       # the user's .AspNetCore.Session cookie value, as for /chat
    lang: Optional[str] = Field(None, max_length=8)


class SupportResponse(BaseModel):
    ok: bool
    code: str
    reference_id: str = ""
    state: str = ""                                                 # "queued" only when ok
    duplicate: bool = False
    retryable: bool = False
    field: str = ""                                                 # for invalid_input: which field
    upstream_code: str = ""                                         # WebiDEAL's own code or a transport-level tag, for diagnostics
    message: str = ""                                               # English fallback; callers should map `code`


_MESSAGES = {
    "ok": "Your report was submitted to the support queue.",
    "duplicate": "This report was already submitted.",
    "invalid_input": "The report is not valid.",
    "session_required": "Please log in again to report an issue.",
    "session_expired": "Your session has expired. Please log in again.",
    "otp_required": "Please complete the verification step and try again.",
    "not_available": "Reporting an issue is not available right now.",
    "rate_limited": "Too many reports. Please try again later.",
    "queue_failed": "The report could not be submitted. Nothing was sent.",
    "unreachable": "The support service could not be reached. Nothing was sent.",
    "upstream_error": "The report could not be submitted. Nothing was sent.",
    "outcome_unknown": "We could not confirm that the report was submitted.",
    "internal_error": "The report could not be submitted. Nothing was sent.",
}
_RETRYABLE = {"queue_failed", "unreachable", "outcome_unknown", "rate_limited", "internal_error"}


def _response(code: str, *, reference: str = "", upstream: str = "", field: str = "", duplicate: bool = False) -> SupportResponse:
    ok = code in ("ok", "duplicate")
    return SupportResponse(ok=ok, code=code, reference_id=reference, state="queued" if ok else "", duplicate=duplicate,
                           retryable=code in _RETRYABLE, field=field, upstream_code=upstream, message=_MESSAGES[code])


# -- validation ------------------------------------------------------------------------------------------------------------
def new_reference() -> str:
    """SR- plus 10 capital hex digits: accepted by WebiDEAL's reference check, unguessable, safe in a subject line."""
    return "SR-" + secrets.token_hex(5).upper()


def _clip(value: Optional[str], limit: int) -> str:
    return (value or "").strip()[:limit]


def validate(req: SupportRequest) -> tuple[Optional[SupportResponse], dict[str, str]]:
    """-> (a ready `invalid_input` answer, {}) or (None, the form fields to post). Nothing is sent when it is rejected."""
    reference = (req.reference_id or "").strip()
    if reference and not _REFERENCE.match(reference):
        return _response("invalid_input", field="reference_id"), {}
    reference = reference or new_reference()

    category = (req.category or "").strip().lower() or "other"
    if category not in CATEGORIES:
        return _response("invalid_input", reference=reference, field="category"), {}

    description = (req.description or "").strip()
    if len(description) < MIN_DESCRIPTION:
        return _response("invalid_input", reference=reference, field="description"), {}
    if len(description) > MAX_DESCRIPTION:
        return _response("invalid_input", reference=reference, field="description"), {}

    form = {
        "ReferenceId": reference,
        "Category": category,
        "Description": description,
        "SessionRef": _clip(req.session_ref, MAX_SESSION_REF),         # context only: cut, not rejected (same as WebiDEAL)
        "LastQuery": _clip(req.last_query, MAX_LAST_QUERY),
        "ChatbotAnswer": _clip(req.chatbot_answer, MAX_ANSWER),
        "AppVersion": version_config.APP_VERSION,                     # this service's own version, never taken from the browser
    }
    return None, form


# -- the call --------------------------------------------------------------------------------------------------------------
def _enabled() -> bool:
    return os.getenv("SUPPORT_REQUEST_ENABLED", "1").strip().lower() not in ("0", "false", "no", "off")


def _timeout() -> httpx.Timeout:
    try:
        read = max(1.0, float(os.getenv("SUPPORT_REQUEST_TIMEOUT_S", "20")))
    except ValueError:
        read = 20.0
    return httpx.Timeout(connect=5.0, read=read, write=10.0, pool=5.0)


def _upstream_url() -> str:
    base = os.getenv("DOTNET_API_URL", "https://localhost:5000").rstrip("/")
    path = os.getenv("DOTNET_SUPPORT_PATH", _DEFAULT_PATH)
    return base + (path if path.startswith("/") else "/" + path)


def _verify() -> bool | str:
    """TLS verification stays ON (as for instance generation); an internal CA can be named in DOTNET_CA_BUNDLE."""
    return os.getenv("DOTNET_CA_BUNDLE", "").strip() or True


def _is_https_upgrade(sent_url: str, location: str) -> bool:
    """The redirect HttpsRedirection issues BEFORE the action runs: same host, https, same path. Nothing was processed, so the
    request can be sent once more to that address. Anything else (the login redirect goes to '/') is not followed."""
    a, b = urllib.parse.urlsplit(sent_url), urllib.parse.urlsplit(urllib.parse.urljoin(sent_url, location))
    return (a.scheme == "http" and b.scheme == "https" and (a.hostname or "").lower() == (b.hostname or "").lower()
            and a.path.rstrip("/").lower() == b.path.rstrip("/").lower())


# WebiDEAL answer code -> this service's code
_UPSTREAM_CODES = {
    "invalid_input": "invalid_input",
    "session_expired": "session_expired",
    "notifications_disabled": "not_available",
    "support_disabled": "not_available",
    "not_configured": "not_available",
    "template_missing": "not_available",
    "user_not_found": "not_available",
    "rate_limited": "rate_limited",
    "queue_failed": "queue_failed",
    "invalid_request": "upstream_error",      # we always send the required header, so this means a mismatch: nothing was queued
    "error": "outcome_unknown",               # WebiDEAL's catch-all: it cannot say whether the queue write had happened
}


def _classify_json(data: Any, reference: str) -> SupportResponse:
    """Map WebiDEAL's JSON answer. Success is accepted only when the whole answer is consistent."""
    if not isinstance(data, dict) or not isinstance(data.get("success"), bool) or not isinstance(data.get("code"), str):
        return _response("outcome_unknown", reference=reference, upstream="bad_json_shape")
    code, success = data["code"], data["success"]
    upstream_ref = data.get("referenceId") if isinstance(data.get("referenceId"), str) else ""
    queued = data.get("state") == "queued"

    if code in ("ok", "duplicate"):
        consistent = success and queued and bool(_REFERENCE.match(upstream_ref)) and (code == "duplicate" or upstream_ref == reference)
        if not consistent:                                            # never claim success from an answer that does not add up
            logger.warning("[SUPPORT] inconsistent success answer code=%s success=%s state=%r", code, success, data.get("state"))
            return _response("outcome_unknown", reference=reference, upstream="inconsistent_success")
        return _response(code, reference=upstream_ref, upstream=code, duplicate=(code == "duplicate"))

    if success:                                                       # success with a code this service does not know
        return _response("outcome_unknown", reference=reference, upstream="unexpected_success:" + code[:40])
    mapped = _UPSTREAM_CODES.get(code)
    if mapped is None:                                                # an unknown failure code: documented as "not queued"
        return _response("upstream_error", reference=reference, upstream="unknown_code:" + code[:40])
    return _response(mapped, reference=upstream_ref or reference, upstream=code)


def _classify_http(resp: httpx.Response, reference: str) -> SupportResponse:
    status = resp.status_code
    text = (resp.text or "").strip()
    if resp.headers.get("x-redirect-to-login"):                      # CustomAuthFilter's answer to an AJAX call without a valid session
        return _response("otp_required" if text == "OtpRequired" else "session_expired", reference=reference,
                         upstream="redirect_header:" + (text[:20] or "empty"))
    if status in (301, 302, 303, 307, 308):                           # the filter's redirect to the login page (Location "/")
        return _response("session_expired", reference=reference, upstream=f"redirect:{status}")
    if status == 200:
        if not text:                                                  # the action always returns JSON: an empty 200 came from the filter
            return _response("session_expired", reference=reference, upstream="empty_200")
        if text in ("SessionExpired", "OtpRequired"):
            return _response("otp_required" if text == "OtpRequired" else "session_expired", reference=reference, upstream="text:" + text)
        try:
            return _classify_json(resp.json(), reference)
        except ValueError:
            return _response("outcome_unknown", reference=reference, upstream="non_json_200")
    if status == 401:
        return _response("session_expired", reference=reference, upstream="http_401")
    if status in (404, 405):                                          # the route is not there: the feature is not deployed
        return _response("not_available", reference=reference, upstream=f"http_{status}")
    if status in (400, 403, 413, 415, 422):                           # refused before the action ran
        return _response("upstream_error", reference=reference, upstream=f"http_{status}")
    return _response("outcome_unknown", reference=reference, upstream=f"http_{status}")   # 5xx and anything else: it may have run


async def _execute(req: SupportRequest, transport: Optional[httpx.AsyncBaseTransport]) -> SupportResponse:
    reference = ""
    sent = False                                                      # True once a request may have reached WebiDEAL
    try:
        if version_config.IS_V6:
            return _response("not_available", upstream="version_6_0")   # the WebiDEAL action exists for 5.5 only
        if not _enabled():
            return _response("not_available", upstream="disabled")

        rejected, form = validate(req)
        if rejected is not None:
            return rejected
        reference = form["ReferenceId"]

        cookie = urllib.parse.unquote((req.asp_session or "").strip())
        if not cookie:                                                # no static fallback cookie, ever: the identity must be the user's own
            return _response("session_required", reference=reference)

        url = _upstream_url()
        headers = {"X-Requested-With": "XMLHttpRequest", "Accept": "application/json"}
        async with httpx.AsyncClient(timeout=_timeout(), follow_redirects=False, verify=_verify(),
                                     transport=transport or _DEFAULT_TRANSPORT) as client:
            sent = True
            resp = await client.post(url, data=form, cookies={_SESSION_COOKIE: cookie}, headers=headers)
            if resp.status_code in (301, 302, 307, 308) and _is_https_upgrade(url, resp.headers.get("location", "")):
                # HttpsRedirection answered before any action ran, so nothing was queued; send once to the https address.
                url = urllib.parse.urljoin(url, resp.headers["location"])
                resp = await client.post(url, data=form, cookies={_SESSION_COOKIE: cookie}, headers=headers)
        result = _classify_http(resp, reference)
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout) as exc:
        result = _response("unreachable", reference=reference, upstream=type(exc).__name__)          # never connected: nothing was sent
    except (httpx.InvalidURL, httpx.UnsupportedProtocol) as exc:
        result = _response("upstream_error", reference=reference, upstream=type(exc).__name__)       # configuration error: not sent
    except httpx.HTTPError as exc:                                    # read/write timeout, reset, protocol error: it may have arrived
        result = _response("outcome_unknown", reference=reference, upstream=type(exc).__name__)
    except Exception as exc:                                          # noqa: BLE001 - this service must answer, never raise
        logger.exception("[SUPPORT] unexpected error before/while sending reference=%s", reference)
        result = _response("outcome_unknown" if sent else "internal_error", reference=reference, upstream=type(exc).__name__)

    return result


async def submit(req: SupportRequest, *, transport: Optional[httpx.AsyncBaseTransport] = None) -> SupportResponse:
    """Validate, forward once, classify. Never raises. Every outcome is logged once."""
    started = time.monotonic()
    result = await _execute(req, transport)
    # The description, the answer text and the session cookie are never logged; the category only when it is one of the fixed values.
    category = (req.category or "").strip().lower() or "other"
    logger.info("[SUPPORT] reference=%s category=%s code=%s upstream=%s duration=%.2fs", result.reference_id or "-",
                category if category in CATEGORIES else "invalid", result.code, result.upstream_code, time.monotonic() - started)
    return result
