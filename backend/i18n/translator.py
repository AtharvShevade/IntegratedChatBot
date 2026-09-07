"""Async Ollama translation client -- the single model seam.

Adapted from the evaluation harness's translator (eval/multilingual/
translator.py), which is the version the 24-case FR/AR/HI measurements were
taken with. The prompt below is byte-identical to the one that produced those
numbers; changing it invalidates the comparison, so it is deliberately not
"improved" here.

Three adaptations from the harness version, all forced by living on a
user-facing request path rather than in a batch runner:

  1. async (httpx.AsyncClient). /chat holds an event loop; a sync client would
     block it for the whole call.
  2. Bounded total time. The harness retries once with a 300s leash each. Here
     the retry shares one TRANSLATION_TIMEOUT budget so a flaky proxy cannot
     turn one request into a ten-minute hang.
  3. Cancellation. The await on httpx is a cooperative cancellation point, so
     Stop Generation (main.py:172 _run_cancellable) interrupts a translation
     exactly as it interrupts any other Ollama call.

Why not reuse backend.services.llm_service._call_ollama:
  * num_predict is hardcoded to 256 (llm_service.py:212) and truncates silently
  * timeout is pinned to CHAT_FALLBACK_TIMEOUT (12s) regardless of `model`
  * its [PERF] log reports the module-global OLLAMA_MODEL, not the model called

Swapping Gemma for Qwen means setting TRANSLATION_MODEL. Nothing here changes.
"""
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from typing import Protocol

import httpx

from backend.i18n import config

logger = logging.getLogger(__name__)

# Thinking models (gemma4:31b advertises the "thinking" capability) emit their
# reasoning inline when the server does not strip it. Left in place it becomes
# part of the "translation" and is shown to the user, so remove it
# belt-and-braces: ask the server not to think, then strip anything that leaks.
_THINK_BLOCK_RE = re.compile(r"<(think|thinking|reasoning)>.*?</\1>", re.DOTALL | re.IGNORECASE)
_ORPHAN_OPEN_RE = re.compile(r"<(think|thinking|reasoning)>.*", re.DOTALL | re.IGNORECASE)

# Models routinely wrap output in fences or a preamble despite being told not
# to. These are conservative: they only fire on a whole-output wrapper.
_FENCE_RE = re.compile(r"^\s*```[a-zA-Z]*\s*\n(.*?)\n?\s*```\s*$", re.DOTALL)
_PREAMBLE_RE = re.compile(
    r"^\s*(?:here(?:’s|'s| is)[^:\n]*|translation|translated text|output)\s*:\s*",
    re.IGNORECASE,
)

_SYSTEM = (
    "You are a professional translator for a regulatory reporting application "
    "used by banks. Translate the user's text from {src_name} to {tgt_name}.\n"
    "\n"
    "Absolute rules:\n"
    "1. Output ONLY the translation. No preamble, no explanation, no quotes, "
    "no code fences, no notes.\n"
    "2. Copy these VERBATIM, character for character, never translated, never "
    "transliterated, never reformatted:\n"
    "   - report, return and form names (e.g. RAQ, DBR01, CIMS_RAQ(Monthly), "
    "FormGPB, DPSS09)\n"
    "   - XBRL concept and member labels\n"
    "   - all numbers, amounts, currency symbols and codes, percentages\n"
    "   - all dates, in exactly the format given (31-03-2025 stays 31-03-2025)\n"
    "   - IDs, GUIDs, codes, file names, URLs, SQL\n"
    "3. Use Western Arabic digits (0-9) for every number, whatever the target "
    "script.\n"
    "4. Preserve line breaks, bullet characters and list numbering exactly.\n"
    "5. Translate nothing that is already a proper noun of the system.\n"
    "\n"
    # Replaces "If the text is already in {tgt_name}, return it unchanged."
    # That clause caused genuine under-translation: qwen3:14b echoed "bonjour"
    # (cv01/FR) and a whole identifier-heavy sentence (gn03/FR) back unchanged,
    # having judged them already-target-language. Rule 2 above still protects
    # identifiers, so this only removes the licence to echo prose.
    "The input is ALWAYS in {src_name}. Translate it even if it is a single "
    "word, a greeting, or mostly proper nouns. Never return the input "
    "unchanged unless it contains no translatable words at all."
)


@dataclass
class TranslationResult:
    """One translation call.

    ``ok=False`` means the caller must decide the failure policy. It is
    load-bearing that ``text`` is NOT silently trusted on failure: inbound
    treats a failure as fatal (never route on a maybe-wrong query), outbound
    treats it as "keep the English". See boundary.py.
    """

    text: str
    latency_ms: float
    ok: bool = True
    error: str | None = None
    attempts: int = 1
    stripped_thinking: bool = False
    model: str = ""
    skipped: bool = False

    def to_dict(self) -> dict:
        return {
            "latency_ms": round(self.latency_ms, 1),
            "ok": self.ok,
            "error": self.error,
            "attempts": self.attempts,
            "stripped_thinking": self.stripped_thinking,
            "model": self.model,
            "skipped": self.skipped,
        }


class Translator(Protocol):
    """The one model seam. Implementations must be side-effect free."""

    name: str

    async def translate(self, text: str, src: str, tgt: str) -> TranslationResult: ...


