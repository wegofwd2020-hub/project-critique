# Atri Sangam — Code Review & Critique

**Reviewed:** 2026-07-21 (v2.1 — disposition update, against `main` at `0effae1`)
**Anchor:** `0effae1`
**Previous:** v2.0, 2026-07-21, against `main` at `d953201` · v1.0, 2026-07-18,
against the v0.1.0 source snapshot

**Repo:** `atri-sangam` (private, GitHub org)
**Phase:** Alpha (`Development Status :: 3 - Alpha`, `pyproject` version `0.1.7`). **Now a deployable monitor, not just a library** — daemon, systemd unit, six live channels, two storage backends, live dashboard.
**Scope:** Fixed-site GPS/PNT integrity monitor — cross-checks a GPS receiver (NMEA RMC/GGA/GSV) against independent references (NTP with Byzantine consensus, Roughtime with Ed25519 verification, WWVB radio, local-clock holdover, C/N₀ uniformity) and raises explainable step/CUSUM/staleness alarms on jamming, spoofing, or outage. Python 3.10+, stdlib-only core.
**Rating key:** ✅ Strong · ⚠️ Gap / Risk · ❌ Critical Issue
**Related:** [atri-sangam-development-pattern.md](atri-sangam-development-pattern.md) · [atri-sangam-practices.md](atri-sangam-practices.md)

