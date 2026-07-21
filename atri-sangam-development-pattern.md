# Atri Sangam — Scoping, Design, Architecture & Development Pattern

> ⚠️ **STALE — superseded in part, 2026-07-21.** This document analyses the
> **v0.1.0 source snapshot of 2026-07-18** and its central thesis — "a
> detection library and red-team simulator, not a deployable monitor" — is
> **no longer true**. In the three days after it was written, 126 commits added
> a runner, a systemd unit, WWVB and Roughtime channels, C/N₀ analysis, a
> TimescaleDB backend and a live dashboard. Read it as a record of how the
> project scoped its *first* release; do not read its present-tense claims
> about what exists as current. Current state:
> [atri-sangam-critique.md](atri-sangam-critique.md) (v2.0, `d953201`).


**Document type:** Development pattern analysis
**Scope:** Design & scoping methodology of a stdlib-only GPS/PNT integrity-monitoring library + red-team simulator
**Period:** Source snapshot dated 2026-07-18 — **no git history in the reviewed artifact**, so this document analyzes the *design methodology visible in the code and specs*, not a commit arc (contrast dronePrjs, whose pattern was read off an 8-commit burst)
**Author:** WeGoFwd2020 / Claude (Anthropic)
**Related:** [atri-sangam-critique.md](atri-sangam-critique.md) · [atri-sangam-practices.md](atri-sangam-practices.md)
**Note:** The reviewed artifact is an extracted tree — 1,961 source LOC across 23 files, 719 test LOC across 7 files, 66 tests passing at 90 % coverage, 6 OpenSpec contracts, `Development Status :: 3 - Alpha`, `v0.1.0`, MIT. There are **no commits to read**. Where dronePrjs let us watch phase-per-commit cadence, here the development pattern must be inferred from what the code and specs *are*: how scope was drawn, what was built, and — just as tellingly — what was deliberately left unbuilt.

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

A fixed installation — a substation, a telecom site, a data center, a timing lab — trusts a single GPS receiver for time and position. GPS is the most precise reference available (nanoseconds) and the most trivially attackable: a $30 SDR can jam it, and a slightly more sophisticated one can *spoof* it, walking the reported time or position away from truth slowly enough that nothing downstream notices until a log timestamp is hours wrong or a phasor measurement is meaningless.

Atri Sangam does not try to make GPS harder to spoof. It answers a narrower, more tractable question:

```
The problem in one frame
─────────────────────────

  "At a site whose antenna position was surveyed once and is thereafter
   treated as truth, decide — from several mutually independent references
   that would not all fail the same way — whether the GPS receiver is
   currently lying, and raise an alarm that says exactly why."
```

The design thesis is in the name. A *sangam* — a confluence, and the classical Tamil academy where independent voices reached consensus by collective judgment (`README.md:11-20`) — of channels that do not share a failure mode:

```
  GPS (NMEA RMC/GGA) ──► gps_time_offset ───┐
                     └──► gps_position_error ┤
  SNTP (RFC 4330) ───────► ntp_time_offset ──┤   residual streams
  Local-clock holdover ──► holdover_residual ┼──► DiscrepancyEngine
  Solar predictor (+sensor)► solar_residual ─┘         │        │
                                                  step+CUSUM  staleness
                                                        ▼        ▼
                                              SQLite store · provenance-carrying Alarms
```

Each channel emits a scalar *residual* (observed minus what a trusted reference predicts). When the channels stop agreeing, the disagreement itself is the alarm signal. The precision hierarchy is stated honestly up front — GPS is nanoseconds, radio time milliseconds, celestial observation seconds (`README.md:22-25`, `openspec/project.md:60`) — because the mission is *detection*, not competing with GPS on accuracy: a millisecond-grade reference is more than good enough to catch a spoof that has walked time by whole seconds.

The central honesty this document keeps returning to: **what exists is a detection-logic library and a red-team simulator, not a deployable monitor.** There is no collection loop, scheduler, serial/gpsd runner, or daemon anywhere in the tree; `check_staleness()` (`discrepancy/engine.py:102`) must be called on a cadence by something that has not been written yet. The "live" dashboard replays a store that was filled to completion before the server started (`dashboard/app.py:144-146`). This is not a defect hidden in the code — it is a scoping decision, and the interesting thing is how cleanly the boundary was drawn.

---

## 2. Scoping Pattern

