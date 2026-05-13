# dronePrjs — Code Review & Critique

**Reviewed:** May 2026 (v1.0 — first review)
**Repo:** `dronePrjs` (local, `main`)
**Phase:** Early-build / pre-simulator. Phases 0–5 of an 8-phase roadmap complete; the in-process kinematic sim drives the test suite end-to-end. No higher-fidelity simulator (Gazebo/PX4 SITL) and no hardware yet.
**Scope:** Umbrella for two domain apps — `closedSpace` (indoor GPS-denied warehouse inventory) and `openSpace` (outdoor, stub only) — over a shared `engine/` Protocol layer.
**Rating key:** ✅ Strong · ⚠️ Gap / Risk · ❌ Critical Issue

---

## Executive Summary

dronePrjs is the engineering-discipline outlier in this critique set: ~5,010 LOC of Python across 52 files, **100 tests passing in 52 s, 97 % line coverage, `mypy --strict` clean across 29 source files, `ruff check` clean.** The repo is six commits old and every commit is a labelled phase delivery (Phase 0–5). Quality gates pass on a freshly-cloned `.venv` without manual intervention.

Architecturally the umbrella is well-shaped. `engine/` exposes four `Protocol`s (`PositionProvider` → `SLAMProvider` / `GPSProvider`, `FlightController`, `Camera`, `TelemetryBus`) and an in-process `engine.sim` package that satisfies them — closedSpace's mission runner is exercised end-to-end against the sim without any conditional `if SIM:` branches. Domain bleed is **actively prevented** by `engine/tests/test_no_domain_bleed.py`, an AST-based scan, and by `ISC-30` / `ISC-36` static probes against the `GPSProvider` symbol. The `closedSpace/ISA.md` is the system-of-record: a single 634-line document that fuses PRD, acceptance criteria (44 ISCs, 29 currently checked), test strategy, feature plan, decision log, changelog, and verification trail. This is unusual rigour for a project at six commits.

The risks are the inverse of the discipline. (1) **`openSpace/` has no Python code** — only a 19-line `CLAUDE.md`. The umbrella's "shared engine" claim is currently single-consumer; the engine Protocols have never been pulled on by a second domain, which is when over- or under-fitting becomes visible. (2) **`engine.sim` is the only thing the tests have ever flown.** Every `[x]` ISC is a sim claim. ISC-12 (SLAM-loss → SAFE_HOVER), ISC-13 (≤50 ms p99 perception→command), ISC-14 (0.5 m clearance), ISC-31 (zero `COLLISION` events), ISC-33 (no clearance violations), ISC-42 (untrained operator ≤15 min) are all unverifiable until Phase 3 (sim choice) and Phase 8 (pilot) land — six of the seven `[ ]` ISCs are in this category. (3) The `ISA.md` itself acknowledges **"thinking-floor doctrine deviation"** (2026-05-03 VERIFY entry): FirstPrinciples / RedTeam capabilities were not tool-invoked during scoping. This is flagged in the decision log rather than hidden, which is the right move, but the remediation ("spawn FirstPrinciples + RedTeam against this ISA before implementation begins") was never executed before Phases 1–5 shipped.

No P0/P1 issues. The pre-simulator window is the right time to address the open-decision queue (D1 sim-first/hardware-first, D2 simulator choice, D3 flight stack) before Phase 3 starts.

---

## Snapshot

| Metric | Value |
|---|---|
| Python source LOC | ~5,010 across 52 files |
| Test count | 100 (all passing in 52 s) |
| Coverage | 97 % (engine.sim 89 % is the only sub-90 module) |
| `mypy --strict` | clean across 29 source files |
| `ruff check` | clean |
| Commits on `main` | 6 (Phase 0 → Phase 5) |
| ISCs declared | 44 |
| ISCs marked complete | 29 (66 %) |
| Open decisions blocking Phase 3 | 3 (D1 sim mode, D2 simulator, D3 flight stack) |
| Domains with code | 1 of 2 (closedSpace; openSpace is `CLAUDE.md` only) |

