# WeGoFwd2020 — Product Catalog

**Owner:** WeGoFwd2020 (`github.com/wegofwd2020-hub`)
**Generated:** 2026-06-11 · **Last updated:** 2026-07-14 (added `medtracker`)
**Scope:** All 19 code repositories in the GitHub organization, cloned and synced into this
folder. (The 13 `*-memory` repos — portable Claude memory, one per project — are excluded;
see `claude-memory-add-project.md`.)

This catalog is auto-derived from each repository's README, `CLAUDE.md`, and design
docs. Status reflects what the repos themselves claim as of their latest synced commit.

---

## Portfolio at a glance

| # | Product | Repo | Category | Primary stack | Status |
|---|---|---|---|---|---|
| 1 | **StudyBuddy OnDemand** | `StudyBuddy_OnDemand` | Education (B2B / schools) | Python · FastAPI · Kivy · PostgreSQL | Active — demo live; awaiting external input (school/teacher pilots) |
| 2 | **Mentible** | `Mentible` | Education (B2C, self-learners) | React Native · Expo · FastAPI (BYOK) | Pre-MVP (spec + stubs) |
| 3 | **Thittam** | `thittam` | Production-management SaaS | Go microservices · gRPC · NATS · Next.js | Late-build / pre-production |
| 4 | **Pramana** | `pramana` | Compliance training & tracking | Python · FastAPI · SQLAlchemy · PostgreSQL | Spec + early data model |
| 5 | **Kathai Chithiram** | `kathai-chithiram` | Assistive media (special needs) | Python · matplotlib/imageio · Blender | Prototype (PoC renderers) |
| 6 | **dronePrjs** | `dronePrjs` | Robotics / drone simulation | Python · pytest | Early build (sim, Phase 3 partial) |
| 7 | **MarketingTools** | `MarketingTools` | Internal go-to-market tooling | Python · Anthropic API · YAML | Active internal tool |
| 8 | **mambakkam.net** | `mambakkam-net` | Company website / demo host | Astro 5 · Tailwind (AstroWind) | Live / actively published |
| 9 | **wegofwd-expenses** | `wegofwd-expenses` | Internal finance/ops tooling | Python · Gmail API · SQLite · `wegofwd-llm` · pdfminer.six | P0 built (76/76 tests, merged); on GitHub org (private); awaiting real-mailbox dry run |
| 10 | **medtracker** | `medtracker` | Personal/family health ops | Django 5 · django-allauth (Google) · `cryptography` (encrypted JSON vaults) · gunicorn · Tailscale | v0.2.0 — **deployed and in daily use** (tailnet-only, real family data); on GitHub org (private) since 2026-07-14 |

### Archived products (no longer maintained)

| Product | Repo | Category | Primary stack | Status |
|---|---|---|---|---|
| **StudyBuddy Free** | `studybuddy_free` | Education (B2C, standalone) | Python · Kivy · Anthropic API (BYOK) | **Archived** — shipped v1.1.0 (proof-of-concept); GitHub repo archived (read-only). Origin app for the StudyBuddy lineage. |

### Supporting repositories (not standalone products)

| Repo | Purpose |
|---|---|
| `coding-standards` | Shared Claude Code coding rules loaded org-wide via `~/.claude/CLAUDE.md` (21 universal rules + Go/Python conventions). |
| `project-critique` | Independent code reviews, development-pattern analyses, and real-world cost estimates across the portfolio. |
| `studybuddy-docs` | Architecture, ADRs, runbooks, and phased plans for StudyBuddy OnDemand (code lives in `StudyBuddy_OnDemand`). |
| `thittam_docs` | Architecture, ADRs, and API specs for Thittam (code lives in `thittam`). |
| `wegofwd-llm` | **Shared multi-provider LLM seam** (Python library, BYOK, schema-agnostic conformance loop). Consumed by StudyBuddy_OnDemand, Mentible, Kathai Chithiram, and wegofwd-expenses. ADR-012. Critique in `project-critique/wegofwd-llm-critique.md` — under top-level watch as of v2.6. |
| `wegofwd-video` | **Shared video-generation library** (Python), promoted to a standalone package per **ADR-026**. Registry-based provider pattern mirroring `wegofwd-llm` — supports AI video generators (Veo 3.1, Runway, Kling) and deterministic renderers, with provenance. Package `v1.0.0`; consumers pin git tag `v0.1.2`. Consumed by pramana and Kathai Chithiram; Mentible adoption planned. |

