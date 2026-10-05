"""M-17/L-07: DB Q&A dispatch consolidation -- investigated, scoped down to
what was safely achievable.

Investigation finding (full writeup in doc/CRITICAL_FIXES_LOG.md): a complete
taxonomy-level comparison showed every intent the legacy classifier
(backend/db_qa/intent_classifier.py + query_handlers/legacy.py's HANDLERS
table) recognizes has a conceptual equivalent in the new ~48-intent taxonomy
(backend/db_qa/intents/taxonomy.py). BUT empirically, the new classifier's
regex rules (new_intent_classifier.py) do not yet catch several real
phrasings the legacy classifier does -- e.g. "show pending submissions",
"show approved submissions", and return-scoped submission-status questions
all return no match from check_new_taxonomy_intent() today, meaning they
fall through to (and are correctly answered by) the legacy path in real
traffic. Full consolidation (deleting legacy.py / the fallback) was
therefore NOT done -- it would break those real queries.

What WAS done, confirmed safe by this test file:
  1. The new classifier's coupling to the old classifier's PRIVATE helpers
     is removed: both now import from the new shared
     backend.db_qa.utils.extraction_helpers module instead of
     new_intent_classifier.py reaching into intent_classifier.py's
     underscore-prefixed internals.
  2. L-07's duplicate "MY_ROLE_PEER_COUNT" key in legacy.py's HANDLERS dict
     is removed (both occurrences mapped to the identical function --
     confirmed zero behavior change, pure dict-literal cleanup).
  3. L-07's dead `"sys" in dir()` branch in legacy.py's dispatch() is
     replaced with the equivalent, always-true branch it already silently
     fell through to (a real top-level `import sys` makes this
     unconditional) -- confirmed zero behavior change.
  4. The `@trace` monkey-patch in legacy.py is explicitly NOT removed --
     legacy.py's dispatch path remains active and load-bearing (see above),
     so removing debug tracing from it is not part of this fix.
"""
from __future__ import annotations

import pytest


class TestSharedExtractionHelpers:
    """Both classifiers now import the same functions from the same shared
    module -- not just equal values, but the SAME function objects (proving
    no accidental fork/copy happened during the move)."""

    def test_both_classifiers_use_the_identical_function_objects(self):
        from backend.db_qa import intent_classifier, new_intent_classifier
        from backend.db_qa.utils import extraction_helpers

        for name in ("_extract_action", "_extract_after_kw", "_extract_period",
                     "_extract_quoted_or_bracketed", "_self_ref"):
            shared_fn = getattr(extraction_helpers, name)
            assert getattr(intent_classifier, name) is shared_fn
            assert getattr(new_intent_classifier, name) is shared_fn

    def test_both_classifiers_use_the_identical_constant_objects(self):
        from backend.db_qa import intent_classifier, new_intent_classifier
        from backend.db_qa.utils import extraction_helpers

        assert intent_classifier.ACTION_MAP is extraction_helpers.ACTION_MAP
        assert new_intent_classifier.ACTION_MAP is extraction_helpers.ACTION_MAP
        assert intent_classifier.PERIOD_ALIASES is extraction_helpers.PERIOD_ALIASES
        assert new_intent_classifier.PERIOD_ALIASES is extraction_helpers.PERIOD_ALIASES

    def test_new_intent_classifier_no_longer_imports_from_old_intent_classifier(self):
        """The actual M-17 coupling complaint: new_intent_classifier.py must
        not import FROM intent_classifier.py at all any more."""
        import ast
        import backend.db_qa.new_intent_classifier as mod
        tree = ast.parse(open(mod.__file__, encoding="utf-8").read())
        offending = [
            n.module for n in ast.walk(tree)
            if isinstance(n, ast.ImportFrom) and n.module == "backend.db_qa.intent_classifier"
        ]
        assert offending == []

    def test_extraction_behavior_is_unchanged(self):
        """Pins down the actual regex behavior survived the move verbatim."""
        from backend.db_qa.utils.extraction_helpers import (
            _extract_action, _extract_period, _extract_quoted_or_bracketed, _self_ref,
        )
        assert _extract_action("please create a new user") == "HasNew"
        assert _extract_period("run this monthly") == "Monthly"
        assert _extract_quoted_or_bracketed('the user "John Smith"') == "John Smith"
        assert _self_ref("what is my department") is True
        assert _self_ref("what is the finance department") is False


