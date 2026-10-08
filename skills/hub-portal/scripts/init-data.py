#!/usr/bin/env python3
"""Write a starter portal data file for a hub that has none.

    python init-data.py [--hub DIR] [--force]

Fills in what can be read from the hub (spec names, the skills and agents under .claude/,
the core documents) and marks every fact a person must supply with TODO. build.py refuses
to build while any TODO remains, so a half-filled page can never be published.
Never overwrites an existing data file unless --force.
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SKILL = Path(__file__).resolve().parents[1]
STARTER = SKILL / "assets" / "portal-data.template.json"


def find_hub(start):
    d = Path(start).resolve()
    for p in [d, *d.parents]:
        if (p / "brain.config.json").is_file():
            return p
    sys.exit("ERROR no brain.config.json in %s or above - run from inside a hub or pass --hub" % d)


def frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text.replace("\r\n", "\n"), re.S)
    out = {}
    for line in (m.group(1).split("\n") if m else []):
        k, _, v = line.partition(":")
        if v.strip():
            out[k.strip()] = v.strip().strip("\"'")
    return out


def first_sentence(text, limit=110):
    text = re.sub(r"^Use (this )?when (the user )?", "", text.strip(), flags=re.I)
    s = re.split(r"(?<=[.;])\s", text)[0].rstrip(".;")
    s = s[:1].upper() + s[1:]
    return s if len(s) <= limit else s[:limit - 1].rsplit(" ", 1)[0] + "…"


def h1(path):
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            return re.sub(r"^(Feature Specification|Spec(ification)?)\s*:\s*", "", line[2:].strip(), flags=re.I)
    return path.stem


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--hub", default=".")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    hub = find_hub(a.hub)
    cfg = json.loads((hub / "brain.config.json").read_text(encoding="utf-8"))
    portal = cfg.get("portal") or {}
    target = portal.get("data")
    if not target:
        sys.exit('ERROR set portal.data in brain.config.json first, e.g. "portal": {"data": "docs/dashboard/hub-portal.json"}')
    dest = hub / target
    if dest.exists() and not a.force:
        sys.exit("ERROR %s already exists - edit it, or pass --force to start over" % target)

    data = json.loads(STARTER.read_text(encoding="utf-8"))
    name = cfg.get("hub", {}).get("name") or cfg.get("hub_name") or hub.name
    data["title"] = "%s Brain Hub" % name
    data["wordmark"]["latin"] = name
    data["wordmark"]["local"] = cfg.get("releases", {}).get("client_note", {}).get("product_name", "")

    specs_dir = (portal.get("specs_dir") or cfg.get("roadmap", {}).get("specs_dir")
                 or cfg.get("releases", {}).get("specs_dir") or "docs/specs")
    sroot = hub / specs_dir
    for child in sorted(sroot.iterdir()) if sroot.is_dir() else []:
        main_doc = child / "spec.md" if child.is_dir() else child
        if child.is_dir() and not main_doc.is_file():
            docs = sorted(child.glob("*.md"))
            main_doc = docs[0] if docs else None
        if child.is_file() and (child.suffix != ".md" or child.name.lower() == "readme.md"):
            continue
        key = child.name if child.is_dir() else child.stem
        note = "TODO: where this spec stands"
        if main_doc and main_doc.is_file():
            m = re.search(r"\*\*Status:\*\*\s*([^\n]+)", main_doc.read_text(encoding="utf-8"))
            if m:
                note = "TODO: confirm. The spec says: " + m.group(1).strip()
        data["specs"][key] = {"name": h1(main_doc) if main_doc else key, "status": "spec", "note": note}

    groups = {}
    for kind, pattern in (("Skills", ".claude/skills/*/SKILL.md"), ("Commands", ".claude/commands/*.md"),
                          ("Agents", ".claude/agents/*.md")):
        for f in sorted(hub.glob(pattern)):
            fm = frontmatter(f.read_text(encoding="utf-8"))
            cmd = fm.get("name") or (f.parent.name if f.name == "SKILL.md" else f.stem)
            groups.setdefault(kind, []).append({
                "cmd": cmd if kind == "Agents" else "/" + cmd,
                "desc": first_sentence(fm.get("description", "")) or "TODO: one line on what it does",
                "path": f.relative_to(hub).as_posix()})
    data["skillGroups"] = [{"group": g, "items": items} for g, items in groups.items()]

    core = [p for p in ("constitution.md", "vocabulary.md", "domains.md", "PRODUCT.md", "DESIGN.md", "README.md")
            if (hub / p).is_file()]
    data["library"]["start"] = core[:6]
    data["hub"]["map"] = [[p, h1(hub / p), p] for p in core]
    data["brand"]["designDoc"] = cfg.get("design", {}).get("system", "DESIGN.md") if (hub / cfg.get("design", {}).get("system", "DESIGN.md")).is_file() else ""

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    todo = json.dumps(data).count("TODO")
    print("Wrote %s with %d specs and %d skill cards. %d TODO field(s) left to fill - build.py lists each one."
          % (target, len(data["specs"]), sum(len(g["items"]) for g in data["skillGroups"]), todo))


if __name__ == "__main__":
    main()
