# Thittam — Scoping, Design, Architecture & Development Pattern

**Document type:** Development pattern analysis  
**Scope:** Full lifecycle — from concept to mid-build production system  
**Period:** 2025–2026  
**Author:** WeGoFwd2020 / Claude (Anthropic)  
**Note:** Thittam application code is private. Analysis is based on documentation, migrations, Go source tree, CLAUDE.md, and coding standards.

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

Unlike StudyBuddy (which scoped by user persona), Thittam scoped by industry vertical. The first scoping question was: *which industries are in scope for GA, and what does each one need?*

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
```

The matrix revealed that the difference between verticals is entirely in the **configuration layer** — the services themselves are identical.

### 2.2 Scoping by Service Boundary

The scope of each service was defined by a single question: *what does this service own, and what does it never touch?*

| Service | Owns | Never touches |
|---|---|---|
| IAM | Tenants, users, roles, invitations, auth | Budgets, expenses, documents |
| Budget Planning | Budget versions, line items, approvals | Ledger journal entries |
| Expense Tracking | POs, receipts, petty cash | Budget balances directly |
| General Ledger | Chart of accounts, journal entries, periods | Budget line items |
| Project Management | Projects, phases, crew, schedules | Financial transactions |
| Inventory | Equipment, props, locations, assets | Project schedules |
| Reporting Analytics | Read-only aggregations | Any write operations |
| Notifications | Templates, delivery, log | Business domain data |
| Document | Files, versions, e-signatures | Content of documents |

This scope matrix was defined before implementation and served as the authoritative boundary for where a given feature belonged.

### 2.3 Scoping the Multi-Tenancy Model

The tenancy scope question was answered early and explicitly via ADR-008:

> "Each tenant gets schema `tenant_<uuid>` in PostgreSQL. Tenant context is set via `X-Tenant-ID` header on every request. The `BeforeAcquire` hook on the pgx pool ensures every connection is scoped to the correct tenant schema."

Three options were evaluated:

| Option | Description | Outcome |
|---|---|---|
| Separate instance per tenant | Strongest isolation, highest cost | Offered as enterprise tier only |
| Shared schema, row-level filtering | Application-layer isolation | Rejected |
| Tenant-per-schema | Database-level isolation | Accepted |

The tenant-per-schema decision locked in a set of operational constraints that shaped every subsequent decision: migrations must run across N schemas, connection pool routing must be tenant-aware, and reporting queries cannot join across schemas.

---

## 3. Design Pattern

### 3.1 Rules Before Code

The most distinctive aspect of Thittam's design pattern is that 17 non-negotiable coding rules were written and locked before significant implementation began. These rules are not style guidelines — they are constraints that cannot be violated:

```
Rule hierarchy

  Non-negotiable (17 rules in CODING_RULES.md)
  │
  ├── Money is never a float (Rule #1)
  ├── Secrets from environment only (Rule #2)
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

  Language-specific (go-conventions.md)
  │
  ├── Service file layout (models/errors/repository/service/handler)
  ├── Error handling (sentinel errors, wrapping at boundaries)
  ├── Monetary types (shopspring/decimal only)
  ├── SQL (sqlc, parameterised, never interpolated)
  └── Testing (table-driven, t.Parallel(), hand-written mocks)
```

Writing the rules first had a specific effect: every design decision was evaluated against 17 explicit constraints before it was accepted. This reduced the cost of design review because the criteria were already written.

### 3.2 The ADR Record

Nine Architecture Decision Records were written before the implementation reached mid-build:

| ADR | Decision | Rationale |
|---|---|---|
| ADR-001 | Go 1.22+ for all services | Type safety, performance, standard library, gRPC support |
| ADR-002 | PostgreSQL with tenant-per-schema | Strongest isolation, compliance-ready, supports complex queries |
| ADR-003 | gRPC for internal service communication | Type-safe contracts, binary protocol, bi-directional streaming |
| ADR-004 | NATS JetStream for async messaging | At-least-once delivery, consumer ACK, replay, persistence |
| ADR-005 | Kong API Gateway at edge | Rate limiting, JWT validation, routing without custom middleware |
| ADR-006 | Docker + Kubernetes | Container portability, HPA for variable load |
| ADR-007 | YAML-driven vertical plugin system | Industry-agnostic without multiple codebases |
| ADR-008 | Tenant-per-schema multi-tenancy | DB-level isolation, compliance provability |
| ADR-009 | Vault for T1 secret management | Audit trail, rotation, never in environment variables |

Each ADR follows the same structure: Context → Decision → Rationale with trade-off table → Consequences. This format forces the team to acknowledge trade-offs rather than treat decisions as obviously correct.

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
  Vertical-aware service (e.g. budget-planning)
  ├── Reads tenant's vertical config from context
  ├── Renders labels from config (not hardcoded)
  ├── Validates phase_type against config's phase_types
  └── Applies workflow rules from config
```

The vertical config flows through every vertical-aware service via a gRPC interceptor that injects it into the request context. Services never hardcode industry-specific behaviour.

### 3.4 Data Classification Design

The security design was anchored by a data classification tier system:

```
T1 — Highly Sensitive (Vault only, AES-256-GCM encrypted at rest)
  day_rate (payroll data)
  vendor_gstin (tax IDs)
  JWT signing keys
  Database passwords
  API keys

T2 — Confidential (encrypted in transit, access-controlled)
  Budget line items
  Expense amounts
  Vendor names
  Salary information

T3 — Internal (standard access controls)
  Project names and descriptions
  Phase schedules
  Crew assignments

T4 — Public (no restrictions)
  Vertical configuration labels
  Phase type definitions
  Public-facing pricing
```

The classification directly drove implementation: T1 data is encrypted at the column level before writing to PostgreSQL. T2 data uses standard field-level access control. The classification is referenced in code comments wherever T1 or T2 data is touched.

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
│  Service Mesh (Istio)                                              │
│  mTLS for all east-west traffic                                   │
│  Circuit breakers · Retries · Canary deployments                  │
│                                                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │   IAM    │  │ Project  │  │  Budget  │  │ Expense  │         │
│  │  :8086   │  │  Mgmt    │  │ Planning │  │Tracking  │         │
│  │          │  │  :8080   │  │  :8081   │  │  :8082   │         │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘         │
│       │              │              │              │               │
│  ┌────▼─────┐  ┌────▼─────┐  ┌────▼─────┐  ┌────▼─────┐         │
│  │  General │  │Inventory │  │Reporting │  │Notifica- │         │
│  │  Ledger  │  │  Mgmt    │  │Analytics │  │  tions   │         │
│  │  :8083   │  │  :8084   │  │  :8085   │  │  :8087   │         │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘         │
│                                              ┌──────────┐         │
│                                              │ Document │         │
│                                              │  :8088   │         │
│                                              └──────────┘         │
└───────────────────────────────────────────────────────────────────┘
                         │  gRPC (sync internal)
                         │  NATS JetStream (async internal)
```

### 4.2 Service Communication Model

Two communication patterns coexist, each chosen for its guarantees:

```
Synchronous (gRPC)
  Used when: Caller needs an immediate response
  Examples:
    ├── IAM → any service (JWT validation)
    ├── Budget → Ledger (expense approval → journal entry)
    └── Reporting → all services (data aggregation)

  Properties:
    Type-safe contracts (protobuf)
    Binary protocol (3-5× smaller than JSON)
    Client-side load balancing via Istio DestinationRule
    Circuit breakers via Istio VirtualService

Asynchronous (NATS JetStream)
  Used when: Caller does not need to wait
  Examples:
    ├── Expense approved → Notifications (email alert)
    ├── Budget threshold hit → Notifications (warning)
    ├── Ledger posted → Reporting (materialise report)
    └── Registration complete → all services (seed data)

  Properties:
    At-least-once delivery (JetStream ACK)
    Consumer-level acknowledgment (not message-level)
    Replay capability (reprocess after downstream failure)
    Dead-letter stream (after N retries)
    Event deduplication via event_id (Rule #5)
```

### 4.3 Multi-Tenant Data Model

```
PostgreSQL Server
│
├── public schema (shared tables: tenants, platform config)
│
├── tenant_<uuid-A> schema (Tenant A's isolated data)
│   ├── projects
│   ├── budgets
│   ├── expenses
│   ├── journal_entries
│   ├── users
│   └── (all domain tables)
│
├── tenant_<uuid-B> schema (Tenant B's isolated data)
│   ├── projects
│   ├── ... (identical table set)
│   └── ...
│
└── tenant_<uuid-N> schema

Connection pool BeforeAcquire hook:
  SET search_path = tenant_<uuid>, public
  (validated as well-formed UUID before interpolation)
```

Migration pattern — every schema migration runs across all tenant schemas:

```
migrate-all target
      │
      ▼
For each tenant schema in public.tenants:
  ├── SET search_path = tenant_<uuid>
  ├── Run migration SQL
  └── Log result (success/failure per schema)

Failure handling:
  ├── Failed schemas logged with tenant_id + migration number
  ├── Migration does NOT abort on first failure (partial progress is recoverable)
  └── Alert sent to operations team
```

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
        [Known gap: no saga pattern — partial failure in steps 2-8
         has no compensating transaction strategy]
```

The registration pipeline is one of the known architectural risks: it spans multiple services and schemas without a formal saga pattern. A failure at step 5 leaves a created schema with no users, and a failure at step 6 leaves a ledger-less tenant. The mitigating factor is that the `pkg/registration/` package tracks pipeline state, but compensating transactions are not yet documented.

### 4.5 Observability Model

Every service implements Rule #13 identically:

```
Service startup
      │
      ├── /healthz  → liveness probe (is the process alive?)
      ├── /readyz   → readiness probe (are dependencies connected?)
      └── /metrics  → Prometheus metrics endpoint

gRPC interceptor chain (every service):
  ├── pkg/observability/interceptor.go
  │   ├── request_duration_seconds (histogram)
  │   ├── request_total (counter, by status)
  │   └── correlation_id injected into every log entry
  │
  ├── pkg/audit/interceptor.go
  │   ├── Captures actor_id, action, target_type, target_id
  │   ├── Captures old_state + new_state for mutations
  │   └── Writes append-only audit log (never UPDATE or DELETE)
  │
  └── pkg/auth/resolver.go
      └── Validates JWT, extracts tenant_id + user claims

Metrics flow:
  Service /metrics → Prometheus scrape → Grafana dashboard
  Alert rules: request_duration_percentile > SLA → PagerDuty
```

### 4.6 The Audit Log Design

Rule #7 mandates audit logging for all authentication events, financial operations, administrative actions, and impersonation. The audit log schema captures the minimum required for legal defensibility:

```
audit_log table (append-only, per-tenant schema)

  actor_id       UUID     who performed the action
  action         TEXT     what was done (CREATE_BUDGET, APPROVE_EXPENSE, ...)
  target_type    TEXT     what entity type (budget, expense, journal_entry, ...)
  target_id      UUID     which specific entity
  tenant_id      UUID     which tenant (for cross-schema audit queries)
  timestamp      TIMESTAMPTZ
  old_state      JSONB    serialised state before mutation
  new_state      JSONB    serialised state after mutation
  ip_address     INET     originating IP
  correlation_id TEXT     links to the request that generated this entry

Constraints:
  No UPDATE on audit_log
  No DELETE on audit_log
  Partition by month for query performance at scale
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
  pkg/tenant/      ← Tenant context helpers
  pkg/vertical/    ← Vertical config loader + gRPC middleware
  pkg/server/      ← gRPC server builder (shared setup)
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
```

### 5.2 The Makefile as Developer Interface

The Makefile is the single entry point for all development operations. It serves as the project's executable documentation:

```
make help          → shows all available targets with descriptions
make infra-up      → start Redis, NATS, MinIO (no Postgres)
make db-init       → create thittam role + database
make db-reset      → fresh start (drop → init → migrate → seed)
make migrate-all   → run all migrations in dependency order
make seed          → load XYZ_CBA demo seed data
make run-all       → start all 9 services via tmuxinator
make test          → unit tests
make test-race     → with Go race detector
make test-cover    → coverage report (opens in browser)
make lint          → golangci-lint
make build         → build all service binaries
```

The Makefile explicitly separates infrastructure concerns (Redis, NATS, MinIO) from the database, and both from the application. This allows running just infrastructure for development, or just the database for migration testing.

### 5.3 Testing Strategy

```
Test pyramid

  Unit tests (go test ./... -short)
  ├── Table-driven with t.Parallel()
  ├── Hand-written mock repositories (function field pattern)
  ├── vertical.WithConfig(ctx, fixture) for vertical-aware tests
  ├── Deterministic UUIDs: uuid.MustParse("d1000000-...")
  └── testify/assert + testify/require

  Integration tests (go test ./... -tags=integration)
  ├── testcontainers-go (real Postgres, real NATS)
  ├── Transaction rollback per test (no state pollution)
  └── Real migrations applied before each test run

  Contract tests (Pact)
  ├── Consumer-driven contracts between services
  ├── Budget → Ledger (expense approval triggers journal entry)
  └── Expense → Notifications (approval triggers email)

  E2E tests (Playwright)
  ├── Run nightly
  ├── Cover: registration → project create → budget → expense → report
  └── [Gap: should run on every PR for critical paths]

Coverage thresholds (enforced in CI):
  iam + general-ledger  ≥ 85%
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

This pattern gives the test full control over each function's behaviour without any framework. The mock is visible, readable, and debuggable.

### 5.5 Vertical-Aware Testing

Every test that touches vertical-aware business logic must inject a vertical config:

```go
// vertical.WithConfig injects the config into the test context
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
│  golangci-lint run ./...      ← linting              │
│  buf lint                     ← proto validation     │
│  buf breaking                 ← breaking change check│
│  govulncheck ./...            ← CVE scanning         │
│  gitleaks protect --staged    ← secret detection     │
│  bandit (if any Python)       ← SAST                │
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
│  Contract tests (Pact)                                │
│                                                       │
│  pact-provider verify        ← service consumers     │
│  pact-broker publish         ← update contract store │
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

  ledger/       ← run after iam
    001_create_accounts.{up,down}.sql
    002_create_accounting_periods.{up,down}.sql
    003_create_journal_entries.{up,down}.sql
    004_create_journal_lines.{up,down}.sql

  budget/       ← run after ledger
    001_create_tables.{up,down}.sql

  expense/      ← run after budget
    001_create_tables.{up,down}.sql

  project/      ← run after iam
  inventory/
  notifications/
    001_create_notification_templates.{up,down}.sql
    002_create_notification_log.{up,down}.sql
  document/
    001_create_folders.{up,down}.sql
    002_create_documents.{up,down}.sql
    003_create_document_versions.{up,down}.sql
  audit/
    001_create_audit_log.{up,down}.sql
  reporting/
    001_create_tables.{up,sql}
    002_create_dashboard_views.{up,down}.sql

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

For 9 services running simultaneously in a shared-infra model, Go's memory footprint advantage compounds.

### Decision 2 — gRPC Over REST for Internal Communication

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
```

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

The alternative to the vertical plugin system was maintaining separate codebases per industry:

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

A YAML schema violation in a new vertical is caught at startup, not at runtime in production. This is enforced by the validator.

### Decision 5 — Column-Level Encryption for T1 Data

T1 financial data (payroll rates, tax IDs) is encrypted at the application layer before writing to PostgreSQL:

```
Write path for T1 field:
  service.go receives day_rate (decimal.Decimal)
      │
      ▼
  Encrypt with AES-256-GCM (key from Vault)
      │
      ▼
  Store as encrypted blob in repository
      │
      ▼
  PostgreSQL stores ciphertext only

Read path for T1 field:
  PostgreSQL returns ciphertext
      │
      ▼
  Decrypt with AES-256-GCM (key from Vault)
      │
      ▼
  service.go receives plaintext decimal.Decimal
```

This means a database breach exposes no plaintext T1 data. The encryption key in Vault is separately audited and rotated.

---

## 7. What This Pattern Teaches

### 7.1 Rules as Architecture

The most important pattern in Thittam is the 17-rule coding standards document. These rules do not describe how Thittam works — they describe how *any* WeGoFwd2020 service works. They are shared across Thittam and StudyBuddy via `~/coding-standards/`.

The effect is that two projects built at the same time, in different languages, by the same team have:
- Identical audit log structure
- Identical caching strategy (L1 → L2 → L3)
- Identical idempotency approach (`ON CONFLICT DO NOTHING`)
- Identical secret management (environment variables / Vault)
- Identical observability endpoints (`/healthz`, `/readyz`, `/metrics`)

Rules written at the organisation level save architectural design time at the project level.

### 7.2 The ADR as a Contract

ADRs in Thittam are not retrospective documentation — they are the boundary between "we are exploring" and "this decision is made". Once an ADR is written and accepted, implementation follows the decision. If the decision turns out to be wrong, a new ADR supersedes it.

The nine ADRs cover:
- Language choice (ADR-001) — affects hiring, tooling, ecosystem
- Database model (ADR-002) — affects scalability ceiling
- Internal communication (ADR-003) — affects developer experience
- Async messaging (ADR-004) — affects operational complexity
- API gateway (ADR-005) — affects security perimeter
- Infrastructure (ADR-006) — affects deployment model
- Vertical plugin (ADR-007) — affects extensibility
- Multi-tenancy (ADR-008) — affects compliance story
- Secret management (ADR-009) — affects security posture

Each ADR addresses a decision that, once made, is expensive to reverse. This is the correct selection criterion for what deserves an ADR.

### 7.3 The Vertical Plugin as a Market Decision

The vertical plugin system is not just a technical pattern — it is a market decision embedded in code. By making industry configuration a YAML file, Thittam can enter a new industry vertical by:

1. Writing a new YAML file
2. Adding vertical-specific labels and phase types
3. Writing a test suite for the new vertical's config

No code changes are required in the core services. This makes the cost of entering a new vertical very low after the core is built.

```
Market expansion cost with vertical plugin system:

  First vertical (Film Production)   ← High cost (build entire core)
  Second vertical (Construction)     ← Low cost (write YAML + test)
  Third vertical (Software Dev)      ← Very low cost (YAML pattern known)
  Fourth vertical (Events Mgmt)      ← Very low cost
  Fifth vertical (Healthcare?)       ← Very low cost (if financial model fits)
```

### 7.4 The Hidden Cost of Microservices at Mid-Build

The most instructive tension in Thittam is the gap between the architectural ambition (9 microservices, gRPC, NATS, Istio) and the mid-build reality (4 proto definitions still pending, ~306 tests for a financial platform, billing service not yet in `cmd/`).

The pattern here is not wrong — it is ahead of its execution capacity. The identification of this gap at mid-build, rather than at launch, is valuable. The resolution is prioritisation:

```
Current state (mid-build)                 Target state (pre-launch)
─────────────────────────                 ──────────────────────────
4 pending protos                    →     All 9 protos defined
~306 tests                          →     800+ tests
No saga for registration            →     Saga pattern documented
Billing in docs but not in cmd/     →     Billing service implemented
E2E nightly only                    →     Critical path E2E on every PR
No NATS dead-letter documented      →     DLQ strategy for financial events
```

The microservices boundary decisions (which service owns which domain) are correct. The physical separation can be phased: start as a modular monolith with service-package boundaries, then extract to separate binaries when load or team size justifies it. The gRPC contracts are already defined — the extraction would be mechanical.

### 7.5 The Documentation Flywheel

Thittam's documentation is its strongest asset. The 41+ markdown files in `thittam_docs`, the 9 ADRs, and the 17 coding rules create a flywheel:

```
Clear rules
    │
    ▼
Consistent implementation
    │
    ▼
Consistent documentation (rules enforced)
    │
    ▼
Faster onboarding
    │
    ▼
More consistent implementation
    │
    ▼
(rules refined from experience)
    │
    └──▶ Clearer rules
```

New team members (and AI coding agents) can derive the project's expectations from written artefacts rather than from tribal knowledge. The CLAUDE.md file in the code repo and the CODING_RULES.md in the shared standards repo make this explicit for AI-assisted development.

---

*This document captures the development pattern as observed through Go source structure, migrations, CLAUDE.md, CODING_RULES.md, ADR records, and Thittam documentation as of April 2026.*
