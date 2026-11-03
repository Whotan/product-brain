#!/usr/bin/env python3
"""Collect the facts a release note is written from, for every configured repo.

Reads git only. Writes <releases.out>/<version> - <date>/facts.json - derived
state, never hand-edited. Everything a note claims about *what changed* must
trace to a field in this file; everything it claims about *what a user can now
do* is judgment written by a human on top of it.

Config (brain.config.json):
    repos                             which clones to read (repos/<id>, or a repo's `path`)
    releases.tag_regex                a matching tag IS a production release
    releases.primary_repo             whose latest matching tag names the release by default
    releases.production_branch        the branch release tags are cut from
    releases.out                      where release folders live
    releases.client_note.locale       the client note's language
    releases.client_note.i18n         [{repo, path}] - the client-locale string files
    releases.client_note.i18n_source  [{repo, path}] - the source-language string files (optional)
    releases.specs_dir | roadmap.specs_dir   Spec Kit folder, for spec citations (optional)
    releases.areas                    [[regex, area], ...] extra path->area rules (optional)

Usage:
    python gather-release-facts.py                      latest release tag on the primary repo
    python gather-release-facts.py --to <tag>
    python gather-release-facts.py --to <tag> --from <earlier-tag>
    python gather-release-facts.py --from origin/main --to origin/develop --label <next> --date YYYY-MM-DD
    python gather-release-facts.py --no-fetch
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys

sys.dont_write_bytecode = True
from pathlib import Path

from _hub import Config, find_hub, safe_ref, shown, utf8_stdio, version_label

UNIT = "\x1f"

# Path -> area. First match wins, so order matters. These cover common backend
# and frontend layouts; a hub adds its own with `releases.areas`, which are
# checked first.
AREA_RULES = [
    (re.compile(r"database/migrations/|/migrations/|\.sql$"), "schema-migration"),
    (re.compile(r"(assets/i18n/|i18n/|locales?/|lang/).*\.(json|ya?ml|po|php)$"), "i18n"),
    (re.compile(r"^(tests?/|spec/|.*\.spec\.[jt]sx?$|.*\.test\.[jt]sx?$|.*Test\.php$|.*_test\.(py|go)$)"), "tests"),
    (re.compile(r"^routes/"), "http-routes"),
    (re.compile(r"^config/|\.env\.example$|environment\.template\.ts$"), "config"),
    (re.compile(r"^app/Actions/"), "action"),
    (re.compile(r"^app/Models/"), "model"),
    (re.compile(r"^app/Services/"), "service"),
    (re.compile(r"^app/Filament/"), "admin-panel"),
    (re.compile(r"^app/Http/"), "http-layer"),
    (re.compile(r"^app/Jobs/|^app/Console/"), "background-job"),
    (re.compile(r"^apps/[^/]+/src/app/|^src/app/|^src/pages/|^src/components/"), "web-feature"),
    (re.compile(r"^libs/|^packages/"), "web-shared-lib"),
    (re.compile(r"Dockerfile|\.gitlab-ci\.yml|^\.github/workflows/|^docker/"), "build-pipeline"),
    (re.compile(r"^docs/|\.md$"), "docs"),
]
TAG_PATTERN = None  # releases.tag_regex, compiled in main()

CONVENTIONAL = re.compile(
    r"^(?P<type>feat|fix|critical-fix|bug|perf|refactor|docs|test|build|ci|chore|style|revert)"
    r"(?:\((?P<scope>[^)]*)\))?(?P<breaking>!)?:\s*(?P<subject>.+)$",
    re.IGNORECASE,
)
# Spec evidence, strongest first. A spec id is only ever cited when a folder
# with that id exists under the specs dir - "404-page" or "Closes #104" is not a
# spec just because it has three digits.
#   slug   "NNN-some-slug" in a subject, and the slug matches the folder name
#   branch the same shape in a merge subject (the branch that carried the work)
#   path   a changed file under specs/NNN-.../
#   issue  a bare "#NNN" - usually an issue number, so WEAK: listed separately
SLUG_ID = re.compile(r"(?<![\w/.])(\d{3})-([a-z0-9][a-z0-9-]*)")
HASH_ID = re.compile(r"(?<![\w&])#(\d{3})\b")
PATH_ID = re.compile(r"(?:^|/)specs/(\d{3})(?:-[^/]*)?/")
KNOWN_SPECS: dict = {}  # id -> folder name, filled in main()


def spec_refs(text: str, via: str) -> list:
    refs = []
    for match in SLUG_ID.finditer(text):
        sid, slug = match.group(1), match.group(2)
        folder = KNOWN_SPECS.get(sid)
        named = f"{sid}-{slug}"
        if folder and (folder == sid or folder.startswith(named) or named.startswith(folder)):
            refs.append({"id": sid, "via": via})
    for match in HASH_ID.finditer(text):
        if match.group(1) in KNOWN_SPECS:
            refs.append({"id": match.group(1), "via": "issue"})
    return refs

def git(repo: Path, *args: str, check: bool = True) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if check and proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed in {repo.name}: {proc.stderr.strip()}")
    return proc.stdout


def area_for(path: str) -> str:
    for pattern, area in AREA_RULES:
        if pattern.search(path):
            return area
    return "other"


def tags_in_order(repo: Path) -> list:
    """Release tags only, in version order.

    `--sort=v:refname`, never alphabetic: alphabetic order puts ...9 after ...16
    and mis-attributes a whole release. A tag that does not match
    releases.tag_regex is not a release (a spec checkpoint, a staging marker) and
    must not become the "previous release" boundary.
    """
    out = git(repo, "tag", "--sort=v:refname")
    tags = [t.strip() for t in out.splitlines() if t.strip()]
    return [t for t in tags if TAG_PATTERN is None or TAG_PATTERN.search(t)]


def release_date(repo: Path, ref: str) -> str:
    """Contract addendum 3, rule 3: the tagger date of an annotated tag, else the
    tagged commit's committer date. Never parsed out of the tag's name."""
    tagged = git(repo, "for-each-ref", "--format=%(taggerdate:iso-strict)", f"refs/tags/{ref}",
                 check=False).strip()
    if tagged:
        return tagged[:10]
    return git(repo, "log", "-1", "--format=%cI", f"{ref}^{{commit}}").strip()[:10]


def fetch_tags(repo: Path) -> bool:
    """Rule 5: a failed fetch is said out loud and recorded, never swallowed."""
    proc = subprocess.run(["git", "-C", str(repo), "fetch", "--tags", "--quiet"],
                          capture_output=True, text=True, errors="replace")
    if proc.returncode != 0:
        print(f"  WARN: git fetch --tags failed in {repo.name} ({proc.stderr.strip()[:200]}) - "
              "the facts describe the local clone as it stands", file=sys.stderr)
    return proc.returncode == 0


def ref_exists(repo: Path, ref: str) -> bool:
    proc = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--verify", "--quiet", "--end-of-options",
         f"{ref}^{{commit}}"],
        capture_output=True, text=True,
    )
    return proc.returncode == 0


def resolve_range(repo: Path, to_tag, from_tag) -> dict:
    """Pick the range for this repo.

    Normally both ends are tags. They may also be arbitrary refs - the case that
    matters is `--from origin/main --to origin/develop`, i.e. "what is merged and
    waiting to go out". Such a range is UNRELEASED: no tag means no production
    image, so the notes must not speak in the past tense.
    """
    tags = tags_in_order(repo)

    non_tag = [r for r in (to_tag, from_tag) if r and r not in tags]
    if non_tag:
        missing = [r for r in non_tag if not ref_exists(repo, r)]
        if missing:
            return {"error": f"ref(s) not found in this repo: {', '.join(missing)}", "tags": tags[-5:]}
        to_ref = to_tag or (tags[-1] if tags else None)
        result = {
            "to": to_ref,
            "from": from_tag,
            "tags": tags[-5:],
            "unreleased": True,
            "toSha": git(repo, "rev-list", "-n", "1", to_ref).strip(),
            "toDate": release_date(repo, to_ref),
            "retagOnly": False,
        }
        result["fromSha"] = git(repo, "rev-list", "-n", "1", from_tag).strip() if from_tag else None
        if from_tag:
            # Which way round the two refs sit is a finding in its own right.
            behind, ahead = git(
                repo, "rev-list", "--left-right", "--count", f"{from_tag}...{to_ref}"
            ).split()
            result["aheadOfFrom"] = int(ahead)
            result["fromAheadOfTo"] = int(behind)
            result["latestTag"] = tags[-1] if tags else None
        return result

    if not tags:
        return {"error": "repo has no tags", "tags": []}

    to_ref = to_tag or tags[-1]
    if to_ref not in tags:
        return {
            "error": f"tag {to_ref} does not exist in this repo",
            "latestTag": tags[-1],
            "tags": tags[-5:],
        }

    if from_tag:
        if from_tag not in tags:
            return {"error": f"tag {from_tag} does not exist in this repo", "tags": tags[-5:]}
        from_ref = from_tag
    else:
        idx = tags.index(to_ref)
        from_ref = tags[idx - 1] if idx > 0 else None

    result = {"to": to_ref, "from": from_ref, "tags": tags[-5:]}
    result["toSha"] = git(repo, "rev-list", "-n", "1", to_ref).strip()
    result["toDate"] = release_date(repo, to_ref)
    if from_ref:
        result["fromSha"] = git(repo, "rev-list", "-n", "1", from_ref).strip()
        # A tag pointing at the same commit as its predecessor shipped nothing.
        result["retagOnly"] = result["toSha"] == result["fromSha"]
    else:
        result["fromSha"] = None
        result["retagOnly"] = False
    return result


def rangespec(rng: dict) -> str:
    return f"{rng['from']}..{rng['to']}" if rng.get("from") else rng["to"]


def commits_in(repo: Path, rng: dict) -> list:
    fmt = UNIT.join(["%H", "%s", "%an", "%aI"])
    raw = git(repo, "log", "--no-merges", f"--format={fmt}", rangespec(rng))
    commits = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        sha, subject, author, date = line.split(UNIT)
        match = CONVENTIONAL.match(subject)
        commits.append(
            {
                "sha": sha[:8],
                "subject": subject,
                "author": author,
                "date": date,
                "type": (match.group("type").lower() if match else None),
                "scope": (match.group("scope") if match else None),
                "breaking": bool(match and match.group("breaking")),
                "specRefs": spec_refs(subject, "slug"),
            }
        )
    return commits


def merges_in(repo: Path, rng: dict) -> list:
    raw = git(repo, "log", "--merges", f"--format=%H{UNIT}%s", rangespec(rng))
    out = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        sha, subject = line.split(UNIT)
        out.append({"sha": sha[:8], "subject": subject, "specRefs": spec_refs(subject, "branch")})
    return out


def files_in(repo: Path, rng: dict) -> dict:
    """Changed files in the range.

    count / added / deleted are FILE counts (added = new files, deleted = removed
    files); linesAdded / linesDeleted are line counts from --numstat.
    """
    empty = {"byArea": {}, "count": 0, "added": 0, "deleted": 0,
             "linesAdded": 0, "linesDeleted": 0, "paths": []}
    if not rng.get("from"):
        return empty
    span = f"{rng['from']}..{rng['to']}"
    raw = git(repo, "diff", "--numstat", span)
    status = git(repo, "diff", "--name-status", "--no-renames", span)
    by_area = {}
    lines_added = lines_deleted = 0
    paths = []
    for line in raw.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        a, d, path = parts
        lines_added += int(a) if a.isdigit() else 0
        lines_deleted += int(d) if d.isdigit() else 0
        paths.append(path)
        by_area.setdefault(area_for(path), []).append(path)
    kinds = [row.split("\t", 1)[0][:1] for row in status.splitlines() if "\t" in row]
    return {
        "byArea": {k: sorted(v) for k, v in sorted(by_area.items())},
        "count": len(paths),
        "added": kinds.count("A"),
        "deleted": kinds.count("D"),
        "linesAdded": lines_added,
        "linesDeleted": lines_deleted,
        "paths": sorted(paths),
    }


def load_json_at(repo: Path, ref: str, path: str) -> dict:
    out = git(repo, "show", f"{ref}:{path}", check=False)
    if not out.strip():
        return {}
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return {}


def flatten(obj, prefix="") -> dict:
    flat = {}
    if isinstance(obj, dict):
        for key, value in obj.items():
            flat.update(flatten(value, f"{prefix}.{key}" if prefix else key))
    else:
        flat[prefix] = obj
    return flat


def i18n_delta(cfg: Config, repo_id: str, repo: Path, rng: dict) -> list:
    """New/changed user-visible strings in the client locale, paired by key.

    This is the vocabulary the client note must be written in. The client-locale
    value is NOT assumed to be a translation of the source-language value - in
    many products both are authored separately and say different things - so
    the note takes its wording from the client-locale file, read AT THE TAG with
    `git show`, never from the working tree.

    Each entry: {key, file, new, client, source}. A key that changed in a source
    file and has no client value is an i18n gap: a finding for the internal note.
    """
    if not rng.get("from"):
        return []
    client_files = [e["path"] for e in cfg.get("releases.client_note.i18n", [])
                    if e.get("repo") == repo_id]
    source_files = [e["path"] for e in cfg.get("releases.client_note.i18n_source", [])
                    if e.get("repo") == repo_id]
    if not client_files and not source_files:
        return []

    def partner_of(path: str, pool: list):
        folder = str(Path(path).parent)
        same = [p for p in pool if str(Path(p).parent) == folder]
        return same[0] if same else None

    pairs = {}
    for path in client_files:
        before = flatten(load_json_at(repo, rng["from"], path))
        after = flatten(load_json_at(repo, rng["to"], path))
        src = partner_of(path, source_files)
        src_after = flatten(load_json_at(repo, rng["to"], src)) if src else {}
        for key, value in after.items():
            if before.get(key) != value:
                pairs[(path, key)] = {"key": key, "file": path, "new": key not in before,
                                      "client": value, "source": src_after.get(key)}
    for src in source_files:
        before = flatten(load_json_at(repo, rng["from"], src))
        after = flatten(load_json_at(repo, rng["to"], src))
        partner = partner_of(src, client_files)
        client_after = flatten(load_json_at(repo, rng["to"], partner)) if partner else {}
        for key, value in after.items():
            if before.get(key) == value or (partner, key) in pairs:
                continue
            pairs[(partner or src, key)] = {"key": key, "file": partner or src,
                                            "new": key not in before,
                                            "client": client_after.get(key), "source": value}
    return sorted(pairs.values(), key=lambda e: (e["file"], e["key"]))


def reverts_in(commits: list) -> list:
    return [c for c in commits if c["type"] == "revert" or c["subject"].lower().startswith("revert")]


def release_folder_name(tag: str, release_date: str) -> str:
    """One folder per release, named '<version> - <release date>'.

    Note for anyone listing this directory: these sort alphabetically, which puts
    a '...9 - ' folder after a '...16 - ' one. Sort by the date half, or by tag
    with `git tag --sort=v:refname`, when order matters.
    """
    return f"{tag} - {release_date}"


def hub_specs(cfg: Config, evidence: dict) -> list:
    """Spec folders this release touches, each with how we know (`evidence`).

    `weak: true` when the only evidence is a bare #NNN - most likely an issue
    number. Confirm those before citing them.
    """
    spec_ids = set(evidence)
    found = []
    rel = cfg.get("releases.specs_dir", None) or cfg.get("roadmap.specs_dir", None)
    if not rel or not spec_ids:
        return found
    specs_dir = cfg.hub / rel
    if not specs_dir.is_dir():
        return found
    for entry in sorted(specs_dir.iterdir()):
        if not entry.is_dir():
            continue
        num = entry.name.split("-")[0]
        if num in spec_ids:
            found.append(
                {
                    "id": entry.name,
                    "spec": f"{rel}/{entry.name}/spec.md" if (entry / "spec.md").exists() else None,
                    "plan": f"{rel}/{entry.name}/plan.md" if (entry / "plan.md").exists() else None,
                    "tasks": f"{rel}/{entry.name}/tasks.md" if (entry / "tasks.md").exists() else None,
                    "ticks": claimed_ticks(entry),
                    "evidence": sorted(evidence[num]),
                    "weak": evidence[num] == {"issue"},
                }
            )
    return found


TICK = re.compile(r"^\s*[-*]\s+\[([ xX])\]", re.MULTILINE)


def claimed_ticks(folder: Path) -> dict:
    """Checkboxes a spec folder CLAIMS are done (contract addendum 6).

    tasks.md if present, else every *.md in the folder - some specs keep their
    task list inline. A claim, not a verdict: ticked tasks have been wrong about
    what shipped, so a release note never cites them as proof.
    """
    tasks = folder / "tasks.md"
    files = [tasks] if tasks.is_file() else sorted(folder.glob("*.md"))
    marks = [m for f in files for m in TICK.findall(f.read_text(encoding="utf-8", errors="replace"))]
    return {"done": sum(1 for m in marks if m in "xX"), "total": len(marks),
            "source": "tasks.md" if tasks.is_file() else "*.md"}


def on_branch(repo: Path, sha: str, branch: str):
    """Is the release commit on the production branch? None if the branch is absent.

    Ancestry is trustworthy in THIS direction (is the tagged commit contained in
    the branch it was cut from). It is the other direction - "is feature X in the
    release" - that lies under squash merges.
    """
    for ref in (f"origin/{branch}", branch):
        if ref_exists(repo, ref):
            proc = subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", sha, ref],
                                  capture_output=True, text=True)
            return proc.returncode == 0
    return None


def collect(cfg: Config, repo_id: str, to_tag, from_tag, fetch: bool) -> dict:
    repo = cfg.repo_path(repo_id)
    if not repo.is_dir():
        return {"id": repo_id, "error": f"clone missing at {shown(repo, cfg.hub)}"}

    fetched = fetch_tags(repo) if fetch else None

    facts = {
        "id": repo_id,
        "fetched": fetched,
        "head": git(repo, "rev-parse", "--short", "HEAD").strip(),
        "branch": git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip(),
        "dirty": bool(git(repo, "status", "--porcelain").strip()),
    }
    rng = resolve_range(repo, to_tag, from_tag)
    facts["range"] = rng
    if rng.get("error"):
        return facts

    commits = commits_in(repo, rng)
    files = files_in(repo, rng)
    facts["commits"] = commits
    facts["merges"] = merges_in(repo, rng)
    facts["files"] = files
    facts["specRefs"] = [ref for path in files["paths"] for ref in
                         ({"id": m.group(1), "via": "path"} for m in [PATH_ID.search(path)] if m)
                         if ref["id"] in KNOWN_SPECS]
    facts["i18n"] = i18n_delta(cfg, repo_id, repo, rng)
    if not rng.get("unreleased"):
        facts["onProductionBranch"] = on_branch(repo, rng["toSha"],
                                                cfg.get("releases.production_branch"))
    facts["reverts"] = reverts_in(commits)
    facts["conventionalCoverage"] = (
        round(100 * sum(1 for c in commits if c["type"]) / len(commits)) if commits else 0
    )
    facts["breaking"] = [c for c in commits if c["breaking"]]
    counts = {}
    for commit in commits:
        key = commit["type"] or "uncategorised"
        counts[key] = counts.get(key, 0) + 1
    facts["typeCounts"] = dict(sorted(counts.items()))
    return facts


def main() -> int:
    global TAG_PATTERN, AREA_RULES
    utf8_stdio()
    parser = argparse.ArgumentParser(description="Collect release facts from every configured repo.")
    parser.add_argument("--to", help="release tag to describe (default: the latest release tag "
                                     "on releases.primary_repo)")
    parser.add_argument("--from", dest="from_tag", help="previous tag (default: the one before --to)")
    parser.add_argument("--no-fetch", action="store_true", help="skip git fetch --tags")
    parser.add_argument("--label", help="version label for the folder (default: the --to tag). "
                                        "Required when --to is not a tag")
    parser.add_argument("--date", help="release date YYYY-MM-DD (default: the tag's commit date). "
                                       "Use it for a release that has not happened yet.")
    parser.add_argument("--out", help="output path (default: <releases.out>/<folder>/facts.json)")
    parser.add_argument("--hub", help="hub root (default: walk up from the current directory)")
    args = parser.parse_args()

    cfg = Config(find_hub(args.hub))
    TAG_PATTERN = re.compile(cfg.get("releases.tag_regex"))
    AREA_RULES = [(re.compile(rx), area) for rx, area in cfg.get("releases.areas", [])] + AREA_RULES
    repo_ids = cfg.repo_ids()
    primary = cfg.get("releases.primary_repo")
    if primary not in repo_ids:
        raise SystemExit(f"releases.primary_repo is {primary!r}, which is not in `repos` "
                         f"({', '.join(repo_ids)})")
    production = safe_ref(cfg.get("releases.production_branch"), "releases.production_branch")
    locale = cfg.client_locale
    for flag, value in (("--to", args.to), ("--from", args.from_tag)):
        if value:
            safe_ref(value, flag)
    primary_clone = cfg.repo_path(primary)
    if primary_clone.is_dir() and not any(ref_exists(primary_clone, r)
                                          for r in (f"origin/{production}", production)):
        print(f"releases.production_branch: neither origin/{production} nor {production} exists "
              f"in {primary}", file=sys.stderr)
        return 2

    rel = cfg.get("releases.specs_dir", None) or cfg.get("roadmap.specs_dir", None)
    if rel and (cfg.hub / rel).is_dir():
        for entry in sorted((cfg.hub / rel).iterdir()):
            if entry.is_dir() and re.match(r"\d{3}(-|$)", entry.name):
                KNOWN_SPECS.setdefault(entry.name[:3], entry.name)

    to_tag = args.to
    if not to_tag:
        primary_path = cfg.repo_path(primary)
        if not primary_path.is_dir():
            raise SystemExit(f"the primary repo's clone is missing at {shown(primary_path, cfg.hub)}")
        if not args.no_fetch:
            fetch_tags(primary_path)
        tags = tags_in_order(primary_path)
        if not tags:
            raise SystemExit(f"{primary} has no tag matching releases.tag_regex "
                             f"({cfg.get('releases.tag_regex')}) - pass --to")
        to_tag = tags[-1]

    repos = [collect(cfg, r, to_tag, args.from_tag, not args.no_fetch) for r in repo_ids]

    label = args.label or version_label(cfg, to_tag)
    unreleased = any(r.get("range", {}).get("unreleased") for r in repos)
    if unreleased and not args.label:
        raise SystemExit(
            "This range is not a tag, so there is no version to name the folder with.\n"
            "Pass --label (the version this is planned to ship as) and --date, e.g.\n"
            "    --from origin/main --to origin/develop --label <next-version> --date YYYY-MM-DD"
        )

    evidence: dict = {}
    for repo in repos:
        refs = [r for c in repo.get("commits", []) for r in c["specRefs"]]
        refs += [r for m in repo.get("merges", []) for r in m["specRefs"]]
        refs += repo.get("specRefs", [])
        for ref in refs:
            evidence.setdefault(ref["id"], set()).add(ref["via"])
    shipping = [
        repo["id"]
        for repo in repos
        if repo.get("commits") and not repo.get("range", {}).get("retagOnly")
    ]

    # The release date is the tag's own date (tagger date, else the tagged
    # commit's) - the latest across the repos that carry the tag, since repos are
    # usually tagged minutes apart.
    dates = [repo["range"]["toDate"] for repo in repos if repo.get("range", {}).get("toDate")]
    release_date = args.date or (max(dates) if dates else "unknown-date")

    facts = {
        "generatedFrom": subprocess.run(
            ["git", "-C", str(cfg.hub), "log", "-1", "--format=%cI"],
            capture_output=True, text=True,
        ).stdout.strip(),
        "tag": to_tag,
        "label": label,
        "versionLabel": label,
        "unreleased": unreleased,
        "releaseDate": release_date,
        "folder": release_folder_name(label, release_date),
        "clientLocale": locale,
        "primaryRepo": primary,
        "reposShipping": shipping,
        "specsCited": hub_specs(cfg, evidence),
        "repos": repos,
    }

    folder = cfg.releases_dir() / facts["folder"]
    out = Path(args.out) if args.out else folder / "facts.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(facts, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"wrote {shown(out, cfg.hub)}")
    print(f"release folder: {shown(out.parent, cfg.hub)}/")
    if unreleased:
        print(f"UNRELEASED: {label} is a planned release dated {release_date}. No tag exists, so no")
        print("production image has been built. Write both notes in the future tense.")
    print(f"release {label} ({release_date}) - repos with changes: {', '.join(shipping) or 'NONE'}")
    for repo in repos:
        rng = repo.get("range", {})
        if repo.get("error") or rng.get("error"):
            print(f"  {repo['id']}: {repo.get('error') or rng.get('error')}")
            continue
        note = " (re-tag only, shipped nothing)" if rng.get("retagOnly") else ""
        print(
            f"  {repo['id']}: {rng.get('from')}..{rng.get('to')} - "
            f"{len(repo['commits'])} commits, {repo['files']['count']} files, "
            f"conventional {repo['conventionalCoverage']}%{note}"
        )
        if rng.get("unreleased"):
            print(f"    ahead of {rng.get('from')}: {rng.get('aheadOfFrom')} commits; "
                  f"{rng.get('from')} ahead of it: {rng.get('fromAheadOfTo')} "
                  f"(last tag {rng.get('latestTag')})")
        if repo.get("onProductionBranch") is False:
            print(f"    NOT ON {cfg.get('releases.production_branch')}: the tagged commit is not "
                  "contained in the production branch - confirm how this was built")
        if repo["reverts"]:
            print(f"    REVERTS in range: {len(repo['reverts'])} - a reverted change is not live")
        if repo["breaking"]:
            print(f"    BREAKING: {len(repo['breaking'])}")
        if repo["files"]["byArea"].get("schema-migration"):
            migrations = len(repo["files"]["byArea"]["schema-migration"])
            print(f"    migrations: {migrations} - rollback is not free, say so under Risks")
        if repo["i18n"]:
            gaps = sum(1 for e in repo["i18n"] if e.get("client") in (None, ""))
            print(f"    i18n strings changed: {len(repo['i18n'])} - client wording comes from these"
                  + (f"; {gaps} with no {locale} value (an i18n gap)" if gaps else ""))
    strong = [s["id"] for s in facts["specsCited"] if not s["weak"]]
    weak = [s["id"] for s in facts["specsCited"] if s["weak"]]
    if strong:
        print(f"  specs cited: {', '.join(strong)}")
    if weak:
        print(f"  WEAK spec refs (only a bare #NNN, likely an issue number - confirm before "
              f"citing): {', '.join(weak)}")
    unfetched = [r["id"] for r in repos if r.get("fetched") is False]
    if unfetched:
        print(f"  fetched: false for {', '.join(unfetched)} - tags may be missing")
    return 0


if __name__ == "__main__":
    sys.exit(main())
