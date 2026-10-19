# KEY-NNN: plan

<!--
Template: task-workflow plugin, templates/task-plan.md. A hub overrides it with its own
templates/task-plan.md (for example to name its real test, lint and review commands in the mode
table). Written by /task-plan into the task's folder.

Every section is required and keeps its heading. A section that does not apply says "None"
and gives the reason. It is never deleted. Files and symbols named here come from the graph
(`pb find`, `graphify`), confirmed in the code, never guessed.
-->

| Field | Value |
|---|---|
| Ticket | [KEY-NNN](<tracker link for KEY-NNN>) |
| Description | [description.md](description.md) |
| Mode | playground · implementation |
| Branches | <repo>: `<branch>` from `<base branch>` (one per repo in scope) · none |
| Graph built from | <branch of each pass, from the graph's sync report, and its date> |
| Status | Draft · Waiting for UI approval · Ready |
| Last updated | YYYY-MM-DD |

## Mode

Why this mode was chosen, in one or two sentences. What each mode runs is fixed:

| Gate | implementation | playground |
|---|---|---|
| Unit and feature tests written first | Yes | Yes |
| Lint, static analysis, type checks and translation keys (the hub's conventions name the commands) | Yes, fixed | Yes, fixed |
| Static-analysis service on the merge request (SonarQube or similar), new-code findings | Yes, fixed | Yes, fixed |
| Code review | Full, with each repo's full review (see the conventions). Every finding fixed. | Light: `code-review` at `low`. Every finding fixed. |
| E2E scenarios added, updated and run | Yes | Skipped. Run by `/quality-gate` |
| Draft merge request opened, so CI runs | Yes | Yes |
| Deployed to a test environment | Yes | Yes, so the writer can confirm the result |
| Merged into the base branch | After review of `report.md` | Only after `/quality-gate` passes |

## Approach

How the change is made, in a short paragraph. Name the alternative you rejected, if there was
a real one, and why.

## Changes

| # | Repo | File · symbol | Change | Found by |
|---|---|---|---|---|
| C1 | <repo> | `path/to/file` · `Symbol::method` | … | `pb find foo` / `graphify explain "Foo"` |

## Blast radius

- **Callers and consumers**: the result of `graphify affected "<Symbol>"` for each changed
  symbol, and what each one needs (nothing, a test run, a change).
- **Apps affected**: every app that builds on a changed shared module, from the repo's own
  "affected" tooling where it has one (the conventions name it).
- **Cross-repo contract**: any payload field, enum, status code, validation message or
  translation key that another repo reads. "None" if there is none.

## Tests first

| # | Tier | Test file · name | New · changed | Proves |
|---|---|---|---|---|
| T1 | <unit · feature · integration> | `tests/…` · `it …` | new | AC 1 |

A new endpoint or action has a test that goes through its route or public entry point.

## E2E scenarios

| Scenario id | App | Catalogue · test file | New · changed · run only | Priority | Locales |
|---|---|---|---|---|---|
| <area>-… | <app> | `<catalogue>` · `<spec file>` | new | high | <all locales the hub uses> |

- **playground**: the same table, with each row marked `Deferred to /quality-gate`. The
  scenarios are still named now, so the gate knows where to start.
- **App with no E2E harness**: say whether this task stands the harness up, or falls back to
  feature tests plus a checked walkthrough in every locale.
- `None` only when no user-facing surface changes, with the reason.

## UI/UX

The description's approved rows (U1, U2, …) are carried over, plus any UI decision the plan
adds: loading, empty and error states, layout details found in the code, mobile or desktop
behaviour. Each new decision gets its own mockup and follows the same approval rule.

| # | From | Change | Mockup | Approval |
|---|---|---|---|---|
| U1 | description | … | [mockups/U1-slug.html](mockups/U1-slug.html) | Approved by <team member>, YYYY-MM-DD, <source> |
| P1 | plan | … | [mockups/P1-slug.html](mockups/P1-slug.html) · [preview](<artifact link>) | Pending |

Status cannot be `Ready` while any row is not Approved. "None" if the description has no
UI/UX changes and the plan adds none.

## Data and migrations

Migrations, backfills, seeders and config or environment variables. For each one: whether it
is reversible and how it is rolled back. "None" if there are none.

## Constitution check

One row per rule in the hub's `constitution.md` that this change could touch. "no" needs a reason.

| Rule | Applies | How this plan meets it |
|---|---|---|
| <number and name> | yes · no | |

## Risks

What could go wrong that is known before starting, and how the plan reduces it.

## Deployment

The automated pipeline creates a test environment for the task's branch, where the team has one.
Note anything the environment needs that the pipeline does not set up: environment variables,
config, feature flags, seed data. "None" if there is nothing.

## Definition of done

Fixed text. Do not edit.

The agent implementing this plan:

1. Works only on the branches above, opens a draft merge request for each, and follows the mode
   table exactly.
2. Writes the tests in **Tests first** before the code that makes them pass.
3. **Fixes every issue it finds** before handing over: failing tests, lint, static analysis,
   translation keys, static-analysis service findings and code-review findings. A finding stays
   unfixed only if it is:
   - a false positive, with the evidence;
   - pre-existing: the same command fails the same way on the merge-base
     (`git merge-base origin/<base branch> HEAD`, checked out in a worktree);
   - or blocked on a named person, which makes the report's Status `Blocked`.
   Every unfixed finding is listed in report §4.
4. Re-runs the code review on any code it changes after the review.
5. Builds UI only from the approved mockups. Any difference from them is listed in the report,
   and a visible change that is not in an approved mockup goes back for approval.
6. Deploys its final commit through the automated pipeline, where there is one, and records the
   environment URL.
7. Writes `report.md` in the task's folder from the hub's `templates/task-report.md`, with every
   section filled in. It pushes the report to the hub, and links it from each merge request,
   before the ticket leaves In Progress.
