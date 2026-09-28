# CLAUDE.md snippet — for your hub

Paste this into the `CLAUDE.md` at the root of your team's hub repo. It tells Claude how to
use the hub. (This is for the *hub*, not for your application repos — for those, use
`app-repo-claude-md-snippet.md`.)

---

## This is a Product Brain hub

This repo is the single source of truth for product knowledge across our code repos.
It is **method-agnostic** — specs may be written in any format, as long as they live in `docs/specs/`.

### Structure

| File / folder | Purpose |
|---|---|
| `constitution.md` | Non-negotiable principles (required) |
| `vocabulary.md` | Glossary: product ↔ code terms (required, graphed) |
| `DESIGN.md` | Product-level design system: brand tokens + artifact styling (required) |
| `domains.md` | Domain map (recommended, graph-assisted) |
| `docs/knowledge/` | Stable product facts: overview, stakeholders, feature status, metrics, ways of working (required) |
| `docs/<type>/` | Extensible knowledge: specs, decisions, meeting-notes, … (Markdown-first; PDFs/recordings/images welcome) |
| `workflows/<role>.md` | Role lenses |
| `brain.config.json` | Repos to pull + registered doc types + graph settings |
| `brand/brand.css`, `brand/tokens.json` | Compiled brand, built by the `brand-system` skill from `DESIGN.md` (committed, unlike `graph/`) |
| `graph/graph.json` | The knowledge graph (built by `pb sync`) |

### Brand

Every artifact this hub (or its skills) generates — docs pages, dashboards, roadmaps, release
notes, decks — is styled only from the compiled brand: `brand/brand.css` and its `--ds-*`
variables, built by the `brand-system` skill from `DESIGN.md`. `DESIGN.md` is lifted from the
frontend's design source, never invented; if that design system moves, re-run `brand-system` and
re-inline the living artifacts. `check-brand.py` fails any artifact that strays from the compiled
tokens — every artifact skill runs it before publishing.

### Where files go

Keep the hub in this layout. It is what keeps the graph, the docs, and every teammate's Claude in sync.

- **The top level is closed.** It holds only the files and folders above, plus `README.md`,
  `CLAUDE.md`, `templates/`, dot-files (`.claude/`, `.mcp.json`, `.gitignore`, …) and `repos/`.
  Never create another file or folder there.
- **Team knowledge goes in `docs/<type>/`**, and `<type>` must be listed in `doc_types` in
  `brain.config.json`. Pick the closest existing type. A genuinely new kind of doc? Add its type to
  `doc_types` first (tell the user), then create `docs/<type>/`.
- **Scratch goes in `.work/`.** Command output, API/JSON exports, and temp files (linter logs, audit
  dumps, downloaded tickets) go in `.work/`, which is git-ignored. Put the *finding* in a doc; don't
  commit the raw dump.
- **One copy only.** Never duplicate a doc into a second folder. Link to it.
- Follow the naming of files already in the folder.

A check (`pb check`) runs when you finish each reply and lists new files outside this layout. Move
them; don't work around it. If a file is the user's own and you're unsure where it belongs, ask.

### Health checks

- Before a complex codebase question, check `graph/graph.json` exists and is recent. If missing or stale, suggest running `pb sync` (pulls repos, rebuilds the graph) — it takes ~1 min.
- When asked about an area with no doc under `docs/`, say so once and offer to start one.

### Answer codebase questions from the graph first

When a question is about how the code works — where something lives, what an entity is, how features
relate, or what a change might touch — consult the knowledge graph **before** falling back to grep or
directory browsing. The graph already encodes the relationships and established patterns that a raw
text search misses.

- Start with `pb find <term> [aliases...]` to locate the relevant code symbols and their files
  (the product term *and* its code aliases — see `vocabulary.md`), then read the chunks via each
  node's `source_file`.
- Scope to one repo with `pb find <term> --repo <id>` when the question is clearly about a single app
  (see below); use the whole graph for cross-app or end-to-end questions.
- Reach for grep/directory browsing only to confirm a specific line or when the graph genuinely has
  no entry — not as the first move.

If `graph/graph.json` is missing or stale, fall back to grep for this answer but say so once and
suggest `pb sync`.

