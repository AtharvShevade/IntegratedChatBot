"""Regression tests from the ROLE_ACCESS gap-analysis pass.

Every case here is a phrasing that a real user would plausibly type and that
the classifier got wrong before this pass. They are grouped by root cause
rather than by intent, because most of the bugs were one cause producing
several unrelated-looking symptoms.

The module assertions deliberately cross-check against the REAL OptionName
values in XML_RoleAccess (see test_every_module_synonym_matches_real_data):
an extracted module value that is not a substring of some real OptionName
can never match anything in the handlers, which filter with
`module.lower() in OptionName.lower()`.
"""
from __future__ import annotations

import pytest

from backend.db_qa.intents.taxonomy import Intent
from backend.db_qa.new_intent_classifier import _MODULE_SYNONYMS, classify_new
from backend.db_qa.query_handlers.role_handlers import _ACTION_MAP, _module_matches
from backend.db_qa.xml_store import XMLStore


def _c(q):
    intent, params, _tt = classify_new(q)
    return intent, params


@pytest.fixture(scope="module")
def real_option_names() -> list[str]:
    store = XMLStore()
    return sorted({store.enrich_role_access(a).get("OptionName", "")
                   for a in store.role_access()} - {""})


# ── module synonyms must correspond to data that actually exists ─────────

def test_every_module_synonym_matches_real_data(real_option_names):
    """A canonical value matching no real OptionName is dead config: the
    handlers' substring filter can never select anything with it, so the
    question silently answers against every module instead."""
    dead = [canon for _pat, canon in _MODULE_SYNONYMS
            if not [n for n in real_option_names if _module_matches(canon, n)]]
    assert dead == [], f"module synonyms matching no real OptionName: {dead}"


@pytest.mark.parametrize("query,expected_module", [
    # "Cross Validation" is spelled with a SPACE in the data; the synonym
    # used to be cross-?validation (hyphen only) and matched neither the
    # data's spelling nor the way users type it.
    ("can i run cross validation", "cross validation"),
    ("can i run cross-validation", "cross validation"),
    # These three *Log modules exist in XML_RoleAccess but had no synonym at
    # all, so the questions resolved to module=None.
    ("can i see the data audit log", "audit log"),
    ("can i view the audit log", "audit log"),
    ("can i view the user activity log", "activity log"),
    ("who can view the return validation log", "validation log"),
    # NX FileUpload had no synonym, so this fell through to the bare
    # "roles?" catch-all and resolved to the "Roles" module.
    ("which roles can upload non-xbrl files", "fileupload"),
])
def test_module_extraction_for_real_modules(query, expected_module, real_option_names):
    _intent, params = _c(query)
    assert params.get("module") == expected_module, query
    assert [n for n in real_option_names if _module_matches(expected_module, n)], expected_module


# ── XBRL / non-XBRL separation ───────────────────────────────────────────

@pytest.mark.parametrize("query,expected_module", [
    ("who can access the non-xbrl query builder", "non-xbrl query"),
    ("who can access the xbrl query builder", "xbrl query"),
    ("can i generate non-xbrl", "non-xbrl generation"),
    ("can i generate xbrl", "xbrl generation"),
    ("can i view non-xbrl reports", "non-xbrl report"),
    ("can i view xbrl reports", "xbrl report"),
])
def test_xbrl_and_non_xbrl_modules_do_not_cross_resolve(query, expected_module):
    """"-" is a non-word character, so `\\bxbrl` matches inside "non-xbrl".
    Every non-XBRL synonym must therefore be ordered ahead of its XBRL
    counterpart; query-builder was not, and claimed both."""
    _intent, params = _c(query)
    assert params.get("module") == expected_module, query


@pytest.mark.parametrize("module,forbidden", [
    ("xbrl generation", "Non-XBRL Generation"),
    ("xbrl report", "Non-XBRL Reports"),
    ("xbrl query", "Non-XBRL Query Builder"),
])
def test_xbrl_module_does_not_select_non_xbrl_option(module, forbidden):
    """Same substring hazard one layer down: even with the right canonical
    value, a plain `in` test in the handler selected the Non-XBRL row too."""
    assert not _module_matches(module, forbidden)


def test_non_xbrl_module_still_selects_its_own_option():
    assert _module_matches("non-xbrl generation", "Non-XBRL Generation")
    assert _module_matches("non-xbrl report", "Non-XBRL Reports")


def test_generic_module_synonyms_keep_their_intended_breadth(real_option_names):
    """The carve-out above must not narrow the deliberately-broad ones."""
    reports = [n for n in real_option_names if _module_matches("report", n)]
    assert "XBRL Report" in reports and "Non-XBRL Reports" in reports and "Report Log" in reports


