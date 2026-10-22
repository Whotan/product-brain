# The `finance` config

Lives in the hub's `brain.config.json` under `"finance"` (one hub = one project), or in a file passed with
`--config`. Keys starting with `_` are notes for people; the script ignores them. Required keys are marked **R**;
`build` stops and names any that are missing. `init` writes a first draft from the finance tab.

| Key | Meaning |
|---|---|
| `id` | Folder name for the work files (`.work/finance/<id>/`); default: the name in lower case. |
| `name` **R** | Project name shown in the report. |
| `mode` | `project` (one finance row per month, no epics) or `workstream` (rows per epic-based workstream, needs `workstreams`). `init` reads it from the tab. |
| `rules` | The organisation's and project's billing rules in plain words, read before every run (e.g. which shared projects are billed, which are internal). |
| `jira.url` **R** | Jira Server/DC base URL. |
| `jira.projects` **R** | Project keys whose Tempo worklogs are fetched. |
| `jira.filter_id` | Jira filter = billing scope; only issues in it count. `null` = all fetched issues. |
| `jira.home_project` **R** | Main project: its issues must have a Tempo account; Tempo allocations go on it. |
| `jira.extra_scope` | `[{project, components, include}]`: shared projects where a component names the client (e.g. a DevOps project). `include: "bill"` counts them; `"report"` (default) lists them in the report only. |
| `jira.shared_projects` | Shared project keys `check` looks into for the client's component (e.g. `["OPS"]`). |
| `jira.tempo_account` | Tempo account key; worklogs on another account are flagged. Optional. |
| `jira.epic_link_field`, `jira.epic_name_field` | Field names (default `Epic Link`, `Epic Name`). |
| `billing.rate`, `billing.currency`, `billing.currency_symbol` | Hourly rate; required only with `sheets.invoices`. |
| `billing.weekend_days` | Day names off work (Tempo allocations), default `["Saturday","Sunday"]`. |
| `billing.todo_statuses` | Statuses flagged when billed (upper case). |
| `billing.sla_reserved_hours` | SLA tabs: default hours reserved (not invoiced) per month; sum(Billable) = this + sum(Invoiceable). `--reserved` overrides it for one month. |
| `other_projects` | Workstream mode: `{default_people, default_workstream, default_epic}` for worklogs on other keys without an epic of ours. Listed people go to `default_workstream` with epic label `default_epic` (`{month}`, `{year}`); everyone else is left out. |
| `sheets.invoices`, `sheets.finance` (+ `_test`) | Google Sheet ids. |
| `sheets.invoice_tab_name` | New invoice tab name: `{next_month} {next_year}` / `{month} {year}`. |
| `sheets.invoice_label` | Label of each invoice row, `INVOICE {n}`. |
| `finance.tab` **R** | Finance tab name. |
| `finance.header_rows` | 1, or 2 when names sit in row 1 and Planned/Logged/Billable in row 2. |
| `finance.row_key_columns` | Columns holding the row's label and month, default `["A","B"]`. |
| `finance.row_label` | Project mode: the column-A label of the month rows; `init` fills it. |
| `finance.logged_counts_non_billable` | Logged includes non-billable worklogs. Default true in project mode, false in workstream mode. |
| `finance.month_label` | How the month column writes a month, default `{month}` (English name). |
| `finance.layout` | The project's agreed finance-tab rules (text, for you to follow). |
| `client_csv.filename` | e.g. `Client_{from}_{to}.csv`. Leave it out when the project sends no client CSV. |
| `client_csv.date_format` | Tokens `YYYY M MM D DD H HH mm`, default `M/D/YYYY H:mm`. |
| `client_csv.columns` | `[{header, field}]`, fields: `epic issue_key summary billed_h logged_h full_name status project_name project_key account_key account_lead account_customer started comment`. |
| `client_csv.drive_folder` | Drive folder for the CSV. |
| `people` **R** | `[{name, role, jira_name?, jira_username?, finance_columns: {planned?, logged, billable, invoiceable?}}]`. `name` = the finance label; `jira_name` when the Jira display name differs; `jira_username` skips the user search in `plan`. `finance_columns` are header texts (written by `init`); a header shared by several columns resolves to the one nearest left of the person's Logged column. |
| `workstreams` (workstream mode) | Ordered `[{match, finance_row, invoice_header, invoice_group}]`; first regex match on the epic name wins; order = order on the invoice. |
| `invoice_groups` | `{"1": "meaning", …}` for the PM. Unmapped epics go to group 9. |
| `descriptions` | Fallback line text: `{"<finance row or invoice header>": {"<person>" or "*": text}, "*": {…}}`. |
| `tempo_planning.start_time` | Allocation start time, default `09:00`. |
| `preferences` | `pm`, `description_style`, `invoice_split`, `downpayment`, `planning_role_order`, `planning_roles`, `planning_notes`, `role_by_project` (`{"<key>": "<role>"}` for `check`'s role guess), `sla_reserved_from` (roles the SLA proposal takes the reserved hours from, default `["PM", "DevOps"]`): the PM's way of working, read by you. |
