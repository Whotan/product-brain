---
name: "release-notes"
description: "Use when the user mentions release notes, a changelog, what went out in a release, announcing or communicating a release to clients or customers, a client update or customer-facing update, an internal or engineering release summary, what to tell clients about a new version, a PDF of a release announcement, or opening the merge/pull request that ships a release branch to production — and when a release tag has just been cut or is about to be."
argument-hint: "[tag] [--from <tag>] (default: the latest release tag on releases.primary_repo, against the release before it)"
compatibility: "Requires a Product Brain hub (brain.config.json with `repos`, `releases` and `design` keys) with the app repos cloned, and the brand-system skill installed alongside this one. git, Python 3.9+, and Chrome or Edge (driven through a clone's playwright-core) for the PDF. Windows/Git Bash safe."
metadata:
  author: "product-brain"
user-invocable: true
---

# Release Notes

`${CLAUDE_SKILL_DIR}` is this skill's base directory (shown when the skill loads);
substitute it if your shell does not expand it.

Produce **two** notes for one release, from one set of git facts. Every product
fact comes from the hub's `brain.config.json` — which repos, what a release tag
looks like, which language the client reads, where the design system lives. Each
release gets its own folder under `releases.out`, named `<version> - <release date>`:

```
<releases.out>/<version> - <date>/
    facts.json     derived from git by the gatherer — never hand-edited
    figures.json   the screenshot spec — which screen, which state, which stub
    figures/       the captures themselves, one PNG per figure, in the client locale
    client.html    client locale only, publishable, self-contained
    client.pdf     rendered from client.html — one continuous page, same design
    internal.md    internal locale only, team only
```

A release that changed no screen has no `figures.json`, and the verifier's
"no screenshots" warning is the answer rather than a gap. A release that **did**
change a screen may skip the capture only when `releases.capture` is not
configured or the app cannot be served — and the internal note must say which.
The "no screenshots" warning is then expected; in every other case, capture.

| | Client note | Internal note |
|---|---|---|
| Language | **`releases.client_note.locale` only** | `releases.internal_note.locale` only |
| Contains | what a person can now do, why it helps, and a picture of it | changes, risks, test coverage, build, citations |
| Publishable | yes — Artifact + PDF for clients | **no** — never sent outside the team |

**The client note is one language.** There is no second half. The verifier
fails any `<article data-lang>` that is not the client locale, so a translation
cannot quietly reappear and then drift out of step — which is what a second half
always does. If the client locale is RTL, read *When the client locale is RTL*
in `references/writing-the-client-note.md` before writing a word.

**The client note is not a bullet list.** Each new feature is a card carrying two
or three sentences on what changes for the person, a concrete scenario where one
exists, where to find it, and — if it changed a screen — a real screenshot of
that screen. A one-line item lets a client read the whole page without learning
whether any of it affected them. The verifier **fails** a feature card with no
benefit paragraph.

