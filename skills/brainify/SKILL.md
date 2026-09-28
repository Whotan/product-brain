---
name: brainify
version: 0.7.1
description: Set up, refresh, and maintain a Product Brain hub — a single, method-agnostic source of truth for product knowledge across one or more code repos. Use when the user says "set up product brain", "brainify", "create a hub", "audit our setup", "what's missing from our brain", "what should I do next", "upgrade the hub", or wants to refresh/update the brain — e.g. "update me", "update the brain", "refresh the brain", "sync the graph", "rebuild the graph", "pull the latest" — in a Product Brain context.
---

# Skill: Brainify

Sets up and maintains a **Product Brain hub**: a dedicated git repo that holds a team's product
knowledge (constitution, vocabulary, domains, and any docs they choose) and a knowledge graph
built over those docs plus the team's code repos.

Two things to keep straight:

- **The framework** = this skill + the templates that ship with it. It is *tooling*.
- **A hub** = an instance the team owns. It holds *only knowledge*, never skills.

This skill is **method-agnostic**. It never imposes a spec methodology. Teams may write specs as
plain Markdown, RFCs, Shape Up pitches, Spec Kit, or exports from another tool — the skill only
cares that knowledge lives under the hub's `docs/`. Markdown is preferred for knowledge the team
authors and maintains, but graphify is multi-modal, so native artifacts (PDFs, `.docx`, images,
and meeting recordings) are welcome as source material too.

---

## Step 0 — Orient

One sentence: "Auditing this Product Brain hub — checking the required core, config, doc types, layout, and graph freshness." Don't lecture about the framework.

Determine whether you're operating **on an existing hub** (a `brain.config.json` is present) or **creating a new one**.

---

## Quick action — refresh / update the brain

If the user just wants to **update or refresh** (phrases like "update me", "update the brain",
"refresh", "sync the graph", "pull the latest"), don't run the whole setup flow — just do the
refresh **for them** and report the result:

1. Run `pb sync` from the hub (use `bin/pb --hub <hub> sync`). It (a) pulls the hub's own latest
   changes, (b) pulls each tracked app repo, (c) rebuilds the graph incrementally using the
   graphify cache, so it's fast, and (d) creates or refreshes the hub's `README.md` from
   `brain.config.json` (a managed block between `product-brain:managed` markers — it replaces a
   git-host default README but never a hand-written one). Don't hand-author a hub README; edit
   `brain.config.json` or the prose outside the markers instead.
2. If `pb` isn't on PATH, run it via its path in the framework repo, or perform the steps directly.
3. Report in plain language: what was pulled, and the new graph stats (nodes/edges) from
   `graph/sync-report.md`. Then invite the next question.

Use `pb sync --rebuild` only if the user explicitly wants a full rebuild from scratch.

---

## Who runs the commands (important — many users are non-technical)

Assume the user may be a PM or other non-technical person who does **not** know git, does not have
Python/pip installed, and has never handled repo authentication. Do not ask them to run commands
they won't understand. Instead:

- **You (Claude) run the commands for them.** When a step needs `pip`, `graphify`, `pb sync`, or
  `git` (add/commit), run it yourself in the shell and report the result in plain language. Never
  hand a non-technical user a command to paste unless they ask for it.
- **Check the toolbox first, fix gaps quietly.** Before relying on a tool, check it exists:
  `command -v python3 pip3 git graphify`. If `graphify` is missing, install it for them — try in
  order until one works: `pipx install graphifyy`, then `python3 -m pip install --user graphifyy`,
  then `python3 -m pip install graphifyy --break-system-packages`; if all fail, show the real error,
  don't hide it. **Python is the one irreducible prerequisite** (both `pb` and graphify are Python).
  If Python is missing, tell them in one friendly sentence what to install (or that a teammate can),
  and offer to continue with everything that doesn't need it.
- **No API key? That's OK — say so, don't stall.** The graph's doc/image pass uses an LLM key, but
  code parsing is local and free. If no key is set, `pb sync` builds a **code-only** graph and prints
  a note; proceed with it and offer to add a key later for richer doc understanding. Never block setup
  on a key.
