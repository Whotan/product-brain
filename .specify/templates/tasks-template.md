# Tasks: [FEATURE NAME]

**Feature Directory**: [SPECIFY_FEATURE_DIRECTORY]
**Plan**: [link to plan.md]
**Generated**: [DATE]

---

## Task Categories

Tasks are grouped by layer. Each task must reference a requirement from spec.md (`REQ-NNN`).

### 0 — Prerequisite / Migration

- [ ] **T000** Create migration(s) for new/modified tables (`make artisan make:migration`)
- [ ] **T001** Create/update model(s) with casts, relationships, strict types

### 1 — Data Layer

- [ ] **T100** Create DTO(s) in `app/Data/` (Spatie Laravel-Data)
- [ ] **T101** Create/update Repository in `app/Repositories/`

### 2 — Business Logic

- [ ] **T200** Create Action class(es) in `app/Actions/[Actor]/`
- [ ] **T201** Create Service class(es) in `app/Services/` (if orchestration needed)
- [ ] **T202** Register route(s) in `routes/api.php`

### 3 — Filament UI (if applicable)

- [ ] **T300** Create/update Filament Resource in `app/Filament/[Panel]/Resources/`
- [ ] **T301** Create Form schema in `.../Schemas/`
- [ ] **T302** Create Table schema in `.../Tables/`
- [ ] **T303** Create/update Relation Managers

### 4 — Notifications / Events / Jobs

- [ ] **T400** Create notification(s) in `app/Notifications/`
- [ ] **T401** Register event listener(s) in `EventServiceProvider`
- [ ] **T402** Create queued job(s) if async processing needed

### 5 — Localisation

- [ ] **T500** Add translation keys to `lang/fa.json`
- [ ] **T501** Add translation keys to `lang/en.json`
- [ ] **T502** Run `make optimize` to bust translation cache

### 6 — Tests

- [ ] **T600** Feature test: happy path(s) — mirrors `Actions/` namespace
- [ ] **T601** Feature test: failure / edge case paths
- [ ] **T602** Filament test(s) if panel resources changed (`tests/Feature/Filament/`)
- [ ] **T603** Run `make test filter=[FeatureName]` — all pass

### 7 — Quality Gate

- [ ] **T700** `make phpstan` — no new errors
- [ ] **T701** `make cs-fixer` — code style clean
- [ ] **T702** Add `CHANGELOG.md` entry
- [ ] **T703** `make commit` — PHPStan + Pint + Insights all pass

---

## Dependency Order

```
T000 → T001 → T100 → T101 → T200 → T202
                                  ↘
                              T300–T303 (if Filament)
T200 → T400–T402 (if notifications/events)
T200 → T500–T502
T*** → T600–T602 → T700–T703
```