---

## 1. Architecture

### Strengths

- ✅ **Two-domain umbrella with a single contract surface.** `engine/` holds nothing but cross-domain Protocols (`PositionProvider`, `FlightController`, `Camera`, `TelemetryBus`) plus reference sim impls. closedSpace consumes only the Protocols; the in-process `engine.sim` package is what tests bind to.
- ✅ **Anti-bleed is mechanically enforced.** `engine/tests/test_no_domain_bleed.py` AST-scans `engine/` for any import of `closedSpace` or `openSpace`. ISC-30 / ISC-36 probes assert the same property by grep. The rule that "domain-specific logic does not appear under `engine/`" is testable, not aspirational.
- ✅ **closedSpace/ISA.md is the system-of-record.** One file covers Problem / Vision / Out-of-Scope / Constraints / Goal / 44 ISCs / Test Strategy / Features / Decisions / Changelog / Verification. The Decision log is dated and links specific code/fixture choices to specific reasons — the rack-fixture geometry bug caught on first integration is recorded with the conjecture/refutation/learning trio.
- ✅ **Pure mission planner.** `closedSpace.mission.plan` is a pure function — no IO, no randomness, no time-of-day inputs. The §10.2.2 vs §10.2.3.2 conflict in the path-derivation spec is resolved in-code with the resolution documented in the module docstring.
- ✅ **Frozen dataclasses with slots throughout.** `Pose`, `Map`, `Aisle`, `Rack`, `Level`, `Waypoint`, `MissionPlan`, `PreflightCheck`, `PreflightResult`, `MissionRunResult`, `StoredArtifact` — all immutable. Mutation lives in the explicit stateful classes (`SimWorld`, `MissionRunner`, `CaptureSink`, `ReportBuilder`).
- ✅ **Atomic local-first storage.** `closedSpace/storage/local.py` writes to `.partial`, fsyncs, then `os.replace()`. Sync failures leave a `.sync-pending` marker and never delete the local copy (ISC-22 / ISC-32).
- ✅ **Operator concerns are decoupled.** `PreflightChecklist` takes `battery_pct` / `calibration_ok` as callables, not imports — tests inject fixed values, real hardware injects live sensor reads.

### Gaps & Risks

- ⚠️ **openSpace is a stub.** `openSpace/CLAUDE.md` exists; no Python, no tests. The engine's "shared contract" claim is single-consumer until openSpace exercises `GPSProvider` and at least one other engine Protocol. Until then, today's Protocols are inferred from one use case, not two — likely over-fit toward closedSpace's SLAM/indoor assumptions.
- ⚠️ **`engine/sim` is the only thing the tests have ever flown.** The kinematic sim snaps to waypoints instantly (`SimFlightController.goto` has no integration). Every `[x]` ISC is a sim-validated claim. ISC-12/13/14/31/33 cannot be probed against this sim by construction — they need a fidelity tier the roadmap defers to Phase 3.
- ⚠️ **No openSpace `GPSProvider` reference impl.** `engine.localization.GPSProvider` is a Protocol; no concrete sim/stub implementation exists. The first openSpace test will need to invent this, and the Protocol shape may shift when it does.
- ⚠️ **Inter-aisle transit is in `mission/transit.py` but only verifies segments don't cross no-go zones (ISC-10).** There is no rerouter — a blocked plan raises `TransitBlockedError` and refuses to fly. Documented as v1 scope, but the operator UX of "the planner can't help, fix your map" is harsh.
- ⚠️ **`closedSpace/run.py` exists but isn't reviewed in this pass.** It's the CLI entry point that the operator README points to (`python -m closedSpace.run --map <map.yaml>`). The runner code under `operator/runner.py` is well-tested; the CLI surface that wires it to `argparse` + stdin abort thread should be re-checked for the I/O edges (Ctrl-C handling, broken pipe to ground-station log).

---

## 2. Code Quality

