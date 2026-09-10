"""backend/i18n/boundary.py -- error_details[] batched translation.

Every prose fragment inside every error card used to be dispatched as its own
translation call, bounded only by the global TRANSLATION_CONCURRENCY
semaphore -- a report with several errors could fan out into dozens of small
calls. translate_outbound now groups whole error_details[] objects into
batches of ERROR_EXPLANATION_TRANSLATION_BATCH_SIZE (default 3) and sends
each batch's prose as ONE combined translation call.

These tests verify: batch counts for 1/3/4/6/7 objects, ordering preserved
across batch boundaries, and that a broken batch (lost separator, or an
outright translator failure) degrades gracefully -- the whole batch keeps its
English text -- without disturbing other batches.
"""
from __future__ import annotations

import asyncio

import pytest

from backend.i18n import boundary
from backend.i18n.translator import TranslationResult


@pytest.fixture(autouse=True)
def _enabled(monkeypatch):
    monkeypatch.setenv("MULTILINGUAL_ENABLED", "true")
    monkeypatch.setenv("SUPPORTED_LANGUAGES", "en,fr,ar,hi")
    monkeypatch.setenv("TRANSLATION_MAX_CHARS", "20000")
    monkeypatch.setenv("ERROR_EXPLANATION_TRANSLATION_BATCH_SIZE", "3")


class BatchSpy:
    """Records each combined batch payload and echoes it back with each
    non-blank LINE prefixed by the target language -- a batch joins several
    fields with "\\n", so a translator (real or fake) that honors "preserve
    line breaks exactly" (translator.py's _SYSTEM prompt) translates each
    field's line independently, which is what this simulates. A single
    whole-blob prefix would be unrealistic: it would only mark the FIRST
    field in a batch as translated, not the others."""

    name = "batch-spy"

    def __init__(self):
        self.calls: list[str] = []

    async def translate(self, text, src, tgt):
        self.calls.append(text)
        lines = [f"<{tgt}>{line}" if line.strip() else line for line in text.split("\n")]
        return TranslationResult(text="\n".join(lines), latency_ms=1.0, ok=True)


def _error(n: int) -> dict:
    """One error_details[] entry with a single LLM-authored fix sentence,
    unique per index -- everything else on the card (heading, rule_name,
    concept, message) is catalogued or raw data, so exactly one nested field
    per object needs a model call. That keeps the expected batch/call counts
    exact and easy to assert.
    """
    return {
        "rule_name": f"R{n:03d}",
        "concept": f"Concept{n}",
        "message": f"assertion R{n:03d} unsatisfied",
        "explanation_sections": [
            {
                "kind": "fix",
                "heading": "How to fix",
                "text": f"Re-check source data for rule {n} and resubmit.",
            },
        ],
    }


def _response(count: int) -> dict:
    return {
        "response_text": "Schedule confirmed:",
        "options": [],
        "error_details": [_error(i) for i in range(count)],
    }


def _out(lang, translator, count):
    return asyncio.run(boundary.translate_outbound(_response(count), lang, translator))


# ---------------------------------------------------------------------------
# Batch counts: 1 -> 1, 3 -> 1, 4 -> 3+1, 6 -> 3+3, 7 -> 3+3+1
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("count,expected_batches", [
    (1, 1), (3, 1), (4, 2), (6, 2), (7, 3),
])
def test_batch_count_matches_object_count(count, expected_batches):
    spy = BatchSpy()
    out = _out("fr", spy, count)
    assert len(spy.calls) == expected_batches, spy.calls
    meta = out["data"]["i18n"]["outbound"]
    assert meta["calls"] == expected_batches


@pytest.mark.parametrize("count", [4, 7])
def test_no_batch_exceeds_the_configured_size(count):
    """Every dispatched batch call must carry at most
    ERROR_EXPLANATION_TRANSLATION_BATCH_SIZE objects' worth of fields -- here
    that is exactly one field per object, so at most 3 per call."""
    spy = BatchSpy()
    _out("fr", spy, count)
    for call_text in spy.calls:
        rule_mentions = sum(1 for i in range(count) if f"rule {i}" in call_text)
        assert rule_mentions <= 3, f"batch carried {rule_mentions} objects: {call_text!r}"


