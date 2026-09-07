"""Tests for the STATIC UI text dictionary (frontend/src/i18n.js).

Static text is looked up locally and NEVER sent to the translation model. These
tests defend the two properties that make that safe:

  1. Completeness -- every key resolves in all four languages, so no user ever
     sees an English string leaking through a French UI (or `undefined`).

  2. Token integrity -- ACTIONS is keyed by the EXACT English strings in
     backend/guided.py's GUIDED_ACTIONS. Those keys are a wire protocol:
     guided.py:179-180 matches an incoming message with `msg in GUIDED_ACTIONS`,
     and /allowed-actions filters on the same literals. If a key here is ever
     renamed to its translation, every guided button silently stops working --
     with no error, in production, only for non-English users.

The dictionary is read by executing the real module (via node) rather than
regex-parsing it, so the test sees exactly what the browser will.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND = PROJECT_ROOT / "frontend"
DUMP_SCRIPT = FRONTEND / "scripts" / "dump-i18n.mjs"

LANGS = ("en", "fr", "ar", "hi")


@pytest.fixture(scope="module")
def i18n() -> dict:
    node = shutil.which("node")
    if node is None or not DUMP_SCRIPT.exists():
        pytest.skip("node / dump-i18n.mjs not available")
    out = subprocess.run(
        [node, str(DUMP_SCRIPT)], cwd=FRONTEND, capture_output=True, timeout=60,
    )
    if out.returncode != 0:
        pytest.fail(out.stderr.decode("utf-8", "replace"))
    return json.loads(out.stdout.decode("utf-8"))


def _all_dicts(i18n: dict):
    yield "STRINGS", i18n["STRINGS"]
    yield "ACTIONS", i18n["ACTIONS"]
    yield "ACTION_DESCRIPTIONS", i18n["ACTION_DESCRIPTIONS"]


# ---------------------------------------------------------------------------
# Completeness
# ---------------------------------------------------------------------------

def test_every_entry_covers_all_four_languages(i18n):
    missing: list[str] = []
    for name, table in _all_dicts(i18n):
        for key, entry in table.items():
            for lang in LANGS:
                if not str(entry.get(lang, "")).strip():
                    missing.append(f"{name}[{key!r}].{lang}")
    assert not missing, "untranslated entries: " + ", ".join(missing)


def test_no_entry_has_an_unexpected_language(i18n):
    for name, table in _all_dicts(i18n):
        for key, entry in table.items():
            extra = set(entry) - set(LANGS)
            assert not extra, f"{name}[{key!r}] has unknown languages {extra}"


def test_selector_offers_exactly_the_supported_languages(i18n):
    assert [item["code"] for item in i18n["LANGUAGES"]] == list(LANGS)
    assert all(item["label"].strip() for item in i18n["LANGUAGES"])
    assert i18n["RTL"] == ["ar"]


def test_translations_actually_differ_from_english(i18n):
    """Catches a placeholder entry that was copy-pasted and never translated."""
    same: list[str] = []
    for name, table in _all_dicts(i18n):
        for key, entry in table.items():
            for lang in ("fr", "ar", "hi"):
                if entry[lang] == entry["en"]:
                    same.append(f"{name}[{key!r}].{lang}")
    assert not same, "still English: " + ", ".join(same)


@pytest.mark.parametrize("lang,lo,hi", [
    ("ar", 0x0600, 0x06FF),   # Arabic
    ("hi", 0x0900, 0x097F),   # Devanagari
])
def test_scripts_are_right_for_the_language(i18n, lang, lo, hi):
    """A French string pasted into the Arabic slot would pass the
    differs-from-English check but not this one."""
    for name, table in _all_dicts(i18n):
        for key, entry in table.items():
            text = entry[lang]
            assert any(lo <= ord(ch) <= hi for ch in text), (
                f"{name}[{key!r}].{lang} contains no {lang} script: {text!r}"
            )


def test_emphasis_markers_are_balanced(i18n):
    """`*bold*` spans are split on '*'; an odd count would bold the rest of
    the line in that language only."""
    for key, entry in i18n["STRINGS"].items():
        for lang in LANGS:
            count = entry[lang].count("*")
            assert count % 2 == 0, f"STRINGS[{key!r}].{lang} has {count} '*'"


# ---------------------------------------------------------------------------
# Token integrity -- the invariant that spans JS and Python
# ---------------------------------------------------------------------------

def test_action_keys_match_backend_guided_actions_exactly(i18n):
    """THE critical one. These keys are sent to /guided verbatim."""
    from backend.guided import GUIDED_ACTIONS
    assert sorted(i18n["ACTIONS"]) == sorted(GUIDED_ACTIONS)
    assert sorted(i18n["ACTION_DESCRIPTIONS"]) == sorted(GUIDED_ACTIONS)


def test_english_action_label_equals_its_own_token(i18n):
    """In English the label IS the token. If these ever diverge, an English
    user's button would send something the backend does not recognise."""
    for token, entry in i18n["ACTIONS"].items():
        assert entry["en"] == token


