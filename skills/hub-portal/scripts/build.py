#!/usr/bin/env python3
"""Build the hub portal: one page with the hub's status and every hub document in it.

    python build.py [--hub DIR] [--no-fetch] [--no-brand]

Reads brain.config.json -> `portal` and the hand-maintained data file it names, derives
everything mechanical from the hub (document index and bundles, spec and task rows,
constitution principles, graph stats, display dates), writes <portal.out>/index.html plus
<portal.out>/md/<bundle>.json, inlines the compiled brand and runs check-brand.

Exit 0 = built (WARN lines may remain; resolve or report them). Exit 1 = at least one
ERROR: a privacy hit, a broken reference, a stale data key, an unknown status, or an
off-brand page. Nothing is written on ERROR except the messages. The last thing printed
on success is the Artifact publish call.

Each check exists because the page would otherwise publish something wrong:
  privacy scan     a phone number from an incident note was about to be published
  references       a workflow card pointed at a runbook that had been renamed
  stale data keys  a spec folder was renamed and its old status kept showing
  spec coverage    a new spec folder silently had no state on the page
"""

import argparse
import datetime as dt
import html
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SKILL = Path(__file__).resolve().parents[1]
SKILLS = SKILL.parent
TEMPLATE = SKILL / "assets" / "portal.template.html"
BRAND_SCRIPTS = SKILLS / "brand-system" / "scripts"
EXCLUDE_TOP = {"repos", "graph", "graphify-out", "logs", "node_modules", "dist"}
EXCLUDE_DOT = {".worktrees", ".work", ".git"}
# Always scanned. Hub-specific patterns (a national phone format, an ID number) go in the
# data file's privacy.patterns.
DEFAULT_PATTERNS = [
    ("phone number", r"(?<![\w+])\+\d{1,3}[ -]?\d{2,4}[ -]?\d{3,4}[ -]?\d{3,4}(?!\d)"),
    ("secret", r"sk_(?:live|test)_[A-Za-z0-9]{8,}|glpat-[A-Za-z0-9_-]{10,}|gh[pousr]_[A-Za-z0-9]{20,}"
               r"|AKIA[0-9A-Z]{12,}|-----BEGIN [A-Z ]*PRIVATE KEY|xox[abpr]-[A-Za-z0-9-]{10,}"),
]
REQUIRED_DATA = ("title", "asOf", "status", "specStatus", "specs", "artifactGroups", "artifacts",
                 "flows", "skillGroups", "library", "brand", "hub", "privacy")
JALALI_MONTHS = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر",
                 "دی", "بهمن", "اسفند"]
FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
SPEC_FILES = ["spec.md", "plan.md", "tasks.md", "research.md", "data-model.md", "quickstart.md"]
TASK_FILES = ["description.md", "plan.md", "report.md"]

errors, warns = [], []


def err(msg):
    errors.append(msg)


def warn(msg):
    warns.append(msg)


def die(msg):
    print("ERROR " + msg)
    sys.exit(1)


def find_hub(start):
    d = Path(start).resolve()
    for p in [d, *d.parents]:
        if (p / "brain.config.json").is_file():
            return p
    die("no brain.config.json in %s or above - run from inside a hub or pass --hub" % d)


