---
name: epic-approval
description: Approval gate before an epic launches — finds or creates one release branch with the same version in every repo of the hub (backend, frontend, mobile; next version from the latest release and the commit messages on develop), measures what it would merge into main against five criteria (change scope controlled, error & edge cases handled, security basics checked, backward compatibility considered, deployment/configuration risks addressed), and writes one report per repo plus a summary into the hub. Use when the user asks to approve, sign off, gate or review an epic / release before launch, to cut a release branch and check it, or before a release branch is merged into main.
argument-hint: "[release-branch] [repo-id ...]"
allowed-tools: [Bash, Read, Write, Edit, Glob, Grep, Agent]
---

# epic-approval

Release branches are cut from the integration branch (`develop`) and merged into the production
branch (`main`) when an epic launches. This skill reviews **exactly what that merge would bring**,
repo by repo, against five criteria:

| # | Criterion | Reviewer agent |
|---|---|---|
| 1 | Change scope controlled | `epic-approval:scope-reviewer` |
| 2 | Error & edge cases handled | `epic-approval:edge-case-reviewer` |
| 3 | Security basics checked | `epic-approval:security-reviewer` |
| 4 | Backward compatibility considered | `epic-approval:compat-reviewer` |
| 5 | Deployment/configuration risks addressed | `epic-approval:deploy-risk-reviewer` |

Scope comes from the **commit messages** (`type(scope): [TICKET-ID] description`, the
git-workflow rule) — no epic or ticket id is needed. The reports land in the hub, so the whole
team (and the graph, on the next `pb sync`) sees them.

**One version for every repo.** Back end and front end always ship under the same release branch
name (`release.1.5.0` in both), so a launch is one version end to end.

**Semantic names.** Every release branch this skill creates is named `release.MAJOR.MINOR.PATCH`,
whatever the older branches look like. Older names are still read for their version — after
`release-5-5` (read as 5.5.0), a `feat` release is `release.5.6.0`, never `release-5-6`.

**English only.** Every question this skill asks and every report it writes is in English,
whatever language the user writes in. Do not write Finglish or any other language in questions,
reports or the summary.

It reports; people decide. It may create a release branch **locally after a yes**, and push it
only after a second, explicit yes. It never merges, tags, deploys, or edits a ticket.
`${CLAUDE_SKILL_DIR}` is this skill's base directory (shown when the skill loads).

## Config

Read from the hub's `brain.config.json`. All optional; `plan` lists the keys it defaulted.

| Key | Used for | Default |
|---|---|---|
| `repos[]` | the repos to review; `repos[].kind` overrides the detected `backend` / `frontend` / `mobile` / `fullstack` | — |
| `releases.production_branch` | where the release merges | `main` |
| `releases.integration_branch` | where release branches are cut from | `develop` |
| `releases.release_branch_regex` | what a release branch is called | `^release[-/._]` |
| `approvals.out` | where reports are written in the hub | none — ask (Step 5) |

## Step 1: Plan one release branch for all repos

Run from the hub (or pass `--hub`). Fetch every repo first so branches are current:

```bash
for r in repos/*/; do git -C "$r" fetch --quiet --prune origin || echo "fetch failed: $r"; done
python3 "${CLAUDE_SKILL_DIR}/scripts/gather-epic-facts.py" plan [--branch <name>] [--repo <id> ...]
```

Pass `--branch` only when the user named a branch; `--repo` only when they named repos. A failed
fetch means that repo's facts may be stale — say so. `--prune` drops `origin/*` refs for branches
deleted on the server; it never touches local branches or work. Origin is the source of truth: a
local release branch that is not on origin is ignored for versioning and reported as a warning.

`plan` returns one shared `release` (the same `branch` and `version` for every repo) and a row
per repo. How the name is chosen (`release.source`):

- `named` — the user gave `--branch`: that name, in every repo.
- `open release` — some repo has a release branch on origin, not yet merged into production and
  newer than what shipped: that name, in every repo. Older unmerged branches are abandoned, not open.
