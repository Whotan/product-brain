---
name: brainify
description: Set up and maintain the Product Brain framework on any project. Use when the user says "set up product brain", "brainify", "walk me through setup", "what's missing from our setup", "help me set up product brain", "audit our documentation setup", or "what should I do next" in a framework context.
---

# Skill: Brainify

**Trigger phrases**: "set up product brain", "walk me through setup", "what's missing from our setup", "help me set up product brain", "audit our documentation setup", "what should I do next (framework)"

---

## What this skill does

Audits a project for all Product Brain components, shows what's present and what's missing, then walks through setup one phase at a time — interactively, with the right questions at the right time. Designed for teams starting from zero and for teams already partway through.

---

## Step 0 — Greet and orient

Start with a single sentence naming what you're about to do:

> "Running a Product Brain audit on this project — checking for all five framework layers."

Do not explain the framework at length. The user already knows why they're here.

---

## Step 1 — Run the audit

Execute the following checks with bash. Run them all at once in a single bash call, capturing each result.

```bash
# 1. graphify installed?
pip show graphifyy 2>/dev/null | grep "^Version" || echo "NOT_INSTALLED"

# 2. graph.json present?
test -f graphify-out/graph.json && echo "PRESENT" || echo "MISSING"

# 3. graph.json age in days (recent = < 7 days)
if [ -f graphify-out/graph.json ]; then
  AGE=$(( ( $(date +%s) - $(stat -f %m graphify-out/graph.json 2>/dev/null || stat -c %Y graphify-out/graph.json 2>/dev/null) ) / 86400 ))
  echo "${AGE} days old"
else
  echo "N/A"
fi

# 4. .specify/ initialized?
test -d .specify && echo "PRESENT" || echo "MISSING"

# 5. constitution.md filled? (present + > 10 lines = filled)
if [ -f .specify/memory/constitution.md ]; then
  LINES=$(wc -l < .specify/memory/constitution.md)
  echo "PRESENT ($LINES lines)"
else
  echo "MISSING"
fi

# 6. vocabulary.json present?
test -f .specify/vocabulary.json && echo "PRESENT" || echo "MISSING"

# 7. spec templates present?
test -f .specify/templates/spec-template.md && echo "PRESENT" || echo "MISSING"

# 8. specs/ count
if [ -d specs ]; then
  COUNT=$(find specs -name "spec.md" | wc -l | tr -d ' ')
  echo "$COUNT spec(s)"
else
  echo "MISSING"
fi

# 9. CLAUDE.md has framework section?
grep -l "Product Brain" CLAUDE.md 2>/dev/null | wc -l | tr -d ' '

# 10. Domain map present?
test -f .specify/memory/domains.md && wc -l < .specify/memory/domains.md | tr -d ' ' || echo "MISSING"
```

---

## Step 2 — Present the audit report

Render as a table. Be concise. Use ✅ / ⚠️ / ❌ with a one-line note per item.

| Layer | Component | Status | Note |
|-------|-----------|--------|------|
| 1 — Codebase Graph | graphify installed | ✅/❌ | |
| 1 — Codebase Graph | graph.json built | ✅/⚠️/❌ | Show age if present |
| 2 — Governance | `.specify/` initialized | ✅/❌ | |
| 2 — Governance | `constitution.md` filled | ✅/⚠️/❌ | Show line count if present |
| 3 — Vocabulary | `vocabulary.json` | ✅/❌ | |
| 4 — Spec templates | `spec-template.md` | ✅/❌ | |
| 5 — Feature specs | Spec count | ✅/⚠️/❌ | Show count |
| 6 — Claude config | CLAUDE.md framework section | ✅/❌ | |
| 7 — Domain map | `.specify/memory/domains.md` | ✅/⚠️/❌ | Show line count; ⚠️ if < 30 lines |

Rules:
- ✅ = present and healthy
- ⚠️ = present but stale (graph > 7 days) or thin (constitution < 20 lines)
- ❌ = missing

Follow the table with a **Priority gaps** list — only the ❌ and ⚠️ items, ordered by the setup sequence below. Do not list items that are ✅.

---

## Step 3 — Ask where to start

After the report:

> "Which gap would you like to address first? I'll guide you through it step by step."

If the user says "start from the top" or "all of them" or gives no preference, start with the highest priority gap in the sequence below. Go one gap at a time — do not attempt multiple phases simultaneously.

