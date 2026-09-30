#!/usr/bin/env python3
"""Open the merge/pull request that ships the latest release branch to production.

This is a **different** document from the client note and the internal note:
a short, English-only, bullet-point summary meant to live as a GitHub pull
request / GitLab merge request description, built straight from
`git log <production>..<release branch>` - never translated, never prose. See
`writing-the-client-note.md` for the client note's contract; this script does
not touch it and does not require facts.json to exist first.

Bullets are grouped by Conventional Commits type, same classification
gather-release-facts.py uses:
    feat                -> Added
    fix                  -> Fixed
    perf/refactor/build/ci/chore/style/docs/test -> Changed
    anything else (no conventional prefix) -> Other changes (never guessed)
A commit later reverted inside the same range, and the revert commit itself,
are both dropped - a reverted change never shipped (Accuracy rules).

Config (brain.config.json):
    releases.primary_repo           which repo's clone to open the MR in (default; --repo overrides)
    releases.production_branch      the MR/PR's base branch
    releases.release_branch_regex   which branch counts as "a release branch"
                                     (default: ^(release|hotfix)[-/._]), to find the latest one

Usage:
    python open-release-mr.py                         plan only: prints base, head, title, body
    python open-release-mr.py --create                 opens it for real (gh or glab, auto-detected
                                                         from the clone's `origin` remote)
    python open-release-mr.py --repo web-app --create
    python open-release-mr.py --branch release/1.4.0 --create   skip picking "the latest" branch
    python open-release-mr.py --host gitlab --create    when the remote URL doesn't say which host

Opening a merge/pull request is a visible, hard-to-undo action, so this prints
the plan and stops there unless you pass --create.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True

from pathlib import Path

from _hub import Config, find_hub, safe_ref, utf8_stdio

UNIT = "\x1f"

DEFAULT_RELEASE_BRANCH_REGEX = r"^(release|hotfix)[-/._]"

CONVENTIONAL = re.compile(
    r"^(?P<type>feat|fix|perf|refactor|docs|test|build|ci|chore|style|revert)"
    r"(?:\((?P<scope>[^)]*)\))?(?P<breaking>!)?:\s*(?P<subject>.+)$",
    re.IGNORECASE,
)
REVERTS = re.compile(r'^Revert\s+"(.+)"\s*$', re.IGNORECASE)

SECTION_FOR_TYPE = {
    "feat": "Added",
    "fix": "Fixed",
    "perf": "Changed",
    "refactor": "Changed",
    "build": "Changed",
    "ci": "Changed",
    "chore": "Changed",
    "style": "Changed",
    "docs": "Changed",
    "test": "Changed",
}
SECTION_ORDER = ["Added", "Changed", "Fixed", "Other changes"]


def git(repo: Path, *args: str, check: bool = True) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if check and proc.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed in {repo.name}: {proc.stderr.strip()}")
    return proc.stdout


def latest_release_branch(repo: Path, pattern: re.Pattern, production: str) -> str:
    """The remote branch matching `pattern` whose tip was committed most recently.

    Sorted by commit date, not by name - a release_branch_regex like the default
    (`^(release|hotfix)[-/._]`) carries no version to sort on, and a branch's own
    naming scheme is not this script's business to parse.
    """
    raw = git(repo, "for-each-ref", "--sort=-committerdate",
              "--format=%(refname:short)" + UNIT + "%(committerdate:iso-strict)",
              "refs/remotes/origin")
    candidates = []
    for line in raw.splitlines():
        if not line.strip() or UNIT not in line:
            continue
        ref, when = line.split(UNIT)
        name = ref.split("/", 1)[1] if ref.startswith("origin/") else ref
        if name in (production, "HEAD") or not pattern.search(name):
            continue
        candidates.append((name, when))
    if not candidates:
        available = sorted({r.split("/", 1)[1] for r in git(repo, "branch", "-r").split()
                            if "/" in r and "HEAD" not in r})
        raise SystemExit(
            f"no remote branch matches releases.release_branch_regex ({pattern.pattern!r}) in "
            f"{repo.name}. Remote branches: {', '.join(available) or '(none)'}"
        )
    return candidates[0][0]


def commits_between(repo: Path, base: str, head: str) -> list:
    fmt = UNIT.join(["%H", "%s"])
    raw = git(repo, "log", "--no-merges", f"--format={fmt}", f"origin/{base}..origin/{head}")
    commits = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        sha, subject = line.split(UNIT)
        match = CONVENTIONAL.match(subject)
        commits.append({
            "sha": sha[:8],
            "subject": (match.group("subject") if match else subject).strip(),
            "type": match.group("type").lower() if match else None,
            "scope": match.group("scope") if match else None,
        })
    return commits


def drop_reverted(commits: list) -> list:
    """Remove a commit and the revert that undid it, inside this same range.

    A change reverted before it ever reached production is not "fixed" or
    "added" - it never shipped (release-notes' own Accuracy rules).
    """
    reverted_subjects = set()
    for commit in commits:
        match = REVERTS.match(commit["subject"])
        if match:
            reverted_subjects.add(match.group(1).strip())
    if not reverted_subjects:
        return commits
    kept = []
    for commit in commits:
        subject = commit["subject"].strip()
        if subject in reverted_subjects:
            continue  # the change this revert undid
        match = REVERTS.match(subject)
        if match and match.group(1).strip() in reverted_subjects:
            continue  # the revert commit itself
        kept.append(commit)
    return kept


def bucket(commits: list) -> dict:
    sections: dict = {name: [] for name in SECTION_ORDER}
    for commit in commits:
        section = SECTION_FOR_TYPE.get(commit["type"], "Other changes" if not commit["type"] else "Changed")
        line = f"- {commit['subject']}"
        if commit["scope"]:
            line = f"- **{commit['scope']}:** {commit['subject']}"
        line += f" (`{commit['sha']}`)"
        sections[section].append(line)
    return {name: lines for name, lines in sections.items() if lines}


def build_title(release_branch: str) -> str:
    version = re.search(r"\d+(?:\.\d+){1,3}", release_branch)
    return f"Release {version.group(0)}" if version else f"Release: {release_branch}"


def build_body(sections: dict) -> str:
    if not sections:
        return "No commits ahead of the base branch."
    parts = []
    for name in SECTION_ORDER:
        if name in sections:
            parts.append(f"## {name}\n" + "\n".join(sections[name]))
    return "\n\n".join(parts) + "\n"


def detect_host(repo: Path, override: str | None) -> str:
    if override:
        return override
    url = git(repo, "remote", "get-url", "origin", check=False).strip().lower()
    if "gitlab" in url:
        return "gitlab"
    if "github" in url:
        return "github"
    raise SystemExit(
        f"could not tell GitHub from GitLab in origin's URL ({url!r}) - pass --host github|gitlab"
    )


def create_mr(repo: Path, host: str, base: str, head: str, title: str, body: str) -> int:
    if host == "github":
        cli = "gh"
        cmd = [cli, "pr", "create", "--base", base, "--head", head, "--title", title, "--body", body]
    else:
        cli = "glab"
        cmd = [cli, "mr", "create", "--source-branch", head, "--target-branch", base,
              "--title", title, "--description", body, "--yes"]
    if shutil.which(cli) is None:
        raise SystemExit(
            f"`{cli}` is not on PATH. Install it: "
            + ("https://cli.github.com" if cli == "gh" else "https://gitlab.com/gitlab-org/cli")
        )
    proc = subprocess.run(cmd, cwd=str(repo))
    return proc.returncode


def main() -> int:
    utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", help="repo id to open the MR in (default: releases.primary_repo)")
    parser.add_argument("--branch", help="release branch to ship (default: the most recently "
                                         "committed branch matching releases.release_branch_regex)")
    parser.add_argument("--host", choices=["github", "gitlab"],
                        help="override auto-detection from the clone's origin remote")
    parser.add_argument("--no-fetch", action="store_true", help="skip git fetch")
    parser.add_argument("--create", action="store_true",
                        help="actually open the MR/PR; without it, only the plan is printed")
    parser.add_argument("--hub", help="hub root (default: walk up from the current directory)")
    args = parser.parse_args()

    cfg = Config(find_hub(args.hub))
    repo_id = args.repo or cfg.get("releases.primary_repo")
    repo = cfg.repo_path(repo_id)
    if not repo.is_dir():
        raise SystemExit(f"repo `{repo_id}` has no clone at {repo}")

    production = safe_ref(cfg.get("releases.production_branch"), "releases.production_branch")
    if args.branch:
        safe_ref(args.branch, "--branch")

    if not args.no_fetch:
        proc = subprocess.run(["git", "-C", str(repo), "fetch", "--prune", "--quiet", "origin"],
                              capture_output=True, text=True)
        if proc.returncode != 0:
            print(f"WARN: git fetch failed in {repo_id} ({proc.stderr.strip()[:200]}) - "
                  "working from what this clone already has", file=sys.stderr)

    pattern = re.compile(cfg.get("releases.release_branch_regex", None) or DEFAULT_RELEASE_BRANCH_REGEX)
    release_branch = args.branch or latest_release_branch(repo, pattern, production)

    commits = drop_reverted(commits_between(repo, production, release_branch))
    if not commits:
        print(f"{release_branch} has no commits ahead of {production} in {repo_id} - nothing to open.")
        return 0

    sections = bucket(commits)
    title = build_title(release_branch)
    body = build_body(sections)

    print(f"repo:   {repo_id}")
    print(f"base:   {production}")
    print(f"head:   {release_branch}")
    print(f"title:  {title}")
    print("body:")
    print(body)

    if not args.create:
        print("(plan only - pass --create to actually open this MR/PR)")
        return 0

    host = detect_host(repo, args.host)
    return create_mr(repo, host, production, release_branch, title, body)


if __name__ == "__main__":
    sys.exit(main())
