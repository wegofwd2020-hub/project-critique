# MarketingTools — Real-World Cost Analysis

**Analysed:** 2026-06-09 (v1.0 — first cost pass, measured on disk at branch `main` @ `76addee`)
**Repo:** `MarketingTools` (`/home/sivam/Documents/code/projects/AIStuff/STEM_studybuddy/MarketingTools`)
**Reviewer:** Claude (Anthropic)
**Question being answered:** if this same toolkit had been built by a conventional team in the real world (not by a single founder with Claude-assisted execution), what would it have cost in money and calendar time?
**Scope of measurement:** code on disk at `76addee` — a **small, working internal toolkit**: a copy generator (`generate.py`), a multi-brand python-pptx deck engine (`decks/`), an asset library + brand rules (`assets/`), and a CRM-lite outreach log (`campaigns/`). The `landing/` builder is an explicit stub and is **excluded** from both columns. The `.venv-decks/` virtualenv is excluded from all LOC measurements.
**Related:** [MarketingTools-critique.md](MarketingTools-critique.md) · [MarketingTools-development-pattern.md](MarketingTools-development-pattern.md) · [MarketingTools-practices.md](MarketingTools-practices.md)

> This is a small tool. The numbers below are deliberately proportionate — a few engineer-weeks, not a six-figure platform. Inflating a 2.3k-LOC personal toolkit into a big headline would be the opposite of the honest, evidence-based read this exercise is for.

---

## 1. What's actually been built

Measured directly from the repository (`76addee`; first commit 2026-06-01 → last 2026-06-09 = **~8 calendar days**, 4 commits, sole-author, `.venv-decks` excluded).

| Slice | Measure |
|---|---|
| Copy generator (`generate.py`) | **173 LOC** — argparse CLI; loads `products.yaml` + concatenated `brand/*.md`; framing-resolution heuristic; `(product × audience × channel × framing)` → scoped prompt; `--list` / `--dry-run` (no-key paths); lazy `anthropic` SDK call |
| Deck engine (`decks/theme.py`) | **437 LOC** — a python-pptx layout library: 7 slide layouts (title/content/columns/flow/table/statement/closing) over a `Brand` dataclass + `set_brand()` multi-brand switch (Mentible + Pramana, logo-or-wordmark fallback) |
| Deck content (`build_decks.py` + `build_pramana.py`) | **886 + 294 = 1,180 LOC** — four complete pitch decks (Mentible investor/architect/author + Pramana buyer), ~60 slides total with speaker notes, sourced from `products.yaml` and the product docs |
| Asset library (`assets/products.yaml`) | **130 LOC** — the source-of-truth registry: products, taglines, links, proof points, audiences, two framings each; `home:` portfolio taxonomy |
| Brand rules (`assets/brand/*.md`) | **44 LOC** — injected into every generation (the "current is load-bearing" rule, voice, compliance signals) |
| Outreach log (`campaigns/`) | CRM-lite CSV (6 rows) + a column-semantics/status-ladder README |
| Templates / docs | WhatsApp invite template + six READMEs/notes (incl. the `landing/` stub plan) |
| Tests | **0** |
| **Total project source** | **~1,790 Python LOC + ~484 data/docs LOC = ~2,274 LOC**, 22 non-venv files |

