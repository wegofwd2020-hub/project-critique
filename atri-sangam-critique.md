# Atri Sangam — Code Review & Critique

**Reviewed:** 2026-07-21 (v2.0 — second review, against `main` at `d953201`)
**Previous:** v1.0, 2026-07-18, against the v0.1.0 source snapshot
**Repo:** `atri-sangam` (private, GitHub org)
**Phase:** Alpha (`Development Status :: 3 - Alpha`, `pyproject` version `0.1.7`). **Now a deployable monitor, not just a library** — daemon, systemd unit, six live channels, two storage backends, live dashboard.
**Scope:** Fixed-site GPS/PNT integrity monitor — cross-checks a GPS receiver (NMEA RMC/GGA/GSV) against independent references (NTP with Byzantine consensus, Roughtime with Ed25519 verification, WWVB radio, local-clock holdover, C/N₀ uniformity) and raises explainable step/CUSUM/staleness alarms on jamming, spoofing, or outage. Python 3.10+, stdlib-only core.
**Rating key:** ✅ Strong · ⚠️ Gap / Risk · ❌ Critical Issue
**Related:** [atri-sangam-development-pattern.md](atri-sangam-development-pattern.md) · [atri-sangam-practices.md](atri-sangam-practices.md)

---

## What changed since v1.0

**126 commits on `main` in three days.** The v1.0 review is comprehensively out of date; treat any of its claims not restated here as void.

| v1.0 finding | Status at `d953201` |
|---|---|
| ❌ **No runner / scheduler / daemon exists** — "library + batch driver, not a monitor" | ✅ **Resolved.** `src/atri_sangam/runner/` — `cli.py`, `monitor.py`, `sources.py`, `config.py`, plus a systemd unit. `atri-sangam-run --source sim\|gpsd\|serial` |
| ⚠️ Dashboard re-derives a binary status from unbounded alarm history; `"stale"` colour unreachable | ⚠️ **Partly resolved** — see §7. The dashboard now reads the engine's published three-way verdict, and `stale` renders. **The alarm latch itself was not fixed** and has moved, not gone |
| ⚠️ "Live" dashboard is a static replay | ✅ **Resolved.** Opens the store read-only and polls; the daemon writes concurrently under WAL |
| ⚠️ No concurrency model — unlocked dict, single connection, no WAL | ✅ **Resolved.** `Monitor` serialises every engine/store touch under one `threading.Lock`; store opens `check_same_thread=False` with `journal_mode=WAL`; `test_store_threadsafe.py` covers it |
| ⚠️ `DiscrepancyEngine.status()` has zero unit coverage | ✅ **Resolved.** Referenced in 21 test assertions |
| ⚠️ SNTP single-server, spoofable | ✅ **Resolved** (was already closed in v1.0) and extended: `MultiNtpCollector` agrees a Marzullo consensus and emits `ntp_consensus_spread` |
| ❌ No lat/lon range validation in `_parse_latlon` | ❌ **Still open.** Unchanged (§2) |
| ⚠️ No sentence-length cap before checksum — *"latent (no serial transport exists yet)"* | ⚠️ **Escalated — no longer latent** (§5). The transport now exists |
| ⚠️ `ingest()` not transactional against store failures | ⚠️ **Still open.** Unchanged (§2) |
| ⚠️ No lint/type gate | ⚠️ **Still open.** No ruff, no mypy, CI runs pytest only |
| ⚠️ `samples_from_rmc` has no direct unit test | ⚠️ **Still open.** Still only exercised via the engine |
| ⚠️ Solar channel is math-only | ⚠️ **Still open.** `predictors/solar.py` is not wired into the daemon; `runner/cli.py` imports no solar collector |

## Executive Summary

Three days turned a well-engineered detection library into a monitor you could actually deploy. Source grew 1,961 → **5,469 LOC**, tests 66 → **323**, OpenSpec contracts 6 → **12**, and the channel set went from four to nine — adding cryptographically-verified Roughtime time (Ed25519, Merkle proofs, multi-server Byzantine consensus), WWVB radio time decoded from GPIO edges, and C/N₀ uniformity from GSV sentences, which is a genuine spoofing tell. A TimescaleDB backend landed behind the same `Store` protocol. The discipline held at speed: still `dependencies = []` in the core, still zero TODO/FIXME, still specs-as-contracts with numeric scenarios mirrored by tests.

The engineering judgement on display is good and occasionally excellent. Marzullo interval intersection for both NTP and Roughtime consensus is the correct algorithm rather than an averaging shortcut, and it emits the disagreement *as its own integrity channel* instead of hiding it. The runner keeps every step body single-threaded and unit-testable, with the thread wrapper as a thin loop. `Store` is a `@runtime_checkable` Protocol, so a backend implementing half the contract fails `isinstance` — a real gate, not a comment.

