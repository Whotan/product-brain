"""Self-check for pb's honest-report checks (pb report check, pb check) and pb owners.

Run: python3 tests/test_pb_reports_owners.py
"""

import json
import os
import runpy
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PB = runpy.run_path(str(ROOT / "bin/pb"), run_name="pb_under_test")

COMPLETE_REPORT = """# CH-1: report

| Field | Value |
|---|---|
| Status | Complete |

## 1. What was done
## 2. Not done and needs attention
## 3. How to check it by hand
Level 1 — quick. Level 2 — standard. Level 3 — deep.
## 6. Test changes and runs
"""


def make_hub(tmp, reports):
    """A git hub with a tasks folder and the given {relative path: text} reports."""
    hub = Path(tmp)
    subprocess.run(["git", "init", "-q", str(hub)], check=True)
    cfg = {"doc_types": ["knowledge"], "tasks": {"dir": "tasks"}}
    (hub / "brain.config.json").write_text(json.dumps(cfg), encoding="utf-8")
    (hub / "docs/knowledge").mkdir(parents=True)
    (hub / "docs/knowledge/.gitkeep").write_text("")
    for rel, text in reports.items():
        (hub / rel).parent.mkdir(parents=True, exist_ok=True)
        (hub / rel).write_text(text, encoding="utf-8")
    return hub, cfg


def test_report_missing_not_done_is_flagged():
    text = COMPLETE_REPORT.replace("## 2. Not done and needs attention", "## 2. What needs attention")
    with tempfile.TemporaryDirectory() as tmp:
        hub, cfg = make_hub(tmp, {"tasks/CH-1/report.md": text})
        problems = PB["report_problems"](hub, cfg, ["tasks/CH-1/report.md"])
    assert len(problems) == 1 and "Not done" in problems[0], problems


def test_report_missing_a_level_is_flagged():
    text = COMPLETE_REPORT.replace("Level 3 — deep.", "")
    assert PB["report_missing"](text) == ["Level 3"]


def test_complete_report_passes():
    assert PB["report_missing"](COMPLETE_REPORT) == []


def test_archived_drafted_and_absorbed_reports_are_skipped():
    bad = "# CH-2: report\n\n| Status | Ready |\n"
    absorbed = "# CH-3: report\n\n| Status | Absorbed into specs/037-case-calendar |\n"
    reports = {"tasks/archive/CH-2/report.md": bad, "tasks/drafts/new-thing/report.md": bad,
               "tasks/CH-3/report.md": absorbed, "tasks/CH-4/notes.md": bad}
    with tempfile.TemporaryDirectory() as tmp:
        hub, cfg = make_hub(tmp, reports)
        assert PB["report_problems"](hub, cfg, list(reports)) == []


def test_pb_report_check_cli():
    with tempfile.TemporaryDirectory() as tmp:
        good, bad = Path(tmp) / "good.md", Path(tmp) / "bad.md"
        good.write_text(COMPLETE_REPORT, encoding="utf-8")
        bad.write_text("# x\n", encoding="utf-8")
        run = lambda f: subprocess.run([sys.executable, str(ROOT / "bin/pb"), "report", "check", str(f)],
                                       capture_output=True, text=True)
        assert run(good).returncode == 0
        out = run(bad)
        assert out.returncode == 1 and "Not done" in out.stdout, out.stdout


def test_check_hook_flags_changed_report():
    text = COMPLETE_REPORT.replace("## 6. Test changes and runs", "## 6. E2E tests")
    with tempfile.TemporaryDirectory() as tmp:
        hub, _ = make_hub(tmp, {"tasks/CH-5/report.md": text})
        event = json.dumps({"cwd": str(hub), "stop_hook_active": False})
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
        out = subprocess.run([sys.executable, str(ROOT / "bin/pb"), "check", "--hook"], input=event,
                             capture_output=True, text=True, cwd=hub, env=env)
    assert out.returncode == 2, (out.returncode, out.stderr)
    assert "Test changes" in out.stderr


def test_generic_report_template_passes():
    text = (ROOT / "plugins/task-workflow/templates/task-report.md").read_text(encoding="utf-8")
    assert PB["report_missing"](text) == [], PB["report_missing"](text)


def owners_cfg(**overrides):
    owners = {
        "file": "docs/knowledge/decision-owners.md",
        "people": {"Saeed": {"gitlab": "Saeed.y"}, "Ashkan": {"gitlab": "Ashkan"},
                   "Hootan": {"gitlab": "Hootan"}, "Arash": {}},
        "domains": [
            {"id": "backend-data-model", "name": "Back-end data model", "owner": "Saeed",
             "backup": "Ashkan", "repo": "api", "paths": ["/database/migrations/", "/app/Models/"]},
            {"id": "api-contracts", "name": "API contracts", "owner": ["Saeed", "Ashkan"],
             "repo": "api", "paths": ["/routes/api.php"]},
            {"id": "product", "name": "Product scope", "owner": "Hootan"},
        ],
    }
    owners.update(overrides)
    return {"owners": owners}


def owners_problems(cfg, with_file=True):
    with tempfile.TemporaryDirectory() as tmp:
        hub = Path(tmp)
        if with_file:
            (hub / "docs/knowledge").mkdir(parents=True)
            (hub / "docs/knowledge/decision-owners.md").write_text("# Decision owners\n")
        return PB["owners_problems"](hub, cfg)


def test_owners_problems_clean():
    assert owners_problems(owners_cfg()) == []


def test_owners_problems_missing_file():
    [p] = owners_problems(owners_cfg(), with_file=False)
    assert "decision-owners.md" in p


def test_owners_problems_unknown_person():
    cfg = owners_cfg()
    cfg["owners"]["domains"][0]["backup"] = "Nobody"
    [p] = owners_problems(cfg)
    assert "backend-data-model" in p and "Nobody" in p


def test_owners_problems_paths_without_repo():
    cfg = owners_cfg()
    del cfg["owners"]["domains"][0]["repo"]
    [p] = owners_problems(cfg)
    assert "backend-data-model" in p and "repo" in p


def test_owners_problems_path_owner_without_gitlab():
    cfg = owners_cfg()
    cfg["owners"]["domains"][1]["owner"] = ["Saeed", "Arash"]
    [p] = owners_problems(cfg)
    assert "Arash" in p and "gitlab" in p


def test_owners_problems_duplicate_id():
    cfg = owners_cfg()
    cfg["owners"]["domains"].append(dict(cfg["owners"]["domains"][2]))
    [p] = owners_problems(cfg)
    assert "product" in p and "more than once" in p


def test_codeowners_sections():
    assert PB["codeowners"](owners_cfg(), "api") == (
        "# Generated by `pb owners codeowners api` from the hub's brain.config.json (owners).\n"
        "# Edit the hub, not this file.\n"
        "\n"
        "[Back-end data model] @Saeed.y @Ashkan\n"
        "/database/migrations/\n"
        "/app/Models/\n"
        "\n"
        "[API contracts] @Saeed.y @Ashkan\n"
        "/routes/api.php\n"
    )


def test_codeowners_unknown_repo_is_an_error():
    assert PB["codeowners"](owners_cfg(), "web") == ""
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "brain.config.json").write_text(json.dumps(owners_cfg()), encoding="utf-8")
        out = subprocess.run([sys.executable, str(ROOT / "bin/pb"), "--hub", tmp, "owners",
                              "codeowners", "web"], capture_output=True, text=True)
    assert out.returncode == 1 and "web" in out.stderr, (out.returncode, out.stderr)


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
    print(f"ok ({len(tests)} tests)")


if __name__ == "__main__":
    main()
