"""Formula / dimension error card localization.

The card is a MIX, and the split is the whole point:

  DETERMINISTIC  section headings ("Where", "Rule", "Values", "Calculation",
                 "Fix"), matrix column headers ("Item", "Expected", "You
                 reported"), the "⚙ Formula Error — <rule>" headline, the batch
                 header, and the recurring sentences the renderers emit.
                 Catalogue -> ZERO model calls.

  LLM-AUTHORED   the headline sentence and the fix steps, written per rule.
                 Generated in English unchanged, then translated ONCE.

  DATA           the rule name, concept labels, expected/actual figures.
                 Never translated, never sent to the model.

Nothing in formula_error.py / error_card.py / dimension_error.py changes.
"""
from __future__ import annotations

import asyncio

import pytest

from backend.i18n import boundary, catalogue
from backend.i18n.translator import TranslationResult

TARGETS = ("fr", "ar", "hi")

RULE = "TermDeposit-WeightedAverageInterestRateByClassificationOfTermDeposits"
RULE2 = "LR-PartA1B1B2AndC-MismatchAsPercentageToOutflows"

# Deterministic UI strings the pipeline emits, with their source.
DETERMINISTIC = {
    "Where": "errcard.where",                       # error_card.py:98
    "Rule": "errcard.rule",                          # error_card.py:104
    "Fix": "errcard.fix",                            # error_card.py:137
    "Values": "errcard.values",                      # formula_error.py:2990
    "Item": "errcard.item",                          # formula_error.py:2991
    "Expected": "errcard.expected",                  # formula_error.py:2991
    "You reported": "errcard.youReported",           # formula_error.py:2991
    "Calculation": "errcard.calculation",            # formula_error.py:3001
    "Validation rule": "errcard.validationRule",     # formula_error.py:2843
    "Technical details": "errcard.technicalDetails", # error_card.py:215
    "Difference": "errcard.difference",              # formula_error.py:1810
}

# Data that must survive byte-for-byte and never reach the model.
PROTECTED = [RULE, RULE2, "0.0001", "0.0599", "0.06", "CIMS_ROR", "R009",
             "356,802,987,000"]


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


def _card():
    """The exact v2 shape formula_error.py:3311-3319 builds."""
    return {
        "response_text": "Schedule confirmed:",
        "options": [],
        "error_details": [{
            "rule_name": RULE,
            "message": "assertion unsatisfied",
            "explanation": f"⚙ Formula Error — {RULE}",
            "explanation_sections": [
                {"kind": "headline",
                 "text": "Weighted average interest rate is 0.0001 higher than "
                         "the calculated weighted average."},
                {"kind": "locator", "heading": "Where",
                 "items": [{"label": "Validation rule", "value": RULE}]},
                {"kind": "matrix", "heading": "Values",
                 "columns": {"label": "Item", "expected": "Expected",
                             "actual": "You reported"},
                 "rows": [{"label": "Weighted average interest rate 1",
                           "expected": "0.0599", "actual": "0.06",
                           "status": "bad",
                           "note": "over by 0.0001, after rounding"}]},
                {"kind": "points", "heading": "Calculation",
                 "bullets": [
                     "Rounded to the nearest 0.0001: 0.0599 expected, 0.06 reported.",
                     "This rule failed for 31 reported items; the first is shown above.",
                 ]},
                {"kind": "fix", "heading": "Fix",
                 "steps": ["Check the amounts and the rates used to calculate "
                           "the weighted average."]},
            ],
        }],
    }


def _out(lang, translator=None, result=None):
    return asyncio.run(boundary.translate_outbound(
        result if result is not None else _card(), lang, translator or Spy()))


# ---------------------------------------------------------------------------
# 1. Deterministic UI -> catalogue, zero model calls
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("english,key", sorted(DETERMINISTIC.items()))
@pytest.mark.parametrize("lang", TARGETS)
def test_deterministic_label_resolves_from_the_catalogue(english, key, lang):
    out = catalogue.resolve(english, lang)
    assert out is not None, f"{english!r} is not catalogued"
    assert out == catalogue.load(lang)[key]


