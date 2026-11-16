---
name: repo-docs
description: "Audit, scaffold, fill or update an app repo's documentation set against the repo-docs standard: a short AGENTS.md + CLAUDE.md, a README that indexes the runbook, environment variables, testing guide, coding conventions, definition of done, MR guide, architecture, domains, business rules, data model, integrations, UI standards, known issues and security docs. Use when the user says 'audit the repo docs', 'document this repo', 'set up the repo docs', 'which docs does this change touch', 'update the docs for this change', or '/repo-docs', and before handing off a change that adds an env key, an integration, a hack or a structural change."
argument-hint: "[audit | write | update] [repo path]"
allowed-tools: [Bash, Read, Write, Edit, Glob, Grep]
---

# repo-docs

## User Input

```text
$ARGUMENTS
```

`${CLAUDE_SKILL_DIR}` is this skill's base directory. The standard — every doc, its path and its
required headings — is `${CLAUDE_SKILL_DIR}/references/standard.md`. Read it before any mode.

The audit script checks presence, required headings, README and cross links, entry-point length
and env-key coverage:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/check_repo_docs.py" <repo> [--client | --no-client] [--hub]
```

It detects client repos (Flutter, Angular, React, Vue, Svelte) by itself; pass the flag to
override. It cannot judge whether a doc is *true* — that is your job in every mode.

## Mode: audit (default)

1. Run the script on the repo. Report its findings grouped by doc.
2. Read each existing doc against the code it describes and list the claims that are stale or
   uncited (a path that no longer exists, a command that fails, an env key nobody reads).
3. Change nothing. End with the list of docs to write or fix.

## Mode: write (scaffold and fill the whole set)

1. Read the repo first: `README.md`, existing entry points and docs, the rules folder, the
   manifest (`composer.json`, `pubspec.yaml`, `package.json`), CI (`.gitlab-ci.yml`,
   `.github/workflows/`), Docker and deploy files, env files, the source tree, tests. When the
   repo is tracked by a Product Brain hub, read the hub's `constitution.md`, `vocabulary.md`,
   `docs/domains/`, `docs/decisions/` and `docs/erd/` — the repo docs link to them, never copy.
2. Reuse what exists: move content from an old doc into its home in the standard and delete
   the old copy (one copy only). An existing docs folder (for example `documentation/`) is the
   `<docs>` folder; do not create a second one.
3. Write each doc with the required headings, from the code. Name the file that proves each
   claim. What the code cannot answer becomes `> **Open question:** …` — never invent a URL,
   owner, retention period or deploy step.
4. Keep `AGENTS.md` and `CLAUDE.md` within their limits. A long tool-generated block in
   `CLAUDE.md` moves to a path-scoped `.claude/rules/` file (see the standard).
5. Comment every key in `.env.example` / `.env.template` on the line above it.
6. Run the script until it reports no findings, then show the diff for review. Never commit
   unless the user says so.

## Mode: update (one change)

1. Read the diff (`git diff <base>...HEAD` and the working tree).
2. Map it to the docs it makes wrong, using the rule list in the plugin's session rule: env keys,
   integrations, markers (`KNOWN-ISSUE` / `DANGER` / `HACK`), structure, security, tests, commands.
3. Update those docs, run the script, and give the MR line: `docs: <list>` or `docs: none`.

## Rules

- Pointers, not copies: AI rules, skills and plugins are linked from `coding-conventions.md` and
  `AGENTS.md` by path or name, never restated.
- Made-up data only in examples. No secret, token or real person's data in any doc.
- `definition-of-done.md` belongs to the product manager: scaffold it as a template marked
  `TODO (PM)` and do not fill it unless the PM provides the content.
