# MarketingTools — Scoping, Design, Architecture & Development Pattern

**Document type:** Development pattern analysis
**Scope:** Full lifecycle of a small internal tool — from "I have five products and one go-to-market channel each" to a working copy-generator + multi-brand deck engine + CRM-lite log
**Period:** 2026-06-01 → 2026-06-09 (~8 days, 4 commits)
**Reviewed:** 2026-06-09 (v1.0 — first review, measured on disk at branch `main` @ `76addee`)
**Repo:** `MarketingTools` (`/home/sivam/Documents/code/projects/AIStuff/STEM_studybuddy/MarketingTools`)
**Author:** Claude (Anthropic)
**Related:** [MarketingTools-critique.md](MarketingTools-critique.md) · [MarketingTools-practices.md](MarketingTools-practices.md)

> This is the development-method analysis: *how* the toolkit was scoped, designed, and built — less about bugs (see the critique), more about the decision discipline visible in 2.3k LOC and 4 commits. The defining trait is **pattern reuse as a deliberate framing**: the toolkit doesn't invent a marketing system, it *re-points the products' own "scoped-retrieval" engine pattern at marketing*, and it scopes itself subtractively (build copy + decks + a log; explicitly **defer** landing pages).

---

## 1. Origin — a tool born from a portfolio problem

MarketingTools exists because the author has **a portfolio, not a product** — StudyBuddy OnDemand, Mentible, Pramana, a home-school wedge, and a special-needs video prototype — and each needs channel-appropriate marketing copy and pitch material drawn from the *same* underlying facts (taglines, proof points, links, audiences). The origin problem is duplication: without a source of truth, a tagline change means editing it in N WhatsApp messages, M decks, and a landing page. The README states the thesis directly: "Never hardcode a tagline outside `products.yaml`. One edit should propagate."

The framing move is the interesting part. Rather than treat marketing as a new domain, the README reframes it as the **same engine the products already are**:

```
Product engine:    (topic × grade × language × format × framing) → lesson
Marketing engine:  (product × audience × channel × framing)      → channel-ready copy
```

So the design starts from an *analogy to existing IP* — "the IP is the scoping, not the model" — which is the same sentence the Mentible and Pramana pitch decks use about the products themselves. The toolkit is, in effect, dogfooding its own portfolio's thesis on itself.

---

## 2. The scoping artifact — `products.yaml` as the design

