# `brain.config.json > support_desk`

One section per hub, one service desk project per hub. Everything team-specific lives here, not in the plugin.

| Field | Required | Meaning |
|---|---|---|
| `jira_url` | yes | Jira Server/Data Center base URL. |
| `project` | yes | The service desk project key; also the page's search label and local-storage prefix. |
| `artifact_url` | after the first run | The shared review page on claude.ai. Every teammate who runs the skills needs **edit** access to it. |
| `title` | no | Page title. Default `<project> Support Desk`. |
| `token_env` | no | The environment variable holding each person's own Jira personal access token. Default `JIRA_PERSONAL_TOKEN`. Read from the environment or from the `env` block of `<hub>/.claude/settings.local.json`; never printed. |
| `triage_skill` | no | The hub's own triage skill (its evidence rules and reply contract). `update` invokes it for each ticket. |
| `reply_language` | no | Language of the replies, for example `fa`. |
| `customer_label` | no | What the page calls the requester side ("Clinic", "Customer"). Default `Customer`. |
| `rules` | no | Standing rules for this desk, in plain sentences. Both skills obey every one. |
| `apps` | no | `[[id, label], ...]`: the page's tabs (product areas). Each ticket has one `app`. |
| `tags` | no | The tags a ticket may carry; the page filters by them. |
| `closed` | no | Statuses the page counts as closed. Default `Closed, Resolved, Done, Canceled`. |
| `flow` | no | `{flowName: {status: [statuses a move may target]}}`: the moves the page offers. Copy them from the Jira workflow. |
| `type_flow` | no | `{issueType: flowName}`. Types not listed use `default_flow`. |
| `default_flow` | no | The flow for every other issue type. |
| `routes` | no | `{flowName: {target: [step, ..., target]}}`: the path `apply` walks when Jira has no direct transition, for example `{"support": {"Closed": ["Resolved", "Closed"]}}`. |
| `resolutions` | no | `{status: resolution}` sent with transitions that need one. Default `Resolved → Done`, `Canceled → Won't Do`. |
| `allowed_placeholders` | no | Bracketed words that are normal text in a reply (for example a role name in brackets), not unfilled placeholders. |
| `linked_issue` | no | Turns on the page's **Create linked issue** button. `{project, types, link_type, answers}`: the project new issues go to (the hub's task tracker project), the issue types offered (default `["Task"]`), the Jira link type (default `Relates`), and fixed answers for the task-workflow skills, for example `{"Bug Source": "Client"}`. Creation itself goes through `task-workflow:task-description` and `task-workflow:task-ticket`, so the hub's `tasks.*` config must be set. |
| `team_users` | no | Jira usernames always counted as the team. Otherwise a comment is the customer's when its author is the reporter or a request participant. |

The page is styled from the hub's compiled brand (`<design.build>/brand.css`, default `brand/brand.css`)
and carries the hub's logo from `design.logo` (`{light, dark}` or one path). Neither is required.

## Example

```json
"support_desk": {
  "jira_url": "https://jira.example.com",
  "project": "SUP",
  "artifact_url": "https://claude.ai/artifact/…",
  "triage_skill": "support",
  "reply_language": "en",
  "apps": [["general", "General"], ["web", "Web app"]],
  "tags": ["bug", "feature", "billing"],
  "type_flow": {"Support": "support"},
  "default_flow": "dev",
  "flow": {
    "dev": {"Waiting for support": ["Ready for Develop", "Waiting for customer"],
            "Waiting for customer": ["Waiting for support", "Closed"]},
    "support": {"Waiting for support": ["In Progress", "Resolved", "Canceled"], "Resolved": ["Closed"]}
  },
  "routes": {"support": {"Closed": ["Resolved", "Closed"]}},
  "linked_issue": {"project": "DEV", "types": ["Task", "Bug"], "link_type": "Relates",
                   "answers": {"Bug Source": "Client"}},
  "rules": ["Never promise a date the owner has not given."]
}
```

## Who can do what

| Person | Needs |
|---|---|
| Reviews and approves on the page | View access plus permission to use the page (anyone it is shared with who can interact). |
| Runs `update` or `apply` | Edit access to the page, the hub open in Claude Code, the plugin enabled, and their own Jira token. Comments and moves appear under their Jira account. |
