---
name: task-ticket
description: "Use when a drafted task (<tasks.dir>/drafts/<slug>/description.md) needs its ticket in Jira, GitLab or GitHub, in a Product Brain hub that keeps task folders: the user says 'create the ticket for this task', 'task-ticket', 'file this from the description', or has just finished /task-description and /task-plan and has no key yet. Creates the ticket from description.md (or, given a key, updates an existing ticket's text from the changed files), moves the draft folder to <tasks.dir>/<KEY>/, and writes the links and finishing instructions into the ticket."
argument-hint: "[draft slug] [assignee name] (new ticket)  or  KEY (update an existing ticket)"
allowed-tools: [Bash, Read, Edit, Glob, Grep]
---

# task-ticket

## User Input

```text
$ARGUMENTS
```

## Which mode

- **Create** (no key in the arguments): sections 1 to 6, from a draft folder
  `<dir>/<drafts>/<slug>/`.
- **Update** (the arguments hold a key, or `<dir>/<KEY>/` exists and the user says the files
  changed): jump to **Update mode** at the end. Never run Create mode for a task that already has a
  ticket.

## What this produces

One ticket in the hub's tracker, built from the draft's `description.md`, and the draft folder
moved to `<dir>/<KEY>/` (the key and nothing else). The ticket carries a good description, links
to the files at their final place on the hub's default branch, and the hub's "How to finish" and
"Manual steps" blocks.

It creates the ticket and nothing more. It does not write or change the description's content,
does not plan, does not implement, and **never moves the ticket's status**. `/task-description`
and `/task-plan` never create tickets; this is the only skill in the family that does.

`${CLAUDE_SKILL_DIR}` is this skill's base directory (shown when the skill loads). The shared
script is `${CLAUDE_SKILL_DIR}/../../scripts/task-facts.py`; call it `task-facts` below. Tracker
details (tools, markup, quirks): [../../references/trackers.md](../../references/trackers.md).

## 1. Preconditions

- **Settings.** `python3 "${CLAUDE_SKILL_DIR}/../../scripts/task-facts.py" config` from the hub
  root. `tracker` must be set; if it is null, stop and show the user the `tasks.tracker` example
  from trackers.md. Read the conventions file it names; if the hub has its own tracker skill (for
  example a `jira` skill holding issue type ids), read its facts there too and don't re-derive them.
- **Which draft.** `task-facts resolve <argument>` takes a slug or a path; a word that is not a
  slug or a key is the assignee. With no argument it picks the only draft, or lists several and
  stops: ask which one. Never guess between drafts; another session may own one.
- The draft folder holds `description.md` and, normally, `plan.md`. If `description.md` is
  missing, stop and point to `/task-description`. If `plan.md` is missing, say so and ask whether
  to create the ticket anyway; the order is `/task-description` → `/task-plan` → `/task-ticket`.
- **Check the tracker connection first, before reading or building anything** (trackers.md,
  "Connection check"). If it fails, stop with the hint there. Do not create anything.
- Read `description.md` in full. Every section must be filled in. If a section is empty, or Status
  is `Draft` with open questions, say so and ask whether to create the ticket anyway. The ticket
  is created with whatever Status the file has.
- The draft must not already have a ticket: if `description.md` links a real key that exists in
  the tracker, stop and use that ticket instead. Never create a duplicate.

## 2. Build the ticket from description.md

- **Type**: the description's Type, mapped through `tracker.types`. If `tracker.fields` lists a
  required field for that type, ask the user to pick one of its options.
- **Summary** (under about 100 characters): `<AREA> | <what and where>`, taken from the
  description's **Problem** and **Change**, in the writer's words. The area is each repo's label
  in `areas` (from the Repos field), joined with ` - ` when there are several, e.g. `BE - FE`.
  With no `areas` set, leave the prefix out. It must not just copy the file title.
- **Assignee**: the name in the arguments, else the person running the skill. Ask only if neither
  is known.
- **Body**, in the tracker's markup (trackers.md):
  - **Context**: the Problem, two to five sentences.
  - **Expected behavior**: the Change, then the acceptance criteria as bullets, shortened but not
    reworded in meaning.
  - **UI/UX**: one bullet per row with the approved mockup preview link, or "None".
  - **Task documents**: the links block in section 5 (written with the real key, see section 4).
  - The blocks from the ticket-blocks template (`templates.task-ticket-blocks.path`): "How to
    finish" and "Manual steps". Fill in their placeholders as the template says, keep only the
    lines whose condition holds, and take each repo's review from the conventions file, at the
    level the plan's Mode sets.
- **Full URLs rule (every section).** Any file, folder, repo or document the ticket mentions is a
  full, clickable URL, never a bare file name or path. A person clicks it, and an AI agent that
  reads the ticket uses it to find the file. `task-facts links <KEY>` gives every hub URL; files
  point at the hub's default branch, because that is where the task folder ends up, so use them
  from the start, even before the folder is pushed. Every published artifact the task has (a
  mockup preview, a report) gets its full URL, never "see the artifact"; artifacts are private by
  default, so say in the hand-off that people must be given access from the artifact's Share menu.
  Before sending, scan the text for any `.md`, `.html` or task-folder mention that is not a link,
  and fix it. Code identifiers and slash commands stay as code, not links.

