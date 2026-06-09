# claude_memory (git-backed portable per-project Claude memory) — Real-World Cost Analysis

**Reviewed:** 2026-06-09 (v1.0 — first review)
**Reviewer:** Claude (Anthropic)
**Question being answered:** if this same tooling had been designed, built, and documented by a conventional team in the real world (not by a single founder with Claude-assisted execution), what would it have cost in money and calendar time?
**Scope of measurement:** the on-disk system as of 2026-06-09 — one global `Stop` hook (~6-line shell body), the encoded-path convention, ten private memory repos + their remotes, the workspace symlinks, and the two runbooks `NEW_MACHINE_SETUP.md` (141 lines) + `claude-memory-add-project.md` (117 lines). This is **small internal DX/infra tooling**, and the estimate is sized accordingly — it is days of senior work, not a product build.
**Related:** [claude-memory-critique.md](claude-memory-critique.md) · [claude-memory-development-pattern.md](claude-memory-development-pattern.md) · [claude-memory-practices.md](claude-memory-practices.md)

---

> Proportionality note up front: this is **deliberately a small cost doc** because it analyzes a small thing. The deliverable is a hook + a convention + two runbooks, totaling a few hundred lines of shell/markdown. The interesting cost story is not the headline multiplier (the absolute dollars are tiny either way) but the **distance between "looks like a one-liner" and "actually designed correctly"** — the no-op-safe hook, the `$PWD`-reset verification gotcha, the path-dependency caveat, and the diagnosis discipline are what a competent team would actually spend its days on.

---

## 1. What was actually built (measured)

| Component | Measure |
|---|---|
| Global `Stop` hook | ~6-line shell body in `~/.claude/settings.json` (`async`, 30 s timeout); no-op-safe; `add → diff-guard → commit → push` |
| Convention | Encoded-path rule (`sed 's|[/_]|-|g'`); cwd-keying; symlink-view-in-non-repo-parent rule |
| Stores | **10** private git repos under `~/.claude/projects/<encoded-path>/memory/`, 10/10 PRIVATE remotes; ~236 KB / ~100 `.md` total |
| Workspace view | 8 `_claude-memory-*` symlinks into the workspace |
| Runbooks | `NEW_MACHINE_SETUP.md` (141 ln, hook JSON + clone-all MAP + symlink script + verify + path-dependency section) · `claude-memory-add-project.md` (117 ln, add-a-project recipe + `$PWD`-reset verify recipe) |
| Reference doc | `reference_claude_memory_git_setup.md` (the full system spec + diagnosis history) |

**Net buildable surface:** a few hundred lines of shell + markdown. There is no service, no database, no UI, no test suite. The value is in *correctness of the small parts* (no-op safety, the diff guard, the verify discipline) and in the documentation, not in volume of code.

---

## 2. What a conventional team would actually do

A real team does not "write a 6-line hook" in 6 minutes. To produce *this* artifact — correct and documented — a competent infra/DX engineer would:

1. **Investigate** how Claude Code stores per-project memory and where (the encoded-path discovery, the cwd-keying behavior, the `MEMORY.md` index format). This is reverse-engineering, not greenfield — and the real system shows it took *three* passes (twice mis-diagnosed). Call it **~1 day**.
2. **Design** the durability model: git-per-store vs one monorepo; remote naming; private-by-default; symlink view placement; the no-op-safe global-hook approach. **~0.5 day.**
3. **Build + harden the hook**: the `[ -d .git ] || exit 0` guard, the `diff --cached` guard, `async`/timeout, `exit 0`-always, and *test it under the real `$PWD`-reset condition* (the gotcha that a naive `bash -c` test gets wrong). **~0.5–1 day.**
4. **Wire the repos**: create N private remotes, init/seed/push each, make the symlinks. At 10 repos this is real (if repetitive) work. **~0.5 day.**
5. **Write the runbooks**: a new-machine restore runbook (verified in a temp dir) and an add-a-project recipe, including the path-dependency caveat and the verify-shipped discipline. Good runbooks that are *actually verified end-to-end* are most of the value here. **~1–1.5 days.**

**Total: ~3.5–4.5 engineer-days** of a senior infra/DX engineer for a correct, documented, verified version. Round to **~4 engineer-days (~0.2 engineer-months)**.

This is the honest size. It is not 0 (the correctness and the verified runbooks are real work), and it is not weeks (there is no product here).

---

## 3. Cost scenarios

Sized at ~4 senior infra/DX engineer-days. Loaded rates are fully burdened.

### Scenario A — US senior infra/DX engineer

| Line | Value |
|---|---|
| Senior infra/DX engineer, loaded | ~$340k/yr ≈ **~$1,400/day** |
| 4 days | **~$5,600** |
| (Optional) a second pair of eyes / light review on the hook + runbook | ~$1,000 |
| **Scenario A total** | **~$6k–7k** |

### Scenario B — Blended / global senior contractor

| Line | Value |
|---|---|
| Senior contractor, loaded | ~$90k/yr ≈ **~$370/day** |
| 4 days | **~$1,500** |
| Review | ~$300 |
| **Scenario B total** | **~$1.8k** |

