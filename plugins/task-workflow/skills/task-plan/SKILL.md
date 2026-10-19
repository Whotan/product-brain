---
name: task-plan
description: "Use when a described task (a draft in <tasks.dir>/drafts/<slug>/description.md, or <tasks.dir>/<KEY>/description.md for an existing ticket) needs an implementation plan before work starts, in a Product Brain hub that keeps task folders; with no key it plans the draft and /task-ticket then creates the ticket; to update an existing plan after the description changed, say it is an update; when the user says 'plan PROJ-123', 'plan this task', 'how should we build PROJ-123', or asks for a playground or implementation plan; and before a ticket moves to In Progress without a plan.md."
argument-hint: "[KEY | draft slug] [playground | implementation] (then run /task-ticket)  |  update: re-check the plan against a changed description"
allowed-tools: [Bash, Read, Write, Edit, Glob, Grep]
---

# task-plan

## User Input

```text
$ARGUMENTS
```

## What this produces

`plan.md` in the task's folder, filled in from the plan template. It writes no code. The agent
that implements the plan follows its **Definition of done** and writes `report.md` from the
report template.

`${CLAUDE_SKILL_DIR}` is this skill's base directory (shown when the skill loads). The shared
script is `${CLAUDE_SKILL_DIR}/../../scripts/task-facts.py`; call it `task-facts` below.

## 1. Preconditions

- **Settings.** Run `python3 "${CLAUDE_SKILL_DIR}/../../scripts/task-facts.py" config` from the hub
  root, and read the conventions file it names in full (test, lint, review and E2E commands, the
  apps, the base branch). It wins over this skill on team details. Use the template at
  `templates.task-plan.path`.
- **Which task.** `task-facts resolve <argument>` takes a key, a draft slug or a path. With no
  argument it picks the only draft, or lists several and stops: ask which one, never guess, since
  another session may own a draft. No draft and no key: point to `/task-description`.
- The task's `description.md` has Status `Ready for plan`. If not, stop and point to
  `/task-description`.
- With no key, write `plan.md` into the draft's folder and use the placeholder key and branch from
  `config` (`placeholder`, `placeholder_branch`); `/task-ticket` swaps in the real ones when it
  creates the ticket. Never create a ticket and never offer to; the ticket is made outside this
  skill. With a key, `task-facts links <KEY>` gives the branch name and the ticket link.
- The graph is usable. Read the **Built from** table in the graph's sync report
  (`<graph.out>/sync-report.md`). If the graph is older than 7 days or was built from the wrong
  branch, say so once and offer `pb sync`. Record the branches in **Graph built from**.

## 2. Choose the mode

If the input does not name a mode, ask the user. Never pick it yourself.

- **implementation**: the full bar. E2E scenarios and the full code review run before hand-off.
  Use it for work that goes to the base branch as it is.
- **playground**: quick delivery, so the writer can see the result. E2E and the heavy code review
  are skipped. Tests, lint, static analysis, translation keys, the static-analysis service and a
  light code review still run, and everything they find is fixed. The work is deployed to a test
  environment, and nothing merges into the base branch until `/quality-gate` passes.

The mode table in the template is fixed text. Copy it as it is.

## 3. Ground the plan in the code

- `pb find <term>` (or the hub's wrapper) for each domain term in the description.
- `graphify query`, `graphify explain "<Class>"` and `graphify affected "<Class>"`
  (`--graph <graph.out>/graph.json`) for structure, callers and blast radius. Then read the code to
  confirm the exact lines.
- E2E: find the scenarios that cover each touched route where the conventions say the catalogue
  lives. Name new scenario ids where nothing covers the surface yet.
- Every file and symbol in **Changes** names its source in **Found by**.

## 4. Write plan.md

Fill in **every** section of the template. A section that does not apply says "None" and gives
the reason.

- **Tests first** lists the tests written before the code, including one through the route or
  entry point for each new endpoint or action.
- **E2E scenarios** is filled in for both modes. In playground mode each row is marked
  `Deferred to /quality-gate`. Apps without a harness follow the template's notes.
- **Constitution check**: go through every rule of the hub's `constitution.md` that could apply.
  "no" needs a reason.
- **Deployment**: record only what the test environment needs beyond what the pipeline sets up
  (environment variables, config, flags, seed data).
- **Definition of done** is copied unchanged.

## 5. UI/UX

Carry over the description's rows (already Approved). For any new UI decision the plan makes (a
state, a layout detail, mobile or desktop behaviour), add a `P#` row with a mockup.
**REQUIRED:** follow [../../references/ui-mockups.md](../../references/ui-mockups.md). You never
approve a row yourself.

## 6. Status and hand-off

`Ready` only when every UI row is Approved and no open risk blocks starting. Otherwise it is
`Waiting for UI approval` (mockups published, approval missing) or `Draft`.

Show the user the plan, then the next steps:

1. A draft: `/task-ticket <slug>` creates the ticket and moves the folder to its key.
2. Commit and push `description.md`, `plan.md` and `mockups/` to the hub before In Progress. Do
   it only when the user says so (`/task-ticket` asks, for a new ticket).
3. Move the ticket to In Progress (the user does; no skill here moves a ticket).
4. Implement from `plan.md`. The implementing agent follows its Definition of done and writes
   `report.md`.
5. Playground only: after a team member (the writer by default) confirms the deployed result,
   run `/quality-gate <KEY>`.

## Update mode (the plan already exists)

Use it when `plan.md` exists and the description changed, or the user asks to revise the plan.
The user says it is an update. Never overwrite the file from the template.

1. **Read `plan.md` and `description.md` in full.** Check the description's Status is `Ready for
   plan`; if it is not, stop and point to `/task-description`.
2. **Find the gaps.** Compare, point by point: every acceptance criterion has a test in **Tests
   first** and a change in **Changes**; every UI row in the description is in the plan's UI/UX
   table with the same approval line; the criteria numbers in the plan still match the
   description. List what is missing, wrong or no longer needed.
3. **No gaps:** say "the plan is up to date", leave the file untouched, and stop.
4. **Gaps:** change only the affected rows and sections (Changes, Blast radius, Tests first, E2E
   scenarios, UI/UX, Risks). Keep the rest word for word.
5. **Mode.** Keep the plan's Mode unless the user changes it. If they do, update the mode table
   text and the E2E rows (playground rows are marked "Deferred to /quality-gate").
6. **Ground again only what changed.** Run `pb find` and `graphify` for new symbols; confirm lines
   in the code. A symbol that no longer exists is removed or fixed, never left in.
7. **UI/UX.** A description row that went back to `Pending` makes the plan `Waiting for UI
   approval`. A new UI decision of the plan's own gets a `P#` row, as in section 5.
8. **Header.** Recompute Status with the rule in section 6, and set `Last updated` to today. Keep
   the ticket link, branch names and graph-built-from line unless they changed (record the new
   graph state if it was rebuilt).
9. **Show what changed**, section by section.
10. **Hand-off.** Push the files when the user says so, then run `/task-ticket <KEY>` so the
    ticket text matches. If an agent is already working on the ticket, say that the change does
    not reach a run that already read it.
