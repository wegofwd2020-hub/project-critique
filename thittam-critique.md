# Thittam — Code Review & Critique

**Reviewed:** April 2026  
**Repos:** `wegofwd2020-hub/thittam` (private — code not directly accessible) · `wegofwd2020-hub/thittam_docs`  
**Phase:** Mid-build  
**Note:** Application code is in a private repo. This review is based on the documentation repo, coding rules, architecture decisions, and structural metadata (file tree, proto index, migration inventory, test counts). Architecture and documentation critique is comprehensive; specific code-level critique is limited to patterns described in docs.  
**Rating key:** ✅ Strong · ⚠️ Gap / Risk · ❌ Critical Issue

---

## Executive Summary

Thittam is the more ambitious of the two projects — a multi-tenant, multi-industry production management SaaS with 9 microservices, gRPC, NATS JetStream, Istio, and a vertical plugin system. The engineering foundations are excellent: the 17 non-negotiable coding rules are well-reasoned, the ADR record (9 decisions) reflects mature architectural thinking, the security model (tenant-per-schema, mTLS, Vault, data classification) is comprehensive, and the documentation quality is genuinely impressive.

The primary risks are ones of ambition outpacing execution. Nine microservices at mid-build, with four proto definitions still pending, creates a large surface area to stabilise before launch. The tenant-per-schema model provides strong isolation but creates operational complexity that scales poorly with tenant count. The 9-step registration pipeline without an explicit saga pattern is a distributed consistency risk. And ~306 tests across 22 packages for a financial platform is below the bar.

The documentation is the strongest aspect of this project — the 17 coding rules alone demonstrate engineering discipline that many teams never codify.

---

## 1. Architecture

### Strengths

- **Vertical plugin system is the right abstraction.** Making the platform industry-agnostic via YAML-driven configuration (entity labels, phase types, budget categories, workflows) is a clever way to serve movie production, construction, software development, and events management without four separate codebases. ADR-007 documents the decision clearly.
- **gRPC for internal communication.** Type-safe, binary, low-latency, contract-enforcing. The decision is justified in ADR-003.
- **NATS JetStream for async patterns.** Better delivery guarantees than bare NATS, with per-consumer acknowledgment and replay. ADR-004 documents the rationale.
- **Kong API Gateway at the edge.** Rate limiting, JWT validation, and routing centralised at the edge before any service sees the request.
- **Istio service mesh for mTLS.** East-west traffic is encrypted and authenticated between services — critical for a financial platform.
- **Tenant-per-schema isolation.** The strongest multi-tenancy model from a data isolation perspective. No risk of cross-tenant data leakage via query bugs.
- **9 ADRs documented.** Architecture Decision Records for language, database, gRPC, events, API gateway, containers, vertical plugins, auth, and platform admin. This is exemplary for a project at this stage.

### Gaps & Risks

⚠️ **Nine microservices at mid-build is likely over-engineered for this stage.** The project has four verticals marked GA (movie production, software development, construction, events management) but is still mid-build. Nine services with separate databases, protos, and deployment units creates a massive coordination surface. A modular monolith with the same domain separation would have shipped faster, been easier to test, and could still be extracted into services later. The gRPC boundaries are correct; the physical separation is premature.

❌ **Four proto definitions are marked "pending."** IAM, GeneralLedger, Notifications, and Document services have `(proto pending)` status. These are not peripheral services — IAM is the authentication and authorisation backbone; GeneralLedger is the financial core. Operating services without formal gRPC contracts means inter-service calls either use REST (inconsistent with the architecture) or are blocked entirely. This is the most critical gap in the project.

⚠️ **Tenant-per-schema creates severe migration overhead.** With 35 migrations already and N tenants, every schema migration must run against `N` schemas. At 100 tenants, this is manageable. At 1000 tenants, a migration that takes 30 seconds per schema takes 8+ hours. A nightly maintenance window cannot absorb this. The migration strategy needs to be designed for multi-schema execution with progress tracking and partial failure recovery before the tenant count grows.

⚠️ **The 9-step registration pipeline is a distributed transaction without a saga.** The pipeline spans multiple services (IAM, Ledger seeding, vertical binding, etc.). If step 4 fails, steps 1–3 have already made writes in different services/schemas. There is no documented compensating transaction strategy. A saga pattern (either choreography via NATS events or orchestration via a dedicated registration orchestrator) is required for correctness.

