---
name: monthly-billing
description: Month-end billing for a Jira Server/Data Center + Tempo project, run by the project's PM from inside the project's Product Brain hub. Pulls last month's Tempo worklogs (the project's Jira project, plus the client's component in shared projects), compares them with the project's tab in the finance workbook, writes the month's Logged/Billable cells after one review the PM approves, and plans next month's hours (Planned cells + Tempo allocations). Optional per project: split by epic (workstreams), a client worklog CSV and an invoice tab, SLA invoiceable hours. The first run sets the project up. Use when a PM says "monthly billing", "month-end billing", "update the finance sheet", "set up billing for <project>", "prepare the client CSV", "invoice <month>", or "plan next month in Tempo".
---

# Monthly billing

One script, one config per project: `scripts/billing.py <cmd>` reads the hub's `brain.config.json > finance`
(one hub = one project; `--config FILE` for a config kept elsewhere). The hub is found by walking up from the
current folder to `brain.config.json` (`--hub` to override). Billing period = the previous calendar month
(`--month YYYY-MM`). Work files go to `<hub>/.work/finance/<id>/<month>/`. The script only reads Jira/Tempo
(except `plan --apply`) and never writes Google Sheets: you do that from its JSON, after the PM's approval.
Standard library only; `preview` alone needs the optional `openpyxl`. Config fields: `reference/config.md`.

**Read `finance.rules` in the config first.** They are the organisation's and the project's billing rules
(e.g. "hours in the shared DevOps project with this project's component are billed with the project",
"meeting projects are internal, never billed"). Follow them; the mechanisms below carry them out.

## The shape of every run: ask once, work alone, one review, then apply

The PM may be using this for the first time and should not have to sit in the chat answering questions one
by one. Every run has four phases, and you tell the PM this shape at the start:

1. **Questions, all at once** (phase A): session settings, the plan, then every question you can ask before
   looking at the data, in one or two AskUserQuestion calls.
2. **Work alone** (phase B): fetch, export, build, audit, plan proposal. Ask nothing in this phase; collect
   every decision the data raises for the review.
3. **One review** (phase C): one report the PM reads in one place, with every change you will make and every
   decision you need, each with its evidence. Then one AskUserQuestion batch for the decisions and the approval.
4. **Apply and close** (phase D): write everything, read it back, show the result and the highlights.

**How to ask.** Make every question a quick confirmation the PM can answer without opening Jira or the sheet:
find the answer yourself, then ask "Is it X?" with choices (X / the next candidates / Other). Each question
says, in plain words for someone new to the skill: **what** it is about, **where** (tab, cell, person),
**the evidence** (issue keys with Jira links, dates, hours, the current value), and **what each option does**.
Never ask "is there a reason?" without listing the worklogs it is about. Ask for typed text only where the PM has
to explain something (a reason for a note, a rate). Up to four questions per AskUserQuestion call.
**Never guess a business value** (rate, scope, who bills, mappings, splits, the PM's name): if the data doesn't
show it, ask, or leave it `null`.

## Phase A: questions, all at once

1. **Session settings, as a question** (you can't read or change them yourself). AskUserQuestion: "For this run
   I recommend the most capable model, effort **High** (first setup) / **Medium** (monthly run), and
   permission mode **Default** (asks before each tool). Is your session set like this?" Options: "Yes" /
   "I changed it now" / "Continue as it is". Why: the script does the arithmetic, but the judgement calls
   (differences, exceptions, roles, the SLA split) land directly in finance and invoice figures; Default
   permissions because the run writes to the shared finance sheet and to Tempo.
2. **The plan, in five short lines**, so the PM knows what will happen and when they are needed:
   > 1) A few questions now. 2) I fetch Jira/Tempo and the finance sheet and check everything on my own (you
   > can leave). 3) I give you one review report: every change, before → after, and the decisions I need.
   > 4) After your OK I write it (only new data; a named version first, so you can revert). 5) Summary and a
   > few highlights of the month.
3. **The questions you can ask before the data**, in one or two calls:
   - **Month**: "<last full month>, right?" If the PM picks the current month, say in the option text that it
     is partial and that later hours won't overwrite what is written now.
   - **First run only (no config)**: the setup checks (section 0).
   - **Projects with an invoice**: downpayment this month?
   - **SLA tabs**: "Reserved hours this month: <default>, right?"
   - **Next month's plan**: "Plan next month too? Total hours: <last month's total> / <3-month average> / I'll
     type it / Not now." The split per person comes in the review.
4. Then say "I'll come back with the review" and start phase B.

