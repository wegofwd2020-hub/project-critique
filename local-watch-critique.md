# local_watch — Code Review & Critique

<!-- doc-meta:start -->
| Field | Value |
|---|---|
| Product repo | `wegofwd2020-hub/local_watch` |
| Branch | `main` |
| Git commit | `13e387e` (as of 2026-08-31) |
| Product version | —  (commit-based; no release version) |
| Doc updated | 2026-09-03 |
| Last deployed | deployed 2026-08-31 — live on 3 machines (mambakkam aggregator + vaganam + macOS Siva-MAC02-4) |
<!-- doc-meta:end -->

**Reviewed:** 2026-09-03 (v1.0 — first review, against `main` at `13e387e`)
**Anchor:** `13e387e`
**Repo:** `local_watch` (public, GitHub org `wegofwd2020-hub`)
**Phase:** v1 shipped and **deployed** — `Development Status` unversioned (`pyproject` version `0.0.1`), but this is a running production monitor, not a pre-release library.
**Scope:** Read-only personal-fleet monitor — per-machine collectors (Linux + macOS) emit metric snapshots → sync over Tailscale → central aggregator on `mambakkam` → deterministic threshold/trend rules produce severity flags → an LLM agent (`wegofwd-llm`) writes plain-language optimization recommendations, **never in the control path** → a self-contained HTML fleet dashboard + Markdown report, surfaced via a `wegofwd-hub` tile. v1 is observe-and-recommend only; no state changes anywhere in the pipeline.
**Rating key:** ✅ Strong · ⚠️ Gap / Risk · ❌ Critical Issue
**Related:** [local-watch-development-pattern.md](local-watch-development-pattern.md) · [local-watch-practices.md](local-watch-practices.md)

---

## Executive Summary

`local_watch` is a small (848 production LOC / 1,170 test LOC, 130 tests, all passing), disciplined system that is unusual in the portfolio for one reason: it is the first product reviewed here whose critique-worthy history is **known from real production incidents rather than inferred from code-reading**. Between the day it first merged (2026-08-29) and the day it went live on all three machines (2026-08-31), it failed in production four distinct ways — three of them the exact "fails open, reads as healthy" class the design explicitly claims to avoid — and every one was diagnosed, fixed, and pinned under a regression test within the same 3-day, 37-commit, 5-PR window. That is the real story here: not "is the code clean" (it is), but "did the safety floor hold under contact with reality, and is it now load-bearing rather than aspirational."

The read-only invariant is genuine and mechanically verifiable — every unit in `deploy/` calls exactly `local_watch collect`, `local_watch ingest`, `local_watch render`, or a single-file `rsync`; none require `sudo`; the collectors' own probe list (`df`, `free`, `apt list`, `systemctl --failed`, `vm_stat`, `softwareupdate --list`, `launchctl list`) is entirely read commands, and `deploy/README.md` tells an operator to `grep` for `read(` to confirm it. The LLM-out-of-control-path invariant is equally real: `agent.recommend()` only ever writes into a `dict[str, str]` that `report.py` renders as escaped text; a provider exception anywhere degrades to a clearly labelled deterministic fallback (`FALLBACK_NOTICE`), never to a retry, a mutation, or a silent guess.

