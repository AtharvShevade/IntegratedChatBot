"""M-19: four `except Exception` blocks swallowed real errors with zero
logging, making a genuine bug indistinguishable from an expected/empty
result. Each now logs (warning/debug, with exc_info=True) before falling
back to its existing (unchanged) default -- behavior is identical, only
observability changed.
"""
from __future__ import annotations

import logging

import backend.tools.formula_error as fe
import backend.tools.variance_explain as ve


class TestFormulaErrorTaxonomyImportFailure:
    def test_import_failure_logs_a_warning_and_still_returns_empty_dict(self, monkeypatch, caplog):
        import builtins
        real_import = builtins.__import__

        def _boom(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "backend.tools" and fromlist and "taxonomy_lookup" in fromlist:
                raise ImportError("simulated import failure")
            return real_import(name, globals, locals, fromlist, level)

        monkeypatch.setattr(builtins, "__import__", _boom)
        with caplog.at_level(logging.WARNING):
            result = fe._json_variable_map({"by_assertion_id": {}}, "rule1")
        assert result == {}
        matching = [r for r in caplog.records if "taxonomy_lookup import failed" in r.message]
        assert matching
        assert matching[0].exc_info is not None


class TestVarianceExplainMovementScoreFailure:
    def test_movement_of_failure_logs_and_returns_none(self, monkeypatch, caplog):
        def _boom(row):
            raise RuntimeError("simulated scoring failure")

        monkeypatch.setattr("backend.tools.xbrl_importance._movement_score", _boom)
        with caplog.at_level(logging.DEBUG):
            result = ve._movement_of({"concept": "TestConcept"})
        assert result is None
        matching = [r for r in caplog.records if "movement_score unavailable" in r.message]
        assert matching
        assert matching[0].exc_info is not None
