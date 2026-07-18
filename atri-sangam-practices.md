# Atri Sangam — Good Practices, Bad Practices & How to Improve

**Document type:** Engineering practices analysis
**Scope:** Python 3.10+ GPS/PNT integrity monitor — collectors, discrepancy engine + detectors, predictors, simulator, storage, dashboard. Reviewed from a source snapshot (no git history).
**Period:** 2026-07-18 (v1.0 — first review, `v0.1.0`, Alpha)
**Related:** [atri-sangam-critique.md](atri-sangam-critique.md) · [atri-sangam-development-pattern.md](atri-sangam-development-pattern.md)
**Rating key:** ✅ Good practice · ⚠️ Bad practice · ❌ Critical issue · 🔧 How to improve

---

## Table of Contents

1. Architecture Practices
2. Detection & Statistics Practices
3. Security & Robustness Practices
4. Code Quality Practices
5. Testing Practices
6. Operational / Deployability Practices

---

## 1. Architecture Practices

### ✅ Good — Everything injectable, so the whole system is deterministic and offline
Sockets, clocks, and stores are constructor parameters: `SntpClient(server, port, timeout_s, socket_factory, time_func)` (`collectors/ntp.py:66-81`), `NtpCollector(client, time_func=time.time)` (`ntp.py:137-141`), `SqliteStore(path)` (`storage/store.py:50`), `DiscrepancyEngine(config, store=None)` (`discrepancy/engine.py:48`). This is the practice that makes a 66-test suite fully deterministic and air-gap-testable — `tests/test_ntp.py` drives a `FakeSocket` with no network at all.

### ✅ Good — Collectors are pure transformers, decoupled from transport
`GpsSampleFactory.samples_from_rmc` (`collectors/gps.py:29-64`) takes a sentence + clock time and returns samples with zero I/O. Wiring it to gpsd/serial is "a few lines" precisely because the transform carries no transport assumptions.

### ✅ Good — Extensibility seam via fallback channel registration
Unknown channel names auto-register against `FALLBACK_DETECTOR` (`config.py:150-153`, `engine.py:54-64`), so a third party can add a WWVB or star-tracker channel without editing the package. The abstraction earns its keep.

### ⚠️ Bad — Two divergent status models; the dashboard uses the lossy one
`DiscrepancyEngine.status()` computes a correct three-way `OK/ALARM/STALE` that resets on new data (`engine.py:142-167`, `:85`), but the dashboard ignores it and re-derives a binary status from the store's *entire unbounded alarm history* (`dashboard/app.py:80`). The `"stale"` color (`app.py:26`) is unreachable dead code; a recovered channel stays red forever.
🔧 **How to improve:** delete the dashboard's ad-hoc status derivation; render from `engine.status()` (or a snapshot table the engine writes). One status model, tested once.

## 2. Detection & Statistics Practices

### ✅ Good — Textbook two-sided tabular CUSUM
`CusumDetector.update()` (`discrepancy/cusum.py:47-75`) implements `S+ = max(0, S+ + (x − target − k))` and its mirror correctly, with slack `k`, threshold `h`, and reset-on-alarm. It is the right tool for the "slow spoof" threat the step detector can't see.

### ✅ Good — Three detectors mapped to three distinct attack shapes
Step (jumps), CUSUM (slow walks), staleness (silence) is a genuine taxonomy, not redundancy — and the tests prove separation (a drift below the step threshold caught only by CUSUM, `test_detectors.py:78-92`).

### ⚠️ Bad — CUSUM direction label can misreport a two-sided event
`direction = "positive" if s_pos >= s_neg else "negative"` (`cusum.py:60`) is computed after both stats update; both can be non-zero, and the alarm reports only the marginally-larger side without noting both accumulated.
🔧 **How to improve:** include both `s_pos`/`s_neg` in the alarm provenance when both exceed zero; it costs nothing and strengthens the "explainable" promise.

## 3. Security & Robustness Practices

### ✅ Good — No fabricated data, ever
Failed collectors raise typed exceptions; a void (`V`) GPS fix returns `[]` rather than a fake zero (`collectors/gps.py:51-52`); silence is caught by staleness. The design commitment "a monitor that invents readings is worse than none" is actually enforced.

### ✅ Fixed 2026-07-18 (`be19c81`) — SNTP reply validation (was: no packet-origin or replay validation)
`collectors/ntp.py`: `query()` now rejects a reply (`NtpQueryError`) unless mode == 4, leap ≠ 3, stratum ∈ 1–15, **and the originate timestamp echoes the request's transmit timestamp** — the echo check defeats off-path injection (an attacker who can't see the request can't forge the 64-bit timestamp). +5 regression tests. *Was:* the client discarded `recvfrom()`'s source address, never verified the originate echo, and never validated mode/stratum/leap, so the time channel meant to catch spoofing was itself off-path-spoofable.
🔧 **Remaining (defence-in-depth, optional):** source-IP filtering via `connect()` (kernel drops foreign-source replies) was not added — the originate-echo check already closes the primary off-path threat. Operationally, still run ≥2 NTP servers and cross-check (the README recommends this).

