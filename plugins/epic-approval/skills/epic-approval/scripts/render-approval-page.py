#!/usr/bin/env python3
"""Render an epic-approval report folder as ONE shareable, self-contained HTML page.

The Markdown reports stay the source of truth. This reads `README.md` (the launch summary) and
every `<repo-id>.md` in one approval folder and writes `approval.html` next to them: the summary
first, then one section per repo. The page has no external resource (no font, script, image or
stylesheet link), so it opens from disk, prints to PDF from any browser, and can be published as
an Artifact.

Styling: the hub's compiled brand (`<design.build>/brand.css`, made by the brand-system skill) is
inlined when it exists; otherwise a small neutral style is used. Both follow the reader's light or
dark setting, and print on light.

    render-approval-page.py [--hub DIR] [--folder PATH] [--out FILE] [--no-brand]

Without --folder, the newest `<YYYY-MM-DD> - <release branch>` folder under `approvals.out` is used.
Exit codes: 0 written, 2 nothing to render (the message says why), 1 error.
"""

import sys

sys.dont_write_bytecode = True

import argparse
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TABLE_SEP = re.compile(r"^\s*\|?[\s:|-]+\|[\s:|-]*$")
ITEM_RE = re.compile(r"^\s*(?:[-*]|\d+[.)])\s+(.*)$")


class Decide(Exception):
    """Nothing to render; exit 2 with the message."""


def find_hub(explicit):
    if explicit:
        hub = Path(explicit).resolve()
        if not (hub / "brain.config.json").is_file():
            raise RuntimeError(f"--hub {explicit}: no brain.config.json there")
        return hub
    here = Path.cwd().resolve()
    for folder in (here, *here.parents):
        if (folder / "brain.config.json").is_file():
            return folder
    return None


def load_config(hub):
    if not hub:
        return {}
    try:
        return json.loads((hub / "brain.config.json").read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise RuntimeError(f"brain.config.json: invalid JSON at line {e.lineno}: {e.msg}")


def newest_folder(root):
    found = []
    if root.is_dir():
        for d in root.iterdir():
            date, sep, _ = d.name.partition(" - ")
            if d.is_dir() and sep and DATE_RE.match(date):
                found.append((date, d.name, d))
    return max(found)[2] if found else None


# ------------------------------------------------------------------------ Markdown -> HTML

def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "section"


def inline(text, anchors):
    text = html.escape(text, quote=False)
    codes = []

    def stash(m):
        codes.append(m.group(1))
        return f"\x00{len(codes) - 1}\x00"

    text = re.sub(r"`([^`]+)`", stash, text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![*\w])\*([^*\s][^*]*)\*(?!\*)", r"<em>\1</em>", text)

    def link(m):
        label, url = m.group(1), m.group(2)
        plain = html.unescape(url)
        own = re.fullmatch(r"(?:\./)?([\w.-]+)\.md", plain)
        if own and own.group(1) in anchors:
            return f'<a href="#repo-{slug(own.group(1))}">{label}</a>'
        if re.match(r"https?://", plain):
            return f'<a href="{url}" rel="noopener noreferrer">{label}</a>'
        return label  # a relative path that means nothing outside the hub: keep the words only

    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, text)
    return re.sub(r"\x00(\d+)\x00", lambda m: f"<code>{codes[int(m.group(1))]}</code>", text)


def cells(line):
    parts = re.split(r"(?<!\\)\|", line.strip().strip("|"))
    return [p.replace("\\|", "|").strip() for p in parts]


def is_block_start(line, nxt):
    return bool(line.strip().startswith("```") or re.match(r"^#{1,6} ", line) or ITEM_RE.match(line)
                or (line.lstrip().startswith("|") and nxt is not None and TABLE_SEP.match(nxt)))


