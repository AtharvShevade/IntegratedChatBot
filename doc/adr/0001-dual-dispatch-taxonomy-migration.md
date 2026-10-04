# 1. Dual-dispatch intent taxonomy migration

## Status
Accepted (in progress — see "Consequences")

## Date
2026-10-04 (ADR written retroactively, describing a decision already
implemented in the codebase; the original decision date is not recorded
anywhere in the repository)

## Context

The DB Q&A feature (`backend/db_qa/`) classifies a user's natural-language
question into an "intent" and routes it to a handler function. Two
classification/dispatch mechanisms currently coexist in
`backend/agent/db_qa_router.py`:

- A **legacy** mechanism: a flat dict, `query_handlers.INTENT_TO_HANDLER`,
  mapping string intent names (many prefixed `db_*`) directly to handler
  functions, with a regex/keyword classifier (tagged `tier="regex_legacy"`
  in logs) feeding it.
- A **new-taxonomy** mechanism: `backend.db_qa.intents.taxonomy.Intent`, an
  enum with structured specs (`INTENT_SPECS`), a multi-tier classifier
  (regex → semantic/embedding search → LLM disambiguation), an
  `access_control.scope_query()` authorization step, and a `dispatch2()`
  function returning typed results.

`db_qa_router.py`'s own inline comment (the file's current source of
truth, since no prior design doc covers this) describes the exact
coexistence rule: an intent is first checked against the `Intent` enum; if
it parses, `dispatch2()` is tried; if `dispatch2()` returns `None` (the
intent is a recognized `Intent` value but has no handler registered yet),
execution **falls through to the legacy dispatch dict unchanged**. An
intent that isn't a valid `Intent` enum value at all (most `db_*`-prefixed
legacy names) skips the new path entirely and goes straight to legacy
dispatch.

## Decision

Keep both dispatch mechanisms running side by side, with the new taxonomy
preferred wherever a handler has been migrated to it, and the legacy dict
as the fallback for everything not yet migrated. The code establishes this
is an intentional, incremental migration strategy — not two independent
systems that happened to end up in the same file — but the project does
not currently have a tracked, finished migration completion criterion
on record anywhere other than this coexistence rule itself.

## Alternatives considered

No alternatives-considered discussion was found in the repository
(commit history, comments, or other docs) for this specific decision. The
two most obvious alternatives — (a) a single "big bang" rewrite of every
legacy handler onto the new taxonomy at once, or (b) an adapter layer that
translates legacy intent names into `Intent` enum values instead of
running two dispatch tables — are not discussed anywhere in-repo; they are
listed here only as the standard alternatives to this kind of incremental
migration, not as alternatives this project is known to have evaluated and
rejected.

## Consequences

- Every DB Q&A request pays the cost of checking BOTH systems in the
  worst case (new-taxonomy classification attempt, then legacy fallback).
- Two parallel sources of truth for "what intents exist" must be kept
  consistent by hand: the `Intent` enum (`backend/db_qa/intents/taxonomy.py`)
  and `INTENT_TO_HANDLER`'s legacy keys.
- Completing the migration (retiring the legacy dict and `regex_legacy`
  tier entirely) is tracked elsewhere in this project's audit backlog as a
  separate, larger item (referred to as "M-17" in recent hardening work)
  and is explicitly **not** undertaken by any of the hardening batches
  that produced the other ADRs in this directory — those batches were
  explicitly instructed to leave `dispatch2()`, `INTENT_TO_HANDLER`, and
  `regex_legacy` untouched pending that future migration.
- Until that migration happens, any change to intent routing must be
  checked against both mechanisms.
