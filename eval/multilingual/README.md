# Multilingual evaluation harness

Answers one question: **can we make the English chatbot multilingual by
wrapping it in translation, and which model should do the translating?**

Architecture under test:

```
user language -> [model] -> English -> existing pipeline -> English -> [model] -> user language
```

The harness **observes** the pipeline. It changes nothing in `backend/agent/`,
`backend/db_qa/`, `backend/sql_agent/` or any handler, and adds no production
code. It is model-agnostic: swapping the model under test is one environment
variable.

## Three tiers

Pick the cheapest tier that answers the question you actually have.

| Tier | Flag | Size | Cost per model | Use it to |
|---|---|---|---|---|
| **Screen** | `--screen` | 5 cases x 3 langs = **15** | minutes | Decide which models deserve a real run |
| **Subset** | `--subset` | 24 cases x N langs | ~1h/lang on a 31B | Get defensible numbers without saturating a shared endpoint |
| **Full** | *(neither)* | 60 cases x N langs | hours | The final evaluation of a shortlisted model |

All three share one baseline, one scorer and one set of case ids, so results
from different tiers stay comparable.

## Quick start

```bash
# 1. Baseline: English through the unmodified pipeline, 3x, to measure how
#    much the pipeline disagrees with ITSELF before blaming any model.
#    Covers every SUBSET_24 and SCREEN_5 case, so it is captured once.
python -m eval.multilingual.supervise --baseline --runs 3 --subset

# 2a. SCREENING -- compare candidate models cheaply.
for M in gemma4:31b qwen2.5:7b; do
  for L in fr ar hi; do
    python -m eval.multilingual.supervise --model $M --lang $L --screen
    python -m eval.multilingual.score_judge --model $M --lang $L --screen
  done
done
python -m eval.multilingual.compare --models gemma4:31b qwen2.5:7b

# 2b. FULL EVALUATION -- for whichever model survives screening.
EVAL_TRANSLATE_MODEL=gemma4:31b python -m eval.multilingual.supervise --lang fr --subset
python -m eval.multilingual.score_judge --model gemma4:31b --lang fr
python -m eval.multilingual.report --model gemma4:31b
```

Drop `--subset` to run all 60 cases instead of the frozen 24.

### What screening is and is not

`SCREEN_5` is one case per dimension -- simple/general, report routing,
regulatory entity, numbers and dates, complex/ambiguous -- run in all three
languages. Every id is drawn from `SUBSET_24`, so the existing baseline already
covers them and screening needs no re-baselining.

It is a **filter, not a measurement**. Five cases per language cannot support a
confident routing-fidelity percentage; a single case moves any rate by 20
points. What it reliably catches is a model that corrupts report codes, drops
figures, or costs a minute per call. `compare.py` states this on its own output
rather than presenting 15 data points as statistics.

## Testing a different model

Nothing in this package changes. Install the model on the Ollama host, then:

```bash
EVAL_TRANSLATE_MODEL=qwen3:30b-a3b python -m eval.multilingual.supervise --lang fr --subset
python -m eval.multilingual.report --model qwen3:30b-a3b
```

Results land in `results/<model>_<lang>.jsonl`, so models never overwrite each
other and any two can be diffed after the fact. The baseline is captured once
and reused by every model.

## Layout

| File | Purpose |
|---|---|
| `config.py` | Every knob, all env-driven. `apply_eval_env()` forces the auth bypass. |
| `translator.py` | The **one model seam**. `Translator` protocol + Ollama impl. |
| `pipeline.py` | Thin `decide()` wrapper: session hygiene, wall-clock timing. |
| `masking.py` | Entity / number / date preservation checks -- the hard gate. |
| `metrics.py` | All 12 scorers, baseline-variance handling, verdict. |
| `judge.py` / `score_judge.py` | LLM-as-judge translation quality (advisory). |
| `run_eval.py` | The runner. |
| `supervise.py` | Restarts the runner until every case is recorded. |
| `report.py` | Renders `results/report_<model>.md`. |
| `dataset/build_dataset.py` | The frozen parallel corpus (en/fr/ar/hi). |

## Things that are load-bearing and easy to break

