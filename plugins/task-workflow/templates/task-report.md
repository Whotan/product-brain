# KEY-NNN: report

<!--
Template: task-workflow plugin, templates/task-report.md. Copy it into the hub as
templates/task-report.md: the implementing agent may work from the git server, where it can read
the hub but not the plugin. Written by the agent that implemented the task; /quality-gate updates
it for playground tasks.

Every section is required and keeps its heading and number. A section that does not apply says
"None" or "Not applicable" and gives the reason. It is never deleted. Every result comes with the
exact command and its counts; "tests pass" without a command is not a result. Write down what
happened, not what was hoped for.
-->

| Field | Value |
|---|---|
| Ticket | [KEY-NNN](<tracker link for KEY-NNN>) |
| Plan | [plan.md](plan.md) |
| Mode | implementation · playground · playground → gated YYYY-MM-DD (only once the gate has passed) |
| Implemented by | <agent and model>, run by <person> |
| Branches · merge requests | <repo>: `<branch>` · <link> (one per repo) |
| Commits | <short SHAs> |
| **Environment** | **[<environment name>](<URL>)**, running commit `<sha>`, deployed by <pipeline link or who> |
| Status | Ready for review · Waiting for approval: <what> · Blocked: <reason> · Merged with open gate items: <follow-up key> |
| Date | YYYY-MM-DD |

The Environment row is required where the team deploys task branches. If the change is not
deployed, Status is `Blocked: not deployed` and the row says why.

## 1. What was done

The change in plain terms, two to five sentences.

| Acceptance criterion | Met | Evidence |
|---|---|---|
| AC 1 | yes · no · partly | test name, screenshot, or step in §3 |

**Changes from plan.md**

| Plan said | Done instead | Why |
|---|---|---|

"None" if the plan was followed exactly.

## 2. What needs attention

Decisions the agent made that a human should confirm, follow-ups (with ticket keys if filed),
and anything left out on purpose. "None" only after saying what was considered.

## 3. How to test manually

Someone who has not read the code can follow this.

- **Environment**: <URL>
- **Account · role**: <which login>
- **Data needed**: <and how to get it>

1. Step, then what to expect.
2. …

Repeat the steps in every locale the hub uses, primary first, when the change shows anything on
screen.

## 4. Risks and failures

- **Could break**: what, and what was done to check it.
- **Not fixed**: each finding or failure left unfixed, as one of:
  - false positive: <evidence>
  - pre-existing: the same command fails the same way on merge-base `<sha>`, <command and output>
  - blocked: needs <person>, <why>
- **Skipped**: every step of the plan or the mode table that did not run, and why.

"None found" only after listing what was checked.

## 5. Code review

| Repo | Skill · level | Ran on |
|---|---|---|
| <repo> | <review skill> · <level> | `<base>..<head>` |

| # | Repo | Category | File:line | Finding | Outcome |
|---|---|---|---|---|---|
| R1 | <repo> | <category> | `path:42` | … | Fixed in `<sha>` · Not fixed (see §4) |

"No findings" is a valid result. The table header stays. If code changed after the review,
the review was run again on those commits, and this table includes that run.

## 6. E2E tests

**Scenarios added or changed**

| Scenario id | App | New · changed | What it checks · what changed | Catalogue · test file |
|---|---|---|---|---|

**Runs**

Each added or changed scenario runs three times in every locale it covers. All repeats must
pass: a scenario that fails one repeat is flaky, and flaky is a defect. A quarantined or skipped
test never counts as a pass for a scenario this task added or changed.

| Command | Locale | Repeats | Passed | Failed | Skipped |
|---|---|---|---|---|---|

In playground mode before the gate, write: "Skipped (playground). Deferred to `/quality-gate`:"
and list the scenarios named in the plan.

## 7. Quality checks

One row per check the hub's conventions list for the repos in scope. Every issue a check finds
is fixed. A failure may stay only if it is listed in §4 under Not fixed. Nothing the change
introduced may fail.

| Check | Command | First run | Fixed | Final run |
|---|---|---|---|---|
| E2E | see §6 | | | |

A check that did not run stays in the table as `Not run: <reason>`. "Not run" is not a pass,
and it is also listed in §4.

## 8. UI/UX against the approved mockups

| # | Approved mockup | Built (screenshot per locale) | Matches | Differences |
|---|---|---|---|---|
| U1 | [mockups/U1-slug.html](mockups/U1-slug.html) | [<locale>](evidence/U1-<locale>.png) | yes · no | |

**Sign-off on the final deployed result**: Pending. This is filled in only from a team member's
own words (the writer by default): `<name>, YYYY-MM-DD, <source with link>`. For a playground
task, this is the sign-off after the gate, not the playground confirmation in §9.

"None. No UI/UX change." if the plan had none.

## 9. Quality gate

Playground tasks only, filled in by `/quality-gate`. For implementation mode, write
"Not applicable (implementation mode)".

| Field | Value |
|---|---|
| Playground result confirmed by | <team member>, YYYY-MM-DD, <source with link>, for commit `<sha>` |
| Gate run | YYYY-MM-DD, <agent and model>, run by <person> |
| Result | Passed · Failed: <what is left> |
| UI changes made during the gate | None · G1, G2 … (rows in §8, each needing approval) |
| Sections updated | <every section this run changed> |
| Override | None · <team member>, YYYY-MM-DD, <source with link>: "<reason in their words>" |
| Open at merge | None · <the failed items, exactly as Result lists them> |
| Follow-up task | None · <key>: runs the quality gate for the open items |
| Gate completed | None · YYYY-MM-DD in <key> |

The Override rows are filled in only when a team member merges after a failed gate. Result
keeps saying `Failed`. An override is never recorded as a pass.
