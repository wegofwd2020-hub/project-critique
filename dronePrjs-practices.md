# dronePrjs — Good Practices, Bad Practices & How to Improve

**Document type:** Engineering practices analysis
**Scope:** Python 3.10+ (closedSpace + engine), shared umbrella, openSpace (stub)
**Period:** 2026-05-24 (v1.1 — alignment with critique v1.1: Phase 6 CI now real, ISC-28 map-signature check now real, D1/D2 ratified in ISA)
**Prior:** v1.0 May 2026 (first review at commit `5c45c9e`, 6 commits, Phase 0–5)
**Related:** [dronePrjs-critique.md](dronePrjs-critique.md) · [dronePrjs-development-pattern.md](dronePrjs-development-pattern.md) · [dronePrjs-cost.md](dronePrjs-cost.md)
**Rating key:** ✅ Good practice · ⚠️ Bad practice · ❌ Critical issue · 🔧 How to improve

> **Note (2026-05-24):** the body below is the v1.0 record, preserved. The v1.1 cycle (HEAD `5e38a44`, 6 → 8 commits) closed three of v1.0's flagged practice gaps and validated the documented good practices held across two more phase deliveries. Updates to the catalogue:
>
> - **✅ Now real (was missing) — CI quality-gate.** `.github/workflows/ci.yml` — single `quality-gate` job (Python 3.12, `pip install -e ".[dev]"`, `make all`, coverage ≥80%). **Closes the v1.0 "no CI" finding** (ISCs 37–41 + 44 done).
> - **✅ Now real (was declared-not-implemented) — map-signature check in pre-arm.** `closedSpace/operator/preflight.py` runs the map-signature check in the pre-arm checklist (ISA line 212). **Closes ISC-28 and the v1.0 example of the declared-not-implemented anti-pattern.**
> - **✅ Now real (was unratified) — D1 + D2 ratified in ISA DECIDE entries (2026-05-13).** D1 = sim-leads / hardware-follows; D2 = two-tier sim (in-process kinematic + Gazebo/PX4-SITL). **The decision-as-doc pattern (ISA carries the decision-record next to the criteria they constrain) demonstrated to work end-to-end.**
> - **✅ New good practice — fidelity tiers with their own quality-gate windows.** Phase 3 partial scaffolded `engine/sim_gazebo/` (Docker: PX4 v1.15.4 + Gazebo Harmonic + Ubuntu 22.04, host-networked for MAVLink) but the heavy build is **deliberately kept out of `make all`** (NS-3.1b is a manual task). Practice: cheap tier runs every commit, expensive tier runs on demand. Reusable for future fidelity tiers (HITL, real hardware).
> - **✅ Carried forward — phase-per-commit cadence.** 8 commits, every one a labelled phase delivery. Pattern scales.
> - **✅ Carried forward — `mypy --strict` + `ruff` clean, frozen dataclasses with slots, zero TODO/FIXME.** All hold across the new code.
> - **⚠️ Still open — ISC-15 (link-loss RTH).** No movement since v1.0. A real safety-critical drone-autonomy team would not have shipped Phase 6 without RTH — regulatory expectation for autonomous BVLOS operations.
> - **⚠️ Still open — openSpace as a stub.** `openSpace/CLAUDE.md` only; no `ISA.md`, no source, no `GPSProvider` / `SimGPS` reference impl. The engine Protocol contract is single-consumer (closedSpace only) until this changes. **Priority #1 in the v1.1 critique.**
> - **🔧 New practice for D3 (flight stack) ratification.** Apply the D1/D2 mechanism (ISA DECIDE entry with criteria + alternatives + decision + reversal-cost) before Phase 8 starts. Don't let D3 deferral pile up into the hardware-procurement window.
>
> Re-measured: 114 test functions / ~133 collected (was 100), coverage 95.3% (was 97%), source LOC corrected to 3,548 (v1.0 over-counted at ~5,010 by including tests), 35 of 44 ISCs complete (was 29/44). All 8 commits landed on 2026-05-13 within ~1h 45m. See [dronePrjs-cost.md](dronePrjs-cost.md) for the real-world cost-of-time-and-money analysis of the practices catalogued below.

---

## Table of Contents

