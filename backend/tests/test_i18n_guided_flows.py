"""End-to-end guided FLOWS in English / French / Arabic / Hindi.

Covers the six flows the product exposes -- generate, schedule, status,
comparative analysis, database retrieval, error explanation -- turn by turn,
using the real strings from the real call sites.

Every fixture is cited to the line that produces it, so a wording change in the
pipeline shows up here as a failing test rather than as English text in a
French conversation.

Two categories of `options[]` are deliberately treated differently and both are
asserted here:

  COMMAND options -- "Schedule", "Change Data", "Yes", "No". A fixed set defined
  in code. Localized by the STATIC dictionary (zero LLM calls) and displayed
  translated, while the click always sends the English value that
  agent/__init__.py:1443-1457 matches on.

  DATA options -- report/return/instance names. Never translated by anything.
"""
from __future__ import annotations

import asyncio
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from backend.i18n import boundary
from backend.i18n.translator import TranslationResult

LANGS = ("fr", "ar", "hi")
FRONTEND = Path(__file__).resolve().parents[2] / "frontend"

# ---------------------------------------------------------------------------
# The six flows, turn by turn. (response_text, options, source)
# ---------------------------------------------------------------------------

FLOWS: dict[str, list[tuple[str, list[str]]]] = {
    # ── 1. Generate ────────────────────────────────────────── guided.py:372
    "generate": [
        ("Enter the report name, ReturnId, or short name (e.g. CIMS_FormGPB, R009):", []),
        # agent/__init__.py:4204
        ("Found multiple matching reports. Which one would you like to generate?\n\n"
         "1. CIMS_FormGPB\n2. CIMS_FormA_R013_F\n\n"
         "Reply with the number or part of the name.",
         ["CIMS_FormGPB", "CIMS_FormA_R013_F"]),
        # agent/__init__.py:4048 (_date_ask_prompt, freq "D")
        ("Please enter the reporting date for **CIMS_FormGPB**.\n\n"
         "Daily reports accept any valid past date.\n\n"
         "Example: 26-May-2026", []),
        # agent/__init__.py:4096-4103 (freq "F")
        ("Please enter the reporting date for **CIMS_FormGPB**.\n\n"
         "Fortnightly reports must use:\n"
         "• 15th of the month\n• Last day of the month\n\n"
         "Example: 15-Sep-2026 or 30-Sep-2026", []),
        # tools/instance_generator.py:441
        ("'30-Sep-2026' is a future date. Future reporting dates are not allowed.", []),
        # agent/__init__.py:4000-4007
        ("Generating instance for 'CIMS_FormGPB'\n"
         "Reporting Date : 30-Sep-2025\n"
         "Status         : Report added successfully for XBRL generation.", []),
    ],
    # ── 2. Schedule ────────────────────────────────────────────────────────
    "schedule": [
        # agent/__init__.py:3791
        ("Found multiple matching reports. Which one would you like to schedule?\n\n"
         "1. CIMS_FormA_R013_F\n\nReply with the number or part of the name.",
         ["CIMS_FormA_R013_F"]),
        # agent/__init__.py:3641-3643
        ("Reporting date confirmed: **30-Sep-2025**.\n"
         "Please provide the schedule date and time.", []),
        # agent/__init__.py:3678-3686  -- COMMAND options
        ("We are going to generate the report instance with the following schedule details:\n\n"
         "Report Name    : CIMS_FormA_R013_F\n"
         "Reporting Date : 30-Sep-2025\n"
         "Schedule Date  : 12-Dec-2026\n"
         "Schedule Time  : 17:00",
         ["Schedule", "Change Data"]),
        # agent/__init__.py:1512-1514
        ("Please confirm the schedule first by selecting **Schedule** or **Change Data**.",
         ["Schedule", "Change Data"]),
        # agent/__init__.py:1487-1493
        ("Schedule confirmed:\n"
         "Report          : CIMS_FormA_R013_F\n"
         "Reporting Date  : 30-Sep-2025\n"
         "Schedule Date   : 12-Dec-2026\n"
         "Schedule Time   : 17:00\n"
         "Scheduled       : 2026-12-12T17:00:00", []),
        # agent/__init__.py:1449-1452
        ("No problem! Let’s start over.\nPlease provide the report name for scheduling.", []),
    ],
    # ── 3. Status ──────────────────────────────────── guided.py:363, agent:3335
    "status": [
        ("Enter the report name, ReturnId, or short name (e.g. CIMS_ROR, R149, RAQ):", []),
        ("Select a reporting date for 'CIMS_ROR':",
         ["31-Mar-2026 | Completed", "31-Dec-2025 | Failed"]),
        # agent/__init__.py:3213-3225 -- the real status card shape
        ("CIMS_ROR\n"
         "Latest Reporting Date : 31-Mar-2026\n"
         "Status                : Completed\n"
         "Initiated On          : 31-Mar-2026", []),
    ],
    # ── 4. Comparative analysis ────────────────────────────── guided.py:390
    "compare": [
        ("Enter the report name, ReturnId, or short name to compare "
         "(e.g. CIMS_RAQ, R009, RAQ):", []),
        # agent/__init__.py:2552
        ("Select a reporting instance for 'CIMS_RAQ(Monthly)':",
         ["31-Mar-2026 | Completed", "28-Feb-2026 | Completed"]),
        # xbrl_comparator -- MODEL-AUTHORED narrative, genuinely free-form
        ("Comparison complete. 42 concepts compared, 7 with significant variance.", []),
    ],
    # ── 5. Database retrieval ──────────────────────── guided.py:410, db_qa ──
    "database": [
        # guided.py:411 -- the real prompt, not a paraphrase
        ("What data would you like to query? Please describe in detail "
         "(include report name and period if relevant):", []),
        # sql_agent/__init__.py:128
        ("Found 5 rows.", []),
        # db_qa_router.py:762 -- LLM-BEAUTIFIED, genuinely free-form
        ("There are 3 active users in the Compliance department.", []),
    ],
    # ── 6. Error explanation ──────────────── guided.py:401, agent:2516-2524
    "errors": [
        ("Enter the report name, ReturnId, or short name (e.g. CIMS_ROR, R149, RAQ):", []),
        ("Good news — CIMS_ROR has no failed instances, so there are no errors "
         "to explain.\n\n"
         'Use "Check report status" if you want to see its other instances.', []),
        # agent/__init__.py:2552 -- the real wording
        ("Select a reporting instance for 'CIMS_ROR':",
         ["31-Dec-2025 | Failed"]),
    ],
}

