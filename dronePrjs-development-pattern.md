# dronePrjs — Scoping, Design, Architecture & Development Pattern

**Document type:** Development pattern analysis
**Scope:** Full lifecycle — from concept to early-build, pre-simulator
**Period:** May 2026 (8 commits on 2026-05-13 within ~1h 45m wall-time; ~2 weeks of work including pre-commit scoping + ISA drafting)
**Last refresh:** 2026-05-24 (v1.1 — alignment with critique v1.1: Phase 6 CI added, Phase 3 partial scaffolded, ISC-28 done, D1/D2 ratified)
**Prior:** v1.0 May 2026 (first review at commit `5c45c9e`, 6 commits, Phase 0–5)
**Related:** [dronePrjs-critique.md](dronePrjs-critique.md) · [dronePrjs-practices.md](dronePrjs-practices.md)
**Author:** WeGoFwd2020 / Claude (Anthropic)
**Note:** The repo is now 8 commits old, all landed on 2026-05-13 within ~1h 45m. Everything below documents a single concentrated window of activity rather than a multi-year arc.

> **Note (2026-05-24):** the body below is the v1.0 record, preserved. The documented pattern (ISA-as-system-of-record, phase-per-commit, engine-Protocol contract surface, anti-bleed enforced by AST scan, three-tier CLAUDE.md) holds and has been *validated* by the v1.1 cycle — Phase 6 landed as a labelled phase delivery the same way Phases 0–5 did, and the ISA's DECIDE entries (D1, D2) materialised at the expected boundary. New since v1.0, worth noting:
>
> - **Phase-per-commit cadence holds across 8 commits, not 6.** `4ec2c92` (Phase 6 CI quality gates) and `5e38a44` (Phase 3 partial: NS-3.1 Gazebo scaffold + NS-3.2 world generator) both follow the established labelled-phase-delivery convention. The pattern scales.
> - **ISA DECIDE entries as a ratification mechanism.** D1 (sim-leads / hardware-follows) and D2 (two-tier sim: in-process kinematic + Gazebo/PX4-SITL) were ratified in the 2026-05-13 ISA update. **The decision-as-doc pattern (ISA carries the decision-record next to the criteria they constrain) was demonstrated to work end-to-end** — the v1.0 critique flagged these as "unratified," v1.1 closed them with an ISA entry. Reusable for D3 (flight stack) when Phase 8 approaches.
> - **"Declared but not implemented" can be closed by a single commit.** ISC-28 (map-signature check) was the v1.0 example of the declared-not-implemented anti-pattern. It now lives in `closedSpace/operator/preflight.py` as part of the pre-arm checklist. Pattern note: the ISC vocabulary surfaced the gap precisely enough that closing it was a targeted edit, not a hunt.
> - **The Gazebo/SITL tier is deliberately deferred from `make all`.** Phase 3 partial scaffolded `engine/sim_gazebo/` with the heavy Docker build kept out of the default quality gate (NS-3.1b is a manual task). This is a pattern worth documenting: **fidelity tiers each have their own quality-gate window**; the cheap tier runs every commit, the expensive tier runs on demand.
> - **The 8-commits-in-1h-45m datum is itself a development-pattern observation.** When the system-of-record (ISA) is written first and well, the commit burst is small. Commits are checkpoints on already-thought work, not the thinking itself.
>
> Re-measured: 114 test functions / ~133 collected (was 100), coverage 95.3% (was 97%), source LOC corrected to 3,548 (v1.0 over-counted at ~5,010 by including tests), 35 of 44 ISCs complete (was 29/44). Still open + load-bearing: ISC-15 (link-loss RTH) and openSpace becoming a real second engine consumer.
---

## Table of Contents

