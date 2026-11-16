# Repo docs stay current (repo-docs plugin)

App repos follow the repo-docs standard: a short `AGENTS.md` + `CLAUDE.md`, and a `README.md`
whose `## Documentation` table links the runbook, environment, testing, coding conventions,
definition of done, MR guide, architecture, domains, business rules, data model, integrations,
UI standards (clients), known issues and security docs.

- **Read before you change.** Open the repo's `README.md` documentation table and the doc that
  covers the area you are touching before writing code.
- **Same change, same MR.** A change that makes any of these docs wrong updates it in the same
  merge request: a new env key (`.env.example` comment + `environment.md`), a new integration
  (`integrations/<name>.md`), a new hack or fragile area (`KNOWN-ISSUE` / `DANGER` / `HACK`
  marker + `known-issues.md`), a structure change (`README.md`, `architecture.md`), a security
  change (`security.md`, second reviewer).
- **The MR says which docs it touched**, or "docs: none".
- **Keep entry points short.** Never grow `CLAUDE.md` or `AGENTS.md` with explanations; add a
  doc or a rules file and link it.
- **Invent nothing.** A doc states what the code does and names the file; what the code cannot
  answer is an open question.

Audit or scaffold the set with the `repo-docs` skill.
