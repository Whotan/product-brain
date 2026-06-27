# Constitution — Todo

**Version:** 1.0.0
**Last updated:** 2026-06-20

---

## Principles

### 1 — Everything is scoped to a user
Every task and list belongs to exactly one user. No endpoint or query may return or mutate
another user's data. A change that can leak cross-user data is rejected.

### 2 — Validate at the edge
Requests are validated against an explicit schema before any business logic runs
(`app/Requests/` in todo-api). No raw request data reaches a model.

### 3 — Soft delete, never hard delete
Tasks and lists are soft-deleted (a `deleted_at` timestamp). Nothing is physically removed,
so an "undo" is always possible.

### 4 — Tests gate the merge
A feature ships with at least one API test and, if it has UI, one component test.
The suite must pass before merge.

---

## Per-repo notes

### todo-api
- REST resource controllers, one per resource. Business logic lives in plain service classes, not controllers.

### todo-web
- Server state goes through the data layer (`src/api/`); components never call `fetch` directly.

---

## Amendment procedure

Open a PR against this file. Bump the version on any change.
