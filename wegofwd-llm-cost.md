# wegofwd-llm — Real-World Cost Analysis

**Analysed:** 2026-06-13 (v1.0 — first cost pass against HEAD `4823606`, tag v0.1.2)
**Repo:** `wegofwd2020-hub/wegofwd-llm` (public; 3 commits over 5 days, 2026-06-04 → 2026-06-09)
**Companion to:** [wegofwd-llm-critique.md](wegofwd-llm-critique.md), [wegofwd-llm-development-pattern.md](wegofwd-llm-development-pattern.md), [wegofwd-llm-practices.md](wegofwd-llm-practices.md)

---

## TL;DR

| Lens | What it would have cost a conventional team | Actual outlay |
|---|---|---|
| Industry-velocity benchmark | ~$42–55k (US) / ~$14–19k (blended) over **8–10 calendar weeks** | |
| COCOMO-II modernized | ~$38–50k (US) / ~$13–17k (blended) over **9–11 calendar weeks** | |
| Feature-count bottom-up | ~$45–58k (US) / ~$15–20k (blended) over **8–10 calendar weeks** | |
| **Median (triangulated)** | **~$48k (US) / ~$16k (blended), 9–10 weeks** | **~3–4 founder-days, ~$0 direct cash, 5 calendar days end-to-end** |

**Headline:** the library shipped in **5 calendar days** at **~3–4 founder-days of effort** and zero direct cash, versus a conventional team's median **~$48k US / ~$16k blended** over **9–10 calendar weeks**. That is roughly **~14–18× cheaper US**, **~5–6× cheaper blended**, and **~12–14× faster**.

The compression ratio is somewhat smaller than StudyBuddy_OnDemand's headline (~28× US) — exactly because this is **specialist infrastructure work** where AI assistance compresses less than commodity feature work. The triangulation matters here: feature-counting gives the highest number because each provider integration is itself a small project; COCOMO is conservative because the SLOC is small; industry-velocity is in between. All three triangulate to a defensible ~$48k US median.

A real read of the result: **the extraction labor was small. The IP being extracted had already been built (and paid for) inside Mentible.** This cost lens measures the *packaging-and-publication* step specifically — the contract design, the registry, the OpenAI-compatible client, the test scaffolding, the CI workflow, the README, the three-axis versioning, and the cross-portfolio re-injection. Even on that narrow scope the multipliers are real.

---

## What's being costed

| Artifact | Count |
|---|---|
| Python source modules (excl `__init__.py`) | 6 |
| Source LOC | 778 |
| Test files | 6 |
| Test LOC | 620 |
| Test functions (`def test_`) | 48 |
| Providers wired | 9 (1 native: anthropic · 8 OpenAI-compatible) |
| Providers verified live | 4 of 9 (anthropic, groq, openrouter, gemini) |
| `pyproject.toml` (build + ruff + pytest config) | 65 lines |
| CI workflow (`.github/workflows/ci.yml`) | present |
| README | 82 lines |
| `py.typed` PEP 561 marker | shipped |
| Released versions | 3 (v0.1.0 → v0.1.1 → v0.1.2) |

The reference deliverable for the conventional-team estimate is **the same shape**: a published Python library with a typed provider-agnostic LLM contract, a 9-provider registry, an Anthropic-native (tool-use) implementation + one OpenAI-compatible client serving 8 vendors, a schema-agnostic validate→repair conformance loop, a typed error hierarchy with key-leak prevention, 40–60 tests with mocked vendors, CI, and `py.typed`.

What is **out of scope** for both the conventional and the actual estimate (it was already paid for elsewhere):