### 2.1 Scope Anchored by Independence, Not by Feature

The first scoping question was not "what features does a GPS monitor need" but *"which references fail independently of GPS and of each other?"* That question is what produced the channel list, and it is why the channels look heterogeneous:

| Channel | Independent of GPS because… | Precision |
|---|---|---|
| `ntp_time_offset` | comes over the network from a different clock | ms |
| `holdover_residual` | comes from the local oscillator's own physics | µs/s drift |
| `solar_elevation_residual` | comes from the sky and an ephemeris, needs no radio at all | seconds / degrees |
| `gps_position_error` | the surveyed antenna position is fixed truth | meters |

The taxonomy is deliberate: a network attacker who owns NTP does not own the Sun; a jammer who kills GPS does not change the local oscillator's drift rate. Scoping by *failure-mode independence* rather than by feature is the defining move — it is why a fixed-site monitor, and not a general GPS library, is the thing that got built.

### 2.2 Attacks Scoped Into Exactly Three Detector Shapes

The threat model was compressed to three shapes, and the detector layer is a one-to-one image of it (`README.md:45-54`):

```
  step      → jumps      (crude spoofing, glitches)      per-sample threshold
  cusum     → slow walks (sophisticated spoofing)        two-sided tabular CUSUM
  staleness → silence    (jamming, outage, dead cable)   per-channel max sample age
```

This is a scope decision disguised as an architecture decision. By asserting that *every* GPS anomaly worth catching is a jump, a walk, or a silence, the project bounds its own detection surface to three well-understood algorithms. Anything subtler — C/N₀ uniformity analysis, multipath signatures — is explicitly pushed to the roadmap (`README.md:118`), not half-implemented.

### 2.3 Subtractive Scoping — The Roadmap as an Out-of-Scope List

dronePrjs kept an explicit `## Out of Scope` block. Atri Sangam has no ISA, but it does the same work through its **roadmap** (`README.md:112-119`), which reads as a list of things deliberately *not* in v0.1.0:

```
  - WWVB (60 kHz) radio-time channel ........ deferred (best $/independent-time)
  - Sun-sensor / camera channel ............. deferred (predictor is built; sensor isn't)
  - Star-tracker channel .................... deferred (night-time position recovery)
  - gpsd / pyserial runner + systemd unit ... deferred (the "monitor" itself)
  - C/N₀ uniformity from GSV ................ deferred (a spoofing tell)
  - TimescaleDB store ....................... deferred (behind the same interface)
```

The discipline visible here is that each deferred item is named *and left absent* rather than stubbed. The solar channel is the sharpest example: the predictor is fully implemented and tested (`predictors/solar.py`, `elevation_residual_deg` at `:125-140`), the channel constant `CH_SOLAR` is registered with a default detector bundle (`models.py:23`, `config.py:141-144`) — but nothing wraps a solar observation into a `Sample`, because the sun-sensor hardware that would produce the observation is roadmap. The math shipped; the fabricated data did not. That is subtractive scoping done honestly: the seam is present, the half-built feature is not.

### 2.4 The Simulator Scoped as a First-Class Deliverable

Most projects treat test data as scaffolding. Here the `NmeaSimulator` is a scoped product surface in its own right, with its own OpenSpec contract (`openspec/specs/simulation/spec.md`) and an explicit triple mandate in its module docstring (`simulators/nmea_sim.py:3-9`): mock data, demo driver, **and red-team tool** — the deploy guide tells operators to point it at their own thresholds to verify an attack of a given profile would be caught (`README.md:80-83`). Scoping the adversary generator as a first-class deliverable, rather than a test fixture, is what lets the same 300-odd lines serve the test suite, the `atri-sangam-demo` CLI, and a customer's threshold-tuning workflow.

---

## 3. Design Pattern

### 3.1 Specs-as-Contracts — Numeric Scenarios the Tests Mirror to the Decimal

Six OpenSpec files under `openspec/specs/` carry the behavioral contract, and their distinguishing feature is that scenarios are *numeric*, not prose. The NTP spec does not say "compute the offset correctly" — it pins the arithmetic:

```
ntp-time/spec.md — Scenario: Deterministic offset from a crafted exchange
  GIVEN server receive/transmit 1005.1, local clock 1000.0 send / 1000.2 receive
  THEN the reported offset is 5.0 s and the delay is 0.2 s
```

