# Model benchmark — Ollama Cloud vs the deployed model

Answers one question with evidence: **is an Ollama-Cloud-hosted model better
than the model this app deploys today?**

Nothing here touches production. No `.env` value changes, no backend code
changes, no model is replaced.

## What is actually being compared

The deployed app calls an LLM in several roles. The one benchmarked here is
the role that decides what the app *does*:

```
backend/services/llm_service.py :: extract_intent_entities_llm()
model = OLLAMA_EXTRACT_MODEL     (.env: qwen2.5:7b)
endpoint = OLLAMA_BASE_URL       (.env: http://3.109.51.228/OllamaProxy)
```

It is the right target because it is the one LLM call whose output is
**gradeable**: a fixed JSON schema with an intent from a closed taxonomy plus
extracted entities. Routing correctness, entity accuracy and hallucination —
the metrics that matter — are all read directly off it. Summary-writing calls
(`OLLAMA_MODEL`, `OLLAMA_COMPARE_MODEL`) produce prose with no ground truth
and would need a human or a judge model.

`_EXTRACT_SYSTEM_PROMPT` is **imported** from the production module, never
copied. A copied prompt drifts, and a benchmark on a drifted prompt is
fiction.

## Arms

| Arm | Model | Where |
|---|---|---|
| `deployed` | `qwen2.5:7b` | the deployed Ollama proxy — **baseline** |
| `gemma_cloud` | `gemma4:31b-cloud` | Ollama Cloud |
| `qwen3_14b` | `qwen3:14b` | the deployed proxy — **not cloud**, see below |

### Qwen 3 14B cloud does not exist

Verified against the registry, not assumed:

```
ollama.com/search?c=cloud       -> no qwen3 entry at all
registry qwen3:14b-cloud        -> 404
api/chat  qwen3:14b-cloud       -> model 'qwen3:14b' not found
```

The only Qwen models Ollama Cloud offers are `qwen3.5:cloud` and
`qwen3.5:397b-cloud`, and both refuse this account:

```
this model requires a subscription or extra usage, upgrade for access
```

So there is **no Qwen cloud result**. The `qwen3_14b` arm is the self-hosted
`qwen3:14b` already on the deployed proxy (it is `TRANSLATION_MODEL` in
`.env`), run as an explicitly labelled stand-in — never presented as the cloud
model that was asked for.

## The test set

56 single-turn English queries, taken verbatim from
`eval/multilingual/dataset/queries_en.jsonl`. **No new queries were written.**
That file predates this benchmark, so it cannot have been shaped to favour a
model. It covers status, generate, schedule, compare, DB Q&A, SQL analytics
and conversational input.

`labels.json` adds the expected intent, and grades each case:

| Grade | Count | Meaning |
|---|---|---|
| `strict` | 40 | one defensible answer — **scored** |
| `ambiguous` | 8 | two defensible answers — recorded, not scored |
| `gap` | 8 | the taxonomy has **no** valid intent — recorded, not scored |

Ambiguous and gap cases are printed in full for manual review. Scoring them
would compare models against an answer that does not exist.

The 4 multi-turn cases are excluded: they carry conversation history, and
handing one arm history that another does not get would break the fairness
rule.

## Fairness

Identical across arms: system prompt, user query, `format: "json"`,
`temperature: 0.0`, no history, no vocabulary hints, no retries.
Only `model` and its base URL differ.

Two safeguards:

- **Warm-up per arm, discarded.** The deployed proxy showed a ~5.9 s cold
  model load; charging that to whichever arm ran first would measure turn
  order.
- **Arms interleaved per query**, not run all-A-then-all-B. Machine load and
  proxy queueing drift over minutes; sequential blocks let that drift land on
  one arm and read as a model difference. This repo already fell into exactly
  that trap once while benchmarking Whisper.

## Metrics

| Metric | Definition |
|---|---|
| Intent accuracy | exact match against the label, strict cases only |
| Report-name accuracy | case- and separator-insensitive (`CIMS_ROR` == `cims ror`) |
| Date/time accuracy | **presence**, not wording — `q1` vs `Q1 2025` is the parser's problem, not the model's |
| Hallucinated entity | a `report_name` whose letters appear nowhere in the query |
| Invalid intent | an intent outside the production taxonomy |
| Schema complete | all 9 keys present |
| **Parses in production as-is** | a bare `json.loads()` succeeds — what `llm_service.py` actually does |
| Failure rate | HTTP error, timeout, or unrecoverable output |
| Latency | wall clock per call: median, mean, p95 |

**Why "parses in production as-is" is separate from accuracy.** A model can
answer perfectly and still be unusable today: `gemma4:31b-cloud` ignores
Ollama's `format: "json"` and fences its output in ```` ```json ````, which
the production `json.loads(content)` rejects. The harness parses leniently so
the *answer* can be scored, and reports the strict-parse rate alongside so the
switching cost stays visible.

## Running it

```bash
python -m eval.model_bench.run_bench                              # all arms
python -m eval.model_bench.run_bench --arms deployed,gemma_cloud  # two arms
python -m eval.model_bench.run_bench --limit 5 --out smoke        # quick check
python -m eval.model_bench.report                                 # newest run
python -m pytest eval/model_bench/tests/ -q                       # 27 tests, no network
```

Gemma cloud is reached through the local Ollama daemon, which proxies
`-cloud` tags to ollama.com using the machine's existing authentication. The
model is never downloaded.

Each run writes two files to `results/`:

- `*_raw.jsonl` — one record per query with every arm's raw output, latency
  and verdict, for manual inspection
- `*_summary.json` — aggregates plus every scored row
