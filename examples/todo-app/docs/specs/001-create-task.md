# Spec: Create a task

**ID:** 001-create-task
**Domain:** Tasks
**Status:** approved
**Repos:** todo-api, todo-web
**Last updated:** 2026-06-20

---

## Problem

Users need to capture a task quickly before they forget it. Today there's no way to add one.

## Goals / non-goals

- **Goal:** create a task with a title, in one step, optionally with a due date and a list.
- **Non-goal:** recurring tasks, reminders, sharing.

## Behaviour

From any screen, the user types a title and presses Enter. The task appears immediately at the
top of the current list. If offline, creation is rejected with a clear message (no silent loss).

## Acceptance criteria

- [ ] (api) `POST /tasks` with a title returns `201` and the created Task, scoped to the current user.
- [ ] (api) A missing or empty title returns `422` with a field error.
- [ ] (api) An optional `due_at` in the past returns `422`.
- [ ] (web) Pressing Enter in the quick-add box adds the task to the top of the list without a full reload.
- [ ] (web) A failed create shows an inline error and keeps the typed text.

## Terms

Touches: Task, Due date, List.

## Open questions

- [ ] Should a task created with no list go to a default "Inbox" list, or stay listless?
