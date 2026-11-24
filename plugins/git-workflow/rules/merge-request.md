# Branches and merge requests (git-workflow plugin)

"MR" below means a GitLab merge request or a GitHub pull request — the rules are the same.

## Branches

- Never commit directly to `main`, `develop`, or a release branch. Work on a branch.
- Branch names: `{type}-{ticket-key}-{short-description}`, lowercase letters, digits and dashes
  only — e.g. `feature-proj-123-user-auth`, `bug-proj-456-login-redirect`. Types: `feature`,
  `bug`, `hotfix`, `chore`, `refactor`, `test`, `docs`. If the repository documents or enforces a
  different scheme, follow the repository.
- Never force-push a shared or protected branch. Fix mistakes there with a revert.
- Before choosing an MR's target branch, check the real remote default
  (`git remote show origin | grep 'HEAD branch'`) or reuse the target of an already-open MR.
  Never assume `main` or `develop`.

## Before any MR is created

- **Always run the `verify-ticket-scope` skill before creating an MR** (`glab mr create`,
  `gh pr create`, or any MR tooling), including when the user asks for an MR directly and for
  draft MRs. A hook blocks `glab mr create` / `gh pr create` until the check has passed for the
  current HEAD.
- **Never create the MR while the scope check reports `BLOCKED`.** Present the `NOT MET` items
  and stop. Only the user may waive a blocked item; on waiver, record the waived items in the MR
  description.
- **`UNVERIFIED` is not a pass.** No tracker access, no ticket key, or no scope section on the
  ticket — surface the reason and ask the user whether to proceed without the check.
- **`UNVERIFIABLE` items never block.** Report them and continue.
- Never re-run the scope check to fish for a different answer, and never soften a `NOT MET`
  into `UNVERIFIABLE` to clear the gate.

## Before an MR is marked ready

- **Always run the `review-mr` skill after the pipeline passes and before marking the MR
  ready.** It collects the signals a human-thread review misses: static-analysis findings
  (e.g. SonarQube, which often posts no MR comments) and review-bot notes (which are often plain
  notes, not resolvable threads).
- Never mark an MR ready off a partial review. If a source was skipped (e.g. no `SONAR_TOKEN`),
  say so — skipped is not clean.
- The `sonar-preflight` agent can triage likely static-analysis findings locally, before the
  push that would otherwise cost a pipeline round trip.

## Reviewing a teammate's MR

- Use the `peer-review-mr` skill. Review in its own worktree, never commit to the author's branch,
  and post comments or approve only when the user says so.
