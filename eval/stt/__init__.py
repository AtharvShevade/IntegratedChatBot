"""Speech-to-text evaluation harness.

Measurement only. Nothing here touches the production STT service, the /chat
pipeline or backend/i18n -- it drives the service over HTTP exactly as a client
would and records what comes back.

Mirrors eval/multilingual/ deliberately: same JSONL result files, same
``{"_meta": True, "config": ...}`` first line, same --resume checkpointing, so
results from the two harnesses can be read with the same habits and tooling.

    python -m eval.stt.run_eval --latency          # works today, no dataset
    python -m eval.stt.run_eval --dataset ...      # needs real recordings
    python -m eval.stt.report --model large-v3-turbo
"""
