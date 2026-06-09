# StudyBuddy SelfLearner (Mentible) — Real-World Cost Analysis

**Analysed:** 2026-06-02 (v1.0 — first cost pass against branch `feat/authoring-regenerate-export-fixes` @ `e1c66f7`)
**Repo / brand:** `wegofwd2020-hub/StudyBuddy_SelfLearner` · public brand **Mentible**
**Question being answered:** if this same artifact had been built by a conventional team in the real world (not by a single founder with Claude-assisted execution), what would it have cost in money and calendar time?
**Scope of measurement:** code on disk at `e1c66f7` — a **pre-deploy MVP** (feature-complete in code for its MVP slice, not yet deployed or run against live Anthropic). Production launch, app-store release, the separate free reader app (ADR-004), and the multi-provider/managed-key layer (ADR-005) are **not** in either column — they are unbuilt in both the real-team and actual columns.

---

## 1. What's actually been built

Measured directly from the repository (`e1c66f7`; first commit 2026-04-25 → last 2026-06-01 = **~5 weeks**, 131 commits, sole-author).

| Slice | Measure |
|---|---|
| Mobile (React Native / Expo) | **6,511 LOC** src + 2,048 test LOC; Expo Router; Query / Library / Books / Settings + book new/import/generate/read + lesson view; WebView KaTeX + Mermaid renderer; `expo-secure-store` BYOK key |
| Backend (FastAPI / Python) | **1,843 LOC** src + 1,428 test LOC; `/generate` + `/jobs/{id}` + `/structure` + `/export`; BYOK AES-GCM/HKDF envelope; in-process async worker; idempotency + retry |
| Compiler (TypeScript / Node) | **1,631 LOC** src + 927 test LOC; `book.json` → **EPUB3 + PDF**; OPF 3.0 + Dublin Core + nav.xhtml + toc.ncx; SVG cover; colophon; embedded Source Serif 4; image packaging; Vivliostyle PDF; optional Mermaid→SVG |
| Pipeline (vendored Python) | **1,007 LOC** — prompts + providers + validator + TOC structurer, vendored one-way from OnDemand with recorded SHAs |
| Database / state | Redis only (encrypted key envelope + job status + idempotency); **no SQL, no multi-tenancy** (single-user by design) |
| Tests | **75 backend `def test_`** + ~60 compiler + ~111 mobile `it/test` blocks; 4-job CI incl. a repo-wide `sk-ant-` key-leak gate |
| Documentation | 6 ADRs + MVP/ARTIFACT_PIPELINE/SCOPE/compile-plan/deploy specs + branding/competitive analyses |
| Integrations | Anthropic SDK (per-call BYOK key), Fly.io (scale-to-zero), Firebase/FCM (planned), headless Chromium (Mermaid) |
| Security | BYOK Pattern B: HKDF-per-job AES-256-GCM envelope, TTL + shred, structlog redaction, CI key-leak gate |
| **Production LOC (excl. tests)** | **~10,992 LOC** (mobile 6,511 / compiler 1,631 / backend 1,843 / pipeline 1,007) |

The cost-defining slice is the **EPUB3 + PDF compiler**: a correct EPUB3 generator (OPF 3.0, dual nav.xhtml/NCX, MathML/SVG properties, font embedding, de-duplicated image packaging) plus a Vivliostyle CSS-Paged-Media PDF path is *specialist* work that a generalist team would either learn slowly or contract out.

---

## 2. Methodology — triangulated three ways

1. **Industry-velocity benchmark.** A BYOK mobile authoring app + a security-reviewed key-handling backend + a publishing-grade EPUB3/PDF compiler, to a *tested pre-deploy MVP*, typically takes a focused 2.5–3-person team **~4–6 calendar months** — call it **12–16 engineer-months**. The EPUB/EPUB3 publishing pipeline is the long pole; teams without prior ebook experience routinely underestimate it.
2. **COCOMO-II modernized.** At ~11 KLOC production code, raw COCOMO gives ~45 EM; modernized with a 0.25 framework-productivity multiplier (Expo / FastAPI / a TS ebook toolchain over 1990s baselines) and a 0.7 single-team coordination multiplier ⇒ **~12–18 EM**. Upper sanity bound.
3. **Feature-counting.** BYOK generate loop + crypto envelope (security-sensitive) ~2.5 EM; RN/Expo app with five screen areas + WebView KaTeX/Mermaid renderer ~3.5 EM; TS EPUB3+PDF compiler ~3.5 EM; vendoring + pipeline integration ~1 EM; CI + test suite + ADRs ~1.5 EM ⇒ **~12 EM**.

