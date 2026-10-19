# KEY-NNN: description

<!--
Template: task-workflow plugin, templates/task-description.md. A hub overrides it with its own
templates/task-description.md. Written by /task-description into <tasks.dir>/<KEY>/description.md,
or into <tasks.dir>/<tasks.drafts>/<slug>/description.md while the task has no ticket yet.

KEY-NNN is the placeholder key (`task-facts.py config` -> placeholder). /task-ticket swaps in the
real key when it creates the ticket.

Every section is required and keeps its heading. A section that does not apply says "None"
and gives the reason. It is never deleted. Use vocabulary.md terms; when the code calls it
something else, give both.
-->

| Field | Value |
|---|---|
| Ticket | [KEY-NNN](<tracker link for KEY-NNN>) |
| Type | Task · Bug · Story · Technical debt |
| Writer | <the person who wrote the task: the ticket's reporter by default. Asked first for UI/UX approval. Any team member may take the role over.> |
| Written up by | <the person who ran /task-description, if not the writer> |
| Repos | <repo ids from brain.config.json that change> |
| Apps | <the apps or panels a user sees the change in, as the hub's conventions name them> · none |
| Size | Task: one ticket, no new user stories, no change across domains. If this stops being true, the work becomes a spec. |
| Status | Draft · Waiting for UI approval · Ready for plan |
| Last updated | YYYY-MM-DD |

<!--
Status: the first match wins.
1. Draft: an open question that changes a criterion or a UI row, or a requested mockup not built yet.
2. Waiting for UI approval: every requested mockup is published, and at least one row is not Approved.
3. Ready for plan: everything else is done.
-->

## Problem

What is wrong or missing today, who runs into it, and the evidence: the ticket, a screenshot, an
error report, a customer report. Two to five sentences. If the ticket itself was not read (only
someone's summary of it), say so here.

## Change

What is different for the user when this task is done. One paragraph, from the user's side.
How it is built belongs in `plan.md`, not here.

## Out of scope

What a reader could expect this task to cover that it does not.

## Acceptance criteria

Numbered. Each one can be checked by someone who has not read the code.

1. Given …, when …, then …

## UI/UX changes

Either:

> None. No screen, text, layout or interaction that a user sees changes.

Or one row per screen (or component) that changes. All the changes to one screen share a row
(and a mockup, if one is made).

| # | App · screen / route | Change (copy proposed by the agent is marked *proposed*) | Mockup | Approval |
|---|---|---|---|---|
| U1 | <app> · `/route` | … | [mockups/U1-slug.html](mockups/U1-slug.html) · [preview](<artifact link>) | Pending |

- **Mockup**: optional. `not built yet` until a requested mockup is published, or
  `none, skipped by <writer>` when the writer does not want one (the Change cell then states the
  change precisely in words, in every locale the hub uses, and that text is what a team member
  approves).
- **Approval** is one of:
  - `Pending`
  - `Approved by <team member>, YYYY-MM-DD, <source>`. The source is where that person said it in
    their own words, with a link: their own session, an artifact comment, a ticket comment, or a
    chat or email message.
  - `Changes requested, YYYY-MM-DD: <what>`

A row moves to Approved only when a team member approves it themselves: the writer, or any other
team member. An agent never approves a row, and an approval passed on second-hand does not count.

## Open questions

| # | Question | Who answers | Answer |
|---|---|---|---|
| Q1 | … | writer · expert · dev | open |

"None" if there are none. Proposed copy that conflicts with `vocabulary.md`, and copy the ticket
does not give (for example a label in the hub's second locale), goes here.
