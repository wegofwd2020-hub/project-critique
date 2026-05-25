# Thittam — Scoping, Design, Architecture & Development Pattern

**Document type:** Development pattern analysis
**Scope:** Full lifecycle — from concept to late-build production system
**Period:** 2025–2026
**Last refresh:** 2026-05-24 (v1.3 — alignment with critique v1.3: first refresh measured against on-disk code; registration saga, reporting read-model, impersonation lifecycle confirmed implemented; schema-injection + T1 fixes verified in source)
**Prior:** v1.2 April 2026 (proto completion, T1 secret fix, schema injection fix, shadcn/ui adoption, XYZ Construction demo)
**Related:** [thittam-critique.md](thittam-critique.md) · [thittam-practices.md](thittam-practices.md) · [thittam-cost.md](thittam-cost.md)
**Author:** WeGoFwd2020 / Claude (Anthropic)

> **Note (2026-05-24):** the body below is the v1.2 record (April 2026), preserved. No documented development-pattern claim has been overturned by the v1.3 refresh — but **the refresh revealed a methodological gap worth naming**: prior reviews were inferred from docs + commit history (the sibling `thittam_docs` repo and PROGRESS files), and the v1.3 pass against actual on-disk source found that **three "open" items were already implemented but undocumented in the public-facing surface**. New since v1.2, worth noting:
>
> - **"Verify against on-disk source" as a review-cadence step.** Documentation and commit subjects under-described what landed. The registration saga (`pkg/registration/saga.go`, 497 LOC), reporting read-model (`services/reporting/consumer.go`, `ProjectionConsumer`), and impersonation lifecycle (`services/iam/service.go` with 4h cap and expiry ticker) were all flagged "open" in v1.2 and v1.3-critique-of-record but were already on disk. Future reviews should not skip the on-disk pass.
> - **Saga as a documented pattern.** The registration saga implementation makes the previously-aspirational compensation pattern concrete: `SagaStatus` state machine (`compensating` / `compensated` / `compensation_failed`), `Compensator` interface, reverse-order compensation 3→2→1, idempotent step tracking. The pattern is reusable across other multi-step orchestrations (billing-tenant-bootstrap, document-storage-migration).
> - **Event-sourced read-model as a documented pattern.** `ProjectionConsumer` subscribes to domain events and maintains a read-model projection — the option the v1.2 critique preferred over CQRS-on-read or denormalized-snapshots. Worth documenting as the canonical Thittam pattern for cross-service aggregations.
> - **Bounded impersonation as a discipline.** 4h cap + background expiry ticker + `impersonation.start` / `.end` audit actions. Sets the template for any time-bounded privilege elevation.
> - **The `thittam_docs` repo unverifiability is now a method-level caveat.** The "71 docs / 13 ADRs (010/011 gap)" claim from earlier cycles cannot be checked from the code repo. Future review cadence should either check both repos or scope claims to one.
>
> Re-measured: 1,715 proto LOC (was 1,659), 1,203 Go test functions across 86 files (was 1,150 / 80). `audit_log` REVOKE remains the one open P0 — append-only is still enforced by convention, not by DB grant. See [thittam-cost.md](thittam-cost.md) for the real-world cost-of-time-and-money analysis of the patterns documented below.

---

## Table of Contents

