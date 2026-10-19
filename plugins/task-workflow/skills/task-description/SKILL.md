---
name: task-description
description: "Use when a task, bug or small change too small for a spec needs to be written up, defined, described or scoped before planning, in a Product Brain hub that keeps task folders. To change an existing description, say it is an update and what changed. With no ticket key it writes a draft (<tasks.dir>/drafts/<slug>/description.md, one folder per draft) that /task-ticket turns into a ticket; with a key it writes <tasks.dir>/<KEY>/description.md. Triggers: when the user says 'describe PROJ-123', 'write the task', 'define this ticket', or hands over a ticket, bug report or request and wants it ready for /task-plan; and when a task's description.md is missing or a UI change in it still needs a mockup or approval."
argument-hint: "what the task is about (then run /task-plan)  |  update: what changed in an existing description"
allowed-tools: [Bash, Read, Write, Edit, Glob, Grep]
---

# task-description

## User Input

```text
$ARGUMENTS
```

## What this produces

`description.md` in the task's folder, filled in from the description template, and a mockup in
the folder's `mockups/` for each UI/UX change the writer wants one for. The description and the
plan both exist before the ticket moves to In Progress.

`${CLAUDE_SKILL_DIR}` is this skill's base directory (shown when the skill loads). The shared
script is `${CLAUDE_SKILL_DIR}/../../scripts/task-facts.py`; call it `task-facts` below.

## 0. Read the hub's settings

Run `python3 "${CLAUDE_SKILL_DIR}/../../scripts/task-facts.py" config` from the hub root. It prints
the task folder (`dir`), the key format (`key_regex`), the drafts folder, the placeholder key,
the locales, the conventions file and which template to use (`templates.task-description.path`:
the hub's own copy wins over the plugin's). If it stops with a missing key, show the user the
message; it names the key and an example. Say each warning once.

Read the conventions file in full if one is set. It holds the team's own rules: app names,
screen widths, how to capture a screen, copy and locale rules. Where it disagrees with this
skill on a team detail, it wins. If none is set, use the hub's `CLAUDE.md`.

## 1. Pin the task id

- A task folder is named by its ticket key and nothing else, matching `key_regex`: `<dir>/<KEY>/`.
  Never add a title or slug to it (`tasks/PROJ-123-fix-date/` is wrong), and never change its case.
- No key given? If the ticket exists, ask for its key. If it does not exist yet, the task is a
  **draft**: work in `<dir>/<drafts>/<slug>/` (and its `mockups/`), and write the placeholder key
  from `config` wherever the template says `KEY-NNN`. `/task-plan` then plans the draft, and
  `/task-ticket` creates the ticket and moves the folder to `<dir>/<KEY>/`. Never create a ticket
  yourself and never offer to; never make up a number.
- **One folder per draft**, so several tasks can wait for a ticket at once. `<slug>` is 2 to 5
  lower-case kebab-case words naming the change, in English (`sms-limit-international`), never a
  number. Tell the user the slug you picked. `task-facts drafts` lists the drafts already there:
  if the slug is taken by a different task, pick another. Never write over another draft; it may
  be another session's work.
- If the task's (or the draft's) `description.md` already exists, use **Update mode** below. A
  folder directly in `<dir>/` that is not a ticket key (`tasks/draft/`, `tasks/draft2/`, made before
  drafts had their own folders) is still a draft: `task-facts drafts` lists it with `"legacy": true`.
  Use it where it is, don't move it; new drafts always go in `<dir>/<drafts>/<slug>/`.

## 2. Check it is task-sized

It is a task if it is one ticket, with no new user stories and no change across domains (see
`domains.md`). If it is really a feature (a new capability, several stories, several domains),
stop and say so: it becomes a spec, through whatever spec workflow the hub uses.

## 3. Gather

- **The ticket**: read it through whichever tracker connection the session has (`tracker.kind` in
  `config`: a Jira, GitLab or GitHub MCP server, `gh`, `glab`, or the browser). If none answers,
  ask the user to paste the ticket text. If you only have someone's summary, write it up and say
  so under **Problem**.
