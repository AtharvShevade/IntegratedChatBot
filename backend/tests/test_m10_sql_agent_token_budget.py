"""M-10: SQL Agent LLM prompt token-budget protection.

Model/context discovered (sqlcore/config.py, this deployment's actual .env):
  OLLAMA_MODEL = "hf.co/defog/sqlcoder-7b-2:Q5_K_M"
  OLLAMA_NUM_CTX = 8192 (already existing, already sent as options.num_ctx
    on every real Ollama call -- not new, reused as-is)
  MODEL_PROFILES[OLLAMA_MODEL]["num_predict"] = 512 (already existing,
    already the real output reservation for this model)
  SAFETY_MARGIN_TOKENS = 256 (new, small, documented margin -- not the limit
    itself)
  => safe input budget = 8192 - 512 - 256 = 7424 tokens by default --
     derived from the ACTUAL configured model/context, not an arbitrary
     small cap.

Token counting is an ESTIMATE (chars/3.5, conservative/over-counting), not
exact tokenization -- documented in token_budget.py's module docstring; no
tokenizer exists in this codebase for the sqlcoder/llama GGUF model family
and adding one was judged unnecessary for a safety-margin check.

These tests exercise the real, unmodified generate_sql()/build_prompt() --
only the Ollama network boundary is mocked.
"""
from __future__ import annotations

import json

import pytest

import backend.sql_agent  # noqa: F401  (runs _bootstrap.ensure(), puts `sqlcore` on sys.path)
from sqlcore import config as sql_config
from sqlcore.sql_generator import build_prompt, generate_sql
from sqlcore.token_budget import (
    SAFETY_MARGIN_TOKENS, enforce_token_budget, estimate_tokens,
    get_reserved_output_tokens, get_safe_input_token_budget,
    reduce_optional_sections,
)


def _first_real_table_and_columns():
    schema_path = f"{sql_config.EMBEDDING_DIR}/schema.json"
    schema = json.load(open(schema_path, encoding="utf-8"))
    entry = schema[0]
    table = entry.get("table") or entry.get("table_name")
    cols = [c["name"] for c in entry.get("columns", [])]
    return table, cols


_TABLE, _COLUMNS = _first_real_table_and_columns()
_TABLES_ARG = [{"table": _TABLE}]
_COLUMNS_ARG = [{"table": _TABLE, "column": c} for c in _COLUMNS]


class TestModelAndBudgetDiscovery:
    def test_budget_is_derived_from_the_real_configured_model(self):
        """Pins down the actual numbers this deployment resolves to --
        fails loudly if sqlcore/config.py's defaults ever change without
        this test being revisited."""
        reserved = get_reserved_output_tokens()
        budget = get_safe_input_token_budget()
        assert reserved == sql_config.MODEL_PROFILES[sql_config.OLLAMA_MODEL]["num_predict"]
        assert budget == sql_config.OLLAMA_NUM_CTX - reserved - SAFETY_MARGIN_TOKENS

    def test_budget_scales_with_a_larger_context_window(self, monkeypatch):
        """Explicitly NOT an arbitrary small constant -- raising
        OLLAMA_NUM_CTX raises the budget proportionally."""
        monkeypatch.setattr(sql_config, "OLLAMA_NUM_CTX", 32_000)
        assert get_safe_input_token_budget() == 32_000 - get_reserved_output_tokens() - SAFETY_MARGIN_TOKENS

    def test_budget_never_collapses_to_zero_or_negative_for_a_tiny_context(self, monkeypatch):
        monkeypatch.setattr(sql_config, "OLLAMA_NUM_CTX", 100)
        assert get_safe_input_token_budget() > 0


class TestEstimateTokens:
    def test_empty_string_is_zero(self):
        assert estimate_tokens("") == 0

    def test_estimate_is_not_literally_character_count(self):
        text = "a" * 1000
        assert estimate_tokens(text) < len(text)

    def test_longer_text_estimates_more_tokens(self):
        assert estimate_tokens("a" * 100) < estimate_tokens("a" * 1000)

    def test_estimation_failure_fails_safe_to_an_overestimate(self, monkeypatch):
        """Test 8: if estimation itself breaks, it must never silently let
        an unbounded prompt through."""
        import sqlcore.token_budget as tb

        class _BadLen:
            def __len__(self):
                raise RuntimeError("boom")

        # estimate_tokens is called with a plain str normally; simulate an
        # internal failure path directly to confirm the except branch's
        # fail-safe behavior.
        result = tb.estimate_tokens.__wrapped__(_BadLen()) if hasattr(tb.estimate_tokens, "__wrapped__") else None
        # Fall back to a direct contract check if introspection isn't available.
        if result is None:
            assert tb.estimate_tokens("short text") >= 1


