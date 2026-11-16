# The repo-docs standard

Every application repo carries the same documentation set. Each doc has one home, the README
indexes all of them, and a change that makes one wrong updates it in the same merge request.

`<docs>` below is the repo's docs folder: `docs/` by default, or the folder the repo already uses
(for example `documentation/`). Never keep two docs folders.

Write every doc from the code, not from memory or a ticket: name the file that proves a claim. What
the code cannot answer is written as an open question (`> **Open question:** …`), never invented.

## The fifteen items

| # | Item | Home | Applies to |
|---|---|---|---|
| 1 | Agent entry point | `AGENTS.md` + `CLAUDE.md` | every repo, and the hub |
| 2 | Project README | `README.md` | every repo |
| 3 | Local setup & runbook | `<docs>/runbook.md` | every repo |
| 4 | Environment variables | `.env.example` / `.env.template` comments + `<docs>/environment.md` | every repo that reads env |
| 5 | Testing guide | `<docs>/testing.md` | every repo |
| 6 | Coding conventions | `<docs>/coding-conventions.md` | every repo |
| 7a | Definition of Done | `<docs>/definition-of-done.md` | every repo |
| 7b | MR guide | `<docs>/merge-requests.md` | every repo |
| 8 | Architecture overview | `<docs>/architecture.md` | every repo |
| 9 | Domain glossary | `<docs>/domains.md` | every repo |
| 10 | Business rules & workflows | `<docs>/business-rules.md` | every repo |
| 11 | Data model | `<docs>/data-model.md` | every repo |
| 12 | API & external integrations | `<docs>/integrations/README.md` + one `<docs>/integrations/<name>.md` per integration | every repo |
| 13 | UI standards (formerly "Frontend conventions") | `<docs>/ui-standards.md` | client repos only (mobile, web) |
| 14 | Known issues & danger zones | `<docs>/known-issues.md` | every repo |
| 15 | Security & data constraints | `<docs>/security.md` | every repo |

Required `##` headings are listed per doc. Add more headings when the repo needs them; a required
heading that does not apply holds one line saying why.

## 1 — Agent entry point: `AGENTS.md` and `CLAUDE.md`

Both stay short so they cost little context. They point; they do not explain.

- `AGENTS.md` (at most 80 lines): what the repo is in two lines, "read `README.md` first", the
  rules folder (`.rules/`, `.ai/guidelines/`, `.claude/rules/` — whatever the repo uses), the
  skills and plugins the repo relies on (names and one line each), and at most seven rules most
  often missed, each linking the doc that explains it.
- `CLAUDE.md` (at most 30 lines outside a tool-generated block): `@AGENTS.md` plus anything only
  Claude needs (plugins to enable, skills folder). Long generated guideline blocks (for example
  Laravel Boost) are moved out of `CLAUDE.md` into a path-scoped `.claude/rules/` file.

## 2 — `README.md`

The structured description of the system. A change to the repo's core systems or structure
updates it. Required headings:

- `## Overview` — what the repo is, who uses it, where it sits in the product.
- `## Tech stack`
- `## Repository structure` — top-level folders and what each holds.
- `## Core systems` — the main modules or subsystems, one line each, linking `architecture.md`.
- `## Quick start` — three to five commands, then "full guide: `<docs>/runbook.md`".
- `## Documentation` — a table linking every doc in this standard (items 3–15).

## 3 — `<docs>/runbook.md`

The most important doc: every way to run, debug, ship and recover the repo. Required headings:

- `## Prerequisites` — tools and versions.
- `## Local setup` — clone to first run, including env (`environment.md`), database, seed data,
  generated code, certificates.
- `## Run` — every way to run it (native, Docker, flavours, against which backend).
- `## Debug` — debugger, logs, inspecting state, common local failures and their fix.
- `## Environments` — table: environment, URL/host, branch or tag that deploys it, config source.
- `## Deploy` — the pipeline stages and what triggers each deploy.
- `## Rollback` — how to return each environment to the previous release.
- `## Logs and monitoring` — where logs, errors and metrics are for each environment.
- `## Incidents` — symptom → first check → fix, for the failures that have happened before.

## 4 — Environment variables

- Every key in `.env.example` / `.env.template` (and each `--dart-define` or build-time variable)
  has a comment line directly above it saying what it does and why it is needed.
- `<docs>/environment.md`, required headings:
  - `## Variables` — table: key, purpose, required, example/default, environments that set it,
    secret (yes/no), where the code reads it.
  - `## How to add a variable` — env example file, this doc, CI/CD variables, and the
    integration doc when the key belongs to an integration.
- Linked from `README.md` and `runbook.md`. Integration keys link their `integrations/<name>.md`.

## 5 — `<docs>/testing.md`

Everything an agent or developer needs to test locally before pushing. Required headings:

- `## Test types` — each kind (unit, feature, widget, golden, e2e, static analysis), what it
  covers, where it lives.
- `## Run tests locally` — every command, including a single test, a single file, coverage.
- `## Write a test` — conventions, helpers, fixtures, test data (made-up data only).
- `## Before you push` — the exact checklist to run before an MR.
- `## Tests in the pipeline` — which CI job runs which tests, and how to add a test job.

## 6 — `<docs>/coding-conventions.md`

Required headings:

- `## AI rules, skills and plugins` — pointers only: one line per rules file, skill or plugin,
  with its path or install name. Never copy their content here.
- `## Tooling` — linters, formatters, static analysis, hooks, with their config files.
- `## Team agreements` — every agreement between the people working on the repo, each as a
  `### <title>` with the rule and the reason.

