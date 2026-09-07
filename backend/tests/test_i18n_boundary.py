"""Unit tests for the multilingual translation boundary.

No network. Every test drives a stub translator, which is itself the point:
TRANSLATION_MODEL is the only model seam, so nothing else in the package can
reach out on its own.

The repo has no pytest-asyncio, so coroutines are driven with asyncio.run(),
matching the existing convention in backend/tests/test_batch_bug_fixes.py:171.
"""
from __future__ import annotations

import asyncio

import pytest

from backend.i18n import boundary, catalogue, config
from backend.i18n.translator import IdentityTranslator, TranslationResult

REGULATORY_IDS = [
    "DBR01", "CIMS_ROR", "CIMS_RAQ(Monthly)",
    "RAQ(Quarterly)", "RAQ(Monthly)", "RAQ(Annually)",
]


@pytest.fixture(autouse=True)
def _enabled(monkeypatch):
    """Default every test to the feature being ON, so a test that wants it OFF
    has to say so explicitly."""
    monkeypatch.setenv("MULTILINGUAL_ENABLED", "true")
    monkeypatch.setenv("TRANSLATION_MODEL", "qwen3:14b")
    monkeypatch.setenv("SUPPORTED_LANGUAGES", "en,fr,ar,hi")
    monkeypatch.setenv("TRANSLATION_MAX_CHARS", "2000")


class StubTranslator:
    """Records everything handed to the model and returns a scripted result."""

    name = "stub"

    def __init__(self, transform=None, ok=True, error=None, text=None):
        self.calls: list[tuple[str, str, str]] = []
        self._transform = transform or (lambda t: f"<{t}>")
        self._ok = ok
        self._error = error
        self._text = text

    async def translate(self, text, src, tgt):
        self.calls.append((text, src, tgt))
        if not self._ok:
            # Mirrors OllamaTranslator's contract: the ORIGINAL text is
            # returned on failure, and callers must consult .ok.
            return TranslationResult(
                text=text, latency_ms=1.0, ok=False, error=self._error, model="stub"
            )
        out = self._text if self._text is not None else self._transform(text)
        return TranslationResult(text=out, latency_ms=1.0, ok=True, model="stub")

    @property
    def sent(self) -> str:
        return "\n".join(c[0] for c in self.calls)


def _st03_like(options):
    """The exact shape backend/agent/__init__.py:3316-3320 produces."""
    opts_text = "\n".join(f"{i + 1}. {n}" for i, n in enumerate(options))
    return (
        f"I found {len(options)} matching reports. Which one are you looking for?\n\n"
        f"{opts_text}\n\n"
        "Reply with the number or part of the name."
    )


def _big_options(n=162):
    return [f"CIMS_REPORT_{i:03d}_LONG_REGULATORY_NAME" for i in range(1, n + 1)]


# ---------------------------------------------------------------------------
# A. Disabled / English -- existing behaviour must be untouched
# ---------------------------------------------------------------------------

def test_disabled_makes_inbound_a_no_op(monkeypatch):
    monkeypatch.setenv("MULTILINGUAL_ENABLED", "false")
    stub = StubTranslator()
    res = asyncio.run(boundary.translate_inbound("bonjour", "fr", stub))
    assert res.ok and res.text == "bonjour" and not res.translated
    assert stub.calls == [], "no model call may happen when disabled"


def test_disabled_returns_the_identical_response_object(monkeypatch):
    monkeypatch.setenv("MULTILINGUAL_ENABLED", "false")
    result = {"response_text": "Report DBR01 is complete.", "options": ["DBR01"]}
    out = asyncio.run(boundary.translate_outbound(result, "fr", StubTranslator()))
    assert out is result, "disabled must return the SAME object, not a copy"
    assert "data" not in out, "no metadata key may be added when disabled"


@pytest.mark.parametrize("lang", [None, "", "en", "en-GB", "EN"])
def test_english_is_a_no_op(lang):
    stub = StubTranslator()
    result = {"response_text": "Report DBR01 is complete."}
    assert asyncio.run(boundary.translate_outbound(result, lang, stub)) is result
    inb = asyncio.run(boundary.translate_inbound("status of DBR01", lang, stub))
    assert inb.ok and inb.text == "status of DBR01"
    assert stub.calls == []