---

## Setup Sequence (priority order)

Work through gaps in this order. Each phase has its own guidance below.

```
Phase A → Install graphify
Phase B → Build the knowledge graph
Phase C → Initialize .specify/
Phase D → Write the constitution
Phase E → Build the vocabulary map
Phase F → Add framework section to CLAUDE.md
Phase G → Create the first feature spec
Phase H → Detect domains & spec core features
```

---

## Phase A: Install graphify

If graphify is not installed:

```bash
pip install graphifyy --break-system-packages
graphify --version
```

Confirm installation succeeded. Then move to Phase B.

---

## Phase B: Build the knowledge graph

Ask:
1. "Where is the source code? (e.g., `app/` or `src/` — code-only directories, no docs/PDFs)"
2. "Where should the output go? (default: `graphify-out/`)"

Then run:

```bash
graphify [source_dir] --out [output_dir]
```

After completion, report:
- Node count, edge count, communities found (parse from GRAPH_REPORT.md or stdout)
- Top 3 god nodes (highest edge count) — these are the most connected entities
- Suggest: "Want me to query the graph to identify the product domains?"

---

## Phase C: Initialize .specify/

If `.specify/` is missing, create the full directory structure:

```
.specify/
  memory/
    constitution.md       ← fill in Phase D
  templates/
    spec-template.md
    plan-template.md
    tasks-template.md
  skills/
    brainify/
      SKILL.md            ← this file
  vocabulary.json         ← fill in Phase E
  init-options.json
  feature.json
```

Create `init-options.json`:
```json
{"feature_numbering": "sequential"}
```

Create `feature.json`:
```json
{"feature_directory": ""}
```

Copy templates from existing `speckit` templates if available; otherwise generate them from the standard speckit format.

After creation: "`.specify/` initialized. Ready to write the constitution?"

---

## Phase D: Write the constitution

The constitution is the most important governance artifact. It takes ~10 minutes with the right questions.

### Interview (ask all questions before writing anything)

Ask each question one at a time. Wait for the answer before moving on. Tag each answer internally as D1–D5.

**D1 — Tech stack**
> "What language and framework does this project use? (e.g., Laravel 12 / PHP 8.4, Rails 7, Django, etc.)"

**D2 — API pattern**
> "How are API endpoints structured? Is there a specific pattern — controllers, use cases, actions, commands, something else?"

**D3 — Data layer**
> "How is data shaped and validated? DTOs, form requests, serializers, schemas?"

**D4 — Multi-tenancy / scoping**
> "Does the product serve multiple tenants or organizations? How is data isolated (e.g., per-clinic, per-team, per-organization)?"

**D5 — Non-negotiable rules**
> "What are the 2-3 rules every developer must never break? Things that would cause a PR to be rejected if violated."

**D6 — Localization / language**
> "Does the product need to support multiple languages? If so, which ones and what's the primary?"

**D7 — Testing expectations**
> "What test coverage is expected? Unit, feature, E2E? Any naming conventions or required passes before commit?"

**D8 — Changelog**
> "Is there a changelog or release notes requirement?"

### After interview

Write `.specify/memory/constitution.md` using the answers. Structure:

```markdown
# Project Constitution

**Version**: 1.0.0
**Project**: [name]
**Last Updated**: [date]

---

## Principles

### 1 — [Pattern derived from D2]
[1-2 sentence rule]

### 2 — [Pattern derived from D3]
...

### 3 — [Pattern derived from D4 if multi-tenant]
...

### 4 — [Tests + Changelog from D7/D8]
...

### 5 — [Localisation from D6]
...

### [Additional principles from D5 answers]
...

---

## Canonical Vocabulary

> These are the authoritative names for domain concepts. Use them in specs, code, and conversation.

| Concept | Canonical Term | Common Aliases |
|---------|---------------|----------------|
| [from graph communities + D answers] | | |

---

## Amendment Procedure

To update these principles: open a PR changing this file. Changes require sign-off from the Tech Lead and PM. Bump the version on any change.
```

Present the draft to the user. Ask: "Does this capture the principles correctly? Anything to add, remove, or reword?"

Iterate until approved. Do not mark Phase D complete until the user explicitly approves.

---

## Phase E: Build the vocabulary map

The vocabulary map is a machine-readable JSON file mapping code terms to product/domain terms.

### Auto-extraction (preferred)

