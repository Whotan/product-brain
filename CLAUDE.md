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
| Setup/maintenance skill | `skills/brainify/SKILL.md` |
| Hub templates | `templates/` |
| Architecture & open problems | `docs/multi-repo-architecture.md` |
| Documentation site | `website/product-brain.html` |

## What a hub looks like (what the templates build)

Required core: `constitution.md`, `vocabulary.md`. Recommended (graph-assisted): `domains.md`.
Plus: `brain.config.json` (repos + doc types), `docs/<type>/` (extensible), `workflows/<role>.md`, `graph/` (built by `pb sync`).

## The graph

`pb sync` pulls each repo from `brain.config.json` into a **visible `repos/`** folder, then runs
graphify once over the hub, producing a single `graph/graph.json`. `repos/` and `graph/` are kept
out of Git via `.git/info/exclude` (not a tracked `.gitignore`, because graphify honors `.gitignore`
and would otherwise skip the clones); a managed `.graphifyignore` makes graphify skip its own
output while still reading `repos/`. Querying returns chunks via each node's `source_file`.

## Deferred — open problems (do not present as solved)

Cross-repo linking adapters, ripple/impact analysis, CI-push freshness, and a vocabulary↔graph
linter are tracked in `docs/multi-repo-architecture.md` §13. Soft co-location via graph communities
is the interim answer for cross-repo questions.

## When working on this repo

- Keep the README, the website, the skill, and the architecture doc consistent with each other.
- After any change, check nothing reintroduces `.specify/`, a Spec Kit dependency, or per-app-repo config.