1. [The Problem Being Solved](#1-the-problem-being-solved)
2. [Scoping Pattern](#2-scoping-pattern)
3. [Design Pattern](#3-design-pattern)
4. [Architecture Pattern](#4-architecture-pattern)
5. [Development Pattern](#5-development-pattern)
6. [Key Decisions and Their Rationale](#6-key-decisions-and-their-rationale)
7. [What This Pattern Teaches](#7-what-this-pattern-teaches)

---

## 1. The Problem Being Solved

Thittam (திட்டம் — "plan" in Tamil) addresses a specific gap: production management — tracking budgets, expenses, crew, schedules, and documents — is handled differently across industries, yet the underlying financial and project management operations are identical.

A film production, a construction site, a software development team, and an event management company all need:

- Budget versions with approval workflows
- Expense tracking with purchase orders and receipts
- A double-entry general ledger
- Crew or team scheduling
- Document management with versioning
- Real-time reporting across all of the above

The difference is vocabulary and workflow configuration — not the underlying financial model.

```
Problem Statement
      │
      ▼
Four industries, four vocabulary sets, one financial model

  Film Production          Construction
  ┌──────────────┐         ┌──────────────┐
  │ Scenes       │         │ Phases       │
  │ Daily rates  │         │ Milestones   │
  │ Crew         │         │ Subcontract  │
  │ Per-diem     │         │ Materials    │
  └──────────────┘         └──────────────┘
          │                        │
          └──────────┬─────────────┘
                     │
          ┌──────────▼─────────────┐
          │  Same financial model   │
          │                        │
          │  Budget → Expense      │
          │  Approval → Ledger     │
          │  Report → Analytics    │
          └────────────────────────┘
                     │
          ┌──────────┴─────────────┐
          │                        │
  Software Dev            Events Mgmt
  ┌──────────────┐         ┌──────────────┐
  │ Sprints      │         │ Venue        │
  │ Story points │         │ Suppliers    │
  │ Contractors  │         │ F&B          │
  │ Licenses     │         │ AV/Tech      │
  └──────────────┘         └──────────────┘
```

The insight that shaped Thittam's architecture: **build the financial core once, make the vocabulary configurable**.

---

## 2. Scoping Pattern

### 2.1 Scope Anchored by Industry Verticals

Thittam scoped by industry vertical. The first scoping question was: *which industries are in scope for GA, and what does each one need?*

```
Vertical scoping matrix

                 Film   Software   Construction   Events
Project phases    ✅      ✅           ✅            ✅
Budget versions   ✅      ✅           ✅            ✅
Expense/PO        ✅      ✅           ✅            ✅
Double-entry GL   ✅      ✅           ✅            ✅
Crew scheduling   ✅      ✅           ✅            ✅
Inventory/equip   ✅      ❌           ✅            ✅
Documents/sigs    ✅      ✅           ✅            ✅
Industry labels   Custom  Custom      Custom        Custom
Phase types       Custom  Custom      Custom        Custom
Budget cats       Custom  Custom      Custom        Custom
Currency          INR     USD/…       USD/…         USD/…
```

The matrix revealed that the difference between verticals is entirely in the **configuration layer** — the services themselves are identical.

### 2.2 Scoping by Service Boundary

The scope of each service was defined by a single question: *what does this service own, and what does it never touch?*

| Service | Owns | Never touches |
|---|---|---|
| IAM | Tenants, users, roles, invitations, auth | Budgets, expenses, documents |
| Budget | Budget versions, line items, approvals | Ledger journal entries |
| Expense | POs, receipts, petty cash | Budget balances directly |
| Ledger | Chart of accounts, journal entries, periods | Budget line items |
| Project | Projects, phases, crew, schedules | Financial transactions |
| Inventory | Equipment, props, locations, assets | Project schedules |
| Reporting | Read-only aggregations | Any write operations |
| Notifications | Templates, delivery, log | Business domain data |
| Document | Files, versions, e-signatures | Content of documents |
| Billing | Subscriptions, invoicing, usage metering | Domain data |

Ten services total. This matrix was defined before implementation and served as the authoritative boundary for where a given feature belonged.

### 2.3 Scoping the Multi-Tenancy Model

The tenancy scope question was answered early and explicitly via ADR-008, then reaffirmed in April 2026 (docs commit `934bd58` "correct isolation model to tenant-per-schema"):

> "Each tenant gets schema `tenant_<uuid>` in PostgreSQL. Tenant context is set via `X-Tenant-ID` header on every request. The `BeforeAcquire` hook on the pgx pool ensures every connection is scoped to the correct tenant schema."

Three options were evaluated:

| Option | Description | Outcome |
|---|---|---|
| Separate instance per tenant | Strongest isolation, highest cost | Offered as enterprise tier only |
| Shared schema, row-level filtering | Application-layer isolation | Rejected |
| Tenant-per-schema | Database-level isolation | Accepted |

The tenant-per-schema decision locked in a set of operational constraints: migrations must run across N schemas, connection pool routing must be tenant-aware, and reporting queries cannot join across schemas.

### 2.4 Scoping Multi-Tenant Demos

Two demo tenants were scoped to exercise the multi-industry, multi-currency posture:

```
XYZ_CBA Productions (fully seeded)
  Tenant UUID:  d0000000-0000-0000-0000-000000000001
  Vertical:     movie-production
  Currency:     INR
  Country:      India
  Purpose:      Demonstrate film-production workflows end-to-end.

XYZ Construction LLC (Phase A scaffold complete, Phase B/C pending)
  Tenant UUID:  d0000000-0000-0000-0000-000000000002
  Vertical:     construction
  Currency:     USD
  Country:      USA
  Purpose:      Demonstrate construction workflows + cross-tenant isolation
                tests with a different currency and country.
```

Cross-tenant UUID alignment (`79e89c7`) makes integration tests that assert isolation tractable.

---

## 3. Design Pattern

### 3.1 Rules Before Code

The most distinctive aspect of Thittam's design pattern is that 17 non-negotiable coding rules were written and locked before significant implementation began:

```
Rule hierarchy

  Non-negotiable (17 rules in CODING_RULES.md)
  │
  ├── Money is never a float (Rule #1)
  ├── Secrets tiered by classification — T1 from Vault, T3 from env (Rule #2)
  ├── Cache by default, not as optimisation (Rule #3)
  ├── Interfaces for all external dependencies (Rule #4)
  ├── Idempotency everywhere (Rule #5)
  ├── Writes never block reads (Rule #6)
  ├── Audit everything that matters (Rule #7)
  ├── Conventional Commits (Rule #8)
  ├── Test isolation (Rule #9)
  ├── Document the WHY, not the WHAT (Rule #10)
  ├── Validate at the boundary, trust internally (Rule #11)
  ├── Structured logging, never print() (Rule #12)
  ├── Observability as first-class concern (Rule #13)
  ├── Consistent project structure (Rule #14)
  ├── Separate documentation repository (Rule #15)
  ├── Guard against documentation drift (Rule #16)
  └── Standard architecture diagrams (Rule #17)
  ├── (v1.2 added) Typography & accessibility standards (Rule #18)
  │     ← Inter + Merriweather + JetBrains Mono + OpenDyslexic

  Language-specific (go-conventions.md)
  │
  ├── Service file layout (models/errors/repository/service/handler)
  ├── Error handling (sentinel errors, wrapping at boundaries)
  ├── Monetary types (shopspring/decimal only)
  ├── SQL (sqlc, parameterised, never interpolated)
  └── Testing (table-driven, t.Parallel(), hand-written mocks)
```

Writing the rules first had a specific effect: every design decision was evaluated against explicit constraints before it was accepted. This reduced the cost of design review because the criteria were already written.

When the security doc and Rule #2 contradicted on T1 secrets (v1.1 critique), the resolution was not to pick one — it was to rewrite Rule #2 in terms of data classification tiers (T1 → Vault, T3 → env), which is now how `cmd/iam/main.go` actually works.

### 3.2 The ADR Record

Thirteen Architecture Decision Records are written (ADR-001 through ADR-015, with 010 and 011 missing from numbering — either reserved or to be renumbered):

| ADR | Decision | Rationale |
|---|---|---|
| ADR-001 | Go 1.22+ for all services | Type safety, performance, standard library, gRPC support |
| ADR-002 | PostgreSQL with tenant-per-schema | Strongest isolation, compliance-ready, complex queries |
| ADR-003 | gRPC for internal service communication | Type-safe contracts, binary protocol, bi-directional streaming |
| ADR-004 | NATS JetStream for async messaging | At-least-once delivery, consumer ACK, replay, persistence |
| ADR-005 | Kong API Gateway at edge | Rate limiting, JWT validation, routing without custom middleware |
| ADR-006 | Docker + Kubernetes | Container portability, HPA for variable load |
| ADR-007 | YAML-driven vertical plugin system | Industry-agnostic without multiple codebases |
| ADR-008 | Tenant-per-schema multi-tenancy | DB-level isolation, compliance provability |
| ADR-009 | Vault for T1 secret management | Audit trail, rotation, never in environment variables |
| ADR-012 | shadcn/ui + Radix primitives for the web tier | Accessibility, theme-ability, component ergonomics |
| ADR-013 | grpc-gateway REST shadow for IAM auth | Browser-friendly auth flow without building a separate HTTP server |
| ADR-014 | RBAC role model (Phase 2 in rollout) | Role-permission-gated endpoints; project-scope in --with-project-rbac |
| ADR-015 | Tenant address + country-driven primary currency | Multi-currency demos without user input |

Each ADR follows the same structure: Context → Decision → Rationale with trade-off table → Consequences.

### 3.3 The Vertical Plugin System Design

ADR-007 is the most distinctive design decision in Thittam. The vertical plugin system enables one codebase to serve four industries without branching:

```
Vertical YAML (e.g. verticals/film-production.yaml)
┌────────────────────────────────────────────────────────┐
│  id: film-production                                    │
│  name: Film Production                                  │
│  entity_labels:                                         │
│    project: Production                                  │
│    phase: Shooting Day                                  │
│    crew_member: Cast & Crew                            │
│  phase_types:                                           │
│    - pre_production                                     │
│    - principal_photography                              │
│    - post_production                                    │
│  budget_categories:                                     │
│    - above_the_line                                     │
│    - below_the_line                                     │
│    - post_production                                    │
│  workflows:                                             │
│    expense_approval_required: true                      │
│    per_diem_enabled: true                               │
│    daily_rate_billing: true                             │
└────────────────────────────────────────────────────────┘
         │
         ▼
  pkg/vertical/loader.go
  ├── Load YAML at service startup
  ├── Validate against schema (pkg/vertical/validator.go)
  ├── Cache in Redis (L1 in-process + L2 Redis)
  └── Serve via gRPC interceptor to all vertical-aware services
         │
         ▼
  Vertical-aware service (e.g. budget)
  ├── Reads tenant's vertical config from context
  ├── Renders labels from config (not hardcoded)
  ├── Validates phase_type against config's phase_types
  └── Applies workflow rules from config
```

The vertical config flows through every vertical-aware service via a gRPC interceptor that injects it into the request context. Services never hardcode industry-specific behaviour.

### 3.4 Data Classification Design

The security design was anchored by a data classification tier system:

```
T1 — Highly Sensitive (Vault only, memory-bytes at runtime, AES-256-GCM column-encryption at rest for financial T1 fields)
  day_rate (payroll data)
  vendor_gstin (tax IDs)
  JWT signing keys
  Database passwords
  API keys (third-party)

T2 — Confidential (encrypted in transit, access-controlled)
  Budget line items
  Expense amounts
  Vendor names
  Salary information

T3 — Internal (standard access controls, acceptable as env vars)
  Project names and descriptions
  Phase schedules
  Crew assignments
  Vault AppRole credentials
  Service endpoints

T4 — Public (no restrictions)
  Vertical configuration labels
  Phase type definitions
  Public-facing pricing
```

The classification directly drives implementation:
- T1 data is fetched from Vault at startup; held in process memory bytes; never env-vars, never logs, never re-serialised.
- T1 financial columns (day_rate, vendor_gstin) are AES-256-GCM encrypted at the application layer before writing to PostgreSQL.
- T3 config sits in env vars (`VAULT_ADDR`, `VAULT_ROLE_ID`).
- `/readyz` gates on Vault reachability; IAM refuses requests without T1 loaded.

### 3.5 Typography & Accessibility Design (Rule #18, v1.2)

The web tier design includes a 3-font typography system plus dyslexia-friendly accessibility:

```
Font stack (all SIL Open Font License, self-hosted via @fontsource):

  --font-heading   Inter          ← headings, labels, buttons, nav
  --font-body      Merriweather   ← paragraphs, tooltips, form inputs
  --font-mono      JetBrains Mono ← amounts, dates, IDs, account codes

Per-vertical icon sets (lucide-react, curated 8–12 per vertical):

  construction → hammer, ruler, hardhat, truck, …
  film         → clapperboard, film-reel, megaphone, …

OpenDyslexic toggle:

  Switches all three font families to OpenDyslexic / OpenDyslexic Mono
  letter-spacing +0.05em, line-height 1.8, word-spacing +0.1em
  Persisted in user preferences (localStorage + API backup)
```

---

## 4. Architecture Pattern

### 4.1 System Topology

```
Internet / Tenant Browser
        │
        ▼
┌───────────────────────────────────────────────────────────────────┐
│  Kong API Gateway                                                  │
│  Rate limiting · JWT validation · Request routing                 │
│  X-Tenant-ID header injection                                     │
└────────────────────────┬──────────────────────────────────────────┘
                         │  REST/JSON (external)
                         ▼
┌───────────────────────────────────────────────────────────────────┐
│  IAM grpc-gateway REST shadow (v1.2)                               │
│  /api/v1/auth/login · /api/v1/auth/refresh · /api/v1/auth/me      │
│  CORS wrapper for browser dev                                     │
└────────────────────────┬──────────────────────────────────────────┘
                         │  REST translated to gRPC calls
                         ▼
┌───────────────────────────────────────────────────────────────────┐
│  Service Mesh (Istio)                                              │
│  mTLS for all east-west traffic                                   │
│  Circuit breakers · Retries · Canary deployments                  │
│                                                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │   IAM    │  │ Project  │  │  Budget  │  │ Expense  │         │
│  │ gRPC:8086│  │  Mgmt    │  │ Planning │  │Tracking  │         │
│  │ REST:9086│  │  :8080   │  │  :8081   │  │  :8082   │         │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘         │
│       │              │              │              │               │
│  ┌────▼─────┐  ┌────▼─────┐  ┌────▼─────┐  ┌────▼─────┐         │
│  │  General │  │Inventory │  │Reporting │  │Notifica- │         │
│  │  Ledger  │  │  Mgmt    │  │Analytics │  │  tions   │         │
│  │  :8083   │  │  :8084   │  │  :8085   │  │  :8087   │         │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘         │
│  ┌──────────┐  ┌──────────┐                                      │
│  │ Document │  │ Billing  │                                      │
│  │  :8088   │  │  :8089   │                                      │
│  └──────────┘  └──────────┘                                      │
└───────────────────────────────────────────────────────────────────┘
                         │  gRPC (sync internal)
                         │  NATS JetStream (async internal)
                         ▼
                   PostgreSQL (per-tenant schemas) · Redis · MinIO · Vault
```

Ten services are deployed (iam, project, budget, expense, ledger, inventory, notifications, document, reporting, billing). All proto definitions are complete.

### 4.2 Service Communication Model

Two communication patterns coexist:

```
Synchronous (gRPC)
  Used when: Caller needs an immediate response
  Examples:
    ├── IAM → any service (JWT validation)
    ├── Budget → Ledger (expense approval → journal entry)
    └── Reporting → all services (data aggregation)

  Properties:
    Type-safe contracts (protobuf)
    Binary protocol (3–5× smaller than JSON)
    Client-side load balancing via Istio DestinationRule
    Circuit breakers via Istio VirtualService

Asynchronous (NATS JetStream)
  Used when: Caller does not need to wait
  Examples:
    ├── Expense approved → Notifications
    ├── Budget threshold hit → Notifications
    ├── Ledger posted → Reporting
    └── Registration complete → all services (seed events)

  Properties:
    At-least-once delivery
    Consumer-level ACK
    Replay capability
    Event deduplication via event_id (Rule #5)
```

### 4.3 Multi-Tenant Data Model

```
PostgreSQL Server
│
├── public schema (shared tables: tenants, platform config, processed_events)
│
├── tenant_<uuid-A> schema (Tenant A's isolated data)
│   ├── projects
│   ├── budgets
│   ├── expenses
│   ├── journal_entries
│   ├── users
│   ├── audit_log
│   └── (all domain tables)
│
├── tenant_<uuid-B> schema (Tenant B's isolated data)
│   ├── (identical table set)
│
└── tenant_<uuid-N> schema

Connection pool BeforeAcquire hook (pkg/tenantdb):
  1. Accept uuid.UUID (type-safe; compile-time guarantee)
  2. Validate != uuid.Nil
  3. Interpolate uuid.UUID.String() — 36 chars, hex + hyphens, safe
  4. SET search_path = tenant_<uuid>, public
```

The schema injection risk flagged in v1.1 is closed at the type boundary.

### 4.4 Registration Pipeline (9-Step Process)

Tenant onboarding is a multi-service distributed transaction:

```
POST /register (Kong API Gateway)
      │
      ▼
pkg/registration/pipeline.go — orchestrates all steps
      │
      ├── Step 1: Validate tenant data (slug, contact email, vertical ID)
      │
      ├── Step 2: Create tenant record in public.tenants
      │
      ├── Step 3: Create tenant schema (CREATE SCHEMA tenant_<uuid>)
      │
      ├── Step 4: Run IAM migrations in new schema
      │
      ├── Step 5: Seed IAM — create platform role + admin user
      │
      ├── Step 6: Seed Ledger — chart of accounts for tenant's vertical
      │
      ├── Step 7: Bind vertical — store tenant's YAML config
      │
      ├── Step 8: Emit registration.complete event (NATS JetStream)
      │
      └── Step 9: Send welcome notification (async via NATS)
              │
              ▼
        [Known architectural gap: no saga pattern —
         partial failure in steps 2-8 has no compensating
         transaction strategy. Identified in v1.1, still open.]
```

The `pkg/registration/` package tracks pipeline state, but compensating transactions are not yet documented or implemented. This remains the most critical architectural gap.

### 4.5 Observability Model

Every service implements Rule #13 identically:

```
Service startup
      │
      ├── /healthz  → liveness probe
      ├── /readyz   → readiness (DB + Redis + NATS + Vault connected)
      └── /metrics  → Prometheus metrics endpoint

gRPC interceptor chain (every service):
  ├── pkg/observability/interceptor.go
  │   ├── request_duration_seconds (histogram)
  │   ├── request_total (counter, by status)
  │   └── correlation_id injected into every log entry
  │
  ├── pkg/audit/interceptor.go
  │   ├── Captures actor_id, action, resource_type, resource_id
  │   ├── Captures old_state + new_state for mutations
  │   └── Writes append-only audit log
  │
  └── pkg/auth/resolver.go
      └── Validates JWT, extracts tenant_id + user claims

Metrics flow:
  Service /metrics → Prometheus (:9300 scrape) → Grafana dashboard

Health aggregation:
  Vault health check plugged in via secrets.VaultSource
  → /readyz blocks until Vault reachable
```

### 4.6 The Audit Log Design

```
audit_log table (per-tenant schema, append-only)

  id              UUID PK
  actor_id        UUID     who performed the action
  action          TEXT     what was done (CREATE_BUDGET, APPROVE_EXPENSE, …)
  resource_type   TEXT     entity type
  resource_id     UUID     specific entity
  tenant_id       UUID     for cross-schema audit queries
  occurred_at     TIMESTAMPTZ
  old_state       JSONB    before mutation
  new_state       JSONB    after mutation
  metadata        JSONB    correlation_id, ip, user_agent

Indexes:
  (tenant_id, resource_type, resource_id)
  (actor_id, occurred_at)
  (occurred_at)
  (action)

Constraints (pending deployment step — see practices doc):
  REVOKE UPDATE ON audit_log FROM thittam_app
  REVOKE DELETE ON audit_log FROM thittam_app

Partition by month for query performance at scale (planned).
```

### 4.7 Service Internal Structure

Every service follows the same 6-file layout (Rule #14):

```
services/{name}/
  models.go       ← Domain types (structs with JSON tags)
  errors.go       ← Sentinel errors (var ErrNotFound = errors.New("budget: not found"))
  repository.go   ← Repository interface (data access contract)
  service.go      ← Business logic (vertical config via context)
  service_test.go ← Unit tests (mock repo + injected config)
  handler.go      ← gRPC handler (wraps service)

Rule: Dependencies flow inward only
  handler.go  ←  service.go  ←  repository.go
  (gRPC)          (logic)         (DB interface)

Shared packages (pkg/):
  pkg/audit/       ← Audit log writer + gRPC interceptor
  pkg/auth/        ← JWT validation + OIDC provider
  pkg/demo/        ← Demo tenant generator + provisioner
  pkg/observability/ ← Metrics + health + gRPC interceptor
  pkg/platform/    ← Platform admin service + impersonation
  pkg/registration/ ← 9-step tenant registration pipeline
  pkg/secrets/     ← Vault source + file source + health check
  pkg/tenant/      ← Tenant context helpers
  pkg/tenantdb/    ← Safe tenant-schema routing
  pkg/vertical/    ← Vertical config loader + gRPC middleware
  pkg/server/      ← gRPC server builder (shared setup)
```

### 4.8 Web Tier Architecture (v1.2)

```
web/ — Next.js 16.2.2, React 19.2.4, Tailwind v4

Component foundation: shadcn/ui + Radix primitives (dialog, dropdown, label,
select, slot, switch, tabs).

Typography (Rule #18):
  @fontsource/inter           (--font-heading)
  @fontsource/merriweather    (--font-body)
  @fontsource/jetbrains-mono  (--font-mono)
  @fontsource/opendyslexic    (accessibility toggle)

Auth flow:
  Browser → /api/v1/auth/login → grpc-gateway :9086 → IAM gRPC :8086
  Response: {access_token, refresh_token} — no {data: …} envelope
  /api/v1/auth/me → roles + permissions populated from JWT claims

Default dev port: :3100 (to avoid StudyBuddy conflicts on :3000).
```

---

## 5. Development Pattern

### 5.1 Code Generation as a Discipline

Thittam uses two code generation tools that enforce correctness at compile time:

```
SQL — sqlc
  Input:  migrations/{service}/*.sql + queries/*.sql
  Output: services/{name}/db/
    db.go           ← DBTX interface
    models.go       ← Go structs (one per table)
    querier.go      ← Repository interface (generated)
    queries.sql.go  ← Implementations

  Effect: SQL queries are type-checked at compile time.
  No string interpolation in SQL is possible by design.

Protobuf — buf
  Input:  proto/{service}/v1/*.proto
  Output: Generated gRPC client + server code

  buf lint                         ← validate proto files
  buf breaking --against .git      ← detect breaking changes
  buf generate                     ← emit Go code

  Effect: Inter-service contracts are validated in CI.
  A breaking change to a proto is caught before merge.
  All 10 protos are now defined (1,659 LOC, 230 messages).
```

### 5.2 The Makefile as Developer Interface

```
make help          → shows all available targets with descriptions
make infra-up      → start Redis, NATS, MinIO (no Postgres)
make db-init       → create thittam role + database
make db-reset      → fresh start (drop → init → migrate → seed)
make migrate-all   → run all migrations in dependency order
make seed          → load XYZ_CBA + XYZ Construction demo seed data
make dev-start     → start all 10 services (IAM first, then core in parallel)
make dev-start-fresh → db-reset && dev-start
make test          → unit tests
make test-race     → with Go race detector
make test-cover    → coverage report (opens in browser)
make lint          → golangci-lint v2
make build         → build all service binaries

Flags:
  --svc-only            skip infra checks
  --with-project-rbac   ADR-014 Phase 2 enforcement
```

`dev-start.sh` orchestrates: IAM (gRPC :8086, REST :9086) first; core services (:9090–:9099) in parallel; grpc-gateway for IAM; Prometheus on :9300. Ports shifted from defaults (commit `82d8338`) to avoid StudyBuddy conflicts.

### 5.3 Testing Strategy

```
Test pyramid

  Unit tests (go test ./... -short)
  ├── Table-driven with t.Parallel()
  ├── Hand-written mock repositories (function field pattern)
  ├── vertical.WithConfig(ctx, fixture) for vertical-aware tests
  ├── Deterministic UUIDs: uuid.MustParse("d1000000-...")
  ├── testify/assert + testify/require
  └── Current: 1,150 test functions across 80 files (was ~306 in v1.1)

  Integration tests (go test ./... -tags=integration)
  ├── Testcontainers (real Postgres, real NATS)
  ├── Transaction rollback per test
  ├── Real migrations applied before each test run
  └── THITTAM_TEST_DSN env var + make db-test-bootstrap

  Contract tests (Pact shape)
  ├── Consumer-driven contracts between services
  └── Scaffolded; not yet exhaustive across 10-service matrix

  E2E tests (Playwright, v1.2 new)
  ├── web/tests/e2e/smoke.spec.ts
  ├── web/tests/e2e/budgets-journey.spec.ts (first business flow)
  └── web/tests/e2e/dashboard.spec.ts

Coverage thresholds (enforced in CI):
  iam + ledger          ≥ 85%
  budget + expense      ≥ 80%
  all others            ≥ 75%
```

### 5.4 The Mock Repository Pattern

Hand-written mocks use the function field pattern — no mock generation library:

```go
// services/budget/service_test.go

type mockBudgetRepo struct {
    CreateBudgetFn  func(ctx context.Context, b Budget) (*Budget, error)
    GetBudgetFn     func(ctx context.Context, id uuid.UUID) (*Budget, error)
    ApproveBudgetFn func(ctx context.Context, id uuid.UUID) error
}

func (m *mockBudgetRepo) CreateBudget(ctx context.Context, b Budget) (*Budget, error) {
    return m.CreateBudgetFn(ctx, b)
}

// In test:
repo := &mockBudgetRepo{
    CreateBudgetFn: func(ctx context.Context, b Budget) (*Budget, error) {
        return &Budget{ID: uuid.MustParse("d1000000-0000-0000-0000-000000000001")}, nil
    },
}
svc := NewService(repo, verticalConfig)
```

### 5.5 Vertical-Aware Testing

Every test that touches vertical-aware business logic must inject a vertical config:

```go
ctx := vertical.WithConfig(context.Background(), vertical.Config{
    ID:   "film-production",
    Name: "Film Production",
    PhaseTypes: []string{
        "pre_production",
        "principal_photography",
        "post_production",
    },
    BudgetCategories: []string{
        "above_the_line",
        "below_the_line",
    },
})
```

This pattern ensures that tests are not accidentally passing because they relied on a default config that would not exist in a real tenant context.

### 5.6 CI Pipeline

```
Push to branch
      │
      ▼
┌──────────────────────────────────────────────────────┐
│  Static analysis (run in parallel)                    │
│                                                       │
│  golangci-lint v2 (action v8)   ← linting            │
│  buf lint                       ← proto validation   │
│  buf breaking                   ← breaking changes   │
│  govulncheck ./...              ← CVE scanning       │
│  gitleaks protect --staged      ← secret detection   │
│  tools/check-doc-drift          ← docs/code parity   │
│  Go pinned to 1.25.9 for stdlib CVE patches          │
└──────────────────────────────────────────────────────┘
      │ all pass
      ▼
┌──────────────────────────────────────────────────────┐
│  Unit tests                                           │
│                                                       │
│  go test ./... -short -race                          │
│  Coverage: iam/ledger ≥ 85%, budget/expense ≥ 80%   │
└──────────────────────────────────────────────────────┘
      │ pass
      ▼
┌──────────────────────────────────────────────────────┐
│  Integration tests (testcontainers-go)                │
│                                                       │
│  go test ./... -tags=integration                     │
│  Real Postgres + NATS in containers                  │
│  Migrations applied before each run                  │
└──────────────────────────────────────────────────────┘
      │ pass
      ▼
┌──────────────────────────────────────────────────────┐
│  E2E tests (Playwright)                               │
│                                                       │
│  web/tests/e2e/* (budgets-journey, smoke, dashboard)  │
└──────────────────────────────────────────────────────┘
      │ pass
      ▼
  PR mergeable (2 approvals required)
  (iam/ledger/security: senior engineer required)
```

### 5.7 Migration Management

Each service has its own migration directory, run in dependency order:

```
migrations/
  iam/          ← run first (tenants and users must exist)
    001_create_tenants.{up,down}.sql
    002_create_users.{up,down}.sql
    003_create_tenant_auth_config.{up,down}.sql
    004_create_platform_users.{up,down}.sql
    005_add_is_demo_to_tenants.{up,down}.sql
    006_create_tenant_settings.{up,down}.sql
    007_create_roles.{up,down}.sql
    008_create_user_roles.{up,down}.sql
    009_create_invitations.{up,down}.sql
    010_add_tenant_address_country.{up,down}.sql   ← v1.2 ADR-015

  ledger/       ← run after iam
  budget/       ← run after ledger
  expense/      ← run after budget
  project/      ← run after iam
  inventory/
  notifications/
  document/
  audit/
    001_create_audit_log.{up,down}.sql   ← REVOKE UPDATE/DELETE pending
  reporting/
  billing/      ← v1.2 new

make migrate-all → runs all services in dependency order
make migrate-down → rolls back all migrations in reverse order
```

Every migration has a `down` file. `make migrate-down` is tested before any migration is merged. This is enforced by convention, not by CI (a gap identified in the critique).

---

## 6. Key Decisions and Their Rationale

### Decision 1 — Go for All Services

Go was chosen over Python (the language used in StudyBuddy) for Thittam's specific requirements:

| Criterion | Go | Python |
|---|---|---|
| gRPC performance | Native, binary, fast | Viable but slower |
| Concurrency model | Goroutines (lightweight, millions) | asyncio (event loop per process) |
| Type safety | Compile-time, no runtime surprises | Runtime type errors |
| Binary deployment | Single binary per service | Runtime + dependencies |
| Financial precision | shopspring/decimal | Decimal stdlib |
| Memory footprint | ~10-50 MB per service | ~150-400 MB per service |

For 10 services running simultaneously in a shared-infra model, Go's memory footprint advantage compounds.

### Decision 2 — gRPC Over REST for Internal Communication; grpc-gateway REST Shadow for Browser Auth

```
REST (rejected for internal)          gRPC (accepted for internal)
┌─────────────────────────┐           ┌─────────────────────────┐
│ Text/JSON encoding       │           │ Binary/protobuf encoding │
│ No contract enforcement  │           │ Schema enforced at build │
│ Manual versioning        │           │ Breaking change detect.  │
│ HTTP/1.1 per request     │           │ HTTP/2 multiplexed       │
│ Swagger for docs         │           │ Proto files = docs       │
└─────────────────────────┘           └─────────────────────────┘

External API (Kong → clients) remains REST/JSON.
Internal (service → service) uses gRPC.
Browser-to-IAM auth uses grpc-gateway REST shadow (v1.2, ADR-013).
```

Why the REST shadow? Browsers speak JSON naturally; bare gRPC requires gRPC-web plus buffer handling plus a manual envelope. The grpc-gateway generated REST surface costs nothing — it's emitted from the same protos — and eliminates friction.

### Decision 3 — NATS JetStream Over Kafka

| Criterion | Kafka | NATS JetStream |
|---|---|---|
| Operational complexity | High (ZooKeeper/KRaft) | Low (single binary) |
| Throughput | Very high (millions/s) | High (millions/s) |
| Delivery guarantee | At-least-once | At-least-once |
| Consumer ACK | Consumer group offset | Per-message ACK |
| Replay | Topic-level | Stream-level |
| Local dev experience | Heavy | Lightweight |

For Thittam's workload (not a high-throughput stream processing system), NATS JetStream provides the delivery guarantees needed at significantly lower operational cost.

### Decision 4 — Vertical Plugin System Over Multiple Codebases

```
Alternative (rejected)          Vertical Plugin (accepted)
┌────────────────────┐          ┌────────────────────────────┐
│ thittam-film       │          │  thittam (single codebase)  │
│ thittam-software   │          │                             │
│ thittam-construction│         │  verticals/                 │
│ thittam-events     │          │    film-production.yaml     │
│                    │          │    software-dev.yaml        │
│ 4× bug fixes       │          │    construction.yaml        │
│ 4× security patches│          │    events-mgmt.yaml         │
│ 4× deployments     │          │                             │
└────────────────────┘          │  pkg/vertical/              │
                                │    loader.go                │
                                │    middleware.go            │
                                │    validator.go             │
                                └────────────────────────────┘
```

A YAML schema violation in a new vertical is caught at startup by the validator.

### Decision 5 — Column-Level Encryption for T1 Data

T1 financial data (payroll rates, tax IDs) is encrypted at the application layer before writing to PostgreSQL:

```
Write path for T1 field:
  service.go receives day_rate (decimal.Decimal)
      │
      ▼
  Encrypt with AES-256-GCM (key from Vault — held in memory)
      │
      ▼
  Store as encrypted blob in repository
      │
      ▼
  PostgreSQL stores ciphertext only

Read path symmetric.
```

A database breach exposes no plaintext T1 data. The encryption key is audited and rotated separately.

### Decision 6 — shadcn/ui + Radix for the Web Tier (ADR-012, v1.2)

The web tier foundation moved to shadcn/ui (copy-in components, not a dep-on library) over Radix primitives in April 2026 (commit `4989191`).

Rationale: shadcn gives theme-ability and accessibility; Radix primitives remove the need to reinvent dialog, dropdown, select, slot; Tailwind v4 is the styling substrate. The result: 60 `.tsx` components, Rule #18–compliant typography (Inter, Merriweather, JetBrains Mono, OpenDyslexic), and consistent keyboard/screen-reader behaviour.

---

## 7. What This Pattern Teaches

### 7.1 Rules as Architecture

The most important pattern in Thittam is the 17-rule coding standards document (now 18 with typography). These rules describe how *any* WeGoFwd2020 service works. They are shared across Thittam and StudyBuddy via `~/coding-standards/`.

The effect: two projects built at the same time, in different languages, by the same team have:
- Identical audit log structure
- Identical caching strategy (L1 → L2 → L3)
- Identical idempotency approach (`ON CONFLICT DO NOTHING`)
- Identical secret management (T1 Vault, T3 env)
- Identical observability endpoints (`/healthz`, `/readyz`, `/metrics`)

Rules written at the organisation level save architectural design time at the project level. When the rules themselves needed refinement (Rule #2's Vault-vs-env contradiction), the fix propagated to both projects consistently.

### 7.2 The ADR as a Contract

ADRs in Thittam are not retrospective documentation — they are the boundary between "we are exploring" and "this decision is made". Once an ADR is written and accepted, implementation follows the decision.

Thirteen ADRs now cover:
- Language choice (ADR-001)
- Database model (ADR-002)
- Internal communication (ADR-003)
- Async messaging (ADR-004)
- API gateway (ADR-005)
- Infrastructure (ADR-006)
- Vertical plugin (ADR-007)
- Multi-tenancy (ADR-008)
- Secret management (ADR-009)
- UI foundation (ADR-012)
- grpc-gateway for browser auth (ADR-013)
- RBAC role model (ADR-014)
- Tenant address + currency (ADR-015)

(ADRs 010 and 011 missing from numbering — fill or renumber.)

Each ADR addresses a decision that is expensive to reverse. This is the correct selection criterion.

### 7.3 The Vertical Plugin as a Market Decision

The vertical plugin system is not just a technical pattern — it is a market decision embedded in code. By making industry configuration a YAML file, Thittam can enter a new industry vertical by:

1. Writing a new YAML file
2. Adding vertical-specific labels and phase types
3. Writing a test suite for the new vertical's config

No code changes are required in the core services. This makes the cost of entering a new vertical very low after the core is built.

```
Market expansion cost with vertical plugin system:

  First vertical (Film Production)   ← High cost (build entire core)
  Second vertical (Construction)     ← Low cost (write YAML + Phase A seed)
  Third vertical (Software Dev)      ← Very low cost (YAML pattern known)
  Fourth vertical (Events Mgmt)      ← Very low cost
  Fifth vertical (Healthcare?)       ← Very low cost (if financial model fits)
```

XYZ Construction's Phase A scaffold is the first validation of this hypothesis: adding a second vertical tenant was a weekend of work, not a month.

### 7.4 Closing the Gap Between Ambition and Execution

The v1.1 critique identified a tension: architectural ambition (9 microservices, gRPC, NATS, Istio, tenant-per-schema) outpaced mid-build execution (4 pending protos, ~306 tests, billing service missing).

v1.2 closes most of that gap:

```
v1.1 state                              v1.2 state
─────────────────────                   ──────────────────────────
4 pending protos                  →     All 10 protos defined
~306 tests                        →     1,150 tests (3.75×)
Billing in docs but not in cmd/   →     services/billing/ + proto
Schema injection risk ❌ Critical  →    Fixed via pkg/tenantdb UUID type
T1 secrets in env vars ❌ Critical →    Fixed via Vault → memory
E2E tests absent                  →     Playwright scaffold + budgets-journey
doc-drift aspirational            →     CI job active in both repos
```

Remaining:
```
No saga for registration          ?     Still open — highest architectural priority
No reporting read model           ?     Still open — highest performance priority
Impersonation lifecycle undef     ?     Still open — highest security hygiene priority
~1,150 tests                      →     Target: 2,000+ before GA (especially ledger)
E2E narrow (1 journey)            →     Target: 5 critical paths before GA
```

The pattern here: identify gaps at mid-build, prioritise them, and systematically close them. v1.2 demonstrates the method works. The remaining open items are scoped, understood, and have documented fix paths.

### 7.5 The Documentation Flywheel

Thittam's documentation is its strongest asset. The 71 markdown files in `thittam_docs`, the 13 ADRs, and the 18 coding rules create a flywheel:

```
Clear rules
    │
    ▼
Consistent implementation
    │
    ▼
Consistent documentation (rules enforced via doc-drift CI)
    │
    ▼
Faster onboarding
    │
    ▼
More consistent implementation
    │
    ▼
(rules refined from experience — Rule #2 secrets tiering, Rule #18 typography)
    │
    └──▶ Clearer rules
```

New team members (and AI coding agents) can derive the project's expectations from written artefacts rather than from tribal knowledge. The CLAUDE.md file in the code repo and the CODING_RULES.md in the shared standards repo make this explicit for AI-assisted development.

The v1.2 typography rule (Rule #18) is a worked example: it started as a design decision in StudyBuddy, got codified into the shared standards repo, and was then applied in Thittam's shadcn/ui adoption. The standards repo is the mechanism by which a pattern proven in one project becomes the default in the next.

---

*This document captures the development pattern as observed through Go source structure (10 services), migrations, CLAUDE.md, CODING_RULES.md (17+1 rules), 13 ADRs, 71 documentation files, Playwright scaffold, and multi-tenant demo seed data. April 2026 (v1.2 refresh).*
