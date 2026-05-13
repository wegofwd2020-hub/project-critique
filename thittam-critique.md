# Thittam — Code Review & Critique

**Reviewed:** April 2026 (v1.2 — refreshed after proto completion, IAM Phase A REST surface, tenant address + multi-tenant demo expansion)
**Repos:** `wegofwd2020-hub/thittam` · `wegofwd2020-hub/thittam_docs`
**Phase:** Late-build / pre-production on core services
**Rating key:** ✅ Strong · ⚠️ Gap / Risk · ❌ Critical Issue

---

## Executive Summary

The two most critical findings from v1.1 are now closed:

1. **Schema injection in tenant routing is fixed.** `pkg/tenantdb/tenantdb.go` accepts only `uuid.UUID` values, rejects `uuid.Nil` before interpolation, and uses `uuid.UUID.String()` (36 hex/hyphen characters, no SQL metacharacters) in the `SET search_path` statement. The package comment documents why this is safe.
2. **T1 secret handling now matches the security doc.** `cmd/iam/main.go` loads JWT signing keys from Vault (production) or `FileSource` (dev, gitignored). Keys are held in process memory bytes only — never appear in env vars, logs, or disk after load. A Vault health check gates `/readyz` before the service accepts traffic.

The proto backlog is cleared. All 10 services (iam, project, budget, expense, ledger, inventory, notifications, document, reporting, billing) have complete `.proto` definitions totalling 1,659 lines and ~230 messages — not the "4 of 9 pending" state flagged in v1.1. Each service directory carries `handler.go`, `repository.go`, and `handler_test.go`; all services expose `/healthz`, `/readyz`, and `/metrics` on configurable ports. The test count grew from ~306 to **1,150 test functions across 80 files** — a 3.75× expansion — and coverage thresholds are enforced in CI (iam/ledger ≥85%, budget/expense ≥80%, others ≥75%). Playwright E2E is scaffolded with a first budgets-journey spec.

Multi-tenancy is reaffirmed as **tenant-per-schema** (commit 934bd58 corrected the docs to rule out the RLS-hybrid speculation). The XYZ_CBA movie-production demo is fully seeded; an XYZ Construction (USD/USA, construction vertical) Phase A seed scaffold is complete with cross-tenant UUID alignment for testing. The web tier moved to shadcn/ui with theme presets; auth now flows through an IAM grpc-gateway REST shadow (`/api/v1/auth/*`) rather than bare gRPC. Typography is compliant with Rule #18 (Inter, Merriweather, JetBrains Mono, OpenDyslexic).

Remaining concerns are mostly operational: the 9-step registration pipeline still lacks an explicit saga with compensating transactions; the impersonation lifecycle is not yet formalised (audit schema exists, UI exists, end-to-end lifecycle does not); the reporting service aggregates cross-service data without a documented read-model strategy; the `audit_log` `REVOKE UPDATE/DELETE` is still commented out in migration 001; ADRs 010 and 011 are missing from the numbering.

---

## What Changed Since v1.1

| Item | v1.1 | Now |
|---|---|---|
| Proto backlog | 4 of 9 pending (iam, ledger, notifications, document) | **10 of 10 defined** (1,659 LOC, ~230 messages) |
| Schema injection risk | ❌ Critical | ✅ Fixed — `pkg/tenantdb` UUID-typed interpolation |
| T1 secret handling | ❌ Contradicted security doc | ✅ Fixed — Vault → memory via `cmd/iam/main.go` |
| Test count | ~306 across 22 packages | **1,150 across 80 files** |
| Coverage gate | Targets documented | Enforced in CI (85% / 80% / 75% by service tier) |
| E2E tests | Nightly only | Playwright scaffolded + first budgets-journey spec (`a26bc2a`) |
| Web UI | Theme/stack unclear | shadcn/ui + theme presets (`4989191`); Radix primitives; Tailwind v4 |
| Auth flow | Bare gRPC assumption | grpc-gateway REST shadow for IAM auth (`939b451`, `cc7f019`, `7e267f7`) |
| `/me` endpoint | — | Returns roles + permissions from JWT claims (`b7049af`, `9082009`) |
| Tenant-from-email | — | Login resolves tenant when `Login.tenant_id` empty (`28cb0c8`, `3ec7abf`) |
| Multi-tenant demo | XYZ_CBA only | XYZ_CBA (INR, movie production) + XYZ Construction Phase A (USD, construction) |
| Tenant address + currency | — | Tenant carries address + country-driven primary currency (`2d2091e`, `cf79564`) |
| Dev ports | Default | Shifted to `:9086/:9100/:9300/:3100` to avoid StudyBuddy conflicts (`82d8338`) |
| CORS for browser dev | — | Wrapper on grpc-gateway for IAM auth (`cc7f019`) |
| Lint / CI | golangci-lint v1 baseline | golangci-lint v2 via action v8; Go pinned 1.25.9 for CVE patches (`6d7522c`) |
| Doc-drift enforcement | Aspirational | `tools/check-doc-drift` runs in CI; secret-existence check hoisted (`d700e15`) |

