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
| `domains.md` | Domain map (recommended, graph-assisted) |
| `docs/<type>/` | Extensible knowledge: specs, decisions, meeting-notes, … (Markdown-first; PDFs/recordings/images welcome) |
| `workflows/<role>.md` | Role lenses |
| `brain.config.json` | Repos to pull + registered doc types + graph settings |
| `graph/graph.json` | The knowledge graph (built by `pb sync`) |

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

### Recognized commands

- "Set up product brain" / "audit our setup" → run the `brainify` skill.
- "Update me" / "update the brain" / "refresh" / "sync the graph" / "pull the latest" → run `pb sync` (it pulls the hub's latest changes, pulls the tracked app repos, and rebuilds the graph incrementally), then report what changed.
- "Rebuild the graph from scratch" → `pb sync --rebuild`.
- "What domains do we have?" → read `domains.md` / query graph communities.
- "Write a spec for X" → check whether `templates/spec-template.md` exists in this hub. If it does, copy it into `docs/specs/` and fill in the details. If not, ask: "Would you like me to copy the Product Brain recommended templates into `templates/`?" If yes, create the `templates/` folder and scaffold `spec-template.md`, `doc-types/decision-template.md`, and `doc-types/meeting-note-template.md` from the Product Brain framework, then proceed with the spec. If no, create the spec using your team's own format.

### Keeping it fresh

After a meaningful code change, ask whether a doc (decision, spec, vocabulary) needs updating, and whether `pb sync` should run.
