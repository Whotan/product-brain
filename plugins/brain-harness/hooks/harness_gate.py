#!/usr/bin/env python3
"""PreToolUse gate for the brain harness's enforceable base rules.

Everywhere:
  - no force push (`--force-with-lease` is allowed);
  - no writes to `.claude/agent-memory/`: lessons become proposed edits to the hub's conventions.
Only in agent runs (PB_AGENT_RUN=1), so a person's local session is never blocked by them:
  - the model never runs `git commit` or `git push`; the run script does, after its checks (rule 9);
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
    for verb, args in git_calls(cmd):
        if agent_run:
            return ("Agent runs never commit or push: the run script commits and pushes after "
                    "its checks (base rule 9). Leave the changes in the working tree.")
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