# ── an action verb is not a role name ────────────────────────────────────

@pytest.mark.parametrize("query,action", [
    ("can i edit roles", "edit"),
    ("can i modify roles", "modify"),
])
def test_verb_before_roles_is_not_captured_as_a_role_name(query, action):
    """"Roles" is itself a module, so these are ordinary permission checks.
    Capturing the verb as target_role both produced "Role 'edit' was not
    found" and suppressed module extraction (the "role" synonym is skipped
    whenever target_role is set)."""
    intent, params = _c(query)
    assert intent == Intent.PERMISSION_CHECK
    assert "target_role" not in params, params
    assert params.get("action") == action
    assert params.get("module") == "role"


def test_which_roles_can_i_create_still_extracts_the_role_module():
    """Guard for the above: here "roles" IS the object, and must stay a
    module reference."""
    _intent, params = _c("which roles can i create")
    assert params.get("module") == "role"


# ── verb coverage parity between the two permission rules ────────────────

@pytest.mark.parametrize("verb", ["create", "edit", "view", "read", "approve",
                                   "update", "modify", "generate", "disable"])
def test_first_and_third_person_phrasings_both_classify(verb):
    """"can i <verb> X" and "who can <verb> X" ask the same thing from
    opposite ends; a verb accepted by one rule must be accepted by the
    other, or the same action is answerable in one voice and not the other."""
    first, _ = _c(f"can i {verb} bank details")
    third, _ = _c(f"who can {verb} bank details")
    assert first == Intent.PERMISSION_CHECK, verb
    assert third == Intent.ROLES_WITH_PERMISSION, verb


@pytest.mark.parametrize("verb,attr", [("generate", "HasNew"), ("disable", "HasEdit")])
def test_unambiguous_verbs_resolve_without_the_llm(verb, attr):
    """These two used to reach the handler with action=None and were resolved
    only by llm_service.normalize_action_word -- a live round trip measured
    at 19-26s (it retries twice) that returns nothing when the proxy is
    unreachable, so the user waited ~26s to be told the request wasn't
    understood."""
    _intent, params = _c(f"who can {verb} bank details")
    assert params.get("action") == verb
    assert _ACTION_MAP[verb] == attr


# ── a named role must not be silently discarded ──────────────────────────

@pytest.mark.parametrize("query,role", [
    ("what modules can the admin role create", "admin"),
    ("can the checker role approve data preparation", "checker"),
    # role BEFORE the name
    ("can role Tester view the audit log", "Tester"),
    # "can" BETWEEN the role and the verb
    ("the checker role can approve what", "checker"),
])
def test_named_role_with_a_verb_is_role_scoped(query, role):
    """ROLES_WITH_PERMISSION answers "which roles system-wide can do X" and
    never reads target_role, so a question naming one role that lands there
    has its subject silently dropped."""
    intent, params = _c(query)
    assert intent == Intent.PERMISSION_CHECK, query
    assert params.get("target_role") == role, query


@pytest.mark.parametrize("query", [
    "which roles can create users",
    "who can approve bank details",
    "which roles have full access to the balance sheet",
])
def test_system_wide_phrasings_are_not_captured_by_the_role_scoped_rules(query):
    """Guard for the above: allowing an optional "can" between the role noun
    and the verb must not swallow the genuinely system-wide framing."""
    intent, _params = _c(query)
    assert intent == Intent.ROLES_WITH_PERMISSION, query


@pytest.mark.parametrize("query,role,module", [
    ("does role Auditor have access to providers", "Auditor", "provider"),
    ("does the tester role have access to cross validation", "tester", "cross validation"),
])
def test_named_role_asking_about_one_module(query, role, module):
    intent, params = _c(query)
    assert intent == Intent.ROLE_MODULE_ACCESS, query
    assert params.get("target_role") == role
    assert params.get("module") == module


# ── self-reference must not be answered as a system-wide question ────────

@pytest.mark.parametrize("query", [
    "do i have access to the balance sheet",
    "do i have permission to edit roles",
])
def test_first_person_permission_questions_stay_self_scoped(query):
    """These landed on ROLE_MODULE_ACCESS / ROLE_PROFILE with no target_role
    and target_type="role", so the handler answered "which roles can access
    X" (or gave the caller's role name) to someone asking about themselves."""
    intent, params = _c(query)
    assert intent == Intent.PERMISSION_CHECK, query
    assert params.get("target_type") == "self", query