---

## The shared thesis: one scoped engine, many products

The portfolio is built around a single reusable idea — a **scoped-retrieval content
engine**. StudyBuddy generates lessons parametrised by `(topic × grade × language ×
format × framing)`; the same pattern is reused elsewhere with a different scope vector:

- **MarketingTools** → `(product × audience × channel × framing) → channel-ready copy`
- **Kathai Chithiram** → `parent story → structured scene script → animation`

Generation is increasingly routed through a shared, provider-agnostic LLM seam
(`wegofwd-llm`), so products can swap between Anthropic, OpenAI, or Gemini. The defensible
IP is described across the repos as the **scoping** (asset libraries, brand rules, curriculum
structure) rather than the model itself.

---

## Product detail

### 1. StudyBuddy OnDemand — `StudyBuddy_OnDemand`
Backend-powered K–12 education platform; the institutional, B2B successor to StudyBuddy Free.
The Anthropic key lives only in backend env vars, content is **pre-generated** by a build
pipeline and served from cache (<1s vs. 5–10s live), progress is durable in PostgreSQL, and
the app is offline-capable with sync. Includes a school portal (classrooms, curriculum
authoring/approval, reports, backup/restore) and multi-provider LLM builds.
Docs report 1,500+ tests (pytest + Playwright), three-track auth (Auth0 + local + admin),
and a production-shaped demo deploy on Hetzner.
- **Stack:** FastAPI backend · Kivy mobile thin-client · content pipeline · PostgreSQL
- **Docs:** `studybuddy-docs`
- **Status:** Active — demo launched; awaiting external input (school/teacher pilots) to move to production.

### 2. Mentible — `Mentible`
A focused, opinionated mobile Anthropic client for **adult self-learners** (BYOK). Public
brand **Mentible** (formerly **StudyBuddy Q**, where "Q = scoped Query"). *"Claude Code, but for learners instead of
coders."* Adults-only (no COPPA/FERPA), quality-over-scale demo of the IP. This repo is also
home to **Mentible** — the book/lesson templating layer (`mentible-professional@1.0`) that
defines how generated content looks and reads.
- **Stack:** React Native + Expo (mobile) · FastAPI (backend) · vendored pipeline (one-way)
- **Status:** Pre-MVP — directory stubs and ADRs; no app code yet.
- **Note:** Shares prompt IP with OnDemand via one-way vendoring; otherwise independent.

### 3. Thittam — `thittam`
Multi-tenant SaaS for **production management** across verticals (film, construction,
software delivery, live events). Each tenant's industry is declared in a YAML "vertical"
file that adapts entity names, phase graphs, budget categories, and workflows. Nine Go
microservices on gRPC + NATS JetStream behind a Kong gateway; tenant-per-schema isolation
in PostgreSQL. Companion docs report four verticals at GA.
- **Stack:** Go microservices · gRPC · NATS · Kong · PostgreSQL · Redis · MinIO · Next.js
- **Docs:** `thittam_docs`
- **Status:** Late-build / pre-production on core services.

### 4. Pramana — `pramana`
*Pramāṇa* (Sanskrit, "valid means of knowledge") — a compliance **training and tracking**
platform. v1 is single-tenant for a corporate client, scoped to SOX, with later frameworks
(HIPAA, ISO 27001, GDPR, PCI DSS) on the roadmap. Repo currently holds locked requirements,
a SQLAlchemy data model + Alembic baseline, and in-process quiz generation.
- **Stack:** Python 3.12 · FastAPI · SQLAlchemy 2.x + Alembic · PostgreSQL · Celery/Redis · `wegofwd-video`
- **Status:** Specification + early data model (no full service yet).
- **License:** Proprietary — © WeGoFwd.

