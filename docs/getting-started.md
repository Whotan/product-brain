# Getting Started with Product Brain

> For everyone — no technical background needed. If you can chat with Claude, you can do this.

---

## The big idea: you can ask Claude to do the commands

You do **not** need to know git, Python, or how to install anything. Whenever a step shows a
command, you can simply **ask Claude to do it** — for example, "install the tools for Product Brain"
or "refresh the brain" — and Claude runs it and tells you what happened in plain words.

The **only** step that might need a technical teammate, once, is creating the hub on a host like
GitHub and signing in the first time. After setup, there are **no commands at all** — you just ask
questions.

---

## Who does what

| Step | You can ask Claude | May need a teammate once |
|---|---|---|
| Install the tools | ✅ | — |
| Add the setup wizard (brainify) | ✅ | — |
| Create the hub folder | ✅ (local) | If it should live on GitHub/GitLab |
| Write your rules, words, decisions | ✅ (Claude interviews you) | — |
| Refresh (build the map) | ✅ | — |
| Ask questions, forever | ✅ | — |

---

## Step by step

### 1. Install the tools
Ask Claude: **"Install the Product Brain tools."** It installs graphify (the map builder). If
Python isn't on the machine, Claude will tell you in one sentence what to install, or that a
teammate can — and continue with everything else.

### 2. Add the setup wizard
The wizard is a Claude skill called **brainify**. Add it once:
- **Cowork:** Settings → Capabilities → add the `brainify` skill.
- **Claude Code:** copy the `skills/brainify/` folder into your project's skills directory.
- **Check:** type "set up product brain" — if Claude starts a checklist, it's working.

### 3. Create the hub
Ask Claude: **"Create a Product Brain hub for our team."** It makes the folder and sets it up. If
you want it shared on GitHub, a technical teammate can connect it once.

### 4. Run the wizard
Say: **"Set up product brain."** Claude asks you simple questions, one at a time — your rules, your
key words, your product's main areas — and writes the files for you. You review and tweak; nothing
is final until you say so.

### 5. Refresh
Ask Claude: **"Refresh the brain."** It pulls your apps and builds the map. The first time takes a
minute or two; after that it's quick, because it only re-reads what changed.

### 6. Ask anything
That's it. From now on, you and your teammates just ask questions:
- "How does checkout work across both apps?"
- "Why did we choose soft-delete?"
- "Is there a spec for guest checkout yet?"

---

## Handy things to say to Claude

- "Add a new doc type called `retros`."
- "Add a term to the glossary: a 'Reminder' is a scheduled nudge; in code it's `NotificationJob`."
- "Write a spec for password reset using our template."
- "Turn this meeting recording into a note and save it."
- "What should I do next?" (the wizard suggests the most useful next step)

---

## A few common questions

**Do I need to be technical?** No. Setup can be done by asking Claude; after that it's just chatting.

**Will this change our app code?** No. The hub reads your apps; it doesn't add anything to them.

**How often do I refresh?** After meaningful changes, or on a schedule. Repeat refreshes are fast.

**Where do I see a finished example?** Copy `examples/todo-app/` to explore a complete hub.
