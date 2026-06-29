# Vocabulary

> The shared glossary: product language ↔ code terms, across every repo.
> This is the source of truth and it is graphed. graphify connects it to the code and docs
> automatically — no manual links needed.

**Version:** 1.0.0
**Last updated:** [DATE]

---

## Session

- **What it is:** A booked block of time between a coach and a client.
- **Also called:** booking (backend-api), appointment (backend-api), session (web-app)
- **In code:** `Appointment` (backend-api, model), `SessionCard` (web-app, component)

## Slot

- **What it is:** An available window a client can book a session into.
- **Also called:** availability (backend-api), opening (web-app)
- **In code:** `AvailabilityWindow` (backend-api, model)

---

> **How to fill an entry:**
>
> - **What it is** — required. One or two sentences in product language, not code language.
> - **Also called** — required. Every alias used for this concept, each tagged with the app or
>   context where that name appears: `term (repo-or-app)`. Different repos often use different
>   names for the same concept — capturing which name lives where is the whole point.
> - **In code** — list the 2–5 *most representative* symbols: typically the main model, the main
>   service or action class, and the main API/UI entry point. Use format `Symbol (repo, type)`.
>   Do **not** list every repository, middleware, test, or resource class — the graph already
>   indexes those. The vocabulary is a navigational bridge, not an exhaustive symbol index.
>
> Add one `##` section per concept. Keep the "In code" line current — it's the bridge between
> product language and the codebase.
