"""The pre-translated message catalogue and its resolver.

The catalogue turns ~72% of the chatbot's output from a 20-second model call
into a dictionary lookup. That is only safe if three things hold, and each has
tests here:

  1. COVERAGE  -- every catalogue entry has all four languages, with matching
     slot counts, so a localized template can never drop a report name.

  2. FIDELITY  -- the English side still matches what the pipeline actually
     emits. If someone edits a string in agent/__init__.py the entry silently
     stops matching and quietly costs a model call again; the drift test below
     fails instead.

  3. SAFETY    -- resolution is exact, never loose. Two different messages must
     never resolve to each other's wording, and anything unrecognised must fall
     through to the runtime translator rather than being guessed at.
"""
from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

import pytest

from backend.i18n import boundary, catalogue
from backend.i18n.translator import TranslationResult

LANGS = ("en", "fr", "ar", "hi")
TARGETS = ("fr", "ar", "hi")
MESSAGES_DIR = Path(catalogue.__file__).resolve().parent / "messages"


@pytest.fixture(autouse=True)
def _enabled(monkeypatch):
    monkeypatch.setenv("MULTILINGUAL_ENABLED", "true")
    monkeypatch.setenv("SUPPORTED_LANGUAGES", "en,fr,ar,hi")
    monkeypatch.setenv("TRANSLATION_MAX_CHARS", "2000")


def _ids() -> list[str]:
    return [k for k in catalogue.load("en") if not k.startswith("_")]


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


def _outbound(text, lang, translator, field="response_text", options=()):
    return asyncio.run(boundary.translate_outbound(
        {field: text, "options": list(options), "result_type": "final"},
        lang, translator,
    ))


# ---------------------------------------------------------------------------
# 1. Coverage
# ---------------------------------------------------------------------------

def test_catalogue_is_not_empty():
    assert len(_ids()) >= 100, "catalogue looks truncated"


@pytest.mark.parametrize("lang", LANGS)
def test_every_language_file_parses(lang):
    with (MESSAGES_DIR / f"{lang}.json").open(encoding="utf-8") as handle:
        assert isinstance(json.load(handle), dict)


@pytest.mark.parametrize("lang", TARGETS)
def test_every_entry_exists_in_every_language(lang):
    missing = sorted(set(_ids()) - set(catalogue.load(lang)))
    assert not missing, f"{lang}.json is missing: {missing}"


@pytest.mark.parametrize("lang", TARGETS)
def test_no_stray_entries(lang):
    extra = sorted(set(catalogue.load(lang)) - set(catalogue.load("en")) - {"_comment"})
    assert not extra, f"{lang}.json has entries en.json does not: {extra}"


@pytest.mark.parametrize("lang", TARGETS)
def test_slot_counts_match_english(lang):
    """A translation that drops a slot would lose a report name; one that adds
    a slot would raise IndexError at the user."""
    english, target = catalogue.load("en"), catalogue.load(lang)
    bad = []
    for message_id in _ids():
        _, want = catalogue.template_key(english[message_id])
        _, got = catalogue.template_key(target[message_id])
        if want != got:
            bad.append(f"{message_id}: en={want} {lang}={got}")
    assert not bad, "slot count mismatch: " + "; ".join(bad)


@pytest.mark.parametrize("lang", TARGETS)
def test_slot_indices_are_contiguous_from_zero(lang):
    for message_id, template in catalogue.load(lang).items():
        if message_id.startswith("_"):
            continue
        indices = sorted({int(n) for n in re.findall(r"\{(\d+)\}", template)})
        assert indices == list(range(len(indices))), (
            f"{lang}/{message_id} has non-contiguous slots {indices}"
        )


