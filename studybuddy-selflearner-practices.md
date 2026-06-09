# StudyBuddy SelfLearner (Mentible) — Good Practices, Bad Practices & How to Improve

**Document type:** Engineering practices analysis
**Scope:** Backend (FastAPI/Python), Mobile (React Native/Expo), Compiler (TypeScript/Node), Pipeline (vendored), Infrastructure
**Period:** 2026-06-02 (v1.0 — first analysis; measured on disk at `e1c66f7`, branch `feat/authoring-regenerate-export-fixes`)
**Repo / brand:** `wegofwd2020-hub/StudyBuddy_SelfLearner` · public brand **Mentible**
**Related:** [studybuddy-selflearner-critique.md](studybuddy-selflearner-critique.md) · [studybuddy-selflearner-development-pattern.md](studybuddy-selflearner-development-pattern.md) · [studybuddy-selflearner-cost.md](studybuddy-selflearner-cost.md) · parent product: [studybuddy-practices.md](studybuddy-practices.md)
**Rating key:** ✅ Good practice · ⚠️ Bad practice · 🔧 How to improve

> A catalogue of concrete practices observed in the Mentible codebase, with fixes. The through-line: **the security practices are exemplary; the discipline gaps are all about the distance between an accepted decision (or a stale spec) and the code that exists.**

---

## ✅ Good Practices

### ✅ Make the core security invariant an enforced test, not a comment

The product's entire trust proposition is "we handle your Anthropic key safely." So the invariant is a test: `backend/tests/test_no_key_in_logs.py` asserts no log line in any code path contains the test key, and a dedicated CI job (`no-real-key-in-repo`) greps the *whole repo* for a committed `sk-ant-` value on every push. The invariant cannot regress silently.

🔧 *Reusable takeaway:* when a product has one non-negotiable property, write the test that fails if it's ever violated **before** the feature, and gate CI on it.

### ✅ BYOK key lifecycle: encrypt-per-job, TTL, shred — on every path

`byok_envelope.py` AES-256-GCM-encrypts the key under a per-job key derived via HKDF-SHA256(master, salt=`job_id`); the master `BYOK_MASTER_KEY` is a 64-hex env var with **no default** (startup fails if unset); TTL defaults to 120 s; the worker re-derives the key (HKDF is deterministic, so plaintext never round-trips through Redis) and the `finally` block does `del api_key` + `DEL byok:{id}` on success and failure alike.

🔧 *One gap to document:* CPython string immutability means `del api_key` can't truly zero the in-process copy. Note in ADR-001's threat model that the in-memory shred is best-effort while the Redis deletion is genuine.

### ✅ Redact secrets by field name *and* value regex

`core/log_redaction.py` is a structlog processor that redacts both known field names (`api_key`, `authorization`, `token`, …) and any value matching `sk-ant-[A-Za-z0-9_\-]{8,}`. Belt and suspenders — a key leaks neither by a known field nor by appearing in an arbitrary string.

### ✅ Log exception *types*, never exception *bodies*, on the key path

The Anthropic caller logs `type(exc).__name__` only — never the message or `exc_info`, because an SDK exception repr can embed the request (and thus the key) — and re-raises `AnthropicCallError` `from None` to drop the chained context.

### ✅ Vendor with recorded provenance, modify deliberately