def render_md(md, anchors, offset=0):
    lines = md.splitlines()
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        nxt = lines[i + 1] if i + 1 < len(lines) else None
        if not line.strip():
            i += 1
        elif line.strip().startswith("```"):
            i += 1
            body = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                body.append(lines[i])
                i += 1
            i += 1
            out.append("<pre><code>" + html.escape("\n".join(body), quote=False) + "</code></pre>")
        elif re.match(r"^#{1,6} ", line):
            level = len(line) - len(line.lstrip("#"))
            tag = f"h{min(6, level + offset)}"
            out.append(f"<{tag}>{inline(line[level:].strip(), anchors)}</{tag}>")
            i += 1
        elif line.lstrip().startswith("|") and nxt is not None and TABLE_SEP.match(nxt):
            head = cells(line)
            i += 2
            rows = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                rows.append(cells(lines[i]))
                i += 1
            t = "<div class=\"table\"><table><thead><tr>"
            t += "".join(f"<th>{inline(c, anchors)}</th>" for c in head) + "</tr></thead><tbody>"
            for row in rows:
                t += "<tr>" + "".join(f"<td>{inline(c, anchors)}</td>" for c in row) + "</tr>"
            out.append(t + "</tbody></table></div>")
        elif ITEM_RE.match(line):
            ordered = bool(re.match(r"^\s*\d", line))
            items = []
            while i < len(lines):
                m = ITEM_RE.match(lines[i])
                if m:
                    items.append(m.group(1))
                elif lines[i].strip() and lines[i].startswith((" ", "\t")) and items:
                    items[-1] += " " + lines[i].strip()
                else:
                    break
                i += 1
            tag = "ol" if ordered else "ul"
            out.append(f"<{tag}>" + "".join(f"<li>{inline(x, anchors)}</li>" for x in items) + f"</{tag}>")
        else:
            para = [line.strip()]
            i += 1
            while i < len(lines) and lines[i].strip() and not is_block_start(
                    lines[i], lines[i + 1] if i + 1 < len(lines) else None):
                para.append(lines[i].strip())
                i += 1
            out.append(f"<p>{inline(' '.join(para), anchors)}</p>")
    return "\n".join(out)


# ------------------------------------------------------------------------ the page

NEUTRAL_LIGHT = ("--bg:#f6f7f9;--surface:#ffffff;--ink:#1c2230;--muted:#5a6376;--border:#d9dde5;"
                 "--accent:#2f5bd8;--ok:#1a7f45;--warn:#9a6700;--bad:#c62828;")
NEUTRAL_DARK = ("--bg:#12151c;--surface:#1b202b;--ink:#e6e9f0;--muted:#a3abbb;--border:#333b4b;"
                "--accent:#8aa8ff;--ok:#5fd08a;--warn:#e0b04a;--bad:#ff8a80;")
BRAND_MAP = ("--bg:var(--ds-canvas);--surface:var(--ds-surface);--ink:var(--ds-ink);"
             "--muted:var(--ds-muted);--border:var(--ds-border);--accent:var(--ds-primary);"
             "--ok:var(--ds-success-ink);--warn:var(--ds-warning-ink);--bad:var(--ds-danger-ink);"
             "font-family:var(--ds-font-body);")

BASE_CSS = """
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 system-ui,sans-serif;
  -webkit-print-color-adjust:exact;print-color-adjust:exact}
main{max-width:62rem;margin:0 auto;padding:2rem 1rem 4rem}
h1{font-size:1.8rem;margin:.2rem 0 1rem}
h2{font-size:1.35rem;margin:2rem 0 .6rem}
h3{font-size:1.1rem;margin:1.6rem 0 .5rem}
h4{font-size:1rem;margin:1.2rem 0 .4rem}
p,li{max-width:70ch}
a{color:var(--accent)}
code{font:.9em ui-monospace,monospace;background:var(--surface);border:1px solid var(--border);
  border-radius:4px;padding:.05em .3em}
pre{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:.8rem;overflow:auto}
pre code{border:0;padding:0;background:none}
.table{overflow-x:auto;margin:.8rem 0}
table{border-collapse:collapse;width:100%;background:var(--surface);border:1px solid var(--border)}
th,td{border:1px solid var(--border);padding:.45rem .6rem;text-align:start;vertical-align:top}
th{background:var(--bg)}
.stamp{color:var(--muted);font-size:.9rem;margin:0 0 1rem}
.decision{border:1px solid var(--border);border-inline-start:6px solid var(--muted);border-radius:8px;
  background:var(--surface);padding:.7rem 1rem;margin:1rem 0;font-size:1.1rem}
.decision.ok{border-inline-start-color:var(--ok)}
.decision.warn{border-inline-start-color:var(--warn)}
.decision.bad{border-inline-start-color:var(--bad)}
section.repo{margin-top:2.5rem;padding-top:1rem;border-top:2px solid var(--border)}
@media print{body{background:#fff}table,pre{break-inside:avoid}h1,h2,h3{break-after:avoid}}
"""


