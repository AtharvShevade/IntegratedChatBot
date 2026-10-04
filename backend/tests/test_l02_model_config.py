"""L-02: centralized LLM model-name configuration (backend/services/llm_config.py).

Model names/base URL used to be re-read from the environment with their own
hardcoded default in several files, and the defaults had drifted apart
(llm_service.py defaulted OLLAMA_MODEL to "phi3:mini" while every other call
site defaulted it to "llama3.1:latest"). These tests prove the centralized
defaults are consistent and that call sites use them.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

from backend.services import llm_config

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import backend.sql_agent  # noqa: F401,E402  (runs _bootstrap.ensure(), puts `sqlcore` on sys.path)
from sqlcore.sql_generator import _get_model_profile  # noqa: E402


class TestCentralizedDefaults:
    def test_base_url_default(self, monkeypatch):
        monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
        assert llm_config.base_url() == "http://127.0.0.1:11434"

    def test_chat_model_default(self, monkeypatch):
        monkeypatch.delenv("OLLAMA_MODEL", raising=False)
        assert llm_config.chat_model() == "llama3.1:latest"

    def test_extract_model_default(self, monkeypatch):
        monkeypatch.delenv("OLLAMA_EXTRACT_MODEL", raising=False)
        assert llm_config.extract_model() == "phi3:mini"

    def test_compare_model_default(self, monkeypatch):
        monkeypatch.delenv("OLLAMA_COMPARE_MODEL", raising=False)
        assert llm_config.compare_model() == "llama3.1:latest"

    def test_env_override_wins(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_MODEL", "custom-model:latest")
        assert llm_config.chat_model() == "custom-model:latest"


class TestCallSitesUseCentralizedConfig:
    def test_llm_service_reads_from_llm_config(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_MODEL", "sentinel-chat-model")
        monkeypatch.setenv("OLLAMA_EXTRACT_MODEL", "sentinel-extract-model")
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://sentinel:1234")
        from backend.services import llm_service
        importlib.reload(llm_service)
        try:
            assert llm_service.OLLAMA_MODEL == "sentinel-chat-model"
            assert llm_service.OLLAMA_EXTRACT_MODEL == "sentinel-extract-model"
            assert llm_service.OLLAMA_BASE_URL == "http://sentinel:1234"
        finally:
            monkeypatch.undo()
            importlib.reload(llm_service)

    def test_error_llm_settings_use_centralized_default(self, monkeypatch):
        monkeypatch.delenv("OLLAMA_MODEL", raising=False)
        monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
        from backend.tools import error_llm
        settings = error_llm.llm_settings()
        assert settings["model"] == "llama3.1:latest"
        assert settings["base"] == "http://127.0.0.1:11434"

    def test_error_llm_settings_honor_env_override(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_MODEL", "custom-explain-model")
        from backend.tools import error_llm
        settings = error_llm.llm_settings()
        assert settings["model"] == "custom-explain-model"

    def test_beautifier_default_url_comes_from_centralized_config(self, monkeypatch):
        """L-02 cleanup: beautify_stream() used to read OLLAMA_BASE_URL
        directly with its own hardcoded default ("http://localhost:11434",
        a THIRD distinct literal from llm_config's "http://127.0.0.1:11434"
        and error_llm's). It must now resolve to the same centralized
        default as every other call site when no explicit ollama_url is
        passed and the env var is unset."""
        monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
        import backend.db_qa.beautifier as beautifier_mod

        captured = {}

        def _fake_post(url, **kwargs):
            captured["url"] = url
            raise ConnectionError("no real network in this test")

        monkeypatch.setattr(beautifier_mod.requests, "post", _fake_post)

        # beautify_stream catches the connection failure and falls back to
        # the plain summary -- draining the generator is enough to trigger
        # the one requests.post() call and capture the URL it used.
        list(beautifier_mod.beautify_stream("question?", {"summary": "fallback"}))

        assert captured["url"].startswith(llm_config.base_url())


class TestUnknownModelProfile:
    """backend/sql_agent/sqlcore/sql_generator.py's _get_model_profile() -- an
    unrecognized OLLAMA_MODEL must get temperature=0.0 (not None) and log a
    warning, never crash."""

    def test_known_model_profile_unchanged(self):
        profile = _get_model_profile("llama3.1:latest")
        assert profile["temperature"] == 0.0
        assert profile["prompt_style"] == "minimal"

    def test_unknown_model_gets_temperature_zero(self):
        profile = _get_model_profile("totally-unknown-model:v9")
        assert profile["temperature"] == 0.0
        assert profile["prompt_style"] == "rules"

    def test_unknown_model_logs_warning(self, caplog):
        import logging
        with caplog.at_level(logging.WARNING, logger="sql_generator"):
            _get_model_profile("totally-unknown-model:v9")
        assert any("Unrecognized OLLAMA_MODEL" in r.message for r in caplog.records)

    def test_unknown_model_does_not_crash(self):
        profile = _get_model_profile(None)
        assert profile["temperature"] == 0.0