Infra cost is effectively **$0** — the memory repos sit inside an existing GitHub account on the free private-repo tier; there is no compute, no hosting, no third-party SaaS. The only ongoing "cost" is the few seconds of git activity per session, which is free.

---

## 4. Calendar time

| Scenario | Wall-clock |
|---|---|
| US senior engineer, focused | **~1 working week** (4 days + review) |
| Blended contractor | ~1 week |
| **Actual (single founder + Claude, woven into other work)** | **~1–2 days of effective effort** spread across 2026-06-01 → 2026-06-09, *concurrent with active work on ~8 other projects* — the system was diagnosed/formalized on 2026-06-01 and extended (`wegofwd-llm`, `pramana`) on 2026-06-09 |

The actual effort was *interstitial*: it happened in the gaps of working on the projects the memory serves, which is exactly how internal tooling tends to get built by a founder. The "~6.5 weeks elapsed" framing used for the product critiques does not apply — this is days of effort, not weeks.

---

## 5. What was actually spent

| Line item | Estimate |
|---|---|
| Founder time (~1–2 effective days, interstitial) | ~8–16 hours |
| Claude Code subscription / API (already paid for the product work) | ~$0 marginal |
| GitHub private repos (10 × `*-memory`) | **$0** (free private tier) |
| Compute / hosting | **$0** (no service) |
| **Direct cash outlay** | **~$0** |
| Founder opportunity cost @ ~$300k/yr × ~1.5 days | **~$1.7k** |
| **All-in actual cost** | **~$1.7k** |

---

## 6. Headline ratios

| Comparison | US scenario | Blended scenario |
|---|---|---|
| Cash-only multiplier | **~6.5k× / ~∞** ($6.5k ÷ ~$0 direct cash) | **~1.8k× / ~∞** |
| All-in multiplier (incl. founder opp-cost) | **~3.8× cheaper** ($6.5k ÷ ~$1.7k) | **~1.1× cheaper** ($1.8k ÷ ~$1.7k) |
| Calendar compression | **~3–5× faster** (~1–2 days vs ~1 week) | similar |

**Read these honestly: the multipliers are large in *ratio* but tiny in *absolute dollars* (a few thousand either way), because the thing itself is small.** The cash-only ratio is enormous mainly because the direct outlay is ~$0 (free private repos, no compute) — that is a property of the *infrastructure choice*, not of AI leverage. The all-in multiplier is modest (~1–4×) precisely because there's so little work for AI to compress: 4 engineer-days is already small, and a chunk of it (creating 10 remotes, writing careful runbooks) is irreducible manual/judgment work that doesn't collapse the way boilerplate does.

This is the opposite end of the spectrum from the product critiques (OnDemand ~27×, Thittam ~61× US all-in): small, judgment-heavy infra shows a *low* compression multiplier, which is the informative result — AI assistance helps most where there's volume to generate, and this artifact is almost entirely correctness-and-documentation, not volume.

---

## 7. Honest caveats

- **The estimate is for a *correct, documented, verified* version.** A team that skipped the runbooks and the `$PWD`-reset verification could "build a sync hook" in an afternoon — but they'd ship the silent-failure and portability footguns without the docs that at least *name* them. The 4-day figure buys the documentation and the verification, which is most of the real value.
- **The diagnosis cost is real and easy to under-count.** The actual system was *twice mis-diagnosed* before being understood (reference memory). A team encountering Claude Code's memory cold would burn the same discovery time; this is why step 1 is a full day, not an hour.
- **Reliability/privacy gaps are not yet closed.** The critique flags silent-hook failure (which already cost `pramana` its off-machine durability for a period), no redaction, and one-token-gates-all-ten. Closing those (a log line + doctor check + secret scan + fine-grained PAT) is *another* ~1–2 engineer-days a real team would likely add — so a *hardened* version is ~5–6 days, not 4.
- **Absolute dollars are tiny.** This doc exists for completeness and proportion; the cost story for this artifact is "a few senior-engineer-days, ~$0 cash, large ratio because the cash floor is zero," not a headline number worth optimizing.

---

## 8. What this means

The genuinely cheap thing here isn't the build — it's the **operating cost: ~$0 forever**, because the durability rides on free private GitHub repos and a hook that costs a few seconds of git per session. A founder gets durable, version-controlled, cross-machine Claude memory across ten projects for no recurring spend and ~1–2 days of interstitial effort. The conventional-team comparison ($6k–7k US, ~1 week) is real but small; the more useful observation is that this is **the right *size* of tooling for the problem** — it solves cross-session/cross-machine context loss with the minimum viable mechanism (git + one hook + a convention), and the only thing standing between "good" and "robust" is ~1–2 more days of observability + secret-hygiene work, not a rewrite.

---

*Cost analysis is a point-in-time exercise sized to a small internal-tooling artifact. Measured on 2026-06-09 from the on-disk hook, the ten memory repos and their private remotes, and the two runbooks (141 + 117 lines). Loaded rates and AI tooling capability evolve; re-run if the system grows a service, a UI, or the hardening described in the critique. The large cash-only ratio is a function of the ~$0 infrastructure floor, not of code volume.*
