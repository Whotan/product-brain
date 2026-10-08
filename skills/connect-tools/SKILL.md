---
name: connect-tools
description: Connect a Product Brain hub to the team's tools — GitLab or GitHub, Jira, SonarQube — through project MCP servers, with personal tokens only as a fallback. Checks what is already signed in without ever reading or printing a token. Use when the user says "set up my connections", "connect my tools", "connect Jira/GitLab", or when `/mcp` shows a server as failed, in a Product Brain hub.
---

# connect-tools

Wire the hub to the team's tools so Claude can read MRs, pipelines and tickets. Everything shared
goes in committed files with **no secrets**; tokens go only in the git-ignored
`.claude/settings.local.json`, and only when a normal sign-in isn't possible.

**Never read, print, echo or copy a token value.** Check presence only (`[ -n "$VAR" ]`, `glab
auth status`). Never ask the user to paste a token into the chat — tell them which placeholder to
fill in the file themselves.

## Facts this design rests on

- MCP servers can only be defined in `.mcp.json` (project) or the user's `~/.claude.json` — not in
  settings files.
- `${VAR}` expansion inside `.mcp.json` does **not** see `env` from `.claude/settings.local.json`;
  it reports "Missing environment variables". So `.mcp.json` never uses `${TOKEN}` placeholders.
- Spawned MCP processes and Bash commands **do** inherit that `env`, merged with the server's own
  `env` block. That is how a token reaches a server.
- A project `.mcp.json` server **shadows** a same-named server in the user's `~/.claude.json`.
  Listing its name in `disabledMcpjsonServers` hands control back to the user's own server.
- A token env var (e.g. `GITLAB_TOKEN`) **overrides** `glab auth login`, and a stale one gives 401.
- On Windows, Application Control / Smart App Control can block the unsigned `mcp-atlassian.exe`
  that a bare `uvx mcp-atlassian` runs: `/mcp` shows Jira as failed, and running the command prints
  "An Application Control policy has blocked this file (os error 4551)". Starting it through Python
  (`uvx --from mcp-atlassian python -c "..."`, as in the template) avoids that file on every OS.

## Step 1: Find the hosts

Read `brain.config.json` repo URLs and the hub's `git remote get-url origin` to get the code host
(GitLab or GitHub, and its hostname). Ask the user whether the team uses **Jira** and, if so, its
URL. Ask for any host you cannot find — never guess or copy one from another hub.

## Step 2: Shared, committed files (no secrets)

Create or merge `.mcp.json` from the framework's `templates/hub-mcp.template.json`, keeping only
what applies and filling non-secret values in each server's `env`:

- **GitLab host** → `gitlab`: `glab mcp serve`, `env: { "GITLAB_HOST": "<host>" }`.
- **GitHub host** → no MCP server needed; Claude uses the `gh` CLI (`gh auth login`).
- **Jira** (only if the team uses it) → `jira`: the template's Python launch (`uvx --from
  mcp-atlassian python -c ...`), `env: { "JIRA_URL": "<url>" }`. If an existing `.mcp.json` still
  has `"args": ["mcp-atlassian"]`, replace just those args with the template's.

Create `.claude/settings.local.example.json` from `templates/hub-settings.local.example.json`,
keeping only the lines for servers that exist.

Make sure the hub's **tracked** `.gitignore` ignores `.claude/settings.local.json` (`pb sync` adds
it; a personal global gitignore doesn't protect teammates). Verify, ignoring global excludes:

```bash
git -c core.excludesFile=/dev/null check-ignore -v .claude/settings.local.json
```

If that prints nothing, add the line to `.gitignore` before writing any personal file.

## Step 3: This machine's connections (presence only)

Work out what this user needs, without looking at any value:

1. **GitLab** — if `env -u GITLAB_TOKEN glab auth status --hostname <host>` succeeds, the login
   works: add **no** `GITLAB_TOKEN` (and if one is set and `glab` fails with 401, tell the user a
   stale token is overriding their login). Also skip it if `GITLAB_TOKEN` is already set and
   `glab auth status` succeeds. If `glab` is missing, give the install command (README step 6).
   For GitHub: `gh auth status`; if it fails, ask the user to run `gh auth login`.
2. **Each `.mcp.json` server** — list only the *names* of the user's own servers:

   ```bash
   python3 -c "import json,os;print(list(json.load(open(os.path.expanduser('~/.claude.json'))).get('mcpServers',{})))"
   ```

   If a name matches (e.g. the user already has `jira`), add it to `disabledMcpjsonServers` and add
   no token for it. Otherwise, if its token variable isn't already set, add it with a placeholder
   (`JIRA_PERSONAL_TOKEN` for Jira Server/DC; `JIRA_USERNAME` + `JIRA_API_TOKEN` for Jira Cloud),
   and add the server to `enabledMcpjsonServers`. Check `uv` is installed for `uvx`.
   On Windows, if the user's own `jira` in `~/.claude.json` has `"args": ["mcp-atlassian"]`, offer
   to switch those args to the template's (back up the file first; change nothing else in it).
3. **SonarQube** — add `SONAR_HOST_URL` / `SONAR_TOKEN` placeholders only if the user wants issue
   details; the pipeline verdict and dashboard link need no token.

Merge into `.claude/settings.local.json`: keep every existing key and value, add only missing
placeholders, and never overwrite an existing value. Then tell the user exactly which
placeholders to fill in **in the file**, and to start a new session afterwards.

## Step 4: Verify

```bash
claude mcp list
```

Report each server as connected / failed / disabled-in-favour-of-yours. For a failure, say which
check to redo (sign-in, missing placeholder, `uv` not installed, or the Windows block above).
Don't report success for a server you couldn't verify.

## Rules

- Never read, print or copy a token value; never ask for one in the chat
- Never put a token or a `${TOKEN}` placeholder in `.mcp.json` or any committed file
- Never write `.claude/settings.local.json` unless git ignores it via the tracked `.gitignore`
- Never overwrite existing values in `.claude/settings.local.json`
- Never add a token when the normal sign-in works — it overrides the login and goes stale
- Ask for any host you cannot find in the hub; never copy another hub's values
