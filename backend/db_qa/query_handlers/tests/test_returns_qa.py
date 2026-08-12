"""XBRL / Non-XBRL Returns Q&A: routing, entity extraction, filter composition.

Three failure classes are pinned here:

  1. Questions that matched no regex rule at all and fell through to the
     generic SQL agent — every one of them a question this taxonomy
     already has an intent for ("which of my returns are SUBMITTED
     quarterly" worked with "filed" and nothing else).
  2. Filters silently dropped when two appear together — "which quarterly
     returns are overdue" answered with all 154 quarterly returns because
     the frequency rule matched first and the overdue half was lost.
  3. The question's own vocabulary captured as the return NAME — "what
     REPORT formats are available for CIMS_ROR" anchored on "report" and
     searched for a return called "formats are available for CIMS_ROR".

Every assertion is XBRL/Non-XBRL symmetric where the question is.
"""
from __future__ import annotations

import pytest

from backend.db_qa.new_intent_classifier import classify_new
from backend.db_qa.intents.taxonomy import Intent


def _classify(q: str):
    intent, params, _target_type = classify_new(q)
    return intent, params


# ── 1. these must never reach the generic SQL agent ──────────────────────

@pytest.mark.parametrize("question", [
    "Which of my returns are filed quarterly?",
    "Which of my returns are submitted quarterly?",
    "Which XBRL returns are accessible to my department?",
    "Which non-XBRL returns are accessible to my department?",
    "Which returns are overdue?",
    "Which monthly returns are overdue?",
    "What is the reporting frequency of CIMS_RAQ?",
    "What is the next due date for CIMS_ROR?",
    "What is the return ID for CIMS_ROR?",
    "Which returns are due in the next 10 days?",
    "Give me all XBRL overdue returns.",
    "Give me all Non-XBRL overdue returns.",
    "how many days are left to submit CIMS_ROR?",
    "how many days do I have to submit CIMS_ROR?",
    "how many days due for return CIMS_ROR for submission",
    "how many days due for submission for return CIMS_ROR",
    "give me reporting calendar for OCB",
    "give me full reporting calendar for CIMS_FormGPB",
    "what report formats are available for CIMS_ROR?",
    "what are my returns submitted quaterly",
    "which returns do I submit quarterly?",
    "which returns are reported quarterly?",
])
def test_question_is_handled_by_db_qa(question):
    intent, _params = _classify(question)
    assert intent is not None, f"{question!r} matched no DB-QA rule"


# ── 2. filed / submitted / reported are one vocabulary ───────────────────

@pytest.mark.parametrize("question, freq", [
    ("Which of my returns are filed quarterly?", "Quarterly"),
    ("Which of my returns are submitted quarterly?", "Quarterly"),
    ("What are my quarterly returns?", "Quarterly"),
    ("Which returns do I submit quarterly?", "Quarterly"),
    ("Which returns do I file quarterly?", "Quarterly"),
    ("Which returns are reported quarterly?", "Quarterly"),
    ("show my quarterly returns", "Quarterly"),
    ("which of my returns are quarterly?", "Quarterly"),
    # the reported typo, in both verb forms
    ("which are my returns filed quaterly", "Quarterly"),
    ("what are my returns submitted quaterly", "Quarterly"),
    ("Which of my returns are filed monthly?", "Monthly"),
    ("Which of my returns are submitted monthly?", "Monthly"),
    ("Which returns do I submit monthly?", "Monthly"),
    # non-XBRL side of the same question
    ("which non xbrl returns are filed quarterly", "Quarterly"),
    ("which non xbrl returns are submitted quarterly", "Quarterly"),
])
def test_frequency_verbs_are_interchangeable(question, freq):
    intent, params = _classify(question)
    assert intent is Intent.RETURNS_BY_FREQUENCY, f"{question!r} -> {intent}"
    assert params["period_name"] == freq


# ── 3. overdue / due-window keeps the frequency AND type filters ─────────

@pytest.mark.parametrize("question, freq, xbrl_type", [
    ("give me list of all monthly overdue returns", "Monthly", None),
    ("which monthly returns are overdue?", "Monthly", None),
    ("which quarterly returns are overdue?", "Quarterly", None),
    ("show overdue monthly returns", "Monthly", None),
    ("which yearly returns are overdue?", "Yearly", None),
    ("which half-yearly returns are overdue?", "HalfYearly", None),
    ("give me all overdue daily returns", "Daily", None),
    ("give me all overdue fortnightly returns", "Fortnightly", None),
    # both filters at once — neither may be dropped
    ("which XBRL monthly returns are overdue?", "Monthly", "xbrl"),
    ("which Non-XBRL quarterly returns are overdue?", "Quarterly", "non_xbrl"),
    ("which of my monthly returns are overdue?", "Monthly", None),
])
def test_overdue_composes_with_frequency_and_type(question, freq, xbrl_type):
    intent, params = _classify(question)
    assert intent is Intent.REPORTS_UPCOMING_IN_RANGE, f"{question!r} -> {intent}"
    assert params.get("query_type") == "overdue"
    assert params.get("period_name") == freq
    assert params.get("xbrl_type") == xbrl_type


@pytest.mark.parametrize("question, xbrl_type", [
    ("give me all overdue returns", None),
    ("are any of my returns overdue?", None),
    ("give me all XBRL overdue returns", "xbrl"),
    ("give me all Non-XBRL overdue returns", "non_xbrl"),
])
def test_unqualified_overdue_has_no_frequency_filter(question, xbrl_type):
    intent, params = _classify(question)
    assert intent is Intent.REPORTS_UPCOMING_IN_RANGE
    assert params.get("query_type") == "overdue"
    assert not params.get("period_name")
    assert params.get("xbrl_type") == xbrl_type


