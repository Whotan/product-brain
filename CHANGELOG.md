# Changelog

All notable changes to Product Brain. Versions follow semver and match `VERSION`; every plugin in
the marketplace ships at the same version. Releases before 1.7.0 are recorded in the Git history.

## 1.8.0 — 2026-11-24

### Added

- **`support-desk` plugin:** a shared review page on claude.ai for a Jira Service Management
  project, so the whole team can triage support tickets and approve what goes back to the customer.
  - `/support-desk:update` pulls new tickets, new customer replies and status changes since the page
    was last built, fact-checks each one with the hub's triage rules, drafts the reply and a
    suggested status move, and republishes the page. Nothing goes to Jira.
  - `/support-desk:apply` sends only what a teammate approved on the page: posts replies as public
    comments, makes status moves (following configured routes where Jira has no direct transition),
    and redrafts rows that carry a reviewer's note. Stale approvals and unfilled placeholders are
    blocked, never forced.
  - **Create linked issue:** a button on each ticket requests a task or bug in the hub's tracker
    project. `apply` checks for duplicates, writes it up with `task-workflow:task-description`,
    creates it with `task-workflow:task-ticket`, and links it to the support ticket.
  - Configured per hub in `brain.config.json > support_desk`; each person uses their own Jira token.
    Engine `scripts/desk.py` is standard-library only; tests in `tests/test_support_desk.py`.

## 1.7.0 — 2026-11-24

### Added

- **`peer-review-mr` skill (git-workflow plugin):** reviews a teammate's merge request / pull
  request as the reviewer, like a co-worker who knows the project.
  - Checks out the MR in its own detached worktree; never commits to or pushes the author's branch.
  - Builds a rulebook for the MR from the hub (constitution, vocabulary, domains, DESIGN.md,
    decisions, conventions), the repo's own docs and tooling config, and the enabled plugins'
    rules (brain-harness, git-workflow, stack-*, guardrails, repo-docs). Findings cite the rule
    they break.
  - Reviews every changed file, tests included, with a coverage ledger; checks the impact on code
    outside the diff; runs type-check, lint, related tests, `guardrail range` and a test merge.
  - Measures the MR against its ticket and the hub's task folder (`plan.md`, `report.md`): flags
    unapproved scope and missing promised tests, and treats recorded decisions as by design.
  - Reports a verdict with Must fix / Should fix / Minor findings, what was checked and what was
    not. Posts a summary or inline threads, or approves, only on the user's word.
  - Re-reviews after the author pushes, with a status per earlier point.
- **`mr-area-reviewer` agent (git-workflow plugin):** a read-only reviewer for one area of a
  large MR, used by `peer-review-mr` to split big reviews.
- The git-workflow merge-request rule and the hub `CLAUDE.md` snippet now point to
  `peer-review-mr` for reviewing a teammate's MR.
