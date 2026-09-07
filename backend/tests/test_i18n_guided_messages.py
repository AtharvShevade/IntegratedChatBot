"""Guided-mode dynamic messages in English / French / Arabic / Hindi.

The reported gap: with French selected the static UI localized but guided-mode
chatbot messages stayed English, e.g.

    "Enter the report name, ReturnId, or short name (e.g. CIMS_FormGPB, R009):"
    "Please enter the reporting date for **CIMS_ROR**."
    "Generating instance for 'CIMS_ROR'\\nReporting Date : 31-Mar-2026"

These are DYNAMIC prose (built at runtime from repository data), so they belong
to the runtime translator, not the static dictionary. They already travelled in
`response_text` -- a translatable field -- so the plumbing was right; what was
missing was any STRUCTURAL guarantee that the identifiers, dates and numbers
embedded in them survived the model unchanged.

Every fixture below is the real string from the real call site, cited.
"""
from __future__ import annotations

import asyncio

import pytest

from backend.i18n import boundary, protect
from backend.i18n.translator import TranslationResult

# The exact prose the pipeline emits, with its source.
GUIDED_MESSAGES = {
    # guided.py:363 / :372 / :381 / :390
    "report_name_prompt":
        "Enter the report name, ReturnId, or short name (e.g. CIMS_FormGPB, R009):",
    "compare_name_prompt":
        "Enter the report name, ReturnId, or short name to compare "
        "(e.g. CIMS_RAQ, R009, RAQ):",
    # guided.py:117
    "menu_prompt": "What would you like to do? Select an action to get started:",
    # agent/__init__.py:4048-4057  (_date_ask_prompt, frequency == "Q")
    "date_prompt_quarterly": (
        "Please enter the reporting date for **CIMS_ROR**.\n"
        "\n"
        "Quarterly reports must use:\n"
        "• 31-Mar\n• 30-Jun\n• 30-Sep\n• 31-Dec\n"
        "\n"
        "Example: 31-Mar-2026"
    ),
    # agent/__init__.py:4000-4007  (_finalize_generation, success)
    "generation_success": (
        "Generating instance for 'CIMS_ROR'\n"
        "Reporting Date : 31-Mar-2026\n"
        "Status         : Report added successfully for XBRL generation.\n"
        "Request ID     : 4f2a1c9e8b7d4a5f9c0e1b2d3a4f5e6c"
    ),
    # agent/__init__.py:4014-4019  (_finalize_generation, failure)
    "generation_failure": (
        "Instance generation failed: service unavailable\n"
        "Please check the XBRL generation service on the server."
    ),
    # agent/__init__.py:3335
    "date_selection": "Select a reporting date for 'CIMS_RAQ(Monthly)':",
}

# Must come back byte-identical, per message.
PROTECTED = {
    "report_name_prompt": ["CIMS_FormGPB", "R009", "ReturnId"],
    "compare_name_prompt": ["CIMS_RAQ", "R009", "RAQ", "ReturnId"],
    "menu_prompt": [],
    "date_prompt_quarterly": ["**CIMS_ROR**", "31-Mar", "30-Jun", "30-Sep",
                              "31-Dec", "31-Mar-2026"],
    "generation_success": ["CIMS_ROR", "31-Mar-2026", "XBRL",
                           "4f2a1c9e8b7d4a5f9c0e1b2d3a4f5e6c", "Request ID"],
    "generation_failure": ["XBRL"],
    "date_selection": ["CIMS_RAQ(Monthly)"],
}

LANGS = ("fr", "ar", "hi")


@pytest.fixture(autouse=True)
def _enabled(monkeypatch):
    monkeypatch.setenv("MULTILINGUAL_ENABLED", "true")
    monkeypatch.setenv("TRANSLATION_MODEL", "qwen3:14b")
    monkeypatch.setenv("SUPPORTED_LANGUAGES", "en,fr,ar,hi")
    monkeypatch.setenv("TRANSLATION_MAX_CHARS", "2000")


