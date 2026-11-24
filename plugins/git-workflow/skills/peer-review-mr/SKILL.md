---
name: peer-review-mr
description: Review a teammate's merge request / pull request as the reviewer — in its own worktree, against its ticket, the hub's task plan and the repo's conventions — run the checks locally, report a verdict with Must fix / Should fix / Minor findings, and only on the user's word post comments (summary or inline threads) or approve. Also handles re-reviews after the author pushes. Use when asked to "review MR !<n>", given an MR/PR link to review, "check this MR", "the MR was updated, review again", or "do the final review".
argument-hint: "<MR/PR URL or number>"
allowed-tools: [Bash, Read, Glob, Grep, Write, Agent]
---

# peer-review-mr

Review someone else's MR the way a careful senior reviewer would, then let the user decide what
goes on the MR. This is the **reviewer** side. The **author** side — triaging the automated
signals on your own MR before marking it ready — is the `review-mr` skill.

"MR" means a GitLab merge request or a GitHub pull request. Detect the host from the URL or
`git remote get-url origin`; examples show GitLab (`glab`). For GitHub use `gh` and PR.

You are a reviewer, not the author:

- **Never commit to, push to, rebase, or merge the MR's branch**, and never edit its files.
  Findings go to the author as comments.
- **Nothing is posted and nothing is approved without the user's explicit word.** Everything you
  post appears under the user's account.

## Step 1: Locate the MR and refresh

Parse the project path and number from the URL (`…/<group>/<project>/-/merge_requests/<n>`,
`…/<owner>/<repo>/pull/<n>`). In a Product Brain hub, the repo is the clone under `repos/` whose
remote matches; pull the hub first (`pb sync`, or `git pull` in the hub and `git fetch` in the
clone) when the user asks for the latest or the clone is behind.

```bash
glab auth status        # stop and ask the user to log in if this fails; never log in for them
glab mr view <n> -R <group>/<project> -F json   # source/target branch, draft, author, description
```

If a fetch fails on a stale refspec or a deleted branch, work around it with explicit refspecs and
tell the user the one-line fix; don't rewrite their git config unasked.

## Step 2: Check it out in its own worktree

Review in a detached worktree so the main clone and any work in it stay untouched:

```bash
cd repos/<repo>
git fetch -q origin "<target>:refs/remotes/origin/<target>" "<source>:refs/remotes/origin/<source>"
git worktree add --detach "../<repo>-mr<n>" "origin/<source>"
```

Record the head SHA you review — every finding, link and re-review is pinned to it.

