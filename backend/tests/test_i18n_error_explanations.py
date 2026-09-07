"""Multilingual error explanations and LLM-generated summaries.

Two kinds of content live in an error card, and they are handled differently:

  DETERMINISTIC  section headings ("Where", "Rule", "How to fix"), item labels
                 ("Concept", "Period") and the fixed sentences the renderers
                 emit. Resolved from the pre-translated catalogue -- ZERO model
                 calls.

  LLM-AUTHORED   the explanation body written per error by the model
                 (formula_error.py / dimension_error.py / report_lookup.py).
                 Generated in English exactly as before, then translated ONCE
                 at runtime.

Nothing in the generation path changes: these tests assert that the English the
pipeline produced is the English that gets translated, and that the caller's own
object is never mutated.
"""
from __future__ import annotations

import asyncio
import copy

import pytest

from backend.i18n import boundary, catalogue
from backend.i18n.translator import TranslationResult

TARGETS = ("fr", "ar", "hi")

# Values that must survive byte-for-byte through translation.
PROTECTED = [
    "CIMS_ROR", "R009", "R149", "TotalOfAverageCashReserves",
    "8,972,828,000", "30-Jun-2026", "2026-12-12T17:00:00",
    "4f2a1c9e8b7d4a5f9c0e1b2d3a4f5e6c",
]


@pytest.fixture(autouse=True)
def _enabled(monkeypatch):
    monkeypatch.setenv("MULTILINGUAL_ENABLED", "true")
    monkeypatch.setenv("SUPPORTED_LANGUAGES", "en,fr,ar,hi")
    monkeypatch.setenv("TRANSLATION_MAX_CHARS", "4000")


class Spy:
    name = "spy"

    def __init__(self):
        self.seen: list[str] = []

    async def translate(self, text, src, tgt):
        self.seen.append(text)
        return TranslationResult(text=f"<{tgt}>{text}", latency_ms=1.0, ok=True)

    @property
    def sent(self) -> str:
        return "\n".join(self.seen)


class Boom:
    name = "boom"

    async def translate(self, text, src, tgt):  # pragma: no cover
        raise AssertionError(f"model called for: {text!r}")


# The shape formula_error.py:3313-3319 and dimension_error.py:1430-1438 build.
def _response():
    return {
        "intent": "get_status",
        "response_text": "Schedule confirmed:",
        "options": [],
        # xbrl_comparator -- genuinely model-authored
        "llm_summary": "Doubtful Assets increased significantly compared with "
                       "the previous period, driven by TotalOfAverageCashReserves.",
        "error_details": [
            {
                # Raw validator output and XBRL identifiers -- DATA.
                "rule_name": "R009",
                "concept": "TotalOfAverageCashReserves",
                "message": "assertion R009 unsatisfied",
                "business_rule": "sum(a,b) = c",
                # Fully deterministic: every line is catalogued.
                "explanation": "Where\nRule\n"
                               "The reported value does not match the calculated value.",
                "explanation_sections": [
                    {
                        "kind": "locator",
                        "heading": "Where",
                        "items": [
                            {"label": "Concept", "value": "TotalOfAverageCashReserves"},
                            {"label": "Period", "value": "30-Jun-2026"},
                        ],
                    },
                    {
                        "kind": "fix",
                        "heading": "How to fix",
                        # LLM-authored body
                        "text": "Re-check the source ledger for CIMS_ROR and "
                                "resubmit; the reported figure of 8,972,828,000 "
                                "does not reconcile.",
                    },
                ],
            }
        ],
    }


def _out(lang, translator, result=None):
    return asyncio.run(boundary.translate_outbound(
        result if result is not None else _response(), lang, translator))


# ---------------------------------------------------------------------------
# 1. English and disabled are untouched
# ---------------------------------------------------------------------------

def test_english_returns_the_identical_object():
    original = _response()
    assert asyncio.run(boundary.translate_outbound(original, "en", Boom())) is original


