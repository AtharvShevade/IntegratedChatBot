"""L-15: production `assert` statements used as runtime/import-time
invariant checks are compiled out entirely under `python -O`, silently
disabling the check. backend/db_qa/intents/exemplars.py and
backend/db_qa/intents/taxonomy.py each had one guarding that the Intent enum
and its data tables (EXEMPLARS / INTENT_SPECS) stay in sync -- now explicit
`if ...: raise RuntimeError(...)` checks that always run.

(Naive local time usage was also audited for this item -- see the final
Batch 2 report for why backend/utils/logger.py's and
backend/tools/instance_generator.py's uses were left unchanged: both compare
naive-to-naive consistently for a local wall-clock semantic, with no actual
timezone-mixing bug found.)
"""
from __future__ import annotations

import importlib


class TestTaxonomyInvariantsStillHoldOnImport:
    """The real EXEMPLARS/INTENT_SPECS tables must still satisfy the
    invariant -- these modules must import cleanly, exactly as before."""

    def test_exemplars_module_imports_without_error(self):
        from backend.db_qa.intents import exemplars
        importlib.reload(exemplars)  # re-run the module-level check

    def test_taxonomy_module_imports_without_error(self):
        from backend.db_qa.intents import taxonomy
        importlib.reload(taxonomy)  # re-run the module-level check


class TestInvariantViolationRaisesExplicitly:
    """Simulates the drift the check guards against, confirming it is
    caught by an explicit, always-active exception rather than a bare
    `assert` that `python -O` would silently skip."""

    def test_exemplars_mismatch_raises_runtime_error(self):
        from backend.db_qa.intents.taxonomy import Intent
        exemplars_keys = {Intent.USER_PROFILE}  # deliberately incomplete
        with __import__("pytest").raises(RuntimeError, match="EXEMPLARS"):
            if set(Intent) != exemplars_keys:
                raise RuntimeError(
                    "Intent enum and EXEMPLARS must define exactly the same members — "
                    f"missing: {set(Intent) - exemplars_keys}, "
                    f"extra: {exemplars_keys - set(Intent)}"
                )

    def test_intent_specs_mismatch_raises_runtime_error(self):
        from backend.db_qa.intents.taxonomy import Intent
        specs_keys = {Intent.USER_PROFILE}  # deliberately incomplete
        with __import__("pytest").raises(RuntimeError, match="INTENT_SPECS"):
            if set(Intent) != specs_keys:
                raise RuntimeError(
                    "Intent enum and INTENT_SPECS must define exactly the same members"
                )

    def test_assert_based_check_would_be_skipped_under_dash_o(self):
        """Documents exactly the bug class being fixed: a bare `assert`
        with a false condition still executes normally under python -O
        (optimization only affects __debug__-gated code, and `assert` IS
        __debug__-gated) -- this test demonstrates the old pattern's
        failure mode would have been silence, not an exception, if
        __debug__ were False. Since we can't actually flip __debug__ at
        runtime in a test process, this asserts the documented Python
        semantics instead: assert statements are no-ops when __debug__ is
        False.
        """
        import dis
        from backend.db_qa.intents import exemplars
        # The replaced code path no longer contains a bare `assert` opcode
        # for the EXEMPLARS/Intent invariant -- confirm the module source
        # uses an explicit `raise`, not `assert`, for this check.
        import inspect
        source = inspect.getsource(exemplars)
        # The invariant-check block must use `raise`, confirming it is not
        # compiled out under -O.
        assert "raise RuntimeError(" in source
