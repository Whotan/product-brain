# CLAUDE.md — Product Brain (framework repo)

This is the **Product Brain framework** repository — the tooling: the `brainify` skill, the hub
templates, the architecture docs, and the website. It is *not* a hub. A team's knowledge lives in a
separate hub repo created by running `brainify`.

> Looking for the snippet to put in a *hub's* `CLAUDE.md`? That's `templates/hub-claude-md-snippet.md` — do not confuse it with this file.

---

## Core principles of the framework

- **Method-agnostic.** Product Brain prescribes structure, not methodology. Never reintroduce a hard dependency on a specific spec tool (e.g. Spec Kit). Specs are just Markdown under a hub's `docs/specs/`, authored however the team likes.
- **Framework ≠ hub.** Tooling (skills, templates) ships here. Knowledge (constitution, vocabulary, domains, docs, graph) lives in a team's hub. Never nest skills inside a hub, and never put team knowledge here.
- **Markdown-first, but multi-modal.** Prefer Markdown for knowledge the team authors and maintains. graphify is multi-modal (Markdown, PDF, docx/xlsx, images, audio/video), so native artifacts like meeting recordings are welcome as source material. JSON is only for machine config (`brain.config.json`). Don't rely on manual cross-links — graphify infers edges and communities; we dropped wikilinks as a convention.
- **App repos stay untouched.** A hub registers repos centrally in `brain.config.json` and pulls them. Don't propose adding config files to application repos.

## Repository map

| Purpose | Path |
|---|---|
| Setup/maintenance/upgrade skill | `skills/brainify/SKILL.md` |
| Tool-connections skill | `skills/connect-tools/SKILL.md` |
| Shared plugins (rules, hooks, skills, stack conventions) | `plugins/<name>/`, listed in `.claude-plugin/marketplace.json` |
| Self-checks | `node --test tests/*.mjs`, `python3 tests/test_git_gate.py`, `python3 tests/test_pb_hub_files.py`, `python3 tests/test_epic_facts.py` |
| Plugin + marketplace manifests (primary install path) | `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` |
| Hub CLI + tooling | `bin/pb`, `bin/package-skill.sh` (Cowork bundle), `bin/install-skill.sh` (fallback) |
| Hub templates | `templates/` |
| Architecture & open problems | `docs/multi-repo-architecture.md` |
| Guides & documentation site | `docs/getting-started.md`, `docs/introduction.md`, `website/product-brain.html` |

**Install is plugin-first.** The repo is a Claude Code plugin (`source: "."`); `/plugin install`
ships the skill and puts `pb` on PATH — no `~/.local/bin` symlink, no PATH edit. `install-skill.sh` is
only a fallback. The `.skill` bundle is generated on demand into `dist/` (gitignored) — never commit
a built skill bundle. Keep `plugin.json`'s `version` in sync with `VERSION`.

## Cutting a release (don't skip the version bump)

`plugin.json` pins a `version`, so **an already-installed plugin only updates when that field
changes** — pushing to `main` alone ships nothing to existing users (a fresh install always gets
`main`, but an update does not). Every release:

1. Commit and push the changes to `main`.
2. **Bump in lockstep:** `VERSION`, `.claude-plugin/plugin.json` `version`, every
   `plugins/*/.claude-plugin/plugin.json` `version`, and the `version:` in
   `skills/brainify/SKILL.md` frontmatter. Use semver (feature → minor, fix → patch). Also update
   the `currently \`x.y.z\`` mention in `README.md`. `python3 tests/test_git_gate.py` fails if any
   plugin manifest is off `VERSION` or a `plugins/` folder is missing from `marketplace.json`.
3. Commit the bump, push, and tell users to run `/plugin marketplace update product-brain` then
   `/reload-plugins` (auto-update users get it in the background after a session starts).

The marketplace **name** is `product-brain` and the plugin **name** is `product-brain`, so the install
ref is `product-brain@product-brain`; the repo path for `/plugin marketplace add Whotan/product-brain`
is separate from the marketplace name. Renaming the marketplace forces existing users to
remove + re-add it (a plain `update` hits a name mismatch), so avoid renames.

## What a hub looks like (what the templates build)