# ---------------------------------------------------------------------------
# Ordering and completeness across batch boundaries
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("lang", ["fr", "hi", "ar"])
def test_ordering_is_preserved_across_batches(lang):
    """7 objects -> batches of 3, 3, 1. The response must still list every
    rule in its original order regardless of how batching grouped them."""
    spy = BatchSpy()
    out = _out(lang, spy, 7)
    rule_names = [d["rule_name"] for d in out["error_details"]]
    assert rule_names == [f"R{i:03d}" for i in range(7)]


@pytest.mark.parametrize("lang", ["fr", "hi", "ar"])
def test_every_object_is_translated(lang):
    spy = BatchSpy()
    out = _out(lang, spy, 7)
    for i, detail in enumerate(out["error_details"]):
        text = detail["explanation_sections"][0]["text"]
        assert text.startswith(f"<{lang}>"), f"object {i} was not translated: {text!r}"
        assert f"rule {i}" in text


@pytest.mark.parametrize("lang", ["fr", "hi", "ar"])
def test_hindi_and_arabic_are_exercised_not_just_french(lang):
    """The user-reported failure was language-specific (Hindi failed while
    French partly worked) -- never assume a French pass means every language
    passes."""
    spy = BatchSpy()
    out = _out(lang, spy, 3)
    assert len(spy.calls) == 1
    for detail in out["error_details"]:
        assert detail["explanation_sections"][0]["text"].startswith(f"<{lang}>")


# ---------------------------------------------------------------------------
# Graceful degradation: a broken batch never corrupts or drops content
# ---------------------------------------------------------------------------

def test_a_batch_that_loses_the_separator_falls_back_to_english_for_that_batch():
    """If the model drops every [[E#]] placeholder (separators included) in
    one batch, that whole batch must keep its English text -- never a
    misaligned split -- while other batches are unaffected."""

    class SeparatorEater:
        name = "separator-eater"

        def __init__(self):
            self.n = 0

        async def translate(self, text, src, tgt):
            self.n += 1
            if self.n == 1:
                mangled = text.replace("[[", "").replace("]]", "")
                return TranslationResult(text=f"<{tgt}>{mangled}", latency_ms=1.0, ok=True)
            return TranslationResult(text=f"<{tgt}>{text}", latency_ms=1.0, ok=True)

    out = _out("fr", SeparatorEater(), 4)  # batches: [0,1,2] then [3]
    details = out["error_details"]
    for i in range(3):
        text = details[i]["explanation_sections"][0]["text"]
        assert text == f"Re-check source data for rule {i} and resubmit.", (
            "a broken batch must keep English, not a corrupted split"
        )
    assert details[3]["explanation_sections"][0]["text"].startswith("<fr>")
    meta = out["data"]["i18n"]["outbound"]
    assert meta["ok"] is False


def test_a_translator_failure_keeps_the_whole_batch_english():
    class Boom:
        name = "boom"

        async def translate(self, text, src, tgt):
            return TranslationResult(text="", latency_ms=1.0, ok=False, error="ReadTimeout")

    out = _out("hi", Boom(), 3)
    for i, detail in enumerate(out["error_details"]):
        text = detail["explanation_sections"][0]["text"]
        assert text == f"Re-check source data for rule {i} and resubmit."
    meta = out["data"]["i18n"]["outbound"]
    assert meta["ok"] is False
    assert meta["fields"] == []


def test_no_batch_field_is_ever_dropped_even_on_failure():
    """Every object must still be present in the response -- a failure may
    leave text English, but it must never vanish."""
    class Boom:
        name = "boom"

        async def translate(self, text, src, tgt):
            return TranslationResult(text="", latency_ms=1.0, ok=False, error="ReadTimeout")

    out = _out("hi", Boom(), 7)
    assert len(out["error_details"]) == 7
    for i, detail in enumerate(out["error_details"]):
        assert detail["explanation_sections"][0]["text"] == (
            f"Re-check source data for rule {i} and resubmit."
        )


# ---------------------------------------------------------------------------
# Configurability
# ---------------------------------------------------------------------------

def test_batch_size_is_configurable(monkeypatch):
    monkeypatch.setenv("ERROR_EXPLANATION_TRANSLATION_BATCH_SIZE", "2")
    spy = BatchSpy()
    out = _out("fr", spy, 5)  # batches of 2,2,1 -> 3 calls
    assert len(spy.calls) == 3
    meta = out["data"]["i18n"]["outbound"]
    assert meta["calls"] == 3
