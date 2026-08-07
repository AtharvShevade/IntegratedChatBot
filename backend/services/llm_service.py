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
import re
import time

import httpx

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL:      str   = os.getenv("OLLAMA_BASE_URL",      "http://127.0.0.1:11434")
OLLAMA_EXTRACT_MODEL: str   = os.getenv("OLLAMA_EXTRACT_MODEL", "phi3:mini")       # intent/entity extraction
OLLAMA_MODEL:         str   = os.getenv("OLLAMA_MODEL",         "phi3:mini")       # conversational fallback
REQUEST_TIMEOUT:      float = float(os.getenv("OLLAMA_TIMEOUT",          "180"))   # 180 s for chat/summary calls
EXTRACT_TIMEOUT:      float = float(os.getenv("OLLAMA_EXTRACT_TIMEOUT",  "30"))    # 30 s for fast intent extraction
# _call_ollama() backs disambiguate_intent/classify_conversational_intent/chat_response
# — the "I didn't understand / let me answer generally" fallback path a plain-worded
# question (e.g. "am i an admin", "show my last 5 logins") falls into whenever the
# db_qa regex/keyword classifier misses. Self-test (doc/INTENT_GAP_ANALYSIS.md) found
# these calls hanging 60s+ because they inherited REQUEST_TIMEOUT (300s in this env's
# .env). CHAT_FALLBACK_TIMEOUT caps just this path so a miss fails fast with a helpful
# message instead of hanging the whole request — independent of REQUEST_TIMEOUT, which
# stays long for calls that legitimately need it (comparative summaries, etc.).
CHAT_FALLBACK_TIMEOUT: float = float(os.getenv("OLLAMA_CHAT_FALLBACK_TIMEOUT", "12"))

# Keep models resident in memory between requests — avoids 60-80 s cold-start penalty.
_KEEP_ALIVE: str = os.getenv("OLLAMA_KEEP_ALIVE", "30m")