### Strengths

- ✅ **`mypy --strict` clean across all 29 source files.** Tests are deliberately excluded (`exclude = ["tests/"]`) — documented in `pyproject.toml` as a deliberate trade-off ("test code uses dynamic fixtures and patching patterns that don't repay strict typing").
- ✅ **`ruff check .` clean** with `line-length = 100`, `target-version = "py310"`.
- ✅ **OpenSpec docstrings on every public surface.** Each module opens with a what/why prose paragraph; each public class names its lifecycle, threading model, and the ISC(s) it satisfies. `closedSpace/operator/runner.py:1-16` is representative.
- ✅ **Domain-specific exceptions.** `MapValidationError`, `UnsupportedMapVersionError`, `TransitBlockedError`, `StorageError`, `SyncFailure`, `ReportValidationError`. The CLAUDE.md rule "raise domain-specific errors, don't swallow exceptions" is held.
- ✅ **Enums where it matters.** `PreflightOutcome` (PASS/FAIL/WARN), `MissReason` (LOW_RESOLUTION/LOW_FOCUS/STORAGE_ERROR), `ControllerState` (DISARMED/ARMED/AIRBORNE). Schema/report enums have explicit string values so downstream tooling can switch on them.
- ✅ **Zero `TODO`/`FIXME`/`XXX` in source.** Verified by inspection across all 52 files.
- ✅ **Constants live in `closedSpace/constants.py`.** `MIN_CLEARANCE_M`, `DRONE_ENVELOPE_M`, `SUPPORTED_MAP_VERSIONS` etc. — not scattered through call sites.

### Gaps & Risks

- ⚠️ **`AbortSignal` uses `threading.Event` but the runner is single-threaded.** The CLI installs a stdin reader thread to flip the flag; the runner polls `is_set()` between waypoints. This is fine for the sim's instant `goto`, but with real hardware the runner will sit inside `fc.goto()` for many seconds — the per-waypoint poll is the only abort granularity, which the ISA already flags as Phase 8 work.
- ⚠️ **`SimFlightController._transition` raises `RuntimeError` for illegal state requests.** `RuntimeError` is the right shape but the right name is a domain error like `IllegalFlightStateTransition`; preserves the closed-vocabulary discipline the rest of the codebase has.
- ⚠️ **`_atomic_write_bytes` doesn't fsync the parent directory.** `os.replace()` is atomic, but on power-loss between the rename and a parent-directory `fsync()`, the filename swap can be lost on some filesystems. Low priority for a sim-only path; high priority before pilot.

---

## 3. Test Coverage

### Strengths

- ✅ **100 tests, 100 passing, 52 s wall time.** Test pyramid is right-shaped: 22 map-loader/validator tests; 6 mission-plan tests; 5 mission/sim-integration tests; 23 operator tests (CLI + runner + preflight); 7 report tests; 7 storage tests; 13 engine.sim tests; 2 end-to-end pipeline tests.
- ✅ **97 % line coverage** (1,955 stmts, 55 missed). `engine/sim` at 89 % is the only sub-90 module; uncovered lines are illegal-state guards.
- ✅ **Static-analysis tests for cross-cutting invariants.** `test_no_domain_bleed.py` uses Python's `ast` module to scan `engine/` for forbidden imports — codifies a discipline rule into CI.
- ✅ **Fixture-driven map tests.** `reference_warehouse.yaml` is committed; tests round-trip it through `dump → load → semantic-equal` (ISC-5). The fixture itself caught a geometry bug on first integration, recorded in `ISA.md` Changelog 2026-05-03.
- ✅ **End-to-end pipeline test** (`closedSpace/tests/test_mission_e2e.py`) flies a full reference mission through the sim and validates the report against `schemas/mission_report.schema.json`.
- ✅ **Co-located test layout** mirrors source — `closedSpace/map/loader.py` → `closedSpace/tests/map/test_loader.py`. Compliance with the CLAUDE.md rule is uniform across the codebase.