Required core: `constitution.md`, `vocabulary.md`, `DESIGN.md`. Recommended (graph-assisted): `domains.md`.
Plus: `brain.config.json` (repos + doc types), `docs/<type>/` (extensible; `docs/knowledge/` is required), `workflows/<role>.md`, `graph/` (built by `pb sync`),
`.claude/settings.json` (plugins, `PYTHONUTF8`, read-only permissions), and optionally `.mcp.json` +
`.claude/settings.local.example.json` (from the `connect-tools` skill). Tokens live only in the
git-ignored `.claude/settings.local.json` and are a fallback — never put a token or a `${TOKEN}`
placeholder in a committed file, and never have a skill read or print a token value.
The top level is closed: a new kind of content is a new registered doc type, never a new folder.
`pb check` enforces this, and `hooks/hooks.json` runs it as a Stop hook in every session. Keep its
allowlist (`ROOT_FILES` / `ROOT_DIRS` in `bin/pb`) in sync with the layout described in the docs.

## The graph

**The hub is the developer's workspace.** `pb sync` clones each repo from `brain.config.json` into
`repos/<id>` as a **full working clone developers work in directly** (each keeps its own Git remote),
then runs graphify once over the hub, producing a single `graph/graph.json`. Because work happens on
the live code in `repos/`, the graph never drifts from a separate copy. Existing clones are pulled
only when clean (fast-forward), so uncommitted work is never disturbed. `repos/` and `graph/` are kept
out of the hub's Git via `.git/info/exclude` (not a tracked `.gitignore`, because graphify honors
`.gitignore` and would otherwise skip the clones); a managed `.graphifyignore` makes graphify skip its
own output while still reading `repos/`. Querying returns chunks via each node's `source_file`. Never
reintroduce a local-copy/mirror option — it leads to stale code.

## Skill scripts

The `brand-system`, `delivery-roadmap`, `release-notes`, `update-product-hub`, and `hub-portal` skills each ship
Python under `skills/<name>/scripts/`; any future skill's scripts follow the same rules:

- **stdlib-only, Python 3.9+.** Optional third-party packages (`fonttools` + `brotli` for font
  subsetting, `playwright` for browser capture/PDF/render-checks, `PyYAML` for the DESIGN.md
  frontmatter) degrade with a clear message when absent — never a traceback, never a silent
  skip that isn't reported.
- **Find the hub by walking up.** From the current directory (and `--hub <path>` to override),
  walk parents until one contains `brain.config.json`. That's the hub root every relative path in
  config is resolved against.
- **Find sibling skills relative to the script's own path**, not a hardcoded install location:
  `SKILLS = Path(__file__).resolve().parents[2]` → `SKILLS / "brand-system" / "scripts" / "brand.py"`.
  This is what makes the same folder work both hub-local (`.claude/skills/<name>/scripts/`) and
  inside the plugin (`skills/<name>/scripts/`).
- **`sys.dont_write_bytecode = True`** before any local import, so running a script never leaves a
  `__pycache__/` behind in a skill folder (or, worse, in a hub someone else's session then reads a
  stale `.pyc` from).
- **Every checker ships a failing fixture, and it must be re-run whenever the checker changes.**
  `check-brand.py` has `fixtures/off-brand.html` / `off-brand-missing-block.html`, which must fail
  every applicable check; `verify-release-notes.py` has `fixtures/leaky-client-note.html` and
  `fixtures/hollow-internal-note.md`; `verify-roadmap.py` has `--self-test` against `fixtures/`; `hub-portal`'s `build.py` is broken one guard at a time by `tests/test_hub_portal.py`. A
  fixture that starts passing means the checker broke, not that the fixture got better — that has
  happened (a case-insensitive placeholder regex once matched the ordinary word "replace"). Re-run
  every fixture as part of any change to the script that reads it, not just once when it's added.

## Deferred — open problems (do not present as solved)

Cross-repo linking adapters, ripple/impact analysis, CI-push freshness, and a vocabulary↔graph
linter are tracked in `docs/multi-repo-architecture.md` §13. Soft co-location via graph communities
is the interim answer for cross-repo questions.

## Shared plugins

`plugins/` holds generic rules, hooks, skills and stack conventions that hubs enable from this same
marketplace. They must stay **generic** — no company, project, repo or host names; a team's own
conventions belong in its hub. Rules that must always apply are injected by a `SessionStart` hook;
stack rules are read on demand through each stack's skill so they don't cost context everywhere.
Enforcement runs as Claude hooks from `${CLAUDE_PLUGIN_ROOT}` — never install git hooks, CI jobs or
config files into app repos.

## When working on this repo

- Keep the README, the website, the skill, and the architecture doc consistent with each other.
- After any change, check nothing reintroduces `.specify/`, a Spec Kit dependency, or per-app-repo config.
