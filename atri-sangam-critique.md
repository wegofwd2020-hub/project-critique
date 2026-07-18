# Atri Sangam — Code Review & Critique

**Reviewed:** 2026-07-18 (v1.0 — first review, against the extracted source snapshot dated 2026-07-18)
**Repo:** `atri-sangam` (source snapshot; no git history in the reviewed artifact)
**Phase:** Alpha library + red-team simulator. `Development Status :: 3 - Alpha`, `v0.1.0`. Detection logic, collectors, persistence, simulator, and dashboard are built and tested; **no live runner/daemon exists** — the shipped artifact is a well-tested library plus a batch/demo driver, not yet a deployable monitor.
**Scope:** Fixed-site GPS/PNT integrity monitor — cross-checks a GPS receiver (NMEA RMC/GGA) against independent references (SNTP, local-clock holdover, solar prediction) and raises explainable step/CUSUM/staleness alarms on jamming, spoofing, or outage. Python 3.10+, stdlib-only core; Dash/Plotly an optional extra.
**Rating key:** ✅ Strong · ⚠️ Gap / Risk · ❌ Critical Issue
**Related:** [atri-sangam-development-pattern.md](atri-sangam-development-pattern.md) · [atri-sangam-practices.md](atri-sangam-practices.md)

---

## Executive Summary

Atri Sangam is an unusually well-engineered **detection-logic library** for GPS/PNT integrity monitoring at a fixed site. The core thesis — a "sangam" of independent channels (GPS, NTP, holdover, celestial) whose disagreement is the alarm signal — is realised cleanly: pure-transformer collectors, a central `DiscrepancyEngine` referee, three complementary detector layers (step for jumps, CUSUM for slow walks, staleness for silence), and provenance-carrying alarms. The engineering discipline is real and verified against the code: **stdlib-only core** (`dependencies = []`), **everything injectable** (sockets, clocks, stores are constructor parameters), **fail-loud config validation** at construction, **6 OpenSpec contracts** whose numeric scenarios are mirrored by the acceptance tests, and a **deterministic-by-seed simulator** that triples as mock data, demo driver, and red-team tool. 66 tests pass at 90 % coverage, with real hand-derived assertions rather than smoke checks.

The gap between what it *is* and what it *claims to protect* is the story of this review. It is a library, not a monitor: **there is no continuous collection loop, scheduler, serial/gpsd runner, or daemon anywhere in the source** — `check_staleness()` must be called by something that does not exist yet. And its one security-sensitive external surface, the **SNTP client, has no anti-spoofing protection** — it never verifies the response's source address or echoed originate timestamp, so the reference channel meant to *catch* spoofing is itself trivially spoofable by off-path UDP. For a product whose entire premise is detecting deception, that is the finding to fix first.

**Verdict:** Strong bones, honest scoping, exemplary test discipline for a v0.1.0. Not deployable as a monitor yet — and the NTP channel needs origin/replay validation before it can be trusted as an independent reference.

## Snapshot