If `graphify-out/graph.json` exists, query it for the top entities:

```bash
graphify query graphify-out/graph.json "list all entity and class names by connection count, top 30" 2>/dev/null || \
  python3 -c "
import json
data = json.load(open('graphify-out/graph.json'))
nodes = data.get('nodes', [])
entities = [(n.get('id',''), n.get('connections', n.get('degree', 0))) for n in nodes if n.get('type') in ['class','model','entity','interface']]
entities.sort(key=lambda x: -x[1])
for name, deg in entities[:30]:
    print(f'{deg:3d}  {name}')
"
```

Present the top entities. For each one, ask:
> "Is '[EntityName]' known by a different name in the product specs, user stories, or customer-facing language? (type the alias, or press enter to skip)"

Batch this — show 5 entities at a time. Collect answers.

Also ask:
> "Are there any product terms that don't appear in the code yet? (e.g., 'Session' → maps to 'Appointment' in code)"

### Write vocabulary.json

```json
{
  "version": "1.0.0",
  "updated": "[date]",
  "terms": [
    {
      "canonical": "[code term / most precise name]",
      "aliases": ["[product term]", "[customer term]", "[doc term]"],
      "context": "[brief note on what this entity represents]",
      "source": "[code path or module]"
    }
  ]
}
```

After saving:
> "Vocabulary map saved. You can add entries at any time. I'll use this to cross-reference code and product language when answering questions."

---

## Phase F: Add framework section to CLAUDE.md

If CLAUDE.md exists but has no framework section, append the standard Product Brain section (from `.specify/templates/claude-md-snippet.md` if it exists, otherwise generate it from the template below).

**Standard CLAUDE.md section to append:**

```markdown

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

- "Set up product brain" / "walk me through setup" → run brainify skill
- "What's missing from our setup?" → run audit (Step 1 of setup skill)
- "What should I do next?" → suggest highest-priority missing framework component
- "Build the graph" → `graphify app/ --out graphify-out` (code-only, no LLM key needed)
- "Rebuild the graph" → delete `graphify-out/` first, then rebuild
- "Write a spec for X" → use speckit-specify
- "What domains does this product have?" → query graph communities
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
```

Confirm with: "Framework section added to CLAUDE.md. Claude will now check framework health and suggest next steps automatically."

---

## Phase G: Create the first feature spec

If no specs exist yet, offer to start one. This is the highest-value first action after setup.

> "The framework is fully set up. The natural first move is to document your product's domains and write the first spec. I can:
> 1. Query the knowledge graph to identify the main domains in this product
> 2. Ask you questions about the most important domain to build your first spec
> 3. Generate a draft spec for review
> 
> Want to start with domain discovery?"

If yes → proceed to Phase H (domain detection & specification).

---


---

## Phase H: Domain Detection & Core Feature Specification

This phase maps the product's functional domains from the knowledge graph, documents each one, and guides the user to write a core feature spec per domain.

### Step H1 — Detect domains from the graph

If `graphify-out/graph.json` exists, run:

```bash
python3 -c "
import json, sys
data = json.load(open('graphify-out/graph.json'))
communities = data.get('communities', [])
if not communities:
    # fall back to node-type clustering
    nodes = data.get('nodes', [])
    types = {}
    for n in nodes:
        t = n.get('type', 'unknown')
        types.setdefault(t, []).append(n.get('id', ''))
    for t, members in sorted(types.items(), key=lambda x: -len(x[1]))[:10]:
        print(f'{t} ({len(members)} entities): {members[:4]}')
    sys.exit()
for i, c in enumerate(communities[:15]):
    name = c.get('label', c.get('name', f'Community {i+1}'))
    members = c.get('members', c.get('nodes', []))
    print(f'Domain {i+1}: {name} ({len(members)} entities)')
    for m in (members[:5] if isinstance(members[0], str) else [n.get('id','') for n in members[:5]]):
        print(f'  - {m}')
    if len(members) > 5:
        print(f'  ... and {len(members)-5} more')
"
```

Present the results as a numbered list of candidate domains. If the graph isn't available, ask the user:
> "No knowledge graph found. Can you list the main functional areas of this product? (e.g., Scheduling, Billing, Identity, Notifications)"

### Step H2 — Confirm and name domains

Show the candidate list and ask:
> "These look like the main domains — does this match how you think about the product? Add, remove, or rename any before we document them."