- **The one thing that may need a technical teammate, once:** creating the hub repository on a host
  (GitHub/GitLab) and signing in the first time (SSH keys / auth). If that's not set up, you can
  still create the hub as a local folder and do everything else; note that pushing to a shared host
  is a one-time setup a teammate can help with.
- **After setup, there are no commands to learn.** The user just talks to you. Make that explicit:
  "From here on, you don't need any commands — just ask me questions."
- **How to run `pb`.** When the Product Brain plugin is installed, `pb` is already on `PATH` — just
  run `pb …`. If it isn't found, run it by path instead: `python3 <framework>/bin/pb --hub <hub> …`
  (where `<framework>` is this cloned product-brain repo). Never tell the user to edit their `PATH`.

---

## Step 1 — Audit

Run these checks in a single bash call. The hub root is the current directory.

```bash
# Required core
test -f constitution.md && echo "constitution: PRESENT ($(wc -l < constitution.md) lines)" || echo "constitution: MISSING"
test -f vocabulary.md   && echo "vocabulary: PRESENT"  || echo "vocabulary: MISSING"

# Required (brand — every generated artifact must style itself from this)
test -f DESIGN.md && echo "DESIGN.md: PRESENT" || echo "DESIGN.md: MISSING"
if [ -f brand/tokens.json ]; then
  STALE=$(python3 - <<'PY' 2>/dev/null
import json, hashlib, os
try:
    t = json.load(open("brand/tokens.json", encoding="utf-8"))
    digest = t.get("design_sha256")
    actual = hashlib.sha256(open("DESIGN.md", "rb").read()).hexdigest() if os.path.exists("DESIGN.md") else None
    print("stale" if digest and actual and digest != actual else "fresh")
except Exception:
    print("unknown")
PY
)
  echo "brand/tokens.json: PRESENT ($STALE vs DESIGN.md)"
else
  echo "brand/tokens.json: MISSING (run the brand-system skill: \`brand.py extract\` then \`brand.py build\`)"
fi

# Recommended
test -f domains.md      && echo "domains: PRESENT ($(wc -l < domains.md) lines)" || echo "domains: ABSENT (recommended)"

# Config
test -f brain.config.json && echo "config: PRESENT" || echo "config: MISSING"

# Doc types present
test -d docs && echo "doc types: $(ls -1 docs 2>/dev/null | tr '\n' ' ')" || echo "docs/: MISSING"

# Layout — stray top-level files/folders, unregistered docs/ folders, missing required types
pb check | head -30

# Graph + freshness
if [ -f graph/graph.json ]; then
  AGE=$(( ( $(date +%s) - $(stat -f %m graph/graph.json 2>/dev/null || stat -c %Y graph/graph.json) ) / 86400 ))
  echo "graph: PRESENT (${AGE} days old)"
else
  echo "graph: MISSING"
fi

# graphify installed?
pip show graphifyy 2>/dev/null | grep "^Version" || echo "graphify: NOT_INSTALLED"

# Multi-surface: does .claude/settings.json declare the plugin marketplace?
# (this is what makes Product Brain load in VS Code, the desktop app, and cloud/Cowork
# sessions that open the hub — not just the CLI where someone ran /plugin install)
if [ -f .claude/settings.json ] && grep -q "extraKnownMarketplaces" .claude/settings.json; then
  echo "surfaces: PRESENT (marketplace declared in .claude/settings.json)"
else
  echo "surfaces: ABSENT (plugin only reachable where it was installed by hand)"
fi

# Shared plugins: which Product Brain plugins does the hub enable?
echo "plugins: $(grep -o '"[a-z-]*@product-brain"' .claude/settings.json 2>/dev/null | tr '\n' ' ')"

# Cross-OS + connections (the "upgrade" layer)
grep -q PYTHONUTF8 .claude/settings.json 2>/dev/null && echo "utf8: PRESENT" || echo "utf8: ABSENT"
git -c core.excludesFile=/dev/null check-ignore -q .claude/settings.local.json && echo "local settings: IGNORED" || echo "local settings: NOT IGNORED"
test -f .mcp.json && echo "mcp: PRESENT ($(python3 -c "import json;print(','.join(json.load(open('.mcp.json')).get('mcpServers',{})))"))" || echo "mcp: ABSENT"
grep -q '"args": *\["mcp-atlassian"\]' .mcp.json 2>/dev/null && echo "jira launch: OLD (Windows can block it)"
grep -q "product-brain:managed:start" README.md 2>/dev/null && echo "readme: MANAGED" || echo "readme: UNMANAGED"
ls repos/*/sonar-project.properties >/dev/null 2>&1 && { test -f docs/runbooks/check-sonarqube-on-mr.md && echo "sonar runbook: PRESENT" || echo "sonar runbook: ABSENT"; } || echo "sonar: not used"
```

