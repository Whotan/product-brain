---
name: update
description: Refresh the team's support-desk review page from Jira. Pulls new service-desk tickets, new customer replies and status changes since the page was last built, fact-checks each new or answered ticket with the hub's triage rules (code, graph, error tracker, Jira), drafts the reply and a suggested Jira move, and republishes the shared page so teammates can approve. Use when someone says "update the support desk", "check the support tickets again", "any new tickets or comments from the client?", "refresh the CHS page", "/support-desk:update", or when a hub's support_desk page is older than a day. Nothing is posted to Jira; posting is /support-desk:apply.
---

# Update the support desk page

One page per hub, shared with the team. This run reads it, asks Jira what changed, triages what needs a
human answer, and republishes it. **Nothing goes to Jira here.** Replies and moves are sent only by
`/support-desk:apply`, after a teammate approves them on the page.

The engine is `${CLAUDE_PLUGIN_ROOT}/scripts/desk.py` (standard library only). Run it from inside the hub;
it reads `brain.config.json > support_desk` (fields: `${CLAUDE_PLUGIN_ROOT}/reference/config.md`) and keeps
work files in `<hub>/.work/support-desk/current/`. Ticket fields: `${CLAUDE_PLUGIN_ROOT}/reference/data.md`.

```
DESK="python3 ${CLAUDE_PLUGIN_ROOT}/scripts/desk.py"
```

## 0. Preflight: stop early, say exactly what is missing

1. `support_desk` exists in `brain.config.json`. If not, offer to set it up (section "First run").
2. A Jira token: `$DESK fetch --keys <any key on the page>` fails with "No Jira token" if it is missing.
   Point the person to the hub's Jira setup (the `jira` skill's setup or `product-brain:connect-tools`).
   Never read, print or ask for the token.
3. Read the page: `Artifact` `action: "read"`, `url: support_desk.artifact_url`. The result must say the
   person is a **writer** and name the saved file. If they are not a writer, stop: the page's owner must
   share it with them with edit access on claude.ai. Do not publish a separate copy.

## 1. Pull and compare (no questions in this phase)

```
$DESK extract <saved file from the read>
$DESK fetch --since auto          # everything Jira changed since the newest activity on the page
$DESK refresh                     # updates statuses/timestamps; writes changes.json
```

`changes.json` has four lists. `status` and `unchanged` need nothing from you: refresh already wrote the
new Jira status, and dropped a suggested move that no longer exists from the new status. `new` (each with
a `seed` of the fields read from Jira) and `commented` (the customer's new public comments) need triage.

If both lists are empty, skip to step 4 and only republish when a status changed.

## 2. Triage each new or answered ticket

Use the hub's own triage rules: invoke the skill named in `support_desk.triage_skill` (if set) for each
ticket and follow its evidence rules and its reply contract; otherwise follow the rules below. Either way,
`support_desk.rules` are the team's standing rules for this desk: obey every one.

- **Verify, never answer from memory.** Read the code the complaint is about, query the knowledge graph,
  search the error tracker and Jira (duplicates, the real status of a linked task, what shipped). Each
  finding is a `checks` row: `[evidence (file:line, MR, issue, error id), confirmed|refuted|cant, finding]`.
  "cant" (can't tell) is a valid verdict; say in `move` what would settle it.
- **Re-check what we already told them.** When a customer pushes back on an earlier reply, verify that
  reply's claim again. If we were wrong, the new draft says so plainly.
- **Attachments:** look at screenshots only through a temporary folder, describe them in the `thread`
  without personal names or identifiers, and delete the files afterwards.
- **Owner decisions** (a date, a price, a commitment) are never invented. Put a bracketed placeholder in
  the reply, e.g. `[date]` in the reply's language. The page refuses to approve a reply with a placeholder,
  and apply refuses to post one. List each placeholder in your final message.
- **Reply** in `support_desk.reply_language`, ready to send, in the product's own wording. `gloss` is a
  one-line English summary. A ticket that needs no answer yet gets `"noreply": true`.
- **Suggested move**: `suggest` must be a status the ticket can reach from its current status (the page's
  flow in the config); `suggestWhy` says why in one line. Leave it `""` when it should stay.
- Never invent a task key; a confirmed bug or feature names the hub's task-description step in `move`.

Write all results to one patch file, `<work>/patch.json`:

```json
{
  "KEY-231": { "...seed fields from changes.json...": "", "app": "...", "alsoApps": [], "pri": "P2",
               "cls": "Bug", "ten": "English title", "asken": "English gist of the ask", "checks": [],
               "truth": "1-2 sentences", "move": "...", "reply": "...", "gloss": "...", "tags": [],
               "suggest": "...", "suggestWhy": "...", "thread_add": [["customer", "22 Nov", "summary"]] },
  "KEY-210": { "thread_add": [["customer", "21 Nov", "what they said, in English"]],
               "checks": [...], "truth": "...", "reply": "...", "gloss": "...", "suggest": "...", "suggestWhy": "..." }
}
```

For an existing ticket, send only the fields you change; `thread_add` appends. Then dump the saved rows
(`ArtifactData` `list` on `replies` and on `moves`, `out_dir: <work>/db`, following `next_cursor` until
done; keep the listing's `version` per document) and merge:

```
$DESK merge --patch <work>/patch.json --db <work>/db
```

It validates every ticket (fix and re-run until it prints `valid`) and writes `db-ops.json`: for each
ticket whose draft you replaced, reset its saved row to a draft (a teammate may have approved the old
text), and delete its saved move (it was for the old suggestion).

## 3. Publish

```
$DESK build --built "updated <d Mon> from Jira"
```

Publish `<work>/page.html` with the `Artifact` tool: `url: support_desk.artifact_url`, `file_path` that
file, no `capabilities` (the page keeps its database). If the publish is refused because someone published
in the meantime, start again from step 0's read: extract, refresh, then `merge` the same patch, and
build again. Never pass `force`.

Then apply `db-ops.json` with one `ArtifactData` `batch`: each entry marked `"if_version": "FILL"`
gets the version you noted; entries without it create new rows. If a pinned write fails because a
teammate saved that row since, re-read that row and decide again. Never overwrite their approval
silently. Tell the person instead.

## 4. Report (short)

- The page link.
- Counts: new, answered, status-only changes.
- One line per triaged ticket: key, what it really is, and the suggested move.
- Every placeholder an owner must fill, and every follow-up step (for example a task to write up).
- Anything you could not check, and why.

## First run (no `support_desk` section yet)

Ask, in one AskUserQuestion call: the Jira URL and service desk project key, the apps or areas to tab by,
the reply language, and whether a page already exists (its claude.ai link). Read the project's statuses
and transitions from Jira to fill `flow` and `routes` (see reference/config.md), write the section to
`brain.config.json`, then `$DESK fetch --open`, triage every ticket as in step 2 (patch with full
tickets, `data.json` starting as `{"tickets": []}`), build and publish a **new** artifact. The page needs
`capabilities: {"db": {}, "user": {}}` on that first publish. Record its URL in
`support_desk.artifact_url`, and tell the person to share it with the team with edit access.
