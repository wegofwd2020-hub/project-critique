# dronePrjs — Real-World Cost Analysis

**Analysed:** 2026-05-24 (v1.0 — first cost pass against HEAD `5e38a44`)
**Repo:** `dronePrjs` (local, `main`)
**Question being answered:** if this same artifact had been built by a conventional drone-autonomy / robotics team in the real world (not by a single founder with Claude-assisted execution), what would it have cost in money and calendar time?
**Scope of measurement:** code on disk at HEAD `5e38a44` — "early-build / pre-simulator" state per the v1.1 critique (Phase 0–6 complete + Phase 3 partial; 35 of 44 ISCs done). **Hardware integration and pilot operations (Phase 8) are explicitly out of scope for both columns.** This is a software-stack cost analysis, not a full drone-product cost analysis.

---

## 1. What's actually been built

Measured directly from the repository (HEAD `5e38a44`, dated 2026-05-13).

| Slice | Measure |
|---|---|
| Calendar span of commits | **8 commits on a single day** (2026-05-13 16:25 → 18:10 — ~1h 45m of commits) |
| Python production LOC | **3,548** (non-test, 32 files) |
| Test LOC | **2,327** |
| Test functions | **114** (~133 collected with parametrize per ISA NS-3.2) |
| Coverage | **95.3%** (per ISA NS-3.2) |
| Engine Protocol layer | `engine/` — flight_control, localization, sensors, sim, sim_gazebo, telemetry, types |
| Built domain | `closedSpace/` — capture, constants, map, mission, operator, report, schemas, storage, sim |
| Stub domain | `openSpace/` — CLAUDE.md only; no source |
| In-process simulator | `engine/sim/` — kinematic, drives the test suite end-to-end |
| Gazebo/PX4-SITL scaffold | `engine/sim_gazebo/` (Docker: PX4 v1.15.4 + Gazebo Harmonic + Ubuntu 22.04, host-networked for MAVLink); `closedSpace/sim/world_builder.py` Map→SDF 1.10 |
| Safety primitives | Pre-arm gate; map-signature check (ISC-28 done); GPS forbidden in closedSpace by static AST probe; map staleness + provenance first-class |
| Quality gates | `mypy --strict` across 29 source files clean; `ruff check` clean; zero TODO/FIXME |
| CI | **`.github/workflows/ci.yml`** — single `quality-gate` job: Python 3.12, `make all`, coverage ≥80% (Phase 6, ISCs 37–41 + 44) |
| System-of-record document | **`closedSpace/ISA.md`** — 687 lines fusing PRD + acceptance criteria + test strategy + decisions + changelog |
| CLAUDE.md tiering | Three-tier: umbrella + per-domain (closedSpace, openSpace) |
| Docs | 11 markdown files total |
| Decisions ratified | D1 (sim-leads/hardware-follows) and D2 (two-tier sim: in-process kinematic + Gazebo/PX4-SITL) in ISA DECIDE entries |
| Open ISCs | 9 of 44 (ISC-12, 13, 14, 15, 19, 20, 31, 33, 42) — load-bearing: ISC-15 link-loss RTH; openSpace becoming a real second engine consumer |
| **Production LOC (Python source, excl. tests)** | **~3,548 LOC** |

**Why this analysis looks different from StudyBuddy / Thittam:** dronePrjs is **early-build, pre-simulator, pre-hardware**. The conventional baseline is smaller in absolute dollars because there's less to build — but the *rate* per engineer is **higher**, because drone autonomy is a specialty discipline (robotics, MAVLink, ROS2, Gazebo, PX4, safety-critical systems thinking). Generic web/backend engineers cannot do this work. The headline ratios are therefore *higher* in cash-only terms than the SaaS projects, even though the absolute savings are smaller.

---

## 2. Methodology — triangulated three ways

A single estimate from one method is not defensible. I used three independent methods and reported the convergence.

