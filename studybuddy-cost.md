# StudyBuddy OnDemand — Real-World Cost Analysis

**Analysed:** 2026-06-02 (v1.1 — re-anchored to HEAD `0d7abe1` on `main`; adds the Curriculum Authoring Studio / Epic 12 + book-export) · 2026-05-24 (v1.0 — first cost pass against HEAD `d5c75ad`)
**Repo:** `wegofwd2020-hub/StudyBuddy_OnDemand`
**Question being answered:** if this same artifact had been built by a conventional team in the real world (not by a single founder with Claude-assisted execution), what would it have cost in money and calendar time?
**Scope of measurement:** code on disk at HEAD `0d7abe1` (2026-06-01) — "late-build / pre-production" state per the v1.6 critique. Production launch costs (load testing, security audit, SOC2-lite, datacentre, on-call rota) are **not** in either column; both a real team and the actual build still need to do that work before paying customers.

> **v1.1 refresh note (2026-06-02).** Re-measured at HEAD `0d7abe1`: **808 commits** (was 726), **1,081 backend test functions** (was 1,029), **60 Alembic migrations** (was 59), **first commit 2026-03-23 → last 2026-06-01 = ~70 calendar days** (was 60). The substantive addition since v1.0 is **Epic 12 — the Curriculum Authoring Studio** (interactive TOC-structure → generate → review/regenerate → snapshot → publish, with a publish-completeness gate) plus the **book-export (#400)** content bridge to the sibling Mentible product. For a conventional team this is roughly **+3–4 engineer-months** of additional work (an interactive, versioned authoring surface + LLM structuring + export transform + completeness gating). The central estimate therefore moves **42 → ~45 EM**, and the Scenario A/B/C dollar figures below scale up by **~7%** (e.g. Scenario A ~$1.41M → ~$1.51M; Scenario B ~$467k → ~$500k). The detailed tables in §3–§4 are preserved as the v1.0 baseline; treat them as the lower bound of the current artifact. Headline multipliers (§7) are essentially unchanged (the actual outlay grew by perhaps a week of founder time).

---

## 1. What's actually been built

Measured directly from the repository (v1.1 re-anchored to HEAD `0d7abe1`, 2026-06-01; first commit 2026-03-23 → **~70 calendar days**. LOC/route figures below are the v1.0 `d5c75ad` measurement unless marked; counts marked ⟳ were re-measured at `0d7abe1`).

| Slice | Measure |
|---|---|
| Backend (FastAPI / Python) | **43,434 LOC** (v1.0), 23 domain modules, **275 API routes**, ⟳ **1,081 test functions** across 78 files |
| Authoring Studio (Epic 12, ⟳ new since v1.0) | super-admin `backend/src/admin/authoring_*` + `pipeline/toc_structurer.py` + `flow_analyzer.py` + web `app/(admin)/admin/authoring`; migration 0060; book-export `admin/book_export.py` |
| Web (Next.js 14 / TypeScript) | **59,294 LOC** across 271 files, 66 components, **130 page routes** |
| Web tests | **17 Playwright specs + 63 unit tests** (18,205 test LOC) |
| Pipeline (Python) | **3,941 LOC** — content + Remotion video generation |
| Mobile harness (Python) | **6,904 LOC** |
| Database | ⟳ **60 Alembic migrations** (latest 0060, Authoring Studio), multi-tenant RLS, pgvector, RedBeat, pgbouncer |
| Visual assets | **500 SVG** library entries with embeddings |
| Documentation | **86 markdown files**, **17 formal Epic specs** (3,855 LOC of specifications) |
| Integrations | Auth0 (JWKS + RBAC), Stripe (subscriptions), Voyage AI (embeddings), Celery/Redis, S3/Local storage backend, Remotion (video), nginx |
| Compliance | COPPA codified in `compliance.ts`, RLS extended in migrations 0028 / 0046 |
| Activity | ⟳ **808 commits**, **214+ GitHub-issue closures**, sole-author |
| **Production LOC (excl. tests, sample-content)** | **~113,500 LOC** |

---

## 2. Methodology — triangulated three ways

A single estimate from one method is not defensible. I used three independent methods and reported the convergence.

1. **Industry-velocity benchmark.** Comparable K-12 EdTech multi-tenant SaaS with COPPA + content pipeline + 3-persona UI + subscription billing typically takes **24–36 engineer-months** in a well-run startup team to reach the equivalent "late-build / pre-production" state. Reference points: post-mortems from YC B2B SaaS cohorts, EdTech case studies, and observed velocity at companies of similar feature surface.
2. **COCOMO-II modernized.** At ~113.5 KLOC production code, raw COCOMO gives ~500 EM; modernized with a 0.25 framework-productivity multiplier (Next.js / FastAPI / SQLAlchemy / Alembic over 1990s baselines) and a 0.7 single-team coordination multiplier ⇒ **~85 EM**. Treated as the upper sanity bound — COCOMO-II is famously punitive on large codebases.
3. **Feature-counting.** 17 epics × ~5 weeks/epic average for a 4-person team × 0.85 coordination factor ⇒ **~42 EM**.

**Convergence: 36–48 engineer-months is the defensible central range.** Point estimate **42 EM**.

---

## 3. Team composition

Assume **42 EM spread across 4.5 FTE for ~9.3 calendar months**. Loaded rates are fully burdened (cash salary + benefits + employer taxes + tooling + recruiting amortization; equity excluded from cash columns).

| Role | FTE | Why needed for this artifact |
|---|---|---|
| Tech Lead / Staff Engineer | 1.0 | Architecture, multi-tenant + RLS + COPPA design, code review |
| Senior Backend Engineer | 1.0 | FastAPI, SQLAlchemy, Celery, pipeline, integrations |
| Senior Frontend Engineer | 1.0 | Next.js, 130 routes, 66 components, three persona UIs |
| DevOps / Platform | 0.5 | Docker, nginx, pgbouncer, Hetzner, RedBeat, CI/CD |
| Product Designer | 0.5 | 3-persona UX, accessibility, Epic 13 branding refresh |
| Product Manager | 0.5 | 17 epics, demo orchestration, school onboarding |
| QA / SDET | 0.5 | 1,029 backend tests + 17 Playwright specs + axe a11y |
| **Total** | **4.5 FTE** | |
| Compliance counsel (COPPA) | external | One-time review + ongoing retainer |

---

## 4. Cost scenarios

### Scenario A — US tech labour market (Bay Area / NYC / Seattle blended, 2025–2026 rates)

| Role | FTE | Loaded $/yr | 9.3-month cost |
|---|---|---|---|
| Tech Lead | 1.0 | $440k | $341k |
| Sr Backend | 1.0 | $320k | $248k |
| Sr Frontend | 1.0 | $320k | $248k |
| DevOps | 0.5 | $320k | $124k |
| Designer | 0.5 | $260k | $101k |
| PM | 0.5 | $300k | $116k |
| QA / SDET | 0.5 | $220k | $85k |
| **People subtotal** | **4.5** | | **$1,263k** |
| COPPA legal review + retainer | | | $45k |
| Infra (AWS / Hetzner / Stripe fees / Auth0 paid tier / Voyage / Sentry / etc.) | | | $40k |
| Tooling & SaaS (GitHub, Linear, Figma, Notion, observability) | | | $25k |
| Equipment + onboarding amortization | | | $35k |
| **Scenario A total** | | | **~$1.41M** |

### Scenario B — Blended global / India tier-1 + EU senior contractors

| Role | FTE | Loaded $/yr | 9.3-month cost |
|---|---|---|---|
| Tech Lead | 1.0 | $140k | $109k |
| Sr Backend | 1.0 | $85k | $66k |
| Sr Frontend | 1.0 | $85k | $66k |
| DevOps | 0.5 | $80k | $31k |
| Designer | 0.5 | $70k | $27k |
| PM | 0.5 | $95k | $37k |
| QA / SDET | 0.5 | $55k | $21k |
| **People subtotal** | **4.5** | | **$357k** |
| COPPA legal (still US-counsel) | | | $30k |
| Infra / SaaS / tooling | | | $55k |
| Equipment + onboarding | | | $25k |
| **Scenario B total** | | | **~$467k** |

### Scenario C — Lean junior-heavy India team (1 senior lead + 3 mid + 0.5 designer, 11 months)

| Bucket | 11-month cost |
|---|---|
| People (5 FTE, junior-skewed) | $215k |
| COPPA legal | $30k |
| Infra + SaaS | $60k |
| **Scenario C total** | **~$305k** |

*Schedule risk caveat:* much higher — junior-heavy teams typically miss the COPPA / RLS / multi-tenant invariants on the first pass, requiring a senior-pass rework before a real-world launch is safe.

---

## 5. Calendar-time cost

| Scenario | Wall-clock duration to reach `d5c75ad` equivalent |
|---|---|
| US team, 4.5 FTE | **9–11 months** |
| Blended global team, 4.5 FTE | **10–12 months** (add ~1 month for timezone coordination overhead) |
| Lean junior team, 5 FTE | **12–15 months** (more rework cycles on compliance + multi-tenant invariants) |
| **Actual (single founder + Claude Opus 4.x)** | **2 months (60 days)** — HEAD `d5c75ad` reached 2026-05-22 from first commit 2026-03-23 |

Calendar duration matters as much as dollar cost — opportunity cost of time-to-market is rarely captured in spreadsheets.

---

## 6. What was actually spent

| Line item | Estimate |
|---|---|
| Founder time, ~60 days × ~10h/day (focused) | ~600 hours |
| Claude Code subscription / API (intensive 2 months) | $400–2,000 |
| Hetzner VM + Postgres + Redis + bandwidth (dev) | ~$150 |
| Auth0 free tier, Stripe (fee-only), Voyage AI dev tier | ~$100 |
| Domain (`usestudybuddy.com`), email, GitHub Pro | ~$100 |
| **Direct cash outlay** | **~$1k–$2.5k** |
| Founder opportunity cost @ $300k/yr equivalent × 2 mo | **~$50k** |
| **All-in actual cost** | **~$50k–$53k** |

---

## 7. Headline ratios

| Comparison | US scenario | Blended scenario |
|---|---|---|
| Cash-only multiplier | **~700× cheaper** ($1.41M ÷ $2k) | **~230× cheaper** ($467k ÷ $2k) |
| All-in multiplier (incl. founder opp-cost) | **~27× cheaper** ($1.41M ÷ $52k) | **~9× cheaper** ($467k ÷ $52k) |
| Calendar compression | **~5× faster** (60 days vs. ~10 months) | **~5.5× faster** (60 days vs. ~11 months) |
| Team-size compression | **4.5× smaller** (1 vs. 4.5 FTE) | **4.5× smaller** |

---

## 8. Honest caveats

- The 42 EM estimate assumes a competent team. A sloppy team would burn more; an elite YC-tier team could probably hit 32 EM. Range **30–55 EM** is defensible.
- US / Blended rate ranges shift ±15% with market conditions. The 2025–2026 market has softened from the 2021–2022 peaks; pre-softening rates would be ~20% higher.
- The actual build benefits from a senior-architect-level founder making structural calls — a less-experienced founder + Claude would not hit this velocity even with the same tooling. **Some of the multiplier is the founder, not just the AI.** Conservative attribution: ~40% founder skill, ~60% AI assistance, but the two compound rather than substitute.
- Production-launch costs (load testing, security audit, SOC2-lite, datacentre, on-call rota) are **not** in either column. Both the real team and the AI-assisted build still need to do that work before paying customers.
- Visual-library content (500 SVGs + Remotion clips) would dominate a real team's cost if hand-produced; Claude generated / curated the bulk. If you stripped that asset class out, the conventional-team cost drops by ~$80–150k (US scenario).
- Equity is excluded from all cash columns. A real team's *total* compensation including equity at face value would be ~30% higher than the loaded-cost figures above. Whether that equity ever liquidates is a separate question.

---

## 9. What this means

The cash-only ratios (700× / 230×) are headline-grabbing but somewhat misleading — they ignore that the founder is paying themselves in time, not cash. The **all-in multipliers (27× US / 9× blended)** are the honest comparison and are still extraordinary.

The more durable observation is the **calendar compression**: a single founder reached a "late-build / pre-production" state in 2 months that a 4.5-FTE conventional team would need 9–11 months to reach. In a competitive market that 7–9 month head-start is worth more than the dollar savings.

The artifact has tests, accessibility coverage, documentation, formal epic specs, and compliance posture — this is not a "demo-quality" comparison. It is a real artifact compared against what a real team would have built.

---

*Cost analysis is a point-in-time exercise. Loaded rates, market conditions, and AI tooling capability all evolve. Re-run this analysis annually if it's being used to inform staffing or fundraising decisions.*