def test_english_response_is_byte_for_byte_unchanged():
    """The strongest form of the guarantee: every key and value identical."""
    result = {
        "intent": "get_status", "report_name": "DBR01",
        "response_text": "Report 'DBR01' completed on 31-03-2025.",
        "result_type": "final", "options": [], "db_sql": "SELECT 1",
    }
    before = dict(result)
    out = asyncio.run(boundary.translate_outbound(result, "en", StubTranslator()))
    assert out == before


# ---------------------------------------------------------------------------
# B. Language normalisation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("fr", "fr"), ("FR", "fr"), ("fr-CA", "fr"), ("fr_CA", "fr"),
    ("ar", "ar"), ("hi", "hi"), ("en", "en"),
    (None, "en"), ("", "en"), ("  ", "en"),
    ("de", "en"), ("zz", "en"), ("klingon", "en"),
])
def test_normalize_lang(raw, expected):
    assert boundary.normalize_lang(raw) == expected


def test_unsupported_language_degrades_to_english_and_never_raises():
    """A serviceable request must not be refused just because we cannot
    localize it."""
    stub = StubTranslator()
    res = asyncio.run(boundary.translate_inbound("status of DBR01", "de", stub))
    assert res.ok and res.text == "status of DBR01"
    assert stub.calls == []


def test_rtl_flag():
    assert boundary.is_rtl("ar") is True
    assert boundary.is_rtl("fr") is False and boundary.is_rtl("hi") is False


# ---------------------------------------------------------------------------
# C. Inbound translation, FR / AR / HI
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("lang,text", [
    ("fr", "quel est le statut de DBR01"),
    ("ar", "ما هي حالة DBR01"),
    ("hi", "DBR01 की स्थिति क्या है"),
])
def test_inbound_translates_and_targets_english(lang, text):
    stub = StubTranslator(transform=lambda t: "what is the status of DBR01")
    res = asyncio.run(boundary.translate_inbound(text, lang, stub))
    assert res.ok and res.translated
    assert res.text == "what is the status of DBR01"
    assert res.lang == lang
    assert stub.calls == [(text, lang, "en")], "must translate INTO English"


def test_inbound_makes_exactly_one_model_call():
    stub = StubTranslator()
    asyncio.run(boundary.translate_inbound("quel est le statut", "fr", stub))
    assert len(stub.calls) == 1


# ---------------------------------------------------------------------------
# D. Inbound skip rules -- messages that must never reach the model
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("message,reason", [
    ("2", "no-letters"),            # disambiguation reply, agent/__init__.py:1103
    ("1", "no-letters"),
    ("162", "no-letters"),
    ("31-03-2025", "no-letters"),   # date prompt
    ("3.5", "no-letters"),
    ("__GUIDED_START__", "guided-sentinel"),
    ("CIMS_ROR", "identifier"),
    ("DBR01", "identifier"),
    ("CIMS_RAQ(Monthly)", "identifier"),
    ("RAQ(Quarterly)", "identifier"),
    ("R149", "identifier"),
    ("", "empty"),
    ("   ", "empty"),
])
def test_inbound_skips(message, reason):
    stub = StubTranslator()
    res = asyncio.run(boundary.translate_inbound(message, "fr", stub))
    assert res.ok and res.skip_reason == reason
    assert res.text == message, "a skipped message must pass through verbatim"
    assert stub.calls == [], f"{message!r} must never reach the model"


def test_numeric_reply_survives_int_parsing_after_the_boundary():
    """agent/__init__.py:1103 does int(raw_input). A model that rendered '2' as
    an Arabic-Indic '٢' would break selection, so '2' must never be sent."""
    res = asyncio.run(boundary.translate_inbound("2", "ar", StubTranslator(text="٢")))
    assert int(res.text) == 2


@pytest.mark.parametrize("message", [
    "bonjour", "RAQ", "merci", "quel est le statut de mon rapport",
    "ما هو دوري", "नमस्ते",
])
def test_ordinary_prose_is_not_skipped(message):
    """The skip rules must stay narrow. 'bonjour' being skipped is exactly the
    under-translation bug the Step 3 prompt change fixed."""
    stub = StubTranslator()
    res = asyncio.run(boundary.translate_inbound(message, "fr", stub))
    assert res.skip_reason is None and res.translated
    assert len(stub.calls) == 1