**Convergence: 12–16 engineer-months is the defensible central range.** Point estimate **13 EM**.

---

## 3. Team composition

Assume **13 EM spread across ~3 FTE for ~4.5 calendar months**. Loaded rates are fully burdened (salary + benefits + employer taxes + tooling + recruiting amortization; equity excluded from cash columns). No compliance counsel line — this is an **adult-only product (no COPPA/FERPA)** — but a BYOK product needs a real security review.

| Role | FTE | Why needed for this artifact |
|---|---|---|
| Senior Full-Stack (FastAPI + RN) | 1.0 | Backend BYOK service + Expo app + integration |
| Publishing/Frontend Specialist | 1.0 | EPUB3/PDF compiler (Vivliostyle, OPF/NCX, fonts) + WebView KaTeX/Mermaid renderer |
| Security / DevOps | 0.5 | BYOK threat model + envelope review, Fly deploy, CI key-leak gating |
| Product Designer / PM | 0.5 | "Author Yourself" UX, scope-dimension input design, brand (Mentible) |
| **Total** | **3.0 FTE** | |
| Security review (external, BYOK) | one-time | Independent review of the key-handling contract |

---

## 4. Cost scenarios

### Scenario A — US tech labour market (Bay Area / NYC / Seattle blended, 2025–2026 rates)

| Role | FTE | Loaded $/yr | 4.5-month cost |
|---|---|---|---|
| Senior Full-Stack | 1.0 | $340k | $128k |
| Publishing/FE Specialist | 1.0 | $320k | $120k |
| Security / DevOps | 0.5 | $340k | $64k |
| Designer / PM | 0.5 | $280k | $53k |
| **People subtotal** | **3.0** | | **$365k** |
| External BYOK security review | | | $20k |
| Infra (Fly, Redis, Anthropic dev, Firebase, Apple/Google dev accounts) | | | $15k |
| Tooling & SaaS (GitHub, Figma, observability) | | | $15k |
| Equipment + onboarding amortization | | | $20k |
| **Scenario A total** | | | **~$435k** |

### Scenario B — Blended global / India tier-1 + EU senior contractors

| Role | FTE | Loaded $/yr | 4.5-month cost |
|---|---|---|---|
| Senior Full-Stack | 1.0 | $90k | $34k |
| Publishing/FE Specialist | 1.0 | $90k | $34k |
| Security / DevOps | 0.5 | $80k | $15k |
| Designer / PM | 0.5 | $70k | $13k |
| **People subtotal** | **3.0** | | **$96k** |
| BYOK security review (US-counsel-adjacent) | | | $18k |
| Infra / SaaS / tooling | | | $25k |
| Equipment + onboarding | | | $12k |
| **Scenario B total** | | | **~$151k** |

### Scenario C — Lean two-person specialist team (1 senior full-stack + 1 ebook/FE specialist, 6 months)

| Bucket | 6-month cost |
|---|---|
| People (2 FTE, senior) | $124k (US) / $34k (blended) |
| Security review | $18k |
| Infra + SaaS | $25k |
| **Scenario C total** | **~$167k (US-led)** |

*Schedule-risk caveat:* a two-person team without prior EPUB3 experience would likely overrun on the compiler; the publishing pipeline is the slice most prone to a "looks done, fails epubcheck" tail.

---

## 5. Calendar-time cost

| Scenario | Wall-clock duration to reach `e1c66f7` equivalent |
|---|---|
| US team, 3 FTE | **4–5 months** |
| Blended global team, 3 FTE | **5–6 months** (add timezone coordination overhead) |
| Lean 2-person specialist team | **5–7 months** (compiler tail risk) |
| **Actual (single founder + Claude Opus 4.x)** | **~5 weeks** — first commit 2026-04-25 → `e1c66f7` 2026-06-01, *concurrent with active OnDemand work* |

The calendar figure carries an honest asterisk: these ~5 weeks overlapped with ongoing StudyBuddy_OnDemand development, so the founder's effort was not exclusively on Mentible. The wall-clock compression is real; the implied single-person-month count is lower than a dedicated-team-month count.

---

## 6. What was actually spent

