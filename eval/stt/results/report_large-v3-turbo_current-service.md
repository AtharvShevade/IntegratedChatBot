# STT benchmark — large-v3-turbo

- **Service**: `http://3.109.51.228/whisper-api`
- **/health reports**: `{"status": "ok", "model": "large-v3-turbo", "device": "cpu"}`
- **Runtime / compute**: unknown / unknown · threads=unknown
- **Hints sent**: True · initial_prompt=no
- **Run started**: 2026-09-03T09:28:44+00:00

## Acceptance

| Metric | Measured | Target | Verdict |
|---|---:|---:|:---|
| EN/FR WER | — | <= 15% | **NOT MEASURED** |
| HI/AR CER | — | <= 15% | **NOT MEASURED** |
| Entity Preservation | — | >= 95% | **NOT MEASURED** |
| Translation leakage | — | <= 0% | **NOT MEASURED** |
| Silence/noise hallucination | — | <= 0% | **NOT MEASURED** |
| p95 latency, 5s | 18318.6ms | <= 3000ms | **FAIL** |
| p95 latency, 15s | 20287.2ms | <= 6000ms | **FAIL** |
| Warm RTF | 3.7 | <= 0.5 | **FAIL** |

**Overall: FAIL**

## Latency

Synthetic tone audio — measures fixed overhead and encoder cost per 30s window, **not** decoding of real speech.

| Audio | n | Cold p50 | Warm p50 | Wall p95 | Server p50 | RTF |
|---:|---:|---:|---:|---:|---:|---:|
| 1s | 3 | 15230 ms | 15508 ms | 16169 ms | — | 15.51 |
| 5s | 3 | 17184 ms | 18305 ms | 18319 ms | — | 3.66 |
| 10s | 3 | 16025 ms | 18536 ms | 22341 ms | — | 1.85 |
| 15s | 3 | 20287 ms | 19174 ms | 20287 ms | — | 1.28 |
| 30s | 3 | 22261 ms | 16176 ms | 22261 ms | — | 0.54 |
| 60s | 3 | 22417 ms | 22216 ms | 22513 ms | — | 0.37 |

> `Server p50` is empty because the service does not report `processing_ms`. Network time and inference time therefore cannot be separated — every figure above is wall clock.

## Accuracy

**NOT MEASURED** — no scored clips.

The dataset template exists but has no recorded audio and no hand-typed reference transcripts, so no accuracy figure can be produced. See `eval/stt/README.md`.
