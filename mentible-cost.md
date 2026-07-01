# Mentible — Real-World Cost Analysis

**Analysed:** 2026-06-09 (v2.0 — major refresh; re-anchored to branch `main` @ `40166ee`. **97 commits since v1.0** added a multi-provider LLM seam *extracted into the installable `wegofwd-llm` package*, free-provider support, the Pramana integration boundary, an opt-in narrative mode, a books-only refactor, and a substantially expanded compiler — real new scope that raises the conventional-team estimate.)
**Prior pass:** 2026-06-02 (v1.0 — first cost pass, branch `feat/authoring-regenerate-export-fixes` @ `e1c66f7`; figure ~$435k US / ~$151k blended at ~13 EM)
**Repo / brand:** `wegofwd2020-hub/Mentible` · public brand **Mentible**
**Question being answered:** if this same artifact had been built by a conventional team in the real world (not by a single founder with Claude-assisted execution), what would it have cost in money and calendar time?
**Scope of measurement:** code on disk at `40166ee` — a **pre-deploy MVP** (feature-complete in code for a now-larger MVP slice: multi-provider, books-only; not yet deployed or run against a deployed backend). The *standalone* `wegofwd-llm` package **is** in scope this time (it is real code Mentible depends on; on disk Mentible is its sole consumer). The separate free reader app (ADR-004), the full managed-key layer, and the Pramana product itself remain out of both columns; the **Mentible↔Pramana integration** counts only the thin outbound HTTP port present on disk (`mentible_client.py`), not the as-yet-unwired Pramana-side generation.

---

## What changed since v1.0 (cost-relevant)

| Cost driver | v1.0 (`e1c66f7`) | v2.0 (`40166ee`) | Cost effect |
|---|---|---|---|
| In-repo production LOC (excl. tests) | ~10,992 | **~13,118** (+~19%) | More to build |
| New external shared package | — | **`wegofwd-llm` 773 LOC src + 48 tests** | A discrete deliverable a real team would scope, design, and test on its own |
| LLM providers | 1 (Anthropic, inline) | **5** (Anthropic native tool-use, OpenAI-compatible, Groq, OpenRouter, Gemini) via a typed seam | Multi-provider conformance + per-provider capability modeling is real integration work |
| Generation robustness | blind retry ×6 | **validate→repair conformance loop** | Non-trivial; harder to get right than re-rolling |
| Product surface | Query + books | **Books-only** (Query removed, ADR-009) | A refactor, modest net |
| Inter-product integration | none | **Mentible↔Pramana boundary** (ADR-011/013; HTTP handoff port on disk) | New boundary design |
| Security | BYOK Pattern B | + **422 key-echo leak found & closed** (ADR-001) | A security-review-grade find |
| ADRs / decisions | 6 | **13** | More design/spec work |
| Backend tests | 75 | **96** | More test surface |
| Compiler | 1,631 LOC | **2,223 LOC** (house-style parity, theming, accessibility, watermarking) | The specialist slice grew |

Net: the conventional-team estimate rises from **~13 EM** (v1.0) to **~16 EM** (v2.0). Arithmetic below.

---

## 1. What's actually been built

Measured directly from the repository (`40166ee`; first commit 2026-04-25 → last 2026-06-09 = **~6.5 weeks**, 228 commits, sole-author), plus the dependent `wegofwd-llm` package.

