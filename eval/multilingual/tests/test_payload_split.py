"""Regression tests for the prose/options translation split.

These lock in the fix for the failure measured on the 24-case subset: every
payload >= 3,294 characters returned HTTP 502 from the shared proxy (8 of 8,
across FR/AR/HI), each burning ~246s, because the rendered list of 150+
regulatory report names was being sent to the translation model.

The tests assert the property that matters: report identifiers never reach the
model, and come back byte-for-byte identical because they were re-inserted from
the structured data rather than translated.
"""
from __future__ import annotations

import json

import pytest

from eval.multilingual import payload, pipeline
from eval.multilingual.translator import TranslationResult

# Real names from the deployment's Returns.xml, as they appear in st03.
REAL_OPTIONS = [
    "CIMS_ROS", "CIMS_IRS", "CIMS_RBS", "CIMS_LOU", "CIMS_MTSS", "CIMS_BBSD",
    "CIMS_CB_MIS", "CIMS_RLC", "CIMS_ROP", "CIMS_RLE", "CIMS_CEM",
    "CIMS_FMRD09_FTD", "CIMS_MPD07_MCLR",
]
REGULATORY_IDS = [
    "DBR01", "CIMS_ROR", "CIMS_RAQ(Monthly)",
    "RAQ(Quarterly)", "RAQ(Monthly)", "RAQ(Annually)",
]


def _st03_like(options: list[str]) -> str:
    """The exact shape backend/agent/__init__.py:3316-3320 produces."""
    opts_text = "\n".join(f"{i + 1}. {n}" for i, n in enumerate(options))
    return (
        f"I found {len(options)} matching reports. Which one are you looking for?\n\n"
        f"{opts_text}\n\n"
        "Reply with the number or part of the name."
    )


class _SpyTranslator:
    """Records every string handed to the model."""

    name = "spy"

    def __init__(self, transform=None):
        self.seen: list[str] = []
        self._transform = transform or (lambda t: f"<{t}>")

    def translate(self, text, src, tgt):
        self.seen.append(text)
        return TranslationResult(text=self._transform(text), latency_ms=1.0, model="spy")


# --------------------------------------------------------------------------
# A. Large option lists
# --------------------------------------------------------------------------

def _big_options(n=162):
    return [f"CIMS_REPORT_{i:03d}_LONG_REGULATORY_NAME" for i in range(1, n + 1)]


def test_large_list_is_not_sent_to_the_model():
    options = _big_options()
    text = _st03_like(options)
    assert len(text) > 3294, "fixture must reproduce the failing payload size"

    spy = _SpyTranslator()
    to_translate, blocks, passthrough = payload.split_payload({"response_text": text}, options)
    for name, t in to_translate.items():
        spy.translate(t, "en", "fr")

    sent = "\n".join(spy.seen)
    for name in options:
        assert name not in sent, f"{name} was sent to the translation model"
    assert payload.OPTIONS_PLACEHOLDER in sent


def test_large_payload_shrinks_below_the_502_threshold():
    options = _big_options()
    text = _st03_like(options)
    to_translate, _, _ = payload.split_payload({"response_text": text}, options)
    sent = sum(len(t) for t in to_translate.values())
    assert len(text) >= 3294
    assert sent < 200, f"still sending {sent} chars"
    # Every payload at or above this size 502'd in the 24-case run.
    assert sent < 3294


def test_all_options_return_in_order_byte_identical():
    options = _big_options()
    text = _st03_like(options)
    spy = _SpyTranslator()
    to_translate, blocks, passthrough = payload.split_payload({"response_text": text}, options)
    translated = {k: spy.translate(v, "en", "fr").text for k, v in to_translate.items()}
    out = payload.reassemble(translated, blocks, passthrough)["response_text"]

    for i, name in enumerate(options, 1):
        assert f"{i}. {name}" in out
    positions = [out.index(f"{i}. {n}") for i, n in enumerate(options, 1)]
    assert positions == sorted(positions), "option order changed"


def test_options_only_field_makes_no_model_call_at_all():
    """backend/agent/__init__.py:1244 sets response_text=opts_text with no prose."""
    options = ["ROR", "CIMS_ROR"]
    text = payload.render_options_block(options)
    spy = _SpyTranslator()
    to_translate, blocks, passthrough = payload.split_payload({"response_text": text}, options)
    for v in to_translate.values():
        spy.translate(v, "en", "fr")
    assert spy.seen == [], "a bare option list must not be translated"
    out = payload.reassemble({}, blocks, passthrough)
    assert out["response_text"] == text


# --------------------------------------------------------------------------
# C. Regulatory entity preservation
# --------------------------------------------------------------------------

@pytest.mark.parametrize("identifier", REGULATORY_IDS)
def test_regulatory_identifiers_never_reach_the_model(identifier):
    options = REGULATORY_IDS
    text = _st03_like(options)
    spy = _SpyTranslator()
    to_translate, blocks, passthrough = payload.split_payload({"response_text": text}, options)
    for v in to_translate.values():
        spy.translate(v, "en", "fr")
    assert identifier not in "\n".join(spy.seen)


