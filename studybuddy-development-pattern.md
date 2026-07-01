# StudyBuddy OnDemand — Scoping, Design, Architecture & Development Pattern

**Document type:** Development pattern analysis
**Scope:** Full lifecycle — from idea to late-build production system
**Period:** 2025–2026
**Last refresh:** 2026-06-09 (v1.6 — alignment with critique v1.7: numbers re-measured on `main` @ `d50bc3e`; school onboarding wizard as a self-service-enablement milestone; "Administration" menu as UI-grouping discipline; ADR-005/006 as retro/refine decision-record hygiene; backup restore-path hardening)
**Prior:** v1.5 June 2026 (alignment with critique v1.6: Curriculum Authoring Studio (Epic 12) as a method milestone; ADR-004 product-boundary decision; book-export as a one-way content bridge) · v1.4 May 2026 (alignment with critique v1.5: numbers re-measured, `teacher_capabilities`, CONTESTED-status discipline) · v1.3 May 2026 (visual-library wave cadence + Pivot 7 helpers-toolkit + resolver-eval feedback loop) · v1.2 April 2026 (Epic 10 governance, Epic 11 content formatting, Streams registry, Playwright persona expansion)
**Related:** [studybuddy-critique.md](studybuddy-critique.md) · [studybuddy-practices.md](studybuddy-practices.md) · [studybuddy-cost.md](studybuddy-cost.md) · sibling product: [mentible-development-pattern.md](mentible-development-pattern.md)
**Author:** WeGoFwd2020 / Claude (Anthropic)