def test_guided_action_labels_are_skipped():
    """guided.py:179-180 matches these as English literals."""
    from backend.guided import GUIDED_ACTIONS
    for label in GUIDED_ACTIONS:
        stub = StubTranslator()
        res = asyncio.run(boundary.translate_inbound(label, "fr", stub))
        assert res.skip_reason == "guided-action"
        assert res.text == label and stub.calls == []


# ---------------------------------------------------------------------------
# E. Inbound failure -- FATAL, must never route
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("error", [
    "ReadTimeout: timed out",
    "HTTPStatusError: 502",
    "ConnectError: connection refused",
    "empty translation after cleaning",
])
def test_inbound_failure_is_not_ok(error):
    stub = StubTranslator(ok=False, error=error)
    res = asyncio.run(boundary.translate_inbound("quel est le statut", "fr", stub))
    assert res.ok is False, "caller MUST NOT be allowed to route on this"
    assert res.error == error


def test_inbound_failure_response_is_localized_and_shaped_like_an_error():
    for lang in ("fr", "ar", "hi"):
        resp = boundary.inbound_failure_response(lang, "ReadTimeout")
        assert resp["result_type"] == "error"
        assert resp["response_text"] and resp["response_text"].strip()
        assert resp["response_text"] != boundary._INBOUND_FAILURE_TEXT["en"]
        assert resp["options"] == []
        assert resp["data"]["i18n"]["lang"] == lang
        assert resp["data"]["i18n"]["inbound"]["ok"] is False


def test_inbound_failure_text_is_static_not_model_generated():
    """An error path that needs the model to report a model failure is not an
    error path."""
    assert set(boundary._INBOUND_FAILURE_TEXT) >= {"en", "fr", "ar", "hi"}
    assert all(v.strip() for v in boundary._INBOUND_FAILURE_TEXT.values())


# ---------------------------------------------------------------------------
# F. Outbound translation
# ---------------------------------------------------------------------------

def test_outbound_translates_prose_fields_only():
    result = {
        "response_text": "Report is complete.",
        "llm_summary": "Values rose.",
        "db_summary": "Two rows.",
        "intent": "get_status",
        "report_name": "DBR01",
        "db_sql": "SELECT * FROM t",
        "options": [],
        "db_columns": ["A"], "db_rows": [[1]],
        "variance_label_a": "Q1", "download_url": "/download-file?x=1",
    }
    stub = StubTranslator()
    out = asyncio.run(boundary.translate_outbound(result, "fr", stub))

    assert out["response_text"] == "<Report is complete.>"
    assert out["llm_summary"] == "<Values rose.>"
    assert out["db_summary"] == "<Two rows.>"
    # Untouched -- this is the primary entity-protection mechanism.
    for key in ("intent", "report_name", "db_sql", "db_columns", "db_rows",
                "variance_label_a", "download_url"):
        assert out[key] == result[key], f"{key} must not be translated"


def test_outbound_targets_the_user_language():
    stub = StubTranslator()
    asyncio.run(boundary.translate_outbound({"response_text": "hi"}, "ar", stub))
    assert stub.calls[0][1:] == ("en", "ar")


def test_outbound_fields_are_translated_concurrently():
    """Independent fields must not serialize -- wall clock is the slowest call,
    not the sum. A response with two prose fields costs one call's latency."""
    order: list[str] = []

    class Slow:
        name = "slow"

        async def translate(self, text, src, tgt):
            order.append(f"start:{text}")
            await asyncio.sleep(0.02)
            order.append(f"end:{text}")
            return TranslationResult(text=f"<{text}>", latency_ms=20.0, ok=True)

    asyncio.run(boundary.translate_outbound(
        {"response_text": "a", "llm_summary": "b"}, "fr", Slow()
    ))
    # Both start before either finishes => concurrent, not sequential.
    assert order[:2] == ["start:a", "start:b"]


