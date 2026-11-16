#!/usr/bin/env python3
"""Collect git facts for the delivery roadmap.

Emits a JSON facts file (machine-readable, diffable across runs so stalls are
detectable) and prints a human-readable summary.

Everything product-specific comes from the hub's brain.config.json:
    repos[]                       id, optional path (else workspace.repos_dir/<id>, else repos/<id>)
    releases.production_branch    e.g. "main"
    releases.integration_branch   e.g. "develop"
    releases.tag_regex            a matching tag IS a production release
    releases.version_regex        optional; group 1 is the version label
    releases.release_branch_regex optional; classifies merges onto production
    roadmap.facts                 where the facts file lives
    roadmap.specs_dir             optional; spec folders summarised as *claimed* progress

Usage, from anywhere inside the hub:
    python gather-git-facts.py
    python gather-git-facts.py --no-fetch
    python gather-git-facts.py --hub <path> --out <facts.json>

Exit codes: 0 all facts gathered; 1 facts written but something failed (a fetch,
a git command) - the summary names it; 2 configuration error (missing key,
branch that does not exist).

Stall detection compares branch tips against a BASELINE: the most recent run
from an earlier day. A same-day re-run keeps that baseline rather than
comparing against itself, so re-running never wipes the stall signal. Never
hand-edit the facts file; it is derived state.
"""

import argparse
import json
import re
import subprocess
import sys
sys.dont_write_bytecode = True
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from roadmap_hub import (fail, find_hub, get, load_config, rel_to_hub, repos,  # noqa: E402
                         require, require_ref_name, utf8_stdio)

# A branch is only interesting to a cycle roadmap if it has moved recently. Older
# refs are abandoned history and would drown the stall signal.
ACTIVE_WINDOW_DAYS = 45

CONVENTIONAL = re.compile(
    r"^(feat|fix|critical-fix|bug|chore|docs|refactor|test|perf|style|ci|build)(\(.+\))?!?:")

DEFAULT_RELEASE_BRANCH_REGEX = r"^(release|hotfix)[-/._]"


class GitError(RuntimeError):
    pass


def git(repo, *args):
    """Run git in `repo` and return stripped stdout. ANY non-zero exit raises
    GitError with git's stderr: an empty result must mean "nothing there", never
    "the command failed" (a bare or misspelt ref fails with "Not a valid object
    name", which a swallowed error would report as "not merged")."""
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        raise GitError(f"git {' '.join(args)}: {proc.stderr.strip() or f'exit {proc.returncode}'}")
    return proc.stdout.strip()


def origin_ref(name):
    """Every ref is origin/<name> (bare names do not resolve in fresh clones -
    trap 3), and a name may never be option-shaped."""
    if not name or name.startswith("-"):
        raise ValueError(f"refusing option-shaped ref name {name!r}")
    return f"origin/{name}"


def verify_branch(repo, key, name):
    """rev-parse --verify a configured branch up front; exit 2 naming the key."""
    ref = origin_ref(name)
    try:
        git(repo, "rev-parse", "--verify", "--quiet", "--end-of-options", f"{ref}^{{commit}}")
    except GitError:
        fail(f"FAIL: `{key}` = {name!r} but {ref} does not exist in {repo}.\n"
             f"  Check the branch name in brain.config.json (and that the clone has been fetched).")
    return ref


def days_since(iso):
    try:
        y, m, d = (int(x) for x in iso.split("-"))
        return (date.today() - date(y, m, d)).days
    except (ValueError, AttributeError):
        return None


def is_boring(ref, prod, integ, rel_branch_re):
    """Branches that are plumbing, not feature work: production, integration,
    origin/HEAD, release/hotfix branches (releases.release_branch_regex). The bare
    "origin" ref (origin/HEAD's symbolic target) shows up in for-each-ref output
    and is not a branch at all."""
    if ref == "origin":
        return True
    name = ref[len("origin/"):] if ref.startswith("origin/") else ref
    return name in {"HEAD", prod, integ} or bool(rel_branch_re.search(name))


def find_prev(prev, key, rel_path):
    """Baseline facts for this repo: by id, else by clone path (so renaming the
    facts keys does not silently reset stall detection)."""
    if key in prev:
        return prev[key]
    for blob in prev.values():
        if isinstance(blob, dict) and blob.get("path") == rel_path:
            return blob
    return None


