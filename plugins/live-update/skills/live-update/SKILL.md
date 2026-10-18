---
name: live-update
description: File the Jira Service Desk request (for example "Production Deployment") for a release once its epic-approval reports and release notes exist — checks that both are there, then fills in the customer-portal form in the user's signed-in browser (summary, description, the Component/s that says which product, attachments), links the release's merge/pull request, and never files a duplicate. Use when the user asks to raise, file or create the Jira ticket, production-deployment request or deployment ticket for a release, to attach the epic-approval report or release notes to a ticket, or after epic-approval and release-notes have run and the ticket is still missing.
argument-hint: "[release-branch] [--client-note-url <url>] [--approval-url <url>] [--merge-request-url <url>]"
allowed-tools: [Bash, Read, Edit, Glob, Grep]
---

# live-update

A release leaves artifacts behind: the epic-approval reports, the release-notes folder, and the merge
request that ships the release branch. This skill checks they exist, then files **one** request on the
team's Jira Service Desk customer portal — the same form a person fills in by hand: pick the request
type, write a summary and description, choose the Component/s (which product the release is for), add
attachments, press Create.

It is **only for this request.** Every other Jira ticket (issues, bugs, scope checks) keeps its own flow;
nothing here changes it. It uses **no Jira MCP connector and no API token.** The agent drives the portal in a browser the user is
already signed in to, so the request is raised as that user.

**English only.** Every question and every ticket text is in English, whatever language the user
writes in. Do not write Finglish or any other language.

It reports and files; people decide. It never types a username, password or token, and never presses
Create before the user has seen the filled-in form and said yes.
`${CLAUDE_SKILL_DIR}` is this skill's base directory (shown when the skill loads).

## What is a link and what is an attachment

| Artifact | Has a URL? | In the request |
|---|---|---|
| Merge / pull request of the release branch | yes | **link** in the description |
| Release note published as an Artifact | only if the user supplies it | **link** |
| epic-approval reports (`<repo>.md`, `README.md`) | no — plain files in the hub | **attachment** |
| epic-approval page (`approval.html` in `.work/epic-approval/`, made by epic-approval Step 6, not committed) | only if published as an Artifact and the user supplies the URL | **link**; **attachment** when no URL is known |
| release-notes `internal.md`, `client.pdf`, `facts.json` | no | **attachment** |
| release-notes `client.html` | no, unless published | **attachment**, only when no published URL is known |

## Config

| Key | Used for | Default |
|---|---|---|
| `live_update.portal_url` | the customer portal, e.g. `https://jira.example.com/servicedesk/customer/portal/8` | none — ask (Step 3) |
| `live_update.request_type` | the request type's name on the portal, e.g. `Production Deployment` | none — ask (Step 3) |
| `live_update.request_type_id` | optional: its id (the number in `.../portal/8/create/66`), for a direct link to the form | pick by name |
| `live_update.component` | the exact Component/s option to choose — which product this release is for | none — ask (Step 5) |
| `live_update.components` | optional `{repo-id: component}` override for the primary repo | — |
| `live_update.require` | optional list of `epic_approval`, `release_notes`, `merge_request` that must exist before the request may be filed (a hard gate) | `[]` — nothing is required |
| `releases.primary_repo`, `releases.production_branch`, `releases.release_branch_regex`, `releases.tag_regex` | which release is "the current one" | see the script |
| `releases.out`, `approvals.out` | where release-notes and epic-approval folders live | none — a missing one is a warning |

## Steps

