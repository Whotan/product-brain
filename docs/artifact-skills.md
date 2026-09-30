# Artifact skills

Four skills that turn a hub's knowledge into generated documents: the brand design system, the
delivery roadmap, release notes, and the product dashboard. They ship in the Product Brain plugin
(`skills/<name>/`), work in **any** hub, and read every product-specific fact from
`brain.config.json` — never a hardcoded default. A missing config key is a clear error naming the
key and an example value, not a silent fallback.

| Skill | Produces | Reads (`brain.config.json` key) |
|---|---|---|
| `brand-system` | The hub's `DESIGN.md` (drafted by `extract`), plus compiled `brand/brand.css` + `brand/tokens.json` | `design` |
| `delivery-roadmap` | The internal delivery roadmap (HTML: one card per feature, a computed timeline, a conflicts panel) and its facts JSON. It reads a per-release **headline** back out of `release-notes`' output, but does not write release notes itself. | `repos`, `releases` (partially — see below), `roadmap` |
| `release-notes` | Per-release folder: `client.html` + `client.pdf` (client locale only, publishable) and `internal.md` (team only). Can also open the merge/pull request that ships the latest release branch to production, with an English, bullet-point, Added/Changed/Fixed body built from git — a separate document from the two notes. | `repos`, `releases`, `design.logo`/`design.source` |
| `update-product-hub` | The product dashboard (HTML: today's focus, at-risk items, yesterday's activity) and the `dashboard.state` recorded layer | `repos`, `releases.integration_branch`, `dashboard`, `graph.out` |

All four are invoked as `product-brain:<name>` once the plugin is installed, or by asking
naturally ("refresh the roadmap", "write release notes for this tag") — see
[Migrating from hub-local copies](#migrating-from-hub-local-copies) below.

This table, and everything below it, is rebuilt from each skill's own `SKILL.md` "Config" /
"Configuration" section — that file is the authority; this page only collects it in one place.

---

## The brand pipeline

Every artifact these skills generate must be styled from the **one** product-level design system,
never invented per-document.

1. **`DESIGN.md`** (hub root) — the brand tokens (colour ramps, semantic colours, type, shape,
   spacing), an `artifact` role mapping (light + dark) every generated document uses, and a
   `provenance` block recording which repo/ref/path each token group was lifted from.
   `brand.py extract` drafts it from the frontend repo(s) named in `design.source`/`design.sources`
   — reviewed by a human, never hand-invented and never sampled from a screenshot. A hub with no
   frontend repo to extract from writes `DESIGN.md` by hand instead (see
   `examples/todo-app/DESIGN.md`, which has no `design.source` at all).
2. **`brand.py build`** resolves every `{group.key}` reference and writes `<design.build>/brand.css`
   (default `brand/brand.css`) and `<design.build>/tokens.json` — resolved values, a sha256 of
   `DESIGN.md` (`design_sha256`) and of the compiled CSS (`brand_css_sha256`), so a stale build or a
   stale inlined copy is mechanically detectable, never eyeballed.
3. **`brand.py inline <file.html>`** — every artifact template inlines `brand.css` between
   `/* BRAND:BEGIN */` / `/* BRAND:END */` markers inside a `<style>` block (published artifacts
   can't load local files). Every colour, font-family and radius in the template's own CSS is a
   `var(--ds-*)` role; derived tints are `color-mix(in oklab, var(--ds-x) N%, var(--ds-y))`. No
   literal hex/rgb/hsl/oklch, no named font-family, no literal shadow or gradient outside that
   block.
4. **`check-brand.py <file.html>...`** fails an artifact on: a missing/stale/malformed BRAND block
   (hash mismatch against `brand_css_sha256`, or no early `<meta charset="utf-8">`); a colour
   literal outside the block; a `font-family` that isn't `var(--ds-font-*)`; a `font-weight` the
   brand doesn't embed (or, with no fonts embedded, doesn't declare); an unknown `var(--ds-x)`; or a
   literal gradient/shadow outside the block. It runs in the verify step of every artifact skill —
   zero failures is the bar for publishing. This is what the constitution's "Brand design system"
   principle enforces.

Every build that changes `brand.css` makes every already-inlined artifact's BRAND block stale —
re-run `inline` on the hub's living artifacts (not on a skill's own template/fixture assets, which
stay brand-free) and re-verify.