@pytest.mark.parametrize("lang", TARGETS)
def test_translations_differ_from_english(lang):
    """Catches an entry copy-pasted from en.json and never translated."""
    # Terms spelled the same in the target language. Listed BY NAME so a real
    # untranslated entry still fails -- an entry is never silently tolerated.
    IDENTICAL_BY_DESIGN = {
        "fr": {"errcard.item.concept", "errcard.item.dimension",
               "errcard.item.section"},
        "ar": set(),
        "hi": set(),
    }
    english, target = catalogue.load("en"), catalogue.load(lang)
    same = [
        message_id for message_id in _ids()
        # A pure-slot template ("{0}") is legitimately identical everywhere.
        if english[message_id] == target[message_id]
        and re.sub(r"\{\d+\}", "", english[message_id]).strip()
        and message_id not in IDENTICAL_BY_DESIGN.get(lang, set())
    ]
    assert not same, f"{lang}.json still English for: {same}"


@pytest.mark.parametrize("lang,lo,hi", [("ar", 0x0600, 0x06FF), ("hi", 0x0900, 0x097F)])
def test_target_script_is_used(lang, lo, hi):
    target = catalogue.load(lang)
    for message_id in _ids():
        text = target[message_id]
        if not re.sub(r"\{\d+\}", "", text).strip():
            continue
        assert any(lo <= ord(ch) <= hi for ch in text), (
            f"{lang}/{message_id} contains no {lang} script"
        )


def test_no_ambiguous_entries_were_dropped():
    """english_index() drops keys that two entries share. If that fires, two
    messages are indistinguishable and BOTH stop resolving."""
    assert len(catalogue.english_index()) == len(_ids())


# ---------------------------------------------------------------------------
# 2. Fidelity -- catalogue vs what the pipeline really emits
# ---------------------------------------------------------------------------

# Real strings, with the call site that produces each.
PIPELINE_OUTPUT = {
    "guided.ask_report_name_4": "Enter the report name, ReturnId, or short name (e.g. CIMS_ROR, R149, RAQ):",
    "guided.ask_report_name_3": "Enter the report name, ReturnId, or short name (e.g. CIMS_FormGPB, R009):",
    "guided.ask_report_name_compare": "Enter the report name, ReturnId, or short name to compare (e.g. CIMS_RAQ, R009, RAQ):",
    "guided.menu_prompt": "What would you like to do? Select an action to get started:",
    "guided.no_access_action": "Sorry, you do not have access to this action.",
    "disambig.generate": "Found multiple matching reports. Which one would you like to generate?",
    "disambig.schedule": "Found multiple matching reports. Which one would you like to schedule?",
    "disambig.generic": "Found multiple matching reports. Which one do you mean?",
    "disambig.reply_hint": "Reply with the number or part of the name.",
    "date.ask": "Please enter the reporting date for **CIMS_ROR**.",
    "date.select_for": "Select a reporting date for 'CIMS_ROR':",
    "date.select_instance_for": "Select a reporting instance for 'CIMS_RAQ(Monthly)':",
    "date.rule_quarterly": "Quarterly reports must use:",
    "date.rule_fortnightly": "Fortnightly reports must use:",
    "date.rule_daily": "Daily reports accept any valid past date.",
    "date.rule_monthly": "Monthly reports must use the last day of the month.",
    "date.rule_weekly": "Weekly reports must use a Friday.",
    "date.bullet_mid_month": "15th of the month",
    "date.bullet_last_day": "Last day of the month",
    "date.example_one": "Example: 31-Mar-2026",
    "date.example_two": "Example: 15-Sep-2026 or 30-Sep-2026",
    "date.future_not_allowed": "'30-Sep-2026' is a future date. Future reporting dates are not allowed.",
    "date.confirmed": "Reporting date confirmed: **30-Sep-2025**.",
    "gen.instance_for": "Generating instance for 'CIMS_ROR'",
    "gen.msg_added": "Report added successfully for XBRL generation.",
    "gen.msg_started": "Instance generation started successfully.",
    "gen.msg_failed": "Instance generation failed. Please try again.",
    "gen.no_access": "Sorry, you do not have access to generate report instances.",
    "sched.preview_intro": "We are going to generate the report instance with the following schedule details:",
    "sched.provide_datetime": "Please provide the schedule date and time.",
    "sched.confirmed": "Schedule confirmed:",
    "sched.confirm_first": "Please confirm the schedule first by selecting **Schedule** or **Change Data**.",
    "sched.start_over": "No problem! Let’s start over.",
    "sched.provide_name": "Please provide the report name for scheduling.",
    "sched.no_access": "Sorry, you do not have access to schedule report generation.",
    "label.report_name": "Report Name",
    "label.reporting_date": "Reporting Date",
    "label.schedule_date": "Schedule Date",
    "label.schedule_time": "Schedule Time",
    "label.status": "Status",
    "label.initiated_on": "Initiated On",
    "label.latest_reporting_date": "Latest Reporting Date",
    "label.run_date_time": "Run Date/Time",
    "lookup.render_missing": "Render file not found.",
    "lookup.error_file_missing": "Error file not found.",
    "lookup.not_found": "Report 'CIMS_ROR' not found.",
    "auth.no_access_report": "You are not authorised to access this report.",
    "auth.required": "Authentication required. Please access this application through the authorised portal.",
    "errors.no_failed_instances": "Good news — CIMS_ROR has no failed instances, so there are no errors to explain.",
    "compare.pick_two_different": "Please select two different instances to compare.",
    "sql.rows_found_many": "Found 5 rows.",
    "convo.bye": "Goodbye! Have a great day.",
    "convo.alright": "Alright! Let me know if you need anything else.",
}


