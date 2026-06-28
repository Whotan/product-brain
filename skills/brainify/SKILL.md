---
name: brainify
version: 0.1.4
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
C → First pb sync — build the graph NOW (later steps query it)
D → Write the constitution
E → Build the vocabulary (graph-assisted — use `pb find`)
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
2. "Which apps should it cover?" For each, get an id and source dir(s) (e.g. `app/`, `src/`), plus **one of**:
   - a **git URL** → recorded as `"url"`; `pb sync` clones it (best for hubs shared across a team), or
   - the **local folder path** if the code is already on this machine → recorded as `"path"`; `pb sync`
     mirrors it into `repos/<id>` with cheap hardlinks. **The working repo is never moved or copied
     destructively.** Prefer this when the user isn't sure of the git URL, the repo is private/auth-heavy,
     or they're non-technical — it avoids cloning and authentication entirely. (A local path is
     machine-specific, so for shared hubs prefer `url`.)
3. "Which doc types do you want? Defaults: specs, decisions, meeting-notes, research, runbooks. Add your own freely."

If the user already has a repo open/checked out, the simplest first step is usually to point at it by
`path` rather than asking for a URL.

Create `docs/<type>/` for each registered type. The pulled apps land in a **visible `repos/`** folder
and the map in `graph/`; `pb sync` keeps both out of Git automatically (via `.git/info/exclude`, so
graphify can still read `repos/`) and writes a managed `.graphifyignore`. Don't add `repos/` to a
tracked `.gitignore` — graphify honors `.gitignore` and would then skip the apps.

### Phase B — Install graphify

Run this **for** the user (don't ask them to). First confirm Python/pip exist
(`command -v python3 pip3`); if they don't, tell the user in one sentence what to install or that a
teammate can, and continue with steps that don't need it.

```bash
pip install graphifyy --break-system-packages && graphify --version
```

### Phase C — First `pb sync` (build the graph first)

Build the graph **now**, before writing vocabulary or domains — those steps depend on it. Run
`pb sync` yourself. It pulls the apps into the visible `repos/` folder and graphs them; code parsing
is free and local, and since there are few/no docs yet, this first build is cheap.

```bash
# pb sync:
# 1. pull the hub's own latest changes (safe: git repo + upstream + clean tree)
# 2. pull/refresh each tracked repo into the visible repos/<id> folder
# 3. keep repos/ and graph/ out of Git (.git/info/exclude) + write .graphifyignore
# 4. run graphify over the hub → graph/graph.json + graph/GRAPH_REPORT.md
```

**Choose the LLM provider.** Only the doc/image pass uses an LLM (code + audio/video are local). Product Brain is provider-agnostic — Gemini, Claude, OpenAI, Kimi, DeepSeek, or local Ollama. Ask the user which they want (or read `graph.provider` from `brain.config.json`). Make sure the matching key is set in the environment — for Gemini, `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) — then run `pb sync --provider <name>` (or set `graph.provider`). **Never** write an API key into the hub or a memory file; it's an environment variable the user/teammate sets.

If a `pb` CLI isn't available, perform the steps directly: clone each repo into `repos/<id>`, exclude `repos/` and `graph/` via `.git/info/exclude`, then run graphify over the hub into `graph/` (graphify auto-detects the provider from the env keys; Gemini has top priority).

**Re-syncs are cheap.** graphify fingerprints every file by content hash and caches results under
`graph/cache/`, so a later `pb sync` only re-reads what changed — never delete `graph/cache/`. Use
`pb sync --rebuild` only for a deliberate full rebuild. Suggest scheduling `pb sync` (e.g. nightly).

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
3. Fill the entry's **In code** line from the confirmed symbols.

Only ask the user to type a code name when the graph genuinely has no match. Write `vocabulary.md`
from the confirmed mappings (Markdown only — no manual links); iterate until approved.

If the graph isn't built yet, build it first (Phase C). Falling back to manual guessing is a last
resort, not the default.

### Phase F — Register doc types & seed docs

Confirm the doc types in `brain.config.json`. Offer the shipped templates (`spec-template.md`, `doc-types/meeting-note-template.md`, `doc-types/decision-template.md`) but make clear teams can use any format. Knowledge the team authors goes in as Markdown under `docs/<type>/`; native artifacts (a recorded call, a PDF brief) can be dropped in as-is and graphify will ingest them.

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