and the acceptance test asserts exactly those numbers against a fake socket. The same holds for the CUSUM contract: the spec fixes "a 0.002 s/s time walk … peak offset ~0.34 s … no step alarm … at least one cusum alarm" (`anomaly-detection/spec.md:33-38`), and `test_detectors.py:78-92` reproduces it, hand-computing that `0.002 × 199 = 0.398 < 0.5` so the drift provably stays under the step threshold while tripping CUSUM — a genuine *separation* test, not a smoke check. The pattern is that a design commitment is not considered stated until a decimal-exact scenario exists and a test mirrors it. Design commitments are verified true, not merely asserted (`README.md:99-110`).

### 3.2 Everything-Injectable — Determinism as a Design Rule

Every external dependency of every component is a constructor parameter. The SNTP client takes its `socket_factory` and `time_func` (`collectors/ntp.py:66-74`); the simulator takes its `seed` (`simulators/nmea_sim.py:152-159`); the engine takes its `store` (`discrepancy/engine.py:48`); the holdover model takes its window. Nothing reaches out to the world on its own initiative.

The payoff is that the *entire* test suite is deterministic and offline — the SNTP four-timestamp exchange is verified with zero network access by handing the client a fake socket that answers with crafted bytes. This is stated as an explicit design commitment ("Everything injectable … so the entire test suite is deterministic and offline", `README.md:106-108`) and it is implemented, not aspirational. Injection is not here for flexibility's sake; it is here so that a monitor whose job is to detect non-determinism in the world can itself be tested with none.

### 3.3 Pure-Transformer Collectors Decoupled From I/O

The collectors contain no I/O. `GpsSampleFactory.samples_from_rmc` (`collectors/gps.py:29-64`) takes a *sentence string* plus the local clock reading and returns 0–2 `Sample` objects — there is no serial port, no gpsd, no file handle anywhere in the class. Its own docstring names the split: "Serial/gpsd I/O lives in a thin runner (future work) so that all the logic here is unit-testable" (`collectors/gps.py:5-7`). The holdover model likewise is pure arithmetic over injected `(t, offset)` points (`collectors/holdover.py:44-66`); even the NTP path separates the wire protocol (`SntpClient.query`) from the sample-shaping adapter (`NtpCollector.collect`).

This is the design decision that makes §2.3's honesty *possible*: because the transforming logic is already fully separated from the transport, the missing runner is a genuinely thin shell to write later, and its absence does not compromise the testability of everything below it.

### 3.4 Stdlib-Only Core as an Air-Gap Commitment

`dependencies = []` in `pyproject.toml:23`, with a comment stating the reason: the core "must run in air-gapped / degraded environments, which is the whole point of the project." Dash and Plotly are an optional extra (`pyproject.toml:26`), and — crucially — the dashboard *lazy-imports* them inside `create_app`, raising a clear actionable error if the extra is absent (`dashboard/app.py:43-51`) rather than failing at package import. The design rule is that nothing on the core monitoring path may require a wheel from PyPI. A monitor built for the exact degraded conditions GPS attacks create cannot itself depend on network reachability to install; the empty dependency list is that principle made mechanical.

### 3.5 Fail-Loud Validation in `__post_init__` on Every Dataclass

Every configuration and value object is a frozen, slotted dataclass that validates at construction and raises a typed exception: `SiteConfig` range-checks latitude/longitude (`config.py:43-51`), `CusumConfig` rejects `k < 0` / `h ≤ 0` (`config.py:72-76`), `StepConfig` rejects a non-positive threshold (`config.py:94-98`), `DetectorConfig` rejects a non-positive `max_sample_age_s` (`config.py:109-113`). The stated intent is that an invalid configuration "fails loudly at startup rather than producing silent nonsense at 3 a.m. during an actual GPS event" (`config.py:4-6`). Combined with the typed exception hierarchy (`exceptions.py` — `NmeaChecksumError(NmeaParseError)`, `ThresholdConfigError(DetectorError, ConfigError)`), the design lets a caller catch at any granularity while guaranteeing that no nonsensical detector ever gets constructed.

### 3.6 No Fabricated Data as a Safety Invariant

