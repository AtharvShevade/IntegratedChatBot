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

---

## Round 4: the semantic embedding tier was never active — and a richer exemplar set

### The big finding

`backend/db_qa/intents/embedding_index.py` implements a **second classification tier**, designed specifically to catch phrasing the first-tier regex classifiers miss: it embeds the user's question and finds the nearest-neighbor match against a curated set of example phrasings per intent (`backend/db_qa/intents/exemplars.py`, already existed — 337 phrasings across all 56 intents). This is exactly the safety net that should have caught many of the casual-phrasing gaps found in Rounds 1-3.

**It had never been built.** Every single log file from this entire session (91 occurrences across `2026-08-06.log` and `2026-08-07.log`) shows:
```
WARNING | backend.db_qa.intents.embedding_index:search_intent | Intent exemplar index not found at ...\intent_exemplar_index.faiss — run `python -m backend.db_qa.intents.embedding_index` to build it.
```
This means every fix applied in Rounds 1-2 was a regex patch layered on top of a completely dormant semantic tier. Building it — a one-command, zero-code-change operation — was the highest-leverage action available.

### The user supplied a much richer exemplar source

`backend/db_qa/app_db_questions_augmented.json` (949 questions across 16 categories, saved to that path) is a heavily paraphrase-augmented version of the catalog `exemplars.py` was originally derived from — for every base question it adds "Can you tell me...", "Please provide...", "I need to know...", "Am I allowed to...", "Do I have permission to..." variants. These are structurally identical to real failing queries from earlier rounds (e.g. "hey can u tell me abt returns pls" ≈ "Can you tell me about returns").

Gap quantified: `exemplars.py` had **18 of 56 intents** flagged as "thin coverage" (<4 exemplars) in its own code comments. The augmented JSON had substantive material for nearly all of them.

### What was done