1. [Architecture Practices](#1-architecture-practices)
2. [Safety Practices](#2-safety-practices)
3. [Code Quality Practices](#3-code-quality-practices)
4. [Testing Practices](#4-testing-practices)
5. [Documentation Practices](#5-documentation-practices)
6. [Domain Isolation Practices](#6-domain-isolation-practices)
7. [Roadmap & Decision Practices](#7-roadmap--decision-practices)
8. [Summary Scorecard](#8-summary-scorecard)

---

## 1. Architecture Practices

### ✅ Good — Engine As Pure Contract Surface

The `engine/` package holds only types, Protocols, and a reference sim. No domain knowledge, no warehouse concepts, no map-shape assumptions. The boundary is enforced by `engine/tests/test_no_domain_bleed.py`, which AST-scans every module under `engine/` and fails if any import resolves to a top-level package starting with `closedSpace` or `openSpace`.

```
engine/                          ← contract surface
├── types.py                     ← Pose (frozen, slots)
├── localization/__init__.py     ← PositionProvider / SLAMProvider / GPSProvider
├── flight_control/__init__.py   ← FlightController + ControllerState
├── sensors/__init__.py          ← Camera + Frame + focus_score
├── telemetry/__init__.py        ← TelemetryBus + JSONL logger
├── sim/__init__.py              ← in-process reference impl
└── tests/test_no_domain_bleed.py← enforces the no-bleed rule
```

The result: a future hardware adapter or Gazebo bridge slots in behind the same Protocols. No `if SIM:` branches, no `RealAdapter` vs `SimAdapter` indirection.

---

### ✅ Good — Layers Depend Downward Only

```
Operator (CLI, runner, preflight)
        │
        ▼
Domain  (closedSpace: map, mission, capture, storage, report)
        │
        ▼
Engine  (types + Protocols + sim)
```

`engine/` has zero imports from `closedSpace/` or `openSpace/`. `closedSpace/operator/` has zero imports from anywhere else's operator code. A new contributor can read top-down and never need to chase upward references.

---

### ✅ Good — Frozen Dataclasses With Slots Throughout

Every data type that crosses a boundary is `@dataclass(frozen=True, slots=True)`:

```
engine.types.Pose
closedSpace.map.types.{Map, Aisle, Rack, Level, NoGoZone, Centerline, Point2D, Point3D, TakeoffPad}
closedSpace.mission.types.{MissionConfig, MissionPlan, Waypoint}
closedSpace.operator.preflight.{PreflightCheck, PreflightResult}
closedSpace.operator.runner.MissionRunResult
closedSpace.storage.local.StoredArtifact
closedSpace.storage.sync.SyncResult
closedSpace.capture.sink.{CaptureRecorded, CaptureMissed}
```

State is concentrated in the few classes that own a lifecycle (`SimWorld`, `MissionRunner`, `CaptureSink`, `ReportBuilder`, `LocalSink`). Everything else is value-typed and immutable. The result: equality is structural, hashing is free, accidental mutation is impossible.

---

### ⚠️ Bad — openSpace Is A Stub; Engine Contract Is Single-Consumer

`openSpace/` contains exactly one file — a 19-line CLAUDE.md. No `ISA.md`, no `GPSProvider` reference impl, no tests. The engine's "shared contract" claim is currently unverified: today's `PositionProvider` / `FlightController` / `Camera` / `TelemetryBus` Protocols are shaped by closedSpace alone.

When openSpace pulls on the engine:

- `GPSProvider.confidence()` may want to expose GPS-specific signals (HDOP, satellite count) that the closedSpace-shaped `confidence()` doesn't accommodate.
- `FlightController.takeoff()` may need a max-altitude parameter that closedSpace ignores.
- `Camera` may want exposure / shutter controls that the SLAM camera doesn't expose.

#### 🔧 How to improve

Write `openSpace/ISA.md` even before any flight code — even a 100-line first cut that names the use case, the constraints (GPS, geofence, wind class, FAA airspace), the Out-of-Scope list, and 5–10 ISCs. Then write a `SimGPS` reference impl under `engine/sim/` so the engine has its second consumer and any Protocol over-fit becomes immediately visible.

---

### ✅ Good — Pure Mission Planner

`closedSpace/mission/plan.py` is a pure function: same map + same `MissionConfig` produces byte-identical waypoint sequences. No IO, no randomness, no clock reads. The §10.2.2 vs §10.2.3.2 path-derivation conflict is documented in the module docstring with the chosen resolution.

```
plan(m: Map, config: MissionConfig | None = None) -> MissionPlan
```

Testable without standing up a sim. Mockable trivially. Determinism is a property the test suite can assert (and does — `test_plan.py`).

---

### ✅ Good — Local-First Atomic Storage

`closedSpace/storage/local.py` writes captures with the partial-file rename pattern: write to `.partial`, fsync, `os.replace()`. Sync to remote (`closedSpace/storage/sync.py`) is post-flight, idempotent, and never deletes the local copy on failure — it writes a `.sync-pending` marker.

```
write(relative_path, image_bytes, sidecar)
  ├─ image_path.parent.mkdir(parents=True, exist_ok=True)
  ├─ tmp = image_path.with_suffix('.jpg.partial')
  ├─ tmp.open('wb') → f.write(data) → f.flush() → os.fsync(f.fileno())
  └─ os.replace(tmp, image_path)
```

ISC-21 (local-first before next waypoint), ISC-22 (sync failure preserves local), ISC-32 (`.sync-pending` marker) — all three are codified, all three have tests.

---

### ⚠️ Bad — No Parent-Directory `fsync()` After Atomic Rename

`os.replace()` is atomic, but on some filesystems a power-loss between the rename and the parent-directory `fsync()` can lose the rename. The current implementation fsyncs the file but not the directory.

#### 🔧 How to improve

```python
# closedSpace/storage/local.py — _atomic_write_bytes
def _atomic_write_bytes(target: Path, data: bytes) -> None:
    tmp = target.with_suffix(target.suffix + ".partial")
    with tmp.open("wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, target)
    # NEW: durability of the rename itself
    dir_fd = os.open(str(target.parent), os.O_DIRECTORY)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)
```

Low priority while sim is the only flyer; high priority before pilot. Add a test that uses `os.O_DIRECTORY` + `os.fsync` to confirm the call shape doesn't regress.

---

## 2. Safety Practices

### ✅ Good — GPS Forbidden In closedSpace By Static Probe

Two anti-tests enforce the rule:

```
ISC-30 probe   :  grep -r "GPSProvider" closedSpace/   → 0 matches
ISC-36 probe   :  engine/tests/test_no_domain_bleed.py → AST scan
```

The Protocol exists in `engine.localization` because `openSpace` will need it. The probe catches the case where someone accidentally imports the wrong provider into closedSpace. Convention is rule; rule is test; test runs in `make all`.

---

### ✅ Good — Pre-Arm Gate Genuinely Gates

`PreflightChecklist.run(map)` runs five checks and returns a `PreflightResult` whose `can_arm` property is `False` if any check returns `FAIL`:

```
1. battery_pct ≥ MIN_BATTERY_PCT (default 30 %)
2. calibration self-test OK
3. takeoff pad inside coverage polygon (ISC-34)
4. no no-go zone inside / near takeoff pad
5. map.surveyed_at ≤ MAX_MAP_AGE_DAYS old (ISC-44)
```

`MissionRunner` reads `can_arm`; nothing in the test suite arms past a `FAIL`. The `WARN` outcome surfaces issues to the operator without blocking — used today only by map staleness when `surveyed_at` is null.

---

### ✅ Good — Map Provenance & Staleness Are First-Class (ISC-43 / ISC-44)

`Map.surveyed_at` and `Map.surveyed_by` are optional fields on the loaded map. The preflight gate:

| Scenario | Outcome |
|---|---|
| `surveyed_at` is null | `WARN` — non-blocking, surface to operator |
| `surveyed_at` ≤ 30 days old | `PASS` |
| `surveyed_at` > 30 days old, no override | `FAIL` — refuse arm |
| `surveyed_at` > 30 days old, `--allow-stale-map` set, `surveyed_at` non-null | `WARN` |
| `surveyed_at` > 30 days old, `--allow-stale-map` set, `surveyed_at` null | the null-warning branch still fires |

Override is honoured *only* when the operator has both opted in (`--allow-stale-map`) AND the map carries provenance. Null + override is not a silent pass.

---

### ⚠️ Bad — Map-Signature Check Is Listed In ISC-28 But Not Implemented

ISC-28 says: *"Pre-flight checklist (battery, calibration, **map signature**, free-space check) is run automatically and reported pass/fail per item before arm."* `PreflightChecklist.run` runs five checks and none of them is a signature verification. A tampered or wrong map (e.g., a map for a different warehouse with the same takeoff pad position) would pass all five checks.

#### 🔧 How to improve

Add a sixth check:

```python
def _check_map_signature(self, m: Map) -> PreflightCheck:
    if self._expected_map_signature is None:
        # No signature expected — non-blocking
        return PreflightCheck(
            name="map_signature",
            outcome=PreflightOutcome.WARN,
            detail="no expected signature provided — operator must confirm map identity",
        )
    actual = compute_map_signature(m)  # canonical hash over normalized fields
    if actual == self._expected_map_signature:
        return PreflightCheck(name="map_signature", outcome=PreflightOutcome.PASS, ...)
    return PreflightCheck(
        name="map_signature",
        outcome=PreflightOutcome.FAIL,
        detail=f"map signature mismatch: expected {self._expected_map_signature}, got {actual}",
    )
```

The signature itself is a SHA-256 over the canonical serialization of the loaded `Map` (sorted keys, normalized floats). The operator console pulls the expected signature from a per-warehouse manifest at the same time the map is downloaded — out-of-band from the map file itself.

---

### ⚠️ Bad — Abort Granularity Is Per-Waypoint Only

`MissionRunner` polls `abort_signal.is_set()` between waypoints. With the in-process sim, `goto()` returns instantly — the poll is effectively continuous. With real hardware, `goto()` can sit for many seconds while the drone transits and dwells; an operator pressing abort will wait until the current waypoint completes.

The ISA flags this explicitly: *"For real hardware with long inter-waypoint dwells, Phase 8 will need to poll inside the dwell too."* The risk is that "Phase 8" arrives at pilot site with the long-dwell case unhandled.

#### 🔧 How to improve

Pre-pilot, add an abort-polling hook into the `FlightController` Protocol:

```python
class FlightController(Protocol):
    def goto(
        self, x: float, y: float, z: float, yaw_deg: float,
        *, abort: Callable[[], bool] | None = None,
    ) -> None: ...
```

The runner passes `abort=lambda: self._abort.is_set()`; implementations check periodically (say, every 100 ms) and raise `AbortRequested` if set. The sim implementation can ignore the hook; the hardware adapter must honour it.

---

### ⚠️ Bad — Link-Loss Return-To-Home Not Implemented (ISC-15 Open)

ISC-15 (*"Ground-station link loss > LINK_LOSS_TIMEOUT_S triggers return-to-home + land sequence"*) is `[ ]`. The runner does not own a heartbeat. No `LINK_LOSS_TIMEOUT_S` constant exists.

#### 🔧 How to improve

Add a heartbeat channel to `TelemetryBus`. Operator console publishes `link.alive` once per second; runner subscribes and tracks the last-seen timestamp. A monotonic-clock-driven `MissionWatchdog` raises `LinkLost` after the timeout, and the runner's catch block triggers RTH + land (same path as abort with reason=`link_loss`).

Wire the test against a degraded `SimTelemetryBus` that stops publishing after N seconds and confirm the state-machine transitions through `RTH` to `LANDING` to `DISARMED`.

---

## 3. Code Quality Practices

### ✅ Good — `mypy --strict` Clean Across All 29 Source Files

`pyproject.toml`:

```
[tool.mypy]
python_version = "3.10"
strict = true
files = ["closedSpace", "engine", "openSpace"]
exclude = ["tests/"]
```

`mypy strict` enables `--disallow-untyped-defs`, `--no-implicit-optional`, `--warn-redundant-casts`, `--warn-unused-ignores`, etc. The codebase passes without `# type: ignore` anywhere. The exclusion of tests is documented as a deliberate trade-off ("test code uses dynamic fixtures and patching patterns that don't repay strict typing").

---

### ✅ Good — `ruff check .` Clean

`ruff` with `line-length = 100`, `target-version = "py310"`. No noqa comments. Default rule set, no opinionated rules disabled.

---

### ✅ Good — Domain-Specific Exceptions, No Bare `Exception` Catches

Domain errors are named:

```
closedSpace.map.{MapValidationError, UnsupportedMapVersionError}
closedSpace.mission.TransitBlockedError
closedSpace.storage.{StorageError, SyncFailure}
closedSpace.report.ReportValidationError
```

Catches are narrow. `closedSpace/capture/sink.py` catches `StorageError` specifically and converts to `CaptureMissed(reason=STORAGE_ERROR)`; `closedSpace/storage/sync.py` catches `SyncFailure` specifically and writes a marker. No `except Exception:`.

The umbrella CLAUDE.md rule — *"Every function must include explicit exception handling. Don't swallow exceptions; raise domain-specific errors."* — is held.

---

### ✅ Good — Closed-Vocabulary Enums Where It Matters

```
PreflightOutcome  = {PASS, FAIL, WARN}
MissReason        = {LOW_RESOLUTION, LOW_FOCUS, STORAGE_ERROR}
ControllerState   = {DISARMED, ARMED, AIRBORNE}
Waypoint.kind     = Literal["takeoff", "landing", "transit", "capture"]
```

Schema/report enums have explicit string values (`"low_resolution"`, `"low_focus"`, etc.) so downstream tooling can switch on them without reflection.

---

### ✅ Good — Zero `TODO` / `FIXME` / `XXX` In Source

Verified by inspection across all 52 Python files. Open items live in the ISA's `## Criteria` (as `[ ]`) and `## Decisions` block, not as inline comments.

---

### ⚠️ Bad — `SimFlightController._transition` Raises `RuntimeError` Instead Of A Domain Error

```python
# engine/sim/__init__.py
def disarm(self) -> None:
    if self._state is ControllerState.AIRBORNE:
        raise RuntimeError("cannot disarm while AIRBORNE — land first")
```

`RuntimeError` is the right shape (it's a programmer error to call `disarm()` while airborne, not a recoverable runtime condition) but the wrong name. Every other module uses domain-specific exceptions.

#### 🔧 How to improve

```python
# engine/flight_control/__init__.py
class IllegalFlightStateTransition(RuntimeError):
    """Raised when a flight-control method is called from an incompatible state."""

# engine/sim/__init__.py
from engine.flight_control import IllegalFlightStateTransition

def disarm(self) -> None:
    if self._state is ControllerState.AIRBORNE:
        raise IllegalFlightStateTransition("cannot disarm while AIRBORNE — land first")
```

`IllegalFlightStateTransition(RuntimeError)` preserves the "this is a programmer error" semantics while joining the closed-vocabulary discipline.

---

### ⚠️ Bad — Constants Layer Has Some Drift

`closedSpace/constants.py` holds `MIN_CLEARANCE_M`, `DRONE_ENVELOPE_M`, `SUPPORTED_MAP_VERSIONS`. But `closedSpace/operator/preflight.py` holds `DEFAULT_MAX_MAP_AGE_DAYS = 30` and `DEFAULT_MIN_BATTERY_PCT = 30.0` as module-level constants, not in `constants.py`. Two patterns coexist.

#### 🔧 How to improve

Promote the preflight defaults to `closedSpace/constants.py`:

```python
# closedSpace/constants.py
DEFAULT_MAX_MAP_AGE_DAYS: int = 30
DEFAULT_MIN_BATTERY_PCT: float = 30.0
DEFAULT_LINK_LOSS_TIMEOUT_S: float = 5.0  # add when ISC-15 lands
```

One file, one place to audit when defaults change.

---

## 4. Testing Practices

### ✅ Good — 100 Tests, 100 Passing, 52 s, 97 % Coverage

| Metric | Value |
|---|---|
| Test count | 100 |
| Pass rate | 100 % |
| Wall time | 52 s |
| Line coverage | 97 % (1,955 stmts, 55 missed) |
| Coverage of `engine/sim` | 89 % (only sub-90 module) |
| Test files | 15 |
| Mock libraries | 0 (no `unittest.mock`, no `pytest-mock`) |

The test pyramid is right-shaped: 73 unit tests under `closedSpace/tests/{map,mission,capture,storage,report,operator}/`; 13 engine.sim tests; 2 end-to-end pipeline tests; 1 static-analysis test for engine bleed.

---

### ✅ Good — Co-Located Tests Mirroring Source Paths

```
closedSpace/map/loader.py          →  closedSpace/tests/map/test_loader.py
closedSpace/map/validate.py        →  closedSpace/tests/map/test_validate.py
closedSpace/mission/plan.py        →  closedSpace/tests/mission/test_plan.py
closedSpace/capture/sink.py        →  closedSpace/tests/capture/test_sink.py
closedSpace/storage/local.py       →  closedSpace/tests/storage/test_local.py
closedSpace/storage/sync.py        →  closedSpace/tests/storage/test_sync.py
closedSpace/report/builder.py      →  closedSpace/tests/report/test_builder.py
closedSpace/operator/preflight.py  →  closedSpace/tests/operator/test_preflight.py
closedSpace/operator/runner.py     →  closedSpace/tests/operator/test_runner.py
closedSpace/operator/cli.py        →  closedSpace/tests/operator/test_cli.py
```

Uniform across all 14 source modules. The umbrella CLAUDE.md rule — *"Tests live next to source in tests/, mirroring src/ layout"* — is held.

---

### ✅ Good — Static-Analysis Tests Codify Cross-Cutting Invariants

```
engine/tests/test_no_domain_bleed.py
  → AST-scans every module under engine/
  → fails if any import resolves to closedSpace or openSpace
```

This is a discipline rule made executable. ISC-30 (no GPS in closedSpace) gets a similar grep-based probe. The pattern — *if the rule matters, encode it as a test that runs every commit* — generalizes; the codebase uses it in two places.

---

### ✅ Good — End-To-End Mission Test Against The Sim

`closedSpace/tests/test_mission_e2e.py` flies the full reference fixture through the in-process sim and validates:

- The mission completes without abort.
- The waypoint count matches the planned count.
- The report passes `mission_report.schema.json`.
- The sidecar records the captured pose accurately (`test_sidecar_records_the_captured_pose`).

This is the integration test that catches "the runner advanced past the sink without the sink confirming" or "the report's `image_uri` doesn't match the actual file on disk" — bugs that no unit test would surface.

---

### ⚠️ Bad — All Fidelity Claims Are Sim-Claims

Every `[x]` ISC is a claim against the in-process kinematic sim. ISCs 12 (SLAM-loss → SAFE_HOVER), 13 (p99 < 50 ms perception→command), 14 (0.5 m clearance), 31 (zero COLLISION events), 33 (no clearance violations), 42 (untrained operator ≤15 min) are six of the seven remaining open ISCs — and they cannot be probed against this sim by construction.

The risk is that the 100-passing-tests velocity reads as "this is nearly done" when in fact the load-bearing physics ISCs sit untouched.

#### 🔧 How to improve

Two things to do in parallel with Phase 3:

1. **Build the latency soak harness now**, against the in-process sim, with a synthetic load (a tight `for _ in range(N): cam.capture(fc.get_pose())` loop). The wall-clock claim is meaningless but the *harness* will be ready when the Phase 3 simulator lands.
2. **Add a "fidelity-tier" marker on each ISC.** Tag `[x] (sim)` vs `[x] (gazebo)` vs `[x] (hardware)`. Today's 29 `[x]` ISCs are all `(sim)`-tier — making that visible in the ISA prevents over-claiming.

---

### ⚠️ Bad — No CI Configuration Committed

`Makefile` collects `make all` (lint + typecheck + test). No `.github/workflows/`, no equivalent. The bar is high; the enforcement bar isn't set up yet. The next-steps roadmap lists Phase 6 (Quality gates) as `partial`.

#### 🔧 How to improve

```yaml
# .github/workflows/ci.yml
name: ci
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -e ".[dev]"
      - run: make all
      - run: pytest --cov=closedSpace --cov=engine --cov-fail-under=80
```

Adds a coverage gate at 80 % (current is 97 %, so the gate has 17 points of headroom for unrelated future changes). On a green build, the badge in a future README anchors the quality claim.

---

### ⚠️ Bad — No Property / Fuzz Tests On The Map Validator

`closedSpace/map/validate.py` is the firewall between operator YAML and the planner. The test suite (`test_validate.py`, 13 tests) covers known-bad cases by name (missing field, bad version, rack outside centerline, etc.). Property-based tests against the JSON Schema would broaden coverage cheaply.

#### 🔧 How to improve

```python
# closedSpace/tests/map/test_validate_properties.py
from hypothesis import given, strategies as st
from hypothesis_jsonschema import from_schema
from closedSpace.map.validate import validate_against_schema

@given(from_schema(map_json_schema()))
def test_schema_valid_maps_dont_raise(m):
    validate_against_schema(m)  # no exception
```

Pairs well with `hypothesis-jsonschema` which generates schema-valid inputs. Catches the cases the suite doesn't name.

---

## 5. Documentation Practices

### ✅ Good — ISA-As-System-Of-Record Is Working

`closedSpace/ISA.md` is 634 lines covering Problem → Vision → Out-of-Scope → Principles → Constraints → Goal → Criteria (44 ISCs) → Test Strategy → Features → Decisions (12 dated entries) → Changelog → Verification (5 entries). A new engineer reads one file, picks an open ISC, finds the test that probes it, ships a PR.

The pattern is unusual in being honored: the document is dated, the Decisions log uses the conjecture/refutation/learning trio for the rack-fixture incident, the Verification log records what was probed and what was returned.

---

### ✅ Good — Three-Tier CLAUDE.md With Non-Overlapping Scope

```
/CLAUDE.md                    ← umbrella: Python, pytest, docstrings, engine rules
/closedSpace/CLAUDE.md        ← indoor: SLAM only, 0.5 m clearance, <15 min, <50 ms
/openSpace/CLAUDE.md          ← outdoor: GPS+IMU, FAA, 60+ min, wind class
```

The umbrella rule "never put domain-specific logic in the engine" is enforced by AST scan; the closedSpace rule "GPS forbidden" is enforced by grep. Convention scales through enforcement, not vigilance.

---

### ✅ Good — Six In-Tree Docs For closedSpace, Each With Stated Audience

```
closedSpace/docs/
├── drones.md             — drone-platform survey, 4 candidate categories
├── map-schema.md         — schema semantics + path-derivation contract
├── next-steps.md         — 9-phase roadmap with open decisions
├── operator-README.md    — operator-facing console + abort flow
├── session-state.md      — active engineering session notes
└── use-cases.md          — UC-1..UC-9 narrative
```

Each names its audience and status legend (DONE / partial / Sketched). `next-steps.md` is the work order; `use-cases.md` is the human-readable narrative every UC maps back to Features and ISCs in the ISA.

---

### ✅ Good — JSON Schemas Committed And Tested

```
closedSpace/schemas/map.schema.json            — validates input
closedSpace/schemas/mission_report.schema.json — validates output
```

Both are loaded by the source they govern (`closedSpace/map/validate.py` and `closedSpace/report/builder.py` respectively). The report builder calls `jsonschema.validate()` on every `finalize()` — the schema is enforced on every produced report, not just at review.

---

### ⚠️ Bad — No Top-Level README At The Umbrella

A human visitor cloning `dronePrjs` hits `pyproject.toml` first and has to puzzle out the project from package metadata. The umbrella `CLAUDE.md` is agent-facing; a human-facing README is missing.

#### 🔧 How to improve

```markdown
# dronePrjs

Umbrella for two warehouse-inventory drone applications sharing a common engine.

- `closedSpace/` — indoor / GPS-denied / SLAM-based. **Status: early build, 5 of 8 phases complete.**
- `openSpace/` — outdoor / GPS-available. **Status: stub only.**
- `engine/` — shared Protocols (flight control, localization, sensors, telemetry) + in-process kinematic reference sim.

## Getting started

    python -m venv .venv && source .venv/bin/activate
    pip install -e ".[dev]"
    make all              # lint + typecheck + test

## Reading order

1. `CLAUDE.md` — universals.
2. `closedSpace/ISA.md` — the indoor PRD-as-spec.
3. `closedSpace/docs/next-steps.md` — work order.

## Status

- 100 tests passing in ~52 s, 97 % coverage.
- `mypy --strict` clean across 29 source files.
- `ruff check` clean.
- Phase 3 (simulator bring-up) blocked on three open decisions.
```

One screen, no agent-isms, points at the ISA for depth.

---

### ⚠️ Bad — openSpace Has No ISA Or Use Cases

The umbrella's design tension between indoor and outdoor can't be resolved without an openSpace contract. Today the only artifact is the CLAUDE.md, which is operating rules — not scope.

#### 🔧 How to improve

Even a 100-line first cut. Problem / Vision / Out-of-Scope / Constraints / Goal / 5–10 ISCs. The act of writing it surfaces engine over-fit before it ossifies.

---

## 6. Domain Isolation Practices

### ✅ Good — Engine Bleed Is AST-Enforced, Not Convention-Enforced

```python
# engine/tests/test_no_domain_bleed.py (abridged)
def test_engine_has_no_domain_imports():
    for py_file in (ENGINE_ROOT).rglob("*.py"):
        if py_file.is_relative_to(ENGINE_ROOT / "tests"):
            continue
        tree = ast.parse(py_file.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                top = node.module.split(".")[0]
                assert top not in {"closedSpace", "openSpace"}, ...
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    assert top not in {"closedSpace", "openSpace"}, ...
```

A new engineer who adds `from closedSpace.map import Map` to an engine module gets a red test in 52 s, not a code-review nit weeks later. This is the right blast-radius for the rule.

---

### ✅ Good — GPS Forbidden In closedSpace By Two Probes

```
ISC-30 (doc-layer):  grep -r "GPSProvider" closedSpace/  → 0
ISC-36 (engine-layer): AST scan ensures engine doesn't import closedSpace/openSpace
```

The two probes guard different boundaries — ISC-30 stops closedSpace from depending on the wrong Protocol; ISC-36 stops engine from leaking either domain. Together they make the umbrella's contract surface mechanically inspectable.

---

### ✅ Good — Rule-Of-Three Deferred Extractions Are Named

ISA Decision 2026-05-03 OBSERVE/iter-2 names what *will* move out of `closedSpace/map/types.py` when openSpace consumes them:

- General geometry primitives: `Point2D`, `Point3D`, polygon utilities → `engine/geometry/`
- Reference-frame conventions (+x east, +y north, +z up, meters) → `engine/conventions.md`

The decision is explicit that *promotion happens after the second consumer demands it*. Premature generalization is named as a failure mode.

---

### ⚠️ Bad — `closedSpace/map/validate._point_in_polygon` Is Used By `closedSpace/operator/preflight.py`

```python
# closedSpace/operator/preflight.py
from closedSpace.map.validate import _point_in_polygon
```

`_point_in_polygon` is leading-underscore-private, but it's used cross-module. Either it should be public (preflight is a legitimate consumer) or it should be promoted to a shared geometry module.

#### 🔧 How to improve

Create `closedSpace/geometry.py` (or, if openSpace also wants it, `engine/geometry/__init__.py` — see the Rule-of-Three list):

```python
# closedSpace/geometry.py
def point_in_polygon(pt: tuple[float, float], polygon: list[list[float]]) -> bool:
    """Return True if pt is inside the simple polygon (winding-rule)."""
    ...
```

Then both `closedSpace/map/validate.py` and `closedSpace/operator/preflight.py` import from there. Leading-underscore stays a convention for module-internal helpers only.

---

## 7. Roadmap & Decision Practices

### ✅ Good — Phase-Per-Commit Cadence

Six commits, six phases. Each commit message names the ISCs flipped:

```
5c45c9e  Phase 5 complete: operator CLI + preflight + abort (6 ISCs)
d806b80  Phase 4 complete: capture, storage, report (9 ISCs)
2108819  Phase 2 complete: engine Protocols (ISC-11, ISC-30, ISC-36)
1293a81  Phase 1 complete: MissionPlanner (ISC-6..10)
8764611  Complete Phase 0 (foundations)
f51a541  Initial commit: dronePrjs umbrella project
```

The git log is usable as project history. A reviewer reads the messages and knows what was delivered.

---

### ✅ Good — `next-steps.md` Is The Work Order And It's Honest About Open Decisions

```
| Phase | Theme                        | Effort | Status              |
| 0     | Foundations                  | 1–2d   | done                |
| 1     | MissionPlanner               | 3–5d   | done                |
| 2     | Engine contracts             | 2–3d   | done                |
| 3     | Simulator bring-up           | 5–10d  | DECISION NEEDED     |
| 4     | Capture + Storage + Report   | 4–6d   | done (sim-fidelity) |
| 5     | OperatorConsole + preflight  | 3–4d   | done (sim-fidelity) |
| 6     | Quality gates + anti-scope   | 2–3d   | partial             |
| 7     | MapBuilderFromWMS            | 5–10d  | sketched            |
| 8     | Pilot mission (real ware.)   | 5+d    | not-started         |
```

Three open decisions (D1 sim-vs-hardware, D2 simulator choice, D3 flight stack) are named with recommendations. None are ratified. They live in the doc with their alternatives so they don't get re-debated each iteration.

---

### ⚠️ Bad — Open Decisions Have Been Open For Six Weeks

D1, D2, D3 were named on 2026-05-03 with the note *"answer before Phase 3"*. Phase 4 and Phase 5 shipped without answering them — possible because the in-process sim was sufficient for those phases. The decisions are still open as of `5c45c9e`.

The risk: Phase 3 work starts with stale assumptions, or doesn't start at all. ISC-12/13/14/31/33 stay `[ ]` indefinitely.

#### 🔧 How to improve

Ratify all three decisions in a single ISA Decisions-block entry before any Phase 3 work begins. The recommendations in `next-steps.md` are defensible (sim-first with Gazebo as Phase 3.2; defer flight stack). The act of writing the entry crystallises the choice — and if any recommendation is wrong, that's the moment to surface it.

---

### ⚠️ Bad — The "Thinking-Floor Doctrine Deviation" Has Never Been Closed

ISA Decision 2026-05-03 VERIFY records: *"E3 hard floor is ≥4 thinking capabilities invoked via Skill/Agent tool; this run invoked ISA only. ... Natural remediation: spawn FirstPrinciples + RedTeam against this ISA before implementation begins (E4 review)."*

Six weeks and five phases later, the FirstPrinciples + RedTeam review has not happened. The flag remains in the document.

#### 🔧 How to improve

Run the review before Phase 3. The cost is one session; the benefit is a sanity-check on the 44 ISCs and 12 Decisions accumulated so far. Honest flag-and-remediate is the discipline; honest flag-and-forget is debt.

---

### ✅ Good — ISA Changelog Uses Conjecture / Refutation / Learning

```
- 2026-05-03 fixture geometry bug caught at first run
  - conjectured: rack centers 0.7 / 1.95 / 3.20 / 4.45 fit four 1.2 m
    racks inside a 5.0 m centerline with comfortable end buffers
  - refuted by: validate() raised MapValidationError: rack 'A1-W4'
    extends outside centerline (position_along=4.45, length_m=1.2,
    centerline_length=5.000), because 4.45 + 0.6 = 5.05 > 5.0
  - learned: rack-extent semantic check works exactly as designed —
    the validator caught a geometry bug in the fixture *before* any
    flight code touched the map.
  - criterion now: ISC-2 / ISC-9 flipped to [x] with smoke-runner
    evidence; rack centers tightened to 0.7 / 1.9 / 3.1 / 4.3.
```

The pattern (conjecture / refutation / learning / criterion-update) is a small ritual that turns each surprise into project memory. It's rare to see this in a changelog.

---

## 8. Summary Scorecard

| Area | Good practices | Bad practices | Net |
|---|---|---|---|
| Architecture | 4 (engine-as-contract, downward layering, frozen dataclasses, pure planner, local-first storage) | 2 (openSpace stub, no directory fsync) | 🟢 Strong |
| Safety | 3 (GPS-static-probe, pre-arm gate, map-staleness first-class) | 3 (no map signature, per-waypoint-only abort, no link-loss RTH) | 🟡 Good |
| Code Quality | 5 (mypy --strict clean, ruff clean, domain exceptions, enums, zero TODO) | 2 (SimFC uses RuntimeError, constants drift) | 🟢 Strong |
| Testing | 4 (100/100 passing, co-located, static-analysis tests, e2e against sim) | 3 (sim-only fidelity, no CI, no property tests) | 🟡 Good |
| Documentation | 4 (ISA-as-SOR, 3-tier CLAUDE.md, 6 in-tree docs, JSON schemas tested) | 2 (no umbrella README, no openSpace ISA) | 🟢 Strong |
| Domain Isolation | 3 (AST-enforced bleed, GPS dual-probe, Rule-of-Three named) | 1 (cross-module _private import) | 🟢 Strong |
| Roadmap & Decisions | 3 (phase-per-commit, honest open decisions, conjecture/refutation changelog) | 2 (decisions stale 6 weeks, thinking-floor remediation never executed) | 🟡 Good |

**Overall posture:** unusually disciplined for a six-commit project. The discipline is concentrated in the parts that survive contact with users (architecture, types, tests, docs). The gaps are concentrated in the parts that only matter at pilot (signed maps, link-loss handling, abort granularity inside long dwells) — appropriate for the phase, *if* they close before pilot rather than at pilot.

The single largest leverage move is **writing `openSpace/ISA.md` and a `SimGPS` reference impl**. It costs one session, surfaces engine over-fit while the engine is still cheap to reshape, and turns the umbrella's central claim ("shared engine for two domains") from inferred to verified.

---

*Analysis based on commit `5c45c9e` on `main`. `make all` + coverage run locally before this writeup; 100 / 100 tests passing in 52 s, 97 % coverage, mypy strict + ruff clean.*
