# wegofwd-video — Real-World Cost Analysis

**Analysed:** 2026-07-01 (v1.0 — first cost pass against HEAD `233f248`, tag v1.0.0)
**Reviewer:** Claude (Anthropic)
**Repo:** `wegofwd2020-hub/wegofwd-video` (4 commits, all on 2026-06-30: scaffold → py3.10 bump → live Veo call → v1.0 freeze)
**Companion to:** [wegofwd-video-critique.md](wegofwd-video-critique.md), [wegofwd-video-development-pattern.md](wegofwd-video-development-pattern.md), [wegofwd-video-practices.md](wegofwd-video-practices.md)

---

## TL;DR

| Lens | What it would have cost a conventional team | Actual outlay |
|---|---|---|
| Industry-velocity benchmark | ~$38–48k (US) / ~$13–16k (blended) over **7–9 calendar weeks** | |
| COCOMO-II modernized | ~$33–42k (US) / ~$11–14k (blended) over **8–10 calendar weeks** | |
| Feature-count bottom-up | ~$42–52k (US) / ~$14–18k (blended) over **7–9 calendar weeks** | |
| **Median (triangulated)** | **~$42k (US) / ~$14k (blended), ~8 weeks** | **~1–2 founder-days, ~$0 direct cash, ONE calendar day end-to-end** |

**Headline:** the library shipped in **one calendar day** at **~1–2 founder-days of effort** and zero direct cash, versus a conventional team's median **~$42k US / ~$14k blended** over **~8 calendar weeks**. That is roughly **~17× cheaper US**, **~6× cheaper blended**, and **~40× faster**.

Two things make this profile different from its sibling [wegofwd-llm](wegofwd-llm-cost.md) (~$48k US / ~$16k blended, 5 days, ~8.5× US). First, the **conventional figure is slightly lower** — this is a smaller artifact (1,103 total LOC vs 1,398; 30 tests vs 48; 4 providers vs 9), even though it *adds* a genuinely harder dimension (a long-running submit→poll→download job path with a deadline). Second, the **actual founder cost is much lower** (~1.5 founder-days vs 3.5), which pushes the cost multiplier *up* (~17× vs ~8.5×) and the time multiplier *way up* (~40× vs ~12×). That is not because wegofwd-video is "cheaper to build from scratch" than wegofwd-llm — it is because **almost all of the hard design work was amortized**: the registry / spec / role-routing / `build_provider` / typed-error-hierarchy / provenance / three-axis-versioning / ruff config are all cloned verbatim from wegofwd-llm, and the interface had been pre-validated against both consumers in [`story-video-template`](story-video-template) before a line was written. The large multiplier is the *signature of a derivative extraction*, and this document is careful to label it as such rather than bank it as raw productivity.

**Honesty caveat up front:** a portion of the "delivered" scope is **interface-only and still unproven**. The Veo live call is wired (submit→poll→download, 600s deadline) but **has never been run against a real key**; `runway` and `kling` are **UNVERIFIED spec-only placeholders**; and Veo reference-image (Ingredients-to-Video) wiring is **deferred** (it fails loudly rather than silently). So the conventional counterfactual below prices the work a specialist *would* have to do to reach the same frozen contract — including live verification the founder has not yet paid for. The actual-outlay column prices only what was actually done. This asymmetry is called out again in the caveats.

---

## What's being costed

| Artifact | Count |
|---|---|
| Python source modules (excl `__init__.py`) | 5 (`contract`, `errors`, `registry`, `providers/veo`, `providers/local_render`) |
| Source LOC | 741 |
| Test files | 5 |
| Test LOC | 362 |
| Test functions (`def test_`) | 30 |
| Providers registered | 4 (`veo`, `deterministic-renderer`, `runway`, `kling`) |
| Providers actually wired | 2 (`veo` = live call wired, docs-verified; `deterministic-renderer` = functional) |
| Providers placeholder-only | 2 (`runway`, `kling` = UNVERIFIED spec rows) |
| Providers verified *live* | 0 of 4 (Veo docs-verified, first real run still pending) |
| JSON schema (`schema/video_brief.v1.json`) | 1 |
| `pyproject.toml` (build + ruff + pytest config) | 62 lines |
| README | 99 lines |
| `py.typed` PEP 561 marker | shipped |
| Decision record | ADR-026 (substantial; lives in StudyBuddy_SelfLearner docs) |
| Released versions | 3 (v0.1.1 → v0.1.2 → v1.0.0) |