| Dimension | Reading |
|---|---|
| Source LOC | **1,961** (23 files); tests **719** (7 files) |
| Tests | **66**, all passing, **90 % coverage** (675 stmts, 66 missed) |
| Dependencies | **Core: none** (stdlib only). `[dashboard]`: dash/plotly. `[dev]`: pytest/pytest-cov |
| Specs | **6 OpenSpec contracts** (anomaly-detection, nmea-ingestion, ntp-time, persistence, simulation, solar-prediction) |
| CI | ✅ Real — GitHub Actions, Python 3.10 + 3.12, `pytest --cov`, plus a dashboard-extra import job |
| Lint/type gate | ⚠️ **None** — no ruff, no mypy config (contrast dronePrjs's `mypy --strict` + ruff) |
| TODO/FIXME in source | **0** |
| Runnable monitor? | ❌ **No** — no runner/daemon/serial loop; library + demo replay only |

## 1. Architecture

### Strengths
- ✅ **Clean fan-out referee.** Independent channels emit frozen `Sample(channel, timestamp, value)` objects into one `DiscrepancyEngine`, which lazily builds a per-channel step+CUSUM detector pair and health record on first sample (`discrepancy/engine.py:54-64`). Unknown channel names auto-register against a `FALLBACK_DETECTOR` (`config.py:150-153`) — a real extensibility seam that lets a third party add a WWVB or star-tracker channel without editing the package.
- ✅ **Collectors are pure transformers.** `GpsSampleFactory.samples_from_rmc` (`collectors/gps.py:29-64`) turns a sentence + local time into 0–2 samples with no I/O; SNTP, holdover likewise take their sockets/clocks by injection. This is what makes the whole suite deterministic and offline.
- ✅ **Three-layer detection maps to a real threat taxonomy** — step catches jumps (crude spoofing/glitches), CUSUM catches sub-threshold slow walks (sophisticated spoofing), staleness catches silence (jamming/outage). The CUSUM is textbook-correct two-sided tabular form (`discrepancy/cusum.py:47-75`).
- ✅ **Provenance is structural, not decorative.** Every `Alarm` carries channel/detector/value/threshold/message (`models.py:34-73`), so operators see an explainable event, not a red light.

### Gaps & Risks
- ⚠️ **The dashboard discards the engine's richer status model.** `DiscrepancyEngine.status()` computes a proper three-way `OK/ALARM/STALE` per channel and resets on new data (`engine.py:142-167`, `:85`), but the dashboard's `_refresh()` never calls it — it re-derives a binary ok/alarm from the *entire unbounded alarm history* in the store (`dashboard/app.py:80`). The `"stale"` color at `app.py:26` is unreachable dead code, and a channel that alarmed once then recovered shows red forever. The two status models have diverged.
- ⚠️ **"Live" dashboard is a static replay.** `main()` runs the whole scenario to completion into the store *before* starting Dash (`dashboard/app.py:133-148`); the `dcc.Interval` re-reads a finished dataset. No code path ingests real-time samples while serving.
- ⚠️ **Solar channel is math-only.** `predictors/solar.py` computes an elevation residual but nothing wraps it into a `Sample` — `CH_SOLAR` is registered (`config.py:141-144`) but never produced outside tests. Honestly labelled roadmap (needs a sun-sensor), but the diagram's celestial channel is aspirational today.

## 2. Code Quality

### Strengths
- ✅ **Frozen, slotted dataclasses with `__post_init__` validation everywhere** — `SiteConfig`, `CusumConfig`, `StepConfig`, `DetectorConfig` all raise `ConfigError`/`ThresholdConfigError` at construction (`config.py:43-113`). "Fail loudly at startup" is implemented, not just claimed.
- ✅ **Typed exception hierarchy with sensible multiple inheritance** — `NmeaChecksumError(NmeaParseError)`, `ThresholdConfigError(DetectorError, ConfigError)` (`exceptions.py`) let callers catch at any granularity.
- ✅ **Zero TODO/FIXME**, clean layer separation, each component independently testable.

### Gaps & Risks
- ❌ **No lat/lon range validation in the NMEA parser.** `_parse_latlon` (`collectors/nmea.py:62-79`) checks hemisphere and `minutes < 60` but never bounds the degrees field. A checksum-valid `"9130.0000,N"` parses to **91.5° latitude** without error and flows into `haversine_m()` producing a numerically valid but meaningless distance. This is inconsistent with the rigor of `SiteConfig.__post_init__` and `solar_position()`, which both range-check — in a module whose own docstring claims "auditable correctness."
- ⚠️ **`ingest()` is not transactional against store failures.** In-memory state (`last_sample`, counts, `alarms`) is mutated (`engine.py:83-93`) *before* the store writes (`:95-98`). A `StorageError` mid-loop propagates out — the caller never gets that call's alarms — while in-memory bookkeeping has already advanced. In-memory state and the persisted evidence trail can diverge during exactly the failure mode (storage errors) the persistence spec cares about.
- ⚠️ **No lint/type gate.** No ruff, no `mypy --strict`. The code *looks* type-clean, but nothing enforces it — a regression that a sibling project (dronePrjs) catches in CI would pass here.

## 3. Test Coverage

### Strengths
- ✅ **66 tests, 90 % coverage, real assertions.** Hand-derived expected values, not smoke: an SNTP offset computed to the decimal from a crafted 4-timestamp exchange (`test_ntp.py:60-72`), an XOR checksum verified by hand (`test_nmea.py:22-24`), holdover drift recovered to `1e-9` (`test_detectors.py:117-126`).
- ✅ **Discriminative detector tests.** A drift provably below the step threshold (`0.002 × 199 = 0.398 < 0.5`) is asserted to be caught by CUSUM *and missed by step* (`test_detectors.py:78-92`) — a genuine separation test.
- ✅ **Physically-grounded solar invariants** (equinox declination ≈ 0, solar-noon elevation > 85°, midnight-sun < −80°) test the approximation without over-fitting to golden values (`test_solar_store_demo.py:16-81`).
- ✅ **End-to-end acceptance spine** — `test_engine.py` runs simulator → GPS factory → engine → alarms/store for all four scenarios plus persistence.

### Gaps & Risks
- ⚠️ **Holes at the seams, not within components.** `GpsSampleFactory.samples_from_rmc` has no *direct* unit test (only indirect via the engine helper); `NtpCollector.collect()` failure-propagation is untested (only `SntpClient.query()` is); `DiscrepancyEngine.status()` — the whole OK/ALARM/STALE model — has **zero unit coverage**.
- ⚠️ **Spec mirroring is partial.** Numeric scenarios that *are* tested match to the decimal, but `nmea-ingestion`'s "valid fix → two residuals" / "void fix → nothing" and `ntp-time`'s "failure produces no sample" have no dedicated test.
- ⚠️ **No fuzz/property tests on the NMEA parser** despite it being a security-relevant surface (see §5); only a fixed set of hand-crafted malformed strings.

## 4. Documentation

### Strengths
- ✅ **Exceptional README** — precise threat model, an accurate architecture diagram, honest precision hierarchy ("GPS is nanoseconds; radio is milliseconds; celestial is seconds"), a real deploy guide, and a `docs/comparable-systems.md` situating it against BlueSky/GPSPATRON/RAIM/chrony. The name essay (Atri restoring the eclipsed Sun) is unusually apt.
- ✅ **Specs-as-contracts** — 6 OpenSpec files with concrete numeric scenarios the tests mirror. Design commitments are stated *and* verified true.

### Gaps & Risks
- ⚠️ **README slightly oversells present tense.** The diagram and "How it works" read as a running system; the celestial channel, the "live" dashboard, and any runner are roadmap. The prose is honest on close reading (roadmap section, `* optional hardware` footnote), but a skim implies more is wired than is.

## 5. Security & Safety

### Strengths
- ✅ **No fabricated data.** Failed collectors raise typed exceptions (`CollectorTimeout`, `NtpQueryError`); a void GPS fix returns `[]` rather than a fake zero (`collectors/gps.py:51-52`); silence is then caught by staleness. "A monitor that invents readings is worse than none" is implemented.

### Gaps & Risks
- ✅ **Closed 2026-07-18 (commit `be19c81`).** ~~SNTP client has no anti-spoofing protection whatsoever~~ — `query()` now rejects a reply (`NtpQueryError`) unless mode == 4, leap indicator ≠ 3, stratum ∈ 1–15, **and the originate timestamp echoes the request's transmit timestamp**. The originate-echo check is the load-bearing defence: an off-path attacker who cannot observe the request cannot forge the 64-bit transmit timestamp, so a blindly-injected reply is rejected. Added 5 anti-spoof regression tests (71 passing). *Original finding (for the record): the client discarded `recvfrom()`'s source address, never verified the originate echo, and never validated mode/stratum/leap — so the reference channel meant to catch GPS spoofing was itself trivially off-path-spoofable.* **Remaining defence-in-depth (optional):** source-IP filtering via `connect()` was not added (the originate-echo check already defeats off-path injection, which is the primary threat).
- ⚠️ **No sentence-length cap before checksum.** `validate_sentence()` XORs the whole payload with no upper bound (`nmea.py:19-31`) — latent (no serial transport exists yet) but a corrupt/hostile stream that never emits `*XX` would scan/allocate proportional to whatever the transport hands it. Remember this when the gpsd/serial runner is built.
- ⚠️ **Thresholds are consumer-grade defaults**, explicitly "meant to be overridden," never validated against real jamming/spoofing hardware (`config.py:116-153`).

## 6. Scalability & Operations

### Strengths
- ✅ **Local-first, air-gap-ready** — SQLite store, stdlib-only core, deterministic offline tests. The right posture for the degraded environments it's built for.

### Gaps & Risks
- ❌ **No runner / scheduler / daemon exists.** Every collector is a one-shot call; `check_staleness()` must be driven by something on a cadence that isn't in the repo. `demo.py` replays a finite generator, not a live feed. Today this is a library + batch driver, not a monitor — the single most important framing for anyone assessing deployability.
- ⚠️ **No concurrency model.** `engine._channels` is an unlocked dict; `SqliteStore` opens one connection without `check_same_thread=False`, WAL, or batching, committing after every write (`storage/store.py:52,89`). Three-to-five concurrent collector channels (as the diagram implies) would need serialization or locking — neither exists nor is documented as a constraint.

## Priority Actions (Top 6)

1. ✅ **Harden the SNTP client** — **done 2026-07-18 (`be19c81`):** `query()` now validates mode/leap/stratum and verifies the originate-timestamp echo, rejecting spoofed/injected replies (+5 regression tests). Optional remaining defence-in-depth: source-IP filtering via `connect()`. (`collectors/ntp.py`)
2. ❌ **Build and test a runner service** — serial/gpsd → `GpsSampleFactory`, periodic `NtpCollector`/`HoldoverModel.update`/`check_staleness`. Zero lines of this exist; it's the gap between "library" and "monitor."
3. ❌ **Add lat/lon range validation** in `_parse_latlon` to match `SiteConfig`/`solar_position` rigor. (`collectors/nmea.py:62-79`)
4. ⚠️ **Fix the dashboard to consume `DiscrepancyEngine.status()`** (or a live feed) instead of re-deriving a lossy binary status from unbounded alarm history; wire the STALE state; clear resolved alarms. (`dashboard/app.py:72-128`)
5. ⚠️ **Make `ingest()` store-transactional** (or persist before advancing in-memory state) so the evidence trail can't diverge on storage failure. (`discrepancy/engine.py:67-99`)
6. ⚠️ **Add a lint/type gate to CI** (ruff + `mypy --strict`) and close the seam-level test holes (`samples_from_rmc`, `collect()` failure, `status()`).

---

*First review (v1.0). Grounded in a full read of `src/`, `tests/`, `openspec/specs/`, and CI, plus a verified local `pytest` run (66 passed, 90 % coverage) and demo-scenario execution. Cost-of-time-and-money analysis is maintained privately.*