### 1. Gather the facts

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/gather-live-update-facts.py" [--branch <name>] [--client-note-url <url>] [--approval-url <url>] [--merge-request-url <url>]
```

Read-only; it does not touch Jira or a browser. Prints one JSON object: the release (`branch`,
`version_label`, `source`, `branch_state`), what epic-approval and release-notes produced, the merge
request (`merge_request.url`; see 1b), `attachments[]` (local files that must be
uploaded), `links`, the `request` block (`portal_url`, `request_type`, `create_url`, `requests_url`,
`component`, `marker`, `suggested_summary`, `missing_keys`), the `gate` block (`require`, `missing`,
`satisfied`, and `pipeline`: the steps in release order, each `done` or not) and `warnings[]`. Show the user every
warning. Exit 2 means the release could not be identified — ask which branch or version, and re-run
with `--branch` / `--version`.

### 1b. Find the merge request through any connection

No particular tool is required. The script uses `gh` / `glab` only when they are installed and signed
in. When `merge_request.url` is null and `merge_request.lookup` is set, find the MR/PR yourself, with
the first connection that answers:

1. **A GitLab or GitHub MCP server**, if this session has one: list the merge/pull requests of
   `lookup.project` whose source branch is `lookup.source_branch` (any state).
2. **The browser**: open `lookup.search_url`, the host's MR/PR list filtered to that branch.
3. **The user**: ask for the link.

Then re-run Step 1 with `--merge-request-url <url>`. That URL counts as found, including for
`live_update.require`. Pass only a URL that you read from the host or that the user gave you, never
one you built yourself. If no connection finds an MR, the branch has none yet, and Step 2 offers to
open one.

### 2. Walk the release's steps, in order

Show the user the checklist from `gate.pipeline`, in release order — a release is reviewed, then
merged, then described, then ticketed:

1. **epic-approval** — the approval reports (before the merge).
2. **merge request** — the release branch's MR/PR (`open-release-mr.py`, step 9 of release-notes).
3. **release-notes** — the release-notes folder (after the merge and tag, so it describes what shipped).
4. **the request** — this skill.

For each step that is not `done`, offer to do it now instead of just reporting it: run the
`epic-approval` skill, open the MR (the plan first, `--create` only after a yes), run the
`release-notes` skill. Take one step at a time, re-run Step 1 after each, and come back here. A
release that has no tag yet cannot have final release notes; say so rather than writing them early.

**The gate.** When `gate.require` is not empty, those artifacts are mandatory: while `gate.missing`
is not empty, **do not fill in the form, and do not offer to file with what exists** — walk the missing
steps, and stop if the user declines. Say that the hub requires them and that `live_update.require`
is the key that says so. When `gate.require` is empty, nothing is mandatory: say what is missing and
let the user choose between doing the step first and filing with what exists. Either way, never file
an empty request silently.

### 3. Portal, and request type

If `request.portal_url` or `request.request_type` is null, ask the user for the portal address and the request
type's name, and offer to write them into `brain.config.json` under `live_update`. Never guess either, and
never copy them from another hub.

### 4. Open the portal and look for an existing request

Use a browser the user is already signed in to Jira on — Claude in Chrome (their real browser) is the
natural choice; the built-in browser pane works too once the user has signed in there themselves. If a
page asks for a login, **stop and ask the user to sign in**; never type credentials.

Open `request.requests_url` (the user's own requests) and search it for `request.marker`. If a request
carrying the marker exists, **do not create another**: report its key and link, and stop. If newer
artifacts exist than it has (a later `epic_approval.report_date`, a release-notes folder that was
missing), offer to add a comment with them, and only do it after a yes.

### 5. Fill in the form — without pressing Create

Open `request.create_url` when it is set; otherwise open `request.portal_url` and choose the request type
named `request.request_type`. Check the page heading shows that request type. Leave "Raise this request
on behalf of" as it is. Then:

- **Summary:** `request.suggested_summary`.
- **Component/s:** open the dropdown and choose `request.component` exactly as written. If it is null, or
  not among the options, read the options off the page, ask the user which product(s) this release is
  for, and offer to save the answer as `live_update.component` (or `live_update.components` per repo). Never guess a
  component.
- **Description**, plain text, one item per line: the merge request link and the published
  release-note and epic-approval page links (only those that are non-null), the names of the files
  attached below and why (they exist only as local files), and the marker.
- **Attachment:** upload every file in `attachments[]` with the browser's file-upload ability (Claude
  in Chrome's file upload into the Attachment box). If the browser you have cannot upload, list the
  absolute paths and ask the user to drag them into the box, then wait for them to say it is done.
  Never claim a file was attached without seeing its name listed on the form.

### 6. Show the form, then create

Tell the user exactly what is in the form — summary, component, description, the attached file names.
Press **Create** only after a clear yes. Then read the confirmation page and report the request key and
its URL.

### 7. Report

Request key and URL; what was linked, what was attached, what was skipped and why.

## Rules

- No script calls Jira or opens a browser; the portal work is yours, in the user's own session.
- Never type or ask for a password, token or one-time code; if signed out, the user signs in.
- Never press Create before the user has seen the filled-in form and said yes.
- Never invent a URL. A published release-note or epic-approval page link is one the user
  supplied (`--client-note-url`, `--approval-url`) or that `facts.json` records (release note only).
  A merge request link is one `gh` / `glab` returned, or one that Step 1b read from the host or got from the user.
- Never attach anything that could hold a secret; these artifacts should not, but check the
  filenames in `attachments[]` before uploading.
- Never create a second request for a release whose marker already appears in the user's requests.
- User instructions override this automation.