def test_outbound_failure_keeps_english_and_never_blanks():
    stub = StubTranslator(ok=False, error="HTTPStatusError: 502")
    result = {"response_text": "Report DBR01 completed on 31-03-2025."}
    out = asyncio.run(boundary.translate_outbound(result, "fr", stub))
    assert out["response_text"] == "Report DBR01 completed on 31-03-2025."
    assert out["status_note"], "user should be told why it is in English"
    assert out["data"]["i18n"]["outbound"]["ok"] is False


def test_outbound_empty_translation_keeps_english():
    """An empty result means the model emitted only a thinking trace."""
    stub = StubTranslator(text="   ")
    out = asyncio.run(boundary.translate_outbound({"response_text": "Done."}, "fr", stub))
    assert out["response_text"] == "Done."


def test_outbound_partial_failure_localizes_what_it_can():
    class Flaky:
        name = "flaky"

        async def translate(self, text, src, tgt):
            if text == "Values rose.":
                return TranslationResult(text=text, latency_ms=1.0, ok=False, error="502")
            return TranslationResult(text=f"<{text}>", latency_ms=1.0, ok=True)

    out = asyncio.run(boundary.translate_outbound(
        {"response_text": "Done.", "llm_summary": "Values rose."}, "fr", Flaky()
    ))
    assert out["response_text"] == "<Done.>"
    assert out["llm_summary"] == "Values rose."
    assert out["data"]["i18n"]["outbound"]["errors"] == {"llm_summary": "502"}


def test_outbound_skips_oversized_payloads(monkeypatch):
    """A field larger than the budget is not sent, and keeps its English."""
    monkeypatch.setenv("TRANSLATION_MAX_CHARS", "50")
    stub = StubTranslator()
    out = asyncio.run(boundary.translate_outbound({"response_text": "x" * 500}, "fr", stub))
    assert out["response_text"] == "x" * 500
    assert stub.calls == []
    assert out["data"]["i18n"]["outbound"]["deferred"] == ["response_text"]


def test_oversized_field_does_not_take_the_rest_of_the_response_with_it(monkeypatch):
    """THE REGRESSION: the budget is per field, not per response.

    A 3-error formula card is ~12,000 characters, so a whole-payload check
    returned the entire response in English -- headings, column labels and
    templated sentences the catalogue already had translations for. One
    oversized field must cost only itself.
    """
    monkeypatch.setenv("TRANSLATION_MAX_CHARS", "50")
    out = asyncio.run(boundary.translate_outbound(
        {"response_text": "Done.", "llm_summary": "x" * 500}, "fr", StubTranslator(),
    ))
    meta = out["data"]["i18n"]["outbound"]
    assert meta["deferred"] == ["llm_summary"]
    assert out["llm_summary"] == "x" * 500          # untouched
    assert out["response_text"] != "Done."          # still localized


def test_catalogue_runs_before_the_budget(monkeypatch):
    """A catalogue hit costs no call and no characters, so no budget applies.

    Gating it on the model budget is what made every error card come back
    English.
    """
    monkeypatch.setenv("TRANSLATION_MAX_CHARS", "1")
    english = catalogue.load("en")["errcard.calculation"]
    stub = StubTranslator()
    out = asyncio.run(boundary.translate_outbound(
        {"response_text": english}, "fr", stub,
    ))
    assert stub.calls == []
    assert out["response_text"] == catalogue.load("fr")["errcard.calculation"]
    assert out["data"]["i18n"]["outbound"]["catalogued"] == ["response_text"]


def test_pure_arithmetic_is_never_sent_to_the_model():
    """A calculation bullet is amounts and operators -- no words at all."""
    bullet = "(₹356,802,987,000 × 0.06 + ₹2,297,563,000 × 0.05) ÷ (₹356,802,987,000) = 0.0599"
    stub = StubTranslator()
    out = asyncio.run(boundary.translate_outbound({"response_text": bullet}, "fr", stub))
    assert stub.calls == []
    assert out["response_text"] == bullet, "figures must stay byte-identical"


def test_prose_containing_many_figures_is_still_translated():
    """The counterpart: figures do not make a sentence into data."""
    stub = StubTranslator()
    text = "Rounded to 0.0001: 0.0599 expected, 0.06 reported."
    asyncio.run(boundary.translate_outbound({"response_text": text}, "fr", stub))
    assert stub.calls, "a sentence with words in it must still be translated"