| Line item | Estimate |
|---|---|
| Founder time, ~3–4 focused weeks-equivalent (part of a 5-week window shared with OnDemand) | ~150–200 hours |
| Claude Code subscription / API (intensive) | $200–800 |
| Anthropic *token* cost for the product itself | **$0 — BYOK; the user pays Anthropic directly** |
| Fly.io (not yet deployed; scale-to-zero) | ~$0–20 |
| Apple/Google developer accounts (not yet purchased) | $0 so far ($25 + $99/yr at release) |
| Domain / brand (Mentible, pending clearance) | ~$50 |
| **Direct cash outlay** | **~$0.3k–1k** |
| Founder opportunity cost @ $300k/yr equivalent × ~1 month | **~$25k** |
| **All-in actual cost** | **~$25k–26k** |

The **BYOK structure is the genuinely novel cost lever**: the product's marginal cost of generation is borne by the *user*, so neither the build nor the run carries an Anthropic token bill. A conventional team building the same product would also choose BYOK (it's the point), so this doesn't change the *comparison* — but it makes the actual operating cost structurally near-zero on the most variable line item.

---

## 7. Headline ratios

| Comparison | US scenario | Blended scenario |
|---|---|---|
| Cash-only multiplier | **~600× cheaper** ($435k ÷ ~$0.7k) | **~215× cheaper** ($151k ÷ ~$0.7k) |
| All-in multiplier (incl. founder opp-cost) | **~17× cheaper** ($435k ÷ $26k) | **~6× cheaper** ($151k ÷ $26k) |
| Calendar compression | **~4× faster** (~5 weeks vs ~4.5 months) | **~4.5× faster** (~5 weeks vs ~5.5 months) |
| Team-size compression | **3× smaller** (1 vs 3 FTE) | **3× smaller** |

These land in the same family as the other three projects in this repo (OnDemand 27× US all-in, Thittam 61×, dronePrjs 44×) — at the lower multiplier end, which is expected: Mentible is the youngest and smallest artifact, and a single specialist-grade slice (the compiler) is the kind of work where AI assistance compresses *less* than on boilerplate-heavy CRUD.

---

## 8. Honest caveats

- The 13 EM estimate assumes a competent team *with* ebook-publishing experience. A team learning EPUB3 on the job would burn more on the compiler; an elite team that has shipped an ebook pipeline before could hit ~10 EM. Range **10–18 EM** is defensible.
- This is a **pre-deploy MVP**. The artifact has never run against live Anthropic or a deployed backend (per `STATUS.md`). A real team's figure to the *same* unverified state is what's compared — both columns still owe deployment, app-store submission, and on-device verification.
- Two **accepted-but-unbuilt** expansions are excluded from both columns: the separate free reader app (ADR-004) and the multi-provider/managed-key layer (ADR-005). Adding either materially raises both the conventional-team and actual cost.
- The founder benefits from having just built the sibling OnDemand product — the prompt IP, the rendering rules, and the scope-dimension model were *vendored*, not re-invented. **Some of the velocity is reuse from OnDemand, not AI assistance per se** — the two compound.
- Equity is excluded from all cash columns; a real team's total comp including equity would be ~30% higher than the loaded figures.
- The calendar figure overlapped with OnDemand work — treat "~5 weeks" as wall-clock, not exclusive founder-time.

---

## 9. What this means

The honest comparison is the **all-in multiplier: ~17× cheaper (US) / ~6× (blended)**, with a **~4× calendar compression**. Those are smaller than the sibling projects' multipliers, and that's the *informative* result: Mentible is dominated by one specialist slice (a publishing-grade EPUB3/PDF compiler) where AI assistance helps but does not collapse the work the way it does on multi-tenant CRUD or test scaffolding. The lesson is directional — **the compression multiplier is a function of how much of the artifact is well-trodden vs specialist**, and a single founder + Claude still reached a tested, security-reviewed, two-runtime MVP in ~5 weeks of shared calendar that a 3-FTE team would need ~4–5 months to match.

The more durable observation is the **cost structure**: BYOK means the product's most variable cost (LLM tokens) is borne by the user, and the build carried *zero* token cost. A bootstrapped founder can ship and operate a generative product without ever underwriting inference — that is a strategic advantage independent of any cheaper-and-faster multiplier.

---

*Cost analysis is a point-in-time exercise. Loaded rates, market conditions, and AI tooling capability all evolve. This is a v1.0 pass against a pre-deploy MVP; re-run once the product is deployed and the reader app / managed-key layer are built, as both will shift the conventional-team baseline.*
