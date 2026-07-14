# WeGoFwd2020 — Portfolio Experiment Scorecard & Now/Next/Later

**Owner:** WeGoFwd2020 · **Date:** 2026-06-11 · **Updated:** 2026-07-14 (added `medtracker`) · **Operator:** solo founder
**Purpose:** Turn parallel builds into readable experiments. Decide where to commit, what to park, and on what signal a parked bet comes back.

> **How to read this.** Capability is proven — the engine works and generalizes across audiences. This doc is about the *second* test every product still has to pass: **will the audience adopt or pay?** Each product gets a demand hypothesis, the cheapest test that answers it, a signal to double down, and a signal to kill/park. The binding constraint is one founder's time, so this is deliberately zero-sum.

---

## Portfolio map — three lineages, not nine random bets

**A. The engine lineage** (organized/scoped query → audience). One IP, pointed at different audiences:
- **StudyBuddy** (origin, most built) → K–12 / schools
- **Pramana** → corporate compliance / L&D
- **Mentible** → adult self-learners / professional content
- **Kathai Chithiram** → parents of children with special needs
- *MarketingTools* = internal reuse of the same engine (enabler, not a product)

**B. The anchor** — **Thittam**: a recreation of a business problem you personally solved, productized for many orgs. Different tech lineage, lowest market risk, strongest founder-domain fit.

**C. The passion track** — **dronePrjs**: exploration, against entrenched incumbents. Kept for learning, not commercial priority.

**Outside the lineages — tools, not bets.** **wegofwd-expenses** (email→ledger) and **medtracker** (family medication refills) are built for an audience of one household. They carry no demand hypothesis and compete for no market; they appear in the scorecard only so the capacity they consume is visible. medtracker is also the portfolio's one product with **no LLM at runtime** — a useful control case for what the engine thesis is actually worth.

---

## Experiment scorecard

| Product | Buyer / audience | Demand hypothesis | Cheapest next test | Double-down signal | Kill / park signal | Evidence today | Stage |
|---|---|---|---|---|---|---|---|
| **Thittam** *(anchor)* | Orgs running productions (film, construction, software, events) | Orgs will replace their spreadsheet patchwork with one configurable multi-vertical platform | Take it to **1 org in the vertical you know best**; get a design-partner pilot or a signed LOI | An org pilots or signs an LOI | Even with your domain credibility, no org will commit to a pilot | Strongest founder-domain fit; late-build; 4 verticals claimed GA in docs; no named customer in repo | Late-build |
| **Pramana** | Corporate compliance / L&D buyer | Orgs will pay for SOX training + tracking with audit-grade completion evidence | Convert the **already-named tenant** into a committed paid pilot with a signed scope | Named tenant commits/pays; a 2nd org expresses interest | Named tenant won't sign a scoped pilot | Spec + SQLAlchemy model; **one named target tenant** (a real demand signal) | Spec / early build |
| **StudyBuddy OnDemand** | Schools (admin/teacher buyer); parents secondary | Schools will pay for pre-generated, curriculum-aligned, offline tutoring with teacher visibility | Run **1–3 real classroom/teacher pilots** of the existing demo; define the launch metric | A school commits to a paid pilot; teachers return weekly | No school will pilot after a focused outreach round; pilots don't retain | Most built (1,500+ tests, demo live); no named pilot customer seen | Active — awaiting external input (pilots) |
| **Kathai Chithiram** | Parents of children with special needs | Parents will value (and pay for) personalized social-story animations that actually help their child | Make **5 real stories for 5 real families** (you have 1 — "Silas"); watch child engagement + parent return | Parents come back for more / will pay / refer | Families don't engage or it doesn't help | Prototype; 1 hand-built story; highest mission value, hardest to monetize | Prototype |
| **Mentible** | Adult self-learners (BYOK); Mentible = pro content/books | Adults will use a scoped learning client, or buy Mentible-generated content | **Landing page + waitlist**, or hand-sell 5 Mentible outputs *before* building the app | Waitlist conversions / pre-orders / repeat manual sales | No signal from landing or manual sales | Pre-MVP, stubs only — **do not build more until tested** | Pre-MVP |
| **StudyBuddy Free** | (origin app) | — | — | — | — | Shipped v1.1.0; proof-of-concept; **GitHub repo archived 2026-07-06** | Archived |
| **dronePrjs** | (passion) | A simple everyday drone use-case is underserved by the big players | Define **one** concrete everyday use-case; check if anyone wants it — *when commercial bets are stable* | — (deferred) | — (deferred) | Early sim, Phase 3 partial | Passion |
| **wegofwd-expenses** *(internal tool)* | Operator (self) — internal finance/ops, not a market bet | Automated email→ledger tracking is more reliable and lower-effort than manual tabulation of Anthropic/vendor spend | Run the **real-mailbox dry run** (live Gmail + LLM + PDF); audit one week of ledger rows for vendor+amount accuracy | ≥95% extraction accuracy + zero-touch daily runs → keep as a standing ops tool | Extraction too noisy or review burden too high → shelve, tabulate manually | P0 built (76/76 tests, merged); on GitHub org (private); live Gmail/LLM/PDF paths not yet exercised | Internal tool — P0 built, awaiting dry run |
| **medtracker** *(personal tool)* | Operator + family — personal health ops, not a market bet | One computed refill date per medication prevents run-outs more reliably than pharmacy apps plus memory | **Demand is already answered** — it is in daily use. The open test is *durability*, not adoption: exercise the backup-and-restore path end-to-end and prove nothing is lost | Family gets through a full refill cycle with no run-out and no manual fallback | Recovery fails, or the computed dates drift from reality → back to the pharmacy app | Deployed 2026-07-13 (one-day build, 10 commits); private repo, tailnet-only; durability gaps tracked in the private review | Deployed — in daily use |

