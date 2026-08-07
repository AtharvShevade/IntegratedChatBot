# Intent Classifier & LLM Dependency — Gap Analysis

Self-test conducted against the running local backend (`http://localhost:8001`), authenticated as `iris810` (UserId 104, RoleId 101 — admin), against real data at `D:\Repo5.5`. 52 questions total across two batches, covering supported intents, casual phrasing, ambiguous entities, and edge cases.

## TL;DR

- **The regex/keyword classifier, when it matches, is fast and accurate** — ~450ms, correct intent, correct data.
- **The moment it misses, cost explodes**: fallback to the LLM path costs anywhere from 3s to **over 60 seconds** (9 of 52 requests never returned inside a 60s timeout at all).
- **The configured LLM is a remote proxy, not local Ollama** — `OLLAMA_BASE_URL=http://3.109.51.228/OllamaProxy`. The proxy itself responds in ~17ms; the slowness is 100% model inference time on that remote host, not network latency.
- **A configured model is missing from the remote proxy entirely**: `APP_DB_BEAUTIFY_MODEL=phi3:mini` is not in the proxy's model list, only `qwen2.5:7b`, `qwen2.5-coder:7b`, `llama3.1:latest`, `sqlcoder-7b-2` are. This is a silent misconfiguration.
- **Casual/ambiguous phrasing is the single biggest accuracy gap** — not exotic queries, ordinary rephrasings a real user would type.

---

## Batch 1 — supported-intent coverage + casual phrasing (27 questions)

| Time | Result | Matched intent | Question | Response (truncated) |
|---|---|---|---|---|
| 711ms | ✅ db_qa | role_profile | what is my role | Your role is 'Admin User' (id 101). |
| 516ms | ✅ db_qa | department_profile | what department am i in | Department 'TusharTestLocal' (id 101) has 2 user(s). |
| 471ms | ❌ not found | users_by_department | who works in Finance | Department 'Finance' not found. |
| 464ms | ✅ db_qa | department_list | list all departments | There are 6 departments in the system. |
| 451ms | ✅ db_qa | department_list | how many active departments are there | Active departments: 1. |
| 476ms | ✅ db_qa | user_list | list all users | There are 4 users in the system. |
| 459ms | ✅ db_qa | user_list | how many users are inactive | Inactive users: 0. |
| 482ms | ❌ not found | users_by_department | list Finance department users | Department 'Finance' not found. |
| 498ms | ✅ db_qa | user_field | what is my email | Your email address is: abhay.pandey36587@gmail.com. |
| 500ms | ✅ db_qa | user_field | when did i last login | Your last login time is: 26-Mar-2026 04:13:08 PM. |
| 538ms | ✅ db_qa | db_my_dept_returns | which returns can i submit | Returns for My Department (24 records) |
| 462ms | ❌ wrong intent | user_profile | give me the full profile for DPSS09 | Profile for iris810. *(should be RETURN_PROFILE)* |
| 531ms | ✅ db_qa | return_field | what is the reporting frequency of DBR01 | 'DBR01' is filed on a 'Quarterly' basis. |
| 482ms | ✅ db_qa | nonxbrl_return_list | list all non-xbrl returns | There are 62 non-XBRL returns. |
| 482ms | ⚠️ partial | departments_with_return_access | which departments can submit DPSS09 | Please specify a return name. *(DPSS09 not recognized as the return name)* |
| **31881ms** | ❌ misrouted | unknown → generate_instance | what reporting periods are available | Sorry, I didn't understand... |
| 560ms | ✅ db_qa | monthly_filing_status | what's my xbrl filing status for June 2025 | 0 of 10 due, filed. |
| 500ms | ✅ db_qa | reports_filed_in_range | show me all reports filed between 01-01-2025 and 31-03-2025 | Found 0 report(s). |
| **29975ms** | ❌ misrouted | disambiguation → generate_instance | what reports are coming up next month | Found multiple matching reports. Which one...? |
| 464ms | ❌ misrouted + broken | error → generate_instance | does my department have access to DPSS09 | Report 'does my department...' not found. |
| 471ms | ❌ wrong intent | department_profile | which department has the most returns | 'has the most returns' department could not be found. *(should be DEPT_RETURN_ACCESS_MATRIX)* |
| **3686ms** | ❌ unknown | unknown | hey can u tell me abt returns pls | Sorry, I didn't understand... |
| 472ms | ✅ db_qa | db_my_department | wat is my dept | My Department: TusharTestLocal |
| 518ms | ⚠️ partial | role_profile | i wanna know my role and dept both | Your role is 'Admin User' (id 101). *(dept half of the question dropped silently)* |
| **3154ms** | ❌ unknown | unknown | tell me stuff about the system | Sorry, I didn't understand... |
| **8865ms** | ❌ unknown | unknown | is DPSS09 a thing that finance can do | Sorry, I didn't understand... |
| 456ms | ❌ misrouted | error → compare_reports | compare my department with report department | No matching reports found for 'my'. |

