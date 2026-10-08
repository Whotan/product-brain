# Data file contract

The data file (`brain.config.json` → `portal.data`) holds everything on the page that a person
decides or reads off another source. The build derives the rest (see the last table).
`scripts/init-data.py` writes a starter with every required key; `assets/portal-data.template.json`
is that starter.

All strings are plain text and are escaped, except two fields that accept inline `<b>` and
`<code>`: `status.milestones[].t` and `flows[].steps[]`. Any string containing `TODO` fails the
build.

## Keys and where their facts come from

| Key | Shape | Source to re-read on every refresh |
|---|---|---|
| `version` | `1` | The contract version. It changes only with the template. |
| `title`, `description` | strings | Stable. `title` is the artifact's name; change it only when the owner asks. |
| `artifact_url` | URL or `""` | The publish result. Empty only before the first publish. |
| `asOf` | ISO date | Today. The build derives the display dates, and the Jalali one when `portal.calendar` is `"jalali"`. |
| `wordmark` | `{local, latin, tagline}` | Stable. `local` is the product name in the client locale (may be empty). |
| `footer` | string | Names the sources and their dates. Refresh the dates every time. |
| `privacy.withhold` | `{path: reason}` | SKILL.md › Privacy. Never shrink it without the owner. |
| `privacy.redact` | `[{pattern, with}]` | A Python regex, applied before the scan. |
| `privacy.allow` | `[value]` | Documented example values only. |
| `privacy.patterns` | `[{name, pattern}]` | Hub-specific values to scan for, added to the built-in phone and secret patterns. |
| `status.eyebrow`, `headline`, `body` | strings | The newest owner decision, or the dashboard's top focus item. The headline is the single most important fact this week. |
| `status.facts` | `[[label, value, note?]]` | Git tags (last release), `git rev-list --count origin/<production>..origin/<integration>` per repo, an audit's headline count. The build appends the spec and document counts. |
| `status.notice` | `{lead, text}` or absent | A warning that another page is out of date. Remove it once that page is fixed. |
| `status.milestones` | `[{d, t, kind?}]` | Goal dates and client promises. `kind` is `today` or `promise`. |
| `status.releases` | up to two cards: `{eyebrow, big, sub, items?[] , rows?[[k, v]]}` | Card 1 is the last release tag, its date, and what shipped (the release's internal note or its merge commits). Card 2 is the next release: the open release decision, plus what sits on the integration branch and on branches. |
| `status.krs` | `{title, lede, link?{label, id}, rows[]}` | Rows are `{objective}` or `{id, name, owner, pct, target, overdue, note}`. The source is the hub's goals tracker. `pct: null` means not reported; `overdue` counts dated items past due on `asOf`; `lede` names the check-in. |
| `status.decisions` | `[{title, body, who}]` | Open decisions and unanswered questions. Drop each one once it is made. |
| `specsLede`, `specsLink?` | string; `{label, id}` | Stable. The link is usually the delivery roadmap artifact. |
| `specStatus` | `{key: {label, pill}}` | Stable. `pill` is one of `p-released p-progress p-branch p-waiting p-spec p-deferred`. |
| `specs` | `{key: {name, status, note}}` | The delivery roadmap's verdict per spec. `key` is the spec's folder name, or its file name without `.md`. |
| `tasksLede`, `tasks` | string; `{KEY: note}` | One line per task folder (only with `portal.tasks`). |
| `artifactGroups` | `[group]` | Add a group only for a new kind of page. |
| `artifacts` | `[{group, title, id, updated?, desc, src?, shared?}]` | The Artifact tool's `list`. `id` is the short id or the full URL; `src` is the hub file the page is generated from. |
| `flows` | `[{title, desc, steps[], docs[]}]` | The hub's runbooks. `docs` must be hub Markdown paths. |
| `skillGroups` | `[{group, items:[{cmd, desc, path?}]}]` | `.claude/skills`, `.claude/agents`, `.claude/commands` and the plugins the hub uses. `path` opens the instructions in the reader; plugin skills have no path. |
| `library` | `{intro, start[], groupLabels?{prefix: label}, groupOrder?[]}` | The reader's empty state, its starter documents, and optional names and order for the library groups. A prefix is `""` (root files), a specs or tasks folder, `docs/<type>`, or a top-level folder. |
| `ruleCaveats` | `{number: text}` | Where the code does not yet do what a numbered constitution principle says. |
| `brand` | `{designDoc?, bookId?, northStar, northStarBody, lineLocal?, lineLatin?, typeNote, shapeNote, roleLabels?, do[], dont[], notice?}` | `DESIGN.md`. Never write a colour here; the page reads every colour from the compiled brand. |
| `hub` | `{lede, map[[path, desc, doc?]], gaps[], repos[[k, v]], commands[]}` | `CLAUDE.md` and `README.md`. `gaps` lists known inaccuracies in hub prose. `commands` are the lines shown on the graph card; a line starting with `#` is a comment. |

## Derived by the build (never in the data file)

| Derived | From |
|---|---|
| Document index, titles, groups, bundles `md/{core,docs,specs,skills}.json` | `git ls-files` for `*.md`, excluding `repos/`, `graph/`, `graphify-out/`, `logs/`, `.worktrees/`, `.work/` |
| "Open in …" vs "not on <branch> yet" | `git ls-tree origin/<portal.source.branch>`, fetched first (`--no-fetch` skips the fetch) |
| Spec rows and their document buttons | Folders and `.md` files in the specs folder, merged with `specs` |
| Task rows | Folders in `portal.tasks.dir` matching `key_regex`, merged with `tasks` |
| Constitution principles | `## 1. Title` or `### 1 — Title` headings in `constitution.md`, plus `ruleCaveats` |
| Graph stats | `<graph.out>/sync-report.md`, written by `pb sync` |
| Brand ramp | The `--ds-color-primary-<n>` steps in `<design.build>/tokens.json` |
| Display dates, build date, branch, withheld count | `asOf`, `portal.calendar`, the clock, `git rev-parse` |