- `proposed` — the highest release that **reached production in any repo**, bumped by the
  strongest change waiting on **any** repo's integration branch (breaking → major, `feat` →
  minor, else patch), always named `release.X.Y.Z`. `based_on` and `bump_reason` say which repo
  drove it.

What "reached production" means: release branches are usually deleted after they are merged into
`main`, so the version is read from what stays on `main` — merge commits of a release branch
(`Merge branch 'release-5-4' into 'main'`, first parent only) and release branches still on origin
that are already merged. **Tags are never read**: the team's tag scheme is independent of release
names. When the history disagrees (releases merged out of order, a hotfix merged after a newer
release), the **highest version wins**, never the most recent merge; `latest_release.seen` lists
the highest releases found so the user can check. A squash-merged release leaves no merge commit
and cannot be seen — keep merging releases with a merge commit.

If `release.needs_decision` is set (two different open releases, no previous release anywhere,
nothing to release, or a non-semantic name that would have to be created in some repo — then
`suggested_branch` holds the semantic name to offer), stop and ask the user; re-run with `--branch <name>` once they decide. Never
let repos go out on different versions.

Show the user one table — the shared branch and why, then per repo: kind, latest release, status —
and act on each row's `status`:

| `status` | Meaning | Do |
|---|---|---|
| `exists` | the shared branch exists in this repo | review `review_ref` |
| `create` | the shared branch does not exist here yet | offer to create it (Step 2) |
| `nothing to release` | no new commits here | ask whether to create the branch anyway so versions stay in step; otherwise skip and list it |
| `already merged` | this version already shipped from this repo | ask for another version |
| `not cloned` / `no … branch` | nothing to review here | skip; list it in the summary |

Show every `warnings` entry (for example repos that were on different versions until now) and,
if `defaulted_keys` is not empty, which defaults were assumed.

## Step 2: Create the branch — only after a yes

Ask once, in English, for every repo that needs the branch — the one shared name and, per repo,
what it is cut from. Create it in every `create` repo (plus any `nothing to release` repo the
user chose to include) or in none of them. On a yes:

```bash
git -C <path> branch <branch> <integration ref>
```

Then ask separately, in English, whether to push. Only on an explicit yes, push every repo's branch:

```bash
git -C <path> push -u origin <branch>
```

If the user declines creating it, review the integration ref (`review_ref`) as the would-be
release and say so in the report. Never check out, reset or rebase a working clone — developers
work in `repos/` directly.

## Step 3: Gather the facts per repo

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/gather-epic-facts.py" facts --repo <id> --head <branch or review_ref> \
  --out ".work/epic-approval/<date>/<id>.json"
```

`.work/` is the hub's git-ignored scratch space. Use each file's `range` (`merge-base..head-sha`)
for everything after this — branch names move, the pinned range does not. Surface every
`warnings` entry. If `merge.status` is `conflicts`, tell the user now: that repo cannot be
`APPROVED` until they are resolved and the skill is run again.

## Step 4: Run the reviewers

For every repo, launch all five agents — every repo's agents **in one message**, so they run
concurrently (two repos = ten agents). Give each the same header:

```text
FACTS: <absolute path to the repo's facts JSON>
RANGE: <range from that file>
REPO: <repo id> at <absolute repo path>
KIND: <kind from the facts>
```

Each returns one fixed block (`CRITERION`, `VERDICT`, `SUMMARY`, `FINDINGS`, `CHECKED`,
`NOT CHECKED`; `RELEASE CONTENTS` from the scope reviewer, `DEPLOY CHECKLIST` from the deployment
reviewer). If an agent returns something else or fails, re-run that one agent once; if it fails
again, record the criterion as `NOT ASSESSABLE (reviewer failed)` — never fill it in from a guess.

Before accepting a `BLOCKER` or `MAJOR`, open the cited file or commit and confirm the finding is
real and inside the range. Drop what does not hold up and list it under *Dismissed*; never drop a
finding just to reach approval.

## Step 5: Decide and write the reports

Per repo, keep each agent's verdict and decide:

| Decision | When |
|---|---|
| ❌ `NOT APPROVED` | any criterion is `FAIL`, or the merge has conflicts |
| ⚠️ `APPROVED WITH CONDITIONS` | no `FAIL`, but any `CONCERNS` or `NOT ASSESSABLE` — every `MAJOR` and every not-assessable criterion becomes a named condition |
| ✅ `APPROVED` | all five `PASS` |

The launch as a whole takes the **worst** repo's decision: a frontend cannot launch against a
backend that is not approved. `NOT ASSESSABLE` is never a pass. A person may waive a finding;
record who waived what and why, but do not change the verdict it came from.

Reports go to `<approvals.out>/<YYYY-MM-DD> - <release branch>/` (slashes in the branch name
become dashes). If `approvals.out` is not set, propose
`"approvals": {"out": "docs/approvals"}` and add it to `brain.config.json` on a yes — `pb check`
accepts any `docs/` folder the config names. If the user says no, write to
`.work/epic-approval/<date>/` and say that it is not shared.

One file per reviewed repo, `<repo-id>.md`:

```markdown
# <repo-id> (<kind>) — <branch> → <production>