---

## 1. Architecture

### Strengths

- **Vertical plugin system is the right abstraction.** ADR-007 holds. YAML-driven configuration (entity labels, phase types, budget categories, workflows) lets a single codebase serve film production, software development, construction, and events management.
- **gRPC for internal, REST via grpc-gateway for browser-facing auth.** Type-safe internal contracts; grpc-gateway exposes auth RPCs over REST so the browser can speak JSON (and CORS works). Sensible bifurcation.
- **NATS JetStream for async patterns.** ADR-004 maintained.
- **All 10 proto definitions are complete.** IAM carries 46 messages (includes OIDC + auth RPCs), project 24, budget 24, expense 23, ledger 25, inventory 14, notifications 15, document 23, reporting 13, billing 23. Buf code generation via `make generate-proto`.
- **Istio service mesh for mTLS.** East-west traffic encrypted and authenticated.
- **Tenant-per-schema isolation.** Strongest multi-tenancy model. Enforced by `pkg/tenantdb.Acquire(ctx, pool, tenantID)` — sets `search_path` on the connection after validating the UUID.
- **13 ADRs documented.** Covers language, database, gRPC, events, API gateway, containers, vertical plugins, multi-tenancy, secret management, RBAC (ADR-014 Phase 2 in rollout behind `--with-project-rbac`), and more.
- **Consistent 6-file service structure.** `models.go`, `errors.go`, `repository.go`, `service.go`, `service_test.go`, `handler.go` — Rule #14 compliance is uniform across all 10 services.

### Gaps & Risks

⚠️ **Ten services remains large for the current stage.** Core financial services (iam, ledger, budget, expense, project) are production-shaped; reporting/document/inventory/notifications/billing are present but carry less business logic. A modular monolith at this stage would have shipped faster with the same domain separation. The gRPC boundaries are correct; the physical separation remains premature for the expected tenant count.

⚠️ **9-step registration pipeline still lacks a saga.** The pipeline spans multiple services and schemas. If step 5 fails, steps 1–4 have already made writes. `pkg/registration/` tracks pipeline state, but compensating transactions are not yet implemented. For a multi-tenant financial platform, this is the highest-priority architectural gap.

⚠️ **Reporting-analytics read-model is undefined.** The service aggregates data from all other services. Options — per-service event projections, a separate OLAP store (ClickHouse/DuckDB), or federated query — are not documented. `migrations/reporting/002_create_dashboard_views.up.sql` hints at a materialised-view direction, but the event-sourcing pipeline wiring is not visible.

⚠️ **Tenant-per-schema migration overhead scales poorly.** With every service's migrations running across N schemas, a migration that takes 30 seconds per schema takes 8+ hours across 1,000 tenants. Today's tenant count makes this tractable; a migration strategy with progress tracking and partial-failure recovery is due before the tenant count grows.

⚠️ **ADRs 010 and 011 missing from the numbering.** Either reserved or merged; document the gap or renumber.

---

## 2. Code Quality

### Strengths