---

## Step 2 — Report

Render a compact table with ✅ / ⚠️ / ❌ and a one-line note each:

| Layer | Component | Status |
|---|---|---|
| Required | `constitution.md` | ✅/⚠️/❌ |
| Required | `vocabulary.md` | ✅/❌ |
| Required | `DESIGN.md` (brand design system) | ✅/❌ |
| Brand | `brand/tokens.json` built & fresh (hash matches `DESIGN.md`) | ✅/⚠️/❌ |
| Recommended | `domains.md` (graph-assisted) | ✅/⚠️/➖ |
| Config | `brain.config.json` | ✅/❌ |
| Docs | registered doc types populated (incl. the required `knowledge`) | ✅/⚠️/❌ |
| Layout | nothing outside the hub layout (`pb check`) | ✅/⚠️ |
| Graph | `graph/graph.json` built & fresh (<7d) | ✅/⚠️/❌ |
| Tool | graphify installed | ✅/❌ |
| Surfaces | `.claude/settings.json` declares the marketplace (loads in IDE/desktop/cloud, not just CLI) | ✅/➖ |
| Shared plugins | `git-workflow`, `guardrails`, and a `stack-*` plugin per stack in `repos/` are enabled | ✅/⚠️/➖ |
| Cross-OS | `PYTHONUTF8` in `.claude/settings.json`; `settings.local.json` ignored by the tracked `.gitignore` | ✅/❌ |
| Connections | `.mcp.json` + `.claude/settings.local.example.json` (run `connect-tools`); ⚠️ if Jira still uses the bare `uvx mcp-atlassian` launch | ✅/⚠️/➖ |
| README | managed block present (non-technical guide kept current by `pb sync`) | ✅/⚠️ |
| Sonar runbook | `docs/runbooks/check-sonarqube-on-mr.md` when any app runs Sonar | ✅/➖ |

Rules: ✅ present & healthy · ⚠️ present but thin/stale · ❌ missing (required) · ➖ absent (recommended only). Follow with a **Priority gaps** list ordered by the sequence below; treat missing required items first. One gap at a time.

---

## Setup sequence

```
A → Stand up the hub repo + brain.config.json
B → Install graphify
C → First pb sync — build the graph NOW (later steps query it)
D → Write the constitution
E → Build the vocabulary (graph-assisted — use `pb find`)
E2 → Set up the brand design system (extract, review, build)
F → Register doc types & seed docs
G → Map domains (graph-assisted)
H → Re-sync to fold the new docs into the graph
I → Add the CLAUDE.md snippet(s)
J → Write role workflows
```

> **Order matters.** Build the graph *before* vocabulary and domains. Both are graph-assisted:
> never ask the user to recall what something is called in code — look it up in the graph.

---

### Phase A — Stand up the hub

If there's no `brain.config.json`, this is a new hub. The hub should be **its own git repo** — the single source of truth, with history and review. If the user isn't comfortable with git or hosting, don't block on it: create the hub as a local folder and `git init` it for them now, and note that connecting it to a shared host (GitHub/GitLab) is a one-time step a teammate can do later. Run any `git` commands yourself.

Copy `brain.config.template.json` to `brain.config.json` and fill it in by asking:
1. "What's the hub name?"
2. "Which apps should it cover?" For each, get an `id`, the git `url`, and source dir(s) (e.g. `app/`, `src/`).
3. "Which doc types do you want? `knowledge` is required (stable product facts). Defaults also include specs, decisions, meeting-notes, research, runbooks. Add your own freely."