**Decision:** ✅ APPROVED | ⚠️ APPROVED WITH CONDITIONS | ❌ NOT APPROVED
**Change:** `<range>` · <n> commits · <n> files · +<added>/−<deleted> · bump: <major|minor|patch>
**Merge:** clean | conflicts in <files> · **Production commits not in release:** <n>
**Branch:** existing | created from <integration> (pushed | local only) | not created — reviewed <integration>
**Reviewed:** <date>

| # | Criterion | Verdict | Blockers | Major | Minor |
|---|---|---|---|---|---|
| 1 | Change scope controlled | … | … | … | … |
| 2 | Error & edge cases handled | … | … | … | … |
| 3 | Security basics checked | … | … | … | … |
| 4 | Backward compatibility considered | … | … | … | … |
| 5 | Deployment/configuration risks addressed | … | … | … | … |

## What this release contains
<RELEASE CONTENTS from the scope reviewer, grouped by type: features, fixes, other>

## Conditions to launch
1. <each BLOCKER, then MAJOR, then not-assessable criterion — one line, commit or file:line>

## Deploy checklist
- <from the deployment reviewer>

## 1. Change scope controlled — <verdict>
<summary, findings BLOCKER → MAJOR → MINOR, *Checked:* … *Not checked:* …>

## 2. … (same shape for each criterion)

## Dismissed
- <findings dropped in Step 4 and why — "none">
```

And `README.md`, the summary a product owner reads first:

```markdown
# Launch approval — <release branch> · <date>

**Launch decision:** <worst repo decision>

| Repo | Kind | Branch | Decision | Scope | Edge cases | Security | Compat | Deploy |
|---|---|---|---|---|---|---|---|---|
| [<id>](<id>.md) | backend | release/1.5.0 | ⚠️ | ✅ | ⚠️ | ✅ | ✅ | ⚠️ |

## Conditions to launch
<every repo's conditions, prefixed with the repo id>

## Deploy order
<which repo deploys first and why — backend before the frontend that needs its new API,
migrations before code that reads new columns; "independent" when nothing links them>

## Not reviewed
<repos skipped in Step 1, with the reason>
```

Write every report and the summary in English.

## Step 6: Show it and offer the next step

Print the summary in the chat with the path to the folder. Then offer — each only on an explicit
yes: commit the report folder to the hub (following the git-workflow commit rule), post each
repo's report to its release merge request (`glab mr note create` / `gh pr comment`). After
fixes land on a release branch, run the skill again: a new head means a new range and a new report.

## Rules

- Review only the pinned range; never report pre-existing code on production as part of this release
- Never create a branch without a yes, never push without a second yes, never merge, tag or deploy
- Never give repos different release versions; one branch name for the whole launch
- Never create a release branch that is not named `release.X.Y.Z`
- Questions and reports in English only
- Never check out, reset or rebase a clone in `repos/`
- Never count `NOT ASSESSABLE` as `PASS`, and never report `APPROVED` with merge conflicts
- Never print a secret a reviewer found — cite its file and line only
- User instructions override automation: if the user explicitly overrides a step, respect it
