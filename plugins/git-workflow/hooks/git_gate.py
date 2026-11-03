#!/usr/bin/env python3
"""PreToolUse gate for Bash: commit-message format, and the ticket-scope check before an MR.

1. `git commit -m ...` — the subject must match the format in rules/commit-message.md.
   Steps aside when the repository enforces its own format (commit-msg hook / commitlint).
2. `glab mr create` / `gh pr create` — denied until the verify-ticket-scope skill has written
   a PASS (or an explicit user waiver) for the current HEAD into <git-dir>/pb-scope-ok.

A hub whose own work is not ticketed sets `commits.ticket_required: false` in its
brain.config.json: its commits may leave the ticket out, and its MRs have no ticket scope to check.

Never blocks on its own failure: an unparseable command or an internal error is let through,
because a gate that breaks the agent when the gate itself is wrong loses everyone's trust.
"""

import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

TYPES = "feat fix critical-fix bug refactor perf test docs style chore ci build revert"
COMMIT_RE = re.compile(
    rf"^({'|'.join(TYPES.split())})"
    r"(\([a-z][a-z0-9-]*\))?: \[[A-Z][A-Z0-9]*-[0-9]+\] \S.*$"
)
UNTICKETED_RE = re.compile(
    rf"^({'|'.join(TYPES.split())})"
    r"(\([a-z][a-z0-9-]*\))?: (\[[A-Z][A-Z0-9]*-[0-9]+\] )?\S.*$"
)
EXEMPT_PREFIXES = ("Merge ", "Revert ", "fixup!", "squash!", "amend!")
# A repository that already enforces its own commit format wins over ours.
OWN_FORMAT_FILES = (
    ".husky/commit-msg", ".githooks/commit-msg", ".commitlintrc", ".commitlintrc.json",
    ".commitlintrc.js", ".commitlintrc.cjs", ".commitlintrc.yml", ".commitlintrc.yaml",
    "commitlint.config.js", "commitlint.config.cjs", "commitlint.config.mjs",
    "commitlint.config.ts",
)
BOUNDARY = r"(?:^|[;&|\n(]|\bthen\b|\bdo\b)\s*(?:[A-Za-z_][A-Za-z0-9_]*=\S*\s+)*(?:\S*/)?"
COMMIT_CALL = re.compile(BOUNDARY + r"git((?:\s+-C\s+\S+|\s+-c\s+\S+)*)\s+commit\b(.*)", re.S)
MR_CALL = re.compile(BOUNDARY + r"(?:glab\s+mr\s+create|gh\s+pr\s+create)\b")
HEREDOC = re.compile(r"<<-?\s*['\"]?(\w+)['\"]?\n(.*?)\n\s*\1\b", re.S)
SEPARATORS = {"&&", "||", ";", "|", "&"}


def emit(decision, reason):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": decision,
        "permissionDecisionReason": reason,
    }}))
    sys.exit(0)


