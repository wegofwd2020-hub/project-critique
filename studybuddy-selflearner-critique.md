# StudyBuddy SelfLearner (Mentible) — Code Review & Critique

**Reviewed:** 2026-06-02 (v1.0 — first review, measured on disk at branch `feat/authoring-regenerate-export-fixes` @ `e1c66f7`)
**Repo:** `wegofwd2020-hub/StudyBuddy_SelfLearner` · **Public brand:** **Mentible** (tagline *"Author Yourself"*; ADR-006, name pending trademark/domain clearance — formerly "StudyBuddy Q")
**Phase:** Pre-deploy MVP — feature-complete in code for its MVP slice, **not yet verified against live Anthropic or a deployed backend**
**Rating key:** ✅ Strong · ⚠️ Gap / Risk · ❌ Critical Issue

---

## Executive Summary

Mentible is the **direct-to-learner answer to a GTM problem**. After the first StudyBuddy_OnDemand demo, an advisor flagged that the *content-generation IP* was the valuable core and the *institutional (school/district) go-to-market* was the expensive part. This repo is the response: a thin, opinionated authoring client over the same scoped-query IP, sold to adults who **bring their own Anthropic key (BYOK)** — so the vendor never carries a token bill — and which **compiles generated content into a portable EPUB3/PDF book**. The framing is "Claude Code, but for learners": refuse free-form chat, refuse generic markdown, force the six scope dimensions that turn a bare prompt into a real educational artefact.

The product has moved fast and **re-scoped itself twice in five weeks** via ADRs. It is now explicitly **two products** (ADR-004): a *paid* authoring app — this repo — and a *separate, free, offline reader* app (not yet started). The brand changed from "StudyBuddy Q" to **Mentible** (ADR-006). A multi-provider + managed-key model (ADR-005) is *accepted but unbuilt*. Reading the ADRs first is mandatory — the `SCOPE.md` / `CLAUDE.md` single-app, "free download" framing predates the split.

**What actually exists on disk is real and well-architected — not a stub.** ~11k lines of source across four clean layers: a React Native/Expo mobile app (the largest area at 6.5k LOC), a FastAPI BYOK generate/structure/export backend, a standalone TypeScript **compiler** that turns a `book.json` into EPUB3 *and* PDF, and a `pipeline/` of prompt IP vendored one-way from OnDemand with recorded source SHAs. The end-to-end loops — generate a lesson, structure a TOC into a book, compile a book to EPUB3/PDF — are all implemented and unit/integration-tested (75 backend test functions + ~171 JS test blocks), behind a four-job CI that includes a **repo-wide "no real `sk-ant-` key committed" gate**.

The security posture is the standout. BYOK is handled with genuine discipline (ADR-001, Pattern B): the key rides in the HTTPS request body, is AES-256-GCM-encrypted at rest in Redis under a **per-job HKDF-derived key** with a short TTL, read once by the worker, then shredded and deleted; it never touches a log line (a structlog redaction processor + a CI grep enforce this), a database row, or an exception traceback. For a product whose entire trust proposition is "we touch your API key safely," this is the right level of paranoia.

The honest gap is **deployment and verification, not code**. Per `STATUS.md`, the backend has no public URL, the APK has never been built, and 5 of 6 MVP success criteria are "code-complete, unverified on device." The job runner is an **in-process FastAPI `BackgroundTask`**, not the Celery/Redis queue the plan and docstrings describe — so a process restart loses in-flight jobs. There is no auth, no accounts, no cloud sync (all deferred by design). And two accepted expansions — the free reader app (ADR-004) and the multi-provider/managed-key layer (ADR-005) — exist only as decisions; `tests/llm/` holds orphan `.pyc` files but no `llm/` source.