@pytest.mark.parametrize("message_id,english", sorted(PIPELINE_OUTPUT.items()))
def test_catalogue_matches_real_pipeline_output(message_id, english):
    """DRIFT GUARD. If a string changes in the pipeline, its entry stops
    matching and the message silently costs a model call again. Fail loudly."""
    key, _ = catalogue.structure(english)
    assert catalogue.english_index().get(key) == message_id, (
        f"{english!r} no longer resolves to {message_id} - the English template "
        f"in the pipeline and in en.json have drifted apart"
    )


@pytest.mark.parametrize("message_id,english", sorted(PIPELINE_OUTPUT.items()))
@pytest.mark.parametrize("lang", TARGETS)
def test_pipeline_output_resolves_in_every_language(message_id, english, lang):
    out = catalogue.resolve(english, lang)
    assert out is not None, f"{message_id} did not resolve to {lang}"
    assert out.strip(), f"{message_id} resolved to empty {lang} text"


@pytest.mark.parametrize("message_id,english", sorted(PIPELINE_OUTPUT.items()))
@pytest.mark.parametrize("lang", TARGETS)
def test_resolution_preserves_every_protected_value(message_id, english, lang):
    _, values = catalogue.structure(english)
    out = catalogue.resolve(english, lang)
    for value in values:
        assert value in out, f"{message_id}/{lang} lost protected value {value!r}"


# ---------------------------------------------------------------------------
# 3. Safety -- exact matching, and fallback
# ---------------------------------------------------------------------------

def test_similar_messages_do_not_collide():
    """The three 'Found multiple matching reports' variants differ only in the
    final verb; each must keep its own wording."""
    fr_gen = catalogue.resolve(PIPELINE_OUTPUT["disambig.generate"], "fr")
    fr_sched = catalogue.resolve(PIPELINE_OUTPUT["disambig.schedule"], "fr")
    fr_generic = catalogue.resolve(PIPELINE_OUTPUT["disambig.generic"], "fr")
    assert fr_gen != fr_sched != fr_generic and fr_gen != fr_generic


@pytest.mark.parametrize("text", [
    "The NPA ratio rose 12% quarter on quarter, driven mainly by the retail book.",
    "Here is a sentence the pipeline has never produced.",
    "Found multiple matching reports. Which one would you like to obliterate?",
])
def test_unknown_text_falls_through_to_the_model(text):
    """The fallback is what makes the catalogue safe to extend gradually."""
    assert catalogue.resolve(text, "fr") is None
    spy = Spy()
    out = _outbound(text, "fr", spy)
    assert spy.seen, "unmatched text must reach the runtime translator"
    assert out["response_text"].startswith("<fr>")