def version_label(tag, tag_re, version_re):
    """releases.version_regex group 1 if set; else the named group (?P<version>)
    of tag_regex; else the whole tag. Never an unnamed tag_regex group - it may be
    an alternation such as ^(v|release-)..."""
    if version_re is not None:
        m = version_re.search(tag)
        return m.group(1) if m and m.group(1) else tag
    if "version" in tag_re.groupindex:
        m = tag_re.search(tag)
        return m.group("version") if m and m.group("version") else tag
    return tag


def collect_repo(key, path, rel_path, cfg_git, baseline_repos, have_baseline):
    out = {"path": rel_path, "errors": []}
    if not (path / ".git").exists():
        out["errors"].append(f"{rel_path} is not a git clone - is the hub checked out fully?")
        return out

    prod, integ, tag_re = cfg_git["prod"], cfg_git["integ"], cfg_git["tag_re"]
    rel_branch_re, version_re = cfg_git["rel_branch_re"], cfg_git["version_re"]
    PROD = verify_branch(path, "releases.production_branch", prod)
    INTEG = verify_branch(path, "releases.integration_branch", integ)

    def section(label, fn):
        try:
            fn()
        except GitError as exc:
            out["errors"].append(f"{label}: {exc}")

    # --- tags, ALWAYS version-sorted (trap 2); only tag_regex matches are releases ---
    def tags_section():
        all_tags = [t for t in git(path, "tag", "--sort=v:refname").splitlines() if t]
        tags = [t for t in all_tags if tag_re.search(t)]
        out["tags"] = tags
        out["otherTags"] = [t for t in all_tags if not tag_re.search(t)]
        out["latestTag"] = tags[-1] if tags else None

        # Commit, and release DATE: tagger date for an annotated tag, else the
        # tagged commit's committer date. Never parsed out of the tag name.
        tag_sha, tag_date, tag_iso = {}, {}, {}
        raw = git(path, "for-each-ref", "refs/tags",
                  "--format=%(refname:short)|%(taggerdate:iso-strict)"
                  "|%(*committerdate:iso-strict)|%(committerdate:iso-strict)"
                  "|%(*objectname)|%(objectname)")
        for line in raw.splitlines():
            parts = line.split("|")
            if len(parts) != 6 or parts[0] not in tags:
                continue
            name, tagger, peeled_commit_date, commit_date, peeled, obj = parts
            when = tagger or commit_date or peeled_commit_date or None
            tag_iso[name] = when
            tag_date[name] = when[:10] if when else None
            tag_sha[name] = (peeled or obj)[:7]
        out["tagSha"] = {t: tag_sha[t] for t in tags if t in tag_sha}
        out["tagDate"] = {t: tag_date[t] for t in tags if t in tag_date}
        out["tagDateIso"] = {t: tag_iso[t] for t in tags if t in tag_iso}

        # Duplicate tags on one commit reveal a release this repo did not contribute to (trap 9).
        dupes = {}
        for t, sha in out["tagSha"].items():
            dupes.setdefault(sha, []).append(t)
        out["tagsSharingACommit"] = {s: ts for s, ts in dupes.items() if len(ts) > 1}

        out["tagVersion"] = {t: version_label(t, tag_re, version_re) for t in tags}
        out["latestVersion"] = out["tagVersion"].get(out["latestTag"]) if tags else None
    section("tags", tags_section)

    # --- how code reached production. Releases are TAGS; these merges are only
    # the route code took onto the production branch, classified by source:
    #   releaseMerges  - from a release/hotfix branch (releases.release_branch_regex)
    #                    or from the integration branch
    #   featureMerges  - any other branch merged straight into production
    #   fastForwardedMerges - merges into ANOTHER branch that reached production
    #                    by fast-forward (counted, not listed)
    #   directCommits  - first-parent non-merge commits (direct pushes; under a
    #                    squash merge style a squashed MR looks exactly like this)
    def merges_section():
        release_merges, feature_merges, other_merges = [], [], []
        raw = git(path, "log", "--merges", "--first-parent", "--format=%h|%ad|%s",
                  "--date=short", "--end-of-options", PROD)
        for line in raw.splitlines():
            parts = line.split("|", 2)
            if len(parts) != 3:
                continue
            sha, when, subject = parts
            m = re.search(r"Merge (?:remote-tracking )?branch '([^']+)'(?: into '?([^'\s]+)'?)?", subject)
            name = m.group(1) if m else None
            target = m.group(2) if m else None
            if name and name.startswith("origin/"):
                name = name[len("origin/"):]
            row = {"sha": sha, "date": when, "branch": name, "into": target, "subject": subject}
            # git omits "into X" only when merging into the default branch. A merge
            # INTO another branch sits on production's first-parent chain because
            # production was fast-forwarded to it - it is not a merge into production.
            if target and target != prod:
                other_merges.append(row)
            elif name and (name == integ or rel_branch_re.search(name)):
                row["kind"] = "integration" if name == integ else "release-branch"
                release_merges.append(row)
            else:
                feature_merges.append(row)
        out["releaseMerges"] = release_merges
        out["featureMerges"] = feature_merges
        out["fastForwardedMerges"] = len(other_merges)
        direct = [l for l in git(path, "log", "--first-parent", "--no-merges",
                                 "--format=%h|%ad|%s", "--date=short",
                                 "--end-of-options", PROD).splitlines() if l]
        out["directCommits"] = {
            "count": len(direct),
            "recent": [dict(zip(("sha", "date", "subject"), l.split("|", 2))) for l in direct[:20]],
        }
    section("merges onto production", merges_section)

    # --- is integration fully contained in production? Measure, never assume (trap 11) ---
    def containment_section():
        counts = git(path, "rev-list", "--left-right", "--count", "--end-of-options",
                     f"{PROD}...{INTEG}")
        prod_only, integ_only = (int(x) for x in counts.split())
        out["productionAheadOfIntegration"] = prod_only
        out["integrationAheadOfProduction"] = integ_only
        out["integrationContainedInProduction"] = integ_only == 0
    section("integration vs production", containment_section)

    # --- feature branches, newest first, compared against the baseline run ---
    base_repo = find_prev(baseline_repos, key, rel_path)
    out["stallDetection"] = bool(have_baseline and base_repo is not None)
    base_tips = {b["ref"]: b.get("tip") for b in ((base_repo or {}).get("branches") or [])}

    def branches_section():
        branches = []
        raw = git(path, "for-each-ref", "--sort=-committerdate",
                  "--format=%(refname:short)|%(committerdate:short)|%(objectname:short)",
                  "refs/remotes/origin")
        for line in raw.splitlines():
            parts = line.split("|")
            if len(parts) != 3:
                continue
            ref, when, tip = parts
            if is_boring(ref, prod, integ, rel_branch_re):
                continue
            c = git(path, "rev-list", "--left-right", "--count", "--end-of-options",
                    f"{ref}...{INTEG}")
            ahead, behind = (int(x) for x in c.split())
            prev_tip = base_tips.get(ref)
            age = days_since(when)
            branches.append({
                "ref": ref, "tip": tip, "tipDate": when,
                "ahead": ahead, "behind": behind,
                "prevTip": prev_tip,
                "daysSinceCommit": age,
                "active": age is not None and age <= ACTIVE_WINDOW_DAYS,
                # Only meaningful against an earlier-day baseline; otherwise the
                # page must render movement as unknown (stallDetection false).
                "stalled": bool(out["stallDetection"] and prev_tip and prev_tip == tip),
            })
        out["branches"] = branches
    section("feature branches", branches_section)

    # --- conventional-commit coverage, so release grouping expectations are calibrated ---
    def coverage_section():
        subjects = git(path, "log", "--no-merges", "--format=%s", "-60",
                       "--end-of-options", PROD).splitlines()
        conv = sum(1 for s in subjects if CONVENTIONAL.match(s))
        out["conventionalCommitCoverage"] = {
            "conforming": conv, "sampled": len(subjects),
            "pct": round(100 * conv / len(subjects)) if subjects else None,
        }
    section("conventional-commit coverage", coverage_section)

    # --- reverts on production: a merged-then-reverted feature is NOT live (trap 3/5) ---
    def reverts_section():
        reverts = [l for l in git(path, "log", "-i", "--grep=revert", "--format=%h %ad %s",
                                  "--date=short", "-30", "--end-of-options", PROD).splitlines() if l]
        out["revertsOnProduction"] = reverts
    section("reverts on production", reverts_section)

    return out


