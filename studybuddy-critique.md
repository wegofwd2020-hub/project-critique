# StudyBuddy OnDemand — Code Review & Critique

**Reviewed:** 2026-05-24 (v1.5 — refresh: numbers re-measured; `teacher_capabilities` #358; corporate-L&D epics 17/18 surfaced) · May 2026 (v1.4 — visual-library wave 1+2, four bug close-outs, PAI removal)
**Prior reviews:** v1.3 April 2026 (Epic 10 / Epic 11 / Streams) · v1.2 March 2026 · v1.1 Feb 2026
**Repos:** `wegofwd2020-hub/StudyBuddy_OnDemand` · `wegofwd2020-hub/studybuddy-docs`
**Phase:** Late-build / pre-production
**Rating key:** ✅ Strong · ⚠️ Gap / Risk · ❌ Critical Issue

---

## Executive Summary

> **Note (2026-05-24):** the summary below is the v1.4 record (May 2026), preserved verbatim. The architectural read still holds. Numbers it cites in current tense (~914 backend tests, 16 Playwright specs / 2,620 LOC, 835 across 59 files) have moved — current is **1,030 tests across 73 files**, **17 specs / 2,781 LOC**, **59 migrations (latest 0059)**. New since v1.4: the `teacher_capabilities` capability (#358, migration 0059) and two speculative corporate-L&D epics (17/18; Epic 17 marked CONTESTED). See **What Changed Since v1.4 (2026-05-24 refresh)** immediately after this summary for the full delta.

The v1.4 cycle is dominated by **execution-throughput evidence rather than new architecture**. Between 2026-04-26 and 2026-05-08 the project closed 10 visual-library expansion sub-issues (#327–#336 under Epic #326) plus four standalone bugs (#295, #297, #338, #339), shipping 144 SVG library entries with non-NULL embeddings, 80 resolver-eval records, and 9 Remotion Option-3 video clips — at roughly 14h 56m wall time against an estimated ~19 FTE-days, an order-of-magnitude compression. The compression source is **process maturity, not primitive reuse**: the helpers-toolkit + declarative SidecarSpec pattern from #327 lifted into every downstream class, the Phase 1/2/3 wave cadence (catalogue → Remotion → eval/seeder/MEMO) became routine, and side-issues were filed and closed inside the same wave rather than queued.

The platform-architecture posture from v1.3 holds. Epic 10 governance, Epic 11 formatting, and the streams registry are stable. New backend additions are scoped: `get_current_student_optional` (FastAPI dependency for opt-in personalisation) and a 3-step stream-aware curriculum resolver in `/curriculum/{grade}` (closing #297). Two operational gotchas were retired — the `seed_library_local.py` docker-cp dance (fixed by `./scripts:/app/scripts-repo:ro` + `./sample_content:/app/sample_content:ro` bind mounts in #339) and the resolver-eval KeyError on Voyage rate-limit (fixed in #338 by mirroring the success-path schema in the error branch). The PAI 5.0 integration was removed in full from `~/.claude/` after a hook-error investigation showed it was unrecoverable; settings.json shrank from 52 KB to 1.9 KB.

Backend tests now sit at ~914 functions across 59+ files (including the +27 from Epic 15 backup/restore). All prior P0/P1 items remain remediated. New residual risk is small: the visual-library promotion CI still depends on AWS secrets the dev box doesn't have, so library content is seeded locally via `seed_library_local.py` rather than the production path — fine for resolver evaluation, but a divergence to retire before launch. The remaining v1.3 risks (`APP_ENV` enum assertion, slowapi/Redis limiter coexistence, pool arithmetic warn-not-assert, load tests absent, E2E weighted to a11y) carry over unchanged.

L-6 (retention sweeper), Epic 10 L-7..L-10, Epic 11 C-5..C-8, and Epic 15 BR-DOC-1/2 remain the open backlog.

## Executive Summary (v1.3 — preserved)

The platform continues to mature along the trajectory set by v1.2. All prior P0/P1 items remain remediated. The v1.3 cycle added three material capability layers: Epic 10 delivers a curriculum-lifecycle governance layer with platform-write guards, archive/unarchive flows, and a retention status column on curricula; Epic 11 unifies content presentation — universal + per-subject prompt guidelines, a shared `SBMarkdown` component with KaTeX, and a format-drift validator in the pipeline; and the new Streams registry (S-2/S-3) introduces a soft-registry model (`science`, `commerce`, `humanities`, `english`, `stem`) with upsert-on-upload and a merge endpoint.

The Playwright suite has grown from 3 student-path specs to 16 spec files totalling 2,620 LOC across persona-accessibility, auth, admin, and public flows (35/35 persona + 86/86 chromium-project specs passing). The backend test count has grown to 835 test functions across 59 files; per-module coverage thresholds (auth/subscription 90%, content 85%, default 80%) are still enforced by `scripts/check_coverage_thresholds.py`.

The remaining risks are second-tier: `APP_ENV` is still not asserted against a valid enum at startup; the Redis-backed auth rate-limiter and the slowapi in-process limiter still coexist; pool arithmetic is logged but not a hard assertion; load/performance tests are still absent; and the E2E suite, while much broader, remains weighted toward accessibility coverage rather than functional teacher/admin flows. L-6 (retention sweeper) was paused deliberately; a handful of Epic 10 tickets (L-7..L-10) and Epic 11 tickets (C-5 regen in flight, C-7 PDF smoke, C-8 mobile parity) remain open.

---

## What Changed Since v1.4 (2026-05-24 refresh)

No architectural change — the v1.4 posture holds in full. The window since the v1.4 cut (46 commits; HEAD `d5c75ad` on branch `fix/frontend-unit-tests-363`, dated 2026-05-22) is **launch/demo hardening plus one new capability**, not new platform architecture. Re-measured current numbers:

| Metric | v1.4 stated | Now (2026-05-24) |
|---|---|---|
| Backend test functions | ~914 across 59+ files | **1,030 across 73 files** |
| Alembic migrations | 48 (latest 0048) | **59 (latest 0059)** |
| Playwright specs | 16 files / 2,620 LOC | **17 files / 2,781 LOC** |
| TODO/FIXME/XXX in `backend/src` + `pipeline` | zero | **zero (holds)** |
| Visual library entries / resolver eval records | 144 / 80 | 144 / 80 (unchanged) |

**New migrations above 0048:** 0049 (fix `class_summary` unique index), 0050–0051 (Epic 12 adopted-curricula + content overrides), 0052 (Epic 13 `school_theme`), 0053–0055 (Epic 15 backup/restore), 0056–0057 (visual library `visual_library_entries` + pgvector embedding), 0058 (`name` on demo leads), **0059 (`teacher_capabilities`, RLS — issue #358)**.

**New capability — `teacher_capabilities` (#358 / PR #359).** Additive RBAC table (migration 0059, RLS) with a two-gate read/act model granting `curriculum.commission` / `curriculum.review` / `curriculum_mgmt`. The same PR fixed school uploads to write `owner_type='school'` (was defaulting to platform). Covered by `test_curriculum_mgmt_capability.py`.

**Launch/demo hardening (bulk of the window).** `vm-localhost-bootstrap.sh` + JSON deploy log; demo unit pre-import (`preimport_demo_units.py` — G11 Science pre-imported as approved+published and auto-adopted into the sandbox school); nginx upstream/DNS fixes; demo JWT TTL extended to 4h. **Domain rename `studybuddy.app` → `usestudybuddy.com`** swept across the codebase (`b544029`). asyncpg jsonb codec fix (`7dec328`) — dropped manual `json.dumps()` and registered json/jsonb codecs so `json_agg` decodes to lists.

**New product direction not seen in v1.4 — corporate L&D.** Two new epic specs appeared: `EPIC_17_corporate_ld_fork.md` (status **CONTESTED** — an advisor recommended against forking the codebase) and `EPIC_18_corporate_scenario_catalog.md` (corporate-compliance scenario catalogue, two scenarios shipped). These signal a possible extension toward corporate training that the K-12 critique does not evaluate — worth a dedicated scoping review before it accretes architecture.

**Backlog correction.** Per the current `CLAUDE.md`, Epic 10 **L-7 and L-8 are shipped** (the v1.4 summary listed L-7..L-10 as open); remaining open are L-6 (sweeper, paused), L-9, L-10. Epic 11 C-5..C-8 and Epic 15 BR-DOC-1/2 are unchanged-open.

**Unchanged residual risks (no commits touched them).** `APP_ENV` enum assertion, slowapi/Redis limiter coexistence, pool-arithmetic warn-not-assert, absent load/perf tests, a11y-weighted E2E (the 6 `fixme`'d `school-admin-curriculum-flow.spec.ts` scenarios, #188). Visual-library promotion CI still gated on AWS secrets; local-seed divergence still to retire before launch.

---

## What Changed Since v1.3

| Item | v1.3 | Now |
|---|---|---|
| Visual library entries (dev DB) | 0 seeded — promotion CI gated on AWS secrets unavailable on dev box | 144 entries with non-NULL Voyage embeddings via `seed_library_local.py` |
| Resolver eval records | Empty harness | 80 records (eval-001..080) covering oscillations, kinematics, atoms, cells, circuits, periodic-table, organic chem, derivatives, waves, optics |
| Remotion Option-3 clips | 0 | 9 (`oscillations`, `g9-kinematics-1d`, `chemistry-atom`, `biology-cells`, `electronics-circuit`, `periodic-table`, `organic-chem`, `derivatives`, `g8-waves`, `optics`) |
| Visual-library generators | 1 (`generate_oscillations_visuals.ts`) | 10 — every issue's catalogue script now follows the same shared-helpers pattern (svgWrap, write, makePlot, plotPolyline) |
| `seed_library_sidecars.ts` | ~50 entries | 144 declarative SidecarSpec entries (canonical source) |
| `/curriculum/{grade}` endpoint | STEM-only fallback for stream students | Stream-aware: 3-step resolver (school-owned → classroom packages RLS bypass → STEM fallback); auth-optional via `get_current_student_optional` (#297) |
| Optional auth dependency | Absent | `get_current_student_optional` in `backend/src/auth/dependencies.py` — `HTTPBearer(auto_error=False)`; missing-header → None, malformed/expired → still raises |
| Resolver eval crash mode | KeyError on Voyage rate-limit branch (#338) | Error branch mirrors success-path schema; `n_errored` reported in summary |
| Library-seeder operator step | `docker cp scripts/* celery-pipeline:/tmp/seed/ && docker compose exec ...` (manual dance) | `docker compose exec -T celery-pipeline python3 /app/scripts-repo/seed_library_local.py` — bind mounts permanent (#339) |
| celery-pipeline mounts | `./backend:/app` only | Adds `./scripts:/app/scripts-repo:ro` + `./sample_content:/app/sample_content:ro` |
| Backend tests | ≥835 | ~914 (incl. Epic 15 +27, #297 +2) |
| PAI 5.0 integration | Active in `~/.claude/{PAI,hooks,agents,skills,MEMORY,...}/` | Removed in full; settings.json 52,688 → 1,908 bytes; snapshot at `~/.claude.pre-pai-removal-20260508T123957Z` (665 MB / 224 MB tar.gz) |
| GitHub issues closed in window | n/a | 13 — #295, #297, #327, #328, #329, #330, #331, #332, #333, #334, #335, #336, #338, #339 |

**Wave compression observation.** The estimated wall time for 10 issues × ~2 FTE-days each = ~19 days; actual = ~14h 56m. The dominant compression mechanism is *not* code reuse (the SVGs and Remotion scenes are class-specific); it is **process maturity** — the same Phase 1/2/3 cadence, the same helpers-toolkit, the same SidecarSpec format, the same eval JSONL append, the same MEMO.md template. First-of-class shipping (#327) consumed ~3h; same-class downstream (#328 kinematics) landed in ~45 min. Section 2.1 in `studybuddy-development-pattern.md` v1.3 documents the cadence.

## What Changed Since v1.2

| Item | v1.2 | Now |
|---|---|---|
| Curriculum governance | Implicit | Platform-write guard via RESTRICTIVE RLS (0046); archive/unarchive endpoints; `is_curriculum_in_use` gate; audit events |
| Retention lifecycle | Not modelled | `retention_status='archived'` CHECK + partial index (0047); L-3..L-5 shipped |
| Content formatting | Ad-hoc `<ReactMarkdown>` in four places | Shared `SBMarkdown` component with `remark-gfm`, `remark-math`, `rehype-katex` (119 LOC) |
| Content prompts | Single universal template | Universal + per-subject guidelines in `pipeline/prompts.py` (465 LOC); attributed-quote rule |
| Streams | Absent | `streams` registry (0045) with 5 system seeds; CRUD + merge; mandatory dropdown on upload |
| Format-drift detection | Absent | `pipeline/content_format_validator.py` flags section/output mismatches |
| Pipeline `max_tokens` | 8192 | 16384 — prevents mid-JSON truncation with richer prompts |
| Playwright specs | 3 student paths | 16 spec files, 2,620 LOC (35/35 persona + 86/86 chromium-project) |
| E2E runbook | Absent | `web/tests/e2e/README.md` — host-Chromium Playwright procedure |
| Backend tests | ≥215 passing | 835 test functions across 59 files |
| Commerce demo data | Absent | MilfordWaterford demo seeded with Commerce test accounts |
| CLAUDE.md | Dated v1.2 | Refreshed 2026-04-15: Epic 8 H-10, Epic 10 L-1..L-5, Epic 11 C-1..C-9 |
| DEV_ACCOUNTS | Flagged as ❌ in v1.2 | Handled — git tag `dev-accounts-repair-2026-04-14` exists; verify file location |

---

## 1. Architecture

### Strengths

- **Three-runtime-context separation remains intact.** Pipeline / Backend / Client boundaries are enforced by convention and documented. No client holds an Anthropic key. The backend never calls Anthropic on the request path.
- **`StorageBackend` abstraction is production-ready.** `LocalStorage` (dev, all I/O via `asyncio.to_thread`) and `S3Storage` (prod, boto3 via thread executor, pre-signed audio URLs). Chosen at startup by `STORAGE_BACKEND` env var. 283 LOC in `backend/src/core/storage.py`.
- **Application factory pattern holds.** `src/core/app_factory.py` owns lifespan, middleware, exception handlers, and router registration. `main.py` remains a 5-line entrypoint.
- **Role-based client segmentation is deliberate.** Kivy mobile for students (content, quizzes, offline), Next.js web for teachers/admins/school management. Not a feature-parity gap — an intentional scope separation. Path B (Expo/React Native) is chosen for future native apps behind Epic 3.
- **Epic 10 governance layer is well-shaped.** Platform owns the canonical default library (`owner_type='platform'`), schools own their custom curricula. RLS on `curricula` rejects mutations on platform rows for non-super-admin sessions; SELECT remains permissive so schools can still read the library. The archive flow gates on active enrolment count via `grade_curriculum_assignments`.
- **Streams are a clean soft-registry.** No FK from `curricula` — allows rename/merge as data actions. The merge endpoint moves all curricula then archives the source. Reserved codes (`none`, `other`, `all`, `default`, `null`) prevent semantic collisions.

### Gaps & Risks

⚠️ **The mobile/web capability boundary is still undocumented.** As Epic 3 (Path B) activates, decisions about which client owns which feature will accumulate ad hoc. A written boundary document is due before native-app work begins.

⚠️ **No API versioning or deprecation policy.** Still absent. With a mobile client that users may not update promptly, the first `/api/v2` change without a policy will cause incidents.

⚠️ **Kivy packaging risk is still a long-term issue.** Not a pre-launch blocker for the web persona surfaces, but should be re-assessed before Epic 3 Path B work starts or the Kivy mobile path is re-activated.

⚠️ **L-6 TTL sweeper paused.** The partial index and retention status exist, but the background job that enforces TTL is deliberately deferred. Until it ships, `archived` curricula accumulate forever — not a correctness issue, but a storage cost tail.

---

## 2. Code Quality

### Strengths

- **Structured logging everywhere.** `get_logger()` consistently used; correlation IDs attached per request via `CorrelationIdMiddleware`.
- **Sentry PII scrubbing.** `_before_send` strips `data`, `email`, `password`, `token`, `refresh_token`, `id_token` before sending to Sentry.
- **bcrypt in executor.** `hash_password()` and `verify_password()` run via `loop.run_in_executor()`.
- **JWKS TTL is enforced.** `cachetools.TTLCache(maxsize=10, ttl=JWKS_CACHE_TTL_HOURS * 3600)`. Key rotation re-fetches once on not-found before failing.
- **JWT validation is thorough.** Separate student/teacher audience validation, `jti` claim on every token, minimum 32-character secrets enforced at startup, `secrets_must_differ` validator.
- **Stripe calls are non-blocking.** `run_stripe(fn, *args, **kwargs)` dispatches any SDK callable to the thread-pool executor; used consistently throughout `subscription/router.py`.
- **`upsert_student` correctly handles `account_status` on conflict.** CASE logic: `suspended` preserved; `pending` → `active` on re-register when incoming does not require consent.
- **Zero `TODO`/`FIXME`/`XXX` in `backend/`, `pipeline/`, `web/`, `mobile/`.** Recent lint sweeps kept debt out of source.
- **Epic 11 pipeline separation is clean.** Universal formatting rules, per-subject overrides, and a format-drift validator all live in `pipeline/`, not in the backend serving path. Content quality does not leak into the hot read path.
- **Streams router quality is solid.** `backend/src/admin/streams_router.py` (536 LOC) validates codes against `_CODE_PATTERN`, gates on reserved codes, and recomputes curriculum-count on merge/archive. Permission-scoped behind `content:publish`.

### Gaps & Risks

⚠️ **Docstring style inconsistency persists.** NumPy-, Google-, and prose-style docstrings still coexist across modules. This was flagged in v1.2 and has not been consolidated.

⚠️ **No automated API changelog.** The OpenAPI → TypeScript drift check catches contract drift, but there is no semver enforcement or automated check that `/api/v1` routes are not silently removed.

---

## 3. Test Coverage

### Strengths

- **Real Postgres in CI.** Alembic migrations applied to `studybuddy_test` before every run. Schema drift caught early.
- **`fakeredis` for Redis.** No live Redis required.
- **Token factory pattern.** `tests/helpers/token_factory.py` provides deterministic JWTs; Auth0 mock not scattered.
- **Per-module coverage thresholds enforced.** `scripts/check_coverage_thresholds.py` — longest-prefix-wins: `src/auth/` = 90%, `src/subscription/` = 90%, `src/school/subscription` = 90%, `src/content/` = 85%, default = 80%. Runs in CI after pytest.
- **Backend test suite has grown.** 835 test functions across 59 files (up from 215 in v1.2). Test files span auth, content, subscription, progress, school, enrolment, notifications, pipeline, curriculum, feedback, reports, RLS, streams, and Epic 10/11 governance paths.
- **RLS isolation verified.** `test_rls.py` uses deterministic school UUIDs; the `SET LOCAL ROLE` strategy covers cross-tenant visibility.
- **Playwright persona coverage is broad.** 16 spec files totalling 2,620 LOC — student-accessibility (276 LOC), teacher-accessibility (319), admin-accessibility (232), school-admin-curriculum-flow (327), plus auth, landing, pricing, admin-portal, and student critical path. Status: 35/35 persona specs + 86/86 chromium-project specs passing.
- **E2E runbook.** `web/tests/e2e/README.md` documents the host-Chromium Playwright setup (not containerised — Chromium is glibc-linked).
- **Mobile logic tests exist.** `test_event_queue`, `test_local_cache`, `test_sync_manager`, `test_i18n` cover offline-sync logic.
- **SBOM generated per CI run.** Syft produces SPDX + CycloneDX artifacts retained 90 days.

### Gaps & Risks

⚠️ **Playwright coverage, while broad, is weighted toward accessibility.** The persona specs predominantly assert axe-rule compliance and structural presence. Functional teacher flows (roster management, reports, alerts) and school admin flows (subscription, billing, content review) have specs only at the accessibility layer. `school-admin-curriculum-flow.spec.ts` has 6 `fixme`'d scenarios (issue #188) covering the actual submission journey.

⚠️ **Accessibility debt: 3 axe rules disabled** (`color-contrast`, `html-has-lang`, `document-title`), tracked in issue #189. These are not minor — they are the rules with the highest compliance weight for school-district procurement.

⚠️ **No load or performance tests.** `SCALABILITY.md` projects specific request volumes, but there are no k6, Locust, or wrk scripts. DB pool sizing, Redis TTL assumptions, S3 throughput, and the `--stream` pipeline path's memory profile are theoretical.

⚠️ **Mobile UI screens are not tested.** Logic coverage is strong; Kivy UI regressions in `CurriculumMapScreen`, `SubjectScreen`, `QuizScreen` go undetected.

⚠️ **Pipeline tests likely mock the Anthropic API.** Without a recorded-response fixture, `test_pipeline.py` covers prompt construction and schema validation but not the actual generation + storage path for formatted content.

⚠️ **No cross-client auth continuity tests.** A student using both mobile and web must share JWT refresh behaviour, subscription entitlements, and progress state. Still no dedicated coverage.

---

## 4. Documentation

### Strengths

- **Separate docs repo is complete.** `studybuddy-docs` contains `ARCHITECTURE.md`, `BACKEND_ARCHITECTURE.md`, `REQUIREMENTS.md`, `SCALABILITY.md`, `TESTING_SETUP.md`, `OPERATIONS.md`, `PRODUCTION_DEPLOYMENT.md`, `COST_PLAN.md`, `MARKETING_PLAN.md`, `GLOSSARY.md`, `AGENTS.md`, `UX_GOALS.md`, `CHANGES.md`, and others covering the full product surface.
- **`CLAUDE.md` is current.** Refreshed 2026-04-15 (commit 4ed8a35): Epic 8 H-10, Epic 10 L-1..L-5, Epic 11 C-1..C-9 all covered. 745 LOC.
- **Epic INDEX is the operational source of truth.** `docs/epics/INDEX.md` tracks all 11 epics with status, updated in lock-step with implementation.
- **Module-level docstrings on routers/services** list endpoints, security model, and key functions.
- **`CHANGES.md` is maintained.** ADR-001 (school-as-primary), retention, streams entries each document the change at file-level fidelity.
- **`StudyBuddy_VC_Deck_Final.md` in docs repo.** Business context alongside technical docs.

### Gaps & Risks

⚠️ **No `CONTRIBUTING.md`.** Local setup, test invocation, branch conventions, PR checklist — absent from the code repo. `AGENTS.md` in the docs repo covers AI agents, not human contributors.

⚠️ **DEV_ACCOUNTS.md location verify.** Git tag `dev-accounts-repair-2026-04-14` indicates remediation occurred. A confirmation that the file is either redacted or moved to a private location should be performed before any next external docs-repo publish.

⚠️ **No API deprecation policy.** Still unwritten. Due before public launch.

⚠️ **Docstring style inconsistency.** See §2.

---

## 5. Security

### Strengths

- **Anthropic API key never reaches the client.** Architecturally enforced.
- **`detect-secrets` baseline prevents accidental commits.**
- **Stripe webhook signature validation** via `construct_event()`, before processing.
- **Swagger/ReDoc disabled in production.** `docs_url=None` when `APP_ENV == "production"`.
- **Parental consent flow for minors.** `requires_parental_consent` flag with `account_status=pending`.
- **GDPR erasure path** via `delete_auth0_user()`.
- **Forgot-password always returns 200.** Prevents email enumeration.
- **Bandit + pip-audit + Snyk + Ruff + detect-secrets** in CI.
- **Rate limiting on auth endpoints (Redis-backed).** `ip_auth_rate_limit` dependency (10 req/60 s per IP). Correctly uses `Depends()` to avoid the slowapi/Pydantic v2 decorator incompatibility.
- **COPPA compliance is now explicit.** `web/lib/compliance.ts` (242 LOC) codifies COPPA, FERPA, GDPR minor handling, data-minimisation, and explicitly excludes location and fingerprinting. Closes the v1.2 gap.
- **Auth0 management token cached.** 23h Redis TTL (1h buffer before Auth0's 24h expiry). Auto-evict and retry on 401.
- **RLS extended.** Migration 0028 (seven tables) is now joined by migration 0046 adding RESTRICTIVE RLS on `curricula` for platform-write protection.

### Gaps & Risks

⚠️ **`APP_ENV` is still not asserted against a valid enum.** `app_factory.py` checks `if settings.APP_ENV == "development"` to gate the dev router but does not fail startup on an unset or mistyped value. If a staging/production deployment has `APP_ENV` unset, it defaults to development behaviour and the dev router is live. This is the single most actionable hardening item — a one-line assertion.

⚠️ **Rate limiting still mixed.** The Redis-backed `ip_auth_rate_limit` dependency is correct and shared across workers; `src/core/limiter.py` (slowapi) remains in-process. Under a four-worker deployment, any endpoint protected only by slowapi can be bypassed 4×. Consolidate on the Redis-backed dependency for every auth-facing route.

⚠️ **No Content Security Policy (CSP) or HSTS verified.** For a platform serving minors, CSP is a baseline requirement. Verify in nginx/ALB configuration.

⚠️ **Pool arithmetic is warn-not-assert.** `app_factory.py` logs `DATABASE_POOL_MAX × WORKER_COUNT` vs `PGBOUNCER_POOL_SIZE` but does not refuse to start when the arithmetic is wrong. Under misconfiguration, silent connection exhaustion can occur after cache warmup.

---

## 6. Scalability

### Strengths

- **`SCALABILITY.md` remains production-grade.** Growth tiers, specific metric thresholds, infrastructure triggers.
- **Three-level caching.** L1 (`cachetools.TTLCache` per worker), L2 (Redis), L3 (Postgres).
- **PgBouncer in transaction-pooling mode.** `statement_cache_size=0` correctly configured.
- **Celery queues are separated.** `io`, `default`, `pipeline` — independent scaling per task type.
- **S3 content store.** Pre-signed URLs served directly from S3/CDN. Near-zero API load per lesson fetch at scale.
- **Celery Beat SPOF resolved by RedBeat.** Primary and standby Beat instances compete for a Redis lock; failover automatic within one `REDBEAT_LOCK_TIMEOUT` window.
- **Pipeline `--stream` flag.** C-5 added a streaming mode to `build_grade.py`, which reduces peak memory for Grade 12 + maths-heavy regeneration runs with the new 16384 `max_tokens` setting.

### Gaps & Risks

⚠️ **No load or performance tests.** Still true. The S3 path, Redis cache hit rates under concurrent load, Celery queue depth under peak pipeline runs, and the new streaming pipeline's steady-state memory are all theoretical.

⚠️ **`DATABASE_POOL_MAX` arithmetic is not a hard assertion.** See §5.

⚠️ **Slowapi + Redis rate-limit coexistence hurts scale.** See §5.

---

## 7. Additional Observations

### DevEx & Tooling

✅ `local-setup.sh` and `docker-compose.yml` are well-structured with health checks and service ordering.
✅ `dev_start.sh` convenience script lowers onboarding friction.
✅ `dependabot.yml` for automated dependency updates.
✅ API contract drift check (OpenAPI → TypeScript) in CI prevents silent breakage.
✅ SBOM artifacts (SPDX + CycloneDX) generated per CI run.
⚠️ No `Makefile`. Still absent. `make test`, `make lint`, `make migrate` would lower friction.

### Operational Readiness

✅ `/health` and `/metrics` endpoints exist.
✅ Sentry integration with PII scrubbing.
✅ Structured logs with correlation IDs.
✅ RedBeat gives Beat resilience without manual intervention.
⚠️ No documented alerting rules or runbooks for: DB connection exhaustion, Redis OOM, Stripe webhook backlog, Beat lock expiry, pipeline failure, `--stream` mode memory pressure.
⚠️ No documented Alembic `downgrade` testing. With 48 migrations, the rollback path for the most recent migration should be verified before each production deploy.

### SaaS Subscription Model Specific

✅ Stripe webhook deduplication (`already_processed`) is correct.
✅ Grace period (3 days) for `past_due` subscriptions.
✅ Entitlement cache invalidated on every subscription state change.
✅ `invoice.payment_action_required` handled — SCA/3DS email dispatched to school admin with hosted invoice URL.
⚠️ No documented process for Stripe test → live key rotation.
⚠️ School-as-primary billing (ADR-001) removed individual student and private-teacher subscription paths. Verify that all legacy subscription webhook events are either handled gracefully or that no live subscriptions remain on the old schema before launch.

### Content & Pipeline

✅ Pipeline format-drift validator (C-6) flags mismatches when a section title (e.g., "Balance Sheet") suggests tabular content but the output lacks tables/KaTeX.
✅ Per-subject prompt rules (C-2): Commerce (Balance Sheet/P&L/Trial Balance as tables), Natural Sciences (reactions + stoichiometry), Mathematics (every expression in KaTeX), CS (truth tables, Big-O).
✅ Attributed-blockquote rule (C-9) forbids invented citations and post-2000 sources; web renderer styles blockquotes consistently.
⚠️ Regen is in flight. Grade 11 Commerce complete; Grade 11 Science resuming; Grade 12 + maths-heavy pending. Until the full library is regenerated, content presentation quality is uneven across grades.
⚠️ C-7 (PDF smoke check) and C-8 (Kivy mobile parity for KaTeX + tables) not yet shipped. Mobile may degrade gracefully on rich content — this should be verified before the mobile app re-opens to real students.

---

## Priority Actions (Ordered)

| Priority | Action | Area |
|---|---|---|
| P1 | Add startup assertion: `APP_ENV ∈ {"development", "staging", "production"}` | Security |
| P1 | Consolidate rate limiting: remove slowapi in-process limiter from auth routes; use Redis-backed `ip_auth_rate_limit` only | Security |
| P1 | Turn `DATABASE_POOL_MAX × WORKER_COUNT ≥ PGBOUNCER_POOL_SIZE` warning into a hard startup assertion | Scalability |
| P1 | Expand E2E suite beyond accessibility — functional teacher admin flows, subscription checkout, school admin flows, content review | Testing |
| P1 | Resolve the 3 disabled axe rules (`color-contrast`, `html-has-lang`, `document-title`) — issue #189 | Accessibility |
| P1 | Unfixme the 6 school-admin curriculum submission specs — issue #188 | Testing |
| P2 | Add load tests (k6 or Locust) for content fetch, auth exchange, and the `--stream` pipeline | Testing |
| P2 | Document the mobile/web capability boundary before Epic 3 Path B activates | Architecture |
| P2 | Add cross-client auth continuity tests (mobile + web same student session) | Testing |
| P2 | Verify ADR-001 legacy Stripe webhook cleanup — no live subscriptions on old schema | Subscription |
| P2 | Ship C-7 (PDF smoke) and C-8 (Kivy KaTeX/table parity) before mobile re-opens | Content |
| P2 | Implement L-6 TTL sweeper before archived-curriculum storage cost becomes material | Governance |
| P3 | Add a `Makefile` | DevEx |
| P3 | Add runbooks: DB exhaustion, Redis OOM, Stripe webhook backlog, Beat lock expiry, `--stream` memory | Operations |
| P3 | Document Alembic `downgrade` testing procedure (48 migrations) | Operations |
| P3 | Schedule Kivy platform assessment before Epic 3 Path B activation | Architecture |
| P3 | Write API deprecation policy for `/api/v1` → `/v2` migration | Architecture |
| P3 | Consolidate docstring style (prefer Google style) | Documentation |
| P3 | Verify DEV_ACCOUNTS.md redaction/relocation is complete | Security |
