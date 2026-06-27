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

### Canonical vocabulary

Use `vocabulary.md` terms when answering. When code uses a different word than the product term, surface both (e.g. "the `Appointment` model, called 'Session' in product docs"). If a term's code reference changes, update `vocabulary.md`.

### Recognized commands

- "Set up product brain" / "audit our setup" → run the `brainify` skill.
- "Update me" / "update the brain" / "refresh" / "sync the graph" / "pull the latest" → run `pb sync` (it pulls the hub's latest changes, pulls the tracked app repos, and rebuilds the graph incrementally), then report what changed.
- "Rebuild the graph from scratch" → `pb sync --rebuild`.
- "What domains do we have?" → read `domains.md` / query graph communities.
- "Write a spec for X" → copy `templates/spec-template.md` (or our chosen format) into `docs/specs/`.

### Keeping it fresh

After a meaningful code change, ask whether a doc (decision, spec, vocabulary) needs updating, and whether `pb sync` should run.
