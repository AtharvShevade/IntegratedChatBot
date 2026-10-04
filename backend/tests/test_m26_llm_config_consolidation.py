"""M-26: OLLAMA_TIMEOUT/OLLAMA_KEEP_ALIVE/OLLAMA_MAX_CONCURRENCY were each
re-read with their own copy-pasted default in 6 separate files
(services/llm_service.py, tools/error_llm.py, tools/formula_error_generic.py,
tools/report_lookup.py x2, tools/xbrl_comparator.py, tools/variance_explain.py).
Consolidated into backend/services/llm_config.py (which already centralized
the Ollama model-name settings for L-02) -- these tests pin the new
functions' defaults/env-override behavior and confirm llm_service.py's
module-level constants (read once at import) match them.
"""
from __future__ import annotations

import importlib

from backend.services import llm_config


class TestDefaults:
    def test_request_timeout_default(self, monkeypatch):
        monkeypatch.delenv("OLLAMA_TIMEOUT", raising=False)
        assert llm_config.request_timeout() == 180.0

    def test_keep_alive_default(self, monkeypatch):
        monkeypatch.delenv("OLLAMA_KEEP_ALIVE", raising=False)
        assert llm_config.keep_alive() == "30m"

    def test_max_concurrency_default(self, monkeypatch):
        monkeypatch.delenv("OLLAMA_MAX_CONCURRENCY", raising=False)
        assert llm_config.max_concurrency() == 2


class TestEnvOverride:
    def test_request_timeout_override(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_TIMEOUT", "45")
        assert llm_config.request_timeout() == 45.0

    def test_keep_alive_override(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_KEEP_ALIVE", "5m")
        assert llm_config.keep_alive() == "5m"

    def test_max_concurrency_override(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_MAX_CONCURRENCY", "5")
        assert llm_config.max_concurrency() == 5


class TestMaxConcurrencyEdgeCases:
    """Preserves the exact fallback-to-2 behavior error_llm.py/
    formula_error_generic.py/report_lookup.py already had for a malformed
    or non-positive value."""

    def test_malformed_value_falls_back_to_default(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_MAX_CONCURRENCY", "not-a-number")
        assert llm_config.max_concurrency() == 2

    def test_zero_is_clamped_to_one(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_MAX_CONCURRENCY", "0")
        assert llm_config.max_concurrency() == 1

    def test_negative_is_clamped_to_one(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_MAX_CONCURRENCY", "-5")
        assert llm_config.max_concurrency() == 1


class TestLlmServiceModuleConstantsUseLlmConfig:
    def test_request_timeout_and_keep_alive_match_llm_config(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_TIMEOUT", "77")
        monkeypatch.setenv("OLLAMA_KEEP_ALIVE", "12m")
        import backend.services.llm_service as llm_service
        importlib.reload(llm_service)
        try:
            assert llm_service.REQUEST_TIMEOUT == 77.0
            assert llm_service._KEEP_ALIVE == "12m"
        finally:
            monkeypatch.delenv("OLLAMA_TIMEOUT", raising=False)
            monkeypatch.delenv("OLLAMA_KEEP_ALIVE", raising=False)
            importlib.reload(llm_service)


class TestErrorLlmSettingsUseLlmConfig:
    def test_llm_settings_reflects_env_overrides(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_TIMEOUT", "99")
        monkeypatch.setenv("OLLAMA_KEEP_ALIVE", "1m")
        monkeypatch.setenv("OLLAMA_MAX_CONCURRENCY", "7")
        from backend.tools import error_llm
        settings = error_llm.llm_settings()
        assert settings["timeout"] == 99.0
        assert settings["keep_alive"] == "1m"
        assert settings["max_concurrency"] == 7