# ---------------------------------------------------------------------------
# LLM extraction prompt — instructs the model to return structured JSON only.
# Now includes both REPORT intents and DATABASE Q&A intents.
# ---------------------------------------------------------------------------
_EXTRACT_SYSTEM_PROMPT = """\
You are an intent and entity extractor for a Report Management System + Database Q&A Assistant.
Analyze the user's message and respond ONLY with a single valid JSON object — no prose, no markdown.

Valid intents:
  # ─ REPORT INTENTS (existing) ─────────────────────────────────────────
  "get_status"        — user wants to check the status/progress/state of a report
  "generate_instance" — user wants to generate/create/run/trigger/kick off a new report instance
  "schedule_report"   — user wants to schedule a report to run at a specific future date and time
  "compare_reports"   — user wants to compare two instances/periods of a report, see variance/differences
                        triggers: compare, comparative, comparative analysis, comparison,
                                  compare instances, compare reports, variance, difference,
                                  vs, versus, side by side, contrast, analyse, analysis
  "query_database"    — user wants to fetch, retrieve, show, list, or analyse data from the Oracle database
                        triggers: show data, get data, fetch records, list transactions, NPA data, how many,
                        what is the value, retrieve from database, query, select, display records,
                        any banking metric (NPA, CAR, SLR, CRR, SMA, exposure, provision, capital)
  
  # ─ DATABASE Q&A INTENTS (new) ────────────────────────────────────────
  "db_my_profile"       — user asking about their own profile/details/who am i/tell me about myself
  "db_my_department"    — user asking what department they belong to
  "db_my_role"          — user asking what role/designation they have
  "db_my_permissions"   — user asking what they can do/what access they have
  "db_list_users"       — user asking for list of users (active/inactive/all)
  "db_list_departments" — user asking for list of departments in system
  "db_list_roles"       — user asking for roles available
  "db_user_info"        — user asking about specific user details
  "db_department_info"  — user asking about specific department
  
  "unknown"           — greeting, small talk, thanks, help, or anything unrelated

Entities to extract:
  "report_name"       : the report or institution identifier. null if not present.
  "reporting_date"    : the period/reporting date for generate_instance. null if not present.
  "schedule_date"     : the date to schedule the report run. null if not present.
  "schedule_time"     : the time to run the scheduled report. null if not present.
  "target_user"       : username or user ID if asking about specific user. null if not present.
  "target_department" : department name if asking about specific department. null if not present.
  "target_role"       : role name if asking about specific role. null if not present.
  "query_type"        : for list queries: "active", "inactive", "all", "details", "count". null if not present.

Intent routing priority — apply in this order, stop at first match:
  1. WORKFLOW  — status/generate/schedule/compare keywords + a report context → use report intents
  2. APP Q&A   — user/department/role/permission/audit/log/return/submission questions → use db_* intents
               IMPORTANT: XML domain wins over action verb — "how many departments" → db_list_departments,
               NOT query_database, even though it contains "how many"
  3. SQL AGENT — Oracle analytics, banking/regulatory metrics with NO XML domain entity →
               use "query_database". This is NOT limited to a fixed list of terms — ANY
               question asking for a specific financial/regulatory data point, aggregate,
               or metric from a report/return/section (a number, amount, balance, ratio,
               or value, however it's phrased — NPA, SLR, CRR, CAR, loans, deposits,
               exposure, provision, transactions, derivatives, notional principal,
               advances, investments, yields, etc. are just examples, not an exhaustive
               list) qualifies, as long as the query does NOT mention
               users/departments/roles/returns-metadata/permissions/audits
  4. UNKNOWN   — greetings, help, or fully unrelated messages

Rules for all intents:
  - Workflow takes priority: if BOTH workflow keywords (status/generate/schedule/compare) AND
    banking metrics (NPA, loan, CAR …) appear together, use the WORKFLOW intent, not query_database.
  - For report intents, follow existing extraction rules (see examples below)
  - For DB Q&A list intents, extract query_type to indicate filter type
  - For DB Q&A info intents, extract target_user/target_department/target_role
  - Preserve exact date/time text as written by user
  - Output ONLY the JSON object, nothing else

Examples for DB Q&A intents:
  "What department am I in?"              → {"intent":"db_my_department","target_department":null,"query_type":null,...}
  "List all departments"                  → {"intent":"db_list_departments","target_department":null,"query_type":"all",...}
  "Who are the active users?"             → {"intent":"db_list_users","query_type":"active",...}
  "Tell me about user Alice"              → {"intent":"db_user_info","target_user":"Alice",...}
  "What's my role?"                       → {"intent":"db_my_role",...}
  "What can I do?"                        → {"intent":"db_my_permissions",...}
  "Show all inactive users"               → {"intent":"db_list_users","query_type":"inactive",...}
  "Who are all the users?"                → {"intent":"db_list_users","query_type":"all",...}
  "Department info"                       → {"intent":"db_list_departments",...}

Examples for report intents (existing):
  "Check status of my report"             → {"intent":"get_status","report_name":null,"reporting_date":null,"schedule_date":null,"schedule_time":null,"target_user":null,"target_department":null,"target_role":null,"query_type":null}
  "Generate CIMS_RAQ report"              → {"intent":"generate_instance","report_name":"CIMS_RAQ","reporting_date":null,"schedule_date":null,"schedule_time":null,"target_user":null,"target_department":null,"target_role":null,"query_type":null}
  "Show NPA data"                         → {"intent":"query_database","report_name":null,"reporting_date":null,"schedule_date":null,"schedule_time":null,"target_user":null,"target_department":null,"target_role":null,"query_type":null}
  "compare HDFC"                          → {"intent":"compare_reports","report_name":"HDFC","reporting_date":null,"schedule_date":null,"schedule_time":null,"target_user":null,"target_department":null,"target_role":null,"query_type":null}
  "give me comparative analysis for HDFC" → {"intent":"compare_reports","report_name":"HDFC","reporting_date":null,"schedule_date":null,"schedule_time":null,"target_user":null,"target_department":null,"target_role":null,"query_type":null}
  "comparative analysis of RAQ"           → {"intent":"compare_reports","report_name":"RAQ","reporting_date":null,"schedule_date":null,"schedule_time":null,"target_user":null,"target_department":null,"target_role":null,"query_type":null}
  "compare two instances of CIMS_RAQ"     → {"intent":"compare_reports","report_name":"CIMS_RAQ","reporting_date":null,"schedule_date":null,"schedule_time":null,"target_user":null,"target_department":null,"target_role":null,"query_type":null}

JSON schema (complete):
{
  "intent":              "<intent>",
  "report_name":        "<name or null>",
  "reporting_date":     "<date text or null>",
  "schedule_date":      "<date text or null>",
  "schedule_time":      "<time text or null>",
  "target_user":        "<username or null>",
  "target_department":  "<dept name or null>",
  "target_role":        "<role name or null>",
  "query_type":         "<active|inactive|all|details|count or null>"
}



""".strip()

