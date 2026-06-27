---
name: brainify
description: Set up, refresh, and maintain a Product Brain hub — a single, method-agnostic source of truth for product knowledge across one or more code repos. Use when the user says "set up product brain", "brainify", "create a hub", "audit our setup", "what's missing from our brain", "what should I do next", or wants to refresh/update the brain — e.g. "update me", "update the brain", "refresh the brain", "sync the graph", "rebuild the graph", "pull the latest" — in a Product Brain context.
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

One sentence: "Auditing this Product Brain hub — checking the required core, config, doc types, and graph freshness." Don't lecture about the framework.

Determine whether you're operating **on an existing hub** (a `brain.config.json` is present) or **creating a new one**.

---

## Quick action — refresh / update the brain

If the user just wants to **update or refresh** (phrases like "update me", "update the brain",
"refresh", "sync the graph", "pull the latest"), don't run the whole setup flow — just do the
refresh **for them** and report the result:

1. Run `pb sync` from the hub (use `bin/pb --hub <hub> sync`). It (a) pulls the hub's own latest
   changes, (b) pulls each tracked app repo, and (c) rebuilds the graph incrementally using the
   graphify cache, so it's fast.
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
  `command -v python3 pip3 git graphify`. If `graphify` is missing, install it for them
  (`pip install graphifyy --break-system-packages`). If Python/pip itself is missing, tell them in
  one friendly sentence what to install (or that a teammate can), and offer to continue with
  everything that doesn't need it.
- **The one thing that may need a technical teammate, once:** creating the hub repository on a host
  (GitHub/GitLab) and signing in the first time (SSH keys / auth). If that's not set up, you can
  still create the hub as a local folder and do everything else; note that pushing to a shared host
  is a one-time setup a teammate can help with.
- **After setup, there are no commands to learn.** The user just talks to you. Make that explicit:
  "From here on, you don't need any commands — just ask me questions."

---

## Step 1 — Audit

Run these checks in a single bash call. The hub root is the current directory.

```bash
# Required core
test -f constitution.md && echo "constitution: PRESENT ($(wc -l < constitution.md) lines)" || echo "constitution: MISSING"
test -f vocabulary.md   && echo "vocabulary: PRESENT"  || echo "vocabulary: MISSING"

# Recommended
test -f domains.md      && echo "domains: PRESENT ($(wc -l < domains.md) lines)" || echo "domains: ABSENT (recommended)"

# Config
test -f brain.config.json && echo "config: PRESENT" || echo "config: MISSING"

# Doc types present
test -d docs && echo "doc types: $(ls -1 docs 2>/dev/null | tr '\n' ' ')" || echo "docs/: MISSING"

# Graph + freshness
if [ -f graph/graph.json ]; then
  AGE=$(( ( $(date +%s) - $(stat -f %m graph/graph.json 2>/dev/null || stat -c %Y graph/graph.json) ) / 86400 ))
  echo "graph: PRESENT (${AGE} days old)"
else
  echo "graph: MISSING"
fi

# graphify installed?
pip show graphifyy 2>/dev/null | grep "^Version" || echo "graphify: NOT_INSTALLED"
```

---

## Step 2 — Report

Render a compact table with ✅ / ⚠️ / ❌ and a one-line note each:

| Layer | Component | Status |
|---|---|---|
| Required | `constitution.md` | ✅/⚠️/❌ |
| Required | `vocabulary.md` | ✅/❌ |
| Recommended | `domains.md` (graph-assisted) | ✅/⚠️/➖ |
| Config | `brain.config.json` | ✅/❌ |
| Docs | registered doc types populated | ✅/⚠️/❌ |
| Graph | `graph/graph.json` built & fresh (<7d) | ✅/⚠️/❌ |
| Tool | graphify installed | ✅/❌ |

Rules: ✅ present & healthy · ⚠️ present but thin/stale · ❌ missing (required) · ➖ absent (recommended only). Follow with a **Priority gaps** list ordered by the sequence below; treat missing required items first. One gap at a time.

---

## Setup sequence

```
A → Stand up the hub repo + brain.config.json
B → Install graphify
C → Write the required core (constitution, vocabulary)
D → Register doc types and seed docs
E → First pb sync (build the graph)
F → Map domains (graph-assisted, recommended)
G → Add the CLAUDE.md snippet(s)
H → Write role workflows
```

---

### Phase A — Stand up the hub

If there's no `brain.config.json`, this is a new hub. The hub should be **its own git repo** — the single source of truth, with history and review. If the user isn't comfortable with git or hosting, don't block on it: create the hub as a local folder and `git init` it for them now, and note that connecting it to a shared host (GitHub/GitLab) is a one-time step a teammate can do later. Run any `git` commands yourself.

Copy `brain.config.template.json` to `brain.config.json` and fill it in by asking:
1. "What's the hub name?"
2. "Which code repos should it cover? Give each an id, git URL, and source dir(s) (e.g. `app/`, `src/`)."
3. "Which doc types do you want? Defaults: specs, decisions, meeting-notes, research, runbooks. Add your own freely."