### 5. Kathai Chithiram — `kathai-chithiram`
*Kathai Chithiram* (Tamil, "story → picture"). Turns a **parent's written story into a short,
calm, captioned animation** designed to be understood by a child with special needs (autism
spectrum / developmental needs) — a personalised, on-demand take on social stories. Pipeline:
parent story → `wegofwd-llm` → structured scene script → renderer (`wegofwd-video`) → mp4.
- **Stack:** Python · matplotlib + imageio (v1 renderer) · Blender Grease Pencil (v2) · `wegofwd-llm` · `wegofwd-video`
- **Status:** Prototype — two reference renderers and a first hand-built story ("Silas Shines His Smile").

### 6. dronePrjs — `dronePrjs`
Umbrella for two domain-specific drone applications sharing a common engine: **closedSpace**
(indoor / GPS-denied / collision-dense) and **openSpace** (outdoor / long-range / GPS-available).
The engine is the contract between them; domain logic stays out of the engine.
- **Stack:** Python · pytest · ruff/mypy (simulation-only so far)
- **Status:** Early build — Phase 3 partial (world generator scaffold).

### 7. MarketingTools — `MarketingTools`
Internal tooling to market the whole portfolio from **one source of truth**
(`assets/products.yaml`). Reuses the scoped-engine pattern to turn
`(product × audience × channel × framing)` into channel-ready copy via Claude, plus brand
rules, paste-ready templates, and a CRM-lite outreach log.
- **Stack:** Python · Anthropic API · YAML asset library
- **Status:** Active internal tool (landing/microsite builder still a stub).

### 8. mambakkam.net — `mambakkam-net`
The company website, built on the **AstroWind** (Astro 5 + Tailwind) theme. Also used to
publish product demos (e.g. the Mentible demo).
- **Stack:** Astro 5 · Tailwind CSS · MDX
- **Status:** Live / actively published.

### 9. wegofwd-expenses — `wegofwd-expenses`
Email-driven **expense-tracking pipeline** — an LLM-augmented *scheduled workflow*
(not an agent; control flow is fixed, the LLM only classifies/extracts). Pulls
bill/payment emails from Gmail, classifies + extracts them, upserts an idempotent
SQLite ledger keyed on `message_id`, and emits a monthly Markdown report with
per-currency totals and month-over-month deltas. Five contract-decoupled packages
(`mailfetch → billclassify → billextract → ledger → expensereport`) that
communicate only through on-disk artifacts; sequenced by `run_pipeline.sh` with a
lockfile and env→`~/.config/wegofwd/`→prompt credential loading. Money is
`Decimal`-as-TEXT (never float); low-confidence extractions divert to a review
queue. Built subagent-driven over 10 TDD tasks; ADRs 0001–0003.
- **Stack:** Python 3.11 · Gmail API (OAuth) · SQLite · `wegofwd-llm` (Anthropic: haiku classify / sonnet extract) · pdfminer.six
- **Status:** **P0 built** — 76/76 tests green, merged to `master`; on the **GitHub org (private)**. Next step: real-mailbox dry run (live Gmail/LLM/PDF paths are the network boundary, unit-untested by design).
- **Note:** Consumes the shared `wegofwd-llm` seam. Real Anthropic billing PDFs (home address in bill-to) live in a gitignored data dir; a hermetic golden test validates the ledger→report math against the documented totals.

