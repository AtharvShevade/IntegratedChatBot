# STT evaluation harness

Measurement only. Nothing here modifies the Whisper service, the `/chat`
pipeline or `backend/i18n/`. It drives an STT service over HTTP exactly as a
client would and records what comes back.

Mirrors `eval/multilingual/`: JSONL results, a `{"_meta": true, "config": {...}}`
first line, `--resume` checkpointing, and configuration stamped into every run
so two result files can always be told apart.

---

## Why this exists

We need to choose between four STT configurations on evidence, not intuition:

1. `large-v3-turbo` — the service as deployed today
2. `large-v3-turbo` — faster-whisper + int8, model resident
3. `large-v3` — int8
4. `medium` — int8

The same harness scores all four. Only the model/runtime/quantization changes;
the audio, references, normalization and decode settings stay fixed, or the
comparison measures the harness instead of the model.

---

## Quick start

```bash
# Latency — works TODAY against the live service, no dataset needed
python -m eval.stt.run_eval --latency

# Read the acceptance table
python -m eval.stt.report

# Accuracy — needs real recordings (see below)
python -m eval.stt.run_eval --init-dataset      # writes the TEMPLATE
python -m eval.stt.run_eval --dataset-status    # what still needs recording
python -m eval.stt.run_eval --accuracy --resume
```

---

## Collecting the dataset — the part a human must do

`--init-dataset` writes `dataset/manifest.jsonl`: **74 clip records with every
`reference_text` empty**. That is deliberate. A harness that invented reference
transcripts would score models against a fiction and every number it produced
would be worthless. `run_eval` refuses to score a clip with no reference.

74 clips = 48 core (4 languages × 12) + 10 code-switching + 10 entity stress +
6 robustness.

### Step 1 — record the audio

Record **through the product's own path** — Chrome, `MediaRecorder`,
`audio/webm;codecs=opus` — so the codec and the microphone are the ones real
users will have. A studio WAV would flatter every model equally and tell us
nothing about production. WAV is also accepted (the service takes
`.flac .m4a .mp3 .ogg .wav .webm`).

Save each file at the `audio_file` path in its record:

```
eval/stt/dataset/audio/
  en/en_clean_01.webm  fr/…  ar/…  hi/…
  codeswitch/cs_devanagari_english_01.webm
  entity/ent_01.webm
  robustness/rob_01_silence.webm
```

Each record's `notes` field says what to say. Target 5–15 s. Use two speakers
per language where you can (`speaker: "s1"` / `"s2"`) so a per-speaker bias is
visible rather than averaged away.

### Step 2 — type what was actually said

Fill in `reference_text` **verbatim**, in the script that was spoken. Not what
should have been said — what was said, including a stumble if there was one.

- Hindi in Devanagari; romanised Hinglish in Latin. Whichever the speaker used.
- Arabic in Arabic script.
- Keep identifiers exactly as spoken: `CIMS_ROR`, not `cims ror`.

### Step 3 — list the entities that must survive

```json
{"id": "ent_01", "audio_file": "entity/ent_01.webm", "language": "en",
 "condition": "entity", "speaker": "s1", "duration": 7.2,
 "reference_text": "what is the status of CIMS_ROR for 31-Mar-2026",
 "entities": ["CIMS_ROR", "31-Mar-2026"], "notes": ""}
```

Leave `entities` empty to have them derived from the reference by
`backend/i18n/protect.py` — the same definition the translation boundary
protects, so "an entity" means one thing across the system.

**The two non-speech clips need no transcript.** `rob_01_silence` and
`rob_02_noise` are scorable as they are: the correct output is nothing at all.

---

## Metrics

### Accuracy

| Metric | Meaning |
|---|---|
| **WER** | Word error rate. **Headline for EN/FR.** |
| **CER** | Character error rate. **Headline for HI/AR** — Devanagari compounds and Arabic clitics make word segmentation unstable, so WER there swings on orthography rather than on what was heard. WER is still reported. |
| **EPR** | Entity Preservation Rate — reference entities reproduced **exactly**. |
| **Translation leak** | Non-English speech transcribed as English. Target **0%**. |
| **Hallucination** | Words on a silence/noise clip. Target **0%**. |

