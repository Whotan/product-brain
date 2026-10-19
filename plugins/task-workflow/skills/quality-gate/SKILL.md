---
name: quality-gate
description: "Use when a playground-mode task in a Product Brain hub has been confirmed by its writer or another team member and must be brought up to the full quality bar before it merges into the base branch; when the user says 'run the quality gate on PROJ-123', 'gate PROJ-123', 'the playground result is good, finish it', or 'make PROJ-123 merge-ready'."
argument-hint: "KEY"
allowed-tools: [Bash, Read, Write, Edit, Glob, Grep]
---

# quality-gate

## User Input

```text
$ARGUMENTS
```

## What this is

A playground task skipped E2E and the heavy code review so that the writer could see the result
quickly (see the mode table in the task's `plan.md`). This skill runs what was skipped, **fixes
every issue it finds**, and updates the task's `report.md`. A playground task merges into the base
branch only after this passes.

`${CLAUDE_SKILL_DIR}` is this skill's base directory (shown when the skill loads). Run
`python3 "${CLAUDE_SKILL_DIR}/../../scripts/task-facts.py" config` from the hub root for the task
folder, the base branch and the conventions file, and `… links <KEY>` for the branch name. Read the
conventions file in full: it names each repo's tests, lint, static analysis, "affected" tooling,
E2E commands and full review. It wins over this skill on team details.

## 1. Preconditions: stop if any is false

- `<dir>/<KEY>/plan.md` exists with Mode `playground`, and `report.md` exists.
- **A team member (the writer by default) has confirmed the playground result, in their own
  words, from a source you can link to**: their own session, an artifact comment, a ticket
  comment, or a chat or email message. "Sara said it's fine", passed on by someone else, does not
  count; ask for the link or the person's own message. Record it in report §9 with the commit they
  saw. If they asked for changes, those come before the gate.
- The task branches are checked out with a clean tree. Bring them up to date by **merging** the
  current base branch into them. Don't rebase a pushed branch.

## 2. Work out the blast radius again

Don't rely only on the plan's list. Work through the constitution's testing rules against what
was actually built:

- `graphify affected` for each changed symbol;
- each repo's own "affected" tooling, from the merge-base (`git merge-base origin/<base> HEAD`),
  where the conventions name one;
- the callers of each changed action, service or component.

## 3. E2E

- Write the new scenarios for every user-facing surface the change touches: the plan's deferred
  list, plus any the new blast radius adds. Update the scenarios whose expectations changed. The
  catalogue entry and the test change go in the same commit.
- Run each added or changed scenario three times, in each locale it covers. All repeats must pass.
- A red or flaky scenario is a defect. Find the cause from its trace, then fix the app, or the test
  if the test is wrong. Never skip, delete or loosen the scenario, or raise its timeout, to get it
  green. A quarantined test never counts as a pass for a scenario this task adds or changes.
- Apps with no E2E harness: follow the plan template's E2E notes.

## 4. Full code review

- Run each repo's full review from the conventions (for example a stack-specific review skill, or
  `code-review` at `high`), then fix every finding.
- If code changes after this step (an E2E fix, a check fix), review those commits again before the
  gate can pass.

## 5. Every other check

Run every check in report §7, with the merge-base as base where a command takes one. Fix whatever
is red, then run the whole list again.

A failure may remain only if it is proved pre-existing: the same command fails the same way on
the merge-base (a worktree at `git merge-base origin/<base> HEAD`). Record it in report §4. If
the static-analysis service is unreachable, try any connector the session has, then ask someone
with access. Until then it is `Not run`, and the gate cannot pass.

## 6. A visible change made during the gate

If fixing something changes what a user sees (a margin, a label, a state):

- Add a `G#` row to report §8, with a mockup (Today vs Built) made by following
  [../../references/ui-mockups.md](../../references/ui-mockups.md).
- Ask the writer (or another team member) about that row by name. The playground confirmation
  does not cover it.
- A UI bug fixed here also gets the E2E scenario that would have caught it.
- The gate cannot pass while a `G#` row is Pending. The reviewer may choose to revert the change
  instead.

## 7. Redeploy and update the report

- Deploy the gate's final commit through the automated pipeline, whatever the result, and update
  the Environment row (URL, commit, pipeline).
- Update report §1–§8 from this run: changes from the plan, risks and not-fixed items, the
  code-review table, added and changed E2E scenarios with their run counts, the quality-check
  table, and UI screenshots.
- Fill in §9. Then set the header:

| Result | Mode | Status |
|---|---|---|
| Passed: every check green or proved pre-existing, no `G#` Pending | `playground → gated YYYY-MM-DD` | `Ready for review` |
| Only a `G#` row waiting for approval | stays `playground` | `Waiting for approval: G1 …` |
| Anything else | stays `playground` | `Blocked: <what is left>` |

## 8. Override: a team member merges a failed gate anyway

Any team member may decide to merge a playground task whose gate failed (a release needs it, for
example). That decision is theirs. An agent never suggests it, and never records it on someone
else's say-so.

1. **Record it only from the person's own words, from a source you can link to** (their own
   session, a merge request comment, a ticket comment, chat or email), with their reason. Fill in
   report §9's Override row.
2. **Keep the failure visible.** Copy the open items into "Open at merge" exactly as Result listed
   them. Nothing is erased or softened.
3. **Create the follow-up task** so the gate is not forgotten: a new ticket (ask before creating
   it; [../../references/trackers.md](../../references/trackers.md) has the tools), titled `Run the
   quality gate for <KEY>`, listing the open items. Put its key in §9's Follow-up task row. The
   follow-up is an ordinary task with its own folder, an `implementation` plan scoped to the open
   items, and a report.
4. **Set the header**: Mode stays `playground`, Status is `Merged with open gate items: <follow-up key>`.
5. **Closing**: when the follow-up's report shows every open item done, add
   `Gate completed YYYY-MM-DD in <follow-up key>` to §9 of this task's report and set its Mode to
   `playground → gated YYYY-MM-DD`.

## Never

- Write `Passed` while any check is red, did not run, is flaky, or is waiting on a fix "in the
  next merge request". Write `Failed: <what>`.
- Pass the gate because someone needs the release. The release can go without this task, since it
  is not in the base branch. If a team member decides to merge it anyway, record it as an override
  (step 8). It is never recorded as a pass.
