#!/usr/bin/env python3
"""Collect the git facts an epic-approval review is grounded in.

Two subcommands, both read-only (they never fetch, create branches, check out, merge or push):

  plan   One release branch name shared by every repo (back end and front end always ship the
         same version). With --branch, that name. Otherwise an open (unmerged, newer) release
         branch, or the next version: the highest release that reached production in any repo
         (release-branch merges into it — release branches are usually deleted after merging;
         tags are never read), bumped by the strongest commit type waiting on any repo's integration branch
         (breaking -> major, feat -> minor, otherwise patch). A proposed name is always
         release.X.Y.Z; old names (release-5-5) are still read as versions. Then, per repo,
         whether that branch exists, must be created, or has nothing new.

  facts  For one repo: exactly what merging the release into the production branch would bring
         — the pinned range, commits with their parsed commit-message fields, ticket keys, every
         changed file sorted into risk categories, env vars newly read, production commits the
         release lacks, and whether the merge conflicts.

Inside a Product Brain hub (a parent folder holds brain.config.json) repos come from `repos[]`
and branch names from `releases.*`; outside one, pass --path. Keys read, all optional:

  releases.production_branch    default "main"
  releases.integration_branch   default "develop"
  releases.release_branch_regex default "^release[-/._]"
  approvals.out                 where reports go (printed by plan; the skill writes there)

    gather-epic-facts.py plan  [--hub DIR | --path REPO] [--repo ID ...] [--branch NAME]
    gather-epic-facts.py facts [--hub DIR | --path REPO] --repo ID --head REF [--out FILE]

Exit codes: 0 ok, 2 something must be decided by a person (the message says what), 1 error.
"""

import sys

sys.dont_write_bytecode = True

import argparse
import json
import re
import subprocess
from datetime import date
from pathlib import Path

DEFAULTS = {
    "releases.production_branch": "main",
    "releases.integration_branch": "develop",
    "releases.release_branch_regex": r"^release[-/._]",
    "approvals.out": None,
}
TICKET_RE = re.compile(r"\b([A-Z][A-Z0-9]+-[0-9]+)\b")
# type(scope)!: [TICKET] description — the git-workflow commit rule, plus the conventional "!".
COMMIT_RE = re.compile(
    r"^(?P<type>[a-z]+)(?:\((?P<scope>[^)]*)\))?(?P<breaking>!)?: (?:\[(?P<ticket>[A-Z][A-Z0-9]*-[0-9]+)\] )?(?P<desc>.+)$"
)
KNOWN_TYPES = {"feat", "fix", "bug", "refactor", "perf", "test", "docs", "style", "chore", "ci", "build", "revert"}
# Old names use any separator (release-5-5, release/1.4, release_2.3); new ones are always semantic.
VERSION_RE = re.compile(r"(\d+(?:[._-]\d+){0,3})")
SEMVER_PREFIX = "release."
SEMVER_BRANCH_RE = re.compile(r"^release\.\d+\.\d+\.\d+$")