def test_disabled_returns_the_identical_object(monkeypatch):
    monkeypatch.setenv("MULTILINGUAL_ENABLED", "false")
    original = _response()
    assert asyncio.run(boundary.translate_outbound(original, "fr", Boom())) is original


def test_the_callers_object_is_never_mutated():
    """The agent still holds this dict. Translating in place would make a later
    English render come back localized."""
    original = _response()
    snapshot = copy.deepcopy(original)
    _out("fr", Spy(), original)
    assert original == snapshot


# ---------------------------------------------------------------------------
# 2. Deterministic content -> catalogue, zero model calls
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("english,key", [
    ("Where", "errcard.where"),
    ("Rule", "errcard.rule"),
    ("How to fix", "errcard.howToFix"),
    ("What is wrong", "errcard.whatIsWrong"),
    ("Values", "errcard.values"),
    ("Details", "errcard.details"),
    ("Expected", "errcard.expected"),
    ("Actual", "errcard.actual"),
    ("Concept", "errcard.item.concept"),
    ("Period", "errcard.item.period"),
    ("The reported value does not match the calculated value.", "errcard.mismatch"),
])
@pytest.mark.parametrize("lang", TARGETS)
def test_deterministic_error_text_resolves_from_the_catalogue(english, key, lang):
    out = catalogue.resolve(english, lang)
    assert out is not None, f"{english!r} is not catalogued"
    assert out == catalogue.load(lang)[key]
    # A few terms are spelled the same in the target language ("Concept" in
    # French). That is a correct translation, not a missing one, so identity
    # is only a failure where the languages genuinely differ.
    if catalogue.load(lang)[key] != catalogue.load("en")[key]:
        assert out != english


@pytest.mark.parametrize("lang", TARGETS)
def test_a_fully_deterministic_card_costs_no_model_call(lang):
    """An explanation whose every line is catalogued must not reach the model."""
    result = _response()
    # Strip the LLM-authored section so only deterministic content remains.
    result["error_details"][0]["explanation_sections"] = [
        result["error_details"][0]["explanation_sections"][0]
    ]
    del result["llm_summary"]
    out = _out(lang, Boom(), result)
    detail = out["error_details"][0]
    assert detail["explanation"] != _response()["error_details"][0]["explanation"]
    assert detail["explanation_sections"][0]["heading"] != "Where"


@pytest.mark.parametrize("lang", TARGETS)
def test_deterministic_template_keeps_its_value(lang):
    """'Difference: {0}' -- the template translates, the amount does not."""
    english = "Difference: 8,972,828,000"
    out = catalogue.resolve(english, lang)
    assert out is not None and "8,972,828,000" in out
    assert out != english


# ---------------------------------------------------------------------------
# 3. LLM-authored content -> exactly one runtime translation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("lang", TARGETS)
def test_llm_explanation_is_translated_at_runtime(lang):
    spy = Spy()
    out = _out(lang, spy)
    body = out["error_details"][0]["explanation_sections"][1]["text"]
    assert body.startswith(f"<{lang}>"), "the LLM body was not translated"
    assert spy.seen, "the model must be used for model-authored prose"


@pytest.mark.parametrize("lang", TARGETS)
def test_llm_summary_is_translated_at_runtime(lang):
    spy = Spy()
    out = _out(lang, spy)
    assert out["llm_summary"].startswith(f"<{lang}>")


@pytest.mark.parametrize("lang", TARGETS)
def test_nothing_is_translated_twice(lang):
    """Catalogue output must not then be handed to the model, and no string
    may be sent more than once."""
    spy = Spy()
    out = _out(lang, spy)
    assert len(spy.seen) == len(set(spy.seen)), f"duplicate calls: {spy.seen}"
    localized_heading = out["error_details"][0]["explanation_sections"][0]["heading"]
    assert localized_heading not in spy.sent, "a catalogue result reached the model"
    for text in spy.seen:
        assert not text.startswith(f"<{lang}>"), "already-translated text re-sent"


