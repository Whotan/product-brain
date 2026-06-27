# Decision: Soft-delete tasks and lists

**ID:** ADR-001
**Date:** 2026-06-18
**Status:** accepted
**Related:** Tasks, Lists

---

## Context

Users delete tasks and lists by accident. Hard deletes make "undo" impossible and lose history
that could help us understand usage.

## Decision

Tasks and lists carry a nullable `deleted_at` timestamp. "Delete" sets it; queries exclude
soft-deleted rows by default. A scheduled job purges rows soft-deleted more than 90 days ago.

## Consequences

- Undo becomes trivial (clear `deleted_at`).
- Every default query must filter `deleted_at IS NULL` — enforced via a global scope.
- Storage grows until the purge job runs; acceptable at our scale.

## Alternatives considered

- **Hard delete** — simplest, but no undo and irreversible data loss. Rejected.
- **Audit table** — more complete history, but more moving parts than we need now. Deferred.
