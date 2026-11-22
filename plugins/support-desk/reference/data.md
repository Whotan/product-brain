# The page's data

## Tickets (embedded in the page, `data.json` in the work folder)

`desk.py check` validates every field below; `build` refuses a page that fails.

| Field | Meaning |
|---|---|
| `key` | Issue key. |
| `app`, `alsoApps` | The tab it belongs to, plus any other areas it touches (ids from `support_desk.apps`). |
| `pri` | `P1` (blocks work) … `P4`. |
| `cls` | Question · Bug · Feature request · Usage/config · Known · Unclear (free text is accepted for nuance). |
| `type`, `jira` | Jira issue type and current status (`refresh` keeps `jira` current). |
| `created`, `createdAt`, `updatedAt`, `lastReplyAt` | Display date (`18 Nov`) and UTC stamps `YYYY-MM-DDTHH:MM:SS`. |
| `tfa`, `ask`, `att` | Title and request text as the customer wrote them; attachment count text. |
| `ten`, `asken` | English title and gist. |
| `thread` | `[[customer\|us, date, English summary], ...]`: the conversation so far, without personal names. |
| `checks` | `[[evidence, confirmed\|refuted\|cant, finding], ...]`: what was verified, and where. |
| `truth` | One or two sentences: what is actually going on. |
| `move` | The next step for the team, in one line. |
| `reply`, `gloss`, `noreply` | The draft reply (in `reply_language`), its one-line English gloss, and whether no reply is needed yet. |
| `tags` | From `support_desk.tags`. |
| `links` | Optional. `[[key, status, summary, relation], ...]`: issues linked in Jira, as the ticket sees them (`fetch`/`link` keep it current). |
| `suggest`, `suggestWhy` | Suggested Jira status (must be reachable per `flow`) and why; `""` to stay. |

## Saved decisions (the page's database)

| Row | Fields |
|---|---|
| `replies/<KEY>` | `reply` (the edited text, if edited), `state` (`draft`, `approved`, `hold`, `noreply`, `posted`), `note` (to Claude), `claude` (Claude's answer to the note), `posted` `{at, commentId, actions}`, `by` (who saved it, an opaque id), `updatedAt`. |
| `moves/<KEY>` | `to`, `state` (`approved`, or `none` to stay), `from` (the status when approved), `by`, `updatedAt`; after apply also `appliedAt`, `appliedTo`. |
| `links/<KEY>` | `state` (`requested`, `cancelled`, `created`, `failed`), `issueType`, `brief` (the requester's words), `by`, `updatedAt`; after apply `issue` and `createdAt`, or `error`. |

No row means: the page's draft, and the suggested move preselected but not approved.

## Work files (`<hub>/.work/support-desk/current/`)

`data.json` (tickets), `fetched.json` (Jira), `changes.json` (refresh), `patch.json` (Claude's triage),
`db/` (database dump), `db-ops.json`, `db-ops-apply.json` and `db-ops-link.json` (writes for one `ArtifactData` batch; an entry
with `"if_version": "FILL"` needs the version from the dump's listing), `plan.json`, `log.json`,
`page.html`. Keep `.work/` out of git: these files hold customer text.