A design rule stated three times across the code and docs (`README.md:104-106`, `openspec/project.md:66-68`, `collectors/gps.py:43-45`): when a channel fails, the failure *propagates* — collectors raise `CollectorTimeout` / `NtpQueryError`, a void GPS fix returns `[]` rather than a fake zero (`collectors/gps.py:51-52`) — and the resulting silence is caught by staleness detection. "A monitor that invents readings is worse than none." This is the invariant that ties the detector taxonomy together: *silence is a first-class anomaly*, so the honest thing (emit nothing) and the safe thing (get caught by the staleness layer) are the same thing.

---

## 4. Architecture Pattern

### 4.1 Fan-In Referee

```
┌──────────────────────────────────────────────────────────────────┐
│ Collector Layer (pure transformers)                               │
│   collectors/nmea.py   ← RMC/GGA parse + XOR checksum             │
│   collectors/gps.py    ← RmcData → [time_offset, position_error]  │
│   collectors/ntp.py    ← SNTP exchange → ntp_time_offset          │
│   collectors/holdover.py← windowed least-squares → residual       │
│   predictors/solar.py  ← ephemeris → elevation residual (no Sample yet)│
└──────────────────────────────────────────────────────────────────┘
                              │  Sample(channel, timestamp, value)
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ Discrepancy Layer (the referee)                                   │
│   discrepancy/engine.py ← routes samples; per-channel health       │
│   discrepancy/step.py   ← instantaneous threshold                 │
│   discrepancy/cusum.py  ← two-sided tabular CUSUM                 │
│   (staleness lives in the engine — it is about absence of samples)│
└──────────────────────────────────────────────────────────────────┘
                              │  Alarm(channel, detector, value, threshold, message)
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ Persistence + UI                                                  │
│   storage/store.py     ← SQLite; samples + alarms tables          │
│   dashboard/app.py     ← optional Dash; replays a finished store  │
└──────────────────────────────────────────────────────────────────┘
```

Three properties hold across the stack:

- **Data flows one way, as frozen values.** `Sample` and `Alarm` are frozen slotted dataclasses (`models.py:34-73`); collectors never see detectors, detectors never see storage. The only stateful objects are the ones with a genuine lifecycle: `DiscrepancyEngine`, the per-channel detectors, `HoldoverModel`, and `SqliteStore`.
- **The engine is a thin router.** `DiscrepancyEngine.ingest` (`engine.py:67-99`) does exactly one thing per sample: fetch-or-build the channel's detector bundle, run step and CUSUM, record health, optionally persist. The domain intelligence is in the detectors, not the referee.
- **Channels are plain strings.** The engine keys everything off `sample.channel` (`engine.py:54-64`), which is what makes §4.3 possible.

### 4.2 Lazy Auto-Registration as a Third-Party Extensibility Seam

The engine builds a channel's state on first sample, looking up its detector bundle through `MonitorConfig.detector_for`, which falls back to a module-level `FALLBACK_DETECTOR` for any unknown channel name (`engine.py:54-64`, `config.py:150-153`, `config.py:170-172`). The consequence is architectural, not cosmetic: **a third party can add a WWVB, star-tracker, or any other channel by emitting `Sample("wwvb_time_offset", …)` — no edit to this package is required.** The channel constants in `models.py:19-23` exist only to prevent typos on the built-ins; they are not an enum the engine switches on. This is the seam through which every roadmap channel is meant to arrive, and it already works today for anything a downstream user cares to feed it.

### 4.3 The Simulator as a Deterministic Red-Team Substrate

`NmeaSimulator` renders scenarios (`Clean`, `TimeWalk`, `PositionJump`, `Dropout` — `nmea_sim.py:36-97`) into checksum-valid NMEA, seeded so a given `(site, start, seed, scenario)` yields **byte-identical** streams (`nmea_sim.py:184`, spec `simulation/spec.md:18-23`). Architecturally this one component substitutes for three things that would otherwise be separate:

- **The whole test suite's data source** — every detector test runs against synthetic sentences, no hardware.
- **The demo driver** — `atri-sangam-demo --scenario …` and the dashboard both replay it (`demo.py:38-43`, `dashboard/app.py:137`).
- **The customer's red-team tool** — a deployed operator injects their own `TimeWalk(rate_s_per_s=…)` to confirm their tuned thresholds would alarm.

Because the simulator produces the same wire format a real receiver would (`_wrap` computes a genuine XOR checksum, `nmea_sim.py:134-135`), the pipeline under test — `NmeaSimulator → GpsSampleFactory → DiscrepancyEngine → SqliteStore` — is the *same* pipeline a real deployment would run, minus only the transport shell. The end-to-end acceptance spine in `test_engine.py` exercises exactly that chain for all four scenarios.

