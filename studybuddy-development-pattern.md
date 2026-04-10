# StudyBuddy OnDemand — Scoping, Design, Architecture & Development Pattern

**Document type:** Development pattern analysis  
**Scope:** Full lifecycle — from idea to mid-build production system  
**Period:** 2025–2026  
**Author:** WeGoFwd2020 / Claude (Anthropic)

---

## Table of Contents

1. [The Origin Story](#1-the-origin-story)
2. [Scoping Pattern](#2-scoping-pattern)
3. [Design Pattern](#3-design-pattern)
4. [Architecture Pattern](#4-architecture-pattern)
5. [Development Pattern](#5-development-pattern)
6. [Key Pivots and Decision Points](#6-key-pivots-and-decision-points)
7. [What This Pattern Teaches](#7-what-this-pattern-teaches)

---

## 1. The Origin Story

StudyBuddy did not begin as a SaaS. It began as a local Kivy desktop/mobile application — `studybuddy_free` — where a student would enter their own Anthropic API key, load a grade-specific JSON file, and receive AI-generated lessons directly on their device.

```
studybuddy_free (v1) — Device-side model
┌─────────────────────────────────────────┐
│  Student Device                         │
│                                         │
│  ┌─────────┐    ┌──────────────────┐   │
│  │  Kivy   │───▶│  Anthropic API   │   │
│  │   App   │    │  (student's key) │   │
│  └─────────┘    └──────────────────┘   │
│       │                                 │
│  ┌─────────┐                           │
│  │ grade5_ │                           │
│  │stem.json│                           │
│  └─────────┘                           │
└─────────────────────────────────────────┘
```

The earliest scratch pad conversations reveal a very hands-on, UI-first iteration style:

- "The drop down does not show the 'title' to choose to learn"
- "There are too many empty rows in the screen, can this be reduced?"
- "When I load the application I see two icons for help on the right-hand bottom"
- "Now for actual testing with my personal email id and a real API Key — how do I protect this from over usage?"

This was the scoping signal: the moment the question "how do I protect from over usage?" appeared, the device-side model revealed its fundamental limitation. A student's API key on a student device is both a security problem and a cost-control problem.

The architectural fork happened explicitly:

> "studybuddy_free and StudyBuddy_OnDemand are 2 distinct projects and not incremental in any sense except that the subject/topic specific contents may be shared."

That single statement defined the boundary between two eras of the product.

---

## 2. Scoping Pattern

### 2.1 The Scoping Journey

StudyBuddy's scope was built in layers, each layer exposing the next set of requirements.

```
Layer 1 — Core learning loop (studybuddy_free)
  "Can a student select a grade, pick a topic, and read AI-generated content?"
        │
        ▼
Layer 2 — Safety and control
  "How do we protect the API key? How do we prevent over-usage?"
        │
        ▼
Layer 3 — Business model
  "Subscription service. Students register. Free tier = 2 lessons.
   Monthly or annual plans. English, French, Spanish."
        │
        ▼
Layer 4 — Content enrichment
  "Lessons read aloud (TTS). Visualisation for experiments.
   Content moderation (AlexJS)."
        │
        ▼
Layer 5 — Institutional model
  "Teacher/School registration. Custom curriculum upload (XLSX).
   Student roster. Restrict access to enrolled students."
        │
        ▼
Layer 6 — Analytics and feedback
  "Time-on-task tracking. Quiz attempt tracking.
   Student feedback on content and UX."
        │
        ▼
Layer 7 — Governance and review
  "Formal content review and approval workflow.
   Versioning with rollback. RBAC for reviewer roles."
        │
        ▼
Layer 8 — Tenancy and compliance
  "School is the primary entity. School-level billing.
   PostgreSQL RLS for FERPA/COPPA compliance."
        │
        ▼
Layer 9 — Retention and lifecycle
  "1-year curriculum retention per school.
   School admin controls renewal or expiry.
   Storage cost model."
```

### 2.2 The Scope Constraint Rule

Each layer's scope was bounded by a practical question: *what is the smallest thing we can ship that validates this layer?*

This manifested as the Phase model. Before any code was written for a new capability, the user articulated requirements in plain language and the scope was captured as a phase goal:

| Phase | Scope question answered |
|---|---|
| 1 | Can the backend stand up and serve authenticated content? |
| 2 | Can the pipeline generate and serve English content? |
| 3 | Can we track what a student has done? |
| 4 | Can students work offline and in other languages? |
| 5 | Can we collect payment? |
| 6 | Can we visualise experiments? |
| 7 | Can admins review and approve content? |
| 8 | Can schools upload their own curriculum? |
| 9 | Can a school roster restrict student access? |
| 10 | Can we measure learning quality? |
| 11 | Can teachers see their class's performance? |

### 2.3 Requirements Format

Requirements were never captured in a formal spec template. They emerged from conversational prompts:

> "Following are features I would like to aim for:
> 1) this will be a subscription service.
> 2) Students will need to register...
> 3) Subscription service can be monthly or annual..."

This conversational requirements style worked because each item was immediately challenged for scope clarity. The question "Is renewal free or paid?" was answered with a precise billing model:

> "Renewal or extending the expiry date of content should cost only the storage space.
>  New version of same curriculum means cost of Anthropic usage + storage space of new content."

The discipline was: no feature entered implementation without a clear answer to *who pays, who controls, and who sees it*.

---

## 3. Design Pattern

### 3.1 Documentation-First

Every phase was preceded by documentation. Before a line of code was written, the design was captured in the docs repo (`studybuddy-docs`). The document hierarchy defined the reading order for any contributor:

```
studybuddy-docs/
  ARCHITECTURE.md          ← Read first. System design, all phases.
  BACKEND_ARCHITECTURE.md  ← Before touching backend.
  REQUIREMENTS.md          ← Check requirement ID before implementing.
  AGENTS.md                ← Conventions, pitfalls, per-phase checklists.
  SCALABILITY.md           ← Capacity planning, growth tiers.
  OPERATIONS.md            ← Runbooks, incident response.
  PHASE1_SETUP.md          ← Phase 1 implementation guide.
  UX_GOALS.md              ← North star per persona.
  CHANGES.md               ← Design decisions log.
  GLOSSARY.md              ← Term definitions.
```

The CLAUDE.md in the code repo served as a live operational reference — not documentation of what *should* be built, but documentation of what *is* built and how to work with it.

### 3.2 Architecture Decision Records

Architectural pivots were captured as ADRs in the `docs/` directory of the code repo. ADR-001 is the canonical example — it resolved three foundational questions that had accumulated conflicting implementations:

**ADR-001 structure:**

```
Context  → Three foundational questions had conflicting code
Decision → Three explicit rules (School-primary / School-billing / PostgreSQL RLS)
Options  → Three tenancy models considered (separate instance / app-layer / RLS)
Consequences → Dead code identified and removal sequenced
Implementation order → 7-step migration sequence
```

The ADR format forced the team to acknowledge that earlier migrations (0022 — private teacher tier) were wrong and needed removal, not patching.

### 3.3 The Three Runtime Contexts Design Principle

The single most important design decision in StudyBuddy is the **separation of three runtime contexts**:

```
┌─────────────────────────────────────────────────────────────────────┐
│  CONTEXT 1: Content Pipeline (offline, operator-run)                 │
│                                                                       │
│  build_grade.py ──▶ Anthropic API ──▶ Content Store                 │
│                │         │                    │                      │
│                │    TTS Provider         S3/filesystem               │
│                │         │             (JSON + MP3 + meta.json)      │
│                └─── PostgreSQL                                        │
│                  (curriculum units)                                   │
└─────────────────────────────────────────────────────────────────────┘
            (no runtime connection to Context 2 or 3)

┌─────────────────────────────────────────────────────────────────────┐
│  CONTEXT 2: Backend API (always-on)                                  │
│                                                                       │
│  FastAPI + uvicorn                                                    │
│       │                                                               │
│   ┌───┴─────────────────────────────────────────┐                   │
│   │ JWT verify → L1 cache → L2 Redis → L3 DB    │ hot read path     │
│   └─────────────────────────────────────────────┘                   │
│       │             │                   │                             │
│  PostgreSQL       Redis            Content Store                     │
│  (subscriptions, (entitlement,     (serving JSON                     │
│   progress,       rate limits,      via pre-signed                   │
│   curricula,      session)          URL or API)                      │
│   schools)                                                           │
└─────────────────────────────────────────────────────────────────────┘
            (never calls Anthropic; reads Content Store read-only)

┌─────────────────────────────────────────────────────────────────────┐
│  CONTEXT 3: Client (user device)                                      │
│                                                                       │
│  Next.js web app          Kivy mobile app                            │
│  (admin, teacher,         (student — offline-capable)                │
│   public portal)                │                                    │
│       │                   SQLite event_queue                         │
│       │                   LocalCache (bounded by MAX_CACHE_MB)       │
│       │                   SyncManager (flushes on foreground)        │
│       │                         │                                    │
│       └─────────────── Backend API only ─────────────────────────── │
│                    (NEVER calls Anthropic or Stripe directly)        │
└─────────────────────────────────────────────────────────────────────┘
```

This separation answers the original problem permanently: no student device ever holds an Anthropic API key, and the API server never blocks on AI generation.

### 3.4 Client Segmentation by Persona

The decision to have two distinct frontend clients was intentional from Phase 7 onward:

```
┌──────────────────────────────────────────────────────────────────┐
│  Client Segmentation                                              │
│                                                                   │
│  Kivy Mobile App              Next.js Web App                    │
│  ┌───────────────┐            ┌──────────────────────────────┐   │
│  │ Students      │            │ Admins    Teachers   Parents  │   │
│  │ Grades 5-12   │            │                              │   │
│  │               │            │ /admin/*     /school/*       │   │
│  │ Content       │            │ /student/*   /public/*       │   │
│  │ consumption   │            │                              │   │
│  │ Quiz          │            │ Pipeline  Review  Reports    │   │
│  │ Progress      │            │ Roster    Analytics Billing  │   │
│  │ Offline sync  │            │                              │   │
│  └───────────────┘            └──────────────────────────────┘   │
│         │                                    │                    │
│         └──────────── Backend API ───────────┘                   │
└──────────────────────────────────────────────────────────────────┘
```

This is not a feature-parity gap — it is deliberate scope separation. Administrative complexity does not belong in a student's mobile interface.

### 3.5 Caching Strategy Design

The caching strategy was designed as a first principle, not retrofitted:

```
Request: GET /content/{unit_id}/lesson
         │
         ▼
L1: cachetools TTLCache (per-worker, in-process)
    ├── JWT JWKS keys         TTL: 1h
    ├── curriculum tree        TTL: 5m
    └── vertical config        TTL: 5m
         │ miss
         ▼
L2: Redis (shared across workers)
    ├── ent:{student_id}       TTL: 5m   (entitlement)
    ├── cur:{student_id}       TTL: 5m   (curriculum resolver)
    ├── school:{id}:ent:{sid}  TTL: 5m   (school-scoped entitlement)
    └── content:{unit_id}:{v}  TTL: 60m  (content JSON)
         │ miss
         ▼
L3: PostgreSQL
    └── source of truth
         │
         ▼
L4: CloudFront CDN (audio and large JSON)
    └── MP3 files via pre-signed URL (never proxied through API)
```

Invalidation rules were equally explicit: L2 Redis and CDN must be invalidated together on content version bump. TTL expiry alone is not sufficient for correctness-critical data.

---

## 4. Architecture Pattern

### 4.1 System Topology

```
Internet
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  nginx / CloudFront                                              │
│  Rate limiting · TLS termination · Static asset CDN             │
└─────────┬───────────────────────────────────────────────────────┘
          │
    ┌─────┴──────┐    ┌──────────────┐
    │  Next.js   │    │   Kivy App   │
    │  Web App   │    │  (mobile)    │
    └─────┬──────┘    └──────┬───────┘
          │                  │
          └────────┬──────────┘
                   │ REST/JSON over HTTPS
                   ▼
    ┌──────────────────────────────────────┐
    │   FastAPI (uvicorn + gunicorn)        │
    │   4 workers · PgBouncer in front     │
    │                                      │
    │  /api/v1/auth/     /api/v1/content/  │
    │  /api/v1/progress/ /api/v1/school/   │
    │  /api/v1/admin/    /api/v1/demo/     │
    └─────┬──────────────────┬─────────────┘
          │                  │
    ┌─────┴──┐          ┌────┴────┐
    │  Redis  │          │Postgres │
    │ (AOF on)│          │ + RLS   │
    └─────────┘          └─────────┘
          │
    ┌─────┴──────────────────────────────┐
    │  Celery Workers                     │
    │                                     │
    │  celery-io       (email, push,      │
    │                   audit log)        │
    │  celery-default  (subscription,     │
    │                   cache invalidate) │
    │  celery-pipeline (content build,    │
    │                   TTS)              │
    │  celery-beat     (grade promotion,  │
    │                   retention alerts, │
    │                   digests)          │
    └─────┬───────────────────────────────┘
          │
    ┌─────┴──────────────────────────────┐
    │  Anthropic API · Stripe · Auth0     │
    │  (external services — never in      │
    │   student request path)             │
    └─────────────────────────────────────┘
```

### 4.2 Database Schema Pattern

The schema grew from a single-user model to a multi-tenant school model across 29 migrations. The pattern followed a clear sequence:

```
Migrations 0001–0011  (Phase 1–11 schema)
  students · admin_users · curricula · curriculum_units
  content_subject_versions · quiz_sessions · quiz_answers
  progress_sessions · notifications · audit_log
  pipeline_jobs · content_annotations · stripe_events

Migrations 0012–0015  (Demo + Pipeline improvements)
  demo_teacher_requests · demo_teacher_accounts
  demo_teacher_verifications · pipeline_jobs (extended)

Migrations 0016–0023  (School/Teacher/Enrolment — Phases 8–9)
  schools · teachers · school_enrolments
  teacher_grade_assignments · school_subscriptions
  school_curricula_assignments

Migration 0024  (Student-teacher assignment model — ADR-001 Decision 1)
  student_teacher_assignments
  school_enrolments ← adds grade, teacher_id columns

Migrations 0025–0027  (ADR-001 cleanup)
  DROP private_teachers · teacher_subscriptions · student_teacher_access
  DROP subscriptions (individual student billing removed)

Migration 0028  (PostgreSQL RLS — ADR-001 Decision 3)
  ENABLE ROW LEVEL SECURITY on 7 tables
  app.current_school_id session variable

Migration 0029  (Lesson Retention Service)
  curricula ← adds retention_status, expires_at, grace_until
  school_storage_quotas · grade_curriculum_assignments
```

The pattern: **schema migrations are the commit history of architectural decisions**. Each migration corresponds to a design decision, not just a database change.

### 4.3 Request Authentication Flow

```
Incoming Request
      │
      ▼
  ┌────────────────────────────────────────────────────────┐
  │  Which auth path?                                       │
  └──────┬──────────────────────┬──────────────────────────┘
         │                      │
   Student/Teacher           Admin
   Auth0 id_token            Local bcrypt
         │                      │
         ▼                      ▼
  POST /auth/exchange    POST /admin/auth/login
  ├── JWKS verify        ├── bcrypt verify
  │   (L1 cached)        │   (run_in_executor)
  ├── upsert_student()   └── issue JWT
  └── issue internal JWT     (ADMIN_JWT_SECRET)
         │
         ▼
  Internal JWT payload
  Student:  {student_id, grade, locale, role:"student", exp}
  Teacher:  {teacher_id, school_id, role:"teacher|school_admin", exp}
  Admin:    {admin_id, role:"developer|product_admin|...", exp}
         │
         ▼
  Middleware checks
  ├── signature verify (per-role secret)
  ├── suspended:{id} Redis check
  └── RLS: SET LOCAL app.current_school_id (teacher requests)
         │
         ▼
  Route handler
```

### 4.4 Content Pipeline Architecture

```
Operator (offline)
      │
      ▼
  build_grade.py --grade 8 --lang en,fr,es
  build_unit.py  --curriculum-id UUID --unit G8-MATH-001
  OR
  POST /admin/pipeline/trigger → Celery job
      │
      ▼
  prompts.py → _call_claude() [max_tokens=8192]
      │
      ├── JSON schema validation (3 retries on failure)
      ├── AlexJS content moderation scan
      ├── TTS: lesson text → MP3 (via Polly/Google TTS)
      └── idempotency: check meta.json before generating
      │
      ▼
  Content Store write
  {CONTENT_STORE_PATH}/curricula/{curriculum_id}/{unit_id}/
    lesson_en.json    quiz_set_1_en.json    tutorial_en.json
    lesson_fr.json    quiz_set_2_en.json    experiment_en.json
    lesson_en.mp3     meta.json
      │
      ▼
  DB write: content_subject_versions (status='pending')
      │
      ▼
  Admin Content Review Queue
  ├── Review → Version Detail → Unit Viewer
  ├── Inline annotations (compound key: unit_id::type::section_id)
  ├── Version diff (word-level highlighting)
  └── Actions: Approve / Reject / Publish / Rollback / Block
```

### 4.5 Multi-Tenancy Model

After ADR-001, the tenancy model is PostgreSQL Row-Level Security:

```
School A Request                    School B Request
      │                                   │
      ▼                                   ▼
JWT: {school_id: "aaa..."}         JWT: {school_id: "bbb..."}
      │                                   │
      ▼                                   ▼
get_db() middleware                 get_db() middleware
SET LOCAL app.current_school_id     SET LOCAL app.current_school_id
  = 'aaa...'                          = 'bbb...'
      │                                   │
      ▼                                   ▼
PostgreSQL RLS policy               PostgreSQL RLS policy
USING (school_id =                  USING (school_id =
  current_setting(                    current_setting(
    'app.current_school_id')            'app.current_school_id')
  ::uuid)                             ::uuid)
      │                                   │
      ▼                                   ▼
Only School A rows visible          Only School B rows visible
(DB-enforced, not app-enforced)     (DB-enforced, not app-enforced)
```

---

## 5. Development Pattern

### 5.1 The Phase-Based Delivery Model

Development was structured as 11 sequential phases, each phase gated by a working test suite. The test count grew monotonically:

```
Phase  1:  38 tests  ← Backend Foundation
Phase  2:  52 tests  ← Content Pipeline + English
Phase  3:  73 tests  ← Progress Tracking
Phase  4:  87 tests  ← Offline + Multilingual + TTS
Phase  5:  99 tests  ← Subscriptions + Stripe
Phase  6: 100 tests  ← Experiment Visualisation
Phase  7: 124 tests  ← Admin + Content Review
Phase  8: 159 tests  ← School + Teacher + Curriculum Upload
Phase  9: 176 tests  ← Student–School Association
Phase 10: 197 tests  ← Extended Analytics + Feedback
Phase 11: 215 tests  ← Teacher Reporting Dashboard
Post-11: 215+ tests  ← ADR-001 + Demo Teacher + RLS
```

The phase model enforced a discipline: **you do not start Phase N+1 until Phase N's tests pass**.

### 5.2 Module Structure

Every backend module follows the same layout:

```
src/{domain}/
  router.py      ← FastAPI endpoints; module docstring listing all routes
  service.py     ← Business logic; no direct DB calls
  schemas.py     ← Pydantic models (request/response)
  tasks.py       ← Celery async tasks (optional)
```

The module docstring convention was non-negotiable. Every `router.py` has a docstring listing its endpoints, security model, and key functions — making it searchable and self-describing.

### 5.3 Non-Negotiable Performance Rules

Seven performance rules were written into CLAUDE.md as constraints, not guidelines:

| Rule | Constraint |
|---|---|
| Hot read path | Zero DB queries on cache-warm requests |
| Event loop | Never blocked — asyncpg, aioredis, httpx everywhere |
| Audio | Never proxied — return pre-signed CDN URL |
| Progress writes | Fire-and-forget Celery — never await on request path |
| Connection pools | Initialised once per worker in lifespan context |
| Redis persistence | AOF mandatory in production — no exceptions |
| CDN invalidation | Must accompany Redis invalidation on content bump |

### 5.4 Testing Strategy

```
Backend tests
├── pytest + httpx.AsyncClient (no live network)
├── Mock PostgreSQL via pytest-asyncio fixture
├── fakeredis (no live Redis)
├── Mock Stripe SDK
├── Mock Auth0 (token factory in tests/helpers/token_factory.py)
├── Deterministic UUIDs in all fixtures
└── CI threshold: --cov-fail-under=70 (identified as too low; target 80%)

Mobile tests
├── Logic only: SyncManager, LocalCache, ProgressQueue, i18n loader
└── No Kivy widget tests (gap)

Pipeline tests
├── Mocked Anthropic SDK
├── Mocked TTS provider
└── Tests schema validation logic and idempotency
```

### 5.5 The CLAUDE.md Operational Pattern

The CLAUDE.md file in the code repo was maintained as a living document and read at the start of every session. It served as:

1. **Phase status dashboard** — which phases are complete, what's active
2. **Repository layout map** — where every file lives and why
3. **Layer rules** — dependency direction (enforced by convention)
4. **Non-negotiable rules** — performance, security, content, compliance
5. **Top pitfalls** — 22 known failure modes, written as they were discovered
6. **Running reference** — exactly how to start, test, build, and deploy

This document is the most important artefact in the project. It replaced the need for onboarding sessions.

### 5.6 Secret and Configuration Management

```
dev_start.sh reads .env
       │
       ▼
pydantic-settings (config.py)
       │
       ├── No defaults for secrets — fail fast at startup
       ├── ANTHROPIC_API_KEY     → pipeline only
       ├── STRIPE_SECRET_KEY     → backend only
       ├── JWT_SECRET            → backend only
       ├── ADMIN_JWT_SECRET      → backend only (separate from student)
       └── DATABASE_URL / REDIS_URL / AUTH0_DOMAIN / etc.

.env.example documents all required vars
.secrets.baseline (detect-secrets) prevents git commits with secrets
```

### 5.7 CI Pipeline

```
Push to branch
      │
      ▼
┌─────────────────────────────────────────────┐
│  Quality gates (run in parallel)             │
│                                              │
│  ruff check          ← linting              │
│  ruff format --check ← formatting          │
│  bandit -r src/      ← security SAST       │
│  pip-audit           ← dependency CVEs     │
│  snyk test           ← advanced vuln scan  │
│  detect-secrets      ← secret scanning     │
└─────────────────────────────────────────────┘
      │ all pass
      ▼
┌─────────────────────────────────────────────┐
│  Test suite                                  │
│                                              │
│  alembic upgrade head (studybuddy_test DB)  │
│  pytest --cov --cov-fail-under=70           │
└─────────────────────────────────────────────┘
      │ pass
      ▼
  PR mergeable
```

---

## 6. Key Pivots and Decision Points

### Pivot 1 — Device-side to Backend-driven (The Foundational Pivot)

| Before | After |
|---|---|
| Student holds Anthropic API key | API key lives in pipeline/backend env only |
| Content generated on demand (per request) | Content pre-generated offline by operator |
| No cost control | Spend cap in pipeline ($50 default) |
| No version management | Versioned content with approve/publish/rollback |
| studybuddy_free | StudyBuddy_OnDemand |

**Driver:** "How do I protect from over usage?" — a single question that invalidated the entire model.

### Pivot 2 — Individual Subscriptions to School-as-Primary-Entity (ADR-001)

| Before | After |
|---|---|
| Students subscribe individually | School subscribes; all students covered |
| Teachers subscribe independently | Teachers are members of a school |
| Private teacher tier (migration 0022) | Removed entirely |
| Individual `subscriptions` table | `school_subscriptions` table only |
| App-layer tenant filtering | PostgreSQL RLS (database-enforced) |

**Driver:** "The School/Institution is the primary entity. The teacher is a member of a single school." — a clarification from a requirements conversation that required removing 3 migrations worth of code.

### Pivot 3 — App-layer Tenant Isolation to PostgreSQL RLS

| Option considered | Decision |
|---|---|
| Separate full instance per school | Rejected: 12× cost and ops burden |
| Shared instance, app-layer filtering | Rejected: isolation relies on bug-free code |
| Shared instance, PostgreSQL RLS | Accepted |

**Driver:** FERPA and COPPA compliance requirements. RLS provides a provable isolation guarantee to security auditors that app-layer filtering cannot.

### Decision Point — Filesystem to S3 (Deferred but Documented)

The content store began as `CONTENT_STORE_PATH=/data/content` (Docker volume). The decision to move to S3 was explicitly deferred but documented as a known scalability cliff:

> "The transition to S3 (already documented in SCALABILITY.md) must happen before the first real deployment, not after."

This is a good example of the pattern: **defer infrastructure decisions that can be changed without schema changes, but document them as explicit blockers before they become incidents**.

---

## 7. What This Pattern Teaches

### 7.1 The Requirement Clarification Loop

```
Feature request (conversational)
        │
        ▼
Scope questions (who controls? who pays? who sees it?)
        │
        ▼
Written design (docs repo)
        │
        ▼
Implementation phase (code repo)
        │
        ▼
Tests (gate before next phase)
        │
        ▼
CLAUDE.md updated (pitfalls + conventions captured)
        │
        ▼ (next feature request)
```

The loop is tight. No phase starts without the previous phase's tests passing. No design starts without the scope questions being answered. No feature is assumed — every edge case (renewal model, who can assign students, what happens when a subscription lapses) is explicitly answered before coding begins.

### 7.2 The Pitfall Register

22 pitfalls are documented in CLAUDE.md. They are not hypothetical — each one was discovered, often in a debugging session:

- `max_tokens=4096` silently truncating Grade 12 tutorials
- Reading `localStorage` during SSR in Next.js
- Clearing Redis cache without invalidating the CDN
- Rebuilding a Docker image without restarting the container

The discipline of writing pitfalls as they are found prevents the same mistake from occurring in a future session.

### 7.3 The Three-Context Boundary as a Security Model

The separation of Pipeline / Backend / Client is not just an architectural pattern — it is a security model. The constraints are enforced by convention and documented as rules:

- The mobile app NEVER calls Anthropic directly (no key, no call)
- The mobile app NEVER has Stripe keys (entitlement is HTTP status codes)
- The backend NEVER generates content on the request path
- The pipeline NEVER serves clients directly

Any feature request that violates a context boundary is visible immediately and forces a design discussion before code is written.

### 7.4 Migrations as Architecture History

The 29 Alembic migrations in StudyBuddy are a readable history of architectural decisions. Each migration has a name that describes the business change, not the SQL operation:

- `0024_student_teacher_assignments` — not "add_columns"
- `0026_remove_private_teacher_tier` — not "drop_tables"
- `0028_rls` — not "alter_tables"

This convention makes the migration history a document, not just a sequence of database changes.

---

*This document captures the development pattern as observed through code, documentation, ADRs, CLAUDE.md history, and scratch pad conversations from the StudyBuddy OnDemand project, April 2026.*