| Slice | Measure |
|---|---|
| Mobile (React Native / Expo) | **7,696 LOC** src + 2,212 test LOC; Expo Router; **Books-only** (Library · Books · Settings · Help · About); multi-provider BYOK keystore + provider/model picker; WebView KaTeX + Mermaid; book JSON round-trip + real EPUB cover import |
| Backend (FastAPI / Python) | **1,953 LOC** src + 1,771 test LOC; `/generate` + `/jobs/{id}` + `/structure` + `/export`; BYOK AES-GCM/HKDF envelope; **422-scrub handler**; in-process async worker; routes generation through the **`wegofwd-llm` seam** (`generate_validated`/`build_provider`/`provenance`) |
| Compiler (TypeScript / Node) | **2,223 LOC** src + 1,048 test LOC; `book.json` → **EPUB3 + PDF**; OPF 3.0 + Dublin Core + **EPUB Accessibility 1.1** + nav.xhtml + toc.ncx; branded diagram themes/tokens; house-style parity; release watermarking; Vivliostyle PDF |
| Pipeline (vendored Python) | **1,246 LOC** — prompts (incl. diagram registers + animated-visual path) + provider adapters/config bridging to the seam + validator + TOC structurer; vendored one-way from OnDemand |
| **`wegofwd-llm` seam (external package)** | **773 LOC src + 48 tests** — typed `Provider`/`LLMRequest`/`LLMResponse`/`Capabilities` contract, `ProviderSpec` registry (per-provider ceilings), `generate_validated` conformance loop, native Anthropic tool-use, OpenAI-compatible provider; `py.typed`; on disk consumed by Mentible (Pramana intended per ADR-012, not yet wired) |
| Database / state | Redis only (encrypted key envelope + job status + idempotency); **no SQL, single-user** by design |
| Tests | **96 backend `def test_`** + 71 compiler + 132 mobile blocks + **48 in the seam** + 15 in `tests/llm/test_config.py`; 4-job CI incl. repo-wide `sk-ant-` key-leak gate |
| Documentation | **13 ADRs** + MVP/ARTIFACT_PIPELINE/SCOPE/PROFESSIONAL_PUBLISHING + 5 multi-provider wiring memos + manus.ai comparisons |
| Security | BYOK Pattern B + **422-scrub** + multi-provider key redaction |
| **In-repo production LOC (excl. tests)** | **~13,118 LOC** (mobile 7,696 / compiler 2,223 / backend 1,953 / pipeline 1,246) **+ 773 external** = **~13,891 LOC** counted for scope |

The cost-defining slices are now **two**: the publishing-grade **EPUB3 + PDF compiler** (unchanged as the specialist long pole, now larger), and the **multi-provider seam + conformance loop**, packaged and shared — a discrete integration deliverable a real team would design, test, and version on its own.

---

## 2. Methodology — triangulated three ways

1. **Industry-velocity benchmark.** v1.0's "BYOK mobile authoring app + security-reviewed key backend + EPUB3/PDF compiler" was ~12–16 EM. v2.0 adds a **multi-provider seam packaged as a shared library with a conformance loop and per-provider capability modeling** (a focused integration engineer, ~2.5–3.5 EM on its own), a **found-and-closed key-leak security fix** (~0.5 EM incl. the review that finds it), and a **larger compiler** (+~0.5 EM). Net **~15–18 calendar-engineer-months** to a tested pre-deploy MVP for a 3-person team over ~5–5.5 months.
2. **COCOMO-II modernized.** At ~13.9 KLOC production code, raw COCOMO gives ~58 EM; modernized with a 0.25 framework-productivity multiplier and a 0.7 single-team coordination multiplier ⇒ **~10–14 EM** — *but* COCOMO under-weights the multi-provider integration and EPUB specialist tails, so treat the lower end as an underestimate. Upper sanity bound ~18 EM.
3. **Feature-counting.** BYOK generate loop + crypto envelope + **422-scrub** (security-sensitive) ~3 EM; RN/Expo books-only app with multi-provider keystore + WebView renderer ~4 EM; TS EPUB3+PDF compiler (now with theming/accessibility/watermarking) ~4 EM; **multi-provider seam package + conformance loop + free providers + clamp** ~3 EM; vendoring + pipeline + Pramana boundary ~1 EM; CI + tests + 13 ADRs ~1.5 EM ⇒ **~16.5 EM**.

**Convergence: 15–18 engineer-months is the defensible central range (was 12–16).** Point estimate **16 EM** (was 13).

---

## 3. Team composition

Assume **16 EM spread across ~3.25 FTE for ~5 calendar months**. Loaded rates are fully burdened (salary + benefits + employer taxes + tooling + recruiting amortization; equity excluded from cash columns). No compliance-counsel line — **adult-only product (no COPPA/FERPA)** — but a BYOK *multi-provider* product needs a real security review (the 422 leak is exactly the kind a review catches).

| Role | FTE | Why needed for this artifact |
|---|---|---|
| Senior Full-Stack (FastAPI + RN) | 1.0 | Backend BYOK service + Expo app + integration |
| Publishing/Frontend Specialist | 1.0 | EPUB3/PDF compiler (Vivliostyle, OPF/NCX, fonts, accessibility, watermarking) + WebView renderer |
| LLM Integration Engineer | 0.5 | **Multi-provider seam package + conformance loop + per-provider capabilities + free-provider verification** |
| Security / DevOps | 0.5 | BYOK threat model + envelope + **422-scrub** review, Fly deploy, CI key-leak gating |
| Product Designer / PM | 0.25 | "Author Yourself" UX, scope-dimension input design, brand |
| **Total** | **3.25 FTE** | |
| Security review (external, BYOK) | one-time | Independent review of the key-handling contract (incl. the 422 echo class) |

---

## 4. Cost scenarios