def test_identifiers_survive_a_hostile_translator():
    """Even a model that mangles everything it is given cannot corrupt an
    identifier, because identifiers are re-inserted from structured data."""
    options = REGULATORY_IDS
    text = _st03_like(options)
    hostile = _SpyTranslator(transform=lambda t: t.replace("RAQ", "DEMANDE").replace(
        "reports", "rapports") + " [MANGLED]")
    to_translate, blocks, passthrough = payload.split_payload({"response_text": text}, options)
    translated = {k: hostile.translate(v, "en", "fr").text for k, v in to_translate.items()}
    out = payload.reassemble(translated, blocks, passthrough)["response_text"]
    for identifier in REGULATORY_IDS:
        assert identifier in out


def test_real_report_names_from_returns_xml_are_preserved():
    text = _st03_like(REAL_OPTIONS)
    spy = _SpyTranslator()
    to_translate, blocks, passthrough = payload.split_payload({"response_text": text}, REAL_OPTIONS)
    translated = {k: spy.translate(v, "en", "fr").text for k, v in to_translate.items()}
    out = payload.reassemble(translated, blocks, passthrough)["response_text"]
    for name in REAL_OPTIONS:
        assert name in out
        assert name not in "\n".join(spy.seen)


# --------------------------------------------------------------------------
# Masking mechanics / safety
# --------------------------------------------------------------------------

def test_prose_is_still_translated():
    options = ["ROR", "CIMS_ROR"]
    text = _st03_like(options)
    to_translate, _, _ = payload.split_payload({"response_text": text}, options)
    sent = to_translate["response_text"]
    assert "matching reports" in sent
    assert "Reply with the number" in sent


def test_no_masking_when_the_list_is_absent():
    text = "Your role is 'Admin User' (id 101)."
    to_translate, blocks, passthrough = payload.split_payload({"response_text": text}, ["RAQ"])
    assert to_translate["response_text"] == text
    assert blocks == {} and passthrough == {}


def test_no_options_means_unchanged_behaviour():
    text = "The report DBR01 is filed on a Quarterly basis."
    to_translate, blocks, passthrough = payload.split_payload({"response_text": text}, [])
    assert to_translate == {"response_text": text}
    assert not blocks and not passthrough


def test_block_is_appended_when_the_model_drops_the_placeholder():
    """A response missing its options is unusable; a slightly oddly-placed list
    is still correct and selectable."""
    block = payload.render_options_block(["RAQ(Monthly)", "RAQ(Annually)"])
    out = payload.restore_options("Le modele a tout supprime.", block)
    assert "RAQ(Monthly)" in out and "RAQ(Annually)" in out


def test_placeholder_variants_are_tolerated():
    block = payload.render_options_block(["DBR01"])
    for variant in ("[[OPTIONS_LIST]]", "[[ OPTIONS_LIST ]]", "[OPTIONS_LIST]",
                    "[[options_list]]"):
        out = payload.restore_options(f"Voici:\n\n{variant}\n\nRepondez.", block)
        assert "1. DBR01" in out
        assert "OPTIONS_LIST" not in out


def test_round_trip_is_byte_identical_with_an_identity_translator():
    options = _big_options(150)
    text = _st03_like(options)
    to_translate, blocks, passthrough = payload.split_payload({"response_text": text}, options)
    identity = {k: v for k, v in to_translate.items()}
    out = payload.reassemble(identity, blocks, passthrough)["response_text"]
    assert out == text


# --------------------------------------------------------------------------
# D/E. Routing-critical terminology and the known failure cases
# --------------------------------------------------------------------------

def test_terminology_fields_are_still_translated_not_masked():
    """dq13 ('filed') and dq09 ('reporting frequency') carry no option list, so
    the split must leave them completely untouched."""
    for text in ("Showing all reports filed between 01-01-2025 and 31-03-2025.",
                 "'DBR01' is filed on a 'Quarterly' basis."):
        to_translate, blocks, passthrough = payload.split_payload({"response_text": text}, [])
        assert to_translate["response_text"] == text
        assert not blocks


def test_translatable_payload_still_selects_the_same_fields():
    """The split must not change which fields are considered translatable."""
    response = {
        "response_text": "hello", "llm_summary": "summary", "db_summary": "db",
        "intent": "get_status", "result_type": "final", "options": ["RAQ"],
        "db_sql": "SELECT 1", "db_rows": [[1]],
    }
    got = pipeline.translatable_payload(response)
    assert set(got) == {"response_text", "llm_summary", "db_summary"}
    assert "options" not in got and "db_sql" not in got


@pytest.mark.parametrize("case_id,options,prose", [
    ("st03", _big_options(162), "I found 162 matching reports."),
    ("cp01", _big_options(158), "I found 158 matching reports."),
    ("sc04", _big_options(150), "Found multiple matching reports."),
])
def test_known_502_cases_no_longer_produce_large_requests(case_id, options, prose):
    text = _st03_like(options)
    to_translate, _, _ = payload.split_payload({"response_text": text}, options)
    sent = sum(len(t) for t in to_translate.values())
    assert sent < 300, f"{case_id} still sends {sent} chars"
