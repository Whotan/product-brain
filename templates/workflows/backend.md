# Workflow — Backend engineer

**Your lens:** spec + the API code slice of the graph + constitution.

- **Before building:** read the spec in `docs/specs/` and the relevant `constitution.md` rules.
- **Understand the code:** ask Claude "how does [feature] work in backend-api?" — it traverses the graph and returns the few relevant chunks.
- **Keep knowledge fresh:** after a meaningful change, note it in the right doc (a decision in `docs/decisions/`, an update to the spec) and re-run `pb sync` so the graph reflects reality.
- **Vocabulary:** if you rename a model that appears in `vocabulary.md`, update the term's "in code" reference.