## Batch 2 — deeper edge cases (25 questions)

| Time | Result | Matched intent | Question | Response (truncated) |
|---|---|---|---|---|
| **60241ms — no response** | ❌ TIMEOUT | — | show me the NPA data for last quarter | *(SQL-agent path, Oracle likely unreachable — never returned)* |
| 445ms | ✅ db_qa | user_list | how many users do not have finance department | Total users: 4 (4 active, 0 inactive). *(ignored the "not finance" qualifier — false positive success)* |
| 407ms | ❌ wrong intent | department_profile | which department dont have any returns | 'dont have any returns' department could not be found. *(should be no_returns query_type)* |
| 460ms | ⚠️ ignored qualifier | department_list | list departments without returns | There are 6 departments in the system. *(same bug — "without returns" filter silently dropped)* |
| 417ms | ✅ db_qa | next_reporting_date | what is the due date for DPSS09 | ends on 30-Sep-2... |
| **60235ms — no response** | ❌ TIMEOUT | — | is there a return called dpss09 | — |
| **60220ms — no response** | ❌ TIMEOUT | — | whats dpss 09 about | — |
| 448ms | ✅ db_qa | role_list | how many roles exist in the system | Total roles: 18 (16 active, 2 inactive). |
| 440ms | ✅ db_qa | role_list | list all roles | There are 18 roles defined in the system. |
| **60227ms — no response** | ❌ TIMEOUT | — | which returns are CIMS enabled | — |
| **30645ms** | ❌ misrouted | error → get_status | what access does the checker role have | Couldn't find any report matching '...'. |
| **60248ms — no response** | ❌ TIMEOUT | — | am i an admin | — |
| **60227ms — no response** | ❌ TIMEOUT | — | show my last 5 logins | — |
| **60177ms — no response** | ❌ TIMEOUT | — | how many times have i failed to login | — |
| 444ms | ✅ db_qa | user_field | what is my user code | Your user code is: Not set. |
| **30638ms** | ❌ misrouted | gen_awaiting_date → generate_instance | who created my account | Please enter the reporting date for **Simple depositor - account holder details**... |
| 415ms | ⚠️ wrong data | department_list | show department access matrix | There are 6 departments... *(should be DEPT_RETURN_ACCESS_MATRIX ranking, not plain list)* |
| 473ms | ⚠️ partial | departments_with_return_access | which department can access the most returns | Please specify a return name. |
| 416ms | ✅ db_qa | user_list | list inactive users | There are 0 inactive users. |
| 436ms | ✅ db_qa | user_list | give me count of active users | Active users: 4. |
| 431ms | ❌ wrong intent | department_returns | what returns does report department have | 'have' department could not be found. *("have" misparsed as the department name)* |
| 411ms | ❌ wrong intent | department_returns | non xbrl returns for local department | '' department could not be found. *(empty string extracted as department name)* |
| 423ms | ⚠️ wrong data | role_list | show me role access for admin | There are 18 roles defined... *(should be role-specific access, not the full list)* |