@pytest.mark.parametrize("lang", TARGETS)
def test_call_count_matches_the_dynamic_content(lang):
    """Two model-authored strings here (llm_summary + the fix body), so two
    calls -- the deterministic headings and labels cost nothing."""
    spy = Spy()
    out = _out(lang, spy)
    meta = out["data"]["i18n"]["outbound"]
    assert meta["calls"] == 2, f"{meta['calls']} calls, expected 2: {spy.seen}"
    # 5, not 6: error_details[].explanation is the same card flattened into one
    # string, so it is rebuilt from the localized sections rather than sent --
    # see _derive_explanations(). It costs no call and cannot disagree with the
    # sections above it.
    assert meta["nested_fields"] == 5
    assert meta["derived"] == 1


# ---------------------------------------------------------------------------
# 4. Protected entities and data
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("lang", TARGETS)
def test_protected_entities_never_reach_the_model(lang):
    spy = Spy()
    _out(lang, spy)
    for token in ("CIMS_ROR", "TotalOfAverageCashReserves", "8,972,828,000",
                  "30-Jun-2026"):
        assert token not in spy.sent, f"{token!r} was sent to the model"


@pytest.mark.parametrize("lang", TARGETS)
def test_protected_entities_come_back_verbatim(lang):
    out = _out(lang, Spy())
    blob = str(out)
    for token in ("CIMS_ROR", "TotalOfAverageCashReserves", "8,972,828,000",
                  "30-Jun-2026", "R009"):
        assert token in blob, f"{token!r} lost from the {lang} response"


@pytest.mark.parametrize("lang", TARGETS)
def test_item_values_are_data_and_stay_unchanged(lang):
    """items[].label is prose; items[].value is the concept/figure."""
    out = _out(lang, Spy())
    items = out["error_details"][0]["explanation_sections"][0]["items"]
    assert items[0]["value"] == "TotalOfAverageCashReserves"
    assert items[1]["value"] == "30-Jun-2026"
    # "Concept" is spelled the same in French; assert it came from the
    # catalogue rather than assuming every word must look different.
    assert items[0]["label"] == catalogue.resolve("Concept", lang)
    assert items[1]["label"] == catalogue.resolve("Period", lang)


@pytest.mark.parametrize("lang", TARGETS)
def test_raw_validator_fields_are_untouched(lang):
    """message / business_rule / rule_name / concept are validator output and
    XBRL identifiers, not authored prose."""
    out = _out(lang, Spy())
    detail = out["error_details"][0]
    assert detail["message"] == "assertion R009 unsatisfied"
    assert detail["business_rule"] == "sum(a,b) = c"
    assert detail["rule_name"] == "R009"
    assert detail["concept"] == "TotalOfAverageCashReserves"


@pytest.mark.parametrize("lang", TARGETS)
def test_a_hostile_translator_cannot_corrupt_the_figures(lang):
    class Hostile:
        name = "hostile"

        async def translate(self, text, src, tgt):
            mangled = (text.replace("CIMS", "SIMC").replace("2026", "٢٠٢٦")
                       .replace("8,972,828,000", "0").upper())
            return TranslationResult(text=mangled, latency_ms=1.0, ok=True)

    out = _out(lang, Hostile())
    blob = str(out)
    for token in ("CIMS_ROR", "8,972,828,000", "30-Jun-2026"):
        assert token in blob, f"hostile model corrupted {token!r}"


# ---------------------------------------------------------------------------
# 5. No accidental English
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("lang", TARGETS)
def test_no_deterministic_english_remains(lang):
    """Checked by exact catalogue comparison, not substring matching -- English
    words occur legitimately inside identifiers and inside French."""
    out = _out(lang, Spy())
    sections = out["error_details"][0]["explanation_sections"]
    for section, english in zip(sections, ("Where", "How to fix")):
        assert section["heading"] == catalogue.resolve(english, lang)
    labels = sections[0]["items"]
    for item, english in zip(labels, ("Concept", "Period")):
        assert item["label"] == catalogue.resolve(english, lang)