### Scenario A — US tech labour market (Bay Area / NYC / Seattle blended, 2025–2026 rates)

| Role | FTE | Loaded $/yr | 5-month cost |
|---|---|---|---|
| Senior Full-Stack | 1.0 | $340k | $142k |
| Publishing/FE Specialist | 1.0 | $320k | $133k |
| LLM Integration Engineer | 0.5 | $340k | $71k |
| Security / DevOps | 0.5 | $340k | $71k |
| Designer / PM | 0.25 | $280k | $29k |
| **People subtotal** | **3.25** | | **$446k** |
| External BYOK security review | | | $22k |
| Infra (Fly, Redis, multi-provider dev keys, Firebase, Apple/Google) | | | $18k |
| Tooling & SaaS (GitHub, Figma, observability) | | | $16k |
| Equipment + onboarding amortization | | | $22k |
| **Scenario A total** | | | **~$524k** |

### Scenario B — Blended global / India tier-1 + EU senior contractors

| Role | FTE | Loaded $/yr | 5-month cost |
|---|---|---|---|
| Senior Full-Stack | 1.0 | $90k | $38k |
| Publishing/FE Specialist | 1.0 | $90k | $38k |
| LLM Integration Engineer | 0.5 | $85k | $18k |
| Security / DevOps | 0.5 | $80k | $17k |
| Designer / PM | 0.25 | $70k | $7k |
| **People subtotal** | **3.25** | | **$118k** |
| BYOK security review (US-counsel-adjacent) | | | $20k |
| Infra / SaaS / tooling | | | $28k |
| Equipment + onboarding | | | $13k |
| **Scenario B total** | | | **~$179k** |

### Scenario C — Lean three-person specialist team (full-stack + ebook/FE + LLM-integration, 6 months)

| Bucket | 6-month cost |
|---|---|
| People (2.5 FTE-equiv, senior) | $175k (US) / $48k (blended) |
| Security review | $20k |
| Infra + SaaS | $28k |
| **Scenario C total** | **~$223k (US-led)** |