class Recorder:
    """Translates by tagging the prose, so the test can tell translated text
    apart from untranslated -- and records exactly what the model saw."""

    name = "recorder"

    def __init__(self, transform=None):
        self.seen: list[str] = []
        self._transform = transform

    async def translate(self, text, src, tgt):
        self.seen.append(text)
        out = self._transform(text) if self._transform else f"<{tgt}>{text}"
        return TranslationResult(text=out, latency_ms=1.0, ok=True, model="recorder")

    @property
    def sent(self) -> str:
        return "\n".join(self.seen)


def _outbound(text, lang, translator, **kw):
    return asyncio.run(boundary.translate_outbound(
        {"response_text": text, "options": [], "result_type": "final"},
        lang, translator, **kw,
    ))


# ---------------------------------------------------------------------------
# A. The messages are translated at all -- the reported bug
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("key", sorted(GUIDED_MESSAGES))
@pytest.mark.parametrize("lang", LANGS)
def test_guided_message_is_translated(key, lang):
    """Localized by EITHER mechanism -- the pre-translated catalogue (no model
    call) or the runtime translator. Which one is asserted separately below;
    what matters here is that the user never sees the English."""
    rec = Recorder()
    out = _outbound(GUIDED_MESSAGES[key], lang, rec)
    meta = out["data"]["i18n"]["outbound"]
    assert out["response_text"] != GUIDED_MESSAGES[key], (
        f"{key} came back identical to English in {lang}"
    )
    assert "response_text" in (meta["catalogued"] + meta["fields"])


# Legitimately NOT catalogue-resolvable: agent/__init__.py:4016 interpolates
# api_result["message"], which is free text returned by the .NET generation
# service. The surrounding sentences are catalogued, but resolution is
# all-or-nothing per field -- a half-French line is worse than one model call --
# so this message correctly falls through to the runtime translator.
NEEDS_MODEL = {"generation_failure"}


@pytest.mark.parametrize("key", sorted(set(GUIDED_MESSAGES) - NEEDS_MODEL))
@pytest.mark.parametrize("lang", LANGS)
def test_deterministic_messages_cost_no_model_call(key, lang):
    """Every message here is a deterministic pipeline template, so all of them
    should now resolve from the catalogue. A miss is not a failure of
    correctness -- it falls through to the model -- but it IS a regression in
    cost, so it is asserted."""
    rec = Recorder()
    out = _outbound(GUIDED_MESSAGES[key], lang, rec)
    meta = out["data"]["i18n"]["outbound"]
    assert meta["calls"] == 0, (
        f"{key}/{lang} fell through to the model ({meta['calls']} calls) - "
        f"its catalogue entry is missing or has drifted"
    )
    assert rec.seen == []


@pytest.mark.parametrize("key", sorted(NEEDS_MODEL))
@pytest.mark.parametrize("lang", LANGS)
def test_free_form_content_still_reaches_the_model(key, lang):
    """The fallback must stay live: a message carrying text the pipeline did
    not author is translated at runtime, not guessed at from the catalogue."""
    rec = Recorder()
    out = _outbound(GUIDED_MESSAGES[key], lang, rec)
    assert out["data"]["i18n"]["outbound"]["calls"] == 1
    assert rec.seen, "free-form text must reach the runtime translator"


@pytest.mark.parametrize("key", sorted(GUIDED_MESSAGES))
def test_english_leaves_guided_messages_untouched(key):
    rec = Recorder()
    original = {"response_text": GUIDED_MESSAGES[key], "options": []}
    assert asyncio.run(boundary.translate_outbound(original, "en", rec)) is original
    assert rec.seen == []


