#!/usr/bin/env python3
"""Audit a repo against the repo-docs standard (references/standard.md).

Usage: check_repo_docs.py [REPO_DIR] [--client | --no-client] [--hub]
Prints one line per finding and exits 1 when anything is missing.
"""
import json
import re
import sys
from pathlib import Path

HEADINGS = {
    "runbook.md": ["Prerequisites", "Local setup", "Run", "Debug", "Environments", "Deploy",
                   "Rollback", "Logs and monitoring", "Incidents"],
    "environment.md": ["Variables", "How to add a variable"],
    "testing.md": ["Test types", "Run tests locally", "Write a test", "Before you push",
                   "Tests in the pipeline"],
    "coding-conventions.md": ["AI rules, skills and plugins", "Tooling", "Team agreements"],
    "definition-of-done.md": ["Product", "Design", "Quality", "Release"],
    "merge-requests.md": ["Branches", "Commits", "Merge request description", "Review",
                          "Stage and production releases"],
    "architecture.md": ["Overview", "Why this architecture", "Current state", "Data flow",
                        "Related docs"],
    "domains.md": ["Domains", "Keeping this current"],
    "business-rules.md": ["Business rules", "Gaps", "Keeping this current"],
    "data-model.md": ["Overview", "Generated models", "Hand-written models", "Storage",
                      "Related docs"],
    "integrations/README.md": ["API contract", "Third-party services"],
    "known-issues.md": ["How to mark an issue in code", "Danger zones", "Known issues",
                        "Hacks and gaps"],
    "security.md": ["Authentication and sessions", "Authorization", "Personal data", "Secrets",
                    "Data retention", "Reporting a vulnerability"],
}
CLIENT_ONLY = {"ui-standards.md": ["Design system", "Structure", "Text and direction",
                                   "Accessibility", "Before PM and design review"]}
README_HEADINGS = ["Overview", "Tech stack", "Repository structure", "Core systems",
                   "Quick start", "Documentation"]
INTEGRATION_HEADINGS = ["Purpose", "Where in the code", "Configuration", "How it is used",
                        "Failure behaviour", "Testing and sandbox"]
# (doc, docs it must link)
CROSS_LINKS = [
    ("runbook.md", ["environment.md"]),
    ("environment.md", ["integrations/"]),
    ("architecture.md", ["data-model.md", "integrations/"]),
]
ENV_FILES = [".env.example", ".env.template"]
BOOST_BLOCK = re.compile(r"<laravel-boost-guidelines>.*?</laravel-boost-guidelines>", re.S)


def docs_dir(repo: Path) -> Path:
    for name in ("docs", "documentation"):
        if (repo / name).is_dir():
            return repo / name
    return repo / "docs"


def is_client(repo: Path) -> bool:
    pubspec = repo / "pubspec.yaml"
    if pubspec.is_file() and "flutter:" in pubspec.read_text(errors="ignore"):
        return True
    if (repo / "angular.json").is_file():
        return True
    pkg = repo / "package.json"
    if pkg.is_file():
        try:
            deps = json.loads(pkg.read_text())
        except ValueError:
            return False
        names = {**deps.get("dependencies", {}), **deps.get("devDependencies", {})}
        return any(n in names for n in ("@angular/core", "react", "vue", "svelte"))
    return False


def headings(text: str) -> set:
    return {m.strip().lower() for m in re.findall(r"^##\s+(.+?)\s*$", text, re.M)}


def missing_headings(path: Path, required: list) -> list:
    have = headings(path.read_text(errors="ignore"))
    return [h for h in required if not any(x.startswith(h.lower()) for x in have)]


def env_keys(path: Path) -> list:
    """Keys in an env file, each with whether a comment sits directly above it."""
    out, prev_comment = [], False
    for line in path.read_text(errors="ignore").splitlines():
        s = line.strip()
        m = re.match(r"(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=", s)
        if m:
            out.append((m.group(1), prev_comment))
            prev_comment = False
        else:
            prev_comment = s.startswith("#") or (prev_comment and s == "")
    return out


def audit(repo: Path, client: bool, hub: bool) -> list:
    problems = []
    docs = docs_dir(repo)
    rel = docs.name

    for name, limit in (("AGENTS.md", 80), ("CLAUDE.md", 30)):
        f = repo / name
        if not f.is_file():
            problems.append(f"missing {name}")
            continue
        lines = BOOST_BLOCK.sub("", f.read_text(errors="ignore")).strip().splitlines()
        if len(lines) > limit:
            problems.append(f"{name} has {len(lines)} lines (limit {limit}); move detail into docs or rules")
    claude = repo / "CLAUDE.md"
    if claude.is_file() and "@AGENTS.md" not in claude.read_text(errors="ignore"):
        problems.append("CLAUDE.md does not import @AGENTS.md")
    if hub:
        return problems

    readme = repo / "README.md"
    readme_text = readme.read_text(errors="ignore") if readme.is_file() else ""
    if not readme_text:
        problems.append("missing README.md")
    else:
        problems += [f"README.md: missing '## {h}'" for h in missing_headings(readme, README_HEADINGS)]

    required = dict(HEADINGS, **(CLIENT_ONLY if client else {}))
    for name, heads in required.items():
        f = docs / name
        if not f.is_file():
            problems.append(f"missing {rel}/{name}")
            continue
        problems += [f"{rel}/{name}: missing '## {h}'" for h in missing_headings(f, heads)]
        if readme_text and f"{rel}/{name}" not in readme_text:
            problems.append(f"README.md does not link {rel}/{name}")

    for name, targets in CROSS_LINKS + ([("coding-conventions.md", ["ui-standards.md"])] if client else []):
        f = docs / name
        if f.is_file():
            text = f.read_text(errors="ignore")
            problems += [f"{rel}/{name} does not link {t}" for t in targets if t not in text]

    integ = docs / "integrations"
    if integ.is_dir():
        for f in sorted(integ.glob("*.md")):
            if f.name != "README.md":
                problems += [f"{rel}/integrations/{f.name}: missing '## {h}'"
                             for h in missing_headings(f, INTEGRATION_HEADINGS)]

    env_doc = docs / "environment.md"
    env_doc_text = env_doc.read_text(errors="ignore") if env_doc.is_file() else ""
    for env_name in ENV_FILES:
        f = repo / env_name
        if not f.is_file():
            continue
        for key, commented in env_keys(f):
            if not commented:
                problems.append(f"{env_name}: {key} has no comment above it")
            if env_doc_text and key not in env_doc_text:
                problems.append(f"{rel}/environment.md does not document {key}")
    return problems


def main(argv: list) -> int:
    args = [a for a in argv if not a.startswith("--")]
    repo = Path(args[0] if args else ".").resolve()
    hub = "--hub" in argv
    client = True if "--client" in argv else False if "--no-client" in argv else is_client(repo)
    problems = audit(repo, client, hub)
    for p in problems:
        print(p)
    kind = "hub" if hub else ("client" if client else "service")
    print(f"repo-docs: {repo.name} ({kind}) — {len(problems)} finding(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