**Import order.** `config.apply_eval_env()` must run before `backend` is
imported. `backend/services/auth_service.py:55` freezes
`AUTHORIZATION_ENABLED` at import time, and with the real `.env` both it and
`REQUIRE_AUTH` are `true` -- so a harness that imports first gets the canned
`"Authentication required."` for all 60 cases and scores a clean, meaningless
zero. `pipeline.bootstrap()` enforces this and raises if backend is already
loaded.

**Session hygiene.** `_session_context` (`backend/agent/__init__.py:259`) is a
process-global dict, never expired. Every case clears its own key before and
after; leaking it between cases is the biggest correctness hazard in a
multi-turn evaluation.

**The intent extractor stays live.** `backend/tests` mock it with an
`AsyncMock`; we must not, because routing fidelity is exactly what is measured.

**Use the supervisor, not the runner, for real runs.** The SQL-agent path can
terminate the interpreter natively -- no traceback, and exit code 0, which
looks like a clean finish. It silently truncated a 60-case baseline at case 42.
`run_turn` now catches the `SystemExit` family, but a hard native abort cannot
be caught in-process, so `supervise.py` re-invokes with `--resume` until every
case is recorded.

**`--resume` is always safe.** It only skips ids already recorded. Omitting it
makes the runner unlink and restart the target file -- which is how an
already-complete baseline run got wiped once. To force a clean run, delete the
file.

## Why the metrics are shaped the way they are

**Routing fidelity is reported against the *stable* baseline subset.** The
pipeline is non-deterministic: anything falling past the regex tiers calls an
LLM on a shared remote proxy. The repo's own archived artifacts prove it --
`results_selftest.jsonl` and `results_selftest_round2.jsonl` are the same query
set, and `'hey can u tell me abt returns pls'` resolves to `unknown` in one and
`return_list` in the other. Scoring against a single baseline capture would
charge the model for the pipeline's own noise, so the baseline is captured N
times and cases that disagree with themselves are excluded from the headline.

**Entity/number preservation is pass/fail, not a similarity score.** A
translation that reads beautifully but renames `CIMS_RAQ(Monthly)` or shifts a
currency figure produces a confidently wrong regulatory answer. Exact multiset
comparison of numbers, dates, GUIDs, codes and known entities; any change is a
failure.

**Digit shapes normalise but warn.** Arabic-Indic and Devanagari digits are
folded to ASCII before comparison -- the value is intact, so failing it would
be a false positive -- but the shape change is recorded, because production
code assumes ASCII.

**The entity lexicon excludes ambiguous plain words.** `Admin`, `Daily` and
`All` are real role and period names but also ordinary English; asserting they
survive verbatim would manufacture false violations. They are listed in
`entities.json` under `_excluded_ambiguous` so the decision is auditable.

**Multi-turn splits into 9a and 9b.** The staged-reply matcher
(`agent/__init__.py:1119-1133`) is a raw ASCII substring test against English
report names, and the reset keywords (`:262-265`) are English literals. So a
name-reply survives translation only if the model leaves the report name
byte-identical -- which the translator prompt explicitly demands, but which is
a property of the model, not a guarantee of the system. 9b therefore measures
how *fragile* the staged flow is: it passes when the model preserves names and
fails the moment one is localised, with no fallback either way. Numeric replies
(9a) are language-neutral and are the real signal on the model; 9b is reported
separately and excluded from the verdict.

**The judge is advisory and never gates.** It defaults to a different model
than the one under test (self-preference bias is well documented), runs out of
band, and its scores sit beside -- not inside -- the PASS/CONDITIONAL/FAIL
verdict, which rests on the objective checks.

## Known caveats

- **The fr/ar/hi query sets are authored, not native-reviewed.** They were
  deliberately not generated by any candidate model (that would score a model
  against its own output). Native review is a prerequisite before treating the
  translation-quality number as final; routing and preservation do not depend
  on the input being idiomatic.
- **`rank_bm25` is not installed**, so the SQL agent's lexical retrieval is
  degraded and logs `Schema retrieval failed`. It affects baseline and
  translated runs equally, so the comparison stays valid, but the SQL cases are
  not representative of a correctly provisioned server.
- **Oracle is optional.** SQL consistency is scored on the generated `db_sql`
  text, which is what translation can damage. Execution comparison needs a
  reachable database.