def test_translation_calls_are_bounded(monkeypatch):
    """Fan-out is capped: the proxy shares one model, and the timeout runs per
    call from dispatch, so queued calls otherwise burn their own budget."""
    monkeypatch.setenv("TRANSLATION_CONCURRENCY", "2")
    live = 0
    peak = 0

    class Counting:
        name = "counting"

        async def translate(self, text, src, tgt):
            nonlocal live, peak
            live += 1
            peak = max(peak, live)
            await asyncio.sleep(0.01)
            live -= 1
            return TranslationResult(text=f"<{text}>", latency_ms=10.0, ok=True)

    fields = {name: f"prose {n}" for n, name in enumerate(boundary.TRANSLATABLE_FIELDS)}
    asyncio.run(boundary.translate_outbound(fields, "fr", Counting()))
    assert peak <= 2, f"at most 2 calls in flight, saw {peak}"


def test_outbound_does_not_mutate_the_input():
    result = {"response_text": "Done.", "options": []}
    asyncio.run(boundary.translate_outbound(result, "fr", StubTranslator()))
    assert result["response_text"] == "Done.", "pipeline result must not be mutated"


# ---------------------------------------------------------------------------
# G. Structured options and entity preservation
# ---------------------------------------------------------------------------

def test_large_162_option_list_never_reaches_the_model():
    """The measured failure: 3,446 chars, HTTP 502 on 8/8 large cases."""
    options = _big_options(162)
    text = _st03_like(options)
    assert len(text) > 3294
    stub = StubTranslator()
    out = asyncio.run(boundary.translate_outbound(
        {"response_text": text, "options": options}, "fr", stub
    ))
    for name in options:
        assert name not in stub.sent, f"{name} was sent to the model"
    assert len(stub.sent) < 200, f"still sending {len(stub.sent)} chars"
    meta = out["data"]["i18n"]["outbound"]
    assert meta["options_count"] == 162
    assert meta["options_masked"] == ["response_text"]
    assert meta["chars_total"] > 3294 and meta["chars_sent"] < 200


def test_all_162_options_return_byte_identical_and_in_order():
    options = _big_options(162)
    out = asyncio.run(boundary.translate_outbound(
        {"response_text": _st03_like(options), "options": options}, "fr", StubTranslator()
    ))
    text = out["response_text"]
    for i, name in enumerate(options, 1):
        assert f"{i}. {name}" in text
    positions = [text.index(f"{i}. {n}") for i, n in enumerate(options, 1)]
    assert positions == sorted(positions), "option order changed"
    assert out["options"] == options, "options[] itself must never be translated"


@pytest.mark.parametrize("identifier", REGULATORY_IDS)
def test_regulatory_identifiers_never_reach_the_model(identifier):
    stub = StubTranslator()
    asyncio.run(boundary.translate_outbound(
        {"response_text": _st03_like(REGULATORY_IDS), "options": REGULATORY_IDS}, "fr", stub
    ))
    assert identifier not in stub.sent


def test_identifiers_survive_a_hostile_translator():
    """Identifiers are re-inserted from options[], so even a model that mangles
    everything it is given cannot corrupt one."""
    hostile = StubTranslator(
        transform=lambda t: t.replace("RAQ", "DEMANDE").replace("reports", "rapports")
        + " [MANGLED]"
    )
    out = asyncio.run(boundary.translate_outbound(
        {"response_text": _st03_like(REGULATORY_IDS), "options": REGULATORY_IDS},
        "ar", hostile,
    ))
    for identifier in REGULATORY_IDS:
        assert identifier in out["response_text"]


def test_options_only_field_makes_no_model_call():
    """agent/__init__.py:1244 sets response_text=opts_text with no prose."""
    from backend.i18n import payload as pl
    options = ["ROR", "CIMS_ROR"]
    text = pl.render_options_block(options)
    stub = StubTranslator()
    out = asyncio.run(boundary.translate_outbound(
        {"response_text": text, "options": options}, "fr", stub
    ))
    assert stub.calls == [], "a bare option list must not be translated"
    assert out["response_text"] == text


