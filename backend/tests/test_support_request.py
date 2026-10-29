"""POST /support-request: validation, the call to the iDEAL .NET action, and the mapping of every kind of answer.

The upstream is mocked with httpx.MockTransport: no network, no WebiDEAL, no email. The answers modelled here are the ones the
real ChatbotSupport/SubmitRequest action and its [CustomAuthFilter] produce (observed over real HTTP against the real controller):
  JSON {success, code, message, referenceId, state, duplicate} for everything the action decides;
  200 text/plain + header X-Redirect-To-Login (empty body, "SessionExpired" or "OtpRequired") when the session is not valid;
  302 with Location "/" for non-AJAX calls; 404/405 when the route is not deployed.
"""
from __future__ import annotations

import asyncio
import logging
import urllib.parse

import httpx
import pytest
from fastapi.testclient import TestClient

from backend import main as main_module
from backend.tools import support_request as sr

GOOD = "The answer about my return was wrong, please check it."
COOKIE = "COOKIE-VALUE-SECRET-123"


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setattr(sr.version_config, "IS_V6", False)
    monkeypatch.setattr(sr.version_config, "APP_VERSION", "5.5")
    monkeypatch.setenv("DOTNET_API_URL", "http://dotnet.test:5000")
    for name in ("SUPPORT_REQUEST_ENABLED", "DOTNET_SUPPORT_PATH", "DOTNET_CA_BUNDLE", "SUPPORT_REQUEST_TIMEOUT_S", "DOTNET_SESSION_COOKIE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(sr, "_DEFAULT_TRANSPORT", None)


class Upstream:
    """A mock WebiDEAL: records every request and answers with `respond(request)` (which may also raise an httpx error)."""

    def __init__(self, respond):
        self.respond, self.requests = respond, []

    def __call__(self, request: httpx.Request):
        self.requests.append(request)
        return self.respond(request)

    @property
    def transport(self):
        return httpx.MockTransport(self)

    def form(self, i: int = 0) -> dict[str, str]:
        return {k: v[0] for k, v in urllib.parse.parse_qs(self.requests[i].content.decode(), keep_blank_values=True).items()}


def json_answer(code="ok", success=True, reference="SR-ABC12345", state=None, duplicate=False, status=200):
    state = ("queued" if success else "") if state is None else state
    return lambda req: httpx.Response(status, json={"success": success, "code": code, "message": "m", "referenceId": reference,
                                                   "state": state, "duplicate": duplicate})


def req(**over) -> sr.SupportRequest:
    base = dict(description=GOOD, category="incorrect_answer", reference_id="SR-ABC12345", asp_session=COOKIE)
    base.update(over)
    return sr.SupportRequest(**base)


def run(request: sr.SupportRequest, upstream: Upstream | None = None):
    return asyncio.run(sr.submit(request, transport=upstream.transport if upstream else None))


# ── validation: nothing is sent when the request itself is not acceptable ──────────────────────────────────────────────────────
class TestValidation:
    @pytest.mark.parametrize("over,field", [
        ({"description": "too short"}, "description"),
        ({"description": "   " + "x" * 5 + "   "}, "description"),
        ({"description": "a" * 2001}, "description"),
        ({"category": "urgent!!"}, "category"),
        ({"reference_id": "sr-abc12345"}, "reference_id"),
        ({"reference_id": "SR-AB"}, "reference_id"),
        ({"reference_id": "SR-ABC123\r\nBcc: x@y.z"}, "reference_id"),
        ({"reference_id": "XX-ABC12345"}, "reference_id"),
    ])
    def test_invalid_input_is_rejected_without_calling_upstream(self, over, field):
        up = Upstream(json_answer())

        out = run(req(**over), up)

        assert (out.ok, out.code, out.field) == (False, "invalid_input", field)
        assert up.requests == []

    def test_description_limits_are_inclusive(self):
        up = Upstream(json_answer())
        assert run(req(description="a" * 10), up).ok
        assert run(req(description="a" * 2000, reference_id="SR-ABC12345"), up).ok

    def test_missing_session_cookie_is_session_required_and_nothing_is_sent(self):
        up = Upstream(json_answer())
        for cookie in (None, "", "   "):
            out = run(req(asp_session=cookie), up)
            assert (out.ok, out.code) == (False, "session_required")
        assert up.requests == []

    def test_a_reference_is_generated_when_none_is_given_and_it_is_accepted_by_the_rules(self):
        up = Upstream(lambda r: json_answer(reference=up.form()["ReferenceId"])(r))

        out = run(req(reference_id=None), up)

        assert out.ok and sr._REFERENCE.match(out.reference_id)
        assert up.form()["ReferenceId"] == out.reference_id

    def test_optional_context_is_cut_not_rejected(self):
        up = Upstream(json_answer())

        out = run(req(last_query="q" * 900, chatbot_answer="a" * 3000, session_ref="s" * 500), up)

        assert out.ok
        form = up.form()
        assert (len(form["LastQuery"]), len(form["ChatbotAnswer"]), len(form["SessionRef"])) == (500, 1000, 128)

    def test_category_defaults_to_other_and_is_case_insensitive(self):
        up = Upstream(json_answer())
        run(req(category=None), up)
        run(req(category="Technical_Problem"), up)
        assert [up.form(0)["Category"], up.form(1)["Category"]] == ["other", "technical_problem"]


# ── identity: nothing in the body can name a user ───────────────────────────────────────────────────────────────────────────────
class TestIdentity:
    @pytest.mark.parametrize("field", ["login_id", "user_id", "email", "recipient", "to", "cc", "role_id", "tenant_id", "from"])
    def test_identity_and_recipient_fields_are_rejected_by_the_model(self, field):
        with pytest.raises(Exception):
            sr.SupportRequest(description=GOOD, asp_session=COOKIE, **{field: "someone"})

    def test_the_model_has_no_field_that_could_carry_an_identity(self):
        names = set(sr.SupportRequest.model_fields)
        assert not [n for n in names if any(w in n for w in ("login", "user", "email", "recipient")) or n in ("to", "cc", "bcc", "from")]

    def test_the_form_sent_upstream_carries_no_identity_and_the_version_is_the_services_own(self):
        up = Upstream(json_answer())

        run(req(), up)

        assert set(up.form()) == {"ReferenceId", "Category", "Description", "SessionRef", "LastQuery", "ChatbotAnswer", "AppVersion"}
        assert up.form()["AppVersion"] == "5.5"


# ── the request to WebiDEAL ──────────────────────────────────────────────────────────────────────────────────────────────────────
class TestUpstreamRequest:
    def test_route_method_headers_and_form(self):
        up = Upstream(json_answer())

        run(req(), up)

        r = up.requests[0]
        assert (r.method, str(r.url)) == ("POST", "http://dotnet.test:5000/ChatbotSupport/SubmitRequest")
        assert r.headers["x-requested-with"] == "XMLHttpRequest"
        assert r.headers["content-type"].startswith("application/x-www-form-urlencoded")
        assert up.form()["Description"] == GOOD and up.form()["Category"] == "incorrect_answer"

    def test_the_users_session_cookie_is_forwarded_as_the_aspnet_session_cookie(self):
        up = Upstream(json_answer())

        run(req(asp_session=urllib.parse.quote("a/b+c=")), up)

        assert up.requests[0].headers["cookie"] == ".AspNetCore.Session=a/b+c="      # percent-decoded, like instance generation

    def test_the_static_fallback_cookie_is_never_used(self, monkeypatch):
        monkeypatch.setenv("DOTNET_SESSION_COOKIE", "shared-service-account")
        monkeypatch.setenv("ALLOW_STATIC_DOTNET_COOKIE", "true")
        up = Upstream(json_answer())

        out = run(req(asp_session=None), up)

        assert out.code == "session_required" and up.requests == []

    def test_unicode_description_survives_the_form_encoding(self):
        up = Upstream(json_answer())
        text = "रिपोर्ट गलत है — خطأ في التقرير — résumé incorrect"

        run(req(description=text), up)

        assert up.form()["Description"] == text

    def test_url_base_path_and_override(self, monkeypatch):
        monkeypatch.setenv("DOTNET_API_URL", "https://host/WebiDEAL/")
        monkeypatch.setenv("DOTNET_SUPPORT_PATH", "Support/Submit")
        up = Upstream(json_answer())
        run(req(), up)
        assert str(up.requests[0].url) == "https://host/WebiDEAL/Support/Submit"

    def test_it_never_follows_a_redirect_with_the_cookie_to_another_place(self):
        up = Upstream(lambda r: httpx.Response(302, headers={"location": "https://evil.example/steal"}))

        out = run(req(), up)

        assert len(up.requests) == 1 and out.code == "session_expired" and not out.ok


# ── answers: success is only what WebiDEAL says it is ─────────────────────────────────────────────────────────────────────────
class TestSuccess:
    def test_ok_means_queued_and_nothing_more(self):
        out = run(req(), Upstream(json_answer()))

        assert (out.ok, out.code, out.state, out.duplicate, out.reference_id) == (True, "ok", "queued", False, "SR-ABC12345")
        assert out.retryable is False

    def test_duplicate_is_success_and_carries_the_original_reference(self):
        out = run(req(reference_id="SR-NEWREF123"), Upstream(json_answer("duplicate", reference="SR-ORIGINAL1", duplicate=True)))

        assert (out.ok, out.code, out.duplicate, out.reference_id) == (True, "duplicate", True, "SR-ORIGINAL1")

    @pytest.mark.parametrize("answer", [
        json_answer("ok", success=False),                               # success flag disagrees with the code
        json_answer("ok", state=""),                                    # not marked as queued
        json_answer("ok", reference="SR-OTHER9999"),                    # a different reference than the one sent
        json_answer("ok", reference=""),                                # no reference
        json_answer("duplicate", state=""),
        json_answer("queued_somehow", success=True),                    # success with a code nobody documented
    ])
    def test_an_answer_that_does_not_add_up_is_never_success(self, answer):
        out = run(req(), Upstream(answer))

        assert out.ok is False and out.code == "outcome_unknown"


class TestUpstreamCodes:
    @pytest.mark.parametrize("upstream,expected,retryable", [
        ("invalid_input", "invalid_input", False),
        ("session_expired", "session_expired", False),
        ("notifications_disabled", "not_available", False),
        ("support_disabled", "not_available", False),
        ("not_configured", "not_available", False),
        ("template_missing", "not_available", False),
        ("user_not_found", "not_available", False),
        ("rate_limited", "rate_limited", True),
        ("queue_failed", "queue_failed", True),
        ("invalid_request", "upstream_error", False),
        ("error", "outcome_unknown", True),                            # WebiDEAL cannot say whether the queue write happened
        ("some_future_code", "upstream_error", False),                 # failure with an unknown code: documented as "not queued"
    ])
    def test_every_notifier_code_maps_to_one_stable_code(self, upstream, expected, retryable):
        out = run(req(), Upstream(json_answer(upstream, success=False)))

        assert (out.ok, out.code, out.retryable) == (False, expected, retryable)
        assert upstream in out.upstream_code
        assert out.message and out.state == ""

    def test_the_support_team_never_sees_internal_detail_in_the_message(self):
        out = run(req(), Upstream(json_answer("template_missing", success=False)))

        assert "xml" not in out.message.lower() and "template" not in out.message.lower()


# ── answers that are not JSON: the situations CustomAuthFilter and the web server produce ───────────────────────────────────
class TestNonJsonAnswers:
    @pytest.mark.parametrize("response,expected", [
        (httpx.Response(200, headers={"x-redirect-to-login": "true", "content-type": "text/plain"}), "session_expired"),
        (httpx.Response(200, text="SessionExpired", headers={"x-redirect-to-login": "true", "content-type": "text/plain"}), "session_expired"),
        (httpx.Response(200, text="OtpRequired", headers={"x-redirect-to-login": "true", "content-type": "text/plain"}), "otp_required"),
        (httpx.Response(200, text="SessionExpired"), "session_expired"),         # header stripped by a proxy
        (httpx.Response(200), "session_expired"),                                # an empty 200: the action always returns JSON
        (httpx.Response(302, headers={"location": "/"}), "session_expired"),     # the login redirect (Location is "/" in this app)
        (httpx.Response(302, headers={"location": "/Login/Login"}), "session_expired"),
        (httpx.Response(401), "session_expired"),
        (httpx.Response(404), "not_available"),                                  # the route is not deployed
        (httpx.Response(405), "not_available"),
        (httpx.Response(400), "upstream_error"),
        (httpx.Response(403), "upstream_error"),
        (httpx.Response(413), "upstream_error"),
        (httpx.Response(415), "upstream_error"),
        (httpx.Response(200, text="<html>Error</html>", headers={"content-type": "text/html"}), "outcome_unknown"),
        (httpx.Response(200, text="not json {"), "outcome_unknown"),
        (httpx.Response(200, json=["a", "list"]), "outcome_unknown"),
        (httpx.Response(200, json={"success": "yes", "code": "ok"}), "outcome_unknown"),
        (httpx.Response(500), "outcome_unknown"),
        (httpx.Response(502), "outcome_unknown"),
        (httpx.Response(503), "outcome_unknown"),
        (httpx.Response(504), "outcome_unknown"),
        (httpx.Response(204), "outcome_unknown"),                                 # not an answer the action or the filter gives
    ])
    def test_classification(self, response, expected):
        up = Upstream(lambda r: response)

        out = run(req(), up)

        assert out.code == expected and out.ok is False and out.state == ""
        assert len(up.requests) == 1                                              # exactly one attempt

    def test_https_upgrade_redirect_is_followed_exactly_once_to_the_same_host_and_path(self):
        calls = []

        def respond(request):
            calls.append(str(request.url))
            if request.url.scheme == "http":
                return httpx.Response(307, headers={"location": "https://dotnet.test:5001/ChatbotSupport/SubmitRequest"})
            return json_answer()(request)

        up = Upstream(respond)

        out = run(req(), up)

        assert out.ok and calls == ["http://dotnet.test:5000/ChatbotSupport/SubmitRequest", "https://dotnet.test:5001/ChatbotSupport/SubmitRequest"]
        assert up.requests[1].headers["cookie"] == ".AspNetCore.Session=" + COOKIE

    def test_a_redirect_that_is_not_an_https_upgrade_is_not_followed(self):
        for location in ("https://other.test/ChatbotSupport/SubmitRequest", "/", "https://dotnet.test:5001/Account/Login", "http://dotnet.test:5000/x"):
            up = Upstream(lambda r, loc=location: httpx.Response(302, headers={"location": loc}))
            out = run(req(), up)
            assert len(up.requests) == 1 and out.code == "session_expired"


# ── transport failures: not sent vs may have been sent ────────────────────────────────────────────────────────────────────────
class TestTransportFailures:
    @pytest.mark.parametrize("error,expected", [
        (httpx.ConnectError("refused"), "unreachable"),
        (httpx.ConnectTimeout("slow connect"), "unreachable"),
        (httpx.PoolTimeout("no connection"), "unreachable"),
        (httpx.ReadTimeout("no answer"), "outcome_unknown"),
        (httpx.WriteTimeout("stalled"), "outcome_unknown"),
        (httpx.ReadError("reset"), "outcome_unknown"),
        (httpx.RemoteProtocolError("bad framing"), "outcome_unknown"),
    ])
    def test_classification_and_no_automatic_retry(self, error, expected):
        def respond(request):
            raise error

        up = Upstream(respond)

        out = run(req(), up)

        assert (out.ok, out.code, out.retryable, out.reference_id) == (False, expected, True, "SR-ABC12345")
        assert len(up.requests) == 1                                              # a timeout is never retried here

    def test_a_timeout_answer_carries_the_reference_so_a_caller_can_retry_without_a_double_submit(self):
        def respond(request):
            raise httpx.ReadTimeout("no answer")

        first = run(req(reference_id=None), Upstream(respond))
        retry = Upstream(json_answer("duplicate", reference=first.reference_id, duplicate=True))

        again = run(req(reference_id=first.reference_id), retry)

        assert first.code == "outcome_unknown" and sr._REFERENCE.match(first.reference_id)
        assert retry.form()["ReferenceId"] == first.reference_id and again.code == "duplicate" and again.ok

    def test_an_unexpected_internal_error_after_sending_is_unknown_never_success(self, monkeypatch):
        monkeypatch.setattr(sr, "_classify_http", lambda resp, ref: (_ for _ in ()).throw(RuntimeError("bug")))

        out = run(req(), Upstream(json_answer()))

        assert (out.ok, out.code) == (False, "outcome_unknown")


# ── switches ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
class TestSwitches:
    def test_version_6_0_is_not_available_and_nothing_is_sent(self, monkeypatch):
        monkeypatch.setattr(sr.version_config, "IS_V6", True)
        up = Upstream(json_answer())

        out = run(req(), up)

        assert (out.ok, out.code, out.upstream_code) == (False, "not_available", "version_6_0") and up.requests == []

    @pytest.mark.parametrize("value", ["0", "false", "no", "off"])
    def test_kill_switch(self, monkeypatch, value):
        monkeypatch.setenv("SUPPORT_REQUEST_ENABLED", value)
        up = Upstream(json_answer())

        out = run(req(), up)

        assert (out.code, out.upstream_code) == ("not_available", "disabled") and up.requests == []


# ── privacy ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
class TestPrivacy:
    def test_logs_contain_neither_the_cookie_nor_the_user_text(self, caplog):
        caplog.set_level(logging.DEBUG)
        secret_text = "PRIVATE-TEXT-ABOUT-MY-CLIENT-ACCOUNT"
        up = Upstream(json_answer())
        asyncio.run(sr.submit(req(description=secret_text + " and more", last_query="PRIVATE-QUERY", chatbot_answer="PRIVATE-ANSWER"),
                              transport=up.transport))
        asyncio.run(sr.submit(req(description=secret_text + " again", category="evil\nINJECTED LOG LINE"), transport=up.transport))

        text = caplog.text
        assert "[SUPPORT]" in text
        for secret in (COOKIE, "PRIVATE-TEXT", "PRIVATE-QUERY", "PRIVATE-ANSWER", "INJECTED LOG LINE"):
            assert secret not in text

    def test_the_answer_never_echoes_the_user_text_or_the_cookie(self):
        out = run(req(), Upstream(json_answer()))

        dumped = out.model_dump_json()
        assert COOKIE not in dumped and GOOD not in dumped


# ── the HTTP endpoint ─────────────────────────────────────────────────────────────────────────────────────────────────────────────
@pytest.fixture
def client():
    main_module.rate_limit.limiter.reset()
    yield TestClient(main_module.app)
    main_module.rate_limit.limiter.reset()


class TestEndpoint:
    BODY = {"description": GOOD, "category": "incorrect_answer", "reference_id": "SR-ABC12345", "asp_session": COOKIE}

    def test_success_shape(self, client, monkeypatch):
        monkeypatch.setattr(sr, "_DEFAULT_TRANSPORT", Upstream(json_answer()).transport)

        res = client.post("/support-request", json=self.BODY)

        assert res.status_code == 200
        assert res.json() == {"ok": True, "code": "ok", "reference_id": "SR-ABC12345", "state": "queued", "duplicate": False,
                              "retryable": False, "field": "", "upstream_code": "ok", "message": sr._MESSAGES["ok"]}

    def test_failures_are_http_200_with_ok_false_and_a_code(self, client, monkeypatch):
        monkeypatch.setattr(sr, "_DEFAULT_TRANSPORT", Upstream(lambda r: httpx.Response(200, headers={"x-redirect-to-login": "true"})).transport)

        res = client.post("/support-request", json=self.BODY)

        assert res.status_code == 200 and res.json()["ok"] is False and res.json()["code"] == "session_expired"

    def test_invalid_input_is_a_normal_answer(self, client):
        res = client.post("/support-request", json={**self.BODY, "description": "short"})

        assert res.status_code == 200
        assert (res.json()["ok"], res.json()["code"], res.json()["field"]) == (False, "invalid_input", "description")

    @pytest.mark.parametrize("field", ["login_id", "user_id", "email", "recipient"])
    def test_identity_fields_in_the_body_are_a_422(self, client, field):
        res = client.post("/support-request", json={**self.BODY, field: "someone"})

        assert res.status_code == 422

    def test_malformed_body_is_a_422(self, client):
        assert client.post("/support-request", json={"category": "other"}).status_code == 422
        assert client.post("/support-request", json={**self.BODY, "description": ["x"]}).status_code == 422

    def test_the_path_is_rate_limited_like_the_other_expensive_endpoints(self, client, monkeypatch):
        assert "/support-request" in main_module._RATE_LIMITED_PATHS
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
        monkeypatch.setenv("RATE_LIMIT_MAX_REQUESTS", "2")
        monkeypatch.setattr(sr, "_DEFAULT_TRANSPORT", Upstream(json_answer()).transport)

        codes = [client.post("/support-request", json=self.BODY).status_code for _ in range(3)]

        assert codes == [200, 200, 429]

    def test_existing_endpoints_are_unaffected(self, client):
        assert client.post("/feedback", json={"rating": "up"}).json() == {"ok": True}
        assert client.get("/health").json() == {"status": "ok"}
