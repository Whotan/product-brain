# Changelog

All notable changes to Product Brain. Versions follow semver and match `VERSION`; every plugin in
the marketplace ships at the same version. Releases before 1.7.0 are recorded in the Git history.

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