The reference deliverable for the conventional-team estimate is **the same shape**: a published Python library with a typed, frozen-dataclass, provider-agnostic video contract (`VideoBrief`/`Shot`/`Ingredient` → `VideoRequest`/`VideoResult`, `VideoProvider` ABC, `VIDEO_CONTRACT_VERSION`), a provider registry with capability rows + role routing + allowlist-before-construction, a capability pre-check that reports **every** violation before dispatch, a typed error hierarchy with key-leak discipline (`raise … from None`, generic messages, HTTP-code-based mapping), a **long-running-job provider** (Veo submit→poll→download with a 600s deadline and a lazy optional `[veo]` SDK import), a caller-injected deterministic-renderer seam, one JSON schema, 30 tests with no live APIs, `py.typed`, and the ADR that justifies it.

What is **out of scope** for both the conventional and the actual estimate (it was already paid for elsewhere):

- **The design of the seam pattern itself** — the registry / spec / role / `build_provider` / error-hierarchy / provenance / versioning shape was invented and paid for in **wegofwd-llm** and simply cloned here. This is the single biggest reason the build took a day; it is explicitly *not* re-charged.
- **The content contract + Veo prompt template** — designed in [`project-critique/story-video-template`](story-video-template) ahead of extraction, and pre-validated against both consumers (pramana + kathai-chithiram). That validation is what let the interface freeze at v1.0 on day one.
- **ADR-026's decision-making** — the deliberation lives in the StudyBuddy_SelfLearner docs, not this repo; the *writing* of it is counted, the *deciding* is sunk.
- **Downstream consumer integration** — pramana (`veo`) and kathai-chithiram (`deterministic-renderer`) wiring is costed under those products' own analyses.

This document costs **only the wegofwd-video repo's own extraction-and-publication work**, on the same basis as [wegofwd-llm-cost.md](wegofwd-llm-cost.md).

---

## Lens 1 — Industry-velocity benchmark

A senior Python platform/media specialist at a competent organization ships **~80–120 quality-LOC/day** including tests on integration-heavy work with vendor SDKs. Video generation sits at the harder end of that band: a **long-running operation** (submit an op, poll to a deadline, then fetch the asset bytes, all key-free) is more finicky than a synchronous request/response, and there is no single OpenAI-compatible client to amortize across providers. Against that, two of the four providers here are thin placeholder rows (near-zero code), and the deterministic-renderer is a small caller-injected shim. Netting the polling complexity against the placeholder discount lands at **~100 quality-LOC/day** — the same figure used for wegofwd-llm, which keeps the two libraries directly comparable.

| Calculation | Value |
|---|---|
| Total quality LOC (source + tests) | 1,103 |
| At 100 LOC/day | ~11 engineer-days |
| Add: Veo long-running-job integration (submit/poll/download + 600s deadline + error taxonomy) **and** first live verification against a real key | +1 day |
| Add: README (99 lines, research/wording heavy) | +0.5 day |
| Add: pyproject + hatchling + `[veo]` extra + `py.typed` + py3.10 bump (v0.1.1) | +0.5 day |
| Add: ADR-026 (substantial decision record) | +1 day |
| Add: PR review / design review (one reviewer, ~2 hr/day) | +1.5 days |
| Add: two pre-1.0 releases (v0.1.2) + the v1.0 freeze gate | +1 day |
| **Total engineer-days** | **~16.5 days (one senior engineer)** |

At industry rates:

| Rate | $/day | Total US | Total blended |
|---|---|---|---|
| US senior media/platform engineer (loaded) | $2,500 | **$41,250** | — |
| Blended offshore senior + US oversight | $850 | — | **$14,025** |

**Calendar:** 16.5 engineer-days at 70% focus (meetings, reviews, context switches) = ~24 working days = **~5 calendar weeks** for one engineer. The live-verification pass against a real Veo key (quota, long-poll latency, asset download) adds real slack — **7–9 weeks end-to-end** is the right calendar shape.

**Lens 1 result:** **~$38–48k US / ~$13–16k blended, 7–9 weeks.**

---

## Lens 2 — COCOMO-II (modernized)

COCOMO-II for SLOC = 1,103 (source + tests, since the 30 tests are real engineering output and the conformance gate):