@pytest.mark.parametrize("english", [
    f"⚙ Formula Error — {RULE}",
    f"⚙ Formula Error — {RULE2}",
    "⚙ Formula Errors — showing 1-3 of 5",
    "⚙ Schema Errors — showing 4-6 of 12",
    "⚙ Dimension Errors — showing 2",
    "This rule failed for 31 reported items; the first is shown above.",
    "Rounded to the nearest 0.0001: 0.0599 expected, 0.06 reported.",
    "over by 0.0001, after rounding",
])
@pytest.mark.parametrize("lang", TARGETS)
def test_deterministic_template_resolves_and_keeps_its_values(english, lang):
    out = catalogue.resolve(english, lang)
    assert out is not None, f"{english!r} is not catalogued"
    assert out != english, f"{english!r} came back English in {lang}"
    _, values = catalogue.structure(english)
    for value in values:
        assert value in out, f"{lang}: lost {value!r} from {english!r}"


@pytest.mark.parametrize("lang", TARGETS)
def test_card_headings_and_columns_cost_no_model_call(lang):
    spy = Spy()
    out = _out(lang, spy)
    sections = out["error_details"][0]["explanation_sections"]

    assert sections[1]["heading"] == catalogue.resolve("Where", lang)
    assert sections[2]["heading"] == catalogue.resolve("Values", lang)
    assert sections[3]["heading"] == catalogue.resolve("Calculation", lang)
    assert sections[4]["heading"] == catalogue.resolve("Fix", lang)
    columns = sections[2]["columns"]
    assert columns["label"] == catalogue.resolve("Item", lang)
    assert columns["expected"] == catalogue.resolve("Expected", lang)
    assert columns["actual"] == catalogue.resolve("You reported", lang)
    assert sections[1]["items"][0]["label"] == catalogue.resolve("Validation rule", lang)

    for phrase in ("Where", "Values", "Calculation", "Item", "Expected",
                   "You reported", "Validation rule"):
        assert phrase not in spy.sent, f"{phrase!r} was sent to the model"


@pytest.mark.parametrize("lang", TARGETS)
def test_only_genuinely_variable_prose_reaches_the_model(lang):
    """The headline sentence and the fix step are written per rule; everything
    else in the card is a template."""
    spy = Spy()
    out = _out(lang, spy)
    meta = out["data"]["i18n"]["outbound"]
    assert meta["calls"] == 2, f"{meta['calls']} calls: {spy.seen}"
    assert len(meta["catalogued"]) >= 12
    assert meta["entities_lost"] == 0


# ---------------------------------------------------------------------------
# 2. Data and technical identifiers
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("lang", TARGETS)
def test_rule_name_survives_as_one_token(lang):
    """A hyphenated CamelCase rule name must mask as ONE entity, or the
    headline template could only match names with the same hyphen count."""
    from backend.i18n import protect
    for name in (RULE, RULE2):
        masked, tokens = protect.mask_entities(name)
        assert len(tokens) == 1 and masked.strip() == "[[E1]]"
    out = _out(lang)
    assert RULE in out["error_details"][0]["explanation"]


@pytest.mark.parametrize("lang", TARGETS)
def test_protected_values_never_reach_the_model(lang):
    spy = Spy()
    _out(lang, spy)
    for value in (RULE, "0.0599", "0.06", "0.0001"):
        assert value not in spy.sent, f"{value!r} was sent to the model"


@pytest.mark.parametrize("lang", TARGETS)
def test_matrix_row_data_is_untouched(lang):
    """rows[].label/expected/actual are the XBRL concept label and its figures
    -- data, even though they sit under a translated 'Item' header."""
    row = _out(lang)["error_details"][0]["explanation_sections"][2]["rows"][0]
    assert row["label"] == "Weighted average interest rate 1"
    assert row["expected"] == "0.0599"
    assert row["actual"] == "0.06"
    assert row["status"] == "bad"
    # The explanatory NOTE beside them is prose and is localized.
    assert row["note"] != "over by 0.0001, after rounding"
    assert "0.0001" in row["note"]


@pytest.mark.parametrize("lang", TARGETS)
def test_hostile_translator_cannot_corrupt_the_card(lang):
    class Hostile:
        name = "hostile"

        async def translate(self, text, src, tgt):
            return TranslationResult(
                text=text.replace("0.0", "9.9").replace("Term", "Terme").upper(),
                latency_ms=1.0, ok=True)

    blob = str(_out(lang, Hostile()))
    for value in (RULE, "0.0599", "0.06"):
        assert value in blob, f"hostile model corrupted {value!r}"


