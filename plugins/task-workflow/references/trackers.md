# Trackers: Jira, GitLab, GitHub

Read by `/task-ticket` (and by `/quality-gate` for its follow-up task). `tasks.tracker.kind` in
`brain.config.json` picks the section. The skills never read, print or ask for a token: a missing
connection goes back to the user.

## Settings (`tasks.tracker`)

| Key | Required | Example | Meaning |
|---|---|---|---|
| `kind` | yes | `"jira"` | `jira`, `gitlab` or `github` |
| `url` | yes | `"https://jira.example.com"` · `"https://gitlab.example.com/team/app"` · `"https://github.com/acme/app"` | Jira's base URL, or the project whose issues hold the tasks |
| `project` | Jira: yes | `"PROJ"` | Jira's project key. For GitLab and GitHub, the prefix of a task key: issue 7 is `PROJ-7`. It also makes the placeholder key `PROJ-NNN` |
| `types` | no | `{"Story": "Task", "Technical debt": "Task"}` | the description's Type → the tracker's issue type (or GitLab/GitHub label). Unmapped types pass through |
| `fields` | no | `{"Bug": [{"name": "Bug Source", "id": "customfield_11001", "options": ["Internal", "Client"]}]}` | fields a type requires; the skill asks the user to pick an option |
| `setup` | no | `"/jira setup"` | what to tell the user to run when the connection is missing. Default: `/product-brain:connect-tools` |

`key_regex` must end in the issue number (`^PROJ-\d+$`), so the key, the folder and the issue
link always agree.

## Connection check (before reading or building anything)

Make one cheap read through whichever connection the session has. If it fails with a missing
tool, a connection error or a 401, stop and tell the user, in plain words, that the tracker is not
connected and what to run (`tracker.setup`, else `/product-brain:connect-tools`), then to run the
skill again. A connect timeout gets the same hint. Never run a setup wizard yourself.

| Kind | Tools, in order of preference | Cheap read |
|---|---|---|
| jira | a Jira MCP server (for example `mcp-atlassian`: `jira_create_issue`, `jira_update_issue`, `jira_get_issue`, `jira_add_comment`, `jira_search_assignable_users`; load them with ToolSearch first) | find the person running the skill with the assignable-users search in `project` |
| gitlab | a GitLab MCP server (work-item tools), else `glab issue …` | read the project, or `glab issue list -R <project> --per-page 1` |
| github | a GitHub MCP server, else `gh issue …` | `gh issue list -R <owner/repo> --limit 1` |

## Writing the ticket

| | Jira | GitLab · GitHub |
|---|---|---|
| Markup | wiki markup: `h2.`, `* ` bullets, `{{code}}`, `[label|https://…]`, `{noformat}` boxes | Markdown: `##`, `- `, backticks, `[label](https://…)`, fenced code blocks |
| Key after create | the issue key the API returns | `<project>-<iid or number>` |
| Link to give people | `<url>/browse/<KEY>` (never the REST `self` URL) | `task-facts links <KEY>` → `ticket` |
| Type | issue type, mapped through `types` | a label named after the type, mapped through `types` |
| Assignee | resolve the display name with the assignable-users search | the user name; `@me` for the person running it |

**Jira quirks (the MCP server rewrites some text on save):**

- It escapes `_` to `\_`, which breaks a link. Never link a URL with an underscore in it (for
  example GitLab's `/-/merge_requests`): link the repo root instead. Write code identifiers that
  hold underscores in words, or inside `{{…}}`.
- A line starting `1.`, `2.` becomes a `#` list item. Use bullets, or plain lines inside
  `{noformat}`.
- Inside `{noformat}` the URLs are plain text, so they copy cleanly. That is the one place a URL is
  not a link.

## Reading and updating

- Read: `jira_get_issue` · the GitLab work-item read or `glab issue view` · `gh issue view`.
- Update the body only: `jira_update_issue` (description) · `glab issue update --description` ·
  `gh issue edit --body-file`.
- Comment: `jira_add_comment` · `glab issue note` · `gh issue comment`.
- Never change the status or state, and never delete or close an issue.