### 4.4 SQLite as a Deliberately Minimal, Interface-Bounded Store

`SqliteStore` (`storage/store.py:40-56`) is two tables (`samples`, `alarms`) with two indices, opened on a file path or `:memory:`. The choice is defended in the module docstring: zero external services fits the degraded-environment mission, and the schema is simple enough to migrate to TimescaleDB later *behind the same interface* (`store.py:2-8`, roadmap `README.md:119`). The architecture bets that the read/write method surface (`add_sample`, `add_alarm`, `samples`, `alarms`, `channels`) is the stable contract and the backing engine is swappable — the same interface-first move dronePrjs made with its Protocols, done here with a concrete class whose method set is the seam.

---

## 5. Development Pattern

> **No commit history is available in this snapshot.** The subsections below therefore document the development *discipline the artifact evidences* — the quality gates, the test architecture, the doc-code coupling — rather than a cadence. Where dronePrjs let us say "six commits, six phases," here we can only say "this is the state the discipline produced."

### 5.1 Quality Gate: Real CI, but No Lint/Type Enforcement

`.github/workflows/ci.yml` runs a genuine gate: `pytest --cov` across a Python 3.10 + 3.12 matrix, plus a second job that installs the `[dashboard]` extra and re-runs the suite so the optional-import path is exercised in CI (`ci.yml:9-33`). That dashboard-extra job is a nice touch — it catches the class of bug where an optional dependency's import path rots unnoticed.

The gap, consistent with the critique, is that **there is no lint or type gate**: no ruff, no `mypy --strict` config anywhere in the tree. The code *reads* type-clean and carries `from __future__ import annotations` throughout, but nothing enforces it — a regression that a sibling project (dronePrjs, with `mypy --strict` in its bar) would catch in CI would pass here. The quality bar is "tests green at 90 % coverage," not "tests + types + lint green."

### 5.2 Test Architecture: Two Tiers, Hand-Derived Assertions

The 66 tests (719 LOC across 7 files) split into two tiers the project's own conventions name (`openspec/project.md:38-45`):

```
Unit tier — parsers, detectors, models, solar, simulator
  test_nmea.py       XOR checksum verified by hand
  test_detectors.py  CUSUM/step separation; holdover drift to 1e-9
  test_ntp.py        4-timestamp offset to the decimal from a crafted socket
  test_solar_store_demo.py  physical invariants (equinox dec ≈ 0, noon el > 85°)

Integration tier — the acceptance spine
  test_engine.py     simulator → GPS factory → engine → alarms/store, all 4 scenarios
```

The distinguishing quality is that assertions are *hand-derived*, not golden-file smoke: the SNTP offset is computed to 5.0 s from crafted timestamps (`test_ntp.py`), holdover drift is recovered to `1e-9` (`test_detectors.py:117-126`), and the solar tests assert physical invariants rather than over-fitting to computed values (`test_solar_store_demo.py`). The known holes are at the *seams* — `samples_from_rmc` has no direct unit test, `NtpCollector.collect()` failure-propagation is untested, and `DiscrepancyEngine.status()` has zero coverage — which is exactly where the critique points its test-coverage findings.

### 5.3 Doc-Code Coupling: Every Module Names Its Governing Spec

A convention holds uniformly across the source: every module docstring ends with a `Spec: openspec/specs/<capability>/spec.md` line (`config.py:8`, `engine.py:8`, `cusum.py:9`, `collectors/nmea.py:8`, `collectors/gps.py:8`, `predictors/solar.py:13`, `storage/store.py:7`, and so on). The exception hierarchy even documents the *inverse* linkage — each capability spec lists which exceptions its requirements may raise (`exceptions.py:6-9`). This is bidirectional traceability achieved without an ISA: from any source file you can find its contract, and from any spec you can find the numeric scenario a test must mirror. `openspec/project.md` sits above all six specs as the shared context — purpose, tech-stack constraints, conventions, and the domain glossary (channel / residual / precision hierarchy).

### 5.4 The Missing Runner as the Development Frontier

