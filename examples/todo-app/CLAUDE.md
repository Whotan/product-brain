# todo-brain

This is a Product Brain **hub** — the single source of truth for the Todo product, covering the
`todo-api` and `todo-web` repos. It is method-agnostic: specs are plain Markdown under `docs/specs/`.

See `../../templates/hub-claude-md-snippet.md` for the full set of rules a hub's CLAUDE.md carries
(health checks, vocabulary usage, recognized commands). This example keeps it short.

- Required core: `constitution.md`, `vocabulary.md`. `domains.md` is recommended (graph-assisted).
- Docs: `docs/specs/`, `docs/decisions/`, `docs/meeting-notes/`.
- Build the graph with `pb sync` (pulls todo-api + todo-web, graphs them with the docs).
- Use `vocabulary.md` terms when answering; surface both product and code names.