_CHAT_SYSTEM_PROMPT = """\
You are a Report Assistant. You help users with:
- Report status checks
- Generating new report instances
- Scheduling reports
- Database queries and information about users, departments, and roles

Rules:
- Greet the user warmly if they say hello/hi/thanks.
- If the user asks something report-related but vague, guide them to be specific.
- If the user asks something completely unrelated to reports, politely say you can only help with report queries and system information, and give one example.
- Keep replies to 1-3 sentences. No bullet lists unless listing examples.
""".strip()

_CLASSIFY_CONVERSATIONAL_SYSTEM_PROMPT = """\
You are a classifier for conversational user messages for a report assistant.
Respond with exactly one word: greeting, acknowledgement, or unsupported.

Definitions:
  greeting       — ONLY a social opener with no request at all, e.g. "hi", "hello",
                   "good morning". Nothing else qualifies.
  acknowledgement — ONLY a short reaction to something the assistant just said, with
                   NO new request and NO data/report/metric/entity mentioned, e.g.
                   "thanks", "ok", "got it", "no", "sounds good".
  unsupported    — EVERYTHING ELSE. This includes any message that names, asks for,
                   or references a report, return, metric, amount, value, date, field,
                   section, table, or any specific data point — even if short, terse,
                   incomplete, or oddly phrased, and even if you don't recognise the
                   specific term used. When in doubt between acknowledgement and
                   unsupported, choose unsupported.

Examples:
  "hi"                                              -> greeting
  "thanks"                                           -> acknowledgement
  "ok sounds good"                                   -> acknowledgement
  "Derivative notional principal from ALE domestic"  -> unsupported
  "gross NPA for Q1"                                 -> unsupported
  "total loan assets"                                -> unsupported
  "what is my role"                                  -> unsupported
  "show me the report status"                        -> unsupported

Only output the one word. Do not include any explanation, punctuation, or extra text.
""".strip()


async def _call_ollama(
    prompt: str,
    system: str,
    history: list[dict] | None = None,
    model: str | None = None,
    temperature: float = 0.1,
) -> str:
    history_msgs = [
        {"role": item["role"], "content": item["text"]}
        for item in (history or [])
        if item.get("role") in ("user", "assistant") and item.get("text")
    ]
    payload = {
        "model":      model or OLLAMA_MODEL,
        "messages":   [
            {"role": "system", "content": system},
            *history_msgs,
            {"role": "user",   "content": prompt},
        ],
        "stream":     False,
        "keep_alive": _KEEP_ALIVE,
        "options": {
            "temperature": temperature,
            "num_predict": 256,
        },
    }

    logger.debug(
        "[LLM_CALL] model=%s endpoint=%s/api/chat prompt_len=%d keep_alive=%s timeout=%.0fs",
        OLLAMA_MODEL, OLLAMA_BASE_URL, len(prompt), _KEEP_ALIVE, CHAT_FALLBACK_TIMEOUT,
    )
    _t0 = time.monotonic()
    # CHAT_FALLBACK_TIMEOUT (not REQUEST_TIMEOUT) — see its definition above for why
    # this call in particular needs a short leash.
    async with httpx.AsyncClient(timeout=CHAT_FALLBACK_TIMEOUT) as client:
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


