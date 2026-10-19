# Ticket blocks

<!--
Template: task-workflow plugin, templates/task-ticket-blocks.md. /task-ticket puts the two blocks
below at the end of every ticket it writes. A hub overrides them with its own
templates/task-ticket-blocks.md, written in its tracker's markup or in Markdown (the skill
converts Markdown to the tracker's markup).

Placeholders the skill fills in: KEY-NNN (the key), BRANCH-NNN (the task branch), <HUB> (the hub's
blob URL prefix on its default branch), <TASKS> (tasks.dir), <MODE> (the plan's mode), <REPOS> (the
repos in scope).
Lines in [brackets] are kept only when their condition holds, without the brackets.
Every file named is a full URL. Keep each step short and point to a skill file for the details.
-->

## How to finish (the agent does this by default)

- The implementation must follow [constitution.md](<HUB>constitution.md) in the Product Brain hub. Read it before starting; it is not optional.
- Follow the plan: [plan.md](<HUB><TASKS>/KEY-NNN/plan.md)
- Mode: <MODE> (see the plan). [playground: The quality gate in the manual steps applies.]
- Repos in scope: <REPOS>. The hub is used only for the report, which is a manual step below.
- Do the manual steps below only when a comment on this ticket asks for them.

## Manual steps (a person triggers each one with a comment)

Each comment starts one agent run, so post them one at a time, in this order. Copy the text of
the comment from the box.

### Step 1: Code review (after CI is green)

```
Run the code review now, in this run.
<one line per repo in scope: the repo and the review it gets in this mode, from the hub's conventions>
Fix what you find. After you push, read the static-analysis result on the merge request and fix every new issue, until it is green.
Post each result as its own comment, "Code review: <repo>".
Do not write the report or run the quality gate.
```

### Step 2: Report (after the code review is clean)

```
CI is green and the review is done. Write the report only.
Make branch BRANCH-NNN in the hub fresh from its default branch. Add only <TASKS>/KEY-NNN/report.md, push, and open the hub merge request. Never push to the default branch.
Plan: <HUB><TASKS>/KEY-NNN/plan.md
Template: <HUB>templates/task-report.md
Link the hub merge request from every code merge request and from this ticket.
Do not change code.
```

### [playground: Step 3: Quality gate (after someone has confirmed the deployed result)]

```
The deployed result is confirmed. Run the quality gate for this ticket and post the result as "Quality gate: KEY-NNN".
```