# ---------------------------------------------------------------------------
# B. Protected entities survive byte-for-byte
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("key", sorted(GUIDED_MESSAGES))
@pytest.mark.parametrize("lang", LANGS)
def test_protected_entities_never_reach_the_model(key, lang):
    rec = Recorder()
    _outbound(GUIDED_MESSAGES[key], lang, rec)
    for entity in PROTECTED[key]:
        assert entity not in rec.sent, (
            f"{key}: {entity!r} was sent to the translation model in {lang}"
        )


@pytest.mark.parametrize("key", sorted(GUIDED_MESSAGES))
@pytest.mark.parametrize("lang", LANGS)
def test_protected_entities_come_back_verbatim(key, lang):
    out = _outbound(GUIDED_MESSAGES[key], lang, Recorder())["response_text"]
    for entity in PROTECTED[key]:
        assert entity in out, f"{key}: {entity!r} lost from the {lang} reply"


@pytest.mark.parametrize("lang", LANGS)
def test_identifiers_survive_a_hostile_translator(lang):
    """The guarantee is structural, not a request: even a model that mangles
    everything it is handed cannot corrupt an entity, because entities are
    re-inserted from the original bytes."""
    hostile = Recorder(transform=lambda t: (
        t.replace("CIMS", "SIMC").replace("Mar", "Mars")
         .replace("2026", "٢٠٢٦").replace("R009", "R٠٠٩").upper()
    ))
    for key, text in GUIDED_MESSAGES.items():
        out = _outbound(text, lang, hostile)["response_text"]
        for entity in PROTECTED[key]:
            assert entity in out, f"{key}: hostile model corrupted {entity!r}"


@pytest.mark.parametrize("lang", LANGS)
def test_dates_keep_their_exact_format(lang):
    """31-Mar-2026 is parsed back by the .NET generation API. A localized
    '31-mars-2026' or Arabic-Indic digits would break generation outright."""
    out = _outbound(GUIDED_MESSAGES["generation_success"], lang, Recorder())
    assert "31-Mar-2026" in out["response_text"]
    for bad in ("31-mars-2026", "٣١", "31 Mar 2026", "2026-03-31"):
        assert bad not in out["response_text"]


@pytest.mark.parametrize("lang", LANGS)
def test_markdown_and_bullets_are_preserved(lang):
    out = _outbound(GUIDED_MESSAGES["date_prompt_quarterly"], lang, Recorder())
    text = out["response_text"]
    assert "**CIMS_ROR**" in text, "markdown bold lost"
    assert text.count("•") == 4, "bullet characters lost"
    assert text.count("\n") >= 6, "line structure lost"


def test_a_lost_entity_falls_back_to_english():
    """If the model drops a placeholder the entity would vanish from the
    sentence. Showing English is the lesser failure.

    Uses free-form text on purpose: a catalogued message never reaches the
    model, so it could not exercise this path."""
    class Dropper:
        name = "dropper"

        async def translate(self, text, src, tgt):
            return TranslationResult(text="Le rapport a bien fonctionne.",
                                     latency_ms=1.0, ok=True)

    free_form = ("The NPA ratio for CIMS_ROR moved from 3.2% to 4.1% between "
                 "31-Mar-2026 and 30-Jun-2026, driven by the retail book.")
    out = _outbound(free_form, "fr", Dropper())
    assert out["response_text"] == free_form
    assert out["data"]["i18n"]["outbound"]["entities_lost"] > 0
    assert out["status_note"], "user is told the reply stayed English"


# ---------------------------------------------------------------------------
# C. Masking mechanics
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("Please enter the reporting date for **CIMS_ROR**.", ["**CIMS_ROR**"]),
    ("Example: 31-Mar-2026", ["31-Mar-2026"]),
    ("• 31-Mar", ["31-Mar"]),
    ("Reporting Date : 31-03-2025", ["31-03-2025"]),
    ("Scheduled for 14:30", ["14:30"]),
    ("e.g. CIMS_FormGPB, R009", ["CIMS_FormGPB", "R009"]),
    ("'CIMS_RAQ(Monthly)'", ["CIMS_RAQ(Monthly)"]),
    ("for XBRL generation", ["XBRL"]),
    ("the ReturnId or short name", ["ReturnId"]),
    ("I found 5 matching reports", ["5"]),
])
def test_mask_catches_the_right_tokens(text, expected):
    _, tokens = protect.mask_entities(text)
    assert sorted(tokens.values()) == sorted(expected)