### ⚠️ Bad — NMEA lat/lon parsed without range validation
`_parse_latlon` (`collectors/nmea.py:62-79`) checks hemisphere and `minutes < 60` but not the degrees bound. `"9130.0000,N"` (checksum-valid) parses to 91.5° without error and flows into `haversine_m()`.
🔧 **How to improve:** bound degrees to `[0,90]`/`[0,180]` and raise `NmeaParseError` — mirror the rigor already in `SiteConfig.__post_init__` (`config.py:43-51`).

### ⚠️ Bad — No sentence-length cap before checksum
`validate_sentence()` XORs the whole payload unbounded (`nmea.py:19-31`). Latent today (no serial transport), but a hostile stream that never terminates a sentence scans/allocates without limit.
🔧 **How to improve:** cap sentence length (NMEA 0183 is ≤82 chars) and reject over-long lines before parsing — do it now, before the serial runner lands.

## 4. Code Quality Practices

### ✅ Good — Fail-loud validation on every config/value object
Frozen dataclasses with `__post_init__` raising `ConfigError`/`ThresholdConfigError` (`config.py:43-113`). Misconfiguration fails at construction, not at 3 a.m. under a real outage.

### ✅ Good — Typed exception hierarchy with useful granularity
`NmeaChecksumError(NmeaParseError)`, `ThresholdConfigError(DetectorError, ConfigError)` (`exceptions.py`) let callers catch broadly or narrowly. Zero bare `except Exception`.

### ✅ Good — Zero TODO/FIXME/XXX in source
A clean tree for a v0.1.0.

### ⚠️ Bad — No lint or type gate
No ruff, no `mypy --strict`, no config for either in `pyproject.toml`. The code reads type-clean but nothing enforces it — a sibling project (dronePrjs) gates exactly this in CI.
🔧 **How to improve:** add `ruff check` + `mypy --strict` to `.github/workflows/ci.yml` and fix to green; cheap insurance on a codebase this disciplined.

### ⚠️ Bad — `ingest()` mutates in-memory state before persisting
`engine.py:83-98` advances counts/alarms before store writes; a `StorageError` mid-loop diverges memory from the evidence trail.
🔧 **How to improve:** persist first (or wrap the sample+alarms write in one transaction) so a storage failure can't leave the two out of sync.

## 5. Testing Practices

### ✅ Good — 66 tests, 90 % coverage, real hand-derived assertions
Not smoke: an SNTP offset derived to the decimal from a crafted exchange (`test_ntp.py:60-72`), an XOR checksum verified by hand (`test_nmea.py:22-24`), holdover drift recovered to `1e-9` (`test_detectors.py:117-126`).

### ✅ Good — Physically-grounded invariants over golden values
Solar tests assert equinox declination ≈ 0, solar-noon elevation > 85°, midnight-sun < −80° (`test_solar_store_demo.py:16-81`) — a mathematically honest way to test an approximation without over-fitting.

### ✅ Good — Spec scenarios mirrored to the decimal
Where a test exists, it matches its `openspec/specs/*/spec.md` scenario's exact numeric parameters (e.g. anomaly-detection's sub-threshold walk, `test_engine.py:39-54`).

### ⚠️ Bad — Coverage holes are at the component seams
`GpsSampleFactory.samples_from_rmc` has no direct unit test; `NtpCollector.collect()` failure propagation is untested; `DiscrepancyEngine.status()` has zero unit coverage; several spec scenarios (nmea "void fix → nothing", ntp "failure → no sample") have no dedicated test.
🔧 **How to improve:** add direct tests for each seam — they're the integration points most likely to break silently.

### ⚠️ Bad — No fuzz/property tests on a security-relevant parser
Only fixed hand-crafted malformed strings exercise the NMEA parser.
🔧 **How to improve:** add a property/fuzz test (e.g. Hypothesis) throwing random/adversarial bytes at `validate_sentence()`/`_parse_latlon` — asserts it always raises a typed error or returns cleanly, never a bad coordinate.

## 6. Operational / Deployability Practices

### ✅ Good — Local-first, air-gap-ready by design
Stdlib-only core (`dependencies = []`), SQLite store, optional lazy-imported dashboard. Correct for the degraded environments the tool exists for.

### ✅ Good — Real CI, not decorative
GitHub Actions on Python 3.10 + 3.12 with `pytest --cov`, plus a dedicated dashboard-extra import job (`.github/workflows/ci.yml`).

### ❌ Critical — No runner/scheduler/daemon exists
Every collector is one-shot; `check_staleness()` needs a periodic driver that isn't in the repo; `demo.py` replays a finite generator, not a live feed. This is a tested library + batch driver, not a running monitor.
🔧 **How to improve:** build a runner service (serial/gpsd → factory; periodic NTP/holdover/staleness ticks; systemd unit) and test it against the simulator as a live source. This is the single biggest step from "library" to "monitor."

### ⚠️ Bad — No concurrency model for multi-channel operation
`engine._channels` is an unlocked dict; `SqliteStore` uses one connection without `check_same_thread=False`/WAL/batching, committing per write (`storage/store.py:52,89`). Concurrent channels would race.
🔧 **How to improve:** decide explicitly — either serialize all engine access through one collector thread (document it), or add locking + WAL. Don't leave it undefined.

---

*First review (v1.0). All findings verified against the source, a local `pytest` run (66 passed, 90 % coverage), and demo-scenario execution. Cost analysis maintained privately.*