def test_partial_match_falls_through_whole():
    """A message whose lines resolve only partially must NOT render half in
    each language."""
    mixed = (
        "Quarterly reports must use:\n"
        "Something the catalogue has never seen before."
    )
    assert catalogue.resolve(mixed, "fr") is None


def test_english_never_resolves():
    for english in PIPELINE_OUTPUT.values():
        assert catalogue.resolve(english, "en") is None


def test_unsupported_language_does_not_resolve():
    assert catalogue.resolve(PIPELINE_OUTPUT["sched.confirmed"], "de") is None


def test_mismatched_slot_count_is_refused(monkeypatch):
    """A hand-edited translation that drops a slot must be rejected, not
    formatted into a message with a missing report name."""
    broken = dict(catalogue.load("fr"))
    broken["gen.instance_for"] = "Génération de l’instance"      # slot removed
    monkeypatch.setattr(catalogue, "load",
                        lambda lang: broken if lang == "fr" else catalogue.load.__wrapped__(lang))
    assert catalogue.resolve("Generating instance for 'CIMS_ROR'", "fr") is None


# ---------------------------------------------------------------------------
# 4. Multi-line flows resolve with ZERO model calls
# ---------------------------------------------------------------------------

GENERATE_RESULT = (
    "Generating instance for 'CIMS_ROR'\n"
    "Reporting Date : 31-Mar-2026\n"
    "Status         : Report added successfully for XBRL generation."
)
DATE_PROMPT = (
    "Please enter the reporting date for **CIMS_ROR**.\n"
    "\n"
    "Quarterly reports must use:\n"
    "• 31-Mar\n• 30-Jun\n• 30-Sep\n• 31-Dec\n"
    "\n"
    "Example: 31-Mar-2026"
)
SCHEDULE_PREVIEW = (
    "We are going to generate the report instance with the following schedule details:\n"
    "\n"
    "Report Name    : CIMS_FormA_R013_F\n"
    "Reporting Date : 30-Sep-2025\n"
    "Schedule Date  : 12-Dec-2026\n"
    "Schedule Time  : 17:00"
)
SCHEDULE_CONFIRMED = (
    "Schedule confirmed:\n"
    "Report          : CIMS_FormA_R013_F\n"
    "Reporting Date  : 30-Sep-2025\n"
    "Schedule Date   : 12-Dec-2026\n"
    "Schedule Time   : 17:00\n"
    "Scheduled       : 2026-12-12T17:00:00"
)
DISAMBIGUATION = (
    "Found multiple matching reports. Which one would you like to generate?\n"
    "\n"
    "1. CIMS_FormGPB\n2. CIMS_FormA_R013_F\n"
    "\n"
    "Reply with the number or part of the name."
)

FLOWS = {
    "generate.result": GENERATE_RESULT,
    "generate.date_prompt": DATE_PROMPT,
    "schedule.preview": SCHEDULE_PREVIEW,
    "schedule.confirmed": SCHEDULE_CONFIRMED,
    "disambiguation": DISAMBIGUATION,
}

FLOW_ENTITIES = {
    "generate.result": ["CIMS_ROR", "31-Mar-2026", "XBRL"],
    "generate.date_prompt": ["**CIMS_ROR**", "31-Mar", "30-Jun", "30-Sep", "31-Dec", "31-Mar-2026"],
    "schedule.preview": ["CIMS_FormA_R013_F", "30-Sep-2025", "12-Dec-2026", "17:00"],
    "schedule.confirmed": ["CIMS_FormA_R013_F", "30-Sep-2025", "12-Dec-2026", "17:00",
                           "2026-12-12T17:00:00"],
    "disambiguation": ["CIMS_FormGPB", "CIMS_FormA_R013_F"],
}


