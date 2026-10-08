---
name: live-update
description: File (or update) the Jira ticket for a release once its epic-approval reports and release notes exist — checks that both are there, links the release's merge/pull request, uploads the local-only artifacts as attachments, and never files a duplicate. Use when the user asks to raise, file or update the Jira ticket or production-deployment request for a release, to attach the epic-approval report or release notes to a ticket, or after epic-approval and release-notes have run and the ticket is still missing.
argument-hint: "[release-branch] [--client-note-url <url>] [--approval-url <url>]"
allowed-tools: [Bash, Read, Edit, Glob, Grep]
---

# live-update

A release leaves artifacts behind: the epic-approval reports, the release-notes folder, and the merge
request that ships the release branch. This skill checks they exist, then files **one** Jira ticket
that carries them — linked where a URL exists, uploaded as a real attachment where the artifact is
only a local file.

**English only.** Every question and every ticket text is in English, whatever language the user
writes in. Do not write Finglish or any other language.

It reports and files; people decide. It never calls Jira from a script, never reads a token, and
never creates the ticket before the user has seen the draft and said yes.
`${CLAUDE_SKILL_DIR}` is this skill's base directory (shown when the skill loads).

## What is a link and what is an attachment

| Artifact | Has a URL? | In the ticket |
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
| `jira.project` | the Jira project the ticket is filed in | none — ask (Step 3) |
| `jira.component` | the Component/s value (which product this ticket is about) | none — ask (Step 3) |
| `jira.components` | optional `{repo-id: component}` override for the primary repo | — |
| `jira.issue_type` | optional issue type or Service Desk request type, if the Jira tool accepts one | the project default |
| `jira.label_prefix` | prefix of the label used to find an existing ticket | `live-update-release-` |
| `releases.primary_repo`, `releases.production_branch`, `releases.release_branch_regex`, `releases.tag_regex` | which release is "the current one" | see the script |
| `releases.out`, `approvals.out` | where release-notes and epic-approval folders live | none — a missing one is a warning |

Jira must already be connected (see the `connect-tools` skill); this skill does not set it up.

## Steps

### 1. Gather the facts

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/gather-live-update-facts.py" [--branch <name>] [--client-note-url <url>] [--approval-url <url>]
```

Read-only. Prints one JSON object: the release (`branch`, `version_label`, `source`,
`branch_state`), what epic-approval and release-notes produced, the merge request
(`merge_request.url`, from `gh` / `glab`), `attachments[]` (local files that must be uploaded),
`links`, the `jira` block (`project`, `component`, `marker`, `suggested_label`,
`suggested_summary`) and `warnings[]`. Show the user every warning. Exit 2 means the release could
not be identified — ask which branch or version, and re-run with `--branch` / `--version`.

### 2. Say what is missing before filing anything

If `epic_approval.exists` or `release_notes.exists` is false, or there is no merge request, say so
plainly and let the user choose: run the missing skill first, or file with what exists. Never file
an empty ticket silently.

### 3. Project and component

Use `jira.project` and `jira.component` from the JSON. If either is null, list the projects (and
that project's components) with the connected Jira tools, ask the user to pick, and offer to write
the answer into `brain.config.json` under `jira`. Never guess a project or component, and never
copy one from another hub.

### 4. Look for an existing ticket

Search with the connected Jira search tool: the project, and the label `jira.suggested_label`; if
the tool cannot filter by label, search the summary for `jira.marker`. Tell the user what you found.

### 5. Create, or leave alone

- **Nothing found:** draft the ticket and **show it to the user first** — summary
  `jira.suggested_summary`, the project and component, the issue type if `jira.issue_type` is set,
  the label `jira.suggested_label`, and a description containing: the merge request link and the
  published release-note link (only those that are non-null), the list of files about to be
  attached and why (they exist only as local files), and the marker. After a yes, create the ticket
  with the connected Jira create tool, then upload every file in `attachments[]` with the connected
  attach tool. If no attach tool exists, say so and list the repo paths in the description instead —
  do not pretend they were attached.
- **Found:** do not create another. Report its key and URL. If newer artifacts exist than the ticket
  has (a later `epic_approval.report_date`, a release-notes folder that was missing), offer a
  comment linking or attaching them, and only add it after a yes. Never reopen a closed ticket.

### 6. Report

Ticket key and URL; what was linked, what was attached, what was skipped and why.

## Rules

- No script calls Jira or reads a token; the Jira work is yours, with the connected tools.
- Never invent a URL. A published release-note or epic-approval page link is one the user
  supplied (`--client-note-url`, `--approval-url`) or that `facts.json` records (release note only).
- Never attach anything that could hold a secret; these artifacts should not, but check the
  filenames in `attachments[]` before uploading.
- Never duplicate a ticket that already carries the marker or the label.
- User instructions override this automation.
