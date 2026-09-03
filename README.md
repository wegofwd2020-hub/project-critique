# Project Critique — WeGoFwd2020

Code review and architectural critique for StudyBuddy OnDemand, Mentible, Thittam, dronePrjs, MarketingTools, medtracker, atri-sangam, agastya, wegofwd-expenses, local_watch, timesheet, and the claude_memory tooling.

**Reviewed:** 2026-09-01 (v3.0 — **re-measured StudyBuddy OnDemand and Mentible against `origin/main` after ~3 months of drift**. **StudyBuddy** → **1,454 backend tests** (from 1,085), 68 migrations, **RLS on 21 tenant tables** (from 7), the **independent-teacher subscription tier is live** (Solo/Growth/Pro with a real Stripe-backed page), **server-side quiz grading** closed a client-trust hole, and a **live-stack "quiz suite"** was born from a P0 escape where every mocked layer had stubbed the one seam that shipped a dead "Submit" button — but it is **still late-build**: Epic 2's production-hosting blocker is open (never run outside local Docker) and both prior P2s (`purge_account.py` env-gate, onboarding-wizard E2E) are **unresolved**. **Mentible** → **ADR-037 SME expert-validation Studio built end-to-end** (capture→structure→validate→share, per-topic generate/approve/withdraw, publish→Library EPUB/PDF/DOCX, studio re-skin), production LOC **~13k→~61k**, **42 ADRs**, and the v2.5 **wegofwd-llm pin lag is closed** — but **doc-drift regressed** (`docs/STATUS.md` is 717 commits stale and never mentions ADR-037, though it's the doc CLAUDE.md names as canonical) and the **Celery migration is only half-done** (new trust path on Celery, legacy routers still in-process). New products (**agastya, wegofwd-expenses, local_watch, timesheet**) now exist but are **not yet in the suite** — first-reviews pending.)
**Prior:** 2026-07-18 v2.9 (**atri-sangam admitted to the critique suite** — a fixed-site GPS/PNT integrity monitor; stdlib-only core, 66 tests/90 %, headline gaps = spoofable SNTP reference channel + no runner/daemon; first product under the new public/private doc split) · 2026-07-14 v2.8 (**medtracker admitted to the critique suite (full four-lens first review v1.0)**: the portfolio's first *deployed-and-in-daily-use* product, and its only one with **no LLM at runtime** — runs at $0/month, built in a single day, the control case for what the shared-engine thesis is actually worth; because it handles personal health data in production, its four documents are held in the private `medtracker` repo and not published here) · 2026-07-01 v2.7 (**wegofwd-video admitted to the critique suite (full four-lens first review v1.0)**: the shared video-generation seam is the **second** cross-cutting shared dependency in the set, load-bearing for pramana (AI Veo path) and Kathai Chithiram (deterministic-renderer path); first review flags a provenance-integrity gap — `veo` stamps `model_verified=True` with no live call ever made — and no in-repo CI/watch yet) · 2026-06-13 v2.6 (**wegofwd-llm admitted to the watch set**, critique v1.0 — the first cross-cutting shared dependency; load-bearing for StudyBuddy_OnDemand, Mentible, and Kathai Chithiram) · 2026-06-09 v2.5 (StudyBuddy OnDemand → v1.7 on `main` @ `d50bc3e`; Mentible → v2.0 on `main` @ `40166ee` with the `wegofwd-llm` extraction itself; new four-lens sets for MarketingTools and claude_memory) · 2026-06-02 v2.4 (StudyBuddy OnDemand → critique v1.6 Authoring Studio/Epic 12; new project Mentible v1.0) · May 2026 v2.3 (all three re-measured on disk: StudyBuddy v1.5, Thittam v1.3, dronePrjs v1.1) · v2.2 (adds dronePrjs first-review; StudyBuddy v1.4; Thittam v1.2) · v2.1 (StudyBuddy visual-library wave 1+2) · April 2026 v2 (proto completion, Epic 10/11 delivery, T1 secret fix, schema injection fix, multi-tenant demo expansion)
**Reviewer:** Claude (Anthropic)
**Scope:** Architecture, code quality, test coverage, documentation, security, scalability

---

## Contents

| File | Project | Description |
|---|---|---|
| [studybuddy-critique.md](studybuddy-critique.md) | StudyBuddy OnDemand | Code review — architecture, quality, security, scalability |
| [mentible-critique.md](mentible-critique.md) | Mentible | Code review — architecture, quality, **BYOK security**, ops |
| [thittam-critique.md](thittam-critique.md) | Thittam | Code review — architecture, quality, security, scalability |
| [dronePrjs-critique.md](dronePrjs-critique.md) | dronePrjs (closedSpace + openSpace) | Code review — architecture, quality, safety, sim-only fidelity caveats |
| [MarketingTools-critique.md](MarketingTools-critique.md) | MarketingTools | Code review — scoped-retrieval marketing toolkit; zero-test gap, reproducibility |
| [claude-memory-critique.md](claude-memory-critique.md) | claude_memory (tooling) | System-design critique — robustness, privacy, portability, observability |
| [wegofwd-llm-critique.md](wegofwd-llm-critique.md) | wegofwd-llm (shared library) | Code review — multi-provider LLM seam; key-leak discipline, provider verification, watch cadence |
| [wegofwd-video-critique.md](wegofwd-video-critique.md) | wegofwd-video (shared library) | Code review — video-generation seam; provenance integrity, provider readiness, deterministic-render seam (dev-pattern · practices · cost linked below) |
| [atri-sangam-critique.md](atri-sangam-critique.md) | atri-sangam | Code review — GPS/PNT integrity monitor; SNTP anti-spoof gap, library-not-monitor framing, detector soundness |
| [wegofwd-expenses-critique.md](wegofwd-expenses-critique.md) | wegofwd-expenses | Code review — email→ledger expense pipeline; live daily cron, no CI, undocumented redaction scope |
| [local-watch-critique.md](local-watch-critique.md) | local_watch | Code review — read-only fleet monitor; fail-open incident history now closed, README metric-domain oversell |
| [timesheet-critique.md](timesheet-critique.md) | timesheet | Code review — testers time & payments Django app; Decimal money, earned-vs-amount rounding caveat |
| [studybuddy-development-pattern.md](studybuddy-development-pattern.md) | StudyBuddy OnDemand | Full lifecycle analysis — scoping, design, architecture, development |
| [mentible-development-pattern.md](mentible-development-pattern.md) | Mentible | Lifecycle analysis — subtractive scoping, ADR-driven re-scoping, security-first design |
| [thittam-development-pattern.md](thittam-development-pattern.md) | Thittam | Full lifecycle analysis — scoping, design, architecture, development |
| [dronePrjs-development-pattern.md](dronePrjs-development-pattern.md) | dronePrjs | Full lifecycle analysis — scoping by operating environment, ISA-as-SOR, phase-per-commit |
| [MarketingTools-development-pattern.md](MarketingTools-development-pattern.md) | MarketingTools | Lifecycle analysis — one-source-of-truth asset model, deterministic deck builders |
| [claude-memory-development-pattern.md](claude-memory-development-pattern.md) | claude_memory (tooling) | How the portable-memory system was designed and grew to 10 repos |
| [atri-sangam-development-pattern.md](atri-sangam-development-pattern.md) | atri-sangam | Design methodology — scope by failure-mode independence, specs-as-contracts, injectable determinism, honest subtractive scoping |
| [wegofwd-expenses-development-pattern.md](wegofwd-expenses-development-pattern.md) | wegofwd-expenses | Lifecycle analysis — subagent-driven TDD across 10 tasks, ADRs 0001–0003 |
| [local-watch-development-pattern.md](local-watch-development-pattern.md) | local_watch | Lifecycle analysis — safety-floor-first design, real production incidents converted into regression tests over a 3-day/37-commit hardening arc |
| [timesheet-development-pattern.md](timesheet-development-pattern.md) | timesheet | Lifecycle analysis — two chained SDD passes in a single 1h49m session |
| [studybuddy-practices.md](studybuddy-practices.md) | StudyBuddy OnDemand | Good practices, bad practices, and how to improve |
| [mentible-practices.md](mentible-practices.md) | Mentible | Good practices, bad practices, and how to improve |
| [thittam-practices.md](thittam-practices.md) | Thittam | Good practices, bad practices, and how to improve |
| [dronePrjs-practices.md](dronePrjs-practices.md) | dronePrjs | Good practices, bad practices, and how to improve |
| [MarketingTools-practices.md](MarketingTools-practices.md) | MarketingTools | Good practices, bad practices, and how to improve |
| [claude-memory-practices.md](claude-memory-practices.md) | claude_memory (tooling) | Good practices (durability, no-op-safe hook), risks (silent failure, secrets-in-memory) |
| [atri-sangam-practices.md](atri-sangam-practices.md) | atri-sangam | Good practices (injectable determinism, no fabricated data), bad practices (spoofable SNTP, unvalidated lat/lon), how to improve |
| [wegofwd-expenses-practices.md](wegofwd-expenses-practices.md) | wegofwd-expenses | Good practices (Decimal-as-TEXT money, refund-aware dedup), bad practices (no CI, undocumented redaction scope), how to improve |
| [local-watch-practices.md](local-watch-practices.md) | local_watch | Good practices (None-vs-empty-string probe signal, LLM never in the control path), bad practices (README oversells the metric domain), how to improve |
| [timesheet-practices.md](timesheet-practices.md) | timesheet | Good practices (derived-not-stored money, CSV formula-injection guard), bad practices (undocumented rounding caveat, no-auth risk unstated), how to improve |
| [agastya-development-pattern.md](agastya-development-pattern.md) | agastya | Design methodology — rehabilitating an inherited AI code-drop via SDD; safe-defaults, verify-don't-trust *(critique + cost held privately — see note)* |
| [agastya-practices.md](agastya-practices.md) | agastya | Good/bad practices, general engineering only — the product-specific security assessment is held privately *(see note)* |
| [NEW_MACHINE_SETUP.md](NEW_MACHINE_SETUP.md) | claude_memory (tooling) | Runbook — restore the per-project memory system on a fresh machine (13 repos) |
| [claude-memory-add-project.md](claude-memory-add-project.md) | claude_memory (tooling) | Runbook — wire a new project into git-backed memory + verify the auto-push |
| [elevator-pitch.md](elevator-pitch.md) | Siva Mambakkam | Elevator pitch for employers and consulting clients |
| [personality-review.md](personality-review.md) | Siva Mambakkam | Practice personality review — strengths, blind spots, and improvement plan |
| [linkedin-posts.md](linkedin-posts.md) | Siva Mambakkam | Five LinkedIn posts — thought leadership, compliance, standards, availability |

> **medtracker — reviewed, but held privately.** medtracker runs in production with real personal
> health data, so its repo is private and its full four-lens set (critique · practices · cost ·
> development-pattern, 2026-07-14) lives **there**, at `medtracker/docs/critique/`, rather than in
> this public repo. Publishing a line-referenced weakness list for a live service holding real health
> records would be the one place in this portfolio where an honest critique does more harm than good.
> What is safe to say here: it is the **only product with no LLM at runtime**, it costs **$0/month to
> run**, and it was built in **one day** — the portfolio's control case for what the shared-engine
> thesis is actually worth.

> **agastya — reviewed 2026-09-02, security assessment held privately.** agastya is a **live-intended
> cyber-detection product**, so a public line-referenced weakness list would be an attacker roadmap.
> Its **critique and cost** lenses therefore live privately in `wegofwd-private-docs/agastya/`; only the
> **development-pattern** and **practices** lenses (general engineering method, no vulnerability map) are
> published here. What is safe to say: it is a FastAPI threat-monitoring service whose **deployment
> hardening is genuinely well-executed** (read-only-by-default container, safe-state-as-default design),
> reviewed as an **inherited AI code-drop rehabilitated via SDD** (a prior "41+ tests passing" claim was
> false — 111 real tests verified on `origin/main`, 7 delivered bugs already fixed by the rehab work).
> The honest maturity read — how much of it is a *demonstrator* versus a shipping detector — is in the
> private critique.

---

## Quick Summary

### StudyBuddy OnDemand

**Overall:** Late-build / pre-production — feature-rich but never run outside local Docker. **2026-09-01 (critique v1.8):** re-measured on `main` @ `b686be7` (346 commits since `d50bc3e`) — **1,454 backend tests / 129 files (2 skipped), 68 migrations (latest 0068), 19 Playwright specs / 3,156 LOC (120 tests / 4 projects), 975 web-unit tests, 8 ADRs, zero TODO/FIXME**. The window's headline is **grade integrity + test honesty**: quizzes are now **graded server-side** (a breaking change — the client's score is no longer trusted), and after a P0 escape (#524 — a dead "Submit" button every mocked layer had stubbed past) a **live-stack `quiz_suite`** now runs against a real dev stack (excluded from normal CI). Also this window: the **independent-teacher subscription tier went from schema to product** (Solo/Growth/Pro, Stripe checkout/upgrade/downgrade, a real `/teacher/subscription` page), **RLS extended to 21 tenant tables** (through migration 0068, from 7), a portal-wide warm-neutrals + measured a11y-contrast pass (#189), stable per-question identity + question-grain feedback (ADR-007/008, migrations 0067/0068), and **Epic 18** (corporate-compliance scenario catalog) shipping 2 scenarios as a gated `/jt` demo *inside* the main app (the advisor's no-fork "Path A"). **ADR-006** is now Accepted; **ADR-005** (school_admin superset) is still *Proposed*. **Epic 17** (corporate-L&D fork) remains CONTESTED; **Epic 2** (production launch) is still pending — the hosting blocker is now the single biggest gap between code maturity and deployability.

| Area | Rating | Key Finding |
|---|---|---|
| Architecture | 🟢 Strong | StorageBackend abstraction, platform/school governance split, Streams; **server-side quiz grading** closes a client-trust seam |
| Code Quality | 🟢 Strong | Zero TODO/FIXME holds; a **live-stack `quiz_suite`** was added after every mocked layer missed a prod-dead button (#524) |
| Test Coverage | 🟡 Good | 1,454 backend / 129 files + 19 Playwright (3,156 LOC) + 975 web-unit; **onboarding wizard + Administration menu still E2E-uncovered** (prior P2 open); #188 school-admin flow has 5 `fixme`'d assertions |
| Documentation | 🟢 Strong | CLAUDE.md current; ADR-006 Accepted, ADR-007/008 added; but `web/lib/pricing.ts` still comments the *live* teacher tier as "future — #57" (stale) |
| Security | 🟢 Strong | RLS now on 21 tenant tables, server-side grading; **`purge_account.py` still gated only by a comment, not an `APP_ENV`/hostname assertion** (prior P2 open); never exposed outside local Docker |
| Scalability | 🟡 Good | S3/Local via StorageBackend, RedBeat; no load tests; deployability gated on Epic 2 hosting |

**Top 3 actions:** (1) Resolve **Epic 2's hosting blocker** — the code is feature-complete (`late-build`) but has never run outside local Docker; biggest maturity-vs-deployability gap. (2) Harden `purge_account.py` with a real environment/hostname gate before any deploy (still comment-only). (3) Add E2E for the onboarding wizard + Administration menu and finish #188's 5 `fixme`'d follow-ups (still web-unit-only).

💰 **Real-world cost** — the v2.5 figure (conventional **~$1.54M US / $510k blended** vs **~$54–56k actual** to reach `d50bc3e`; **~28× US / ~9× blended**) is carried forward but now **understates scope**: +369 tests, +8 migrations, doubled ADR count, the independent-teacher subscription surface, Epic 18's corporate-scenario system (avatar video via D-ID), and server-side grading were all added since. A refreshed cost pass is a v3.0 follow-up (held privately in `wegofwd-private-docs`).

---

### Mentible

**Overall:** Pre-deploy, but the v2.0 "MVP" is now a large multi-surface app. **2026-09-01 (critique v2.1):** re-measured on `main` @ `e13f10b` (v0.2.63; 1,126 commits since `40166ee`) — **~61k production LOC** (backend src 16,037 / **929** `def test_` sync+async; compiler 3,881 / 201 test blocks; mobile 41,507 / 1,649 test blocks), **42 ADRs**. The headline is **ADR-037 — the SME expert-validation Studio — built end-to-end**: capture→structure→validate→share, per-topic generate/approve/withdraw endpoints (`backend/src/trust/`, migrations 0009–0026+), publish→Library with EPUB/PDF/**DOCX** export, and a Playfair studio re-skin (10 theme palettes; ADR-038 self-corrected a forced-navy UX bug from field feedback via PR #375/#376). The v2.5 **`wegofwd-llm` pin lag is closed** (exact v0.2.0 both sides). Per-user private hosted library (ADR-033/035) remains **design-only** (zero storage code). Still BYOK, adults-only, compiles to portable EPUB3/PDF.

| Area | Rating | Key Finding |
|---|---|---|
| Architecture | 🟢 Strong | Packaged provider seam; trust/Studio pipeline shipped; **new inconsistency** — mixed job runners (Celery for the new trust path, in-process `BackgroundTasks` still in generate/export/library/structure) |
| Code Quality | 🟢 Strong | ruff/tsc clean; single brand constant; backend test defs 96→**929**, mobile test blocks 132→**1,649** |
| Test Coverage | 🟡 Good | ~929 backend + 201 compiler + 1,649 mobile blocks; **still no live-Anthropic or on-device E2E** (the gate everything waits on); new trust/Celery surface coverage not separately verified |
| Documentation | 🟡 **Regressed** | CLAUDE.md is current + self-corrects the old "Pre-MVP" line — but it names `docs/STATUS.md` as canonical, and STATUS.md is **717 commits stale** (frozen 2026-07-03, zero mention of ADR-037); `project-status.yaml` still says `pre-mvp` |
| Security (BYOK) | 🟢 Strong | Pattern B + the 422-scrub leak fix hold; not re-audited deeply this pass |
| Scalability / Ops | 🟡 Good | Celery+Redis now runs trust generation (job-runner ceiling **half-closed**); `wegofwd-llm` pin now exact but still `git+https` (no registry); `wegofwd-secure@v0.1.0` carries the same git-pin risk |

**Top 3 actions:** (1) **Refresh `docs/STATUS.md`** — the doc CLAUDE.md names canonical, yet 717 commits stale and missing ADR-037 (doc-drift *reopened*, escalated). (2) **Finish the Celery migration** — move generate/export/library/structure off in-process `BackgroundTasks`, or document why they stay. (3) **Reconcile ADR-037's `Status: Proposed` header with its built-and-merged reality** (a recurring ADR-status-vs-reality pattern here). Running one real BYOK E2E remains the standing pre-deploy gate.

💰 **Real-world cost** — the v2.0 figure (conventional **~$524k US / $179k blended** vs **~$26k actual**, BYOK/zero token cost; **~16× US**) is carried forward but **materially outgrown** (~13k→~61k LOC + the full ADR-037 Studio since). Note **ADR-039 (Accepted 2026-08-16)** pivots monetization to a **services-led** sequence (Discovery/Sprint/Pilot) over self-serve billing — a scope/positioning change for the private cost/scorecard doc. Refreshed cost pass = v3.0 follow-up.

---

### Thittam

**Overall:** Unchanged since v2.3 — re-checked 2026-06-09, HEAD is still `3883769` (the Go 1.25.10 security bump, 2026-05-13); everything dated later is the nightly `chore(progress)` bot. v2.3 verified the code on disk: the registration saga, reporting read-model, and impersonation lifecycle are all implemented. 10 protos (1,715 LOC, 221 messages); tests 1,203 / 86 files. The `audit_log` REVOKE remains the one open P0.

| Area | Rating | Key Finding |
|---|---|---|
| Architecture | 🟢 Strong | All 10 protos complete; grpc-gateway REST shadow for browser auth; shadcn/ui web tier; 13 ADRs |
| Code Quality | 🟢 Strong | T1 secrets via Vault → memory; sentinel errors; sqlc + buf enforcement; doc-drift CI active |
| Test Coverage | 🟡 Good | 1,203 tests / 86 files; Playwright scaffold + budgets-journey; load/chaos absent |
| Documentation | 🟢 Strong | docs live in separate `thittam_docs` repo (not on disk) — "71 files / 13 ADRs" unverified this pass |
| Security | 🟡 Good | Schema injection + T1 verified on disk; impersonation lifecycle implemented (4h cap); `audit_log` REVOKE still commented (P0) |
| Scalability | 🟡 Good | Tenant-per-schema needs strategy past 500 tenants; reporting read-model implemented; no circuit-breaker policy |

**Top 3 actions:** (1) Apply `audit_log` REVOKE UPDATE/DELETE — the last open P0, (2) Stress the registration saga's compensation paths under partial-failure tests, (3) Review `thittam_docs` directly to verify the 13-ADR / 71-file claims.

💰 **Real-world cost** — conventional 5.5-FTE team would have spent **~$2.20M (US) / $711k (blended)** to reach HEAD `ce64378`. Actual: **~$36k all-in / ~$2k cash, 41 days, one founder.** Headline: **61× cheaper US / 20× blended, 7.5× faster.**

---

### dronePrjs

**Overall:** Unchanged since v2.3 — re-checked 2026-06-09, HEAD is still `5e38a44` on `main` (0 commits since). Eight commits (Phase 0–6 complete + Phase 3 partial). 114 tests (~133 collected), 95.3 % coverage, `mypy --strict` + `ruff` clean, CI in place. Umbrella for `closedSpace` (indoor GPS-denied warehouse inventory drone) and `openSpace` (outdoor — stub only) over a shared `engine/` Protocol layer. 35 of 44 ISCs complete; sim-only fidelity (Phase 8 pilot outstanding).

| Area | Rating | Key Finding |
|---|---|---|
| Architecture | 🟢 Strong | Engine Protocols + in-process `engine.sim` reference impl; anti-bleed enforced by AST scan; ISA.md is the system-of-record (634 lines) |
| Code Quality | 🟢 Strong | `mypy --strict` across 29 source files clean; ruff clean; frozen dataclasses with slots; zero TODO/FIXME |
| Test Coverage | 🟢 Strong | 114 tests, 95.3 % coverage, co-located by source path; e2e mission test against the sim |
| Documentation | 🟢 Strong | ISA fuses PRD/criteria/test-strategy/decisions/changelog; three-tier CLAUDE.md |
| Safety | 🟡 Good | Pre-arm gate; map staleness + provenance first-class; GPS forbidden in closedSpace by static probe; ISC-15 link-loss RTH still open |
| Scalability | 🟡 Good | Two-tier simulator strategy correct; openSpace is still a stub — engine contract is single-consumer until that changes |

**Top 3 actions:** (1) Write `openSpace/ISA.md` + a `GPSProvider` reference sim so the engine contract has a second consumer, (2) Implement ISC-15 link-loss RTH, (3) Build the perception→command latency soak harness alongside the Phase-3 Gazebo tier.

💰 **Real-world cost** — conventional 3.75-FTE robotics team would have spent **~$522k (US) / $179k (blended)** to reach HEAD `5e38a44`. Actual: **~$12k all-in / ~$0.2k cash, ~2 weeks, one founder.** Headline: **44× cheaper US / 15× blended, 8× faster.** *Hardware costs (Phase 8) excluded.*

---

### Atri Sangam

**Overall:** New this cycle (v2.9, first review 2026-07-18). A fixed-site **GPS/PNT integrity monitor** — cross-checks a GPS receiver (NMEA RMC/GGA) against independent references (SNTP, local-clock holdover, celestial prediction) and raises explainable **step / CUSUM / staleness** alarms on jamming, spoofing, or outage. Reviewed from a source snapshot (no git history). 1,961 source LOC (23 files), 719 test LOC, **66 tests / 90 % coverage**, 6 OpenSpec contracts, CI on Python 3.10 + 3.12, 0 TODO/FIXME, stdlib-only core. `Development Status :: 3 - Alpha`, `v0.1.0`, MIT.

| Area | Rating | Key Finding |
|---|---|---|
| Architecture | 🟢 Strong | Fan-in `DiscrepancyEngine` referee; three detectors mapped to three attack shapes; pure-transformer collectors; `FALLBACK_DETECTOR` channel auto-registration as a third-party extensibility seam |
| Code Quality | 🟡 Good | Frozen dataclasses + fail-loud `__post_init__` validation, typed exception hierarchy, 0 TODO — but **no ruff/mypy gate**, and NMEA lat/lon parsed without range validation |
| Test Coverage | 🟢 Strong | 66 tests, 90 %, hand-derived assertions (SNTP offset to the decimal, drift to 1e-9), spec scenarios mirrored — holes at the seams (`samples_from_rmc`, `collect()` failure, `status()`) |
| Documentation | 🟢 Strong | Exceptional README + 6 OpenSpec contracts (numeric scenarios) + a `comparable-systems.md` landscape vs BlueSky/GPSPATRON/RAIM/chrony |
| Security & Safety | 🔴 Critical | **SNTP client has no anti-spoofing origin/replay validation** — the reference channel meant to catch spoofing is itself off-path-spoofable. No fabricated data (typed failures + staleness) is done right |
| Scalability & Ops | 🔴 Critical | **No runner/daemon exists** — a tested detection *library* + red-team simulator, not a deployable monitor; no concurrency model for multi-channel operation |

**Top 3 actions:** (1) Harden the SNTP client — verify response source address + echoed originate timestamp, validate mode/stratum; (2) Build and test a runner service (serial/gpsd → factory; periodic NTP/holdover/staleness ticks) — the gap between library and monitor; (3) Add lat/lon range validation and fix the dashboard to consume `DiscrepancyEngine.status()` instead of re-deriving a lossy binary status from unbounded alarm history.

💰 **Real-world cost** — a conventional **GNSS/PNT specialist** team would have spent **~$128k (US) / ~$44k (blended)** for the equivalent detection-logic library + simulator + specs + tests + CI. Actual: **~$8.8k all-in / ~$0.15k cash, one founder.** Headline: **~15× cheaper US / ~5× blended**, at a **~850× cash-only ratio** — a specialist-infra multiplier (between MarketingTools's ~7.5× and dronePrjs's ~44×), because getting CUSUM/SNTP/celestial math correct is senior judgement AI accelerates but doesn't replace. *Runner/daemon and hardware excluded from both columns; actual-time inferred (no git history).*

---

### MarketingTools

**Overall:** Small, single-author Python "scoped-retrieval marketing toolkit" (branch `main` @ `76addee`, 4 commits over ~8 days). Markets the product portfolio (StudyBuddy, Mentible, Pramana, home-school, special-needs) from one source of truth (`assets/products.yaml`): `generate.py` builds a scoped `(product × audience × channel × framing)` prompt and asks Claude for channel-ready copy; `decks/` deterministically builds python-pptx pitch decks over a shared multi-brand theme engine; `campaigns/campaigns.csv` is a hand-maintained outreach log. **~2,274 LOC (1,790 Python), 22 source files, zero tests.**

| Area | Rating | Key Finding |
|---|---|---|
| Architecture | 🟢 Strong | One-source-of-truth asset model; scoped-prompt builder mirrors the products' own scoped-retrieval IP; shared theme engine |
| Code Quality | 🟢 Strong | Clean, readable; minor dead `qn` import (`theme.py:21`); no linter config |
| Test Coverage | 🔴 Critical | Zero tests on trivially-testable pure logic (`build_prompt` framing heuristic, optional-field fallbacks) |
| Documentation | 🟢 Strong | Honest README; landing-page generation explicitly marked a stub |
| Security | 🟡 Gap | Key handling correct (env-only, gitignored, no committed secrets) but no `.env.example`/validation; contact email hardcoded into deck content (breaks its own one-source rule) |
| Scalability / Reproducibility | 🟡 Gap | `requirements.txt` declares only `anthropic`+`PyYAML`; deck builders need `python-pptx`+`Pillow` (prose-only) → a clean clone can't build decks |

**Top 3 actions:** (1) Add tests for the pure prompt/framing logic, (2) Complete `requirements.txt` (`python-pptx`, `Pillow`) so decks build from a clean clone, (3) Move the hardcoded contact email into the one-source asset library + add `.env.example`.

💰 **Real-world cost** — conventional build ~1.3 EM → **~$33k (US)**. Actual: **~$4.4k all-in, ~8 days, one founder.** Headline: **~7.5× cheaper US / ~2.3× blended** (deliberately modest — proportionate to a 2.3k-LOC tool dominated by design/content work).

---

### claude_memory (tooling)

**Overall:** Small, durable, well-documented DX infrastructure (not an app): a git-backed durability layer for Claude Code's per-project memory. Each project's memory is its own git repo under `~/.claude/projects/<encoded-path>/memory/`, and a single global `Stop` hook in `~/.claude/settings.json` auto-commits and pushes it to a private `github.com/wegofwd2020-hub/<name>-memory` remote after every session. **10 memory repos, 10/10 private; hook present (async, 30 s, no-op-safe); runbooks [`NEW_MACHINE_SETUP.md`](NEW_MACHINE_SETUP.md) (141 lines) + [`claude-memory-add-project.md`](claude-memory-add-project.md) (117 lines).**

| Area | Rating | Key Finding |
|---|---|---|
| Architecture | 🟢 Strong | Remotes are source of truth; symlinks are a browse-only view; encoded-path convention; hook derives path from `$PWD` |
| Robustness | 🟡 Gap | Every git op is `>/dev/null 2>&1` + async → failures are silent (see findings) |
| Security / Privacy | 🟡 Gap | All private, but memory is pushed verbatim — no redaction, no at-rest encryption beyond GitHub's, one `repo`-scoped token gates all 10 |
| Portability | 🟡 Gap | Encoded path embeds username/layout → a different machine silently resolves the wrong store (documented caveat) |
| Observability | 🔴 Critical | No sync log, no health check — a broken store is invisible until you go looking |
| Maintainability | 🟢 Strong | ~6-line hook + two clear runbooks; trivially extended per project |

**Top 3 actions:** (1) **Make the hook observable** — one sync-log line + a `claude-memory-doctor` that flags no-`.git`/no-remote/ahead-of-origin (retires the silent-failure gap), (2) Add a secret-scan/redaction step before push, (3) Document/automate the absolute-path remap for new machines.

> **Finding that already bit a project:** `pramana`'s memory dir held 4 real files but was never `git init`'d, so the silent hook no-op'd and its memory was machine-local-only with no remote — until it was wired up on 2026-06-09. This is the silent-failure gap, observed in the wild.

💰 **Real-world cost** — a correct, documented, verified version is ~4 senior infra/DX engineer-days → **~$6–7k (US) / ~$1.8k (blended)**. Actual: ~1–2 interstitial founder-days, **~$1.7k all-in, ~$0 direct cash** (free private repos, no compute). Headline: large cash-only ratio, modest all-in multiplier (~1–4×) — the expected result for small, judgment-heavy infra.

---

### wegofwd-llm (shared LLM seam)

**Overall:** Small, disciplined, **already load-bearing for the portfolio**. v0.1.2 at HEAD `4823606` (2026-06-09). Three commits, 778 src LOC / 620 test LOC, 9 providers registered (1 native Anthropic + 8 OpenAI-compat), 48 tests with no live APIs, CI present, zero TODO/FIXME. The two non-negotiable rules — *"the package never sources keys"* and *"no key ever leaks"* — are real in code (every SDK path is `raise ... from None`, no env reading anywhere). Three-axis versioning (package semver / `LLM_CONTRACT_VERSION` / per-provider `integration_version`) is stamped into `provenance()`. **Consumed by StudyBuddy_OnDemand (PRs #430/#431), Mentible (the extraction source), and Kathai Chithiram** — which is why "top-level watch" is warranted: a regression here is a portfolio incident, not a single-product incident.

| Area | Rating | Key Finding |
|---|---|---|
| Architecture | 🟢 Strong | Frozen-dataclass contract, schema-agnostic conformance loop, logical-role pinning; **no retry/failover/circuit-breaker policy in-package** — each consumer must write its own |
| Code Quality | 🟢 Strong | PEP 561 `py.typed`; ruff config mirrors consumers; one docstring drift in `openai_compatible` re `raw=` |
| Test Coverage | 🟡 Good | 48 tests mocked correctly; **no key-leak regression test** (the hardest rule has zero coverage); no per-provider live-smoke job |
| Documentation | 🟢 Strong | README + module docstrings carry the *why*; **no CHANGELOG / SECURITY.md / async-consumer note**; UNVERIFIED markers live only inline |
| Security (BYOK) | 🟢 Strong | BYOK enforced at construction; `raise ... from None` everywhere; typed errors → safe HTTP mapping; **no test guards the leak rule** |
| Scalability / Ops | 🟡 Good | Stateless, no warm-up; **`git+https` distribution, no PyPI**; Mentible already lags at `v0.1.0` while package is at `v0.1.2`; **4 of 9 providers carry `UNVERIFIED` defaults**, gemma is dead-on-arrival (`base_url=""`) |

**Top 3 actions:** (1) Resolve the `gemma` registry entry (remove / wire / mark unavailable) and the `license="Proprietary"` vs `public` GitHub contradiction, (2) Add the **key-leak regression test** (mock SDK to raise an exception whose `repr()` contains the api_key; assert the wrapped `LLMError` does not stringify it), (3) Document sync-only / async-consumer pattern + add a *"providers — verification matrix"* table to the README. See [wegofwd-llm-critique.md](wegofwd-llm-critique.md) §7 for the full ranked list.

> **Watch case.** Because three on-disk consumers already depend on this package, a regression here is a portfolio outage. §8 of the critique proposes a watch cadence (weekly commit-delta + on-version-bump + on-consumer-pin-change). **Wired and live** as `wegofwd-llm/.github/workflows/watch.yml` — weekly + on-push + manual; opens a PR here when anything changes. The `PROJECT_CRITIQUE_PR_TOKEN` secret is set and the workflow is **verified green** (2026-07-01); baseline reset to HEAD `3b08f442` so quiet weeks produce no PR (see `wegofwd-llm/.watch/README.md`).

💰 **Real-world cost** — conventional median **~$48k (US) / ~$16k (blended)**, ~9–10 weeks for a one-senior-plus-reviewer team. Actual: **~$5.6k all-in, ~3–4 founder-days, 5 calendar days.** Headline: **~8.5× cheaper US / 5.6× blended, ~9.5× faster** — smaller multiplier than products (e.g. StudyBuddy's ~28×) because specialist infra compresses less.

---

### wegofwd-video (shared video seam)

**Overall:** Small, disciplined, and — like `wegofwd-llm` one domain over — **already load-bearing for two products**. v1.0.0 at HEAD `233f248` (2026-06-30). Four commits in a single evening, 741 src LOC / 362 test LOC, 30 tests (no live APIs), **zero core dependencies** (optional `[veo]` extra), zero TODO/FIXME. The registry / spec / role-routing / provenance / error-hierarchy are the `wegofwd-llm` pattern reused *by type, not by copy* — created **standalone up front** (ADR-026 D7, a conscious exception to the "extract on the 2nd consumer" rule) and frozen at v1.0 only once both real integrations were wired green. Two provider paths are live: **`veo`** (Veo 3.1, AI) for pramana's compliance lesson-video, and a **`deterministic-renderer`** that wraps a caller-supplied `render_fn` for Kathai Chithiram (its Blender/matplotlib code stays in the consumer; child content never leaves the boundary). It ships the **two key-leak regression tests `wegofwd-llm` lacked** (`repr` safety + code-based error mapping). **Second cross-cutting shared dependency** → the same top-level-watch argument applies.

| Area | Rating | Key Finding |
|---|---|---|
| Architecture | 🟢 Strong | Frozen-dataclass contract, capability pre-check (reports multiple violations at once), provenance+seed reproducibility, callable-injection deterministic path; pattern reused verbatim from wegofwd-llm |
| Code Quality | 🟢 Strong | Zero-dep core with lazy per-provider SDK import; ruff config mirrors the family so a file lints identically across `wegofwd-*` |
| Test Coverage | 🟡 Good | 30 tests incl. **two key-leak regressions** wegofwd-llm lacked; but **no live Veo call has ever run** (all Veo tests use a fake client); runway/kling untested |
| Documentation | 🟢 Strong | README + ADR-026 carry the *why*; no CHANGELOG/SECURITY.md; async/queue-consumer note is thin |
| Security (BYOK) | 🟢 Strong | BYOK enforced pre-call; `raise ... from None`; `repr=False` on `asset_bytes`/`raw`; error mapping branches on HTTP code, never the exception string |
| Provider readiness | 🔴 Needs work | **`veo` stamps `model_verified=True` with no live run** — `provenance()` over-claims a live-verified basis onto immutable `CourseVersion`s; **`runway`/`kling` are dead-on-arrival** — listed by `available_providers()` but `build_provider()` has no constructor and always raises |
| Distribution / CI | 🔴 Needs work | **No in-repo CI and no `.watch/`** (the "conformance gate" runs by nobody automatically); consumers pin `v0.1.2` while frozen at `v1.0.0`; `Proprietary` license on a cross-repo shared lib |

**Top 3 actions:** (1) Fix the `veo` `model_verified` integrity gap — set it `False` until a live run passes (or split `docs_verified` / `live_verified`), so `provenance()` can't stamp a live-verified basis onto a `CourseVersion` for a call that never happened; (2) Add in-repo CI (`ruff` + `pytest`) and a `.watch/` mechanism mirroring `wegofwd-llm`, since this is now a portfolio-level shared dependency; (3) Resolve `runway`/`kling` dead-on-arrival (wire constructors or filter them from `available_providers()`), and either wire Veo Ingredients-to-Video or guard the currently-aspirational contract surface. See [wegofwd-video-critique.md](wegofwd-video-critique.md) for the full ranked list, plus [development-pattern](wegofwd-video-development-pattern.md) · [practices](wegofwd-video-practices.md).

> **Watch case.** `wegofwd-video` is the **second** cross-cutting shared dependency in the set (after `wegofwd-llm`): a regression cascades into both pramana and Kathai Chithiram. Its watch is now **wired and live** too — `wegofwd-video/.github/workflows/watch.yml` (plus an in-repo `ci.yml`), the `PROJECT_CRITIQUE_PR_TOKEN` secret set, **verified green** (2026-07-01), baseline at HEAD `837dfb5`. **Both shared-library watches are now active** — each opens a single PR here only when a real commit lands in its repo.

💰 **Real-world cost** — conventional **~$42k (US) / ~$14k (blended)**, ~8 calendar weeks for a one-senior-plus-reviewer team. Actual: **~$2.4k all-in, ~1–2 founder-days, one calendar day.** Headline: **~17× cheaper US / ~6× blended, ~40× faster** — the large time multiplier is the *derivative discount*: the hard design was amortized from `wegofwd-llm`, so this was domain-specialization + Veo long-running-job wiring, not a from-scratch seam. Caveat: some scope is interface-only (no live Veo run, two placeholder providers), so a *fully proven* library costs more than the banked figure.

---

### wegofwd-expenses

**Overall:** New this cycle (v3.1, first review 2026-09-03). A deterministic **email→ledger expense pipeline** for a single WeGoFwd mailbox — five fixed stages (`mailfetch` → `billclassify` → `billextract` → `ledger` → `expensereport`) plus a self-contained HTML dashboard (`expenseweb`), with the LLM confined to classification/extraction behind schema gates and never in control flow (ADR-0001, "pipeline, not agent"). Measured against `wegofwd2020-hub/wegofwd-expenses` `master` @ `aaa7fb3` (2026-08-01). **130 tests** (verified by running pytest locally; up from 76 at the 2026-07-06 merge), 3 ADRs, no CI, no lint/type gate. The headline finding is a **correction to prior tracking, not a code defect**: the pipeline has been running as a **live daily cron against the real mailbox continuously since 2026-07-06** — not the "dry-run pending" state carried in prior notes — and this review found direct production evidence that its own anticipated Gmail-cursor-retention gotcha fired for real on 2026-07-12 and self-healed exactly as designed.

| Area | Rating | Key Finding |
|---|---|---|
| Architecture | 🟢 Strong | Pipeline-not-agent boundary is structural (separate installable packages, artifact-only handoff); LLM confined to two stages, both schema/confidence-gated |
| Code Quality | 🟡 Good | Decimal-as-TEXT money enforced everywhere (test-checked), typed exception hierarchies per package; but **no ruff/mypy config anywhere in the six packages** |
| Test Coverage | 🟢 Strong | **130 tests passing** (verified locally); the suite honestly names its own two untested boundaries (Gmail wire, pdfminer) in module docstrings |
| Documentation | 🟡 Good | Three ADRs record real trade-offs; but the **README still reads as pre-dry-run** — no mention of the live daily cron or two months of production history |
| Security | 🟡 Good | Uniform env→file(`0600`)→prompt credential precedence; idempotent `message_id` dedup protects financial integrity; but `redact.py`'s SSN/card-only scope is undocumented as a deliberate trade-off |
| Scalability / Ops | 🟡 Good | Lockfile + bounded-lookback cursor recovery **proven live** (self-healed a real 2026-07-12 incident); but no CI, no alerting on a halted cron, no log rotation |

**Top 3 actions:** (1) Refresh the README and docstrings to reflect production reality — it is live, not dry-run-pending. (2) Add CI — even one workflow running `pytest` across all six packages would close the largest process gap found. (3) Document `redact.py`'s narrow redaction scope as a deliberate decision (a fourth ADR).

💰 **Real-world cost** — Headline: **~59× cheaper all-in (US) / ~21× (blended)**. Full analysis held privately in `wegofwd-private-docs`.

---

### local_watch

**Overall:** New this cycle (v3.1, first review 2026-09-03). A read-only **personal-fleet monitor** — per-machine collectors (Linux + macOS) → sync over Tailscale → a central aggregator on `mambakkam` → deterministic threshold/trend rules → an LLM agent that writes plain-language recommendations **never in the control path** → an HTML dashboard + Markdown report, surfaced via a `wegofwd-hub` tile. Measured against `wegofwd2020-hub/local_watch` `main` @ `13e387e` (2026-08-31). 848 production LOC / 1,170 test LOC, **130 tests**, CI (pytest only, Python 3.11 + 3.13). The headline is a real production incident history: between first merge (2026-08-29) and the three-machine live deploy (2026-08-31), the system **failed in production four distinct ways — three of them the exact "fails open, reads as healthy" class it exists to prevent** — and every one was diagnosed, fixed, and pinned under a regression test inside the same 3-day, 37-commit, 5-PR window.

| Area | Rating | Key Finding |
|---|---|---|
| Architecture | 🟢 Strong | Strict one-way layering (collectors→store→rules→agent→report); LLM-out-of-control-path is structural — `agent.recommend()` only ever populates an opaque, uniformly-escaped text dict |
| Code Quality | 🟡 Good | Atomic-write race fix (motivated by a real `RunAtLoad` race), careful disk-trend numerics (min points + min time span); but **`ruff` is a dev dependency never run in CI** |
| Test Coverage | 🟢 Strong | **130 tests**; each of the four historical incidents has a named regression test, not incidental coverage |
| Documentation | 🟡 Good | Deploy runbook is exceptional (exact verification commands, explicit "do not continue" gates); but the **README oversells the collected metric domain ~5×** and its status line is stale ("not yet running on the fleet") |
| Safety | 🟢 Strong | All 4 production incidents (3-way fail-open, XSS via LLM output, deploy gap, self-sync bug) verified **FIXED with dedicated regression tests**; no defense-in-depth beyond the Tailscale transport itself |
| Scalability / Ops | 🟡 Good | Staggered timer cadence explicitly coupled to the staleness threshold; but the aggregator is a single point of failure and no alerting exists on a stale/degraded state |

**Top 3 actions:** (1) Reconcile the README with the shipped collectors — implement or strike the ~10 metric domains that don't exist (only `disk_root_pct`/`mem_used_pct` are collected). (2) Update the README's status line and "Getting started" section to reflect the live 2026-08-31 three-machine deploy. (3) Add `ruff check` to CI alongside `pytest`.

💰 **Real-world cost** — Headline: **~39× cheaper all-in (US) / ~14× (blended)**. Full analysis held privately in `wegofwd-private-docs`.

---

### timesheet

**Overall:** New this cycle (v3.1, first review 2026-09-03). A small Django app living inside `wegofwd-hub` (not a standalone product repo) — testers'/contractors' time-by-project tracking and bank-payment tracking, rolled up into a per-tester running balance (earned − paid) and per-project cost, with a monthly drill-down and a CSV export for the books. Local-only, `127.0.0.1`, no authentication by design. Measured against `wegofwd2020-hub/wegofwd-hub` `main` @ `dd7d888` (2026-09-01). 309 production LOC, **39 app tests** (56 hub-wide) — built in a single ~1h49m session across two chained SDD passes. The money model is right: `hours`/`rate_usd`/`amount_usd` are `Decimal` end-to-end, and `amount_usd`/`total_cost_usd` are derived `@property` methods computed on read, never stored columns. The one real subtlety: the app computes "earned" **two different ways that can disagree by a cent** — `TimeEntry.amount_usd` rounds per-entry, while `summary.py`'s dashboard figure sums first and rounds once — both individually valid, neither documented as different from the other, and no fixture currently exercises the case where they diverge.

| Area | Rating | Key Finding |
|---|---|---|
| Architecture | 🟢 Strong | Decimal end-to-end, derived-not-stored money properties (no column to drift); `summary.py` is a pure zero-HTTP aggregation module |
| Code Quality | 🟡 Good | CSV formula-injection guard correctly scoped (OWASP trigger set) with its own regression test; but hub-wide `DEBUG = True` and no lint/type gate anywhere |
| Test Coverage | 🟢 Strong | **39 tests** (corrected from a stale "~52" planning estimate); real assertions incl. 3 rounds of 500-hardening regressions with inline "was 500: ..." comments |
| Documentation | 🟡 Good | Design doc and shipped code match exactly (same session); but the earned/amount rounding caveat and the no-auth risk assumption are undocumented at the point of risk |
| Security | 🟡 Good | CSRF on every mutating form, Django autoescape protects every free-text field; **no-auth-by-design** is fine for its actual `127.0.0.1` deployment but stated nowhere as an explicit risk boundary |
| Correctness | 🟡 Good | The **earned-vs-amount cent-reconciliation caveat** — two valid but different rounding conventions (round-per-entry vs. round-after-sum) can diverge by up to a cent; untested, undocumented |

**Top 3 actions:** (1) Document the earned-figure reconciliation caveat — one sentence stating the dashboard and the CSV/drill-down use different (both valid) rounding conventions. (2) Add a fixture that actually exercises the rounding disagreement, pinning current behavior with a test. (3) State the no-auth assumption where the risk lives (near `views.py`'s top or `ALLOWED_HOSTS`), not only in the roadmap's "out of scope" list.

💰 **Real-world cost** — Headline: **~24× cheaper all-in (US) / ~7× (blended)**. Full analysis held privately in `wegofwd-private-docs`.

---

## What Changed in v3.1 (2026-09-03)

This cycle admits **three new internal tools** to the critique suite — **wegofwd-expenses**, **local_watch**, and **timesheet** — completing the four products flagged as pending in v3.0, one day after **agastya** was admitted (2026-09-02). All three are reviewed under the **normal** public/private split (critique + development-pattern + practices public here, cost private in `wegofwd-private-docs`), unlike agastya's **tightened** split — none of these three has a live-intended attack surface that would turn a public weakness list into an attacker roadmap.

- **New: wegofwd-expenses — full four-lens first review (v1.0).** A deterministic email→ledger pipeline, measured against `master` @ `aaa7fb3`. Headline: the pipeline is not dry-run-pending as prior tracking held — it has been a **live daily cron since 2026-07-06** (130 tests, up from 76 at merge), and a real Gmail-cursor-retention incident on 2026-07-12 self-healed exactly as designed. Gaps are process-level: no CI, no lint/type gate, and an undocumented redaction-scope trade-off. Headline cost: ~59× cheaper US / ~21× blended.
- **New: local_watch — full four-lens first review (v1.0).** A read-only fleet monitor, measured against `main` @ `13e387e`, **live on 3 machines** since 2026-08-31. Headline: four real production incidents (three "fails open, reads as healthy") between first merge and live deploy, all fixed with dedicated regression tests inside a 3-day, 37-commit window — but the README oversells the collected metric domain ~5× and its status line is stale. Headline cost: ~39× cheaper US / ~14× blended.
- **New: timesheet — full four-lens first review (v1.0).** A testers' time & payments Django app inside `wegofwd-hub`, measured against `main` @ `dd7d888`, live at `127.0.0.1:8088/timesheet/` since 2026-09-01. Money is Decimal end-to-end with derived-not-stored totals; the one real subtlety is an underdocumented cent-level reconciliation gap between two valid ways of computing "earned." Headline cost: ~24× cheaper US / ~7× blended.
- **Doc-meta table standard shipped.** Every product document now carries a doc-meta table (git commit · branch · product version · doc-updated · last-deployed) right after its H1, per `DOC_STANDARDS.md` and stamped via `scripts/stamp_doc.py`; applied to all three new admissions' docs (and to agastya's the day before).
- **Other projects unchanged this cycle.** StudyBuddy OnDemand, Mentible, Thittam, dronePrjs, MarketingTools, medtracker, atri-sangam, agastya, claude_memory, wegofwd-llm, and wegofwd-video carry forward at their prior measurements.

---

## What Changed in v3.0 (2026-09-01)

This cycle is a **re-measurement**, not a new admission: the two fastest-moving products in the suite — StudyBuddy OnDemand and Mentible — were re-checked against `origin/main` after ~3 months of drift (their prior summaries were measured 2026-06-09). No new products were admitted, but four now exist that are **not yet reviewed** (see below).

- **StudyBuddy OnDemand → critique v1.8.** Re-measured on `main` @ `b686be7` (346 commits since `d50bc3e`): **1,085 → 1,454 backend tests** (77 → 129 files), **60 → 68 migrations**, **4 → 8 ADRs** (ADR-006 now Accepted; ADR-007 academic calendar + ADR-008 delivery calibration added; ADR-005 still Proposed), RLS **7 → 21 tenant tables**. Headlines: **server-side quiz grading** (a breaking change closing a client-trust hole), a **live-stack `quiz_suite`** built after a P0 escape (#524 — a prod-dead "Submit" button every mocked layer had stubbed past), the **independent-teacher subscription tier shipped as a product** (Solo/Growth/Pro + Stripe + `/teacher/subscription`), a portal-wide warm-neutrals + a11y-contrast pass (#189), and **Epic 18** (corporate-compliance scenarios, gated `/jt` demo — the advisor's no-fork Path A; Epic 17 fork stays CONTESTED). **Both prior P2s are still open** (`purge_account.py` comment-only gate; onboarding-wizard/Administration-menu E2E gap), and **Epic 2's production-hosting blocker is unresolved** — the app has never run outside local Docker, now the largest maturity-vs-deployability gap.
- **Mentible → critique v2.1.** Re-measured on `main` @ `e13f10b` (v0.2.63, 1,126 commits since `40166ee`): production LOC **~13,118 → ~61,425**, backend `def test_` **96 → 929** (sync+async; mobile test blocks 132 → 1,649), ADRs **13 → 42**. Headline: **ADR-037 SME expert-validation Studio built end-to-end** (capture→validate→share, per-topic approve/withdraw, publish→Library EPUB/PDF/DOCX, Playfair re-skin, 10 palettes). The v2.5 **`wegofwd-llm` pin lag closed** (exact v0.2.0). **Two prior wins regressed or half-landed:** doc-drift **reopened** — `docs/STATUS.md` (the doc CLAUDE.md names canonical) is 717 commits stale and never mentions ADR-037; and the job-runner is **half-migrated** (Celery for the new trust path, legacy routers still in-process). ADR-037's own file still reads `Status: Proposed` despite shipping (recurring ADR-status-vs-reality pattern). **ADR-039 (Accepted)** pivots monetization to services-led (Discovery/Sprint/Pilot).
- **New products not yet in the suite.** **agastya** (cybersecurity FastAPI, 108+ tests, own repo), **wegofwd-expenses** (email→ledger pipeline), **local_watch** (read-only fleet monitor, live on 3 machines), and **timesheet** (testers time & payments, a Django app inside wegofwd-hub) all now exist. First-reviews are pending — flagged for a future cycle.
- **README housekeeping.** Prose references to in-repo docs are now proper links; the `*-cost.md` note clarifies those analyses are held privately in `wegofwd-private-docs`.
- **Companion docs not yet regenerated.** This cycle refreshes the README summaries + this section against verified `origin/main` numbers; the deeper four-lens docs (`studybuddy-critique.md`, `mentible-critique.md`, dev-pattern, practices) for the two re-measured products are a v3.0 follow-up.
- **Other projects unchanged this cycle.** Thittam, dronePrjs, MarketingTools, medtracker, atri-sangam, claude_memory, wegofwd-llm, and wegofwd-video carry forward at their prior HEADs.

---

## What Changed in v2.9 (2026-07-18)

This cycle admits **atri-sangam** to the critique suite — a fixed-site GPS/PNT integrity monitor, and the portfolio's first venture into GNSS/PNT-security as a domain. It is also the **first product reviewed under the new public/private documentation split**: the critique, development-pattern, and practices are public here; the cost analysis is held in the private `wegofwd-private-docs` repo (its per-engineer rate assumptions are internal), with only the headline multiplier surfaced in the Quick Summary above.

- **New: atri-sangam — full four-lens first review (v1.0).** 1,961 source LOC / 719 test LOC, 66 tests at 90 % coverage, 6 OpenSpec contracts, CI on Python 3.10 + 3.12, `v0.1.0` Alpha, MIT. Reviewed from a source snapshot (**no git history** — so the development-pattern and cost passes analyze code-on-disk methodology and complexity, not a commit arc). Three public docs: [critique](atri-sangam-critique.md), [development-pattern](atri-sangam-development-pattern.md), [practices](atri-sangam-practices.md). **Strengths:** stdlib-only air-gap-ready core, everything-injectable determinism, three detector layers (step/CUSUM/staleness) mapped to three attack shapes, specs-as-contracts with decimal-exact scenarios mirrored by hand-derived tests, and a deterministic red-team simulator that triples as mock data + demo + threat generator. **Headline gaps:** the **SNTP reference channel has no anti-spoofing origin/replay validation** (the channel meant to catch spoofing is itself off-path-spoofable — Priority Action #1), and there is **no runner/daemon** — the artifact is a well-tested detection *library* + simulator, not a deployable monitor (Priority Action #2); plus unvalidated NMEA lat/lon, a dashboard that collapses the engine's STALE/ALARM model, and no ruff/mypy gate. Cost: ~**$128k US / $44k blended** conventional specialist build vs **~$8.8k all-in** actual — ~15× cheaper US / ~5× blended, ~850× cash-only (specialist-infra multiplier; runner/hardware excluded).
- **Other projects unchanged this cycle.** StudyBuddy_OnDemand, Mentible, Thittam, dronePrjs, MarketingTools, medtracker, claude_memory, wegofwd-llm, and wegofwd-video are all carried forward at their prior HEADs.

---

## What Changed in v2.7 (2026-07-01)

This cycle admits **wegofwd-video** to the critique suite as the **second cross-cutting shared dependency** in the set — the same architectural move as `wegofwd-llm`, one domain over (video instead of text). Built in a single evening by reusing the `wegofwd-llm` registry/provenance/error pattern, it is already load-bearing for two products on two different provider paths, which is the case for top-level watch.

- **New: wegofwd-video — full four-lens first review (v1.0).** A 741-LOC (+362 test) Python video-generation seam; v1.0.0 at HEAD `233f248` (4 commits, all 2026-06-30). Created **standalone** per ADR-026 **D7** — a *conscious exception* to ADR-019's "extract on the 2nd consumer" rule: the contract was validated against both consumers (pramana + Kathai Chithiram) as worked examples *before* any package code, then frozen at v1.0 only once both real integrations were wired green (the demand-driven `>=3.10` bump for the kathai consumer proves the loop was live). Four new docs: [critique](wegofwd-video-critique.md), [development-pattern](wegofwd-video-development-pattern.md), [practices](wegofwd-video-practices.md). Strengths: zero-dependency core, the two key-leak regression tests `wegofwd-llm` lacked, a caller-supplied deterministic-renderer that keeps heavy/product code in the consumer, capability pre-check, provenance+seed reproducibility, and the up-front-extract discipline gated on two green consumers. Gaps (pre-1.0 / shared-infra governance): a **provenance-integrity bug** (`veo` ships `model_verified=True` though it has never made a live call), **`runway`/`kling` dead-on-arrival** (registered but `build_provider()` always raises), deferred Ingredients-to-Video, **no in-repo CI or watch**, consumers pinned at `v0.1.2` while frozen at `v1.0.0`, and `Proprietary` license on a shared repo. Cost: ~**$42k US / $14k blended** conventional vs **~$2.4k all-in / 1–2 founder-days** actual — ~17× cheaper US / ~40× faster (the large time multiplier is the derivative discount from cloning the `wegofwd-llm` pattern).
- **Diagrams + catalog updated.** `shared_library.drawio` gains the `wegofwd-video` hub (solid edges to pramana & Kathai, dashed/planned to Mentible); the `apps_features*.drawio` footers and [`PRODUCT_CATALOG.md`](PRODUCT_CATALOG.md) note the video seam. This followed the **`StudyBuddy_SelfLearner` → `Mentible`** rename applied across the docs and diagrams the same day.
- **Other projects unchanged this cycle.** StudyBuddy_OnDemand, Mentible, Thittam, dronePrjs, MarketingTools, claude_memory, and wegofwd-llm are all carried forward at their v2.6 HEADs.

---

## What Changed in v2.6 (2026-06-13)

This cycle admits **wegofwd-llm** to the critique suite as the **first cross-cutting shared dependency** in the set. Until now every tracked project was a product or piece of internal tooling; `wegofwd-llm` is neither — it is library infrastructure consumed by three other tracked projects, and a regression in it cascades. That asymmetry is the case for top-level watch.

- **New: wegofwd-llm — full four-lens first review (v1.0).** A 778-LOC Python library extracted from Mentible per ADR-012 and re-injected into StudyBuddy_OnDemand via PRs #430/#431 (anthropic+openai) and #431 (Gemini consolidation). 3 commits / 48 tests / 9 providers / CI present / zero TODO. Four new docs: [critique](wegofwd-llm-critique.md), [development-pattern](wegofwd-llm-development-pattern.md), [practices](wegofwd-llm-practices.md). Strengths concentrate in design discipline (BYOK enforcement, key-leak prevention via `raise ... from None`, three-axis versioning stamped into `provenance()`, schema-agnostic conformance, the *extract-then-use* timing pattern). Gaps concentrate in pre-1.0 polish (4 UNVERIFIED providers, gemma dead-on-arrival, no key-leak regression test, no PyPI release, `Proprietary` license on a public repo, no in-package retry policy). Cost: ~**$48k US / $16k blended** for a conventional team vs **~$5.6k all-in / 3–4 founder-days** actual — ~8.5× cheaper US / 9.5× faster (smaller multiplier than products because specialist infra compresses less).
- **New: wegofwd-llm watch wired in the watched repo.** `.github/workflows/watch.yml` in `wegofwd-llm` runs weekly (Mondays 09:00 UTC), on every push to `main`, and on manual `workflow_dispatch`. It compares HEAD against `wegofwd-llm-last-reviewed.txt` in this repo and opens a PR here with a dated `wegofwd-llm-watch-YYYY-MM-DD.md` when anything has changed. Quiet weeks produce no PR. Security-hardened: attacker-influenced values (commit subjects, diffstat) flow via `env:` not `${{ }}` interpolation; commit messages and PR bodies use `git commit -F` / `gh pr create --body-file`. **One-time setup required** — see `wegofwd-llm/.watch/README.md` for the PAT instructions.
- **Founder docs reconciliation done.** [elevator-pitch.md](elevator-pitch.md) → v1.2 (anchored on Thittam + StudyBuddy + the shared seam as architectural credential; "past year"→"since 2025"; 17/18→21 rule count with continuity note; cost-evidence numbers added). [linkedin-posts.md](linkedin-posts.md) → v1.2 (same fixes + the **Thittam `audit_log` REVOKE marketing claim corrected** — the prior wording said "UPDATE and DELETE are revoked, not just discouraged", which is factually false per the v2.3 critique; replaced with the honest *"the migration ships with the REVOKE staged for a post-deploy step after role creation"*). [personality-review.md](personality-review.md) → v1.2 (refresh adds §2.4 *Extract-Then-Use Pattern* with wegofwd-llm as the cleanest example; §3.1 second cycle of closure observed; scorecard refreshed; new *Reusable IP extraction* row).
- **Other projects unchanged this cycle.** StudyBuddy_OnDemand, Mentible, Thittam, dronePrjs, MarketingTools, claude_memory all re-checked at the same HEADs as v2.5 (StudyBuddy moved to a different branch since v1.7 but no code change relevant to this cycle). Their entries are carried forward.

---

## Planned — v2.8 (follow-ups)

- **✅ Shared-library watches — both wired and verified (done 2026-07-01).** `wegofwd-video` got an in-repo `ci.yml` (ruff + pytest, green) and a `watch.yml` mirroring `wegofwd-llm`. The `PROJECT_CRITIQUE_PR_TOKEN` secret is set on **both** `wegofwd-llm` and `wegofwd-video`, both `watch` runs are **verified green**, and both baselines were reset to current HEAD (`wegofwd-llm` `3b08f442`, `wegofwd-video` `837dfb5`) so quiet weeks produce no PR. Token setup is documented in `NEW_MACHINE_SETUP.md` ("Shared-library watch tokens"), and each library's `.watch/README.md`.
- **Kathai Chithiram — full four-lens first review (deferred from v2.6).** The project (Tamil: கதை சித்திரம், "story → picture"; renamed from `behavioral_practices`) turns a parent's written story into an animation a special-needs child can understand, using the shared **`wegofwd-llm`** generation seam. As of 2026-06-09 it is two prototype renderers (`generate_animation.py`, `blender_animation.py`) + the hand-built "Silas Shines His Smile" social story — a proof-of-concept, not yet a system: the scene-script schema, the generation step, and parent intake are still roadmap. **Add the four-lens set once the generation→scene-script→renderer contract lands** (there is little to critique architecturally until then). Repo: `wegofwd2020-hub/kathai-chithiram`.
- **Pramana — full four-lens first review (deferred).** Currently spec + early data model only; review when the v1 service surface lands and the named tenant pilot is in motion.
- **Founder-doc *positioning* pass.** This cycle reconciled facts (numbers, dates, the audit-trail claim) and added the seam credential. A future pass may reconsider the *anchor* itself if the strategic fork resolves toward selling the engine vs an application.

---

## What Changed in v2.5 (2026-06-09)

This cycle re-ran the critique against the **code on disk** for the two projects that moved, and added **two new four-lens projects**.

- **StudyBuddy OnDemand → critique v1.7 / dev-pattern v1.6 / practices v1.7 / cost v1.2.** Re-measured on `main` @ `d50bc3e` (26 commits since `0d7abe1`): **1,081 → 1,085** backend tests (78 → 77 files), migrations unchanged at 60, ADRs 2 → **4** (ADR-005 school_admin superset role *Proposed*; ADR-006 multi-provider LLM retro-formalized). The window is school-ops enablement: onboarding wizard (#420), Administration menu (#415/#417), a real backup restore-path data-loss fix (#411, +297 test LOC) + PII-leak fix (#413), classroom curriculum picker (#418), branding. New P2s: the wizard/menu are web-unit-tested only (no E2E), and `purge_account.py` is "test only" by comment, not by an env assertion.
- **Mentible → all four docs v2.0** (major refresh, not an increment). Re-measured on `main` @ `40166ee` (97 commits since `e1c66f7`): **131 → 228** commits, **6 → 13** ADRs, ~13,118 in-repo production LOC. The headline is the **extraction of the LLM provider seam into the installable `wegofwd-llm` package (ADR-012)** (773 LOC / 48 tests) and multi-provider BYOK. The **BYOK 422-leak is confirmed closed**. Honest correction surfaced during review: ADR-012 frames the package as serving the family, but Mentible is currently its *only* on-disk consumer (Pramana imports nothing from it; the link is an HTTP artifact port) — so it's forward-looking DRY with payoff pending, and the pin already lags (`v0.1.0` vs package `v0.1.1`).
- **New: MarketingTools — full four-lens first review (v1.0).** A ~2.3k-LOC scoped-retrieval marketing toolkit (`main` @ `76addee`). Strong design/docs, **zero tests** (🔴), and an incomplete `requirements.txt` that breaks deck builds from a clean clone.
- **New: claude_memory tooling — full four-lens first review (v1.0).** The git-backed portable per-project memory system (10 private repos + a global Stop hook + two runbooks). Durable and well-documented, with two real gaps: **silent hook failure** (already bit `pramana`) and an **unredacted/unencrypted, one-token blast-radius** privacy posture. The two runbooks (`NEW_MACHINE_SETUP.md`, `claude-memory-add-project.md`) are now indexed here.
- **Thittam and dronePrjs unchanged this cycle** — re-checked on disk 2026-06-09; HEADs are identical to their v2.3 measurements (Thittam `3883769`, dronePrjs `5e38a44`). Their entries above are carried forward.

---

## What Changed in v2.4 (2026-06-02)

This cycle adds a **fourth project** and refreshes StudyBuddy OnDemand, both measured against the **code on disk**.

- **New: Mentible — full four-lens first review (v1.0).** A pre-deploy MVP (branch `feat/authoring-regenerate-export-fixes` @ `e1c66f7`): a BYOK, adults-only, direct-to-learner authoring app that compiles generated content into EPUB3/PDF books. Four new docs: [critique](mentible-critique.md), [development-pattern](mentible-development-pattern.md), [practices](mentible-practices.md). Headlines: exemplary BYOK security (HKDF-per-job AES-GCM envelope, TTL+shred, CI key-leak gate), a complete standalone EPUB3/PDF compiler, ADR-driven re-scoping into two products + a rebrand to **Mentible** — but **not yet deployed or run against live Anthropic**, and the job runner is an in-process `BackgroundTask`, not the planned Celery worker.
- **StudyBuddy OnDemand → critique v1.6 / dev-pattern v1.5 / practices v1.6 / cost v1.1.** Re-measured on `main` @ `0d7abe1`: **1,030 → 1,081** backend tests (73 → 78 files), **59 → 60** migrations (latest 0060, `curriculum_authoring_studio`), 17 Playwright specs / 2,779 LOC. The headline addition is the **Curriculum Authoring Studio (Epic 12, super-admin)** — interactive TOC-structure → generate → review/regenerate → snapshot → publish with a publish-completeness gate (#401/#402) — plus **book-export (#400)**, a one-way content bridge into Mentible. **ADR-004** decides the standalone author-your-own-book product belongs to the Mentible repo, not OnDemand; OnDemand's own ADR-002/ADR-003 were closed without merge. Zero TODO/FIXME holds. Epic 17 remains CONTESTED.
- **Thittam and dronePrjs unchanged this cycle** — refer to their v2.3 entries below.

---

## What Changed in v2.3 (2026-05-24)

This cycle re-measured all three projects against the **code on disk** (prior cycles inferred Thittam largely from docs). It is mostly verification + a numbers refresh; the architectural reads from v2.2 hold.

- **StudyBuddy → critique v1.5.** No architecture change. Re-measured: 914 → **1,030** backend tests (73 files), 48 → **59** migrations (latest 0059), 16 → **17** Playwright specs. New `teacher_capabilities` capability (#358, migration 0059). Two speculative **corporate-L&D epics (17/18)** surfaced — Epic 17 marked CONTESTED. The window since was launch/demo hardening (incl. domain rename to `usestudybuddy.com`). Zero TODO/FIXME holds. Backlog correction: Epic 10 L-7/L-8 are shipped per current CLAUDE.md (v1.4 had listed them open).
- **Thittam → critique v1.3.** Verified against real code for the first time. **Three v1.2-flagged gaps are now implemented:** registration saga (`pkg/registration/saga.go`, 497 LOC), reporting read-model (`ProjectionConsumer`), impersonation lifecycle (4h cap). Schema-injection + T1 fixes confirmed real in source. Numbers: 1,150 → **1,203** tests, 1,659 → **1,715** proto LOC. The `audit_log` REVOKE remains the one open P0. The "71 docs / 13 ADRs" claim is **unverifiable** here (docs live in the un-checked-out `thittam_docs` repo).
- **dronePrjs → critique v1.1.** Surpassed the reviewed commit (6 → **8** commits, HEAD `5e38a44`). **CI now exists** (Phase 6), **ISC-28 map-signature check done**, **D1/D2 ratified**. Still open: ISC-15 link-loss RTH, openSpace stub. Numbers: 100 → ~**133** tests, coverage 97 % → **95.3 %**, source LOC corrected to **3,548** (the v1.0 ~5,010 over-counted tests), 29 → **35** of 44 ISCs.

---

## What Changed in v2.2 (May 2026)

- **Added dronePrjs** as a third project under critical analysis, with the full three-lens treatment: `dronePrjs-critique.md`, `dronePrjs-development-pattern.md`, `dronePrjs-practices.md`.
- **Thittam docs refreshed to v1.2** — all three lenses (critique, development pattern, practices) updated to reflect proto completion (all 10 protos / 1,659 LOC / 230 messages), T1 secret handling via Vault → memory, `pkg/tenantdb` schema-injection fix, test growth 306 → 1,150, shadcn/ui web tier adoption, and XYZ Construction Phase A demo.
- StudyBuddy content unchanged from v2.1.

---

## What Changed in v2.1 (May 2026)

| Project | v2 (April 2026 refresh) | v2.1 (May 2026 refresh) |
|---|---|---|
| StudyBuddy — Visual library (dev DB) | 0 entries (promotion CI gated on AWS secrets) | 144 entries with embeddings via `seed_library_local.py` |
| StudyBuddy — Resolver eval records | Empty harness | 80 records (eval-001..080) |
| StudyBuddy — Remotion clips | 0 | 9 (Option-3 video catalogue) |
| StudyBuddy — Issues closed in window | n/a | 13 — #327–#336, #295, #297, #338, #339 |
| StudyBuddy — `/curriculum/{grade}` | STEM-only fallback | Stream-aware 3-step resolver (auth-optional) |
| StudyBuddy — Operator dance for library seeding | `docker cp scripts/* celery-pipeline:/tmp/seed/` | Bind mounts permanent (#339) |
| StudyBuddy — Resolver eval crash on rate-limit | KeyError | Schema-mirroring error branch + `n_errored` |
| StudyBuddy — Backend tests | 835 | ~914 |
| StudyBuddy — PAI 5.0 integration | Active in `~/.claude/` | Removed in full; settings.json 52,688 → 1,908 bytes |
| Thittam | (April refresh content) | Unchanged in this cycle — refer to v2 entries below |

---

## What Changed in v2 (April 2026)

| Project | v1 (earlier April 2026) | v2 (April 2026 refresh) |
|---|---|---|
| StudyBuddy — Epics | Phases 1–11 complete | Epic 1, Epic 8, Epic 10 L-1..L-5, Epic 11 C-1..C-4, C-6, C-9 delivered |
| StudyBuddy — Tests | 215+ backend | 835 backend + 2,620 LOC Playwright |
| StudyBuddy — Migrations | ≤45 | 48 (0046–0048 ship Epic 10 governance + hotfix) |
| StudyBuddy — Content | Single rendering; ad-hoc prompts | Shared `SBMarkdown` + universal/per-subject prompt guidelines + format-drift validator |
| Thittam — Protos | 4 of 9 pending | 10 of 10 defined |
| Thittam — Tests | ~306 across 22 pkgs | 1,150 across 80 files |
| Thittam — T1 secrets | ❌ Env-var contradiction | ✅ Vault → memory (cmd/iam/main.go) |
| Thittam — Schema injection | ❌ Critical | ✅ Fixed (pkg/tenantdb UUID type) |
| Thittam — Web tier | Theme unclear | shadcn/ui + Radix + Tailwind v4 + Rule #18 typography |
| Thittam — Demos | XYZ_CBA only | XYZ_CBA (INR, movie) + XYZ Construction Phase A (USD, construction) |
| Thittam — IAM | bare gRPC | grpc-gateway REST shadow (`/api/v1/auth/*`) + CORS + `/me` |

---

## How This Repository Is Organised

- **`*-critique.md`** — point-in-time code review with priority-ordered actions.
- **`*-development-pattern.md`** — how the project was scoped, designed, architected, and developed. Less about bugs, more about method.
- **`*-practices.md`** — catalogue of good + bad practices with concrete fixes.
- **`*-cost.md`** — real-world cost analysis: what a conventional team would have spent in money and calendar time to reach the same artifact, triangulated three ways (industry-velocity benchmark, COCOMO-II modernized, feature-counting). Triangulated against the actual cash + founder-opportunity-cost outlay to produce defensible cheaper-and-faster multipliers. **Held privately in `wegofwd-private-docs`, not in this public repo** (per-engineer rate assumptions are internal); only headline multipliers are surfaced in the Quick Summary above.
- **[`NEW_MACHINE_SETUP.md`](NEW_MACHINE_SETUP.md) / [`claude-memory-add-project.md`](claude-memory-add-project.md)** — operational runbooks for the claude_memory tooling (restore on a fresh machine; add + verify a new project).
- **[`elevator-pitch.md`](elevator-pitch.md) / [`personality-review.md`](personality-review.md) / [`linkedin-posts.md`](linkedin-posts.md)** — founder-facing material derived from the technical review.

---

*This critique is a point-in-time review. The **2026-07-01 (v2.7)** cycle admits **wegofwd-video** to the critique suite as the second cross-cutting shared dependency — a full four-lens first review based on the source at HEAD `233f248` (v1.0.0, 4 commits 2026-06-30), read directly on disk; tests were not re-run live this pass (30 tests present, all mocked, no live Veo call exists to run) and the two consumer integrations (pramana, kathai-chithiram) are taken from ADR-026's 2026-06-30 amendment, not separately re-confirmed against those repos. The same cycle applied the **`StudyBuddy_SelfLearner` → `Mentible`** rename across the docs and diagrams. The **2026-06-13 (v2.6)** cycle admits **wegofwd-llm** to the watch set as the first cross-cutting shared dependency tracked here — first-review based on the source at HEAD `4823606` (`/tmp/wegofwd-llm` clone), CI workflow existence checked but tests not re-run live this pass. Three companion lenses (dev-pattern, practices, cost) and the watch mechanism itself are deferred to v2.7 pending operator decision on cadence/mechanism. The **2026-06-09 (v2.5)** cycle re-measured StudyBuddy OnDemand (`main` @ `d50bc3e`) and Mentible (`main` @ `40166ee`) directly against the code on disk, and added first-review four-lens sets for MarketingTools (`main` @ `76addee`) and the claude_memory tooling (10 private memory repos + Stop hook + runbooks, inspected live). Thittam and dronePrjs were re-checked and are byte-identical to their v2.3 measurements (HEADs `3883769` and `5e38a44`); their entries are carried forward unchanged. As before, Thittam's "71 docs / 13 ADRs" count lives in the sibling `thittam_docs` repo (not checked out here) and remains unverified. Where a test suite could not be executed in the review environment (e.g. `pytest` absent for Mentible), claims rest on reading the handlers/tests and are noted as such in the relevant doc.*