## 0. Setup checks (first run: no `finance` section yet; part of phase A)
1. Download the finance workbook as xlsx (Drive `download_file_content`, export mime xlsx) to
   `<hub>/.work/finance/finance.xlsx`.
2. `check --name "<project name from the PM's prompt>" --jira-url <url> [--shared <KEY,...>] --finance <xlsx>`
   (read only) finds what it can: the Jira project and key, the client's component in each shared project
   (e.g. a DevOps project with one component per client), the finance tab, the mode (from the tab: one row per
   month = project mode; several rows per month = workstream mode, not asked), the people who logged in the
   last 3 months vs the tab's columns, and a role guess per person (keywords in everything they logged,
   `preferences.role_by_project`, Tempo team memberships).
3. Ask as double-checks, with the evidence in the question:
   - **Jira project**: "Acme → ACM (Acme Platform), right?" (the name from the prompt, its best match and key).
   - **Shared projects**: "Component 'Acme' in OPS (its logs are billed with the project), right?" Whether such
     hours are billed is an organisation rule: ask once, then record it in `finance.rules`.
   - **Finance tab**: "Tab 'Acme', right?"
   - **People without columns** (logged in Jira in the last 3 months): "Jane (1.8 h) and Omar (1 h) have no
     columns. I'll add Planned/Logged/Billable columns for them after the last column, formatted like the
     others; you'll see the exact columns in the review. OK?" A column with no logs for 3 months is only
     mentioned. Headers `init` could not read (`unread_headers`) go here too.
   - **Roles**: "Jane = BE, Omar = FE, Lea = Design, Sam = DevOps, right?" (from the guess).
   - **SLA reserve** (only when the tab has Invoiceable columns): "Default reserved hours per month: 8, right?"
   - **Organisation rules**: "Any billing rules I should keep for every month (e.g. internal meeting projects
     never billed)?" → `finance.rules`.
   - **Offer**, as a choice: "I can also produce a client worklog CSV and an invoice tab with a description per
     line drawn from the tasks. Want them?" Only on yes ask for the rate, currency and invoices sheet.
4. `init --finance <xlsx> --tab "<tab>" --name "<Name>" --jira-url … --keys <KEY> --write` writes the hub's
   `brain.config.json > finance` (mode and row label from the tab, people and their headers). Add the confirmed
   `extra_scope` entries, `shared_projects`, roles, `jira_name`s and `rules`.
5. On a later run, re-run `check` only when the report shows new people or the tab's columns changed; `init`
   on an existing config keeps the confirmed values and only refreshes the headers and adds new people.

## 1. Rules (every project)
- **Two modes**, read from the finance tab (`mode`). **project**: one finance row per month
  (`finance.row_label | <Month>`), per person Logged/Billable = the Tempo totals of the scope; no epics needed.
  **workstream**: rows per workstream (a block of month rows per workstream), see next rule.
- **Workstream mode only: workstream = Epic Link** of the worklog's issue (subtask → parent's epic), mapped by
  `workstreams[].match` (regex on the epic name) to a finance row, an invoice header (`{epic}`, `{month}`,
  `{year}`) and an invoice group. Worklogs on other project keys count only with one of the project's epics;
  `other_projects.default_people` without one go to `default_workstream` and are flagged.
- **Scope** = `jira.projects` (narrowed by the Jira filter `jira.filter_id` when set) plus `jira.extra_scope`:
  shared projects where a component names the client. `include: "bill"` counts them like the project's own
  worklogs; `include: "report"` lists them in the report only. Which is which comes from `finance.rules`.
- **Logged and Billable.** Billable = Tempo billable hours. In project mode Logged = all time logged in the
  scope, billable or not (`finance.logged_counts_non_billable`, default true in project mode); in workstream mode
  the default is the time spent of billable worklogs only. Only billable worklogs go into the client CSV and the
  invoice.
- **Logged but not billed.** The report lists, per person, every worklog billed below its logged time (date,
  issue with link, logged, billable, task, worklog text). In the review, show that list in the question itself
  and ask only whether there is a reason to note. A reason goes into `adjust.json` as a note-only entry
  (`{"person", "reason"}`): the billable cell gets a note "Logged X, billable Y. <reason>"; no value changes.
- **Only new data; existing values never change.** The skill writes only cells that are empty now
  (`finance_cells.json`; a 0 counts as empty only in a month row with no figures yet). Cells that already hold
  the same value are skipped; cells that hold a different value are left as they are and listed under
  "Not written", for the PM to fix separately.
