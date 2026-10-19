"""Self-check for plugins/task-workflow/scripts/task-facts.py.

Run: python3 tests/test_task_facts.py

Builds a throwaway hub with a bare origin, then walks one task from two drafts to a ticketed
folder: config defaults, draft listing, resolving, links, the move, and the server check.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "plugins/task-workflow/scripts/task-facts.py"


def git(cwd, *args):
    subprocess.run(["git", "-C", str(cwd), "-c", "user.email=t@t", "-c", "user.name=t", *args],
                   check=True, capture_output=True)


def run(hub, *args):
    p = subprocess.run([sys.executable, str(SCRIPT), "--hub", str(hub), *args],
                       capture_output=True, text=True, encoding="utf-8")
    return p.returncode, p.stdout, p.stderr


def facts(hub, *args):
    code, out, err = run(hub, *args)
    assert code == 0, (args, code, out, err)
    return json.loads(out)


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


CONFIG = {
    "tasks": {
        "dir": "tasks", "key_regex": "^CH-\\d+$", "branch": "ai-ch-{n}",
        "tracker": {"kind": "jira", "url": "https://jira.example.com/", "project": "CH"},
        "areas": {"api": "BE", "web": "FE"}, "locales": ["fa", "en"],
    },
    "releases": {"integration_branch": "develop"},
}
DESCRIPTION = """# CH-NNN: description