The cost-defining slices are two: the **deck engine + four hand-built decks** (~1,617 LOC, the bulk of the toolkit — and the part with real visual-design and python-pptx fiddliness) and the **copy generator + asset library** (~347 LOC, small but it's the conceptual core).

---

## 2. Methodology — triangulated three ways

This is small enough that all three methods land within a tight band.

1. **Industry-velocity benchmark.** Decompose into what a competent team would actually scope:
   - A thin LLM-backed CLI over a YAML registry with a dry-run/list mode, env-based secrets, and a framing heuristic: **~1.0–1.5 engineer-weeks** (it's a small, well-trodden CLI).
   - A reusable python-pptx brand/theme engine (7 layouts, multi-brand switch, logo fallback): **~1.5–2.0 EW** (slide-layout geometry in python-pptx is fiddly hand-work; the first such engine always overruns the estimate).
   - Four hand-built, on-message pitch decks with speaker notes (content + assembly, even with the engine in hand): **~1.5–2.0 EW** (this is design/copy time as much as code time).
   - The asset library + brand rules + campaign-log scaffolding + the six docs: **~0.5–1.0 EW**.
   - **Net ~4.5–6.5 engineer-weeks ≈ ~1.1–1.6 engineer-months.**
2. **COCOMO-II modernized (sanity check, not anchor).** At ~2.27 KLOC, raw organic COCOMO (`2.4 × KLOC^1.05`) ≈ **~5.7 EM** — but COCOMO is a poor fit below ~5 KLOC and *over*-weights small glue tools badly; applying a 0.25 framework/scripting-productivity multiplier ⇒ **~1.4 EM**, consistent with the velocity benchmark. Treat COCOMO here as a loose corroboration, not a driver.
3. **Feature-counting.** Generator (CLI + prompt assembly + framing logic + dry-run/list) ~1 EW; theme engine ~2 EW; 4 decks ~2 EW; assets + brand + log + docs ~0.75 EW ⇒ **~5.75 EW ≈ ~1.4 EM.**

**Convergence: ~1–1.6 engineer-months is the defensible range.** Point estimate **~1.3 EM** (≈ **5.5 engineer-weeks**). This is a tool, not a product — the estimate is sized to match.

---

## 3. Team composition

A real team would staff this with a fraction of one person plus a sliver of design. No security review line (no BYOK, no server, no PII store — just a personal env var) and no QA line beyond the developer's own.

| Role | FTE-equiv over the build | Why needed for this artifact |
|---|---|---|
| Mid/Senior Python engineer | 0.8 | The generator, the python-pptx theme engine, the asset/registry plumbing |
| Designer / marketer (part-time) | 0.3 | Deck visual identity, the copy/positioning in the four decks, brand rules |
| **Total** | **~1.1 FTE** | for ~5–6 weeks |

---

## 4. Cost scenarios

### Scenario A — US tech labour market (Bay Area / NYC / Seattle blended, 2025–2026 loaded rates)

Loaded rates are fully burdened (salary + benefits + employer taxes + tooling). At **~5.5 engineer-weeks** of effort:

| Role | Loaded $/yr | Weeks | Cost |
|---|---|---|---|
| Mid/Senior Python engineer | $300k | 4.4 (0.8 FTE × 5.5 wk) | $25k |
| Designer / marketer | $230k | 1.65 (0.3 FTE × 5.5 wk) | $7k |
| **People subtotal** | | | **$32k** |
| Tooling / SaaS (GitHub, Figma, an Anthropic dev key) | | | $1k |
| **Scenario A total** | | | **~$33k** |

*(Arithmetic: $300k/yr ÷ 52 ≈ $5,769/wk × 4.4 wk ≈ $25k; $230k/yr ÷ 52 ≈ $4,423/wk × 1.65 wk ≈ $7k.)*

### Scenario B — Blended global (India tier-1 / EU senior contractors)

| Role | Loaded $/yr | Weeks | Cost |
|---|---|---|---|
| Mid/Senior Python engineer | $85k | 4.4 | $7.2k |
| Designer / marketer | $55k | 1.65 | $1.7k |
| **People subtotal** | | | **$8.9k** |
| Tooling / SaaS | | | $1k |
| **Scenario B total** | | | **~$10k** |

*(Arithmetic: $85k ÷ 52 ≈ $1,635/wk × 4.4 ≈ $7.2k; $55k ÷ 52 ≈ $1,058/wk × 1.65 ≈ $1.7k.)*

---

## 5. Calendar-time cost

| Scenario | Wall-clock to reach `76addee` equivalent |
|---|---|
| US team, ~1.1 FTE | **~5–6 weeks** |
| Blended global team, ~1.1 FTE | **~6–7 weeks** (timezone coordination) |
| **Actual (single founder + Claude)** | **~8 calendar days** (first commit 2026-06-01 → `76addee` 2026-06-09), *concurrent with active OnDemand / Mentible / Pramana work* — likely only a few focused days of actual effort within that window |

The calendar figure carries the same asterisk as the sibling projects: those ~8 days overlapped with the larger product work this toolkit *markets* (the decks pull directly from those products' docs and `products.yaml`). The wall-clock compression is real and the reuse leverage is real — much of the deck content is the product thesis the founder already had in hand, re-expressed.

---

## 6. What was actually spent

| Line item | Estimate |
|---|---|
| Founder time, ~3–4 focused days within an 8-day window shared with other projects | ~24–32 hours |
| Claude Code subscription / API (during the build) | $50–200 |
| Anthropic token cost for the tool's *own* generations (copy) | ~$0–5 (a handful of `generate.py` runs; `--dry-run` is free) |
| python-pptx / Pillow / LibreOffice | **$0 — all open-source** |
| Domains / infra / accounts | **$0 — no server, no deploy, no hosting** |
| **Direct cash outlay** | **~$0.05k–0.2k** |
| Founder opportunity cost @ $300k/yr equivalent × ~0.75 weeks of focused effort | **~$4.3k** |
| **All-in actual cost** | **~$4.4k** |

This toolkit has essentially **zero recurring cost**: no server, no database, no deploy, no hosting account. It runs on a laptop, calls a pay-per-use API the founder already has, and emits files. The only ongoing "cost" is the founder's time to maintain the asset library.

---

## 7. Headline ratios

| Comparison | US scenario | Blended scenario |
|---|---|---|
| Cash-only multiplier | **~265× cheaper** ($33k ÷ ~$0.125k) | **~80× cheaper** ($10k ÷ ~$0.125k) |
| All-in multiplier (incl. founder opp-cost) | **~7.5× cheaper** ($33k ÷ $4.4k) | **~2.3× cheaper** ($10k ÷ $4.4k) |
| Calendar compression | **~4–5× faster** (~8 days vs ~5–6 weeks) | **~4–5× faster** |
| Team-size compression | **~1.1× smaller** (1 vs ~1.1 FTE) | **~1.1× smaller** |

**Headline: ~7.5× cheaper all-in (US) / ~2.3× (blended), at a ~265× cash-only ratio (US), for a tool that cost ~$4.4k all-in vs a ~$33k conventional US build.**

These multipliers are *lower* than the larger sibling projects (OnDemand ~27× US all-in, Mentible ~16×, Thittam ~61×) — and that is the expected, informative result at this scale. Two reasons: (1) the toolkit is dominated by **design-and-content work** (four hand-built decks, brand identity) where AI assistance compresses *less* than on boilerplate CRUD; and (2) at ~1.3 EM of conventional effort there is simply **less absolute work for any multiplier to act on** — the founder's near-fixed opportunity-cost floor (~$4.4k for a few focused days) is a larger *fraction* of a small build than of a large one, which compresses the all-in ratio. The cash-only ratio stays large precisely because the conventional team's labour cost dwarfs the founder's trivial direct outlay.

---

## 8. Honest caveats

- This is a **small internal tool**, not a product. The ~1.3 EM estimate is for a competent generalist + a part-time designer; an elite engineer who has built a python-pptx theme engine before could do it in ~1 EM, a team learning python-pptx slide geometry on the job in ~1.6 EM. Range **1.0–1.6 EM** is defensible.
- **The `landing/` builder is excluded from both columns** (it's an explicit stub). Building it would add ~1–2 EW to the conventional estimate and a few days to the actual.
- **Tests are excluded from both columns because none exist.** A conventional team *would* have written some; folding in ~0.3 EW of testing would raise the conventional baseline slightly (and the actual cost barely).
- **Reuse compounds the velocity.** The four decks aren't net-new thinking — they re-express the product thesis the founder already had in `products.yaml` and the product docs. Some of the ~8-day speed is first-party content reuse, not AI assistance per se; the two compound.
- The calendar figure overlapped with OnDemand / Mentible / Pramana work — treat "~8 days" as wall-clock within a shared window, not exclusive founder-time (the real focused effort is closer to a few days).
- Equity is excluded from the cash columns; a real team's total comp including equity would be ~30% higher.

---

## 9. What this means

The honest comparison is the **all-in multiplier: ~7.5× cheaper (US) / ~2.3× (blended)**, with a **~4–5× calendar compression** — modest multipliers, and that's the point. At this scale the dominant cost is design-and-content time (decks, brand, copy) and the founder's near-fixed opportunity-cost floor, neither of which AI collapses the way it collapses scaffolding and CRUD on the larger projects. The multiplier is small *because the artifact is small*, not because the leverage is weak.

The more durable observations are about **cost structure, not multiples**. This toolkit has **zero infrastructure cost** — no server, no DB, no deploy — and its only token cost is a few cents of `generate.py` runs (with the free `--dry-run` path doing the inspection). It is the cheapest possible shape of software: a stateless CLI + a script that emits files, built on open-source libraries, calling an API the founder already pays for. A bootstrapped founder can stand up a real marketing capability — one source of truth, channel-ready copy on demand, four investor-grade decks — for **low-hundreds of dollars all-in and a few days**, and then run it indefinitely for the cost of occasional API calls. That near-zero standing cost, more than any speed multiplier, is the strategic fact here.

---

*Cost analysis is a point-in-time exercise. Loaded rates, market conditions, and AI tooling capability all evolve. This is a v1.0 pass against a small internal toolkit at `76addee` (branch `main`, 2026-06-09), with the `landing/` stub and the `.venv-decks/` virtualenv excluded. Re-run if the landing builder is built, tests are added, or the deck set grows substantially — each shifts the conventional-team baseline. All LOC, file, commit, and test counts are measured from disk; all dollar figures are stated estimates with the arithmetic shown.*