Client repos link `ui-standards.md` from here.

## 7a — `<docs>/definition-of-done.md`

Owned by the product manager. Until the PM fills it, it is a template with every section marked
`TODO (PM)`. Required headings: `## Product`, `## Design`, `## Quality`, `## Release`.

## 7b — `<docs>/merge-requests.md`

Required headings:

- `## Branches` — naming and target branches.
- `## Commits` — the commit message format.
- `## Merge request description` — the template: what changed, the ticket link (every MR has
  one), docs touched (or "docs: none"), tests run with their result, screenshots for UI.
- `## Review` — who reviews what, and the pipeline that must be green.
- `## Stage and production releases` — an MR into a staging or production branch goes through
  the Product Brain release-notes check (`release-notes` skill, and `epic-approval` when the hub
  uses it) when the repo is tracked by a hub.

## 8 — `<docs>/architecture.md`

Required headings:

- `## Overview` — the shape of the system (a diagram is welcome).
- `## Why this architecture` — each major choice and the reason, linking decision records.
- `## Current state` — table: module or layer, what it does, path.
- `## Data flow` — how a request or user action travels through the system.
- `## Related docs` — links to `data-model.md` and `integrations/README.md`.

## 9 — `<docs>/domains.md`

Required headings:

- `## Domains` — table: domain, what it covers, where its code lives in this repo, its glossary
  and domain docs in the hub (when the repo is tracked by a hub; otherwise the glossary itself).
- `## Keeping this current` — adding, removing or renaming a domain or a domain term updates this
  table and the hub in the same change.

## 10 — `<docs>/business-rules.md`

Required headings:

- `## Business rules` — table: rule, where it is implemented (path), the hub doc or decision that
  defines it. A rule with no hub doc is listed under the next heading.
- `## Gaps` — implemented rules not yet documented in the hub.
- `## Keeping this current` — a change that adds or changes a rule updates the hub doc first, then
  this table.

## 11 — `<docs>/data-model.md`

Required headings:

- `## Overview` — the entities this repo stores or exchanges, and their relationships.
- `## Generated models` — what is generated, from what source, and the command (or "none").
- `## Hand-written models` — the models written by hand and where they live.
- `## Storage` — databases, local storage, caches, files.
- `## Related docs` — `architecture.md` and the hub's data model / ERD when there is a hub.

Linked from `README.md` and `architecture.md`.

## 12 — `<docs>/integrations/`

- `integrations/README.md`, required headings:
  - `## API contract` — the conventions between the backend and its clients: base URL and
    versioning, authentication headers and token refresh, the error shape and status codes,
    pagination, ids and dates, how the OpenAPI document is produced and how clients are typed from
    it. The backend owns this; clients link to it and add how they consume it.
  - `## Third-party services` — table: service, purpose, its doc, env keys, owner.
- One `integrations/<name>.md` per third-party service (SMS, email, storage, push, analytics,
  crash reporting, maps, payment, …), with `## Purpose`, `## Where in the code`,
  `## Configuration`, `## How it is used`, `## Failure behaviour`, `## Testing and sandbox`.
- Linked from `README.md`, `architecture.md` and `environment.md`.

## 13 — `<docs>/ui-standards.md` (client repos only)

The client-side decisions applied before a product manager or designer ever sees the result.
Formerly called "Frontend conventions". Required headings:

- `## Design system` — tokens, components, icons; what may and may not be built by hand.
- `## Structure` — screens, widgets/components, state, routing.
- `## Text and direction` — translations, copy source, RTL/LTR.
- `## Accessibility`
- `## Before PM and design review` — the checklist a screen passes before it is shown.

Linked from `README.md` and `coding-conventions.md`.

## 14 — `<docs>/known-issues.md`

Required headings:

- `## How to mark an issue in code` — the comment markers, each on the line above the code:
  - `KNOWN-ISSUE(<TICKET>): <what is wrong> — <fix-later | accepted>`
  - `DANGER: <don't touch X without Y>`
  - `HACK(<TICKET or none>): <why it is there> — <remove when …>`
  Every marker has an entry below, and every entry names its marker's file.
- `## Danger zones` — table: area (paths), what breaks, "don't touch without", owner, guarding test.
- `## Known issues` — table: issue, paths, decision (fix later with ticket / accepted and why).
- `## Hacks and gaps` — workarounds and missing pieces, why they exist, when they can go.

A new hack, gap or danger zone gets its marker and its entry in the same MR; a fix removes both.

## 15 — `<docs>/security.md`

Required headings:

- `## Authentication and sessions` — how users sign in, tokens, refresh, expiry.
- `## Authorization` — roles, policies, tenant or account isolation.
- `## Personal data` — the personal fields stored or shown, and where they must never appear
  (logs, analytics, crash reports, URLs, fixtures).
- `## Secrets` — where each secret comes from; never in source, docs or tickets.
- `## Data retention` — how long data is kept and how it is deleted (an open question until the
  product owner sets it).
- `## Reporting a vulnerability`

A change to any of these updates this doc and gets a second reviewer.

## The hub (Product Brain)

- Item 1 applies to the hub too: a short `AGENTS.md` and `CLAUDE.md`, with the hub's standing
  rules in `.claude/rules/` (path-scoped where they only concern one repo).
- The hub `README.md` links every tracked repo's `README.md`.
- Items 9–11 live in the hub (`vocabulary.md`, `docs/domains/`, `docs/erd/`); the repos'
  `domains.md`, `business-rules.md` and `data-model.md` point to them.