# Tokens that must survive byte-for-byte in every language.
PROTECTED_TOKENS = [
    "CIMS_FormGPB", "CIMS_FormA_R013_F", "CIMS_RAQ", "CIMS_RAQ(Monthly)",
    "CIMS_ROR", "R009", "R149", "RAQ", "XBRL", "ReturnId",
    "26-May-2026", "15-Sep-2026", "30-Sep-2026", "30-Sep-2025",
    "12-Dec-2026", "31-Mar-2026", "31-Dec-2025", "28-Feb-2026",
    "17:00", "2026-12-12T17:00:00", "4f2a1c9e8b7d4a5f9c0e1b2d3a4f5e6c",
]


@pytest.fixture(autouse=True)
def _enabled(monkeypatch):
    monkeypatch.setenv("MULTILINGUAL_ENABLED", "true")
    monkeypatch.setenv("TRANSLATION_MODEL", "qwen3:14b")
    monkeypatch.setenv("SUPPORTED_LANGUAGES", "en,fr,ar,hi")
    monkeypatch.setenv("TRANSLATION_MAX_CHARS", "2000")


class Recorder:
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


def _turn(text, options, lang, translator):
    return asyncio.run(boundary.translate_outbound(
        {"response_text": text, "options": list(options), "result_type": "final"},
        lang, translator,
    ))


def _cases():
    for flow, turns in FLOWS.items():
        for i, (text, options) in enumerate(turns):
            yield flow, i, text, options


ALL_TURNS = list(_cases())
IDS = [f"{flow}-{i}" for flow, i, _, _ in ALL_TURNS]

