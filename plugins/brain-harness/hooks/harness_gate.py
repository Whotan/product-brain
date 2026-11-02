#!/usr/bin/env python3
"""PreToolUse gate for the brain harness's enforceable base rules.

Everywhere:
  - no force push (`--force-with-lease` is allowed);
  - no writes to `.claude/agent-memory/`: lessons become proposed edits to the hub's conventions.
Only in agent runs (PB_AGENT_RUN=1), so a person's local session is never blocked by them:
  - the model never runs a git command that writes history or a remote (commit, push, merge, rebase,
    cherry-pick, revert, am); the run script does, after its checks (rule 9). The match is broad on
    purpose: in an agent run a false positive costs a rephrase, and text matching is backed by a
    git-level hook in the run image;
  - sub-agents must be named types, never untyped or `general-purpose`.

Never blocks on its own failure: unreadable input or an internal error lets the call through,
because a gate that breaks the session when the gate itself is wrong loses everyone's trust.
"""

import json
import os
import re
import sys

BOUNDARY = r"(?:^|[;&|\n(]|\bthen\b|\bdo\b)\s*(?:[A-Za-z_][A-Za-z0-9_]*=\S*\s+)*(?:\S*/)?"
GIT_CALL = re.compile(BOUNDARY + r"git(?:\s+-C\s+\S+|\s+-c\s+\S+)*\s+(commit|push)\b([^;&|\n]*)")
SHELL_C = re.compile(r"\b(?:ba|z)?sh\s+-c\s+(\"[^\"]*\"|'[^']*')")
# Agent runs: `git`, any global options, then a verb that writes history or a remote, anywhere.
GLOBAL_OPTS = r"(?:\s+(?:-[Cc]\s+(?:\"[^\"]*\"|'[^']*'|\S+)|--?[\w-]+(?:=\S+)?))*"
AGENT_GIT = re.compile(r"\bgit" + GLOBAL_OPTS + r"\s+(?:commit|push|merge|rebase|cherry-pick|revert|am)\b")
FORCE = re.compile(r"(?:^|\s)(?:--force(?![-\w])|-[A-Za-z]*f[A-Za-z]*)(?=\s|$)")
UNTYPED = {"", "general-purpose"}


def emit_deny(reason):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }}))
    sys.exit(0)


def git_calls(cmd, depth=0):
    """(verb, arguments) for every `git commit` / `git push`, including inside `bash -c "…"`."""
    calls = [(m.group(1), m.group(2)) for m in GIT_CALL.finditer(cmd)]
    if depth < 3:
        for inner in SHELL_C.finditer(cmd):
            calls += git_calls(inner.group(1)[1:-1], depth + 1)
    return calls


def check_bash(cmd, agent_run):
    if agent_run and AGENT_GIT.search(cmd):
        return ("Agent runs never commit, push, merge or rebase: the run script does that after its "
                "checks (base rule 9). Leave the changes in the working tree. This check matches "
                "text, so a search for these words is refused too: rephrase it.")
    for verb, args in git_calls(cmd):
        if verb == "push" and FORCE.search(args):
            return "No force push. Use --force-with-lease if a rewrite is truly needed."
    return None


def check_subagent(tool_input, agent_run):
    if agent_run and (tool_input.get("subagent_type") or "").strip() in UNTYPED:
        return ("Agent runs use named sub-agents only (for example impl-standard or impl-careful), "
                "never an untyped or general-purpose one.")
    return None


def check_write(tool_input):
    path = (tool_input.get("file_path") or "").replace("\\", "/")
    if "/.claude/agent-memory/" in path:
        return ("Lessons go into the hub's conventions as a proposed edit, not into agent memory "
                "inside a product repo.")
    return None


def main():
    try:
        payload = json.loads(sys.stdin.read() or "{}")
        tool = payload.get("tool_name") or ""
        tool_input = payload.get("tool_input") or {}
        agent_run = os.environ.get("PB_AGENT_RUN") == "1"
        if tool == "Bash":
            reason = check_bash(tool_input.get("command") or "", agent_run)
        elif tool in ("Agent", "Task"):
            reason = check_subagent(tool_input, agent_run)
        elif tool in ("Edit", "Write", "MultiEdit"):
            reason = check_write(tool_input)
        else:
            reason = None
    except Exception:
        return
    if reason:
        emit_deny(reason)


if __name__ == "__main__":
    main()
