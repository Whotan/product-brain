"""Self-check for plugins/git-workflow/hooks/git_gate.py and plugin version lockstep.

Run: python3 tests/test_git_gate.py
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GATE = ROOT / "plugins/git-workflow/hooks/git_gate.py"


def run(cmd, cwd, env=None):
    out = subprocess.run(
        [sys.executable, str(GATE)],
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": str(cwd)}),
        capture_output=True, text=True, env=env,
    ).stdout
    return json.loads(out)["hookSpecificOutput"]["permissionDecision"] if out.strip() else None


def git(cwd, *args):
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        repo.mkdir()
        git(repo, "init", "-q")
        git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "init")

        good = 'feat(auth): [PROJ-101] add two-factor flow'
        # commit messages
        assert run(f'git commit -m "{good}"', repo) is None
        assert run('git commit -m "added stuff"', repo) == "deny"
        assert run('git commit -m "[PROJ-1] feat: wrong order"', repo) == "deny"
        assert run(f'git add . && git commit -am "{good}" && git push', repo) is None
        assert run('git add -A && git commit -am "wip"', repo) == "deny"
        assert run(f'git commit --message="{good}"', repo) is None
        assert run(f"git commit -m \"$(cat <<'EOF'\n{good}\n\nBody line.\nEOF\n)\"", repo) is None
        assert run("git commit -m \"$(cat <<'EOF'\nbad subject\nEOF\n)\"", repo) == "deny"
        assert run(f"cd {repo} && git commit -m 'nope'", Path(tmp)) == "deny"
        assert run(f"git -C {repo} commit -m 'nope'", Path(tmp)) == "deny"
        assert run('git commit -m "Merge branch develop"', repo) is None
        assert run("git commit --amend --no-edit", repo) is None
        assert run("git commit -F msg.txt", repo) is None
        assert run('echo "git commit -m nope"', repo) is None
        assert run("git status", repo) is None
        for kind in ("critical-fix(payments)", "build", "revert(auth)"):
            assert run(f'git commit -m "{kind}: [PROJ-7] the app repos allow this type"', repo) is None, kind

        # a hub whose own work carries no ticket (commits.ticket_required: false in brain.config.json)
        hub = Path(tmp) / "hub"
        hub.mkdir()
        git(hub, "init", "-q")
        git(hub, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "init")
        (hub / "brain.config.json").write_text(json.dumps({"product": "x"}))
        assert run('git commit -m "chore(owners): add the repo owners"', hub) == "deny", "ticket required by default"
        (hub / "brain.config.json").write_text(json.dumps({"commits": {"ticket_required": False}}))
        assert run('git commit -m "chore(owners): add the repo owners"', hub) is None
        assert run(f'git commit -m "{good}"', hub) is None, "a ticket is still allowed"
        assert run('git commit -m "added stuff"', hub) == "deny", "the type is still required"
        assert run('glab mr create --fill', hub) is None, "no ticket, so no ticket scope to check"
        (hub / "brain.config.json").write_text("{not json")
        assert run('git commit -m "chore(owners): add the repo owners"', hub) == "deny", "unreadable config: default"

        (repo / ".husky").mkdir()
        (repo / ".husky/commit-msg").write_text("#!/bin/sh\n")
        assert run('git commit -m "repo owns its format"', repo) is None, "repo's own hook wins"

        # MR scope gate
        assert run('glab mr create --fill', repo) == "deny"
        assert run('gh pr create --fill', repo) == "deny"
        head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        marker = repo / ".git/pb-scope-ok"
        marker.write_text(head + "\n")
        assert run('glab mr create --fill', repo) == "allow"
        marker.write_text("0" * 40 + "\n")
        assert run('glab mr create --fill', repo) == "deny", "stale marker"
        assert run('glab mr view', repo) is None
        import os
        assert run('gh pr create', repo, env={**os.environ, "PB_SCOPE_WAIVED": "1"}) == "allow"

    # every plugin ships the repo VERSION, so a release bumps them all together
    version = (ROOT / "VERSION").read_text().strip()
    manifests = [ROOT / ".claude-plugin/plugin.json", *ROOT.glob("plugins/*/.claude-plugin/plugin.json")]
    for m in manifests:
        assert json.loads(m.read_text())["version"] == version, f"{m} is not at {version}"
    listed = {p["name"] for p in json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())["plugins"]}
    for d in (ROOT / "plugins").iterdir():
        assert d.name in listed, f"plugins/{d.name} missing from marketplace.json"
    print("ok")


if __name__ == "__main__":
    main()
