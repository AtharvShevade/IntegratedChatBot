"""Formula-error explanations authored DIRECTLY in the target language.

Context: the deterministic "Why It Failed" / "How to Fix" sentences used to be
built once in English and then localized afterwards through
backend/i18n/catalogue.py — a structural, template-per-rule-kind match. That
meant a formula-rule "kind" formula_kind.py had never been taught a wording
for (or a compound "A — B" label the catalogue's masking could not match)
fell back to a generic per-field model translation call, or to English.

This suite tests the replacement path: backend/tools/error_llm.phrase() is
asked to author "why_failed"/"how_to_fix" DIRECTLY in the requested language
from the same verified, grounded payload build_llm_payload() already builds —
no catalogue entry, no per-kind template, ever required. The result is tagged
`_i18n_native` on its section, and backend/i18n/boundary.py's outbound
translation step must skip re-translating that section's body (translating
Hindi-labelled-as-English a second time could only corrupt an already-grounded
answer), while still translating the section's HEADING normally through the
existing catalogue (a fixed UI label, independent of rule kind).

No network is used: httpx.Client is stubbed to return a canned model
response, exactly like backend/tests/test_error_explanation_v2.py.
"""
from __future__ import annotations

import asyncio
import re

import pytest

from backend.i18n import boundary, catalogue
from backend.i18n.translator import TranslationResult
from backend.tools import error_llm
from backend.tools import formula_error as fe
from backend.tools import formula_kind

DEVANAGARI_RE = re.compile(r"[ऀ-ॿ]")


# ── LLM stub, matching test_error_explanation_v2.py's _stub_llm exactly ─────

class _FakeResponse:
    def __init__(self, content: str):
        self._content = content

    def raise_for_status(self):
        pass

    def json(self):
        return {"message": {"content": self._content}}


class _FakeClient:
    def __init__(self, content, *a, **kw):
        self._content = content

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def post(self, *a, **kw):
        return _FakeResponse(self._content)


def _stub_llm(monkeypatch, content: str) -> None:
    import httpx
    monkeypatch.setattr(httpx, "Client", lambda *a, **kw: _FakeClient(content), raising=True)
    monkeypatch.setenv("ERROR_EXPLAIN_LLM", "1")


@pytest.fixture(autouse=True)
def _force_v1_cards(monkeypatch):
    """Pin ERROR_CARD_V2 off so explanation_sections has the plain
    heading/bullets shape this suite asserts against (test_error_explanation_v2.py
    does the same for the same reason)."""
    monkeypatch.setenv("ERROR_CARD_V2", "0")
    monkeypatch.setenv("MULTILINGUAL_ENABLED", "true")
    monkeypatch.setenv("SUPPORTED_LANGUAGES", "en,fr,ar,hi")


def _rule(rule_name: str = "R"):
    """A — B style aggregate check: Alpha Total = Beta Part + Gamma Part."""
    return {
        "rule_name": rule_name, "has_backtracking": False, "error_count": 1,
        "formula_expression": "$V1 = $V2 + $V3",
        "instances": [{"business_message": "", "facts": [
            {"var": "V1", "concept": "AlphaTotal", "value": "100", "context": "c1",
             "unit": "INR", "decimal": "0", "precision": ""},
            {"var": "V2", "concept": "BetaPart", "value": "60", "context": "c2",
             "unit": "INR", "decimal": "0", "precision": ""},
            {"var": "V3", "concept": "GammaPart", "value": "30", "context": "c3",
             "unit": "INR", "decimal": "0", "precision": ""},
        ]}],
    }


_HI_WHY = (
    "Alpha Total में रिपोर्ट किया गया मान 100 है, जबकि Beta Part (60) और "
    "Gamma Part (30) का योग होना आवश्यक है। इसलिए यह जांच विफल हो गई।"
)
_HI_FIX = (
    "स्रोत डेटा में Alpha Total, Beta Part और Gamma Part की समीक्षा करें और "
    "रिटर्न को पुनः सत्यापित करें।"
)
_HI_CONTENT = f'{{"why_failed": "{_HI_WHY}", "how_to_fix": "{_HI_FIX}"}}'


def _why_section(sections):
    return next(s for s in sections if s.get("heading") == "Why It Failed")


def _fix_section(sections):
    return next(s for s in sections if s.get("heading") == "How to Fix")


# ═════════════════════════════════════════════════════════════════════════
# 1. A brand-new / unclassified rule kind — no catalogue template exists
# ═════════════════════════════════════════════════════════════════════════