The single most important development-state fact: **the collection loop does not exist.** Every collector is a one-shot call, and `check_staleness(now)` must be driven on a cadence (`engine.py:102-139`). The only thing that drives the full pipeline today is `demo.run_scenario` (`demo.py:46-81`), which iterates the *finite* simulator generator and calls `engine.ingest` / `engine.check_staleness` in a loop — and the dashboard's `main()` runs that scenario to completion *before* starting Dash (`dashboard/app.py:144-146`), so the "live" UI is a replay of a finished dataset polled by a `dcc.Interval`. The development frontier is therefore sharply defined: a `gpsd`/`pyserial` runner that puts `GpsSampleFactory` on a real byte stream and `NtpCollector` / `HoldoverModel.update` / `check_staleness` on timers turns this library into the monitor its README describes. Section 3.3's pure-transformer discipline is what makes that runner a thin shell rather than a rewrite.

---

## 6. Key Decisions and Their Rationale

### Decision 1: Ship a detection library + red-team simulator before a runner

**Why:** The hard, novel, testable part of a PNT integrity monitor is the *detection logic and its calibration*, not the plumbing that reads a serial port. By building the transformers, detectors, engine, store, and a deterministic adversary generator first — all unit-testable offline — the project front-loads the part where correctness is subtle and defers the part where correctness is mechanical.

**Trade-off:** The artifact is not deployable as a monitor, and a skim of the README (whose diagram and "How it works" read in the present tense) implies more is wired than is. Honest on close reading; overstated on a glance. This is the critique's headline framing, and this document agrees with it.

### Decision 2: Stdlib-only core, dashboard as a lazy-imported optional extra

**Why:** The environments a GPS attack creates — degraded, possibly air-gapped — are precisely where a `pip install` from PyPI cannot be relied on. `dependencies = []` guarantees the monitoring path never needs a wheel; the lazy import in `create_app` keeps the Dash requirement off the core path entirely.

**Trade-off:** No pandas/numpy means the holdover least-squares and solar ephemeris are hand-rolled in pure Python (`holdover.py:58-66`, `solar.py:82-122`). Correct and dependency-free, but the numerics are the project's to maintain and verify rather than a library's.

### Decision 3: Channels as strings + fallback detector, not an enum

**Why:** A closed enum of channels would force every new reference (WWVB, star-tracker) to edit the core package. Plain-string channels plus `FALLBACK_DETECTOR` auto-registration make third-party extension a matter of emitting a `Sample` with a new name — the extensibility seam is free and already exercised by the fallback path.

**Trade-off:** No compile-time guarantee that a channel name is spelled correctly; a typo silently creates a new channel with fallback thresholds rather than erroring. The `CH_*` constants mitigate this for the built-ins but cannot for user channels.

### Decision 4: Specs carry decimal-exact scenarios the tests must mirror

**Why:** "Detect a slow walk" is untestable; "a 0.002 s/s walk peaking at ~0.34 s fires CUSUM but not step" is a test. Numeric OpenSpec scenarios make each behavioral commitment falsifiable, and mirroring them one-for-one in the acceptance suite means the contract and the proof cannot silently diverge. The project treats a changed threshold or astronomy constant as a **breaking change under SemVer even with no signature change** (`openspec/project.md:50-52`) — numerical behavior *is* the public contract.

**Trade-off:** Spec mirroring is currently partial — some scenarios (`nmea-ingestion`'s valid-fix/void-fix pair, `ntp-time`'s failure-produces-no-sample) have no dedicated test yet, so the "one-for-one" claim is an aspiration the suite has not fully met.

### Decision 5: No fabricated data — failures propagate, silence is an anomaly

**Why:** A monitor that invents a plausible reading when a channel fails defeats its own purpose. Raising typed exceptions and returning `[]` for a void fix, then catching the resulting silence with a dedicated staleness layer, means every failure mode surfaces as either an exception at the seam or a staleness alarm downstream — never as a fake zero that reads as healthy.

**Trade-off:** Puts weight on the staleness cadence that does not exist yet (Decision 1): silence is only caught if `check_staleness` is actually being called on a timer, which today only the demo loop does.

### Decision 6: Build the solar predictor, defer the solar channel

**Why:** The ephemeris math (USNO/Meeus low-accuracy solar position, `solar.py:1-13`) is pure, verifiable against known astronomical invariants, and worth having ready. The *observation* half needs a sun sensor that is roadmap hardware. Shipping the predictor while leaving the `Sample`-producing wrapper unwritten keeps the celestial channel honest — the capability the diagram shows is aspirational, and the code says so by omission rather than by a fake feed.