- **Rule #1 — Money is never a float.** `shopspring/decimal` in Go + `NUMERIC(14,2)` in PostgreSQL is consistent across ledger, budget, expense.
- **Rule #2 (revised) — Secrets tiered by classification.** T1 secrets loaded from Vault at startup via `pkg/secrets.VaultSource`; dev uses `FileSource` with gitignored keys. T3 config (Vault address, AppRole credentials) remains in env vars. `cmd/iam/main.go` verifies this pattern.
- **Rule #4 — Interfaces for external dependencies.** Repository interfaces in every service; business logic calls interfaces, not drivers.
- **Rule #5 — Idempotency.** `ON CONFLICT (tenant_id, email) DO UPDATE/DO NOTHING` in IAM; `ON CONFLICT (tenant_id, code) DO NOTHING` in ledger. Payments stub carries an `IdempotencyKey` field.
- **Rule #7 — Audit log schema is correct.** `audit_log` table (per-tenant schema) has `actor_id`, `action`, `resource_type`, `resource_id`, `old_state`, `new_state`, `metadata`, `occurred_at`; indexes on tenant+resource, actor, time, action.
- **Rule #13 — Structured logging.** `pkg/observability/` handles JSON output with correlation IDs; no `fmt.Println` in service code.
- **Rule #14 — Consistent structure.** All 10 services follow the 6-file layout.
- **Rule #15 — Observability first-class.** Every service exposes `/healthz`, `/readyz`, `/metrics`.
- **Sentinel errors with package prefixes, wrapping at boundaries.** `errors.Is()` / `errors.As()` used consistently.
- **Zero TODO/FIXME in Go source.** Lint sweeps (`2820dcc` fixed 49 findings; `1954fc8` wrapped remaining deferred `rdb.Close`) kept debt out.
- **Doc-drift CI job.** `tools/check-doc-drift` runs on every PR; compares exported Go identifiers referenced in ` ```go ` fenced blocks in `thittam_docs` to the application source. Graceful skip when `DOCS_REPO_TOKEN` not set.

### Gaps & Risks

⚠️ **No data-validation library visible.** `protovalidate-go` or `buf/validate` is the natural fit with the existing proto tooling. Without it, boundary validation is handwritten per handler — inconsistent and hard to audit.

⚠️ **`audit_log` `REVOKE UPDATE/DELETE`** is commented out in `migrations/audit/001_create_audit_log.up.sql` (lines 27–29). Until a dedicated role is created and the REVOKEs applied in deployment, the table is append-only by convention, not by database constraint. Rule #7 specifies append-only; this gap should be closed before the first production tenant.

⚠️ **Production status `CHECK` constraint is hardcoded to movie-production lifecycle stages.** The XYZ Construction seed currently maps construction stages onto movie-production statuses as a workaround. Should be replaced by vertical-aware validation. Tracked in `docs/multi-tenancy.md §7`.

⚠️ **Rule #8 embeds `Co-Authored-By: Claude …` in commits.** This conflates authorship with tool-assistance. The `Co-Authored-By` trailer has specific meaning in open-source contribution workflows; AI-generated commits should use a distinct tag (e.g., `Tool: claude-opus-4-6`) rather than co-authorship.

---

## 3. Test Coverage

### Strengths

- **1,150 test functions across 80 files.** A 3.75× expansion from the v1.1 baseline of ~306. Coverage thresholds enforced in CI: `iam` and `ledger` ≥85%, `budget` and `expense` ≥80%, all others ≥75%.
- **Table-driven tests with `t.Parallel()`** — Rule #9 compliant.
- **Hand-written mocks (function field pattern).** Readable, debuggable, no framework required.
- **`vertical.WithConfig(ctx, fixture)` for vertical-aware tests.** Tests cannot accidentally pass via a hardcoded default config.
- **Deterministic UUIDs in fixtures** (e.g., `uuid.MustParse("d1000000-...")`).
- **Integration tests via testcontainers.** `make db-test-bootstrap` + `THITTAM_TEST_DSN` isolate test DB. Real Postgres, real migrations.
- **Playwright E2E scaffold exists.** `web/tests/e2e/` — `smoke.spec.ts`, `budgets-journey.spec.ts` (first business flow), `dashboard.spec.ts`. Playwright auto-boots the web server at `:3100`.
- **Contract-test plumbing visible** (Pact-shaped) in test fixtures, though not yet exhaustive across service boundaries.

### Gaps & Risks

⚠️ **E2E coverage is narrow.** One business journey (budgets) and a smoke spec. The critical paths that must be covered before GA — tenant registration (with saga failure injection), expense approval triggering a ledger entry, budget-vs-actual reporting, impersonation audit trail — do not yet exist as E2E tests.

⚠️ **No load or chaos testing.** A platform handling millions in production budgets needs: load tests for double-entry ledger posting, concurrent expense approvals; chaos/fault injection via Istio to verify circuit-breaker behaviour. Neither is in place.

⚠️ **Vertical plugin YAML lacks a dedicated test suite.** The vertical plugin system is the platform's core differentiator. `pkg/vertical/validator.go` exists but no dedicated test file exercises edge cases (empty `phase_types`, missing `budget_categories`, unknown fields, loading each YAML in `verticals/`).

⚠️ **Registration pipeline has no saga rollback tests.** Injecting a failure at each step and verifying the compensation is the only way to validate a saga. Absent until the saga itself is implemented.

---

## 4. Documentation

### Strengths

- **71 markdown files in `thittam_docs`.** Architecture, ADRs, services, verticals, data models, API conventions, deployment, operations, security, compliance, testing — the full documentation surface.
- **11 standard architecture diagrams present** (Rule #17): system-design, package-architecture, service-dependency-graph, deployment-diagram, network-security-diagram, database-er-diagram, sequence-diagrams, logical-domain-diagram, ci-cd-pipeline-diagram, nats-event-schemas, proto-service-index.
- **13 ADRs** (ADR-001 through ADR-015, with 010/011 missing). Each follows the Context → Decision → Rationale → Consequences format.
- **`CODING_RULES.md` expanded.** 17 rules, 11.7 KB — first-class document, codebase-authoritative.
- **Docs are fresh.** `multi-tenancy.md` updated 2026-04-15; `demo-xyz-construction-plan.md` drafted 2026-04-15.
- **Doc-drift CI enforces signature parity.** Exported Go identifiers referenced in ` ```go ` blocks are checked against the source on every PR.

