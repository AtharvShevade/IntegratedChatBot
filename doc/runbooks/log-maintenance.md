# Runbook: Log rotation / log maintenance

## Where logs are stored

`LOG_DIR` (env var, see `.env.example`) — defaults to `logs/`, but this
deployment commonly sets it per-version (e.g. `LOG_DIR=logs_5.5`; confirm
the actual value in the running process's `.env`). Set at
`backend/utils/logger.py`.

Within `LOG_DIR`:
- `YYYY-MM-DD.log` — one file per day (`DailyFileHandler`), the main
  application log.
- `app.log` / `error.log` — see `APP_LOG_PATH`/`ERROR_LOG_PATH` in
  `backend/utils/logger.py` for their exact role alongside the daily files.
- `intent_classifications.jsonl` — intent-classification outcome dataset
  (`backend/utils/intent_log.py`), appended forever by design — **not**
  date-rotated, since it's a dataset to mine over time, not an operational
  log.
- `feedback.jsonl` — user thumbs-up/down records (`log_feedback()` in
  `backend/utils/intent_log.py`). Size-bounded: once it exceeds
  `FEEDBACK_LOG_MAX_BYTES` (default 10 MB, env-configurable), it is
  automatically rotated to `feedback.jsonl.1` on the next write.

## How to safely rotate/clean them

1. **Daily app logs (`YYYY-MM-DD.log`)**: already auto-pruned on startup by
   `_prune_old_logs()` (`backend/utils/logger.py`), based on
   `LOG_RETENTION_DAYS` (env var, default 30). To change the retention
   window, set `LOG_RETENTION_DAYS` and restart the backend — do not hand-delete
   files from a live `LOG_DIR` while the process is running and actively
   writing to today's file.
2. **`feedback.jsonl`**: rotation is automatic (see above). If you need to
   archive it manually, copy `feedback.jsonl`/`feedback.jsonl.1` elsewhere
   first, then it is safe to delete the originals — nothing in the backend
   reads this file back at runtime.
3. **`intent_classifications.jsonl`**: this file is intentionally never
   auto-rotated (it's a mining dataset). If it needs archiving, stop the
   backend first (or accept a brief gap in captured records), move/copy the
   file, and let the backend recreate it on next write. **Do not** delete
   it while treating the loss of historical classification data as
   harmless — confirm with whoever owns intent-classification tuning
   before removing it.

## What should NOT be deleted

- The **current day's** log file while the process is running (it's an
  open file handle — deleting it on Windows while in use will generally
  fail or behave unpredictably rather than cleanly rotating).
- `feedback.jsonl`/`intent_classifications.jsonl` without first confirming
  nobody needs the historical data (see above) — these are not purely
  operational logs, they are data.
- Anything under `eval/*/results/` — these are evaluation run outputs
  (see `doc/README.md` §10), not operational logs; they are not covered by
  this runbook's rotation mechanism at all.

## How to verify logging afterward

1. Confirm the backend process is still running and the latest log file
   for today's date exists and is growing (`Get-Content <LOG_DIR>\<today>.log -Tail 5`
   a few seconds apart should show new lines after any request).
2. Hit `GET /health` and confirm a `200 {"status": "ok"}` response, then
   check the log for the corresponding request-handling line.
3. If you changed `LOG_RETENTION_DAYS` or `LOG_DIR`, restart the backend
   and check the startup log line that reports the active log
   configuration (`backend/main.py`'s startup summary logs `log_dir=...`).