---

## Now / Next / Later

### NOW (next 4–6 weeks) — validate, don't build
All three are *conversations and pilots*, which run in parallel and cost little time. No new feature work.

- **Thittam — chase the anchor.** Get one design-partner pilot or LOI in your strongest vertical. This is your lowest-risk path to a paying customer and external credibility.
- **Pramana — close the named tenant.** Turn the one named target into a committed, scoped paid pilot. A signed B2B compliance pilot is worth more than any amount of additional code.
- **StudyBuddy OnDemand — get it in front of real classrooms.** 1–3 teacher/school pilots of the *existing* demo. In parallel, define the single launch success metric (activation or weekly retention) and add product telemetry so the pilot produces a readable signal.
- **Decide the strategic fork** (see below). A thinking task, not a build task — but it gates everything in NEXT.

Plus one item that is **not a bet — a chore**, and does not compete with the three above:

- **medtracker — retire its one irreversible risk.** It is deployed, holds real data, and has an encryption-key/backup recovery path that has never been exercised end-to-end. Run the restore drill and confirm the key is escrowed. It is roughly an hour of work, and it is the only item in this portfolio where the downside is permanent. (Specifics are in the private review — `medtracker/docs/critique/`.)

### NEXT (1–3 months) — commit only where NOW showed pull
- Whichever of the three NOW bets produced a real signal → **build toward a paid v1**: pricing & packaging, launch-readiness, and for StudyBuddy the COPPA/FERPA + privacy/ToS artifacts that don't exist yet.
- **Kathai Chithiram — tiny 5-family pilot.** Cheap, high-learning, high-meaning. Reads demand for the hardest-to-monetize but most mission-aligned product.
- **Repurpose StudyBuddy Free** as top-of-funnel / lead magnet for the engine lineage rather than a maintained product.

### LATER (3–6+ months) — directional, revisit on trigger
- **Mentible** — build the app *only after* a landing/manual-sale test passes.
- **Pramana v2 frameworks** (HIPAA, ISO 27001, GDPR, PCI DSS) — *after* the v1 SOX pilot succeeds.
- **dronePrjs** — passion track; pick one everyday use-case to explore once the commercial bets are stable.

---

## The strategic fork you haven't resolved

The engine lineage forces one decision: **are you selling the engine, or the applications?**

- **Sell an application** — win *one* vertical convincingly (e.g. Pramana for compliance, or StudyBuddy for schools), use it as proof, monetize that. Narrower, faster to revenue, defensible by depth.
- **Sell the engine** — productize the scoped-query platform itself and let others build the applications. Broader, slower, harder to sell, bigger ceiling.

You can't run both indefinitely as one person. Picking changes what you build in NEXT. My read: prove it with **one application first** (it de-risks the engine claim and produces revenue), then decide on platform later — but the call is yours.

---

## Priority call & capacity note

**Actively validate now (max focus):** Thittam (anchor) + Pramana (named buyer) + StudyBuddy OnDemand (most built).
**Park until a NOW bet pays off:** Mentible.
**Cheap parallel mission pilot:** Kathai Chithiram (5 families).
**Passion track, no commercial clock:** dronePrjs.

**Capacity reality.** With one operator, *validation* (conversations, pilots) parallelizes; *building* does not. Cap concurrent **build** bets at one — at most two. Every time something new enters "build," something else must leave. The reason to validate three products at once in NOW is that talking to buyers is cheap and the goal is to find which one earns the right to be built next.

**The personal tools are done building.** wegofwd-expenses and medtracker each cost real build days (medtracker: one day, 2026-07-13). Both are now **maintain**, not **build** — they solve a household problem, and neither has a market to earn more time. Watch that the low friction of shipping them doesn't keep pulling days away from the three bets that actually need a buyer.

---

*Companion file: `PRODUCT_CATALOG.md` (full portfolio inventory + sync status).*