### What not to commit

`pb sync` manages this automatically, but if you ever run `git status` and see unexpected untracked files:

| Path | Decision |
|---|---|
| `graphify-out/` | **Ignore** — graphify's AST parse cache (regenerable, can be 200 MB+). Covered by `.gitignore`. |
| `repos/` | **Ignore** — cloned source repos; each has its own remote. Covered by `.git/info/exclude`. |
| `.work/` | **Ignore** — temporary directory used during brainify runs. Covered by `.gitignore`. |
| `graph/graph.json`, `graph/sync-report.md` | **Keep** — the knowledge graph and its sync summary. |
| `constitution.md`, `vocabulary.md`, `docs/` | **Keep** — the hub's knowledge. |
| `.mcp.json` | **Keep** — shared tool connections; hosts and URLs only, never a token. |
| `.claude/settings.local.example.json` | **Keep** — the template for personal settings (placeholders only). |
| `.claude/settings.local.json` | **Never commit** — personal tokens. Covered by the hub's `.gitignore`. |

If `graphify-out/` was accidentally committed before this fix, clean it up once with:
```bash
git rm -r --cached graphify-out/
git commit -m "remove accidentally committed graphify cache"
```

### Scope answers to one repo when the question is repo-specific

There is one combined graph for the whole hub (best for cross-repo questions and shared communities).
When a question is clearly about a single app, scope to it for a tighter, more accurate answer:
restrict to graph nodes whose `source_file` is under `repos/<id>/…`, plus the shared docs
(`constitution.md`, `vocabulary.md`, `domains.md`, `docs/`). For symbol lookups, use
`pb find <term> --repo <id>`. Use the whole graph for cross-app or "how does this work end to end"
questions.

### Canonical vocabulary

Use `vocabulary.md` terms when answering. When code uses a different word than the product term, surface both (e.g. "the `Appointment` model, called 'Session' in product docs"). If a term's code reference changes, update `vocabulary.md`.

### Connecting tools: tokens are a fallback

"Set up my connections" / "connect Jira" / "`/mcp` shows a server as failed" → run the
`connect-tools` skill. It checks **presence only** — never read, print or copy a token value, and
never ask the user to paste one into the chat.

### Recognized commands

- "Set up product brain" / "audit our setup" → run the `brainify` skill.
- "Update me" / "update the brain" / "refresh" / "sync the graph" / "pull the latest" → run `pb sync` (it pulls the hub's latest changes, pulls the tracked app repos, and rebuilds the graph incrementally), then report what changed.
- "Rebuild the graph from scratch" → `pb sync --rebuild`.
- "Update Product Brain" / "upgrade the tooling" → run `pb version --check`, tell the user to run `/plugin marketplace update product-brain` then `/reload-plugins`, then `pb sync` and the `brainify` audit to turn on anything new. If `pb version` names a personal skill or an old `pb` path, point that out as the likely shadowing copy and suggest removing it.
- "Set up my connections" → the `connect-tools` skill.
- "Check SonarQube on MR !<n>" → follow `docs/runbooks/check-sonarqube-on-mr.md` if the hub has it, otherwise the `review-mr` skill (git-workflow plugin).
- "What domains do we have?" → read `domains.md` / query graph communities.
- "Tidy the hub" / "check the layout" → run `pb check`, then propose where each listed file should go (move nothing until the user agrees).
- "Create the knowledge docs" → the `brainify` skill's Phase G2: draft the missing `docs/knowledge/` files (overview, stakeholders, feature-status, metrics, ways-of-working) from what the hub already knows, then ask only for the gaps.
- "Write a spec for X" → check whether `templates/spec-template.md` exists in this hub. If it does, copy it into `docs/specs/` and fill in the details. If not, ask: "Would you like me to copy the Product Brain recommended templates into `templates/`?" If yes, create the `templates/` folder and scaffold `spec-template.md`, `doc-types/decision-template.md`, and `doc-types/meeting-note-template.md` from the Product Brain framework, then proceed with the spec. If no, create the spec using your team's own format.

### Keeping it fresh

After a meaningful code change, ask whether a doc (decision, spec, vocabulary) needs updating, and whether `pb sync` should run.
