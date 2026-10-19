# UI/UX mockups for a task

Used by `/task-description` (rows `U1`, `U2`, …), `/task-plan` (rows `P1`, …) and `/quality-gate`
(rows `G1`, … for a visible change made during the gate). Every UI/UX change is approved by a
**team member**, never by an agent. The task's writer is asked first, and any team member may
approve. The mockup is what they approve, so it has to show the real product, not an idealised one.

The hub's conventions file (`tasks.conventions`) names the team's apps, the screen widths to
capture, how to log in and reach a screen, and its copy rules. Where it is silent, use the
defaults below.

## Where things go

```
<task folder>/mockups/
  current/U1-<app>-<screen>-<locale>-<width>.png   the screen as it is today, one per locale
  U1-<slug>.html                                   the mockup, one file per row
```

One row per screen or component. All the changes to one screen share a row and a mockup.

## 1. Capture the current screen first

Take a screenshot of each affected screen as it is today, in every locale the hub uses
(`tasks.locales`, primary first).

- **Widths**: every width at which the change shows, plus one at which it should not show (a
  mobile-only change is also captured at desktop width, to prove desktop is unchanged). Defaults:
  390 px for mobile and 1440 px for desktop.
- **States**: every state the change touches (empty, error, a filled form).
- **How**: Playwright from the app's repo (its E2E setup shows how to log in and reach a screen), or
  any browser tool you have, against the local stack or the test environment.

If a screen cannot be reached, build the "Today" side from the component's template and styles
in the code. Write `Reconstructed from source, not captured` on the mockup and in the row. Never
draw the current screen from memory.

## 2. Read the real component

Open the component and template the screen comes from: its classes, UI-library components,
spacing, icons and copy. The mockup reuses what exists. A new pattern appears only where the
change needs one, and the mockup says so.

## 3. Build the mockup

One self-contained HTML file per row, `mockups/U1-<slug>.html`:

- **Layout**: "Today" (the screenshot from `current/`) next to "Proposed", with a short note
  marking each difference.
- **Styling**: inline the hub's compiled brand (`<design.build>/brand.css`) between
  `/* BRAND:BEGIN */` and `/* BRAND:END */`, and use its `--ds-*` variables. Where the app has its
  own `DESIGN.md`, follow its component and layout rules as well. If the real screen uses a value
  the brand does not have (a UI-library colour, for example), copy the exact value from the app's
  source and allow it in the brand check with `--allow-literal <value>`. Add an HTML comment
  naming the source file. Never invent a value.
- **Language**: the primary locale first, then the others. For a right-to-left locale, mirror the
  layout; do not just flip the text direction. If the ticket gives no copy for a locale, propose
  some, mark it *proposed* on the mockup, and add it to Open questions. It is approved together
  with the mockup.
- **States**: every state the change affects: loading, empty, error, disabled, long text.
- **Data**: realistic names and dates, in the hub's calendar. Never real customer or patient data.

Run the brand check (`check-brand.py` from the `brand-system` skill of the product-brain plugin)
and fix every failure before showing the mockup.

## 4. Share it and wait

Publish the HTML with the Artifact tool, including the `current/` screenshots as supporting files.
Put the link in the row's Mockup cell next to the file link. Then ask the writer (or whichever
team member is reviewing), for each row: **approve, or what should change?**

**Approval counts only in the approving team member's own words, from a source you can link to**:
a session they are running themselves, a comment on the artifact, a ticket comment, or a chat or
email message. Record what they said:

| What happens | Row becomes |
|---|---|
| A team member explicitly approves that mockup ("U1 approved", "U1 is fine, go ahead") | `Approved by <name>, YYYY-MM-DD, <source with link>` |
| A team member asks for changes | `Changes requested, YYYY-MM-DD: <what>`. Update the same file, republish to the same URL, set the row back to `Pending`, and ask again. |
| Someone reports another person's approval: "Sara said it's fine", "the PM OK'd it on a call" | Stays `Pending`. Ask the approver to confirm in their own words, or ask the person reporting it whether they approve it themselves. |
| Silence, "ok", "continue", "let's plan", or approval of a different row | Stays `Pending`. Ask about this row by name. |

**When the writer is away**, any team member may approve the row or take over the writer role. If
they take over, update the description's Writer field with their name, the date and the source. An
agent never takes the role, and never fills it in without that person's own words.

## The approval rule

**An agent never approves a UI/UX change.** Not when the change is tiny, not when it copies an
existing pattern exactly, not when the writer is busy, and not when the plan or a release is
waiting. A row is Approved only when a team member approved that specific mockup themselves, and
the row records who, when and where.

| Thought | Reality |
|---|---|
| "It's just a label / colour / spacing change" | It is still a UI change, so a team member approves it. A small mockup takes minutes. |
| "It matches the design system, so it's already approved" | Matching the design system is required for every mockup. It is not approval. |
| "The writer said 'looks good' about the whole task" | Ask row by row. Record only what was approved. |
| "The developer says the writer agreed" | Second-hand. Ask the writer to confirm, or ask the developer whether they approve it themselves. |
| "I'll mark it approved and they can object later" | That is the agent approving. Leave it Pending. |
| "No screenshot possible, so I'll skip the mockup" | Reconstruct the screen from source and say so. A row without a mockup cannot be approved. |