def decision_class(readme):
    m = re.search(r"\*\*Launch decision:\*\*\s*(.+)", readme)
    text = (m.group(1) if m else "").upper()
    if "NOT APPROVED" in text:
        return "bad"
    if "CONDITIONS" in text:
        return "warn"
    return "ok" if "APPROVED" in text else ""


def build_page(folder, brand_css):
    readme_path = folder / "README.md"
    if not readme_path.is_file():
        raise Decide(f"{folder.name} has no README.md (the launch summary) - nothing to render")
    reports = [(p.stem, p.read_text(encoding="utf-8")) for p in sorted(folder.glob("*.md"))
               if p.name.lower() != "readme.md"]
    anchors = {name for name, _ in reports}
    readme = readme_path.read_text(encoding="utf-8")
    body = render_md(readme, anchors)
    cls = decision_class(readme)
    if cls:
        body = re.sub(r"<p>(<strong>Launch decision:</strong>.*?)</p>",
                      rf'<p class="decision {cls}">\1</p>', body, count=1, flags=re.S)
    for name, text in reports:
        body += f'\n<section class="repo" id="repo-{slug(name)}">\n{render_md(text, anchors, 1)}\n</section>'
    title = re.search(r"^# (.+)$", readme, re.M)
    title = html.escape(title.group(1) if title else f"Launch approval - {folder.name}")
    stamp = html.escape(folder.name)
    generated = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if brand_css:
        theme = (f"<style>\n/* BRAND:BEGIN */\n{brand_css}\n/* BRAND:END */\n</style>\n"
                 f"<style>\n:root{{{BRAND_MAP}}}\n{BASE_CSS}</style>")
    else:
        theme = (f"<style>\n:root{{{NEUTRAL_LIGHT}}}\n@media (prefers-color-scheme:dark){{:root{{{NEUTRAL_DARK}}}}}\n"
                 f"{BASE_CSS}</style>")
    return (f'<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f'<meta name="generated" content="{generated}">\n<title>{title}</title>\n{theme}\n</head>\n'
            f'<body>\n<main>\n<p class="stamp">{stamp}</p>\n{body}\n</main>\n</body>\n</html>\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--hub", help="hub folder (default: walk up from the current directory)")
    ap.add_argument("--folder", help="the approval folder (default: the newest under approvals.out)")
    ap.add_argument("--out", help="output file (default: <folder>/approval.html)")
    ap.add_argument("--no-brand", action="store_true", help="use the neutral style even if a brand exists")
    args = ap.parse_args()
    try:
        hub = find_hub(args.hub)
        cfg = load_config(hub)
        if args.folder:
            folder = Path(args.folder)
            if not folder.is_dir() and hub and (hub / args.folder).is_dir():
                folder = hub / args.folder
            if not folder.is_dir():
                raise Decide(f"--folder {args.folder}: no such folder")
        else:
            out = (cfg.get("approvals") or {}).get("out")
            if not hub or not out:
                raise Decide("approvals.out is not set (or no hub here); pass --folder PATH")
            folder = newest_folder(hub / out)
            if not folder:
                raise Decide(f"no '<date> - <release branch>' folder under {out} - "
                             "has epic-approval written its reports yet?")
        brand_css, style = None, "neutral"
        if hub and not args.no_brand:
            build = (cfg.get("design") or {}).get("build") or "brand"
            css = hub / build / "brand.css"
            if css.is_file():
                brand_css, style = css.read_text(encoding="utf-8"), "brand"
        page = build_page(folder.resolve(), brand_css)
        target = Path(args.out) if args.out else folder / "approval.html"
        target.write_text(page, encoding="utf-8")
    except Decide as e:
        print(f"decide: {e}", file=sys.stderr)
        return 2
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(f"wrote {target} ({target.stat().st_size // 1024} KB, {style} style)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
