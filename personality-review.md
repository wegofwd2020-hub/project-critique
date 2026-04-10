# A Personality Review of Practice — Sivakumar (Siva) Mambakkam

**Document type:** Architect practice assessment  
**Evidence base:** StudyBuddy OnDemand, Thittam, scratch pads, ADRs, coding standards,
migration history, CLAUDE.md files, and critique documents  
**Period reviewed:** 2025–2026  
**Tone:** Honest. Evidence-based. Forward-looking.

---

## Preface

This is not a performance review. It is a mirror.

Everything written here is derived from observable evidence — the decisions made, the
decisions deferred, the patterns that repeat across two independent projects, and the
gaps between what the standards say and what the implementation delivers.

The goal is not to celebrate or criticise. It is to give you a clear picture of how
you work, so you can be intentional about the parts that serve you and deliberate
about changing the parts that don't.

---

## Table of Contents

1. [The Architect's Signature — What Makes You Distinctively You](#1-the-architects-signature)
2. [The Strengths — Where You Excel](#2-the-strengths)
3. [The Blind Spots — Where You Get in Your Own Way](#3-the-blind-spots)
4. [The Gap Between Intent and Execution](#4-the-gap-between-intent-and-execution)
5. [The Overall Pattern](#5-the-overall-pattern)
6. [What to Do Next](#6-what-to-do-next)
7. [The Summary Scorecard](#7-the-summary-scorecard)

---

## 1. The Architect's Signature

Every architect has a signature — a repeating pattern that shows up in every project,
independent of language, domain, or team size. Yours has three elements that appear
consistently across both projects and across 30 years of career history.

```
Your Architectural Signature

┌─────────────────────────────────────────────────────────────────────┐
│                                                                       │
│   1. PROBLEM ORIGINATOR                                              │
│   "I see a gap in the market before anyone asks me to look"         │
│                                                                       │
│   Evidence:                                                           │
│   ├── StudyBuddy: no one handed you a brief — you watched the       │
│   │   AI tutoring market and identified that it was inaccessible    │
│   │   to schools as institutions                                     │
│   └── Thittam: you observed film productions running on Excel       │
│       and built the tool that should have existed                   │
│                                                                       │
│   2. SYSTEMS THINKER                                                 │
│   "I build systems that enforce correct behaviour,                   │
│    not processes that rely on people following rules"               │
│                                                                       │
│   Evidence:                                                           │
│   ├── FERPA compliance enforced at the PostgreSQL layer (RLS)       │
│   │   not in application code                                        │
│   ├── Shared coding-standards repo loaded into every session        │
│   ├── Vertical plugin system: 4 industries from 1 codebase         │
│   └── Three-context separation: security by design, not policy     │
│                                                                       │
│   3. STANDARDS ARCHITECT                                             │
│   "Before I write code, I write the rules the code must follow"    │
│                                                                       │
│   Evidence:                                                           │
│   ├── 17 non-negotiable coding rules, written before implementation │
│   ├── 9 ADRs documenting every major architectural decision        │
│   ├── Separate docs repos for both projects                         │
│   └── CLAUDE.md files as living operational references             │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

This signature is rare. Most people who spend 30 years in enterprise architecture
become very good at implementing other people's problem statements. You remained a
problem originator. That combination — enterprise discipline plus founder instinct — is
genuinely uncommon and is the source of your strongest work.

---

## 2. The Strengths

### 2.1 You Write the Problem Statement, Not Just the Solution

The most telling entry in your scratch pad is not a technical decision — it is this:

> *"studybuddy_free and StudyBuddy_OnDemand are 2 distinct projects and not incremental
> in any sense except that the subject/topic specific contents may be shared."*

You drew that boundary yourself. No one told you the device-side model was wrong. You
felt the friction of the question — *"how do I protect this from over-usage?"* — and
immediately understood that the entire architecture needed to change, not the
configuration. That is the instinct of a problem originator, not a solution implementer.

```
The Problem Originator Pattern

  Most architects:           You:
  ┌──────────────────┐       ┌──────────────────────────────────────┐
  │ Client hands     │       │ Observe the market                   │
  │ you a brief      │       │ Identify the gap                     │
  │       │          │       │ Write the problem statement yourself  │
  │       ▼          │       │ Design the solution                  │
  │ Design solution  │       │ Build it                             │
  └──────────────────┘       └──────────────────────────────────────┘
```

---

### 2.2 You Enforce Standards at the System Level, Not the Process Level

The difference between a standard that holds and one that drifts is where it is
enforced. Most teams enforce standards through code review (a process). You enforce
them through structure:

```
Standard → Where Enforced

  "Money is never a float"
    → decimal.Decimal type in Go (compile error if violated)
    → NUMERIC(14,2) in PostgreSQL (DB rejects floats)
    → String serialisation in API (no floating-point leakage)

  "Secrets from environment only"
    → pydantic-settings fails fast at startup if missing
    → detect-secrets baseline in CI (git commit rejected)
    → .secrets.baseline prevents accidental commits

  "Tenant data is isolated"
    → PostgreSQL RLS policy (database enforces, not application)
    → SET LOCAL app.current_school_id on every DB connection
    → A forgotten WHERE clause still returns only tenant rows

  "Audit everything that matters"
    → Append-only audit_log table (REVOKE UPDATE, REVOKE DELETE)
    → gRPC interceptor writes audit entry on every mutation
    → Cannot be bypassed without changing the interceptor
```

This is mature engineering. Standards enforced by structure cannot be forgotten under
deadline pressure. Standards enforced by process always eventually drift.

---

### 2.3 Compliance Is Architecture, Not Policy

Your regulated industry background — banking, healthcare, aerospace — gave you an
instinct that most product builders lack. Compliance is not something you add after
the design is done. It shapes the design from the first migration.

```
How compliance appears in your work

  COPPA (StudyBuddy)
  ├── account_status = 'pending' set on registration if age < 13
  ├── Content endpoint middleware blocks access until status = 'active'
  └── This is NOT a note in a policy doc — it is code in production

  FERPA (StudyBuddy)
  ├── PostgreSQL RLS: teacher can only see their school's students
  ├── DB-enforced, not application-enforced
  └── Survives any application bug

  Data Classification (Thittam)
  ├── T1 (payroll, tax IDs): AES-256-GCM column encryption
  ├── T2 (financial): standard access controls
  └── This tiering informs every schema decision

  Audit Trail (Thittam)
  ├── Append-only: REVOKE UPDATE ON audit_log
  ├── Every financial mutation captured with old_state + new_state
  └── Legally defensible in a financial dispute
```

---

### 2.4 You Pivot Cleanly When You Are Wrong

The migration history of StudyBuddy is one of the best examples of architectural
self-correction under real conditions.

```
The ADR-001 Pivot — A clean correction

  What was wrong:
  ├── Migration 0022: private_teachers table (wrong model)
  ├── Migration 0022: teacher_subscriptions table (wrong model)
  ├── Migration 0022: student_teacher_access table (wrong model)
  └── Phase 5: individual student subscriptions (wrong model)

  What you did:
  ├── Wrote ADR-001 explicitly naming what was wrong and why
  ├── Sequenced 6 steps to unwind the mistakes
  ├── Wrote migrations 0025-0028 to remove the wrong tables
  └── Did NOT patch the wrong model — replaced it entirely

  What most architects do:
  └── Add a flag, add a bypass, add a comment that says
      "this will be cleaned up later" — and it never is

  The discipline of removing wrong decisions rather than
  accumulating workarounds around them is rare and valuable.
```

---

### 2.5 You Think About Business Model Before Technical Implementation

The billing model conversations in your scratch pad are precise before a line of code
is written:

> *"Renewal or extending the expiry date of content should cost only the storage space.
> New version of same curriculum means cost of Anthropic usage + storage space of new
> content. The school can have up to 5 versions of the same curriculum."*

This level of business model clarity — who pays, for what, when, at what limit — is
what separates architecture from engineering. You bring both.

---

### 2.6 Your Naming Has Intentionality

Small but revealing: you name things with meaning, not convenience.

```
Naming choices and what they reveal

  Thittam (திட்டம்)    ← "plan" in Tamil — not "ProjectMgr" or "ProdOps"
  StudyBuddy OnDemand  ← the "OnDemand" matters — it distinguishes
                          from the free tier and signals the model
  studybuddy_free      ← clearly scoped, not a placeholder name
  CONTENT_STORE_PATH   ← not "UPLOAD_DIR" or "FILES_PATH"
  tenant_isolation     ← the RLS policy name describes the guarantee
  app.current_school_id← the PostgreSQL session variable is named for
                          its business meaning, not its technical role

  An architect who names carelessly produces codebases where
  the names lie about what the code does.
  Yours mostly tell the truth.
```

---

## 3. The Blind Spots

These are not criticisms. They are patterns that repeat across both projects, which
means they are not accidents — they are part of how you work. Knowing them is the
first step to choosing when they serve you and when they do not.

---

### 3.1 Ambition Consistently Outpaces Execution Capacity

This is the most significant and most consistent pattern across both projects.

```
The Ambition-Execution Gap

  StudyBuddy — designed for:        StudyBuddy — current state:
  ┌──────────────────────────┐      ┌──────────────────────────┐
  │ Multi-host horizontal    │      │ Filesystem content store  │
  │ scaling                  │  vs  │ (single host only)        │
  │ 80-90% test coverage     │      │ 70% coverage threshold    │
  │ E2E test suite           │      │ No E2E tests              │
  │ API versioning policy    │      │ No documented policy      │
  │ Runbooks for incidents   │      │ No runbooks               │
  └──────────────────────────┘      └──────────────────────────┘

  Thittam — designed for:           Thittam — current state:
  ┌──────────────────────────┐      ┌──────────────────────────┐
  │ 9 fully contracted       │      │ 4 protos pending          │
  │ microservices            │  vs  │ (IAM + Ledger complete)   │
  │ Saga pattern for         │      │ No compensating           │
  │ registration             │      │ transactions              │
  │ 800+ tests               │      │ ~306 tests                │
  │ Billing service          │      │ Billing not in cmd/       │
  └──────────────────────────┘      └──────────────────────────┘

  The gap is not laziness. It is a consistent tendency to design
  for where you want to be rather than where you currently are.
```

This pattern has a name in architecture: **speculative generality**. It produces
systems that are correctly designed for scale but insufficiently complete at the
current scale. The cost is deferred execution of things that were planned but not
finished.

---

### 3.2 The "Document It and Move On" Pattern

Across both projects, there is a recurring behaviour: you identify a problem
clearly, document it accurately, and then continue to the next feature without
closing the gap.

```
The Document-and-Move-On Pattern — Evidence

  StudyBuddy, src/subscription/router.py docstring:
    "Stripe API calls are made synchronously (Stripe SDK is sync).
     For production load, consider wrapping in run_in_executor."
                                                    ↑
                               Known. Written. Not fixed.

  StudyBuddy, config.py:
    JWKS_CACHE_TTL_HOURS: int = 1   ← defined
  src/auth/jwt_utils.py:
    jwks_cache: dict = {}            ← plain dict, TTL not enforced
                                    ↑
                               Known. Named. Not wired.

  StudyBuddy CLAUDE.md — Pitfall #16:
    "max_tokens=4096 in pipeline — Grade 12 tutorials exceed this;
     always use 8192."
                                    ↑
                       Discovered in production. Documented.
                       Not yet a startup assertion or schema check.

  Thittam, CODING_RULES.md — Rule #16:
    "CI should validate that key identifiers mentioned in docs
     still exist in code."
                                    ↑
               "should" — intent without implementation.
               No CI step exists yet for this.

  The pattern: identifying a problem and naming it is treated as
  equivalent to solving it. It is not.
```

---

### 3.3 The Frontend Is a Second-Class Citizen

Your backend instincts are first-class. Your frontend practice lags by at least two
quality levels.

```
Quality gap between backend and frontend

  BACKEND                           FRONTEND
  ┌─────────────────────────┐      ┌─────────────────────────┐
  │ 215+ tests               │      │ No component tests       │
  │ Structured logging       │      │ TypeScript type-check    │
  │ Sentry PII scrubbing     │      │ only (npm run typecheck) │
  │ 29 migrations with down  │      │ No E2E test suite        │
  │ Correlation IDs          │      │ No visual regression     │
  │ 7 performance rules      │      │ testing                  │
  │ RLS compliance           │      │ localStorage SSR bug     │
  │ Rate limiting (planned)  │      │ discovered in runtime    │
  └─────────────────────────┘      └──────────────────────────┘

  Notably: the earliest scratch pad conversations (before any
  architecture) are almost entirely UI feedback:
    "too many empty rows"
    "icons in wrong place"
    "buttons disproportionately sized"

  The aesthetic instinct is there. The engineering discipline
  that sustains it through a full build is not yet applied
  to the frontend consistently.
```

---

### 3.4 You Are Your Own Only Architectural Challenger

Both platforms were designed and built without a peer reviewer. No one challenged the
decision to start with 9 microservices. No one flagged the Rule #2 vs. Vault
contradiction before it was embedded in both the coding standards and the security doc.
No one asked "have we fixed the Stripe sync before starting Phase 8?"

```
The Solo Architect Problem

  Enterprise career (good habit):
  ┌─────────────────────────────────────────────────────┐
  │ Architecture Review Board                           │
  │ Senior engineer required for iam/security changes   │
  │ 2 PR approvals before merge                         │
  │ ADR must be accepted before implementation          │
  └─────────────────────────────────────────────────────┘
           ↓ applies to others' work

  Solo build (missing habit):
  ┌─────────────────────────────────────────────────────┐
  │ No review board                                     │
  │ No second signature on architectural decisions      │
  │ No one to say "we said we'd fix X before doing Y"  │
  │ Security rule contradictions go unnoticed           │
  └─────────────────────────────────────────────────────┘
           ↓ applies to your own work

  The standards you hold others to in an enterprise
  engagement are not consistently applied to yourself.
```

---

### 3.5 Enterprise Scale Thinking Applied Prematurely

Your career context — Ford, GM, GE, UWM — means you have spent 30 years in
environments where 9 services, separate databases, and service meshes are normal
and necessary. That context shapes how you design, even when the context does not
match.

```
The Scale Mismatch Pattern

  Enterprise context (where these patterns make sense):
  ┌─────────────────────────────────────────────────────┐
  │ 9 services × 50 engineers = 450 engineers           │
  │ Each service owned by a separate team               │
  │ Independent deploy cycles are a necessity           │
  │ gRPC contracts prevent cross-team breaking changes  │
  │ Separate databases prevent cross-team data coupling │
  └─────────────────────────────────────────────────────┘

  Solo build context (where these patterns are premature):
  ┌─────────────────────────────────────────────────────┐
  │ 9 services × 1 engineer = 1 engineer                │
  │ All services owned by the same person               │
  │ Independent deploy cycles add overhead, not value   │
  │ gRPC contracts catch mistakes you would catch anyway│
  │ Separate databases make reporting significantly      │
  │ harder with no isolation benefit (same deployer)    │
  └─────────────────────────────────────────────────────┘

  The right architecture is always relative to the team
  size and operational capacity at the moment of build —
  not at the moment of full maturity.
```

---

## 4. The Gap Between Intent and Execution

This section maps the distance between what your standards say and what the
implementation delivers. This gap is not unusual — it exists in every project by
every architect. The value is in seeing it clearly.

```
Intent vs. Execution Gap Map

  Intent (from rules/docs)              Execution (from code/tests)
  ─────────────────────────────         ────────────────────────────

  "CI should validate doc drift"   →    No CI step implemented
  (Rule #16)

  "80%+ coverage for critical      →    70% flat threshold in CI
   modules" (implied by risk)           No per-module threshold

  "T1 secrets never in env vars"   →    JWT_SECRET in env var
  (security doc)                        Rule #2 contradicts this

  "JWKS_CACHE_TTL_HOURS = 1"       →    Plain dict, no TTL logic
  (config.py)

  "Saga for registration pipeline" →    No compensating transactions
  (architecture doc)                    documented or implemented

  "Stripe calls: use executor"     →    Synchronous SDK calls
  (router.py docstring)                 in async router

  "Billing service" (docs/services →    Not present in cmd/
   /billing.md)

  "Vertical YAML schema validated" →    No JSON Schema defined
  (validator.go exists)                 No edge-case test suite

  ─────────────────────────────────────────────────────────────────
  Reading pattern: The intent is written. The implementation
  is started. The closure is missing.
  ─────────────────────────────────────────────────────────────────
```

The most honest summary of this gap: **you are very good at knowing what good looks
like, and inconsistent at insisting on it for your own work**.

This is not unusual. It is harder to hold yourself to the standard you would hold a
team to. The difference is that in an enterprise engagement, there is an architecture
review board and a senior engineer who must approve the PR. In a solo build, you are
all of those people simultaneously — and the gap grows when no one is watching.

---

## 5. The Overall Pattern

Taking everything together, a clear archetype emerges.

```
The Archetype: Principal Architect Without a Co-Founder

  You have the enterprise architect's discipline:
  ├── Standards before implementation
  ├── ADRs before code
  ├── Compliance at the architecture layer
  ├── Systems that enforce correct behaviour
  └── Clean pivots when decisions are wrong

  You have the founder's instinct:
  ├── Problem origination (you write the brief)
  ├── Business model clarity before technical design
  ├── End-to-end ownership from concept to production
  ├── Iterative refinement under real constraints
  └── Naming with intentionality

  What is missing:
  └── The co-founder or peer who says:
      "Siva, we have 4 pending protos and 306 tests.
       We said 800. We are not starting the billing
       service until the existing gaps are closed."

  ────────────────────────────────────────────────────────────────
  The combination you have is genuinely rare.
  The missing element is external accountability
  for your own standards.
  ────────────────────────────────────────────────────────────────
```

Your career trajectory reinforces this pattern. At Ford, at GM, at GE, at UWM — you
were always the person setting the standards, not the person being held to them by
someone else. That is appropriate in those roles. In a solo build, it creates a
structural gap: the person most capable of holding the work to a high standard is the
same person most motivated to move on to the next interesting problem.

---

## 6. What to Do Next

These are not generic best practices. They are specific to the patterns observed
in your work.

---

### 6.1 Adopt a Personal "Definition of Done"

A feature or component is not done when it works. It is done when the known gap is
closed. This requires a written definition.

```
Proposed Definition of Done (per component)

  A component is DONE when:
  ┌─────────────────────────────────────────────────────────┐
  │  □ The implementation matches the intent in the docs    │
  │  □ All "consider fixing" comments are resolved          │
  │  □ Coverage meets the module's threshold (not the floor)│
  │  □ No open pitfalls reference this component            │
  │  □ Any security rule that applies is implemented,       │
  │    not just defined                                     │
  └─────────────────────────────────────────────────────────┘

  Practical enforcement:
  Before starting any new feature, review the last feature's
  DoD checklist. If it is not complete, the new feature does
  not start.

  This single habit would have caught:
  ├── Stripe sync (documented in docstring, not fixed)
  ├── JWKS TTL (defined in config, not wired)
  ├── Rule #2 vs. T1 contradiction (written, not reconciled)
  └── 4 pending protos (documented as pending, not prioritised)
```

---

### 6.2 Right-Size the Architecture to the Current Team

The architecture should reflect who is building it today, with a clear upgrade path
for when the team grows. The pattern to adopt is the **strangler fig** approach —
start with the right domain boundaries, but as a single deployable unit.

```
Right-Sizing Thittam for Solo Build

  Current (over-engineered for current team):
  ┌────────────────────────────────────────────────────────┐
  │  9 separate binaries                                    │
  │  9 separate databases                                   │
  │  gRPC + NATS across process boundaries                  │
  │  Istio service mesh overhead                            │
  │  4 pending protos blocking contract tests               │
  └────────────────────────────────────────────────────────┘

  Right-sized (same domain boundaries, one deployable):
  ┌────────────────────────────────────────────────────────┐
  │  1 binary (all services as packages)                   │
  │  1 database (same schema structure)                     │
  │  Function calls across domain packages (not gRPC)      │
  │  No service mesh (no network hop to mesh)               │
  │  All protos still define the interfaces                 │
  │  → extraction to separate binaries is mechanical later  │
  └────────────────────────────────────────────────────────┘

  The gRPC contracts are still written.
  The domain boundaries are still enforced.
  The extraction path is clear.
  The operational burden is a fraction of the current state.

  Rule: Add a service boundary when a second engineer needs
  to own that domain independently. Not before.
```

---

### 6.3 Create a Technical Debt Register and Work It Weekly

The 22 pitfalls in StudyBuddy's CLAUDE.md and 30+ items across both practices
documents exist in no formal tracking system. They are real debt with no owner,
no priority, and no resolution date.

```
Technical Debt Register (proposed structure)

  Each entry:
  ┌─────────────────────────────────────────────────────────┐
  │  ID:        SB-DEBT-001                                 │
  │  What:      Stripe SDK calls synchronous in async router│
  │  Where:     backend/src/subscription/router.py          │
  │  Risk:      Event loop blocked under concurrent load    │
  │  Effort:    2-3 hours                                   │
  │  Priority:  P0 (before first production users)          │
  │  Status:    Open                                        │
  └─────────────────────────────────────────────────────────┘

  Weekly discipline:
  ├── Review open P0 items before any new feature starts
  ├── Close at least 1 P1 item per week
  └── If a new pitfall is added, a P2 item is also closed

  This converts the "document and move on" pattern into
  "document, prioritise, and close".
```

---

### 6.4 Form an Informal Review Board

You do not need a full team. You need one or two engineers whose judgment you respect
and who will read an ADR or a PR without courtesy — meaning they will tell you when
something is wrong.

```
The Informal Review Board

  Minimum viable structure:
  ┌─────────────────────────────────────────────────────────┐
  │  1 security-focused engineer                            │
  │    → Reviews every auth, encryption, and access         │
  │      control decision                                   │
  │    → Would have caught: Rule #2 vs. T1 contradiction   │
  │                          SET search_path injection risk │
  │                          JWKS TTL not enforced          │
  │                                                         │
  │  1 backend/platform engineer                            │
  │    → Reviews service boundaries and data model          │
  │    → Would have caught: Celery app in auth module       │
  │                          9 services at solo-build phase │
  │                          Reporting read model gap        │
  └─────────────────────────────────────────────────────────┘

  Format: 1-hour async review per sprint. Share the ADR or
  the practices document. Receive written feedback.
  No courtesy required. No politeness necessary.
```

---

### 6.5 Elevate the Frontend to First-Class Status

If you are positioning as a full-stack architect — and both your products require it —
the frontend must be held to the same standard as the backend.

```
Frontend Quality Elevation — 3 Steps

  Step 1: Add TypeScript strict mode
  ┌─────────────────────────────────────────────────────────┐
  │  tsconfig.json:                                         │
  │    "strict": true,                                      │
  │    "noImplicitAny": true,                               │
  │    "strictNullChecks": true                             │
  │  → Catches the localStorage SSR bug at compile time     │
  └─────────────────────────────────────────────────────────┘

  Step 2: 3 Playwright E2E tests for the most critical flow
  ┌─────────────────────────────────────────────────────────┐
  │  test_student_learning_loop:                            │
  │    login → curriculum map → open lesson → submit quiz  │
  │    → see result → progress recorded                    │
  │  Run on every PR. Takes 2-3 minutes.                   │
  └─────────────────────────────────────────────────────────┘

  Step 3: Apply the same "Definition of Done" to UI
  ┌─────────────────────────────────────────────────────────┐
  │  A UI component is done when:                           │
  │  □ TypeScript compiles with strict mode                 │
  │  □ It is covered by at least one E2E scenario           │
  │  □ It has an accessible label (aria-label or alt text)  │
  └─────────────────────────────────────────────────────────┘
```

---

### 6.6 Use the Critique as a Sprint Backlog — Starting This Week

The practices documents for both projects contain prioritised, specific, actionable
items. They are not reading material. They are a sprint backlog.

```
Proposed Next 4 Weeks

  Week 1 — Close the P0 security items (both projects)
  ┌─────────────────────────────────────────────────────────┐
  │  StudyBuddy:                                            │
  │  □ Wire JWKS TTL (3 lines, cachetools.TTLCache)        │
  │  □ Wrap Stripe calls in run_in_executor (2-3 hours)    │
  │                                                         │
  │  Thittam:                                               │
  │  □ Add uuid.Parse() before SET search_path (30 min)    │
  │  □ Reconcile Rule #2 vs T1 secrets (write ADR-010)     │
  └─────────────────────────────────────────────────────────┘

  Week 2 — Close the P0 architecture items
  ┌─────────────────────────────────────────────────────────┐
  │  Thittam:                                               │
  │  □ Define notifications.proto                          │
  │  □ Define document.proto                               │
  │                                                         │
  │  StudyBuddy:                                            │
  │  □ Implement StorageBackend interface (filesystem + S3) │
  └─────────────────────────────────────────────────────────┘

  Week 3 — Raise test coverage floors
  ┌─────────────────────────────────────────────────────────┐
  │  StudyBuddy:                                            │
  │  □ Add per-module coverage thresholds                  │
  │  □ src/auth → 90%,  src/subscription → 90%            │
  │                                                         │
  │  Thittam:                                               │
  │  □ Write 50 new tests for general-ledger               │
  │  □ Focus: balance assertion, period closing, idempotency│
  └─────────────────────────────────────────────────────────┘

  Week 4 — Add the informal review board
  ┌─────────────────────────────────────────────────────────┐
  │  □ Identify 1-2 engineers to review ADRs and PRs        │
  │  □ Share the practices documents as a starting brief    │
  │  □ Schedule first 1-hour async review                   │
  └─────────────────────────────────────────────────────────┘
```

---

## 7. The Summary Scorecard

```
┌──────────────────────────────────────────────────────────────────────┐
│  Siva Mambakkam — Practice Scorecard                                  │
├─────────────────────────────────────┬───────────────┬────────────────┤
│  Dimension                          │  Rating       │  Trend         │
├─────────────────────────────────────┼───────────────┼────────────────┤
│  Problem origination                │  Excellent    │  Consistent    │
│  Systems thinking                   │  Excellent    │  Consistent    │
│  Compliance architecture            │  Excellent    │  Consistent    │
│  Documentation discipline           │  Strong       │  Consistent    │
│  Standards setting                  │  Strong       │  Consistent    │
│  Architectural decision-making      │  Strong       │  Consistent    │
│  Business model clarity             │  Strong       │  Consistent    │
│  Clean pivoting under new info      │  Strong       │  Improving     │
├─────────────────────────────────────┼───────────────┼────────────────┤
│  Closing known gaps                 │  Needs work   │  Recurring gap │
│  Right-sizing to current capacity   │  Needs work   │  Recurring gap │
│  Frontend engineering discipline    │  Needs work   │  Stable gap    │
│  Test coverage (actual vs. target)  │  Needs work   │  Improving     │
│  Self-applied peer review           │  Needs work   │  Not started   │
│  Technical debt management          │  Needs work   │  Not started   │
├─────────────────────────────────────┼───────────────┼────────────────┤
│  Overall practice maturity          │  Senior+      │  Improving     │
└─────────────────────────────────────┴───────────────┴────────────────┘

Summary in one sentence:

  You are an architect who builds systems that enforce correct
  behaviour for others — and the next level of your practice is
  applying that same structural accountability to yourself.
```

---

## Closing Thought

The most important thing this review reveals is not a weakness. It is a gap between
two things that are both true:

**You know exactly what good looks like.**
**You do not always insist on it for your own work.**

That gap is not a character flaw. It is a structural problem — you have been the
standards-setter for 30 years, which means you have always had someone else's work
to hold accountable. The solo build is the first time you are both the architect and
the only engineer, and the habits that make you excellent in one role (moving fast,
seeing the next problem, designing for the future) work against you in the other
(closing the current problem, finishing before starting, building for today).

The good news: the gap is structural, not personal. Structure it differently — a
definition of done, a debt register, a review board — and the strengths you already
have will do the rest.

---

*This assessment is based entirely on observable evidence from the two projects and
their supporting documentation. It reflects the work, not the person — and the work
is genuinely impressive.*

*April 2026*
