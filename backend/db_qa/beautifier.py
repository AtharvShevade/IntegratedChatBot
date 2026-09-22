"""LLM beautifier — takes pre-fetched structured data and formats it naturally.

The LLM is only used for formatting, not for answering.  The prompt is small,
so this is fast (typically < 5s on phi3:mini).
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Generator

import requests

logger = logging.getLogger("db_beautifier")

# Maximum number of records passed to the LLM (keep prompt small)
_MAX_RECORDS_IN_PROMPT = 30
_MAX_CHARS_IN_PROMPT = 6_000

_SYSTEM = (
    "You are a concise data assistant for iDEAL, a regulatory reporting application. "
    "You will receive a user question and structured data fetched directly from the application database. "
    "Your job is to format this data as a clear, friendly, human-readable response. "
    "Rules: "
    "1. Never invent data — only use what is provided. "
    "2. If the data is empty or shows an access denied message, relay that politely. "
    "3. Use bullet points or a short table for lists of records. "
    "4. Keep the response concise. Do not add advice, caveats, or extra commentary. "
    "5. Do not mention internal field names like 'RoleId' — convert them to plain English."
)


def _format_records(records: list[dict]) -> str:
    """Convert records to a compact JSON block suitable for the prompt."""
    trimmed = records[:_MAX_RECORDS_IN_PROMPT]
    text = json.dumps(trimmed, indent=2, default=str)
    if len(text) > _MAX_CHARS_IN_PROMPT:
        text = text[:_MAX_CHARS_IN_PROMPT] + "\n... (truncated)"
    return text


def _build_prompt(question: str, result: dict) -> str:
    label = result.get("label", "Result")
    summary = result.get("summary", "")
    records = result.get("records", [])
    found = result.get("found", False)

    if not found:
        data_block = f"Result: {summary}"
    else:
        data_block = f"Category: {label}\nRecords ({len(records)} total):\n{_format_records(records)}"

    return (
        f"{_SYSTEM}\n\n"
        f"User question: {question}\n\n"
        f"Data from database:\n{data_block}\n\n"
        f"Response:"
    )


def beautify_stream(
    question: str,
    result: dict,
    model: str = "phi3:mini",
    ollama_url: str | None = None,
) -> Generator[str, None, None]:
    """Yield LLM tokens that beautifully present *result* for *question*.

    Yields plain text tokens.  Caller is responsible for SSE framing.
    Falls back to the plain ``summary`` string if Ollama is unavailable.
    """
    # Get Ollama URL from parameter, env var, or default
    if ollama_url is None:
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    base_url = ollama_url.rstrip("/")
    prompt = _build_prompt(question, result)
    _t0 = time.monotonic()

    try:
        resp = requests.post(
            f"{base_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": True,
                "options": {"num_predict": 512, "num_ctx": 4096, "temperature": 0.3},
            },
            stream=True,
            timeout=120,
        )
        if not resp.ok:
            logger.warning(
                "AI request failed | flow=db_qa_beautify | model=%s | duration_ms=%.0f | "
                "http_status=%s | error=%s",
                model, (time.monotonic() - _t0) * 1000, resp.status_code, resp.text[:200],
            )
            yield result.get("summary", "No data found.")
            return

        token_count = 0
        for line in resp.iter_lines():
            if not line:
                continue
            try:
                chunk = json.loads(line)
            except json.JSONDecodeError:
                continue
            token = chunk.get("response", "")
            if token:
                token_count += 1
                yield token
            if chunk.get("done"):
                break
        logger.info(
            "AI completed | flow=db_qa_beautify | model=%s | duration_ms=%.0f | tokens=%d",
            model, (time.monotonic() - _t0) * 1000, token_count,
        )

    except requests.ConnectionError as exc:
        logger.warning(
            "AI request failed | flow=db_qa_beautify | model=%s | duration_ms=%.0f | "
            "error=unreachable at %s: %s",
            model, (time.monotonic() - _t0) * 1000, base_url, exc,
        )
        yield result.get("summary", "No data found.")
    except Exception as exc:
        logger.warning(
            "AI request failed | flow=db_qa_beautify | model=%s | duration_ms=%.0f | error=%s",
            model, (time.monotonic() - _t0) * 1000, exc, exc_info=True,
        )
        yield result.get("summary", "No data found.")