def git(hub, *args, timeout=60):
    try:
        r = subprocess.run(["git", "-C", str(hub), *args], capture_output=True, text=True,
                           encoding="utf-8", timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout if r.returncode == 0 else None


def load_json(path, what):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        die("%s not found: %s" % (what, path))
    except json.JSONDecodeError as e:
        die("%s is not valid JSON: line %d column %d: %s" % (path, e.lineno, e.colno, e.msg))


def to_jalali(gy, gm, gd):
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    gy2 = gy + 1 if gm > 2 else gy
    days = 355666 + 365 * gy + (gy2 + 3) // 4 - (gy2 + 99) // 100 + (gy2 + 399) // 400 + gd + g_d_m[gm - 1]
    jy = -1595 + 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        return jy, 1 + days // 31, 1 + days % 31
    return jy, 7 + (days - 186) // 30, 1 + (days - 186) % 30


def humanize(name):
    name = name.lstrip(".").replace("-", " ").replace("_", " ")
    return name[:1].upper() + name[1:]


def clean_heading(t):
    t = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", t)
    return re.sub(r"[*_`]|<[^>]+>", "", t).strip()


def title_of(path, text):
    fm = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    name = re.search(r"^name:\s*['\"]?([^'\"\n]+)", fm.group(1), re.M) if fm else None
    if path.endswith("SKILL.md") and name:
        return "/" + name.group(1).strip()
    for line in (text[fm.end():] if fm else text).split("\n"):
        m = re.match(r"^#\s+(.+)", line)
        if m:
            t = clean_heading(m.group(1))
            t = re.sub(r"^[^\w؀-ۿ]+", "", t)
            return t[:140] or os.path.basename(path)
    return name.group(1).strip() if name else os.path.basename(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--hub", default=".")
    ap.add_argument("--no-fetch", action="store_true", help="do not fetch the source branch first")
    ap.add_argument("--no-brand", action="store_true", help="skip brand inline + check (debugging only; never publish)")
    a = ap.parse_args()
    hub = find_hub(a.hub)
    cfg = load_json(hub / "brain.config.json", "brain.config.json")

    # ── config ─────────────────────────────────────────────────────────
    portal = cfg.get("portal")
    if not isinstance(portal, dict) or not portal.get("data"):
        die('brain.config.json has no portal.data. Add e.g. "portal": {"data": "docs/dashboard/hub-portal.json"} '
            "and create the file with scripts/init-data.py")
    out = (hub / portal.get("out", ".work/hub-portal")).resolve()
    specs_dir = (portal.get("specs_dir") or cfg.get("roadmap", {}).get("specs_dir")
                 or cfg.get("releases", {}).get("specs_dir"))
    if not specs_dir:
        die('no specs folder configured. Set portal.specs_dir (or roadmap.specs_dir), e.g. "docs/specs"')
    specs_dir = specs_dir.strip("/")
    tasks_cfg = portal.get("tasks")
    if tasks_cfg is not None and not (isinstance(tasks_cfg, dict) and tasks_cfg.get("dir") and tasks_cfg.get("key_regex")):
        die('portal.tasks needs "dir" and "key_regex", e.g. {"dir": "tasks", "key_regex": "^PROJ-\\\\d+$"}')
    source = portal.get("source") or {}
    if source and not all(source.get(k) for k in ("blob", "tree", "branch")):
        die('portal.source needs "blob", "tree" and "branch", e.g. {"blob": "https://github.com/org/hub/blob/main/", '
            '"tree": "https://github.com/org/hub/tree/main/", "branch": "main"}')
    calendar = portal.get("calendar")
    if calendar not in (None, "gregorian", "jalali"):
        die('portal.calendar must be "jalali", "gregorian" or absent')
    graph_out = hub / cfg.get("graph", {}).get("out", "graph/")
    brand_build = hub / cfg.get("design", {}).get("build", "brand")

    data = load_json(hub / portal["data"], "portal.data")
    for k in REQUIRED_DATA:
        if k not in data:
            err("the data file is missing key '%s' - see references/data-contract.md" % k)
    if errors:
        return finish()
    for where, text in _placeholders(data):
        err("the data file still has a TODO placeholder at %s: %s" % (where, text[:80]))

    # ── documents ──────────────────────────────────────────────────────
    branch = source.get("branch")
    if branch and not a.no_fetch and git(hub, "fetch", "--quiet", "origin", branch) is None:
        warn("could not fetch origin/%s; on-%s flags use the local copy" % (branch, branch))
    listing = git(hub, "ls-files", "-co", "--exclude-standard", "--", "*.md")
    if listing is None:
        die("the hub is not a git repository (git ls-files failed)")
    files = sorted(f for f in listing.split("\n") if f and f.split("/")[0] not in EXCLUDE_TOP | EXCLUDE_DOT)
    on_branch = set((git(hub, "ls-tree", "-r", "origin/" + branch, "--name-only") or "").split("\n")) if branch else set()

    priv = data["privacy"]
    withhold, allow = priv.get("withhold", {}), set(priv.get("allow", []))
    redact = [(re.compile(r["pattern"]), r["with"]) for r in priv.get("redact", [])]
    patterns = [(n, re.compile(p)) for n, p in DEFAULT_PATTERNS]
    patterns += [(x.get("name", "pattern"), re.compile(x["pattern"])) for x in priv.get("patterns", [])]
    for p in withhold:
        if p not in files:
            warn("privacy.withhold names a file that no longer exists: " + p)

    labels = data["library"].get("groupLabels", {})
    tasks_dir = tasks_cfg["dir"].strip("/") if tasks_cfg else None

    def place(p):
        """(group label, bundle, nesting base) for a hub-relative path."""
        parts = p.split("/")
        if len(parts) == 1:
            return labels.get("", "Core"), "core", ""
        if p.startswith(specs_dir + "/"):
            return labels.get(specs_dir, "Specs"), "specs", specs_dir
        if tasks_dir and p.startswith(tasks_dir + "/"):
            return labels.get(tasks_dir, "Tasks"), "core", tasks_dir
        if parts[0] == "docs":
            key = "docs/" + parts[1]
            return labels.get(key, humanize(parts[1])), "docs", key
        if parts[0] == ".claude":
            return labels.get(".claude", "Skills & agents"), "skills", ".claude/skills" if parts[1] == "skills" else ".claude"
        return labels.get(parts[0], humanize(parts[0])), "core", parts[0]

    index, bundles = [], {}
    for p in files:
        try:
            text = (hub / p).read_text(encoding="utf-8").replace("\r\n", "\n")
        except (OSError, UnicodeDecodeError) as e:
            warn("skipped %s (%s)" % (p, e.__class__.__name__))
            continue
        group, bundle, base = place(p)
        rest = p[len(base) + 1:] if base else p
        entry = {"p": p, "g": group, "t": title_of(p, text), "k": bundle,
                 "n": rest.split("/")[0] if "/" in rest else "", "m": p in on_branch}
        if p in withhold:
            entry["w"] = withhold[p]
            text = ""
        for rx, rep in redact:
            text = rx.sub(rep, text)
        for n, line in enumerate(text.split("\n"), 1):
            for kind, rx in patterns:
                for m in rx.finditer(line):
                    if m.group(0) not in allow:
                        err("%s in %s:%d (%s) - withhold the file, add a privacy.redact rule, or allow it "
                            "if it is a documented example" % (kind, p, n, m.group(0)[:24]))
        bundles.setdefault(bundle, {})[p] = text
        index.append(entry)
    by_path = {d["p"]: d for d in index}

    # ── specs ──────────────────────────────────────────────────────────
    sroot = hub / specs_dir
    keys = []
    if sroot.is_dir():
        for child in sorted(sroot.iterdir()):
            if child.is_dir() and any(d["p"].startswith("%s/%s/" % (specs_dir, child.name)) for d in index):
                keys.append((child.name, True))
            elif child.suffix == ".md" and child.name.lower() != "readme.md":
                keys.append((child.stem, False))
    else:
        warn("specs folder %s does not exist - the Specs tab is empty" % specs_dir)
    specs = []
    for key, is_dir in keys:
        if is_dir:
            prefix = "%s/%s/" % (specs_dir, key)
            docs = [[prefix + f, f[:-3]] for f in SPEC_FILES if prefix + f in by_path]
            docs = docs or [[d["p"], d["p"].rsplit("/", 1)[1][:-3]] for d in index if d["p"].startswith(prefix)][:3]
            main_doc = docs[0][0] if docs else None
        else:
            main_doc = "%s/%s.md" % (specs_dir, key)
            docs = [[main_doc, "open"]]
        s = data["specs"].get(key)
        if not s:
            name, note = key, "Not yet described on this page."
            if main_doc in by_path:
                name = re.sub(r"^(Feature Specification|Spec(ification)?)\s*:\s*", "", by_path[main_doc]["t"], flags=re.I)
                m = re.search(r"\*\*Status:\*\*\s*([^\n]+)", (hub / main_doc).read_text(encoding="utf-8"))
                if m:
                    note = "Status in the spec: " + clean_heading(m.group(1))
            warn("spec %s has no entry in the data file's specs - shown as 'spec' with a placeholder note" % key)
            s = {"name": name, "status": "spec", "note": note}
        if s.get("status") not in data["specStatus"]:
            err("spec %s has status '%s'; use one of: %s" % (key, s.get("status"), ", ".join(data["specStatus"])))
        specs.append({"key": key, "name": s["name"], "status": s["status"], "note": s.get("note", ""), "docs": docs})
    for key in data["specs"]:
        if key not in {k for k, _ in keys}:
            err("the data file's specs has '%s' but %s/ has no such spec - rename or remove it" % (key, specs_dir))

    # ── tasks ──────────────────────────────────────────────────────────
    tasks = []
    if tasks_cfg:
        troot, rx = hub / tasks_dir, re.compile(tasks_cfg["key_regex"])
        for child in sorted(troot.iterdir()) if troot.is_dir() else []:
            if not (child.is_dir() and rx.match(child.name)):
                continue
            prefix = "%s/%s/" % (tasks_dir, child.name)
            docs = [[prefix + f, f[:-3]] for f in TASK_FILES if prefix + f in by_path]
            note = data.get("tasks", {}).get(child.name)
            if not note:
                note = by_path[docs[0][0]]["t"] if docs else ""
                warn("task %s has no note in the data file's tasks - using its first document's title" % child.name)
            tasks.append({"key": child.name, "note": note, "docs": docs})
        for key in data.get("tasks", {}):
            if not (troot / key).is_dir():
                err("the data file's tasks has '%s' but %s/%s/ does not exist" % (key, tasks_dir, key))

    # ── constitution principles ────────────────────────────────────────
    rules = []
    const = hub / "constitution.md"
    if const.is_file():
        for m in re.finditer(r"^#{2,3}\s+(\d+)\s*(?:[.)]|[—–:-])\s*(.+)$", const.read_text(encoding="utf-8"), re.M):
            rules.append({"n": m.group(1), "title": clean_heading(m.group(2)),
                          "caveat": data.get("ruleCaveats", {}).get(m.group(1), "")})
        if not rules:
            warn("constitution.md has no numbered principle headings ('## 1. Title' or '### 1 — Title')")
    else:
        warn("constitution.md not found - the principles list is empty")
    for n in data.get("ruleCaveats", {}):
        if n not in {r["n"] for r in rules}:
            err("ruleCaveats has principle %s but constitution.md has no heading numbered %s" % (n, n))

    # ── graph ──────────────────────────────────────────────────────────
    graph = None
    report = graph_out / "sync-report.md"
    if report.is_file():
        rep = report.read_text(encoding="utf-8")
        nm = re.search(r"\*\*Graph:\*\*\s*([\d,]+) nodes,\s*([\d,]+) edges", rep)
        when = re.search(r"\*\*Last sync:\*\*\s*(.+)", rep)
        rows = re.findall(r"^\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|", rep, re.M)
        if nm:
            graph = {"nodes": int(nm.group(1).replace(",", "")), "edges": int(nm.group(2).replace(",", "")),
                     "synced": when.group(1).strip() if when else "unknown",
                     "built": "; ".join("%s on %s" % r for r in rows), "codeOnly": "code-only" in rep}
    else:
        warn("%s not found - run pb sync to show graph stats" % report.relative_to(hub).as_posix())

    # ── brand ramp (whatever primary steps this brand has) ─────────────
    ramp = []
    tokens = brand_build / "tokens.json"
    if tokens.is_file():
        tv = load_json(tokens, "brand tokens")
        names = tv.get("css_vars") or []
        names = list(names) if isinstance(names, (list, dict)) else []
        steps = sorted((int(m.group(1)), v) for v in names for m in [re.fullmatch(r"--ds-color-primary-(\d+)", v)] if m)
        ramp = [[str(n), "var(%s)" % v] for n, v in steps]

    # ── references ─────────────────────────────────────────────────────
    refs = [("flows", p) for f in data["flows"] for p in f.get("docs", [])]
    refs += [("skillGroups", i["path"]) for g in data["skillGroups"] for i in g["items"] if i.get("path")]
    refs += [("library.start", p) for p in data["library"].get("start", [])]
    refs += [("hub.map", r[2]) for r in data["hub"].get("map", []) if len(r) > 2 and r[2]]
    if data["brand"].get("designDoc"):
        refs.append(("brand.designDoc", data["brand"]["designDoc"]))
    for where, p in refs:
        if p not in by_path:
            err("%s points at %s, which is not a Markdown file in the hub" % (where, p))
    listed = {i.get("path") for g in data["skillGroups"] for i in g["items"]}
    for p in by_path:
        if re.match(r"^\.claude/(skills/[^/]+/SKILL\.md|agents/[^/]+\.md|commands/[^/]+\.md)$", p) and p not in listed:
            warn("%s is not on the Skills tab - add it to the data file's skillGroups" % p)
    ids = [x["id"] for x in data["artifacts"]]
    for i in sorted({i for i in ids if ids.count(i) > 1}):
        err("artifact %s is listed twice" % i)
    for x in data["artifacts"]:
        if x.get("group") not in data["artifactGroups"]:
            err("artifact '%s' has group '%s', which is not in artifactGroups" % (x.get("title"), x.get("group")))
        if x.get("src") and not (hub / x["src"]).exists():
            warn("artifact '%s' names src %s, which does not exist" % (x["title"], x["src"]))
    try:
        as_of = dt.date.fromisoformat(data["asOf"])
    except ValueError:
        if "TODO" not in data["asOf"]:
            err("asOf must be an ISO date (YYYY-MM-DD), got %r" % data["asOf"])
        as_of = dt.date.today()
    if (dt.date.today() - as_of).days > 7:
        warn("asOf is %s, %d days old - refresh the status section" % (data["asOf"], (dt.date.today() - as_of).days))
    if errors:
        return finish()

    local = ""
    if calendar == "jalali":
        jy, jm, jd = to_jalali(as_of.year, as_of.month, as_of.day)
        local = ("%d %s %d" % (jd, JALALI_MONTHS[jm - 1], jy)).translate(FA_DIGITS)
    host = source.get("blob", "")
    auto = {
        "asOfLabel": "%s %d %s" % (as_of.strftime("%a"), as_of.day, as_of.strftime("%b %Y")),
        "asOfLocal": local,
        "built": "%d %s" % (dt.date.today().day, dt.date.today().strftime("%b %Y")),
        "branch": (git(hub, "rev-parse", "--abbrev-ref", "HEAD") or "unknown").strip(),
        "source": {"blob": source.get("blob"), "tree": source.get("tree"), "branch": branch,
                   "label": "GitHub" if "github" in host else "GitLab" if "gitlab" in host else "the repo"} if source else None,
        "specs": specs, "tasks": tasks if tasks_cfg else None, "rules": rules, "graph": graph, "ramp": ramp,
        "bundles": sorted(bundles), "withheld": sum(1 for d in index if d.get("w")),
    }

    # ── write ──────────────────────────────────────────────────────────
    (out / "md").mkdir(parents=True, exist_ok=True)
    for f in (out / "md").glob("*.json"):
        if f.stem not in bundles:
            f.unlink()
    for b, docs in bundles.items():
        (out / "md" / (b + ".json")).write_text(json.dumps(docs, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    def js(v):
        return json.dumps(v, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

    page = TEMPLATE.read_text(encoding="utf-8")
    page = (page.replace("__TITLE__", html.escape(data["title"]))
                .replace("__DESCRIPTION__", html.escape(data.get("description", ""), quote=True))
                .replace("/*__DOCS__*/[]", js(index)).replace("/*__DATA__*/{}", js(data))
                .replace("/*__AUTO__*/{}", js(auto)))
    page_path = out / "index.html"
    page_path.write_text(page, encoding="utf-8", newline="\n")

    if a.no_brand:
        warn("--no-brand: the brand was not inlined or checked - do not publish this build")
    elif not (BRAND_SCRIPTS / "check-brand.py").is_file():
        err("brand-system scripts not found at %s - this skill must sit beside brand-system" % BRAND_SCRIPTS)
    else:
        for cmd in (["brand.py", "--hub", str(hub), "inline", str(page_path)],
                    ["check-brand.py", "--hub", str(hub), str(page_path)]):
            r = subprocess.run([sys.executable, str(BRAND_SCRIPTS / cmd[0]), *cmd[1:]],
                               capture_output=True, text=True, encoding="utf-8")
            if r.returncode != 0:
                err("%s failed:\n%s%s" % (cmd[0], r.stdout, r.stderr))
                break
    summary = "%d documents (%d withheld), %d specs, %s, %d artifacts" % (
        len(index), auto["withheld"], len(specs), "%d tasks" % len(tasks) if tasks_cfg else "no tasks folder",
        len(data["artifacts"]))
    files = {"md/%s.json" % b: str(out / "md" / (b + ".json")) for b in sorted(bundles)}
    call = {"file_path": str(page_path), "files": files}
    if data.get("artifact_url"):
        call["url"] = data["artifact_url"]
    else:
        call["icon"] = "library"
    return finish(page_path, summary, call)


def _placeholders(v, where="data"):
    if isinstance(v, dict):
        for k, x in v.items():
            yield from _placeholders(x, "%s.%s" % (where, k))
    elif isinstance(v, list):
        for i, x in enumerate(v):
            yield from _placeholders(x, "%s[%d]" % (where, i))
    elif isinstance(v, str) and "TODO" in v:
        yield where, v


def finish(page_path=None, summary="", call=None):
    for w in warns:
        print("WARN  " + w)
    for e in errors:
        print("ERROR " + e)
    if errors:
        print("\nBuild FAILED: %d error(s). Fix them in the data file or the hub, then re-run." % len(errors))
        return 1
    print("\nBuilt %s\n%s" % (page_path, summary))
    if "url" not in call:
        print("\nFirst publish: no artifact_url in the data file yet. Publish, then write the new URL into it.")
    print("\nPublish with the Artifact tool:")
    print(json.dumps(call, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
