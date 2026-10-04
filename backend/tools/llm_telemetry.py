"""L-03: token usage and truncation visibility, shared across every Ollama
call site (chat/intent extraction in services/llm_service.py, error
explanation in tools/error_llm.py, the DB Q&A beautifier in
db_qa/beautifier.py, and SQL generation in sql_agent/sqlcore/sql_generator.py).

Ollama's own response (streaming final chunk, or the whole body when
``stream: False``) already carries ``prompt_eval_count``, ``eval_count``, and
``done_reason`` -- this just extracts and formats them consistently instead
of each call site inventing its own version (or, as sql_generator.py did,
computing them and never actually logging them).

Deliberately does not log prompt/response text -- only counts and a
truncation flag, so this adds visibility without adding a new place raw
user/AI content could leak into logs.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TokenInfo:
    prompt_tokens: int | None
    completion_tokens: int | None
    done_reason: str | None
    truncated: bool

    def as_log_str(self) -> str:
        """``prompt_tokens=.. completion_tokens=.. truncated=..`` -- safe to
        append to any existing "AI completed" log line."""
        return (
            f"prompt_tokens={self.prompt_tokens} "
            f"completion_tokens={self.completion_tokens} "
            f"truncated={self.truncated}"
        )


def extract_token_info(response_json: dict | None) -> TokenInfo:
    """Build a TokenInfo from an Ollama response body (streaming final chunk
    or the whole non-streaming response -- both carry the same field names).

    Never raises: a missing/malformed field degrades to None/False rather
    than an exception, since this is purely observability -- it must never
    be able to break the actual LLM call it's reporting on.
    """
    if not isinstance(response_json, dict):
        return TokenInfo(None, None, None, False)

    def _as_int(value) -> int | None:
        return value if isinstance(value, int) else None

    prompt_tokens = _as_int(response_json.get("prompt_eval_count"))
    completion_tokens = _as_int(response_json.get("eval_count"))
    done_reason = response_json.get("done_reason")
    done_reason = done_reason if isinstance(done_reason, str) else None
    # Ollama uses "length" for "stopped because num_predict/context was hit"
    # (truncated) vs "stop" for a natural end-of-generation.
    truncated = done_reason == "length"

    return TokenInfo(prompt_tokens, completion_tokens, done_reason, truncated)