What has not moved is the small set of correctness gaps v1.0 already named. `_parse_latlon` still accepts 91° latitude. `ingest()` still advances in-memory state before persisting, so the evidence trail can diverge on exactly the storage failure the persistence spec cares about. There is still no lint or type gate. And one v1.0 finding has **got worse without changing a line**: the unbounded NMEA sentence scan was excused as latent because no serial transport existed. `GpsdSource` and `SerialSource` now exist, and neither bounds line length.

The new finding of this review is that the **alarm state latches forever** (§7). A channel that alarms once reports `alarm` until the process restarts, because `status()` derives it from a cumulative counter that is never reset. The recent dashboard work correctly removed the *viewer's* duplicate status rule — but it made the engine's rule authoritative rather than correcting it, and that rule has the same defect. For a monitor whose pitch is explainable, actionable alarms, a pill that can never go green is the finding to fix first.

**Verdict:** Genuinely deployable now, and the growth was disciplined rather than frantic. Two input-validation gaps on the one untrusted surface, one latching-state defect, and no lint gate are what stand between this and something you would leave running unattended at a site that matters.

## Snapshot

| Dimension | v1.0 (2026-07-18) | v2.0 (`d953201`) |
|---|---|---|
| Source LOC | 1,961 (23 files) | **5,469** (42 files) |
| Test LOC | 719 (7 files) | **4,104** (35 files) |
| Tests | 66 | **323, all passing** (verified locally) |
| Coverage | 90 % | **not re-measured this pass** — `pytest-cov` absent from the local env; CI runs `--cov` |
| Channels | 4 | **9** (+ WWVB, Roughtime, C/N₀ spread, consensus-spread channels) |
| Specs | 6 | **12** |
| Dependencies | core: none | **core: none** (`dependencies = []`); extras: dashboard, roughtime, serial, gpio, timescale |
| CI | pytest, 3.10 + 3.12 | pytest, 3.10 + 3.12 (unchanged) |
| Lint/type gate | ⚠️ none | ⚠️ **still none** |
| TODO/FIXME | 0 | **0** |
| Runnable monitor? | ❌ no | ✅ **yes** — daemon + systemd unit |

## 1. Architecture

### Strengths
- ✅ **The referee pattern scaled cleanly to nine channels.** Adding WWVB, Roughtime and C/N₀ required no change to `DiscrepancyEngine`: they are collectors emitting `Sample`s into the same fan-in. The extensibility seam v1.0 praised in theory has now been exercised three times in practice.
- ✅ **Consensus is modelled as evidence, not just a number.** `MultiNtpCollector` and `MultiRoughtimeCollector` agree a Byzantine-tolerant offset by Marzullo interval intersection *and* emit `ntp_consensus_spread` / `roughtime_consensus_spread` / `roughtime_verify_failures` as first-class channels. Disagreement among references is itself monitored — the correct instinct for this problem.
- ✅ **The runner is testable by construction.** Each `_*_step` is a single-threaded method unit-tested directly; the threading layer only loops them. One `threading.Lock` guards every engine and store touch, so the concurrency story is "serialise everything" — simple, and honestly documented as such.
- ✅ **Storage is a real protocol, enforced.** `Store` is `@runtime_checkable`; both backends implement the full interface; `test_store_protocol.py` and `test_store_factory.py` assert conformance by `isinstance`.

### Gaps & Risks
- ⚠️ **Solar remains aspirational.** `predictors/solar.py` computes an elevation residual with real physics and real tests, but `runner/cli.py` imports no solar collector — the celestial channel in the README diagram still does not exist at runtime. Honestly labelled as roadmap; still the widest gap between the diagram and the daemon.
- ⚠️ **Publishing latency is one staleness period.** Channel state reaches the store from `Monitor._staleness_step`, so a transition is visible to a viewer after up to `--staleness-check-s` (default 1 s). Fine for a dashboard; worth knowing before anything alarms off this table.

## 2. Code Quality

### Strengths
- ✅ **Frozen, slotted, self-validating dataclasses throughout**, now including the two new published records. Fail-loud-at-construction is applied consistently rather than selectively.
- ✅ **Zero TODO/FIXME across 5,469 lines**, sustained through a 2.8× expansion.
- ✅ **Optional dependencies stay optional.** `psycopg`, `dash`, `cryptography`, `pyserial` and `gpiod` are all imported lazily inside the functions that need them, so the stdlib-only core claim survives five extras.

