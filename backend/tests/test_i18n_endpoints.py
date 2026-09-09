"""Endpoint-level tests for the multilingual boundary: /chat and /guided.

These cover what backend/tests/test_i18n_boundary.py deliberately cannot --
the wiring in main.py, ChatRequest.lang, and ChatResponse serialization.

decide() and guided_step() are replaced with recording stubs. That is the whole
point: the assertion that matters is what the ENGLISH PIPELINE RECEIVES. The
real decide() is never called and never modified.

TestClient is constructed without a context manager so the lifespan hook (and
its SentenceTransformer/FAISS/Ollama warm-up) does not run.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend import main as main_module
from backend.i18n.translator import TranslationResult
from backend.models import ChatResponse

REGULATORY_IDS = ["DBR01", "CIMS_ROR", "CIMS_RAQ(Monthly)", "RAQ(Quarterly)"]


@pytest.fixture
def client():
    return TestClient(main_module.app)


@pytest.fixture(autouse=True)
def _enabled(monkeypatch):
    monkeypatch.setenv("MULTILINGUAL_ENABLED", "true")
    monkeypatch.setenv("TRANSLATION_MODEL", "qwen3:14b")
    monkeypatch.setenv("SUPPORTED_LANGUAGES", "en,fr,ar,hi")
    monkeypatch.setenv("TRANSLATION_MAX_CHARS", "2000")


class Recorder:
    """Stands in for decide()/guided_step() and records what it was handed."""

    def __init__(self, response=None):
        self.calls: list[dict] = []
        self.response = response or {
            "intent": "get_status",
            "report_name": "DBR01",
            "response_text": "Report 'DBR01' completed on 31-03-2025.",
            "result_type": "final",
            "options": [],
        }

    async def __call__(self, message, **kwargs):
        self.calls.append({"message": message, **kwargs})
        return dict(self.response)

    @property
    def seen(self) -> str:
        return self.calls[0]["message"]


class StubTranslator:
    name = "stub"

    def __init__(self, transform=None, ok=True, error=None):
        self.calls: list[tuple[str, str, str]] = []
        self._transform = transform or (lambda t: f"[{t}]")
        self._ok = ok
        self._error = error

    async def translate(self, text, src, tgt):
        self.calls.append((text, src, tgt))
        if not self._ok:
            return TranslationResult(text=text, latency_ms=1.0, ok=False,
                                     error=self._error, model="stub")
        return TranslationResult(text=self._transform(text), latency_ms=1.0,
                                 ok=True, model="stub")


def _install(monkeypatch, decide=None, guided=None, translator=None):
    if decide is not None:
        monkeypatch.setattr(main_module, "decide", decide)
    if guided is not None:
        monkeypatch.setattr(main_module, "guided_step", guided)
    if translator is not None:
        # **kwargs tolerates /compare-summary's get_translator(timeout=...,
        # model=..., base_url=...) call as well as every other call site's
        # zero-arg one. Calls are recorded onto the translator itself so a
        # test can assert exactly what /compare-summary requested.
        calls: list[dict] = []
        translator.get_translator_calls = calls

        def _get_translator(**kwargs):
            calls.append(kwargs)
            return translator

        monkeypatch.setattr("backend.i18n.boundary.get_translator", _get_translator)


# ---------------------------------------------------------------------------
# A. Existing English behaviour is unchanged
# ---------------------------------------------------------------------------

def test_no_lang_field_behaves_exactly_as_before(client, monkeypatch):
    rec, tr = Recorder(), StubTranslator()
    _install(monkeypatch, decide=rec, translator=tr)

    resp = client.post("/chat", json={"message": "status of DBR01"})
    assert resp.status_code == 200
    body = resp.json()

    assert rec.seen == "status of DBR01", "pipeline must see the original message"
    assert tr.calls == [], "no model call without a lang"
    assert body["response_text"] == "Report 'DBR01' completed on 31-03-2025."
    assert body["data"] == {}, "no i18n metadata added on the English path"


def test_lang_en_behaves_exactly_as_before(client, monkeypatch):
    rec, tr = Recorder(), StubTranslator()
    _install(monkeypatch, decide=rec, translator=tr)
    body = client.post("/chat", json={"message": "status of DBR01", "lang": "en"}).json()
    assert rec.seen == "status of DBR01"
    assert tr.calls == []
    assert body["data"] == {}


def test_multilingual_disabled_is_a_full_no_op(client, monkeypatch):
    monkeypatch.setenv("MULTILINGUAL_ENABLED", "false")
    rec, tr = Recorder(), StubTranslator()
    _install(monkeypatch, decide=rec, translator=tr)

    body = client.post("/chat", json={"message": "bonjour", "lang": "fr"}).json()
    assert rec.seen == "bonjour", "message reaches the pipeline untranslated"
    assert tr.calls == [], "kill switch must prevent every model call"
    assert body["data"] == {}


def test_english_response_identical_with_feature_on_and_off(client, monkeypatch):
    """The regression that matters most: turning the feature on must not change
    a single byte of an English turn."""
    bodies = []
    for enabled in ("false", "true"):
        monkeypatch.setenv("MULTILINGUAL_ENABLED", enabled)
        _install(monkeypatch, decide=Recorder(), translator=StubTranslator())
        bodies.append(client.post("/chat", json={"message": "status of DBR01"}).json())
    assert bodies[0] == bodies[1]


# ---------------------------------------------------------------------------
# B. The round trip, FR / AR / HI
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("lang,question", [
    ("fr", "quel est le statut de DBR01"),
    ("ar", "ما هي حالة DBR01"),
    ("hi", "DBR01 की स्थिति क्या है"),
])
def test_full_round_trip(client, monkeypatch, lang, question):
    rec = Recorder()
    tr = StubTranslator(
        transform=lambda t: "what is the status of DBR01"
        if t == question else f"[{lang}]{t}"
    )
    _install(monkeypatch, decide=rec, translator=tr)

    body = client.post("/chat", json={"message": question, "lang": lang}).json()

    # The English pipeline received English.
    assert rec.seen == "what is the status of DBR01"
    # Inbound targeted English, outbound targeted the user's language.
    assert tr.calls[0] == (question, lang, "en")
    assert tr.calls[1][1:] == ("en", lang)
    # The user got a localized answer plus the English source for history.
    assert body["response_text"].startswith(f"[{lang}]")
    assert body["data"]["i18n"]["lang"] == lang
    assert body["data"]["i18n"]["english"]["user_message"] == "what is the status of DBR01"
    assert (body["data"]["i18n"]["english"]["response_text"]
            == "Report 'DBR01' completed on 31-03-2025.")


def test_exactly_two_model_calls_per_translated_turn(client, monkeypatch):
    rec, tr = Recorder(), StubTranslator()
    _install(monkeypatch, decide=rec, translator=tr)
    client.post("/chat", json={"message": "quel est le statut", "lang": "fr"})
    assert len(tr.calls) == 2, "one inbound, one outbound -- never more"


def test_unsupported_language_falls_back_to_english(client, monkeypatch):
    rec, tr = Recorder(), StubTranslator()
    _install(monkeypatch, decide=rec, translator=tr)
    resp = client.post("/chat", json={"message": "wie ist der status", "lang": "de"})
    assert resp.status_code == 200, "must be served, not refused"
    assert rec.seen == "wie ist der status"
    assert tr.calls == []


# ---------------------------------------------------------------------------
# C. Inbound failure must never reach the pipeline
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("error", [
    "ReadTimeout: timed out",
    "HTTPStatusError: 502",
    "ConnectError: connection refused",
    "empty translation after cleaning",
])
def test_inbound_failure_never_calls_decide(client, monkeypatch, error):
    rec = Recorder()
    _install(monkeypatch, decide=rec, translator=StubTranslator(ok=False, error=error))

    resp = client.post("/chat", json={"message": "quel est le statut", "lang": "fr"})
    body = resp.json()

    assert resp.status_code == 200
    assert rec.calls == [], "THE critical guarantee: no routing on a bad translation"
    assert body["result_type"] == "error"
    assert body["response_text"] and "Désolé" in body["response_text"]
    assert body["data"]["i18n"]["inbound"]["ok"] is False


def test_outbound_failure_still_returns_the_english_answer(client, monkeypatch):
    rec = Recorder()

    class InboundOnly:
        name = "inbound-only"

        def __init__(self):
            self.n = 0

        async def translate(self, text, src, tgt):
            self.n += 1
            if tgt == "en":
                return TranslationResult(text="what is the status of DBR01",
                                         latency_ms=1.0, ok=True)
            return TranslationResult(text=text, latency_ms=1.0, ok=False, error="502")

    _install(monkeypatch, decide=rec, translator=InboundOnly())
    body = client.post("/chat", json={"message": "quel est le statut", "lang": "fr"}).json()

    assert body["result_type"] == "final", "the answer is still delivered"
    assert body["response_text"] == "Report 'DBR01' completed on 31-03-2025."
    assert body["status_note"], "user is told why it is English"


# ---------------------------------------------------------------------------
# D. Multi-turn selection and identifiers
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("reply", ["1", "2", "162"])
def test_numeric_reply_reaches_the_pipeline_untouched(client, monkeypatch, reply):
    """agent/__init__.py:1103 does int(raw_input)."""
    rec, tr = Recorder(), StubTranslator()
    _install(monkeypatch, decide=rec, translator=tr)
    client.post("/chat", json={"message": reply, "lang": "ar"})
    assert rec.seen == reply
    assert int(rec.seen) == int(reply)
    assert all(c[2] != "en" for c in tr.calls), "no inbound call for a numeric reply"


@pytest.mark.parametrize("identifier", REGULATORY_IDS)
def test_identifier_reply_reaches_the_pipeline_verbatim(client, monkeypatch, identifier):
    """The staged matcher at agent/__init__.py:1119-1122 is a raw ASCII
    substring test against the English name."""
    rec, tr = Recorder(), StubTranslator()
    _install(monkeypatch, decide=rec, translator=tr)
    client.post("/chat", json={"message": identifier, "lang": "hi"})
    assert rec.seen == identifier
    assert all(c[2] != "en" for c in tr.calls)


def test_162_option_disambiguation_over_http(client, monkeypatch):
    options = [f"CIMS_REPORT_{i:03d}_LONG_REGULATORY_NAME" for i in range(1, 163)]
    opts_text = "\n".join(f"{i + 1}. {n}" for i, n in enumerate(options))
    rec = Recorder({
        "intent": "get_status", "report_name": None,
        "response_text": (
            f"I found {len(options)} matching reports. Which one are you looking for?"
            f"\n\n{opts_text}\n\nReply with the number or part of the name."
        ),
        "result_type": "disambiguation", "options": options,
    })
    tr = StubTranslator()
    _install(monkeypatch, decide=rec, translator=tr)

    body = client.post("/chat", json={"message": "rapports", "lang": "fr"}).json()

    sent = "\n".join(c[0] for c in tr.calls)
    for name in options:
        assert name not in sent, f"{name} was sent to the translation model"
        assert name in body["response_text"], f"{name} missing from the reply"
    assert body["options"] == options, "options[] must survive serialization intact"
    assert body["data"]["i18n"]["outbound"]["options_count"] == 162
    assert body["data"]["i18n"]["outbound"]["chars_sent"] < 200


def test_conversation_history_is_passed_through_untranslated(client, monkeypatch):
    """Decision 4: history stays English and costs zero extra model calls."""
    rec, tr = Recorder(), StubTranslator()
    _install(monkeypatch, decide=rec, translator=tr)
    history = [
        {"role": "user", "text": "what is the status of DBR01"},
        {"role": "assistant", "text": "Report 'DBR01' completed on 31-03-2025."},
    ]
    client.post("/chat", json={
        "message": "et RAQ", "lang": "fr", "conversation_history": history,
    })
    assert rec.calls[0]["conversation_history"] == history
    assert len(tr.calls) == 2, "history must not add a single translation call"


# ---------------------------------------------------------------------------
# E. /guided -- outbound only, by design
# ---------------------------------------------------------------------------

def test_guided_never_translates_inbound(client, monkeypatch):
    """guided.py:179-180 matches GUIDED_ACTIONS as English literals, and step 2
    takes the message verbatim as a report name."""
    from backend.guided import GUIDED_ACTIONS

    for label in GUIDED_ACTIONS:
        rec = Recorder({"response_text": "Which report?", "result_type": "final",
                        "options": []})
        tr = StubTranslator()
        _install(monkeypatch, guided=rec, translator=tr)
        client.post("/guided", json={"message": label, "lang": "fr"})
        assert rec.seen == label, f"guided action {label!r} must arrive verbatim"
        assert all(c[2] != "en" for c in tr.calls), "no inbound call on /guided"


@pytest.mark.parametrize("message", ["__GUIDED_START__", "CIMS_ROR", "DBR01"])
def test_guided_passes_sentinel_and_names_verbatim(client, monkeypatch, message):
    rec = Recorder({"response_text": "Menu", "result_type": "final", "options": []})
    tr = StubTranslator()
    _install(monkeypatch, guided=rec, translator=tr)
    client.post("/guided", json={"message": message, "lang": "ar"})
    assert rec.seen == message
    assert all(c[2] != "en" for c in tr.calls)


def test_guided_localizes_the_response(client, monkeypatch):
    rec = Recorder({"response_text": "Which report would you like?",
                    "result_type": "final", "options": []})
    tr = StubTranslator()
    _install(monkeypatch, guided=rec, translator=tr)
    body = client.post("/guided", json={"message": "__GUIDED_START__", "lang": "fr"}).json()
    assert body["response_text"] == "[Which report would you like?]"
    assert body["data"]["i18n"]["lang"] == "fr"


def test_guided_english_path_unchanged(client, monkeypatch):
    rec, tr = Recorder({"response_text": "Menu", "result_type": "final",
                        "options": []}), StubTranslator()
    _install(monkeypatch, guided=rec, translator=tr)
    body = client.post("/guided", json={"message": "__GUIDED_START__"}).json()
    assert body["response_text"] == "Menu"
    assert tr.calls == [] and body["data"] == {}


# ---------------------------------------------------------------------------
# F. Request/response contract
# ---------------------------------------------------------------------------

def test_lang_is_optional_on_the_request_model():
    from backend.models import ChatRequest
    assert ChatRequest(message="x").lang is None


def test_chat_response_shape_is_unchanged():
    """No field added to ChatResponse, none renamed. The i18n metadata lives
    inside the pre-existing free-form `data` dict."""
    fields = set(ChatResponse.model_fields)
    assert "lang" not in fields
    assert "options_display" not in fields
    assert "response_text_en" not in fields
    assert {"response_text", "options", "data"} <= fields


def test_an_over_long_lang_tag_is_rejected_by_validation(client):
    resp = client.post("/chat", json={"message": "x", "lang": "x" * 64})
    assert resp.status_code == 422


def test_decide_is_called_with_the_same_kwargs_as_before(client, monkeypatch):
    """The wrapper must not alter the call signature the pipeline relies on."""
    rec = Recorder()
    _install(monkeypatch, decide=rec, translator=StubTranslator())
    client.post("/chat", json={
        "message": "status of DBR01", "session_id": "s1", "login_id": "u1",
        "user_id": "42", "role_id": "101", "asp_session": "cookie",
    })
    call = rec.calls[0]
    assert set(call) == {
        "message", "session_id", "asp_session", "login_id", "user_id",
        "role_id", "conversation_history",
    }
    assert call["session_id"] == "s1" and call["login_id"] == "u1"
    assert call["user_id"] == "42" and call["role_id"] == "101"


# ---------------------------------------------------------------------------
# G. /compare-execute, /compare-summary, /explain-category
# ---------------------------------------------------------------------------
#
# These three carry the Comparative Analysis output, including the AI Analysis
# narrative. They shipped English because the FRONTEND never sent `lang`; the
# wire side is covered by frontend/scripts/check-lang-propagation.mjs, and this
# covers the server side.

LANGS_ALL = ("en", "fr", "ar", "hi")


@pytest.mark.parametrize("lang", LANGS_ALL)
def test_compare_execute_honours_lang(client, monkeypatch, lang):
    rec = Recorder({
        "intent": "compare_reports", "report_name": "RAQ(Monthly)",
        "response_text": "Variance Analysis — RAQ(Monthly)\n"
                         "Comparing: 30-Jun-2026  vs  30-Sep-2025",
        "result_type": "variance_table", "options": [],
        "variance_data": [{"concept": "AmountOutstanding", "val_a": 1, "val_b": 2}],
        "variance_label_a": "30-Jun-2026", "variance_label_b": "30-Sep-2025",
    })

    async def _execute(*args, **kwargs):
        return dict(rec.response)

    monkeypatch.setattr("backend.agent.execute_comparison", _execute, raising=False)
    _install(monkeypatch, translator=StubTranslator())

    body = {"session_id": "s1", "instance_a": 0, "instance_b": 1}
    if lang != "en":
        body["lang"] = lang
    resp = client.post("/compare-execute", json=body)
    assert resp.status_code == 200
    data = resp.json()

    # The header is catalogued, so it localizes with no model call.
    if lang == "en":
        assert data["response_text"].startswith("Variance Analysis")
        assert data["data"] == {}
    else:
        assert not data["response_text"].startswith("Variance Analysis"), (
            f"{lang}: the variance header came back English"
        )
        assert data["data"]["i18n"]["lang"] == lang
    # Data is never touched.
    assert data["variance_label_a"] == "30-Jun-2026"
    assert data["report_name"] == "RAQ(Monthly)"
    assert "RAQ(Monthly)" in data["response_text"]


def test_compare_summary_requests_its_own_model_override(client, monkeypatch):
    """/compare-summary must ask for compare_summary_translation_model()
    (aya-expanse:8b, benchmarked faster+safer for this narrative), NOT
    TRANSLATION_MODEL (qwen3:14b, still used everywhere else)."""
    async def _generate(*args, **kwargs):
        return "Amount Outstanding — Domestic increased from Rs 4,855 Cr to Rs 506,108 Cr."

    monkeypatch.setattr("backend.tools.variance_explain.generate_explanations",
                        _generate, raising=False)
    tr = StubTranslator()
    _install(monkeypatch, translator=tr)

    resp = client.post("/compare-summary", json={
        "rows": [{"concept": "AmountOutstanding", "val_a": 1.0, "val_b": 2.0}],
        "label_a": "30-Jun-2026", "label_b": "30-Sep-2025",
        "report_name": "RAQ(Monthly)", "lang": "fr",
    })
    assert resp.status_code == 200
    assert tr.get_translator_calls, "get_translator was never called"
    kwargs = tr.get_translator_calls[-1]
    assert kwargs.get("model") == "aya-expanse:8b"
    assert kwargs.get("model") != "qwen3:14b"
    assert kwargs.get("timeout") == 180.0


@pytest.mark.parametrize("lang", ("hi", "fr", "ar"))
def test_compare_summary_falls_back_to_english_when_translation_is_unsafe(client, monkeypatch, lang):
    """A translation that corrupts a protected placeholder (dropped, or an
    invented bare number alongside an intact one -- the two failure modes
    measured on aya-expanse:8b) must never reach the user: /compare-summary
    keeps the English narrative instead, via the SAME 'keep English'
    fallback any other translation failure already uses."""
    narrative = "Amount Outstanding — Domestic increased from Rs 4,855 Cr to Rs 506,108 Cr for CIMS_ROR."

    async def _generate(*args, **kwargs):
        return narrative

    monkeypatch.setattr("backend.tools.variance_explain.generate_explanations",
                        _generate, raising=False)

    # Drops every placeholder outright -- an aggressively unsafe "translation".
    tr = StubTranslator(transform=lambda t: "Le montant a augmenté de manière significative.")
    _install(monkeypatch, translator=tr)

    resp = client.post("/compare-summary", json={
        "rows": [{"concept": "AmountOutstanding", "val_a": 1.0, "val_b": 2.0}],
        "label_a": "30-Jun-2026", "label_b": "30-Sep-2025",
        "report_name": "RAQ(Monthly)", "lang": lang,
    })
    assert resp.status_code == 200
    summary = resp.json()["llm_summary"]
    assert summary == narrative, (
        f"{lang}: an unsafe translation reached the user instead of falling back to English"
    )


@pytest.mark.parametrize("lang", ("hi", "fr", "ar"))
def test_compare_summary_invented_number_also_falls_back(client, monkeypatch, lang):
    """The specific defect observed on aya-expanse:8b: placeholders survive
    intact, but an illustrative figure is fabricated in the surrounding
    prose. protect.restore_entities() alone would not catch this -- the
    PlaceholderSafeTranslator guardrail must."""
    narrative = "Amount Outstanding — Domestic increased from Rs 4,855 Cr to Rs 506,108 Cr for CIMS_ROR."

    async def _generate(*args, **kwargs):
        return narrative

    monkeypatch.setattr("backend.tools.variance_explain.generate_explanations",
                        _generate, raising=False)

    def _invent_a_number(masked_text: str) -> str:
        # Echo the masked text back (placeholders intact) but with a
        # fabricated figure inserted -- exactly the observed defect shape.
        return "500 million rupees, " + masked_text

    tr = StubTranslator(transform=_invent_a_number)
    _install(monkeypatch, translator=tr)

    resp = client.post("/compare-summary", json={
        "rows": [{"concept": "AmountOutstanding", "val_a": 1.0, "val_b": 2.0}],
        "label_a": "30-Jun-2026", "label_b": "30-Sep-2025",
        "report_name": "RAQ(Monthly)", "lang": lang,
    })
    assert resp.status_code == 200
    assert resp.json()["llm_summary"] == narrative


@pytest.mark.parametrize("lang", LANGS_ALL)
def test_compare_summary_translates_the_ai_narrative(client, monkeypatch, lang):
    """The AI Analysis. Model-authored, so it legitimately costs one runtime
    call -- but it must not come back English when a language was asked for."""
    narrative = ("Amount Outstanding — Domestic increased from Rs 4,855 Cr to "
                 "Rs 506,108 Cr for CIMS_ROR on 30-Jun-2026.")

    async def _generate(*args, **kwargs):
        return narrative

    monkeypatch.setattr("backend.tools.variance_explain.generate_explanations",
                        _generate, raising=False)
    tr = StubTranslator()
    _install(monkeypatch, translator=tr)

    body = {"rows": [{"concept": "AmountOutstanding", "val_a": 1.0, "val_b": 2.0}],
            "label_a": "30-Jun-2026", "label_b": "30-Sep-2025",
            "report_name": "RAQ(Monthly)"}
    if lang != "en":
        body["lang"] = lang
    resp = client.post("/compare-summary", json=body)
    assert resp.status_code == 200
    summary = resp.json()["llm_summary"]

    if lang == "en":
        assert summary == narrative, "English must be byte-identical"
        assert tr.calls == [], "English must make no model call"
    else:
        assert summary != narrative, f"{lang}: the AI narrative came back English"
        assert tr.calls, "a model-authored narrative must be translated"
        # Figures, identifiers and dates are masked out and restored.
        for token in ("CIMS_ROR", "506,108", "30-Jun-2026"):
            assert token in summary, f"{lang}: lost {token!r}"
            assert token not in "\n".join(c[0] for c in tr.calls), (
                f"{lang}: {token!r} was sent to the model"
            )


@pytest.mark.parametrize("lang", LANGS_ALL)
def test_explain_category_honours_lang(client, monkeypatch, lang):
    async def _explain(*args, **kwargs):
        return {
            "intent": "get_status", "report_name": "CIMS_ROR",
            "response_text": "Render file not found.",
            "result_type": "error", "options": [],
        }

    monkeypatch.setattr("backend.main.explain_category_for_report", _explain)
    _install(monkeypatch, translator=StubTranslator())

    body = {"error_file_path": "f.xml", "category": "formula_error"}
    if lang != "en":
        body["lang"] = lang
    resp = client.post("/explain-category", json=body)
    assert resp.status_code == 200
    data = resp.json()
    if lang == "en":
        assert data["response_text"] == "Render file not found."
    else:
        assert data["response_text"] != "Render file not found.", (
            f"{lang}: the message came back English"
        )
