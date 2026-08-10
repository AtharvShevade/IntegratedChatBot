"""Internal parser output must never be quoted back to the user.

"Department 'has most return' was not found." reads as though the system
looked for a department called "has most return" — it advertises that a
regex mis-fired and sends the user hunting for a name they never typed.

The guard only runs AFTER a lookup has already failed, so the cost of a
wrong call is choosing the wrong one of two error messages; it can never
suppress a real answer. But a false positive still hurts (a genuine typo
would stop being named), so the first test checks it against every real
entity name in the dataset rather than against hand-picked examples.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from backend.db_qa.query_handlers._extraction_guard import (
    UNDERSTAND_FAILURE_MSG,
    looks_like_extraction_garbage,
    not_found_summary,
)
from backend.db_qa.xml_store import XMLStore

PATH_5_5 = Path(r"D:\Repo(new)\DataBase")
_need_5_5 = pytest.mark.skipif(not PATH_5_5.is_dir(), reason="5.5 real data tree not present")


@_need_5_5
def test_no_real_entity_name_is_mistaken_for_parser_output():
    """Every department, role and return name in the real data. An earlier
    version of this guard treated the entity's own type noun as a garbage
    signal and flagged 39 of them — including 'Dept 1' (contains "dept"),
    'Admin User' ("user") and 30-odd returns named 'Form ...'."""
    store = XMLStore(str(PATH_5_5))
    names = [d.get("Name", "") for d in store.departments()]
    names += [r.get("RoleName") or r.get("Name", "") for r in store.roles()]
    names += [r.get("Name", "") for r in store.returns()]
    names += [r.get("Name", "") for r in store.non_xbrl_returns()]
    flagged = sorted({n for n in names if n and looks_like_extraction_garbage(n)})
    assert flagged == [], f"real names would be suppressed: {flagged}"


@pytest.mark.parametrize("value", [
    "has most return",        # the reported bug
    "has least users",
    "are currently active",
    "does my department",
    "in the system",
    "along",
    "ID of department Ghost",
    "",
    "   ",
])
def test_captured_sentence_fragments_are_suppressed(value):
    assert looks_like_extraction_garbage(value)


@pytest.mark.parametrize("value", [
    "Ghost",
    "Dept 1",
    "Dept 99",
    "Admin User",
    # A function word INSIDE a name is fine — only the first position and
    # the all-grammar case count, so a genuine miss on a real-looking name
    # still names it.
    "Bank of India",
    "Form I (SLR of StCB/DCCBs)",
    "Not_in_Use_CIMS_CRILC_NBFC",
])
def test_plausible_names_are_still_reported(value):
    assert not looks_like_extraction_garbage(value)


def test_not_found_summary_is_three_way():
    tpl = "Department '{name}' not found."
    assert not_found_summary(tpl, "Ghost", "empty") == "Department 'Ghost' not found."
    assert not_found_summary(tpl, "", "empty") == "empty"
    assert not_found_summary(tpl, None, "empty") == "empty"
    assert not_found_summary(tpl, "has most return", "empty") == UNDERSTAND_FAILURE_MSG


def test_the_generic_message_does_not_mention_a_search():
    """It must not imply we looked something up and failed — that is the
    impression the reported message gave."""
    low = UNDERSTAND_FAILURE_MSG.lower()
    assert "not found" not in low
    assert "rephrase" in low
