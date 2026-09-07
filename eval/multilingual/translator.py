"""Model-agnostic translation client for the evaluation harness.

Why this exists instead of reusing backend.services.llm_service._call_ollama:

  1. ``num_predict`` is hardcoded to 256 there (llm_service.py:212). A variance
     summary or a 7-option disambiguation list translates to well over that,
     and Ollama truncates silently -- the harness would score a truncation as a
     translation-quality failure and never know why.
  2. ``timeout`` is pinned to CHAT_FALLBACK_TIMEOUT (12s) regardless of the
     ``model`` argument (llm_service.py:224). That leash is deliberate for the
     conversational fallback, but a 31B model on a shared remote proxy will not
     answer inside it.
  3. Its [PERF] log reports the module-global OLLAMA_MODEL rather than the
     ``model`` actually called, so log-derived timings would be mislabelled for
     every overridden call.

The Translator protocol is the single model seam in the whole harness. Swapping
Gemma for Qwen means setting EVAL_TRANSLATE_MODEL -- nothing here changes.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Protocol

import httpx

from eval.multilingual import config

# Thinking models (gemma4:31b advertises the "thinking" capability) emit their
# reasoning inline when the server does not strip it. Left in place it becomes
# part of the "translation" and poisons every downstream metric, so remove it
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
    """One translation call. ``ok=False`` means the harness should record a
    failure for this case rather than silently scoring the fallback text."""

    text: str
    latency_ms: float
    ok: bool = True
    error: str | None = None
    raw: str | None = None
    attempts: int = 1
    stripped_thinking: bool = False
    model: str = ""

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "latency_ms": round(self.latency_ms, 1),
            "ok": self.ok,
            "error": self.error,
            "attempts": self.attempts,
            "stripped_thinking": self.stripped_thinking,
            "model": self.model,
        }


class Translator(Protocol):
    """The one model seam. Implementations must be side-effect free."""

    name: str

    def translate(self, text: str, src: str, tgt: str) -> TranslationResult: ...


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
    """Translator backed by any Ollama-served model."""

    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
        temperature: float | None = None,
        num_predict: int | None = None,
    ) -> None:
        self.model = model or config.translate_model()
        self.base_url = (base_url or config.translate_base_url()).rstrip("/")
        self.timeout = timeout if timeout is not None else config.translate_timeout()
        self.temperature = (
            temperature if temperature is not None else config.translate_temperature()
        )
        self.num_predict = (
            num_predict if num_predict is not None else config.translate_num_predict()
        )
        self.name = self.model
        # Set False once the server rejects the top-level "think" field, so a
        # single probe covers the whole run instead of one per call.
        self._supports_think_flag = True

    def _payload(self, text: str, src: str, tgt: str, with_think: bool) -> dict:
        system = _SYSTEM.format(
            src_name=config.LANGUAGES.get(src, src),
            tgt_name=config.LANGUAGES.get(tgt, tgt),
        )
        payload: dict = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": text},
            ],
            "stream": False,
            "keep_alive": "30m",
            "options": {
                "temperature": self.temperature,
                "num_predict": self.num_predict,
            },
        }
        if with_think:
            payload["think"] = False
        return payload

    def translate(self, text: str, src: str, tgt: str) -> TranslationResult:
        if src == tgt or not text or not text.strip():
            return TranslationResult(text=text, latency_ms=0.0, ok=True, model=self.model)

        last_error: str | None = None
        started = time.perf_counter()

        # Retry once: the Ollama endpoint is a shared remote proxy that throws
        # transient 502s/timeouts mid-run. One flaky call must not lose the
        # case -- the same reasoning as the archived sql_agent eval harness.
        for attempt in range(1, 3):
            try:
                payload = self._payload(text, src, tgt, self._supports_think_flag)
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(f"{self.base_url}/api/chat", json=payload)
                if resp.status_code == 400 and self._supports_think_flag:
                    # Older Ollama builds reject the "think" field outright.
                    # Drop it for the rest of the run and retry immediately;
                    # _clean() still removes any trace that leaks through.
                    self._supports_think_flag = False
                    continue
                resp.raise_for_status()
                raw = resp.json()["message"]["content"]
                cleaned, had_thinking = _clean(raw)
                elapsed = (time.perf_counter() - started) * 1000.0
                if not cleaned:
                    return TranslationResult(
                        text="", latency_ms=elapsed, ok=False,
                        error="empty translation after cleaning",
                        raw=raw, attempts=attempt,
                        stripped_thinking=had_thinking, model=self.model,
                    )
                return TranslationResult(
                    text=cleaned, latency_ms=elapsed, ok=True, raw=raw,
                    attempts=attempt, stripped_thinking=had_thinking,
                    model=self.model,
                )
            except Exception as exc:  # noqa: BLE001 - record, never abort the run
                last_error = f"{type(exc).__name__}: {exc}"

        elapsed = (time.perf_counter() - started) * 1000.0
        return TranslationResult(
            text=text,  # fall back to source so the pipeline still runs
            latency_ms=elapsed, ok=False, error=last_error, attempts=2,
            model=self.model,
        )


class IdentityTranslator:
    """Returns input unchanged. Used by the unit tests to prove that
    EVAL_TRANSLATE_MODEL is the only model seam in the harness."""

    name = "identity"

    def translate(self, text: str, src: str, tgt: str) -> TranslationResult:
        return TranslationResult(text=text, latency_ms=0.0, ok=True, model="identity")


def warmup(translator: Translator) -> float:
    """Prime the model so the first measured call does not absorb a 60-80s cold
    start (mirrors the startup warm-up at backend/main.py:125-134). Returns the
    warm-up latency in ms, which is reported but never scored."""
    return translator.translate("Report status", "en", "fr").latency_ms