async def disambiguate_intent(user_message: str, candidates: list[tuple[str, str]]) -> str | None:
    """Ask the LLM to pick ONE of a small set of pre-narrowed intent
    candidates for *user_message* — used only when the embedding-similarity
    tier (backend.db_qa.intents.embedding_index) finds 2-3 close-scoring
    candidates and can't confidently pick a winner on its own.

    This is deliberately NOT a general classifier: candidates is always a
    short list (2-3 items) already narrowed by embedding similarity, which
    is the case a small model like phi3:mini is actually reliable at —
    unlike classifying cold against the full ~55-intent taxonomy.

    Parameters
    ----------
    user_message:
        The raw user query.
    candidates:
        [(intent_value, description), ...] — intent_value is the exact
        Intent.value string the model must echo back verbatim if it picks
        that option (e.g. "user_field", not a paraphrase).

    Returns
    -------
    The chosen intent_value if the model picked one of the given
    candidates, or None if it declined ("none") or returned anything
    unexpected — callers should treat None the same as "still no
    confident match" and fall through to the next tier.
    """
    if not candidates:
        return None

    valid_values = {value for value, _ in candidates}
    options_block = "\n".join(f'  "{value}" — {desc}' for value, desc in candidates)
    system = (
        "You are a narrow intent disambiguator. The user's message is known to be "
        "close to one of these specific options:\n"
        f"{options_block}\n"
        '  "none" — the message does not clearly match any of the above\n\n'
        "Respond with EXACTLY ONE of the option values shown above (in quotes), or \"none\". "
        "Output ONLY that value, no explanation, no punctuation, no extra text."
    )

    content = await _call_ollama(
        prompt=user_message,
        system=system,
        model=OLLAMA_EXTRACT_MODEL,
    )
    normalized = content.strip().strip('"').strip()

    if normalized in valid_values:
        return normalized
    if normalized == "none" or normalized.lower().startswith("none"):
        return None

    # Small models sometimes ignore "output ONLY the value" and echo back
    # the option's description, or wrap the value in extra prose — fall
    # back to a whole-word search for one of the candidate values
    # anywhere in the response, rather than requiring an exact match.
    # Ambiguous only if none, or more than one, candidate value appears
    # (picking arbitrarily between two echoed values would be worse than
    # declining).
    found = [v for v in valid_values if re.search(rf"\b{re.escape(v)}\b", normalized)]
    if len(found) == 1:
        return found[0]

    logger.warning(
        "[LLM_DISAMBIGUATE_UNEXPECTED] response=%r normalized=%r candidates=%r",
        content, normalized, valid_values,
    )
    return None


async def classify_conversational_intent(user_message: str, history: list[dict] | None = None) -> str:
    content = await _call_ollama(
        prompt=user_message,
        system=_CLASSIFY_CONVERSATIONAL_SYSTEM_PROMPT,
        history=history,
        model=OLLAMA_EXTRACT_MODEL,
        temperature=0.0,
    )
    normalized = re.sub(r'[^a-z]', '', content.strip().lower())
    if normalized in {"greeting", "acknowledgement", "unsupported"}:
        return normalized
    logger.warning(
        "[LLM_CLASSIFIER_UNEXPECTED] response=%r normalized=%r",
        content,
        normalized,
    )
    return "unsupported"


async def extract_intent_entities_llm(user_query: str, history: list[dict] | None = None) -> dict:
    """Call Ollama to extract intent and entities as structured JSON.

    Returns a dict with keys: intent, report_name, reporting_date, schedule_date, schedule_time,
    target_user, target_department, target_role, query_type.
    
    Intents can be either REPORT intents (get_status, generate_instance, etc.) or 
    DATABASE Q&A intents (db_my_profile, db_list_users, etc.).
    
    Raises httpx or json errors on failure — caller must handle.
    Passing *history* (last 6-7 messages) lets the LLM resolve references like
    'it', 'that report', 'the same one' across turns.
    """
    history_msgs = [
        {"role": item["role"], "content": item["text"]}
        for item in (history or [])
        if item.get("role") in ("user", "assistant") and item.get("text")
    ]
    payload = {
        "model":      OLLAMA_EXTRACT_MODEL,
        "messages":   [
            {"role": "system", "content": _EXTRACT_SYSTEM_PROMPT},
            *history_msgs,
            {"role": "user",   "content": user_query},
        ],
        "stream":     False,
        "format":     "json",
        "options": {
            "temperature": 0.0,
        },
    }

    logger.debug(
        "[LLM_EXTRACT_CALL] model=%s endpoint=%s/api/chat keep_alive=%s timeout=%.0fs",
        OLLAMA_EXTRACT_MODEL, OLLAMA_BASE_URL, _KEEP_ALIVE, EXTRACT_TIMEOUT,
    )
    _t0 = time.monotonic()
    async with httpx.AsyncClient(timeout=EXTRACT_TIMEOUT) as client:
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


async def chat_response(user_message: str, history: list[dict] | None = None) -> str:
    return await _call_ollama(prompt=user_message, system=_CHAT_SYSTEM_PROMPT, history=history)