# Turns whose text is NOT authored by the pipeline as a template, so they
# legitimately reach the runtime translator:
#   database-2  db_qa_router.py:762, beautified by the LLM per query
#   compare-2   the variance narrative, written by the model
NEEDS_MODEL = {("database", 2), ("compare", 2)}

DETERMINISTIC = [(f, i, t, o) for f, i, t, o in ALL_TURNS if (f, i) not in NEEDS_MODEL]
DET_IDS = [f"{f}-{i}" for f, i, _, _ in DETERMINISTIC]


# ---------------------------------------------------------------------------
# A. Every turn of every flow is translated
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("flow,i,text,options", ALL_TURNS, ids=IDS)
@pytest.mark.parametrize("lang", LANGS)
def test_every_turn_is_translated(flow, i, text, options, lang):
    """Localized by EITHER mechanism: the pre-translated catalogue (0 model
    calls) or the runtime translator. What matters to the user is that the
    English is gone; which path did it is asserted separately."""
    rec = Recorder()
    out = _turn(text, options, lang, rec)
    meta = out["data"]["i18n"]["outbound"]
    assert out["response_text"] != text, (
        f"{flow} turn {i} came back identical to English in {lang}"
    )
    assert "response_text" in (meta["catalogued"] + meta["fields"])


@pytest.mark.parametrize("flow,i,text,options", ALL_TURNS, ids=IDS)
def test_english_is_untouched(flow, i, text, options):
    rec = Recorder()
    original = {"response_text": text, "options": list(options)}
    assert asyncio.run(boundary.translate_outbound(original, "en", rec)) is original
    assert rec.seen == [], "English must make no model call"


@pytest.mark.parametrize("flow,i,text,options", DETERMINISTIC, ids=DET_IDS)
@pytest.mark.parametrize("lang", LANGS)
def test_no_english_prose_survives(flow, i, text, options, lang):
    """No English prose may remain.

    Checked by exact reconstruction rather than word-spotting: the localized
    output must equal what the catalogue produces for this message. A
    substring scan for English words is unsound here -- French legitimately
    contains "date", "instance", "confirmer", "comparer" and so on, so it
    reports failures that are not failures.

    Protected values (report names, dates, numbers, acronyms) SHOULD survive
    verbatim; that is asserted separately.
    """
    from backend.i18n import catalogue

    out = _turn(text, options, lang, Recorder())["response_text"]
    assert out != text, f"{flow} turn {i} came back identical to English"

    # Every prose line must be reproducible from the target-language
    # catalogue: take the English line, resolve it, and require the result to
    # appear in the output. Data-only lines (option entries, bare identifiers)
    # are skipped -- those are meant to stay verbatim.
    for english_line in text.split("\n"):
        stripped = english_line.strip()
        if not stripped or catalogue._is_pure_data(stripped):
            continue
        localized_line = catalogue._resolve_line(english_line, lang)
        assert localized_line is not None, (
            f"{flow} turn {i}: line {english_line!r} has no {lang} translation"
        )
        assert localized_line.strip() in out, (
            f"{flow} turn {i}: expected {localized_line.strip()!r} in the "
            f"{lang} output but got:\n{out}"
        )


# ---------------------------------------------------------------------------
# B. Protected entities
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("flow,i,text,options", ALL_TURNS, ids=IDS)
@pytest.mark.parametrize("lang", LANGS)
def test_protected_tokens_never_reach_the_model(flow, i, text, options, lang):
    rec = Recorder()
    _turn(text, options, lang, rec)
    for token in PROTECTED_TOKENS:
        if token in text:
            assert token not in rec.sent, (
                f"{flow} turn {i}: {token!r} was sent to the model in {lang}"
            )


@pytest.mark.parametrize("flow,i,text,options", ALL_TURNS, ids=IDS)
@pytest.mark.parametrize("lang", LANGS)
def test_protected_tokens_return_verbatim(flow, i, text, options, lang):
    body = _turn(text, options, lang, Recorder())["response_text"]
    for token in PROTECTED_TOKENS:
        if token in text:
            assert token in body, f"{flow} turn {i}: {token!r} lost in {lang}"


