"""M-10: SQL Agent prompt token-budget protection.

Goal: a SAFETY GUARD against exceeding the configured model's actual context
window (config.OLLAMA_NUM_CTX) -- not a blanket prompt-size reduction. A
prompt that already fits comfortably is returned completely unchanged; only
a prompt that would genuinely overflow the model's context gets its OPTIONAL
sections trimmed, in priority order, with the user's question and the core
schema/instructions always preserved.

Model/context discovered (see sqlcore/config.py):
  - OLLAMA_MODEL defaults to "hf.co/defog/sqlcoder-7b-2:Q5_K_M" (this
    deployment's actual configured model, read from .env).
  - OLLAMA_NUM_CTX (already existing, already sent as `options.num_ctx` on
    every Ollama call in sql_generator.py) defaults to 8192 and is already
    env-configurable -- reused here as-is, no new context-window config
    introduced.
  - MODEL_PROFILES[OLLAMA_MODEL]["num_predict"] (already existing) reserves
    the output budget -- 512 for the active sqlcoder profile.
  - Safe input budget = OLLAMA_NUM_CTX - num_predict - SAFETY_MARGIN_TOKENS.
    With the defaults above: 8192 - 512 - 256 = 7424 tokens of INPUT budget
    -- not an arbitrary small cap; it scales with whatever OLLAMA_NUM_CTX/
    num_predict are actually configured for the active model.

Token counting: this deployment has no tokenizer for sqlcoder/llama-family
GGUF models (tiktoken is OpenAI-specific and would not be accurate here, and
adding a model-specific tokenizer dependency is unnecessary for a safety
margin check). Token count is therefore ESTIMATED, conservatively, via a
chars-per-token ratio -- documented explicitly as an estimate, not exact
tokenization, erring on the side of OVER-counting (triggering a reduction a
little earlier than strictly necessary) rather than under-counting (which
could let a genuinely oversized prompt through).
"""
from __future__ import annotations

import logging
import re

import sqlcore.config as config

log = logging.getLogger("sql_generator")

# Conservative: real tokenizers for this model family average ~3.3-4 chars/
# token for English+SQL-identifier text; 3.5 rounds toward over-counting
# (the safe direction for a guard whose job is to never UNDER-estimate).
_CHARS_PER_TOKEN_ESTIMATE = 3.5

# Buffer for message-formatting/role overhead and estimation error -- not
# itself the "limit", just margin on top of the real reserved-output budget.
SAFETY_MARGIN_TOKENS = 256

# Optional, lower-priority prompt sections, in the order they should be
# dropped (first entry removed first). Identified by their own "### <Header>"
# marker, which every prompt style (ddl/minimal/rules) that has such an
# optional block already uses -- a block is everything from its header up to
# (not including) the next "### " header or end of string. Matches across
# all current styles without needing per-style code.
_OPTIONAL_SECTION_HEADERS = (
    "### Worked example",       # ddl style's qa_example block
    "### Few-shot examples",    # minimal style's qa_example + pattern examples
    "### Business semantics",   # shared by ddl + minimal styles
    "### Reasoning plan",       # ddl style only
)


def estimate_tokens(text: str) -> int:
    """Conservative token-count ESTIMATE (not exact tokenization) -- see
    module docstring. Never returns less than a character-count-based lower
    bound of 1 token per 4 characters even for degenerate input."""
    if not text:
        return 0
    try:
        return max(1, int(len(text) / _CHARS_PER_TOKEN_ESTIMATE))
    except Exception:
        # M-10 test 8: estimation must never raise and silently let an
        # unbounded prompt through -- fail toward the SAFE (over-count) side
        # by treating the whole string as "all non-whitespace is one token
        # each", a gross overestimate that forces a reduction pass rather
        # than skipping the check entirely.
        log.warning("[SQL_AGENT] M-10: token estimation failed, failing safe to an overestimate")
        return len(text)


def get_reserved_output_tokens() -> int:
    profile = config.MODEL_PROFILES.get(config.OLLAMA_MODEL, {})
    return int(profile.get("num_predict", 512))


def get_safe_input_token_budget() -> int:
    """The real, model-derived input budget -- see module docstring for the
    exact formula. Never hardcoded to a small constant: it scales with
    whatever OLLAMA_NUM_CTX/num_predict this deployment actually has
    configured for the active model."""
    budget = config.OLLAMA_NUM_CTX - get_reserved_output_tokens() - SAFETY_MARGIN_TOKENS
    # A pathological config (tiny OLLAMA_NUM_CTX) must still yield a usable,
    # positive budget rather than a negative one that would reject every
    # prompt outright.
    return max(budget, 1024)


def _strip_section(prompt: str, header: str) -> str | None:
    """Remove the block starting at *header* up to the next "### " header or
    end of string (plus the blank-line separators around it). Returns the
    reduced prompt, or None if *header* is not present (nothing to remove)."""
    idx = prompt.find(header)
    if idx == -1:
        return None
    # Find the next top-level header AFTER this one's own start.
    next_match = re.search(r"\n### ", prompt[idx + len(header):])
    end = idx + len(header) + next_match.start() if next_match else len(prompt)
    reduced = (prompt[:idx].rstrip("\n") + "\n\n" + prompt[end:].lstrip("\n")).strip() + "\n"
    return reduced


def reduce_optional_sections(prompt: str, budget: int) -> tuple[str, list[str]]:
    """Drop optional sections in priority order until *prompt* fits *budget*
    (by the same estimate_tokens() used for the check) or no more optional
    sections remain. Returns (resulting_prompt, headers_actually_removed)."""
    removed: list[str] = []
    current = prompt
    for header in _OPTIONAL_SECTION_HEADERS:
        if estimate_tokens(current) <= budget:
            break
        reduced = _strip_section(current, header)
        if reduced is not None:
            current = reduced
            removed.append(header)
    return current, removed


def enforce_token_budget(prompt: str, *, context: str = "") -> str:
    """M-10 entry point: return *prompt* UNCHANGED if it already fits the
    safe input budget; otherwise reduce optional sections (preserving the
    user's question and core schema/instructions, which are never one of
    the _OPTIONAL_SECTION_HEADERS blocks) and return the result. Safe to
    call on every SQL Agent prompt-construction path -- a no-op for the
    overwhelming majority of real prompts.
    """
    budget = get_safe_input_token_budget()
    estimated = estimate_tokens(prompt)
    if estimated <= budget:
        return prompt

    reduced_prompt, removed = reduce_optional_sections(prompt, budget)
    final_estimated = estimate_tokens(reduced_prompt)
    # Safe diagnostic logging only -- never the prompt/schema/question text
    # itself (M-10 requirement: no credentials, no full schema, no full
    # prompt in logs).
    log.warning(
        "[SQL_AGENT] M-10: prompt exceeded safe context budget "
        "(estimated_input_tokens=%d, safe_input_budget=%d, context=%s); "
        "reduced_sections=%s, final_estimated_input_tokens=%d%s",
        estimated, budget, context or "unspecified",
        removed or "none", final_estimated,
        " (STILL over budget after exhausting optional sections -- sending as-is)"
        if final_estimated > budget else "",
    )
    return reduced_prompt