TASK_DONE = re.compile(r"^\s*[-*+]\s+\[[xX]\]", re.M)
TASK_OPEN = re.compile(r"^\s*[-*+]\s+\[ \]", re.M)


def claimed_ticks(folder):
    """Claimed ticks: checkboxes in tasks.md if present, else across every *.md
    in the folder (specs with inline task lists). Returns (done, total, source)."""
    tasks = folder / "tasks.md"
    files = [tasks] if tasks.is_file() else sorted(folder.glob("*.md"))
    done = total = 0
    for f in files:
        txt = f.read_text(encoding="utf-8", errors="replace")
        d = len(TASK_DONE.findall(txt))
        done += d
        total += d + len(TASK_OPEN.findall(txt))
    source = "tasks.md" if tasks.is_file() else ("*.md" if files else None)
    return done, total, source


def collect_specs(hub, specs_dir):
    """Spec folders as *claimed* progress only - a tick is an intention (trap 5)."""
    root = Path(hub) / specs_dir
    if not root.is_dir():
        return {"dir": specs_dir, "error": f"{specs_dir}/ does not exist"}
    rows = []
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        done, total, source = claimed_ticks(d)
        rows.append({
            "dir": d.name,
            "hasSpec": (d / "spec.md").is_file(),
            "hasPlan": (d / "plan.md").is_file(),
            "tasksClaimed": ({"done": done, "total": total, "source": source}
                             if total else None),
        })
    return {"dir": specs_dir, "folders": rows}


