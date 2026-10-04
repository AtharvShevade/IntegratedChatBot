"""Regression tests for the H-06 fix (doc/CRITICAL_FIXES_LOG.md): background
work started via loop.run_in_executor() (which does NOT copy contextvars
into its worker thread) or a nested ThreadPoolExecutor (same gap) could
silently read the wrong tenant's repo root under APP_VERSION=6.0, since
config._active_root() resolves from a contextvar set by
version_config.repo_scope() for the calling request.

Covers the three fixed call sites:
  1. backend/agent/error_explanation.py's explain_category_for_report()
     (loop.run_in_executor -> asyncio.to_thread)
  2. backend/tools/report_lookup.py's explain_formula_errors() (inner
     ThreadPoolExecutor -> contextvars.copy_context().run(...))
  3. backend/tools/formula_error_generic.py's explain_generic_formula_errors()
     (same fix as #2)

Each test sets a distinct tenant_id via version_config.repo_scope() in the
"request" thread, then asserts the background work observes THAT SAME
tenant_id via version_config.get_active_tenant_id() -- proving context
actually crossed the thread boundary, not just that the code compiles.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend import version_config


class TestErrorExplanationContextPropagation:
    def test_tenant_context_reaches_the_background_thread(self, monkeypatch, tmp_path):
        from backend import config as config_module
        import backend.agent.error_explanation as ee

        base = tmp_path / "Instance"
        form_dir = base / "4046"
        form_dir.mkdir(parents=True)
        (form_dir / "errors.xml").write_text("<x/>", encoding="utf-8")
        monkeypatch.setattr(config_module, "instance_base_dir", lambda: str(base))
        monkeypatch.setattr(ee, "instance_base_dir", lambda: str(base))

        seen = {}

        def _fake_explain(error_file_path, category, form_id, offset, lang):
            seen["tenant_id"] = version_config.get_active_tenant_id()
            return []

        async def _run():
            with patch(
                "backend.tools.report_lookup.explain_errors_by_category_for_form", _fake_explain,
            ), patch("backend.tools.report_lookup.count_errors_by_category", lambda *a, **k: {}):
                with version_config.repo_scope(str(tmp_path), tenant_id="TENANT_A"):
                    return await ee.explain_category_for_report("errors.xml", "formula_error", form_id="4046")

        asyncio.run(_run())
        assert seen["tenant_id"] == "TENANT_A"

    def test_different_tenants_never_cross_contaminate(self, monkeypatch, tmp_path):
        """The concrete H-06 concern: tenant A's request must never cause
        background work to see tenant B's (or no) tenant context."""
        from backend import config as config_module
        import backend.agent.error_explanation as ee

        base = tmp_path / "Instance"
        for fid in ("1001", "2002"):
            (base / fid).mkdir(parents=True)
            (base / fid / "errors.xml").write_text("<x/>", encoding="utf-8")
        monkeypatch.setattr(config_module, "instance_base_dir", lambda: str(base))
        monkeypatch.setattr(ee, "instance_base_dir", lambda: str(base))

        seen = []

        def _fake_explain(error_file_path, category, form_id, offset, lang):
            seen.append(version_config.get_active_tenant_id())
            return []

        async def _run_for(tenant_id, form_id):
            with patch(
                "backend.tools.report_lookup.explain_errors_by_category_for_form", _fake_explain,
            ), patch("backend.tools.report_lookup.count_errors_by_category", lambda *a, **k: {}):
                with version_config.repo_scope(str(tmp_path), tenant_id=tenant_id):
                    return await ee.explain_category_for_report("errors.xml", "formula_error", form_id=form_id)

        asyncio.run(_run_for("TENANT_A", "1001"))
        asyncio.run(_run_for("TENANT_B", "2002"))

        assert seen == ["TENANT_A", "TENANT_B"]


class TestExplainFormulaErrorsNestedExecutorContextPropagation:
    """report_lookup.py's explain_formula_errors() -- the nested
    ThreadPoolExecutor path (only used when >1 rule is being explained)."""

    def test_tenant_context_reaches_every_pooled_worker(self):
        import backend.tools.report_lookup as rl

        seen = []

        def _fake_worker(rule, taxonomy, ollama_base, model, timeout, keep_alive):
            seen.append(version_config.get_active_tenant_id())
            return rule

        rules = [{"rule_name": f"Rule{i}"} for i in range(4)]  # >1 forces the pooled path
        with patch.object(rl, "_explain_single_formula_rule", _fake_worker), \
             patch.object(rl.os, "getenv", side_effect=lambda k, d=None: {"OLLAMA_MAX_CONCURRENCY": "4"}.get(k, d)):
            with version_config.repo_scope("D:\\fake-root", tenant_id="TENANT_C"):
                rl.explain_formula_errors(rules)

        assert len(seen) == 4
        assert all(t == "TENANT_C" for t in seen)


class TestExplainGenericFormulaErrorsNestedExecutorContextPropagation:
    """formula_error_generic.py's explain_generic_formula_errors() -- same
    nested-pool fix as above."""

    def test_tenant_context_reaches_every_pooled_worker(self):
        import backend.tools.formula_error_generic as feg

        seen = []

        def _fake_worker(rule, taxonomy, ollama_base, model, timeout, keep_alive):
            seen.append(version_config.get_active_tenant_id())
            return rule

        rules = [{"rule_name": f"Rule{i}"} for i in range(4)]
        with patch.object(feg, "explain_one_generic_rule", _fake_worker):
            with version_config.repo_scope("D:\\fake-root", tenant_id="TENANT_D"):
                feg.explain_generic_formula_errors(rules)

        assert len(seen) == 4
        assert all(t == "TENANT_D" for t in seen)
