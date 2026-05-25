# llm_service.py -- Async Ollama client: LLM intent/entity extraction + conversational fallback.
# Model roles:
#   OLLAMA_EXTRACT_MODEL  (default: phi3:mini)      — intent/entity extraction + fallback chat
#   OLLAMA_MODEL          (default: phi3:mini)      — conversational fallback / unknown intent
#   comparative analysis summaries use OLLAMA_COMPARE_MODEL (mistral:latest) via xbrl_comparator.py
# Env vars: OLLAMA_BASE_URL, OLLAMA_EXTRACT_MODEL, OLLAMA_MODEL, OLLAMA_TIMEOUT

from __future__ import annotations

import json
import logging
import os
import time

import httpx

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL:      str   = os.getenv("OLLAMA_BASE_URL",      "http://127.0.0.1:11434")
OLLAMA_EXTRACT_MODEL: str   = os.getenv("OLLAMA_EXTRACT_MODEL", "phi3:mini")       # intent/entity extraction
OLLAMA_MODEL:         str   = os.getenv("OLLAMA_MODEL",         "phi3:mini")       # conversational fallback
REQUEST_TIMEOUT:      float = float(os.getenv("OLLAMA_TIMEOUT",  "180"))            # 180 s to survive cold load

# Keep models resident in memory between requests — avoids 60-80 s cold-start penalty.
_KEEP_ALIVE: str = os.getenv("OLLAMA_KEEP_ALIVE", "30m")

# ---------------------------------------------------------------------------
# LLM extraction prompt — instructs the model to return structured JSON only.
# ---------------------------------------------------------------------------
_EXTRACT_SYSTEM_PROMPT = """\
You are an intent and entity extractor for a Report Management System.
Analyze the user's message and respond ONLY with a single valid JSON object — no prose, no markdown.

Valid intents:
  "get_status"        — user wants to check the status/progress/state of a report
  "generate_instance" — user wants to generate/create/run/trigger/kick off a new report instance
  "schedule_report"   — user wants to schedule a report to run at a specific future date and time
  "compare_reports"   — user wants to compare two instances/periods of a report, see variance/differences
                        triggers: compare, variance, difference, vs, versus, side by side, contrast
  "query_database"    — user wants to fetch, retrieve, show, list, or analyse data from the Oracle database
                        triggers: show data, get data, fetch records, list transactions, NPA data, how many,
                        what is the value, retrieve from database, query, select, display records,
                        any banking metric (NPA, CAR, SLR, CRR, SMA, exposure, provision, capital)
  "unknown"           — greeting, small talk, thanks, help, or anything unrelated to reports

Entities to extract:
  "report_name"    : the report or institution identifier mentioned. This can be a report code (e.g. "CIMS_RAQ", "RAQ", "CIMS_MONTHLY"), a bank/institution prefix (e.g. "HDFC", "APBL", "ICICI", "SBI"), or any non-generic proper noun. Extract it even if it looks like a bank name. null only if truly absent.
  "reporting_date" : the period/reporting date for generate_instance (raw text as written by user). null if not present.
  "schedule_date"  : the date to schedule the report run (raw text as written). null if not present.
  "schedule_time"  : the time to run the scheduled report (raw text as written, e.g. "4 PM", "16:00"). null if not present.

Rules:
  - For "schedule_report", extract both schedule_date and schedule_time when present.
  - For "generate_instance", extract reporting_date (not schedule_date/schedule_time).
  - If a time expression is present alongside a generate intent, reclassify to "schedule_report".
  - For "compare_reports", extract the bank name, institution code, or report code as report_name (e.g. "HDFC", "APBL", "CIMS_RAQ"). Never return null for report_name when the user clearly names something.
  - Preserve the exact date/time text the user wrote — do not reformat.
  - Output ONLY the JSON object, nothing else.

Examples for compare_reports:
  "compare HDFC"             → {"intent":"compare_reports","report_name":"HDFC","reporting_date":null,"schedule_date":null,"schedule_time":null}
  "compare HDFC reports"     → {"intent":"compare_reports","report_name":"HDFC","reporting_date":null,"schedule_date":null,"schedule_time":null}
  "compare APBL instances"   → {"intent":"compare_reports","report_name":"APBL","reporting_date":null,"schedule_date":null,"schedule_time":null}
  "variance analysis of RAQ" → {"intent":"compare_reports","report_name":"RAQ","reporting_date":null,"schedule_date":null,"schedule_time":null}
  "compare CIMS_RAQ"         → {"intent":"compare_reports","report_name":"CIMS_RAQ","reporting_date":null,"schedule_date":null,"schedule_time":null}

Examples for query_database:
  "show NPA data for March 2025"          → {"intent":"query_database","report_name":null,"reporting_date":null,"schedule_date":null,"schedule_time":null}
  "what is the gross NPA for Q1 FY2024"   → {"intent":"query_database","report_name":null,"reporting_date":null,"schedule_date":null,"schedule_time":null}
  "list all bank codes with CAR below 12" → {"intent":"query_database","report_name":null,"reporting_date":null,"schedule_date":null,"schedule_time":null}
  "fetch exposure data from database"     → {"intent":"query_database","report_name":null,"reporting_date":null,"schedule_date":null,"schedule_time":null}
  "retrieve SLR figures for last quarter" → {"intent":"query_database","report_name":null,"reporting_date":null,"schedule_date":null,"schedule_time":null}

JSON schema:
{
  "intent":         "<intent>",
  "report_name":    "<name or null>",
  "reporting_date": "<date text or null>",
  "schedule_date":  "<date text or null>",
  "schedule_time":  "<time text or null>"
}



""".strip()