@pytest.mark.parametrize("lang", TARGETS)
def test_every_prose_string_changed_language(lang):
    """Nothing user-visible may come back byte-identical to its English."""
    english = _response()
    out = _out(lang, Spy())
    same = []
    if out["llm_summary"] == english["llm_summary"]:
        same.append("llm_summary")
    detail, edetail = out["error_details"][0], english["error_details"][0]
    if detail["explanation"] == edetail["explanation"]:
        same.append("explanation")
    for i, (sec, esec) in enumerate(
            zip(detail["explanation_sections"], edetail["explanation_sections"])):
        # Compare against the catalogue, not against "did the bytes change" --
        # a term can be identical in both languages and still be correct.
        if sec.get("heading") != catalogue.resolve(esec.get("heading"), lang):
            same.append(f"sections.{i}.heading")
        if sec.get("text") and sec.get("text") == esec.get("text"):
            same.append(f"sections.{i}.text")
    assert not same, f"{lang} left these in English: {same}"


# ---------------------------------------------------------------------------
# 6. Scope: db_beautified is NOT part of this task
# ---------------------------------------------------------------------------

def test_db_beautified_behaviour_is_unchanged():
    """This task must not add or alter db_beautified handling. It was already
    in TRANSLATABLE_FIELDS before this change and stays exactly as it was."""
    assert "db_beautified" in boundary.TRANSLATABLE_FIELDS
    assert boundary.TRANSLATABLE_FIELDS == (
        "response_text", "llm_summary", "db_summary", "db_beautified",
        "status_note", "accuracy_hint", "more_info_hint", "download_label",
    )


def test_nested_extraction_covers_only_the_intended_paths():
    result = _response()
    keys = set(boundary._nested_payload(result)[0])
    # explanation is deliberately ABSENT: it duplicates the sections and is
    # derived from them afterwards instead of costing a second translation.
    assert keys == {
        "error_details.0.explanation_sections.0.heading",
        "error_details.0.explanation_sections.0.items.0.label",
        "error_details.0.explanation_sections.0.items.1.label",
        "error_details.0.explanation_sections.1.heading",
        "error_details.0.explanation_sections.1.text",
    }


def test_malformed_error_details_do_not_raise():
    for details in ([None], ["a string"], [{}], [{"explanation_sections": "x"}],
                    [{"explanation_sections": [{"items": "x"}]}]):
        out = _out("fr", Spy(), {"response_text": "Schedule confirmed:",
                                 "options": [], "error_details": details})
        assert "error_details" in out


def test_explanation_blob_is_derived_from_the_localized_sections():
    """The flattened card must end up localized WITHOUT its own model call, and
    must agree word-for-word with the sections it was rebuilt from."""
    spy = Spy()
    result = _response()
    english_sections = [
        s.get("heading") for s in result["error_details"][0]["explanation_sections"]
    ]
    english_blob = result["error_details"][0]["explanation"]
    out = _out("fr", spy, result)
    blob = out["error_details"][0]["explanation"]
    localized = out["error_details"][0]["explanation_sections"]
    checked = 0
    for n, heading in enumerate(english_sections):
        # Only headings the flattened card actually carries: the blob is a
        # rendering of the card, not a concatenation of every section.
        if not heading or heading not in english_blob:
            continue
        checked += 1
        assert heading not in blob, f"{heading!r} left English in the blob"
        assert localized[n]["heading"] in blob, "blob must reuse the section wording"
    assert checked, "fixture must exercise at least one heading"
    assert out["data"]["i18n"]["outbound"]["derived"] == 1


def test_deriving_the_blob_costs_no_extra_model_call():
    spy = Spy()
    out = _out("fr", spy, _response())
    sent = chr(10).join(spy.seen)
    blob = _response()["error_details"][0]["explanation"]
    assert blob not in sent, "the flattened card must never be sent to the model"
    assert out["data"]["i18n"]["outbound"]["calls"] == 2