def test_placeholder_masking_and_restoration_round_trip():
    from backend.i18n import payload as pl
    options = _big_options(20)
    text = _st03_like(options)
    masked, block = pl.mask_options(text, options)
    assert pl.OPTIONS_PLACEHOLDER in masked
    assert pl.restore_options(masked, block) == text


def test_block_is_appended_when_the_model_drops_the_placeholder():
    """A response missing its options is unusable; one with the list slightly
    misplaced is still correct and selectable."""
    options = ["RAQ(Monthly)", "RAQ(Annually)"]
    stub = StubTranslator(text="Le modele a tout supprime.")
    out = asyncio.run(boundary.translate_outbound(
        {"response_text": _st03_like(options), "options": options}, "fr", stub
    ))
    assert "RAQ(Monthly)" in out["response_text"]
    assert "RAQ(Annually)" in out["response_text"]


def test_no_masking_when_the_rendered_list_is_absent():
    """Never a silent partial mask: if the block is not present verbatim the
    text is translated whole."""
    from backend.i18n import payload as pl
    text = "Your role is 'Admin User' (id 101)."
    to_translate, blocks, passthrough = pl.split_payload({"response_text": text}, ["RAQ"])
    assert to_translate["response_text"] == text
    assert blocks == {} and passthrough == {}


# ---------------------------------------------------------------------------
# H. Conversation history / i18n metadata
# ---------------------------------------------------------------------------

def test_english_source_is_echoed_for_history_replay():
    """This is what keeps decide() on English context without seven extra
    translation calls per turn."""
    result = {"response_text": "Report DBR01 is complete.", "llm_summary": "Rose 5%."}
    out = asyncio.run(boundary.translate_outbound(
        result, "fr", StubTranslator(), english_message="status of DBR01"
    ))
    english = out["data"]["i18n"]["english"]
    assert english["response_text"] == "Report DBR01 is complete."
    assert english["llm_summary"] == "Rose 5%."
    assert english["user_message"] == "status of DBR01"
    assert out["response_text"] != english["response_text"], "localized differs"


def test_metadata_goes_under_the_existing_data_field():
    """ChatResponse keeps its exact current shape: no field added, none
    renamed."""
    from backend.models import ChatResponse
    before = set(ChatResponse.model_fields)
    out = asyncio.run(boundary.translate_outbound(
        {"response_text": "Done.", "data": {"status_code": 7}}, "fr", StubTranslator()
    ))
    assert set(ChatResponse.model_fields) == before
    assert out["data"]["status_code"] == 7, "existing data keys preserved"
    assert out["data"]["i18n"]["lang"] == "fr"


def test_metadata_records_the_configured_model(monkeypatch):
    monkeypatch.setenv("TRANSLATION_MODEL", "gemma4:31b")
    out = asyncio.run(boundary.translate_outbound(
        {"response_text": "Done."}, "fr", StubTranslator()
    ))
    assert out["data"]["i18n"]["model"] == "gemma4:31b"


def test_rtl_is_reported_to_the_frontend():
    out = asyncio.run(boundary.translate_outbound(
        {"response_text": "Done."}, "ar", StubTranslator()
    ))
    assert out["data"]["i18n"]["rtl"] is True


# ---------------------------------------------------------------------------
# I. Cancellation / Stop Generation
# ---------------------------------------------------------------------------

def test_inbound_cancellation_propagates():
    """Stop Generation cancels the asyncio.Task; the boundary must not swallow
    CancelledError, or /stop would stop working during a translation."""

    class Hanging:
        name = "hang"

        async def translate(self, text, src, tgt):
            await asyncio.sleep(10)
            return TranslationResult(text=text, latency_ms=0.0)

    async def _run():
        task = asyncio.ensure_future(
            boundary.translate_inbound("quel est le statut", "fr", Hanging())
        )
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(_run())


def test_outbound_cancellation_propagates_through_gather():
    class Hanging:
        name = "hang"

        async def translate(self, text, src, tgt):
            await asyncio.sleep(10)
            return TranslationResult(text=text, latency_ms=0.0)

    async def _run():
        task = asyncio.ensure_future(boundary.translate_outbound(
            {"response_text": "a", "llm_summary": "b"}, "fr", Hanging()
        ))
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# J. Configuration -- the model must be the only difference between runs
# ---------------------------------------------------------------------------

