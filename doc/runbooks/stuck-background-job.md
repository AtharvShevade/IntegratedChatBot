# Runbook: Handle a stuck background job

## A note on scope

This repository has **no database-migration tooling** (no Alembic, no
migration scripts, no schema-versioning mechanism) — the application reads
Oracle directly (SQL Agent) and a flat-file XML "database" (App DB Q&A),
neither of which has a migration concept in this codebase. If "a stuck
migration" refers to something on the **.NET iDEAL side** (report/data
migrations in that separate application), this repository has no visibility
into or control over that — confirm with whoever owns the .NET app.

What this repository **does** have is a background-job mechanism for
**error-enrichment jobs** (`backend/agent/background_jobs.py`): when a
report-status lookup finds a failed submission, the backend kicks off an
async job to fetch the detailed error list, tracked by `job_id`, polled via
`GET /status-errors/{job_id}`. This is the closest real "long-running
async operation that can get stuck" in this codebase, and is what this
runbook covers.

## How to identify a stuck job

1. From the frontend: a status card shows a persistent "loading errors..."
   state that never resolves to either a result or an error.
2. From the backend: poll `GET /status-errors/{job_id}` directly (the
   `job_id` is visible in the frontend's network requests, or in the
   backend log line that created it — see `backend/agent/background_jobs.py`'s
   `_error_jobs[job_id] = {...}` assignment). A job stuck in `"pending"`
   indefinitely (well beyond the time a normal error-enrichment lookup
   takes — check recent successful jobs' durations in the log for a
   baseline) is the symptom.
3. Check the backend log around the time the job was created for the
   `_run_error_enrichment` task — an unhandled exception there is logged
   with `exc_info=True` (`logger.error(..., job_id, form_id, ret_name, exc,
   exc_info=True)`); its absence despite the job never completing suggests
   the task itself may have stalled (e.g. blocked on a slow/unresponsive
   downstream call) rather than failed outright.

## What to inspect

- **Backend process health**: is the process still responsive to other
  requests (`GET /health`)? If the whole process is unresponsive, this is
  not a single-job problem — treat it as a process-level incident instead.
- **Downstream dependencies**: `GET /health/ready` — a stuck error-enrichment
  job is frequently a symptom of a slow/unreachable dependency the job's
  own code calls into (e.g. the XML repo path, or a `.NET` instance-log
  lookup) rather than a bug in the job-tracking mechanism itself.
- **The specific job's recorded state**: `_error_jobs` is an **in-memory**
  dict (`backend/agent/background_jobs.py`) — it is not persisted to disk
  or a database. There is no admin endpoint in this repository to list or
  inspect all in-flight jobs; `GET /status-errors/{job_id}` is the only
  exposed way to query one, and only if you already have its `job_id`.

## Safe recovery procedure

1. If the backend process itself is healthy and only a specific job is
   stuck: there is no in-repo mechanism to cancel or force-complete an
   individual stuck job — because `_error_jobs` is purely in-memory, the
   job's state is cleared when the process restarts.
2. Restarting the backend process clears all in-flight job state
   (including any OTHER jobs currently in progress, which will need to be
   re-triggered by the user re-opening the relevant status card). Only do
   this if the job is confirmed stuck (not merely slow) and no other
   mitigation is available.
3. After a restart, confirm the underlying cause (a slow/unreachable
   dependency identified above) before concluding the issue won't recur —
   restarting clears the symptom, not the cause.

## What NOT to do

- Do not edit or delete any on-disk file to "unstick" this job type — the
  job state is in-memory only; there is nothing on disk to fix for this
  specific mechanism.
- Do not restart the backend process as a first response to a single slow
  (not yet confirmed stuck) job — this interrupts every other in-flight
  request on the process, not just the one job.
- Do not assume this mechanism is the same as a "stuck migration" in the
  database-schema sense — if that's genuinely what's being asked about,
  escalate rather than applying this runbook to the wrong problem.

## How to verify the system afterward

1. `GET /health` and `GET /health/ready` both healthy.
2. Re-trigger the status lookup that previously produced the stuck job and
   confirm it now completes (either a result or a clean error) within the
   normal time range.
3. Check the backend log for the new job's completion line
   (`_error_jobs[job_id] = {"status": "done", ...}`) to confirm it
   actually finished rather than silently remaining pending again.
