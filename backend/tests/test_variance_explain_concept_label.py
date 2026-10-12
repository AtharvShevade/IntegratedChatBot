"""A model-written explanation line must still name the concept by its taxonomy
label. 'Exposures in DM000012 decreased ...' is numerically fine but no longer
says which figure moved, so validate_and_merge falls back to the template."""
from backend.tools.variance_explain import template_sentence, validate_and_merge

LABEL = "Loans And Advances - Private Sector SMEs"


def _fact(concept_label=LABEL):
    return {
        "id": 1, "concept": "PE001504", "context_key": "dim=DM000012",
        "dimension": "DM000012",
        "business_name": f"{LABEL} — DM000012" if concept_label else "PE001504 — DM000012",
        "concept_label": concept_label,
        "unit": "", "val_a": 49507.0, "val_b": 4950700.0,
        "fmt_a": "49,507", "fmt_b": "4,950,700", "pct_change": -99.0,
        "fmt_pct": "-99.0%", "direction": "decreased", "zero_baseline": False,
    }


def test_template_names_the_concept_by_label():
    assert LABEL in template_sentence(_fact())


def test_llm_line_without_the_label_falls_back_to_template():
    f = _fact()
    raw = "[1] Exposures in DM000012 decreased from 4,950,700 to 49,507 (-99.0%)."
    out, from_llm = validate_and_merge(raw, [f])
    assert from_llm == 0
    assert out == [template_sentence(f)]


def test_llm_line_that_keeps_the_label_is_used():
    f = _fact()
    raw = f"[1] {LABEL} fell from 4,950,700 to 49,507, a drop of 99.0%."
    out, from_llm = validate_and_merge(raw, [f])
    assert from_llm == 1
    assert LABEL in out[0]


def test_no_label_means_no_extra_constraint():
    f = _fact(concept_label="")
    raw = "[1] Exposures in DM000012 decreased from 4,950,700 to 49,507 (-99.0%)."
    out, from_llm = validate_and_merge(raw, [f])
    assert from_llm == 1