def test_a_translated_label_is_never_a_valid_token(i18n):
    """Guards the reverse mistake: a localized label must not accidentally
    collide with a token, which would mask a send-the-label bug."""
    from backend.guided import GUIDED_ACTIONS
    tokens = set(GUIDED_ACTIONS)
    for token, entry in i18n["ACTIONS"].items():
        for lang in ("fr", "ar", "hi"):
            assert entry[lang] not in tokens


# ---------------------------------------------------------------------------
# Static text costs zero LLM calls
# ---------------------------------------------------------------------------

def _strip_comments(source: str) -> str:
    """Drop // and /* */ comments.

    Comments legitimately discuss the very things these tests ban from the
    code -- the translation model, the /chat endpoint, the English strings
    being replaced -- and banning the explanation along with the behaviour
    would only push the reasoning out of the file.
    """
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    return re.sub(r"(?<![:'\"])//[^\n]*", "", source)


def test_dictionary_module_makes_no_network_call():
    """The whole point of static resources: no fetch, no api.js, no model."""
    code = _strip_comments((FRONTEND / "src" / "i18n.js").read_text(encoding="utf-8"))
    for forbidden in ("fetch(", "XMLHttpRequest", "axios", "services/api",
                      "TRANSLATION_MODEL", "'/chat'", "'/guided'"):
        assert forbidden not in code, f"i18n.js references {forbidden!r}"
    # Only react (for the context binding) and the sibling UI dictionary.
    # Anything else would mean the dictionary grew a runtime dependency.
    imports = sorted(set(re.findall(r"from\s+'([^']+)'", code)))
    assert imports == ["./i18n.ui.js", "react"], f"unexpected imports: {imports}"


def test_static_text_is_not_in_the_backend_translatable_payload():
    """Static UI text never travels through the response fields the runtime
    translator touches, so it can never reach TRANSLATION_MODEL."""
    from backend.i18n.boundary import TRANSLATABLE_FIELDS
    assert "options" not in TRANSLATABLE_FIELDS
    assert "db_qa_data" not in TRANSLATABLE_FIELDS
    # The prose fields are dynamic content only; nothing here is UI chrome.
    assert set(TRANSLATABLE_FIELDS) == {
        "response_text", "llm_summary", "db_summary", "db_beautified",
        "status_note", "accuracy_hint", "more_info_hint", "download_label",
    }


# ---------------------------------------------------------------------------
# The components actually use the dictionary
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("literal", [
    "🧭 Guided<",          # the guided badge, MessageBubble.jsx:1085
    "I can help you with:",
    "What would you like to do next?",
    "Was this helpful?",
    "Ask about a report",
    "Type your answer",
    "Guided mode — answer the question above",
    "Something went wrong. Please try again.",
])
def test_hardcoded_english_literals_are_gone(literal):
    """A literal left behind renders English regardless of the selection."""
    for name in ("App.jsx", "components/MessageBubble.jsx"):
        code = _strip_comments((FRONTEND / "src" / name).read_text(encoding="utf-8"))
        assert literal not in code, f"{name} still hardcodes {literal!r}"


def test_action_tokens_remain_literal_in_the_frontend():
    """The tokens themselves MUST still appear verbatim -- they are the wire
    protocol. This is the counterpart to the test above: chrome gets replaced,
    tokens do not."""
    from backend.guided import GUIDED_ACTIONS
    source = (FRONTEND / "src" / "components" / "MessageBubble.jsx").read_text(
        encoding="utf-8"
    )
    for token in GUIDED_ACTIONS:
        assert token in source, f"action token {token!r} lost from the frontend"