### Gaps & Risks
- ❌ **No lat/lon range validation in the NMEA parser — unchanged from v1.0.** `_parse_latlon` (`collectors/nmea.py`) validates the hemisphere letter and `minutes < 60` but never bounds degrees. A checksum-valid `"9130.0000,N"` parses to **91.5° latitude** and flows into `haversine_m()`, producing a numerically valid, physically meaningless distance. Still inconsistent with `SiteConfig.__post_init__` and `solar_position()`, which both range-check. Three days of new validation code went in around it.
- ⚠️ **`ingest()` is still not transactional against store failures — unchanged from v1.0.** In-memory state (`last_sample`, counts, `alarms`) is mutated before the store writes. A `StorageError` mid-loop propagates out — the caller never receives that call's alarms — while bookkeeping has already advanced. In-memory state and the persisted evidence trail diverge during precisely the failure the persistence spec exists to cover.
- ⚠️ **Still no lint or type gate.** No ruff, no `mypy --strict`, no config file, and `ci.yml` runs pytest only. The code reads type-clean and the new modules carry full annotations, but nothing enforces it — and the codebase is now 2.8× larger than when this was first raised.

## 3. Test Coverage

### Strengths
- ✅ **323 tests, and the growth is proportional** — test LOC grew faster than source (5.7× vs 2.8×). Not a suite that got left behind.
- ✅ **The hardest new logic is the best tested.** Marzullo consensus, Roughtime Ed25519 verification and the RFC-compliant codec, WWVB edge decoding, and the C/N₀ transport/verification failure split all carry dedicated files with derived expected values.
- ✅ **`status()` now has real coverage** — the v1.0 hole is closed, with 21 assertions across the suite.
- ✅ **Storage parity is tested on both backends**, including an offline fake-connection harness for TimescaleDB that needs no database server.

### Gaps & Risks
- ⚠️ **`GpsSampleFactory.samples_from_rmc` still has no direct unit test** — unchanged from v1.0. It remains exercised only through the engine, so a regression in the 0-, 1-, or 2-sample fan-out surfaces as a confusing integration failure rather than a pointed one. This is the oldest untouched test gap in the repo.
- ⚠️ **No fuzz or property tests on the NMEA parser**, unchanged from v1.0 and now more pressing: §5's transports feed it directly from a socket or serial port.
- ⚠️ **Coverage is unverified in this review.** v1.0 measured 90 %; the local environment lacks `pytest-cov`, so this pass reports test count only. CI does measure it — worth reading the badge rather than trusting either number here.

## 4. Documentation

### Strengths
- ✅ **The README kept pace with a 2.8× expansion**, including an accurate mermaid diagram of the full nine-channel set, opt-in markers for every channel requiring hardware or configuration, and an honest precision hierarchy.
- ✅ **12 specs-as-contracts**, doubled from six, with the newest requirement (channel-state publishing) carrying scenarios that the tests mirror.
- ✅ **The known limitation is documented where users will hit it** — §7's latch is called out in both the README and the CHANGELOG rather than left for a reader to discover.

### Gaps & Risks
- ⚠️ **Roadmap strikethroughs are accumulating.** The README's roadmap now mixes delivered items (struck through, or annotated "implemented") with genuine roadmap in one list. It is accurate but increasingly hard to skim for what is *not* done — the single question a prospective operator most needs answered.
- ✅ **Fixed since v1.0:** the "README slightly oversells present tense" finding no longer holds — the runner exists, so the present tense is now earned.

## 5. Security & Safety

### Strengths
- ✅ **Roughtime is a genuinely strong addition.** Ed25519 signature verification with Merkle proofs gives a time reference an off-path attacker cannot forge without the private key, and multi-server consensus tolerates a lying minority. This is a meaningful step beyond what NTP alone can promise.
- ✅ **Failure never fabricates.** Failed collectors raise typed exceptions; a void GPS fix returns nothing; a failed Roughtime round still persists its verification-failure count as evidence. "A monitor that invents readings is worse than none" continues to be implemented, not just claimed.
- ✅ **NTP consensus closes the v1.0 single-server exposure** structurally rather than by patching one client.

### Gaps & Risks
- ⚠️ **Unbounded NMEA sentence scan — escalated from v1.0, and the escalation needed no code change.** `validate_sentence()` strips, finds the last `*`, and XORs the whole payload with no upper bound. v1.0 rated this latent because "no serial transport exists yet" and said to remember it when the runner was built. **The runner was built.** `GpsdSource.lines()` iterates a text-mode socket file object and `SerialSource` a serial port, neither bounding line length — a corrupt or hostile stream that never emits a newline makes Python buffer without limit before the parser ever sees it. Cap the line at NMEA's 82-character maximum (plus slack) at the transport, and again before checksum.
- ❌ **Unbounded latitude/longitude — see §2.** This is the other half of the same story: the one untrusted input surface is now reachable from a real device, and it validates neither length nor range.
- ⚠️ **Thresholds remain consumer-grade defaults**, unchanged from v1.0 and explicitly documented as "meant to be overridden", still never validated against real jamming or spoofing hardware. Everything downstream — bands, alarms, the operator's trust — inherits that.

