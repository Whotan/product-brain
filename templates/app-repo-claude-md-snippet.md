# CLAUDE.md snippet — for an application repo

The normal setup is to develop **inside the hub** (`<hub>/repos/<id>`), where the hub's own
`CLAUDE.md`, specs, vocabulary, and graph are already alongside your code. Use this snippet only if
some developers keep a **separate checkout outside the hub** and still want their in-repo Claude
session to use the hub.

Paste it into that app repo's `CLAUDE.md`. It's **optional** and pure guidance — no config, no
dependency, nothing that breaks if the hub moves. Point the path at where the hub is cloned.

---

## Product knowledge lives in the hub

This repo is one of several covered by a Product Brain **hub** — the single source of truth for
product specs, vocabulary, domains, and decisions.

- **Hub:** `git@github.com:example/todo-brain.git` (clone alongside this repo, or browse on the host)
- **Local checkout (if present):** `../todo-brain/`

### Use the hub before answering

Before answering a non-trivial question about *what* this code should do or *why* it exists:

1. **Check the hub's vocabulary** (`vocabulary.md`) so you use the product's real names. When this
   repo's code uses a different word than the product term, surface both
   (e.g. "`TaskList` model — called a 'List' in the product").
2. **Read the relevant spec** under the hub's `docs/specs/` for the feature you're touching, and the
   matching domain in `domains.md`.
3. **Respect the hub's `constitution.md`** — its principles override local habits.
4. **Prefer the hub's graph** for cross-repo questions ("how does X work end to end?"): the hub's
   `graph/graph.json` already spans this repo and its siblings. If it's stale, suggest `pb sync`.

### Keep the hub honest

After a change that renames a model/component listed in the hub's vocabulary, or that alters
behaviour described in a spec, note that the hub needs an update (vocabulary entry, spec, or a new
decision record). Don't duplicate specs or vocabulary *into* this repo — the hub is the one source.

> If no hub checkout is available and you can't reach it, proceed normally and mention that
> hub-grounded answers would be more accurate with the hub present.