To run checks without a fresh install, symlink `node_modules` (or the stack's equivalent) from the
main clone **only when the lockfiles are identical** (`cmp` them); otherwise install in the
worktree. Say that you linked it.

## Step 3: Know the project, then build the rulebook

Review like a co-worker who knows the project: the yardstick is the project's knowledge and every
written guideline, not the existing threads or what an earlier session remembers. Threads and
memory only tell you what was already said.

**Project knowledge** (hub root, when present): `constitution.md` (principles that override
everything), `vocabulary.md` (product ↔ code terms — names in the diff should match), `domains.md`
and `DESIGN.md` (UI work), the relevant `docs/architecture/` and `docs/decisions/` entries, and the
graph (`graph/graph.json`, query it as the hub's `CLAUDE.md` says) for the area the MR touches.

**What this MR is measured against:**

- **The MR description** — what it claims to change, and any test or rollout notes.
- **The ticket** — key from the branch or title; fetch it from the connected tracker (scope,
  acceptance criteria).
- **The hub's task folder**, if the hub has `tasks.dir` in `brain.config.json`:
  `<dir>/<KEY>/description.md`, `plan.md` (approved UI rows, scope items, the tests it promised),
  `report.md` (recorded decisions). A behaviour the report records as a decision is *by design*,
  not a finding.

**The rulebook** — collect every guideline that applies to the changed files, and write the list
(source → rule ids or headings) to `<scratchpad>/mr<n>-rulebook.md`. Read each source in full:

| Source | Where |
|---|---|
| Hub conventions | `tasks.conventions` in `brain.config.json`, `docs/runbooks/`, `workflows/` |
| Repo docs | the repo's `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`, `docs/` (conventions, testing, architecture, MR guide, security, known issues) |
| Base rules | the `brain-harness` plugin's `rules/base-rules.md` |
| Git rules | this plugin's `rules/` (commit messages, branch naming, MR rules) |
| Stack rules | each enabled `stack-*` plugin's `rules/*.md` for the stacks in the diff (or its conventions skill) |
| Guardrails | the `guardrails` plugin's `rules/` for the stacks in the diff |
| Repo docs standard | the `repo-docs` plugin's standard, when the MR touches docs or should have |
| Tooling config | lint, formatter, type-check and analyzer configs in the repo (`eslint`, `phpstan`, `analysis_options.yaml`, `sonar-project.properties` exclusions, …) |

Enabled plugins are listed in the hub's `.claude/settings.json` (`enabledPlugins`); their files are
under `$CLAUDE_CONFIG_DIR/plugins/cache/product-brain/<plugin>/<version>/` (fall back to
`~/.claude/` when the variable is unset). A source that doesn't exist is noted, not guessed.

**The conversation so far** — existing discussions and replies, and the newest review-bot note.
**Automated signals** — pipeline status and the SonarQube gate, read as in `review-mr` Steps 1–3.
Neither replaces your own review: a green pipeline and a clean bot note are inputs, not a verdict.

## Step 4: Review every changed file

```bash
git diff --stat "origin/<target>...HEAD"
git diff --name-status "origin/<target>...HEAD" > "<scratchpad>/mr<n>-files.txt"
git log --oneline "origin/<target>..HEAD"
```

Keep a ledger with one row per changed file — including tests, migrations, config, CI, i18n and
docs — and mark each `reviewed` only after reading its full hunks and enough surrounding code to
judge them. Lockfiles and generated files get a sanity check (the lockfile change matches the
manifest change; generated output was regenerated, not hand-edited). The review is not finished
while a row is unmarked.

**Large MRs** (roughly over 40 files or 3,000 changed lines): split the ledger by area (module,
app, layer) and give each area to the `mr-area-reviewer` agent (this plugin; never an untyped
sub-agent) with the same yardstick — the ticket and plan, the
rulebook file, and the project knowledge paths — asking for findings with `file:line` and its
ledger rows back. Then check the cross-area seams (API contracts, shared types, migrations vs.
models) yourself. Say in the report that the review was split.

For each file, check:

- **Correctness** — logic, edge cases (time zones, midnight, empty/null, races, stale async
  replies), error handling, security (input validation, authorisation, injection, secrets).
- **Impact beyond the diff** — for every changed public function, type, route, event, config key
  or DB column, find its other users (`grep` and the graph) and check they still hold. A changed
  contract with an untouched caller is a finding.
- **Every rulebook rule that applies** — go through the rulebook, not memory. Also run the
  guardrails engine on the branch when the plugin is installed:
  `guardrail range origin/<target>` from the worktree.
- **Scope** — every change maps to the plan or ticket. Unapproved visible changes (spacing, text,
  layout, behaviour) are findings even when they look like improvements.
- **Tests** — the tests the plan promised exist; new behaviour and fixed bugs have a test that
  would fail without the change; tests assert behaviour, not implementation details; no skipped,
  focused or flaky-by-design tests (fixed sleeps, real clocks, network).
- **Description vs. reality** — claims with no commit behind them, renamed scripts, items already
  fixed on the target branch (`git log origin/<target> -- <path>`).
- **Project fit** — names match `vocabulary.md`, the change respects the constitution and recorded
  decisions, hard-coded values don't couple unrelated files, comments say what the code does.
- **Reviewability** — formatter-only churn mixed into real changes; commits that don't follow the
  commit-message rule.

## Step 5: Run the checks

Run what the conventions name for the changed area, in the worktree: type-check, lint on changed
files, the related tests. Don't run the full end-to-end suite unless asked. Then check the merge:

```bash
git merge-tree --write-tree "origin/<target>" HEAD >/dev/null && echo "merges clean" || echo "CONFLICTS"
```

Tell code failures apart from infrastructure failures (a runner that couldn't download a plugin,
a full disk, a timed-out fetch): an infra failure is "retry the job", not a finding against the
author. Never retry jobs or play manual jobs without the user's word.

## Step 6: Report to the user

Report in the chat first. Lead with the verdict and the head SHA:

```text
MR !<n> (<KEY>, <title>) at <sha>: <approve | approve with follow-ups | changes requested>

Must fix      — blocks approval: bugs, failing lint/tests, unapproved scope, missing promised tests
Should fix    — real but not blocking
Minor / Nit   — no action needed to merge

Each finding: what is wrong, file:line, why it matters, the smallest fix.

Checked and fine — the risky things you verified and found correct
Coverage      — files reviewed n/n (split by area: yes/no); rulebook sources read, and any missing
Ran           — each command and its result (guardrail range included); pipeline id and status; Sonar gate; merge state
Not checked   — what you didn't run or read, and why
```

Each finding that breaks a written rule names its source (`stack-angular/rules/rxjs.md`,
`constitution.md §3`, `plan.md U1`), so the author can check it rather than take it on trust.

A skipped source is stated, never implied clean. End by asking what to post: nothing, one summary
comment, or the summary plus inline threads — and whether to approve.

## Step 7: Post and approve — only on the user's word

Write the bodies in plain English, as normal prose. Link files at the reviewed SHA.

- **Summary comment:** `glab mr note create <n> -R <group>/<project> -m "$(cat <file>)"`
  (GitHub: `gh pr comment <n> --body-file <file>`).
- **Inline threads:** one per finding that has a line. Take the SHAs from the MR's latest diff
  version and post to `discussions`:

  ```bash
  glab api "projects/<url-encoded path>/merge_requests/<n>/versions" | python3 -c \
    'import json,sys; v=json.load(sys.stdin)[0]; print(v["base_commit_sha"], v["start_commit_sha"], v["head_commit_sha"])'
  # body: {"body": "...", "position": {"position_type": "text", "base_sha": B, "start_sha": S,
  #        "head_sha": H, "old_path": P, "new_path": P, "new_line": L}}
  glab api -X POST "projects/<url-encoded path>/merge_requests/<n>/discussions" \
    -H "Content-Type: application/json" --input <json-file>
  ```

  GitHub: one `gh api repos/<owner>/<repo>/pulls/<n>/reviews` call with `event: COMMENT` and a
  `comments` array of `{path, line, body}`.
- **Approve:** `glab mr approve <n> -R <group>/<project>` (GitHub: `gh pr review <n> --approve`).
  Never request changes, approve, merge, resolve the author's threads or change draft status unless
  the user said so. If the user says "just approve" while findings are unposted, approve, then
  list the findings that are still not on the MR.

Report the links to what you posted.

## Step 8: Re-review after the author pushes

When told the MR was updated:

1. Fetch, move the worktree to the new head, and diff from the last reviewed SHA
   (`git diff <old>..<new>`). If the target branch was merged in, re-diff against the new merge
   base and check the merge resolution.
2. Read new replies on your threads and anything new in the hub's task folder.
3. Re-run the Step 5 checks — new commits on the target can change lint rules or tests under the MR.
4. Report one row per earlier point:

   | # | Item | Status |
   |---|---|---|
   | 1 | … | Fixed / Partly fixed / Not addressed / By design (where recorded) / Moved to hub follow-up |

   plus any new findings in the new commits. On the final pass, say whether it is ready to approve
   and what non-blocking follow-ups remain (and where — code, ticket or hub doc).

Post follow-ups and approve only as in Step 7.

## Step 9: Clean up — when the user asks

Remove the symlinked dependency folder first, then the worktree; never touch the main clone or
other worktrees:

```bash
rm "../<repo>-mr<n>/node_modules" 2>/dev/null   # the link only, never the target
git worktree remove "../<repo>-mr<n>"
```

## Rules

- Never commit, push, rebase or merge on the MR's branch; never edit its files
- Never post, approve, request changes, resolve threads or retry jobs without the user's explicit word
- Never report a finding without file:line and the reason it matters
- Never call the review done while a changed file is unreviewed or a rulebook source unread
- Never let existing threads, bot notes, a green pipeline or memory stand in for your own review
- Never flag as a defect a behaviour the hub's task report records as a decision; call it by design
- Never count an infrastructure failure against the author
- Never report a partial review as clean — say what wasn't run
- Never reuse a dependency folder from the main clone when the lockfiles differ
- User instructions override automation: if the user explicitly overrides a step, respect it
