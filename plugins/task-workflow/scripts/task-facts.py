#!/usr/bin/env python3
"""Facts and the one file move behind the task-workflow skills (task-description, task-plan,
task-ticket, quality-gate).

Reads the `tasks` block of brain.config.json. It never calls the tracker, never commits and never
pushes: the skills do that, after a person confirms. What it does do is the part that must be
exact every time - where a task or draft lives, what its links and branch are called, moving a
draft to its key, and whether the files an agent will read are really on the hub's server.

    task-facts.py [--hub DIR] config                  resolved settings, templates and warnings
    task-facts.py [--hub DIR] drafts                  every draft waiting for a ticket
    task-facts.py [--hub DIR] resolve [KEY|SLUG|PATH] which folder a skill should work in
    task-facts.py [--hub DIR] links KEY               ticket URL, branch, hub URLs of the task files
    task-facts.py [--hub DIR] finalize DRAFT KEY      move a draft to <dir>/<KEY>/, swap in the key
    task-facts.py [--hub DIR] verify KEY [--no-fetch] are the task files on the server, and current?

Keys read from brain.config.json (`tasks`; `portal.tasks` is the older place for dir/key_regex):

  dir            required  "tasks" - one folder per ticket, <dir>/<KEY>/
  key_regex      required  "^PROJ-\\d+$" - a ticket key, and the only folder name allowed for a task
  drafts         "drafts"  drafts without a ticket: <dir>/<drafts>/<slug>/, one folder per draft
  placeholder    "<tracker.project>-NNN" (else "KEY-NNN") - the key written into a draft's files
  branch         "{key_lower}" - branch name; {key}, {key_lower} and {n} (the key's number)
  base_branch    releases.integration_branch, else "main" - where task branches start and merge
  tracker        {"kind": "jira|gitlab|github", "url": ..., "project": ..., "fields": {...}}
  areas          {"<repo id>": "BE"} - the short label each repo gets in a ticket summary
  locales        ["en"] - the first one is the primary language for copy and screenshots
  conventions    path of the hub's own task rules (test commands, review commands, apps, widths)
  source         {"blob", "tree", "branch"} - else portal.source, else derived from the origin remote

Exit codes: 0 done, 2 a person must decide (which draft, a folder already there, not ready to
run), 1 error.
"""

import sys

sys.dont_write_bytecode = True

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
TEMPLATES = ["task-description", "task-plan", "task-report", "task-ticket-blocks"]
TRACKERS = ("jira", "gitlab", "github")
LEGACY_DRAFT = "draft"  # the single draft folder used before drafts had a folder each


class Decide(Exception):
    """Something a person has to choose: exit 2 with the message."""


def die(msg):
    print("task-facts: ERROR: " + msg, file=sys.stderr)
    sys.exit(1)