| Area | Rating | Key Finding |
|---|---|---|
| Architecture | 🟢 Strong | Four clean layers; key-free deterministic compiler as a separate runtime; one-way vendoring with recorded SHAs; security-first BYOK design captured in ADRs |
| Code Quality | 🟢 Strong | `mypy`/`ruff`-linted backend, typed TS compiler, zero committed secrets, single-source brand constant; idempotency + retry budgets thought through |
| Test Coverage | 🟡 Good | 75 backend test functions (incl. mandatory `test_no_key_in_logs`) + ~171 mobile/compiler JS test blocks + full CI; **no live-Anthropic or on-device E2E**; `tests/` dir effectively empty |
| Documentation | 🟢 Strong | 6 ADRs capturing every pivot; MVP/ARTIFACT_PIPELINE/SCOPE specs; but `SCOPE.md`/`CLAUDE.md`/`STATUS.md` are **stale vs current HEAD** and the brand/decisions drift between them |
| Security | 🟢 Strong | BYOK Pattern B done right: HKDF-per-job AES-GCM envelope, TTL + shred, structlog key-redaction, CI key-leak gate, no hardcoded keys |
| Scalability / Ops | 🟡 Good | Scale-to-zero Fly config ready; **but** in-process BackgroundTask (not durable), CORS `*`, no rate-limit / queue-depth cap / auth — all flagged as by-design MVP fragility |

**Top 5 actions:** (1) Replace the in-process `BackgroundTask` with the planned Celery/Redis worker (or document the data-loss window as accepted for MVP) before any real-device run. (2) Deploy the backend to Fly and run the BYOK loop against live Anthropic — the one verification gate everything else waits on. (3) Reconcile the stale `SCOPE.md`/`CLAUDE.md`/`STATUS.md` with the ADRs (brand = Mentible, two-product split, paid app) so the durable spec matches reality. (4) Tighten CORS off `*` and add request rate-limiting + a queue-depth cap before exposing a public URL. (5) Decide the ADR-005 sequencing — build the multi-provider/managed-key layer or mark it explicitly deferred, so it stops being an accepted-but-absent fork in the road.

---

## What This Product Is (and Isn't)

| | StudyBuddy_OnDemand | **Mentible (this repo)** |
|---|---|---|
| Audience | Schools, teachers, districts (K-12) | Self-motivated adult learners + professionals |
| GTM | B2B sales | App-store distribution |
| Compliance | FERPA + COPPA | **Adult-only — neither** |
| Multi-tenancy | Multi-tenant FastAPI + RLS | **Single-user; no RLS, no tenancy** |
| Token spend | StudyBuddy pays Anthropic | **User pays Anthropic (BYOK)** |
| Output | Rendered lessons in-app | **Compiled EPUB3 / PDF book artifact** |
| Value prop | Governance, audit, curriculum lifecycle | Quality scoping + education-grade artifact |
| Code reuse | — | **One-way vendor of `pipeline/` prompts from OnDemand; never cross-imports** |

The IP shared with OnDemand is the **six scope dimensions** (topic / level / language / prior-knowledge / format / real-world framing) — "the LLM is the commodity; the scoping layer is the product." OnDemand's `book_export.py` (#400) emits content *into* this product's reader as neutral "Book JSON." There is deliberately **no customer funnel** between the two.

---

## 1. Architecture

### Strengths