class TestUnseenRuleKindNeedsNoCatalogueEntry:
    _KIND = "SOME_BRAND_NEW_KIND_NEVER_SEEN"

    def test_baseline_the_english_sentence_has_no_catalogue_match(self, monkeypatch):
        """Proves the scenario is genuinely uncovered, so the test below
        cannot be passing by accident (e.g. a template that happens to fit)."""
        monkeypatch.setattr(formula_kind, "classify", lambda *a, **kw: self._KIND)
        out = fe.explain_one_rule(_rule(), None, None, error_llm.llm_settings())
        why = _why_section(out["explanation_sections"])
        english_sentence = why["bullets"][-1]
        for lang in ("fr", "ar", "hi"):
            assert catalogue.resolve(english_sentence, lang) is None, (
                f"expected no catalogue template for an unclassified kind ({lang})"
            )

    def test_unseen_kind_still_produces_a_hindi_explanation(self, monkeypatch):
        monkeypatch.setattr(formula_kind, "classify", lambda *a, **kw: self._KIND)
        _stub_llm(monkeypatch, _HI_CONTENT)

        out = fe.explain_one_rule(
            _rule(), None, None, error_llm.llm_settings(), lang="hi",
        )
        sections = out["explanation_sections"]
        why = _why_section(sections)
        fix = _fix_section(sections)

        assert why.get("_i18n_native") == "hi"
        assert fix.get("_i18n_native") == "hi"
        assert DEVANAGARI_RE.search(" ".join(why["bullets"]))
        assert DEVANAGARI_RE.search(" ".join(fix["bullets"]))
        # The grounded facts must still be present verbatim.
        assert "100" in " ".join(why["bullets"])
        assert "Alpha Total" in " ".join(why["bullets"])

    def test_english_request_is_unaffected_by_the_new_path(self, monkeypatch):
        """lang='en' (the default / omitted) must still take the deterministic
        template exactly as before -- this feature only changes what happens
        for a translated request."""
        monkeypatch.setattr(formula_kind, "classify", lambda *a, **kw: self._KIND)
        _stub_llm(monkeypatch, _HI_CONTENT)  # would be used if the gate were wrong
        out = fe.explain_one_rule(_rule(), None, None, error_llm.llm_settings())
        why = _why_section(out["explanation_sections"])
        assert "_i18n_native" not in why
        assert not DEVANAGARI_RE.search(" ".join(why["bullets"]))


# ═════════════════════════════════════════════════════════════════════════
# 2. The four exact reported rule identifiers
# ═════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("rule_name", [
    "cbj54_cal_01", "f013_calc_04", "f013_calc_06", "f013_calc_08",
])
class TestReportedHindiExamples:
    """These four rule names were reported live, with the explanatory body
    ("Why It Failed") staying in English while the section labels around it
    were already Hindi -- exactly the defect this change fixes. Runs each
    rule through the REAL AGGREGATE classification (formula_kind is not
    monkeypatched here), then the full i18n boundary, and checks that BOTH
    the heading (via the existing catalogue) and the body (via native LLM
    phrasing) come back Hindi -- not just one of the two."""

    def test_body_and_heading_are_both_hindi(self, rule_name, monkeypatch):
        _stub_llm(monkeypatch, _HI_CONTENT)
        out = fe.explain_one_rule(
            _rule(rule_name), None, None, error_llm.llm_settings(), lang="hi",
        )
        why = _why_section(out["explanation_sections"])
        assert why.get("_i18n_native") == "hi"
        body = " ".join(why["bullets"])
        assert DEVANAGARI_RE.search(body), (
            f"{rule_name}: explanatory body must be Hindi, got: {body!r}"
        )

    def test_full_pipeline_heading_translated_body_left_untouched(
        self, rule_name, monkeypatch,
    ):
        """End-to-end through translate_outbound with a translator that would
        corrupt any text it is asked to translate -- proving the native-Hindi
        body is never sent to it a second time, while the "Why It Failed"
        heading (a fixed UI label) still comes back Hindi via the catalogue,
        zero model calls."""
        _stub_llm(monkeypatch, _HI_CONTENT)
        out = fe.explain_one_rule(
            _rule(rule_name), None, None, error_llm.llm_settings(), lang="hi",
        )
        # The heading is still English ("Why It Failed") at this point --
        # translate_outbound has not run yet -- so find its index now and look
        # up the SAME position afterwards, since the heading text itself is
        # expected to change to Hindi.
        why_index = out["explanation_sections"].index(
            _why_section(out["explanation_sections"])
        )

        class _CorruptingTranslator:
            name = "corrupting-stub"

            def __init__(self):
                self.calls: list[str] = []

            async def translate(self, text, src, tgt):
                self.calls.append(text)
                return TranslationResult(text="<CORRUPTED>", latency_ms=1.0, ok=True)

        translator = _CorruptingTranslator()
        result = {
            "response_text": "", "options": [],
            "error_details": [out],
        }
        localized = asyncio.run(boundary.translate_outbound(result, "hi", translator))

        why = localized["error_details"][0]["explanation_sections"][why_index]
        body = " ".join(why["bullets"])
        assert "<CORRUPTED>" not in body, (
            "the natively-generated Hindi body must not be re-translated"
        )
        assert DEVANAGARI_RE.search(body)
        # The heading is a fixed catalogue-backed UI label independent of rule
        # kind, and must still be localized normally.
        assert why["heading"] != "Why It Failed"
        assert DEVANAGARI_RE.search(why["heading"])
        # The translator must never have been asked to translate the native
        # Hindi bullet text itself.
        assert not any(_HI_WHY in call or _HI_FIX in call for call in translator.calls)