*Schedule-risk caveat:* the compiler tail risk from v1.0 remains (a team without prior EPUB3 experience overruns on "looks done, fails epubcheck"), and the multi-provider seam adds a *second* tail — verifying free-provider endpoints/models against live APIs is fiddly (the project's own commits show a dedicated "verify + correct endpoints (2026-06-05)" pass and a live Groq 413 fix).

---

## 5. Calendar-time cost

| Scenario | Wall-clock duration to reach `40166ee` equivalent |
|---|---|
| US team, 3.25 FTE | **5 months** |
| Blended global team, 3.25 FTE | **5.5–6 months** (add timezone coordination overhead) |
| Lean 3-person specialist team | **5.5–7 months** (compiler + multi-provider tails) |
| **Actual (single founder + Claude Opus 4.x)** | **~6.5 weeks** — first commit 2026-04-25 → `40166ee` 2026-06-09, *concurrent with active OnDemand and Pramana work* |

The calendar figure carries the same honest asterisk as v1.0, now larger: these ~6.5 weeks overlapped with ongoing OnDemand *and* Pramana development (the `wegofwd-llm` seam was built once *intending* to serve the family, though on disk only Mentible consumes it). The wall-clock compression is real; the implied single-person-month count is lower than a dedicated-team-month count, and some velocity is **reuse leverage** (the seam is built to amortize across the family, even if the second consumer is still pending).

---

## 6. What was actually spent

| Line item | Estimate |
|---|---|
| Founder time, ~4–5 focused weeks-equivalent (part of a 6.5-week window shared with OnDemand + Pramana) | ~190–260 hours |
| Claude Code subscription / API (intensive) | $300–1,000 |
| Anthropic *token* cost for the product itself | **$0 — BYOK; the user pays the provider directly** |
| Free-provider dev keys (Groq / OpenRouter / Gemini) for live verification | **$0 — free tiers** |
| Fly.io (not yet deployed; scale-to-zero) | ~$0–20 |
| Apple/Google developer accounts (not yet purchased) | $0 so far ($25 + $99/yr at release) |
| Domain / brand (Mentible, pending clearance) | ~$50 |
| **Direct cash outlay** | **~$0.4k–1.1k** |
| Founder opportunity cost @ $300k/yr equivalent × ~1.25 months | **~$31k** |
| **All-in actual cost** | **~$31k–32k** |

The **BYOK structure is still the genuinely novel cost lever**, now reinforced: with multi-provider + *free* providers (Groq/OpenRouter/Gemini), the product's marginal generation cost is borne by the user *and* a learner can run it on a free key — the build and the run both carried zero token cost, and live verification used free tiers.

---

## 7. Headline ratios

| Comparison | US scenario | Blended scenario |
|---|---|---|
| Cash-only multiplier | **~660× cheaper** ($524k ÷ ~$0.8k) | **~225× cheaper** ($179k ÷ ~$0.8k) |
| All-in multiplier (incl. founder opp-cost) | **~16× cheaper** ($524k ÷ $32k) | **~5.6× cheaper** ($179k ÷ $32k) |
| Calendar compression | **~4.3× faster** (~6.5 weeks vs ~5 months) | **~4.6× faster** (~6.5 weeks vs ~5.75 months) |
| Team-size compression | **~3.25× smaller** (1 vs 3.25 FTE) | **~3.25× smaller** |

These land in the same family as v1.0 (~17× US all-in → now ~16×) and the sibling projects (OnDemand 27× US all-in, Thittam 61×, dronePrjs 44×) — still at the lower multiplier end, which is expected and *informative*: Mentible is dominated by two specialist slices (the EPUB3/PDF compiler and the multi-provider seam), and specialist integration work is where AI assistance compresses *less* than on boilerplate CRUD. The all-in multiplier dipped slightly (17×→16×) because the new scope (a packaged seam, multi-provider verification, a security fix) is *more* specialist than the v1.0 baseline, not less.

---

## 8. Honest caveats

- The 16 EM estimate assumes a competent team *with* both ebook-publishing and LLM-integration experience. A team learning EPUB3 or multi-provider conformance on the job burns more; an elite team that has shipped both could hit ~13 EM. Range **13–18 EM** is defensible (was 10–18).
- This is still a **pre-deploy MVP** — never run against a deployed backend (per `docs/STATUS.md`, now stale). Both columns still owe deployment, app-store submission, and on-device verification. (Some *provider* paths are self-reported live-verified — Groq, Anthropic — but that is commit-message provenance, not a deployed E2E.)
- The `wegofwd-llm` package **is** counted (real, shared code Mentible depends on). The separate free reader app (ADR-004), the full managed-key layer, and the Pramana *product* are still excluded from both columns; adding any raises both baselines.
- **Reuse compounds the velocity, and is built to compound further.** The seam was vendored-then-packaged from prior OnDemand work; on disk it serves Mentible, and is designed (ADR-012) to serve Pramana next. Some of the speed is first-party reuse, not AI assistance per se — the two compound, and the package is positioned to amortize one build across multiple consumers even though only one is wired today.
- Equity is excluded from all cash columns; a real team's total comp including equity would be ~30% higher.
- The calendar figure overlapped with OnDemand *and* Pramana work — treat "~6.5 weeks" as wall-clock, not exclusive founder-time.

---

## 9. What this means

The honest comparison is the **all-in multiplier: ~16× cheaper (US) / ~5.6× (blended)**, with a **~4.3× calendar compression**. Those are slightly *lower* than v1.0's, and that's the *informative* result again: the 97-commit window added the two most specialist kinds of work this product has — a publishing-grade compiler (grew) and a multi-provider LLM seam packaged for reuse — and specialist integration is precisely where AI assistance helps but does not collapse the work the way it does on multi-tenant CRUD or test scaffolding. The compression multiplier remains a function of how much of the artifact is well-trodden vs specialist, and this window shifted the mix *toward* specialist.

The more durable observations sharpen too. **Cost structure:** BYOK + *free* providers means the product's most variable cost (LLM tokens) is borne by the user and can be $0 for a learner on a free key; the build carried zero token cost. **Reuse structure:** extracting the provider seam into `wegofwd-llm` packages one ~773-LOC build as a shared-platform investment — a real team would book it as exactly that, and a bootstrapped founder built it once to amortize across the family (Mentible today, Pramana intended). A founder can ship and operate a generative product without ever underwriting inference, and stage the hardest shared slice to amortize once — a strategic advantage independent of any cheaper-and-faster multiplier, though the multi-consumer payoff is realized only when the second consumer ships.

---

*Cost analysis is a point-in-time exercise. Loaded rates, market conditions, and AI tooling capability all evolve. This is a v2.0 pass against a pre-deploy MVP at `40166ee` (branch `main`), with the dependent `wegofwd-llm` package (latest tag `v0.1.1`, 773 LOC / 48 tests; Mentible pins `v0.1.0`) counted. Re-run once the product is deployed and the reader app / full managed-key layer / Pramana product are built, as each will shift the conventional-team baseline. Supersedes v1.0 (2026-06-02 @ `e1c66f7`, ~$435k US / ~$151k blended at ~13 EM).*