@pytest.mark.parametrize("flow,i,text,options", ALL_TURNS, ids=IDS)
@pytest.mark.parametrize("lang", LANGS)
def test_options_are_never_translated(flow, i, text, options, lang):
    """options[] is the wire value in every case -- report names AND command
    tokens. Only the DISPLAY is localized, and that happens in the frontend."""
    out = _turn(text, options, lang, Recorder())
    assert out["options"] == list(options)


@pytest.mark.parametrize("lang", LANGS)
def test_hostile_translator_cannot_corrupt_any_flow(lang):
    hostile = Recorder(transform=lambda t: (
        t.replace("CIMS", "SIMC").replace("Sep", "Sept").replace("Dec", "Déc")
         .replace("17:00", "5 PM").replace("2026", "٢٠٢٦").upper()
    ))
    for flow, i, text, options in ALL_TURNS:
        body = _turn(text, options, lang, hostile)["response_text"]
        for token in PROTECTED_TOKENS:
            if token in text:
                assert token in body, f"{flow} turn {i}: corrupted {token!r}"


@pytest.mark.parametrize("lang", LANGS)
def test_iso_timestamp_stays_one_token(lang):
    """agent/__init__.py:1493 emits 2026-12-12T17:00:00. Split across the date
    and time patterns the bare 'T' would be handed to the model."""
    text = "Scheduled       : 2026-12-12T17:00:00"
    rec = Recorder()
    out = _turn(text, [], lang, rec)
    assert "2026-12-12T17:00:00" in out["response_text"]
    assert "2026-12-12" not in rec.sent and "17:00:00" not in rec.sent
    assert rec.sent.count("T") == 0 or "[[E1]]T" not in rec.sent


@pytest.mark.parametrize("lang", LANGS)
def test_markdown_and_bullets_survive(lang):
    text = FLOWS["generate"][3][0]          # fortnightly rules, with bullets
    body = _turn(text, [], lang, Recorder())["response_text"]
    assert "**CIMS_FormGPB**" in body
    assert body.count("•") == 2
    assert body.count("\n") == text.count("\n")


@pytest.mark.parametrize("lang", LANGS)
def test_disambiguation_list_is_re_rendered_locally(lang):
    text, options = FLOWS["generate"][1]
    rec = Recorder()
    body = _turn(text, options, lang, rec)["response_text"]
    for n, name in enumerate(options, 1):
        assert f"{n}. {name}" in body
        assert name not in rec.sent


# ---------------------------------------------------------------------------
# C. Command options are localized statically, tokens stay English
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def static_dict() -> dict:
    """The real frontend dictionary, read by executing the module."""
    node = shutil.which("node")
    script = FRONTEND / "scripts" / "dump-i18n.mjs"
    if node is None or not script.exists():
        pytest.skip("node / dump-i18n.mjs not available")
    out = subprocess.run([node, str(script)], cwd=FRONTEND,
                         capture_output=True, timeout=60)
    if out.returncode != 0:
        pytest.fail(out.stderr.decode("utf-8", "replace"))
    return json.loads(out.stdout.decode("utf-8"))


COMMAND_OPTIONS = ("Schedule", "Change Data", "Yes", "No")


@pytest.mark.parametrize("value", COMMAND_OPTIONS)
def test_command_options_are_in_the_static_dictionary(static_dict, value):
    """They are a fixed, code-defined set the user reads and clicks -- genuinely
    static UI text, so they cost zero LLM calls."""
    labels = static_dict["OPTION_LABELS"]
    assert value in labels, f"{value!r} missing from OPTION_LABELS"
    for lang in ("en",) + LANGS:
        assert labels[value][lang].strip()


@pytest.mark.parametrize("value", COMMAND_OPTIONS)
def test_command_option_keys_are_the_english_wire_value(static_dict, value):
    """agent/__init__.py:1443 does `"change" in raw`, :1457 does
    `raw == "schedule"`, both on the lower-cased English reply. The key must
    stay English or the confirmation buttons stop working."""
    assert static_dict["OPTION_LABELS"][value]["en"] == value


