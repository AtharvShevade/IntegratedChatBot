# Whisper service — instrumentation and A/B protocol

**Reference only. Nothing here is deployed by this repo.** `app_instrumented.py`
is for the service owner to run on **port 8081**, beside the live service on
8080, so latency can be attributed and optimisations compared without taking
voice input down.

---

## Why: what the client-side numbers can and cannot tell us

The live service returns only `text`, so every figure we have is wall clock and
cannot distinguish network from encode from decode. What that *can* establish
is the **shape** of the cost, and it is unambiguous — measured with digital
silence, where decoding produces ~2 tokens and is therefore near-free:

| Audio | Median wall | 30 s windows |
|---:|---:|---:|
| 5 s silence | 13.9 s | 1 |
| 30 s silence | 14.7 s | 1 |
| 60 s silence | 21.2 s | 2 |

Solving `fixed + n × window`:

```
encoder window (30 s)      ≈ 6.5 s
fixed per-request overhead ≈ 8.2 s
```

Two conclusions follow immediately:

1. **Cost is per *window*, not per *second*.** 5 s and 30 s of audio cost the
   same, because Whisper pads every window to 30 s. Trimming an utterance from
   15 s to 5 s buys nothing.
2. **~8 s is spent per request on something that is not decoding**, since
   silence has nothing to decode.

**The prime suspect is language detection.** The service calls
`model.transcribe(..., language=None)`, which makes faster-whisper run the
encoder over the first 30 s window purely to choose a language, before
transcription encodes it again. That is one extra encoder pass per request,
independent of audio length — and ~8.2 s sits suspiciously close to the ~6.5 s
a window costs.

**This is a hypothesis, not a finding.** `detect_ms` exists to confirm or kill
it. Do not optimise on the strength of the paragraph above.

---

## Running it

```powershell
$env:WHISPER_CPU_THREADS = "8"      # match the live service exactly
python -m uvicorn app_instrumented:app --host 127.0.0.1 --port 8081
```

Keep every setting identical to production for the first run. The point is to
measure the current configuration, not a better one.

```bash
curl http://127.0.0.1:8081/health
```

## Reading one request

```json
"timings": {
  "request_ms": 12, "save_ms": 3, "decode_ms": 90,
  "detect_ms": 6600, "transcribe_ms": 6800,
  "response_ms": 1, "total_ms": 13506
}
```

| If the time is in… | Then the bottleneck is… | Do this |
|---|---|---|
| `detect_ms` | language detection — a duplicated encoder pass | Pass `language=` (**already required for correctness**) |
| `transcribe_ms`, and it scales with beam | decoding | `beam_size` 5 → 1 |
| `transcribe_ms`, flat regardless of content | the encoder itself | More threads, or a smaller model |
| `decode_ms` | PyAV / container handling | Feed 16 kHz mono WAV |
| `request_ms` | IIS buffering or the network | Proxy config |
| None of them (client ≫ `total_ms`) | IIS, or queueing behind another request | Proxy / concurrency |

The last row matters: the client already measures ~14 s, so if `total_ms` comes
back at 3 s the problem is the proxy, not Whisper — and every optimisation below
would be wasted effort. **Check that gap first.**

---

## A/B protocol

The harness already targets any URL, so a comparison is two runs:

```bash
# Baseline — the live service, unchanged
python -m eval.stt.run_eval --latency \
  --base-url http://3.109.51.228/whisper-api \
  --model large-v3-turbo --runtime faster-whisper --compute-type int8 --cpu-threads 8

# Candidate — instrumented, on 8081
python -m eval.stt.run_eval --latency \
  --base-url http://127.0.0.1:8081 \
  --model large-v3-turbo --runtime faster-whisper-instrumented --compute-type int8

python -m eval.stt.report --model large-v3-turbo
```

Change **one variable at a time**, and re-run the whole sweep each time. The
service is shared and noisy — one 30 s silence run came back at 39 s while its
neighbour took 14.7 s — so a single measurement proves nothing. Three repeats
is the minimum, which is why `--repeats` defaults to 3.

Once real recordings exist, the same protocol runs with `--accuracy`, and
**that** is what decides whether a speed win cost us accuracy.