⚠️ **Reporting-analytics faces a cross-service data fan-out problem.** The service is "read-only" and aggregates data from all other services. Without a dedicated read model (e.g., event-sourced projections, a separate OLAP store, or CQRS), reporting-analytics must either make N gRPC calls per report or maintain its own denormalised copy of data from every other service. Neither approach is documented.

---

## 2. Code Quality

*Based on documented coding rules and architectural patterns, not direct code inspection.*

### Strengths

- **Rule #1 — Money is never a float.** `decimal.Decimal` in Go and `NUMERIC(14,2)` in PostgreSQL. This is the correct choice for a financial platform. Many SaaS products get this wrong and pay for it in rounding bugs at scale.
- **Rule #4 — Interfaces for all external dependencies.** Business logic never calls external services directly. This enables unit testing without real databases or network, and makes the system more resilient to dependency changes.
- **Rule #5 — Idempotency everywhere.** `INSERT ... ON CONFLICT`, event deduplication via `event_id`, idempotency keys on REST POST requests. Correct for a distributed system.
- **Rule #6 — Writes never block reads.** Async cache writes, fire-and-forget NATS publishing with logged failures. Correct for low-latency request paths.
- **Rule #7 — Audit everything that matters.** Append-only audit logs with `actor_id`, `action`, `target_type`, `target_id`, `tenant_id`, `timestamp`, `old_state`, `new_state`, `ip_address`. This is comprehensive and legally defensible.
- **Rule #13 — Structured logging, never `print()`.** Every log entry includes `service`, `method`, `tenant_id`, `request_id`, `level`. PII scrubbing is enforced.
- **Rule #14 — Consistent service structure.** `models.go`, `errors.go`, `repository.go`, `service.go`, `service_test.go`, `handler.go` — every service follows the same layout. This is critical for a multi-service system where developers move between services.
- **Rule #15 — Observability as a first-class concern.** `/healthz`, `/readyz`, `/metrics` on every service. Prometheus metrics with gRPC interceptors. This is the right default.

### Gaps & Risks

⚠️ **Rule #2 ("secrets from environment") contradicts the data-security-rbac doc ("T1 secrets never in env vars — Vault only").** The coding rule says `os.Getenv("JWT_SECRET")` and fail fast; the security doc says T1 data never leaves Vault and never goes in env vars. JWT signing keys are T1 data. The correct pattern is: process startup fetches the secret from Vault and holds it in memory — it should not be in an environment variable that could appear in `/proc/environ`, container inspects, or log output. Resolve this contradiction explicitly.

⚠️ **Rule #16 (guard against documentation drift) relies on "CI should validate" — but no CI implementation is shown.** The word "should" implies intent, not enforcement. For 41+ documentation files across a fast-moving codebase, manual review will not prevent drift. Implement an automated check (e.g., a script that verifies that every public Go function signature mentioned in docs still exists in code) as a real CI step.

⚠️ **Rule #8 embeds `Co-Authored-By: Claude Opus 4.6` in commit messages.** This is non-standard and may cause issues with git tooling (blame, commit-graph analysis, GitHub Insights attribution). It also conflates authorship with tool-assistance. AI-generated commits should use a consistent tag in the commit body, not the `Co-Authored-By` trailer, which has specific meaning in open-source contribution workflows.

⚠️ **No data validation library is mentioned.** Rule #12 requires boundary validation at every service handler, but there is no mention of `go-playground/validator`, `ozzo-validation`, or proto-level field validation (e.g., `google/protobuf/validate`). Without a library, boundary validation is handwritten in each handler — inconsistent and error-prone.

---

## 3. Test Coverage

### Strengths

- **Layered test pyramid is correctly designed.** Unit → Integration → Contract → E2E, with tooling choices documented: `testify`, `testcontainers-go`, `Pact`, `Playwright`.
- **`t.Parallel()` required for all unit tests.** This is the correct default for Go tests.
- **Deterministic IDs and fixed timestamps in fixtures.** Rule #9 prevents flaky tests caused by non-deterministic data.
- **Transaction rollback for integration tests.** Each integration test rolls back, leaving no state pollution.
- **Pact for contract tests.** Service-to-service contract tests catch breaking changes before they reach integration. This is advanced testing practice.
- **~306 tests across 22 packages.** Breadth of coverage across the full service map.