def git(hub, *args, check=True):
    p = subprocess.run(["git", "-C", str(hub), *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if check and p.returncode:
        raise RuntimeError("git %s: %s" % (" ".join(args), p.stderr.strip()))
    return p


# ── settings ──────────────────────────────────────────────────────────


def derive_source(hub, branch):
    """Blob/tree URL prefixes from the origin remote (GitHub style for github.com, else GitLab)."""
    p = git(hub, "remote", "get-url", "origin", check=False)
    url = p.stdout.strip()
    m = (re.match(r"^(?:ssh://)?[^@/]+@([^:/]+)(?::\d+)?[:/](.+?)(?:\.git)?/?$", url)
         or re.match(r"^https?://(?:[^@/]+@)?([^/:]+)(?::\d+)?/(.+?)(?:\.git)?/?$", url))
    if not m:
        return None
    host, path = m.groups()
    base = "https://%s/%s" % (host, path)
    sep = "" if host == "github.com" else "/-"
    return {"blob": "%s%s/blob/%s/" % (base, sep, branch), "tree": "%s%s/tree/%s/" % (base, sep, branch),
            "branch": branch}


def default_branch(hub):
    p = git(hub, "symbolic-ref", "--short", "refs/remotes/origin/HEAD", check=False)
    return p.stdout.strip().split("/", 1)[1] if p.returncode == 0 and "/" in p.stdout else "main"


def load(hub):
    path = hub / "brain.config.json"
    if not path.is_file():
        die("no brain.config.json in %s - run this from the hub, or pass --hub" % hub)
    try:
        cfg = json.loads(path.read_text(encoding="utf-8-sig"))
    except ValueError as e:
        die("brain.config.json is not valid JSON: %s" % e)
    t = cfg.get("tasks") if cfg.get("tasks") is not None else (cfg.get("portal") or {}).get("tasks")
    example = '{"dir": "tasks", "key_regex": "^PROJ-\\\\d+$"}'
    if not isinstance(t, dict) or not t.get("dir") or not t.get("key_regex"):
        die('brain.config.json needs a "tasks" block with "dir" and "key_regex", e.g. "tasks": ' + example)
    try:
        key_rx = re.compile(t["key_regex"])
    except re.error as e:
        die("tasks.key_regex is not a valid regex: %s" % e)
    warnings = []
    tracker = t.get("tracker")
    if tracker is not None:
        if not isinstance(tracker, dict) or tracker.get("kind") not in TRACKERS or not tracker.get("url"):
            die('tasks.tracker needs "kind" (jira, gitlab or github) and "url", e.g. '
                '{"kind": "jira", "url": "https://jira.example.com", "project": "PROJ"}')
        if tracker["kind"] == "jira" and not tracker.get("project"):
            die('tasks.tracker.project is required for Jira, e.g. "PROJ"')
        tracker = {**tracker, "url": tracker["url"].rstrip("/")}
    else:
        warnings.append("tasks.tracker is not set: /task-ticket cannot create tickets until it is")
    placeholder = t.get("placeholder") or ("%s-NNN" % tracker["project"] if tracker and tracker.get("project")
                                           else "KEY-NNN")
    branch = t.get("branch") or "{key_lower}"
    try:
        branch.format(key="K-1", key_lower="k-1", n="1")
    except (KeyError, IndexError, ValueError):
        die('tasks.branch may use only {key}, {key_lower} and {n}, e.g. "task/{key_lower}"')
    branch_on = (t.get("source") or (cfg.get("portal") or {}).get("source") or {}).get("branch") or default_branch(hub)
    source = t.get("source") or (cfg.get("portal") or {}).get("source") or derive_source(hub, branch_on)
    if not source:
        warnings.append("no hub URL: set tasks.source (or portal.source) - ticket links need it")
    conventions = t.get("conventions")
    if conventions and not (hub / conventions).is_file():
        warnings.append("tasks.conventions names %s, which does not exist" % conventions)
    if not conventions:
        warnings.append("tasks.conventions is not set: the skills fall back to the hub's CLAUDE.md "
                        "for test, review and app rules")
    templates = {}
    for name in TEMPLATES:
        own = hub / "templates" / (name + ".md")
        templates[name] = ({"path": own.relative_to(hub).as_posix(), "from": "hub"} if own.is_file()
                           else {"path": str(PLUGIN / "templates" / (name + ".md")), "from": "plugin"})
    if templates["task-report"]["from"] == "plugin":
        warnings.append("the hub has no templates/task-report.md: an agent working from the git server "
                        "cannot read the plugin's copy, so copy it into the hub")
    s = {
        "dir": t["dir"].strip("/"),
        "key_regex": t["key_regex"],
        "drafts": (t.get("drafts") or "drafts").strip("/"),
        "placeholder": placeholder,
        "placeholder_branch": render_branch(branch, placeholder, "NNN"),
        "branch": branch,
        "base_branch": t.get("base_branch") or (cfg.get("releases") or {}).get("integration_branch") or "main",
        "tracker": tracker,
        "areas": t.get("areas") or {},
        "locales": t.get("locales") or ["en"],
        "conventions": conventions,
        "source": source,
        "templates": templates,
        "warnings": warnings,
    }
    s["_key_rx"] = key_rx
    return s


def render_branch(pattern, key, n):
    return pattern.format(key=key, key_lower=key.lower(), n=n)


def key_number(key):
    m = re.search(r"(\d+)$", key)
    return m.group(1) if m else key


def public(s):
    return {k: v for k, v in s.items() if not k.startswith("_")}


# ── drafts and folders ────────────────────────────────────────────────


def header_field(text, name):
    m = re.search(r"^\|\s*%s\s*\|\s*(.*?)\s*\|\s*$" % re.escape(name), text, re.M)
    return m.group(1) if m else None


def draft_info(hub, folder, legacy=False):
    desc = folder / "description.md"
    text = desc.read_text(encoding="utf-8", errors="replace") if desc.is_file() else ""
    title = next((ln[2:].strip() for ln in text.splitlines() if ln.startswith("# ")), None)
    return {"slug": folder.name, "path": folder.relative_to(hub).as_posix(), "title": title,
            "status": header_field(text, "Status"), "has_description": desc.is_file(),
            "has_plan": (folder / "plan.md").is_file(), "legacy": legacy}


def legacy_drafts(hub, s):
    """Drafts made before drafts had a folder each: any folder directly in <dir>/ that is neither a
    ticket key nor the drafts folder (tasks/draft/, and the tasks/draft2/ people made to get a second)."""
    root = hub / s["dir"]
    return sorted((p for p in root.glob("*") if p.is_dir() and p.name != s["drafts"]
                   and not p.name.startswith(".") and not s["_key_rx"].match(p.name)), key=lambda p: p.name)


def list_drafts(hub, s):
    found = sorted((p for p in (hub / s["dir"] / s["drafts"]).glob("*") if p.is_dir()), key=lambda p: p.name)
    return [draft_info(hub, p) for p in found] + [draft_info(hub, p, legacy=True) for p in legacy_drafts(hub, s)]


def resolve(hub, s, arg):
    if arg and s["_key_rx"].match(arg):
        folder = hub / s["dir"] / arg
        return {"kind": "task", "key": arg, "path": folder.relative_to(hub).as_posix(), "exists": folder.is_dir()}
    if arg:
        rel = arg.replace("\\", "/").strip("/")
        prefix = "%s/%s/" % (s["dir"], s["drafts"])
        legacy = {p.name: p for p in legacy_drafts(hub, s)}
        if rel.startswith(prefix):
            rel = rel[len(prefix):]
        elif rel.startswith(s["dir"] + "/") and rel[len(s["dir"]) + 1:] in legacy:
            rel = rel[len(s["dir"]) + 1:]
        elif "/" in rel:
            raise Decide("%s is not a task (%s/<KEY>/) or a draft (%s<slug>/)" % (arg, s["dir"], prefix))
        if rel in legacy and not (hub / s["dir"] / s["drafts"] / rel).is_dir():
            folder = legacy[rel]  # an older draft is used where it is, never moved
        else:
            if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", rel):
                raise Decide("draft slug %r must be lower-case kebab-case, e.g. sms-limit-international" % rel)
            folder = hub / s["dir"] / s["drafts"] / rel
        return {"kind": "draft", "slug": folder.name, "path": folder.relative_to(hub).as_posix(),
                "exists": folder.is_dir()}
    drafts = list_drafts(hub, s)
    if len(drafts) == 1:
        return {"kind": "draft", "slug": drafts[0]["slug"], "path": drafts[0]["path"], "exists": True}
    if not drafts:
        raise Decide("no drafts in %s/%s/ - start one with /task-description" % (s["dir"], s["drafts"]))
    lines = ["  %s  %s  [%s]" % (d["slug"], d["title"] or "(no description)", d["status"] or "no status")
             for d in drafts]
    raise Decide("several drafts - ask which one:\n" + "\n".join(lines))


# ── links, finalize, verify ───────────────────────────────────────────


def links(hub, s, key):
    if not s["_key_rx"].match(key):
        raise Decide("%s does not match tasks.key_regex %s" % (key, s["key_regex"]))
    n, folder = key_number(key), "%s/%s" % (s["dir"], key)
    tr, ticket = s["tracker"], None
    if tr:
        ticket = {"jira": "%s/browse/%s" % (tr["url"], key), "gitlab": "%s/-/issues/%s" % (tr["url"], n),
                  "github": "%s/issues/%s" % (tr["url"], n)}[tr["kind"]]
    src = s["source"] or {}
    blob, tree = src.get("blob"), src.get("tree")
    files = {name: (blob + "%s/%s" % (folder, name)) if blob else None
             for name in ("description.md", "plan.md", "report.md")}
    report_tpl = s["templates"]["task-report"]
    return {
        "key": key, "folder": folder, "ticket": ticket,
        "branch": render_branch(s["branch"], key, n), "base_branch": s["base_branch"],
        "files": files,
        "mockups": (tree + folder + "/mockups") if tree else None,
        "constitution": (blob + "constitution.md") if blob and (hub / "constitution.md").is_file() else None,
        "report_template": (blob + report_tpl["path"]) if blob and report_tpl["from"] == "hub" else None,
        "on_branch": src.get("branch"),
    }


def finalize(hub, s, draft, key):
    if not s["_key_rx"].match(key):
        raise Decide("%s does not match tasks.key_regex %s" % (key, s["key_regex"]))
    d = resolve(hub, s, draft)
    if d["kind"] != "draft" or not d["exists"]:
        raise Decide("no draft folder %s" % d["path"])
    src, dst = hub / d["path"], hub / s["dir"] / key
    if dst.exists():
        raise Decide("%s already exists - ask before touching it" % dst.relative_to(hub).as_posix())
    shutil.move(str(src), str(dst))
    branch = render_branch(s["branch"], key, key_number(key))
    changed = []
    for f in sorted(p for p in dst.rglob("*") if p.is_file() and p.suffix in (".md", ".html")):
        text = f.read_text(encoding="utf-8")
        new = text.replace(s["placeholder_branch"], branch).replace(s["placeholder"], key)
        if new != text:
            f.write_text(new, encoding="utf-8")
            changed.append(f.relative_to(hub).as_posix())
    return {"from": d["path"], "to": dst.relative_to(hub).as_posix(), "branch": branch, "changed": changed}


def verify(hub, s, key, fetch=True):
    """One line per file the agent reads: OK, MISSING on <branch>, or DIFFERS from <branch>."""
    if not s["_key_rx"].match(key):
        raise Decide("%s does not match tasks.key_regex %s" % (key, s["key_regex"]))
    on = (s["source"] or {}).get("branch") or "main"
    if fetch:
        git(hub, "fetch", "-q", "origin", on)
    ref, folder = "origin/" + on, hub / s["dir"] / key
    if not folder.is_dir():
        raise Decide("%s does not exist locally" % folder.relative_to(hub).as_posix())
    paths = (["constitution.md"] if (hub / "constitution.md").is_file() else []) + sorted(
        p.relative_to(hub).as_posix() for p in folder.rglob("*") if p.is_file() and p.name != "report.md")
    rows, stale = [], []
    for p in paths:
        remote = git(hub, "rev-parse", "-q", "--verify", "%s:%s" % (ref, p), check=False).stdout.strip()
        if not remote:
            rows.append("MISSING on %s: %s" % (on, p))
            stale.append(p)
        elif git(hub, "hash-object", "--", p).stdout.strip() != remote:
            rows.append("DIFFERS from %s: %s" % (on, p))
            stale.append(p)
        else:
            rows.append("OK %s" % p)
    return rows, push_list(paths, stale, folder.relative_to(hub).as_posix()), on


def push_list(paths, stale, folder):
    """What to push, as short as it stays exact: the task folder when every file in it is stale."""
    inside = [p for p in paths if p.startswith(folder + "/")]
    stale_inside = [p for p in stale if p.startswith(folder + "/")]
    if inside and stale_inside == inside:
        return [p for p in stale if not p.startswith(folder + "/")] + [folder + "/"]
    return stale


# ── main ──────────────────────────────────────────────────────────────


def main():
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(prog="task-facts.py", description=__doc__.split("\n\n")[0])
    ap.add_argument("--hub", default=".")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("config")
    sub.add_parser("drafts")
    r = sub.add_parser("resolve")
    r.add_argument("target", nargs="?", default="")
    lk = sub.add_parser("links")
    lk.add_argument("key")
    f = sub.add_parser("finalize")
    f.add_argument("draft")
    f.add_argument("key")
    v = sub.add_parser("verify")
    v.add_argument("key")
    v.add_argument("--no-fetch", action="store_true")
    a = ap.parse_args()

    hub = Path(a.hub).resolve()
    s = load(hub)
    try:
        if a.cmd == "config":
            out = public(s)
        elif a.cmd == "drafts":
            out = list_drafts(hub, s)
        elif a.cmd == "resolve":
            out = resolve(hub, s, a.target)
        elif a.cmd == "links":
            out = links(hub, s, a.key)
        elif a.cmd == "finalize":
            out = finalize(hub, s, a.draft, a.key)
        else:
            rows, push, on = verify(hub, s, a.key, fetch=not a.no_fetch)
            print("\n".join(rows))
            print("Not ready to run: push %s to %s first." % (", ".join(push), on) if push else
                  "Ready to run: every file the agent reads is current on %s." % on)
            return 2 if push else 0
    except Decide as e:
        print(str(e), file=sys.stderr)
        return 2
    except RuntimeError as e:
        die(str(e))
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