**The PDF is the same document as the page.** Not a paper redesign of it: same
width, same two-column cards, same background (the brand's wash), one continuous page. See
*The PDF* below — getting this wrong is silent.

**The note wears the product's design system, and nothing else.** See
*Design system* below.

**They are not two views of one document.** The client note is the smaller, but
it is not the internal note with words removed — an item with no user-visible
effect appears in the internal note and *nowhere* in the client note.

> Folder names sort alphabetically, which puts a `…9 - …` folder after a
> `…16 - …` one. Sort by the date half when order matters.

**Notes already sent to clients are not retrofitted.** An older note written to an
earlier contract — one-line items, the skill's own old stylesheet, no BRAND block —
fails today's verifier. It is the record of what a client actually received;
leave it. Only verify the release you are working on.

## Config

| Key | Used for |
|---|---|
| `hub.name` | wordmark and footer; `releases.client_note.product_name` overrides it in the client locale |
| `repos`, `workspace.repos_dir` | which clones are read: `repos[].path` if set, else `<workspace.repos_dir>/<id>`, else `repos/<id>` |
| `releases.tag_regex` | a matching tag **is** a production release; other tags are ignored |
| `releases.version_regex` | optional, one capture group: the version label artifacts show (default: group 1 of `tag_regex` if it has one, else the tag) |
| `releases.specs_dir` / `roadmap.specs_dir` | where spec folders live, for citations and their claimed ticks |
| `releases.primary_repo` | whose latest release tag names the release by default |
| `releases.production_branch` | where release tags are cut from; the gatherer flags a tag that is not on it; also the base branch `open-release-mr.py` opens its merge/pull request against |
| `releases.release_branch_regex` | optional, default `^(release\|hotfix)[-/._]`; which branch `open-release-mr.py` treats as "a release branch" when picking the latest one |
| `releases.merge_style` | `squash` means "is X in the release" ancestry negatives lie — see *Accuracy rules* |
| `releases.out` | where release folders live |
| `releases.client_note` | `locale`, `dir` (`ltr`/`rtl`), `calendar` (`gregorian` default, `jalali`), `i18n` / `i18n_source` (`[{repo, path}]` string files) |
| `releases.internal_note.locale` | the internal note's language |
| `releases.tests` | `{repo: command}` — the suites the internal note must report |
| `releases.capture` | `repo`, and `apps.<app>` = `{serve, base_url, base_path?}` for screenshots |
| `design.build`, `design.logo`, `design.source` | the compiled brand, and the logo read at `design.source.ref` |

A missing key is an error that names the key and an example value. Nothing falls
back to another product's defaults.

## Workflow

### 1. Gather the facts

```bash
python "${CLAUDE_SKILL_DIR}/scripts/gather-release-facts.py" --to <tag>
```

Creates the release folder, writes `facts.json` into it, and prints the headline
numbers. `--from` spans several tags; `--no-fetch` skips the network; with no
`--to` it takes the latest release tag on `releases.primary_repo`. For "what is
merged and waiting", `--from origin/<production> --to origin/<integration>
--label <next> --date YYYY-MM-DD` — the notes are then written in the future tense.

Read what it prints before writing a word. It calls out the things that change
what the notes must say:

- **`repos with changes`** — a tag pointing at its predecessor's commit shipped
  nothing. Never write content for a repo that only re-tagged.
- **`REVERTS in range`** — a reverted change is **not live**, even with its `feat`
  commit on the production branch. It gets no client line and a Risks row.
- **`migrations`** — rollback is no longer free. Required Risks row.
- **`NOT ON <production branch>`** — the tag was cut somewhere else; find out how
  it was built before calling it released.
- **`i18n strings changed`** — this is the client note's vocabulary, read from
  the client-locale files at the tag. A key with no client-locale value is an
  i18n gap: a finding for the internal note. See step 5.
- **`specs cited`** / **`WEAK spec refs`** — a spec id is cited only when a folder
  with that id exists under the specs dir, with its evidence: `slug` (an
  `NNN-slug` subject matching the folder), `branch` (a merge subject), `path` (a
  changed `specs/NNN-…/` file). A bare `#NNN` is usually an issue number, so it
  is listed as WEAK — confirm it before citing it.
- **`fetched: false`** — `git fetch --tags` failed; the facts describe the local
  clone as it stands and a newer tag may be missing.

The release date is the tag's own: the tagger date of an annotated tag, else the
tagged commit's committer date — never parsed out of the tag's name. The folder is
`<version label> - <date>`. In `files`, `count` / `added` / `deleted` count FILES
and `linesAdded` / `linesDeleted` count lines. A ref given on the command line or
in config that starts with `-`, or a `releases.production_branch` that does not
exist, stops the gatherer with exit 2.

Release **tags** are the boundary: a matching tag is what builds production. A
merge to the production branch makes code reachable, not shipped.

### 2. Scaffold both notes

```bash
python "${CLAUDE_SKILL_DIR}/scripts/scaffold-note.py" --tag <tag>
```

Drops `client.html` and `internal.md` into the folder with the dates filled (the
client calendar and digits for the client note, Gregorian for the internal one),
the locale and direction set, the version label (see `releases.version_regex`)
in place of the raw tag, the product logo embedded, the page chrome in the client
locale and marked `data-chrome`, the internal note's citation links computed
relative to the folder, and the BRAND block filled by `brand.py inline`. A locale the
scaffold has no chrome strings for gets `REPLACE-LABEL-*` slots to translate.
`--folder <path>` scaffolds a folder anywhere (a scratch copy). With `--tag`, more
than one matching folder (a release gathered twice under two dates) is an error
that lists them — pass `--folder` with the one you mean. When the version label is
a raw tag carrying a prefix (`release-2026.09.1`), the scaffold prints a hint to
set `releases.version_regex`.

It **will not overwrite a note you have already written** — a file with no
`REPLACE` slots left is treated as authored. `--force-client` / `--force-internal`
re-scaffold one file; discarding a finished note additionally needs
`--overwrite-filled`.

### 3. Write the internal note first

Writing it first is what makes the client note honest — you cannot decide which
changes are user-visible until you have listed them all.

Its five sections are **required slots**. A section with nothing in it gets an
explicit finding, not silence:

| Section | The slot | What "nothing to report" looks like |
|---|---|---|
| Technical changes | one row per change, `Evidence` = SHA or `path:line` | n/a — an empty release has no note |
| Risks | trigger, blast radius, rollback | `None found` **plus the check that produced it** |
| Test coverage | the command you ran and its output | name the suites, and say which changes shipped untested |
| Build and release | how this became production, and who confirmed it | "not yet confirmed in production" is a legitimate answer |
| Document citations | link per claim | `No spec covers this release` is a finding worth writing |

Two rules carry most of the value:

- **A test file in the diff proves a test was written, not that it passes.** Run
  each suite in `releases.tests` and paste what it says, including known baseline
  failures. If you did not run it, the Result column says `not run`.
- **State which changes shipped with no test.** Nobody volunteers this later,
  and it is the line the next person actually needs.

### 4. Capture the screenshots

Do this before writing the client copy, not after: looking at the screen tells
you what to call the controls, and it is the cheapest way to find out that a
feature does not look the way the commits implied.

Write `figures.json` in the release folder — one entry per picture, naming the
app (a key of `releases.capture.apps`), the route, the state, and the stubs that
produce it — then serve the app and capture:

```bash
python "${CLAUDE_SKILL_DIR}/scripts/capture-figures.py" "<releases.out>/<version> - <date>" --serve
```

The script's own docstring carries the full `figures.json` schema. It writes
`figures/<id>--<locale>.png`, then rewrites every
`<img data-figure="id" data-locale="<locale>">` in `client.html` to carry the
bytes as a `data:` URI. Figures default to the client locale; a capture in any
other locale is a verifier failure. `--serve` runs `releases.capture.apps.<app>.serve`
**through a shell** (treat that config value as code) in its own process group, and
kills the whole tree after — a dev server outliving its shell would otherwise hold
the port for the next run. It refuses to start (exit 2) when something already
answers on the app's URL, because the capture would screenshot that server
instead, and stops waiting the moment the serve command exits; `--only id` re-takes one picture while you tune its clip;
`--base-url` points at an already running server or a deployed environment; and
`--inline-only` skips the browser altogether to re-fill the `src` slots from the
PNGs already on disk, which is what you want after re-authoring the copy.

Four things decide whether the pictures are usable:

- **Stub the data, do not chase a live backend.** Each figure declares its own
  `mocks`, fulfilled at the HTTP boundary, so a capture is reproducible and needs
  no database, no containers and no seeded account. An auth-gated screen
  additionally needs a `seed` — whatever the app's route guard reads, written to
  storage before boot. A guard that only checks a stored user record parses and
  carries an allowed role is satisfied by a synthetic session. Read the guard
  first; a capture that bounced to sign-in is reported by its landing path.
- **Clip to the component, not the page.** A full-page capture drags in the
  sidebar, the header, and every error toast raised by the calls you did not
  stub. A component selector as `clip` with a little `padding` is the difference
  between a figure and a screenshot of a broken page.
- **Choose the state deliberately, and say why in `note`.** Four identical rows
  of default toggles teach nobody anything; a lived-in state does. And a state
  that shows a defect does not get published — pick another state and record the
  defect in the internal note.
- **Look at every PNG.** They are files in the release folder for exactly this
  reason. A screenshot of the wrong state is worse than no screenshot: it is a
  promise the product does not keep.

The browser scripts prefer the Python `playwright` package when it is importable
(`pip install playwright`), then a Node `playwright-core` found on `NODE_PATH` or in
a configured clone; `render-client-pdf.py` falls back to the Chrome command line
last. If Playwright's browser download is blocked on your network, the pinned
build is missing and the run fails with `Executable doesn't exist`. Point it at a
browser that is already on disk — every renderer, the command-line fallback
included, honours both:

```bash
export UX_EXECUTABLE_PATH="<path to a chrome or chrome-headless-shell executable>"
# or: export UX_BROWSER_CHANNEL=msedge     (or chrome)
```

Then record each figure's state in the internal note. A picture is a claim about
the product, and it needs the same evidence trail as a sentence.

### 5. Write the client note

**REQUIRED READING:** `references/writing-the-client-note.md` before writing a
word. Every product noun comes from the app's own **client-locale** i18n value
(`facts.repos[].i18n[].client`), never from the source-language value and never
from the commit subject.

For each change in the internal note, ask: *can a person using the product tell
the difference?* If no, it does not appear here. If yes, it becomes one card:

```html
<article class="feature has-shot" data-id="notification-settings">
  <div>
    <p class="who">{who it is for}</p>
    <b>{the thing, named as the UI names it}</b>
    <p class="benefit">{two or three sentences — what they can now do, and what it saves them}</p>
    <p class="scenario"><span class="label">{"For example", in the locale}</span> {one concrete situation}</p>
    <ul class="where"><li>{where to find it}</li></ul>
  </div>
  <figure class="shot" data-shot="notification-settings">…</figure>
</article>
```

An improvement that is genuinely one line of news stays one line — those go in
the `fixed` block as `.minor` cards, three across:

```html
<div class="minor" data-id="meeting-links">
  <b>{the thing}</b>
  <span>{what stopped going wrong}</span>
</div>
```

A release with no new feature drops the `new` section entirely.

Rules the verifier enforces on this structure:

| Rule | Why |
|---|---|
| exactly one `<article>` with `data-lang`, `lang` = the client locale and `dir` = `releases.client_note.dir` | one language; a second half drifts |
| `<meta charset="utf-8">` at the top | opened from disk, Chrome otherwise guesses windows-1252 and prints mojibake |
| jargon checks skip `[data-chrome]` | the scaffold's own labels ("Version", the stamp, the footer) are not the author's copy — never put copy inside a `data-chrome` element |
| `data-id` unique per card | it is what the verifier and the figures key off |
| every `new` card has a `.benefit` of ≥12 words | a named feature that explains nothing is the failure this layout replaced |
| `<meta name="release-headline" content="…">` present, one sentence, not the h1 | other skills (the roadmap) read what a person can now do from it |
| every `<img src>` is a `data:` URI | the Artifact's CSP blocks external hosts, and a relative path dies in the published page |
| every `<img>` has non-empty `alt` | the picture carries meaning; so must the words |
| `data-locale` = the client locale | a capture in another language shows the client a screen they will never see |

Three details of the layout worth knowing before you fight it:

- A card with a picture spans the full width; a card without one takes half, and
  the grid is `dense`, so pairing the figure-less cards next to each other keeps
  the last row from ending in an empty half.
- A figure-less card with no partner — the only card, or the last of an odd
  number — spans the full row rather than sitting beside an empty half.
- A **portrait** capture — a whole phone-width screen rather than a cropped
  panel — needs `class="feature has-shot tall-shot"`, which narrows its column.
  Without it the picture towers over its own copy.
- Nothing is `left` or `right`: the stylesheet is written in logical properties
  (`padding-inline`, `border-inline-start`, `text-align: start`), so an RTL
  layout falls out of one rule set rather than a mirrored copy of it.

**Write from the client-locale screen.** Two languages in one product are often
authored separately, so the same key can carry different ideas — "Load again" in
one file and *try again* in the other. Take every noun from the client value in
`facts.json`. The reference has the full method and a worked RTL example.

### 6. Render the PDF

```bash
python "${CLAUDE_SKILL_DIR}/scripts/render-client-pdf.py" "<folder>/client.html"
python "${CLAUDE_SKILL_DIR}/scripts/compare-pdf-to-html.py" "<folder>/client.html"
```

Headless Chrome, because real glyph joining, shaping and bidi are required for
many scripts — a generic PDF writer emits disconnected or reversed text and
reports success.

**Driven through Playwright, not `chrome --print-to-pdf`.** The command line has
no paper-size flag and no way to ask for `preferCSSPageSize`, so it prints A4
whatever the stylesheet says — and A4 is the whole problem, see *The PDF* below.
The renderer reads the width from the CSS `@page`, measures the content height,
and prints one continuous page. `--paginate` gives fixed sheets instead.

It reports the page geometry, the page count and the embedded fonts, checks the
fonts with brand-system's `brand.py pdf-fonts` against the design system's
`allowed_families`, and when anything else landed it **names the character**
that pulled it in — and exits 1. Treat that as a failure; see *Fonts* below.

`compare-pdf-to-html.py` then renders both and measures the difference. A few
percent is antialiasing; tens of percent is a layout that reflowed or a
background that dropped out, and `diff.png` shows where. Look at `diff.png`:
glyph edges only is a pass. Its PNGs land in `<folder>/compare/` (or `--out-dir`);
that folder is scratch — delete it, and never commit it.

### 7. Verify — before sending anything

```bash
python "${CLAUDE_SKILL_DIR}/scripts/verify-release-notes.py" "<folder>/client.html" "<folder>/internal.md"
```

The two notes are checked for opposite failures. The client note for:

- **leaking** — jargon (English always, plus the client locale's list), SHAs, spec
  ids; in an RTL note, an unwrapped version string or a `·` next to a `<bdi>`
- **being thin** — a feature card with no benefit paragraph, or one under twelve
  words
- **pictures that will not travel** — a src that is not a `data:` URI, a missing
  `alt`, a capture in another locale
- **a second language creeping back** — any `<article data-lang>` that is not the
  client locale, or two in it
- **a PDF that will not match the page** — a paper `@page` size, a missing
  `print-color-adjust: exact`, no `break-inside: avoid`, a `max-width` query not
  scoped to `screen`, a dark token the print block does not reset at matching
  specificity, a missing `<meta charset>`
- **straying from the design system** — brand-system's `check-brand.py` runs on
  the file; a missing or stale BRAND block, a colour literal, a `font-family` that
  is not `var(--ds-font-*)` or a weight that is not embedded fails verify

The internal note for **omitting** — and it reads only lines the author wrote.
Each line is classified against the internal template first: the template's own
prose carries backticks, paths and example links, so a scaffold with every slot
set to "none" would otherwise satisfy every check. It fails a note with no
author-written technical-change row, no author-written risk (or a "none" with no
check named), no test-coverage row whose Result is real (`not run` / `n/a` counts
only with a reason beside it; `none` never does), no line naming the changes that
shipped untested, no author-written build line, no author-written citation link,
or text in the client locale's script. It warns when `figures.json` exists and the
note never says what state the captures are in — and when there is no
`figures.json` and the note never says why.

Word caps, all warnings except the floor: `.benefit` ≥12 words (a **failure**
below it) and ≤85, `.scenario` ≤70, `.lede` ≤55, `figcaption` ≤36, a `.where` line
≤34, the `.glance` row ≤34 and **each glance chip ≤9**, **`.who` ≤8**, a `.minor`
≤44, the stamp ≤14, `h1` and a card's `<b>` ≤16, any other paragraph ≤44, the
release-headline ≤30. The scaffold's own `[data-chrome]` wording is exempt from
the jargon lists; a commit hash is 7–40 hex characters with at least one digit
and one letter (an all-digit run is a date or a phone number unless the copy
calls it a commit), and nothing inside `<bdi>` is checked for one.

`--locale` / `--dir` override the config (the fixture below uses them). Take every
count you report from this output. Zero failures is the bar for sending.

Then open the PDF itself. Letters must join, text must run in the note's
direction, the cards must still be two-up, and the background must be the brand's
wash (which may be flat) rather than bare white.

**If you change the verifier, re-run it against both fixtures first:**

```bash
python "${CLAUDE_SKILL_DIR}/scripts/verify-release-notes.py" --locale fa --dir rtl "${CLAUDE_SKILL_DIR}/fixtures/leaky-client-note.html"
python "${CLAUDE_SKILL_DIR}/scripts/verify-release-notes.py" "${CLAUDE_SKILL_DIR}/fixtures/hollow-internal-note.md"
```

`fixtures/hollow-internal-note.md` is the internal template as the scaffold
writes it with every slot set to "none". It must fail six ways; a pass means the
checks are reading the template instead of the author — which is exactly how it
once passed "All contracts satisfied".

`fixtures/leaky-client-note.html` is an RTL note that fails in every documented
way at once, brand checks included. A pass means the verifier broke — which has
happened: a case-insensitive placeholder regex once matched the ordinary word
"replace"; a check once matched the comment that explained it rather than the
rule; a check once matched a selector anywhere in the print block, so an
unrelated rule made it pass; and a patch that silently wrote control characters
into a pattern turned a check into a no-op that still reported success.

### 8. Publish and report

- Commit the whole release folder — `facts.json`, `figures.json` and `figures/`
  included — **except `compare/`**, which is scratch output. The figure PNGs are
  the evidence behind the pictures in the published page, and they are small
  enough to keep.
- Publish **only** the client note as an Artifact. If one already exists for this
  tag, republish to the **same URL** with a dated `label`.
- The internal note stays in the repo. It names untested changes and unconfirmed
  deploys — correct for the team, wrong to hand a client.
- Report: the verifier tallies, which repos shipped, every risk flagged, and any
  spec whose shipped verdict this release changes. Shipped verdicts belong to the
  `delivery-roadmap` skill (plugin form `product-brain:delivery-roadmap`); if one
  moved, re-cut the roadmap with it.

### 9. Open the release merge/pull request (optional)

A separate, English-only, bullet-point document from the two notes above — the
kind git hosts show on the MR/PR itself, not something a client ever sees. It
does not require `facts.json` or a cut tag: it reads
`git log <production>..<release branch>` directly, so it is usable before step 1
as the thing that actually ships the release branch into
`releases.production_branch`.

```bash
python "${CLAUDE_SKILL_DIR}/scripts/open-release-mr.py"              plan only — prints it, opens nothing
python "${CLAUDE_SKILL_DIR}/scripts/open-release-mr.py" --create      opens it for real
```

It finds **the latest release branch** — the remote branch matching
`releases.release_branch_regex` whose tip was committed most recently — and
groups its commits by Conventional Commits type into `## Added` (`feat`),
`## Changed` (`perf`/`refactor`/`build`/`ci`/`chore`/`style`/`docs`/`test`) and
`## Fixed` (`fix`); a subject with no conventional prefix goes under
`## Other changes` rather than being guessed into one of the three. A commit
later reverted inside the same range, and the revert commit itself, are both
dropped — same *Accuracy rules* as the notes above: a reverted change never
shipped. `--repo <id>` targets a repo other than `releases.primary_repo`;
`--branch <name>` skips picking "the latest" one.

**Opening an MR/PR is visible to the whole team and not something to silently
automate.** Without `--create` the script only prints the plan — repo, base,
head, title, and the full bullet body — so you can read it over (and let the
user look, if one is present) before anything is opened. `--create` then calls
`gh pr create` or `glab mr create`, auto-detected from the clone's `origin`
remote (`--host github|gitlab` overrides when the URL doesn't say); either CLI
must already be authenticated (`gh auth status` / `glab auth status`).

## Design system

The client note is often the only document a paying customer reads without
anyone from the team in the room, so it carries the product's own identity — and
only that. **It styles itself exclusively through the BRAND block.**

- `brand/brand.css` (under `design.build`) is compiled from the hub's `DESIGN.md`
  by the **`brand-system`** skill (`product-brain:brand-system`): embedded faces,
  `--ds-*` role tokens for light and dark, a print reset. `scaffold-note.py`
  inlines it between `/* BRAND:BEGIN */` and `/* BRAND:END */` by calling
  `"${CLAUDE_SKILL_DIR}/../brand-system/scripts/brand.py" inline`. Never edit that
  block by hand.
- Every colour, font-family and radius in the template's own CSS is a
  `var(--ds-*)` role or a `color-mix(in oklab, var(--ds-x) N%, var(--ds-y))` of
  two of them. No colour literal, no named face, no weight the brand does not
  embed. `check-brand.py` is part of verify and fails any of them.
- **Effects are the brand's.** The background is `var(--ds-wash)` and cards use
  `var(--ds-shadow-sm|md)`; the template draws no gradient and no shadow of its
  own. A brand that forbids them leaves those roles at their defaults (the canvas
  colour, `none`) and the note comes out flat — correctly. Weights are
  `var(--ds-weight-regular|strong|bold)`, mapped by the brand to what it embeds
  or declares; Latin runs use `var(--ds-font-latin)`.
- The masthead shows the product's logo from `design.logo`, read at
  `design.source.ref` and embedded as a `data:` URI — never a redrawn
  approximation of it. With no logo configured, the product name is set as a
  wordmark. On the dark theme the logo sits on a light tile.
- When the design system changes: rebuild with brand-system, then refresh the
  block in the note you are working on with `brand.py inline <client.html>` (or
  re-scaffold with `--force-client --overwrite-filled` and re-fill). **Notes
  already sent are not retrofitted.**

The layout is a 62rem column of cards on the brand's wash (which may be flat): a masthead carrying the
logo, the version and a row of at-a-glance chips; full-width cards for anything
with a screenshot, half-width cards for anything without; and a three-across grid
for the one-line improvements.

### Fonts — four traps, all of which fail silently

Every one of these renders perfectly on screen and degrades only in the PDF, so
none of them announces itself. The renderer's font report is the detector.
brand-system does the build; these are why it builds the way it does.

1. **Linked webfonts are not an option for the PDF.** Headless Chrome does not
   fetch a font stylesheet when printing, so a linked face falls back to a system
   font. The brand embeds every face as base64.
2. **Chrome will not embed a CFF-flavoured webfont in a PDF.** A face shipped with
   CFF outlines must be converted to TrueType (glyf) outlines at build time —
   brand-system does this when fonttools is present.
3. **Chrome only activates a face that laid-out content uses, and decides
   mid-paint.** A face used by one short run — a Latin version string, a dash the
   primary face lacks — can miss that window and fall back in the PDF while
   looking perfect on screen. The page's script calls `load()` on every declared
   face up front and the renderer waits on `document.fonts.ready`; do not remove
   either.
4. **The embedded faces are subsets, and a rare character falls out of all of
   them.** One arrow in a "where to find it" line once put a system face in a
   whole PDF while the screen looked perfect. The renderer names the character;
   fix the copy (a word instead of an arrow) or widen the subset in the
   brand-system build and re-inline. Naming it requires `fonttools`; without it
   the report says so rather than passing.

Only the weights in `tokens.json` `embedded_weights` exist. Asking for any other
falls out of the family to a system font, and `check-brand.py` fails it.

## The PDF

The PDF and the HTML are **one design**, and the print block's whole job is to
stop them diverging. This is not a preference; it is a bug class. An early
version of this note had a proper paper design — white stock, reflowed single
column, small type — and nobody noticed until the two were opened side by side,
because each looked finished on its own.

Three mechanisms, and each one silently un-matches the pair if it is missing:

| Mechanism | Without it |
|---|---|
| `@page { size: 1120px 1584px }` — a page as wide as the layout | A4 portrait gives ~688px of printable width, which trips the narrow-viewport rule and collapses every two-column card |
| `print-color-adjust: exact` | Chrome drops the wash, the card surfaces and every tinted panel, and prints on bare white |
| `@media screen and (max-width: ...)` — the media type, not just the query | an unqualified width query also matches the printed page, so the PDF reflows to the phone layout |

Further details, all learned by getting them wrong:

- **Paper is light, at matching specificity.** Every dark token must be reset in
  `@media print` by a rule whose selector matches the dark rule's —
  `:root:not([data-theme="light"])` needs exactly that selector; a bare `:root`
  or `:root[data-theme]` loses or does not match, and a reader printing from a
  dark-mode browser gets pale ink on white. The BRAND block owns the reset for
  `--ds-*`; the template resets its own tokens and drops a dark `data-theme` for
  the duration of a browser print. The renderer additionally pins the light theme.
- **The CSS page box and the PDF sheet must agree.** Passing width/height to
  `page.pdf()` sizes the *sheet*, but Chrome still breaks the document at the
  height in the stylesheet's `@page` rule. Give it a 2864px sheet while the CSS
  says 1584px and you get three pages, each with the content crammed into its top
  55% and the rest blank. The renderer injects a matching `@page` rule and prints
  with `preferCSSPageSize`, which is what keeps the two in step.
- **One continuous page, by default.** Cutting the note into sheets cannot be
  done without gaps — cards must not be sliced, so every break leaves whatever
  space the next card could not fit into (440px and 700px at page feet, measured,
  against an HTML page with no gaps anywhere). So the renderer measures the
  content — with a short viewport, since a document is never measured shorter
  than its viewport — and makes the page that tall. Text stays selectable; a
  viewer scales it to paper like any oversized page.
- **But a continuous page has a ceiling: ~8,192 CSS px.** Past it the PDF opens
  BLANK, and nothing else in this skill notices — the file is valid, the fonts
  embed, the verifier passes, `compare-pdf-to-html.py` passes. Viewers built on
  pdf.js (browser previews, editor PDF extensions) draw a page into one canvas,
  and Skia/WebKit cap a canvas side at 16,384px — which a Retina display hits at
  twice the CSS height. A long feature note measured 10,148px, needed a
  2,240×20,296 canvas, and displayed nothing; every note that displayed was under
  2,900px. **A note over ~8,000px must be rendered with `--paginate`**, and the
  gaps at a page foot are the cosmetic price of a document that renders at all.
  `render-client-pdf.py` warns when a continuous render crosses the line — but
  only a real viewer proves it, because pdfium rasterises the bad file fine.
- **No shadows in print.** A blurred `box-shadow` cannot be vector PDF; Chrome
  rasterises each into an image mask at print DPI, which once made up ~70% of a
  note's bytes for a glow the comparison could not even see.

## Accuracy rules

- **Never write a client line for a reverted change.** It is not live.
- **Never fabricate content for a repo that only re-tagged.** `reposShipping` is
  the authority.
- **Conventional-commit coverage is partial** (often well under 100% in at least
  one repo). Uncategorised subjects go in verbatim; never invent a type.
- **Sort tags with `--sort=v:refname`** — the gatherer does, and it considers only
  tags matching `releases.tag_regex`; alphabetic sort puts `…9` after `…16` and
  mis-attributes the whole release.
- **Under squash merges, ancestry lies in one direction.** "Is feature X's branch
  an ancestor of the release?" says *no* for work that shipped squashed. Check
  the squash commit on the production branch instead. (A release that was merged
  and reverted inside one tag reads as present too — check the reverts.)
- **A tag proves a build, not a deployment.** Say who confirmed the running version.
- **Never echo non-Latin text to a console you have not checked.** A cp1252
  console raises `UnicodeEncodeError`. Every script here reconfigures its own
  stdout to UTF-8; for anything else, write files as UTF-8 and read the rendered
  output rather than the terminal.
- Cross-check a shipped claim against the roadmap facts (`roadmap.facts`,
  produced by `delivery-roadmap`) rather than a spec's `Status:` header or a
  ticked task list; both are demonstrably wrong about what shipped. The
  verification recipes live in
  `"${CLAUDE_SKILL_DIR}/../delivery-roadmap/references/git-verification-recipes.md"`.

## Common mistakes

| Mistake | What it looks like | Fix |
|---|---|---|
| Client note is the internal note, softened | "We optimised the reports query" | Ask what the *person* sees: "Your report history loads faster" |
| Client copy written by translating the source language | Words that appear on no screen of the product | Take nouns from the client-locale i18n values via `facts.json` |
| Invisible work padded into the client note | "Moved test helpers into classes" | Cut it. Internal note only. |
| Empty Risks section | Section header, nothing under it | `None found` + the check that produced it |
| Coverage claimed from the diff | "Tests added" with no command | Run the suite; paste the result, or write `not run` |
| Version number scrambled in RTL copy | A digit torn off the date and parked by the version | `<bdi dir="ltr">` **and** an em dash separator, never `·` |
| PDF is mojibake | `Ø±Ù` everywhere, screen fine over a server | `<meta charset="utf-8">` first in the file |
| PDF prints pale on white | Reader's browser is in dark mode | The print reset must match the dark rule's specificity |
| PDF looks like a different document | One white column of small type, no wash | The PDF is the screen — see *The PDF*. Run `compare-pdf-to-html.py` |
| PDF has near-empty pages, or a blank band at the foot | Big gaps at a page foot | Cards cannot be sliced; render one continuous page measured on a short viewport |
| PDF opens blank in the viewer | Valid file, verifier passes, nothing on screen | The continuous page is over ~8,000px — re-render with `--paginate` |
| A second language reappears | A second `<article data-lang="…">` | The note is one language; the verifier fails it |
| PDF in the wrong typeface | Screen looks right, PDF does not | Read the renderer's font report — see *Fonts* |
| Off-brand colour or face | A hex in the template, a named font | `var(--ds-*)` only; `check-brand.py` fails it |
| A redrawn logo | An SVG "inspired by" the product mark | `design.logo`, embedded — or the product name as a wordmark |
| A feature card that only names the feature | "**Channel X** — Channel X is now supported." | Two or three sentences on what it changes for the person; the verifier fails it otherwise |
| A screenshot of a broken page | Error toasts and an error panel around the feature | Clip to the component and stub the calls that screen actually makes |
| A screenshot that publishes a defect | A localised screen showing an unlocalised month name | Pick a different state, and put the defect in the internal note |
| An invented screenshot | A hand-drawn panel that looks like the product | Capture the running app, or show no picture at all |
| A relative image path | Renders locally, broken in the Artifact | `capture-figures.py` inlines the bytes; never hand-write a `src` |
