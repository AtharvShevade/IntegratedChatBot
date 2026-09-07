"""One call, three models, byte-identical request shape.

The request is built to match backend/services/llm_service.py::
extract_intent_entities_llm exactly -- same system prompt (imported, never
copied, so it cannot drift), same `format: "json"`, same temperature 0.0, same
single-user-message shape, no history. The ONLY thing that differs between
arms is `model` and the base URL that serves it.

The prompt is imported rather than duplicated on purpose: a copied prompt that
falls behind the real one turns a benchmark into fiction.
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from backend.services.llm_service import _EXTRACT_SYSTEM_PROMPT  # noqa: E402

# The arms. `local` here means "the Ollama daemon on this machine", which is
# how a -cloud tag is reached -- the daemon proxies it to ollama.com; the model
# itself never lands on disk.
DEPLOYED_BASE = "http://3.109.51.228/OllamaProxy"
CLOUD_BASE = "http://127.0.0.1:11434"


def extract(query: str, model: str, base_url: str, timeout: float = 120.0) -> dict:
    """Run one extraction. Never raises -- a failure IS a result worth scoring."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": _EXTRACT_SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ],
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.0},
    }
    started = time.perf_counter()
    try:
        resp = httpx.post(f"{base_url}/api/chat", json=payload, timeout=timeout)
        elapsed = (time.perf_counter() - started) * 1000.0
        if resp.status_code != 200:
            return {"ok": False, "latency_ms": elapsed, "error": f"http {resp.status_code}",
                    "strict_json_ok": False, "raw": resp.text[:400], "parsed": None}
        body = resp.json()
        if "error" in body:
            return {"ok": False, "latency_ms": elapsed, "error": str(body["error"])[:400],
                    "strict_json_ok": False, "raw": None, "parsed": None}
        content = body["message"]["content"]
    except Exception as exc:                        # noqa: BLE001 - any failure is data
        return {"ok": False, "latency_ms": (time.perf_counter() - started) * 1000.0,
                "error": f"{type(exc).__name__}: {exc}"[:400], "strict_json_ok": False, "raw": None, "parsed": None}

    # Two parses, because they answer two different questions.
    #
    # STRICT is literally what backend/services/llm_service.py does today:
    # `json.loads(content)`, no cleanup. If that raises, the deployed pipeline
    # raises too, and the request fails for a real user. gemma4:31b-cloud
    # ignores Ollama's `format: "json"` and fences its output in ```json, so
    # this distinction is not hypothetical -- it decides whether the model is
    # a drop-in or needs a code change first.
    #
    # LENIENT strips the fence. It measures the model's ANSWER rather than its
    # packaging, which is what "is this model smarter?" actually asks.
    strict_ok = True
    try:
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise ValueError("top-level JSON is not an object")
    except Exception:                               # noqa: BLE001
        strict_ok = False
        parsed = _lenient(content)

    if parsed is None:
        return {"ok": False, "latency_ms": elapsed, "error": "unparsable json",
                "strict_json_ok": False, "raw": content[:1000], "parsed": None}

    return {"ok": True, "latency_ms": elapsed, "error": None,
            "strict_json_ok": strict_ok, "raw": content[:2000], "parsed": parsed}


_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.S)


def _lenient(content: str) -> dict | None:
    """Recover a JSON object from fenced or prose-padded output."""
    fenced = _FENCE.search(content)
    candidates = ([fenced.group(1)] if fenced else [])
    start, end = content.find("{"), content.rfind("}")
    if start != -1 and end > start:
        candidates.append(content[start:end + 1])
    for text in candidates:
        try:
            value = json.loads(text)
        except Exception:                           # noqa: BLE001
            continue
        if isinstance(value, dict):
            return value
    return None