Wait for confirmation. Work from the agreed list.

### Step H3 — Interview per domain

For each domain, ask these questions **one at a time**, then move to the next domain. Tag answers H3a–H3f.

**H3a — Product name**
> "What's the business/product name for this domain? (e.g., code says `Appointment`, product calls it 'Sessions')"

**H3b — Responsibility**
> "In one sentence: what is [domain] responsible for?"

**H3c — Core features**
> "What are the 3–5 core features this domain provides to end users?"

**H3d — Boundaries**
> "What does this domain NOT do — what's explicitly out of scope?"

**H3e — Owner**
> "Who owns this domain? (team name, squad, or person)"

**H3f — Status**
> "Is this domain: stable / actively evolving / partially built / planned?"

Collect all answers for a domain before moving on. Do not write anything until all domains are interviewed.

### Step H4 — Write the domain map

Write `.specify/memory/domains.md`:

```markdown
# Domain Map

**Version**: 1.0.0
**Last Updated**: [date]

---

## [Domain Name]

**Responsibility**: [H3b]
**Owner**: [H3e]
**Status**: [H3f]

**Core Features**:
- [feature from H3c]
- ...

**Out of scope**: [H3d]

**Key entities** (from graph): [top 5 node names from the detected community]

---

## [Next Domain]
...
```

After saving:
> "Domain map written to `.specify/memory/domains.md`. I'll use this as a reference when you ask about what different parts of the product do."

### Step H5 — Offer core feature specs

After the domain map is saved:

> "You've documented [N] domains. The highest-value next step is to write a spec for the most important core feature in each domain — this gives Claude and your team a shared reference for what each domain is supposed to do.
>
> Which domain should we start with?"

For the chosen domain, list the core features named in H3c. Ask which one to spec first. Then invoke the `speckit-specify` skill for that feature.

After each spec is drafted: "Want to continue to the next domain, or stop here for now?"

Repeat until the user stops or all domains have a spec.

### Domain map checklist

Before marking Phase H complete, verify:

- [ ] All agreed domains have an entry in `domains.md`
- [ ] Each entry has responsibility, owner, status, and core features filled
- [ ] At least one core feature spec exists (or is in progress) per domain
- [ ] Domain names in `domains.md` match the vocabulary in `vocabulary.json` (update vocabulary if not)

---

## Completion summary

After all chosen phases are complete (or user says "done for now"), print a final status:

```
✅ Product Brain — Setup Status

Layer              Status
───────────────────────────────
Knowledge graph    ✅ Built (NNN nodes, NNN edges)
Governance         ✅ Constitution v1.0.0
Vocabulary         ✅ NN terms mapped
Domain map         ✅ NN domains documented
Spec coverage      NN specs (NN domains)
Claude config      ✅ CLAUDE.md updated

Next recommended action: [highest-value next step]
```

Offer to schedule a graph rebuild reminder if the graph is over 7 days old.

---

## Ongoing: "What should I do next?"

When the user asks this at any point after setup, run a lightweight re-audit (just the file checks, no stdout) and respond with the single highest-value next action based on what's missing or stale:

| Condition | Suggestion |
|-----------|------------|
| Graph missing | "Build the knowledge graph — it unlocks all codebase querying" |
| Graph > 14 days | "Rebuild the graph — significant code changes may have drifted since last build" |
| Constitution missing | "Write the constitution — it prevents misaligned specs and code" |
| Constitution < 20 lines | "The constitution looks thin — let's flesh out the principles" |
| Vocabulary missing | "Build the vocabulary map — it bridges code and product language" |
| Domain map missing, has graph | "Map your product domains — I'll query the graph for communities and guide you through Phase H" |
| Domain map missing, no graph | "Name your product's main functional areas — I'll document them as domains in `.specify/memory/domains.md`" |
| Domain map thin (< 30 lines) | "The domain map looks incomplete — let's finish documenting the remaining domains" |
| Domains documented, no specs | "Start speccing core features — pick a domain and I'll open speckit-specify for its top feature" |
| No specs, has graph | "Start documenting domains — run Phase H to detect communities and write the first specs" |
| Has specs, no plan | "Run speckit-plan on spec [name]" |
| Has plan, no tasks | "Run speckit-tasks to generate the implementation task list" |
| Everything green | "Run speckit-converge on your last completed spec to check for drift" |