@pytest.mark.parametrize("name", sorted(FLOWS))
@pytest.mark.parametrize("lang", TARGETS)
def test_flow_needs_zero_model_calls(name, lang):
    """THE success criterion: known deterministic responses cost no LLM call."""
    options = ["CIMS_FormGPB", "CIMS_FormA_R013_F"] if name == "disambiguation" else []
    out = _outbound(FLOWS[name], lang, Boom(), options=options)
    meta = out["data"]["i18n"]["outbound"]
    assert meta["calls"] == 0, f"{name}/{lang} still made {meta['calls']} model calls"
    assert meta["catalogued"] == ["response_text"]


@pytest.mark.parametrize("name", sorted(FLOWS))
@pytest.mark.parametrize("lang", TARGETS)
def test_flow_preserves_protected_entities(name, lang):
    options = ["CIMS_FormGPB", "CIMS_FormA_R013_F"] if name == "disambiguation" else []
    out = _outbound(FLOWS[name], lang, Boom(), options=options)
    for entity in FLOW_ENTITIES[name]:
        assert entity in out["response_text"], f"{name}/{lang} lost {entity!r}"


@pytest.mark.parametrize("name", sorted(FLOWS))
@pytest.mark.parametrize("lang", TARGETS)
def test_flow_preserves_line_structure(name, lang):
    options = ["CIMS_FormGPB", "CIMS_FormA_R013_F"] if name == "disambiguation" else []
    out = _outbound(FLOWS[name], lang, Boom(), options=options)
    assert out["response_text"].count("\n") == FLOWS[name].count("\n")


@pytest.mark.parametrize("lang", TARGETS)
def test_markdown_and_bullets_survive(lang):
    out = _outbound(DATE_PROMPT, lang, Boom())["response_text"]
    assert "**CIMS_ROR**" in out
    assert out.count("•") == 4


@pytest.mark.parametrize("lang", TARGETS)
def test_flows_are_actually_localized(lang):
    """Zero calls is only a win if the text really changed language."""
    for name, english in FLOWS.items():
        options = ["CIMS_FormGPB", "CIMS_FormA_R013_F"] if name == "disambiguation" else []
        out = _outbound(english, lang, Boom(), options=options)["response_text"]
        assert out != english, f"{name}/{lang} came back identical to English"


# ---------------------------------------------------------------------------
# 5. English and the disabled path are untouched
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", sorted(FLOWS))
def test_english_returns_the_identical_object(name):
    original = {"response_text": FLOWS[name], "options": []}
    assert asyncio.run(boundary.translate_outbound(original, "en", Boom())) is original


@pytest.mark.parametrize("name", sorted(FLOWS))
def test_disabled_returns_the_identical_object(name, monkeypatch):
    monkeypatch.setenv("MULTILINGUAL_ENABLED", "false")
    original = {"response_text": FLOWS[name], "options": []}
    assert asyncio.run(boundary.translate_outbound(original, "fr", Boom())) is original


def test_options_are_never_touched_by_the_catalogue():
    options = ["CIMS_FormGPB", "CIMS_FormA_R013_F"]
    out = _outbound(DISAMBIGUATION, "fr", Boom(), options=options)
    assert out["options"] == options


def test_dynamic_fields_still_use_the_model():
    """llm_summary and db_beautified are free-form and must keep going to the
    translator even when response_text resolves from the catalogue."""
    spy = Spy()
    out = asyncio.run(boundary.translate_outbound(
        {"response_text": "Schedule confirmed:",
         "llm_summary": "Provisions rose 12% because the retail book deteriorated.",
         "options": []},
        "fr", spy,
    ))
    meta = out["data"]["i18n"]["outbound"]
    assert meta["catalogued"] == ["response_text"]
    assert meta["calls"] == 1, "the free-form summary must still be translated"
    assert out["llm_summary"].startswith("<fr>")