- **The writer**: the person who wrote the task, the ticket's reporter by default. They are not
  automatically the person running this skill. Confirm the name and put it in the header. If the
  person running the skill is someone else, record them under "Written up by". The writer is
  asked first about UI/UX. Any team member may approve a row or take over the writer role. A
  human always approves, never an agent.
- **Words**: use `vocabulary.md` terms in the description. Look up code names with
  `pb find <term>` (or the hub's own wrapper, if its `CLAUDE.md` names one). Where the code uses
  another word, give both. If proposed user-facing copy conflicts with the vocabulary, raise it
  as an open question.

## 4. Write description.md

Copy the template and fill in **every** section. A section that does not apply says "None" and
gives the reason. Keep the headings and the header fields. Each acceptance criterion is
something a tester can check without the code. Put anything you are unsure of into
**Open questions**. Don't turn a guess into a criterion.

## 5. UI/UX changes

If anything a user sees changes (a screen, text, layout or interaction), give it a row and have
a team member approve it (ask the writer first). **A mockup is optional.** Ask the writer once:
"Do you want a mockup for this change?" Do not build one unless they say yes, and do not nag.

- **No mockup:** the row states the change precisely in words (what is disabled, added or moved,
  on which screen, in every locale the hub uses, with any proposed copy marked *proposed*), and
  the Mockup cell says `none, skipped by <writer>`. A screenshot of today's screen may be saved in
  `mockups/current/` and linked, but is not required. The team member approves that written
  change.
- **Mockup wanted:** follow [../../references/ui-mockups.md](../../references/ui-mockups.md) step
  by step: capture the current UI, read the real component, build the mockup from the brand,
  publish it, and record exactly what the approving team member says, in their own words, from a
  source you can link to.

Either way, a team member approves every UI/UX change, and the row records who, when and where,
in their own words. You never approve a row, and you never take an approval passed on by someone
else.

## 6. Status and hand-off

Set Status from the rule in the template; the first match wins:

1. `Draft`: an open question changes a criterion or a UI row, or a mockup the writer asked for is not built yet.
2. `Waiting for UI approval`: every requested mockup is published, and at least one row is not Approved.
3. `Ready for plan`: everything else is done.

`/task-plan` will not start until the description is `Ready for plan`. That is deliberate: a plan
built on an unapproved UI gets redone.

Show the writer the description and the mockup links. A ticketed task's `description.md` and
`mockups/` go to the hub before the ticket moves to In Progress, so offer to commit and push
them; do it only when the user says so. The next step is `/task-plan <KEY>`. For a draft, the
next step is `/task-plan <slug>`, then `/task-ticket <slug>`, which creates the ticket, moves the
folder to the key and publishes it. Don't commit a draft folder unless the user asks.

## Update mode (the description already exists)

Use it when a task's or a draft's `description.md` exists and something in it changes. The user
says it is an update and what changed. Never start from the template again. For a draft, the
user names it by slug; if they don't, run `task-facts resolve`: with several drafts it lists them,
so ask which one.

1. **Read the file in full**, and read the user's change. Name the sections it touches.
2. **Change only those parts.** Everything else stays word for word.
3. **Questions and answers.** Keep every answered question with its answer, date and source. A
   change that makes an answer wrong reopens that question: set it back to `open`, keep the old
   answer in the row as "previously: …", and ask again. Add new questions as new rows.
4. **UI/UX rows and approvals.** A row whose Change text is edited goes back to `Pending`, with
   the old approval kept as "previously approved by <name>, <date>, for the earlier text". A row
   that is not edited keeps its approval exactly as written. If a mockup was built, it is
   rebuilt and republished for the edited row only. You never approve a row, and you never carry
   an approval over to changed text.
5. **Acceptance criteria.** Edit in place and keep the numbering stable. Add new criteria at the
   end; never renumber, because `plan.md` refers to them by number.
6. **Header.** Recompute Status with the same rule as section 6, and set `Last updated` to today.
   Do not touch the ticket, the key, or the Writer field.
7. **Show what changed**, section by section (added, removed, reworded, reopened).
8. **Hand-off.** If `plan.md` exists, the next step is `/task-plan` in update mode, because the
   plan may no longer match. Then push the files and run `/task-ticket <KEY>` to bring the ticket
   text back in line. Commit and push only when the user says so.