The fail-open history is the headline finding, in both directions. **The failure mode was real**: a dead collector, a broken probe, or a machine that stopped reporting all rendered the dashboard green — the exact opposite of what a monitor exists to do — and shipped that way in the first merge. **The fix is real too**: `test_rules_failopen.py` and `test_collector_degradation.py` now assert the previously-silent failure paths directly (missing metrics do not read as `0%`; a probe that never ran is distinguished from one that ran and returned nothing; a stale snapshot is `crit`, not silently served as current). A second production bug — the aggregator rsyncing to itself — produced a misleading `ssh` authentication error that pointed the operator at the wrong layer entirely; the fix (`sync-to-aggregator.sh`'s self-target guard) is covered by 8 tests including one that asserts the error message names the actual problem, not the symptom. A third — `pip install -e .` never producing an executable because `pyproject.toml` had no build backend or console script — meant the entire deploy runbook was unreachable from a cold clone; `test_packaging.py` now pins both facts directly against the TOML. A fourth — an XSS-via-LLM-output path, since every string reaching `render_dashboard` (recommendations, flag messages, machine names, OS strings, metric names) is attacker- or LLM-influenced — is closed by `html.escape()` applied uniformly, with `test_report_escaping.py` asserting the specific payload `</pre><script>alert(1)</script>` never survives unescaped.

What has not fully caught up is the documentation. The README's architecture section and metric-domain list (CPU/load average, thermals, fan state, battery health, top-process tracking, log volume, network throughput, disk SMART health) describe a monitor considerably larger than what ships: the collectors emit exactly two metrics (`disk_root_pct`, `mem_used_pct`) plus four facts, one of which (`reboot_required`) is hardcoded `"false"` in both collectors and can never fire. The README's own status line still reads "Not yet running on the fleet" and "Getting started: TBD once implemented" — both false as of the 2026-08-31 three-machine deploy this review is measuring. None of this is a safety problem (the rules and dashboard are honest about what they *do* have data for), but a reader skimming the README would materially overestimate what is actually being watched.

**Verdict:** A small, safety-floor-first monitor whose most important property — read-only by construction, LLM never in the control path — held together across a real deploy, and whose real production failures were converted into regression tests rather than folklore. The gap between the README's stated metric scope and the two metrics actually collected is the most material open finding; the fail-open class itself is now closed with tests standing in its place. Deployable and, more importantly, already deployed.

## Snapshot

| Dimension | Measured @ `13e387e` |
|---|---|
| Production LOC | 848 (13 files: `local_watch/` + `collectors/`) |
| Test LOC | 1,170 (16 files) |
| Tests | **130**, all passing (verified locally, `pytest -q`, 16.5s) |
| Test-to-source LOC ratio | 1.4:1 |
| Commits on `main` | 37, across 5 merged PRs, 2026-08-29 → 2026-08-31 (~45h calendar span) |
| Dependencies | 1 runtime (`wegofwd-llm[anthropic]`, pinned to a tag via git URL); dev-only `pytest`, `ruff` |
| CI | GitHub Actions, Python 3.11 + 3.13 matrix, `pytest -q` only |
| Lint/type gate | ⚠️ `ruff` is a dev dependency; **not run in CI** |
| Metrics actually collected | 2 (`disk_root_pct`, `mem_used_pct`) + 4 facts (`updates_pending`, `failed_units`, `reboot_required` [dead — always `false`], `probes_failed`) |
| Metrics the README describes | ~12 (adds CPU/load, thermals, fan, battery, top-process, log volume, network, SMART — none implemented) |
| Deployed? | ✅ Yes — 3 machines live since 2026-08-31 (mambakkam aggregator + vaganam + macOS) |
| Known incidents in this window | 4 (3 fail-open variants, 1 XSS, 1 deploy-gap, 1 first-deploy self-sync bug — see §5) — **all fixed and test-pinned** |

## 1. Architecture

### Strengths
- ✅ **The layering is exactly what the pitch promises.** `collectors/{linux,macos}.py` → `Snapshot` (pure data) → `store.Store` (SQLite, keyed `machine, ts`) → `rules.evaluate()` (pure function, `Snapshot` + history → `list[Flag]`) → `agent.recommend()` (flags + snapshots → text, LLM optional) → `report.py` (escapes everything, renders HTML/Markdown). No layer reaches backward: rules never touch the LLM, the LLM never touches the store, collectors never see rules.
- ✅ **The LLM-out-of-control-path invariant is structural, not a comment.** `agent.recommend()`'s only side effect is populating a `dict[str, str]`; every consumer of that dict (`report.render_dashboard`, `render_markdown`) treats it as opaque, untrusted text and escapes it identically to every other field. There is no code path by which an LLM response can reach a shell, a file write, or a rule.
- ✅ **The None-vs-empty-string distinction in `collectors/base.py:probe()` is the single decision the whole fail-open fix hangs on.** A probe that never ran (timeout, missing binary, non-zero exit with no stdout) returns `None`; a probe that ran and legitimately produced nothing (`systemctl --failed` on a healthy box) returns `""`. Collapsing those two cases is precisely what made a broken collector render as a healthy machine before the fix — see §5.
- ✅ **One clock per render pass.** `cli.py`'s `render` subcommand computes `now` once and threads it through every machine's staleness check, so no machine is judged against a different instant than its neighbors.

### Gaps & Risks
- ⚠️ **The README's architecture section describes a materially larger system than what runs.** It lists CPU/load average, thermals/fan/battery, top-process tracking, log-volume, network throughput, and disk SMART health as collected metric domains. None of these exist in `collectors/linux.py` or `collectors/macos.py` — the only two metrics are `disk_root_pct` and `mem_used_pct`. This is not a safety gap (nothing downstream assumes data that isn't there), but it is a documentation-vs-code gap a reader has no way to detect without reading the collector source.
- ⚠️ **`reboot_required` is a fact the rules layer checks but no collector can ever set true.** Both `linux.py` and `macos.py` write `facts["reboot_required"] = "false"` unconditionally, with an identical comment ("refined in a later step / task 2b if desired"). `rules.evaluate()`'s `reboot_required` flag is therefore permanently dead code in production — it is exercised only by hand-constructed test fixtures, never by a real collection.
- ⚠️ **Single-point-of-failure aggregation.** `mambakkam` is both a collector and the sole aggregator; if it is down, no machine's snapshot is merged or rendered, and no external alert exists to say so (explicitly out of scope for v1, but worth stating plainly since the dashboard itself would go stale and silent along with the machine hosting it).