@pytest.mark.parametrize("question, days, freq", [
    ("which of my returns are due in the next 10 days?", 10, None),
    ("Which returns are due within the next 10 days?", 10, None),
    ("What returns are due in the next 30 days?", 30, None),
    ("which quarterly returns are due in the next 30 days?", 30, "Quarterly"),
    ("which XBRL returns are due in the next 10 days?", 10, None),
])
def test_due_window_extracts_n_and_keeps_frequency(question, days, freq):
    from datetime import date, timedelta
    intent, params = _classify(question)
    assert intent is Intent.REPORTS_UPCOMING_IN_RANGE, f"{question!r} -> {intent}"
    expected_to = (date.today() + timedelta(days=days)).strftime("%d-%b-%Y")
    assert params.get("date_to") == expected_to
    assert params.get("period_name") == freq


def test_due_this_month_is_a_window_not_a_monthly_filter():
    """"this month" is a date phrase; reading "month" out of it as a
    frequency filter drops every quarterly/yearly return whose period ends
    inside the window."""
    _intent, params = _classify("How many returns are due this month across the organization?")
    assert not params.get("period_name")
    assert params.get("date_from") and params.get("date_to")


# ── 4. return-name extraction excludes the question's own words ──────────

@pytest.mark.parametrize("question, name", [
    ("what is the return ID for CIMS_ROR?", "CIMS_ROR"),
    ("how many days due for return CIMS_ROR for submission", "CIMS_ROR"),
    ("how many days due for submission for return CIMS_ROR", "CIMS_ROR"),
    ("what report formats are available for CIMS_ROR?", "CIMS_ROR"),
    ("give me reporting calendar for OCB", "OCB"),
    ("give me reporting calendar for return OCB", "OCB"),
    ("give me reporting calendar for LR (Fortnightly)", "LR (Fortnightly)"),
    ("give me full reporting calendar for CIMS_FormGPB", "CIMS_FormGPB"),
    ("what is the reporting frequency for CRILC?", "CRILC"),
    ("what is the reporting frequency for CRILC-SMA2NBFC?", "CRILC-SMA2NBFC"),
    ("how many days until CIMS_FormGPB is due", "CIMS_FormGPB"),
    ("how many days remaining for submission of CIMS_RAQ(Monthly)", "CIMS_RAQ(Monthly)"),
    # the noun is the user's sentence, not part of the name
    ("what is the return ID for returns CIMS?", "CIMS"),
    ("what is the reporting frequency for BSR1(Quarterly)", "BSR1(Quarterly)"),
])
def test_return_name_extraction(question, name):
    _intent, params = _classify(question)
    assert params.get("target_return") == name, f"{question!r} -> {params.get('target_return')!r}"


# ── 5. the current query's return always wins over prior context ─────────

@pytest.mark.parametrize("question, name", [
    ("When should I submit CIMS_ROR next?", "CIMS_ROR"),
    ("When should I submit CIMS_RAQ next?", "CIMS_RAQ"),
    ("When is CIMS_ROR due?", "CIMS_ROR"),
    ("What is the next due date for CIMS_ROR?", "CIMS_ROR"),
    ("When do I need to submit CIMS_ROR?", "CIMS_ROR"),
])
def test_explicit_return_is_extracted_from_the_current_query(question, name):
    intent, params = _classify(question)
    assert intent is Intent.NEXT_REPORTING_DATE, f"{question!r} -> {intent}"
    assert params.get("target_return") == name


@pytest.mark.parametrize("reply", [
    "CIMS_RAQ(Monthly)", "LR (Fortnightly)", "CIMS_ROR", "2", "1",
])
def test_bare_disambiguation_replies_are_not_fresh_questions(reply):
    """agent.decide() treats any message that classifies to its own DB-QA
    intent as a NEW question, dropping the pending disambiguation. A bare
    option reply must therefore keep matching nothing, or picking an
    option from the list would stop working."""
    intent, _params = _classify(reply)
    assert intent is None, f"{reply!r} -> {intent}"


# ── 6. preserved behaviour ───────────────────────────────────────────────

@pytest.mark.parametrize("question, expected", [
    ("which xbrl returns are accessible to department test", Intent.DEPARTMENT_RETURNS),
    ("which XBRL returns are accessible to my department?", Intent.DEPARTMENT_RETURNS),
    ("which non-xbrl returns are accessible to my department", Intent.DEPARTMENT_RETURNS),
    ("what is the return ID of CIMS_RAQ annually", Intent.RETURN_FIELD),
    ("what is the reporting frequency of CIMS_RAQ", Intent.RETURN_FIELD),
    ("what is the next due date for CIMS_ROR", Intent.NEXT_REPORTING_DATE),
    ("can I see the full reporting calendar for CIMS_ROR?", Intent.NEXT_REPORTING_DATE),
    # a non-XBRL return's report format lives on its own row and is
    # answered by the non-XBRL profile, not by the XBRL formats field
    ("What report formats are supported for Non-XBRL return BSR1?",
     Intent.NONXBRL_RETURN_PROFILE),
])
def test_existing_return_questions_still_route_the_same(question, expected):
    intent, _params = _classify(question)
    assert intent is expected, f"{question!r} -> {intent}"


def test_calendar_query_type_is_flagged():
    _intent, params = _classify("give me full reporting calendar for CIMS_FormGPB")
    assert params.get("query_type") == "calendar"
