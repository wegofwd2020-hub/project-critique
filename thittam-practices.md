# Thittam — Good Practices, Bad Practices & How to Improve

**Document type:** Engineering practices analysis  
**Scope:** Go microservices, gRPC, NATS JetStream, PostgreSQL, Istio, Kong, Vertical Plugin System  
**Period:** April 2026  
**Rating key:** ✅ Good practice · ⚠️ Bad practice · ❌ Critical issue · 🔧 How to improve

---

## Table of Contents

1. [Architecture Practices](#1-architecture-practices)
2. [Security Practices](#2-security-practices)
3. [Financial Data Practices](#3-financial-data-practices)
4. [Code Quality Practices](#4-code-quality-practices)
5. [Testing Practices](#5-testing-practices)
6. [Observability Practices](#6-observability-practices)
7. [Documentation Practices](#7-documentation-practices)
8. [Summary Scorecard](#8-summary-scorecard)

---

## 1. Architecture Practices

### ✅ Good — Vertical Plugin System Makes the Platform Industry-Agnostic

The vertical plugin system is the most valuable design decision in Thittam. It encodes the insight that four industries share the same financial model but speak different vocabularies.

```
GOOD: Configuration-driven industry support

  Without vertical plugins (rejected approach):
  ┌──────────────────────────────────────────────────────────┐
  │  thittam-film/        4 separate codebases               │
  │  thittam-software/    4× security patches                │
  │  thittam-construction 4× deployments                     │
  │  thittam-events/      4× bug fixes to sync               │
  │                       divergence guaranteed within 6mo   │
  └──────────────────────────────────────────────────────────┘

  With vertical plugins (current approach):
  ┌──────────────────────────────────────────────────────────┐
  │  thittam (one codebase)                                  │
  │                                                           │
  │  verticals/film-production.yaml    ← vocabulary + rules  │
  │  verticals/software-dev.yaml       ← vocabulary + rules  │
  │  verticals/construction.yaml       ← vocabulary + rules  │
  │  verticals/events-mgmt.yaml        ← vocabulary + rules  │
  │                                                           │
  │  Adding vertical 5 (Healthcare):                         │
  │  ├── Write verticals/healthcare.yaml  (~50 lines)        │
  │  ├── Add test suite for new YAML      (~1 day)           │
  │  └── No core service changes                             │
  └──────────────────────────────────────────────────────────┘

  The vertical config flows through every vertical-aware service
  via a gRPC interceptor — services never hardcode industry terms:

  service receives: budget.CreateLineItem(ctx, item)
       │
       ▼
  vertical.FromContext(ctx).BudgetCategories  ← from YAML, not code
       │
       ▼
  validation against config's allowed categories
       │
       ▼
  UI label from config: "Above the Line" (film) or "Labor" (construction)
```

---

### ✅ Good — Service Structure Is Identical Across All 9 Services

```
GOOD: Consistent 6-file layout per service (Rule #14)

  services/budget/          services/expense/         services/iam/
  ├── models.go             ├── models.go             ├── models.go
  ├── errors.go             ├── errors.go             ├── errors.go
  ├── repository.go         ├── repository.go         ├── repository.go
  ├── service.go            ├── service.go            ├── service.go
  ├── service_test.go       ├── service_test.go       ├── service_test.go
  └── handler.go            └── handler.go            └── handler.go

  A developer who has worked in budget can navigate expense on day one.
  Grep for any pattern → it appears in the same file in every service.
  "Where is error handling?" → errors.go in every service.
  "Where is the DB interface?" → repository.go in every service.

  Dependency direction enforced by structure:
  handler.go → service.go → repository.go (interface)
                                  ↑
                             DB implementation
                          (injected at startup)
```

---

### ✅ Good — gRPC for Internal, REST for External

```
GOOD: The right protocol at each boundary

  External boundary (client → Kong → services):
  ┌──────────────────────────────────────────────────────────┐
  │  REST/JSON                                               │
  │  Reason: clients are browsers and mobile apps            │
  │  Kong handles: auth, rate-limit, routing                 │
  │  Human-readable, debuggable with curl                    │
  └──────────────────────────────────────────────────────────┘

  Internal boundary (service → service):
  ┌──────────────────────────────────────────────────────────┐
  │  gRPC / protobuf                                         │
  │  Reason: type-safe contracts, binary efficiency          │
  │                                                           │
  │  JSON REST comparison:                                   │
  │    {"amount": 15000.00, "currency": "USD", ...}          │
  │    → 35 bytes + parsing overhead                         │
  │                                                           │
  │  Protobuf comparison:                                    │
  │    amount: 15000.00 currency: USD                        │
  │    → ~8 bytes binary, generated parser                   │
  │                                                           │
  │  At 10,000 inter-service calls/second:                  │
  │    JSON:    350 KB/s on the wire + CPU parse cost       │
  │    Protobuf: ~80 KB/s + compiled deserialiser           │
  │                                                           │
  │  Breaking change detection (buf breaking):               │
  │    Rename a proto field → CI fails before merge          │
  │    Remove a required field → CI fails before merge       │
  └──────────────────────────────────────────────────────────┘
```

---

### ✅ Good — Code Generation Enforces Correctness at Compile Time

```
GOOD: sqlc makes SQL type-safe; buf makes protos enforceable

  sqlc (SQL → Go):
  ┌──────────────────────────────────────────────────────────┐
  │  Input: migrations/budget/001_create_tables.up.sql       │
  │         queries/budget/get_budget.sql                    │
  │                                                           │
  │  Output: services/budget/db/                             │
  │    queries.sql.go  ← type-safe functions                 │
  │    models.go       ← Go structs matching schema          │
  │                                                           │
  │  Effect: The following is a compile error, not a runtime │
  │  error:                                                   │
  │    budget.Amount = "not a decimal"  ← type mismatch     │
  │                                                           │
  │  SQL injection: impossible (queries are parameterised    │
  │  by design — sqlc does not support interpolation)        │
  └──────────────────────────────────────────────────────────┘

  buf (protobuf → Go):
  ┌──────────────────────────────────────────────────────────┐
  │  buf lint       → validates proto style rules            │
  │  buf breaking   → detects breaking changes vs main       │
  │  buf generate   → emits type-safe gRPC client/server     │
  │                                                           │
  │  Effect: If expense-tracking renames an RPC method that  │
  │  budget-planning calls, `buf breaking` fails in CI       │
  │  before any code is merged.                              │
  └──────────────────────────────────────────────────────────┘
```

---

### ⚠️ Bad — Nine Microservices at Mid-Build Is Ahead of Execution Capacity

```
BAD: Service count exceeds current team throughput

  Current state:
  ┌──────────────────────────────────────────────────────────┐
  │  9 services × (4 pending protos + tests + docs) =        │
  │  a very large surface area to stabilise before launch    │
  │                                                           │
  │  Status:                                                  │
  │  iam              ✅ proto defined    ← critical service  │
  │  general-ledger   ✅ proto defined    ← critical service  │
  │  budget-planning  ✅ proto defined                        │
  │  expense-tracking ✅ proto defined                        │
  │  project-mgmt     ✅ proto defined                        │
  │  inventory-mgmt   ✅ proto defined                        │
  │  reporting        ⚠️ proto pending   ← blocks cross-svc  │
  │  notifications    ⚠️ proto pending   ← no typed contract │
  │  document         ⚠️ proto pending   ← no typed contract │
  │                                                           │
  │  4 pending protos = 4 services with no formal contract   │
  │  = no Pact contract tests = undetected breaking changes  │
  └──────────────────────────────────────────────────────────┘
```

#### 🔧 How to Improve

```
GOOD: Define pending protos first; add a service-addition gate

  Priority order for pending protos:

  1. notifications.proto (IMMEDIATELY)
     Required by: registration pipeline (step 9)
     Required by: expense approval (email alert)
     Without it: no typed contract for the most-called async service

  2. document.proto (NEXT)
     Required by: project-management (attach files to productions)
     Required by: expense-tracking (receipts, POs)

  3. reporting.proto (BEFORE GA)
     Required by: dashboard consumers
     Can be stubbed with REST endpoint in the interim

  Structural gate (add to Makefile):
  ┌──────────────────────────────────────────────────────────┐
  │  .PHONY: check-protos                                    │
  │  check-protos:                                           │
  │      buf lint                                            │
  │      buf build  ← fails if any .proto is syntactically  │
  │                   incomplete or references undefined types│
  │                                                           │
  │  # CI pipeline adds check-protos before unit tests      │
  └──────────────────────────────────────────────────────────┘

  Alternative: keep notifications + document as REST-only
  until the gRPC contract is fully designed. A REST endpoint
  with a JSON schema is better than a pending proto.
```

---

### ⚠️ Bad — Registration Pipeline Has No Saga Pattern

```
BAD: Distributed transaction with no compensating logic

  9-step registration pipeline:
  ┌──────────────────────────────────────────────────────────┐
  │  Step 1: Validate tenant data              ← reversible  │
  │  Step 2: INSERT INTO public.tenants        ← written     │
  │  Step 3: CREATE SCHEMA tenant_<uuid>       ← written     │
  │  Step 4: Run IAM migrations                ← written     │
  │  Step 5: Seed IAM (admin user)             ← written     │
  │  Step 6: Seed Ledger (chart of accounts)   ← written     │
  │  Step 7: Bind vertical config              ← written     │
  │  Step 8: Emit registration.complete (NATS) ← written     │
  │  Step 9: Send welcome notification         ← async       │
  └──────────────────────────────────────────────────────────┘

  Failure scenario (step 6 panics):
  ┌──────────────────────────────────────────────────────────┐
  │  Steps 2-5 already committed to the DB                   │
  │  Step 6 fails mid-way                                    │
  │                                                           │
  │  State left behind:                                      │
  │  ├── tenant row in public.tenants (orphan)               │
  │  ├── schema tenant_<uuid> exists (orphan)               │
  │  ├── IAM tables populated with admin user               │
  │  ├── Ledger half-seeded or empty                         │
  │  └── No vertical config → every service errors          │
  │                                                           │
  │  Retrying registration for the same email:               │
  │  ├── Step 2 fails with UNIQUE violation (tenant exists)  │
  │  └── Tenant is permanently stuck in broken state         │
  └──────────────────────────────────────────────────────────┘
```

#### 🔧 How to Improve

```
GOOD: Explicit saga with compensating transactions

  pkg/registration/pipeline.go refactor:

  ┌─────────────────────────────────────────────────────────┐
  │  type Step struct {                                      │
  │      Name       string                                   │
  │      Execute    func(ctx context.Context) error          │
  │      Compensate func(ctx context.Context) error          │
  │  }                                                       │
  │                                                          │
  │  steps := []Step{                                        │
  │      {                                                   │
  │          Name: "create_tenant_record",                   │
  │          Execute: func(ctx context.Context) error {      │
  │              return db.InsertTenant(ctx, tenant)         │
  │          },                                              │
  │          Compensate: func(ctx context.Context) error {   │
  │              return db.DeleteTenant(ctx, tenant.ID)      │
  │          },                                              │
  │      },                                                  │
  │      {                                                   │
  │          Name: "create_schema",                          │
  │          Execute: func(ctx context.Context) error {      │
  │              return db.CreateTenantSchema(ctx, tenant.ID)│
  │          },                                              │
  │          Compensate: func(ctx context.Context) error {   │
  │              return db.DropTenantSchema(ctx, tenant.ID)  │
  │          },                                              │
  │      },                                                  │
  │      // ... remaining steps                              │
  │  }                                                       │
  └─────────────────────────────────────────────────────────┘

  Execution with rollback:
  ┌─────────────────────────────────────────────────────────┐
  │  completed := []Step{}                                   │
  │                                                          │
  │  for _, step := range steps {                            │
  │      if err := step.Execute(ctx); err != nil {          │
  │          // Compensate in reverse order                  │
  │          for i := len(completed) - 1; i >= 0; i-- {    │
  │              _ = completed[i].Compensate(ctx)            │
  │          }                                               │
  │          return fmt.Errorf("pipeline failed at %s: %w", │
  │                            step.Name, err)              │
  │      }                                                   │
  │      completed = append(completed, step)                │
  │  }                                                       │
  └─────────────────────────────────────────────────────────┘

  Effect:
  Step 6 fails → steps 5, 4, 3, 2 compensated in order
  → DB is clean → retry is safe
  → No orphan tenants or schemas
```

---

### ⚠️ Bad — Reporting-Analytics Has No Defined Read Model Strategy

```
BAD: Cross-service aggregation is architecturally unresolved

  The problem:
  ┌──────────────────────────────────────────────────────────┐
  │  Reporting service needs data from all 8 other services  │
  │                                                           │
  │  Option A: Live gRPC fan-out (current implicit approach) │
  │                                                           │
  │  Report request → reporting-service                      │
  │    → GetBudgets() to budget-planning                     │
  │    → GetExpenses() to expense-tracking                   │
  │    → GetJournalEntries() to general-ledger               │
  │    → GetProjects() to project-management                 │
  │    → ...8 serial or parallel gRPC calls                  │
  │                                                           │
  │  Problems:                                               │
  │    ├── Tail latency: slowest service = slow report       │
  │    ├── All 8 services must be healthy for any report     │
  │    ├── No caching without complex invalidation logic     │
  │    └── Reporting load stresses transactional services    │
  │                                                           │
  │  Option B: Shared DB (anti-pattern, not used — good)     │
  │    reporting reads from budget's DB directly             │
  │    Problems: tight coupling, breaks service isolation    │
  └──────────────────────────────────────────────────────────┘
```

#### 🔧 How to Improve

```
GOOD: Event-sourced read model via NATS JetStream

  Architecture:

  ┌──────────────────────────────────────────────────────────┐
  │  Every domain service publishes events on state change:  │
  │                                                           │
  │  budget-planning  → "budget.approved"                    │
  │  expense-tracking → "expense.submitted"                  │
  │  general-ledger   → "journal.posted"                     │
  │  project-mgmt     → "project.phase.completed"            │
  └──────────────────────────────────────────────────────────┘
                 │ NATS JetStream
                 ▼
  ┌──────────────────────────────────────────────────────────┐
  │  reporting-analytics subscribes to all events            │
  │  → materialises its own read model (PostgreSQL views)    │
  │                                                           │
  │  migrations/reporting/002_create_dashboard_views.up.sql  │
  │  (already exists! — just needs event consumers wired in) │
  │                                                           │
  │  Report request hits pre-materialised views:             │
  │    SELECT * FROM reporting.budget_summary WHERE ...       │
  │    → single DB query, no cross-service calls at query time│
  │    → <50ms for any report                                │
  └──────────────────────────────────────────────────────────┘

  Event envelope (standard across all services):
  ┌──────────────────────────────────────────────────────────┐
  │  type DomainEvent struct {                               │
  │      EventID    uuid.UUID  `json:"event_id"`             │
  │      EventType  string     `json:"event_type"`           │
  │      TenantID   uuid.UUID  `json:"tenant_id"`            │
  │      OccurredAt time.Time  `json:"occurred_at"`          │
  │      Payload    []byte     `json:"payload"`              │
  │  }                                                        │
  └──────────────────────────────────────────────────────────┘

  Deduplication: ON CONFLICT (event_id) DO NOTHING (Rule #5)
  Replay: NATS JetStream replay → rebuild any view from scratch
```

---

## 2. Security Practices

### ✅ Good — Tenant-Per-Schema Provides Database-Level Isolation

```
GOOD: Cross-tenant data access is impossible, not just unlikely

  Standard row-level filtering (weaker approach):
  ┌──────────────────────────────────────────────────────────┐
  │  SELECT * FROM budgets WHERE tenant_id = $1              │
  │  ↑ Developer forgets this → returns all tenants' data   │
  │  ↑ Relies on 100% correct application code              │
  └──────────────────────────────────────────────────────────┘

  Tenant-per-schema (Thittam's approach):
  ┌──────────────────────────────────────────────────────────┐
  │  BeforeAcquire hook:                                      │
  │    SET search_path = tenant_<uuid>, public               │
  │                                                           │
  │  SELECT * FROM budgets                                   │
  │  ↑ No WHERE needed → only this schema's budgets exist   │
  │  ↑ Cross-tenant access requires wrong search_path        │
  │  ↑ Kong validates X-Tenant-ID header before any service  │
  │    sees the request                                       │
  │                                                           │
  │  Security audit statement:                               │
  │  "Physical schema separation means cross-tenant query    │
  │   is architecturally impossible from within a correctly  │
  │   set connection context."                               │
  └──────────────────────────────────────────────────────────┘
```

---

### ✅ Good — Istio mTLS for All East-West Traffic

```
GOOD: Service-to-service calls are authenticated and encrypted

  Without mTLS:
  ┌──────────────────────────────────────────────────────────┐
  │  budget-planning ──HTTP──▶ general-ledger                │
  │  If budget-planning is compromised:                      │
  │    → attacker can call any service from inside the mesh  │
  │    → general-ledger accepts the call (no auth check)     │
  └──────────────────────────────────────────────────────────┘

  With Istio mTLS (current):
  ┌──────────────────────────────────────────────────────────┐
  │  budget-planning ──mTLS──▶ general-ledger                │
  │  If budget-planning is compromised:                      │
  │    → attacker has budget-planning's certificate          │
  │    → general-ledger sees: caller = budget-planning       │
  │    → AuthorizationPolicy: allow only expected callers    │
  │    → A rogue service calling general-ledger is rejected  │
  └──────────────────────────────────────────────────────────┘

  Enforcement:
  PeerAuthentication: STRICT mode (no plaintext allowed)
  AuthorizationPolicy: per-service allowlist
```

---

### ✅ Good — Append-Only Audit Logs Are Legally Defensible

```
GOOD: Financial audit trail cannot be tampered with

  Audit log table design:
  ┌──────────────────────────────────────────────────────────┐
  │  CREATE TABLE audit_log (                                │
  │    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),│
  │    actor_id       UUID NOT NULL,                         │
  │    action         TEXT NOT NULL,                         │
  │    target_type    TEXT NOT NULL,                         │
  │    target_id      UUID NOT NULL,                         │
  │    tenant_id      UUID NOT NULL,                         │
  │    old_state      JSONB,                                 │
  │    new_state      JSONB,                                 │
  │    ip_address     INET,                                  │
  │    correlation_id TEXT,                                  │
  │    occurred_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()     │
  │  );                                                       │
  │                                                           │
  │  -- These constraints make the log append-only:          │
  │  REVOKE UPDATE ON audit_log FROM thittam_app;            │
  │  REVOKE DELETE ON audit_log FROM thittam_app;            │
  └──────────────────────────────────────────────────────────┘

  If a budget approval is disputed:
    SELECT * FROM audit_log
    WHERE target_type = 'budget'
      AND target_id = '<disputed-budget-uuid>'
    ORDER BY occurred_at;
    
  → Shows every action, who took it, old state, new state.
  → Cannot be backdated or deleted.
  → Admissible in financial dispute resolution.
```

---

### ❌ Critical — SQL Injection Risk in Tenant Schema Routing

```
CRITICAL: String interpolation in SET search_path

  pkg/tenant/context.go (likely pattern):
  ┌──────────────────────────────────────────────────────────┐
  │  tenantID := r.Header.Get("X-Tenant-ID")                 │
  │  query := fmt.Sprintf(                                    │
  │      "SET search_path = tenant_%s, public",              │
  │      tenantID    ← DANGER: user-controlled input         │
  │  )                                                        │
  │  db.Exec(query)                                          │
  └──────────────────────────────────────────────────────────┘

  Attack vector:
  X-Tenant-ID: '; DROP SCHEMA tenant_legitimate; --

  Executed SQL:
  SET search_path = tenant_; DROP SCHEMA tenant_legitimate; --, public

  Effect: An attacker with a valid JWT but a crafted tenant ID
  can destroy any tenant's schema.

  Note: Kong validates the X-Tenant-ID header, which reduces
  but does not eliminate this risk (depends on Kong config).
  Validation must also happen at the service layer.
```

#### 🔧 How to Improve

```
GOOD: Validate UUID format before any interpolation

  pkg/tenant/context.go:
  ┌──────────────────────────────────────────────────────────┐
  │  import "github.com/google/uuid"                         │
  │                                                           │
  │  func SetTenantSchema(ctx context.Context,               │
  │                       db *pgxpool.Pool,                  │
  │                       tenantID string) error {           │
  │                                                           │
  │      // MUST validate before any interpolation           │
  │      parsed, err := uuid.Parse(tenantID)                 │
  │      if err != nil {                                     │
  │          return fmt.Errorf("invalid tenant ID: %w", err) │
  │      }                                                    │
  │                                                           │
  │      // parsed.String() is always the canonical UUID form│
  │      // Format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx     │
  │      // No SQL metacharacters possible in this format     │
  │      schema := "tenant_" + parsed.String()               │
  │                                                           │
  │      _, err = db.Exec(ctx,                               │
  │          "SET search_path = "+schema+", public",         │
  │      )                                                    │
  │      return err                                          │
  │  }                                                        │
  └──────────────────────────────────────────────────────────┘

  Why parsed.String() is safe:
    uuid.Parse() rejects anything that is not a valid UUID.
    A valid UUID contains only hex digits and hyphens.
    Hyphens in schema names are fine; no SQL metacharacters.

  Add to test suite:
  ┌──────────────────────────────────────────────────────────┐
  │  func TestSetTenantSchemaRejectsInjection(t *testing.T) {│
  │      cases := []string{                                  │
  │          "'; DROP TABLE tenants; --",                    │
  │          "../../etc/passwd",                             │
  │          "not-a-uuid",                                   │
  │          "",                                             │
  │      }                                                    │
  │      for _, tc := range cases {                          │
  │          err := SetTenantSchema(ctx, db, tc)             │
  │          require.Error(t, err)                           │
  │      }                                                    │
  │  }                                                        │
  └──────────────────────────────────────────────────────────┘
```

---

### ⚠️ Bad — Contradiction Between Rule #2 and Security Doc on T1 Secrets

```
BAD: Two conflicting rules for how JWT signing keys are stored

  CODING_RULES.md — Rule #2:
    "All secrets come from environment variables.
     os.Getenv('JWT_SECRET')"

  data-security-rbac.md (Security doc):
    "T1 data never leaves Vault and never goes in env vars.
     JWT signing keys are T1 data."

  What actually happens:
  ┌──────────────────────────────────────────────────────────┐
  │  Deployment → JWT_SECRET set as env var (Rule #2)        │
  │                                                           │
  │  Security risk:                                          │
  │  ├── /proc/environ on any container exposes JWT_SECRET   │
  │  ├── docker inspect exposes env vars                     │
  │  ├── Log aggregation accidentally captures env dumps     │
  │  └── Container orchestration (K8s) ConfigMaps leak       │
  └──────────────────────────────────────────────────────────┘
```

#### 🔧 How to Improve

```
GOOD: Vault-sourced secrets held in memory only

  Service startup pattern (consistent with ADR-009):
  ┌──────────────────────────────────────────────────────────┐
  │  func loadSecrets(ctx context.Context,                   │
  │                   vault *vault.Client) (*Secrets, error) {│
  │      // Fetch from Vault at startup — not from env       │
  │      data, err := vault.Logical().Read(                  │
  │          "secret/data/thittam/jwt",                      │
  │      )                                                    │
  │      if err != nil {                                     │
  │          return nil, fmt.Errorf(                         │
  │              "fetch jwt secret from vault: %w", err)     │
  │      }                                                    │
  │      return &Secrets{                                    │
  │          JWTSigningKey: data.Data["signing_key"].(string)│
  │      }, nil                                              │
  │  }                                                        │
  └──────────────────────────────────────────────────────────┘

  The secret lives in process memory only.
  Never written to disk. Never in env var. Never in logs.

  Update Rule #2 in CODING_RULES.md:
  ┌──────────────────────────────────────────────────────────┐
  │  Rule #2 — Secrets From Environment Only (updated)       │
  │                                                           │
  │  T3/T4 config: environment variables (DATABASE_URL,      │
  │                REDIS_URL, feature flags)                 │
  │  T1/T2 secrets: Vault-sourced at startup (JWT signing    │
  │                 keys, DB passwords, API keys)            │
  │                                                           │
  │  Never log any secret at any tier.                       │
  │  Fail fast at startup if Vault is unreachable (T1/T2).  │
  └──────────────────────────────────────────────────────────┘
```

---

### ⚠️ Bad — Impersonation Session Lifecycle Is Undefined

```
BAD: Platform admin impersonation has no time limit or revocation policy

  pkg/platform/service.go — impersonation exists, but:
  ┌──────────────────────────────────────────────────────────┐
  │  Questions with no documented answers:                   │
  │                                                           │
  │  Who can initiate impersonation?                         │
  │    → Any platform admin? Only super-admin?               │
  │                                                           │
  │  How long can an impersonation session last?             │
  │    → Indefinite? 1 hour? 15 minutes?                     │
  │                                                           │
  │  Is the impersonated session revoked when:               │
  │    → Target user changes their password?                 │
  │    → Target tenant is suspended?                         │
  │    → Impersonating admin's session expires?              │
  │                                                           │
  │  What is audited?                                        │
  │    → Start of impersonation?                             │
  │    → Every action taken while impersonating?             │
  │    → End of impersonation?                               │
  │                                                           │
  │  Risk: A platform admin impersonates a finance director, │
  │  approves a fraudulent expense, and there is no audit    │
  │  trail distinguishing the action from a legitimate one.  │
  └──────────────────────────────────────────────────────────┘
```

#### 🔧 How to Improve

```
GOOD: Explicit impersonation session model

  pkg/platform/types.go:
  ┌──────────────────────────────────────────────────────────┐
  │  type ImpersonationSession struct {                       │
  │      ID              uuid.UUID                           │
  │      AdminID         uuid.UUID   // who is impersonating │
  │      TargetUserID    uuid.UUID   // who is being impersonated│
  │      TenantID        uuid.UUID                           │
  │      StartedAt       time.Time                           │
  │      ExpiresAt       time.Time   // StartedAt + 30min    │
  │      EndedAt         *time.Time  // nil if active        │
  │      EndReason       string      // "timeout"|"manual"|..│
  │  }                                                        │
  └──────────────────────────────────────────────────────────┘

  Rules to document and enforce:
  ┌──────────────────────────────────────────────────────────┐
  │  1. Only super_admin role can initiate impersonation     │
  │  2. Session expires after 30 minutes (hard TTL in Redis) │
  │  3. Impersonation tokens carry is_impersonated:true      │
  │     and impersonating_admin_id in the JWT payload        │
  │  4. Every request in an impersonation session writes to  │
  │     audit_log with both actor_id AND impersonating_id    │
  │  5. Target user password change → immediate revocation   │
  │  6. Maximum 1 active impersonation per admin at a time   │
  └──────────────────────────────────────────────────────────┘

  Audit log entry during impersonation:
    actor_id:           <target_user_uuid>
    impersonated_by:    <admin_uuid>
    action:             APPROVE_EXPENSE
    ...

  Any auditor can see: this action was taken by the admin
  while impersonating the target user.
```

---

## 3. Financial Data Practices

### ✅ Good — Money Is Never a Float (Rule #1)

```
GOOD: Decimal precision enforced at every layer

  Layer 1: Go struct
  ┌──────────────────────────────────────────────────────────┐
  │  import "github.com/shopspring/decimal"                  │
  │                                                           │
  │  type BudgetLineItem struct {                            │
  │      Amount   decimal.Decimal  ← never float64          │
  │      Tax      decimal.Decimal  ← never float64          │
  │      Total    decimal.Decimal  ← never float64          │
  │  }                                                        │
  └──────────────────────────────────────────────────────────┘

  Layer 2: PostgreSQL
  ┌──────────────────────────────────────────────────────────┐
  │  amount NUMERIC(14,2) NOT NULL   ← never FLOAT or REAL  │
  └──────────────────────────────────────────────────────────┘

  Layer 3: API response (Kong → client)
  ┌──────────────────────────────────────────────────────────┐
  │  {"amount": "15000.00"}  ← string, 2dp, never a number  │
  └──────────────────────────────────────────────────────────┘

  Why this matters:
  ┌──────────────────────────────────────────────────────────┐
  │  float64 arithmetic:                                     │
  │    0.1 + 0.2 = 0.30000000000000004                      │
  │                                                           │
  │  On a film production with a $5,000,000 budget:          │
  │    Daily rate calculations accumulate float errors       │
  │    Budget vs. actual difference may be $0.01 or $100     │
  │    Financial reports don't balance                       │
  │    Auditors flag the discrepancy                         │
  │                                                           │
  │  decimal.Decimal arithmetic:                             │
  │    0.1 + 0.2 = 0.3 (exact)                              │
  │    Budget always balances to the cent                    │
  └──────────────────────────────────────────────────────────┘
```

---

### ✅ Good — Double-Entry Ledger Is Correctly Modelled

```
GOOD: General ledger enforces accounting identity at the DB level

  migrations/ledger/003_create_journal_entries.up.sql:
  ┌──────────────────────────────────────────────────────────┐
  │  CREATE TABLE journal_entries (                          │
  │    id             UUID PRIMARY KEY,                      │
  │    tenant_id      UUID NOT NULL,                         │
  │    period_id      UUID NOT NULL,                         │
  │    description    TEXT NOT NULL,                         │
  │    posted_at      TIMESTAMPTZ,                           │
  │    created_by     UUID NOT NULL,                         │
  │    idempotency_key TEXT UNIQUE                           │
  │  );                                                       │
  │                                                           │
  │  migrations/ledger/004_create_journal_lines.up.sql:      │
  │  CREATE TABLE journal_lines (                            │
  │    entry_id    UUID REFERENCES journal_entries(id),      │
  │    account_id  UUID REFERENCES accounts(id),             │
  │    debit       NUMERIC(14,2) NOT NULL DEFAULT 0,         │
  │    credit      NUMERIC(14,2) NOT NULL DEFAULT 0,         │
  │    CHECK (debit >= 0 AND credit >= 0),                   │
  │    CHECK (debit = 0 OR credit = 0)  ← one side only     │
  │  );                                                       │
  │                                                           │
  │  -- Enforced in service.go (DB constraint is backup):    │
  │  -- SUM(debit) = SUM(credit) for any journal_entry       │
  └──────────────────────────────────────────────────────────┘

  Every expense approval produces a balanced journal entry:
  Debit:  Production Expenses (above-the-line)  $5,000.00
  Credit: Accounts Payable                      $5,000.00
  → These always balance. A financial statement that does not
    balance is a service bug, detected immediately.
```

---

### ⚠️ Bad — bcrypt Cost 12 Is Vulnerable Under Concurrent Auth Load

```
BAD: bcrypt at cost 12 creates a CPU exhaustion vector

  Measurement on modern hardware:
    bcrypt cost 12 ≈ 250ms per hash

  Concurrent login storm (100 simultaneous users):
  ┌──────────────────────────────────────────────────────────┐
  │  goroutine 1: bcrypt.CompareHashAndPassword() ← 250ms   │
  │  goroutine 2: bcrypt.CompareHashAndPassword() ← 250ms   │
  │  ... (goroutines 3-100 same)                             │
  │                                                           │
  │  Go's goroutine scheduler uses GOMAXPROCS threads        │
  │  If GOMAXPROCS=4: 4 bcrypt hashes run truly parallel    │
  │  Remaining 96 goroutines queue                           │
  │  Last goroutine waits: 96/4 × 250ms = 6,000ms (6 sec)  │
  │                                                           │
  │  Deliberate attack: attacker sends 1000 login requests  │
  │  from 1000 IPs (bypasses per-IP rate limit)             │
  │  → IAM service CPU saturated for minutes                │
  │  → All other IAM operations (JWT validation, user       │
  │    lookup) queued behind bcrypt workers                  │
  └──────────────────────────────────────────────────────────┘
```

#### 🔧 How to Improve

```
GOOD: Replace bcrypt with argon2id + bounded worker pool

  Option A: argon2id (better memory-hardness profile)
  ┌──────────────────────────────────────────────────────────┐
  │  import "golang.org/x/crypto/argon2"                     │
  │                                                           │
  │  func HashPassword(password string) (string, error) {    │
  │      salt := make([]byte, 16)                            │
  │      rand.Read(salt)                                     │
  │      hash := argon2.IDKey(                               │
  │          []byte(password),                               │
  │          salt,                                           │
  │          1,      // time cost (iterations)               │
  │          64*1024,// memory cost (64 MB)                  │
  │          4,      // parallelism                          │
  │          32,     // key length                           │
  │      )                                                    │
  │      return encode(salt, hash), nil                      │
  │  }                                                        │
  └──────────────────────────────────────────────────────────┘

  Option B: Keep bcrypt, but bound the worker pool
  ┌──────────────────────────────────────────────────────────┐
  │  // Bounded semaphore: max 8 concurrent bcrypt operations│
  │  var bcryptSem = make(chan struct{}, 8)                   │
  │                                                           │
  │  func VerifyPassword(hash, password string) error {      │
  │      bcryptSem <- struct{}{}          // acquire         │
  │      defer func() { <-bcryptSem }()  // release         │
  │      return bcrypt.CompareHashAndPassword(               │
  │          []byte(hash), []byte(password),                 │
  │      )                                                    │
  │  }                                                        │
  └──────────────────────────────────────────────────────────┘

  The semaphore approach: 1001st login request gets a 503
  (semaphore full) rather than queuing indefinitely.
  Combined with per-IP rate limiting → attack is bounded.
```

---

## 4. Code Quality Practices

### ✅ Good — Sentinel Errors with Package Prefixes

```
GOOD: Errors are typed, not stringly-typed

  services/budget/errors.go:
  ┌──────────────────────────────────────────────────────────┐
  │  var (                                                    │
  │      ErrNotFound     = errors.New("budget: not found")   │
  │      ErrAlreadyApproved = errors.New(                    │
  │                           "budget: already approved")    │
  │      ErrVersionConflict = errors.New(                    │
  │                           "budget: version conflict")    │
  │  )                                                        │
  └──────────────────────────────────────────────────────────┘

  Handler converts errors to gRPC status codes:
  ┌──────────────────────────────────────────────────────────┐
  │  func (h *Handler) ApproveBudget(ctx context.Context,    │
  │       req *budgetpb.ApproveBudgetRequest) (              │
  │       *budgetpb.ApproveBudgetResponse, error) {          │
  │                                                           │
  │      err := h.svc.ApproveBudget(ctx, req.BudgetId)      │
  │      if err != nil {                                     │
  │          switch {                                        │
  │          case errors.Is(err, budget.ErrNotFound):        │
  │              return nil, status.Error(codes.NotFound,    │
  │                  "budget not found")                     │
  │          case errors.Is(err, budget.ErrAlreadyApproved): │
  │              return nil, status.Error(codes.FailedPrecondition,│
  │                  "budget already approved")              │
  │          default:                                        │
  │              return nil, status.Error(codes.Internal,    │
  │                  "internal error")  ← never leak details │
  │          }                                               │
  │      }                                                    │
  │  }                                                        │
  └──────────────────────────────────────────────────────────┘

  Logged once at the handler. Not re-wrapped at every layer.
  Internal details never reach the gRPC caller (Rule #11).
```

---

### ✅ Good — Idempotency Is Structural, Not Bolted On

```
GOOD: Every write operation is safe to retry (Rule #5)

  SQL (via sqlc):
    INSERT INTO journal_entries (id, ..., idempotency_key)
    VALUES ($1, ..., $N)
    ON CONFLICT (idempotency_key) DO NOTHING

  Event deduplication:
    INSERT INTO processed_events (event_id, processed_at)
    VALUES ($1, NOW())
    ON CONFLICT (event_id) DO NOTHING

  gRPC client retries (Istio):
    retries:
      attempts: 3
      perTryTimeout: 5s
      retryOn: gateway-error,connect-failure

  Effect: Stripe sends a webhook twice → second is a no-op.
  Network glitch causes retry → duplicate journal entry impossible.
  NATS redelivers an event → second processing is a no-op.
```

---

### ⚠️ Bad — No Input Validation Library Mentioned

```
BAD: Boundary validation is likely handwritten and inconsistent

  Rule #11 requires: "Validate all external input at the service boundary"

  Go has no built-in validation framework. Without a library:
  ┌──────────────────────────────────────────────────────────┐
  │  handler.go (budget service):                            │
  │    if req.Amount == "" {                                 │
  │        return nil, status.Error(codes.InvalidArgument,  │
  │            "amount required")                           │
  │    }                                                      │
  │    // No: min value check, max value check,              │
  │    // currency code validation, date range validation   │
  │                                                           │
  │  handler.go (expense service):                           │
  │    // Different developer, different validation style    │
  │    if req.Amount <= 0 {                                  │
  │        return error  // inconsistent with budget handler │
  │    }                                                      │
  │                                                           │
  │  Without a standard: validation coverage is spotty,      │
  │  inconsistent, and not systematically tested.            │
  └──────────────────────────────────────────────────────────┘
```

#### 🔧 How to Improve

```
GOOD: protovalidate for protobuf-level validation

  proto/budget/v1/budget.proto:
  ┌──────────────────────────────────────────────────────────┐
  │  syntax = "proto3";                                      │
  │  import "buf/validate/validate.proto";                   │
  │                                                           │
  │  message CreateBudgetRequest {                           │
  │      string name = 1 [(buf.validate.field).string = {    │
  │          min_len: 1,                                     │
  │          max_len: 200,                                   │
  │      }];                                                  │
  │                                                           │
  │      string amount = 2 [(buf.validate.field).string = {  │
  │          pattern: "^\\d+\\.\\d{2}$",  // "15000.00"    │
  │      }];                                                  │
  │                                                           │
  │      string currency = 3 [(buf.validate.field).string = {│
  │          len: 3,                                         │
  │          // ISO 4217 currency code                       │
  │      }];                                                  │
  │  }                                                        │
  └──────────────────────────────────────────────────────────┘

  gRPC interceptor validates every incoming request:
  ┌──────────────────────────────────────────────────────────┐
  │  import "github.com/bufbuild/protovalidate-go"           │
  │                                                           │
  │  func ValidationInterceptor() grpc.UnaryServerInterceptor│
  │  {                                                        │
  │      v, _ := protovalidate.New()                         │
  │      return func(ctx context.Context,                    │
  │                  req interface{},                        │
  │                  _ *grpc.UnaryServerInfo,                │
  │                  handler grpc.UnaryHandler) (            │
  │                  interface{}, error) {                   │
  │          if msg, ok := req.(proto.Message); ok {         │
  │              if err := v.Validate(msg); err != nil {     │
  │                  return nil, status.Error(               │
  │                      codes.InvalidArgument, err.Error()) │
  │              }                                           │
  │          }                                               │
  │          return handler(ctx, req)                        │
  │      }                                                    │
  │  }                                                        │
  └──────────────────────────────────────────────────────────┘

  Result: Validation rules live in the proto file — the single
  source of truth — and are enforced automatically for every
  service that uses that proto. No handwritten validation.
```

---

## 5. Testing Practices

### ✅ Good — Hand-Written Mocks Are Readable and Debuggable

```
GOOD: Function field mocks — no magic, no code generation

  services/budget/service_test.go:
  ┌──────────────────────────────────────────────────────────┐
  │  type mockBudgetRepo struct {                            │
  │      CreateBudgetFn  func(ctx, Budget) (*Budget, error)  │
  │      ApproveBudgetFn func(ctx, uuid.UUID) error          │
  │  }                                                        │
  │                                                           │
  │  func (m *mockBudgetRepo) CreateBudget(                  │
  │      ctx context.Context, b Budget) (*Budget, error) {   │
  │      return m.CreateBudgetFn(ctx, b)                     │
  │  }                                                        │
  │                                                           │
  │  // Test:                                                │
  │  func TestApproveBudget_AlreadyApproved(t *testing.T) { │
  │      t.Parallel()                                        │
  │      repo := &mockBudgetRepo{                            │
  │          ApproveBudgetFn: func(ctx context.Context,      │
  │                                id uuid.UUID) error {     │
  │              return budget.ErrAlreadyApproved            │
  │          },                                              │
  │      }                                                    │
  │      svc := NewService(repo, verticalConfig)             │
  │      err := svc.ApproveBudget(ctx,                       │
  │                 uuid.MustParse("d1000000-..."))          │
  │      require.ErrorIs(t, err, budget.ErrAlreadyApproved) │
  │  }                                                        │
  └──────────────────────────────────────────────────────────┘

  The mock is 10 lines. The test is 15 lines.
  No setup, no teardown, no framework to learn.
  When the test fails, the call stack is obvious.
```

---

### ⚠️ Bad — ~306 Tests Is Too Low for a Financial Platform

```
BAD: Test count does not match the financial risk surface

  Expected vs. actual:
  ┌──────────────────────────────────────────────────────────┐
  │  Service         Files  Expected tests  Approx. actual   │
  │  ─────────────────────────────────────────────────────── │
  │  iam             6      60+             ~40?             │
  │  general-ledger  6      80+  ← critical ~35?             │
  │  budget-planning 6      60+             ~35?             │
  │  expense-track.  6      60+             ~30?             │
  │  project-mgmt    6      40+             ~25?             │
  │  inventory-mgmt  6      30+             ~20?             │
  │  reporting       7      50+             ~30?             │
  │  notifications   5      30+             ~20?             │
  │  document        5      40+             ~20?             │
  │  shared packages 8      80+             ~30?             │
  │  ─────────────────────────────────────────────────────── │
  │  Total expected: ~530+   Total actual: ~306              │
  │                                                           │
  │  Most undercovered area: general-ledger                  │
  │  A single rounding error in journal line posting         │
  │  on a $5M production budget = financial misstatement     │
  └──────────────────────────────────────────────────────────┘

  Coverage thresholds defined:
    iam/general-ledger ≥ 85%  (enforced in CI)
    budget/expense ≥ 80%
    others ≥ 75%

  These thresholds are correct. The question is whether they
  are actually met with 306 total tests across 9 services.
```

#### 🔧 How to Improve

```
GOOD: Explicit test targets per service, tracked in CI

  Set concrete targets and a CI gate:
  ┌──────────────────────────────────────────────────────────┐
  │  Target: 800+ tests by GA                                │
  │                                                           │
  │  Priority order for new tests:                           │
  │                                                           │
  │  1. general-ledger — double-entry balance assertion       │
  │     Test: every journal_entry has SUM(debit)=SUM(credit) │
  │     Test: closed period rejects new entries              │
  │     Test: posting idempotency (same idempotency_key)     │
  │                                                           │
  │  2. expense approval workflow                            │
  │     Test: state machine (draft→submitted→approved→posted) │
  │     Test: approver cannot self-approve                   │
  │     Test: approval triggers ledger entry                 │
  │                                                           │
  │  3. budget version workflow                              │
  │     Test: version conflict detection                     │
  │     Test: line item budget does not exceed parent        │
  │     Test: approved version cannot be edited              │
  │                                                           │
  │  4. registration pipeline                                │
  │     Test: idempotency (same email, second attempt)       │
  │     Test: saga rollback (inject failure at each step)    │
  │     Test: vertical YAML loaded correctly                 │
  └──────────────────────────────────────────────────────────┘
```

---

### ⚠️ Bad — Vertical Plugin YAML Has No Schema and No Test Suite

```
BAD: The platform's core differentiator has no contract

  Current state:
  ┌──────────────────────────────────────────────────────────┐
  │  pkg/vertical/validator.go  exists                       │
  │  (validates YAML at load time)                           │
  │                                                           │
  │  BUT:                                                    │
  │  ├── No JSON Schema / proto schema for the YAML format   │
  │  ├── No documentation of required vs. optional fields    │
  │  ├── No test suite for the validator itself              │
  │  └── No test cases for edge cases:                       │
  │       - Empty phase_types list                           │
  │       - Missing budget_categories                        │
  │       - Unknown field (should it fail or warn?)          │
  │       - Vertical with 0 workflow rules                   │
  │                                                           │
  │  A developer adding a new vertical has no authoritative  │
  │  reference. They copy an existing YAML and guess.        │
  └──────────────────────────────────────────────────────────┘
```

#### 🔧 How to Improve

```
GOOD: JSON Schema + comprehensive validator test suite

  verticals/schema/vertical-schema.json:
  ┌──────────────────────────────────────────────────────────┐
  │  {                                                        │
  │    "$schema": "https://json-schema.org/draft/2020-12",  │
  │    "type": "object",                                     │
  │    "required": ["id", "name", "entity_labels",           │
  │                 "phase_types", "budget_categories"],     │
  │    "properties": {                                       │
  │      "id": { "type": "string", "pattern": "^[a-z-]+$" },│
  │      "phase_types": {                                    │
  │        "type": "array",                                  │
  │        "minItems": 1,                                    │
  │        "items": { "type": "string" }                     │
  │      },                                                   │
  │      "budget_categories": {                              │
  │        "type": "array",                                  │
  │        "minItems": 1                                     │
  │      }                                                    │
  │    }                                                      │
  │  }                                                        │
  └──────────────────────────────────────────────────────────┘

  pkg/vertical/validator_test.go:
  ┌──────────────────────────────────────────────────────────┐
  │  func TestValidateVertical(t *testing.T) {               │
  │      cases := []struct {                                 │
  │          name    string                                   │
  │          yaml    string                                   │
  │          wantErr bool                                     │
  │      }{                                                   │
  │          {"valid film", filmYAML, false},                │
  │          {"missing phase_types", missingPhasesYAML, true},│
  │          {"empty budget_categories", emptyCatsYAML, true},│
  │          {"unknown field", unknownFieldYAML, true},      │
  │          {"all verticals load cleanly", nil, false},     │
  │          // last case: load every YAML in verticals/     │
  │          // none should fail                             │
  │      }                                                    │
  │  }                                                        │
  └──────────────────────────────────────────────────────────┘

  CI step: test that every vertical YAML in the repository
  loads without error before any service test runs.
```

---

## 6. Observability Practices

### ✅ Good — Observability Is Enforced by the Shared gRPC Interceptor

```
GOOD: Every service gets metrics and correlation IDs for free

  pkg/observability/interceptor.go:
  ┌──────────────────────────────────────────────────────────┐
  │  Every gRPC server uses this interceptor chain:          │
  │                                                           │
  │  1. CorrelationID interceptor                            │
  │     → generates/propagates correlation_id               │
  │     → adds to context + response metadata               │
  │                                                           │
  │  2. Metrics interceptor                                  │
  │     → records request_duration_seconds{service, method} │
  │     → records request_total{service, method, status}    │
  │                                                           │
  │  3. Audit interceptor (for mutation methods)             │
  │     → writes audit_log row for every state change        │
  │                                                           │
  │  Effect:                                                 │
  │  A new service added to the platform automatically gets  │
  │  metrics, correlation IDs, and audit logging by wiring   │
  │  in pkg/server/server.go (which applies the chain).     │
  └──────────────────────────────────────────────────────────┘
```

---

### ⚠️ Bad — No Circuit Breaker Policy for gRPC Service Failures

```
BAD: If general-ledger is down, what happens to expense-tracking?

  Current: Istio retries configured (3 attempts, 5s timeout each)
  Missing: Circuit breaker policy

  Without a circuit breaker:
  ┌──────────────────────────────────────────────────────────┐
  │  general-ledger goes down (OOM, deploy, crash)           │
  │       │                                                   │
  │       ▼                                                   │
  │  expense-tracking tries to post journal entry            │
  │  → 3 retries × 5s timeout = 15 seconds per request      │
  │       │                                                   │
  │       ▼                                                   │
  │  Expense approval queue backs up                         │
  │  All approval requests now take 15+ seconds              │
  │  expense-tracking goroutines pile up waiting on retries  │
  │  expense-tracking runs out of goroutines                 │
  │  expense-tracking itself becomes unavailable             │
  │       │                                                   │
  │  Cascading failure: one downed service takes down two    │
  └──────────────────────────────────────────────────────────┘
```

#### 🔧 How to Improve

```
GOOD: Istio DestinationRule circuit breaker per service

  infra/k8s/general-ledger-destination-rule.yaml:
  ┌──────────────────────────────────────────────────────────┐
  │  apiVersion: networking.istio.io/v1beta1                 │
  │  kind: DestinationRule                                   │
  │  metadata:                                               │
  │    name: general-ledger-circuit-breaker                  │
  │  spec:                                                    │
  │    host: general-ledger.thittam.svc.cluster.local        │
  │    trafficPolicy:                                        │
  │      outlierDetection:                                   │
  │        consecutive5xxErrors: 5     ← trip after 5 errors │
  │        interval: 30s               ← evaluation window  │
  │        baseEjectionTime: 30s       ← how long to open   │
  │        maxEjectionPercent: 50      ← max pods ejected   │
  │      connectionPool:               ← max concurrent conns│
  │        http:                                             │
  │          http1MaxPendingRequests: 100                    │
  │          http2MaxRequests: 1000                          │
  └──────────────────────────────────────────────────────────┘

  With circuit breaker:
  ┌──────────────────────────────────────────────────────────┐
  │  general-ledger: 5 consecutive errors in 30s             │
  │       │                                                   │
  │       ▼ circuit opens                                    │
  │  expense-tracking: immediate UNAVAILABLE from Istio      │
  │  → no 15-second retry loop                               │
  │  → expense-tracking can degrade gracefully:              │
  │    - Queue journal entry for retry when circuit closes   │
  │    - Return 202 Accepted to caller (async posting)       │
  │    - Notify ops via NATS event                           │
  │  → expense-tracking stays healthy                        │
  └──────────────────────────────────────────────────────────┘

  Document per service: "If X is unavailable, we do Y."
  This is the circuit breaker policy — write it before launch.
```

---

### ⚠️ Bad — NATS Dead-Letter Strategy Is Undocumented

```
BAD: Financial events can be silently lost after N retries

  NATS JetStream delivery model:
  ┌──────────────────────────────────────────────────────────┐
  │  Producer: expense.approved event published              │
  │  Consumer: reporting-analytics subscribes                │
  │                                                           │
  │  reporting-analytics is down for maintenance             │
  │  → NATS retries delivery (MaxDeliver: N times)           │
  │  → After N attempts: what happens?                       │
  │                                                           │
  │  If MaxDeliver is hit with no dead-letter stream:        │
  │  → Event is dropped                                      │
  │  → reporting-analytics never processes the approval      │
  │  → Budget vs. actual report shows wrong figures          │
  │  → No alert, no log entry, no recovery path             │
  └──────────────────────────────────────────────────────────┘
```

#### 🔧 How to Improve

```
GOOD: Dead-letter stream per consumer group

  NATS JetStream configuration:
  ┌──────────────────────────────────────────────────────────┐
  │  // Create dead-letter stream for financial events       │
  │  js.AddStream(&nats.StreamConfig{                        │
  │      Name:     "FINANCIAL_DLQ",                          │
  │      Subjects: []string{"dlq.financial.>"},             │
  │      MaxAge:   30 * 24 * time.Hour,  // 30-day retention│
  │  })                                                       │
  │                                                           │
  │  // Consumer with DLQ on max delivery exceeded           │
  │  js.AddConsumer("FINANCIAL", &nats.ConsumerConfig{      │
  │      Durable:     "reporting-analytics",                 │
  │      MaxDeliver:  5,                                     │
  │      AckPolicy:   nats.AckExplicitPolicy,               │
  │      // On MaxDeliver: republish to DLQ subject          │
  │  })                                                       │
  └──────────────────────────────────────────────────────────┘

  Alert rule:
  ┌──────────────────────────────────────────────────────────┐
  │  Prometheus:                                             │
  │    nats_consumer_dlq_count{stream="FINANCIAL"} > 0      │
  │  → PagerDuty: "Financial event in dead letter queue"     │
  │  → Runbook: how to replay from FINANCIAL_DLQ stream     │
  └──────────────────────────────────────────────────────────┘

  Recovery (manual or automated):
    nats stream sub FINANCIAL_DLQ
    → inspect each dead-lettered event
    → re-publish to original subject after fix
    → idempotency key prevents duplicate processing
```

---

## 7. Documentation Practices

### ✅ Good — 9 ADRs Covering Every Major Decision

```
GOOD: Decisions are documented with their rationale and trade-offs

  ADR format used:
  ┌──────────────────────────────────────────────────────────┐
  │  # ADR-NNN — [Decision Title]                            │
  │                                                           │
  │  ## Context                                              │
  │  Why was this decision needed? What problem was it       │
  │  solving? What options existed?                          │
  │                                                           │
  │  ## Decision                                             │
  │  What was chosen?                                        │
  │                                                           │
  │  ## Rationale                                            │
  │  Trade-off table comparing options.                      │
  │                                                           │
  │  ## Consequences                                         │
  │  What does this decision make harder?                    │
  │  What does it make easier?                               │
  │  What must be done differently as a result?             │
  └──────────────────────────────────────────────────────────┘

  Effect:
  A new team member asked "why gRPC and not REST for internal
  services?" reads ADR-003 and gets: the question, the options
  considered, the reasons for the choice, and the trade-offs
  accepted. No tribal knowledge required.

  When a decision turns out to be wrong:
  Write ADR-010 that supersedes ADR-NNN. Never edit the
  original — the history of wrong decisions is as valuable
  as the correct ones.
```

---

### ⚠️ Bad — Documentation Drift Is Inevitable at 41+ Files

```
BAD: Rule #16 says CI "should" validate — but it does not yet

  Documentation surface at risk:
  ┌──────────────────────────────────────────────────────────┐
  │  thittam_docs/ (41+ markdown files)                      │
  │  ├── services/*.md        ← lists endpoints + fields     │
  │  ├── adrs/*.md            ← references Go types          │
  │  ├── architecture/*.md    ← references service names     │
  │  └── api/*.md             ← references proto methods     │
  │                                                           │
  │  Risk timeline:                                          │
  │  Week 1:  service renamed → docs not updated            │
  │  Week 4:  API field changed → docs show old name        │
  │  Month 3: docs describe a service that no longer exists  │
  │  Month 6: new developers trust the docs → write wrong   │
  │           code → debugging takes 2× longer              │
  │                                                           │
  │  "CI should validate" (Rule #16) remains aspirational.  │
  └──────────────────────────────────────────────────────────┘
```

#### 🔧 How to Improve

```
GOOD: Automated doc validation script in CI

  scripts/check_doc_drift.sh:
  ┌──────────────────────────────────────────────────────────┐
  │  #!/bin/bash                                             │
  │  # Check that every service name mentioned in docs       │
  │  # exists as a directory in services/ or cmd/           │
  │                                                           │
  │  FAIL=0                                                  │
  │                                                           │
  │  # Extract service names mentioned in docs               │
  │  grep -rh "services/" docs/ | \                         │
  │      grep -oE "services/[a-z-]+" | \                    │
  │      sort -u | \                                         │
  │  while read svc; do                                      │
  │      dir="${svc#services/}"                              │
  │      if [ ! -d "services/$dir" ]; then                  │
  │          echo "DRIFT: docs mention services/$dir"        │
  │          echo "       but directory does not exist"      │
  │          FAIL=1                                          │
  │      fi                                                   │
  │  done                                                     │
  │                                                           │
  │  # Check proto method names exist in generated code      │
  │  grep -rh "\.proto" docs/ | \                           │
  │      grep -oE "Rpc[A-Z][a-zA-Z]+" | \                  │
  │      sort -u | \                                         │
  │  while read method; do                                   │
  │      if ! grep -rq "$method" --include="*.go" .; then   │
  │          echo "DRIFT: docs mention $method"              │
  │          echo "       but not found in Go code"          │
  │          FAIL=1                                          │
  │      fi                                                   │
  │  done                                                     │
  │                                                           │
  │  exit $FAIL                                              │
  └──────────────────────────────────────────────────────────┘

  Add to Makefile:
    check-drift:
        bash scripts/check_doc_drift.sh

  Add to CI pipeline (after lint, before tests):
    - run: make check-drift
```

---

## 8. Summary Scorecard

```
┌──────────────────────────────────────────────────────────────────────┐
│  Thittam — Practices Scorecard                                        │
├────────────────────────────────┬──────────┬───────────────────────── │
│  Practice                      │  Rating  │  Priority Fix            │
├────────────────────────────────┼──────────┼──────────────────────────┤
│  Vertical plugin system        │  ✅ Good  │  —                       │
│  Consistent 6-file service layout│ ✅ Good │  —                       │
│  gRPC internal / REST external │  ✅ Good  │  —                       │
│  sqlc type-safe SQL            │  ✅ Good  │  —                       │
│  buf proto enforcement         │  ✅ Good  │  —                       │
│  Tenant-per-schema isolation   │  ✅ Good  │  —                       │
│  Istio mTLS east-west          │  ✅ Good  │  —                       │
│  Append-only audit log         │  ✅ Good  │  —                       │
│  Money as decimal.Decimal      │  ✅ Good  │  —                       │
│  Double-entry ledger model     │  ✅ Good  │  —                       │
│  Sentinel errors + wrapping    │  ✅ Good  │  —                       │
│  Idempotency structural (Rule#5)│ ✅ Good  │  —                       │
│  17 non-negotiable coding rules│  ✅ Good  │  —                       │
│  9 ADRs with trade-off tables  │  ✅ Good  │  —                       │
│  Hand-written mock repos       │  ✅ Good  │  —                       │
│  t.Parallel() + deterministic  │  ✅ Good  │  —                       │
│  Shared observability interceptor│ ✅ Good │  —                       │
│  /healthz /readyz /metrics     │  ✅ Good  │  —                       │
├────────────────────────────────┼──────────┼──────────────────────────┤
│  SET search_path injection     │  ❌ Crit  │  P0 — validate UUID first │
│  T1 secrets in env vars        │  ❌ Crit  │  P0 — resolve with Vault  │
│  4 protos pending              │  ❌ Crit  │  P0 — define immediately  │
│  No saga for registration      │  ⚠️  Bad  │  P0 — compensating txns   │
│  No reporting read model       │  ⚠️  Bad  │  P1 — event-sourced views │
│  bcrypt under concurrent load  │  ⚠️  Bad  │  P1 — argon2id or semaphore│
│  No input validation library   │  ⚠️  Bad  │  P1 — protovalidate       │
│  ~306 tests too low            │  ⚠️  Bad  │  P1 — target 800+         │
│  Vertical YAML no schema/tests │  ⚠️  Bad  │  P1 — JSON Schema + tests │
│  No circuit breaker policy     │  ⚠️  Bad  │  P1 — Istio DestinationRule│
│  NATS dead-letter undocumented │  ⚠️  Bad  │  P1 — DLQ per consumer    │
│  Impersonation lifecycle undef │  ⚠️  Bad  │  P2 — 30min TTL + rules   │
│  Documentation drift risk      │  ⚠️  Bad  │  P2 — CI drift check      │
│  E2E tests nightly only        │  ⚠️  Bad  │  P2 — PR-level for critical│
│  Billing service missing       │  ⚠️  Bad  │  P1 — ship before GA      │
│  No gRPC load balancing config │  ⚠️  Bad  │  P2 — Istio DestinationRule│
└────────────────────────────────┴──────────┴──────────────────────────┘

P0 = Fix immediately (security or data integrity risk)
P1 = Fix before first production tenants
P2 = Fix before scale / after launch
```

---

*Analysis based on Go source structure, migrations, CLAUDE.md, CODING_RULES.md, ADR records, and Thittam documentation. April 2026.*