There is no `SCOPE.md` or ADR series here (and at 2.3k LOC, there shouldn't be). The scoping artifact *is* `assets/products.yaml` — a 130-line, heavily-commented YAML file whose header is the closest thing to a design doc:

- It declares the **single-source-of-truth contract** ("Every product you market lives here once… a tagline change here propagates everywhere") and the anti-pattern it forbids ("Don't generate into it — generated copy goes to stdout / out/").
- It encodes a **portfolio taxonomy** via the `home:` key (StudyBuddy / Mentible / Pramana repos), and even records the dated `briefcase → pramana` rename and that the rename was propagated to `campaigns.csv` — a migration note inside the data file.
- It defines the **two-framing model** (`consumer` / `technical`) per product, which the generator's framing-resolution heuristic then consumes.

This is a small but real instance of *spec-as-data*: the design decision ("one registry, never duplicated, never generated-into") lives in the file it governs, and the code (`generate.py`) is written to honor it generically rather than to special-case any product.

---

## 3. The defining pattern — subtractive scoping by status table

The README's "What's here" table is the development plan, and it scopes by **explicit deferral**:

| Path | Job | Status (as shipped) |
|---|---|---|
| `assets/products.yaml` | Central asset library (source of truth) | ✅ built |
| `assets/brand/*.md` | Brand rules injected into every generation | ✅ built |
| `generate.py` | `(product × audience × channel × framing)` → copy | ✅ built |
| `templates/` | Hand-tuned paste-ready formats | ✅ built (one seed: WhatsApp invite) |
| `campaigns/` | Outreach log (CRM-lite CSV) | ✅ built |
| `landing/` | Landing/microsite builder | 🟡 **stub — deliberately deferred** |

The instructive choice is `landing/`: rather than build a half-baked site generator, `landing/README.md` ships a **plan and a today-workaround** ("Until the builder exists, you can already generate the hero text: `python ../generate.py --product pramana --audience L&D_leads --channel landing_hero`"). The deferral is *named, justified, and given an interim path*, not silently skipped. That is the same "scope subtractively, name what you're not building" discipline visible in the larger sibling projects, applied at small scale.

A second subtractive signal: the `decks/` engine ships exactly the decks that were *needed* (three Mentible audiences that a real investor/architect/author conversation requires, one Pramana buyer deck for a named pilot), not a generic deck framework. The brand engine generalizes (`set_brand`), but the *content* is built to the actual outreach in flight.

---

## 4. Architecture method — thin CLI over data, layout library under content

Three method choices define the architecture, all consistent with the project's small scale:

**4.1 Keep the executable thin; put the value in the data.** `generate.py` is 173 lines and does almost no "work" — it loads YAML, concatenates brand markdown, assembles a prompt string, and (lazily) calls one SDK method. All the *marketing judgment* lives in `products.yaml` (the facts) and `brand/*.md` (the rules). This is the "the IP is the scoping, not the model" thesis enforced structurally: the code is commodity glue, the data is the asset.

**4.2 Defer the network as late as possible, and make the no-network path first-class.** The generator's control flow is `--list` (no SDK, no key) → build prompt → `--dry-run` (no SDK, no key) → *only then* require `ANTHROPIC_API_KEY` and lazily `import anthropic`. Inspecting exactly what will be sent to the model — for free, offline — is the default-reachable path. For a tool whose output is *prompts*, making the prompt the inspectable artifact is the right design.

**4.3 Generalize the deck engine to a brand, specialize the content.** `theme.py` was built so one layout library serves multiple identities: a `Brand` dataclass (`wordmark`, `primary`/`accent`/`support` colors, `logo: Path | None`, `tag`), an active-brand global, and a `set_brand()` switch. The Pramana builder flips to indigo/gold with a **text-logotype fallback** (`logo=None` → the layouts render a wordmark instead of an image). The method here is "build the framework only as wide as you have a second case for" — there are two brands, so the engine supports exactly two-brands-worth of variation (color + logo-or-wordmark), not a hypothetical theming system.

---

## 5. Build sequence — one scaffold commit, then targeted additions

The 4-commit history is legible and shows a thinnest-viable-thing-first sequence:

```
94778f5  2026-06-01  scaffold MarketingTools — the whole copy-gen toolkit in one commit
                      (generate.py + products.yaml + brand rules + templates + campaigns + landing stub)
5b1629d  2026-06-09  tag products with `home:` portfolio (StudyBuddy vs Mentible split)
4eb3f80  2026-06-09  track python-pptx deck builders + ignore the deck venv
76addee  2026-06-09  rename briefcase product → pramana (own portfolio)
```

The shape: **the copy-generation core landed whole in one scaffold commit** (the genuinely useful unit — you can generate copy from day one), and the three later commits are *portfolio-maintenance and capability-addition* (taxonomy tagging, the deck builders, a product rename) all on the same day. There is no churn, no half-built-then-reverted surface — for an 8-day tool that's appropriate. The deck engine arriving as a separate later commit (`4eb3f80`) with its own gitignored venv shows the decks were added once a concrete need (the Mentible/Pramana pitches) materialized, not speculatively up front.

---

## 6. What's deferred — and how honestly

The deferrals are named, exactly as in the sibling projects:

- **Landing pages** — `landing/README.md` is explicitly "STUB (deferred)," with the plan (reuse OnDemand's `web/app/(public)/` routes or a static 11ty/Astro generator reading `products.yaml`) and the interim workaround.
- **Tests** — not deferred *in writing* (there's no "tests TODO"), which is the one honest gap in the otherwise-candid status reporting: a status table that marks `landing/` as a stub but is silent on the absence of any test is under-disclosing that absence. (See the critique, §3.)
- **A unified dependency manifest** — the split between `requirements.txt` (generator) and the prose-only deck-deps in `decks/README.md` is a deferral-by-omission rather than a stated one; the README *documents* the deck setup but doesn't promote it into a manifest.

The pattern's one weakness, then, is the same family as the larger projects' "ADR-outran-spec" gap, scaled down: **the status table reports product-surface deferrals honestly but is silent on engineering-hygiene deferrals** (tests, a complete manifest). Those aren't design errors; they're the durable-frame-lags-reality gap in miniature.

---

## 7. Lessons this tool teaches

1. **Reframe a new problem as your existing pattern.** Marketing wasn't modeled as a new domain; it was modeled as the products' own scoped-retrieval engine with a different scope vector. The analogy did real design work — it told the author what the source of truth was (a registry of scope inputs) and what the code should be (thin glue, not the asset).
2. **Make the data the design.** `products.yaml`'s header carries the single-source-of-truth contract, the portfolio taxonomy, and even the migration history — spec-as-data at a scale where a separate spec doc would be overhead.
3. **Defer with a plan and an interim path, not silence.** `landing/` is a stub that ships the plan *and* a working today-workaround — the honest way to not-build something.
4. **Generalize a framework only as wide as your second real case.** The deck engine supports exactly two brands because there are two brands; the `logo: Path | None` fallback is the minimal generalization that the Pramana (no-logo) case actually required.
5. **The one to fix: promote hygiene deferrals into the frame too.** The status table that honestly flags `landing/` as a stub should equally flag "no tests yet" and pull the deck deps into a manifest — the same "reconcile the durable frame with reality" discipline the products themselves are coached on.

---

*This analysis is drawn from the code on disk at `76addee` (branch `main`), the 4-commit history (2026-06-01 → 2026-06-09), `products.yaml` and its header, the six in-repo docs, and the generator/deck source — all with the `.venv-decks/` virtualenv excluded. The toolkit is small and personal; this is a development-method read of a deliberately modest artifact, not a heavyweight process audit.*