1. Added targeted exemplars (pulled from the augmented JSON, not mechanically dumped — a few structurally distinct phrasings per intent, matching the file's own stated design philosophy of favoring quality over repetition for nearest-neighbor matching) to all 18 thin-coverage intents, plus `ROLE_MODULE_ACCESS`, `RETURN_PROFILE`, `SUBMISSION_STATUS`, and `DEPT_RETURN_ACCESS_MATRIX` specifically targeting phrasings that failed in Rounds 1-3. `exemplars.py` grew from 337 → 374 phrasings; **0 intents remain thin-coverage** (down from 18).
2. Built the index for the first time: `python -m backend.db_qa.intents.embedding_index` → `intent_exemplar_index.faiss` (374 vectors). Confirmed on the next backend startup: `Intent exemplar FAISS index loaded` (first time this log line has ever appeared).
3. While testing, found a **precise, different root cause** for "what access does the checker role have" (failing since Round 1, always assumed to be a missing db_qa rule): `_STATUS_STEMS = ['stat', 'chec', 'prog', 'deta', 'info']` in `backend/agent/__init__.py` matches any word starting with `'chec'` as a status-check signal — but **"Checker" is a real role name** in this domain's Maker-Checker workflow. The query was being hijacked into the report-status fast-path at STEP1, before ever reaching db_qa or the embedding tier at all. Fixed by excluding "checker"/"checkers" from that stem match.
4. **Process hygiene finding**: while iterating on `.env` and restarting the dev server repeatedly this session, **12 zombie Python processes** had silently accumulated (visible via `Get-Process python` — none from a single clean launch, spanning timestamps back to the morning). `uvicorn --reload`'s parent/child process model on Windows doesn't reliably die when the wrong PID is targeted for `taskkill`, so repeated ad-hoc restarts leaked workers instead of replacing them — meaning **some earlier test results in this session may have hit stale, pre-fix worker processes** rather than the current code. All zombies were killed and a single clean instance confirmed (`Get-NetTCPConnection -LocalPort 8001` showing exactly one owning PID) before this round's numbers were captured. If you restart the dev server manually, verify old workers actually died the same way.

### Verified results (single clean process, embedding tier active)

| Question | Before (Round 1-3) | After (Round 4) | What changed |
|---|---|---|---|
| "what access does the checker role have" | 30.6s, misrouted to `get_status`/`generate_instance`, every round | **520ms**, routes to db_qa (`roles_with_permission`) | Root-caused and fixed the `_STATUS_STEMS` false positive — was never a missing db_qa rule |
| "whats dpss 09 about" | 42-60s, `unknown` | **6.9s**, correctly classified `return_profile` | Embedding tier now catches it; remaining ~7s is the entity extractor failing to parse "dpss 09" (with a space) as "DPSS09" — a separate, smaller gap |
| "did my last submission go through" | 9-15s, `unknown` | **1.9s**, correctly classified `submission_status` | Embedding tier match; asks for a submission ID since none was given — correct behavior |

### Remaining gap after this round, precisely scoped

- **"what access does the checker role have"** now reaches db_qa but lands on the wrong sibling intent (`roles_with_permission` instead of `role_module_access`) and fails entity extraction ("Unrecognized action ''"). This is a much smaller, more precise problem than the original catastrophic misroute — a regex/embedding specificity tie-break between two similar intents, not a routing failure.
- **"am i an admin", "show my last 5 logins", "how many times have i failed to login"** are still slow (~10-40s) — these specific phrasings weren't in this round's targeted exemplar additions (scoped to the 18 thin intents + the Round 1-3 failures actively traced). They're the natural next candidates: add "Am I an admin?"-shaped and "show my last N logins"-shaped exemplars to `ROLE_PROFILE`/`USER_FIELD` and rebuild the index.
- **"which returns can i submit"** measured 12.9s in this round vs. ~450ms in earlier rounds — likely first-request-after-restart model warm-up cost rather than a regression (the exemplar/index changes don't touch this intent's regex path), but flagged here rather than silently assumed benign.

### Recommended next round

1. Add exemplars for the still-slow self-referential questions above (`ROLE_PROFILE`: "am I an admin", "is my account an admin account"; `USER_FIELD`: "show my last N logins", "how many times have I failed to login") and rebuild the index.
2. Resolve the `roles_with_permission` vs. `role_module_access` tie-break for "what access does ROLE have" phrasing — likely needs the regex tier's rule ordering adjusted, or a distinguishing exemplar added to `role_module_access` that embeds closer than any `roles_with_permission` exemplar.
3. Fix the entity extractor to normalize "dpss 09" (with a space) to "DPSS09" before return-name lookup — affects any spaced-out alphanumeric return code, not just this one case.
4. **Operational note for whoever runs this locally next**: always launch `dev_server.py` with the venv's Python explicitly (`.venv\Scripts\python.exe dev_server.py`), and after any restart, verify exactly one process holds port 8001 (`Get-NetTCPConnection -LocalPort 8001 | Select OwningProcess -Unique`) before trusting timing measurements — this session's zombie-process issue would otherwise reproduce.
5. Consider periodically re-running `python -m backend.db_qa.intents.embedding_index` as part of a deploy/setup checklist — it is a **manual, offline step** with no automatic trigger, so any future exemplar edits (including this round's) silently do nothing until someone remembers to rebuild the index.

---

## Round 5: answer-quality audit against verified ground truth

Every prior round judged success mainly by "did it classify the intent and respond quickly." This round instead pulled **real ground truth** directly from the XML data (`D:\Repo5.5\Database\XML_Role.xml`, `XML_Dept.xml`, `Returns.xml`) and checked whether the chatbot's actual answer content was correct — not just fast or well-routed.

Ground truth confirmed: 18 roles (Admin User, Tester, Business Analyst, Team Lead, QA analyst, CEO [inactive], etc. — **no role named "Checker" actually exists** in this test data, worth remembering when judging that earlier fix), 6 departments (only "USER" is active), 281 XBRL returns including `DBR01` and `CIMS_CB_OSS3`.

### Bugs found by comparing answers to ground truth

| Question | Answer given | Verdict |
|---|---|---|
| "can I create new users" | Routed to `generate_instance` → "I couldn't find any report matching 'users'" | **Wrong subsystem entirely.** Fixed this round (see below). |
| "is there a role called Tester in the system" | "No role named 'Tester in the system' was found." | **False negative** — Tester is a real, active role. Fixed this round (see below). |
| "what is the status of my submission ID 1" | Routed to `get_status` → "I found 4 matching reports [report names containing '1']..." | **Wrong subsystem.** "status" is the single most natural word for this question, and it always wins STEP1's report-workflow gate over db_qa's `SUBMISSION_STATUS`/`SUBMISSION_LIST`/`SUBMISSION_DETAIL` family. **Not yet fixed — flagged as the most severe remaining gap, see below.** |
| "give me the full profile for DBR01" | `user_profile` → "Profile for iris810." (ignores DBR01 entirely) | **Still broken**, same bug as Round 1. "profile" is overloaded between `USER_PROFILE` and `RETURN_PROFILE`; the exemplar added in Round 4 used "full details" not "full profile" and didn't close the gap. |
| "is my department currently active" | `db_my_department` → "My Department \| \| Department: TusharTestLocal" | **Malformed answer** — doesn't address active/inactive at all, and has stray `|` characters (a formatting/markdown leak into plain text). |
| "what is the bank name configured in the system" | "Bank details: RBI � Indian." | Content plausible but the recurring **mojibake** bug (Round 3) is still present. |
| "what is my user level" / "what permissions does the Tester role have" / "how many non-xbrl returns..." / "which returns does my department have access to" / "how many active users are there" | All correct, well-formed, fast | ✅ Good quality — confirms the system does work well for a large share of well-posed questions. |

### Fixes applied this round

**1. "can I create new users" and the broader "can I / am I allowed to / do I have permission to" pattern.** Root cause: identical class of bug to the earlier "who created my account" fix — `_GEN_STEMS` contains `'crea'`, so "create" wins `_fuzzy_has_generate()` even though "Can I create new users?" is **already a `PERMISSION_CHECK` exemplar in `exemplars.py`** — it never got the chance to reach db_qa or the embedding tier because STEP1's report-workflow gate claimed it first. Added `_PERMISSION_QUESTION_RE` (matches a leading "can/could I", "am/are I allowed to", "do I have permission to") to `backend/agent/__init__.py`, applied to both `_fuzzy_has_generate()` and `_fuzzy_has_schedule()` (the same ambiguity applies to "can I schedule..." questions). **Verified: now routes correctly to `permission_check`** (small residual issue — the answer text "You can create." is truncated, dropping "new users" from the description; not fixed this round).

**2. Entity extraction swallowing trailing filler with no `?` present.** Root cause: `_extract_after_kw()` (`backend/db_qa/intent_classifier.py`, shared by many intents) only stops capturing at `?`, "is", "has", "and", or end-of-string. A real user question with no trailing `?` — "is there a role called Tester **in the system**" — fell through to the end-of-string branch and captured the whole trailing phrase as if it were part of the role name. Fixed by stripping a well-known, never-part-of-a-real-name trailing phrase (`"in the system"` / `"in the application"` / `"in the app"`) from the captured group, rather than loosening the shared terminator set itself (which many other intents' extraction also depends on — a narrow fix was safer than a broad one). **Verified: now correctly answers "Yes, role 'Tester' exists."**

### Process note (again)

Restarting the dev server this round hit a ~40s LLM warm-up delay against the remote Ollama proxy (slower than the usual ~10s) — not a bug, just a reminder that `/health` won't respond until the full FastAPI `lifespan` startup (including the LLM ping) completes. Confirmed the fixes only after polling until the server was genuinely ready, not from a premature health check.

### Remaining gaps after this round, in priority order (#1 fixed same round, see below)

1. ~~**"status of my submission" is likely unreachable**~~ **FIXED.** `_fuzzy_has_status()` was winning on the word "status" before db_qa's `SUBMISSION_STATUS`/`SUBMISSION_LIST`/`SUBMISSION_DETAIL` intents ever got a turn — this affected every natural phrasing of "what's the status of my submission/filing" across the whole `INSTANCE_LOG` category, not just one test question. Fixed the same way `MONTHLY_FILING_STATUS` was already special-cased in the code: added a `_has_submission_status` pre-check (reusing the same `classify_new()` call already made for the monthly-status check, so no added cost) to `backend/agent/__init__.py`'s `_has_workflow` gate. **Verified**: "what is the status of my submission ID 1" → `submission_status`, "Submission '1' not found." (correct — no such submission exists); "which of my submissions are pending approval" → `submission_list`, "Found 1 submission record(s)." Regression-checked: ordinary report-status questions ("whats the status of my raq report") still correctly route to `get_status`, unaffected.
2. ~~**"profile" ambiguity between `USER_PROFILE` and `RETURN_PROFILE`**~~ **FIXED.** Two layers, both fixed: (a) `USER_PROFILE`'s keyword rule matched bare "profile" unconditionally, so it always won the classification tier before `RETURN_PROFILE`'s (lower-priority) literal patterns ever got a chance — added an `excludes` clause (mirroring `USER_FIELD`'s existing precedent) for the literal word "return"/"filing" or a return-code-shaped token (letters + 2+ digits, e.g. "DBR01"). (b) Even once classification was fixed, entity extraction still failed for phrasings with no "return"/"form"/"report" anchor word at all — added `_extract_return_name_generic()` (`backend/db_qa/new_intent_classifier.py`), which tries "profile for/of" anchors, then falls back to a bare return-code-shaped regex scan (handles "whats dpss 09 about", where the code appears *before* the only anchor word "about" — direction `_extract_after_kw` can't handle). **Verified**: "give me the full profile for DBR01" → "Details for return 'DBR01'."; "whats dpss 09 about" → "Details for return 'DPSS09_ATM_Transactions_Decline'." (correctly fuzzy-resolved). Regression-checked: "what is my role" and "who am i" still correctly route to `role_profile`/`user_profile`.
3. ~~**`db_my_department`'s answer formatting**~~ **FIXED — but the original diagnosis was wrong, and the real bug was different.** The "stray `|` characters" reported in Round 5 turned out to be an artifact of this session's own test-display code (`.replace(chr(10), ' | ')` used to compact multi-line output for readability) — not a real bug in the app's output. Re-tracing "is my department currently active" fresh (via `check_new_taxonomy_intent_full` directly) found the actual issue: the embedding tier correctly flagged this question as ambiguous between `department_profile` and `department_list`, but the LLM disambiguation tie-break sometimes picked the wrong one — producing "There are 1 active departments." (a system-wide count) instead of an answer about the caller's own department. Fixed by adding a direct regex rule to `DEPARTMENT_PROFILE` in `backend/db_qa/new_intent_classifier.py` ("my department...active", "is my department") so this phrasing no longer depends on an unreliable LLM tie-break at all. **Verified**: now correctly routes to `department_profile` and answers about "TusharTestLocal" (the caller's actual department), not a system-wide count. Regression-checked: "what department am i in" unaffected. Residual, smaller nicety not fixed: the response's one-line text summary doesn't explicitly echo the word "active"/"inactive" (the `Status` field is present in the underlying record for the table view, just not phrased into the sentence).
4. ~~**Mojibake**~~ **NOT A BUG — closed.** Inspected the raw response bytes directly: `d[0]='—'` — the correct em-dash codepoint. The `�` seen in every prior round was this session's own git-bash/Windows-console terminal failing to *display* that character, not the API sending anything wrong. No code change made; flagged in Rounds 3 and 5 as a real bug in error, corrected here.
5. **"You can create." for `permission_check`** — traced and **not a truncation bug either**. The handler (`backend/db_qa/query_handlers/role_handlers.py::handle_permission_check`) only ever tracks a fixed action (create/edit/view/approve) against a *module* (e.g. "Balance Sheet") — "new users" isn't a module in this schema, it's the object of the CREATE action for the User entity specifically, which this permission model has no slot to represent at all. The response is accurately describing what the system actually checked (generic create-permission), just without an object to echo back. Fixing the *wording* to feel complete would require adding real entity-extraction for the action's object noun — a feature addition, not a bug fix — so left as a documented design characteristic rather than patched with a cosmetic string change that wouldn't reflect what the system actually knows.

---

## Round 6: generalized fix for the whole class of stem-collision bugs, plus an XML data-access review

### More improvement found: the "checker"/"created" bug was one instance of a whole class

Rounds 5-6 each fixed one specific word colliding with a report-workflow stem (`'chec'` matching "Checker", `'crea'` matching "create"). Audited the remaining stems (`_GEN_STEMS`, `_STATUS_STEMS`, `_SCHED_STEMS`) against real English words a user would plausibly type and found **more of the same class**, confirmed live:

| Query | Before | Cause |
|---|---|---|
| "give me the details of my role" | `_fuzzy_has_status` = True (wrongly) | `'deta'` stem matches "details" — a deliberate status synonym, but "details of my role" is a legitimate `ROLE_PROFILE` question |
| "is there a role called Executive" | `_fuzzy_has_generate` = True (wrongly) | `'exec'` stem matches "Executive" — deliberately added to catch "execute the report", collides with any role/word starting "Exec-" |

Rather than patch these two words individually (the same whack-a-mole pattern as before, which doesn't scale — more collisions will keep surfacing as real users type real words), **generalized the fix**: the code already had two one-off special cases doing exactly the right thing (`MONTHLY_FILING_STATUS`, then `SUBMISSION_*`, each added independently as discovered in earlier rounds) — both probed `classify_new()` (the confident, structural regex tier) and excluded a match from the fuzzy workflow gate. Replaced both narrow checks with one general one: **any** confident `classify_new()` match now excludes the query from `_has_workflow`, not just the two previously-special-cased intents.

**Verified safe**: `classify_new()` stays silent (`None`) on every genuine report-workflow phrasing tested ("what is the status of my raq report", "generate the DBR01 report", "schedule DBR01...", "check status for cims filing") — so trusting its match doesn't risk misrouting real report-workflow requests. **Verified fixed**: both new collision cases now route correctly (`role_profile`, `role_list`), and both previously-special-cased intents (`SUBMISSION_STATUS`, `MONTHLY_FILING_STATUS`) still work identically under the generalized check — confirmed via live re-test, zero regression.

This closes the *general* version of a bug class that's been found and re-found three separate times this session (Checker, created, details/Executive) — future stem collisions in this same family should now self-resolve without another patch, as long as the colliding phrasing also happens to match some db_qa shape (which is the common case — a colliding word is usually colliding because it's part of a legitimate db_qa question).

### XML data-access review

Read through `backend/db_qa/xml_store.py`, `backend/db_qa/versions/loader.py`, and `backend/tools/report_lookup.py`'s caching to answer "how do we access all our XML files."

**What's solid:**
- **Security-by-default field allowlisting**: `EntitySpec.attribute_map` only ever reads the specific raw XML attributes it declares — credential fields (`Password`, `RefreshToken`, etc.) are structurally impossible to leak into a loaded row because they're simply never listed, not filtered after the fact.
- **Auto-invalidating cache, not a dumb one-time read**: both `xml_store.py` and `report_lookup.py`'s `_TTLCache` re-check the file's on-disk mtime and reload automatically on change — a report/return edited on disk is picked up on the next request without a backend restart.
- **BOM/encoding tolerance and graceful degradation**: a malformed or missing XML file logs a warning and returns `[]` rather than crashing the whole request.
- **Per-tenant cache keying** (`report_lookup.py`'s caches are path-keyed, not global) — correctly avoids one 6.0 tenant's data leaking into another's cache in a multi-tenant deployment.

**One real finding — duplicated parsing logic, not a live bug:** `Returns.xml` (and likely other files) is independently parsed by **two separate code paths** — `backend/db_qa/versions/v5_5_schema.py`/`xml_store.py` (used by db_qa) and `backend/tools/report_lookup.py` (used by the report-workflow tools). Both do correct mtime-based invalidation, so this isn't a staleness bug — but it is a maintenance-surface duplication: a parsing fix (encoding edge case, a new attribute name variant) applied to one path has to be remembered and re-applied to the other, or the two subsystems' answers about the same file can silently drift apart over time. Not fixed this round (a real refactor, not a quick patch) — flagged for whoever owns this codebase long-term to consider unifying onto one loader.

**Why two paths exist in the first place — traced via git history, not guessed:**

| Date | Commit | What happened |
|---|---|---|
| 2026-05-20 | `6e71e8a` "first commit" | `backend/tools/xml_loader.py` and `backend/tools/report_lookup.py` land together as part of the **original** report generate/status/schedule/compare feature — the app's core purpose from day one. |
| 2026-05-28 (8 days later) | `640875e` "integrating general_qa" | `backend/db_qa/xml_store.py` is added as a **separate, subsequent feature** — the natural-language "Application Database Q&A" capability — merged in as its own branch of work. |

`xml_loader.py`'s own header comment states the original intent explicitly: *"Reusable, safe XML file loader for repository-sourced files. All callers that need to parse Returns.xml or XML_InstanceLog should use `load_xml_tree()` so error handling is consistent across the codebase."* That guideline was never followed by the later `db_qa` work — when the Q&A feature was added a week later, it needed something `report_lookup.py` was never designed for: a declarative, multi-entity loader covering 16 different XML sources (Users, Departments, Roles, RoleAccess, Periods, UserLevels, Segments, Bank Details, Audit, ErrorLog, and more), with a security-first attribute allowlist (`EntitySpec`) that `report_lookup.py` never needed since it wasn't reading credential-adjacent files. `report_lookup.py` by contrast is narrow and deep — tightly coupled to report-generation-specific domain logic like status-code interpretation (`_SUCCESS_STATUSES`, `_FAILED_STATUSES`) that has nothing to do with, say, looking up a user's email.

So the split reflects two genuinely different shapes of need (narrow+deep vs. broad+shallow), not pure oversight — but it does mean `Returns.xml` specifically ends up parsed by both, for different purposes (checking a report's generation status vs. answering "which returns can I access").

**Decision: not merging these for now.** Documented here for whoever revisits this later — unifying would mean either generalizing `xml_loader.py` to `db_qa`'s security/multi-entity requirements, or moving `report_lookup.py`'s status logic on top of `xml_store.py`'s rows. A real design decision, not a quick refactor — deliberately left alone this round.

## Test artifacts
Raw JSONL responses saved at the repo root, for reproducing or extending this analysis:
- `results_selftest.jsonl` — Round 1, batch 1 (27 questions), before any fixes
- `results_selftest2.jsonl` — Round 1, batch 2 (25 questions), before any fixes
- `results_selftest_round2.jsonl` — Round 2, all 52 questions combined, after fixes #1-#5 above (note: 3 rows for "show returns with formula validation enabled" / "show returns due in more than 30 days" / "which returns are CIMS enabled" are missing from this file due to a shell-argv-length quirk in the test harness itself, not a backend issue — their live results are recorded in the "Verified before/after" table above instead)
- `complex_baseline.jsonl` — Round 3, 30 report/return/schedule/time questions against the baseline model config
- `model_14b.jsonl` / `model_gptoss.jsonl` — Round 3, the 8 hardest-failing questions re-run against `qwen2.5:14b-instruct` and `gpt-oss:20b-cloud` respectively, for the model-comparison study
- `results_selftest_round4_embedding.jsonl` — Round 4, all 52 questions re-run after building the embedding index and fixing the `_STATUS_STEMS` false positive
- `backend/db_qa/app_db_questions_augmented.json` — the user-supplied richer exemplar source used to fill 18 thin-coverage intents this round (not raw test output, but the input data for the exemplar work)
- `coverage_results.jsonl` — Round 5, 20 category-spanning questions using real, ground-truth-verified entities, used for the answer-quality audit