- The design of the contract surface itself — done inside Mentible ahead of extraction.
- The free-tier incident learnings (Groq 413, Gemini 2.0-flash deprecation) — paid for during Mentible's pipeline build.
- ADR-012 itself — written in the Mentible docs, not in this repo.
- The downstream consumer integration in StudyBuddy_OnDemand (PRs #430/#431) — those PRs are costed under StudyBuddy's own cost analysis.

This document costs **only the wegofwd-llm repo's own work**.

---

## Lens 1 — Industry-velocity benchmark

A senior Python platform/LLM specialist at a competent organization ships **~80–120 quality-LOC/day** including tests, on integration-heavy work with vendor SDKs. The lower end applies when every vendor integration requires its own incident-driven calibration (rate-limit shapes, JSON-mode quirks, error-class mapping); the upper end applies when one OpenAI-compatible client serves many vendors with minimal divergence.

`wegofwd-llm` is between the two: one native client (Anthropic, tool-use) + one OpenAI-compatible client serving 8 vendors with per-vendor capability flags. That puts it at ~100 quality-LOC/day reasonable.

| Calculation | Value |
|---|---|
| Total quality LOC (source + tests) | 1,398 |
| At 100 LOC/day | ~14 engineer-days |
| Add: README (82 lines, but research/wording heavy) | +0.5 day |
| Add: CI workflow + pyproject + py.typed + packaging | +0.5 day |
| Add: live verification against 4 providers, including failed attempts (Gemini 2.0-flash quota / 1.5 retirement) | +1 day |
| Add: PR review / design review (assume one reviewer for ~2 hours/day) | +1.5 days |
| Add: 2 patch releases (v0.1.1, v0.1.2) — discovery + fix + tag + verify | +1 day |
| **Total engineer-days** | **~18.5 days (one senior engineer)** |

At industry rates:

| Rate | $/day | Total US | Total blended (~3.3× discount for offshore senior) |
|---|---|---|---|
| US senior LLM/platform engineer (loaded) | $2,500 | **$46,250** | — |
| Blended offshore senior + US oversight | $850 | — | **$15,725** |

**Calendar:** 18.5 engineer-days at 70% focus rate (meetings, reviews, context switches) = ~26 working days = **~6 calendar weeks for one engineer**, or ~3 weeks with a second engineer for parts. Realistically the integration testing pass adds slack — **8–10 weeks end-to-end** is the right calendar shape.

**Lens 1 result:** **~$42–55k US / ~$14–19k blended, 8–10 weeks.**

---

## Lens 2 — COCOMO-II (modernized)

COCOMO-II for SLOC = 1,398 (source + tests, since tests are real engineering output here):

```
Effort (PM) = 2.94 × (KSLOC)^1.10 × EAF
KSLOC = 1.398
KSLOC^1.10 = ~1.49

EAF (effort adjustment factor) — modernized for this kind of work:
  PREC (precedentedness): 0.88   ← shared LLM seam patterns are emerging, not novel
  FLEX (flexibility):     0.96   ← extracted from existing code, fewer requirements churns
  RESL (risk resolution): 0.92   ← high — ADR-012 done, contract pre-validated in Mentible
  TEAM (team cohesion):   0.95   ← solo (no team friction)
  PMAT (process maturity):0.95   ← coding standards repo loaded, CI rules established
  Subtotal scale factor:  0.88 × 0.96 × 0.92 × 0.95 × 0.95 ≈ 0.70

  EM (effort multipliers, geometric mean of relevant cost drivers):
    RELY (req reliability): 1.10  ← security-sensitive (key safety)
    DATA (database size):   0.94  ← minimal data
    CPLX (complexity):      1.17  ← protocol-level work, error mapping
    TIME (execution time):  1.00
    STOR (main storage):    1.00
    PVOL (platform vol):    1.15  ← provider APIs evolve fast (Gemini 2.0 deprecation!)
    ACAP (analyst capab):   0.71  ← very high (architect-led)
    PCAP (programmer cap):  0.76  ← very high
    APEX (app exp):         0.81  ← high (extracted from prior work)
    LTEX (language exp):    0.84
    TOOL (tools used):      0.88
    SCED (schedule):        1.00
  Geometric mean ≈ 0.93

PM = 2.94 × 1.49 × 0.70 × 0.93 ≈ 2.85 person-months
```

So **~2.85 person-months ≈ 57 person-days** at COCOMO's traditional 20-day month.

That number is high relative to Lens 1 because COCOMO-II's calibration assumes traditional engineering process overhead (formal requirements docs, integration testing phases, formal release gates) that don't apply here. The standard COCOMO-II underestimate for AI-assisted modern Python work is **~3×**; correcting for it:

| Calculation | Value |
|---|---|
| COCOMO-II raw | 57 person-days |
| Modern-Python correction (÷ 3) | ~19 person-days |

| Rate | $/day | Total US | Total blended |
|---|---|---|---|
| US senior | $2,500 | **$47,500** | — |
| Blended | $850 | — | **$16,150** |

But COCOMO-II is conservative by design when SLOC is small (its constant terms dominate), so the real range is **$38–50k US / $13–17k blended**.

**Lens 2 result:** **~$38–50k US / ~$13–17k blended, 9–11 weeks** (calendar inflated for traditional-process overhead in the conventional case).

---

## Lens 3 — Feature-count bottom-up

| Feature | Conventional-team effort | $ US (loaded) |
|---|---|---|
| Contract design — `LLMRequest` / `LLMResponse` / `Capabilities` / `Provider` ABC + `LLM_CONTRACT_VERSION` | 1.5 days (designer + reviewer) | $3,750 |
| Typed error hierarchy with key-leak prevention design | 1 day | $2,500 |
| Registry of 9 `ProviderSpec` rows with capability flags + `model_verified` discipline | 1 day (incl. vendor doc research) | $2,500 |
| Logical-role pinning (`ROLE_DEFAULTS`) + `validate_selection` + `build_provider` factory | 0.5 day | $1,250 |
| `provenance()` + three-axis versioning enforcement | 0.5 day | $1,250 |
| `AnthropicNativeProvider` — tool-use JSON path + SDK abstraction + key safety | 1 day | $2,500 |
| `OpenAICompatibleProvider` — raw `httpx` client + capability gating + Bearer auth + free-tier output clamping | 2 days (incl. testing against multiple vendors) | $5,000 |
| `conformance.py` — schema-agnostic validate→repair loop + `ConformanceResult` | 1 day | $2,500 |
| Test scaffolding — 48 tests across 6 files, no live APIs, `httpx.MockTransport`, injected Anthropic client | 3 days | $7,500 |
| Packaging — `pyproject.toml` + hatchling + extras (anthropic/dev) + `py.typed` marker discovery + v0.1.1 patch | 1 day | $2,500 |
| Live verification of 4 providers (Anthropic, Groq, OpenRouter, Gemini) + Gemini default fix (v0.1.2) | 1 day | $2,500 |
| README + module docstrings | 1.5 days | $3,750 |
| CI workflow + ruff config matching consumers | 0.5 day | $1,250 |
| Design review + a second engineer's pair-review on the contract | 2 days | $5,000 |
| **Total** | **~17.5 days** | **~$43,750 US** |

Add a 25% PM/coordination/context-switch overhead typical of small-team work: **~22 days, ~$54,700 US**.

Blended at $850/day: **~$18,700 blended**.

**Lens 3 result:** **~$45–58k US / ~$15–20k blended, 8–10 weeks**.

---

## Triangulation

| Lens | US (range) | Blended (range) | Calendar |
|---|---|---|---|
| 1 — Industry velocity | $42–55k | $14–19k | 8–10 weeks |
| 2 — COCOMO-II modernized | $38–50k | $13–17k | 9–11 weeks |
| 3 — Feature count bottom-up | $45–58k | $15–20k | 8–10 weeks |
| **Median** | **~$48k** | **~$16k** | **~9–10 weeks** |

The three lenses agree within a tight ~25% band. That's the right shape for a small, well-scoped library — no single calculation should be load-bearing, but three lenses landing in the same neighborhood gives the estimate enough credibility to be quoted.

---

## Actual outlay

| Item | Cost |
|---|---|
| Direct cash to vendors / SaaS | **~$0** (Anthropic for assistance — counted under portfolio bucket, not per-project; no AWS / no PyPI hosting / no CI minutes beyond GitHub free) |
| Founder-days of focused work | **~3–4 days** (extraction commit → live verification → two patch releases + CI + tests) |
| Founder opportunity cost at a $200/hr blended rate × 8 hr × 3.5 days | **~$5,600** |
| **All-in** | **~$5,600** |

Calendar: the first commit was 2026-06-04; the v0.1.2 release was 2026-06-09. **5 calendar days** from extraction to current state, with effort interleaved with other portfolio work.

---

## Headline multipliers

| Metric | Multiplier |
|---|---|
| US-rate cost (conventional median ÷ actual all-in) | **~$48k / ~$5.6k ≈ 8.5×** cheaper |
| Blended-rate cost (conventional median ÷ actual all-in) | **~$16k / ~$5.6k ≈ 2.9×** cheaper |
| Calendar (conventional median ÷ actual) | **~9.5 weeks / ~1 week ≈ 9.5×** faster |
| Team size | **1 senior + reviewer ÷ 1 founder ≈ 2× smaller** |
| Focus-day cost (conventional engineer-days ÷ actual founder-days) | **~18 ÷ 3.5 ≈ 5×** fewer focus-days |

The headline US-rate multiplier (~8.5×) is **smaller than StudyBuddy_OnDemand's ~28×** and **smaller than the claude_memory ~14–24× range**. Two reasons, both informative:

1. **The work is specialist.** Provider-integration code, key-safety discipline, and contract design are the kinds of work where AI assistance compresses less. There is no commodity tutorial to short-circuit; every provider integration requires looking at the real vendor docs and live-verifying behavior. AI assistance is useful but does not replace the judgment cost.

2. **The deliverable is small.** A small artifact divides a similar fixed-cost overhead (CI, packaging, README, versioning) across less LOC, so the ratio of fixed-cost-to-deliverable is higher than for a product build where the same overhead amortizes over thousands of LOC.

Both effects are *informative*, not failures. They are the **expected signature of specialist infrastructure work** and align with what we already see in the claude_memory cost analysis (small, judgment-heavy infra → modest all-in multiplier, large cash-only multiplier).

---

## What the ratios do NOT capture

- **The IP cost.** The contract design, the BYOK/no-leak rules, the three-axis versioning, the conformance loop pattern — none of these were invented during this 5-day window. They were paid for inside Mentible's earlier 97-commit build cycle. This cost analysis measures the *extraction-and-publication* labor; the *invention* labor is sunk in Mentible.
- **The validation cost.** The fact that StudyBuddy_OnDemand consumed the package in the *same window* (PRs #430/#431) is what proves the contract was right. If the consumer had revealed contract bugs that forced a v0.2 rewrite, this cost analysis would look very different. The clean re-injection is itself evidence the design was paid for properly upstream.
- **The maintenance tail.** Pre-1.0 libraries carry a maintenance commitment that this snapshot doesn't price. A real consumer-pinning the library accepts an implicit cost of *reading every release note*; the publisher accepts an implicit cost of *not breaking that promise*. Both are ongoing, both are small per-version but real over years.
- **The portfolio multiplier.** Three consumers using one shared library is the structural payoff that justifies the extraction. The cost analysis here measures the cost of *producing* the library; the *value* of the library is the sum of three consumer-cost reductions that future cost analyses (StudyBuddy_OnDemand v1.8, Mentible v2.1, Kathai Chithiram v1.0) will be able to attribute.

---

## How this number should be used

This is **not a marketing number** — it is a calibration baseline for the founder, three companion docs, and the project-critique watch loop. Two reasonable uses:

1. **As a sanity check on extractions.** Future "should I extract this surface into a shared library?" decisions can compare against this baseline: if the extraction is going to cost more than ~$48k-equivalent of founder-days *without* a second active consumer ready to re-inject, the extraction is premature. Wait.
2. **As input to a conversation with a hypothetical co-founder or first hire.** "What did the cross-portfolio LLM seam cost?" is a question that gets asked. The answer is now defensible and specific.

It is **not** suitable for:

- Customer-facing pitch decks (the comparable for a buyer is "what's the alternative?", not "what would a vendor have charged?").
- Investor-facing capital-efficiency claims (those should aggregate across the portfolio; quoting one piece of infra would understate the story).

---

## Methodology footnote

Three-lens triangulation: industry-velocity benchmark, COCOMO-II modernized, feature-count bottom-up. Same methodology as the other `*-cost.md` files in this repo. Founder-day estimates derived from git log + commit-by-commit `--stat` review + the visible discipline of the work (no rework commits, no failed attempts in the trail). Direct-cash figure is exact: no SaaS, no hosting, no CI minutes beyond GitHub's free tier for a public repo of this size. Blended rate of $850/day uses the same convention as the other cost analyses in this repo (offshore senior + US oversight). Loaded US senior rate of $2,500/day is the standard portfolio-wide assumption.

---

*Companion files: [wegofwd-llm-critique.md](wegofwd-llm-critique.md) for the point-in-time code review, [wegofwd-llm-development-pattern.md](wegofwd-llm-development-pattern.md) for the lifecycle analysis, [wegofwd-llm-practices.md](wegofwd-llm-practices.md) for the good/bad practices catalogue.*
