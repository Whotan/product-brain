# Product Brain — Introduction & Overview

> A shared brain for your product. One place that knows your plans, your words, and your
> decisions — connected to your apps — that anyone can ask in plain language.

---

## What it is

Product Brain is a shared, always-available knowledge layer for a product team. Think of it as a
knowledgeable teammate who has read every document and every line of code, never forgets, and is
happy to answer the same question a hundred times.

It lives in one folder (a **hub**) that holds the knowledge worth keeping — your rules, your shared
words, your decisions — and connects it to your actual apps. Then anyone on the team can ask a
question like they'd ask a colleague and get a clear answer grounded in what's really there.

---

## Why now: the end of heavy documentation

Keeping thick technical documents up to date — and reading through them to find a single answer —
used to be a real burden. It isn't anymore.

In a world with capable LLMs and indexing tools like **graphify**, you can simply **ask a question
or request an explanation** and get it, grounded in the real code and the real decisions. You no
longer have to write and maintain heavy documents just so people can find things, or dig through
pages to get unstuck.

The knowledge that *is* worth writing down stays small and human — your rules, your words, and your
"why." Everything else, you just ask.

---

## The problems it solves

1. **"What does this part even do?"** — Get a grounded answer in seconds instead of reading files
   for an hour or waiting for the one person who knows.
2. **"Why was it built this way?"** — The reasoning is written down once and findable forever, not
   trapped in someone's memory.
3. **"We all call it something different."** — A shared glossary connects "Session", `Appointment`,
   and "booking" so everyone speaks the same language.
4. **"This question touches two apps."** — One question covers the web app and the API at once.
5. **"Knowledge walks out the door."** — Context stays in the hub; new hires read one place and ask
   the rest.

---

## How it works (in plain terms)

There is one button to remember: **refresh**. Everything else is just asking questions.

1. Your apps' code and your hub's documents are gathered together.
2. A tool called **graphify** reads them and builds a **map** of how everything connects.
3. When you ask a question, Claude follows the map straight to the few relevant pieces — fast, and
   grounded in what's really there.

Refresh (`pb sync`) is quick after the first run, because graphify only re-reads what changed. You
can run it after meaningful changes or schedule it to run automatically.

It reads more than text: code, written docs (Markdown, PDF, Word, spreadsheets), images, and even
**meeting recordings** (transcribed on your own machine). So a recorded kickoff can become
searchable knowledge sitting right next to the code it affects.

---

## What a hub contains

**Required — the knowledge that can't be guessed from code:**

- **constitution.md** — your non-negotiable rules (e.g. "every user only sees their own data").
- **vocabulary.md** — your glossary tying product words to code words.

**Recommended:** **domains.md** — the big areas of your product, with owners and status. It's
"graph-assisted": after a refresh, the map already groups related things, so you mostly just tidy
up names.

**Everything else is yours:** a `docs/` folder for specs, decisions, meeting notes, research,
runbooks — or any type you invent. Write in Markdown when it's easy; drop in PDFs or recordings when
that's the natural form.

---

## Use any method you like

Product Brain prescribes *structure*, not *methodology*. Write specs as plain notes, RFCs, Shape Up
pitches, or exported docs. As long as they live under `docs/`, the hub holds and connects them.

---

## Where to go next

- **New to it?** Read **Getting Started** (`docs/getting-started.md`).
- **Want to see a finished hub?** Copy **`examples/todo-app/`** and poke around.
- **Want the full picture?** Open **`website/product-brain.html`** in a browser.