### 10. medtracker — `medtracker`
Family **medication refill tracker**. A Django app that answers one question per
medication — *when must this be requested so it never runs out?* — from the rule
`request_by = last_filled + day_supply − (lead_time_days + buffer_days)`, driving the
status ladder `OK → DUE SOON → REQUEST NOW → OVERDUE` (plus `REQUESTED`, `Paused`,
and a `Renewal needed` flag when refills run out or the prescription expires before
the supply does). Medication data is **deliberately kept out of the database**: each
family member's records live in a schema-versioned, `cryptography`-encrypted JSON
**vault file**, with SQLite holding only Django auth. Encrypted vaults are optionally
backed up to the super admin's Google Drive. Access is Google sign-in via allauth,
gated by a super-admin list plus a per-vault email allowlist (`MEDTRACKER_RESTRICT_SIGNIN`).
- **Stack:** Python 3.11 · Django 5 · django-allauth (Google OAuth) · `cryptography` · SQLite (auth only) · gunicorn + WhiteNoise · Tailscale
- **Status:** **v0.2.0 — deployed and in daily use.** Built in a single day (10 commits, 2026-07-13); pushed to the **GitHub org (private)** 2026-07-14. Runs as a local `systemd --user` gunicorn service behind `tailscale serve` (Let's Encrypt TLS) — reachable on the private tailnet only, never the public internet.
- **Note:** The **only product in the portfolio with no LLM seam** — no `wegofwd-llm`, no inference cost, no AI at runtime. AI was used to *build* it, not to *run* it, which makes it the portfolio's control case for what the shared-engine thesis is actually worth. Because it handles personal health information, the **code repo is private and every data file is kept out of git by design**, and the full four-lens review (critique · practices · cost · development-pattern) is held **in that private repo** under `docs/critique/` rather than published here.

---

## Archived

### StudyBuddy Free — `studybuddy_free`
The original standalone Python/Kivy app for Grades 5–12 STEM. Students bring their own
Anthropic key (called from the device), read AI-generated chapters, take adaptive quizzes
with hints and step-by-step remediation, and manage a token balance / top-up screen.
Proved the concept that OnDemand productized; retained here for lineage.
- **Stack:** Python · Kivy 2.2 · Anthropic API (BYOK) · local JSON storage
- **Status:** **Archived** — shipped v1.1.0 (2025-03-17), MIT licensed. GitHub repo archived (read-only) 2026-07-06; no longer maintained.

---

## Repository relationships

```
StudyBuddy family
  studybuddy_free ──(productized into)──▶ StudyBuddy_OnDemand ──(docs)──▶ studybuddy-docs
                                          Mentible (formerly StudyBuddy Q)
                                              └─ vendors prompt IP one-way from OnDemand

Thittam family
  thittam ──(docs)──▶ thittam_docs

Shared scoped-retrieval engine / wegofwd-llm seam
  StudyBuddy ─ MarketingTools ─ Kathai Chithiram   (same pattern, different scope vector)
  wegofwd-expenses ──(consumes)──▶ wegofwd-llm   (classify + extract stages)

Standalone (no shared-library dependency)
  medtracker   ─ no wegofwd-llm, no wegofwd-video; the only product with no LLM at runtime

Cross-cutting
  coding-standards ─▶ applies to all projects (Claude Code global rules)
  project-critique ─▶ reviews StudyBuddy, Thittam, dronePrjs, MarketingTools, medtracker, claude-memory
```

---

## Sync status (2026-06-11)

All 13 repositories are present locally and synced with GitHub.

| Repo | Action taken | Result |
|---|---|---|
| `pramana` | Pulled (was 34 behind) | Fast-forwarded to `0d88ebc` |
| `thittam` | Pulled (was 22 behind) | Fast-forwarded to `c3f9078` |
| `project-critique` | Pulled (was 10 behind) | Fast-forwarded to `ba8f9e1` |
| `Mentible` | Fixed missing auth token on remote, then fetched | Up to date |
| `studybuddy-docs` | Cloned (was missing locally) | New |
| `thittam_docs` | Cloned (was missing locally) | New |
| `MarketingTools` | Cloned (was missing locally) | New |
| `kathai-chithiram` | Cloned (was missing locally) | New |
| `StudyBuddy_OnDemand`, `coding-standards`, `dronePrjs`, `mambakkam-net`, `studybuddy_free` | None needed | Already in sync |

**Notes**
- No local repo was ahead of its remote, so every sync was a safe fast-forward — no local work was lost.
- Two repos are checked out on feature branches (left as-is): `StudyBuddy_OnDemand` → `fix/frontend-unit-tests-363`, `Mentible` → `docs/adr-014-user-accounts`.
- A full account-wide repo enumeration via the GitHub API/website wasn't reachable from this environment; the four cloned repos were discovered from cross-references inside your project docs. If the org has additional repos not referenced anywhere, tell me the names and I'll clone them too.