## 6. Scalability & Operations

### Strengths
- ✅ **Deployable.** systemd unit, three source types, two storage backends, a read-only live viewer. The v1.0 headline gap is closed.
- ✅ **TimescaleDB behind the same interface** gives a real path off SQLite for multi-node or long-retention deployments without touching the engine.
- ✅ **Local-first posture preserved.** Stdlib-only core, deterministic offline tests, every network channel opt-in — omit them all and it still runs air-gapped.

### Gaps & Risks
- ⚠️ **Serialise-everything will become the ceiling.** One lock around every engine and store touch is right for nine channels at ≤1 Hz. It is documented rather than hidden, but it is the first thing that will bind if channel count or sample rate rises.
- ⚠️ **`cli.py` has no `__main__` guard**, unlike `demo.py` and `dashboard/app.py`. `python -m atri_sangam.runner.cli` imports the module, does nothing, and **exits 0** — a silent no-op that reads as success. Harmless with the console script, actively misleading in a smoke test or container `CMD`.

## 7. NEW — Alarm state latches forever

The single most important finding of this review.

`DiscrepancyEngine.status()` resolves a channel to `ALARM` whenever `state.alarm_count > 0`, and `ingest()` increments that counter without ever resetting or decaying it. Only `state.stale` is cleared on new data. So **a channel that alarms once reports `alarm` for the lifetime of the process**, no matter how long it has since behaved.

This was partially visible in v1.0, which described the dashboard re-deriving a lossy binary status from unbounded alarm history and recommended consuming `status()` instead. That recommendation was implemented — correctly, in that the viewer's duplicate rule is gone and the engine's verdict is now single-sourced and authoritative. But the engine's rule has the same defect the dashboard's did, so the behaviour did not change. The recent work made the rule canonical rather than correct, and its CHANGELOG says so.

Confirmed empirically: replaying the `dropout` scenario leaves every channel reporting `alarm` at the end, including channels whose data resumed.

Why it matters for this product specifically: the pitch is explainable, actionable alarms — "an operator sees an explainable event, not a red light." A pill that can never return to green is exactly a red light. It also makes the state useless for the obvious downstream consumer, alerting: you cannot page on a signal that never clears.

The fix is a semantic decision, not a patch: `ALARM` should mean "alarmed within a recent window" (the channel's `max_sample_age_s`, or an explicit dwell) or decay on sustained clean samples. Either changes the anomaly-detection contract and deserves its own spec scenarios.

## Priority Actions (Top 6)

1. ❌ **Fix the alarm latch** (§7). Decide what `ALARM` means — a recent window, or decay on clean samples — write the scenarios, then change `status()`. Everything downstream of channel health is unreliable until this lands. (`discrepancy/engine.py`)
2. ❌ **Bound and range-check the untrusted input surface.** Cap NMEA line length at the transport (`runner/sources.py`) and before checksum (`collectors/nmea.py`), and add degree-range validation to `_parse_latlon`. These are one surface, now reachable from a real device, and both have been open since v1.0.
3. ⚠️ **Add a lint/type gate to CI** — ruff + `mypy --strict`, as a sibling project already does. Third review running; the codebase has nearly tripled since it was first raised.
4. ⚠️ **Make `ingest()` store-transactional** (or persist before advancing in-memory state) so the evidence trail cannot diverge on storage failure. Unchanged since v1.0. (`discrepancy/engine.py`)
5. ⚠️ **Close the oldest test gap** — direct unit tests for `samples_from_rmc`, plus property/fuzz tests on the NMEA parser now that a real transport feeds it.
6. ⚠️ **Add a `__main__` guard to `cli.py`** (§6) so `python -m` cannot silently succeed at doing nothing, and wire the solar predictor into the daemon or move it out of the architecture diagram.

---

*Second review (v2.0), against `main` at `d953201`. Grounded in a re-read of `src/`, `tests/`, `openspec/specs/`, CI, and the README, plus a verified local `pytest` run (323 passed) and execution of all four demo scenarios. Coverage was not re-measured — `pytest-cov` is absent from the review environment. Every v1.0 finding was re-checked against current code rather than carried forward; the disposition table above records each one. Cost-of-time-and-money analysis is maintained privately.*
