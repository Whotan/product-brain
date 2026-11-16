"""Self-check for plugins/brain-harness: the base rules it injects and its gate hook.

Run: python3 tests/test_brain_harness.py
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugins/brain-harness"

BASE_RULE_HEADINGS = [
    "1. Evidence, not claims",
    "2. Reports say what wasn't done",
    "3. One change, one ticket, one branch",
    "4. No self-approval",
    "5. Named owners decide",
    "6. Tests travel with the change",
    "7. Clients hear only what a human approved",
    "8. No production data, no personal data in messages",
    "9. Agent runs never commit or push",
    "10. The hub outranks the ticket",
]


def hook_commands(event):
    hooks = json.loads((PLUGIN / "hooks/hooks.json").read_text(encoding="utf-8"))["hooks"]
    return [h["command"] for entry in hooks.get(event, []) for h in entry["hooks"]]


def test_session_start_prints_base_rules():
    [cmd] = hook_commands("SessionStart")
    env = {**os.environ, "CLAUDE_PLUGIN_ROOT": str(PLUGIN)}
    # shutil.which: on Windows a bare "bash" resolves to System32's WSL launcher first
    out = subprocess.run([shutil.which("bash") or "bash", "-c", cmd], capture_output=True, text=True, env=env,
                         encoding="utf-8").stdout
    for heading in BASE_RULE_HEADINGS:
        assert heading in out, f"SessionStart output lacks the base rule {heading!r}"


def test_marketplace_lists_brain_harness():
    market = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text(encoding="utf-8"))
    entries = {p["name"]: p for p in market["plugins"]}
    assert "brain-harness" in entries, "brain-harness missing from marketplace.json"
    assert entries["brain-harness"]["source"] == "./plugins/brain-harness"
    manifest = json.loads((PLUGIN / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
    assert manifest["name"] == "brain-harness"


GATE = PLUGIN / "hooks/harness_gate.py"
AGENT_RUN = {"PB_AGENT_RUN": "1"}


def gate(tool, tool_input, agent_run=False, raw=None):
    """The gate's decision for one tool call: "deny", or None when it stays silent (allow)."""
    env = {k: v for k, v in os.environ.items() if k != "PB_AGENT_RUN"}
    if agent_run:
        env.update(AGENT_RUN)
    payload = raw if raw is not None else json.dumps(
        {"tool_name": tool, "tool_input": tool_input, "cwd": str(ROOT)})
    out = subprocess.run([sys.executable, str(GATE)], input=payload, capture_output=True,
                         text=True, env=env).stdout
    return json.loads(out)["hookSpecificOutput"]["permissionDecision"] if out.strip() else None


def bash(cmd, agent_run=False):
    return gate("Bash", {"command": cmd}, agent_run)


def test_gate_local_session_may_commit_and_push():
    assert bash('git commit -m "x"') is None
    assert bash("git push origin ch-1") is None
    assert bash("git push --force-with-lease origin ch-1") is None


def test_gate_agent_run_denies_commit_and_push():
    for cmd in ['git commit -m "x"', "git push origin ai-ch-1", "cd repo && git commit -am x",
                "git -C repo push origin ai-ch-1", "FOO=1 git commit -m x", 'bash -c "git push"',
                "sh -c 'git commit -m x'", "git status; git push", "/usr/bin/git push"]:
        assert bash(cmd, agent_run=True) == "deny", cmd


def test_gate_agent_run_denies_wrapped_and_history_writing_git():
    for cmd in ["env FOO=1 git commit -m x", "timeout 60 git push", "nohup git push &",
                "command git commit -m x", "exec git push", "xargs git push",
                "if git commit -m x; then echo ok; fi", "! git push", "{ git push; }", "`git push`",
                "bash -lc 'git push'", "git --no-pager commit -m x", "git --git-dir=.git commit -m x",
                'git -C "my repo" push', "git merge origin/develop", "git rebase develop",
                "git cherry-pick abc123", "git revert HEAD", "git am < fix.patch"]:
        assert bash(cmd, agent_run=True) == "deny", cmd


def test_gate_agent_run_allows_read_only_git():
    for cmd in ["git status", "git diff --stat", "git log --oneline -3", "git add -A",
                "git fetch origin", "git show HEAD"]:
        assert bash(cmd, agent_run=True) is None, cmd


def test_gate_denies_force_push_everywhere():
    assert bash("git push --force origin ch-1") == "deny"
    assert bash("git push -f origin ch-1") == "deny"
    assert bash("git push origin ch-1 --force") == "deny"


def test_hooks_register_gate_for_every_gated_tool():
    hooks = json.loads((PLUGIN / "hooks/hooks.json").read_text(encoding="utf-8"))["hooks"]
    [entry] = hooks["PreToolUse"]
    assert set(entry["matcher"].split("|")) == {"Bash", "Agent", "Task", "Edit", "Write", "MultiEdit"}
    assert "harness_gate.py" in entry["hooks"][0]["command"]


def test_gate_agent_run_requires_typed_subagents():
    for tool in ("Agent", "Task"):
        assert gate(tool, {"prompt": "x"}, agent_run=True) == "deny"
        assert gate(tool, {"subagent_type": "", "prompt": "x"}, agent_run=True) == "deny"
        assert gate(tool, {"subagent_type": "general-purpose", "prompt": "x"}, agent_run=True) == "deny"
        assert gate(tool, {"subagent_type": "impl-careful", "prompt": "x"}, agent_run=True) is None


def test_gate_local_session_may_use_untyped_subagents():
    assert gate("Agent", {"subagent_type": "Explore", "prompt": "x"}) is None
    assert gate("Agent", {"prompt": "x"}) is None


def test_gate_denies_writes_to_agent_memory():
    for tool in ("Edit", "Write", "MultiEdit"):
        assert gate(tool, {"file_path": "/repo/.claude/agent-memory/notes.md"}) == "deny"
        assert gate(tool, {"file_path": "D:\\repo\\.claude\\agent-memory\\notes.md"}) == "deny"
        assert gate(tool, {"file_path": "/repo/app/Models/User.php"}) is None


def test_gate_fails_open_on_bad_input():
    assert gate(None, None, agent_run=True, raw="not json") is None
    assert gate(None, None, agent_run=True, raw="") is None


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
    print(f"ok ({len(tests)} tests)")


if __name__ == "__main__":
    main()
