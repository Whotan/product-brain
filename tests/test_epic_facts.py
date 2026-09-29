"""Self-check for plugins/epic-approval/skills/epic-approval/scripts/gather-epic-facts.py.

Run: python3 tests/test_epic_facts.py
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "plugins/epic-approval/skills/epic-approval/scripts/gather-epic-facts.py"


def git(cwd, *args):
    subprocess.run(["git", "-C", str(cwd), "-c", "user.email=t@t", "-c", "user.name=t", *args],
                   check=True, capture_output=True)


def write(repo, path, text):
    p = repo / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def commit(repo, msg, **files):
    for path, text in files.items():
        write(repo, path.replace("__", "/"), text)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", msg)


def run(cwd, *args):
    proc = subprocess.run([sys.executable, str(SCRIPT), *args], cwd=cwd, capture_output=True, text=True)
    return proc.returncode, (json.loads(proc.stdout) if proc.returncode == 0 else proc.stderr)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        hub = Path(tmp) / "hub"
        (hub / "docs").mkdir(parents=True)
        (hub / "brain.config.json").write_text(json.dumps({
            "repos": [{"id": "api"}, {"id": "web"}, {"id": "mobile"}, {"id": "idle"}, {"id": "missing"}],
            "approvals": {"out": "docs/approvals"},
        }))

        # api: Laravel-shaped backend; last release is a tag; develop carries a feat -> minor
        api = hub / "repos/api"
        api.mkdir(parents=True)
        git(api, "init", "-q", "-b", "main")
        commit(api, "chore: [API-1] init", **{"composer.json": "{}\n", "app__Shared.php": "<?php // v1\n",
                                               "app__Legacy.php": "<?php // legacy code\n", "routes__api.php": "<?php Route::get(\"/a\", A::class);\n"})
        git(api, "tag", "v9.9.9")  # tags never drive the version
        git(api, "checkout", "-q", "-b", "release-1-4")
        commit(api, "fix: [API-2] release fix", **{"app__Rel.php": "<?php // rel\n"})
        git(api, "checkout", "-q", "main")
        git(api, "merge", "-q", "--no-ff", "release-1-4", "-m", "Merge branch 'release-1-4' into 'main'")
        git(api, "branch", "-D", "release-1-4")
        git(api, "checkout", "-q", "-b", "develop")
        commit(api, "feat(pay): [PAY-12] add payment middleware", **{
            "database__migrations__2026_01_01_add_col.php": "<?php Schema::table('u', fn () => 1);\n",
            "app__Http__Middleware__Auth.php": "<?php $k = env('PAYMENT_KEY');\n",
            ".env.example": "PAYMENT_KEY=\n", "tests__Feature__PayTest.php": "<?php\n"})
        git(api, "rm", "-q", "app/Legacy.php")
        git(api, "mv", "routes/api.php", "routes/api_v2.php")
        commit(api, "tidy routes")
        commit(api, "fix: [PAY-13] shared tweak", **{"app__Shared.php": "<?php // release\n"})
        git(api, "checkout", "-q", "main")
        commit(api, "fix: [OPS-9] hotfix on main", **{"app__Shared.php": "<?php // hotfix\n"})

        # web: React frontend; last release is a branch release-2.3; develop has only fixes -> patch
        web = hub / "repos/web"
        web.mkdir(parents=True)
        git(web, "init", "-q", "-b", "main")
        commit(web, "chore: [WEB-1] init", **{"package.json": json.dumps({"dependencies": {"react": "18"}})})
        git(web, "branch", "release-2.3")
        git(web, "branch", "release-2.10")  # numeric, not lexical, ordering
        git(web, "checkout", "-q", "-b", "develop")
        commit(web, "fix(ui): [WEB-7] button spacing", **{"src__Button.tsx": "export {}\n"})

        # mobile: Flutter, no release yet
        mobile = hub / "repos/mobile"
        mobile.mkdir(parents=True)
        git(mobile, "init", "-q", "-b", "main")
        commit(mobile, "chore: [APP-1] init", **{"pubspec.yaml": "name: app\n"})
        git(mobile, "checkout", "-q", "-b", "develop")
        commit(mobile, "feat!: [APP-2] new login", **{"lib__login.dart": "//\n"})

        # idle: develop has nothing main lacks
        idle = hub / "repos/idle"
        idle.mkdir(parents=True)
        git(idle, "init", "-q", "-b", "main")
        commit(idle, "chore: [IDL-1] init", **{"go.mod": "module idle\n"})
        git(idle, "branch", "develop")

        code, p = run(hub / "docs", "plan")  # found by walking up
        assert code == 0, p
        assert p["approvals_out"] == str(hub / "docs/approvals")
        assert "releases.integration_branch" in p["defaulted_keys"]
        rows = {r["repo"]: r for r in p["repos"]}
        assert rows["api"]["kind"] == "backend" and rows["web"]["kind"] == "frontend" and rows["mobile"]["kind"] == "mobile"
        assert rows["api"]["latest_release"] == {"name": "release-1-4", "version": "1.4", "source": "merge into main",
                                                 "seen": ["release-1-4"]}, rows["api"]
        assert rows["web"]["latest_release"]["name"] == "release-2.10", rows["web"]  # numeric, not lexical
        # one shared version: highest latest release (web 2.10) bumped by the strongest change (mobile feat!)
        rel = p["release"]
        assert rel["branch"] == "release.3.0.0" and rel["version"] == "3.0.0" and rel["source"] == "proposed", rel
        assert rel["bump"] == "major" and "mobile" in rel["bump_reason"] and rel["needs_decision"] is None, rel
        assert any("different release versions" in w for w in p["warnings"]), p["warnings"]
        for rid in ("api", "web", "mobile"):
            assert rows[rid]["branch"] == "release.3.0.0" and rows[rid]["status"] == "create", rows[rid]
            assert rows[rid]["review_ref"] == "develop"
        assert rows["idle"]["status"] == "nothing to release" and rows["idle"]["branch"] == "release.3.0.0"
        assert rows["missing"]["status"] == "not cloned"

        # without the breaking mobile commit the shared bump is minor (api's feat)
        code, p = run(hub, "plan", "--repo", "api", "--repo", "web")
        assert p["release"]["branch"] == "release.2.11.0" and p["release"]["bump"] == "minor", p["release"]

        # a named branch is used for every repo: reviewed where it exists, created where it does not
        git(api, "branch", "release/1.5.0", "develop")
        code, p = run(hub, "plan", "--branch", "release/1.5.0", "--repo", "api", "--repo", "web")
        rows = {r["repo"]: r for r in p["repos"]}
        assert p["release"]["source"] == "named"
        # not semantic, and web would need it created: ask, suggesting the semantic name
        assert p["release"]["suggested_branch"] == "release.1.5.0" and "web" in p["release"]["needs_decision"]
        assert rows["api"]["status"] == "exists" and rows["api"]["review_ref"] == "release/1.5.0"
        assert rows["web"]["status"] == "create" and rows["web"]["review_ref"] == "develop"

        # with no name, an open (unmerged) release branch in any repo becomes the shared name
        code, p = run(hub, "plan")
        rows = {r["repo"]: r for r in p["repos"]}
        assert p["release"]["branch"] == "release/1.5.0" and p["release"]["source"] == "open release", p["release"]
        assert rows["api"]["status"] == "exists" and rows["web"]["status"] == "create"
        assert p["release"]["suggested_branch"] == "release.1.5.0"

        # two different open releases need a person to choose
        git(web, "branch", "release-9.0", "develop")
        code, p = run(hub, "plan")
        assert p["release"]["branch"] == "release-9.0" and "different open release" in p["release"]["needs_decision"]
        git(web, "branch", "-D", "release-9.0")

        # a semantic name that already exists everywhere needs no decision
        git(api, "branch", "release.1.5.0", "develop")
        git(web, "branch", "release.1.5.0", "develop")
        code, p = run(hub, "plan", "--branch", "release.1.5.0", "--repo", "api", "--repo", "web")
        assert p["release"]["needs_decision"] is None and {r["status"] for r in p["repos"]} == {"exists"}, p
        git(api, "branch", "-D", "release.1.5.0")
        git(web, "branch", "-D", "release.1.5.0")

        # old dash-separated names are read as versions; the next branch is always release.X.Y.Z
        legacy = Path(tmp) / "legacy"
        legacy.mkdir()
        git(legacy, "init", "-q", "-b", "main")
        commit(legacy, "chore: [LEG-1] init", **{"go.mod": "module legacy\n"})
        git(legacy, "branch", "release-5-5")
        git(legacy, "branch", "release-5-4")
        git(legacy, "checkout", "-q", "-b", "develop")
        commit(legacy, "feat: [LEG-2] export", **{"export.go": "package main\n"})
        code, p = run(tmp, "--path", str(legacy), "plan")
        assert p["repos"][0]["latest_release"]["name"] == "release-5-5", p["repos"][0]
        assert p["release"]["branch"] == "release.5.6.0" and p["release"]["needs_decision"] is None, p["release"]

        # with a remote, origin is the truth: a release deleted on the server stops counting once
        # `fetch --prune` drops its ref, and a local leftover is ignored with a warning
        server = Path(tmp) / "server.git"
        subprocess.run(["git", "clone", "-q", "--bare", str(legacy), str(server)], check=True)
        clone = Path(tmp) / "clone"
        subprocess.run(["git", "clone", "-q", str(server), str(clone)], check=True)
        git(clone, "branch", "release-5-5", "origin/release-5-5")  # local copy of the release
        code, p = run(tmp, "--path", str(clone), "plan")
        assert p["release"]["branch"] == "release.5.6.0", p["release"]
        git(server, "branch", "-D", "release-5-5")  # deleted on the server
        git(clone, "fetch", "-q", "--prune", "origin")
        code, p = run(tmp, "--path", str(clone), "plan")
        assert p["repos"][0]["latest_release"]["name"] == "release-5-4", p["repos"][0]
        assert p["release"]["branch"] == "release.5.5.0", p["release"]
        assert any("release-5-5" in w and "not on origin" in w for w in p["warnings"]), p["warnings"]

        # the team's flow: release merged into main, tagged in another scheme, branch deleted —
        # the version comes from the merge commit left on main
        flow = Path(tmp) / "flow"
        flow.mkdir()
        git(flow, "init", "-q", "-b", "main")
        commit(flow, "chore: [FL-1] init", **{"go.mod": "module flow\n"})
        git(flow, "checkout", "-q", "-b", "develop")
        for n, name in enumerate(["release-5-3", "release-5-4"]):
            commit(flow, f"feat: [FL-{n + 2}] work for {name}", **{f"f{n}.go": "package main\n"})
            git(flow, "checkout", "-q", "-b", name)
            git(flow, "checkout", "-q", "main")
            git(flow, "merge", "-q", "--no-ff", name, "-m", f"Merge branch '{name}' into 'main'")
            git(flow, "tag", f"v-1.0.{n + 1}")  # a tag scheme unrelated to the release names
            git(flow, "branch", "-D", name)
            git(flow, "checkout", "-q", "develop")
        git(flow, "checkout", "-q", "-b", "release-4-0")  # old and never merged: abandoned, not open
        commit(flow, "fix: [FL-8] abandoned", **{"old.go": "package main\n"})
        git(flow, "checkout", "-q", "develop")
        commit(flow, "feat: [FL-9] next thing", **{"next.go": "package main\n"})
        # an older hotfix merged after 5-4: the highest version still wins, not the newest merge
        git(flow, "checkout", "-q", "-b", "release-4-5-hotfix", "main")
        commit(flow, "fix: [FL-7] hotfix", **{"hot.go": "package main\n"})
        git(flow, "checkout", "-q", "main")
        git(flow, "merge", "-q", "--no-ff", "release-4-5-hotfix", "-m", "Merge branch 'release-4-5-hotfix' into 'main'")
        git(flow, "branch", "-D", "release-4-5-hotfix")
        git(flow, "checkout", "-q", "develop")
        code, p = run(tmp, "--path", str(flow), "plan")
        row = p["repos"][0]
        assert row["latest_release"]["name"] == "release-5-4" and row["latest_release"]["source"] == "merge into main", row
        assert row["latest_release"]["seen"] == ["release-5-4", "release-5-3", "release-4-5-hotfix"], row
        assert "open_release" not in row, row
        assert p["release"]["branch"] == "release.5.5.0" and p["release"]["source"] == "proposed", p["release"]
        assert row["status"] == "create" and row["review_ref"] == "develop", row

        code, err = run(hub, "facts", "--head", "develop")
        assert code == 2 and "--repo" in err, err

        code, f = run(hub, "facts", "--repo", "api", "--head", "release/1.5.0")
        assert code == 0, f
        assert f["kind"] == "backend" and f["base"]["ref"] == "main"
        assert f["totals"]["commits"] == 3 and f["bump"] == "minor", f["totals"]
        assert f["commit_types"] == {"(unparsed)": 1, "feat": 1, "fix": 1}, f["commit_types"]
        assert [c["subject"] for c in f["malformed_commits"]] == ["tidy routes"]
        assert f["tickets"] == {"PAY-12": 1, "PAY-13": 1}
        feat = next(c for c in f["commits"] if c["type"] == "feat")
        assert feat["scope"] == "pay" and feat["ticket"] == "PAY-12" and feat["format_ok"]
        cat = f["by_category"]
        assert "database/migrations/2026_01_01_add_col.php" in cat["migrations"]
        assert ".env.example" in cat["env"] and "app/Http/Middleware/Auth.php" in cat["security_sensitive"]
        assert "tests/Feature/PayTest.php" in cat["tests"] and "routes/api_v2.php" in cat["api"]
        assert f["deleted_files"] == ["app/Legacy.php"]
        assert f["renamed_files"] == [{"from": "routes/api.php", "to": "routes/api_v2.php"}]
        assert [e["name"] for e in f["new_env_vars"]] == ["PAYMENT_KEY"]
        assert [c["subject"] for c in f["base_commits_missing_from_release"]] == ["fix: [OPS-9] hotfix on main"]
        assert f["merge"] == {"status": "conflicts", "conflicts": ["app/Shared.php"]}, f["merge"]
        assert f["range"] == f"{f['merge_base']}..{f['head']['sha']}"
        assert any("not on origin" in w for w in f["warnings"])

        # outside a hub: --path
        code, f = run(tmp, "--path", str(web), "facts", "--head", "develop")
        assert code == 0 and f["kind"] == "frontend" and f["merge"]["status"] == "clean", f
        code, err = run(tmp, "plan")
        assert code == 1 and "no Product Brain hub" in err, err

        assert not list(SCRIPT.parent.glob("__pycache__")), "script left bytecode behind"
    print("ok")


if __name__ == "__main__":
    main()
