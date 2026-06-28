# 🧠 Product Brain

> **One source of truth for product knowledge — across every repo, for every role, in whatever method your team already uses.**

Product Brain is an open framework for keeping product knowledge — specs, vocabulary, domains, decisions, meeting notes — in one place, connected to your code, and answerable by Claude. It works across multiple repositories, and it's **method-agnostic**: bring your own way of writing specs.

---

## The idea in one picture

```
                 ┌────────────────────────────────────┐
                 │            your hub repo            │   ← single source of truth
                 │  constitution · vocabulary · domains │
                 │  docs/ (specs, decisions, notes, …) │
                 │  graph/ (built over docs + code)    │
                 └───────────────┬────────────────────┘
                         pb sync  │  pulls code, builds one graph
                 ┌───────────────┴───────────────┐
                 ▼                                 ▼
          ┌─────────────┐                  ┌──────────────┐
          │   web-app   │                  │  backend-api │   ← your code repos
          │ (untouched) │                  │  (untouched) │      (nothing added)
          └─────────────┘                  └──────────────┘
```

The **hub** is its own git repo. Your application repos stay exactly as they are — the hub pulls them and builds a single knowledge graph over your docs *and* your code. Ask Claude anything; answers are grounded in real code and real decisions.

---

## Two things, kept separate

| **Product Brain (this framework)** | **Your hub (an instance)** |
|---|---|
| The `brainify` skill + templates + docs | Your team's actual knowledge |
| Tooling | Knowledge only — no skills inside |
| Lives here | Its own git repo, created by running `brainify` |

This separation is what keeps the framework method-neutral and your hub clean.

---

## What problems it solves

| # | Problem | Without Product Brain |
|---|---|---|
| 1 | Codebase questions | Read every file, ask the "code person" |
| 2 | Missing context | Code exists; nobody wrote down why |
| 3 | Vocabulary mismatch | "Session" in the meeting, `Appointment` in the code |
| 4 | Multi-repo knowledge | A question spans two repos and takes days |
| 5 | Institutional knowledge | Lives in people's heads, leaves when they do |

> Precise cross-repo *impact analysis* ("change X here → exactly these files break there") is **not** solved yet — it's a tracked [open problem](docs/multi-repo-architecture.md#13-open-problems-deferred-not-solved-here).

---

## What's in this repo

```
product-brain/
  README.md                         ← you are here
  CLAUDE.md                         ← framework guidance for Claude
  docs/
    multi-repo-architecture.md      ← the full architecture proposal
  skills/
    brainify/SKILL.md               ← the setup & maintenance skill
  templates/                        ← what a hub is made of (method-agnostic)
    brain.config.template.json
    constitution-template.md
    vocabulary-template.md
    domains-template.md
    spec-template.md
    doc-types/                      meeting-note, decision (ADR)
    workflows/                      pm, backend, frontend, qa, onboarding
    hub-claude-md-snippet.md        for a hub's CLAUDE.md
    app-repo-claude-md-snippet.md   optional: makes an app repo hub-aware
  examples/
    todo-app/                       ← a complete tiny hub (todo-api + todo-web)
  website/
    product-brain.html              ← documentation site (open in a browser)
```

---

## Quick start

### 1. Install graphify

```bash
pip install graphifyy        # CLI is `graphify`; no LLM key needed for code
graphify --version
```

### 2. Add the brainify skill to Claude

Claude Code / Cowork auto-discover skills from `~/.claude/skills/` or a project's `.claude/skills/`.
Install the bundled skill there (no restart needed — Claude Code picks it up live):

```bash
bin/install-skill.sh            # personal: ~/.claude/skills (all projects)
bin/install-skill.sh --project  # this repo only: ./.claude/skills
```

### 3. Create your hub

Make a new git repo for your hub and run Claude in it:

> **"Set up product brain"**

`brainify` audits what's there, then walks you through it one step at a time: declaring your repos in `brain.config.json`, writing the required core (constitution, vocabulary), mapping domains from the graph, registering the doc types you want, and building the graph.

