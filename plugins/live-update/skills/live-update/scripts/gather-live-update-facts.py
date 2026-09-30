#!/usr/bin/env python3
"""Collect the facts needed to file one Jira ticket for a release.

Read-only: it reads git and hub files, and asks `gh` / `glab` (never `create`) for the release's
merge/pull request. It makes NO Jira call and reads no token - the skill's agent does the Jira
work with whatever Jira MCP tools are connected. This script only answers: which release is this,
which artifacts exist for it, which have a URL, and which are local files that must be attached.

Finding the release, in order: --branch / --version; else the most recently committed remote
branch matching releases.release_branch_regex on the primary repo; else its latest release tag;
else the newest facts.json under releases.out. Nothing found -> exit 2.

Keys read from brain.config.json (all optional; a missing one becomes a warning, never a guess):

  releases.primary_repo          repo whose branches/tags identify the release (default: the only repo)
  releases.production_branch     default "main"
  releases.integration_branch    default "develop" (never treated as a release branch)
  releases.release_branch_regex  default "^(release|hotfix)[-/._]"
  releases.tag_regex             enables the tag fallback
  releases.out                   release-notes folders: "<version> - <date>"
  approvals.out                  epic-approval folders: "<date> - <release branch>"
  jira.project, jira.component   what the ticket is filed under (asked for by the skill when unset)
  jira.components                optional {repo-id: component} override for the primary repo
  jira.issue_type                optional
  jira.label_prefix              default "live-update-release-"

    gather-live-update-facts.py [--hub DIR] [--repo ID] [--branch NAME | --version LABEL]
                                [--client-note-url URL] [--approval-url URL] [--host github|gitlab]
                                [--no-fetch] [--no-vcs-host]

Exit codes: 0 facts printed (missing artifacts are data), 2 a person must decide, 1 error.
"""

import sys

sys.dont_write_bytecode = True

import argparse
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_BRANCH_RE = r"^(release|hotfix)[-/._]"
DEFAULT_LABEL_PREFIX = "live-update-release-"
VERSION_RE = re.compile(r"\d+(?:[._-]\d+){0,3}")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class Decide(Exception):
    """Something a person has to choose; exit 2 with the message."""


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


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
    raise Decide("no Product Brain hub here (no brain.config.json in this folder or any parent); "
                 "run inside the hub or pass --hub DIR")