- **The month row it writes into gets correct totals.** `build` checks C/D/E of that row
  (`finance_formula_fixes.json`): a formula that leaves out a person's column, or a typed number, is replaced by
  `=SUM(...)` over every person's column (SUM skips a stray text cell). This is part of the change, shown in
  the review; you don't ask about it separately.
- **People without columns get columns.** Someone who logged in scope but has no columns gets Planned/Logged/
  Billable columns appended after the last column, named like the others, formatted like the right-most
  person's columns (`finance_new_columns.json`); their cells and the totals already use them.
- **A missing month row is created** (project mode): `finance_new_rows.json`, inserted under the month before,
  its format copied, A/B = label and month, its formulas moved to the new row, C/D/E over every person's column.
  In workstream mode, rows are added by `finance.layout`.
- **Earlier months: ask, then fix or flag.** `audit` lists total formulas of earlier months that leave out a
  column, typed totals, and earlier cells that differ from Jira. In the review, ask once: "Fix these earlier
  formulas too, or only flag them?" Earlier values are never changed by the skill; they stay flags.
- **Jira vs finance**: a difference is a one-off exception the PM agrees for that project and month (finance-tab
  comments show past ones); never carry one over to another project or month as a rule. For an empty cell the
  PM wants written differently: `adjust.json` (`[{"person", "workstream"?, "logged"?, "billable"?,
  "reason"}]`, `--adjust`): the cell gets that value and a note "Jira <kind>: <x>. <reason>".
- **Downpayments** (projects with an invoice): ask in phase A (`preferences.downpayment`). Pass them with
  `--downpayment file.json` (`[{"workstream","person","hours","label","header"[,"group"]}]`).
- **Invoice split** by `invoice_group` (meanings in `invoice_groups`); propose it in the review
  (`preferences.invoice_split`); change it per run in `overrides.json` (`{"<header>": {"invoice": n}}`).
- **Line descriptions** follow `preferences.description_style`, drawn from that person's tasks in the block
  (`invoice.json > lines[].tasks`) and their worklog descriptions. Write them into `overrides.json`
  (`{"<header>": {"lines": {"<person>": "..."}}}`), rebuild with `--overrides`. Config descriptions are only
  the fallback; lines without one are listed as guessed.
