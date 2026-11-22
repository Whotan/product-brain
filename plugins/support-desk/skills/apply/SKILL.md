---
name: apply
description: Send what the team approved on the support-desk review page to Jira. Posts each approved reply as a public comment, makes each approved status move, and for each "Create linked issue" request writes the task up with task-workflow:task-description, creates it with task-workflow:task-ticket and links it to the support ticket, all under the runner's own Jira token; acts on reviewers' notes by redrafting; writes back what happened so the page shows it. Use when someone says "apply my approvals", "apply my decisions and notes", "send the approved replies", "post the support replies", "/support-desk:apply". Only rows a teammate approved on the page are sent.
---

# Apply the team's approvals

An approval on the page **is** the go-ahead: a teammate read the reply and pressed Approve, or picked a
move. Do not ask again for those. Everything else (drafts, on-hold rows, notes) is never sent.

Engine, config and work folder as in `/support-desk:update`:

```
DESK="python3 ${CLAUDE_PLUGIN_ROOT}/scripts/desk.py"
```

## 0. Preflight

Same three checks as update: the `support_desk` config, a Jira token (never read or printed), and an
`Artifact` read of `support_desk.artifact_url` that says **writer** and names the saved file. Comments and
moves are made as the person running this, so say whose Jira account will appear on them.

## 1. Read the page and its saved decisions

```
$DESK extract <saved file from the read>
```

Dump the saved rows: `ArtifactData` `list` on `replies`, `moves` and `links`, `out_dir: <work>/db`, following
`next_cursor` until done. Keep each document's `version` from the listing.

## 2. Plan, against Jira as it is now

```
$DESK plan --db <work>/db
$DESK fetch --keys <every key in plan.json>     # Jira may have moved since the page was built
$DESK refresh
$DESK plan --db <work>/db
```

The plan lists, per ticket, the reply to post, the move to make, and why something is **blocked**:

- a reply that still has a `[placeholder]` (an owner decision nobody filled in),
- a move approved from a status the ticket has since left (Jira moved it, so the approval is stale),
- a move to the status it is already in,
- a linked-issue request on a hub with no `support_desk.linked_issue`.

Items with a `link` are "Create linked issue" requests (section 3b).

Blocked items are reported, never forced. Resolve the `by` ids to names with `ArtifactData`
`action: "profiles"` so the report says who approved what.

**Notes.** A note on a row is a teammate's request to Claude ("make it shorter", "check whether X shipped",
"why this move?"). For each note on a row that is not approved:

1. Do what it asks, with the same evidence rules as update's triage step. If it asks for a new draft,
   redraft and re-check the facts.
2. Put the outcome in a patch for that key: changed fields, plus `"_claude"` set to a one-line answer to
   the note (shown under the note on the page). `merge` turns this into a row reset to draft with the
   answer and an empty note, so the teammate reviews the new text before anything is sent.

A note on an **approved** row: post as approved, and answer the note in `_claude` only if it asks a question.

Show the person the plan in a few lines (what will be posted and moved, and what is blocked) and continue.
Approved items need no further confirmation.

## 3. Send

```
$DESK apply --db <work>/db
```

For each item it posts the reply first; if that fails, it does not move the ticket. A move that has no
direct transition follows `support_desk.routes` (for example Resolved, then Closed); with no route it
reports the transitions Jira offered. Resolutions for statuses such as Resolved and Canceled come from
`support_desk.resolutions`. It writes `log.json`, updates the page data to Jira's new statuses, and writes
`db-ops-apply.json` (replies marked posted with the comment id, moves marked applied).

If you redrafted anything for notes: `$DESK merge --patch <work>/patch.json --db <work>/db`, which writes
its resets to `db-ops.json`. A redrafted row is never one that was just posted (notes are acted on only
for rows that were not approved), so the two files never touch the same document.

## 3b. Create the linked issues

A teammate pressed **Create linked issue** on the page: that is the request to create one, so the
"create it?" confirmation inside task-ticket is already answered. For each plan item with a `link`
(`issueType`, `brief`, `project`, `by`):

1. **Duplicates first.** Look at the ticket's `links` (issues already linked) and search
   `link.project` in Jira for the same problem. If an open issue already covers it, do not create
   another: ask the person, in one AskUserQuestion call for all such tickets, whether to link the
   existing issue instead (`$DESK link --key <KEY> --issue <EXISTING>`) or create a new one anyway.
2. **Write it up** with `/task-workflow:task-description` as a draft (no key). Hand it: the issue
   type; the brief, if given (it is the requester's own words and leads); the ticket's `truth`,
   `checks` (with their file:line evidence), `move` and the customer's ask in English (`asken`); the
   support ticket's key and link (`<jira_url>/browse/<KEY>`) as the source; and every answer in
   `support_desk.linked_issue.answers` (for example `Bug Source: Client`). Follow that skill fully:
   its own rules decide the sections, mockups and approvals. A UI change's mockup is never approved by
   you; the description goes ahead with that row open, and you say so in the report.
3. **Create it** with `/task-workflow:task-ticket <slug>`. The page request stands in for its
   section 3 confirmation; show the summary and body in your report instead. Pick required fields from
   `linked_issue.answers`, or ask. If there is no `plan.md`, create it anyway (the request was for the
   issue, not the plan) and list `/task-plan <NEW>` as the next step. Ask its push question **once**,
   at the end, for all the new task folders together.
4. **Link it**: `$DESK link --key <KEY> --issue <NEW> --db <work>/db`. It links the two in Jira
   (`linked_issue.link_type`, default Relates), refreshes the page's list of linked issues, and adds the
   write-back to `db-ops-link.json`. Linking is safe to repeat.
5. If any step stops (no tracker connection, the person declines a duplicate question, a required
   field nobody can answer): `$DESK link --key <KEY> --failed "<reason in one line>" --db <work>/db`.
   The page shows the reason and the button again. Never leave a half-created issue unlinked: if the
   issue exists, link it even if a later step failed.

Never create an issue for a ticket nobody requested one for, and never in a project other than
`linked_issue.project`.

## 4. Write back and republish

1. Apply `db-ops-apply.json`, `db-ops-link.json` and `db-ops.json` together in one `ArtifactData` `batch` (50 entries at most per batch), putting the listing's version wherever an entry
   says `"if_version": "FILL"`. If a row changed since your read, re-read it and decide again. Never
   overwrite a teammate's newer save.
2. `$DESK build --built "updated <d Mon> from Jira, approvals applied"`, then publish `<work>/page.html` to
   `support_desk.artifact_url` (no `capabilities`; on a conflict re-read, re-extract and redo steps 2-4
   for anything not yet sent; never `force`).

## 5. Report (short)

- Posted: keys, with who approved each.
- Moved: `key from → to`.
- Blocked or failed: key and reason, and what would unblock it (usually: fill the placeholder, re-approve).
- Linked issues: `support key → new key`, with type, assignee, and the description's open items
  (mockups awaiting approval, missing plan), plus whether the task folders are pushed.
- Notes answered or redrafted, now waiting for review on the page.
- Follow-ups: a confirmed bug moved to development needs the hub's task write-up step; say so per key.
