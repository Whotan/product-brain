"""Self-check for skills/release-notes/scripts/open-release-mr.py.

Run: python3 tests/test_open_release_mr.py
"""

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills/release-notes/scripts/open-release-mr.py"


def git(cwd, *args):
    subprocess.run(["git", "-C", str(cwd), "-c", "user.email=t@t", "-c", "user.name=t", *args],
                   check=True, capture_output=True)


def commit(repo, msg, name):
    (repo / name).write_text(msg + "\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", msg)


def run(hub, *args, path=None):
    env = dict(os.environ)
    if path is not None:
        env["PATH"] = path
    proc = subprocess.run([sys.executable, str(SCRIPT), "--hub", str(hub), "--no-fetch", *args],
                          capture_output=True, text=True, env=env)
    return proc.returncode, proc.stdout, proc.stderr


def shim(folder, name, body):
    p = folder / name
    p.write_text("#!/bin/sh\n" + body + "\n")
    p.chmod(p.stat().st_mode | stat.S_IEXEC)


def check(cond, what):
    if not cond:
        print("FAIL:", what)
        sys.exit(1)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        origin = tmp / "github-origin.git"  # a path naming "github" so host detection picks gh
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
        hub = tmp / "hub"
        repo = hub / "repos/web-app"
        repo.mkdir(parents=True)
        git(repo, "init", "-q", "-b", "main")
        git(repo, "remote", "add", "origin", str(origin))
        commit(repo, "chore: init", "a.txt")
        git(repo, "push", "-q", "origin", "main")
        git(repo, "checkout", "-q", "-b", "release/1.4.0")
        commit(repo, "feat(auth): add SSO login", "b.txt")
        commit(repo, "fix(auth): stop token expiring early", "c.txt")
        commit(repo, "chore: bump deps", "d.txt")
        commit(repo, "temp", "e.txt")
        commit(repo, 'Revert "temp"', "f.txt")
        git(repo, "push", "-q", "origin", "release/1.4.0")
        (hub / "brain.config.json").write_text(json.dumps({
            "repos": [{"id": "web-app"}], "releases": {"primary_repo": "web-app", "production_branch": "main"}}))

        # 1. plan only: grouped, reverted pair dropped, nothing opened
        rc, out, err = run(hub)
        check(rc == 0 and "## Added" in out and "## Changed" in out and "## Fixed" in out, f"plan: {out}{err}")
        check("add SSO login" in out and "temp" not in out.replace("plan only", ""), "revert pair dropped")
        check("MCP tool" in out, "plan points at the MCP route too")

        # 2. --json: the plan as data, host from origin, which CLIs exist
        rc, out, err = run(hub, "--json")
        plan = json.loads(out)
        check(rc == 0 and plan["head"] == "release/1.4.0" and plan["base"] == "main"
              and plan["title"] == "Release 1.4.0" and plan["host"] == "github"
              and "## Added" in plan["body"] and set(plan["cli"]) == {"gh", "glab"}, f"json plan: {plan}")
        check("github-origin" not in out, "the origin URL is never printed")

        # 3. --create with no gh / glab at all: nothing opened, plan shown, exit 3 - not a crash
        bare = tmp / "bare-path"
        bare.mkdir()
        (bare / "git").symlink_to(shutil.which("git"))
        rc, out, err = run(hub, "--create", path=str(bare))
        check(rc == 3 and "not installed" in err and "MCP tool" in err and "## Added" in out,
              f"no CLI: exit {rc} {err}")

        # 4. --create with a gh on PATH: it is called with the plan
        shims = tmp / "shims"
        shims.mkdir()
        log = tmp / "gh-args.txt"
        shim(shims, "gh", f'printf "%s\\n" "$@" > "{log}"; echo https://github.com/o/r/pull/9')
        rc, out, err = run(hub, "--create", path=f"{shims}{os.pathsep}{os.environ['PATH']}")
        args = log.read_text().split("\n")
        check(rc == 0 and args[:2] == ["pr", "create"] and "--base" in args and "main" in args
              and "release/1.4.0" in args and "Release 1.4.0" in args, f"gh called with the plan: {args}")
        check(any("## Added" in a for a in args), "the body went to gh")

        # 5. --host gitlab uses glab
        glog = tmp / "glab-args.txt"
        shim(shims, "glab", f'printf "%s\\n" "$@" > "{glog}"')
        rc, out, err = run(hub, "--create", "--host", "gitlab", path=f"{shims}{os.pathsep}{os.environ['PATH']}")
        gargs = glog.read_text().split("\n")
        check(rc == 0 and gargs[:2] == ["mr", "create"] and "--target-branch" in gargs and "--source-branch" in gargs,
              f"glab called: {gargs}")

        # 6. an origin that names neither host: --json says null, --create exits 3 with advice
        other = tmp / "plain-origin.git"
        shutil.copytree(origin, other)
        git(repo, "remote", "set-url", "origin", str(other))
        rc, out, err = run(hub, "--json")
        check(rc == 0 and json.loads(out)["host"] is None, "unknown host reported as null")
        rc, out, err = run(hub, "--create", path=f"{shims}{os.pathsep}{os.environ['PATH']}")
        check(rc == 3 and "could not tell" in err, f"unknown host: exit {rc} {err}")

        # 7. nothing ahead of main
        git(repo, "remote", "set-url", "origin", str(origin))
        rc, out, err = run(hub, "--branch", "main")
        check(rc == 0 and "nothing to open" in out, f"nothing ahead: {out}")

    print("ok")


if __name__ == "__main__":
    main()