```
Effort (PM) = 2.94 × (KSLOC)^1.10 × EAF
KSLOC = 1.103
KSLOC^1.10 = ~1.11

EAF (effort adjustment factor) — modernized for this kind of work:
  PREC (precedentedness): 0.85   ← MORE precedented than wegofwd-llm; the seam pattern is cloned, not emerging
  FLEX (flexibility):     0.96   ← extracted from a pre-validated interface, minimal churn
  RESL (risk resolution): 0.90   ← very high — ADR-026 D7 gate met, contract validated vs BOTH consumers
  TEAM (team cohesion):   0.95   ← solo (no team friction)
  PMAT (process maturity):0.95   ← standards + ruff config inherited from wegofwd-llm
  Subtotal scale factor:  0.85 × 0.96 × 0.90 × 0.95 × 0.95 ≈ 0.66

  EM (effort multipliers, geometric mean of relevant cost drivers):
    RELY (req reliability): 1.10  ← security-sensitive (BYOK key safety, no-leak discipline)
    DATA (database size):   0.94  ← minimal data
    CPLX (complexity):      1.18  ← protocol-level + long-running-job polling + error mapping
    TIME (execution time):  1.00
    STOR (main storage):    1.00
    PVOL (platform vol):    1.15  ← video vendor APIs evolve fast (Veo/Runway/Kling all moving)
    ACAP (analyst capab):   0.71  ← very high (architect-led)
    PCAP (programmer cap):  0.76  ← very high
    APEX (app exp):         0.80  ← very high (cloned from prior work)
    LTEX (language exp):    0.84
    TOOL (tools used):      0.88
    SCED (schedule):        1.00
  Geometric mean ≈ 0.93

PM = 2.94 × 1.11 × 0.66 × 0.93 ≈ 2.0 person-months
```

So **~2.0 person-months ≈ 40 person-days** at COCOMO's traditional 20-day month.

As with wegofwd-llm, that number is high relative to Lens 1 because COCOMO-II's calibration assumes traditional-process overhead (formal requirements docs, integration-testing phases, formal release gates) that does not apply to AI-assisted modern Python. The standard COCOMO-II underestimate-correction for this kind of work is **~3×**; applying it:

| Calculation | Value |
|---|---|
| COCOMO-II raw | 40 person-days |
| Modern-Python correction (÷ 3) | ~13.3 person-days |

| Rate | $/day | Total US | Total blended |
|---|---|---|---|
| US senior | $2,500 | **$33,250** | — |
| Blended | $850 | — | **$11,300** |

COCOMO-II is conservative by design when SLOC is small (its constant terms dominate a sub-1.2-KSLOC library), so the real range is **$30–42k US / $10–14k blended**.

**Lens 2 result:** **~$33–42k US / ~$11–14k blended, 8–10 weeks** (calendar inflated for traditional-process overhead in the conventional case).

---

## Lens 3 — Feature-count bottom-up

| Feature | Conventional-team effort | $ US (loaded) |
|---|---|---|
| Contract design — frozen `VideoBrief`/`Shot`/`Ingredient` + `VideoRequest`/`VideoResult`/`VideoCapabilities` + `VideoProvider` ABC + `VIDEO_CONTRACT_VERSION` | 1.5 days (designer + reviewer) | $3,750 |
| Typed error hierarchy with key-leak discipline (`raise … from None`, generic messages, HTTP-code mapping) | 1 day | $2,500 |
| Registry of 4 `VideoProviderSpec` rows w/ capability flags + `model_verified` + allowlist | 1 day (incl. vendor-doc research) | $2,500 |
| Role routing (`ROLE_DEFAULTS`) + `resolve_role` + `validate_selection` + `build_provider` factory + allowlist-before-construction | 0.75 day | $1,875 |
| Capability pre-check reporting *every* violation (`assert_brief_within_capabilities`) | 0.5 day | $1,250 |
| `provenance()` + seed + three-axis versioning enforcement | 0.5 day | $1,250 |
| `VeoProvider` — long-running job: submit→poll→download, 600s deadline, `build_request` shaping, `render_brief_text`, lazy `[veo]` SDK import, HTTP-code error mapping | 2.5 days (incl. reading google-genai docs) | $6,250 |
| Deterministic-renderer seam (`CallableRenderProvider`, caller-injected render fn, no key) | 0.5 day | $1,250 |
| `video_brief.v1.json` schema | 0.5 day | $1,250 |
| Test scaffolding — 30 tests across 5 files, no live APIs, injected client double | 2 days | $5,000 |
| Packaging — `pyproject.toml` + hatchling + `[veo]` extra + `py.typed` + py3.10 bump (v0.1.1) | 0.75 day | $1,875 |
| Veo live verification against a real key (submit/poll/download end-to-end) | 1 day | $2,500 |
| ADR-026 (substantial decision record) | 1 day | $2,500 |
| README + module docstrings | 1 day | $2,500 |
| Design review + a second engineer's pair-review on the contract | 1.5 days | $3,750 |
| **Total** | **~16 days** | **~$40,000 US** |