@pytest.mark.parametrize("value", COMMAND_OPTIONS)
@pytest.mark.parametrize("lang", LANGS)
def test_command_option_is_actually_localized(static_dict, value, lang):
    assert static_dict["OPTION_LABELS"][value][lang] != value


def test_data_options_are_absent_from_the_dictionary(static_dict):
    """t.option() returns anything it does not know unchanged, which is what
    makes report and instance names pass through untouched."""
    labels = static_dict["OPTION_LABELS"]
    for name in ("CIMS_ROR", "CIMS_FormGPB", "CIMS_FormA_R013_F",
                 "RAQ(Quarterly)", "31-Mar-2026 | Completed"):
        assert name not in labels


def test_every_command_option_in_the_pipeline_is_covered(static_dict):
    """Scans the agent for literal command option lists so a new one added to
    the pipeline cannot silently render in English."""
    source = (Path(__file__).resolve().parents[1] / "agent" / "__init__.py").read_text(
        encoding="utf-8"
    )
    literal_lists = re.findall(r'options=\[((?:\s*"[^"]+"\s*,?)+)\]', source)
    found: set[str] = set()
    for group in literal_lists:
        found.update(re.findall(r'"([^"]+)"', group))
    uncovered = found - set(static_dict["OPTION_LABELS"])
    assert not uncovered, (
        f"command options with no localized label: {sorted(uncovered)}"
    )


def test_frontend_sends_the_english_value_not_the_label():
    """The click handler must pass `opt`, never `t.option(opt)`."""
    source = (FRONTEND / "src" / "components" / "MessageBubble.jsx").read_text(
        encoding="utf-8"
    )
    assert "onSuggestion?.(t.option(" not in source
    assert "onSuggestion?.(opt)" in source
    assert source.count("t.option(opt)") >= 4, "chip labels not localized"


# ---------------------------------------------------------------------------
# D. Nothing else moved
# ---------------------------------------------------------------------------

def test_guided_action_protocol_tokens_stay_english(static_dict):
    from backend.guided import GUIDED_ACTIONS
    assert sorted(static_dict["ACTIONS"]) == sorted(GUIDED_ACTIONS)
    for token in GUIDED_ACTIONS:
        assert static_dict["ACTIONS"][token]["en"] == token


def test_translatable_fields_unchanged():
    assert boundary.TRANSLATABLE_FIELDS == (
        "response_text", "llm_summary", "db_summary", "db_beautified",
        "status_note", "accuracy_hint", "more_info_hint", "download_label",
    )


def test_one_call_per_distinct_string_across_a_whole_flow():
    """A flow whose turns repeat a string must not pay for it twice.

    Uses free-form text: a catalogued message costs zero calls, so it could
    not demonstrate deduplication."""
    rec = Recorder()
    repeated = "Provisions rose sharply across the retail portfolio this quarter."
    asyncio.run(boundary.translate_outbound(
        {"response_text": repeated, "db_summary": repeated, "options": []},
        "fr", rec,
    ))
    assert len(rec.seen) == 1


@pytest.mark.parametrize("flow,i,text,options", DETERMINISTIC, ids=DET_IDS)
@pytest.mark.parametrize("lang", LANGS)
def test_deterministic_turns_cost_no_model_call(flow, i, text, options, lang):
    """THE cost guarantee: a deterministic turn must not touch the model."""
    rec = Recorder()
    out = _turn(text, options, lang, rec)
    assert out["data"]["i18n"]["outbound"]["calls"] == 0, (
        f"{flow} turn {i}/{lang} fell through to the model - its catalogue "
        f"entry is missing or has drifted"
    )
    assert rec.seen == []


@pytest.mark.parametrize("flow,i", sorted(NEEDS_MODEL))
@pytest.mark.parametrize("lang", LANGS)
def test_free_form_turns_still_reach_the_model(flow, i, lang):
    """The fallback stays live for content the pipeline did not author."""
    text, options = FLOWS[flow][i]
    rec = Recorder()
    out = _turn(text, options, lang, rec)
    assert out["data"]["i18n"]["outbound"]["calls"] == 1
    assert rec.seen