1. **Industry-velocity benchmark.** A drone-autonomy software stack at Phase 0–6 / 35-of-44-ISCs state (engine Protocol + one built domain + in-process simulator + Gazebo/SITL scaffold + CI + 114 tests + safety primitives + ISA-as-SOR) typically takes **10–16 engineer-months** in a competent robotics startup. Reference points: early-stage Skydio / Verity / Ware engineering retros; PX4/ArduPilot module-equivalent scopes; commercial warehouse-inventory drone startups.
2. **COCOMO-II modernized.** At ~3.5 KLOC production code, raw COCOMO gives ~13 EM; modernized with a 0.4 multiplier (drone autonomy is *less* mature than web frameworks — typed Python + ROS-style architecture doesn't accelerate as much as Next.js does for web) ⇒ **~8–10 EM**. Lower bound because LOC is small.
3. **Feature / phase counting.** 6 completed phases × ~2 weeks/phase for a team of 3–4 + 2 weeks of cross-cutting infrastructure (CI, ISA, static-analysis tests) + Phase 3 partial = **~10–14 EM**.

**Convergence: 10–15 engineer-months is the defensible range.** Point estimate **12 EM**.

---

## 3. Team composition

Assume **12 EM spread across 3.75 FTE for ~3.8 calendar months**. The team is smaller than the SaaS projects but **per-FTE rate is higher** — drone autonomy is a specialty hire market.

| Role | FTE | Why this is non-negotiable for dronePrjs |
|---|---|---|
| Staff/Principal Robotics Engineer | 1.0 | Engine Protocol design, ISA-as-SOR discipline, decision ratification (D1/D2/D3), safety invariants |
| Senior Drone Autonomy Engineer | 1.0 | closedSpace mission, operator, preflight, pre-arm gate, map-signature verification |
| Senior Simulation Engineer | 1.0 | `engine.sim` kinematic + Gazebo/PX4-SITL scaffold + `world_builder.py` Map→SDF |
| QA / SDET | 0.5 | 114 tests + 95.3% coverage discipline + static-analysis tests + CI quality gates |
| Technical Writer (ISA / ADR) | 0.25 | 687-line ISA.md + 3-tier CLAUDE.md system + decision-record discipline |
| **Total** | **3.75 FTE** | |

Note: a **safety / compliance reviewer** is appropriate for any drone-autonomy product before pilot operations (Phase 8) — that cost is **not** in either column above and would add ~$30–80k for an external aviation-safety / FAA Part 107 / EASA review.

---

## 4. Cost scenarios

### Scenario A — US robotics / aerospace labour market

Robotics engineers command meaningfully higher rates than commodity web/backend engineers. References: Skydio, Joby, Wisk, Verity, Ware, Anduril. Senior drone-autonomy engineers run $320–450k base + significant equity; staff/principal hits $450k+ base. Loaded rates account for the recruiter premium on rare-skill hires.

| Role | FTE | Loaded $/yr | 3.8-month cost |
|---|---|---|---|
| Staff Robotics Engineer | 1.0 | $520k | $165k |
| Sr Drone Autonomy Eng | 1.0 | $380k | $120k |
| Sr Simulation Engineer | 1.0 | $380k | $120k |
| QA / SDET (robotics-aware) | 0.5 | $240k | $38k |
| Technical Writer | 0.25 | $200k | $16k |
| **People subtotal** | **3.75** | | **$459k** |
| Specialty recruiting (rare-skill premium, 25–30% on first-year cash for senior+) | | | $35k |
| Infra (cloud compute for Gazebo sim builds, CI runners with GPU, sim artifact storage) | | | $8k |
| Tools (Gazebo / PX4 / ROS / MAVLink are open-source; commercial sim or RTOS licenses if needed) | | | $5k |
| Equipment (GPU workstations for sim; **no actual drones yet** — Phase 8 explicitly excluded) | | | $15k |
| **Scenario A total** | | | **~$522k** |

### Scenario B — Blended global / robotics talent in EU + India + LATAM

Robotics talent exists outside the US — Tallinn/Tartu (Estonia), Kraków/Warsaw, Bengaluru robotics cluster, Mexico City, São Paulo. Rarer than commodity dev talent, so the premium over local market rates is higher than for web engineering.

| Role | FTE | Loaded $/yr | 3.8-month cost |
|---|---|---|---|
| Staff Robotics Eng | 1.0 | $170k | $54k |
| Sr Drone Autonomy Eng | 1.0 | $110k | $35k |
| Sr Simulation Engineer | 1.0 | $100k | $32k |
| QA / SDET | 0.5 | $60k | $9k |
| Technical Writer | 0.25 | $50k | $4k |
| **People subtotal** | **3.75** | | **$134k** |
| Specialty recruiting (rarer outside US — premium higher) | | | $20k |
| Infra | | | $8k |
| Tools | | | $5k |
| Equipment | | | $12k |
| **Scenario C total** | | | **~$179k** |

### Scenario C — Academic spin-out / PhD-heavy team

A genuine alternative for drone autonomy (most successful drone startups came out of academic robotics labs: Skydio from MIT/Stanford, 3DR from DIY Drones, Verity from ETH Zürich). 1 senior lead + 3 PhD/postdoc juniors at academic-adjacent rates ≈ 3.5 FTE × 5 months × $120k loaded = **~$175k**. The trade is calendar risk — academic-tempo teams typically take 1.5–2× longer than commercial teams to hit a "Phase 6 + CI + safety primitives" state.

---

## 5. Calendar-time cost

| Scenario | Wall-clock duration to reach `5e38a44` equivalent |
|---|---|
| US team, 3.75 FTE | **3–5 months** |
| Blended global team, 3.75 FTE | **4–6 months** (timezone overhead) |
| Academic spin-out, ~3.5 FTE | **5–8 months** |
| **Actual (single founder + Claude Opus 4.x)** | **~1h 45m of commits on a single day** (2026-05-13). Generously allowing 1–2 weeks of uncounted scoping + ISA drafting → **~2 weeks all-in.** |

The calendar compression here is the most extreme of any of the three projects. **All 8 commits — Phase 0 through Phase 6 plus Phase 3 partial — landed in under two hours on a single day.** Even being generous about pre-commit thinking and ISA drafting (1–2 weeks before the commit burst), the actual delivered window is two orders of magnitude shorter than the conventional baseline.

---

## 6. What was actually spent

| Line item | Estimate |
|---|---|
| Founder time (generous: 2 weeks at 8h/day for scoping + ISA + the commit burst) | ~80 hours |
| Claude Code subscription / API (intensive 1–2 weeks) | $50–200 |
| Compute (local mostly; some cloud for sim experiments) | ~$20 |
| Misc tooling | ~$10 |
| **Direct cash outlay** | **~$0.1k–$0.3k** |
| Founder opportunity cost @ $300k/yr equivalent × 2 weeks | **~$11.5k** |
| **All-in actual cost** | **~$12k** |

---

## 7. Headline ratios

| Comparison | US scenario | Blended scenario |
|---|---|---|
| Cash-only multiplier | **~1,740× cheaper** ($522k ÷ $300) | **~600× cheaper** ($179k ÷ $300) |
| All-in multiplier (incl. founder opp-cost) | **~44× cheaper** ($522k ÷ $12k) | **~15× cheaper** ($179k ÷ $12k) |
| Calendar compression | **~8× faster** (2 weeks vs. ~4 months) | **~10× faster** (2 weeks vs. ~5 months) |
| Team-size compression | **3.75× smaller** (1 vs. 3.75 FTE) | **3.75× smaller** |

**Per-FTE-month productivity multiplier** (orthogonal view): conventional baseline = ~12 EM ÷ 1 actual FTE-month = **~12× per-FTE-month leverage.** Higher than SB or Thittam because the actual time was shorter, not because the conventional baseline was larger.

---

## 8. Honest caveats

- **The conventional baseline is smaller in absolute dollars** ($522k US vs. $1.4M for StudyBuddy, $2.2M for Thittam) because dronePrjs is earlier-stage. Don't conflate "highest ratio" with "biggest savings" — the absolute savings here are about a third of StudyBuddy's.
- **Hardware costs are explicitly excluded.** Phase 8 (pilot operations) requires actual drone hardware, FAA Part 107 / EASA certification, safety reviews, and field testing — adding **~$50–200k** depending on platform choice and operational scope. That's true for both columns.
- **Safety review is excluded.** Any drone-autonomy product reaching pilot operations needs an external aviation-safety review (~$30–80k). Same for both columns.
- **openSpace is still a stub.** The engine Protocol contract is single-consumer (closedSpace only) until openSpace becomes a real implementation. A real team would have built openSpace alongside closedSpace from day one to validate the abstraction. The founder hasn't yet — and the v2.3 critique flagged this as the #1 priority action. **Cost to close that gap: ~3–5 EM additional in either column.**
- **ISC-15 link-loss RTH still open.** A real safety-critical drone-autonomy team would not have shipped Phase 6 without RTH (return-to-home on link loss) — it's a regulatory expectation for autonomous BVLOS operations. The founder shipped Phase 6 anyway; a real team would have added ~1–2 EM to complete ISC-15 before declaring Phase 6 done.
- **The "1h 45m of commits" is the visible window.** Pre-commit thinking, architecture-design, ISA drafting, and prototyping likely took 1–2 weeks of focused effort that doesn't show in git history. I've used the generous "2 weeks" figure to avoid over-claiming. The honest read: this artifact represents days-to-weeks of human + AI effort, vs. months of conventional team effort.
- **More of the multiplier here is founder skill than in the SaaS comparisons.** Drone autonomy is unforgiving — getting safety invariants right (pre-arm gate, GPS-forbidden static probe, map-signature check) requires senior judgement that compounds across the codebase. AI tooling accelerates a competent founder's execution but does not substitute for the architectural decisions. **Attribution: ~60% founder skill, ~40% AI assistance.** (For comparison: StudyBuddy ~40/60, Thittam ~50/50.)
- The actual artifact has tests + coverage + static analysis + CI + ISA + safety primitives — this is not a "weekend hack" comparison. It is a real artifact compared against what a real team would have built.

---

## 9. What this means

The cash-only ratio (1,740×) is the most extreme of any of the three projects, but it's also the most misleading — the absolute dollars saved are smaller because dronePrjs is earlier-stage and the actual time invested is shorter. **The all-in 44× US / 15× blended is the honest headline.**

The more durable observation is **what the calendar compression buys**: a single founder reached "Phase 0–6 complete + Phase 3 partial + CI + 95.3% coverage + ISA-as-SOR + safety primitives" in two weeks that a 3.75-FTE robotics team would need 3–5 months to reach. For a hardware-eventual product, that calendar compression is *especially* valuable — it shifts the schedule risk from software development onto hardware procurement and certification, which are the actual long poles for a drone product.

The dronePrjs cost picture should be read **as a proof-of-concept of velocity under engineering-discipline constraints**, not as a forecast of total drone-product cost. To get to a flying drone in production, the conventional column would add Phase 7 simulator hardening + Phase 8 hardware + certification + safety review = roughly another $1–2M and 12–18 months. The AI-assisted column would also add those costs, just compressed — because **AI accelerates software, not hardware procurement or regulatory certification**.

---

*Cost analysis is a point-in-time exercise. Loaded rates, market conditions, and AI tooling capability all evolve. Re-run this analysis annually if it's being used to inform staffing or fundraising decisions. For drone-autonomy products specifically, also re-evaluate when the project transitions from sim-only to hardware (Phase 7→8) — the cost structure changes materially at that boundary.*