### The `artifact` role block

**Required, in both `light` and `dark`:** `canvas surface inset ink muted border primary
primary-strong primary-soft on-primary accent success warning danger info`.
**Required, shared:** `font-body font-display font-mono`, `radius-sm radius-md radius-lg`.
If the product has no dark scheme, the dark roles map onto existing ramp tokens (950/900 grounds,
100/200 ink, 300/400 emphasis) — never a hex that exists only for dark mode.

**Optional roles — `brand.css` always emits their variables regardless**, with a default when
`DESIGN.md` omits them:

| Role | Where | Default |
|---|---|---|
| `font-latin` | shared | the `font-body` stack |
| `success-ink` `warning-ink` `danger-ink` `info-ink` | per scheme | the base role |
| `shadow-sm` `shadow-md` | per scheme or shared | `none` |
| `wash` | per scheme or shared | `var(--ds-canvas)` |

A per-scheme effect falls back to the shared value, then the default — never to the other scheme's
value. The `*-ink` roles are the text-safe variant of a semantic colour (amber/bright-green fills
usually fail 4.5:1 as text); use the base role for fills/dots/bars, the `-ink` role for text.

### Always-emitted `--ds-*` variables

Every one of these exists on every build, for any brand — a template may rely on all of them:

- The 15 required colour roles above, plus the 4 optional `*-ink` roles, `shadow-sm`/`shadow-md`
  and `wash` — each as `--ds-<role>` (e.g. `--ds-primary`, `--ds-danger-ink`, `--ds-shadow-md`).
- `--ds-font-body`, `--ds-font-display`, `--ds-font-mono`, `--ds-font-latin`.
- `--ds-radius-sm`, `--ds-radius-md`, `--ds-radius-lg`.
- `--ds-leading-body` — the `font-body` tier's `lineHeight` (default `1.6`).
- `--ds-space-1` … `--ds-space-8` — from numeric `spacing` keys (missing steps interpolated), plus
  any other `--ds-space-<key>` the design system defines.
- `--ds-weight-regular`, `--ds-weight-strong`, `--ds-weight-bold` — 400/600/700 mapped to the
  nearest weight the brand actually has (embedded, or declared if nothing is embedded).
- `--ds-color-<name>` and `--ds-rounded-<name>` — every raw token, for the rare case a role isn't
  enough.

---

## `brain.config.json` keys

### `design` (read by `brand-system`; `design.logo`/`design.source` also by `release-notes`)

| Key | Required? | Default | Example |
|---|---|---|---|
| `system` | No | `"DESIGN.md"` | `"DESIGN.md"` |
| `build` | No in `brand-system` (defaults to `"brand"` when absent). `release-notes`' own config reader has no such default for this key, so set it explicitly to avoid a hard failure there | `"brand"` | `"brand"` |
| `source.repo` / `source.ref` | For `extract`, for `fonts`, and for `logo` (omit for a hand-authored `DESIGN.md` with no logo) | — | `{ "repo": "web-app", "ref": "origin/main" }` — read with `git show <ref>:<path>`, never the working checkout |
| `sources` | For `extract` | — | `["src/styles/tokens.css", "src/design/colors.ts"]` — evidence at `source.ref`; extra one-offs can be passed to `extract --source` instead |
| `fonts` | No | — (system stacks; PDF font checks warn instead of fail) | `{ "Inter": { "400": "src/assets/fonts/Inter-Regular.woff2", "700": "src/assets/fonts/Inter-Bold.woff2" } }` — family → weight → path at `source.ref`; only listed weights are ever embedded |
| `logo` | No (`release-notes` masthead; falls back to a text wordmark) | — | `"src/assets/logo.svg"` — read at `source.ref`, embedded as a `data:` URI |