## 2. Code Quality

### Strengths
- ✅ **`_write_atomic` in `cli.py` is a real, motivated correctness fix, not defensive boilerplate.** The docstring names the exact race it closes: `collect` and `sync` both fire on `RunAtLoad=true` at boot/login, so a plain `open(path, "w")` could let a concurrent `rsync` grab a truncated spool file. `tempfile.mkstemp` + `fsync` + `os.replace` in the same directory closes it properly (same filesystem, atomic rename).
- ✅ **Facts are omitted, never zeroed, on probe failure** — both collectors follow the same rule as metrics: a failed `apt`/`softwareupdate`/`systemctl`/`launchctl` probe leaves the corresponding fact absent from `Snapshot.facts` rather than writing a reassuring default, so `rules.evaluate()` sees "unknown" instead of "healthy."
- ✅ **The disk-trend projection (`rules._disk_trend`) is genuinely careful numerics for a small function.** It fits a least-squares slope against real elapsed wall-clock time (not sample index, so a sleeping machine's gap doesn't compress into a fake steep climb), requires both a minimum point count (6) and a minimum time span (6h) before trusting the slope, and floors the ETA rather than rounding — all three guard against the specific way a short noisy history could produce a false-confident projection.
- ✅ **`macos.py`'s Apple crash-respawn filter is a well-reasoned, well-commented judgment call**: a `com.apple.*` agent killed by a signal is respawn noise (cites `com.apple.BiomeAgent` crashing every few minutes as the concrete example); a non-Apple agent killed by a signal, or *any* agent with a clean non-zero exit, is still surfaced. This is exactly the kind of platform-specific noise-filtering that is easy to get either too loose (misses real Apple failures) or too tight (drowns the operator); the boundary drawn here is defensible and tested (`test_macos_collector.py`).