- The finance tab belongs to finance. Keep to `finance.layout` (the project's agreed rules).
- **SLA tabs with Invoiceable columns** (`billing.sla_reserved_hours` set, people have
  `finance_columns.invoiceable`): Logged/Billable come from Jira as everywhere. The SLA plan reserves a default
  number of hours each month that are not invoiced, so **sum(Billable) = reserved hours + sum(Invoiceable)**.
  The PM decides who carries the reserved hours (usually part of the PM's and DevOps' hours). The review shows
  the proposal (reserved hours split equally across `preferences.sla_reserved_from`, default PM + DevOps) as a
  question: "Use this split / Change it". Then rebuild with `--invoiceable split.json`
  (`{"_source": "pm", "<person>": hours, …}`). The total must add up (the report says so if it doesn't).

## Phase B: work alone (ask nothing)
1. `python <skill>/scripts/billing.py fetch --month YYYY-MM` (needs `JIRA_PERSONAL_TOKEN`; never print it).
   Fallback without a token: export the Tempo report as a CSV in the client format and run `import --csv FILE`.
   Also fetch the two or three months before if their `records.json` is missing (for the audit and the plan).
2. Download the finance workbook as xlsx to `<hub>/.work/finance/<id>/<month>/finance.xlsx`.
3. `build --month YYYY-MM --finance <xlsx> [--downpayment …]` → `report.md` (opens with "Changes to apply":
   new columns, new rows, total fixes, every cell with person and value, notes), `finance_cells.json`,
   `finance_new_columns.json`, `finance_new_rows.json`, `finance_formula_fixes.json`, `finance_compare.json`,
   `highlights.json` (and the client CSV / `invoice.json` when set up).
4. `audit --month YYYY-MM --finance <xlsx>` → `audit.md` (earlier months).
5. If the PM asked for a plan: `history`, then the split per person (section 3), then `plan … --finance <xlsx>`
   (dry run).
6. Draft what needs the PM: reasons for logged-but-not-billed, the SLA split, invoice descriptions, the plan
   split, earlier-month formulas (fix or flag), and anything odd (billable time on TO DO issues, billed above
   logged, other accounts, unmapped epics). Worklogs without a description are normal: don't flag them.

## Phase C: one review
1. Write `<hub>/.work/finance/<id>/<month>/review.md` and link it: the plan of changes in order (from
   `report.md` "Changes to apply", with before → after for every cell, column, row, formula and note; the
   Planned cells and Tempo allocations if planning), then "Decisions I need" with the evidence for each, then
   "Flags only" (audit, not-written cells). State at the top: "Nothing already in the sheet changes, except
   <the total fixes listed>." Keep it short enough to read in a few minutes.
2. In the chat, a five-line summary (totals, number of changes, decisions needed) and the link.
3. One AskUserQuestion batch (two calls at most): each decision as a self-contained question, plus the
   approval: "Apply all the changes in review.md?" (Yes / Yes, but … / Not now).

## Phase D: apply and close
1. Load the Google Workspace guidance if available. **Name a version first** of every shared sheet you change
   (File → Version history → Name current version, in the PM's signed-in browser; the API cannot name
   versions), and tell the PM its name so they can revert.
2. **Finance tab**, in this order: new columns (append, headers, copy the format of `copy_format_from`); new
   rows (`insertDimension`, startIndex = `insert_after_row`, endIndex +1, `inheritFromBefore: true`, then the
   row's `cells` with `update_formulas`); total fixes (`finance_formula_fixes.json`, `update_formulas`);
   `finance_cells.json` (values only); notes (`updateCells` with `fields: "note"`); then the earlier-month
   formula fixes if the PM chose "fix".
3. **Invoices sheet** (only when `sheets.invoices` is set): add tab `sheets.invoice_tab_name` (duplicate the
   previous tab, clear its values and formats, write the rows from `invoice.json`: Description | Amount |
   Price | Total, `=B*C` per line, Total row = SUM over **all** lines). Then copy formats **by row type** from
   the previous tab with `copyPaste PASTE_FORMAT`: a line row to every row first, then the invoice label row,
   each workstream header row and the Total row. Upload the client CSV to `client_csv.drive_folder`.
4. Plan, if approved: Planned cells, then `plan … --apply` (section 3).
5. Read everything back: the month's totals (C/D/E) equal the report; SLA Invoiceable = Billable − reserved;
   planned total = `total_hours`; each Tempo `planned_hours` equals its figure. Re-run `init` on the config so
   new columns and people are saved.
6. **Close**: a short summary (what was written, the version name, what stays flagged), then the two
   highlights from `highlights.json > picked` in a block that stands out, e.g.

   > 🏆 **Most billable hours:** Jane, 110 h
   > ✍️ **Clearest worklogs:** Omar, 100% of 81 worklogs with a description

   and one line: "Worth a thank-you." (`highlights.json > all` has the other figures if the PM asks.)

## 3. Plan the next month (in phase B, approved in phase C)
1. Default: **project level**, one Tempo allocation per person for the whole month. In phase A offer, as a
   choice, more detail: "If you can, give me the epics (workstreams) or issues."
2. Split the total per person: `history --month <next> [--months 3]` (billable hours per row × person in the
   earlier months), the roles in `people[].role`, and (when epics or issues are given) their open tasks with
   assignees and original estimates (Jira search). Flag anyone above their recent monthly hours. Show the split
   in the review with a one-line reason per person.
3. Write `<hub>/.work/finance/<id>/<next>/plan.json` (`[{"person": "...", "hours": n}]` in project mode; add
   `"workstream"` (the description) and `"finance_row"` in workstream mode) and run
   `plan --month <next> --plan … --finance <xlsx>` (dry run: Planned cells, new rows, the Tempo allocations it
   would create with working days and seconds per day).
4. After the approval: insert `new_rows` if any, write the Planned cells (only empty ones; `not_written` lists
   any that already hold a value), then `plan … --apply` creates the allocations on the home project
   (`/rest/tempo-planning/1/allocation`, AllocationBean: `assignee.key` = username, `planItem` = project, the
   whole month, no reviewer). `secondsPerDay` is set over the working days (`billing.weekend_days`) and
   corrected after a read-back. Allocations are created as the owner of the token, so each PM runs this with
   their own token.

## Google Sheets lessons
- With a filter hiding rows, `copyPaste` is rejected for the whole batch. Never remove the PM's filter: insert
  rows with `inheritFromBefore` and write formats (`repeatCell`, `updateBorders`) and formulas
  (`update_formulas`) explicitly. After inserting rows, rewrite ranges (block totals, SUMIFS) to cover them.
- Always send a field mask (`fields`) with `repeatCell` / `updateCells`, or other formatting is wiped.
- Read back after every write; a totals mismatch means stop and ask.