`pipeline/VENDORED.md` records the source repo + per-file SHA, marks which files are verbatim vs modified vs explicitly-not-vendored, and `scripts/sync-from-ondemand.sh` makes re-syncing a deliberate, reviewable act. The two *modified* copies (`anthropic.py` for per-call BYOK, `toc_structurer.py` with the network wrapper removed so an error path can't stringify the key) document *why* they diverge. Copying code without provenance is debt; this is copying done right.

### ✅ Idempotency + bounded retry on the generation path

`/generate` dedups on a client `request_id` (`req:{id}` Redis key) so a retried submit doesn't double-spend the user's tokens; the worker retries invalid-JSON/schema failures up to 6× before failing the job; every response is `model_validate`-d against `LessonOutput` before it reaches the client.

### ✅ Isolate the heavy/risky runtime as a subprocess

The EPUB3/PDF compiler is a separate, key-free, network-free TypeScript CLI invoked over stdin/stdout. The secret-handling surface and the headless-Chromium/Vivliostyle rendering surface live in different processes.

### ✅ Single source of brand truth

`mobile/src/constants/brand.ts` holds `BRAND_NAME`/`BRAND_TAGLINE`; the Mentible rebrand flowed from one constant. The `app.json` identifiers staying `studybuddy-q` is a *documented* intentional inconsistency (pending trademark clearance), not an oversight.

### ✅ Config fails fast, no secret defaults

`pydantic-settings`; `BYOK_MASTER_KEY`, `REDIS_URL`, `ANTHROPIC_DEFAULT_MODEL` required at startup. No silent fallback to an insecure default in app code.

---

## ⚠️ Bad Practices (and 🔧 fixes)

### ⚠️ The plan says Celery; the code is an in-process `BackgroundTask`

`MVP_v1.md` and several docstrings describe a Celery worker; the implementation is a FastAPI `BackgroundTask`. A process restart silently drops in-flight (minutes-long) jobs and leaves an encrypted envelope in Redis until TTL.

🔧 Either implement the Celery/Redis worker, or make the spec tell the truth and add a one-line user-visible caveat that an in-flight job can be lost on redeploy. Don't let three documents disagree.

### ⚠️ Doc drift: `SCOPE.md`/`CLAUDE.md`/`STATUS.md` predate the current product

`CLAUDE.md` still says "Pre-MVP — directory stubs only, no application code yet"; `SCOPE.md` describes a single free app; `STATUS.md` is pinned to an old branch. The real product (Mentible, two-product split, paid app, ~11k LOC, working compiler) is described only in the ADRs.

🔧 **Promote the ADR outcomes into the durable spec.** An ADR is half-done until the `SCOPE.md`/`CLAUDE.md` it changes is updated. This is the exact doc-drift class the team polices well in OnDemand — apply the same rigor here.

### ⚠️ CORS `allow_origins=["*"]` on an endpoint that carries the user's key

Acceptable only because there's no cookie/session yet.

🔧 Lock to the app's origins before any public URL exists; revisit when auth lands.

### ⚠️ No rate limiting, no queue-depth cap, no auth

By-design MVP omissions — but the first public deploy would be unauthenticated and unbounded, and a single client can saturate the one in-process worker.

🔧 Add a basic per-IP rate limit and a queue-depth cap *before* exposing a URL, even ahead of full auth (v1.1+).

### ⚠️ docker-compose ships an all-zeros dev `BYOK_MASTER_KEY`

Documented and dev-only, but a copy-paste-to-prod hazard.

🔧 Refuse to start if the master key is the all-zeros value when `APP_ENV != development`.

### ⚠️ Orphan `.pyc` files with no source (`tests/llm/`)

Leftovers from deleted multi-provider work; the top-level `tests/` dir is otherwise just a README.

🔧 `git rm` the orphans. Committed bytecode without source is debt and a minor supply-chain smell.

### ⚠️ Only `format="lesson"` is implemented, but v1 claims three formats

Quiz and Explanation (D13) are rejected at the boundary.

🔧 Implement them, or narrow the v1 scope statement to "Lesson only" so the spec matches the code.

### ⚠️ Unversioned `book.json` contract on two boundaries

The Book JSON is the contract backend↔compiler *and* OnDemand-export↔reader, with no schema version or validator.

🔧 Add a `schema_version` field and validate on ingest at both boundaries — a field rename otherwise breaks the bridge silently.

---

## 🔧 Testing practices — strong core, missing edges

| Practice | State | Fix |
|---|---|---|
| Security path tested first (`test_no_key_in_logs`, `test_byok_envelope`) | ✅ Excellent | — |
| Idempotency / export / structure unit+integration tests | ✅ Good | — |
| Compiler independently tested (EPUB/PDF/cover/metadata) | ✅ Good | — |
| Mobile component tests (22 files) | ✅ Good | — |
| Live-Anthropic E2E | ⚠️ Absent | Run one real BYOK generation against a deployed backend |
| On-device mobile E2E | ⚠️ Absent | Detox/Maestro for key-load → generate → poll → render |
| Direct `pipeline/` tests in this repo | ⚠️ Absent (transitive only) | Add schema/retry/prompt tests locally |

---

## Practices Scorecard (v1.0)

```
┌─────────────────────────────────────────────────────────────────────┐
│  Mentible (StudyBuddy_SelfLearner) — Practices Scorecard (v1.0)       │
├──────────────────────────────────────┬───────────┬───────────────────┤
│  Practice area                        │  Rating   │  Note              │
├──────────────────────────────────────┼───────────┼───────────────────┤
│  BYOK key lifecycle (encrypt/TTL/shred)│  ✅ Strong │  HKDF-per-job AES  │
│  Secret redaction + CI key-leak gate  │  ✅ Strong │  field + regex     │
│  Vendoring with recorded provenance   │  ✅ Strong │  VENDORED.md SHAs  │
│  Idempotency + bounded retry          │  ✅ Strong │  request_id dedup  │
│  Runtime isolation (compiler subproc) │  ✅ Strong │  key-free renderer │
│  ADR decision discipline              │  ✅ Strong │  6 ADRs, losers    │
│                                       │           │  closed            │
│  Config fail-fast / no secret defaults│  ✅ Good   │  pydantic-settings │
│  Durable job execution                │  ⚠️ Weak   │  in-proc BG task   │
│  Spec ↔ code reconciliation           │  ⚠️ Weak   │  ADRs outran specs │
│  Public-surface hardening (CORS/RL)   │  ⚠️ Weak   │  MVP-deferred      │
│  Live + on-device test coverage       │  ⚠️ Gap    │  not yet run       │
│  v1 format completeness               │  ⚠️ Gap    │  lesson-only       │
└──────────────────────────────────────┴───────────┴───────────────────┘
```

The shape is consistent and telling: **everything that protects the user's key is strong; everything that bridges "decided/planned" to "running in production" is the work that remains.** None of the weak items are architectural mistakes — they are MVP deferrals and spec-reconciliation debt, both cheap to close.

---

*Practices observed in the code on disk at `e1c66f7`. Where docstrings, `MVP_v1.md`, or `STATUS.md` disagreed with the implementation, the implementation was treated as the source of truth.*