Add a 25% PM/coordination/context-switch overhead typical of small-team work: **~20 days, ~$50,000 US**.

Blended at $850/day: **~$17,000 blended**.

As with wegofwd-llm, feature-counting gives the **highest** of the three lenses — each provider integration and the long-running-job path are each a small project in their own right, and bottom-up counting does not get the amortization discount that COCOMO's scale factors apply.

**Lens 3 result:** **~$42–52k US / ~$14–18k blended, 7–9 weeks.**

---

## Triangulation

| Lens | US (range) | Blended (range) | Calendar |
|---|---|---|---|
| 1 — Industry velocity | $38–48k | $13–16k | 7–9 weeks |
| 2 — COCOMO-II modernized | $33–42k | $11–14k | 8–10 weeks |
| 3 — Feature count bottom-up | $42–52k | $14–18k | 7–9 weeks |
| **Median** | **~$42k** | **~$14k** | **~8 weeks** |

The three lenses agree within a ~25% band, the same tightness as wegofwd-llm's. COCOMO sits lowest (small-SLOC conservatism), feature-count sits highest (no amortization credit), velocity sits in between — exactly the ordering seen for wegofwd-llm. All three triangulate to a defensible **~$42k US / ~$14k blended, ~8 weeks** — a touch below wegofwd-llm's ~$48k / ~$16k, which is the right relationship for a slightly smaller library that nonetheless carries the extra long-running-job dimension.

---

## Actual outlay

| Item | Cost |
|---|---|
| Direct cash to vendors / SaaS | **~$0** (Anthropic assistance counted under the portfolio bucket, not per-project; **no live Veo run means no vendor spend**; no AWS / no PyPI hosting / no CI minutes) |
| Founder-days of focused work | **~1–2 days** (scaffold → py3.10 bump → live-call wiring → v1.0 freeze, all on 2026-06-30) |
| Founder opportunity cost at a $200/hr blended rate × 8 hr × ~1.5 days | **~$2,400** |
| **All-in** | **~$2,400** |

Calendar: all four commits landed on **2026-06-30** — **one calendar day** from scaffold to a frozen v1.0.0 interface, effort interleaved with other portfolio work.

The founder-day figure is **lower than wegofwd-llm's ~3–4 days** for a concrete, verifiable reason: wegofwd-llm had to *invent* the registry/spec/role/error/provenance/versioning pattern; wegofwd-video **cloned it verbatim** and only needed (a) domain-specialization of the contract to briefs/shots/ingredients, (b) the one genuinely new piece of engineering — the Veo submit→poll→download long-running-job path — and (c) the two placeholder provider rows. The git trail shows no rework commits and no failed attempts, consistent with a pattern that was already de-risked upstream.

---

## Headline multipliers

| Metric | Multiplier |
|---|---|
| US-rate cost (conventional median ÷ actual all-in) | **~$42k / ~$2.4k ≈ 17×** cheaper |
| Blended-rate cost (conventional median ÷ actual all-in) | **~$14k / ~$2.4k ≈ 6×** cheaper |
| Calendar (conventional median ÷ actual) | **~8 weeks / ~1 day ≈ 40×** faster |
| Team size | **1 senior + reviewer ÷ 1 founder ≈ 2×** smaller |
| Focus-day cost (conventional engineer-days ÷ actual founder-days) | **~16 ÷ ~1.5 ≈ 11×** fewer focus-days |

The US-rate multiplier (~17×) is **larger** than wegofwd-llm's (~8.5×), and the time multiplier (~40×) is much larger. Both are driven by the *same* thing, and it is important to read it correctly:

1. **The large multipliers are a derivative discount, not raw productivity.** wegofwd-video is *not* fundamentally 2× easier to build from scratch than wegofwd-llm — the conventional counterfactuals are within ~15% of each other. The gap is almost entirely in the *actual* column: ~1.5 founder-days vs ~3.5, because the expensive design work (the seam pattern) was already amortized in wegofwd-llm and the interface was pre-validated in `story-video-template`. If you were to *re-attribute* a fair share of wegofwd-llm's original design cost to this library, the multiplier would collapse toward wegofwd-llm's ~8.5×. The honest reading is: **this is the second pull from a mold that was expensive to cut once and is nearly free to reuse.**

2. **The ~40× "faster" figure is inflated for exactly that reason.** A one-day build against an ~8-week conventional counterfactual produces a spectacular ratio precisely because the hard, slow design phase happened *before* the clock started. It is a real number, but it measures *reuse leverage*, not a repeatable from-cold velocity.

