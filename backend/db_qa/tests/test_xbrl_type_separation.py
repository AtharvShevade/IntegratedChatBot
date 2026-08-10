"""XBRL vs Non-XBRL separation across every return-scoped question.

The reported symptom was that "what are the XBRL returns filed monthly?" and
"what are the Non-XBRL returns filed monthly?" returned the same combined
list. The cause was general rather than specific to frequency: several
intents extracted no xbrl_type at all, and several handlers read
store.returns() (XBRL only) regardless of what the question asked for.

The contract these tests lock in, from _extract_xbrl_type's own docstring:

    "xbrl"      -> only XBRL returns
    "non_xbrl"  -> only Non-XBRL returns
    None        -> BOTH types

and, critically, that the type filter COMPOSES with the other filters
(frequency, CIMS flag, due days, department scope) rather than replacing
them. The partition assertions below (xbrl + non_xbrl == untyped, and the
two sets being disjoint) are what actually catch a filter that is silently
ignored -- a count assertion alone would not.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from backend.db_qa import access_control, query_handlers as qh
from backend.db_qa.intents.taxonomy import Intent
from backend.db_qa.new_intent_classifier import classify_new
from backend.db_qa.xml_store import XMLStore

PATH_5_5 = Path(r"D:\Repo(new)\DataBase")
_need_5_5 = pytest.mark.skipif(not PATH_5_5.is_dir(), reason="5.5 real data tree not present")

ADMIN_LOGIN = "iris810"


@pytest.fixture(scope="module")
def store():
    return XMLStore(str(PATH_5_5))


def _params(text):
    _intent, params, _tt = classify_new(text)
    return params


def _answer(text, store, login_id=ADMIN_LOGIN):
    intent, params, _ = classify_new(text)
    assert intent is not None, f"unclassified: {text!r}"
    scope = access_control.scope_query({"login_id": login_id}, intent.value, params)
    return intent, qh.dispatch2(intent, scope, params, store)


def _ids(result) -> set[str]:
    """Identify rows by Id, NOT Name: the real data contains two distinct
    returns both named "CRILC" (Id 1039 Monthly, Id 1032 Quarterly), so a
    name-keyed set comparison reports a bogus overlap between two correctly
    disjoint answers. Id is unique and, unlike ReturnId, is disjoint across
    the XBRL and non-XBRL sets."""
    return {str(r.get("Id") or r.get("ReturnName") or r) for r in result.get("records", [])}


@pytest.fixture(scope="module")
def type_ids(store):
    return ({r.get("Id", "") for r in store.returns()},
            {r.get("Id", "") for r in store.non_xbrl_returns()})


# ── the classifier must see the type at all ──────────────────────────────

@pytest.mark.parametrize("text,expected", [
    ("what are the XBRL returns filed monthly?", "xbrl"),
    ("what are the Non-XBRL returns filed monthly?", "non_xbrl"),
    ("which returns are filed monthly?", None),
    ("which non-xbrl returns are filed quarterly?", "non_xbrl"),
    ("show me all the xbrl returns filed annually", "xbrl"),
    ("which XBRL returns are CIMS enabled?", "xbrl"),
    ("which Non-XBRL returns are CIMS enabled?", "non_xbrl"),
    ("which returns are CIMS enabled?", None),
    ("which XBRL returns can i submit?", "xbrl"),
    ("which Non-XBRL returns can i submit?", "non_xbrl"),
    ("which returns can i submit?", None),
])
def test_xbrl_type_is_extracted(text, expected):
    assert _params(text).get("xbrl_type") == expected, text


def test_non_xbrl_is_not_misread_as_xbrl():
    """"\\bxbrl" matches inside "non-xbrl", so any optional-type pattern that
    is not anchored on the non- prefix tags non-XBRL questions as XBRL."""
    for text in ("which non-xbrl returns are filed monthly?",
                 "which non xbrl returns can i submit?",
                 "list the nonxbrl returns filed daily"):
        assert _params(text).get("xbrl_type") == "non_xbrl", text


# ── frequency x type must compose ────────────────────────────────────────

FREQUENCIES = ["monthly", "quarterly", "annually", "half yearly", "daily"]


@_need_5_5
@pytest.mark.parametrize("freq", FREQUENCIES)
def test_frequency_and_type_partition_cleanly(freq, store, type_ids):
    """The reported bug: all three variants returned the same rows."""
    xbrl_ids, nx_ids = type_ids
    _i, x = _answer(f"what are the XBRL returns filed {freq}?", store)
    _i, n = _answer(f"what are the Non-XBRL returns filed {freq}?", store)
    _i, b = _answer(f"what are the returns filed {freq}?", store)

    xn, nn, bn = _ids(x), _ids(n), _ids(b)
    assert xn != nn, f"{freq}: XBRL and Non-XBRL returned identical rows"
    assert not (xn & nn), f"{freq}: a return appears in BOTH type answers"
    assert xn | nn == bn, f"{freq}: typed answers do not partition the untyped one"
    assert xn and nn, f"{freq}: expected both sets to be non-empty in this dataset"

    # ...and the rows really are of the type asked for, not merely different.
    assert all(r.get("Id") in xbrl_ids for r in x["records"]), freq
    assert all(r.get("Id") in nx_ids for r in n["records"]), freq


@_need_5_5
def test_frequency_filter_still_applies_within_a_type(store):
    """Guard against "fixing" the type filter by dropping the frequency one."""
    _i, monthly = _answer("what are the XBRL returns filed monthly?", store)
    _i, quarterly = _answer("what are the XBRL returns filed quarterly?", store)
    assert _ids(monthly) and _ids(quarterly)
    assert not (_ids(monthly) & _ids(quarterly)), \
        "a return cannot be both monthly and quarterly — frequency filter lost"


@_need_5_5
@pytest.mark.parametrize("phrasing", [
    "what are the {t} returns filed monthly?",
    "which {t} returns are filed monthly?",
    "show me all the {t} returns filed every month",
    "list the {t} returns with a monthly frequency",
    "{t} returns filed monthly",
])
def test_alternate_frequency_phrasings_all_respect_the_type(phrasing, store):
    _i, x = _answer(phrasing.format(t="XBRL"), store)
    _i, n = _answer(phrasing.format(t="Non-XBRL"), store)
    assert _ids(x) != _ids(n), phrasing
    assert not (_ids(x) & _ids(n)), phrasing


# ── attribute filters x type ─────────────────────────────────────────────

@_need_5_5
@pytest.mark.parametrize("tpl", [
    "which {t} returns are CIMS enabled?",
    "which {t} returns have no due days configured?",
])
def test_attribute_filters_partition_by_type(tpl, store, type_ids):
    xbrl_ids, nx_ids = type_ids
    _i, x = _answer(tpl.format(t="XBRL"), store)
    _i, n = _answer(tpl.format(t="Non-XBRL"), store)
    _i, b = _answer(tpl.format(t="").replace("  ", " "), store)

    assert _ids(x) | _ids(n) == _ids(b), tpl
    assert not (_ids(x) & _ids(n)), tpl
    assert all(r.get("Id") in xbrl_ids for r in x["records"]), tpl
    assert all(r.get("Id") in nx_ids for r in n["records"]), tpl


@_need_5_5
def test_untyped_list_covers_both_types(store):
    """"no type mentioned -> both". These used to match no rule at all,
    because every RETURN_LIST pattern required the literal word "xbrl"."""
    intent, both = _answer("list all returns", store)
    assert intent == Intent.RETURN_LIST
    assert len(both["records"]) == len(list(store.returns())) + len(list(store.non_xbrl_returns()))


@_need_5_5
def test_typed_list_counts_match_the_data(store):
    _i, x = _answer("list all xbrl returns", store)
    assert len(x["records"]) == len(list(store.returns()))
    _i, n = _answer("list all non-xbrl returns", store)
    assert len(n["records"]) == len(list(store.non_xbrl_returns()))


# ── submittable / department-scoped questions ────────────────────────────

@_need_5_5
def test_submittable_returns_partition_by_type(store):
    _i, x = _answer("which XBRL returns can i submit?", store)
    _i, n = _answer("which Non-XBRL returns can i submit?", store)
    _i, b = _answer("which returns can i submit?", store)
    assert _ids(x) | _ids(n) == _ids(b)
    assert not (_ids(x) & _ids(n))


@_need_5_5
def test_departments_that_can_submit_a_non_xbrl_return(store):
    """A non-XBRL return is listed in a department's NXForms, never Forms —
    checking Forms alone answered "0 departments" for every one of them."""
    nx = next(r for r in store.non_xbrl_returns() if r.get("Name"))
    _i, res = _answer(f"which departments have access to return {nx['Name']}?", store)
    assert res["records"], f"no departments found for non-XBRL return {nx['Name']!r}"


@_need_5_5
def test_untyped_department_access_question_answers_instead_of_returning_zero(store):
    _i, res = _answer("which departments can access returns?", store)
    assert res["records"], "untyped type-level question returned nothing"


# ── labels must not claim the wrong type ─────────────────────────────────

@_need_5_5
@pytest.mark.parametrize("text,must_contain,must_not_contain", [
    ("which Non-XBRL returns are CIMS enabled?", "Non-XBRL", None),
    ("which XBRL returns are CIMS enabled?", "XBRL", "Non-XBRL"),
])
def test_labels_state_the_type_actually_answered(text, must_contain, must_not_contain, store):
    _i, res = _answer(text, store)
    label = res["label"]
    assert must_contain in label, f"{text!r} -> {label!r}"
    if must_not_contain:
        assert must_not_contain not in label, f"{text!r} -> {label!r}"


@_need_5_5
def test_untyped_label_does_not_claim_a_type(store):
    _i, res = _answer("which returns are CIMS enabled?", store)
    assert "XBRL" not in res["label"], res["label"]
