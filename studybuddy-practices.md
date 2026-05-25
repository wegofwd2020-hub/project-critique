# StudyBuddy OnDemand — Good Practices, Bad Practices & How to Improve

**Document type:** Engineering practices analysis
**Scope:** Backend (FastAPI/Python), Web (Next.js), Mobile (Kivy), Pipeline, Infrastructure
**Period:** 2026-05-24 (v1.5 — alignment with critique v1.5: numbers re-measured; new practices surfaced — additive-RBAC via capabilities table, CONTESTED-status discipline for speculative epics)
**Prior:** v1.4 May 2026 (visual-library wave 1+2, four bug close-outs, PAI removal) · v1.3 April 2026 (Epic 10 / Epic 11 / Streams / Playwright persona expansion)
**Related:** [studybuddy-critique.md](studybuddy-critique.md) · [studybuddy-development-pattern.md](studybuddy-development-pattern.md) · [studybuddy-cost.md](studybuddy-cost.md)
**Rating key:** ✅ Good practice · ⚠️ Bad practice · 🔧 How to improve

> **Note (2026-05-24):** the body below is the v1.4 record, preserved. No documented practice has been overturned. New since v1.4, worth adding to the catalogue:
>
> - **✅ New good practice — additive-RBAC via a dedicated capabilities table.** `teacher_capabilities` (#358, migration 0059, RLS) extends RBAC by *adding* an authoritative table with a two-gate read/act model rather than mutating existing role-grant logic. Same PR also fixed school uploads to write `owner_type='school'` (was defaulting to platform). Pattern reusable for future capability classes.
> - **✅ New good practice — CONTESTED status stamp on speculative epics.** Epic 17 (corporate-L&D fork) was stamped `CONTESTED` after advisor pushback rather than silently dropped or deleted. Healthy discipline — keeps the speculative-epic visible-but-on-hold rather than invisible-but-lurking. Recommend extending the formal epic-status vocabulary alongside DELIVERED / IN-PROGRESS / DEFERRED.
> - **✅ Carried forward — zero TODO/FIXME/XXX in `backend/src` + `pipeline`.** Holds at 1,030 backend tests / 73 files. The "no TODO debt" practice scales — this is no longer just a small-codebase artefact.
> - **✅ Carried forward — operational-gotcha retirement before launch.** The `seed_library_local.py` docker-cp dance was retired by `./scripts:/app/scripts-repo:ro` + `./sample_content:/app/sample_content:ro` bind mounts; the resolver-eval Voyage-rate-limit KeyError was retired by mirroring the success-path schema in the error branch. Practice: each operational gotcha is closed with code, not with a runbook entry.
> - **⚠️ Carried forward — visual-library promotion CI still gated on AWS secrets.** Library content is seeded locally via `seed_library_local.py` rather than the production path. Fine for resolver evaluation; a divergence to retire before launch.
> - **⚠️ Carried forward — `APP_ENV` not asserted against a valid enum at startup, slowapi/Redis limiter coexistence, pool-arithmetic warn-not-assert, absent load/perf tests, a11y-weighted E2E.** None touched in the v1.4 → v1.5 window.
>
> Re-measured: 1,030 backend tests / 73 files, 17 Playwright specs / 2,781 LOC, 59 migrations (latest 0059). See [studybuddy-cost.md](studybuddy-cost.md) for the real-world cost-of-time-and-money analysis of the practices catalogued below.

---

## Table of Contents

1. [Architecture Practices](#1-architecture-practices)
2. [Security Practices](#2-security-practices)
3. [Performance Practices](#3-performance-practices)
4. [Code Quality Practices](#4-code-quality-practices)
5. [Testing Practices](#5-testing-practices)
6. [Data Practices](#6-data-practices)
7. [Content & Pipeline Practices](#7-content--pipeline-practices)
8. [Operational Practices](#8-operational-practices)
9. [Summary Scorecard](#9-summary-scorecard)

---

## 1. Architecture Practices

### ✅ Good — Three Runtime Contexts Are Hard-Separated

The separation of Pipeline / Backend / Client is enforced by convention and documented as a security boundary. No client holds an API key. No backend generates content on the request path.

```
GOOD: Context boundary enforcement

  ┌──────────────────────────────────────────────────────────────────┐
  │  Context 1: Pipeline (offline)                                    │
  │                                                                   │
  │  build_grade.py ──▶ Anthropic API ──▶ Content Store (S3/local)   │
  │                                                                   │
  │  Keys present: ANTHROPIC_API_KEY, TTS_API_KEY                    │
  │  Keys absent:  STRIPE_*, JWT_*, DATABASE_URL                     │
  └──────────────────────────────────────────────────────────────────┘
             ↕ no runtime connection
  ┌──────────────────────────────────────────────────────────────────┐
  │  Context 2: Backend API (always-on)                               │
  │                                                                   │
  │  FastAPI ──▶ PostgreSQL + Redis + Content Store (read-only)      │
  │                                                                   │
  │  Keys present: STRIPE_*, JWT_*, DATABASE_URL, REDIS_URL           │
  │  Keys absent:  ANTHROPIC_API_KEY (never called at runtime)       │
  └──────────────────────────────────────────────────────────────────┘
             ↕ REST/HTTPS only
  ┌──────────────────────────────────────────────────────────────────┐
  │  Context 3: Clients (user device)                                 │
  │                                                                   │
  │  Next.js / Kivy ──▶ Backend REST API                             │
  │                                                                   │
  │  Keys present: none                                               │
  └──────────────────────────────────────────────────────────────────┘
```

---

### ✅ Good — Pre-Generation Model Eliminates Per-Student Latency

Offline pipeline runs; content stored; request path serves pre-generated JSON from Redis/S3. Deterministic latency, cost does not scale with students, Anthropic outage ≠ student outage.

---

### ✅ Good — `StorageBackend` Abstraction Decouples Dev From Prod

```
src/core/storage.py (283 LOC)

  class StorageBackend(ABC):
      async def read(self, path: str) -> bytes: ...
      async def write(self, path: str, data: bytes) -> None: ...
      async def presigned_url(self, path: str, ttl: int) -> str: ...

  class LocalStorage(StorageBackend):
      """Dev — all I/O via asyncio.to_thread to avoid blocking."""
      ...

  class S3Storage(StorageBackend):
      """Production — boto3 via thread executor; pre-signed URLs for audio."""
      ...

Selected at startup by STORAGE_BACKEND env var. Callers pass relative paths only —
implementations translate to filesystem paths or S3 keys internally.
```

Horizontal scaling is now a configuration change, not an architecture change.

---

### ✅ Good — Application Factory Pattern

`src/core/app_factory.py` owns lifespan, middleware, exception handlers, and router registration. `main.py` is a 5-line entrypoint that calls `create_app()`. No `# noqa: E402` circular-import workarounds anywhere.

Testable — tests call `create_app()` with custom settings. Production and test share the same construction path.

---

### ✅ Good — Epic 10 Governance Layer Separates Platform Content From School Content

```
Platform library (owner_type='platform')
  ├── Seeded default curricula (Grades 5–12, all languages)
  ├── RESTRICTIVE RLS on curricula (migration 0046):
  │     INSERT/UPDATE/DELETE refused unless app.current_school_id='bypass'
  └── SELECT remains permissive — schools read the library freely

School library (owner_type='school')
  ├── Schools upload custom curricula
  ├── Schools own their retention lifecycle
  └── Archive gated by is_curriculum_in_use() against grade_curriculum_assignments

Archive/unarchive flow:
  POST /admin/curricula/{id}/archive       ← platform super-admin
  POST /schools/{school_id}/curricula/{id}/archive  ← school admin
  POST /admin/curricula/{id}/unarchive
  GET  /admin/curricula/{id}/usage         ← {in_use, active_students, active_teachers}

Audit:
  curriculum.archive, curriculum.archive_by_platform_admin,
  curriculum.unarchive, curriculum.hard_delete_by_sweeper
```

The governance model is clean and defensible for SaaS procurement review.

---

### ✅ Good — Streams As Soft-Registry

```
streams table (migration 0045, 5 system seeds):
  science, commerce, humanities, english, stem

No FK from curricula — rename/merge is a data action, not a schema migration.
Reserved codes: {none, other, all, default, null}
Upsert on upload: /admin/pipeline/trigger?stream_display_name=... auto-creates.
Merge endpoint: POST /admin/streams/{code}/merge → moves curricula, archives source.
```

Soft registries are exactly right for evolving taxonomies. Curriculum identity remains stable; stream identity is fluid.

---

### ⚠️ Bad — Mobile/Web Capability Boundary Is Still Undocumented

As Epic 3 (Path B — Expo/React Native student mobile) activates, decisions about which client owns which feature will accumulate ad hoc.

#### 🔧 How to Improve

Write `studybuddy-docs/CLIENT_BOUNDARY.md` before Epic 3 activates. Cover: where subscription management lives, how deep-links bridge mobile → web, what the mobile offline model covers and what it excludes, how teacher features are gated out of the student mobile app.

---

### ⚠️ Bad — No API Versioning or Deprecation Policy

With a mobile client that users may not update promptly, the first `/api/v2` change without a policy will cause incidents.

#### 🔧 How to Improve

```
ARCHITECTURE.md — Add section "API Versioning":

  Version support window: 6 months after the next major version ships
  Deprecation mechanism: X-API-Deprecated: true header on /api/v1 responses
  Mobile upgrade check: GET /api/version-check?client=mobile&version=1.3.0
                       Response: {"min_supported", "latest", "update_required",
                                  "deprecation_date"}
  Sunset gate: CI fails if a /api/v1 route is removed before deprecation_date.
```

---

### ⚠️ Bad — L-6 TTL Sweeper Deferred; Archived Curricula Accumulate

The retention_status='archived' CHECK and partial index exist (migration 0047). The background sweeper does not — L-6 was paused deliberately.

#### 🔧 How to Improve

Implement the sweeper as a Celery Beat task on the `pipeline` queue. Gate on `hard_delete_by_sweeper` audit event. Default retention: 365 days after archive.

---

## 2. Security Practices

### ✅ Good — Two-Track Authentication with Separate Secrets

Student/teacher Auth0 → internal JWT (`JWT_SECRET`); admin local bcrypt → admin JWT (`ADMIN_JWT_SECRET`). Pydantic `secrets_must_differ` validator prevents them being the same value. A student JWT presented to an admin endpoint fails signature verification (wrong secret), not merely role check.

---

### ✅ Good — Forgot-Password Always Returns 200

Email enumeration attack is impossible. Both valid and unknown emails get the same 200 with the same neutral message.

---

### ✅ Good — Stripe Webhook Signature Verification + Idempotency + SCA Handling

```
Layer 1: construct_event() verifies signature with STRIPE_WEBHOOK_SECRET
Layer 2: SELECT 1 FROM stripe_events WHERE event_id = $1 — dedup
Layer 3: invoice.payment_action_required → send_payment_action_required_email_task
         → school admin receives hosted_invoice_url for 3DS completion
```

---

### ✅ Good — COPPA/FERPA Controls Are Codified

```
web/lib/compliance.ts (242 LOC):
  COPPA (Children's Online Privacy Protection Act) — under-13:
    ├── Parental consent flow — account_status='pending' → /consent
    ├── Data minimisation — name, email, grade, locale only
    ├── No location, no fingerprinting, no third-party trackers
    └── 90-day automatic deletion on consent not granted

  FERPA — cross-school isolation:
    PostgreSQL RLS on 7 tables (migration 0028)
    SET LOCAL app.current_school_id = <jwt.school_id>
    → SELECT * FROM teachers returns only this school's rows

  GDPR — right to erasure:
    delete_auth0_user() + purge_student_data()
```

Closes the v1.2 "COPPA is implicit, not documented" gap.

---

### ✅ Good — JWKS TTL Is Enforced

```
from cachetools import TTLCache
jwks_cache = TTLCache(maxsize=10, ttl=JWKS_CACHE_TTL_HOURS * 3600)
```

Revoked signing keys are evicted automatically. Key rotation handled (re-fetch on not-found once before failing).

---

### ✅ Good — Rate Limiting on Auth (Redis-Backed)

`src/core/rate_limit.py` — `ip_auth_rate_limit` dependency (10 req/60 s per IP) via Redis INCR/EXPIRE. Correctly uses `Depends()` to avoid the slowapi/Pydantic v2 decorator incompatibility. State is shared across workers.

---

### ✅ Good — Auth0 Management Token Cached

23h Redis TTL (1h buffer before Auth0's 24h expiry). Auto-evict and retry on 401.

---

### ✅ Good — RLS Extended to Curricula for Platform-Write Protection

Migration 0046 adds three RESTRICTIVE RLS policies on `curricula` refusing INSERT/UPDATE/DELETE on `owner_type='platform'` rows unless the session variable is `'bypass'`. Schools cannot modify platform curricula even if the application path is bypassed.

---

### ⚠️ Bad — `APP_ENV` Is Not Asserted Against a Valid Enum at Startup

```
BAD: Silent defaulting to 'development'

  app_factory.py:
    if settings.APP_ENV == "development":
        app.include_router(dev_router)  ← dev endpoints live

  If APP_ENV is unset or mistyped in a staging/production deploy:
  → Pydantic Settings default kicks in (or fails softly)
  → Dev router is live in production
  → /dev/reset-db, /dev/impersonate, /dev/seed-school are exposed
```

#### 🔧 How to Improve

```python
# app_factory.py — one-line hardening

def create_app() -> FastAPI:
    if settings.APP_ENV not in ("development", "staging", "production"):
        raise RuntimeError(
            f"APP_ENV must be 'development', 'staging', or 'production'; "
            f"got {settings.APP_ENV!r}"
        )
    ...
```

---

### ⚠️ Bad — Slowapi + Redis Rate-Limit Coexist

The Redis-backed `ip_auth_rate_limit` dependency is correct and shared across workers. `src/core/limiter.py` (slowapi) remains in-process. Under a four-worker deployment, any endpoint protected only by slowapi can be bypassed 4× (40 req/min instead of 10).

#### 🔧 How to Improve

```
1. Audit every auth-facing route — which limiter is in force?
2. Migrate all auth routes to the Redis-backed dependency.
3. Either remove slowapi from main.py, or restrict it explicitly to
   non-critical, non-auth endpoints (e.g., /health, /metrics).
4. Add an E2E test:
   - 4 parallel workers
   - 10 requests per worker to /auth/login
   - Assert: 10 succeed, 30 receive 429 (Redis-backed)
```

---

### ⚠️ Bad — Pool Arithmetic Is Warn-Not-Assert

`DATABASE_POOL_MAX × WORKER_COUNT` vs `PGBOUNCER_POOL_SIZE` is logged at startup but does not fail startup when misconfigured. Under silent misconfiguration, connection exhaustion occurs after cache warmup.

#### 🔧 How to Improve

```python
# backend/src/config.py

class Settings(BaseSettings):
    DATABASE_POOL_MAX: int = 20
    GUNICORN_WORKERS: int = 4
    PGBOUNCER_POOL_SIZE: int = 50

    @model_validator(mode="after")
    def validate_pool_arithmetic(self) -> "Settings":
        total = self.DATABASE_POOL_MAX * self.GUNICORN_WORKERS
        if total > self.PGBOUNCER_POOL_SIZE:
            max_allowed = self.PGBOUNCER_POOL_SIZE // self.GUNICORN_WORKERS
            raise ValueError(
                f"Pool overflow: {total} conns requested, PgBouncer max is "
                f"{self.PGBOUNCER_POOL_SIZE}. Set DATABASE_POOL_MAX ≤ {max_allowed}."
            )
        return self
```

---

### ⚠️ Bad — No CSP or HSTS Verified

For a platform serving minors, CSP is a baseline requirement. These live in nginx/ALB configuration, not application code, but their presence should be verified and documented.

#### 🔧 How to Improve

Add `infra/nginx/security_headers.conf` to version control. Reference it from the main nginx config. Document in `PRODUCTION_DEPLOYMENT.md`.

---

### ⚠️ Bad — DEV_ACCOUNTS.md Location Verification Outstanding

Git tag `dev-accounts-repair-2026-04-14` exists, indicating remediation occurred. Confirm the file is redacted or in a private location before the next docs-repo publish.

---

## 3. Performance Practices

### ✅ Good — Hot Read Path Touches Zero DB on Cache-Warm Requests

```
GET /api/v1/content/{unit_id}/lesson
  → JWT verify (in-process, ~0.1ms)
  → L1 TTLCache: ent:{student_id} hit? → entitlement confirmed
  → L1: content:{unit_id} hit? → return JSON (~1 ms total)
  → (otherwise) L2 Redis, then L3 Postgres (~5–15 ms)

Target: 95% cache hit rate, <20 ms p99.
```

---

### ✅ Good — bcrypt Runs in an Executor

`hash_password` and `verify_password` dispatch via `loop.run_in_executor()`. Event loop free during hashing.

---

### ✅ Good — Audio Is Never Proxied Through the API

`GET /api/v1/content/{unit_id}/lesson/audio` returns a pre-signed CloudFront URL (1 DB/cache lookup). Client fetches MP3 bytes directly from CDN. API worker free in <5 ms.

---

### ✅ Good — Stripe Calls Are Non-Blocking

```
src/core/stripe_async.py:
    async def run_stripe(fn, *args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, functools.partial(fn, *args, **kwargs))
```

Used consistently throughout `subscription/router.py`. Event loop free during Stripe HTTP round-trips.

---

### ✅ Good — Pipeline `--stream` Flag Reduces Peak Memory

C-5 added a streaming mode to `build_grade.py`. With `max_tokens` raised from 8192 to 16384 to prevent mid-JSON truncation on rich content, streaming keeps peak memory from following the token cap.

---

### ⚠️ Bad — No Load or Performance Tests

`SCALABILITY.md` projects request volumes; there are no k6, Locust, or wrk scripts. S3 path, Redis cache hit rates under concurrent load, Celery queue depth under peak pipeline runs, and the `--stream` mode's steady-state memory profile are all theoretical.

#### 🔧 How to Improve

```
tests/load/ (new directory)

  scenarios/
    student_content_fetch.js        ← 500 concurrent lesson fetches/min
    auth_exchange.js                ← 100 concurrent Auth0 exchanges/min
    subscription_checkout.js        ← 20 concurrent Stripe checkouts/min
    pipeline_stream_mode.py         ← regenerate Grade 12 math with --stream,
                                      observe resident memory + duration

CI: run weekly on a staging environment; fail if p99 latency > SCALABILITY.md target.
```

---

## 4. Code Quality Practices

### ✅ Good — Structured Logging With Correlation IDs

Every log entry carries `service`, `method`, `correlation_id`, `level`. CloudWatch query by `correlation_id` returns the full request trace across workers.

---

### ✅ Good — Sentry PII Scrubbing Is Explicit

`_before_send` strips `data`, `email`, `password`, `token`, `refresh_token`, `id_token` before sending to Sentry.

---

### ✅ Good — `_verify_auth0_token` Is Deduplicated

Single `_verify_auth0_token(id_token, audience)` helper; student and teacher paths differ only in the `audience` argument. Bugs fixed in one function cannot silently diverge.

---

### ✅ Good — `upsert_student` Handles `account_status` Correctly

```sql
ON CONFLICT (email) DO UPDATE SET
    name = EXCLUDED.name,
    grade = EXCLUDED.grade,
    locale = EXCLUDED.locale,
    account_status = CASE
        WHEN students.account_status = 'suspended' THEN 'suspended'
        WHEN students.account_status = 'pending'
             AND EXCLUDED.account_status = 'active'  THEN 'active'
        ELSE students.account_status
    END
```

Suspended is preserved; pending → active on re-registration without consent requirement.

---

### ✅ Good — Application Factory + 5-Line main.py

All `# noqa: E402` workarounds eliminated. Router imports happen inside `create_app()` after module loading is complete.

---

### ✅ Good — Zero TODO/FIXME/XXX in Source

Recent lint sweeps kept debt out of `backend/`, `pipeline/`, `web/`, `mobile/`.

---

### ⚠️ Bad — Docstring Style Is Inconsistent

NumPy-, Google-, and prose-style docstrings coexist. This blocks automated API doc generation.

#### 🔧 How to Improve

Pick one style (recommend Google — best Sphinx/mkdocs support) and run a one-time migration via `docformatter` or a custom transform. Enforce with a Ruff rule (`D` family) in pre-commit.

---

### ⚠️ Bad — No Semver Enforcement on API Surface

The OpenAPI → TypeScript drift check catches contract drift but does not fail a PR that removes a `/api/v1` route.

#### 🔧 How to Improve

Add a route-existence test. Snapshot the OpenAPI `paths` list on every main merge; fail any PR that removes a path without an accompanying `X-API-Deprecated` marker.

---

## 5. Testing Practices

### ✅ Good — Real Postgres in CI via Alembic

Schema drift caught before production. `alembic upgrade head` applies all 48 migrations before pytest runs.

---

### ✅ Good — Token Factory Pattern

Deterministic JWTs via `tests/helpers/token_factory.py`. No Auth0 network call in CI.

---

### ✅ Good — Per-Module Coverage Thresholds

`scripts/check_coverage_thresholds.py` with longest-prefix-wins matching:

```
src/auth/                  → 90%
src/subscription/          → 90%
src/school/subscription/   → 90%
src/content/               → 85%
default                    → 80%
```

Enforced in CI after pytest. Much stronger than the old flat 70% floor.

---

### ✅ Good — RLS Isolation Tests

`test_rls.py` uses deterministic school UUIDs and a single connection with `SET LOCAL app.current_school_id`. Verifies that School A cannot see School B's rows.

---

### ✅ Good — Playwright E2E Suite Has Broadened

16 spec files, 2,620 LOC total:

| Category | Specs |
|---|---|
| Landing / public | landing (191 LOC), public pages (201 LOC) |
| Auth | login + redirects + school/student flows (73+111+77+25+25 LOC) |
| Persona accessibility | student-accessibility (276), teacher-accessibility (319), admin-accessibility (232), school-admin-curriculum-flow (327) |
| Admin portal | 228 LOC |
| Pricing | 130 LOC |
| Student critical path | 293 LOC — landing → curriculum map → lesson → quiz → result → history |

Status: 35/35 persona + 86/86 chromium-project specs passing; 6 `fixme`'d in `school-admin-curriculum-flow` tracked in issue #188.

---

### ⚠️ Bad — E2E Coverage Is Weighted Toward Accessibility

Persona specs predominantly assert axe-rule compliance and structural presence. Functional teacher flows (roster management, reports, alerts) and school admin flows (subscription, billing, content review) have specs only at the accessibility layer.

#### 🔧 How to Improve

```
tests/e2e/functional/
  teacher_roster_management.spec.ts
  teacher_reports.spec.ts
  school_admin_subscription.spec.ts
  school_admin_content_review.spec.ts
  school_admin_curriculum_submission.spec.ts   ← unfixme issue #188

Each spec: full user journey, real form submission, real backend state change,
assert on downstream visible effect (not just page render).
```

---

### ⚠️ Bad — 3 Axe Rules Disabled

`color-contrast`, `html-has-lang`, `document-title` — issue #189. These are high-weight rules for school-district procurement.

#### 🔧 How to Improve

Fix each rule, then remove the disable. Add a Playwright axe-config diff test that fails if a rule is re-disabled without explanation in the config comment.

---

### ⚠️ Bad — Mobile UI Screens Are Not Tested

Mobile logic (EventQueue, LocalCache, SyncManager, i18n) is covered. Kivy screens are not.

#### 🔧 How to Improve

Evaluate whether Kivy remains the student mobile path given Epic 3 Path B selection. If yes, add `pytest-kivy` screen tests for `CurriculumMapScreen`, `SubjectScreen`, `QuizScreen`. If Path B activates, this gap closes itself via Playwright against the Expo web dev build.

---

### ⚠️ Bad — No Cross-Client Auth Continuity Tests

A student using both mobile and web must share JWT refresh behaviour, subscription entitlements, and progress state. No dedicated coverage.

---

## 6. Data Practices

### ✅ Good — PostgreSQL Row-Level Security for Tenant Isolation

Migration 0028 enabled RLS on 7 tables with a `tenant_isolation` policy. `get_db()` stamps `app.current_school_id` per request. Fixtures use a `'bypass'` value for test isolation.

```
Without RLS: SELECT forgets WHERE school_id = $1 → cross-tenant leak.
With RLS:    SELECT returns this school's rows only, regardless of WHERE.
```

---

### ✅ Good — RLS Extended to Curricula (Migration 0046)

Three RESTRICTIVE RLS policies refuse mutations on `owner_type='platform'` rows unless the session is super-admin. SELECT remains permissive so schools can still read the library.

---

### ✅ Good — Streams Table Is a Soft-Registry

No FK from `curricula`. Rename/merge is a data action. `streams_router.py` validates codes, gates on reserved codes, and recomputes curriculum-count on merge/archive.

---

### ✅ Good — Migration History Is Legible

48 numbered migrations, each with a business-level name. Recent examples:

| Migration | Delivered |
|---|---|
| 0043 | Epic 1 — `provider` column on content_subject_versions + pipeline_jobs |
| 0044 | Epic 8 — nullable stream_code on curricula, students, teachers |
| 0045 | Epic 8 — streams registry (5 system seeds) |
| 0046 | Epic 10 L-1 — RESTRICTIVE RLS on curricula (platform write-guard) |
| 0047 | Epic 10 L-3 — retention_status='archived' CHECK + partial index |
| 0048 | Hotfix — drop stale RLS from L-1 debug draft |

---

### ⚠️ Bad — No Documented Alembic Downgrade Testing

With 48 migrations, the rollback path for the most recent migration should be verified before each production deploy.

#### 🔧 How to Improve

Add a CI job on PRs that touch `alembic/versions/`:

```
1. alembic upgrade head
2. alembic downgrade -1
3. alembic upgrade head
4. Run a small smoke test suite against the final schema.
```

Fails any PR whose `down` migration is broken.

---

## 7. Content & Pipeline Practices

### ✅ Good — Universal + Per-Subject Prompt Guidelines (C-1, C-2)

```
pipeline/prompts.py (465 LOC):

  Universal block (injected into every prompt):
    ├── GFM tables with alignment markers for comparisons, timelines, numeric data
    ├── LaTeX delimiters ($...$ inline, $$...$$ display) for equations
    ├── Currency escaping: \$ or spell out currency code
    ├── Fenced code blocks
    └── Attributed blockquotes (em-dashed, no invented citations)

  Per-subject block (keyed by subject):
    ├── Commerce: Balance Sheet, P&L, Trial Balance as markdown tables;
    │             accounting equations as KaTeX
    ├── Natural Sciences: formulae, reaction mechanisms, stoichiometry tables,
    │                     periodic-table excerpts, Punnett squares
    ├── Mathematics: every expression in KaTeX
    └── CS: truth tables, Big-O notation
```

---

### ✅ Good — Shared `SBMarkdown` Component (C-3)

`web/components/content/Markdown.tsx` (119 LOC) consolidates four inline `<ReactMarkdown>` copies. Plugins: `remark-gfm`, `remark-math`, `rehype-katex`. Styling: tables zebra-striped, numeric cells `font-mono` + `tabular-nums`, blockquotes left-border italic, code blocks gray + scroll.

One component, one surface to style, one surface to audit for rendering bugs.

---

### ✅ Good — Content Format-Drift Validator (C-6)

`pipeline/content_format_validator.py` emits `format_drift` warnings when a section title (e.g., "Balance Sheet", "Chemical Equation") suggests tabular/formula content but the output lacks tables or KaTeX. Part of pipeline quality gates before content-store write.

---

### ✅ Good — Attributed-Quote Discipline (C-9)

Universal prompt block: only widely-documented, verifiable statements; no invented citations; no living people or post-2000 sources; strict format `> Quote\n> — Name`. Web renderer styles blockquotes consistently.

This is hard to get right with LLMs. Codifying the rule in the prompt — rather than hoping the model behaves — is the correct move.

---

### ✅ Good — Helpers-Toolkit + Declarative SidecarSpec for Visual-Library Authoring (Wave 1+2)

The visual-library expansion (Epic #326, May 2026) shipped 10 sub-issues against a single shared template: every per-subject generator script (`generate_<class>_visuals.ts`, 470–790 LOC each) imports the same micro-helpers — `svgWrap`, `write`, `makePlot`, `plotPolyline`, `mkdirSync` recursively — from a thin shared module, then encodes class-specific knowledge as **module-local primitive functions** (e.g., `wire`, `node`, `resistor`, `batteryCell` for circuits; `zigzagPoints`, `singleBond`, `doubleBond` for organic chem). The same primitives lift into Remotion clips verbatim — `secantLine` from the derivatives generator becomes the Remotion `<SecantLine>` scene component.

`scripts/seed_library_sidecars.ts` is the **single declarative source** for the library: a `SidecarSpec[]` array, one entry per asset, fed into the generator at the bottom of each script. Catalogue grew from ~50 to 144 entries in the wave.

#### Why this is good

- **Adding a new subject class is bounded.** Author the generator (catalogue + Remotion lifts), append SidecarSpec entries, write 8–10 eval JSONL records, run `seed_library_local.py`. Wave-2 issues averaged ~45 min wall time.
- **Authoring rules are enforced at one point**, not 10. The closed enum (subject, kind, license), filename regex, and metadata-yaml schema all live in `promote_library_metadata.py`; both the production CI and the dev seeder reuse it via `importlib.util.spec_from_file_location` — no drift possible.
- **Eval coverage scales with the catalogue.** 80 records produced gradient evidence on resolver precision/recall over a representative subject mix.

#### Caveats to retire before launch

- Dev seeding still uses `local://` fake `s3_path` values — production promotion (`promote_visual_library.yml`) will UPSERT the same rows with real S3 keys. Confirm the resolver doesn't dereference `s3_path` in any code path before launch (it doesn't today, per the seeder docstring).
- Voyage free tier (3 RPM) caused 7 errored seedings in a 80-record run; `_embed_with_backoff` in the seeder + `n_errored` in `run_resolver_eval.py` make these soft-fails. A paid Voyage key removes the throttle entirely.

---

### ⚠️ Bad — Regen Is In Flight; Content Presentation Is Uneven Across Grades

C-5 (`--stream` flag + regen) is mid-execution. Grade 11 Commerce done; Grade 11 Science resuming; Grade 12 + maths-heavy pending.

#### 🔧 How to Improve

Track regen status in `docs/epics/INDEX.md` with last-regenerated-date per grade × subject. Surface in admin UI so operators know which content is on the new format vs legacy.

---

### ⚠️ Bad — C-7 (PDF Smoke) and C-8 (Mobile KaTeX Parity) Not Shipped

PDF export may collapse on rich content; Kivy mobile renderer may not handle KaTeX + tables.

#### 🔧 How to Improve

Before the Kivy mobile app re-opens to real students, verify that a smoke set of lessons (one per subject) renders acceptably on the Kivy side. If KaTeX is infeasible in Kivy, fall back to pre-rendered PNG for equations in the mobile content bundle.

---

## 8. Operational Practices

### ✅ Good — Health and Metrics Endpoints

`/health` (liveness), `/metrics` (Prometheus). Metrics exposed: request duration histograms by endpoint/method/status, cache hit totals by level, Celery task duration, content served by grade/subject/lang, Stripe webhook processed by event type.

---

### ✅ Good — Dependabot + pip-audit + Snyk + Ruff + Bandit + detect-secrets

CVE surface actively managed. Layered scanning (SAST, dependency, secret).

---

### ✅ Good — SBOM Generated Per CI Run

Syft produces SPDX + CycloneDX. Retained 90 days. Useful for school-district procurement review.

---

### ✅ Good — Celery Beat SPOF Resolved

RedBeat stores schedule state in Redis. Primary + standby Beat instances compete for a Redis lock; failover is automatic within one `REDBEAT_LOCK_TIMEOUT` window.

---

### ✅ Good — API Contract Drift Check

OpenAPI → TypeScript type re-gen on every PR. Silent backend/frontend contract drift is caught in review.

---

### ⚠️ Bad — No Runbooks for Common Failure Scenarios

When DB exhausts / Redis OOMs / Stripe webhook backs up / Beat lock expires / pipeline fails / `--stream` mode OOMs — on-call investigates from scratch.

#### 🔧 How to Improve

Write 6 runbooks in `OPERATIONS.md`, one per failure mode. Template: Symptoms, Diagnosis (exact commands), Immediate mitigation, Root-cause fixes, Recovery validation. 30–60 min per runbook. The first time one is used pays for it.

---

### ⚠️ Bad — No `Makefile`

`make test`, `make lint`, `make migrate`, `make seed` would lower onboarding friction. Today contributors read `docker-compose.yml` and `dev_start.sh` to figure out commands.

---

### ⚠️ Bad — Stripe Test → Live Key Rotation Process Is Undocumented

Before the first paying school, the live-key rollout procedure must exist.

---

## 9. Summary Scorecard

```
┌──────────────────────────────────────────────────────────────────────┐
│  StudyBuddy OnDemand — Practices Scorecard (v1.3)                    │
├─────────────────────────────┬──────────┬────────────────────────────┤
│  Practice Area              │  Rating  │  Priority Fix               │
├─────────────────────────────┼──────────┼────────────────────────────┤
│  Three-context separation   │  ✅ Good  │  —                         │
│  Pre-generation model       │  ✅ Good  │  —                         │
│  StorageBackend abstraction │  ✅ Good  │  —                         │
│  Application factory + main │  ✅ Good  │  —                         │
│  Epic 10 governance layer   │  ✅ Good  │  —                         │
│  Streams soft-registry      │  ✅ Good  │  —                         │
│  Two-track auth + secrets   │  ✅ Good  │  —                         │
│  Forgot-password 200        │  ✅ Good  │  —                         │
│  Stripe sig + idem + SCA    │  ✅ Good  │  —                         │
│  COPPA/FERPA codified       │  ✅ Good  │  —                         │
│  JWKS TTL enforced          │  ✅ Good  │  —                         │
│  Redis-backed auth limiter  │  ✅ Good  │  —                         │
│  Auth0 mgmt token cached    │  ✅ Good  │  —                         │
│  RLS (0028) + 0046 extend   │  ✅ Good  │  —                         │
│  Hot read path caching      │  ✅ Good  │  —                         │
│  bcrypt in executor         │  ✅ Good  │  —                         │
│  Audio via CDN              │  ✅ Good  │  —                         │
│  Stripe async wrapper       │  ✅ Good  │  —                         │
│  Pipeline --stream flag     │  ✅ Good  │  —                         │
│  Correlation ID logging     │  ✅ Good  │  —                         │
│  Sentry PII scrubbing       │  ✅ Good  │  —                         │
│  _verify_auth0_token dedup  │  ✅ Good  │  —                         │
│  upsert_student conflict    │  ✅ Good  │  —                         │
│  Zero TODO/FIXME            │  ✅ Good  │  —                         │
│  Real Postgres in CI        │  ✅ Good  │  —                         │
│  Token factory              │  ✅ Good  │  —                         │
│  Per-module coverage        │  ✅ Good  │  —                         │
│  RLS isolation tests        │  ✅ Good  │  —                         │
│  Playwright 16 specs        │  ✅ Good  │  —                         │
│  Universal + per-subject    │  ✅ Good  │  —                         │
│  Shared SBMarkdown          │  ✅ Good  │  —                         │
│  Format-drift validator     │  ✅ Good  │  —                         │
│  Attributed-quote discipline│  ✅ Good  │  —                         │
│  Health + metrics endpoints │  ✅ Good  │  —                         │
│  Dependabot + scanning      │  ✅ Good  │  —                         │
│  SBOM per CI run            │  ✅ Good  │  —                         │
│  RedBeat resolves Beat SPOF │  ✅ Good  │  —                         │
│  OpenAPI → TS drift check   │  ✅ Good  │  —                         │
├─────────────────────────────┼──────────┼────────────────────────────┤
│  APP_ENV not asserted       │  ⚠️  Bad  │  P1 — 3-line fix           │
│  Slowapi + Redis coexist    │  ⚠️  Bad  │  P1 — audit + consolidate  │
│  Pool arith warn-not-assert │  ⚠️  Bad  │  P1 — Pydantic validator   │
│  E2E narrow (accessibility) │  ⚠️  Bad  │  P1 — functional specs     │
│  3 axe rules disabled       │  ⚠️  Bad  │  P1 — issue #189           │
│  L-6 sweeper deferred       │  ⚠️  Bad  │  P2 — Beat task            │
│  No load/perf tests         │  ⚠️  Bad  │  P2 — k6/Locust suite      │
│  No mobile/web boundary doc │  ⚠️  Bad  │  P2 — before Epic 3 Path B │
│  No API versioning policy   │  ⚠️  Bad  │  P2 — document + header    │
│  C-7/C-8 not shipped        │  ⚠️  Bad  │  P2 — before mobile reopens│
│  No CSP/HSTS verified       │  ⚠️  Bad  │  P2 — nginx/ALB config     │
│  No runbooks                │  ⚠️  Bad  │  P2 — 6 runbooks           │
│  Docstring style inconsistent│ ⚠️  Bad  │  P3 — Google + ruff D rule │
│  No Makefile                │  ⚠️  Bad  │  P3 — common targets       │
│  No Alembic downgrade tests │  ⚠️  Bad  │  P3 — CI job on migrations │
│  Stripe key rotation undoc  │  ⚠️  Bad  │  P3 — before first paying  │
│  DEV_ACCOUNTS verify outstand│ ⚠️  Bad  │  P3 — confirm tag action   │
│  Mobile UI not tested       │  ⚠️  Bad  │  P3 — pending Epic 3 choice│
│  No cross-client auth tests │  ⚠️  Bad  │  P3 — as Epic 3 activates  │
└─────────────────────────────┴──────────┴────────────────────────────┘

P1 = Fix before first production users
P2 = Fix before scale / general availability
P3 = Fix before Epic 3 / 2nd-wave features
```

---

*Analysis based on code (StudyBuddy_OnDemand), docs (studybuddy-docs), CLAUDE.md (refreshed 2026-04-15), migrations 0001–0048, Playwright specs, Epic INDEX. April 2026.*