# ---------------------------------------------------------------------------
# 3. English unchanged, no double translation
# ---------------------------------------------------------------------------

def test_english_returns_the_identical_object():
    class Boom:
        name = "boom"

        async def translate(self, text, src, tgt):  # pragma: no cover
            raise AssertionError("model called on the English path")

    original = _card()
    assert asyncio.run(boundary.translate_outbound(original, "en", Boom())) is original


def test_the_pipelines_card_is_never_mutated():
    import copy
    original = _card()
    snapshot = copy.deepcopy(original)
    _out("fr", Spy(), original)
    assert original == snapshot


@pytest.mark.parametrize("lang", TARGETS)
def test_nothing_is_translated_twice(lang):
    spy = Spy()
    out = _out(lang, spy)
    assert len(spy.seen) == len(set(spy.seen)), f"duplicates: {spy.seen}"
    localized_heading = out["error_details"][0]["explanation_sections"][1]["heading"]
    assert localized_heading not in spy.sent, "a catalogue result reached the model"
    for text in spy.seen:
        assert not text.startswith(f"<{lang}>")


@pytest.mark.parametrize("lang,lo,hi", [("ar", 0x0600, 0x06FF), ("hi", 0x0900, 0x097F)])
def test_target_script_is_present(lang, lo, hi):
    out = _out(lang)
    sections = out["error_details"][0]["explanation_sections"]
    for text in (sections[1]["heading"], sections[2]["heading"],
                 sections[2]["columns"]["label"], sections[4]["heading"]):
        assert any(lo <= ord(ch) <= hi for ch in text), (
            f"{text!r} contains no {lang} script"
        )


def test_nested_walker_covers_the_whole_card_schema():
    """Every prose slot in error_card.py's schema is extracted; every data
    slot is left alone."""
    keys = set(boundary._nested_payload(_card())[0])
    base = "error_details.0.explanation_sections"
    assert f"{base}.0.text" in keys                       # headline
    assert f"{base}.1.heading" in keys                    # locator
    assert f"{base}.1.items.0.label" in keys
    assert f"{base}.2.columns.label" in keys              # matrix headers
    assert f"{base}.2.columns.expected" in keys
    assert f"{base}.2.columns.actual" in keys
    assert f"{base}.2.rows.0.note" in keys                # row note
    assert f"{base}.3.bullets.0" in keys                  # points
    assert f"{base}.4.steps.0" in keys                    # fix
    # Data slots must NOT be extracted.
    for data_key in (f"{base}.1.items.0.value", f"{base}.2.rows.0.label",
                     f"{base}.2.rows.0.expected", f"{base}.2.rows.0.actual"):
        assert data_key not in keys, f"{data_key} is DATA and must not translate"


def test_details_kind_recurses_into_nested_sections():
    """A v2 `details` section carries whole v1 sections inside it."""
    card = _card()
    card["error_details"][0]["explanation_sections"].append({
        "kind": "details", "heading": "Technical details",
        "sections": [{"kind": "rule", "heading": "Rule", "text": "inner prose"}],
    })
    keys = set(boundary._nested_payload(card)[0])
    assert f"error_details.0.explanation_sections.5.sections.0.heading" in keys
    # A `rule` nested inside `details` is the VALIDATOR'S OWN message -- a
    # formula expression, not a sentence. Its heading is a UI label and is
    # translated; its text is data and is kept byte-identical, exactly like
    # error_details[].message.
    assert f"error_details.0.explanation_sections.5.sections.0.text" not in keys
    out = _out("fr", Spy(), card)
    inner = out["error_details"][0]["explanation_sections"][5]["sections"][0]
    assert inner["heading"] == catalogue.resolve("Rule", "fr")
    assert inner["text"] == "inner prose"


def test_top_level_rule_text_is_still_prose_and_is_translated():
    """Only the nesting makes it raw: a top-level `rule` section carries the
    plain-English restatement of the rule, which must localize."""
    card = _card()
    card["error_details"][0]["explanation_sections"].append(
        {"kind": "rule", "heading": "Rule", "text": "Rate must equal the average."}
    )
    keys = set(boundary._nested_payload(card)[0])
    assert "error_details.0.explanation_sections.5.text" in keys