- **Four clean layers with downward-only dependencies.** `mobile/` (RN/Expo) → backend REST; `backend/src/{generate,structure,export}` → `core/` + `pipeline/`; `pipeline/` → Anthropic SDK only (kept import-portable so it can be re-vendored). The CLAUDE.md layer rules are actually respected in the tree.
- **The compiler is a separate, key-free, deterministic runtime.** `compiler/` is a TypeScript Node CLI (`dist/cli.js`) the backend invokes as a subprocess: `book.json` in on stdin, artifact bytes out on stdout. It never sees the Anthropic key and has no network dependency, so the security-sensitive surface (the key) and the heavy-rendering surface (EPUB/PDF/Chromium-Mermaid) are physically isolated processes. Good blast-radius thinking.
- **EPUB3 generation is genuinely complete, not a toy.** `epub.ts` walks `book.toc.subjects[].units[]` in reading order, emits one XHTML chapter per content-bearing topic, and builds a proper OCF container: `mimetype` (STORE), `META-INF/container.xml`, OPF 3.0 with full Dublin Core metadata (`dc:identifier/title/language/creator` + MARC relator role, publisher/date/description/subject/rights, `belongs-to-collection` series, `dcterms:modified`), **both** an EPUB3 `nav.xhtml` and a legacy EPUB2 `toc.ncx`, chapter items flagged `properties="mathml svg"` when present, a generated SVG cover, a colophon, an embedded Source Serif 4 font, and base64 images extracted into de-duplicated manifest resources. The PDF path (Vivliostyle, CSS Paged Media) lays out a real textbook: title → colophon → page-numbered TOC → chapters → Quizzes → Answers.
- **One-way vendoring discipline with recorded provenance.** `pipeline/VENDORED.md` records the source repo and per-file SHAs (last sync `0e7ebc06`, 2026-04-25). `providers/anthropic.py` and `toc_structurer.py` are *deliberately modified* copies (per-call BYOK key; network wrapper dropped so an error path can't stringify the key) — the modifications are documented, not silent. Nothing imports across the repo boundary.
- **Security-first design captured as decisions, not folklore.** ADR-001 specifies the full BYOK contract before any key-handling code; ADR-002 specifies the vendoring contract before any copy. The architecture was argued on paper first.

### Gaps & Risks

⚠️ **The job runner is not what the architecture says it is.** `MVP_v1.md` and several docstrings describe a "Celery worker"; the implementation is an in-process FastAPI `BackgroundTask` (`tasks.py` is honest about this: "Migration to Celery for v1.1 is straightforward… a process restart loses in-flight jobs"). For a *minutes-long* async generation (D12), an unlucky deploy or crash silently drops a user's in-flight job and leaves an encrypted envelope in Redis until TTL. Fine as a stated MVP shortcut; dangerous if it ships unannounced.

⚠️ **Single-consumer compiler contract, like OnDemand's engine.** The `book.json` schema is the contract between backend and compiler, and between this product and OnDemand's `book_export.py`. There is no schema version field or validator on the boundary — a field rename on either side breaks the bridge silently. Pin and version the Book JSON schema.

⚠️ **The two accepted expansions are absent from the tree.** ADR-004's free reader app (separate repo) and ADR-005's multi-provider/managed-key `llm/` layer are *accepted decisions with no code*. `tests/llm/` contains only orphan `.pyc` files. This is fine as roadmap, but the gap between "accepted" and "exists" is exactly where architecture drifts.

⚠️ **Stale specs outrank current reality.** `STATUS.md` is dated to branch `feat/mobile-skeleton` (2026-05-26) and predates ~40 commits of compiler/EPUB/cover/metadata work; `SCOPE.md`/`CLAUDE.md` still describe a single free app. A new contributor reading top-down would build the wrong mental model before reaching the ADRs.

---

## 2. Code Quality

### Strengths

- **No committed secrets, enforced.** `grep -rn "sk-ant-[A-Za-z0-9]"` across `.py/.ts/.tsx` (excluding tests) returns zero, and a dedicated CI job re-checks the whole repo every push.
- **Backend is linted and typed.** `ruff check` + `ruff format` gate in CI; `pydantic-settings` config with no secret defaults (startup fails if `BYOK_MASTER_KEY` is unset). The compiler is TypeScript with a `tsc` typecheck job.
- **Defensive generation logic.** `/generate` dedups on `request_id` (idempotency key `req:{id}`), the worker retries invalid-JSON/schema failures up to 6× (raised from 3 — commit `d8316df`) before failing the job, and every Claude response is `model_validate`-d against `LessonOutput` before returning.
- **Single source of brand truth.** `mobile/src/constants/brand.ts` holds `BRAND_NAME`/`BRAND_TAGLINE`; the rebrand to Mentible flows from one constant rather than scattered string literals. (The `app.json` `slug`/`package` deliberately stay `studybuddy-q` until trademark clearance — a documented, intentional inconsistency.)
- **The Anthropic caller refuses to leak.** It logs only `type(exc).__name__` (never the message or `exc_info`, which can carry the key in an SDK repr) and re-raises `AnthropicCallError` `from None`.

### Gaps & Risks

⚠️ **`tests/` is a misleading empty shell.** The top-level `tests/` dir holds only a README (real tests live in `backend/tests`, `compiler/__tests__`, `mobile/__tests__`); `tests/llm/` holds stale `.pyc` files from deleted multi-provider work. Delete the orphans — committed `.pyc` with no source is debt and a small supply-chain smell.

⚠️ **CPython `del api_key` cannot zero memory.** The code comments acknowledge this; string immutability means the plaintext key can persist in the process heap until GC. Not fixable in pure Python, but worth a one-line note in ADR-001's threat model that the "shred" is best-effort for the in-process copy (the Redis copy *is* genuinely deleted).

⚠️ **Only `format="lesson"` is wired.** Quiz and Explanation (D13 v1 formats) are rejected at the `/generate` boundary despite being in-scope for v1. Either implement them or down-scope the v1 format claim so the spec matches the code.

---

## 3. Test Coverage

### Strengths

- **The security-critical path is tested first.** `backend/tests/test_no_key_in_logs.py` asserts no log line in any code path contains the test key — and CI enforces it. `test_byok_envelope.py` covers the AES-GCM/HKDF envelope, `test_idempotency.py` the dedup, `test_generate_e2e.py` the (mocked) generate loop, `test_export.py` the compile path, `test_structure.py` the TOC structuring. 75 `def test_` functions across 11 files.
- **The compiler is independently tested.** `compiler/__tests__` — 9 files / ~60 `it/test` blocks covering EPUB assembly, PDF render, cover, colophon, metadata, image packaging.
- **Mobile has the most tests by count.** `mobile/__tests__` — 22 files / ~111 `it/test` blocks (Jest + RNTL).
- **Four-job CI.** `.github/workflows/ci.yml`: backend-lint (ruff), backend-test (pytest with a test `BYOK_MASTER_KEY`), compiler-test (tsc + jest), and the `no-real-key-in-repo` defence job. Triggers on PR, push to main, and manual.
- **No external calls in CI, by rule.** Anthropic/Redis are mocked (`fakeredis`-style + mocked SDK); the discipline matches OnDemand's.

### Gaps & Risks

⚠️ **The headline loop has never run for real.** No test (and per `STATUS.md`, no manual run) exercises a live Anthropic call or a deployed backend. 5 of 6 MVP success criteria are "code-complete, unverified on device." The single most valuable test right now is one real end-to-end BYOK generation against a deployed Fly instance.

⚠️ **No mobile on-device E2E.** The BYOK loop's UX — `expo-secure-store` async key load, WebView KaTeX/Mermaid render, minutes-long poll — is only unit-tested. Detox/Maestro on a real device (or at least an emulator) is the gap before alpha.

⚠️ **Pipeline has no dedicated tests.** `pipeline/` is exercised only transitively via backend tests; the vendored prompt/validator logic has no direct coverage in this repo (it inherits OnDemand's, but those don't run here).

⚠️ **JS counts are `it/test(` blocks, not asserted-unique cases.** Treat the ~171 mobile+compiler figure as an upper-bound approximation; backend's 75 is an exact `def test_` count.

---

## 4. Documentation

### Strengths

- **Six ADRs capture every pivot.** ADR-001 (BYOK Pattern B), ADR-002 (vendoring, Approach C), ADR-003 (book authoring — *Proposed*), ADR-004 (two-product split + EPUB3 artifact — *Proposed*), ADR-005 (multi-provider + hybrid keys — *Accepted 2026-05-29, unbuilt*), ADR-006 (rebrand to Mentible — *Accepted 2026-05-29*). The product's reasoning is fully legible.
- **Companion specs are thorough.** `MVP_v1.md` (the BYOK single-lesson loop + 6 success criteria + named "intentionally fragile" gaps), `ARTIFACT_PIPELINE.md` (book.json → EPUB3/PDF/MOBI matrix, matches the compiler closely), plus `PARAMETERS.md`, `COMPILE_PIPELINE_PLAN.md`, `CONTENT_MIGRATION_CONTEXT_ENGINEERING.md`, `DEPLOY_FLY.md`, and branding/competitive analyses.
- **`VENDORED.md` is real provenance.** Per-file source SHAs + which files are verbatim vs modified vs explicitly-not-vendored.

### Gaps & Risks

⚠️ **The top-of-funnel docs are stale and contradict the ADRs.** `SCOPE.md` (single free app, BYOK only), `CLAUDE.md` ("Pre-MVP — directory stubs only, no application code yet"), and `STATUS.md` (branch `feat/mobile-skeleton`) all predate the current state. The CLAUDE.md *header note* points to the ADRs, but the body still misleads. **Promote the ADR outcomes into `CLAUDE.md`/`SCOPE.md`** so the durable spec is self-consistent — the doc-drift this product warns about in OnDemand is now present here.

⚠️ **`MVP_v1.md` plan says Celery; code is BackgroundTask.** A reader trusting the plan will look for a worker that isn't there.

⚠️ **No `CONTRIBUTING.md` / runbook.** Local dev is inferable from `docker-compose.yml` + `dev_start.sh`, but there's no single onboarding doc, and no deploy runbook beyond `DEPLOY_FLY.md`.

---

## 5. Security — the headline area

### Strengths

- **BYOK Pattern B is implemented as specified (ADR-001).** The user's Anthropic key travels in the HTTPS request *body* (validated `min_length=20, max_length=512`, must start `sk-ant-`) — never in a URL, query string, or an `Authorization` header the backend owns.
- **Encrypted at rest with a per-job key.** `byok_envelope.py` AES-256-GCM-encrypts the key into `byok:{job_id}` using a key derived via **HKDF-SHA256(master, salt=job_id)**; the master `BYOK_MASTER_KEY` is a 64-hex env var with no default (startup fails if absent), giving the master key a separate blast radius from the Redis ciphertext. TTL defaults to 120 s; the worker re-derives the key (HKDF is deterministic) so plaintext is never shared back through Redis.
- **Explicit shred on every path.** The worker `finally`-block does `del api_key` and `DEL byok:{id}` on success and failure alike. Status rows outlive the envelope (×10) so polling still works after the key is gone.
- **Key never reaches logs.** `core/log_redaction.py` is a structlog processor that redacts by field name (`api_key`, `authorization`, `token`, …) *and* by value regex (`sk-ant-[A-Za-z0-9_\-]{8,}` → `<redacted-anthropic-key>`). The Anthropic caller logs only the exception *type*. `test_no_key_in_logs.py` + the CI key-leak job enforce both.
- **Mobile stores the key in hardware-backed secure storage.** `expo-secure-store` (`WHEN_UNLOCKED_THIS_DEVICE_ONLY`) on native, with a `localStorage` fallback only on web; `maskApiKey` shows last-4 in Settings.

### Gaps & Risks

⚠️ **CORS is `allow_origins=["*"]`.** Acceptable for a single-user MVP with no cookies/session, but must be locked to the app's origins before a public URL exists — especially since the request body carries the user's key.

⚠️ **No rate limiting, no queue-depth cap, no auth.** All by-design MVP omissions (single-user, no accounts until v1.1+), but together they mean the first public deployment is unauthenticated and unbounded. A single misbehaving client can exhaust the in-process worker.

⚠️ **docker-compose ships an all-zeros dev master key.** Documented, dev-only — but a copy-paste-to-prod hazard. Consider refusing to start if `BYOK_MASTER_KEY` is the all-zeros value outside `APP_ENV=development`.

⚠️ **The in-process worker holds the encrypted envelope through a restart window.** Until TTL expires, a crashed/restarted process leaves the (still-encrypted) key in Redis with no worker to consume or shred it. The encryption makes this low-severity, but the durable-queue migration closes it cleanly.

---

## 6. Scalability / Operability

### Strengths

- **Scale-to-zero Fly config is deploy-ready.** `fly.toml` (app `studybuddyq-backend`, region `iad`, `shared-cpu-1x`/512 MB, `min_machines_running = 0`, `/healthz` check) + `REDIS_URL`/`BYOK_MASTER_KEY` via `fly secrets`. Matches the "demo/quality-first, not scale-first" stance (D7).
- **`/readyz` actually checks dependencies** (pings Redis), distinct from a liveness `/healthz`.
- **The expensive work is isolated.** EPUB/PDF/Chromium-Mermaid rendering happens in the subprocess compiler, not the request path; the backend stays light.

### Gaps & Risks

⚠️ **In-process BackgroundTask is the scaling ceiling.** One process = one worker pool; minutes-long jobs block capacity and don't survive restarts. The Celery/Redis migration is the prerequisite for any concurrency story.

⚠️ **No load/perf testing and no real latency data.** D12 promises "minutes" but nothing has timed a real generation+compile. The compile step (headless Chromium for Mermaid, Vivliostyle for PDF) is the likely tail-latency risk and is untested under load.

⚠️ **Not yet deployed.** No public URL, APK never built (per `STATUS.md`). Everything operational is theoretical until the first Fly deploy + device run.

---

## Priority Actions (Ordered)

| Priority | Action | Area |
|---|---|---|
| P1 | Deploy backend to Fly + run one real BYOK generation against live Anthropic — clears the single gate everything else waits on | Verification |
| P1 | Replace in-process `BackgroundTask` with the planned Celery/Redis worker, or explicitly document the restart-data-loss window as accepted for MVP | Architecture |
| P1 | Lock CORS to the app origins (off `*`) and add request rate-limiting + a queue-depth cap before exposing a public URL | Security |
| P1 | Refuse startup if `BYOK_MASTER_KEY` is the all-zeros dev value when `APP_ENV != development` | Security |
| P2 | Reconcile `SCOPE.md`/`CLAUDE.md`/`STATUS.md` with ADR-004/005/006 (brand = Mentible, two products, paid app) — kill the doc drift | Documentation |
| P2 | Pin + version the `book.json` schema and validate it on both the backend↔compiler and OnDemand↔reader boundaries | Architecture |
| P2 | Add on-device (Detox/Maestro or emulator) E2E for the BYOK loop: key load → generate → poll → render | Testing |
| P2 | Implement the remaining v1 formats (Quiz, Explanation) or down-scope the v1 format claim to "Lesson only" | Code Quality |
| P2 | Decide ADR-005 sequencing — build the multi-provider/managed-key `llm/` layer or mark it explicitly deferred | Architecture |
| P3 | Delete the orphan `tests/llm/*.pyc` files | Code Quality |
| P3 | Add `CONTRIBUTING.md` + a deploy runbook beyond `DEPLOY_FLY.md` | Documentation |
| P3 | Note in ADR-001's threat model that the in-process `del api_key` shred is best-effort (CPython string immutability) | Security |
| P3 | Add direct `pipeline/` tests in this repo rather than relying only on transitive backend coverage | Testing |

---

*This critique is a point-in-time review measured against the code on disk at `e1c66f7` (branch `feat/authoring-regenerate-export-fixes`). Deployment status, live-Anthropic behaviour, and on-device UX are **self-reported in `STATUS.md`** and were not verifiable from source. The brand "Mentible" is adopted per ADR-006 but pending trademark/domain clearance; the repo and some identifiers remain `StudyBuddy_SelfLearner` / `studybuddy-q` intentionally.*