### Gaps & Risks

- ⚠️ **All fidelity claims are sim-claims.** The 100 passing tests prove the wiring is right; they don't and can't prove the drone clears 0.5 m, holds <50 ms perception→command, or recovers from SLAM loss. The ISA marks the relevant ISCs `[ ]` honestly — the risk is that progress velocity makes them feel further along than they are.
- ⚠️ **No performance / soak tests.** ISC-13 (p99 < 50 ms over 2-min soak) has no harness. The hot loop doesn't exist yet, so this is correctly deferred — but the harness should land in Phase 3 alongside whichever simulator is chosen, not in Phase 8.
- ⚠️ **No CI configuration committed.** `Makefile` provides `make all` (lint + typecheck + test); no `.github/workflows/` or equivalent. The quality bar is high; the enforcement bar isn't set up yet. Phase 6 of `next-steps.md` lists this as `partial`.
- ⚠️ **No fuzz / property tests on the map validator.** `closedSpace/map/validate.py` is the firewall between operator YAML and the planner; the suite tests known-bad cases by name. Hypothesis-style property tests against the JSON Schema would broaden coverage cheaply.

---

## 4. Documentation

### Strengths

- ✅ **ISA-as-system-of-record is genuinely working.** 634 lines covering Problem → Verification, every Feature linked to ISCs, every ISC linked to a test type, every Decision dated and reasoned. New engineer onboarding cost is bounded by reading one file plus `docs/use-cases.md`.
- ✅ **Three-tier CLAUDE.md** — umbrella + closedSpace + openSpace — with non-overlapping scope. Umbrella holds universals (Python, pytest, docstrings, exception discipline); subproject files hold domain rules (closedSpace forbids GPS, openSpace forbids assuming GPS-denied).
- ✅ **`docs/map-schema.md`, `docs/use-cases.md`, `docs/next-steps.md`, `docs/drones.md`, `docs/operator-README.md`.** Six in-tree docs for closedSpace, each with a stated audience and a status legend (DONE / partial / Sketched).
- ✅ **JSON Schemas committed and tested.** `schemas/map.schema.json` validates inputs; `schemas/mission_report.schema.json` validates outputs; both are loaded by the source they govern.

### Gaps & Risks

- ⚠️ **openSpace has only a CLAUDE.md.** No ISA, no use cases, no map schema. Whatever the outdoor product is, it's currently a tagline, not a contract. The umbrella's design tension between indoor and outdoor cannot be resolved without it.
- ⚠️ **ISA's "Verification" section logs *which ISCs were probed by what*, not *what the probe returned*.** "smoke runner — `load(reference_warehouse.yaml)` returned `Map(...)`" is good; a CI artifact link or commit-hash for each verification would be better as the project grows.
- ⚠️ **No top-level `README.md` at the umbrella.** The umbrella's `CLAUDE.md` works for agents; a human visitor hits `pyproject.toml` first and has to puzzle out the project from package metadata.

---

## 5. Security & Safety

### Strengths

- ✅ **Map provenance is first-class (ISC-43 / ISC-44).** `surveyed_at` and `surveyed_by` carry through load; `PreflightChecklist._check_map_staleness` refuses stale maps past `MAX_MAP_AGE_DAYS` (default 30) unless `--allow-stale-map` is set AND the map has non-null provenance. Null provenance is a non-blocking warning, not a silent pass.
- ✅ **Pre-arm gate is genuinely gating.** `PreflightResult.can_arm` requires zero failures across battery, calibration, takeoff-in-coverage, free-takeoff-pad, and map-staleness. The runner reads this; nothing in the test suite arms past a FAIL.
- ✅ **Coverage-polygon containment refuses takeoff outside the map** (ISC-34). The check is in `_check_takeoff_in_coverage` and uses the same point-in-polygon routine as map validation.
- ✅ **Sync never deletes local data on upload failure** (ISC-22 / ISC-32). Failure writes a `.sync-pending` marker; the next sync re-uploads.
- ✅ **GPS forbidden in closedSpace by static probe** (ISC-30). Two anti-tests check this — one grep-based at the doc layer, one AST-based in `engine/tests/test_no_domain_bleed.py`.

