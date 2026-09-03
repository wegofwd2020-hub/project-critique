# local_watch — Good Practices, Bad Practices & How to Improve

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

**Document type:** Engineering practices analysis
**Scope:** Python 3.11+ read-only personal-fleet monitor — collectors, rules engine, LLM agent seam, report renderer, storage, deploy scripts.
**Period:** 2026-09-03 (v1.0 — first review, against `main` at `13e387e`)
**Related:** [local-watch-critique.md](local-watch-critique.md) · [local-watch-development-pattern.md](local-watch-development-pattern.md)
**Rating key:** ✅ Good practice · ⚠️ Bad practice · ❌ Critical issue · 🔧 How to improve

---

## Table of Contents

1. Architecture Practices
2. Fail-Open / Safety-Floor Practices
3. Security & Robustness Practices
4. Code Quality Practices
5. Testing Practices
6. Documentation Practices
7. Operational / Deployability Practices

---

## 1. Architecture Practices

### ✅ Good — One-way pipeline, no backward edges
`collectors → Snapshot → Store → rules.evaluate() → agent.recommend() → report.py` never reverses: rules never import the agent, the agent never touches the store, collectors know nothing about any downstream layer. This is what makes each layer testable and reasoned about in isolation (`test_rules.py` never needs a fake LLM; `test_agent.py` never needs a fake collector).

### ✅ Good — The LLM's blast radius is "a string in a dict"
`agent.recommend()`'s entire interface to the rest of the system is `dict[str, str]`. There is no code path in `report.py` or anywhere downstream that treats that string as anything but display text to escape — the LLM cannot be coerced into producing markup that isn't neutralized, a flag that isn't real, or a write that doesn't go through `report.py`'s own escaping.

### ⚠️ Bad — The README describes an architecture the code doesn't implement
The architecture diagram and "Collectors" section list CPU/load, thermals, battery, network, top-process, log-volume, and SMART metrics; the actual collectors emit two metrics and four facts. See the critique's §1 and §4 for the full gap.
🔧 **How to improve:** either implement the gap or apply atri-sangam's convention — strike through undelivered items in the README and label them "roadmap," so the diagram matches the running code at a glance.

## 2. Fail-Open / Safety-Floor Practices

### ✅ Good — `None` means "unknown," never a default
`collectors/base.py:probe()` returns `None` for a probe that never ran and `""` for one that ran and legitimately produced nothing; every collector's `metric()`/`read()` helpers propagate that distinction into a `probes_failed` fact rather than silently defaulting. This single decision is the fix for what was, before it, the project's most serious bug (§5.1 of the critique).

### ✅ Good — Staleness is judged against one shared clock per render
`cli.py`'s `render` subcommand computes `now` once and threads it through every machine's evaluation, so no two machines in the same render are judged against different instants — a small thing that avoids a whole class of "why does machine B look staler than machine A when they synced at the same time" confusion.

### ✅ Good — A failed probe is named in the flag message, not just flagged
`rules.evaluate()`'s `collector_degraded` flag reads `f"Collector probes failed: {probes_failed} — those readings are missing, not zero"` — the operator learns *which* probe broke and is told explicitly not to read the absence as a healthy zero, in the same sentence.