def _clean(raw: str) -> tuple[str, bool]:
    """Strip thinking traces and output wrappers. Returns (text, had_thinking)."""
    had_thinking = bool(_THINK_BLOCK_RE.search(raw)) or bool(_ORPHAN_OPEN_RE.search(raw))
    out = _THINK_BLOCK_RE.sub("", raw)
    # An unterminated <think> means the model never emitted a translation at
    # all; keep the flag but do not invent content by keeping the trace.
    out = _ORPHAN_OPEN_RE.sub("", out)
    out = out.strip()
    fence = _FENCE_RE.match(out)
    if fence:
        out = fence.group(1).strip()
    out = _PREAMBLE_RE.sub("", out, count=1)
    return out.strip(), had_thinking


class OllamaTranslator:
    """Translator backed by any Ollama-served model.

    Every parameter defaults to its config function, read at construction, so a
    per-request instance always reflects the current TRANSLATION_MODEL without
    the module needing to be reimported.
    """

    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
        temperature: float | None = None,
        num_predict: int | None = None,
    ) -> None:
        self.model = model or config.translation_model()
        self.base_url = (base_url or config.translation_base_url()).rstrip("/")
        self.timeout = timeout if timeout is not None else config.translation_timeout()
        self.temperature = (
            temperature if temperature is not None else config.translation_temperature()
        )
        self.num_predict = (
            num_predict if num_predict is not None else config.translation_num_predict()
        )
        self.name = self.model
        # Set False once the server rejects the top-level "think" field, so one
        # probe covers the process instead of one per call.
        self._supports_think_flag = True

    def _payload(self, text: str, src: str, tgt: str, with_think: bool) -> dict:
        system = _SYSTEM.format(
            src_name=config.language_name(src),
            tgt_name=config.language_name(tgt),
        )
        payload: dict = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": text},
            ],
            "stream": False,
            "keep_alive": config.keep_alive(),
            "options": {
                "temperature": self.temperature,
                "num_predict": self.num_predict,
            },
        }
        if with_think:
            payload["think"] = False
        return payload

    async def translate(self, text: str, src: str, tgt: str) -> TranslationResult:
        if src == tgt or not text or not text.strip():
            return TranslationResult(
                text=text, latency_ms=0.0, ok=True, model=self.model, skipped=True
            )

        last_error: str | None = None
        started = time.perf_counter()

        def _elapsed() -> float:
            return (time.perf_counter() - started) * 1000.0

        # Retry once: the Ollama endpoint is frequently a shared remote proxy
        # that throws transient 502s. One flaky call must not cost the user
        # their answer. The retry shares the SAME wall-clock budget rather than
        # getting a fresh timeout -- an unbounded retry on a user-facing path
        # is how a 60s leash becomes a 120s hang.
        for attempt in range(1, 3):
            remaining = self.timeout - (_elapsed() / 1000.0)
            if remaining <= 0:
                last_error = last_error or f"TimeoutError: exceeded {self.timeout}s budget"
                break
            try:
                payload = self._payload(text, src, tgt, self._supports_think_flag)
                async with httpx.AsyncClient(timeout=remaining) as client:
                    resp = await client.post(f"{self.base_url}/api/chat", json=payload)
                if resp.status_code == 400 and self._supports_think_flag:
                    # Older Ollama builds reject the "think" field outright.
                    # Drop it for the rest of the process and retry; _clean()
                    # still removes any trace that leaks through.
                    self._supports_think_flag = False
                    continue
                resp.raise_for_status()
                raw = resp.json()["message"]["content"]
                cleaned, had_thinking = _clean(raw)
                if not cleaned:
                    # Empty after cleaning means the model emitted only a
                    # thinking trace. Never return "" as a translation.
                    return TranslationResult(
                        text="", latency_ms=_elapsed(), ok=False,
                        error="empty translation after cleaning",
                        attempts=attempt, stripped_thinking=had_thinking,
                        model=self.model,
                    )
                return TranslationResult(
                    text=cleaned, latency_ms=_elapsed(), ok=True, attempts=attempt,
                    stripped_thinking=had_thinking, model=self.model,
                )
            except httpx.HTTPStatusError as exc:
                last_error = f"HTTPStatusError: {exc.response.status_code}"
            except Exception as exc:  # noqa: BLE001 - recorded, never raised at the user
                last_error = f"{type(exc).__name__}: {exc}"

        logger.warning(
            "[I18N_TRANSLATE_FAIL] model=%s %s->%s chars=%d error=%s",
            self.model, src, tgt, len(text), last_error,
        )
        return TranslationResult(
            # The ORIGINAL text, never a partial result. Callers must check
            # .ok before using it; inbound refuses to route on it at all.
            text=text,
            latency_ms=_elapsed(), ok=False, error=last_error, attempts=2,
            model=self.model,
        )


class IdentityTranslator:
    """Returns input unchanged. Proves in tests that TRANSLATION_MODEL is the
    only model seam -- nothing else in the package reaches a network."""

    name = "identity"

    async def translate(self, text: str, src: str, tgt: str) -> TranslationResult:
        return TranslationResult(text=text, latency_ms=0.0, ok=True, model="identity")


def get_translator() -> Translator:
    """Build the translator for one request from current configuration."""
    return OllamaTranslator()


async def warmup() -> float:
    """Prime the model so the first real request does not absorb a 60-80s cold
    start. Mirrors the existing startup warm-up at main.py:125-134."""
    result = await OllamaTranslator().translate("Report status", "en", "fr")
    return result.latency_ms
