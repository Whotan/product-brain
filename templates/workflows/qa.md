# Workflow — QA

**Your lens:** a spec's acceptance criteria + the relevant graph slices.

- **Build a test plan:** start from the spec's acceptance criteria in `docs/specs/`. Each `(api)` / `(web)` tag tells you which side to exercise.
- **Find the surface area:** ask Claude "what does [feature] touch across both apps?" to see the code involved.
- **Report gaps as knowledge:** when behaviour diverges from the spec, file it as a decision or spec update so the gap is visible, not lost in a ticket.