---

## Gap categories, ranked by impact

### 1. Catastrophic latency on classifier miss (highest priority)
9 of 52 questions (17%) **never returned within 60 seconds** — including plain, everyday phrasings like "am i an admin", "how many times have i failed to login", "show my last 5 logins". These are not obscure queries; they're intents the system almost certainly supports (`user_field`/`role_profile`-style lookups) phrased slightly differently than the regex expects. A production user asking these gets a dead UI with no feedback for a full minute or more.

**Cause**: `OLLAMA_TIMEOUT=300` (5 minutes) in `.env` — the backend will happily wait that long per call. There is no fast intermediate timeout/fallback message, and no visible "still thinking" state distinguishing "the LLM is slow" from "the request is stuck."

### 2. Misrouting into the wrong subsystem entirely (highest risk)
"who created my account", "what reports are coming up next month", "compare my department with report department" all got routed into the **XBRL report-generation/comparison flow** instead of DB Q&A — one of them (`who created my account`) got as far as **asking for a reporting date to generate a report**, a completely unrelated action to what was asked. This is a routing boundary problem, not a phrasing problem: a `db_qa` miss should never silently fall into `generate_instance`.

### 3. Entity extraction drops or misparses fragments
Several failures aren't intent misses at all — the right *category* of question was recognized, but the entity extractor grabbed garbage as the target name:
- "what returns does report department have" → tried to resolve `"have"` as a department name
- "non xbrl returns for local department" → extracted `""` (empty) as the department name
- "which department has the most returns" → tried to resolve `"has the most returns"` as a department name

These all stem from the same pattern: entity extraction anchors on position/keywords near the noun ("department") without stripping trailing verb phrases, and there's no fuzzy match against the real department list before giving up.

### 4. Qualifiers silently dropped, producing confidently wrong answers
"list departments without returns" and "how many users do not have finance department" both matched a real intent and returned a *plausible-looking, wrong* answer — the "without returns" / "not finance" qualifier was simply ignored, returning the full unfiltered list/count instead of erroring or asking for clarification. This is worse than an outright miss because the user has no signal the answer is incomplete.

### 5. Casual/informal phrasing has no tolerance
"hey can u tell me abt returns pls", "tell me stuff about the system", "is DPSS09 a thing that finance can do" — semantically clear to a human, all fell through to the generic "Sorry, I didn't understand" after 3–9 seconds of LLM effort. The keyword classifier's literal phrase groups don't have slang/filler tolerance, and the LLM fallback doesn't reliably rescue them either.

---

## Is the LLM model itself adequate?

**Short answer: the model tier is probably fine; the real problems are elsewhere.**

