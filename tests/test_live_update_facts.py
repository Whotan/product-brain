"""Self-check for plugins/live-update/skills/live-update/scripts/gather-live-update-facts.py.

Run: python3 tests/test_live_update_facts.py
"""

import json
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "plugins/live-update/skills/live-update/scripts/gather-live-update-facts.py"


def git(cwd, *args):
    subprocess.run(["git", "-C", str(cwd), "-c", "user.email=t@t", "-c", "user.name=t", *args],
                   check=True, capture_output=True)


def commit(repo, msg, name):
    (repo / name).write_text(msg + "\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", msg)


def write(path, text="x\n"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def run(hub, *args, path=None):
    env = dict(os.environ)
    if path:
        env["PATH"] = path + os.pathsep + env["PATH"]
    proc = subprocess.run([sys.executable, str(SCRIPT), "--hub", str(hub), "--no-fetch", *args],
                          capture_output=True, text=True, env=env)
    return proc.returncode, (json.loads(proc.stdout) if proc.returncode == 0 else proc.stderr)


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
        api = hub / "repos/api"
        api.mkdir(parents=True)
        git(api, "init", "-q", "-b", "main")
        git(api, "remote", "add", "origin", str(origin))
        commit(api, "chore: init", "a.txt")
        git(api, "push", "-q", "origin", "main")
        git(api, "checkout", "-q", "-b", "develop")
        git(api, "push", "-q", "origin", "develop")
        git(api, "checkout", "-q", "-b", "release.1.5.0")
        commit(api, "feat: thing", "b.txt")
        git(api, "push", "-q", "origin", "release.1.5.0")

        config = {
            "hub_name": "Acme",
            "repos": [{"id": "api"}],
            "releases": {"primary_repo": "api", "production_branch": "main", "out": "docs/releases",
                         "tag_regex": r"^v\d+\.\d+\.\d+$"},
            "approvals": {"out": "docs/approvals"},
            "jira": {"project": "PROD", "component": "Acme"},
        }
        (hub / "brain.config.json").write_text(json.dumps(config))

        # 1. nothing produced yet
        rc, f = run(hub, "--no-vcs-host")
        check(rc == 0, f"nothing exists: exit {rc} {f}")
        check(f["release"]["branch"] == "release.1.5.0" and f["release"]["source"] == "branch", "latest branch found")
        check(f["release"]["branch_state"] == "open" and f["release"]["version_label"] == "1.5.0", "open, label 1.5.0")
        check(not f["epic_approval"]["exists"] and not f["release_notes"]["exists"], "nothing exists")
        check(f["attachments"] == [], "no attachments yet")
        check(f["merge_request"]["found_via"] == "skipped (--no-vcs-host)", "no gh call")
        check(f["jira"]["marker"] == "[release:1.5.0]"
              and f["jira"]["suggested_label"] == "live-update-release-1.5.0"
              and f["jira"]["suggested_summary"] == "[release:1.5.0] Production deployment - Acme 1.5.0",
              "jira dedupe marker, label and summary")
        check(f["jira"]["project"] == "PROD" and f["jira"]["component"] == "Acme", "jira project/component from config")
        check(any("epic-approval" in w for w in f["warnings"]) and any("release-notes" in w for w in f["warnings"]),
              "missing artifacts warned about")

        # 2. epic-approval only: several dated runs, newest wins; another release's folder ignored
        ea = hub / "docs/approvals"
        write(ea / "2026-09-10 - release.1.5.0/api.md")
        write(ea / "2026-09-20 - release.1.5.0/api.md")
        write(ea / "2026-09-20 - release.1.5.0/README.md")
        write(ea / "2026-09-25 - release.1.4.0/api.md")
        write(hub / ".work/epic-approval/2026-09-20 - release.1.5.0/approval.html")
        rc, f = run(hub, "--no-vcs-host")
        e = f["epic_approval"]
        check(e["exists"] and e["report_date"] == "2026-09-20", f"newest epic-approval run: {e}")
        check([r["repo"] for r in e["reports"]] == ["api"] and e["summary_path"].endswith("README.md"), "reports and summary")
        check(sorted(a["kind"] for a in f["attachments"])
              == ["epic_approval_page", "epic_approval_report", "epic_approval_summary"],
              "epic-approval files are attachments, page included until it is published")
        check(e["page_path"].endswith("approval.html"), "page path reported")
        rc, f2 = run(hub, "--no-vcs-host", "--approval-url", "https://claude.ai/artifacts/appr")
        check("epic_approval_page" not in [a["kind"] for a in f2["attachments"]]
              and f2["links"]["epic_approval_page_url"] == "https://claude.ai/artifacts/appr"
              and f2["epic_approval"]["page_url_source"] == "cli-arg", "published approval page is linked, not attached")
        check(all(Path(a["path"]).is_absolute() for a in f["attachments"]), "attachment paths are absolute")
        check(not f["release_notes"]["exists"], "release notes still missing")

        # 3. release-notes: local files are attachments, client.html only without a published URL
        rn = hub / "docs/releases/1.5.0 - 2026-09-28"
        write(rn / "facts.json", json.dumps({"label": "1.5.0", "unreleased": False}))
        for name in ("internal.md", "client.pdf", "client.html"):
            write(rn / name)
        write(hub / "docs/releases/1.4.0 - 2026-08-01/facts.json", "{}")
        rc, f = run(hub, "--no-vcs-host")
        kinds = sorted(a["kind"] for a in f["attachments"])
        check(f["release_notes"]["exists"] and f["release_notes"]["folder"] == "docs/releases/1.5.0 - 2026-09-28",
              "release-notes folder for this release only")
        check("client_html" in kinds and "internal_note" in kinds and "client_pdf" in kinds and "facts_json" in kinds,
              f"release-notes attachments: {kinds}")
        rc, f = run(hub, "--no-vcs-host", "--client-note-url", "https://claude.ai/artifacts/abc")
        check("client_html" not in [a["kind"] for a in f["attachments"]], "client.html not attached when published")
        check(f["links"]["client_note_artifact_url"] == "https://claude.ai/artifacts/abc"
              and f["release_notes"]["client_note_artifact_url_source"] == "cli-arg", "client note link from the argument")
        write(rn / "facts.json", json.dumps({"label": "1.5.0", "clientNoteArtifactUrl": "https://claude.ai/artifacts/xyz"}))
        rc, f = run(hub, "--no-vcs-host")
        check(f["links"]["client_note_artifact_url"] == "https://claude.ai/artifacts/xyz"
              and f["release_notes"]["client_note_artifact_url_source"] == "facts.json", "client note link from facts.json")

        # 4. merge request lookup through a fake gh / glab on PATH
        shims = tmp / "shims"
        shims.mkdir()
        shim(shims, "gh", 'echo \'{"url":"https://github.com/o/r/pull/7","state":"OPEN"}\'')
        rc, f = run(hub, path=str(shims))
        m = f["merge_request"]
        check(m["host"] == "github" and m["url"] == "https://github.com/o/r/pull/7" and m["state"] == "open"
              and m["found_via"] == "gh view", f"gh lookup: {m}")
        check(f["links"]["merge_request_url"] == m["url"], "mr link in links")
        shim(shims, "glab", 'echo \'{"web_url":"https://gitlab.example/o/r/-/merge_requests/3","state":"opened"}\'')
        rc, f = run(hub, "--host", "gitlab", path=str(shims))
        check(f["merge_request"]["url"].endswith("/merge_requests/3") and f["merge_request"]["state"] == "open",
              "glab lookup")
        shim(shims, "gh", "exit 1")
        rc, f = run(hub, path=str(shims))
        check(f["merge_request"]["url"] is None and f["merge_request"]["found_via"] == "not found", "no mr found")
        check(any("no merge/pull request" in w for w in f["warnings"]), "missing mr warned about")

        # 5. release branch merged and deleted -> latest tag; artifacts found by version
        git(api, "push", "-q", "origin", "--delete", "release.1.5.0")
        git(api, "tag", "v1.5.0", "main")
        rc, f = run(hub, "--no-vcs-host")
        check(f["release"]["source"] == "tag" and f["release"]["branch"] is None
              and f["release"]["version_label"] == "1.5.0", f"tag fallback: {f['release']}")
        check(f["epic_approval"]["exists"] and f["release_notes"]["exists"], "artifacts found by version")
        rc, f = run(hub)
        check(f["merge_request"]["found_via"] == "no release branch to look up", "no mr lookup without a branch")

        # 6. jira keys missing -> null plus warnings, never a guess
        del config["jira"]
        (hub / "brain.config.json").write_text(json.dumps(config))
        rc, f = run(hub, "--no-vcs-host")
        check(f["jira"]["project"] is None and f["jira"]["component"] is None
              and f["jira"]["missing_keys"] == ["jira.project", "jira.component"], "missing jira keys reported")

        # 7. per-repo component override
        config["jira"] = {"project": "PROD", "component": "Default", "components": {"api": "Bugloos"}}
        (hub / "brain.config.json").write_text(json.dumps(config))
        rc, f = run(hub, "--no-vcs-host")
        check(f["jira"]["component"] == "Bugloos", "per-repo component override")

        # 8. nothing identifies a release -> a person must decide
        bare = tmp / "hub2"
        (bare / "repos/api").mkdir(parents=True)
        git(bare / "repos/api", "init", "-q", "-b", "main")
        commit(bare / "repos/api", "chore: init", "a.txt")
        (bare / "brain.config.json").write_text(json.dumps({"repos": [{"id": "api"}]}))
        rc, err = run(bare, "--no-vcs-host")
        check(rc == 2 and "--branch" in err, f"undecidable release: exit {rc} {err}")
        rc, f = run(bare, "--no-vcs-host", "--version", "2.0.0")
        check(rc == 0 and f["release"]["source"] == "cli-version" and f["release"]["version_label"] == "2.0.0",
              "--version accepted")

    print("ok")


if __name__ == "__main__":
    main()