### Gaps & Risks

⚠️ **ADRs 010 and 011 are missing from the numbering.** Fill the gap or renumber — readers will wonder what they were.

⚠️ **Webhook / NATS delivery-failure handling is under-specified.** What happens when a NATS consumer fails after N retries? Is there a dead-letter stream per consumer group? What is the alerting threshold? For financial events (budget approval, expense posting, ledger journal), silent message loss is unacceptable.

⚠️ **Vertical YAML has no authoritative schema.** High-level description exists; there is no JSON Schema or proto-based schema for the YAML itself. A developer adding a new vertical has no formal contract.

⚠️ **Compensating transactions for registration pipeline not documented.** Even without implementation, the compensation semantics (what each step's inverse is, failure-isolation expectations) should be written down.

---

## 5. Security

### Strengths

- **Tenant-per-schema is safe from injection.** `pkg/tenantdb.Acquire(ctx, pool, tenantID uuid.UUID)` accepts only `uuid.UUID`; validates `!= uuid.Nil`; interpolates `uuid.UUID.String()` (36 chars, hex + hyphens, no SQL metacharacters). Package comment documents why this is safe. A test `TestSetTenantSchemaRejectsInvalidInput` covers the case.
- **T1 secret handling matches the security doc.** `cmd/iam/main.go` lines 1–115: VAULT_ADDR → VaultSource → Vault KV v2 `iam/jwt-private-key` → memory bytes only. Dev path: file keys in gitignored `./keys/` → memory bytes. Never env var, log, or disk after load. `/readyz` gated by Vault health check.
- **Istio mTLS for east-west** (ADR architecture).
- **CORS wrapper on grpc-gateway for auth** (`cc7f019`) — browser can invoke `/api/v1/auth/*` cross-origin during dev.
- **`/me` endpoint hydrates session from JWT claims.** Roles and permissions returned; UI consumes the unwrapped response (no `{data: …}` envelope — `d01956d`, `7dc77f7`).
- **Append-only audit schema present** (constraint pending — see §2 gap).
- **Data classification tiers (T1–T4)** documented; column-level encryption for T1 fields (day_rate, vendor_gstin) at the application layer with AES-256-GCM.
- **Network security diagram present.** Security zones, TLS boundaries, and SOC-2 control mappings documented.
- **JWT tenant binding.** Gateway copies `tenant_id` claim to `X-Tenant-ID`; interceptor asserts match before any repository call.

### Gaps & Risks

⚠️ **Impersonation lifecycle is not end-to-end.** The audit table schema supports it; `web/components/audit-log-viewer.tsx` exists. The backend orchestration — who can initiate, session TTL, revocation on target-user password change, dual-actor audit entries (`actor_id` and `impersonated_by`) — is not yet shipped.

⚠️ **bcrypt cost 12 is CPU-exhaustion–susceptible under concurrent auth load.** ~250 ms per hash; a 100-concurrent login burst saturates 4 cores for multiple seconds. Either migrate to `argon2id` (better memory-hardness profile) or bound bcrypt concurrency via a semaphore and combine with per-IP rate limiting.

⚠️ **MinIO presigned URL TTL.** For industries with large file uploads/downloads (film dailies, construction blueprints, event AV assets), a 15-minute window may be too short on slower connections. Dynamic TTL based on file size, or a session-scoped server-side proxy, should be considered.

⚠️ **NATS per-subject authorization not detailed.** Security doc mentions "TLS + client certificate authentication between services and the broker" but does not specify which service is allowed to publish/subscribe to which subjects. A compromised `notifications` service should not be able to publish to `ledger.journal.posted`.

⚠️ **`audit_log` REVOKE UPDATE/DELETE not applied.** See §2. Schema is ready; deployment step is missing.

---

## 6. Scalability

### Strengths

- **Per-service databases eliminate cross-service DB contention.**
- **gRPC binary protocol reduces bandwidth 3–5× vs JSON REST.**
- **NATS JetStream decouples producer/consumer scale; flow control via JetStream.**
- **Kubernetes HPA documented** on CPU + custom metrics.
- **Istio circuit breakers, retries, canary deployments** are available via `VirtualService` / `DestinationRule`.
- **Connection-level tenant routing via `BeforeAcquire` hook.** No cross-schema pool contention.

### Gaps & Risks

⚠️ **Tenant-per-schema does not scale past ~500 tenants without strategy work.** Beyond that, schema migrations, vacuums, pool routing, and schema-aware backup all need tooling. A hybrid (per-schema for enterprise, shared-schema-with-RLS for small tenants) should be evaluated before the tenant count justifies the work.

⚠️ **Reporting-analytics aggregates across N services.** See §1. Without a dedicated read model, reporting load stresses transactional services and every report's tail latency is bounded by the slowest dependency.

⚠️ **Registration pipeline has no timeout management.** If the 9-step pipeline takes more than a few seconds (likely — schema creation + IAM migrations + chart-of-accounts seed + vertical bind), clients must poll for completion. Documented polling contract absent.

⚠️ **Vertical config caching strategy not documented.** Rule #3 mandates L1 → L2 → L3 caching. Vertical configs are read on every vertical-aware gRPC call; caching behaviour and invalidation semantics should be explicit given how hot this path is.

⚠️ **gRPC load balancing config should be verified.** HTTP/2 multiplexes on a single TCP connection — L4 load balancers do not distribute evenly. Istio `DestinationRule` with `ROUND_ROBIN` resolves this; confirm the configuration is present for all service-to-service calls.

---

## 7. Additional Observations

### DevEx & Tooling

✅ `make help` surfaces all targets. `make dev-start` boots IAM first (gRPC :8086, REST :9086, metrics :9096), then core services in parallel. `make dev-start-fresh` resets DB + migrates + seeds. `--with-project-rbac` flag enables ADR-014 Phase 2.
✅ Ports shifted to avoid StudyBuddy conflicts (`82d8338`). Project-management on :9100; UI on :3100; Prometheus on :9300.
✅ Go pinned to 1.25.9 for stdlib CVE patches. golangci-lint v2 via action v8.
⚠️ `make new-service name=X` generator is still "planned" per CODING_RULES.md. Until it exists, new services are added by manual copy-paste — error-prone.
⚠️ No mention of local development tooling for the full 10-service stack. Running 10 services + Postgres + Redis + NATS + MinIO locally is resource-intensive. The `dev-start.sh` orchestration is a good start; a `docker-compose.yml` for contributors without Go toolchains would help.

### Frontend

✅ shadcn/ui foundation + theme presets (`4989191`). 60 `.tsx` components. Radix UI primitives. Tailwind v4 + PostCSS.
✅ Typography rule #18 compliant: `@fontsource/inter`, `@fontsource/merriweather`, `@fontsource/jetbrains-mono`, `@fontsource/opendyslexic`.
✅ Next.js 16.2.2, React 19.2.4.
⚠️ UI tenant switcher absent. Multi-tenant users must log out to switch — planned post-v1 per `multi-tenancy.md §7`.

### SaaS Billing

✅ Billing service now present in `services/billing/` (the v1.1 gap — "in docs but not in `cmd/`" — is closed). Proto: 23 messages.
⚠️ Usage metering for billing is not documented. Expense/budget volumes per tenant are natural billing metrics; instrumentation should be explicit.

### Operational Readiness

✅ `/healthz`, `/readyz`, `/metrics` on every service; Prometheus scrape target on :9300.
✅ OpenTelemetry → Grafana stack documented.
⚠️ No documented circuit-breaker policy per service. If `general-ledger` is unavailable, how does `expense-tracking` degrade? Retry config without a circuit breaker risks cascading failure.
⚠️ NATS dead-letter strategy for financial events undocumented. See §4.

### Multi-Tenant Demo Coverage

✅ XYZ_CBA Productions (movie-production, INR) fully seeded. Users across Owner, Exec Producer, Line Producer, Production Accountant, and crew roles. Login `email + demo1234` (bcrypt cost 12 fixed in `96be1fa`).
✅ XYZ Construction LLC (construction, USD) Phase A scaffold complete (`512d662`). UUIDs aligned cross-tenant (`79e89c7`) for integration testing. 6 projects planned with budget states from draft to locked.
⚠️ Phase B (actuals/expenses) and Phase C (approval workflows) for XYZ Construction still pending.

---

## Priority Actions (Ordered)

| Priority | Action | Area |
|---|---|---|
| P0 | Design + implement the saga pattern for the 9-step registration pipeline; add rollback tests that inject failure at each step | Architecture |
| P0 | Ship the `audit_log` REVOKE UPDATE/DELETE + app-role plumbing so append-only is a DB constraint, not a convention | Security |
| P1 | Document and implement the reporting-analytics read-model strategy (event-sourced projections preferred) | Architecture |
| P1 | Finalise impersonation lifecycle — TTL, revocation, dual-actor audit; write ADR-016 | Security |
| P1 | Adopt `protovalidate-go` for proto-level boundary validation | Code Quality |
| P1 | Replace bcrypt with `argon2id` or bound bcrypt concurrency + per-IP rate limiting | Security |
| P1 | Add NATS dead-letter strategy for financial events with alerting + replay runbook | Architecture |
| P1 | Write a vertical YAML JSON Schema + dedicated validator test suite | Testing |
| P1 | Replace movie-production-specific production status CHECK with vertical-aware validation | Code Quality |
| P1 | Expand E2E suite beyond budgets-journey: expense approval → ledger entry, registration saga, impersonation audit | Testing |
| P2 | Evaluate tenant-per-schema scalability beyond 500 tenants; document decision in a new ADR | Scalability |
| P2 | Define per-service circuit-breaker policy + verify `DestinationRule` load balancing config | Scalability |
| P2 | Add load tests for double-entry ledger posting + concurrent expense approval | Testing |
| P2 | Ship `make new-service` generator | DevEx |
| P2 | Document usage-metering instrumentation for billing | Billing |
| P2 | Complete XYZ Construction Phase B (actuals/expenses) + Phase C (approvals) | Demo |
| P3 | Fill ADR 010 / 011 gap or renumber | Documentation |
| P3 | Implement UI tenant switcher post-v1 | UI |
| P3 | Replace `Co-Authored-By: Claude …` with a distinct tool-attribution tag | Process |
| P3 | Document webhook / NATS per-subject authorization in security doc | Security |