def test_translation_model_is_the_only_model_seam(monkeypatch):
    from backend.i18n.translator import OllamaTranslator
    for name in ("qwen3:14b", "gemma4:31b"):
        monkeypatch.setenv("TRANSLATION_MODEL", name)
        assert config.translation_model() == name
        assert OllamaTranslator().model == name
        assert OllamaTranslator()._payload("x", "en", "fr", False)["model"] == name


def test_model_is_never_hardcoded_outside_config():
    """A stray model literal would silently break the A/B comparison.

    Checks executable string constants only. Comments and docstrings legitimately
    name models when explaining WHY something is the way it is (the qwen3:14b
    under-translation that motivated the prompt fix, for instance), and banning
    that would only push the explanation out of the code.
    """
    import ast
    import pathlib

    banned = ("qwen3:14b", "gemma4:31b", "qwen2.5", "llama3.1", "phi3:mini")
    pkg = pathlib.Path(config.__file__).parent
    for path in pkg.glob("*.py"):
        if path.name == "config.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        docstrings = {
            node.body[0].value
            for node in ast.walk(tree)
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
            and node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        }
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            if node in docstrings:
                continue
            for literal in banned:
                assert literal not in node.value, (
                    f"{path.name}:{node.lineno} hardcodes model {literal!r}"
                )


def test_prompt_is_identical_to_the_evaluated_one():
    """The 24-case FR/AR/HI measurements were taken with this exact prompt.
    Changing it invalidates the Qwen-vs-Gemma comparison."""
    from backend.i18n.translator import _SYSTEM
    assert "The input is ALWAYS in {src_name}" in _SYSTEM
    assert "Never return the input unchanged" in _SYSTEM
    assert "CIMS_RAQ(Monthly)" in _SYSTEM
    assert "31-03-2025 stays 31-03-2025" in _SYSTEM
    # The Step 3 regression: this clause caused 'bonjour' to be echoed.
    assert "return it unchanged." not in _SYSTEM.replace(
        "Never return the input unchanged", ""
    )


def test_timeout_is_not_the_300s_ollama_timeout(monkeypatch):
    monkeypatch.delenv("TRANSLATION_TIMEOUT", raising=False)
    monkeypatch.setenv("OLLAMA_TIMEOUT", "300")
    assert config.translation_timeout() == 60.0


def test_num_predict_is_unbounded_by_default(monkeypatch):
    """llm_service pins 256 and truncates silently."""
    monkeypatch.delenv("TRANSLATION_NUM_PREDICT", raising=False)
    assert config.translation_num_predict() == -1


def test_base_url_inherits_ollama_base_url(monkeypatch):
    monkeypatch.delenv("TRANSLATION_BASE_URL", raising=False)
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://3.109.51.228/OllamaProxy/")
    assert config.translation_base_url() == "http://3.109.51.228/OllamaProxy"


def test_identity_translator_proves_no_hidden_network():
    res = asyncio.run(IdentityTranslator().translate("x", "en", "fr"))
    assert res.ok and res.text == "x"


# ---------------------------------------------------------------------------
# K. Response cleaning -- thinking models
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("<think>reasoning here</think>Bonjour", "Bonjour"),
    ("<thinking>a\nb</thinking>\n\nBonjour", "Bonjour"),
    ("```\nBonjour\n```", "Bonjour"),
    ("```text\nBonjour\n```", "Bonjour"),
    ("Translation: Bonjour", "Bonjour"),
    ("Here is the translation: Bonjour", "Bonjour"),
    ("Bonjour", "Bonjour"),
])
def test_clean_strips_wrappers(raw, expected):
    from backend.i18n.translator import _clean
    assert _clean(raw)[0] == expected


def test_unterminated_thinking_yields_empty_not_a_trace():
    """gemma4:31b advertises the thinking capability. An unterminated <think>
    means no translation was produced -- returning the trace would show the
    model's reasoning to a banking user."""
    from backend.i18n.translator import _clean
    text, had = _clean("<think>I should translate this")
    assert text == "" and had is True
