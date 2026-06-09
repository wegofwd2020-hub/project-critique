# Project Critique — WeGoFwd2020

Code review and architectural critique for StudyBuddy OnDemand, StudyBuddy SelfLearner (Mentible), Thittam, dronePrjs, MarketingTools, and the claude_memory tooling.

**Reviewed:** 2026-06-09 (v2.5 — **StudyBuddy OnDemand re-measured + refreshed (critique v1.7)** on `main` @ `d50bc3e` (school onboarding wizard, Administration menu, ADR-005/006, backup hardening); **SelfLearner / Mentible major refresh (v2.0)** on `main` @ `40166ee` (97 commits: LLM provider seam extracted into the `wegofwd-llm` package, Pramana integration, BYOK 422-scrub fix); **two new four-lens projects: MarketingTools (v1.0)** and **claude_memory tooling (v1.0)**; Thittam + dronePrjs re-checked, code unchanged since v2.3/v2.4)
**Prior:** 2026-06-02 v2.4 (StudyBuddy OnDemand → critique v1.6 Authoring Studio/Epic 12; new project SelfLearner/Mentible v1.0) · May 2026 v2.3 (all three re-measured on disk: StudyBuddy v1.5, Thittam v1.3, dronePrjs v1.1) · v2.2 (adds dronePrjs first-review; StudyBuddy v1.4; Thittam v1.2) · v2.1 (StudyBuddy visual-library wave 1+2) · April 2026 v2 (proto completion, Epic 10/11 delivery, T1 secret fix, schema injection fix, multi-tenant demo expansion)
**Reviewer:** Claude (Anthropic)
**Scope:** Architecture, code quality, test coverage, documentation, security, scalability

---

## Contents

| File | Project | Description |
|---|---|---|
| [studybuddy-critique.md](studybuddy-critique.md) | StudyBuddy OnDemand | Code review — architecture, quality, security, scalability |
| [studybuddy-selflearner-critique.md](studybuddy-selflearner-critique.md) | StudyBuddy SelfLearner (Mentible) | Code review — architecture, quality, **BYOK security**, ops |
| [thittam-critique.md](thittam-critique.md) | Thittam | Code review — architecture, quality, security, scalability |
| [dronePrjs-critique.md](dronePrjs-critique.md) | dronePrjs (closedSpace + openSpace) | Code review — architecture, quality, safety, sim-only fidelity caveats |
| [MarketingTools-critique.md](MarketingTools-critique.md) | MarketingTools | Code review — scoped-retrieval marketing toolkit; zero-test gap, reproducibility |
| [claude-memory-critique.md](claude-memory-critique.md) | claude_memory (tooling) | System-design critique — robustness, privacy, portability, observability |
| [studybuddy-development-pattern.md](studybuddy-development-pattern.md) | StudyBuddy OnDemand | Full lifecycle analysis — scoping, design, architecture, development |
| [studybuddy-selflearner-development-pattern.md](studybuddy-selflearner-development-pattern.md) | StudyBuddy SelfLearner (Mentible) | Lifecycle analysis — subtractive scoping, ADR-driven re-scoping, security-first design |
| [thittam-development-pattern.md](thittam-development-pattern.md) | Thittam | Full lifecycle analysis — scoping, design, architecture, development |
| [dronePrjs-development-pattern.md](dronePrjs-development-pattern.md) | dronePrjs | Full lifecycle analysis — scoping by operating environment, ISA-as-SOR, phase-per-commit |
| [MarketingTools-development-pattern.md](MarketingTools-development-pattern.md) | MarketingTools | Lifecycle analysis — one-source-of-truth asset model, deterministic deck builders |
| [claude-memory-development-pattern.md](claude-memory-development-pattern.md) | claude_memory (tooling) | How the portable-memory system was designed and grew to 10 repos |
| [studybuddy-practices.md](studybuddy-practices.md) | StudyBuddy OnDemand | Good practices, bad practices, and how to improve |
| [studybuddy-selflearner-practices.md](studybuddy-selflearner-practices.md) | StudyBuddy SelfLearner (Mentible) | Good practices, bad practices, and how to improve |
| [thittam-practices.md](thittam-practices.md) | Thittam | Good practices, bad practices, and how to improve |
| [dronePrjs-practices.md](dronePrjs-practices.md) | dronePrjs | Good practices, bad practices, and how to improve |
| [MarketingTools-practices.md](MarketingTools-practices.md) | MarketingTools | Good practices, bad practices, and how to improve |
| [claude-memory-practices.md](claude-memory-practices.md) | claude_memory (tooling) | Good practices (durability, no-op-safe hook), risks (silent failure, secrets-in-memory) |
| [studybuddy-cost.md](studybuddy-cost.md) | StudyBuddy OnDemand | Real-world cost analysis — conventional team would have spent (~$1.54M US / $510k blended) |
| [studybuddy-selflearner-cost.md](studybuddy-selflearner-cost.md) | StudyBuddy SelfLearner (Mentible) | Real-world cost analysis — conventional team would have spent (~$524k US / $179k blended) |
| [thittam-cost.md](thittam-cost.md) | Thittam | Real-world cost analysis — conventional team would have spent (~$2.2M US / $711k blended) |
| [dronePrjs-cost.md](dronePrjs-cost.md) | dronePrjs | Real-world cost analysis — conventional robotics team would have spent (~$522k US / $179k blended) |
| [MarketingTools-cost.md](MarketingTools-cost.md) | MarketingTools | Real-world cost analysis — conventional team would have spent (~$33k US / proportionate) |
| [claude-memory-cost.md](claude-memory-cost.md) | claude_memory (tooling) | Real-world cost analysis — ~4 senior infra/DX engineer-days (~$6–7k US) |
| [NEW_MACHINE_SETUP.md](NEW_MACHINE_SETUP.md) | claude_memory (tooling) | Runbook — restore the per-project memory system on a fresh machine (10 repos) |
| [claude-memory-add-project.md](claude-memory-add-project.md) | claude_memory (tooling) | Runbook — wire a new project into git-backed memory + verify the auto-push |
| [elevator-pitch.md](elevator-pitch.md) | Siva Mambakkam | Elevator pitch for employers and consulting clients |
| [personality-review.md](personality-review.md) | Siva Mambakkam | Practice personality review — strengths, blind spots, and improvement plan |
| [linkedin-posts.md](linkedin-posts.md) | Siva Mambakkam | Five LinkedIn posts — thought leadership, compliance, standards, availability |

