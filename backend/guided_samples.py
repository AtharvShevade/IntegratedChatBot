# backend/guided_samples.py
#
# Sample return names / ReturnIds quoted in the guided prompts, per chatbot
# version. The values live in backend/guided_samples.json so they can be changed
# without touching code or the frontend (the frontend only displays the
# response_text the backend sends).
#
# Version selection reuses version_config (APP_VERSION): 6.0 -> the "6.0"
# section, anything else -> "5.5". A missing, unreadable or malformed file, or a
# missing entry, falls back to the built-in defaults below (the wording the
# prompt had before this file existed), so the guided flow never breaks.

from __future__ import annotations

import json
import logging
import os
import threading

from backend import version_config

logger = logging.getLogger(__name__)

__all__ = ["get_samples", "report_name_prompt", "active_version_key"]

_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "guided_samples.json")

# What the prompt said before it became configurable (5.5 wording).
_DEFAULTS: dict[str, list[str]] = {
    "check_report_status": ["CIMS_ROR", "R149", "RAQ"],
    "generate_instance": ["CIMS_FormGPB", "R009"],
    "schedule_report": ["CIMS_RAQ", "R162"],
    "comparative_analysis": ["CIMS_RAQ", "R009", "RAQ"],
}

_MAX_SAMPLES = 6
_MAX_LEN = 200

_lock = threading.Lock()
_cache: tuple[float, dict] | None = None      # (mtime, parsed file)


def active_version_key() -> str:
    """The JSON section for the running chatbot: "6.0" or "5.5"."""
    return "6.0" if version_config.IS_V6 else "5.5"


def _load() -> dict:
    """The parsed file, cached until its modified time changes; {} on any problem."""
    global _cache
    try:
        mtime = os.path.getmtime(_PATH)
    except OSError:
        return {}
    with _lock:
        if _cache is not None and _cache[0] == mtime:
            return _cache[1]
    try:
        with open(_PATH, "r", encoding="utf-8-sig") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            raise ValueError("top level is not an object")
    except (OSError, ValueError) as exc:
        logger.warning("[GUIDED_SAMPLES] cannot use %s: %s - using built-in samples", _PATH, exc)
        return {}
    with _lock:
        _cache = (mtime, data)
    return data


def _clean(value) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        text = str(item).strip() if isinstance(item, (str, int)) else ""
        if text and len(text) <= _MAX_LEN and text not in out:
            out.append(text)
    return out[:_MAX_SAMPLES]


def get_samples(action: str, version: str | None = None) -> list[str]:
    """Ordered sample names for *action* under *version* (default: the running one)."""
    section = _load().get(version or active_version_key())
    samples = _clean(section.get(action)) if isinstance(section, dict) else []
    if samples:
        return samples
    logger.info("[GUIDED_SAMPLES] no samples for action=%s version=%s - using built-in", action, version or active_version_key())
    return list(_DEFAULTS.get(action, []))


def report_name_prompt(samples: list[str], compare: bool = False) -> str:
    """The guided "enter the report" prompt, in the exact wording it always had."""
    head = "Enter the report name, ReturnId, or short name" + (" to compare" if compare else "")
    if not samples:
        return head + ":"
    return f"{head} (e.g. {', '.join(samples)}):"