# Path heuristics, stack-agnostic. A file may land in several categories.
CATEGORIES = {
    "migrations": [
        r"(^|/)(database/)?migrations?/", r"(^|/)db/migrate/", r"(^|/)alembic/versions/",
        r"(^|/)DoctrineMigrations/", r"\.sql$",
    ],
    "dependencies": [
        r"(^|/)(package\.json|package-lock\.json|yarn\.lock|pnpm-lock\.yaml|composer\.json|composer\.lock"
        r"|pubspec\.yaml|pubspec\.lock|requirements[^/]*\.txt|pyproject\.toml|poetry\.lock|Pipfile(\.lock)?"
        r"|go\.mod|go\.sum|Gemfile(\.lock)?|Cargo\.(toml|lock)|build\.gradle(\.kts)?|pom\.xml|Podfile(\.lock)?)$",
    ],
    "env": [r"(^|/)\.env(\.[^/]+)?$", r"(^|/)environments?/[^/]+$"],
    "config": [
        r"(^|/)config/", r"(^|/)conf/", r"(^|/)settings[^/]*\.(py|json|ya?ml)$",
        r"(^|/)application[^/]*\.(ya?ml|properties)$", r"(^|/)(angular|nx|firebase|app)\.json$",
        r"(^|/)services\.ya?ml$", r"(^|/)(AndroidManifest\.xml|Info\.plist)$",
    ],
    "ci": [
        r"(^|/)\.gitlab-ci\.ya?ml$", r"(^|/)\.gitlab/", r"(^|/)\.github/workflows/", r"(^|/)Jenkinsfile$",
        r"(^|/)bitbucket-pipelines\.ya?ml$", r"(^|/)\.circleci/", r"(^|/)azure-pipelines\.ya?ml$",
    ],
    "infra": [
        r"(^|/)Dockerfile[^/]*$", r"(^|/)docker-compose[^/]*\.ya?ml$", r"(^|/)(k8s|kubernetes|helm|charts|deploy|"
        r"terraform|ansible|infra)/", r"\.tf$", r"(^|/)nginx[^/]*\.conf$", r"(^|/)Procfile$", r"(^|/)supervisor",
    ],
    "api": [
        r"(^|/)routes?/", r"routes?\.(php|ts|js|py|ya?ml)$", r"(^|/)(openapi|swagger)[^/]*\.(ya?ml|json)$",
        r"\.(graphql|gql|proto)$", r"Controller[^/]*\.(php|ts|js|java|kt|cs)$", r"(^|/)controllers?/",
        r"(^|/)(api|endpoints|resolvers)/",
    ],
    "security_sensitive": [
        r"(auth|login|logout|password|passwd|permission|policy|policies|guard|middleware|security|crypt|"
        r"token|session|csrf|cors|oauth|jwt|(^|[/_.-])acl|role|firewall|voter|sanitiz|upload)",
    ],
    "jobs": [r"(^|/)(jobs?|queues?|workers?|listeners?|consumers?|schedul|cron|commands?|messenger)[^/]*/?"],
    "tests": [
        r"(^|/)(tests?|__tests__|spec|integration_test|e2e)/", r"\.(spec|test)\.[^/]+$", r"_test\.[^/]+$",
        r"Test\.(php|java|kt|cs)$",
    ],
    "docs": [r"\.(md|rst|adoc)$", r"(^|/)docs?/"],
}
COMPILED = {k: [re.compile(p, re.I) for p in v] for k, v in CATEGORIES.items()}

# Environment variables read by code, in the syntaxes of the stacks the shared plugins cover.
ENV_READ_RES = [
    re.compile(r"""\benv\(\s*['"]([A-Z][A-Z0-9_]*)['"]"""),  # Laravel
    re.compile(r"""\bgetenv\(\s*['"]([A-Z][A-Z0-9_]*)['"]"""),
    re.compile(r"""\bprocess\.env\.([A-Z][A-Z0-9_]*)"""),
    re.compile(r"""\bprocess\.env\[\s*['"]([A-Z][A-Z0-9_]*)['"]"""),
    re.compile(r"""\bimport\.meta\.env\.([A-Z][A-Z0-9_]*)"""),
    re.compile(r"""\$_(?:ENV|SERVER)\[\s*['"]([A-Z][A-Z0-9_]*)['"]"""),
    re.compile(r"""%env\((?:[a-z]+:)*([A-Z][A-Z0-9_]*)\)%"""),  # Symfony
    re.compile(r"""\bos\.environ(?:\.get)?[\[(]\s*['"]([A-Z][A-Z0-9_]*)['"]"""),
    re.compile(r"""\bos\.getenv\(\s*['"]([A-Z][A-Z0-9_]*)['"]"""),
    re.compile(r"""\bfromEnvironment\(\s*['"]([A-Z][A-Z0-9_]*)['"]"""),  # Dart
    re.compile(r"""\bPlatform\.environment\[\s*['"]([A-Z][A-Z0-9_]*)['"]"""),
]
ENV_FILE_KEY_RE = re.compile(r"^\s*(?:export\s+)?([A-Z][A-Z0-9_]*)\s*=")


class Decide(Exception):
    """Something a person has to choose; exit 2 with the message."""


# ------------------------------------------------------------------------------------ plumbing

def git(repo, *args, check=True):
    proc = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if check and proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {proc.stderr.strip()}")
    return proc