1. [The Problem Being Solved](#1-the-problem-being-solved)
2. [Scoping Pattern](#2-scoping-pattern)
3. [Design Pattern](#3-design-pattern)
4. [Architecture Pattern](#4-architecture-pattern)
5. [Development Pattern](#5-development-pattern)
6. [Key Decisions and Their Rationale](#6-key-decisions-and-their-rationale)
7. [What This Pattern Teaches](#7-what-this-pattern-teaches)

---

## 1. The Problem Being Solved

Warehouses still rely on humans pushing scan-carts up and down aisles to count inventory. Fixed-camera solutions don't see behind the front face of a rack and miss upper shelves. Handheld scanning misses bin-level granularity unless an operator climbs. The work is slow, ergonomically punishing, and scales linearly with floor area.

The dronePrjs umbrella addresses a single shape of problem in two operating environments:

```
The problem in one frame
─────────────────────────

  "Given a structural map and a drone, autonomously visit every
   declared (aisle, rack, shelf-level) tuple, capture an image, and
   produce a single mission report with coverage stats."

  Two environments split the engineering:

  closedSpace                          openSpace
  ┌──────────────────┐                 ┌──────────────────┐
  │ Indoor warehouse │                 │ Outdoor yard /   │
  │                  │                 │ open inventory   │
  │ GPS-DENIED       │                 │ GPS-AVAILABLE    │
  │ <50 ms latency   │                 │ Wind/weather     │
  │ 0.5 m clearance  │                 │ FAA airspace     │
  │ <15 min battery  │                 │ 60+ min battery  │
  │ SLAM/VIO         │                 │ GPS + IMU        │
  └──────────────────┘                 └──────────────────┘
            \                          /
             \                        /
              \   shared contract:   /
               \  engine/ Protocols /
                \                  /
                 ▼                ▼
              ┌──────────────────────┐
              │  engine/             │
              │  - flight_control    │
              │  - localization      │
              │  - sensors           │
              │  - telemetry         │
              │  - sim (in-process)  │
              └──────────────────────┘
```

The bet: the flight loop, telemetry plumbing, and sensor surface are common; what differs is the localizer (`SLAMProvider` vs `GPSProvider`) and the operational envelope. Build the engine once; let each domain own its own constraints.

As of May 2026 only the closedSpace half exists in code. openSpace is a stub — a 19-line `CLAUDE.md` declaring the domain rules and engine wiring intent, with no Python yet.

---

## 2. Scoping Pattern

### 2.1 Scope Anchored by Operating Environment

Unlike StudyBuddy (scoped by user persona) and Thittam (scoped by industry vertical), dronePrjs scoped by **physical operating environment**. The first scoping question was: *what does the drone fly inside, and what does that physically allow or forbid?*

The split fell out of two questions:

| Question | closedSpace answer | openSpace answer |
|---|---|---|
| Where does position come from? | SLAM only — GPS forbidden | GPS + IMU fusion |
| What's the safety envelope? | 0.5 m clearance hard-coded | Geofencing + airspace class |
| What's the latency budget? | < 50 ms p99 perception→command | Looser — humans tolerate seconds |
| How long can a mission run? | ≤ 15 min battery | 60+ min |
| Who authorizes the airspace? | Property owner | FAA + property owner |
| Can the link drop? | Mission must complete autonomously | Return-to-home + land |

The environmental answers — not the user persona — drove the package boundary. A "drone for warehouse inventory" could have been one package with a `mode='indoor'` flag; it would have been wrong, because the failure modes (GPS jamming inside a steel rack) have no overlap with the failure modes outside (wind shear, rain on the lens).

### 2.2 The Two-Use-Case Scope Decision

The original `project_scope.txt` (committed 2026-05-03) reads almost identically for both use cases — "track the inventory in their warehouse" appears in both. Within a week the scope had been re-stated as:

- **closedSpace v1:** indoor / confined-airspace, GPS-denied, ≤15 min, < 50 ms latency
- **openSpace v1:** outdoor / unrestricted-airspace, GPS-available, ≥60 min, wind-class

Same product shape, two physically incompatible operating envelopes. The umbrella exists because both share a flight loop, telemetry bus, and sensor abstraction; the domains exist because nothing else does.

### 2.3 The ISA-as-Scope-Container

closedSpace's `ISA.md` is the scope container — 634 lines covering Problem / Vision / Out-of-Scope / Principles / Constraints / Goal / Criteria / Test Strategy / Features / Decisions / Changelog / Verification. The `## Out of Scope` block is unusually load-bearing:

```
Explicit v1 exclusions
──────────────────────

  - Outdoor / hybrid missions ........... → openSpace territory
  - Onboard SKU recognition ............. → downstream pipeline
  - Real-time inventory deltas .......... → post-flight only
  - Dynamic re-planning ................. → abort, not reroute
  - Multi-drone coordination ............ → single drone
  - Inventory reconciliation logic ...... → ERP/WMS owns this
  - SLAM-based map building ............. → maps are upstream
  - GPS / magnetometer localization ..... → indoor only
  - Crewed / piloted operation .......... → manual is safety only
```

Every entry has a one-line reason. The discipline is that no Feature, no ISC, and no Decision is allowed to drift past these boundaries without a Decisions-log entry promoting the item out of scope.

### 2.4 Requirements Format — The ISC

Requirements emerged as **Independently-Specifiable Criteria (ISCs)** — 44 of them, numbered, each one a single testable predicate with a stated probe:

```
- [x] ISC-7: The plan's total path length matches a hand-computed
  reference within ±5% on `reference_warehouse.yaml`.

- [ ] ISC-13: End-to-end perception-to-command latency p99 < 50 ms
  on the reference simulator over a 2-minute soak.

- [x] ISC-30: Anti: GPS — no module under `closedSpace/` or `engine/`
  imports `engine.localization.GPSProvider` (probe: `grep -r
  "GPSProvider"` zero matches).
```

The ISC pattern has three properties the project leans on:

1. **Bit-flippable.** `[ ]` or `[x]`. No "in progress", no "blocked".
2. **Co-located with the test.** Test Strategy block names the probe.
3. **Anti-ISCs exist.** ISC-30..36 are negative — "this thing must not happen" — and have static probes (grep, AST scan).

The result is that the scope document doubles as the acceptance suite. There is no separate `acceptance.yaml`; the ISA is the source of truth.

---

## 3. Design Pattern

### 3.1 Contract-First (Protocols Before Implementations)

`engine/` was scaffolded before any flight code: `Protocol` classes for `PositionProvider`, `SLAMProvider`, `GPSProvider`, `FlightController`, `Camera`, `TelemetryBus`. Concrete implementations (`SimSLAM`, `SimFlightController`, `SimCamera`, `JSONLTelemetryLogger`) came later and bound to the Protocols structurally — no inheritance required.

```
engine/localization/__init__.py
───────────────────────────────

  @runtime_checkable
  class PositionProvider(Protocol):
      def start(self) -> None: ...
      def stop(self) -> None: ...
      def get_pose(self) -> Pose: ...
      def confidence(self) -> float: ...

  @runtime_checkable
  class SLAMProvider(PositionProvider, Protocol):
      """closedSpace-only."""

  @runtime_checkable
  class GPSProvider(PositionProvider, Protocol):
      """openSpace-only. FORBIDDEN in closedSpace."""
```

Two consequences:

- **Tests bind to Protocols, not Sim classes.** A future hardware adapter or Gazebo bridge can drop in without touching the test surface.
- **The forbidden-import rule is symbolic.** ISC-30 grep-checks for the literal string `GPSProvider` in `closedSpace/`. The Protocol is the contract *and* the static-analysis target.

### 3.2 Documentation-First — ISA Drives Code, Not the Other Way

Every Phase started with an ISA edit:

1. New ISCs appended (and any becoming-obsolete ones removed) under `## Criteria`.
2. New Features sketched under `## Features` with `satisfies: [ISC-...]` and `depends_on:` keys.
3. A dated `## Decisions` entry explaining why the work is shaped this way.

Only then did code begin. Each Phase commit message names the ISCs it flipped (`Phase 2 complete: engine Protocols (ISC-11, ISC-30, ISC-36)`).

The result is bidirectional traceability: every line of source ties back to an ISC; every ISC names the test that proves it; every test name appears in the ISA's Test Strategy block.

### 3.3 Fixture-First — Reference Warehouse As Spec Probe

Before the loader, validator, planner, or runner existed, `tests/fixtures/maps/reference_warehouse.yaml` was committed — a 64-capture-position fixture with two aisles, sixteen racks, and four shelf levels per rack. This fixture is referenced by ISC-1, ISC-5, ISC-7, ISC-16, and ISC-23.

On first integration, the fixture's geometry broke the validator (rack `A1-W4` overflowed the centerline by 0.05 m). The ISA Changelog 2026-05-03 records this with the conjecture/refutation/learning pattern:

```
- conjectured: rack centers 0.7 / 1.95 / 3.20 / 4.45 fit four 1.2 m
  racks inside a 5.0 m centerline with comfortable end buffers
- refuted by: validate() raised MapValidationError ('rack A1-W4
  extends outside centerline (position_along=4.45, length_m=1.2,
  centerline_length=5.000)') because 4.45 + 0.6 = 5.05 > 5.0
- learned: rack-extent semantic check works exactly as designed —
  the validator caught a geometry bug in the fixture *before* any
  flight code touched the map.
```

The validator did its job on day one. The fixture did its job too — by being wrong, it proved the firewall was holding.

### 3.4 Three-Tier CLAUDE.md

Three CLAUDE.md files exist, with non-overlapping scope:

- **Umbrella** (`/CLAUDE.md`): Python version, pytest, OpenSpec docstrings, exception discipline, engine contract rules.
- **closedSpace** (`closedSpace/CLAUDE.md`): SLAM only, 0.5 m clearance, <15 min battery, <50 ms latency.
- **openSpace** (`openSpace/CLAUDE.md`): GPS + IMU, geofencing, FAA classes, 60+ min duration.

The umbrella rule "never put domain-specific logic in the engine" is enforced by AST scan; the closedSpace rule "GPS forbidden" is enforced by grep; the openSpace rules are still aspirational until openSpace has code.

---

## 4. Architecture Pattern

### 4.1 Three-Layer Stack

```
┌──────────────────────────────────────────────────────────────────┐
│ Operator Layer                                                    │
│                                                                   │
│ closedSpace/run.py            ← CLI entry (`python -m ...`)       │
│ closedSpace/operator/cli.py   ← argparse + stdin abort thread     │
│ closedSpace/operator/runner.py← per-waypoint drive loop           │
│ closedSpace/operator/preflight.py← checklist (battery, pad, age)  │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ Domain Layer (closedSpace)                                        │
│                                                                   │
│ map/        ← YAML loader + JSON Schema + semantic validators     │
│ mission/    ← pure plan(Map) → MissionPlan; transit verifier      │
│ capture/    ← per-waypoint gate (resolution, focus) + sidecar     │
│ storage/    ← atomic local writer + sync coordinator              │
│ report/     ← mission report builder + schema validator           │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ Engine Layer (shared)                                             │
│                                                                   │
│ types.py        ← Pose (frozen dataclass)                         │
│ localization/   ← PositionProvider / SLAMProvider / GPSProvider    │
│ flight_control/ ← FlightController + ControllerState              │
│ sensors/        ← Camera + Frame + Laplacian focus_score          │
│ telemetry/      ← TelemetryBus + JSONL logger                     │
│ sim/            ← in-process reference impl for every Protocol    │
└──────────────────────────────────────────────────────────────────┘
```

Three properties hold across the stack:

- **Layers depend downward only.** Engine has no imports from `closedSpace`; closedSpace has no imports from `operator`. The first rule is AST-enforced; the second is convention.
- **State is concentrated.** Domain modules emit frozen dataclasses; the only stateful classes are `SimWorld`, `MissionRunner`, `CaptureSink`, `ReportBuilder`. Mutation lives where the lifecycle is.
- **Pure functions where possible.** `mission.plan` is pure (same map → same plan, byte-for-byte). The planner can be tested without standing up a sim.

### 4.2 The Engine as Contract Surface

The engine has one job: provide types and Protocols that mean the same thing to closedSpace and openSpace. It has no domain knowledge — the AST anti-bleed test enforces this.

```
engine/tests/test_no_domain_bleed.py
────────────────────────────────────

  Scans engine/ for any import whose top-level package is
  "closedSpace" or "openSpace". Any match fails the test.

  Currently 0 violations.
```

When openSpace eventually pulls on the engine, the Protocols may need to flex. The ISA's Rule-of-Three deferred extractions list (Decision 2026-05-03 OBSERVE/iter-2) names what *will* move when there's a second consumer: general geometry primitives (`Point2D`, `Point3D`, polygon utilities) and reference-frame conventions (+x east, +y north, +z up). Today they live in `closedSpace/map/types.py`; they earn promotion to `engine/geometry/` after openSpace lands.

### 4.3 Reference Sim As First-Class Test Substrate

`engine/sim` is not a mock library. It's a concrete `engine.flight_control.FlightController`, `engine.localization.SLAMProvider`, `engine.sensors.Camera`, and `engine.telemetry.TelemetryBus` that implements the Protocols with instant-snap kinematics and a deterministic synthetic image renderer.

```
SimWorld ←──── SimFlightController writes pose here
   ▲
   ├──── SimSLAM reads pose; confidence() returns 1.0 by default
   └──── SimCamera reads pose; renders a deterministic frame
```

Why this matters:

- **End-to-end testable without a real drone.** The 100-test suite includes a full mission e2e (`test_mission_e2e.py`) that flies the reference fixture through the sim and validates the resulting report against the JSON schema.
- **No conditional `if SIM:` branches.** The runner doesn't know it's in a sim. The same `MissionRunner.run()` will drive Gazebo or hardware once Phase 3 ships those adapters.
- **Sim confidence can be degraded.** `SimSLAM.set_confidence(0.0)` is the hook ISC-12's loss-of-tracking probe will use once the safety state machine is built.

The sim's limit is documented in its module docstring: *"Suitability gate: this sim is for unit + smoke testing. Anything that needs sensor fidelity (real SLAM drift, motion blur, lighting) must use the Phase 3 simulator behind the same Protocols."*

### 4.4 Local-First Durability

`closedSpace/storage/local.py` writes captures to local persistent storage *before* the runner advances to the next waypoint. The write pattern is atomic-rename: write to `.partial`, fsync, `os.replace()`. Sync to remote (S3/HTTP/NFS) is post-flight, idempotent, and never deletes the local copy.

```
Capture lifecycle
─────────────────

  1. Runner.execute(wp)
  2. cam.capture(pose) → Frame
  3. sink.consume(wp, frame)
        ├─ gate: resolution ≥ 4 MP
        ├─ gate: focus_score ≥ threshold
        ├─ compose path: warehouse/aisle/rack/level/timestamp.jpg
        ├─ compose sidecar (pose, mission_id, image_uri, ...)
        ├─ LocalSink.write() — atomic rename
        └─ → StoredArtifact
  4. ReportBuilder.record(outcome)
  5. Runner advances to next waypoint

  Post-flight:
  6. sync_to_remote(artifacts, remote)
        ├─ for each artifact: remote.upload(art)
        ├─ on SyncFailure: write .sync-pending marker, continue
        └─ never delete local
```

ISC-21 (local-first before next waypoint), ISC-22 (sync failure preserves local), and ISC-32 (`.sync-pending` marker on failure) are the contract; all three are covered by `test_local.py` + `test_sync.py`.

---

## 5. Development Pattern

### 5.1 Phase-Per-Commit Cadence

Six commits on `main`, each a named phase delivery:

| Commit | Phase | Scope | ISCs flipped |
|---|---|---|---|
| `f51a541` | — | Initial umbrella scaffold | — |
| `8764611` | Phase 0 | Foundations (venv, gitignore, engine skeleton, Makefile, ISC-5 dump) | ISC-5 |
| `1293a81` | Phase 1 | MissionPlanner | ISC-6..10 |
| `2108819` | Phase 2 | Engine Protocols | ISC-11, ISC-30, ISC-36 |
| `d806b80` | Phase 4 | Capture, storage, report | 9 ISCs |
| `5c45c9e` | Phase 5 | Operator CLI + preflight + abort | 6 ISCs |

Phase 3 (simulator bring-up) was implicitly delivered as part of Phases 1–5 in the form of the in-process kinematic sim; the *higher-fidelity* simulator decision (Gazebo / PX4 SITL / AirSim) is still open.

Each commit message names the deliverables and the ISCs flipped. Reviewing the project's progress means reading `git log --oneline` + the ISA's `## Criteria` block; both are designed to be skimmable together.

### 5.2 Quality Bar Enforced By Convention, Not CI (Yet)

`Makefile` collects every quality gate in one place:

```
make lint       → ruff check .
make typecheck  → mypy closedSpace engine
make test       → pytest
make all        → lint + typecheck + test
```

The bar is **`make all` clean** before any phase commit. As of `5c45c9e`:

- 100 tests pass in 52 s
- 97 % line coverage
- `mypy --strict` clean across 29 source files
- `ruff check` clean

No `.github/workflows/` exists yet — the bar is high but the enforcement is local. Phase 6 of `next-steps.md` lists CI as `partial`.

### 5.3 Test Strategy Is Three-Layered

```
Layer 1 — Per-module unit tests (mirrored under tests/)
  closedSpace/map/loader.py   →  closedSpace/tests/map/test_loader.py
  closedSpace/mission/plan.py →  closedSpace/tests/mission/test_plan.py
  ...
  → 73 tests, sub-second each

Layer 2 — Static-analysis tests for cross-cutting invariants
  engine/tests/test_no_domain_bleed.py  ← AST scan
  → ISC-30, ISC-36 enforced at every test run, not just at review

Layer 3 — End-to-end mission against the in-process sim
  closedSpace/tests/test_mission_e2e.py
  → fixture-fly the reference warehouse; validate report against schema
  → catches integration regressions (CLI → runner → sink → builder → schema)
```

Tests are co-located with source (`closedSpace/map/loader.py` → `closedSpace/tests/map/test_loader.py`). The convention is uniform across all 14 source modules.

### 5.4 The ISA's Decisions Log As Process Memory

Every architectural choice is dated and recorded in the ISA's `## Decisions` block. Examples:

- **2026-05-03 OBSERVE/iter-2 — Warehouse-map definition stays in closedSpace, not promoted to engine.** Reasoning: aisles, racks, shelf levels are intrinsically indoor concepts; promoting now would either drag closedSpace into a "shared" zone openSpace must ignore, or create a single-consumer zone. Rule-of-Three deferred extractions named: `Point2D/Point3D`, polygon utilities, reference-frame conventions move when openSpace consumes them.
- **2026-05-03 OBSERVE/iter-4 — Map staleness as first-class concern.** Reasoning: warehouses re-rack constantly; a map drifts the moment the next pallet moves. ISC-43 (loader exposes `surveyed_at` / `surveyed_by`) and ISC-44 (preflight refuses stale maps past `MAX_MAP_AGE_DAYS`) encoded the policy.
- **2026-05-03 PLAN/iter-6 — Roadmap committed to `next-steps.md` with three open decisions blocking Phase 3.** D1 (sim-first vs hardware-first), D2 (simulator choice), D3 (flight stack). All three have recommendations, none have been ratified.
- **2026-05-03 VERIFY — Thinking-floor doctrine deviation flagged.** "E3 hard floor is ≥4 thinking capabilities invoked via Skill/Agent tool; this run invoked ISA only. ... Flagged rather than hidden. Natural remediation: spawn FirstPrinciples + RedTeam against this ISA before implementation begins." This is honest record-keeping. The remediation has not yet been executed.

The pattern: every decision carries its date, its alternatives, its reason, and its blast radius. A new engineer can read the log in fifteen minutes and know not just *what* the design is but *why each fork was taken*.

### 5.5 Roadmap As Living Companion (`next-steps.md`)

`closedSpace/docs/next-steps.md` is the project's work order: nine phases (NS-0 through NS-8), deliberate-day estimates, status per task, and three open decisions (D1/D2/D3) that gate Phase 3.

```
Roadmap at-a-glance (May 2026)
──────────────────────────────

  Phase 0  Foundations                  1–2d   ✅ done
  Phase 1  MissionPlanner               3–5d   ✅ done
  Phase 2  Engine contracts             2–3d   ✅ done
  Phase 3  Simulator bring-up           5–10d  ⏳ decision needed (D1, D2)
  Phase 4  Capture + Storage + Report   4–6d   ✅ done
  Phase 5  OperatorConsole + preflight  3–4d   ✅ done
  Phase 6  Quality gates + anti-scope   2–3d   ◐ partial (CI missing)
  Phase 7  MapBuilderFromWMS            5–10d  □ sketched
  Phase 8  Pilot mission (real ware.)   5+d    □ not-started

  Total to pilot, single engineer: ~25–45 deliberate-days.
```

The phases are non-strict — Phases 4 and 5 shipped before Phase 3 because the in-process kinematic sim was sufficient. Phase 3's "real" task — choosing Gazebo or PX4 SITL — sits idle until D1/D2 are answered.

---

## 6. Key Decisions and Their Rationale

### Decision 1: Umbrella with two domain packages, not one package with a mode flag

**Why:** The failure modes have zero overlap. A `mode='indoor'` flag would have led to a codebase littered with `if mode == 'indoor': ... else: ...` checks at every safety boundary. Two packages with a shared engine puts the boundary in import paths, not in runtime branches. The AST anti-bleed test makes it mechanical.

**Trade-off:** Until openSpace has code, the engine is single-consumer. The shared contract is inferred from one use case, which means some of today's Protocols may over-fit to closedSpace.

### Decision 2: Protocols before implementations

**Why:** Concrete classes are easy to test against, hard to swap. Protocols force the contract to be named explicitly. They also let the in-process sim and a future Gazebo bridge share the same surface — no `SimAdapter` / `RealAdapter` indirection layer.

**Trade-off:** Tests can pass against the Protocols and still fail against an implementation if the Protocols don't capture every real-world precondition. Mitigated by `@runtime_checkable` + structural conformance tests.

### Decision 3: ISA-as-system-of-record (no separate PRD / acceptance / spec)

**Why:** A parallel artifact diverges. One document with twelve sections covers Problem → Vision → Out-of-Scope → Principles → Constraints → Goal → Criteria → Test Strategy → Features → Decisions → Changelog → Verification. A new engineer reads one file, finds their first ISC, and ships a PR.

**Trade-off:** The file is 634 lines. Search-by-ISC-number is fast; search by topic requires familiarity with the convention.

### Decision 4: Fixture-first — reference warehouse before any flight code

**Why:** The fixture is the contract probe. If the loader, validator, planner, and runner all accept the reference fixture without flagging, the integration is end-to-end coherent. The fixture caught a geometry bug on day one — the firewall worked before any flight code existed.

**Trade-off:** One fixture is not exhaustive; property-based tests against the JSON Schema would broaden coverage cheaply.

### Decision 5: Map staleness is first-class (ISC-43 / ISC-44)

**Why:** Warehouses re-rack constantly. A drone flying a stale map will collide with new shelves. The pre-flight gate (`PreflightChecklist._check_map_staleness`) refuses stale maps past 30 days unless `--allow-stale-map` is set AND the map carries non-null `surveyed_at`. Null provenance is a non-blocking warning — not a silent pass.

**Trade-off:** The 30-day default is a guess. A real deployment will need per-warehouse calibration based on observed re-rack frequency.

### Decision 6: Two-tier simulator strategy

**Why:** A pure in-process kinematic sim ships in days and runs the full mission e2e in 52 s. Gazebo or PX4 SITL takes weeks to wire up and runs orders of magnitude slower. Both behind the same Protocols means unit tests stay fast and integration tests gain fidelity later.

**Trade-off:** The in-process sim cannot probe ISC-12, ISC-13, ISC-14, ISC-31, or ISC-33 by construction. These ISCs sit `[ ]` until the second tier lands.

### Decision 7: Defer flight-stack choice until hardware bring-up

**Why:** `engine.flight_control.FlightController` is a Protocol. PX4, ArduPilot, or a vendor SDK all bind to the same surface. Choosing today is premature — the choice depends on which drone the pilot site uses, which depends on D1 (sim-vs-hardware).

**Trade-off:** When D1 activates the hardware path, three weeks of integration work appear at once. Documented in `docs/drones.md` with vendor categories and rough cost estimates.

### Decision 8: Single-drone, single-mission v1 (out of scope: choreography)

**Why:** Multi-drone coordination is a different problem class (collision avoidance between drones, choreographed handoffs). The data model doesn't anticipate it. Adding it later won't be a small change — but neither would building it now and using none of it.

**Trade-off:** The boundary should be surfaced in the umbrella docs before Phase 7 (WMS builder) so it isn't assumed-away by a vendor adapter.

---

## 7. What This Pattern Teaches

### Lesson 1 — Engineering discipline can be front-loaded into the spec, and the spec then enforces it on the code

The ISA-with-ISCs pattern is the most striking thing about this project. It is genuinely a system-of-record: every ISC has a probe, every probe lives in the test suite, every Decision is dated, every Changelog entry uses the conjecture/refutation/learning trio.

This is not zero-cost. The ISA is 634 lines on a project that is 5,010 lines of code — roughly 1:8 doc-to-code ratio, where most projects sit at 1:50 or worse. The investment pays off when the codebase grows: each new contributor has one document to read, every line of source has an ISC that anchors it, and architectural drift is bounded by the Decisions log's blast-radius discipline.

The lesson is not "always write an ISA" — it is "the highest-leverage docs are the ones the code is forced to obey".

### Lesson 2 — Anti-rules need static probes, not vigilance

"Don't import GPS in closedSpace" is the kind of rule that fails silently. A junior engineer adds it; nobody notices in code review; the indoor drone crashes when GPS lookup blocks for 3 seconds inside a steel rack. The rule needs a *probe*, not a guideline.

dronePrjs encodes three anti-rules as static probes:

- **ISC-30:** `grep -r "GPSProvider" closedSpace/` returns zero.
- **ISC-35:** dependency graph scan — no CV/OCR library imported.
- **ISC-36:** AST scan of `engine/` for any `closedSpace`/`openSpace` import.

These run in every `make test`. When a rule moves from convention to probe, it moves from "should hold" to "does hold" — a meaningful upgrade.

### Lesson 3 — The reference sim is worth building, even though it can't probe what matters

`engine/sim` cannot probe latency, clearance, SLAM drift, or collision rate. Those need real sensors or a high-fidelity simulator. But it *can* probe:

- Are the wiring contracts right? (e.g., does the runner advance only after the sink confirms?)
- Are the report fields populated correctly? (e.g., does `coverage_pct` match `captured / planned * 100`?)
- Are the schemas honoured end-to-end? (e.g., does the produced `mission_report.json` validate against `mission_report.schema.json`?)
- Are the state transitions legal? (e.g., does `disarm()` raise when AIRBORNE?)

These are the bugs that show up in real flights as "the drone landed fine but the report says it captured zero images". Catching them in 52 s of unit tests before any real-hardware time is bought is high-leverage work.

The trap to avoid is *believing* the sim's claims about latency or clearance. The ISA marks those ISCs `[ ]` honestly — the bar to flip them is a probe against a fidelity-tier simulator or real hardware, not the in-process kinematic sim.

### Lesson 4 — Acknowledge the umbrella's single-consumer state

The umbrella's value proposition is "shared engine for two domains". As of May 2026, that's "shared engine for one domain plus a stub". The engine Protocols are shaped by one consumer; some of today's Protocols may not survive the first time openSpace pulls on them.

The honest framing: today's `engine/` is "*provisional* shared engine — designed for two consumers, exercised by one". The ISA's Rule-of-Three deferred extractions list names what *will* move when there's a second consumer. The discipline is to resist promoting more code than the second consumer actually demands.

### Lesson 5 — Phase-per-commit is a forcing function for keeping commits coherent

Six commits, six phases. Each commit's diff is one phase's worth of code; each commit message names the ISCs flipped. This makes the git log usable as a project history, not just a record of edits. It also means rollback semantics are clean — reverting a phase reverts a coherent unit of work, not a fragment.

The lesson is not "always commit in big phases" — small commits have their own virtues — but "let the commit boundary mean something the reviewer can act on". On a project with this much scope discipline, "phase" is a meaningful unit.

### Lesson 6 — Flagging doctrine deviations beats hiding them

The ISA's 2026-05-03 VERIFY entry says, in essence: *I was supposed to invoke four thinking capabilities; I invoked one. Here's the remediation.* The remediation has not yet been executed.

This pattern — flag the deviation in the same document that recorded the rule — is rare. The temptation is to either silently skip the rule or weaken the rule. Flagging it means future-you (or any reviewer) can spot the open commitment and close it.

The unfinished remediation is itself a lesson. *Flagging is necessary but not sufficient.* Phase 6 (or a Phase 2.5 pre-Phase-3 review) should close the loop before pilot.

---

*Analysis based on commit `5c45c9e` on `main`. Quality probes (`make all` + coverage) run locally before this writeup; all green at the time of review.*