### Gaps & Risks

- ⚠️ **No mission-level kill-switch tested.** The abort path is per-waypoint; long inter-waypoint dwells on real hardware are unaddressed (ISA flags this for Phase 8). Until then, an operator pressing abort during a 5-second `goto` waits 5 seconds.
- ⚠️ **No signing of the map file.** The pre-flight checklist trusts whatever YAML it's given. ISC-28 mentions "map signature" as a checklist item; the implementation in `preflight.py` doesn't include a signature check (the test for ISC-28 covers battery, calibration, coverage, free pad, staleness — not signature).
- ⚠️ **`run.py` is unreviewed in this pass.** The link-loss return-to-home behaviour (ISC-15) and `LINK_LOSS_TIMEOUT_S` are not yet implemented anywhere visible in the tree — currently `[ ]` in the ISA.

---

## 6. Scalability & Operations

### Strengths

- ✅ **Two-tier simulator strategy is the right call** (ISA Decision 2026-05-03 PLAN/iter-6, D2 recommendation). The in-process kinematic sim is what's shipped; Gazebo / PX4 SITL slot in later behind the same Protocols.
- ✅ **`MapBuilderFromWMS` is sketched, not implemented** (ISA Features block). The right level of detail: adapter strategy named (SAP EWM, Manhattan, Fishbowl), module layout proposed, public signature drafted, scope set ("v1 deployment path, not v1 flight path"). No premature code.
- ✅ **Engine `flight_control` Protocol abstracts the flight stack.** D3 ("PX4 vs ArduPilot vs SDK") is correctly deferred — Phase 3 doesn't need to answer it.

### Gaps & Risks

- ⚠️ **Single-drone, single-mission, single-aisle-set per run** (out-of-scope by design). The data model doesn't anticipate multi-drone choreography. Adding it later won't be a small change; surfacing the boundary now in the umbrella docs would prevent it from being assumed-away in Phase 7 (WMS builder) or Phase 8 (pilot).
- ⚠️ **No backpressure / retention strategy on local capture storage.** A long mission with focus-rejected captures fills the disk; there's no `.partial` cleanup sweeper, no retention policy on `.sync-pending` markers. Pilot deployment will need one.

---

## Priority Actions (Top 5)

| # | Action | Why | Where |
|---|---|---|---|
| 1 | **Answer D1 / D2 / D3 before Phase 3 work begins** | Three decisions gate the next 5–10 days of engineering; ISA flags them as `## Decisions` material, not roadmap notes | `closedSpace/ISA.md` `## Decisions` |
| 2 | **Write `openSpace/ISA.md` (or equivalent) and a `GPSProvider` reference sim** | The umbrella's "shared engine" claim is unverified until two domains pull on it; engine Protocols may over-fit until then | `openSpace/` |
| 3 | **Add `.github/workflows/ci.yml` (or equivalent) running `make all` on push** | Quality bar is set; enforcement bar isn't — Phase 6 is `partial` per `next-steps.md` | repo root |
| 4 | **Implement the `RedTeam` + `FirstPrinciples` review the ISA's VERIFY entry commits to** | The decision log records a doctrine deviation that was never closed; the cheap remediation is to run the review before Phase 3 — not after pilot | `closedSpace/ISA.md` `## Decisions` |
| 5 | **Add a perception→command latency soak harness when the Phase-3 simulator lands** | ISC-13 is the load-bearing real-time claim and currently has no harness; building it alongside the simulator (not after pilot) is the cheaper sequencing | new module under `closedSpace/tests/control/` |

---

*Review based on commit `5c45c9e` on `main`. Quality probes: `make all` (lint + typecheck + test) passes locally; coverage 97 %; 100 tests pass in 52 s.*