### 3. Sync

The `pb` CLI ships in this repo under `bin/pb`. Run it from your hub:

```bash
/path/to/product-brain/bin/pb --hub . sync     # pull the hub + tracked repos, rebuild the graph
/path/to/product-brain/bin/pb --hub . status   # quick health check
/path/to/product-brain/bin/pb --hub . find session booking   # look up code symbols in the graph
pb sync --dry-run                               # preview the plan without running graphify
pb sync --rebuild                               # ignore the cache and rebuild from scratch
```

`pb find <term> [aliases…]` searches the built graph for the code symbols a product term maps to
(e.g. `Appointment — app/Models/Appointment.php`). It's what powers **graph-assisted vocabulary** —
so you never have to recall what something is called in code; the graph tells you.

`pb sync` first pulls the hub's own latest changes (only when it's a clean git repo with an upstream),
then pulls each tracked app repo, then rebuilds the graph **incrementally** — graphify caches by
content hash, so only changed files are re-read. Use `--no-hub-pull` to skip the hub pull.

### Versions & updates

The framework version lives in `VERSION` (currently `0.1.0`) and is stamped into the skill's
frontmatter. Check what you have — and whether your installed skill is current — with:

```bash
pb version          # framework version + commit + whether your installed skill matches
pb version --check  # also fetches and tells you if a newer version is available upstream
```

If you installed the skill in **copy** mode, re-run `bin/install-skill.sh` after pulling updates.
If you used `--link` mode, it always reflects the repo — nothing to re-run.

Tip: add `bin/` to your `PATH` (or symlink `bin/pb` into `/usr/local/bin`) so you can just type `pb sync`.

That's it. Ask Claude about your product, your code, or your decisions.

---

## What a hub is made of

**Required core** (this is what makes a directory a "brain"):

- `constitution.md` — the non-negotiable principles.
- `vocabulary.md` — the glossary tying product language to code.

**Recommended:** `domains.md` — the functional areas, owners, status, and which repos implement them. It's graph-assisted: after a sync, the graph's communities are good candidate domains, so you curate rather than author from scratch.

**Extensible docs** — register any doc types you like in `brain.config.json` (`specs`, `decisions`, `meeting-notes`, `research`, `runbooks`, or your own). Markdown is preferred, and graphify connects it automatically.

**Role workflows** — each role gets a lens over the one source: PM, backend, frontend, QA, onboarding.

---

## Method-agnostic by design

Product Brain prescribes **structure**, not **methodology**. Write specs as plain Markdown, RFCs, Shape Up pitches, Spec Kit, or paste exports from Notion — as long as they live under `docs/specs/`, the hub holds and graphs them. Use the tool of your choice.

---

## Markdown-first, but multi-modal

The graph is built with [graphify](https://pypi.org/project/graphifyy/), which parses code locally via tree-sitter and ingests Markdown, PDFs, `.docx`/`.xlsx`, images, and even meeting recordings (transcribed locally). Markdown is preferred for knowledge you author and maintain — it's diffable and free to ingest — but you can drop in native artifacts (a recorded kickoff, a PDF brief) as source material. JSON is used only for machine config (`brain.config.json`). graphify connects related docs and code automatically via inferred edges and communities, so no manual cross-linking is needed. Ask a question and the agent traverses the graph, returning just the few relevant chunks via each node's `source_file` — which is why the graph can live in the hub, away from the code, and still answer.

---

## Tools used

- **[graphify](https://pypi.org/project/graphifyy/)** (`pip install graphifyy`) — local AST + doc knowledge graph.
- **[Claude](https://claude.ai)** (Cowork or Claude Code) — runs `brainify`, answers graph-grounded questions.
- **Your spec method of choice** — optional; Product Brain doesn't require one.

---

## Full documentation

Open `website/product-brain.html` in a browser, or read `docs/multi-repo-architecture.md` for the architecture and open problems.