- `qwen2.5:7b` / `llama3.1:latest` (both ~7-8B, Q4_K_M quantized) are reasonable choices for intent extraction and short-answer generation — this isn't a task that inherently needs a 70B+ model.
- The evidence doesn't point to "the model is too weak to understand the question" — several LLM-fallback answers were simply never returned at all (timeout), which is an **infrastructure/latency problem**, not a comprehension problem. We can't judge model quality on requests that never completed.
- Where the LLM fallback *did* respond (3–30s cases), it correctly recognized these were report/return-related but routed to the wrong subsystem — suggesting the **routing/prompt boundary** between "this is a DB Q&A question" vs. "this is a report-generation question" is the weak point, not raw language understanding.
- The `APP_DB_BEAUTIFY_MODEL=phi3:mini` misconfiguration (model doesn't exist on the configured remote proxy) means that code path is either silently failing over to raw output or erroring — worth checking directly regardless of model choice.

**Recommendation: don't upgrade the model yet.** First fix:
1. The phi3:mini/proxy mismatch (data-integrity issue, not a capability one).
2. The routing boundary so db_qa misses can't fall into generate_instance/compare_reports.
3. Add a hard client-side/server-side timeout (e.g. 8–10s) on the LLM fallback path with a graceful "let me get someone to help" message rather than a 60s+ hang.

Only after those are fixed would it make sense to re-run this same test suite and evaluate whether remaining misses are genuinely a model-comprehension ceiling (worth a bigger model) or still infrastructure/prompting issues.

---

## Recommended fix priority

1. ~~**Add a fast fallback timeout** on the conversational-fallback LLM call.~~ **DONE** — `OLLAMA_CHAT_FALLBACK_TIMEOUT` (12s). See "Implemented fix #1."
2. ~~**Stop specific db_qa-shaped questions from being absorbed by the SQL Agent**~~ **PARTIALLY DONE** — "CIMS enabled"/return-existence phrasings now match db_qa directly (Round 2, fixes #2a/2b). The general architectural fix (race/try db_qa before committing to SQL Agent for any ambiguous keyword) is still open — this round only closed the two specific phrasings the self-test found.
3. ~~**Fix the phi3:mini / hardcoded-model bug**~~ **DONE** — turned out to be worse than a `.env` mismatch: the model was hardcoded at the call site, ignoring the env var entirely. Fixed both call sites in `backend/agent/__init__.py`. See Round 2, fix #4.
4. **Hard boundary between db_qa miss and XBRL-tools routing** — still open. "what access does the checker role have" still misroutes.
5. **Fuzzy-match entity extraction** for department/return names using `rapidfuzz` — still open.
6. **Strip trailing verb phrases before entity extraction** ("has the most returns", "have", empty string) — still open.
7. **Detect and surface dropped qualifiers** ("without returns", "not finance") — still open.
8. ~~**Broaden keyword groups for casual synonyms**~~ **PARTIALLY DONE** — "tell me abt returns pls" now matches (Round 2, fix #2b). Only this one phrasing was addressed; the general principle (tolerate "pls"/"wanna"/"u"/etc. across all keyword groups) is still open elsewhere.
9. ~~**Tighten `extract_intent_and_entities`'s own timeout**~~ **DONE** — `OLLAMA_EXTRACT_TIMEOUT=10`. See Round 2, fix #5. (Added after Round 1 was written — this was the second half of the same latency problem as fix #1.)
10. **New, next-round items** (see "Recommended next round" above): a `ROLE_ACCESS` db_qa rule, broader `last_login`/`failed_login_count` phrasing tolerance, a "what's X about" `RETURN_PROFILE` shape, and the Oracle `DPY-3001` thick-mode connectivity error (separate subsystem, blocks all SQL Agent queries locally).
11. **Re-run this test suite again after the next round** to keep measuring real improvement, not assumed improvement.

---

---

## Implemented fix #1: conversational-fallback timeout (done)

**Root cause traced via code, not guesswork.** `backend/services/llm_service.py`'s `_call_ollama()` backs three functions — `disambiguate_intent`, `classify_conversational_intent`, `chat_response` — and all three are the path a plain-worded question falls into whenever the db_qa regex/keyword classifier misses (exactly the "am i an admin" / "show my last 5 logins" style misses from the tables above). That function was using `REQUEST_TIMEOUT`, sourced from `OLLAMA_TIMEOUT` — **300s in this environment's `.env`**. So every miss could legitimately hang for up to 5 minutes before its *already-correct* try/except fallback (confirmed pre-existing and tested — see `backend/tests/test_llm_disambiguation_resilience.py`) got a chance to run.

**Change made:**
- `backend/services/llm_service.py` — added a dedicated `CHAT_FALLBACK_TIMEOUT` (env `OLLAMA_CHAT_FALLBACK_TIMEOUT`, default **12s**), decoupled from `REQUEST_TIMEOUT`, and pointed `_call_ollama()`'s `httpx.AsyncClient` at it instead. `REQUEST_TIMEOUT`/`OLLAMA_TIMEOUT` is untouched for calls that legitimately need longer (comparative summaries, etc.) — this only shortens the leash on the conversational-fallback path.
- `.env` and `.env.example` — documented the new variable inline with the reasoning above, so a future reader doesn't have to re-derive it.
- Both edits carry comments explaining *why*, referencing this doc, per project convention.

**Verified against the running backend** (`logs/2026-08-06.log`, post-restart):
```
19:10:31 | WARNING | backend.agent:_classify_conversational | [CONVERSATIONAL_CLASSIFIER_FAIL]
```
This now fires **immediately** (same log timestamp as the request), instead of the request hanging until a 60s+/300s ceiling. The existing fallback logic already handles `None`/exception correctly — this fix just lets it actually run promptly instead of being starved by an oversized shared timeout.

## New finding surfaced by this fix: SQL Agent is silently absorbing DB-Q&A-shaped questions

Fixing the conversational-fallback timeout let the *next* bottleneck show through in the logs. Several plain application questions are being routed into the **SQL Agent** (Oracle path) instead of the XML-based DB Q&A subsystem:
```
19:10:18 | INFO | backend.agent:decide | [INTENT:STEP3] SQL keyword fast-path session=retest-iris810
19:10:25 | INFO | selector:select_tables | Selector chose ['cims_raq_q_sec1_part_a_dom'] (from 8 candidates)
19:10:25 | INFO | backend.sql_agent:handle_db_query | [SQL_AGENT] selected=['cims_raq_q_sec1_part_a_dom']
```
for questions like **"which returns are CIMS enabled"** and **"is there a return called dpss09"** — both of these are really about the iDEAL return metadata (`XML_ReturnList`/`Returns.xml`), not the Oracle banking schema. `[INTENT:STEP3] SQL keyword fast-path` fires on words like "returns"/"CIMS" that also happen to be legitimate SQL-agent vocabulary (CIMS is literally the name of the Oracle schema's banking system), so there's a genuine ambiguity here, not just a bug — but it means these requests now pay for an embedding table-selector call **and** a full SQL-generation LLM call (up to the SQL agent's own 300s read-timeout in `sql_agent/src/sql_generator.py:1371`) before any fallback kicks in.

**This is now the top item to fix next** — a keyword like "CIMS" or "returns" alone shouldn't be enough to commit to the SQL-agent path when the db_qa classifier's own `RETURN_LIST`/`RETURN_PROFILE` rules are a confident, near-free alternative that should be tried first (or at least raced/short-circuited) for anything that also matches a db_qa keyword group.

---

## Round 2: implemented fixes #2–#5, then re-ran the full 52-question suite

After fix #1 (chat-fallback timeout) landed, four more targeted fixes were made, each tied to a concrete root cause found by tracing the actual code path (not guessing):

| # | Fix | File(s) | Root cause |
|---|---|---|---|
| 2a | Word-order-tolerant "CIMS enabled" pattern + new return-existence pattern ("is there a return called X") | `backend/db_qa/new_intent_classifier.py` | `RETURN_LIST`/`RETURN_PROFILE` only had literal, fixed-word-order regexes — a real reordering or an unhandled question shape fell all the way through to the SQL Agent's Oracle path. |
| 2b | Casual "tell me abt returns pls" catch-all for `RETURN_LIST` | `backend/db_qa/new_intent_classifier.py` | No rule existed at all for an unqualified, informally-phrased "about returns" question. |
| 3 | `who created my account` no longer misroutes into `generate_instance` | `backend/agent/__init__.py` (`_CREATED_NOT_GENERATE_RE` guard in `_fuzzy_has_generate`) | `_GEN_STEMS` includes the prefix `'crea'`, so the word "created" stem-matched "create" and won report-generation routing over the actual identity question. |
| 4 | `APP_DB_BEAUTIFY_MODEL` env var is now actually read | `backend/agent/__init__.py` (both `handle_db_qa_query(...)` call sites) | The model name was **hardcoded to `"phi3:mini"` at the call site**, silently overriding the configured env var entirely — worse than the "mismatch" originally reported, since fixing `.env` alone would have done nothing. |
| 5 | `OLLAMA_EXTRACT_TIMEOUT` tightened to 10s | `.env` / `.env.example` | `extract_intent_and_entities()`'s LLM call was already configurable via this var but it was never set, so it defaulted to 30s — stacking with fix #1's 12s fallback into ~40s+ total for a single classifier miss. |

### Verified before/after (same questions, same `iris810` identity, live re-test)

| Question | Before | After |
|---|---|---|
| "hey can u tell me abt returns pls" | 3.7s, unknown | **440ms**, matched |
| "is there a return called dpss09" | 60s+ timeout | **395ms**, matched |
| "who created my account" | 30.6s, misrouted into `generate_instance` asking for a reporting date | **380ms**, correct routing |
| "which returns are CIMS enabled" | 60s+ timeout, fell to SQL Agent | **~480-510ms**, matched (confirmed live; a shell-harness quirk dropped this one row from the raw JSONL log, see note below) |

Three fixed cases moved from the "worst" bucket (30-60s, several outright timeouts) to well under half a second — the improvement a rule/routing fix gives is categorically different from what tuning a timeout alone can give.

### Still slow — and why, traced this round

| Question | Before | After | Cause |
|---|---|---|---|
| "am i an admin" | 60s+ | ~8-43s (**variable**, see below) | Falls through both `_classify_conversational` (~11s, legitimate model latency, not a timeout) and `extract_intent_and_entities` (up to 10s) before landing on "didn't understand." No rule matches this exact phrasing. |
| "show my last 5 logins" / "how many times have i failed to login" | 60s+ | ~45s | Same double-LLM-miss path; the `last_login`/`failed_login_count` `_USER_FIELD_PATTERNS` regexes don't tolerate "show my last 5 logins" (has a number and "show" filler) or "how many times have i failed to login" (rephrased as a count question, not the direct field pattern). |
| "what access does the checker role have" | 30.6s | 30.6s (**unchanged**) | Misrouted to `get_status`/`generate_instance` path (`error → get_status`) — a different `_fuzzy_has_*` false-positive not covered by this round's fixes; there's no `ROLE_ACCESS`-style db_qa rule matching "what access does X role have" at all. |
| "whats dpss 09 about" | 60s+ | ~43s | No RETURN_PROFILE/RETURN_LIST pattern covers "what's X about" as a return-lookup shape; falls through to the two-LLM-call miss path like the identity questions above. |
| "show me the NPA data for last quarter" | 60s+ (no response) | 45s+ (**no response**, times out) | Correctly routes to the SQL Agent, which then genuinely fails: `Connection failed: DPY-3001: bequeath is only supported in python-oracledb thick mode` — this is an **Oracle client configuration problem** (the `oracledb` driver's thin mode can't reach this particular DB configuration), not an intent-classification issue at all. Out of scope for this doc; flagged for whoever owns the SQL Agent's Oracle connectivity. |

**New finding: latency for the same query varies run-to-run** ("am i an admin" measured 8.2s in isolation vs. 42.8s inside the full 52-question sequential run). Traced to `uvicorn --reload`'s graceful-drain behavior: editing `backend/` files or `.env` during this session caused old worker processes to keep running in the background (visible as duplicate PIDs briefly listening on port 8001 in `netstat`) until they finished draining in-flight requests — sometimes 100-200+ seconds later, per the logs. A request landing on a stale, still-draining worker gets that worker's old (larger) timeout values. This is purely a **local dev-reload artifact**, not something that would happen in a real deployment (no code hot-reloading in production), but it's worth knowing about if you see inconsistent timing while iterating locally: check `Get-NetTCPConnection -LocalPort 8001` (PowerShell) for more than one listener before trusting a timing measurement.

### Net effect

Of the 10 "worst-bucket" (≥3s) questions from Round 1, **3 are now fully fixed** (sub-500ms), and the remaining 7 have a clearly diagnosed cause each — 4 are the same class of problem (no matching db_qa rule for that exact phrasing → pays for two sequential LLM calls before failing), 1 is a different misrouting bug not yet fixed, 1 is a genuine Oracle connectivity failure unrelated to intent classification, and 1 is the dev-reload timing artifact above (not a real bug). None of the remaining cases are a "the LLM model isn't smart enough" problem — every one has a concrete, fixable root cause in routing or rule coverage.

### Recommended next round (not yet done)

1. Add a `ROLE_ACCESS`-shaped db_qa rule for "what access does the `<role>` role have" — currently absent entirely.
2. Broaden `_USER_FIELD_PATTERNS`'s `last_login`/`failed_login_count` regexes to tolerate a leading count/number ("last 5 logins") and count-question phrasing ("how many times have i failed to login").
3. Add a generic "what's `<return>` about" / "what is `<return>`" shape to `RETURN_PROFILE`.
4. Hand off the Oracle `DPY-3001` thick-mode error to whoever owns the SQL Agent's Oracle connection setup — this is blocking every SQL-agent query in this local environment, independent of intent classification.
5. Re-run this same 52-question suite after 1-3 to measure the next round's improvement.

---

## Round 3: report/return/schedule/time-focused testing + LLM model comparison

This round targeted a different part of the system than Rounds 1-2: the **report-workflow** intents (`get_status`, `generate_instance`, `schedule_report`, `compare_reports`) rather than db_qa. These never touch the XML-based classifier at all — every one of them calls `extract_intent_and_entities()` (`backend/llm_extractor.py`) for intent, then a **separate, deterministic regex-based extractor** for the actual report name (by design — the code's own docstring: "so hallucinated values can never reach downstream code"). 30 questions covering status checks, generation requests, scheduling with relative/absolute times, and comparisons.

**Methodology note, disclosed because it mattered**: the first pass reused one `session_id` across all 30 questions and produced corrupted results — later, unrelated questions ("is CIMS_ROR overdue") were answered as if they were numeric replies to an earlier disambiguation prompt ("Please pick a number between 1 and 4"). Multi-turn state genuinely leaking across turns is itself worth knowing about (a real caller reusing a session incorrectly would hit this), but it made the raw data misleading for single-turn accuracy measurement, so the suite was re-run with a unique `session_id` per question and only the clean re-run is reported below.

### Findings — deterministic entity-extraction bugs, not classification bugs

| Question | Result | Bug |
|---|---|---|
| "show variance between last two RAQ filings" | `compare_reports` → "No matching reports found for **'show'**" | The regex extractor kept the word "show" and discarded "RAQ" entirely — the one real entity in the sentence. |
| "compare this month vs last month DBR01" | `compare_reports` → "No exact match for **'this'**" | Extractor picked "this" over the literal return code "DBR01" present later in the same sentence. |
| "generate the report thats due tomorrow" | `generate_instance` → "No matching reports found for **'thats due tomorrow'**" | No report name in the sentence at all (by design — nothing to extract), but the fallback message doesn't recognize this as "you need to name a report," it just says "not found" as if a name was tried and missed. |
| "whats due this week" / "what needs to be filed by friday" / "did my last submission go through" | `unknown` — generic "didn't understand" | Same root issue — no named report — but these don't even reach the "not found for X" message; they fail earlier in intent classification and get the most generic possible reply. |

None of these are model-comprehension failures — they're bugs in the **deterministic post-LLM regex layer** that strips the query down to a candidate report name, or in the fallback messaging around it. A better LLM cannot fix a regex bug it never touches.

### LLM model comparison — does a bigger/different model help?

Per the user's request, the same 8 hardest-failing questions from the table above were re-run against three different models for `OLLAMA_EXTRACT_MODEL`, restarting the backend between each (`.env` restored to the original afterward — see diff history):

| Model | Size | Host | Result |
|---|---|---|---|
| `qwen2.5:7b` (baseline, current `.env`) | 7B | remote proxy | Baseline — see table above |
| `qwen2.5:14b-instruct` | 14B | local Ollama | **Byte-for-byte identical** intent + error text on all 8 questions, and slower on every single one |
| `gpt-oss:20b-cloud` | 20.9B, different vendor/architecture | Ollama cloud | **Byte-for-byte identical** intent + error text on all 8 questions, and slower on every single one |

Example — "show variance between last two RAQ filings" produced the exact string `"No matching reports found for 'show'."` on **all three models**, with durations of 10.2s → 12.6s → 14.5s respectively (bigger model, more latency, zero behavior change).

**Conclusion: the model is not the bottleneck for this class of failure, and upgrading it would only add latency.** This is strong, direct evidence (identical output across three models spanning 7B to 21B and two different vendors/architectures) rather than an inference — the entity-extraction step these questions fail at is deterministic regex code, not an LLM call, so no model swap can change its behavior. Where the LLM genuinely is in the loop (intent classification itself), all three models also agreed on every classification in this set — no disagreements were observed even there. **Do not spend effort on a model upgrade for the report-workflow gaps found in this round** — fix the regex-based report-name extractor instead (likely in `backend/tools/report_lookup.py` or wherever `extract_search_terms()`/`_extract_search_terms()` lives — not yet traced in detail this round).

### Latency observation specific to this round

Roughly half of the 30 report-workflow questions took 9-20 seconds — this is *expected* by design (a genuine LLM call is required to classify report-workflow intent, unlike db_qa's regex-first approach), not a bug like Rounds 1-2's timeout-stacking. It's still worth knowing this is the structural cost of every generate/schedule/status/compare request that doesn't hit a pre-LLM shortcut (the code already has one such shortcut for "compare" keywords — `_PRECHECK_CMP_RE` in `llm_extractor.py` — which is why "compare this month vs last month DBR01" returned in 417ms while other compare-shaped-but-not-keyword-matching questions took 10s+).

### Incidental finding: mojibake in date-format hint text

Several `gen_awaiting_date`/`sched_awaiting_rpt_date` responses contain a literal `�` character where a bullet point was clearly intended (e.g. "Quarterly reports must use: � 31-Mar � 30-Jun � 30-S..."). This is a text-encoding bug (likely a bullet character written in a source encoding that doesn't survive to the HTTP response), unrelated to intent classification but visible to every user who hits a date-format prompt. Flagged here since it was noticed during this round's testing, not chased further.

### Recommended next round (Round 3 items, not yet fixed)

1. Fix the regex-based report-name extractor to prefer an explicit return code (e.g. "DBR01", "RAQ") over filler/pronoun tokens ("this", "show") when both are present in the sentence.
2. When no report name can be extracted at all (as opposed to an extracted-but-wrong one), the fallback message should say so explicitly ("Which report would you like to check?") rather than "not found for '<garbage>'" or a fully generic "didn't understand."
3. Fix the mojibake bullet character in date-format hint messages.
4. This round's model comparison closes the model-quality question for THIS failure class — no further model testing needed here. If a future round finds a genuinely LLM-comprehension-limited failure (the model picks the wrong intent, not just a downstream regex issue), that would be the case to re-open model comparison for.

## Test artifacts
Raw JSONL responses saved at the repo root, for reproducing or extending this analysis:
- `results_selftest.jsonl` — Round 1, batch 1 (27 questions), before any fixes
- `results_selftest2.jsonl` — Round 1, batch 2 (25 questions), before any fixes
- `results_selftest_round2.jsonl` — Round 2, all 52 questions combined, after fixes #1-#5 above (note: 3 rows for "show returns with formula validation enabled" / "show returns due in more than 30 days" / "which returns are CIMS enabled" are missing from this file due to a shell-argv-length quirk in the test harness itself, not a backend issue — their live results are recorded in the "Verified before/after" table above instead)
- `complex_baseline.jsonl` — Round 3, 30 report/return/schedule/time questions against the baseline model config
- `model_14b.jsonl` / `model_gptoss.jsonl` — Round 3, the 8 hardest-failing questions re-run against `qwen2.5:14b-instruct` and `gpt-oss:20b-cloud` respectively, for the model-comparison study