class Config:
    def __init__(self, hub):
        self.hub = hub
        try:
            self.data = json.loads((hub / "brain.config.json").read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise RuntimeError(f"brain.config.json: invalid JSON at line {e.lineno}: {e.msg}")

    def get(self, dotted, default=None):
        node = self.data
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def repo_ids(self):
        return [r["id"] for r in self.get("repos", []) if isinstance(r, dict) and r.get("id")]

    def repo_path(self, repo_id):
        base = self.get("workspace.repos_dir") or "repos"
        for r in self.get("repos", []):
            if isinstance(r, dict) and r.get("id") == repo_id:
                return self.hub / (r.get("path") or f"{base}/{repo_id}")
        raise Decide(f"repo '{repo_id}' is not in brain.config.json repos: {', '.join(self.repo_ids())}")

    def product(self):
        return self.get("hub.name") or self.get("hub_name") or self.hub.name


def version_of(text):
    m = VERSION_RE.search(text or "")
    return re.sub(r"[._-]", ".", m.group()) if m else None


def rel(hub, path):
    try:
        return str(Path(path).resolve().relative_to(hub))
    except ValueError:
        return str(path)


# ------------------------------------------------------------------------ finding the release

def latest_release_branch(repo, pattern, skip):
    """Most recently committed origin branch matching `pattern` (same rule as open-release-mr.py)."""
    out = git(repo, "for-each-ref", "--sort=-committerdate", "--format=%(refname:short)",
              "refs/remotes/origin").stdout.split()
    for ref in out:
        name = ref[len("origin/"):] if ref.startswith("origin/") else ref
        if name in skip or name in ("HEAD", "origin"):
            continue
        if pattern.search(name):
            return name
    return None


def latest_tag(repo, tag_re):
    if not tag_re:
        return None
    tags = [t for t in git(repo, "tag", "--sort=v:refname").stdout.split() if re.search(tag_re, t)]
    return tags[-1] if tags else None


def dated_folders(out_dir, date_first):
    """[(date, label_part, folder)] for `<date> - <x>` (epic-approval) or `<x> - <date>` (release-notes)."""
    found = []
    if not out_dir or not out_dir.is_dir():
        return found
    for d in out_dir.iterdir():
        if not d.is_dir():
            continue
        a, sep, b = (d.name.partition(" - ") if date_first else d.name.rpartition(" - "))
        date, name = (a, b) if date_first else (b, a)
        if sep and DATE_RE.match(date):
            found.append((date, name, d))
    return found


def branch_state(repo, branch, prod):
    if not branch:
        return "unknown"
    if git(repo, "rev-parse", "--verify", "--quiet", f"origin/{branch}^{{commit}}").returncode != 0:
        return "unknown"
    if git(repo, "rev-parse", "--verify", "--quiet", f"origin/{prod}^{{commit}}").returncode != 0:
        return "unknown"
    merged = git(repo, "merge-base", "--is-ancestor", f"origin/{branch}", f"origin/{prod}").returncode == 0
    return "merged" if merged else "open"


def identify_release(cfg, repo, args, prod, warnings):
    if args.branch:
        return {"branch": args.branch, "version_label": version_of(args.branch) or args.branch,
                "source": "cli-branch"}
    if args.version:
        return {"branch": None, "version_label": version_of(args.version) or args.version,
                "source": "cli-version"}
    pattern = re.compile(cfg.get("releases.release_branch_regex") or DEFAULT_BRANCH_RE)
    skip = {prod, cfg.get("releases.integration_branch") or "develop"}
    branch = latest_release_branch(repo, pattern, skip)
    if branch:
        return {"branch": branch, "version_label": version_of(branch) or branch, "source": "branch"}
    tag = latest_tag(repo, cfg.get("releases.tag_regex"))
    if tag:
        warnings.append("no release branch on origin; using the latest release tag "
                        f"'{tag}' (the branch was probably merged and deleted)")
        return {"branch": None, "version_label": version_of(tag) or tag, "source": "tag"}
    out = cfg.get("releases.out")
    newest = max(dated_folders(cfg.hub / out if out else None, False), default=None,
                 key=lambda t: t[0])
    if newest:
        date, name, folder = newest
        label = name
        facts = folder / "facts.json"
        if facts.is_file():
            try:
                label = json.loads(facts.read_text(encoding="utf-8")).get("label") or name
            except (json.JSONDecodeError, OSError):
                pass
        warnings.append("no release branch or tag found; using the newest release-notes folder "
                        f"'{folder.name}'")
        return {"branch": None, "version_label": version_of(label) or label, "source": "release_notes_folder"}
    raise Decide("could not tell which release this is: no branch matching "
                 f"{pattern.pattern!r} on origin, no release tag, no release-notes folder. "
                 "Pass --branch NAME or --version LABEL.")


# ------------------------------------------------------------------------ the artifacts

def epic_approval_facts(cfg, release, approval_url, warnings):
    out = cfg.get("approvals.out")
    info = {"configured": bool(out), "folder": None, "exists": False, "reports": [],
            "summary_path": None, "page_path": None, "report_date": None, "note": None,
            "page_url": None, "page_url_source": None}
    files = []
    if not out:
        info["note"] = "approvals.out is not set in brain.config.json"
        warnings.append("approvals.out is not set, so epic-approval reports cannot be looked up")
        return info, files
    want = release["branch"].replace("/", "-") if release["branch"] else None
    best = None
    for date, name, folder in dated_folders(cfg.hub / out, True):
        exact = want is not None and name == want
        if exact or version_of(name) == release["version_label"]:
            if best is None or (date, exact) > (best[0], best[3]):
                best = (date, name, folder, exact)
    if not best:
        info["note"] = "no epic-approval folder matches this release - has epic-approval run yet?"
        warnings.append(info["note"])
        return info, files
    date, _, folder, _ = best
    info.update(folder=rel(cfg.hub, folder), exists=True, report_date=date)
    page = cfg.hub / ".work/epic-approval" / folder.name / "approval.html"  # git-ignored, made by epic-approval Step 6
    if page.is_file():
        info["page_path"] = rel(cfg.hub, page)
    if approval_url:
        info.update(page_url=approval_url, page_url_source="cli-arg")
    elif page.is_file():
        files.append({"kind": "epic_approval_page", "path": str(page.resolve()),
                      "label": "epic-approval: approval.html (not published as an Artifact)"})
    for md in sorted(folder.glob("*.md")):
        if md.name.lower() == "readme.md":
            info["summary_path"] = rel(cfg.hub, md)
            files.append({"kind": "epic_approval_summary", "path": str(md.resolve()),
                          "label": "epic-approval: README.md"})
        else:
            info["reports"].append({"repo": md.stem, "path": rel(cfg.hub, md)})
            files.append({"kind": "epic_approval_report", "repo": md.stem, "path": str(md.resolve()),
                          "label": f"epic-approval: {md.name}"})
    return info, files


def release_notes_facts(cfg, release, client_url, warnings):
    out = cfg.get("releases.out")
    info = {"configured": bool(out), "folder": None, "exists": False, "files": {},
            "unreleased": None, "client_note_artifact_url": None,
            "client_note_artifact_url_source": None}
    files = []
    if not out:
        warnings.append("releases.out is not set, so release-notes output cannot be looked up")
        return info, files
    best = None
    for date, name, folder in dated_folders(cfg.hub / out, False):
        if version_of(name) == release["version_label"] and (best is None or date > best[0]):
            best = (date, folder)
    if not best:
        warnings.append("no release-notes folder matches this release - has release-notes run yet?")
        return info, files
    folder = best[1]
    info.update(folder=rel(cfg.hub, folder), exists=True)
    names = {"facts_json": "facts.json", "internal_md": "internal.md", "client_html": "client.html",
             "client_pdf": "client.pdf", "figures_dir": "figures"}
    for key, fname in names.items():
        p = folder / fname
        info["files"][key] = rel(cfg.hub, p) if p.exists() else None
    facts_url = None
    if info["files"]["facts_json"]:
        try:
            facts = json.loads((folder / "facts.json").read_text(encoding="utf-8"))
            info["unreleased"] = facts.get("unreleased")
            facts_url = facts.get("clientNoteArtifactUrl")
        except (json.JSONDecodeError, OSError):
            warnings.append("release-notes facts.json is not readable JSON")
    if client_url:
        info.update(client_note_artifact_url=client_url, client_note_artifact_url_source="cli-arg")
    elif facts_url:
        info.update(client_note_artifact_url=facts_url, client_note_artifact_url_source="facts.json")
    for key, kind, label in (("internal_md", "internal_note", "release-notes: internal.md"),
                             ("client_pdf", "client_pdf", "release-notes: client.pdf"),
                             ("facts_json", "facts_json", "release-notes: facts.json")):
        if info["files"][key]:
            files.append({"kind": kind, "path": str((cfg.hub / info["files"][key]).resolve()), "label": label})
    if info["files"]["client_html"] and not info["client_note_artifact_url"]:
        files.append({"kind": "client_html", "path": str((cfg.hub / info["files"]["client_html"]).resolve()),
                      "label": "release-notes: client.html (not published as an Artifact)"})
    return info, files


def detect_host(repo):
    url = git(repo, "remote", "get-url", "origin").stdout.strip().lower()
    return "gitlab" if "gitlab" in url else "github" if "github" in url else None


def merge_request_facts(repo, branch, host, skip):
    info = {"branch": branch, "host": None, "url": None, "state": None, "found_via": ""}
    if skip:
        info["found_via"] = "skipped (--no-vcs-host)"
        return info
    if not branch:
        info["found_via"] = "no release branch to look up"
        return info
    host = host or detect_host(repo)
    info["host"] = host
    if not host:
        info["found_via"] = "host not detected (origin names neither github nor gitlab; pass --host)"
        return info
    cli = "gh" if host == "github" else "glab"
    if not shutil.which(cli):
        info["found_via"] = f"{cli} not available"
        return info
    cmd = ([cli, "pr", "view", branch, "--json", "url,state"] if host == "github"
           else [cli, "mr", "view", branch, "-F", "json"])
    proc = subprocess.run(cmd, cwd=str(repo), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        info["found_via"] = "not found"
        return info
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        info["found_via"] = "unreadable output"
        return info
    state = str(data.get("state") or "").lower()
    info.update(url=data.get("url") or data.get("web_url"),
                state={"opened": "open"}.get(state, state) or None, found_via=f"{cli} view")
    return info


def jira_facts(cfg, repo_id, release, warnings):
    project = cfg.get("jira.project")
    component = (cfg.get("jira.components") or {}).get(repo_id) or cfg.get("jira.component")
    missing = [k for k, v in (("jira.project", project), ("jira.component", component)) if not v]
    for key in missing:
        warnings.append(f"{key} is not set - ask the user, then offer to save it in brain.config.json")
    label = release["version_label"]
    safe = re.sub(r"[^A-Za-z0-9._-]", "-", label)
    marker = f"[release:{label}]"
    return {"project": project, "component": component, "issue_type": cfg.get("jira.issue_type"),
            "marker": marker,
            "suggested_label": (cfg.get("jira.label_prefix") or DEFAULT_LABEL_PREFIX) + safe,
            "suggested_summary": f"{marker} Production deployment - {cfg.product()} {label}",
            "missing_keys": missing}


# ------------------------------------------------------------------------ main

def run(args):
    hub = find_hub(args.hub)
    cfg = Config(hub)
    warnings = []
    repo_id = args.repo or cfg.get("releases.primary_repo")
    if not repo_id:
        ids = cfg.repo_ids()
        if len(ids) != 1:
            raise Decide("releases.primary_repo is not set and the hub has "
                         f"{len(ids)} repos - set it, or pass --repo ID")
        repo_id = ids[0]
    repo = cfg.repo_path(repo_id)
    if not repo.is_dir():
        raise Decide(f"the clone of '{repo_id}' is missing at {rel(hub, repo)} - run `pb sync`")
    prod = cfg.get("releases.production_branch") or "main"

    if not args.no_fetch:
        proc = git(repo, "fetch", "--prune", "--quiet", "origin")
        if proc.returncode != 0:
            warnings.append(f"git fetch failed in {repo_id} ({proc.stderr.strip()[:160]}); "
                            "facts describe the clone as it stands")

    release = identify_release(cfg, repo, args, prod, warnings)
    release["branch_state"] = branch_state(repo, release["branch"], prod)
    release["primary_repo"] = repo_id

    epic, epic_files = epic_approval_facts(cfg, release, args.approval_url, warnings)
    notes, notes_files = release_notes_facts(cfg, release, args.client_note_url, warnings)
    mr = merge_request_facts(repo, release["branch"], args.host, args.no_vcs_host)
    if not args.no_vcs_host and release["branch"] and not mr["url"]:
        warnings.append(f"no merge/pull request found for '{release['branch']}' ({mr['found_via']})")

    return {
        "hub": str(hub),
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "release": release,
        "epic_approval": epic,
        "release_notes": notes,
        "merge_request": mr,
        "links": {"merge_request_url": mr["url"],
                  "epic_approval_page_url": epic["page_url"],
                  "client_note_artifact_url": notes["client_note_artifact_url"]},
        "attachments": epic_files + notes_files,
        "jira": jira_facts(cfg, repo_id, release, warnings),
        "warnings": warnings,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--hub", help="hub folder (default: walk up from the current directory)")
    ap.add_argument("--repo", help="repo id (default: releases.primary_repo)")
    which = ap.add_mutually_exclusive_group()
    which.add_argument("--branch", help="the release branch, instead of finding the latest")
    which.add_argument("--version", help="the release version label, when there is no branch")
    ap.add_argument("--client-note-url", help="URL of the client note published as an Artifact")
    ap.add_argument("--approval-url", help="URL of the epic-approval page (approval.html) published as an Artifact")
    ap.add_argument("--host", choices=["github", "gitlab"], help="override host detection")
    ap.add_argument("--no-fetch", action="store_true", help="skip git fetch")
    ap.add_argument("--no-vcs-host", action="store_true", help="do not call gh / glab")
    args = ap.parse_args()
    try:
        facts = run(args)
    except Decide as e:
        print(f"decide: {e}", file=sys.stderr)
        return 2
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(json.dumps(facts, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
