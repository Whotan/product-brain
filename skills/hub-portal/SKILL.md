---
name: "hub-portal"
description: "Use when the user wants one page anyone can open to see where the product stands and find every hub document, artifact, spec, skill or runbook; when they mention the hub portal, the hub's front page or index page, or a 'where we stand' page; when they ask to create, refresh, rebuild or republish it; and after a release, a new spec, a new skill or a newly published artifact that should appear on it."
argument-hint: "[setup | refresh | rebuild-only] (default: refresh)"
compatibility: "Requires a Product Brain hub (brain.config.json with a portal block) under git, python3, and the brand-system skill beside this one with the brand built. The render check needs the Python playwright package. Publishing needs the Artifact tool."
metadata:
  author: "product-brain"
user-invocable: true
---

# Hub Portal

`${CLAUDE_SKILL_DIR}` is this skill's base directory; substitute it if your shell does not expand it.

One published page that answers "where do we stand, and where is everything": a status
section, every Markdown file in the hub rendered in place and searchable, the live artifacts,
specs, workflows, skills, the brand and a map of the hub. A newcomer, a stakeholder or a
teammate opens one link instead of cloning the repo.

The page has three layers, and only the first is edited by hand:

| Layer | Where | Who changes it |
|---|---|---|
| Facts a person decides or reads off another page | the data file named by `portal.data` (committed) | you, in step 2 |
| Everything mechanical: document index and bundles, spec and task rows, constitution principles, graph stats, on-branch flags, display dates | `scripts/build.py`, on every build | nobody |
| Layout and behaviour | `assets/portal.template.html` | only when the page itself changes |

The build lands in `portal.out` (default `.work/hub-portal/`, git-ignored). Never edit or commit it.

## Configuration

Read from `brain.config.json` → `portal`. The scripts stop with a message naming any missing
or malformed key.

| Key | Required | Meaning |
|---|---|---|
| `data` | yes | Hub-relative path of the data file, e.g. `"docs/dashboard/hub-portal.json"` |
| `out` | no (`.work/hub-portal`) | Where the page and its `md/*.json` bundles are written |
| `specs_dir` | no (falls back to `roadmap.specs_dir`, then `releases.specs_dir`) | Where specs live: one folder or one `.md` file per spec |
| `tasks` | no | `{"dir": "tasks", "key_regex": "^PROJ-\\d+$"}`. Adds a task section, with one row per matching folder. |
| `source` | no | `{"blob": "<url>/blob/main/", "tree": "<url>/tree/main/", "branch": "main"}`. Adds an "Open in GitHub/GitLab" button and flags docs not yet on that branch. |
| `calendar` | no | `"jalali"` adds the Jalali date beside the Gregorian one |

Also read: `graph.out` (for `sync-report.md`) and `design.build` (for the brand's ramp).

## Which mode

- **setup:** no data file exists yet. Add the `portal` block, then run
  `python "${CLAUDE_SKILL_DIR}/scripts/init-data.py"`. It writes a starter file with every spec,
  skill and core document already filled in, and marks each fact a person must supply with
  `TODO`. The build refuses to run while any `TODO` remains. Then follow **Refresh** from step 2.
- **refresh** (the default): use this whenever a status fact may have moved: a release, a merge,
  a decision, an artifact, a spec changing state, or an `asOf` older than a day.
- **rebuild-only:** skip steps 1–2. Use it when only document text, a new spec or a new skill
  changed. A new spec shows its own `Status:` line and a WARN until the next refresh. When both
  kinds of change happen, run refresh.

## Refresh

1. **Verify, then refresh the sources.** Check every claim you were given against git:
   tags, branches, and folders on disk. Git wins; when git and the user disagree, stop and ask.
   The status section is copied from other pages, such as the hub's dashboard
   (`update-product-hub`) and roadmap (`delivery-roadmap`). If anything happened after their
   dates, re-run those skills first. A stale source makes a stale page.
2. **Update the data file**, key by key, from the sources named in
   [references/data-contract.md](references/data-contract.md). Set `asOf` to today; the build
   derives the display dates. Never carry a figure forward from this page's previous version.
   - **Artifacts:** call the Artifact tool with `action: "list"`, `scope: "all"`, `limit: 50`.
     Rows marked "(shared)" get `"shared": true`. If the listing says more exist than it shows,
     ask the user for the ones you cannot see. For a new artifact, take `desc` from the page
     itself (`action: "read"`, asking for its purpose in one sentence), and choose its group by
     what a reader uses it for.
   - **After a release:** update `status.facts`, the release cards, and every spec, KR and
     decision note that names the release. Drop the decisions it settled.
3. **Build:** `python "${CLAUDE_SKILL_DIR}/scripts/build.py"` from the hub. Fix every `ERROR`
   and re-run until it passes. Resolve each `WARN` or list it in your report.
4. **Look once:** `python "${CLAUDE_SKILL_DIR}/scripts/render-check.py"`. Any FAIL blocks the
   publish. Then read one desktop and one phone screenshot from `<out>-shots/`. A WARN that the
   render was NOT checked means you check it by hand; never report it as verified.
5. **Publish** with the call the build prints: `file_path`, the `files` map, and `url` when the
   data file has `artifact_url`, so the existing link updates in place. On the first publish the
   build prints `icon` instead; write the returned URL into `artifact_url`.
6. **Report** what moved on the status tab, any warnings left, and who can open the page (the
   publish result says how it is shared). Commit the data file only when the user asks, using
   the hub's normal branch and review flow.

## Privacy

The build scans every document it would publish. It fails on international phone numbers,
token-shaped secrets, and any hub-specific pattern in `privacy.patterns` (a national phone
format, an ID number). Each failure has exactly three fixes, all in the data file's `privacy`:
- `withhold`: the doc is listed but its text is not published (incident reports, anything naming a customer or patient);
- `redact`: a pattern and its replacement, for one value inside an otherwise publishable doc;
- `allow`: only a value that is a documented example, such as a contract's sample number.

Names cannot be detected automatically. Before every publish, read each Markdown file that is
new or changed since the last `asOf` (`git log --since=<asOf> --name-only -- '*.md'`, plus
untracked files). Withhold any file that names a real person outside the team, or describes a
real case, an incident or a data repair.

## Common mistakes

| Mistake | Fix |
|---|---|
| Hand-editing the built `index.html` | Change the data file or the template, then rebuild. |
| Publishing without `url` when the data file has one | That creates a second page. Use the printed call. |
| Copying status figures from the previous page | Re-read the sources. This page's own numbers are not a source. |
| Refreshing from a dashboard or roadmap older than the change | Re-run those skills first. |
| Removing a `withhold` entry to get past an error | Never. Withhold or redact the new doc instead. |
| Adding a spec, task or principle to the data file by hand | Those rows are derived. Add the folder, file or heading in the hub. |
| A local copy of this skill in the hub's `.claude/skills/` | It shadows the plugin's version silently. Delete it once the plugin is installed. |