---

## Quick Summary

### StudyBuddy OnDemand

**Overall:** Late-build / pre-production. All prior P0/P1 items remediated. **2026-06-09 (critique v1.7):** re-measured on `main` @ `d50bc3e` (26 commits since `0d7abe1`) — **1,085 backend tests / 77 files, 60 migrations (latest 0060, unchanged this window), 17 Playwright specs / 2,779 LOC, 65 web-unit files / 948 it·test blocks, 4 ADRs (ADR-005/006 added), zero TODO/FIXME**. The window is **school-ops enablement**: a guided "Set up your school" onboarding wizard (#420) whose checklist is computed purely from signals the portal already exposes, an "Administration" top-bar menu grouping school_admin tasks (#415/#417, explicitly *not* an authz boundary), a real backup restore-path data-loss fix (#411, +297 test LOC) with sibling key-column (#410) and PII-leak (#413) fixes, a classroom curriculum picker (#418), and banyan favicon/branding. **ADR-005** (school_admin superset role) is still *Proposed*; **ADR-006** is a healthy retro-ADR formalizing already-shipped Epic 1 multi-provider LLM. Epic 17 (corporate-L&D fork) remains CONTESTED.

| Area | Rating | Key Finding |
|---|---|---|
| Architecture | 🟢 Strong | StorageBackend abstraction, app factory, Epic 10 platform/school governance split, Streams soft-registry |
| Code Quality | 🟢 Strong | Zero TODO/FIXME holds; SBMarkdown consolidates rendering; backup fixes add real test depth |
| Test Coverage | 🟡 Good | 1,085 backend tests / 77 files + 17 Playwright specs (2,779 LOC) + 65 web-unit files; **onboarding wizard + Administration menu are web-unit only, no E2E** (new P2) |
| Documentation | 🟢 Strong | CLAUDE.md + curriculum_mgmt docs refreshed (#427); ADR-005/006 added; per-module coverage thresholds enforced |
| Security | 🟢 Strong | RLS extended, COPPA codified, JWKS TTL, Redis auth limiter; `purge_account.py` (#416) is test-only by *comment*, not an env assertion (new P2) |
| Scalability | 🟡 Good | S3/Local via StorageBackend, RedBeat resolves Beat SPOF; no load tests |

**Top 3 actions:** (1) Add E2E coverage for the onboarding wizard + Administration menu (currently web-unit only), (2) Gate `purge_account.py` behind a hard `APP_ENV` assertion rather than a "test only" comment, (3) Ship or close ADR-005 (still Proposed).

💰 **Real-world cost** — conventional ~4.5-FTE team (~46 EM) would have spent **~$1.54M (US) / $510k (blended)** to reach HEAD `d50bc3e`. Actual: **~$54–56k all-in / ~$2k cash, ~78 days, one founder.** Headline: **~28× cheaper US / ~9× blended, ~4–4.5× faster, 4.5× smaller team.** See [studybuddy-cost.md](studybuddy-cost.md).

---

### StudyBuddy SelfLearner (Mentible)

**Overall:** Pre-deploy MVP, but **architecturally matured** since the v1.0 first review. **2026-06-09 (critique v2.0):** re-measured on `main` @ `40166ee` (97 commits since `e1c66f7`) — **228 commits, 13 ADRs, ~1,953 backend src LOC / 96 `def test_`, compiler 2,223 LOC / 71 test blocks, mobile 7,696 LOC / 132 test blocks, ~13,118 in-repo production LOC** plus a new **external `wegofwd-llm` package (773 LOC / 48 tests)**. The headline shift is the **extraction of the LLM provider seam into the installable `wegofwd-llm` package (ADR-012)** — a typed contract + registry + validate→repair conformance loop, proven in-repo across 5 phases before packaging — and **multi-provider BYOK** with free providers (per-provider output-token clamping after Groq's 413). The **BYOK 422-leak is confirmed closed** (custom `RequestValidationError` handler + `scrub_validation_errors` + an asserting test). Still BYOK, adults-only, compiles to portable EPUB3/PDF.

| Area | Rating | Key Finding |
|---|---|---|
| Architecture | 🟢 Strong | Provider seam extracted into a typed, py.typed package; clean four-layer split; Pramana link is an HTTP artifact-exchange port (`NullMentibleClient` default) |
| Code Quality | 🟢 Strong | ruff/tsc clean; idempotency + retry budget; single brand constant; 48 package tests |
| Test Coverage | 🟡 Good | 96 backend `def test_` + 71 compiler + 132 mobile blocks; **still no live-Anthropic or on-device E2E** (the gate everything waits on) |
| Documentation | 🟡 Gap | 13 ADRs capture every pivot, but `CLAUDE.md` still says "Pre-MVP — directory stubs only, no application code yet" over ~13k LOC; `STATUS.md` ~140 commits stale |
| Security (BYOK) | 🟢 Strong | Pattern B done right + the **422-scrub leak fix confirmed closed** (loc-based + value-pattern redaction, asserting test) |
| Scalability / Ops | 🟡 Good | `wegofwd-llm` pinned `@v0.1.0` while package is at `v0.1.1`, via registry-less `git+https` built every CI run; job runner still in-process `BackgroundTask`, not Celery |

**Top 3 actions:** (1) Fix the lagging `wegofwd-llm` pin (`v0.1.0`→`v0.1.1`) and move off `git+https` to a resolvable registry, (2) Close the doc-drift *for real* — `CLAUDE.md`/`STATUS.md` still describe a pre-MVP stub, (3) Replace the in-process `BackgroundTask` with the planned worker and run one real BYOK E2E.

💰 **Real-world cost** — conventional ~3-FTE team (~16 EM, incl. an ebook + an LLM-platform specialist) would have spent **~$524k (US) / $179k (blended)**. Actual: **~$26k all-in / ~$1k cash, one founder. Zero Anthropic token cost — BYOK.** Headline: **~16× cheaper US / ~5.6× blended, ~4.3× faster.** The slight dip from v1.0 (17×→16×) is the informative result: the new scope (packaged seam, multi-provider verification, a security fix) is *more specialist*, where AI assistance compresses less. See [studybuddy-selflearner-cost.md](studybuddy-selflearner-cost.md).

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

💰 **Real-world cost** — conventional 5.5-FTE team would have spent **~$2.20M (US) / $711k (blended)** to reach HEAD `ce64378`. Actual: **~$36k all-in / ~$2k cash, 41 days, one founder.** Headline: **61× cheaper US / 20× blended, 7.5× faster.** See [thittam-cost.md](thittam-cost.md).

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

💰 **Real-world cost** — conventional 3.75-FTE robotics team would have spent **~$522k (US) / $179k (blended)** to reach HEAD `5e38a44`. Actual: **~$12k all-in / ~$0.2k cash, ~2 weeks, one founder.** Headline: **44× cheaper US / 15× blended, 8× faster.** *Hardware costs (Phase 8) excluded.* See [dronePrjs-cost.md](dronePrjs-cost.md).

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

💰 **Real-world cost** — conventional build ~1.3 EM → **~$33k (US)**. Actual: **~$4.4k all-in, ~8 days, one founder.** Headline: **~7.5× cheaper US / ~2.3× blended** (deliberately modest — proportionate to a 2.3k-LOC tool dominated by design/content work). See [MarketingTools-cost.md](MarketingTools-cost.md).

---

### claude_memory (tooling)

**Overall:** Small, durable, well-documented DX infrastructure (not an app): a git-backed durability layer for Claude Code's per-project memory. Each project's memory is its own git repo under `~/.claude/projects/<encoded-path>/memory/`, and a single global `Stop` hook in `~/.claude/settings.json` auto-commits and pushes it to a private `github.com/wegofwd2020-hub/<name>-memory` remote after every session. **10 memory repos, 10/10 private; hook present (async, 30 s, no-op-safe); runbooks `NEW_MACHINE_SETUP.md` (141 lines) + `claude-memory-add-project.md` (117 lines).**

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

💰 **Real-world cost** — a correct, documented, verified version is ~4 senior infra/DX engineer-days → **~$6–7k (US) / ~$1.8k (blended)**. Actual: ~1–2 interstitial founder-days, **~$1.7k all-in, ~$0 direct cash** (free private repos, no compute). Headline: large cash-only ratio, modest all-in multiplier (~1–4×) — the expected result for small, judgment-heavy infra. See [claude-memory-cost.md](claude-memory-cost.md).

---

## What Changed in v2.5 (2026-06-09)

This cycle re-ran the critique against the **code on disk** for the two projects that moved, and added **two new four-lens projects**.

- **StudyBuddy OnDemand → critique v1.7 / dev-pattern v1.6 / practices v1.7 / cost v1.2.** Re-measured on `main` @ `d50bc3e` (26 commits since `0d7abe1`): **1,081 → 1,085** backend tests (78 → 77 files), migrations unchanged at 60, ADRs 2 → **4** (ADR-005 school_admin superset role *Proposed*; ADR-006 multi-provider LLM retro-formalized). The window is school-ops enablement: onboarding wizard (#420), Administration menu (#415/#417), a real backup restore-path data-loss fix (#411, +297 test LOC) + PII-leak fix (#413), classroom curriculum picker (#418), branding. New P2s: the wizard/menu are web-unit-tested only (no E2E), and `purge_account.py` is "test only" by comment, not by an env assertion.
- **SelfLearner / Mentible → all four docs v2.0** (major refresh, not an increment). Re-measured on `main` @ `40166ee` (97 commits since `e1c66f7`): **131 → 228** commits, **6 → 13** ADRs, ~13,118 in-repo production LOC. The headline is the **extraction of the LLM provider seam into the installable `wegofwd-llm` package (ADR-012)** (773 LOC / 48 tests) and multi-provider BYOK. The **BYOK 422-leak is confirmed closed**. Honest correction surfaced during review: ADR-012 frames the package as serving the family, but Mentible is currently its *only* on-disk consumer (Pramana imports nothing from it; the link is an HTTP artifact port) — so it's forward-looking DRY with payoff pending, and the pin already lags (`v0.1.0` vs package `v0.1.1`).
- **New: MarketingTools — full four-lens first review (v1.0).** A ~2.3k-LOC scoped-retrieval marketing toolkit (`main` @ `76addee`). Strong design/docs, **zero tests** (🔴), and an incomplete `requirements.txt` that breaks deck builds from a clean clone.
- **New: claude_memory tooling — full four-lens first review (v1.0).** The git-backed portable per-project memory system (10 private repos + a global Stop hook + two runbooks). Durable and well-documented, with two real gaps: **silent hook failure** (already bit `pramana`) and an **unredacted/unencrypted, one-token blast-radius** privacy posture. The two runbooks (`NEW_MACHINE_SETUP.md`, `claude-memory-add-project.md`) are now indexed here.
- **Thittam and dronePrjs unchanged this cycle** — re-checked on disk 2026-06-09; HEADs are identical to their v2.3 measurements (Thittam `3883769`, dronePrjs `5e38a44`). Their entries above are carried forward.

---

## What Changed in v2.4 (2026-06-02)

This cycle adds a **fourth project** and refreshes StudyBuddy OnDemand, both measured against the **code on disk**.

- **New: StudyBuddy SelfLearner / Mentible — full four-lens first review (v1.0).** A pre-deploy MVP (branch `feat/authoring-regenerate-export-fixes` @ `e1c66f7`): a BYOK, adults-only, direct-to-learner authoring app that compiles generated content into EPUB3/PDF books. Four new docs: [critique](studybuddy-selflearner-critique.md), [development-pattern](studybuddy-selflearner-development-pattern.md), [practices](studybuddy-selflearner-practices.md), [cost](studybuddy-selflearner-cost.md). Headlines: exemplary BYOK security (HKDF-per-job AES-GCM envelope, TTL+shred, CI key-leak gate), a complete standalone EPUB3/PDF compiler, ADR-driven re-scoping into two products + a rebrand to **Mentible** — but **not yet deployed or run against live Anthropic**, and the job runner is an in-process `BackgroundTask`, not the planned Celery worker.
- **StudyBuddy OnDemand → critique v1.6 / dev-pattern v1.5 / practices v1.6 / cost v1.1.** Re-measured on `main` @ `0d7abe1`: **1,030 → 1,081** backend tests (73 → 78 files), **59 → 60** migrations (latest 0060, `curriculum_authoring_studio`), 17 Playwright specs / 2,779 LOC. The headline addition is the **Curriculum Authoring Studio (Epic 12, super-admin)** — interactive TOC-structure → generate → review/regenerate → snapshot → publish with a publish-completeness gate (#401/#402) — plus **book-export (#400)**, a one-way content bridge into Mentible. **ADR-004** decides the standalone author-your-own-book product belongs to the SelfLearner repo, not OnDemand; OnDemand's own ADR-002/ADR-003 were closed without merge. Zero TODO/FIXME holds. Epic 17 remains CONTESTED.
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
- **`*-cost.md`** — real-world cost analysis: what a conventional team would have spent in money and calendar time to reach the same artifact, triangulated three ways (industry-velocity benchmark, COCOMO-II modernized, feature-counting). Triangulated against the actual cash + founder-opportunity-cost outlay to produce defensible cheaper-and-faster multipliers.
- **`NEW_MACHINE_SETUP.md` / `claude-memory-add-project.md`** — operational runbooks for the claude_memory tooling (restore on a fresh machine; add + verify a new project).
- **`elevator-pitch.md` / `personality-review.md` / `linkedin-posts.md`** — founder-facing material derived from the technical review.

---

*This critique is a point-in-time review. The **2026-06-09 (v2.5)** cycle re-measured StudyBuddy OnDemand (`main` @ `d50bc3e`) and SelfLearner/Mentible (`main` @ `40166ee`) directly against the code on disk, and added first-review four-lens sets for MarketingTools (`main` @ `76addee`) and the claude_memory tooling (10 private memory repos + Stop hook + runbooks, inspected live). Thittam and dronePrjs were re-checked and are byte-identical to their v2.3 measurements (HEADs `3883769` and `5e38a44`); their entries are carried forward unchanged. As before, Thittam's "71 docs / 13 ADRs" count lives in the sibling `thittam_docs` repo (not checked out here) and remains unverified. Where a test suite could not be executed in the review environment (e.g. `pytest` absent for SelfLearner), claims rest on reading the handlers/tests and are noted as such in the relevant doc.*
