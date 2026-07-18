# Thittam — Good Practices, Bad Practices & How to Improve

**Document type:** Engineering practices analysis
**Scope:** Go microservices, gRPC, NATS JetStream, PostgreSQL, Istio, Kong, Vertical Plugin System, shadcn/ui web tier
**Period:** 2026-05-24 (v1.3 — alignment with critique v1.3: first refresh measured against on-disk code; saga / reporting / impersonation practices verified real in source)
**Prior:** v1.2 April 2026 (proto completion, T1 secret fix, schema injection fix, test expansion, multi-tenant demo expansion)
**Related:** [thittam-critique.md](thittam-critique.md) · [thittam-development-pattern.md](thittam-development-pattern.md)
**Rating key:** ✅ Good practice · ⚠️ Bad practice · ❌ Critical issue · 🔧 How to improve

> **Note (2026-05-24):** the body below is the v1.2 record, preserved. The v1.3 refresh measured against on-disk source for the first time and revealed that several practices the v1.2 catalogue flagged as **aspirational or absent are now real**. Updates to the catalogue:
>
> - **✅ Now real (was aspirational) — saga with compensation for the registration pipeline.** `pkg/registration/saga.go` (497 LOC) implements `RegistrationSaga` with a `SagaStatus` state machine (`compensating` / `compensated` / `compensation_failed`), a `Compensator` interface, documented reverse-order compensation 3→2→1, and idempotent step tracking. Plus `errors.go` + `db/models.go`. **The "9-step pipeline lacks a saga" v1.2 gap is closed.**
> - **✅ Now real (was undefined) — event-sourced read-model for reporting.** `services/reporting/consumer.go` — `ProjectionConsumer` subscribes to domain events and maintains the read-model projection. **The "reporting aggregates cross-service data without a documented read-model strategy" v1.2 gap is closed** with the event-sourced option the critique preferred.
> - **✅ Now real (was undefined) — bounded impersonation lifecycle.** `services/iam/service.go` + `models.go` — `StartImpersonation` / `EndImpersonation`, `ImpersonationSession`, 4h `maxImpersonationDuration`, background expiry ticker, `impersonation.start` / `.end` audit actions. **The "impersonation lifecycle is not yet formalised" v1.2 gap is closed.**
> - **✅ Verified-true-against-code (was inferred from docs) — schema-injection-resistant tenant routing.** `pkg/tenantdb.Acquire` accepts only `uuid.UUID`, rejects `uuid.Nil` before interpolation, uses `uuid.UUID.String()` (36 hex/hyphen characters, no SQL metacharacters) in `SET search_path`. The package comment documents why this is safe.
> - **✅ Verified-true-against-code — T1 secret handling.** `cmd/iam/main.go` loads JWT signing keys from Vault (production) or `FileSource` (dev, gitignored); keys held in process memory bytes only; Vault health gates `/readyz`.
> - **❌ Still open (P0, unchanged) — `audit_log` REVOKE UPDATE/DELETE is commented out.** `migrations/audit/001_create_audit_log.up.sql:29` with a "run after role creation" note. Append-only is still enforced by convention, not by DB grant. **The only open P0.**
> - **⚠️ Still open — circuit-breaker policy across service boundaries; tenant-per-schema scalability past 500 tenants.**
> - **🔧 New methodological practice — "verify against on-disk source" as part of review cadence.** The v1.2 → v1.3 delta is mostly *practices that already existed but were not documented*, not new practices. Future reviews should not skip the on-disk verification pass.
>
> Re-measured: 1,715 proto LOC (was 1,659), 1,203 Go test functions / 86 files (was 1,150 / 80), 80 SQL migration files / 2,076 LOC. The "71 docs / 13 ADRs (010/011 gap)" claim is **unverifiable** from the code repo — the sibling `thittam_docs` repo is not checked out locally.
---

## Table of Contents