3. **The work is still specialist.** The one piece that was genuinely new here — a long-running submit→poll→download job with a deadline, key-free error mapping, and a lazy optional SDK import — is at least as specialist as multi-provider LLM work. AI assistance compresses it, but does not eliminate the judgment cost. This is the same "specialist infra compresses less" signature seen in wegofwd-llm and claude_memory.

---

## What the ratios do NOT capture

- **A chunk of the delivered scope is unproven.** The Veo live call has **never been run** — `model_verified` stays docs-verified, not live-verified; `runway` and `kling` are **UNVERIFIED spec-only placeholders**; Ingredients-to-Video wiring is **deferred** (it raises rather than silently drops). The conventional counterfactual prices the live-verification a specialist *would* do; the actual column does not include it because it hasn't happened yet. So the real all-in for a *fully proven* library is higher than ~$2,400 — the first live Veo run, the two placeholder integrations, and the Ingredients path are **future cost, not banked cost**. The multipliers above are for the frozen-interface milestone, not a battle-tested integration.
- **The IP cost.** The seam pattern (registry/spec/roles/`build_provider`/error-hierarchy/provenance/three-axis versioning) was invented and paid for in wegofwd-llm. This analysis measures *domain-specialization + long-running-job wiring*; the *pattern-invention* labor is sunk in wegofwd-llm and should not be double-counted here — nor should its leverage be booked here as if it were free forever.
- **The validation cost.** The contract froze at v1.0 on day one because it had been pre-validated against **both** consumers in `story-video-template` and both are merged (ADR-026 D7 gate). Had a consumer revealed a contract bug forcing a v2 rewrite, this analysis would look very different. The clean freeze is evidence the design was paid for properly upstream.
- **The maintenance tail.** A pre-frozen-but-unrun integration carries an *especially* real maintenance commitment: the first live Veo run may surface response-shape or polling-behavior surprises that the docs-verified path did not anticipate. That is an accepted, unpriced liability of shipping a wired-but-unrun provider.
- **The portfolio multiplier.** Two consumers on two provider paths (pramana=`veo`, kathai=`deterministic-renderer`) is the structural payoff that justifies the extraction. This document costs *producing* the library; the *value* is the sum of consumer-cost reductions their own analyses will attribute.

---

## How this number should be used

This is **not a marketing number** — it is a calibration baseline for the founder, three companion docs, and the project-critique watch loop. Two reasonable uses:

1. **As a sanity check on the "clone-the-seam" play.** The genuinely interesting datapoint here is *how cheap the second extraction is once the first mold exists* (~1.5 founder-days vs ~3.5). Future "should I spin up another `wegofwd-*` shared library?" decisions can use ~1–2 founder-days as the marginal cost **provided** a validated interface and a live consumer exist — and should treat a *from-cold* new pattern as costing more like wegofwd-llm's 3–4 days.
2. **As input to a conversation with a hypothetical co-founder or first hire.** "What did the cross-portfolio video seam cost?" now has a defensible, specific answer — with the derivative-discount and the unproven-scope caveats attached, so it is not oversold.

It is **not** suitable for:

- Customer-facing pitch decks (the buyer's comparable is "what's the alternative?", not "what would a vendor have charged?").
- Investor-facing capital-efficiency claims (those should aggregate across the portfolio; quoting one derivative piece of infra with a wired-but-unrun provider would overstate the story).

---

## Methodology footnote

Three-lens triangulation: industry-velocity benchmark, COCOMO-II modernized, feature-count bottom-up — the **same methodology, rates, and US-vs-blended convention** as [wegofwd-llm-cost.md](wegofwd-llm-cost.md), so the two libraries are directly comparable on one scale. Loaded US senior rate: **$2,500/day**; blended (offshore senior + US oversight): **$850/day** — both portfolio-wide constants. Founder-day estimate derived from the git log (4 commits, all 2026-06-30, no rework/failed-attempt commits) + module-by-module review of the 741 source / 362 test LOC + the visible discipline of the work. Direct-cash figure is exact: no SaaS, no hosting, no CI minutes, and — because the Veo live call has not been run — no vendor inference spend. The large headline multipliers are explicitly attributed to a **derivative extraction** (cloned seam + pre-validated interface), not to raw from-cold velocity, and a portion of delivered scope is flagged as **interface-only / unproven**.

---

*Companion files: [wegofwd-video-critique.md](wegofwd-video-critique.md) for the point-in-time code review, [wegofwd-video-development-pattern.md](wegofwd-video-development-pattern.md) for the lifecycle analysis, [wegofwd-video-practices.md](wegofwd-video-practices.md) for the good/bad practices catalogue.*
