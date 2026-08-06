"""End-to-end paraphrase coverage for the DEPARTMENT module, run against the
FULL classify_new_with_semantic_tiers() pipeline (regex -> embedding ->
LLM disambiguation) rather than classify_new() (regex only).

Why this file exists, and why it's separate from
test_new_intent_classifier_phrasing.py: as of the department-module accuracy
pass, tier-1 regex was DELIBERATELY narrowed to only its clearest,
templated triggers (see new_intent_classifier.py's DEPARTMENT_RETURNS rule
comment) — broad paraphrase coverage is now the embedding tier's job,
reinforced by richer exemplars (exemplars.py) and, for genuinely novel
phrasings that don't clear the embedding floor at all, a scoped widening of
LLM disambiguation (DEPARTMENT_INTENTS in new_intent_classifier.py). Testing
these paraphrases against classify_new() alone would now correctly fail —
that isn't a regression, it's what "stop relying primarily on regex" means.

Two run modes:
  - test_*_stubbed: disambiguate_intent() is monkeypatched to a fixed,
    deterministic choice. Fast, no Ollama dependency, safe for CI. This
    checks that a paraphrase reaches the CORRECT CANDIDATE LIST — i.e. the
    right intent is actually on offer — even if it can't verify the live
    model's own judgment.
  - test_live_llm_department_paraphrases: calls the real
    disambiguate_intent() (Ollama). Skipped automatically if Ollama isn't
    reachable. This is what actually confirms end-to-end accuracy; the
    stubbed tests alone cannot.
"""
from __future__ import annotations

import asyncio

import pytest

from backend.db_qa.intents.taxonomy import Intent
from backend.db_qa.new_intent_classifier import classify_new_with_semantic_tiers


def _classify(text: str) -> tuple[Intent | None, dict, str | None, str]:
    return asyncio.run(classify_new_with_semantic_tiers(text))


# ── stubbed disambiguation: correct candidate always offered, always picked ──

def _stub_pick_first(monkeypatch):
    """Patch disambiguate_intent to always pick its first candidate. Since
    _disambiguate() builds candidates directly from the embedding tier's own
    ranking, this verifies "was the correct intent even offered and ranked
    first" without depending on a live model's judgment call."""
    async def _fake(question, candidates):
        return candidates[0][0] if candidates else None

    monkeypatch.setattr(
        "backend.services.llm_service.disambiguate_intent", _fake,
    )


@pytest.mark.parametrize("text", [
    "What department do I belong to?",
    "Which team am I assigned to?",
    "Can you tell me my department?",
    "Show my department.",
    "Where am I assigned?",
])
def test_department_profile_paraphrases_stubbed(monkeypatch, text):
    _stub_pick_first(monkeypatch)
    intent, params, tt, tier = _classify(text)
    assert intent == Intent.DEPARTMENT_PROFILE
    assert tt == "self"


@pytest.mark.parametrize("text", [
    "Which returns can my department access?",
    "Show all returns assigned to my department.",
    "What returns are available for my department?",
    "Which reports can my department file?",
    "List my department's assigned returns.",
    # The originally-reported live failure this whole pass started from.
    "give me list of returns applicable to my department?",
    # Moved from test_new_intent_classifier_phrasing.py — no longer matched
    # by the deliberately-narrowed tier-1 regex; correctly resolved via the
    # embedding/LLM tiers instead.
    "Show me the returns accessible to my department.",
    "Show returns accessible by my department.",
    "What returns are assigned to my department?",
])
def test_department_returns_paraphrases_stubbed(monkeypatch, text):
    _stub_pick_first(monkeypatch)
    intent, params, tt, tier = _classify(text)
    assert intent == Intent.DEPARTMENT_RETURNS
    assert tt == "self"


def test_my_return_access_not_stolen_by_department_returns(monkeypatch):
    """Regression guard for the resolved DEPARTMENT_RETURNS / MY_RETURN_ACCESS
    overlap: these summary/total-framed questions must still resolve to
    MY_RETURN_ACCESS, not get pulled into DEPARTMENT_RETURNS now that the
    latter has much richer exemplar coverage."""
    _stub_pick_first(monkeypatch)
    for text in [
        "What is the complete list of returns I can work with?",
        "How many returns can I access in total?",
        "What returns am I entitled to access?",
        "Give me a full count of the returns I'm allowed to use.",
    ]:
        intent, params, tt, tier = _classify(text)
        assert intent == Intent.MY_RETURN_ACCESS, f"{text!r} -> {intent}"


def test_embedding_none_widened_to_llm_for_department_only(monkeypatch):
    """A phrasing far enough from every exemplar to clear no MIN_SCORE floor
    at all still reaches LLM disambiguation, because it's a department-module
    query (scoped widening) — while a genuinely unrelated query is NOT
    widened and correctly falls straight through instead of paying for an
    LLM call it doesn't need."""
    calls: list[str] = []

    async def _fake(question, candidates):
        calls.append(question)
        return None  # decline — we only care whether the LLM was invoked

    monkeypatch.setattr("backend.services.llm_service.disambiguate_intent", _fake)

    intent, params, tt, tier = _classify("my squad returns pls")
    assert tier == "llm_disambiguation"
    assert calls, "expected disambiguate_intent to be invoked for a department-adjacent novel phrasing"

    calls.clear()
    intent, params, tt, tier = _classify("what is the weather today")
    assert tier == "none"
    assert not calls, "an unrelated query must not trigger the widened department LLM path"


# ── live-Ollama confirmation (skipped automatically if unreachable) ─────────

def _ollama_reachable() -> bool:
    import os
    import urllib.request

    base = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    try:
        urllib.request.urlopen(base, timeout=2)
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _ollama_reachable(), reason="Ollama not reachable")
@pytest.mark.parametrize("text,expected", [
    ("Which team am I assigned to?", Intent.DEPARTMENT_PROFILE),
    ("Where am I assigned?", Intent.DEPARTMENT_PROFILE),
    ("What returns are available for my department?", Intent.DEPARTMENT_RETURNS),
    ("List my department's assigned returns.", Intent.DEPARTMENT_RETURNS),
    ("give me list of returns applicable to my department?", Intent.DEPARTMENT_RETURNS),
])
def test_live_llm_department_paraphrases(text, expected):
    intent, params, tt, tier = _classify(text)
    assert intent == expected, f"{text!r} -> {intent} (tier={tier}), expected {expected}"