### Gaps & Risks

⚠️ **~306 tests is low for a financial SaaS with 9 services.** At the documented service structure (6 files per service × ~10 tests per file × 9 services = ~540 expected for services alone, plus shared packages), 306 total suggests significant gaps in either unit or integration coverage. The general ledger, expense approval workflow, and tenant registration pipeline should each have 50+ test cases given their financial and correctness requirements.

⚠️ **IAM, Ledger, Notifications, and Document have no proto contracts.** Without formal proto definitions, there are no consumer-driven contract tests (Pact) for these services. This means breaking changes in these services' interfaces go undetected until integration or E2E tests, which run less frequently.

⚠️ **E2E tests run nightly only.** For a B2B SaaS where a regression in budget approval or expense posting could directly impact customers' financial records, nightly is too slow. At minimum, a subset of critical-path E2E tests (tenant registration, budget creation, expense approval, ledger posting) should run on every PR.

⚠️ **No load or chaos testing documented.** A platform handling financial operations for film productions (where a single production budget can be millions of dollars) needs load testing of the double-entry ledger, concurrent expense approvals, and budget utilisation calculations. The Istio service mesh enables chaos injection (fault injection, delay injection) — this should be part of the test strategy before GA.

⚠️ **No test coverage for the vertical plugin system's YAML validation.** The vertical plugin system is the platform's core differentiator. If a malformed vertical YAML is loaded, all vertical-aware services fail. The YAML schema validation should have its own test suite with edge cases (missing fields, invalid phase types, empty budget categories).

---

## 4. Documentation

### Strengths