### ⚠️ Bad — `reboot_required` is a fact no collector can ever set true
Both `linux.py` and `macos.py` hardcode `facts["reboot_required"] = "false"` with an identical "refined in a later step" comment. The corresponding rule in `rules.evaluate()` is therefore dead in production, exercised only by hand-built test fixtures.
🔧 **How to improve:** implement the real check (`/var/run/reboot-required` on Debian/Mint-family Linux; comparing `sw_vers` against `softwareupdate --list`'s advertised OS updates on macOS, or checking for a pending-restart marker) or remove the fact and its rule branch until it is.

## 3. Security & Robustness Practices

### ✅ Good — Every rendered string is escaped uniformly, on the stated theory that all of it is untrusted
`report.py`'s module comment: "Every value here is attacker-influenced: `recs` is LLM output, flag messages carry service names, and machine/OS come from hostnames. Escape all of it — the only markup in a card is markup written above." `test_report_escaping.py` verifies this against a real payload (`</pre><script>alert(1)</script>`) across five distinct fields, not just the obvious one (LLM recommendations).

### ✅ Good — Read-only is mechanically checkable, not just claimed
`deploy/README.md` lists the exact probe commands every collector runs and tells the operator to `grep` the collector files for `read(` to confirm none passes a mutating flag — turning a security claim into something a skeptical operator can verify in thirty seconds without reading Python.

### ✅ Good — Atomic writes close a real concurrent-write race
`cli.py:_write_atomic` uses `tempfile.mkstemp` in the same directory + `fsync` + `os.replace`, motivated by a specific, named race: `collect` and `sync` both fire on `RunAtLoad=true` at boot/login, and a plain truncate-in-place `open(path, "w")` could let a concurrent `rsync` ship a zero-byte snapshot.

### ⚠️ Bad — The self-sync guard was originally duplicated per-platform and drifted
The guard now lives in one shared `sync-to-aggregator.sh` invoked by both the systemd unit and the launchd plist — but the historical bug (the aggregator syncing to itself) happened precisely because the check was not consistently present across both platform configs beforehand.
🔧 **How to improve:** already done — flagging this as a practice to *keep*: any future cross-platform behavioral guard should default to a shared script from day one, not per-platform unit/plist logic.

### ⚠️ Bad — No property/fuzz testing on locally-produced parser input
`df`, `free`, `vm_stat`, and `launchctl list` output is parsed only against fixed fixtures and a few hand-crafted malformed strings. Lower risk than an attacker-facing parser (this is local system output, not network input), but a locale change, an unusual filesystem type, or a future macOS `vm_stat` format change could still produce unparsed garbage silently.
🔧 **How to improve:** a Hypothesis-style property test asserting `_disk_root_pct`/`_mem_used_pct`/`_vm_stat_pages` always either parse cleanly or return `None` (never raise, never return nonsense) would catch a format-drift regression before a real machine does.

## 4. Code Quality Practices

### ✅ Good — Comments carry incident history as load-bearing rationale, not decoration
`pyproject.toml`'s dependency comment states the exact failure the `[anthropic]` extra prevents; `agent.py`'s `_default_provider` comment names the exact model/parameter incompatibility that pinned the model version; `cli.py`'s `_write_atomic` docstring names the exact race it closes. A future engineer changing any of these lines has the "why" right there, not in a separate changelog they'd have to go find.

### ✅ Good — Facts are omitted, never zeroed, symmetric with the metric convention
Both collectors follow one rule for both metrics and facts: on probe failure, omit the value entirely rather than writing a default that would read as healthy. Applying the same discipline to both data shapes (numeric metrics and string facts) rather than only to the one that was originally buggy is a sign the fix was understood as a principle, not patched locally.

### ✅ Good — Trend projection excludes metrics whose noise profile would make it misleading
`rules.py` explicitly does not apply `_disk_trend`'s least-squares projection to memory, with the reasoning stated inline (memory sawtooths by design; a short-window fit would be noise dressed as a warning). Resisting "we have this machinery, apply it everywhere" is itself worth noting as a positive discipline.

### ⚠️ Bad — `ruff` is declared but never enforced
`pyproject.toml`'s `dev` extra includes `ruff`, and the implementation plan states "Run `ruff`/`pytest` green before each commit" as a discipline — but `.github/workflows/ci.yml` runs `pytest -q` only. The discipline is real but entirely manual, and CI would not catch a regression against it.
🔧 **How to improve:** add a `ruff check .` step to `ci.yml` — this is a five-line addition, not a redesign, and it converts a stated intention into an enforced one.

## 5. Testing Practices

### ✅ Good — Every production incident has a test named after the incident, not just the current behavior
`test_missing_metrics_do_not_read_as_zero_percent_used`, `test_self_sync_message_explains_the_actual_problem`, `test_wegofwd_llm_is_requested_with_the_anthropic_extra`, `test_fallback_output_is_labelled_as_rules_only` — each of these test names encodes the historical failure mode, so a future contributor reading the test file learns the "why" of the assertion without needing separate documentation.

### ✅ Good — The shell-script fixes are tested as subprocesses of the real script, not reimplemented in Python
`test_sync_script.py` invokes `deploy/sync-to-aggregator.sh` directly via `subprocess.run`, with a stub `rsync` on `PATH` recording its arguments. This tests the artifact that actually runs in production (bash, not a Python model of the bash), closing the gap where a Python-side re-implementation of the guard could pass while the real script still had the bug.

### ✅ Good — Packaging is tested against the real `pyproject.toml`, not asserted separately
`test_packaging.py` parses the actual `pyproject.toml` with `tomllib` and asserts the console script, build backend, package list, and dependency extra directly from it — a regression in any of these is caught by reading the same file that `pip install` reads, not by a parallel assertion that could drift from it.

### ⚠️ Bad — The measured test count doesn't match the count carried into this review
This review's brief cited "~145 `def test_`" as a starting figure; a direct count and a `pytest -q` run both confirm **130** passing tests. Not evidence of anything false being claimed — just a reminder that a remembered count should be re-measured, not carried forward, consistent with this suite's own practice of measuring against `origin/main` rather than trusting an earlier snapshot.
🔧 **How to improve:** no code change needed — a process note for future reviews of this project: `pytest -q --collect-only -q | tail -1` gives the authoritative count in one command.

### ⚠️ Bad — The real LLM call path has no test coverage at all
`agent._default_provider()` (reading the key file, building the `anthropic` provider, calling `generate()`) is only reachable in production, never in CI — reasonably so, since it needs a live key, but it means the `claude-sonnet-4-6` pin (chosen specifically to dodge a `temperature`-rejection error on newer models) has no regression protection if `wegofwd-llm`'s `generate()` signature changes again.
🔧 **How to improve:** a test using a fake `anthropic`-shaped SDK object (rather than a live key) could at least assert `_default_provider()` builds its request without passing `temperature`, closing the gap between "works because I tried it once on the real deploy" and "verified in CI."

## 6. Documentation Practices

### ✅ Good — The deploy runbook tells the reader what to expect and what failure looks like, at every step
`INSTALL-linux.md`: "Expected: a usage line listing `{collect,ingest,render}`. If you instead get 'No such file or directory', the install failed — re-read the `pip` output. Do not continue; every later step depends on this binary existing." This is the exact defensive-writing pattern that would have caught the deploy-gap bug before it reached production, applied consistently through both platform guides.

### ✅ Good — The security claim is written to be independently verifiable, not just asserted
"Grep those two files for `read(` to confirm no probe passes a mutating flag" in `deploy/README.md` turns "trust me, it's read-only" into "here's how to check yourself in ten seconds."

### ⚠️ Bad — The README's status line and "Getting started" section are stale post-deploy
"Not yet running on the fleet" and "_TBD once implemented_" are both false as of the 2026-08-31 three-machine live deploy this review measures — the README was written before deploy and never updated after.
🔧 **How to improve:** a one-line status update ("Live since 2026-08-31 on 3 machines") plus removing or filling in the "Getting started" TBD would close this in minutes.

### ⚠️ Bad — A stale, factually wrong comment in `.gitignore`
"internal SDD docs stay local if this ever mirrors to a public surface (**it won't; private repo**)" — the repo is confirmed public, and the README's own Security & Privacy section says so. The docs the comment refers to (`docs/superpowers/`) are in fact committed and public.
🔧 **How to improve:** delete or correct the comment; it costs nothing and currently contradicts the README two files away.

## 7. Operational / Deployability Practices

### ✅ Good — The timer cadence's dependency on the staleness threshold is stated explicitly, not left implicit
`deploy/README.md`'s Timing table is followed directly by: "This cadence is load-bearing. The rules layer flags a snapshot as `stale` after 60 minutes — three missed collection runs — so slowing collect much past 20 minutes will start producing false staleness." A future operator tuning the timer for battery life or resource use is told exactly what breaks if they go too far, rather than discovering it as a mystery flag later.

### ✅ Good — A degraded or missing sync doesn't blank the dashboard
`mambakkam-ingest-render.sh` renders from existing history even when no new snapshots have arrived, explicitly to avoid "going blank the moment a sync breaks" — the dashboard degrades to "showing stale data with a staleness flag," which is the correct failure mode for a monitor, rather than "showing nothing."

### ✅ Good — One bad snapshot file cannot sink the whole fleet's render
`cli.py`'s `ingest` subcommand catches per-file errors and continues, printing to stderr rather than aborting — directly motivated by `mambakkam-ingest-render.sh` passing every machine's file in a single call.

### ⚠️ Bad — The aggregator is a single point of failure with no external alerting
`mambakkam` is both a collector and the sole aggregator; if it goes down, no snapshot from any machine is merged or rendered, and nothing pushes a notification anywhere — the operator only learns by opening a dashboard that, by definition, also isn't updating.
🔧 **How to improve:** out of v1 scope reasonably, but worth a stated roadmap line (mirroring atri-sangam's explicit roadmap convention) rather than leaving it undiscussed: e.g. a simple external heartbeat (a cron job on a fourth, independent surface checking the dashboard file's mtime) would close the "who watches the watcher" gap cheaply.

---

*First review (v1.0). All findings verified against `main` at `13e387e`, a local `pytest -q` run (130 passed), and a read of every file referenced above via `git show origin/main:<path>` (working tree confirmed identical to `origin/main`). Cost analysis maintained privately.*
