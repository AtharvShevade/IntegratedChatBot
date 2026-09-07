# Production patch — accept an explicit language

**For the Whisper service owner to apply. This repo cannot deploy it** (the
service is on 3.109.51.228, reachable only over HTTP from here).

One change, no behaviour change when the caller stays silent.

---

## Evidence

Measured on the instrumented build, settings identical to production
(`large-v3-turbo`, cpu, int8, `cpu_threads=8`, `beam_size=5`, model resident):

```
5s silence, language=None :  detect_ms 11,852 | transcribe_ms 11,661 | total 23,620
5s silence, language="en" :  detect_ms      0 | transcribe_ms 11,957 | total 12,064
```

`detect_ms` is **flat at ~11.6 s for 5 s, 30 s and 60 s audio** — a fixed
per-request cost — and it is almost exactly equal to one `transcribe_ms`
window. That is one **extra encoder pass per request**, spent solely to decide
a language the caller already knows.

Interleaved A/B medians (all-A-then-all-B was discarded; the machine drifts):

| Audio | `language=None` | explicit | saved |
|---:|---:|---:|---:|
| 5 s | 23,850 ms | 12,026 ms | **−49.6%** |
| 30 s | 22,224 ms | 12,239 ms | **−44.9%** |
| 60 s | 47,020 ms | 25,256 ms | **−46.3%** |

Transcripts were byte-identical in both arms. Detection was arriving at `en`
anyway — we were paying ~12 s to be told what the caller had already said.

> Absolute numbers are from a dev laptop, not the server. The **structure**
> transfers, not the milliseconds. On production, where one window costs ~6.5 s
> rather than ~11.8 s, expect roughly **14 s → 7 s for a 5 s utterance**.

---

## The change

```diff
  @app.post("/transcribe")
- async def transcribe(file: UploadFile = File(...)):
+ async def transcribe(
+     file: UploadFile = File(...),
+     language: str | None = Form(None),
+ ):
      ...
+     # Normalise: treat "", "auto" and unknown codes as "detect for me", so a
+     # malformed caller degrades to today's behaviour instead of forcing a
+     # wrong language. Forcing the WRONG language produces confidently wrong
+     # TEXT, which is worse than being slow.
+     requested = (language or "").strip().lower()
+     if requested not in {"en", "fr", "ar", "hi"}:
+         requested = None
+
      segments, info = model.transcribe(
          audio,
          task="transcribe",
          beam_size=5,
-         language=None,
+         # None keeps the existing auto-detect path for callers that send
+         # nothing. Detection is NOT removed -- only skipped when the caller
+         # already knows, which is the common case: the chatbot always sends
+         # the language the user selected in the UI.
+         language=requested,
      )
```

Also worth returning, at no cost, so latency can be attributed without
redeploying an instrumented build again:

```diff
  return {
      "text": text,
      "language": info.language,
      "language_probability": info.language_probability,
+     "duration": round(audio_seconds, 2),
+     "processing_ms": round(elapsed_ms, 1),
+     "model": MODEL_SIZE,
  }
```

`python-multipart` is already installed (the service accepts file uploads), so
`Form` needs no new dependency.

---

## Why this is safe

- **No caller is broken.** `language` is optional; omitting it runs exactly
  today's code path, including detection.
- **The chatbot already sends it.** `backend/stt/` and `VoiceInput.jsx` have
  been sending `lang` since the STT client landed — the service currently
  discards it. Verified: `language=fr` on a clip still returns
  `"language":"en"`.
- **Nothing else changes.** `beam_size` stays 5, VAD stays off, threads stay 8,
  the model stays `large-v3-turbo`. One variable.
- **Wrong-language risk is bounded** by the allow-list: anything unrecognised
  falls back to detection rather than forcing a wrong language.

---

## Verify after deploying

```bash
# language must now be honoured -- this should NOT come back "en"
curl -s -X POST http://127.0.0.1:8080/transcribe \
     -F "file=@sil_5s.wav" -F "language=fr" | jq .language

# before/after sweep, same harness, same audio
python -m eval.stt.run_eval --latency \
  --base-url http://3.109.51.228/whisper-api \
  --model large-v3-turbo --runtime faster-whisper --compute-type int8 --cpu-threads 8
python -m eval.stt.report --model large-v3-turbo
```

Note the sweep in `run_eval --latency` does **not** send a language (it probes
raw service behaviour). To measure the win, send `language=en` explicitly, or
re-run the accuracy mode once real recordings exist — that path does send it.
