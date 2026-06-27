# CLAUDE.md Snippet — Product Brain

Copy the section below into your project's `CLAUDE.md`. It gives Claude permanent awareness
of the framework and tells it when to check health, suggest next steps, and bridge vocabulary.

---

## Product Brain

This project uses the Product Brain framework. As Claude, follow these rules:

### Framework health checks

Before answering a complex codebase question, check if `graphify-out/graph.json` exists and is recent (< 7 days). If not:
- Missing: suggest building it first — "The knowledge graph isn't built. It takes ~1 min. Build it now?"
- Stale: mention it — "The graph is X days old — consider rebuilding for an accurate answer."

When discussing a feature with no spec in `specs/`, mention it once per session: "No spec exists for [area] yet — want me to draft one with speckit?"

### Next-step awareness

After any framework action, suggest the logical next step:
- After a spec → suggest `speckit-clarify` or `speckit-plan`
- After a plan → suggest `speckit-tasks`
- After tasks → suggest implementation
- After implementation → suggest `speckit-converge` to check for drift
- After any code change → ask if CHANGELOG.md and vocabulary.json need updating

### Recognized commands

- "Set up product brain" / "walk me through setup" → run `.specify/skills/brainify/SKILL.md`
- "What's missing from our setup?" → run audit (bash checks for all framework components)
- "What should I do next?" → suggest highest-priority missing framework component
- "Build the graph" → `graphify app/ --out graphify-out` (code-only, no LLM key needed)
- "Rebuild the graph" → delete `graphify-out/` first, then rebuild
- "Write a spec for X" → use speckit-specify
- "What domains does this product have?" → query graph communities from `graphify-out/graph.json`
- "Check for drift" → use speckit-converge on the active spec

### Canonical vocabulary

Always use `.specify/vocabulary.json` terms when answering questions. When code uses a different term than the product/user-facing term, surface both: "This is the `Appointment` model (called 'Session' in product docs)."

### Framework file map

| Purpose | File |
|---------|------|
| Codebase knowledge graph | `graphify-out/graph.json` |
| Project constitution | `.specify/memory/constitution.md` |
| Vocabulary synonyms | `.specify/vocabulary.json` |
| Active feature spec | `specs/NNN-name/spec.md` |
| Active feature tracker | `.specify/feature.json` |
| Setup skill | `.specify/skills/brainify/SKILL.md` |

---

*Template source: `.specify/templates/claude-md-snippet.md`*
*Framework: Product Brain — see product-brain.html for full documentation*