### Gaps & Risks
- ⚠️ **No lint/type gate enforced in CI**, despite `ruff` being declared as a dev dependency and the implementation plan (`docs/superpowers/plans/2026-08-29-local_watch.md`) stating "Run `ruff`/`pytest` green before each commit" as a stated discipline. `.github/workflows/ci.yml` runs `pytest -q` only — `ruff check` never executes automatically, so the discipline depends entirely on the one developer remembering to run it locally.
- ⚠️ **`Store` has no WAL mode, no `check_same_thread=False`, and commits on every write** (`store.py:append` — `self.db.commit()` per call). This is a non-issue at the current single-writer-per-process cadence (the staggered 20-minute timers in `deploy/README.md` ensure `ingest`/`render` never overlaps another process touching the same file), but it is an undocumented assumption rather than an enforced one — nothing in the code would catch a future change (e.g., a manual re-render while the timer also fires) that violated it.

## 3. Test Coverage

### Strengths
- ✅ **The fail-open class has direct, named regression tests, not incidental coverage.** `test_rules_failopen.py`'s own module docstring states the thesis precisely: "A machine must not read as healthy just because we stopped hearing from it, or because its collector broke... Both are worse than a threshold breach." Its 9 tests cover degraded-collector flagging, message content, the no-false-positive case, the exact `0.0%`-vs-absent regression ("The old code reported 0.0% and stayed silent; now the absence must be loud"), stale-snapshot severity, age-label content, unparseable-timestamp handling, and the no-clock-supplied case. `test_collector_degradation.py` (16 tests) exercises the same class at the collector level for both OSes.
- ✅ **The XSS fix has a named attack payload as its test fixture.** `test_report_escaping.py` uses `PAYLOAD = "</pre><script>alert(1)</script>"` — a payload chosen to specifically defeat naive escaping that only handles `<script>` tags in isolation — across six tests covering LLM recommendation text, flag messages (which flow from raw `systemctl` output), machine name, OS name, and metric name/unit. A sixth test (`test_escaping_preserves_the_readable_text`) confirms escaping doesn't mangle legitimate text (`&` becomes `&amp;` but stays readable) — guarding against an overcorrection that would make the dashboard unreadable.
- ✅ **The deploy-gap fix is tested against the actual artifact that broke, not a re-implementation of the bug.** `test_packaging.py` reads `pyproject.toml` directly via `tomllib` and asserts the console script is declared, importable, and callable; that a build backend is pinned; that packages are explicit; and — the specific historical bug — that `wegofwd-llm[anthropic]` (not bare `wegofwd-llm`) is the declared dependency, with a docstring explaining exactly why the extra is load-bearing (`_default_provider()` requires the anthropic SDK, and its absence causes recommendations to *silently* degrade to fallback text with no error surfaced to CI).
- ✅ **The self-sync bug is tested end-to-end against the real shell script, not a Python re-implementation of its logic.** `test_sync_script.py` invokes `deploy/sync-to-aggregator.sh` as a subprocess with a controlled environment, using a stub `rsync` on `PATH` to assert what would actually have been sent, covering: FQDN self-match, bare-hostname self-match, empty-remote handling, missing-snapshot (non-error) exit, a genuine remote host *not* being mistaken for self, and the exact destination path `rsync` receives.

### Gaps & Risks
- ⚠️ **Context claimed ~145 test functions; the measured count is 130** (`grep -c '^def test_' tests/*.py`, corroborated by an actual `pytest -q` run reporting `130 passed`). Not a red flag in itself — no test was found to assert something false — but it is a reminder to count rather than trust a remembered figure, consistent with this suite's own `verify-from-repos` practice.
- ⚠️ **No test exercises the real `agent._default_provider()` path end-to-end** (reading the key file, building the `anthropic` provider, calling `generate()`) — reasonably so, since it needs a live key and network, but it means the `claude-sonnet-4-6` pin (chosen specifically because `wegofwd-llm` 0.2.0 always sends `temperature` and current-generation models reject it) is verified only by the comment and by the fact that recommendations are reported as actually working in production, not by any test that would catch a regression if `wegofwd-llm` changed its `generate()` signature again.
- ⚠️ **No property/fuzz test on the `df`/`free`/`launchctl`/`vm_stat` parsers.** Each parser is exercised only against fixed fixture files (`fixtures/*.txt`) and a handful of hand-crafted malformed strings. These parse locally-produced, not attacker-controlled, text, so the risk is lower than atri-sangam's NMEA-over-serial case, but a malformed `df` line from an unusual filesystem type or locale is exactly the kind of input a fuzz pass would catch before a real machine does.