def test_mono_text_is_never_translated():
    """error_card.py:104 documents mono as a raw identifier; the UI renders it
    inside <code>."""
    card = _card()
    card["error_details"][0]["explanation_sections"].append(
        {"kind": "rule", "heading": "Rule", "text": "Sum(A) > B", "mono": True}
    )
    keys = set(boundary._nested_payload(card)[0])
    assert "error_details.0.explanation_sections.5.heading" in keys
    assert "error_details.0.explanation_sections.5.text" not in keys


# ---------------------------------------------------------------------------
# Concept labels are DATA, and the prose around them is a catalogue template.
#
# The card publishes the concept labels it used in each section's `terms`
# (error_card.attach_emphasis). Masking those does two things at once: the
# labels survive byte-identical -- a translated "Weighted average interest
# rate" sends the user looking for a field the application does not have --
# and the sentence collapses to a fixed shape the catalogue can resolve with
# no model call at all.
# ---------------------------------------------------------------------------

def _terms_card(text, terms, kind="fix"):
    section = {"kind": kind, "heading": "Fix", "terms": list(terms)}
    section["steps" if kind == "fix" else "bullets"] = [text]
    return {"response_text": "x", "options": [],
            "error_details": [{"rule_name": "R", "explanation_sections": [section]}]}


def test_concept_labels_are_collected_from_the_sections_terms():
    card = _terms_card("Check Weighted average interest rate now.",
                       ["Weighted average interest rate"])
    _fields, terms = boundary._nested_payload(card)
    key = "error_details.0.explanation_sections.0.steps.0"
    assert terms[key] == ("Weighted average interest rate",)


@pytest.mark.parametrize("lang", ["fr", "ar", "hi"])
def test_the_fix_sentence_costs_no_model_call_and_keeps_the_concept(lang):
    """THE REGRESSION: this sentence is an f-string template
    (formula_error.py:1462), so it must come from the catalogue, and the
    concept label inside it must not be translated."""
    label = "Weighted average interest rate"
    english = (f"Check the amounts and the rates used to calculate {label} in the "
               "source data, correct whichever is wrong, then regenerate and "
               "revalidate the return.")
    spy = Spy()
    out = _out(lang, spy, _terms_card(english, [label]))
    step = out["error_details"][0]["explanation_sections"][0]["steps"][0]
    # The fixture's own response_text is the only thing that may be sent;
    # the fix sentence itself must be resolved from the catalogue.
    assert not any("calculate" in sent for sent in spy.seen), spy.seen
    assert step != english, "the sentence must be localized"
    assert label in step, "the concept label must survive byte-identical"


@pytest.mark.parametrize("lang", ["fr", "ar", "hi"])
def test_variable_length_operand_list_matches_one_template(lang):
    """The operand list changes length per rule. Masked as ONE token, every
    arity resolves from the SAME catalogue entry."""
    lhs = "Weighted average interest rate"
    operands = ["Amount outstanding term deposit 1", "Amount outstanding term deposit 2",
                "Amount outstanding term deposit 3"]
    for count in (1, 2, 3):
        joined = operands[0] if count == 1 else (
            ", ".join(operands[:count - 1]) + ", and " + operands[count - 1])
        english = (f"Check {lhs} and the values it is calculated from ({joined}) in the "
                   "source data — the reported value does not match the one calculated "
                   "from them. Then regenerate and revalidate the return.")
        spy = Spy()
        out = _out(lang, spy, _terms_card(english, [lhs] + operands))
        step = out["error_details"][0]["explanation_sections"][0]["steps"][0]
        assert not any("calculated from" in sent for sent in spy.seen), spy.seen
        assert step != english
        for operand in operands[:count]:
            assert operand in step, f"{operand!r} lost at arity {count}"


def test_a_short_label_stem_is_not_protected():
    """Stems are only added at three words or more. A one-word stem would
    match ordinary prose -- including catalogue headings, which would then
    look like pure data and silently stop being translated."""
    from backend.i18n import protect
    masked, _ = protect.mask_entities("The Difference is large.", extra=["Difference 1"])
    assert "Difference" in masked, "a one-word stem must not be masked"
    masked, tokens = protect.mask_entities(
        "using each Amount outstanding term deposit as its weight",
        extra=["Amount outstanding term deposit 1"])
    assert "Amount outstanding term deposit" in tokens.values(), "4-word stem must mask"