- **41+ markdown files in `thittam_docs`.** Architecture, ADRs, services, verticals, data models, API conventions, deployment, operations, security, compliance, and testing — the full documentation surface is mapped.
- **Rule #17 mandates 11 standard architecture diagrams.** System design, package/component, service dependencies, deployment, network/security, database ER, sequence diagrams, logical/domain, CI/CD, event schemas, API/proto index — requiring all 11 at defined project milestones is excellent practice.
- **Separate documentation repository (Rule #11).** Code and docs evolve at different cadences. Keeping them in separate repos prevents documentation PRs from blocking code reviews.
- **ADRs explain the why.** Each ADR (ADR-001 through ADR-009) includes context, decision, rationale with trade-off table, and consequences. This is the correct ADR format.
- **Compliance documentation.** `docs/compliance/audit-trail.md` addresses audit requirements. For a financial platform, this is essential.
- **CODING_RULES.md is a first-class document.** 17 non-negotiable rules in a single, readable file. New team members (and AI agents) have clear expectations before writing a line of code.

### Gaps & Risks

⚠️ **Documentation drift is nearly inevitable at this scale.** With 41+ markdown files, 9 services with independent release cycles, and a coding rule that says "CI _should_ validate" (not "CI _does_ validate"), drift will accumulate. Either: (a) implement automated doc validation in CI (parse Go ASTs to verify function signatures match docs), or (b) reduce the documentation surface to what can actually be maintained.

⚠️ **No API versioning strategy for inter-service gRPC contracts.** The proto files are versioned (`/v1/`), but there is no documented policy for how `/v2` protos are introduced, how deprecation is communicated between service teams, or what backward-compatibility guarantees are offered. For a microservices system, proto backward compatibility is a first-class concern.

⚠️ **Webhook documentation exists but NATS delivery failure handling is not specified.** What happens when a NATS consumer fails to process an event after N retries? Is there a dead-letter stream? What is the alerting threshold? For financial events (budget approval, expense posting, ledger journal), silent message loss is a critical risk.

⚠️ **The vertical YAML schema is not documented.** The vertical plugin system is documented at a high level, but there is no schema definition (JSON Schema or protobuf) for the YAML files themselves. A developer adding a new vertical has no authoritative reference for what fields are required, what values are valid, and what happens on validation failure.

---

## 5. Security

### Strengths

- **Data classification tier system (T1–T4).** Clear policy for how each tier of data is handled, encrypted, and access-controlled.
- **Column-level encryption for sensitive fields.** `day_rate` (payroll) and `vendor_gstin` (tax IDs) encrypted at the application layer with AES-256-GCM. This exceeds the baseline for most SaaS platforms.
- **Istio mTLS for all east-west traffic.** No service can call another without a valid client certificate. This prevents lateral movement if one service is compromised.
- **Vault for T1 secrets.** DB passwords, JWT keys, and API keys sourced from Vault, not environment variables (per security doc, even if Rule #2 is inconsistent — see Code Quality).
- **Tenant-per-schema with `search_path` enforcement.** The `BeforeAcquire` hook on the pgx pool ensures every connection is scoped to the correct tenant schema.
- **Append-only audit logs.** Audit rows are never updated or deleted. Legally defensible for financial operations.
- **Network security diagram documented.** Security zones, TLS boundaries, and SOC-2 control mappings are documented.

### Gaps & Risks

❌ **SQL injection risk in tenant schema routing.** The `search_path = tenant_<uuid>` approach involves interpolating a tenant ID into a SQL string. If `tenant_id` is ever sourced from user-controlled input without rigorous UUID validation, this is a schema injection attack. The `BeforeAcquire` hook must validate that the tenant ID is a well-formed UUID before interpolating it into the `SET search_path` command. Document this validation requirement explicitly.

⚠️ **Rule #2 vs. Security doc contradiction on T1 secrets.** See Code Quality. JWT signing keys should never appear in `os.Getenv()` calls — they should be fetched from Vault at startup and held in memory. Resolve this before any security audit.

⚠️ **bcrypt cost 12 for password hashing.** At Go's goroutine concurrency, bcrypt cost 12 takes ~250ms per hash. Under a burst of 100 simultaneous logins, this creates a ~25-second backlog. Consider `argon2id` (better memory-hardness, more efficient with goroutines) or at minimum ensure bcrypt calls are rate-limited per IP to prevent CPU exhaustion via deliberate auth floods.

⚠️ **Platform admin impersonation session lifecycle is not defined.** The platform admin tier supports impersonation (`pkg/platform`). Who can initiate impersonation? How long can an impersonation session last? Is there a maximum duration? Is the impersonated session revoked if the target user changes their password? This needs a documented security model and audit logging that shows impersonation start, every action taken, and impersonation end.

⚠️ **MinIO presigned URLs at 15-minute windows may be too short for large file uploads/downloads.** A film production handling large video dailies or high-resolution asset files may exceed 15 minutes on a slow connection. The URL window should be dynamically set based on file size, with a maximum cap. Alternatively, use a server-side proxy with a session-scoped token rather than presigned URLs.

⚠️ **NATS JetStream authentication model is not detailed in the security docs.** The security doc mentions "TLS + client certificate authentication between services and the broker" but does not specify per-subject authorization (which subjects each service is allowed to publish/subscribe). A compromised `notifications` service should not be able to publish to the `ledger.journal.posted` subject.

---

## 6. Scalability

### Strengths

- **Per-service databases eliminate the single-database bottleneck.** Each service owns its data store. No cross-service database contention.
- **gRPC binary protocol reduces inter-service bandwidth.** Compared to JSON REST, gRPC payloads are typically 3–5× smaller with faster serialisation.
- **NATS JetStream enables decoupled scale.** Producers and consumers scale independently. Backpressure is handled by JetStream's flow control.
- **Kubernetes with HPA documented.** Horizontal Pod Autoscaling based on CPU and custom metrics (Prometheus) is the correct approach for variable load.
- **Istio enables fine-grained traffic management.** Circuit breakers, retries, and canary deployments are available via Istio's `VirtualService` and `DestinationRule`.

### Gaps & Risks

⚠️ **Tenant-per-schema does not scale to thousands of tenants.** PostgreSQL has no hard limit on schema count, but the operational overhead grows linearly: vacuums, migrations, connection pool routing, and schema-aware backup/restore all become harder. Beyond ~500 tenants, a row-level security (RLS) model or a hybrid (per-schema for enterprise, shared-schema for smaller tenants) should be evaluated.

⚠️ **Reporting-analytics aggregates across all service databases.** With per-service databases, the reporting service cannot join across schemas. Options are: (a) each service publishes events that reporting-analytics materialises into its own read model, (b) a separate OLAP database (ClickHouse, DuckDB) consumes events and serves reports, or (c) federated query (complex, slow). None of these is documented. This is the most performance-critical unresolved design decision.

⚠️ **The 9-step registration pipeline is a long-running operation without timeout management.** If the pipeline takes more than a few seconds (likely, given schema creation + ledger seeding + vertical binding), the client must poll for completion status. The pipeline's timeout, retry, and idempotency behaviour needs explicit design and documentation.

⚠️ **No caching strategy is documented for the vertical plugin system.** Each vertical-aware service loads the tenant's vertical config on every request (or is it cached?). If vertical configs are loaded from the database on every gRPC call, this adds a database read to every request. Rule #3 mandates L1 → L2 → L3 caching, but the vertical config is the most-read piece of data in the system and deserves explicit cache documentation.

⚠️ **gRPC load balancing across service replicas requires client-side load balancing.** HTTP/2 multiplexes all requests on a single TCP connection, which means L4 load balancers (standard Kubernetes Services) do not distribute gRPC traffic evenly across replicas. Istio's `DestinationRule` with `ROUND_ROBIN` load balancing solves this — verify this is configured for all service-to-service gRPC calls.

---

## 7. Additional Observations

### DevEx & Tooling

✅ `make new-service name=X` generator is planned (Rule #14). This will reduce the friction of adding services significantly.  
⚠️ The generator is "planned" — until it exists, new services are added by manual copy-paste, which is error-prone.  
⚠️ No mention of local development tooling for the full 9-service stack. Running 9 services + Postgres × 9 + NATS + Redis + Kong + Istio locally is extremely resource-intensive. A `docker-compose.yml` with service mocking (e.g., a stub IAM service) would help.

### SaaS Billing

⚠️ A `billing` service is documented in `docs/services/billing.md` but does not appear in the `cmd/` directory. This service is needed for subscription management, invoicing, and usage metering. Its status (planned, in-progress, blocked?) should be explicitly tracked.

⚠️ Multi-tenancy billing requires usage metering per tenant. The expense and budget volumes per tenant are the natural billing metrics. No instrumentation for this is documented.

### Operational Readiness

✅ `/healthz`, `/readyz`, `/metrics` on every service (Rule #15).  
✅ OpenTelemetry → Grafana stack documented.  
⚠️ 35 migrations with no documented rollback procedure. Each migration should have a `down` migration that is tested.  
⚠️ No circuit breaker policy documented for gRPC service failures. If `general-ledger` is unavailable, which services degrade gracefully and which fail completely?

---

## Priority Actions (Ordered)

| Priority | Action | Area |
|---|---|---|
| P0 | Define protos for IAM, GeneralLedger, Notifications, Document | Architecture |
| P0 | Resolve `SET search_path` tenant ID validation to prevent schema injection | Security |
| P0 | Resolve Rule #2 vs. security doc contradiction (env vars vs. Vault for T1 secrets) | Security |
| P0 | Design and document the saga pattern for the 9-step registration pipeline | Architecture |
| P1 | Document and implement the reporting-analytics read model strategy | Architecture |
| P1 | Validate vertical YAML schema in CI with a dedicated test suite | Testing |
| P1 | Raise test count target to 800+ with explicit thresholds per service | Testing |
| P1 | Add critical-path E2E tests to PR pipeline (not just nightly) | Testing |
| P1 | Document NATS dead-letter strategy for financial events | Documentation |
| P2 | Document the vertical plugin YAML schema (JSON Schema or protobuf) | Documentation |
| P2 | Implement and ship the billing service | Architecture |
| P2 | Evaluate tenant-per-schema scalability beyond 500 tenants; document decision | Scalability |
| P2 | Add load testing for double-entry ledger and concurrent expense approvals | Testing |
| P2 | Document gRPC `DestinationRule` load balancing config for all services | Scalability |
| P3 | Replace bcrypt with argon2id or add per-IP rate limiting on auth endpoints | Security |
| P3 | Implement automated documentation drift detection in CI (Rule #16) | Documentation |
| P3 | Define and document impersonation session lifecycle and revocation policy | Security |