## 4. Documentation

### Strengths
- ✅ **The deploy runbook is exceptional for a personal-scale project.** `deploy/README.md` and the two `INSTALL-{linux,macos}.md` guides give exact verification commands at every step (`.venv/bin/local_watch --help`, "Expected: a usage line listing `{collect,ingest,render}`. If you instead get 'No such file or directory', the install failed — re-read the `pip` output. Do not continue.") — this is the kind of defensive, assume-nothing runbook writing that would have caught the deploy-gap bug (§5) before it reached production, had it existed at the time.
- ✅ **The read-only invariant is documented in a way an operator can independently verify**, not just asserted: `deploy/README.md` lists the exact commands every unit runs and tells the reader to `grep` the two collector files for `read(` to confirm no probe passes a mutating flag.
- ✅ **In-code comments carry real incident history as rationale**, not just what the code does: `pyproject.toml`'s dependency comment explains the `[anthropic]` extra requirement by naming the exact failure it once caused; `agent.py`'s `_default_provider` comment explains the `claude-sonnet-4-6` pin by naming the `temperature` rejection; `cli.py`'s `_write_atomic` docstring names the exact race (`RunAtLoad=true` on both units) it closes.

### Gaps & Risks
- ⚠️ **The README's own status line is stale relative to the deploy this review measures.** It reads "**Status:** v1 implemented and merged to `main`. ... Not yet running on the fleet — the units are inert until an operator enables them," and the closing "Getting started" section says "_TBD once implemented._" Both were true at merge time (2026-08-29) but are false as of the 2026-08-31 three-machine live deploy — the README was never updated after the fleet actually went live, so a new reader is told the opposite of the current state.
- ⚠️ **The README's metric-domain list oversells the collectors by roughly 5x**, listing CPU/load average, thermals/fan/battery, top-process tracking, log volume, and network throughput alongside the two metrics (`disk_root_pct`, `mem_used_pct`) that actually exist. Unlike atri-sangam's roadmap convention (struck-through or explicitly labelled "deferred"), nothing here marks these as unimplemented — a reader has to cross-check the collector source to learn the real scope.
- ⚠️ **A stale/contradictory comment in `.gitignore`** claims the repo's internal SDD docs "stay local if this ever mirrors to a public surface (**it won't; private repo**)" — but the repo is confirmed **public** on GitHub, and the README's own Security & Privacy section says so explicitly ("The source repository is public, but it holds only code"). Harmless (the SDD docs under `docs/superpowers/` are in fact committed and public), but the comment is simply wrong and reads as a leftover from before the repo's visibility was set.

## 5. Security & Safety — the incident history

This is the section this review weighs most heavily, because `local_watch`'s history since first merge is dominated by four production incidents rather than by static code-reading findings. Each is verified fixed at `13e387e`.

### 5.1 Fail-open, three ways — ✅ FIXED (PR #1, `c151974`)
**The finding.** Before the fix, a broken collector, a probe that timed out, and a machine that had stopped reporting entirely all rendered the same as a healthy machine — the dashboard's job is to surface exactly this class of failure, and it did the opposite. The root cause was collapsing "probe never ran" and "probe ran and returned nothing" into the same empty value, which then flowed into rules as a false `0%` reading rather than an absence.
**The fix.** `collectors/base.py:probe()` now returns `None` (never ran) vs `""` (ran, empty) as distinct signals; both collectors' `metric()`/`read()` helpers append to a `probes_failed` fact list instead of emitting a default; `rules.evaluate()` raises a `crit` `collector_degraded` flag naming the failed probes, and a `stale` `crit` flag for any snapshot older than `STALE_AFTER_MIN` (60 minutes — three missed 20-minute collection cycles).
**Evidence it worked.** `test_rules_failopen.py` (9 tests) and `test_collector_degradation.py` (16 tests) assert each of the three paths directly, including the specific regression ("missing metrics do not read as zero percent used").

