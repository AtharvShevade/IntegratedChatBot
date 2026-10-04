"""L-04: prompt/configuration hardening.

Concrete fix implemented: backend/db_qa/beautifier.py's beautify_stream()
and backend/agent/db_qa_router.py's handle_db_qa_query()/
stream_db_qa_beautifier() each hardcoded their own "phi3:mini" default for
the `model` parameter -- duplicated in three places, and in practice never
actually used by any production call site (every real caller already passes
its own explicit model via backend.config.APP_DB_BEAUTIFY_MODEL). These now
fall back to the centralized backend.services.llm_config.chat_model()
default instead of a hardcoded literal, matching the same pattern already
used for the `ollama_url` parameter.

Other L-04 findings (duplicated instructional wording across error_llm.py/
formula_error_generic.py/llm_service.py/beautifier.py's system prompts; the
SQL Agent's build_prompt() interpolating the user's raw query directly into
a single flat instruction string with no role separation or delimiter) were
investigated and are documented in the Batch 3 report as intentionally NOT
changed -- fixing the SQL Agent's prompt structure risks shifting a
carefully-tuned, temperature=0 SQL-generation prompt's output with no way
to verify against a live model in this environment, and consolidating the
duplicated instructional text across files would mean editing live prompts
"merely for style", which this item explicitly rules out.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from backend.services import llm_config


class TestBeautifierModelDefaultIsCentralized:
    def test_beautify_stream_resolves_none_model_to_centralized_default(self, monkeypatch):
        import backend.db_qa.beautifier as beautifier_mod

        monkeypatch.delenv("OLLAMA_MODEL", raising=False)
        captured = {}

        def _fake_post(url, **kwargs):
            captured["payload"] = kwargs.get("json")
            raise ConnectionError("no real network in this test")

        monkeypatch.setattr(beautifier_mod.requests, "post", _fake_post)

        list(beautifier_mod.beautify_stream("question?", {"summary": "fallback"}))

        assert captured["payload"]["model"] == llm_config.chat_model()

    def test_explicit_model_argument_still_overrides_the_default(self, monkeypatch):
        import backend.db_qa.beautifier as beautifier_mod

        captured = {}

        def _fake_post(url, **kwargs):
            captured["payload"] = kwargs.get("json")
            raise ConnectionError("no real network in this test")

        monkeypatch.setattr(beautifier_mod.requests, "post", _fake_post)

        list(beautifier_mod.beautify_stream("question?", {"summary": "fallback"}, model="explicit-model"))

        assert captured["payload"]["model"] == "explicit-model"


class TestDbQaRouterModelDefaultIsCentralized:
    def test_stream_db_qa_beautifier_passes_none_through_and_beautifier_resolves_it(self, monkeypatch):
        from backend.agent import db_qa_router

        captured = {}

        def _fake_beautify_stream(message, result, model=None, ollama_url=None):
            captured["model"] = model
            yield "token"

        monkeypatch.setattr(db_qa_router, "beautify_stream", _fake_beautify_stream)

        list(db_qa_router.stream_db_qa_beautifier("question?", {"summary": "x"}))

        # None flows through unchanged -- beautify_stream() itself is the
        # single place that resolves it to the centralized default.
        assert captured["model"] is None

    def test_handle_db_qa_query_default_parameter_is_none_not_a_literal(self):
        """handle_db_qa_query itself (not just beautify_stream) must no
        longer declare its own hardcoded model default."""
        import inspect
        from backend.agent import db_qa_router

        sig = inspect.signature(db_qa_router.handle_db_qa_query)
        assert sig.parameters["model"].default is None

    def test_stream_db_qa_beautifier_default_parameter_is_none_not_a_literal(self):
        import inspect
        from backend.agent import db_qa_router

        sig = inspect.signature(db_qa_router.stream_db_qa_beautifier)
        assert sig.parameters["model"].default is None


class TestNoUnrelatedPromptBehaviorChange:
    """Pins down that this fix is purely a default-value change -- the
    actual prompt/messages construction in beautify_stream is untouched."""

    def test_beautify_stream_message_structure_unchanged(self, monkeypatch):
        import backend.db_qa.beautifier as beautifier_mod

        captured = {}

        def _fake_post(url, **kwargs):
            captured["payload"] = kwargs.get("json")
            raise ConnectionError("no real network in this test")

        monkeypatch.setattr(beautifier_mod.requests, "post", _fake_post)

        list(beautifier_mod.beautify_stream("what is my department?", {"summary": "Finance"}))

        messages = captured["payload"]["messages"]
        assert messages[0]["role"] == "system"
        assert messages[-1]["role"] == "user"
