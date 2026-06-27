# 🧠 Product Brain

> **Keep your product, code, and team knowledge in sync — no matter how fast you move or how many people work on it.**

Product Brain is an open framework that connects your codebase, specs, vocabulary, and team decisions into a single queryable layer. Ask Claude anything about your product. Get answers grounded in real code and real requirements — not hallucinated structure.

---

## The problems it solves

| # | Problem | Without Product Brain |
|---|---------|----------------------|
| 1 | Codebase questions | Read every file manually, ask the "code person" |
| 2 | Missing specs | Code exists, nobody documented why or what |
| 3 | Vocabulary mismatch | "sessions" in the meeting, `Appointment` in the code |
| 4 | Ripple effects | A spec changes, nobody knows what else breaks |
| 5 | Multi-app knowledge | A question spans three repos and takes days |
| 6 | Institutional knowledge | Lives in people's heads, leaves when they do |

---

## How it works

```
Your codebase
      │
      ▼
  graphify              AST-based knowledge graph (19+ languages, no LLM key needed)
      │
      ▼
  graph.json            3,000+ nodes, communities, god-node analysis
      │
      ├──▶  Claude       Ask questions, get answers grounded in real code
      │
      ├──▶  speckit      Write specs, plans, and tasks from the graph context
      │
      └──▶  brainify     Interactive setup skill — audits what's missing, guides you through
```

---

## What's in this repo

```
product-brain/
  README.md                                   ← you are here
  CLAUDE.md                                   ← copy this into your project's CLAUDE.md
  website/
    product-brain.html                        ← full documentation site (open in browser)
  .specify/
    skills/
      brainify/
        SKILL.md                              ← interactive Claude setup assistant
    templates/
      spec-template.md                        ← feature spec template
      plan-template.md                        ← implementation plan template
      tasks-template.md                       ← task list template
      claude-md-snippet.md                    ← CLAUDE.md section to copy into any project
    memory/
      constitution-template.md               ← blank project constitution to fill in
    vocabulary-template.json                 ← vocabulary map starter
    init-options.json                        ← speckit config
    feature.json                             ← active feature tracker
```

---

## Quick start — 5 steps

### 1. Install graphify

```bash
pip install graphifyy
graphify --version
```

### 2. Copy `.specify/` to your project root

```bash
cp -r .specify/ /path/to/your-project/
```

### 3. Add the CLAUDE.md section to your project

Open `CLAUDE.md` in this repo. Copy everything from `## Product Brain` to the end.
Paste it into the bottom of your project's `CLAUDE.md` (create one if it doesn't exist).

### 4. Build your knowledge graph

```bash
cd /path/to/your-project
graphify app/ --out graphify-out      # point at your source code directory
open graphify-out/graph.html          # explore visually
```

> No LLM key needed for code-only directories. Only doc/PDF parsing requires a key.

### 5. Let Claude guide you through the rest

Open your project in Claude (Cowork or Claude Code) and say:

> **"Set up product brain"**

Claude audits what's present, shows a status report, and walks you through each step interactively — writing your constitution, building your vocabulary map, and drafting your first spec.

---

## The five framework layers

| Layer | Tool | What it gives you |
|-------|------|-------------------|
| 1. Knowledge graph | graphify | Ask questions of any codebase in seconds |
| 2. Governance | constitution.md | Non-negotiable principles every spec must follow |
| 3. Vocabulary | vocabulary.json | Bridge between product language and code terms |
| 4. Feature specs | speckit | Structured, reviewable specs with clear requirements |
| 5. Drift detection | speckit-converge | Find where implementation diverged from spec |

---

## Hygiene — keep it healthy

| Cadence | Action |
|---------|--------|
| Every PR | Run `speckit-converge` if the PR touches a spec'd feature |
| Weekly | Rebuild the graph — `graphify app/ --out graphify-out` |
| Per new feature | Write a spec with `speckit-specify` before coding starts |
| Per new term | Add to `vocabulary.json` when a new domain concept appears |
| Per architectural change | Amend `constitution.md`, bump version |

---

## Language support

graphify uses Tree-sitter grammars — works with any of the following out of the box:

`PHP` · `Python` · `TypeScript` · `JavaScript` · `Go` · `Rust` · `Java` · `C#` · `Swift` · `Kotlin` · `Ruby` · `C` · `C++` · `Scala` · `Lua` · `Julia` · `R` · `Elixir` · `Dart` · `SQL`

---

## Contributing

We need testers, researchers, stack champions, and integration builders. Every role has a clear goal and a PR format. See the full guide at **Section 10 — Contribute** in `website/product-brain.html`.

**Quick contribution paths:**

- **Dev Tester** — run the framework on your stack, report what breaks
- **PM Tester** — validate the spec workflow without writing code
- **Researcher** — investigate whether we're using the best tools for each problem
- **Stack Champion** — own the experience for Python, Rails, Node, Go, or any other stack
- **Integration Builder** — wire Product Brain to Linear, GitHub Actions, Slack, Notion
- **Lifecycle Mapper** — solve the unsolved stages: intake, UAT, post-launch monitoring

**PR format:** Problem you hit → what you changed → which product/stack you tested on → what you're unsure about.

```
contributions/[role]/[stack-or-topic]/[artifact.md]
```

There are 13 open problems documented in `website/product-brain.html` → Section 11. Each one is a concrete, unresolved gap with a proposed approach. Pick one and take a swing.

---

## Tools used

- **[graphify](https://pypi.org/project/graphifyy/)** (`pip install graphifyy`) — AST knowledge graph, 19+ languages, no LLM key for code analysis
- **[speckit](https://github.com/anthropics/speckit)** — spec/plan/task workflow via Claude skills
- **[Claude](https://claude.ai)** (Cowork or Claude Code) — runs brainify, writes specs, answers graph queries

---

## Full documentation

Open `website/product-brain.html` in any browser for the complete documentation: how-tos, role guides, workflows, hygiene schedule, FAQ, contributor roles, open problems, and the origin story of how the framework was developed.