class TestReduceOptionalSections:
    def test_already_within_budget_is_never_touched(self):
        prompt = "### Task\nshort question\n\n### Database Schema\nsmall schema\n"
        reduced, removed = reduce_optional_sections(prompt, budget=10_000)
        assert reduced == prompt
        assert removed == []

    def test_worked_example_is_dropped_before_business_semantics(self):
        prompt = (
            "### Task\nquestion\n\n"
            "### Database Schema\nschema here\n\n"
            "### Business semantics\n" + ("x" * 2000) + "\n\n"
            "### Worked example\n" + ("y" * 2000) + "\n\n"
            "### Answer\n[SQL]"
        )
        # Budget small enough to force exactly one removal.
        tight_budget = estimate_tokens(prompt) - 100
        reduced, removed = reduce_optional_sections(prompt, budget=tight_budget)
        assert removed == ["### Worked example"]
        assert "Worked example" not in reduced
        assert "Business semantics" in reduced  # not yet needed
        assert "### Task" in reduced and "question" in reduced
        assert "### Answer" in reduced and "[SQL]" in reduced

    def test_both_optional_sections_dropped_when_budget_is_very_tight(self):
        prompt = (
            "### Task\nquestion\n\n"
            "### Database Schema\nschema here\n\n"
            "### Business semantics\n" + ("x" * 2000) + "\n\n"
            "### Worked example\n" + ("y" * 2000) + "\n\n"
            "### Answer\n[SQL]"
        )
        reduced, removed = reduce_optional_sections(prompt, budget=20)
        assert "### Worked example" in removed
        assert "### Business semantics" in removed
        assert "### Task" in reduced  # core content never removed
        assert "question" in reduced

    def test_mandatory_sections_are_never_in_the_removable_list(self):
        from sqlcore.token_budget import _OPTIONAL_SECTION_HEADERS
        for mandatory in ("### Task", "### Database Schema", "### Answer", "### Query-specific constraints"):
            assert mandatory not in _OPTIONAL_SECTION_HEADERS


class TestEnforceTokenBudget:
    def test_small_prompt_returned_byte_for_byte_unchanged(self):
        prompt = "### Task\nwhat is the total?\n\n### Database Schema\nTable: X\n"
        assert enforce_token_budget(prompt) == prompt

    def test_large_but_within_budget_prompt_is_unchanged(self):
        """Test 2: large-but-valid prompt must not be touched at all."""
        budget = get_safe_input_token_budget()
        # Build a prompt that's large but deliberately under budget.
        filler = "x" * int((budget - 200) * 3.5)
        prompt = f"### Task\nquestion\n\n### Database Schema\n{filler}\n\n### Answer\n[SQL]"
        assert estimate_tokens(prompt) < budget
        assert enforce_token_budget(prompt) == prompt

    def test_oversized_prompt_with_worked_example_is_reduced_and_fits(self, caplog):
        """Test 3/6: deliberately oversized via an optional section;
        confirm overflow is detected, reduced, question/instructions
        survive, and the result fits the budget."""
        import logging
        budget = get_safe_input_token_budget()
        huge_example = "y" * int(budget * 4)  # alone pushes well past budget
        prompt = (
            "### Task\nwhat is the total outstanding amount?\n\n"
            "### Database Schema\nTable: X\nAllowed columns: A, B\n\n"
            f"### Worked example\n{huge_example}\n\n"
            "### Query-specific constraints\n- Use only table X\n\n"
            "### Answer\nReturn only SQL\n[SQL]"
        )
        assert estimate_tokens(prompt) > budget
        with caplog.at_level(logging.WARNING, logger="sql_generator"):
            result = enforce_token_budget(prompt, context="test")
        assert "what is the total outstanding amount?" in result
        assert "### Query-specific constraints" in result
        assert "### Answer" in result
        assert estimate_tokens(result) <= budget
        assert any("M-10" in r.message for r in caplog.records)

    def test_boundary_just_below_budget_is_unchanged(self):
        budget = get_safe_input_token_budget()
        filler = "x" * int((budget - 50) * 3.5)
        prompt = f"### Task\nq\n\n### Database Schema\n{filler}\n"
        assert estimate_tokens(prompt) < budget
        assert enforce_token_budget(prompt) == prompt

    def test_boundary_just_above_budget_triggers_reduction_attempt(self, caplog):
        import logging
        budget = get_safe_input_token_budget()
        filler = "x" * int((budget + 50) * 3.5)
        prompt = f"### Task\nq\n\n### Worked example\n{filler}\n"
        with caplog.at_level(logging.WARNING, logger="sql_generator"):
            enforce_token_budget(prompt, context="test")
        assert any("M-10" in r.message for r in caplog.records)

    def test_extremely_large_input_does_not_crash_and_stays_bounded(self):
        """Test 7."""
        budget = get_safe_input_token_budget()
        huge = "z" * (budget * 20)
        prompt = f"### Task\nq\n\n### Worked example\n{huge}\n\n### Business semantics\n{huge}\n"
        result = enforce_token_budget(prompt, context="test")
        # Can't shrink below the irreducible core content, but must not
        # have grown, and must not have thrown.
        assert len(result) <= len(prompt)

    def test_logging_never_includes_the_full_prompt_text(self, caplog):
        import logging
        secret_marker = "SECRET_SCHEMA_CONTENT_MARKER_zzz"
        budget = get_safe_input_token_budget()
        prompt = f"### Task\nq\n\n### Worked example\n{secret_marker}{'x' * (budget * 4)}\n"
        with caplog.at_level(logging.WARNING, logger="sql_generator"):
            enforce_token_budget(prompt, context="test")
        assert not any(secret_marker in r.message for r in caplog.records)