def ref_exists(repo, ref):
    return git(repo, "rev-parse", "--verify", "--quiet", ref + "^{commit}", check=False).returncode == 0


def pick_ref(repo, name, remote="origin"):
    """Prefer the remote-tracking ref: it is what the merge request will actually merge."""
    for ref in ([name] if name.startswith(remote + "/") else [f"{remote}/{name}", name]):
        if ref_exists(repo, ref):
            return ref
    return None


def find_hub(explicit):
    if explicit:
        hub = Path(explicit).resolve()
        if not (hub / "brain.config.json").is_file():
            raise RuntimeError(f"--hub {explicit}: no brain.config.json there")
        return hub
    for folder in (Path.cwd().resolve(), *Path.cwd().resolve().parents):
        if (folder / "brain.config.json").is_file():
            return folder
    return None


class Workspace:
    """Repos and branch conventions, from the hub's brain.config.json or from --path alone."""

    def __init__(self, hub, path):
        self.hub, self.cfg, self.defaulted = hub, {}, []
        if hub:
            try:
                self.cfg = json.loads((hub / "brain.config.json").read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                raise RuntimeError(f"brain.config.json: invalid JSON at line {e.lineno}: {e.msg}")
        self.single = Path(path).resolve() if path else None

    def get(self, dotted):
        node = self.cfg
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                if dotted not in self.defaulted:
                    self.defaulted.append(dotted)
                return DEFAULTS[dotted]
            node = node[part]
        return node

    def repos(self):
        """[(id, path)] — `repos[].path`, else `<workspace.repos_dir>/<id>`, else `repos/<id>`."""
        if self.single:
            return [(self.single.name, self.single)]
        if not self.hub:
            raise RuntimeError("no Product Brain hub here (no brain.config.json above this folder); "
                               "run inside the hub, or pass --hub DIR or --path REPO")
        base = (self.cfg.get("workspace") or {}).get("repos_dir") or "repos"
        out = []
        for r in self.cfg.get("repos") or []:
            if isinstance(r, dict) and r.get("id"):
                out.append((r["id"], self.hub / (r.get("path") or f"{base}/{r['id']}")))
        return out

    def repo(self, repo_id):
        for rid, path in self.repos():
            if rid == repo_id or (self.single and repo_id in (None, rid)):
                return rid, path
        raise Decide(f"repo '{repo_id}' is not in brain.config.json repos: "
                     + ", ".join(r for r, _ in self.repos()))

    def approvals_dir(self):
        out = self.get("approvals.out")
        return str(self.hub / out) if (self.hub and out) else None


def repo_kind(path, cfg_repo=None):
    """backend / frontend / mobile / fullstack, from `repos[].kind` or the files at the root."""
    if cfg_repo and cfg_repo.get("kind"):
        return cfg_repo["kind"]
    p = Path(path)
    backend = any((p / f).exists() for f in ("artisan", "composer.json", "symfony.lock", "go.mod", "pom.xml",
                                             "manage.py", "requirements.txt", "pyproject.toml", "Gemfile"))
    mobile = (p / "pubspec.yaml").exists()
    web = (p / "angular.json").exists() or (p / "nx.json").exists()
    pkg = p / "package.json"
    if pkg.exists():
        try:
            deps = json.loads(pkg.read_text(encoding="utf-8"))
            names = set((deps.get("dependencies") or {}).keys()) | set((deps.get("devDependencies") or {}).keys())
            web = web or bool(names & {"react", "vue", "@angular/core", "next", "nuxt", "svelte", "vite",
                                       "@inertiajs/react", "@inertiajs/vue3"})
            backend = backend or bool(names & {"express", "@nestjs/core", "fastify", "koa"})
        except (json.JSONDecodeError, OSError):
            pass
    if mobile:
        return "mobile"
    if backend and web:
        return "fullstack"
    return "backend" if backend else ("frontend" if web else "unknown")


# ------------------------------------------------------------------------------------ versions

def parse_version(text):
    m = VERSION_RE.search(text)
    return tuple(int(x) for x in re.split(r"[._-]", m.group(1))) if m else None


def fmt_version(parts):
    return ".".join(str(x) for x in parts)


def bump(version, level):
    parts = list(version) + [0] * (3 - len(version))
    i = {"major": 0, "minor": 1, "patch": 2}[level]
    parts[i] += 1
    for j in range(i + 1, len(parts)):
        parts[j] = 0
    return tuple(parts[:max(len(version), i + 1)])


def parse_commit(subject, body):
    m = COMMIT_RE.match(subject)
    tickets = sorted(set(TICKET_RE.findall(subject + "\n" + body)))
    if not m:
        return {"format_ok": False, "type": None, "scope": None, "ticket": None, "breaking": False,
                "tickets": tickets, "problem": "subject is not `type(scope): [TICKET] description`"}
    problems = []
    if m.group("type") not in KNOWN_TYPES:
        problems.append(f"unknown type '{m.group('type')}'")
    if not m.group("ticket"):
        problems.append("no [TICKET] after `type(scope):`")
    return {
        "format_ok": not problems, "type": m.group("type"), "scope": m.group("scope"), "ticket": m.group("ticket"),
        "breaking": bool(m.group("breaking")) or "BREAKING CHANGE" in body, "tickets": tickets,
        "problem": "; ".join(problems) or None,
    }


def commits(repo, rng, merges=False):
    fmt = "%H%x1f%an%x1f%ad%x1f%s%x1f%b%x1e"
    out = []
    for rec in git(repo, "log", "--merges" if merges else "--no-merges", "--date=short", f"--format={fmt}", rng).stdout.split("\x1e"):
        rec = rec.strip("\n")
        if not rec:
            continue
        sha, author, day, subject, body = (rec.split("\x1f") + [""] * 5)[:5]
        c = {"sha": sha[:12], "author": author, "date": day, "subject": subject}
        c.update(parse_commit(subject, body))
        out.append(c)
    return out


def bump_level(work):
    if any(c["breaking"] for c in work):
        return "major", "a commit is marked breaking (`!` or BREAKING CHANGE)"
    if any(c["type"] == "feat" for c in work):
        return "minor", "feat commits present"
    return "patch", "only fix / chore / other commits"


def release_branches(repo, branch_re):
    """(release branch names that count, local-only ones ignored).

    With an origin remote, only origin's branches count: a local branch that is not on origin is
    a leftover (deleted on the server, or never pushed), not a release. Without a remote, local
    branches are all there is."""
    remote = "origin" in git(repo, "remote").stdout.split()
    origin = {r[len("origin/"):] for r in git(repo, "for-each-ref", "--format=%(refname:short)",
                                             "refs/remotes/origin").stdout.split() if r != "origin/HEAD" and r != "origin"}
    local = set(git(repo, "for-each-ref", "--format=%(refname:short)", "refs/heads").stdout.split())
    names = origin if remote else local
    ignored = sorted(n for n in local - origin if branch_re.search(n)) if remote else []
    return sorted(n for n in names if branch_re.search(n)), ignored


# The source branch of a merge commit: git / GitLab, GitHub, and merges of a remote-tracking ref.
MERGE_SOURCE_RES = [
    re.compile(r"^Merge branch '([^']+)'"),
    re.compile(r"^Merge pull request #\d+ from [^/\s]+/(\S+)"),
    re.compile(r"^Merge remote-tracking branch '(?:[^/']+/)?([^']+)'"),
]


def vkey(v):
    return tuple(v) + (0,) * (4 - len(v))


def shipped_release(repo, prod, branch_re):
    """The highest release version that has reached production, and every one seen.

    Tags are deliberately not read: a team's tag scheme need not follow its release names.
    Release branches are usually deleted once merged, so they are read from what stays on
    production: merge commits of a release branch into it (first parent only, so merges into
    other branches do not count), plus release branches still on origin that are already merged.
    When the history disagrees — releases merged out of order, a hotfix merged after a newer
    release — the highest version wins, never the most recent merge."""
    found = {}
    for subject in git(repo, "log", prod, "--first-parent", "--merges", "--format=%s").stdout.splitlines():
        for rx in MERGE_SOURCE_RES:
            m = rx.match(subject)
            if m and branch_re.search(m.group(1)):
                v = parse_version(branch_re.sub("", m.group(1), count=1))
                if v:
                    found.setdefault(m.group(1), (v, "merge into " + prod.split("/")[-1]))
                break
    for name in release_branches(repo, branch_re)[0]:
        ref = pick_ref(repo, name)
        v = parse_version(branch_re.sub("", name, count=1))
        if v and name not in found and git(repo, "merge-base", "--is-ancestor", ref, prod, check=False).returncode == 0:
            found[name] = (v, "branch merged")
    if not found:
        return None
    ranked = sorted(found.items(), key=lambda kv: vkey(kv[1][0]), reverse=True)
    name, (v, source) = ranked[0]
    return {"name": name, "version": fmt_version(v), "source": source, "_v": v,
            "seen": [n for n, _ in ranked[:8]]}


def open_release(repo, prod, branch_re, shipped):
    """The highest release branch on origin that is not merged into production and is newer than
    what shipped. Older unmerged branches are abandoned, not open."""
    best = None
    for name in release_branches(repo, branch_re)[0]:
        v = parse_version(branch_re.sub("", name, count=1))
        if not v or (shipped and vkey(v) <= vkey(shipped["_v"])):
            continue
        if git(repo, "merge-base", "--is-ancestor", pick_ref(repo, name), prod, check=False).returncode != 0:
            if best is None or vkey(v) > vkey(best[0]):
                best = (v, name)
    return best[1] if best else None


# ------------------------------------------------------------------------------------ plan

LEVELS = ["patch", "minor", "major"]


def pad3(v):
    return tuple(v) + (0,) * (3 - len(v))


def plan(ws, repo_ids, branch):
    """One release name for every repo: back end and front end always ship the same version."""
    prod_name, integ_name = ws.get("releases.production_branch"), ws.get("releases.integration_branch")
    branch_re = re.compile(ws.get("releases.release_branch_regex"))
    cfg_repos = {r.get("id"): r for r in (ws.cfg.get("repos") or []) if isinstance(r, dict)}
    targets = [ws.repo(r) for r in repo_ids] if repo_ids else ws.repos()
    rows, usable, warnings = [], [], []

    # Pass 1: what each repo has — latest release, an open (unmerged) release branch, pending work.
    for rid, path in targets:
        row = {"repo": rid, "path": str(path), "kind": None, "production": None, "integration": None}
        rows.append(row)
        if not (Path(path) / ".git").exists():
            row["status"], row["action"] = "not cloned", "run `pb sync` to clone it, or skip this repo"
            continue
        row["kind"] = repo_kind(path, cfg_repos.get(rid))
        prod, integ = pick_ref(path, prod_name), pick_ref(path, integ_name)
        row["production"], row["integration"] = prod, integ
        if not prod:
            row["status"], row["action"] = "no production branch", f"'{prod_name}' not found; set releases.production_branch"
            continue
        if not integ:
            row["status"], row["action"] = "no integration branch", f"'{integ_name}' not found; set releases.integration_branch"
            continue
        latest = shipped_release(path, prod, branch_re)
        row["latest_release"] = {k: v for k, v in latest.items() if k != "_v"} if latest else None
        row["_latest"] = latest
        opened = open_release(path, prod, branch_re, latest)
        if opened:
            row["open_release"] = opened
        mb = git(path, "merge-base", prod, integ).stdout.strip()
        pending = commits(path, f"{mb}..{integ}")
        row["pending_commits"] = len(pending)
        if pending:
            row["bump"], row["bump_reason"] = bump_level(pending)
        ignored = release_branches(path, branch_re)[1]
        if ignored:
            warnings.append(f"{rid}: local release branches not on origin were ignored: {', '.join(ignored)} "
                            "(deleted on the server or never pushed; `git branch -D <name>` removes a stale one)")
        usable.append(row)

    # One shared name.
    release = {"branch": None, "version": None, "source": None, "bump": None, "bump_reason": None,
               "based_on": None, "needs_decision": None}
    latests = [r["_latest"] for r in usable if r.get("_latest")]
    if len({pad3(l["_v"]) for l in latests}) > 1:
        warnings.append("repos are on different release versions: "
                        + ", ".join(f"{r['repo']} {r['_latest']['version']}" for r in usable if r.get("_latest"))
                        + " — the shared version brings them into step")
    opens = sorted({r["open_release"] for r in usable if r.get("open_release")})
    if branch:
        release.update(branch=branch, source="named")
    elif opens:
        pick = max(opens, key=lambda n: pad3(parse_version(branch_re.sub("", n, count=1)) or (0,)))
        release.update(branch=pick, source="open release")
        if len(opens) > 1:
            release["needs_decision"] = ("different open release branches: " + ", ".join(
                f"{r['repo']} {r['open_release']}" for r in usable if r.get("open_release"))
                + f" — confirm '{pick}' for every repo, or pass --branch")
    else:
        levels = [(r["bump"], r["repo"], r["bump_reason"]) for r in usable if r.get("bump")]
        if not levels:
            release["needs_decision"] = f"no repo has commits on {integ_name} that {prod_name} lacks — nothing to release"
        elif not latests:
            release["needs_decision"] = "no release branch or tag in any repo to version from — ask for the first version, then pass --branch"
        else:
            base = max(latests, key=lambda l: vkey(l["_v"]))
            level = max(levels, key=lambda x: LEVELS.index(x[0]))
            version = fmt_version(bump(pad3(base["_v"]), level[0]))
            release.update(branch=SEMVER_PREFIX + version, source="proposed", bump=level[0],
                           bump_reason=f"{level[2]} in {level[1]}",
                           based_on={"name": base["name"], "version": base["version"]})
    # A branch this skill creates is always named release.X.Y.Z; an existing one is reviewed as it is.
    if release["branch"] and not SEMVER_BRANCH_RE.match(release["branch"]) and not release["needs_decision"]:
        v = parse_version(branch_re.sub("", release["branch"], count=1))
        suggestion = SEMVER_PREFIX + fmt_version(pad3(v)) if v else SEMVER_PREFIX + "X.Y.Z"
        missing = [r["repo"] for r in usable if not pick_ref(r["path"], release["branch"])]
        if missing:
            release["needs_decision"] = (
                f"'{release['branch']}' is not a semantic release name and would have to be created in "
                + ", ".join(missing) + f" — new release branches are named release.X.Y.Z; "
                f"use '{suggestion}' (pass --branch {suggestion}) or confirm the existing name")
            release["suggested_branch"] = suggestion
    if release["branch"]:
        release["version"] = fmt_version(parse_version(branch_re.sub("", release["branch"], count=1)) or ()) or None

    # Pass 2: what that one name means in each repo.
    name = release["branch"]
    for row in usable:
        row.pop("_latest", None)
        if not name:
            row["status"], row["action"] = "undecided", "see release.needs_decision"
            continue
        ref = pick_ref(row["path"], name)
        row["branch"], row["branch_ref"] = name, ref
        if ref and git(row["path"], "merge-base", "--is-ancestor", ref, row["production"], check=False).returncode == 0 \
                and git(row["path"], "rev-parse", ref).stdout != git(row["path"], "rev-parse", row["production"]).stdout:
            row["status"], row["action"] = "already merged", f"'{name}' is already in {prod_name} — pick another version"
            row["review_ref"] = None
        elif ref:
            row["status"], row["action"], row["review_ref"] = "exists", "review it", ref
        elif row.get("pending_commits") or release["source"] == "named":
            row["status"], row["action"], row["review_ref"] = "create", f"create '{name}' from {row['integration']} (ask first)", row["integration"]
        else:
            row["status"], row["review_ref"] = "nothing to release", row["integration"]
            row["action"] = f"no new commits — create '{name}' anyway to keep versions in step, or skip"
    for row in rows:
        row.pop("_latest", None)
    return {
        "hub": str(ws.hub) if ws.hub else None,
        "approvals_out": ws.approvals_dir(),
        "production_branch": prod_name, "integration_branch": integ_name,
        "release": release, "warnings": warnings,
        "defaulted_keys": ws.defaulted, "date": date.today().isoformat(), "repos": rows,
    }


# ------------------------------------------------------------------------------------ facts

def categorize(path):
    return [cat for cat, pats in COMPILED.items() if any(p.search(path) for p in pats)]


def changed_files(repo, mb, head_sha):
    """name-status and numstat, rename-aware, NUL-separated so odd paths survive."""
    status_raw = git(repo, "diff", "-z", "-M", "--name-status", mb, head_sha).stdout.split("\0")
    files, i = {}, 0
    while i < len(status_raw) and status_raw[i]:
        code = status_raw[i]
        if code[0] in "RC":
            files[status_raw[i + 2]] = {"path": status_raw[i + 2], "status": code[0], "old_path": status_raw[i + 1]}
            i += 3
        else:
            files[status_raw[i + 1]] = {"path": status_raw[i + 1], "status": code[0]}
            i += 2
    num_raw = git(repo, "diff", "-z", "-M", "--numstat", mb, head_sha).stdout.split("\0")
    i = 0
    while i < len(num_raw) and num_raw[i]:
        added, deleted, path = num_raw[i].split("\t", 2)
        if path == "":  # rename: old and new follow as separate fields
            path, i = num_raw[i + 2], i + 3
        else:
            i += 1
        entry = files.setdefault(path, {"path": path, "status": "M"})
        entry["binary"] = added == "-"
        entry["added"] = 0 if added == "-" else int(added)
        entry["deleted"] = 0 if deleted == "-" else int(deleted)
    out = []
    for entry in files.values():
        entry.setdefault("added", 0)
        entry.setdefault("deleted", 0)
        entry["categories"] = categorize(entry["path"])
        out.append(entry)
    return sorted(out, key=lambda f: f["path"])


def env_vars(repo, mb, head_sha):
    """Env var names that appear in added lines but not in removed ones: newly read or newly set."""
    diff = git(repo, "diff", "-U0", "--no-color", mb, head_sha).stdout
    added, removed, in_env_file, current = {}, set(), False, None
    for line in diff.splitlines():
        if line.startswith("+++ "):
            current = line[6:] if line.startswith("+++ b/") else None
            in_env_file = bool(current and COMPILED["env"][0].search(current))
            continue
        if line.startswith("--- ") or not current or line[:1] not in "+-":
            continue
        sign, body = line[:1], line[1:]
        names = {m.group(1) for rx in ENV_READ_RES for m in rx.finditer(body)}
        if in_env_file:
            m = ENV_FILE_KEY_RE.match(body)
            if m:
                names.add(m.group(1))
        for n in names:
            if sign == "+":
                added.setdefault(n, set()).add(current)
            else:
                removed.add(n)
    return [{"name": n, "files": sorted(fs)} for n, fs in sorted(added.items()) if n not in removed]


def merge_check(repo, base_sha, head_sha):
    proc = git(repo, "merge-tree", "--write-tree", "--name-only", "--no-messages", base_sha, head_sha, check=False)
    if proc.returncode == 0:
        return {"status": "clean", "conflicts": []}
    if proc.returncode == 1:
        return {"status": "conflicts", "conflicts": [p for p in proc.stdout.splitlines()[1:] if p]}
    return {"status": "unknown", "conflicts": [], "reason": "git merge-tree --write-tree needs git >= 2.38"}


def facts(ws, repo_id, head):
    rid, path = ws.repo(repo_id)
    cfg_repos = {r.get("id"): r for r in (ws.cfg.get("repos") or []) if isinstance(r, dict)}
    base_ref = pick_ref(path, ws.get("releases.production_branch"))
    head_ref = pick_ref(path, head)
    if not base_ref:
        raise Decide(f"{rid}: production branch '{ws.get('releases.production_branch')}' not found")
    if not head_ref:
        raise Decide(f"{rid}: '{head}' not found (tried origin/{head} and {head})")
    head_sha = git(path, "rev-parse", head_ref).stdout.strip()
    base_sha = git(path, "rev-parse", base_ref).stdout.strip()
    mb = git(path, "merge-base", base_sha, head_sha).stdout.strip()
    warnings = []
    local = head_ref[len("origin/"):] if head_ref.startswith("origin/") else None
    if local and ref_exists(path, local):
        local_sha = git(path, "rev-parse", local).stdout.strip()
        if local_sha != head_sha:
            warnings.append(f"local '{local}' ({local_sha[:12]}) differs from {head_ref} ({head_sha[:12]}); "
                            "facts describe the remote branch — push or pull first if that is not intended")
    if not head_ref.startswith("origin/"):
        warnings.append(f"{head_ref} is not on origin yet; facts describe the local branch")

    files = changed_files(path, mb, head_sha)
    work = commits(path, f"{mb}..{head_sha}")
    tickets = {}
    for c in work:
        for t in c["tickets"]:
            tickets[t] = tickets.get(t, 0) + 1
    by_cat = {cat: [f["path"] for f in files if cat in f["categories"]] for cat in CATEGORIES}
    by_cat["uncategorized"] = [f["path"] for f in files if not f["categories"]]
    types = {}
    for c in work:
        types[c["type"] or "(unparsed)"] = types.get(c["type"] or "(unparsed)", 0) + 1
    if not files:
        warnings.append("the release brings no changes into the production branch")

    return {
        "repo": rid, "path": str(path), "kind": repo_kind(path, cfg_repos.get(rid)),
        "head": {"ref": head_ref, "sha": head_sha},
        "base": {"ref": base_ref, "sha": base_sha},
        "merge_base": mb,
        "range": f"{mb}..{head_sha}",
        "totals": {
            "commits": len(work), "merge_commits": len(commits(path, f"{mb}..{head_sha}", merges=True)),
            "files": len(files), "added": sum(f["added"] for f in files), "deleted": sum(f["deleted"] for f in files),
        },
        "commit_types": dict(sorted(types.items())),
        "bump": bump_level(work)[0] if work else None,
        "tickets": dict(sorted(tickets.items())),
        "malformed_commits": [c for c in work if not c["format_ok"]],
        "commits_without_ticket": [c for c in work if not c["tickets"]],
        "commits": work,
        "files": files,
        "by_category": by_cat,
        "deleted_files": [f["path"] for f in files if f["status"] == "D"],
        "renamed_files": [{"from": f["old_path"], "to": f["path"]} for f in files if f["status"] == "R"],
        "new_env_vars": env_vars(path, mb, head_sha),
        "base_commits_missing_from_release": commits(path, f"{head_sha}..{base_sha}"),
        "merge": merge_check(path, base_sha, head_sha),
        "warnings": warnings,
    }


# ------------------------------------------------------------------------------------ main

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--hub", help="hub folder (default: walk up from the current directory)")
    ap.add_argument("--path", help="a single repo, outside any hub")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan", help="find or propose the release branch per repo")
    p.add_argument("--repo", action="append", help="repo id (repeatable; default: every repo)")
    p.add_argument("--branch", help="release branch the user named")
    f = sub.add_parser("facts", help="facts for one repo's release")
    f.add_argument("--repo", help="repo id (optional with --path)")
    f.add_argument("--head", required=True, help="the release branch (or integration branch) to review")
    f.add_argument("--out", help="write the JSON here instead of stdout")
    args = ap.parse_args()

    try:
        ws = Workspace(None if args.path else find_hub(args.hub), args.path)
        if args.cmd == "plan":
            result = plan(ws, args.repo, args.branch)
        else:
            if not args.repo and not ws.single:
                raise Decide("facts needs --repo inside a hub: " + ", ".join(r for r, _ in ws.repos()))
            result = facts(ws, args.repo, args.head)
    except Decide as e:
        print(f"epic-approval: {e}", file=sys.stderr)
        return 2
    except RuntimeError as e:
        print(f"epic-approval: {e}", file=sys.stderr)
        return 1

    text = json.dumps(result, indent=2, ensure_ascii=False)
    if args.cmd == "facts" and args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        t = result["totals"]
        print(f"{result['repo']} ({result['kind']}): {result['head']['ref']} -> {result['base']['ref']}: "
              f"{t['commits']} commits, {t['files']} files, +{t['added']}/-{t['deleted']}, "
              f"merge {result['merge']['status']}, {len(result['malformed_commits'])} malformed commit messages "
              f"— written to {args.out}")
        for w in result["warnings"]:
            print("warning:", w)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