**The hub is the developer's workspace.** `pb sync` clones each app into `repos/<id>` as a *full
working clone* — developers do their actual work there, inside the hub, so they sit right next to the
constitution, specs, vocabulary, and the graph, and the graph is always built over the live code (no
copies, no drift). Re-syncs pull each clone only when it's clean (fast-forward), so uncommitted work
is never disturbed. Each repo entry in `brain.config.json` can set `"branch": "<name>"` (which branch
to clone, and to switch a *clean* clone to on re-sync) and `"pull": false` (never auto-pull that
clone — it's still cloned once if missing). Sync never touches a dirty tree, and a branch that has
diverged from its upstream is skipped rather than force-merged; developers reconcile with git when ready.

**Onboarding a developer who already has the code.** Don't make them re-clone or keep a second copy.
Ask: *"Where is your current checkout?"* and run `pb adopt <path>` — it **moves** their existing
checkout into `repos/<id>`, preserving git history, branches, the remote, and uncommitted work, then
registers it in `brain.config.json`. After that there's a single copy (in the hub). Prefer move over
`--copy`; a copy leaves a stale duplicate, which is exactly the drift we avoid. (Moving via `adopt` is
a one-time relocation — that's fine; an ongoing *mirror* of a separate copy is what we never do.)

**Make Product Brain reachable in every surface (important).** Copy `hub-settings.template.json` to
the hub's `.claude/settings.json` (create `.claude/` if needed). This file does two things, and it's
safe to commit (no machine paths):

1. **Declares the plugin marketplace** (`extraKnownMarketplaces` + `enabledPlugins`). A plugin
   installed by hand with `/plugin` only exists in *that one* Claude Code CLI. Declaring it in the
   hub's committed settings is what makes Product Brain load for anyone who opens the hub in **any**
   surface — VS Code/JetBrains, the desktop app, and **cloud/Cowork sessions** — not just the CLI
   where it was installed. When a teammate trusts the hub folder, Claude Code prompts them to install
   the declared marketplace + plugin; then `/reload-plugins` activates it.
2. **Pre-allows the safe, path-free commands** the team runs (`pb sync`, `pb status`, `graphify`,
   read-only `git`) so teammates aren't prompted for each one.
3. **Enables the shared plugins** from the same marketplace: `git-workflow` (commit-message and MR
   rules loaded every session, a commit-message hook, a ticket-scope gate before MR/PR creation) and
   `guardrails` (blocks writes that break shared engineering standards). Then add a `stack-*`
   plugin to `enabledPlugins` for each stack found in the hub's repos — check each `repos/<id>`:

   | Found in a repo | Enable |
   |---|---|
   | `composer.json` requiring `laravel/framework` | `stack-laravel@product-brain` |
   | `composer.json` requiring `inertiajs/inertia-laravel` | `stack-inertia@product-brain` (plus `stack-laravel`) |
   | `composer.json` requiring `symfony/framework-bundle` | `stack-symfony@product-brain` |
   | `package.json` depending on `@angular/core` | `stack-angular@product-brain` |
   | `pubspec.yaml` depending on `flutter` | `stack-flutter@product-brain` |

   Say which ones you enabled and why. If the team already has its own commit format or MR flow,
   ask before enabling `git-workflow` (its commit hook steps aside automatically when a repo has its
   own `commit-msg` hook or commitlint config). On an existing hub, the audit's *Shared plugins* row
   is how you notice these are missing — offer to add them.

Personal approvals still go in the untracked `.claude/settings.local.json`. Tell the user plainly:
"I've set the hub up so Product Brain loads automatically for anyone who opens it — in the terminal,
in VS Code, in the desktop app, or on the web." For **Cowork specifically**, note the one extra option
below (the account-level skill), since a cloud session needs the skill available before it can run me.

Create `docs/<type>/` for each registered type. The pulled apps land in a **visible `repos/`** folder
and the map in `graph/`; `pb sync` keeps both out of Git automatically (via `.git/info/exclude`, so
graphify can still read `repos/`) and writes a managed `.graphifyignore`. Don't add `repos/` to a
tracked `.gitignore` — graphify honors `.gitignore` and would then skip the apps. `pb sync` also
writes tracked `.gitignore` entries for graphify's internal AST cache (`graphify-out/`) and `.work/`
— those are graphify's own output, never source input, so excluding them in `.gitignore` is safe and
shared when the hub is pushed to a remote.

### Phase B — Install graphify

Run this **for** the user (don't ask them to). First confirm Python exists
(`command -v python3`); if it doesn't, tell the user in one sentence what to install or that a
teammate can, and continue with steps that don't need it. Then install graphify, trying each until
one succeeds (environments differ — some block system-wide installs):

```bash
pipx install graphifyy \
  || python3 -m pip install --user graphifyy \
  || python3 -m pip install graphifyy --break-system-packages
graphify --version
```

If all three fail, show the actual error rather than hiding it — it's usually a missing Python/pip or
a locked-down machine a teammate can help with.

### Phase C — First `pb sync` (build the graph first)

Build the graph **now**, before writing vocabulary or domains — those steps depend on it. Run
`pb sync` yourself. It pulls the apps into the visible `repos/` folder and graphs them; code parsing
is free and local, and since there are few/no docs yet, this first build is cheap.

```bash
# pb sync:
# 1. pull the hub's own latest changes (safe: git repo + upstream + clean tree)
# 2. pull/refresh each tracked repo into the visible repos/<id> folder
# 3. keep repos/ and graph/ out of Git (.git/info/exclude) + write .graphifyignore
#    write .gitignore entries for graphify-out/ cache and .work/ (committed, shared)
# 4. run graphify over the hub → graph/graph.json; pb writes graph/sync-report.md
```

**Choose the LLM provider.** Only the doc/image pass uses an LLM (code + audio/video are local). Product Brain is provider-agnostic — Gemini, Claude, OpenAI, Kimi, DeepSeek, or local Ollama. Ask the user which they want (or read `graph.provider` from `brain.config.json`). Make sure the matching key is set in the environment — for Gemini, `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) — then run `pb sync --provider <name>` (or set `graph.provider`). **Never** write an API key into the hub or a memory file; it's an environment variable the user/teammate sets.

**No key yet? Build anyway.** If the user has no key, don't stall the setup: run `pb sync` as-is. It
builds a **code-only** graph (code is parsed locally, free) and records a note in
`graph/sync-report.md`. The vocabulary/domains steps still work off the code symbols; offer to add a
key and re-sync later to fold in document understanding. Only when the user *explicitly picks* a
provider does a missing key stop the run (that's a config mistake worth surfacing).

If a `pb` CLI isn't available, perform the steps directly: clone each repo into `repos/<id>`, exclude `repos/` and `graph/` via `.git/info/exclude`, then run graphify over the hub into `graph/` (graphify auto-detects the provider from the env keys; Gemini has top priority).

**Re-syncs are cheap.** graphify fingerprints every file by content hash and caches results under
`graphify-out/cache/`, so a later `pb sync` only re-reads what changed. Never delete that cache
manually — use `pb sync --rebuild` for a deliberate full rebuild. Suggest scheduling `pb sync` (e.g.
nightly).

### Phase D — Write the constitution

Interview, then write. Ask one question at a time; write nothing until the questions are answered.
From `constitution-template.md`: the 2–4 non-negotiable rules, plus any per-repo differences (test
conventions, API patterns). Principles, not bureaucracy. Present the draft; iterate until approved.

### Phase E — Build the vocabulary (graph-assisted — do NOT guess code names)

The vocabulary is the keystone, and it **must use the graph**. When the user names a concept (and you
both may be unsure what it's called in the code), look it up — don't ask them to recall it and don't
guess:

```bash
pb find <term> [aliases...]     # e.g.  pb find session booking appointment
pb find <term> --code-only      # only code symbols (skip docs)
```

`pb find` searches the built graph and returns candidate code symbols with their files (e.g.
`Appointment — app/Models/Appointment.php`). For each concept:

1. Run `pb find` with the product term **and** its aliases.
2. Show the top candidates and let the user pick the right one(s) per repo, or say "none".
3. Write **What it is** — required. One or two sentences in product language. This is the
   definition; never leave it implicit as prose above the field list.
4. Fill **Also called** — required. For each alias, tag the repo or app where that name is used:
   `term (repo-or-app)`. Different repos often use different names for the same concept; capturing
   which name lives where is the main value of this field. These tags are also critical for
   `pb find` to surface the concept under any of its names.
5. Fill the **In code** line from the confirmed symbols — **select 2–5 representative anchors**
   (typically: main model, main service/action class, main API/UI entry point). Do NOT enumerate
   every repository, middleware, test, or resource class — the graph already indexes all of those.
   The vocabulary is a navigational bridge; exhaustive symbol lists make it an index, which is
   exactly what the graph is for.

Only ask the user to type a code name when the graph genuinely has no match. Write `vocabulary.md`
from the confirmed mappings (Markdown only — no manual links); iterate until approved.

If the graph isn't built yet, build it first (Phase C). Falling back to manual guessing is a last
resort, not the default.

### Phase E2 — Brand design system

Every artifact this hub can generate (roadmap, dashboard, release notes, and anything else styled
as a document) must share one visual identity, so this step is required, not optional, right after
the vocabulary is drafted.

Invoke the `brand-system` skill (`product-brain:brand-system`):

1. **Extract.** It runs `brand.py extract` against the frontend repo(s) registered in
   `brain.config.json` → `design.source` / `design.sources` — never invented, never sampled from a
   screenshot — and drafts the hub-root `DESIGN.md`: brand tokens (colour ramps, semantic colours,
   type, shape, spacing) plus the `artifact` role mapping every generated document uses.
2. **Review with the user.** Show the draft. If two apps disagree on a brand-level token, that
   conflict goes to the user to decide — the extractor never picks a winner on its own.
3. **Build.** Once approved, run `brand.py build` to compile `brand/brand.css` and
   `brand/tokens.json`. From here on, every artifact skill inlines `brand.css` and styles itself
   only from its `--ds-*` variables; `check-brand.py` (run in each artifact skill's verify step)
   fails anything that strays from it.

If the hub has no registered frontend repo to extract from, offer a hand-authored `DESIGN.md`
instead (system font stacks, a small colour ramp, the same `artifact` block) — see
`examples/todo-app/DESIGN.md` for a worked example with no frontend source.

### Phase F — Register doc types & seed docs

Confirm the doc types in `brain.config.json`. Offer the shipped templates (`spec-template.md`, `doc-types/meeting-note-template.md`, `doc-types/decision-template.md`) but make clear teams can use any format. Knowledge the team authors goes in as Markdown under `docs/<type>/`; native artifacts (a recorded call, a PDF brief) can be dropped in as-is and graphify will ingest them.

**`docs/knowledge/` is required.** It holds the stable product facts that aren't rules
(constitution), terms (vocabulary), or areas (domains): what the product is and who it's for,
stakeholders and how they work, feature status, metrics, and ways of working. It's the context
Claude reads first. Offer to seed `docs/knowledge/overview.md` from a short interview.

**The layout is the standard.** The top level is closed (core files, `docs/`, `workflows/`,
`templates/`, dot-files, `repos/`, the graph folder). Every other kind of content becomes a
registered doc type, never a new top-level folder. Scratch and command output go in `.work/`. The
plugin runs `pb check --hook` when Claude finishes each reply, so new files in the wrong place are
caught at once. `pb check` lists everything out of place for a cleanup.

### Phase G — Map domains (recommended, graph-assisted)

Domains aren't required, and they're partly derivable. Read the graph's Leiden communities and propose them as candidate domains; use `pb find` to confirm the key entities per area. Then use `domains-template.md` to capture, per area: responsibility, owner, status, repos, core features, and key terms.

### Phase H — Re-sync

After writing the constitution, vocabulary, and any seeded docs, run `pb sync` again so the new
Markdown is folded into the graph. It's cheap — only the changed files are re-read.

### Phase I — Add the CLAUDE.md snippet(s)

Append `hub-claude-md-snippet.md` to the hub's `CLAUDE.md`. Optionally, offer to add `app-repo-claude-md-snippet.md` to each application repo so in-repo Claude sessions consult the hub — it's the only (optional, dependency-free) thing ever added to an app repo. Registration itself lives only in `brain.config.json`.

### Phase J — Role workflows

Offer `workflows/<role>.md` for the roles the team has (pm, backend, frontend, qa, onboarding). Each is a lens over the one source, not a copy.

---

## Completion summary

```
✅ Product Brain hub — status
Required core  ✅ constitution / vocabulary / DESIGN.md
Brand          ✅ brand/tokens.json built & fresh   [or ⚠️ stale, or ❌ missing]
Domains        ✅ N domains (graph-assisted)   [or ➖ not mapped yet]
Config         ✅ brain.config.json (N repos, M doc types)
Graph          ✅ built (NNN nodes) — Xd old
Workflows      ✅ K roles
Next: [highest-value next action]
```

---

## Upgrade an existing hub

When the audit shows ❌/⚠️/➖ in the *Shared plugins*, *Cross-OS*, *Connections*, *README* or *Sonar
runbook* rows — or the user says "upgrade the hub" — offer this upgrade.

**Ask how to deliver it, every time:** commit on the current branch, or work on a new `hub-upgrade`
branch and open a merge request / pull request. Never commit to `main` directly (it is usually
protected), and never merge the MR yourself.

**Read first:** `brain.config.json`, `README.md`, `CLAUDE.md`, `.claude/settings.json`, `.gitignore`,
the `docs/` folders, and each app's CI (`repos/<id>/.gitlab-ci.yml` or `.github/workflows/`) and
`sonar-project.properties`. Use this hub's own repo ids, hosts and URLs everywhere; ask for any host
you cannot find — never copy values from another hub.

1. **Docs, `.gitignore`, README** — run `pb sync`. It creates `docs/<type>/.gitkeep` for every
   registered doc type, adds `.claude/settings.local.json` to the tracked `.gitignore`, and refreshes
   the README's managed block (the non-technical, cross-OS guide). If the README has no managed
   markers, put the markers in above the team's own prose rather than rewriting it; keep domain
   owners and other hand-written content as they are.
2. **Windows UTF-8** — add `"env": { "PYTHONUTF8": "1" }` to `.claude/settings.json` as a minimal
   insert (don't reformat the file). It covers graphify and older `pb` versions.
3. **Shared plugins and read-only commands** — merge the missing `enabledPlugins` entries (see
   Phase A) and the read-only `glab`/`gh` permissions from `hub-settings.template.json` into
   `.claude/settings.json`, again without reformatting.
4. **Connections** — run the `connect-tools` skill: commit `.mcp.json` and
   `.claude/settings.local.example.json` (no secrets), then run its presence-only check for the
   user on this machine.
5. **Hub `CLAUDE.md`** — add the *What not to commit* rows and the *Connecting tools* section from
   `hub-claude-md-snippet.md` if missing.
6. **Sonar runbook** (only if an app runs Sonar; otherwise skip it and say so) — find the Sonar job
   in each app's pipeline. CI files may `include:` shared templates; read those with
   `glab api "projects/<url-encoded-project>/repository/files/<url-encoded-path>/raw?ref=HEAD"`.
   Note the job name, stage, rules, and whether `sonar.qualitygate.wait=true`. Verify on a real open
   MR: MR → `glab api projects/:id/merge_requests/<iid>/pipelines` → the pipeline's jobs → the Sonar
   job → `glab ci trace <job-id>`; look for `QUALITY GATE STATUS` and the dashboard URL. Write
   `docs/runbooks/check-sonarqube-on-mr.md` from `templates/runbooks/check-sonarqube-on-mr.md` with
   the real values and that example.
7. **Finish** — commit in logical chunks (one per step above). If delivering by MR: push the branch
   and open the MR/PR (`glab mr create` / `gh pr create`). Report the link, what you verified,
   anything skipped and why, and which placeholders the user still has to fill in
   `.claude/settings.local.json` themselves.

---

## Missing programs

The plugin's SessionStart hook (`hooks/check-deps.sh`, plain shell, so it runs even without
Python) warns when something Product Brain needs is missing: `git`, a working `python3`, `node` (for
guardrails), `graphify` in a hub, and each program the hub's `.mcp.json` launches (`glab`, `gh`,
`uvx`). It prints the install command for the user's OS: macOS, Linux, or Windows via Git Bash.
When it reports something, tell the user what each program is for, offer to run the install for
them, and ask first. On Windows, a `python3` that exists but won't run is usually the Microsoft Store
alias. The warning says how to turn it off.

---

## Clean up an older install

Before the plugin, Product Brain was installed by copying the skill into `~/.claude/skills/brainify`
and linking `pb` into `~/.local/bin`. Those copies stay behind after the plugin is installed and
**shadow** it: Claude loads the old brainify, and the old `pb` runs first on PATH, so the user never
sees newer features (shared plugins, `pb check`, this section).

The plugin's SessionStart hook runs `pb version --hook` and lists what it finds. `pb version` prints
the same list. When either reports leftovers:

1. Tell the user in plain words what is old and why it matters. Ask before deleting anything.
2. With their OK, remove the old skill folder (`~/.claude/skills/brainify` or the hub's
   `.claude/skills/brainify`) and the old `pb` link (`which pb`). Leave any old framework checkout
   alone. The user can delete it.
3. Have them run `/reload-plugins` (or restart), then `pb version` again. It should show no warnings.
4. If the hook also said the hub was set up by an older version, run the audit and offer
   **Upgrade an existing hub** above.

---

## "What should I do next?" (lightweight re-audit)

| Condition | Suggestion |
|---|---|
| Config missing | "Create `brain.config.json` — declare your repos and doc types." |
| constitution / vocabulary missing | "Write the missing required file — it's what makes this a brain." |
| `DESIGN.md` missing, or `brand/tokens.json` missing/stale | "Run the brand-system skill to extract/build the brand from your frontend's design source." |
| Graph missing | "Run `pb sync` to build the graph." |
| Graph > 7 days | "Re-run `pb sync` — the code may have drifted." |
| No domains, has graph | "Map domains from the graph's communities (recommended)." |
| Doc type registered but empty | "Seed the first doc for [type]." |
| `knowledge` not registered | "Register the required `knowledge` doc type and move your product facts into `docs/knowledge/`." |
| `pb check` lists files | "Some files are outside the hub layout — I'll propose where each belongs." (Propose; move only once the user agrees.) |
| No workflows | "Add role workflows so each role has a lens." |
| Cross-OS / Connections / README / Sonar runbook rows not ✅ | "Upgrade the hub — cross-OS README, UTF-8, tool connections (I'll ask whether to open an MR)." |
| All green | "Keep it fresh: `pb sync` on a schedule; record decisions as they happen." |

---

## Deferred (don't attempt here — they are open problems)

- **Cross-repo linking adapters** (wiring web↔api graphs via their contract).
- **Ripple / impact analysis** across repos. Soft co-location via graph communities is the interim answer.
- **CI-push freshness** and a **machine vocabulary index / linter** (a structured `vocabulary.json` would be (re)introduced only when such tooling needs it).

If asked for these, explain they're tracked as open problems, not yet implemented.

---

## Artifact skills

Four sibling skills produce the hub's generated documents. Each reads its own `brain.config.json`
key and nothing else is hardcoded — a missing key is a clear error naming the key, never a silent
default.

| Skill | Produces | Reads |
|---|---|---|
| `brand-system` | The hub's `DESIGN.md`, plus compiled `brand/brand.css` + `brand/tokens.json` | `design` |
| `delivery-roadmap` | A git-grounded delivery roadmap (HTML) and its facts JSON | `roadmap` |
| `release-notes` | Per-release client + internal notes (HTML/PDF/Markdown) | `releases` |
| `update-product-hub` | The product dashboard (HTML) and its state JSON | `dashboard` |

Every one of them runs `check-brand.py` (from `brand-system`) in its verify step before it's
considered done — see the "Brand design system" constitution principle.