## 3. Show the draft and confirm

Show the user the type, summary, assignee and the full body. Creating a ticket is visible to the
whole team, so create it only after they confirm. A fix they ask for changes the ticket text only;
it never changes `description.md` (that is `/task-description`'s file).

## 4. Create the ticket and move the folder

1. Create the issue with the type, summary, assignee and body (the key is not known yet, so the
   placeholder stays in the text for now). Report the key and its link from `task-facts links`.
2. `task-facts finalize <slug> <KEY>`: it moves the draft to `<dir>/<KEY>/` and swaps the
   placeholder key and branch for the real ones in every `.md` and `.html` file of the folder. If
   it says the folder exists, stop and ask. It leaves the other drafts alone.
3. Update the ticket text once: the placeholder replaced with the real key everywhere, and the
   Task documents block from section 5. Every link points at the default branch.
4. If the mockups changed, re-run the brand check on them (`check-brand.py` from the
   `brand-system` skill in the product-brain plugin) and republish an artifact only if its text
   shows the key.
5. Nothing else in the files changes, and the approvals recorded in them stay exactly as written.

## 5. Publish and link

The task folder goes to the hub before the ticket moves to In Progress.

Task documents block (links from `task-facts links <KEY>`; include the plan only if `plan.md`
exists, else write "Plan: to be added by `/task-plan <KEY>`"; the mockups folder only if there is
one):

```
Task documents (Product Brain hub, default branch)
- Description: <files.description.md>
- Implementation plan: <files.plan.md>
- Mockups folder: <mockups>
```

- **Push prompt (always shown, at the end).** An agent that runs the ticket reads the task files
  from the git server, so they must be there before it starts. Ask the user directly: "Push
  `<dir>/<KEY>/` to the hub now? The agent needs these files on the server." Choices: push now, or
  leave it (then the ticket is **not ready to run**).
- **Push, only after a yes:** on the hub's default branch, `git pull --ff-only`, add only that
  folder (leave every other uncommitted file alone), commit, push. If the push is rejected (a
  protected branch), push a branch named after the key, open a merge request, and say the files
  are on the server only after it is merged.
- **Verify on the server** (after every push, and whenever the user says they pushed):
  `task-facts verify <KEY>`. It fetches, then prints `OK`, `MISSING on <branch>` or
  `DIFFERS from <branch>` for the constitution and every task file. `report.md` is expected to be
  missing until the agent's merge request is merged and is never checked. Until the push happens
  the links return 404; say so.

## 6. Hand-off

Report the key and its link, the assignee, and the server check. The last line is always one of
these, from `task-facts verify`:

- **Ready to run** (exit 0): "Safe to assign to the agent."
- **Not ready to run** (exit 2, or the push was declined): say which files, and that the agent
  would read missing or old files. Give the exact fix: push `<dir>/<KEY>/`.

Then the next steps:

1. `/task-plan <KEY>` if there is no `plan.md` yet.
2. Move the ticket to In Progress (the user does it; this skill does not).
3. Implement from `plan.md`.

## Update mode: `/task-ticket <KEY>`

Use it when the task's `description.md` or `plan.md` changed after the ticket was created. It
brings the ticket text back in line with the files. It never creates a ticket, moves the folder,
or changes the files.

1. **Connection check**: as in section 1.
2. **Read both sides**: the issue (body, summary, status, assignee) and the task's
   `description.md` and `plan.md` in full. If the ticket does not exist, stop: this is a Create
   case. If the folder does not exist, stop and say so.
3. **Rebuild the ticket text** exactly as section 2 does (same sections, the same template
   blocks, full URLs, review level from the plan's Mode), using the real key. Keep any lines in
   the ticket that are not generated from the files (a human's additions) and show them as "kept".
4. **Show a diff, not just the new text**: which sections changed and what was added, removed or
   reworded. If nothing differs, say "the ticket is already up to date" and stop.
5. **Confirm**, then update the body only. Title, assignee, type and status stay as they are,
   unless the user asks to change one; a changed title is confirmed separately.
6. **Leave a comment** on the ticket: "Task updated by <user> on <date>: <one line per changed
   section>. Changed files: <full URLs>." This tells the team and the agent that something changed.
7. **An agent may already be working.** If the ticket's status or a recent comment from the agent
   suggests a run is in progress, say so: a change does not reach a run that already read the
   ticket. Stop or restart the run, or give the change as a comment for it to read.
8. **Drift check** (before the diff, and again at the end). Compare the local files, the server
   copy (`task-facts verify <KEY>`) and the ticket text, and say which is newer. Local files newer
   than the server: "ticket and server disagree, push first". Ticket text newer than the files
   (someone edited the ticket by hand): show those lines and ask before overwriting them.
9. **Push prompt and server check**: as in section 5, ending with the Ready / Not ready line from
   section 6. An update that changes the ticket but leaves the server files old always ends
   **Not ready to run**.

## Do not

- Create a second ticket for the same description, or create or update one without the user's
  confirmation.
- Edit `description.md`'s content, approvals or Status.
- Change a ticket's status, delete or close tickets, or comment on other tickets. In update mode
  the only comment is the "Task updated" note on the same ticket.
- Print or ask for a token. A missing connection goes to the user.