_CHAT_SYSTEM_PROMPT = """\
You are a Report Assistant. You help users with:
- Report status checks
- Generating new report instances
- Scheduling reports

Rules:
- Greet the user warmly if they say hello/hi/thanks.
- If the user asks something report-related but vague, guide them to be specific.
- If the user asks something completely unrelated to reports, politely say you can only help with report queries and give one example.
- Keep replies to 1-3 sentences. No bullet lists unless listing examples.
""".strip()


async def _call_ollama(prompt: str, system: str) -> str:
    payload = {
        "model":      OLLAMA_MODEL,
        "messages":   [
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ],
        "stream":     False,
        "keep_alive": _KEEP_ALIVE,
        "options": {
            "temperature": 0.1,
            "num_predict": 256,
        },
    }

    logger.debug(
        "[LLM_CALL] model=%s endpoint=%s/api/chat prompt_len=%d keep_alive=%s",
        OLLAMA_MODEL, OLLAMA_BASE_URL, len(prompt), _KEEP_ALIVE,
    )
    _t0 = time.monotonic()
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        resp = await client.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json=payload,
        )
        resp.raise_for_status()

    _elapsed = time.monotonic() - _t0
    content: str = resp.json()["message"]["content"]
    logger.info(
        "[PERF] operation=llm_chat model=%s duration=%.2fs response_len=%d",
        OLLAMA_MODEL, _elapsed, len(content),
    )
    logger.debug("[LLM_RESPONSE] content_preview=%r", content[:200])
    return content


async def extract_intent_entities_llm(user_query: str) -> dict:
    """Call Ollama to extract intent and entities as structured JSON.

    Returns a dict with keys: intent, report_name, reporting_date, schedule_date, schedule_time.
    Raises httpx or json errors on failure — caller must handle.
    """
    payload = {
        "model":      OLLAMA_EXTRACT_MODEL,
        "messages":   [
            {"role": "system", "content": _EXTRACT_SYSTEM_PROMPT},
            {"role": "user",   "content": user_query},
        ],
        "stream":     False,
        "format":     "json",
    }

    logger.debug(
        "[LLM_EXTRACT_CALL] model=%s endpoint=%s/api/chat keep_alive=%s",
        OLLAMA_EXTRACT_MODEL, OLLAMA_BASE_URL, _KEEP_ALIVE,
    )
    _t0 = time.monotonic()
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        resp = await client.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json=payload,
        )
        resp.raise_for_status()

    _elapsed = time.monotonic() - _t0
    content: str = resp.json()["message"]["content"]
    logger.info(
        "[PERF] operation=llm_extract model=%s duration=%.2fs",
        OLLAMA_EXTRACT_MODEL, _elapsed,
    )
    logger.debug("[LLM_EXTRACT_RAW] content=%r", content)
    return json.loads(content)


async def chat_response(user_message: str) -> str:
    return await _call_ollama(prompt=user_message, system=_CHAT_SYSTEM_PROMPT)