Create `docs/<type>/` for each registered type, plus `graph/` and a `.gitignore` ignoring `.work/`.

### Phase B — Install graphify

Run this **for** the user (don't ask them to). First confirm Python/pip exist
(`command -v python3 pip3`); if they don't, tell the user in one sentence what to install or that a
teammate can, and continue with steps that don't need it.

```bash
pip install graphifyy --break-system-packages && graphify --version
```

### Phase C — Write the required core

Interview, then write. Ask one question at a time; write nothing until a section's questions are answered.

**Constitution** (from `constitution-template.md`): the 2–4 non-negotiable rules, plus any per-repo differences (test conventions, API patterns). Principles, not bureaucracy.

**Vocabulary** (from `vocabulary-template.md`): the keystone. For each core concept capture the product term, definition, aliases, and what it's called in each repo's code. Markdown only — graphify connects these terms to the code and docs automatically; no manual links are needed.

Present each draft; iterate until approved before moving on.

### Phase D — Register doc types & seed docs

Confirm the doc types in `brain.config.json`. Offer the shipped templates (`spec-template.md`, `doc-types/meeting-note-template.md`, `doc-types/decision-template.md`) but make clear teams can use any format. Knowledge the team authors goes in as Markdown under `docs/<type>/`; native artifacts (a recorded call, a PDF brief) can be dropped in as-is and graphify will ingest them.

### Phase E — First `pb sync`

`pb sync` builds one graph over the hub docs + the pulled code repos:

```bash
# 1. pull the hub's own latest changes (safe: only if git repo + upstream + clean tree)
# 2. pull/refresh each tracked repo from brain.config.json into .work/repos/<id>
# 3. run graphify over a workspace = { constitution.md, vocabulary.md, domains.md, docs/**, .work/repos/** }
# 4. write graph/graph.json + graph/GRAPH_REPORT.md
```

If a `pb` CLI isn't available yet, perform the steps directly: clone/pull each repo into `.work/repos/<id>`, then run graphify over the assembled paths into `graph/`. Report node/edge counts, communities, and thin areas. Keep `.work/` so `source_file` chunk lookups keep working.

**Re-syncs are cheap.** graphify fingerprints every file by content hash and caches results under
`graph/cache/`, so a later `pb sync` only re-reads what changed — never delete `graph/cache/`
between runs. The first sync costs the most; routine refreshes are fast. Use `pb sync --rebuild`
only when you deliberately want a full rebuild. Run `pb sync` yourself for the user, and suggest
scheduling it (e.g. nightly) so the graph stays fresh with no one having to remember.

### Phase F — Map domains (recommended, graph-assisted)

Domains aren't required, and they're partly derivable. After the first sync, read the graph's Leiden communities and propose them as candidate domains. Then use `domains-template.md` to capture, per area: responsibility, owner, status, repos, core features, and key terms. If there's no graph yet, ask the user to name the main functional areas.

### Phase G — Add the CLAUDE.md snippet(s)

Append `hub-claude-md-snippet.md` to the hub's `CLAUDE.md`. Optionally, offer to add `app-repo-claude-md-snippet.md` to each application repo so in-repo Claude sessions consult the hub — it's the only (optional, dependency-free) thing ever added to an app repo. Registration itself lives only in `brain.config.json`.

### Phase H — Role workflows

Offer `workflows/<role>.md` for the roles the team has (pm, backend, frontend, qa, onboarding). Each is a lens over the one source, not a copy.

---

## Completion summary

```
✅ Product Brain hub — status
Required core  ✅ constitution / vocabulary
Domains        ✅ N domains (graph-assisted)   [or ➖ not mapped yet]
Config         ✅ brain.config.json (N repos, M doc types)
Graph          ✅ built (NNN nodes) — Xd old
Workflows      ✅ K roles
Next: [highest-value next action]
```

---

## "What should I do next?" (lightweight re-audit)

| Condition | Suggestion |
|---|---|
| Config missing | "Create `brain.config.json` — declare your repos and doc types." |
| constitution / vocabulary missing | "Write the missing required file — it's what makes this a brain." |
| Graph missing | "Run `pb sync` to build the graph." |
| Graph > 7 days | "Re-run `pb sync` — the code may have drifted." |
| No domains, has graph | "Map domains from the graph's communities (recommended)." |
| Doc type registered but empty | "Seed the first doc for [type]." |
| No workflows | "Add role workflows so each role has a lens." |
| All green | "Keep it fresh: `pb sync` on a schedule; record decisions as they happen." |

---

## Deferred (don't attempt here — they are open problems)

- **Cross-repo linking adapters** (wiring web↔api graphs via their contract).
- **Ripple / impact analysis** across repos. Soft co-location via graph communities is the interim answer.
- **CI-push freshness** and a **machine vocabulary index / linter** (a structured `vocabulary.json` would be (re)introduced only when such tooling needs it).

If asked for these, explain they're tracked as open problems, not yet implemented.
