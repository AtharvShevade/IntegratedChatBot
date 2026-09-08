"""Status-card translation must use the existing catalogue, not the LLM.

Background: backend/i18n/messages/{fr,ar,hi}.json already carry hand
translations for every status label the app shows ("statusvalue.*"), and the
catalogue's line-by-line resolver (backend/i18n/catalogue.py::resolve) already
picks these up generically -- a "Label : value" line has its label resolved
from the catalogue and, if the value itself is not pure data, the value is
ALSO looked up in the catalogue (catalogue.py::_resolve_line). So a status
card is only as good as its weakest label.

Investigation for this task found FOUR call sites in backend/agent/__init__.py
that render a "Status : <map_status() label>" line (1076, 2798, 2864, 2994).
Three of them (2798, 2864, 2994) already resolved with ZERO model calls,
because every label they use ("Reporting Date", "Latest Reporting Date",
"Initiated On", "Status") was already catalogued. The fourth (1076, the
"pick which run" status display) used a label -- "Run Date/Time" -- that had
no catalogue entry, so the WHOLE card (all-or-nothing per resolve()) fell
through to the runtime translator every time, even though its status value
was one of the same fixed enum. The fix is a single new catalogue entry
("label.run_date_time") in all four message files -- not a new status
translation table. report_lookup._STATUS_LABELS / map_status() remains the
one and only source of truth for what a status CODE means in English; this
module only adds the missing LABEL that was blocking catalogue resolution of
the surrounding line.

A fifth call site (3586, instance-generation success) uses a free-form
message from the .NET generate API, not a map_status() enum value, and is
intentionally left alone -- it is not a static status choice.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.i18n import boundary, catalogue
from backend.i18n.translator import TranslationResult
from backend.tools.report_lookup import map_status, _STATUS_LABELS

TARGETS = ("fr", "ar", "hi")


@pytest.fixture(autouse=True)
def _enabled(monkeypatch):
    monkeypatch.setenv("MULTILINGUAL_ENABLED", "true")
    monkeypatch.setenv("SUPPORTED_LANGUAGES", "en,fr,ar,hi")
    monkeypatch.setenv("TRANSLATION_MAX_CHARS", "2000")


class Boom:
    """Fails the test if the translation model is called at all."""

    name = "boom"

    async def translate(self, text, src, tgt):  # pragma: no cover - must not run
        raise AssertionError(f"translation model called for: {text!r}")


class Spy:
    name = "spy"

    def __init__(self):
        self.seen: list[str] = []

    async def translate(self, text, src, tgt):
        self.seen.append(text)
        return TranslationResult(text=f"<{tgt}>{text}", latency_ms=1.0, ok=True)


def _outbound(text, lang, translator, report_name="CIMS_ROR"):
    return asyncio.run(boundary.translate_outbound(
        {"response_text": text, "report_name": report_name, "options": [],
         "result_type": "final"},
        lang, translator,
    ))


# Every status label real InstanceLog codes actually resolve to (the single
# source of truth -- see backend/tools/report_lookup.py::_STATUS_LABELS).
REAL_STATUS_VALUES = sorted(set(_STATUS_LABELS.values()) | {"Unknown"})

# The four call sites in backend/agent/__init__.py that render a status
# enum inside a "Label : value" card (line numbers as found during
# investigation; kept here only as documentation, not imported).
CARD_TEMPLATES = {
    "run_selected (agent/__init__.py:1076)": (
        "{name}\n"
        "Reporting Date : {date}\n"
        "Run Date/Time  : {dtc}\n"
        "Status         : {status}"
    ),
    "latest_with_ask (agent/__init__.py:2798)": (
        "{name}\n"
        "Latest Reporting Date : {date}\n"
        "Status                : {status}"
    ),
    "final (agent/__init__.py:2864)": (
        "{name}\n"
        "Reporting Date : {date}\n"
        "Initiated On   : {dtc}\n"
        "Status         : {status}"
    ),
    "ask_another_date (agent/__init__.py:2994)": (
        "{name}\n"
        "Reporting Date : {date}\n"
        "Initiated On   : {dtc}\n"
        "Status         : {status}"
    ),
}


# ---------------------------------------------------------------------------
# 1. A known status resolves through map_status() -> catalogue, zero model
#    calls, for every one of the four real card shapes.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("card_name,template", sorted(CARD_TEMPLATES.items()))
@pytest.mark.parametrize("lang", TARGETS)
def test_known_status_card_needs_zero_model_calls(card_name, template, lang):
    text = template.format(
        name="CIMS_ROR", date="30-Sep-2020", dtc="07-Oct-2025 06:55:05 PM",
        status=map_status(11),  # "Approval Pending"
    )
    out = _outbound(text, lang, Boom())
    meta = out["data"]["i18n"]["outbound"]
    assert meta["calls"] == 0, f"{card_name}/{lang} still called the model"


@pytest.mark.parametrize("lang", TARGETS)
def test_approval_pending_resolves_to_the_existing_translation(lang):
    """The literal scenario reported by the user: 'Approval Pending' must
    resolve to backend/i18n/messages/{lang}.json's own statusvalue.approval_pending,
    never a fresh model translation."""
    expected = catalogue.load(lang)["statusvalue.approval_pending"]
    assert catalogue.resolve("Approval Pending", lang) == expected


# ---------------------------------------------------------------------------
# 2. Every status map_status() can actually return resolves in fr/ar/hi.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("status", REAL_STATUS_VALUES)
@pytest.mark.parametrize("lang", TARGETS)
def test_every_real_status_value_resolves(status, lang):
    out = catalogue.resolve(status, lang)
    assert out is not None, f"{status!r} has no catalogue translation for {lang}"
    assert out.strip()


@pytest.mark.parametrize("code,expected_label", sorted(_STATUS_LABELS.items()))
def test_map_status_is_the_single_source_of_truth(code, expected_label):
    """This module must never keep its own status vocabulary -- every status
    string it tests comes from map_status(), not a local literal list."""
    assert map_status(code) == expected_label


# ---------------------------------------------------------------------------
# 3. Arabic and Hindi specifically (not just "some non-English language").
# ---------------------------------------------------------------------------

def test_arabic_approval_pending():
    assert catalogue.resolve("Approval Pending", "ar") == catalogue.load("ar")["statusvalue.approval_pending"]


def test_hindi_approval_pending():
    assert catalogue.resolve("Approval Pending", "hi") == catalogue.load("hi")["statusvalue.approval_pending"]


# ---------------------------------------------------------------------------
# 4. Unknown / unexpected status values must not crash -- they simply fall
#    through to the runtime translator like any other unrecognised text.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("lang", TARGETS)
def test_unrecognised_status_value_does_not_crash(lang):
    weird = "Some Brand New Status Nobody Catalogued Yet"
    assert catalogue.resolve(weird, lang) is None  # no crash, just "not found"

    spy = Spy()
    text = f"CIMS_ROR\nStatus         : {weird}"
    out = _outbound(text, lang, spy)
    assert spy.seen, "an uncatalogued status must still be handled -- via the model, not a crash"
    assert weird in out["response_text"] or out["response_text"].startswith(f"<{lang}>")


def test_map_status_itself_never_crashes_on_an_unknown_code():
    assert map_status(999999) == "Unknown"


# ---------------------------------------------------------------------------
# 5. Dynamic values (report name, dates, request IDs) are never translated or
#    altered, regardless of which status accompanies them.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("lang", TARGETS)
def test_dynamic_values_survive_alongside_a_known_status(lang):
    text = (
        "CIMS_ROR\n"
        "Reporting Date : 30-Sep-2020\n"
        "Initiated On   : 07-Oct-2025 06:55:05 PM\n"
        "Status         : Approval Pending"
    )
    out = _outbound(text, lang, Boom())
    for dynamic in ("CIMS_ROR", "30-Sep-2020", "07-Oct-2025", "06:55:05"):
        assert dynamic in out["response_text"], f"{lang} lost dynamic value {dynamic!r}"


@pytest.mark.parametrize("lang", TARGETS)
def test_request_id_label_and_value_stay_untranslated(lang):
    """'Request ID' is a protected domain term (backend/i18n/protect.py
    _GLOSSARY) -- it must never be translated, unlike an ordinary label."""
    text = "CIMS_ROR\nRequest ID     : abc123def456"
    out = _outbound(text, lang, Boom())
    assert "Request ID" in out["response_text"]
    assert "abc123def456" in out["response_text"]


# ---------------------------------------------------------------------------
# 6. Fixed regression: the specific gap found during investigation
#    ("Run Date/Time" had no catalogue entry) is closed.
# ---------------------------------------------------------------------------

def test_run_date_time_label_is_catalogued_in_every_language():
    for lang in ("en",) + TARGETS:
        assert catalogue.load(lang).get("label.run_date_time"), (
            f"label.run_date_time missing from {lang}.json"
        )