def git(workdir, *args):
    out = subprocess.run(["git", "-C", workdir, *args], capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else ""


def workdir_for(cmd, payload, git_opts=""):
    """The tree the command acts on: `git -C <dir>`, a leading `cd <dir> &&`, or the cwd."""
    base = payload.get("cwd") or os.getcwd()
    lead = re.match(r"\s*cd\s+(\"[^\"]+\"|'[^']+'|[^\s;&|]+)", cmd)
    if lead:
        base = os.path.join(base, os.path.expanduser(shlex.split(lead.group(1))[0]))
    c_dir = re.search(r"-C\s+(\"[^\"]+\"|'[^']+'|\S+)", git_opts)
    if c_dir:
        base = os.path.join(base, os.path.expanduser(shlex.split(c_dir.group(1))[0]))
    return base


def ticket_required(root):
    """False only when the repo's own brain.config.json says its work carries no ticket."""
    if not root:
        return True
    try:
        config = json.loads((Path(root) / "brain.config.json").read_text(encoding="utf-8"))
        return (config.get("commits") or {}).get("ticket_required") is not False
    except (OSError, ValueError, AttributeError):
        return True


def commit_subject(rest):
    """The subject of `git commit <rest>`, "" when none is given inline, None to skip."""
    heredoc = HEREDOC.search(rest)
    if heredoc and re.search(r"(-m|--message)(=|\s+)\S*\$\(cat\s+<<", rest):
        return heredoc.group(2).strip().splitlines()[0].strip() if heredoc.group(2).strip() else ""
    try:
        tokens = shlex.split(rest, posix=True)
    except ValueError:
        return None
    for i, tok in enumerate(tokens):
        if tok in SEPARATORS:
            break
        if tok in ("-F", "--file") or tok.startswith("--file="):
            return None  # message comes from a file we can't see here
        if tok in ("-m", "--message") or (re.fullmatch(r"-[a-zA-Z]*m", tok) and not tok.startswith("--")):
            return tokens[i + 1].splitlines()[0].strip() if i + 1 < len(tokens) else None
        if tok.startswith("--message="):
            return tok.split("=", 1)[1].splitlines()[0].strip()
        if re.fullmatch(r"-m.+", tok):
            return tok[2:].splitlines()[0].strip()
    return ""


def check_commit(cmd, payload):
    match = COMMIT_CALL.search(cmd)
    if not match:
        return
    subject = commit_subject(match.group(2))
    if not subject or subject.startswith(EXEMPT_PREFIXES):
        return  # no inline message (editor, --no-edit, -F) or a git-generated one
    root = git(workdir_for(cmd, payload, match.group(1)), "rev-parse", "--show-toplevel")
    if root and any((Path(root) / f).exists() for f in OWN_FORMAT_FILES):
        return
    ticketed = ticket_required(root)
    if (COMMIT_RE if ticketed else UNTICKETED_RE).match(subject):
        return
    emit("deny", (
        f'Commit message rejected: "{subject}"\n\n'
        f"Required: type(scope): {'[TASK-ID] ' if ticketed else ''}description\n"
        f"  type  : {TYPES}\n"
        "  scope : optional, lowercase letters/digits/dashes\n"
        + ("  TASK-ID: uppercase key + number, e.g. [PROJ-123] — take it from the branch name or ask the user\n"
           "Example: feat(auth): [PROJ-101] add two-factor authentication flow\n"
           if ticketed else
           "  This repo's work carries no ticket (commits.ticket_required: false in brain.config.json).\n"
           "Example: docs(runbook): explain the release train\n")
        + "(git-workflow plugin — see its commit-message rule)"
    ))


def check_mr(cmd, payload):
    if not MR_CALL.search(cmd):
        return
    if os.environ.get("PB_SCOPE_WAIVED") == "1":
        emit("allow", "Ticket-scope gate waived via PB_SCOPE_WAIVED=1.")
    workdir = workdir_for(cmd, payload)
    if not ticket_required(git(workdir, "rev-parse", "--show-toplevel")):
        return  # no ticket, so no ticket scope to check
    git_dir = git(workdir, "rev-parse", "--absolute-git-dir")
    if not git_dir:
        emit("ask", f"Not inside a git repository ({workdir}); cannot verify ticket scope.")
    head = git(workdir, "rev-parse", "HEAD")
    marker = Path(git_dir) / "pb-scope-ok"
    lines = marker.read_text().splitlines() if marker.exists() else []
    if lines and head and lines[0].strip() == head:
        waived = next((l for l in lines if l.startswith("WAIVED:")), "")
        emit("allow", f"Ticket scope waived by the user for this HEAD. {waived} — record these in the MR description."
             if waived else "Ticket-scope check passed for this HEAD.")
    stale = f" (marker is for {lines[0][:12]}, HEAD is {head[:12]} — new commits landed since)" if lines else ""
    emit("deny", (
        f"Ticket-scope check not recorded for the current HEAD{stale}.\n\n"
        "Run the verify-ticket-scope skill before creating this MR (git-workflow plugin).\n"
        "- PASS       -> the skill records the marker; retry this command.\n"
        "- BLOCKED    -> show the NOT MET items and ask the user to waive explicitly. Never waive on their behalf.\n"
        "- UNVERIFIED -> surface the reason and ask the user whether to proceed without the check."
    ))


def main():
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return
    cmd = (payload.get("tool_input") or {}).get("command") or ""
    if "git" not in cmd and "glab" not in cmd and "gh " not in cmd:
        return
    check_commit(cmd, payload)
    check_mr(cmd, payload)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        pass  # never break the agent because the gate is broken