**No fuzzy correction anywhere.** EPR is exact, case-sensitive containment:
`cims ror` will not match a report name downstream, so it must not score as
preserved. Whether `/chat`'s own fuzzy resolution rescues a near-miss is a
different question, deliberately not conflated with this one.

Normalization (case, punctuation, diacritics, digit shape) applies to WER/CER
only. EPR runs on the raw strings, because case and punctuation are exactly
what distinguishes an identifier from prose.

**Translation leak is exact for HI/AR and heuristic for FR.** Devanagari and
Arabic are decidable by script. French shares Latin script with English, so the
test is the absence of any common French function word — reported honestly as a
heuristic, and returning "undecidable" rather than guessing.

### Performance

Wall-clock p50/p95, cold vs warm, RTF, and — when the service reports
`processing_ms` — server-side time separated from network. The service as
deployed does **not** report it, so today every latency figure is wall clock,
and the report says so rather than implying otherwise.

---

## The latency sweep uses tones, not speech

`--latency` generates 16 kHz mono tones at 1/5/10/15/30/60 s. A tone contains no
speech, so the decoder emits almost nothing: this measures **fixed per-request
overhead plus encoder cost**, not realistic decoding.

That is the right probe for the two questions it asks:

- Does a fixed cost dominate? (Is 1 s as expensive as 30 s?)
- Does cost scale with Whisper's 30 s windows? (Is 60 s twice 30 s?)

It is the wrong input for an accuracy number, and nothing here is ever scored
for WER.

---

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `EVAL_STT_BASE_URL` | falls back to `STT_BASE_URL` | service under test |
| `EVAL_STT_MODEL` | `large-v3-turbo` | **label** stamped into results |
| `EVAL_STT_RUNTIME` | `unknown` | `faster-whisper` / `transformers` / `whisper.cpp` |
| `EVAL_STT_COMPUTE_TYPE` | `unknown` | `int8` / `float16` / `float32` |
| `EVAL_STT_CPU_THREADS` | `unknown` | threads the service is configured with |
| `EVAL_STT_SEND_HINTS` | `true` | send `language` / `task` / `initial_prompt` |
| `EVAL_STT_INITIAL_PROMPT` | *(empty)* | vocabulary hint, for the Phase 6 A/B |

Model, runtime, compute type and threads are **descriptive labels**: this
harness cannot configure a remote service. Whoever runs a benchmark must set
them to match what is actually deployed. `run_eval` cross-checks the model
against `/health` and warns loudly on a mismatch, because mislabelled results
are worse than unlabelled ones.

---

## Acceptance gate

| Metric | Target |
|---|---:|
| EN/FR WER | ≤ 15% |
| HI/AR CER | ≤ 15% |
| Entity Preservation | ≥ 95% |
| Translation leakage | 0% |
| Silence/noise hallucination | 0% |
| p95 latency, 5 s | ≤ 3 s |
| p95 latency, 15 s | ≤ 6 s |
| Warm RTF | ≤ 0.5 |

Every row is graded **PASS / FAIL / NOT MEASURED**. `NOT MEASURED` is a
first-class outcome and never counts as a pass — a run that completed against a
dataset with no transcripts has measured nothing about accuracy. The overall
verdict is `INCOMPLETE` whenever any row lacks data.

---

## Dependencies

No new ones. `rapidfuzz` (already used by `backend/tools/report_lookup.py`)
provides the Levenshtein distance behind WER/CER, and `httpx` is already a
backend dependency. `jiwer` is deliberately not used.

CPU and RAM of the *service* cannot be sampled from here — it runs on another
host. Those numbers must come from the service side (`psutil`, not currently
installed anywhere), which is part of the Phase 0/1 work on the service itself.

---

## Tests

```bash
python -m pytest eval/stt/tests/ -q
```

62 tests, none of which touch the network.