> **v2.1 — what this revision changes.** Priority actions 1 and 2 of v2.0 were
> both implemented and merged the same day (PRs #25 and #26), so §7 and §5's
> input-bounds findings are now closed. A fourth finding this revision raised —
> the simulator source's false alarms — was fixed before this revision landed
> (PR #27) and is recorded as closed rather than open. This revision re-dispositions them
> against the code rather than restating v2.0; the sections below are marked
> where they changed. Nothing else was re-reviewed — §§1, 3, 4, 6 and the
> remaining §2 findings stand as written at v2.0. Suite is now **350 tests**.

---

## What changed since v1.0

**126 commits on `main` in three days.** The v1.0 review is comprehensively out of date; treat any of its claims not restated here as void.

| v1.0 finding | Status at `0effae1` (v2.1) |
|---|---|
| ❌ **No runner / scheduler / daemon exists** — "library + batch driver, not a monitor" | ✅ **Resolved.** `src/atri_sangam/runner/` — `cli.py`, `monitor.py`, `sources.py`, `config.py`, plus a systemd unit. `atri-sangam-run --source sim\|gpsd\|serial` |
| ⚠️ Dashboard re-derives a binary status from unbounded alarm history; `"stale"` colour unreachable | ✅ **Resolved at v2.1** (PR #25). The dashboard reads the engine's published three-way verdict, `stale` renders, and the latch itself is now gone — see §7 |
| ⚠️ "Live" dashboard is a static replay | ✅ **Resolved.** Opens the store read-only and polls; the daemon writes concurrently under WAL |
| ⚠️ No concurrency model — unlocked dict, single connection, no WAL | ✅ **Resolved.** `Monitor` serialises every engine/store touch under one `threading.Lock`; store opens `check_same_thread=False` with `journal_mode=WAL`; `test_store_threadsafe.py` covers it |
| ⚠️ `DiscrepancyEngine.status()` has zero unit coverage | ✅ **Resolved.** Referenced in 21 test assertions |
| ⚠️ SNTP single-server, spoofable | ✅ **Resolved** (was already closed in v1.0) and extended: `MultiNtpCollector` agrees a Marzullo consensus and emits `ntp_consensus_spread` |
| ❌ No lat/lon range validation in `_parse_latlon` | ✅ **Resolved at v2.1** (PR #26). Degrees bounded by the hemisphere letter — 90 for `N`/`S`, 180 for `E`/`W` (§2) |
| ⚠️ No sentence-length cap before checksum — *"latent (no serial transport exists yet)"* | ✅ **Resolved at v2.1** (PR #26). Capped at the NMEA 0183 maximum of 82 before the checksum scan, and both transports bound each read (§5) |
| ⚠️ `ingest()` not transactional against store failures | ⚠️ **Still open.** Unchanged (§2) |
| ⚠️ No lint/type gate | ⚠️ **Still open.** No ruff, no mypy, CI runs pytest only |
| ⚠️ `samples_from_rmc` has no direct unit test | ⚠️ **Still open.** Still only exercised via the engine |
| ⚠️ Solar channel is math-only | ⚠️ **Still open.** `predictors/solar.py` is not wired into the daemon; `runner/cli.py` imports no solar collector |

## Executive Summary

Three days turned a well-engineered detection library into a monitor you could actually deploy. Source grew 1,961 → **5,469 LOC**, tests 66 → **323**, OpenSpec contracts 6 → **12**, and the channel set went from four to nine — adding cryptographically-verified Roughtime time (Ed25519, Merkle proofs, multi-server Byzantine consensus), WWVB radio time decoded from GPIO edges, and C/N₀ uniformity from GSV sentences, which is a genuine spoofing tell. A TimescaleDB backend landed behind the same `Store` protocol. The discipline held at speed: still `dependencies = []` in the core, still zero TODO/FIXME, still specs-as-contracts with numeric scenarios mirrored by tests.

The engineering judgement on display is good and occasionally excellent. Marzullo interval intersection for both NTP and Roughtime consensus is the correct algorithm rather than an averaging shortcut, and it emits the disagreement *as its own integrity channel* instead of hiding it. The runner keeps every step body single-threaded and unit-testable, with the thread wrapper as a thin loop. `Store` is a `@runtime_checkable` Protocol, so a backend implementing half the contract fails `isinstance` — a real gate, not a comment.

**Updated at v2.1.** v2.0 named two correctness gaps that had survived since the first review, and raised a third of its own. All three are now closed. `_parse_latlon` bounds degrees by the hemisphere letter; the NMEA sentence scan is capped before the checksum and both transports bound each read; and the alarm state clears after a per-channel quiet window instead of latching (§§2, 5, 7). Two of those had been open across two reviews, and the third was found and fixed the same day.

What genuinely has not moved: `ingest()` still advances in-memory state before persisting, so the evidence trail can diverge on exactly the storage failure the persistence spec cares about, and there is **still no lint or type gate** — now raised across three consecutive reviews while the codebase nearly tripled. The solar channel remains unwired, and `samples_from_rmc` remains the oldest untested seam in the repo.

**Verdict:** Deployable, and the correctness gaps that would have made it untrustworthy at a real site are closed. What remains is discipline debt rather than defect: no enforced types or lint, one non-transactional write path, and a diagram that still shows a channel the daemon does not run.

## Snapshot

| Dimension | v1.0 (2026-07-18) | v2.1 (`0effae1`) |
|---|---|---|
| Source LOC | 1,961 (23 files) | **5,469** (42 files) |
| Test LOC | 719 (7 files) | **4,104** (35 files) |
| Tests | 66 | **350, all passing** (verified locally) |
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
- ✅ **Resolved at v2.1 (PR #26).** ~~No lat/lon range validation in the NMEA parser~~ — `_parse_latlon` now bounds degrees using the hemisphere letter itself (90 for `N`/`S`, 180 for `E`/`W`), so the checksum-valid `"9130.0000,N"` that previously parsed to **91.5° latitude** and flowed into `haversine_m()` is rejected with `NmeaParseError`. The limit needed no new parameter and no caller change, because the hemisphere already distinguishes a valid 179.5° longitude from an impossible 179.5° latitude. *Original finding (for the record): open across both prior reviews, in a module whose own docstring claims "auditable correctness", while three days of new validation code went in around it.*
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
- ✅ **Resolved at v2.1 (PR #26).** ~~Unbounded NMEA sentence scan~~ — capped in both places the v2.0 finding called for. `validate_sentence()` refuses anything past the NMEA 0183 maximum of 82 characters **before** computing the checksum, and `GpsdSource`/`SerialSource` each read at most 128 bytes per line, so a stream that never emits a newline can no longer be buffered without limit before the parser is consulted. Verified not to clip legitimate traffic: the longest sentence the simulator emits is a 68-character GSV, and a 60 s daemon replay dropped zero lines. *This is the finding that escalated from latent to live without a line of code changing, when the runner gave the parser real transports.*
- ✅ **Unbounded latitude/longitude — see §2, also resolved at v2.1.** Both halves of the untrusted input surface are now bounded: length at the transport and before the checksum, range at the field.
- ⚠️ **Thresholds remain consumer-grade defaults**, unchanged from v1.0 and explicitly documented as "meant to be overridden", still never validated against real jamming or spoofing hardware. Everything downstream — bands, alarms, the operator's trust — inherits that.

## 6. Scalability & Operations

### Strengths
- ✅ **Deployable.** systemd unit, three source types, two storage backends, a read-only live viewer. The v1.0 headline gap is closed.
- ✅ **TimescaleDB behind the same interface** gives a real path off SQLite for multi-node or long-retention deployments without touching the engine.
- ✅ **Local-first posture preserved.** Stdlib-only core, deterministic offline tests, every network channel opt-in — omit them all and it still runs air-gapped.

### Gaps & Risks
- ⚠️ **Serialise-everything will become the ceiling.** One lock around every engine and store touch is right for nine channels at ≤1 Hz. It is documented rather than hidden, but it is the first thing that will bind if channel count or sample rate rises.
- ⚠️ **`cli.py` has no `__main__` guard**, unlike `demo.py` and `dashboard/app.py`. `python -m atri_sangam.runner.cli` imports the module, does nothing, and **exits 0** — a silent no-op that reads as success. Harmless with the console script, actively misleading in a smoke test or container `CMD`.

## 7. Alarm state latches forever — ✅ RESOLVED at v2.1

*Raised as the single most important finding of v2.0; fixed the same day by PR #25. Retained here because the shape of the bug is worth keeping on the record.*

**The finding.** `DiscrepancyEngine.status()` resolved a channel to `ALARM` whenever `state.alarm_count > 0`, and `ingest()` incremented that counter without ever resetting or decaying it. Only `state.stale` was cleared on new data. So a channel that alarmed once reported `alarm` for the lifetime of the process, no matter how long it had since behaved. Confirmed empirically at the time: replaying the `dropout` scenario left **every** channel reporting `alarm`, including channels whose data had resumed.

**Why it mattered.** The product's pitch is explainable, actionable alarms — "an operator sees an explainable event, not a red light." A pill that can never return to green *is* a red light. It also made the state useless for the obvious downstream consumer, alerting: you cannot page on a signal that never clears.

**Why the preceding work did not fix it.** v1.0 described the dashboard re-deriving a lossy binary status from unbounded alarm history and recommended consuming `status()` instead. That was implemented — the viewer's duplicate rule went away and the engine's verdict became authoritative — but the engine's rule carried the same defect, so behaviour did not change. That work made the rule canonical rather than correct, and said so in its own CHANGELOG.

**The fix.** `ALARM` now means *alarmed within `alarm_clear_s` of the channel's newest sample*, with `alarm_clear_s` set per channel at roughly 2–4× its own observation cadence. Recency is measured on the sample clock, so `status()` needed no new argument and stays deterministic offline. `alarm_count` is retained and still published as context — it was always sound as history and only ever wrong as a status input.

Two consequences the fix introduced, both documented in the anomaly-detection spec: `STALE`-before-`ALARM` precedence is now **load-bearing** (a silent channel produces no samples and so cannot advance its own window), and sample timestamps must share a clock with the value passed to `check_staleness` (both existing paths already do).

**Evidence it worked** — scenario replays, before → after:

| Scenario | Before | After |
|---|---|---|
| `clean` | all `ok` | all `ok` |
| `time_walk` | **all 4 `alarm`** | only `gps_time_offset` |
| `position_jump` | **all 4 `alarm`** | only `gps_position_error` |
| `dropout` | **all 4 `alarm`** | all `ok` — outage ended, channels recovered |

Every scenario previously ended with unrelated channels red. Status now names the channel actually under attack.

## Priority Actions

**Closed since v2.0** — both the same day the review landed:

1. ✅ ~~Fix the alarm latch~~ (§7) — PR #25.
2. ✅ ~~Bound and range-check the untrusted input surface~~ (§§2, 5) — PR #26.
3. ✅ ~~Fix the simulator source's false alarms~~ — PR #27. Raised by this
   revision and fixed before it landed. `--source sim --scenario clean` produced
   118 alarms because the replay ran ~3× faster than real time while samples
   were stamped with the wall clock; the daemon now replays in real time, and
   the same run produces zero step and zero CUSUM alarms with the offset holding
   under 0.01 s against a 0.5 s threshold. The same discarded clock also meant a
   simulated outage cost no wall time, so staleness never fired for the reason
   the `dropout` scenario exercises — also fixed.

**Open, in priority order:**

1. ⚠️ **Add a lint/type gate to CI** — ruff + `mypy --strict`, as a sibling project already does. **Third consecutive review** raising this; the codebase has nearly tripled since it was first noted, and it is now the oldest unaddressed finding in the file.
2. ⚠️ **Make `ingest()` store-transactional** (or persist before advancing in-memory state) so the evidence trail cannot diverge on storage failure. Unchanged since v1.0. (`discrepancy/engine.py`)
3. ⚠️ **Close the oldest test gap** — direct unit tests for `samples_from_rmc`, plus property/fuzz tests on the NMEA parser. More valuable now than when first raised: the parser has real transports feeding it, and v2.1's bounds are exactly the kind of logic fuzzing exercises well.
4. ⚠️ **Add a `__main__` guard to `cli.py`** (§6) so `python -m atri_sangam.runner.cli` cannot silently succeed at doing nothing, and wire the solar predictor into the daemon or move it out of the architecture diagram.

---

*Revision v2.1, against `main` at `0effae1` — a disposition update, not a full re-review. §§2, 5 and 7 were re-checked against current code after PRs #25 and #26 merged; §§1, 3, 4, 6 stand as written at v2.0. Verified by a local `pytest` run (350 passed) and execution of all four demo scenarios. Coverage was not measured — `pytest-cov` is absent from the review environment; CI measures it. Cost-of-time-and-money analysis is maintained privately.*

*v2.0 (`d953201`) was the second review, grounded in a full re-read of `src/`, `tests/`, `openspec/specs/`, CI and the README, with every v1.0 finding re-checked against current code rather than carried forward.*