### 5.2 XSS via LLM output and other untrusted strings — ✅ FIXED (same PR #1)
**The finding.** `render_dashboard`'s only source of text is: LLM-generated recommendations, flag messages (which include raw `systemctl`/`launchctl` output), and machine/OS/metric names (hostname- and probe-derived). All of it was documented as being interpolated raw at the time.
**The fix.** Every user-facing string in `report.py` passes through `html.escape()` uniformly — recommendations, flag messages, machine names, OS names, metric names and units.
**Evidence it worked.** `test_report_escaping.py` (6 tests) uses the concrete payload `</pre><script>alert(1)</script>` (chosen to close a script tag opened inside a `<pre>` block, not just a naive raw `<script>` tag) across every one of those five surfaces, plus a readability-preservation test.

### 5.3 The deploy gap — `pip install -e .` never worked — ✅ FIXED (PR #2, `2a31476`)
**The finding.** `pyproject.toml` originally declared no `[build-system]` and no console script. Without an explicit build backend, setuptools' flat-layout auto-discovery refuses to build the repo at all (it sees `local_watch/`, `tests/`, `fixtures/`, `deploy/`, `docs/` as competing top-level packages), and without a `[project.scripts]` entry, `.venv/bin/local_watch` — the binary every deploy unit and `mambakkam-ingest-render.sh` invokes by absolute path — never existed. The entire runbook was unreachable from a cold clone.
**The fix.** `[build-system]` pinned to `setuptools>=68` with `setuptools.build_meta`; `local_watch = "local_watch.cli:main"` declared under `[project.scripts]`; `[tool.setuptools] packages` listed explicitly.
**Evidence it worked.** `test_packaging.py` reads the TOML directly and asserts the console script exists, is importable and callable, that a build backend is pinned, and that packages are explicit — plus the specific historical variant, that `wegofwd-llm[anthropic]` (not bare `wegofwd-llm`) is declared, since the missing extra silently degraded every deployed recommendation to fallback text with no visible error (fixed alongside in PR #4, `80fb129`).

### 5.4 First deploy — the aggregator rsynced to itself — ✅ FIXED (PR #3, `fc0a667`)
**The finding.** `env.example` shipped with `LOCAL_WATCH_REMOTE` pre-filled to the aggregator's own address and no guard against a machine syncing to itself. The failure surfaced as `ssh`'s "Too many authentication failures" — an error that sends an operator investigating SSH keys, nowhere near the actual mistake (a role misconfiguration).
**The fix.** `sync-to-aggregator.sh` now normalizes and compares the local hostname against `LOCAL_WATCH_REMOTE`'s host before attempting any sync, refusing with a message naming the actual problem ("This machine is the aggregator: it is the destination, so it has nothing to sync to") and pointing at the exact install-guide step. `env.example` now ships `LOCAL_WATCH_REMOTE` commented out by default with an explicit warning about which role should uncomment it.
**Evidence it worked.** `test_sync_script.py` (8 tests) runs the actual shell script as a subprocess with a stub `rsync`, covering FQDN and bare-hostname self-match, the specific "names the actual problem, not the ssh symptom" assertion, empty-remote handling, missing-snapshot as a non-error, and confirming a genuine remote host is not mistaken for self.

### Strengths beyond the incident history
- ✅ **No credentials collected, ever.** The only secret in the pipeline is the local Anthropic API key file (`~/.config/wegofwd/anthropic_api_key`), read once per render and never logged, echoed, or included in any Snapshot/Flag/report.
- ✅ **Tailscale-only transport.** `sync-to-aggregator.sh` and the install guides are explicit that `LOCAL_WATCH_REMOTE` must be a MagicDNS tailnet name, never a public or LAN address — the sync path never crosses the open internet.

### Remaining gaps
- ⚠️ **No transport-layer defense-in-depth beyond Tailscale itself** — reasonable for a personal 3-machine fleet, but worth naming: if Tailscale ACLs were ever misconfigured, nothing in `local_watch` itself would catch an unauthorized `rsync` push into the ingest directory (the ingest path trusts any file that lands there, distinguishing only good-JSON from bad-JSON, not provenance).

## 6. Scalability & Operations

### Strengths
- ✅ **The staggered timer cadence is designed around the staleness threshold, not arbitrary.** Collect at +2min/20min, sync at +7min/20min, ingest+render at +12min/20min — `deploy/README.md` states outright that this cadence is load-bearing because `STALE_AFTER_MIN=60` assumes three uninterrupted 20-minute cycles; slowing collection materially would start producing false staleness flags. Naming the coupling explicitly is what keeps it from becoming a landmine for a future "let's collect less often to save resources" change.
- ✅ **Ingest is deliberately non-atomic-per-file and idempotent** — `mambakkam-ingest-render.sh`'s comment explains that ingested snapshot files are never deleted (each machine overwrites its own `<hostname>.json`, so the directory stays bounded, and re-ingesting is safe because the store keys on `machine, ts`) and that a missing ingest directory renders anyway from existing history rather than going blank.
- ✅ **A single bad snapshot file cannot sink a fleet-wide render.** `cli.py`'s `ingest` subcommand catches `(OSError, ValueError, KeyError, TypeError)` per file and skips with a stderr message rather than aborting the whole batch — directly motivated by the observation that `mambakkam-ingest-render.sh` passes every machine's file in one call.

### Gaps & Risks
- ⚠️ **The aggregator being both the destination and a collector is efficient but a real SPOF** (see §1) — acceptable for a personal fleet where the operator is also the one who'd notice `mambakkam` being down, but worth stating as a scaling ceiling before any fourth machine or any non-technical stakeholder depends on this dashboard.
- ⚠️ **No automated alerting on the staleness/degraded states themselves** — the dashboard will correctly show a machine as `stale` or `collector_degraded`, but nothing pushes that fact anywhere; an operator has to open the dashboard to learn their monitor stopped monitoring. Explicitly out of v1 scope per the README, and reasonable at this scale, but it is the natural next capability gap once the safety floor (this review's main subject) is trusted.

## Priority Actions

In priority order:

1. ⚠️ **Reconcile the README with the shipped collectors** — either implement the promised metric domains (CPU/load, thermals, battery, network, top-process, log volume, SMART) or strike them from the architecture section and metric-domain list the way atri-sangam's roadmap marks deferred items. Right now a reader has no signal that ~80% of the described scope doesn't exist yet.
2. ⚠️ **Update the README's status line and "Getting started" section** to reflect the live 2026-08-31 three-machine deploy — both currently read as if the units are still inert.
3. ⚠️ **Add `ruff check` to CI** alongside `pytest -q`. The dev dependency and the implementation plan's own stated discipline ("Run `ruff`/`pytest` green before each commit") are not backed by an automated gate — the same finding raised for atri-sangam and dronePrjs in this suite.
4. ⚠️ **Either wire up `reboot_required` detection or remove the dead fact/rule pair.** Both collectors hardcode it `false`; the corresponding `rules.evaluate()` branch and its test coverage exercise a code path that can never fire on a real machine.
5. ⚠️ **Fix the stale `.gitignore` comment** claiming the repo won't mirror to a public surface — it already is public, per the README's own Security & Privacy section and confirmed repo visibility.

---

*First review (v1.0), against `main` at `13e387e`. Verified by a local `pytest -q` run (130 passed) and a full read of `local_watch/`, `local_watch/collectors/`, `tests/`, `deploy/`, `pyproject.toml`, `.github/workflows/ci.yml`, `README.md`, and `.gitignore`, all read from `origin/main` (working tree confirmed identical). Cost-of-time-and-money analysis is maintained privately.*
