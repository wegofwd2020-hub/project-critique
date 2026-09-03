# local_watch — Scoping, Design, Architecture & Development Pattern

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

**Document type:** Development pattern analysis
**Scope:** Design & scoping methodology of a read-only personal-fleet monitor with LLM-assisted recommendations
**Period:** 37 commits across 5 merged PRs, 2026-08-29 → 2026-08-31 (~45 hours of calendar span, first merge to full 3-machine live deploy)
**Author:** WeGoFwd2020 / Claude (Anthropic)
**Related:** [local-watch-critique.md](local-watch-critique.md) · [local-watch-practices.md](local-watch-practices.md)
**Note:** Unlike some products in this suite (atri-sangam's v1.0 pass, which had no git history), `local_watch` has full commit history from scaffold to live deploy — this document reads velocity directly off `git log`, not off inference from code density.

---

## Table of Contents

1. [The Problem Being Solved](#1-the-problem-being-solved)
2. [Scoping Pattern](#2-scoping-pattern)
3. [Design Pattern](#3-design-pattern)
4. [Architecture Pattern](#4-architecture-pattern)
5. [Development Pattern — Contact With Reality](#5-development-pattern--contact-with-reality)
6. [Key Decisions and Their Rationale](#6-key-decisions-and-their-rationale)
7. [What This Pattern Teaches](#7-what-this-pattern-teaches)

---

## 1. The Problem Being Solved

A personal fleet of three machines (a Linux desktop that doubles as home server, a second Linux box, a MacBook) drifts out of shape in ways that are individually cheap to notice by hand but collectively easy to forget to check: a disk creeping toward full, pending security updates piling up, a `systemd` unit or `launchd` agent that died silently, a machine that's been asking for a reboot for weeks. None of this needs a fleet-management platform. It needs a small, boring watcher that runs unattended, tells the truth about what it can and can't see, and — the one genuinely novel piece — turns raw thresholds into "here's what to actually do about it" using an LLM that is explicitly forbidden from doing anything except writing that sentence.

The design thesis, stated in the README's Principles section, is a hard split between two kinds of intelligence: **deterministic where it matters** (collection and threshold detection: plain, fast, offline code) and **smart where it helps** (an LLM that only reads the aggregate and writes recommendations — "it is never in the control path"). This split is not a nice-to-have; it is the thing that makes the rest of the design legible: safety comes entirely from the deterministic half, and everything the LLM half can do is bounded to producing text that flows through the same escaping path as every other untrusted string in the system.

The honest complication, visible only by reading the actual collectors rather than the README: **the metric domain that shipped is far narrower than the metric domain that was scoped.** The README's "Compute / Storage / Thermals / Processes / Updates / Network" taxonomy describes a genuinely fleet-grade monitor; what runs is disk-percentage, memory-percentage, pending-updates count, and failed-unit names. This is not dishonesty in the code — the collectors do exactly what they claim, and the rules layer never assumes data it doesn't have — but it is a scoping decision the README does not surface as a decision. Contrast atri-sangam's roadmap, which strikes through delivered items and explicitly labels the rest "deferred": `local_watch`'s README reads in the present tense about a scope it has not reached.

## 2. Scoping Pattern

### 2.1 The Safety Floor Is the First Design Decision, Stated as a Constraint

The README's Principles section leads with "Read-only in v1. No writes, no killing processes, no config changes, no package installs" and calls it "the safety floor the whole design rests on" — before describing a single collector or metric. This ordering matters: every subsequent architectural choice (LLM-out-of-control-path, escaping everything, the collectors' probe list being entirely read commands) is a consequence of that one sentence, not an independent good idea layered on top. The roadmap makes the same point structurally: v2's "act with approval" is explicitly gated on "trusting v1's recommendations" first, and v3's "autonomous bounded actions" is hedged with "maybe" and "everything risky still escalates." Each version is scoped to require the previous version's trust to be earned, not assumed.

### 2.2 Scope Was Drawn Wider in the README Than in the Code — and the Gap Was Never Closed

The plan document (`docs/superpowers/plans/2026-08-29-local_watch.md`) and the README both describe a broad metric taxonomy up front. What actually got built across the 10-task implementation plan settled on two metrics (`disk_root_pct`, `mem_used_pct`) and four facts. This looks, from the commit history, like ordinary and defensible scope-narrowing during implementation — the kind of thing that happens on every project. What is unusual is that nothing in the README was ever walked back to match: the architecture diagram, the metric-domain bullet list, and the "Collectors (read-only, per-OS)" section all still describe the wider scope in the present tense, as if it shipped. This is the inverse of atri-sangam's subtractive-scoping discipline (§2.3 of that project's development-pattern doc), where every deferred item was named and left honestly absent from the code *and* struck through or labeled in the docs. Here the code is honest (it does exactly what it does, nothing more); the README is the part that didn't get the memo.

### 2.3 The Deploy Gap Reveals an Un-Scoped Dependency: "Merged" Was Not the Same As "Runnable"

The first PR (`7943bb5`→`c151974`, the initial 10-task implementation plan through the first hardening PR) treated "all tests pass" as the finish line, which is a reasonable definition for a library. But `local_watch` was scoped from the start as a *deployed daemon*, and nothing in that first plan's definition of done included "can a fresh clone actually produce the executable every deploy unit calls." That gap — no `[build-system]`, no console script — was invisible to `pytest` (which runs inside an already-editable-installed environment) and only surfaced when an operator tried to follow the runbook on a clean machine. PR #2 (`feat/close-deploy-gap`) closed it, and `test_packaging.py` now encodes "is this actually installable" as a first-class test assertion rather than an assumption. The lesson embedded in the commit sequence: for a product whose deliverable is a running daemon, not a library, "tests green" and "deployable" are two different definitions of done, and the second one has to be scoped and tested explicitly or it will be discovered by an operator instead of by CI.

## 3. Design Pattern

### 3.1 The None/Empty-String Distinction Is the Single Design Decision That Fail-Open Hinges On

`collectors/base.py:probe()`'s docstring states the design rule directly: "The None-vs-'' distinction matters: an empty stdout from a command that *did* run is a real answer... whereas a probe that never ran means 'unknown'. Collapsing both into '' is what made a broken collector render as a healthy machine." This is a small, almost invisible type-level decision (`str | None` instead of `str`) that turned out to be load-bearing for the entire safety-floor claim. Every collector's `read()`/`metric()` helper pair is built to propagate that distinction outward as a named `probes_failed` fact rather than as a missing key or a default value — the same pattern repeated identically in `linux.py` and `macos.py`.

### 3.2 Trend Projection Is Scoped to Metrics Whose Rate of Change Is Meaningful, Not to All Metrics Uniformly

`rules.py`'s comment on why memory is excluded from trend projection ("Memory is deliberately left out... it sawtooths by design (caches grow until something needs the pages), so a rising fit over any short window is noise dressed up as a warning") is a design decision that resisted the temptation to apply one projection mechanism uniformly across every numeric metric just because the machinery existed. Disk usage genuinely trends monotonically until something is deleted; memory usage does not. Applying `_disk_trend`'s least-squares slope to memory would have produced technically-correct-looking but semantically-false warnings on every machine's daily cache cycle.

### 3.3 Escape Everything, Uniformly, Because Everything Is Attacker-Influenced

`report.py`'s module-level comment states the design rule plainly: "Every value here is attacker-influenced: `recs` is LLM output, flag messages carry service names, and machine/OS come from hostnames. Escape all of it." The design choice is *uniform* escaping rather than case-by-case judgment about which fields are "probably safe" (machine names, say, since they come from `hostname` and not literally the internet) — a judgment call that the actual XSS incident (§5.2 of the critique) proved wrong once, when the same reasoning ("this field is probably safe") was applied selectively and one path was missed.

### 3.4 Fail-Loud Naming Instead of Fail-Loud Exceptions

Where atri-sangam's design pattern uses typed exceptions raised at construction (`__post_init__` validation), `local_watch` uses a different fail-loud idiom suited to a monitor rather than a library: failures are named as data (`Flag`, `probes_failed` string, `FALLBACK_NOTICE` text) that flows all the way to the dashboard, rather than raised as exceptions that would need a caller to catch them. This is the right idiom for a system whose job is to keep running and reporting even when parts of it are broken — an exception raised inside a collector would crash the collection cycle for the one machine that most needs its failure surfaced; a `Flag` describing the failure survives to the render step and shows up as `crit` on the dashboard instead.

## 4. Architecture Pattern

### 4.1 A Five-Stage Pipeline With No Backward Edges

```
┌─────────────┐  ┌──────────┐  ┌───────┐  ┌────────────┐  ┌────────┐
│ collectors/  │─▶│ Snapshot │─▶│ Store │─▶│ rules.py   │─▶│ agent  │
│ {linux,macos}│  │ (schema) │  │(SQLite)│  │ evaluate() │  │(LLM,   │
└─────────────┘  └──────────┘  └───────┘  └─────┬──────┘  │optional)│
                                                  │         └───┬────┘
                                                  ▼             ▼
                                            list[Flag]  ──▶ report.py
                                                          (HTML + MD,
                                                           escapes all)
```
Each arrow is a one-way data dependency: collectors never import `rules`; `rules.evaluate()` is a pure function of `(Snapshot, series, now)` with zero knowledge of the LLM; `agent.recommend()` takes flags and snapshots but never touches the store directly; `report.py` treats every string reaching it — LLM output included — as equally untrusted. This is the same fan-in-referee shape atri-sangam uses for its discrepancy engine, applied to a much smaller domain.

### 4.2 The CLI Is a Thin Three-Verb Shell Over the Pipeline

`cli.py`'s `main()` has exactly three subcommands — `collect`, `ingest`, `render` — each a few lines that call into `local_watch/{collectors,store,rules,agent,report}` and nothing else. This thinness is what makes `deploy/mambakkam-ingest-render.sh`'s "the two-command body" claim literally true, and it is what makes `test_cli.py` able to test the orchestration logic (atomic writes, per-file ingest error handling, one-clock-per-render) without needing a real collector or a real LLM key — every dependency the CLI has is either pure (`rules`, `report`) or already designed to degrade gracefully (`agent.recommend()` with `provider=None`).

### 4.3 The Deploy Layer Duplicates No Logic Between Platforms

`sync-to-aggregator.sh` is shared verbatim between the Linux systemd unit and the macOS launchd plist — its own header comment explains why: "the checks below used to be duplicated in a unit file and a plist XML string, which is how they drifted apart." This is a small but telling architectural correction made *after* the fact (visible in the commit history as part of the self-sync-guard PR): the original design had the self-sync guard logic living separately per platform, and the fix was not just "add the guard" but "stop duplicating the guard," closing off the drift mechanism itself rather than patching the one instance that broke.

### 4.4 The Store's Schema Is Two Columns Wide on Purpose

`Store` is a single SQLite table, `snapshots(machine, ts, json)`, primary-keyed on `(machine, ts)`. Rather than modeling metrics as first-class rows, the entire `Snapshot` is serialized as JSON and stored opaquely; `series()` deserializes every row it reads and filters client-side for the one metric requested. This is a deliberate trade of query efficiency for schema stability: adding a new metric to a collector requires no migration, because the store never had a column for any specific metric to begin with. At three machines and a 20-minute cadence, the cost of deserializing every row is invisible; the benefit (a collector can add a new `Metric` any day without touching `store.py`) is the kind of thing that pays for itself repeatedly at this scale.

## 5. Development Pattern — Contact With Reality

Unlike a purely code-read development-pattern analysis, `local_watch`'s git history gives a genuine before/after: 5 PRs, in order, each responding to a specific discovered failure rather than to a planned feature.

| PR | What broke | What the fix looked like |
|---|---|---|
| #1 `fix/fail-open-and-escaping` | Broken/dead/degraded machines rendered green; LLM output could inject markup | `None`-vs-`""` probe distinction, `probes_failed`/staleness flags, uniform `html.escape()` |
| #2 `feat/close-deploy-gap` | `pip install -e .` never produced a binary | `[build-system]` + `[project.scripts]` pinned, `test_packaging.py` added |
| #3 `fix/self-sync-guard` | Aggregator rsynced to itself, surfaced as a misleading ssh error | Hostname-comparison guard shared across both platforms' sync scripts |
| #4 `fix/llm-recommendations` | LLM recommendations silently never ran on the real deploy | `wegofwd-llm[anthropic]` extra declared; model pinned off `temperature`-rejecting `claude-sonnet-5` |
| #9 `feat/dashboard-presentation` | (not a bug) dashboard redesign — per-metric-kind rendering (meter/sparkline/stat/chip) | Presentational only |

The pattern across #1–#4 is consistent: **every one of them is a gap between "the code does what it was written to do" and "the code does what it needs to do to actually run unattended on real machines."** None of the four are logic bugs in the conventional sense (an off-by-one, a wrong comparison) — they are boundary failures: a type collapsing two meaningfully different signals into one (#1), a packaging step nobody exercised outside an already-set-up dev environment (#2), a default value that happened to equal a real machine's own identity (#3), a dependency declared without its required extra (#4). This is the profile of bugs that a design review, however careful, tends not to catch, because each one requires either a genuinely broken component (#1), a genuinely fresh clone (#2), a genuinely second machine (#3), or a genuinely real API key (#4) to surface — exactly the four things a fast, single-developer implementation pass is least likely to have all present simultaneously until deploy day. The discipline that matters here is not "avoid these bugs" (arguably unavoidable at this development speed) but "close every one of them with a test that would have caught it," which the commit history shows happening consistently — each fix PR ships alongside the specific regression test named in this document's critique §3.

The remaining test suite (`test_rules.py`, `test_rules_trend.py`, `test_report_dashboard.py`, `test_probe_timeouts.py`) grew across the same window covering the originally-planned functionality (thresholds, trend projection, dashboard rendering, slow-probe handling) — the "planned feature" tests and the "production incident" tests are interleaved in the same 37-commit history rather than segregated into a separate hardening phase, which suggests the fixes were folded into ongoing development rather than treated as a distinct post-mortem exercise.

## 6. Key Decisions and Their Rationale

### Decision 1: Split "deterministic where it matters, smart where it helps" as the top-level architectural axis

**Why:** The LLM is valuable for exactly one thing here — turning "disk_root_pct=93, trend=+2%/day" into "here's what's probably filling it and what to try first" — and dangerous for everything else a monitor could plausibly ask an LLM to do (deciding severity, deciding what to render, deciding what to do about it). Drawing the line at "read-only reasoning about text" rather than at a more permissive "reasoning that suggests actions the operator could still veto" removes an entire category of prompt-injection risk: even if a compromised or hallucinating LLM response tried to instruct something, nothing downstream interprets its text as anything other than a string to escape and display.
**Trade-off:** The LLM path adds real operational fragility that has nothing to do with prompt injection — a dependency pin (#4 above) silently degrading the entire recommendation layer without an error surfacing anywhere except a label in the rendered output.

### Decision 2: Prefer `None`/absence over sentinel values across every layer

**Why:** A `0.0%` disk reading and an unreadable disk reading are catastrophically different facts for an operator to receive, and the type system (`float | None`, absent dict keys, an empty `probes_failed` list vs. a populated one) is used consistently to keep those facts distinguishable all the way to the dashboard. This is the single decision that both caused the fail-open bug (before it was applied uniformly) and fixed it (once it was).
**Trade-off:** Every consumer of a `Snapshot` has to handle the `None`/absent case explicitly rather than getting a default to fall back on — visible in `report.py`'s `_metric()` helper and the repeated `if x is not None:` guards throughout `rules.py`. More code, but code whose omissions are the actual point.

### Decision 3: Ship the deploy scripts as a shared shell script rather than duplicated per-platform unit logic

**Why:** systemd units and launchd plists have no shared templating mechanism, so any logic embedded directly in either format (the self-sync guard, in particular) has to be reimplemented in the other's syntax — and the self-sync bug's root cause was exactly that duplication drifting apart. Extracting `sync-to-aggregator.sh` as the single source of truth both units/plists invoke removes the drift mechanism rather than just the one bug it caused.
**Trade-off:** An extra layer of indirection (plist/unit → shell script → actual work) for what could in principle be a single `rsync` line, but the indirection is exactly where the safety logic (the self-sync guard) needed to live once, not twice.

### Decision 4: Scope the README's stated metric domain wider than the shipped collectors, and never reconcile them

**Why (as inferred, not stated):** The README functions partly as a design/pitch document written before implementation (its own "Getting started: _TBD once implemented_" line signals this), and the 10-task implementation plan narrowed scope during execution — a normal and often correct thing to do under time pressure.
**Trade-off:** Unlike atri-sangam, which built a documentation convention (struck-through roadmap items) specifically to keep this kind of narrowing visible, `local_watch`'s README has no such marker, so the gap between pitch and shipped reality is currently invisible to anyone who hasn't read the collector source — this review's most concrete recommendation (§ Priority Actions in the critique) is to close that gap the same way atri-sangam does.

## 7. What This Pattern Teaches

### Lesson 1 — A type that distinguishes "unknown" from "empty" is a safety mechanism, not a style preference

The entire fail-open incident and its fix both trace back to one function's return type. `str | None` versus `str` looks like a minor typing decision until you notice that collapsing it is precisely what let a dead collector paint green. The generalizable lesson: anywhere a system reports "no data" and "data says zero" through the same channel, that channel is a latent fail-open bug waiting for the day a probe actually breaks.

### Lesson 2 — "Tests pass" and "deployable" are different definitions of done for a daemon, and the difference needs its own tests

The packaging gap survived an entire implementation plan's worth of green tests because nothing in that plan's test suite exercised a fresh, non-editable install. For any project whose actual deliverable is a running background process rather than a library import, "can a clean checkout produce the artifact every deploy step invokes" deserves to be a first-class, CI-checked assertion (as `test_packaging.py` now is) from the start, not discovered by an operator on deploy day.

### Lesson 3 — Duplicated safety logic across platforms will drift; extract it before the second platform exists, not after

The self-sync guard existed in some form before the fix — the bug was that the check was live on one platform's config and not consistently enforced across both, because it lived in per-platform artifacts (unit file, plist) with no shared source of truth. `sync-to-aggregator.sh`'s post-fix design (one script both platforms invoke) is the correct shape; the lesson is to reach for that shape the first time cross-platform logic needs to agree, not after the first divergence causes an incident.

### Lesson 4 — A production incident converted into a named regression test is worth more than the same incident described in a postmortem

Every one of the four incidents this document and its companion critique describe is represented in the test suite by a test whose name states the historical failure, not just the current expected behavior (`test_missing_metrics_do_not_read_as_zero_percent_used`, `test_self_sync_message_explains_the_actual_problem`, `test_wegofwd_llm_is_requested_with_the_anthropic_extra`). This is a stronger artifact than a changelog entry or a runbook warning: it cannot silently rot, because a regression in the fixed behavior fails CI rather than waiting to be rediscovered on the next real machine.

### Lesson 5 — A pitch document and a shipped scope will diverge under time pressure; only an explicit convention keeps the divergence visible

`local_watch`'s README oversold its metric domain not through any dishonesty in the code, but through ordinary scope-narrowing during a fast implementation pass that nothing in the doc-writing process caught. Compare atri-sangam's roadmap convention, built specifically to survive this pressure by making "not yet built" a first-class, skim-visible state rather than a fact a reader has to derive by cross-referencing source files. The lesson generalizes past this project: any team moving fast enough to narrow scope mid-implementation needs a documentation habit that survives the narrowing, not just a documentation habit that was accurate at the moment it was written.

---

*Analysis based on `main` at `13e387e`, grounded in a full read of `local_watch/**`, `tests/**`, `deploy/**`, `pyproject.toml`, `README.md`, `.github/workflows/ci.yml`, and `git log origin/main` (37 commits, 5 PRs, 2026-08-29 → 2026-08-31). Consistent with the companion [local-watch-critique.md](local-watch-critique.md) (v1.0). Cost-of-time-and-money analysis is maintained privately.*