> **Note (2026-06-09, v1.6):** the body below is the v1.3 record, preserved; nothing in the method has been overturned. New since v1.5 (26-commit window, HEAD `d50bc3e`), worth adding to the documented pattern:
>
> - **Self-service onboarding built on derived signals, not new endpoints.** The school_admin onboarding wizard (#420) computes a guided checklist (`web/lib/school/setup-checklist.ts`) purely from counts the portal *already* exposes — teachers, students, adoptions, classrooms — so the feature added **zero backend surface**. The step computation is a pure function, unit-tested without rendering. Method pattern: *build the guidance layer on top of existing read signals; do not grow the API to power a UI affordance.*
> - **UI grouping that explicitly disclaims being an authorization boundary.** The "Administration" top-bar menu (#415/#417) supersedes the older Curriculum menu and gates section visibility by capability — but its own docstring states "the backend enforces each action's gate independently — hiding a link is never the control." Healthy: the convenience surface is documented as *not* the security control, so no one mistakes link-hiding for authz.
> - **Two flavors of ADR hygiene in one window.** ADR-005 (Proposed) *refines* an open question (school_admin as role-superset vs additive flag; email-only uniqueness) before the code fully lands — a decision-ahead-of-code ADR. ADR-006 (Accepted) *retro-documents* a capability that shipped two months earlier (multi-provider LLM = Epic 1 / migration 0043) and corrects a stale `exploration` status in the same commit — a back-fill ADR. Both are good practice; together they show the ADR register is used both prospectively and to pay down documentation debt.
> - **A backup that could not restore was caught and fixed with tests, not patched.** #411 found the restore path didn't match the real schema; the fix reconciled it and grew `test_backup.py` by ~297 lines (now 32 tests). Method: *a restore-path bug is a data-loss bug; close it with test coverage proportional to the blast radius, not a one-liner.*
>
> Re-measured 2026-06-09: **1,085 backend tests / 77 files** (was 1,081/78), **60 migrations (latest 0060 — no schema change this window)**, 17 Playwright specs / 2,779 LOC, **4 ADRs (ADR-005/006 added)**. Zero TODO/FIXME holds.
>
> **Note (2026-06-02, v1.5):** the body below is the v1.3 record, preserved; nothing in the method has been overturned. New since v1.4, worth adding to the documented pattern:
>
> - **Generation pipeline turned inward — the Authoring Studio (Epic 12).** The same scoped-query IP that generated *student-facing* content per curriculum is now driven by a super-admin **authoring workflow**: paste a TOC → LLM structures it (`pipeline/toc_structurer.py`) + advisory flow analysis (`pipeline/flow_analyzer.py`) → editable topic tree → staged curriculum → per-topic generate → review with unlimited regenerate → snapshot/restore → publish. The method milestone: the content pipeline graduated from a batch `build_grade.py` script into an *interactive, reviewable, governed* studio with versioning and a hard publish-completeness gate (#401/#402). This is the "tooling-eats-its-own-pipeline" pattern — the generator becomes a product surface.
> - **Product-boundary decision recorded as an ADR, not a fork (ADR-004).** When the "author a book + free reader, BYOK" idea grew large enough to be its own product, the team did not bolt it onto OnDemand — ADR-004 (Accepted 2026-05-26) sends it to the sibling Mentible repo and *closes OnDemand's own ADR-002/ADR-003 without merge*. Healthy discipline: a scope-defining decision gets a durable artifact and the losing options are explicitly closed, not left dangling. See [mentible-development-pattern.md](mentible-development-pattern.md).
> - **One-way content bridge over cross-import (book-export #400).** Sharing between the two products is `port + vendor`, never a runtime dependency — `book_export.py` emits a neutral "Book JSON" the sibling consumes; no code crosses the repo boundary. Same vendoring discipline as Pivot 7, applied at the *product* boundary.
>
> Re-measured 2026-06-02: **1,081 backend tests / 78 files** (was 1,030), **60 migrations (latest 0060, `curriculum_authoring_studio`)**, 17 Playwright specs / 2,779 LOC. Zero TODO/FIXME holds.
>
> **Note (2026-05-24, v1.4):** the v1.4 additions (preserved): launch/demo hardening as a lifecycle stage; additive-RBAC via `teacher_capabilities`; CONTESTED epics; backlog correction as a first-class operation —
>
> - **Launch/demo hardening as its own lifecycle stage.** The window since v1.3 was almost entirely launch-readiness work — `vm-localhost-bootstrap.sh` + JSON deploy log, demo unit pre-import (`preimport_demo_units.py`), nginx/DNS fixes, demo JWT TTL extension to 4h, domain rename `studybuddy.app` → `usestudybuddy.com`. This sits between "feature-complete" and "first paying customer" and deserves a named phase in the lifecycle taxonomy.
> - **Additive-RBAC via a capabilities table.** `teacher_capabilities` (#358, migration 0059, RLS) extends RBAC by adding an authoritative table with a two-gate read/act model rather than mutating existing role-grant logic. Reusable pattern for future capability classes.
> - **CONTESTED epics as a discipline.** Epic 17 (corporate-L&D fork) was stamped `CONTESTED` after advisor pushback rather than silently dropped. Healthy pattern — speculative epics get a status stamp instead of disappearing. Recommend adding `CONTESTED` to the formal epic-status vocabulary alongside DELIVERED / IN-PROGRESS / DEFERRED.
> - **Backlog correction as a first-class operation.** Epic 10 L-7/L-8 were listed open in v1.3 but were already shipped per current `CLAUDE.md`. The v1.4 cycle treated this as a real correction (not a footnote) — sign that the engineering log is the source of truth, not the critique doc.
>
> Re-measured: 1,030 backend tests / 73 files (was 914), 59 migrations (latest 0059), 17 Playwright specs / 2,781 LOC. Zero TODO/FIXME holds. See [studybuddy-cost.md](studybuddy-cost.md) for the real-world cost-of-time-and-money analysis of the patterns documented below.

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

The earliest scratch-pad conversations reveal a hands-on, UI-first iteration style:

- "The drop down does not show the 'title' to choose to learn"
- "Too many empty rows in the screen, can this be reduced?"
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
        │
        ▼
Layer 10 — Curriculum governance (Epic 10, shipped 2026)
  "Platform owns a canonical library; schools own their custom curricula.
   Archive/unarchive with in-use gating. Audit every lifecycle action.
   Retention sweeper paused — storage cost tail accepted for now."
        │
        ▼
Layer 11 — Content presentation standard (Epic 11, shipped 2026)
  "Every subject renders correctly: Commerce tables, Maths KaTeX,
   Science reactions, attributed quotes. Format drift is detectable."
        │
        ▼
Layer 12 — Content identity (Streams, shipped 2026)
  "Curricula belong to streams (science, commerce, humanities, english, stem).
   Soft registry — rename/merge as data, not schema."
```

### 2.2 The Scope Constraint Rule

Each layer's scope was bounded by a practical question: *what is the smallest thing we can ship that validates this layer?*

This manifested as the Phase model, later extended by Epic numbering as the product matured past the initial phases:

| Phase / Epic | Scope question answered |
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
| Epic 1 | Can multiple LLM providers back the pipeline? |
| Epic 8 | Can curricula belong to streams? |
| Epic 10 | Can platform and school content coexist with per-party governance? |
| Epic 11 | Can every subject render its content with the correct formatting? |

### 2.3 Requirements Format

Requirements were never captured in a formal spec template. They emerged from conversational prompts:

> "Following are features I would like to aim for:
> 1) this will be a subscription service.
> 2) Students will need to register...
> 3) Subscription service can be monthly or annual..."

This conversational requirements style worked because each item was immediately challenged for scope clarity. The discipline was: no feature entered implementation without a clear answer to *who pays, who controls, and who sees it*.

For Epic 10, the scoping question was:

> "Platform admins own the default curricula. School admins own their own. What happens if a school admin archives a curriculum that has active students? What happens if a platform admin tries to modify a school curriculum? What happens when retention expires?"

The archive-gating on `is_curriculum_in_use` and the RESTRICTIVE RLS on platform curricula fell directly out of those questions.

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

The `CLAUDE.md` in the code repo served as a live operational reference — not documentation of what *should* be built, but documentation of what *is* built and how to work with it. Refreshed 2026-04-15 to cover Epic 8, Epic 10 L-1..L-5, Epic 11 C-1..C-9.

### 3.2 Architecture Decision Records

Architectural pivots were captured as ADRs in the `docs/` directory of the code repo. ADR-001 is the canonical example — it resolved three foundational questions that had accumulated conflicting implementations:

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
│  build_grade.py ──▶ Anthropic API ──▶ Content Store (S3/local)      │
│                │         │                    │                      │
│                │    TTS Provider         JSON + MP3 + meta.json      │
│                │         │                                            │
│                └─── PostgreSQL                                        │
│                  (curriculum units, streams, jobs)                   │
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
│  (subs, progress, (entitlement,     (reads via StorageBackend        │
│   curricula, RLS) rate limits)       abstraction — Local/S3)        │
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

This separation answers the original problem permanently: no student device holds an Anthropic API key, and the API server never blocks on AI generation.

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

Epic 3 (Path B — Expo/React Native) is chosen as the future student mobile path. Kivy remains until Path B activates.

### 3.5 Caching Strategy Design

The caching strategy was designed as a first principle, not retrofitted:

```
Request: GET /content/{unit_id}/lesson
         │
         ▼
L1: cachetools TTLCache (per-worker, in-process)
    ├── JWT JWKS keys         TTL: 1h
    ├── curriculum tree        TTL: 5m
    └── stream registry        TTL: 5m   ← added for Epic 8 streams
         │ miss
         ▼
L2: Redis (shared across workers)
    ├── ent:{student_id}       TTL: 5m
    ├── cur:{student_id}       TTL: 5m
    ├── school:{id}:ent:{sid}  TTL: 5m
    └── content:{unit_id}:{v}  TTL: 60m
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

### 3.6 Content Presentation Standard (Epic 11)

The Epic 11 design decision was that content presentation quality is a platform concern, not a per-lesson concern. The design moved in three pieces:

```
1. Universal + per-subject prompt guidelines  (pipeline/prompts.py)
   │
   │  Every prompt carries:
   │  ├── Table formatting rules (GFM alignment markers)
   │  ├── LaTeX delimiters ($...$ inline, $$...$$ display)
   │  ├── Currency escape rules (\$ or ISO code)
   │  ├── Attributed blockquote rules (em-dashed, verifiable only)
   │  └── Subject-specific overrides (Commerce tables, Maths KaTeX, ...)
   │
2. Shared renderer (web/components/content/Markdown.tsx)
   │
   │  One SBMarkdown component; four inline <ReactMarkdown> copies
   │  consolidated. Plugins: remark-gfm, remark-math, rehype-katex.
   │
3. Format-drift validator (pipeline/content_format_validator.py)
   │
   │  Emits a warning when a section title suggests tabular/formula
   │  content but the output lacks tables or KaTeX.
```

The discipline: encoded rules in the prompt, enforced rules in the renderer, detected drift in the validator.

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
    │  /api/v1/admin/streams               │
    │  /api/v1/admin/curricula/{id}/...    │
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
    │                   TTS, --stream)    │
    │  celery-beat     (grade promotion,  │
    │                   retention alerts, │
    │                   digests) via      │
    │                   RedBeat           │
    └─────┬───────────────────────────────┘
          │
    ┌─────┴──────────────────────────────┐
    │  Anthropic API · Stripe · Auth0     │
    │  (external services — never in      │
    │   student request path)             │
    └─────────────────────────────────────┘
```

### 4.2 Database Schema Pattern

The schema grew from a single-user model through 48 migrations. The pattern followed a clear sequence:

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

Migrations 0030–0042  (Phase 10–11 dashboard + feedback + reports)

Migration 0043  (Epic 1 — multi-provider pipeline)
  provider column on content_subject_versions + pipeline_jobs

Migration 0044  (Epic 8 — streams column)
  nullable stream_code on curricula, students, teachers

Migration 0045  (Epic 8 — streams registry)
  streams table (5 system seeds, no FK from curricula)

Migration 0046  (Epic 10 L-1 — platform write-guard)
  3 RESTRICTIVE RLS policies on curricula
  Block INSERT/UPDATE/DELETE on owner_type='platform' rows
  unless app.current_school_id='bypass'

Migration 0047  (Epic 10 L-3 — retention)
  retention_status='archived' CHECK + partial index
  (sweeper implementation L-6 paused)

Migration 0048  (Hotfix)
  Drop stale RLS policies from L-1 debug draft
  on curriculum_units / content_subject_versions
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
  │   (L1 TTLCache)      │   (run_in_executor)
  ├── upsert_student()   └── issue JWT
  └── issue internal JWT     (ADMIN_JWT_SECRET)
         │
         ▼
  Internal JWT payload
  Student:  {student_id, grade, locale, role:"student", exp}
  Teacher:  {teacher_id, school_id, role:"teacher|school_admin", exp}
  Admin:    {admin_id, role:"developer|product_admin|super_admin|...", exp}
         │
         ▼
  Middleware checks
  ├── signature verify (per-role secret)
  ├── suspended:{id} Redis check
  ├── Redis-backed ip_auth_rate_limit (10 req/60s)
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
  build_grade.py --grade 8 --lang en,fr,es [--stream science] [--force] [--dry-run]
  build_unit.py  --curriculum-id UUID --unit G8-MATH-001
  OR
  POST /admin/pipeline/trigger → Celery job
      │
      ▼
  prompts.py — inject universal + per-subject formatting rules
      │
      ▼
  _call_claude() [max_tokens=16384, optional streaming via --stream]
      │
      ├── JSON schema validation (3 retries on failure)
      ├── AlexJS content moderation scan
      ├── content_format_validator.py — emit format_drift warnings
      ├── TTS: lesson text → MP3 (Polly/Google TTS)
      └── idempotency: check meta.json before generating
      │
      ▼
  Content Store write (via StorageBackend interface)
  {path}/curricula/{curriculum_id}/{unit_id}/
    lesson_en.json    quiz_set_1_en.json    tutorial_en.json
    lesson_fr.json    quiz_set_2_en.json    experiment_en.json
    lesson_en.mp3     meta.json
      │
      ▼
  DB write: content_subject_versions (status='pending', stream_code)
      │
      ▼
  Admin Content Review Queue
  ├── Review → Version Detail → Unit Viewer (SBMarkdown renders)
  ├── Inline annotations (compound key: unit_id::type::section_id)
  ├── Version diff (word-level highlighting)
  └── Actions: Approve / Reject / Publish / Rollback / Block
```

### 4.5 Multi-Tenancy Model

After ADR-001, the tenancy model is PostgreSQL Row-Level Security. Epic 10 extended this to governance:

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
PostgreSQL RLS policy (0028)        Same policy enforces isolation
      │                                   │
      ▼                                   ▼
PostgreSQL RLS policy (0046)        Same policy:
  Block writes on                   - School A and B can read platform
  owner_type='platform' unless        curricula
  session = 'bypass'                - Neither can modify platform rows
      │                                   │
      ▼                                   ▼
Only permitted rows visible         Only permitted rows visible
(DB-enforced, not app-enforced)     (DB-enforced, not app-enforced)
```

### 4.6 Streams Governance Architecture

Streams are a soft registry — identity for curricula without a schema-enforced FK:

```
streams table (migration 0045):
  code         VARCHAR PK    ← stable identifier
  display_name VARCHAR       ← editable
  is_system    BOOLEAN       ← true for 5 seeds (science, commerce, …)
  is_archived  BOOLEAN       ← soft-delete
  curriculum_count INT       ← recomputed by service on change

curricula table:
  stream_code  VARCHAR       ← no FK; soft reference to streams.code

Upsert on upload:
  POST /admin/pipeline/trigger?stream_display_name=...
    → streams_router._upsert_by_display_name()
    → INSERT ... ON CONFLICT (display_name) DO UPDATE
    → returns canonical code for curriculum assignment

Merge endpoint (lifecycle cleanup):
  POST /admin/streams/{code}/merge?target={other_code}
    → UPDATE curricula SET stream_code = target WHERE stream_code = code
    → archive the source stream
    → audit: stream.merge event
```

Why soft? Renaming a stream would otherwise require a schema migration across every curriculum row and every attached student/teacher assignment. As a data operation, the change is bounded and reversible.

---

## 5. Development Pattern

### 5.1 The Phase-Based Delivery Model

Development was structured as 11 sequential phases, each phase gated by a working test suite. The test count grew monotonically; after Phase 11, Epic-numbered delivery took over:

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
Post-11:  215+      ← ADR-001 + Demo Teacher + RLS
Epic 1:   ~450      ← multi-provider pipeline + fixtures
Epic 8:   ~600      ← streams + governance groundwork
Epic 10:  ~750      ← curriculum lifecycle governance + RLS test expansion
Epic 11:  ~835      ← content formatting tests + renderer tests

Current: 835 test functions across 59 files.
E2E:     16 Playwright spec files, 2,620 LOC.
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
| Event loop | Never blocked — asyncpg, aioredis, httpx, run_stripe(), run_in_executor everywhere |
| Audio | Never proxied — return pre-signed CDN URL |
| Progress writes | Fire-and-forget Celery — never await on request path |
| Connection pools | Initialised once per worker in lifespan context |
| Redis persistence | AOF mandatory in production — no exceptions |
| CDN invalidation | Must accompany Redis invalidation on content bump |

### 5.4 Testing Strategy

```
Backend tests
├── pytest + httpx.AsyncClient (no live network)
├── Mock PostgreSQL via pytest-asyncio fixture; real Postgres in CI via Alembic
├── fakeredis (no live Redis)
├── Mock Stripe SDK
├── Mock Auth0 (token factory in tests/helpers/token_factory.py)
├── Deterministic UUIDs in all fixtures
├── RLS isolation verified via test_rls.py
└── Per-module coverage thresholds: auth/subscription 90%, content 85%, default 80%

Mobile tests
├── Logic only: SyncManager, LocalCache, ProgressQueue, i18n loader
└── No Kivy widget tests (gap — pending Epic 3 Path B activation)

Pipeline tests
├── Mocked Anthropic SDK
├── Mocked TTS provider
├── Tests schema validation logic and idempotency
└── format_drift validator has its own coverage

E2E tests (Playwright)
├── 16 spec files / 2,620 LOC
├── Student critical path (293 LOC)
├── Persona accessibility (student/teacher/admin/school-admin — 276+319+232+327 LOC)
├── Auth, landing, pricing, admin portal
└── School-admin-curriculum-flow has 6 fixme'd scenarios (issue #188)
```

### 5.5 The CLAUDE.md Operational Pattern

The CLAUDE.md file in the code repo is maintained as a living document and read at the start of every session. It serves as:

1. **Phase / Epic status dashboard** — which phases are complete, what's active (refreshed 2026-04-15 for Epic 10 L-1..L-5 + Epic 11 C-1..C-9)
2. **Repository layout map** — where every file lives and why
3. **Layer rules** — dependency direction (enforced by convention)
4. **Non-negotiable rules** — performance, security, content, compliance
5. **Top pitfalls** — known failure modes, written as discovered
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
Git tag `dev-accounts-repair-2026-04-14` marks DEV_ACCOUNTS.md remediation.
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
│  OpenAPI → TS drift  ← contract drift      │
└─────────────────────────────────────────────┘
      │ all pass
      ▼
┌─────────────────────────────────────────────┐
│  Test suite                                  │
│                                              │
│  alembic upgrade head (studybuddy_test DB)  │
│  pytest --cov                                │
│  scripts/check_coverage_thresholds.py       │
│    ← per-module 90/85/80 enforcement        │
│  Syft SBOM generation (SPDX + CycloneDX)    │
└─────────────────────────────────────────────┘
      │ pass
      ▼
┌─────────────────────────────────────────────┐
│  E2E (on every PR)                           │
│                                              │
│  Playwright — chromium-project (86 specs)    │
│  Persona specs (35 specs)                    │
└─────────────────────────────────────────────┘
      │ pass
      ▼
  PR mergeable
```

---

### 5.8 The Three-Phase Wave Cadence (Visual-Library Pattern, Epic #326)

Epic #326 imposed a 3-phase pattern on every sub-issue, repeated 10 times in the May 2026 wave:

```
Phase 1 — Catalogue
   ├── generate_<class>_visuals.ts (SVG primitives + assets)
   ├── append SidecarSpec[] entries to seed_library_sidecars.ts
   └── commit + push

Phase 2 — Remotion clip (optional but routine)
   ├── sample_content/<grade>/<unit>/Option3_Video/
   │     package.json · tsconfig.json · remotion.config.ts
   │     src/index.ts · src/Root.tsx · src/theme.ts
   │     src/scenes/*.tsx (lift primitives from Phase 1)
   ├── bunx remotion render → MP4
   └── commit + push

Phase 3 — Library promotion + eval
   ├── seed_library_local.py → UPSERT 144 entries with embeddings
   ├── append eval-NNN records to backend/tests/eval/visual_resolver_eval.jsonl
   ├── run_resolver_eval.py → precision@1 / recall@k report
   ├── MEMO.md (per-unit reflection for #320 lift)
   └── close GH issue
```

**Why this works.** Each phase is shippable on its own. Phase 1 alone closes the issue if the unit doesn't warrant a clip. Phase 2 rides on Phase 1's primitives — `secantLine` from `generate_derivatives_visuals.ts` lifts verbatim into the Remotion `<SecantLine>` scene. Phase 3 measures whether the resolver actually surfaces the new entries — without it, you've authored content blind. Side-issues encountered during the wave (#338 resolver eval KeyError, #339 docker-cp dance) get filed and closed *inside* the wave, not queued.

**The shared-theme pattern.** All 9 Remotion clips share `src/theme.ts` palette/typography conventions — title/body fonts, primary/accent/danger colours, AbsoluteFill spacing. The compositions are visually consistent without per-clip styling work.

**The cumulative-phase integral pattern.** For time-evolving simulations (oscillations, optics, derivatives, waves) the React-Remotion convention is `useCurrentFrame()` → integrate the time-derivative explicitly per-frame, never re-derive from scratch. Used in 6 of the 9 clips.

**Compression evidence.** First-of-class shipping (#327 oscillations) consumed ~3h. Same-class downstream (#328 G9 kinematics) landed in ~45 min. Estimated wave wall-time ~19 FTE-days; actual ~14h 56m — driven by ritual, not by primitive sharing (most SVGs are class-specific).

**Sticky cross-class primitives ready for #320 component lift.** `<LeaderLabel />`, `<DotCluster />`, `<MotionStrip />`, `<Spring />`, `<RotatingPoint />`, `<EmittedParticle />`, `<SpinArrow />`, `<SecantLine />` — these recurred across ≥2 clips during the wave and are the natural first batch to factor into a shared Remotion component library.

---

## 6. Key Pivots and Decision Points

### Pivot 1 — Device-side to Backend-driven (The Foundational Pivot)

| Before | After |
|---|---|
| Student holds Anthropic API key | API key lives in pipeline/backend env only |
| Content generated on demand (per request) | Content pre-generated offline by operator |
| No cost control | Spend cap in pipeline |
| No version management | Versioned content with approve/publish/rollback |
| studybuddy_free | StudyBuddy_OnDemand |

**Driver:** "How do I protect from over usage?"

### Pivot 2 — Individual Subscriptions to School-as-Primary-Entity (ADR-001)

| Before | After |
|---|---|
| Students subscribe individually | School subscribes; all students covered |
| Teachers subscribe independently | Teachers are members of a school |
| Private teacher tier (migration 0022) | Removed entirely |
| Individual `subscriptions` table | `school_subscriptions` table only |
| App-layer tenant filtering | PostgreSQL RLS (database-enforced) |

**Driver:** "The School/Institution is the primary entity. The teacher is a member of a single school."

### Pivot 3 — App-layer Tenant Isolation to PostgreSQL RLS

| Option considered | Decision |
|---|---|
| Separate full instance per school | Rejected: 12× cost and ops burden |
| Shared instance, app-layer filtering | Rejected: isolation relies on bug-free code |
| Shared instance, PostgreSQL RLS | Accepted |

**Driver:** FERPA and COPPA compliance. RLS provides a provable isolation guarantee.

### Pivot 4 — Filesystem to StorageBackend Abstraction (Completed)

The content store began as `CONTENT_STORE_PATH=/data/content` (Docker volume). The transition to S3 was originally deferred but documented as a scalability cliff. In v1.2 this was resolved via the `StorageBackend` abstraction (`LocalStorage` for dev, `S3Storage` for production). Horizontal scaling is now a config flip, not an architectural change.

### Pivot 5 — Ad-Hoc Curriculum Mutations to Platform-vs-School Governance (Epic 10)

| Before Epic 10 | After Epic 10 |
|---|---|
| Any admin could modify any curriculum | Platform write-guard via RESTRICTIVE RLS |
| No distinction between platform-owned and school-owned content | `owner_type` column + RLS |
| Archive was ad hoc | Archive/unarchive endpoints with in-use gating |
| Retention was policy | Retention status modelled in DB (sweeper paused) |
| Lifecycle events untracked | Audit events: `curriculum.archive`, `unarchive`, `archive_by_platform_admin` |

**Driver:** "Platform admins own the default curricula. School admins own their own. What happens if a school archives a curriculum that has active students?"

### Pivot 6 — Ad-Hoc Rendering to Content Presentation Standard (Epic 11)

| Before Epic 11 | After Epic 11 |
|---|---|
| Four `<ReactMarkdown>` copies in different components | One shared `SBMarkdown` component |
| Tables rendered inconsistently across subjects | GFM tables with alignment; numeric cells `tabular-nums` |
| No LaTeX rendering; maths content broke | KaTeX via `remark-math` + `rehype-katex` |
| Prompts were per-subject, no universal spine | Universal + per-subject block in `pipeline/prompts.py` |
| No drift detection | `content_format_validator.py` warns on section/output mismatch |
| Attributed quotes were ad hoc, sometimes fabricated | Strict prompt rule; em-dash format; verifiable sources only |

**Driver:** Content presentation quality is a platform concern, not a per-lesson concern.

### Pivot 7 — Ad-Hoc Visual Authoring to Helpers-Toolkit + Wave Cadence (Epic #326, May 2026)

The first visual-library catalogue (`generate_oscillations_visuals.ts`) was written end-to-end on its own. By the second class (`generate_g9_kinematics_visuals.ts`) the script had factored a small shared toolkit — `svgWrap`, `write`, `makePlot`, `plotPolyline`, recursive `mkdirSync` — and a declarative `SidecarSpec[]` array consumed by `seed_library_sidecars.ts`. That toolkit lifted into every subsequent generator (chemistry, biology, electronics, periodic-table, organic-chem, derivatives, waves, optics) and the **same primitives lift verbatim into Remotion clips** — the `secantLine` helper in the derivatives generator becomes the Remotion `<SecantLine>` scene component without modification.

| Before #326 wave | After |
|---|---|
| One-off SVG generator per topic, copy-paste-and-adjust | 10 generators sharing a 5-helper toolkit; primitives lift into Remotion |
| Library sidecars hand-edited per asset | Declarative `SidecarSpec[]` → `seed_library_sidecars.ts` is the single source |
| Promotion CI required for any dev evaluation | `seed_library_local.py` UPSERTs into dev DB with `local://` fake `s3_path`; resolver only surfaces this string |
| Operator workflow: `docker cp scripts/* celery-pipeline:/tmp/` | `./scripts:/app/scripts-repo:ro` + `./sample_content:/app/sample_content:ro` bind mounts (#339) |
| Eval harness crashed on Voyage rate-limits (#338 KeyError) | Error branch mirrors success-path schema; `n_errored` in summary |
| Wall time per class | First-of-class ~3h; same-class downstream ~45 min |

**Driver:** ten near-identical sub-issues invited a wave cadence. The compression result (estimated ~19 FTE-days → actual ~14h 56m) is **process maturity, not primitive reuse** — most SVGs and Remotion scenes are class-specific. What scaled was the Phase 1/2/3 ritual.

### Decision Point — PAI 5.0 Removal (May 2026)

PAI 5.0 (TOOLS, MEMORY, ALGORITHM, agents Forge/Cato/Anvil/Arthur, hooks, voice via localhost:31337) was integrated under `~/.claude/`. After a `Cannot find module '../PAI/TOOLS/TranscriptParser'` Stop-hook error proved unrecoverable, the integration was removed in full: ~/.claude/{PAI,hooks,agents,skills,MEMORY,commands,rules,debug,paste-cache,...}, ~/.config/PAI/, install.sh, voice.local.md. settings.json shrank from 52,688 to 1,908 bytes (kept: `$schema`, `permissions`, `enabledPlugins`, `plansDirectory`). Snapshot retained at `~/.claude.pre-pai-removal-20260508T123957Z`.

**Driver:** PAI was speculative tooling layered on top of Claude Code. It produced no shipped value in the StudyBuddy or Thittam projects and broke the hook surface. Decisive removal beat partial recovery.

### Decision Point — Epic 3 Path B (Deferred, Documented)

Native student mobile app: Kivy/Buildozer has been replaced as the future path by Expo/React Native (Path B). Kivy remains until Path B activates. The decision is documented; implementation is parked behind hosting (Epic 2).

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
Implementation phase/epic (code repo)
        │
        ▼
Tests (gate before next phase)
        │
        ▼
CLAUDE.md updated (pitfalls + conventions captured)
        │
        ▼ (next feature request)
```

The loop is tight. No phase starts without the previous phase's tests passing. No design starts without the scope questions being answered. For Epic 10, the scope question "what happens when a school archives a curriculum with active students?" drove the `is_curriculum_in_use` gate directly into the design.

### 7.2 The Pitfall Register

Pitfalls are documented in CLAUDE.md as they're discovered. Recent additions:

- `max_tokens=8192` silently truncating Grade 12 tutorials under richer Epic 11 prompts → raised to 16384
- Stale RLS policies from an L-1 debug draft left on `curriculum_units` → hotfix 0048
- Four inline `<ReactMarkdown>` components drift in styling → consolidated into `SBMarkdown`
- `_verify_auth0_token` and `_verify_auth0_teacher_token` diverged silently → deduplicated into one audience-parameterised function

The discipline of writing pitfalls as they are found prevents the same mistake from occurring in a future session.

### 7.3 The Three-Context Boundary as a Security Model

The separation of Pipeline / Backend / Client is not just an architectural pattern — it is a security model. The constraints are enforced by convention and documented as rules:

- The mobile app NEVER calls Anthropic directly (no key, no call)
- The mobile app NEVER has Stripe keys (entitlement is HTTP status codes)
- The backend NEVER generates content on the request path
- The pipeline NEVER serves clients directly

Any feature request that violates a context boundary is visible immediately and forces a design discussion before code is written.

### 7.4 Migrations as Architecture History

The 48 Alembic migrations are a readable history. Each migration has a name that describes the business change, not the SQL operation:

- `0024_student_teacher_assignments` — not "add_columns"
- `0026_remove_private_teacher_tier` — not "drop_tables"
- `0028_rls` — not "alter_tables"
- `0045_streams_registry` — not "add_lookup_table"
- `0046_platform_readable_rls` — not "add_policy"

This convention makes the migration history a document, not just a sequence of database changes.

### 7.5 Governance as a Shippable Feature

Epic 10 treats governance as a first-class feature, not an afterthought. Platform-vs-school ownership, archive/unarchive with in-use gating, audit events per lifecycle transition — these are not policy documents; they are code paths, migrations, and test cases.

For SaaS products serving regulated customers (schools, healthcare, finance), governance as a shippable feature is the difference between "we can demo" and "we can pass procurement review". Epic 10 earned the latter posture.

### 7.6 Presentation as a Platform Concern

Epic 11 's insight: when content is generated by LLMs across many subjects, uneven presentation quality is indistinguishable from uneven generation quality to the student. A Maths lesson that renders as a wall of plain text next to a Science lesson that renders with proper tables and equations is not a "Maths content" problem — it is a platform problem.

Codifying the rules in the prompt, enforcing them in the renderer, and detecting drift in the validator is the three-part discipline. Each piece alone is insufficient; together they are sufficient.

---

*This document captures the development pattern as observed through code, documentation, ADRs, CLAUDE.md history, migrations 0001–0048, the Epic INDEX, and scratch-pad conversations from the StudyBuddy OnDemand project, as of April 2026 (v1.2 refresh).*
