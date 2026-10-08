"""Self-check for plugins/epic-approval/skills/epic-approval/scripts/render-approval-page.py.

Run: python3 tests/test_render_approval.py
"""

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "plugins/epic-approval/skills/epic-approval/scripts/render-approval-page.py"

README = """# Launch approval — release.1.5.0 · 2026-09-20

**Launch decision:** ⚠️ APPROVED WITH CONDITIONS

| Repo | Kind | Decision |
|---|---|---|
| [api](api.md) | backend | ⚠️ |
| [web](web.md) | frontend | ✅ |

## Conditions to launch
1. api: run the migration first (`2026_01_add_col.php`)
2. api: `<script>alert(1)</script> is not escaped upstream

## Not reviewed
none
"""
API = """# api (backend) — release.1.5.0 → main

**Decision:** ⚠️ APPROVED WITH CONDITIONS

## 1. Change scope controlled — PASS
- feat: add payments | see [docs](https://example.com/docs?a=1&b=2)
- *Checked:* commit messages

```
env('PAYMENT_KEY')
```

[local file](../../secret.md) and [bad](javascript:alert(1))
"""
WEB = "# web (frontend) — release.1.5.0 → main\n\n**Decision:** ✅ APPROVED\n"


def run(*args, cwd=None):
    proc = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, cwd=cwd)
    return proc.returncode, proc.stdout, proc.stderr


def check(cond, what):
    if not cond:
        print("FAIL:", what)
        sys.exit(1)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        hub = Path(tmp) / "hub"
        old = hub / "docs/approvals/2026-09-10 - release.1.5.0"
        new = hub / "docs/approvals/2026-09-20 - release.1.5.0"
        for d in (old, new):
            d.mkdir(parents=True)
        (old / "README.md").write_text("# old run\n")
        (new / "README.md").write_text(README, encoding="utf-8")
        (new / "api.md").write_text(API, encoding="utf-8")
        (new / "web.md").write_text(WEB, encoding="utf-8")
        (hub / "brain.config.json").write_text(json.dumps({"approvals": {"out": "docs/approvals"}}))

        # neutral style, newest folder chosen
        rc, out, err = run("--hub", str(hub))
        check(rc == 0, f"render failed: {err}")
        made = hub / ".work/epic-approval" / new.name / "approval.html"
        check(made.is_file() and not (new / "approval.html").exists(),
              "page goes to .work, never into the report folder")
        page = made.read_text(encoding="utf-8")
        check("old run" not in page and "Launch approval" in page, "newest folder rendered")
        check('<meta charset="utf-8">' in page and "neutral style" in out, "charset first, neutral style")
        check(page.count('<section class="repo"') == 2 and 'id="repo-api"' in page and 'id="repo-web"' in page,
              "one section per repo")
        check('href="#repo-api"' in page and 'href="#repo-web"' in page, "repo links became in-page anchors")
        check("<table>" in page and "<th>Repo</th>" in page and "<ol>" in page, "table and list rendered")
        check('class="decision warn"' in page, "decision callout tone")
        check("<script>" not in page.replace("<script>alert", "") and "&lt;script&gt;" in page, "HTML escaped")
        check("<h2>api (backend)" in page and "<h3>1. Change scope controlled" in page, "repo headings nested a level")
        check('href="https://example.com/docs?a=1&amp;b=2"' in page, "external link kept, ampersand escaped")
        check("secret.md" not in re.sub(r"<[^>]+>", "", page).replace("local file", "") and "javascript:" not in page,
              "relative and javascript links dropped to plain words")
        check("<pre><code>env('PAYMENT_KEY')" in page, "code block kept")
        check(not re.search(r"<(link|script|img|iframe)\b", page), "no external resource of any kind")
        check("BRAND:BEGIN" not in page, "no brand block without a brand")

        # brand inlined when the hub has one
        (hub / "brand").mkdir()
        (hub / "brand/brand.css").write_text(":root{--ds-canvas:#fefefe;--ds-ink:#111}\n")
        rc, out, err = run("--hub", str(hub))
        page = made.read_text(encoding="utf-8")
        check(rc == 0 and "brand style" in out and "BRAND:BEGIN" in page and "--ds-canvas:#fefefe" in page
              and "--bg:var(--ds-canvas)" in page, "brand inlined and mapped")
        rc, out, err = run("--hub", str(hub), "--no-brand")
        check("neutral style" in out, "--no-brand forces the neutral style")

        # explicit folder and output, blocked cases
        target = Path(tmp) / "shared.html"
        rc, out, err = run("--hub", str(hub), "--folder", "docs/approvals/2026-09-20 - release.1.5.0", "--out", str(target))
        check(rc == 0 and target.is_file(), "--folder (hub-relative) and --out")
        rc, out, err = run("--hub", str(hub), "--folder", str(old / "nope"))
        check(rc == 2, "missing folder -> exit 2")
        (old / "README.md").unlink()
        rc, out, err = run("--hub", str(hub), "--folder", str(old))
        check(rc == 2 and "README.md" in err, "folder without a summary -> exit 2")
        (hub / "brain.config.json").write_text("{}")
        rc, out, err = run("--hub", str(hub))
        check(rc == 2 and "approvals.out" in err, "no approvals.out -> exit 2")

    print("ok")


if __name__ == "__main__":
    main()