def load_baseline(out_path, today):
    """Return (baseline_generated, baseline_repos, note).

    The baseline is the most recent run from an EARLIER day:
      - previous file from an earlier day -> that file's own branch tips;
      - previous file from today          -> the baseline IT compared against,
        so a same-day re-run neither compares against itself nor wipes the
        prior-day snapshot.
    """
    if not out_path.exists():
        return None, {}, "no previous facts file at that path"
    try:
        with open(out_path, encoding="utf-8") as fh:
            blob = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        return None, {}, f"previous facts file unreadable ({exc})"
    gen = blob.get("generated")
    if gen and gen < today:
        return gen, blob.get("repos") or {}, None
    base = blob.get("baseline") or {}
    if base.get("generated") and base["generated"] < today:
        return base["generated"], base.get("repos") or {}, None
    return None, {}, f"previous run is same-day ({gen}) and carries no earlier-day baseline"


def snapshot(repos_blob):
    """Minimal per-repo branch tips, stored as the next run's baseline."""
    return {k: {"path": r.get("path"),
                "branches": [{"ref": b["ref"], "tip": b.get("tip")} for b in r.get("branches") or []]}
            for k, r in repos_blob.items() if isinstance(r, dict)}


def main():
    utf8_stdio()

    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--hub", help="hub root (default: nearest ancestor with brain.config.json)")
    ap.add_argument("--no-fetch", action="store_true",
                    help="skip git fetch (offline; every count may be stale)")
    ap.add_argument("--out", help="facts file (default: roadmap.facts from the config)")
    args = ap.parse_args()

    hub = find_hub(args.hub)
    cfg = load_config(hub)
    prod = require_ref_name(cfg, "releases.production_branch", '"releases": {"production_branch": "main"}')
    integ = require_ref_name(cfg, "releases.integration_branch", '"releases": {"integration_branch": "develop"}')
    tag_src = require(cfg, "releases.tag_regex", r'"releases": {"tag_regex": "^v\\d+\\.\\d+\\.\\d+$"}')
    try:
        tag_re = re.compile(tag_src)
    except re.error as exc:
        fail(f"FAIL: releases.tag_regex {tag_src!r} does not compile: {exc}")
    facts_rel = args.out or require(cfg, "roadmap.facts",
                                    '"roadmap": {"facts": "docs/roadmap/.roadmap-facts.json"}')
    out_path = Path(facts_rel) if Path(facts_rel).is_absolute() else hub / facts_rel
    specs_dir = get(cfg, "roadmap.specs_dir")
    merge_style = get(cfg, "releases.merge_style")
    rel_src = get(cfg, "releases.release_branch_regex") or DEFAULT_RELEASE_BRANCH_REGEX
    ver_src = get(cfg, "releases.version_regex")
    try:
        rel_branch_re = re.compile(rel_src)
        version_re = re.compile(ver_src) if ver_src else None
    except re.error as exc:
        fail(f"FAIL: releases.release_branch_regex / version_regex does not compile: {exc}")
    if version_re is not None and version_re.groups < 1:
        fail(f"FAIL: releases.version_regex {ver_src!r} needs one capture group, "
             'e.g. "^v(\\d+\\.\\d+\\.\\d+)$"')
    cfg_git = {"prod": prod, "integ": integ, "tag_re": tag_re,
               "rel_branch_re": rel_branch_re, "version_re": version_re}

    today = date.today().isoformat()
    base_generated, base_repos, base_note = load_baseline(out_path, today)
    # Stall detection needs a baseline from an earlier day. Without one,
    # `stalled` is meaningless and must be reported as unknown, not as False.
    stall_detection = base_generated is not None
    facts = {
        "generated": today,
        "previousRun": base_generated,
        "stallDetection": stall_detection,
        "productionBranch": prod,
        "integrationBranch": integ,
        "tagRegex": tag_src,
        "releaseBranchRegex": rel_src,
        "mergeStyle": merge_style,
        "fetch": "skipped" if args.no_fetch else "attempted",
        "repos": {},
    }

    failures = []
    for key, path in repos(cfg, hub):
        rel_path = rel_to_hub(hub, path)
        fetched = None
        fetch_error = None
        if not args.no_fetch:
            # EVERY repo, every run. Fetching one and reading another is how
            # stale numbers get reported as current.
            print(f"fetching {rel_path} ...", file=sys.stderr)
            try:
                git(path, "fetch", "--all", "--prune", "--tags")
                fetched = True
            except GitError as exc:
                fetched, fetch_error = False, str(exc)
                print(f"FAIL fetch {rel_path}: {exc}", file=sys.stderr)
        blob = collect_repo(key, path, rel_path, cfg_git, base_repos, stall_detection)
        blob["fetched"] = fetched
        if fetch_error:
            blob["fetchError"] = fetch_error
            blob["errors"].insert(0, f"fetch failed - every figure below may be stale: {fetch_error}")
        failures.extend(f"[{key}] {e}" for e in blob["errors"])
        facts["repos"][key] = blob

    if specs_dir:
        facts["specs"] = collect_specs(hub, specs_dir)
        if facts["specs"].get("error"):
            failures.append(f"specs: {facts['specs']['error']}")

    # The baseline the NEXT same-day run must compare against: today's baseline if
    # we had one, else nothing (tomorrow's run will use this file itself).
    facts["baseline"] = ({"generated": base_generated, "repos": snapshot(base_repos)}
                         if stall_detection else None)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(facts, fh, indent=2, sort_keys=True)

    # ---- human summary ----
    print(f"\n=== roadmap git facts | {facts['generated']} ===")
    print(f"(written to {rel_to_hub(hub, out_path)}; production={prod}, integration={integ}, "
          f"tags /{tag_src}/, merge style {merge_style or 'unset'})")
    if stall_detection:
        print(f"stall detection ON  (baseline: run of {base_generated})\n")
    else:
        print("stall detection OFF - " + base_note + ".")
        print("  Branch movement is UNKNOWN this run, not 'no stalls'. Do not")
        print("  populate prevTip/stalled in DATA from this output, and do not")
        print("  report a stalled-branch count. Re-run tomorrow, or point --out")
        print("  at the tracked facts file to compare against the last real run.\n")
    for key, r in facts["repos"].items():
        print(f"[{key}] {r['path']}  (fetch: {'skipped' if r.get('fetched') is None else ('ok' if r['fetched'] else 'FAILED')})")
        for e in r.get("errors") or []:
            print(f"  FAIL {e}")
        if "tags" not in r and "branches" not in r:
            print()
            continue
        cov = r.get("conventionalCommitCoverage") or {}
        repo_stall = r.get("stallDetection")
        lt = r.get("latestTag")
        print(f"  latest tag        : {lt}  ({len(r.get('tags', []))} release tags"
              f", {len(r.get('otherTags', []))} other)"
              + (f"; version {r.get('latestVersion')}, dated {r.get('tagDate', {}).get(lt)}"
                 if lt else ""))
        fm = r.get("featureMerges", [])
        dc = (r.get("directCommits") or {}).get("count")
        print(f"  onto {prod}".ljust(20) + f": {len(r.get('releaseMerges', []))} release merge(s),"
              f" {len(fm)} direct feature merge(s), {dc} direct commit(s),"
              f" {r.get('fastForwardedMerges', 0)} merge(s) into other branches fast-forwarded in"
              + (" - squash merges look like direct commits" if merge_style == "squash" else ""))
        for row in fm[:5]:
            print(f"      feature merge {row['sha']} {row['date']} {row['branch'] or row['subject']}")
        contained = r.get("integrationContainedInProduction")
        print(f"  {integ} in {prod}".ljust(20) + f": {contained}"
              f"  ({integ} ahead by {r.get('integrationAheadOfProduction')})")
        print(f"  conv-commit cover : {cov.get('conforming')}/{cov.get('sampled')}"
              f" ({cov.get('pct')}%) - expect an Uncategorised group")
        dupes = r.get("tagsSharingACommit") or {}
        if dupes:
            print(f"  duplicate tags    : {len(dupes)} commit(s) carry >1 tag"
                  " -> that repo shipped nothing new in those releases")
        all_branches = r.get("branches", [])
        active = [b for b in all_branches if b.get("active")]
        print(f"  feature branches  : {len(all_branches)} total,"
              f" {len(active)} active (commit within {ACTIVE_WINDOW_DAYS}d)")
        if stall_detection and not repo_stall:
            print("  stall detection   : OFF for this repo - no entry for it in the baseline run")
        for b in active:
            # Without a usable baseline there is no evidence either way.
            # Printing "moving" here would assert movement never measured, and
            # that claim propagates into the page as a "0 stalled" tile.
            if not repo_stall or not b.get("prevTip"):
                mark = "movement unknown"
            elif b.get("stalled"):
                mark = "STALLED         "
            else:
                mark = "moved           "
            print(f"      {mark} {b['ref']} @ {b['tip']}"
                  f" ({b['tipDate']}, {b['daysSinceCommit']}d ago,"
                  f" +{b['ahead']}/-{b['behind']} vs {integ})")
        dormant = len(all_branches) - len(active)
        if dormant:
            print(f"      ... {dormant} dormant branch(es) omitted; see the JSON facts file")
        if r.get("revertsOnProduction"):
            print(f"  reverts on {prod}".ljust(20) + f": {len(r['revertsOnProduction'])}"
                  " -> check none of them reverts a feature you are about to call shipped")
        print()

    specs = facts.get("specs")
    if specs:
        if specs.get("error"):
            print(f"FAIL specs: {specs['error']}\n")
        else:
            folders = specs["folders"]
            full = [s["dir"] for s in folders
                    if s["tasksClaimed"] and s["tasksClaimed"]["total"]
                    and s["tasksClaimed"]["done"] == s["tasksClaimed"]["total"]]
            print(f"specs ({specs['dir']}/): {len(folders)} folder(s),"
                  f" {sum(1 for s in folders if s['tasksClaimed'])} with task checkboxes,"
                  f" {sum(1 for s in folders if s['hasPlan'])} with plan.md,"
                  f" {len(full)} fully ticked (claimed - verify each against git)\n")

    print("Next: this file holds facts only. A shipped verdict still requires the")
    print("per-feature decision procedure in references/git-verification-recipes.md.")
    if merge_style == "squash":
        print("releases.merge_style is 'squash': ancestry alone gives false negatives here.")
    else:
        print("Ancestry negatives still need the content-presence check before you trust them.")

    if failures:
        print(f"\n{len(failures)} FAILURE(S) - the facts file was written but is incomplete:")
        for f in failures:
            print(f"  FAIL {f}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