### `workspace` and repo clone resolution (read by every skill)

| Key | Required? | Default | Example |
|---|---|---|---|
| `workspace.repos_dir` | No | `"repos"` | `"repos"` |
| `repos[].path` | No, per repo | — | `"repos/backend-api"` |

Every skill resolves a repo's clone the same way: `repos[].path` if the repo entry sets one
(hub-relative), else `<workspace.repos_dir>/<id>`, else `repos/<id>`.

### `hub` (optional; each reader's requirement differs — see Read by)

| Key | Read by | Required? | Default | Example |
|---|---|---|---|---|
| `hub.name` | `release-notes` (internal note's product name, always); `update-product-hub` (dashboard title fallback) | **Yes** for `release-notes` (no default — it's a hard `Config.get` with no fallback, even though `releases.client_note.product_name` can override what the *client* note shows); **No** for `update-product-hub` (only consulted when `dashboard.title` is unset, and even then only to sanity-check the page's own `<title>`) | — | `{ "name": "Acme" }` |

`hub.name` is nested (`{"hub": {"name": "…"}}`), which is a **different key** from the top-level
`hub_name` string `bin/pb` reads for the generated README's heading. Set both if you want the
generated README's heading and the dashboard/release-notes wordmark to agree — see
[Hub name](#hub-name-hubname-or-hub_name) below.

### `releases`

| Key | Read by | Required? | Default | Example |
|---|---|---|---|---|
| `tag_regex` | `release-notes`, `delivery-roadmap` | Yes | — | `"^v\\d+\\.\\d+\\.\\d+$"` — a matching tag **is** a production release, nothing else |
| `primary_repo` | `release-notes` | Yes | — | `"backend-api"` — whose latest matching tag names the release when no tag is given on the command line |
| `production_branch` | `release-notes`, `delivery-roadmap` | Yes | — | `"main"` — where release tags are cut from |
| `integration_branch` | `delivery-roadmap`, `update-product-hub` | Yes | — | `"develop"` |
| `release_branch_regex` | `delivery-roadmap` (classifies merges onto production), `release-notes` (picks "the latest release branch" to open its MR/PR from) | No | `"^(release\|hotfix)[-/._]"` | `"^release/"` |
| `version_regex` | `release-notes`, `delivery-roadmap` | No | group 1 of `version_regex` if set; else `tag_regex`'s named group `(?P<version>…)` if it has one; else the whole tag | `"^v(\\d+\\.\\d+\\.\\d+)$"` — one capture group; the version label artifacts show instead of the raw tag |
| `merge_style` | `delivery-roadmap` | Yes | — | `"squash"` — `squash\|merge\|rebase`; squash means a plain ancestry check can give a false negative, so verdicts are checked by content, not ancestry alone. `release-notes`' own Accuracy rules apply the same caution in prose but don't branch on this key in code |
| `out` | `release-notes` (release folders live here); `delivery-roadmap` (reads a release's headline back from `<out>/<version> - <date>/client.html` if that folder exists) | Yes | — | `"docs/releases"` |
| `specs_dir` | `release-notes` (falls back to `roadmap.specs_dir` if unset) | No | `roadmap.specs_dir` | `"specs"` — spec citations and their claimed ticks |
| `areas` | `release-notes` | No | the built-in path→area rules (migrations, i18n, tests, routes, …), checked after this list | `[["^app/Http/", "http-routes"], ["^resources/js/", "frontend"]]` — `[[regex, area], ...]` |
| `client_note.locale` | `release-notes` | Yes | — | `"en"` |
| `client_note.dir` | `release-notes` | Yes | — | `"ltr"` (or `"rtl"`; anything else is a config error) |
| `client_note.calendar` | `release-notes` | No | `"gregorian"` | `"jalali"` |
| `client_note.product_name` | `release-notes` | No | `hub.name` | `"Acme Todo"` — overrides the wordmark shown in the client locale only; the internal note always uses `hub.name` regardless |
| `client_note.i18n` | `release-notes` | No, defaults to `[]` — but without it the client note has no client-locale vocabulary source, so set it whenever the app ships i18n files | `[]` | `[{ "repo": "web-app", "path": "src/assets/i18n/en.json" }]` — client-locale string files at the release tag |
| `client_note.i18n_source` | `release-notes` | No | — | `[{ "repo": "web-app", "path": "src/assets/i18n/en-US.json" }]` — the source-language files, for comparison |
| `internal_note.locale` | `release-notes` | Yes | — | `"en"` |
| `tests` | `release-notes` | No, defaults to `{}` — an empty map produces a "no releases.tests configured" placeholder row instead of failing | `{}` | `{ "backend-api": "./vendor/bin/phpunit", "web-app": "npm test" }` — one entry per repo whose suite the internal note reports |
| `capture.repo` | `release-notes` | No (only if release notes screenshot the app) | — | `"web-app"` |
| `capture.apps.<app>.serve` | `release-notes` | With `capture` | — | `"npm start"` — run through a shell; treat as code |
| `capture.apps.<app>.base_url` | `release-notes` | With `capture` | — | `"http://localhost:4200"` |
| `capture.apps.<app>.base_path` | `release-notes` | No | `""` (no base path) | `"/app"` |

### `roadmap` (read by `delivery-roadmap`)

| Key | Required? | Default | Example |
|---|---|---|---|
| `out` | Required by the workflow (the skill needs it to know where to render), but not enforced by a script-level "missing key" check — it's read by the agent and passed as a CLI argument, not looked up inside a script | — | `"docs/roadmap/delivery-roadmap.html"` |
| `facts` | Yes — `gather-git-facts.py` fails with the key name and this example if it's absent | — | `"docs/roadmap/.roadmap-facts.json"` — derived, never hand-edited |
| `specs_dir` | No | — (spec folders are skipped; claimed-progress checks don't run) | `"specs"` — read as *claimed* progress only |
| `framing` | No | `"none"` | `"shape-up"` — one of `shape-up`, `scrum`, `kanban`, `none`; changes only the page's vocabulary (window/commitment/size/progress words), never structure or checks — see the skill's framing table |
| `okrs` | No | — (OKR reconciliation step is skipped) | `"docs/okrs/tracker.html"` |

### `dashboard` (read by `update-product-hub`)

| Key | Required? | Default | Example |
|---|---|---|---|
| `out` | Yes | — | `"docs/dashboard/product-hub.html"` |
| `state` | Yes | — | `"docs/dashboard/hub-state.json"` — shape: `{version, updated, focus, decisions, syncLog}`; start a new hub from `assets/hub-state.template.json` |
| `title` | No | falls back to `hub.name` (the page's existing `<title>` must then be stable, dateless, and name the product) | `"Acme — Product Hub"` |
| `inputs` | Yes — the key itself must exist (an empty `[]` is valid; no entries just means no inputs to gate or reconcile) | — | `[]` |
| `inputs[].id` | Yes, per input | — | `"roadmap"` |
| `inputs[].path` | Yes, per input | — | `"docs/roadmap/.roadmap-facts.json"` |
| `inputs[].produced_by` | Yes, per input (nullable) | — | `"delivery-roadmap"`, or `null` when a person maintains the file by hand |
| `inputs[].kind` | No | — | `"goals"` — marks the **one** input carrying dated commitments (OKRs, a plan); only then does the page render the Obligations-at-risk tile and frame its timeline on that input's measurement window. Without a `"goals"` input the tile must be omitted entirely (the gate fails a page that renders one anyway) |
| `inputs[].check` | No | — | `"docs/checks/goals-match-audit.py"` — hub-relative `.py`, run as `python <check> <hub-root> <page-path> <input-path>`, must print `PASS\|WARN\|FAIL name — detail — remedy` lines and exit 0 |
| `inputs[].max_age_days` | No | `0` for an input the refresh re-runs itself, `7` otherwise | `7` |

Workers and the skills themselves never edit `brain.config.json` — a missing or wrong key stops
the script with the key's name and an example value; the user (or Claude, on their behalf) edits
the file.

### Hub name: `hub.name` or `hub_name`

`bin/pb` and brainify write a flat top-level `"hub_name"`; hand-made hubs often use a nested
`{"hub": {"name": "…"}}`. The artifact skills accept either (nested wins when both are set).
`bin/pb` still reads only `hub_name` for the generated README heading, so a hub that uses the nested
form and wants that heading sets both.

---

## `brand/tokens.json` keys

Written by `brand.py build` under `<design.build>/tokens.json`. Consumed by `check-brand.py`,
`brainify`'s audit, and `brand.py pdf-fonts`/`show` — never hand-edited.

| Key | Meaning |
|---|---|
| `design_md` | hub-relative path of the `DESIGN.md` that was compiled |
| `design_sha256` | sha256 of that `DESIGN.md`'s bytes — compare to detect a build that's stale against the source |
| `brand_css_sha256` | sha256 of `brand.css` (CRLF→LF, trimmed) — what every inlined BRAND block is compared against |
| `source` | `{repo, ref, commit}`, or `null` for a hand-authored `DESIGN.md` |
| `roles` | `{light, dark, common}` — every resolved role, optional roles included with their defaults |
| `colors`, `rounded`, `spacing` | resolved raw tokens |
| `fonts_embedded` | `false` when `design.fonts` is absent (artifacts use system stacks; PDF font checks warn, not fail) |
| `embedded_weights` | `{family: [weights]}` — only these weights may appear in an artifact; asking for another falls back to a system face |
| `embedded_faces` | `[{postscript, font_family}, …]` — what `brand.py pdf-fonts` matches a rendered PDF's embedded fonts against |
| `declared_weights` | every `fontWeight` `DESIGN.md` typography declares — the font-weight check's set when nothing is embedded |
| `weights` | `{regular, strong, bold}` as emitted in `--ds-weight-*` |
| `allowed_families` | families a PDF may contain (embedded faces + the mono stack; every declared family when nothing is embedded) |
| `css_vars` | every `--ds-*` name `brand.css` defines — what `check-brand.py`'s unknown-token check compares against |

---

## Migrating from hub-local copies

Development on these four skills can start as hub-local copies under
`.claude/skills/<name>/` while they're being written or customized for one team. Once the plugin
ships the same skill under `skills/<name>/`, migrate:

1. Confirm the Product Brain plugin is installed and up to date (`/plugin marketplace update
   product-brain`, `/reload-plugins`), and that `product-brain:<name>` responds for each of the
   four skills.
2. Delete the hub-local copy: `rm -rf .claude/skills/<name>` for each of `brand-system`,
   `delivery-roadmap`, `release-notes`, `update-product-hub`. **A hub-local skill of the same name
   shadows the plugin's** — Claude Code resolves the more specific one first — so leaving the old
   copy in place silently keeps running the stale version even after the plugin updates.
3. Plugin skills are namespaced `product-brain:<name>` (e.g. `product-brain:brand-system`) —
   update any doc or memory that referenced the unqualified name. You can still just ask naturally
   ("refresh the roadmap") and the matching skill triggers on its description.
4. **Hub-specific rules belong in the hub, not in a forked skill.** If the hub-local copy grew
   team-specific wording (a house style for release notes, an extra roadmap section), move that
   into the hub's `CLAUDE.md` or `constitution.md` instead of re-forking the skill — the shared
   skill stays generic and upgradeable; the hub layers its own rules on top by reading them from
   `brain.config.json` and the hub's own docs.