| Field | Value |
|---|---|
| Jira | [CH-NNN](https://jira.example.com/browse/CH-NNN) |
| Status | Ready for plan |

Branch `ai-ch-NNN` from develop.
"""


def main():
    with tempfile.TemporaryDirectory() as tmp:
        origin, hub = Path(tmp) / "origin.git", Path(tmp) / "hub"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
        subprocess.run(["git", "init", "-q", "-b", "main", str(hub)], check=True)
        git(hub, "remote", "add", "origin", str(origin))
        write(hub / "brain.config.json", json.dumps(CONFIG))
        write(hub / "constitution.md", "# Constitution\n")
        write(hub / "templates/task-report.md", "# report\n")
        git(hub, "add", "-A")
        git(hub, "commit", "-qm", "init")
        git(hub, "push", "-q", "origin", "main")
        # links are built from the remote the way a GitLab ssh URL spells it; pushes still reach
        # the bare repo, and sync() stands in for the fetch that `verify` does without --no-fetch
        git(hub, "remote", "set-url", "origin", "ssh://git@gitlab.example.com:2222/team/acme-brain.git")
        git(hub, "remote", "set-url", "--push", "origin", str(origin))

        def sync():
            git(hub, "fetch", "-q", str(origin), "+main:refs/remotes/origin/main")
        sync()

        s = facts(hub, "config")
        assert s["placeholder"] == "CH-NNN" and s["placeholder_branch"] == "ai-ch-NNN", s
        assert s["drafts"] == "drafts" and s["base_branch"] == "develop", s
        assert s["tracker"]["url"] == "https://jira.example.com", "trailing slash trimmed"
        assert s["source"]["blob"] == "https://gitlab.example.com/team/acme-brain/-/blob/main/", s["source"]
        assert s["templates"]["task-report"]["from"] == "hub", s["templates"]
        assert s["templates"]["task-plan"]["from"] == "plugin", s["templates"]
        assert (Path(s["templates"]["task-plan"]["path"])).is_file(), "the plugin ships every template"

        # no drafts yet: a person has to start one
        code, _, err = run(hub, "resolve")
        assert code == 2 and "no drafts" in err, err

        for slug in ("sms-limit", "otp-retry"):
            write(hub / "tasks/drafts" / slug / "description.md", DESCRIPTION)
        write(hub / "tasks/drafts/sms-limit/plan.md", "Plan for CH-NNN on `ai-ch-NNN`.\n")
        write(hub / "tasks/drafts/sms-limit/mockups/U1-x.html", "<p>CH-NNN</p>")
        write(hub / "tasks/draft/description.md", "# Legacy draft\n")
        write(hub / "tasks/draft2/description.md", "# A second draft made before drafts/ existed\n")
        write(hub / "tasks/CH-7/description.md", "# a ticketed task, never a draft\n")

        drafts = facts(hub, "drafts")
        assert [d["slug"] for d in drafts] == ["otp-retry", "sms-limit", "draft", "draft2"], drafts
        assert drafts[1]["has_plan"] and drafts[1]["status"] == "Ready for plan", drafts[1]
        assert drafts[2]["path"] == "tasks/draft", "the older single draft folder still counts"
        assert drafts[3]["path"] == "tasks/draft2" and drafts[3]["legacy"], "any non-key folder in tasks/ is a draft"
        assert not drafts[0]["legacy"], drafts[0]

        code, _, err = run(hub, "resolve")
        assert code == 2 and "several drafts" in err and "otp-retry" in err and "sms-limit" in err, err
        assert facts(hub, "resolve", "sms-limit")["path"] == "tasks/drafts/sms-limit"
        assert facts(hub, "resolve", "tasks/drafts/otp-retry/")["slug"] == "otp-retry"
        assert facts(hub, "resolve", "draft")["path"] == "tasks/draft"
        assert facts(hub, "resolve", "draft2")["path"] == "tasks/draft2"
        assert facts(hub, "resolve", "tasks/draft2/")["slug"] == "draft2"
        (hub / "tasks/CH-7/description.md").unlink()
        (hub / "tasks/CH-7").rmdir()
        assert facts(hub, "resolve", "CH-12") == {"kind": "task", "key": "CH-12", "path": "tasks/CH-12",
                                                    "exists": False}
        code, _, err = run(hub, "resolve", "Fix The Thing")
        assert code == 2 and "kebab-case" in err, err

        lk = facts(hub, "links", "CH-1201")
        assert lk["ticket"] == "https://jira.example.com/browse/CH-1201", lk
        assert lk["branch"] == "ai-ch-1201", lk
        assert lk["files"]["plan.md"] == "https://gitlab.example.com/team/acme-brain/-/blob/main/tasks/CH-1201/plan.md"
        assert lk["mockups"] == "https://gitlab.example.com/team/acme-brain/-/tree/main/tasks/CH-1201/mockups"
        assert lk["report_template"].endswith("/-/blob/main/templates/task-report.md"), lk

        write(hub / "tasks/CH-1201/description.md", "taken\n")
        code, _, err = run(hub, "finalize", "sms-limit", "CH-1201")
        assert code == 2 and "already exists" in err, err
        assert (hub / "tasks/drafts/sms-limit/plan.md").is_file(), "a refused move touches nothing"
        (hub / "tasks/CH-1201/description.md").unlink()
        (hub / "tasks/CH-1201").rmdir()

        done = facts(hub, "finalize", "sms-limit", "CH-1201")
        assert done["to"] == "tasks/CH-1201" and len(done["changed"]) == 3, done
        assert not (hub / "tasks/drafts/sms-limit").exists()
        assert (hub / "tasks/drafts/otp-retry").is_dir(), "the other drafts stay where they are"
        desc = (hub / "tasks/CH-1201/description.md").read_text(encoding="utf-8")
        assert "[CH-1201](https://jira.example.com/browse/CH-1201)" in desc and "`ai-ch-1201`" in desc, desc
        assert "NNN" not in (hub / "tasks/CH-1201/plan.md").read_text(encoding="utf-8")

        code, out, _ = run(hub, "verify", "CH-1201", "--no-fetch")
        assert code == 2 and "MISSING on main: tasks/CH-1201/plan.md" in out and "Not ready" in out, out
        assert "OK constitution.md" in out, out
        git(hub, "add", "tasks/CH-1201")
        git(hub, "commit", "-qm", "task")
        git(hub, "push", "-q", "origin", "main")
        sync()
        write(hub / "tasks/CH-1201/report.md", "not pushed yet\n")
        code, out, _ = run(hub, "verify", "CH-1201", "--no-fetch")
        assert code == 0 and "Ready to run" in out and "report.md" not in out, out
        write(hub / "tasks/CH-1201/plan.md", "changed locally\n")
        code, out, _ = run(hub, "verify", "CH-1201", "--no-fetch")
        assert code == 2 and "DIFFERS from main: tasks/CH-1201/plan.md" in out, out
        assert "push tasks/CH-1201/plan.md to main" in out, out
        git(hub, "checkout", "--", "tasks/CH-1201/plan.md")
        write(hub / "constitution.md", "# Constitution, edited locally\n")
        code, out, _ = run(hub, "verify", "CH-1201", "--no-fetch")
        assert code == 2 and "push constitution.md to main" in out and "push tasks/CH-1201" not in out, out

        # config errors name the key and give an example
        write(hub / "brain.config.json", json.dumps({"tasks": {"dir": "tasks"}}))
        code, _, err = run(hub, "config")
        assert code == 1 and '"key_regex"' in err, err
        write(hub / "brain.config.json", json.dumps({"tasks": {**CONFIG["tasks"], "tracker": {"kind": "trello",
                                                                                            "url": "x"}}}))
        code, _, err = run(hub, "config")
        assert code == 1 and "tasks.tracker" in err, err
        # portal.tasks, the older place, still works; GitHub issue links use the number
        write(hub / "brain.config.json", json.dumps({"portal": {"tasks": {"dir": "tasks", "key_regex": "^GH-\\d+$"}},
                                                     "tasks": None}))
        cfg = facts(hub, "config")
        assert cfg["placeholder"] == "KEY-NNN" and cfg["tracker"] is None and cfg["warnings"], cfg
        write(hub / "brain.config.json", json.dumps({"tasks": {"dir": "tasks", "key_regex": "^GH-\\d+$",
                                                               "tracker": {"kind": "github",
                                                                           "url": "https://github.com/acme/app"}}}))
        assert facts(hub, "links", "GH-7")["ticket"] == "https://github.com/acme/app/issues/7"

    print("task-facts selftest: ok")


if __name__ == "__main__":
    main()