1. [Architecture Practices](#1-architecture-practices)
2. [Security Practices](#2-security-practices)
3. [Financial Data Practices](#3-financial-data-practices)
4. [Code Quality Practices](#4-code-quality-practices)
5. [Testing Practices](#5-testing-practices)
6. [Observability Practices](#6-observability-practices)
7. [Documentation Practices](#7-documentation-practices)
8. [Multi-Tenant & Demo Practices](#8-multi-tenant--demo-practices)
9. [Summary Scorecard](#9-summary-scorecard)

---

## 1. Architecture Practices

### ✅ Good — Vertical Plugin System Makes the Platform Industry-Agnostic

```
GOOD: Configuration-driven industry support (ADR-007)

  Without vertical plugins (rejected):
    thittam-film / thittam-software / thittam-construction / thittam-events
    → 4× security patches, 4× deployments, divergence guaranteed within 6 months

  With vertical plugins (current):
    thittam (one codebase)
    verticals/film-production.yaml    ← vocabulary + rules
    verticals/software-dev.yaml
    verticals/construction.yaml
    verticals/events-mgmt.yaml

    Adding vertical 5 (Healthcare):
      Write verticals/healthcare.yaml (~50 lines)
      Add test suite for new YAML (~1 day)
      No core service changes

  The vertical config flows through every vertical-aware service via a gRPC
  interceptor that injects it into the request context. Services never hardcode
  industry-specific terms.
```

---

### ✅ Good — Consistent 6-File Service Layout Across All 10 Services

```
services/budget/        services/expense/        services/ledger/
├── models.go           ├── models.go            ├── models.go
├── errors.go           ├── errors.go            ├── errors.go
├── repository.go       ├── repository.go       ├── repository.go
├── service.go          ├── service.go          ├── service.go
├── service_test.go     ├── service_test.go     ├── service_test.go
└── handler.go          └── handler.go           └── handler.go

A developer who has worked in budget navigates expense on day one.
Dependency direction enforced by structure: handler → service → repository.
```

Holds across all 10 services: iam, project, budget, expense, ledger, inventory, notifications, document, reporting, billing.

---

### ✅ Good — gRPC Internal / REST External With grpc-gateway Shadow for Auth

```
External boundary (client → Kong → services):
  REST/JSON — clients are browsers and mobile apps; Kong handles auth, rate-limit, routing.

Internal boundary (service → service):
  gRPC/protobuf — type-safe contracts, binary efficiency, buf breaking detection.

Browser-to-IAM boundary (new in v1.2):
  grpc-gateway REST shadow at :9086 for /api/v1/auth/*
  → Browser can call login, refresh, /me via JSON with CORS working.
  → Backend remains gRPC-native; REST is generated.
```

Commits: `939b451` (grpc-gateway surface), `cc7f019` (CORS wrapper), `7e267f7` (snake_case JSON for TS types), `259d0fb` (web points at gateway, not bare gRPC).

---

### ✅ Good — All 10 Proto Definitions Are Complete

The v1.1 "4 of 9 protos pending" gap is closed.

```
proto/ — 1,659 LOC total, ~230 messages across 10 files:

  iam.proto              46 msgs   ← auth + OIDC
  project.proto          24 msgs
  budget.proto           24 msgs
  expense.proto          23 msgs
  ledger.proto           25 msgs
  inventory.proto        14 msgs
  notifications.proto    15 msgs
  document.proto         23 msgs
  reporting.proto        13 msgs
  billing.proto          23 msgs

Buf toolchain: buf lint + buf breaking + buf generate.
make generate-proto regenerates Go stubs on demand.
```

---

### ✅ Good — Code Generation Enforces Correctness at Compile Time

```
sqlc (SQL → Go):
  Input:  migrations/{service}/*.sql + queries/*.sql
  Output: services/{name}/db/{db.go, models.go, querier.go, queries.sql.go}

  Effect: SQL queries are type-checked at compile time.
  Effect: SQL injection is impossible (sqlc does not support interpolation).

buf (protobuf → Go):
  buf lint        → validates proto style rules
  buf breaking    → detects breaking changes vs main
  buf generate    → emits type-safe gRPC client/server

  Effect: Renaming an RPC method breaks CI before merge.
```

---

### ⚠️ Bad — Registration Pipeline Still Has No Saga Pattern

```
BAD: Distributed transaction with no compensating logic

  The 9-step registration pipeline:
    Step 1: Validate tenant data              ← reversible
    Step 2: INSERT INTO public.tenants        ← written
    Step 3: CREATE SCHEMA tenant_<uuid>       ← written
    Step 4: Run IAM migrations                ← written
    Step 5: Seed IAM (admin user)             ← written
    Step 6: Seed Ledger (chart of accounts)   ← written
    Step 7: Bind vertical config              ← written
    Step 8: Emit registration.complete (NATS) ← written
    Step 9: Send welcome notification (async)

  Failure at step 6: steps 2–5 already committed to different DBs/schemas.
  No compensating transaction; no documented rollback.
  Retrying registration for the same email fails with UNIQUE violation (step 2).
  Tenant stuck in broken state.
```

This is the most critical remaining architectural gap.

#### 🔧 How to Improve

```go
// pkg/registration/saga.go

type Step struct {
    Name       string
    Execute    func(ctx context.Context) error
    Compensate func(ctx context.Context) error
}

func (s *Saga) Run(ctx context.Context) error {
    var completed []Step
    for _, step := range s.steps {
        if err := step.Execute(ctx); err != nil {
            // Compensate in reverse order
            for i := len(completed) - 1; i >= 0; i-- {
                if compErr := completed[i].Compensate(ctx); compErr != nil {
                    logger.Error("compensation failed",
                        "step", completed[i].Name, "err", compErr)
                }
            }
            return fmt.Errorf("pipeline failed at %s: %w", step.Name, err)
        }
        completed = append(completed, step)
    }
    return nil
}
```

Add a dedicated test that injects a failure at each step index and asserts a clean rollback.

---

### ⚠️ Bad — Reporting-Analytics Has No Defined Read Model Strategy

```
BAD: Cross-service aggregation is architecturally unresolved

  Reporting service needs data from all 9 other services.

  Option A: Live gRPC fan-out (implicit)
    → Tail latency bounded by slowest service
    → All 9 services must be healthy for any report
    → Reporting load stresses transactional services
    → No caching without complex invalidation

  Option B: Shared DB (not used — correctly rejected as anti-pattern)

  Option C: Event-sourced read model (undocumented but hinted at by
            migrations/reporting/002_create_dashboard_views.up.sql)
```

#### 🔧 How to Improve

```
Every domain service publishes on state change:
  budget.approved, expense.submitted, expense.approved, journal.posted,
  project.phase.completed, ...

  → NATS JetStream → reporting-analytics subscribes
  → materialises its own read model (PostgreSQL views)
  → report request hits a single DB query, <50 ms
  → no cross-service calls at report time

Event envelope:
  type DomainEvent struct {
      EventID    uuid.UUID   // Rule #5 dedup key
      EventType  string
      TenantID   uuid.UUID
      OccurredAt time.Time
      Payload    []byte
  }

Deduplication:
  INSERT INTO processed_events (event_id) VALUES ($1) ON CONFLICT DO NOTHING;

Replay:
  NATS JetStream supports stream-level replay → any view can be rebuilt.
```

Write this up as ADR-016 before the first reporting consumer ships.

---

## 2. Security Practices

### ✅ Good — Tenant-Per-Schema Is Safe From Injection (v1.1 ❌ Critical Resolved)

The schema injection risk flagged in v1.1 is fixed.

```go
// pkg/tenantdb/tenantdb.go

func Acquire(ctx context.Context, pool *pgxpool.Pool, tenantID uuid.UUID) (*pgxpool.Conn, error) {
    // Accepts only uuid.UUID — compile-time type safety.
    if tenantID == uuid.Nil {
        return nil, ErrEmptyTenantID
    }

    conn, err := pool.Acquire(ctx)
    if err != nil {
        return nil, err
    }

    // uuid.UUID.String() is always canonical — 36 chars, hex + hyphens.
    // No SQL metacharacters are possible in this format.
    schema := "tenant_" + tenantID.String()
    _, err = conn.Exec(ctx, "SET search_path = "+schema+", public")
    if err != nil {
        conn.Release()
        return nil, err
    }
    return conn, nil
}
```

Package comment documents why this is safe. Test `TestSetTenantSchemaRejectsInvalidInput` covers `uuid.Nil`, malformed strings, and `'; DROP SCHEMA ...; --` payloads (rejected at the type level).

---

### ✅ Good — T1 Secrets Live in Memory, Never in Env Vars (v1.1 ❌ Critical Resolved)

```go
// cmd/iam/main.go — production path

vaultCfg := secrets.VaultConfig{
    Address:  os.Getenv("VAULT_ADDR"),
    RoleID:   os.Getenv("VAULT_ROLE_ID"),
    SecretID: os.Getenv("VAULT_SECRET_ID"),
}
// AppRole credentials are T3 — acceptable as env vars.

src := secrets.NewVaultSource(vaultCfg)

// T1 JWT signing key fetched from Vault, held in memory bytes only.
jwtKey, err := src.GetSecret(ctx, "iam/jwt-private-key")
// Never written to disk, never logged, never re-serialised.

// Register the Vault source as a /readyz health checker.
healthServer.Register("vault", src)
```

Dev path: `VAULT_ADDR` unset → `FileSource` reads from gitignored `./keys/` directory → memory bytes. Same discipline: never re-serialised, never logged.

Aligns Rule #2 with the security doc's T1 requirements.

---

### ✅ Good — Istio mTLS for All East-West Traffic

```
PeerAuthentication: STRICT mode (no plaintext)
AuthorizationPolicy: per-service allowlist

A compromised service with its own cert cannot call unintended services.
```

---

### ✅ Good — Append-Only Audit Log Schema Is Legally Defensible

```sql
CREATE TABLE audit_log (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id       UUID NOT NULL,
    action         TEXT NOT NULL,
    resource_type  TEXT NOT NULL,
    resource_id    UUID NOT NULL,
    tenant_id      UUID NOT NULL,
    old_state      JSONB,
    new_state      JSONB,
    metadata       JSONB,
    occurred_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX ... ON audit_log (tenant_id, resource_type, resource_id);
CREATE INDEX ... ON audit_log (actor_id, occurred_at);
CREATE INDEX ... ON audit_log (occurred_at);
CREATE INDEX ... ON audit_log (action);
```

---

### ✅ Good — Schema Injection Test Coverage

Test suite exercises malformed UUIDs, SQL metacharacter payloads, empty strings — all rejected at the `uuid.UUID` type boundary before ever reaching `SET search_path`.

---

### ⚠️ Bad — `audit_log` REVOKE UPDATE/DELETE Is Commented Out

```sql
-- migrations/audit/001_create_audit_log.up.sql, lines 27–29
-- REVOKE UPDATE ON audit_log FROM thittam_app;
-- REVOKE DELETE ON audit_log FROM thittam_app;
```

Until a dedicated app role is created and the REVOKEs applied in deployment, the table is append-only by convention, not by database constraint. Rule #7 specifies append-only.

#### 🔧 How to Improve

```
1. Create thittam_app role in ops setup (not via migration — role should outlive schemas).
2. Uncomment the REVOKE statements; run as a post-deploy step.
3. Add a test that attempts UPDATE/DELETE as thittam_app and asserts it fails.
4. Document the role model in docs/security/roles.md.
```

---

### ⚠️ Bad — Impersonation Session Lifecycle Is Undefined

```
pkg/platform/ supports impersonation; web/components/audit-log-viewer.tsx exists.
Missing end-to-end:
  Who can initiate? (super_admin only?)
  Session TTL? (30 min? indefinite?)
  Revocation triggers? (target password change, tenant suspension)
  Dual-actor audit entries? (actor_id AND impersonated_by)
  Concurrent impersonations per admin? (max 1?)
```

#### 🔧 How to Improve

```go
type ImpersonationSession struct {
    ID              uuid.UUID
    AdminID         uuid.UUID    // who is impersonating
    TargetUserID    uuid.UUID    // who is being impersonated
    TenantID        uuid.UUID
    StartedAt       time.Time
    ExpiresAt       time.Time    // StartedAt + 30 min
    EndedAt         *time.Time   // nil if active
    EndReason       string       // "timeout" | "manual" | "password_change" | ...
}

Rules:
  1. Only super_admin role can initiate
  2. Session expires after 30 min (Redis TTL enforced)
  3. Impersonation JWT carries: is_impersonated=true, impersonating_admin_id=...
  4. Every request in an impersonation session writes audit_log with
     actor_id=<target> AND impersonated_by=<admin>
  5. Target password change → immediate revocation
  6. Max 1 active impersonation per admin at a time
```

File as ADR-016.

---

### ⚠️ Bad — bcrypt Cost 12 Is CPU-Exhaustion–Susceptible Under Concurrent Load

~250 ms per hash. A 1000-request login storm from 1000 IPs (bypasses per-IP rate limit) saturates IAM CPU for minutes; JWT validation and user lookup queue behind bcrypt workers.

#### 🔧 How to Improve

```go
// Option A: migrate to argon2id (better memory-hardness profile)
hash := argon2.IDKey([]byte(password), salt,
    1,      // time cost
    64*1024,// memory cost (64 MB)
    4,      // parallelism
    32,     // key length
)

// Option B: keep bcrypt, bound concurrency
var bcryptSem = make(chan struct{}, 8)

func VerifyPassword(hash, password string) error {
    bcryptSem <- struct{}{}
    defer func() { <-bcryptSem }()
    return bcrypt.CompareHashAndPassword([]byte(hash), []byte(password))
}
```

Combined with per-IP rate limiting at Kong.

---

### ⚠️ Bad — NATS Per-Subject Authorization Not Specified

A compromised `notifications` service should not be able to publish to `ledger.journal.posted`.

#### 🔧 How to Improve

```
NATS user accounts per service (TLS cert identity):
  service-ledger    → pub: ledger.>, journal.>
                      sub: expense.approved
  service-expense   → pub: expense.>
                      sub: (various)
  service-notifications → pub: notifications.>
                      sub: notifications.>, expense.approved, budget.approved, ...

Document in docs/security/nats-subjects.md.
Enforce via NATS account configuration.
```

---

### ⚠️ Bad — MinIO Presigned URL TTL Is a Fixed 15 min

For industries with large uploads (film dailies, construction blueprints, event AV assets), 15 minutes may be too short on slow connections.

#### 🔧 How to Improve

Dynamic TTL based on file size (e.g., `max(15min, file_size_mb × 30s)`), or a session-scoped server-side proxy that reads MinIO on behalf of the client using a short-lived session token.

---

## 3. Financial Data Practices

### ✅ Good — Money Is Never a Float (Rule #1)

```
Go:             github.com/shopspring/decimal
PostgreSQL:     NUMERIC(14,2)
API response:   string with 2 decimal places ("15000.00")

float64 arithmetic: 0.1 + 0.2 = 0.30000000000000004
decimal arithmetic: 0.1 + 0.2 = 0.3 (exact)

On a $5,000,000 production budget, float accumulation produces pennies
of mismatch at report time — auditors flag discrepancies.
```

---

### ✅ Good — Double-Entry Ledger Correctly Modelled

```sql
CREATE TABLE journal_entries (
    id                UUID PRIMARY KEY,
    tenant_id         UUID NOT NULL,
    period_id         UUID NOT NULL,
    description       TEXT NOT NULL,
    posted_at         TIMESTAMPTZ,
    created_by        UUID NOT NULL,
    idempotency_key   TEXT UNIQUE
);

CREATE TABLE journal_lines (
    entry_id   UUID REFERENCES journal_entries(id),
    account_id UUID REFERENCES accounts(id),
    debit      NUMERIC(14,2) NOT NULL DEFAULT 0,
    credit     NUMERIC(14,2) NOT NULL DEFAULT 0,
    CHECK (debit >= 0 AND credit >= 0),
    CHECK (debit = 0 OR credit = 0)  -- one side only
);

-- Enforced in service.go (DB constraint is backup):
-- SUM(debit) = SUM(credit) per journal_entry
```

Every expense approval produces a balanced entry. A financial statement that doesn't balance is a detectable service bug.

---

### ✅ Good — Tenant-Level Primary Currency From Country

Commit `2d2091e` — tenant carries address + country-driven primary currency. XYZ_CBA (India) → INR; XYZ Construction (USA) → USD. No hardcoding; country → currency mapping drives display.

---

### ✅ Good — Column-Level Encryption for T1 Financial Fields

`day_rate` (payroll), `vendor_gstin` (tax IDs) — encrypted at the application layer with AES-256-GCM before writing to PostgreSQL. Key from Vault.

A database breach exposes no plaintext T1 data.

---

## 4. Code Quality Practices

### ✅ Good — Sentinel Errors With Package Prefixes

```go
// services/budget/errors.go
var (
    ErrNotFound         = errors.New("budget: not found")
    ErrAlreadyApproved  = errors.New("budget: already approved")
    ErrVersionConflict  = errors.New("budget: version conflict")
)
```

Handler switches on `errors.Is()`, maps to gRPC status codes, logs once, never leaks internal details.

---

### ✅ Good — Idempotency Is Structural, Not Bolted On (Rule #5)

```
SQL (via sqlc):
  INSERT INTO journal_entries (..., idempotency_key) VALUES (...)
  ON CONFLICT (idempotency_key) DO NOTHING

Event deduplication:
  INSERT INTO processed_events (event_id) VALUES ($1)
  ON CONFLICT (event_id) DO NOTHING

gRPC client retries (Istio):
  attempts: 3, perTryTimeout: 5s, retryOn: gateway-error,connect-failure
```

---

### ✅ Good — Zero `TODO` / `FIXME` in Go Source

Lint sweeps kept debt out. `2820dcc` fixed 49 findings; `1954fc8` wrapped remaining deferred `rdb.Close` calls. golangci-lint v2 clean.

---

### ✅ Good — Doc-Drift CI Job

`tools/check-doc-drift` runs on every PR. Compares Go identifiers inside ` ```go ` fenced blocks in `thittam_docs` against the application source. Graceful skip if `DOCS_REPO_TOKEN` not set; `d700e15` hoisted the secret check to job-level env.

Closes the v1.1 aspirational "CI should validate" gap.

---

### ⚠️ Bad — No Data-Validation Library

Rule #11 mandates boundary validation at every service handler. Without a library, validation is handwritten per handler — inconsistent and hard to audit.

#### 🔧 How to Improve

```proto
// proto/budget/v1/budget.proto
syntax = "proto3";
import "buf/validate/validate.proto";

message CreateBudgetRequest {
    string name = 1 [(buf.validate.field).string = {
        min_len: 1,
        max_len: 200,
    }];
    string amount = 2 [(buf.validate.field).string = {
        pattern: "^\\d+\\.\\d{2}$"
    }];
    string currency = 3 [(buf.validate.field).string = {
        len: 3  // ISO 4217
    }];
}
```

```go
// gRPC interceptor validates every incoming request
v, _ := protovalidate.New()
if err := v.Validate(msg); err != nil {
    return nil, status.Error(codes.InvalidArgument, err.Error())
}
```

Validation lives in the proto — the single source of truth — enforced automatically by the interceptor for every service.

---

### ⚠️ Bad — Production Status CHECK Is Movie-Production Specific

The production status `CHECK` constraint on tenant status columns is hardcoded to movie-production lifecycle stages. XYZ Construction's seed maps construction stages onto allowed statuses as a workaround.

#### 🔧 How to Improve

Replace the table-level `CHECK` with vertical-aware validation:
1. Remove the CHECK constraint from the migration.
2. In service.go, validate incoming status against `vertical.FromContext(ctx).AllowedStatuses`.
3. Test: XYZ_CBA accepts movie-production statuses, XYZ Construction accepts construction statuses, neither accepts the other.

---

### ⚠️ Bad — `Co-Authored-By: Claude …` in Commits

Conflates tool-assistance with authorship. `Co-Authored-By` has specific meaning in open-source contribution workflows (GitHub Insights, attribution).

#### 🔧 How to Improve

Replace with a distinct tool-attribution trailer:

```
Tool: claude-opus-4-6
```

Or add to the commit body as a descriptive line:

```
Generated with assistance from Claude Opus 4.6.
```

Update Rule #8 in CODING_RULES.md to reflect the new convention.

---

## 5. Testing Practices

### ✅ Good — 1,150 Tests Across 80 Files (v1.1 gap resolved)

3.75× growth from the v1.1 baseline of ~306. Coverage thresholds enforced in CI: `iam` and `ledger` ≥85%, `budget` and `expense` ≥80%, others ≥75%.

---

### ✅ Good — Hand-Written Mocks (Function Field Pattern)

```go
type mockBudgetRepo struct {
    CreateBudgetFn  func(ctx, Budget) (*Budget, error)
    ApproveBudgetFn func(ctx, uuid.UUID) error
}

func (m *mockBudgetRepo) CreateBudget(ctx context.Context, b Budget) (*Budget, error) {
    return m.CreateBudgetFn(ctx, b)
}

// Test:
repo := &mockBudgetRepo{
    ApproveBudgetFn: func(ctx context.Context, id uuid.UUID) error {
        return budget.ErrAlreadyApproved
    },
}
svc := NewService(repo, verticalConfig)
require.ErrorIs(t, svc.ApproveBudget(ctx, id), budget.ErrAlreadyApproved)
```

10 lines of mock, 15 lines of test. No framework. Readable call stack on failure.

---

### ✅ Good — `t.Parallel()` + Deterministic UUIDs

Rule #9 compliance across the unit test corpus. Fixtures use `uuid.MustParse("d1000000-...")` for cross-suite consistency.

---

### ✅ Good — Integration Tests via Testcontainers

Real Postgres + real migrations applied before each test run (`make db-test-bootstrap` + `THITTAM_TEST_DSN`). Transaction rollback per test.

---

### ✅ Good — Playwright E2E Scaffold (New in v1.2)

`web/tests/e2e/` — `smoke.spec.ts`, `budgets-journey.spec.ts` (first business flow), `dashboard.spec.ts`. Playwright auto-boots the web server at `:3100`.

First E2E in the codebase. Correct first journey choice — budgets are the authoring surface.

---

### ⚠️ Bad — E2E Coverage Is Narrow

One business journey (budgets) + smoke. Not enough for GA.

#### 🔧 How to Improve

Before GA, add:

```
web/tests/e2e/
  registration-saga.spec.ts       ← tenant registration end-to-end, incl. failure injection
  expense-approval-ledger.spec.ts ← expense → approval → journal entry visible
  budget-vs-actual-report.spec.ts ← reporting consumer sees approved expenses
  impersonation-audit.spec.ts     ← super_admin impersonates; audit shows dual-actor
  multi-tenant-isolation.spec.ts  ← XYZ_CBA user cannot see XYZ Construction data
```

---

### ⚠️ Bad — Vertical Plugin YAML Has No Dedicated Validator Tests

The platform's core differentiator has a validator (`pkg/vertical/validator.go`) but no exhaustive test suite.

#### 🔧 How to Improve

```
verticals/schema/vertical-schema.json:
  JSON Schema defining required fields, types, patterns, min/max cardinality.

pkg/vertical/validator_test.go:
  TestValidateVertical table-driven:
    - valid film          → ok
    - missing phase_types → error
    - empty budget_cats   → error
    - unknown field       → warn (or error, by policy)
    - load every YAML in verticals/ → all pass
```

Run as a CI step before service tests. A malformed new vertical fails fast, not at runtime in production.

---

### ⚠️ Bad — No Load or Chaos Testing

A platform handling financial operations for productions with multi-million-dollar budgets needs:
- Load tests for double-entry ledger posting at concurrent volume
- Load tests for concurrent expense approvals (bcrypt contention + DB contention)
- Chaos/fault injection via Istio to verify circuit-breaker behaviour
- Resilience tests for NATS consumer failure + DLQ replay

None exist.

#### 🔧 How to Improve

Add a `tests/load/` directory with k6 scripts targeting ledger post-rate, expense-approval throughput, and reporting-service p99 under concurrent load. Run weekly in staging; fail if p99 exceeds documented SLAs.

---

### ⚠️ Bad — Registration Pipeline Has No Saga Rollback Tests

See §1. Cannot test a saga until one is implemented.

---

## 6. Observability Practices

### ✅ Good — Shared gRPC Interceptor Chain

```
pkg/observability/ + pkg/audit/ + pkg/auth/

Every gRPC server uses:
  1. CorrelationID interceptor (generates/propagates correlation_id)
  2. Metrics interceptor (request_duration_seconds, request_total)
  3. Audit interceptor (writes audit_log row for mutations)
  4. Auth resolver (validates JWT, extracts tenant + user claims)

A new service added to the platform gets metrics, correlation IDs, and audit
logging by wiring in pkg/server/server.go.
```

---

### ✅ Good — `/healthz`, `/readyz`, `/metrics` on Every Service

```
/healthz   → liveness (process alive?)
/readyz    → readiness (DB + Redis + NATS + Vault connected?)
/metrics   → Prometheus scrape target

Prometheus scrape target on :9300 (dev-start).
Health/metrics HTTP server on configurable port per service (9090–9099).
```

---

### ✅ Good — Vault Is a `/readyz` Health Checker

`secrets.VaultSource` implements `observability.HealthChecker`. IAM refuses `/readyz` until Vault is reachable — no chance of serving requests without T1 secrets loaded.

---

### ⚠️ Bad — No Circuit Breaker Policy for gRPC Service Failures

```
If general-ledger is down:
  → expense-tracking retries (3 × 5s timeout = 15s per request)
  → approval queue backs up
  → expense-tracking goroutines pile up
  → expense-tracking itself becomes unavailable
  → Cascading failure: one service down → two services down
```

#### 🔧 How to Improve

```yaml
# infra/k8s/general-ledger-destination-rule.yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: general-ledger-circuit-breaker
spec:
  host: general-ledger.thittam.svc.cluster.local
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
    connectionPool:
      http:
        http1MaxPendingRequests: 100
        http2MaxRequests: 1000
```

For each service, document in `docs/operations/circuit-breakers.md`: "If X is unavailable, Y degrades by …". This is the circuit-breaker contract.

---

### ⚠️ Bad — NATS Dead-Letter Strategy Undocumented

```
NATS JetStream: MaxDeliver retries.
After max delivery with no DLQ: event is dropped.
Financial event loss → budget-vs-actual wrong → no alert, no log entry.
```

#### 🔧 How to Improve

```go
js.AddStream(&nats.StreamConfig{
    Name:     "FINANCIAL_DLQ",
    Subjects: []string{"dlq.financial.>"},
    MaxAge:   30 * 24 * time.Hour,
})

js.AddConsumer("FINANCIAL", &nats.ConsumerConfig{
    Durable:    "reporting-analytics",
    MaxDeliver: 5,
    AckPolicy:  nats.AckExplicitPolicy,
    // On MaxDeliver: republish to dlq.financial.<original-subject>
})
```

Prometheus alert: `nats_consumer_dlq_count{stream="FINANCIAL"} > 0` → PagerDuty. Runbook: `docs/operations/nats-dlq-replay.md` — how to inspect, fix, and replay.

---

### ⚠️ Bad — Business-Specific Metrics Are Not Yet Standardised

CODING_RULES.md mentions business-specific metrics "registered per service" but the actual metric names (approval_count, budget_utilization_ratio, etc.) are not documented or enforced.

#### 🔧 How to Improve

`docs/operations/business-metrics.md` lists, per service, the required business metrics with label conventions. Add a test that asserts each service registers its documented metrics.

---

## 7. Documentation Practices

### ✅ Good — 13 ADRs Covering Every Major Decision

ADR-001 through ADR-015 (010/011 missing — see below). Each follows Context → Decision → Rationale with trade-off table → Consequences.

A new team member asking "why gRPC over REST?" reads ADR-003 and gets: the options, the reasons, the trade-offs accepted. No tribal knowledge.

---

### ✅ Good — 71 Markdown Files in `thittam_docs`

Architecture, ADRs, services, verticals, data models, API conventions, deployment, operations, security, compliance, testing.

---

### ✅ Good — 11 Standard Architecture Diagrams Present (Rule #17)

system-design, package-architecture, service-dependency-graph, deployment-diagram, network-security-diagram, database-er-diagram, sequence-diagrams, logical-domain-diagram, ci-cd-pipeline-diagram, nats-event-schemas, proto-service-index.

---

### ✅ Good — Docs Are Fresh

`multi-tenancy.md` updated 2026-04-15 (corrects the isolation model to tenant-per-schema); `demo-xyz-construction-plan.md` drafted 2026-04-15.

---

### ✅ Good — Doc-Drift CI Is Active

`tools/check-doc-drift` runs on every PR in both repos. The v1.1 aspirational "CI should validate" is now real.

---

### ⚠️ Bad — ADRs 010 and 011 Are Missing From Numbering

Readers wonder what the gap is. Either reserved + documented, or renumber.

---

### ⚠️ Bad — Vertical YAML Has No Authoritative Schema File

High-level description exists in docs; no JSON Schema or proto-based schema for the YAML itself. Developers adding a vertical have no formal contract.

#### 🔧 How to Improve

See §5 — pair the schema with the validator test suite.

---

### ⚠️ Bad — Registration Pipeline Compensation Semantics Not Documented

Even without implementation, document what each step's inverse is and what the failure-isolation expectations are. File under `docs/architecture/registration-saga.md` as a precursor to the implementation (ties to §1).

---

## 8. Multi-Tenant & Demo Practices

### ✅ Good — XYZ_CBA Productions Fully Seeded

```
Tenant UUID:     d0000000-0000-0000-0000-000000000001
Vertical:        movie-production
Currency:        INR (India)
Users:           Rajesh Kumar (Owner), Priya Sharma (Exec Producer),
                 Arun Nair (Line Producer), Meena Iyer (Production Accountant),
                 + 4 crew roles
Credentials:     email + "demo1234" (bcrypt cost 12, fixed in 96be1fa)
```

---

### ✅ Good — XYZ Construction LLC Phase A Scaffold (v1.2 new)

```
Tenant UUID:     d0000000-0000-0000-0000-000000000002
Vertical:        construction
Currency:        USD (USA)
Status:          Phase A scaffold complete; UUIDs aligned cross-tenant (79e89c7)
Users:           Miles Sullivan (Owner), Dana Reyes (Director), Ethan Choi (Estimator),
                 Nora Patel (Supervisor), Raj Menon (Finance), Kim Alvarez (Procurement)
Projects:        6 planned (Oakwood Medical Plaza, Riverbend Logistics Hub,
                 Cedar Park Townhomes, Great Lakes Brewery, Huron Valley Water,
                 Midtown Office Renovation) with budget states from draft to locked
```

Cross-tenant UUID alignment enables integration tests that verify isolation between INR and USD tenants on real data.

---

### ⚠️ Bad — XYZ Construction Phase B + C Pending

Phase B (actuals/expenses) and Phase C (approval workflows) are deferred. Until they ship, the construction vertical has no live expense or approval coverage for demos.

---

### ⚠️ Bad — UI Tenant Switcher Absent

Multi-tenant users must log out to switch. Planned post-v1 per `multi-tenancy.md §7`.

---

## 9. Summary Scorecard

```
┌──────────────────────────────────────────────────────────────────────┐
│  Thittam — Practices Scorecard (v1.2)                                │
├────────────────────────────────┬──────────┬──────────────────────────┤
│  Practice                      │  Rating  │  Priority Fix            │
├────────────────────────────────┼──────────┼──────────────────────────┤
│  Vertical plugin system        │  ✅ Good  │  —                       │
│  6-file service layout × 10    │  ✅ Good  │  —                       │
│  gRPC internal / REST external │  ✅ Good  │  —                       │
│  grpc-gateway shadow for auth  │  ✅ Good  │  —                       │
│  All 10 protos defined         │  ✅ Good  │  —                       │
│  sqlc type-safe SQL            │  ✅ Good  │  —                       │
│  buf proto enforcement         │  ✅ Good  │  —                       │
│  Tenant-per-schema safe        │  ✅ Good  │  —                       │
│  T1 secrets Vault → memory     │  ✅ Good  │  —                       │
│  Istio mTLS east-west          │  ✅ Good  │  —                       │
│  Append-only audit schema      │  ✅ Good  │  —                       │
│  Schema injection test suite   │  ✅ Good  │  —                       │
│  Money as decimal.Decimal      │  ✅ Good  │  —                       │
│  Double-entry ledger model     │  ✅ Good  │  —                       │
│  Tenant primary currency       │  ✅ Good  │  —                       │
│  Column-level T1 encryption    │  ✅ Good  │  —                       │
│  Sentinel errors + wrapping    │  ✅ Good  │  —                       │
│  Idempotency structural        │  ✅ Good  │  —                       │
│  Zero TODO/FIXME               │  ✅ Good  │  —                       │
│  Doc-drift CI active           │  ✅ Good  │  —                       │
│  1150 tests / coverage gates   │  ✅ Good  │  —                       │
│  Hand-written mocks            │  ✅ Good  │  —                       │
│  t.Parallel + deterministic    │  ✅ Good  │  —                       │
│  Testcontainers integration    │  ✅ Good  │  —                       │
│  Playwright E2E scaffold       │  ✅ Good  │  —                       │
│  Shared observability interceptor│ ✅ Good │  —                       │
│  /healthz /readyz /metrics     │  ✅ Good  │  —                       │
│  Vault as readyz checker       │  ✅ Good  │  —                       │
│  13 ADRs                       │  ✅ Good  │  —                       │
│  71-file docs repo             │  ✅ Good  │  —                       │
│  11 architecture diagrams      │  ✅ Good  │  —                       │
│  Docs fresh (2026-04-15)       │  ✅ Good  │  —                       │
│  XYZ_CBA fully seeded          │  ✅ Good  │  —                       │
│  XYZ Construction Phase A      │  ✅ Good  │  —                       │
├────────────────────────────────┼──────────┼──────────────────────────┤
│  No registration saga          │  ⚠️  Bad  │  P0 — compensating txns  │
│  audit_log REVOKE not applied  │  ⚠️  Bad  │  P0 — role + REVOKE step │
│  No reporting read model       │  ⚠️  Bad  │  P1 — event-sourced views│
│  Impersonation lifecycle undef │  ⚠️  Bad  │  P1 — TTL + ADR-016      │
│  bcrypt concurrency unbounded  │  ⚠️  Bad  │  P1 — argon2id or semaphore│
│  No protovalidate              │  ⚠️  Bad  │  P1 — proto-level rules  │
│  Production status movie-only  │  ⚠️  Bad  │  P1 — vertical-aware     │
│  NATS per-subject auth undoc   │  ⚠️  Bad  │  P1 — NATS account config│
│  No NATS DLQ documented        │  ⚠️  Bad  │  P1 — DLQ + replay runbook│
│  E2E narrow (1 journey)        │  ⚠️  Bad  │  P1 — 5 critical paths   │
│  Vertical YAML no schema/tests │  ⚠️  Bad  │  P1 — JSON Schema + tests│
│  No circuit breaker policy     │  ⚠️  Bad  │  P1 — Istio DestinationRule│
│  No load / chaos testing       │  ⚠️  Bad  │  P2 — k6 + Istio fault inj│
│  MinIO URL TTL fixed 15min     │  ⚠️  Bad  │  P2 — dynamic TTL        │
│  Business metrics unstandard.  │  ⚠️  Bad  │  P2 — catalogue + tests  │
│  ADR 010/011 missing           │  ⚠️  Bad  │  P3 — fill or renumber   │
│  `Co-Authored-By: Claude`      │  ⚠️  Bad  │  P3 — tool: trailer      │
│  XYZ Construction Phase B/C    │  ⚠️  Bad  │  P3 — ship after core    │
│  UI tenant switcher            │  ⚠️  Bad  │  P3 — post-v1            │
└────────────────────────────────┴──────────┴──────────────────────────┘

P0 = Fix immediately (architectural correctness or security constraint)
P1 = Fix before first production tenants
P2 = Fix before scale
P3 = Fix after launch
```

---

*Analysis based on Go source (thittam), docs (thittam_docs, 71 files, updated 2026-04-15), CLAUDE.md, CODING_RULES.md, 13 ADRs, proto definitions (1,659 LOC, 230 messages), and Playwright E2E scaffold. April 2026.*
