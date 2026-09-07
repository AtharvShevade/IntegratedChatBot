"""LLM-as-judge scoring for translation quality (metric 1).

Two deliberate choices:

  * The judge model defaults to a DIFFERENT model than the one under test
    (EVAL_JUDGE_MODEL, default qwen2.5:14b). A model scoring its own
    translations is marking its own homework, and self-preference bias in
    LLM judges is well documented.

  * The judge is advisory, never a gate. It runs only with --judge, and its
    scores are reported alongside -- not folded into -- the PASS/CONDITIONAL/
    FAIL verdict, which rests on the objective checks in masking.py. A judge
    that is itself weak in Arabic or Hindi would otherwise quietly set the
    verdict. Calibrate it against the ~20% human spot-check before trusting it.
"""
from __future__ import annotations

import json
import re
import time

import httpx

from eval.multilingual import config

_SYSTEM = (
    "You are an impartial evaluator of machine translation for a banking "
    "regulatory reporting system. You are given a SOURCE text and a "
    "TRANSLATION. Score the translation on three axes, each an integer 1-5:\n"
    "  adequacy   - is all meaning of the source preserved, nothing added or lost?\n"
    "  fluency    - is it natural, grammatical, idiomatic in the target language?\n"
    "  terminology - are report names, codes, numbers, dates and regulatory "
    "terms carried over correctly and in an appropriate professional register?\n"
    "\n"
    "5 = flawless, 3 = usable with reservations, 1 = unusable.\n"
    "Respond with ONLY a JSON object and nothing else:\n"
    '{"adequacy": <int>, "fluency": <int>, "terminology": <int>, "note": "<short reason>"}'
)

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)
_THINK_RE = re.compile(r"<(think|thinking|reasoning)>.*?</\1>", re.DOTALL | re.IGNORECASE)


class Judge:
    def __init__(self, model: str | None = None, base_url: str | None = None,
                 timeout: float | None = None) -> None:
        self.model = model or config.judge_model()
        self.base_url = (base_url or config.ollama_base_url()).rstrip("/")
        self.timeout = timeout if timeout is not None else config.translate_timeout()

    def score(self, source: str, translation: str, src: str, tgt: str) -> dict:
        if not source or not translation:
            return {"error": "empty source or translation"}
        prompt = (
            f"SOURCE ({config.LANGUAGES.get(src, src)}):\n{source}\n\n"
            f"TRANSLATION ({config.LANGUAGES.get(tgt, tgt)}):\n{translation}"
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "keep_alive": "30m",
            "format": "json",
            "options": {"temperature": 0, "num_predict": 256},
        }
        started = time.perf_counter()
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(f"{self.base_url}/api/chat", json=payload)
            resp.raise_for_status()
            raw = _THINK_RE.sub("", resp.json()["message"]["content"])
            match = _JSON_RE.search(raw)
            if not match:
                return {"error": "no JSON in judge response", "raw": raw[:300]}
            parsed = json.loads(match.group(0))
        except Exception as exc:  # noqa: BLE001 - judging is advisory
            return {"error": f"{type(exc).__name__}: {exc}"}

        out: dict = {"judge_ms": round((time.perf_counter() - started) * 1000.0, 1)}
        for axis in ("adequacy", "fluency", "terminology"):
            value = parsed.get(axis)
            if isinstance(value, (int, float)) and 1 <= value <= 5:
                out[axis] = int(value)
        if isinstance(parsed.get("note"), str):
            out["note"] = parsed["note"][:300]
        return out
