# StudyBuddy OnDemand — Good Practices, Bad Practices & How to Improve

**Document type:** Engineering practices analysis  
**Scope:** Backend (FastAPI/Python), Web (Next.js), Mobile (Kivy), Pipeline, Infrastructure  
**Period:** April 2026  
**Rating key:** ✅ Good practice · ⚠️ Bad practice · 🔧 How to improve

---

## Table of Contents

1. [Architecture Practices](#1-architecture-practices)
2. [Security Practices](#2-security-practices)
3. [Performance Practices](#3-performance-practices)
4. [Code Quality Practices](#4-code-quality-practices)
5. [Testing Practices](#5-testing-practices)
6. [Data Practices](#6-data-practices)
7. [Operational Practices](#7-operational-practices)
8. [Summary Scorecard](#8-summary-scorecard)

---

## 1. Architecture Practices

### ✅ Good — Three Runtime Contexts Are Hard-Separated

The separation of Pipeline / Backend / Client is enforced by convention and documented as a security boundary. No client holds an API key. No backend generates content on the request path.

```
GOOD: Context boundary enforcement

  ┌──────────────────────────────────────────────────────────────────┐
  │  Context 1: Pipeline (offline)                                    │
  │                                                                   │
  │  build_grade.py ──▶ Anthropic API ──▶ Content Store             │
  │                                                                   │
  │  Keys present: ANTHROPIC_API_KEY, TTS_API_KEY                    │
  │  Keys absent:  STRIPE_*, JWT_*, DATABASE_URL (no API access)     │
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
  │  Keys present: none (no secrets on the device, ever)             │
  └──────────────────────────────────────────────────────────────────┘

WHY THIS IS GOOD:
  A compromised student device exposes nothing.
  A compromised API server cannot generate runaway Anthropic costs.
  The pipeline budget cap is the only cost control needed.
```

---

### ✅ Good — Pre-Generation Model Eliminates Per-Student Latency

```
BAD (rejected) — Live generation model
  Student requests lesson
        │
        ▼
  Backend calls Anthropic API ──▶ 2-8 seconds wait
        │
        ▼
  Student sees content                  ← unpredictable latency
                                        ← cost scales with students
                                        ← one API outage = all students blocked

GOOD (current) — Pre-generation model
  Offline operator runs pipeline
        │
        ▼
  Content stored in Content Store ──▶ instant on request
        │
  Student requests lesson
        │
        ▼
  Backend checks entitlement (L1/L2 cache) ──▶ ~5ms
        │
        ▼
  Serves JSON from Redis/Content Store ──▶ ~20ms total
                                        ← deterministic latency
                                        ← cost does not scale with students
                                        ← Anthropic outage ≠ student outage
```

---

### ✅ Good — Layer Dependencies Flow in One Direction

```
GOOD: Unidirectional dependency graph

  web/(admin)/                 ← imports from
    web/lib/api/admin.ts       ← imports from
      backend /api/v1/admin/*  ← imports from
        backend/src/admin/     ← imports from
          backend/src/core/    ← imports from
            PostgreSQL + Redis

  mobile/src/ui/               ← imports from
    mobile/src/logic/          ← imports from
      mobile/src/api/          ← imports from
        backend REST API

No circular dependencies. No layer calls upward.
Test any layer in isolation by mocking the layer below it.
```

---

### ⚠️ Bad — Celery App Lives in `src/auth/tasks`

```
BAD: Celery application defined in the wrong module

  docker-compose.yml
    celery-worker:
      command: celery -A src.auth.tasks worker ...    ← 'auth' module?

    celery-pipeline:
      command: celery -A src.auth.tasks worker ...    ← still 'auth'?

    celery-beat:
      command: celery -A src.auth.tasks beat          ← why is beat in auth?

PROBLEM:
  A developer joining the project looks at celery-pipeline and
  immediately asks: "why does the content pipeline import auth tasks?"
  The answer: it doesn't — src.auth.tasks just happens to be where
  the Celery app object was defined. This is a naming accident that
  misleads every future reader.

  Import graph confusion:
    src/content/ ──▶ src/auth/tasks.py (to access the Celery app object)
    src/school/  ──▶ src/auth/tasks.py
    src/admin/   ──▶ src/auth/tasks.py
```

#### 🔧 How to Improve

```
GOOD: Move Celery app to a neutral home

  src/core/celery_app.py
  ┌─────────────────────────────────────────┐
  │  from celery import Celery               │
  │                                         │
  │  app = Celery("studybuddy")             │
  │  app.config_from_object("src.core.      │
  │                          celery_config") │
  │                                         │
  │  # Task modules imported here           │
  │  app.autodiscover_tasks([               │
  │      "src.auth",                        │
  │      "src.content",                     │
  │      "src.subscription",               │
  │      "src.school",                      │
  │      "src.admin",                       │
  │  ])                                     │
  └─────────────────────────────────────────┘

  docker-compose.yml update:
    command: celery -A src.core.celery_app worker ...

  Result: The import graph now reads correctly.
    src/content/ ──▶ src/core/celery_app (neutral)
    src/auth/    ──▶ src/core/celery_app (neutral)

Migration: zero behaviour change, one rename, update docker-compose.
```

---

### ⚠️ Bad — Content Store Is a Filesystem Volume (Horizontal Scaling Cliff)

```
BAD: Filesystem content store blocks horizontal scaling

  Worker 1 (host-A)                Worker 2 (host-B)
  ┌─────────────────┐              ┌─────────────────┐
  │  FastAPI        │              │  FastAPI        │
  │                 │              │                 │
  │  /data/content  │              │  /data/content  │
  │  (local volume) │              │  (empty!)       │
  └─────────────────┘              └─────────────────┘

  Worker 2 cannot find content → 404 for 50% of requests
  No horizontal scaling possible until this is fixed.

Current state in config.py:
  CONTENT_STORE_PATH = "/data/content"  ← named Docker volume
```

#### 🔧 How to Improve

```
GOOD: Abstract behind a StorageBackend interface

  src/core/storage.py
  ┌─────────────────────────────────────────────────────────┐
  │  from abc import ABC, abstractmethod                     │
  │                                                         │
  │  class StorageBackend(ABC):                             │
  │      @abstractmethod                                    │
  │      async def read(self, path: str) -> bytes: ...      │
  │      @abstractmethod                                    │
  │      async def write(self, path: str,                   │
  │                      data: bytes) -> None: ...          │
  │      @abstractmethod                                    │
  │      async def presigned_url(self, path: str,           │
  │                              ttl: int) -> str: ...      │
  │                                                         │
  │  class FilesystemBackend(StorageBackend):               │
  │      """Dev + single-host prod"""                       │
  │      ...                                               │
  │                                                         │
  │  class S3Backend(StorageBackend):                       │
  │      """Multi-host prod"""                              │
  │      ...                                               │
  └─────────────────────────────────────────────────────────┘

  config.py:
    STORAGE_BACKEND: Literal["filesystem", "s3"] = "filesystem"

  Result: flip STORAGE_BACKEND=s3 in environment → horizontal scaling works.
  Dev workflow unchanged. No code changes in content serving logic.

Migration path:
  1. Implement S3Backend (1 file, ~80 lines)
  2. Run pipeline once with STORAGE_BACKEND=s3 → content written to S3
  3. Update content serving to use StorageBackend.presigned_url
  4. Deploy → zero downtime
```

---

### ⚠️ Bad — No API Versioning Policy for Mobile Clients

```
BAD: Mobile clients may not auto-update

  Backend ships /api/v2 with breaking changes
         │
         ▼
  Students on old mobile app (v1) send requests to /api/v1
         │
         ├── If /api/v1 is live:  old students work (good)
         └── If /api/v1 is gone: old students get 404 (incident)

  There is no documented policy for:
    - How long /api/v1 is supported after /api/v2 ships
    - How the mobile app is notified of required upgrades
    - What happens to students on unsupported versions
```

#### 🔧 How to Improve

```
GOOD: Explicit versioning policy documented and enforced

  Policy (to document in ARCHITECTURE.md):
  ┌─────────────────────────────────────────────────────────┐
  │  Version support window: 6 months after next version    │
  │  Deprecation notice: via API response header            │
  │  Forced upgrade: via version-check endpoint             │
  └─────────────────────────────────────────────────────────┘

  Implementation:
  1. Add X-API-Deprecated: true header on /api/v1 responses
     after /api/v2 ships

  2. Mobile startup version check:
     GET /api/version-check?client=mobile&version=1.3.0
     Response: {
       "min_supported": "1.2.0",
       "latest": "1.5.0",
       "update_required": false,
       "deprecation_date": "2026-10-01"
     }

  3. Add to main.py startup:
     if settings.APP_ENV == "production":
         register_deprecated_v1_routes(app)  # adds sunset headers
```

---

## 2. Security Practices

### ✅ Good — Two-Track Authentication with Separate Secrets

```
GOOD: Authentication tracks cannot cross-contaminate

  Student/Teacher track          Admin track
  ┌────────────────────┐        ┌────────────────────┐
  │  Auth0 id_token    │        │  Local bcrypt       │
  │       │            │        │       │             │
  │  JWKS verify       │        │  Hash verify        │
  │       │            │        │       │             │
  │  Internal JWT      │        │  Admin JWT          │
  │  signed with       │        │  signed with        │
  │  JWT_SECRET        │        │  ADMIN_JWT_SECRET   │
  └────────────────────┘        └────────────────────┘
           │                              │
           ▼                              ▼
    /api/v1/content/*           /api/v1/admin/*
    /api/v1/progress/*          (different middleware)
    /api/v1/subscription/*

  A student JWT presented to an admin endpoint → 403 (wrong secret)
  An admin JWT presented to a student endpoint → 403 (wrong secret)
  A teacher JWT presented to a student endpoint → 403 (different role check)

  Pydantic validator prevents the secrets from being the same value:
    secrets_must_differ() → raises if JWT_SECRET == ADMIN_JWT_SECRET
```

---

### ✅ Good — Forgot-Password Always Returns 200

```
GOOD: Email enumeration attack is impossible

  POST /auth/forgot-password {"email": "unknown@example.com"}
  Response: 200 {"message": "If this email is registered, you will receive a link."}

  POST /auth/forgot-password {"email": "real@student.com"}
  Response: 200 {"message": "If this email is registered, you will receive a link."}

  An attacker probing valid emails gets no signal from the status code.

BAD (common mistake, not present here):
  POST /auth/forgot-password {"email": "unknown@example.com"}
  Response: 404 {"error": "Email not found"}  ← leaks registered emails
```

---

### ✅ Good — Stripe Webhook Signature Verification + Idempotency

```
GOOD: Two defensive layers on the webhook handler

  Layer 1: Signature verification
  ┌──────────────────────────────────────────────────────────┐
  │  try:                                                     │
  │      event = stripe.Webhook.construct_event(             │
  │          payload, sig_header, settings.STRIPE_WEBHOOK_SECRET │
  │      )                                                    │
  │  except stripe.error.SignatureVerificationError:         │
  │      raise HTTPException(400)  ← reject unsigned payload │
  └──────────────────────────────────────────────────────────┘

  Layer 2: Event deduplication
  ┌──────────────────────────────────────────────────────────┐
  │  existing = await db.fetchrow(                           │
  │      "SELECT 1 FROM stripe_events WHERE event_id = $1", │
  │       event.id                                           │
  │  )                                                        │
  │  if existing:                                            │
  │      return 200  ← idempotent, already processed         │
  └──────────────────────────────────────────────────────────┘

  Effect: Stripe can safely retry webhook delivery.
  Effect: A replayed attack with a valid payload does nothing.
```

---

### ✅ Good — COPPA/FERPA Controls Are Architecturally Enforced

```
GOOD: Compliance as code, not policy documents

  COPPA — Under-13 account blocking:
    account_status = 'pending'  (set on registration if age < 13)
         │
         ▼
    Content endpoint middleware:
    if student.account_status != 'active':
        raise HTTPException(403, "account_pending_consent")
         │
         ▼
    Parent receives consent email → clicks link → status → 'active'

  FERPA — Cross-school data isolation:
    PostgreSQL RLS policy (migration 0028):
    CREATE POLICY tenant_isolation ON teachers
      USING (school_id = current_setting('app.current_school_id')::uuid);

    Every teacher API request:
    SET LOCAL app.current_school_id = '<school_id_from_jwt>'
         │
         ▼
    SELECT * FROM teachers  → only returns this school's teachers
    (No WHERE clause needed — the DB enforces it)
```

---

### ⚠️ Bad — JWKS Cache Has No TTL Enforcement

```
BAD: TTL setting defined but not enforced

  config.py:
    JWKS_CACHE_TTL_HOURS: int = 1   ← defined

  src/auth/jwt_utils.py:
    jwks_cache: dict = {}            ← plain dict, no TTL

  What actually happens:
  ┌──────────────────────────────────────────────────────────┐
  │  Process start                                            │
  │       │                                                   │
  │       ▼                                                   │
  │  Auth0 JWKS fetched → stored in jwks_cache               │
  │       │                                                   │
  │       ▼                                                   │
  │  1 hour passes ... 10 hours ... 10 days ...               │
  │       │                                                   │
  │  Auth0 rotates signing key ──▶ new key not in cache      │
  │       │                                                   │
  │  Student login: key-not-found triggers one evict+refetch  │
  │  (but the TTL-expired scenario is never triggered)        │
  │       │                                                   │
  │  Auth0 revokes old key ──▶ still trusted until restart   │
  └──────────────────────────────────────────────────────────┘

  Security risk: A revoked signing key remains trusted indefinitely.
```

#### 🔧 How to Improve

```
GOOD: Use cachetools TTLCache (already a project dependency)

  src/auth/jwt_utils.py
  ┌──────────────────────────────────────────────────────────┐
  │  from cachetools import TTLCache                          │
  │  from src.config import settings                          │
  │                                                           │
  │  # TTL in seconds, maxsize=1 (one JWKS set at a time)   │
  │  jwks_cache: TTLCache = TTLCache(                        │
  │      maxsize=1,                                          │
  │      ttl=settings.JWKS_CACHE_TTL_HOURS * 3600            │
  │  )                                                        │
  │                                                           │
  │  async def _get_jwks() -> dict:                          │
  │      if "keys" not in jwks_cache:                        │
  │          jwks_cache["keys"] = await _fetch_jwks()        │
  │      return jwks_cache["keys"]                           │
  └──────────────────────────────────────────────────────────┘

  Effect: After JWKS_CACHE_TTL_HOURS, the next request triggers
  a fresh JWKS fetch. A revoked key is untrusted within 1 hour.

  Complexity: 3 lines changed. Zero behaviour change for happy path.
```

---

### ⚠️ Bad — No Rate Limiting in the FastAPI Layer

```
BAD: Rate limiting gap in the auth endpoints

  Current state:
  ┌──────────────────────────────────────────────────────────┐
  │  nginx.conf                                               │
  │    limit_req_zone $binary_remote_addr zone=api:10m rate=... │
  │    (configuration not reviewed — may or may not exist)   │
  │                                                           │
  │  FastAPI layer:                                           │
  │    POST /auth/register    ← no explicit rate limit       │
  │    POST /auth/login       ← no explicit rate limit       │
  │    POST /auth/exchange    ← no explicit rate limit       │
  │    POST /auth/forgot-password ← no explicit rate limit   │
  └──────────────────────────────────────────────────────────┘

  Attack surface without rate limiting:
  ┌─────────────────────────────────────────────────────────┐
  │  Brute-force login:                                      │
  │    attacker tries 10,000 passwords/minute               │
  │    → bcrypt at cost 12 costs ~250ms each                │
  │    → 10,000 × 250ms = 2,500 seconds of bcrypt work     │
  │    → 4 API workers saturated, all other requests queued │
  │                                                         │
  │  OTP/token enumeration:                                 │
  │    attacker tries all 6-digit codes for reset token     │
  │    → 999,999 attempts, no throttle                      │
  │                                                         │
  │  Demo slot exhaustion:                                  │
  │    attacker creates 100 demo accounts (the hard cap)    │
  │    → all demo slots consumed, no real teachers can demo │
  └─────────────────────────────────────────────────────────┘
```

#### 🔧 How to Improve

```
GOOD: SlowAPI (fastapi-limiter) for endpoint-level rate limiting

  requirements.txt:
    slowapi>=0.1.9

  main.py:
  ┌──────────────────────────────────────────────────────────┐
  │  from slowapi import Limiter, _rate_limit_exceeded_handler│
  │  from slowapi.util import get_remote_address              │
  │  from slowapi.errors import RateLimitExceeded             │
  │                                                           │
  │  limiter = Limiter(key_func=get_remote_address,           │
  │                    storage_uri=settings.REDIS_URL)        │
  │  app.state.limiter = limiter                              │
  │  app.add_exception_handler(RateLimitExceeded,            │
  │                            _rate_limit_exceeded_handler)  │
  └──────────────────────────────────────────────────────────┘

  src/auth/router.py:
  ┌──────────────────────────────────────────────────────────┐
  │  @router.post("/login")                                   │
  │  @limiter.limit("10/minute")   ← per IP                  │
  │  async def login(request: Request, ...): ...             │
  │                                                           │
  │  @router.post("/forgot-password")                        │
  │  @limiter.limit("5/hour")      ← stricter for reset     │
  │  async def forgot_password(request: Request, ...): ...   │
  │                                                           │
  │  @router.post("/demo/request")                           │
  │  @limiter.limit("3/hour")      ← prevent slot exhaustion │
  │  async def demo_request(request: Request, ...): ...      │
  └──────────────────────────────────────────────────────────┘

  Rate limit state stored in Redis → consistent across all workers.
  429 response returns Retry-After header automatically.
```

---

### ⚠️ Bad — Auth0 Management Token Fetched on Every Call

```
BAD: New OAuth exchange on every block/delete

  block_auth0_user(user_id):
    token = _get_mgmt_token()   ← full OAuth client_credentials flow
    PATCH /api/v2/users/{id}

  delete_auth0_user(user_id):
    token = _get_mgmt_token()   ← another full OAuth exchange
    DELETE /api/v2/users/{id}

  Problem:
  ├── Each token request is an HTTPS round-trip to Auth0
  ├── Management tokens are valid for 24 hours (Auth0 default)
  ├── Fetching a new one for every call wastes quota + latency
  └── Under concurrent admin actions → multiple simultaneous token fetches
```

#### 🔧 How to Improve

```
GOOD: Cache the management token in Redis with TTL

  src/auth/auth0_client.py
  ┌──────────────────────────────────────────────────────────┐
  │  MGMT_TOKEN_CACHE_KEY = "auth0:mgmt_token"               │
  │  MGMT_TOKEN_TTL = 82800  # 23 hours (1 hr safety margin) │
  │                                                           │
  │  async def _get_mgmt_token(redis: Redis) -> str:         │
  │      cached = await redis.get(MGMT_TOKEN_CACHE_KEY)      │
  │      if cached:                                          │
  │          return cached.decode()                          │
  │                                                           │
  │      token = await _fetch_mgmt_token_from_auth0()        │
  │      await redis.setex(                                   │
  │          MGMT_TOKEN_CACHE_KEY, MGMT_TOKEN_TTL, token     │
  │      )                                                    │
  │      return token                                         │
  └──────────────────────────────────────────────────────────┘

  Effect: Auth0 management API called once per 23 hours, not per action.
  Bonus: Reduces Auth0 rate-limit exposure during bulk operations.
```

---

## 3. Performance Practices

### ✅ Good — Hot Read Path Touches Zero DB Queries on Cache-Warm Requests

```
GOOD: Request serviced entirely from memory on cache hit

  GET /api/v1/content/{unit_id}/lesson
        │
        ▼
  JWT verify (in-process, ~0.1ms)
        │
        ▼
  L1 TTLCache: ent:{student_id} hit? ──yes──▶ entitlement confirmed
        │                                       │
       no                                       ▼
        │                               L1: content:{unit_id} hit?
        ▼                                ──yes──▶ return JSON  ~1ms total
  L2 Redis: ent:{student_id} hit? ──yes──▶ entitlement confirmed
        │
       no
        │
        ▼
  L3 PostgreSQL query (~5-15ms)

  Cache hit rate target: 95% (from SCALABILITY.md)
  Hot path latency target: <20ms p99
```

---

### ✅ Good — bcrypt Runs in an Executor

```
GOOD: CPU-bound hashing does not block the event loop

  BAD pattern (not used):
    password_hash = bcrypt.hashpw(...)  ← blocks event loop for ~250ms
    # No other requests serviced during this 250ms

  GOOD pattern (used):
    loop = asyncio.get_event_loop()
    password_hash = await loop.run_in_executor(
        None,                          # default ThreadPoolExecutor
        bcrypt.hashpw,
        password.encode(),
        bcrypt.gensalt(rounds=12)
    )
    # Event loop free during hashing; other requests continue
```

---

### ✅ Good — Audio Is Never Proxied Through the API

```
GOOD: CDN handles all audio bytes

  BAD pattern (not used):
    GET /api/v1/content/{unit_id}/audio
    → FastAPI reads MP3 from disk
    → FastAPI streams 3-8 MB through the API server
    → API worker tied up for 2-10 seconds per audio request

  GOOD pattern (used):
    GET /api/v1/content/{unit_id}/lesson/audio
    → FastAPI generates pre-signed CloudFront URL (1 DB/cache lookup)
    → Returns {"audio_url": "https://cdn.studybuddy.com/...?sig=...&exp=..."}
    → Client fetches MP3 bytes directly from CDN
    → API worker free in <5ms
```

---

### ⚠️ Bad — Stripe SDK Calls Are Synchronous in an Async Router

```
BAD: Synchronous I/O blocks the event loop

  src/subscription/router.py (docstring even admits this):
    "Stripe API calls are made synchronously (Stripe SDK is sync).
     For production load, consider wrapping in run_in_executor."

  What happens under load:
  ┌──────────────────────────────────────────────────────────┐
  │  Event loop timeline (4 concurrent Stripe checkouts)     │
  │                                                           │
  │  t=0ms   Request A arrives → stripe.checkout.create()   │
  │  t=0ms   Event loop BLOCKED waiting for Stripe HTTP      │
  │  t=800ms Stripe responds to A → loop free briefly        │
  │  t=800ms Request B starts → stripe.checkout.create()    │
  │  t=800ms Event loop BLOCKED again                        │
  │                                                           │
  │  Requests C and D sit waiting for 800ms+ each            │
  │  Other endpoints (progress, curriculum) also blocked     │
  └──────────────────────────────────────────────────────────┘

  Under 100 concurrent checkouts → event loop effectively single-threaded
  for the duration of all Stripe calls.
```

#### 🔧 How to Improve

```
GOOD: Wrap all Stripe calls in run_in_executor

  src/subscription/service.py
  ┌──────────────────────────────────────────────────────────┐
  │  import asyncio                                           │
  │  import functools                                         │
  │                                                           │
  │  async def create_checkout_session(                      │
  │      school_id: UUID, plan: str                          │
  │  ) -> stripe.checkout.Session:                           │
  │      loop = asyncio.get_event_loop()                     │
  │      return await loop.run_in_executor(                  │
  │          None,                                           │
  │          functools.partial(                              │
  │              stripe.checkout.Session.create,            │
  │              mode="subscription",                        │
  │              ...                                         │
  │          )                                               │
  │      )                                                    │
  └──────────────────────────────────────────────────────────┘

  Alternative: stripe-python-async (third-party async wrapper)
    pip install stripe-async
    session = await stripe_async.checkout.Session.create(...)

  Effect: Stripe HTTP round-trip runs in thread pool.
  Event loop free during the wait. Other requests serviced normally.
  Estimated effort: 2-3 hours to wrap all Stripe call sites.
```

---

### ⚠️ Bad — `DATABASE_POOL_MAX × worker_count` May Exceed PgBouncer Pool

```
BAD: Connection arithmetic not validated

  config.py:
    DATABASE_POOL_MAX: int = 20   (per worker)

  docker-compose.yml:
    pgbouncer:
      DEFAULT_POOL_SIZE: 50

  Deployment (4 gunicorn workers):
    4 workers × 20 max connections = 80 connections requested
    PgBouncer pool size = 50

  Result:
  ┌──────────────────────────────────────────────────────────┐
  │  Workers 1-2 (40 conns) ──▶ PgBouncer (50 max) ──▶ OK  │
  │  Worker 3 (60 total)    ──▶ PgBouncer FULL              │
  │  Worker 4 (80 total)    ──▶ PgBouncer FULL              │
  │                                                           │
  │  Under load: "connection pool exhausted" errors          │
  │  Intermittent 500s with no obvious log cause             │
  └──────────────────────────────────────────────────────────┘
```

#### 🔧 How to Improve

```
GOOD: Enforce the arithmetic with a startup assertion

  backend/config.py
  ┌──────────────────────────────────────────────────────────┐
  │  class Settings(BaseSettings):                           │
  │      DATABASE_POOL_MAX: int = 20                         │
  │      GUNICORN_WORKERS: int = 4                           │
  │      PGBOUNCER_POOL_SIZE: int = 50                       │
  │                                                           │
  │      @model_validator(mode="after")                      │
  │      def validate_pool_arithmetic(self) -> "Settings":   │
  │          total = self.DATABASE_POOL_MAX *                │
  │                  self.GUNICORN_WORKERS                   │
  │          if total > self.PGBOUNCER_POOL_SIZE:            │
  │              raise ValueError(                           │
  │                  f"Pool overflow: {total} connections    │
  │                   requested, PgBouncer max is            │
  │                   {self.PGBOUNCER_POOL_SIZE}. Set        │
  │                   DATABASE_POOL_MAX ≤               │
  │                   {self.PGBOUNCER_POOL_SIZE //           │
  │                    self.GUNICORN_WORKERS}"               │
  │              )                                           │
  │          return self                                      │
  └──────────────────────────────────────────────────────────┘

  Startup: if misconfigured, the process refuses to start.
  No silent degradation at runtime.

  Correct sizing:
    DATABASE_POOL_MAX = floor(PGBOUNCER_POOL_SIZE / WORKERS) - 1
    = floor(50 / 4) - 1 = 11   (leave headroom for admin connections)
```

---

## 4. Code Quality Practices

### ✅ Good — Structured Logging with Correlation IDs

```
GOOD: Every log entry is queryable and traceable

  Request arrives → CorrelationIdMiddleware assigns UUID
       │
       ▼
  X-Correlation-ID: "a1b2c3d4-..." injected into request state
       │
       ▼
  Every log call:
    log.info("content_served",
        student_id=student_id,
        unit_id=unit_id,
        curriculum_id=curriculum_id,
        correlation_id=request.state.correlation_id,  ← always present
        cache_hit="l1",
        duration_ms=12
    )

  CloudWatch query:
    fields @message | filter correlation_id = "a1b2c3d4-..."
    → returns every log line from that request, across all workers

  Never log:
    passwords, JWT tokens, API keys, student PII beyond auth context
```

---

### ✅ Good — Sentry PII Scrubbing Is Explicit

```
GOOD: Error reports never contain secrets or PII

  src/core/sentry.py:
    def _before_send(event, hint):
        for field in ["data", "email", "password", "token",
                      "refresh_token", "id_token"]:
            if field in event.get("request", {}).get("data", {}):
                event["request"]["data"][field] = "[Filtered]"
        return event

  stripe.api_key never appears in a log statement.
  JWT payload never appears in a Sentry breadcrumb.
  Student email appears only in auth context at INFO level.
```

---

### ⚠️ Bad — `verify_auth0_token` and `verify_auth0_teacher_token` Are 90% Duplicated

```
BAD: Two functions sharing 90% identical logic

  verify_auth0_token(id_token):          verify_auth0_teacher_token(id_token):
    jwks = await _get_jwks()               jwks = await _get_jwks()
    kid = _extract_kid(id_token)           kid = _extract_kid(id_token)
    key = _find_key(jwks, kid)             key = _find_key(jwks, kid)
    if not key:                            if not key:
        evict_cache()                          evict_cache()
        jwks = await _get_jwks()               jwks = await _get_jwks()
        key = _find_key(jwks, kid)             key = _find_key(jwks, kid)
    return jwt.decode(                     return jwt.decode(
        id_token, key,                         id_token, key,
        audience=STUDENT_AUDIENCE,  ←DIFF      audience=TEACHER_AUDIENCE, ←DIFF
        algorithms=["RS256"]                   algorithms=["RS256"]
    )                                      )

  Bugs fixed in one function must be manually mirrored to the other.
  The JWKS eviction logic was already slightly different between the two.
```

#### 🔧 How to Improve

```
GOOD: Single implementation, audience as parameter

  src/auth/jwt_utils.py
  ┌──────────────────────────────────────────────────────────┐
  │  async def _verify_auth0_token(                          │
  │      id_token: str,                                      │
  │      audience: str                                       │
  │  ) -> dict:                                              │
  │      """Verify an Auth0 id_token against the JWKS.      │
  │      audience: STUDENT_AUDIENCE or TEACHER_AUDIENCE      │
  │      """                                                  │
  │      jwks = await _get_jwks()                            │
  │      kid = _extract_kid(id_token)                        │
  │      key = _find_key(jwks, kid)                          │
  │      if not key:                                         │
  │          _evict_jwks_cache()                             │
  │          jwks = await _get_jwks()                        │
  │          key = _find_key(jwks, kid)                      │
  │      return jwt.decode(id_token, key,                    │
  │                        audience=audience,                │
  │                        algorithms=["RS256"])             │
  │                                                           │
  │  async def verify_auth0_token(id_token: str) -> dict:    │
  │      return await _verify_auth0_token(                   │
  │          id_token, settings.AUTH0_STUDENT_AUDIENCE       │
  │      )                                                    │
  │                                                           │
  │  async def verify_auth0_teacher_token(id_token: str):    │
  │      return await _verify_auth0_token(                   │
  │          id_token, settings.AUTH0_TEACHER_AUDIENCE       │
  │      )                                                    │
  └──────────────────────────────────────────────────────────┘

  Result: One implementation. Public interface unchanged.
  Any future JWKS logic change applies to both tracks automatically.
```

---

### ⚠️ Bad — `upsert_student` Does Not Update `account_status` on Conflict

```
BAD: A correctness bug in the upsert logic

  SQL (current):
    INSERT INTO students (id, name, email, grade, locale, account_status)
    VALUES ($1, $2, $3, $4, $5, $6)
    ON CONFLICT (email) DO UPDATE SET
        name = EXCLUDED.name,
        grade = EXCLUDED.grade,
        locale = EXCLUDED.locale
        -- account_status NOT updated ← bug

  Scenario:
    1. Student registers from context requiring parental consent
       → account_status = 'pending'
    2. Student re-registers from a context where consent is not required
       (e.g., a different auth0 flow, or an older user)
    3. ON CONFLICT fires → name/grade/locale updated
    4. account_status remains 'pending' ← student permanently locked out
```

#### 🔧 How to Improve

```
GOOD: Conditional update with explicit business rule

  SQL (fixed):
    INSERT INTO students (id, name, email, grade, locale, account_status)
    VALUES ($1, $2, $3, $4, $5, $6)
    ON CONFLICT (email) DO UPDATE SET
        name = EXCLUDED.name,
        grade = EXCLUDED.grade,
        locale = EXCLUDED.locale,
        account_status = CASE
            -- Only upgrade from pending → active, never downgrade
            WHEN students.account_status = 'pending'
             AND EXCLUDED.account_status = 'active'
            THEN 'active'
            ELSE students.account_status
        END

  Add to test_auth.py:
    async def test_upsert_upgrades_pending_to_active():
        # Insert with pending status
        await upsert_student(..., account_status='pending')
        # Re-register with active status
        await upsert_student(..., account_status='active')
        student = await get_student_by_email(email)
        assert student.account_status == 'active'  ← was failing before
```

---

### ⚠️ Bad — Router Imports at Bottom of `main.py` (Circular Import Smell)

```
BAD: Import order forced by circular dependency

  main.py:
    from fastapi import FastAPI           ← top of file
    from src.core.db import init_db       ← top of file
    from src.core.cache import init_redis ← top of file

    app = FastAPI()

    # ... 50 lines of app setup ...

    from src.auth.router import router as auth_router    # noqa: E402
    from src.content.router import router as content_router  # noqa: E402
    from src.school.router import router as school_router    # noqa: E402
    # ...12 more like this, all with # noqa: E402

  The # noqa comments acknowledge the problem.
  The problem is circular imports caused by modules importing from main.py
  or from each other in a cycle.
```

#### 🔧 How to Improve

```
GOOD: Application factory pattern breaks the cycle

  main.py (after refactor):
  ┌──────────────────────────────────────────────────────────┐
  │  from src.app import create_app                           │
  │                                                           │
  │  app = create_app()                                       │
  └──────────────────────────────────────────────────────────┘

  src/app.py:
  ┌──────────────────────────────────────────────────────────┐
  │  from fastapi import FastAPI                              │
  │  from contextlib import asynccontextmanager              │
  │                                                           │
  │  def create_app() -> FastAPI:                            │
  │      from src.auth.router import router as auth_router   │
  │      from src.content.router import router               │
  │      # all router imports here — no global state yet     │
  │                                                           │
  │      @asynccontextmanager                                │
  │      async def lifespan(app: FastAPI):                   │
  │          await init_db(app)                              │
  │          await init_redis(app)                           │
  │          yield                                           │
  │          await cleanup(app)                              │
  │                                                           │
  │      app = FastAPI(lifespan=lifespan)                    │
  │      app.include_router(auth_router)                     │
  │      app.include_router(router)                          │
  │      return app                                          │
  └──────────────────────────────────────────────────────────┘

  All imports happen inside create_app() after module loading is complete.
  No # noqa needed. No circular imports.
  Bonus: testable — tests can call create_app() with different configs.
```

---

## 5. Testing Practices

### ✅ Good — Real Postgres in CI via Alembic

```
GOOD: Schema drift is caught before production

  CI pipeline:
    1. Start PostgreSQL container
    2. Run alembic upgrade head  ← applies all 29 migrations to test DB
    3. pytest                    ← tests run against real schema

  Effect: If migration 0026 has a typo in a column name,
  CI fails at step 2 before any tests run.
  No "works on my machine" migration issues reach production.

  Contrast with mocked schema (bad):
    pytest --use-mock-db  ← tests pass even if real migration fails
    deploy to production  ← alembic upgrade head fails at step 1
    incident              ← site down until migration fixed
```

---

### ✅ Good — Token Factory Provides Deterministic Test JWTs

```
GOOD: Auth0 not called in tests; tokens are predictable

  tests/helpers/token_factory.py:
    def make_student_token(
        student_id=FIXED_STUDENT_UUID,   ← deterministic
        grade=8,
        locale="en",
        exp=9999999999                   ← far future, never expires in CI
    ) -> str:
        return jwt.encode({
            "student_id": str(student_id),
            "grade": grade,
            "locale": locale,
            "role": "student",
            "exp": exp
        }, settings.JWT_SECRET, algorithm="HS256")

  Tests:
    headers = {"Authorization": f"Bearer {make_student_token()}"}
    response = await client.get("/api/v1/content/...", headers=headers)

  No Auth0 mock needed. No network call. Runs offline.
  The token factory is the single source of truth for test tokens.
```

---

### ⚠️ Bad — 70% Coverage Threshold Is Too Low for a Children's SaaS

```
BAD: Coverage floor does not reflect risk profile

  Current:
    --cov-fail-under=70  (all modules, no differentiation)

  Risk profile of the modules:

  Module                  Risk Level    Appropriate Coverage
  ─────────────────────────────────────────────────────────
  src/auth/               CRITICAL      ≥ 90%
    (JWT, session, COPPA)
  src/subscription/       CRITICAL      ≥ 90%
    (Stripe, billing, entitlement)
  src/progress/           HIGH          ≥ 85%
    (student learning records)
  src/school/             HIGH          ≥ 85%
    (FERPA-scoped data)
  src/admin/              MEDIUM        ≥ 80%
  src/content/            MEDIUM        ≥ 80%
  src/analytics/          LOW-MEDIUM    ≥ 75%
  src/demo/               LOW           ≥ 70%

  Current 70% flat threshold allows auth to have 70% coverage
  while src/demo/ also has 70% — same floor for very different risk.
```

#### 🔧 How to Improve

```
GOOD: Per-module coverage thresholds in pyproject.toml

  pyproject.toml:
  ┌──────────────────────────────────────────────────────────┐
  │  [tool.coverage.report]                                   │
  │  fail_under = 75  # global floor                         │
  │                                                           │
  │  [tool.coverage.paths]                                    │
  │  # Per-module thresholds enforced separately in CI       │
  └──────────────────────────────────────────────────────────┘

  CI script (check_coverage.py):
  ┌──────────────────────────────────────────────────────────┐
  │  THRESHOLDS = {                                           │
  │      "src/auth": 90,                                      │
  │      "src/subscription": 90,                             │
  │      "src/progress": 85,                                  │
  │      "src/school": 85,                                    │
  │      "src/admin": 80,                                     │
  │      "src/content": 80,                                   │
  │      "src/analytics": 75,                                 │
  │      "src/demo": 70,                                      │
  │  }                                                        │
  │                                                           │
  │  for module, threshold in THRESHOLDS.items():            │
  │      actual = get_coverage(module)                        │
  │      if actual < threshold:                              │
  │          fail(f"{module}: {actual}% < {threshold}%")     │
  └──────────────────────────────────────────────────────────┘
```

---

### ⚠️ Bad — No End-to-End Tests

```
BAD: Backend and frontend tested in isolation only

  Current test landscape:
  ┌─────────────────────────────────────────────────────────┐
  │                                                          │
  │  Backend unit tests ✅        215 passing               │
  │  Mobile logic tests ✅        EventQueue, SyncManager   │
  │  Pipeline unit tests ✅       Mocked Anthropic          │
  │                                                          │
  │  E2E tests ❌                 Not present               │
  │  Frontend component tests ❌  Not present               │
  │                                                          │
  └─────────────────────────────────────────────────────────┘

  Gap: These flows are never tested as a whole:
    Student registers → enrolled → accesses content → submits quiz
    → progress recorded → school admin sees report
    → school admin uploads new curriculum → pipeline runs
    → admin approves → students see new content

  A regression in any cross-layer interaction goes undetected
  until a real user encounters it.
```

#### 🔧 How to Improve

```
GOOD: Playwright E2E suite for critical student flows

  tests/e2e/ (new directory):
    test_student_flow.py
    test_school_admin_flow.py
    test_content_review_flow.py

  tests/e2e/test_student_flow.py:
  ┌──────────────────────────────────────────────────────────┐
  │  async def test_student_learning_loop(page: Page):       │
  │      # 1. Student lands on public page                   │
  │      await page.goto("http://localhost:3000")            │
  │                                                           │
  │      # 2. Registers (or logs in via Auth0 stub)          │
  │      await page.click("[data-testid=login]")             │
  │                                                           │
  │      # 3. Sees curriculum map                            │
  │      await expect(page.locator(".curriculum-map"))       │
  │          .to_be_visible()                                 │
  │                                                           │
  │      # 4. Opens a lesson                                 │
  │      await page.click("[data-testid=lesson-G8-MATH-001]")│
  │      await expect(page.locator(".lesson-content"))       │
  │          .to_be_visible()                                 │
  │                                                           │
  │      # 5. Submits quiz answers                           │
  │      # 6. Sees result screen with score                  │
  │      # 7. Progress reflected in history                  │
  └──────────────────────────────────────────────────────────┘

  Run in CI:
    On every PR: 3 critical-path tests (register → lesson → quiz)
    Nightly: full suite (20-30 scenarios)
```

---

## 6. Data Practices

### ✅ Good — PostgreSQL Row-Level Security for Tenant Isolation

```
GOOD: Isolation is a database guarantee, not an application promise

  Without RLS (application-layer isolation):
  ┌──────────────────────────────────────────────────────────┐
  │  SELECT * FROM teachers                                   │
  │  WHERE school_id = $1    ← developer forgets this clause │
  │                          ← returns ALL schools' teachers  │
  │                          ← FERPA violation               │
  └──────────────────────────────────────────────────────────┘

  With RLS (database-layer isolation):
  ┌──────────────────────────────────────────────────────────┐
  │  SET LOCAL app.current_school_id = 'school-A-uuid'       │
  │                                                           │
  │  SELECT * FROM teachers   ← developer forgets WHERE      │
  │                           ← PostgreSQL applies RLS policy │
  │                           ← returns ONLY school-A rows   │
  │                           ← FERPA-compliant by default   │
  └──────────────────────────────────────────────────────────┘

  Security audit statement:
  "Cross-tenant data access is prevented at the database engine level,
   regardless of application code correctness."
```

---

### ⚠️ Bad — No Stripe Webhook for `invoice.payment_action_required`

```
BAD: European students cannot complete SCA/3DS payments

  Current webhook handlers:
    invoice.payment_succeeded       ✅
    invoice.payment_failed          ✅
    customer.subscription.updated   ✅
    customer.subscription.deleted   ✅
    invoice.payment_action_required ❌  ← missing

  What happens without this handler:
  ┌──────────────────────────────────────────────────────────┐
  │  European school admin subscribes                         │
  │  → Stripe requires 3D Secure (SCA regulation)            │
  │  → Stripe sends invoice.payment_action_required          │
  │  → No handler → event ignored                            │
  │  → School admin's bank declines after 3DS timeout        │
  │  → School subscription goes to 'past_due'                │
  │  → No notification sent (handler not there to send it)   │
  │  → Admin has no idea why their subscription failed       │
  └──────────────────────────────────────────────────────────┘
```

#### 🔧 How to Improve

```
GOOD: Add the missing webhook handler

  src/subscription/webhook_router.py:
  ┌──────────────────────────────────────────────────────────┐
  │  elif event.type == "invoice.payment_action_required":   │
  │      invoice = event.data.object                         │
  │      customer_id = invoice.customer                      │
  │      school = await get_school_by_stripe_customer(       │
  │          customer_id, db                                  │
  │      )                                                    │
  │      if school:                                          │
  │          # Send action-required email to school admin    │
  │          await celery.send_task(                         │
  │              "tasks.send_payment_action_required_email", │
  │              args=[school.id,                            │
  │                    invoice.hosted_invoice_url]            │
  │          )                                               │
  │          # Log to audit                                  │
  │          await write_audit_log(                          │
  │              action="PAYMENT_ACTION_REQUIRED",           │
  │              target_id=school.id                         │
  │          )                                               │
  └──────────────────────────────────────────────────────────┘

  The hosted_invoice_url gives the school admin a direct link
  to complete 3DS authentication in their bank's UI.
  No custom payment flow needed — Stripe hosts it.
```

---

## 7. Operational Practices

### ✅ Good — Health and Metrics Endpoints Exist

```
GOOD: Every component is observable from day one

  /health  → liveness (is the process running?)
  /metrics → Prometheus metrics (scrape every 15s)

  Metrics exposed:
    http_request_duration_seconds{endpoint, method, status}
    cache_hit_total{level, type}
    celery_task_duration_seconds{task_name}
    content_served_total{grade, subject, lang}
    stripe_webhook_processed_total{event_type, status}
```

---

### ✅ Good — Dependabot for Automated Dependency Updates

```
GOOD: CVE surface is actively managed

  .github/dependabot.yml:
    schedule: weekly
    targets: pip, npm, docker

  Effect:
    A critical CVE in a Python dependency → Dependabot PR within 24h
    A major version update → Dependabot PR for review
    pip-audit in CI → fails if a known CVE is present in requirements.txt
    Snyk integration → deeper transitive dependency scanning
```

---

### ⚠️ Bad — No Runbooks for Common Failure Scenarios

```
BAD: Incidents require investigation from scratch

  When this happens:          The on-call engineer must...
  ─────────────────────────   ──────────────────────────────────
  DB connection exhausted     grep logs, figure out PgBouncer
                              settings, guess pool config
  Redis OOM                   unclear what to evict, what to
                              restart, what data is lost
  Stripe webhook backlog       unclear if webhook needs retry,
                              what the retry policy is
  Pipeline failure             unclear if content is partial,
                              whether to re-run with --force
  Celery Beat crash            unclear which scheduled tasks
                              were missed, what to run manually

  Without runbooks, every incident is a first-time incident.
```

#### 🔧 How to Improve

```
GOOD: Runbooks in OPERATIONS.md (one section per failure type)

  OPERATIONS.md template for each runbook:
  ┌──────────────────────────────────────────────────────────┐
  │  ## DB Connection Pool Exhausted                          │
  │                                                           │
  │  Symptoms:                                               │
  │    "connection pool exhausted" in API logs               │
  │    HTTP 500 on database-backed endpoints                 │
  │    Prometheus: db_pool_exhausted_total rising            │
  │                                                           │
  │  Diagnosis:                                              │
  │    docker compose exec pgbouncer psql ... SHOW POOLS;   │
  │    → check cl_waiting (clients waiting for connection)   │
  │                                                           │
  │  Immediate mitigation:                                   │
  │    docker compose restart api  ← resets worker pools    │
  │                                                           │
  │  Root cause fixes:             (in order of preference)  │
  │    1. Reduce DATABASE_POOL_MAX (see config arithmetic)   │
  │    2. Scale PgBouncer DEFAULT_POOL_SIZE                 │
  │    3. Add a worker → recheck pool arithmetic             │
  │                                                           │
  │  Recovery validation:                                    │
  │    curl /health → 200                                    │
  │    Prometheus: db_pool_exhausted_total flattens          │
  └──────────────────────────────────────────────────────────┘

  Priority: Write the 5 runbooks above. Each takes 30-60 minutes.
  The first time they are used pays for them.
```

---

### ⚠️ Bad — Celery Beat Is a Single Point of Failure

```
BAD: Scheduled tasks silently miss if beat crashes

  Current:
  ┌──────────────────────────────────────────────────────────┐
  │  celery-beat (single instance)                            │
  │    ├── grade_promotion_task      (runs annually)         │
  │    ├── retention_alert_task      (runs weekly)           │
  │    ├── weekly_teacher_digest     (runs weekly)           │
  │    └── lesson_nudge_task         (runs daily)            │
  │                                                           │
  │  If celery-beat crashes:                                 │
  │    → No alert (no health check on beat)                  │
  │    → No scheduled tasks run                              │
  │    → Grade promotion silently skipped                    │
  │    → Retention alerts silently skipped                   │
  │    → Teachers stop receiving digests                     │
  │    → Discovery: manual review of Celery logs             │
  └──────────────────────────────────────────────────────────┘
```

#### 🔧 How to Improve

```
GOOD: Replace celery-beat with celery-redbeat (Redis-backed)

  pip install celery-redbeat

  src/core/celery_app.py:
  ┌──────────────────────────────────────────────────────────┐
  │  app.conf.beat_scheduler = "redbeat.RedBeatScheduler"    │
  │  app.conf.redbeat_redis_url = settings.REDIS_URL         │
  │  app.conf.redbeat_lock_timeout = 5 * 60  # 5 min lock   │
  └──────────────────────────────────────────────────────────┘

  Result:
  ┌──────────────────────────────────────────────────────────┐
  │  celery-beat instance A (running)  ← holds Redis lock   │
  │  celery-beat instance B (standby)  ← waiting for lock   │
  │                                                           │
  │  If instance A crashes:                                  │
  │    → Redis lock expires after 5 minutes                  │
  │    → Instance B acquires lock                            │
  │    → Scheduled tasks resume                              │
  │    → No manual intervention needed                       │
  └──────────────────────────────────────────────────────────┘

  Alternative: Kubernetes CronJob per task (if deploying to K8s)
  → each task is an independent job; no single beat process.
```

---

## 8. Summary Scorecard

```
┌──────────────────────────────────────────────────────────────────────┐
│  StudyBuddy OnDemand — Practices Scorecard                            │
├─────────────────────────────┬──────────┬────────────────────────────┤
│  Practice Area              │  Rating  │  Priority Fix               │
├─────────────────────────────┼──────────┼────────────────────────────┤
│  Three-context separation   │  ✅ Good  │  —                         │
│  Pre-generation model       │  ✅ Good  │  —                         │
│  Layer dependency direction │  ✅ Good  │  —                         │
│  Two-track auth + secrets   │  ✅ Good  │  —                         │
│  Forgot-password 200        │  ✅ Good  │  —                         │
│  Stripe sig + idempotency   │  ✅ Good  │  —                         │
│  COPPA/FERPA as code        │  ✅ Good  │  —                         │
│  Hot read path caching      │  ✅ Good  │  —                         │
│  bcrypt in executor         │  ✅ Good  │  —                         │
│  Audio via CDN              │  ✅ Good  │  —                         │
│  Correlation ID logging     │  ✅ Good  │  —                         │
│  Sentry PII scrubbing       │  ✅ Good  │  —                         │
│  Real Postgres in CI        │  ✅ Good  │  —                         │
│  Token factory pattern      │  ✅ Good  │  —                         │
│  Health + metrics endpoints │  ✅ Good  │  —                         │
│  PostgreSQL RLS             │  ✅ Good  │  —                         │
├─────────────────────────────┼──────────┼────────────────────────────┤
│  JWKS cache has no TTL      │  ⚠️  Bad  │  P0 — 3-line fix           │
│  Stripe calls synchronous   │  ⚠️  Bad  │  P0 — 2-3hr refactor       │
│  Content store on filesystem│  ⚠️  Bad  │  P0 — before multi-host    │
│  No rate limiting on auth   │  ⚠️  Bad  │  P1 — 1 day with SlowAPI   │
│  Celery app in auth module  │  ⚠️  Bad  │  P1 — rename + update yml  │
│  Duplicated auth0 verify    │  ⚠️  Bad  │  P1 — 30min refactor       │
│  upsert_student status bug  │  ⚠️  Bad  │  P1 — 1 SQL CASE fix       │
│  Pool arithmetic not checked│  ⚠️  Bad  │  P1 — startup validator    │
│  Router imports at bottom   │  ⚠️  Bad  │  P2 — factory pattern      │
│  70% coverage threshold     │  ⚠️  Bad  │  P1 — raise to 80/90%      │
│  No E2E tests               │  ⚠️  Bad  │  P2 — Playwright suite     │
│  No SCA webhook handler     │  ⚠️  Bad  │  P1 — 1 event handler      │
│  Auth0 mgmt token uncached  │  ⚠️  Bad  │  P2 — Redis cache 23h      │
│  No API versioning policy   │  ⚠️  Bad  │  P2 — document + header    │
│  No runbooks                │  ⚠️  Bad  │  P2 — 5 runbooks           │
│  Celery Beat is SPOF        │  ⚠️  Bad  │  P2 — redbeat or K8s cron  │
└─────────────────────────────┴──────────┴────────────────────────────┘

P0 = Fix before any multi-host deployment
P1 = Fix before first production users
P2 = Fix before scale / after launch
```

---

*Analysis based on code, CLAUDE.md, ADR-001, migrations, and critique documents. April 2026.*