**Trade-off:** `CH_SOLAR` is registered and defaulted (`config.py:141-144`) but never produced outside tests, so the architecture diagram's fourth channel is present in configuration and absent in operation — a gap a reader must cross-check to notice.

### Decision 7: SQLite now, TimescaleDB behind the same interface later

**Why:** Zero external services fits the air-gap mission; two tables and two indices are enough for a single-site evidence trail; the read/write method surface is the stable contract. Deferring the time-series database until scale demands it avoids paying for Postgres operations on day one.

**Trade-off:** The store commits after every write with a single unlocked connection and no WAL or batching (`store.py:52,89`) — fine for the demo's serial replay, but the three-to-five concurrent collector channels the diagram implies would need a concurrency model that neither exists nor is documented as a constraint.

---

## 7. What This Pattern Teaches

### Lesson 1 — Scope a monitor by failure-mode independence, and the architecture writes itself

The strongest move in the whole project is upstream of any code: choosing the channels by asking "what fails independently of GPS and of each other?" That single question produces the heterogeneous channel list (network / oscillator / sky / survey), justifies why a *fixed-site* monitor rather than a general library is the right unit, and — because independence is the whole value — explains why "no fabricated data" has to be a hard invariant. When the scoping axis is right, the detector taxonomy, the extensibility seam, and the safety rules all fall out of it. The lesson is not "monitor GPS this way"; it is "find the axis along which your problem's parts are genuinely independent, and scope to that."

### Lesson 2 — A specification is only a contract when its scenarios carry numbers

Prose requirements ("detect slow walks", "compute the offset correctly") cannot fail a test, so they cannot bind the code. Atri Sangam's specs bind because they are decimal-exact — offset 5.0 s, delay 0.2 s; a 0.002 s/s walk that trips CUSUM but not a 0.5 s step — and the acceptance tests reproduce those numbers. Elevating numerical behavior to a SemVer-breaking part of the public contract completes the loop: the spec, the test, and the version number all agree on what the constants mean. The reusable idea is that the highest-leverage line in a spec is the one a test can copy verbatim.

### Lesson 3 — Injection is how a detector of non-determinism becomes deterministic itself

A monitor whose job is to notice when the world misbehaves has an awkward property: the world is exactly what you cannot put in a test. Constructor-injecting every socket, clock, and store dissolves the paradox — the SNTP four-timestamp calculation is verified with a fake socket and a fake clock, the simulator is seeded to byte-identity, the whole suite runs offline. The teaching generalizes past this project: the more a system's correctness depends on external, non-reproducible inputs, the more its testability depends on making every one of those inputs a parameter.

### Lesson 4 — Deferring a feature honestly means leaving a seam, not a stub

The solar channel is the model to copy. The predictor is built and tested; the channel is registered and defaulted; and the one missing piece — the `Sample`-producing wrapper that needs hardware — is simply *absent*, not faked with a placeholder feed. Contrast the failure mode the project's own "no fabricated data" rule warns against: a stub that returns a plausible value reads as a working feature and lies. A named roadmap entry plus a live extensibility seam (any `Sample` with a new channel name just works) is how you defer without deceiving. The absence is the honesty.

### Lesson 5 — Name the gap between "library" and "product" in one sentence, at the top

The most valuable thing an assessment of this codebase can do is state plainly that it is a well-tested library and red-team simulator, not a deployable monitor — that no runner, scheduler, or daemon exists, and the "live" dashboard replays a finished store. The code supports this framing everywhere (pure transformers awaiting a shell, `check_staleness` awaiting a caller, the demo loop standing in for the missing loop), but only a skim-proof sentence at the top prevents the README's present-tense diagram from overselling. The lesson for any pre-1.0 artifact: the single most useful line you can write is the one that says exactly which part of the product is not built yet — and the corollary is that a clean architecture is one where that missing part is a thin shell, not a rewrite. Here it is a thin shell, which is the real compliment.

---

*Analysis based on the source snapshot dated 2026-07-18 (no git history in the reviewed artifact). Grounded in a full read of `src/atri_sangam/**`, `tests/**`, `openspec/specs/**`, `README.md`, `openspec/project.md`, `.github/workflows/ci.yml`, and `pyproject.toml`. Consistent with the companion [atri-sangam-critique.md](atri-sangam-critique.md) (v1.0). Cost-of-time-and-money analysis is maintained privately.*
