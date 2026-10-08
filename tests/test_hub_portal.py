"""Self-check for skills/hub-portal: a clean hub builds, and every guard fires when it should.

Run: python3 tests/test_hub_portal.py

Builds a throwaway hub from examples/todo-app, then breaks it one way at a time. Each
broken case must fail the build with its own message; each privacy fix must clear it.
A case that stops failing means a guard broke, not that the hub got better.
"""

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skills/hub-portal/scripts"
EXAMPLE = ROOT / "examples/todo-app"
# Assembled at runtime so this file never contains a token-shaped string itself.
FAKE_TOKEN = "gh" + "p_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5"


def git(cwd, *args):
    subprocess.run(["git", "-C", str(cwd), "-c", "user.email=t@t", "-c", "user.name=t", *args],
                   check=True, capture_output=True)


def run(script, hub, *args):
    p = subprocess.run([sys.executable, str(SCRIPTS / script), "--hub", str(hub), *args],
                       capture_output=True, text=True, encoding="utf-8")
    return p.returncode, p.stdout + p.stderr


def copy_example(tmp, name):
    hub = Path(tmp) / name
    shutil.copytree(EXAMPLE, hub)
    git(hub, "init", "-q")
    git(hub, "add", "-A")
    git(hub, "commit", "-qm", "init")
    return hub


