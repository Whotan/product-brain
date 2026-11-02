"""Self-check for plugins/brain-harness: the base rules it injects and its gate hook.

Run: python3 tests/test_brain_harness.py
"""

import json
import os
import shutil
import subprocess
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


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
    print(f"ok ({len(tests)} tests)")


if __name__ == "__main__":
    main()