@pytest.mark.parametrize("text", [
    "Please enter the reporting date.",
    "What would you like to do next?",
    "Sorry, you do not have access to this action.",
])
def test_plain_prose_is_not_over_masked(text):
    """Over-masking would hand the model a sentence of placeholders and
    produce unnatural output."""
    _, tokens = protect.mask_entities(text)
    assert tokens == {}, f"over-masked: {tokens}"


def test_repeated_entity_shares_one_placeholder():
    masked, tokens = protect.mask_entities("CIMS_ROR then CIMS_ROR again")
    assert len(tokens) == 1
    assert masked.count("[[E1]]") == 2


def test_round_trip_is_byte_identical():
    for text in GUIDED_MESSAGES.values():
        masked, tokens = protect.mask_entities(text)
        restored, missing = protect.restore_entities(masked, tokens)
        assert restored == text and missing == []


def test_placeholder_variants_are_tolerated():
    masked, tokens = protect.mask_entities("date for **CIMS_ROR**.")
    for variant in ("[[E1]]", "[ E1 ]", "[E1]", "[[e1]]"):
        restored, missing = protect.restore_entities(f"date pour {variant}.", tokens)
        assert "**CIMS_ROR**" in restored and missing == []


def test_missing_placeholder_is_reported():
    _, tokens = protect.mask_entities("date for **CIMS_ROR** on 31-Mar-2026")
    _, missing = protect.restore_entities("date pour [[E1]]", tokens)
    assert missing == ["[[E2]]"]


# ---------------------------------------------------------------------------
# D. No duplicate translation calls
# ---------------------------------------------------------------------------

def test_identical_fields_are_translated_once():
    """db_qa_router.py:762-763 puts the same string in response_text and
    db_beautified; that was costing two identical calls."""
    rec = Recorder()
    same = "There are 3 active users in the Compliance department."
    out = asyncio.run(boundary.translate_outbound(
        {"response_text": same, "db_beautified": same, "db_summary": same,
         "options": []}, "fr", rec,
    ))
    assert len(rec.seen) == 1, f"{len(rec.seen)} calls for one string"
    assert out["data"]["i18n"]["outbound"]["calls"] == 1
    assert out["response_text"] == out["db_beautified"] == out["db_summary"]


def test_distinct_fields_still_get_their_own_call():
    rec = Recorder()
    asyncio.run(boundary.translate_outbound(
        {"response_text": "Done.", "llm_summary": "Values rose.", "options": []},
        "fr", rec,
    ))
    assert len(rec.seen) == 2


# ---------------------------------------------------------------------------
# E. Nothing else moved
# ---------------------------------------------------------------------------

def test_guided_action_tokens_are_not_touched_by_the_translator():
    """The protocol tokens travel in options[], which is never translated."""
    from backend.guided import GUIDED_ACTIONS
    rec = Recorder()
    out = asyncio.run(boundary.translate_outbound(
        {"response_text": "What would you like to do? Select an action to get started:",
         "options": list(GUIDED_ACTIONS), "result_type": "guided_menu"},
        "fr", rec,
    ))
    assert out["options"] == list(GUIDED_ACTIONS)
    for action in GUIDED_ACTIONS:
        assert action not in rec.sent


def test_translatable_fields_are_unchanged():
    """Guided prose rides in response_text; no new field was added for it."""
    assert boundary.TRANSLATABLE_FIELDS == (
        "response_text", "llm_summary", "db_summary", "db_beautified",
        "status_note", "accuracy_hint", "more_info_hint", "download_label",
    )
