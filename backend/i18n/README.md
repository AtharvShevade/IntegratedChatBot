# `backend/i18n` — multilingual translation boundary

```
user language ──▶ inbound translation ──▶ ENGLISH ──▶ existing pipeline
                                                            │
user language ◀── outbound translation ◀── ENGLISH ◀────────┘
```

The English pipeline is **not modified**. `backend/agent/__init__.py:811 decide()`
receives the same English string and returns the same dict it did before this
package existed. Nothing in `agent/`, `db_qa/`, `sql_agent/`, or the 14
list-rendering sites is aware this layer exists.

## Why the boundary is here and not inside the agent

Routing is entirely English string matching. `lower_q`
(`agent/__init__.py:821`) feeds the regex fast-paths (`:378-449`), the db_qa
taxonomy classifier, and FAISS retrieval over `BAAI/bge-large-en` — an
English-only embedder. Translating **before** `decide()` preserves all of it.
Translating inside it would break all of it.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `MULTILINGUAL_ENABLED` | `false` | Master switch / kill switch |
| `TRANSLATION_MODEL` | `qwen3:14b` | **The only model seam** |
| `TRANSLATION_BASE_URL` | inherits `OLLAMA_BASE_URL` | Where the translator is served |
| `TRANSLATION_TIMEOUT` | `60` | Not `OLLAMA_TIMEOUT` (300s) — user-facing path |
| `TRANSLATION_TEMPERATURE` | `0` | Determinism |
| `TRANSLATION_NUM_PREDICT` | `-1` | Unbounded; `llm_service` pins 256 and truncates |
| `TRANSLATION_MAX_CHARS` | `2000` | Above this, stay English rather than stall |
| `SUPPORTED_LANGUAGES` | `en,fr,ar,hi` | Anything else degrades to English |

Every value is read **per call**, not frozen at import, so the model can be
swapped and the feature killed without a code change.

Switching models for the A/B comparison is one line:

```bash
TRANSLATION_MODEL=qwen3:14b     # run A
TRANSLATION_MODEL=gemma4:31b    # run B
```

Same code, same prompt, same masking, same tests, same pipeline.

## The two rules that matter most

**1. Inbound failure is fatal; outbound failure is not.**
A timed-out or truncated inbound translation is indistinguishable from a valid
short question once it reaches `decide()`, which would route it confidently and
wrongly. So inbound failure refuses the turn and never calls the pipeline.
Outbound failure returns the correct **English** answer — unhelpful beats wrong.

**2. Option lists never reach the model.**
`payload.py` masks the rendered list out of the prose and re-renders it from
`options[]` afterwards, so identifiers are the pipeline's own strings. For a
162-option disambiguation that is **3,446 → 122 characters**, and report
identifiers become *impossible* to corrupt rather than merely instructed not to
be. `options[]` itself is never translated — the staged matcher at
`agent/__init__.py:1119-1122` is a raw ASCII substring test against the English
name.

## Scope

**Translated (8 prose fields):** `response_text`, `llm_summary`, `db_summary`,
`db_beautified`, `status_note`, `accuracy_hint`, `more_info_hint`,
`download_label`.

**Never translated:** everything else — `report_name`, `options`, `db_sql`,
`db_columns`, `db_rows`, `db_records`, `db_qa_data`, `variance_*`,
`instances_data`, `download_url`, `error_details`, `job_id`. Every regulatory
identifier the system emits travels in one of these.

**Phase 1 limitation — `error_details[].explanation` stays ENGLISH.** Those are
long LLM-generated markdown blocks; translating them means a second expensive
call on an already-slow path, and nothing in the evaluation measured them.
Deferred to Phase 2 by decision.

## `/guided` is outbound-only, deliberately

Every message `/guided` receives is a token matched verbatim, never free prose:
the `__GUIDED_START__` sentinel, an exact `GUIDED_ACTIONS` label (matched with
`msg in GUIDED_ACTIONS`, `guided.py:179-180`), or a report name / Request ID
taken verbatim (`guided.py:198-230`). Translating any of them breaks the flow.
The user still gets a localized **response**; the button labels stay English,
which is also what keeps them matchable on the next turn.

## Conversation history

`data["i18n"]["english"]` carries the English source of every translated field
plus the English form of the user's message. The frontend replays those as
`conversation_history`, so `decide()`'s classifier and LLM extractor always see
English context — **zero** extra translation calls per turn.

## Files

| File | Role |
|---|---|
| `config.py` | Env knobs. The only place a model name appears. |
| `translator.py` | Async Ollama client. The single model seam. |
| `payload.py` | Prose/options split. **Byte-identical copy** of `eval/multilingual/payload.py` — asserted by a test. |
| `boundary.py` | `translate_inbound` / `translate_outbound`, skip rules, failure policy. |

## Tests

```bash
python -m pytest backend/tests/test_i18n_boundary.py \
                 backend/tests/test_i18n_endpoints.py \
                 backend/tests/test_i18n_payload_split.py -q
```

No network: every test drives a stub translator, which is itself the assertion
that `TRANSLATION_MODEL` is the only way this package reaches a model.
