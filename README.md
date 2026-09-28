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
  .claude-plugin/                   ← makes this repo a Claude Code plugin + marketplace
    plugin.json                     one-command install of the skill + pb CLI
    marketplace.json
  docs/
    getting-started.md              ← no-jargon guide for everyone
    multi-repo-architecture.md      ← the full architecture proposal
  skills/
    brainify/SKILL.md               ← the setup, maintenance & upgrade skill
    connect-tools/SKILL.md          ← "set up my connections": MCP servers, tokens only as a fallback
  plugins/                          ← shared plugins in the same marketplace (see below)
    git-workflow/                   commit + MR rules, commit-message hook, MR scope gate, skills
    guardrails/                     blocks writes that break shared engineering standards
    stack-laravel/ stack-inertia/ stack-angular/ stack-symfony/ stack-flutter/
  tests/                            engine + hook self-checks (node --test tests/*.mjs; python3 tests/test_*.py)
  bin/
    pb                              the hub CLI (on PATH automatically via the plugin)
    package-skill.sh                build the Cowork upload bundle on demand
    install-skill.sh                fallback installer (when you can't use plugins)
  templates/                        ← what a hub is made of (method-agnostic)
    brain.config.template.json
    constitution-template.md
    vocabulary-template.md
    domains-template.md
    spec-template.md
    doc-types/                      meeting-note, decision (ADR)
    workflows/                      pm, backend, frontend, qa, onboarding
    hub-claude-md-snippet.md        for a hub's CLAUDE.md
    hub-readme-template.md          the hub README (non-technical, Windows/macOS/Linux guide)
    hub-settings.template.json      the hub's .claude/settings.json (plugins, UTF-8, read-only perms)
    hub-mcp.template.json           the hub's .mcp.json (hosts only, no secrets)
    hub-settings.local.example.json template for personal tokens (fallback only)
    runbooks/                       check-sonarqube-on-mr
    app-repo-claude-md-snippet.md   optional: makes an app repo hub-aware
  examples/
    todo-app/                       ← a complete tiny hub (todo-api + todo-web)
  website/
    product-brain.html              ← documentation site (open in a browser)
```

---

## Quick start

### 1. Install the plugin (Claude Code)

Product Brain ships as a **Claude Code plugin**. Installing it adds the `brainify` skill *and* puts
the `pb` CLI on your `PATH` — **no scripts, no PATH editing, no manual copying**. In Claude Code:

```text
/plugin marketplace add Whotan/product-brain
/plugin install product-brain@product-brain
/reload-plugins
```

That's the entire install. (`graphify`, the local graph builder, is installed for you the first time
you set up a hub — see step 2.)

> **Using Cowork instead of Claude Code?** Plugins are a Claude Code feature. For Cowork, add the
> skill to your claude.ai account once: run `bin/package-skill.sh` to build `dist/brainify.skill`,
> then upload it at **claude.ai → Settings → Features**. After that, "set up product brain" works in
> any Cowork chat. (There's no supported way to auto-install a skill mid-session, so this one-time
> account step is required.)
>
> **Can't use plugins at all?** `bin/install-skill.sh` is a fallback that copies the skill into
> `~/.claude/skills` and optionally symlinks `pb`.

### 2. Create your hub — just ask

Open Claude in a new folder for your hub and say:

> **"Set up product brain"**

`brainify` does the technical parts **for you**: it installs `graphify` if it's missing, creates the
hub, and walks you through it one step at a time — declaring your repos in `brain.config.json`,
writing the required core (constitution, vocabulary), mapping domains from the graph, registering the
doc types you want, and building the graph. No git or Python knowledge required (Python just needs to
be present on the machine — the one prerequisite).

### 3. From here on, just talk

There are no commands to learn. Ask questions ("How does checkout work across both apps?"), add
knowledge ("record this decision"), and refresh with **"update the brain."** Under the hood that runs
`pb sync`, but you never have to.

<details>
<summary>The <code>pb</code> commands (for developers who want them)</summary>

With the plugin installed, `pb` is on your `PATH`. Without it, run `python3 <clone>/bin/pb …` — no
PATH edit needed.

```bash
pb sync                          # pull the hub + tracked repos, rebuild the graph
pb adopt ~/dev/backend-api       # move an existing checkout into the hub
pb status                        # quick health check
pb find session                  # look up code symbols in the graph
pb sync --dry-run                # preview without running graphify
pb sync --rebuild                # ignore the cache and rebuild from scratch
```
</details>

`pb adopt <path>` is a one-time migration for developers who already have a repo checked out: it
**moves** that checkout into the hub's `repos/<id>` (keeping history, branches, remote, and
uncommitted work), so there's a single working copy and no drift. After that you develop inside the
hub. See the website's **For developers** guide.

`pb find <term> [aliases…]` searches the built graph for the code symbols a product term maps to
(e.g. `Appointment — app/Models/Appointment.php`). It's what powers **graph-assisted vocabulary** —
so you never have to recall what something is called in code; the graph tells you. Add
`--repo <id>` to scope to one app (e.g. `pb find session --repo backend-api`).

**One combined graph, scoped at query time.** Product Brain keeps a single graph over all repos +
docs — that's what makes cross-app questions and shared communities work. For a focused, accurate
answer about just one app, you *scope* the query (filter to that repo's `source_file` paths) rather
than maintaining a separate graph per repo. Separate-then-merge would actually lose the cross-repo
edges a combined run infers, so it's not the default. (Optional isolated per-repo graphs for very
large/noisy monorepos are noted in the architecture doc's open problems.)

`pb sync` first pulls the hub's own latest changes (only when it's a clean git repo with an upstream),
then pulls each tracked app repo, then rebuilds the graph **incrementally** — graphify caches by
content hash, so only changed files are re-read. Use `--no-hub-pull` to skip the hub pull.

### Upgrading from the script install

Earlier versions installed via `bin/install-skill.sh`, which **copied** the skill into
`~/.claude/skills/brainify` and symlinked `pb` into `~/.local/bin/pb`. If you now install the plugin
on top of that, you'll have **two** brainify skills and **two** `pb`s — and the stale one may win
depending on PATH order. Remove the old install first, then add the plugin. **Your hubs are
untouched** — this only changes how the tooling is installed.

```bash
# 1. Remove the old skill copy/symlink (personal — and project, if you used --project)
rm -rf ~/.claude/skills/brainify
rm -rf ./.claude/skills/brainify        # only if you'd installed with --project

# 2. Remove the old pb symlink so the plugin's pb is the one that runs
rm -f ~/.local/bin/pb
```

Then install the plugin (see [Quick start](#quick-start)) and verify with `pb version` (should run
from the plugin and report up to date) and "set up product brain" (the skill should start its audit).

- If you kept a local clone of this repo **only** to run the installer, you can delete it now — the
  plugin carries everything. Still developing *on the framework*? Keep the clone and `git pull` it.
- The `export PATH=".../.local/bin:…"` line you added to your shell profile is now harmless; leave or
  remove it.
- From here, updates are just `/plugin marketplace update` — no more re-running `install-skill.sh`.

### Versions & updates

The framework version lives in `VERSION` (currently `0.7.0`) and is stamped into the skill's
frontmatter. Check what you have — and whether your installed skill is current — with:

```bash
pb version          # framework version + commit + whether your installed skill matches
pb version --check  # also fetches and tells you if a newer version is available upstream
```

**Plugin (recommended):** update everything — skill *and* `pb` — with `/plugin marketplace update`
in Claude Code. Nothing to re-run.

**Fallback installs:** if you used `bin/install-skill.sh` in copy mode, re-run it after `git pull`;
in `--link` mode (and for the `pb` symlink), a `git pull` in this repo is enough.

### Choose your AI provider (Gemini, Claude, OpenAI, …)

Code and audio/video are processed locally and need no key. Only the document/image pass uses an LLM,
and you choose which one — Product Brain is not tied to Anthropic. Pick a provider per sync or in
`brain.config.json`:

```bash
export GEMINI_API_KEY=your-key       # or GOOGLE_API_KEY
pb sync --provider gemini            # one-off override
```

```json
"graph": { "out": "graph/", "provider": "gemini" }   // persistent, in brain.config.json
```

Supported: `gemini`, `claude`, `openai`, `kimi`, `deepseek`, `ollama` (local), or `auto` (graphify
picks based on whichever key is set). `pb` validates that the chosen provider's key is present before
it does any work, and forces that provider even if other providers' keys are also in your environment.
Keep API keys in environment variables — never commit them to the hub.

That's it. Ask Claude about your product, your code, or your decisions.

---

## Using Product Brain in every Claude surface

"Claude Code" runs in several places, and **they don't share one plugin store.** `/plugin install`
only registers the plugin in the *one* Claude Code CLI you ran it in. To make Product Brain available
everywhere — the terminal, your IDE, the desktop app, and cloud/Cowork sessions — the reliable trick
is to **declare the marketplace in your hub's `.claude/settings.json`** (committed, path-free).
`brainify` writes this for you during setup; here's the file and what each surface does with it.

```json
// <hub>/.claude/settings.json  — commit this; it has no machine paths
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "extraKnownMarketplaces": {
    "product-brain": {
      "source": { "source": "github", "repo": "Whotan/product-brain" },
      "autoUpdate": true
    }
  },
  "enabledPlugins": {
    "product-brain@product-brain": true,
    "git-workflow@product-brain": true,
    "guardrails@product-brain": true
  }
}
```

When anyone opens the hub and trusts the folder, Claude Code offers to install the declared
marketplace + plugin; a `/reload-plugins` (or a new session) activates it. Per surface:

| Surface | How Product Brain gets there | Notes |
|---|---|---|
| **Claude Code CLI** (terminal) | `/plugin marketplace add Whotan/product-brain` → `/plugin install product-brain@product-brain` → `/reload-plugins`. Or just open a hub that has the `.claude/settings.json` above. | The one place `/plugin` fully lives. |
| **VS Code extension** | Open the hub → accept the install prompt. Or type `/plugins` in the extension to add the marketplace via its graphical manager. | Shares the CLI's user-scope `~/.claude/`. If a CLI-installed plugin doesn't show, run **Developer: Reload Window**. |
| **JetBrains extension** | Use the built-in terminal: the same `/plugin` CLI commands, or open a hub with the settings file. | No graphical plugin manager — manage from the terminal. |
| **Claude Desktop app** | Its **Code** tab runs Claude Code — use the desktop plugin browser, or the same `/plugin` commands, or open a hub with the settings file. | Shares `~/.claude/` with the CLI. |
| **Cloud / Claude Code on the web / Cowork** | Commit the `.claude/settings.json` above to the hub — cloud sessions read `enabledPlugins` from it. **For Cowork also** upload the skill to your claude.ai account once (`bin/package-skill.sh` → `dist/brainify.skill` → **claude.ai → Settings → Features**), since a fresh cloud agent needs the `brainify` skill available before it can run setup. | Cloud can't see your local `~/.claude/` — repo-committed config (or the account skill) is the only way in. |

**Why the settings-file approach wins:** it's config-as-code. Every teammate, on every surface, opening
the hub gets the same offer to load Product Brain — no one hand-installs a plugin per machine, and it
travels with the repo into cloud sessions.

> **One caveat, honestly:** that cloud/web/Cowork sessions read `enabledPlugins` from a committed
> `.claude/settings.json` is what the plugin docs describe, but we haven't hard-verified it inside a
> live **Cowork** session yet — the two behave slightly differently. The **guaranteed** Cowork path is
> the account-level skill upload (`bin/package-skill.sh` → `dist/brainify.skill` → claude.ai →
> Settings → Features). Treat the repo-declared marketplace as the documented-but-unconfirmed path for
> Cowork, and confirm it in your own session before relying on it for a non-technical teammate.

---

## Shared rules, skills & stack plugins

The marketplace ships more than `product-brain`. Every plugin below updates the same way — bump
the version here, and every hub that enables it picks the change up on
`/plugin marketplace update product-brain` (or automatically, with auto-update on). No one copies
rules into their repos, and app repos stay untouched: rules load as session context, and
enforcement runs as Claude hooks from the plugin's own folder.

| Plugin | What it gives every session in the hub |
|---|---|
| `git-workflow` | **Rules** (commit-message format `type(scope): [TASK-ID] description`, branch naming, MR gates) loaded at session start. **Hooks:** rejects a malformed `git commit -m` (steps aside when a repo has its own `commit-msg` hook or commitlint), and blocks `glab mr create` / `gh pr create` until the ticket scope has been checked for the current HEAD. **Skills:** `verify-ticket-scope` (diff vs. the ticket's acceptance criteria — Jira, GitLab or GitHub issues), `review-mr` (pipeline, SonarQube, review-bot notes → triage). **Agent:** `sonar-preflight`. |
| `guardrails` | A `PreToolUse` hook that blocks writes breaking shared standards — hardcoded secrets, debug output, unsafe PHP/TS/React/Laravel/Angular/Flutter patterns — only for the stacks each repo actually contains, and only in added code. `guardrail info / staged / range` on PATH for manual checks. |
| `stack-laravel`, `stack-inertia`, `stack-symfony`, `stack-angular`, `stack-flutter` | A conventions skill per stack plus topic rules, read on demand when a change touches that stack — never loaded into every session. |

`brainify` enables `git-workflow` and `guardrails` for new hubs and adds the `stack-*` plugins that
match the repos it finds. On an existing hub, run "audit our setup" — the *Shared plugins* row shows
what's missing — or add the lines to `enabledPlugins` in `.claude/settings.json` yourself.

---

## What a hub is made of

**The hub is your workspace.** Each app is declared in `brain.config.json` with a git `url`, and
`pb sync` clones it into `repos/<id>` as a **full working clone you develop in** — right next to the
constitution, specs, vocabulary, and graph. Because you work on the live code inside the hub, the
graph is always current — no separate copies to drift out of date. Re-syncs pull each clone only when
it's clean (fast-forward), so your uncommitted work is never touched (`--no-repo-pull` to skip
entirely).

Each repo's `src` lists the source folders worth graphing (e.g. `["app/"]`, `["src/"]`); `pb sync`
tells graphify to skip that repo's other top-level entries (migrations, infra, generated docs…) so
the graph stays focused. Use `["."]` (the default for adopted repos) to graph the whole repo.

**Required core** (this is what makes a directory a "brain"):

- `constitution.md` — the non-negotiable principles.
- `vocabulary.md` — the glossary tying product language to code.
- `DESIGN.md` — the product's one design system: brand tokens (colour, type, shape) lifted from the
  frontend's design source, compiled to `brand/` and used to style every artifact the hub generates.

**Recommended:** `domains.md` — the functional areas, owners, status, and which repos implement them. It's graph-assisted: after a sync, the graph's communities are good candidate domains, so you curate rather than author from scratch.

**Product facts** — `docs/knowledge/` (required): the stable context Claude reads first, in five standard files: `overview`, `stakeholders`, `feature-status`, `metrics` and `ways-of-working`. `brainify` drafts them from what the hub already knows and asks only for the gaps; say "create the knowledge docs" to run just that step.

**Extensible docs** — register any doc types you like in `brain.config.json` (`specs`, `decisions`, `meeting-notes`, `research`, `runbooks`, or your own). Markdown is preferred, and graphify connects it automatically. Registering a type is the one way to add a folder: the top level stays closed, scratch goes in `.work/`, and `pb check` (which also runs automatically when Claude finishes a reply) flags anything out of place.

**Role workflows** — each role gets a lens over the one source: PM, backend, frontend, QA, onboarding.

**Made for non-technical teammates, on any OS.** `pb sync` keeps a managed block in the hub's
README current: install steps for Windows, macOS and Linux, everyday prompts, where things go, and
fixes for the usual problems (SSH keys, the Windows Python alias, long paths, UTF-8). It also creates
`docs/<type>/.gitkeep` for every doc type and keeps `.claude/settings.local.json` out of Git.

**Tool connections, tokens only as a fallback.** Say "set up my connections" and the `connect-tools`
skill writes a shared `.mcp.json` (GitLab via `glab mcp serve`, Jira via `mcp-atlassian`, hosts only)
and checks this machine's sign-ins **without ever reading a token** — a token is added only when a
normal login isn't possible, and a user's own same-named MCP server wins over the project's. An
existing hub gets all of this with "upgrade the hub" (brainify asks whether to open an MR).

---

## Using the artifact skills

Four sibling skills turn the hub's knowledge into generated documents, all styled from the one
compiled brand (see `DESIGN.md` above):

| Skill | Scope |
|---|---|
| `brand-system` | Extracts and compiles the product-level `DESIGN.md` into `brand/brand.css` + `brand/tokens.json`, and provides `check-brand.py`, the brand gate every other artifact skill runs before publishing. |
| `delivery-roadmap` | The internal delivery roadmap: one card per feature, a computed timeline, and a conflicts panel — grounded in git, not task lists. It reads a release's headline back out of `release-notes`, but does not write release notes itself. |
| `release-notes` | Owns release notes: a publishable client note (HTML + PDF, one locale) and a team-only internal note, per release tag. |
| `update-product-hub` | The product dashboard: what to do today, what's at risk, what shipped yesterday — re-derived every run from git, the graph, and the other skills' output. |

Invoke one directly as `/product-brain:<name>` (e.g. `/product-brain:release-notes`), or just ask
naturally — "refresh the roadmap", "write release notes for this tag", "what's at risk today" —
and the matching skill triggers on its own description. Full config reference (every
`brain.config.json` key each skill reads, required vs optional, with defaults):
[`docs/artifact-skills.md`](docs/artifact-skills.md).

**A hub-local copy shadows the plugin's.** If a hub still has `.claude/skills/<name>/` for one of
these four (from before the plugin shipped them, or from local development), Claude Code resolves
that copy instead of the plugin's — silently, even after the plugin updates. Once the plugin
version is installed, delete the hub-local copy (`rm -rf .claude/skills/<name>`) so there is only
one version to drift.

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

- **[docs/getting-started.md](docs/getting-started.md)** — a no-jargon walkthrough for everyone (start here if you're not technical).
- **[docs/introduction.md](docs/introduction.md)** — what Product Brain is and why, in plain language.
- **[docs/multi-repo-architecture.md](docs/multi-repo-architecture.md)** — the full architecture and open problems.
- **`website/product-brain.html`** — the documentation site (open in a browser).
