# Architecture Decision Records

This directory records significant architectural decisions for this
project: the context that prompted them, what was decided, what
alternatives (if any) are known to have been weighed, and the known
consequences/trade-offs.

## Index

| # | Title |
|---|---|
| [0001](0001-dual-dispatch-taxonomy-migration.md) | Dual-dispatch intent taxonomy migration |
| [0002](0002-sql-agent-vendoring.md) | Vendor the SQL Agent as a self-contained sub-package |
| [0003](0003-shared-http-client-for-llm-calls.md) | Shared httpx.AsyncClient for outbound LLM calls |
| [0004](0004-version-scoping-5.5-and-6.0.md) | Coexistence of iDEAL versions 5.5 and 6.0 in one codebase |

ADRs 0001–0004 were written retroactively, from the current state of the
code and its own in-source documentation, to record decisions that were
already made and implemented. Where the original historical reasoning
could not be established from the repository, each ADR says so explicitly
under "Alternatives considered" rather than inventing a rationale.

## When to write a new ADR

Add a new ADR (`NNNN-short-title.md`, next sequential number) whenever a
change introduces a significant architectural decision — something that
would be expensive to reverse, affects multiple subsystems, or changes a
cross-cutting policy (e.g. how versions/tenants are scoped, how a shared
resource's lifecycle is managed, how a vendored dependency is integrated).
A bug fix, a localized refactor, or a routine feature addition does not
need one.

Use this template:

```markdown
# N. Title

## Status
Proposed | Accepted | Superseded by ADR-NNNN

## Date
YYYY-MM-DD

## Context
What situation/problem prompted this decision.

## Decision
What was decided.

## Alternatives considered
What else was weighed, and why it wasn't chosen. If genuinely unknown,
say so rather than inventing a rationale.

## Consequences
What this decision makes easier, harder, or riskier going forward.
```
