# Implementation Plan: [FEATURE NAME]

**Feature Directory**: [SPECIFY_FEATURE_DIRECTORY]
**Spec**: [link to spec.md]
**Created**: [DATE]
**Branch**: [GIT_BRANCH]

---

## Technical Context

> Map the spec requirements to the chaman-api architecture. Fill or mark NEEDS CLARIFICATION.

| Concern | Resolution |
|---------|-----------|
| Action class(es) needed | `app/Actions/[Actor]/[ActionName].php` |
| DTO(s) needed | `app/Data/[FeatureData].php` |
| Repository changes | `app/Repositories/[Repo].php` |
| Model/migration changes | |
| Filament resource changes | Admin / Clinic / None |
| New routes | `routes/api.php` — actor prefix |
| Notification / event | |
| Queue jobs | |
| Payment gateway impact | None / [Gateway] |
| Translation keys | fa.json + en.json |

---

## Constitution Check

| Principle | Gate Status | Notes |
|-----------|-------------|-------|
| 1 — Actions as API Contract | ✅ PASS / ❌ FAIL | |
| 2 — Typed Data In/Out | ✅ PASS / ❌ FAIL | |
| 3 — Filament Tenant Scoping | ✅ PASS / ❌ FAIL / N/A | |
| 4 — Tests + Changelog | ✅ PASS / ❌ FAIL | |
| 5 — Farsi Localisation | ✅ PASS / ❌ FAIL / N/A | |
| 6 — Payment Gateway Pattern | ✅ PASS / ❌ FAIL / N/A | |

> ❌ FAIL gates block planning until resolved or explicitly waived with written rationale.

---

## research.md

> Generated in Phase 0. Resolves all NEEDS CLARIFICATION items.

---

## data-model.md

> Generated in Phase 1. Entity definitions, fields, relationships, state transitions.

---

## contracts/

> Generated in Phase 1. API endpoint contracts (request/response shapes).

---

## quickstart.md

> Generated in Phase 1. Runnable validation guide proving the feature works end-to-end.
