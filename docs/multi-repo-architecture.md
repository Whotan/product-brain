# Product Brain — Multi-Repo Knowledge Architecture

> **Status:** Proposal v0.3 (for review)
> **Date:** 2026-06-27
> **Scope:** Restructure Product Brain so that two or more separate code repositories (e.g. a web app and a back-end API) share one institutional brain — a single, method-agnostic source of truth for product knowledge — that serves every role.
>
> **Changes since v0.2:** **dropped wikilinks** as a convention (graphify infers edges and communities, so manual links aren't worth the upkeep); **dropped `vocabulary.json`** — `vocabulary.md` is the single source, and a structured index returns only when a consumer (linter/adapters) needs it; **demoted `domains.md`** from required to recommended + graph-assisted; **clarified Markdown-first ≠ Markdown-only** — graphify is multi-modal, so PDFs, docx, images, and meeting recordings are welcome as source material.
>
> **Changes since v0.1:** dropped the hard dependency on Spec Kit (now method-agnostic); made doc types extensible (e.g. meeting notes); Markdown-first content; clarified the hub is its own git repo; removed the per-app-repo ("spoke") additions; moved the brainify skill out of the hub's data structure; replaced the per-repo merge+adapter model with a single graph over one assembled workspace; **deferred cross-repo linking (adapters) and ripple/impact analysis to Open Problems.**

---

## 1. Context & problem

Product Brain today is **repo-local** and **method-bound**: you copy a `.specify/` folder (Spec Kit's convention) into a repository, build a graph of that repo, and write Spec Kit specs against it. Two things are wrong for our use case.

First, it's tied to one repo. A single feature ("book a session") lives in both the **web-app** and the **backend-api** repos, so the knowledge splits into two folders, two graphs, two drifting vocabularies.

Second, it's tied to one method. Not every team wants Spec Kit. Some use RFCs, some shape work, some keep specs in Notion, some just write Markdown. Product Brain should not force a methodology — it should hold whatever knowledge a team produces and make it queryable.

We want one brain that both repos feed, that is agnostic about how docs are authored, that lets teams add their own document types (meeting notes, ADRs, research, runbooks…), and that every role can query without anything being duplicated.

---

## 2. Goals & non-goals

**Goals**

- **Single source of truth** for product knowledge across repos — not copies per repo.
- **Method-agnostic.** Product Brain prescribes *structure*, not *methodology*. Spec Kit, RFCs, Shape Up, or plain Markdown all fit.
- **Extensible doc types.** A required core, plus any document types a team wants to add (meeting notes, decisions, research…).
- **Every role served** from that one source through role-specific views, not separate documents.
- **Low operational toil** — staying current must not depend on humans remembering to rebuild.
- **No changes forced on the app repos.** Registering a repo happens entirely in the hub.

**Non-goals**

- Not a monorepo migration. The repos stay independent.
- Not a methodology. We don't ship a "right way" to write specs.
- Not a hosted service. The brain is a git repo.
- **Not (yet) cross-repo impact analysis.** Automatic "what breaks if I change X" across repos is explicitly deferred (see §9).

---

## 3. The reframe

Two reframes drive everything below.

> **A. Knowledge becomes its own product.** It stops being a guest inside each code repo and lives in a dedicated **hub repository** — the single source of truth. Code repos are just *sources* the hub reads.

> **B. Product Brain is the tool; the hub is an instance.** The open-source framework (the skill, templates, docs) is separate from any team's actual knowledge. The framework operates *on* a hub; it doesn't live *inside* one.

Reframe B is the answer to "why is the skill under `.specify/`?" — it shouldn't be. See §6.

---

## 4. Two distinct things

| | **Product Brain (the framework)** | **A team's hub (an instance)** |
|---|---|---|
| What it is | The open-source tool: the `brainify` skill, templates, the docs site | A team's actual knowledge: constitution, vocabulary, domains, docs, graph |
| Who ships it | Maintainers (this repository) | Created by a team running `brainify` |
| Form | A Claude plugin / skill bundle | Its own git repo |
| Contains skills? | Yes — that's its whole job | **No.** Pure knowledge + config. |

Keeping these separate is what makes Product Brain method-agnostic and reusable: the framework knows nothing about a specific team's methodology, and a hub carries no tooling.

---

## 5. Hub repository layout

The hub is **its own git repo** (decision §11). It holds a small required core, an extensible `docs/` tree, and the graph output. Everything meant to be *queried as knowledge* is **Markdown**; the only JSON is machine config that Claude reads directly (see §7 for why).

```
acme-brain/                          ← the hub: its own git repo, single source of truth
  brain.config.json                  machine config: which repos to pull, doc types, graph settings
  constitution.md                    principles / non-negotiables        (CORE, required)
  vocabulary.md                      glossary: product term ↔ code term   (CORE, required)
  domains.md                         domain map: area → owner, status, which repos   (recommended, graph-assisted)
  docs/                              extensible, typed knowledge — Markdown-first (multimodal supported)
    specs/                           authored however the team likes (Spec Kit, RFC, plain MD…)
    decisions/                       ADRs
    meeting-notes/                   ← teams add types like this freely
    research/
    runbooks/
    <your-own-type>/                 anything the team registers in brain.config.json
  workflows/                         role playbooks: pm.md, backend.md, frontend.md, qa.md, …
  graph/                             graphify output: graph.json, GRAPH_REPORT.md, graph.html
  repos/                             VISIBLE: pulled clones of the code repos (browsable by devs)
  .graphifyignore                    managed: graphify skips graph/, keeps repos/
```

`repos/` and `graph/` are kept out of Git via `.git/info/exclude` (a local, untracked exclude),
**not** a tracked `.gitignore` — because graphify honors `.gitignore` and would otherwise skip the
clones. They stay visible so developers can open the pulled apps normally.

The **required core** is just two files (`constitution.md`, `vocabulary.md`) — the knowledge that can't be derived from code. `domains.md` is **recommended and graph-assisted** (curate it from the graph's communities after a sync). Everything under `docs/` is optional and extensible. There is **no spec-kit-specific folder and no required methodology**.

The app repos themselves get **nothing added** — see §8.

---

## 6. The skill lives outside the hub

`brainify` (and any future Product Brain skills) is a **standalone Claude skill**, distributed with the framework (as a plugin / skill bundle), **not** placed inside a team's hub and **not** under a `.specify/` directory.

Why:

- It's tooling, not knowledge. A hub should contain only the team's knowledge so it stays clean, diffable, and method-neutral.
- `.specify/` is Spec Kit's namespace. Using it re-couples us to the very dependency we're removing.
- One skill version can operate on many hubs; embedding a copy per hub guarantees drift.

The skill reads `brain.config.json` to discover the hub's shape and operates on it from the outside.

---

## 7. Formats — Markdown-first, JSON only for config

This follows directly from what graphify can ingest (verified against graphify v8 docs). graphify is **multi-modal**: it parses code locally and ingests a range of document and media formats.

| Format | graphify ingests it? | Use it for |
|---|---|---|
| **Markdown** (`.md`) | **Yes** — cheap to ingest, diffable | All authored knowledge: specs, domains, vocabulary, meeting notes, ADRs, research |
| PDF, `.docx`/`.xlsx`, images | Yes — via the LLM pass (costs tokens on first build) | Native source material: briefs, exports, designs |
| Audio / video | Yes — transcribed locally (faster-whisper) | Meeting and call recordings |
| **JSON** | **No** — not parsed as code or as a document | Machine config only (`brain.config.json`), read directly by tooling/Claude |
| Code (25 languages) | Yes — tree-sitter AST, local, free | The pulled app repos |

Consequences for the schema:

1. **Markdown-first, not Markdown-only.** Prefer Markdown for knowledge the team authors and maintains (diffable, free, easy to review). But native artifacts — a recorded kickoff, a PDF brief — are first-class inputs and can be dropped into `docs/` as-is; graphify will ingest them.

2. **No wikilinks.** We rely on graphify's inferred semantic edges and Leiden communities to connect related docs and code. Manual `[[wikilinks]]` were dropped — the upkeep (renames, broken links, governance) outweighed the marginal value over inferred edges. The vocabulary glossary is plain Markdown:

   ```markdown
   ## Session
   A booked block of time between a coach and a client.
   **Also called:** booking, appointment.
   **In code:** `Appointment` (backend-api model), `SessionCard` (web-app component).
   ```

3. **No `vocabulary.json` (for now).** `vocabulary.md` is the single source. graphify doesn't read JSON and Claude reads the Markdown directly, so a structured index has no current consumer. It returns only if/when the deferred linter or cross-repo adapters need it.

4. **`brain.config.json` stays JSON** because it's read by the sync tooling and by Claude directly — it never needs to be in the graph.

   ```json
   {
     "version": "1.0.0",
     "repos": [
       { "id": "backend-api", "url": "git@github.com:acme/backend-api.git", "src": ["app/"] },
       { "id": "web-app",     "url": "git@github.com:acme/web-app.git",     "src": ["src/"] }
     ],
     "doc_types": ["specs", "decisions", "meeting-notes", "research", "runbooks"],
     "graph": { "out": "graph/" }
   }
   ```

`doc_types` is the extensibility hook: add a type here and `brainify` recognizes it as a first-class knowledge area.

---

## 8. No changes to the app repos ("spokes" removed)

v0.1 proposed adding a `.pb.json` and a CLAUDE pointer to each app repo. **Removed.** With the hub pulling and building centrally, those additions were pure redundancy:

- `.pb.json` duplicated what `brain.config.json` already declares — two places to keep in sync, for no gain.
- Registration belongs in exactly one place: the hub's `brain.config.json`.

So the app repos stay **completely untouched**. This is strictly better for the "single source of truth" goal (one registration point) and removes all adoption friction (no PRs against the product repos).

*Optional, never required:* a team may drop a one-line note in an app repo's `CLAUDE.md` ("knowledge lives in the acme-brain hub") purely so an in-repo Claude session can find the hub. It carries no config and nothing depends on it.

---

## 9. How the graph is built — one graph over one assembled workspace

Because we've **deferred cross-repo linking and ripple analysis** (your call, see Open Problems §13), we don't need per-repo graphs plus a merge-and-link step. We build **one graph over the hub**:

```
pb sync
  1. pull the hub's own latest changes (safe: git repo + upstream + clean tree)
  2. pull/refresh each repo in brain.config.json into the VISIBLE repos/<id> folder
  3. keep repos/ and graph/ out of Git via .git/info/exclude; write a managed .graphifyignore
  4. run graphify over the hub → graph/graph.json + graph/GRAPH_REPORT.md
  5. write a short staleness/health note
```

**Why `.git/info/exclude` rather than `.gitignore`?** graphify honors `.gitignore`, so a git-ignored
`repos/` would be skipped by graphify too. Using the local `.git/info/exclude` keeps the clones out
of commits while leaving them visible *and* readable by graphify. A managed `.graphifyignore`
excludes only the generated `graph/` output.

One graphify run over docs + both codebases yields a single graph in which:

- code structure comes free from tree-sitter (local, no tokens);
- docs are connected to each other and to the code by graphify's inferred semantic edges (no manual links);
- graphify's own semantic-similarity edges and Leiden communities **softly co-locate** related code and docs across repos — e.g. the booking spec, the `Appointment` model, and the `SessionCard` component tend to land in the same community — *without* any adapter.

This gives genuinely useful cross-repo querying ("how does booking work across both apps?") today. What it does **not** give is precise, automatic impact analysis ("change this model → exactly these web files break"); that needs explicit cross-repo edges and is deferred.

**Why outside-the-repo graphs still answer questions and return chunks.** Each graph node stores a `source_file`. When Claude answers, it traverses the graph and opens only the few relevant chunks via those pointers. Because the pulled source lives in the hub's visible `repos/`, those pointers always resolve. The graph's physical location is irrelevant.

---

## 10. One source, many role lenses

The source is never duplicated. Each role gets a **view/query over the hub**, documented in `workflows/<role>.md`.

| Role | Lens (what they read) | Backed by |
|---|---|---|
| PM | Domains + specs + glossary, no code-node noise | `domains.md`, `docs/specs/`, `vocabulary.md` |
| Backend dev | Spec + graph scoped to the API code + constitution | `docs/specs/`, `graph/`, `constitution.md` |
| Frontend dev | Spec + graph scoped to the web code + constitution | `docs/specs/`, `graph/`, `constitution.md` |
| QA | Acceptance criteria + the relevant graph slices | `docs/specs/`, `graph/` |
| Designer | Domains + specs + UX copy + research | `domains.md`, `docs/specs/`, `docs/research/` |
| New hire | Guided path: constitution → domains → vocabulary → one spec → its graph slice | all of the above, sequenced in `workflows/onboarding.md` |

Every lens reads the same files; the lens only decides what to surface.

---

## 11. Tooling & skill changes

- **`brainify` becomes hub-aware and method-agnostic.** It audits the hub (required core present? `brain.config.json` valid? graph fresh? doc types populated?), not a single `.specify/`. It never invokes Spec Kit; it helps create and organize Markdown docs, and can hand off to whatever spec method the team configured.
- **New `pb sync`** (the §9 flow): pull → graphify over the assembled workspace → write graph + health note. Run nightly via a scheduled task or git hook to start.
- **Vocabulary is Markdown**, maintained as a glossary (§7); a future linter can verify "in code" references still resolve in the latest graph.
- **`brain.config.json`** is the single registration + extensibility point (repos + doc types).
- The framework ships the skill and templates; a hub holds only knowledge. (§4, §6)

---

## 12. Migration plan (incremental, low-risk)

1. **Stand up the hub repo.** Create `acme-brain` with the required core files and `brain.config.json` listing `web-app` and `backend-api`.
2. **Author the required core** in Markdown (constitution, vocabulary glossary). Map domains after the first sync.
3. **First sync.** Run `pb sync` to pull both repos and build the single graph over docs + code.
4. **Add the doc types you actually use** to `brain.config.json` and start dropping Markdown into `docs/` (specs however you author them; meeting notes; decisions).
5. **Write role workflows** for the roles you have.
6. **Automate freshness.** Schedule `pb sync`.

App repos require **no changes** at any step. Nothing is wasted if you stop partway.

---

## 13. Open problems (deferred, not solved here)

These are explicitly out of scope for this version and tracked for later:

- **Cross-repo linking adapters.** Wiring the web graph to the API graph via the contract between them (OpenAPI / GraphQL / tRPC / path heuristics). Hard because the contract style varies by product, and heuristic matching is error-prone. Deferred.
- **Ripple / impact analysis.** Precise "change X here → these things break there," especially across repos. Depends on the linking above. Deferred. (Soft co-location via communities, §9, is the interim partial answer.)
- **Freshness via CI-push.** Moving graph builds from central pull into each repo's CI so the hub is always current. Optimization, not required for v1.
- **Vocabulary ↔ graph linter.** Auto-verify that each glossary "in code" reference still resolves to a real node.
- **Non-git knowledge sources.** Pulling docs from Notion/Drive into the hub as exported Markdown.

---

## 14. Decisions recorded

| Decision | Choice | Rationale |
|---|---|---|
| Methodology coupling | **Method-agnostic; drop Spec Kit dependency** | Teams should use any spec/PM method; PB prescribes structure, not method. |
| Doc types | **Required core (3) + extensible `docs/` types** | Teams can add meeting notes, ADRs, etc. via `brain.config.json`. |
| Content format | **Markdown-first; multimodal supported; JSON only for config** | graphify ingests Markdown cheaply and also PDFs/docx/images/recordings; JSON isn't graphed. |
| Wikilinks | **Dropped** | graphify infers semantic edges and communities; manual links weren't worth the upkeep. |
| Vocabulary format | **`vocabulary.md` only** | Single source; no current consumer for a structured JSON index — re-add when the linter/adapters need it. |
| Domains | **Recommended, graph-assisted (not required core)** | Largely derivable from graph communities; humans curate names/owners/status. |
| Is the hub a repo? | **Yes — its own git repo** | Version history, PR review of knowledge, access control, graphify works on a dir. |
| Skill location | **Standalone with the framework; not in the hub, not under `.specify/`** | Skill is tooling, not knowledge; `.specify/` is Spec Kit's namespace. |
| App-repo additions | **None (spokes removed)** | Central registration in `brain.config.json`; zero friction, single source. |
| Graph for outside-repo querying | **One graph over one assembled workspace; querying/chunks work via `source_file`** | No merge needed; chunk retrieval is location-independent. |
| Cross-repo adapters + ripple | **Deferred to Open Problems** | Contract varies per product; heuristics error-prone; do it later. |

---

## 15. Appendix — booking, end to end (without ripple)

1. PM writes `docs/specs/003-booking.md` in whatever format the team uses, referencing the Scheduling domain and the `Session` glossary entry in plain prose.
2. `pb sync` pulls both repos and builds one graph spanning the spec, the `Appointment` model (api), and the `SessionCard` component (web); communities co-locate them.
3. Backend dev asks "what does booking touch in the API?" → the graph slice over the API code, grounded in the spec.
4. Frontend dev asks the same for the web code; both read the *same* spec and glossary.
5. QA reads the spec's acceptance criteria and the relevant graph slices to plan tests.
6. New hire follows `workflows/onboarding.md`: constitution → Scheduling domain → Session term → the booking spec → its graph slice — one path, one source.
7. *(Deferred)* "If I change `Appointment`, what web files break?" — answered only softly today via community co-location; precise cross-repo impact awaits the adapter/ripple work in §13.