def make_hub(tmp):
    """The example hub with a fresh data file from init-data, its TODOs filled in."""
    hub = copy_example(tmp, "hub")
    cfg = json.loads((hub / "brain.config.json").read_text(encoding="utf-8"))
    cfg["portal"] = {"data": "docs/dashboard/test-portal.json", "calendar": "jalali"}
    (hub / "brain.config.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    code, out = run("init-data.py", hub)
    assert code == 0, out
    code, out = run("init-data.py", hub)
    assert code != 0 and "already exists" in out, "init-data must never overwrite a data file"
    path = hub / "docs/dashboard/test-portal.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "TODO" in json.dumps(data), "init-data should leave TODO markers for a person to fill"

    def fill(v):
        if isinstance(v, dict):
            return {k: fill(x) for k, x in v.items()}
        if isinstance(v, list):
            return [fill(x) for x in v]
        return v.replace("TODO: ", "").replace("TODO", "x") if isinstance(v, str) else v
    data = fill(data)
    data["asOf"] = "2026-10-07"
    data["flows"] = [{"title": "Decide", "desc": "d", "steps": ["s"], "docs": ["docs/decisions/ADR-001-soft-delete.md"]}]
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return hub, path


def edit(path, fn):
    data = json.loads(path.read_text(encoding="utf-8"))
    fn(data)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def expect(name, ok, out=""):
    print("%s %s" % ("PASS" if ok else "FAIL", name))
    if not ok:
        print("    " + out.strip().replace("\n", "\n    ")[:1500])
    return ok


def main():
    results = []
    with tempfile.TemporaryDirectory() as tmp:
        shipped = copy_example(tmp, "shipped")
        code, out = run("build.py", shipped, "--no-fetch")
        results.append(expect("the example hub builds as shipped", code == 0 and "Built" in out, out))

        hub, data = make_hub(tmp)
        original = data.read_text(encoding="utf-8")

        code, out = run("build.py", hub, "--no-fetch")
        built = hub / ".work/hub-portal/index.html"
        page = built.read_text(encoding="utf-8") if built.exists() else ""
        results.append(expect("clean hub builds and passes check-brand", code == 0 and "Built" in out, out))
        results.append(expect("bundles written", (hub / ".work/hub-portal/md/specs.json").exists(), out))
        results.append(expect("constitution '### 1 —' principles derived", page.count('"caveat"') == 5, out))
        results.append(expect("jalali as-of date derived", "۱۵ مهر ۱۴۰۵" in page, out))
        results.append(expect("publish call printed with icon on first publish", '"icon": "library"' in out, out))

        doc = hub / "docs/knowledge/overview.md"
        clean_doc = doc.read_text(encoding="utf-8")
        cases = [
            ("international phone number fails", lambda: doc.write_text(clean_doc + "\nCall +44 20 7946 0958.\n", encoding="utf-8"), "phone number in docs/knowledge/overview.md"),
            ("token-shaped secret fails", lambda: doc.write_text(clean_doc + "\nkey " + FAKE_TOKEN + "\n", encoding="utf-8"), "secret in docs/knowledge/overview.md"),
            ("hub-specific pattern fails", lambda: (doc.write_text(clean_doc + "\nmobile 09121234567\n", encoding="utf-8"),
                edit(data, lambda d: d["privacy"].__setitem__("patterns", [{"name": "local mobile", "pattern": r"(?<!\d)09\d{9}(?!\d)"}]))), "local mobile in docs/knowledge/overview.md"),
            ("stale spec key fails", lambda: edit(data, lambda d: d["specs"].__setitem__("999-ghost", {"name": "g", "status": "spec", "note": "n"})), "999-ghost"),
            ("unknown spec status fails", lambda: edit(data, lambda d: d["specs"]["001-create-task"].__setitem__("status", "shipped")), "has status 'shipped'"),
            ("broken doc reference fails", lambda: edit(data, lambda d: d["flows"][0]["docs"].append("docs/nope.md")), "docs/nope.md"),
            ("leftover TODO fails", lambda: edit(data, lambda d: d["status"].__setitem__("headline", "TODO later")), "TODO placeholder at data.status.headline"),
            ("unknown artifact group fails", lambda: edit(data, lambda d: d["artifacts"].append({"group": "Nope", "title": "t", "id": "x", "desc": "d"})), "group 'Nope'"),
        ]
        for name, breakit, needle in cases:
            data.write_text(original, encoding="utf-8")
            doc.write_text(clean_doc, encoding="utf-8")
            breakit()
            code, out = run("build.py", hub, "--no-fetch", "--no-brand")
            results.append(expect(name, code == 1 and needle in out, out))

        fixes = [
            ("withhold clears a privacy hit", lambda d: d["privacy"]["withhold"].__setitem__("docs/knowledge/overview.md", "names a customer")),
            ("redact clears a privacy hit", lambda d: d["privacy"]["redact"].append({"pattern": r"\+44 20 7946 0958", "with": "+44 •••"})),
            ("allow clears a documented example", lambda d: d["privacy"]["allow"].append("+44 20 7946 0958")),
        ]
        for name, fix in fixes:
            data.write_text(original, encoding="utf-8")
            doc.write_text(clean_doc + "\nCall +44 20 7946 0958.\n", encoding="utf-8")
            edit(data, fix)
            code, out = run("build.py", hub, "--no-fetch", "--no-brand")
            results.append(expect(name, code == 0, out))

        data.write_text(original, encoding="utf-8")
        doc.write_text(clean_doc, encoding="utf-8")
        (hub / "docs/specs/002-due-dates").mkdir()
        (hub / "docs/specs/002-due-dates/spec.md").write_text("# Spec: Due dates\n\n**Status:** draft\n", encoding="utf-8")
        code, out = run("build.py", hub, "--no-fetch", "--no-brand")
        results.append(expect("new spec folder builds with a WARN and its own status",
                              code == 0 and "spec 002-due-dates has no entry" in out, out))
        page = (hub / ".work/hub-portal/index.html").read_text(encoding="utf-8")
        results.append(expect("folder and file specs both listed", '"key":"001-create-task"' in page and '"key":"002-due-dates"' in page
                              and "Status in the spec: draft" in page, out))

    spec = importlib.util.spec_from_file_location("hub_portal_build", SCRIPTS / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    results.append(expect("jalali conversion", mod.to_jalali(2026, 10, 7) == (1405, 7, 15) and mod.to_jalali(2026, 3, 21) == (1405, 1, 1)))

    print("\n%d/%d passed" % (sum(results), len(results)))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