class TestLegacyHandlersDictDuplicateKeyFixed:
    def test_my_role_peer_count_appears_exactly_once_in_source(self):
        import backend.db_qa.query_handlers.legacy as legacy_mod
        source = open(legacy_mod.__file__, encoding="utf-8").read()
        # Only the HANDLERS table assignment should remain -- not counting
        # the one function DEFINITION (`def handle_my_role_peer_count`) or
        # the INTENT_TO_HANDLER table's own (already-single) entry.
        handlers_count = source.count('"MY_ROLE_PEER_COUNT":    handle_my_role_peer_count,')
        assert handlers_count == 1

    def test_handler_still_resolves_correctly(self):
        """Compared by __name__, not object identity -- legacy.py's own
        @trace monkey-patch (pre-existing, untouched) replaces every
        handle_* name in the module namespace with a traced wrapper AFTER
        HANDLERS is built, so HANDLERS itself always holds the original,
        pre-trace function object. dispatch() deliberately re-resolves the
        traced version via getattr() at call time (see
        TestLegacyDeadSysCheckFixed) -- that indirection is intentional and
        unrelated to this fix."""
        from backend.db_qa.query_handlers.legacy import HANDLERS
        assert HANDLERS["MY_ROLE_PEER_COUNT"].__name__ == "handle_my_role_peer_count"


class TestLegacyDeadSysCheckFixed:
    def test_dispatch_still_resolves_a_handler_correctly(self, monkeypatch):
        """The dead branch removal must not change dispatch()'s actual
        behavior -- confirm it still routes to the right handler."""
        from backend.db_qa.query_handlers import legacy
        from unittest.mock import MagicMock

        store = MagicMock()
        called = {}

        def _fake_handler(store, params, user_id, is_admin):
            called["ran"] = True
            return {"intent": "UNKNOWN", "found": False}

        monkeypatch.setitem(legacy.INTENT_TO_HANDLER, "UNKNOWN", _fake_handler)
        monkeypatch.setattr(legacy, "handle_unknown", _fake_handler, raising=False)
        result = legacy.dispatch("UNKNOWN", {}, "u1", "r1", False, store)
        assert called.get("ran") is True
        assert result["intent"] == "UNKNOWN"

    def test_sys_is_a_real_module_level_import(self):
        import backend.db_qa.query_handlers.legacy as legacy_mod
        assert legacy_mod.sys is __import__("sys")


class TestLegacyPathStillLoadBearing:
    """Documents WHY full M-17 consolidation was not done -- these phrasings
    are real, supported DB Q&A questions that only the legacy classifier
    currently recognizes. If a future change to new_intent_classifier.py
    makes these also match there, this test should be revisited (not just
    deleted) as evidence the legacy fallback may finally be safe to retire
    for these cases."""

    @pytest.mark.parametrize("question", [
        "show pending submissions",
        "show approved submissions",
    ])
    def test_new_classifier_does_not_yet_match_these_legacy_covered_questions(self, question):
        from backend.agent.db_qa_router import check_new_taxonomy_intent
        new_intent, _params = check_new_taxonomy_intent(question)
        assert new_intent is None, (
            f"new_intent_classifier now matches {question!r} -- if this is "
            "intentional, the legacy fallback may be safe to retire for this "
            "case; update this test's expectation deliberately, don't just delete it."
        )

    @pytest.mark.parametrize("question,expected_old_intent", [
        ("show pending submissions", "SUBMISSION_PENDING"),
        ("show approved submissions", "SUBMISSION_APPROVED"),
    ])
    def test_legacy_classifier_still_correctly_answers_them(self, question, expected_old_intent):
        from backend.db_qa.intent_classifier import classify
        intent, _params = classify(question)
        assert intent == expected_old_intent
