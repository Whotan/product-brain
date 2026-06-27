# Vocabulary — Todo

**Version:** 1.0.0
**Last updated:** 2026-06-20

> The source of truth for product ↔ code naming. graphify connects these terms to the code and
> docs automatically — no manual links needed.

---

## Task

A single thing the user wants to get done.

- **Also called:** todo, item, card
- **In code:** `Task` (todo-api model), `TaskItem` (todo-web component)

## List

A named collection that groups related tasks.

- **Also called:** project, board, group
- **In code:** `TaskList` (todo-api model), `ListPanel` (todo-web component)

## Due date

The optional date a task is meant to be completed by.

- **Also called:** deadline, when
- **In code:** `Task.due_at` (todo-api)