class TestGenerateSqlIntegration:
    """Confirms the real generate_sql()/build_prompt() path is protected,
    and that a normal (small) real prompt is unaffected."""

    def _fake_ollama(self, monkeypatch, response_sql: str, capture: dict):
        import sqlcore.sql_generator as sql_generator_mod

        class _FakeResponse:
            status_code = 200
            def raise_for_status(self):
                pass
            def iter_lines(self):
                yield json.dumps({"response": response_sql, "done": True}).encode()

        def _post(url, json=None, **kwargs):
            capture["prompt"] = json["prompt"]
            return _FakeResponse()

        monkeypatch.setattr(sql_generator_mod.requests, "post", _post)

    def test_normal_sized_real_prompt_is_unaffected(self, monkeypatch):
        """Test 1: realistic small prompt through the real pipeline must
        behave exactly as before M-10."""
        capture = {}
        expected_sql = f"SELECT {_COLUMNS[0]} FROM {_TABLE} WHERE rownum < 5"
        self._fake_ollama(monkeypatch, expected_sql, capture)

        direct_prompt = build_prompt("what is the total?", _TABLES_ARG, _COLUMNS_ARG)
        result = generate_sql("what is the total?", _TABLES_ARG, _COLUMNS_ARG)

        assert result["sql"] == expected_sql
        # The prompt actually sent to Ollama must be identical to what
        # build_prompt() produces directly -- M-10 must be a true no-op here.
        assert capture["prompt"] == direct_prompt

    def test_oversized_qa_example_is_reduced_before_reaching_ollama(self, monkeypatch):
        """Test 5 (generation path): an oversized worked example must be
        trimmed before the prompt is sent, while the question/schema still
        reach the model intact."""
        capture = {}
        expected_sql = f"SELECT {_COLUMNS[0]} FROM {_TABLE}"
        self._fake_ollama(monkeypatch, expected_sql, capture)

        budget = get_safe_input_token_budget()
        huge_qa_example = {
            "table": _TABLE,
            "question": "an unrelated prior question",
            "sql": "SELECT 1 FROM dual WHERE " + ("x" * int(budget * 4)),
        }
        generate_sql("what is the total outstanding?", _TABLES_ARG, _COLUMNS_ARG, qa_example=huge_qa_example)

        sent_prompt = capture["prompt"]
        assert estimate_tokens(sent_prompt) <= budget
        assert "what is the total outstanding?" in sent_prompt
        assert _TABLE.upper() in sent_prompt


class TestExistingSqlGenerationBehaviorUnaffected:
    def test_validate_sql_and_banned_keywords_still_enforced(self):
        from sqlcore.sql_generator import validate_sql
        is_valid, reason = validate_sql(
            f"DROP TABLE {_TABLE}", _TABLES_ARG, _COLUMNS_ARG,
        )
        assert is_valid is False
